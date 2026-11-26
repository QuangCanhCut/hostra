"""Bộ kiểm thử đơn vị cho `PlayedTurnSummary`, `RewriteBudgetState`, `AgentState` và tương thích LangGraph.

1. File này giải quyết vấn đề gì?
   Xác minh các bất biến trạng thái đồ thị `AgentState` (tách biệt working memory khỏi authoritative state,
   đồng nhất `StoryPlan`–`StoryCheckpoint`–`Active SKU`, tách biệt `draft_candidate` và `verified_candidate`)
   cùng khả năng chạy trực tiếp trên `langgraph.graph.StateGraph(AgentState)`.
2. Trách nhiệm chính của module là gì?
   Kiểm tra chuyển đổi `PlayedTurnSummary.from_playback_completed()`, kiểm tra ngân sách `RewriteBudgetState`,
   kiểm tra toàn bộ negative invariants của `AgentState`, và chạy smoke test `StateGraph(AgentState)` với
   các dummy node không dùng LLM.
3. Module này liên kết với các thành phần nào?
   Kiểm thử `p06.schemas.state` cùng các schema liên quan trong `p06.schemas` và thư viện `langgraph`.
4. Input và output chính là gì?
   Input là trạng thái khởi tạo `AgentState` và các node giả lập cập nhật từng phần trạng thái;
   Output là xác nhận trạng thái hợp lệ/không hợp lệ và vết thực thi `node_trace` từ LangGraph.
5. Có những constraints hoặc invariants quan trọng nào?
   Không gọi LLM hoặc `ProviderFactory`; đồ thị `StateGraph` trong file này chỉ là dummy smoke test
   kiểm tra tương thích Pydantic v2 + LangGraph theo phạm vi Phase 1.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from p06.schemas import (
    MAX_REWRITE_RETRIES_LIMIT,
    AgentState,
    AgentTurnOutcome,
    CandidateOrigin,
    CandidateVerificationStatus,
    CoverageMode,
    PlaybackCompleted,
    PlaybackEventSource,
    PlayedTurnSummary,
    ProposedResponseCoverage,
    RewriteBudgetState,
    SkuVersionBinding,
    SpeechCandidate,
    StoryArc,
    StoryCheckpoint,
    StoryChunk,
    StoryChunkRole,
    StoryPlan,
    StoryPlanApprovalStatus,
    StoryTopic,
    TargetScopeMode,
)


def _make_plan(status: StoryPlanApprovalStatus = StoryPlanApprovalStatus.APPROVED) -> StoryPlan:
    """Khởi tạo `StoryPlan` mẫu phục vụ kiểm thử `AgentState`.

    Args:
        status: Trạng thái duyệt kế hoạch.

    Returns:
        StoryPlan: Kế hoạch mẫu có 2 arc và 2 topic.
    """
    return StoryPlan(
        plan_id="plan-state-01",
        tenant_id="tenant-demo-01",
        session_id="session-demo-01",
        plan_revision=1,
        approval_status=status,
        approved_by="owner-01" if status == StoryPlanApprovalStatus.APPROVED else None,
        approved_at=datetime(2026, 11, 25, 9, 0, tzinfo=timezone.utc)
        if status == StoryPlanApprovalStatus.APPROVED
        else None,
        session_goal="Kể chuyện mật ong và trà Shan Tuyết",
        pinned_sku_ids=["SKU-HONEY-01", "SKU-TEA-02"],
        knowledge_versions_by_sku={"SKU-HONEY-01": 1, "SKU-TEA-02": 1},
        arcs=[
            StoryArc(
                arc_id="arc-01",
                position=1,
                title="Mật ong Đắk Lắk",
                sku_id="SKU-HONEY-01",
                target_duration_sec=300,
                topics=[
                    StoryTopic(
                        topic_id="topic-01",
                        title="Nguồn gốc hoa cà phê",
                        sku_id="SKU-HONEY-01",
                        fact_refs=["ev-honey-04"],
                    )
                ],
            ),
            StoryArc(
                arc_id="arc-02",
                position=2,
                title="Trà Shan Tuyết",
                sku_id="SKU-TEA-02",
                target_duration_sec=300,
                topics=[
                    StoryTopic(
                        topic_id="topic-02",
                        title="Cách pha trà",
                        sku_id="SKU-TEA-02",
                        fact_refs=["ev-tea-01"],
                    )
                ],
            ),
        ],
    )


def _make_checkpoint() -> StoryCheckpoint:
    """Khởi tạo `StoryCheckpoint` đồng bộ với `_make_plan()`.

    Returns:
        StoryCheckpoint: Checkpoint mẫu tại `arc-01`.
    """
    return StoryCheckpoint(
        tenant_id="tenant-demo-01",
        session_id="session-demo-01",
        session_epoch=1,
        plan_id="plan-state-01",
        plan_revision=1,
        active_sku_id="SKU-HONEY-01",
        current_arc_id="arc-01",
        next_topic_id="topic-01",
    )


def _make_candidate(
    status: CandidateVerificationStatus = CandidateVerificationStatus.DRAFT,
    tenant_id: str = "tenant-demo-01",
    session_id: str = "session-demo-01",
    session_epoch: int = 1,
) -> SpeechCandidate:
    """Khởi tạo `SpeechCandidate` mẫu tương ứng trạng thái kiểm chứng yêu cầu.

    Args:
        status: Trạng thái kiểm chứng (`DRAFT`, `VERIFIED`, `REJECTED`).
        tenant_id: Mã tenant.
        session_id: Mã phiên.
        session_epoch: Thế hệ phiên.

    Returns:
        SpeechCandidate: Ứng viên hợp lệ theo trạng thái đã chọn.
    """
    return SpeechCandidate(
        candidate_id=f"cand-{status.value.lower()}",
        tenant_id=tenant_id,
        session_id=session_id,
        session_epoch=session_epoch,
        origin=CandidateOrigin.PROACTIVE_STORY,
        source_chunk_id="chunk-01",
        scope_mode=TargetScopeMode.SINGLE_SKU,
        sku_refs=["SKU-HONEY-01"],
        sku_bindings=[
            SkuVersionBinding(
                sku_id="SKU-HONEY-01",
                knowledge_version=1,
                ocop_version=1,
                rights_version=1,
                cited_evidence_ids=["ev-honey-04"],
            )
        ],
        session_rights_version=1,
        intent="product_story",
        text="Mật ong hoa cà phê Cư M'gar Đắk Lắk thu hoạch đúng mùa tháng 2-3.",
        estimated_duration_sec=6.0,
        proposed_coverage=ProposedResponseCoverage(
            covered_topic_ids=["topic-01"],
            covered_intents=["product_story"],
            coverage_mode=CoverageMode.FULL,
        ),
        verification_status=status,
        verified_by_gate_decision_id="gate-01" if status == CandidateVerificationStatus.VERIFIED else None,
        verified_at=datetime.now(timezone.utc) if status == CandidateVerificationStatus.VERIFIED else None,
        rejection_reasons=["MISSING_EVIDENCE"] if status == CandidateVerificationStatus.REJECTED else [],
    )


def _make_initial_state() -> AgentState:
    """Tạo `AgentState` khởi đầu hợp lệ cho các kịch bản test.

    Returns:
        AgentState: Trạng thái đầu lượt với `turn_outcome=IN_PROGRESS`.
    """
    return AgentState(
        tenant_id="tenant-demo-01",
        session_id="session-demo-01",
        session_epoch=1,
        active_sku_id="SKU-HONEY-01",
        story_plan=_make_plan(),
        story_checkpoint=_make_checkpoint(),
    )


class TestPlayedTurnSummaryAndRewriteBudget:
    """Kiểm định `PlayedTurnSummary` và `RewriteBudgetState`."""

    def test_from_playback_completed_conversion(self) -> None:
        """Kiểm tra chuyển đổi từ `PlaybackCompleted` sang `PlayedTurnSummary` giữ đúng provenance."""
        event = PlaybackCompleted(
            playback_event_id="pb-01",
            tenant_id="tenant-demo-01",
            session_id="session-demo-01",
            session_epoch=1,
            turn_id="turn-01",
            candidate_id="cand-verified",
            chunk_id="chunk-01",
            sku_refs=["SKU-HONEY-01"],
            confirmed_topic_ids=["topic-01"],
            spoken_text="Mật ong hoa cà phê nguyên chất 500ml.",
            actual_duration_ms=3500,
            occurred_at=datetime.now(timezone.utc),
            event_source=PlaybackEventSource.SIMULATED_HARNESS,
            is_simulated=True,
            simulation_run_id="run-01",
        )
        summary = PlayedTurnSummary.from_playback_completed(event=event, intent="product_story")
        assert summary.playback_event_id == "pb-01"
        assert summary.topic_ids == ["topic-01"]
        assert summary.intent == "product_story"
        assert summary.is_simulated is True

        with pytest.raises(ValidationError):
            PlayedTurnSummary.from_playback_completed(event=event, intent="   ")

    def test_rewrite_budget_bounds_and_can_retry(self) -> None:
        """Kiểm tra thuộc tính `can_retry`, chặn `retries_used > max_retries` và strict types."""
        budget = RewriteBudgetState(max_retries=2, retries_used=1)
        assert budget.can_retry is True

        exhausted = RewriteBudgetState(max_retries=2, retries_used=2)
        assert exhausted.can_retry is False

        with pytest.raises(ValidationError):
            RewriteBudgetState(max_retries=2, retries_used=3)

        with pytest.raises(ValidationError):
            RewriteBudgetState(max_retries=MAX_REWRITE_RETRIES_LIMIT + 1)

        with pytest.raises(ValidationError):
            RewriteBudgetState(max_retries=True, retries_used=0)  # type: ignore[arg-type]

        with pytest.raises(ValidationError):
            RewriteBudgetState(last_failure_reasons=["   "])


class TestAgentStateInvariants:
    """Kiểm định các bất biến đồng bộ, toàn vẹn tham chiếu, `frozen=True` và cô lập trạng thái trên `AgentState`."""

    def test_valid_agent_state_and_json_roundtrip(self) -> None:
        """Đảm bảo `AgentState` hợp lệ và khôi phục nguyên vẹn qua JSON."""
        state = _make_initial_state()
        assert state.is_authoritative_session_state is False
        restored = AgentState.model_validate_json(state.model_dump_json())
        assert restored == state

    def test_frozen_immutability_and_validated_update(self) -> None:
        """`frozen=True` ngăn gán trực tiếp, và `validated_update()` giữ nguyên bản gốc nếu lỗi."""
        state = _make_initial_state()
        with pytest.raises(ValidationError):
            state.turn_outcome = AgentTurnOutcome.VERIFIED_READY  # type: ignore[misc]
        assert state.turn_outcome == AgentTurnOutcome.IN_PROGRESS

        # validated_update vi phạm invariant -> ném ValidationError và giữ nguyên state gốc
        with pytest.raises(ValidationError):
            state.validated_update(turn_outcome=AgentTurnOutcome.VERIFIED_READY, verified_candidate=None)
        assert state.turn_outcome == AgentTurnOutcome.IN_PROGRESS

        # completed_topic_ids là frozenset để chặn mutation ngầm ngoài validator
        assert isinstance(state.completed_topic_ids, frozenset)
        with pytest.raises(AttributeError):
            state.completed_topic_ids.add("topic-01")  # type: ignore[attr-defined]

        # validated_update chấp nhận set đầu vào, chuyển thành frozenset và giữ nguyên state gốc
        verified = _make_candidate(CandidateVerificationStatus.VERIFIED)
        updated = state.validated_update(
            completed_topic_ids={"topic-01"},
            verified_candidate=verified,
            turn_outcome=AgentTurnOutcome.VERIFIED_READY,
            node_trace=["verify_node"],
        )
        assert updated.completed_topic_ids == frozenset({"topic-01"})
        assert isinstance(updated.completed_topic_ids, frozenset)
        assert AgentState.model_validate_json(updated.model_dump_json()) == updated
        assert updated.turn_outcome == AgentTurnOutcome.VERIFIED_READY
        assert updated.verified_candidate is not None
        assert updated.node_trace == ["verify_node"]
        assert state.turn_outcome == AgentTurnOutcome.IN_PROGRESS
        assert state.completed_topic_ids == frozenset()

    def test_non_authoritative_and_plan_approval_enforced(self) -> None:
        """Từ chối cờ authoritative sai kiểu/giá trị hoặc `StoryPlan` chưa `APPROVED`."""
        for bad_auth in (True, 0, "false"):
            with pytest.raises(ValidationError):
                AgentState(
                    is_authoritative_session_state=bad_auth,  # type: ignore[arg-type]
                    tenant_id="tenant-demo-01",
                    session_id="session-demo-01",
                    session_epoch=1,
                    active_sku_id="SKU-HONEY-01",
                    story_plan=_make_plan(),
                    story_checkpoint=_make_checkpoint(),
                )

        with pytest.raises(ValidationError):
            AgentState(
                tenant_id="tenant-demo-01",
                session_id="session-demo-01",
                session_epoch=1,
                active_sku_id="SKU-HONEY-01",
                story_plan=_make_plan(status=StoryPlanApprovalStatus.DRAFT),
                story_checkpoint=_make_checkpoint(),
            )

    def test_context_sync_and_referential_integrity_rejected(self) -> None:
        """Kiểm tra lệch tenant/session/epoch/plan/SKU, tham chiếu arc/topic/chunk sai và tràn cửa sổ."""
        base = _make_initial_state()

        # Lệch active_sku ngoài danh sách ghim
        with pytest.raises(ValidationError):
            AgentState(**{**base.model_dump(), "active_sku_id": "SKU-CASHEW-03"})

        # Checkpoint lệch tenant_id (R10)
        bad_tenant_cp = StoryCheckpoint.model_validate(
            {**_make_checkpoint().model_dump(), "tenant_id": "tenant-other"}
        )
        with pytest.raises(ValidationError):
            base.validated_update(story_checkpoint=bad_tenant_cp)

        # Checkpoint lệch session_epoch
        bad_cp = StoryCheckpoint.model_validate(
            {**_make_checkpoint().model_dump(), "session_epoch": 2}
        )
        with pytest.raises(ValidationError):
            base.validated_update(story_checkpoint=bad_cp)

        # Checkpoint trỏ vào arc không tồn tại
        bad_arc_cp = StoryCheckpoint.model_validate(
            {**_make_checkpoint().model_dump(), "current_arc_id": "arc-missing"}
        )
        with pytest.raises(ValidationError):
            base.validated_update(story_checkpoint=bad_arc_cp)

        # Checkpoint.next_topic_id không tồn tại trong story_plan
        bad_next_topic_cp = StoryCheckpoint.model_validate(
            {**_make_checkpoint().model_dump(), "next_topic_id": "topic-nonexistent"}
        )
        with pytest.raises(ValidationError):
            base.validated_update(story_checkpoint=bad_next_topic_cp)

        # completed_topic_ids chứa topic không có trong story_plan
        with pytest.raises(ValidationError):
            base.validated_update(completed_topic_ids={"topic-999"})

        # selected_arc_id không tồn tại trong story_plan
        with pytest.raises(ValidationError):
            base.validated_update(selected_arc_id="arc-missing")

        # selected_topic_id không tồn tại trong story_plan
        with pytest.raises(ValidationError):
            base.validated_update(selected_topic_id="topic-missing")

        # selected_topic_id tồn tại nhưng thuộc arc khác với selected_arc_id
        with pytest.raises(ValidationError):
            base.validated_update(selected_arc_id="arc-01", selected_topic_id="topic-02")

        # draft_chunk lệch plan_id / arc_id / topic_id khác arc / sku_id ngoài phiên
        valid_chunk = StoryChunk(
            chunk_id="chunk-01",
            plan_id=base.story_plan.plan_id,
            plan_revision=base.story_plan.plan_revision,
            arc_id="arc-01",
            topic_id="topic-01",
            sequence_index=0,
            role=StoryChunkRole.PRODUCT_STORY,
            sku_id="SKU-HONEY-01",
            text="Mật ong hoa cà phê Cư M'gar Đắk Lắk.",
            estimated_duration_sec=5.0,
        )
        with pytest.raises(ValidationError):
            base.validated_update(
                draft_chunk=StoryChunk.model_validate({**valid_chunk.model_dump(), "plan_id": "plan-other"})
            )
        with pytest.raises(ValidationError):
            base.validated_update(
                draft_chunk=StoryChunk.model_validate({**valid_chunk.model_dump(), "arc_id": "arc-missing"})
            )
        with pytest.raises(ValidationError):
            base.validated_update(
                draft_chunk=StoryChunk.model_validate({**valid_chunk.model_dump(), "topic_id": "topic-02"})
            )
        with pytest.raises(ValidationError):
            base.validated_update(
                draft_chunk=StoryChunk.model_validate({**valid_chunk.model_dump(), "sku_id": "SKU-CASHEW-03"})
            )

        # len(played_history) vượt quá played_history_window_size
        sample_event = PlaybackCompleted(
            playback_event_id="pb-w1",
            tenant_id=base.tenant_id,
            session_id=base.session_id,
            session_epoch=1,
            turn_id="turn-1",
            candidate_id="cand-1",
            spoken_text="Mật ong hoa cà phê.",
            actual_duration_ms=2000,
            occurred_at=datetime.now(timezone.utc),
            event_source=PlaybackEventSource.SIMULATED_HARNESS,
            is_simulated=True,
            simulation_run_id="run-w",
        )
        summary_1 = PlayedTurnSummary.from_playback_completed(sample_event, intent="story")
        summary_2 = PlayedTurnSummary.from_playback_completed(
            PlaybackCompleted(**{**sample_event.model_dump(), "playback_event_id": "pb-w2", "turn_id": "turn-2"}),
            intent="story",
        )
        with pytest.raises(ValidationError):
            base.validated_update(
                played_history_window_size=1,
                played_history=[summary_1, summary_2],
            )

        # Chuỗi khoảng trắng và bool->int trên AgentState bị chặn
        with pytest.raises(ValidationError):
            base.validated_update(node_trace=["   "])
        with pytest.raises(ValidationError):
            base.validated_update(session_epoch=True)

    def test_draft_vs_verified_separation_and_outcome_consistency(self) -> None:
        """I-02: cô lập `draft_candidate` khỏi `verified_candidate` và đối chiếu `turn_outcome`."""
        base = _make_initial_state()

        # draft_candidate không được phép ở trạng thái VERIFIED
        with pytest.raises(ValidationError):
            base.validated_update(
                draft_candidate=_make_candidate(CandidateVerificationStatus.VERIFIED),
            )

        # verified_candidate không được phép ở trạng thái DRAFT
        with pytest.raises(ValidationError):
            base.validated_update(
                verified_candidate=_make_candidate(CandidateVerificationStatus.DRAFT),
            )

        # verified_candidate lệch tenant hoặc epoch -> chặn rò rỉ đa tenant/stale epoch
        with pytest.raises(ValidationError):
            base.validated_update(
                verified_candidate=_make_candidate(
                    CandidateVerificationStatus.VERIFIED,
                    tenant_id="tenant-other",
                ),
                turn_outcome=AgentTurnOutcome.VERIFIED_READY,
            )

        # VERIFIED_READY và FALLBACK_PREAPPROVED thiếu verified_candidate -> từ chối
        with pytest.raises(ValidationError):
            base.validated_update(
                turn_outcome=AgentTurnOutcome.VERIFIED_READY,
                verified_candidate=None,
            )
        with pytest.raises(ValidationError):
            base.validated_update(
                turn_outcome=AgentTurnOutcome.FALLBACK_PREAPPROVED,
                verified_candidate=None,
            )

        # SAFE_ABORT_NO_CANDIDATE nhưng vẫn còn verified_candidate -> từ chối
        with pytest.raises(ValidationError):
            base.validated_update(
                turn_outcome=AgentTurnOutcome.SAFE_ABORT_NO_CANDIDATE,
                verified_candidate=_make_candidate(CandidateVerificationStatus.VERIFIED),
            )


class TestLangGraphStateCompatibility:
    """Smoke test và kiểm định biên `AgentState.from_graph_result` với `langgraph.graph.StateGraph`."""

    def test_state_graph_dummy_invocation(self) -> None:
        """Biên dịch và gọi một `StateGraph(AgentState)` tối giản để xác nhận tương thích schema."""

        def dummy_draft_node(state: AgentState) -> dict[str, Any]:
            """Node giả lập sinh bản nháp `StoryChunk` và `SpeechCandidate` chưa duyệt."""
            chunk = StoryChunk(
                chunk_id="chunk-01",
                plan_id=state.story_plan.plan_id,
                plan_revision=state.story_plan.plan_revision,
                arc_id="arc-01",
                topic_id="topic-01",
                sequence_index=0,
                role=StoryChunkRole.PRODUCT_STORY,
                sku_id=state.active_sku_id,
                text="Mật ong hoa cà phê Cư M'gar Đắk Lắk thu hoạch đúng mùa tháng 2-3.",
                cited_evidence_ids=["ev-honey-04"],
                estimated_duration_sec=6.0,
            )
            return {
                "selected_arc_id": "arc-01",
                "selected_topic_id": "topic-01",
                "draft_chunk": chunk,
                "draft_candidate": _make_candidate(CandidateVerificationStatus.DRAFT),
                "node_trace": [*state.node_trace, "dummy_draft_node"],
            }

        def dummy_verify_node(state: AgentState) -> dict[str, Any]:
            """Node giả lập nhận kết quả `VERIFIED` và chốt `AgentTurnOutcome.VERIFIED_READY`."""
            return {
                "draft_candidate": None,
                "verified_candidate": _make_candidate(CandidateVerificationStatus.VERIFIED),
                "turn_outcome": AgentTurnOutcome.VERIFIED_READY,
                "node_trace": [*state.node_trace, "dummy_verify_node"],
            }

        graph = StateGraph(AgentState)
        graph.add_node("dummy_draft_node", dummy_draft_node)
        graph.add_node("dummy_verify_node", dummy_verify_node)
        graph.add_edge(START, "dummy_draft_node")
        graph.add_edge("dummy_draft_node", "dummy_verify_node")
        graph.add_edge("dummy_verify_node", END)

        compiled = graph.compile()
        result = compiled.invoke(_make_initial_state())

        final_state = AgentState.from_graph_result(result)
        assert final_state.turn_outcome == AgentTurnOutcome.VERIFIED_READY
        assert final_state.verified_candidate is not None
        assert final_state.verified_candidate.is_ready_for_tts() is True
        assert final_state.node_trace == ["dummy_draft_node", "dummy_verify_node"]

    def test_from_graph_result_catches_invalid_final_node_output_a_blk_01(self) -> None:
        """A-BLK-01: tái hiện `StateGraph.invoke()` bỏ qua model_validator cuối và bị `from_graph_result()` chặn."""

        def broken_final_node(state: AgentState) -> dict[str, Any]:
            """Node lỗi trả về `VERIFIED_READY` nhưng `verified_candidate=None`."""
            return {
                "turn_outcome": AgentTurnOutcome.VERIFIED_READY,
                "verified_candidate": None,
                "node_trace": [*state.node_trace, "broken_final_node"],
            }

        graph = StateGraph(AgentState)
        graph.add_node("broken_final_node", broken_final_node)
        graph.add_edge(START, "broken_final_node")
        graph.add_edge("broken_final_node", END)

        compiled = graph.compile()
        raw_result = compiled.invoke(_make_initial_state())

        # Bằng chứng thực nghiệm A-BLK-01: LangGraph trả về dict thô chưa chạy model_validator.
        assert isinstance(raw_result, dict)
        assert raw_result["turn_outcome"] == AgentTurnOutcome.VERIFIED_READY
        assert raw_result["verified_candidate"] is None

        # Cổng biên AgentState.from_graph_result() bắt buộc bắt được vi phạm và ném ValidationError.
        with pytest.raises(ValidationError):
            AgentState.from_graph_result(raw_result)
