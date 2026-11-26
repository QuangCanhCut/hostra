"""Kiểm thử đơn vị toàn diện cho 5 nhóm metric, evaluator, comparison và human_eval (`p06.evaluation`).

1. File này giải quyết vấn đề gì?
   Xác minh tính đúng đắn toán học (tính tay từng con số) và các bất biến liêm chính dữ liệu
   của hệ thống đánh giá P06 (`coverage`, `repetition`, `safety`, `reliability`, `performance`,
   `evaluator`, `comparison`, `human_eval`).
2. Trách nhiệm chính của module là gì?
   Kiểm thử mọi ca biên: transcript rỗng/1 lượt, mẫu số 0, ACK trùng lặp, ứng viên bị từ chối,
   playback `FAILED`/`UNKNOWN`, thiếu telemetry token, `target_duration_sec <= 0`, lặp ngoài `W`,
   so sánh chéo tầng bị cấm, và phiếu chấm mù không rò rỉ metadata hay điểm giả.
3. Module này liên kết với các thành phần nào?
   Kiểm thử trực tiếp `p06.evaluation` (`metrics`, `evaluator`, `comparison`, `human_eval`, `models`).
4. Input và output chính là gì?
   Input là các fixture `RunEvidence` và thư mục run tạm (`tmp_path`);
   Output là khẳng định trạng thái, giá trị số chính xác và Hard Gates.
5. Có những constraints hoặc invariants quan trọng nào?
   - Tuyệt đối không nới lỏng bất kỳ kiểm định nào về `NOT_EVALUATED` / `value=None` khi thiếu dữ liệu.
"""

from __future__ import annotations

import csv
import json
import shutil
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

_MODULE_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def tmp_path() -> Iterator[Path]:
    """Cấp thư mục tạm cô lập trong `.pytest_cache` và dọn sạch sau mỗi test."""
    base_dir = _MODULE_ROOT / ".pytest_cache" / f"eval_tmp_{uuid.uuid4().hex[:10]}"
    base_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield base_dir
    finally:
        shutil.rmtree(base_dir, ignore_errors=True)

from p06.evaluation import (
    ErrorRecord,
    GoldFactualLabel,
    GraphTraceRecord,
    MetricProvenance,
    MetricStatus,
    PlaybackEventRecord,
    ProviderCallRecord,
    RunEvidence,
    TranscriptEntry,
    compare_runs,
    compute_coverage_metrics,
    compute_percentile,
    compute_performance_metrics,
    compute_reliability_metrics,
    compute_repetition_metrics,
    compute_safety_metrics,
    evaluate_run,
    evaluate_run_directory,
    export_blind_human_eval_sheets,
    export_comparison_csv,
    export_comparison_json,
    export_comparison_markdown,
    load_run_evidence,
)
from p06.schemas.story import StoryArc, StoryPlan, StoryPlanApprovalStatus, StoryTopic


def _make_story_plan(
    *,
    plan_id: str = "plan-e01-test",
    plan_revision: int = 1,
    mandatory_topics: tuple[tuple[str, bool, tuple[str, ...]], ...] = (
        ("top-1", True, ("clm-1", "clm-2")),
        ("top-2", True, ("clm-3",)),
        ("top-opt", False, ()),
    ),
) -> StoryPlan:
    """Tạo `StoryPlan` chuẩn phục vụ kiểm thử đơn vị."""
    topics = [
        StoryTopic(
            topic_id=tid,
            title=f"Chủ đề {tid}",
            sku_id="SKU-HONEY-01",
            is_mandatory=is_mand,
            fact_refs=["ev-e01-honey-origin"],
            allowed_claim_ids=list(claims),
            talking_points=["Điểm nhấn sản phẩm"],
        )
        for tid, is_mand, claims in mandatory_topics
    ]
    return StoryPlan(
        plan_id=plan_id,
        tenant_id="tenant-p06-poc-01",
        session_id="sess-e01-test",
        plan_revision=plan_revision,
        approval_status=StoryPlanApprovalStatus.APPROVED,
        approved_by="owner-01",
        approved_at=datetime(2026, 11, 26, 0, 0, 0, tzinfo=timezone.utc),
        session_goal="Giới thiệu mật ong hoa cà phê Đắk Lắk",
        pinned_sku_ids=["SKU-HONEY-01", "SKU-TEA-02"],
        arcs=[
            StoryArc(
                arc_id="arc-1",
                position=1,
                title="Arc mật ong",
                sku_id="SKU-HONEY-01",
                target_duration_sec=300,
                topics=topics,
            )
        ],
    )


def _base_manifest(**overrides: Any) -> dict[str, Any]:
    """Tạo manifest mặc định hợp lệ cho các ca kiểm thử."""
    data: dict[str, Any] = {
        "run_id": "run-001",
        "experiment_id": "P06-E01",
        "method": "langgraph_structured_story",
        "scenario": "e01_10m_no_comments",
        "provider_tier": "formal_experiment",
        "provider_name": "gemini",
        "model_id": "gemini-2.5-flash",
        "history_window": 5,
        "termination_reason": "TARGET_DURATION_REACHED",
        "dataset_sha256": "abc123",
        "contract_version": "p06-mock-v0.1",
        "target_duration_sec": 100.0,
        "simulated_elapsed_sec": 30.0,
        "planning_latency_ms": 120.0,
        "upfront_script_generation_latency_ms": 0.0,
        "total_measured_processing_ms": 450.0,
    }
    data.update(overrides)
    return data


