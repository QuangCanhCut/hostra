"""Kiểm thử đơn vị cho hệ thống bộ nhớ 4 phần (`p06.memory`), `RepetitionDetector` và tích hợp nguyên tử vào `SimulatedPlaybackHarness`.

1. File này giải quyết vấn đề gì?
   Xác minh tính đúng đắn, bất biến phiên và chống lặp của toàn bộ thành phần bộ nhớ E01-T06
   (`ShortTermPlayedHistory`, `GlobalTopicCoverage`, `SessionViewerContext`, `NoOpSemanticMemory`),
   bộ phát hiện lặp `RepetitionDetector` và cập nhật nguyên tử trong `SimulatedPlaybackHarness`.
2. Trách nhiệm chính của module là gì?
   Kiểm tra đầy đủ cửa sổ trượt `W ∈ {5, 10, 20}`, tập chống trùng bất biến, tách biệt đề xuất/kiểm chứng/phát thật,
   5 phân loại của `RepetitionDetector`, chuẩn hóa tiếng Việt NFC và `build_agent_state()` (`I-04`).
3. Module này liên kết với các thành phần nào?
   Kiểm thử trực tiếp `p06.memory`, `p06.simulation.SimulatedPlaybackHarness`, `p06.adapters.mocks.MockPlaybackAckBus`
   và các schema trong `p06.schemas`.
4. Input và output chính là gì?
   Input là `StoryPlan`, `StoryCheckpoint`, `SpeechCandidate`, `PlaybackCompleted`/`PlaybackAckResult`,
   và chuỗi văn bản tiếng Việt;
   Output là xác nhận mọi bất biến trạng thái, ngưỡng lặp và tính nguyên tử đạt chuẩn.
5. Có những constraints hoặc invariants quan trọng nào?
   - `FAILED`, `UNKNOWN`, duplicate, stale không bao giờ làm thay đổi bất kỳ lớp bộ nhớ nào.
   - `completed_topic_ids` chỉ tiến khi `PlaybackCompleted` đạt `min_chunks_per_topic`.
   - `build_agent_state()` từ chối tự đổi `active_sku_id` (`I-04`) hoặc lệch `plan_id`/`plan_revision`.
"""

from __future__ import annotations

import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from pydantic import ValidationError

from p06.adapters.interfaces import AckApplyStatus, PlaybackAckResult
from p06.adapters.mocks import MockPlaybackAckBus
from p06.memory import (
    GlobalTopicCoverage,
    NoOpSemanticMemory,
    OptionalSemanticMemory,
    RepetitionAction,
    RepetitionCategory,
    RepetitionCheckResult,
    RepetitionConfig,
    RepetitionDetector,
    SemanticSimilarityMatch,
    SessionViewerContext,
    ShortTermPlayedHistory,
    TopicCoverageSnapshot,
    ViewerQuestionRecord,
    normalize_vietnamese_for_repetition,
)
from p06.schemas import (
    AgentState,
    CandidateOrigin,
    CoverageMode,
    MAX_PLAYED_HISTORY_WINDOW,
    PlaybackCompleted,
    PlaybackEventSource,
    PlaybackOutcomeStatus,
    PlayedTurnSummary,
    ProposedResponseCoverage,
    SkuVersionBinding,
    SpeechCandidate,
    StoryArc,
    StoryCheckpoint,
    StoryPlan,
    StoryPlanApprovalStatus,
    StoryTopic,
)
from p06.schemas.candidate import TargetScopeMode
from p06.simulation import SimulatedPlaybackHarness, VirtualClock

TENANT_ID = "tenant-p06-mem-01"
SESSION_ID = "session-mem-01"
SIM_RUN_ID = "sim-run-e01-mem"
START_AT = datetime(2026, 11, 26, 14, 0, 0, tzinfo=timezone.utc)


def _make_turn(
    index: int,
    *,
    chunk_id: Optional[str] = None,
    spoken_text: Optional[str] = None,
    topic_ids: Optional[list[str]] = None,
    sku_refs: Optional[list[str]] = None,
    covered_claim_ids: Optional[list[str]] = None,
    intent: str = "PRODUCT_STORY",
) -> PlayedTurnSummary:
    return PlayedTurnSummary(
        playback_event_id=f"evt-{index:03d}",
        turn_id=f"turn-{index:03d}",
        candidate_id=f"cand-{index:03d}",
        chunk_id=chunk_id if chunk_id is not None else f"chunk-{index:03d}",
        sku_refs=sku_refs if sku_refs is not None else ["SKU-HONEY-01"],
        topic_ids=topic_ids if topic_ids is not None else ["topic-01"],
        covered_claim_ids=covered_claim_ids if covered_claim_ids is not None else [],
        intent=intent,
        spoken_text=spoken_text or f"Lời thoại lượt thứ {index} về mật ong hoa cà phê Đắk Lắk.",
        occurred_at=START_AT + timedelta(seconds=index * 10),
        is_simulated=True,
    )


