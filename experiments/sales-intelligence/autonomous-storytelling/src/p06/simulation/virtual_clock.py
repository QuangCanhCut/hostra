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

from pydantic import BaseModel, ConfigDict

from p06.schemas.story import StrictBool, StrictPositiveInt

# Tốc độ nói tiếng Việt trung bình tự nhiên trong livestream (~155 từ/phút ≈ 2.6 từ/giây).
DEFAULT_SPEECH_WORDS_PER_SEC: Final[float] = 2.6
MIN_SPEECH_DURATION_MS: Final[int] = 1000
MAX_SPEECH_DURATION_MS: Final[int] = 30000
MS_PER_SECOND: Final[int] = 1000

# Mốc thời gian khởi tạo mặc định tất định phục vụ kiểm thử tái lập.
DEFAULT_VIRTUAL_START_AT: Final[datetime] = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)


def _validate_max_duration_ms(max_duration_ms: Optional[int]) -> Optional[int]:
    """Kiểm định tham số ngưỡng thời lượng tối đa (ms), từ chối `bool` và số <= 0."""
    if max_duration_ms is None:
        return None
    if isinstance(max_duration_ms, bool) or not isinstance(max_duration_ms, int) or max_duration_ms <= 0:
        raise ValueError(
            f"max_duration_ms phải là số nguyên dương hoặc None, nhận được {max_duration_ms}."
        )
    return max_duration_ms


