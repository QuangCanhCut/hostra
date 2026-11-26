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

from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Final, Optional

from pydantic import BaseModel, ConfigDict

from p06.adapters.interfaces import (
    AckApplyStatus,
    PlaybackAckResult,
    PlaybackApplyResult,
)
from p06.memory.played_history import ShortTermPlayedHistory
from p06.memory.semantic_memory import NoOpSemanticMemory, OptionalSemanticMemory
from p06.memory.topic_coverage import GlobalTopicCoverage
from p06.memory.viewer_context import SessionViewerContext
from p06.schemas.candidate import SpeechCandidate
from p06.schemas.events import (
    PlaybackCompleted,
    PlaybackEventSource,
    PlaybackOutcomeStatus,
    ResumeMode,
    StoryCheckpoint,
)
from p06.schemas.state import (
    AgentState,
    DEFAULT_MAX_REWRITE_RETRIES,
    DEFAULT_PLAYED_HISTORY_WINDOW,
    MAX_PLAYED_HISTORY_WINDOW,
    PlayedTurnSummary,
    RewriteBudgetState,
)
from p06.schemas.story import (
    NonBlankStr,
    OptionalNonBlankStr,
    StoryPlan,
    StrictBool,
    StrictPositiveInt,
)


class _UnsetType:
    """Sentinel nội bộ phân biệt tham số không truyền với giá trị tường minh `None`."""


_UNSET: Final[_UnsetType] = _UnsetType()


