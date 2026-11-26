"""Bộ nhớ ngắn hạn theo cửa sổ trượt (`ShortTermPlayedHistory`) cho lượt đã phát thực sự.

1. File này giải quyết vấn đề gì?
   Cung cấp cửa sổ `W ∈ {5, 10, 20}` (tối đa `MAX_PLAYED_HISTORY_WINDOW`) lượt phát gần nhất
   để đưa vào prompt/state của LangGraph nhằm chống lặp ngôn từ, đồng thời vẫn giữ nguyên toàn bộ
   lịch sử phiên và các tập chống trùng (`playback_event_id`, `turn_id`, `chunk_id`) không bị rơi mất
   khi cửa sổ trượt tiến lên.
2. Trách nhiệm chính của module là gì?
   Quản lý `ShortTermPlayedHistory` với kiểm định kích thước cửa sổ, cô lập ngữ cảnh phiên
   (`tenant_id`, `session_id`, `session_epoch`), chống trùng lặp ID sự kiện/lượt trên toàn phiên,
   và chuyển đổi cửa sổ sang `AgentState.played_history`.
3. Module này liên kết với các thành phần nào?
   Sử dụng `PlayedTurnSummary`, `DEFAULT_PLAYED_HISTORY_WINDOW`, `MAX_PLAYED_HISTORY_WINDOW` từ
   `p06.schemas.state`, được dùng bởi `SimulatedPlaybackHarness` (`p06.simulation`) và `RepetitionDetector`.
4. Input và output chính là gì?
   Input là các bản ghi `PlayedTurnSummary` đã được xác nhận qua `PlaybackCompleted`;
   Output là lát cắt cửa sổ `recent_turns()` / `to_agent_state_window()`, toàn bộ lịch sử `all_turns()`,
   và các truy vấn tra cứu chống lặp toàn phiên (`has_chunk_been_played`, `has_event`, `has_turn`).
5. Có những constraints hoặc invariants quan trọng nào?
   - Chỉ nhận lượt đã phát thực sự (`PlayedTurnSummary`); bản nháp chưa phát không được phép nạp.
   - Khi cửa sổ trượt đẩy lượt cũ ra khỏi `recent_turns()`, các tập `seen_event_ids`, `seen_turn_ids`
     và `completed_chunk_ids` tuyệt đối không được mất dữ liệu (tránh replay mù sau > W lượt).
   - Từ chối `bool` khi kiểm định `window_size` hoặc `session_epoch`.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Optional

from p06.schemas.state import (
    DEFAULT_PLAYED_HISTORY_WINDOW,
    MAX_PLAYED_HISTORY_WINDOW,
    PlayedTurnSummary,
)


def _validate_window_size(value: int) -> int:
    """Kiểm định kích thước cửa sổ `W` nằm trong biên an toàn và từ chối kiểu `bool`.

    Args:
        value: Kích thước cửa sổ `W` (hỗ trợ cấu hình YAML như 5, 10, 20).

    Returns:
        int: Kích thước cửa sổ hợp lệ trong `[1, MAX_PLAYED_HISTORY_WINDOW]`.

    Raises:
        ValueError: Nếu `value` là `bool`, không phải `int`, hoặc nằm ngoài biên hợp lệ.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"window_size phải là số nguyên thuần túy, nhận được {type(value).__name__}."
        )
    if not (1 <= value <= MAX_PLAYED_HISTORY_WINDOW):
        raise ValueError(
            f"window_size phải nằm trong [1, {MAX_PLAYED_HISTORY_WINDOW}], nhận được {value}."
        )
    return value


def _validate_optional_non_blank(value: Optional[str], field_name: str) -> Optional[str]:
    """Kiểm định mã định danh ngữ cảnh tùy chọn (cho phép `None`, cấm chuỗi rỗng)."""
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} phải là chuỗi khác rỗng hoặc None.")
    return value.strip()


