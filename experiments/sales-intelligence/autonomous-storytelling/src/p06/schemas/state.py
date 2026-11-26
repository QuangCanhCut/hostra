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

from datetime import datetime
from enum import Enum
from typing import Final, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from p06.schemas.candidate import CandidateVerificationStatus, SpeechCandidate
from p06.schemas.events import PlaybackCompleted, StoryCheckpoint
from p06.schemas.story import (
    CONTRACT_VERSION,
    ContractVersion,
    StoryChunk,
    StoryPlan,
    StoryPlanApprovalStatus,
)

# Hằng số cấu hình mặc định và biên an toàn cho cửa sổ trí nhớ ngắn hạn (W ∈ {5, 10, 20}) & bounded rewrite.
DEFAULT_PLAYED_HISTORY_WINDOW: Final[int] = 10
MAX_PLAYED_HISTORY_WINDOW: Final[int] = 100
DEFAULT_MAX_REWRITE_RETRIES: Final[int] = 2
MAX_REWRITE_RETRIES_LIMIT: Final[int] = 5


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
        intent: Ý định giao tiếp của lượt vừa phát.
        spoken_text: Toàn văn lời đã thực sự phát tới người xem.
        occurred_at: Thời điểm hoàn tất phát sóng.
        is_simulated: Phân biệt lượt chạy mô phỏng với thực tế.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    playback_event_id: str = Field(min_length=1)
    turn_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    chunk_id: Optional[str] = None
    sku_refs: list[str] = Field(default_factory=list)
    topic_ids: list[str] = Field(default_factory=list)
    intent: str = Field(min_length=1)
    spoken_text: str = Field(min_length=1)
    occurred_at: datetime
    is_simulated: bool

    @field_validator("intent", "spoken_text")
    @classmethod
    def strip_and_reject_blank_fields(cls, value: str) -> str:
        """Chuẩn hóa và ngăn chuỗi chỉ chứa khoảng trắng cho `intent` và `spoken_text`.

        Args:
            value: Chuỗi đầu vào cần kiểm tra.

        Returns:
            str: Chuỗi đã `strip()` hợp lệ.

        Raises:
            ValueError: Nếu chuỗi rỗng sau khi `strip()`.
        """
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("PlayedTurnSummary không chấp nhận intent hoặc spoken_text chỉ toàn khoảng trắng.")
        return cleaned

    @classmethod
    def from_playback_completed(
        cls,
        event: PlaybackCompleted,
        intent: str,
    ) -> PlayedTurnSummary:
        """Chuyển đổi một sự kiện `PlaybackCompleted` sang bản ghi tóm tắt cho bộ nhớ ngắn hạn.

        Args:
            event: Sự kiện xác nhận phát sóng hợp lệ từ P04 hoặc harness mô phỏng.
            intent: Ý định giao tiếp gắn với ứng viên đã phát trong sự kiện đó.

        Returns:
            PlayedTurnSummary: Bản ghi tóm tắt bất biến sẵn sàng nạp vào `played_history`.

        Raises:
            ValueError: Nếu `intent` rỗng hoặc toàn khoảng trắng.
        """
        return cls(
            playback_event_id=event.playback_event_id,
            turn_id=event.turn_id,
            candidate_id=event.candidate_id,
            chunk_id=event.chunk_id,
            sku_refs=list(event.sku_refs),
            topic_ids=list(event.confirmed_topic_ids),
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

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    max_retries: int = Field(default=DEFAULT_MAX_REWRITE_RETRIES, ge=0, le=MAX_REWRITE_RETRIES_LIMIT)
    retries_used: int = Field(default=0, ge=0)
    last_failure_reasons: list[str] = Field(default_factory=list)

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
        played_history: Danh sách các lượt thực sự đã phát gần nhất.
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

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    contract_version: ContractVersion = CONTRACT_VERSION
    is_authoritative_session_state: Literal[False] = False
    tenant_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    session_epoch: int = Field(ge=1)
    active_sku_id: str = Field(min_length=1)
    story_plan: StoryPlan
    story_checkpoint: StoryCheckpoint
    played_history_window_size: int = Field(
        default=DEFAULT_PLAYED_HISTORY_WINDOW,
        ge=1,
        le=MAX_PLAYED_HISTORY_WINDOW,
    )
    played_history: list[PlayedTurnSummary] = Field(default_factory=list)
    completed_topic_ids: set[str] = Field(default_factory=set)
    selected_arc_id: Optional[str] = None
    selected_topic_id: Optional[str] = None
    draft_chunk: Optional[StoryChunk] = None
    draft_candidate: Optional[SpeechCandidate] = None
    verified_candidate: Optional[SpeechCandidate] = None
    rewrite_budget: RewriteBudgetState = Field(default_factory=RewriteBudgetState)
    turn_outcome: AgentTurnOutcome = AgentTurnOutcome.IN_PROGRESS
    node_trace: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_agent_state_invariants(self) -> AgentState:
        """Kiểm định đồng bộ phiên, bất biến tách biệt draft/verified (I-02) và kết quả lượt.

        Returns:
            AgentState: Trạng thái đồ thị hợp lệ ở bất kỳ bước chuyển nào.

        Raises:
            ValueError: Nếu `story_plan` chưa `APPROVED`, lệch tenant/session/epoch/plan/SKU,
                `completed_topic_ids` chứa topic lạ, `draft_candidate`/`verified_candidate` vi phạm
                trạng thái hoặc `turn_outcome` mâu thuẫn với `verified_candidate`.
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

        # 3. StoryCheckpoint phải đồng nhất tuyệt đối với phiên, kế hoạch và arc hợp lệ (I-06).
        cp = self.story_checkpoint
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
        valid_arc_ids = {arc.arc_id for arc in self.story_plan.arcs}
        if cp.current_arc_id not in valid_arc_ids:
            raise ValueError(
                f"story_checkpoint.current_arc_id='{cp.current_arc_id}' không tồn tại trong story_plan.arcs."
            )

        # 4. Độ phủ chủ đề đã hoàn tất phải là tập con của các topic trong kế hoạch hiện hành.
        unknown_topics = self.completed_topic_ids - self.story_plan.all_topic_ids()
        if unknown_topics:
            raise ValueError(
                f"completed_topic_ids chứa topic không thuộc story_plan: {sorted(unknown_topics)}."
            )

        # 5. Cô lập ranh giới Draft vs Verified (Bất biến I-02) và đồng bộ tenant/session/epoch.
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

        # 6. Tính nhất quán giữa kết quả đầu lượt (`turn_outcome`) và sự hiện diện của `verified_candidate`.
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