def _make_story_plan(
    *,
    plan_id: str = "plan-mem-01",
    plan_revision: int = 1,
    tenant_id: str = TENANT_ID,
    session_id: str = SESSION_ID,
) -> StoryPlan:
    return StoryPlan(
        plan_id=plan_id,
        tenant_id=tenant_id,
        session_id=session_id,
        plan_revision=plan_revision,
        approval_status=StoryPlanApprovalStatus.APPROVED,
        approved_by="owner-01",
        approved_at=START_AT - timedelta(minutes=5),
        session_goal="Giới thiệu mật ong hoa cà phê và trà shan tuyết đạt chuẩn OCOP.",
        pinned_sku_ids=["SKU-HONEY-01", "SKU-TEA-01"],
        arcs=[
            StoryArc(
                arc_id="arc-01",
                position=1,
                title="Mật ong hoa cà phê",
                sku_id="SKU-HONEY-01",
                target_duration_sec=300,
                topics=[
                    StoryTopic(
                        topic_id="topic-01",
                        title="Nguồn gốc vùng trồng",
                        sku_id="SKU-HONEY-01",
                        is_mandatory=True,
                        allowed_claim_ids=["claim-h-01"],
                    ),
                    StoryTopic(
                        topic_id="topic-02",
                        title="Quy trình thu hoạch",
                        sku_id="SKU-HONEY-01",
                        is_mandatory=True,
                        allowed_claim_ids=["claim-h-02"],
                    ),
                ],
            ),
            StoryArc(
                arc_id="arc-02",
                position=2,
                title="Trà Shan Tuyết",
                sku_id="SKU-TEA-01",
                target_duration_sec=300,
                topics=[
                    StoryTopic(
                        topic_id="topic-03",
                        title="Trà cổ thụ Hà Giang",
                        sku_id="SKU-TEA-01",
                        is_mandatory=False,
                        allowed_claim_ids=["claim-t-01"],
                    ),
                ],
            ),
        ],
    )


def _make_checkpoint(
    *,
    plan_id: str = "plan-mem-01",
    plan_revision: int = 1,
    session_epoch: int = 1,
    active_sku_id: str = "SKU-HONEY-01",
    next_topic_id: Optional[str] = "topic-01",
) -> StoryCheckpoint:
    return StoryCheckpoint(
        tenant_id=TENANT_ID,
        session_id=SESSION_ID,
        session_epoch=session_epoch,
        plan_id=plan_id,
        plan_revision=plan_revision,
        active_sku_id=active_sku_id,
        current_arc_id="arc-01",
        next_topic_id=next_topic_id,
        updated_at=START_AT,
    )


def _make_playback_event(
    *,
    playback_event_id: str = "evt-pb-01",
    turn_id: str = "turn-01",
    candidate_id: str = "cand-01",
    chunk_id: Optional[str] = "chunk-01",
    confirmed_topic_ids: Optional[list[str]] = None,
    tenant_id: str = TENANT_ID,
    session_id: str = SESSION_ID,
    session_epoch: int = 1,
    offset_sec: int = 10,
) -> PlaybackCompleted:
    return PlaybackCompleted(
        playback_event_id=playback_event_id,
        tenant_id=tenant_id,
        session_id=session_id,
        session_epoch=session_epoch,
        turn_id=turn_id,
        candidate_id=candidate_id,
        chunk_id=chunk_id,
        sku_refs=["SKU-HONEY-01"],
        confirmed_topic_ids=["topic-01"] if confirmed_topic_ids is None else confirmed_topic_ids,
        spoken_text="Mật ong hoa cà phê Đắk Lắk thu hoạch mùa khô nguyên chất 500ml.",
        actual_duration_ms=5000,
        occurred_at=START_AT + timedelta(seconds=offset_sec),
        event_source=PlaybackEventSource.SIMULATED_HARNESS,
        is_simulated=True,
        simulation_run_id=SIM_RUN_ID,
    )


def _make_verified_candidate(
    *,
    candidate_id: str = "cand-01",
    source_chunk_id: str = "chunk-01",
    topic_ids: Optional[list[str]] = None,
    text: str = "Mật ong hoa cà phê Đắk Lắk thu hoạch mùa khô nguyên chất chai 500ml giá 159.000đ.",
    sku_id: str = "SKU-HONEY-01",
    intent: str = "PRODUCT_STORY",
    session_epoch: int = 1,
) -> SpeechCandidate:
    draft = SpeechCandidate(
        candidate_id=candidate_id,
        tenant_id=TENANT_ID,
        session_id=SESSION_ID,
        session_epoch=session_epoch,
        origin=CandidateOrigin.PROACTIVE_STORY,
        source_chunk_id=source_chunk_id,
        scope_mode=TargetScopeMode.SINGLE_SKU,
        sku_refs=[sku_id],
        sku_bindings=[
            SkuVersionBinding(
                sku_id=sku_id,
                knowledge_version=1,
                ocop_version=1,
                rights_version=1,
                cited_evidence_ids=["ev-01"],
                stated_price_vnd=159000,
            )
        ],
        session_rights_version=1,
        intent=intent,
        text=text,
        estimated_duration_sec=5.0,
        proposed_coverage=ProposedResponseCoverage(
            covered_topic_ids=["topic-01"] if topic_ids is None else topic_ids,
            covered_intents=[intent],
            coverage_mode=CoverageMode.FULL,
        ),
    )
    return draft.mark_verified("gate-allow-01", START_AT)


