"""Triển khai baseline lập kịch bản trước toàn phiên (`ScriptFirstBaseline`) cho thí nghiệm P06-E01.

1. File này giải quyết vấn đề gì?
   Cung cấp đối chứng thực nghiệm (`Script-First Baseline`) so sánh với agent tự chủ LangGraph:
   toàn bộ lời thoại của các chủ đề thuộc `active_sku_id` được sinh một lần trước khi phiên phát
   bắt đầu, sau đó phát tuần tự mù mà không đọc `played_history` để tái lập kế hoạch hay viết lại.
2. Trách nhiệm chính của module là gì?
   Định nghĩa hợp đồng DTO untrusted `UpfrontChunkDraftLLMOutput`, các mô hình kết quả/chỉ số
   (`BaselineScriptSource`, `BaselineMetrics`, `BaselineTurnRecord`, `BaselineSessionResult`),
   và lớp `ScriptFirstBaseline` với hai chế độ nguồn kịch bản (`UPFRONT_LLM` và
   `DETERMINISTIC_TALKING_POINTS`).
3. Module này liên kết với các thành phần nào?
   Tái sử dụng hợp đồng từ `p06.schemas`, cổng `KnowledgeVerifierPort` và `PlaybackAckBusPort`
   (`p06.adapters.interfaces`), `LLMProvider` (`p06.providers.base`), `SafeFallbackSelector`
   (`p06.guardrails.fallback_selector`), `SimulatedPlaybackHarness` và `VirtualClock` (`p06.simulation`).
4. Input và output chính là gì?
   Input là `StoryPlan` đã `APPROVED`, `active_sku_id` hợp lệ từ `StoryCheckpoint`, và các tùy chọn
   giả lập ACK theo lượt; Output là `UpfrontScriptPlan` (sau bước chuẩn bị) và `BaselineSessionResult`
   (sau bước phát tuần tự kèm `BaselineMetrics` có provenance rõ ràng).
5. Có những constraints hoặc invariants quan trọng nào?
   - Tuyệt đối không dùng `played_history` để tái lập kế hoạch, không chạy `RepetitionDetector` hay
     `bounded_rewrite` (`rewrite_attempt` luôn là `0`).
   - Bất biến `I-04`: Không bao giờ tự ý đổi `active_sku_id`; phải khớp `harness.checkpoint.active_sku_id`
     và thuộc `story_plan.pinned_sku_ids`.
   - Tách trạng thái `Generated != Verified != Played`: mọi ứng viên trước khi phát bắt buộc qua P05
     (`verify_candidate`) và tiến độ chỉ cập nhật qua `SimulatedPlaybackHarness.apply_ack()`.
   - Cấm `model_copy(update=...)` và cấm bịa token `0` khi telemetry là `UNAVAILABLE`.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any, Final, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError, model_validator

from p06.adapters.interfaces import (
    AckApplyStatus,
    KnowledgeVerifierPort,
    PlaybackAckBusPort,
    PlaybackAckResult,
    SkuEvidenceView,
)
from p06.guardrails.fallback_selector import SafeFallbackSelector
from p06.providers.base import (
    GenerationRequest,
    LLMProvider,
    ProviderError,
    ProviderTelemetry,
    StrictNonNegFloat,
    TokenUsageSource,
)
from p06.schemas.candidate import (
    CandidateOrigin,
    CandidateVerificationStatus,
    CoverageMode,
    ProposedResponseCoverage,
    SpeechCandidate,
    TargetScopeMode,
)
from p06.schemas.events import PlaybackOutcomeStatus, StoryCheckpoint
from p06.schemas.state import AgentTurnOutcome
from p06.schemas.story import (
    BreakpointType,
    MAX_CHUNK_DURATION_SEC,
    NonBlankStr,
    OptionalNonBlankStr,
    StoryArc,
    StoryChunk,
    StoryChunkRole,
    StoryPlan,
    StoryPlanApprovalStatus,
    StoryTopic,
    StrictNonNegInt,
    StrictPositivePriceVnd,
)
from p06.simulation.playback_harness import SimulatedPlaybackHarness
from p06.simulation.virtual_clock import DEFAULT_SPEECH_WORDS_PER_SEC, VirtualClock

# Giới hạn số từ mục tiêu khi ghép kịch bản tất định để thời lượng đọc luôn nằm gọn dưới ngưỡng 30s.
_DETERMINISTIC_MAX_WORDS: Final[int] = int(MAX_CHUNK_DURATION_SEC * DEFAULT_SPEECH_WORDS_PER_SEC) - 6
_UPFRONT_PROMPT_VERSION: Final[str] = "baseline-script-first-v0.1"
_UPFRONT_SYSTEM_PROMPT_TEMPLATE: Final[str] = (
    "Bạn là trợ lý viết kịch bản livestream tiếng Việt trung thực với dữ liệu. "
    "Chỉ sử dụng thông tin trong `sku_evidence` và `topic`, giữ độ dài dưới {max_words} từ "
    "(<= {max_duration_sec} giây đọc), trích dẫn đúng `evidence_id` từ `approved_chunks`, không bịa giá "
    "hoặc công dụng chữa bệnh, và tuyệt đối không nhắc tên SKU khác."
)
_UPFRONT_PROMPT_SHA256: Final[str] = hashlib.sha256(
    _UPFRONT_SYSTEM_PROMPT_TEMPLATE.encode("utf-8")
).hexdigest()


class BaselineScriptSource(str, Enum):
    """Nguồn sinh kịch bản đầu phiên của `ScriptFirstBaseline`.

    Attributes:
        UPFRONT_LLM: Gọi `LLMProvider.generate_structured` trước khi phát cho từng chủ đề hợp lệ.
        DETERMINISTIC_TALKING_POINTS: Ghép thoại tiếng Việt tất định trực tiếp từ `talking_points`
            và `SkuEvidenceView` đã kiểm chứng, không gọi LLM và không chép transcript tham chiếu.
    """

    UPFRONT_LLM = "UPFRONT_LLM"
    DETERMINISTIC_TALKING_POINTS = "DETERMINISTIC_TALKING_POINTS"


class UpfrontChunkDraftLLMOutput(BaseModel):
    """DTO đầu ra có cấu trúc không đáng tin cậy từ LLM cho một chunk kịch bản đầu phiên.

    Lý do tách biệt: Không chứa bất kỳ trường thẩm quyền nào như `verified`, `gate_decision_id`
    hay `tenant_id` nhằm bảo đảm bất biến `Generated != Verified` (`I-02`).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    text: NonBlankStr
    role: StoryChunkRole = StoryChunkRole.PRODUCT_STORY
    cited_evidence_ids: list[NonBlankStr] = Field(default_factory=list)
    stated_price_vnd: Optional[StrictPositivePriceVnd] = None
    mentions_ocop: StrictBool = False
    semantic_breakpoint: StrictBool = True
    breakpoint_type: BreakpointType = BreakpointType.TOPIC_END
    rationale: OptionalNonBlankStr = None