def _validate_optional_epoch(value: Optional[int], field_name: str = "session_epoch") -> Optional[int]:
    """Kiểm định `session_epoch` tùy chọn: chỉ nhận số nguyên >= 1, từ chối `bool`."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} phải là số nguyên >= 1 hoặc None, nhận được {value!r}.")
    return value


class ShortTermPlayedHistory:
    """Bộ nhớ ngắn hạn theo cửa sổ trượt `W` kèm tập chống lặp bất biến trên toàn phiên.

    Cấu trúc này tách biệt giữa hai lớp dữ liệu:
    - Toàn bộ chuỗi lượt đã phát (`_all_turns`) và các tập chống trùng (`_seen_event_ids`,
      `_seen_turn_ids`, `_completed_chunk_ids`) được giữ nguyên suốt phiên.
    - Lát cắt cửa sổ `W` gần nhất (`recent_turns()`, `to_agent_state_window()`) phục vụ prompt
      và `AgentState` mà không đánh mất dấu vết chống replay các chunk cũ hơn `W`.
    """

    def __init__(
        self,
        window_size: int = DEFAULT_PLAYED_HISTORY_WINDOW,
        *,
        tenant_id: Optional[str] = None,
        session_id: Optional[str] = None,
        session_epoch: Optional[int] = None,
        initial_turns: Iterable[PlayedTurnSummary] = (),
    ) -> None:
        """Khởi tạo bộ nhớ ngắn hạn với kích thước cửa sổ `W` và lịch sử ban đầu (nếu có).

        Args:
            window_size: Kích thước cửa sổ trượt `W` (mặc định `DEFAULT_PLAYED_HISTORY_WINDOW`).
            tenant_id: Mã tenant ràng buộc (nếu truyền thì kiểm tra đồng nhất khi nạp lượt mới).
            session_id: Mã phiên livestream ràng buộc (tùy chọn).
            session_epoch: Thế hệ phiên ràng buộc >= 1 (tùy chọn).
            initial_turns: Dòng lượt `PlayedTurnSummary` khởi tạo khi phục hồi phiên.

        Raises:
            ValueError: Nếu `window_size` sai biên, ngữ cảnh không hợp lệ, hoặc `initial_turns`
                chứa `playback_event_id`/`turn_id` trùng lặp.
            TypeError: Nếu phần tử trong `initial_turns` không phải `PlayedTurnSummary`.
        """
        self._window_size: int = _validate_window_size(window_size)
        self._tenant_id: Optional[str] = _validate_optional_non_blank(tenant_id, "tenant_id")
        self._session_id: Optional[str] = _validate_optional_non_blank(session_id, "session_id")
        self._session_epoch: Optional[int] = _validate_optional_epoch(session_epoch)

        self._all_turns: list[PlayedTurnSummary] = []
        self._seen_event_ids: set[str] = set()
        self._seen_turn_ids: set[str] = set()
        self._completed_chunk_ids: set[str] = set()

        # Chuẩn bị và kiểm định toàn bộ initial_turns trước khi ghi để giữ trạng thái nhất quán.
        for turn in initial_turns:
            self.append_confirmed_turn(turn)

    @property
    def window_size(self) -> int:
        """Kích thước cửa sổ trượt `W` hiện tại."""
        return self._window_size

    @property
    def tenant_id(self) -> Optional[str]:
        """Mã tenant gắn với bộ nhớ này (hoặc `None` nếu không khóa ở mức memory)."""
        return self._tenant_id

    @property
    def session_id(self) -> Optional[str]:
        """Mã phiên gắn với bộ nhớ này (hoặc `None` nếu không khóa ở mức memory)."""
        return self._session_id

    @property
    def session_epoch(self) -> Optional[int]:
        """Thế hệ phiên gắn với bộ nhớ này (hoặc `None` nếu không khóa ở mức memory)."""
        return self._session_epoch

    @property
    def seen_event_ids(self) -> frozenset[str]:
        """Tập toàn bộ `playback_event_id` đã ghi nhận trong phiên (không bị cắt bởi cửa sổ)."""
        return frozenset(self._seen_event_ids)

    @property
    def seen_turn_ids(self) -> frozenset[str]:
        """Tập toàn bộ `turn_id` đã ghi nhận trong phiên (không bị cắt bởi cửa sổ)."""
        return frozenset(self._seen_turn_ids)

    @property
    def completed_chunk_ids(self) -> frozenset[str]:
        """Tập toàn bộ `chunk_id` đã phát xong trong phiên (không bị mất khi trượt cửa sổ)."""
        return frozenset(self._completed_chunk_ids)

    def __len__(self) -> int:
        """Trả về tổng số lượt đã phát thực sự trong toàn phiên."""
        return len(self._all_turns)

    def append_confirmed_turn(
        self,
        summary: PlayedTurnSummary,
        *,
        tenant_id: Optional[str] = None,
        session_id: Optional[str] = None,
        session_epoch: Optional[int] = None,
    ) -> None:
        """Nạp một lượt đã xác nhận phát sóng (`PlayedTurnSummary`) vào bộ nhớ ngắn hạn.

        Args:
            summary: Bản tóm tắt lượt phát trích xuất từ `PlaybackCompleted`.
            tenant_id: Mã tenant của sự kiện nguồn (nếu có để đối chiếu chống rò rỉ R10).
            session_id: Mã phiên của sự kiện nguồn (nếu có).
            session_epoch: Thế hệ phiên của sự kiện nguồn (nếu có).

        Raises:
            TypeError: Nếu `summary` không phải `PlayedTurnSummary`.
            ValueError: Nếu trùng `playback_event_id`/`turn_id` hoặc lệch ngữ cảnh phiên đã khóa.
        """
        if not isinstance(summary, PlayedTurnSummary):
            raise TypeError(
                f"Chỉ được nạp PlayedTurnSummary vào ShortTermPlayedHistory, nhận được {type(summary).__name__}."
            )

        clean_tenant = _validate_optional_non_blank(tenant_id, "tenant_id")
        clean_session = _validate_optional_non_blank(session_id, "session_id")
        valid_epoch = _validate_optional_epoch(session_epoch)

        if self._tenant_id is not None and clean_tenant is not None and clean_tenant != self._tenant_id:
            raise ValueError(
                f"Lệch tenant_id khi nạp PlayedTurnSummary: nhận '{clean_tenant}', "
                f"kỳ vọng '{self._tenant_id}'."
            )
        if self._session_id is not None and clean_session is not None and clean_session != self._session_id:
            raise ValueError(
                f"Lệch session_id khi nạp PlayedTurnSummary: nhận '{clean_session}', "
                f"kỳ vọng '{self._session_id}'."
            )
        if self._session_epoch is not None and valid_epoch is not None and valid_epoch != self._session_epoch:
            raise ValueError(
                f"Lệch session_epoch khi nạp PlayedTurnSummary: nhận {valid_epoch}, "
                f"kỳ vọng {self._session_epoch}."
            )

        if summary.playback_event_id in self._seen_event_ids:
            raise ValueError(
                f"playback_event_id '{summary.playback_event_id}' đã tồn tại trong ShortTermPlayedHistory."
            )
        if summary.turn_id in self._seen_turn_ids:
            raise ValueError(
                f"turn_id '{summary.turn_id}' đã tồn tại trong ShortTermPlayedHistory."
            )

        self._all_turns.append(summary)
        self._seen_event_ids.add(summary.playback_event_id)
        self._seen_turn_ids.add(summary.turn_id)
        if summary.chunk_id is not None:
            self._completed_chunk_ids.add(summary.chunk_id)

    def recent_turns(self) -> tuple[PlayedTurnSummary, ...]:
        """Trả về tối đa `W` lượt phát gần nhất theo đúng thứ tự thời gian."""
        return tuple(self._all_turns[-self._window_size :])

    def all_turns(self) -> tuple[PlayedTurnSummary, ...]:
        """Trả về toàn bộ các lượt đã phát trong phiên từ đầu đến hiện tại."""
        return tuple(self._all_turns)

    def to_agent_state_window(self) -> list[PlayedTurnSummary]:
        """Xuất danh sách `<= W` lượt gần nhất tương thích trường `AgentState.played_history`."""
        return list(self._all_turns[-self._window_size :])

    def has_chunk_been_played(self, chunk_id: str) -> bool:
        """Kiểm tra `chunk_id` đã từng phát trong phiên hay chưa (kể cả ngoài cửa sổ `W`)."""
        if not isinstance(chunk_id, str) or not chunk_id.strip():
            return False
        return chunk_id.strip() in self._completed_chunk_ids

    def has_event(self, event_id: str) -> bool:
        """Kiểm tra `playback_event_id` đã từng được ghi nhận hay chưa."""
        if not isinstance(event_id, str) or not event_id.strip():
            return False
        return event_id.strip() in self._seen_event_ids

    def has_turn(self, turn_id: str) -> bool:
        """Kiểm tra `turn_id` đã từng được ghi nhận hay chưa."""
        if not isinstance(turn_id, str) or not turn_id.strip():
            return False
        return turn_id.strip() in self._seen_turn_ids

    def with_window_size(self, new_window_size: int) -> ShortTermPlayedHistory:
        """Tạo bản sao `ShortTermPlayedHistory` mới với kích thước cửa sổ `W` khác nhưng giữ đủ lịch sử.

        Lý do kỹ thuật: Khi chạy thí nghiệm sensitivity (`W ∈ {5, 10, 20}`), việc đổi `W`
        chỉ được thay đổi độ dài lát cắt `recent_turns()`, tuyệt đối không làm rơi lịch sử
        và các tập chống trùng của toàn phiên.

        Args:
            new_window_size: Kích thước cửa sổ `W` mới trong `[1, MAX_PLAYED_HISTORY_WINDOW]`.

        Returns:
            ShortTermPlayedHistory: Thực thể độc lập mang toàn bộ lịch sử và tập chống trùng hiện có.

        Raises:
            ValueError: Nếu `new_window_size` không hợp lệ.
        """
        return ShortTermPlayedHistory(
            window_size=new_window_size,
            tenant_id=self._tenant_id,
            session_id=self._session_id,
            session_epoch=self._session_epoch,
            initial_turns=self._all_turns,
        )
