"""Kiểm thử hồi quy ngoại tuyến cho gói khắc phục Pilot v1 (`P06-E01-T09` Remediation R01–R06).

1. File này giải quyết vấn đề gì?
   Kiểm chứng mọi sửa lỗi mục tiêu phát hiện từ Pilot v1 bằng fixture ngoại tuyến và mock client:
   - R01: Chặn rò rỉ ID nội bộ (`ev-...`, `clm-...`, `SKU-...`, JSON) khỏi lời thoại ở mọi lớp.
   - R02: Bắt buộc trích dẫn bằng chứng hợp lệ cho lời thoại factual (chặn lọt khi chỉ có giá),
          từ chối ID sai/chéo SKU, và vẫn cho phép non-factual bridge khi chính sách phù hợp.
   - R03/R05: Truyền ngân sách từ (`max_words`), lọc `mandatory_messages` theo SKU, chặn rút gọn
              lời thoại thành câu kiểu catalog mất `talking_points` (`TOPIC_OBJECTIVE_MISSED`).
   - R04: Sinh câu fallback hoàn chỉnh không cắt cụt `", thông tin."`, không lặp lại máy móc
          và rút lui `SAFE_ABORT_NO_CANDIDATE` khi hết fallback; giữ nghiêm `I-02`/`I-06`.
   - Provenance & Pilot v2: Kiểm chứng `blind_key_mapping.private.json`, OpenAPI sanitizer,
     và `run_gemini_pilot.py` hoàn toàn ngoại tuyến (0 cuộc gọi Gemini API thật).
2. Có những constraints nào?
   Mọi kiểm thử chạy 100% ngoại tuyến bằng `MockLLMProvider` hoặc `monkeypatch`; kết quả PASS
   xác nhận tính đúng đắn triển khai (không thay thế đánh giá chất lượng tiếng Việt trên LLM thật).
"""

from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from p06.adapters.mocks import MockPlaybackAckBus
from p06.adapters.p05_knowledge_adapter import P05KnowledgeAdapter
from p06.agent import (
    NODE_BOUNDED_REWRITE,
    NODE_VERIFY_P05,
    GraphRuntimeDeps,
    run_storytelling_turn,
)
from p06.agent.nodes._common import build_base_prompt_variables
from p06.baselines import (
    BaselineScriptSource,
    ScriptFirstBaseline,
    UpfrontChunkDraftLLMOutput,
)
from p06.evaluation.human_eval import export_blind_human_eval_sheets
from p06.evaluation.models import (
    EvaluationReport,
    GateStatus,
    MetricResult,
    MetricStatus,
    RunEvidence,
)
from p06.guardrails import (
    SafeFallbackSelector,
    check_spoken_text_hygiene,
    check_topic_objective_alignment,
    validate_draft_evidence_attribution,
)
from p06.memory.repetition_detector import RepetitionConfig, RepetitionDetector
from p06.planning.draft_dtos import ChunkDraftLLMOutput
from p06.providers.gemini_provider import (
    GeminiRawResponse,
    _sanitize_gemini_response_schema,
)
from p06.providers.mock_provider import MockBehavior, MockLLMProvider, MockResponseStep
from p06.runner.config import (
    ExperimentMethod,
    load_e01_story_plan,
    load_experiment_run_config,
)
from p06.runner.mock_fixtures import build_e01_mock_provider
from p06.runner.session_runner import _build_default_fallbacks_by_sku, run_experiment
from p06.schemas import (
    AgentTurnOutcome,
    CandidateOrigin,
    CandidateVerificationStatus,
    CoverageMode,
    ProposedResponseCoverage,
    SpeechCandidate,
    StoryCheckpoint,
    StoryChunkRole,
    StoryTopic,
    TargetScopeMode,
)
from p06.simulation import SimulatedPlaybackHarness, VirtualClock

