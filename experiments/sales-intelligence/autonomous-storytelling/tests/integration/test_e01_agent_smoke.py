"""Bộ kiểm thử tích hợp end-to-end 17 kịch bản cho P06-E01 Agent Core (Tier 1 Mock).

1. File này giải quyết vấn đề gì?
   Xác minh toàn bộ luồng khép kín `StoryPlan -> LangGraph 8 node -> P05KnowledgeAdapter ->
   MockPlaybackAckBus -> SimulatedPlaybackHarness (ShortTermPlayedHistory + GlobalTopicCoverage)`
   với 17 kịch bản an toàn và chống lặp cốt lõi của Phase 3.
2. Trách nhiệm chính của module là gì?
   Chạy kiểm thử tích hợp hoàn toàn ngoại tuyến, tất định dựa trên bộ dữ liệu synthetic
   (`e01_verified_skus.json`, `e01_negative_skus.json`, `e01_story_plans.json`) và `MockLLMProvider`.
3. Module này liên kết với các thành phần nào?
   Tích hợp `p06.agent`, `p06.planning`, `p06.memory`, `p06.adapters`, `p06.guardrails`,
   `p06.providers.mock_provider` và `p06.simulation`.
4. Input và output chính là gì?
   Input là kịch bản synthetic + `MockLLMProvider`;
   Output là xác nhận 17 kịch bản chạy đúng bất biến `I-01..I-06` và tái lập 100%.
5. Có những constraints hoặc invariants quan trọng nào?
   Mọi kết quả dưới đây dùng `MockLLMProvider` (`UNIT_TEST`), tuyệt đối KHÔNG phải bằng chứng
   chất lượng tiếng Việt hay năng lực sinh thoại của LLM thật (`Gemini`/`Ollama`).
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from p06.adapters.interfaces import AckApplyStatus, CandidateVerificationResult
from p06.adapters.mocks.playback_bus import MockPlaybackAckBus
from p06.adapters.p05_knowledge_adapter import P05KnowledgeAdapter
from p06.agent import (
    NODE_BOUNDED_REWRITE,
    NODE_CHECK_REPETITION,
    NODE_DRAFT_CHUNK,
    NODE_FINALIZE_CANDIDATE,
    NODE_LOAD_CONTEXT,
    NODE_PLAN_CHUNK,
    NODE_SAFE_FALLBACK,
    NODE_VERIFY_P05,
    GraphRuntimeDeps,
    run_storytelling_turn,
)
from p06.memory import (
    GlobalTopicCoverage,
    NoOpSemanticMemory,
    RepetitionConfig,
    RepetitionDetector,
    SessionViewerContext,
    ShortTermPlayedHistory,
)
from p06.providers.mock_provider import MockBehavior, MockLLMProvider, MockResponseStep
from p06.schemas.candidate import (
    CandidateOrigin,
    CandidateVerificationStatus,
    CoverageMode,
    ProposedResponseCoverage,
    SpeechCandidate,
    TargetScopeMode,
)
from p06.schemas.events import PlaybackOutcomeStatus, StoryCheckpoint
from p06.schemas.state import (
    AgentState,
    AgentTurnOutcome,
    PlayedTurnSummary,
    RewriteBudgetState,
)
from p06.schemas.story import StoryArc, StoryPlan, StoryPlanApprovalStatus, StoryTopic
from p06.simulation import SimulatedPlaybackHarness, VirtualClock

MODULE_ROOT = Path(__file__).resolve().parents[2]
VERIFIED_SEED_PATH = MODULE_ROOT / "data" / "products" / "e01_verified_skus.json"
NEGATIVE_SEED_PATH = MODULE_ROOT / "data" / "products" / "e01_negative_skus.json"
STORY_PLANS_PATH = MODULE_ROOT / "data" / "story_plans" / "e01_story_plans.json"

TENANT_ID = "tenant-p06-poc-01"
ACTIVE_SKU_ID = "SKU-HONEY-01"
SIM_RUN_ID = "smoke-e01-sim-01"
START_AT = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)


def _load_e01_plan(plan_key: str = "product_education_10m") -> StoryPlan:
    """Nạp một `StoryPlan` synthetic từ fixture chuẩn `e01_story_plans.json`."""
    raw = json.loads(STORY_PLANS_PATH.read_text(encoding="utf-8"))
    return StoryPlan.model_validate(raw["plans"][plan_key])


def _make_harness(
    plan: StoryPlan,
    *,
    active_sku_id: str = ACTIVE_SKU_ID,
    window_size: int = 10,
) -> tuple[SimulatedPlaybackHarness, VirtualClock, MockPlaybackAckBus]:
    """Khởi tạo bộ điều phối chuẩn gồm `VirtualClock`, `MockPlaybackAckBus` và `SimulatedPlaybackHarness`."""
    clock = VirtualClock(START_AT)
    first_arc = next(arc for arc in plan.arcs if arc.sku_id == active_sku_id)
    first_topic = first_arc.topics[0]
    checkpoint = StoryCheckpoint(
        tenant_id=plan.tenant_id,
        session_id=plan.session_id,
        session_epoch=1,
        plan_id=plan.plan_id,
        plan_revision=plan.plan_revision,
        active_sku_id=active_sku_id,
        current_arc_id=first_arc.arc_id,
        next_topic_id=first_topic.topic_id,
        updated_at=START_AT,
    )
    played_history = ShortTermPlayedHistory(
        window_size=window_size,
        tenant_id=plan.tenant_id,
        session_id=plan.session_id,
        session_epoch=1,
    )
    topic_coverage = GlobalTopicCoverage(plan)
    viewer_context = SessionViewerContext(
        tenant_id=plan.tenant_id,
        session_id=plan.session_id,
        session_epoch=1,
    )
    semantic_memory = NoOpSemanticMemory()
    harness = SimulatedPlaybackHarness(
        initial_checkpoint=checkpoint,
        expected_simulation_run_id=SIM_RUN_ID,
        played_history_window_size=window_size,
        story_plan=plan,
        played_history=played_history,
        topic_coverage=topic_coverage,
        viewer_context=viewer_context,
        semantic_memory=semantic_memory,
    )
    bus = MockPlaybackAckBus(clock=clock, simulation_run_id=SIM_RUN_ID)
    return harness, clock, bus


def _make_honey_fallback(
    verifier: P05KnowledgeAdapter,
    plan: StoryPlan,
    *,
    session_epoch: int = 1,
) -> SpeechCandidate:
    """Tạo câu dự phòng an toàn đã gắn bằng chứng sống cho `SKU-HONEY-01`."""
    evidence = verifier.get_sku_evidence(plan.tenant_id, ACTIVE_SKU_ID, at_time=START_AT)
    binding = evidence.to_version_binding(
        cited_evidence_ids=["ev-e01-honey-shipping"],
        stated_price_vnd=159000,
    )
    return SpeechCandidate(
        candidate_id=f"fb-honey-safe-{session_epoch}",
        tenant_id=plan.tenant_id,
        session_id=plan.session_id,
        session_epoch=session_epoch,
        origin=CandidateOrigin.PREAPPROVED_FALLBACK,
        scope_mode=TargetScopeMode.SINGLE_SKU,
        sku_refs=[ACTIVE_SKU_ID],
        sku_bindings=[binding],
        session_rights_version=1,
        intent="FALLBACK_SAFE_SHIPPING",
        text="Mật ong Đắk Lắk 500ml giá 159.000đ, bọc chống sốc 2 lớp, đổi mới 7 ngày.",
        estimated_duration_sec=6.8,
        proposed_coverage=ProposedResponseCoverage(
            covered_topic_ids=[],
            covered_intents=["Thông tin sản phẩm an toàn"],
            coverage_mode=CoverageMode.FULL,
            is_authoritative=False,
        ),
        verification_status=CandidateVerificationStatus.DRAFT,
    )


def _chunk_payload(
    text: str,
    *,
    evidence_ids: list[str] | None = None,
    claim_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Tạo JSON đầu ra hợp lệ cho `ChunkDraftLLMOutput`."""
    return {
        "text": text,
        "role": "PRODUCT_STORY",
        "cited_evidence_ids": evidence_ids if evidence_ids is not None else ["ev-e01-honey-usage"],
        "stated_price_vnd": None,
        "mentions_ocop": False,
        "semantic_breakpoint": True,
        "breakpoint_type": "TOPIC_END",
        "covered_claim_ids": claim_ids if claim_ids is not None else ["clm-e01-honey-allowed-01"],
        "rationale": "Kịch bản smoke E01 bám bằng chứng",
    }


