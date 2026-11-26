"""Hợp đồng dữ liệu Pydantic v2 cho kế hoạch kể chuyện (StoryPlan, StoryArc, StoryTopic, StoryChunk).

1. File này giải quyết vấn đề gì?
   Định nghĩa cấu trúc dữ liệu phân cấp từ kế hoạch phiên live (`StoryPlan`) tới từng đoạn thoại
   dự kiến (`StoryChunk`), giúp tách biệt khung nội dung đã được merchant duyệt khỏi lời thoại sinh động
   theo thời gian thực của LLM.
2. Trách nhiệm chính của module là gì?
   Cung cấp các Enum trạng thái duyệt kế hoạch, vai trò đoạn thoại, điểm ngắt ngữ nghĩa và các mô hình
   Pydantic v2 kèm validator bảo toàn cấu trúc, ràng buộc SKU được ghim (`pinned_sku_ids`) và dấu vết phê duyệt.
3. Module này liên kết với các thành phần nào?
   Liên kết trực tiếp với `candidate.py`, `events.py`, `state.py` trong `p06.schemas`, cũng như
   `planning/` (StoryPlanner), `agent/nodes/` (LangGraph nodes), và bảng kiểm soát phiên P08/P10.
4. Input và output chính là gì?
   Input là dữ liệu JSON/dict khởi tạo kế hoạch từ merchant goal hoặc bản nháp chunk từ generator;
   Output là các đối tượng Pydantic đã kiểm định bất biến (`StoryPlan`, `StoryChunk`) và JSON tuần tự hóa chuẩn `p06-mock-v0.1`.
5. Có những constraints hoặc invariants quan trọng nào?
   - `StoryPlan` chỉ hợp lệ ở trạng thái `APPROVED` khi có đủ `approved_by` và `approved_at` (Gate G6).
   - `pinned_sku_ids` giới hạn 1–5 SKU (`MIN_PINNED_SKUS..MAX_PINNED_SKUS`), không trùng lặp hoặc rỗng (`ACR-002`).
   - Vị trí `StoryArc` phải liên tục `1..len(arcs)`, `arc_id` và `topic_id` duy nhất toàn kế hoạch.
   - `StoryChunk` bắt buộc không rỗng sau khi strip và thời lượng ước lượng nằm trong `(0, MAX_CHUNK_DURATION_SEC]`.
"""

from __future__ import annotations

import copy
import math
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, Final, Literal, Optional

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)

# Phiên bản hợp đồng mock cho giai đoạn PoC Stage 03 trước khi đóng băng packages/contracts/ (P06-OPEN-5).
CONTRACT_VERSION: Final[str] = "p06-mock-v0.1"
ContractVersion = Literal["p06-mock-v0.1"]

# Giới hạn số lượng SKU ghim trong một phiên: tối thiểu 1 cho unit test W0 và tối đa 5 theo ACR-002.
MIN_PINNED_SKUS: Final[int] = 1
MAX_PINNED_SKUS: Final[int] = 5

# Chặn độ dài ước lượng một chunk <= 30s để giữ nhịp live tự nhiên và đảm bảo điểm ngắt khi có comment.
MAX_CHUNK_DURATION_SEC: Final[float] = 30.0

# Chặn thời lượng mục tiêu một StoryArc <= 3600s (1 giờ) nhằm tránh cấu hình bất thường ở cấp PoC.
MAX_ARC_DURATION_SEC: Final[int] = 3600


def _validate_optional_non_blank_str(value: Any) -> Optional[str]:
    """Kiểm định chuỗi tùy chọn: giữ nguyên `None`, cắt khoảng trắng và cấm chuỗi rỗng.

    Args:
        value: Giá trị đầu vào cho trường chuỗi tùy chọn.

    Returns:
        Optional[str]: `None` hoặc chuỗi đã `strip()` khác rỗng.

    Raises:
        ValueError: Nếu giá trị không phải `str`/`None` hoặc sau khi `strip()` bị rỗng.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(
            f"Giá trị chuỗi tùy chọn phải là str hoặc None, nhận được {type(value).__name__}."
        )
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Chuỗi tùy chọn không được rỗng hoặc chỉ chứa khoảng trắng.")
    return cleaned


def _validate_strict_duration_sec(value: Any) -> float:
    """Kiểm định thời lượng giây nghiêm ngặt: chỉ nhận `int`/`float` hữu hạn, từ chối `bool` và `str`.

    Lý do kỹ thuật: Trong Python, `bool` là lớp con của `int` nên `isinstance(True, int)` là `True`;
    cần chặn tường minh để tránh `True` bị ép kiểu thành `1.0` giây.

    Args:
        value: Giá trị thời lượng đầu vào.

    Returns:
        float: Giá trị thời lượng dạng số thực hữu hạn.

    Raises:
        ValueError: Nếu giá trị là `bool`, không phải `int`/`float`, hoặc không hữu hạn (`nan`/`inf`).
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"Thời lượng (giây) phải là int hoặc float thuần túy, nhận được {type(value).__name__}."
        )
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError("Thời lượng (giây) phải là số hữu hạn.")
    return numeric


