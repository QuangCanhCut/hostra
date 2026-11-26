"""Node `bounded_rewrite` trong đồ thị LangGraph P06: viết lại có giới hạn `1 + K` lượt.

1. File này giải quyết vấn đề gì?
   Sửa lời thoại bị Cổng P05 hoặc `RepetitionDetector` từ chối dựa trên `last_failure_reasons`,
   hoặc chuyển sang chủ đề khác khi `SWITCH_TOPIC` được yêu cầu, trong giới hạn ngân sách `K`.
2. Trách nhiệm chính của module là gì?
   Tăng `retries_used += 1` (không bao giờ reset), xử lý chuyển chủ đề qua `ArcSequencer` nếu
   `ctx.excluded_topic_ids` vừa loại chủ đề cũ, và gọi `execute_chunk_generation` với `rewrite.txt`.
3. Module này liên kết với các thành phần nào?
   Dùng `ArcSequencer` (`planning/arc_sequencer.py`), `execute_chunk_generation` (`_common.py`)
   và `prompts/rewrite.txt`.
4. Input và output chính là gì?
   Input là `AgentState` kèm `rewrite_budget.last_failure_reasons`;
   Output là bản nháp `StoryChunk` và `SpeechCandidate(DRAFT, rewrite_attempt=retries_used)` mới.
5. Có những constraints hoặc invariants quan trọng nào?
   - Tổng số lần gọi LLM tối đa trong một lượt là `1 + max_retries` (`K`).
   - Mọi bản viết lại đều bắt buộc quay vòng qua `check_repetition -> verify_p05`, không đi tắt.
"""

from __future__ import annotations

from typing import Any

from p06.agent.deps import GraphRuntimeDeps, TurnExecutionContext
from p06.agent.nodes._common import (
    build_base_prompt_variables,
    execute_chunk_generation,
    validate_node_updates,
)
from p06.agent.routing import NODE_BOUNDED_REWRITE
from p06.memory.repetition_detector import RepetitionAction
from p06.planning.arc_sequencer import ArcSequencer
from p06.schemas.state import AgentState, RewriteBudgetState


def run_bounded_rewrite(
    state: AgentState,
    deps: GraphRuntimeDeps,
    ctx: TurnExecutionContext,
) -> dict[str, Any]:
    """Thực hiện một vòng viết lại có kiểm soát trong ngân sách `max_retries`."""
    if not state.rewrite_budget.can_retry or ctx.active_sku_evidence is None:
        ctx.non_retryable_failure = "REWRITE_BUDGET_EXHAUSTED"
        return validate_node_updates(state, NODE_BOUNDED_REWRITE)

    new_retries_used = state.rewrite_budget.retries_used + 1
    target_arc_id = state.selected_arc_id
    target_topic = ctx.selected_topic
    extra_updates: dict[str, Any] = {}

    if (
        ctx.last_repetition_result is not None
        and ctx.last_repetition_result.recommended_action == RepetitionAction.SWITCH_TOPIC
    ):
        selection = ArcSequencer.select_next_topic(
            story_plan=state.story_plan,
            checkpoint=state.story_checkpoint,
            active_sku_id=state.active_sku_id,
            completed_topic_ids=state.completed_topic_ids,
            excluded_topic_ids=ctx.excluded_topic_ids,
        )
        if selection.should_terminate or selection.selected_topic is None or selection.selected_arc_id is None:
            ctx.non_retryable_failure = (
                selection.termination_reason or "NO_ALTERNATIVE_TOPIC_FOR_SWITCH"
            )
            return validate_node_updates(
                state,
                NODE_BOUNDED_REWRITE,
                draft_chunk=None,
                draft_candidate=None,
                selected_arc_id=None,
                selected_topic_id=None,
                rewrite_budget=RewriteBudgetState(
                    max_retries=state.rewrite_budget.max_retries,
                    retries_used=new_retries_used,
                    last_failure_reasons=state.rewrite_budget.last_failure_reasons
                    or ["NO_ALTERNATIVE_TOPIC_FOR_SWITCH"],
                ),
            )
        target_arc_id = selection.selected_arc_id
        target_topic = selection.selected_topic
        ctx.selected_topic = target_topic
        ctx.next_topic_id_hint = selection.next_topic_id_after_selection
        ctx.next_arc_id_hint = selection.next_arc_id_after_selection
        ctx.last_repetition_result = None
        extra_updates = {
            "selected_arc_id": target_arc_id,
            "selected_topic_id": target_topic.topic_id,
        }

    if target_arc_id is None or target_topic is None:
        ctx.non_retryable_failure = "MISSING_TARGET_TOPIC_FOR_REWRITE"
        return validate_node_updates(state, NODE_BOUNDED_REWRITE)

    arc = next(
        (item for item in state.story_plan.arcs if item.arc_id == target_arc_id),
        None,
    )
    if arc is None:
        ctx.non_retryable_failure = f"ARC_NOT_FOUND_ON_REWRITE: {target_arc_id}"
        return validate_node_updates(state, NODE_BOUNDED_REWRITE)

    previous_text = ctx.last_failed_draft_text or (
        state.draft_candidate.text if state.draft_candidate is not None else "(không có bản nháp trước)"
    )
    failure_reasons = "; ".join(state.rewrite_budget.last_failure_reasons) or "(không rõ lý do)"

    variables = build_base_prompt_variables(
        state=state,
        evidence=ctx.active_sku_evidence,
        arc_title=arc.title,
        topic=target_topic,
        max_duration_sec=deps.max_chunk_duration_sec,
    )
    variables["previous_draft_text"] = previous_text
    variables["failure_reasons"] = failure_reasons
    variables["retry_attempt"] = str(new_retries_used)
    variables["max_retries"] = str(state.rewrite_budget.max_retries)

    return execute_chunk_generation(
        state=state,
        deps=deps,
        ctx=ctx,
        node_name=NODE_BOUNDED_REWRITE,
        template_name="rewrite.txt",
        variables=variables,
        arc_id=arc.arc_id,
        topic=target_topic,
        rewrite_attempt=new_retries_used,
        extra_state_updates=extra_updates,
    )
