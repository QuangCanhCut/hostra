"""Bộ thu thập bằng chứng thô trung thực theo từng lượt chạy (`EvidenceCollector`).

1. File này giải quyết vấn đề gì?
   Tách biệt hoàn toàn công đoạn ghi nhận dữ liệu thô (`transcript`, `playback_events`,
   `graph_trace`, `provider_calls`, `errors`, `token_usage`) khỏi công đoạn tính toán metric
   trong `p06.evaluation`, bảo đảm không bịa số `0` khi thiếu telemetry và không ghi nhầm
   ứng viên chưa phát vào transcript.
2. Trách nhiệm chính của module là gì?
   Cung cấp lớp `EvidenceCollector` tích lũy `TranscriptEntry`, `PlaybackEventRecord`,
   `GraphTraceRecord`, `ProviderCallRecord`, `ErrorRecord`, tính tóm tắt `token_usage.json`
   trung thực provenance, và xuất `RunEvidence`.
3. Module này liên kết với các thành phần nào?
   Tiêu thụ DTO từ `p06.evaluation.models`, `p06.agent.deps`, `p06.baselines.script_first`,
   `p06.adapters.interfaces`, `p06.providers.base` và `p06.schemas`.
4. Input và output chính là gì?
   Input là kết quả từng lượt LangGraph hoặc `BaselineSessionResult` cùng ACK phát sóng;
   Output là `RunEvidence` bất biến và bảng tổng hợp `token_usage.json`.
5. Có những constraints hoặc invariants quan trọng nào?
   - `TranscriptEntry` CHỈ được ghi khi `applied is True` và `outcome == COMPLETED` (`I-03`/`I-06`).
   - Mọi `ProviderTelemetry` (kể cả lỗi và bản viết lại bị loại) đều ghi vào `provider_calls`,
     trong đó chỉ lượt gọi thắng cuộc cuối cùng của ứng viên được chấp nhận mới đặt `is_wasted=False`.
   - Khi `total_model_calls == 0` hoặc có bất kỳ lượt gọi `UNAVAILABLE`, tổng hợp token
     bắt buộc giữ giá trị `None` và `token_usage_source="UNAVAILABLE"`, tuyệt đối không bịa `0`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Optional

from p06.adapters.interfaces import AckApplyStatus, PlaybackAckResult, PlaybackApplyResult
from p06.agent.deps import AgentTurnResult
from p06.baselines.script_first import BaselineSessionResult, BaselineTurnRecord
from p06.evaluation.models import (
    ErrorRecord,
    GraphTraceRecord,
    PlaybackEventRecord,
    ProviderCallRecord,
    RunEvidence,
    TranscriptEntry,
)
from p06.providers.base import ProviderTelemetry, TokenUsageSource
from p06.runner.config import ExperimentMethod
from p06.schemas.candidate import SpeechCandidate
from p06.schemas.events import PlaybackOutcomeStatus
from p06.schemas.state import AgentTurnOutcome
from p06.schemas.story import StoryPlan


def _collect_cited_evidence_ids(candidate: SpeechCandidate) -> tuple[str, ...]:
    """Gom toàn bộ `evidence_id` đã trích dẫn từ các `sku_bindings` của ứng viên."""
    collected: list[str] = []
    for binding in candidate.sku_bindings:
        for eid in binding.cited_evidence_ids:
            if eid not in collected:
                collected.append(eid)
    return tuple(collected)


class EvidenceCollector:
    """Bộ tích lũy bằng chứng thô cho một phiên chạy thí nghiệm P06-E01 độc lập."""

    def __init__(
        self,
        story_plan: StoryPlan,
        *,
        target_duration_sec: float = 600.0,
    ) -> None:
        """Khởi tạo bộ thu thập bằng chứng cho một phiên chạy đơn lẻ.

        Args:
            story_plan: Kế hoạch kể chuyện đã `APPROVED` của phiên chạy.
            target_duration_sec: Ngân sách thời lượng mô phỏng mục tiêu (giây).
        """
        self._story_plan: StoryPlan = story_plan
        self._target_duration_sec: float = float(target_duration_sec)
        self._transcript: list[TranscriptEntry] = []
        self._playback_events: list[PlaybackEventRecord] = []
        self._graph_traces: list[GraphTraceRecord] = []
        self._provider_calls: list[ProviderCallRecord] = []
        self._errors: list[ErrorRecord] = []
        self.planning_latency_ms: float = 0.0
        self.upfront_script_generation_latency_ms: float = 0.0
        self.total_measured_processing_ms: float = 0.0
        self.simulated_elapsed_sec: float = 0.0

    @property
    def transcript(self) -> tuple[TranscriptEntry, ...]:
        """Danh sách các lượt thoại thực sự đã phát thành công (`APPLIED` + `COMPLETED`)."""
        return tuple(self._transcript)

    @property
    def playback_events(self) -> tuple[PlaybackEventRecord, ...]:
        """Danh sách toàn bộ sự kiện ACK phát sóng (bao gồm cả thất bại hoặc bị từ chối)."""
        return tuple(self._playback_events)

    @property
    def graph_traces(self) -> tuple[GraphTraceRecord, ...]:
        """Danh sách dấu vết thực thi từng lượt của Agent hoặc Baseline."""
        return tuple(self._graph_traces)

    @property
    def provider_calls(self) -> tuple[ProviderCallRecord, ...]:
        """Danh sách mọi lượt gọi `LLMProvider` đã ghi nhận."""
        return tuple(self._provider_calls)

    @property
    def errors(self) -> tuple[ErrorRecord, ...]:
        """Danh sách các lỗi, từ chối P05 hoặc safe abort trong phiên chạy."""
        return tuple(self._errors)

    def record_error(
        self,
        *,
        stage: str,
        error_type: str,
        message: str,
        turn_id: Optional[str] = None,
        is_retryable: Optional[bool] = None,
        sku_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        occurred_at_utc: Optional[str] = None,
    ) -> ErrorRecord:
        """Ghi nhận một sự cố hoặc quyết định từ chối vào danh sách `errors`.

        Args:
            stage: Giai đoạn xảy ra sự cố (vd: `draft_chunk`, `verify_p05`, `playback_ack`).
            error_type: Mã phân loại lỗi.
            message: Mô tả chi tiết phục vụ phân tích lỗi.
            turn_id: Mã lượt liên quan (nếu có).
            is_retryable: Lỗi có khả năng retry hay không (nếu xác định được).
            sku_id: Mã SKU đang hoạt động tại thời điểm lỗi.
            topic_id: Mã chủ đề liên quan (nếu có).
            occurred_at_utc: Dấu thời gian UTC xảy ra sự cố.

        Returns:
            ErrorRecord: Bản ghi lỗi bất biến vừa được thêm.
        """
        record = ErrorRecord(
            error_index=len(self._errors),
            turn_id=turn_id,
            stage=stage,
            error_type=error_type,
            message=message,
            is_retryable=is_retryable,
            sku_id=sku_id,
            topic_id=topic_id,
            occurred_at_utc=occurred_at_utc,
        )
        self._errors.append(record)
        return record

    def record_provider_call(
        self,
        telemetry: ProviderTelemetry,
        *,
        turn_id: Optional[str] = None,
        request_id: Optional[str] = None,
        is_wasted: bool = False,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> ProviderCallRecord:
        """Ghi nhận một lượt gọi `LLMProvider` từ `ProviderTelemetry`.

        Args:
            telemetry: Telemetry bất biến trả về từ provider hoặc ngoại lệ `ProviderError`.
            turn_id: Mã lượt gắn với lệnh gọi.
            request_id: Mã định danh request gửi tới provider.
            is_wasted: `True` nếu lượt gọi bị lỗi, bị từ chối hoặc thuộc lần thử rewrite bị loại.
            error_type: Tên lớp lỗi nếu có.
            error_message: Thông điệp lỗi nếu có.

        Returns:
            ProviderCallRecord: Bản ghi cuộc gọi LLM đã lưu.
        """
        record = ProviderCallRecord(
            call_index=len(self._provider_calls),
            turn_id=turn_id,
            request_id=request_id,
            provider_name=telemetry.provider_name,
            model_id=telemetry.model_id,
            tier=telemetry.tier.value,
            latency_ms=telemetry.latency_ms,
            is_simulated_metric=telemetry.is_simulated_metric,
            input_tokens=telemetry.input_tokens,
            output_tokens=telemetry.output_tokens,
            thinking_tokens=telemetry.thinking_tokens,
            token_usage_source=telemetry.token_usage_source.value,
            finish_reason=telemetry.finish_reason,
            raw_response_valid=telemetry.raw_response_valid,
            is_wasted=is_wasted,
            error_type=error_type,
            error_message=error_message,
        )
        self._provider_calls.append(record)
        return record

    def record_playback_outcome(
        self,
        *,
        turn_id: str,
        sku_id: str,
        candidate: Optional[SpeechCandidate],
        ack_result: PlaybackAckResult,
        applied: bool,
        apply_status: AckApplyStatus,
        apply_reason: Optional[str] = None,
        semantic_index_error: Optional[str] = None,
        topic_id: Optional[str] = None,
        arc_id: Optional[str] = None,
        chunk_id: Optional[str] = None,
        covered_claim_ids: Sequence[str] = (),
        proposed_topic_ids: Sequence[str] = (),
        is_fallback: bool = False,
        gate_decision_id: Optional[str] = None,
        apply_result: Optional[PlaybackApplyResult] = None,
    ) -> None:
        """Ghi nhận kết quả ACK phát sóng và CHỈ ghi `TranscriptEntry` khi phát thành công (`I-06`).

        Args:
            turn_id: Mã lượt phát sóng.
            sku_id: Mã SKU đang hoạt động.
            candidate: Ứng viên `SpeechCandidate` đã gửi phát (nếu có).
            ack_result: Kết quả ACK trả về từ `PlaybackAckBusPort`.
            applied: Cờ xác nhận `SimulatedPlaybackHarness` đã chấp nhận và cập nhật tiến độ.
            apply_status: Trạng thái xử lý ACK chi tiết (`AckApplyStatus`).
            apply_reason: Lý do nếu ACK bị bỏ qua hoặc từ chối.
            semantic_index_error: Lỗi không nghiêm trọng từ semantic memory (nếu có).
            topic_id: Mã chủ đề chính của lượt (nếu có).
            arc_id: Mã arc của lượt (nếu có).
            chunk_id: Mã `StoryChunk` (nếu có).
            covered_claim_ids: Các `claim_id` gắn với lượt.
            proposed_topic_ids: Các `topic_id` ứng viên đề xuất phủ.
            is_fallback: `True` nếu lượt sử dụng câu dự phòng an toàn.
            gate_decision_id: Mã quyết định `ALLOW` từ Cổng P05.
            apply_result: Đối tượng `PlaybackApplyResult` gốc (nếu truyền sẽ ưu tiên đồng bộ trường).
        """
        effective_applied = apply_result.applied if apply_result is not None else applied
        effective_status = apply_result.status if apply_result is not None else apply_status
        effective_reason = apply_result.reason if apply_result is not None else apply_reason
        effective_sem_err = (
            apply_result.semantic_index_error
            if apply_result is not None
            else semantic_index_error
        )

        event = ack_result.event
        resolved_chunk_id = (
            chunk_id
            or (event.chunk_id if event is not None else None)
            or (candidate.source_chunk_id if candidate is not None else None)
        )
        pb_record = PlaybackEventRecord(
            sequence_index=len(self._playback_events),
            turn_id=turn_id,
            candidate_id=ack_result.candidate_id,
            chunk_id=resolved_chunk_id,
            sku_id=sku_id,
            outcome=ack_result.outcome.value,
            apply_status=effective_status.value,
            applied=effective_applied,
            playback_event_id=event.playback_event_id if event is not None else None,
            actual_duration_ms=event.actual_duration_ms if event is not None else None,
            confirmed_topic_ids=tuple(event.confirmed_topic_ids) if event is not None else (),
            covered_claim_ids=tuple(covered_claim_ids),
            occurred_at_utc=event.occurred_at.isoformat() if event is not None else None,
            failure_reason=ack_result.failure_reason or effective_reason,
            semantic_index_error=effective_sem_err,
        )
        self._playback_events.append(pb_record)

        # Bất biến I-03 / I-06: Chỉ ứng viên thực sự nhận ACK COMPLETED và APPLIED mới vào transcript.
        if (
            effective_applied is True
            and ack_result.outcome == PlaybackOutcomeStatus.COMPLETED
            and event is not None
            and candidate is not None
        ):
            resolved_topic_id = topic_id
            if resolved_topic_id is None and event.confirmed_topic_ids:
                resolved_topic_id = event.confirmed_topic_ids[0]
            resolved_proposed = (
                tuple(proposed_topic_ids)
                if proposed_topic_ids
                else tuple(candidate.proposed_coverage.covered_topic_ids)
            )
            transcript_entry = TranscriptEntry(
                turn_index=len(self._transcript),
                turn_id=turn_id,
                sku_id=sku_id,
                topic_id=resolved_topic_id,
                arc_id=arc_id,
                chunk_id=resolved_chunk_id,
                candidate_id=candidate.candidate_id,
                origin=candidate.origin.value,
                intent=candidate.intent,
                text=event.spoken_text,
                cited_evidence_ids=_collect_cited_evidence_ids(candidate),
                covered_claim_ids=tuple(covered_claim_ids),
                proposed_topic_ids=resolved_proposed,
                confirmed_topic_ids=tuple(event.confirmed_topic_ids),
                actual_duration_ms=event.actual_duration_ms,
                playback_event_id=event.playback_event_id,
                occurred_at_utc=event.occurred_at.isoformat(),
                is_fallback=is_fallback,
                verification_status=candidate.verification_status.value,
                gate_decision_id=gate_decision_id or candidate.verified_by_gate_decision_id,
            )
            self._transcript.append(transcript_entry)

    def record_langgraph_turn(
        self,
        *,
        turn_index: int,
        turn_id: str,
        active_sku_id: str,
        turn_result: AgentTurnResult,
        invocation_latency_ms: float,
    ) -> GraphTraceRecord:
        """Ghi nhận dấu vết đồ thị và toàn bộ telemetry LLM của một lượt LangGraph.

        Args:
            turn_index: Chỉ số thứ tự lượt trong phiên.
            turn_id: Mã lượt duy nhất.
            active_sku_id: Mã SKU active ở đầu lượt.
            turn_result: Kết quả `AgentTurnResult` trả về từ `run_storytelling_turn`.
            invocation_latency_ms: Thời gian xử lý thực đo trên đồng hồ thật (ms).

        Returns:
            GraphTraceRecord: Bản ghi dấu vết lượt vừa tạo.
        """
        final_state = turn_result.final_state
        outcome = final_state.turn_outcome
        verified = final_state.verified_candidate
        proposed_topics = (
            tuple(verified.proposed_coverage.covered_topic_ids)
            if verified is not None
            else ()
        )
        verified_topics = proposed_topics if outcome == AgentTurnOutcome.VERIFIED_READY else ()
        chunk_id = (
            verified.source_chunk_id
            if verified is not None and verified.source_chunk_id is not None
            else (final_state.draft_chunk.chunk_id if final_state.draft_chunk is not None else None)
        )

        trace = GraphTraceRecord(
            turn_index=turn_index,
            turn_id=turn_id,
            method=ExperimentMethod.LANGGRAPH.value,
            active_sku_id=active_sku_id,
            selected_arc_id=final_state.selected_arc_id,
            selected_topic_id=final_state.selected_topic_id,
            node_trace=tuple(final_state.node_trace),
            turn_outcome=outcome.value,
            retries_used=final_state.rewrite_budget.retries_used,
            max_retries=final_state.rewrite_budget.max_retries,
            used_fallback=(outcome == AgentTurnOutcome.FALLBACK_PREAPPROVED),
            should_terminate=turn_result.should_terminate,
            termination_reason=turn_result.termination_reason,
            non_retryable_failure=turn_result.non_retryable_failure,
            invocation_latency_ms=float(invocation_latency_ms),
            draft_attempts=tuple(item.model_dump(mode="json") for item in turn_result.draft_attempts),
            repetition_checks=tuple(
                item.model_dump(mode="json") for item in turn_result.repetition_checks
            ),
            p05_decisions=tuple(item.model_dump(mode="json") for item in turn_result.p05_decisions),
            proposed_topic_ids=proposed_topics,
            verified_topic_ids=verified_topics,
            covered_claim_ids=tuple(turn_result.covered_claim_ids),
            candidate_id=verified.candidate_id if verified is not None else None,
            chunk_id=chunk_id,
        )
        self._graph_traces.append(trace)

        telemetry_list = turn_result.telemetry_records
        last_idx = len(telemetry_list) - 1
        for idx, telemetry in enumerate(telemetry_list):
            is_winning_call = (
                outcome == AgentTurnOutcome.VERIFIED_READY
                and idx == last_idx
                and telemetry.raw_response_valid
            )
            self.record_provider_call(
                telemetry,
                turn_id=turn_id,
                is_wasted=not is_winning_call,
                error_type=None if telemetry.raw_response_valid else "INVALID_OR_FAILED_CALL",
            )

        return trace

    def record_baseline_turn(
        self,
        *,
        turn_index: int,
        method: ExperimentMethod,
        active_sku_id: str,
        turn: BaselineTurnRecord,
        invocation_latency_ms: float = 0.0,
        chunk_id_override: Optional[str] = None,
    ) -> GraphTraceRecord:
        """Ghi nhận dấu vết thực thi của một lượt `ScriptFirstBaseline`.

        Args:
            turn_index: Chỉ số lượt toàn cục trong phiên chạy.
            method: Phương pháp baseline (`SCRIPT_FIRST_DETERMINISTIC` hoặc `SCRIPT_FIRST_UPFRONT_LLM`).
            active_sku_id: Mã SKU active của lượt.
            turn: Bản ghi `BaselineTurnRecord` từ `ScriptFirstBaseline.run_session`.
            invocation_latency_ms: Độ trễ đo được phân bổ (ms).

        Returns:
            GraphTraceRecord: Bản ghi dấu vết chuẩn hóa tương thích với tầng đánh giá.
        """
        if turn.outcome == AgentTurnOutcome.VERIFIED_READY:
            node_trace = ("prepare_upfront_script", "verify_p05", "finalize_candidate")
            proposed_topics: tuple[str, ...] = (turn.topic_id,)
            verified_topics: tuple[str, ...] = (turn.topic_id,)
        elif turn.outcome == AgentTurnOutcome.FALLBACK_PREAPPROVED:
            node_trace = ("prepare_upfront_script", "verify_p05", "safe_fallback", "finalize_candidate")
            proposed_topics = ()
            verified_topics = ()
        else:
            node_trace = ("prepare_upfront_script", "verify_p05", "safe_fallback", "finalize_candidate")
            proposed_topics = ()
            verified_topics = ()

        p05_decisions: tuple[dict[str, Any], ...] = ()
        if turn.p05_rejected or turn.p05_gate_decision_id is not None:
            p05_decisions = (
                {
                    "attempt": 0,
                    "candidate_id": turn.verified_candidate_id or turn.chunk_id,
                    "status": "REJECTED" if turn.p05_rejected else "VERIFIED",
                    "gate_decision_id": turn.p05_gate_decision_id,
                    "reasons": list(turn.p05_rejection_reasons),
                    "is_non_retryable": False,
                },
            )

        trace = GraphTraceRecord(
            turn_index=turn_index,
            turn_id=turn.turn_id,
            method=method.value,
            active_sku_id=active_sku_id,
            selected_arc_id=turn.arc_id,
            selected_topic_id=turn.topic_id,
            node_trace=node_trace,
            turn_outcome=turn.outcome.value,
            retries_used=0,
            max_retries=0,
            used_fallback=(turn.outcome == AgentTurnOutcome.FALLBACK_PREAPPROVED),
            should_terminate=False,
            invocation_latency_ms=float(invocation_latency_ms),
            p05_decisions=p05_decisions,
            proposed_topic_ids=proposed_topics,
            verified_topic_ids=verified_topics,
            covered_claim_ids=tuple(turn.covered_claim_ids),
            candidate_id=turn.verified_candidate_id,
            chunk_id=chunk_id_override or turn.chunk_id,
        )
        self._graph_traces.append(trace)
        return trace

    def record_baseline_telemetry_and_errors(
        self,
        *,
        session_result: BaselineSessionResult,
        active_sku_id: str,
    ) -> None:
        """Ghi nhận telemetry và danh sách lỗi phát sinh trong một lượt chạy `BaselineSessionResult`.

        Args:
            session_result: Kết quả trả về từ `ScriptFirstBaseline.run_session`.
            active_sku_id: Mã SKU của phân đoạn phiên chạy.
        """
        discarded_by_turn = {
            str(d["turn_id"]): d
            for d in session_result.discarded_candidates
            if d.get("turn_id") is not None
        }
        # Khớp theo vị trí 1-1 với lượt trong BaselineSessionResult (mỗi item hợp lệ gọi LLM đúng 1 lần).
        # Các cuộc gọi dư sau điểm dừng sớm (nếu có) mang matched_turn=None và tính is_wasted=True.
        for idx, telemetry in enumerate(session_result.telemetry_records):
            matched_turn: Optional[BaselineTurnRecord] = (
                session_result.turns[idx] if idx < len(session_result.turns) else None
            )
            is_winning = (
                telemetry.raw_response_valid
                and matched_turn is not None
                and matched_turn.outcome == AgentTurnOutcome.VERIFIED_READY
            )
            error_type: Optional[str] = None
            discard_info = discarded_by_turn.get(matched_turn.turn_id) if matched_turn is not None else None
            gen_err = discard_info.get("generation_error") if discard_info is not None else None
            if not telemetry.raw_response_valid:
                error_type = "UPFRONT_GENERATION_FAILED"
            elif isinstance(gen_err, str) and "OVER_MAX_DURATION_SEC" in gen_err:
                error_type = "OVER_MAX_DURATION_SEC"
            elif (
                matched_turn is not None
                and matched_turn.failure_reason is not None
                and "OVER_MAX_DURATION_SEC" in matched_turn.failure_reason
            ):
                error_type = "OVER_MAX_DURATION_SEC"
            self.record_provider_call(
                telemetry,
                turn_id=matched_turn.turn_id if matched_turn is not None else None,
                is_wasted=not is_winning,
                error_type=error_type,
            )

        for raw_err in session_result.errors:
            self.record_error(
                turn_id=raw_err.get("turn_id"),
                stage=str(raw_err.get("stage", "baseline")),
                error_type=str(raw_err.get("error_type", "BASELINE_ERROR")),
                message=str(raw_err.get("message", "Unknown baseline error")),
                sku_id=raw_err.get("sku_id", active_sku_id),
                topic_id=raw_err.get("topic_id"),
            )

    def build_token_usage_summary(self) -> dict[str, Any]:
        """Tổng hợp thống kê token cho `token_usage.json` theo nguyên tắc không bịa `0`.

        Returns:
            dict[str, Any]: Bản tóm tắt gồm tổng token, token lãng phí và `token_usage_source`.
        """
        total_calls = len(self._provider_calls)
        wasted_calls = sum(1 for call in self._provider_calls if call.is_wasted)
        has_unavailable = total_calls == 0 or any(
            call.token_usage_source == TokenUsageSource.UNAVAILABLE.value
            or call.input_tokens is None
            or call.output_tokens is None
            for call in self._provider_calls
        )

        if has_unavailable:
            input_tokens: Optional[int] = None
            output_tokens: Optional[int] = None
            thinking_tokens: Optional[int] = None
            total_tokens: Optional[int] = None
            wasted_input_tokens: Optional[int] = None
            wasted_output_tokens: Optional[int] = None
            wasted_tokens: Optional[int] = None
            source = TokenUsageSource.UNAVAILABLE.value
        else:
            input_tokens = sum(
                call.input_tokens for call in self._provider_calls if call.input_tokens is not None
            )
            output_tokens = sum(
                call.output_tokens for call in self._provider_calls if call.output_tokens is not None
            )
            thinking_vals = [call.thinking_tokens for call in self._provider_calls if call.thinking_tokens is not None]
            thinking_tokens = sum(thinking_vals) if thinking_vals else 0
            total_tokens = input_tokens + output_tokens + thinking_tokens
            wasted_input_tokens = sum(
                call.input_tokens
                for call in self._provider_calls
                if call.is_wasted and call.input_tokens is not None
            )
            wasted_output_tokens = sum(
                call.output_tokens
                for call in self._provider_calls
                if call.is_wasted and call.output_tokens is not None
            )
            wasted_thinking_tokens = sum(
                call.thinking_tokens
                for call in self._provider_calls
                if call.is_wasted and call.thinking_tokens is not None
            )
            wasted_tokens = wasted_input_tokens + wasted_output_tokens + wasted_thinking_tokens
            has_simulated = any(
                call.token_usage_source == TokenUsageSource.SIMULATED.value
                for call in self._provider_calls
            )
            source = (
                TokenUsageSource.SIMULATED.value
                if has_simulated
                else TokenUsageSource.MEASURED.value
            )

        return {
            "total_model_calls": total_calls,
            "wasted_model_calls": wasted_calls,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "thinking_tokens": thinking_tokens,
            "total_tokens": total_tokens,
            "wasted_input_tokens": wasted_input_tokens,
            "wasted_output_tokens": wasted_output_tokens,
            "wasted_tokens": wasted_tokens,
            "token_usage_source": source,
            "is_simulated_metric": any(call.is_simulated_metric for call in self._provider_calls),
            "provider_tiers": sorted({call.tier for call in self._provider_calls}),
        }

    def to_run_evidence(self, manifest: Mapping[str, Any]) -> RunEvidence:
        """Đóng gói toàn bộ bằng chứng thô đã thu thập thành `RunEvidence` bất biến.

        Args:
            manifest: Bản ghi manifest đầy đủ của phiên chạy.

        Returns:
            RunEvidence: Đối tượng bằng chứng sẵn sàng đưa vào bộ đánh giá.
        """
        return RunEvidence(
            manifest=dict(manifest),
            story_plan=self._story_plan,
            transcript=tuple(self._transcript),
            playback_events=tuple(self._playback_events),
            graph_traces=tuple(self._graph_traces),
            provider_calls=tuple(self._provider_calls),
            errors=tuple(self._errors),
            planning_latency_ms=self.planning_latency_ms,
            upfront_script_generation_latency_ms=self.upfront_script_generation_latency_ms,
            total_measured_processing_ms=self.total_measured_processing_ms,
            simulated_elapsed_sec=self.simulated_elapsed_sec,
            target_duration_sec=self._target_duration_sec,
        )