def _write_run_dir(
    root: Path,
    evidence: RunEvidence,
) -> Path:
    """Ghi một `RunEvidence` ra thư mục chuẩn `manifest.json` + `story_plan.json` + `.jsonl`."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(
        json.dumps(evidence.manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (root / "story_plan.json").write_text(
        evidence.story_plan.model_dump_json(indent=2), encoding="utf-8"
    )
    for filename, items in (
        ("transcript.jsonl", evidence.transcript),
        ("playback_events.jsonl", evidence.playback_events),
        ("graph_trace.jsonl", evidence.graph_traces),
        ("provider_calls.jsonl", evidence.provider_calls),
        ("errors.jsonl", evidence.errors),
    ):
        lines = [item.model_dump_json() for item in items]
        (root / filename).write_text(
            ("\n".join(lines) + "\n") if lines else "", encoding="utf-8"
        )
    return root


class TestPercentileHelper:
    """Kiểm thử hàm nội suy tuyến tính `compute_percentile()`."""

    def test_empty_single_and_interpolated_values(self) -> None:
        assert compute_percentile([], 0.50) is None
        assert compute_percentile([42.0], 0.95) == pytest.approx(42.0)
        assert compute_percentile([40.0, 10.0, 30.0, 20.0], 0.50) == pytest.approx(25.0)
        assert compute_percentile([10.0, 20.0, 30.0, 40.0], 0.95) == pytest.approx(38.5)

    def test_invalid_q_raises(self) -> None:
        with pytest.raises(ValueError):
            compute_percentile([1.0, 2.0], -0.1)
        with pytest.raises(ValueError):
            compute_percentile([1.0, 2.0], 1.1)
        with pytest.raises(ValueError):
            compute_percentile([1.0, 2.0], True)  # type: ignore[arg-type]


class TestCoverageMetrics:
    """Kiểm thử trục Coverage: tách proposed/verified/completed, khử trùng ACK và các ca biên."""

    def test_coverage_separates_states_deduplicates_acks_and_excludes_fallbacks(self) -> None:
        plan = _make_story_plan()
        evidence = RunEvidence(
            manifest=_base_manifest(started_at_utc="2026-11-26T10:00:00Z"),
            story_plan=plan,
            target_duration_sec=20.0,
            simulated_elapsed_sec=18.0,
            graph_traces=(
                GraphTraceRecord(
                    turn_index=0,
                    turn_id="turn-1",
                    method="langgraph_structured_story",
                    active_sku_id="SKU-HONEY-01",
                    turn_outcome="VERIFIED_READY",
                    proposed_topic_ids=("top-1", "top-2"),
                    verified_topic_ids=("top-1", "top-2"),
                ),
                GraphTraceRecord(
                    turn_index=1,
                    turn_id="turn-2-failed",
                    method="langgraph_structured_story",
                    active_sku_id="SKU-HONEY-01",
                    turn_outcome="VERIFIED_READY",
                    proposed_topic_ids=("top-2",),
                    verified_topic_ids=("top-2",),
                ),
                GraphTraceRecord(
                    turn_index=2,
                    turn_id="turn-3-fb",
                    method="langgraph_structured_story",
                    active_sku_id="SKU-HONEY-01",
                    turn_outcome="FALLBACK_PREAPPROVED",
                    used_fallback=True,
                    proposed_topic_ids=("top-2",),
                    verified_topic_ids=(),
                ),
            ),
            playback_events=(
                PlaybackEventRecord(
                    sequence_index=0,
                    turn_id="turn-1",
                    candidate_id="cand-1",
                    chunk_id="chk-1",
                    sku_id="SKU-HONEY-01",
                    outcome="COMPLETED",
                    apply_status="APPLIED",
                    applied=True,
                    playback_event_id="ack-1",
                    actual_duration_ms=6000,
                    confirmed_topic_ids=("top-1",),
                    occurred_at_utc="2026-11-26T10:00:06Z",
                ),
                # ACK trùng playback_event_id phải bị bỏ qua
                PlaybackEventRecord(
                    sequence_index=1,
                    turn_id="turn-1",
                    candidate_id="cand-1",
                    chunk_id="chk-1",
                    sku_id="SKU-HONEY-01",
                    outcome="COMPLETED",
                    apply_status="APPLIED",
                    applied=True,
                    playback_event_id="ack-1",
                    actual_duration_ms=6000,
                    confirmed_topic_ids=("top-1",),
                    occurred_at_utc="2026-11-26T10:00:06Z",
                ),
                # Sự kiện FAILED và unapplied không bao giờ được tính
                PlaybackEventRecord(
                    sequence_index=2,
                    turn_id="turn-2-failed",
                    candidate_id="cand-2",
                    chunk_id="chk-2",
                    sku_id="SKU-HONEY-01",
                    outcome="FAILED",
                    apply_status="REJECTED_NON_COMPLETED",
                    applied=False,
                    playback_event_id="ack-2",
                    actual_duration_ms=5000,
                    confirmed_topic_ids=("top-2",),
                ),
                # Fallback đã phát: cộng duration nhưng KHÔNG tính topic top-2 vào coverage
                PlaybackEventRecord(
                    sequence_index=3,
                    turn_id="turn-3-fb",
                    candidate_id="cand-fb",
                    chunk_id="chk-fb",
                    sku_id="SKU-HONEY-01",
                    outcome="COMPLETED",
                    apply_status="APPLIED",
                    applied=True,
                    playback_event_id="ack-3",
                    actual_duration_ms=4000,
                    confirmed_topic_ids=("top-2",),
                    occurred_at_utc="2026-11-26T10:00:10Z",
                ),
            ),
            transcript=(
                TranscriptEntry(
                    turn_index=0,
                    turn_id="turn-1",
                    sku_id="SKU-HONEY-01",
                    topic_id="top-1",
                    chunk_id="chk-1",
                    candidate_id="cand-1",
                    origin="PROACTIVE_STORY",
                    intent="origin_story",
                    text="Mật ong hoa cà phê Cư M'gar Đắk Lắk nguyên chất.",
                    covered_claim_ids=("clm-1",),
                    confirmed_topic_ids=("top-1",),
                    actual_duration_ms=6000,
                    playback_event_id="ack-1",
                    occurred_at_utc="2026-11-26T10:00:06Z",
                    gate_decision_id="p05-allow-1",
                ),
                TranscriptEntry(
                    turn_index=1,
                    turn_id="turn-3-fb",
                    sku_id="SKU-HONEY-01",
                    chunk_id="chk-fb",
                    candidate_id="cand-fb",
                    origin="PREAPPROVED_FALLBACK",
                    intent="safe_fallback",
                    text="Sản phẩm mật ong hoa cà phê 500ml giá 159.000đ.",
                    covered_claim_ids=("clm-3",),
                    confirmed_topic_ids=("top-2",),
                    actual_duration_ms=4000,
                    playback_event_id="ack-3",
                    occurred_at_utc="2026-11-26T10:00:10Z",
                    is_fallback=True,
                    gate_decision_id="p05-allow-fb",
                ),
            ),
        )

        metrics = compute_coverage_metrics(evidence)
        assert metrics["planned_mandatory_topic_count"].value == 2
        assert metrics["proposed_topic_count"].value == 2
        assert metrics["verified_topic_count"].value == 2
        assert metrics["completed_topic_count"].value == 1
        assert metrics["mandatory_topic_coverage"].value == pytest.approx(0.5)
        assert metrics["remaining_mandatory_topics"].value == 1
        assert metrics["remaining_mandatory_topics"].metadata["remaining_topic_ids"] == ["top-2"]
        # clm-1 covered trên 3 allowed_claim_ids (fallback clm-3 bị loại) -> 1/3
        assert metrics["declared_verified_claim_coverage"].value == pytest.approx(1.0 / 3.0)
        assert any(
            "semantic entailment" in note.lower()
            for note in metrics["declared_verified_claim_coverage"].limitations
        )
        assert metrics["human_assessed_fact_coverage"].status == MetricStatus.NOT_EVALUATED
        assert metrics["human_assessed_fact_coverage"].value is None
        # 6.0s + 4.0s = 10.0s trên target 20.0s
        assert metrics["simulated_played_duration_sec"].value == pytest.approx(10.0)
        assert metrics["duration_fulfillment"].value == pytest.approx(0.5)
        assert metrics["raw_duration_ratio"].value == pytest.approx(0.5)
        assert metrics["simulated_elapsed_sec"].value == pytest.approx(18.0)
        assert metrics["simulated_idle_sec"].value == pytest.approx(8.0)
        # top-2 chưa hoàn tất -> time_to_complete_mandatory_topics_sec = NOT_EVALUATED
        assert metrics["time_to_complete_mandatory_topics_sec"].status == MetricStatus.NOT_EVALUATED
        assert metrics["time_to_complete_mandatory_topics_sec"].value is None

    def test_coverage_zero_denominators_invalid_duration_and_full_completion_time(self) -> None:
        plan_no_mand = _make_story_plan(
            mandatory_topics=(("top-opt", False, ()),),
        )
        ev_invalid = RunEvidence(
            manifest=_base_manifest(),
            story_plan=plan_no_mand,
            target_duration_sec=0.0,
            simulated_elapsed_sec=0.0,
        )
        m_invalid = compute_coverage_metrics(ev_invalid)
        assert m_invalid["mandatory_topic_coverage"].status == MetricStatus.NOT_EVALUATED
        assert m_invalid["mandatory_topic_coverage"].value is None
        assert m_invalid["declared_verified_claim_coverage"].status == MetricStatus.NOT_EVALUATED
        assert m_invalid["declared_verified_claim_coverage"].value is None
        assert m_invalid["duration_fulfillment"].status == MetricStatus.INVALID
        assert m_invalid["duration_fulfillment"].value is None
        assert m_invalid["raw_duration_ratio"].status == MetricStatus.INVALID
        assert m_invalid["raw_duration_ratio"].value is None

        # Trường hợp hoàn tất toàn bộ mandatory topics
        plan_full = _make_story_plan(
            mandatory_topics=(
                ("top-1", True, ("clm-1",)),
                ("top-2", True, ("clm-2",)),
            )
        )
        ev_full = RunEvidence(
            manifest=_base_manifest(),
            story_plan=plan_full,
            target_duration_sec=10.0,
            simulated_elapsed_sec=15.0,
            playback_events=(
                PlaybackEventRecord(
                    sequence_index=0,
                    turn_id="t1",
                    sku_id="SKU-HONEY-01",
                    outcome="COMPLETED",
                    apply_status="APPLIED",
                    applied=True,
                    playback_event_id="p1",
                    actual_duration_ms=7000,
                    confirmed_topic_ids=("top-1",),
                ),
                PlaybackEventRecord(
                    sequence_index=1,
                    turn_id="t2",
                    sku_id="SKU-HONEY-01",
                    outcome="COMPLETED",
                    apply_status="APPLIED",
                    applied=True,
                    playback_event_id="p2",
                    actual_duration_ms=8000,
                    confirmed_topic_ids=("top-2",),
                ),
            ),
        )
        m_full = compute_coverage_metrics(ev_full)
        assert m_full["mandatory_topic_coverage"].value == pytest.approx(1.0)
        assert m_full["duration_fulfillment"].value == pytest.approx(1.0)
        assert m_full["raw_duration_ratio"].value == pytest.approx(1.5)
        assert m_full["time_to_complete_mandatory_topics_sec"].status == MetricStatus.COMPUTED
        assert m_full["time_to_complete_mandatory_topics_sec"].value == pytest.approx(15.0)

    def test_time_to_complete_ignores_wall_clock_and_uses_virtual_clock_start(self) -> None:
        """Hồi quy BUG-B: Tuyệt đối không lấy occurred_at_utc (VirtualClock) trừ started_at_utc (wall-clock)."""
        plan_full = _make_story_plan(
            mandatory_topics=(
                ("top-1", True, ("clm-1",)),
                ("top-2", True, ("clm-2",)),
            )
        )
        ev = RunEvidence(
            manifest=_base_manifest(
                started_at_utc="2026-11-26T08:00:00Z",
                simulator_assumptions={"virtual_clock_start_utc": "2026-11-26T12:00:00Z"},
            ),
            story_plan=plan_full,
            target_duration_sec=600.0,
            simulated_elapsed_sec=12.5,
            playback_events=(
                PlaybackEventRecord(
                    sequence_index=0,
                    turn_id="t1",
                    sku_id="SKU-HONEY-01",
                    outcome="COMPLETED",
                    apply_status="APPLIED",
                    applied=True,
                    playback_event_id="p1",
                    actual_duration_ms=5500,
                    confirmed_topic_ids=("top-1",),
                    occurred_at_utc="2026-11-26T12:00:05.500000+00:00",
                ),
                PlaybackEventRecord(
                    sequence_index=1,
                    turn_id="t2",
                    sku_id="SKU-HONEY-01",
                    outcome="COMPLETED",
                    apply_status="APPLIED",
                    applied=True,
                    playback_event_id="p2",
                    actual_duration_ms=7000,
                    confirmed_topic_ids=("top-2",),
                    occurred_at_utc="2026-11-26T12:00:12.500000+00:00",
                ),
            ),
        )
        m = compute_coverage_metrics(ev)
        # 12:00:12.500 - 12:00:00.000 = 12.5s (KHÔNG phải 14412.5s do trừ 08:00:00Z)
        assert m["time_to_complete_mandatory_topics_sec"].value == pytest.approx(12.5)
        assert m["time_to_complete_mandatory_topics_sec"].metadata["time_basis"] == "virtual_clock"


class TestRepetitionMetrics:
    """Kiểm thử trục Repetition: câu đơn/rỗng, lặp nguyên văn, ngoài cửa sổ W và tiếp nối hợp lệ."""

    def test_empty_and_single_turn_transcript_edge_cases(self) -> None:
        plan = _make_story_plan()
        ev_empty = RunEvidence(manifest=_base_manifest(history_window=None), story_plan=plan)
        m_empty = compute_repetition_metrics(ev_empty)
        assert m_empty["exact_chunk_replay_count"].value == 0
        assert m_empty["exact_normalized_text_replay_count"].value == 0
        assert m_empty["outside_window_exact_text_replay_count"].status == MetricStatus.NOT_APPLICABLE
        assert m_empty["max_prior_word_jaccard_mean"].status == MetricStatus.NOT_EVALUATED
        assert m_empty["distinct_1"].status == MetricStatus.NOT_EVALUATED
        assert m_empty["human_unnecessary_semantic_repetition"].status == MetricStatus.NOT_EVALUATED
        assert m_empty["human_unnecessary_semantic_repetition"].value is None

    def test_exact_replay_outside_window_and_hand_calculated_jaccard(self) -> None:
        plan = _make_story_plan()
        entries = (
            TranscriptEntry(
                turn_index=0,
                turn_id="t0",
                sku_id="SKU-HONEY-01",
                chunk_id="c1",
                candidate_id="cand-0",
                origin="PROACTIVE_STORY",
                intent="origin",
                text="Mật ong hoa cà phê Đắk Lắk nguyên chất.",
                covered_claim_ids=("clm-1",),
                actual_duration_ms=4000,
                playback_event_id="ack-0",
                occurred_at_utc="2026-11-26T10:00:04Z",
                gate_decision_id="g0",
            ),
            TranscriptEntry(
                turn_index=1,
                turn_id="t1",
                sku_id="SKU-HONEY-01",
                chunk_id="c2",
                candidate_id="cand-1",
                origin="PROACTIVE_STORY",
                intent="usage",
                text="Pha hai thìa với nước ấm mỗi sáng sớm.",
                covered_claim_ids=("clm-2",),
                actual_duration_ms=4000,
                playback_event_id="ack-1",
                occurred_at_utc="2026-11-26T10:00:08Z",
                gate_decision_id="g1",
            ),
            TranscriptEntry(
                turn_index=2,
                turn_id="t2",
                sku_id="SKU-HONEY-01",
                chunk_id="c3",
                candidate_id="cand-2",
                origin="PROACTIVE_STORY",
                intent="storage",
                text="Bảo quản nơi khô thoáng tránh ánh nắng.",
                covered_claim_ids=("clm-3",),
                actual_duration_ms=4000,
                playback_event_id="ack-2",
                occurred_at_utc="2026-11-26T10:00:12Z",
                gate_decision_id="g2",
            ),
            # Lặp nguyên văn chuẩn hóa của lượt 0 (cách 3 lượt, ngoài history_window=2) + trùng chunk c1
            TranscriptEntry(
                turn_index=3,
                turn_id="t3",
                sku_id="SKU-HONEY-01",
                chunk_id="c1",
                candidate_id="cand-3",
                origin="PROACTIVE_STORY",
                intent="origin",
                text="  Mật ong hoa cà phê Đắk Lắk nguyên chất! ",
                covered_claim_ids=("clm-1",),
                actual_duration_ms=4000,
                playback_event_id="ack-3",
                occurred_at_utc="2026-11-26T10:00:16Z",
                gate_decision_id="g3",
            ),
        )
        ev = RunEvidence(
            manifest=_base_manifest(history_window=2),
            story_plan=plan,
            transcript=entries,
        )
        m = compute_repetition_metrics(ev, lookback_windows=(2, 5))
        assert m["exact_chunk_replay_count"].value == 1
        assert m["exact_normalized_text_replay_count"].value == 1
        assert m["outside_window_exact_text_replay_count"].value == 1
        # Turn 1 vs 0: 0.0; Turn 2 vs {0,1}: 0.0; Turn 3 vs {0,1,2}: 1.0 -> mean = 1/3, max = 1.0
        assert m["max_prior_word_jaccard_mean"].value == pytest.approx(1.0 / 3.0)
        assert m["max_prior_word_jaccard_max"].value == pytest.approx(1.0)
        assert m["max_prior_ngram3_jaccard_mean"].value == pytest.approx(1.0 / 3.0)
        assert m["lexical_repetition_rate"].value == pytest.approx(1.0 / 3.0)
        # Với lookback_window=2: turn 3 chỉ nhìn lại [1, 2], không thấy turn 0 -> 0.0
        assert m["windowed_ngram3_jaccard_mean_w2"].value == pytest.approx(0.0)
        # Với lookback_window=5: turn 3 nhìn thấy turn 0 -> mean = 1/3
        assert m["windowed_ngram3_jaccard_mean_w5"].value == pytest.approx(1.0 / 3.0)
        # Turn 1 (clm-2), Turn 2 (clm-3) không trùng; Turn 3 (clm-1) trùng Turn 0 -> 1/3
        assert m["claim_overlap_rate"].value == pytest.approx(1.0 / 3.0)
        assert m["distinct_1"].status == MetricStatus.COMPUTED
        assert 0.0 < m["distinct_1"].value < 1.0

    def test_legitimate_continuation_has_zero_repetition(self) -> None:
        plan = _make_story_plan()
        entries = (
            TranscriptEntry(
                turn_index=0,
                turn_id="t0",
                sku_id="SKU-HONEY-01",
                topic_id="top-1",
                chunk_id="c1",
                candidate_id="cand-0",
                origin="PROACTIVE_STORY",
                intent="origin",
                text="Khai thác chính vụ tại Cư Mgar Đắk Lắk.",
                covered_claim_ids=("clm-1",),
                actual_duration_ms=4000,
                playback_event_id="ack-0",
                occurred_at_utc="2026-11-26T10:00:04Z",
                gate_decision_id="g0",
            ),
            TranscriptEntry(
                turn_index=1,
                turn_id="t1",
                sku_id="SKU-HONEY-01",
                topic_id="top-1",
                chunk_id="c2",
                candidate_id="cand-1",
                origin="PROACTIVE_STORY",
                intent="pricing",
                text="Chai thủy tinh giá niêm yết một trăm năm mươi chín nghìn.",
                covered_claim_ids=("clm-2",),
                actual_duration_ms=4000,
                playback_event_id="ack-1",
                occurred_at_utc="2026-11-26T10:00:08Z",
                gate_decision_id="g1",
            ),
        )
        ev = RunEvidence(manifest=_base_manifest(history_window=5), story_plan=plan, transcript=entries)
        m = compute_repetition_metrics(ev)
        assert m["exact_chunk_replay_count"].value == 0
        assert m["exact_normalized_text_replay_count"].value == 0
        assert m["lexical_repetition_rate"].value == pytest.approx(0.0)
        assert m["claim_overlap_rate"].value == pytest.approx(0.0)


class TestSafetyAndReliabilityMetrics:
    """Kiểm thử trục Safety và Reliability cùng Hard Gates."""

    def test_safety_without_and_with_gold_labels(self) -> None:
        plan = _make_story_plan()
        ev = RunEvidence(
            manifest=_base_manifest(),
            story_plan=plan,
            graph_traces=(
                GraphTraceRecord(
                    turn_index=0,
                    turn_id="t0",
                    method="langgraph_structured_story",
                    active_sku_id="SKU-HONEY-01",
                    turn_outcome="VERIFIED_READY",
                    retries_used=1,
                    max_retries=2,
                    p05_decisions=(
                        {"status": "REJECTED", "reasons": ["PRICE_MISMATCH"]},
                        {"status": "VERIFIED", "reasons": []},
                    ),
                ),
            ),
            transcript=(
                TranscriptEntry(
                    turn_index=0,
                    turn_id="t0",
                    sku_id="SKU-HONEY-01",
                    chunk_id="c1",
                    candidate_id="cand-0",
                    origin="PROACTIVE_STORY",
                    intent="origin",
                    text="Nội dung bị lọt chưa verified.",
                    actual_duration_ms=4000,
                    playback_event_id="ack-0",
                    occurred_at_utc="2026-11-26T10:00:04Z",
                    verification_status="DRAFT",
                    gate_decision_id=None,
                ),
            ),
        )

        m_no_gold = compute_safety_metrics(ev, gold_labels=None)
        assert m_no_gold["p05_rejection_count"].value == 1
        assert m_no_gold["p05_rejection_rate"].value == pytest.approx(0.5)
        assert m_no_gold["p05_rejection_reason_distribution"].value == {"PRICE_MISMATCH": 1}
        assert m_no_gold["invalid_candidate_playback_count"].value == 1
        for k in (
            "unsupported_claim_rate",
            "verifier_false_accept_count",
            "verifier_false_reject_count",
            "verifier_precision",
            "verifier_recall",
        ):
            assert m_no_gold[k].status == MetricStatus.NOT_EVALUATED
            assert m_no_gold[k].value is None

        labels = (
            GoldFactualLabel(
                candidate_id="g1",
                text="Sai giá bằng số",
                verifier_decision="BLOCK",
                expected_factual_valid=False,
                has_unsupported_claim=True,
            ),
            GoldFactualLabel(
                candidate_id="g2",
                text="Sai giá bằng chữ lọt qua P05",
                verifier_decision="ALLOW",
                expected_factual_valid=False,
                has_unsupported_claim=True,
            ),
            GoldFactualLabel(
                candidate_id="g3",
                text="Câu đúng bị chặn nhầm",
                verifier_decision="BLOCK",
                expected_factual_valid=True,
                has_unsupported_claim=False,
            ),
            GoldFactualLabel(
                candidate_id="g4",
                text="Câu đúng được duyệt",
                verifier_decision="ALLOW",
                expected_factual_valid=True,
                has_unsupported_claim=False,
            ),
        )
        m_gold = compute_safety_metrics(ev, gold_labels=labels)
        assert m_gold["verifier_false_accept_count"].value == 1
        assert m_gold["verifier_false_reject_count"].value == 1
        assert m_gold["verifier_precision"].value == pytest.approx(0.5)
        assert m_gold["verifier_recall"].value == pytest.approx(0.5)
        assert m_gold["unsupported_claim_rate"].value == pytest.approx(0.5)

    def test_reliability_metrics_and_budget_violation(self) -> None:
        plan = _make_story_plan()
        ev = RunEvidence(
            manifest=_base_manifest(termination_reason="MAX_TURNS_REACHED"),
            story_plan=plan,
            graph_traces=(
                GraphTraceRecord(
                    turn_index=0,
                    turn_id="t0",
                    method="langgraph_structured_story",
                    active_sku_id="SKU-HONEY-01",
                    turn_outcome="VERIFIED_READY",
                    retries_used=0,
                    max_retries=2,
                    draft_attempts=({"attempt": 0},),
                ),
                GraphTraceRecord(
                    turn_index=1,
                    turn_id="t1",
                    method="langgraph_structured_story",
                    active_sku_id="SKU-HONEY-01",
                    turn_outcome="FALLBACK_PREAPPROVED",
                    retries_used=3,
                    max_retries=2,
                    used_fallback=True,
                    draft_attempts=({"attempt": 0}, {"attempt": 1}, {"attempt": 2}, {"attempt": 3}),
                ),
                GraphTraceRecord(
                    turn_index=2,
                    turn_id="t2",
                    method="langgraph_structured_story",
                    active_sku_id="SKU-HONEY-01",
                    turn_outcome="SAFE_ABORT_NO_CANDIDATE",
                    retries_used=1,
                    max_retries=2,
                    draft_attempts=({"attempt": 0}, {"attempt": 1}),
                ),
            ),
            provider_calls=(
                ProviderCallRecord(
                    call_index=0,
                    provider_name="gemini",
                    model_id="gemini-2.5-flash",
                    tier="formal_experiment",
                    latency_ms=100.0,
                    is_simulated_metric=False,
                    input_tokens=10,
                    output_tokens=5,
                    token_usage_source="MEASURED",
                    finish_reason="STOP",
                    raw_response_valid=False,
                    error_type="SchemaValidationError",
                ),
            ),
            errors=(
                ErrorRecord(
                    error_index=0,
                    stage="verify_p05",
                    error_type="PRICE_MISMATCH",
                    message="Sai giá",
                    is_retryable=True,
                ),
                ErrorRecord(
                    error_index=1,
                    stage="verify_p05",
                    error_type="STALE_RIGHTS_VERSION",
                    message="Quyền cũ",
                    is_retryable=False,
                ),
            ),
        )
        m = compute_reliability_metrics(ev)
        assert m["generation_attempts"].value == 7
        assert m["successful_candidate_count"].value == 1
        assert m["rewrite_count"].value == 4
        assert m["rewrite_rate"].value == pytest.approx(2.0 / 3.0)
        assert m["attempts_per_turn_mean"].value == pytest.approx(7.0 / 3.0)
        assert m["attempts_per_turn_p50"].value == pytest.approx(2.0)
        assert m["attempts_per_turn_max"].value == pytest.approx(4.0)
        assert m["retry_budget_violations"].value == 1
        assert m["fallback_count"].value == 1
        assert m["fallback_rate"].value == pytest.approx(1.0 / 3.0)
        assert m["safe_abort_count"].value == 1
        assert m["safe_abort_rate"].value == pytest.approx(1.0 / 3.0)
        assert m["retryable_failure_distribution"].value == {"PRICE_MISMATCH": 1}
        assert m["non_retryable_failure_distribution"].value == {"STALE_RIGHTS_VERSION": 1}
        assert m["provider_error_distribution"].value == {"SchemaValidationError": 1}
        assert m["termination_reason"].value == "MAX_TURNS_REACHED"

    def test_clean_sku_termination_boundary_excluded_from_safe_aborts_and_latency(self) -> None:
        """Hồi quy BUG-C & NEW-05: Lượt biên chuyển SKU sạch không tính vào safe_abort hay làm méo p50/p95."""
        plan = _make_story_plan()
        ev = RunEvidence(
            manifest=_base_manifest(termination_reason="EARLY_COMPLETION"),
            story_plan=plan,
            graph_traces=(
                GraphTraceRecord(
                    turn_index=0,
                    turn_id="t0",
                    method="langgraph_structured_story",
                    active_sku_id="SKU-HONEY-01",
                    node_trace=("load_context", "plan_chunk", "generate_chunk", "verify_p05", "finalize_candidate"),
                    turn_outcome="VERIFIED_READY",
                    invocation_latency_ms=10.0,
                    draft_attempts=({"attempt": 0},),
                ),
                # Lượt kết thúc biên SKU-HONEY-01 (không gọi LLM, không lỗi) -> phải bị loại khỏi mẫu số
                GraphTraceRecord(
                    turn_index=1,
                    turn_id="t1-boundary",
                    method="langgraph_structured_story",
                    active_sku_id="SKU-HONEY-01",
                    node_trace=("load_context", "plan_chunk", "finalize_candidate"),
                    turn_outcome="SAFE_ABORT_NO_CANDIDATE",
                    should_terminate=True,
                    termination_reason="ALL_ELIGIBLE_TOPICS_COMPLETED",
                    invocation_latency_ms=0.2,
                ),
                # Một lượt SAFE_ABORT thật (qua safe_fallback) vẫn PHẢI bị đếm
                GraphTraceRecord(
                    turn_index=2,
                    turn_id="t2-real-abort",
                    method="langgraph_structured_story",
                    active_sku_id="SKU-TEA-02",
                    node_trace=("load_context", "plan_chunk", "generate_chunk", "safe_fallback", "finalize_candidate"),
                    turn_outcome="SAFE_ABORT_NO_CANDIDATE",
                    invocation_latency_ms=30.0,
                    draft_attempts=({"attempt": 0},),
                ),
            ),
        )
        rel = compute_reliability_metrics(ev)
        perf = compute_performance_metrics(ev)
        assert rel["safe_abort_count"].value == 1
        assert rel["safe_abort_count"].metadata["termination_boundary_turns_excluded"] == 1
        assert rel["safe_abort_rate"].value == pytest.approx(0.5)
        assert perf["invocation_latency_p50_ms"].value == pytest.approx(20.0)
        assert perf["invocation_latency_p50_ms"].metadata["termination_boundary_turns_excluded"] == 1

        # NEW-05: script_first_deterministic không có LLM generation attempts -> NOT_APPLICABLE
        ev_det = RunEvidence(
            manifest=_base_manifest(method="script_first_deterministic", history_window=None),
            story_plan=plan,
            graph_traces=(
                GraphTraceRecord(
                    turn_index=0,
                    turn_id="t-det-0",
                    method="script_first_deterministic",
                    active_sku_id="SKU-HONEY-01",
                    turn_outcome="VERIFIED_READY",
                    invocation_latency_ms=0.5,
                ),
            ),
        )
        rel_det = compute_reliability_metrics(ev_det)
        for name in (
            "attempts_per_turn_mean",
            "attempts_per_turn_p50",
            "attempts_per_turn_p95",
            "attempts_per_turn_max",
        ):
            assert rel_det[name].status == MetricStatus.NOT_APPLICABLE
            assert rel_det[name].value is None


class TestPerformanceMetrics:
    """Kiểm thử trục Performance: không điền 0 cho token thiếu và tách bạch chi phí."""

    def test_unavailable_tokens_and_zero_calls_never_fill_zero(self) -> None:
        plan = _make_story_plan()
        ev_det = RunEvidence(
            manifest=_base_manifest(provider_tier="formal_experiment", provider_name="gemini"),
            story_plan=plan,
            provider_calls=(),
        )
        m_det = compute_performance_metrics(ev_det)
        assert m_det["total_model_calls"].value == 0
        for name in ("input_tokens", "output_tokens", "wasted_tokens"):
            assert m_det[name].status == MetricStatus.NOT_EVALUATED
            assert m_det[name].value is None
        assert m_det["estimated_llm_cost_usd"].status == MetricStatus.NOT_APPLICABLE
        assert m_det["estimated_llm_cost_usd"].value is None

        # Có 1 call báo UNAVAILABLE -> toàn bộ tổng token phải NOT_EVALUATED (None)
        ev_unavail = RunEvidence(
            manifest=_base_manifest(),
            story_plan=plan,
            provider_calls=(
                ProviderCallRecord(
                    call_index=0,
                    provider_name="ollama",
                    model_id="qwen3:1.7b",
                    tier="local_smoke_test",
                    latency_ms=250.0,
                    is_simulated_metric=False,
                    input_tokens=100,
                    output_tokens=50,
                    token_usage_source="MEASURED",
                    finish_reason="stop",
                    raw_response_valid=True,
                ),
                ProviderCallRecord(
                    call_index=1,
                    provider_name="ollama",
                    model_id="qwen3:1.7b",
                    tier="local_smoke_test",
                    latency_ms=350.0,
                    is_simulated_metric=False,
                    input_tokens=None,
                    output_tokens=None,
                    token_usage_source="UNAVAILABLE",
                    finish_reason="stop",
                    raw_response_valid=True,
                ),
            ),
        )
        m_unavail = compute_performance_metrics(ev_unavail)
        assert m_unavail["provider_latency_p50_ms"].value == pytest.approx(300.0)
        for name in ("input_tokens", "output_tokens", "wasted_tokens"):
            assert m_unavail[name].status == MetricStatus.NOT_EVALUATED
            assert m_unavail[name].value is None

    def test_mock_cost_not_applicable_and_priced_gemini_cost_computed(self) -> None:
        plan = _make_story_plan()
        ev_mock = RunEvidence(
            manifest=_base_manifest(provider_tier="unit_test", provider_name="mock"),
            story_plan=plan,
            provider_calls=(
                ProviderCallRecord(
                    call_index=0,
                    provider_name="mock",
                    model_id="deterministic-mock-v0.1",
                    tier="unit_test",
                    latency_ms=1.0,
                    is_simulated_metric=True,
                    input_tokens=40,
                    output_tokens=20,
                    token_usage_source="SIMULATED",
                    finish_reason="stop",
                    raw_response_valid=True,
                    is_wasted=True,
                ),
            ),
        )
        m_mock = compute_performance_metrics(ev_mock)
        assert m_mock["input_tokens"].value == 40
        assert m_mock["output_tokens"].value == 20
        assert m_mock["wasted_tokens"].value == 60
        assert m_mock["input_tokens"].is_simulated is True
        assert m_mock["estimated_llm_cost_usd"].status == MetricStatus.NOT_APPLICABLE
        assert m_mock["estimated_llm_cost_usd"].value is None

        ev_gemini = RunEvidence(
            manifest=_base_manifest(
                pricing={"input_per_1m_usd": 0.15, "output_per_1m_usd": 0.60}
            ),
            story_plan=plan,
            provider_calls=(
                ProviderCallRecord(
                    call_index=0,
                    provider_name="gemini",
                    model_id="gemini-2.5-flash",
                    tier="formal_experiment",
                    latency_ms=400.0,
                    is_simulated_metric=False,
                    input_tokens=1_000_000,
                    output_tokens=500_000,
                    token_usage_source="MEASURED",
                    finish_reason="STOP",
                    raw_response_valid=True,
                    is_wasted=False,
                ),
            ),
        )
        m_gemini = compute_performance_metrics(ev_gemini)
        assert m_gemini["estimated_llm_cost_usd"].status == MetricStatus.COMPUTED
        # 1.0 * 0.15 + 0.5 * 0.60 = 0.45 USD
        assert m_gemini["estimated_llm_cost_usd"].value == pytest.approx(0.45)

        # Hồi quy NEW-05: Fallback đọc pricing nằm lồng trong manifest["provider_config"]["pricing"]
        ev_gemini_nested = RunEvidence(
            manifest=_base_manifest(
                provider_config={"pricing": {"input_per_1m_usd": 0.15, "output_per_1m_usd": 0.60}},
            ),
            story_plan=plan,
            provider_calls=ev_gemini.provider_calls,
        )
        m_nested = compute_performance_metrics(ev_gemini_nested)
        assert m_nested["estimated_llm_cost_usd"].status == MetricStatus.COMPUTED
        assert m_nested["estimated_llm_cost_usd"].value == pytest.approx(0.45)


class TestEvaluatorComparisonAndBlindExport:
    """Kiểm thử nạp thư mục, báo cáo tổng hợp, kiểm tra cô lập tầng và xuất phiếu chấm mù."""

    def test_invalid_manifest_raises(self, tmp_path: Path) -> None:
        bad_dir = tmp_path / "bad_run"
        bad_dir.mkdir()
        with pytest.raises(FileNotFoundError):
            load_run_evidence(bad_dir)

        (bad_dir / "manifest.json").write_text(json.dumps({"run_id": "r1"}), encoding="utf-8")
        with pytest.raises(ValueError):
            load_run_evidence(bad_dir)

    def test_evaluate_directory_and_hard_gates(self, tmp_path: Path) -> None:
        plan = _make_story_plan()
        ev = RunEvidence(
            manifest=_base_manifest(run_id="run-clean"),
            story_plan=plan,
            transcript=(
                TranscriptEntry(
                    turn_index=0,
                    turn_id="t0",
                    sku_id="SKU-HONEY-01",
                    topic_id="top-1",
                    chunk_id="c1",
                    candidate_id="cand-0",
                    origin="PROACTIVE_STORY",
                    intent="origin",
                    text="Mật ong hoa cà phê Cư Mgar Đắk Lắk.",
                    covered_claim_ids=("clm-1",),
                    confirmed_topic_ids=("top-1",),
                    actual_duration_ms=5000,
                    playback_event_id="ack-0",
                    occurred_at_utc="2026-11-26T10:00:05Z",
                    gate_decision_id="p05-allow-0",
                ),
            ),
            playback_events=(
                PlaybackEventRecord(
                    sequence_index=0,
                    turn_id="t0",
                    candidate_id="cand-0",
                    chunk_id="c1",
                    sku_id="SKU-HONEY-01",
                    outcome="COMPLETED",
                    apply_status="APPLIED",
                    applied=True,
                    playback_event_id="ack-0",
                    actual_duration_ms=5000,
                    confirmed_topic_ids=("top-1",),
                ),
            ),
            graph_traces=(
                GraphTraceRecord(
                    turn_index=0,
                    turn_id="t0",
                    method="langgraph_structured_story",
                    active_sku_id="SKU-HONEY-01",
                    turn_outcome="VERIFIED_READY",
                    proposed_topic_ids=("top-1",),
                    verified_topic_ids=("top-1",),
                    p05_decisions=({"status": "VERIFIED", "reasons": []},),
                ),
            ),
        )
        run_dir = _write_run_dir(tmp_path / "run_clean", ev)
        report = evaluate_run_directory(run_dir)
        assert report.hard_gates_passed is True
        assert report.hard_gate_failures == ()
        assert len(report.human_eval_placeholders) == 6
        assert all(
            res.status == MetricStatus.NOT_EVALUATED and res.value is None
            for res in report.human_eval_placeholders.values()
        )
        assert report.metric_provenance["mandatory_topic_coverage"] == MetricProvenance.DERIVED_FROM_EVIDENCE.value

        # Khi có gold label phát hiện false_accept -> hard_gates_passed phải là False
        bad_gold = (
            GoldFactualLabel(
                candidate_id="cand-0",
                text="Sai lọt",
                verifier_decision="ALLOW",
                expected_factual_valid=False,
                has_unsupported_claim=True,
            ),
        )
        report_gold_fail = evaluate_run(ev, gold_labels=bad_gold)
        assert report_gold_fail.hard_gates_passed is False
        assert any("verifier_false_accept_count" in f for f in report_gold_fail.hard_gate_failures)

    def test_compare_runs_blocks_cross_tier_and_incompatible_configs(self, tmp_path: Path) -> None:
        plan_a = _make_story_plan(plan_id="plan-a", plan_revision=1)
        plan_b = _make_story_plan(plan_id="plan-b", plan_revision=2)

        dir_gemini = _write_run_dir(
            tmp_path / "r_gemini",
            RunEvidence(
                manifest=_base_manifest(
                    run_id="r-gemini",
                    provider_tier="formal_experiment",
                    provider_name="gemini",
                    model_id="gemini-2.5-flash",
                ),
                story_plan=plan_a,
            ),
        )
        dir_gemini_2 = _write_run_dir(
            tmp_path / "r_gemini_baseline",
            RunEvidence(
                manifest=_base_manifest(
                    run_id="r-gemini-base",
                    method="script_first",
                    history_window=None,
                    provider_tier="formal_experiment",
                    provider_name="gemini",
                    model_id="gemini-2.5-flash",
                ),
                story_plan=plan_a,
            ),
        )
        dir_ollama = _write_run_dir(
            tmp_path / "r_ollama",
            RunEvidence(
                manifest=_base_manifest(
                    run_id="r-ollama",
                    provider_tier="local_smoke_test",
                    provider_name="ollama",
                    model_id="qwen3:1.7b",
                    scenario="different_scenario",
                    dataset_sha256="other_sha",
                    contract_version="p06-mock-v0.2",
                ),
                story_plan=plan_b,
            ),
        )

        comp_ok = compare_runs([dir_gemini, dir_gemini_2])
        assert comp_ok.compatible is True
        assert comp_ok.grouped_tiers == ("formal_experiment",)

        comp_bad = compare_runs([dir_gemini, dir_ollama])
        assert comp_bad.compatible is False
        codes = {issue.code for issue in comp_bad.compatibility_issues}
        assert "CROSS_TIER_POOLING_PROHIBITED" in codes
        assert "SCENARIO_MISMATCH" in codes
        assert "DATASET_SHA256_MISMATCH" in codes
        assert "STORY_PLAN_MISMATCH" in codes
        assert "CONTRACT_VERSION_MISMATCH" in codes

        json_path = export_comparison_json(comp_ok, tmp_path / "out" / "cmp.json")
        csv_path = export_comparison_csv(comp_ok, tmp_path / "out" / "cmp.csv")
        md_path = export_comparison_markdown(comp_ok, tmp_path / "out" / "cmp.md")
        assert json_path.is_file() and csv_path.is_file() and md_path.is_file()
        assert "N/A" in md_path.read_text(encoding="utf-8")

    def test_blind_human_eval_export_zero_leaks_and_no_fake_scores(self, tmp_path: Path) -> None:
        plan = _make_story_plan()
        d1 = _write_run_dir(
            tmp_path / "run1",
            RunEvidence(
                manifest=_base_manifest(
                    run_id="secret-run-script-first",
                    method="script_first",
                    history_window=None,
                    model_id="gemini-2.5-flash-secret-tag",
                ),
                story_plan=plan,
                transcript=(
                    TranscriptEntry(
                        turn_index=0,
                        turn_id="t0",
                        sku_id="SKU-HONEY-01",
                        candidate_id="c0",
                        origin="PROACTIVE_STORY",
                        intent="origin",
                        text="Lời thoại mẫu thứ nhất.",
                        actual_duration_ms=4000,
                        playback_event_id="a0",
                        occurred_at_utc="2026-11-26T10:00:04Z",
                    ),
                ),
            ),
        )
        d2 = _write_run_dir(
            tmp_path / "run2",
            RunEvidence(
                manifest=_base_manifest(
                    run_id="secret-run-lg-w10",
                    method="langgraph_structured_story",
                    history_window=10,
                    model_id="gemini-2.5-flash-secret-tag",
                ),
                story_plan=plan,
                transcript=(
                    TranscriptEntry(
                        turn_index=0,
                        turn_id="t0",
                        sku_id="SKU-HONEY-01",
                        candidate_id="c0",
                        origin="PROACTIVE_STORY",
                        intent="origin",
                        text="Lời thoại mẫu thứ hai.",
                        actual_duration_ms=4000,
                        playback_event_id="a0",
                        occurred_at_utc="2026-11-26T10:00:04Z",
                    ),
                ),
            ),
        )

        csv_p, jsonl_p, map_p = export_blind_human_eval_sheets(
            [d1, d2], tmp_path / "blind", seed=42
        )
        csv_text = csv_p.read_text(encoding="utf-8")
        jsonl_text = jsonl_p.read_text(encoding="utf-8")
        for forbidden in (
            "secret-run-script-first",
            "secret-run-lg-w10",
            "script_first",
            "langgraph_structured_story",
            "gemini-2.5-flash-secret-tag",
            "formal_experiment",
        ):
            assert forbidden not in csv_text
            assert forbidden not in jsonl_text

        with csv_p.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 2
        for row in rows:
            assert row["blind_method_id"].startswith("METHOD_")
            for score_col in (
                "narrative_coherence",
                "naturalness",
                "persuasiveness",
                "context_relevance",
                "transition_quality",
                "repetition_quality",
                "hard_constraint_violation",
            ):
                assert row[score_col] == ""

        mapping_data = json.loads(map_p.read_text(encoding="utf-8"))
        assert {item["run_id"] for item in mapping_data} == {
            "secret-run-script-first",
            "secret-run-lg-w10",
        }
