"""Node `load_context` trong đồ thị LangGraph P06: nạp & kiểm định tri thức sống của SKU active.

1. File này giải quyết vấn đề gì?
   Kiểm tra tính hợp lệ của ngữ cảnh đầu lượt và phát hiện sớm tình trạng tri thức bị thu hồi,
   hết hiệu lực hoặc lệch phiên bản (TOCTOU) trước khi tốn chi phí gọi LLM.
2. Trách nhiệm chính của module là gì?
   Đọc `SkuEvidenceView` cho `state.active_sku_id`, xác minh `is_eligible=True` và đối chiếu
   `knowledge_version` với `story_plan.knowledge_versions_by_sku` (nếu có).
3. Module này liên kết với các thành phần nào?
   Gọi `KnowledgeVerifierPort.get_sku_evidence()` (`adapters/interfaces.py`), ghi `active_sku_evidence`
   hoặc `non_retryable_failure` vào `TurnExecutionContext` (`agent/deps.py`).
4. Input và output chính là gì?
   Input là `AgentState`, `GraphRuntimeDeps`, `TurnExecutionContext`;
   Output là bản cập nhật `node_trace` đã qua `state.validated_update()`.
5. Có những constraints hoặc invariants quan trọng nào?
   - `I-04`: Tuyệt đối không thay đổi `active_sku_id`.
   - Fail-closed: Thiếu SKU, sai tenant, prompt injection nguồn hoặc `is_eligible=False`/stale
     đều đánh dấu `ctx.non_retryable_failure` để chuyển thẳng sang `safe_fallback`.
"""

from __future__ import annotations

from typing import Any

from p06.agent.deps import GraphRuntimeDeps, TurnExecutionContext
from p06.agent.nodes._common import validate_node_updates
from p06.agent.routing import NODE_LOAD_CONTEXT
from p06.schemas.state import AgentState
from p06.schemas.story import StoryPlanApprovalStatus


def run_load_context(
    state: AgentState,
    deps: GraphRuntimeDeps,
    ctx: TurnExecutionContext,
) -> dict[str, Any]:
    """Nạp bản chụp tri thức sống cho `active_sku_id` và kiểm tra tính sẵn sàng đầu lượt."""
    if state.story_plan.approval_status != StoryPlanApprovalStatus.APPROVED:
        ctx.non_retryable_failure = (
            f"UNAPPROVED_STORY_PLAN: status={state.story_plan.approval_status.value}"
        )
        return validate_node_updates(state, NODE_LOAD_CONTEXT)

    try:
        evidence = deps.knowledge_verifier.get_sku_evidence(
            state.tenant_id,
            state.active_sku_id,
            at_time=deps.clock.now(),
        )
    except (KeyError, PermissionError, ValueError) as exc:
        ctx.non_retryable_failure = f"SKU_EVIDENCE_UNAVAILABLE: {type(exc).__name__}: {exc}"
        return validate_node_updates(state, NODE_LOAD_CONTEXT)

    ctx.active_sku_evidence = evidence

    if not evidence.is_eligible:
        reasons = ",".join(evidence.ineligible_reasons)
        ctx.non_retryable_failure = f"SKU_NOT_ELIGIBLE: {reasons}"
        return validate_node_updates(state, NODE_LOAD_CONTEXT)

    planned_kv = state.story_plan.knowledge_versions_by_sku.get(state.active_sku_id)
    if planned_kv is not None and evidence.knowledge_version != planned_kv:
        ctx.non_retryable_failure = (
            f"STALE_KNOWLEDGE_VERSION: plan_kv={planned_kv}, live_kv={evidence.knowledge_version}"
        )
        return validate_node_updates(state, NODE_LOAD_CONTEXT)

    return validate_node_updates(state, NODE_LOAD_CONTEXT)
