"""Gói con chứa các hàm tính 5 trục chỉ số tự động cho P06 (`p06.evaluation.metrics`).

1. File này giải quyết vấn đề gì?
   Cung cấp điểm nhập gọn gàng cho 5 nhóm hàm thuần tính toán metric (`coverage`, `repetition`,
   `safety`, `reliability`, `performance`) cùng hàm nội suy phân vị `compute_percentile`.
2. Trách nhiệm chính của module là gì?
   Tái xuất các hàm công khai từ 5 module con thuộc `p06.evaluation.metrics`.
3. Module này liên kết với các thành phần nào?
   Được sử dụng bởi `p06.evaluation.evaluator` và các bài kiểm thử đơn vị.
4. Input và output chính là gì?
   Input của các hàm tính toán là `RunEvidence` (và `gold_labels` cho `safety`);
   Output là `dict[str, MetricResult]`.
5. Có những constraints hoặc invariants quan trọng nào?
   - Tất cả hàm tính metric đều thuần hàm (pure functions), không sửa đổi `RunEvidence` đầu vào.
"""

from __future__ import annotations

from p06.evaluation.metrics.coverage import compute_coverage_metrics
from p06.evaluation.metrics.performance import (
    compute_percentile,
    compute_performance_metrics,
)
from p06.evaluation.metrics.reliability import compute_reliability_metrics
from p06.evaluation.metrics.repetition import compute_repetition_metrics
from p06.evaluation.metrics.safety import compute_safety_metrics

__all__ = [
    "compute_coverage_metrics",
    "compute_percentile",
    "compute_performance_metrics",
    "compute_reliability_metrics",
    "compute_repetition_metrics",
    "compute_safety_metrics",
]
