"""Node `check_repetition` trong đồ thị LangGraph P06: rà soát lặp từ/lặp ý trước khi qua Cổng P05.

1. File này giải quyết vấn đề gì?
   Ngăn AI livestream lặp lại câu cũ, cụm từ cũ hoặc tập `claim_id` đã nói ở các lượt trước
   trong cửa sổ `state.played_history`.
2. Trách nhiệm chính của module là gì?
   Gọi `RepetitionDetector.check()`, đánh dấu `draft_candidate` sang `REJECTED` nếu vi phạm
   (`REWRITE` hoặc `SWITCH_TOPIC`), và thêm `topic_id` vào `ctx.excluded_topic_ids` khi cần đổi chủ đề.
3. Module này liên kết với các thành phần nào?
   Sử dụng `RepetitionDetector` / `RepetitionAction` (`memory/repetition_detector.py`) và
   `SpeechCandidate.mark_rejected()` (`schemas/candidate.py`).
4. Input và output chính là gì?
   Input là `AgentState.draft_candidate` (`DRAFT`) và `AgentState.played_history`;
   Output là cập nhật `node_trace` (và `draft_candidate` + `rewrite_budget` nếu bị chặn lặp).
5. Có những constraints hoặc invariants quan trọng nào?
   - Không làm thay đổi `played_history` hay `completed_topic_ids` trong node này.
   - Không tăng `retries_used` ở node kiểm tra; bộ đếm retry chỉ tăng trong `bounded_rewrite`.
"""

from __future__ import annotations

from typing import Any

from p06.agent.deps import GraphRuntimeDeps, TurnExecutionContext
from p06.agent.nodes._common import validate_node_updates
from p06.agent.routing import NODE_CHECK_REPETITION
from p06.memory.repetition_detector import RepetitionAction
from p06.schemas.state import AgentState, RewriteBudgetState


def run_check_repetition(
    state: AgentState,
    deps: GraphRuntimeDeps,
    ctx: TurnExecutionContext,
) -> dict[str, Any]:
    """Kiểm tra mức độ lặp của `draft_candidate` đối chiếu với `played_history` hiện hành."""
    candidate = state.draft_candidate
    if candidate is None:
        ctx.non_retryable_failure = "MISSING_DRAFT_CANDIDATE_FOR_REPETITION_CHECK"
        return validate_node_updates(state, NODE_CHECK_REPETITION)

    rep_result = deps.repetition_detector.check(
        candidate_text=candidate.text,
        played_turns=state.played_history,
        candidate_chunk_id=state.draft_chunk.chunk_id if state.draft_chunk is not None else candidate.source_chunk_id,
        topic_id=state.selected_topic_id,
        sku_id=state.active_sku_id,
        intent=candidate.intent,
        candidate_claim_ids=ctx.covered_claim_ids,
    )
    ctx.last_repetition_result = rep_result

    if rep_result.recommended_action == RepetitionAction.ALLOW:
        return validate_node_updates(state, NODE_CHECK_REPETITION)

    reasons = list(rep_result.reasons) or [f"REPETITION_{rep_result.category.value}"]
    if (
        rep_result.recommended_action == RepetitionAction.SWITCH_TOPIC
        and state.selected_topic_id is not None
    ):
        ctx.excluded_topic_ids.add(state.selected_topic_id)
        reasons.append(f"SWITCH_TOPIC_REQUESTED: loại trừ topic '{state.selected_topic_id}'.")

    ctx.last_failed_draft_text = candidate.text
    rejected_cand = candidate.mark_rejected(reasons, increment_rewrite=False)
    updated_budget = RewriteBudgetState(
        max_retries=state.rewrite_budget.max_retries,
        retries_used=state.rewrite_budget.retries_used,
        last_failure_reasons=reasons,
    )
    return validate_node_updates(
        state,
        NODE_CHECK_REPETITION,
        draft_candidate=rejected_cand,
        rewrite_budget=updated_budget,
    )