# ---------------------------------------------------------------------------
# 1. ShortTermPlayedHistory
# ---------------------------------------------------------------------------


class TestShortTermPlayedHistory:
    @pytest.mark.parametrize("window_size", [5, 10, 20])
    def test_sliding_window_preserves_full_dedup_sets(self, window_size: int) -> None:
        history = ShortTermPlayedHistory(
            window_size=window_size,
            tenant_id=TENANT_ID,
            session_id=SESSION_ID,
            session_epoch=1,
        )
        total_turns = window_size + 7
        for idx in range(1, total_turns + 1):
            history.append_confirmed_turn(
                _make_turn(idx),
                tenant_id=TENANT_ID,
                session_id=SESSION_ID,
                session_epoch=1,
            )

        recent = history.recent_turns()
        assert len(recent) == window_size
        assert recent[0].turn_id == f"turn-{total_turns - window_size + 1:03d}"
        assert recent[-1].turn_id == f"turn-{total_turns:03d}"
        assert history.to_agent_state_window() == list(recent)

        # Lượt đầu tiên đã trượt khỏi cửa sổ W nhưng vẫn phải tồn tại trong all_turns và tập chống trùng.
        assert len(history.all_turns()) == total_turns
        assert history.has_chunk_been_played("chunk-001") is True
        assert history.has_event("evt-001") is True
        assert history.has_turn("turn-001") is True
        assert "chunk-001" in history.completed_chunk_ids
        assert "evt-001" in history.seen_event_ids
        assert "turn-001" in history.seen_turn_ids

    def test_with_window_size_copies_full_history_and_dedup_sets(self) -> None:
        base = ShortTermPlayedHistory(
            window_size=20,
            tenant_id=TENANT_ID,
            session_id=SESSION_ID,
            session_epoch=2,
            initial_turns=[_make_turn(i) for i in range(1, 13)],
        )
        narrowed = base.with_window_size(5)

        assert narrowed.window_size == 5
        assert len(narrowed.recent_turns()) == 5
        assert len(narrowed.all_turns()) == 12
        assert narrowed.has_chunk_been_played("chunk-001") is True
        assert narrowed.has_event("evt-001") is True
        assert narrowed.has_turn("turn-001") is True
        assert narrowed.tenant_id == TENANT_ID
        assert narrowed.session_id == SESSION_ID
        assert narrowed.session_epoch == 2

        # Đảm bảo hai thực thể độc lập nhau khi nạp thêm vào bản sao mới.
        narrowed.append_confirmed_turn(_make_turn(13))
        assert len(narrowed.all_turns()) == 13
        assert len(base.all_turns()) == 12

    def test_rejects_invalid_window_size_duplicates_and_context_mismatch(self) -> None:
        for invalid in (True, False, 0, -3, MAX_PLAYED_HISTORY_WINDOW + 1):
            with pytest.raises(ValueError):
                ShortTermPlayedHistory(window_size=invalid)  # type: ignore[arg-type]

        # Trùng playback_event_id hoặc turn_id ngay trong initial_turns.
        t1 = _make_turn(1)
        t1_dup_event = PlayedTurnSummary(
            playback_event_id=t1.playback_event_id,
            turn_id="turn-999",
            candidate_id="cand-999",
            intent="PRODUCT_STORY",
            spoken_text="Khác nội dung nhưng trùng event id.",
            occurred_at=START_AT + timedelta(seconds=99),
            is_simulated=True,
        )
        with pytest.raises(ValueError, match="playback_event_id"):
            ShortTermPlayedHistory(window_size=5, initial_turns=[t1, t1_dup_event])

        t1_dup_turn = PlayedTurnSummary(
            playback_event_id="evt-999",
            turn_id=t1.turn_id,
            candidate_id="cand-999",
            intent="PRODUCT_STORY",
            spoken_text="Khác nội dung nhưng trùng turn id.",
            occurred_at=START_AT + timedelta(seconds=99),
            is_simulated=True,
        )
        with pytest.raises(ValueError, match="turn_id"):
            ShortTermPlayedHistory(window_size=5, initial_turns=[t1, t1_dup_turn])

        history = ShortTermPlayedHistory(
            window_size=5,
            tenant_id=TENANT_ID,
            session_id=SESSION_ID,
            session_epoch=1,
            initial_turns=[t1],
        )
        with pytest.raises(ValueError, match="playback_event_id"):
            history.append_confirmed_turn(t1_dup_event)
        with pytest.raises(ValueError, match="turn_id"):
            history.append_confirmed_turn(t1_dup_turn)

        # Lệch tenant, session hoặc epoch phải bị từ chối.
        t2 = _make_turn(2)
        with pytest.raises(ValueError, match="tenant_id"):
            history.append_confirmed_turn(t2, tenant_id="other-tenant")
        with pytest.raises(ValueError, match="session_id"):
            history.append_confirmed_turn(t2, session_id="other-session")
        with pytest.raises(ValueError, match="session_epoch"):
            history.append_confirmed_turn(t2, session_epoch=9)


