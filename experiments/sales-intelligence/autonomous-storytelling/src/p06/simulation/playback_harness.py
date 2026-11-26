"""Bộ điều phối xác nhận phát sóng mô phỏng (`SimulatedPlaybackHarness`) thực thi bất biến `I-03` & `I-06`.

1. File này giải quyết vấn đề gì?
   Trong kiến trúc event-driven của HOSTRA AI, việc LLM sinh lời thoại hoặc P05 duyệt ứng viên
   KHÔNG đồng nghĩa lời thoại đã được phát tới người xem. Harness này khóa chặt trạng thái
   `StoryCheckpoint`, `played_history` và `completed_topic_ids` để chỉ cập nhật khi nhận được
   `PlaybackCompleted` hợp lệ, đúng thứ tự, đúng ngữ cảnh và chưa từng xử lý.
2. Trách nhiệm chính của module là gì?
   Đăng ký lượt chờ phát (`register_pending_turn`), tiếp nhận `PlaybackAckResult` (`apply_ack`) hoặc
   sự kiện `PlaybackCompleted` (`apply_playback_event`), thực hiện chuỗi kiểm tra 5 lớp (non-completed,
   idempotency chống duplicate, đồng bộ tenant/session/epoch/plan_revision/candidate/chunk/thời gian,
   provenance mô phỏng, và cập nhật nguyên tử).
3. Module này liên kết với các thành phần nào?
   Sử dụng `AckApplyStatus`, `PlaybackAckResult`, `PlaybackApplyResult` (`adapters/interfaces.py`)
   cùng `StoryCheckpoint`, `PlaybackCompleted`, `PlayedTurnSummary` (`p06.schemas`).
4. Input và output chính là gì?
   Input là thông tin đăng ký lượt chờ phát và `PlaybackAckResult` / `PlaybackCompleted`;
   Output là `PlaybackApplyResult` phản ánh rõ lý do chấp nhận hay từ chối cùng snapshot tiến độ.
5. Có những constraints hoặc invariants quan trọng nào?
   - Idempotency: Mỗi `playback_event_id` và mỗi `turn_id` chỉ được kết thúc đúng 1 lần.
   - Không tự phát lặp (`auto_replay_permitted=False`) khi `FAILED` hay `UNKNOWN`.
   - Chống stale/cross-context: Mọi lệch `tenant_id`, `session_id`, `session_epoch`, `plan_revision`,
     `candidate_id`, `chunk_id` hoặc `occurred_at` lùi thời gian đều bị từ chối nguyên trạng.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Final, Optional

from pydantic import BaseModel, ConfigDict

from p06.adapters.interfaces import (
    AckApplyStatus,
    PlaybackAckResult,
    PlaybackApplyResult,
)
from p06.schemas.candidate import SpeechCandidate
from p06.schemas.events import (
    PlaybackCompleted,
    PlaybackEventSource,
    PlaybackOutcomeStatus,
    ResumeMode,
    StoryCheckpoint,
)
from p06.schemas.state import (
    DEFAULT_PLAYED_HISTORY_WINDOW,
    MAX_PLAYED_HISTORY_WINDOW,
    PlayedTurnSummary,
)
from p06.schemas.story import (
    NonBlankStr,
    OptionalNonBlankStr,
    StrictBool,
    StrictPositiveInt,
)


class _UnsetType:
    """Sentinel nội bộ phân biệt tham số không truyền với giá trị tường minh `None`."""


_UNSET: Final[_UnsetType] = _UnsetType()


class PendingTurnRecord(BaseModel):
    """Bản ghi bất biến mô tả một lượt đã được gửi đi phát và đang chờ ACK từ P04."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    turn_id: NonBlankStr
    tenant_id: NonBlankStr
    session_id: NonBlankStr
    session_epoch: StrictPositiveInt
    plan_revision: StrictPositiveInt
    candidate_id: NonBlankStr
    chunk_id: OptionalNonBlankStr = None
    intent: NonBlankStr
    has_next_topic_override: StrictBool = False
    next_topic_id_after_turn: OptionalNonBlankStr = None
    next_arc_id_after_turn: OptionalNonBlankStr = None
    next_resume_mode: Optional[ResumeMode] = None


