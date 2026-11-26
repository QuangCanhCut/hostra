"""Bộ lập nháp kế hoạch kể chuyện (`StoryPlanner`) và ranh giới phê duyệt mô phỏng (`Gate G6`).

1. File này giải quyết vấn đề gì?
   Chuyển đổi mục tiêu bán hàng của merchant (`MerchantGoalInput`) và tri thức sản phẩm đã kiểm chứng
   từ P05 (`SkuEvidenceView`) thành bản nháp `StoryPlan` ở trạng thái `DRAFT`, đồng thời tách biệt
   tường minh hành động phê duyệt kế hoạch qua `SimulatedMerchantApprovalBoundary`.
2. Trách nhiệm chính của module là gì?
   Định nghĩa `MerchantGoalInput`, lớp `StoryPlanner` (nạp tri thức live, dựng prompt có delimiter
   chống injection, gọi `LLMProvider`, đối chiếu chống bịa `fact_refs`/`allowed_claim_ids`, hydrate
   `StoryPlan(approval_status=DRAFT)`), và `SimulatedMerchantApprovalBoundary.approve_plan()`.
3. Module này liên kết với các thành phần nào?
   Liên kết với `prompt_loader.py`, `draft_dtos.py`, `p06.adapters.interfaces` (`KnowledgeVerifierPort`,
   `SkuEvidenceView`), `p06.providers.base` (`LLMProvider`, `GenerationRequest`, `ProviderTelemetry`),
   và `p06.schemas.story` (`StoryPlan`, `StoryArc`, `StoryTopic`).
4. Input và output chính là gì?
   Input là `MerchantGoalInput` + cổng tri thức P05 + `LLMProvider`;
   Output là cặp `(StoryPlan[DRAFT], ProviderTelemetry)` hoặc `StoryPlan[APPROVED]` sau ranh giới duyệt.
5. Có những constraints hoặc invariants quan trọng nào?
   - `StoryPlanner` CHỈ được trả về `StoryPlan` ở trạng thái `DRAFT` (`approved_by=None`,
     `approved_at=None`, `reviewed_by_merchant=False`) theo Gate G6 và bất biến `I-02`.
   - Mọi SKU không đủ điều kiện (`is_eligible=False`), thiếu trong kho, hoặc lệch tenant đều fail-closed.
   - Mọi `fact_refs` và `allowed_claim_ids` do LLM sinh ra phải tồn tại trong `SkuEvidenceView` live
     của đúng SKU hiệu lực (chặn LLM bịa mã bằng chứng/claim).
   - Cấm tuyệt đối dùng `model_copy(update=...)`.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator

from p06.adapters.interfaces import KnowledgeVerifierPort, SkuEvidenceView
from p06.planning.draft_dtos import StoryPlanDraftLLMOutput
from p06.planning.prompt_loader import load_prompt_template, render_prompt_template
from p06.providers.base import GenerationRequest, LLMProvider, ProviderTelemetry
from p06.schemas.story import (
    MAX_PINNED_SKUS,
    MIN_PINNED_SKUS,
    NonBlankStr,
    StoryArc,
    StoryPlan,
    StoryPlanApprovalStatus,
    StoryTopic,
    StrictPositiveInt,
)


class MerchantGoalInput(BaseModel):
    """Đầu vào mục tiêu phiên livestream do merchant cung cấp để lập bản nháp `StoryPlan`.

    Attributes:
        tenant_id: Mã tenant sở hữu phiên (cô lập R10).
        session_id: Mã phiên livestream.
        plan_id: Mã định danh dự kiến cho `StoryPlan`.
        plan_revision: Số phiên bản kế hoạch (`>= 1`).
        session_goal: Mục tiêu bán hàng hoặc truyền tải thông điệp của phiên.
        pinned_sku_ids: Danh sách 1–5 `sku_id` được ghim cho phiên (không trùng lặp).
        target_duration_sec: Thời lượng mục tiêu toàn phiên tính bằng giây (`>= 1`).
        mandatory_messages: Danh sách thông điệp bắt buộc merchant yêu cầu đưa vào kế hoạch.
        prohibited_topics: Danh sách chủ đề bị cấm đề cập trong phiên.
        is_synthetic: Cờ đánh dấu dữ liệu tổng hợp phục vụ PoC hay dữ liệu thực.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    tenant_id: NonBlankStr
    session_id: NonBlankStr
    plan_id: NonBlankStr
    plan_revision: StrictPositiveInt = 1
    session_goal: NonBlankStr
    pinned_sku_ids: list[NonBlankStr] = Field(min_length=MIN_PINNED_SKUS, max_length=MAX_PINNED_SKUS)
    target_duration_sec: StrictPositiveInt = 600
    mandatory_messages: list[NonBlankStr] = Field(default_factory=list)
    prohibited_topics: list[NonBlankStr] = Field(default_factory=list)
    is_synthetic: StrictBool = True

    @field_validator("pinned_sku_ids")
    @classmethod
    def validate_unique_pinned_skus(cls, value: list[str]) -> list[str]:
        """Bảo đảm danh sách `pinned_sku_ids` không chứa mã SKU trùng lặp."""
        seen: set[str] = set()
        for sku_id in value:
            if sku_id in seen:
                raise ValueError(f"pinned_sku_ids chứa sku_id trùng lặp: '{sku_id}'.")
            seen.add(sku_id)
        return value


