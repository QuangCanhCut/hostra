"""Ngữ cảnh người xem phạm vi một phiên (`SessionViewerContext`) — placeholder tối thiểu cho E01.

1. File này giải quyết vấn đề gì?
   Cung cấp phần khung tối thiểu trong kiến trúc 4-part memory (`PlayedHistory`, `TopicCoverage`,
   `ViewerContext`, `SemanticMemory`) cho các thí nghiệm E01–E03 mà không vi phạm quyết định
   `D11`/`D23` (không lưu PII, không lập hồ sơ người dùng, không lưu chéo phiên).
2. Trách nhiệm chính của module là gì?
   Lưu giữ danh sách câu hỏi ẩn danh tạm thời trong phiên (`ViewerQuestionRecord`) gắn chặt với
   `(tenant_id, session_id, session_epoch)`, cho phép kiểm tra `is_empty` và xóa sạch qua `clear()`.
3. Module này liên kết với các thành phần nào?
   Thuộc gói `p06.memory`, sử dụng kiểu `NonBlankStr`, `OptionalNonBlankStr`, `StrictPositiveInt`
   từ `p06.schemas.story` và có thể gắn tùy chọn vào `SimulatedPlaybackHarness`.
4. Input và output chính là gì?
   Input là `question_id`, `question_text`, `recorded_at`, `topic_hint`;
   Output là `tuple[ViewerQuestionRecord, ...]` chỉ tồn tại trong bộ nhớ của phiên hiện hành.
5. Có những constraints hoặc invariants quan trọng nào?
   - Mặc định rỗng trong E01 (không có người xem/comment).
   - Tuyệt đối không chứa PII (`user_id`, `nickname`, `phone`, `ip`), không phân loại comment
     (thuộc P07), không profiling người xem và không lưu trữ liên phiên (`D11`/`D23`).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from p06.schemas.story import NonBlankStr, OptionalNonBlankStr


class ViewerQuestionRecord(BaseModel):
    """Bản ghi câu hỏi tối giản phi PII trong một phiên live (không lưu danh tính người xem).

    Attributes:
        question_id: Mã định danh câu hỏi trong phiên.
        question_text: Nội dung câu hỏi thuần văn bản (cấm rỗng).
        recorded_at: Thời điểm ghi nhận câu hỏi trong phiên.
        topic_hint: Gợi ý `topic_id` liên quan (nếu có).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    question_id: NonBlankStr
    question_text: NonBlankStr
    recorded_at: datetime
    topic_hint: OptionalNonBlankStr = None


class SessionViewerContext:
    """Bộ nhớ ngữ cảnh người xem giới hạn trong đúng một phiên (`tenant_id, session_id, session_epoch`).

    Ở E01, ngữ cảnh này luôn rỗng mặc định; cấu trúc chỉ giữ vai trò điểm nối sạch cho E03
    mà không thu thập PII hay tạo hồ sơ liên phiên.
    """

    def __init__(self, tenant_id: str, session_id: str, session_epoch: int) -> None:
        """Khởi tạo ngữ cảnh người xem trống cho một phiên cụ thể.

        Args:
            tenant_id: Mã tenant sở hữu phiên.
            session_id: Mã phiên livestream hiện hành.
            session_epoch: Thế hệ phiên >= 1 (từ chối `bool`).

        Raises:
            ValueError: Nếu `tenant_id`/`session_id` rỗng hoặc `session_epoch < 1`.
        """
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise ValueError("tenant_id không được rỗng.")
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id không được rỗng.")
        if isinstance(session_epoch, bool) or not isinstance(session_epoch, int) or session_epoch < 1:
            raise ValueError(
                f"session_epoch phải là số nguyên >= 1, nhận được {session_epoch!r}."
            )

        self._tenant_id: str = tenant_id.strip()
        self._session_id: str = session_id.strip()
        self._session_epoch: int = session_epoch
        self._questions: list[ViewerQuestionRecord] = []
        self._seen_question_ids: set[str] = set()

    @property
    def tenant_id(self) -> str:
        """Mã tenant gắn với ngữ cảnh người xem."""
        return self._tenant_id

    @property
    def session_id(self) -> str:
        """Mã phiên gắn với ngữ cảnh người xem."""
        return self._session_id

    @property
    def session_epoch(self) -> int:
        """Thế hệ phiên gắn với ngữ cảnh người xem."""
        return self._session_epoch

    @property
    def questions(self) -> tuple[ViewerQuestionRecord, ...]:
        """Danh sách bất biến các câu hỏi đã ghi nhận trong phiên hiện hành."""
        return tuple(self._questions)

    @property
    def is_empty(self) -> bool:
        """Cho biết ngữ cảnh người xem hiện có đang rỗng hay không (mặc định `True` ở E01)."""
        return len(self._questions) == 0

    def record_question(
        self,
        question_id: str,
        question_text: str,
        *,
        recorded_at: datetime,
        topic_hint: Optional[str] = None,
    ) -> ViewerQuestionRecord:
        """Ghi nhận một câu hỏi phi PII vào ngữ cảnh tạm thời của phiên.

        Args:
            question_id: Mã câu hỏi duy nhất trong phiên.
            question_text: Nội dung câu hỏi (không chứa thông tin định danh cá nhân).
            recorded_at: Thời điểm ghi nhận.
            topic_hint: Gợi ý chủ đề liên quan (tùy chọn).

        Returns:
            ViewerQuestionRecord: Bản ghi đã được kiểm định và lưu vào phiên.

        Raises:
            ValueError: Nếu `question_id` bị trùng lặp trong cùng phiên.
            ValidationError: Nếu các trường không đạt ràng buộc schema.
        """
        record = ViewerQuestionRecord(
            question_id=question_id,
            question_text=question_text,
            recorded_at=recorded_at,
            topic_hint=topic_hint,
        )
        if record.question_id in self._seen_question_ids:
            raise ValueError(
                f"question_id '{record.question_id}' đã tồn tại trong SessionViewerContext."
            )
        self._seen_question_ids.add(record.question_id)
        self._questions.append(record)
        return record

    def clear(self) -> None:
        """Xóa toàn bộ câu hỏi tạm trong bộ nhớ khi kết thúc hoặc đặt lại phiên."""
        self._questions.clear()
        self._seen_question_ids.clear()
