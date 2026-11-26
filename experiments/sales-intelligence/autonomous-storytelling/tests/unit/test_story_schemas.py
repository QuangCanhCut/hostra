"""Bộ kiểm thử đơn vị (unit tests) cho các schema kế hoạch kể chuyện trong `p06.schemas.story`.

1. File này giải quyết vấn đề gì?
   Xác minh toàn bộ hợp đồng dữ liệu cho `StoryTopic`, `StoryArc`, `StoryPlan` và `StoryChunk`
   ở cả kịch bản hợp lệ lẫn các trường hợp biên vi phạm bất biến.
2. Trách nhiệm chính của module là gì?
   Kiểm tra validation của Pydantic v2 (`extra="forbid"`, `frozen=True`), chuyển đổi bất biến
   nguyên tử (`with_approval`), điều kiện `is_mvp_live_eligible()`, kiểm định kiểu nghiêm ngặt
   (từ chối `bool`/`str` ép kiểu và chuỗi chỉ chứa khoảng trắng), tuần tự hóa JSON roundtrip,
   ràng buộc `pinned_sku_ids`, thứ tự vị trí `StoryArc`, dấu vết duyệt `APPROVED` và `StoryChunk`.
3. Module này liên kết với các thành phần nào?
   Kiểm thử trực tiếp `p06.schemas.story` và các re-export từ `p06` / `p06.schemas`.
4. Input và output chính là gì?
   Input là các factory payload hợp lệ và các đột biến dữ liệu cố tình sai;
   Output là kết quả pass/fail xác định qua `pytest`.
5. Có những constraints hoặc invariants quan trọng nào?
   Không gọi LLM, không dùng mạng hoặc dữ liệu ngoài sandbox; mọi kiểm thử chạy hoàn toàn deterministic.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from p06.schemas import (
    CONTRACT_VERSION,
    MAX_ARC_DURATION_SEC,
    MAX_CHUNK_DURATION_SEC,
    MAX_PINNED_SKUS,
    BreakpointType,
    StoryArc,
    StoryChunk,
    StoryChunkRole,
    StoryPlan,
    StoryPlanApprovalStatus,
    StoryTopic,
)


def _make_topic(
    topic_id: str = "topic-01",
    sku_id: str | None = "SKU-HONEY-01",
    is_mandatory: bool = True,
) -> StoryTopic:
    """Tạo nhanh một `StoryTopic` hợp lệ dùng chung cho các test case kế hoạch.

    Args:
        topic_id: Mã định danh chủ đề.
        sku_id: Mã SKU gắn với chủ đề (hoặc `None`).
        is_mandatory: Có bắt buộc phủ trong phiên live hay không.

    Returns:
        StoryTopic: Đối tượng chủ đề hợp lệ.
    """
    return StoryTopic(
        topic_id=topic_id,
        title="Nguồn gốc mật ong hoa cà phê",
        sku_id=sku_id,
        is_mandatory=is_mandatory,
        fact_refs=["ev-honey-04"],
        allowed_claim_ids=["clm-honey-allowed-01"],
        talking_points=["Thu hoạch tháng 2-3 tại Cư M'gar"],
    )


def _make_arc(
    arc_id: str = "arc-01",
    position: int = 1,
    sku_id: str | None = "SKU-HONEY-01",
    topics: list[StoryTopic] | None = None,
) -> StoryArc:
    """Tạo nhanh một `StoryArc` hợp lệ cho kiểm thử.

    Args:
        arc_id: Mã arc.
        position: Thứ tự arc (>= 1).
        sku_id: Mã SKU chính của arc.
        topics: Danh sách topic bên trong arc; mặc định tạo 1 topic hợp lệ.

    Returns:
        StoryArc: Đối tượng arc hợp lệ.
    """
    return StoryArc(
        arc_id=arc_id,
        position=position,
        title=f"Giới thiệu {sku_id or 'Phiên live'}",
        sku_id=sku_id,
        target_duration_sec=300,
        topics=topics or [_make_topic(topic_id=f"{arc_id}-t1", sku_id=sku_id)],
    )


def _make_approved_plan(
    pinned_sku_ids: list[str] | None = None,
    arcs: list[StoryArc] | None = None,
) -> StoryPlan:
    """Tạo một `StoryPlan` ở trạng thái `APPROVED` hợp lệ làm dữ liệu chuẩn.

    Args:
        pinned_sku_ids: Danh sách SKU ghim (mặc định 2 SKU).
        arcs: Danh sách arc (mặc định 2 arc vị trí 1 và 2).

    Returns:
        StoryPlan: Kế hoạch đã phê duyệt hợp lệ.
    """
    skus = ["SKU-HONEY-01", "SKU-TEA-02"] if pinned_sku_ids is None else pinned_sku_ids
    default_arcs = (
        [
            _make_arc(arc_id="arc-01", position=1, sku_id=skus[0] if skus else None),
            _make_arc(
                arc_id="arc-02",
                position=2,
                sku_id=skus[-1] if skus else None,
                topics=[
                    _make_topic(
                        topic_id="arc-02-t1",
                        sku_id=skus[-1] if skus else None,
                        is_mandatory=False,
                    )
                ],
            ),
        ]
        if arcs is None
        else arcs
    )
    return StoryPlan(
        plan_id="plan-demo-01",
        tenant_id="tenant-demo-01",
        session_id="session-demo-01",
        plan_revision=1,
        approval_status=StoryPlanApprovalStatus.APPROVED,
        approved_by="merchant-owner-01",
        approved_at=datetime(2026, 11, 25, 10, 0, tzinfo=timezone.utc),
        session_goal="Giới thiệu bộ sản phẩm đặc sản OCOP 4 sao",
        pinned_sku_ids=skus,
        mandatory_messages=["Không nói công dụng chữa bệnh"],
        prohibited_topics=["Chữa đau dạ dày"],
        knowledge_versions_by_sku={sku: 1 for sku in skus},
        arcs=default_arcs,
    )


class TestStoryPlanAndHierarchy:
    """Nhóm test kiểm định `StoryTopic`, `StoryArc` và `StoryPlan`."""

    def test_valid_single_and_multi_sku_plans_and_helpers(self) -> None:
        """Kiểm tra kế hoạch 1 SKU (W0) và nhiều SKU (ACR-002) cùng các helper topic IDs."""
        single_plan = _make_approved_plan(
            pinned_sku_ids=["SKU-HONEY-01"],
            arcs=[_make_arc(arc_id="arc-01", position=1, sku_id="SKU-HONEY-01")],
        )
        assert single_plan.contract_version == CONTRACT_VERSION
        assert single_plan.all_topic_ids() == {"arc-01-t1"}
        assert single_plan.mandatory_topic_ids() == {"arc-01-t1"}

        multi_plan = _make_approved_plan()
        assert multi_plan.all_topic_ids() == {"arc-01-t1", "arc-02-t1"}
        # arc-02-t1 có is_mandatory=False nên chỉ còn arc-01-t1 trong tập bắt buộc.
        assert multi_plan.mandatory_topic_ids() == {"arc-01-t1"}

    def test_story_plan_json_roundtrip(self) -> None:
        """Đảm bảo `StoryPlan` tuần tự hóa sang JSON và đọc lại giữ nguyên toàn bộ trường."""
        plan = _make_approved_plan()
        raw_json = plan.model_dump_json()
        restored = StoryPlan.model_validate_json(raw_json)
        assert restored == plan

    def test_extra_fields_forbidden_on_story_models(self) -> None:
        """Đảm bảo mọi schema từ chối trường thừa ngoài hợp đồng (`extra='forbid'`)."""
        with pytest.raises(ValidationError):
            StoryTopic(topic_id="t1", title="T1", unexpected_field="bad")  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            StoryArc(
                arc_id="a1",
                position=1,
                title="A1",
                target_duration_sec=120,
                topics=[_make_topic()],
                extra_flag=True,  # type: ignore[call-arg]
            )

    def test_invalid_contract_version_and_missing_fields_rejected(self) -> None:
        """Từ chối `contract_version` sai hoặc thiếu trường bắt buộc."""
        payload = _make_approved_plan().model_dump()
        payload["contract_version"] = "p06-mock-v9.9"
        with pytest.raises(ValidationError):
            StoryPlan.model_validate(payload)

        payload.pop("session_goal")
        payload["contract_version"] = CONTRACT_VERSION
        with pytest.raises(ValidationError):
            StoryPlan.model_validate(payload)

    def test_pinned_sku_bounds_blank_and_duplicates_rejected(self) -> None:
        """Kiểm tra giới hạn 1–5 SKU, cấm rỗng và cấm trùng SKU trong `pinned_sku_ids`."""
        with pytest.raises(ValidationError):
            _make_approved_plan(pinned_sku_ids=[], arcs=[_make_arc(sku_id=None)])

        too_many = [f"SKU-{idx}" for idx in range(MAX_PINNED_SKUS + 1)]
        with pytest.raises(ValidationError):
            _make_approved_plan(
                pinned_sku_ids=too_many,
                arcs=[_make_arc(sku_id=too_many[0])],
            )

        with pytest.raises(ValidationError):
            _make_approved_plan(
                pinned_sku_ids=["SKU-HONEY-01", "   "],
                arcs=[_make_arc(sku_id="SKU-HONEY-01")],
            )

        with pytest.raises(ValidationError):
            _make_approved_plan(
                pinned_sku_ids=["SKU-HONEY-01", "SKU-HONEY-01"],
                arcs=[_make_arc(sku_id="SKU-HONEY-01")],
            )

    def test_knowledge_versions_must_match_pinned_skus_and_be_positive(self) -> None:
        """Từ chối `knowledge_versions_by_sku` chứa SKU ngoài phiên hoặc version < 1."""
        plan = _make_approved_plan()
        with pytest.raises(ValidationError):
            plan.model_validate(
                {**plan.model_dump(), "knowledge_versions_by_sku": {"SKU-UNKNOWN": 1}}
            )

        with pytest.raises(ValidationError):
            plan.model_validate(
                {**plan.model_dump(), "knowledge_versions_by_sku": {"SKU-HONEY-01": 0}}
            )

    def test_arc_topic_uniqueness_and_sku_alignment(self) -> None:
        """Kiểm tra trùng `topic_id` trong arc, xung đột `sku_id` giữa arc và topic, và giới hạn duration."""
        with pytest.raises(ValidationError):
            StoryArc(
                arc_id="arc-dup",
                position=1,
                title="Arc lỗi trùng topic",
                sku_id="SKU-HONEY-01",
                target_duration_sec=120,
                topics=[
                    _make_topic(topic_id="t-same", sku_id="SKU-HONEY-01"),
                    _make_topic(topic_id="t-same", sku_id="SKU-HONEY-01"),
                ],
            )

        with pytest.raises(ValidationError):
            StoryArc(
                arc_id="arc-mismatch",
                position=1,
                title="Arc lệch SKU",
                sku_id="SKU-HONEY-01",
                target_duration_sec=120,
                topics=[_make_topic(topic_id="t1", sku_id="SKU-TEA-02")],
            )

        with pytest.raises(ValidationError):
            StoryArc(
                arc_id="arc-too-long",
                position=1,
                title="Arc quá dài",
                target_duration_sec=MAX_ARC_DURATION_SEC + 1,
                topics=[_make_topic()],
            )

    def test_plan_arc_position_contiguity_global_uniqueness_and_sku_scope(self) -> None:
        """Kiểm tra vị trí arc liên tục `1..N`, duy nhất toàn cục và SKU nằm trong `pinned_sku_ids`."""
        # Vị trí bị nhảy cóc [1, 3]
        with pytest.raises(ValidationError):
            _make_approved_plan(
                arcs=[
                    _make_arc(arc_id="arc-01", position=1, sku_id="SKU-HONEY-01"),
                    _make_arc(arc_id="arc-02", position=3, sku_id="SKU-TEA-02"),
                ]
            )

        # Trùng arc_id
        with pytest.raises(ValidationError):
            _make_approved_plan(
                arcs=[
                    _make_arc(arc_id="arc-dup", position=1, sku_id="SKU-HONEY-01"),
                    _make_arc(
                        arc_id="arc-dup",
                        position=2,
                        sku_id="SKU-TEA-02",
                        topics=[_make_topic(topic_id="t-2", sku_id="SKU-TEA-02")],
                    ),
                ]
            )

        # Trùng topic_id giữa 2 arc khác nhau
        with pytest.raises(ValidationError):
            _make_approved_plan(
                arcs=[
                    _make_arc(
                        arc_id="arc-01",
                        position=1,
                        sku_id="SKU-HONEY-01",
                        topics=[_make_topic(topic_id="global-dup", sku_id="SKU-HONEY-01")],
                    ),
                    _make_arc(
                        arc_id="arc-02",
                        position=2,
                        sku_id="SKU-TEA-02",
                        topics=[_make_topic(topic_id="global-dup", sku_id="SKU-TEA-02")],
                    ),
                ]
            )

        # Arc hoặc topic trỏ sang SKU không nằm trong pinned_sku_ids
        with pytest.raises(ValidationError):
            _make_approved_plan(
                pinned_sku_ids=["SKU-HONEY-01"],
                arcs=[_make_arc(arc_id="arc-01", position=1, sku_id="SKU-CASHEW-03")],
            )

    def test_approved_plan_requires_provenance_and_frozen_atomic_transition(self) -> None:
        """Gate G6 & frozen=True: chặn gán trực tiếp, giữ nguyên bản gốc khi lỗi và hỗ trợ `with_approval`."""
        draft_plan = StoryPlan(
            plan_id="plan-draft-01",
            tenant_id="tenant-demo-01",
            session_id="session-demo-01",
            plan_revision=1,
            approval_status=StoryPlanApprovalStatus.DRAFT,
            session_goal="Test draft",
            pinned_sku_ids=["SKU-HONEY-01"],
            arcs=[_make_arc(sku_id="SKU-HONEY-01")],
        )

        # Kiểm tra frozen=True chặn gán trực tiếp và bảo toàn 100% trạng thái bản gốc.
        with pytest.raises(ValidationError):
            draft_plan.approval_status = StoryPlanApprovalStatus.APPROVED  # type: ignore[misc]
        assert draft_plan.approval_status == StoryPlanApprovalStatus.DRAFT

        approved_at = datetime(2026, 11, 26, 8, 30, tzinfo=timezone.utc)
        # Thử with_approval với approved_by toàn khoảng trắng -> ném ValidationError và giữ nguyên draft_plan.
        with pytest.raises(ValidationError):
            draft_plan.with_approval(approved_by="   ", approved_at=approved_at)
        assert draft_plan.approval_status == StoryPlanApprovalStatus.DRAFT
        assert draft_plan.approved_by is None

        # with_approval hợp lệ trả về thể hiện mới, không làm thay đổi draft_plan gốc.
        approved_plan = draft_plan.with_approval(
            approved_by="  merchant-owner-01  ",
            approved_at=approved_at,
        )
        assert approved_plan.approval_status == StoryPlanApprovalStatus.APPROVED
        assert approved_plan.approved_by == "merchant-owner-01"
        assert approved_plan.approved_at == approved_at
        assert draft_plan.approval_status == StoryPlanApprovalStatus.DRAFT

        payload = draft_plan.model_dump()
        payload["approval_status"] = StoryPlanApprovalStatus.APPROVED
        payload["approved_by"] = "   "
        payload["approved_at"] = approved_at
        with pytest.raises(ValidationError):
            StoryPlan.model_validate(payload)

    def test_is_mvp_live_eligible_distinguishes_w0_single_sku_from_acr002(self) -> None:
        """A-MIN-02: chỉ kế hoạch APPROVED có >= 2 SKU ghim mới đạt chuẩn phát live MVP (ACR-002)."""
        single_approved = _make_approved_plan(
            pinned_sku_ids=["SKU-HONEY-01"],
            arcs=[_make_arc(arc_id="arc-01", position=1, sku_id="SKU-HONEY-01")],
        )
        assert single_approved.is_mvp_live_eligible() is False

        multi_draft = StoryPlan(
            plan_id="plan-multi-draft",
            tenant_id="tenant-demo-01",
            session_id="session-demo-01",
            plan_revision=1,
            approval_status=StoryPlanApprovalStatus.DRAFT,
            session_goal="Test multi draft",
            pinned_sku_ids=["SKU-HONEY-01", "SKU-TEA-02"],
            arcs=[
                _make_arc(arc_id="arc-01", position=1, sku_id="SKU-HONEY-01"),
                _make_arc(
                    arc_id="arc-02",
                    position=2,
                    sku_id="SKU-TEA-02",
                    topics=[_make_topic(topic_id="arc-02-t1", sku_id="SKU-TEA-02")],
                ),
            ],
        )
        assert multi_draft.is_mvp_live_eligible() is False

        multi_approved = multi_draft.with_approval(
            approved_by="owner-01",
            approved_at=datetime(2026, 11, 26, 9, 0, tzinfo=timezone.utc),
        )
        assert multi_approved.is_mvp_live_eligible() is True

    def test_strict_types_and_non_blank_strings_enforced_on_story_models(self) -> None:
        """A-MAJ-01 & A-MAJ-02: từ chối ép kiểu bool<->int, str->bool và chuỗi toàn khoảng trắng."""
        # Chuỗi chỉ chứa khoảng trắng trong ID, title, optional str và list items bị từ chối.
        with pytest.raises(ValidationError):
            StoryTopic(topic_id="   ", title="Hợp lệ")
        with pytest.raises(ValidationError):
            StoryTopic(topic_id="t1", title="Hợp lệ", sku_id="   ")
        with pytest.raises(ValidationError):
            StoryTopic(topic_id="t1", title="Hợp lệ", fact_refs=["ev-1", "   "])
        with pytest.raises(ValidationError):
            StoryTopic(topic_id="t1", title="Hợp lệ", talking_points=["   "])
        with pytest.raises(ValidationError):
            StoryArc(
                arc_id="a1",
                position=1,
                title="Arc 1",
                target_duration_sec=120,
                topics=[_make_topic()],
                preview_text="   ",
            )
        with pytest.raises(ValidationError):
            StoryPlan(
                plan_id="plan-bad-list",
                tenant_id="tenant-demo-01",
                session_id="session-demo-01",
                plan_revision=1,
                session_goal="   ",
                pinned_sku_ids=["SKU-HONEY-01"],
                arcs=[_make_arc(sku_id="SKU-HONEY-01")],
            )
        with pytest.raises(ValidationError):
            StoryPlan(
                plan_id="plan-bad-msg",
                tenant_id="tenant-demo-01",
                session_id="session-demo-01",
                plan_revision=1,
                session_goal="Mục tiêu hợp lệ",
                pinned_sku_ids=["SKU-HONEY-01"],
                mandatory_messages=["   "],
                arcs=[_make_arc(sku_id="SKU-HONEY-01")],
            )

        # Từ chối bool truyền vào trường int và str/int truyền vào trường bool.
        with pytest.raises(ValidationError):
            StoryTopic(topic_id="t1", title="T1", is_mandatory="true")  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            StoryTopic(topic_id="t1", title="T1", is_mandatory=1)  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            StoryArc(
                arc_id="a1",
                position=True,  # type: ignore[arg-type]
                title="Arc 1",
                target_duration_sec=120,
                topics=[_make_topic()],
            )
        with pytest.raises(ValidationError):
            StoryArc(
                arc_id="a1",
                position=1,
                title="Arc 1",
                target_duration_sec=True,  # type: ignore[arg-type]
                topics=[_make_topic()],
            )
        with pytest.raises(ValidationError):
            StoryArc(
                arc_id="a1",
                position=1,
                title="Arc 1",
                target_duration_sec=120,
                topics=[_make_topic()],
                reviewed_by_merchant="false",  # type: ignore[arg-type]
            )


class TestStoryChunk:
    """Nhóm test kiểm định `StoryChunk`."""

    def test_valid_chunk_strips_text_and_roundtrips(self) -> None:
        """Kiểm tra strip khoảng trắng hai đầu cho `text` và roundtrip JSON."""
        chunk = StoryChunk(
            chunk_id="chunk-01",
            plan_id="plan-demo-01",
            plan_revision=1,
            arc_id="arc-01",
            topic_id="arc-01-t1",
            sequence_index=0,
            role=StoryChunkRole.PRODUCT_STORY,
            sku_id="SKU-HONEY-01",
            text="   Mật ong hoa cà phê Cư M'gar thu hoạch đúng mùa tháng 2-3.   ",
            cited_evidence_ids=["ev-honey-04"],
            estimated_duration_sec=8.5,
            breakpoint_type=BreakpointType.TOPIC_END,
        )
        assert chunk.text == "Mật ong hoa cà phê Cư M'gar thu hoạch đúng mùa tháng 2-3."
        restored = StoryChunk.model_validate_json(chunk.model_dump_json())
        assert restored == chunk

    def test_invalid_chunk_text_duration_and_sequence(self) -> None:
        """Từ chối `text` toàn khoảng trắng, thời lượng sai kiểu/vượt ngưỡng hoặc trường rỗng."""
        base_kwargs = {
            "chunk_id": "chunk-bad",
            "plan_id": "plan-demo-01",
            "plan_revision": 1,
            "arc_id": "arc-01",
            "topic_id": "arc-01-t1",
            "sequence_index": 0,
            "role": StoryChunkRole.OPENING,
            "text": "Xin chào cả nhà.",
            "estimated_duration_sec": 5.0,
        }

        with pytest.raises(ValidationError):
            StoryChunk(**{**base_kwargs, "text": "   \t\n "})

        with pytest.raises(ValidationError):
            StoryChunk(**{**base_kwargs, "estimated_duration_sec": 0.0})

        with pytest.raises(ValidationError):
            StoryChunk(**{**base_kwargs, "estimated_duration_sec": MAX_CHUNK_DURATION_SEC + 0.1})

        with pytest.raises(ValidationError):
            StoryChunk(**{**base_kwargs, "estimated_duration_sec": True})

        with pytest.raises(ValidationError):
            StoryChunk(**{**base_kwargs, "estimated_duration_sec": "5.0"})

        with pytest.raises(ValidationError):
            StoryChunk(**{**base_kwargs, "sequence_index": -1})

        with pytest.raises(ValidationError):
            StoryChunk(**{**base_kwargs, "sequence_index": False})

        with pytest.raises(ValidationError):
            StoryChunk(**{**base_kwargs, "semantic_breakpoint": 0})

        with pytest.raises(ValidationError):
            StoryChunk(**{**base_kwargs, "rationale": "   "})

        with pytest.raises(ValidationError):
            StoryChunk(**{**base_kwargs, "cited_evidence_ids": ["   "]})
