"""Bộ lọc phòng thủ theo lớp (defense-in-depth) chống lặp cụm từ bị cấm và bẫy nhại câu hỏi y tế.

1. File này giải quyết vấn đề gì?
   Ngăn chặn tình huống LLM vô tình lặp lại (echo) cụm từ công dụng như thuốc từ bình luận
   của người xem (ví dụ: "Mật ong có chữa khỏi đau dạ dày không?" -> "Dạ mật ong không chữa khỏi đau dạ dày...")
   hoặc chèn cụm từ bị cấm kèm khoảng trắng/chữ hoa bất thường.
2. Trách nhiệm chính của module là gì?
   Chuẩn hóa khoảng trắng và chữ thường (`" ".join(text.lower().split())`), đối chiếu chuỗi con
   với danh sách cụm từ cấm mặc định của P05 và cụm từ cấm riêng theo từng SKU.
3. Module này liên kết với các thành phần nào?
   Được sử dụng bởi `P05KnowledgeAdapter` (`adapters/p05_knowledge_adapter.py`) như một lớp
   bảo vệ bổ trợ song song với `PublicationGate`.
4. Input và output chính là gì?
   Input là văn bản lời thoại (`text`) và danh sách cụm từ cấm theo SKU;
   Output là `ProhibitedEchoResult` (`passed`, `matched_phrases`).
5. Có những constraints hoặc invariants quan trọng nào?
   - **QUAN TRỌNG:** Bộ lọc từ khóa/chuỗi con CHỈ là lớp phòng thủ bổ trợ (**defense-in-depth**),
     TUYỆT ĐỐI KHÔNG phải bằng chứng duy nhất chứng minh toàn bộ tuyên bố (claims) đều an toàn!
   - Phải hoạt động theo nguyên tắc fail-closed khi phát hiện bất kỳ cụm từ cấm nào.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, StrictBool, model_validator


def _normalize_for_match(text: str) -> str:
    """Chuẩn hóa NFC, chữ thường và gộp mọi khoảng trắng liên tiếp thành một dấu cách.

    Lý do kỹ thuật: Kẻ tấn công hoặc LLM có thể dùng tổ hợp Unicode khác nhau (NFD vs NFC)
    hoặc nhiều dấu cách/xuống dòng giữa các từ (ví dụ `"chữa   bệnh"`) làm trượt phép so sánh thô.

    Args:
        text: Chuỗi văn bản cần chuẩn hóa.

    Returns:
        str: Chuỗi đã chuẩn hóa NFC, chữ thường và khoảng trắng đơn.
    """
    nfc_text = unicodedata.normalize("NFC", text)
    return " ".join(nfc_text.lower().split())


def _normalize_alnum_tokens(text: str) -> str:
    """Chuẩn hóa NFC và trích xuất chuỗi token chữ/số bỏ dấu câu để chặn lách bằng dấu câu."""
    nfc_text = unicodedata.normalize("NFC", text).lower()
    tokens = re.findall(r"[^\W_]+", nfc_text, flags=re.UNICODE)
    return " ".join(tokens)


class ProhibitedEchoResult(BaseModel):
    """Kết quả kiểm tra cụm từ bị cấm / bẫy nhại câu hỏi từ bộ lọc `ProhibitedEchoGuard`.

    Attributes:
        passed: `True` chỉ khi không phát hiện bất kỳ cụm từ bị cấm nào.
        matched_phrases: Danh sách cụm từ bị cấm đã khớp trong văn bản (rỗng khi `passed=True`).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    passed: StrictBool
    matched_phrases: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_consistency(self) -> ProhibitedEchoResult:
        """Bảo đảm `passed` luôn nhất quán tuyệt đối với danh sách `matched_phrases`.

        Returns:
            ProhibitedEchoResult: Kết quả hợp lệ.

        Raises:
            ValueError: Nếu `passed=True` nhưng vẫn có `matched_phrases` hoặc ngược lại.
        """
        if self.passed and self.matched_phrases:
            raise ValueError("ProhibitedEchoResult với passed=True không được có matched_phrases.")
        if not self.passed and not self.matched_phrases:
            raise ValueError("ProhibitedEchoResult với passed=False bắt buộc phải có matched_phrases.")
        return self


class ProhibitedEchoGuard:
    """Bộ kiểm tra chuỗi con cụm từ bị cấm (defense-in-depth) chống bẫy nhại câu hỏi y tế.

    Cảnh báo thiết kế: Bộ lọc này chỉ là **lớp phòng thủ bổ trợ (defense-in-depth)** nhằm
    bắt nhanh các biến thể khoảng trắng/chữ hoa và lỗi nhại lại cụm từ cấm từ câu hỏi của khách
    (medical-question echo trap). Bộ lọc này KHÔNG thay thế `PublicationGate` và KHÔNG phải
    bằng chứng duy nhất chứng minh toàn bộ nội dung phát ngôn đều an toàn.
    """

    def __init__(self, extra_prohibited_phrases: Sequence[str] = ()) -> None:
        """Khởi tạo bộ lọc với danh sách cụm từ cấm nền tảng (ví dụ từ `DEFAULT_PROHIBITED_PHRASES`).

        Args:
            extra_prohibited_phrases: Tập cụm từ bị cấm dùng chung cho mọi kiểm tra.
        """
        self._base_phrases: tuple[str, ...] = self._deduplicate_normalized(extra_prohibited_phrases)

    @staticmethod
    def _deduplicate_normalized(phrases: Sequence[str]) -> tuple[str, ...]:
        """Chuẩn hóa và loại bỏ trùng lặp cụm từ nhưng giữ nguyên thứ tự khai báo."""
        seen: set[str] = set()
        ordered: list[str] = []
        for phrase in phrases:
            normalized = _normalize_for_match(phrase)
            if normalized and normalized not in seen:
                seen.add(normalized)
                ordered.append(normalized)
        return tuple(ordered)

    def check(
        self,
        text: str,
        sku_prohibited_phrases: Sequence[str] = (),
    ) -> ProhibitedEchoResult:
        """Kiểm tra văn bản lời thoại có chứa cụm từ bị cấm hay nhại cụm từ y tế hay không.

        Args:
            text: Văn bản lời thoại cần kiểm tra.
            sku_prohibited_phrases: Cụm từ/tuyên bố bị cấm bổ sung riêng cho các SKU liên quan.

        Returns:
            ProhibitedEchoResult: `passed=True` nếu sạch; `passed=False` kèm `matched_phrases` nếu vi phạm.
        """
        normalized_text = _normalize_for_match(text)
        token_text = f" {_normalize_alnum_tokens(text)} "
        combined_phrases = self._deduplicate_normalized(
            (*self._base_phrases, *sku_prohibited_phrases)
        )
        matched_list: list[str] = []
        for phrase in combined_phrases:
            if phrase in normalized_text:
                matched_list.append(phrase)
                continue
            token_phrase = _normalize_alnum_tokens(phrase)
            if token_phrase and f" {token_phrase} " in token_text:
                matched_list.append(phrase)

        matched = tuple(matched_list)
        return ProhibitedEchoResult(
            passed=(len(matched) == 0),
            matched_phrases=matched,
        )
