"""Gói lập kế hoạch kể chuyện, tải prompt và sắp xếp mạch `StoryArc` cho P06 (`p06.planning`).

1. File này giải quyết vấn đề gì?
   Cung cấp điểm nhập thống nhất (`from p06.planning import ...`) cho toàn bộ thành phần lập kế hoạch:
   nạp/băm prompt có phiên bản, DTO bản nháp không tin cậy cho LLM, `StoryPlanner`, ranh giới phê duyệt
   mô phỏng merchant và bộ tuần tự `ArcSequencer`.
2. Trách nhiệm chính của module là gì?
   Tái xuất (re-export) toàn bộ lớp, hàm và hằng số công khai từ `prompt_loader.py`, `draft_dtos.py`,
   `story_planner.py`, và `arc_sequencer.py` thông qua danh sách `__all__`.
3. Module này liên kết với các thành phần nào?
   Kết nối các module nội bộ trong `src/p06/planning/` với `agent/nodes/`, `simulation/`, và `tests/`.
4. Input và output chính là gì?
   Không xử lý dữ liệu runtime trực tiếp; xuất khẩu giao diện Python chuẩn cho tầng lập kế hoạch.
5. Có những constraints hoặc invariants quan trọng nào?
   - Tách biệt rạch ròi bản nháp không tin cậy (`*DraftLLMOutput`, `StoryPlan[DRAFT]`) khỏi trạng thái
     đã phê duyệt (`APPROVED`) và trạng thái đã kiểm chứng P05 (`VERIFIED`).
"""

from __future__ import annotations

from p06.planning.arc_sequencer import ArcSequencer, TopicSelectionResult
from p06.planning.draft_dtos import (
    ChunkDraftLLMOutput,
    StoryArcDraftLLMOutput,
    StoryPlanDraftLLMOutput,
    StoryTopicDraftLLMOutput,
)
from p06.planning.prompt_loader import (
    DEFAULT_PROMPTS_DIR,
    PromptTemplate,
    compute_prompt_hashes,
    load_prompt_template,
    render_prompt_template,
)
from p06.planning.story_planner import (
    MerchantGoalInput,
    SimulatedMerchantApprovalBoundary,
    StoryPlanner,
)

__all__ = [
    # Prompt loading & provenance
    "DEFAULT_PROMPTS_DIR",
    "PromptTemplate",
    "compute_prompt_hashes",
    "load_prompt_template",
    "render_prompt_template",
    # Untrusted LLM Draft DTOs
    "ChunkDraftLLMOutput",
    "StoryArcDraftLLMOutput",
    "StoryPlanDraftLLMOutput",
    "StoryTopicDraftLLMOutput",
    # StoryPlanner & Merchant Approval Boundary
    "MerchantGoalInput",
    "SimulatedMerchantApprovalBoundary",
    "StoryPlanner",
    # Arc Sequencer
    "ArcSequencer",
    "TopicSelectionResult",
]
