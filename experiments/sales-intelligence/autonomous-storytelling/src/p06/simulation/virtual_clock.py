"""Đồng hồ ảo tất định (`VirtualClock`) phục vụ mô phỏng phiên live 10–30 phút không dùng `sleep()`.

1. File này giải quyết vấn đề gì?
   Cho phép chạy thí nghiệm mô phỏng phiên livestream dài 10–30 phút (`P06-E01..E04`) chỉ trong
   vài mili-giây CPU thật với mốc thời gian UTC hoàn toàn tất định và tái lập được 100%.
2. Trách nhiệm chính của module là gì?
   Quản lý con trỏ thời gian ảo (`now()`, `advance_ms()`, `advance_sec()`, `elapsed_sec()`)
   và ước lượng thời lượng phát tiếng nói (`estimate_speech_duration_ms()`) theo tốc độ đọc tiếng Việt.
3. Module này liên kết với các thành phần nào?
   Được sử dụng bởi `MockPlaybackAckBus` (`adapters/mocks/playback_bus.py`) để sinh dấu thời gian
   `occurred_at` tăng đơn điệu cho `PlaybackCompleted`, và bởi `SimulatedPlaybackHarness`.
4. Input và output chính là gì?
   Input là thời điểm khởi đầu UTC tùy chọn, bước nhảy thời gian (ms/s) hoặc văn bản lời thoại;
   Output là đối tượng `datetime` (UTC) và thời lượng ước lượng tính bằng mili-giây.
5. Có những constraints hoặc invariants quan trọng nào?
   - Tuyệt đối không sử dụng `time.sleep()` hay đồng hồ hệ thống không kiểm soát khi đang chạy mô phỏng.
   - Thời gian chỉ tịnh tiến không giảm (`>= 0`); mọi giá trị âm, `bool` hoặc `NaN`/`Inf` đều bị từ chối.
   - Bắt buộc dùng `datetime` có múi giờ (UTC) để tương thích chặt với `p06.schemas`.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Final, Optional

# Tốc độ nói tiếng Việt trung bình tự nhiên trong livestream (~155 từ/phút ≈ 2.6 từ/giây).
DEFAULT_SPEECH_WORDS_PER_SEC: Final[float] = 2.6
MIN_SPEECH_DURATION_MS: Final[int] = 1000
MAX_SPEECH_DURATION_MS: Final[int] = 30000
MS_PER_SECOND: Final[int] = 1000

# Mốc thời gian khởi tạo mặc định tất định phục vụ kiểm thử tái lập.
DEFAULT_VIRTUAL_START_AT: Final[datetime] = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)


class VirtualClock:
    """Đồng hồ ảo UTC tất định phục vụ mô phỏng phát sóng và kiểm thử bất biến thời gian."""

    def __init__(self, start_at: Optional[datetime] = None) -> None:
        """Khởi tạo đồng hồ ảo tại một mốc thời gian UTC xác định.

        Args:
            start_at: Thời điểm bắt đầu (bắt buộc có `tzinfo`); mặc định dùng `DEFAULT_VIRTUAL_START_AT`.

        Raises:
            ValueError: Nếu `start_at` không có thông tin múi giờ (`tzinfo is None`).
        """
        if start_at is None:
            resolved = DEFAULT_VIRTUAL_START_AT
        else:
            if start_at.tzinfo is None:
                raise ValueError("VirtualClock yêu cầu start_at phải là datetime có múi giờ (UTC).")
            resolved = start_at.astimezone(timezone.utc)

        self._start_at: datetime = resolved
        self._current_at: datetime = resolved

    @property
    def start_at(self) -> datetime:
        """Thời điểm khởi đầu của đồng hồ ảo (UTC)."""
        return self._start_at

    def now(self) -> datetime:
        """Trả về dấu thời gian hiện tại của đồng hồ ảo (UTC)."""
        return self._current_at

    def advance_ms(self, milliseconds: int) -> datetime:
        """Tịnh tiến đồng hồ ảo thêm một khoảng mili-giây không âm.

        Args:
            milliseconds: Số mili-giây cần cộng thêm (`int >= 0`, cấm `bool`).

        Returns:
            datetime: Dấu thời gian UTC mới sau khi tịnh tiến.

        Raises:
            ValueError: Nếu `milliseconds` là `bool`, không phải `int` hoặc nhỏ hơn `0`.
        """
        if isinstance(milliseconds, bool) or not isinstance(milliseconds, int):
            raise ValueError(
                f"milliseconds phải là int thuần túy, nhận được {type(milliseconds).__name__}."
            )
        if milliseconds < 0:
            raise ValueError(f"Không thể lùi đồng hồ ảo: milliseconds={milliseconds} < 0.")
        self._current_at = self._current_at + timedelta(milliseconds=milliseconds)
        return self._current_at

    def advance_sec(self, seconds: float) -> datetime:
        """Tịnh tiến đồng hồ ảo thêm một khoảng giây không âm.

        Args:
            seconds: Số giây cần cộng thêm (`int`/`float >= 0`, hữu hạn, cấm `bool`).

        Returns:
            datetime: Dấu thời gian UTC mới sau khi tịnh tiến.

        Raises:
            ValueError: Nếu `seconds` là `bool`, không hữu hạn hoặc nhỏ hơn `0`.
        """
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
            raise ValueError(
                f"seconds phải là int hoặc float thuần túy, nhận được {type(seconds).__name__}."
            )
        numeric = float(seconds)
        if not math.isfinite(numeric) or numeric < 0.0:
            raise ValueError(f"seconds phải hữu hạn và >= 0, nhận được {seconds}.")
        ms = int(round(numeric * MS_PER_SECOND))
        return self.advance_ms(ms)

    def elapsed_sec(self) -> float:
        """Trả về tổng số giây đã trôi qua kể từ `start_at`."""
        return (self._current_at - self._start_at).total_seconds()

    @staticmethod
    def estimate_speech_duration_ms(
        text: str,
        words_per_sec: float = DEFAULT_SPEECH_WORDS_PER_SEC,
    ) -> int:
        """Ước lượng thời lượng phát tiếng nói (ms) một cách tất định từ số từ trong lời thoại.

        Lý do thiết kế: Thay vì chờ phát âm thanh thực tế hay dùng `sleep()`, mô phỏng quy đổi số từ
        sang mili-giây và kẹp trong `[MIN_SPEECH_DURATION_MS, MAX_SPEECH_DURATION_MS]` để bảo toàn
        giới hạn chunk `<= 30s`.

        Args:
            text: Văn bản lời thoại cần ước lượng thời lượng.
            words_per_sec: Tốc độ đọc giả định (từ/giây, phải `> 0`).

        Returns:
            int: Thời lượng ước lượng tính bằng mili-giây.

        Raises:
            ValueError: Nếu `text` rỗng hoặc `words_per_sec` không hợp lệ.
        """
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text dùng để ước lượng thời lượng không được rỗng.")
        if (
            isinstance(words_per_sec, bool)
            or not isinstance(words_per_sec, (int, float))
            or not math.isfinite(float(words_per_sec))
            or float(words_per_sec) <= 0.0
        ):
            raise ValueError(f"words_per_sec phải là số dương hữu hạn, nhận được {words_per_sec}.")

        word_count = len(text.split())
        raw_ms = int(round((word_count / float(words_per_sec)) * MS_PER_SECOND))
        return max(MIN_SPEECH_DURATION_MS, min(MAX_SPEECH_DURATION_MS, raw_ms))
