"""Hợp đồng dữ liệu Pydantic v2 cho ứng viên lời thoại (`SpeechCandidate`) và kiểm chứng P05.

1. File này giải quyết vấn đề gì?
   Mô hình hóa đầy đủ ứng viên phát ngôn do P06 tạo ra trước khi gửi qua Cổng phát ngôn P05
   (`PublicationGate`) và sau khi nhận phán quyết `VERIFIED`/`REJECTED`, đồng thời tách biệt rõ ràng
   4 chế độ phạm vi SKU (`TargetScopeMode`) và phần đề xuất độ phủ (`ProposedResponseCoverage`).
2. Trách nhiệm chính của module là gì?
   Cung cấp các Enum phân loại phạm vi, lý do chưa phân giải SKU, chế độ độ phủ, nguồn gốc ứng viên,
   trạng thái kiểm chứng, cùng các model `SkuVersionBinding`, `ProposedResponseCoverage` và `SpeechCandidate`
   với validator liên trường nghiêm ngặt.
3. Module này liên kết với các thành phần nào?
   Liên kết với `story.py` (dùng chung `CONTRACT_VERSION`, `MAX_CHUNK_DURATION_SEC`), `state.py`
   (lưu `draft_candidate` và `verified_candidate`), `guardrails/` (adapter gọi P05 `PublicationGate`),
   và P07/P08 (qua `ProposedResponseCoverage` và `sku_bindings`).
4. Input và output chính là gì?
   Input là bản nháp lời thoại + metadata gắn phiên bản từ P05/P07/P09/P11;
   Output là `SpeechCandidate` hợp lệ về mặt cấu trúc cho trạng thái `DRAFT`, `VERIFIED` hoặc `REJECTED`.
5. Có những constraints hoặc invariants quan trọng nào?
   - `ProposedResponseCoverage.is_authoritative` luôn là `False`: P06 chỉ ĐỀ XUẤT, P08/P04 mới chốt sau ACK.
   - Tách biệt nghiêm ngặt `UNRESOLVED_SKU` khỏi `SHOP_WIDE_POLICY` (P06-OPEN-5).
   - Bất biến vòng đời kiểm chứng: chỉ `VERIFIED` mới được phát sang TTS (`is_ready_for_tts()`), và
     ứng viên `VERIFIED` thuộc phạm vi SKU bắt buộc có bằng chứng hoặc giá khai báo rõ ràng.
"""

from __future__ import annotations

import copy
from collections.abc import Sequence
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from p06.schemas.story import (
    CONTRACT_VERSION,
    ContractVersion,
    NonBlankStr,
    OptionalNonBlankStr,
    StrictDurationSec,
    StrictFalse,
    StrictNonNegInt,
    StrictPositiveDurationMs,
    StrictPositiveInt,
    StrictPositivePriceVnd,
)


class TargetScopeMode(str, Enum):
    """Chế độ phạm vi sản phẩm của lời thoại để tránh nhầm lẫn ngữ cảnh SKU (P06-OPEN-5).

    Attributes:
        SINGLE_SKU: Lời thoại nói về đúng 1 SKU cụ thể.
        MULTI_SKU_COMPARE: Lời thoại so sánh từ 2 SKU trở lên cùng phiên.
        SHOP_WIDE_POLICY: Lời thoại về chính sách chung của shop (vận chuyển, đổi trả), không gắn SKU cụ thể.
        UNRESOLVED_SKU: Chưa xác định được SKU từ câu hỏi/bình luận (tách biệt hẳn khỏi `SHOP_WIDE_POLICY`).
    """

    SINGLE_SKU = "SINGLE_SKU"
    MULTI_SKU_COMPARE = "MULTI_SKU_COMPARE"
    SHOP_WIDE_POLICY = "SHOP_WIDE_POLICY"
    UNRESOLVED_SKU = "UNRESOLVED_SKU"


