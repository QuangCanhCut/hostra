"""Hợp đồng dữ liệu bất biến cho hệ thống đánh giá P06 (`p06.evaluation.models`).

1. File này giải quyết vấn đề gì?
   Định nghĩa các DTO Pydantic v2 chuẩn hóa cho raw evidence, kết quả từng metric có
   truy vết nguồn gốc (`provenance`), báo cáo đánh giá một lần chạy, báo cáo so sánh
   nhiều lần chạy và phiếu xuất chấm mù cho con người.
2. Trách nhiệm chính của module là gì?
   Khóa chặt schema trao đổi giữa tầng thu thập (`runner`) và tầng tính toán (`evaluation/metrics`,
   `evaluator`, `comparison`, `human_eval`), đồng thời ép buộc quy tắc không giả lập `0` cho dữ liệu thiếu.
3. Module này liên kết với các thành phần nào?
   Sử dụng `StoryPlan`, `NonBlankStr`, `OptionalNonBlankStr`, `StrictNonNegInt` từ `p06.schemas.story`
   và `StrictNonNegFloat` từ `p06.providers.base`.
4. Input và output chính là gì?
   Input là dữ liệu từ file JSONL/JSON trong thư mục run hoặc cấu trúc in-memory;
   Output là các đối tượng bất biến (`frozen=True`, `extra="forbid"`).
5. Có những constraints hoặc invariants quan trọng nào?
   - Khi `MetricResult.status != MetricStatus.COMPUTED`, `MetricResult.value` BẮT BUỘC là `None`
     và `missing_reason` phải khác rỗng (chống ngụy tạo số `0`).
   - Toàn bộ container lồng nhau được sao chép sâu khi kiểm định (`revalidate_instances="always"`).
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from p06.providers.base import StrictNonNegFloat
from p06.schemas.story import (
    NonBlankStr,
    OptionalNonBlankStr,
    StoryPlan,
    StrictNonNegInt,
    StrictPositiveInt,
)


class MetricStatus(str, Enum):
    """Trạng thái tính toán trung thực của một chỉ số đánh giá."""

    COMPUTED = "COMPUTED"
    NOT_EVALUATED = "NOT_EVALUATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INVALID = "INVALID"


class MetricProvenance(str, Enum):
    """Nguồn gốc dữ liệu của chỉ số để tách bạch thời gian thật, mô phỏng và ước lượng."""

    MEASURED_WALL_CLOCK = "MEASURED_WALL_CLOCK"
    SIMULATED_CLOCK = "SIMULATED_CLOCK"
    PROVIDER_REPORTED = "PROVIDER_REPORTED"
    DERIVED_FROM_EVIDENCE = "DERIVED_FROM_EVIDENCE"
    ESTIMATED = "ESTIMATED"
    UNAVAILABLE = "UNAVAILABLE"


class GateStatus(str, Enum):
    """Trạng thái thẩm định cổng an toàn (không bao giờ đánh đồng `NOT_EVALUATED` thành `PASS`)."""

    PASS = "PASS"
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"


class MetricResult(BaseModel):
    """Kết quả chuẩn hóa của một metric đơn lẻ kèm công thức/ngữ cảnh nguồn gốc.

    Lý do thiết kế: Ngăn việc trả `0` khi thiếu dữ liệu hoặc mất telemetry; tách rõ
    `is_simulated` và `provenance` để không bao giờ nhầm số liệu Mock với kết quả LLM thật.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    name: NonBlankStr
    status: MetricStatus
    value: Optional[Any] = None
    unit: NonBlankStr
    numerator: Optional[float] = None
    denominator: Optional[float] = None
    data_source: NonBlankStr
    provenance: MetricProvenance
    is_simulated: StrictBool = False
    missing_reason: OptionalNonBlankStr = None
    limitations: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _deep_copy_nested(cls, data: Any) -> Any:
        """Sao chép sâu `value` và `metadata` để tránh rò rỉ tham chiếu ngoài."""
        if isinstance(data, cls):
            return copy.deepcopy(data.model_dump())
        if isinstance(data, Mapping):
            copied = dict(data)
            if "value" in copied and copied["value"] is not None:
                copied["value"] = copy.deepcopy(copied["value"])
            if "metadata" in copied and copied["metadata"] is not None:
                copied["metadata"] = copy.deepcopy(copied["metadata"])
            return copied
        return data

    @model_validator(mode="after")
    def validate_missing_data_policy(self) -> MetricResult:
        """Ép buộc bất biến: chỉ trạng thái `COMPUTED` mới được mang `value` khác `None`."""
        if self.status != MetricStatus.COMPUTED:
            if self.value is not None:
                raise ValueError(
                    f"Metric '{self.name}' có status={self.status.value} bắt buộc value phải là None, "
                    f"không được gán {self.value!r}."
                )
            if self.missing_reason is None:
                raise ValueError(
                    f"Metric '{self.name}' có status={self.status.value} bắt buộc phải ghi rõ missing_reason."
                )
        return self