def _validate_strict_false(value: Any) -> Literal[False]:
    """Bảo đảm giá trị là boolean `False` thuần túy, từ chối `0`, `'false'` và `True`.

    Lý do kỹ thuật: Pydantic `Literal[False]` mặc định có thể ép kiểu `0` thành `False`
    ở chế độ non-strict; validator này khóa chặt mọi ép kiểu ngầm cho cờ thẩm quyền.

    Args:
        value: Giá trị đầu vào cho cờ thẩm quyền luôn phải là `False`.

    Returns:
        Literal[False]: Giá trị `False` hợp lệ.

    Raises:
        ValueError: Nếu `value is not False`.
    """
    if value is not False:
        raise ValueError("Cờ thẩm quyền bắt buộc phải là boolean False thuần túy.")
    return False


# Các kiểu dữ liệu nghiêm ngặt dùng chung toàn module P06 (ngăn ép kiểu ngầm và chuỗi toàn khoảng trắng).
NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
OptionalNonBlankStr = Annotated[Optional[str], BeforeValidator(_validate_optional_non_blank_str)]
StrictPositiveInt = Annotated[StrictInt, Field(ge=1)]
StrictNonNegInt = Annotated[StrictInt, Field(ge=0)]
StrictPositivePriceVnd = Annotated[StrictInt, Field(gt=0)]
StrictPositiveDurationMs = Annotated[StrictInt, Field(gt=0)]
StrictDurationSec = Annotated[
    float,
    BeforeValidator(_validate_strict_duration_sec),
    Field(gt=0.0, le=MAX_CHUNK_DURATION_SEC),
]
StrictArcDurationSec = Annotated[StrictInt, Field(gt=0, le=MAX_ARC_DURATION_SEC)]
StrictFalse = Annotated[Literal[False], BeforeValidator(_validate_strict_false)]


class StoryPlanApprovalStatus(str, Enum):
    """Trạng thái phê duyệt vòng đời của một StoryPlan trước và trong phiên live.

    Attributes:
        DRAFT: Bản nháp mới lập, chưa trình merchant kiểm duyệt.
        REVIEW_REQUIRED: Đang chờ merchant/Owner rà soát trước khi phát sóng.
        APPROVED: Đã được merchant/Owner phê duyệt hợp lệ, đủ điều kiện dùng trong phiên.
        INVALIDATED: Bị vô hiệu hóa do dữ liệu tri thức, OCOP hoặc quyền liên quan thay đổi.
        SUPERSEDED: Đã bị thay thế bởi một `plan_revision` mới hơn.
    """

    DRAFT = "DRAFT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    INVALIDATED = "INVALIDATED"
    SUPERSEDED = "SUPERSEDED"


class StoryChunkRole(str, Enum):
    """Vai trò ngữ dụng của một `StoryChunk` trong dòng chảy kể chuyện bán hàng.

    Attributes:
        OPENING: Lời chào mở đầu phiên hoặc mở đầu một arc sản phẩm mới.
        PRODUCT_STORY: Kể câu chuyện nguồn gốc, quy trình, điểm khác biệt của sản phẩm.
        FACT_HIGHLIGHT: Nhấn mạnh thông số cốt lõi (giá, khối lượng, hướng dẫn sử dụng) có dẫn chứng.
        CTA_SOFT: Kêu gọi tương tác nhẹ nhàng hoặc nhắc xem giỏ hàng, tránh ép mua phản cảm.
        TRANSITION_BRIDGE: Câu chuyển tiếp mượt mà sau khi trả lời comment quay lại mạch kể (I-06).
    """

    OPENING = "OPENING"
    PRODUCT_STORY = "PRODUCT_STORY"
    FACT_HIGHLIGHT = "FACT_HIGHLIGHT"
    CTA_SOFT = "CTA_SOFT"
    TRANSITION_BRIDGE = "TRANSITION_BRIDGE"


