"""Hợp đồng cổng trừu tượng (Ports) và DTO trao đổi dữ liệu cho tầng Adapter của P06.

1. File này giải quyết vấn đề gì?
   Áp dụng nguyên lý Dependency Inversion và Adapter Pattern để tách biệt logic nghiệp vụ của P06
   (LangGraph nodes, guardrails, simulation) khỏi chi tiết cài đặt cụ thể của P05 (`PublicationGate`),
   P04 (`PlaybackCompleted` bus) hay các bộ mock phục vụ thí nghiệm.
2. Trách nhiệm chính của module là gì?
   Định nghĩa các DTO bất biến (`SkuEvidenceView`, `CandidateVerificationResult`, `PlaybackAckResult`,
   `PlaybackApplyResult`, `AckApplyStatus`) và các giao diện trừu tượng `KnowledgeVerifierPort`,
   `PlaybackAckBusPort`.
3. Module này liên kết với các thành phần nào?
   Tái sử dụng các kiểu kiểm định từ `p06.schemas`; được triển khai bởi `p05_knowledge_adapter.py`
   và `adapters/mocks/playback_bus.py`; được tiêu thụ bởi `guardrails/` và `simulation/`.
4. Input và output chính là gì?
   Đầu vào/đầu ra là các bản chụp tri thức SKU, ứng viên `SpeechCandidate`, và kết quả xác nhận
   phát sóng `PlaybackAckResult` / `PlaybackApplyResult` tuân thủ `p06-mock-v0.1`.
5. Có những constraints hoặc invariants quan trọng nào?
   - Toàn bộ DTO đều dùng `ConfigDict(extra="forbid", frozen=True)`.
   - `auto_replay_permitted` luôn cố định là `False` (`StrictFalse`) để bảo đảm bất biến chống lặp mù (I-03/I-06).
   - `PlaybackAckResult` bắt buộc phân tách rạch ròi `COMPLETED` (phải có `event`) với `FAILED`/`UNKNOWN`
     (cấm có `event` và bắt buộc có `failure_reason`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
import copy
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from p06.schemas.candidate import (
    CandidateVerificationStatus,
    SkuVersionBinding,
    SpeechCandidate,
)
from p06.schemas.events import (
    PlaybackCompleted,
    PlaybackOutcomeStatus,
    StoryCheckpoint,
)
from p06.schemas.story import (
    NonBlankStr,
    OptionalNonBlankStr,
    StrictFalse,
    StrictNonNegInt,
    StrictPositiveInt,
    StrictPositivePriceVnd,
)

# Các khóa tối thiểu bắt buộc trong mỗi chunk bằng chứng xuất sang tầng sinh thoại P06.
_REQUIRED_CHUNK_KEYS: frozenset[str] = frozenset({"evidence_id", "section", "content"})


class SkuEvidenceView(BaseModel):
    """Ảnh chụp chỉ-đọc toàn bộ tri thức đã kiểm chứng và trạng thái điều kiện của một SKU.

    Lý do thiết kế: P06 chỉ được đọc bản chụp tri thức theo phiên bản từ P05/P09/P11 và dùng
    `to_version_binding()` để khóa chặt phiên bản chống lỗi TOCTOU, tuyệt đối không tự duyệt claim.

    Attributes:
        tenant_id: Mã tenant sở hữu SKU (cô lập R10).
        sku_id: Mã định danh SKU.
        sku_name: Tên sản phẩm chuẩn hóa từ `ProductFact`.
        price_vnd: Giá bán chính thức (VNĐ) theo `ProductFact`.
        weight_display: Khối lượng/dung tích hiển thị chuẩn.
        expiry_display: Hạn sử dụng chuẩn.
        origin: Xuất xứ sản phẩm.
        ingredients: Danh sách thành phần sản phẩm.
        storage_instructions: Hướng dẫn bảo quản.
        knowledge_version: Phiên bản `ProductFact` hiện hành tại kho tri thức P05.
        ocop_status: Trạng thái xác minh OCOP từ P09 (chỉ-đọc).
        ocop_version: Phiên bản trạng thái OCOP hiện hành.
        ocop_code: Mã chứng nhận OCOP (nếu có).
        food_safety_verified: Cờ xác nhận đạt điều kiện an toàn thực phẩm.
        rights_status: Trạng thái quyền tài sản/presenter từ P11 (chỉ-đọc).
        rights_version: Phiên bản trạng thái quyền hiện hành.
        approved_chunks: Tập hợp các đoạn bằng chứng `APPROVED` (`evidence_id`, `section`, `content`).
        allowed_claims: Tập hợp các claim được phép sử dụng cho SKU.
        prohibited_claims: Danh sách văn bản claim bị cấm để làm đầu vào cho guard phòng thủ theo lớp.
        is_eligible: `True` chỉ khi đồng thời đạt `APPROVED` fact, `OCOP VERIFIED`, ATTP và `RIGHTS ACTIVE`.
        ineligible_reasons: Lý do không đủ điều kiện (rỗng khi và chỉ khi `is_eligible=True`).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    tenant_id: NonBlankStr
    sku_id: NonBlankStr
    sku_name: NonBlankStr
    price_vnd: StrictPositivePriceVnd
    weight_display: NonBlankStr
    expiry_display: NonBlankStr
    origin: NonBlankStr
    ingredients: tuple[NonBlankStr, ...]
    storage_instructions: NonBlankStr
    knowledge_version: StrictPositiveInt
    ocop_status: NonBlankStr
    ocop_version: StrictPositiveInt
    ocop_code: OptionalNonBlankStr = None
    food_safety_verified: StrictBool
    rights_status: NonBlankStr
    rights_version: StrictPositiveInt
    approved_chunks: tuple[dict[str, str], ...] = ()
    allowed_claims: tuple[dict[str, Any], ...] = ()
    prohibited_claims: tuple[NonBlankStr, ...] = ()
    is_eligible: StrictBool
    ineligible_reasons: tuple[NonBlankStr, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def _deep_copy_nested_containers(cls, data: Any) -> Any:
        """Sao chép sâu các dict lồng trong `approved_chunks` và `allowed_claims` để chống đột biến ngoài."""
        if isinstance(data, cls):
            return copy.deepcopy(data.model_dump())
        if isinstance(data, Mapping):
            copied = dict(data)
            if "approved_chunks" in copied and copied["approved_chunks"] is not None:
                copied["approved_chunks"] = copy.deepcopy(copied["approved_chunks"])
            if "allowed_claims" in copied and copied["allowed_claims"] is not None:
                copied["allowed_claims"] = copy.deepcopy(copied["allowed_claims"])
            return copied
        return data

    @model_validator(mode="after")
    def validate_evidence_view_invariants(self) -> SkuEvidenceView:
        """Kiểm định tính nhất quán giữa `is_eligible` với `ineligible_reasons` và cấu trúc chunk.

        Returns:
            SkuEvidenceView: Bản chụp tri thức hợp lệ.

        Raises:
            ValueError: Nếu `is_eligible` mâu thuẫn với `ineligible_reasons` hoặc chunk thiếu khóa.
        """
        if self.is_eligible and self.ineligible_reasons:
            raise ValueError("SkuEvidenceView có is_eligible=True bắt buộc ineligible_reasons phải rỗng.")
        if not self.is_eligible and not self.ineligible_reasons:
            raise ValueError("SkuEvidenceView có is_eligible=False bắt buộc phải nêu ít nhất 1 ineligible_reasons.")

        for idx, chunk in enumerate(self.approved_chunks):
            missing = _REQUIRED_CHUNK_KEYS - set(chunk.keys())
            if missing:
                raise ValueError(
                    f"approved_chunks[{idx}] thiếu khóa bắt buộc: {sorted(missing)}."
                )
            for key in _REQUIRED_CHUNK_KEYS:
                if not isinstance(chunk[key], str) or not chunk[key].strip():
                    raise ValueError(
                        f"approved_chunks[{idx}]['{key}'] phải là chuỗi không rỗng."
                    )
        return self

    def to_version_binding(
        self,
        cited_evidence_ids: Sequence[str] = (),
        stated_price_vnd: Optional[int] = None,
        mentions_ocop: bool = False,
    ) -> SkuVersionBinding:
        """Tạo `SkuVersionBinding` khóa chặt các số phiên bản hiện hành của SKU (chống TOCTOU).

        Args:
            cited_evidence_ids: Danh sách `evidence_id` mà lời thoại dự kiến trích dẫn.
            stated_price_vnd: Giá bán VNĐ nếu lời thoại có nhắc tới giá.
            mentions_ocop: Cờ đánh dấu lời thoại có đề cập chứng nhận OCOP hay không.

        Returns:
            SkuVersionBinding: Ràng buộc phiên bản sẵn sàng gắn vào `SpeechCandidate`.
        """
        return SkuVersionBinding(
            sku_id=self.sku_id,
            knowledge_version=self.knowledge_version,
            ocop_version=self.ocop_version,
            rights_version=self.rights_version,
            cited_evidence_ids=list(cited_evidence_ids),
            stated_price_vnd=stated_price_vnd,
            mentions_ocop=mentions_ocop,
        )


class CandidateVerificationResult(BaseModel):
    """Kết quả kiểm định một `SpeechCandidate` qua Cổng phát ngôn (`KnowledgeVerifierPort`).

    Attributes:
        status: Trạng thái sau kiểm định (`VERIFIED` hoặc `REJECTED`, cấm `DRAFT`).
        candidate: Bản sao `SpeechCandidate` đã cập nhật trạng thái tương ứng.
        reasons: Tập mã lý do từ chối khi `status == REJECTED`.
        details: Diễn giải chi tiết các bước kiểm tra phục vụ log/audit và bounded rewrite.
        gate_decision_id: Mã quyết định `ALLOW` khi `VERIFIED`, hoặc `None` khi `REJECTED`.
        per_sku_decisions: Chi tiết kết quả đánh giá theo từng `sku_id` (đặc biệt cho `MULTI_SKU_COMPARE`).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    status: CandidateVerificationStatus
    candidate: SpeechCandidate
    reasons: tuple[NonBlankStr, ...] = ()
    details: tuple[NonBlankStr, ...] = ()
    gate_decision_id: OptionalNonBlankStr = None
    per_sku_decisions: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _deep_copy_per_sku_decisions(cls, data: Any) -> Any:
        """Sao chép sâu `per_sku_decisions` để đột biến từ caller không làm thay đổi DTO bất biến."""
        if isinstance(data, cls):
            return copy.deepcopy(data.model_dump())
        if isinstance(data, Mapping):
            copied = dict(data)
            if "per_sku_decisions" in copied and copied["per_sku_decisions"] is not None:
                copied["per_sku_decisions"] = copy.deepcopy(copied["per_sku_decisions"])
            return copied
        return data

    @model_validator(mode="after")
    def validate_verification_result(self) -> CandidateVerificationResult:
        """Bảo đảm tính nhất quán giữa `status`, `candidate`, `reasons` và `gate_decision_id`.

        Returns:
            CandidateVerificationResult: Kết quả kiểm định hợp lệ.

        Raises:
            ValueError: Nếu trạng thái là `DRAFT` hoặc mâu thuẫn với trạng thái trên `candidate`.
        """
        if self.status == CandidateVerificationStatus.DRAFT:
            raise ValueError("CandidateVerificationResult không được mang trạng thái DRAFT.")
        if self.candidate.verification_status != self.status:
            raise ValueError(
                f"Trạng thái candidate ({self.candidate.verification_status.value}) không khớp "
                f"status của kết quả ({self.status.value})."
            )
        if self.status == CandidateVerificationStatus.VERIFIED:
            if self.reasons:
                raise ValueError("Kết quả VERIFIED không được chứa reasons từ chối.")
            if self.gate_decision_id is None:
                raise ValueError("Kết quả VERIFIED bắt buộc phải có gate_decision_id.")
        elif self.status == CandidateVerificationStatus.REJECTED:
            if not self.reasons:
                raise ValueError("Kết quả REJECTED bắt buộc phải có ít nhất 1 reasons.")
            if self.gate_decision_id is not None:
                raise ValueError("Kết quả REJECTED không được chứa gate_decision_id.")
        return self


class PlaybackAckResult(BaseModel):
    """Kết quả trả về từ bus phát sóng (`PlaybackAckBusPort`) cho một lượt đã gửi phát.

    Lý do thiết kế: Phân tách rạch ròi `COMPLETED` (có bằng chứng `PlaybackCompleted`) khỏi
    `FAILED`/`UNKNOWN` (không có sự kiện, buộc giữ nguyên checkpoint và `auto_replay_permitted=False`).

    Attributes:
        outcome: Kết quả phát sóng (`COMPLETED`, `FAILED`, hoặc `UNKNOWN`).
        event: Sự kiện `PlaybackCompleted` hợp lệ (chỉ có khi `outcome == COMPLETED`).
        turn_id: Mã lượt nói tương ứng.
        candidate_id: Mã `SpeechCandidate` đã gửi phát.
        plan_revision: Phiên bản `StoryPlan` được đính kèm lúc gửi phát (dùng đối chiếu stale ACK).
        auto_replay_permitted: Luôn cố định là `False` để ngăn phát lặp mù sau lỗi/timeout.
        failure_reason: Mô tả lỗi hoặc lý do mất tín hiệu (bắt buộc khi `FAILED`/`UNKNOWN`).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    outcome: PlaybackOutcomeStatus
    event: Optional[PlaybackCompleted] = None
    turn_id: NonBlankStr
    candidate_id: NonBlankStr
    plan_revision: Optional[StrictPositiveInt] = None
    auto_replay_permitted: StrictFalse = False
    failure_reason: OptionalNonBlankStr = None

    @model_validator(mode="after")
    def validate_outcome_consistency(self) -> PlaybackAckResult:
        """Thực thi nguyên tắc ACK nghiêm ngặt: chỉ `COMPLETED` mới mang `PlaybackCompleted`.

        Returns:
            PlaybackAckResult: Kết quả ACK hợp lệ.

        Raises:
            ValueError: Nếu `COMPLETED` thiếu `event` / lệch ID, hoặc `FAILED`/`UNKNOWN`
                mang `event` hay thiếu `failure_reason`.
        """
        if self.outcome == PlaybackOutcomeStatus.COMPLETED:
            if self.event is None:
                raise ValueError("PlaybackAckResult với outcome=COMPLETED bắt buộc phải có event.")
            if self.failure_reason is not None:
                raise ValueError("PlaybackAckResult với outcome=COMPLETED không được có failure_reason.")
            if self.event.turn_id != self.turn_id or self.event.candidate_id != self.candidate_id:
                raise ValueError("turn_id hoặc candidate_id trong event không khớp với PlaybackAckResult.")
        else:
            if self.event is not None:
                raise ValueError(
                    f"PlaybackAckResult với outcome={self.outcome.value} tuyệt đối không được chứa event."
                )
            if self.failure_reason is None:
                raise ValueError(
                    f"PlaybackAckResult với outcome={self.outcome.value} bắt buộc phải có failure_reason."
                )
        return self


class AckApplyStatus(str, Enum):
    """Kết quả xử lý một ACK phát sóng khi đối chiếu vào harness/trạng thái phiên.

    Attributes:
        APPLIED: ACK hợp lệ và đã tịnh tiến checkpoint, lịch sử phát, độ phủ chủ đề.
        IGNORED_NON_COMPLETED: ACK có trạng thái `FAILED` hoặc `UNKNOWN` -> giữ nguyên tiến độ.
        REJECTED_DUPLICATE: Sự kiện hoặc `turn_id` đã được xử lý trước đó -> từ chối idempotent.
        REJECTED_STALE_OR_MISMATCH: Lệch `tenant_id`/`session_id`/`epoch`/`plan_revision`/`candidate`/`chunk`,
            chưa đăng ký chờ phát, hoặc thời gian ACK đi ngược chiều thời gian.
        REJECTED_INVALID_PROVENANCE: Nguồn gốc sự kiện không khớp harness mô phỏng kỳ vọng.
    """

    APPLIED = "APPLIED"
    IGNORED_NON_COMPLETED = "IGNORED_NON_COMPLETED"
    REJECTED_DUPLICATE = "REJECTED_DUPLICATE"
    REJECTED_STALE_OR_MISMATCH = "REJECTED_STALE_OR_MISMATCH"
    REJECTED_INVALID_PROVENANCE = "REJECTED_INVALID_PROVENANCE"


class PlaybackApplyResult(BaseModel):
    """Ảnh chụp kết quả sau khi áp dụng một ACK/sự kiện vào `SimulatedPlaybackHarness`.

    Attributes:
        status: Trạng thái xử lý ACK (`APPLIED` hoặc mã từ chối/bỏ qua cụ thể).
        applied: `True` khi và chỉ khi `status == AckApplyStatus.APPLIED`.
        checkpoint: `StoryCheckpoint` hiện hành sau bước xử lý.
        completed_topic_ids: Tập các `topic_id` đã được xác nhận hoàn tất.
        played_history_count: Tổng số lượt phát thành công đã ghi nhận.
        auto_replay_permitted: Luôn cố định là `False`.
        reason: Lý do chi tiết nếu bị từ chối hoặc bỏ qua (`None` khi `APPLIED`).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    status: AckApplyStatus
    applied: StrictBool
    checkpoint: StoryCheckpoint
    completed_topic_ids: frozenset[str]
    played_history_count: StrictNonNegInt
    auto_replay_permitted: StrictFalse = False
    reason: OptionalNonBlankStr = None

    @model_validator(mode="after")
    def validate_apply_consistency(self) -> PlaybackApplyResult:
        """Bảo đảm `applied` khớp chính xác với `status == AckApplyStatus.APPLIED`.

        Returns:
            PlaybackApplyResult: Kết quả áp dụng hợp lệ.

        Raises:
            ValueError: Nếu `applied` mâu thuẫn với `status` hoặc thiếu lý do khi bị từ chối.
        """
        if self.status == AckApplyStatus.APPLIED:
            if not self.applied:
                raise ValueError("status=APPLIED yêu cầu applied=True.")
        else:
            if self.applied:
                raise ValueError(f"status={self.status.value} yêu cầu applied=False.")
            if self.reason is None:
                raise ValueError(f"status={self.status.value} bắt buộc phải có reason.")
        return self


class KnowledgeVerifierPort(ABC):
    """Cổng trừu tượng kết nối P06 tới bộ kiểm chứng tri thức và Cổng phát ngôn P05.

    Lý do kiến trúc: Áp dụng Dependency Inversion để P06 graph/guardrails chỉ phụ thuộc vào
    giao diện này, không gắn cứng vào cấu trúc nội bộ của `VersionedKnowledgeStore`.
    """

    @abstractmethod
    def get_sku_evidence(
        self,
        tenant_id: str,
        sku_id: str,
        at_time: Optional[datetime] = None,
    ) -> SkuEvidenceView:
        """Truy xuất bản chụp tri thức và trạng thái điều kiện của một SKU theo tenant.

        Args:
            tenant_id: Mã tenant yêu cầu truy xuất (bắt buộc kiểm tra cô lập).
            sku_id: Mã SKU cần lấy bằng chứng.
            at_time: Mốc thời gian kiểm tra cửa sổ hiệu lực (`valid_from..valid_until`, mặc định UTC hiện tại).

        Returns:
            SkuEvidenceView: Bản chụp thông tin, bằng chứng đã duyệt và cờ `is_eligible`.

        Raises:
            KeyError: Nếu không tìm thấy SKU trong kho tri thức (fail-closed).
            PermissionError: Nếu SKU thuộc tenant khác (ngăn rò rỉ dữ liệu chéo tenant).
        """

    @abstractmethod
    def verify_candidate(
        self,
        candidate: SpeechCandidate,
        verified_at: Optional[datetime] = None,
    ) -> CandidateVerificationResult:
        """Kiểm định một `SpeechCandidate` theo `TargetScopeMode` và trạng thái tri thức hiện hành.

        Args:
            candidate: Ứng viên lời thoại cần kiểm định.
            verified_at: Dấu thời gian kiểm định tùy chọn (hữu ích cho test tất định với VirtualClock).

        Returns:
            CandidateVerificationResult: Kết quả `VERIFIED` hoặc `REJECTED` kèm lý do và chi tiết.
        """


class PlaybackAckBusPort(ABC):
    """Cổng trừu tượng mô phỏng/kết nối tới hạ tầng phát sóng P04 để nhận ACK xác nhận phát."""

    @abstractmethod
    def dispatch_turn(
        self,
        candidate: SpeechCandidate,
        turn_id: str,
        plan_revision: int,
        outcome_override: Optional[PlaybackOutcomeStatus] = None,
        failure_reason: Optional[str] = None,
    ) -> PlaybackAckResult:
        """Gửi một ứng viên đã `VERIFIED` xuống tuyến phát sóng và nhận `PlaybackAckResult`.

        Args:
            candidate: Ứng viên lời thoại bắt buộc đã đạt `VERIFIED`.
            turn_id: Mã lượt phát sóng do bộ điều phối cấp.
            plan_revision: Phiên bản `StoryPlan` gắn với lượt phát.
            outcome_override: Kết quả cưỡng bức phục vụ kịch bản kiểm thử (nếu có).
            failure_reason: Lý do lỗi tường minh khi giả lập `FAILED` hoặc `UNKNOWN`.

        Returns:
            PlaybackAckResult: Kết quả ACK (chỉ mang `PlaybackCompleted` khi `COMPLETED`).
        """