def _make_deps(
    steps: list[MockResponseStep],
    verifier: P05KnowledgeAdapter,
    clock: VirtualClock,
    fallback_candidates: list[SpeechCandidate] | None = None,
) -> GraphRuntimeDeps:
    """Dựng `GraphRuntimeDeps` dùng `MockLLMProvider` và `P05KnowledgeAdapter`."""
    return GraphRuntimeDeps(
        llm_provider=MockLLMProvider(response_sequence=steps),
        knowledge_verifier=verifier,
        repetition_detector=RepetitionDetector(RepetitionConfig()),
        fallback_candidates=fallback_candidates or [],
        clock=clock,
        max_chunk_duration_sec=8.0,
    )


class TestE01AgentIntegrationSmoke:
    """Kiểm chứng 17 kịch bản tích hợp khép kín của Phase 3 (`P06-E01`)."""

    def test_01_valid_chunk_generated(self) -> None:
        """Kịch bản 01: Sinh `StoryChunk` và `SpeechCandidate` hợp lệ cho `topic-edu-honey-usage`."""
        plan = _load_e01_plan()
        verifier = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
        harness, clock, _ = _make_harness(plan)
        deps = _make_deps(
            [
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_chunk_payload(
                        "Pha 1-2 thìa mật ong với nước ấm dưới 50 độ C, không dùng cho trẻ dưới 1 tuổi."
                    ),
                )
            ],
            verifier=verifier,
            clock=clock,
        )
        state = harness.build_agent_state(plan, ACTIVE_SKU_ID)
        result = run_storytelling_turn(state, deps, turn_id="turn-s01", sequence_index=0)

        assert result.final_state.turn_outcome == AgentTurnOutcome.VERIFIED_READY
        assert result.final_state.draft_chunk is not None
        assert result.final_state.draft_chunk.topic_id == "topic-edu-honey-usage"
        assert result.final_state.verified_candidate is not None
        assert result.final_state.verified_candidate.origin == CandidateOrigin.PROACTIVE_STORY

    def test_02_p05_verification_passes(self) -> None:
        """Kịch bản 02: Ứng viên qua Cổng P05 mang `gate_decision_id`, version binding và prompt SHA-256."""
        plan = _load_e01_plan()
        verifier = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
        harness, clock, _ = _make_harness(plan)
        deps = _make_deps(
            [
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_chunk_payload(
                        "Pha mật ong với 150ml nước ấm dưới 50 độ C, không dùng cho trẻ dưới 1 tuổi."
                    ),
                )
            ],
            verifier=verifier,
            clock=clock,
        )
        result = run_storytelling_turn(harness.build_agent_state(plan), deps, turn_id="turn-s02")

        cand = result.final_state.verified_candidate
        assert cand is not None
        assert cand.verification_status == CandidateVerificationStatus.VERIFIED
        assert cand.verified_by_gate_decision_id == f"p05-allow-{cand.candidate_id}"
        assert cand.sku_bindings[0].knowledge_version == 1
        assert "story_generation.txt" in result.prompt_hashes

    def test_03_playback_ack_completed_accepted(self) -> None:
        """Kịch bản 03: `MockPlaybackAckBus` phát ứng viên đã duyệt và `SimulatedPlaybackHarness` nhận `APPLIED`."""
        plan = _load_e01_plan()
        verifier = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
        harness, clock, bus = _make_harness(plan)
        deps = _make_deps(
            [
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_chunk_payload(
                        "Pha một thìa mật ong với nước ấm dưới 50 độ C, không dùng cho trẻ dưới 1 tuổi."
                    ),
                )
            ],
            verifier=verifier,
            clock=clock,
        )
        turn = run_storytelling_turn(harness.build_agent_state(plan), deps, turn_id="turn-s03")
        verified = turn.final_state.verified_candidate
        assert verified is not None

        harness.register_pending_turn(
            turn_id="turn-s03",
            candidate=verified,
            plan_revision=plan.plan_revision,
            next_topic_id=turn.next_topic_id_hint,
            current_arc_id=turn.next_arc_id_hint,
            covered_claim_ids=turn.covered_claim_ids,
        )
        ack = bus.dispatch_turn(verified, turn_id="turn-s03", plan_revision=plan.plan_revision)
        apply_res = harness.apply_ack(ack)

        assert apply_res.status == AckApplyStatus.APPLIED
        assert apply_res.applied is True

    def test_04_memory_updated_only_after_ack(self) -> None:
        """Kịch bản 04: Trước khi có ACK `PlaybackCompleted`, mọi bộ nhớ & checkpoint đều giữ nguyên."""
        plan = _load_e01_plan()
        verifier = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
        harness, clock, bus = _make_harness(plan)
        deps = _make_deps(
            [
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_chunk_payload(
                        "Pha mật ong với nước ấm dưới 50 độ C, không dùng cho trẻ dưới 1 tuổi."
                    ),
                )
            ],
            verifier=verifier,
            clock=clock,
        )
        turn = run_storytelling_turn(harness.build_agent_state(plan), deps, turn_id="turn-s04")
        verified = turn.final_state.verified_candidate
        assert verified is not None

        # Sau khi LangGraph chạy xong nhưng chưa có ACK -> toàn bộ tiến độ vẫn bằng 0 (I-03/I-06).
        assert harness.played_history == ()
        assert harness.completed_topic_ids == frozenset()
        assert harness.checkpoint.last_completed_chunk_id is None

        harness.register_pending_turn(
            turn_id="turn-s04",
            candidate=verified,
            plan_revision=plan.plan_revision,
            next_topic_id=turn.next_topic_id_hint,
            current_arc_id=turn.next_arc_id_hint,
            covered_claim_ids=turn.covered_claim_ids,
        )
        # Ngay cả sau khi đăng ký pending vẫn chưa được tính là đã phát.
        assert harness.played_history == ()
        assert harness.completed_topic_ids == frozenset()

        ack = bus.dispatch_turn(verified, turn_id="turn-s04", plan_revision=plan.plan_revision)
        harness.apply_ack(ack)

        assert len(harness.played_history) == 1
        assert "topic-edu-honey-usage" in harness.completed_topic_ids
        assert harness.checkpoint.last_completed_chunk_id == verified.source_chunk_id

    def test_05_next_invocation_receives_new_played_history_and_coverage(self) -> None:
        """Kịch bản 05: Lượt gọi đồ thị kế tiếp nhận đầy đủ `played_history` & `completed_topic_ids` mới."""
        plan = _load_e01_plan()
        verifier = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
        harness, clock, bus = _make_harness(plan)
        deps = _make_deps(
            [
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_chunk_payload(
                        "Pha 1 thìa mật ong với nước ấm dưới 50 độ C, không dùng cho trẻ dưới 1 tuổi."
                    ),
                ),
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_chunk_payload(
                        "Mật ong tự nhiên có thể kết tinh nhẹ khi lạnh, ngâm nước ấm 40 độ C sẽ tan.",
                        evidence_ids=["ev-e01-honey-quality"],
                        claim_ids=["clm-e01-honey-allowed-01"],
                    ),
                ),
            ],
            verifier=verifier,
            clock=clock,
        )

        # Lượt 1
        t1 = run_storytelling_turn(harness.build_agent_state(plan), deps, turn_id="turn-s05-1", sequence_index=0)
        assert t1.final_state.verified_candidate is not None
        harness.register_pending_turn(
            turn_id="turn-s05-1",
            candidate=t1.final_state.verified_candidate,
            plan_revision=plan.plan_revision,
            next_topic_id=t1.next_topic_id_hint,
            current_arc_id=t1.next_arc_id_hint,
            covered_claim_ids=t1.covered_claim_ids,
        )
        harness.apply_ack(bus.dispatch_turn(t1.final_state.verified_candidate, turn_id="turn-s05-1", plan_revision=plan.plan_revision))

        # Xây state cho lượt 2 từ harness -> chứa lượt 1 và chọn sang topic kế tiếp.
        next_state = harness.build_agent_state(plan)
        assert len(next_state.played_history) == 1
        assert "topic-edu-honey-usage" in next_state.completed_topic_ids

        t2 = run_storytelling_turn(next_state, deps, turn_id="turn-s05-2", sequence_index=1)
        assert t2.final_state.selected_topic_id == "topic-edu-honey-quality"
        assert t2.final_state.turn_outcome == AgentTurnOutcome.VERIFIED_READY

    def test_06_repetition_detected_on_lexical_duplication(self) -> None:
        """Kịch bản 06: `check_repetition` bắt lặp bề mặt từ vựng so với `played_history`."""
        plan = _load_e01_plan()
        verifier = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
        harness, clock, bus = _make_harness(plan)
        repeated_text = (
            "Pha mật ong với nước ấm dưới 50 độ C, không dùng cho trẻ dưới 1 tuổi."
        )
        deps = _make_deps(
            [
                MockResponseStep(behavior=MockBehavior.VALID_JSON, payload=_chunk_payload(repeated_text)),
                # Lượt 2 lần 0 lặp gần như nguyên văn; lần 1 sửa lại mới hoàn toàn
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_chunk_payload(
                        repeated_text + " Uống mỗi sáng.",
                        evidence_ids=["ev-e01-honey-quality"],
                    ),
                ),
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_chunk_payload(
                        "Mật ong nguyên chất không pha đường tinh luyện, để nơi khô mát tránh nắng.",
                        evidence_ids=["ev-e01-honey-quality"],
                        claim_ids=[],
                    ),
                ),
            ],
            verifier=verifier,
            clock=clock,
        )

        t1 = run_storytelling_turn(harness.build_agent_state(plan), deps, turn_id="turn-s06-1", sequence_index=0)
        assert t1.final_state.verified_candidate is not None
        harness.register_pending_turn(
            turn_id="turn-s06-1",
            candidate=t1.final_state.verified_candidate,
            plan_revision=plan.plan_revision,
            next_topic_id=t1.next_topic_id_hint,
            current_arc_id=t1.next_arc_id_hint,
        )
        harness.apply_ack(bus.dispatch_turn(t1.final_state.verified_candidate, turn_id="turn-s06-1", plan_revision=plan.plan_revision))

        t2 = run_storytelling_turn(harness.build_agent_state(plan), deps, turn_id="turn-s06-2", sequence_index=1)
        assert NODE_CHECK_REPETITION in t2.final_state.node_trace
        assert NODE_BOUNDED_REWRITE in t2.final_state.node_trace
        assert t2.final_state.rewrite_budget.retries_used == 1
        assert t2.final_state.turn_outcome == AgentTurnOutcome.VERIFIED_READY

    def test_07_valid_rewrite_reverified_through_repetition_and_p05(self) -> None:
        """Kịch bản 07: Bản viết lại từ `bounded_rewrite` phải đi vòng qua cả `check_repetition` lẫn `verify_p05`."""
        plan = _load_e01_plan()
        verifier = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
        harness, clock, _ = _make_harness(plan)
        deps = _make_deps(
            [
                # Lần 0 nhắc sai giá -> bị P05 từ chối (PRICE_MISMATCH)
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_chunk_payload("Chai mật ong này đang bán giá chỉ 99.000đ thôi ạ!"),
                ),
                # Lần 1 sửa lại chuẩn 159.000đ -> qua check_repetition -> verify_p05 PASS
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload={
                        "text": "Mật ong 500ml giá 159.000đ, pha nước ấm dưới 50 độ C, không dùng cho trẻ dưới 1 tuổi.",
                        "role": "FACT_HIGHLIGHT",
                        "cited_evidence_ids": ["ev-e01-honey-shipping", "ev-e01-honey-usage"],
                        "stated_price_vnd": 159000,
                        "mentions_ocop": False,
                        "semantic_breakpoint": True,
                        "breakpoint_type": "TOPIC_END",
                        "covered_claim_ids": ["clm-e01-honey-allowed-01"],
                        "rationale": "Đã sửa giá chuẩn 159.000đ",
                    },
                ),
            ],
            verifier=verifier,
            clock=clock,
        )
        result = run_storytelling_turn(harness.build_agent_state(plan), deps, turn_id="turn-s07")

        assert result.final_state.turn_outcome == AgentTurnOutcome.VERIFIED_READY
        assert result.final_state.node_trace == [
            NODE_LOAD_CONTEXT,
            NODE_PLAN_CHUNK,
            NODE_DRAFT_CHUNK,
            NODE_CHECK_REPETITION,
            NODE_VERIFY_P05,
            NODE_BOUNDED_REWRITE,
            NODE_CHECK_REPETITION,
            NODE_VERIFY_P05,
            NODE_FINALIZE_CANDIDATE,
        ]

    def test_08_rewrite_budget_exhausted_cleanly(self) -> None:
        """Kịch bản 08: Cạn ngân sách `1 + K` (`K=2` -> 3 lần gọi LLM) thì dừng vòng lặp dứt khoát."""
        plan = _load_e01_plan()
        verifier = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
        harness, clock, _ = _make_harness(plan)
        bad_step = MockResponseStep(
            behavior=MockBehavior.VALID_JSON,
            payload=_chunk_payload("Mật ong giúp chữa dứt điểm đau dạ dày!", evidence_ids=[], claim_ids=[]),
        )
        deps = _make_deps(
            [bad_step, bad_step, bad_step, bad_step],
            verifier=verifier,
            clock=clock,
            fallback_candidates=[_make_honey_fallback(verifier, plan)],
        )
        result = run_storytelling_turn(
            harness.build_agent_state(plan, max_rewrite_retries=2),
            deps,
            turn_id="turn-s08",
        )
        assert len(result.telemetry_records) == 3  # đúng 1 + 2 = 3 lần gọi
        assert result.final_state.rewrite_budget.retries_used == 2
        assert result.final_state.turn_outcome == AgentTurnOutcome.FALLBACK_PREAPPROVED

    def test_09_safe_fallback_selected_and_live_verified(self) -> None:
        """Kịch bản 09: Fallback được chọn qua `SafeFallbackSelector` và tái kiểm chứng P05 sống."""
        plan = _load_e01_plan()
        verifier = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
        harness, clock, _ = _make_harness(plan)
        deps = _make_deps(
            [MockResponseStep(behavior=MockBehavior.TIMEOUT)],
            verifier=verifier,
            clock=clock,
            fallback_candidates=[_make_honey_fallback(verifier, plan)],
        )
        result = run_storytelling_turn(harness.build_agent_state(plan), deps, turn_id="turn-s09")

        cand = result.final_state.verified_candidate
        assert result.final_state.turn_outcome == AgentTurnOutcome.FALLBACK_PREAPPROVED
        assert cand is not None
        assert cand.origin == CandidateOrigin.PREAPPROVED_FALLBACK
        assert cand.verification_status == CandidateVerificationStatus.VERIFIED
        assert cand.verified_by_gate_decision_id is not None

    def test_10_safe_abort_when_fallback_empty_or_invalid(self) -> None:
        """Kịch bản 10: Không có fallback hợp lệ -> `SAFE_ABORT_NO_CANDIDATE` với `verified_candidate=None`."""
        plan = _load_e01_plan()
        verifier = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
        harness, clock, _ = _make_harness(plan)
        deps = _make_deps(
            [MockResponseStep(behavior=MockBehavior.PROVIDER_FAILURE)],
            verifier=verifier,
            clock=clock,
            fallback_candidates=[],
        )
        result = run_storytelling_turn(harness.build_agent_state(plan), deps, turn_id="turn-s10")

        assert result.final_state.turn_outcome == AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE
        assert result.final_state.verified_candidate is None
        assert NODE_SAFE_FALLBACK in result.final_state.node_trace

    @pytest.mark.parametrize("bad_outcome", [PlaybackOutcomeStatus.FAILED, PlaybackOutcomeStatus.UNKNOWN])
    def test_11_failed_and_unknown_acks_freeze_progress(self, bad_outcome: PlaybackOutcomeStatus) -> None:
        """Kịch bản 11: ACK `FAILED` hoặc `UNKNOWN` tuyệt đối không tiến checkpoint/lịch sử/độ phủ."""
        plan = _load_e01_plan()
        verifier = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
        harness, clock, bus = _make_harness(plan)
        deps = _make_deps(
            [
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_chunk_payload(
                        "Pha một thìa mật ong với nước ấm dưới 50 độ C, không dùng cho trẻ dưới 1 tuổi."
                    ),
                )
            ],
            verifier=verifier,
            clock=clock,
        )
        turn = run_storytelling_turn(harness.build_agent_state(plan), deps, turn_id="turn-s11")
        verified = turn.final_state.verified_candidate
        assert verified is not None

        harness.register_pending_turn(
            turn_id="turn-s11",
            candidate=verified,
            plan_revision=plan.plan_revision,
            next_topic_id=turn.next_topic_id_hint,
        )
        ack = bus.dispatch_turn(
            verified,
            turn_id="turn-s11",
            plan_revision=plan.plan_revision,
            outcome_override=bad_outcome,
            failure_reason=f"Giả lập {bad_outcome.value}",
        )
        apply_res = harness.apply_ack(ack)

        assert apply_res.status == AckApplyStatus.IGNORED_NON_COMPLETED
        assert apply_res.applied is False
        assert apply_res.auto_replay_permitted is False
        assert harness.played_history == ()
        assert harness.completed_topic_ids == frozenset()
        assert harness.checkpoint.last_completed_chunk_id is None
        assert harness.checkpoint.next_topic_id == "topic-edu-honey-usage"

    def test_12_duplicate_playback_ack_rejected_idempotently(self) -> None:
        """Kịch bản 12: Gửi trùng ACK `COMPLETED` lần 2 bị từ chối `REJECTED_DUPLICATE`, không đếm đúp."""
        plan = _load_e01_plan()
        verifier = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
        harness, clock, bus = _make_harness(plan)
        deps = _make_deps(
            [
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_chunk_payload(
                        "Pha mật ong với nước ấm dưới 50 độ C mỗi sáng, không dùng cho trẻ dưới 1 tuổi."
                    ),
                )
            ],
            verifier=verifier,
            clock=clock,
        )
        turn = run_storytelling_turn(harness.build_agent_state(plan), deps, turn_id="turn-s12")
        verified = turn.final_state.verified_candidate
        assert verified is not None

        harness.register_pending_turn(
            turn_id="turn-s12",
            candidate=verified,
            plan_revision=plan.plan_revision,
            next_topic_id=turn.next_topic_id_hint,
        )
        ack = bus.dispatch_turn(verified, turn_id="turn-s12", plan_revision=plan.plan_revision)

        first = harness.apply_ack(ack)
        second = harness.apply_ack(ack)

        assert first.status == AckApplyStatus.APPLIED
        assert second.status == AckApplyStatus.REJECTED_DUPLICATE
        assert second.applied is False
        assert len(harness.played_history) == 1

    def test_13_stale_knowledge_toctou_fail_closed_non_retryable(self) -> None:
        """Kịch bản 13: TOCTOU — nâng `knowledge_version` trong kho sau khi lập `StoryPlan` -> chặn ngay không retry LLM."""
        plan = _load_e01_plan()
        verifier = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
        # Giả lập tri thức trên kho vừa tăng lên version 2 sau khi plan v1 được duyệt.
        fact_v1 = verifier._store.facts[ACTIVE_SKU_ID]
        verifier._store.facts[ACTIVE_SKU_ID] = fact_v1.model_copy(update={"knowledge_version": 2})

        harness, clock, _ = _make_harness(plan)
        deps = _make_deps(
            [MockResponseStep(behavior=MockBehavior.VALID_JSON, payload=_chunk_payload("Nội dung không nên được gọi"))],
            verifier=verifier,
            clock=clock,
            fallback_candidates=[],
        )
        result = run_storytelling_turn(harness.build_agent_state(plan, max_rewrite_retries=2), deps, turn_id="turn-s13")

        assert result.telemetry_records == ()
        assert result.final_state.turn_outcome == AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE
        assert result.final_state.node_trace == [
            NODE_LOAD_CONTEXT,
            NODE_SAFE_FALLBACK,
            NODE_FINALIZE_CANDIDATE,
        ]

    def test_14_invalid_state_transition_and_tampered_graph_output_blocked(self) -> None:
        """Kịch bản 14: `validated_update()` và `AgentState.from_graph_result()` chặn chuyển trạng thái sai bất biến."""
        plan = _load_e01_plan()
        harness, _, _ = _make_harness(plan)
        state = harness.build_agent_state(plan)

        with pytest.raises(ValidationError):
            state.validated_update(turn_outcome=AgentTurnOutcome.VERIFIED_READY, verified_candidate=None)

        # Giả lập node lỗi trả dict thô trong LangGraph (VERIFIED_READY nhưng không có verified_candidate).
        def rogue_node(cur: AgentState) -> dict[str, Any]:
            return {
                "turn_outcome": AgentTurnOutcome.VERIFIED_READY,
                "verified_candidate": None,
                "node_trace": [*cur.node_trace, "rogue_node"],
            }

        bad_graph = StateGraph(AgentState)
        bad_graph.add_node("rogue_node", rogue_node)
        bad_graph.add_edge(START, "rogue_node")
        bad_graph.add_edge("rogue_node", END)
        raw_out = bad_graph.compile().invoke(state)

        with pytest.raises(ValidationError):
            AgentState.from_graph_result(raw_out)

    def test_15_unapproved_story_plan_rejected_before_execution(self) -> None:
        """Kịch bản 15: `StoryPlan` chưa `APPROVED` (`DRAFT`) bị từ chối trước khi chạy đồ thị."""
        approved = _load_e01_plan()
        payload = copy.deepcopy(approved.model_dump())
        payload["approval_status"] = StoryPlanApprovalStatus.DRAFT
        payload["approved_by"] = None
        payload["approved_at"] = None
        draft_plan = StoryPlan.model_validate(payload)

        checkpoint = StoryCheckpoint(
            tenant_id=draft_plan.tenant_id,
            session_id=draft_plan.session_id,
            session_epoch=1,
            plan_id=draft_plan.plan_id,
            plan_revision=draft_plan.plan_revision,
            active_sku_id=ACTIVE_SKU_ID,
            current_arc_id="arc-edu-honey-01",
            next_topic_id="topic-edu-honey-usage",
            updated_at=START_AT,
        )

        with pytest.raises(ValidationError):
            AgentState(
                tenant_id=draft_plan.tenant_id,
                session_id=draft_plan.session_id,
                session_epoch=1,
                active_sku_id=ACTIVE_SKU_ID,
                story_plan=draft_plan,
                story_checkpoint=checkpoint,
            )

    def test_16_invalid_or_ineligible_active_sku_fail_closed_i04(self) -> None:
        """Kịch bản 16 (`I-04`): Chặn `active_sku_id` ngoài `pinned_sku_ids` và fail-closed với SKU chưa đủ điều kiện OCOP."""
        approved = _load_e01_plan()
        harness, _, _ = _make_harness(approved)
        with pytest.raises(ValueError):
            harness.build_agent_state(approved, active_sku_id="SKU-UNKNOWN-99")

        # Kiểm tra SKU-CASHEW-03 (OCOP PENDING) từ bộ negative fixture -> fail-closed tại load_context, 0 lần gọi LLM.
        neg_verifier = P05KnowledgeAdapter.from_seed_file(NEGATIVE_SEED_PATH)
        neg_plan = StoryPlan(
            plan_id="plan-neg-cashew",
            tenant_id=TENANT_ID,
            session_id="session-neg-cashew",
            plan_revision=1,
            approval_status=StoryPlanApprovalStatus.APPROVED,
            approved_by="synthetic-owner-01",
            approved_at=START_AT,
            session_goal="Kiểm tra fail-closed với SKU có OCOP PENDING",
            pinned_sku_ids=["SKU-CASHEW-03"],
            knowledge_versions_by_sku={"SKU-CASHEW-03": 1},
            arcs=[
                StoryArc(
                    arc_id="arc-neg-cashew",
                    position=1,
                    title="Hạt điều",
                    sku_id="SKU-CASHEW-03",
                    target_duration_sec=120,
                    topics=[
                        StoryTopic(
                            topic_id="topic-neg-cashew",
                            title="Giới thiệu hạt điều",
                            sku_id="SKU-CASHEW-03",
                            is_mandatory=True,
                        )
                    ],
                )
            ],
        )
        neg_harness, neg_clock, _ = _make_harness(neg_plan, active_sku_id="SKU-CASHEW-03")
        neg_deps = _make_deps(
            [MockResponseStep(behavior=MockBehavior.VALID_JSON, payload=_chunk_payload("Không được gọi"))],
            verifier=neg_verifier,
            clock=neg_clock,
            fallback_candidates=[],
        )
        neg_result = run_storytelling_turn(
            neg_harness.build_agent_state(neg_plan, active_sku_id="SKU-CASHEW-03"),
            neg_deps,
            turn_id="turn-s16-neg",
        )
        assert neg_result.telemetry_records == ()
        assert neg_result.final_state.turn_outcome == AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE
        assert neg_result.final_state.node_trace == [
            NODE_LOAD_CONTEXT,
            NODE_SAFE_FALLBACK,
            NODE_FINALIZE_CANDIDATE,
        ]

    def test_17_mandatory_topics_completed_and_clean_termination(self) -> None:
        """Kịch bản 17: Hoàn tất toàn bộ topic bắt buộc của `SKU-HONEY-01` -> lượt kế tiếp dừng sạch (không lặp vô hạn)."""
        plan = _load_e01_plan()
        verifier = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
        harness, clock, bus = _make_harness(plan)
        deps = _make_deps(
            [
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_chunk_payload(
                        "Pha 1 thìa mật ong với nước ấm dưới 50 độ C, không dùng cho trẻ dưới 1 tuổi.",
                        evidence_ids=["ev-e01-honey-usage"],
                        claim_ids=["clm-e01-honey-allowed-01"],
                    ),
                ),
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_chunk_payload(
                        "Mật ong có thể kết tinh nhẹ khi lạnh, ngâm chai vào nước ấm 40 độ C.",
                        evidence_ids=["ev-e01-honey-quality"],
                        claim_ids=["clm-e01-honey-allowed-01"],
                    ),
                ),
            ],
            verifier=verifier,
            clock=clock,
        )

        # Chạy tuần tự 2 lượt tương ứng 2 mandatory topic của SKU-HONEY-01
        for idx in range(2):
            turn_id = f"turn-s17-{idx + 1}"
            res = run_storytelling_turn(
                harness.build_agent_state(plan),
                deps,
                turn_id=turn_id,
                sequence_index=idx,
            )
            assert res.should_terminate is False
            assert res.final_state.verified_candidate is not None
            harness.register_pending_turn(
                turn_id=turn_id,
                candidate=res.final_state.verified_candidate,
                plan_revision=plan.plan_revision,
                next_topic_id=res.next_topic_id_hint,
                current_arc_id=res.next_arc_id_hint,
                covered_claim_ids=res.covered_claim_ids,
            )
            ack = bus.dispatch_turn(
                res.final_state.verified_candidate,
                turn_id=turn_id,
                plan_revision=plan.plan_revision,
            )
            assert harness.apply_ack(ack).status == AckApplyStatus.APPLIED

        assert harness.completed_topic_ids == frozenset(
            {"topic-edu-honey-usage", "topic-edu-honey-quality"}
        )

        # Lượt thứ 3: hết topic cho SKU-HONEY-01 -> dừng sạch với 0 lần gọi LLM.
        t3 = run_storytelling_turn(
            harness.build_agent_state(plan),
            deps,
            turn_id="turn-s17-3",
            sequence_index=2,
        )
        assert t3.should_terminate is True
        assert t3.termination_reason == "ALL_ELIGIBLE_TOPICS_COMPLETED"
        assert t3.telemetry_records == ()
        assert t3.final_state.turn_outcome == AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE
        assert t3.final_state.node_trace == [
            NODE_LOAD_CONTEXT,
            NODE_PLAN_CHUNK,
            NODE_FINALIZE_CANDIDATE,
        ]
