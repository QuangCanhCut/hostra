"""Bộ điều phối phiên thực nghiệm cô lập hoàn toàn cho P06-E01 (`session_runner.py`).

1. File này giải quyết vấn đề gì?
   Chạy trọn vẹn một cấu hình `ExperimentRunConfig` (trên toàn bộ `pinned_sku_ids`) bằng
   đồng hồ ảo `VirtualClock`, bộ nhớ và harness cô lập hoàn toàn giữa các lần chạy, xử lý
   các ngưỡng dừng an toàn, đánh giá bằng chứng và xuất đủ 10 tệp artifact bất biến.
2. Trách nhiệm chính của module là gì?
   Định nghĩa `ExperimentRunnerResult` và hàm `run_experiment()` hỗ trợ cả 3 phương pháp
   (`script_first_deterministic`, `script_first_upfront_llm`, `langgraph_structured_story`).
3. Module này liên kết với các thành phần nào?
   Tích hợp `p06.agent.graph`, `p06.baselines.script_first`, `p06.adapters`, `p06.simulation`,
   `p06.memory`, `p06.providers.factory`, `p06.runner.mock_fixtures`, `p06.runner.evidence_collector`,
   `p06.runner.manifest`, và gọi lười `p06.evaluation.evaluator.evaluate_run` (nếu có).
4. Input và output chính là gì?
   Input là `ExperimentRunConfig` cùng các dependency tiêm tùy chọn phục vụ kiểm thử;
   Output là `ExperimentRunnerResult` chứa `run_id`, `run_dir`, `manifest`, `evidence`, `report`.
5. Có những constraints hoặc invariants quan trọng nào?
   - Không chia sẻ bất kỳ trạng thái khả biến nào giữa hai lần gọi `run_experiment()`.
   - Tôn trọng tuyệt đối Offline Guard đối với `ollama` và `gemini` khi `allow_live_provider=False`.
   - Khi `FALLBACK_PREAPPROVED` được phát, KHÔNG truyền `next_topic_id_hint` vào
     `register_pending_turn` để giữ nguyên chủ đề đang dở.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Optional

from pydantic import BaseModel, ConfigDict

from p06.adapters.interfaces import AckApplyStatus, PlaybackAckResult
from p06.adapters.mocks.playback_bus import MockPlaybackAckBus
from p06.adapters.p05_knowledge_adapter import P05KnowledgeAdapter
from p06.agent.deps import GraphRuntimeDeps
from p06.agent.graph import run_storytelling_turn
from p06.baselines.script_first import (
    BaselineScriptSource,
    BaselineSessionResult,
    ScriptFirstBaseline,
)
from p06.evaluation.models import EvaluationReport, RunEvidence
from p06.memory.played_history import ShortTermPlayedHistory
from p06.memory.repetition_detector import RepetitionDetector
from p06.memory.semantic_memory import NoOpSemanticMemory
from p06.memory.topic_coverage import GlobalTopicCoverage
from p06.memory.viewer_context import SessionViewerContext
from p06.guardrails.fallback_selector import normalize_fallback_text
from p06.guardrails.spoken_text_hygiene import check_spoken_text_hygiene
from p06.providers.base import (
    LLMProvider,
    ProviderConfigError,
    ProviderRateLimitError,
    ProviderTier,
    TokenUsageSource,
)
from p06.providers.factory import ProviderFactory
from p06.providers.mock_provider import DEFAULT_MOCK_MODEL_ID
from p06.runner.config import (
    DEFAULT_MAX_CHUNK_DURATION_SEC,
    DEFAULT_PROMPTS_DIR,
    LIVE_PROVIDERS,
    ExperimentMethod,
    ExperimentRunConfig,
    RunTerminationReason,
    load_e01_story_plan,
    load_yaml_mapping,
    resolve_dataset_profile,
)
from p06.runner.evidence_collector import EvidenceCollector
from p06.runner.manifest import (
    build_experiment_manifest,
    generate_run_id,
    persist_run_artifacts,
)
from p06.runner.mock_fixtures import build_e01_mock_provider
from p06.schemas.candidate import (
    CandidateOrigin,
    CandidateVerificationStatus,
    CoverageMode,
    ProposedResponseCoverage,
    SpeechCandidate,
    TargetScopeMode,
)
from p06.schemas.events import PlaybackOutcomeStatus, StoryCheckpoint
from p06.schemas.state import DEFAULT_PLAYED_HISTORY_WINDOW, AgentTurnOutcome
from p06.schemas.story import NonBlankStr, StoryPlan
from p06.simulation.playback_harness import SimulatedPlaybackHarness
from p06.simulation.virtual_clock import DEFAULT_SPEECH_WORDS_PER_SEC, VirtualClock

_MS_PER_SECOND: Final[float] = 1000.0
_MAX_FALLBACK_WORDS: Final[int] = int(DEFAULT_MAX_CHUNK_DURATION_SEC * DEFAULT_SPEECH_WORDS_PER_SEC)


class ExperimentRunnerResult(BaseModel):
    """Kết quả trọn vẹn của một lượt chạy thực nghiệm đã lưu artifact xuống đĩa."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    run_id: NonBlankStr
    run_dir: Path
    manifest: dict[str, Any]
    evidence: RunEvidence
    report: Optional[EvaluationReport] = None
    termination_reason: RunTerminationReason