# ---------------------------------------------------------------------------
# 2. GlobalTopicCoverage
# ---------------------------------------------------------------------------


class TestGlobalTopicCoverage:
    def test_separates_proposed_verified_from_completed_and_enforces_min_chunks(self) -> None:
        plan = _make_story_plan()
        coverage = GlobalTopicCoverage(plan, min_chunks_per_topic=2)

        # Proposed và Verified tuyệt đối không được làm topic thành completed.
        coverage.record_proposed_topics(["topic-01", "topic-02"])
        coverage.record_verified_topics(["topic-01"])
        assert coverage.proposed_topic_ids == frozenset({"topic-01", "topic-02"})
        assert coverage.verified_topic_ids == frozenset({"topic-01"})
        assert coverage.completed_topic_ids == frozenset()
        assert coverage.completed_mandatory_count == 0
        assert coverage.total_mandatory_count == 2
        assert coverage.mandatory_coverage_ratio == 0.0

        # Lượt phát 1 cho topic-01: count=1 < min_chunks_per_topic=2 -> chưa completed.
        ev1 = _make_playback_event(playback_event_id="evt-1", turn_id="turn-1", confirmed_topic_ids=["topic-01"])
        promoted_1 = coverage.record_playback_completed(ev1, plan_revision=1)
        assert promoted_1 == frozenset()
        assert coverage.played_chunk_counts_by_topic["topic-01"] == 1
        assert coverage.completed_topic_ids == frozenset()

        # Idempotent: lặp lại đúng evt-1 không được tăng bộ đếm lên 2.
        promoted_dup = coverage.record_playback_completed(ev1, plan_revision=1)
        assert promoted_dup == frozenset()
        assert coverage.played_chunk_counts_by_topic["topic-01"] == 1
        assert coverage.completed_topic_ids == frozenset()

        # Lượt phát 2 khác playback_event_id -> count=2 >= 2 -> thăng hạng topic-01.
        ev2 = _make_playback_event(
            playback_event_id="evt-2",
            turn_id="turn-2",
            confirmed_topic_ids=["topic-01"],
            offset_sec=20,
        )
        promoted_2 = coverage.record_playback_completed(ev2, plan_revision=1)
        assert promoted_2 == frozenset({"topic-01"})
        assert coverage.completed_topic_ids == frozenset({"topic-01"})
        assert coverage.remaining_mandatory_topic_ids == frozenset({"topic-02"})

        snap = coverage.snapshot()
        assert isinstance(snap, TopicCoverageSnapshot)
        assert snap.completed_mandatory_count == 1
        assert snap.total_mandatory_count == 2
        assert snap.mandatory_coverage_ratio == pytest.approx(0.5)

    def test_validates_bounds_and_rejects_mismatches_and_unknown_topics(self) -> None:
        plan = _make_story_plan()

        with pytest.raises(ValueError):
            GlobalTopicCoverage(plan, min_chunks_per_topic=True)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            GlobalTopicCoverage(plan, min_chunks_per_topic=0)
        with pytest.raises(ValueError):
            GlobalTopicCoverage(plan, initial_completed_topic_ids=["topic-unknown"])

        coverage = GlobalTopicCoverage(plan)
        with pytest.raises(ValueError):
            coverage.record_proposed_topics(["topic-unknown"])
        with pytest.raises(ValueError):
            coverage.record_verified_topics(["topic-unknown"])

        # Lệch tenant, session, plan_revision hoặc topic ngoài plan.
        with pytest.raises(ValueError, match="tenant_id"):
            coverage.record_playback_completed(
                _make_playback_event(tenant_id="other-tenant"),
                plan_revision=1,
            )
        with pytest.raises(ValueError, match="session_id"):
            coverage.record_playback_completed(
                _make_playback_event(session_id="other-session"),
                plan_revision=1,
            )
        with pytest.raises(ValueError, match="plan_revision"):
            coverage.record_playback_completed(_make_playback_event(), plan_revision=2)
        with pytest.raises(ValueError, match="StoryPlan"):
            coverage.record_playback_completed(
                _make_playback_event(confirmed_topic_ids=["topic-unknown"]),
                plan_revision=1,
            )

    def test_completed_topics_survive_short_term_history_window_slides(self) -> None:
        plan = _make_story_plan()
        history = ShortTermPlayedHistory(
            window_size=5,
            tenant_id=TENANT_ID,
            session_id=SESSION_ID,
            session_epoch=1,
        )
        coverage = GlobalTopicCoverage(plan)
        ev1 = _make_playback_event(
            playback_event_id="evt-01",
            turn_id="turn-01",
            chunk_id="chunk-01",
            confirmed_topic_ids=["topic-01"],
            offset_sec=10,
        )
        coverage.record_playback_completed(ev1, plan_revision=1)
        history.append_confirmed_turn(PlayedTurnSummary.from_playback_completed(ev1, intent="PRODUCT_STORY"))

        # Phát thêm 8 lượt khác khiến lượt đầu trượt khỏi cửa sổ W=5.
        for idx in range(2, 10):
            ev = _make_playback_event(
                playback_event_id=f"evt-{idx:02d}",
                turn_id=f"turn-{idx:02d}",
                chunk_id=f"chunk-{idx:02d}",
                confirmed_topic_ids=["topic-02"],
                offset_sec=idx * 10,
            )
            coverage.record_playback_completed(ev, plan_revision=1)
            history.append_confirmed_turn(PlayedTurnSummary.from_playback_completed(ev, intent="PRODUCT_STORY"))

        assert len(history.recent_turns()) == 5
        assert all(t.turn_id != "turn-01" for t in history.recent_turns())
        assert "topic-01" in coverage.completed_topic_ids
        assert coverage.mandatory_coverage_ratio == 1.0