class UnresolvedSkuReason(str, Enum):
    """Lý do khiến bộ phân giải P07/P06 chưa xác định được SKU mục tiêu.

    Attributes:
        AMBIGUOUS_SKU: Bình luận khớp nhiều SKU cùng lúc nhưng chưa rõ sản phẩm nào.
        OUT_OF_CATALOG: Khách hỏi sản phẩm không nằm trong danh mục được ghim/hỗ trợ.
        MISSING_CONTEXT: Câu hỏi quá mơ hồ, thiếu ngữ cảnh để suy ra SKU.
    """

    AMBIGUOUS_SKU = "AMBIGUOUS_SKU"
    OUT_OF_CATALOG = "OUT_OF_CATALOG"
    MISSING_CONTEXT = "MISSING_CONTEXT"


class CoverageMode(str, Enum):
    """Mức độ bao phủ ý định/chủ đề mà ứng viên lời thoại đề xuất giải quyết.

    Attributes:
        FULL: Giải quyết trọn vẹn tất cả `intents` đã nhắm tới (`uncovered_intents` rỗng).
        PARTIAL: Chỉ trả lời được một phần, còn ý định chưa phủ do thiếu bằng chứng hoặc bị chặn.
        CLARIFICATION_ONLY: Chỉ hỏi lại làm rõ khi chưa phân giải được SKU, không đánh dấu phủ topic nào.
        ABSTAIN_NO_EVIDENCE: Từ chối trả lời an toàn (abstain) do thiếu bằng chứng hoặc vi phạm cổng P05.
    """

    FULL = "FULL"
    PARTIAL = "PARTIAL"
    CLARIFICATION_ONLY = "CLARIFICATION_ONLY"
    ABSTAIN_NO_EVIDENCE = "ABSTAIN_NO_EVIDENCE"


class CandidateOrigin(str, Enum):
    """Nguồn gốc sinh ra ứng viên lời thoại trong chu trình điều phối P06.

    Attributes:
        PROACTIVE_STORY: Sinh chủ động từ một `StoryChunk` của `StoryPlan` khi không có comment chen ngang.
        COMMENT_REPLY: Sinh ra để trả lời bình luận của người xem đã được P07 phân loại.
        RESUME_BRIDGE: Câu chuyển tiếp nối lại mạch kể chuyện sau khi trả lời comment (I-06).
        PREAPPROVED_FALLBACK: Câu dự phòng đã phê duyệt trước dùng khi vượt quá `rewrite_budget` (P06-E04).
    """

    PROACTIVE_STORY = "PROACTIVE_STORY"
    COMMENT_REPLY = "COMMENT_REPLY"
    RESUME_BRIDGE = "RESUME_BRIDGE"
    PREAPPROVED_FALLBACK = "PREAPPROVED_FALLBACK"


