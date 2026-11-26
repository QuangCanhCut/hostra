"""Mã tái sử dụng cho PoC Stage 03 của module P06 (Sales Intelligence & Autonomous Storytelling).

1. File này giải quyết vấn đề gì?
   Đóng vai trò điểm vào cấp gói (`p06`) của mã nguồn nghiên cứu P06, cung cấp thông tin phiên bản
   và tái xuất trực tiếp các hợp đồng dữ liệu cốt lõi từ `p06.schemas`.
2. Trách nhiệm chính của module là gì?
   Khai báo `__version__`, `CONTRACT_VERSION`, và tái xuất toàn bộ public schemas qua `__all__`
   để người dùng/thí nghiệm có thể nhập gọn từ `p06` hoặc `p06.schemas`.
3. Module này liên kết với các thành phần nào?
   Liên kết trực tiếp với `p06.schemas` và là gốc nhập của các module con (`planning`, `agent`,
   `memory`, `guardrails`, `providers`, `adapters`, `baselines`, `simulation`).
4. Input và output chính là gì?
   Không xử lý dữ liệu runtime; xuất khẩu phiên bản và tập các lớp/enum/hằng số hợp đồng `p06-mock-v0.1`.
5. Có những constraints hoặc invariants quan trọng nào?
   Đây là mã nghiên cứu PoC trong `experiments/`, KHÔNG phải mã production của
   `apps/api/src/hostra_api/modules/sales/`. Không khởi tạo provider hay logic nghiệp vụ ở cấp `__init__.py`.
"""

from __future__ import annotations

from p06.schemas import (
    AgentState,
    AgentTurnOutcome,
    BreakpointType,
    CONTRACT_VERSION,
    CandidateOrigin,
    CandidateVerificationStatus,
    ContractVersion,
    CoverageMode,
    DEFAULT_MAX_REWRITE_RETRIES,
    DEFAULT_PLAYED_HISTORY_WINDOW,
    MAX_ARC_DURATION_SEC,
    MAX_CHUNK_DURATION_SEC,
    MAX_PINNED_SKUS,
    MAX_PLAYED_HISTORY_WINDOW,
    MAX_REWRITE_RETRIES_LIMIT,
    MIN_PINNED_SKUS,
    NonBlankStr,
    OptionalNonBlankStr,
    PlaybackCompleted,
    PlaybackEventSource,
    PlaybackOutcomeStatus,
    PlayedTurnSummary,
    ProposedResponseCoverage,
    ResumeMode,
    RewriteBudgetState,
    SkuVersionBinding,
    SpeechCandidate,
    StoryArc,
    StoryCheckpoint,
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
    TargetScopeMode,
    UnresolvedSkuReason,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
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