# ---------------------------------------------------------------------------
# 3. SessionViewerContext & NoOpSemanticMemory
# ---------------------------------------------------------------------------


class TestViewerContextAndNoOpSemanticMemory:
    def test_viewer_context_empty_by_default_records_and_clears_without_pii(self) -> None:
        ctx = SessionViewerContext(tenant_id=TENANT_ID, session_id=SESSION_ID, session_epoch=1)
        assert ctx.is_empty is True
        assert ctx.questions == ()

        rec = ctx.record_question(
            "q-01",
            "Sản phẩm này có chứng nhận OCOP mấy sao ạ?",
            recorded_at=START_AT,
            topic_hint="topic-01",
        )
        assert isinstance(rec, ViewerQuestionRecord)
        assert ctx.is_empty is False
        assert len(ctx.questions) == 1

        # Không cho phép trường thừa / PII trên ViewerQuestionRecord.
        with pytest.raises(ValidationError):
            ViewerQuestionRecord(
                question_id="q-02",
                question_text="Giá bao nhiêu?",
                recorded_at=START_AT,
                user_id="viewer-pii-123",  # type: ignore[call-arg]
            )

        with pytest.raises(ValueError):
            ctx.record_question("q-01", "Trùng mã câu hỏi", recorded_at=START_AT)

        ctx.clear()
        assert ctx.is_empty is True
        assert ctx.questions == ()

        with pytest.raises(ValueError):
            SessionViewerContext(TENANT_ID, SESSION_ID, session_epoch=True)  # type: ignore[arg-type]

    def test_noop_semantic_memory_disabled_and_returns_empty(self) -> None:
        mem: OptionalSemanticMemory = NoOpSemanticMemory()
        assert mem.is_enabled is False
        mem.index_played_turn(_make_turn(1))
        assert mem.query_similar("Mật ong hoa cà phê", top_k=3) == ()
        mem.clear()

        with pytest.raises(ValueError):
            mem.query_similar("Mật ong", top_k=0)
        with pytest.raises(ValueError):
            mem.query_similar("Mật ong", top_k=True)  # type: ignore[arg-type]

        with pytest.raises(ValidationError):
            SemanticSimilarityMatch(
                turn_id="turn-1",
                similarity_score=True,  # type: ignore[arg-type]
                text_excerpt="Đoạn trích.",
            )


# ---------------------------------------------------------------------------
# 4. RepetitionDetector
# ---------------------------------------------------------------------------


