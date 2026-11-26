"""Gói các baseline thực nghiệm cho P06 (`ScriptFirstBaseline`).

1. File này giải quyết vấn đề gì?
   Cung cấp điểm nhập thống nhất cho các baseline đối chứng trong thí nghiệm P06-E01..E04.
2. Trách nhiệm chính của module là gì?
   Tái xuất `ScriptFirstBaseline` cùng các enum/DTO kết quả (`BaselineScriptSource`,
   `UpfrontChunkDraftLLMOutput`, `BaselineTurnRecord`, `BaselineMetrics`, `BaselineSessionResult`).
3. Module này liên kết với các thành phần nào?
   Tái xuất từ `p06.baselines.script_first`.
4. Input và output chính là gì?
   Không xử lý logic runtime; chỉ xuất khẩu API công khai của gói `p06.baselines`.
5. Có những constraints hoặc invariants quan trọng nào?
   Không khởi tạo provider hay trạng thái toàn cục tại cấp `__init__.py`.
"""

from __future__ import annotations

from p06.baselines.script_first import (
    BaselineMetrics,
    BaselineScriptSource,
    BaselineSessionResult,
    BaselineTurnRecord,
    ScriptFirstBaseline,
    UpfrontChunkDraftLLMOutput,
)

__all__ = [
    "BaselineMetrics",
    "BaselineScriptSource",
    "BaselineSessionResult",
    "BaselineTurnRecord",
    "ScriptFirstBaseline",
    "UpfrontChunkDraftLLMOutput",
]
