"""Kiểm thử đơn vị cho `ScriptFirstBaseline` (`P06-E01` baseline lập kịch bản đầu phiên).

1. File này giải quyết vấn đề gì?
   Xác minh toàn diện hành vi của `ScriptFirstBaseline` ở cả hai chế độ `UPFRONT_LLM` và
   `DETERMINISTIC_TALKING_POINTS`, bảo đảm đối chứng công bằng cho thí nghiệm `P06-E01` mà
   vẫn giữ nghiêm các bất biến an toàn của hệ thống.
2. Trách nhiệm chính của module là gì?
   Kiểm thử từ chối `StoryPlan` chưa duyệt, cô lập SKU đang hoạt động (`I-04`), chuẩn bị toàn bộ
   ứng viên `DRAFT` (`rewrite_attempt=0`) trước khi phát, kiểm định P05 -> `SafeFallbackSelector` ->
   `SAFE_ABORT_NO_CANDIDATE`, giữ nguyên checkpoint khi ACK `FAILED`/`UNKNOWN`, và provenance token.
3. Module này liên kết với các thành phần nào?
   Kiểm thử trực tiếp `p06.baselines`, `p06.adapters.P05KnowledgeAdapter`, `p06.providers.MockLLMProvider`,
   `p06.adapters.mocks.MockPlaybackAckBus`, `p06.simulation.SimulatedPlaybackHarness` và `VirtualClock`.
4. Input và output chính là gì?
   Input là dữ liệu synthetic E01 (`e01_verified_skus.json`, `e01_story_plans.json`) và các kịch bản
   mô phỏng LLM/ACK; Output là xác nhận đúng từng bất biến và chỉ số `BaselineMetrics`.
5. Có những constraints hoặc invariants quan trọng nào?
   - Không đọc `played_history` để tái lập kế hoạch, không chạy `RepetitionDetector` hay `bounded_rewrite`.
   - `FAILED`/`UNKNOWN` ACK tuyệt đối không được làm tiến checkpoint hay `completed_topic_ids`.
   - `UpfrontChunkDraftLLMOutput` phải từ chối mọi trường thẩm quyền (`verified`, `gate_decision_id`, ...).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from p06.adapters import AckApplyStatus, P05KnowledgeAdapter
from p06.adapters.mocks import MockPlaybackAckBus
from p06.adapters.p05_knowledge_adapter import _load_p05_modules
from p06.baselines import (
    BaselineMetrics,
    BaselineScriptSource,
    BaselineSessionResult,
    BaselineTurnRecord,
    ScriptFirstBaseline,
    UpfrontChunkDraftLLMOutput,
)
from p06.providers import (
    GenerationRequest,
    GenerationResult,
    LLMProvider,
    MockBehavior,
    MockLLMProvider,
    MockResponseStep,
    ProviderTelemetry,
    ProviderTier,
    ProviderTransportError,
    TokenUsageSource,
)
from p06.schemas import (
    AgentTurnOutcome,
    CandidateOrigin,
    CandidateVerificationStatus,
    CoverageMode,
    PlaybackOutcomeStatus,
    ProposedResponseCoverage,
    SkuVersionBinding,
    SpeechCandidate,
    StoryArc,
    StoryCheckpoint,
    StoryPlan,
    StoryPlanApprovalStatus,
    StoryTopic,
    TargetScopeMode,
)
from p06.simulation import SimulatedPlaybackHarness, VirtualClock

P06_ROOT: Path = Path(__file__).resolve().parents[2]
E01_SEED_PATH: Path = P06_ROOT / "data" / "products" / "e01_verified_skus.json"
E01_PLANS_PATH: Path = P06_ROOT / "data" / "story_plans" / "e01_story_plans.json"
P05_DIR: Path = P06_ROOT.parent / "knowledge-verification"

TENANT_ID = "tenant-p06-poc-01"
SIM_RUN_ID = "sim-run-baseline-001"
START_AT = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)


def _load_e01_plan(plan_key: str = "product_education_10m") -> StoryPlan:
    """Nạp một `StoryPlan` hợp lệ từ fixture tham chiếu E01."""
    raw = json.loads(E01_PLANS_PATH.read_text(encoding="utf-8"))
    return StoryPlan.model_validate(raw["plans"][plan_key])


def _make_p05_adapter() -> tuple[P05KnowledgeAdapter, Any, Any]:
    """Khởi tạo `P05KnowledgeAdapter` độc lập kèm `store` và `p05_schemas`."""
    p05_schemas, p05_gate = _load_p05_modules(P05_DIR)
    store = p05_gate.VersionedKnowledgeStore.from_seed_file(E01_SEED_PATH).clone()
    adapter = P05KnowledgeAdapter(store=store, p05_dir=P05_DIR)
    return adapter, store, p05_schemas


def _make_harness_and_bus(
    story_plan: StoryPlan,
    *,
    active_sku_id: str = "SKU-HONEY-01",
    current_arc_id: str | None = None,
    next_topic_id: str | None = None,
) -> tuple[SimulatedPlaybackHarness, MockPlaybackAckBus, VirtualClock, StoryCheckpoint]:
    """Tạo bộ `VirtualClock`, `StoryCheckpoint`, `SimulatedPlaybackHarness` và `MockPlaybackAckBus`."""
    clock = VirtualClock(start_at=START_AT)
    resolved_arc_id = current_arc_id or story_plan.arcs[0].arc_id
    resolved_topic_id = next_topic_id or story_plan.arcs[0].topics[0].topic_id
    checkpoint = StoryCheckpoint(
        tenant_id=story_plan.tenant_id,
        session_id=story_plan.session_id,
        session_epoch=1,
        plan_id=story_plan.plan_id,
        plan_revision=story_plan.plan_revision,
        active_sku_id=active_sku_id,
        current_arc_id=resolved_arc_id,
        next_topic_id=resolved_topic_id,
        updated_at=START_AT,
    )
    harness = SimulatedPlaybackHarness(
        initial_checkpoint=checkpoint,
        expected_simulation_run_id=SIM_RUN_ID,
        story_plan=story_plan,
    )
    bus = MockPlaybackAckBus(clock=clock, simulation_run_id=SIM_RUN_ID)
    return harness, bus, clock, checkpoint


def _make_preapproved_fallback(
    story_plan: StoryPlan,
    *,
    candidate_id: str = "fb-honey-safe-01",
    sku_id: str = "SKU-HONEY-01",
    text: str = "Mật ong hoa cà phê Đắk Lắk chai 500ml hiện có giá niêm yết 159.000đ, mời anh chị tham khảo giỏ hàng ạ.",
    knowledge_version: int = 1,
    ocop_version: int = 1,
    rights_version: int = 1,
) -> SpeechCandidate:
    """Tạo một ứng viên dự phòng `PREAPPROVED_FALLBACK` không tự đánh dấu phủ topic."""
    return SpeechCandidate(
        candidate_id=candidate_id,
        tenant_id=story_plan.tenant_id,
        session_id=story_plan.session_id,
        session_epoch=1,
        origin=CandidateOrigin.PREAPPROVED_FALLBACK,
        source_chunk_id=None,
        scope_mode=TargetScopeMode.SINGLE_SKU,
        sku_refs=[sku_id],
        sku_bindings=[
            SkuVersionBinding(
                sku_id=sku_id,
                knowledge_version=knowledge_version,
                ocop_version=ocop_version,
                rights_version=rights_version,
                cited_evidence_ids=["ev-e01-honey-shipping"],
                stated_price_vnd=159000,
            )
        ],
        session_rights_version=1,
        intent="safe_fallback",
        text=text,
        estimated_duration_sec=8.0,
        proposed_coverage=ProposedResponseCoverage(
            covered_topic_ids=[],
            covered_intents=["safe_fallback"],
            coverage_mode=CoverageMode.FULL,
        ),
        verification_status=CandidateVerificationStatus.DRAFT,
    )


class _UnavailableTelemetryLLMProvider(LLMProvider):
    """Provider giả lập tình huống một lượt gọi trả về token `UNAVAILABLE` hoặc lỗi không telemetry."""

    def __init__(self, *, fail_without_telemetry: bool = False) -> None:
        self._fail_without_telemetry = fail_without_telemetry
        self.calls: int = 0

    @property
    def provider_name(self) -> str:
        return "fake-unavailable"

    @property
    def model_id(self) -> str:
        return "fake-model"

    @property
    def tier(self) -> ProviderTier:
        return ProviderTier.LOCAL_SMOKE_TEST

    def generate_structured(
        self,
        request: GenerationRequest,
        output_schema: type[UpfrontChunkDraftLLMOutput],
    ) -> GenerationResult[Any]:
        self.calls += 1
        if self.calls == 1 and self._fail_without_telemetry:
            raise ProviderTransportError("Mất kết nối đột ngột không kịp thu telemetry.", telemetry=None)

        telemetry = ProviderTelemetry(
            provider_name=self.provider_name,
            model_id=self.model_id,
            tier=self.tier,
            latency_ms=12.5,
            is_simulated_metric=False,
            input_tokens=None,
            output_tokens=None,
            token_usage_source=TokenUsageSource.UNAVAILABLE,
            finish_reason="stop",
            raw_response_valid=True,
        )
        payload = output_schema(
            text="Mật ong hoa cà phê Đắk Lắk chai 500ml pha nước ấm dưới 50 độ C, giá 159.000đ.",
            cited_evidence_ids=["ev-e01-honey-usage"],
            stated_price_vnd=159000,
        )
        return GenerationResult(parsed_output=payload, raw_text="{}", telemetry=telemetry)


class TestScriptFirstBaselineContracts:
    """Kiểm thử hợp đồng DTO và các điều kiện đầu vào của `ScriptFirstBaseline`."""

    def test_upfront_llm_output_rejects_trusted_metadata_and_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            UpfrontChunkDraftLLMOutput.model_validate(
                {
                    "text": "Mật ong hoa cà phê Đắk Lắk giá 159.000đ.",
                    "verified": True,
                }
            )
        with pytest.raises(ValidationError):
            UpfrontChunkDraftLLMOutput.model_validate(
                {
                    "text": "Mật ong hoa cà phê Đắk Lắk giá 159.000đ.",
                    "gate_decision_id": "p05-allow-fake",
                }
            )

    def test_baseline_metrics_enforces_token_provenance_invariants(self) -> None:
        with pytest.raises(ValidationError):
            BaselineMetrics(
                script_source=BaselineScriptSource.DETERMINISTIC_TALKING_POINTS,
                total_topics_planned=2,
                turns_attempted=2,
                verified_ready_count=2,
                fallback_count=0,
                safe_abort_count=0,
                playback_applied_count=2,
                llm_calls=0,
                input_tokens=0,
                output_tokens=0,
                token_usage_source=TokenUsageSource.SIMULATED,
            )
        with pytest.raises(ValidationError):
            BaselineMetrics(
                script_source=BaselineScriptSource.UPFRONT_LLM,
                total_topics_planned=1,
                turns_attempted=1,
                verified_ready_count=1,
                fallback_count=0,
                safe_abort_count=0,
                playback_applied_count=1,
                llm_calls=1,
                input_tokens=10,
                output_tokens=10,
                token_usage_source=TokenUsageSource.UNAVAILABLE,
            )

    def test_upfront_llm_requires_llm_provider(self) -> None:
        story_plan = _load_e01_plan()
        adapter, _, _ = _make_p05_adapter()
        harness, bus, clock, _ = _make_harness_and_bus(story_plan)

        with pytest.raises(ValueError, match="llm_provider"):
            ScriptFirstBaseline(
                knowledge_verifier=adapter,
                playback_bus=bus,
                harness=harness,
                clock=clock,
                llm_provider=None,
                script_source=BaselineScriptSource.UPFRONT_LLM,
            )

    def test_rejects_unapproved_story_plan(self) -> None:
        approved_plan = _load_e01_plan()
        raw_draft = approved_plan.model_dump()
        raw_draft["approval_status"] = StoryPlanApprovalStatus.DRAFT
        raw_draft["approved_by"] = None
        raw_draft["approved_at"] = None
        draft_plan = StoryPlan.model_validate(raw_draft)

        adapter, _, _ = _make_p05_adapter()
        harness, bus, clock, _ = _make_harness_and_bus(approved_plan)
        baseline = ScriptFirstBaseline(
            knowledge_verifier=adapter,
            playback_bus=bus,
            harness=harness,
            clock=clock,
        )

        with pytest.raises(ValueError, match="APPROVED"):
            baseline.prepare_upfront_script(draft_plan, "SKU-HONEY-01")
        with pytest.raises(ValueError, match="APPROVED"):
            baseline.run_session(draft_plan)


class TestScriptFirstBaselineExecution:
    """Kiểm thử thực thi hai chế độ kịch bản, P05 -> fallback -> abort, I-04 và ACK."""

    def test_deterministic_talking_points_runs_full_active_sku_session(self) -> None:
        story_plan = _load_e01_plan("product_education_10m")
        adapter, _, _ = _make_p05_adapter()
        harness, bus, clock, _ = _make_harness_and_bus(story_plan, active_sku_id="SKU-HONEY-01")

        baseline = ScriptFirstBaseline(
            knowledge_verifier=adapter,
            playback_bus=bus,
            harness=harness,
            clock=clock,
            script_source=BaselineScriptSource.DETERMINISTIC_TALKING_POINTS,
        )

        prepared = baseline.prepare_upfront_script(story_plan, "SKU-HONEY-01")
        assert len(prepared.items) == 2
        assert [item.topic.topic_id for item in prepared.items] == [
            "topic-edu-honey-usage",
            "topic-edu-honey-quality",
        ]
        # Mọi ứng viên đầu phiên đều phải là DRAFT, PROACTIVE_STORY và chưa từng rewrite.
        for item in prepared.items:
            assert item.candidate is not None
            assert item.candidate.verification_status == CandidateVerificationStatus.DRAFT
            assert item.candidate.origin == CandidateOrigin.PROACTIVE_STORY
            assert item.candidate.rewrite_attempt == 0
            assert "159.000đ" in item.candidate.text
            assert "Đắk Lắk" in item.candidate.text

        result = baseline.run_session(story_plan)
        assert isinstance(result, BaselineSessionResult)
        assert result.metrics.script_source == BaselineScriptSource.DETERMINISTIC_TALKING_POINTS
        assert result.metrics.total_topics_planned == 2
        assert result.metrics.turns_attempted == 2
        assert result.metrics.verified_ready_count == 2
        assert result.metrics.fallback_count == 0
        assert result.metrics.safe_abort_count == 0
        assert result.metrics.playback_applied_count == 2
        assert result.metrics.llm_calls == 0
        assert result.metrics.input_tokens is None
        assert result.metrics.output_tokens is None
        assert result.metrics.token_usage_source == TokenUsageSource.UNAVAILABLE
        assert result.metrics.planning_latency_ms == 0.0
        assert result.metrics.generation_latency_ms == 0.0

        assert result.completed_topic_ids == frozenset(
            {"topic-edu-honey-usage", "topic-edu-honey-quality"}
        )
        assert result.played_history_count == 2
        assert result.final_checkpoint.active_sku_id == "SKU-HONEY-01"
        assert result.final_checkpoint.next_topic_id is None
        assert result.final_checkpoint.last_completed_chunk_id is not None
        assert result.final_checkpoint.last_playback_event_id is not None

    def test_upfront_llm_with_mock_provider_generates_all_topics_before_playback(self) -> None:
        story_plan = _load_e01_plan("product_education_10m")
        adapter, _, _ = _make_p05_adapter()
        harness, bus, clock, _ = _make_harness_and_bus(story_plan, active_sku_id="SKU-HONEY-01")

        mock_llm = MockLLMProvider(
            keyed_responses={
                "topic-edu-honey-usage": [
                    MockResponseStep(
                        behavior=MockBehavior.VALID_JSON,
                        latency_ms=4.0,
                        input_tokens=110,
                        output_tokens=40,
                        payload={
                            "text": "Mật ong hoa cà phê Đắk Lắk chai 500ml giá 159.000đ, pha nước ấm dưới 50 độ C và không dùng cho trẻ dưới 1 tuổi.",
                            "role": "OPENING",
                            "cited_evidence_ids": ["ev-e01-honey-usage"],
                            "stated_price_vnd": 159000,
                            "mentions_ocop": False,
                        },
                    )
                ],
                "topic-edu-honey-quality": [
                    MockResponseStep(
                        behavior=MockBehavior.VALID_JSON,
                        latency_ms=6.0,
                        input_tokens=130,
                        output_tokens=50,
                        payload={
                            "text": "Mật ong hoa cà phê nguyên chất 100% giá 159.000đ, nếu kết tinh nhẹ mùa lạnh chỉ cần ngâm nước ấm 40 độ C.",
                            "role": "PRODUCT_STORY",
                            "cited_evidence_ids": ["ev-e01-honey-quality"],
                            "stated_price_vnd": 159000,
                            "mentions_ocop": False,
                        },
                    )
                ],
            }
        )

        baseline = ScriptFirstBaseline(
            knowledge_verifier=adapter,
            playback_bus=bus,
            harness=harness,
            clock=clock,
            llm_provider=mock_llm,
            script_source=BaselineScriptSource.UPFRONT_LLM,
            seed=42,
        )

        result = baseline.run_session(story_plan)
        assert result.metrics.script_source == BaselineScriptSource.UPFRONT_LLM
        assert result.metrics.llm_calls == 2
        assert result.metrics.input_tokens == 240
        assert result.metrics.output_tokens == 90
        assert result.metrics.token_usage_source == TokenUsageSource.SIMULATED
        assert result.metrics.planning_latency_ms == pytest.approx(10.0)
        assert result.metrics.generation_latency_ms == 0.0
        assert result.metrics.verified_ready_count == 2
        assert result.metrics.playback_applied_count == 2
        assert result.completed_topic_ids == frozenset(
            {"topic-edu-honey-usage", "topic-edu-honey-quality"}
        )

    def test_p05_rejection_falls_back_then_safe_aborts_when_no_valid_fallback(self) -> None:
        story_plan = _load_e01_plan("product_education_10m")
        adapter, store, p05_schemas = _make_p05_adapter()
        harness, bus, clock, _ = _make_harness_and_bus(story_plan, active_sku_id="SKU-HONEY-01")

        # Lượt 0 vi phạm tuyên bố y tế bị cấm -> bị P05 chặn -> dùng fallback hợp lệ.
        # Lượt 1 lỗi từ Provider -> không có fallback cho case không hợp lệ sau khi thu hồi -> safe abort.
        mock_llm = MockLLMProvider(
            response_sequence=[
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    input_tokens=100,
                    output_tokens=30,
                    payload={
                        "text": "Mật ong hoa cà phê giúp chữa khỏi đau dạ dày rất nhanh.",
                        "cited_evidence_ids": ["ev-e01-honey-usage"],
                    },
                ),
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    input_tokens=100,
                    output_tokens=30,
                    payload={
                        "text": "Mật ong hoa cà phê Đắk Lắk chai 500ml giá 999.000đ.",
                        "cited_evidence_ids": ["ev-e01-honey-quality"],
                        "stated_price_vnd": 999000,
                    },
                ),
            ]
        )

        # Mỗi fallback chỉ phát một lần để tránh lặp máy móc; khi có 2 fallback khác nhau -> dùng đủ 2,
        # còn khi không còn fallback mới hợp lệ -> SAFE_ABORT_NO_CANDIDATE.
        valid_fallback = _make_preapproved_fallback(story_plan)
        valid_fallback_2 = SpeechCandidate(
            candidate_id="fb-safe-honey-02",
            tenant_id=story_plan.tenant_id,
            session_id=story_plan.session_id,
            session_epoch=1,
            origin=CandidateOrigin.PREAPPROVED_FALLBACK,
            scope_mode=TargetScopeMode.SINGLE_SKU,
            sku_refs=["SKU-HONEY-01"],
            sku_bindings=[
                adapter.get_sku_evidence(story_plan.tenant_id, "SKU-HONEY-01", at_time=START_AT).to_version_binding(
                    cited_evidence_ids=["ev-e01-honey-origin"],
                    stated_price_vnd=159000,
                )
            ],
            session_rights_version=1,
            intent="FALLBACK_SAFE_INFO",
            text="Mật ong hoa cà phê Đắk Lắk thu hái chính vụ, chai 500ml giá niêm yết 159.000đ.",
            estimated_duration_sec=5.5,
            proposed_coverage=ProposedResponseCoverage(
                covered_topic_ids=[],
                covered_intents=["Thông tin nguồn gốc an toàn"],
                coverage_mode=CoverageMode.FULL,
            ),
            verification_status=CandidateVerificationStatus.DRAFT,
        )
        baseline_with_fb = ScriptFirstBaseline(
            knowledge_verifier=adapter,
            playback_bus=bus,
            harness=harness,
            clock=clock,
            llm_provider=mock_llm,
            fallback_candidates=[valid_fallback, valid_fallback_2],
            script_source=BaselineScriptSource.UPFRONT_LLM,
        )
        fb_result = baseline_with_fb.run_session(story_plan)
        assert fb_result.metrics.verified_ready_count == 0
        assert fb_result.metrics.fallback_count == 2
        assert fb_result.metrics.safe_abort_count == 0
        assert fb_result.metrics.playback_applied_count == 2
        assert all(t.outcome == AgentTurnOutcome.FALLBACK_PREAPPROVED for t in fb_result.turns)
        assert fb_result.turns[0].spoken_text != fb_result.turns[1].spoken_text
        # Fallback không được tự ý đánh dấu chủ đề đã phủ (require_empty_covered_topics=True).
        assert fb_result.completed_topic_ids == frozenset()

        # Phiên 2: OCOP bị thu hồi -> cả draft lẫn preapproved fallback đều bị P05 từ chối -> SAFE_ABORT_NO_CANDIDATE.
        store.update_ocop_status("SKU-HONEY-01", p05_schemas.OcopStatus.EXPIRED)
        harness2, bus2, clock2, cp2 = _make_harness_and_bus(story_plan, active_sku_id="SKU-HONEY-01")
        baseline_abort = ScriptFirstBaseline(
            knowledge_verifier=adapter,
            playback_bus=bus2,
            harness=harness2,
            clock=clock2,
            fallback_candidates=[valid_fallback],
            script_source=BaselineScriptSource.DETERMINISTIC_TALKING_POINTS,
        )
        abort_result = baseline_abort.run_session(story_plan)
        assert abort_result.metrics.turns_attempted == 2
        assert abort_result.metrics.verified_ready_count == 0
        assert abort_result.metrics.fallback_count == 0
        assert abort_result.metrics.safe_abort_count == 2
        assert abort_result.metrics.playback_applied_count == 0
        assert abort_result.played_history_count == 0
        assert abort_result.final_checkpoint == cp2
        for turn in abort_result.turns:
            assert turn.outcome == AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE
            assert turn.verified_candidate_id is None
            assert turn.ack_status is None
            assert turn.failure_reason is not None

    def test_upfront_llm_handles_provider_error_and_unavailable_tokens_gracefully(self) -> None:
        story_plan = _load_e01_plan("product_education_10m")
        adapter, _, _ = _make_p05_adapter()
        harness, bus, clock, _ = _make_harness_and_bus(story_plan, active_sku_id="SKU-HONEY-01")

        # Lượt 0 lỗi TIMEOUT từ provider, lượt 1 thành công -> không sập phiên, lượt 0 safe abort (không có fallback).
        mock_llm = MockLLMProvider(
            response_sequence=[
                MockResponseStep(behavior=MockBehavior.TIMEOUT, latency_ms=25.0),
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    latency_ms=5.0,
                    input_tokens=100,
                    output_tokens=35,
                    payload={
                        "text": "Mật ong hoa cà phê nguyên chất Đắk Lắk chai 500ml giá 159.000đ.",
                        "cited_evidence_ids": ["ev-e01-honey-quality"],
                        "stated_price_vnd": 159000,
                    },
                ),
            ]
        )
        baseline = ScriptFirstBaseline(
            knowledge_verifier=adapter,
            playback_bus=bus,
            harness=harness,
            clock=clock,
            llm_provider=mock_llm,
            script_source=BaselineScriptSource.UPFRONT_LLM,
        )
        result = baseline.run_session(story_plan)
        assert result.metrics.llm_calls == 2
        assert result.metrics.safe_abort_count == 1
        assert result.metrics.verified_ready_count == 1
        assert result.metrics.playback_applied_count == 1
        assert result.turns[0].outcome == AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE
        assert result.turns[1].outcome == AgentTurnOutcome.VERIFIED_READY
        assert result.completed_topic_ids == frozenset({"topic-edu-honey-quality"})

        # Kiểm tra token_usage_source=UNAVAILABLE khi provider thiếu telemetry hoặc trả None.
        harness2, bus2, clock2, _ = _make_harness_and_bus(story_plan, active_sku_id="SKU-HONEY-01")
        unavailable_llm = _UnavailableTelemetryLLMProvider(fail_without_telemetry=True)
        baseline2 = ScriptFirstBaseline(
            knowledge_verifier=adapter,
            playback_bus=bus2,
            harness=harness2,
            clock=clock2,
            llm_provider=unavailable_llm,
            script_source=BaselineScriptSource.UPFRONT_LLM,
        )
        result2 = baseline2.run_session(story_plan)
        assert result2.metrics.llm_calls == 2
        assert result2.metrics.token_usage_source == TokenUsageSource.UNAVAILABLE
        assert result2.metrics.input_tokens is None
        assert result2.metrics.output_tokens is None

    def test_active_sku_isolation_i04_ignores_other_skus_and_rejects_mismatch_or_unpinned(self) -> None:
        base_plan = _load_e01_plan("product_education_10m")
        # Thêm một topic có sku_id=None trong arc của SKU-HONEY-01 để xác nhận quy tắc kế thừa arc.sku_id.
        honey_arc = base_plan.arcs[0]
        extra_honey_topic = StoryTopic(
            topic_id="topic-edu-honey-inherit",
            title="Tổng kết lưu ý dùng mật ong hoa cà phê",
            sku_id=None,
            is_mandatory=False,
            fact_refs=["ev-e01-honey-shipping"],
            talking_points=["Đậy kín nắp sau khi dùng và bảo quản nơi khô ráo."],
        )
        updated_honey_arc = StoryArc.model_validate(
            {
                **honey_arc.model_dump(),
                "topics": [*honey_arc.topics, extra_honey_topic],
            }
        )
        plan_payload = base_plan.model_dump()
        plan_payload["arcs"][0] = updated_honey_arc.model_dump()
        plan = StoryPlan.model_validate(plan_payload)

        adapter, _, _ = _make_p05_adapter()
        harness, bus, clock, _ = _make_harness_and_bus(plan, active_sku_id="SKU-HONEY-01")
        baseline = ScriptFirstBaseline(
            knowledge_verifier=adapter,
            playback_bus=bus,
            harness=harness,
            clock=clock,
        )

        # Chỉ chọn các topic của SKU-HONEY-01, bỏ qua hoàn toàn SKU-TEA-02 và SKU-MACADAMIA-03.
        result = baseline.run_session(plan, active_sku_id="SKU-HONEY-01")
        assert [t.topic_id for t in result.turns] == [
            "topic-edu-honey-usage",
            "topic-edu-honey-quality",
            "topic-edu-honey-inherit",
        ]
        assert result.final_checkpoint.active_sku_id == "SKU-HONEY-01"

        # Vi phạm I-04: truyền active_sku_id khác với harness.checkpoint.active_sku_id.
        with pytest.raises(ValueError, match="I-04"):
            baseline.prepare_upfront_script(plan, "SKU-TEA-02")

        # Từ chối active_sku_id không thuộc pinned_sku_ids.
        harness_unpinned, bus_unpinned, clock_unpinned, _ = _make_harness_and_bus(
            plan,
            active_sku_id="SKU-UNKNOWN-99",
        )
        baseline_unpinned = ScriptFirstBaseline(
            knowledge_verifier=adapter,
            playback_bus=bus_unpinned,
            harness=harness_unpinned,
            clock=clock_unpinned,
        )
        with pytest.raises(ValueError, match="pinned_sku_ids"):
            baseline_unpinned.run_session(plan)

    def test_failed_and_unknown_acks_keep_checkpoint_and_completed_topics_frozen(self) -> None:
        story_plan = _load_e01_plan("product_education_10m")
        adapter, _, _ = _make_p05_adapter()
        harness, bus, clock, initial_cp = _make_harness_and_bus(
            story_plan,
            active_sku_id="SKU-HONEY-01",
        )
        baseline = ScriptFirstBaseline(
            knowledge_verifier=adapter,
            playback_bus=bus,
            harness=harness,
            clock=clock,
        )

        result = baseline.run_session(
            story_plan,
            outcome_overrides_by_turn={
                0: PlaybackOutcomeStatus.FAILED,
                1: PlaybackOutcomeStatus.UNKNOWN,
            },
        )
        assert result.metrics.turns_attempted == 2
        assert result.metrics.verified_ready_count == 2
        assert result.metrics.playback_applied_count == 0
        assert result.completed_topic_ids == frozenset()
        assert result.played_history_count == 0
        assert result.final_checkpoint == initial_cp
        for turn in result.turns:
            assert turn.ack_status == AckApplyStatus.IGNORED_NON_COMPLETED
            assert turn.failure_reason is not None

    def test_missing_sku_in_knowledge_store_is_handled_without_crash(self) -> None:
        base_plan = _load_e01_plan("product_education_10m")
        raw_plan = base_plan.model_dump()
        raw_plan["pinned_sku_ids"] = ["SKU-MISSING-999"]
        raw_plan["knowledge_versions_by_sku"] = {"SKU-MISSING-999": 1}
        raw_plan["arcs"] = [
            {
                "arc_id": "arc-missing",
                "position": 1,
                "title": "Arc SKU thiếu dữ liệu",
                "sku_id": "SKU-MISSING-999",
                "target_duration_sec": 120,
                "topics": [
                    {
                        "topic_id": "topic-missing-01",
                        "title": "Chủ đề SKU chưa có trong kho P05",
                        "sku_id": "SKU-MISSING-999",
                        "is_mandatory": True,
                        "fact_refs": ["ev-missing"],
                        "talking_points": ["Giới thiệu sản phẩm mới."],
                    }
                ],
            }
        ]
        missing_plan = StoryPlan.model_validate(raw_plan)
        adapter, _, _ = _make_p05_adapter()
        harness, bus, clock, initial_cp = _make_harness_and_bus(
            missing_plan,
            active_sku_id="SKU-MISSING-999",
        )
        baseline = ScriptFirstBaseline(
            knowledge_verifier=adapter,
            playback_bus=bus,
            harness=harness,
            clock=clock,
        )
        result = baseline.run_session(missing_plan)
        assert result.metrics.turns_attempted == 1
        assert result.metrics.safe_abort_count == 1
        assert result.metrics.playback_applied_count == 0
        assert result.final_checkpoint == initial_cp
        assert result.turns[0].outcome == AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE
        assert result.turns[0].failure_reason is not None