class BaselineMetrics(BaseModel):
    """Tổng hợp chỉ số thực nghiệm của một lượt chạy `ScriptFirstBaseline` với provenance trung thực.

    Attributes:
        script_source: Nguồn kịch bản đã sử dụng (`UPFRONT_LLM` hoặc `DETERMINISTIC_TALKING_POINTS`).
        total_topics_planned: Tổng số chủ đề thuộc `active_sku_id` được lập kịch bản đầu phiên.
        turns_attempted: Số lượt phát đã thử thực thi tuần tự.
        verified_ready_count: Số lượt ứng viên gốc vượt qua Cổng P05 (`VERIFIED_READY`).
        fallback_count: Số lượt phải chuyển sang câu dự phòng (`FALLBACK_PREAPPROVED`).
        safe_abort_count: Số lượt hủy an toàn do cả ứng viên gốc lẫn dự phòng đều trượt (`SAFE_ABORT_NO_CANDIDATE`).
        playback_applied_count: Số lượt nhận ACK `COMPLETED` và được harness ghi nhận `APPLIED`.
        llm_calls: Tổng số lần gọi `LLMProvider` trong giai đoạn chuẩn bị kịch bản.
        input_tokens: Tổng token đầu vào (`None` khi `token_usage_source == UNAVAILABLE`).
        output_tokens: Tổng token đầu ra (`None` khi `token_usage_source == UNAVAILABLE`).
        token_usage_source: Nguồn gốc thống kê token (`UNAVAILABLE`, `SIMULATED`, hoặc `MEASURED`).
        planning_latency_ms: Tổng độ trễ sinh kịch bản đầu phiên tính bằng mili-giây.
        generation_latency_ms: Độ trễ sinh thoại động trong lúc phát (luôn `0.0` ở baseline tĩnh).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    script_source: BaselineScriptSource
    total_topics_planned: StrictNonNegInt
    turns_attempted: StrictNonNegInt
    verified_ready_count: StrictNonNegInt
    fallback_count: StrictNonNegInt
    safe_abort_count: StrictNonNegInt
    playback_applied_count: StrictNonNegInt
    llm_calls: StrictNonNegInt
    input_tokens: Optional[StrictNonNegInt] = None
    output_tokens: Optional[StrictNonNegInt] = None
    token_usage_source: TokenUsageSource
    planning_latency_ms: StrictNonNegFloat = 0.0
    generation_latency_ms: StrictNonNegFloat = 0.0

    @model_validator(mode="after")
    def validate_metrics_consistency(self) -> BaselineMetrics:
        """Bảo đảm tính nhất quán giữa số lượng lượt, số gọi LLM và provenance của token."""
        outcome_sum = self.verified_ready_count + self.fallback_count + self.safe_abort_count
        if outcome_sum != self.turns_attempted:
            raise ValueError(
                f"Tổng verified_ready + fallback + safe_abort ({outcome_sum}) phải bằng "
                f"turns_attempted ({self.turns_attempted})."
            )
        if self.playback_applied_count > (self.verified_ready_count + self.fallback_count):
            raise ValueError(
                "playback_applied_count không thể vượt quá số lượt đã gửi phát tới bus."
            )
        if self.llm_calls == 0 and self.token_usage_source != TokenUsageSource.UNAVAILABLE:
            raise ValueError(
                "Khi llm_calls == 0, token_usage_source bắt buộc phải là UNAVAILABLE."
            )
        if self.token_usage_source == TokenUsageSource.UNAVAILABLE:
            if self.input_tokens is not None or self.output_tokens is not None:
                raise ValueError(
                    "Khi token_usage_source == UNAVAILABLE, input_tokens và output_tokens phải là None."
                )
        else:
            if self.input_tokens is None or self.output_tokens is None:
                raise ValueError(
                    f"Khi token_usage_source == {self.token_usage_source.value}, "
                    "input_tokens và output_tokens không được để None."
                )
        return self


class BaselineTurnRecord(BaseModel):
    """Bản ghi kết quả từng lượt phát tuần tự trong `ScriptFirstBaseline`."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    turn_index: StrictNonNegInt
    turn_id: NonBlankStr
    topic_id: NonBlankStr
    arc_id: NonBlankStr
    chunk_id: NonBlankStr
    outcome: AgentTurnOutcome
    verified_candidate_id: OptionalNonBlankStr = None
    ack_status: Optional[AckApplyStatus] = None
    failure_reason: OptionalNonBlankStr = None
    spoken_text: OptionalNonBlankStr = None
    cited_evidence_ids: tuple[NonBlankStr, ...] = ()
    actual_duration_ms: Optional[StrictNonNegInt] = None
    p05_rejected: StrictBool = False
    p05_rejection_reasons: tuple[NonBlankStr, ...] = ()
    p05_gate_decision_id: OptionalNonBlankStr = None
    candidate_text_before_fallback: OptionalNonBlankStr = None
    covered_claim_ids: tuple[NonBlankStr, ...] = ()

    @model_validator(mode="after")
    def validate_turn_record_invariants(self) -> BaselineTurnRecord:
        """Kiểm định tính nhất quán giữa `outcome`, `verified_candidate_id`, `ack_status` và `failure_reason`."""
        if self.outcome == AgentTurnOutcome.IN_PROGRESS:
            raise ValueError("BaselineTurnRecord không được mang outcome=IN_PROGRESS.")
        if self.outcome == AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE:
            if self.verified_candidate_id is not None:
                raise ValueError(
                    "SAFE_ABORT_NO_CANDIDATE bắt buộc verified_candidate_id phải là None."
                )
            if self.ack_status is not None:
                raise ValueError(
                    "SAFE_ABORT_NO_CANDIDATE không được gửi tới bus nên ack_status phải là None."
                )
            if self.failure_reason is None:
                raise ValueError("SAFE_ABORT_NO_CANDIDATE bắt buộc phải có failure_reason.")
        else:
            if self.verified_candidate_id is None:
                raise ValueError(
                    f"outcome={self.outcome.value} bắt buộc phải có verified_candidate_id."
                )
            if self.ack_status is None:
                raise ValueError(
                    f"outcome={self.outcome.value} bắt buộc phải có ack_status sau khi gửi bus."
                )
        return self


