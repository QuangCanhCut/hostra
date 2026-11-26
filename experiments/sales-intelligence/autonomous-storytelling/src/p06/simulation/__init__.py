"""Gói mô phỏng thời gian và xác nhận phát sóng (`p06.simulation`) cho thí nghiệm PoC.

1. File này giải quyết vấn đề gì?
   Cung cấp bộ công cụ chạy mô phỏng các phiên live dài 10–30 phút hoàn toàn tất định trên CPU
   (`VirtualClock`) và kiểm soát tiến độ dựa trên sự kiện ACK chuẩn P04 (`SimulatedPlaybackHarness`).
2. Trách nhiệm chính của module là gì?
   Tái xuất `VirtualClock`, `SimulatedPlaybackHarness`, `PendingTurnRecord`, cùng các hằng số
   cấu hình thời lượng nói mặc định qua `__all__`.
3. Module này liên kết với các thành phần nào?
   Nhập từ `virtual_clock.py` và `playback_harness.py`; phối hợp với `MockPlaybackAckBus`
   (`p06.adapters.mocks`) và `p06.schemas`.
4. Input và output chính là gì?
   Không xử lý dữ liệu runtime; xuất khẩu các lớp điều khiển mô phỏng công khai của P06.
5. Có những constraints hoặc invariants quan trọng nào?
   Không dùng `time.sleep()` thực tế; mọi tịnh tiến checkpoint đều bắt buộc đi qua ACK hợp lệ (I-06).
"""

from __future__ import annotations

from p06.simulation.playback_harness import (
    PendingTurnRecord,
    SimulatedPlaybackHarness,
)
from p06.simulation.virtual_clock import (
    DEFAULT_SPEECH_WORDS_PER_SEC,
    DEFAULT_VIRTUAL_START_AT,
    MAX_SPEECH_DURATION_MS,
    MIN_SPEECH_DURATION_MS,
    VirtualClock,
)

__all__ = [
    "DEFAULT_SPEECH_WORDS_PER_SEC",
    "DEFAULT_VIRTUAL_START_AT",
    "MAX_SPEECH_DURATION_MS",
    "MIN_SPEECH_DURATION_MS",
    "PendingTurnRecord",
    "SimulatedPlaybackHarness",
    "VirtualClock",
]
