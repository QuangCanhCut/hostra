"""Nhóm chỉ số độ tin cậy, vòng lặp viết lại có giới hạn (bounded rewrite) và lỗi hệ thống (`p06.evaluation.metrics.reliability`).

1. File này giải quyết vấn đề gì?
   Đánh giá mức độ ổn định của đồ thị LangGraph và baseline `ScriptFirst`: tần suất phải viết lại
   do bị P05 từ chối hoặc trùng lặp, mức độ tuân thủ ngân sách retry `K`, tỷ lệ fallback,
   tỷ lệ dừng an toàn (`SAFE_ABORT_NO_CANDIDATE`), và phân bố lỗi retryable/non-retryable/provider.
2. Trách nhiệm chính của module là gì?
   Cung cấp hàm thuần `compute_reliability_metrics()` tính 17 chỉ số thuộc trục Reliability
   từ `graph_traces`, `provider_calls`, `errors` và `manifest`.
3. Module này liên kết với các thành phần nào?
   Đọc `RunEvidence` từ `p06.evaluation.models`, tái sử dụng `compute_percentile` từ
   `p06.evaluation.metrics.performance`.
4. Input và output chính là gì?
   Input là `RunEvidence`; Output là `dict[str, MetricResult]`.
5. Có những constraints hoặc invariants quan trọng nào?
   - `retry_budget_violations == 0` là Hard Gate (cấm vượt trần `max_retries` trong `RewriteBudgetState`).
   - Khi `turns_attempted == 0` (`len(graph_traces) == 0`), mọi tỷ lệ và phân vị theo lượt trả
     `MetricStatus.NOT_EVALUATED` (`value=None`), không ngụy tạo `0`.
"""

from __future__ import annotations

from collections import Counter

from p06.evaluation.metrics.performance import compute_percentile
from p06.evaluation.models import (
    MetricProvenance,
    MetricResult,
    MetricStatus,
    RunEvidence,
    is_clean_termination_boundary_trace,
)


