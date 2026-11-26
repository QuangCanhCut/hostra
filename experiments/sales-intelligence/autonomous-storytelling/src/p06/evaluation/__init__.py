"""Gói đánh giá thực nghiệm P06 (`p06.evaluation`).

1. File này giải quyết vấn đề gì?
   Cung cấp điểm nhập duy nhất cho các hợp đồng đánh giá, 5 nhóm chỉ số tự động,
   bộ nạp và đánh giá từ raw evidence (`evaluator`), bộ so sánh đa cấu hình (`comparison`),
   và bộ xuất phiếu chấm mù cho con người (`human_eval`).
2. Trách nhiệm chính của module là gì?
   Tái xuất các mô hình Pydantic v2 khóa chặt trong `models.py`, các hàm tính metric trong
   `metrics/`, cùng các hàm điều phối cấp cao tại gốc gói `p06.evaluation`.
3. Module này liên kết với các thành phần nào?
   Liên kết với `p06.schemas`, `p06.memory.repetition_detector`, và `evaluation/rubrics/human_eval_rubric_v0.1.md`.
4. Input và output chính là gì?
   Input là `RunEvidence` hoặc thư mục `runs/p06_e01/<run_id>/`;
   Output là `EvaluationReport`, `ComparisonReport` và các tệp phiếu chấm mù.
5. Có những constraints hoặc invariants quan trọng nào?
   - Không dùng `0` thay cho dữ liệu thiếu (`NOT_EVALUATED` / `NOT_APPLICABLE` / `INVALID` -> `value=None`).
   - Không gộp số liệu giữa `Mock` (`unit_test`), `Ollama` (`local_smoke_test`) và `Gemini` (`formal_experiment`).
"""

from __future__ import annotations

from p06.evaluation.comparison import (
    compare_runs,
    export_comparison_csv,
    export_comparison_json,
    export_comparison_markdown,
)
from p06.evaluation.evaluator import (
    evaluate_run,
    evaluate_run_directory,
    load_run_evidence,
)
from p06.evaluation.human_eval import (
    export_blind_human_eval_sheets,
    export_human_eval_sheets,
)
from p06.evaluation.metrics import (
    compute_coverage_metrics,
    compute_percentile,
    compute_performance_metrics,
    compute_reliability_metrics,
    compute_repetition_metrics,
    compute_safety_metrics,
)
from p06.evaluation.models import (
    ComparisonReport,
    ComparisonRow,
    CompatibilityIssue,
    ErrorRecord,
    EvaluationReport,
    GoldFactualLabel,
    GraphTraceRecord,
    HumanEvalBlindMapping,
    HumanEvalSheetEntry,
    MetricProvenance,
    MetricResult,
    MetricStatus,
    PlaybackEventRecord,
    ProviderCallRecord,
    RunEvidence,
    TranscriptEntry,
    is_clean_termination_boundary_trace,
)

__all__ = [
    "ComparisonReport",
    "ComparisonRow",
    "CompatibilityIssue",
    "ErrorRecord",
    "EvaluationReport",
    "GoldFactualLabel",
    "GraphTraceRecord",
    "HumanEvalBlindMapping",
    "HumanEvalSheetEntry",
    "MetricProvenance",
    "MetricResult",
    "MetricStatus",
    "PlaybackEventRecord",
    "ProviderCallRecord",
    "RunEvidence",
    "TranscriptEntry",
    "compare_runs",
    "compute_coverage_metrics",
    "compute_percentile",
    "compute_performance_metrics",
    "compute_reliability_metrics",
    "compute_repetition_metrics",
    "compute_safety_metrics",
    "evaluate_run",
    "evaluate_run_directory",
    "export_blind_human_eval_sheets",
    "export_comparison_csv",
    "export_comparison_json",
    "export_comparison_markdown",
    "export_human_eval_sheets",
    "is_clean_termination_boundary_trace",
    "load_run_evidence",
]
