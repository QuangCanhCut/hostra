"""Bộ chuyển đổi chỉ-đọc kết nối P06 tới Cổng phát ngôn P05 (`knowledge-verification`).

1. File này giải quyết vấn đề gì?
   Cầu nối giữa hợp đồng `p06-mock-v0.1` (hỗ trợ 4 `TargetScopeMode` và `SkuEvidenceView`) với
   `PublicationGate` / `VersionedKnowledgeStore` đơn-SKU của P05 mà tuyệt đối không sao chép,
   chia nhánh hay chỉnh sửa mã nguồn của module P05.
2. Trách nhiệm chính của module là gì?
   Nạp động chỉ-đọc `schemas.py` và `publication_gate.py` từ `knowledge-verification/` (có cache
   và cô lập `sys.modules`), triển khai `get_sku_evidence()` (cô lập tenant, kiểm tra eligibility)
   và `verify_candidate()` cho cả 4 chế độ `SINGLE_SKU`, `MULTI_SKU_COMPARE`, `SHOP_WIDE_POLICY`,
   và `UNRESOLVED_SKU`.
3. Module này liên kết với các thành phần nào?
   Triển khai `KnowledgeVerifierPort` (`adapters/interfaces.py`), tái sử dụng `ProhibitedEchoGuard`
   (`guardrails/prohibited_echo_guard.py`), và đọc chỉ-đọc từ `../knowledge-verification/`.
4. Input và output chính là gì?
   Input là `(tenant_id, sku_id)` hoặc `SpeechCandidate` (`DRAFT` / tái kiểm định TOCTOU);
   Output là `SkuEvidenceView` hoặc `CandidateVerificationResult` (`VERIFIED` / `REJECTED`).
5. Có những constraints hoặc invariants quan trọng nào?
   - Không bao giờ chỉnh sửa, sao chép hay làm yếu logic của `PublicationGate` P05.
   - Mọi kịch bản thiếu dữ liệu, sai tenant, sai phiên bản TOCTOU, so sánh cảm tính chưa có căn cứ,
     chính sách shop chưa có cổng kiểm chứng (`SHOP_WIDE_POLICY`), hay rò rỉ SKU trong `UNRESOLVED_SKU`
     đều phải **fail-closed** (`REJECTED`).
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import re
import sys
import threading
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Final, Optional

from p06.adapters.interfaces import (
    CandidateVerificationResult,
    KnowledgeVerifierPort,
    SkuEvidenceView,
)
from p06.guardrails.prohibited_echo_guard import ProhibitedEchoGuard
from p06.guardrails.spoken_text_hygiene import check_spoken_text_hygiene
from p06.schemas.candidate import (
    CandidateVerificationStatus,
    SkuVersionBinding,
    SpeechCandidate,
    TargetScopeMode,
)

# Đường dẫn mặc định sang module P05 (`experiments/sales-intelligence/knowledge-verification/`).
_DEFAULT_P05_DIR: Final[Path] = Path(__file__).resolve().parents[4] / "knowledge-verification"

# Cache mức module theo đường dẫn tuyệt đối và khóa đồng bộ cho nạp module trong một tiến trình PoC.
_P05_MODULE_CACHE: dict[Path, tuple[ModuleType, ModuleType]] = {}
_P05_IMPORT_LOCK = threading.RLock()

# Từ khóa so sánh cảm tính / tuyệt đối phải fail-closed trừ khi có claim/chunk APPROVED tường minh.
_SUBJECTIVE_COMPARATIVE_KEYWORDS: Final[tuple[str, ...]] = (
    "tốt hơn",
    "ngon hơn",
    "nhiều hơn",
    "ít hơn",
    "vượt trội",
    "bán chạy hơn",
    "đáng mua hơn",
    "rẻ nhất",
    "tốt nhất",
    "số 1",
    "hàng đầu",
)

# Các mẫu nhận diện prompt injection mở rộng (bổ trợ thêm ngoài PROMPT_INJECTION_PATTERNS của P05).
_PROMPT_INJECTION_REGEXES: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(
        r"ignore\s+(?:all\s+|any\s+)?(?:prior|above|previous)\s+(?:instructions?|prompts?|rules?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"disregard\s+(?:all\s+|any\s+)?(?:previous|prior|above)\s+(?:instructions?|rules?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"bỏ\s+qua\s+(?:tất\s+cả|toàn\s+bộ|mọi)\s+(?:hướng\s+dẫn|quy\s+tắc|lệnh)",
        re.IGNORECASE,
    ),
    re.compile(
        r"quên\s+(?:tất\s+cả|toàn\s+bộ|mọi)?\s*(?:hướng\s+dẫn|quy\s+tắc|lệnh)\s*(?:trước|cũ)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:reveal|show|print|dump|tiết\s+lộ|hiển\s+thị)\s+(?:your\s+|the\s+)?(?:system\s+prompt|hidden\s+instructions?)",
        re.IGNORECASE,
    ),
    re.compile(r"\[\s*(?:SYSTEM|INST|/INST|SYS|/SYS)\s*\]", re.IGNORECASE),
    re.compile(r"<\s*(?:system|im_start|im_end)\s*>", re.IGNORECASE),
    re.compile(
        r"(?:you\s+are\s+now|act\s+as|hãy\s+đóng\s+vai)\s+(?:a\s+)?(?:jailbreak|developer\s+mode|unfiltered|admin)",
        re.IGNORECASE,
    ),
    re.compile(
        r"override\s+(?:safety|guardrails?|policy|policies|instructions?)",
        re.IGNORECASE,
    ),
)

# Từ khóa so sánh giá khách quan (chỉ được phép khi đủ giá verified và đúng chiều so sánh).
_OBJECTIVE_PRICE_COMPARATIVE_KEYWORDS: Final[tuple[str, ...]] = (
    "rẻ hơn",
    "đắt hơn",
    "cao hơn",
    "thấp hơn",
)

# Từ chung/đơn vị không đủ đặc trưng để tự nhận diện đơn lẻ một SKU trong câu so sánh giá.
_GENERIC_ALIAS_STOPWORDS: Final[frozenset[str]] = frozenset(
    {
        "hạt",
        "trái",
        "quả",
        "chai",
        "hộp",
        "lọ",
        "túi",
        "gói",
        "sản",
        "phẩm",
        "loại",
        "nguyên",
        "chất",
        "tự",
        "nhiên",
        "đặc",
        "biệt",
        "cổ",
        "thụ",
        "hoa",
        "sấy",
        "nứt",
        "vỏ",
        "thiếc",
        "thủy",
        "tinh",
        "tỉnh",
        "huyện",
        "xã",
        "giá",
        "bán",
        "còn",
        "và",
        "với",
        "cho",
        "của",
        "từ",
        "tại",
    }
)

# Tách câu/vế giữ nguyên dấu chấm/phẩy nằm giữa chữ số (vd: 159.000đ hoặc 245,000đ).
_CLAUSE_PUNCT_SPLIT_RE: Final[re.Pattern[str]] = re.compile(r"(?:\.(?!\d)|,(?!\d)|[;!\n])+")
_SENTENCE_SPLIT_RE: Final[re.Pattern[str]] = re.compile(r"(?:\.(?!\d)|[;!\n])+")
_CLAUSE_CONNECTOR_SPLIT_RE: Final[re.Pattern[str]] = re.compile(
    r"\s+(?:còn|trong khi|so với|nhưng|mà|rẻ hơn|đắt hơn|cao hơn|thấp hơn)\s+",
    re.IGNORECASE,
)
_AND_CONNECTOR_SPLIT_RE: Final[re.Pattern[str]] = re.compile(r"\s+và\s+", re.IGNORECASE)
_PRICE_CONTEXT_HINTS: Final[tuple[str, ...]] = ("giá", "đồng", "vnđ", "vnd", "đắt", "rẻ")
_UNIT_TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"^\d+(?:ml|g|kg|l|%)?$")


def _load_p05_modules(p05_dir: Path) -> tuple[ModuleType, ModuleType]:
    """Nạp chỉ-đọc `schemas.py` và `publication_gate.py` từ P05 mà không gây xung đột `sys.modules`.

    Lý do kỹ thuật: `publication_gate.py` của P05 dùng câu lệnh `from schemas import ...`.
    Hàm này dùng `_P05_IMPORT_LOCK` (RLock) bảo đảm an toàn luồng trong phạm vi một tiến trình
    Python đơn lẻ của giai đoạn PoC (giả định single-process, không chia sẻ trạng thái qua nhiều
    tiến trình), tạm gán `sys.modules["schemas"] = p05_schemas` trong `try ... except ... finally`
    để dọn sạch module lỗi nếu `exec_module` ném ngoại lệ và khôi phục nguyên trạng `sys.modules`.

    Args:
        p05_dir: Đường dẫn tới thư mục `experiments/sales-intelligence/knowledge-verification`.

    Returns:
        tuple[ModuleType, ModuleType]: Cặp module `(p05_schemas, p05_gate)` đã nạp và lưu cache.

    Raises:
        RuntimeError: Nếu không tìm thấy hoặc không nạp được các tệp nguồn của P05.
    """
    resolved_dir = p05_dir.resolve()
    with _P05_IMPORT_LOCK:
        cached = _P05_MODULE_CACHE.get(resolved_dir)
        if cached is not None:
            return cached

        schemas_path = resolved_dir / "schemas.py"
        gate_path = resolved_dir / "publication_gate.py"
        if not schemas_path.is_file() or not gate_path.is_file():
            raise RuntimeError(
                f"Không tìm thấy đầy đủ mã nguồn chỉ-đọc của P05 tại '{resolved_dir}'."
            )

        dir_hash = hashlib.sha256(str(resolved_dir).encode("utf-8")).hexdigest()[:12]
        schemas_mod_name = f"p05_schemas_readonly_{dir_hash}"
        gate_mod_name = f"p05_gate_readonly_{dir_hash}"

        schemas_spec = importlib.util.spec_from_file_location(schemas_mod_name, schemas_path)
        gate_spec = importlib.util.spec_from_file_location(gate_mod_name, gate_path)
        if schemas_spec is None or schemas_spec.loader is None:
            raise RuntimeError(f"Không thể tạo module spec cho P05 schemas tại '{schemas_path}'.")
        if gate_spec is None or gate_spec.loader is None:
            raise RuntimeError(
                f"Không thể tạo module spec cho P05 publication_gate tại '{gate_path}'."
            )

        p05_schemas = importlib.util.module_from_spec(schemas_spec)
        p05_gate = importlib.util.module_from_spec(gate_spec)

        sys.modules[schemas_mod_name] = p05_schemas
        sys.modules[gate_mod_name] = p05_gate
        previous_schemas_mod = sys.modules.get("schemas")
        sys.modules["schemas"] = p05_schemas
        try:
            schemas_spec.loader.exec_module(p05_schemas)
            gate_spec.loader.exec_module(p05_gate)
        except Exception:
            sys.modules.pop(schemas_mod_name, None)
            sys.modules.pop(gate_mod_name, None)
            raise
        finally:
            if previous_schemas_mod is None:
                sys.modules.pop("schemas", None)
            else:
                sys.modules["schemas"] = previous_schemas_mod

        _P05_MODULE_CACHE[resolved_dir] = (p05_schemas, p05_gate)
        return p05_schemas, p05_gate


def _ensure_utc(dt: datetime) -> datetime:
    """Chuẩn hóa `datetime` về UTC có múi giờ để đối chiếu cửa sổ hiệu lực an toàn."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _is_fact_within_validity_window(fact: Any, at_time: datetime) -> bool:
    """Kiểm tra `ProductFact` có đang nằm trong cửa sổ `[valid_from, valid_until]` hay không."""
    check_ts = _ensure_utc(at_time)
    valid_from = _ensure_utc(fact.valid_from)
    if check_ts < valid_from:
        return False
    if fact.valid_until is not None:
        valid_until = _ensure_utc(fact.valid_until)
        if check_ts > valid_until:
            return False
    return True


