"""Kiểm thử hợp đồng đối chiếu trực tiếp giữa schema P06 và Cổng phát ngôn P05 (`knowledge-verification`).

1. File này giải quyết vấn đề gì?
   Xác minh bằng chứng thực thi rằng `p06.schemas.SpeechCandidate` (giai đoạn `p06-mock-v0.1`)
   ánh xạ đầy đủ trường dữ liệu sang P05 `SpeechCandidate`, nhận phán quyết `PublicationDecision`
   từ `PublicationGate.evaluate()` và cập nhật vòng đời `VERIFIED`/`REJECTED` chính xác.
2. Trách nhiệm chính của module là gì?
   Nạp chỉ-đọc `schemas.py`, `publication_gate.py` và `data/catalog_seed.json` từ module P05,
   chạy kiểm định thực tế trên 2 SKU mẫu (`SKU-HONEY-01` -> `ALLOW`, `SKU-CASHEW-03` -> `BLOCK`
   vì `OCOP_NOT_VERIFIED`) và kiểm tra chống TOCTOU khi giá sản phẩm tăng phiên bản.
3. Module này liên kết với các thành phần nào?
   Đọc chỉ-đọc từ `experiments/sales-intelligence/knowledge-verification/` và kiểm thử tương thích
   với `p06.schemas.candidate`.
4. Input và output chính là gì?
   Input là `SpeechCandidate` của P06 (ở trạng thái `DRAFT`) và `VersionedKnowledgeStore` nạp từ
   `catalog_seed.json`; Output là P05 `PublicationDecision` được chuyển đổi ngược sang P06 `SpeechCandidate`.
5. Có những constraints hoặc invariants quan trọng nào?
   - Chỉ đọc P05, tuyệt đối không chỉnh sửa tệp trong `knowledge-verification/`.
   - Cô lập việc nạp module `schemas` của P05 bằng `importlib.util` và khôi phục `sys.modules` ngay
     để không xung đột tên với `p06.schemas`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

from p06.adapters.p05_knowledge_adapter import _load_p05_modules
from p06.schemas import (
    CandidateOrigin,
    CandidateVerificationStatus,
    CoverageMode,
    ProposedResponseCoverage,
    SkuVersionBinding,
    SpeechCandidate as P06SpeechCandidate,
    TargetScopeMode,
)

# Đường dẫn tương đối ổn định từ `tests/contract/test_p05_contract_alignment.py` sang P05.
P05_DIR: Path = Path(__file__).resolve().parents[3] / "knowledge-verification"
P05_SEED_PATH: Path = P05_DIR / "data" / "catalog_seed.json"


def _to_p05_candidate(p06_candidate: P06SpeechCandidate, p05_schemas: ModuleType) -> Any:
    """Ánh xạ một `P06SpeechCandidate` (chế độ `SINGLE_SKU`) sang DTO `SpeechCandidate` của P05.

    Args:
        p06_candidate: Ứng viên lời thoại do P06 tạo ở trạng thái `DRAFT`.
        p05_schemas: Module `schemas` đã nạp từ P05.

    Returns:
        Any: Thể hiện `p05_schemas.SpeechCandidate` tương ứng.
    """
    binding = p06_candidate.sku_bindings[0]
    return p05_schemas.SpeechCandidate(
        candidate_id=p06_candidate.candidate_id,
        tenant_id=p06_candidate.tenant_id,
        session_id=p06_candidate.session_id,
        sku_id=binding.sku_id,
        text=p06_candidate.text,
        cited_evidence_ids=list(binding.cited_evidence_ids),
        stated_price_vnd=binding.stated_price_vnd,
        mentions_ocop=binding.mentions_ocop,
        knowledge_version=binding.knowledge_version,
        ocop_version=binding.ocop_version,
        rights_version=binding.rights_version,
    )


def _apply_p05_decision(
    p06_candidate: P06SpeechCandidate,
    decision: Any,
    p05_schemas: ModuleType,
) -> P06SpeechCandidate:
    """Chuyển `PublicationDecision` từ P05 thành bản `SpeechCandidate` mới của P06 (`VERIFIED`/`REJECTED`).

    Args:
        p06_candidate: Ứng viên `DRAFT` ban đầu.
        decision: Phán quyết `PublicationDecision` trả về từ `PublicationGate.evaluate()`.
        p05_schemas: Module `schemas` của P05 để đối chiếu `PublicationStatus`.

    Returns:
        P06SpeechCandidate: Ứng viên mới đã qua kiểm định lại bằng `model_validate`.
    """
    payload = p06_candidate.model_dump()
    if decision.status == p05_schemas.PublicationStatus.ALLOW:
        payload["verification_status"] = CandidateVerificationStatus.VERIFIED
        payload["verified_by_gate_decision_id"] = f"p05-allow-{decision.candidate_id}"
        payload["verified_at"] = decision.checked_at or datetime.now(timezone.utc)
        payload["rejection_reasons"] = []
    else:
        payload["verification_status"] = CandidateVerificationStatus.REJECTED
        payload["verified_by_gate_decision_id"] = None
        payload["verified_at"] = None
        payload["rejection_reasons"] = [reason.value for reason in decision.reasons]
    return P06SpeechCandidate.model_validate(payload)


def test_p05_contract_alignment_allow_honey_and_block_cashew() -> None:
    """Đối chiếu hợp đồng P06 <-> P05 trên `catalog_seed.json` cho `SKU-HONEY-01` và `SKU-CASHEW-03`."""
    p05_schemas, p05_gate = _load_p05_modules(P05_DIR)
    store = p05_gate.VersionedKnowledgeStore.from_seed_file(P05_SEED_PATH)
    gate = p05_gate.PublicationGate(store)

    # 1. SKU-HONEY-01: có evidence hợp lệ, giá 159.000đ khớp ProductFact, OCOP VERIFIED -> ALLOW -> VERIFIED
    honey_draft = P06SpeechCandidate(
        candidate_id="cand-honey-01",
        tenant_id="tenant-demo-01",
        session_id="session-contract-01",
        session_epoch=1,
        origin=CandidateOrigin.PROACTIVE_STORY,
        source_chunk_id="chunk-honey-01",
        scope_mode=TargetScopeMode.SINGLE_SKU,
        sku_refs=["SKU-HONEY-01"],
        sku_bindings=[
            SkuVersionBinding(
                sku_id="SKU-HONEY-01",
                knowledge_version=1,
                ocop_version=1,
                rights_version=1,
                cited_evidence_ids=["ev-honey-04"],
                stated_price_vnd=159000,
                mentions_ocop=True,
            )
        ],
        session_rights_version=1,
        intent="product_story",
        text="Mật ong hoa cà phê Cư M'gar đạt chuẩn OCOP 4 sao cấp tỉnh, giá 159.000đ cho chai 500ml.",
        estimated_duration_sec=8.0,
        proposed_coverage=ProposedResponseCoverage(
            covered_topic_ids=["topic-honey-ocop"],
            covered_intents=["product_story"],
            coverage_mode=CoverageMode.FULL,
        ),
    )

    honey_decision = gate.evaluate(_to_p05_candidate(honey_draft, p05_schemas))
    assert honey_decision.status == p05_schemas.PublicationStatus.ALLOW
    assert honey_decision.reasons == []

    honey_verified = _apply_p05_decision(honey_draft, honey_decision, p05_schemas)
    assert honey_verified.verification_status == CandidateVerificationStatus.VERIFIED
    assert honey_verified.is_ready_for_tts() is True

    # 2. SKU-CASHEW-03: trong catalog_seed.json có ocop_status="PENDING" -> BLOCK với OCOP_NOT_VERIFIED
    cashew_draft = P06SpeechCandidate(
        candidate_id="cand-cashew-01",
        tenant_id="tenant-demo-01",
        session_id="session-contract-01",
        session_epoch=1,
        origin=CandidateOrigin.COMMENT_REPLY,
        scope_mode=TargetScopeMode.SINGLE_SKU,
        sku_refs=["SKU-CASHEW-03"],
        sku_bindings=[
            SkuVersionBinding(
                sku_id="SKU-CASHEW-03",
                knowledge_version=1,
                ocop_version=1,
                rights_version=1,
                cited_evidence_ids=["ev-cashew-01"],
                stated_price_vnd=185000,
                mentions_ocop=False,
            )
        ],
        session_rights_version=1,
        intent="product_quality",
        text="Hạt điều rang củi vỏ lụa Bình Phước giữ nhân giòn béo, giá 185.000đ hộp 500g.",
        estimated_duration_sec=7.0,
        proposed_coverage=ProposedResponseCoverage(
            covered_intents=["product_quality"],
            coverage_mode=CoverageMode.FULL,
        ),
    )

    cashew_decision = gate.evaluate(_to_p05_candidate(cashew_draft, p05_schemas))
    assert cashew_decision.status == p05_schemas.PublicationStatus.BLOCK
    assert p05_schemas.BlockReason.OCOP_NOT_VERIFIED in cashew_decision.reasons

    cashew_rejected = _apply_p05_decision(cashew_draft, cashew_decision, p05_schemas)
    assert cashew_rejected.verification_status == CandidateVerificationStatus.REJECTED
    assert cashew_rejected.is_ready_for_tts() is False
    assert p05_schemas.BlockReason.OCOP_NOT_VERIFIED.value in cashew_rejected.rejection_reasons


def test_p05_toctou_version_binding_detects_stale_price_update() -> None:
    """Xác minh `SkuVersionBinding` phát hiện đúng lỗi TOCTOU khi `ProductFact` tăng phiên bản."""
    p05_schemas, p05_gate = _load_p05_modules(P05_DIR)
    store = p05_gate.VersionedKnowledgeStore.from_seed_file(P05_SEED_PATH).clone()
    store.update_price("SKU-HONEY-01", 169000)
    gate = p05_gate.PublicationGate(store)

    stale_draft = P06SpeechCandidate(
        candidate_id="cand-honey-stale",
        tenant_id="tenant-demo-01",
        session_id="session-contract-01",
        session_epoch=1,
        origin=CandidateOrigin.COMMENT_REPLY,
        scope_mode=TargetScopeMode.SINGLE_SKU,
        sku_refs=["SKU-HONEY-01"],
        sku_bindings=[
            SkuVersionBinding(
                sku_id="SKU-HONEY-01",
                knowledge_version=1,  # Đã cũ so với v2 sau update_price
                ocop_version=1,
                rights_version=1,
                cited_evidence_ids=["ev-honey-04"],
                stated_price_vnd=159000,
                mentions_ocop=False,
            )
        ],
        session_rights_version=1,
        intent="ask_price",
        text="Mật ong hoa cà phê giá 159.000đ chai 500ml ạ.",
        estimated_duration_sec=5.0,
        proposed_coverage=ProposedResponseCoverage(
            covered_intents=["ask_price"],
            coverage_mode=CoverageMode.FULL,
        ),
    )

    decision = gate.evaluate(_to_p05_candidate(stale_draft, p05_schemas))
    assert decision.status == p05_schemas.PublicationStatus.BLOCK
    assert p05_schemas.BlockReason.STALE_KNOWLEDGE_VERSION in decision.reasons
    assert p05_schemas.BlockReason.PRICE_MISMATCH in decision.reasons

    rejected = _apply_p05_decision(stale_draft, decision, p05_schemas)
    assert rejected.verification_status == CandidateVerificationStatus.REJECTED
    assert rejected.is_ready_for_tts() is False