class TranscriptEntry(BaseModel):
    """Một lượt lời thoại thực sự đã được chấp nhận phát sóng (`APPLIED` + `COMPLETED`)."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    turn_index: StrictNonNegInt
    turn_id: NonBlankStr
    sku_id: NonBlankStr
    topic_id: OptionalNonBlankStr = None
    arc_id: OptionalNonBlankStr = None
    chunk_id: OptionalNonBlankStr = None
    candidate_id: NonBlankStr
    origin: NonBlankStr
    intent: NonBlankStr
    text: NonBlankStr
    cited_evidence_ids: tuple[NonBlankStr, ...] = ()
    covered_claim_ids: tuple[NonBlankStr, ...] = ()
    proposed_topic_ids: tuple[NonBlankStr, ...] = ()
    confirmed_topic_ids: tuple[NonBlankStr, ...] = ()
    actual_duration_ms: StrictNonNegInt
    playback_event_id: NonBlankStr
    occurred_at_utc: NonBlankStr
    is_fallback: StrictBool = False
    verification_status: NonBlankStr = "VERIFIED"
    gate_decision_id: OptionalNonBlankStr = None


class PlaybackEventRecord(BaseModel):
    """Bản ghi một sự kiện ACK phát sóng (bao gồm cả sự kiện bị từ chối hoặc `FAILED`/`UNKNOWN`)."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    sequence_index: StrictNonNegInt
    turn_id: NonBlankStr
    candidate_id: OptionalNonBlankStr = None
    chunk_id: OptionalNonBlankStr = None
    sku_id: NonBlankStr
    outcome: NonBlankStr
    apply_status: NonBlankStr
    applied: StrictBool
    playback_event_id: OptionalNonBlankStr = None
    actual_duration_ms: Optional[StrictNonNegInt] = None
    confirmed_topic_ids: tuple[NonBlankStr, ...] = ()
    covered_claim_ids: tuple[NonBlankStr, ...] = ()
    occurred_at_utc: OptionalNonBlankStr = None
    failure_reason: OptionalNonBlankStr = None
    semantic_index_error: OptionalNonBlankStr = None


class GraphTraceRecord(BaseModel):
    """Bản ghi dấu vết chi tiết một lượt thực thi của Agent hoặc Baseline."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    turn_index: StrictNonNegInt
    turn_id: NonBlankStr
    method: NonBlankStr
    active_sku_id: NonBlankStr
    selected_arc_id: OptionalNonBlankStr = None
    selected_topic_id: OptionalNonBlankStr = None
    node_trace: tuple[str, ...] = ()
    turn_outcome: NonBlankStr
    retries_used: StrictNonNegInt = 0
    max_retries: StrictNonNegInt = 2
    used_fallback: StrictBool = False
    should_terminate: StrictBool = False
    termination_reason: OptionalNonBlankStr = None
    non_retryable_failure: OptionalNonBlankStr = None
    invocation_latency_ms: StrictNonNegFloat = 0.0
    draft_attempts: tuple[dict[str, Any], ...] = ()
    repetition_checks: tuple[dict[str, Any], ...] = ()
    p05_decisions: tuple[dict[str, Any], ...] = ()
    proposed_topic_ids: tuple[NonBlankStr, ...] = ()
    verified_topic_ids: tuple[NonBlankStr, ...] = ()
    covered_claim_ids: tuple[NonBlankStr, ...] = ()
    candidate_id: OptionalNonBlankStr = None
    chunk_id: OptionalNonBlankStr = None

    @model_validator(mode="before")
    @classmethod
    def _deep_copy_nested_lists(cls, data: Any) -> Any:
        """Sao chép sâu các bản ghi attempt lồng nhau."""
        if isinstance(data, cls):
            return copy.deepcopy(data.model_dump())
        if isinstance(data, Mapping):
            copied = dict(data)
            for key in ("draft_attempts", "repetition_checks", "p05_decisions"):
                if key in copied and copied[key] is not None:
                    copied[key] = copy.deepcopy(copied[key])
            return copied
        return data


def is_clean_termination_boundary_trace(trace: GraphTraceRecord) -> bool:
    """Phân biệt lượt kết thúc biên SKU/phiên sạch với lượt `SAFE_ABORT_NO_CANDIDATE` thực sự.

    Lý do: Ở cuối mỗi SKU trong LangGraph, `plan_chunk` đặt `should_terminate=True` và
    `finalize_candidate` gán `turn_outcome='SAFE_ABORT_NO_CANDIDATE'` dù không hề gọi LLM
    hay phát sinh lỗi; lọc các lượt biên sạch giúp không tính nhầm vào `safe_abort_count`,
    không làm loãng `turns_attempted`, và không kéo lệch phân vị độ trễ invocation.
    """
    return bool(
        trace.should_terminate
        and trace.non_retryable_failure is None
        and not trace.draft_attempts
        and not trace.p05_decisions
        and "safe_fallback" not in trace.node_trace
    )


class ProviderCallRecord(BaseModel):
    """Bản ghi một lần gọi LLMProvider (kể cả các lần gọi bị từ chối/rewrite hoặc lỗi)."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    call_index: StrictNonNegInt
    turn_id: OptionalNonBlankStr = None
    request_id: OptionalNonBlankStr = None
    provider_name: NonBlankStr
    model_id: NonBlankStr
    tier: NonBlankStr
    latency_ms: StrictNonNegFloat
    is_simulated_metric: StrictBool
    input_tokens: Optional[StrictNonNegInt] = None
    output_tokens: Optional[StrictNonNegInt] = None
    thinking_tokens: Optional[StrictNonNegInt] = None
    token_usage_source: NonBlankStr
    finish_reason: NonBlankStr
    raw_response_valid: StrictBool
    is_wasted: StrictBool = False
    error_type: OptionalNonBlankStr = None
    error_message: OptionalNonBlankStr = None