def _serialize_untrusted_knowledge_block(
    evidence_by_sku: dict[str, SkuEvidenceView],
) -> str:
    """Tuần tự hóa ảnh chụp tri thức P05 thành khối JSON đặt trong thẻ `<untrusted_knowledge_data>`."""
    payload: list[dict[str, Any]] = []
    for sku_id, view in evidence_by_sku.items():
        payload.append(
            {
                "sku_id": sku_id,
                "sku_name": view.sku_name,
                "price_vnd": view.price_vnd,
                "weight_display": view.weight_display,
                "expiry_display": view.expiry_display,
                "origin": view.origin,
                "ingredients": list(view.ingredients),
                "storage_instructions": view.storage_instructions,
                "ocop_status": view.ocop_status,
                "ocop_code": view.ocop_code,
                "knowledge_version": view.knowledge_version,
                "approved_chunks": [dict(chunk) for chunk in view.approved_chunks],
                "allowed_claims": [dict(claim) for claim in view.allowed_claims],
                "prohibited_claims": list(view.prohibited_claims),
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _extract_valid_evidence_and_claim_ids(
    evidence_by_sku: dict[str, SkuEvidenceView],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Trích xuất tập `evidence_id` và `claim_id` hợp lệ theo từng SKU từ kho P05 live."""
    evidence_ids_by_sku: dict[str, set[str]] = {}
    claim_ids_by_sku: dict[str, set[str]] = {}
    for sku_id, view in evidence_by_sku.items():
        evidence_ids_by_sku[sku_id] = {
            chunk["evidence_id"].strip()
            for chunk in view.approved_chunks
            if isinstance(chunk.get("evidence_id"), str) and chunk["evidence_id"].strip()
        }
        claim_ids_by_sku[sku_id] = {
            claim["claim_id"].strip()
            for claim in view.allowed_claims
            if isinstance(claim.get("claim_id"), str) and claim["claim_id"].strip()
        }
    return evidence_ids_by_sku, claim_ids_by_sku


class StoryPlanner:
    """Bộ lập bản nháp `StoryPlan` bám chặt tri thức P05 đã kiểm chứng và bất biến Gate G6.

    Lý do thiết kế:
        `StoryPlanner` chỉ dùng DTO đầu ra thô (`StoryPlanDraftLLMOutput`) cho LLM để model
        không thể tự điền `approval_status=APPROVED` hoặc thay đổi `knowledge_versions_by_sku`;
        toàn bộ metadata thẩm quyền được hydrate từ nguồn P05 live với trạng thái cứng `DRAFT`.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        knowledge_verifier: KnowledgeVerifierPort,
        prompts_dir: Optional[Path] = None,
    ) -> None:
        """Khởi tạo `StoryPlanner` với provider LLM và cổng kiểm chứng tri thức P05.

        Args:
            llm_provider: Nhà cung cấp LLM trừu tượng (Mock, Ollama hoặc Gemini).
            knowledge_verifier: Cổng truy xuất tri thức và điều kiện SKU từ P05.
            prompts_dir: Thư mục chứa prompt templates tùy chọn (mặc định `DEFAULT_PROMPTS_DIR`).
        """
        self._llm_provider: LLMProvider = llm_provider
        self._knowledge_verifier: KnowledgeVerifierPort = knowledge_verifier
        self._prompts_dir: Optional[Path] = prompts_dir

    def _fetch_eligible_evidence(
        self,
        goal: MerchantGoalInput,
        at_time: Optional[datetime],
    ) -> dict[str, SkuEvidenceView]:
        """Nạp và kiểm tra điều kiện `is_eligible` cho toàn bộ SKU ghim trong `goal`."""
        evidence_by_sku: dict[str, SkuEvidenceView] = {}
        for sku_id in goal.pinned_sku_ids:
            view = self._knowledge_verifier.get_sku_evidence(
                goal.tenant_id,
                sku_id,
                at_time=at_time,
            )
            # Phòng thủ chiều sâu: đảm bảo adapter không trả về bản chụp thuộc tenant khác.
            if view.tenant_id != goal.tenant_id:
                raise PermissionError(
                    f"Vi phạm cô lập tenant: nhận được tenant_id='{view.tenant_id}' "
                    f"cho yêu cầu '{goal.tenant_id}'."
                )
            if not view.is_eligible:
                raise ValueError(
                    f"SKU '{sku_id}' không đủ điều kiện lập kế hoạch StoryPlan: "
                    f"{list(view.ineligible_reasons)}."
                )
            evidence_by_sku[sku_id] = view
        return evidence_by_sku

    @staticmethod
    def _validate_draft_grounding(
        draft: StoryPlanDraftLLMOutput,
        pinned_sku_ids: list[str],
        evidence_by_sku: dict[str, SkuEvidenceView],
    ) -> None:
        """Đối chiếu chặt mọi `sku_id`, `fact_refs` và `allowed_claim_ids` của bản nháp với P05 live."""
        pinned_set = set(pinned_sku_ids)
        evidence_ids_by_sku, claim_ids_by_sku = _extract_valid_evidence_and_claim_ids(evidence_by_sku)
        all_valid_evidence_ids = {
            ev_id for ev_set in evidence_ids_by_sku.values() for ev_id in ev_set
        }
        all_valid_claim_ids = {
            clm_id for clm_set in claim_ids_by_sku.values() for clm_id in clm_set
        }

        for arc_draft in draft.arcs:
            if arc_draft.sku_id is not None and arc_draft.sku_id not in pinned_set:
                raise ValueError(
                    f"Arc nháp '{arc_draft.arc_id}' tham chiếu sku_id='{arc_draft.sku_id}' "
                    f"nằm ngoài pinned_sku_ids={pinned_sku_ids}."
                )

            for topic_draft in arc_draft.topics:
                if topic_draft.sku_id is not None and topic_draft.sku_id not in pinned_set:
                    raise ValueError(
                        f"Topic nháp '{topic_draft.topic_id}' tham chiếu sku_id='{topic_draft.sku_id}' "
                        f"nằm ngoài pinned_sku_ids={pinned_sku_ids}."
                    )

                effective_sku_id = (
                    topic_draft.sku_id if topic_draft.sku_id is not None else arc_draft.sku_id
                )
                allowed_ev_ids = (
                    evidence_ids_by_sku[effective_sku_id]
                    if effective_sku_id is not None
                    else all_valid_evidence_ids
                )
                allowed_clm_ids = (
                    claim_ids_by_sku[effective_sku_id]
                    if effective_sku_id is not None
                    else all_valid_claim_ids
                )

                unknown_refs = [ref for ref in topic_draft.fact_refs if ref not in allowed_ev_ids]
                if unknown_refs:
                    raise ValueError(
                        f"Topic nháp '{topic_draft.topic_id}' chứa fact_refs không hợp lệ hoặc "
                        f"bịa đặt cho SKU '{effective_sku_id}': {unknown_refs}."
                    )

                unknown_claims = [
                    clm for clm in topic_draft.allowed_claim_ids if clm not in allowed_clm_ids
                ]
                if unknown_claims:
                    raise ValueError(
                        f"Topic nháp '{topic_draft.topic_id}' chứa allowed_claim_ids không hợp lệ "
                        f"hoặc bịa đặt cho SKU '{effective_sku_id}': {unknown_claims}."
                    )

    def draft_plan(
        self,
        goal: MerchantGoalInput,
        *,
        request_id: str,
        at_time: Optional[datetime] = None,
        seed: Optional[int] = None,
        data_classification: str = "SYNTHETIC",
    ) -> tuple[StoryPlan, ProviderTelemetry]:
        """Lập bản nháp `StoryPlan` (`DRAFT`) từ mục tiêu merchant và tri thức P05 hiện hành.

        Args:
            goal: Mục tiêu phiên live và danh sách SKU ghim do merchant chỉ định.
            request_id: Mã định danh duy nhất cho lượt gọi LLM (phục vụ telemetry/seed).
            at_time: Mốc thời gian kiểm tra cửa sổ hiệu lực tri thức P05 (tùy chọn).
            seed: Hạt giống ngẫu nhiên truyền xuống `GenerationRequest` (nếu có).
            data_classification: Phân loại dữ liệu gửi provider (mặc định `'SYNTHETIC'`).

        Returns:
            tuple[StoryPlan, ProviderTelemetry]: Cặp gồm `StoryPlan` ở trạng thái `DRAFT`
                (chưa duyệt) và `ProviderTelemetry` của lượt sinh kế hoạch.

        Raises:
            KeyError: Nếu một SKU ghim không tồn tại trong kho P05.
            PermissionError: Nếu SKU thuộc tenant khác với `goal.tenant_id`.
            ValueError: Nếu `request_id` rỗng, SKU không đủ điều kiện (`is_eligible=False`),
                hoặc LLM sinh `sku_id`/`fact_refs`/`allowed_claim_ids` không hợp lệ/bịa đặt.
            ProviderError: Nếu gọi `LLMProvider` hoặc phân tích JSON schema thất bại.
        """
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError("request_id không được rỗng khi gọi StoryPlanner.draft_plan().")

        evidence_by_sku = self._fetch_eligible_evidence(goal, at_time=at_time)
        knowledge_versions_by_sku = {
            sku_id: view.knowledge_version for sku_id, view in evidence_by_sku.items()
        }

        template = load_prompt_template("story_planner.txt", prompts_dir=self._prompts_dir)
        rendered_prompt = render_prompt_template(
            template,
            {
                "session_goal": goal.session_goal,
                "pinned_skus": ", ".join(goal.pinned_sku_ids),
                "mandatory_messages": json.dumps(goal.mandatory_messages, ensure_ascii=False),
                "prohibited_topics": json.dumps(goal.prohibited_topics, ensure_ascii=False),
                "target_duration_sec": str(goal.target_duration_sec),
                "untrusted_knowledge_block": _serialize_untrusted_knowledge_block(evidence_by_sku),
            },
        )

        request = GenerationRequest(
            request_id=request_id.strip(),
            system_prompt=rendered_prompt,
            user_prompt=(
                f"Hãy lập StoryPlanDraftLLMOutput dạng JSON cho mục tiêu '{goal.session_goal}' "
                f"với các SKU được ghim {goal.pinned_sku_ids}."
            ),
            prompt_version=template.version,
            data_classification=data_classification,
            seed=seed,
            metadata={
                "plan_id": goal.plan_id,
                "plan_revision": goal.plan_revision,
                "prompt_name": template.name,
                "prompt_sha256": template.sha256,
            },
        )
        gen_result = self._llm_provider.generate_structured(request, StoryPlanDraftLLMOutput)
        draft = gen_result.parsed_output

        self._validate_draft_grounding(draft, goal.pinned_sku_ids, evidence_by_sku)

        hydrated_arcs = [
            StoryArc(
                arc_id=arc_draft.arc_id,
                position=position,
                title=arc_draft.title,
                sku_id=arc_draft.sku_id,
                target_duration_sec=arc_draft.target_duration_sec,
                topics=[
                    StoryTopic(
                        topic_id=topic_draft.topic_id,
                        title=topic_draft.title,
                        sku_id=topic_draft.sku_id,
                        is_mandatory=topic_draft.is_mandatory,
                        fact_refs=list(topic_draft.fact_refs),
                        allowed_claim_ids=list(topic_draft.allowed_claim_ids),
                        talking_points=list(topic_draft.talking_points),
                    )
                    for topic_draft in arc_draft.topics
                ],
                breakpoint_hint=arc_draft.breakpoint_hint,
                preview_text=arc_draft.preview_text,
                reviewed_by_merchant=False,
            )
            for position, arc_draft in enumerate(draft.arcs, start=1)
        ]

        # Luôn khóa trạng thái khởi tạo là DRAFT (Gate G6); tuyệt đối không tự duyệt trong planner.
        draft_plan = StoryPlan(
            plan_id=goal.plan_id,
            tenant_id=goal.tenant_id,
            session_id=goal.session_id,
            plan_revision=goal.plan_revision,
            approval_status=StoryPlanApprovalStatus.DRAFT,
            approved_by=None,
            approved_at=None,
            session_goal=goal.session_goal,
            pinned_sku_ids=list(goal.pinned_sku_ids),
            mandatory_messages=list(goal.mandatory_messages),
            prohibited_topics=list(goal.prohibited_topics),
            knowledge_versions_by_sku=knowledge_versions_by_sku,
            arcs=hydrated_arcs,
            is_synthetic=goal.is_synthetic,
        )
        return draft_plan, gen_result.telemetry


class SimulatedMerchantApprovalBoundary:
    """Ranh giới mô phỏng hành động merchant/Owner phê duyệt `StoryPlan` (Gate G6).

    Lý do tách riêng khỏi `StoryPlanner`:
        Trong kiến trúc HOSTRA, LLM/P06 chỉ tạo bản nháp (`DRAFT`), còn quyền chuyển sang
        `APPROVED` thuộc về merchant/Owner thông qua giao diện kiểm duyệt (P10/P08). Lớp này
        mô phỏng rõ ràng cổng chuyển trạng thái đó cho kiểm thử và thí nghiệm PoC.
    """

    _APPROVABLE_STATUSES: frozenset[StoryPlanApprovalStatus] = frozenset(
        {
            StoryPlanApprovalStatus.DRAFT,
            StoryPlanApprovalStatus.REVIEW_REQUIRED,
        }
    )

    @staticmethod
    def approve_plan(
        draft_plan: StoryPlan,
        approved_by: str,
        approved_at: datetime,
    ) -> StoryPlan:
        """Phê duyệt một `StoryPlan` từ trạng thái `DRAFT` hoặc `REVIEW_REQUIRED` sang `APPROVED`.

        Args:
            draft_plan: Kế hoạch nháp cần phê duyệt.
            approved_by: Định danh merchant/Owner phê duyệt (bắt buộc không rỗng).
            approved_at: Dấu thời gian phê duyệt.

        Returns:
            StoryPlan: Bản sao kế hoạch mới ở trạng thái `APPROVED` gắn đủ provenance.

        Raises:
            ValueError: Nếu `draft_plan` đang ở trạng thái không thể duyệt lại
                (`APPROVED`, `INVALIDATED`, `SUPERSEDED`).
            ValidationError: Nếu `approved_by` rỗng hoặc `approved_at` không hợp lệ.
        """
        if draft_plan.approval_status not in SimulatedMerchantApprovalBoundary._APPROVABLE_STATUSES:
            raise ValueError(
                f"Chỉ có thể phê duyệt StoryPlan từ trạng thái DRAFT hoặc REVIEW_REQUIRED; "
                f"trạng thái hiện tại là '{draft_plan.approval_status.value}'."
            )
        return draft_plan.with_approval(approved_by=approved_by, approved_at=approved_at)
