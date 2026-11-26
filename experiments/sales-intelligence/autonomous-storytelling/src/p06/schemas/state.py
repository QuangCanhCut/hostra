"""Hợp đồng dữ liệu Pydantic v2 cho trạng thái đồ thị LangGraph (`AgentState`) và bộ nhớ ngắn hạn.

1. File này giải quyết vấn đề gì?
   Cung cấp cấu trúc trạng thái thống nhất cho từng lượt chạy của LangGraph (`StateGraph(AgentState)`),
   bao gồm cửa sổ lịch sử đã phát (`PlayedTurnSummary`), ngân sách viết lại có giới hạn (`RewriteBudgetState`)
   và kết quả đầu ra của lượt (`AgentTurnOutcome`).
2. Trách nhiệm chính của module là gì?
   Định nghĩa các hằng số cửa sổ/retry mặc định, Enum `AgentTurnOutcome`, và các model `PlayedTurnSummary`,
   `RewriteBudgetState`, `AgentState` kèm bộ kiểm định liên trường toàn diện.
3. Module này liên kết với các thành phần nào?
   Tổng hợp các model từ `story.py`, `candidate.py`, `events.py`, và làm schema state đầu vào/đầu ra
   cho `agent/` (LangGraph nodes), `memory/` (PlayedHistory & TopicCoverage), và `guardrails/`.
4. Input và output chính là gì?
   Input là ngữ cảnh đầu lượt gồm `StoryPlan` đã `APPROVED`, `StoryCheckpoint`, cửa sổ `played_history`;
   Output là `AgentState` ở cuối lượt chứa `verified_candidate` (nếu hợp lệ) và `turn_outcome`.
5. Có những constraints hoặc invariants quan trọng nào?
   - `is_authoritative_session_state` luôn là `False` (I-01/I-04): LangGraph state chỉ là working memory
     cho một lượt, tuyệt đối không thay thế state phiên chính thức của P08/P09.
   - `story_plan` phải ở trạng thái `APPROVED`, đồng nhất `tenant_id`, `session_id`, `session_epoch`,
     `active_sku_id` với `story_checkpoint`.
   - Tách bạch trạng thái draft vs verified (I-02): `draft_candidate` không được là `VERIFIED`, và
     `verified_candidate` bắt buộc phải là `VERIFIED`.
   - Nhất quán đầu ra: `VERIFIED_READY`/`FALLBACK_PREAPPROVED` bắt buộc có `verified_candidate`;
     `SAFE_ABORT_NO_CANDIDATE` bắt buộc `verified_candidate is None`.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Final, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from p06.schemas.candidate import CandidateVerificationStatus, SpeechCandidate
from p06.schemas.events import PlaybackCompleted, StoryCheckpoint
from p06.schemas.story import (
    CONTRACT_VERSION,
    ContractVersion,
    NonBlankStr,
    OptionalNonBlankStr,
    StoryChunk,
    StoryPlan,
    StoryPlanApprovalStatus,
    StrictFalse,
    StrictNonNegInt,
    StrictPositiveInt,
)

# Hằng số cấu hình mặc định và biên an toàn cho cửa sổ trí nhớ ngắn hạn (W ∈ {5, 10, 20}) & bounded rewrite.
DEFAULT_PLAYED_HISTORY_WINDOW: Final[int] = 10
MAX_PLAYED_HISTORY_WINDOW: Final[int] = 100
DEFAULT_MAX_REWRITE_RETRIES: Final[int] = 2
MAX_REWRITE_RETRIES_LIMIT: Final[int] = 5


def _normalize_value_for_revalidation(value: Any) -> Any:
    """Chuẩn hóa đệ quy mọi `BaseModel` và container khả biến để ép tái kiểm định và chống aliasing.

    Lý do kỹ thuật: Khi truyền trực tiếp một instance Pydantic (hoặc list/dict chứa instance đó)
    vào `validated_update()` / `from_graph_result()`, việc chuyển `BaseModel -> deepcopy(model_dump())`
    và deep-copy container bảo đảm toàn bộ `@model_validator` lồng nhau đều chạy lại và không
    còn tham chiếu chung với container bên ngoài (`[A-BLK-01]`).
    """
    if isinstance(value, BaseModel):
        return copy.deepcopy(value.model_dump())
    if isinstance(value, list):
        return [_normalize_value_for_revalidation(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize_value_for_revalidation(item) for item in value)
    if isinstance(value, set):
        return {_normalize_value_for_revalidation(item) for item in value}
    if isinstance(value, frozenset):
        return frozenset(_normalize_value_for_revalidation(item) for item in value)
    if isinstance(value, Mapping):
        return {
            _normalize_value_for_revalidation(k): _normalize_value_for_revalidation(v)
            for k, v in value.items()
        }
    return copy.deepcopy(value)


class AgentTurnOutcome(str, Enum):
    """Trạng thái kết thúc của một lượt thực thi LangGraph trong P06 (P06-E04).

    Attributes:
        IN_PROGRESS: Lượt thực thi đang chạy qua các node trong đồ thị.
        VERIFIED_READY: Đã có ứng viên lời thoại vượt qua Cổng P05, sẵn sàng gửi P08/TTS.
        FALLBACK_PREAPPROVED: Hết ngân sách rewrite hoặc model lỗi, chuyển sang câu dự phòng đã duyệt.
        SAFE_ABORT_NO_CANDIDATE: Không tìm được phương án an toàn hợp lệ, trả về rỗng để chuyển safe scene.
    """

    IN_PROGRESS = "IN_PROGRESS"
    VERIFIED_READY = "VERIFIED_READY"
    FALLBACK_PREAPPROVED = "FALLBACK_PREAPPROVED"
    SAFE_ABORT_NO_CANDIDATE = "SAFE_ABORT_NO_CANDIDATE"


class PlayedTurnSummary(BaseModel):
    """Bản tóm tắt bất biến một lượt đã phát thực sự, trích xuất từ `PlaybackCompleted` để chống lặp.

    Attributes:
        playback_event_id: Mã sự kiện `PlaybackCompleted` làm căn cứ ghi nhận.
        turn_id: Mã lượt phát sóng.
        candidate_id: Mã `SpeechCandidate` đã phát.
        chunk_id: Mã `StoryChunk` (nếu có).
        sku_refs: Danh sách SKU đã nhắc trong lượt.
        topic_ids: Danh sách `topic_id` đã được xác nhận phủ qua phát sóng.
        covered_claim_ids: Danh sách `claim_id` đã được phủ trong lượt phát phục vụ chống lặp E01-T06.
        confirmed_comment_ids: Danh sách `comment_id` đã được xác nhận trả lời xong trong lượt.
        intent: Ý định giao tiếp của lượt vừa phát.
        spoken_text: Toàn văn lời đã thực sự phát tới người xem.
        occurred_at: Thời điểm hoàn tất phát sóng.
        is_simulated: Phân biệt lượt chạy mô phỏng với thực tế.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    playback_event_id: NonBlankStr
    turn_id: NonBlankStr
    candidate_id: NonBlankStr
    chunk_id: OptionalNonBlankStr = None
    sku_refs: list[NonBlankStr] = Field(default_factory=list)
    topic_ids: list[NonBlankStr] = Field(default_factory=list)
    covered_claim_ids: list[NonBlankStr] = Field(default_factory=list)
    confirmed_comment_ids: list[NonBlankStr] = Field(default_factory=list)
    intent: NonBlankStr
    spoken_text: NonBlankStr
    occurred_at: datetime
    is_simulated: StrictBool

    @classmethod
    def from_playback_completed(
        cls,
        event: PlaybackCompleted,
        intent: str,
        covered_claim_ids: Sequence[str] = (),
    ) -> PlayedTurnSummary:
        """Chuyển đổi một sự kiện `PlaybackCompleted` sang bản ghi tóm tắt cho bộ nhớ ngắn hạn.

        Args:
            event: Sự kiện xác nhận phát sóng hợp lệ từ P04 hoặc harness mô phỏng.
            intent: Ý định giao tiếp gắn với ứng viên đã phát trong sự kiện đó.
            covered_claim_ids: Danh sách `claim_id` đã phủ ở lượt phát tương ứng (nếu có).

        Returns:
            PlayedTurnSummary: Bản ghi tóm tắt bất biến sẵn sàng nạp vào `played_history`.

        Raises:
            ValidationError: Nếu `intent` rỗng, toàn khoảng trắng hoặc không phải chuỗi.
        """
        return cls(
            playback_event_id=event.playback_event_id,
            turn_id=event.turn_id,
            candidate_id=event.candidate_id,
            chunk_id=event.chunk_id,
            sku_refs=list(event.sku_refs),
            topic_ids=list(event.confirmed_topic_ids),
            covered_claim_ids=list(covered_claim_ids),
            confirmed_comment_ids=list(event.confirmed_comment_ids),
            intent=intent,
            spoken_text=event.spoken_text,
            occurred_at=event.occurred_at,
            is_simulated=event.is_simulated,
        )