class BreakpointType(str, Enum):
    """Loại điểm ngắt ngữ nghĩa dùng để tạm dừng hoặc chuyển mạch an toàn khi có comment (G2).

    Attributes:
        SENTENCE_END: Điểm kết thúc một câu hoàn chỉnh trong cùng chủ đề.
        TOPIC_END: Điểm kết thúc một `StoryTopic`, thích hợp để xen câu trả lời rồi resume.
        ARC_BOUNDARY: Ranh giới chuyển sang `StoryArc` tiếp theo.
    """

    SENTENCE_END = "SENTENCE_END"
    TOPIC_END = "TOPIC_END"
    ARC_BOUNDARY = "ARC_BOUNDARY"


class StoryTopic(BaseModel):
    """Đơn vị chủ đề nhỏ nhất trong một `StoryArc`, gắn với các tham chiếu bằng chứng P05.

    Attributes:
        topic_id: Mã định danh duy nhất của chủ đề trong toàn `StoryPlan`.
        title: Tiêu đề ngắn gọn mô tả nội dung chủ đề.
        sku_id: Mã SKU gắn với chủ đề (hoặc `None` nếu là chủ đề mở đầu/chuyển chung).
        is_mandatory: Đánh dấu chủ đề bắt buộc phải phủ trong phiên để tracker theo dõi coverage.
        fact_refs: Danh sách `evidence_id` từ P05 mà chủ đề này được phép dựa vào.
        allowed_claim_ids: Danh sách `claim_id` đã duyệt trong Claim Registry của P05.
        talking_points: Các gạch đầu dòng gợi ý ý chính cho LLM khi sinh chunk.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    topic_id: NonBlankStr
    title: NonBlankStr
    sku_id: OptionalNonBlankStr = None
    is_mandatory: StrictBool = True
    fact_refs: list[NonBlankStr] = Field(default_factory=list)
    allowed_claim_ids: list[NonBlankStr] = Field(default_factory=list)
    talking_points: list[NonBlankStr] = Field(default_factory=list)


class StoryArc(BaseModel):
    """Một chương (arc) trong kịch bản kể chuyện, nhóm các `StoryTopic` theo thứ tự phát triển.

    Attributes:
        arc_id: Mã định danh duy nhất của arc trong `StoryPlan`.
        position: Thứ tự tuần tự bắt đầu từ 1, dùng để sắp xếp mạch kể chuyện.
        title: Tên arc hiển thị cho merchant khi rà soát kế hoạch.
        sku_id: Mã SKU chính của arc; nếu được gán thì mọi topic có `sku_id` bên trong phải khớp.
        target_duration_sec: Thời lượng mục tiêu (giây) của arc trong khoảng `(0, MAX_ARC_DURATION_SEC]`.
        topics: Danh sách không rỗng các `StoryTopic` thuộc arc này.
        breakpoint_hint: Gợi ý loại điểm ngắt mặc định ở cuối arc.
        preview_text: Bản tóm tắt xem trước dành cho UI merchant duyệt kế hoạch (Gate G6).
        reviewed_by_merchant: Cờ ghi nhận merchant đã xem qua arc này hay chưa.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    arc_id: NonBlankStr
    position: StrictPositiveInt
    title: NonBlankStr
    sku_id: OptionalNonBlankStr = None
    target_duration_sec: StrictArcDurationSec
    topics: list[StoryTopic] = Field(min_length=1)
    breakpoint_hint: BreakpointType = BreakpointType.ARC_BOUNDARY
    preview_text: OptionalNonBlankStr = None
    reviewed_by_merchant: StrictBool = False

    @model_validator(mode="after")
    def validate_arc_topics_consistency(self) -> StoryArc:
        """Kiểm tra tính duy nhất của `topic_id` và tính nhất quán `sku_id` trong cùng một arc.

        Returns:
            StoryArc: Chính đối tượng `StoryArc` sau khi thỏa mãn các bất biến nội bộ.

        Raises:
            ValueError: Nếu có `topic_id` bị trùng lặp trong arc hoặc `topic.sku_id` xung đột
                với `arc.sku_id` khi `arc.sku_id` đã được chỉ định.
        """
        seen_topic_ids: set[str] = set()
        for topic in self.topics:
            # Tránh mơ hồ khi theo dõi Global Topic Coverage nếu hai topic dùng chung ID.
            if topic.topic_id in seen_topic_ids:
                raise ValueError(
                    f"arc '{self.arc_id}' chứa topic_id bị trùng lặp: '{topic.topic_id}'."
                )
            seen_topic_ids.add(topic.topic_id)

            # Bảo vệ ranh giới SKU: topic thuộc một arc gắn SKU cụ thể không được trỏ sang SKU khác.
            if self.sku_id is not None and topic.sku_id is not None and topic.sku_id != self.sku_id:
                raise ValueError(
                    f"Topic '{topic.topic_id}' có sku_id='{topic.sku_id}' không khớp với "
                    f"arc.sku_id='{self.sku_id}'."
                )
        return self