class SpeechDurationEstimate(BaseModel):
    """Kết quả ước lượng thời lượng phát tiếng nói kèm thông tin vượt ngưỡng (khắc phục A-MAJ-06).

    Attributes:
        raw_ms: Thời lượng ước lượng thực tế chưa cắt ngầm (`>= MIN_SPEECH_DURATION_MS`).
        clamped_ms: Thời lượng đã kẹp theo `limit_ms` (bằng `raw_ms` nếu `limit_ms is None`).
        exceeds_limit: `True` nếu `limit_ms is not None` và `raw_ms > limit_ms`.
        limit_ms: Ngưỡng giới hạn tối đa (ms) dùng để đối chiếu, hoặc `None` nếu không giới hạn.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    raw_ms: StrictPositiveInt
    clamped_ms: StrictPositiveInt
    exceeds_limit: StrictBool
    limit_ms: Optional[StrictPositiveInt] = None


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
    def _compute_raw_duration_ms(text: str, words_per_sec: float) -> int:
        """Tính thời lượng thô (ms) không kẹp ngưỡng trên từ số từ và tốc độ đọc."""
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
        return max(MIN_SPEECH_DURATION_MS, raw_ms)

    @staticmethod
    def estimate_raw_speech_duration_ms(
        text: str,
        words_per_sec: float = DEFAULT_SPEECH_WORDS_PER_SEC,
    ) -> int:
        """Ước lượng thời lượng phát tiếng nói thực tế (ms) và KHÔNG bao giờ cắt ngầm ở ngưỡng 30s.

        Args:
            text: Văn bản lời thoại cần ước lượng thời lượng.
            words_per_sec: Tốc độ đọc giả định (từ/giây, phải `> 0`).

        Returns:
            int: Thời lượng ước lượng không cắt ngưỡng trên (`>= MIN_SPEECH_DURATION_MS`).

        Raises:
            ValueError: Nếu `text` rỗng hoặc `words_per_sec` không hợp lệ.
        """
        return VirtualClock._compute_raw_duration_ms(text, words_per_sec)

    @staticmethod
    def evaluate_speech_duration(
        text: str,
        words_per_sec: float = DEFAULT_SPEECH_WORDS_PER_SEC,
        max_duration_ms: Optional[int] = MAX_SPEECH_DURATION_MS,
    ) -> SpeechDurationEstimate:
        """Đánh giá thời lượng nói kèm cờ `exceeds_limit` mà không âm thầm cắt mất dữ liệu thật.

        Args:
            text: Văn bản lời thoại cần ước lượng.
            words_per_sec: Tốc độ đọc giả định (từ/giây, phải `> 0`).
            max_duration_ms: Ngưỡng đối chiếu tối đa (ms), mặc định `MAX_SPEECH_DURATION_MS`.

        Returns:
            SpeechDurationEstimate: Kết quả gồm `raw_ms`, `clamped_ms`, `exceeds_limit`, `limit_ms`.

        Raises:
            ValueError: Nếu `text`, `words_per_sec`, hoặc `max_duration_ms` không hợp lệ.
        """
        validated_limit = _validate_max_duration_ms(max_duration_ms)
        raw_ms = VirtualClock._compute_raw_duration_ms(text, words_per_sec)
        if validated_limit is None:
            return SpeechDurationEstimate(
                raw_ms=raw_ms,
                clamped_ms=raw_ms,
                exceeds_limit=False,
                limit_ms=None,
            )
        exceeds = raw_ms > validated_limit
        return SpeechDurationEstimate(
            raw_ms=raw_ms,
            clamped_ms=min(validated_limit, raw_ms),
            exceeds_limit=exceeds,
            limit_ms=validated_limit,
        )

    @staticmethod
    def estimate_speech_duration_ms(
        text: str,
        words_per_sec: float = DEFAULT_SPEECH_WORDS_PER_SEC,
        max_duration_ms: Optional[int] = None,
        enforce_limit: bool = False,
    ) -> int:
        """Ước lượng thời lượng phát tiếng nói (ms) tất định và an toàn không cắt ngầm (A-MAJ-06).

        Lý do thiết kế: Phiên bản trước tự động kẹp về 30.000ms có thể che giấu lỗi LLM sinh
        câu quá dài; hàm mới luôn trả về thời lượng thô thực tế trừ khi `enforce_limit=True`
        yêu cầu ném `ValueError` khi vượt `max_duration_ms`.

        Args:
            text: Văn bản lời thoại cần ước lượng thời lượng.
            words_per_sec: Tốc độ đọc giả định (từ/giây, phải `> 0`).
            max_duration_ms: Ngưỡng kiểm tra tùy chọn (ms) khi `enforce_limit=True`.
            enforce_limit: Nếu `True` và `raw_ms > max_duration_ms`, ném `ValueError` thay vì cắt.

        Returns:
            int: Thời lượng ước lượng thực tế tính bằng mili-giây (`>= MIN_SPEECH_DURATION_MS`).

        Raises:
            ValueError: Nếu `text`/`words_per_sec`/`max_duration_ms` không hợp lệ hoặc vượt ngưỡng khi `enforce_limit=True`.
        """
        validated_limit = _validate_max_duration_ms(max_duration_ms)
        raw_ms = VirtualClock._compute_raw_duration_ms(text, words_per_sec)
        if validated_limit is not None and enforce_limit and raw_ms > validated_limit:
            raise ValueError(
                f"Thời lượng ước lượng ({raw_ms}ms) vượt quá giới hạn cho phép ({validated_limit}ms)."
            )
        return raw_ms


def compute_chunk_word_budget(
    max_duration_sec: float,
    *,
    words_per_sec: float = DEFAULT_SPEECH_WORDS_PER_SEC,
) -> tuple[int, int, str]:
    """Tính ngân sách từ nhất quán trực tiếp từ bộ ước lượng thời lượng `VirtualClock`.

    Args:
        max_duration_sec: Giới hạn thời lượng tối đa của một chunk (giây, `> 0`).
        words_per_sec: Tốc độ đọc giả định (từ/giây, `> 0`).

    Returns:
        tuple[int, int, str]: `(recommended_max_words, hard_max_words, target_words_range)`
            trong đó `hard_max_words` là số từ nguyên lớn nhất bảo đảm thời lượng ước lượng
            `<= max_duration_sec`, còn `recommended_max_words` chừa biên an toàn `2` từ
            (ví dụ với `8.0s` ở `2.6` từ/giây: `(18, 20, '12–18 từ')`).

    Raises:
        ValueError: Nếu `max_duration_sec` hoặc `words_per_sec` không phải số dương hữu hạn.
    """
    if (
        isinstance(max_duration_sec, bool)
        or not isinstance(max_duration_sec, (int, float))
        or not math.isfinite(float(max_duration_sec))
        or float(max_duration_sec) <= 0.0
    ):
        raise ValueError(
            f"max_duration_sec phải là số dương hữu hạn, nhận được {max_duration_sec!r}."
        )
    if (
        isinstance(words_per_sec, bool)
        or not isinstance(words_per_sec, (int, float))
        or not math.isfinite(float(words_per_sec))
        or float(words_per_sec) <= 0.0
    ):
        raise ValueError(
            f"words_per_sec phải là số dương hữu hạn, nhận được {words_per_sec!r}."
        )

    max_ms = int(round(float(max_duration_sec) * MS_PER_SECOND))
    upper_bound = max(1, int(math.floor(float(max_duration_sec) * float(words_per_sec))) + 2)
    hard_max_words = 1
    for candidate_words in range(1, upper_bound + 1):
        est_ms = max(
            MIN_SPEECH_DURATION_MS,
            int(round((candidate_words / float(words_per_sec)) * MS_PER_SECOND)),
        )
        if est_ms <= max_ms:
            hard_max_words = candidate_words
        else:
            break

    recommended_max_words = (
        max(8, hard_max_words - 2) if hard_max_words >= 8 else hard_max_words
    )
    recommended_min_words = min(recommended_max_words, max(8, recommended_max_words - 6))
    target_words_range = f"{recommended_min_words}–{recommended_max_words} từ"
    return recommended_max_words, hard_max_words, target_words_range
