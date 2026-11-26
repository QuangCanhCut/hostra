"""Bộ sắp xếp tuần tự chủ đề theo từng `StoryArc` và khóa `active_sku_id` (`ArcSequencer`).

1. File này giải quyết vấn đề gì?
   Xác định tất định chủ đề kế tiếp (`StoryTopic`) cần kể trong phiên livestream dựa trên
   `StoryPlan` đã `APPROVED`, `StoryCheckpoint` hiện hành, `active_sku_id` do P08 chỉ định,
   và tập chủ đề đã hoàn tất hoặc bị loại trừ.
2. Trách nhiệm chính của module là gì?
   Định nghĩa DTO kết quả bất biến `TopicSelectionResult` và lớp `ArcSequencer` với phương thức
   thuần túy `select_next_topic()` không gây hiệu ứng phụ.
3. Module này liên kết với các thành phần nào?
   Tiêu thụ `StoryPlan`, `StoryArc`, `StoryTopic` (`p06.schemas.story`), `StoryCheckpoint`
   (`p06.schemas.events`); được sử dụng bởi LangGraph nodes (`agent/nodes/`) và runner thí nghiệm.
4. Input và output chính là gì?
   Input là `story_plan`, `checkpoint`, `active_sku_id`, `completed_topic_ids`, `excluded_topic_ids`;
   Output là `TopicSelectionResult` chỉ rõ chủ đề được chọn, con trỏ kế tiếp hoặc tín hiệu dừng sạch.
5. Có những constraints hoặc invariants quan trọng nào?
   - `Gate G6`: Chỉ làm việc trên `StoryPlan` có `approval_status == APPROVED`.
   - `I-04`: `active_sku_id` phải thuộc `pinned_sku_ids` và khớp `checkpoint.active_sku_id`;
     tuyệt đối không chọn chủ đề thuộc SKU khác.
   - Thuần túy (pure function): không bao giờ làm thay đổi `completed_topic_ids`, `excluded_topic_ids`,
     hay `checkpoint`.
"""

from __future__ import annotations

from collections.abc import Set as AbstractSet
from typing import Optional

from pydantic import BaseModel, ConfigDict, StrictBool, model_validator

from p06.schemas.events import StoryCheckpoint
from p06.schemas.story import (
    OptionalNonBlankStr,
    StoryArc,
    StoryPlan,
    StoryPlanApprovalStatus,
    StoryTopic,
)


