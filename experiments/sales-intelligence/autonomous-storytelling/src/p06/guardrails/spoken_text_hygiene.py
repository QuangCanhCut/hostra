"""Bộ kiểm tra vệ sinh văn bản lời thoại (`spoken_text_hygiene.py`) chống rò rỉ metadata nội bộ (R01).

1. File này giải quyết vấn đề gì?
   Ngăn lỗi rò rỉ định danh kỹ thuật nội bộ (`ev-...`, `clm-...`, `SKU-...`, `topic-...`),
   mảnh JSON hoặc tên trường schema vào lời thoại tiếng Việt trước khi phát TTS.
2. Trách nhiệm chính của module là gì?
   Cung cấp hàm thuần `check_spoken_text_hygiene(text)` kiểm tra văn bản theo danh sách mẫu
   cấm và trả về `SpokenTextHygieneResult` (pass/fail kèm danh sách vi phạm cụ thể).
3. Module này liên kết với các thành phần nào?
   Được gọi trong LangGraph (`agent/nodes/_common.py`), `ScriptFirstBaseline`
   (`baselines/script_first.py`), và lớp phòng thủ chiều sâu `P05KnowledgeAdapter`.
4. Input và output chính là gì?
   Input: chuỗi `text` lời thoại cần kiểm tra;
   Output: `SpokenTextHygieneResult(passed, violations)`.
5. Có những constraints hoặc invariants quan trọng nào?
   - Tuyệt đối KHÔNG âm thầm xóa hoặc sửa văn bản đầu vào (tránh làm biến đổi nghĩa rồi bỏ qua
     kiểm chứng); chỉ phát hiện và trả lỗi để nhánh gọi từ chối hoặc yêu cầu viết lại có kiểm soát.
"""

from __future__ import annotations

import re
from typing import Final

from pydantic import BaseModel, ConfigDict

# Mẫu phát hiện các định danh nội bộ không bao giờ được đọc thành lời cho người xem livestream.
_INTERNAL_ID_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    (
        "RAW_EVIDENCE_OR_SYSTEM_ID",
        re.compile(
            r"(?<![A-Za-z0-9_])(?:ev|clm|topic|arc|cand|chunk|turn|plan|fb|sess)-[a-z0-9][a-z0-9-]*\b",
            re.IGNORECASE,
        ),
    ),
    (
        "RAW_SKU_CODE",
        re.compile(
            r"(?<![A-Za-z0-9_])SKU-[A-Z0-9][A-Z0-9-]*\b",
            re.IGNORECASE,
        ),
    ),
)

# Mẫu phát hiện mảnh JSON, thẻ XML nội bộ hoặc tên trường DTO lọt vào lời thoại.
_JSON_OBJECT_OR_KEY_RE: Final[re.Pattern[str]] = re.compile(
    r"\{[^{}]*\"[^\"]+\"\s*:[^{}]*\}|\"[a-z_]{3,}\"\s*:"
)

_INTERNAL_FIELD_NAMES: Final[tuple[str, ...]] = (
    "cited_evidence_ids",
    "covered_claim_ids",
    "stated_price_vnd",
    "mentions_ocop",
    "semantic_breakpoint",
    "breakpoint_type",
    "active_sku_id",
    "fact_refs",
    "allowed_claim_ids",
    "approved_chunks",
    "untrusted_knowledge_data",
    "sku_evidence",
    "talking_points",
    "prohibited_claims",
    "allowed_claims",
)

_INTERNAL_FIELD_RE: Final[re.Pattern[str]] = re.compile(
    r"</?untrusted_knowledge_data>|(?<![A-Za-z0-9_])(?:"
    + "|".join(re.escape(name) for name in _INTERNAL_FIELD_NAMES)
    + r")(?![A-Za-z0-9_])",
    re.IGNORECASE,
)


class SpokenTextHygieneResult(BaseModel):
    """Kết quả kiểm tra vệ sinh lời thoại phát sóng (không chứa metadata nội bộ).

    Attributes:
        passed: `True` nếu lời thoại sạch, không chứa ID nội bộ hay mảnh cấu trúc JSON.
        violations: Danh sách mô tả từng vi phạm phát hiện được (rỗng nếu `passed=True`).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    passed: bool
    violations: tuple[str, ...] = ()


def check_spoken_text_hygiene(text: str) -> SpokenTextHygieneResult:
    """Kiểm tra lời thoại có làm rò rỉ ID nội bộ, tên trường schema hay mảnh JSON hay không.

    Hàm hoạt động thuần túy (pure function), không chỉnh sửa chuỗi `text` đầu vào để bảo đảm
    mọi thay đổi câu chữ đều phải đi qua quy trình viết lại và tái kiểm định đầy đủ.
    """
    if not isinstance(text, str) or not text.strip():
        return SpokenTextHygieneResult(
            passed=False,
            violations=("INTERNAL_METADATA_LEAK: Lời thoại rỗng hoặc sai kiểu dữ liệu.",),
        )

    violations: list[str] = []

    for label, pattern in _INTERNAL_ID_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            unique_matches = ", ".join(dict.fromkeys(matches))
            violations.append(
                f"INTERNAL_METADATA_LEAK ({label}): Không được đưa mã nội bộ [{unique_matches}] vào lời thoại."
            )

    if _JSON_OBJECT_OR_KEY_RE.search(text):
        violations.append(
            "INTERNAL_METADATA_LEAK (JSON_FRAGMENT): Lời thoại chứa mảnh cú pháp JSON."
        )

    field_matches = _INTERNAL_FIELD_RE.findall(text)
    if field_matches:
        unique_fields = ", ".join(dict.fromkeys(field_matches))
        violations.append(
            f"INTERNAL_METADATA_LEAK (INTERNAL_FIELD): Lời thoại chứa tên trường hoặc thẻ nội bộ [{unique_fields}]."
        )

    return SpokenTextHygieneResult(
        passed=(len(violations) == 0),
        violations=tuple(violations),
    )
