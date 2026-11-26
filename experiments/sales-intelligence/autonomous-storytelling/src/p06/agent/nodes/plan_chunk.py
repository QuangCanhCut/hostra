"""Node `plan_chunk` trong đồ thị LangGraph P06: chọn chủ đề kể chuyện kế tiếp từ `ArcSequencer`.

1. File này giải quyết vấn đề gì?
   Xác định chính xác một `StoryTopic` hợp lệ cho `active_sku_id` chưa được đánh dấu hoàn tất
   trong `completed_topic_ids`, hoặc báo hiệu kết thúc sạch khi đã hết chủ đề.
2. Trách nhiệm chính của module là gì?
   Gọi hàm thuần `ArcSequencer.select_next_topic()`, ghi `selected_topic` và gợi ý chuyển tiếp vào
   `TurnExecutionContext`, đồng thời cập nhật `selected_arc_id` / `selected_topic_id` trong `AgentState`.
3. Module này liên kết với các thành phần nào?
   Sử dụng `ArcSequencer` (`planning/arc_sequencer.py`) và `TurnExecutionContext` (`agent/deps.py`).
4. Input và output chính là gì?
   Input là `AgentState`, `GraphRuntimeDeps`, `TurnExecutionContext`;
   Output là bản cập nhật `selected_arc_id`, `selected_topic_id`, `node_trace`.
5. Có những constraints hoặc invariants quan trọng nào?
   - `I-04`: Chỉ chọn chủ đề gắn với `active_sku_id` hiện hành.
   - `I-03`/`I-06`: Không bao giờ tự đánh dấu chủ đề hoàn tất khi mới chỉ chọn để nói.
"""

from __future__ import annotations

from typing import Any

from p06.agent.deps import GraphRuntimeDeps, TurnExecutionContext
from p06.agent.nodes._common import validate_node_updates
from p06.agent.routing import NODE_PLAN_CHUNK
from p06.planning.arc_sequencer import ArcSequencer
from p06.schemas.state import AgentState


def run_plan_chunk(
    state: AgentState,
    deps: GraphRuntimeDeps,
    ctx: TurnExecutionContext,
) -> dict[str, Any]:
    """Chọn chủ đề kế tiếp cho `active_sku_id` hoặc bật cờ dừng sạch nếu đã phủ hết."""
    _ = deps
    try:
        selection = ArcSequencer.select_next_topic(
            story_plan=state.story_plan,
            checkpoint=state.story_checkpoint,
            active_sku_id=state.active_sku_id,
            completed_topic_ids=state.completed_topic_ids,
            excluded_topic_ids=ctx.excluded_topic_ids,
        )
    except ValueError as exc:
        ctx.non_retryable_failure = f"PLAN_SELECTION_INVALID: {exc}"
        return validate_node_updates(
            state,
            NODE_PLAN_CHUNK,
            selected_arc_id=None,
            selected_topic_id=None,
        )

    if selection.should_terminate:
        ctx.should_terminate = True
        ctx.termination_reason = selection.termination_reason
        ctx.selected_topic = None
        ctx.next_topic_id_hint = None
        ctx.next_arc_id_hint = None
        return validate_node_updates(
            state,
            NODE_PLAN_CHUNK,
            selected_arc_id=None,
            selected_topic_id=None,
        )

    ctx.selected_topic = selection.selected_topic
    ctx.next_topic_id_hint = selection.next_topic_id_after_selection
    ctx.next_arc_id_hint = selection.next_arc_id_after_selection
    return validate_node_updates(
        state,
        NODE_PLAN_CHUNK,
        selected_arc_id=selection.selected_arc_id,
        selected_topic_id=selection.selected_topic.topic_id if selection.selected_topic else None,
    )
