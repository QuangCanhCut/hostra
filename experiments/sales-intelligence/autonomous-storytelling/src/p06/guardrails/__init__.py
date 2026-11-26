"""Gói các bộ bảo vệ (Guardrails) của module P06 theo nguyên tắc fail-closed (Hard Gate G4).

1. File này giải quyết vấn đề gì?
   Cung cấp điểm nhập thống nhất cho các thành phần bảo vệ phát ngôn của P06: bộ lọc phòng thủ
   cụm từ bị cấm (`ProhibitedEchoGuard`) và bộ chọn câu dự phòng an toàn (`SafeFallbackSelector`).
2. Trách nhiệm chính của module là gì?
   Tái xuất các lớp và kết quả công khai của tầng `guardrails` qua `__all__`.
3. Module này liên kết với các thành phần nào?
   Nhập từ `prohibited_echo_guard.py` và `fallback_selector.py`; được dùng bởi `adapters/`,
   `agent/nodes/`, và các bộ kiểm thử đơn vị/tích hợp.
4. Input và output chính là gì?
   Không xử lý dữ liệu runtime; xuất khẩu các lớp guardrail công khai của P06.
5. Có những constraints hoặc invariants quan trọng nào?
   Tất cả guardrails đều hoạt động theo nguyên tắc fail-closed và không thay thế thẩm quyền
   kiểm duyệt của `PublicationGate` (P05).
"""

from __future__ import annotations

from p06.guardrails.fallback_selector import SafeFallbackSelector
from p06.guardrails.prohibited_echo_guard import (
    ProhibitedEchoGuard,
    ProhibitedEchoResult,
)

__all__ = [
    "ProhibitedEchoGuard",
    "ProhibitedEchoResult",
    "SafeFallbackSelector",
]
