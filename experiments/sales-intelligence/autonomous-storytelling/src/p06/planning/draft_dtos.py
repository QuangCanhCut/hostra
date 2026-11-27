"""Hợp đồng DTO bản nháp không tin cậy cho đầu ra có cấu trúc của LLM (Draft DTOs).

1. File này giải quyết vấn đề gì?
   Tạo ranh giới kiểu dữ liệu cứng giữa cấu trúc mà LLM được phép sinh ra với các trường metadata
   thẩm quyền của hệ thống (`tenant_id`, `approval_status`, `knowledge_version`, `verification_status`).
2. Trách nhiệm chính của module là gì?
   Định nghĩa các schema Pydantic v2 chỉ dành cho đầu ra thô từ LLM: `StoryTopicDraftLLMOutput`,
   `StoryArcDraftLLMOutput`, `StoryPlanDraftLLMOutput` và `ChunkDraftLLMOutput`.
3. Module này liên kết với các thành phần nào?
   Tái sử dụng các kiểu kiểm định từ `p06.schemas.story`; được truyền làm `output_schema` vào
   `LLMProvider.generate_structured()` trong `story_planner.py` và các node sinh thoại (`agent/nodes/`).
4. Input và output chính là gì?
   Input là JSON thô do LLM trả về;
   Output là các DTO bản nháp bất biến đã kiểm tra kiểu và tính nhất quán nội bộ trước khi hydrate
   sang `StoryPlan` (`DRAFT`) hoặc `SpeechCandidate` (`DRAFT`).
5. Có những constraints hoặc invariants quan trọng nào?
   - Tất cả DTO dùng `ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")`.
   - Tuyệt đối KHÔNG chứa bất kỳ trường thẩm quyền nào (`tenant_id`, `session_id`, `session_epoch`,
     `approval_status`, `approved_by`, `approved_at`, `knowledge_version`, `ocop_version`,
     `rights_version`, `verification_status`, `verified_by_gate_decision_id`, `verified_at`, `is_eligible`)
     để LLM không thể tự phê duyệt hoặc giả mạo trạng thái kiểm chứng (`I-02`, `Gate G6`).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from p06.schemas.story import (
    BreakpointType,
    NonBlankStr,
    OptionalNonBlankStr,
    StoryChunkRole,
    StrictArcDurationSec,
    StrictPositivePriceVnd,
)


class StoryTopicDraftLLMOutput(BaseModel):
    """Bản nháp không tin cậy cho một `StoryTopic` do LLM đề xuất khi lập kế hoạch.

    Attributes:
        topic_id: Mã định danh chủ đề đề xuất (không rỗng).
        title: Tiêu đề ngắn gọn của chủ đề.
        sku_id: Mã SKU liên quan (hoặc `None` nếu là chủ đề mở đầu/chung).
        is_mandatory: Đánh dấu chủ đề có bắt buộc phải phủ trong phiên hay không.
        fact_refs: Danh sách `evidence_id` mà LLM đề xuất bám theo (sẽ đối chiếu lại P05).
        allowed_claim_ids: Danh sách `claim_id` mà LLM đề xuất sử dụng (sẽ đối chiếu lại P05).
        talking_points: Các ý chính gợi ý để triển khai lời thoại.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    topic_id: NonBlankStr
    title: NonBlankStr
    sku_id: OptionalNonBlankStr = None
    is_mandatory: StrictBool = True
    fact_refs: list[NonBlankStr] = Field(default_factory=list)
    allowed_claim_ids: list[NonBlankStr] = Field(default_factory=list)
    talking_points: list[NonBlankStr] = Field(default_factory=list)