class CandidateVerificationStatus(str, Enum):
    """Trạng thái kiểm duyệt của ứng viên lời thoại đối với Cổng phát ngôn P05.

    Attributes:
        DRAFT: Bản nháp mới sinh từ LLM/planner, chưa qua kiểm định P05 (tuyệt đối không phát TTS).
        VERIFIED: Đã vượt qua Cổng phát ngôn P05 với `gate_decision_id` và dấu thời gian hợp lệ.
        REJECTED: Bị Cổng phát ngôn P05 từ chối kèm ít nhất một lý do để phục vụ bounded rewrite.
    """

    DRAFT = "DRAFT"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class SkuVersionBinding(BaseModel):
    """Ràng buộc phiên bản dữ liệu đa nguồn gắn chặt theo từng SKU nhằm chống lỗi TOCTOU (Hard Gate G3).

    Attributes:
        sku_id: Mã SKU được đề cập trong lời thoại.
        product_version_id: Mã định danh phiên bản sản phẩm từ backend (nếu có).
        knowledge_version: Phiên bản `ProductFact`/`EvidenceChunk` tại P05 (>= 1).
        ocop_version: Phiên bản trạng thái OCOP từ P09 (>= 1).
        rights_version: Phiên bản trạng thái bản quyền từ P11 (>= 1).
        cited_evidence_ids: Danh sách `evidence_id` cụ thể thuộc SKU này mà lời thoại dẫn chứng.
        stated_price_vnd: Mức giá VNĐ (nếu lời thoại nhắc tới giá của SKU này).
        mentions_ocop: Cờ đánh dấu lời thoại có nhắc tới chứng nhận OCOP của SKU hay không.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    sku_id: NonBlankStr
    product_version_id: OptionalNonBlankStr = None
    knowledge_version: StrictPositiveInt
    ocop_version: StrictPositiveInt
    rights_version: StrictPositiveInt
    cited_evidence_ids: list[NonBlankStr] = Field(default_factory=list)
    stated_price_vnd: Optional[StrictPositivePriceVnd] = None
    mentions_ocop: StrictBool = False


class ProposedResponseCoverage(BaseModel):
    """Đề xuất phạm vi độ phủ chủ đề/comment do P06 đính kèm cho mỗi ứng viên lời thoại.

    Lưu ý kiến trúc: Trường `is_authoritative` luôn cố định là `False` vì P06 không có quyền
    chốt độ phủ; chỉ P08/P09 sau khi nhận `P04 PlaybackCompleted` mới xác nhận độ phủ chính thức.

    Attributes:
        response_group_id: Mã nhóm câu hỏi gom từ P07 (nếu ứng viên trả lời comment).
        covered_topic_ids: Danh sách `topic_id` trong `StoryPlan` dự kiến sẽ được phủ.
        covered_comment_ids: Danh sách `comment_id` dự kiến sẽ được giải đáp.
        covered_intents: Các ý định câu hỏi đã được giải quyết trong lời thoại.
        uncovered_intents: Các ý định chưa thể giải quyết (do thiếu dữ liệu hoặc bị gate chặn).
        coverage_mode: Chế độ độ phủ (`FULL`, `PARTIAL`, `CLARIFICATION_ONLY`, `ABSTAIN_NO_EVIDENCE`).
        is_authoritative: Luôn là `False`, khẳng định đây mới chỉ là đề xuất từ P06.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    response_group_id: OptionalNonBlankStr = None
    covered_topic_ids: list[NonBlankStr] = Field(default_factory=list)
    covered_comment_ids: list[NonBlankStr] = Field(default_factory=list)
    covered_intents: list[NonBlankStr] = Field(default_factory=list)
    uncovered_intents: list[NonBlankStr] = Field(default_factory=list)
    coverage_mode: CoverageMode = CoverageMode.FULL
    is_authoritative: StrictFalse = False

    @model_validator(mode="after")
    def validate_coverage_consistency(self) -> ProposedResponseCoverage:
        """Kiểm tra tính nhất quán giữa `coverage_mode` và các tập intent/topic đi kèm.

        Returns:
            ProposedResponseCoverage: Đối tượng độ phủ đề xuất hợp lệ.

        Raises:
            ValueError: Nếu cùng một intent vừa nằm trong `covered_intents` vừa nằm trong
                `uncovered_intents`, hoặc tập rỗng/không rỗng mâu thuẫn với `coverage_mode`.
        """
        overlap = set(self.covered_intents) & set(self.uncovered_intents)
        if overlap:
            raise ValueError(
                f"covered_intents và uncovered_intents không được giao nhau: {sorted(overlap)}."
            )

        if self.coverage_mode == CoverageMode.FULL and self.uncovered_intents:
            raise ValueError(
                "CoverageMode.FULL yêu cầu uncovered_intents phải rỗng."
            )

        if self.coverage_mode == CoverageMode.PARTIAL:
            if not self.uncovered_intents:
                raise ValueError(
                    "CoverageMode.PARTIAL yêu cầu uncovered_intents phải có ít nhất 1 phần tử."
                )
            if not self.covered_intents and not self.covered_topic_ids:
                raise ValueError(
                    "CoverageMode.PARTIAL yêu cầu phải có ít nhất 1 covered_intents hoặc covered_topic_ids."
                )

        if self.coverage_mode == CoverageMode.CLARIFICATION_ONLY and self.covered_topic_ids:
            raise ValueError(
                "CoverageMode.CLARIFICATION_ONLY không được đánh dấu covered_topic_ids."
            )

        if self.coverage_mode == CoverageMode.ABSTAIN_NO_EVIDENCE:
            if self.covered_topic_ids or self.covered_intents:
                raise ValueError(
                    "CoverageMode.ABSTAIN_NO_EVIDENCE không được đánh dấu covered_topic_ids hoặc covered_intents."
                )

        return self