def _find_initial_arc_and_topic(
    story_plan: StoryPlan,
    active_sku_id: str,
) -> tuple[str, Optional[str]]:
    """Tìm `(current_arc_id, next_topic_id)` khởi đầu hợp lệ cho `active_sku_id`."""
    sorted_arcs = sorted(story_plan.arcs, key=lambda item: item.position)
    resolved_arc_id: Optional[str] = None
    for arc in sorted_arcs:
        if arc.sku_id == active_sku_id or any(
            topic.sku_id == active_sku_id for topic in arc.topics
        ):
            resolved_arc_id = arc.arc_id
            break
    if resolved_arc_id is None:
        resolved_arc_id = sorted_arcs[0].arc_id

    resolved_topic_id: Optional[str] = None
    for arc in sorted_arcs:
        for topic in arc.topics:
            is_eligible = topic.sku_id == active_sku_id or (
                topic.sku_id is None and (arc.sku_id == active_sku_id or arc.sku_id is None)
            )
            if is_eligible:
                resolved_topic_id = topic.topic_id
                break
        if resolved_topic_id is not None:
            break
    return resolved_arc_id, resolved_topic_id


def _all_mandatory_topics_completed(
    story_plan: StoryPlan,
    completed_topic_ids: frozenset[str],
) -> bool:
    """Kiểm tra toàn bộ chủ đề bắt buộc trong `StoryPlan` đã nhận ACK phát hoàn tất hay chưa."""
    mandatory_ids = {
        topic.topic_id
        for arc in story_plan.arcs
        for topic in arc.topics
        if topic.is_mandatory
    }
    return mandatory_ids.issubset(completed_topic_ids)


def _select_complete_fallback_texts(evidence: SkuEvidenceView, price_display: str) -> list[str]:
    """Tạo tối đa 2 câu dự phòng tiếng Việt hoàn chỉnh, không cắt cụt giữa câu và vừa trần 8 giây.

    Mỗi mẫu đều giữ đủ tên SKU + giá niêm yết đã kiểm chứng để P05 xác thực, đồng thời
    khác nhau ở thông tin quy cách/xuất xứ nhằm tránh lặp nguyên văn khi có 2 lần fallback.
    """
    primary_candidates = (
        f"{evidence.sku_name} hiện có giá niêm yết {price_display}.",
        f"{evidence.sku_name}: giá niêm yết {price_display}.",
    )
    secondary_candidates = (
        f"{evidence.sku_name}, nguồn gốc {evidence.origin}, giá {price_display}."
        if evidence.origin
        else "",
        f"{evidence.sku_name}, quy cách {evidence.weight_display}, giá {price_display}."
        if evidence.weight_display
        else "",
        f"Giá niêm yết của {evidence.sku_name} là {price_display}.",
    )

    selected: list[str] = []
    seen_norm: set[str] = set()
    for group in (primary_candidates, secondary_candidates):
        for raw_sentence in group:
            sentence = raw_sentence.strip()
            if not sentence:
                continue
            word_count = len(sentence.split())
            duration_sec = VirtualClock.estimate_raw_speech_duration_ms(sentence) / _MS_PER_SECOND
            if (
                word_count <= _MAX_FALLBACK_WORDS
                and duration_sec <= DEFAULT_MAX_CHUNK_DURATION_SEC
                and check_spoken_text_hygiene(sentence).passed
            ):
                norm = normalize_fallback_text(sentence)
                if norm not in seen_norm:
                    seen_norm.add(norm)
                    selected.append(sentence)
                break
    return selected


def _build_default_fallbacks_by_sku(
    *,
    story_plan: StoryPlan,
    evidence_adapter: P05KnowledgeAdapter,
    at_time: datetime,
    session_epoch: int = 1,
) -> dict[str, tuple[SpeechCandidate, ...]]:
    """Tạo các câu dự phòng `PREAPPROVED_FALLBACK` hoàn chỉnh, hợp lệ cho từng SKU trong kế hoạch."""
    fallbacks_by_sku: dict[str, tuple[SpeechCandidate, ...]] = {}
    for sku_id in story_plan.pinned_sku_ids:
        try:
            evidence = evidence_adapter.get_sku_evidence(
                story_plan.tenant_id,
                sku_id,
                at_time=at_time,
            )
        except (KeyError, PermissionError, ValueError):
            fallbacks_by_sku[sku_id] = ()
            continue

        if not evidence.is_eligible or not evidence.approved_chunks:
            fallbacks_by_sku[sku_id] = ()
            continue

        shipping_chunk = next(
            (chunk for chunk in evidence.approved_chunks if "shipping" in chunk["evidence_id"]),
            evidence.approved_chunks[0],
        )
        price_display = f"{evidence.price_vnd:,}".replace(",", ".") + "đ"
        fallback_texts = _select_complete_fallback_texts(evidence, price_display)
        if not fallback_texts:
            fallbacks_by_sku[sku_id] = ()
            continue

        candidates: list[SpeechCandidate] = []
        for idx, sentence in enumerate(fallback_texts):
            duration_sec = VirtualClock.estimate_raw_speech_duration_ms(sentence) / _MS_PER_SECOND
            binding = evidence.to_version_binding(
                cited_evidence_ids=[shipping_chunk["evidence_id"]],
                stated_price_vnd=evidence.price_vnd,
                mentions_ocop=False,
            )
            suffix = "" if idx == 0 else f"-v{idx + 1}"
            candidates.append(
                SpeechCandidate(
                    candidate_id=f"fb-{sku_id.lower()}-e{session_epoch}{suffix}",
                    tenant_id=story_plan.tenant_id,
                    session_id=story_plan.session_id,
                    session_epoch=session_epoch,
                    origin=CandidateOrigin.PREAPPROVED_FALLBACK,
                    scope_mode=TargetScopeMode.SINGLE_SKU,
                    sku_refs=[sku_id],
                    sku_bindings=[binding],
                    session_rights_version=1,
                    intent="FALLBACK_SAFE_INFO",
                    text=sentence,
                    estimated_duration_sec=duration_sec,
                    proposed_coverage=ProposedResponseCoverage(
                        covered_topic_ids=[],
                        covered_intents=["Thông tin sản phẩm an toàn"],
                        coverage_mode=CoverageMode.FULL,
                        is_authoritative=False,
                    ),
                    verification_status=CandidateVerificationStatus.DRAFT,
                )
            )
        fallbacks_by_sku[sku_id] = tuple(candidates)
    return fallbacks_by_sku


