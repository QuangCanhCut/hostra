"""Bộ kiểm thử đơn vị cho đồ thị LangGraph 8 node P06 (`src/p06/agent/`).

1. File này giải quyết vấn đề gì?
   Kiểm chứng cơ chế điều phối 8 node trên `StateGraph(AgentState)`: ngân sách viết lại
   giới hạn `1 + K`, phân loại lỗi retry/non-retry, kiểm tra thời lượng không cắt ngầm,
   chuyển chủ đề khi lặp sự thật, dự phòng an toàn và kết thúc sạch.
2. Trách nhiệm chính của module là gì?
   Kiểm thử `GraphRuntimeDeps`, các node riêng lẻ, hàm định tuyến `routing.py`,
   `build_storytelling_graph` và `run_storytelling_turn`.
3. Module này liên kết với các thành phần nào?
   Kiểm thử `p06.agent` kết hợp `P05KnowledgeAdapter`, `MockLLMProvider`, `RepetitionDetector`,
   `VirtualClock` và `p06.schemas`.
4. Input và output chính là gì?
   Input là `AgentState` (`APPROVED` plan) + `MockLLMProvider` theo kịch bản lỗi/thành công;
   Output là `AgentTurnResult` khẳng định số lần gọi LLM (`1 + K`), vết node và tính đúng đắn bất biến.
5. Có những constraints hoặc invariants quan trọng nào?
   Mọi kiểm thử dùng `MockLLMProvider` ngoại tuyến, không gọi LLM thật và không chạm P05.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

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
from p06.memory.repetition_detector import RepetitionConfig, RepetitionDetector
from p06.providers.mock_provider import MockBehavior, MockLLMProvider, MockResponseStep
from p06.schemas.candidate import (
    CandidateOrigin,
    CandidateVerificationStatus,
    CoverageMode,
    ProposedResponseCoverage,
    SpeechCandidate,
    TargetScopeMode,
)
from p06.schemas.events import StoryCheckpoint
from p06.schemas.state import (
    AgentState,
    AgentTurnOutcome,
    PlayedTurnSummary,
    RewriteBudgetState,
)
from p06.schemas.story import (
    StoryArc,
    StoryPlan,
    StoryPlanApprovalStatus,
    StoryTopic,
)
from p06.simulation.virtual_clock import VirtualClock

MODULE_ROOT = Path(__file__).resolve().parents[2]
VERIFIED_SEED_PATH = MODULE_ROOT / "data" / "products" / "e01_verified_skus.json"
TENANT_ID = "tenant-p06-poc-01"
SESSION_ID = "session-agent-unit-01"
ACTIVE_SKU_ID = "SKU-HONEY-01"
NOW = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)


def _make_plan(
    *,
    status: StoryPlanApprovalStatus = StoryPlanApprovalStatus.APPROVED,
    honey_kv: int = 1,
) -> StoryPlan:
    """Tạo `StoryPlan` synthetic gọn có 2 topic thuộc `SKU-HONEY-01`."""
    return StoryPlan(
        plan_id="plan-agent-unit-01",
        tenant_id=TENANT_ID,
        session_id=SESSION_ID,
        plan_revision=1,
        approval_status=status,
        approved_by="owner-unit-01" if status == StoryPlanApprovalStatus.APPROVED else None,
        approved_at=NOW if status == StoryPlanApprovalStatus.APPROVED else None,
        session_goal="Giới thiệu mật ong hoa cà phê Đắk Lắk chuẩn P05",
        pinned_sku_ids=[ACTIVE_SKU_ID, "SKU-TEA-02"],
        mandatory_messages=["Không dùng mật ong cho trẻ dưới 1 tuổi."],
        prohibited_topics=["Chữa bách bệnh"],
        knowledge_versions_by_sku={ACTIVE_SKU_ID: honey_kv, "SKU-TEA-02": 1},
        arcs=[
            StoryArc(
                arc_id="arc-honey",
                position=1,
                title="Câu chuyện Mật ong hoa cà phê",
                sku_id=ACTIVE_SKU_ID,
                target_duration_sec=180,
                topics=[
                    StoryTopic(
                        topic_id="topic-honey-usage",
                        title="Cách dùng mật ong an toàn",
                        sku_id=ACTIVE_SKU_ID,
                        is_mandatory=True,
                        fact_refs=["ev-e01-honey-usage"],
                        allowed_claim_ids=["clm-e01-honey-allowed-01"],
                        talking_points=["Pha 1-2 thìa với nước ấm dưới 50 độ C."],
                    ),
                    StoryTopic(
                        topic_id="topic-honey-quality",
                        title="Nguồn gốc Cư M'gar và bảo quản",
                        sku_id=ACTIVE_SKU_ID,
                        is_mandatory=True,
                        fact_refs=["ev-e01-honey-origin"],
                        allowed_claim_ids=["clm-e01-honey-allowed-01"],
                        talking_points=["Màu vàng hổ phách tự nhiên tại Cư M'gar."],
                    ),
                ],
            )
        ],
    )


def _make_initial_state(
    *,
    plan: StoryPlan | None = None,
    max_retries: int = 2,
    completed_topic_ids: frozenset[str] = frozenset(),
    played_history: list[PlayedTurnSummary] | None = None,
    next_topic_id: str | None = "topic-honey-usage",
) -> AgentState:
    """Tạo `AgentState` khởi tạo cho một lượt kiểm thử đồ thị."""
    effective_plan = plan or _make_plan()
    checkpoint = StoryCheckpoint(
        tenant_id=TENANT_ID,
        session_id=SESSION_ID,
        session_epoch=1,
        plan_id=effective_plan.plan_id,
        plan_revision=effective_plan.plan_revision,
        active_sku_id=ACTIVE_SKU_ID,
        current_arc_id="arc-honey",
        next_topic_id=next_topic_id,
        updated_at=NOW,
    )
    return AgentState(
        tenant_id=TENANT_ID,
        session_id=SESSION_ID,
        session_epoch=1,
        active_sku_id=ACTIVE_SKU_ID,
        story_plan=effective_plan,
        story_checkpoint=checkpoint,
        played_history=played_history or [],
        completed_topic_ids=completed_topic_ids,
        rewrite_budget=RewriteBudgetState(max_retries=max_retries),
    )


def _make_fallback_candidate(
    verifier: P05KnowledgeAdapter,
    *,
    tenant_id: str = TENANT_ID,
    session_id: str = SESSION_ID,
    session_epoch: int = 1,
    covered_topic_ids: list[str] | None = None,
) -> SpeechCandidate:
    """Tạo ứng viên `PREAPPROVED_FALLBACK` gắn binding sống của `SKU-HONEY-01`."""
    evidence = verifier.get_sku_evidence(TENANT_ID, ACTIVE_SKU_ID, at_time=NOW)
    binding = evidence.to_version_binding(
        cited_evidence_ids=["ev-e01-honey-usage"],
        stated_price_vnd=159000,
    )
    topics = covered_topic_ids or []
    return SpeechCandidate(
        candidate_id=f"fb-{tenant_id}-{session_epoch}",
        tenant_id=tenant_id,
        session_id=session_id,
        session_epoch=session_epoch,
        origin=CandidateOrigin.PREAPPROVED_FALLBACK,
        scope_mode=TargetScopeMode.SINGLE_SKU,
        sku_refs=[ACTIVE_SKU_ID],
        sku_bindings=[binding],
        session_rights_version=1,
        intent="FALLBACK_SAFE_REMINDER",
        text="Mật ong hoa cà phê Đắk Lắk chai 500ml giá niêm yết 159.000đ, không dùng cho trẻ dưới 1 tuổi.",
        estimated_duration_sec=6.5,
        proposed_coverage=ProposedResponseCoverage(
            covered_topic_ids=topics,
            covered_intents=["An toàn sử dụng"],
            coverage_mode=CoverageMode.FULL,
            is_authoritative=False,
        ),
        verification_status=CandidateVerificationStatus.DRAFT,
    )


def _valid_draft_payload(
    *,
    text: str = "Pha 1-2 thìa mật ong với nước ấm dưới 50 độ C, không dùng cho trẻ dưới 1 tuổi.",
    cited_evidence_ids: list[str] | None = None,
    covered_claim_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Tạo payload JSON hợp lệ khớp `ChunkDraftLLMOutput`."""
    return {
        "text": text,
        "role": "PRODUCT_STORY",
        "cited_evidence_ids": cited_evidence_ids if cited_evidence_ids is not None else ["ev-e01-honey-usage"],
        "stated_price_vnd": None,
        "mentions_ocop": False,
        "semantic_breakpoint": True,
        "breakpoint_type": "TOPIC_END",
        "covered_claim_ids": covered_claim_ids if covered_claim_ids is not None else ["clm-e01-honey-allowed-01"],
        "rationale": "Bám sát hướng dẫn sử dụng an toàn",
    }


