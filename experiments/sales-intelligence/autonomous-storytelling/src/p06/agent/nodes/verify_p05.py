"""Node `verify_p05` trong đồ thị LangGraph P06: kiểm định ứng viên qua Cổng phát ngôn P05.

1. File này giải quyết vấn đề gì?
   Thực thi ranh giới bất biến `I-02`: mọi ứng viên trước khi ra khỏi đồ thị đều phải được
   `KnowledgeVerifierPort` (`P05KnowledgeAdapter`) xác thực trực tiếp trên kho tri thức hiện hành.
2. Trách nhiệm chính của module là gì?
   Gọi `verify_candidate()`, chuyển ứng viên đạt sang `verified_candidate`, hoặc phân loại
   lý do từ chối (`non_retryable` như stale TOCTOU/hết quyền vs `retryable` để bounded rewrite).
3. Module này liên kết với các thành phần nào?
   Sử dụng `KnowledgeVerifierPort.verify_candidate()` (`adapters/interfaces.py`) và cập nhật
   `AgentState` (`verified_candidate`, `draft_candidate`, `rewrite_budget`).
4. Input và output chính là gì?
   Input là `state.draft_candidate`;
   Output là `verified_candidate` (`VERIFIED`) hoặc `draft_candidate` (`REJECTED`) kèm lý do.
5. Có những constraints hoặc invariants quan trọng nào?
   - Tuyệt đối không tự đóng dấu `VERIFIED`; chỉ nhận kết quả từ `KnowledgeVerifierPort`.
   - Lỗi stale TOCTOU, sai tenant, mất eligibility hoặc sai OCOP/rights phải fail-fast không retry vô ích.
"""

from __future__ import annotations

from typing import Any, Final

from p06.agent.deps import GraphRuntimeDeps, TurnExecutionContext
from p06.agent.nodes._common import validate_node_updates
from p06.agent.routing import NODE_VERIFY_P05
from p06.schemas.candidate import CandidateVerificationStatus
from p06.schemas.state import AgentState, RewriteBudgetState

_NON_RETRYABLE_EXACT_REASONS: Final[frozenset[str]] = frozenset(
    {
        "FACT_OUTSIDE_VALIDITY_WINDOW",
        "OCOP_NOT_VERIFIED",
        "FOOD_SAFETY_UNVERIFIED",
        "RIGHTS_INVALID",
        "RIGHTS_REVOKED",
        "UNAPPROVED_FACT",
        "SKU_NOT_FOUND",
        "MISSING_ELIGIBILITY",
        "INELIGIBLE_SKU",
        "SKU_NOT_ELIGIBLE",
        "TENANT_MISMATCH",
        "TENANT_ISOLATION_VIOLATION",
        "UNSUPPORTED_SHOP_POLICY_VERIFICATION",
    }
)
_NON_RETRYABLE_PREFIXES: Final[tuple[str, ...]] = (
    "STALE_",
    "VERSION_MISMATCH",
    "TENANT_",
    "RIGHTS_",
    "OCOP_NOT_",
)


def _is_non_retryable_reason(reason: str) -> bool:
    """Phân biệt lý do hệ thống/TOCTOU không thể khắc phục bằng cách viết lại câu chữ."""
    normalized = reason.strip().upper()
    if normalized in _NON_RETRYABLE_EXACT_REASONS:
        return True
    if normalized.startswith(_NON_RETRYABLE_PREFIXES):
        return True
    return "STALE" in normalized and "VERSION" in normalized


def run_verify_p05(
    state: AgentState,
    deps: GraphRuntimeDeps,
    ctx: TurnExecutionContext,
) -> dict[str, Any]:
    """Gửi `draft_candidate` qua Cổng P05 tại mốc thời gian hiện tại của `VirtualClock`."""
    candidate = state.draft_candidate
    if candidate is None:
        ctx.non_retryable_failure = "MISSING_DRAFT_CANDIDATE_FOR_P05"
        return validate_node_updates(state, NODE_VERIFY_P05)

    result = deps.knowledge_verifier.verify_candidate(
        candidate,
        verified_at=deps.clock.now(),
    )
    ctx.last_verification_result = result

    if (
        result.status == CandidateVerificationStatus.VERIFIED
        and result.candidate.is_ready_for_tts()
    ):
        return validate_node_updates(
            state,
            NODE_VERIFY_P05,
            verified_candidate=result.candidate,
            draft_candidate=None,
            rewrite_budget=RewriteBudgetState(
                max_retries=state.rewrite_budget.max_retries,
                retries_used=state.rewrite_budget.retries_used,
                last_failure_reasons=[],
            ),
        )

    reasons = list(result.reasons) or ["P05_REJECTED_UNSPECIFIED"]
    ctx.last_failed_draft_text = candidate.text
    non_retryable_matches = [r for r in reasons if _is_non_retryable_reason(r)]
    if non_retryable_matches:
        ctx.non_retryable_failure = f"P05_NON_RETRYABLE: {', '.join(non_retryable_matches)}"

    return validate_node_updates(
        state,
        NODE_VERIFY_P05,
        draft_candidate=result.candidate,
        verified_candidate=None,
        rewrite_budget=RewriteBudgetState(
            max_retries=state.rewrite_budget.max_retries,
            retries_used=state.rewrite_budget.retries_used,
            last_failure_reasons=reasons,
        ),
    )