def _filter_fallbacks_for_sku(
    all_fallbacks: Sequence[SpeechCandidate],
    sku_id: str,
) -> tuple[SpeechCandidate, ...]:
    """Lọc danh sách fallback khớp đúng `sku_id` (hoặc giữ nguyên nếu không gắn SKU cụ thể)."""
    matched = tuple(cand for cand in all_fallbacks if sku_id in cand.sku_refs)
    return matched if matched else tuple(all_fallbacks)


def _resolve_default_evaluator() -> Optional[Callable[[RunEvidence], EvaluationReport]]:
    """Nạp lười `p06.evaluation.evaluator.evaluate_run` nếu gói đánh giá đã sẵn sàng."""
    try:
        from p06.evaluation.evaluator import evaluate_run  # type: ignore[import-not-found]

        return evaluate_run
    except ModuleNotFoundError:
        return None


def _budget_limit_reached(
    config: ExperimentRunConfig,
    collector: EvidenceCollector,
    model_yaml: Mapping[str, Any],
) -> bool:
    """Kiểm tra ngưỡng an toàn chi phí (`max_llm_calls`, `max_estimated_cost_usd`)."""
    if config.max_llm_calls is None and config.max_estimated_cost_usd is None:
        return False
    usage = collector.build_token_usage_summary()
    if config.max_llm_calls is not None and usage["total_model_calls"] >= config.max_llm_calls:
        return True
    if config.max_estimated_cost_usd is not None:
        pricing = model_yaml.get("pricing")
        in_tok = usage.get("input_tokens")
        out_tok = usage.get("output_tokens")
        think_tok = int(usage.get("thinking_tokens") or 0)
        if (
            isinstance(pricing, Mapping)
            and isinstance(in_tok, int)
            and isinstance(out_tok, int)
            and isinstance(pricing.get("input_per_1m_usd"), (int, float))
            and not isinstance(pricing.get("input_per_1m_usd"), bool)
            and isinstance(pricing.get("output_per_1m_usd"), (int, float))
            and not isinstance(pricing.get("output_per_1m_usd"), bool)
        ):
            est_cost = (in_tok / 1_000_000.0) * float(pricing["input_per_1m_usd"]) + (
                (out_tok + think_tok) / 1_000_000.0
            ) * float(pricing["output_per_1m_usd"])
            if est_cost >= config.max_estimated_cost_usd:
                return True
    return False


