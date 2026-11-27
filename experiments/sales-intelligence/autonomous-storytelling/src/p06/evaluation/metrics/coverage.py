"""Nhóm chỉ số độ phủ chủ đề, claim và thời lượng phát sóng cho P06 (`p06.evaluation.metrics.coverage`).

1. File này giải quyết vấn đề gì?
   Đo lường độ phủ thực tế của phiên kể chuyện dựa trên bằng chứng phát sóng có xác nhận
   (`PlaybackCompleted` ACK), tách biệt rạch ròi giữa chủ đề được đề xuất (`proposed`),
   đã qua cổng P05 (`verified`), và thực sự đã phát hoàn tất (`completed`) theo bất biến `I-03`/`I-06`.
2. Trách nhiệm chính của module là gì?
   Cung cấp hàm thuần `compute_coverage_metrics()` tính các chỉ số độ phủ chủ đề bắt buộc,
   độ phủ claim khai báo, thời lượng phát mô phỏng, thời gian hoàn tất các chủ đề bắt buộc,
   và giữ chỗ trung thực cho `human_assessed_fact_coverage`.
3. Module này liên kết với các thành phần nào?
   Đọc `RunEvidence` và `StoryPlan` (`p06.evaluation.models`, `p06.schemas.story`),
   tái sử dụng bộ khử trùng playback từ `p06.evaluation.metrics.performance`.
4. Input và output chính là gì?
   Input là `RunEvidence`; Output là `dict[str, MetricResult]` gồm 13 chỉ số thuộc trục Coverage.
5. Có những constraints hoặc invariants quan trọng nào?
   - `completed_topic_ids` CHỈ lấy từ `playback_events` thỏa mãn `applied=True` và `outcome=='COMPLETED'`
     sau khi khử trùng theo `playback_event_id`/`turn_id`, loại trừ tuyệt đối `FAILED`, `UNKNOWN`,
     bản ghi bị từ chối và lượt `FALLBACK_PREAPPROVED`.
   - `declared_verified_claim_coverage` KHÔNG đồng nghĩa với chứng minh suy diễn ngữ nghĩa (semantic entailment)
     vì cổng P05 hiện tại không kiểm tra ngữ nghĩa câu văn với `claim_id`.
   - `target_duration_sec <= 0` khiến `duration_fulfillment` và `raw_duration_ratio` mang trạng thái `INVALID`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from p06.evaluation.metrics.performance import _deduplicated_completed_events
from p06.evaluation.models import (
    MetricProvenance,
    MetricResult,
    MetricStatus,
    RunEvidence,
)


def _parse_iso_utc(raw: Optional[str]) -> Optional[datetime]:
    """Chuyển chuỗi thời gian ISO-8601 sang `datetime` nếu hợp lệ, ngược lại trả `None`."""
    if not raw or not isinstance(raw, str):
        return None
    normalized = raw.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def compute_coverage_metrics(evidence: RunEvidence) -> dict[str, MetricResult]:
    """Tính toàn bộ nhóm chỉ số độ phủ chủ đề, claim và thời lượng từ `RunEvidence`.

    Công thức chính:
    1. `planned_mandatory_topic_count = |story_plan.mandatory_topic_ids()|`.
    2. `proposed_topic_count = |⋃ trace.proposed_topic_ids|`, `verified_topic_count = |⋃ trace.verified_topic_ids|`.
       - Ý nghĩa: Tách rạch ròi ý định sinh (`proposed`) và kết quả qua cổng P05 (`verified`) khỏi phát sóng.
    3. `completed_topic_count`: Số `topic_id` duy nhất trích CHỈ từ `playback_events` đã khử trùng
       có `applied=True`, `outcome=='COMPLETED'` và KHÔNG thuộc lượt `FALLBACK_PREAPPROVED`.
       Đối chiếu chéo với `transcript` và lưu sai lệch vào `metadata`.
    4. `mandatory_topic_coverage = |completed ∩ expected_mandatory| / |expected_mandatory|`.
       - Trường hợp biên: `|expected_mandatory| == 0` -> `NOT_EVALUATED` (`value=None`).
    5. `remaining_mandatory_topics = |expected_mandatory - completed|` (metadata lưu `remaining_topic_ids`).
    6. `declared_verified_claim_coverage = |covered_claims ∩ allowed_claims| / |allowed_claims|`,
       trong đó `covered_claims` lấy từ `transcript` hợp lệ (`verification_status=='VERIFIED'` và không fallback).
       - Trường hợp biên: `|allowed_claims| == 0` -> `NOT_EVALUATED` (`value=None`).
       - Giới hạn quan trọng: P05 chỉ kiểm tra mã `evidence_id` và giá/cụm từ cấm, KHÔNG kiểm tra
         semantic entailment giữa văn bản và `claim_id`.
    7. `human_assessed_fact_coverage`: Luôn là `NOT_EVALUATED` (`value=None`) cho tới khi chấm người thật (T09).
    8. `simulated_played_duration_sec = sum(actual_duration_ms / 1000.0)` trên các ACK hoàn tất đã khử trùng.
    9. `duration_fulfillment = min(simulated_played_duration_sec / target_duration_sec, 1.0)` và
       `raw_duration_ratio = simulated_played_duration_sec / target_duration_sec` (`INVALID` nếu `target <= 0`).
    10. `simulated_elapsed_sec` và `simulated_idle_sec = max(0.0, simulated_elapsed_sec - simulated_played_duration_sec)`.
    11. `time_to_complete_mandatory_topics_sec`: Thời gian ảo tại sự kiện ACK hoàn tất `topic_id` bắt buộc cuối cùng
        (tính trên hệ quy chiếu `VirtualClock` từ `simulator_assumptions.virtual_clock_start_utc` nếu có,
        ngược lại dùng tổng thời lượng phát tích lũy `cumulative_played_duration_sec`, tuyệt đối KHÔNG trừ
        đồng hồ tường `started_at_utc` vào mốc thời gian ảo); nếu chưa hoàn tất đủ mọi mandatory topics
        hoặc không có mandatory topic nào -> `NOT_EVALUATED` (`value=None`).

    Ví dụ tính tay:
        `StoryPlan` có 2 mandatory topics `{'t1', 't2'}` và 2 `allowed_claim_ids` `{'c1', 'c2'}`.
        Playback ACK hoàn tất `'t1'` (6.0s) và `'t2'` (4.0s), `target_duration_sec = 20.0`:
        `mandatory_topic_coverage = 2/2 = 1.0`, `simulated_played_duration_sec = 10.0`,
        `duration_fulfillment = 10.0/20.0 = 0.5`, `time_to_complete_mandatory_topics_sec = 10.0`.

    Args:
        evidence: Tập bằng chứng thô của một lần chạy.

    Returns:
        dict[str, MetricResult]: Từ điển các chỉ số thuộc trục Coverage.
    """
    results: dict[str, MetricResult] = {}
    story_plan = evidence.story_plan

    expected_mandatory_ids = story_plan.mandatory_topic_ids()
    planned_mandatory_count = len(expected_mandatory_ids)

    proposed_topic_ids: set[str] = {
        tid for trace in evidence.graph_traces for tid in trace.proposed_topic_ids
    }
    verified_topic_ids: set[str] = {
        tid for trace in evidence.graph_traces for tid in trace.verified_topic_ids
    }

    # Xác định toàn bộ lượt fallback để cấm tính nhầm topic vào độ phủ chính thức.
    fallback_turn_ids: set[str] = {
        entry.turn_id
        for entry in evidence.transcript
        if entry.is_fallback or entry.origin == "PREAPPROVED_FALLBACK"
    } | {
        trace.turn_id
        for trace in evidence.graph_traces
        if trace.used_fallback or trace.turn_outcome == "FALLBACK_PREAPPROVED"
    }

    accepted_events = _deduplicated_completed_events(evidence.playback_events)
    accepted_non_fallback_events = [
        ev for ev in accepted_events if ev.turn_id not in fallback_turn_ids
    ]

    raw_min_chunks = evidence.manifest.get("min_chunks_per_topic", 1)
    min_chunks_per_topic = max(1, int(raw_min_chunks)) if raw_min_chunks is not None else 1

    played_chunk_counts_by_topic: dict[str, int] = {}
    for ev in accepted_non_fallback_events:
        for tid in set(ev.confirmed_topic_ids):
            played_chunk_counts_by_topic[tid] = played_chunk_counts_by_topic.get(tid, 0) + 1

    completed_topic_ids: set[str] = {
        tid for tid, count in played_chunk_counts_by_topic.items() if count >= min_chunks_per_topic
    }
    partially_covered_topic_ids = sorted(
        tid for tid, count in played_chunk_counts_by_topic.items() if 0 < count < min_chunks_per_topic
    )

    # Đối chiếu chéo giữa transcript và playback_events để phát hiện sai lệch nhật ký.
    accepted_turn_ids = {ev.turn_id for ev in accepted_events}
    transcript_turn_ids = {entry.turn_id for entry in evidence.transcript}
    transcript_only_turns = sorted(transcript_turn_ids - accepted_turn_ids)
    playback_only_turns = sorted(accepted_turn_ids - transcript_turn_ids)
    transcript_chunk_counts_by_topic: dict[str, int] = {}
    for entry in evidence.transcript:
        if not entry.is_fallback and entry.origin != "PREAPPROVED_FALLBACK":
            for tid in set(entry.confirmed_topic_ids):
                transcript_chunk_counts_by_topic[tid] = (
                    transcript_chunk_counts_by_topic.get(tid, 0) + 1
                )
    transcript_confirmed_topics = {
        tid
        for tid, count in transcript_chunk_counts_by_topic.items()
        if count >= min_chunks_per_topic
    }
    cross_check_consistent = (
        not transcript_only_turns
        and not playback_only_turns
        and transcript_confirmed_topics == completed_topic_ids
        and transcript_chunk_counts_by_topic == played_chunk_counts_by_topic
    )

    results["planned_mandatory_topic_count"] = MetricResult(
        name="planned_mandatory_topic_count",
        status=MetricStatus.COMPUTED,
        value=planned_mandatory_count,
        unit="topics",
        data_source="story_plan",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
    )
    results["proposed_topic_count"] = MetricResult(
        name="proposed_topic_count",
        status=MetricStatus.COMPUTED,
        value=len(proposed_topic_ids),
        unit="topics",
        data_source="graph_traces",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
        metadata={"proposed_topic_ids": sorted(proposed_topic_ids)},
    )
    results["verified_topic_count"] = MetricResult(
        name="verified_topic_count",
        status=MetricStatus.COMPUTED,
        value=len(verified_topic_ids),
        unit="topics",
        data_source="graph_traces",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
        metadata={"verified_topic_ids": sorted(verified_topic_ids)},
    )
    results["completed_topic_count"] = MetricResult(
        name="completed_topic_count",
        status=MetricStatus.COMPUTED,
        value=len(completed_topic_ids),
        unit="topics",
        data_source="playback_events",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
        metadata={
            "completed_topic_ids": sorted(completed_topic_ids),
            "min_chunks_per_topic": min_chunks_per_topic,
            "played_chunk_counts_by_topic": dict(sorted(played_chunk_counts_by_topic.items())),
            "partially_covered_topic_ids": partially_covered_topic_ids,
            "cross_check_consistent": cross_check_consistent,
            "transcript_only_turn_ids": transcript_only_turns,
            "playback_only_turn_ids": playback_only_turns,
        },
    )

    covered_mandatory_ids = completed_topic_ids & expected_mandatory_ids
    remaining_mandatory_ids = sorted(expected_mandatory_ids - completed_topic_ids)

    if planned_mandatory_count == 0:
        results["mandatory_topic_coverage"] = MetricResult(
            name="mandatory_topic_coverage",
            status=MetricStatus.NOT_EVALUATED,
            value=None,
            unit="ratio",
            data_source="playback_events+story_plan",
            provenance=MetricProvenance.UNAVAILABLE,
            is_simulated=False,
            missing_reason="StoryPlan has no mandatory topics (denominator is 0).",
        )
    else:
        results["mandatory_topic_coverage"] = MetricResult(
            name="mandatory_topic_coverage",
            status=MetricStatus.COMPUTED,
            value=len(covered_mandatory_ids) / planned_mandatory_count,
            unit="ratio",
            numerator=float(len(covered_mandatory_ids)),
            denominator=float(planned_mandatory_count),
            data_source="playback_events+story_plan",
            provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
            is_simulated=False,
            metadata={
                "min_chunks_per_topic": min_chunks_per_topic,
                "completed_mandatory_topic_ids": sorted(covered_mandatory_ids),
                "remaining_topic_ids": remaining_mandatory_ids,
                "partially_covered_topic_ids": partially_covered_topic_ids,
                "played_chunk_counts_by_topic": dict(sorted(played_chunk_counts_by_topic.items())),
            },
        )

    results["remaining_mandatory_topics"] = MetricResult(
        name="remaining_mandatory_topics",
        status=MetricStatus.COMPUTED,
        value=len(remaining_mandatory_ids),
        unit="topics",
        data_source="playback_events+story_plan",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
        metadata={"remaining_topic_ids": remaining_mandatory_ids},
    )

    # Độ phủ claim khai báo: loại trừ fallback và các lượt bị đánh dấu thất bại trong playback_events.
    rejected_only_turn_ids = {
        ev.turn_id for ev in evidence.playback_events if ev.turn_id not in accepted_turn_ids
    }
    allowed_claim_ids: set[str] = {
        claim_id
        for arc in story_plan.arcs
        for topic in arc.topics
        for claim_id in topic.allowed_claim_ids
    }
    covered_claim_ids: set[str] = {
        claim_id
        for entry in evidence.transcript
        if (
            not entry.is_fallback
            and entry.origin != "PREAPPROVED_FALLBACK"
            and entry.verification_status == "VERIFIED"
            and entry.turn_id not in rejected_only_turn_ids
        )
        for claim_id in entry.covered_claim_ids
    }
    entailment_limitation = (
        "P05 PublicationGate does NOT verify semantic entailment between spoken text and declared claim_id/evidence_id."
    )
    if not allowed_claim_ids:
        results["declared_verified_claim_coverage"] = MetricResult(
            name="declared_verified_claim_coverage",
            status=MetricStatus.NOT_EVALUATED,
            value=None,
            unit="ratio",
            data_source="transcript+story_plan",
            provenance=MetricProvenance.UNAVAILABLE,
            is_simulated=False,
            missing_reason="StoryPlan has no allowed_claim_ids (denominator is 0).",
            limitations=(entailment_limitation,),
        )
    else:
        covered_allowed = covered_claim_ids & allowed_claim_ids
        results["declared_verified_claim_coverage"] = MetricResult(
            name="declared_verified_claim_coverage",
            status=MetricStatus.COMPUTED,
            value=len(covered_allowed) / len(allowed_claim_ids),
            unit="ratio",
            numerator=float(len(covered_allowed)),
            denominator=float(len(allowed_claim_ids)),
            data_source="transcript+story_plan",
            provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
            is_simulated=False,
            limitations=(entailment_limitation,),
            metadata={
                "covered_allowed_claim_ids": sorted(covered_allowed),
                "extra_claim_ids": sorted(covered_claim_ids - allowed_claim_ids),
            },
        )

    results["human_assessed_fact_coverage"] = MetricResult(
        name="human_assessed_fact_coverage",
        status=MetricStatus.NOT_EVALUATED,
        value=None,
        unit="ratio",
        data_source="human_eval_sheet",
        provenance=MetricProvenance.UNAVAILABLE,
        is_simulated=False,
        missing_reason="Requires independent human factual assessment (T09).",
    )

    # Thời lượng phát mô phỏng & độ khớp mục tiêu phiên
    played_duration_sec = sum(
        (ev.actual_duration_ms or 0) / 1000.0 for ev in accepted_events
    )
    results["simulated_played_duration_sec"] = MetricResult(
        name="simulated_played_duration_sec",
        status=MetricStatus.COMPUTED,
        value=played_duration_sec,
        unit="sec",
        data_source="playback_events",
        provenance=MetricProvenance.SIMULATED_CLOCK,
        is_simulated=True,
    )

    target_sec = float(evidence.target_duration_sec)
    if target_sec <= 0.0:
        for name in ("duration_fulfillment", "raw_duration_ratio"):
            results[name] = MetricResult(
                name=name,
                status=MetricStatus.INVALID,
                value=None,
                unit="ratio",
                data_source="playback_events+run_evidence",
                provenance=MetricProvenance.UNAVAILABLE,
                is_simulated=True,
                missing_reason=f"Invalid target_duration_sec={target_sec}; must be > 0.",
            )
    else:
        raw_ratio = played_duration_sec / target_sec
        results["duration_fulfillment"] = MetricResult(
            name="duration_fulfillment",
            status=MetricStatus.COMPUTED,
            value=min(raw_ratio, 1.0),
            unit="ratio",
            numerator=played_duration_sec,
            denominator=target_sec,
            data_source="playback_events+run_evidence",
            provenance=MetricProvenance.SIMULATED_CLOCK,
            is_simulated=True,
        )
        results["raw_duration_ratio"] = MetricResult(
            name="raw_duration_ratio",
            status=MetricStatus.COMPUTED,
            value=raw_ratio,
            unit="ratio",
            numerator=played_duration_sec,
            denominator=target_sec,
            data_source="playback_events+run_evidence",
            provenance=MetricProvenance.SIMULATED_CLOCK,
            is_simulated=True,
        )

    elapsed_sec = float(evidence.simulated_elapsed_sec)
    idle_sec = max(0.0, elapsed_sec - played_duration_sec)
    results["simulated_elapsed_sec"] = MetricResult(
        name="simulated_elapsed_sec",
        status=MetricStatus.COMPUTED,
        value=elapsed_sec,
        unit="sec",
        data_source="run_evidence",
        provenance=MetricProvenance.SIMULATED_CLOCK,
        is_simulated=True,
    )
    results["simulated_idle_sec"] = MetricResult(
        name="simulated_idle_sec",
        status=MetricStatus.COMPUTED,
        value=idle_sec,
        unit="sec",
        data_source="run_evidence+playback_events",
        provenance=MetricProvenance.SIMULATED_CLOCK,
        is_simulated=True,
    )

    # Thời gian hoàn tất toàn bộ mandatory topics
    if planned_mandatory_count == 0:
        results["time_to_complete_mandatory_topics_sec"] = MetricResult(
            name="time_to_complete_mandatory_topics_sec",
            status=MetricStatus.NOT_EVALUATED,
            value=None,
            unit="sec",
            data_source="playback_events+story_plan",
            provenance=MetricProvenance.UNAVAILABLE,
            is_simulated=True,
            missing_reason="StoryPlan has no mandatory topics.",
        )
    elif remaining_mandatory_ids:
        results["time_to_complete_mandatory_topics_sec"] = MetricResult(
            name="time_to_complete_mandatory_topics_sec",
            status=MetricStatus.NOT_EVALUATED,
            value=None,
            unit="sec",
            data_source="playback_events+story_plan",
            provenance=MetricProvenance.UNAVAILABLE,
            is_simulated=True,
            missing_reason=(
                f"Not all mandatory topics were completed; remaining={remaining_mandatory_ids}."
            ),
        )
    else:
        seen_mandatory_counts: dict[str, int] = {}
        completed_mandatory: set[str] = set()
        cumulative_ms = 0
        completion_event = None
        for ev in accepted_events:
            cumulative_ms += ev.actual_duration_ms or 0
            if ev.turn_id not in fallback_turn_ids:
                for tid in set(ev.confirmed_topic_ids):
                    if tid in expected_mandatory_ids:
                        new_count = seen_mandatory_counts.get(tid, 0) + 1
                        seen_mandatory_counts[tid] = new_count
                        if new_count >= min_chunks_per_topic:
                            completed_mandatory.add(tid)
            if len(completed_mandatory) == planned_mandatory_count:
                completion_event = ev
                break

        cumulative_sec = cumulative_ms / 1000.0
        elapsed_at_completion = cumulative_sec
        time_basis = "cumulative_played_duration_sec"
        sim_assumptions = evidence.manifest.get("simulator_assumptions")
        raw_v_start = (
            sim_assumptions.get("virtual_clock_start_utc")
            if isinstance(sim_assumptions, dict)
            else None
        ) or evidence.manifest.get("virtual_clock_start_utc")
        # Tuyệt đối không lấy occurred_at_utc (VirtualClock) trừ wall-clock started_at_utc.
        v_start_dt = _parse_iso_utc(raw_v_start)
        if v_start_dt is not None and completion_event is not None:
            comp_dt = _parse_iso_utc(completion_event.occurred_at_utc)
            if comp_dt is not None and comp_dt >= v_start_dt:
                elapsed_at_completion = (comp_dt - v_start_dt).total_seconds()
                time_basis = "virtual_clock"

        results["time_to_complete_mandatory_topics_sec"] = MetricResult(
            name="time_to_complete_mandatory_topics_sec",
            status=MetricStatus.COMPUTED,
            value=elapsed_at_completion,
            unit="sec",
            data_source="playback_events+story_plan",
            provenance=MetricProvenance.SIMULATED_CLOCK,
            is_simulated=True,
            metadata={
                "cumulative_played_duration_sec": cumulative_sec,
                "time_basis": time_basis,
            },
        )

    return results
