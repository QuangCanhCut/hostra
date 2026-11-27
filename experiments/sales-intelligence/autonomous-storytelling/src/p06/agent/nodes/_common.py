"""Hàm tiện ích dùng chung nội bộ cho các node trong đồ thị LangGraph P06.

1. File này giải quyết vấn đề gì?
   Tránh lặp lại logic render prompt, gọi `LLMProvider`, phân loại lỗi retry/non-retry,
   đo thời lượng phát không cắt ngầm và dựng `StoryChunk` / `SpeechCandidate(DRAFT)` giữa
   `draft_chunk.py` và `bounded_rewrite.py`.
2. Trách nhiệm chính của module là gì?
   Cung cấp `validate_and_prepare_updates()`, bộ định dạng `<untrusted_knowledge_data>`,
   bộ tóm tắt lịch sử đã phát, và `execute_chunk_generation()`.
3. Module này liên kết với các thành phần nào?
   Sử dụng `AgentState` (`schemas/state.py`), `load_prompt_template` / `render_prompt_template`
   (`planning/prompt_loader.py`), `ChunkDraftLLMOutput` (`planning/draft_dtos.py`),
   `VirtualClock` (`simulation/virtual_clock.py`) và `LLMProvider` (`providers/base.py`).
4. Input và output chính là gì?
   Input là `AgentState`, `GraphRuntimeDeps`, `TurnExecutionContext`, tên template và tham số biến;
   Output là `dict[str, Any]` chứa cập nhật hợp lệ đã đi qua `state.validated_update()`.
5. Có những constraints hoặc invariants quan trọng nào?
   - Mọi cập nhật state đều phải đi qua `state.validated_update()` trước khi trả cho LangGraph.
   - Không bao giờ dùng `model_copy(update=...)` và không bao giờ cắt ngầm thời lượng quá dài.
   - Đầu ra LLM luôn được hydrate ở trạng thái `DRAFT` với `SkuVersionBinding` từ tri thức sống.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Optional

from p06.adapters.interfaces import SkuEvidenceView
from p06.agent.deps import DraftAttemptTrace, GraphRuntimeDeps, TurnExecutionContext
from p06.planning.draft_dtos import ChunkDraftLLMOutput
from p06.planning.prompt_loader import load_prompt_template, render_prompt_template
from p06.providers.base import (
    GenerationRequest,
    MalformedJsonOutputError,
    ProviderAuthError,
    ProviderConfigError,
    ProviderError,
    ProviderTimeoutError,
    ProviderTransportError,
    SchemaValidationOutputError,
)
from p06.schemas.candidate import (
    CandidateOrigin,
    CandidateVerificationStatus,
    CoverageMode,
    ProposedResponseCoverage,
    SpeechCandidate,
    TargetScopeMode,
)
from p06.schemas.state import AgentState, PlayedTurnSummary, RewriteBudgetState
from p06.schemas.story import StoryChunk, StoryTopic
from p06.simulation.virtual_clock import compute_chunk_word_budget

MS_PER_SECOND_FLOAT: float = 1000.0


def validate_node_updates(
    state: AgentState,
    node_name: str,
    **changes: Any,
) -> dict[str, Any]:
    """Kiểm định mọi cập nhật state bằng `AgentState.validated_update()` trước khi trả về LangGraph."""
    next_trace = [*state.node_trace, node_name]
    updates: dict[str, Any] = {"node_trace": next_trace, **changes}
    state.validated_update(**updates)
    return updates


def format_untrusted_knowledge_block(
    evidence: SkuEvidenceView,
    topic: StoryTopic,
) -> str:
    """Đóng gói dữ liệu SKU/chứng cứ thành chuỗi JSON dùng trong `<untrusted_knowledge_data>`."""
    relevant_ids = set(topic.fact_refs)
    filtered_chunks = [
        chunk
        for chunk in evidence.approved_chunks
        if not relevant_ids or chunk["evidence_id"] in relevant_ids
    ]
    if not filtered_chunks:
        filtered_chunks = list(evidence.approved_chunks)

    allowed_claim_ids = set(topic.allowed_claim_ids)
    filtered_claims = [
        claim
        for claim in evidence.allowed_claims
        if not allowed_claim_ids or claim.get("claim_id") in allowed_claim_ids
    ]
    if not filtered_claims:
        filtered_claims = list(evidence.allowed_claims)

    payload = {
        "sku_id": evidence.sku_id,
        "sku_name": evidence.sku_name,
        "price_vnd": evidence.price_vnd,
        "weight_display": evidence.weight_display,
        "expiry_display": evidence.expiry_display,
        "origin": evidence.origin,
        "ingredients": list(evidence.ingredients),
        "storage_instructions": evidence.storage_instructions,
        "ocop_status": evidence.ocop_status,
        "ocop_code": evidence.ocop_code,
        "approved_chunks": filtered_chunks,
        "allowed_claims": filtered_claims,
        "prohibited_claims": list(evidence.prohibited_claims),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def format_played_history_summary(played_history: Sequence[PlayedTurnSummary]) -> str:
    """Tạo tóm tắt gọn các lượt đã phát gần nhất để prompt tránh lặp nội dung."""
    if not played_history:
        return "(Chưa có lượt nào được phát trong phiên.)"
    lines: list[str] = []
    for turn in played_history:
        topics = ",".join(turn.topic_ids) if turn.topic_ids else "none"
        claims = ",".join(turn.covered_claim_ids) if turn.covered_claim_ids else "none"
        lines.append(
            f"- [{turn.turn_id}] topics=[{topics}] claims=[{claims}] intent={turn.intent}: {turn.spoken_text}"
        )
    return "\n".join(lines)


def _filter_mandatory_messages_for_sku(
    messages: Sequence[str],
    state: AgentState,
    evidence: SkuEvidenceView,
) -> list[str]:
    """Lọc `mandatory_messages` liên quan tới SKU đang nói để tránh nhồi thông tin đa SKU."""
    if not messages:
        return []
    active_tokens = {
        tok.lower()
        for tok in evidence.sku_name.split()
        if len(tok) >= 3 and tok.lower() not in {"chai", "hộp", "gói", "hạt", "túi", "500ml", "500g", "200g"}
    }
    filtered: list[str] = []
    for msg in messages:
        msg_lower = msg.lower()
        if any(tok in msg_lower for tok in active_tokens) or state.active_sku_id.lower() in msg_lower:
            filtered.append(msg)
    return filtered or list(messages)


def _compute_word_budget(max_duration_sec: float) -> tuple[int, str]:
    """Tính trần số từ khuyến nghị và dải mục tiêu nhất quán từ `compute_chunk_word_budget`."""
    recommended_max_words, _hard_max_words, target_words_range = compute_chunk_word_budget(
        max_duration_sec
    )
    return recommended_max_words, target_words_range


def build_base_prompt_variables(
    state: AgentState,
    evidence: SkuEvidenceView,
    arc_title: str,
    topic: StoryTopic,
    max_duration_sec: float,
) -> dict[str, str]:
    """Chuẩn bị tập biến ngữ cảnh chung cho prompt `story_generation.txt` và `rewrite.txt`."""
    max_words, target_words_range = _compute_word_budget(max_duration_sec)
    relevant_eids = set(topic.fact_refs)
    allowed_eids = [
        chunk["evidence_id"]
        for chunk in evidence.approved_chunks
        if not relevant_eids or chunk["evidence_id"] in relevant_eids
    ] or [chunk["evidence_id"] for chunk in evidence.approved_chunks]

    allowed_cids_filter = set(topic.allowed_claim_ids)
    allowed_cids = [
        claim["claim_id"]
        for claim in evidence.allowed_claims
        if claim.get("claim_id")
        and (not allowed_cids_filter or claim["claim_id"] in allowed_cids_filter)
    ] or [
        claim["claim_id"]
        for claim in evidence.allowed_claims
        if claim.get("claim_id")
    ]
    scoped_mandatory = _filter_mandatory_messages_for_sku(
        state.story_plan.mandatory_messages,
        state,
        evidence,
    )
    return {
        "active_sku_id": state.active_sku_id,
        "session_goal": state.story_plan.session_goal,
        "arc_title": arc_title,
        "topic_id": topic.topic_id,
        "topic_title": topic.title,
        "talking_points": "; ".join(topic.talking_points) or "(không có)",
        "allowed_evidence_ids": json.dumps(allowed_eids, ensure_ascii=False),
        "allowed_claim_ids": json.dumps(allowed_cids, ensure_ascii=False),
        "mandatory_messages": "; ".join(scoped_mandatory) or "(không có)",
        "prohibited_topics": "; ".join(state.story_plan.prohibited_topics) or "(không có)",
        "max_duration_sec": f"{max_duration_sec:g}",
        "max_words": str(max_words),
        "target_words_range": target_words_range,
        "played_history_summary": format_played_history_summary(state.played_history),
        "untrusted_knowledge_block": format_untrusted_knowledge_block(evidence, topic),
    }


def _build_retry_budget_update(
    budget: RewriteBudgetState,
    *,
    retries_used: int,
    reasons: Sequence[str],
) -> RewriteBudgetState:
    """Tạo `RewriteBudgetState` mới với danh sách lý do từ chối đã chuẩn hóa."""
    clean_reasons = [r.strip() for r in reasons if isinstance(r, str) and r.strip()]
    if not clean_reasons:
        clean_reasons = ["DRAFT_REJECTED_UNSPECIFIED"]
    return RewriteBudgetState(
        max_retries=budget.max_retries,
        retries_used=retries_used,
        last_failure_reasons=clean_reasons,
    )


def execute_chunk_generation(
    *,
    state: AgentState,
    deps: GraphRuntimeDeps,
    ctx: TurnExecutionContext,
    node_name: str,
    template_name: str,
    variables: Mapping[str, str],
    arc_id: str,
    topic: StoryTopic,
    rewrite_attempt: int,
    extra_state_updates: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Thực thi gọi LLM sinh/viết lại chunk và hydrate `StoryChunk` + `SpeechCandidate(DRAFT)`.

    Lý do gộp helper: `draft_chunk` (lần 0) và `bounded_rewrite` (lần 1..K) chia sẻ cùng hợp đồng
    prompt provenance, phân loại lỗi retryable vs non-retryable, kiểm tra thời lượng không cắt ngầm
    và quy trình hydrate `DRAFT` gắn `SkuVersionBinding` sống.
    """
    assert ctx.active_sku_evidence is not None
    evidence = ctx.active_sku_evidence
    resolved_extra = dict(extra_state_updates or {})

    template = load_prompt_template(template_name, prompts_dir=deps.prompts_dir)
    ctx.prompt_hashes[template.name] = template.sha256
    user_prompt = render_prompt_template(template, variables)

    request_id = f"{ctx.turn_id}-{topic.topic_id}-r{rewrite_attempt}"
    fixture_key = (
        f"{topic.topic_id}:r{rewrite_attempt}"
        if rewrite_attempt > 0
        else topic.topic_id
    )
    request = GenerationRequest(
        request_id=request_id,
        system_prompt=(
            "Bạn là agent kể chuyện bán hàng tiếng Việt P06 thuộc HOSTRA AI. "
            "Tuân thủ chặt I-02 (chỉ nháp), I-04 (khóa SKU hiện hành) và chỉ xuất JSON thuần túy."
        ),
        user_prompt=user_prompt,
        prompt_version=template.version,
        data_classification=deps.data_classification,
        seed=deps.seed,
        metadata={
            "fixture_key": fixture_key,
            "turn_id": ctx.turn_id,
            "topic_id": topic.topic_id,
            "active_sku_id": state.active_sku_id,
            "rewrite_attempt": rewrite_attempt,
        },
    )

    try:
        gen_result = deps.llm_provider.generate_structured(request, ChunkDraftLLMOutput)
    except (
        ProviderTimeoutError,
        ProviderTransportError,
        ProviderAuthError,
        ProviderConfigError,
    ) as exc:
        if exc.telemetry is not None:
            ctx.telemetry_records.append(exc.telemetry)
        ctx.non_retryable_failure = f"{type(exc).__name__}: {exc}"
        ctx.covered_claim_ids = ()
        reason_msg = f"NON_RETRYABLE_PROVIDER_ERROR: {type(exc).__name__}: {exc}"
        ctx.draft_attempts.append(
            DraftAttemptTrace(
                attempt=rewrite_attempt,
                topic_id=topic.topic_id,
                succeeded=False,
                is_retryable=False,
                failure_reasons=(reason_msg,),
            )
        )
        return validate_node_updates(
            state,
            node_name,
            draft_chunk=None,
            draft_candidate=None,
            rewrite_budget=_build_retry_budget_update(
                state.rewrite_budget,
                retries_used=rewrite_attempt,
                reasons=[f"NON_RETRYABLE_PROVIDER_ERROR: {type(exc).__name__}"],
            ),
            **resolved_extra,
        )
    except (MalformedJsonOutputError, SchemaValidationOutputError) as exc:
        if exc.telemetry is not None:
            ctx.telemetry_records.append(exc.telemetry)
        ctx.covered_claim_ids = ()
        reason_msg = f"RETRYABLE_STRUCTURED_OUTPUT_ERROR: {type(exc).__name__}: {exc}"
        ctx.draft_attempts.append(
            DraftAttemptTrace(
                attempt=rewrite_attempt,
                topic_id=topic.topic_id,
                succeeded=False,
                is_retryable=True,
                failure_reasons=(reason_msg,),
            )
        )
        return validate_node_updates(
            state,
            node_name,
            draft_chunk=None,
            draft_candidate=None,
            rewrite_budget=_build_retry_budget_update(
                state.rewrite_budget,
                retries_used=rewrite_attempt,
                reasons=[reason_msg],
            ),
            **resolved_extra,
        )
    except ProviderError as exc:
        if exc.telemetry is not None:
            ctx.telemetry_records.append(exc.telemetry)
        ctx.non_retryable_failure = f"{type(exc).__name__}: {exc}"
        ctx.covered_claim_ids = ()
        reason_msg = f"NON_RETRYABLE_PROVIDER_ERROR: {type(exc).__name__}: {exc}"
        ctx.draft_attempts.append(
            DraftAttemptTrace(
                attempt=rewrite_attempt,
                topic_id=topic.topic_id,
                succeeded=False,
                is_retryable=False,
                failure_reasons=(reason_msg,),
            )
        )
        return validate_node_updates(
            state,
            node_name,
            draft_chunk=None,
            draft_candidate=None,
            rewrite_budget=_build_retry_budget_update(
                state.rewrite_budget,
                retries_used=rewrite_attempt,
                reasons=[f"NON_RETRYABLE_PROVIDER_ERROR: {type(exc).__name__}"],
            ),
            **resolved_extra,
        )

    ctx.telemetry_records.append(gen_result.telemetry)
    draft: ChunkDraftLLMOutput = gen_result.parsed_output

    # Đánh giá thời lượng thực tế không cắt ngầm (khắc phục A-MAJ-06): vượt ngưỡng phải retry/fallback.
    max_duration_ms = int(round(deps.max_chunk_duration_sec * MS_PER_SECOND_FLOAT))
    duration_eval = deps.clock.evaluate_speech_duration(
        draft.text,
        max_duration_ms=max_duration_ms,
    )
    if duration_eval.exceeds_limit:
        ctx.last_failed_draft_text = draft.text
        ctx.covered_claim_ids = ()
        word_count = len(draft.text.split())
        max_words, target_range = _compute_word_budget(deps.max_chunk_duration_sec)
        over_reason = (
            f"OVER_MAX_DURATION_SEC: Lời thoại hiện dài {word_count} từ "
            f"(~{duration_eval.raw_ms / MS_PER_SECOND_FLOAT:.2f}s), vượt quá giới hạn "
            f"{deps.max_chunk_duration_sec:.2f}s (tối đa {max_words} từ). Hãy rút gọn về "
            f"{target_range}, giữ nguyên talking_points của chủ đề và bỏ phần lặp tên/giá nếu không cần."
        )
        ctx.draft_attempts.append(
            DraftAttemptTrace(
                attempt=rewrite_attempt,
                topic_id=topic.topic_id,
                text=draft.text,
                cited_evidence_ids=tuple(draft.cited_evidence_ids),
                estimated_duration_sec=duration_eval.raw_ms / MS_PER_SECOND_FLOAT,
                succeeded=False,
                is_retryable=True,
                failure_reasons=(over_reason,),
            )
        )
        return validate_node_updates(
            state,
            node_name,
            draft_chunk=None,
            draft_candidate=None,
            rewrite_budget=_build_retry_budget_update(
                state.rewrite_budget,
                retries_used=rewrite_attempt,
                reasons=[over_reason],
            ),
            **resolved_extra,
        )

    estimated_duration_sec = duration_eval.raw_ms / MS_PER_SECOND_FLOAT
    chunk_id = f"{ctx.turn_id}-{topic.topic_id}-c{ctx.sequence_index}-r{rewrite_attempt}"
    candidate_id = f"cand-{ctx.turn_id}-r{rewrite_attempt}"

    story_chunk = StoryChunk(
        chunk_id=chunk_id,
        plan_id=state.story_plan.plan_id,
        plan_revision=state.story_plan.plan_revision,
        arc_id=arc_id,
        topic_id=topic.topic_id,
        sequence_index=ctx.sequence_index,
        role=draft.role,
        sku_id=state.active_sku_id,
        text=draft.text,
        cited_evidence_ids=list(draft.cited_evidence_ids),
        estimated_duration_sec=estimated_duration_sec,
        semantic_breakpoint=draft.semantic_breakpoint,
        breakpoint_type=draft.breakpoint_type,
        rationale=draft.rationale,
        created_at=deps.clock.now(),
    )

    version_binding = evidence.to_version_binding(
        cited_evidence_ids=draft.cited_evidence_ids,
        stated_price_vnd=draft.stated_price_vnd,
        mentions_ocop=draft.mentions_ocop,
    )

    # Giữ coverage ở trạng thái đề xuất (is_authoritative=False) và ứng viên luôn khởi tạo ở DRAFT (I-02).
    draft_candidate = SpeechCandidate(
        candidate_id=candidate_id,
        turn_id=ctx.turn_id,
        tenant_id=state.tenant_id,
        session_id=state.session_id,
        session_epoch=state.session_epoch,
        origin=CandidateOrigin.PROACTIVE_STORY,
        source_chunk_id=chunk_id,
        scope_mode=TargetScopeMode.SINGLE_SKU,
        sku_refs=[state.active_sku_id],
        sku_bindings=[version_binding],
        session_rights_version=deps.session_rights_version,
        intent=f"PROACTIVE_STORY:{topic.topic_id}",
        text=draft.text,
        safe_summary=f"Arc {arc_id} / Topic {topic.topic_id} (attempt {rewrite_attempt})",
        semantic_breakpoint=draft.semantic_breakpoint,
        estimated_duration_sec=estimated_duration_sec,
        proposed_coverage=ProposedResponseCoverage(
            covered_topic_ids=[topic.topic_id],
            covered_intents=[topic.title],
            coverage_mode=CoverageMode.FULL,
            is_authoritative=False,
        ),
        verification_status=CandidateVerificationStatus.DRAFT,
        rewrite_attempt=rewrite_attempt,
        created_at=deps.clock.now(),
    )

    ctx.covered_claim_ids = tuple(draft.covered_claim_ids)
    ctx.last_failed_draft_text = draft.text
    ctx.draft_attempts.append(
        DraftAttemptTrace(
            attempt=rewrite_attempt,
            candidate_id=candidate_id,
            chunk_id=chunk_id,
            topic_id=topic.topic_id,
            text=draft.text,
            cited_evidence_ids=tuple(draft.cited_evidence_ids),
            estimated_duration_sec=estimated_duration_sec,
            succeeded=True,
            is_retryable=True,
            failure_reasons=(),
        )
    )
    return validate_node_updates(
        state,
        node_name,
        draft_chunk=story_chunk,
        draft_candidate=draft_candidate,
        rewrite_budget=RewriteBudgetState(
            max_retries=state.rewrite_budget.max_retries,
            retries_used=rewrite_attempt,
            last_failure_reasons=[],
        ),
        **resolved_extra,
    )