P06_ROOT = Path(__file__).resolve().parents[2]
EXT_SKUS_PATH = P06_ROOT / "data" / "products" / "e01_ext_v1_verified_skus.json"
EXT_PLANS_PATH = P06_ROOT / "data" / "story_plans" / "e01_ext_v1_story_plans.json"
PILOT_SCRIPT_PATH = P06_ROOT / "experiments" / "p06_e01_no_comments" / "run_gemini_pilot.py"
START_AT = datetime(2026, 11, 27, 0, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def tmp_path() -> Iterator[Path]:
    """Cấp thư mục tạm cô lập trong `.pytest_cache` để tránh lỗi quyền Temp trên Windows."""
    base_dir = P06_ROOT / ".pytest_cache" / f"remed_tmp_{uuid.uuid4().hex[:10]}"
    base_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield base_dir
    finally:
        shutil.rmtree(base_dir, ignore_errors=True)


def _load_pilot_script_module() -> Any:
    """Nạp động module `run_gemini_pilot.py` để kiểm thử chữ ký và sổ cái ở chế độ mock."""
    spec = importlib.util.spec_from_file_location("run_gemini_pilot_test_mod", PILOT_SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_ext_pilot_context() -> tuple[Any, P05KnowledgeAdapter, VirtualClock]:
    """Nạp kịch bản `pilot_short_3sku_ext` và adapter `e01_ext_v1` cho test ngoại tuyến."""
    plan, _, _ = load_e01_story_plan("pilot_short_3sku_ext", story_plans_path=EXT_PLANS_PATH)
    adapter = P05KnowledgeAdapter.from_seed_file(EXT_SKUS_PATH)
    clock = VirtualClock(start_at=START_AT)
    return plan, adapter, clock


def _make_harness(plan: Any, clock: VirtualClock, sku_id: str) -> tuple[SimulatedPlaybackHarness, MockPlaybackAckBus]:
    """Khởi tạo harness và bus mô phỏng cho một `sku_id` cụ thể."""
    arc = next(a for a in plan.arcs if a.sku_id == sku_id)
    cp = StoryCheckpoint(
        tenant_id=plan.tenant_id,
        session_id=plan.session_id,
        session_epoch=1,
        plan_id=plan.plan_id,
        plan_revision=plan.plan_revision,
        active_sku_id=sku_id,
        current_arc_id=arc.arc_id,
        next_topic_id=arc.topics[0].topic_id,
        updated_at=clock.now(),
    )
    harness = SimulatedPlaybackHarness(
        initial_checkpoint=cp,
        expected_simulation_run_id="sim-run-remediation-test",
        story_plan=plan,
    )
    bus = MockPlaybackAckBus(clock=clock, simulation_run_id="sim-run-remediation-test")
    return harness, bus


def _dummy_report(evidence: RunEvidence) -> EvaluationReport:
    """Tạo `EvaluationReport` tối giản để kiểm thử runner và CLI mà không phụ thuộc evaluator nặng."""
    _ = evidence
    return EvaluationReport(
        experiment_id="P06-E01",
        run_id="dummy-eval",
        structural_hard_gates_status=GateStatus.PASS,
        overall_gate_status=GateStatus.NOT_EVALUATED,
        metrics={
            "dummy": MetricResult(
                name="dummy",
                value=1.0,
                status=MetricStatus.COMPUTED,
                source_fields=("transcript",),
            )
        },
    )


class TestR01InternalMetadataHygiene:
    """R01: Ngăn rò rỉ evidence_id, claim_id, SKU_id và mảnh JSON vào lời thoại nói."""

    @pytest.mark.parametrize(
        "dirty_text",
        [
            "Mắc ca sấy đối lưu thơm bơ (ev-e01-ext-macadamia-harvest, ev-e01-ext-macadamia-sensory).",
            "Sản phẩm đạt chuẩn theo clm-e01-ext-honey-allowed-03 đã duyệt.",
            "Mã SKU-HONEY-01 hiện có giá 159.000đ một chai.",
            'Chào bạn {"cited_evidence_ids": ["ev-1"]} rất ngon ạ.',
            "Dữ liệu lấy từ untrusted_knowledge_data rất an toàn.",
        ],
    )
    def test_spoken_text_hygiene_rejects_internal_metadata_without_mutating(self, dirty_text: str) -> None:
        res = check_spoken_text_hygiene(dirty_text)
        assert res.passed is False
        assert any("INTERNAL_METADATA_LEAK" in v for v in res.violations)

    def test_clean_spoken_text_passes_hygiene(self) -> None:
        res = check_spoken_text_hygiene(
            "Mắc ca sấy đối lưu nhiệt độ thấp giúp nhân chín đều, thơm bơ nhẹ và giòn tan."
        )
        assert res.passed is True
        assert res.violations == ()

    def test_p05_adapter_blocks_internal_id_leak_defense_in_depth(self) -> None:
        plan, adapter, clock = _load_ext_pilot_context()
        ev = adapter.get_sku_evidence(plan.tenant_id, "SKU-MACADAMIA-03", at_time=clock.now())
        cand = SpeechCandidate(
            candidate_id="cand-r01-p05",
            tenant_id=plan.tenant_id,
            session_id=plan.session_id,
            session_epoch=1,
            origin=CandidateOrigin.PROACTIVE_STORY,
            source_chunk_id="chunk-r01-p05",
            scope_mode=TargetScopeMode.SINGLE_SKU,
            sku_refs=["SKU-MACADAMIA-03"],
            sku_bindings=[ev.to_version_binding(cited_evidence_ids=["ev-e01-ext-macadamia-harvest"])],
            session_rights_version=1,
            intent="story_topic:topic-pilot-macadamia-01",
            text="Mắc ca sấy đối lưu thơm bơ nhẹ (ev-e01-ext-macadamia-harvest).",
            estimated_duration_sec=4.0,
            proposed_coverage=ProposedResponseCoverage(
                covered_topic_ids=["topic-pilot-macadamia-01"],
                covered_intents=["story_topic:topic-pilot-macadamia-01"],
                coverage_mode=CoverageMode.FULL,
            ),
            verification_status=CandidateVerificationStatus.DRAFT,
        )
        ver = adapter.verify_candidate(cand, verified_at=clock.now())
        assert ver.status == CandidateVerificationStatus.REJECTED
        assert "INTERNAL_METADATA_LEAK" in ver.reasons

    def test_script_first_and_langgraph_reject_raw_evidence_id_leak(self) -> None:
        plan, adapter, clock = _load_ext_pilot_context()
        harness_sf, bus_sf = _make_harness(plan, clock, "SKU-MACADAMIA-03")
        dirty_payload = {
            "text": "Mắc ca sấy đối lưu nhiệt độ thấp giữ độ giòn béo (ev-e01-ext-macadamia-harvest).",
            "cited_evidence_ids": ["ev-e01-ext-macadamia-harvest"],
            "covered_claim_ids": ["clm-e01-ext-macadamia-allowed-03"],
        }
        mock_sf = MockLLMProvider(
            response_sequence=[
                MockResponseStep(behavior=MockBehavior.VALID_JSON, payload=dirty_payload),
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload={
                        "text": "Hộp 500g giá 195.000đ kèm thanh tách thép và gói hút ẩm.",
                        "cited_evidence_ids": ["ev-e01-macadamia-shipping"],
                        "covered_claim_ids": ["clm-e01-macadamia-allowed-02"],
                        "stated_price_vnd": 195000,
                    },
                ),
            ]
        )
        baseline = ScriptFirstBaseline(
            knowledge_verifier=adapter,
            playback_bus=bus_sf,
            harness=harness_sf,
            clock=clock,
            llm_provider=mock_sf,
            script_source=BaselineScriptSource.UPFRONT_LLM,
        )
        sf_res = baseline.run_session(plan, active_sku_id="SKU-MACADAMIA-03")
        assert sf_res.turns[0].outcome == AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE
        assert "INTERNAL_METADATA_LEAK" in (sf_res.turns[0].failure_reason or "")

        # LangGraph chặn tại verify_p05 rồi sửa sạch qua bounded_rewrite.
        harness_lg, _ = _make_harness(plan, clock, "SKU-MACADAMIA-03")
        deps = GraphRuntimeDeps(
            llm_provider=MockLLMProvider(
                response_sequence=[
                    MockResponseStep(behavior=MockBehavior.VALID_JSON, payload=dirty_payload),
                    MockResponseStep(
                        behavior=MockBehavior.VALID_JSON,
                        payload={
                            "text": "Mắc ca sấy đối lưu nhiệt độ thấp giúp giữ trọn độ giòn béo tự nhiên.",
                            "cited_evidence_ids": ["ev-e01-ext-macadamia-harvest"],
                            "covered_claim_ids": ["clm-e01-ext-macadamia-allowed-03"],
                        },
                    ),
                ]
            ),
            knowledge_verifier=adapter,
            repetition_detector=RepetitionDetector(RepetitionConfig()),
            fallback_candidates=[],
            clock=clock,
            max_chunk_duration_sec=8.0,
        )
        lg_res = run_storytelling_turn(
            harness_lg.build_agent_state(plan, active_sku_id="SKU-MACADAMIA-03", max_rewrite_retries=1),
            deps,
            turn_id="turn-r01-lg",
        )
        assert lg_res.final_state.turn_outcome == AgentTurnOutcome.VERIFIED_READY
        assert NODE_BOUNDED_REWRITE in lg_res.final_state.node_trace
        assert "ev-" not in lg_res.final_state.verified_candidate.text


class TestR02EvidenceAttribution:
    """R02: Kiểm tra trích dẫn bằng chứng đầy đủ, chống cross-SKU và hỗ trợ non-factual bridge."""

    def test_missing_evidence_blocked_even_when_price_stated_in_langgraph_and_script_first(self) -> None:
        plan, adapter, clock = _load_ext_pilot_context()
        # Lỗi Pilot v1: stated_price_vnd=159000 nhưng cited_evidence_ids=[] phải bị chặn.
        price_only_no_ev = {
            "text": "Mật ong hoa cà phê vàng hổ phách dịu ngọt giá 159.000đ.",
            "cited_evidence_ids": [],
            "covered_claim_ids": [],
            "stated_price_vnd": 159000,
        }
        harness_lg, _ = _make_harness(plan, clock, "SKU-HONEY-01")
        deps = GraphRuntimeDeps(
            llm_provider=MockLLMProvider(
                response_sequence=[
                    MockResponseStep(behavior=MockBehavior.VALID_JSON, payload=price_only_no_ev),
                    MockResponseStep(
                        behavior=MockBehavior.VALID_JSON,
                        payload={
                            "text": "Mật ong sánh dẻo màu vàng hổ phách, vị ngọt dịu tự nhiên.",
                            "cited_evidence_ids": ["ev-e01-ext-honey-sensory"],
                            "covered_claim_ids": ["clm-e01-ext-honey-allowed-03"],
                        },
                    ),
                ]
            ),
            knowledge_verifier=adapter,
            repetition_detector=RepetitionDetector(RepetitionConfig()),
            fallback_candidates=[],
            clock=clock,
        )
        lg_res = run_storytelling_turn(
            harness_lg.build_agent_state(plan, active_sku_id="SKU-HONEY-01", max_rewrite_retries=1),
            deps,
            turn_id="turn-r02-lg",
        )
        assert lg_res.final_state.turn_outcome == AgentTurnOutcome.VERIFIED_READY
        assert NODE_VERIFY_P05 in lg_res.final_state.node_trace
        assert NODE_BOUNDED_REWRITE in lg_res.final_state.node_trace
        assert lg_res.final_state.verified_candidate.sku_bindings[0].cited_evidence_ids == [
            "ev-e01-ext-honey-sensory"
        ]

        # Script-first cũng phải từ chối cited_evidence_ids=[] dù có stated_price_vnd.
        harness_sf, bus_sf = _make_harness(plan, clock, "SKU-HONEY-01")
        baseline = ScriptFirstBaseline(
            knowledge_verifier=adapter,
            playback_bus=bus_sf,
            harness=harness_sf,
            clock=clock,
            llm_provider=MockLLMProvider(
                response_sequence=[
                    MockResponseStep(behavior=MockBehavior.VALID_JSON, payload=price_only_no_ev),
                    MockResponseStep(behavior=MockBehavior.VALID_JSON, payload=price_only_no_ev),
                ]
            ),
            script_source=BaselineScriptSource.UPFRONT_LLM,
        )
        sf_res = baseline.run_session(plan, active_sku_id="SKU-HONEY-01")
        assert all(t.outcome == AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE for t in sf_res.turns)
        assert all("MISSING_EVIDENCE_ATTRIBUTION" in (t.failure_reason or "") for t in sf_res.turns)

    def test_invalid_or_cross_sku_evidence_and_non_factual_bridge_policy(self) -> None:
        plan, adapter, clock = _load_ext_pilot_context()
        ev_honey = adapter.get_sku_evidence(plan.tenant_id, "SKU-HONEY-01", at_time=clock.now())
        topic_factual = plan.arcs[0].topics[0]

        bad_cross = validate_draft_evidence_attribution(
            text="Mật ong thu hái vùng cao.",
            role=StoryChunkRole.PRODUCT_STORY,
            cited_evidence_ids=["ev-e01-tea-origin"],
            covered_claim_ids=["clm-fake-01"],
            evidence=ev_honey,
            topic=topic_factual,
        )
        assert bad_cross.passed is False
        assert any("INVALID_OR_CROSS_SKU_EVIDENCE_ID" in r for r in bad_cross.failure_reasons)
        assert any("INVALID_CLAIM_ID" in r for r in bad_cross.failure_reasons)

        bridge_topic = StoryTopic(
            topic_id="topic-bridge-welcome",
            title="Chào khách đầu phiên",
            is_mandatory=False,
            fact_refs=[],
            talking_points=["Chào mừng quý khách đến với phiên live hôm nay."],
        )
        bridge_res = validate_draft_evidence_attribution(
            text="Xin chào quý khách đã ghé phiên livestream hôm nay ạ.",
            role=StoryChunkRole.TRANSITION_BRIDGE,
            cited_evidence_ids=[],
            covered_claim_ids=[],
            evidence=ev_honey,
            topic=bridge_topic,
            stated_price_vnd=None,
            mentions_ocop=False,
        )
        assert bridge_res.passed is True


class TestR03AndR05TopicObjectiveAndDuration:
    """R03 & R05: Kiểm tra từ vựng chủ đề, phản hồi ngân sách từ và lọc `mandatory_messages`."""

    def test_catalog_stub_flagged_by_topic_alignment_and_duration_rewrite_preserves_talking_points(
        self,
    ) -> None:
        plan, adapter, clock = _load_ext_pilot_context()
        ev_tea = adapter.get_sku_evidence(plan.tenant_id, "SKU-TEA-02", at_time=clock.now())
        topic_tea_02 = plan.arcs[1].topics[1]

        # (a) Bộ kiểm tra mục tiêu chủ đề phát hiện chính xác lỗi Pilot v1 rút gọn thành stub báo giá.
        stub_check = check_topic_objective_alignment(
            text="Trà Shan Tuyết 200g giá niêm yết 245.000đ.",
            topic=topic_tea_02,
            evidence=ev_tea,
        )
        assert stub_check.passed is False
        assert stub_check.reason is not None and "TOPIC_OBJECTIVE_MISSED" in stub_check.reason

        good_check = check_topic_objective_alignment(
            text="Hộp thiếc 200g hút chân không đẹp mắt, giá 245.000đ rất hợp làm quà biếu.",
            topic=topic_tea_02,
            evidence=ev_tea,
        )
        assert good_check.passed is True

        # (b) Khi vượt ngưỡng 8s, OVER_MAX_DURATION_SEC phản hồi kèm số từ + ngân sách từ + giữ talking_points.
        harness, _ = _make_harness(plan, clock, "SKU-TEA-02")
        state = harness.build_agent_state(plan, active_sku_id="SKU-TEA-02", max_rewrite_retries=2)
        state = state.validated_update(
            completed_topic_ids=frozenset({"topic-pilot-tea-01"}),
            story_checkpoint=state.story_checkpoint.model_copy(
                update={"next_topic_id": "topic-pilot-tea-02"}
            ),
        )
        too_long_draft = {
            "text": " ".join(
                ["Trà Shan Tuyết cổ thụ Hà Giang hộp thiếc hai trăm gam hút chân không"] * 2
            )
            + " giá hai trăm bốn mươi lăm nghìn.",
            "cited_evidence_ids": ["ev-e01-tea-shipping"],
            "covered_claim_ids": ["clm-e01-tea-allowed-02"],
            "stated_price_vnd": 245000,
        }
        rewritten_good = {
            "text": "Hộp thiếc 200g hút chân không đẹp mắt, giá 245.000đ rất hợp làm quà biếu.",
            "cited_evidence_ids": ["ev-e01-tea-shipping"],
            "covered_claim_ids": ["clm-e01-tea-allowed-02"],
            "stated_price_vnd": 245000,
        }
        deps_tea02 = GraphRuntimeDeps(
            llm_provider=MockLLMProvider(
                response_sequence=[
                    MockResponseStep(behavior=MockBehavior.VALID_JSON, payload=too_long_draft),
                    MockResponseStep(behavior=MockBehavior.VALID_JSON, payload=rewritten_good),
                ]
            ),
            knowledge_verifier=adapter,
            repetition_detector=RepetitionDetector(RepetitionConfig()),
            fallback_candidates=[],
            clock=clock,
            max_chunk_duration_sec=8.0,
        )
        res = run_storytelling_turn(state, deps_tea02, turn_id="turn-r05-tea02")
        assert res.final_state.turn_outcome == AgentTurnOutcome.VERIFIED_READY
        assert NODE_BOUNDED_REWRITE in res.final_state.node_trace
        assert "talking_points" in res.draft_attempts[0].failure_reasons[0]
        assert "từ" in res.draft_attempts[0].failure_reasons[0]
        assert "quà biếu" in res.final_state.verified_candidate.text

    def test_prompt_variables_include_word_budget_and_sku_scoped_mandatory_messages(self) -> None:
        plan, adapter, clock = _load_ext_pilot_context()
        harness, _ = _make_harness(plan, clock, "SKU-HONEY-01")
        state = harness.build_agent_state(plan, active_sku_id="SKU-HONEY-01")
        ev = adapter.get_sku_evidence(plan.tenant_id, "SKU-HONEY-01", at_time=clock.now())
        variables = build_base_prompt_variables(
            state=state,
            evidence=ev,
            arc_title=plan.arcs[0].title,
            topic=plan.arcs[0].topics[0],
            max_duration_sec=8.0,
        )
        assert int(variables["max_words"]) == 18
        assert "12–18 từ" in variables["target_words_range"]
        assert "ev-e01-ext-honey-sensory" in variables["allowed_evidence_ids"]
        assert "clm-e01-ext-honey-allowed-03" in variables["allowed_claim_ids"]
        assert "Mật ong" in variables["mandatory_messages"]
        assert "Trà Shan Tuyết" not in variables["mandatory_messages"]
        assert "Mắc ca" not in variables["mandatory_messages"]


class TestR04NaturalFallbackAndNonRepetition:
    """R04: Fallback hoàn chỉnh không cắt cụt `", thông tin."`, không lặp máy móc và giữ `I-02`/`I-06`."""

    def test_default_fallbacks_complete_hygienic_within_8s_and_live_verified(self) -> None:
        plan, adapter, clock = _load_ext_pilot_context()
        fallbacks_by_sku = _build_default_fallbacks_by_sku(
            story_plan=plan,
            evidence_adapter=adapter,
            at_time=clock.now(),
        )
        for sku_id, candidates in fallbacks_by_sku.items():
            assert len(candidates) >= 2, f"SKU {sku_id} phải có >= 2 mẫu fallback khác nhau."
            texts = [c.text for c in candidates]
            assert len(set(texts)) == len(texts)
            for cand in candidates:
                assert not cand.text.endswith(", thông tin.")
                assert cand.text.endswith(".")
                assert cand.estimated_duration_sec <= 8.0
                assert check_spoken_text_hygiene(cand.text).passed is True
                assert cand.proposed_coverage.covered_topic_ids == []
                ver = adapter.verify_candidate(cand, verified_at=clock.now())
                assert ver.status == CandidateVerificationStatus.VERIFIED

    def test_repeated_failures_exhaust_fallback_to_safe_abort_without_advancing_topics(self) -> None:
        plan, adapter, clock = _load_ext_pilot_context()
        harness, bus = _make_harness(plan, clock, "SKU-HONEY-01")
        fallbacks = _build_default_fallbacks_by_sku(
            story_plan=plan,
            evidence_adapter=adapter,
            at_time=clock.now(),
        )["SKU-HONEY-01"]

        outcomes: list[AgentTurnOutcome] = []
        spoken_fallbacks: list[str] = []
        for idx in range(len(fallbacks) + 1):
            deps = GraphRuntimeDeps(
                llm_provider=MockLLMProvider(
                    response_sequence=[MockResponseStep(behavior=MockBehavior.PROVIDER_FAILURE)]
                ),
                knowledge_verifier=adapter,
                repetition_detector=RepetitionDetector(RepetitionConfig()),
                fallback_candidates=list(fallbacks),
                clock=clock,
            )
            state = harness.build_agent_state(plan, active_sku_id="SKU-HONEY-01")
            res = run_storytelling_turn(state, deps, turn_id=f"turn-r04-{idx}", sequence_index=idx)
            outcomes.append(res.final_state.turn_outcome)
            if res.final_state.verified_candidate is not None:
                cand = res.final_state.verified_candidate
                spoken_fallbacks.append(cand.text)
                harness.register_pending_turn(
                    turn_id=f"turn-r04-{idx}",
                    candidate=cand,
                    plan_revision=plan.plan_revision,
                    covered_claim_ids=(),
                )
                ack = bus.dispatch_turn(cand, turn_id=f"turn-r04-{idx}", plan_revision=plan.plan_revision)
                harness.apply_ack(ack)

        assert outcomes[:-1] == [AgentTurnOutcome.FALLBACK_PREAPPROVED] * len(fallbacks)
        assert outcomes[-1] == AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE
        assert len(set(spoken_fallbacks)) == len(fallbacks)
        # Bất biến I-06: Fallback và Safe Abort tuyệt đối không làm tăng topic coverage.
        assert harness.completed_topic_ids == frozenset()


class TestProvenanceSanitizationAndPilotRunnerOffline:
    """Kiểm chứng Blind Export Provenance, Gemini Schema Sanitizer, và `run_gemini_pilot.py` offline."""

    def test_blind_human_eval_export_includes_private_provenance_without_leaking_to_csv(
        self, tmp_path: Path
    ) -> None:
        plan, adapter, clock = _load_ext_pilot_context()
        provider = build_e01_mock_provider(plan, adapter, include_claim_ids=False, seed=42)
        cfg = load_experiment_run_config(
            scenario="pilot_short_3sku_ext",
            dataset_profile="e01_ext_v1",
            method=ExperimentMethod.SCRIPT_FIRST_UPFRONT_LLM,
            provider="mock",
            seed=42,
            output_dir=tmp_path / "runs",
        )
        run_res = run_experiment(cfg, custom_llm_provider=provider)
        csv_p, jsonl_p, map_p = export_blind_human_eval_sheets(
            [run_res.run_dir], tmp_path / "blind_out", seed=42
        )

        mapping = json.loads(map_p.read_text(encoding="utf-8"))
        assert mapping[0]["dataset_profile"] == "e01_ext_v1"
        assert mapping[0]["prompt_versions"]["baseline_script_first"] == "baseline-script-first-v0.2"
        assert mapping[0]["prompt_versions"]["story_generation.txt"] == "v0.2"
        assert mapping[0]["prompt_versions"]["rewrite.txt"] == "v0.2"
        assert mapping[0]["exported_at_utc"].endswith("Z")

        csv_text = csv_p.read_text(encoding="utf-8")
        jsonl_text = jsonl_p.read_text(encoding="utf-8")
        assert "e01_ext_v1" not in csv_text
        assert "baseline-script-first-v0.2" not in jsonl_text
        with csv_p.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 1
        assert rows[0]["narrative_coherence"] == ""

    def test_gemini_sanitizer_preserves_required_citations_and_strips_exclusive_min(self) -> None:
        for schema_cls in (ChunkDraftLLMOutput, UpfrontChunkDraftLLMOutput):
            raw_schema = schema_cls.model_json_schema()
            assert "cited_evidence_ids" in raw_schema["required"]
            assert "covered_claim_ids" in raw_schema["required"]
            clean = _sanitize_gemini_response_schema(raw_schema)
            assert "cited_evidence_ids" in clean["required"]
            assert "covered_claim_ids" in clean["required"]
            stated_price = clean["properties"]["stated_price_vnd"]
            assert "exclusiveMinimum" not in json.dumps(stated_price)

    def test_run_gemini_pilot_stage_a_verify_signature_and_partial_token_summary(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pilot_mod = _load_pilot_script_module()

        class FakeGeminiRestClient:
            """Mock `GeminiRestClient` hoàn toàn ngoại tuyến để kiểm tra `run_gemini_pilot.py`."""

            def __init__(self, *args: Any, **kwargs: Any) -> None:
                _ = (args, kwargs)
                self.requests_attempted = 0
                self.rate_limited = False
                self.last_response_headers = {"content-type": "application/json"}

            def check_model_metadata(self, model_id: str, timeout_sec: float = 30.0) -> dict[str, Any]:
                _ = timeout_sec
                self.requests_attempted += 1
                return {"name": f"models/{model_id}", "displayName": "Gemini Mock", "version": "mock-1"}

            def generate_json(
                self,
                model_id: str,
                system_prompt: str,
                user_prompt: str,
                json_schema: dict[str, Any],
                sampling: dict[str, Any],
                timeout_sec: float,
            ) -> Any:
                _ = (model_id, system_prompt, json_schema, sampling, timeout_sec)
                self.requests_attempted += 1
                is_tea = "SKU-TEA-02" in user_prompt
                payload = (
                    {
                        "text": "Trà Shan Tuyết cổ thụ nước vàng mơ sáng trong, hậu ngọt sâu.",
                        "role": "PRODUCT_STORY",
                        "cited_evidence_ids": ["ev-e01-ext-tea-sensory"],
                        "covered_claim_ids": ["clm-e01-ext-tea-allowed-03"],
                        "stated_price_vnd": None,
                        "mentions_ocop": False,
                        "semantic_breakpoint": True,
                        "breakpoint_type": "TOPIC_END",
                        "rationale": "Mock offline test",
                    }
                    if is_tea
                    else {
                        "text": "Mật ong hoa cà phê vàng hổ phách sóng sánh, vị ngọt dịu tự nhiên.",
                        "role": "PRODUCT_STORY",
                        "cited_evidence_ids": ["ev-e01-ext-honey-sensory"],
                        "covered_claim_ids": ["clm-e01-ext-honey-allowed-03"],
                        "stated_price_vnd": None,
                        "mentions_ocop": False,
                        "semantic_breakpoint": True,
                        "breakpoint_type": "TOPIC_END",
                        "rationale": "Mock offline test",
                    }
                )
                return GeminiRawResponse(
                    raw_text=json.dumps(payload, ensure_ascii=False),
                    input_tokens=150,
                    output_tokens=45,
                    thinking_tokens=None,
                    finish_reason="STOP",
                )

        monkeypatch.setattr(pilot_mod, "GeminiRestClient", FakeGeminiRestClient)
        out_v2 = tmp_path / "gemini_3.5_flash_lite_pilot_v2"
        cfg_path = P06_ROOT / "configs" / "models" / "gemini_3.5_flash_lite_free.yaml"
        rc = pilot_mod._run_stage_a_smoke(out_v2, cfg_path)
        assert rc == 0
        smoke_doc = json.loads((out_v2 / "stage_a_smoke_results.json").read_text(encoding="utf-8"))
        assert smoke_doc["all_passed"] is True
        assert smoke_doc["checks"]["request_2_chunk_draft_dto"]["p05_verification"]["status"] == "VERIFIED"
        assert smoke_doc["checks"]["request_3_upfront_draft_dto"]["p05_verification"]["status"] == "VERIFIED"

        # Kiểm tra `_summarize_partial_token_usage` tách rạch ròi measured calls với failed calls.
        run_dir = tmp_path / "partial_run"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "token_usage.json").write_text(
            json.dumps(
                {"token_usage_source": "UNAVAILABLE", "input_tokens": None, "output_tokens": None}
            ),
            encoding="utf-8",
        )
        (run_dir / "provider_calls.jsonl").write_text(
            "\n".join(
                [
                    json.dumps({"call_index": 0, "token_usage_source": "MEASURED", "input_tokens": 1000, "output_tokens": 50}),
                    json.dumps({"call_index": 1, "token_usage_source": "UNAVAILABLE", "input_tokens": None, "output_tokens": None}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        summary = pilot_mod._summarize_partial_token_usage(run_dir)
        assert summary["aggregate_token_usage_source"] == "UNAVAILABLE"
        assert summary["aggregate_input_tokens"] is None
        assert summary["measured_calls_count"] == 1
        assert summary["failed_calls_count"] == 1
        assert summary["missing_token_call_indices"] == [1]
        assert summary["partial_measured_input_tokens"] == 1000
        assert summary["partial_measured_output_tokens"] == 50

    def test_pilot_short_3sku_ext_offline_mock_dryrun_both_methods(self, tmp_path: Path) -> None:
        plan, adapter, _ = _load_ext_pilot_context()
        sf_provider = build_e01_mock_provider(plan, adapter, include_claim_ids=True, seed=42)
        lg_provider = build_e01_mock_provider(plan, adapter, include_claim_ids=True, seed=42)

        cfg_sf = load_experiment_run_config(
            scenario="pilot_short_3sku_ext",
            dataset_profile="e01_ext_v1",
            method=ExperimentMethod.SCRIPT_FIRST_UPFRONT_LLM,
            provider="mock",
            seed=42,
            output_dir=tmp_path / "sf",
        )
        cfg_lg = load_experiment_run_config(
            scenario="pilot_short_3sku_ext",
            dataset_profile="e01_ext_v1",
            method=ExperimentMethod.LANGGRAPH,
            history_window=5,
            provider="mock",
            seed=42,
            output_dir=tmp_path / "lg",
        )
        res_sf = run_experiment(cfg_sf, custom_llm_provider=sf_provider)
        res_lg = run_experiment(cfg_lg, custom_llm_provider=lg_provider)

        assert res_sf.report is not None
        assert res_lg.report is not None
        assert res_sf.report.coverage["mandatory_topic_coverage"].value == pytest.approx(1.0)
        assert res_lg.report.coverage["mandatory_topic_coverage"].value == pytest.approx(1.0)
        for entry in (*res_sf.evidence.transcript, *res_lg.evidence.transcript):
            assert check_spoken_text_hygiene(entry.text).passed is True