def _prepare_candidate_for_verification(candidate: SpeechCandidate) -> SpeechCandidate:
    """Đưa bản sao ứng viên về trạng thái `DRAFT` trước khi chấm lại (hỗ trợ tái kiểm định TOCTOU)."""
    if candidate.verification_status == CandidateVerificationStatus.DRAFT:
        return candidate
    payload = copy.deepcopy(candidate.model_dump())
    payload["verification_status"] = CandidateVerificationStatus.DRAFT
    payload["verified_by_gate_decision_id"] = None
    payload["verified_at"] = None
    payload["rejection_reasons"] = []
    return SpeechCandidate.model_validate(payload)


def _normalize_text(text: str) -> str:
    """Chuẩn hóa chữ thường và khoảng trắng đơn để đối chiếu nhất quán."""
    return " ".join(text.lower().split())


def _tokenize_name(name: str) -> list[str]:
    """Tách tên SKU thành các token chữ/số sạch phục vụ trích xuất cụm nhận diện."""
    cleaned = re.sub(r"[^\w\s]", " ", name.lower(), flags=re.UNICODE)
    return [tok for tok in cleaned.split() if tok]


def _build_unique_sku_alias_patterns(
    facts_by_sku: dict[str, Any],
) -> dict[str, re.Pattern[str]]:
    """Xây dựng regex nhận diện riêng biệt từng SKU cho câu so sánh nhiều sản phẩm.

    Lý do kỹ thuật: Chỉ giữ những cụm tên xuất hiện duy nhất ở một SKU trong tập đang xét,
    loại bỏ hoàn toàn các từ/cụm dùng chung để không gán nhầm giá giữa 2 sản phẩm.

    Args:
        facts_by_sku: Ánh xạ `sku_id -> ProductFact` của các SKU cần phân biệt.

    Returns:
        dict[str, re.Pattern[str]]: Ánh xạ `sku_id -> Pattern` biên dịch sẵn theo ranh giới từ.
    """
    raw_aliases: dict[str, set[str]] = {}
    alias_owners: dict[str, set[str]] = {}

    for sku_id, fact in facts_by_sku.items():
        candidates: set[str] = {sku_id.lower(), _normalize_text(fact.sku_name)}
        tokens = _tokenize_name(fact.sku_name)
        lead_tokens = [tok for tok in tokens if not _UNIT_TOKEN_RE.match(tok)]

        # Lấy các n-gram 2..4 từ liên tiếp trong phần tên cốt lõi.
        for n in (2, 3, 4):
            for idx in range(0, max(0, len(lead_tokens) - n + 1)):
                phrase_tokens = lead_tokens[idx : idx + n]
                if all(tok in _GENERIC_ALIAS_STOPWORDS for tok in phrase_tokens):
                    continue
                candidates.add(" ".join(phrase_tokens))

        # Chỉ nhận từ đơn thuộc 3 từ đầu tiên nếu không nằm trong danh sách từ chung.
        for tok in lead_tokens[:3]:
            if len(tok) >= 3 and tok not in _GENERIC_ALIAS_STOPWORDS:
                candidates.add(tok)

        raw_aliases[sku_id] = candidates
        for alias in candidates:
            alias_owners.setdefault(alias, set()).add(sku_id)

    patterns: dict[str, re.Pattern[str]] = {}
    for sku_id, candidates in raw_aliases.items():
        unique_aliases = sorted(
            (alias for alias in candidates if len(alias_owners.get(alias, set())) == 1),
            key=len,
            reverse=True,
        )
        escaped = [re.escape(alias) for alias in unique_aliases]
        if not escaped:
            escaped = [re.escape(sku_id.lower())]
        patterns[sku_id] = re.compile(
            r"(?<!\w)(?:" + "|".join(escaped) + r")(?!\w)",
            re.IGNORECASE,
        )
    return patterns