class BaselineSessionResult(BaseModel):
    """Kết quả tổng thể sau khi `ScriptFirstBaseline` hoàn tất chạy toàn bộ kịch bản đầu phiên."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    turns: tuple[BaselineTurnRecord, ...]
    metrics: BaselineMetrics
    final_checkpoint: StoryCheckpoint
    completed_topic_ids: frozenset[str]
    played_history_count: StrictNonNegInt
    telemetry_records: tuple[ProviderTelemetry, ...] = ()
    prompt_version: OptionalNonBlankStr = None
    prompt_sha256: OptionalNonBlankStr = None
    playback_events: tuple[PlaybackAckResult, ...] = ()
    discarded_candidates: tuple[dict[str, Any], ...] = ()
    errors: tuple[dict[str, Any], ...] = ()


class UpfrontPlannedItem(BaseModel):
    """Một đơn vị kịch bản được chuẩn bị sẵn đầu phiên cho một `(StoryArc, StoryTopic)` hợp lệ."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    arc: StoryArc
    topic: StoryTopic
    planned_chunk_id: NonBlankStr
    chunk: Optional[StoryChunk] = None
    candidate: Optional[SpeechCandidate] = None
    generation_error: OptionalNonBlankStr = None

    @model_validator(mode="after")
    def validate_item_consistency(self) -> UpfrontPlannedItem:
        """Đảm bảo mục đã lập hoặc có đủ `(chunk, candidate)` nháp hoặc có `generation_error`."""
        if self.generation_error is None:
            if self.chunk is None or self.candidate is None:
                raise ValueError(
                    "UpfrontPlannedItem không có lỗi sinh bắt buộc phải có đủ chunk và candidate."
                )
            if self.candidate.verification_status != CandidateVerificationStatus.DRAFT:
                raise ValueError(
                    "Ứng viên lập trước đầu phiên bắt buộc phải ở trạng thái DRAFT."
                )
            if self.candidate.rewrite_attempt != 0:
                raise ValueError(
                    "ScriptFirstBaseline không chạy bounded rewrite nên rewrite_attempt phải là 0."
                )
        else:
            if self.chunk is not None or self.candidate is not None:
                raise ValueError(
                    "UpfrontPlannedItem có generation_error không được gắn kèm chunk hoặc candidate."
                )
        return self