class TopicSelectionResult(BaseModel):
    """Kết quả chọn chủ đề tiếp theo từ `ArcSequencer` (bất biến).

    Attributes:
        selected_arc_id: Mã `StoryArc` chứa chủ đề được chọn (`None` khi kết thúc sạch).
        selected_topic: Đối tượng `StoryTopic` được chọn cho lượt hiện tại (`None` khi kết thúc).
        next_topic_id_after_selection: Gợi ý `topic_id` tiếp theo sau khi chủ đề này hoàn tất.
        next_arc_id_after_selection: Gợi ý `arc_id` tương ứng với `next_topic_id_after_selection`.
        should_terminate: `True` khi không còn chủ đề hợp lệ nào cho `active_sku_id`.
        termination_reason: Lý do dừng sạch khi `should_terminate=True`.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    selected_arc_id: OptionalNonBlankStr = None
    selected_topic: Optional[StoryTopic] = None
    next_topic_id_after_selection: OptionalNonBlankStr = None
    next_arc_id_after_selection: OptionalNonBlankStr = None
    should_terminate: StrictBool = False
    termination_reason: OptionalNonBlankStr = None

    @model_validator(mode="after")
    def validate_selection_consistency(self) -> TopicSelectionResult:
        """Bảo đảm tính nhất quán giữa cờ `should_terminate` và các trường chủ đề đi kèm."""
        if self.should_terminate:
            if self.selected_topic is not None or self.selected_arc_id is not None:
                raise ValueError(
                    "TopicSelectionResult có should_terminate=True bắt buộc "
                    "selected_topic và selected_arc_id phải là None."
                )
            if (
                self.next_topic_id_after_selection is not None
                or self.next_arc_id_after_selection is not None
            ):
                raise ValueError(
                    "TopicSelectionResult có should_terminate=True không được đặt "
                    "next_topic_id_after_selection hoặc next_arc_id_after_selection."
                )
        else:
            if self.selected_topic is None or self.selected_arc_id is None:
                raise ValueError(
                    "TopicSelectionResult có should_terminate=False bắt buộc phải có "
                    "cả selected_arc_id và selected_topic."
                )
        return self


def _is_topic_eligible_for_sku(
    arc: StoryArc,
    topic: StoryTopic,
    active_sku_id: str,
) -> bool:
    """Kiểm tra chủ đề có hợp lệ cho `active_sku_id` mà không rò rỉ sang SKU khác (`I-04`)."""
    if topic.sku_id is not None:
        return topic.sku_id == active_sku_id
    if arc.sku_id is not None:
        return arc.sku_id == active_sku_id
    # Chủ đề mở đầu/chuyển chung (`arc.sku_id is None` và `topic.sku_id is None`) không gắn SKU xung đột.
    return True


class ArcSequencer:
    """Bộ chọn chủ đề tất định theo thứ tự `StoryArc` với khóa `active_sku_id` (`I-04`)."""

    @staticmethod
    def select_next_topic(
        story_plan: StoryPlan,
        checkpoint: StoryCheckpoint,
        active_sku_id: str,
        completed_topic_ids: AbstractSet[str],
        excluded_topic_ids: AbstractSet[str] = frozenset(),
        include_optional: bool = True,
    ) -> TopicSelectionResult:
        """Chọn chủ đề kế tiếp hợp lệ cho `active_sku_id` mà không đột biến trạng thái đầu vào.

        Args:
            story_plan: Kế hoạch kể chuyện đã được phê duyệt (`APPROVED`).
            checkpoint: Điểm dừng `StoryCheckpoint` hiện hành của phiên.
            active_sku_id: Mã SKU đang hoạt động do P08 chỉ định (P06 chỉ đọc).
            completed_topic_ids: Tập `topic_id` đã hoàn tất (từ `PlaybackCompleted` ACK).
            excluded_topic_ids: Tập `topic_id` cần tạm bỏ qua (ví dụ khi đổi chủ đề/đã thử thất bại).
            include_optional: Nếu `False`, chỉ xét các chủ đề có `is_mandatory=True`.

        Returns:
            TopicSelectionResult: Chủ đề được chọn kèm con trỏ kế tiếp, hoặc `should_terminate=True`.

        Raises:
            ValueError: Nếu `story_plan` chưa `APPROVED`, lệch tenant/session/plan với `checkpoint`,
                hoặc vi phạm bất biến `I-04` (`active_sku_id` ngoài `pinned_sku_ids` / lệch checkpoint).
        """
        if story_plan.approval_status != StoryPlanApprovalStatus.APPROVED:
            raise ValueError(
                f"ArcSequencer chỉ nhận StoryPlan ở trạng thái APPROVED, nhận được "
                f"'{story_plan.approval_status.value}'."
            )
        if not isinstance(active_sku_id, str) or not active_sku_id.strip():
            raise ValueError("active_sku_id không được rỗng.")
        if (
            checkpoint.tenant_id != story_plan.tenant_id
            or checkpoint.session_id != story_plan.session_id
        ):
            raise ValueError(
                "StoryCheckpoint không khớp (tenant_id, session_id) với StoryPlan."
            )
        if (
            checkpoint.plan_id != story_plan.plan_id
            or checkpoint.plan_revision != story_plan.plan_revision
        ):
            raise ValueError(
                "StoryCheckpoint không khớp (plan_id, plan_revision) với StoryPlan."
            )
        if active_sku_id not in story_plan.pinned_sku_ids:
            raise ValueError(
                f"Vi phạm I-04: active_sku_id='{active_sku_id}' không nằm trong "
                f"pinned_sku_ids={story_plan.pinned_sku_ids}."
            )
        if checkpoint.active_sku_id != active_sku_id:
            raise ValueError(
                f"Vi phạm I-04: checkpoint.active_sku_id='{checkpoint.active_sku_id}' "
                f"không khớp active_sku_id='{active_sku_id}'."
            )

        blocked_ids = frozenset(completed_topic_ids) | frozenset(excluded_topic_ids)
        ordered_arcs = sorted(story_plan.arcs, key=lambda arc: arc.position)

        eligible_remaining: list[tuple[StoryArc, StoryTopic]] = [
            (arc, topic)
            for arc in ordered_arcs
            for topic in arc.topics
            if _is_topic_eligible_for_sku(arc, topic, active_sku_id)
            and topic.topic_id not in blocked_ids
            and (include_optional or topic.is_mandatory)
        ]

        if not eligible_remaining:
            termination_reason = (
                "ALL_ELIGIBLE_TOPICS_COMPLETED"
                if not excluded_topic_ids
                else "ALL_ELIGIBLE_TOPICS_COMPLETED_OR_EXCLUDED"
            )
            return TopicSelectionResult(
                should_terminate=True,
                termination_reason=termination_reason,
            )

        # Ưu tiên giữ đúng mạch checkpoint.next_topic_id nếu chủ đề đó vẫn hợp lệ cho active_sku_id.
        selected_pair: Optional[tuple[StoryArc, StoryTopic]] = None
        if checkpoint.next_topic_id is not None:
            for pair in eligible_remaining:
                if pair[1].topic_id == checkpoint.next_topic_id:
                    selected_pair = pair
                    break

        # Nếu không bám được checkpoint (None, đã hoàn tất hoặc bị loại trừ), ưu tiên chủ đề bắt buộc trước.
        prioritized_remaining: list[tuple[StoryArc, StoryTopic]] = [
            pair for pair in eligible_remaining if pair[1].is_mandatory
        ] + [pair for pair in eligible_remaining if not pair[1].is_mandatory]

        if selected_pair is None:
            selected_pair = prioritized_remaining[0]

        selected_arc, selected_topic = selected_pair
        selected_plan_idx = eligible_remaining.index(selected_pair)

        remaining_after = [
            pair for pair in prioritized_remaining if pair[1].topic_id != selected_topic.topic_id
        ]

        if not remaining_after:
            next_topic_id: Optional[str] = None
            next_arc_id: Optional[str] = None
        else:
            # Ưu tiên chọn chủ đề nằm sau vị trí hiện tại theo thứ tự kế hoạch trước khi vòng lại phần còn thiếu.
            plan_index_by_topic_id = {
                pair[1].topic_id: idx for idx, pair in enumerate(eligible_remaining)
            }
            following_candidates = [
                pair
                for pair in remaining_after
                if plan_index_by_topic_id[pair[1].topic_id] > selected_plan_idx
            ]
            next_arc, next_topic = (
                following_candidates[0] if following_candidates else remaining_after[0]
            )
            next_topic_id = next_topic.topic_id
            next_arc_id = next_arc.arc_id

        return TopicSelectionResult(
            selected_arc_id=selected_arc.arc_id,
            selected_topic=selected_topic,
            next_topic_id_after_selection=next_topic_id,
            next_arc_id_after_selection=next_arc_id,
            should_terminate=False,
        )