class TestRepetitionDetector:
    def test_vietnamese_normalization_nfc_punctuation_and_short_text_safety(self) -> None:
        nfc_text = "Mật ong hoa cà phê, Đắk Lắk — 500ml!!!"
        nfd_text = unicodedata.normalize("NFD", "MẬT ONG HOA CÀ PHÊ... ĐẮK LẮK: 500ML?")

        assert normalize_vietnamese_for_repetition(nfc_text) == "mật ong hoa cà phê đắk lắk 500ml"
        assert (
            normalize_vietnamese_for_repetition(nfd_text)
            == normalize_vietnamese_for_repetition(nfc_text)
        )

        # Văn bản ngắn (< ngram_size=3) không gây ZeroDivisionError và không báo lặp giả.
        detector = RepetitionDetector()
        short_played = [_make_turn(1, chunk_id="c-1", spoken_text="Chào bạn")]
        res = detector.check("Xin chào", short_played, candidate_chunk_id="c-2")
        assert res.category == RepetitionCategory.NONE
        assert res.recommended_action == RepetitionAction.ALLOW
        assert res.is_repetitive is False

    def test_all_five_categories_and_statelessness(self) -> None:
        detector = RepetitionDetector()
        turn1 = _make_turn(
            1,
            chunk_id="chunk-01",
            topic_ids=["topic-01"],
            sku_refs=["SKU-HONEY-01"],
            covered_claim_ids=["claim-h-01", "claim-h-02"],
            intent="PRODUCT_STORY",
            spoken_text="Mật ong hoa cà phê Đắk Lắk nguyên chất chai 500ml giá 159.000đ thu hoạch tháng 3.",
        )

        # 1. NONE
        res_none = detector.check(
            "Trà Shan Tuyết cổ thụ Hà Giang hái búp non trên núi cao mang hương cốm dịu nhẹ.",
            [turn1],
            candidate_chunk_id="chunk-99",
            topic_id="topic-03",
            sku_id="SKU-TEA-01",
            intent="PRODUCT_STORY",
            candidate_claim_ids=["claim-t-01"],
        )
        assert res_none.category == RepetitionCategory.NONE
        assert res_none.recommended_action == RepetitionAction.ALLOW
        assert res_none.is_repetitive is False

        # 2a. EXACT_REPLAY qua played_chunk_ids ngoài cửa sổ -> SWITCH_TOPIC
        res_chunk_replay = detector.check(
            "Nội dung mới hoàn toàn nhưng trùng chunk_id đã phát ở lượt cũ.",
            [],
            candidate_chunk_id="chunk-old-00",
            played_chunk_ids={"chunk-old-00"},
        )
        assert res_chunk_replay.category == RepetitionCategory.EXACT_REPLAY
        assert res_chunk_replay.recommended_action == RepetitionAction.SWITCH_TOPIC
        assert res_chunk_replay.is_repetitive is True
        assert res_chunk_replay.matched_chunk_id == "chunk-old-00"

        # 2b. EXACT_REPLAY qua trùng văn bản chuẩn hóa (khác dấu câu/NFD) -> REWRITE
        nfd_same = unicodedata.normalize(
            "NFD",
            "MẬT ONG HOA CÀ PHÊ ĐẮK LẮK, NGUYÊN CHẤT CHAI 500ML GIÁ 159.000Đ THU HOẠCH THÁNG 3!",
        )
        res_text_replay = detector.check(nfd_same, [turn1], candidate_chunk_id="chunk-new")
        assert res_text_replay.category == RepetitionCategory.EXACT_REPLAY
        assert res_text_replay.recommended_action == RepetitionAction.REWRITE
        assert res_text_replay.is_repetitive is True
        assert res_text_replay.word_jaccard == pytest.approx(1.0)

        # 3. LEXICAL_DUPLICATION -> REWRITE
        near_dup = (
            "Chai mật ong hoa cà phê Đắk Lắk nguyên chất 500ml giá 159.000đ thu hoạch đúng tháng 3 nhé."
        )
        res_lexical = detector.check(near_dup, [turn1], candidate_chunk_id="chunk-new")
        assert res_lexical.category == RepetitionCategory.LEXICAL_DUPLICATION
        assert res_lexical.recommended_action == RepetitionAction.REWRITE
        assert res_lexical.is_repetitive is True
        assert res_lexical.word_jaccard >= detector.config.word_jaccard_threshold

        # 4a. REPEATED_FACTS cùng topic -> SWITCH_TOPIC
        paraphrase_same_facts = "Sản phẩm này lấy từ vùng đất bazan Tây Nguyên vào mùa xuân khô ráo."
        res_facts_same_topic = detector.check(
            paraphrase_same_facts,
            [turn1],
            candidate_chunk_id="chunk-new",
            topic_id="topic-01",
            sku_id="SKU-HONEY-01",
            intent="PRODUCT_STORY",
            candidate_claim_ids=["claim-h-01", "claim-h-02"],
        )
        assert res_facts_same_topic.category == RepetitionCategory.REPEATED_FACTS
        assert res_facts_same_topic.recommended_action == RepetitionAction.SWITCH_TOPIC
        assert res_facts_same_topic.is_repetitive is True
        assert res_facts_same_topic.fact_overlap_ratio == pytest.approx(1.0)

        # 4b. REPEATED_FACTS khác topic -> REWRITE
        res_facts_diff_topic = detector.check(
            paraphrase_same_facts,
            [turn1],
            candidate_chunk_id="chunk-new",
            topic_id="topic-02",
            sku_id="SKU-HONEY-01",
            intent="PRODUCT_STORY",
            candidate_claim_ids=["claim-h-01", "claim-h-02"],
        )
        assert res_facts_diff_topic.category == RepetitionCategory.REPEATED_FACTS
        assert res_facts_diff_topic.recommended_action == RepetitionAction.REWRITE
        assert res_facts_diff_topic.is_repetitive is True

        # 5. LEGITIMATE_CONTINUATION -> ALLOW
        continuation_text = "Quy trình lọc sáp khép kín giữ trọn vitamin và enzyme tự nhiên."
        res_cont = detector.check(
            continuation_text,
            [turn1],
            candidate_chunk_id="chunk-02",
            topic_id="topic-01",
            sku_id="SKU-HONEY-01",
            intent="PRODUCT_STORY",
            candidate_claim_ids=["claim-h-03"],
        )
        assert res_cont.category == RepetitionCategory.LEGITIMATE_CONTINUATION
        assert res_cont.recommended_action == RepetitionAction.ALLOW
        assert res_cont.is_repetitive is False
        assert res_cont.word_jaccard < detector.config.continuation_lexical_ceiling

        # Xác nhận tính thuần stateless: gọi lại với res_none cho kết quả y hệt.
        res_none_again = detector.check(
            "Trà Shan Tuyết cổ thụ Hà Giang hái búp non trên núi cao mang hương cốm dịu nhẹ.",
            [turn1],
            candidate_chunk_id="chunk-99",
            topic_id="topic-03",
            sku_id="SKU-TEA-01",
            intent="PRODUCT_STORY",
            candidate_claim_ids=["claim-t-01"],
        )
        assert res_none_again == res_none

    def test_repetition_config_rejects_bool_and_out_of_bounds(self) -> None:
        with pytest.raises(ValidationError):
            RepetitionConfig(word_jaccard_threshold=True)  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            RepetitionConfig(word_jaccard_threshold=0.0)
        with pytest.raises(ValidationError):
            RepetitionConfig(ngram_size=False)  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            RepetitionCheckResult(
                is_repetitive=False,
                category=RepetitionCategory.NONE,
                recommended_action=RepetitionAction.ALLOW,
                word_jaccard=1.2,
                ngram_jaccard=0.0,
                fact_overlap_ratio=0.0,
            )