def _make_deps(
    steps: list[MockResponseStep],
    *,
    verifier: P05KnowledgeAdapter | None = None,
    fallback_candidates: list[SpeechCandidate] | None = None,
    max_chunk_duration_sec: float = 8.0,
) -> GraphRuntimeDeps:
    """Tạo `GraphRuntimeDeps` cho kiểm thử đồ thị offline."""
    effective_verifier = verifier or P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
    fb = (
        fallback_candidates
        if fallback_candidates is not None
        else [_make_fallback_candidate(effective_verifier)]
    )
    return GraphRuntimeDeps(
        llm_provider=MockLLMProvider(response_sequence=steps),
        knowledge_verifier=effective_verifier,
        repetition_detector=RepetitionDetector(RepetitionConfig()),
        fallback_candidates=fb,
        clock=VirtualClock(NOW),
        max_chunk_duration_sec=max_chunk_duration_sec,
    )


class TestBoundedRewriteBudgetAndRouting:
    """Kiểm thử ngân sách `1 + K` và các nhánh điều hướng của `StateGraph(AgentState)`."""

    @pytest.mark.parametrize("max_retries", [0, 1, 2])
    def test_continuous_retryable_failures_enforce_exact_1_plus_k_calls(
        self, max_retries: int
    ) -> None:
        """Khi bản nháp liên tục trượt P05/schema, tổng số lần gọi LLM phải bằng đúng `1 + K`."""
        bad_steps = [
            MockResponseStep(
                behavior=MockBehavior.VALID_JSON,
                payload=_valid_draft_payload(
                    text="Sản phẩm này giúp trị dứt điểm ho mãn tính cực nhanh!",
                    cited_evidence_ids=[],
                    covered_claim_ids=[],
                ),
            )
            for _ in range(1 + max_retries + 2)
        ]
        deps = _make_deps(bad_steps)
        state = _make_initial_state(max_retries=max_retries)

        result = run_storytelling_turn(state, deps, turn_id=f"turn-k-{max_retries}")

        assert len(result.telemetry_records) == 1 + max_retries
        assert result.final_state.rewrite_budget.retries_used == max_retries
        assert result.final_state.turn_outcome == AgentTurnOutcome.FALLBACK_PREAPPROVED
        assert result.final_state.verified_candidate is not None
        assert result.final_state.verified_candidate.origin == CandidateOrigin.PREAPPROVED_FALLBACK
        assert NODE_SAFE_FALLBACK in result.final_state.node_trace
        assert result.final_state.node_trace[-1] == NODE_FINALIZE_CANDIDATE
        assert result.final_state.completed_topic_ids == frozenset()

    def test_fail_then_succeed_on_bounded_rewrite(self) -> None:
        """Lần 0 lỗi JSON hoặc P05, lần 1 sửa đạt P05 -> `VERIFIED_READY` với `rewrite_attempt=1`."""
        deps = _make_deps(
            [
                MockResponseStep(behavior=MockBehavior.MALFORMED_JSON),
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_valid_draft_payload(),
                ),
            ]
        )
        result = run_storytelling_turn(_make_initial_state(max_retries=2), deps, turn_id="turn-fix-01")

        assert len(result.telemetry_records) == 2
        assert result.final_state.turn_outcome == AgentTurnOutcome.VERIFIED_READY
        assert result.final_state.rewrite_budget.retries_used == 1
        assert result.final_state.verified_candidate is not None
        assert result.final_state.verified_candidate.rewrite_attempt == 1
        assert result.final_state.node_trace == [
            NODE_LOAD_CONTEXT,
            NODE_PLAN_CHUNK,
            NODE_DRAFT_CHUNK,
            NODE_BOUNDED_REWRITE,
            NODE_CHECK_REPETITION,
            NODE_VERIFY_P05,
            NODE_FINALIZE_CANDIDATE,
        ]

    @pytest.mark.parametrize("failure_behavior", [MockBehavior.TIMEOUT, MockBehavior.PROVIDER_FAILURE])
    def test_non_retryable_provider_error_routes_immediately_to_fallback(
        self, failure_behavior: MockBehavior
    ) -> None:
        """Lỗi `TIMEOUT` hoặc `PROVIDER_FAILURE` không lãng phí ngân sách rewrite."""
        deps = _make_deps(
            [
                MockResponseStep(behavior=failure_behavior),
                MockResponseStep(behavior=MockBehavior.VALID_JSON, payload=_valid_draft_payload()),
            ]
        )
        result = run_storytelling_turn(_make_initial_state(max_retries=2), deps, turn_id="turn-err-01")

        assert len(result.telemetry_records) == 1
        assert result.final_state.rewrite_budget.retries_used == 0
        assert result.final_state.turn_outcome == AgentTurnOutcome.FALLBACK_PREAPPROVED
        assert result.final_state.node_trace == [
            NODE_LOAD_CONTEXT,
            NODE_PLAN_CHUNK,
            NODE_DRAFT_CHUNK,
            NODE_SAFE_FALLBACK,
            NODE_FINALIZE_CANDIDATE,
        ]

    def test_over_length_chunk_is_rejected_for_rewrite_not_silently_clamped(self) -> None:
        """Lời thoại dài vượt `max_chunk_duration_sec` phải bị từ chối để sửa lại chứ không cắt ngầm."""
        long_text = " ".join(["mật ong hoa cà phê đắk lắk"] * 12)  # ~60 từ -> ~23s > 8s
        deps = _make_deps(
            [
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_valid_draft_payload(text=long_text),
                ),
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_valid_draft_payload(),
                ),
            ],
            max_chunk_duration_sec=8.0,
        )
        result = run_storytelling_turn(_make_initial_state(max_retries=2), deps, turn_id="turn-len-01")

        assert len(result.telemetry_records) == 2
        assert result.final_state.turn_outcome == AgentTurnOutcome.VERIFIED_READY
        assert result.final_state.verified_candidate is not None
        assert result.final_state.verified_candidate.estimated_duration_sec <= 8.0
        assert result.final_state.draft_chunk is not None
        assert result.final_state.draft_chunk.estimated_duration_sec <= 8.0

    def test_invalid_or_cross_context_fallback_leads_to_safe_abort(self) -> None:
        """Fallback sai tenant/epoch hoặc phủ topic ngầm bị loại -> `SAFE_ABORT_NO_CANDIDATE`."""
        verifier = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
        bad_epoch_fallback = _make_fallback_candidate(verifier, session_epoch=99)
        bad_topic_fallback = _make_fallback_candidate(verifier, covered_topic_ids=["topic-honey-usage"])
        deps = _make_deps(
            [MockResponseStep(behavior=MockBehavior.TIMEOUT)],
            verifier=verifier,
            fallback_candidates=[bad_epoch_fallback, bad_topic_fallback],
        )
        result = run_storytelling_turn(_make_initial_state(max_retries=1), deps, turn_id="turn-abort-01")

        assert result.final_state.turn_outcome == AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE
        assert result.final_state.verified_candidate is None

    def test_switch_topic_when_repetition_detector_reports_repeated_facts(self) -> None:
        """Khi lặp dữ kiện cùng chủ đề (`REPEATED_FACTS`), `SWITCH_TOPIC` đổi sang chủ đề tiếp theo."""
        played_turn = PlayedTurnSummary(
            playback_event_id="pb-prev-01",
            turn_id="turn-prev-01",
            candidate_id="cand-prev-01",
            chunk_id="chunk-prev-01",
            sku_refs=[ACTIVE_SKU_ID],
            topic_ids=["topic-honey-usage"],
            covered_claim_ids=["clm-e01-honey-allowed-01"],
            intent="PROACTIVE_STORY:topic-honey-usage",
            spoken_text="Cách dùng mật ong mỗi sáng với nước ấm nhẹ.",
            occurred_at=NOW,
            is_simulated=True,
        )
        deps = _make_deps(
            [
                # Lần 0 trùng claim_id trên cùng intent & topic -> kích hoạt REPEATED_FACTS + SWITCH_TOPIC
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_valid_draft_payload(
                        text="Quý khách nhớ khuấy mật ong cùng nước vừa ấm để giữ trọn hương thơm.",
                        cited_evidence_ids=["ev-e01-honey-usage"],
                        covered_claim_ids=["clm-e01-honey-allowed-01"],
                    ),
                ),
                # Lần 1 sau khi chuyển sang topic-honey-quality -> nhắc bằng chứng khác & text khác biệt
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_valid_draft_payload(
                        text="Mật ong Đắk Lắk có màu vàng hổ phách sáng từ chính vụ Cư M'gar, nên để nơi khô thoáng.",
                        cited_evidence_ids=["ev-e01-honey-origin"],
                        covered_claim_ids=[],
                    ),
                ),
            ]
        )
        state = _make_initial_state(max_retries=2, played_history=[played_turn])

        result = run_storytelling_turn(state, deps, turn_id="turn-switch-01")

        assert result.final_state.turn_outcome == AgentTurnOutcome.VERIFIED_READY
        assert result.final_state.selected_topic_id == "topic-honey-quality"
        assert result.final_state.verified_candidate is not None
        assert result.final_state.verified_candidate.rewrite_attempt == 1
        assert NODE_CHECK_REPETITION in result.final_state.node_trace
        assert NODE_BOUNDED_REWRITE in result.final_state.node_trace

    def test_clean_termination_when_all_sku_topics_completed(self) -> None:
        """Khi toàn bộ chủ đề của `active_sku_id` đã hoàn tất, đồ thị dừng sạch với 0 lần gọi LLM."""
        deps = _make_deps([])
        state = _make_initial_state(
            completed_topic_ids=frozenset({"topic-honey-usage", "topic-honey-quality"}),
            next_topic_id=None,
        )
        result = run_storytelling_turn(state, deps, turn_id="turn-term-01")

        assert result.should_terminate is True
        assert result.termination_reason == "ALL_ELIGIBLE_TOPICS_COMPLETED"
        assert result.telemetry_records == ()
        assert result.final_state.turn_outcome == AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE
        assert result.final_state.node_trace == [
            NODE_LOAD_CONTEXT,
            NODE_PLAN_CHUNK,
            NODE_FINALIZE_CANDIDATE,
        ]


