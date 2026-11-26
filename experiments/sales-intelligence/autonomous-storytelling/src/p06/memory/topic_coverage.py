"""Bộ theo dõi độ phủ chủ đề toàn cục (`GlobalTopicCoverage`) tách bạch đề xuất, kiểm chứng và hoàn tất phát sóng.

1. File này giải quyết vấn đề gì?
   Ngăn lỗi đếm ảo độ phủ chủ đề khi LLM mới sinh bản nháp hoặc P05 mới duyệt ứng viên nhưng âm thanh
   chưa phát tới người xem, đồng thời giữ bền vững tiến độ phủ chủ đề trên toàn bộ phiên live ngay cả
   khi cửa sổ `ShortTermPlayedHistory` trượt qua nhiều lượt.
2. Trách nhiệm chính của module là gì?
   Quản lý vòng đời độ phủ chủ đề gắn chặt với `(tenant_id, session_id, plan_id, plan_revision)`:
   tách riêng `proposed_topic_ids`, `verified_topic_ids` và `completed_topic_ids` (chỉ thăng hạng
   khi `PlaybackCompleted` hợp lệ đạt ngưỡng `min_chunks_per_topic`), đồng thời xuất `TopicCoverageSnapshot`.
3. Module này liên kết với các thành phần nào?
   Nhập `StoryPlan`, `PlaybackCompleted` từ `p06.schemas`; phối hợp với `SimulatedPlaybackHarness`
   (`p06.simulation`) và các metrics đánh giá độ phủ chủ đề bắt buộc trong E01–E04.
4. Input và output chính là gì?
   Input là `StoryPlan`, các `topic_id` đề xuất/đã duyệt (phi thẩm quyền) và sự kiện `PlaybackCompleted`
   (có thẩm quyền);
   Output là tập `completed_topic_ids`, danh sách chủ đề bắt buộc còn lại và `TopicCoverageSnapshot`.
5. Có những constraints hoặc invariants quan trọng nào?
   - `record_proposed_topics` và `record_verified_topics` KHÔNG BAO GIỜ thay đổi `completed_topic_ids`.
   - `record_playback_completed` bất biến theo `playback_event_id` (idempotent), từ chối sự kiện
     lệch `tenant_id`, `session_id`, `plan_revision` hoặc chứa `topic_id` ngoài `StoryPlan`.
   - Một `topic_id` chỉ được tính vào `completed_topic_ids` khi số lượt phát xác nhận đạt
     `>= min_chunks_per_topic`.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from p06.schemas.events import PlaybackCompleted
from p06.schemas.story import (
    NonBlankStr,
    StoryPlan,
    StrictNonNegInt,
    StrictPositiveInt,
)


def _validate_unit_ratio(value: Any) -> float:
    """Kiểm định tỷ lệ độ phủ nằm trong `[0.0, 1.0]` và từ chối kiểu `bool`."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"mandatory_coverage_ratio phải là số thực trong [0.0, 1.0], nhận được {type(value).__name__}."
        )
    numeric = float(value)
    if not math.isfinite(numeric) or not (0.0 <= numeric <= 1.0):
        raise ValueError(f"mandatory_coverage_ratio phải nằm trong [0.0, 1.0], nhận được {value!r}.")
    return numeric


StrictUnitRatio = Annotated[float, BeforeValidator(_validate_unit_ratio)]


def _normalize_topic_ids(topic_ids: Iterable[str], planned_topic_ids: frozenset[str]) -> list[str]:
    """Chuẩn hóa danh sách `topic_id` và kiểm tra toàn bộ đều thuộc `StoryPlan`."""
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_id in topic_ids:
        if not isinstance(raw_id, str) or not raw_id.strip():
            raise ValueError(f"topic_id phải là chuỗi khác rỗng, nhận được {raw_id!r}.")
        clean_id = raw_id.strip()
        if clean_id not in planned_topic_ids:
            raise ValueError(
                f"topic_id '{clean_id}' không tồn tại trong StoryPlan."
            )
        if clean_id not in seen:
            seen.add(clean_id)
            normalized.append(clean_id)
    return normalized


