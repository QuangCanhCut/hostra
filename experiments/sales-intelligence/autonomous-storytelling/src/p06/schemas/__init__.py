"""Gói xuất khẩu công khai toàn bộ hợp đồng dữ liệu Pydantic v2 cho P06 (`p06.schemas`).

1. File này giải quyết vấn đề gì?
   Cung cấp một điểm nhập duy nhất (`from p06.schemas import ...`) cho toàn bộ model, enum và hằng số
   của P06, giúp các module `planning/`, `agent/`, `memory/`, `guardrails/` và `tests/` không phải
   phụ thuộc vào cấu trúc file nội bộ bên dưới.
2. Trách nhiệm chính của module là gì?
   Tái xuất (re-export) toàn bộ các thành phần công khai từ `story.py`, `candidate.py`, `events.py`,
   và `state.py` qua danh sách `__all__` tường minh.
3. Module này liên kết với các thành phần nào?
   Thu thập từ 4 module con trong `src/p06/schemas/` và cung cấp cho `src/p06/__init__.py` cùng
   toàn bộ các tầng xử lý của module P06.
4. Input và output chính là gì?
   Không nhận input chạy runtime; output là không gian tên chuẩn hóa của hợp đồng `p06-mock-v0.1`.
5. Có những constraints hoặc invariants quan trọng nào?
   Danh sách `__all__` phải bao phủ đầy đủ và khớp chính xác với toàn bộ public enums, constants,
   và Pydantic models đã thiết kế cho `p06-mock-v0.1`.
"""

from __future__ import annotations

from p06.schemas.candidate import (
    CandidateOrigin,
    CandidateVerificationStatus,
    CoverageMode,
    ProposedResponseCoverage,
    SkuVersionBinding,
    SpeechCandidate,
    TargetScopeMode,
    UnresolvedSkuReason,
)
from p06.schemas.events import (
    PlaybackCompleted,
    PlaybackEventSource,
    PlaybackOutcomeStatus,
    ResumeMode,
    StoryCheckpoint,
)
from p06.schemas.state import (
    AgentState,
    AgentTurnOutcome,
    DEFAULT_MAX_REWRITE_RETRIES,
    DEFAULT_PLAYED_HISTORY_WINDOW,
    MAX_PLAYED_HISTORY_WINDOW,
    MAX_REWRITE_RETRIES_LIMIT,
    PlayedTurnSummary,
    RewriteBudgetState,
)
from p06.schemas.story import (
    BreakpointType,
    CONTRACT_VERSION,
    ContractVersion,
    MAX_ARC_DURATION_SEC,
    MAX_CHUNK_DURATION_SEC,
    MAX_PINNED_SKUS,
    MIN_PINNED_SKUS,
    NonBlankStr,
    OptionalNonBlankStr,
    StoryArc,
    StoryChunk,
    StoryChunkRole,
    StoryPlan,
    StoryPlanApprovalStatus,
    StoryTopic,
    StrictArcDurationSec,
    StrictDurationSec,
    StrictFalse,
    StrictNonNegInt,
    StrictPositiveDurationMs,
    StrictPositiveInt,
    StrictPositivePriceVnd,
)

__all__ = [
    # Constants & Type Aliases
    "CONTRACT_VERSION",
    "ContractVersion",
    "DEFAULT_MAX_REWRITE_RETRIES",
    "DEFAULT_PLAYED_HISTORY_WINDOW",
    "MAX_ARC_DURATION_SEC",
    "MAX_CHUNK_DURATION_SEC",
    "MAX_PINNED_SKUS",
    "MAX_PLAYED_HISTORY_WINDOW",
    "MAX_REWRITE_RETRIES_LIMIT",
    "MIN_PINNED_SKUS",
    "NonBlankStr",
    "OptionalNonBlankStr",
    "StrictArcDurationSec",
    "StrictDurationSec",
    "StrictFalse",
    "StrictNonNegInt",
    "StrictPositiveDurationMs",
    "StrictPositiveInt",
    "StrictPositivePriceVnd",
    # Enums
    "AgentTurnOutcome",
    "BreakpointType",
    "CandidateOrigin",
    "CandidateVerificationStatus",
    "CoverageMode",
    "PlaybackEventSource",
    "PlaybackOutcomeStatus",
    "ResumeMode",
    "StoryChunkRole",
    "StoryPlanApprovalStatus",
    "TargetScopeMode",
    "UnresolvedSkuReason",
    # Models
    "AgentState",
    "PlaybackCompleted",
    "PlayedTurnSummary",
    "ProposedResponseCoverage",
    "RewriteBudgetState",
    "SkuVersionBinding",
    "SpeechCandidate",
    "StoryArc",
    "StoryCheckpoint",
    "StoryChunk",
    "StoryPlan",
    "StoryTopic",
]