class TestAgentGraphContractsAndValidation:
    """Kiểm định ràng buộc đầu vào cho `GraphRuntimeDeps` và `run_storytelling_turn`."""

    def test_runtime_deps_rejects_invalid_duration_or_rights_version(self) -> None:
        verifier = P05KnowledgeAdapter.from_seed_file(VERIFIED_SEED_PATH)
        provider = MockLLMProvider(response_sequence=[])
        detector = RepetitionDetector()
        clock = VirtualClock(NOW)

        for bad_duration in (True, 0, -1.0, 31.0, float("nan")):
            with pytest.raises(ValueError):
                GraphRuntimeDeps(
                    llm_provider=provider,
                    knowledge_verifier=verifier,
                    repetition_detector=detector,
                    fallback_candidates=[],
                    clock=clock,
                    max_chunk_duration_sec=bad_duration,  # type: ignore[arg-type]
                )

        with pytest.raises(ValueError):
            GraphRuntimeDeps(
                llm_provider=provider,
                knowledge_verifier=verifier,
                repetition_detector=detector,
                fallback_candidates=[],
                clock=clock,
                session_rights_version=0,
            )

    def test_run_turn_rejects_unapproved_plan_or_finalized_state(self) -> None:
        deps = _make_deps([])
        draft_plan = _make_plan(status=StoryPlanApprovalStatus.DRAFT)
        with pytest.raises(Exception):
            run_storytelling_turn(_make_initial_state(plan=draft_plan), deps, turn_id="t-bad-plan")

        valid_state = _make_initial_state()
        finalized = valid_state.validated_update(
            turn_outcome=AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE,
            verified_candidate=None,
        )
        with pytest.raises(ValueError):
            run_storytelling_turn(finalized, deps, turn_id="t-finalized")

        with pytest.raises(ValueError):
            run_storytelling_turn(valid_state, deps, turn_id="   ")
