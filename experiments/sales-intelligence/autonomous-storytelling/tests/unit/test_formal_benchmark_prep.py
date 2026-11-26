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

import json
import shutil
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from p06.adapters.mocks import MockPlaybackAckBus
from p06.adapters.p05_knowledge_adapter import P05KnowledgeAdapter
from p06.agent.nodes._common import _compute_word_budget
from p06.baselines import BaselineScriptSource, ScriptFirstBaseline
from p06.providers import MockBehavior, MockLLMProvider, MockResponseStep
from p06.runner import (
    ExperimentMethod,
    RunTerminationReason,
    load_e01_story_plan,
    load_experiment_run_config,
    run_e01_sweep,
)
from p06.schemas import StoryCheckpoint, StoryPlan
from p06.simulation import SimulatedPlaybackHarness, VirtualClock, compute_chunk_word_budget

P06_ROOT = Path(__file__).resolve().parents[2]
EXT_SKUS_PATH = P06_ROOT / "data" / "products" / "e01_ext_v1_verified_skus.json"
EXT_PLANS_PATH = P06_ROOT / "data" / "story_plans" / "e01_ext_v1_story_plans.json"
FORMAL_SKUS_PATH = P06_ROOT / "data" / "products" / "e01_formal_v1_verified_skus.json"
FORMAL_PLANS_PATH = P06_ROOT / "data" / "story_plans" / "e01_formal_v1_story_plans.json"
PILOT_V2_HE_DIR = P06_ROOT / "runs" / "P06-E01" / "gemini_3.5_flash_lite_pilot_v2" / "human_eval"
START_AT = datetime(2026, 11, 27, 0, 0, 0, tzinfo=timezone.utc)


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
        assert run.report.coverage["mandatory_topic_coverage"].value == pytest.approx(1.0)
        assert len(run.evidence.transcript) >= 72
        if run.manifest.get("history_window") == 20:
            # Ở lag=12 < W=20, lượt thứ 2 của cùng topic (chỉ có 1 claim_id) kích hoạt REPEATED_FACTS
            # và cạn 2 fallback/SKU -> dừng an toàn MAX_CONSECUTIVE_ABORTS, phân tách rõ W=20 khỏi W=5/10.
            assert run.termination_reason == RunTerminationReason.MAX_CONSECUTIVE_ABORTS
        else:
            assert run.termination_reason == RunTerminationReason.EARLY_COMPLETION


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