def _build_unresolved_leak_patterns(
    facts: Sequence[Any],
    excluded_terms: frozenset[str] = frozenset(),
) -> tuple[tuple[str, re.Pattern[str]], ...]:
    """Tạo bộ nhận diện tên/mã SKU (kể cả n-gram 2 từ cốt lõi) để chặn rò rỉ SKU."""
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for fact in facts:
        leak_terms: set[str] = {fact.sku_id.lower(), _normalize_text(fact.sku_name)}
        tokens = [tok for tok in _tokenize_name(fact.sku_name) if not _UNIT_TOKEN_RE.match(tok)]
        # Thu thập toàn bộ 2-gram cốt lõi (loại cặp toàn stopword) và 3-gram đầu tên sản phẩm.
        for idx in range(0, max(0, len(tokens) - 1)):
            bigram = tokens[idx : idx + 2]
            if all(tok in _GENERIC_ALIAS_STOPWORDS for tok in bigram):
                continue
            leak_terms.add(" ".join(bigram))
        if len(tokens) >= 3:
            leak_terms.add(" ".join(tokens[:3]))
            if tokens[0] in _GENERIC_ALIAS_STOPWORDS:
                leak_terms.add(" ".join(tokens[1:3]))

        filtered_terms = [
            t for t in leak_terms if t and t not in excluded_terms
        ]
        if not filtered_terms:
            filtered_terms = [fact.sku_id.lower()]
        sorted_terms = sorted(filtered_terms, key=len, reverse=True)
        regex = re.compile(
            r"(?<!\w)(?:" + "|".join(re.escape(t) for t in sorted_terms) + r")(?!\w)",
            re.IGNORECASE,
        )
        patterns.append((fact.sku_id, regex))
    return tuple(patterns)


def _compile_word_boundary_pattern(phrase: str) -> re.Pattern[str]:
    """Biên dịch regex khớp cụm từ có ranh giới từ để tránh khớp nhầm tiền tố/hậu tố."""
    return re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.IGNORECASE)


