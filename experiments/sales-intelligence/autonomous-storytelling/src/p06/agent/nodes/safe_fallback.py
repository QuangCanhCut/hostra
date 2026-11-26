"""Node `safe_fallback` trong đồ thị LangGraph P06: rút lui an toàn khi lỗi hoặc cạn ngân sách.

1. File này giải quyết vấn đề gì?
   Cung cấp một câu dự phòng đã duyệt trước (`PREAPPROVED_FALLBACK`) nhưng vẫn bắt buộc
   tái kiểm định trực tiếp trên kho tri thức P05 tại thời điểm hiện tại (chống TOCTOU).
2. Trách nhiệm chính của module là gì?
   Ủy quyền cho `SafeFallbackSelector.select_safe_fallback()` với bộ lọc cô lập
   `tenant_id`/`session_id`/`session_epoch` và cấm fallback tự đánh dấu phủ chủ đề.
3. Module này liên kết với các thành phần nào?
   Sử dụng `SafeFallbackSelector` (`guardrails/fallback_selector.py`).
4. Input và output chính là gì?
   Input là `AgentState` và `deps.fallback_candidates`;
   Output là `verified_candidate` (`VERIFIED` + `ctx.used_fallback=True`) hoặc `None` (fail-closed).
5. Có những constraints hoặc invariants quan trọng nào?
   - Không bao giờ dùng fallback lệch tenant/session/epoch hoặc trượt tái kiểm định P05.
   - `require_empty_covered_topics=True` bảo đảm câu fallback an toàn không làm giả độ phủ chủ đề.
"""

from __future__ import annotations

from typing import Any

from p06.agent.deps import GraphRuntimeDeps, TurnExecutionContext
from p06.agent.nodes._common import validate_node_updates
from p06.agent.routing import NODE_SAFE_FALLBACK
from p06.guardrails.fallback_selector import SafeFallbackSelector, normalize_fallback_text
from p06.schemas.state import AgentState


def run_safe_fallback(
    state: AgentState,
    deps: GraphRuntimeDeps,
    ctx: TurnExecutionContext,
) -> dict[str, Any]:
    """Chọn và tái kiểm định câu dự phòng an toàn; bỏ qua câu đã phát gần đây để tránh lặp."""
    excluded_texts = {
        normalize_fallback_text(turn.spoken_text)
        for turn in state.played_history
        if turn.intent == "FALLBACK_SAFE_INFO"
    }
    if state.played_history:
        excluded_texts.add(normalize_fallback_text(state.played_history[-1].spoken_text))

    selected = SafeFallbackSelector.select_safe_fallback(
        verifier=deps.knowledge_verifier,
        candidates=deps.fallback_candidates,
        verified_at=deps.clock.now(),
        tenant_id=state.tenant_id,
        session_id=state.session_id,
        session_epoch=state.session_epoch,
        require_empty_covered_topics=True,
        excluded_normalized_texts=excluded_texts,
    )
    # Xóa gợi ý chuyển topic của lượt chính vì câu dự phòng an toàn không hoàn thành chủ đề đó.
    ctx.next_topic_id_hint = None
    ctx.next_arc_id_hint = None
    if selected is not None:
        ctx.used_fallback = True
        ctx.covered_claim_ids = ()
        return validate_node_updates(
            state,
            NODE_SAFE_FALLBACK,
            verified_candidate=selected,
            draft_candidate=None,
        )

    ctx.used_fallback = False
    ctx.covered_claim_ids = ()
    return validate_node_updates(
        state,
        NODE_SAFE_FALLBACK,
        verified_candidate=None,
        draft_candidate=None,
    )