class RewriteBudgetState(BaseModel):
    """Trạng thái ngân sách viết lại có giới hạn (bounded rewrite) khi P05 từ chối (P06-E04).

    Attributes:
        max_retries: Số lần thử viết lại tối đa cho phép trong một lượt (`0..MAX_REWRITE_RETRIES_LIMIT`).
        retries_used: Số lần viết lại đã tiêu thụ (`<= max_retries`).
        last_failure_reasons: Lý do bị P05 chặn ở lần gần nhất, dùng làm phản hồi cho node rewrite.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    max_retries: Annotated[StrictInt, Field(ge=0, le=MAX_REWRITE_RETRIES_LIMIT)] = (
        DEFAULT_MAX_REWRITE_RETRIES
    )
    retries_used: StrictNonNegInt = 0
    last_failure_reasons: list[NonBlankStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_budget_bounds(self) -> RewriteBudgetState:
        """Đảm bảo số lần đã thử lại không bao giờ vượt quá ngân sách tối đa.

        Returns:
            RewriteBudgetState: Trạng thái ngân sách hợp lệ.

        Raises:
            ValueError: Nếu `retries_used > max_retries`.
        """
        if self.retries_used > self.max_retries:
            raise ValueError(
                f"retries_used ({self.retries_used}) không được vượt quá max_retries ({self.max_retries})."
            )
        return self

    @property
    def can_retry(self) -> bool:
        """Cho biết đồ thị có còn quyền thực hiện thêm một bước rewrite hay không.

        Returns:
            bool: `True` nếu `retries_used < max_retries`, ngược lại `False`.
        """
        return self.retries_used < self.max_retries


class AgentState(BaseModel):
    """Trạng thái làm việc theo từng lượt của LangGraph `StateGraph` trong P06.

    Trạng thái này chỉ là working memory tạm thời của P06 (`is_authoritative_session_state=False`),
    không thay thế P08/P09 trong việc giữ `Active SKU` hay xác nhận hoàn tất phát sóng.

    Lưu ý an toàn: Không bao giờ sử dụng `model_copy(update=...)` vì phương thức đó bỏ qua
    toàn bộ validator của Pydantic v2; hãy dùng `validated_update(...)` hoặc `from_graph_result(...)`.

    Attributes:
        contract_version: Phiên bản hợp đồng dữ liệu (`p06-mock-v0.1`).
        is_authoritative_session_state: Luôn là `False` theo bất biến I-01/I-04.
        tenant_id: Mã tenant hiện hành.
        session_id: Mã phiên livestream hiện hành.
        session_epoch: Thế hệ phiên hiện hành (>= 1).
        active_sku_id: Mã SKU đang active do P08 truyền vào (bắt buộc thuộc `story_plan.pinned_sku_ids`).
        story_plan: Kế hoạch kể chuyện đã ở trạng thái `APPROVED`.
        story_checkpoint: Điểm dừng/nối mạch đồng bộ với `story_plan` và phiên.
        played_history_window_size: Kích thước cửa sổ `W` cấu hình qua YAML (`1..MAX_PLAYED_HISTORY_WINDOW`).
        played_history: Danh sách các lượt thực sự đã phát gần nhất (`len <= played_history_window_size`).
        completed_topic_ids: Tập các `topic_id` đã hoàn tất (tập con của `story_plan.all_topic_ids()`).
        selected_arc_id: Arc được chọn để sinh nội dung trong lượt hiện tại.
        selected_topic_id: Topic được chọn để sinh nội dung trong lượt hiện tại.
        draft_chunk: Bản nháp `StoryChunk` vừa sinh trong lượt (nếu là proactive story).
        draft_candidate: Ứng viên `SpeechCandidate` chưa `VERIFIED` (đang nháp hoặc vừa bị `REJECTED`).
        verified_candidate: Ứng viên `SpeechCandidate` đã đạt `VERIFIED` từ P05.
        rewrite_budget: Trạng thái bộ đếm retry có giới hạn.
        turn_outcome: Kết quả cuối lượt của đồ thị.
        node_trace: Vết tên các node đã đi qua trong lượt để phục vụ kiểm thử và báo cáo E04.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    contract_version: ContractVersion = CONTRACT_VERSION
    is_authoritative_session_state: StrictFalse = False
    tenant_id: NonBlankStr
    session_id: NonBlankStr
    session_epoch: StrictPositiveInt
    active_sku_id: NonBlankStr
    story_plan: StoryPlan
    story_checkpoint: StoryCheckpoint
    played_history_window_size: Annotated[
        StrictInt, Field(ge=1, le=MAX_PLAYED_HISTORY_WINDOW)
    ] = DEFAULT_PLAYED_HISTORY_WINDOW
    played_history: list[PlayedTurnSummary] = Field(default_factory=list)
    completed_topic_ids: frozenset[NonBlankStr] = Field(default_factory=frozenset)
    selected_arc_id: OptionalNonBlankStr = None
    selected_topic_id: OptionalNonBlankStr = None
    draft_chunk: Optional[StoryChunk] = None
    draft_candidate: Optional[SpeechCandidate] = None
    verified_candidate: Optional[SpeechCandidate] = None
    rewrite_budget: RewriteBudgetState = Field(default_factory=RewriteBudgetState)
    turn_outcome: AgentTurnOutcome = AgentTurnOutcome.IN_PROGRESS
    node_trace: list[NonBlankStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_agent_state_invariants(self) -> AgentState:
        """Kiểm định đồng bộ phiên, toàn vẹn tham chiếu kế hoạch, tách biệt draft/verified (I-02) và kết quả lượt.

        Returns:
            AgentState: Trạng thái đồ thị hợp lệ ở bất kỳ bước chuyển nào.

        Raises:
            ValueError: Nếu `story_plan` chưa `APPROVED`, lệch tenant/session/epoch/plan/SKU,
                vi phạm tham chiếu arc/topic/chunk, vượt `played_history_window_size`,
                `draft_candidate`/`verified_candidate` vi phạm trạng thái hoặc `turn_outcome`
                mâu thuẫn với `verified_candidate`.
        """
        # 1. Kế hoạch phải đã được merchant/Owner phê duyệt và khớp ngữ cảnh tenant/session (Gate G6).
        if self.story_plan.approval_status != StoryPlanApprovalStatus.APPROVED:
            raise ValueError(
                f"AgentState yêu cầu story_plan ở trạng thái APPROVED, hiện tại là "
                f"'{self.story_plan.approval_status.value}'."
            )
        if self.story_plan.tenant_id != self.tenant_id or self.story_plan.session_id != self.session_id:
            raise ValueError(
                "tenant_id hoặc session_id của story_plan không khớp với AgentState."
            )

        # 2. Active SKU do P08 truyền vào bắt buộc nằm trong danh sách SKU ghim của phiên (ACR-002, I-04).
        if self.active_sku_id not in self.story_plan.pinned_sku_ids:
            raise ValueError(
                f"active_sku_id='{self.active_sku_id}' không nằm trong story_plan.pinned_sku_ids."
            )

        # 3. StoryCheckpoint phải đồng nhất tuyệt đối với tenant, phiên, kế hoạch, arc và next_topic_id (I-06, R10).
        cp = self.story_checkpoint
        if cp.tenant_id != self.tenant_id:
            raise ValueError(
                f"story_checkpoint.tenant_id='{cp.tenant_id}' không khớp với AgentState.tenant_id='{self.tenant_id}'."
            )
        if cp.session_id != self.session_id or cp.session_epoch != self.session_epoch:
            raise ValueError(
                "story_checkpoint không khớp session_id hoặc session_epoch của AgentState."
            )
        if cp.plan_id != self.story_plan.plan_id or cp.plan_revision != self.story_plan.plan_revision:
            raise ValueError(
                "story_checkpoint không khớp plan_id hoặc plan_revision của story_plan."
            )
        if cp.active_sku_id != self.active_sku_id:
            raise ValueError(
                f"story_checkpoint.active_sku_id='{cp.active_sku_id}' không khớp với "
                f"AgentState.active_sku_id='{self.active_sku_id}'."
            )

        topics_by_arc: dict[str, set[str]] = {
            arc.arc_id: {topic.topic_id for topic in arc.topics}
            for arc in self.story_plan.arcs
        }
        valid_arc_ids = set(topics_by_arc.keys())
        all_topic_ids = self.story_plan.all_topic_ids()

        if cp.current_arc_id not in valid_arc_ids:
            raise ValueError(
                f"story_checkpoint.current_arc_id='{cp.current_arc_id}' không tồn tại trong story_plan.arcs."
            )
        if cp.next_topic_id is not None and cp.next_topic_id not in all_topic_ids:
            raise ValueError(
                f"story_checkpoint.next_topic_id='{cp.next_topic_id}' không tồn tại trong story_plan."
            )

        # 4. Độ phủ chủ đề, vùng chọn arc/topic hiện tại và draft_chunk phải tham chiếu đúng kế hoạch.
        unknown_topics = self.completed_topic_ids - all_topic_ids
        if unknown_topics:
            raise ValueError(
                f"completed_topic_ids chứa topic không thuộc story_plan: {sorted(unknown_topics)}."
            )

        if self.selected_arc_id is not None and self.selected_arc_id not in valid_arc_ids:
            raise ValueError(
                f"selected_arc_id='{self.selected_arc_id}' không tồn tại trong story_plan.arcs."
            )

        if self.selected_topic_id is not None:
            if self.selected_topic_id not in all_topic_ids:
                raise ValueError(
                    f"selected_topic_id='{self.selected_topic_id}' không tồn tại trong story_plan."
                )
            if (
                self.selected_arc_id is not None
                and self.selected_topic_id not in topics_by_arc[self.selected_arc_id]
            ):
                raise ValueError(
                    f"selected_topic_id='{self.selected_topic_id}' không thuộc "
                    f"selected_arc_id='{self.selected_arc_id}'."
                )

        if self.draft_chunk is not None:
            chunk = self.draft_chunk
            if (
                chunk.plan_id != self.story_plan.plan_id
                or chunk.plan_revision != self.story_plan.plan_revision
            ):
                raise ValueError(
                    "draft_chunk không khớp plan_id hoặc plan_revision với story_plan."
                )
            if chunk.arc_id not in valid_arc_ids:
                raise ValueError(
                    f"draft_chunk.arc_id='{chunk.arc_id}' không tồn tại trong story_plan.arcs."
                )
            if chunk.topic_id not in topics_by_arc[chunk.arc_id]:
                raise ValueError(
                    f"draft_chunk.topic_id='{chunk.topic_id}' không thuộc arc '{chunk.arc_id}' trong story_plan."
                )
            if chunk.sku_id is not None and chunk.sku_id not in self.story_plan.pinned_sku_ids:
                raise ValueError(
                    f"draft_chunk.sku_id='{chunk.sku_id}' không nằm trong story_plan.pinned_sku_ids."
                )

        # 5. Cửa sổ trí nhớ ngắn hạn không được vượt quá giới hạn `played_history_window_size`.
        if len(self.played_history) > self.played_history_window_size:
            raise ValueError(
                f"played_history ({len(self.played_history)}) vượt quá "
                f"played_history_window_size ({self.played_history_window_size})."
            )

        # 6. Cô lập ranh giới Draft vs Verified (Bất biến I-02) và đồng bộ tenant/session/epoch.
        if self.draft_candidate is not None:
            if self.draft_candidate.verification_status == CandidateVerificationStatus.VERIFIED:
                raise ValueError(
                    "draft_candidate không được phép mang trạng thái VERIFIED (phải đặt vào verified_candidate)."
                )
            self._validate_candidate_context(self.draft_candidate, field_name="draft_candidate")

        if self.verified_candidate is not None:
            if self.verified_candidate.verification_status != CandidateVerificationStatus.VERIFIED:
                raise ValueError(
                    f"verified_candidate bắt buộc phải có verification_status=VERIFIED, nhận được "
                    f"'{self.verified_candidate.verification_status.value}'."
                )
            self._validate_candidate_context(self.verified_candidate, field_name="verified_candidate")

        # 7. Tính nhất quán giữa kết quả đầu lượt (`turn_outcome`) và sự hiện diện của `verified_candidate`.
        if self.turn_outcome in {
            AgentTurnOutcome.VERIFIED_READY,
            AgentTurnOutcome.FALLBACK_PREAPPROVED,
        }:
            if self.verified_candidate is None:
                raise ValueError(
                    f"turn_outcome={self.turn_outcome.value} bắt buộc phải có verified_candidate khác None."
                )
        elif self.turn_outcome == AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE:
            if self.verified_candidate is not None:
                raise ValueError(
                    "turn_outcome=SAFE_ABORT_NO_CANDIDATE bắt buộc verified_candidate phải là None."
                )

        return self

    def validated_update(self, **changes: Any) -> AgentState:
        """Tạo bản sao `AgentState` mới có kiểm định toàn vẹn thay cho `model_copy(update=...)`.

        Lý do kỹ thuật: `BaseModel.model_copy(update=...)` của Pydantic v2 bỏ qua toàn bộ field
        validator và `@model_validator(mode="after")`, dễ tạo ra state vi phạm bất biến `I-02`/`I-06`
        nhưng không bị phát hiện. Phương thức này chuẩn hóa đệ quy mọi `BaseModel`/container khả biến
        và đi qua `model_validate()` để ép chạy lại toàn bộ validator lồng nhau (`[A-BLK-01]`).

        Args:
            **changes: Các trường cần cập nhật theo cặp tên trường -> giá trị mới.

        Returns:
            AgentState: Bản sao state mới hợp lệ hoàn toàn sau kiểm định.

        Raises:
            ValidationError: Nếu có trường thừa, sai kiểu, hoặc làm gãy bất biến liên trường.
        """
        payload = copy.deepcopy(self.model_dump())
        normalized_changes = {
            key: _normalize_value_for_revalidation(value)
            for key, value in changes.items()
        }
        payload.update(normalized_changes)
        return type(self).model_validate(payload)

    @classmethod
    def from_graph_result(cls, result: Mapping[str, Any] | AgentState) -> AgentState:
        """Kiểm định lại bắt buộc ở ranh giới đầu ra của `StateGraph.invoke()` (khắc phục A-BLK-01).

        Lý do kỹ thuật: LangGraph `StateGraph(AgentState).compile().invoke()` trả về `dict` thô
        và không tự chạy `@model_validator(mode="after")` trên trạng thái cuối cùng sau node cuối.
        Mọi caller gọi đồ thị bắt buộc phải đi qua cổng `from_graph_result()` để chặn state lỗi
        và loại bỏ aliasing container từ các node.

        Args:
            result: Kết quả thô (`Mapping`) hoặc `AgentState` trả về từ LangGraph `invoke()`.

        Returns:
            AgentState: Đối tượng `AgentState` đã được tái kiểm định toàn bộ bất biến.

        Raises:
            ValidationError: Nếu kết quả đồ thị vi phạm bất kỳ ràng buộc nào của `AgentState`.
            TypeError: Nếu `result` không phải `Mapping` hay `AgentState`.
        """
        if isinstance(result, cls):
            return cls.model_validate(copy.deepcopy(result.model_dump()))
        if isinstance(result, Mapping):
            normalized = _normalize_value_for_revalidation(dict(result))
            return cls.model_validate(normalized)
        raise TypeError(
            f"AgentState.from_graph_result chỉ nhận Mapping hoặc AgentState, nhận được {type(result).__name__}."
        )

    def _validate_candidate_context(self, candidate: SpeechCandidate, field_name: str) -> None:
        """Kiểm tra ứng viên lời thoại khớp đúng `tenant_id`, `session_id` và `session_epoch` của state.

        Args:
            candidate: Ứng viên cần kiểm tra ngữ cảnh.
            field_name: Tên trường chứa ứng viên để thông báo lỗi rõ ràng.

        Raises:
            ValueError: Nếu ứng viên bị rò rỉ từ tenant, session hoặc epoch khác.
        """
        if (
            candidate.tenant_id != self.tenant_id
            or candidate.session_id != self.session_id
            or candidate.session_epoch != self.session_epoch
        ):
            raise ValueError(
                f"{field_name} không khớp (tenant_id, session_id, session_epoch) với AgentState."
            )
