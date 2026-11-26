"""Kiểm thử chuẩn bị Formal Benchmark `P06-E01-T09` (100% ngoại tuyến).

1. File này giải quyết vấn đề gì?
   Xác minh các chỉnh sửa tối thiểu trước Formal Benchmark:
   - Đồng bộ ngân sách từ `compute_chunk_word_budget(8.0)` giữa `ScriptFirstBaseline`
     và `LangGraph` (`12–18 từ`, trần `20 từ`, `rewrite_attempt=0` ở baseline).
   - Tính đầy đủ và hợp lệ của `fact_refs` trong `e01_ext_v1_story_plans.json`.
   - Tính hợp lệ của hồ sơ `e01_formal_v1` (`36` chunks, `window_stress_12lag_3sku` `36` chủ đề,
     `lag=12` phân tách `W=5/10/20` trong mô phỏng Mock).
   - Tính mù hoàn toàn và không điền sẵn điểm của tài liệu hướng dẫn chấm Pilot v2.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import sys
import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from p06.adapters.mocks import MockPlaybackAckBus
from p06.adapters.p05_knowledge_adapter import P05KnowledgeAdapter
from p06.agent.nodes._common import _compute_word_budget
from p06.baselines import BaselineScriptSource, ScriptFirstBaseline
from p06.baselines.script_first import _UPFRONT_SYSTEM_PROMPT_TEMPLATE
from p06.evaluation.metrics.coverage import compute_coverage_metrics
from p06.evaluation.models import (
    PlaybackEventRecord,
    RunEvidence,
    TranscriptEntry,
)
from p06.memory import (
    RepetitionAction,
    RepetitionCategory,
    RepetitionDetector,
    ShortTermPlayedHistory,
)
from p06.planning.prompt_loader import load_prompt_template
from p06.providers import (
    GeminiRawResponse,
    MockBehavior,
    MockLLMProvider,
    MockResponseStep,
    ProviderConfigError,
)
from p06.runner import (
    ExperimentMethod,
    RunTerminationReason,
    load_e01_story_plan,
    load_experiment_run_config,
    run_e01_sweep,
)
from p06.schemas import PlayedTurnSummary, StoryCheckpoint, StoryPlan
from p06.simulation import SimulatedPlaybackHarness, VirtualClock, compute_chunk_word_budget

P06_ROOT = Path(__file__).resolve().parents[2]
EXT_SKUS_PATH = P06_ROOT / "data" / "products" / "e01_ext_v1_verified_skus.json"
EXT_PLANS_PATH = P06_ROOT / "data" / "story_plans" / "e01_ext_v1_story_plans.json"
FORMAL_SKUS_PATH = P06_ROOT / "data" / "products" / "e01_formal_v1_verified_skus.json"
FORMAL_PLANS_PATH = P06_ROOT / "data" / "story_plans" / "e01_formal_v1_story_plans.json"
BATCH1A_CONFIG_PATH = P06_ROOT / "configs" / "experiments" / "p06_e01_formal_batch1a.yaml"
TRACK2A_CONFIG_PATH = P06_ROOT / "configs" / "experiments" / "p06_e01_formal_track2a_w5_w10.yaml"
TRACK2B_CONFIG_PATH = P06_ROOT / "configs" / "experiments" / "p06_e01_formal_track2b_w10_w20.yaml"
FORMAL_BATCH_SCRIPT_PATH = (
    P06_ROOT / "experiments" / "p06_e01_no_comments" / "run_gemini_formal_batch.py"
)
PILOT_V2_DIR = P06_ROOT / "runs" / "P06-E01" / "gemini_3.5_flash_lite_pilot_v2"
PILOT_V2_HE_DIR = PILOT_V2_DIR / "human_eval"
PILOT_V2_AI_DIR = PILOT_V2_DIR / "ai_assisted_eval"
START_AT = datetime(2026, 11, 27, 0, 0, 0, tzinfo=timezone.utc)


def _load_formal_batch_module() -> Any:
    spec = importlib.util.spec_from_file_location("run_gemini_formal_batch", FORMAL_BATCH_SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def tmp_path() -> Iterator[Path]:
    """Cấp thư mục tạm cô lập trong `.pytest_cache` và dọn sạch sau mỗi test."""
    base_dir = P06_ROOT / ".pytest_cache" / f"formal_prep_tmp_{uuid.uuid4().hex[:10]}"
    base_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield base_dir
    finally:
        shutil.rmtree(base_dir, ignore_errors=True)


def test_word_budget_synced_between_script_first_and_langgraph() -> None:
    """Ngân sách từ `8.0s` ở 2.6 từ/giây phải đồng nhất: khuyến nghị `12–18 từ`, trần `20 từ`."""
    rec_max, hard_max, target_range = compute_chunk_word_budget(8.0)
    assert rec_max == 18
    assert hard_max == 20
    assert target_range == "12–18 từ"
    assert _compute_word_budget(8.0) == (18, "12–18 từ")

    # Kiểm chứng biên 20 từ <= 8.0s và 21 từ > 8.0s trực tiếp từ VirtualClock.
    words_20 = " ".join(["từ"] * 20)
    words_21 = " ".join(["từ"] * 21)
    assert VirtualClock.estimate_raw_speech_duration_ms(words_20) <= 8000
    assert VirtualClock.estimate_raw_speech_duration_ms(words_21) > 8000

    plan, _, _ = load_e01_story_plan("pilot_short_3sku_ext", story_plans_path=EXT_PLANS_PATH)
    adapter = P05KnowledgeAdapter.from_seed_file(EXT_SKUS_PATH)
    clock = VirtualClock(start_at=START_AT)
    cp = StoryCheckpoint(
        tenant_id=plan.tenant_id,
        session_id=plan.session_id,
        session_epoch=1,
        plan_id=plan.plan_id,
        plan_revision=plan.plan_revision,
        active_sku_id="SKU-HONEY-01",
        current_arc_id=plan.arcs[0].arc_id,
        next_topic_id=plan.arcs[0].topics[0].topic_id,
        updated_at=START_AT,
    )
    harness = SimulatedPlaybackHarness(
        initial_checkpoint=cp,
        expected_simulation_run_id="sim-sync-check",
        story_plan=plan,
    )
    bus = MockPlaybackAckBus(clock=clock, simulation_run_id="sim-sync-check")
    captured_prompts: list[str] = []

    class _InspectMock(MockLLMProvider):
        def generate_structured(self, request: Any, output_schema: Any) -> Any:
            captured_prompts.append(request.system_prompt)
            return super().generate_structured(request, output_schema)

    provider = _InspectMock(
        response_sequence=[
            MockResponseStep(
                behavior=MockBehavior.VALID_JSON,
                payload={
                    "text": "Mật ong sánh dẻo màu vàng hổ phách vị ngọt dịu tự nhiên.",
                    "cited_evidence_ids": ["ev-e01-ext-honey-sensory"],
                    "covered_claim_ids": ["clm-e01-ext-honey-allowed-03"],
                },
            ),
            MockResponseStep(
                behavior=MockBehavior.VALID_JSON,
                payload={
                    "text": " ".join(["Mật"] * 21),
                    "cited_evidence_ids": ["ev-e01-honey-shipping"],
                    "covered_claim_ids": ["clm-e01-honey-allowed-02"],
                },
            ),
        ]
    )
    baseline = ScriptFirstBaseline(
        knowledge_verifier=adapter,
        playback_bus=bus,
        harness=harness,
        clock=clock,
        llm_provider=provider,
        script_source=BaselineScriptSource.UPFRONT_LLM,
        max_chunk_duration_sec=8.0,
    )
    res = baseline.run_session(plan, active_sku_id="SKU-HONEY-01")
    assert len(captured_prompts) == 2
    assert "12–18 từ" in captured_prompts[0]
    assert "20 từ" in captured_prompts[0]
    assert res.turns[1].outcome.value == "SAFE_ABORT_NO_CANDIDATE"
    assert "tối đa 20 từ" in (res.turns[1].failure_reason or "")
    # Bảo đảm ScriptFirst vẫn KHÔNG có dynamic rewrite (đúng 1 call cho mỗi topic).
    assert res.metrics.llm_calls == 2


def test_e01_ext_v1_story_plans_evidence_completeness() -> None:
    """Toàn bộ fact_refs trong e01_ext_v1 phải hợp lệ theo SKU và phủ đủ ý macadamia."""
    skus_doc = json.loads(EXT_SKUS_PATH.read_text(encoding="utf-8"))
    plans_doc = json.loads(EXT_PLANS_PATH.read_text(encoding="utf-8"))
    sku_by_eid = {c["evidence_id"]: c["sku_id"] for c in skus_doc["evidence_chunks"]}

    for plan_name, raw_plan in plans_doc["plans"].items():
        plan = StoryPlan.model_validate(raw_plan)
        for arc in plan.arcs:
            for topic in arc.topics:
                assert topic.fact_refs, f"{plan_name}/{topic.topic_id} thiếu fact_refs."
                for eid in topic.fact_refs:
                    assert eid in sku_by_eid, f"Không tìm thấy {eid} trong verified_skus."
                    assert sku_by_eid[eid] == topic.sku_id

    pilot_topics = {
        t["topic_id"]: t
        for a in plans_doc["plans"]["pilot_short_3sku_ext"]["arcs"]
        for t in a["topics"]
    }
    assert {"ev-e01-ext-macadamia-harvest", "ev-e01-ext-macadamia-sensory", "ev-e01-macadamia-quality"} <= set(
        pilot_topics["topic-pilot-macadamia-01"]["fact_refs"]
    )
    assert {"ev-e01-macadamia-shipping", "ev-e01-ext-macadamia-packaging", "ev-e01-macadamia-usage"} <= set(
        pilot_topics["topic-pilot-macadamia-02"]["fact_refs"]
    )


def test_e01_formal_v1_capacity_and_window_lag12_mock_validation(tmp_path: Path) -> None:
    """Hồ sơ e01_formal_v1 có 36 evidence/36 topic độc lập (12/SKU) và chạy đủ W=5/10/20."""
    adapter = P05KnowledgeAdapter.from_seed_file(FORMAL_SKUS_PATH)
    at_now = datetime(2026, 11, 27, 0, 0, tzinfo=timezone.utc)
    total_chunks = 0
    for sku_id in ("SKU-HONEY-01", "SKU-TEA-02", "SKU-MACADAMIA-03"):
        view = adapter.get_sku_evidence("tenant-p06-poc-01", sku_id, at_time=at_now)
        assert view.is_eligible is True
        assert len(view.approved_chunks) == 12
        total_chunks += len(view.approved_chunks)
    assert total_chunks == 36

    plan, _, _ = load_e01_story_plan("window_stress_12lag_3sku", story_plans_path=FORMAL_PLANS_PATH)
    assert plan.is_mvp_live_eligible() is True
    assert len(plan.mandatory_topic_ids()) == 36

    cfg = load_experiment_run_config(
        scenario="window_stress_12lag_3sku",
        dataset_profile="e01_formal_v1",
        method=ExperimentMethod.LANGGRAPH,
        history_window=10,
        min_chunks_per_topic=2,
        output_dir=tmp_path / "cfg_check",
    )
    assert cfg.dataset_profile == "e01_formal_v1"

    sweep_res = run_e01_sweep(
        scenarios=("window_stress_12lag_3sku",),
        methods=(ExperimentMethod.SCRIPT_FIRST_UPFRONT_LLM, ExperimentMethod.LANGGRAPH),
        dataset_profile="e01_formal_v1",
        min_chunks_per_topic=2,
        history_windows=(5, 10, 20),
        output_dir=tmp_path / "formal_mock_sweep",
    )
    assert len(sweep_res.run_results) == 4
    assert sweep_res.comparison_report is not None
    assert sweep_res.comparison_report.compatible is True
    for run in sweep_res.run_results:
        assert run.report is not None
        cov = run.report.coverage["mandatory_topic_coverage"]
        assert cov.value is not None
        assert len(run.evidence.transcript) >= 72
        if run.manifest.get("history_window") == 20:
            # Ở lag=12 < W=20, lượt thứ 2 của cùng topic (chỉ có 1 claim_id) kích hoạt REPEATED_FACTS
            # và cạn 2 fallback/SKU -> dừng an toàn MAX_CONSECUTIVE_ABORTS khi chưa đủ 2 chunks cho mọi
            # topic; mandatory_topic_coverage phải phản ánh trung thực (< 1.0) thay vì báo nhầm 1.0.
            assert run.termination_reason == RunTerminationReason.MAX_CONSECUTIVE_ABORTS
            assert 0.0 < cov.value < 1.0
            assert cov.metadata["min_chunks_per_topic"] == 2
            assert len(cov.metadata["partially_covered_topic_ids"]) > 0
        else:
            assert cov.value == pytest.approx(1.0)
            assert run.termination_reason == RunTerminationReason.EARLY_COMPLETION


def test_coverage_metric_respects_min_chunks_per_topic() -> None:
    """`compute_coverage_metrics` chỉ tính hoàn tất topic khi số ACK không-fallback >= `min_chunks_per_topic`."""
    plan, _, _ = load_e01_story_plan("pilot_short_3sku_ext", story_plans_path=EXT_PLANS_PATH)
    mandatory_topics = sorted(plan.mandatory_topic_ids())
    first_topic = mandatory_topics[0]

    def _make_evidence(min_chunks: int, topic_ack_counts: dict[str, int]) -> RunEvidence:
        transcript: list[TranscriptEntry] = []
        playback: list[PlaybackEventRecord] = []
        idx = 0
        for tid, count in topic_ack_counts.items():
            for part in range(count):
                turn_id = f"turn-{idx}"
                occ_iso = (
                    (START_AT + timedelta(seconds=(idx + 1) * 4))
                    .isoformat()
                    .replace("+00:00", "Z")
                )
                transcript.append(
                    TranscriptEntry(
                        turn_id=turn_id,
                        turn_index=idx,
                        sku_id="SKU-HONEY-01",
                        candidate_id=f"cand-{idx}",
                        intent="STORY_TELLING",
                        text=f"Lời thoại hợp lệ cho {tid} phần {part}.",
                        confirmed_topic_ids=(tid,),
                        origin="PROACTIVE_STORY",
                        verification_status="VERIFIED",
                        is_fallback=False,
                        actual_duration_ms=4000,
                        playback_event_id=f"pb-{idx}",
                        occurred_at_utc=occ_iso,
                    )
                )
                playback.append(
                    PlaybackEventRecord(
                        sequence_index=idx,
                        playback_event_id=f"pb-{idx}",
                        turn_id=turn_id,
                        candidate_id=f"cand-{idx}",
                        sku_id="SKU-HONEY-01",
                        outcome="COMPLETED",
                        apply_status="APPLIED",
                        applied=True,
                        confirmed_topic_ids=(tid,),
                        actual_duration_ms=4000,
                        occurred_at_utc=occ_iso,
                    )
                )
                idx += 1
        return RunEvidence(
            manifest={
                "run_id": "test-min-chunks",
                "min_chunks_per_topic": min_chunks,
                "virtual_clock_start_utc": "2026-11-27T00:00:00Z",
            },
            story_plan=plan,
            transcript=tuple(transcript),
            playback_events=tuple(playback),
            graph_traces=(),
            target_duration_sec=600.0,
            simulated_elapsed_sec=float(idx * 4),
        )

    # 1 chunk/topic với min_chunks_per_topic=2 -> coverage phải bằng 0.0 và ghi vào partially_covered_topic_ids.
    res_partial = compute_coverage_metrics(_make_evidence(2, {tid: 1 for tid in mandatory_topics}))
    assert res_partial["completed_topic_count"].value == 0
    assert res_partial["mandatory_topic_coverage"].value == pytest.approx(0.0)
    assert set(res_partial["mandatory_topic_coverage"].metadata["partially_covered_topic_ids"]) == set(
        mandatory_topics
    )
    assert res_partial["time_to_complete_mandatory_topics_sec"].value is None

    # 2 chunks/topic cho riêng first_topic, các topic khác mới 1 -> 1 / len(mandatory_topics).
    counts_mixed = {tid: 1 for tid in mandatory_topics}
    counts_mixed[first_topic] = 2
    res_mixed = compute_coverage_metrics(_make_evidence(2, counts_mixed))
    assert res_mixed["completed_topic_count"].value == 1
    assert res_mixed["mandatory_topic_coverage"].value == pytest.approx(1.0 / len(mandatory_topics))

    # Đủ 2 chunks cho toàn bộ mandatory_topics -> 1.0 và có time_to_complete_mandatory_topics_sec.
    res_full = compute_coverage_metrics(_make_evidence(2, {tid: 2 for tid in mandatory_topics}))
    assert res_full["completed_topic_count"].value == len(mandatory_topics)
    assert res_full["mandatory_topic_coverage"].value == pytest.approx(1.0)
    assert res_full["mandatory_topic_coverage"].metadata["partially_covered_topic_ids"] == []
    assert res_full["time_to_complete_mandatory_topics_sec"].value == pytest.approx(
        float(len(mandatory_topics) * 2 * 4)
    )


def test_safety_review_fixes_in_datasets_and_prompts() -> None:
    """Xác minh các sửa lỗi Targeted Safety Review (A/B/C) và quy tắc prompt v0.2.1."""
    ext_plans = json.loads(EXT_PLANS_PATH.read_text(encoding="utf-8"))
    formal_plans = json.loads(FORMAL_PLANS_PATH.read_text(encoding="utf-8"))
    assert ext_plans["dataset_meta"]["version"] == "1.0.2"
    assert formal_plans["dataset_meta"]["version"] == "1.1.1"

    ext_topics = {
        t["topic_id"]: t
        for sc in ext_plans["plans"].values()
        for a in sc["arcs"]
        for t in a["topics"]
    }
    formal_topics = {
        t["topic_id"]: t
        for sc in formal_plans["plans"].values()
        for a in sc["arcs"]
        for t in a["topics"]
    }

    # A. Bảo toàn điều kiện chính sách đổi trả ("khi nhận hàng kèm video mở hộp" / "khi mở hộp").
    for tid in ("topic-pilot-honey-02", "topic-ext-sales-honey-offer"):
        joined = " ".join(ext_topics[tid]["talking_points"]).lower()
        assert "khi nhận hàng" in joined and "video mở hộp" in joined
    assert "khi nhận hàng" in " ".join(formal_topics["topic-formal-honey-09"]["talking_points"]).lower()
    assert "video mở hộp" in " ".join(formal_topics["topic-formal-honey-09"]["talking_points"]).lower()
    for tid in ("topic-ext-sales-macadamia-offer", "topic-stress-macadamia-08"):
        assert "khi mở hộp" in " ".join(ext_topics[tid]["talking_points"]).lower()
    assert "khi mở hộp" in " ".join(formal_topics["topic-formal-macadamia-09"]["talking_points"]).lower()

    # B. Sửa suy diễn nhân quả chưa được chứng minh & lỗi Batch 1A tea-pairing ("hạt rang bùi").
    mac_pilot_tp = " ".join(ext_topics["topic-pilot-macadamia-01"]["talking_points"]).lower()
    assert "giữ độ giòn béo" not in mac_pilot_tp
    assert "chín đều" in mac_pilot_tp and "giòn béo tự nhiên" in mac_pilot_tp

    tea_edu_tp = " ".join(ext_topics["topic-ext-edu-tea-pairing"]["talking_points"]).lower()
    assert "hạt rang bùi" not in tea_edu_tp
    assert "bánh quy nhạt" in tea_edu_tp and "mứt gừng nhẹ" in tea_edu_tp

    # C. Prompt safety rules + version bump.
    gen_tmpl = load_prompt_template("story_generation.txt")
    rew_tmpl = load_prompt_template("rewrite.txt")
    assert gen_tmpl.version == "v0.2.1"
    assert rew_tmpl.version == "v0.2.1"
    assert "video mở hộp" in gen_tmpl.content and "nhân quả" in gen_tmpl.content
    assert "video mở hộp" in rew_tmpl.content and "nhân quả" in rew_tmpl.content
    assert "video mở hộp" in _UPFRONT_SYSTEM_PROMPT_TEMPLATE
    assert "nhân quả" in _UPFRONT_SYSTEM_PROMPT_TEMPLATE


def test_formal_batch1a_config_guard_and_global_ledger_offline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Batch 1A khóa đúng thông số, chặn live provider thiếu cờ và chạy Mock+FakeClient ổn định."""
    mod = _load_formal_batch_module()
    cfg = mod.load_batch_config(BATCH1A_CONFIG_PATH)
    assert cfg["model_id"] == "gemini-3.5-flash-lite"
    assert cfg["billing_tier"] == "free_tier"
    assert cfg["max_cost_usd"] == 0.0
    assert cfg["dataset_profile"] == "e01_ext_v1"
    assert cfg["scenario"] == "product_education_10m_ext"
    assert cfg["seed"] == 42
    assert cfg["min_chunks_per_topic"] == 1
    assert cfg["max_chunk_duration_sec"] == 8.0
    assert cfg["max_requests_per_run"] == 30
    assert cfg["global_max_requests"] == 120
    assert cfg["min_request_interval_sec"] == 6.0
    assert [(r["method"], r["history_window"]) for r in cfg["runs"]] == [
        ("script_first_upfront_llm", None),
        ("langgraph_structured_story", 5),
        ("langgraph_structured_story", 10),
        ("langgraph_structured_story", 20),
    ]

    # Offline Guard: không có allow_live_provider=True phải chặn ngay.
    with pytest.raises(ProviderConfigError, match="Offline Guard"):
        mod.execute_formal_batch(BATCH1A_CONFIG_PATH, output_dir_override=tmp_path / "blocked")

    # Chạy 100% ngoại tuyến bằng Mock qua execute_formal_batch -> tạo đủ ledger, summary, comparison, human_eval.
    mock_out = tmp_path / "batch1a_mock"
    summary_mock = mod.execute_formal_batch(
        BATCH1A_CONFIG_PATH,
        provider_override="mock",
        output_dir_override=mock_out,
    )
    assert summary_mock["status"] == "COMPLETED"
    assert len(summary_mock["runs"]) == 4
    assert summary_mock["comparison_compatible"] is True
    assert (mock_out / "budget_ledger.json").is_file()
    assert (mock_out / "batch_summary.json").is_file()
    assert (mock_out / "comparison.json").is_file()
    assert (mock_out / "human_eval" / "blind_eval_sheet.csv").is_file()

    # Giả lập FakeGeminiRestClient ngoại tuyến để xác minh global_max_requests & shared client accounting.
    ext_skus_doc = json.loads(EXT_SKUS_PATH.read_text(encoding="utf-8"))
    evidence_by_sku: dict[str, list[str]] = {}
    claims_by_sku: dict[str, list[str]] = {}
    for c in ext_skus_doc["evidence_chunks"]:
        evidence_by_sku.setdefault(c["sku_id"], []).append(c["evidence_id"])
    for c in ext_skus_doc["claim_registry"]:
        if c["category"] == "ALLOWED":
            claims_by_sku.setdefault(c["sku_id"], []).append(c["claim_id"])

    class FakeGeminiRestClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            _ = args
            self.max_requests = int(kwargs.get("max_requests") or 120)
            self.requests_attempted = 0
            self.rate_limited = False

        def generate_json(
            self,
            model_id: str,
            system_prompt: str,
            user_prompt: str,
            json_schema: dict[str, Any],
            sampling: dict[str, Any],
            timeout_sec: float,
        ) -> GeminiRawResponse:
            _ = (model_id, json_schema, sampling, timeout_sec)
            self.requests_attempted += 1
            active_sku = "SKU-HONEY-01"
            for sku in ("SKU-HONEY-01", "SKU-TEA-02", "SKU-MACADAMIA-03"):
                if sku in system_prompt or sku in user_prompt:
                    active_sku = sku
                    break
            ev_id = evidence_by_sku[active_sku][self.requests_attempted % len(evidence_by_sku[active_sku])]
            clm_id = claims_by_sku[active_sku][self.requests_attempted % len(claims_by_sku[active_sku])]
            # Tạo câu có vốn từ khác nhau theo lượt để tránh kích hoạt ngưỡng Word Jaccard 0.65.
            noun_a = (
                "hương thơm", "độ sánh", "màu sắc", "chất lượng", "quy trình",
                "đóng gói", "bảo quản", "thu hoạch", "nguyên liệu", "tiêu chuẩn",
            )[self.requests_attempted % 10]
            noun_b = (
                "tự nhiên", "đặc trưng", "tinh tế", "ổn định", "cẩn thận",
                "an toàn", "minh bạch", "truyền thống", "hài hòa", "thanh nhẹ",
            )[(self.requests_attempted // 3) % 10]
            phrase = f"Điểm nhấn thứ {self.requests_attempted} về {noun_a} mang nét {noun_b} cho sản phẩm."
            payload = {
                "text": phrase,
                "role": "PRODUCT_STORY",
                "cited_evidence_ids": [ev_id],
                "covered_claim_ids": [clm_id],
                "stated_price_vnd": None,
                "mentions_ocop": False,
                "semantic_breakpoint": True,
                "breakpoint_type": "TOPIC_END",
                "rationale": "Fake Gemini offline verification.",
            }
            return GeminiRawResponse(
                raw_text=json.dumps(payload, ensure_ascii=False),
                input_tokens=100,
                output_tokens=25,
                thinking_tokens=None,
                finish_reason="STOP",
            )

    monkeypatch.setenv("GEMINI_API_KEY", "dummy-offline-test-key")
    fake_out = tmp_path / "batch1a_fake_gemini"
    summary_fake = mod.execute_formal_batch(
        BATCH1A_CONFIG_PATH,
        provider_override="gemini",
        allow_live_provider=True,
        output_dir_override=fake_out,
        rest_client_factory=FakeGeminiRestClient,
    )
    assert summary_fake["status"] == "COMPLETED"
    assert summary_fake["cumulative_global_requests"] <= 120
    assert summary_fake["total_requests_attempted_in_session"] >= 72
    assert summary_fake["artifact_locks"]["story_plans_version"] == "1.0.2"
    ledger = json.loads((fake_out / "budget_ledger.json").read_text(encoding="utf-8"))
    assert ledger["global_max_requests"] == 120
    assert ledger["max_requests_per_run"] == 30
    assert len(ledger["runs"]) == 4


def test_pilot_v2_ai_assisted_eval_isolated_from_human_eval() -> None:
    """Bảo đảm hai CSV AI-assisted tách biệt hoàn toàn khỏi phiếu chấm mù human_eval gốc."""
    if not PILOT_V2_DIR.is_dir():
        pytest.skip("Không có thư mục Pilot v2.")
    assert (PILOT_V2_AI_DIR / "pilot_v2_ai_assisted_quality.csv").is_file()
    assert (PILOT_V2_AI_DIR / "pilot_v2_ai_assisted_factual_semantic.csv").is_file()
    assert (PILOT_V2_AI_DIR / "README.md").is_file()

    with (PILOT_V2_HE_DIR / "blind_eval_sheet.csv").open("r", encoding="utf-8", newline="") as handle:
        he_rows = list(csv.DictReader(handle))
    assert len(he_rows) == 2
    assert all(row["narrative_coherence"] == "" for row in he_rows)


def test_pilot_v2_reviewer_guides_remain_strictly_blind_if_present() -> None:
    """Hai tài liệu hướng dẫn người chấm Pilot v2 không được rò method, model, W hay run_id."""
    if not PILOT_V2_HE_DIR.is_dir():
        pytest.skip("Không có thư mục human_eval Pilot v2.")
    forbidden_terms = (
        "script_first",
        "langgraph",
        "gemini",
        "flash-lite",
        "w=5",
        "f722769c",
        "defb5376",
        "preapproved_fallback",
    )
    for fname in ("REVIEWER_GUIDE_BLIND_QUALITY.md", "REVIEWER_GUIDE_FACTUAL_AND_SEMANTIC_AUDIT.md"):
        fpath = PILOT_V2_HE_DIR / fname
        assert fpath.is_file(), f"Thiếu {fname}"
        content = fpath.read_text(encoding="utf-8").lower()
        leaks = [term for term in forbidden_terms if term in content]
        assert leaks == [], f"{fname} bị rò rỉ thông tin ẩn danh: {leaks}"


def test_fixed_history_detector_memory_contrast_lag6_lag8_lag12() -> None:
    """Kiểm tra cố định lịch sử (`fixed-history`) tách biệt ảnh hưởng của W=5/10/20 khỏi biến thiên LLM."""
    detector = RepetitionDetector()
    target_text = "Mật ong hoa cà phê Cư M'gar Đắk Lắk thu hoạch chính vụ chín tự nhiên."
    base_candidates = (
        ("EXACT_TEXT", target_text, ("clm-other",), RepetitionCategory.EXACT_REPLAY, RepetitionAction.REWRITE),
        (
            "LEXICAL_NEAR",
            "Mật ong hoa cà phê Cư M'gar Đắk Lắk thu hoạch chính vụ ngon.",
            ("clm-other",),
            RepetitionCategory.LEXICAL_DUPLICATION,
            RepetitionAction.REWRITE,
        ),
        (
            "PARAPHRASE_SAME_CLAIM",
            "Khách yêu thưởng thức đặc sản rẫy cà phê Tây Nguyên vào mùa hoa rộ.",
            ("clm-e01-honey-allowed-01",),
            RepetitionCategory.REPEATED_FACTS,
            RepetitionAction.SWITCH_TOPIC,
        ),
        (
            "LEGITIMATE_CONTINUATION",
            "Đóng chai thủy tinh 500ml nắp kín bảo quản nơi khô ráo thoáng mát.",
            ("clm-e01-honey-allowed-02",),
            RepetitionCategory.LEGITIMATE_CONTINUATION,
            RepetitionAction.ALLOW,
        ),
    )

    # Định nghĩa lag trên tổng số lượt đã phát L: lượt đích nằm ở chỉ số 0 nên in_window <=> lag <= W.
    for lag in (5, 6, 8, 10, 11, 12, 20, 21):
        turns: list[PlayedTurnSummary] = [
            PlayedTurnSummary(
                playback_event_id="ev-fixed-000",
                turn_id="turn-fixed-000",
                candidate_id="cand-fixed-000",
                chunk_id="chunk-fixed-target-000",
                sku_refs=["SKU-HONEY-01"],
                topic_ids=["topic-target"],
                covered_claim_ids=["clm-e01-honey-allowed-01"],
                intent="PROACTIVE_STORY:topic-target",
                spoken_text=target_text,
                occurred_at=START_AT,
                is_simulated=True,
            )
        ]
        for idx in range(1, lag):
            turns.append(
                PlayedTurnSummary(
                    playback_event_id=f"ev-fixed-{idx:03d}",
                    turn_id=f"turn-fixed-{idx:03d}",
                    candidate_id=f"cand-fixed-{idx:03d}",
                    chunk_id=f"chunk-fixed-filler-{idx:03d}",
                    sku_refs=["SKU-TEA-02"],
                    topic_ids=[f"topic-filler-{idx:03d}"],
                    covered_claim_ids=[f"clm-filler-{idx:03d}"],
                    intent=f"PROACTIVE_STORY:topic-filler-{idx:03d}",
                    spoken_text=f"Búp trà cổ thụ số hiệu {idx} hái tay vùng cao nguyên sương mù.",
                    occurred_at=START_AT + timedelta(seconds=idx * 6),
                    is_simulated=True,
                )
            )

        for window_size in (5, 10, 20):
            history = ShortTermPlayedHistory(window_size=window_size, initial_turns=turns)
            window_turns = history.recent_turns()
            in_window = lag <= window_size
            assert any(t.turn_id == "turn-fixed-000" for t in window_turns) is in_window

            for _, cand_text, cand_claims, expected_cat, expected_act in base_candidates:
                chk = detector.check(
                    candidate_text=cand_text,
                    played_turns=window_turns,
                    candidate_chunk_id="chunk-fixed-new-001",
                    topic_id="topic-target",
                    sku_id="SKU-HONEY-01",
                    intent="PROACTIVE_STORY:topic-target",
                    candidate_claim_ids=cand_claims,
                    played_chunk_ids=history.completed_chunk_ids,
                )
                if in_window:
                    assert chk.category == expected_cat
                    assert chk.recommended_action == expected_act
                else:
                    assert chk.category == RepetitionCategory.NONE
                    assert chk.recommended_action == RepetitionAction.ALLOW


def test_track2a_and_track2b_configs_guard_and_mock_execution(tmp_path: Path) -> None:
    """Cấu hình Track 2A (lag=6) và 2B (lag=12) tuân thủ Offline Guard, công bằng và tạo đủ tương phản."""
    mod = _load_formal_batch_module()

    cfg_2a = mod.load_batch_config(TRACK2A_CONFIG_PATH)
    cfg_2b = mod.load_batch_config(TRACK2B_CONFIG_PATH)
    assert cfg_2a["min_chunks_per_topic"] == 2
    assert cfg_2b["min_chunks_per_topic"] == 2
    assert cfg_2a["max_turns"] == 80 and cfg_2a["max_requests_per_run"] == 120 and cfg_2a["global_max_requests"] == 240
    assert cfg_2b["max_turns"] == 120 and cfg_2b["max_requests_per_run"] == 200 and cfg_2b["global_max_requests"] == 400
    assert [r["history_window"] for r in cfg_2a["runs"]] == [5, 10]
    assert [r["history_window"] for r in cfg_2b["runs"]] == [10, 20]

    for cfg_path in (TRACK2A_CONFIG_PATH, TRACK2B_CONFIG_PATH):
        with pytest.raises(ProviderConfigError, match="Offline Guard"):
            mod.execute_formal_batch(cfg_path, output_dir_override=tmp_path / f"blocked_{cfg_path.stem}")

    sum_2a = mod.execute_formal_batch(
        TRACK2A_CONFIG_PATH,
        provider_override="mock",
        output_dir_override=tmp_path / "track2a_mock",
    )
    assert sum_2a["status"] == "COMPLETED"
    assert sum_2a["comparison_compatible"] is True
    assert set(sum_2a["runs"].keys()) == {"langgraph_w5", "langgraph_w10"}

    # Xác nhận Track 2A W=5 đạt 18/18 topics đủ 2 chunks không-fallback, và W=10 dù có fallback không được đếm nhầm fallback vào coverage.
    w10_metrics_2a = json.loads(
        (Path(sum_2a["runs"]["langgraph_w10"]["run_dir"]) / "metrics.json").read_text(encoding="utf-8")
    )
    assert w10_metrics_2a["coverage"]["completed_topic_count"]["value"] == 18
    assert w10_metrics_2a["reliability"]["fallback_count"]["value"] >= 1

    sum_2b = mod.execute_formal_batch(
        TRACK2B_CONFIG_PATH,
        provider_override="mock",
        output_dir_override=tmp_path / "track2b_mock",
    )
    assert sum_2b["status"] == "COMPLETED"
    assert sum_2b["comparison_compatible"] is True
    assert sum_2b["runs"]["langgraph_w10"]["termination_reason"] == "EARLY_COMPLETION"
    assert sum_2b["runs"]["langgraph_w20"]["termination_reason"] == "MAX_CONSECUTIVE_ABORTS"
    w20_metrics_2b = json.loads(
        (Path(sum_2b["runs"]["langgraph_w20"]["run_dir"]) / "metrics.json").read_text(encoding="utf-8")
    )
    cov_2b = w20_metrics_2b["coverage"]["mandatory_topic_coverage"]
    assert 0.0 < cov_2b["value"] < 1.0
    assert len(cov_2b["metadata"]["partially_covered_topic_ids"]) >= 1
