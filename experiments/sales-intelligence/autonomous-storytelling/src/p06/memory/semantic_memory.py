"""Giao diện bộ nhớ ngữ nghĩa tùy chọn (`OptionalSemanticMemory`) và triển khai rỗng `NoOpSemanticMemory`.

1. File này giải quyết vấn đề gì?
   Chuẩn hóa điểm mở rộng cho thành phần thứ 4 trong hệ nhớ (`SemanticMemory`) mà không kéo theo
   embedding model, pgvector hay API ngoài vào baseline E01 khi chưa có bằng chứng kiểm chứng
   lợi ích vượt trội so với `ShortTermPlayedHistory` + `RepetitionDetector` (`P06-OPEN-2`).
2. Trách nhiệm chính của module là gì?
   Định nghĩa DTO `SemanticSimilarityMatch`, lớp trừu tượng `OptionalSemanticMemory`, và triển khai
   mặc định `NoOpSemanticMemory` luôn tắt (`is_enabled=False`) để chạy tất định không mạng/không DB.
3. Module này liên kết với các thành phần nào?
   Sử dụng `PlayedTurnSummary` (`p06.schemas.state`) và `NonBlankStr`/`OptionalNonBlankStr` (`p06.schemas.story`);
   được tích hợp tùy chọn vào `SimulatedPlaybackHarness` (`p06.simulation`).
4. Input và output chính là gì?
   Input là `PlayedTurnSummary` (khi index) và chuỗi truy vấn `text`, `top_k` (khi query);
   Output là `tuple[SemanticSimilarityMatch, ...]` (luôn rỗng `()` với `NoOpSemanticMemory`).
5. Có những constraints hoặc invariants quan trọng nào?
   - `NoOpSemanticMemory` không gọi API, không tải embedding, không dùng pgvector và không bịa điểm số giả.
   - `query_similar` vẫn kiểm định `top_k >= 1` (từ chối `bool`) để giữ hợp đồng nhất quán.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict

from p06.schemas.state import PlayedTurnSummary
from p06.schemas.story import NonBlankStr, OptionalNonBlankStr


def _validate_similarity_score(value: Any) -> float:
    """Kiểm định điểm tương đồng ngữ nghĩa nằm trong `[0.0, 1.0]` và từ chối `bool`."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"similarity_score phải là số thực trong [0.0, 1.0], nhận được {type(value).__name__}."
        )
    numeric = float(value)
    if not math.isfinite(numeric) or not (0.0 <= numeric <= 1.0):
        raise ValueError(f"similarity_score phải nằm trong [0.0, 1.0], nhận được {value!r}.")
    return numeric


StrictSimilarityScore = Annotated[float, BeforeValidator(_validate_similarity_score)]


class SemanticSimilarityMatch(BaseModel):
    """Kết quả khớp tương đồng ngữ nghĩa trả về từ một backend `OptionalSemanticMemory`.

    Attributes:
        chunk_id: Mã `StoryChunk` của lượt đã phát khớp nhất (nếu có).
        turn_id: Mã lượt phát sóng tương ứng.
        similarity_score: Điểm tương đồng trong `[0.0, 1.0]`.
        text_excerpt: Đoạn trích lời đã phát phục vụ đối chiếu/giải thích.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    chunk_id: OptionalNonBlankStr = None
    turn_id: NonBlankStr
    similarity_score: StrictSimilarityScore
    text_excerpt: NonBlankStr


class OptionalSemanticMemory(ABC):
    """Giao diện trừu tượng cho bộ nhớ ngữ nghĩa tùy chọn (tắt mặc định ở E01)."""

    @property
    @abstractmethod
    def is_enabled(self) -> bool:
        """Cho biết bộ nhớ ngữ nghĩa hiện có được kích hoạt hay đang ở chế độ no-op."""

    @abstractmethod
    def index_played_turn(self, summary: PlayedTurnSummary) -> None:
        """Đánh chỉ mục một lượt đã phát thực sự (chỉ gọi sau `PlaybackCompleted`)."""

    @abstractmethod
    def query_similar(
        self,
        text: str,
        top_k: int = 3,
    ) -> tuple[SemanticSimilarityMatch, ...]:
        """Truy vấn các lượt phát tương đồng nhất với `text` trong phạm vi `top_k`."""

    @abstractmethod
    def clear(self) -> None:
        """Giải phóng dữ liệu chỉ mục trong phiên hiện tại."""


class NoOpSemanticMemory(OptionalSemanticMemory):
    """Triển khai rỗng không thao tác (`is_enabled=False`) cho giai đoạn E01–E03.

    Không thực hiện gọi API ngoài, không tạo vector nhúng, không kết nối pgvector
    và không trả về điểm tương đồng giả mạo.
    """

    @property
    def is_enabled(self) -> bool:
        """Luôn trả về `False` vì bộ nhớ ngữ nghĩa bị tắt ở baseline E01."""
        return False

    def index_played_turn(self, summary: PlayedTurnSummary) -> None:
        """Bỏ qua đánh chỉ mục một cách an toàn sau khi xác nhận đúng kiểu `PlayedTurnSummary`."""
        if not isinstance(summary, PlayedTurnSummary):
            raise TypeError(
                f"summary phải là PlayedTurnSummary, nhận được {type(summary).__name__}."
            )

    def query_similar(
        self,
        text: str,
        top_k: int = 3,
    ) -> tuple[SemanticSimilarityMatch, ...]:
        """Kiểm định `top_k >= 1` (từ chối `bool`) và luôn trả về tuple rỗng `()`."""
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise ValueError(f"top_k phải là số nguyên >= 1, nhận được {top_k!r}.")
        return ()

    def clear(self) -> None:
        """Không có trạng thái nội bộ để xóa ở chế độ no-op."""
        return None
