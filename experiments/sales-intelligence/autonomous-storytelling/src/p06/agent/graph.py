"""Đồ thị điều phối 8 node `StateGraph(AgentState)` và hàm thực thi từng lượt cho P06.

1. File này giải quyết vấn đề gì?
   Lắp ghép 8 node đơn trách nhiệm thành một quy trình kể chuyện an toàn trên LangGraph:
   nạp tri thức sống -> lập kế hoạch chunk -> sinh nháp -> chống lặp -> kiểm chứng P05 ->
   viết lại có giới hạn `1 + K` -> dự phòng an toàn -> chốt kết quả đầu lượt.
2. Trách nhiệm chính của module là gì?
   Cung cấp `build_storytelling_graph(deps, ctx)` để dựng & biên dịch `StateGraph(AgentState)`,
   và `run_storytelling_turn(initial_state, deps, ...)` để chạy một lượt an toàn qua biên `from_graph_result`.
3. Module này liên kết với các thành phần nào?
   Liên kết `AgentState` (`schemas/state.py`), 8 node (`agent/nodes/`), 6 bộ định tuyến (`agent/routing.py`),
   và các DTO runtime (`agent/deps.py`).
4. Input và output chính là gì?
   Input là `AgentState` hợp lệ (`StoryPlan` đã `APPROVED`) và `GraphRuntimeDeps`;
   Output là `AgentTurnResult` gồm `final_state` đã tái kiểm định và metadata telemetry/provenance.
5. Có những constraints hoặc invariants quan trọng nào?
   - `I-01` & `I-04`: `AgentState` không giữ thẩm quyền phiên và không tự đổi `active_sku_id`.
   - `I-02`: Chỉ ứng viên qua `verify_p05` hoặc fallback đã tái kiểm định mới xuất ra `VERIFIED`.
   - `I-03` & `I-06`: Đồ thị kết thúc TRƯỚC khi phát sóng và không tự cập nhật `played_history` hay `checkpoint`.
   - Bắt buộc đi qua `AgentState.from_graph_result()` ở cả đầu vào và đầu ra (`[A-BLK-01]`).
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from p06.agent.deps import AgentTurnResult, GraphRuntimeDeps, TurnExecutionContext
from p06.agent.nodes import (
    run_bounded_rewrite,
    run_check_repetition,
    run_draft_chunk,
    run_finalize_candidate,
    run_load_context,
    run_plan_chunk,
    run_safe_fallback,
    run_verify_p05,
)
from p06.agent.routing import (
    NODE_BOUNDED_REWRITE,
    NODE_CHECK_REPETITION,
    NODE_DRAFT_CHUNK,
    NODE_FINALIZE_CANDIDATE,
    NODE_LOAD_CONTEXT,
    NODE_PLAN_CHUNK,
    NODE_SAFE_FALLBACK,
    NODE_VERIFY_P05,
    route_after_bounded_rewrite,
    route_after_check_repetition,
    route_after_draft_chunk,
    route_after_load_context,
    route_after_plan_chunk,
    route_after_verify_p05,
)
from p06.schemas.state import AgentState, AgentTurnOutcome


def build_storytelling_graph(
    deps: GraphRuntimeDeps,
    ctx: TurnExecutionContext,
) -> Any:
    """Xây dựng và biên dịch đồ thị LangGraph 8 node cho một lượt kể chuyện P06."""
    workflow = StateGraph(AgentState)

    workflow.add_node(NODE_LOAD_CONTEXT, lambda state: run_load_context(state, deps, ctx))
    workflow.add_node(NODE_PLAN_CHUNK, lambda state: run_plan_chunk(state, deps, ctx))
    workflow.add_node(NODE_DRAFT_CHUNK, lambda state: run_draft_chunk(state, deps, ctx))
    workflow.add_node(NODE_CHECK_REPETITION, lambda state: run_check_repetition(state, deps, ctx))
    workflow.add_node(NODE_VERIFY_P05, lambda state: run_verify_p05(state, deps, ctx))
    workflow.add_node(NODE_BOUNDED_REWRITE, lambda state: run_bounded_rewrite(state, deps, ctx))
    workflow.add_node(NODE_SAFE_FALLBACK, lambda state: run_safe_fallback(state, deps, ctx))
    workflow.add_node(NODE_FINALIZE_CANDIDATE, lambda state: run_finalize_candidate(state, deps, ctx))

    workflow.add_edge(START, NODE_LOAD_CONTEXT)
    workflow.add_conditional_edges(
        NODE_LOAD_CONTEXT,
        lambda state: route_after_load_context(state, ctx),
        {
            NODE_PLAN_CHUNK: NODE_PLAN_CHUNK,
            NODE_SAFE_FALLBACK: NODE_SAFE_FALLBACK,
        },
    )
    workflow.add_conditional_edges(
        NODE_PLAN_CHUNK,
        lambda state: route_after_plan_chunk(state, ctx),
        {
            NODE_DRAFT_CHUNK: NODE_DRAFT_CHUNK,
            NODE_FINALIZE_CANDIDATE: NODE_FINALIZE_CANDIDATE,
            NODE_SAFE_FALLBACK: NODE_SAFE_FALLBACK,
        },
    )
    workflow.add_conditional_edges(
        NODE_DRAFT_CHUNK,
        lambda state: route_after_draft_chunk(state, ctx),
        {
            NODE_CHECK_REPETITION: NODE_CHECK_REPETITION,
            NODE_BOUNDED_REWRITE: NODE_BOUNDED_REWRITE,
            NODE_SAFE_FALLBACK: NODE_SAFE_FALLBACK,
        },
    )
    workflow.add_conditional_edges(
        NODE_CHECK_REPETITION,
        lambda state: route_after_check_repetition(state, ctx),
        {
            NODE_VERIFY_P05: NODE_VERIFY_P05,
            NODE_BOUNDED_REWRITE: NODE_BOUNDED_REWRITE,
            NODE_SAFE_FALLBACK: NODE_SAFE_FALLBACK,
        },
    )
    workflow.add_conditional_edges(
        NODE_VERIFY_P05,
        lambda state: route_after_verify_p05(state, ctx),
        {
            NODE_FINALIZE_CANDIDATE: NODE_FINALIZE_CANDIDATE,
            NODE_BOUNDED_REWRITE: NODE_BOUNDED_REWRITE,
            NODE_SAFE_FALLBACK: NODE_SAFE_FALLBACK,
        },
    )
    workflow.add_conditional_edges(
        NODE_BOUNDED_REWRITE,
        lambda state: route_after_bounded_rewrite(state, ctx),
        {
            NODE_CHECK_REPETITION: NODE_CHECK_REPETITION,
            NODE_BOUNDED_REWRITE: NODE_BOUNDED_REWRITE,
            NODE_SAFE_FALLBACK: NODE_SAFE_FALLBACK,
        },
    )
    workflow.add_edge(NODE_SAFE_FALLBACK, NODE_FINALIZE_CANDIDATE)
    workflow.add_edge(NODE_FINALIZE_CANDIDATE, END)

    return workflow.compile()


def run_storytelling_turn(
    initial_state: AgentState,
    deps: GraphRuntimeDeps,
    *,
    turn_id: str,
    sequence_index: int = 0,
) -> AgentTurnResult:
    """Thực thi một lượt kể chuyện trọn vẹn qua đồ thị LangGraph 8 node và tái kiểm định biên.

    Args:
        initial_state: Trạng thái đầu lượt (đã gắn `StoryPlan` ở trạng thái `APPROVED`).
        deps: Tập hợp phụ thuộc runtime tiêm vào đồ thị.
        turn_id: Mã định danh lượt nói duy nhất do bộ điều phối/harness cấp.
        sequence_index: Chỉ số thứ tự chunk trong phiên (`>= 0`).

    Returns:
        AgentTurnResult: Kết quả chứa `final_state` đã qua `AgentState.from_graph_result()`.

    Raises:
        ValueError: Nếu `turn_id` rỗng, `sequence_index < 0`, hoặc `initial_state` không ở `IN_PROGRESS`.
        ValidationError: Nếu trạng thái vào/ra vi phạm bất biến `AgentState`.
    """
    if not isinstance(turn_id, str) or not turn_id.strip():
        raise ValueError("turn_id không được rỗng.")
    if isinstance(sequence_index, bool) or not isinstance(sequence_index, int) or sequence_index < 0:
        raise ValueError(f"sequence_index phải là số nguyên không âm, nhận được {sequence_index!r}.")

    validated_initial = AgentState.from_graph_result(initial_state)
    if validated_initial.turn_outcome != AgentTurnOutcome.IN_PROGRESS:
        raise ValueError(
            f"run_storytelling_turn yêu cầu turn_outcome khởi đầu là IN_PROGRESS, "
            f"nhận được '{validated_initial.turn_outcome.value}'."
        )

    ctx = TurnExecutionContext(
        turn_id=turn_id.strip(),
        sequence_index=sequence_index,
    )
    compiled_graph = build_storytelling_graph(deps, ctx)
    raw_result = compiled_graph.invoke(validated_initial)
    final_state = AgentState.from_graph_result(raw_result)

    return AgentTurnResult(
        final_state=final_state,
        should_terminate=ctx.should_terminate,
        termination_reason=ctx.termination_reason,
        telemetry_records=tuple(ctx.telemetry_records),
        prompt_hashes=dict(ctx.prompt_hashes),
        covered_claim_ids=tuple(ctx.covered_claim_ids),
        next_topic_id_hint=ctx.next_topic_id_hint,
        next_arc_id_hint=ctx.next_arc_id_hint,
        draft_attempts=tuple(ctx.draft_attempts),
        repetition_checks=tuple(ctx.repetition_checks),
        p05_decisions=tuple(ctx.p05_decisions),
        non_retryable_failure=ctx.non_retryable_failure,
        excluded_topic_ids=tuple(sorted(ctx.excluded_topic_ids)),
    )
