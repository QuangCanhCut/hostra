"""P05 — Bộ lưu trữ tri thức có phiên bản (Mock Store) và Cổng phát ngôn (Publication Gate).

Nguyên tắc thiết kế:
- Fail-closed: Thiếu bằng chứng, sai giá, sai phiên bản hoặc vi phạm điều kiện OCOP/quyền
  đều bị CHẶN ngay lập tức, không bao giờ tự suy đoán để cho qua.
- Tách bạch chủ sở hữu: P05 chỉ ĐỌC trạng thái OCOP (từ P09) và quyền (từ P11),
  không tự ý nâng trạng thái thành VERIFIED.
- Chống TOCTOU: Cùng một hàm `evaluate()` được gọi 2 lần — lần 1 trước khi sinh TTS (P02)
  và lần 2 ngay sát thời điểm P08 commit sang P04.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Optional

from schemas import (
    ApprovalStatus,
    BlockReason,
    ClaimCategory,
    ClaimRegistryEntry,
    EligibilitySnapshot,
    EvidenceChunk,
    OcopStatus,
    ProductFact,
    PublicationDecision,
    PublicationStatus,
    RightsStatus,
    SpeechCandidate,
)

# Danh sách cụm từ cấm phổ biến cho thực phẩm đóng gói (R17 — không gán công dụng như thuốc)
DEFAULT_PROHIBITED_PHRASES: tuple[str, ...] = (
    "chữa khỏi",
    "chữa bệnh",
    "chữa bách bệnh",
    "trị dứt điểm",
    "chữa đau dạ dày",
    "chữa tiểu đường",
    "phòng ngừa ung thư",
    "chữa ung thư",
    "thay thế thuốc",
    "giảm mỡ máu cấp tốc",
)

# Các mẫu nhận diện dấu hiệu chèn lệnh (prompt injection) trong lời thoại hoặc nguồn đầu vào
PROMPT_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"bỏ qua mọi hướng dẫn", re.IGNORECASE),
    re.compile(r"bỏ qua hướng dẫn trước", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
)

# Regex trích xuất mức giá VNĐ xuất hiện trực tiếp trong văn bản lời thoại
# Hỗ trợ các dạng phổ biến: "159.000đ", "159,000 đồng", "159000 vnd", "159k"
PRICE_FULL_PATTERN = re.compile(
    r"(?<!\d)(\d{1,3}(?:[.,]\d{3})+|\d{4,7})\s*(?:đ|đồng|vnd|vnđ)\b",
    re.IGNORECASE,
)
PRICE_K_PATTERN = re.compile(r"(?<!\d)(\d{2,4})\s*k\b", re.IGNORECASE)


def extract_prices_vnd(text: str) -> list[int]:
    """Trích xuất toàn bộ mức giá (VNĐ) xuất hiện trong văn bản lời thoại."""
    prices: list[int] = []
    for match in PRICE_FULL_PATTERN.finditer(text):
        raw_digits = match.group(1).replace(".", "").replace(",", "")
        if raw_digits.isdigit():
            prices.append(int(raw_digits))
    for match in PRICE_K_PATTERN.finditer(text):
        prices.append(int(match.group(1)) * 1000)
    return prices


class VersionedKnowledgeStore:
    """Kho tri thức giả lập trong bộ nhớ có hỗ trợ tăng phiên bản để test E03 và E04."""

    def __init__(
        self,
        facts: dict[str, ProductFact],
        eligibilities: dict[str, EligibilitySnapshot],
        chunks: dict[str, EvidenceChunk],
        claims: list[ClaimRegistryEntry],
    ) -> None:
        self.facts = facts
        self.eligibilities = eligibilities
        self.chunks = chunks
        self.claims = claims

    @classmethod
    def from_seed_file(cls, seed_path: Path) -> "VersionedKnowledgeStore":
        """Nạp dữ liệu khởi tạo từ file JSON (đã được kiểm tra bằng Pydantic)."""
        raw = json.loads(seed_path.read_text(encoding="utf-8"))
        facts = {item["sku_id"]: ProductFact(**item) for item in raw["product_facts"]}
        eligibilities = {
            item["sku_id"]: EligibilitySnapshot(**item)
            for item in raw["eligibility_snapshots"]
        }
        chunks = {
            item["evidence_id"]: EvidenceChunk(**item) for item in raw["evidence_chunks"]
        }
        claims = [ClaimRegistryEntry(**item) for item in raw["claim_registry"]]
        return cls(facts=facts, eligibilities=eligibilities, chunks=chunks, claims=claims)

    def clone(self) -> "VersionedKnowledgeStore":
        """Tạo bản sao độc lập để chạy từng kịch bản đột biến dữ liệu mà không ảnh hưởng ca khác."""
        return copy.deepcopy(self)

    def update_price(self, sku_id: str, new_price_vnd: int) -> ProductFact:
        """Giả lập merchant cập nhật giá mới -> tự động tăng knowledge_version."""
        fact = self.facts[sku_id]
        updated = fact.model_copy(
            update={
                "price_vnd": new_price_vnd,
                "knowledge_version": fact.knowledge_version + 1,
            }
        )
        self.facts[sku_id] = updated
        return updated

    def update_ocop_status(self, sku_id: str, new_status: OcopStatus) -> EligibilitySnapshot:
        """Giả lập P09 cập nhật trạng thái OCOP (vd: hết hạn/thu hồi) -> tăng ocop_version."""
        snap = self.eligibilities[sku_id]
        updated = snap.model_copy(
            update={
                "ocop_status": new_status,
                "ocop_version": snap.ocop_version + 1,
            }
        )
        self.eligibilities[sku_id] = updated
        return updated

    def update_rights_status(
        self, sku_id: str, new_status: RightsStatus
    ) -> EligibilitySnapshot:
        """Giả lập P11 cập nhật trạng thái quyền (vd: thu hồi) -> tăng rights_version."""
        snap = self.eligibilities[sku_id]
        updated = snap.model_copy(
            update={
                "rights_status": new_status,
                "rights_version": snap.rights_version + 1,
            }
        )
        self.eligibilities[sku_id] = updated
        return updated


class PublicationGate:
    """Cổng kiểm duyệt phát ngôn P05 theo nguyên tắc fail-closed (Hard Gate G3/G4)."""

    def __init__(self, store: VersionedKnowledgeStore) -> None:
        self.store = store

    def evaluate(self, candidate: SpeechCandidate) -> PublicationDecision:
        """Kiểm tra toàn bộ điều kiện an toàn, dữ liệu và phiên bản của một lời thoại."""
        reasons: list[BlockReason] = []
        details: list[str] = []

        fact: Optional[ProductFact] = self.store.facts.get(candidate.sku_id)
        elig: Optional[EligibilitySnapshot] = self.store.eligibilities.get(candidate.sku_id)

        # 1. Kiểm tra tồn tại SKU & trạng thái điều kiện (fail-closed nếu thiếu)
        if fact is None or elig is None:
            return PublicationDecision(
                candidate_id=candidate.candidate_id,
                status=PublicationStatus.BLOCK,
                reasons=[BlockReason.MISSING_EVIDENCE],
                details=[f"Không tìm thấy dữ liệu hoặc trạng thái điều kiện cho SKU '{candidate.sku_id}'."],
                checked_knowledge_version=0,
                checked_ocop_version=0,
                checked_rights_version=0,
            )

        # 2. Kiểm tra cô lập tenant (R10)
        if candidate.tenant_id != fact.tenant_id or candidate.tenant_id != elig.tenant_id:
            reasons.append(BlockReason.TENANT_MISMATCH)
            details.append(
                f"Lệch tenant: candidate thuộc '{candidate.tenant_id}', dữ liệu thuộc '{fact.tenant_id}'."
            )

        # 3. Kiểm tra dấu hiệu Prompt Injection
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(candidate.text):
                reasons.append(BlockReason.PROMPT_INJECTION_DETECTED)
                details.append(f"Phát hiện mẫu nghi ngờ prompt injection: '{pattern.pattern}'.")
                break

        # 4. Kiểm tra trạng thái phê duyệt của ProductFact
        if fact.approval_status != ApprovalStatus.APPROVED:
            reasons.append(BlockReason.UNAPPROVED_FACT)
            details.append(
                f"ProductFact của '{candidate.sku_id}' chưa được duyệt (hiện tại: {fact.approval_status.value})."
            )

        # 5. Kiểm tra phiên bản chống lỗi TOCTOU (Hard Gate G3)
        if candidate.knowledge_version != fact.knowledge_version:
            reasons.append(BlockReason.STALE_KNOWLEDGE_VERSION)
            details.append(
                f"Dữ liệu tri thức đã cũ: candidate dùng v{candidate.knowledge_version}, "
                f"hiện tại là v{fact.knowledge_version}."
            )
        if candidate.ocop_version != elig.ocop_version:
            reasons.append(BlockReason.STALE_OCOP_VERSION)
            details.append(
                f"Phiên bản OCOP đã cũ: candidate dùng v{candidate.ocop_version}, "
                f"hiện tại là v{elig.ocop_version}."
            )
        if candidate.rights_version != elig.rights_version:
            reasons.append(BlockReason.STALE_RIGHTS_VERSION)
            details.append(
                f"Phiên bản quyền đã cũ: candidate dùng v{candidate.rights_version}, "
                f"hiện tại là v{elig.rights_version}."
            )

        # 6. Kiểm tra quyền tài sản từ P11 (R09)
        if elig.rights_status != RightsStatus.ACTIVE:
            reasons.append(BlockReason.RIGHTS_INVALID)
            details.append(
                f"Quyền sử dụng tài sản không còn hiệu lực (trạng thái P11: {elig.rights_status.value})."
            )

        # 7. Kiểm tra điều kiện an toàn thực phẩm & OCOP từ P09 (ACR-002, R16, R17)
        if not elig.food_safety_verified:
            reasons.append(BlockReason.FOOD_SAFETY_UNVERIFIED)
            details.append(f"SKU '{candidate.sku_id}' chưa đạt xác minh điều kiện thực phẩm áp dụng.")

        mentions_ocop = candidate.mentions_ocop or ("ocop" in candidate.text.lower())
        if elig.ocop_status != OcopStatus.VERIFIED:
            reasons.append(BlockReason.OCOP_NOT_VERIFIED)
            if mentions_ocop:
                details.append(
                    f"Lời thoại nhắc đến OCOP nhưng trạng thái P09 của '{candidate.sku_id}' "
                    f"là {elig.ocop_status.value} (chưa VERIFIED)."
                )
            else:
                details.append(
                    f"SKU '{candidate.sku_id}' chưa đạt điều kiện OCOP VERIFIED của MVP "
                    f"(trạng thái P09: {elig.ocop_status.value})."
                )

        # 8. Kiểm tra bằng chứng trích dẫn & chặn dẫn chứng chéo SKU
        if not candidate.cited_evidence_ids and candidate.stated_price_vnd is None:
            reasons.append(BlockReason.MISSING_EVIDENCE)
            details.append("Lời thoại không trích dẫn evidence_id nào và không phải câu báo giá từ ProductFact.")

        for eid in candidate.cited_evidence_ids:
            chunk = self.store.chunks.get(eid)
            if chunk is None:
                reasons.append(BlockReason.MISSING_EVIDENCE)
                details.append(f"Không tồn tại bằng chứng với mã '{eid}'.")
                continue
            if chunk.tenant_id != candidate.tenant_id:
                reasons.append(BlockReason.TENANT_MISMATCH)
                details.append(f"Bằng chứng '{eid}' thuộc tenant khác ('{chunk.tenant_id}').")
            if chunk.sku_id != candidate.sku_id:
                reasons.append(BlockReason.CROSS_SKU_VIOLATION)
                details.append(
                    f"Vi phạm chéo SKU: lời thoại cho '{candidate.sku_id}' nhưng trích dẫn "
                    f"bằng chứng '{eid}' thuộc '{chunk.sku_id}'."
                )
            if chunk.approval_status != ApprovalStatus.APPROVED:
                reasons.append(BlockReason.UNAPPROVED_FACT)
                details.append(
                    f"Bằng chứng '{eid}' chưa được phê duyệt (trạng thái: {chunk.approval_status.value})."
                )

        # 9. Kiểm tra khớp giá tuyệt đối (cả trường stated_price_vnd lẫn con số trong text)
        if candidate.stated_price_vnd is not None and candidate.stated_price_vnd != fact.price_vnd:
            reasons.append(BlockReason.PRICE_MISMATCH)
            details.append(
                f"Sai giá khai báo: candidate ghi {candidate.stated_price_vnd:,}đ, "
                f"giá chuẩn hiện tại là {fact.price_vnd:,}đ."
            )

        for found_price in extract_prices_vnd(candidate.text):
            if found_price != fact.price_vnd:
                if BlockReason.PRICE_MISMATCH not in reasons:
                    reasons.append(BlockReason.PRICE_MISMATCH)
                details.append(
                    f"Phát hiện giá sai trong văn bản lời thoại: {found_price:,}đ "
                    f"(giá chuẩn hiện tại là {fact.price_vnd:,}đ)."
                )

        # 10. Kiểm tra tuyên bố / công dụng bị cấm (R17)
        text_lower = candidate.text.lower()
        for phrase in DEFAULT_PROHIBITED_PHRASES:
            if phrase in text_lower:
                reasons.append(BlockReason.PROHIBITED_CLAIM)
                details.append(f"Lời thoại chứa cụm từ công dụng bị cấm đối với thực phẩm: '{phrase}'.")
                break

        if BlockReason.PROHIBITED_CLAIM not in reasons:
            for claim in self.store.claims:
                if (
                    claim.sku_id == candidate.sku_id
                    and claim.category == ClaimCategory.PROHIBITED
                    and claim.claim_text.lower() in text_lower
                ):
                    reasons.append(BlockReason.PROHIBITED_CLAIM)
                    details.append(f"Lời thoại khớp với tuyên bố bị cấm trong Claim Registry ({claim.claim_id}).")
                    break

        # Loại bỏ mã lỗi trùng lặp nhưng giữ nguyên thứ tự
        unique_reasons = list(dict.fromkeys(reasons))
        status = PublicationStatus.BLOCK if unique_reasons else PublicationStatus.ALLOW

        return PublicationDecision(
            candidate_id=candidate.candidate_id,
            status=status,
            reasons=unique_reasons,
            details=details,
            checked_knowledge_version=fact.knowledge_version,
            checked_ocop_version=elig.ocop_version,
            checked_rights_version=elig.rights_version,
        )