class UpfrontScriptPlan(BaseModel):
    """Toàn bộ kịch bản đã dựng sẵn trước khi bất kỳ lượt phát nào diễn ra."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    plan_id: NonBlankStr
    plan_revision: int
    active_sku_id: NonBlankStr
    script_source: BaselineScriptSource
    items: tuple[UpfrontPlannedItem, ...]
    llm_calls: StrictNonNegInt = 0
    input_tokens: Optional[StrictNonNegInt] = None
    output_tokens: Optional[StrictNonNegInt] = None
    token_usage_source: TokenUsageSource = TokenUsageSource.UNAVAILABLE
    planning_latency_ms: StrictNonNegFloat = 0.0
    telemetry_records: tuple[ProviderTelemetry, ...] = ()
    prompt_version: OptionalNonBlankStr = None
    prompt_sha256: OptionalNonBlankStr = None


def _format_vnd_price(price_vnd: int) -> str:
    """Định dạng số nguyên giá VNĐ theo chuẩn phân tách dấu chấm dễ đọc cho tiếng Việt."""
    return f"{price_vnd:,}".replace(",", ".") + "đ"


def _join_bounded_clauses(clauses: Sequence[str], max_words: int) -> str:
    """Ghép các mệnh đề tiếng Việt sao cho tổng số từ không vượt quá ngân sách thời lượng 30s."""
    selected: list[str] = []
    word_count = 0
    for raw_clause in clauses:
        cleaned = raw_clause.strip()
        if not cleaned:
            continue
        if cleaned[-1] not in ".!?":
            cleaned = f"{cleaned}."
        clause_words = len(cleaned.split())
        if selected and (word_count + clause_words) > max_words:
            break
        if not selected and clause_words > max_words:
            # Cắt tại ranh giới từ nếu mệnh đề đơn lẻ đầu tiên quá dài để giữ ngưỡng <= 30s.
            trimmed = " ".join(cleaned.split()[:max_words]).rstrip(",;:")
            if trimmed and trimmed[-1] not in ".!?":
                trimmed = f"{trimmed}."
            selected.append(trimmed)
            break
        selected.append(cleaned)
        word_count += clause_words
    return " ".join(selected)


def _compose_deterministic_chunk(
    topic: StoryTopic,
    evidence_view: SkuEvidenceView,
    *,
    max_words: int = _DETERMINISTIC_MAX_WORDS,
    chunk_part: int = 0,
) -> tuple[str, list[str], int, bool]:
    """Ghép lời thoại tiếng Việt tất định từ `talking_points` và `SkuEvidenceView` đã duyệt.

    Lý do thiết kế: Không sao chép hay hardcode bất kỳ transcript mẫu nào trong `data/story_plans/`;
    chỉ dùng trực tiếp `sku_name`, `origin`, `price_vnd`, `topic.talking_points` và `fact_refs`
    khớp với `evidence_view.approved_chunks`. Khi `chunk_part > 0` (`min_chunks_per_topic > 1`),
    xoay vòng `talking_points` và `matching_chunks` để sinh lời thoại tiếp nối tự nhiên.
    """
    chunks_by_id = {chunk["evidence_id"]: chunk for chunk in evidence_view.approved_chunks}
    matching_chunks = [chunks_by_id[eid] for eid in topic.fact_refs if eid in chunks_by_id]

    if matching_chunks:
        cited_evidence_ids = [chunk["evidence_id"] for chunk in matching_chunks]
        first_matching_chunk = matching_chunks[chunk_part % len(matching_chunks)]
    elif not topic.fact_refs and evidence_view.approved_chunks:
        first_matching_chunk = evidence_view.approved_chunks[
            chunk_part % len(evidence_view.approved_chunks)
        ]
        cited_evidence_ids = [first_matching_chunk["evidence_id"]]
    else:
        # Giữ nguyên fact_refs gốc nếu không khớp approved_chunks để cổng P05 tự chặn fail-closed.
        cited_evidence_ids = list(topic.fact_refs)
        first_matching_chunk = None

    price_text = _format_vnd_price(evidence_view.price_vnd)
    if chunk_part == 0:
        clauses: list[str] = [
            f"{evidence_view.sku_name}, xuất xứ {evidence_view.origin}, giá niêm yết {price_text}"
        ]
    else:
        clauses = [
            f"Phần {chunk_part + 1} - {evidence_view.sku_name} ({price_text})"
        ]

    if topic.talking_points:
        shift = chunk_part % len(topic.talking_points)
        rotated_points = list(topic.talking_points[shift:]) + list(topic.talking_points[:shift])
        clauses.extend(rotated_points)
    else:
        clauses.append(topic.title)

    if first_matching_chunk is not None and len(" ".join(clauses).split()) < max(0, max_words - 12):
        clauses.append(first_matching_chunk["content"])

    composed_text = _join_bounded_clauses(clauses, max_words=max_words)
    mentions_ocop = "ocop" in composed_text.lower()
    return composed_text, cited_evidence_ids, evidence_view.price_vnd, mentions_ocop


class _TelemetryAccumulator:
    """Bộ cộng dồn telemetry gọi LLM bảo toàn nguyên tắc trung thực provenance token."""

    def __init__(self) -> None:
        self.llm_calls: int = 0
        self.planning_latency_ms: float = 0.0
        self.records: list[ProviderTelemetry] = []
        self._input_tokens: int = 0
        self._output_tokens: int = 0
        self._has_unavailable: bool = False
        self._saw_simulated: bool = False
        self._saw_measured: bool = False

    def record(self, telemetry: Optional[ProviderTelemetry]) -> None:
        """Ghi nhận một lượt gọi LLM (thành công hoặc lỗi có gắn telemetry)."""
        self.llm_calls += 1
        if telemetry is None:
            self._has_unavailable = True
            return

        self.records.append(telemetry)
        self.planning_latency_ms += telemetry.latency_ms
        if (
            telemetry.token_usage_source == TokenUsageSource.UNAVAILABLE
            or telemetry.input_tokens is None
            or telemetry.output_tokens is None
        ):
            self._has_unavailable = True
            return

        self._input_tokens += telemetry.input_tokens
        self._output_tokens += telemetry.output_tokens
        if telemetry.token_usage_source == TokenUsageSource.SIMULATED:
            self._saw_simulated = True
        elif telemetry.token_usage_source == TokenUsageSource.MEASURED:
            self._saw_measured = True

    def finalize(self) -> tuple[Optional[int], Optional[int], TokenUsageSource]:
        """Trả về `(input_tokens, output_tokens, token_usage_source)` tuân thủ provenance."""
        if self.llm_calls == 0 or self._has_unavailable:
            return None, None, TokenUsageSource.UNAVAILABLE
        # Nếu có bất kỳ lượt gọi mô phỏng nào thì toàn phiên phải gắn SIMULATED, tuyệt đối không gắn MEASURED.
        if self._saw_simulated:
            return self._input_tokens, self._output_tokens, TokenUsageSource.SIMULATED
        if self._saw_measured:
            return self._input_tokens, self._output_tokens, TokenUsageSource.MEASURED
        return None, None, TokenUsageSource.UNAVAILABLE


class ScriptFirstBaseline:
    """Baseline lập kịch bản một lần đầu phiên rồi phát tuần tự mù (`Script-First Baseline`).

    Đặc tính thực nghiệm phục vụ E01:
    - Sinh toàn bộ `StoryChunk` và `SpeechCandidate(DRAFT, rewrite_attempt=0)` trước khi phát lượt 0.
    - Không đọc `played_history`, không chạy `RepetitionDetector`, không chạy `bounded_rewrite`.
    - Vẫn giữ nguyên ranh giới an toàn hệ thống: `I-04` (không tự đổi `active_sku_id`),
      `I-02` (mọi lượt đều qua `KnowledgeVerifierPort.verify_candidate`), `SafeFallbackSelector`
      (khi bị P05 từ chối hoặc lỗi sinh), và `I-06` (`SimulatedPlaybackHarness.apply_ack`).
    """

    def __init__(
        self,
        knowledge_verifier: KnowledgeVerifierPort,
        playback_bus: PlaybackAckBusPort,
        harness: SimulatedPlaybackHarness,
        clock: VirtualClock,
        llm_provider: Optional[LLMProvider] = None,
        fallback_candidates: Sequence[SpeechCandidate] = (),
        script_source: BaselineScriptSource = BaselineScriptSource.DETERMINISTIC_TALKING_POINTS,
        session_rights_version: int = 1,
        data_classification: str = "SYNTHETIC",
        seed: Optional[int] = None,
        max_chunk_duration_sec: float = MAX_CHUNK_DURATION_SEC,
        min_chunks_per_topic: int = 1,
    ) -> None:
        """Khởi tạo `ScriptFirstBaseline` với các cổng phụ thuộc tiêm từ ngoài.

        Args:
            knowledge_verifier: Cổng kiểm chứng tri thức P05 (`KnowledgeVerifierPort`).
            playback_bus: Bus gửi phát sóng và nhận ACK P04 (`PlaybackAckBusPort`).
            harness: Bộ điều phối checkpoint và lịch sử phát (`SimulatedPlaybackHarness`).
            clock: Đồng hồ ảo UTC phục vụ mốc thời gian kiểm định và phát sóng.
            llm_provider: Nhà cung cấp LLM (bắt buộc khi `script_source == UPFRONT_LLM`).
            fallback_candidates: Danh sách câu dự phòng `PREAPPROVED_FALLBACK` theo thứ tự ưu tiên.
            script_source: Chế độ sinh kịch bản đầu phiên (`UPFRONT_LLM` hoặc `DETERMINISTIC_TALKING_POINTS`).
            session_rights_version: Phiên bản quyền sử dụng presenter/asset cấp phiên (`>= 1`).
            data_classification: Nhãn phân loại dữ liệu truyền vào `GenerationRequest`.
            seed: Hạt giống ngẫu nhiên tùy chọn truyền cho `GenerationRequest`.

        Raises:
            ValueError: Nếu tham số cấu hình sai kiểu/biên hoặc chọn `UPFRONT_LLM` nhưng thiếu `llm_provider`.
        """
        if not isinstance(script_source, BaselineScriptSource):
            script_source = BaselineScriptSource(script_source)
        if script_source == BaselineScriptSource.UPFRONT_LLM and llm_provider is None:
            raise ValueError("Chế độ UPFRONT_LLM bắt buộc phải cung cấp llm_provider khác None.")
        if isinstance(session_rights_version, bool) or session_rights_version < 1:
            raise ValueError(
                f"session_rights_version phải là số nguyên >= 1, nhận được {session_rights_version}."
            )
        if not isinstance(data_classification, str) or not data_classification.strip():
            raise ValueError("data_classification không được rỗng.")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
            raise ValueError("seed phải là số nguyên hoặc None.")
        if (
            isinstance(max_chunk_duration_sec, bool)
            or not isinstance(max_chunk_duration_sec, (int, float))
            or not math.isfinite(float(max_chunk_duration_sec))
        ):
            raise ValueError(
                f"max_chunk_duration_sec phải là số thực hữu hạn, nhận được {max_chunk_duration_sec!r}."
            )
        numeric_duration = float(max_chunk_duration_sec)
        if not (0.0 < numeric_duration <= MAX_CHUNK_DURATION_SEC):
            raise ValueError(
                f"max_chunk_duration_sec phải nằm trong (0.0, {MAX_CHUNK_DURATION_SEC}], "
                f"nhận được {numeric_duration}."
            )
        if isinstance(min_chunks_per_topic, bool) or not isinstance(min_chunks_per_topic, int) or min_chunks_per_topic < 1:
            raise ValueError(
                f"min_chunks_per_topic phải là số nguyên >= 1, nhận được {min_chunks_per_topic!r}."
            )

        self._knowledge_verifier = knowledge_verifier
        self._playback_bus = playback_bus
        self._harness = harness
        self._clock = clock
        self._llm_provider = llm_provider
        self._fallback_candidates: tuple[SpeechCandidate, ...] = tuple(fallback_candidates)
        self._script_source = script_source
        self._session_rights_version = session_rights_version
        self._data_classification = data_classification.strip()
        self._seed = seed
        self._max_chunk_duration_sec: float = numeric_duration
        self._min_chunks_per_topic: int = min_chunks_per_topic
        margin_words = 6 if numeric_duration >= 20.0 else 3
        self._max_words: int = max(
            6,
            int(numeric_duration * DEFAULT_SPEECH_WORDS_PER_SEC) - margin_words,
        )

    def prepare_upfront_script(
        self,
        story_plan: StoryPlan,
        active_sku_id: str,
    ) -> UpfrontScriptPlan:
        """Chuẩn bị toàn bộ `StoryChunk` và `SpeechCandidate(DRAFT)` trước khi phiên phát bắt đầu.

        Lưu ý kiến trúc: Phương thức này tuyệt đối không đọc `harness.played_history` hay
        `harness.completed_topic_ids` để điều chỉnh kế hoạch.

        Args:
            story_plan: Kế hoạch kể chuyện đã ở trạng thái `APPROVED`.
            active_sku_id: Mã SKU đang active từ P08 (bắt buộc thuộc `pinned_sku_ids` và khớp checkpoint).

        Returns:
            UpfrontScriptPlan: Kịch bản dựng sẵn theo thứ tự `(arc.position, topic order)`.

        Raises:
            ValueError: Nếu `story_plan` chưa `APPROVED`, lệch tenant/session/plan với checkpoint,
                hoặc `active_sku_id` vi phạm bất biến `I-04` / không nằm trong `pinned_sku_ids`.
        """
        if self._script_source == BaselineScriptSource.UPFRONT_LLM and self._llm_provider is None:
            raise ValueError("Chế độ UPFRONT_LLM bắt buộc phải có llm_provider.")

        self._validate_plan_and_active_sku(story_plan=story_plan, active_sku_id=active_sku_id)

        eligible_pairs = self._select_eligible_topics(story_plan=story_plan, active_sku_id=active_sku_id)
        expanded_pairs: list[tuple[StoryArc, StoryTopic, int]] = [
            (arc, topic, part_idx)
            for arc, topic in eligible_pairs
            for part_idx in range(self._min_chunks_per_topic)
        ]
        last_index_by_arc: dict[str, int] = {}
        for seq_idx, (arc, _topic, _part_idx) in enumerate(expanded_pairs):
            last_index_by_arc[arc.arc_id] = seq_idx

        evidence_view: Optional[SkuEvidenceView] = None
        evidence_error: Optional[str] = None
        try:
            evidence_view = self._knowledge_verifier.get_sku_evidence(
                story_plan.tenant_id,
                active_sku_id,
                at_time=self._clock.now(),
            )
        except (KeyError, PermissionError, ValueError) as exc:
            evidence_error = f"{type(exc).__name__}: {exc}"

        telemetry_acc = _TelemetryAccumulator()
        items: list[UpfrontPlannedItem] = []

        for seq_idx, (arc, topic, chunk_part) in enumerate(expanded_pairs):
            planned_chunk_id = (
                f"chunk-baseline-{story_plan.plan_id}-r{story_plan.plan_revision}-"
                f"{active_sku_id}-{seq_idx:03d}"
            )
            if evidence_view is None:
                items.append(
                    UpfrontPlannedItem(
                        arc=arc,
                        topic=topic,
                        planned_chunk_id=planned_chunk_id,
                        generation_error=evidence_error or "Không truy xuất được SkuEvidenceView.",
                    )
                )
                continue

            item = self._build_upfront_item(
                story_plan=story_plan,
                active_sku_id=active_sku_id,
                arc=arc,
                topic=topic,
                sequence_index=seq_idx,
                planned_chunk_id=planned_chunk_id,
                is_last_in_arc=(last_index_by_arc.get(arc.arc_id) == seq_idx),
                evidence_view=evidence_view,
                telemetry_acc=telemetry_acc,
                chunk_part=chunk_part,
            )
            items.append(item)

        in_tokens, out_tokens, token_source = telemetry_acc.finalize()
        return UpfrontScriptPlan(
            plan_id=story_plan.plan_id,
            plan_revision=story_plan.plan_revision,
            active_sku_id=active_sku_id,
            script_source=self._script_source,
            items=tuple(items),
            llm_calls=telemetry_acc.llm_calls,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            token_usage_source=token_source,
            planning_latency_ms=telemetry_acc.planning_latency_ms,
            telemetry_records=tuple(telemetry_acc.records),
            prompt_version=(
                _UPFRONT_PROMPT_VERSION
                if self._script_source == BaselineScriptSource.UPFRONT_LLM
                else "deterministic-talking-points-v0.1"
            ),
            prompt_sha256=(
                _UPFRONT_PROMPT_SHA256
                if self._script_source == BaselineScriptSource.UPFRONT_LLM
                else None
            ),
        )

    def run_session(
        self,
        story_plan: StoryPlan,
        active_sku_id: Optional[str] = None,
        *,
        outcome_overrides_by_turn: Optional[Mapping[int, PlaybackOutcomeStatus]] = None,
        max_turns: Optional[int] = None,
        target_duration_sec: Optional[float] = None,
        max_consecutive_aborts: Optional[int] = None,
        initial_consecutive_aborts: int = 0,
    ) -> BaselineSessionResult:
        """Chạy tuần tự kịch bản đã dựng sẵn đầu phiên qua P05 -> P04 bus -> Harness.

        Args:
            story_plan: Kế hoạch kể chuyện đã được `APPROVED`.
            active_sku_id: Mã SKU active (mặc định đọc từ `harness.checkpoint.active_sku_id`).
            outcome_overrides_by_turn: Bản đồ `turn_index -> PlaybackOutcomeStatus` để mô phỏng
                lỗi `FAILED` hoặc `UNKNOWN` trên từng lượt cụ thể.
            max_turns: Giới hạn số lượt tối đa trong lần chạy SKU này (tùy chọn).
            target_duration_sec: Ngưỡng thời lượng ảo phiên để dừng ngay trước khi phát lượt tiếp.
            max_consecutive_aborts: Số lượt `SAFE_ABORT_NO_CANDIDATE` liên tiếp tối đa cho phép.
            initial_consecutive_aborts: Số lượt abort liên tiếp tích lũy từ các SKU trước đó.

        Returns:
            BaselineSessionResult: Kết quả từng lượt, `BaselineMetrics`, `StoryCheckpoint` cuối,
                tập `completed_topic_ids` và tổng `played_history_count`.
        """
        resolved_sku_id = (
            active_sku_id if active_sku_id is not None else self._harness.checkpoint.active_sku_id
        )
        prepared = self.prepare_upfront_script(story_plan=story_plan, active_sku_id=resolved_sku_id)

        turns: list[BaselineTurnRecord] = []
        playback_events: list[PlaybackAckResult] = []
        discarded_candidates: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        verified_ready_count = 0
        fallback_count = 0
        safe_abort_count = 0
        playback_applied_count = 0
        consecutive_aborts = initial_consecutive_aborts

        total_items = len(prepared.items)
        for turn_index, item in enumerate(prepared.items):
            # Kiểm tra các rào dừng TRƯỚC khi tạo/phát lượt mới để VirtualClock không bị trượt lố.
            if max_consecutive_aborts is not None and consecutive_aborts >= max_consecutive_aborts:
                break
            if max_turns is not None and len(turns) >= max_turns:
                break
            if target_duration_sec is not None and self._clock.elapsed_sec() >= target_duration_sec:
                break

            turn_id = self._allocate_turn_id(story_plan=story_plan, turn_index=turn_index)
            (
                selected_candidate,
                outcome,
                rejection_note,
                p05_rejected,
                p05_reasons,
                p05_gate_decision_id,
                candidate_text_before_fallback,
            ) = self._resolve_turn_candidate(
                item=item,
                story_plan=story_plan,
            )

            if p05_rejected or item.generation_error is not None:
                discarded_candidates.append(
                    {
                        "turn_id": turn_id,
                        "topic_id": item.topic.topic_id,
                        "arc_id": item.arc.arc_id,
                        "chunk_id": item.planned_chunk_id,
                        "text": candidate_text_before_fallback,
                        "generation_error": item.generation_error,
                        "p05_rejected": p05_rejected,
                        "p05_reasons": list(p05_reasons),
                    }
                )
                errors.append(
                    {
                        "turn_id": turn_id,
                        "stage": "verify_p05" if p05_rejected else "upfront_generation",
                        "error_type": "P05_REJECTED" if p05_rejected else "GENERATION_ERROR",
                        "message": rejection_note or item.generation_error or "Unknown baseline failure",
                        "topic_id": item.topic.topic_id,
                        "sku_id": resolved_sku_id,
                    }
                )

            if outcome == AgentTurnOutcome.VERIFIED_READY:
                verified_ready_count += 1
                consecutive_aborts = 0
            elif outcome == AgentTurnOutcome.FALLBACK_PREAPPROVED:
                fallback_count += 1
                consecutive_aborts = 0
            else:
                safe_abort_count += 1
                consecutive_aborts += 1
                errors.append(
                    {
                        "turn_id": turn_id,
                        "stage": "safe_fallback",
                        "error_type": "SAFE_ABORT_NO_CANDIDATE",
                        "message": rejection_note or "No valid candidate or fallback.",
                        "topic_id": item.topic.topic_id,
                        "sku_id": resolved_sku_id,
                    }
                )
                turns.append(
                    BaselineTurnRecord(
                        turn_index=turn_index,
                        turn_id=turn_id,
                        topic_id=item.topic.topic_id,
                        arc_id=item.arc.arc_id,
                        chunk_id=item.planned_chunk_id,
                        outcome=AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE,
                        verified_candidate_id=None,
                        ack_status=None,
                        failure_reason=rejection_note,
                        p05_rejected=p05_rejected,
                        p05_rejection_reasons=p05_reasons,
                        p05_gate_decision_id=p05_gate_decision_id,
                        candidate_text_before_fallback=candidate_text_before_fallback,
                    )
                )
                continue

            assert selected_candidate is not None
            if turn_index + 1 < total_items:
                next_item = prepared.items[turn_index + 1]
                next_topic_id: Optional[str] = next_item.topic.topic_id
                next_arc_id: str = next_item.arc.arc_id
            else:
                next_topic_id = None
                next_arc_id = item.arc.arc_id

            turn_claim_ids = (
                tuple(item.topic.allowed_claim_ids)
                if outcome == AgentTurnOutcome.VERIFIED_READY
                else ()
            )
            # Truyền đúng source_chunk_id của ứng viên đã chọn (PROACTIVE_STORY hoặc PREAPPROVED_FALLBACK)
            # để khớp với PlaybackCompleted.chunk_id do MockPlaybackAckBus phát hành.
            self._harness.register_pending_turn(
                turn_id=turn_id,
                candidate=selected_candidate,
                plan_revision=story_plan.plan_revision,
                chunk_id=selected_candidate.source_chunk_id,
                next_topic_id=next_topic_id,
                current_arc_id=next_arc_id,
                covered_claim_ids=turn_claim_ids,
            )

            override_status = (
                outcome_overrides_by_turn.get(turn_index)
                if outcome_overrides_by_turn is not None
                else None
            )
            ack_result = self._playback_bus.dispatch_turn(
                candidate=selected_candidate,
                turn_id=turn_id,
                plan_revision=story_plan.plan_revision,
                outcome_override=override_status,
            )
            playback_events.append(ack_result)
            apply_result = self._harness.apply_ack(ack_result)
            if apply_result.applied:
                playback_applied_count += 1
                turn_failure_reason: Optional[str] = None
            else:
                turn_failure_reason = apply_result.reason or ack_result.failure_reason
                errors.append(
                    {
                        "turn_id": turn_id,
                        "stage": "playback_ack",
                        "error_type": f"PLAYBACK_{apply_result.status.value}",
                        "message": turn_failure_reason or "Playback ACK rejected/ignored",
                        "topic_id": item.topic.topic_id,
                        "sku_id": resolved_sku_id,
                    }
                )

            cited_ids: tuple[str, ...] = ()
            if selected_candidate.sku_bindings:
                cited_ids = tuple(selected_candidate.sku_bindings[0].cited_evidence_ids)
            actual_duration_ms = (
                ack_result.event.actual_duration_ms if ack_result.event is not None else None
            )
            turns.append(
                BaselineTurnRecord(
                    turn_index=turn_index,
                    turn_id=turn_id,
                    topic_id=item.topic.topic_id,
                    arc_id=item.arc.arc_id,
                    chunk_id=selected_candidate.source_chunk_id or item.planned_chunk_id,
                    outcome=outcome,
                    verified_candidate_id=selected_candidate.candidate_id,
                    ack_status=apply_result.status,
                    failure_reason=turn_failure_reason,
                    spoken_text=selected_candidate.text,
                    cited_evidence_ids=cited_ids,
                    actual_duration_ms=actual_duration_ms,
                    p05_rejected=p05_rejected,
                    p05_rejection_reasons=p05_reasons,
                    p05_gate_decision_id=p05_gate_decision_id,
                    candidate_text_before_fallback=candidate_text_before_fallback,
                    covered_claim_ids=turn_claim_ids,
                )
            )

        metrics = BaselineMetrics(
            script_source=prepared.script_source,
            total_topics_planned=total_items,
            turns_attempted=len(turns),
            verified_ready_count=verified_ready_count,
            fallback_count=fallback_count,
            safe_abort_count=safe_abort_count,
            playback_applied_count=playback_applied_count,
            llm_calls=prepared.llm_calls,
            input_tokens=prepared.input_tokens,
            output_tokens=prepared.output_tokens,
            token_usage_source=prepared.token_usage_source,
            planning_latency_ms=prepared.planning_latency_ms,
            generation_latency_ms=0.0,
        )
        return BaselineSessionResult(
            turns=tuple(turns),
            metrics=metrics,
            final_checkpoint=self._harness.checkpoint,
            completed_topic_ids=self._harness.completed_topic_ids,
            played_history_count=len(self._harness.played_history),
            telemetry_records=prepared.telemetry_records,
            prompt_version=prepared.prompt_version,
            prompt_sha256=prepared.prompt_sha256,
            playback_events=tuple(playback_events),
            discarded_candidates=tuple(discarded_candidates),
            errors=tuple(errors),
        )

    def _validate_plan_and_active_sku(self, story_plan: StoryPlan, active_sku_id: str) -> None:
        """Kiểm định kế hoạch đã duyệt, khóa bất biến `I-04` và tính đồng bộ với checkpoint."""
        if story_plan.approval_status != StoryPlanApprovalStatus.APPROVED:
            raise ValueError(
                f"ScriptFirstBaseline yêu cầu StoryPlan ở trạng thái APPROVED, hiện tại là "
                f"'{story_plan.approval_status.value}'."
            )
        if not isinstance(active_sku_id, str) or not active_sku_id.strip():
            raise ValueError("active_sku_id không được rỗng.")
        if active_sku_id not in story_plan.pinned_sku_ids:
            raise ValueError(
                f"active_sku_id='{active_sku_id}' không nằm trong story_plan.pinned_sku_ids."
            )

        cp = self._harness.checkpoint
        if active_sku_id != cp.active_sku_id:
            raise ValueError(
                f"Vi phạm bất biến I-04: active_sku_id='{active_sku_id}' không khớp với "
                f"harness.checkpoint.active_sku_id='{cp.active_sku_id}'."
            )
        if story_plan.tenant_id != cp.tenant_id or story_plan.session_id != cp.session_id:
            raise ValueError(
                "StoryPlan không khớp tenant_id hoặc session_id với harness.checkpoint."
            )
        if story_plan.plan_id != cp.plan_id or story_plan.plan_revision != cp.plan_revision:
            raise ValueError(
                "StoryPlan không khớp plan_id hoặc plan_revision với harness.checkpoint."
            )

    @staticmethod
    def _select_eligible_topics(
        story_plan: StoryPlan,
        active_sku_id: str,
    ) -> list[tuple[StoryArc, StoryTopic]]:
        """Lọc các cặp `(arc, topic)` hợp lệ cho `active_sku_id` đồng bộ quy tắc `ArcSequencer` (`I-04`)."""
        eligible: list[tuple[StoryArc, StoryTopic]] = []
        for arc in sorted(story_plan.arcs, key=lambda item: item.position):
            for topic in arc.topics:
                if topic.sku_id == active_sku_id or (
                    topic.sku_id is None and (arc.sku_id == active_sku_id or arc.sku_id is None)
                ):
                    eligible.append((arc, topic))
        return eligible

    def _build_upfront_item(
        self,
        *,
        story_plan: StoryPlan,
        active_sku_id: str,
        arc: StoryArc,
        topic: StoryTopic,
        sequence_index: int,
        planned_chunk_id: str,
        is_last_in_arc: bool,
        evidence_view: SkuEvidenceView,
        telemetry_acc: _TelemetryAccumulator,
        chunk_part: int = 0,
    ) -> UpfrontPlannedItem:
        """Tạo một `UpfrontPlannedItem` từ LLM đầu phiên hoặc trình ghép tất định."""
        if self._script_source == BaselineScriptSource.UPFRONT_LLM:
            assert self._llm_provider is not None
            request = self._build_upfront_llm_request(
                story_plan=story_plan,
                active_sku_id=active_sku_id,
                arc=arc,
                topic=topic,
                evidence_view=evidence_view,
                chunk_part=chunk_part,
            )
            try:
                gen_result = self._llm_provider.generate_structured(
                    request,
                    UpfrontChunkDraftLLMOutput,
                )
                telemetry_acc.record(gen_result.telemetry)
                llm_out = gen_result.parsed_output
                text = llm_out.text
                role = llm_out.role
                cited_evidence_ids = list(llm_out.cited_evidence_ids)
                stated_price_vnd = llm_out.stated_price_vnd
                mentions_ocop = llm_out.mentions_ocop
                semantic_breakpoint = llm_out.semantic_breakpoint
                breakpoint_type = llm_out.breakpoint_type
                rationale = llm_out.rationale
            except ProviderError as exc:
                telemetry_acc.record(exc.telemetry)
                return UpfrontPlannedItem(
                    arc=arc,
                    topic=topic,
                    planned_chunk_id=planned_chunk_id,
                    generation_error=f"{type(exc).__name__}: {exc}",
                )
        else:
            text, cited_evidence_ids, stated_price_vnd, mentions_ocop = _compose_deterministic_chunk(
                topic=topic,
                evidence_view=evidence_view,
                max_words=self._max_words,
                chunk_part=chunk_part,
            )
            role = StoryChunkRole.OPENING if sequence_index == 0 else StoryChunkRole.PRODUCT_STORY
            semantic_breakpoint = True
            breakpoint_type = (
                arc.breakpoint_hint if is_last_in_arc else BreakpointType.TOPIC_END
            )
            rationale = f"Ghép tất định từ talking_points của chủ đề '{topic.topic_id}'."

        estimated_duration_sec = VirtualClock.estimate_raw_speech_duration_ms(text) / 1000.0
        if (
            self._script_source == BaselineScriptSource.UPFRONT_LLM
            and estimated_duration_sec > self._max_chunk_duration_sec
        ):
            return UpfrontPlannedItem(
                arc=arc,
                topic=topic,
                planned_chunk_id=planned_chunk_id,
                generation_error=(
                    f"OVER_MAX_DURATION_SEC: Thời lượng ước lượng {estimated_duration_sec:.2f}s "
                    f"vượt quá giới hạn {self._max_chunk_duration_sec:.2f}s."
                ),
            )
        intent = f"story_topic:{topic.topic_id}"
        candidate_id = (
            f"cand-baseline-{story_plan.plan_id}-r{story_plan.plan_revision}-"
            f"{active_sku_id}-{sequence_index:03d}"
        )

        try:
            chunk = StoryChunk(
                chunk_id=planned_chunk_id,
                plan_id=story_plan.plan_id,
                plan_revision=story_plan.plan_revision,
                arc_id=arc.arc_id,
                topic_id=topic.topic_id,
                sequence_index=sequence_index,
                role=role,
                sku_id=active_sku_id,
                text=text,
                cited_evidence_ids=cited_evidence_ids,
                estimated_duration_sec=estimated_duration_sec,
                semantic_breakpoint=semantic_breakpoint,
                breakpoint_type=breakpoint_type,
                rationale=rationale,
            )
            binding = evidence_view.to_version_binding(
                cited_evidence_ids=cited_evidence_ids,
                stated_price_vnd=stated_price_vnd,
                mentions_ocop=mentions_ocop,
            )
            candidate = SpeechCandidate(
                candidate_id=candidate_id,
                tenant_id=story_plan.tenant_id,
                session_id=story_plan.session_id,
                session_epoch=self._harness.checkpoint.session_epoch,
                origin=CandidateOrigin.PROACTIVE_STORY,
                source_chunk_id=chunk.chunk_id,
                scope_mode=TargetScopeMode.SINGLE_SKU,
                sku_refs=[active_sku_id],
                sku_bindings=[binding],
                session_rights_version=self._session_rights_version,
                intent=intent,
                text=chunk.text,
                semantic_breakpoint=chunk.semantic_breakpoint,
                estimated_duration_sec=chunk.estimated_duration_sec,
                proposed_coverage=ProposedResponseCoverage(
                    covered_topic_ids=[topic.topic_id],
                    covered_intents=[intent],
                    coverage_mode=CoverageMode.FULL,
                ),
                verification_status=CandidateVerificationStatus.DRAFT,
                rewrite_attempt=0,
            )
        except ValidationError as exc:
            return UpfrontPlannedItem(
                arc=arc,
                topic=topic,
                planned_chunk_id=planned_chunk_id,
                generation_error=f"ValidationError: {exc}",
            )

        return UpfrontPlannedItem(
            arc=arc,
            topic=topic,
            planned_chunk_id=planned_chunk_id,
            chunk=chunk,
            candidate=candidate,
        )

    def _build_upfront_llm_request(
        self,
        *,
        story_plan: StoryPlan,
        active_sku_id: str,
        arc: StoryArc,
        topic: StoryTopic,
        evidence_view: SkuEvidenceView,
        chunk_part: int = 0,
    ) -> GenerationRequest:
        """Tạo `GenerationRequest` có cấu trúc cho lượt gọi LLM chuẩn bị đầu phiên."""
        system_prompt = _UPFRONT_SYSTEM_PROMPT_TEMPLATE.format(
            max_words=self._max_words,
            max_duration_sec=f"{self._max_chunk_duration_sec:g}",
        )
        user_payload: dict[str, Any] = {
            "session_goal": story_plan.session_goal,
            "chunk_part_index": chunk_part,
            "min_chunks_per_topic": self._min_chunks_per_topic,
            "arc": {
                "arc_id": arc.arc_id,
                "position": arc.position,
                "title": arc.title,
            },
            "topic": {
                "topic_id": topic.topic_id,
                "title": topic.title,
                "fact_refs": list(topic.fact_refs),
                "allowed_claim_ids": list(topic.allowed_claim_ids),
                "talking_points": list(topic.talking_points),
            },
            "sku_evidence": {
                "sku_id": evidence_view.sku_id,
                "sku_name": evidence_view.sku_name,
                "price_vnd": evidence_view.price_vnd,
                "origin": evidence_view.origin,
                "weight_display": evidence_view.weight_display,
                "expiry_display": evidence_view.expiry_display,
                "approved_chunks": list(evidence_view.approved_chunks),
                "allowed_claims": list(evidence_view.allowed_claims),
                "prohibited_claims": list(evidence_view.prohibited_claims),
            },
        }
        part_suffix = f"-p{chunk_part}" if chunk_part > 0 else ""
        return GenerationRequest(
            request_id=(
                f"upfront-{story_plan.plan_id}-r{story_plan.plan_revision}-"
                f"{arc.arc_id}-{topic.topic_id}{part_suffix}"
            ),
            system_prompt=system_prompt,
            user_prompt=json.dumps(user_payload, ensure_ascii=False),
            prompt_version=_UPFRONT_PROMPT_VERSION,
            data_classification=self._data_classification,
            seed=self._seed,
            metadata={
                "fixture_key": topic.topic_id,
                "topic_id": topic.topic_id,
                "arc_id": arc.arc_id,
                "sku_id": active_sku_id,
                "chunk_part": chunk_part,
                "min_chunks_per_topic": self._min_chunks_per_topic,
            },
        )

    def _resolve_turn_candidate(
        self,
        *,
        item: UpfrontPlannedItem,
        story_plan: StoryPlan,
    ) -> tuple[
        Optional[SpeechCandidate],
        AgentTurnOutcome,
        Optional[str],
        bool,
        tuple[str, ...],
        Optional[str],
        Optional[str],
    ]:
        """Kiểm định ứng viên đầu phiên qua P05 hoặc rơi về `SafeFallbackSelector` / safe abort."""
        primary_failure_reason: Optional[str] = item.generation_error
        p05_rejected = False
        p05_reasons: tuple[str, ...] = ()
        p05_gate_decision_id: Optional[str] = None
        candidate_text_before_fallback: Optional[str] = (
            item.candidate.text if item.candidate is not None else None
        )

        if item.candidate is not None:
            ver_result = self._knowledge_verifier.verify_candidate(
                item.candidate,
                verified_at=self._clock.now(),
            )
            if (
                ver_result.status == CandidateVerificationStatus.VERIFIED
                and ver_result.candidate.is_ready_for_tts()
            ):
                return (
                    ver_result.candidate,
                    AgentTurnOutcome.VERIFIED_READY,
                    None,
                    False,
                    (),
                    ver_result.gate_decision_id,
                    candidate_text_before_fallback,
                )
            p05_rejected = True
            p05_reasons = tuple(ver_result.reasons) or ("P05_REJECTED_UNSPECIFIED",)
            primary_failure_reason = f"P05 REJECTED: {', '.join(p05_reasons)}"

        fallback = SafeFallbackSelector.select_safe_fallback(
            self._knowledge_verifier,
            self._fallback_candidates,
            verified_at=self._clock.now(),
            tenant_id=story_plan.tenant_id,
            session_id=story_plan.session_id,
            session_epoch=self._harness.checkpoint.session_epoch,
            require_empty_covered_topics=True,
        )
        if fallback is not None:
            return (
                fallback,
                AgentTurnOutcome.FALLBACK_PREAPPROVED,
                primary_failure_reason,
                p05_rejected,
                p05_reasons,
                p05_gate_decision_id,
                candidate_text_before_fallback,
            )

        abort_reason = (
            f"{primary_failure_reason}; không có câu dự phòng hợp lệ."
            if primary_failure_reason
            else "Không có ứng viên hoặc câu dự phòng hợp lệ."
        )
        return (
            None,
            AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE,
            abort_reason,
            p05_rejected,
            p05_reasons,
            p05_gate_decision_id,
            candidate_text_before_fallback,
        )

    def _allocate_turn_id(self, *, story_plan: StoryPlan, turn_index: int) -> str:
        """Sinh `turn_id` tất định và bảo đảm không trùng với các lượt đã đăng ký/kết thúc."""
        epoch = self._harness.checkpoint.session_epoch
        base = f"turn-baseline-{story_plan.plan_id}-e{epoch}-{turn_index:04d}"
        if (
            base not in self._harness.pending_turn_ids
            and base not in self._harness.finalized_turn_ids
        ):
            return base
        suffix = 1
        while True:
            candidate = f"{base}-n{suffix}"
            if (
                candidate not in self._harness.pending_turn_ids
                and candidate not in self._harness.finalized_turn_ids
            ):
                return candidate
            suffix += 1
