"""Gói hệ thống bộ nhớ 4 thành phần và bộ phát hiện lặp (`p06.memory`) cho P06.

1. File này giải quyết vấn đề gì?
   Cung cấp điểm nhập thống nhất cho toàn bộ lớp bộ nhớ phiên (`ShortTermPlayedHistory`,
   `GlobalTopicCoverage`, `SessionViewerContext`, `OptionalSemanticMemory`) và bộ phát hiện lặp
   (`RepetitionDetector`) dùng trong vòng lặp LangGraph và harness mô phỏng.
2. Trách nhiệm chính của module là gì?
   Tái xuất sạch sẽ các lớp, DTO cấu hình/kết quả và hàm chuẩn hóa văn bản tiếng Việt qua `__all__`.
3. Module này liên kết với các thành phần nào?
   Tổng hợp từ `played_history.py`, `topic_coverage.py`, `viewer_context.py`, `semantic_memory.py`
   và `repetition_detector.py`; được tiêu thụ bởi `p06.simulation.playback_harness` và các runner E01–E04.
4. Input và output chính là gì?
   Không xử lý logic runtime; chỉ xuất khẩu API công khai của gói `p06.memory`.
5. Có những constraints hoặc invariants quan trọng nào?
   Mọi thành phần bộ nhớ chỉ được thăng hạng trạng thái đã phát sau khi có `PlaybackCompleted` hợp lệ.
"""

from __future__ import annotations

from p06.memory.played_history import ShortTermPlayedHistory
from p06.memory.repetition_detector import (
    RepetitionAction,
    RepetitionCategory,
    RepetitionCheckResult,
    RepetitionConfig,
    RepetitionDetector,
    normalize_vietnamese_for_repetition,
)
from p06.memory.semantic_memory import (
    NoOpSemanticMemory,
    OptionalSemanticMemory,
    SemanticSimilarityMatch,
)
from p06.memory.topic_coverage import (
    GlobalTopicCoverage,
    TopicCoverageSnapshot,
)
from p06.memory.viewer_context import (
    SessionViewerContext,
    ViewerQuestionRecord,
)

__all__ = [
    "GlobalTopicCoverage",
    "NoOpSemanticMemory",
    "OptionalSemanticMemory",
    "RepetitionAction",
    "RepetitionCategory",
    "RepetitionCheckResult",
    "RepetitionConfig",
    "RepetitionDetector",
    "SemanticSimilarityMatch",
    "SessionViewerContext",
    "ShortTermPlayedHistory",
    "TopicCoverageSnapshot",
    "ViewerQuestionRecord",
    "normalize_vietnamese_for_repetition",
]
