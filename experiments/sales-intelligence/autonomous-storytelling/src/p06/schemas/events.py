"""Hợp đồng dữ liệu Pydantic v2 cho sự kiện xác nhận phát sóng (`PlaybackCompleted`) và điểm dừng (`StoryCheckpoint`).

1. File này giải quyết vấn đề gì?
   Phân biệt rạch ròi giữa sự kiện phát sóng thực tế từ P04 (`PlaybackCompleted`) với điểm đánh dấu
   trạng thái kịch bản dùng để phục hồi sau khi bị bình luận ngắt quãng (`StoryCheckpoint`).
2. Trách nhiệm chính của module là gì?
   Định nghĩa nguồn phát sự kiện (`PlaybackEventSource`), chế độ nối mạch (`ResumeMode`), sự kiện
   `PlaybackCompleted` (tách biệt sự kiện mô phỏng `SIMULATED_HARNESS` và sự kiện thật `P04_MEDIA_CONTROLLER`)
   cùng `StoryCheckpoint` bảo toàn bất biến `I-06`.
3. Module này liên kết với các thành phần nào?
   Liên kết với `story.py` (chia sẻ `CONTRACT_VERSION`), `state.py` (`PlayedTurnSummary.from_playback_completed`
   và `AgentState.story_checkpoint`), `adapters/mocks/` (sinh ACK giả lập), và `simulation/` (E03 interrupt/resume).
4. Input và output chính là gì?
   Input là payload sự kiện phát sóng từ P04 hoặc harness mô phỏng;
   Output là các đối tượng `PlaybackCompleted` và `StoryCheckpoint` đã xác thực nguồn gốc và dấu vết.
5. Có những constraints hoặc invariants quan trọng nào?
   - `SIMULATED_HARNESS` bắt buộc `is_simulated=True`, có `simulation_run_id` và `p04_evidence_ref=None`.
   - `P04_MEDIA_CONTROLLER` bắt buộc `is_simulated=False`, có `p04_evidence_ref` và `simulation_run_id=None`.
   - Bất biến `I-06`: `StoryCheckpoint` chỉ được ghi nhận `last_completed_chunk_id` khi đi kèm
     `last_playback_event_id` hợp lệ (không thể tự đánh dấu đã nói xong chỉ từ trạng thái LLM/LangGraph).
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from p06.schemas.story import (
    CONTRACT_VERSION,
    ContractVersion,
    NonBlankStr,
    OptionalNonBlankStr,
    StrictPositiveDurationMs,
    StrictPositiveInt,
)


class PlaybackEventSource(str, Enum):
    """Nguồn phát hành sự kiện xác nhận đã phát sóng (`PlaybackCompleted`).

    Attributes:
        P04_MEDIA_CONTROLLER: Sự kiện thực từ bộ điều khiển phát sóng P04 trong môi trường tích hợp/thực.
        SIMULATED_HARNESS: Sự kiện giả lập từ bộ chạy thí nghiệm PoC (`simulation/`) phục vụ E01–E04.
    """

    P04_MEDIA_CONTROLLER = "P04_MEDIA_CONTROLLER"
    SIMULATED_HARNESS = "SIMULATED_HARNESS"


class PlaybackOutcomeStatus(str, Enum):
    """Trạng thái kết quả phát sóng trả về từ hạ tầng media P04 để phân biệt phát thành công và lỗi.

    Attributes:
        COMPLETED: Audio/video đã thực sự phát xong tới phòng live theo ACK của P04.
        FAILED: Quá trình phát sóng gặp lỗi trước hoặc trong khi phát, không được tính là đã phủ topic.
        UNKNOWN: Mất tín hiệu xác nhận cuối (timeout/reconnect), cần xử lý an toàn tránh phát lặp mù.
    """

    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class ResumeMode(str, Enum):
    """Chiến lược nối lại mạch kể chuyện sau khi trả lời bình luận xen ngang (P06-E03).

    Attributes:
        EXACT: Tiếp tục trực tiếp vào `next_topic_id` còn dang dở vì điểm ngắt vừa khít.
        CONTEXTUAL_BRIDGE: Chèn một câu chuyển tiếp (`TRANSITION_BRIDGE`) trước khi nói tiếp topic kế.
        REPLAN: Lập lại phần kế hoạch còn lại do ngữ cảnh hoặc SKU đã thay đổi đáng kể.
    """

    EXACT = "EXACT"
    CONTEXTUAL_BRIDGE = "CONTEXTUAL_BRIDGE"
    REPLAN = "REPLAN"


class PlaybackCompleted(BaseModel):
    """Sự kiện xác nhận một lượt lời thoại đã thực sự phát tới người xem (nguồn chân lý P04).

    Đây là tín hiệu duy nhất cho phép P06 cập nhật `played_history` và `completed_topic_ids` (I-03, I-06).

    Attributes:
        contract_version: Phiên bản hợp đồng dữ liệu (`p06-mock-v0.1`).
        playback_event_id: Mã định danh duy nhất của sự kiện phát sóng.
        tenant_id: Mã tenant sở hữu phiên.
        session_id: Mã phiên livestream.
        session_epoch: Thế hệ phiên hiện hành (>= 1).
        turn_id: Mã lượt phát sóng do P08 quản lý.
        candidate_id: Mã `SpeechCandidate` đã được phát.
        chunk_id: Mã `StoryChunk` tương ứng nếu lượt phát xuất phát từ mạch kể chuyện chủ động.
        playout_generation: Thế hệ hàng đợi phát sóng (nếu P04 gắn để chống stale barge-in).
        sku_refs: Danh sách SKU đã thực sự nhắc tới trong lượt phát.
        confirmed_topic_ids: Các `topic_id` được xác nhận đã hoàn tất sau phát sóng.
        confirmed_comment_ids: Các `comment_id` đã được trả lời xong.
        spoken_text: Nội dung văn bản thực tế đã phát ra loa/stream (cấm rỗng).
        actual_duration_ms: Thời lượng phát thực tế tính bằng mili-giây (> 0).
        occurred_at: Thời điểm phát sóng hoàn tất.
        event_source: Nguồn phát sự kiện (`P04_MEDIA_CONTROLLER` hoặc `SIMULATED_HARNESS`).
        is_simulated: Cờ phân biệt sự kiện mô phỏng với sự kiện production (cấm trộn lẫn).
        p04_evidence_ref: Tham chiếu bằng chứng log phát sóng của P04 (chỉ có khi là sự kiện thật).
        simulation_run_id: Mã lần chạy thí nghiệm giả lập (chỉ có khi là sự kiện mô phỏng).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: ContractVersion = CONTRACT_VERSION
    playback_event_id: NonBlankStr
    tenant_id: NonBlankStr
    session_id: NonBlankStr
    session_epoch: StrictPositiveInt
    turn_id: NonBlankStr
    candidate_id: NonBlankStr
    chunk_id: OptionalNonBlankStr = None
    playout_generation: Optional[StrictPositiveInt] = None
    sku_refs: list[NonBlankStr] = Field(default_factory=list)
    confirmed_topic_ids: list[NonBlankStr] = Field(default_factory=list)
    confirmed_comment_ids: list[NonBlankStr] = Field(default_factory=list)
    spoken_text: NonBlankStr
    actual_duration_ms: StrictPositiveDurationMs
    occurred_at: datetime
    event_source: PlaybackEventSource
    is_simulated: StrictBool
    p04_evidence_ref: OptionalNonBlankStr = None
    simulation_run_id: OptionalNonBlankStr = None

    @model_validator(mode="after")
    def validate_event_source_provenance(self) -> PlaybackCompleted:
        """Bảo đảm sự kiện mô phỏng và sự kiện P04 thật mang đầy đủ dấu vết tương ứng, không lẫn lộn.

        Returns:
            PlaybackCompleted: Sự kiện hợp lệ sau khi đối chiếu nguồn phát và cờ `is_simulated`.

        Raises:
            ValueError: Nếu `SIMULATED_HARNESS` thiếu `simulation_run_id` / đặt sai `is_simulated` /
                chứa `p04_evidence_ref`, hoặc `P04_MEDIA_CONTROLLER` vi phạm điều kiện ngược lại.
        """
        if self.event_source == PlaybackEventSource.SIMULATED_HARNESS:
            if self.is_simulated is not True:
                raise ValueError(
                    "Sự kiện từ SIMULATED_HARNESS bắt buộc phải đặt is_simulated=True."
                )
            if self.simulation_run_id is None or not self.simulation_run_id.strip():
                raise ValueError(
                    "Sự kiện từ SIMULATED_HARNESS bắt buộc phải có simulation_run_id không rỗng."
                )
            if self.p04_evidence_ref is not None:
                raise ValueError(
                    "Sự kiện từ SIMULATED_HARNESS không được phép chứa p04_evidence_ref."
                )

        elif self.event_source == PlaybackEventSource.P04_MEDIA_CONTROLLER:
            if self.is_simulated is not False:
                raise ValueError(
                    "Sự kiện từ P04_MEDIA_CONTROLLER bắt buộc phải đặt is_simulated=False."
                )
            if self.p04_evidence_ref is None or not self.p04_evidence_ref.strip():
                raise ValueError(
                    "Sự kiện từ P04_MEDIA_CONTROLLER bắt buộc phải có p04_evidence_ref không rỗng."
                )
            if self.simulation_run_id is not None:
                raise ValueError(
                    "Sự kiện từ P04_MEDIA_CONTROLLER không được phép chứa simulation_run_id."
                )

        return self


