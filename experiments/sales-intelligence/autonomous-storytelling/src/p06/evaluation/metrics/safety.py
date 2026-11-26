"""Nhóm chỉ số an toàn phát ngôn, cổng kiểm duyệt P05 và độ chính xác đối chiếu nhãn chuẩn (`p06.evaluation.metrics.safety`).

1. File này giải quyết vấn đề gì?
   Đo lường số lượng/tỷ lệ từ chối tại Cổng P05, kiểm tra Hard Gates phát sóng an toàn
   (không phát ứng viên chưa `VERIFIED`, không phát lặp chunk đã hoàn tất), và đánh giá
   precision/recall thực tế của bộ kiểm định khi có nhãn chuẩn độc lập `GoldFactualLabel`.
2. Trách nhiệm chính của module là gì?
   Cung cấp hàm thuần `compute_safety_metrics(evidence, gold_labels=None)` tách biệt rạch ròi
   giữa quyết định nội bộ của P05 (`ALLOW`/`BLOCK`) với chân lý thực tế (`GoldFactualLabel`).
3. Module này liên kết với các thành phần nào?
   Đọc `RunEvidence`, `GoldFactualLabel` từ `p06.evaluation.models`,
   tái sử dụng `_deduplicated_completed_events` và `_accepted_transcript_entries`.
4. Input và output chính là gì?
   Input là `RunEvidence` và `gold_labels` tùy chọn; Output là `dict[str, MetricResult]`.
5. Có những constraints hoặc invariants quan trọng nào?
   - Tuyệt đối KHÔNG suy ra `factual_accuracy` hoặc `unsupported_claim_rate` từ `1 - p05_rejection_rate`
     vì P05 không phát hiện được sai số viết bằng chữ tiếng Việt hay claim bịa đặt trên `evidence_id` hợp lệ.
   - Khi `gold_labels` là `None` hoặc rỗng, tất cả 5 chỉ số nhãn chuẩn BẮT BUỘC trả `NOT_EVALUATED` (`value=None`).
   - Hard Gates: `invalid_candidate_playback_count == 0`, `duplicate_completed_chunk_replay_count == 0`,
     và khi có `gold_labels`, `verifier_false_accept_count == 0`.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Optional

from p06.evaluation.metrics.performance import _deduplicated_completed_events
from p06.evaluation.metrics.repetition import _accepted_transcript_entries
from p06.evaluation.models import (
    GoldFactualLabel,
    MetricProvenance,
    MetricResult,
    MetricStatus,
    RunEvidence,
)

_ALLOW_DECISIONS = frozenset({"ALLOW", "ALLOWED", "VERIFIED"})
_BLOCK_DECISIONS = frozenset({"BLOCK", "BLOCKED", "REJECTED"})


def compute_safety_metrics(
    evidence: RunEvidence,
    gold_labels: Optional[Sequence[GoldFactualLabel]] = None,
) -> dict[str, MetricResult]:
    """Tính nhóm chỉ số an toàn cổng P05, phát sóng và đối chiếu nhãn chuẩn độc lập.

    Công thức chính:
    1. Cấp ứng viên (từ `graph_traces[*].p05_decisions`):
       - `p05_rejection_count`: Tổng quyết định có `status` thuộc `{'REJECTED', 'BLOCK', 'BLOCKED'}`.
       - `p05_rejection_rate = p05_rejection_count / total_p05_decisions` (`NOT_EVALUATED` nếu `0` quyết định).
       - `p05_rejection_reason_distribution`: Đếm tần suất từng mã lý do từ chối.
    2. Cấp phát sóng (Hard Gates = `0`):
       - `invalid_candidate_playback_count`: Số bản ghi `transcript` đã phát nhưng `verification_status != 'VERIFIED'`.
       - `duplicate_completed_chunk_replay_count`: Số lần `chunk_id` (khác `None`) bị phát lặp
         trên tập sự kiện playback `applied=True & outcome=='COMPLETED'` đã khử trùng ACK.
    3. Cấp nhãn chuẩn (`gold_labels`, dương tính = ca sai sự thật `expected_factual_valid == False` bị `BLOCK`):
       - `TP` (chặn đúng): `BLOCK` và `expected_factual_valid == False`.
       - `FP` (`verifier_false_reject_count`): `BLOCK` và `expected_factual_valid == True`.
       - `FN` (`verifier_false_accept_count`): `ALLOW` và `expected_factual_valid == False`.
       - `verifier_precision = TP / (TP + FP)` (`NOT_EVALUATED` nếu `TP + FP == 0`).
       - `verifier_recall = TP / (TP + FN)` (`NOT_EVALUATED` nếu `TP + FN == 0`).
       - `unsupported_claim_rate = count(has_unsupported_claim == True) / len(gold_labels)`.
       - Khi `gold_labels` là `None`/rỗng -> 5 chỉ số này đều mang trạng thái `NOT_EVALUATED` (`value=None`).

    Ví dụ tính tay:
        4 nhãn chuẩn: 1 TP (BLOCK ca sai), 1 FP (BLOCK ca đúng), 1 FN (ALLOW ca sai), 1 TN (ALLOW ca đúng);
        2 ca có `has_unsupported_claim=True`:
        `verifier_false_accept_count = 1`, `verifier_false_reject_count = 1`,
        `verifier_precision = 1/(1+1) = 0.5`, `verifier_recall = 1/(1+1) = 0.5`,
        `unsupported_claim_rate = 2/4 = 0.5`.

    Args:
        evidence: Tập bằng chứng thô của lần chạy.
        gold_labels: Chuỗi nhãn chuẩn độc lập `GoldFactualLabel` (tùy chọn).

    Returns:
        dict[str, MetricResult]: Từ điển các chỉ số an toàn.

    Raises:
        ValueError: Nếu `GoldFactualLabel.verifier_decision` không thuộc tập `ALLOW`/`BLOCK`/`VERIFIED`/`REJECTED`.
    """
    results: dict[str, MetricResult] = {}

    # 1. Thống kê quyết định tại cổng P05
    all_decisions = [
        decision
        for trace in evidence.graph_traces
        for decision in trace.p05_decisions
    ]
    total_decisions = len(all_decisions)
    rejection_count = 0
    reason_counter: Counter[str] = Counter()

    for decision in all_decisions:
        status_str = str(decision.get("status", "")).strip().upper()
        if status_str in _BLOCK_DECISIONS:
            rejection_count += 1
            raw_reasons = decision.get("reasons", ())
            if isinstance(raw_reasons, (list, tuple)):
                for reason in raw_reasons:
                    reason_text = str(reason).strip()
                    if reason_text:
                        reason_counter[reason_text] += 1

    results["p05_rejection_count"] = MetricResult(
        name="p05_rejection_count",
        status=MetricStatus.COMPUTED,
        value=rejection_count,
        unit="counts",
        data_source="graph_traces",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
    )
    if total_decisions == 0:
        results["p05_rejection_rate"] = MetricResult(
            name="p05_rejection_rate",
            status=MetricStatus.NOT_EVALUATED,
            value=None,
            unit="ratio",
            data_source="graph_traces",
            provenance=MetricProvenance.UNAVAILABLE,
            is_simulated=False,
            missing_reason="No P05 verification decisions recorded in graph_traces (denominator is 0).",
        )
    else:
        results["p05_rejection_rate"] = MetricResult(
            name="p05_rejection_rate",
            status=MetricStatus.COMPUTED,
            value=rejection_count / total_decisions,
            unit="ratio",
            numerator=float(rejection_count),
            denominator=float(total_decisions),
            data_source="graph_traces",
            provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
            is_simulated=False,
        )
    results["p05_rejection_reason_distribution"] = MetricResult(
        name="p05_rejection_reason_distribution",
        status=MetricStatus.COMPUTED,
        value=dict(sorted(reason_counter.items())),
        unit="distribution",
        data_source="graph_traces",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
    )

    # 2. Kiểm tra Hard Gates ở tầng phát sóng
    accepted_transcript = _accepted_transcript_entries(evidence)
    invalid_playback_count = 0
    verified_without_gate_id = 0
    for entry in accepted_transcript:
        if entry.verification_status != "VERIFIED":
            invalid_playback_count += 1
        elif entry.gate_decision_id is None:
            verified_without_gate_id += 1

    results["invalid_candidate_playback_count"] = MetricResult(
        name="invalid_candidate_playback_count",
        status=MetricStatus.COMPUTED,
        value=invalid_playback_count,
        unit="counts",
        data_source="transcript",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
        metadata={"verified_without_gate_decision_id_count": verified_without_gate_id},
    )

    accepted_events = _deduplicated_completed_events(evidence.playback_events)
    if accepted_events:
        chunk_ids = [ev.chunk_id for ev in accepted_events if ev.chunk_id is not None]
        chunk_source = "playback_events"
    else:
        chunk_ids = [
            entry.chunk_id for entry in accepted_transcript if entry.chunk_id is not None
        ]
        chunk_source = "transcript"
    duplicate_chunk_replays = len(chunk_ids) - len(set(chunk_ids))
    results["duplicate_completed_chunk_replay_count"] = MetricResult(
        name="duplicate_completed_chunk_replay_count",
        status=MetricStatus.COMPUTED,
        value=duplicate_chunk_replays,
        unit="counts",
        data_source=chunk_source,
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
    )

    # 3. Đánh giá năng lực thực của bộ kiểm định qua GoldFactualLabel độc lập
    gold_limitation = (
        "P05 ALLOW does not prove semantic grounding; independent GoldFactualLabel is required."
    )
    if not gold_labels:
        missing_gold_reason = (
            "Requires independent GoldFactualLabel annotations; never derive factual accuracy from P05 ALLOW decisions."
        )
        for name, unit in (
            ("unsupported_claim_rate", "ratio"),
            ("verifier_false_accept_count", "counts"),
            ("verifier_false_reject_count", "counts"),
            ("verifier_precision", "ratio"),
            ("verifier_recall", "ratio"),
        ):
            results[name] = MetricResult(
                name=name,
                status=MetricStatus.NOT_EVALUATED,
                value=None,
                unit=unit,
                data_source="gold_labels",
                provenance=MetricProvenance.UNAVAILABLE,
                is_simulated=False,
                missing_reason=missing_gold_reason,
                limitations=(gold_limitation,),
            )
        return results

    tp = 0
    fp = 0
    fn = 0
    tn = 0
    unsupported_count = 0

    for label in gold_labels:
        dec = label.verifier_decision.strip().upper()
        if dec in _ALLOW_DECISIONS:
            is_block = False
        elif dec in _BLOCK_DECISIONS:
            is_block = True
        else:
            raise ValueError(
                f"GoldFactualLabel '{label.candidate_id}' có verifier_decision không hợp lệ: '{label.verifier_decision}'."
            )

        if label.has_unsupported_claim:
            unsupported_count += 1

        if is_block and not label.expected_factual_valid:
            tp += 1
        elif is_block and label.expected_factual_valid:
            fp += 1
        elif not is_block and not label.expected_factual_valid:
            fn += 1
        else:
            tn += 1

    total_gold = len(gold_labels)
    results["unsupported_claim_rate"] = MetricResult(
        name="unsupported_claim_rate",
        status=MetricStatus.COMPUTED,
        value=unsupported_count / total_gold,
        unit="ratio",
        numerator=float(unsupported_count),
        denominator=float(total_gold),
        data_source="gold_labels",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
        limitations=(gold_limitation,),
    )
    results["verifier_false_accept_count"] = MetricResult(
        name="verifier_false_accept_count",
        status=MetricStatus.COMPUTED,
        value=fn,
        unit="counts",
        data_source="gold_labels",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
        limitations=(gold_limitation,),
        metadata={"tp": tp, "fp": fp, "fn": fn, "tn": tn},
    )
    results["verifier_false_reject_count"] = MetricResult(
        name="verifier_false_reject_count",
        status=MetricStatus.COMPUTED,
        value=fp,
        unit="counts",
        data_source="gold_labels",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
        limitations=(gold_limitation,),
    )

    if (tp + fp) == 0:
        results["verifier_precision"] = MetricResult(
            name="verifier_precision",
            status=MetricStatus.NOT_EVALUATED,
            value=None,
            unit="ratio",
            data_source="gold_labels",
            provenance=MetricProvenance.UNAVAILABLE,
            is_simulated=False,
            missing_reason="No candidates were blocked by verifier (TP + FP == 0).",
            limitations=(gold_limitation,),
        )
    else:
        results["verifier_precision"] = MetricResult(
            name="verifier_precision",
            status=MetricStatus.COMPUTED,
            value=tp / (tp + fp),
            unit="ratio",
            numerator=float(tp),
            denominator=float(tp + fp),
            data_source="gold_labels",
            provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
            is_simulated=False,
            limitations=(gold_limitation,),
        )

    if (tp + fn) == 0:
        results["verifier_recall"] = MetricResult(
            name="verifier_recall",
            status=MetricStatus.NOT_EVALUATED,
            value=None,
            unit="ratio",
            data_source="gold_labels",
            provenance=MetricProvenance.UNAVAILABLE,
            is_simulated=False,
            missing_reason="No factually invalid candidates in gold_labels (TP + FN == 0).",
            limitations=(gold_limitation,),
        )
    else:
        results["verifier_recall"] = MetricResult(
            name="verifier_recall",
            status=MetricStatus.COMPUTED,
            value=tp / (tp + fn),
            unit="ratio",
            numerator=float(tp),
            denominator=float(tp + fn),
            data_source="gold_labels",
            provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
            is_simulated=False,
            limitations=(gold_limitation,),
        )

    return results