class P05KnowledgeAdapter(KnowledgeVerifierPort):
    """Adapter chỉ-đọc kết nối P06 tới `PublicationGate` và `VersionedKnowledgeStore` của P05."""

    def __init__(
        self,
        store: Any,
        p05_dir: Optional[Path] = None,
    ) -> None:
        """Khởi tạo adapter với kho tri thức P05 hiện hành.

        Args:
            store: Thể hiện `VersionedKnowledgeStore` từ P05.
            p05_dir: Thư mục chứa mã nguồn P05 (mặc định trỏ sang `../knowledge-verification`).
        """
        resolved_dir = p05_dir if p05_dir is not None else _DEFAULT_P05_DIR
        self._p05_schemas, self._p05_gate = _load_p05_modules(resolved_dir)
        self._store = store
        self._gate = self._p05_gate.PublicationGate(store)
        self._echo_guard = ProhibitedEchoGuard(
            extra_prohibited_phrases=self._p05_gate.DEFAULT_PROHIBITED_PHRASES
        )

    @classmethod
    def from_seed_file(
        cls,
        seed_path: Path,
        p05_dir: Optional[Path] = None,
    ) -> P05KnowledgeAdapter:
        """Khởi tạo adapter trực tiếp từ tệp JSON hạt giống theo định dạng P05.

        Args:
            seed_path: Đường dẫn tới tệp dữ liệu tri thức JSON.
            p05_dir: Thư mục mã nguồn P05 tùy chọn.

        Returns:
            P05KnowledgeAdapter: Adapter đã nạp sẵn kho tri thức và `PublicationGate`.
        """
        resolved_dir = p05_dir if p05_dir is not None else _DEFAULT_P05_DIR
        _, p05_gate = _load_p05_modules(resolved_dir)
        store = p05_gate.VersionedKnowledgeStore.from_seed_file(seed_path)
        return cls(
            store=store,
            p05_dir=resolved_dir,
        )

    def get_sku_evidence(
        self,
        tenant_id: str,
        sku_id: str,
        at_time: Optional[datetime] = None,
    ) -> SkuEvidenceView:
        """Truy xuất bản chụp tri thức chỉ-đọc cho một SKU kèm kiểm tra cô lập tenant và eligibility.

        Lý do thiết kế (Fail-closed): Nếu thiếu SKU sẽ ném `KeyError`; nếu lệch `tenant_id`
        sẽ ném `PermissionError`; nếu `ProductFact` chứa dấu hiệu prompt injection sẽ ném `ValueError`;
        nếu `ProductFact` hết hạn hoặc chưa đến ngày hiệu lực sẽ đánh dấu `is_eligible=False`;
        và mọi `EvidenceChunk` chứa prompt injection sẽ bị loại khỏi `approved_chunks`.

        Args:
            tenant_id: Mã tenant yêu cầu dữ liệu.
            sku_id: Mã SKU cần truy xuất.
            at_time: Mốc thời gian kiểm tra hiệu lực (`valid_from..valid_until`, mặc định UTC hiện tại).

        Returns:
            SkuEvidenceView: Bản chụp tri thức và trạng thái điều kiện hiện hành.

        Raises:
            KeyError: Nếu không tồn tại `ProductFact` hoặc `EligibilitySnapshot` cho `sku_id`.
            PermissionError: Nếu `tenant_id` không khớp với dữ liệu sở hữu SKU.
            ValueError: Nếu các trường văn bản của `ProductFact` có dấu hiệu prompt injection.
        """
        fact = self._store.facts.get(sku_id)
        elig = self._store.eligibilities.get(sku_id)
        if fact is None or elig is None:
            raise KeyError(f"Không tìm thấy dữ liệu hoặc trạng thái điều kiện cho SKU '{sku_id}'.")

        if fact.tenant_id != tenant_id or elig.tenant_id != tenant_id:
            raise PermissionError(
                f"Từ chối truy cập chéo tenant cho SKU '{sku_id}' (yêu cầu từ '{tenant_id}')."
            )

        fact_inj = self._find_fact_prompt_injection(fact)
        if fact_inj is not None:
            raise ValueError(
                f"ProductFact của SKU '{sku_id}' chứa dấu hiệu prompt injection ({fact_inj})."
            )

        check_ts = at_time if at_time is not None else datetime.now(timezone.utc)
        ineligible_reasons: list[str] = []
        if fact.approval_status != self._p05_schemas.ApprovalStatus.APPROVED:
            ineligible_reasons.append("UNAPPROVED_FACT")
        if not _is_fact_within_validity_window(fact, check_ts):
            ineligible_reasons.append("FACT_OUTSIDE_VALIDITY_WINDOW")
        if elig.ocop_status != self._p05_schemas.OcopStatus.VERIFIED:
            ineligible_reasons.append("OCOP_NOT_VERIFIED")
        if elig.food_safety_verified is not True:
            ineligible_reasons.append("FOOD_SAFETY_UNVERIFIED")
        if elig.rights_status != self._p05_schemas.RightsStatus.ACTIVE:
            ineligible_reasons.append("RIGHTS_INVALID")

        approved_chunks = tuple(
            {
                "evidence_id": chunk.evidence_id,
                "section": chunk.section,
                "content": chunk.content,
            }
            for chunk in self._store.chunks.values()
            if (
                chunk.tenant_id == tenant_id
                and chunk.sku_id == sku_id
                and chunk.approval_status == self._p05_schemas.ApprovalStatus.APPROVED
                and self._has_prompt_injection(chunk.content) is None
                and self._has_prompt_injection(chunk.section) is None
            )
        )

        allowed_claims: list[dict[str, Any]] = []
        prohibited_claims: list[str] = []
        for claim in self._store.claims:
            if (
                claim.tenant_id != tenant_id
                or claim.sku_id != sku_id
                or claim.approval_status != self._p05_schemas.ApprovalStatus.APPROVED
            ):
                continue

            if claim.category == self._p05_schemas.ClaimCategory.PROHIBITED:
                prohibited_claims.append(claim.claim_text)
            else:
                if self._has_prompt_injection(claim.claim_text) is not None:
                    continue
                # Không xuất claim yêu cầu OCOP VERIFIED nếu trạng thái OCOP hiện tại chưa VERIFIED.
                if (
                    claim.requires_ocop_verified
                    and elig.ocop_status != self._p05_schemas.OcopStatus.VERIFIED
                ):
                    continue
                allowed_claims.append(
                    {
                        "claim_id": claim.claim_id,
                        "claim_text": claim.claim_text,
                        "category": claim.category.value,
                        "evidence_ids": list(claim.evidence_ids),
                        "requires_ocop_verified": claim.requires_ocop_verified,
                    }
                )

        return SkuEvidenceView(
            tenant_id=fact.tenant_id,
            sku_id=fact.sku_id,
            sku_name=fact.sku_name,
            price_vnd=fact.price_vnd,
            weight_display=fact.weight_display,
            expiry_display=fact.expiry_display,
            origin=fact.origin,
            ingredients=tuple(fact.ingredients),
            storage_instructions=fact.storage_instructions,
            knowledge_version=fact.knowledge_version,
            ocop_status=elig.ocop_status.value,
            ocop_version=elig.ocop_version,
            ocop_code=elig.ocop_code,
            food_safety_verified=elig.food_safety_verified,
            rights_status=elig.rights_status.value,
            rights_version=elig.rights_version,
            approved_chunks=approved_chunks,
            allowed_claims=tuple(allowed_claims),
            prohibited_claims=tuple(prohibited_claims),
            is_eligible=(len(ineligible_reasons) == 0),
            ineligible_reasons=tuple(ineligible_reasons),
        )

    def verify_candidate(
        self,
        candidate: SpeechCandidate,
        verified_at: Optional[datetime] = None,
    ) -> CandidateVerificationResult:
        """Kiểm định một `SpeechCandidate` qua cổng P05 và các bộ bảo vệ theo từng `TargetScopeMode`.

        Args:
            candidate: Ứng viên lời thoại cần kiểm định (hỗ trợ tái kiểm định TOCTOU).
            verified_at: Dấu thời gian kiểm định (dùng đồng hồ mô phỏng hoặc mặc định UTC hiện tại).

        Returns:
            CandidateVerificationResult: Kết quả `VERIFIED` hoặc `REJECTED` kèm chi tiết từng SKU.
        """
        ts = verified_at if verified_at is not None else datetime.now(timezone.utc)
        working_candidate = _prepare_candidate_for_verification(candidate)

        if working_candidate.scope_mode == TargetScopeMode.SINGLE_SKU:
            return self._verify_single_sku(working_candidate, ts)
        if working_candidate.scope_mode == TargetScopeMode.MULTI_SKU_COMPARE:
            return self._verify_multi_sku_compare(working_candidate, ts)
        if working_candidate.scope_mode == TargetScopeMode.SHOP_WIDE_POLICY:
            return self._verify_shop_wide_policy(working_candidate)
        return self._verify_unresolved_sku(working_candidate, ts)

    def _to_p05_candidate(
        self,
        candidate: SpeechCandidate,
        binding: SkuVersionBinding,
    ) -> Any:
        """Ánh xạ `SpeechCandidate` + một `SkuVersionBinding` sang DTO của P05 `PublicationGate`."""
        return self._p05_schemas.SpeechCandidate(
            candidate_id=candidate.candidate_id,
            tenant_id=candidate.tenant_id,
            session_id=candidate.session_id,
            sku_id=binding.sku_id,
            text=candidate.text,
            cited_evidence_ids=list(binding.cited_evidence_ids),
            stated_price_vnd=binding.stated_price_vnd,
            mentions_ocop=binding.mentions_ocop,
            knowledge_version=binding.knowledge_version,
            ocop_version=binding.ocop_version,
            rights_version=binding.rights_version,
        )

    def _collect_sku_prohibited_phrases(
        self,
        tenant_id: str,
        sku_ids: Sequence[str],
    ) -> tuple[str, ...]:
        """Thu thập các cụm từ/claim bị cấm từ `ClaimRegistry` cho tập SKU thuộc đúng tenant."""
        sku_set = set(sku_ids)
        return tuple(
            claim.claim_text
            for claim in self._store.claims
            if (
                claim.tenant_id == tenant_id
                and claim.sku_id in sku_set
                and claim.category == self._p05_schemas.ClaimCategory.PROHIBITED
            )
        )

    def _has_prompt_injection(self, text: str) -> Optional[str]:
        """Kiểm tra mẫu chèn lệnh (prompt injection) gồm bộ P05 và bộ regex mở rộng."""
        for pattern in (*self._p05_gate.PROMPT_INJECTION_PATTERNS, *_PROMPT_INJECTION_REGEXES):
            if pattern.search(text):
                return pattern.pattern
        return None

    def _find_fact_prompt_injection(self, fact: Any) -> Optional[str]:
        """Quét toàn bộ trường văn bản của `ProductFact` để chặn dữ liệu nguồn nhiễm injection."""
        fields_to_scan = (
            fact.sku_name,
            fact.weight_display,
            fact.expiry_display,
            fact.origin,
            fact.storage_instructions,
            *fact.ingredients,
        )
        for field_text in fields_to_scan:
            matched = self._has_prompt_injection(field_text)
            if matched is not None:
                return matched
        return None

    def _collect_approved_corpus(
        self,
        tenant_id: str,
        sku_ids: Sequence[str],
    ) -> tuple[str, ...]:
        """Thu thập ngữ liệu chunk/claim `APPROVED` của tập SKU dùng cho đối chiếu so sánh."""
        sku_set = set(sku_ids)
        return tuple(
            _normalize_text(chunk.content)
            for chunk in self._store.chunks.values()
            if (
                chunk.tenant_id == tenant_id
                and chunk.sku_id in sku_set
                and chunk.approval_status == self._p05_schemas.ApprovalStatus.APPROVED
                and self._has_prompt_injection(chunk.content) is None
            )
        ) + tuple(
            _normalize_text(claim.claim_text)
            for claim in self._store.claims
            if (
                claim.tenant_id == tenant_id
                and claim.sku_id in sku_set
                and claim.approval_status == self._p05_schemas.ApprovalStatus.APPROVED
                and claim.category == self._p05_schemas.ClaimCategory.ALLOWED
                and self._has_prompt_injection(claim.claim_text) is None
            )
        )

    def _check_cross_sku_name_leaks(
        self,
        candidate_text: str,
        tenant_id: str,
        target_sku_id: str,
    ) -> list[str]:
        """Phát hiện rò rỉ tên/mã của SKU khác trong cùng tenant khi đang ở chế độ `SINGLE_SKU`."""
        target_fact = self._store.facts.get(target_sku_id)
        excluded_terms: set[str] = set()
        if target_fact is not None:
            target_tokens = [
                tok for tok in _tokenize_name(target_fact.sku_name) if not _UNIT_TOKEN_RE.match(tok)
            ]
            excluded_terms.add(_normalize_text(target_fact.sku_name))
            for idx in range(0, max(0, len(target_tokens) - 1)):
                excluded_terms.add(" ".join(target_tokens[idx : idx + 2]))
            if len(target_tokens) >= 3:
                excluded_terms.add(" ".join(target_tokens[:3]))

        other_facts = [
            fact
            for fact in self._store.facts.values()
            if fact.tenant_id == tenant_id and fact.sku_id != target_sku_id
        ]
        if not other_facts:
            return []
        patterns = _build_unresolved_leak_patterns(other_facts, excluded_terms=frozenset(excluded_terms))
        return [sku_id for sku_id, pattern in patterns if pattern.search(candidate_text)]

    def _verify_single_sku(
        self,
        candidate: SpeechCandidate,
        verified_at: datetime,
    ) -> CandidateVerificationResult:
        """Kiểm định chế độ `SINGLE_SKU`: ủy quyền cho P05 kèm kiểm tra hiệu lực, echo, so sánh và rò rỉ SKU."""
        binding = candidate.sku_bindings[0]
        p05_cand = self._to_p05_candidate(candidate, binding)
        decision = self._gate.evaluate(p05_cand)

        reasons = [r.value for r in decision.reasons]
        details = list(decision.details)

        inj_pattern = self._has_prompt_injection(candidate.text)
        if inj_pattern is not None:
            reasons.append("PROMPT_INJECTION_DETECTED")
            details.append(f"Phát hiện dấu hiệu prompt injection trong lời thoại: '{inj_pattern}'.")

        fact = self._store.facts.get(binding.sku_id)
        if fact is not None and fact.tenant_id == candidate.tenant_id:
            if not _is_fact_within_validity_window(fact, verified_at):
                reasons.append("FACT_OUTSIDE_VALIDITY_WINDOW")
                details.append(
                    f"ProductFact của '{binding.sku_id}' ngoài cửa sổ hiệu lực tại {verified_at.isoformat()}."
                )
            fact_inj = self._find_fact_prompt_injection(fact)
            if fact_inj is not None:
                reasons.append("PROMPT_INJECTION_DETECTED")
                details.append(f"ProductFact của '{binding.sku_id}' chứa dấu hiệu prompt injection.")

        for eid in binding.cited_evidence_ids:
            chunk = self._store.chunks.get(eid)
            if chunk is not None and (
                self._has_prompt_injection(chunk.content) is not None
                or self._has_prompt_injection(chunk.section) is not None
            ):
                reasons.append("PROMPT_INJECTION_DETECTED")
                details.append(f"EvidenceChunk '{eid}' chứa dấu hiệu prompt injection.")

        sku_prohibited = self._collect_sku_prohibited_phrases(
            candidate.tenant_id, [binding.sku_id]
        )
        echo_result = self._echo_guard.check(
            candidate.text, sku_prohibited_phrases=sku_prohibited
        )
        if not echo_result.passed:
            if "PROHIBITED_CLAIM" not in reasons:
                reasons.append("PROHIBITED_CLAIM")
            details.append(
                f"ProhibitedEchoGuard chặn cụm từ bị cấm: {list(echo_result.matched_phrases)}."
            )

        # Kiểm tra từ khóa so sánh/tuyệt đối cảm tính chưa có căn cứ APPROVED cho SKU đơn lẻ.
        normalized_text = _normalize_text(candidate.text)
        approved_corpus = self._collect_approved_corpus(candidate.tenant_id, [binding.sku_id])
        for kw in (*_SUBJECTIVE_COMPARATIVE_KEYWORDS, "rẻ hơn", "đắt hơn"):
            if _compile_word_boundary_pattern(kw).search(normalized_text):
                if not any(kw in corpus_item for corpus_item in approved_corpus):
                    reasons.append("UNVERIFIED_COMPARATIVE_CLAIM")
                    details.append(
                        f"Phát hiện cụm từ so sánh/tuyệt đối chưa có bằng chứng kiểm chứng ở SINGLE_SKU: '{kw}'."
                    )

        leaked_skus = self._check_cross_sku_name_leaks(
            candidate_text=candidate.text,
            tenant_id=candidate.tenant_id,
            target_sku_id=binding.sku_id,
        )
        if leaked_skus:
            reasons.append("CROSS_SKU_VIOLATION")
            details.append(
                f"Lời thoại SINGLE_SKU '{binding.sku_id}' nhắc tới tên/mã SKU khác trong tenant: {leaked_skus}."
            )

        hygiene_res = check_spoken_text_hygiene(candidate.text)
        if not hygiene_res.passed:
            reasons.append("INTERNAL_METADATA_LEAK")
            details.extend(hygiene_res.violations)

        unique_reasons = tuple(dict.fromkeys(reasons))
        per_sku_decisions = {
            binding.sku_id: {
                "status": decision.status.value,
                "reasons": [r.value for r in decision.reasons],
                "details": list(decision.details),
                "checked_knowledge_version": decision.checked_knowledge_version,
                "checked_ocop_version": decision.checked_ocop_version,
                "checked_rights_version": decision.checked_rights_version,
            }
        }

        if not unique_reasons:
            decision_id = f"p05-allow-{candidate.candidate_id}"
            verified_cand = candidate.mark_verified(decision_id, verified_at)
            return CandidateVerificationResult(
                status=CandidateVerificationStatus.VERIFIED,
                candidate=verified_cand,
                reasons=(),
                details=tuple(details),
                gate_decision_id=decision_id,
                per_sku_decisions=per_sku_decisions,
            )

        rejected_cand = candidate.mark_rejected(unique_reasons)
        return CandidateVerificationResult(
            status=CandidateVerificationStatus.REJECTED,
            candidate=rejected_cand,
            reasons=unique_reasons,
            details=tuple(details),
            gate_decision_id=None,
            per_sku_decisions=per_sku_decisions,
        )

    def _verify_multi_sku_compare(
        self,
        candidate: SpeechCandidate,
        verified_at: datetime,
    ) -> CandidateVerificationResult:
        """Kiểm định chế độ `MULTI_SKU_COMPARE`: chạy P05 cho từng SKU + gán giá nghiêm ngặt + so sánh fail-closed."""
        reasons: list[str] = []
        details: list[str] = []
        per_sku_decisions: dict[str, dict[str, Any]] = {}

        bound_facts: dict[str, Any] = {}
        raw_decisions: list[tuple[SkuVersionBinding, Any]] = []
        for binding in candidate.sku_bindings:
            p05_cand = self._to_p05_candidate(candidate, binding)
            decision = self._gate.evaluate(p05_cand)
            raw_decisions.append((binding, decision))

            fact = self._store.facts.get(binding.sku_id)
            if fact is not None:
                bound_facts[binding.sku_id] = fact

            per_sku_decisions[binding.sku_id] = {
                "status": decision.status.value,
                "reasons": [r.value for r in decision.reasons],
                "details": list(decision.details),
                "checked_knowledge_version": decision.checked_knowledge_version,
                "checked_ocop_version": decision.checked_ocop_version,
                "checked_rights_version": decision.checked_rights_version,
            }

        inj_pattern = self._has_prompt_injection(candidate.text)
        if inj_pattern is not None:
            reasons.append("PROMPT_INJECTION_DETECTED")
            details.append(f"Phát hiện dấu hiệu prompt injection trong so sánh: '{inj_pattern}'.")

        for binding in candidate.sku_bindings:
            fact = bound_facts.get(binding.sku_id)
            if fact is not None and fact.tenant_id == candidate.tenant_id:
                if not _is_fact_within_validity_window(fact, verified_at):
                    reasons.append("FACT_OUTSIDE_VALIDITY_WINDOW")
                    details.append(
                        f"[{binding.sku_id}] ProductFact ngoài cửa sổ hiệu lực tại {verified_at.isoformat()}."
                    )
                fact_inj = self._find_fact_prompt_injection(fact)
                if fact_inj is not None:
                    reasons.append("PROMPT_INJECTION_DETECTED")
                    details.append(f"[{binding.sku_id}] ProductFact chứa dấu hiệu prompt injection.")

        # Kiểm tra gán giá theo từng SKU trước để biết PRICE_MISMATCH từ P05 đơn-SKU có phải nhiễu chéo giá hợp lệ hay không.
        price_ok, price_errors = self._verify_multi_sku_price_attribution(
            candidate=candidate,
            bound_facts=bound_facts,
        )
        if not price_ok:
            reasons.append("PRICE_MISMATCH")
            details.extend(price_errors)

        for binding, decision in raw_decisions:
            for block_reason in decision.reasons:
                # Chỉ triệt tiêu PRICE_MISMATCH đơn-SKU khi toàn bộ giá khai báo và giá trong text đã khớp chặt từng SKU.
                if block_reason == self._p05_schemas.BlockReason.PRICE_MISMATCH and price_ok:
                    continue
                reasons.append(block_reason.value)
            for detail in decision.details:
                if price_ok and "giá" in detail.lower() and "Phát hiện giá sai trong văn bản" in detail:
                    continue
                details.append(f"[{binding.sku_id}] {detail}")

        # Kiểm tra câu khẳng định so sánh (chỉ cho phép so sánh giá khách quan đúng chiều; cảm tính -> fail-closed).
        comp_ok, comp_errors = self._verify_comparative_claims(
            candidate=candidate,
            bound_facts=bound_facts,
        )
        if not comp_ok:
            reasons.append("UNVERIFIED_COMPARATIVE_CLAIM")
            details.extend(comp_errors)

        # Lớp phòng thủ bổ trợ chống cụm từ/claim bị cấm trên toàn bộ SKU tham gia so sánh.
        sku_prohibited = self._collect_sku_prohibited_phrases(
            candidate.tenant_id, candidate.sku_refs
        )
        echo_result = self._echo_guard.check(
            candidate.text, sku_prohibited_phrases=sku_prohibited
        )
        if not echo_result.passed:
            reasons.append("PROHIBITED_CLAIM")
            details.append(
                f"ProhibitedEchoGuard chặn cụm từ bị cấm trong so sánh: {list(echo_result.matched_phrases)}."
            )

        hygiene_res = check_spoken_text_hygiene(candidate.text)
        if not hygiene_res.passed:
            reasons.append("INTERNAL_METADATA_LEAK")
            details.extend(hygiene_res.violations)

        unique_reasons = tuple(dict.fromkeys(reasons))
        if not unique_reasons:
            decision_id = f"p05-multi-allow-{candidate.candidate_id}"
            verified_cand = candidate.mark_verified(decision_id, verified_at)
            return CandidateVerificationResult(
                status=CandidateVerificationStatus.VERIFIED,
                candidate=verified_cand,
                reasons=(),
                details=tuple(details),
                gate_decision_id=decision_id,
                per_sku_decisions=per_sku_decisions,
            )

        rejected_cand = candidate.mark_rejected(unique_reasons)
        return CandidateVerificationResult(
            status=CandidateVerificationStatus.REJECTED,
            candidate=rejected_cand,
            reasons=unique_reasons,
            details=tuple(details),
            gate_decision_id=None,
            per_sku_decisions=per_sku_decisions,
        )

    def _verify_multi_sku_price_attribution(
        self,
        candidate: SpeechCandidate,
        bound_facts: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Kiểm tra nghiêm ngặt mọi con số giá trong `MULTI_SKU_COMPARE` thuộc đúng SKU tương ứng."""
        errors: list[str] = []

        for binding in candidate.sku_bindings:
            fact = bound_facts.get(binding.sku_id)
            if fact is None:
                errors.append(f"Thiếu ProductFact cho SKU '{binding.sku_id}' khi đối chiếu giá.")
                continue
            if binding.stated_price_vnd is not None and binding.stated_price_vnd != fact.price_vnd:
                errors.append(
                    f"Sai giá khai báo cho '{binding.sku_id}': candidate ghi {binding.stated_price_vnd:,}đ, "
                    f"giá chuẩn là {fact.price_vnd:,}đ."
                )

        found_prices = self._p05_gate.extract_prices_vnd(candidate.text)
        if not found_prices:
            return (len(errors) == 0), errors

        if len(bound_facts) != len(candidate.sku_bindings):
            errors.append("Không thể gán giá đa SKU khi thiếu ProductFact của một hoặc nhiều SKU.")
            return False, errors

        sku_patterns = _build_unique_sku_alias_patterns(bound_facts)
        clauses = self._split_text_into_price_clauses(candidate.text)

        attributed_prices: list[int] = []
        for clause in clauses:
            clause_prices = self._p05_gate.extract_prices_vnd(clause)
            if not clause_prices:
                continue
            attributed_prices.extend(clause_prices)

            matched_skus = [
                sku_id for sku_id, pattern in sku_patterns.items() if pattern.search(clause)
            ]
            if len(matched_skus) == 0:
                errors.append(
                    f"Phát hiện giá {clause_prices} trong mệnh đề không nêu rõ SKU nào: '{clause.strip()}'."
                )
                continue
            if len(matched_skus) > 1:
                distinct_prices = {bound_facts[sku_id].price_vnd for sku_id in matched_skus}
                if len(distinct_prices) > 1:
                    errors.append(
                        f"Mệnh đề nhắc nhiều SKU có mức giá khác nhau ({matched_skus}) nên gán giá mơ hồ: '{clause.strip()}'."
                    )
                    continue
            target_sku = matched_skus[0]
            expected_price = bound_facts[target_sku].price_vnd
            for price in clause_prices:
                if price != expected_price:
                    errors.append(
                        f"Sai giá trong mệnh đề cho '{target_sku}': phát hiện {price:,}đ, "
                        f"giá chuẩn là {expected_price:,}đ."
                    )

        # Phòng trường hợp regex tách mệnh đề làm sót hoặc biến đổi giá so với toàn văn.
        if sorted(attributed_prices) != sorted(found_prices):
            errors.append(
                f"Không thể đối chiếu đầy đủ các mức giá trích xuất {found_prices} qua từng mệnh đề."
            )

        return (len(errors) == 0), errors

    def _split_text_into_price_clauses(self, text: str) -> list[str]:
        """Tách văn bản thành các mệnh đề nhỏ để kiểm tra gắn kết SKU–giá không mơ hồ."""
        punct_segments = [seg.strip() for seg in _CLAUSE_PUNCT_SPLIT_RE.split(text) if seg.strip()]
        clauses: list[str] = []
        for segment in punct_segments:
            sub_segments = [
                sub.strip() for sub in _CLAUSE_CONNECTOR_SPLIT_RE.split(segment) if sub.strip()
            ]
            for sub in sub_segments:
                # Nếu một vế chứa nhiều hơn 1 mức giá nối bằng "và", tách tiếp để kiểm tra từng vế.
                if len(self._p05_gate.extract_prices_vnd(sub)) > 1:
                    clauses.extend(
                        part.strip() for part in _AND_CONNECTOR_SPLIT_RE.split(sub) if part.strip()
                    )
                else:
                    clauses.append(sub)
        return clauses

    def _verify_comparative_claims(
        self,
        candidate: SpeechCandidate,
        bound_facts: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Kiểm định câu so sánh đa SKU theo nguyên tắc fail-closed.

        - Từ khóa cảm tính/hiệu quả (`tốt hơn`, `ngon hơn`, `vượt trội`, ...): bị chặn trừ khi
          có sẵn trong claim `ALLOWED`/`APPROVED` hoặc chunk `APPROVED` của SKU đang gắn.
        - Từ khóa so sánh giá khách quan (`rẻ hơn`, `đắt hơn`, `cao hơn`, `thấp hơn` trong ngữ cảnh giá):
          chỉ cho phép khi TẤT CẢ `sku_bindings` đều khai báo `stated_price_vnd` khớp `ProductFact`
          và chiều so sánh khớp với `fact_left.price_vnd` vs `fact_right.price_vnd`.
        """
        errors: list[str] = []
        normalized_text = _normalize_text(candidate.text)

        approved_comparative_corpus = self._collect_approved_corpus(
            candidate.tenant_id, candidate.sku_refs
        )

        # 1. Chặn mọi từ khóa so sánh cảm tính/tuyệt đối nếu chưa có bằng chứng APPROVED trực tiếp.
        for kw in _SUBJECTIVE_COMPARATIVE_KEYWORDS:
            if _compile_word_boundary_pattern(kw).search(normalized_text):
                if not any(kw in corpus_item for corpus_item in approved_comparative_corpus):
                    errors.append(
                        f"Phát hiện cụm từ so sánh chưa có bằng chứng kiểm chứng: '{kw}'."
                    )

        # 2. Kiểm tra các cụm so sánh giá khách quan theo từng câu.
        sku_patterns = _build_unique_sku_alias_patterns(bound_facts) if bound_facts else {}
        sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(normalized_text) if s.strip()]

        for sentence in sentences:
            for kw in _OBJECTIVE_PRICE_COMPARATIVE_KEYWORDS:
                kw_pattern = _compile_word_boundary_pattern(kw)
                for match in kw_pattern.finditer(sentence):
                    is_price_cmp = kw in ("rẻ hơn", "đắt hơn") or self._is_price_context(sentence)
                    if not is_price_cmp:
                        if not any(kw in corpus_item for corpus_item in approved_comparative_corpus):
                            errors.append(
                                f"So sánh '{kw}' ngoài ngữ cảnh giá đã xác minh chưa có căn cứ APPROVED."
                            )
                        continue

                    if not self._all_bindings_have_verified_prices(candidate, bound_facts):
                        errors.append(
                            f"So sánh giá '{kw}' yêu cầu mọi SKU gắn kèm phải có stated_price_vnd khớp ProductFact."
                        )
                        continue

                    negation_re = re.compile(
                        rf"(?<!\w)(?:không|chưa|chẳng)(?:\s+\w+){{0,2}}\s+{re.escape(kw)}(?!\w)",
                        re.IGNORECASE,
                    )
                    if negation_re.search(sentence):
                        errors.append(
                            f"Phát hiện câu so sánh giá phủ định/mơ hồ ('{kw}' kèm phủ định) không bảo đảm rõ nghĩa."
                        )
                        continue

                    resolved_pair = self._resolve_compared_sku_pair(
                        sentence=sentence,
                        kw_start=match.start(),
                        kw_end=match.end(),
                        sku_patterns=sku_patterns,
                    )
                    if resolved_pair is None:
                        errors.append(
                            f"Không xác định được rạch ròi cặp SKU cho so sánh giá '{kw}' trong câu: '{sentence}'."
                        )
                        continue

                    left_sku, right_sku = resolved_pair
                    left_price = bound_facts[left_sku].price_vnd
                    right_price = bound_facts[right_sku].price_vnd
                    if kw in ("rẻ hơn", "thấp hơn") and not (left_price < right_price):
                        errors.append(
                            f"Ngược chiều so sánh giá: nêu '{left_sku}' ({left_price:,}đ) {kw} "
                            f"'{right_sku}' ({right_price:,}đ)."
                        )
                    elif kw in ("đắt hơn", "cao hơn") and not (left_price > right_price):
                        errors.append(
                            f"Ngược chiều so sánh giá: nêu '{left_sku}' ({left_price:,}đ) {kw} "
                            f"'{right_sku}' ({right_price:,}đ)."
                        )

        return (len(errors) == 0), errors

    def _is_price_context(self, sentence: str) -> bool:
        """Nhận diện câu có ngữ cảnh giá (`giá`, `đồng`, `vnđ`, hoặc con số giá trích xuất)."""
        if self._p05_gate.extract_prices_vnd(sentence):
            return True
        return any(hint in sentence for hint in _PRICE_CONTEXT_HINTS)

    @staticmethod
    def _all_bindings_have_verified_prices(
        candidate: SpeechCandidate,
        bound_facts: dict[str, Any],
    ) -> bool:
        """Kiểm tra toàn bộ SKU trong `MULTI_SKU_COMPARE` đều khai báo giá đúng với `ProductFact`."""
        if len(bound_facts) != len(candidate.sku_bindings):
            return False
        for binding in candidate.sku_bindings:
            fact = bound_facts.get(binding.sku_id)
            if fact is None or binding.stated_price_vnd is None:
                return False
            if binding.stated_price_vnd != fact.price_vnd:
                return False
        return True

    @staticmethod
    def _resolve_compared_sku_pair(
        sentence: str,
        kw_start: int,
        kw_end: int,
        sku_patterns: dict[str, re.Pattern[str]],
    ) -> Optional[tuple[str, str]]:
        """Phân giải `(left_sku, right_sku)` trong cấu trúc `left_sku <kw> right_sku` hoặc `so với right_sku, left_sku <kw>`."""
        mentions: list[tuple[int, int, str]] = []
        for sku_id, pattern in sku_patterns.items():
            for m in pattern.finditer(sentence):
                mentions.append((m.start(), m.end(), sku_id))
        mentions.sort(key=lambda item: item[0])

        before_kw = [item for item in mentions if item[1] <= kw_start]
        after_kw = [item for item in mentions if item[0] >= kw_end]

        if before_kw and after_kw:
            left_sku = before_kw[-1][2]
            right_sku = after_kw[0][2]
            if left_sku != right_sku:
                return left_sku, right_sku
            return None

        # Hỗ trợ cấu trúc tiếng Việt "So với <SKU_B>, <SKU_A> rẻ hơn/đắt hơn".
        so_voi_match = re.search(r"(?<!\w)so với(?!\w)", sentence[:kw_start], re.IGNORECASE)
        if so_voi_match is not None and len(before_kw) >= 2:
            after_so_voi = [item for item in before_kw if item[0] >= so_voi_match.end()]
            if len(after_so_voi) >= 2:
                right_sku = after_so_voi[0][2]
                left_sku = after_so_voi[-1][2]
                if left_sku != right_sku:
                    return left_sku, right_sku
        return None

    def _verify_shop_wide_policy(
        self,
        candidate: SpeechCandidate,
    ) -> CandidateVerificationResult:
        """Kiểm định chế độ `SHOP_WIDE_POLICY`: chạy guard bổ trợ và luôn fail-closed khi P05 chưa hỗ trợ."""
        reasons: list[str] = []
        details: list[str] = []

        echo_result = self._echo_guard.check(candidate.text)
        if not echo_result.passed:
            reasons.append("PROHIBITED_CLAIM")
            details.append(
                f"ProhibitedEchoGuard phát hiện cụm từ bị cấm: {list(echo_result.matched_phrases)}."
            )

        inj_pattern = self._has_prompt_injection(candidate.text)
        if inj_pattern is not None:
            reasons.append("PROMPT_INJECTION_DETECTED")
            details.append(f"Phát hiện dấu hiệu prompt injection: '{inj_pattern}'.")

        found_prices = self._p05_gate.extract_prices_vnd(candidate.text)
        if found_prices:
            reasons.append("PRICE_MISMATCH")
            details.append(
                f"SHOP_WIDE_POLICY không được phép nêu giá sản phẩm chưa qua kiểm định SKU: {found_prices}."
            )

        reasons.append("UNSUPPORTED_SHOP_POLICY_VERIFICATION")
        details.append(
            "PublicationGate của P05 hiện yêu cầu sku_id cụ thể và chưa có cổng kiểm chứng chính sách toàn shop (fail-closed)."
        )

        unique_reasons = tuple(dict.fromkeys(reasons))
        rejected_cand = candidate.mark_rejected(unique_reasons)
        return CandidateVerificationResult(
            status=CandidateVerificationStatus.REJECTED,
            candidate=rejected_cand,
            reasons=unique_reasons,
            details=tuple(details),
            gate_decision_id=None,
            per_sku_decisions={},
        )

    def _verify_unresolved_sku(
        self,
        candidate: SpeechCandidate,
        verified_at: datetime,
    ) -> CandidateVerificationResult:
        """Kiểm định chế độ `UNRESOLVED_SKU`: tuyệt đối không gọi P05 với `active_sku_id`, chặn rò rỉ SKU."""
        details: list[str] = []
        violation_found = False

        all_tenant_prohibited = tuple(
            claim.claim_text
            for claim in self._store.claims
            if (
                claim.tenant_id == candidate.tenant_id
                and claim.category == self._p05_schemas.ClaimCategory.PROHIBITED
            )
        )
        echo_result = self._echo_guard.check(
            candidate.text, sku_prohibited_phrases=all_tenant_prohibited
        )
        if not echo_result.passed:
            violation_found = True
            details.append(
                f"Vi phạm cụm từ bị cấm trong UNRESOLVED_SKU: {list(echo_result.matched_phrases)}."
            )

        inj_pattern = self._has_prompt_injection(candidate.text)
        if inj_pattern is not None:
            violation_found = True
            details.append(f"Phát hiện dấu hiệu prompt injection: '{inj_pattern}'.")

        found_prices = self._p05_gate.extract_prices_vnd(candidate.text)
        if found_prices:
            violation_found = True
            details.append(
                f"UNRESOLVED_SKU không được phép nhắc giá tiền: {found_prices}."
            )

        if "ocop" in candidate.text.lower():
            violation_found = True
            details.append("UNRESOLVED_SKU không được phép nhắc chứng nhận OCOP.")

        tenant_facts = [
            fact for fact in self._store.facts.values() if fact.tenant_id == candidate.tenant_id
        ]
        leak_patterns = _build_unresolved_leak_patterns(tenant_facts)
        for sku_id, pattern in leak_patterns:
            if pattern.search(candidate.text):
                violation_found = True
                details.append(
                    f"UNRESOLVED_SKU làm rò rỉ tên hoặc mã SKU '{sku_id}' khi chưa phân giải sản phẩm."
                )

        hygiene_res = check_spoken_text_hygiene(candidate.text)
        if not hygiene_res.passed:
            violation_found = True
            details.extend(hygiene_res.violations)

        if not violation_found:
            decision_id = f"p06-unresolved-safe-guard-{candidate.candidate_id}"
            verified_cand = candidate.mark_verified(decision_id, verified_at)
            return CandidateVerificationResult(
                status=CandidateVerificationStatus.VERIFIED,
                candidate=verified_cand,
                reasons=(),
                details=("Đã qua zero-leak guard cho câu hỏi làm rõ/từ chối an toàn (UNRESOLVED_SKU).",),
                gate_decision_id=decision_id,
                per_sku_decisions={},
            )

        reasons = ("UNSAFE_UNRESOLVED_SKU_CONTENT",)
        rejected_cand = candidate.mark_rejected(reasons)
        return CandidateVerificationResult(
            status=CandidateVerificationStatus.REJECTED,
            candidate=rejected_cand,
            reasons=reasons,
            details=tuple(details),
            gate_decision_id=None,
            per_sku_decisions={},
        )
