"""Kiểm thử hồi quy cho các phát hiện kiểm toán Phase 3 trước khi chạy Phase 4 (`E01-T08`).

1. File này giải quyết vấn đề gì?
   Khóa chặt các bản sửa lỗi có bằng chứng từ Wave A (Scouts A & B): chuyển `active_sku_id` ở biên
   điều phối qua 3 SKU, cô lập lỗi `OptionalSemanticMemory.index_played_turn()`, xóa `next_topic_id_hint`
   trên nhánh `safe_fallback`, ghi nhận đủ trace theo từng attempt trong `AgentTurnResult`, đồng bộ
   `max_chunk_duration_sec` trên `ScriptFirstBaseline`, và hỗ trợ `seeded_variants_by_schema` trong
   `ProviderFactory`.
2. Trách nhiệm chính của module là gì?
   Kiểm định đơn vị và hợp đồng cho từng điểm sửa mà không làm vỡ 189 test cũ.
3. Module này liên kết với các thành phần nào?
   Kiểm thử `p06.schemas.events`, `p06.simulation.playback_harness`, `p06.agent`,
   `p06.baselines.script_first`, `p06.providers.factory` và `p06.evaluation.models`.
4. Input và output chính là gì?
   Input là dữ liệu synthetic E01 và `MockLLMProvider`; output là các khẳng định bất biến `I-02..I-06`.
5. Có những constraints hoặc invariants quan trọng nào?
   Chạy 100% ngoại tuyến bằng `MockLLMProvider`.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence

import pytest
from pydantic import ValidationError

from p06.adapters.interfaces import AckApplyStatus
from p06.adapters.mocks.playback_bus import MockPlaybackAckBus
from p06.adapters.p05_knowledge_adapter import P05KnowledgeAdapter
from p06.agent import GraphRuntimeDeps, run_storytelling_turn
from p06.baselines.script_first import BaselineScriptSource, ScriptFirstBaseline
from p06.evaluation.models import MetricProvenance, MetricResult, MetricStatus
from p06.memory import OptionalSemanticMemory, RepetitionDetector
from p06.planning.draft_dtos import ChunkDraftLLMOutput
from p06.providers.base import GenerationRequest, ProviderConfigError
from p06.providers.factory import ProviderFactory
from p06.providers.mock_provider import MockBehavior, MockResponseStep
from p06.schemas.candidate import (
    CandidateOrigin,
    CandidateVerificationStatus,
    CoverageMode,
    ProposedResponseCoverage,
    SkuVersionBinding,
    SpeechCandidate,
    TargetScopeMode,
)
from p06.schemas.events import StoryCheckpoint
from p06.schemas.state import AgentTurnOutcome, PlayedTurnSummary
from p06.schemas.story import StoryPlan
from p06.simulation import SimulatedPlaybackHarness, VirtualClock

MODULE_ROOT = Path(__file__).resolve().parents[2]
VERIFIED_SEED_PATH = MODULE_ROOT / "data" / "products" / "e01_verified_skus.json"
STORY_PLANS_PATH = MODULE_ROOT / "data" / "story_plans" / "e01_story_plans.json"
MODELS_DIR = MODULE_ROOT / "configs" / "models"
TENANT_ID = "tenant-p06-poc-01"
START_AT = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)


def _load_plan(key: str = "product_education_10m") -> StoryPlan:
    raw = json.loads(STORY_PLANS_PATH.read_text(encoding="utf-8"))
    return StoryPlan.model_validate(raw["plans"][key])


def _make_verified_candidate(
    *,
    turn_id: str,
    session_id: str,
    sku_id: str,
    chunk_id: str,
    topic_id: str,
    text: str,
    evidence_id: str,
    price_vnd: int,
    adapter: P05KnowledgeAdapter,
) -> SpeechCandidate:
    ev = adapter.get_sku_evidence(TENANT_ID, sku_id, at_time=START_AT)
    draft = SpeechCandidate(
        candidate_id=f"cand-{turn_id}",
        turn_id=turn_id,
        tenant_id=TENANT_ID,
        session_id=session_id,
        session_epoch=1,
        origin=CandidateOrigin.PROACTIVE_STORY,
        source_chunk_id=chunk_id,
        scope_mode=TargetScopeMode.SINGLE_SKU,
        sku_refs=[sku_id],
        sku_bindings=[
            SkuVersionBinding(
                sku_id=sku_id,
                knowledge_version=ev.knowledge_version,
                ocop_version=ev.ocop_version,
                rights_version=ev.rights_version,
                cited_evidence_ids=[evidence_id],
                stated_price_vnd=price_vnd,
                mentions_ocop=False,
            )
        ],
        session_rights_version=1,
        intent=f"PROACTIVE_STORY:{topic_id}",
        text=text,
        semantic_breakpoint=True,
        estimated_duration_sec=4.0,
        proposed_coverage=ProposedResponseCoverage(
            covered_topic_ids=[topic_id],
            covered_intents=[topic_id],
            coverage_mode=CoverageMode.FULL,
            is_authoritative=False,
        ),
        verification_status=CandidateVerificationStatus.DRAFT,
        rewrite_attempt=0,
        created_at=START_AT,
    )
    ver = adapter.verify_candidate(draft, verified_at=START_AT)
    assert ver.status == CandidateVerificationStatus.VERIFIED
    return ver.candidate


class _FailingSemanticMemory(OptionalSemanticMemory):
    """Giả lập lỗi trong `index_played_turn()` sau khi checkpoint cốt lõi đã commit."""

    @property
    def is_enabled(self) -> bool:
        return True

    def index_played_turn(self, turn: PlayedTurnSummary) -> None:
        raise RuntimeError(f"Simulated semantic index failure for {turn.turn_id}")

    def query_similar(
        self,
        candidate_text: str,
        *,
        sku_id: str | None = None,
        top_k: int = 5,
    ) -> Sequence[tuple[PlayedTurnSummary, float]]:
        _ = candidate_text, sku_id, top_k
        return ()

    def clear(self) -> None:
        return None


def test_switch_active_sku_across_3_skus_preserves_history_and_blocks_pending() -> None:
    """F-02 / AUD-02: Chuyển SKU ở biên điều phối giữ nguyên history/dedup/coverage và chặn nếu còn pending."""
    plan = _load_plan("product_education_10m")
    adapter = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
    clock = VirtualClock(start_at=START_AT)
    bus = MockPlaybackAckBus(clock=clock, simulation_run_id="sim-audit-01")
    initial_cp = StoryCheckpoint(
        tenant_id=plan.tenant_id,
        session_id=plan.session_id,
        session_epoch=1,
        plan_id=plan.plan_id,
        plan_revision=plan.plan_revision,
        active_sku_id="SKU-HONEY-01",
        current_arc_id=plan.arcs[0].arc_id,
        next_topic_id=plan.arcs[0].topics[0].topic_id,
        updated_at=START_AT,
    )
    harness = SimulatedPlaybackHarness(
        initial_checkpoint=initial_cp,
        expected_simulation_run_id="sim-audit-01",
        story_plan=plan,
        played_history_window_size=5,
    )

    cand_honey = _make_verified_candidate(
        turn_id="turn-h1",
        session_id=plan.session_id,
        sku_id="SKU-HONEY-01",
        chunk_id="chunk-h1",
        topic_id=plan.arcs[0].topics[0].topic_id,
        text="Mật ong hoa cà phê Đắk Lắk nguyên chất giá 159.000đ một chai.",
        evidence_id="ev-e01-honey-usage",
        price_vnd=159000,
        adapter=adapter,
    )
    harness.register_pending_turn(
        turn_id="turn-h1",
        candidate=cand_honey,
        plan_revision=plan.plan_revision,
        chunk_id="chunk-h1",
        next_topic_id=plan.arcs[0].topics[1].topic_id,
    )
    with pytest.raises(ValueError, match="đang chờ ACK"):
        harness.switch_active_sku("SKU-TEA-02", story_plan=plan, updated_at=clock.now())

    ack1 = bus.dispatch_turn(cand_honey, turn_id="turn-h1", plan_revision=plan.plan_revision)
    assert harness.apply_ack(ack1).applied is True

    with pytest.raises(ValueError, match="pinned_sku_ids"):
        harness.switch_active_sku("SKU-UNKNOWN-99", story_plan=plan, updated_at=clock.now())

    cp_tea = harness.switch_active_sku("SKU-TEA-02", story_plan=plan, updated_at=clock.now())
    assert cp_tea.active_sku_id == "SKU-TEA-02"
    assert cp_tea.current_arc_id == plan.arcs[1].arc_id
    assert cp_tea.next_topic_id == plan.arcs[1].topics[0].topic_id
    assert cp_tea.last_completed_chunk_id == "chunk-h1"
    assert len(harness.played_history) == 1
    assert harness.completed_topic_ids == frozenset({plan.arcs[0].topics[0].topic_id})

    state_tea = harness.build_agent_state(plan, active_sku_id="SKU-TEA-02")
    assert state_tea.active_sku_id == "SKU-TEA-02"
    assert len(state_tea.played_history) == 1


def test_semantic_memory_exception_after_commit_is_isolated() -> None:
    """F-03: Ngoại lệ ở `OptionalSemanticMemory.index_played_turn()` không làm mất `APPLIED` hay cho phép replay."""
    plan = _load_plan("product_education_10m")
    adapter = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
    clock = VirtualClock(start_at=START_AT)
    bus = MockPlaybackAckBus(clock=clock, simulation_run_id="sim-audit-02")
    initial_cp = StoryCheckpoint(
        tenant_id=plan.tenant_id,
        session_id=plan.session_id,
        session_epoch=1,
        plan_id=plan.plan_id,
        plan_revision=plan.plan_revision,
        active_sku_id="SKU-HONEY-01",
        current_arc_id=plan.arcs[0].arc_id,
        next_topic_id=plan.arcs[0].topics[0].topic_id,
        updated_at=START_AT,
    )
    harness = SimulatedPlaybackHarness(
        initial_checkpoint=initial_cp,
        expected_simulation_run_id="sim-audit-02",
        story_plan=plan,
        semantic_memory=_FailingSemanticMemory(),
    )
    cand = _make_verified_candidate(
        turn_id="turn-sem-1",
        session_id=plan.session_id,
        sku_id="SKU-HONEY-01",
        chunk_id="chunk-sem-1",
        topic_id=plan.arcs[0].topics[0].topic_id,
        text="Mật ong hoa cà phê nguyên chất đóng chai 500ml giá 159.000đ.",
        evidence_id="ev-e01-honey-usage",
        price_vnd=159000,
        adapter=adapter,
    )
    harness.register_pending_turn(
        turn_id="turn-sem-1",
        candidate=cand,
        plan_revision=plan.plan_revision,
        chunk_id="chunk-sem-1",
        next_topic_id=plan.arcs[0].topics[1].topic_id,
    )
    ack = bus.dispatch_turn(cand, turn_id="turn-sem-1", plan_revision=plan.plan_revision)
    result = harness.apply_ack(ack)

    assert result.status == AckApplyStatus.APPLIED
    assert result.applied is True
    assert result.auto_replay_permitted is False
    assert result.semantic_index_error is not None
    assert "RuntimeError" in result.semantic_index_error
    assert len(harness.semantic_index_errors) == 1
    assert harness.checkpoint.last_completed_chunk_id == "chunk-sem-1"

    dup = harness.apply_ack(ack)
    assert dup.status == AckApplyStatus.REJECTED_DUPLICATE
    assert dup.applied is False


def test_safe_fallback_clears_next_topic_hint_and_captures_per_attempt_traces() -> None:
    """F-06 & F-07: `safe_fallback` xóa hint chuyển topic và `AgentTurnResult` giữ đủ dấu vết mọi attempt."""
    plan = _load_plan("product_education_10m")
    adapter = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
    ev = adapter.get_sku_evidence(TENANT_ID, "SKU-HONEY-01", at_time=START_AT)
    clock = VirtualClock(start_at=START_AT)
    initial_cp = StoryCheckpoint(
        tenant_id=plan.tenant_id,
        session_id=plan.session_id,
        session_epoch=1,
        plan_id=plan.plan_id,
        plan_revision=plan.plan_revision,
        active_sku_id="SKU-HONEY-01",
        current_arc_id=plan.arcs[0].arc_id,
        next_topic_id=plan.arcs[0].topics[0].topic_id,
        updated_at=START_AT,
    )
    harness = SimulatedPlaybackHarness(
        initial_checkpoint=initial_cp,
        expected_simulation_run_id="sim-audit-03",
        story_plan=plan,
    )
    fallback_cand = SpeechCandidate(
        candidate_id="cand-fb-audit",
        tenant_id=plan.tenant_id,
        session_id=plan.session_id,
        session_epoch=1,
        origin=CandidateOrigin.PREAPPROVED_FALLBACK,
        source_chunk_id="chunk-fb-audit",
        scope_mode=TargetScopeMode.SINGLE_SKU,
        sku_refs=["SKU-HONEY-01"],
        sku_bindings=[
            SkuVersionBinding(
                sku_id="SKU-HONEY-01",
                knowledge_version=ev.knowledge_version,
                ocop_version=ev.ocop_version,
                rights_version=ev.rights_version,
                cited_evidence_ids=["ev-e01-honey-usage"],
                stated_price_vnd=159000,
                mentions_ocop=False,
            )
        ],
        session_rights_version=1,
        intent="SAFE_FALLBACK:SKU-HONEY-01",
        text="Mật ong hoa cà phê Đắk Lắk chai 500ml có giá niêm yết 159.000đ.",
        semantic_breakpoint=True,
        estimated_duration_sec=4.0,
        proposed_coverage=ProposedResponseCoverage(
            covered_topic_ids=[],
            covered_intents=["safe_fallback"],
            coverage_mode=CoverageMode.FULL,
            is_authoritative=False,
        ),
        verification_status=CandidateVerificationStatus.DRAFT,
        rewrite_attempt=0,
        created_at=START_AT,
    )

    bad_payload = {
        "text": "Mật ong hoa cà phê giá chỉ 99.000đ thôi ạ.",
        "cited_evidence_ids": ["ev-e01-honey-usage"],
        "stated_price_vnd": 99000,
        "mentions_ocop": False,
        "covered_claim_ids": ["CLM-HONEY-01"],
        "semantic_breakpoint": True,
    }
    provider = ProviderFactory.from_yaml(
        MODELS_DIR / "mock.yaml",
        response_sequence=[
            MockResponseStep(behavior=MockBehavior.VALID_JSON, payload=bad_payload),
            MockResponseStep(behavior=MockBehavior.VALID_JSON, payload=bad_payload),
        ],
    )
    deps = GraphRuntimeDeps(
        llm_provider=provider,
        knowledge_verifier=adapter,
        repetition_detector=RepetitionDetector(),
        fallback_candidates=[fallback_cand],
        clock=clock,
        max_chunk_duration_sec=8.0,
        seed=42,
    )
    state = harness.build_agent_state(plan, active_sku_id="SKU-HONEY-01", max_rewrite_retries=1)
    result = run_storytelling_turn(state, deps, turn_id="turn-fb-01", sequence_index=0)

    assert result.final_state.turn_outcome == AgentTurnOutcome.FALLBACK_PREAPPROVED
    assert result.next_topic_id_hint is None
    assert result.next_arc_id_hint is None
    assert len(result.draft_attempts) == 2
    assert len(result.repetition_checks) == 2
    assert len(result.p05_decisions) == 2
    assert all(d.status == "REJECTED" for d in result.p05_decisions)


def test_script_first_duration_parity_and_provider_factory_seeded_variants_by_schema() -> None:
    """AUD-03 & AUD-04: `ScriptFirstBaseline(max_chunk_duration_sec=8.0)` đồng bộ 8s và `ProviderFactory` truyền `seeded_variants_by_schema`."""
    plan = _load_plan("product_education_10m")
    adapter = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
    clock = VirtualClock(start_at=START_AT)
    bus = MockPlaybackAckBus(clock=clock, simulation_run_id="sim-audit-04")
    initial_cp = StoryCheckpoint(
        tenant_id=plan.tenant_id,
        session_id=plan.session_id,
        session_epoch=1,
        plan_id=plan.plan_id,
        plan_revision=plan.plan_revision,
        active_sku_id="SKU-HONEY-01",
        current_arc_id=plan.arcs[0].arc_id,
        next_topic_id=plan.arcs[0].topics[0].topic_id,
        updated_at=START_AT,
    )
    harness = SimulatedPlaybackHarness(
        initial_checkpoint=initial_cp,
        expected_simulation_run_id="sim-audit-04",
        story_plan=plan,
    )
    baseline = ScriptFirstBaseline(
        knowledge_verifier=adapter,
        playback_bus=bus,
        harness=harness,
        clock=clock,
        script_source=BaselineScriptSource.DETERMINISTIC_TALKING_POINTS,
        max_chunk_duration_sec=8.0,
    )
    res = baseline.run_session(plan, active_sku_id="SKU-HONEY-01")
    assert len(res.turns) == 2
    for turn in res.turns:
        assert turn.spoken_text is not None
        assert len(turn.spoken_text.split()) <= 18
        assert turn.actual_duration_ms is not None
        assert turn.actual_duration_ms <= 8000
    assert len(res.playback_events) == 2

    mock_provider = ProviderFactory.from_yaml(
        MODELS_DIR / "mock.yaml",
        seed=42,
        seeded_variants_by_schema={
            "ChunkDraftLLMOutput": [
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload={
                        "text": "Mật ong hoa cà phê Đắk Lắk nguyên chất giá 159.000đ.",
                        "cited_evidence_ids": ["ev-e01-honey-usage"],
                        "stated_price_vnd": 159000,
                        "mentions_ocop": False,
                        "covered_claim_ids": ["CLM-HONEY-01"],
                        "semantic_breakpoint": True,
                    },
                )
            ]
        },
    )
    gen = mock_provider.generate_structured(
        GenerationRequest(
            request_id="req-schema-1",
            system_prompt="sys",
            user_prompt="user",
            prompt_version="v0.1",
            seed=42,
        ),
        ChunkDraftLLMOutput,
    )
    assert gen.parsed_output.stated_price_vnd == 159000

    with pytest.raises(ProviderConfigError):
        ProviderFactory.from_yaml(
            MODELS_DIR / "ollama_qwen3_1.7b.yaml",
            seeded_variants_by_schema={"ChunkDraftLLMOutput": []},
        )


def test_metric_result_enforces_none_value_when_not_computed() -> None:
    """Khóa bất biến `MetricResult`: không được gán giá trị `0` giả khi thiếu dữ liệu."""
    with pytest.raises(ValidationError, match="bắt buộc value phải là None"):
        MetricResult(
            name="estimated_llm_cost_usd",
            status=MetricStatus.NOT_APPLICABLE,
            value=0.0,
            unit="USD",
            data_source="provider_calls.jsonl",
            provenance=MetricProvenance.UNAVAILABLE,
            missing_reason="Mock provider",
        )
    valid = MetricResult(
        name="estimated_llm_cost_usd",
        status=MetricStatus.NOT_APPLICABLE,
        value=None,
        unit="USD",
        data_source="provider_calls.jsonl",
        provenance=MetricProvenance.UNAVAILABLE,
        is_simulated=True,
        missing_reason="Mock provider tokens are simulated and have no real USD cost.",
    )
    assert valid.value is None
