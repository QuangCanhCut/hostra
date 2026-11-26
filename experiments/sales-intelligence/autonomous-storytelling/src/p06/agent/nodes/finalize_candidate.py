"""Node `finalize_candidate` trong đồ thị LangGraph P06: đóng gói kết quả cuối lượt an toàn.

1. File này giải quyết vấn đề gì?
   Quyết định `AgentTurnOutcome` cuối lượt (`VERIFIED_READY`, `FALLBACK_PREAPPROVED`, hoặc
   `SAFE_ABORT_NO_CANDIDATE`) nhất quán tuyệt đối với sự hiện diện của `verified_candidate`.
2. Trách nhiệm chính của module là gì?
   Dọn `draft_candidate=None` và gán `turn_outcome` theo đúng kết quả đã được kiểm chứng.
3. Module này liên kết với các thành phần nào?
   Cập nhật `AgentState.turn_outcome` (`schemas/state.py`), tạo điểm dừng trước biên `END` của LangGraph.
4. Input và output chính là gì?
   Input là `AgentState` và `TurnExecutionContext`;
   Output là bản cập nhật cuối `turn_outcome`, `draft_candidate=None`, `node_trace`.
5. Có những constraints hoặc invariants quan trọng nào?
   - `I-03` & `I-06`: Node này KHÔNG BAO GIỜ cập nhật `completed_topic_ids`, `played_history`,
     hay `story_checkpoint`. Tiến độ chỉ tiến sau khi nhận `PlaybackCompleted` ACK tại harness.
"""

from __future__ import annotations

from typing import Any

from p06.agent.deps import GraphRuntimeDeps, TurnExecutionContext
from p06.agent.nodes._common import validate_node_updates
from p06.agent.routing import NODE_FINALIZE_CANDIDATE
from p06.schemas.state import AgentState, AgentTurnOutcome


def run_finalize_candidate(
    state: AgentState,
    deps: GraphRuntimeDeps,
    ctx: TurnExecutionContext,
) -> dict[str, Any]:
    """Chốt `turn_outcome` ở cuối đồ thị mà không tự ghi nhận tiến độ phát sóng."""
    _ = deps
    if state.verified_candidate is not None and ctx.used_fallback:
        outcome = AgentTurnOutcome.FALLBACK_PREAPPROVED
    elif state.verified_candidate is not None:
        outcome = AgentTurnOutcome.VERIFIED_READY
    else:
        outcome = AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE

    return validate_node_updates(
        state,
        NODE_FINALIZE_CANDIDATE,
        draft_candidate=None,
        turn_outcome=outcome,
    )
