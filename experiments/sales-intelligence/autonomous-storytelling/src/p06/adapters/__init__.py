"""Gói cổng giao tiếp và bộ chuyển đổi (`p06.adapters`) giữa P06 với P05 và P04.

1. File này giải quyết vấn đề gì?
   Cung cấp điểm nhập thống nhất cho các cổng trừu tượng (`interfaces.py`) và bộ chuyển đổi
   chỉ-đọc sang Cổng phát ngôn P05 (`P05KnowledgeAdapter`), giữ ranh giới sạch giữa logic
   nghiệp vụ P06 và các hệ thống phụ thuộc ngoài.
2. Trách nhiệm chính của module là gì?
   Tái xuất các DTO, Enum, Port trừu tượng và `P05KnowledgeAdapter` qua `__all__`.
3. Module này liên kết với các thành phần nào?
   Nhập từ `interfaces.py` và `p05_knowledge_adapter.py`; sử dụng bởi `guardrails/`,
   `simulation/`, `agent/nodes/`, và bộ kiểm thử hợp đồng `tests/contract/`.
4. Input và output chính là gì?
   Không xử lý dữ liệu runtime; xuất khẩu các hợp đồng và adapter công khai của gói `p06.adapters`.
5. Có những constraints hoặc invariants quan trọng nào?
   Các mock phục vụ PoC được tách riêng trong gói con `p06.adapters.mocks`, không trộn lẫn
   với cổng trừu tượng hay adapter production.
"""

from __future__ import annotations

from p06.adapters.interfaces import (
    AckApplyStatus,
    CandidateVerificationResult,
    KnowledgeVerifierPort,
    PlaybackAckBusPort,
    PlaybackAckResult,
    PlaybackApplyResult,
    SkuEvidenceView,
)
from p06.adapters.p05_knowledge_adapter import P05KnowledgeAdapter

__all__ = [
    "AckApplyStatus",
    "CandidateVerificationResult",
    "KnowledgeVerifierPort",
    "P05KnowledgeAdapter",
    "PlaybackAckBusPort",
    "PlaybackAckResult",
    "PlaybackApplyResult",
    "SkuEvidenceView",
]