def compute_reliability_metrics(evidence: RunEvidence) -> dict[str, MetricResult]:
    """Tính toàn bộ nhóm chỉ số độ tin cậy, rewrite, fallback và phân bố lỗi từ `RunEvidence`.

    Công thức chính:
    1. `generation_attempts`: Tổng `len(trace.draft_attempts)` trên `graph_traces` (nếu `graph_traces`
       không ghi `draft_attempts`, rơi về `len(provider_calls)` nếu có, ngược lại `0`).
    2. `successful_candidate_count`: Số lượt có `turn_outcome == 'VERIFIED_READY'`.
    3. `rewrite_count`: Tổng `trace.retries_used` trên `graph_traces` (baseline `script_first` là `0`).
    4. `rewrite_rate = count(retries_used > 0) / len(graph_traces)` (`NOT_EVALUATED` nếu `0` lượt).
    5. `attempts_per_turn_{mean, p50, p95, max}`: Với mỗi lượt, số lần thử là `len(trace.draft_attempts)`
       nếu khác rỗng, ngược lại `1 + trace.retries_used`. (`NOT_EVALUATED` nếu `0` lượt).
    6. `retry_budget_violations`: Số lượt có `trace.retries_used > trace.max_retries` (Hard Gate = `0`).
    7. `fallback_count` và `fallback_rate`: Lượt có `used_fallback=True` hoặc `turn_outcome == 'FALLBACK_PREAPPROVED'`.
    8. `safe_abort_count` và `safe_abort_rate`: Lượt có `turn_outcome == 'SAFE_ABORT_NO_CANDIDATE'`.
    9. `retryable_failure_distribution`, `non_retryable_failure_distribution` (từ `evidence.errors`),
       `provider_error_distribution` (từ `evidence.provider_calls[*].error_type`).
    10. `termination_reason`: Chuỗi lý do kết thúc phiên từ `manifest['termination_reason']`
        (hoặc dấu vết lượt cuối; `NOT_EVALUATED` nếu thiếu).

    Ví dụ tính tay:
        3 lượt `graph_traces`: lượt 0 (`retries_used=0`, `VERIFIED_READY`, 1 draft),
        lượt 1 (`retries_used=2`, `max_retries=2`, `FALLBACK_PREAPPROVED`, 3 drafts),
        lượt 2 (`retries_used=1`, `max_retries=2`, `VERIFIED_READY`, 2 drafts):
        `generation_attempts = 6`, `successful_candidate_count = 2`, `rewrite_count = 3`,
        `rewrite_rate = 2/3`, `attempts_per_turn_mean = 2.0`, `retry_budget_violations = 0`,
        `fallback_count = 1`, `fallback_rate = 1/3`.

    Args:
        evidence: Tập bằng chứng thô của lần chạy.

    Returns:
        dict[str, MetricResult]: Từ điển các chỉ số độ tin cậy.
    """
    results: dict[str, MetricResult] = {}
    traces = evidence.graph_traces
    # Loại bỏ các lượt kết thúc biên SKU/phiên sạch (không gọi LLM, không lỗi) khỏi mẫu số lượt nội dung.
    content_traces = [t for t in traces if not is_clean_termination_boundary_trace(t)]
    termination_boundary_turns_excluded = len(traces) - len(content_traces)
    turns_attempted = len(content_traces)

    draft_attempt_total = sum(len(t.draft_attempts) for t in content_traces)
    if draft_attempt_total > 0:
        generation_attempts = draft_attempt_total
        attempts_source = "graph_traces"
    elif evidence.provider_calls:
        generation_attempts = len(evidence.provider_calls)
        attempts_source = "provider_calls"
    else:
        generation_attempts = 0
        attempts_source = "graph_traces"

    successful_count = sum(1 for t in content_traces if t.turn_outcome == "VERIFIED_READY")
    rewrite_count = sum(int(t.retries_used) for t in content_traces)
    turns_with_retries = sum(1 for t in content_traces if t.retries_used > 0)
    budget_violations = sum(1 for t in content_traces if t.retries_used > t.max_retries)
    fallback_count = sum(
        1 for t in content_traces if t.used_fallback or t.turn_outcome == "FALLBACK_PREAPPROVED"
    )
    safe_abort_count = sum(
        1 for t in content_traces if t.turn_outcome == "SAFE_ABORT_NO_CANDIDATE"
    )

    results["generation_attempts"] = MetricResult(
        name="generation_attempts",
        status=MetricStatus.COMPUTED,
        value=generation_attempts,
        unit="counts",
        data_source=attempts_source,
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
    )
    results["successful_candidate_count"] = MetricResult(
        name="successful_candidate_count",
        status=MetricStatus.COMPUTED,
        value=successful_count,
        unit="counts",
        data_source="graph_traces",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
    )
    results["rewrite_count"] = MetricResult(
        name="rewrite_count",
        status=MetricStatus.COMPUTED,
        value=rewrite_count,
        unit="counts",
        data_source="graph_traces",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
    )
    results["retry_budget_violations"] = MetricResult(
        name="retry_budget_violations",
        status=MetricStatus.COMPUTED,
        value=budget_violations,
        unit="counts",
        data_source="graph_traces",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
    )
    results["fallback_count"] = MetricResult(
        name="fallback_count",
        status=MetricStatus.COMPUTED,
        value=fallback_count,
        unit="counts",
        data_source="graph_traces",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
    )
    results["safe_abort_count"] = MetricResult(
        name="safe_abort_count",
        status=MetricStatus.COMPUTED,
        value=safe_abort_count,
        unit="counts",
        data_source="graph_traces",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
        metadata={"termination_boundary_turns_excluded": termination_boundary_turns_excluded},
    )

    if turns_attempted == 0:
        no_turns_reason = "No substantive graph traces recorded (turns_attempted == 0)."
        for name, unit in (
            ("rewrite_rate", "ratio"),
            ("attempts_per_turn_mean", "attempts"),
            ("attempts_per_turn_p50", "attempts"),
            ("attempts_per_turn_p95", "attempts"),
            ("attempts_per_turn_max", "attempts"),
            ("fallback_rate", "ratio"),
            ("safe_abort_rate", "ratio"),
        ):
            results[name] = MetricResult(
                name=name,
                status=MetricStatus.NOT_EVALUATED,
                value=None,
                unit=unit,
                data_source="graph_traces",
                provenance=MetricProvenance.UNAVAILABLE,
                is_simulated=False,
                missing_reason=no_turns_reason,
                metadata={"termination_boundary_turns_excluded": termination_boundary_turns_excluded},
            )
    else:
        method_name = str(evidence.manifest.get("method", "")).strip()
        per_turn_attempts = [
            float(len(t.draft_attempts)) if t.draft_attempts else float(1 + t.retries_used)
            for t in content_traces
        ]
        results["rewrite_rate"] = MetricResult(
            name="rewrite_rate",
            status=MetricStatus.COMPUTED,
            value=turns_with_retries / turns_attempted,
            unit="ratio",
            numerator=float(turns_with_retries),
            denominator=float(turns_attempted),
            data_source="graph_traces",
            provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
            is_simulated=False,
            metadata={"termination_boundary_turns_excluded": termination_boundary_turns_excluded},
        )
        if method_name == "script_first_deterministic" and generation_attempts == 0:
            det_reason = "script_first_deterministic performs 0 LLM generation attempts."
            for name in (
                "attempts_per_turn_mean",
                "attempts_per_turn_p50",
                "attempts_per_turn_p95",
                "attempts_per_turn_max",
            ):
                results[name] = MetricResult(
                    name=name,
                    status=MetricStatus.NOT_APPLICABLE,
                    value=None,
                    unit="attempts",
                    data_source="graph_traces",
                    provenance=MetricProvenance.UNAVAILABLE,
                    is_simulated=False,
                    missing_reason=det_reason,
                )
        else:
            results["attempts_per_turn_mean"] = MetricResult(
                name="attempts_per_turn_mean",
                status=MetricStatus.COMPUTED,
                value=sum(per_turn_attempts) / turns_attempted,
                unit="attempts",
                data_source="graph_traces",
                provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
                is_simulated=False,
            )
            results["attempts_per_turn_p50"] = MetricResult(
                name="attempts_per_turn_p50",
                status=MetricStatus.COMPUTED,
                value=compute_percentile(per_turn_attempts, 0.50),
                unit="attempts",
                data_source="graph_traces",
                provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
                is_simulated=False,
            )
            results["attempts_per_turn_p95"] = MetricResult(
                name="attempts_per_turn_p95",
                status=MetricStatus.COMPUTED,
                value=compute_percentile(per_turn_attempts, 0.95),
                unit="attempts",
                data_source="graph_traces",
                provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
                is_simulated=False,
            )
            results["attempts_per_turn_max"] = MetricResult(
                name="attempts_per_turn_max",
                status=MetricStatus.COMPUTED,
                value=max(per_turn_attempts),
                unit="attempts",
                data_source="graph_traces",
                provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
                is_simulated=False,
            )
        results["fallback_rate"] = MetricResult(
            name="fallback_rate",
            status=MetricStatus.COMPUTED,
            value=fallback_count / turns_attempted,
            unit="ratio",
            numerator=float(fallback_count),
            denominator=float(turns_attempted),
            data_source="graph_traces",
            provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
            is_simulated=False,
            metadata={"termination_boundary_turns_excluded": termination_boundary_turns_excluded},
        )
        results["safe_abort_rate"] = MetricResult(
            name="safe_abort_rate",
            status=MetricStatus.COMPUTED,
            value=safe_abort_count / turns_attempted,
            unit="ratio",
            numerator=float(safe_abort_count),
            denominator=float(turns_attempted),
            data_source="graph_traces",
            provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
            is_simulated=False,
            metadata={"termination_boundary_turns_excluded": termination_boundary_turns_excluded},
        )

    # Phân bố lỗi từ errors.jsonl và provider_calls.jsonl
    retryable_counter: Counter[str] = Counter()
    non_retryable_counter: Counter[str] = Counter()
    unknown_retryable_count = 0
    for err in evidence.errors:
        if err.is_retryable is True:
            retryable_counter[err.error_type] += 1
        elif err.is_retryable is False:
            non_retryable_counter[err.error_type] += 1
        else:
            unknown_retryable_count += 1

    results["retryable_failure_distribution"] = MetricResult(
        name="retryable_failure_distribution",
        status=MetricStatus.COMPUTED,
        value=dict(sorted(retryable_counter.items())),
        unit="distribution",
        data_source="errors",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
    )
    results["non_retryable_failure_distribution"] = MetricResult(
        name="non_retryable_failure_distribution",
        status=MetricStatus.COMPUTED,
        value=dict(sorted(non_retryable_counter.items())),
        unit="distribution",
        data_source="errors",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
        metadata={"unknown_retryable_flag_count": unknown_retryable_count},
    )

    provider_error_counter: Counter[str] = Counter()
    for call in evidence.provider_calls:
        if call.error_type is not None:
            provider_error_counter[call.error_type] += 1
    results["provider_error_distribution"] = MetricResult(
        name="provider_error_distribution",
        status=MetricStatus.COMPUTED,
        value=dict(sorted(provider_error_counter.items())),
        unit="distribution",
        data_source="provider_calls",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
    )

    raw_term = evidence.manifest.get("termination_reason")
    term_reason = raw_term.strip() if isinstance(raw_term, str) and raw_term.strip() else None
    if term_reason is None and traces:
        for t in reversed(traces):
            if t.termination_reason is not None:
                term_reason = t.termination_reason
                break

    if term_reason is None:
        results["termination_reason"] = MetricResult(
            name="termination_reason",
            status=MetricStatus.NOT_EVALUATED,
            value=None,
            unit="category",
            data_source="manifest+graph_traces",
            provenance=MetricProvenance.UNAVAILABLE,
            is_simulated=False,
            missing_reason="termination_reason missing in manifest and graph_traces.",
        )
    else:
        results["termination_reason"] = MetricResult(
            name="termination_reason",
            status=MetricStatus.COMPUTED,
            value=term_reason,
            unit="category",
            data_source="manifest",
            provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
            is_simulated=False,
        )

    return results
