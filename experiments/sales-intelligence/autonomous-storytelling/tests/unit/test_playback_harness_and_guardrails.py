"""Kiểm thử đơn vị cho Guardrails (`ProhibitedEchoGuard`, `SafeFallbackSelector`) và hệ mô phỏng ACK (`VirtualClock`, `MockPlaybackAckBus`, `SimulatedPlaybackHarness`).

1. File này giải quyết vấn đề gì?
   Xác minh toàn bộ bộ bảo vệ chống lặp từ cấm, tái kiểm định fallback theo nguyên tắc fail-closed,
   tính tất định của đồng hồ ảo 10–30 phút và đủ 8 kịch bản bất biến ACK phát sóng (`I-03`, `I-06`).
2. Trách nhiệm chính của module là gì?
   Kiểm chứng `ProhibitedEchoGuard`, `SafeFallbackSelector`, `VirtualClock`, `MockPlaybackAckBus`,
   và `SimulatedPlaybackHarness` qua các ca tích cực, tiêu cực và biên nghiêm ngặt.
3. Module này liên kết với các thành phần nào?
   Kiểm thử trực tiếp `p06.guardrails`, `p06.simulation`, `p06.adapters.mocks`, `p06.adapters.interfaces`
   và hợp đồng `p06.schemas`.
4. Input và output chính là gì?
   Input là câu thoại mẫu, fallback candidates, trạng thái ACK (`COMPLETED`/`FAILED`/`UNKNOWN`)
   và các sự kiện `PlaybackCompleted` giả mạo/trùng/lệch ngữ cảnh;
   Output là kết quả xác nhận tất cả bất biến đạt chuẩn.
5. Có những constraints hoặc invariants quan trọng nào?
   - Generation/đăng ký chờ phát KHÔNG BAO GIỜ tự làm tiến `StoryCheckpoint` hay `completed_topic_ids`.
   - `FAILED`/`UNKNOWN` tuyệt đối không cho phép tự phát lặp (`auto_replay_permitted=False`).
   - Mọi sự kiện trùng, lệch `tenant_id`/`session_id`/`session_epoch`/`plan_revision`/`candidate_id`/`chunk_id`,
     sai thứ tự thời gian hay sai provenance đều bị từ chối nguyên trạng.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from p06.adapters import (
    AckApplyStatus,
    P05KnowledgeAdapter,
)
from p06.adapters.mocks import MockPlaybackAckBus
from p06.adapters.p05_knowledge_adapter import _load_p05_modules
from p06.guardrails import ProhibitedEchoGuard, SafeFallbackSelector
from p06.schemas import (
    CandidateOrigin,
    CandidateVerificationStatus,
    CoverageMode,
    PlaybackCompleted,
    PlaybackEventSource,
    PlaybackOutcomeStatus,
    ProposedResponseCoverage,
    SkuVersionBinding,
    SpeechCandidate,
    StoryCheckpoint,
)
from p06.schemas.candidate import TargetScopeMode
from p06.simulation import SimulatedPlaybackHarness, VirtualClock

P06_ROOT: Path = Path(__file__).resolve().parents[2]
E01_SEED_PATH: Path = P06_ROOT / "data" / "products" / "e01_verified_skus.json"
P05_DIR: Path = P06_ROOT.parent / "knowledge-verification"

TENANT_ID = "tenant-p06-poc-01"
SESSION_ID = "session-sim-01"
SIM_RUN_ID = "sim-run-e01-001"
START_AT = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)


def _make_checkpoint(
    *,
    plan_revision: int = 1,
    session_epoch: int = 1,
    next_topic_id: str | None = "topic-01",
) -> StoryCheckpoint:
    return StoryCheckpoint(
        tenant_id=TENANT_ID,
        session_id=SESSION_ID,
        session_epoch=session_epoch,
        plan_id="plan-e01-01",
        plan_revision=plan_revision,
        active_sku_id="SKU-HONEY-01",
        current_arc_id="arc-01",
        next_topic_id=next_topic_id,
        updated_at=START_AT,
    )


def _make_verified_candidate(
    *,
    candidate_id: str = "cand-01",
    origin: CandidateOrigin = CandidateOrigin.PROACTIVE_STORY,
    source_chunk_id: str | None = "chunk-01",
    topic_ids: list[str] | None = None,
    text: str = "Mật ong hoa cà phê Đắk Lắk nguyên chất chai 500ml giá 159.000đ.",
    session_epoch: int = 1,
    tenant_id: str = TENANT_ID,
    session_id: str = SESSION_ID,
) -> SpeechCandidate:
    draft = SpeechCandidate(
        candidate_id=candidate_id,
        tenant_id=tenant_id,
        session_id=session_id,
        session_epoch=session_epoch,
        origin=origin,
        source_chunk_id=source_chunk_id,
        scope_mode=TargetScopeMode.SINGLE_SKU,
        sku_refs=["SKU-HONEY-01"],
        sku_bindings=[
            SkuVersionBinding(
                sku_id="SKU-HONEY-01",
                knowledge_version=1,
                ocop_version=1,
                rights_version=1,
                cited_evidence_ids=["ev-e01-honey-shipping"],
                stated_price_vnd=159000,
            )
        ],
        session_rights_version=1,
        intent="product_story",
        text=text,
        estimated_duration_sec=7.0,
        proposed_coverage=ProposedResponseCoverage(
            covered_topic_ids=["topic-01"] if topic_ids is None else topic_ids,
            covered_intents=["product_story"],
            coverage_mode=CoverageMode.FULL,
        ),
    )
    return draft.mark_verified(f"p05-allow-{candidate_id}", START_AT)


class TestGuardrails:
    """Kiểm thử `ProhibitedEchoGuard` và `SafeFallbackSelector`."""

    def test_prohibited_echo_guard_catches_medical_echo_and_whitespace_obfuscation(self) -> None:
        guard = ProhibitedEchoGuard(
            extra_prohibited_phrases=("chữa khỏi", "chữa đau dạ dày", "thay thế thuốc")
        )
        clean = guard.check("Mật ong hoa cà phê pha nước ấm uống buổi sáng rất dịu nhẹ ạ.")
        assert clean.passed is True
        assert clean.matched_phrases == ()

        # Bẫy nhại câu hỏi y tế từ comment kèm nhiều dấu cách/xuống dòng
        echoed = guard.check(
            "Dạ mật ong bên em KHÔNG   CHỮA\nKHỎI đau dạ dày đâu ạ, đây chỉ là thực phẩm tự nhiên."
        )
        assert echoed.passed is False
        assert "chữa khỏi" in echoed.matched_phrases

        # Cụm từ cấm riêng của từng SKU
        sku_blocked = guard.check(
            "Sản phẩm giúp giảm mỡ máu cấp tốc cho người cao tuổi.",
            sku_prohibited_phrases=("giảm mỡ máu cấp tốc",),
        )
        assert sku_blocked.passed is False
        assert "giảm mỡ máu cấp tốc" in sku_blocked.matched_phrases

    def test_safe_fallback_selector_revalidates_live_and_fails_closed(self) -> None:
        p05_schemas, p05_gate = _load_p05_modules(P05_DIR)
        store = p05_gate.VersionedKnowledgeStore.from_seed_file(E01_SEED_PATH).clone()
        adapter = P05KnowledgeAdapter(store=store, p05_dir=P05_DIR)

        non_fallback = _make_verified_candidate(
            candidate_id="cand-story-not-fb",
            origin=CandidateOrigin.PROACTIVE_STORY,
            source_chunk_id="chunk-99",
        )
        # Fallback #1 cho HONEY (đã gắn VERIFIED trước đó để thử bẫy stale cache)
        fb_honey_stale_flag = SpeechCandidate(
            candidate_id="fb-honey-01",
            tenant_id=TENANT_ID,
            session_id=SESSION_ID,
            session_epoch=1,
            origin=CandidateOrigin.PREAPPROVED_FALLBACK,
            scope_mode=TargetScopeMode.SINGLE_SKU,
            sku_refs=["SKU-HONEY-01"],
            sku_bindings=[
                SkuVersionBinding(
                    sku_id="SKU-HONEY-01",
                    knowledge_version=1,
                    ocop_version=1,
                    rights_version=1,
                    cited_evidence_ids=["ev-e01-honey-origin"],
                )
            ],
            session_rights_version=1,
            intent="fallback_honey",
            text="Mật ong hoa cà phê Đắk Lắk thu hoạch tại Cư M'gar có hương thơm dịu đặc trưng ạ.",
            estimated_duration_sec=5.0,
            proposed_coverage=ProposedResponseCoverage(
                covered_intents=["fallback_honey"],
                coverage_mode=CoverageMode.FULL,
            ),
        ).mark_verified("old-stale-decision", START_AT)

        # Fallback #2 cho TEA
        fb_tea = SpeechCandidate(
            candidate_id="fb-tea-01",
            tenant_id=TENANT_ID,
            session_id=SESSION_ID,
            session_epoch=1,
            origin=CandidateOrigin.PREAPPROVED_FALLBACK,
            scope_mode=TargetScopeMode.SINGLE_SKU,
            sku_refs=["SKU-TEA-02"],
            sku_bindings=[
                SkuVersionBinding(
                    sku_id="SKU-TEA-02",
                    knowledge_version=1,
                    ocop_version=1,
                    rights_version=1,
                    cited_evidence_ids=["ev-e01-tea-origin"],
                )
            ],
            session_rights_version=1,
            intent="fallback_tea",
            text="Trà Shan Tuyết cổ thụ Hà Giang hái chuẩn 1 tôm 2 lá từ vùng cao Phìn Hồ ạ.",
            estimated_duration_sec=5.0,
            proposed_coverage=ProposedResponseCoverage(
                covered_intents=["fallback_tea"],
                coverage_mode=CoverageMode.FULL,
            ),
        )

        # Ban đầu HONEY hợp lệ -> chọn fb_honey_01 (bỏ qua non_fallback)
        selected_1 = SafeFallbackSelector.select_safe_fallback(
            adapter, [non_fallback, fb_honey_stale_flag, fb_tea], verified_at=START_AT
        )
        assert selected_1 is not None
        assert selected_1.candidate_id == "fb-honey-01"
        assert selected_1.verified_by_gate_decision_id == "p05-allow-fb-honey-01"

        # Thu hồi quyền HONEY -> dù fb_honey_stale_flag từng VERIFIED vẫn bị từ chối, chuyển sang fb_tea
        store.update_rights_status("SKU-HONEY-01", p05_schemas.RightsStatus.REVOKED)
        selected_2 = SafeFallbackSelector.select_safe_fallback(
            adapter, [fb_honey_stale_flag, fb_tea], verified_at=START_AT
        )
        assert selected_2 is not None
        assert selected_2.candidate_id == "fb-tea-01"
        assert selected_2.verification_status == CandidateVerificationStatus.VERIFIED

        # Hết hạn OCOP TEA -> tất cả fallback đều không hợp lệ -> fail-closed trả về None
        store.update_ocop_status("SKU-TEA-02", p05_schemas.OcopStatus.EXPIRED)
        selected_none = SafeFallbackSelector.select_safe_fallback(
            adapter, [fb_honey_stale_flag, fb_tea], verified_at=START_AT
        )
        assert selected_none is None


class TestVirtualClockAndMockPlaybackAckBus:
    """Kiểm thử `VirtualClock` và `MockPlaybackAckBus`."""

    def test_virtual_clock_deterministic_30_min_advance_without_sleep(self) -> None:
        clock = VirtualClock(START_AT)
        assert clock.now() == START_AT
        assert clock.elapsed_sec() == 0.0

        # Mô phỏng bước nhảy 30 phút = 1800 giây tức thì trên CPU
        clock.advance_sec(600)
        clock.advance_ms(1_200_000)
        assert clock.elapsed_sec() == pytest.approx(1800.0)
        assert clock.now() == START_AT + timedelta(minutes=30)

        dur_short = clock.estimate_speech_duration_ms("Xin chào.")
        dur_med = clock.estimate_speech_duration_ms(
            "Mật ong hoa cà phê Đắk Lắk nguyên chất chai thủy tinh 500ml giá niêm yết 159.000đ."
        )
        assert dur_short == 1000
        assert 1000 < dur_med <= 30000

        with pytest.raises(ValueError):
            clock.advance_ms(-1)
        with pytest.raises(ValueError):
            clock.advance_sec(True)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            VirtualClock(datetime(2026, 11, 26, 12, 0, 0))  # Naive datetime

    def test_mock_bus_rejects_non_verified_and_emits_simulated_provenance(self) -> None:
        clock = VirtualClock(START_AT)
        bus = MockPlaybackAckBus(clock=clock, simulation_run_id=SIM_RUN_ID)

        draft = SpeechCandidate(
            candidate_id="cand-draft",
            tenant_id=TENANT_ID,
            session_id=SESSION_ID,
            session_epoch=1,
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
                    cited_evidence_ids=["ev-e01-honey-origin"],
                )
            ],
            session_rights_version=1,
            intent="product_story",
            text="Bản nháp chưa kiểm chứng.",
            estimated_duration_sec=4.0,
            proposed_coverage=ProposedResponseCoverage(
                covered_topic_ids=["topic-01"],
                covered_intents=["product_story"],
                coverage_mode=CoverageMode.FULL,
            ),
        )
        with pytest.raises(ValueError):
            bus.dispatch_turn(draft, turn_id="turn-draft", plan_revision=1)

        rejected = draft.mark_rejected(["PRICE_MISMATCH"])
        with pytest.raises(ValueError):
            bus.dispatch_turn(rejected, turn_id="turn-rejected", plan_revision=1)

        verified = _make_verified_candidate(candidate_id="cand-ok")
        ack = bus.dispatch_turn(verified, turn_id="turn-01", plan_revision=1)
        assert ack.outcome == PlaybackOutcomeStatus.COMPLETED
        assert ack.auto_replay_permitted is False
        assert ack.event is not None
        assert ack.event.event_source == PlaybackEventSource.SIMULATED_HARNESS
        assert ack.event.is_simulated is True
        assert ack.event.simulation_run_id == SIM_RUN_ID
        assert ack.event.p04_evidence_ref is None
        assert clock.elapsed_sec() > 0


class TestSimulatedPlaybackHarnessEightScenarios:
    """Kiểm thử đầy đủ 8 kịch bản toàn vẹn ACK + bất biến không ACK thì không tiến."""

    def test_generation_without_ack_does_not_advance_progress(self) -> None:
        harness = SimulatedPlaybackHarness(
            initial_checkpoint=_make_checkpoint(),
            expected_simulation_run_id=SIM_RUN_ID,
        )
        cand = _make_verified_candidate(candidate_id="cand-01", source_chunk_id="chunk-01")
        harness.register_pending_turn(
            turn_id="turn-01",
            candidate=cand,
            plan_revision=1,
            next_topic_id="topic-02",
        )
        # Chưa nhận PlaybackCompleted -> checkpoint, coverage và played_history phải giữ nguyên
        assert harness.checkpoint.last_completed_chunk_id is None
        assert harness.checkpoint.last_playback_event_id is None
        assert harness.checkpoint.next_topic_id == "topic-01"
        assert harness.completed_topic_ids == frozenset()
        assert harness.played_history == ()
        assert harness.pending_turn_ids == frozenset({"turn-01"})

    def test_scenario_1_successful_playback_advances_checkpoint_and_coverage(self) -> None:
        clock = VirtualClock(START_AT)
        bus = MockPlaybackAckBus(clock=clock, simulation_run_id=SIM_RUN_ID)
        harness = SimulatedPlaybackHarness(
            initial_checkpoint=_make_checkpoint(),
            expected_simulation_run_id=SIM_RUN_ID,
        )
        cand = _make_verified_candidate(candidate_id="cand-01", source_chunk_id="chunk-01", topic_ids=["topic-01"])
        harness.register_pending_turn(
            turn_id="turn-01",
            candidate=cand,
            plan_revision=1,
            next_topic_id="topic-02",
        )
        ack = bus.dispatch_turn(cand, turn_id="turn-01", plan_revision=1)
        result = harness.apply_ack(ack)

        assert result.status == AckApplyStatus.APPLIED
        assert result.applied is True
        assert result.auto_replay_permitted is False
        assert result.checkpoint.last_completed_chunk_id == "chunk-01"
        assert result.checkpoint.last_playback_event_id == ack.event.playback_event_id  # type: ignore[union-attr]
        assert result.checkpoint.next_topic_id == "topic-02"
        assert result.completed_topic_ids == frozenset({"topic-01"})
        assert result.played_history_count == 1
        assert len(harness.played_history) == 1

    def test_scenario_2_and_3_failed_and_unknown_do_not_advance_or_allow_auto_replay(self) -> None:
        clock = VirtualClock(START_AT)
        bus = MockPlaybackAckBus(
            clock=clock,
            simulation_run_id=SIM_RUN_ID,
            scripted_outcomes={
                "turn-fail": PlaybackOutcomeStatus.FAILED,
                "turn-unk": PlaybackOutcomeStatus.UNKNOWN,
            },
        )
        harness = SimulatedPlaybackHarness(
            initial_checkpoint=_make_checkpoint(),
            expected_simulation_run_id=SIM_RUN_ID,
        )
        c_fail = _make_verified_candidate(candidate_id="cand-fail", source_chunk_id="chunk-fail", topic_ids=["topic-01"])
        c_unk = _make_verified_candidate(candidate_id="cand-unk", source_chunk_id="chunk-unk", topic_ids=["topic-02"])

        harness.register_pending_turn("turn-fail", c_fail, plan_revision=1, next_topic_id="topic-02")
        ack_fail = bus.dispatch_turn(c_fail, turn_id="turn-fail", plan_revision=1)
        res_fail = harness.apply_ack(ack_fail)
        assert res_fail.status == AckApplyStatus.IGNORED_NON_COMPLETED
        assert res_fail.applied is False
        assert res_fail.auto_replay_permitted is False
        assert res_fail.checkpoint.last_completed_chunk_id is None
        assert res_fail.completed_topic_ids == frozenset()
        assert res_fail.played_history_count == 0

        harness.register_pending_turn("turn-unk", c_unk, plan_revision=1, next_topic_id="topic-03")
        ack_unk = bus.dispatch_turn(c_unk, turn_id="turn-unk", plan_revision=1)
        res_unk = harness.apply_ack(ack_unk)
        assert res_unk.status == AckApplyStatus.IGNORED_NON_COMPLETED
        assert res_unk.applied is False
        assert res_unk.auto_replay_permitted is False
        assert res_unk.checkpoint.last_completed_chunk_id is None
        assert res_unk.completed_topic_ids == frozenset()
        assert res_unk.played_history_count == 0

    def test_scenario_4_duplicate_ack_rejected_idempotently(self) -> None:
        clock = VirtualClock(START_AT)
        bus = MockPlaybackAckBus(clock=clock, simulation_run_id=SIM_RUN_ID)
        harness = SimulatedPlaybackHarness(
            initial_checkpoint=_make_checkpoint(),
            expected_simulation_run_id=SIM_RUN_ID,
        )
        cand = _make_verified_candidate(candidate_id="cand-dup", source_chunk_id="chunk-01")
        harness.register_pending_turn("turn-dup", cand, plan_revision=1, next_topic_id="topic-02")
        ack = bus.dispatch_turn(cand, turn_id="turn-dup", plan_revision=1)

        first = harness.apply_ack(ack)
        assert first.status == AckApplyStatus.APPLIED

        # Lặp lại y hệt playback_event_id
        dup_same_event = harness.apply_ack(ack)
        assert dup_same_event.status == AckApplyStatus.REJECTED_DUPLICATE
        assert dup_same_event.applied is False
        assert dup_same_event.played_history_count == 1

        # Sự kiện mới khác ID nhưng trùng turn_id đã hoàn tất
        assert ack.event is not None
        payload = copy.deepcopy(ack.event.model_dump())
        payload["playback_event_id"] = "sim-pb-forged-dup-turn"
        dup_turn_event = PlaybackCompleted.model_validate(payload)
        dup_turn_res = harness.apply_playback_event(dup_turn_event, intent=cand.intent, plan_revision=1)
        assert dup_turn_res.status == AckApplyStatus.REJECTED_DUPLICATE
        assert dup_turn_res.applied is False

    def test_scenario_5_stale_ack_out_of_order_timestamp_rejected(self) -> None:
        clock = VirtualClock(START_AT)
        bus = MockPlaybackAckBus(clock=clock, simulation_run_id=SIM_RUN_ID)
        harness = SimulatedPlaybackHarness(
            initial_checkpoint=_make_checkpoint(),
            expected_simulation_run_id=SIM_RUN_ID,
        )
        c1 = _make_verified_candidate(candidate_id="cand-1", source_chunk_id="chunk-01", topic_ids=["topic-01"])
        c2 = _make_verified_candidate(candidate_id="cand-2", source_chunk_id="chunk-02", topic_ids=["topic-02"])

        harness.register_pending_turn("turn-1", c1, plan_revision=1, next_topic_id="topic-02")
        ack1 = bus.dispatch_turn(c1, turn_id="turn-1", plan_revision=1)
        assert harness.apply_ack(ack1).status == AckApplyStatus.APPLIED

        # Tạo sự kiện cho turn-2 có occurred_at nhỏ hơn turn-1 (ACK đến trễ/lùi thời gian)
        harness.register_pending_turn("turn-2", c2, plan_revision=1, next_topic_id="topic-03")
        stale_event = PlaybackCompleted(
            playback_event_id="sim-pb-stale-time",
            tenant_id=TENANT_ID,
            session_id=SESSION_ID,
            session_epoch=1,
            turn_id="turn-2",
            candidate_id="cand-2",
            chunk_id="chunk-02",
            sku_refs=["SKU-HONEY-01"],
            confirmed_topic_ids=["topic-02"],
            spoken_text=c2.text,
            actual_duration_ms=4000,
            occurred_at=START_AT,  # Nhỏ hơn ack1.event.occurred_at!
            event_source=PlaybackEventSource.SIMULATED_HARNESS,
            is_simulated=True,
            simulation_run_id=SIM_RUN_ID,
        )
        res = harness.apply_playback_event(stale_event, intent=c2.intent, plan_revision=1)
        assert res.status == AckApplyStatus.REJECTED_STALE_OR_MISMATCH
        assert res.applied is False
        assert res.checkpoint.last_completed_chunk_id == "chunk-01"

    def test_scenario_6_wrong_tenant_session_or_epoch_rejected(self) -> None:
        harness = SimulatedPlaybackHarness(
            initial_checkpoint=_make_checkpoint(session_epoch=2),
            expected_simulation_run_id=SIM_RUN_ID,
        )
        cand = _make_verified_candidate(candidate_id="cand-ctx", source_chunk_id="chunk-01", session_epoch=2)
        harness.register_pending_turn("turn-ctx", cand, plan_revision=1, next_topic_id="topic-02")

        base_kwargs = {
            "playback_event_id": "sim-pb-ctx",
            "tenant_id": TENANT_ID,
            "session_id": SESSION_ID,
            "session_epoch": 2,
            "turn_id": "turn-ctx",
            "candidate_id": "cand-ctx",
            "chunk_id": "chunk-01",
            "sku_refs": ["SKU-HONEY-01"],
            "confirmed_topic_ids": ["topic-01"],
            "spoken_text": cand.text,
            "actual_duration_ms": 5000,
            "occurred_at": START_AT + timedelta(seconds=5),
            "event_source": PlaybackEventSource.SIMULATED_HARNESS,
            "is_simulated": True,
            "simulation_run_id": SIM_RUN_ID,
        }

        for override_id, field, bad_val in (
            ("sim-pb-bad-tenant", "tenant_id", "wrong-tenant"),
            ("sim-pb-bad-session", "session_id", "wrong-session"),
            ("sim-pb-bad-epoch", "session_epoch", 1),
        ):
            bad_payload = dict(base_kwargs)
            bad_payload["playback_event_id"] = override_id
            bad_payload[field] = bad_val
            bad_event = PlaybackCompleted.model_validate(bad_payload)
            res = harness.apply_playback_event(bad_event, intent=cand.intent, plan_revision=1)
            assert res.status == AckApplyStatus.REJECTED_STALE_OR_MISMATCH
            assert res.applied is False

    def test_scenario_7_wrong_plan_revision_rejected(self) -> None:
        clock = VirtualClock(START_AT)
        bus = MockPlaybackAckBus(clock=clock, simulation_run_id=SIM_RUN_ID)
        harness = SimulatedPlaybackHarness(
            initial_checkpoint=_make_checkpoint(plan_revision=2),
            expected_simulation_run_id=SIM_RUN_ID,
        )
        cand = _make_verified_candidate(candidate_id="cand-rev", source_chunk_id="chunk-01")
        harness.register_pending_turn("turn-rev", cand, plan_revision=2, next_topic_id="topic-02")
        ack = bus.dispatch_turn(cand, turn_id="turn-rev", plan_revision=2)
        assert ack.event is not None
        assert ack.plan_revision == 2

        res = harness.apply_playback_event(ack.event, intent=cand.intent, plan_revision=1)
        assert res.status == AckApplyStatus.REJECTED_STALE_OR_MISMATCH
        assert res.applied is False
        assert res.checkpoint.last_completed_chunk_id is None

        # Lệch plan_revision ngay từ dispatch_turn -> apply_ack phải từ chối REJECTED_STALE_OR_MISMATCH
        ack_wrong_rev = bus.dispatch_turn(cand, turn_id="turn-rev", plan_revision=1)
        assert ack_wrong_rev.plan_revision == 1
        res_ack_wrong = harness.apply_ack(ack_wrong_rev)
        assert res_ack_wrong.status == AckApplyStatus.REJECTED_STALE_OR_MISMATCH
        assert res_ack_wrong.applied is False
        assert res_ack_wrong.checkpoint.last_completed_chunk_id is None

    def test_scenario_8_wrong_chunk_candidate_unregistered_and_bad_provenance_rejected(self) -> None:
        harness = SimulatedPlaybackHarness(
            initial_checkpoint=_make_checkpoint(),
            expected_simulation_run_id=SIM_RUN_ID,
        )
        cand = _make_verified_candidate(candidate_id="cand-8", source_chunk_id="chunk-08")
        harness.register_pending_turn("turn-8", cand, plan_revision=1, next_topic_id="topic-02")

        # Chưa đăng ký turn_id
        unregistered = PlaybackCompleted(
            playback_event_id="sim-pb-unreg",
            tenant_id=TENANT_ID,
            session_id=SESSION_ID,
            session_epoch=1,
            turn_id="turn-unknown",
            candidate_id="cand-8",
            chunk_id="chunk-08",
            sku_refs=["SKU-HONEY-01"],
            confirmed_topic_ids=["topic-01"],
            spoken_text=cand.text,
            actual_duration_ms=4000,
            occurred_at=START_AT + timedelta(seconds=4),
            event_source=PlaybackEventSource.SIMULATED_HARNESS,
            is_simulated=True,
            simulation_run_id=SIM_RUN_ID,
        )
        assert (
            harness.apply_playback_event(unregistered, intent=cand.intent, plan_revision=1).status
            == AckApplyStatus.REJECTED_STALE_OR_MISMATCH
        )

        # Sai candidate_id
        wrong_cand = unregistered.model_copy(
            update={"playback_event_id": "sim-pb-wrong-cand", "turn_id": "turn-8", "candidate_id": "cand-other"}
        )
        assert (
            harness.apply_playback_event(wrong_cand, intent=cand.intent, plan_revision=1).status
            == AckApplyStatus.REJECTED_STALE_OR_MISMATCH
        )

        # Sai chunk_id
        wrong_chunk = unregistered.model_copy(
            update={"playback_event_id": "sim-pb-wrong-chunk", "turn_id": "turn-8", "chunk_id": "chunk-other"}
        )
        assert (
            harness.apply_playback_event(wrong_chunk, intent=cand.intent, plan_revision=1).status
            == AckApplyStatus.REJECTED_STALE_OR_MISMATCH
        )

        # Sai simulation_run_id -> REJECTED_INVALID_PROVENANCE
        wrong_sim_run = unregistered.model_copy(
            update={
                "playback_event_id": "sim-pb-wrong-run",
                "turn_id": "turn-8",
                "simulation_run_id": "other-sim-run",
            }
        )
        assert (
            harness.apply_playback_event(wrong_sim_run, intent=cand.intent, plan_revision=1).status
            == AckApplyStatus.REJECTED_INVALID_PROVENANCE
        )

        # Gửi nhầm event P04 thật vào simulated harness -> REJECTED_INVALID_PROVENANCE
        p04_event = PlaybackCompleted(
            playback_event_id="p04-pb-real",
            tenant_id=TENANT_ID,
            session_id=SESSION_ID,
            session_epoch=1,
            turn_id="turn-8",
            candidate_id="cand-8",
            chunk_id="chunk-08",
            sku_refs=["SKU-HONEY-01"],
            confirmed_topic_ids=["topic-01"],
            spoken_text=cand.text,
            actual_duration_ms=4000,
            occurred_at=START_AT + timedelta(seconds=4),
            event_source=PlaybackEventSource.P04_MEDIA_CONTROLLER,
            is_simulated=False,
            p04_evidence_ref="p04-log-ref-01",
            simulation_run_id=None,
        )
        assert (
            harness.apply_playback_event(p04_event, intent=cand.intent, plan_revision=1).status
            == AckApplyStatus.REJECTED_INVALID_PROVENANCE
        )
