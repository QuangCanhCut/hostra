"""Node `draft_chunk` trong đồ thị LangGraph P06: sinh bản nháp lời thoại đầu lượt (`attempt 0`).

1. File này giải quyết vấn đề gì?
   Chuyển mục tiêu chủ đề đã chọn + bằng chứng SKU thành bản nháp `StoryChunk` và `SpeechCandidate(DRAFT)`
   qua `LLMProvider.generate_structured(..., ChunkDraftLLMOutput)`.
2. Trách nhiệm chính của module là gì?
   Nạp & kết xuất `prompts/story_generation.txt`, gọi `execute_chunk_generation()` cho lần thử `0`,
   và cập nhật `draft_chunk`/`draft_candidate`/`rewrite_budget` vào `AgentState`.
3. Module này liên kết với các thành phần nào?
   Dùng `execute_chunk_generation` (`agent/nodes/_common.py`) và `prompts/story_generation.txt`.
4. Input và output chính là gì?
   Input là `AgentState` đã có `selected_arc_id`, `selected_topic_id` và `ctx.active_sku_evidence`;
   Output là bản cập nhật chứa `draft_chunk`, `draft_candidate` (`DRAFT`) hoặc lý do lỗi retry/non-retry.
5. Có những constraints hoặc invariants quan trọng nào?
   - `I-02`: Mọi ứng viên sinh từ LLM luôn khởi tạo ở `CandidateVerificationStatus.DRAFT`.
   - Không cắt ngầm thời lượng nếu lời thoại vượt `deps.max_chunk_duration_sec`.
"""

from __future__ import annotations

from typing import Any

from p06.agent.deps import GraphRuntimeDeps, TurnExecutionContext
from p06.agent.nodes._common import (
    build_base_prompt_variables,
    execute_chunk_generation,
    validate_node_updates,
)
from p06.agent.routing import NODE_DRAFT_CHUNK
from p06.schemas.state import AgentState


def run_draft_chunk(
    state: AgentState,
    deps: GraphRuntimeDeps,
    ctx: TurnExecutionContext,
) -> dict[str, Any]:
    """Sinh bản nháp lời thoại lần đầu (`retries_used=0`) cho chủ đề đang chọn."""
    if ctx.active_sku_evidence is None or ctx.selected_topic is None or state.selected_arc_id is None:
        ctx.non_retryable_failure = "MISSING_CONTEXT_FOR_DRAFT_CHUNK"
        return validate_node_updates(state, NODE_DRAFT_CHUNK)

    arc = next(
        (item for item in state.story_plan.arcs if item.arc_id == state.selected_arc_id),
        None,
    )
    if arc is None:
        ctx.non_retryable_failure = f"ARC_NOT_FOUND: {state.selected_arc_id}"
        return validate_node_updates(state, NODE_DRAFT_CHUNK)

    variables = build_base_prompt_variables(
        state=state,
        evidence=ctx.active_sku_evidence,
        arc_title=arc.title,
        topic=ctx.selected_topic,
        max_duration_sec=deps.max_chunk_duration_sec,
    )
    return execute_chunk_generation(
        state=state,
        deps=deps,
        ctx=ctx,
        node_name=NODE_DRAFT_CHUNK,
        template_name="story_generation.txt",
        variables=variables,
        arc_id=arc.arc_id,
        topic=ctx.selected_topic,
        rewrite_attempt=0,
    )