def _run_script_first_loop(
    *,
    config: ExperimentRunConfig,
    model_yaml: Mapping[str, Any],
    story_plan: StoryPlan,
    evidence_adapter: P05KnowledgeAdapter,
    playback_bus: MockPlaybackAckBus,
    harness: SimulatedPlaybackHarness,
    clock: VirtualClock,
    llm_provider: Optional[LLMProvider],
    fallbacks_by_sku: Mapping[str, Sequence[SpeechCandidate]],
    collector: EvidenceCollector,
    outcome_overrides: Optional[Mapping[int, PlaybackOutcomeStatus]],
) -> tuple[RunTerminationReason, Optional[str], Optional[str]]:
    """Điều phối chạy `ScriptFirstBaseline` qua toàn bộ `pinned_sku_ids` với các ngưỡng dừng."""
    script_source = (
        BaselineScriptSource.DETERMINISTIC_TALKING_POINTS
        if config.method == ExperimentMethod.SCRIPT_FIRST_DETERMINISTIC
        else BaselineScriptSource.UPFRONT_LLM
    )
    total_turns = 0
    consecutive_aborts = 0
    termination_reason: Optional[RunTerminationReason] = None
    extra_prompt_version: Optional[str] = None
    extra_prompt_sha256: Optional[str] = None

    for sku_idx, sku_id in enumerate(story_plan.pinned_sku_ids):
        if _budget_limit_reached(config, collector, model_yaml):
            termination_reason = RunTerminationReason.BUDGET_LIMIT_REACHED
            break
        if consecutive_aborts >= config.max_consecutive_aborts:
            termination_reason = RunTerminationReason.MAX_CONSECUTIVE_ABORTS
            break
        if total_turns >= config.max_turns:
            termination_reason = RunTerminationReason.MAX_TURNS_REACHED
            break
        if clock.elapsed_sec() >= config.target_duration_sec:
            termination_reason = RunTerminationReason.TIME_BUDGET_EXHAUSTED
            break

        if sku_idx > 0:
            harness.switch_active_sku(
                sku_id,
                story_plan=story_plan,
                updated_at=clock.now(),
            )

        baseline = ScriptFirstBaseline(
            knowledge_verifier=evidence_adapter,
            playback_bus=playback_bus,
            harness=harness,
            clock=clock,
            llm_provider=llm_provider,
            fallback_candidates=fallbacks_by_sku.get(sku_id, ()),
            script_source=script_source,
            seed=config.seed,
            max_chunk_duration_sec=config.max_chunk_duration_sec,
            min_chunks_per_topic=config.min_chunks_per_topic,
        )

        local_overrides: Optional[dict[int, PlaybackOutcomeStatus]] = None
        if outcome_overrides is not None:
            filtered = {
                idx - total_turns: status
                for idx, status in outcome_overrides.items()
                if idx >= total_turns
            }
            if filtered:
                local_overrides = filtered

        turn_t0 = time.perf_counter()
        session_res: BaselineSessionResult = baseline.run_session(
            story_plan,
            active_sku_id=sku_id,
            outcome_overrides_by_turn=local_overrides,
            max_turns=max(0, config.max_turns - total_turns),
            target_duration_sec=config.target_duration_sec,
            max_consecutive_aborts=config.max_consecutive_aborts,
            initial_consecutive_aborts=consecutive_aborts,
        )
        session_wall_ms = (time.perf_counter() - turn_t0) * _MS_PER_SECOND

        collector.planning_latency_ms += session_res.metrics.planning_latency_ms
        collector.upfront_script_generation_latency_ms += session_res.metrics.planning_latency_ms
        extra_prompt_version = session_res.prompt_version or extra_prompt_version
        extra_prompt_sha256 = session_res.prompt_sha256 or extra_prompt_sha256

        per_turn_wall_ms = (
            session_wall_ms / len(session_res.turns) if session_res.turns else 0.0
        )
        pb_idx = 0
        played_by_turn_id = {entry.turn_id: entry for entry in harness.played_history}

        for turn in session_res.turns:
            global_turn_index = total_turns
            scoped_chunk_id = turn.chunk_id
            collector.record_baseline_turn(
                turn_index=global_turn_index,
                method=config.method,
                active_sku_id=sku_id,
                turn=turn,
                invocation_latency_ms=per_turn_wall_ms,
                chunk_id_override=scoped_chunk_id,
            )

            if turn.outcome == AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE:
                consecutive_aborts += 1
            else:
                consecutive_aborts = 0
                if pb_idx < len(session_res.playback_events):
                    ack_result: PlaybackAckResult = session_res.playback_events[pb_idx]
                    pb_idx += 1
                    played_entry = played_by_turn_id.get(turn.turn_id)
                    synthetic_candidate = _reconstruct_candidate_stub_for_evidence(
                        story_plan=story_plan,
                        sku_id=sku_id,
                        turn=turn,
                        played_entry_text=played_entry.spoken_text if played_entry else turn.spoken_text,
                        chunk_id_override=scoped_chunk_id,
                    )
                    collector.record_playback_outcome(
                        turn_id=turn.turn_id,
                        sku_id=sku_id,
                        candidate=synthetic_candidate,
                        ack_result=ack_result,
                        applied=(turn.ack_status == AckApplyStatus.APPLIED),
                        apply_status=turn.ack_status or AckApplyStatus.IGNORED_NON_COMPLETED,
                        apply_reason=turn.failure_reason,
                        topic_id=turn.topic_id,
                        arc_id=turn.arc_id,
                        chunk_id=scoped_chunk_id,
                        covered_claim_ids=turn.covered_claim_ids,
                        proposed_topic_ids=(
                            (turn.topic_id,)
                            if turn.outcome == AgentTurnOutcome.VERIFIED_READY
                            else ()
                        ),
                        is_fallback=(turn.outcome == AgentTurnOutcome.FALLBACK_PREAPPROVED),
                        gate_decision_id=turn.p05_gate_decision_id,
                    )

            total_turns += 1
            if consecutive_aborts >= config.max_consecutive_aborts:
                termination_reason = RunTerminationReason.MAX_CONSECUTIVE_ABORTS
                break
            if total_turns >= config.max_turns:
                termination_reason = RunTerminationReason.MAX_TURNS_REACHED
                break
            if clock.elapsed_sec() >= config.target_duration_sec:
                termination_reason = RunTerminationReason.TIME_BUDGET_EXHAUSTED
                break

        collector.record_baseline_telemetry_and_errors(
            session_result=session_res,
            active_sku_id=sku_id,
        )
        rate_or_budget_hit = any(
            marker in msg
            for marker in ("ProviderRateLimitError", "GLOBAL_REQUEST_BUDGET_EXCEEDED")
            for msg in (
                *[str(err.get("message", "")) for err in session_res.errors],
                *[t.failure_reason or "" for t in session_res.turns],
            )
        )
        if rate_or_budget_hit:
            termination_reason = RunTerminationReason.BUDGET_LIMIT_REACHED
            break
        if termination_reason is not None:
            break

    if termination_reason is None:
        if clock.elapsed_sec() >= config.target_duration_sec:
            termination_reason = RunTerminationReason.TIME_BUDGET_EXHAUSTED
        elif _all_mandatory_topics_completed(story_plan, harness.completed_topic_ids):
            termination_reason = RunTerminationReason.EARLY_COMPLETION
        else:
            termination_reason = RunTerminationReason.CONTENT_EXHAUSTED

    return termination_reason, extra_prompt_version, extra_prompt_sha256


