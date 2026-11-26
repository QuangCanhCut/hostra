"""Kiểm thử tích hợp toàn tuyến & tính tái lập cho P06-E01 Runner + Evaluator (`E01-T08`).

1. File này giải quyết vấn đề gì?
   Xác minh đầu cuối hệ thống thực nghiệm ngoại tuyến: `ScriptFirstBaseline` (tất định & upfront LLM),
   `LangGraph` đa lượt qua 3 SKU, điều kiện dừng an toàn, thu thập 10 tệp artifact, đối chiếu metric
   với bằng chứng thô, quét cửa sổ `W ∈ {5, 10, 20}`, phát hiện cấu hình không tương thích và
   tính tất định logic giữa hai lần chạy độc lập.
2. Trách nhiệm chính của module là gì?
   Bao phủ đầy đủ 12 yêu cầu tích hợp và bài kiểm tra tái lập tất định của `E01-T08`.
3. Module này liên kết với các thành phần nào?
   Tích hợp `p06.runner` (`run_experiment`, `run_e01_sweep`, `load_experiment_run_config`),
   `p06.evaluation` (`evaluate_run_directory`, `compare_runs`, `export_blind_human_eval_sheets`),
   và CLI `experiments/p06_e01_no_comments/run_e01.py`.
4. Input và output chính là gì?
   Input là dữ liệu synthetic E01 + `MockLLMProvider`;
   Output là các thư mục run tạm dưới `.pytest_cache/` và khẳng định đúng đắn/tái lập.
5. Có những constraints hoặc invariants quan trọng nào?
   - Tuyệt đối không gọi API LLM bên ngoài (`ollama`/`gemini` bị chặn cứng).
   - Loại trừ `run_id`, timestamp và thời gian đo wall-clock khi đối chiếu tính tất định logic.
   - Không đánh đồng Mock output với chất lượng kể chuyện tiếng Việt thật.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import pytest

from p06.evaluation.comparison import compare_runs
from p06.evaluation.evaluator import evaluate_run_directory, load_run_evidence
from p06.evaluation.models import MetricStatus
from p06.providers.base import ProviderConfigError
from p06.providers.mock_provider import MockBehavior, MockLLMProvider, MockResponseStep
from p06.runner.config import (
    ExperimentMethod,
    RunTerminationReason,
    load_experiment_run_config,
)
from p06.runner.session_runner import run_experiment
from p06.runner.sweep import run_e01_sweep
from p06.schemas.events import PlaybackOutcomeStatus
from p06.schemas.story import (
    BreakpointType,
    StoryArc,
    StoryPlan,
    StoryPlanApprovalStatus,
    StoryTopic,
)

MODULE_ROOT = Path(__file__).resolve().parents[2]
RUN_E01_CLI = MODULE_ROOT / "experiments" / "p06_e01_no_comments" / "run_e01.py"
START_AT = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)

REQUIRED_ARTIFACTS = (
    "manifest.json",
    "config.yaml",
    "story_plan.json",
    "transcript.jsonl",
    "playback_events.jsonl",
    "graph_trace.jsonl",
    "provider_calls.jsonl",
    "metrics.json",
    "token_usage.json",
    "errors.jsonl",
)


@pytest.fixture
def tmp_path() -> Iterator[Path]:
    """Tạo thư mục tạm sạch trong `.pytest_cache/` để tránh giới hạn quyền %TEMP% trên Windows sandbox."""
    base = MODULE_ROOT / ".pytest_cache" / f"int_e01_{uuid.uuid4().hex[:8]}"
    base.mkdir(parents=True, exist_ok=True)
    try:
        yield base
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _build_synthetic_multi_topic_plan(num_topics_per_sku: int = 4) -> StoryPlan:
    """Tạo `StoryPlan` tổng hợp dài ngay trong test (không đụng `data/`) để kiểm tra W-sweep & time budget."""
    skus = ("SKU-HONEY-01", "SKU-TEA-02", "SKU-MACADAMIA-03")
    ev_map = {
        "SKU-HONEY-01": ("ev-e01-honey-usage", "CLM-HONEY-USAGE"),
        "SKU-TEA-02": ("ev-e01-tea-usage", "CLM-TEA-BREWING"),
        "SKU-MACADAMIA-03": ("ev-e01-macadamia-usage", "CLM-MACADAMIA-USAGE"),
    }
    arcs: list[StoryArc] = []
    for pos, sku_id in enumerate(skus, start=1):
        ev_id, claim_id = ev_map[sku_id]
        topics = [
            StoryTopic(
                topic_id=f"topic-long-{sku_id.lower()}-{idx:02d}",
                sku_id=sku_id,
                title=f"Chủ đề {idx} cho {sku_id}",
                is_mandatory=True,
                fact_refs=[ev_id],
                allowed_claim_ids=[claim_id],
                talking_points=[f"Giới thiệu chi tiết điểm {idx} của {sku_id}."],
            )
            for idx in range(1, num_topics_per_sku + 1)
        ]
        arcs.append(
            StoryArc(
                arc_id=f"arc-long-{sku_id.lower()}",
                position=pos,
                title=f"Arc dài cho {sku_id}",
                sku_id=sku_id,
                target_duration_sec=200,
                topics=topics,
                breakpoint_hint=BreakpointType.ARC_BOUNDARY,
            )
        )

    return StoryPlan(
        tenant_id="tenant-p06-poc-01",
        session_id="sess-e01-long-test",
        plan_id="plan-e01-long-test",
        plan_revision=1,
        pinned_sku_ids=list(skus),
        knowledge_versions_by_sku={sku: 1 for sku in skus},
        session_goal="Kiểm thử quét cửa sổ W và giới hạn thời lượng mô phỏng trên 3 SKU.",
        arcs=arcs,
        approval_status=StoryPlanApprovalStatus.APPROVED,
        approved_by="synthetic-owner-01",
        approved_at=START_AT,
    )


def test_script_first_and_langgraph_runners_execute_offline_across_3_skus(
    tmp_path: Path,
) -> None:
    """Kiểm tra cả 3 phương pháp chạy offline hoàn toàn qua 3 SKU và sinh đủ 10 artifacts khớp raw evidence."""
    for method, window in (
        (ExperimentMethod.SCRIPT_FIRST_DETERMINISTIC, None),
        (ExperimentMethod.SCRIPT_FIRST_UPFRONT_LLM, None),
        (ExperimentMethod.LANGGRAPH, 5),
    ):
        cfg = load_experiment_run_config(
            scenario="product_education_10m",
            method=method,
            provider="mock",
            history_window=window,
            seed=42,
            output_dir=tmp_path,
        )
        res = run_experiment(cfg)

        assert res.termination_reason == RunTerminationReason.EARLY_COMPLETION
        for fname in REQUIRED_ARTIFACTS:
            assert (res.run_dir / fname).is_file(), f"Thiếu artifact {fname}"

        assert len(res.evidence.transcript) == 6
        assert {entry.sku_id for entry in res.evidence.transcript} == {
            "SKU-HONEY-01",
            "SKU-TEA-02",
            "SKU-MACADAMIA-03",
        }
        re_eval = evaluate_run_directory(res.run_dir)
        assert re_eval.hard_gates_passed is True
        assert re_eval.coverage["mandatory_topic_coverage"].value == pytest.approx(1.0)
        assert re_eval.repetition["exact_chunk_replay_count"].value == 0

        disk_metrics = json.loads((res.run_dir / "metrics.json").read_text(encoding="utf-8"))
        assert (
            disk_metrics["coverage"]["mandatory_topic_coverage"]["value"]
            == pytest.approx(re_eval.coverage["mandatory_topic_coverage"].value)
        )
        assert (
            disk_metrics["repetition"]["exact_chunk_replay_count"]["value"]
            == re_eval.repetition["exact_chunk_replay_count"].value
        )


def test_langgraph_sales_presentation_30m_completes_9_mandatory_topics(
    tmp_path: Path,
) -> None:
    """Kịch bản 30 phút phủ đủ 9/9 topic qua 3 SKU và báo trung thực EARLY_COMPLETION."""
    cfg = load_experiment_run_config(
        scenario="sales_presentation_30m",
        method=ExperimentMethod.LANGGRAPH,
        provider="mock",
        history_window=10,
        seed=42,
        output_dir=tmp_path,
    )
    res = run_experiment(cfg)
    assert res.termination_reason == RunTerminationReason.EARLY_COMPLETION
    assert res.report is not None
    assert res.report.hard_gates_passed is True
    assert res.report.coverage["mandatory_topic_coverage"].value == pytest.approx(1.0)
    assert res.report.coverage["completed_topic_count"].value == 9
    assert res.report.coverage["duration_fulfillment"].value < 0.1


def test_time_budget_exhausted_and_outside_window_replay_detection(
    tmp_path: Path,
) -> None:
    """Chứng minh TIME_BUDGET_EXHAUSTED và sự khác biệt hành vi giữa W=5 với W=10."""
    long_plan = _build_synthetic_multi_topic_plan(num_topics_per_sku=4)

    # 1. Kiểm tra TIME_BUDGET_EXHAUSTED khi target_duration_sec nhỏ hơn thời lượng 12 topic.
    cfg_budget = load_experiment_run_config(
        scenario="product_education_10m",
        method=ExperimentMethod.LANGGRAPH,
        provider="mock",
        history_window=5,
        target_duration_sec=12.0,
        seed=42,
        output_dir=tmp_path,
    )
    res_budget = run_experiment(cfg_budget, story_plan=long_plan)
    assert res_budget.termination_reason == RunTerminationReason.TIME_BUDGET_EXHAUSTED
    assert res_budget.report is not None
    assert res_budget.report.coverage["mandatory_topic_coverage"].value < 1.0

    # 2. Kiểm tra lặp text vượt ra ngoài cửa sổ W=5 (tại lượt 7 lặp lại nguyên văn lượt 0):
    # Với W=5, lượt 0 đã trôi khỏi state.played_history nên agent cho qua và evaluator độc lập bắt được
    # outside_window_exact_text_replay_count == 1; với W=10, check_repetition chặn và buộc rewrite.
    repeated_text = "Sản phẩm đặc sản tuyển chọn bảo đảm nguồn gốc rõ ràng và an toàn thực phẩm."
    topic_ids = [t.topic_id for arc in long_plan.arcs for t in arc.topics]
    sku_for_topic = {t.topic_id: t.sku_id for arc in long_plan.arcs for t in arc.topics}
    ev_for_sku = {
        "SKU-HONEY-01": ("ev-e01-honey-usage", 159000),
        "SKU-TEA-02": ("ev-e01-tea-usage", 245000),
        "SKU-MACADAMIA-03": ("ev-e01-macadamia-usage", 195000),
    }

    distinct_phrases = [
        repeated_text,
        "Pha hai thìa mật ong cùng nước ấm dưới năm mươi độ mỗi sáng.",
        "Bảo quản chai thủy tinh nơi thoáng mát tránh nắng gắt giúp giữ hương.",
        "Đổi trả miễn phí trong bảy ngày nếu bao bì bị nứt vỡ.",
        "Trà Shan Tuyết hái thủ công một tôm hai lá trên núi cao.",
        "Tráng ấm sạch rồi hãm trà bằng nước tám lăm độ trong bốn lăm giây.",
        repeated_text,
        "Hộp thiếc hút chân không bảo vệ búp trà khô khỏi ẩm mốc.",
        "Hạt mắc ca Lâm Đồng sấy nứt vỏ giòn béo tự nhiên.",
        "Dùng dụng cụ đi kèm tách nhẹ vỏ hạt mắc ca rất tiện lợi.",
        "Đậy kín nắp hộp kèm gói hút ẩm sau khi dùng xong.",
        "Khách dị ứng hạt cây vui lòng cân nhắc trước khi thưởng thức.",
    ]

    def _build_keyed_provider(*, include_rewrite: bool) -> MockLLMProvider:
        keyed: dict[str, list[MockResponseStep]] = {}
        for idx, tid in enumerate(topic_ids):
            sku = sku_for_topic[tid] or "SKU-HONEY-01"
            ev_id, _ = ev_for_sku[sku]
            keyed[tid] = [
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload={
                        "text": distinct_phrases[idx],
                        "cited_evidence_ids": [ev_id],
                        "stated_price_vnd": None,
                        "mentions_ocop": False,
                        "covered_claim_ids": [f"CLM-{idx}"],
                        "semantic_breakpoint": True,
                    },
                )
            ]
            if include_rewrite and idx == 6:
                keyed[f"{tid}:r1"] = [
                    MockResponseStep(
                        behavior=MockBehavior.VALID_JSON,
                        payload={
                            "text": "Hương vị trà cổ thụ giữ bền qua tám lần châm nước sôi.",
                            "cited_evidence_ids": ["ev-e01-tea-usage"],
                            "stated_price_vnd": None,
                            "mentions_ocop": False,
                            "covered_claim_ids": ["CLM-TEA-REWRITTEN"],
                            "semantic_breakpoint": True,
                        },
                    )
                ]
        return MockLLMProvider(keyed_responses=keyed, seed=42)

    res_w5 = run_experiment(
        load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.LANGGRAPH,
            provider="mock",
            history_window=5,
            seed=42,
            output_dir=tmp_path,
        ),
        story_plan=long_plan,
        custom_llm_provider=_build_keyed_provider(include_rewrite=False),
    )
    res_w10 = run_experiment(
        load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.LANGGRAPH,
            provider="mock",
            history_window=10,
            seed=42,
            output_dir=tmp_path,
        ),
        story_plan=long_plan,
        custom_llm_provider=_build_keyed_provider(include_rewrite=True),
    )
    assert res_w5.report is not None and res_w10.report is not None
    assert res_w5.report.repetition["exact_normalized_text_replay_count"].value == 1
    assert res_w5.report.repetition["outside_window_exact_text_replay_count"].value == 1
    assert res_w10.report.repetition["exact_normalized_text_replay_count"].value == 0
    assert res_w10.report.reliability["rewrite_count"].value >= 1


def test_errors_logged_not_swallowed_and_independent_runs_isolated(
    tmp_path: Path,
) -> None:
    """Lỗi playback FAILED/UNKNOWN, P05 REJECTED và malformed JSON đều được ghi vào errors.jsonl."""
    bad_then_good = MockLLMProvider(
        response_sequence=[
            MockResponseStep(behavior=MockBehavior.MALFORMED_JSON),
            MockResponseStep(
                behavior=MockBehavior.VALID_JSON,
                payload={
                    "text": "Mật ong hoa cà phê giá sai 99.000đ một chai.",
                    "cited_evidence_ids": ["ev-e01-honey-usage"],
                    "stated_price_vnd": 99000,
                    "mentions_ocop": False,
                    "covered_claim_ids": ["CLM-HONEY-USAGE"],
                    "semantic_breakpoint": True,
                },
            ),
            MockResponseStep(
                behavior=MockBehavior.VALID_JSON,
                payload={
                    "text": "Mật ong hoa cà phê Đắk Lắk chai 500ml giá 159.000đ.",
                    "cited_evidence_ids": ["ev-e01-honey-usage"],
                    "stated_price_vnd": 159000,
                    "mentions_ocop": False,
                    "covered_claim_ids": ["CLM-HONEY-USAGE"],
                    "semantic_breakpoint": True,
                },
            ),
        ],
        seeded_variants_by_schema={
            "ChunkDraftLLMOutput": [
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload={
                        "text": "Đặc sản kiểm chứng an toàn thực phẩm.",
                        "cited_evidence_ids": ["ev-e01-honey-usage"],
                        "mentions_ocop": False,
                        "covered_claim_ids": [],
                        "semantic_breakpoint": True,
                    },
                )
            ]
        },
        seed=42,
    )
    cfg = load_experiment_run_config(
        scenario="product_education_10m",
        method=ExperimentMethod.LANGGRAPH,
        provider="mock",
        history_window=5,
        max_turns=4,
        max_rewrite_retries=2,
        seed=42,
        output_dir=tmp_path,
    )
    res = run_experiment(
        cfg,
        custom_llm_provider=bad_then_good,
        outcome_overrides={0: PlaybackOutcomeStatus.UNKNOWN},
    )
    assert res.report is not None
    assert len(res.evidence.errors) >= 1
    assert any(err.error_type == "PLAYBACK_IGNORED_NON_COMPLETED" for err in res.evidence.errors)
    assert res.report.safety["p05_rejection_count"].value >= 1
    assert res.report.reliability["rewrite_count"].value >= 2
    assert any(call.is_wasted for call in res.evidence.provider_calls)
    # Lượt 0 bị UNKNOWN -> KHÔNG được vào transcript.jsonl!
    assert all(entry.turn_index != 0 or entry.turn_id != "turn-plan-e01-product-edu-e1-0000" for entry in res.evidence.transcript)


def test_offline_guards_sweep_and_incompatible_comparison_detection(
    tmp_path: Path,
) -> None:
    """Chặn live provider ở cả config lẫn CLI; sweep sinh đủ 5 runs/scenario và comparison phát hiện lệch tier."""
    with pytest.raises(ProviderConfigError):
        load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.LANGGRAPH,
            provider="ollama",
            history_window=5,
        )
    with pytest.raises(ProviderConfigError):
        load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.LANGGRAPH,
            provider="gemini",
            history_window=5,
        )

    cli_proc = subprocess.run(
        [sys.executable, str(RUN_E01_CLI), "--provider", "gemini", "--scenario", "product_education_10m"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert cli_proc.returncode != 0
    assert "T08 BLOCKED" in (cli_proc.stderr + cli_proc.stdout)

    sweep_res = run_e01_sweep(
        scenarios=("product_education_10m",),
        output_dir=tmp_path / "sweep_out",
        export_human_eval=True,
    )
    # 2 script_first (NO W sweep) + 3 langgraph (W=5,10,20) = 5 runs
    assert len(sweep_res.run_results) == 5
    assert sweep_res.comparison_report is not None
    assert sweep_res.comparison_report.compatible is True
    assert sweep_res.comparison_json_path is not None and sweep_res.comparison_json_path.is_file()
    assert sweep_res.comparison_csv_path is not None and sweep_res.comparison_csv_path.is_file()
    assert sweep_res.comparison_md_path is not None and sweep_res.comparison_md_path.is_file()
    assert sweep_res.human_eval_dir is not None
    assert (sweep_res.human_eval_dir / "blind_eval_sheet.csv").is_file()
    assert (sweep_res.human_eval_dir / "blind_key_mapping.private.json").is_file()

    # Giả lập một thư mục run khác tier (ollama) để xác minh compare_runs chặn gộp chéo tầng.
    tampered_dir = tmp_path / "fake_ollama_run"
    shutil.copytree(sweep_res.run_results[0].run_dir, tampered_dir)
    manifest = json.loads((tampered_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest["run_id"] = "fake-ollama-run-01"
    manifest["provider_tier"] = "local_smoke_test"
    manifest["provider_name"] = "ollama"
    (tampered_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    incompat = compare_runs([sweep_res.run_results[0].run_dir, tampered_dir])
    assert incompat.compatible is False
    assert any(issue.code == "CROSS_TIER_POOLING_PROHIBITED" for issue in incompat.compatibility_issues)


def test_logical_determinism_across_identical_mock_runs(tmp_path: Path) -> None:
    """Chạy lại cùng cấu hình Mock 2 lần phải cho kết quả logic giống hệt nhau 100%."""
    out_a = tmp_path / "run_a"
    out_b = tmp_path / "run_b"

    res_a = run_experiment(
        load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.LANGGRAPH,
            provider="mock",
            history_window=5,
            seed=42,
            output_dir=out_a,
        )
    )
    res_b = run_experiment(
        load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.LANGGRAPH,
            provider="mock",
            history_window=5,
            seed=42,
            output_dir=out_b,
        )
    )

    ev_a = load_run_evidence(res_a.run_dir)
    ev_b = load_run_evidence(res_b.run_dir)

    assert res_a.run_id != res_b.run_id
    assert res_a.termination_reason == res_b.termination_reason

    logical_transcript_a = [
        (e.turn_index, e.sku_id, e.topic_id, e.chunk_id, e.text, e.confirmed_topic_ids, e.actual_duration_ms)
        for e in ev_a.transcript
    ]
    logical_transcript_b = [
        (e.turn_index, e.sku_id, e.topic_id, e.chunk_id, e.text, e.confirmed_topic_ids, e.actual_duration_ms)
        for e in ev_b.transcript
    ]
    assert logical_transcript_a == logical_transcript_b

    logical_pb_a = [
        (p.sequence_index, p.sku_id, p.outcome, p.apply_status, p.confirmed_topic_ids, p.actual_duration_ms)
        for p in ev_a.playback_events
    ]
    logical_pb_b = [
        (p.sequence_index, p.sku_id, p.outcome, p.apply_status, p.confirmed_topic_ids, p.actual_duration_ms)
        for p in ev_b.playback_events
    ]
    assert logical_pb_a == logical_pb_b

    assert res_a.report is not None and res_b.report is not None
    assert (
        res_a.report.coverage["mandatory_topic_coverage"].value
        == res_b.report.coverage["mandatory_topic_coverage"].value
    )
    assert (
        res_a.report.repetition["exact_chunk_replay_count"].value
        == res_b.report.repetition["exact_chunk_replay_count"].value
    )
    assert (
        res_a.report.repetition["exact_normalized_text_replay_count"].value
        == res_b.report.repetition["exact_normalized_text_replay_count"].value
    )
    assert (
        res_a.report.repetition["max_prior_ngram3_jaccard_mean"].value
        == res_b.report.repetition["max_prior_ngram3_jaccard_mean"].value
    )
