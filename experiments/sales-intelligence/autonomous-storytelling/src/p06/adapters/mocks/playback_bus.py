"""Bus phát sóng giả lập (`MockPlaybackAckBus`) sinh ACK theo `VirtualClock` cho môi trường PoC.

1. File này giải quyết vấn đề gì?
   Mô phỏng tuyến phát sóng P04 trong môi trường nghiên cứu offline của P06 (khi P04/P02 chưa triển khai),
   hỗ trợ giả lập cả 3 trạng thái kết quả `COMPLETED`, `FAILED`, và `UNKNOWN` một cách tất định.
2. Trách nhiệm chính của module là gì?
   Kiểm tra ứng viên bắt buộc đã đạt `VERIFIED` (`is_ready_for_tts()`), tịnh tiến `VirtualClock`,
   và phát hành `PlaybackAckResult` gắn dấu vết mô phỏng `SIMULATED_HARNESS` (`is_simulated=True`).
3. Module này liên kết với các thành phần nào?
   Triển khai `PlaybackAckBusPort` (`adapters/interfaces.py`), sử dụng `VirtualClock`
   (`simulation/virtual_clock.py`), và cung cấp dữ liệu cho `SimulatedPlaybackHarness`.
4. Input và output chính là gì?
   Input là `SpeechCandidate` (`VERIFIED`), `turn_id`, `plan_revision` và kịch bản kết quả tùy chọn;
   Output là `PlaybackAckResult` (`COMPLETED` kèm `PlaybackCompleted`, hoặc `FAILED`/`UNKNOWN` không kèm event).
5. Có những constraints hoặc invariants quan trọng nào?
   - Tuyệt đối từ chối phát bất kỳ ứng viên `DRAFT` hoặc `REJECTED` nào (`ValueError`).
   - Toàn bộ sự kiện sinh ra bắt buộc mang `event_source=SIMULATED_HARNESS`, `is_simulated=True`,
     `p04_evidence_ref=None` và `simulation_run_id` rõ ràng (không trộn lẫn production P04).
   - `auto_replay_permitted` luôn là `False`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, Optional

from p06.adapters.interfaces import PlaybackAckBusPort, PlaybackAckResult
from p06.schemas.candidate import CoverageMode, SpeechCandidate
from p06.schemas.events import (
    PlaybackCompleted,
    PlaybackEventSource,
    PlaybackOutcomeStatus,
)
from p06.simulation.virtual_clock import VirtualClock

# Độ trễ mặc định khi tuyến phát sóng giả lập gặp sự cố hoặc mất tín hiệu ACK.
DEFAULT_FAILURE_LATENCY_MS: Final[int] = 250


class MockPlaybackAckBus(PlaybackAckBusPort):
    """Bus giả lập P04 dùng cho kiểm thử PoC, tách biệt hoàn toàn khỏi luồng production."""

    def __init__(
        self,
        clock: VirtualClock,
        simulation_run_id: str,
        default_outcome: PlaybackOutcomeStatus = PlaybackOutcomeStatus.COMPLETED,
        scripted_outcomes: Optional[Mapping[str, PlaybackOutcomeStatus]] = None,
        scripted_failure_reasons: Optional[Mapping[str, str]] = None,
        failure_latency_ms: int = DEFAULT_FAILURE_LATENCY_MS,
        event_id_prefix: str = "sim-pb",
        max_speech_duration_ms: Optional[int] = None,
    ) -> None:
        """Khởi tạo bus giả lập phát sóng gắn với `VirtualClock` và mã lần chạy mô phỏng.

        Args:
            clock: Đồng hồ ảo UTC dùng để sinh dấu thời gian `occurred_at`.
            simulation_run_id: Mã định danh lần chạy mô phỏng (bắt buộc không rỗng).
            default_outcome: Trạng thái ACK mặc định nếu `turn_id` không nằm trong kịch bản.
            scripted_outcomes: Ánh xạ `turn_id -> PlaybackOutcomeStatus` để ép ca lỗi/timeout.
            scripted_failure_reasons: Lý do lỗi tùy chỉnh cho từng `turn_id`.
            failure_latency_ms: Thời gian trôi trên đồng hồ ảo khi lượt phát thất bại/mất tín hiệu.
            event_id_prefix: Tiền tố tạo `playback_event_id` tuần tự tất định.
            max_speech_duration_ms: Giới hạn tối đa tùy chọn (ms) để chặn lời thoại quá dài khi phát.

        Raises:
            ValueError: Nếu `simulation_run_id`/`event_id_prefix` rỗng, `failure_latency_ms < 0`,
                hoặc `max_speech_duration_ms` không hợp lệ.
        """
        if not isinstance(simulation_run_id, str) or not simulation_run_id.strip():
            raise ValueError("simulation_run_id không được rỗng.")
        if not isinstance(event_id_prefix, str) or not event_id_prefix.strip():
            raise ValueError("event_id_prefix không được rỗng.")
        if isinstance(failure_latency_ms, bool) or failure_latency_ms < 0:
            raise ValueError("failure_latency_ms phải là số nguyên không âm.")
        if max_speech_duration_ms is not None and (
            isinstance(max_speech_duration_ms, bool)
            or not isinstance(max_speech_duration_ms, int)
            or max_speech_duration_ms <= 0
        ):
            raise ValueError("max_speech_duration_ms phải là số nguyên dương hoặc None.")

        self._clock = clock
        self._simulation_run_id = simulation_run_id.strip()
        self._default_outcome = default_outcome
        self._scripted_outcomes: dict[str, PlaybackOutcomeStatus] = (
            dict(scripted_outcomes) if scripted_outcomes is not None else {}
        )
        self._scripted_failure_reasons: dict[str, str] = (
            dict(scripted_failure_reasons) if scripted_failure_reasons is not None else {}
        )
        self._failure_latency_ms = failure_latency_ms
        self._event_id_prefix = event_id_prefix.strip()
        self._max_speech_duration_ms: Optional[int] = max_speech_duration_ms
        self._event_seq: int = 0
        self._playout_generation: int = 0

    def set_turn_outcome(
        self,
        turn_id: str,
        outcome: PlaybackOutcomeStatus,
        failure_reason: Optional[str] = None,
    ) -> None:
        """Cập nhật kết quả giả lập cho một `turn_id` cụ thể trước khi phát."""
        clean_turn_id = turn_id.strip()
        if not clean_turn_id:
            raise ValueError("turn_id không được rỗng.")
        self._scripted_outcomes[clean_turn_id] = outcome
        if failure_reason is not None and failure_reason.strip():
            self._scripted_failure_reasons[clean_turn_id] = failure_reason.strip()

    def dispatch_turn(
        self,
        candidate: SpeechCandidate,
        turn_id: str,
        plan_revision: int,
        outcome_override: Optional[PlaybackOutcomeStatus] = None,
        failure_reason: Optional[str] = None,
    ) -> PlaybackAckResult:
        """Phát giả lập một `SpeechCandidate` đã `VERIFIED` và trả về `PlaybackAckResult`.

        Args:
            candidate: Ứng viên lời thoại bắt buộc ở trạng thái `VERIFIED`.
            turn_id: Mã lượt phát sóng do bộ điều phối cấp.
            plan_revision: Phiên bản kế hoạch gắn với lượt (bắt buộc `>= 1`).
            outcome_override: Kết quả ghi đè trực tiếp cho lệnh gọi này (nếu có).
            failure_reason: Lý do thất bại tường minh nếu `outcome` là `FAILED` hoặc `UNKNOWN`.

        Returns:
            PlaybackAckResult: Kết quả ACK chuẩn hợp đồng `p06-mock-v0.1`.

        Raises:
            ValueError: Nếu `candidate` chưa `VERIFIED`, `turn_id` rỗng hoặc `plan_revision < 1`.
        """
        if not candidate.is_ready_for_tts():
            raise ValueError(
                f"Từ chối phát candidate '{candidate.candidate_id}': trạng thái hiện tại là "
                f"'{candidate.verification_status.value}', bắt buộc phải là VERIFIED (I-02)."
            )
        if not isinstance(turn_id, str) or not turn_id.strip():
            raise ValueError("turn_id không được rỗng.")
        if isinstance(plan_revision, bool) or plan_revision < 1:
            raise ValueError(f"plan_revision phải >= 1, nhận được {plan_revision}.")

        clean_turn_id = turn_id.strip()
        outcome = (
            outcome_override
            if outcome_override is not None
            else self._scripted_outcomes.get(clean_turn_id, self._default_outcome)
        )

        if outcome == PlaybackOutcomeStatus.COMPLETED:
            duration_ms = self._clock.estimate_raw_speech_duration_ms(candidate.text)
            if self._max_speech_duration_ms is not None and duration_ms > self._max_speech_duration_ms:
                raise ValueError(
                    f"Thời lượng lời thoại ({duration_ms}ms) vượt quá giới hạn tối đa "
                    f"({self._max_speech_duration_ms}ms)."
                )
            occurred_at = self._clock.advance_ms(duration_ms)
            self._event_seq += 1
            self._playout_generation += 1

            # Chỉ quảng bá độ phủ chủ đề/comment khi candidate thực sự mang CoverageMode FULL hoặc PARTIAL.
            should_promote_coverage = candidate.proposed_coverage.coverage_mode in {
                CoverageMode.FULL,
                CoverageMode.PARTIAL,
            }
            confirmed_topics = (
                list(candidate.proposed_coverage.covered_topic_ids)
                if should_promote_coverage
                else []
            )
            confirmed_comments = (
                list(candidate.proposed_coverage.covered_comment_ids)
                if should_promote_coverage
                else []
            )

            event = PlaybackCompleted(
                playback_event_id=f"{self._event_id_prefix}-{self._event_seq:04d}",
                tenant_id=candidate.tenant_id,
                session_id=candidate.session_id,
                session_epoch=candidate.session_epoch,
                turn_id=clean_turn_id,
                candidate_id=candidate.candidate_id,
                chunk_id=candidate.source_chunk_id,
                playout_generation=self._playout_generation,
                sku_refs=list(candidate.sku_refs),
                confirmed_topic_ids=confirmed_topics,
                confirmed_comment_ids=confirmed_comments,
                spoken_text=candidate.text,
                actual_duration_ms=duration_ms,
                occurred_at=occurred_at,
                event_source=PlaybackEventSource.SIMULATED_HARNESS,
                is_simulated=True,
                p04_evidence_ref=None,
                simulation_run_id=self._simulation_run_id,
            )
            return PlaybackAckResult(
                outcome=PlaybackOutcomeStatus.COMPLETED,
                event=event,
                turn_id=clean_turn_id,
                candidate_id=candidate.candidate_id,
                plan_revision=plan_revision,
                auto_replay_permitted=False,
                failure_reason=None,
            )

        # Với FAILED hoặc UNKNOWN: đồng hồ có thể trôi một khoảng latency nhưng TUYỆT ĐỐI không tạo PlaybackCompleted.
        if self._failure_latency_ms > 0:
            self._clock.advance_ms(self._failure_latency_ms)

        resolved_reason = (
            failure_reason
            if failure_reason is not None and failure_reason.strip()
            else self._scripted_failure_reasons.get(
                clean_turn_id,
                f"Trạng thái phát sóng mô phỏng {outcome.value} cho lượt '{clean_turn_id}'.",
            )
        )
        return PlaybackAckResult(
            outcome=outcome,
            event=None,
            turn_id=clean_turn_id,
            candidate_id=candidate.candidate_id,
            plan_revision=plan_revision,
            auto_replay_permitted=False,
            failure_reason=resolved_reason,
        )