def _reconstruct_candidate_stub_for_evidence(
    *,
    story_plan: StoryPlan,
    sku_id: str,
    turn: Any,
    played_entry_text: Optional[str],
    chunk_id_override: Optional[str] = None,
) -> SpeechCandidate:
    """Dựng bản sao `SpeechCandidate(VERIFIED)` rút gọn để `EvidenceCollector` ghi transcript chuẩn."""
    from p06.schemas.candidate import SkuVersionBinding

    origin = (
        CandidateOrigin.PREAPPROVED_FALLBACK
        if turn.outcome == AgentTurnOutcome.FALLBACK_PREAPPROVED
        else CandidateOrigin.PROACTIVE_STORY
    )
    text = played_entry_text or turn.spoken_text or "(empty)"
    duration_sec = (
        (turn.actual_duration_ms / _MS_PER_SECOND)
        if turn.actual_duration_ms is not None
        else (VirtualClock.estimate_raw_speech_duration_ms(text) / _MS_PER_SECOND)
    )
    return SpeechCandidate(
        candidate_id=turn.verified_candidate_id,
        turn_id=turn.turn_id,
        tenant_id=story_plan.tenant_id,
        session_id=story_plan.session_id,
        session_epoch=1,
        origin=origin,
        source_chunk_id=chunk_id_override or turn.chunk_id,
        scope_mode=TargetScopeMode.SINGLE_SKU,
        sku_refs=[sku_id],
        sku_bindings=[
            SkuVersionBinding(
                sku_id=sku_id,
                knowledge_version=1,
                ocop_version=1,
                rights_version=1,
                cited_evidence_ids=list(turn.cited_evidence_ids),
            )
        ],
        session_rights_version=1,
        intent=f"story_topic:{turn.topic_id}",
        text=text,
        estimated_duration_sec=min(30.0, max(0.5, duration_sec)),
        proposed_coverage=ProposedResponseCoverage(
            covered_topic_ids=(
                [turn.topic_id] if origin == CandidateOrigin.PROACTIVE_STORY else []
            ),
            covered_intents=[f"story_topic:{turn.topic_id}"],
            coverage_mode=CoverageMode.FULL,
            is_authoritative=False,
        ),
        verification_status=CandidateVerificationStatus.VERIFIED,
        verified_by_gate_decision_id=turn.p05_gate_decision_id or f"p05-allow-{turn.verified_candidate_id}",
        verified_at=datetime.now(timezone.utc),
    )