class StoryCheckpoint(BaseModel):
    """Điểm đánh dấu tiến độ kể chuyện để phục hồi chính xác sau ngắt quãng (I-06, P06-E03).

    Attributes:
        contract_version: Phiên bản hợp đồng dữ liệu (`p06-mock-v0.1`).
        tenant_id: Mã tenant sở hữu phiên (bảo đảm cô lập R10 khi lưu trữ độc lập).
        session_id: Mã phiên livestream.
        session_epoch: Thế hệ phiên tương ứng.
        plan_id: Mã `StoryPlan` đang thực thi.
        plan_revision: Phiên bản `StoryPlan` đang thực thi.
        active_sku_id: Mã SKU đang hoạt động do P08 chỉ định (P06 chỉ đọc).
        current_arc_id: Mã `StoryArc` hiện tại trong kế hoạch.
        next_topic_id: Mã `StoryTopic` kế tiếp sẽ nói (hoặc `None` nếu đã hết kế hoạch).
        last_completed_chunk_id: Mã `StoryChunk` cuối cùng đã phát xong hoàn toàn.
        last_playback_event_id: Mã `PlaybackCompleted` chứng minh cho `last_completed_chunk_id`.
        resume_mode: Chiến lược nối lại mạch kể ở lượt tiếp theo.
        updated_at: Thời điểm cập nhật checkpoint (UTC).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: ContractVersion = CONTRACT_VERSION
    tenant_id: NonBlankStr
    session_id: NonBlankStr
    session_epoch: StrictPositiveInt
    plan_id: NonBlankStr
    plan_revision: StrictPositiveInt
    active_sku_id: NonBlankStr
    current_arc_id: NonBlankStr
    next_topic_id: OptionalNonBlankStr = None
    last_completed_chunk_id: OptionalNonBlankStr = None
    last_playback_event_id: OptionalNonBlankStr = None
    resume_mode: ResumeMode = ResumeMode.EXACT
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_playback_evidence_for_completed_chunk(self) -> StoryCheckpoint:
        """Thực thi bất biến I-06: không thể đánh dấu chunk đã hoàn tất nếu thiếu ACK từ P04.

        Returns:
            StoryCheckpoint: Checkpoint hợp lệ bảo đảm 0 replay và không đánh dấu ảo.

        Raises:
            ValueError: Nếu `last_completed_chunk_id` khác `None` nhưng `last_playback_event_id`
                bị thiếu hoặc rỗng.
        """
        if self.last_completed_chunk_id is not None:
            if self.last_playback_event_id is None or not self.last_playback_event_id.strip():
                raise ValueError(
                    "Bất biến I-06: StoryCheckpoint có last_completed_chunk_id bắt buộc phải có "
                    "last_playback_event_id không rỗng chứng minh đã phát xong."
                )
        return self

    def advance_on_playback(
        self,
        event: PlaybackCompleted,
        next_topic_id: Optional[str],
        current_arc_id: Optional[str] = None,
        resume_mode: Optional[ResumeMode] = None,
    ) -> StoryCheckpoint:
        """Tạo checkpoint mới một cách nguyên tử sau khi nhận sự kiện `PlaybackCompleted` (I-06).

        Lý do kỹ thuật: Chỉ cho phép tịnh tiến `last_completed_chunk_id` khi gắn kèm
        `last_playback_event_id` từ đúng `(tenant_id, session_id, session_epoch)` của phiên.

        Args:
            event: Sự kiện xác nhận phát sóng hợp lệ.
            next_topic_id: Mã chủ đề tiếp theo sẽ nói (hoặc `None` nếu đã hoàn tất kế hoạch).
            current_arc_id: Mã arc hiện tại mới (nếu vừa chuyển sang arc kế tiếp).
            resume_mode: Chế độ nối mạch cho lượt tiếp theo (giữ nguyên nếu `None`).

        Returns:
            StoryCheckpoint: Điểm dừng mới đã qua kiểm định `model_validate()`.

        Raises:
            ValueError: Nếu `event` lệch `tenant_id`, `session_id`, hoặc `session_epoch`.
            ValidationError: Nếu `next_topic_id` hoặc `current_arc_id` là chuỗi toàn khoảng trắng.
        """
        if (
            event.tenant_id != self.tenant_id
            or event.session_id != self.session_id
            or event.session_epoch != self.session_epoch
        ):
            raise ValueError(
                "PlaybackCompleted không khớp (tenant_id, session_id, session_epoch) với StoryCheckpoint."
            )

        payload = copy.deepcopy(self.model_dump())
        payload["next_topic_id"] = next_topic_id
        if current_arc_id is not None:
            payload["current_arc_id"] = current_arc_id
        if resume_mode is not None:
            payload["resume_mode"] = resume_mode
        # Chỉ ghi đè dấu vết StoryChunk khi lượt phát thực sự thuộc một StoryChunk để không làm mất checkpoint sau comment reply/bridge.
        if event.chunk_id is not None:
            payload["last_completed_chunk_id"] = event.chunk_id
            payload["last_playback_event_id"] = event.playback_event_id
        payload["updated_at"] = event.occurred_at
        return type(self).model_validate(payload)