class StoryArcDraftLLMOutput(BaseModel):
    """Bản nháp không tin cậy cho một `StoryArc` do LLM đề xuất (không chứa `reviewed_by_merchant`).

    Attributes:
        arc_id: Mã định danh arc đề xuất.
        title: Tiêu đề arc hiển thị cho merchant rà soát.
        sku_id: Mã SKU chính của arc (hoặc `None`).
        target_duration_sec: Thời lượng mục tiêu của arc trong `(0, MAX_ARC_DURATION_SEC]`.
        topics: Danh sách không rỗng các `StoryTopicDraftLLMOutput`.
        breakpoint_hint: Gợi ý loại điểm ngắt ở cuối arc.
        preview_text: Tóm tắt xem trước để merchant đọc nhanh khi kiểm duyệt.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    arc_id: NonBlankStr
    title: NonBlankStr
    sku_id: OptionalNonBlankStr = None
    target_duration_sec: StrictArcDurationSec
    topics: list[StoryTopicDraftLLMOutput] = Field(min_length=1)
    breakpoint_hint: BreakpointType = BreakpointType.ARC_BOUNDARY
    preview_text: OptionalNonBlankStr = None

    @model_validator(mode="after")
    def validate_draft_arc_topics(self) -> StoryArcDraftLLMOutput:
        """Kiểm tra tính duy nhất của `topic_id` và tính khớp `sku_id` trong phạm vi arc nháp."""
        seen_topic_ids: set[str] = set()
        for topic in self.topics:
            if topic.topic_id in seen_topic_ids:
                raise ValueError(
                    f"Arc nháp '{self.arc_id}' chứa topic_id trùng lặp: '{topic.topic_id}'."
                )
            seen_topic_ids.add(topic.topic_id)
            if self.sku_id is not None and topic.sku_id is not None and topic.sku_id != self.sku_id:
                raise ValueError(
                    f"Topic nháp '{topic.topic_id}' có sku_id='{topic.sku_id}' không khớp "
                    f"arc.sku_id='{self.sku_id}'."
                )
        return self


class StoryPlanDraftLLMOutput(BaseModel):
    """Bản nháp kế hoạch cấp cao không tin cậy do LLM trả về cho `StoryPlanner`.

    Attributes:
        arcs: Danh sách không rỗng các `StoryArcDraftLLMOutput` theo thứ tự đề xuất.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    arcs: list[StoryArcDraftLLMOutput] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_ids_across_arcs(self) -> StoryPlanDraftLLMOutput:
        """Bảo đảm `arc_id` và `topic_id` là duy nhất trên toàn bộ bản nháp kế hoạch."""
        seen_arc_ids: set[str] = set()
        seen_topic_ids: set[str] = set()
        for arc in self.arcs:
            if arc.arc_id in seen_arc_ids:
                raise ValueError(f"Bản nháp kế hoạch chứa arc_id trùng lặp: '{arc.arc_id}'.")
            seen_arc_ids.add(arc.arc_id)
            for topic in arc.topics:
                if topic.topic_id in seen_topic_ids:
                    raise ValueError(
                        f"Bản nháp kế hoạch chứa topic_id trùng lặp toàn cục: '{topic.topic_id}'."
                    )
                seen_topic_ids.add(topic.topic_id)
        return self


def _require_citation_fields_in_json_schema(schema: dict[str, object]) -> None:
    """Đưa `cited_evidence_ids` và `covered_claim_ids` vào danh sách `required` trên OpenAPI schema.

    Lý do kỹ thuật: Giữ `default_factory=list` trên Python DTO để tương thích các test tạo trực tiếp
    trong bộ nhớ, đồng thời ép Gemini Structured Output (`responseSchema`) phải xuất tường minh
    hai trường trích dẫn bằng chứng/claim thay vì bỏ qua khi chạy `thinkingLevel=MINIMAL`.
    """
    raw_required = schema.get("required")
    required: list[str] = list(raw_required) if isinstance(raw_required, list) else []
    for field_name in ("text", "role", "cited_evidence_ids", "covered_claim_ids"):
        if field_name not in required:
            required.append(field_name)
    schema["required"] = required


class ChunkDraftLLMOutput(BaseModel):
    """Bản nháp không tin cậy cho một đoạn thoại ngắn (`StoryChunk` / `SpeechCandidate`) từ LLM.

    Attributes:
        text: Nội dung lời thoại tiếng Việt (chưa được xem là `VERIFIED`).
        role: Vai trò ngữ dụng của đoạn thoại trong mạch kể.
        cited_evidence_ids: Các `evidence_id` mà LLM khai báo đã trích dẫn.
        stated_price_vnd: Mức giá VNĐ nếu đoạn thoại có nhắc tới giá.
        mentions_ocop: Cờ cho biết đoạn thoại có nhắc tới chứng nhận OCOP hay không.
        semantic_breakpoint: Đánh dấu đoạn thoại kết thúc tại điểm ngắt ngữ nghĩa sạch.
        breakpoint_type: Loại điểm ngắt ngữ nghĩa ở cuối đoạn thoại.
        covered_claim_ids: Các `claim_id` mà đoạn thoại khai báo đã đề cập.
        rationale: Giải thích ngắn gọn phục vụ truy vết/gỡ lỗi.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        revalidate_instances="always",
        json_schema_extra=_require_citation_fields_in_json_schema,
    )

    text: NonBlankStr
    role: StoryChunkRole = StoryChunkRole.PRODUCT_STORY
    cited_evidence_ids: list[NonBlankStr] = Field(default_factory=list)
    stated_price_vnd: Optional[StrictPositivePriceVnd] = None
    mentions_ocop: StrictBool = False
    semantic_breakpoint: StrictBool = True
    breakpoint_type: BreakpointType = BreakpointType.TOPIC_END
    covered_claim_ids: list[NonBlankStr] = Field(default_factory=list)
    rationale: OptionalNonBlankStr = None