def _run_langgraph_loop(
    *,
    config: ExperimentRunConfig,
    model_yaml: Mapping[str, Any],
    story_plan: StoryPlan,
    evidence_adapter: P05KnowledgeAdapter,
    playback_bus: MockPlaybackAckBus,
    harness: SimulatedPlaybackHarness,
    clock: VirtualClock,
    llm_provider: LLMProvider,
    fallbacks_by_sku: Mapping[str, Sequence[SpeechCandidate]],
    collector: EvidenceCollector,
    outcome_overrides: Optional[Mapping[int, PlaybackOutcomeStatus]],
    prompts_dir: Optional[Path],
) -> RunTerminationReason:
    """Điều phối vòng lặp từng lượt LangGraph qua toàn bộ `pinned_sku_ids`."""
    repetition_detector = RepetitionDetector(config.repetition_config)
    deps_by_sku: dict[str, GraphRuntimeDeps] = {
        sku_id: GraphRuntimeDeps(
            llm_provider=llm_provider,
            knowledge_verifier=evidence_adapter,
            repetition_detector=repetition_detector,
            fallback_candidates=fallbacks_by_sku.get(sku_id, ()),
            clock=clock,
            prompts_dir=prompts_dir or DEFAULT_PROMPTS_DIR,
            max_chunk_duration_sec=config.max_chunk_duration_sec,
            seed=config.seed,
        )
        for sku_id in story_plan.pinned_sku_ids
    }

    sku_index = 0
    turn_index = 0
    consecutive_aborts = 0

    while True:
        if _budget_limit_reached(config, collector, model_yaml):
            return RunTerminationReason.BUDGET_LIMIT_REACHED
        if clock.elapsed_sec() >= config.target_duration_sec:
            return RunTerminationReason.TIME_BUDGET_EXHAUSTED
        if turn_index >= config.max_turns:
            return RunTerminationReason.MAX_TURNS_REACHED
        if consecutive_aborts >= config.max_consecutive_aborts:
            return RunTerminationReason.MAX_CONSECUTIVE_ABORTS

        active_sku_id = harness.checkpoint.active_sku_id
        state = harness.build_agent_state(
            story_plan,
            max_rewrite_retries=config.max_rewrite_retries,
        )
        turn_id = (
            f"turn-{story_plan.plan_id}-e{harness.checkpoint.session_epoch}-{turn_index:04d}"
        )

        turn_t0 = time.perf_counter()
        turn_res = run_storytelling_turn(
            state,
            deps_by_sku[active_sku_id],
            turn_id=turn_id,
            sequence_index=turn_index,
        )
        invocation_latency_ms = (time.perf_counter() - turn_t0) * _MS_PER_SECOND

        collector.record_langgraph_turn(
            turn_index=turn_index,
            turn_id=turn_id,
            active_sku_id=active_sku_id,
            turn_result=turn_res,
            invocation_latency_ms=invocation_latency_ms,
        )

        if turn_res.non_retryable_failure is not None:
            collector.record_error(
                turn_id=turn_id,
                stage="langgraph_turn",
                error_type="NON_RETRYABLE_FAILURE",
                message=turn_res.non_retryable_failure,
                is_retryable=False,
                sku_id=active_sku_id,
                topic_id=turn_res.final_state.selected_topic_id,
            )
            if (
                "ProviderRateLimitError" in turn_res.non_retryable_failure
                or "GLOBAL_REQUEST_BUDGET_EXCEEDED" in turn_res.non_retryable_failure
            ):
                return RunTerminationReason.BUDGET_LIMIT_REACHED

        if turn_res.should_terminate:
            sku_index += 1
            if sku_index < len(story_plan.pinned_sku_ids):
                next_sku = story_plan.pinned_sku_ids[sku_index]
                harness.switch_active_sku(
                    next_sku,
                    story_plan=story_plan,
                    updated_at=clock.now(),
                )
                turn_index += 1
                continue
            if clock.elapsed_sec() >= config.target_duration_sec:
                return RunTerminationReason.TIME_BUDGET_EXHAUSTED
            if _all_mandatory_topics_completed(story_plan, harness.completed_topic_ids):
                return RunTerminationReason.EARLY_COMPLETION
            return RunTerminationReason.CONTENT_EXHAUSTED

        outcome = turn_res.final_state.turn_outcome
        if outcome in {
            AgentTurnOutcome.VERIFIED_READY,
            AgentTurnOutcome.FALLBACK_PREAPPROVED,
        }:
            consecutive_aborts = 0
            candidate = turn_res.final_state.verified_candidate
            assert candidate is not None

            if outcome == AgentTurnOutcome.VERIFIED_READY:
                harness.register_pending_turn(
                    turn_id=turn_id,
                    candidate=candidate,
                    plan_revision=story_plan.plan_revision,
                    chunk_id=candidate.source_chunk_id,
                    next_topic_id=turn_res.next_topic_id_hint,
                    current_arc_id=turn_res.next_arc_id_hint,
                    covered_claim_ids=turn_res.covered_claim_ids,
                )
            else:
                # Không truyền next_topic_id_hint khi phát fallback để không nhảy cóc chủ đề dở dang.
                harness.register_pending_turn(
                    turn_id=turn_id,
                    candidate=candidate,
                    plan_revision=story_plan.plan_revision,
                    chunk_id=candidate.source_chunk_id,
                    covered_claim_ids=(),
                )

            override_status = (
                outcome_overrides.get(turn_index) if outcome_overrides is not None else None
            )
            ack_result = playback_bus.dispatch_turn(
                candidate=candidate,
                turn_id=turn_id,
                plan_revision=story_plan.plan_revision,
                outcome_override=override_status,
            )
            apply_result = harness.apply_ack(ack_result)
            gate_id = (
                turn_res.p05_decisions[-1].gate_decision_id
                if turn_res.p05_decisions
                else candidate.verified_by_gate_decision_id
            )
            collector.record_playback_outcome(
                turn_id=turn_id,
                sku_id=active_sku_id,
                candidate=candidate,
                ack_result=ack_result,
                applied=apply_result.applied,
                apply_status=apply_result.status,
                apply_reason=apply_result.reason,
                apply_result=apply_result,
                topic_id=turn_res.final_state.selected_topic_id,
                arc_id=turn_res.final_state.selected_arc_id,
                chunk_id=candidate.source_chunk_id,
                covered_claim_ids=turn_res.covered_claim_ids,
                proposed_topic_ids=candidate.proposed_coverage.covered_topic_ids,
                is_fallback=(outcome == AgentTurnOutcome.FALLBACK_PREAPPROVED),
                gate_decision_id=gate_id,
            )
            if not apply_result.applied:
                collector.record_error(
                    turn_id=turn_id,
                    stage="playback_ack",
                    error_type=f"PLAYBACK_{apply_result.status.value}",
                    message=apply_result.reason or ack_result.failure_reason or "Playback ACK rejected",
                    sku_id=active_sku_id,
                    topic_id=turn_res.final_state.selected_topic_id,
                )
        else:
            consecutive_aborts += 1
            collector.record_error(
                turn_id=turn_id,
                stage="safe_fallback",
                error_type="SAFE_ABORT_NO_CANDIDATE",
                message=turn_res.non_retryable_failure
                or "Không có ứng viên hoặc câu dự phòng hợp lệ.",
                is_retryable=False,
                sku_id=active_sku_id,
                topic_id=turn_res.final_state.selected_topic_id,
            )

        turn_index += 1