class StoryPlan(BaseModel):
    """Kế hoạch kể chuyện phiên live cấp cao (Hierarchical Plan) có phiên bản và trạng thái duyệt.

    Attributes:
        contract_version: Phiên bản hợp đồng dữ liệu (`p06-mock-v0.1`).
        plan_id: Mã định danh kế hoạch.
        tenant_id: Mã tenant sở hữu phiên live (bảo đảm cô lập R10).
        session_id: Mã phiên livestream gắn với kế hoạch.
        plan_revision: Số phiên bản tăng dần mỗi lần merchant chỉnh sửa hoặc tái lập kế hoạch.
        approval_status: Trạng thái phê duyệt của kế hoạch.
        approved_by: Định danh người phê duyệt (bắt buộc khi `APPROVED`).
        approved_at: Thời điểm phê duyệt (bắt buộc khi `APPROVED`).
        session_goal: Mục tiêu bán hàng do merchant đặt ra cho phiên live.
        pinned_sku_ids: Danh sách 1–5 mã SKU được ghim trong phiên (theo ACR-002).
        mandatory_messages: Các thông điệp bắt buộc merchant yêu cầu nhắc tới.
        prohibited_topics: Các chủ đề bị cấm đề cập trong phiên.
        knowledge_versions_by_sku: Ánh xạ `sku_id -> knowledge_version` để phát hiện dữ liệu cũ.
        arcs: Danh sách các `StoryArc` theo thứ tự vị trí liên tục `1..len(arcs)`.
        is_synthetic: Đánh dấu dữ liệu tổng hợp phục vụ PoC/thí nghiệm hay dữ liệu thực.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    contract_version: ContractVersion = CONTRACT_VERSION
    plan_id: NonBlankStr
    tenant_id: NonBlankStr
    session_id: NonBlankStr
    plan_revision: StrictPositiveInt
    approval_status: StoryPlanApprovalStatus = StoryPlanApprovalStatus.DRAFT
    approved_by: OptionalNonBlankStr = None
    approved_at: Optional[datetime] = None
    session_goal: NonBlankStr
    pinned_sku_ids: list[NonBlankStr] = Field(min_length=MIN_PINNED_SKUS, max_length=MAX_PINNED_SKUS)
    mandatory_messages: list[NonBlankStr] = Field(default_factory=list)
    prohibited_topics: list[NonBlankStr] = Field(default_factory=list)
    knowledge_versions_by_sku: dict[NonBlankStr, StrictPositiveInt] = Field(default_factory=dict)
    arcs: list[StoryArc] = Field(min_length=1)
    is_synthetic: StrictBool = True

    @field_validator("pinned_sku_ids")
    @classmethod
    def validate_pinned_sku_ids(cls, value: list[str]) -> list[str]:
        """Bảo đảm danh sách SKU ghim không chứa chuỗi rỗng/khoảng trắng và không bị trùng lặp.

        Args:
            value: Danh sách `sku_id` được ghim cho phiên live.

        Returns:
            list[str]: Danh sách `sku_id` hợp lệ giữ nguyên thứ tự.

        Raises:
            ValueError: Nếu có `sku_id` bị lặp lại.
        """
        seen: set[str] = set()
        for sku_id in value:
            if sku_id in seen:
                raise ValueError(f"pinned_sku_ids chứa sku_id bị trùng lặp: '{sku_id}'.")
            seen.add(sku_id)
        return value

    @model_validator(mode="after")
    def validate_plan_invariants(self) -> StoryPlan:
        """Kiểm tra toàn bộ bất biến liên trường của `StoryPlan` (vị trí arc, phạm vi SKU, dấu vết duyệt).

        Returns:
            StoryPlan: Kế hoạch hợp lệ sau khi qua kiểm định liên trường.

        Raises:
            ValueError: Nếu khóa `knowledge_versions_by_sku` nằm ngoài `pinned_sku_ids`,
                vị trí `arcs` không liên tục `1..N`, trùng `arc_id`/`topic_id` toàn cục,
                `sku_id` tham chiếu ngoài danh sách ghim, hoặc thiếu provenance khi `APPROVED`.
        """
        pinned_set = set(self.pinned_sku_ids)

        # Chỉ giữ phiên bản tri thức cho các SKU thực sự thuộc phiên để tránh state rác khi kiểm tra TOCTOU.
        for sku_id in self.knowledge_versions_by_sku:
            if sku_id not in pinned_set:
                raise ValueError(
                    f"knowledge_versions_by_sku chứa SKU '{sku_id}' không nằm trong pinned_sku_ids."
                )

        # Kiểm tra thứ tự vị trí liên tục 1..len(arcs), tính duy nhất của arc_id và topic_id toàn cục.
        expected_positions = list(range(1, len(self.arcs) + 1))
        actual_positions = [arc.position for arc in self.arcs]
        if actual_positions != expected_positions:
            raise ValueError(
                f"Vị trí các StoryArc phải liên tục {expected_positions}, nhận được {actual_positions}."
            )

        seen_arc_ids: set[str] = set()
        seen_topic_ids: set[str] = set()
        for arc in self.arcs:
            if arc.arc_id in seen_arc_ids:
                raise ValueError(f"StoryPlan '{self.plan_id}' chứa arc_id trùng lặp: '{arc.arc_id}'.")
            seen_arc_ids.add(arc.arc_id)

            if arc.sku_id is not None and arc.sku_id not in pinned_set:
                raise ValueError(
                    f"StoryArc '{arc.arc_id}' tham chiếu sku_id='{arc.sku_id}' không thuộc pinned_sku_ids."
                )

            for topic in arc.topics:
                if topic.topic_id in seen_topic_ids:
                    raise ValueError(
                        f"StoryPlan '{self.plan_id}' chứa topic_id trùng lặp toàn cục: '{topic.topic_id}'."
                    )
                seen_topic_ids.add(topic.topic_id)

                if topic.sku_id is not None and topic.sku_id not in pinned_set:
                    raise ValueError(
                        f"StoryTopic '{topic.topic_id}' tham chiếu sku_id='{topic.sku_id}' "
                        "không thuộc pinned_sku_ids."
                    )

        # Gate G6: Kế hoạch chỉ được xem là APPROVED khi truy vết được người duyệt và thời điểm duyệt.
        if self.approval_status == StoryPlanApprovalStatus.APPROVED:
            if self.approved_by is None or not self.approved_by.strip():
                raise ValueError(
                    "StoryPlan ở trạng thái APPROVED bắt buộc phải có approved_by không rỗng."
                )
            if self.approved_at is None:
                raise ValueError(
                    "StoryPlan ở trạng thái APPROVED bắt buộc phải có approved_at."
                )

        return self

    def with_approval(self, approved_by: str, approved_at: datetime) -> StoryPlan:
        """Tạo bản sao `StoryPlan` mới ở trạng thái `APPROVED` một cách nguyên tử.

        Lý do kỹ thuật: Vì `frozen=True` ngăn đột biến từng phần tại chỗ, phương thức này sao chép sâu
        payload và chạy lại `model_validate()` để giữ nguyên bản gốc nếu dữ liệu duyệt không hợp lệ.

        Args:
            approved_by: Định danh người phê duyệt (cấm rỗng hoặc chỉ khoảng trắng).
            approved_at: Thời điểm phê duyệt.

        Returns:
            StoryPlan: Bản sao kế hoạch đã đạt kiểm định đầy đủ ở trạng thái `APPROVED`.

        Raises:
            ValidationError: Nếu `approved_by` rỗng/sai kiểu hoặc bất biến kế hoạch không thỏa mãn.
        """
        payload = copy.deepcopy(self.model_dump())
        payload["approval_status"] = StoryPlanApprovalStatus.APPROVED
        payload["approved_by"] = approved_by
        payload["approved_at"] = approved_at
        return type(self).model_validate(payload)

    def is_mvp_live_eligible(self) -> bool:
        """Kiểm tra kế hoạch có đủ điều kiện phát live thực tế ở giai đoạn MVP (ACR-002 & Gate G6).

        Lý do phân tách: Schema cho phép `MIN_PINNED_SKUS = 1` để hỗ trợ unit test cô lập `W0`,
        còn cấu hình phát live MVP theo `ACR-002` yêu cầu tối thiểu 2 SKU được ghim (2–5 SKU)
        và kế hoạch đã đạt `APPROVED`.

        Returns:
            bool: `True` chỉ khi kế hoạch đã `APPROVED` và có từ 2 đến `MAX_PINNED_SKUS` SKU ghim.
        """
        return (
            2 <= len(self.pinned_sku_ids) <= MAX_PINNED_SKUS
            and self.approval_status == StoryPlanApprovalStatus.APPROVED
        )

    def all_topic_ids(self) -> set[str]:
        """Trả về tập hợp toàn bộ `topic_id` xuất hiện trong tất cả `StoryArc`.

        Returns:
            set[str]: Tập mã chủ đề của toàn kế hoạch.
        """
        return {topic.topic_id for arc in self.arcs for topic in arc.topics}

    def mandatory_topic_ids(self) -> set[str]:
        """Trả về tập hợp các `topic_id` có `is_mandatory=True` cần theo dõi độ phủ.

        Returns:
            set[str]: Tập mã chủ đề bắt buộc trong kế hoạch.
        """
        return {
            topic.topic_id
            for arc in self.arcs
            for topic in arc.topics
            if topic.is_mandatory
        }


class StoryChunk(BaseModel):
    """Một đoạn thoại kể chuyện ngắn (<= 30s) sinh ra cho một chủ đề trong `StoryPlan`.

    Lưu ý bất biến: `StoryChunk` chỉ là bản nháp kịch bản nội bộ của P06, chưa phải lời thoại
    được phép phát sóng (`VerifiedSpeechCandidate`) và chưa chứng minh đã phát (`PlaybackCompleted`).

    Attributes:
        contract_version: Phiên bản hợp đồng dữ liệu (`p06-mock-v0.1`).
        chunk_id: Mã định danh duy nhất của chunk.
        plan_id: Mã `StoryPlan` gốc.
        plan_revision: Phiên bản `StoryPlan` mà chunk này bám theo.
        arc_id: Mã `StoryArc` tương ứng.
        topic_id: Mã `StoryTopic` tương ứng.
        sequence_index: Chỉ số thứ tự chunk (bắt đầu từ 0) phục vụ resume không trùng lặp.
        role: Vai trò ngữ dụng của đoạn thoại.
        sku_id: Mã SKU liên quan (nếu có).
        text: Nội dung lời thoại tiếng Việt (tự động strip khoảng trắng đầu/cuối, cấm rỗng).
        cited_evidence_ids: Các `evidence_id` P05 được trích dẫn để làm căn cứ.
        estimated_duration_sec: Thời lượng đọc ước lượng (giây), giới hạn `(0, MAX_CHUNK_DURATION_SEC]`.
        semantic_breakpoint: Đánh dấu cuối chunk có phải điểm ngắt ngữ nghĩa an toàn hay không.
        breakpoint_type: Loại điểm ngắt ngữ nghĩa tại cuối chunk.
        rationale: Giải thích ngắn lý do chọn chunk này phục vụ audit/debug.
        created_at: Thời điểm tạo bản nháp (UTC).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    contract_version: ContractVersion = CONTRACT_VERSION
    chunk_id: NonBlankStr
    plan_id: NonBlankStr
    plan_revision: StrictPositiveInt
    arc_id: NonBlankStr
    topic_id: NonBlankStr
    sequence_index: StrictNonNegInt
    role: StoryChunkRole
    sku_id: OptionalNonBlankStr = None
    text: NonBlankStr
    cited_evidence_ids: list[NonBlankStr] = Field(default_factory=list)
    estimated_duration_sec: StrictDurationSec
    semantic_breakpoint: StrictBool = True
    breakpoint_type: BreakpointType = BreakpointType.TOPIC_END
    rationale: OptionalNonBlankStr = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
