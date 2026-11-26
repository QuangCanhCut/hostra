"""Bộ kiểm thử đơn vị cho `SpeechCandidate`, `ProposedResponseCoverage`, `PlaybackCompleted` và `StoryCheckpoint`.

1. File này giải quyết vấn đề gì?
   Kiểm chứng các bất biến nghiêm ngặt về phạm vi SKU (`TargetScopeMode`), vòng đời kiểm chứng P05
   (`DRAFT` -> `VERIFIED`/`REJECTED`), độ phủ đề xuất không mang thẩm quyền (`is_authoritative=False`),
   và sự tách biệt giữa sự kiện mô phỏng với sự kiện phát sóng thật P04.
2. Trách nhiệm chính của module là gì?
   Chạy kiểm thử tích cực và tiêu cực (negative invariants) cho `p06.schemas.candidate` và
   `p06.schemas.events`, bao gồm `frozen=True`, helper chuyển trạng thái nguyên tử, kiểm định
   kiểu nghiêm ngặt (`StrictBool`/`StrictInt`/không nhận khoảng trắng) và JSON roundtrip.
3. Module này liên kết với các thành phần nào?
   Kiểm thử trực tiếp các lớp trong `p06.schemas.candidate` và `p06.schemas.events`.
4. Input và output chính là gì?
   Input là các mẫu ứng viên thuộc 4 `TargetScopeMode` và sự kiện phát sóng `PlaybackCompleted`;
   Output là kết quả xác nhận toàn bộ invariant vượt qua hoặc ném `ValidationError` đúng kỳ vọng.
5. Có những constraints hoặc invariants quan trọng nào?
   - `UNRESOLVED_SKU` tách biệt hoàn toàn khỏi `SHOP_WIDE_POLICY`.
   - Không có đường tắt biến `DRAFT` thành `VERIFIED` mà thiếu `verified_by_gate_decision_id` và `verified_at`.
   - Bất biến `I-06`: `StoryCheckpoint.last_completed_chunk_id` bắt buộc đi kèm `last_playback_event_id`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from p06.schemas import (
    CONTRACT_VERSION,
    CandidateOrigin,
    CandidateVerificationStatus,
    CoverageMode,
    PlaybackCompleted,
    PlaybackEventSource,
    PlaybackOutcomeStatus,
    ProposedResponseCoverage,
    ResumeMode,
    SkuVersionBinding,
    SpeechCandidate,
    StoryCheckpoint,
    TargetScopeMode,
    UnresolvedSkuReason,
)


def _make_binding(
    sku_id: str = "SKU-HONEY-01",
    cited_evidence_ids: list[str] | None = None,
    stated_price_vnd: int | None = None,
) -> SkuVersionBinding:
    """Tạo nhanh một `SkuVersionBinding` hợp lệ dùng cho kiểm thử ứng viên.

    Args:
        sku_id: Mã SKU.
        cited_evidence_ids: Danh sách `evidence_id` dẫn chứng.
        stated_price_vnd: Giá bán nhắc tới trong lời thoại (nếu có).

    Returns:
        SkuVersionBinding: Ràng buộc phiên bản tri thức/OCOP/quyền của SKU.
    """
    return SkuVersionBinding(
        sku_id=sku_id,
        product_version_id=f"pv-{sku_id}-1",
        knowledge_version=1,
        ocop_version=1,
        rights_version=1,
        cited_evidence_ids=["ev-honey-04"] if cited_evidence_ids is None else cited_evidence_ids,
        stated_price_vnd=stated_price_vnd,
        mentions_ocop=False,
    )


def _base_candidate_kwargs() -> dict[str, Any]:
    """Tạo bộ tham số cơ sở cho một `SpeechCandidate` phạm vi `SINGLE_SKU` ở trạng thái `DRAFT`.

    Returns:
        dict[str, Any]: Từ điển kwargs chuẩn để test dễ ghi đè từng trường.
    """
    return {
        "candidate_id": "cand-01",
        "turn_id": "turn-01",
        "tenant_id": "tenant-demo-01",
        "session_id": "session-demo-01",
        "session_epoch": 1,
        "origin": CandidateOrigin.PROACTIVE_STORY,
        "source_chunk_id": "chunk-01",
        "scope_mode": TargetScopeMode.SINGLE_SKU,
        "sku_refs": ["SKU-HONEY-01"],
        "sku_bindings": [_make_binding("SKU-HONEY-01")],
        "session_rights_version": 1,
        "intent": "product_story",
        "text": "Mật ong hoa cà phê Cư M'gar nguyên chất 500ml.",
        "estimated_duration_sec": 7.5,
        "proposed_coverage": ProposedResponseCoverage(
            covered_topic_ids=["arc-01-t1"],
            covered_intents=["product_story"],
            coverage_mode=CoverageMode.FULL,
        ),
    }


class TestProposedResponseCoverage:
    """Kiểm định `ProposedResponseCoverage` và quy tắc không mang thẩm quyền."""

    def test_is_authoritative_locked_to_false(self) -> None:
        """P06 chỉ đề xuất độ phủ (`is_authoritative` luôn phải là `False` thuần túy)."""
        cov = ProposedResponseCoverage(covered_intents=["ask_price"])
        assert cov.is_authoritative is False

        with pytest.raises(ValidationError):
            ProposedResponseCoverage(is_authoritative=True)  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            ProposedResponseCoverage(is_authoritative=0)  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            ProposedResponseCoverage(is_authoritative="false")  # type: ignore[arg-type]

    def test_coverage_modes_and_disjoint_intents(self) -> None:
        """Kiểm tra từng `CoverageMode` (`FULL`, `PARTIAL`, `CLARIFICATION_ONLY`, `ABSTAIN_NO_EVIDENCE`) và chống giao intent."""
        # Giao nhau giữa covered_intents và uncovered_intents
        with pytest.raises(ValidationError):
            ProposedResponseCoverage(
                covered_intents=["ask_price"],
                uncovered_intents=["ask_price"],
                coverage_mode=CoverageMode.PARTIAL,
            )

        # FULL nhưng lại có uncovered_intents
        with pytest.raises(ValidationError):
            ProposedResponseCoverage(
                covered_intents=["ask_price"],
                uncovered_intents=["ask_ship"],
                coverage_mode=CoverageMode.FULL,
            )

        # PARTIAL hợp lệ khi có cả covered và uncovered
        partial = ProposedResponseCoverage(
            covered_intents=["ask_price"],
            uncovered_intents=["ask_medical_effect"],
            coverage_mode=CoverageMode.PARTIAL,
        )
        assert partial.coverage_mode == CoverageMode.PARTIAL

        # PARTIAL nhưng rỗng uncovered_intents
        with pytest.raises(ValidationError):
            ProposedResponseCoverage(
                covered_intents=["ask_price"],
                uncovered_intents=[],
                coverage_mode=CoverageMode.PARTIAL,
            )

        # PARTIAL nhưng không có gì được covered
        with pytest.raises(ValidationError):
            ProposedResponseCoverage(
                covered_intents=[],
                covered_topic_ids=[],
                uncovered_intents=["ask_ship"],
                coverage_mode=CoverageMode.PARTIAL,
            )

        # CLARIFICATION_ONLY không được đánh dấu covered_topic_ids
        with pytest.raises(ValidationError):
            ProposedResponseCoverage(
                covered_topic_ids=["topic-01"],
                coverage_mode=CoverageMode.CLARIFICATION_ONLY,
            )

        # ABSTAIN_NO_EVIDENCE hợp lệ khi không đánh dấu phủ topic/intent nào
        abstain_ok = ProposedResponseCoverage(
            uncovered_intents=["ask_medical_effect"],
            coverage_mode=CoverageMode.ABSTAIN_NO_EVIDENCE,
        )
        assert abstain_ok.coverage_mode == CoverageMode.ABSTAIN_NO_EVIDENCE
        assert abstain_ok.is_authoritative is False

        # ABSTAIN_NO_EVIDENCE không được phép đánh dấu covered_topic_ids hoặc covered_intents
        with pytest.raises(ValidationError):
            ProposedResponseCoverage(
                covered_topic_ids=["topic-01"],
                uncovered_intents=["ask_medical_effect"],
                coverage_mode=CoverageMode.ABSTAIN_NO_EVIDENCE,
            )
        with pytest.raises(ValidationError):
            ProposedResponseCoverage(
                covered_intents=["ask_price"],
                uncovered_intents=["ask_medical_effect"],
                coverage_mode=CoverageMode.ABSTAIN_NO_EVIDENCE,
            )


class TestSpeechCandidateScopeAndLifecycle:
    """Kiểm định 4 `TargetScopeMode` và vòng đời `DRAFT` / `VERIFIED` / `REJECTED`."""

    def test_all_four_scope_modes_valid_and_json_roundtrip(self) -> None:
        """Kiểm tra cả 4 `TargetScopeMode` hợp lệ và tuần tự hóa JSON roundtrip."""
        single = SpeechCandidate(**_base_candidate_kwargs())
        assert single.contract_version == CONTRACT_VERSION
        assert single.is_ready_for_tts() is False
        assert SpeechCandidate.model_validate_json(single.model_dump_json()) == single

        multi_kwargs = _base_candidate_kwargs()
        multi_kwargs.update(
            {
                "origin": CandidateOrigin.COMMENT_REPLY,
                "source_chunk_id": None,
                "scope_mode": TargetScopeMode.MULTI_SKU_COMPARE,
                "sku_refs": ["SKU-HONEY-01", "SKU-TEA-02"],
                "sku_bindings": [
                    _make_binding("SKU-HONEY-01"),
                    _make_binding("SKU-TEA-02", cited_evidence_ids=["ev-tea-03"]),
                ],
                "intent": "compare_skus",
            }
        )
        multi = SpeechCandidate(**multi_kwargs)
        assert len(multi.sku_bindings) == 2

        shop_kwargs = _base_candidate_kwargs()
        shop_kwargs.update(
            {
                "origin": CandidateOrigin.COMMENT_REPLY,
                "source_chunk_id": None,
                "scope_mode": TargetScopeMode.SHOP_WIDE_POLICY,
                "sku_refs": [],
                "sku_bindings": [],
                "policy_version": 2,
                "policy_evidence_ids": ["ev-policy-ship-01"],
                "intent": "shipping_policy",
                "verification_status": CandidateVerificationStatus.VERIFIED,
                "verified_by_gate_decision_id": "gate-dec-01",
                "verified_at": datetime.now(timezone.utc),
            }
        )
        shop = SpeechCandidate(**shop_kwargs)
        assert shop.is_ready_for_tts() is True

        unresolved_kwargs = _base_candidate_kwargs()
        unresolved_kwargs.update(
            {
                "origin": CandidateOrigin.COMMENT_REPLY,
                "source_chunk_id": None,
                "scope_mode": TargetScopeMode.UNRESOLVED_SKU,
                "sku_refs": [],
                "sku_bindings": [],
                "unresolved_reason": UnresolvedSkuReason.AMBIGUOUS_SKU,
                "intent": "clarify_sku",
                "proposed_coverage": ProposedResponseCoverage(
                    covered_topic_ids=[],
                    covered_intents=["clarify_sku"],
                    coverage_mode=CoverageMode.CLARIFICATION_ONLY,
                ),
            }
        )
        unresolved = SpeechCandidate(**unresolved_kwargs)
        assert unresolved.unresolved_reason == UnresolvedSkuReason.AMBIGUOUS_SKU

    def test_single_and_multi_sku_scope_negative_cases(self) -> None:
        """Từ chối các trường hợp lệch `sku_refs` / `sku_bindings` hoặc lẫn trường của scope khác."""
        # SINGLE_SKU nhưng thiếu sku_bindings
        bad_single = _base_candidate_kwargs()
        bad_single["sku_bindings"] = []
        with pytest.raises(ValidationError):
            SpeechCandidate(**bad_single)

        # SINGLE_SKU nhưng sku_id lệch nhau
        bad_single_id = _base_candidate_kwargs()
        bad_single_id["sku_bindings"] = [_make_binding("SKU-TEA-02")]
        with pytest.raises(ValidationError):
            SpeechCandidate(**bad_single_id)

        # MULTI_SKU_COMPARE trùng SKU hoặc sai thứ tự binding
        bad_multi_dup = _base_candidate_kwargs()
        bad_multi_dup.update(
            {
                "scope_mode": TargetScopeMode.MULTI_SKU_COMPARE,
                "sku_refs": ["SKU-HONEY-01", "SKU-HONEY-01"],
                "sku_bindings": [_make_binding("SKU-HONEY-01"), _make_binding("SKU-HONEY-01")],
            }
        )
        with pytest.raises(ValidationError):
            SpeechCandidate(**bad_multi_dup)

        bad_multi_order = _base_candidate_kwargs()
        bad_multi_order.update(
            {
                "scope_mode": TargetScopeMode.MULTI_SKU_COMPARE,
                "sku_refs": ["SKU-HONEY-01", "SKU-TEA-02"],
                "sku_bindings": [_make_binding("SKU-TEA-02"), _make_binding("SKU-HONEY-01")],
            }
        )
        with pytest.raises(ValidationError):
            SpeechCandidate(**bad_multi_order)

    def test_shop_wide_policy_vs_unresolved_sku_strict_separation(self) -> None:
        """P06-OPEN-5: tách biệt nghiêm ngặt `UNRESOLVED_SKU` khỏi `SHOP_WIDE_POLICY`."""
        # SHOP_WIDE_POLICY thiếu policy_version hoặc dùng CLARIFICATION_ONLY
        bad_shop = _base_candidate_kwargs()
        bad_shop.update(
            {
                "origin": CandidateOrigin.COMMENT_REPLY,
                "source_chunk_id": None,
                "scope_mode": TargetScopeMode.SHOP_WIDE_POLICY,
                "sku_refs": [],
                "sku_bindings": [],
                "policy_version": None,
            }
        )
        with pytest.raises(ValidationError):
            SpeechCandidate(**bad_shop)

        # SHOP_WIDE_POLICY VERIFIED thiếu policy_evidence_ids
        bad_shop_verified = _base_candidate_kwargs()
        bad_shop_verified.update(
            {
                "origin": CandidateOrigin.COMMENT_REPLY,
                "source_chunk_id": None,
                "scope_mode": TargetScopeMode.SHOP_WIDE_POLICY,
                "sku_refs": [],
                "sku_bindings": [],
                "policy_version": 1,
                "policy_evidence_ids": [],
                "verification_status": CandidateVerificationStatus.VERIFIED,
                "verified_by_gate_decision_id": "gate-1",
                "verified_at": datetime.now(timezone.utc),
            }
        )
        with pytest.raises(ValidationError):
            SpeechCandidate(**bad_shop_verified)

        # UNRESOLVED_SKU nhưng mang policy_version hoặc FULL coverage_mode
        bad_unresolved = _base_candidate_kwargs()
        bad_unresolved.update(
            {
                "origin": CandidateOrigin.COMMENT_REPLY,
                "source_chunk_id": None,
                "scope_mode": TargetScopeMode.UNRESOLVED_SKU,
                "sku_refs": [],
                "sku_bindings": [],
                "unresolved_reason": UnresolvedSkuReason.MISSING_CONTEXT,
                "policy_version": 1,
                "proposed_coverage": ProposedResponseCoverage(
                    covered_topic_ids=[],
                    coverage_mode=CoverageMode.CLARIFICATION_ONLY,
                ),
            }
        )
        with pytest.raises(ValidationError):
            SpeechCandidate(**bad_unresolved)

    def test_verification_lifecycle_and_proactive_source_guards(self) -> None:
        """Kiểm tra tách biệt `DRAFT`/`VERIFIED`/`REJECTED`, chặn tự phong `VERIFIED` và `PROACTIVE_STORY`."""
        # PROACTIVE_STORY thiếu source_chunk_id
        no_chunk = _base_candidate_kwargs()
        no_chunk["source_chunk_id"] = None
        with pytest.raises(ValidationError):
            SpeechCandidate(**no_chunk)

        # DRAFT mang sẵn gate decision -> từ chối
        draft_with_gate = _base_candidate_kwargs()
        draft_with_gate["verified_by_gate_decision_id"] = "fake-gate"
        with pytest.raises(ValidationError):
            SpeechCandidate(**draft_with_gate)

        # VERIFIED thiếu evidence và thiếu giá cho SINGLE_SKU -> từ chối
        verified_no_ev = _base_candidate_kwargs()
        verified_no_ev.update(
            {
                "sku_bindings": [_make_binding("SKU-HONEY-01", cited_evidence_ids=[], stated_price_vnd=None)],
                "verification_status": CandidateVerificationStatus.VERIFIED,
                "verified_by_gate_decision_id": "gate-ok",
                "verified_at": datetime.now(timezone.utc),
            }
        )
        with pytest.raises(ValidationError):
            SpeechCandidate(**verified_no_ev)

        # VERIFIED hợp lệ khi báo giá chuẩn từ ProductFact (không cần cited_evidence_ids)
        verified_price_only = _base_candidate_kwargs()
        verified_price_only.update(
            {
                "sku_bindings": [_make_binding("SKU-HONEY-01", cited_evidence_ids=[], stated_price_vnd=159000)],
                "verification_status": CandidateVerificationStatus.VERIFIED,
                "verified_by_gate_decision_id": "gate-ok-price",
                "verified_at": datetime.now(timezone.utc),
            }
        )
        cand_ok = SpeechCandidate(**verified_price_only)
        assert cand_ok.is_ready_for_tts() is True

        # REJECTED bắt buộc có rejection_reasons và không có gate_decision_id
        rejected_bad = _base_candidate_kwargs()
        rejected_bad.update(
            {
                "verification_status": CandidateVerificationStatus.REJECTED,
                "rejection_reasons": [],
            }
        )
        with pytest.raises(ValidationError):
            SpeechCandidate(**rejected_bad)

        # frozen=True: không cho gán trực tiếp DRAFT -> VERIFIED và giữ nguyên hoàn toàn bản gốc.
        draft_cand = SpeechCandidate(**_base_candidate_kwargs())
        with pytest.raises(ValidationError):
            draft_cand.verification_status = CandidateVerificationStatus.VERIFIED  # type: ignore[misc]
        assert draft_cand.verification_status == CandidateVerificationStatus.DRAFT
        assert draft_cand.is_ready_for_tts() is False

        # Helper mark_verified / mark_rejected nguyên tử: lỗi phải giữ nguyên đối tượng gốc.
        verified_at = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            draft_cand.mark_verified(gate_decision_id="   ", verified_at=verified_at)
        assert draft_cand.verification_status == CandidateVerificationStatus.DRAFT
        assert draft_cand.is_ready_for_tts() is False

        verified_cand = draft_cand.mark_verified(
            gate_decision_id="gate-allow-01",
            verified_at=verified_at,
        )
        assert verified_cand.is_ready_for_tts() is True
        assert verified_cand.verified_by_gate_decision_id == "gate-allow-01"
        assert draft_cand.is_ready_for_tts() is False

        with pytest.raises(ValidationError):
            draft_cand.mark_rejected(reasons=["   "])
        assert draft_cand.verification_status == CandidateVerificationStatus.DRAFT

        rejected_cand = verified_cand.mark_rejected(
            reasons=["PRICE_MISMATCH"],
            increment_rewrite=True,
        )
        assert rejected_cand.verification_status == CandidateVerificationStatus.REJECTED
        assert rejected_cand.verified_by_gate_decision_id is None
        assert rejected_cand.verified_at is None
        assert rejected_cand.rewrite_attempt == 1
        assert verified_cand.is_ready_for_tts() is True

        # Text rỗng, trường tùy chọn chỉ khoảng trắng và list items rỗng bị chặn.
        blank_text = _base_candidate_kwargs()
        blank_text["text"] = "   "
        with pytest.raises(ValidationError):
            SpeechCandidate(**blank_text)

        blank_turn = _base_candidate_kwargs()
        blank_turn["turn_id"] = "   "
        with pytest.raises(ValidationError):
            SpeechCandidate(**blank_turn)

        blank_list = _base_candidate_kwargs()
        blank_list["rejection_reasons"] = ["   "]
        with pytest.raises(ValidationError):
            SpeechCandidate(**blank_list)

    def test_strict_types_rejected_on_binding_and_candidate(self) -> None:
        """A-MAJ-01 & A-MAJ-02: từ chối bool trong int/float và str/int trong bool."""
        with pytest.raises(ValidationError):
            SkuVersionBinding(
                sku_id="SKU-HONEY-01",
                knowledge_version=True,  # type: ignore[arg-type]
                ocop_version=1,
                rights_version=1,
            )
        with pytest.raises(ValidationError):
            SkuVersionBinding(
                sku_id="SKU-HONEY-01",
                knowledge_version=1,
                ocop_version=1,
                rights_version=1,
                stated_price_vnd=True,  # type: ignore[arg-type]
            )
        with pytest.raises(ValidationError):
            SkuVersionBinding(
                sku_id="SKU-HONEY-01",
                knowledge_version=1,
                ocop_version=1,
                rights_version=1,
                mentions_ocop="false",  # type: ignore[arg-type]
            )
        with pytest.raises(ValidationError):
            SkuVersionBinding(
                sku_id="SKU-HONEY-01",
                product_version_id="   ",
                knowledge_version=1,
                ocop_version=1,
                rights_version=1,
                cited_evidence_ids=["   "],
            )

        bad_dur = _base_candidate_kwargs()
        bad_dur["estimated_duration_sec"] = True
        with pytest.raises(ValidationError):
            SpeechCandidate(**bad_dur)

        bad_epoch = _base_candidate_kwargs()
        bad_epoch["session_epoch"] = True
        with pytest.raises(ValidationError):
            SpeechCandidate(**bad_epoch)

        bad_bool = _base_candidate_kwargs()
        bad_bool["semantic_breakpoint"] = "true"
        with pytest.raises(ValidationError):
            SpeechCandidate(**bad_bool)


class TestEventsAndCheckpoint:
    """Kiểm định `PlaybackCompleted`, `PlaybackOutcomeStatus` và `StoryCheckpoint` (Bất biến I-06)."""

    def test_playback_completed_simulated_vs_real_provenance_and_strict_types(self) -> None:
        """Tách biệt `SIMULATED_HARNESS` với `P04_MEDIA_CONTROLLER`, kiểm định `playout_generation` và strict types."""
        assert {s.value for s in PlaybackOutcomeStatus} == {"COMPLETED", "FAILED", "UNKNOWN"}

        sim_event = PlaybackCompleted(
            playback_event_id="pb-sim-01",
            tenant_id="tenant-demo-01",
            session_id="session-demo-01",
            session_epoch=1,
            turn_id="turn-01",
            candidate_id="cand-01",
            chunk_id="chunk-01",
            playout_generation=2,
            sku_refs=["SKU-HONEY-01"],
            confirmed_topic_ids=["arc-01-t1"],
            spoken_text="   Mật ong hoa cà phê Cư M'gar giá 159.000đ. ",
            actual_duration_ms=4200,
            occurred_at=datetime.now(timezone.utc),
            event_source=PlaybackEventSource.SIMULATED_HARNESS,
            is_simulated=True,
            simulation_run_id="run-e01-001",
        )
        assert sim_event.spoken_text == "Mật ong hoa cà phê Cư M'gar giá 159.000đ."
        assert sim_event.playout_generation == 2
        assert PlaybackCompleted.model_validate_json(sim_event.model_dump_json()) == sim_event

        real_event = PlaybackCompleted(
            playback_event_id="pb-real-01",
            tenant_id="tenant-demo-01",
            session_id="session-demo-01",
            session_epoch=1,
            turn_id="turn-02",
            candidate_id="cand-02",
            spoken_text="Chai 500ml bảo quản nơi khô ráo.",
            actual_duration_ms=3100,
            occurred_at=datetime.now(timezone.utc),
            event_source=PlaybackEventSource.P04_MEDIA_CONTROLLER,
            is_simulated=False,
            p04_evidence_ref="p04://livekit/room-1/seg-2",
        )
        assert real_event.is_simulated is False

        # Cấm SIMULATED_HARNESS gắn is_simulated=False hoặc chèn p04_evidence_ref
        with pytest.raises(ValidationError):
            PlaybackCompleted(
                playback_event_id="pb-bad-1",
                tenant_id="tenant-demo-01",
                session_id="session-demo-01",
                session_epoch=1,
                turn_id="turn-01",
                candidate_id="cand-01",
                spoken_text="Hợp lệ",
                actual_duration_ms=1000,
                occurred_at=datetime.now(timezone.utc),
                event_source=PlaybackEventSource.SIMULATED_HARNESS,
                is_simulated=False,
                simulation_run_id="run-1",
            )

        with pytest.raises(ValidationError):
            PlaybackCompleted(
                playback_event_id="pb-bad-2",
                tenant_id="tenant-demo-01",
                session_id="session-demo-01",
                session_epoch=1,
                turn_id="turn-01",
                candidate_id="cand-01",
                spoken_text="Hợp lệ",
                actual_duration_ms=1000,
                occurred_at=datetime.now(timezone.utc),
                event_source=PlaybackEventSource.P04_MEDIA_CONTROLLER,
                is_simulated=False,
                p04_evidence_ref="p04://ok",
                simulation_run_id="should-not-exist",
            )

        # Từ chối ép kiểu is_simulated="false"/0, playout_generation=0/True, actual_duration_ms=True
        for bad_sim in ("false", 0, "0"):
            with pytest.raises(ValidationError):
                PlaybackCompleted(
                    playback_event_id="pb-bad-bool",
                    tenant_id="tenant-demo-01",
                    session_id="session-demo-01",
                    session_epoch=1,
                    turn_id="turn-01",
                    candidate_id="cand-01",
                    spoken_text="Hợp lệ",
                    actual_duration_ms=1000,
                    occurred_at=datetime.now(timezone.utc),
                    event_source=PlaybackEventSource.P04_MEDIA_CONTROLLER,
                    is_simulated=bad_sim,  # type: ignore[arg-type]
                    p04_evidence_ref="p04://ok",
                )

        with pytest.raises(ValidationError):
            PlaybackCompleted(
                playback_event_id="pb-bad-gen",
                tenant_id="tenant-demo-01",
                session_id="session-demo-01",
                session_epoch=1,
                turn_id="turn-01",
                candidate_id="cand-01",
                playout_generation=True,  # type: ignore[arg-type]
                spoken_text="Hợp lệ",
                actual_duration_ms=1000,
                occurred_at=datetime.now(timezone.utc),
                event_source=PlaybackEventSource.P04_MEDIA_CONTROLLER,
                is_simulated=False,
                p04_evidence_ref="p04://ok",
            )

    def test_story_checkpoint_invariant_i06_and_advance_on_playback(self) -> None:
        """I-06: `last_completed_chunk_id` phải đi kèm `last_playback_event_id` và tịnh tiến qua `advance_on_playback`."""
        initial_cp = StoryCheckpoint(
            tenant_id="tenant-demo-01",
            session_id="session-demo-01",
            session_epoch=1,
            plan_id="plan-demo-01",
            plan_revision=1,
            active_sku_id="SKU-HONEY-01",
            current_arc_id="arc-01",
            next_topic_id="arc-01-t1",
        )
        assert initial_cp.resume_mode == ResumeMode.EXACT

        completed_cp = StoryCheckpoint(
            tenant_id="tenant-demo-01",
            session_id="session-demo-01",
            session_epoch=1,
            plan_id="plan-demo-01",
            plan_revision=1,
            active_sku_id="SKU-HONEY-01",
            current_arc_id="arc-01",
            next_topic_id="arc-01-t2",
            last_completed_chunk_id="chunk-01",
            last_playback_event_id="pb-sim-01",
            resume_mode=ResumeMode.CONTEXTUAL_BRIDGE,
        )
        assert StoryCheckpoint.model_validate_json(completed_cp.model_dump_json()) == completed_cp

        # Chặn gán trực tiếp nhờ frozen=True
        with pytest.raises(ValidationError):
            initial_cp.last_completed_chunk_id = "chunk-01"  # type: ignore[misc]
        assert initial_cp.last_completed_chunk_id is None

        # advance_on_playback hợp lệ tạo checkpoint mới, giữ nguyên initial_cp
        occurred = datetime(2026, 11, 26, 9, 15, tzinfo=timezone.utc)
        valid_event = PlaybackCompleted(
            playback_event_id="pb-adv-01",
            tenant_id="tenant-demo-01",
            session_id="session-demo-01",
            session_epoch=1,
            turn_id="turn-01",
            candidate_id="cand-01",
            chunk_id="chunk-01",
            spoken_text="Đã phát xong đoạn mở đầu.",
            actual_duration_ms=2500,
            occurred_at=occurred,
            event_source=PlaybackEventSource.SIMULATED_HARNESS,
            is_simulated=True,
            simulation_run_id="run-e03",
        )
        advanced_cp = initial_cp.advance_on_playback(
            event=valid_event,
            next_topic_id="arc-01-t2",
            resume_mode=ResumeMode.CONTEXTUAL_BRIDGE,
        )
        assert advanced_cp.last_completed_chunk_id == "chunk-01"
        assert advanced_cp.last_playback_event_id == "pb-adv-01"
        assert advanced_cp.next_topic_id == "arc-01-t2"
        assert advanced_cp.resume_mode == ResumeMode.CONTEXTUAL_BRIDGE
        assert advanced_cp.updated_at == occurred
        assert initial_cp.last_completed_chunk_id is None

        # Lượt phát không gắn chunk_id (vd COMMENT_REPLY / RESUME_BRIDGE) phải bảo toàn checkpoint StoryChunk trước đó.
        reply_occurred = datetime(2026, 11, 26, 9, 16, tzinfo=timezone.utc)
        comment_reply_event = PlaybackCompleted(
            playback_event_id="pb-reply-01",
            tenant_id="tenant-demo-01",
            session_id="session-demo-01",
            session_epoch=1,
            turn_id="turn-02",
            candidate_id="cand-reply-01",
            chunk_id=None,
            spoken_text="Dạ chai này dung tích 500ml giá 159.000đ ạ.",
            actual_duration_ms=2200,
            occurred_at=reply_occurred,
            event_source=PlaybackEventSource.SIMULATED_HARNESS,
            is_simulated=True,
            simulation_run_id="run-e03",
        )
        after_reply_cp = advanced_cp.advance_on_playback(
            event=comment_reply_event,
            next_topic_id="arc-01-t2",
            current_arc_id="arc-01",
            resume_mode=ResumeMode.CONTEXTUAL_BRIDGE,
        )
        assert after_reply_cp.last_completed_chunk_id == "chunk-01"
        assert after_reply_cp.last_playback_event_id == "pb-adv-01"
        assert after_reply_cp.updated_at == reply_occurred
        assert after_reply_cp.next_topic_id == "arc-01-t2"
        assert after_reply_cp.resume_mode == ResumeMode.CONTEXTUAL_BRIDGE

        # Lệch tenant/session/epoch bị từ chối khi advance_on_playback
        wrong_tenant_event = PlaybackCompleted(
            **{**valid_event.model_dump(), "tenant_id": "tenant-other"}
        )
        with pytest.raises(ValueError):
            initial_cp.advance_on_playback(event=wrong_tenant_event, next_topic_id="arc-01-t2")

        wrong_epoch_event = PlaybackCompleted(
            **{**valid_event.model_dump(), "session_epoch": 2}
        )
        with pytest.raises(ValueError):
            initial_cp.advance_on_playback(event=wrong_epoch_event, next_topic_id="arc-01-t2")

        with pytest.raises(ValidationError):
            initial_cp.advance_on_playback(event=valid_event, next_topic_id="   ")

        with pytest.raises(ValidationError):
            StoryCheckpoint(
                tenant_id="tenant-demo-01",
                session_id="session-demo-01",
                session_epoch=1,
                plan_id="plan-demo-01",
                plan_revision=1,
                active_sku_id="SKU-HONEY-01",
                current_arc_id="arc-01",
                last_completed_chunk_id="chunk-01",
                last_playback_event_id=None,
            )

        with pytest.raises(ValidationError):
            StoryCheckpoint(
                tenant_id="tenant-demo-01",
                session_id="session-demo-01",
                session_epoch=1,
                plan_id="plan-demo-01",
                plan_revision=1,
                active_sku_id="SKU-HONEY-01",
                current_arc_id="arc-01",
                last_completed_chunk_id="chunk-01",
                last_playback_event_id="   ",
            )