class ErrorRecord(BaseModel):
    """Bản ghi một sự cố, từ chối P05, lỗi schema hoặc dừng an toàn trong phiên chạy."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    error_index: StrictNonNegInt
    turn_id: OptionalNonBlankStr = None
    stage: NonBlankStr
    error_type: NonBlankStr
    message: NonBlankStr
    is_retryable: Optional[StrictBool] = None
    sku_id: OptionalNonBlankStr = None
    topic_id: OptionalNonBlankStr = None
    occurred_at_utc: OptionalNonBlankStr = None


class GoldFactualLabel(BaseModel):
    """Nhãn chuẩn thực tế được gán độc lập (không lấy từ quyết định ALLOW của P05)."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    candidate_id: NonBlankStr
    text: NonBlankStr
    sku_id: OptionalNonBlankStr = None
    verifier_decision: NonBlankStr
    expected_factual_valid: StrictBool
    has_unsupported_claim: StrictBool = False
    failure_category: OptionalNonBlankStr = None
    notes: OptionalNonBlankStr = None


class RunEvidence(BaseModel):
    """Tập hợp bằng chứng thô đầy đủ của một lần chạy thí nghiệm phục vụ tính metric độc lập."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    manifest: dict[str, Any]
    story_plan: StoryPlan
    transcript: tuple[TranscriptEntry, ...] = ()
    playback_events: tuple[PlaybackEventRecord, ...] = ()
    graph_traces: tuple[GraphTraceRecord, ...] = ()
    provider_calls: tuple[ProviderCallRecord, ...] = ()
    errors: tuple[ErrorRecord, ...] = ()
    planning_latency_ms: StrictNonNegFloat = 0.0
    upfront_script_generation_latency_ms: StrictNonNegFloat = 0.0
    total_measured_processing_ms: StrictNonNegFloat = 0.0
    simulated_elapsed_sec: StrictNonNegFloat = 0.0
    target_duration_sec: StrictNonNegFloat = 600.0

    @model_validator(mode="before")
    @classmethod
    def _deep_copy_manifest(cls, data: Any) -> Any:
        """Sao chép sâu `manifest` để bảo toàn tính bất biến."""
        if isinstance(data, cls):
            return copy.deepcopy(data.model_dump())
        if isinstance(data, Mapping):
            copied = dict(data)
            if "manifest" in copied and copied["manifest"] is not None:
                copied["manifest"] = copy.deepcopy(copied["manifest"])
            return copied
        return data


class EvaluationReport(BaseModel):
    """Báo cáo đánh giá đầy đủ cho một lần chạy, nhóm theo 5 trục tự động + Human Eval."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    run_id: NonBlankStr
    experiment_id: NonBlankStr
    method: NonBlankStr
    scenario: NonBlankStr
    provider_tier: NonBlankStr
    provider_name: NonBlankStr
    model_id: NonBlankStr
    history_window: Optional[StrictPositiveInt] = None
    termination_reason: NonBlankStr
    coverage: dict[str, MetricResult] = Field(default_factory=dict)
    repetition: dict[str, MetricResult] = Field(default_factory=dict)
    safety: dict[str, MetricResult] = Field(default_factory=dict)
    reliability: dict[str, MetricResult] = Field(default_factory=dict)
    performance: dict[str, MetricResult] = Field(default_factory=dict)
    human_eval_placeholders: dict[str, MetricResult] = Field(default_factory=dict)
    hard_gates_passed: StrictBool
    structural_hard_gates_status: GateStatus = GateStatus.PASS
    factual_safety_gate_status: GateStatus = GateStatus.NOT_EVALUATED
    overall_gate_status: GateStatus = GateStatus.NOT_EVALUATED
    not_evaluated_gates: tuple[str, ...] = ()
    hard_gate_failures: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    metric_provenance: dict[str, str] = Field(default_factory=dict)