class PendingTurnRecord(BaseModel):
    """Bản ghi bất biến mô tả một lượt đã được gửi đi phát và đang chờ ACK từ P04."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    turn_id: NonBlankStr
    tenant_id: NonBlankStr
    session_id: NonBlankStr
    session_epoch: StrictPositiveInt
    plan_revision: StrictPositiveInt
    candidate_id: NonBlankStr
    chunk_id: OptionalNonBlankStr = None
    intent: NonBlankStr
    sku_refs: tuple[NonBlankStr, ...] = ()
    proposed_topic_ids: tuple[NonBlankStr, ...] = ()
    covered_claim_ids: tuple[NonBlankStr, ...] = ()
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
        story_plan: Optional[StoryPlan] = None,
        initial_played_history: Iterable[PlayedTurnSummary] = (),
        played_history: Optional[ShortTermPlayedHistory] = None,
        topic_coverage: Optional[GlobalTopicCoverage] = None,
        viewer_context: Optional[SessionViewerContext] = None,
        semantic_memory: Optional[OptionalSemanticMemory] = None,
        min_chunks_per_topic: int = 1,
    ) -> None:
        """Khởi tạo harness với `StoryCheckpoint`, mã lần chạy mô phỏng và hệ thống bộ nhớ 4 phần.

        Args:
            initial_checkpoint: Điểm dừng kịch bản ban đầu của phiên.
            expected_simulation_run_id: Mã `simulation_run_id` bắt buộc trên mọi event hợp lệ.
            played_history_window_size: Kích thước cửa sổ `W` cho `recent_played_history()`.
            initial_completed_topic_ids: Tập `topic_id` đã hoàn tất trước đó (nếu khôi phục phiên).
            story_plan: Kế hoạch kể chuyện tùy chọn để kiểm định `confirmed_topic_ids` thuộc kế hoạch.
            initial_played_history: Lịch sử các lượt đã phát trước đó (nếu khôi phục phiên).
            played_history: Thể hiện `ShortTermPlayedHistory` tiêm từ ngoài (tùy chọn).
            topic_coverage: Thể hiện `GlobalTopicCoverage` tiêm từ ngoài (tùy chọn).
            viewer_context: Thể hiện `SessionViewerContext` tiêm từ ngoài (tùy chọn).
            semantic_memory: Thể hiện `OptionalSemanticMemory` tiêm từ ngoài (mặc định `NoOpSemanticMemory`).

        Raises:
            TypeError: Nếu đối tượng bộ nhớ truyền vào không đúng kiểu hợp đồng.
            ValueError: Nếu `expected_simulation_run_id` rỗng, `played_history_window_size` ngoài biên,
                hoặc ngữ cảnh của `played_history` / `topic_coverage` / `viewer_context` / `story_plan`
                không khớp với `initial_checkpoint`.
        """
        if not isinstance(expected_simulation_run_id, str) or not expected_simulation_run_id.strip():
            raise ValueError("expected_simulation_run_id không được rỗng.")
        if (
            isinstance(played_history_window_size, bool)
            or not isinstance(played_history_window_size, int)
            or not (1 <= played_history_window_size <= MAX_PLAYED_HISTORY_WINDOW)
        ):
            raise ValueError(
                f"played_history_window_size phải trong [1, {MAX_PLAYED_HISTORY_WINDOW}], "
                f"nhận được {played_history_window_size}."
            )

        if story_plan is not None:
            if not isinstance(story_plan, StoryPlan):
                raise TypeError(
                    f"story_plan phải là StoryPlan hoặc None, nhận được {type(story_plan).__name__}."
                )
            if (
                story_plan.tenant_id != initial_checkpoint.tenant_id
                or story_plan.session_id != initial_checkpoint.session_id
                or story_plan.plan_id != initial_checkpoint.plan_id
                or story_plan.plan_revision != initial_checkpoint.plan_revision
            ):
                raise ValueError(
                    "story_plan không khớp (tenant_id, session_id, plan_id, plan_revision) với initial_checkpoint."
                )

        if played_history is None:
            self._played_history_store: ShortTermPlayedHistory = ShortTermPlayedHistory(
                window_size=played_history_window_size,
                tenant_id=initial_checkpoint.tenant_id,
                session_id=initial_checkpoint.session_id,
                session_epoch=initial_checkpoint.session_epoch,
                initial_turns=initial_played_history,
            )
        else:
            if not isinstance(played_history, ShortTermPlayedHistory):
                raise TypeError(
                    f"played_history phải là ShortTermPlayedHistory, nhận được {type(played_history).__name__}."
                )
            if (
                isinstance(played_history.window_size, bool)
                or not isinstance(played_history.window_size, int)
                or not (1 <= played_history.window_size <= MAX_PLAYED_HISTORY_WINDOW)
            ):
                raise ValueError(
                    f"played_history.window_size phải trong [1, {MAX_PLAYED_HISTORY_WINDOW}], "
                    f"nhận được {played_history.window_size!r}."
                )
            if (
                played_history.tenant_id is not None
                and played_history.tenant_id != initial_checkpoint.tenant_id
            ):
                raise ValueError(
                    f"Lệch tenant_id trên played_history: '{played_history.tenant_id}' != "
                    f"'{initial_checkpoint.tenant_id}'."
                )
            if (
                played_history.session_id is not None
                and played_history.session_id != initial_checkpoint.session_id
            ):
                raise ValueError(
                    f"Lệch session_id trên played_history: '{played_history.session_id}' != "
                    f"'{initial_checkpoint.session_id}'."
                )
            if (
                played_history.session_epoch is not None
                and played_history.session_epoch != initial_checkpoint.session_epoch
            ):
                raise ValueError(
                    f"Lệch session_epoch trên played_history: {played_history.session_epoch} != "
                    f"{initial_checkpoint.session_epoch}."
                )
            for turn in initial_played_history:
                if not played_history.has_event(turn.playback_event_id) and not played_history.has_turn(turn.turn_id):
                    played_history.append_confirmed_turn(
                        turn,
                        tenant_id=initial_checkpoint.tenant_id,
                        session_id=initial_checkpoint.session_id,
                        session_epoch=initial_checkpoint.session_epoch,
                    )
            self._played_history_store = played_history

        initial_topics_list = list(initial_completed_topic_ids)
        self._initial_extra_completed_topic_ids: set[str] = set()

        if (
            isinstance(min_chunks_per_topic, bool)
            or not isinstance(min_chunks_per_topic, int)
            or min_chunks_per_topic < 1
        ):
            raise ValueError(
                f"min_chunks_per_topic phải là số nguyên >= 1, nhận được {min_chunks_per_topic!r}."
            )
        if topic_coverage is None:
            if story_plan is not None:
                self._topic_coverage: Optional[GlobalTopicCoverage] = GlobalTopicCoverage(
                    story_plan=story_plan,
                    initial_completed_topic_ids=initial_topics_list,
                    min_chunks_per_topic=min_chunks_per_topic,
                )
                self._completed_topic_ids: set[str] = set(self._topic_coverage.completed_topic_ids)
            else:
                self._topic_coverage = None
                self._completed_topic_ids = set(initial_topics_list)
        else:
            if not isinstance(topic_coverage, GlobalTopicCoverage):
                raise TypeError(
                    f"topic_coverage phải là GlobalTopicCoverage, nhận được {type(topic_coverage).__name__}."
                )
            if (
                topic_coverage.tenant_id != initial_checkpoint.tenant_id
                or topic_coverage.session_id != initial_checkpoint.session_id
                or topic_coverage.plan_id != initial_checkpoint.plan_id
                or topic_coverage.plan_revision != initial_checkpoint.plan_revision
            ):
                raise ValueError(
                    "topic_coverage không khớp (tenant_id, session_id, plan_id, plan_revision) "
                    "với initial_checkpoint."
                )
            if story_plan is not None and topic_coverage.planned_topic_ids != frozenset(story_plan.all_topic_ids()):
                raise ValueError(
                    "topic_coverage.planned_topic_ids không đồng bộ với story_plan."
                )
            unknown_initial = set(initial_topics_list) - topic_coverage.planned_topic_ids
            if unknown_initial:
                raise ValueError(
                    f"initial_completed_topic_ids chứa topic không thuộc topic_coverage: {sorted(unknown_initial)}."
                )
            self._topic_coverage = topic_coverage
            self._initial_extra_completed_topic_ids = set(initial_topics_list) - set(
                topic_coverage.completed_topic_ids
            )
            self._completed_topic_ids = (
                set(topic_coverage.completed_topic_ids) | self._initial_extra_completed_topic_ids
            )

        if viewer_context is None:
            self._viewer_context: SessionViewerContext = SessionViewerContext(
                tenant_id=initial_checkpoint.tenant_id,
                session_id=initial_checkpoint.session_id,
                session_epoch=initial_checkpoint.session_epoch,
            )
        else:
            if not isinstance(viewer_context, SessionViewerContext):
                raise TypeError(
                    f"viewer_context phải là SessionViewerContext, nhận được {type(viewer_context).__name__}."
                )
            if (
                viewer_context.tenant_id != initial_checkpoint.tenant_id
                or viewer_context.session_id != initial_checkpoint.session_id
                or viewer_context.session_epoch != initial_checkpoint.session_epoch
            ):
                raise ValueError(
                    "viewer_context không khớp (tenant_id, session_id, session_epoch) với initial_checkpoint."
                )
            self._viewer_context = viewer_context

        if semantic_memory is None:
            self._semantic_memory: OptionalSemanticMemory = NoOpSemanticMemory()
        else:
            if not isinstance(semantic_memory, OptionalSemanticMemory):
                raise TypeError(
                    f"semantic_memory phải là OptionalSemanticMemory, nhận được {type(semantic_memory).__name__}."
                )
            self._semantic_memory = semantic_memory

        self._checkpoint: StoryCheckpoint = initial_checkpoint
        self._expected_sim_run_id: str = expected_simulation_run_id.strip()
        self._window_size: int = self._played_history_store.window_size
        self._story_plan: Optional[StoryPlan] = story_plan
        self._pending_turns: dict[str, PendingTurnRecord] = {}
        self._seen_event_ids: set[str] = set(self._played_history_store.seen_event_ids)
        self._finalized_turns: set[str] = set(self._played_history_store.seen_turn_ids)
        self._last_ack_occurred_at: Optional[datetime] = initial_checkpoint.updated_at
        for item in self._played_history_store.all_turns():
            if (
                self._last_ack_occurred_at is not None
                and (item.occurred_at.tzinfo is None) == (self._last_ack_occurred_at.tzinfo is None)
                and item.occurred_at > self._last_ack_occurred_at
            ):
                self._last_ack_occurred_at = item.occurred_at
        self._last_playout_generation: Optional[int] = None
        self._semantic_index_errors: list[str] = []

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
        return self._played_history_store.all_turns()

    @property
    def recent_played_history(self) -> tuple[PlayedTurnSummary, ...]:
        """Cửa sổ `W` lượt phát gần nhất phục vụ nạp vào `AgentState.played_history`."""
        return self._played_history_store.recent_turns()

    @property
    def played_history_window_size(self) -> int:
        """Kích thước cửa sổ `W` hiện tại của `ShortTermPlayedHistory`."""
        return self._window_size

    @property
    def played_history_memory(self) -> ShortTermPlayedHistory:
        """Thể hiện `ShortTermPlayedHistory` nội bộ phục vụ kiểm tra chống lặp toàn phiên."""
        return self._played_history_store

    @property
    def topic_coverage(self) -> Optional[GlobalTopicCoverage]:
        """Thể hiện `GlobalTopicCoverage` gắn với kế hoạch (hoặc `None` nếu không truyền plan)."""
        return self._topic_coverage

    @property
    def viewer_context(self) -> SessionViewerContext:
        """Thể hiện `SessionViewerContext` phạm vi phiên hiện hành."""
        return self._viewer_context

    @property
    def semantic_memory(self) -> OptionalSemanticMemory:
        """Thể hiện `OptionalSemanticMemory` đang gắn với harness (mặc định `NoOpSemanticMemory`)."""
        return self._semantic_memory

    @property
    def pending_turn_ids(self) -> frozenset[str]:
        """Tập các `turn_id` đang ở trạng thái chờ xác nhận ACK."""
        return frozenset(self._pending_turns.keys())

    @property
    def finalized_turn_ids(self) -> frozenset[str]:
        """Tập các `turn_id` đã kết thúc vòng đời (thành công hoặc lỗi/không rõ)."""
        return frozenset(self._finalized_turns)

    @property
    def semantic_index_errors(self) -> tuple[str, ...]:
        """Danh sách lỗi không nghiêm trọng phát sinh từ `OptionalSemanticMemory.index_played_turn()`."""
        return tuple(self._semantic_index_errors)

    def switch_active_sku(
        self,
        new_active_sku_id: str,
        *,
        story_plan: StoryPlan,
        current_arc_id: Optional[str] = None,
        next_topic_id: Optional[str] = None,
        updated_at: Optional[datetime] = None,
    ) -> StoryCheckpoint:
        """Chuyển `active_sku_id` tại ranh giới điều phối mô phỏng (P08 boundary) theo bất biến I-04.

        Lý do thiết kế: Khi phiên chạy qua 3 SKU tuần tự trong `P06-E01`, bộ điều phối phiên bên ngoài
        P06 cần chuyển `active_sku_id` mà KHÔNG làm mất lịch sử đã phát (`_played_history_store`),
        tập chống lặp (`_seen_event_ids`, `_finalized_turns`), hay tiến độ phủ toàn cục (`_topic_coverage`).

        Args:
            new_active_sku_id: Mã SKU mục tiêu mới thuộc `story_plan.pinned_sku_ids`.
            story_plan: Kế hoạch kể chuyện hiện hành khớp với checkpoint.
            current_arc_id: Mã arc mục tiêu (nếu `None` sẽ tự tìm arc đầu tiên phù hợp với SKU mới).
            next_topic_id: Mã topic mở đầu cho SKU mới (nếu `None` sẽ chọn topic chưa hoàn tất đầu tiên).
            updated_at: Mốc thời gian chuyển SKU trên đồng hồ ảo.

        Returns:
            StoryCheckpoint: Điểm dừng mới mang `active_sku_id` mới.

        Raises:
            TypeError: Nếu `story_plan` không phải `StoryPlan`.
            ValueError: Nếu còn lượt đang chờ ACK (`_pending_turns`), `story_plan` không khớp checkpoint,
                `new_active_sku_id` không nằm trong `pinned_sku_ids`, hoặc `updated_at` lùi thời gian.
        """
        if not isinstance(story_plan, StoryPlan):
            raise TypeError(
                f"story_plan phải là StoryPlan, nhận được {type(story_plan).__name__}."
            )
        if self._pending_turns:
            raise ValueError(
                f"Không thể chuyển active_sku_id khi còn lượt đang chờ ACK: {sorted(self._pending_turns)}."
            )
        if (
            story_plan.tenant_id != self._checkpoint.tenant_id
            or story_plan.session_id != self._checkpoint.session_id
            or story_plan.plan_id != self._checkpoint.plan_id
            or story_plan.plan_revision != self._checkpoint.plan_revision
        ):
            raise ValueError(
                "story_plan không khớp (tenant_id, session_id, plan_id, plan_revision) với checkpoint."
            )
        if not isinstance(new_active_sku_id, str) or not new_active_sku_id.strip():
            raise ValueError("new_active_sku_id không được rỗng.")
        clean_sku = new_active_sku_id.strip()
        if clean_sku not in story_plan.pinned_sku_ids:
            raise ValueError(
                f"new_active_sku_id='{clean_sku}' không nằm trong story_plan.pinned_sku_ids "
                f"{story_plan.pinned_sku_ids}."
            )

        if updated_at is not None and self._last_ack_occurred_at is not None:
            if (updated_at.tzinfo is None) != (self._last_ack_occurred_at.tzinfo is None):
                raise ValueError("Múi giờ của updated_at không đồng bộ với StoryCheckpoint.updated_at.")
            if updated_at < self._last_ack_occurred_at:
                raise ValueError(
                    f"updated_at ({updated_at.isoformat()}) không được lùi trước mốc ACK cuối "
                    f"({self._last_ack_occurred_at.isoformat()})."
                )

        sorted_arcs = sorted(story_plan.arcs, key=lambda item: item.position)
        resolved_arc_id = current_arc_id
        if resolved_arc_id is None:
            for arc in sorted_arcs:
                if arc.sku_id == clean_sku or any(
                    topic.sku_id == clean_sku for topic in arc.topics
                ):
                    resolved_arc_id = arc.arc_id
                    break
            if resolved_arc_id is None:
                for arc in sorted_arcs:
                    if arc.sku_id is None:
                        resolved_arc_id = arc.arc_id
                        break
            if resolved_arc_id is None:
                resolved_arc_id = sorted_arcs[0].arc_id

        resolved_next_topic_id = next_topic_id
        if resolved_next_topic_id is None:
            for arc in sorted_arcs:
                for topic in arc.topics:
                    is_eligible = topic.sku_id == clean_sku or (
                        topic.sku_id is None and (arc.sku_id == clean_sku or arc.sku_id is None)
                    )
                    if is_eligible and topic.topic_id not in self._completed_topic_ids:
                        resolved_next_topic_id = topic.topic_id
                        break
                if resolved_next_topic_id is not None:
                    break

        self._checkpoint = self._checkpoint.with_active_sku(
            clean_sku,
            current_arc_id=resolved_arc_id,
            next_topic_id=resolved_next_topic_id,
            updated_at=updated_at,
        )
        if updated_at is not None:
            self._last_ack_occurred_at = updated_at
        return self._checkpoint

    def build_agent_state(
        self,
        story_plan: StoryPlan,
        active_sku_id: Optional[str] = None,
        max_rewrite_retries: int = DEFAULT_MAX_REWRITE_RETRIES,
    ) -> AgentState:
        """Dựng `AgentState` đầu lượt đồng bộ từ trạng thái xác thực hiện hành của harness.

        Lý do kỹ thuật (`I-04`): P06 không được tự ý thay đổi `active_sku_id`; nếu caller
        truyền `active_sku_id`, giá trị đó bắt buộc phải khớp `checkpoint.active_sku_id`.

        Args:
            story_plan: Kế hoạch kể chuyện đã `APPROVED` khớp với checkpoint.
            active_sku_id: Mã SKU đang hoạt động do P08 chỉ định (tùy chọn; mặc định lấy từ checkpoint).
            max_rewrite_retries: Ngân sách viết lại tối đa cho lượt LangGraph.

        Returns:
            AgentState: Trạng thái đầu lượt hợp lệ (`is_authoritative_session_state=False`).

        Raises:
            TypeError: Nếu `story_plan` không phải `StoryPlan`.
            ValueError: Nếu `active_sku_id` lệch với `checkpoint.active_sku_id`, hoặc `story_plan`
                lệch `plan_id`/`plan_revision` với checkpoint.
        """
        if not isinstance(story_plan, StoryPlan):
            raise TypeError(
                f"story_plan phải là StoryPlan, nhận được {type(story_plan).__name__}."
            )
        if story_plan.plan_id != self._checkpoint.plan_id or story_plan.plan_revision != self._checkpoint.plan_revision:
            raise ValueError(
                f"story_plan (plan_id={story_plan.plan_id}, plan_revision={story_plan.plan_revision}) "
                f"không khớp checkpoint (plan_id={self._checkpoint.plan_id}, "
                f"plan_revision={self._checkpoint.plan_revision})."
            )

        if active_sku_id is not None:
            if not isinstance(active_sku_id, str) or not active_sku_id.strip():
                raise ValueError("active_sku_id phải là chuỗi khác rỗng hoặc None.")
            clean_sku = active_sku_id.strip()
            if clean_sku != self._checkpoint.active_sku_id:
                raise ValueError(
                    f"Bất biến I-04: active_sku_id='{clean_sku}' không khớp với "
                    f"checkpoint.active_sku_id='{self._checkpoint.active_sku_id}'."
                )

        return AgentState(
            tenant_id=self._checkpoint.tenant_id,
            session_id=self._checkpoint.session_id,
            session_epoch=self._checkpoint.session_epoch,
            active_sku_id=self._checkpoint.active_sku_id,
            story_plan=story_plan,
            story_checkpoint=self._checkpoint,
            played_history_window_size=self._window_size,
            played_history=self._played_history_store.to_agent_state_window(),
            completed_topic_ids=self.completed_topic_ids,
            rewrite_budget=RewriteBudgetState(max_retries=max_rewrite_retries),
        )

    def register_pending_turn(
        self,
        turn_id: str,
        candidate: SpeechCandidate,
        plan_revision: int,
        chunk_id: Optional[str] = None,
        next_topic_id: Optional[str] | _UnsetType = _UNSET,
        current_arc_id: Optional[str] = None,
        resume_mode: Optional[ResumeMode] = None,
        covered_claim_ids: Sequence[str] = (),
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
            covered_claim_ids: Danh sách `claim_id` gắn với lượt này để ghi vào `PlayedTurnSummary`.

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
            sku_refs=tuple(candidate.sku_refs),
            proposed_topic_ids=tuple(candidate.proposed_coverage.covered_topic_ids),
            covered_claim_ids=tuple(covered_claim_ids),
            has_next_topic_override=has_override,
            next_topic_id_after_turn=resolved_next_topic,
            next_arc_id_after_turn=current_arc_id,
            next_resume_mode=resume_mode,
        )
        # Ghi nhận phi thẩm quyền trước khi hoàn tất đăng ký (candidate đã được P05 VERIFIED ở trên).
        if self._topic_coverage is not None and record.proposed_topic_ids:
            self._topic_coverage.record_proposed_topics(record.proposed_topic_ids)
            self._topic_coverage.record_verified_topics(record.proposed_topic_ids)
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
            # Kiểm tra duplicate và đối chiếu đăng ký lượt chờ trước khi kết thúc turn_id (A-MAJ-01).
            if ack_result.turn_id in self._finalized_turns:
                return self._build_apply_result(
                    status=AckApplyStatus.REJECTED_DUPLICATE,
                    applied=False,
                    reason=f"Lượt '{ack_result.turn_id}' đã được kết thúc trước đó.",
                )
            pending = self._pending_turns.get(ack_result.turn_id)
            if pending is None:
                return self._build_apply_result(
                    status=AckApplyStatus.REJECTED_STALE_OR_MISMATCH,
                    applied=False,
                    reason=f"turn_id '{ack_result.turn_id}' chưa được đăng ký trong danh sách chờ phát.",
                )
            if ack_result.candidate_id != pending.candidate_id:
                return self._build_apply_result(
                    status=AckApplyStatus.REJECTED_STALE_OR_MISMATCH,
                    applied=False,
                    reason=(
                        f"Lệch candidate_id trên ACK {ack_result.outcome.value}: "
                        f"ack='{ack_result.candidate_id}', pending='{pending.candidate_id}'."
                    ),
                )
            if pending.plan_revision != self._checkpoint.plan_revision or (
                ack_result.plan_revision is not None
                and ack_result.plan_revision != pending.plan_revision
            ):
                return self._build_apply_result(
                    status=AckApplyStatus.REJECTED_STALE_OR_MISMATCH,
                    applied=False,
                    reason=(
                        f"Lệch plan_revision trên ACK {ack_result.outcome.value}: "
                        f"ack={ack_result.plan_revision}, pending={pending.plan_revision}, "
                        f"checkpoint={self._checkpoint.plan_revision}."
                    ),
                )

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
        return self._apply_completed_event(
            event=ack_result.event,
            expected_plan_revision=ack_result.plan_revision,
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
        expected_plan_revision: Optional[int],
        expected_intent: Optional[str],
        next_topic_id: Optional[str] | _UnsetType,
        current_arc_id: Optional[str],
        resume_mode: Optional[ResumeMode],
    ) -> PlaybackApplyResult:
        """Logic dùng chung kiểm định 4 lớp còn lại cho sự kiện `PlaybackCompleted` và commit nguyên tử."""
        # Lớp 2: Kiểm tra idempotency — chặn trùng playback_event_id hoặc turn_id đã xử lý.
        if (
            event.playback_event_id in self._seen_event_ids
            or self._played_history_store.has_event(event.playback_event_id)
        ):
            return self._build_apply_result(
                status=AckApplyStatus.REJECTED_DUPLICATE,
                applied=False,
                reason=f"Sự kiện '{event.playback_event_id}' đã được áp dụng trước đó (idempotent).",
            )
        if event.turn_id in self._finalized_turns or self._played_history_store.has_turn(event.turn_id):
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

        summary = PlayedTurnSummary.from_playback_completed(
            event,
            intent=pending.intent,
            covered_claim_ids=pending.covered_claim_ids,
        )
        new_checkpoint = self._checkpoint.advance_on_playback(
            event=event,
            next_topic_id=resolved_next_topic,
            current_arc_id=resolved_arc_id,
            resume_mode=resolved_resume_mode,
        )

        # Chỉ commit nguyên tử vào toàn bộ các lớp bộ nhớ và checkpoint sau khi mọi kiểm định thành công.
        self._played_history_store.append_confirmed_turn(
            summary,
            tenant_id=event.tenant_id,
            session_id=event.session_id,
            session_epoch=event.session_epoch,
        )
        if self._topic_coverage is not None:
            self._topic_coverage.record_playback_completed(event, pending.plan_revision)
            self._completed_topic_ids = (
                set(self._topic_coverage.completed_topic_ids)
                | self._initial_extra_completed_topic_ids
            )
        else:
            self._completed_topic_ids.update(event.confirmed_topic_ids)

        self._seen_event_ids.add(event.playback_event_id)
        self._finalized_turns.add(event.turn_id)
        self._pending_turns.pop(event.turn_id, None)
        self._last_ack_occurred_at = event.occurred_at
        if event.playout_generation is not None:
            self._last_playout_generation = event.playout_generation
        self._checkpoint = new_checkpoint
        # Chỉ lập chỉ mục vào semantic memory tùy chọn SAU KHI checkpoint và các kho cốt lõi đã commit xong.
        # Cô lập ngoại lệ tại đây để lỗi lập chỉ mục phụ không làm caller hiểu nhầm ACK thất bại hay replay.
        semantic_error: Optional[str] = None
        try:
            self._semantic_memory.index_played_turn(summary)
        except Exception as exc:
            semantic_error = f"{type(exc).__name__}: {exc}"
            self._semantic_index_errors.append(semantic_error)

        return self._build_apply_result(
            status=AckApplyStatus.APPLIED,
            applied=True,
            reason=None,
            semantic_index_error=semantic_error,
        )

    def _find_context_mismatch_reason(
        self,
        event: PlaybackCompleted,
        pending: PendingTurnRecord,
        incoming_plan_revision: Optional[int],
        incoming_intent: Optional[str],
    ) -> Optional[str]:
        """Kiểm tra toàn bộ trường ngữ cảnh, độ phủ hợp lệ và tính đơn điệu thời gian/generation."""
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
        if pending.plan_revision != self._checkpoint.plan_revision or (
            incoming_plan_revision is not None
            and incoming_plan_revision != self._checkpoint.plan_revision
        ):
            return (
                f"Lệch plan_revision: event={incoming_plan_revision}, "
                f"pending={pending.plan_revision}, checkpoint={self._checkpoint.plan_revision}."
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
        if pending.sku_refs and (
            set(event.sku_refs) != set(pending.sku_refs)
            or len(event.sku_refs) != len(pending.sku_refs)
        ):
            return (
                f"Lệch sku_refs: event={event.sku_refs}, pending={list(pending.sku_refs)}."
            )
        if self._story_plan is not None:
            unknown_topics = set(event.confirmed_topic_ids) - self._story_plan.all_topic_ids()
            if unknown_topics:
                return (
                    f"confirmed_topic_ids chứa topic không thuộc StoryPlan: {sorted(unknown_topics)}."
                )
        if self._topic_coverage is not None:
            if (
                event.tenant_id != self._topic_coverage.tenant_id
                or event.session_id != self._topic_coverage.session_id
                or pending.plan_revision != self._topic_coverage.plan_revision
            ):
                return "Sự kiện không khớp ngữ cảnh (tenant_id, session_id, plan_revision) của GlobalTopicCoverage."
            unknown_coverage_topics = (
                set(event.confirmed_topic_ids) - self._topic_coverage.planned_topic_ids
            )
            if unknown_coverage_topics:
                return (
                    f"confirmed_topic_ids chứa topic không thuộc GlobalTopicCoverage: "
                    f"{sorted(unknown_coverage_topics)}."
                )
        if event.event_source == PlaybackEventSource.SIMULATED_HARNESS:
            extra_topics = set(event.confirmed_topic_ids) - set(pending.proposed_topic_ids)
            if extra_topics:
                return (
                    f"confirmed_topic_ids chứa topic ngoài đề xuất của candidate: {sorted(extra_topics)}."
                )
        if self._last_ack_occurred_at is not None:
            if (event.occurred_at.tzinfo is None) != (self._last_ack_occurred_at.tzinfo is None):
                return "Múi giờ của event.occurred_at không đồng bộ với StoryCheckpoint.updated_at."
            if event.occurred_at < self._last_ack_occurred_at:
                return (
                    f"ACK đến sai thứ tự thời gian (stale): event.occurred_at={event.occurred_at.isoformat()} "
                    f"< last_ack={self._last_ack_occurred_at.isoformat()}."
                )
        if (
            event.playout_generation is not None
            and self._last_playout_generation is not None
            and event.playout_generation <= self._last_playout_generation
        ):
            return (
                f"playout_generation không tăng đơn điệu (stale barge-in): "
                f"event={event.playout_generation} <= last={self._last_playout_generation}."
            )
        return None

    def _build_apply_result(
        self,
        status: AckApplyStatus,
        applied: bool,
        reason: Optional[str],
        semantic_index_error: Optional[str] = None,
    ) -> PlaybackApplyResult:
        """Tạo `PlaybackApplyResult` phản ánh đúng trạng thái hiện hành của harness."""
        return PlaybackApplyResult(
            status=status,
            applied=applied,
            checkpoint=self._checkpoint,
            completed_topic_ids=frozenset(self._completed_topic_ids),
            played_history_count=len(self._played_history_store),
            auto_replay_permitted=False,
            reason=reason,
            semantic_index_error=semantic_index_error,
        )