class TopicCoverageSnapshot(BaseModel):
    """Ảnh chụp bất biến trạng thái độ phủ chủ đề tại một thời điểm của phiên live.

    Attributes:
        tenant_id: Mã tenant sở hữu kế hoạch.
        session_id: Mã phiên livestream gắn với kế hoạch.
        plan_id: Mã `StoryPlan` đang theo dõi.
        plan_revision: Phiên bản `StoryPlan` đang theo dõi.
        planned_topic_ids: Toàn bộ `topic_id` có trong `StoryPlan`.
        mandatory_topic_ids: Tập `topic_id` đánh dấu `is_mandatory=True`.
        proposed_topic_ids: Tập `topic_id` từng được LLM/candidate đề xuất (chưa chứng minh đã phát).
        verified_topic_ids: Tập `topic_id` từng vượt qua P05 (chưa chứng minh đã phát).
        played_chunk_counts_by_topic: Số lượt `PlaybackCompleted` xác nhận cho từng `topic_id`.
        completed_topic_ids: Tập `topic_id` đã hoàn tất thực sự (`count >= min_chunks_per_topic`).
        remaining_mandatory_topic_ids: Tập chủ đề bắt buộc chưa hoàn tất.
        completed_mandatory_count: Tử số độ phủ chủ đề bắt buộc đã hoàn tất.
        total_mandatory_count: Mẫu số tổng số chủ đề bắt buộc trong `StoryPlan`.
        mandatory_coverage_ratio: Tỷ lệ `completed_mandatory_count / total_mandatory_count`.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    tenant_id: NonBlankStr
    session_id: NonBlankStr
    plan_id: NonBlankStr
    plan_revision: StrictPositiveInt
    planned_topic_ids: frozenset[NonBlankStr]
    mandatory_topic_ids: frozenset[NonBlankStr] = Field(default_factory=frozenset)
    proposed_topic_ids: frozenset[NonBlankStr] = Field(default_factory=frozenset)
    verified_topic_ids: frozenset[NonBlankStr] = Field(default_factory=frozenset)
    played_chunk_counts_by_topic: dict[NonBlankStr, StrictNonNegInt] = Field(default_factory=dict)
    completed_topic_ids: frozenset[NonBlankStr] = Field(default_factory=frozenset)
    remaining_mandatory_topic_ids: frozenset[NonBlankStr] = Field(default_factory=frozenset)
    completed_mandatory_count: StrictNonNegInt
    total_mandatory_count: StrictNonNegInt
    mandatory_coverage_ratio: StrictUnitRatio


class GlobalTopicCoverage:
    """Bộ theo dõi độ phủ chủ đề toàn cục xuyên suốt phiên cho một `(StoryPlan, plan_revision)`."""

    def __init__(
        self,
        story_plan: StoryPlan,
        initial_completed_topic_ids: Iterable[str] = (),
        min_chunks_per_topic: int = 1,
    ) -> None:
        """Khởi tạo bộ theo dõi độ phủ gắn chặt với ngữ cảnh và revision của `StoryPlan`.

        Args:
            story_plan: Kế hoạch kể chuyện gốc định nghĩa toàn bộ `topic_id` hợp lệ.
            initial_completed_topic_ids: Tập `topic_id` đã hoàn tất trước khi phục hồi phiên.
            min_chunks_per_topic: Số lượt phát xác nhận tối thiểu để coi một topic là hoàn tất (>= 1).

        Raises:
            TypeError: Nếu `story_plan` không phải `StoryPlan`.
            ValueError: Nếu `min_chunks_per_topic < 1` (hoặc `bool`), hay `initial_completed_topic_ids`
                chứa `topic_id` nằm ngoài `story_plan.all_topic_ids()`.
        """
        if not isinstance(story_plan, StoryPlan):
            raise TypeError(
                f"story_plan phải là StoryPlan, nhận được {type(story_plan).__name__}."
            )
        if isinstance(min_chunks_per_topic, bool) or not isinstance(min_chunks_per_topic, int) or min_chunks_per_topic < 1:
            raise ValueError(
                f"min_chunks_per_topic phải là số nguyên >= 1, nhận được {min_chunks_per_topic!r}."
            )

        self._tenant_id: str = story_plan.tenant_id
        self._session_id: str = story_plan.session_id
        self._plan_id: str = story_plan.plan_id
        self._plan_revision: int = story_plan.plan_revision
        self._min_chunks_per_topic: int = min_chunks_per_topic

        self._planned_topic_ids: frozenset[str] = frozenset(story_plan.all_topic_ids())
        self._mandatory_topic_ids: frozenset[str] = frozenset(story_plan.mandatory_topic_ids())

        initial_normalized = _normalize_topic_ids(initial_completed_topic_ids, self._planned_topic_ids)

        self._proposed_topic_ids: set[str] = set()
        self._verified_topic_ids: set[str] = set()
        self._completed_topic_ids: set[str] = set(initial_normalized)
        self._played_chunk_counts_by_topic: dict[str, int] = {
            topic_id: 0 for topic_id in self._planned_topic_ids
        }
        # Đồng bộ bộ đếm ban đầu với các topic đã hoàn tất trước đó khi khôi phục phiên.
        for topic_id in self._completed_topic_ids:
            self._played_chunk_counts_by_topic[topic_id] = self._min_chunks_per_topic
        self._seen_event_ids: set[str] = set()

    @property
    def tenant_id(self) -> str:
        """Mã tenant gắn với bộ theo dõi độ phủ."""
        return self._tenant_id

    @property
    def session_id(self) -> str:
        """Mã phiên gắn với bộ theo dõi độ phủ."""
        return self._session_id

    @property
    def plan_id(self) -> str:
        """Mã `StoryPlan` gắn với bộ theo dõi độ phủ."""
        return self._plan_id

    @property
    def plan_revision(self) -> int:
        """Phiên bản `StoryPlan` gắn với bộ theo dõi độ phủ."""
        return self._plan_revision

    @property
    def min_chunks_per_topic(self) -> int:
        """Ngưỡng số lượt phát xác nhận tối thiểu để hoàn tất một chủ đề."""
        return self._min_chunks_per_topic

    @property
    def planned_topic_ids(self) -> frozenset[str]:
        """Toàn bộ tập `topic_id` có trong kế hoạch."""
        return self._planned_topic_ids

    @property
    def mandatory_topic_ids(self) -> frozenset[str]:
        """Tập `topic_id` bắt buộc phải phủ trong phiên."""
        return self._mandatory_topic_ids

    @property
    def proposed_topic_ids(self) -> frozenset[str]:
        """Tập `topic_id` đã từng được đề xuất bởi candidate (phi thẩm quyền)."""
        return frozenset(self._proposed_topic_ids)

    @property
    def verified_topic_ids(self) -> frozenset[str]:
        """Tập `topic_id` đã từng qua cổng P05 (phi thẩm quyền cho tới khi có ACK phát sóng)."""
        return frozenset(self._verified_topic_ids)

    @property
    def completed_topic_ids(self) -> frozenset[str]:
        """Tập `topic_id` đã được xác nhận hoàn tất phát sóng thực tế."""
        return frozenset(self._completed_topic_ids)

    @property
    def remaining_mandatory_topic_ids(self) -> frozenset[str]:
        """Tập `topic_id` bắt buộc chưa hoàn tất phát sóng."""
        return self._mandatory_topic_ids - self._completed_topic_ids

    @property
    def played_chunk_counts_by_topic(self) -> dict[str, int]:
        """Bản sao ánh xạ `topic_id -> số lượt đã phát xác nhận`."""
        return dict(self._played_chunk_counts_by_topic)

    @property
    def completed_mandatory_count(self) -> int:
        """Số lượng chủ đề bắt buộc đã hoàn tất."""
        return len(self._mandatory_topic_ids & self._completed_topic_ids)

    @property
    def total_mandatory_count(self) -> int:
        """Tổng số chủ đề bắt buộc trong kế hoạch."""
        return len(self._mandatory_topic_ids)

    @property
    def mandatory_coverage_ratio(self) -> float:
        """Tỷ lệ hoàn thành chủ đề bắt buộc trong `[0.0, 1.0]`."""
        total = self.total_mandatory_count
        if total == 0:
            return 1.0
        return self.completed_mandatory_count / total

    def record_proposed_topics(self, topic_ids: Iterable[str]) -> None:
        """Ghi nhận phi thẩm quyền các `topic_id` vừa được candidate/LLM đề xuất.

        Không bao giờ cập nhật `completed_topic_ids` vì lời thoại chưa qua P05 và chưa phát.

        Args:
            topic_ids: Tập mã chủ đề dự kiến phủ của bản nháp.

        Raises:
            ValueError: Nếu có `topic_id` rỗng hoặc không thuộc `StoryPlan`.
        """
        valid_ids = _normalize_topic_ids(topic_ids, self._planned_topic_ids)
        self._proposed_topic_ids.update(valid_ids)

    def record_verified_topics(self, topic_ids: Iterable[str]) -> None:
        """Ghi nhận phi thẩm quyền các `topic_id` trên ứng viên đã đạt P05 `VERIFIED`.

        Không bao giờ cập nhật `completed_topic_ids` vì ứng viên `VERIFIED` vẫn có thể bị lỗi
        hoặc gián đoạn trước khi hoàn tất phát sóng (`I-03`).

        Args:
            topic_ids: Tập mã chủ đề gắn trên ứng viên đã duyệt P05.

        Raises:
            ValueError: Nếu có `topic_id` rỗng hoặc không thuộc `StoryPlan`.
        """
        valid_ids = _normalize_topic_ids(topic_ids, self._planned_topic_ids)
        self._verified_topic_ids.update(valid_ids)

    def record_playback_completed(
        self,
        event: PlaybackCompleted,
        plan_revision: int,
    ) -> frozenset[str]:
        """Cập nhật độ phủ có thẩm quyền từ sự kiện `PlaybackCompleted` (idempotent & nguyên tử).

        Args:
            event: Sự kiện xác nhận phát sóng hợp lệ.
            plan_revision: Phiên bản `StoryPlan` gắn với lượt phát vừa hoàn tất.

        Returns:
            frozenset[str]: Tập các `topic_id` vừa mới đạt ngưỡng `min_chunks_per_topic`
                để thăng hạng vào `completed_topic_ids` trong lần gọi này (rỗng nếu sự kiện
                trùng lặp hoặc các chủ đề chưa đủ ngưỡng lượt phát).

        Raises:
            TypeError: Nếu `event` không phải `PlaybackCompleted`.
            ValueError: Nếu lệch `tenant_id`, `session_id`, `plan_revision`, hoặc chứa
                `topic_id` nằm ngoài `StoryPlan`.
        """
        if not isinstance(event, PlaybackCompleted):
            raise TypeError(
                f"event phải là PlaybackCompleted, nhận được {type(event).__name__}."
            )
        if isinstance(plan_revision, bool) or not isinstance(plan_revision, int) or plan_revision < 1:
            raise ValueError(
                f"plan_revision phải là số nguyên >= 1, nhận được {plan_revision!r}."
            )

        if event.tenant_id != self._tenant_id:
            raise ValueError(
                f"Lệch tenant_id trên PlaybackCompleted: nhận '{event.tenant_id}', "
                f"kỳ vọng '{self._tenant_id}'."
            )
        if event.session_id != self._session_id:
            raise ValueError(
                f"Lệch session_id trên PlaybackCompleted: nhận '{event.session_id}', "
                f"kỳ vọng '{self._session_id}'."
            )
        if plan_revision != self._plan_revision:
            raise ValueError(
                f"Lệch plan_revision: nhận {plan_revision}, kỳ vọng {self._plan_revision}."
            )

        # Kiểm tra hợp lệ toàn bộ topic trước để từ chối sạch nếu payload sai dù sự kiện hợp lệ nguồn.
        unique_confirmed_topics = _normalize_topic_ids(
            event.confirmed_topic_ids,
            self._planned_topic_ids,
        )

        # Bất biến idempotency: cùng playback_event_id chỉ cộng điểm độ phủ đúng một lần.
        if event.playback_event_id in self._seen_event_ids:
            return frozenset()

        newly_completed: set[str] = set()
        for topic_id in unique_confirmed_topics:
            new_count = self._played_chunk_counts_by_topic[topic_id] + 1
            self._played_chunk_counts_by_topic[topic_id] = new_count
            if new_count >= self._min_chunks_per_topic and topic_id not in self._completed_topic_ids:
                self._completed_topic_ids.add(topic_id)
                newly_completed.add(topic_id)

        self._seen_event_ids.add(event.playback_event_id)
        return frozenset(newly_completed)

    def snapshot(self) -> TopicCoverageSnapshot:
        """Xuất bản chụp bất biến trạng thái độ phủ chủ đề hiện hành."""
        return TopicCoverageSnapshot(
            tenant_id=self._tenant_id,
            session_id=self._session_id,
            plan_id=self._plan_id,
            plan_revision=self._plan_revision,
            planned_topic_ids=self._planned_topic_ids,
            mandatory_topic_ids=self._mandatory_topic_ids,
            proposed_topic_ids=frozenset(self._proposed_topic_ids),
            verified_topic_ids=frozenset(self._verified_topic_ids),
            played_chunk_counts_by_topic=dict(self._played_chunk_counts_by_topic),
            completed_topic_ids=frozenset(self._completed_topic_ids),
            remaining_mandatory_topic_ids=self.remaining_mandatory_topic_ids,
            completed_mandatory_count=self.completed_mandatory_count,
            total_mandatory_count=self.total_mandatory_count,
            mandatory_coverage_ratio=self.mandatory_coverage_ratio,
        )