class SpeechCandidate(BaseModel):
    """Ứng viên lời thoại đầu ra của P06, mang đầy đủ ngữ cảnh phiên bản và trạng thái kiểm chứng P05.

    Attributes:
        contract_version: Phiên bản hợp đồng dữ liệu (`p06-mock-v0.1`).
        candidate_id: Mã định danh duy nhất của ứng viên.
        turn_id: Mã lượt nói do P08 cấp (hoặc `None` ở giai đoạn nháp trước khi lập lịch).
        tenant_id: Mã tenant để kiểm tra cô lập đa khách hàng (R10).
        session_id: Mã phiên livestream.
        session_epoch: Thế hệ phiên tăng dần khi reconnect/reset nhằm chống stale state.
        origin: Nguồn gốc sinh ứng viên (`PROACTIVE_STORY`, `COMMENT_REPLY`, ...).
        source_chunk_id: Mã `StoryChunk` nguồn (bắt buộc khi `origin == PROACTIVE_STORY`).
        scope_mode: Phạm vi SKU của lời thoại (`SINGLE_SKU`, `MULTI_SKU_COMPARE`, `SHOP_WIDE_POLICY`, `UNRESOLVED_SKU`).
        sku_refs: Danh sách `sku_id` liên quan theo đúng thứ tự với `sku_bindings`.
        sku_bindings: Danh sách `SkuVersionBinding` khóa phiên bản tri thức/OCOP/quyền theo từng SKU.
        unresolved_reason: Lý do chưa phân giải được SKU (chỉ có khi `scope_mode == UNRESOLVED_SKU`).
        policy_evidence_ids: Danh sách bằng chứng chính sách chung của shop (khi `SHOP_WIDE_POLICY`).
        policy_version: Phiên bản chính sách shop (bắt buộc khi `SHOP_WIDE_POLICY`).
        session_rights_version: Phiên bản quyền sử dụng presenter/asset cấp phiên (>= 1).
        intent: Ý định giao tiếp chính của ứng viên lời thoại.
        text: Nội dung lời thoại tiếng Việt (tự động strip, cấm rỗng).
        safe_summary: Tóm tắt an toàn dùng cho log/trace không chứa dữ liệu nhạy cảm.
        semantic_breakpoint: Đánh dấu ứng viên kết thúc ở điểm ngắt ngữ nghĩa sạch.
        estimated_duration_sec: Thời lượng đọc ước lượng trong `(0, MAX_CHUNK_DURATION_SEC]`.
        deadline_ms: Ngưỡng thời hạn trễ (ms) nếu là trả lời comment theo SLA `W1`.
        proposed_coverage: Đề xuất độ phủ (luôn `is_authoritative=False`).
        verification_status: Trạng thái kiểm định đối với Cổng phát ngôn P05.
        verified_by_gate_decision_id: Mã quyết định `ALLOW` do P05 cấp (chỉ có khi `VERIFIED`).
        verified_at: Thời điểm P05 cấp quyết định `ALLOW` (chỉ có khi `VERIFIED`).
        rejection_reasons: Danh sách mã/lý do chặn từ P05 (bắt buộc >= 1 khi `REJECTED`).
        rewrite_attempt: Số lần ứng viên đã trải qua vòng viết lại (0 là lần sinh đầu).
        created_at: Thời điểm tạo ứng viên (UTC).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    contract_version: ContractVersion = CONTRACT_VERSION
    candidate_id: NonBlankStr
    turn_id: OptionalNonBlankStr = None
    tenant_id: NonBlankStr
    session_id: NonBlankStr
    session_epoch: StrictPositiveInt
    origin: CandidateOrigin
    source_chunk_id: OptionalNonBlankStr = None
    scope_mode: TargetScopeMode
    sku_refs: list[NonBlankStr] = Field(default_factory=list)
    sku_bindings: list[SkuVersionBinding] = Field(default_factory=list)
    unresolved_reason: Optional[UnresolvedSkuReason] = None
    policy_evidence_ids: list[NonBlankStr] = Field(default_factory=list)
    policy_version: Optional[StrictPositiveInt] = None
    session_rights_version: StrictPositiveInt
    intent: NonBlankStr
    text: NonBlankStr
    safe_summary: OptionalNonBlankStr = None
    semantic_breakpoint: StrictBool = True
    estimated_duration_sec: StrictDurationSec
    deadline_ms: Optional[StrictPositiveDurationMs] = None
    proposed_coverage: ProposedResponseCoverage
    verification_status: CandidateVerificationStatus = CandidateVerificationStatus.DRAFT
    verified_by_gate_decision_id: OptionalNonBlankStr = None
    verified_at: Optional[datetime] = None
    rejection_reasons: list[NonBlankStr] = Field(default_factory=list)
    rewrite_attempt: StrictNonNegInt = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_scope_and_verification_invariants(self) -> SpeechCandidate:
        """Kiểm định đồng thời hai nhóm bất biến: phạm vi `scope_mode` và vòng đời `verification_status`.

        Returns:
            SpeechCandidate: Ứng viên hợp lệ về mọi ràng buộc liên trường.

        Raises:
            ValueError: Nếu cấu hình `sku_refs`/`sku_bindings`/`policy_*`/`unresolved_reason`
                không khớp `scope_mode`, nếu thiếu `source_chunk_id` cho `PROACTIVE_STORY`, hoặc nếu
                thông tin kiểm chứng mâu thuẫn với `verification_status`.
        """
        # 1. Ràng buộc nguồn gốc PROACTIVE_STORY: phải truy vết ngược về StoryChunk đã sinh.
        if self.origin == CandidateOrigin.PROACTIVE_STORY:
            if self.source_chunk_id is None or not self.source_chunk_id.strip():
                raise ValueError(
                    "SpeechCandidate có origin=PROACTIVE_STORY bắt buộc phải có source_chunk_id không rỗng."
                )

        # 2. Ràng buộc nghiêm ngặt theo 4 TargetScopeMode (P06-OPEN-5).
        if self.scope_mode == TargetScopeMode.SINGLE_SKU:
            if len(self.sku_refs) != 1 or len(self.sku_bindings) != 1:
                raise ValueError(
                    "TargetScopeMode.SINGLE_SKU yêu cầu đúng 1 sku_refs và đúng 1 sku_bindings."
                )
            if self.sku_bindings[0].sku_id != self.sku_refs[0]:
                raise ValueError(
                    f"sku_bindings[0].sku_id='{self.sku_bindings[0].sku_id}' không khớp với "
                    f"sku_refs[0]='{self.sku_refs[0]}'."
                )
            if self.unresolved_reason is not None:
                raise ValueError("SINGLE_SKU không được phép đặt unresolved_reason.")
            if self.policy_evidence_ids:
                raise ValueError("SINGLE_SKU không được phép chứa policy_evidence_ids.")

        elif self.scope_mode == TargetScopeMode.MULTI_SKU_COMPARE:
            if len(self.sku_refs) < 2:
                raise ValueError("TargetScopeMode.MULTI_SKU_COMPARE yêu cầu ít nhất 2 sku_refs.")
            if len(set(self.sku_refs)) != len(self.sku_refs):
                raise ValueError("sku_refs trong MULTI_SKU_COMPARE không được chứa SKU trùng lặp.")
            binding_sku_ids = [binding.sku_id for binding in self.sku_bindings]
            if binding_sku_ids != self.sku_refs:
                raise ValueError(
                    f"Thứ tự sku_bindings ({binding_sku_ids}) phải khớp chính xác với sku_refs ({self.sku_refs})."
                )
            if self.unresolved_reason is not None:
                raise ValueError("MULTI_SKU_COMPARE không được phép đặt unresolved_reason.")
            if self.policy_evidence_ids:
                raise ValueError("MULTI_SKU_COMPARE không được phép chứa policy_evidence_ids.")

        elif self.scope_mode == TargetScopeMode.SHOP_WIDE_POLICY:
            if self.sku_refs or self.sku_bindings:
                raise ValueError("SHOP_WIDE_POLICY yêu cầu sku_refs và sku_bindings phải rỗng.")
            if self.unresolved_reason is not None:
                raise ValueError("SHOP_WIDE_POLICY không được phép đặt unresolved_reason.")
            if self.policy_version is None:
                raise ValueError("SHOP_WIDE_POLICY bắt buộc phải có policy_version.")
            if self.proposed_coverage.coverage_mode == CoverageMode.CLARIFICATION_ONLY:
                raise ValueError(
                    "SHOP_WIDE_POLICY không được dùng CoverageMode.CLARIFICATION_ONLY."
                )
            if (
                self.verification_status == CandidateVerificationStatus.VERIFIED
                and not self.policy_evidence_ids
            ):
                raise ValueError(
                    "Ứng viên SHOP_WIDE_POLICY ở trạng thái VERIFIED phải có ít nhất 1 policy_evidence_ids."
                )

        elif self.scope_mode == TargetScopeMode.UNRESOLVED_SKU:
            if self.sku_refs or self.sku_bindings:
                raise ValueError("UNRESOLVED_SKU yêu cầu sku_refs và sku_bindings phải rỗng.")
            if self.policy_evidence_ids or self.policy_version is not None:
                raise ValueError(
                    "UNRESOLVED_SKU phải tách biệt khỏi SHOP_WIDE_POLICY: policy_evidence_ids rỗng và policy_version=None."
                )
            if self.unresolved_reason is None:
                raise ValueError("UNRESOLVED_SKU bắt buộc phải chỉ rõ unresolved_reason.")
            if self.proposed_coverage.coverage_mode not in {
                CoverageMode.CLARIFICATION_ONLY,
                CoverageMode.ABSTAIN_NO_EVIDENCE,
            }:
                raise ValueError(
                    "UNRESOLVED_SKU chỉ được phép dùng CoverageMode.CLARIFICATION_ONLY hoặc ABSTAIN_NO_EVIDENCE."
                )
            if self.proposed_coverage.covered_topic_ids:
                raise ValueError("UNRESOLVED_SKU không được phép có covered_topic_ids.")

        # 3. Ràng buộc vòng đời kiểm chứng đối với Cổng P05 (tách biệt Generated != Verified).
        if self.verification_status == CandidateVerificationStatus.DRAFT:
            if self.verified_by_gate_decision_id is not None or self.verified_at is not None:
                raise ValueError(
                    "Ứng viên DRAFT không được chứa verified_by_gate_decision_id hoặc verified_at."
                )
            if self.rejection_reasons:
                raise ValueError("Ứng viên DRAFT không được chứa rejection_reasons.")

        elif self.verification_status == CandidateVerificationStatus.VERIFIED:
            if (
                self.verified_by_gate_decision_id is None
                or not self.verified_by_gate_decision_id.strip()
            ):
                raise ValueError(
                    "Ứng viên VERIFIED bắt buộc phải có verified_by_gate_decision_id không rỗng."
                )
            if self.verified_at is None:
                raise ValueError("Ứng viên VERIFIED bắt buộc phải có verified_at.")
            if self.rejection_reasons:
                raise ValueError("Ứng viên VERIFIED không được chứa rejection_reasons.")

            if self.scope_mode in {TargetScopeMode.SINGLE_SKU, TargetScopeMode.MULTI_SKU_COMPARE}:
                for binding in self.sku_bindings:
                    if not binding.cited_evidence_ids and binding.stated_price_vnd is None:
                        raise ValueError(
                            f"SkuVersionBinding của '{binding.sku_id}' khi VERIFIED phải có ít nhất "
                            "1 cited_evidence_ids hoặc stated_price_vnd."
                        )

        elif self.verification_status == CandidateVerificationStatus.REJECTED:
            if not self.rejection_reasons:
                raise ValueError("Ứng viên REJECTED bắt buộc phải có ít nhất 1 rejection_reasons.")
            if self.verified_by_gate_decision_id is not None or self.verified_at is not None:
                raise ValueError(
                    "Ứng viên REJECTED không được chứa verified_by_gate_decision_id hoặc verified_at."
                )

        return self

    def mark_verified(self, gate_decision_id: str, verified_at: datetime) -> SpeechCandidate:
        """Tạo bản sao `SpeechCandidate` mới ở trạng thái `VERIFIED` một cách nguyên tử.

        Lý do kỹ thuật: Vì mọi schema dùng `frozen=True`, phương thức này sao chép sâu payload
        và chạy `model_validate()` để bảo đảm bản gốc không bao giờ bị biến đổi nửa vời nếu lỗi.
        Chỉ cho phép chuyển từ `DRAFT` sang `VERIFIED` để tránh đóng dấu lại ứng viên đã chốt.

        Args:
            gate_decision_id: Mã quyết định `ALLOW` do Cổng phát ngôn P05 cấp.
            verified_at: Thời điểm P05 cấp phán quyết hợp lệ.

        Returns:
            SpeechCandidate: Ứng viên mới ở trạng thái `VERIFIED` đủ điều kiện phát TTS.

        Raises:
            ValueError: Nếu `self.verification_status != CandidateVerificationStatus.DRAFT`.
            ValidationError: Nếu `gate_decision_id` rỗng, thiếu bằng chứng, hoặc ứng viên
                đang mang `rejection_reasons`.
        """
        if self.verification_status != CandidateVerificationStatus.DRAFT:
            raise ValueError(
                f"Chỉ có thể mark_verified từ trạng thái DRAFT, hiện tại là "
                f"'{self.verification_status.value}'."
            )
        payload = copy.deepcopy(self.model_dump())
        payload["verification_status"] = CandidateVerificationStatus.VERIFIED
        payload["verified_by_gate_decision_id"] = gate_decision_id
        payload["verified_at"] = verified_at
        return type(self).model_validate(payload)

    def mark_rejected(
        self,
        reasons: Sequence[str],
        increment_rewrite: bool = False,
    ) -> SpeechCandidate:
        """Tạo bản sao `SpeechCandidate` mới ở trạng thái `REJECTED` kèm lý do từ P05.

        Chỉ cho phép chuyển từ `DRAFT` sang `REJECTED` để không hạ cấp hoặc ghi đè ứng viên
        đã kiểm chứng/từ chối trước đó (`[B-MAJ-01]`).

        Args:
            reasons: Danh sách mã/lý do chặn từ P05 (bắt buộc ít nhất 1 chuỗi không rỗng).
            increment_rewrite: Nếu `True`, tăng `rewrite_attempt` thêm 1 cho vòng bounded rewrite.

        Returns:
            SpeechCandidate: Ứng viên mới ở trạng thái `REJECTED` đã xóa dấu vết `VERIFIED`.

        Raises:
            ValueError: Nếu `self.verification_status != CandidateVerificationStatus.DRAFT`.
            ValidationError: Nếu `reasons` rỗng hoặc chứa phần tử chỉ gồm khoảng trắng.
        """
        if self.verification_status != CandidateVerificationStatus.DRAFT:
            raise ValueError(
                f"Chỉ có thể mark_rejected từ trạng thái DRAFT, hiện tại là "
                f"'{self.verification_status.value}'."
            )
        payload = copy.deepcopy(self.model_dump())
        payload["verification_status"] = CandidateVerificationStatus.REJECTED
        payload["verified_by_gate_decision_id"] = None
        payload["verified_at"] = None
        payload["rejection_reasons"] = list(reasons)
        if increment_rewrite:
            payload["rewrite_attempt"] = self.rewrite_attempt + 1
        return type(self).model_validate(payload)

    def is_ready_for_tts(self) -> bool:
        """Kiểm tra ứng viên đã đạt kiểm định P05 để chuyển sang tổng hợp giọng nói (P02) hay chưa.

        Returns:
            bool: `True` chỉ khi `verification_status == CandidateVerificationStatus.VERIFIED`.
        """
        return self.verification_status == CandidateVerificationStatus.VERIFIED
