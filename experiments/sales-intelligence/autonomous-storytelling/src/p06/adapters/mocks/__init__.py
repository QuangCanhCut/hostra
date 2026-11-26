"""Gói mock adapters (`p06.adapters.mocks`) phục vụ thí nghiệm và kiểm thử offline PoC.

1. File này giải quyết vấn đề gì?
   Cô lập hoàn toàn các thành phần giả lập (như `MockPlaybackAckBus`) khỏi tầng cổng trừu tượng
   và adapter production để bảo đảm nguyên tắc không trộn lẫn mock với hệ thống thật.
2. Trách nhiệm chính của module là gì?
   Tái xuất `MockPlaybackAckBus` qua `__all__`.
3. Module này liên kết với các thành phần nào?
   Nhập từ `playback_bus.py`; được sử dụng trong `tests/` và `simulation/` ở giai đoạn Stage 03 PoC.
4. Input và output chính là gì?
   Không xử lý dữ liệu runtime; xuất khẩu các lớp mock công khai.
5. Có những constraints hoặc invariants quan trọng nào?
   Cấm đưa trực tiếp các lớp từ `p06.adapters.mocks` vào nhánh production `apps/api/`.
"""

from __future__ import annotations

from p06.adapters.mocks.playback_bus import MockPlaybackAckBus

__all__ = [
    "MockPlaybackAckBus",
]