class SimulatedPlaybackHarness:
    """Harness mô phỏng quản lý checkpoint, lịch sử đã phát và độ phủ dựa trên ACK nghiêm ngặt."""

    def __init__(
        self,
        initial_checkpoint: StoryCheckpoint,
        expected_simulation_run_id: str,
        played_history_window_size: int = DEFAULT_PLAYED_HISTORY_WINDOW,
        initial_completed_topic_ids: Iterable[str] = (),
    ) -> None:
        """Khởi tạo harness với `StoryCheckpoint` ban đầu và mã lần chạy mô phỏng kỳ vọng.

        Args:
            initial_checkpoint: Điểm dừng kịch bản ban đầu của phiên.
            expected_simulation_run_id: Mã `simulation_run_id` bắt buộc trên mọi event hợp lệ.
            played_history_window_size: Kích thước cửa sổ `W` cho `recent_played_history()`.
            initial_completed_topic_ids: Tập `topic_id` đã hoàn tất trước đó (nếu khôi phục phiên).

        Raises:
            ValueError: Nếu `expected_simulation_run_id` rỗng hoặc `played_history_window_size` ngoài biên.
        """
        if not isinstance(expected_simulation_run_id, str) or not expected_simulation_run_id.strip():
            raise ValueError("expected_simulation_run_id không được rỗng.")
        if (
            isinstance(played_history_window_size, bool)
            or not (1 <= played_history_window_size <= MAX_PLAYED_HISTORY_WINDOW)
        ):
            raise ValueError(
                f"played_history_window_size phải trong [1, {MAX_PLAYED_HISTORY_WINDOW}], "
                f"nhận được {played_history_window_size}."
            )

        self._checkpoint: StoryCheckpoint = initial_checkpoint
        self._expected_sim_run_id: str = expected_simulation_run_id.strip()
        self._window_size: int = played_history_window_size
        self._played_history: list[PlayedTurnSummary] = []
        self._completed_topic_ids: set[str] = set(initial_completed_topic_ids)
        self._pending_turns: dict[str, PendingTurnRecord] = {}
        self._seen_event_ids: set[str] = set()
        self._finalized_turns: set[str] = set()
        self._last_ack_occurred_at: Optional[datetime] = None

    @property
    def checkpoint(self) -> StoryCheckpoint:
        """`StoryCheckpoint` hiện hành (chỉ tiến khi có `PlaybackCompleted` hợp lệ)."""
        return self._checkpoint

    @property
    def completed_topic_ids(self) -> frozenset[str]:
        """Tập `topic_id` đã được xác nhận hoàn tất phát sóng."""
        return frozenset(self._completed_topic_ids)

    @property
    def played_history(self) -> tuple[PlayedTurnSummary, ...]:
        """Toàn bộ danh sách các lượt phát thành công đã ghi nhận theo thứ tự thời gian."""
        return tuple(self._played_history)

    @property
    def recent_played_history(self) -> tuple[PlayedTurnSummary, ...]:
        """Cửa sổ `W` lượt phát gần nhất phục vụ nạp vào `AgentState.played_history`."""
        return tuple(self._played_history[-self._window_size :])

    @property
    def pending_turn_ids(self) -> frozenset[str]:
        """Tập các `turn_id` đang ở trạng thái chờ xác nhận ACK."""
        return frozenset(self._pending_turns.keys())

    @property
    def finalized_turn_ids(self) -> frozenset[str]:
        """Tập các `turn_id` đã kết thúc vòng đời (thành công hoặc lỗi/không rõ)."""
        return frozenset(self._finalized_turns)

    def register_pending_turn(
        self,
        turn_id: str,
        candidate: SpeechCandidate,
        plan_revision: int,
        chunk_id: Optional[str] = None,
        next_topic_id: Optional[str] | _UnsetType = _UNSET,
        current_arc_id: Optional[str] = None,
        resume_mode: Optional[ResumeMode] = None,
    ) -> PendingTurnRecord:
        """Đăng ký một lượt đã được chọn để gửi phát sóng (chưa được tính là đã phát).

        Lý do thiết kế: Tách rạch ròi bước gửi lệnh phát (`register_pending_turn`) khỏi bước
        xác nhận đã phát (`apply_ack`). Nếu không có bước ACK sau đó, tiến độ tuyệt đối không đổi.

        Args:
            turn_id: Mã lượt phát sóng duy nhất.
            candidate: Ứng viên `SpeechCandidate` bắt buộc đã đạt `VERIFIED`.
            plan_revision: Phiên bản `StoryPlan` hiện hành khớp với checkpoint.
            chunk_id: Mã `StoryChunk` (mặc định lấy `candidate.source_chunk_id`).
            next_topic_id: Chủ đề kế tiếp dự kiến sau khi lượt này phát xong (có thể truyền `None`).
            current_arc_id: Mã arc dự kiến sau khi lượt này phát xong.
            resume_mode: Chế độ nối mạch cho lượt sau.

        Returns:
            PendingTurnRecord: Bản ghi lượt chờ phát đã được lưu.

        Raises:
            ValueError: Nếu `candidate` chưa `VERIFIED`, `turn_id` trùng, hoặc lệch ngữ cảnh phiên.
        """
        if not candidate.is_ready_for_tts():
            raise ValueError(
                f"Chỉ được đăng ký chờ phát cho candidate đã VERIFIED, nhận được "
                f"'{candidate.verification_status.value}'."
            )
        clean_turn_id = turn_id.strip() if isinstance(turn_id, str) else ""
        if not clean_turn_id:
            raise ValueError("turn_id không được rỗng.")
        if clean_turn_id in self._pending_turns or clean_turn_id in self._finalized_turns:
            raise ValueError(f"turn_id '{clean_turn_id}' đã được đăng ký hoặc đã kết thúc trước đó.")

        if (
            candidate.tenant_id != self._checkpoint.tenant_id
            or candidate.session_id != self._checkpoint.session_id
            or candidate.session_epoch != self._checkpoint.session_epoch
        ):
            raise ValueError(
                "Candidate không khớp (tenant_id, session_id, session_epoch) với StoryCheckpoint."
            )
        if plan_revision != self._checkpoint.plan_revision:
            raise ValueError(
                f"plan_revision={plan_revision} không khớp checkpoint.plan_revision={self._checkpoint.plan_revision}."
            )

        effective_chunk_id = chunk_id if chunk_id is not None else candidate.source_chunk_id
        has_override = next_topic_id is not _UNSET
        resolved_next_topic = None if next_topic_id is _UNSET else next_topic_id

        record = PendingTurnRecord(
            turn_id=clean_turn_id,
            tenant_id=candidate.tenant_id,
            session_id=candidate.session_id,
            session_epoch=candidate.session_epoch,
            plan_revision=plan_revision,
            candidate_id=candidate.candidate_id,
            chunk_id=effective_chunk_id,
            intent=candidate.intent,
            has_next_topic_override=has_override,
            next_topic_id_after_turn=resolved_next_topic,
            next_arc_id_after_turn=current_arc_id,
            next_resume_mode=resume_mode,
        )
        self._pending_turns[clean_turn_id] = record
        return record

    def apply_ack(
        self,
        ack_result: PlaybackAckResult,
        next_topic_id: Optional[str] | _UnsetType = _UNSET,
        current_arc_id: Optional[str] = None,
        resume_mode: Optional[ResumeMode] = None,
    ) -> PlaybackApplyResult:
        """Xử lý kết quả `PlaybackAckResult` trả về từ bus phát sóng theo 5 tầng kiểm tra.

        Args:
            ack_result: Kết quả ACK (`COMPLETED`, `FAILED`, hoặc `UNKNOWN`).
            next_topic_id: Chủ đề kế tiếp (ghi đè giá trị đã đăng ký nếu được truyền).
            current_arc_id: Arc kế tiếp (nếu chuyển arc).
            resume_mode: Chế độ nối mạch tiếp theo.

        Returns:
            PlaybackApplyResult: Kết quả áp dụng kèm trạng thái tiến độ hiện hành.
        """
        if ack_result.outcome != PlaybackOutcomeStatus.COMPLETED:
            # Đánh dấu turn đã kết thúc để ngăn ACK đến trễ hoặc tự phát lại mù (auto_replay_permitted=False).
            self._finalized_turns.add(ack_result.turn_id)
            self._pending_turns.pop(ack_result.turn_id, None)
            return self._build_apply_result(
                status=AckApplyStatus.IGNORED_NON_COMPLETED,
                applied=False,
                reason=(
                    f"Giữ nguyên checkpoint vì ACK mang trạng thái {ack_result.outcome.value}: "
                    f"{ack_result.failure_reason}"
                ),
            )

        assert ack_result.event is not None  # Được bảo đảm bởi validator của PlaybackAckResult.
        expected_plan_revision = (
            ack_result.plan_revision
            if ack_result.plan_revision is not None
            else self._checkpoint.plan_revision
        )
        return self._apply_completed_event(
            event=ack_result.event,
            expected_plan_revision=expected_plan_revision,
            expected_intent=None,
            next_topic_id=next_topic_id,
            current_arc_id=current_arc_id,
            resume_mode=resume_mode,
        )

    def apply_playback_event(
        self,
        event: PlaybackCompleted,
        intent: str,
        plan_revision: int,
        next_topic_id: Optional[str] | _UnsetType = _UNSET,
        current_arc_id: Optional[str] = None,
        resume_mode: Optional[ResumeMode] = None,
    ) -> PlaybackApplyResult:
        """Áp dụng trực tiếp một sự kiện `PlaybackCompleted` thô vào harness kèm đối chiếu hợp đồng.

        Args:
            event: Sự kiện `PlaybackCompleted` nhận được.
            intent: Ý định giao tiếp tương ứng với lượt phát.
            plan_revision: Phiên bản `StoryPlan` gắn với sự kiện đến.
            next_topic_id: Chủ đề kế tiếp (tùy chọn).
            current_arc_id: Arc kế tiếp (tùy chọn).
            resume_mode: Chế độ nối mạch (tùy chọn).

        Returns:
            PlaybackApplyResult: Trạng thái áp dụng (`APPLIED` hoặc mã từ chối cụ thể).
        """
        return self._apply_completed_event(
            event=event,
            expected_plan_revision=plan_revision,
            expected_intent=intent,
            next_topic_id=next_topic_id,
            current_arc_id=current_arc_id,
            resume_mode=resume_mode,
        )

    def _apply_completed_event(
        self,
        event: PlaybackCompleted,
        expected_plan_revision: int,
        expected_intent: Optional[str],
        next_topic_id: Optional[str] | _UnsetType,
        current_arc_id: Optional[str],
        resume_mode: Optional[ResumeMode],
    ) -> PlaybackApplyResult:
        """Logic dùng chung kiểm định 4 lớp còn lại cho sự kiện `PlaybackCompleted` và commit nguyên tử."""
        # Lớp 2: Kiểm tra idempotency — chặn trùng playback_event_id hoặc turn_id đã xử lý.
        if event.playback_event_id in self._seen_event_ids:
            return self._build_apply_result(
                status=AckApplyStatus.REJECTED_DUPLICATE,
                applied=False,
                reason=f"Sự kiện '{event.playback_event_id}' đã được áp dụng trước đó (idempotent).",
            )
        if event.turn_id in self._finalized_turns:
            return self._build_apply_result(
                status=AckApplyStatus.REJECTED_DUPLICATE,
                applied=False,
                reason=f"Lượt '{event.turn_id}' đã được kết thúc trước đó.",
            )

        # Lớp 3: Kiểm tra đăng ký lượt chờ và toàn vẹn ngữ cảnh phiên / kế hoạch / thứ tự thời gian.
        pending = self._pending_turns.get(event.turn_id)
        if pending is None:
            return self._build_apply_result(
                status=AckApplyStatus.REJECTED_STALE_OR_MISMATCH,
                applied=False,
                reason=f"turn_id '{event.turn_id}' chưa được đăng ký trong danh sách chờ phát.",
            )

        mismatch_reason = self._find_context_mismatch_reason(
            event=event,
            pending=pending,
            incoming_plan_revision=expected_plan_revision,
            incoming_intent=expected_intent,
        )
        if mismatch_reason is not None:
            return self._build_apply_result(
                status=AckApplyStatus.REJECTED_STALE_OR_MISMATCH,
                applied=False,
                reason=mismatch_reason,
            )

        # Lớp 4: Kiểm tra nguồn gốc sự kiện mô phỏng (cấm sự kiện giả mạo hoặc trộn từ run khác).
        if (
            event.event_source != PlaybackEventSource.SIMULATED_HARNESS
            or event.is_simulated is not True
            or event.simulation_run_id != self._expected_sim_run_id
        ):
            return self._build_apply_result(
                status=AckApplyStatus.REJECTED_INVALID_PROVENANCE,
                applied=False,
                reason=(
                    f"Nguồn gốc sự kiện không hợp lệ: event_source={event.event_source.value}, "
                    f"is_simulated={event.is_simulated}, simulation_run_id='{event.simulation_run_id}' "
                    f"(kỳ vọng '{self._expected_sim_run_id}')."
                ),
            )

        # Lớp 5: Xây dựng bản ghi và tịnh tiến checkpoint trước khi commit để bảo đảm tính nguyên tử.
        if next_topic_id is not _UNSET:
            resolved_next_topic = next_topic_id
        elif pending.has_next_topic_override:
            resolved_next_topic = pending.next_topic_id_after_turn
        else:
            resolved_next_topic = self._checkpoint.next_topic_id

        resolved_arc_id = (
            current_arc_id if current_arc_id is not None else pending.next_arc_id_after_turn
        )
        resolved_resume_mode = (
            resume_mode if resume_mode is not None else pending.next_resume_mode
        )

        summary = PlayedTurnSummary.from_playback_completed(event, intent=pending.intent)
        new_checkpoint = self._checkpoint.advance_on_playback(
            event=event,
            next_topic_id=resolved_next_topic,
            current_arc_id=resolved_arc_id,
            resume_mode=resolved_resume_mode,
        )

        self._seen_event_ids.add(event.playback_event_id)
        self._finalized_turns.add(event.turn_id)
        self._pending_turns.pop(event.turn_id, None)
        self._last_ack_occurred_at = event.occurred_at
        self._played_history.append(summary)
        self._completed_topic_ids.update(event.confirmed_topic_ids)
        self._checkpoint = new_checkpoint

        return self._build_apply_result(
            status=AckApplyStatus.APPLIED,
            applied=True,
            reason=None,
        )

    def _find_context_mismatch_reason(
        self,
        event: PlaybackCompleted,
        pending: PendingTurnRecord,
        incoming_plan_revision: int,
        incoming_intent: Optional[str],
    ) -> Optional[str]:
        """Kiểm tra toàn bộ trường ngữ cảnh và tính đơn điệu thời gian của sự kiện đến."""
        if event.tenant_id != self._checkpoint.tenant_id or event.tenant_id != pending.tenant_id:
            return (
                f"Lệch tenant_id: event='{event.tenant_id}', "
                f"checkpoint='{self._checkpoint.tenant_id}'."
            )
        if event.session_id != self._checkpoint.session_id or event.session_id != pending.session_id:
            return (
                f"Lệch session_id: event='{event.session_id}', "
                f"checkpoint='{self._checkpoint.session_id}'."
            )
        if (
            event.session_epoch != self._checkpoint.session_epoch
            or event.session_epoch != pending.session_epoch
        ):
            return (
                f"Lệch session_epoch (stale ACK): event={event.session_epoch}, "
                f"checkpoint={self._checkpoint.session_epoch}."
            )
        if (
            incoming_plan_revision != self._checkpoint.plan_revision
            or pending.plan_revision != self._checkpoint.plan_revision
        ):
            return (
                f"Lệch plan_revision: event={incoming_plan_revision}, "
                f"checkpoint={self._checkpoint.plan_revision}."
            )
        if event.candidate_id != pending.candidate_id:
            return (
                f"Lệch candidate_id: event='{event.candidate_id}', "
                f"pending='{pending.candidate_id}'."
            )
        if event.chunk_id != pending.chunk_id:
            return (
                f"Lệch chunk_id: event='{event.chunk_id}', "
                f"pending='{pending.chunk_id}'."
            )
        if incoming_intent is not None and incoming_intent != pending.intent:
            return (
                f"Lệch intent: event='{incoming_intent}', pending='{pending.intent}'."
            )
        if self._last_ack_occurred_at is not None and event.occurred_at < self._last_ack_occurred_at:
            return (
                f"ACK đến sai thứ tự thời gian (stale): event.occurred_at={event.occurred_at.isoformat()} "
                f"< last_ack={self._last_ack_occurred_at.isoformat()}."
            )
        return None

    def _build_apply_result(
        self,
        status: AckApplyStatus,
        applied: bool,
        reason: Optional[str],
    ) -> PlaybackApplyResult:
        """Tạo `PlaybackApplyResult` phản ánh đúng trạng thái hiện hành của harness."""
        return PlaybackApplyResult(
            status=status,
            applied=applied,
            checkpoint=self._checkpoint,
            completed_topic_ids=frozenset(self._completed_topic_ids),
            played_history_count=len(self._played_history),
            auto_replay_permitted=False,
            reason=reason,
        )