class CompatibilityIssue(BaseModel):
    """Mô tả một sai lệch biến kiểm soát hoặc vi phạm cô lập tầng khi so sánh các lượt chạy."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    severity: NonBlankStr
    code: NonBlankStr
    message: NonBlankStr
    run_ids: tuple[NonBlankStr, ...] = ()


class ComparisonRow(BaseModel):
    """Một dòng tóm tắt các chỉ số chính của một lượt chạy trong bảng đối chiếu."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    run_id: NonBlankStr
    method: NonBlankStr
    scenario: NonBlankStr
    provider_tier: NonBlankStr
    provider_name: NonBlankStr
    model_id: NonBlankStr
    history_window: Optional[StrictPositiveInt] = None
    termination_reason: NonBlankStr
    hard_gates_passed: StrictBool
    structural_hard_gates_status: GateStatus = GateStatus.PASS
    factual_safety_gate_status: GateStatus = GateStatus.NOT_EVALUATED
    overall_gate_status: GateStatus = GateStatus.NOT_EVALUATED
    mandatory_topic_coverage: Optional[float] = None
    duration_fulfillment: Optional[float] = None
    exact_chunk_replay_count: Optional[int] = None
    exact_normalized_text_replay_count: Optional[int] = None
    outside_window_exact_text_replay_count: Optional[int] = None
    max_prior_ngram3_jaccard_mean: Optional[float] = None
    lexical_repetition_rate: Optional[float] = None
    p05_rejection_rate: Optional[float] = None
    rewrite_rate: Optional[float] = None
    fallback_rate: Optional[float] = None
    safe_abort_rate: Optional[float] = None
    provider_latency_p50_ms: Optional[float] = None
    provider_latency_p95_ms: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    wasted_tokens: Optional[int] = None
    total_model_calls: Optional[int] = None
    estimated_llm_cost_usd: Optional[float] = None
    missing_or_not_evaluated: tuple[str, ...] = ()


class ComparisonReport(BaseModel):
    """Báo cáo so sánh nhiều lần chạy kèm kiểm tra tính tương thích thực nghiệm."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    compatible: StrictBool
    compatibility_issues: tuple[CompatibilityIssue, ...] = ()
    grouped_tiers: tuple[NonBlankStr, ...] = ()
    rows: tuple[ComparisonRow, ...] = ()
    notes: tuple[str, ...] = ()


class HumanEvalSheetEntry(BaseModel):
    """Mẫu dòng xuất ra phiếu chấm mù (`human_eval_rubric_v0.1.md`), không lộ danh tính phương pháp."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    sample_id: NonBlankStr
    blind_method_id: NonBlankStr
    experiment_id: NonBlankStr
    scenario: NonBlankStr
    transcript_text: NonBlankStr
    evaluator_id: Optional[str] = None
    narrative_coherence: Optional[int] = None
    naturalness: Optional[int] = None
    persuasiveness: Optional[int] = None
    context_relevance: Optional[int] = None
    transition_quality: Optional[int] = None
    repetition_quality: Optional[int] = None
    hard_constraint_violation: Optional[bool] = None
    violation_notes: str = ""
    overall_notes: str = ""


class HumanEvalBlindMapping(BaseModel):
    """Bảng ánh xạ bí mật giữa `sample_id` / `blind_method_id` và cấu hình thật của lần chạy."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    sample_id: NonBlankStr
    blind_method_id: NonBlankStr
    run_id: NonBlankStr
    method: NonBlankStr
    provider_tier: NonBlankStr
    provider_name: NonBlankStr
    model_id: NonBlankStr
    history_window: Optional[StrictPositiveInt] = None
    scenario: NonBlankStr