def run_experiment(
    config: ExperimentRunConfig,
    *,
    story_plan: Optional[StoryPlan] = None,
    evaluator: Optional[Callable[[RunEvidence], EvaluationReport]] = None,
    custom_llm_provider: Optional[LLMProvider] = None,
    outcome_overrides: Optional[Mapping[int, PlaybackOutcomeStatus]] = None,
    fallback_candidates: Optional[Sequence[SpeechCandidate]] = None,
    evidence_seed_path: Optional[Path] = None,
    story_plans_path: Optional[Path] = None,
    prompts_dir: Optional[Path] = None,
    run_id: Optional[str] = None,
) -> ExperimentRunnerResult:
    """Thực thi trọn vẹn một lượt chạy thí nghiệm cô lập và lưu 10 tệp artifact xuống đĩa.

    Args:
        config: Cấu hình chạy thực nghiệm đã kiểm định (`ExperimentRunConfig`).
        story_plan: `StoryPlan` tùy chọn (mặc định nạp từ `e01_story_plans.json` theo `scenario`).
        evaluator: Hàm đánh giá `RunEvidence -> EvaluationReport` (mặc định gọi lười `evaluate_run`).
        custom_llm_provider: `LLMProvider` tiêm từ ngoài phục vụ kiểm thử lỗi/retry.
        outcome_overrides: Ánh xạ `turn_index -> PlaybackOutcomeStatus` để mô phỏng lỗi P04 ACK.
        fallback_candidates: Danh sách câu dự phòng tiêm từ ngoài (truyền `()` để tắt fallback).
        evidence_seed_path: Đường dẫn tệp JSON tri thức SKU (mặc định `e01_verified_skus.json`).
        story_plans_path: Đường dẫn tệp JSON kế hoạch (mặc định `e01_story_plans.json`).
        prompts_dir: Thư mục chứa prompt template (mặc định `prompts/`).
        run_id: Định danh `run_id` tùy chọn (mặc định tự sinh kèm UTC timestamp và UUID ngắn).

    Returns:
        ExperimentRunnerResult: Kết quả bất biến gồm `run_id`, `run_dir`, `manifest`, `evidence`, `report`.

    Raises:
        ProviderConfigError: Nếu vi phạm rào chắn ngoại tuyến đối với `ollama` / `gemini`.
        FileExistsError: Nếu `output_dir / run_id` đã tồn tại trước đó.
    """
    if (
        config.provider in LIVE_PROVIDERS
        and not config.allow_live_provider
        and custom_llm_provider is None
    ):
        raise ProviderConfigError(
            f"Offline Guard: từ chối chạy provider '{config.provider}' khi allow_live_provider=False."
        )

    model_yaml = load_yaml_mapping(config.model_config_path)
    yaml_provider = str(model_yaml.get("provider", config.provider)).strip().lower()
    if (
        yaml_provider in LIVE_PROVIDERS
        and not config.allow_live_provider
        and custom_llm_provider is None
    ):
        raise ProviderConfigError(
            f"Offline Guard: tệp model '{config.model_config_path}' khai báo '{yaml_provider}' "
            f"nhưng allow_live_provider=False."
        )

    started_at_utc = datetime.now(timezone.utc)
    run_t0 = time.perf_counter()

    profile_cfg = resolve_dataset_profile(config.dataset_profile)
    resolved_seed_path = (
        evidence_seed_path
        or config.evidence_seed_path
        or Path(profile_cfg["evidence_seed_path"])
    ).resolve()
    resolved_plans_path_override = (
        story_plans_path
        or config.story_plans_path
        or Path(profile_cfg["story_plans_path"])
    )
    dataset_files: list[Path] = [resolved_seed_path]
    dataset_meta: dict[str, Any] = {}
    if story_plan is None:
        loaded_plan, dataset_meta, resolved_plans_path = load_e01_story_plan(
            config.scenario,
            story_plans_path=resolved_plans_path_override,
        )
        resolved_plan = loaded_plan
        dataset_files.append(resolved_plans_path)
    else:
        resolved_plan = story_plan

    resolved_run_id = run_id or generate_run_id(
        config.experiment_id,
        config.scenario,
        config.method,
        config.history_window,
    )

    clock = VirtualClock()
    virtual_clock_start_utc = clock.now()
    evidence_adapter = P05KnowledgeAdapter.from_seed_file(resolved_seed_path)
    initial_sku = resolved_plan.pinned_sku_ids[0]
    first_arc_id, first_topic_id = _find_initial_arc_and_topic(resolved_plan, initial_sku)
    initial_checkpoint = StoryCheckpoint(
        tenant_id=resolved_plan.tenant_id,
        session_id=resolved_plan.session_id,
        session_epoch=1,
        plan_id=resolved_plan.plan_id,
        plan_revision=resolved_plan.plan_revision,
        active_sku_id=initial_sku,
        current_arc_id=first_arc_id,
        next_topic_id=first_topic_id,
        updated_at=clock.now(),
    )

    effective_window = (
        config.history_window
        if config.history_window is not None
        else DEFAULT_PLAYED_HISTORY_WINDOW
    )
    played_history = ShortTermPlayedHistory(
        window_size=effective_window,
        tenant_id=resolved_plan.tenant_id,
        session_id=resolved_plan.session_id,
        session_epoch=1,
    )
    topic_coverage = GlobalTopicCoverage(
        resolved_plan,
        min_chunks_per_topic=config.min_chunks_per_topic,
    )
    viewer_context = SessionViewerContext(
        tenant_id=resolved_plan.tenant_id,
        session_id=resolved_plan.session_id,
        session_epoch=1,
    )
    harness = SimulatedPlaybackHarness(
        initial_checkpoint=initial_checkpoint,
        expected_simulation_run_id=resolved_run_id,
        played_history_window_size=effective_window,
        story_plan=resolved_plan,
        played_history=played_history,
        topic_coverage=topic_coverage,
        viewer_context=viewer_context,
        semantic_memory=NoOpSemanticMemory(),
        min_chunks_per_topic=config.min_chunks_per_topic,
    )
    playback_bus = MockPlaybackAckBus(clock=clock, simulation_run_id=resolved_run_id)

    if fallback_candidates is not None:
        fallbacks_by_sku: dict[str, Sequence[SpeechCandidate]] = {
            sku_id: _filter_fallbacks_for_sku(fallback_candidates, sku_id)
            for sku_id in resolved_plan.pinned_sku_ids
        }
    else:
        fallbacks_by_sku = _build_default_fallbacks_by_sku(
            story_plan=resolved_plan,
            evidence_adapter=evidence_adapter,
            at_time=clock.now(),
            session_epoch=1,
        )

    configured_model_id = str(model_yaml.get("model_id", DEFAULT_MOCK_MODEL_ID))
    llm_provider: Optional[LLMProvider]
    if custom_llm_provider is not None:
        llm_provider = custom_llm_provider
    elif config.method == ExperimentMethod.SCRIPT_FIRST_DETERMINISTIC:
        llm_provider = None
    elif config.provider == "mock":
        llm_provider = build_e01_mock_provider(
            resolved_plan,
            evidence_adapter,
            seed=config.seed,
            model_id=configured_model_id,
            at_time=clock.now(),
            include_claim_ids=(config.method == ExperimentMethod.LANGGRAPH),
            min_chunks_per_topic=config.min_chunks_per_topic,
        )
    else:
        llm_provider = ProviderFactory.from_yaml(
            config.model_config_path,
            allow_live_client=config.allow_live_provider,
        )

    collector = EvidenceCollector(
        resolved_plan,
        target_duration_sec=config.target_duration_sec,
    )

    extra_prompt_version: Optional[str] = None
    extra_prompt_sha256: Optional[str] = None
    try:
        if config.method == ExperimentMethod.LANGGRAPH:
            assert llm_provider is not None
            termination_reason = _run_langgraph_loop(
                config=config,
                model_yaml=model_yaml,
                story_plan=resolved_plan,
                evidence_adapter=evidence_adapter,
                playback_bus=playback_bus,
                harness=harness,
                clock=clock,
                llm_provider=llm_provider,
                fallbacks_by_sku=fallbacks_by_sku,
                collector=collector,
                outcome_overrides=outcome_overrides,
                prompts_dir=prompts_dir,
            )
        else:
            (
                termination_reason,
                extra_prompt_version,
                extra_prompt_sha256,
            ) = _run_script_first_loop(
                config=config,
                model_yaml=model_yaml,
                story_plan=resolved_plan,
                evidence_adapter=evidence_adapter,
                playback_bus=playback_bus,
                harness=harness,
                clock=clock,
                llm_provider=llm_provider,
                fallbacks_by_sku=fallbacks_by_sku,
                collector=collector,
                outcome_overrides=outcome_overrides,
            )
    except Exception as exc:  # noqa: BLE001 - Bảo toàn lịch sử chạy lỗi với FATAL_ERROR thay vì mất dấu vết.
        collector.record_error(
            stage="session_runner",
            error_type=type(exc).__name__,
            message=str(exc) or type(exc).__name__,
            is_retryable=False,
            sku_id=harness.checkpoint.active_sku_id,
        )
        termination_reason = RunTerminationReason.FATAL_ERROR

    finished_at_utc = datetime.now(timezone.utc)
    collector.total_measured_processing_ms = (time.perf_counter() - run_t0) * _MS_PER_SECOND
    collector.simulated_elapsed_sec = clock.elapsed_sec()

    token_usage_summary = collector.build_token_usage_summary()
    provider_name = (
        llm_provider.provider_name
        if llm_provider is not None
        else ("deterministic" if config.method == ExperimentMethod.SCRIPT_FIRST_DETERMINISTIC else config.provider)
    )
    provider_tier = (
        llm_provider.tier.value
        if llm_provider is not None
        else str(model_yaml.get("run_tier", ProviderTier.UNIT_TEST.value))
    )
    model_id = (
        llm_provider.model_id
        if llm_provider is not None
        else (
            "deterministic-talking-points-v0.1"
            if config.method == ExperimentMethod.SCRIPT_FIRST_DETERMINISTIC
            else configured_model_id
        )
    )

    manifest = build_experiment_manifest(
        run_id=resolved_run_id,
        config=config,
        story_plan=resolved_plan,
        model_yaml=model_yaml,
        provider_name=provider_name,
        provider_tier=provider_tier,
        model_id=model_id,
        started_at_utc=started_at_utc,
        finished_at_utc=finished_at_utc,
        termination_reason=termination_reason,
        token_usage_summary=token_usage_summary,
        planning_latency_ms=collector.planning_latency_ms,
        upfront_script_generation_latency_ms=collector.upfront_script_generation_latency_ms,
        total_measured_processing_ms=collector.total_measured_processing_ms,
        simulated_elapsed_sec=collector.simulated_elapsed_sec,
        virtual_clock_start_utc=virtual_clock_start_utc,
        dataset_meta=dataset_meta,
        dataset_files=dataset_files,
        prompts_dir=prompts_dir,
        extra_prompt_version=extra_prompt_version,
        extra_prompt_sha256=extra_prompt_sha256,
    )
    evidence = collector.to_run_evidence(manifest)

    resolved_evaluator = evaluator if evaluator is not None else _resolve_default_evaluator()
    report: Optional[EvaluationReport] = (
        resolved_evaluator(evidence) if resolved_evaluator is not None else None
    )

    run_dir = persist_run_artifacts(
        output_dir=config.output_dir,
        run_id=resolved_run_id,
        manifest=manifest,
        config=config,
        model_yaml=model_yaml,
        evidence=evidence,
        report=report,
        token_usage_summary=token_usage_summary,
    )

    return ExperimentRunnerResult(
        run_id=resolved_run_id,
        run_dir=run_dir,
        manifest=manifest,
        evidence=evidence,
        report=report,
        termination_reason=termination_reason,
    )