# ---------------------------------------------------------------------------
# 5. SimulatedPlaybackHarness atomic integration & build_agent_state()
# ---------------------------------------------------------------------------


class _RecordingSemanticMemory(OptionalSemanticMemory):
    """Triển khai giả phục vụ kiểm tra harness chỉ index khi ACK COMPLETED."""

    def __init__(self) -> None:
        self.indexed_turn_ids: list[str] = []

    @property
    def is_enabled(self) -> bool:
        return True

    def index_played_turn(self, summary: PlayedTurnSummary) -> None:
        self.indexed_turn_ids.append(summary.turn_id)

    def query_similar(self, text: str, top_k: int = 3) -> tuple[SemanticSimilarityMatch, ...]:
        return ()

    def clear(self) -> None:
        self.indexed_turn_ids.clear()


class TestHarnessMemoryIntegration:
    def test_atomic_updates_on_completed_and_zero_mutation_on_non_completed_duplicate_stale(
        self,
    ) -> None:
        plan = _make_story_plan()
        checkpoint = _make_checkpoint()
        clock = VirtualClock(START_AT)
        bus = MockPlaybackAckBus(clock=clock, simulation_run_id=SIM_RUN_ID)
        history = ShortTermPlayedHistory(
            window_size=5,
            tenant_id=TENANT_ID,
            session_id=SESSION_ID,
            session_epoch=1,
        )
        coverage = GlobalTopicCoverage(plan)
        viewer = SessionViewerContext(TENANT_ID, SESSION_ID, 1)
        semantic = _RecordingSemanticMemory()

        harness = SimulatedPlaybackHarness(
            initial_checkpoint=checkpoint,
            expected_simulation_run_id=SIM_RUN_ID,
            story_plan=plan,
            played_history=history,
            topic_coverage=coverage,
            viewer_context=viewer,
            semantic_memory=semantic,
        )

        # Lượt 1: FAILED -> proposed/verified được ghi phi thẩm quyền, nhưng completed/history/semantic không đổi.
        cand1 = _make_verified_candidate(candidate_id="cand-1", source_chunk_id="chunk-1", topic_ids=["topic-01"])
        harness.register_pending_turn("turn-1", cand1, plan_revision=1, next_topic_id="topic-02")
        assert coverage.proposed_topic_ids == frozenset({"topic-01"})
        assert coverage.verified_topic_ids == frozenset({"topic-01"})
        assert coverage.completed_topic_ids == frozenset()

        ack_fail = bus.dispatch_turn(cand1, turn_id="turn-1", plan_revision=1, outcome_override=PlaybackOutcomeStatus.FAILED)
        res_fail = harness.apply_ack(ack_fail)
        assert res_fail.status == AckApplyStatus.IGNORED_NON_COMPLETED
        assert len(history.all_turns()) == 0
        assert coverage.completed_topic_ids == frozenset()
        assert semantic.indexed_turn_ids == []

        # Lượt 2: UNKNOWN -> giữ nguyên mọi bộ nhớ.
        cand2 = _make_verified_candidate(candidate_id="cand-2", source_chunk_id="chunk-2", topic_ids=["topic-01"])
        harness.register_pending_turn("turn-2", cand2, plan_revision=1, next_topic_id="topic-02")
        ack_unknown = bus.dispatch_turn(cand2, turn_id="turn-2", plan_revision=1, outcome_override=PlaybackOutcomeStatus.UNKNOWN)
        res_unknown = harness.apply_ack(ack_unknown)
        assert res_unknown.status == AckApplyStatus.IGNORED_NON_COMPLETED
        assert len(history.all_turns()) == 0
        assert coverage.completed_topic_ids == frozenset()
        assert semantic.indexed_turn_ids == []

        # Lượt 3: COMPLETED -> cập nhật nguyên tử đồng bộ mọi lớp bộ nhớ và checkpoint.
        cand3 = _make_verified_candidate(candidate_id="cand-3", source_chunk_id="chunk-3", topic_ids=["topic-01"])
        harness.register_pending_turn(
            "turn-3",
            cand3,
            plan_revision=1,
            next_topic_id="topic-02",
            covered_claim_ids=["claim-h-01"],
        )
        ack_ok = bus.dispatch_turn(cand3, turn_id="turn-3", plan_revision=1)
        res_ok = harness.apply_ack(ack_ok)
        assert res_ok.status == AckApplyStatus.APPLIED
        assert res_ok.applied is True
        assert harness.checkpoint.last_completed_chunk_id == "chunk-3"
        assert len(history.all_turns()) == 1
        assert history.has_chunk_been_played("chunk-3") is True
        assert coverage.completed_topic_ids == frozenset({"topic-01"})
        assert harness.completed_topic_ids == frozenset({"topic-01"})
        assert semantic.indexed_turn_ids == ["turn-3"]

        # Duplicate ACK của turn-3 -> bị chặn, không làm tăng count hay index lần 2.
        res_dup = harness.apply_ack(ack_ok)
        assert res_dup.status == AckApplyStatus.REJECTED_DUPLICATE
        assert len(history.all_turns()) == 1
        assert coverage.played_chunk_counts_by_topic["topic-01"] == 1
        assert semantic.indexed_turn_ids == ["turn-3"]

        # Stale epoch event -> bị chặn, giữ nguyên toàn bộ bộ nhớ.
        cand4 = _make_verified_candidate(candidate_id="cand-4", source_chunk_id="chunk-4", topic_ids=["topic-02"])
        harness.register_pending_turn("turn-4", cand4, plan_revision=1, next_topic_id=None)
        stale_event = _make_playback_event(
            playback_event_id="evt-stale",
            turn_id="turn-4",
            candidate_id="cand-4",
            chunk_id="chunk-4",
            confirmed_topic_ids=["topic-02"],
            session_epoch=99,
            offset_sec=50,
        )
        res_stale = harness.apply_playback_event(stale_event, intent=cand4.intent, plan_revision=1)
        assert res_stale.status == AckApplyStatus.REJECTED_STALE_OR_MISMATCH
        assert len(history.all_turns()) == 1
        assert coverage.completed_topic_ids == frozenset({"topic-01"})
        assert semantic.indexed_turn_ids == ["turn-3"]

        # Kiểm tra build_agent_state() đồng bộ với harness & ép bất biến I-04.
        state = harness.build_agent_state(plan)
        assert isinstance(state, AgentState)
        assert state.is_authoritative_session_state is False
        assert state.active_sku_id == "SKU-HONEY-01"
        assert state.played_history_window_size == 5
        assert len(state.played_history) == 1
        assert state.completed_topic_ids == frozenset({"topic-01"})

        with pytest.raises(ValueError, match="I-04"):
            harness.build_agent_state(plan, active_sku_id="SKU-TEA-01")

        wrong_rev_plan = _make_story_plan(plan_revision=2)
        with pytest.raises(ValueError, match="plan_revision"):
            harness.build_agent_state(wrong_rev_plan)

    def test_harness_rejects_mismatched_injected_memory_components(self) -> None:
        plan = _make_story_plan()
        checkpoint = _make_checkpoint()

        with pytest.raises(ValueError, match="tenant_id"):
            SimulatedPlaybackHarness(
                initial_checkpoint=checkpoint,
                expected_simulation_run_id=SIM_RUN_ID,
                played_history=ShortTermPlayedHistory(5, tenant_id="other-tenant"),
            )

        with pytest.raises(ValueError, match="topic_coverage"):
            SimulatedPlaybackHarness(
                initial_checkpoint=checkpoint,
                expected_simulation_run_id=SIM_RUN_ID,
                topic_coverage=GlobalTopicCoverage(_make_story_plan(plan_revision=9)),
            )

        with pytest.raises(ValueError, match="viewer_context"):
            SimulatedPlaybackHarness(
                initial_checkpoint=checkpoint,
                expected_simulation_run_id=SIM_RUN_ID,
                viewer_context=SessionViewerContext(TENANT_ID, SESSION_ID, session_epoch=9),
            )
