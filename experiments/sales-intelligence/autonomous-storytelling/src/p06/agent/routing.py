"""Hàm định tuyến rẽ nhánh có điều kiện thuần túy cho đồ thị LangGraph 8 node của P06.

1. File này giải quyết vấn đề gì?
   Quyết định bước chuyển tiếp theo giữa 8 node trong `StateGraph(AgentState)` một cách minh bạch,
   tất định và dễ kiểm thử đơn vị độc lập khỏi logic gọi LLM/P05.
2. Trách nhiệm chính của module là gì?
   Khai báo các hằng tên node (`NODE_*`) và 6 hàm định tuyến (`route_after_*`) thực thi đúng
   ngân sách `1 + K` (`bounded_rewrite`) và rẽ nhánh nhanh sang `safe_fallback` khi gặp lỗi
   không thể thử lại.
3. Module này liên kết với các thành phần nào?
   Đọc `AgentState` (`schemas/state.py`), `CandidateVerificationStatus` (`schemas/candidate.py`),
   và `TurnExecutionContext` (`agent/deps.py`); được nối thành cạnh điều kiện trong `agent/graph.py`.
4. Input và output chính là gì?
   Input là `(state: AgentState, ctx: TurnExecutionContext)`;
   Output là tên node đích (`NODE_*`) kế tiếp trong đồ thị.
5. Có những constraints hoặc invariants quan trọng nào?
   - Không bao giờ vượt quá ngân sách `state.rewrite_budget.can_retry` (`1 + K`).
   - Lỗi không thể thử lại (`ctx.non_retryable_failure`) đi thẳng sang `NODE_SAFE_FALLBACK`.
   - Chỉ khi `verified_candidate is not None` mới đi thẳng sang `NODE_FINALIZE_CANDIDATE`.
"""

from __future__ import annotations

from typing import Final

from p06.agent.deps import TurnExecutionContext
from p06.schemas.candidate import CandidateVerificationStatus
from p06.schemas.state import AgentState

NODE_LOAD_CONTEXT: Final[str] = "load_context"
NODE_PLAN_CHUNK: Final[str] = "plan_chunk"
NODE_DRAFT_CHUNK: Final[str] = "draft_chunk"
NODE_CHECK_REPETITION: Final[str] = "check_repetition"
NODE_VERIFY_P05: Final[str] = "verify_p05"
NODE_BOUNDED_REWRITE: Final[str] = "bounded_rewrite"
NODE_SAFE_FALLBACK: Final[str] = "safe_fallback"
NODE_FINALIZE_CANDIDATE: Final[str] = "finalize_candidate"


def route_after_load_context(state: AgentState, ctx: TurnExecutionContext) -> str:
    """Định tuyến sau `load_context`: đi tiếp `plan_chunk` hoặc rẽ nhanh sang `safe_fallback`."""
    _ = state
    if ctx.non_retryable_failure is not None:
        return NODE_SAFE_FALLBACK
    return NODE_PLAN_CHUNK


def route_after_plan_chunk(state: AgentState, ctx: TurnExecutionContext) -> str:
    """Định tuyến sau `plan_chunk`: kết thúc sạch nếu hết chủ đề, ngược lại sang `draft_chunk`."""
    _ = state
    if ctx.non_retryable_failure is not None:
        return NODE_SAFE_FALLBACK
    if ctx.should_terminate:
        return NODE_FINALIZE_CANDIDATE
    return NODE_DRAFT_CHUNK


def route_after_draft_chunk(state: AgentState, ctx: TurnExecutionContext) -> str:
    """Định tuyến sau `draft_chunk`: tách lỗi không thể retry khỏi lỗi có thể retry theo ngân sách."""
    if ctx.non_retryable_failure is not None:
        return NODE_SAFE_FALLBACK
    if (
        state.draft_candidate is not None
        and state.draft_candidate.verification_status == CandidateVerificationStatus.DRAFT
    ):
        return NODE_CHECK_REPETITION
    if state.rewrite_budget.can_retry:
        return NODE_BOUNDED_REWRITE
    return NODE_SAFE_FALLBACK


def route_after_check_repetition(state: AgentState, ctx: TurnExecutionContext) -> str:
    """Định tuyến sau `check_repetition`: qua P05 nếu đạt, hoặc rewrite/fallback nếu lặp."""
    if ctx.last_repetition_result is not None and ctx.last_repetition_result.is_repetitive:
        if state.rewrite_budget.can_retry:
            return NODE_BOUNDED_REWRITE
        return NODE_SAFE_FALLBACK
    return NODE_VERIFY_P05


def route_after_verify_p05(state: AgentState, ctx: TurnExecutionContext) -> str:
    """Định tuyến sau `verify_p05`: chốt kết quả nếu `VERIFIED`, fail-fast hoặc bounded rewrite nếu bị chặn."""
    if state.verified_candidate is not None:
        return NODE_FINALIZE_CANDIDATE
    if ctx.non_retryable_failure is not None:
        return NODE_SAFE_FALLBACK
    if state.rewrite_budget.can_retry:
        return NODE_BOUNDED_REWRITE
    return NODE_SAFE_FALLBACK


def route_after_bounded_rewrite(state: AgentState, ctx: TurnExecutionContext) -> str:
    """Định tuyến sau `bounded_rewrite`: lặp lại `check_repetition -> verify_p05` hoặc rút lui an toàn."""
    if ctx.non_retryable_failure is not None:
        return NODE_SAFE_FALLBACK
    if (
        state.draft_candidate is not None
        and state.draft_candidate.verification_status == CandidateVerificationStatus.DRAFT
    ):
        return NODE_CHECK_REPETITION
    if state.rewrite_budget.can_retry:
        return NODE_BOUNDED_REWRITE
    return NODE_SAFE_FALLBACK
