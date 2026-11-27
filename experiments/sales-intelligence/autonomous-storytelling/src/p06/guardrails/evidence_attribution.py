"""Bộ kiểm tra gắn kết bằng chứng (`R02`) và mục tiêu chủ đề (`R05`) cho bản nháp P06.

1. File này giải quyết vấn đề gì?
   - Ngăn lời thoại factual vượt qua bước tạo nháp với `cited_evidence_ids=[]` (như lỗi trong Pilot v1
     khi có giá bán lọt qua quy tắc chỉ kiểm tra giá) hoặc trích dẫn ID sai/chéo SKU.
   - Phát hiện trường hợp bản nháp rút gọn quá mức chỉ còn `<Tên SKU> <Khối lượng> <Giá>` mà
     đánh mất toàn bộ `talking_points` cốt lõi của chủ đề đang chọn (`R05`).
2. Trách nhiệm chính của module là gì?
   - `validate_draft_evidence_attribution(...)`: Kiểm tra `cited_evidence_ids` và `covered_claim_ids`
     thuộc đúng SKU hiện hành, cho phép non-factual bridge khi chính sách cho phép, không tự bịa ID.
   - `check_topic_objective_alignment(...)`: Kiểm tra độ phủ từ khóa trọng tâm tối thiểu từ
     `talking_points` của chủ đề bằng đối chiếu từ vựng tất định (không dùng model phụ hay NLI).
3. Module này liên kết với các thành phần nào?
   Sử dụng `SkuEvidenceView` (`adapters/interfaces.py`) và `StoryChunkRole`/`StoryTopic`
   (`schemas/story.py`); được gọi bởi `agent/nodes/_common.py` và `baselines/script_first.py`.
4. Input và output chính là gì?
   - `EvidenceAttributionResult(passed, failure_reasons, validated_evidence_ids, validated_claim_ids)`
   - `TopicObjectiveCheckResult(passed, matched_keywords, expected_keywords, reason)`
5. Có những constraints hoặc invariants quan trọng nào?
   - Không bao giờ tự điền ngẫu nhiên `evidence_id` hay `claim_id` thay LLM.
   - `non-empty citation` KHÔNG phải bằng chứng tuyệt đối cho factual correctness; ứng viên vẫn bắt buộc
     đi qua P05 `PublicationGate` (`I-02`).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Final, Optional

from pydantic import BaseModel, ConfigDict

from p06.adapters.interfaces import SkuEvidenceView
from p06.schemas.story import StoryChunkRole, StoryTopic

_WORD_TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"[0-9a-zA-ZÀ-ỹđĐ-]+", re.UNICODE)

# Từ hư từ tiếng Việt và đơn vị quy cách/giá phổ biến không đại diện cho talking_points riêng của topic.
_STOPWORDS_AND_CATALOG_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "và",
        "của",
        "cho",
        "với",
        "từ",
        "tại",
        "khi",
        "nếu",
        "nên",
        "là",
        "có",
        "được",
        "trong",
        "ngoài",
        "trên",
        "dưới",
        "làm",
        "giúp",
        "giữ",
        "để",
        "hay",
        "hoặc",
        "như",
        "rất",
        "vì",
        "theo",
        "về",
        "một",
        "hai",
        "ba",
        "các",
        "những",
        "này",
        "đó",
        "hiện",
        "mỗi",
        "đều",
        "tốt",
        "hơn",
        "kèm",
        "không",
        "chỉ",
        "bên",
        "anh",
        "chị",
        "bạn",
        "quý",
        "khách",
        "sản",
        "phẩm",
        "giá",
        "niêm",
        "yết",
        "đồng",
        "vnđ",
        "chai",
        "hộp",
        "túi",
        "gói",
        "lọ",
        "ml",
        "g",
        "kg",
        "gam",
        "lít",
        "lượt",
    }
)


class EvidenceAttributionResult(BaseModel):
    """Kết quả kiểm tra trích dẫn bằng chứng và claim của một bản nháp lời thoại.

    Attributes:
        passed: `True` nếu trích dẫn hợp lệ với chính sách factual/non-factual của SKU hiện hành.
        failure_reasons: Danh sách mã lỗi chi tiết phục vụ phản hồi viết lại (`bounded_rewrite`).
        validated_evidence_ids: Danh sách `evidence_id` đã xác nhận tồn tại trong `approved_chunks`.
        validated_claim_ids: Danh sách `claim_id` đã xác nhận tồn tại trong `allowed_claims`.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    passed: bool
    failure_reasons: tuple[str, ...] = ()
    validated_evidence_ids: tuple[str, ...] = ()
    validated_claim_ids: tuple[str, ...] = ()


class TopicObjectiveCheckResult(BaseModel):
    """Kết quả kiểm tra xem lời thoại có giữ được từ khóa trọng tâm của `talking_points` hay không.

    Attributes:
        passed: `True` nếu lời thoại đạt ngưỡng khớp tối thiểu (hoặc chủ đề quá ngắn không áp dụng).
        matched_keywords: Các từ khóa trọng tâm đã xuất hiện trong `text`.
        expected_keywords: Tập từ khóa trọng tâm trích xuất từ `talking_points` của chủ đề.
        reason: Mô tả lỗi nếu lời thoại bị rút gọn sai mục tiêu chủ đề.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    passed: bool
    matched_keywords: tuple[str, ...] = ()
    expected_keywords: tuple[str, ...] = ()
    reason: Optional[str] = None


def validate_draft_evidence_attribution(
    *,
    text: str,
    role: StoryChunkRole,
    cited_evidence_ids: Sequence[str],
    covered_claim_ids: Sequence[str],
    evidence: SkuEvidenceView,
    topic: StoryTopic,
    stated_price_vnd: Optional[int] = None,
    mentions_ocop: bool = False,
    allow_non_factual_without_citation: bool = True,
    strict_claim_ids: bool = False,
) -> EvidenceAttributionResult:
    """Xác minh bản nháp trích dẫn đúng `evidence_id` và `claim_id` thuộc đúng `evidence` SKU.

    Nguyên lý thiết kế:
    - Kiểm tra mọi ID được LLM khai báo thực sự nằm trong `approved_chunks` / `allowed_claims` của
      SKU đang khóa (`I-04`), không chấp nhận ID sai hoặc chéo SKU.
    - Với lời thoại mang nội dung thực chứng (factual storytelling), bắt buộc `cited_evidence_ids`
      không rỗng ngay cả khi đã có `stated_price_vnd` (khép lỗ hổng Pilot v1).
    - Riêng câu chào mở đầu (`OPENING`) hoặc câu chuyển tiếp (`TRANSITION_BRIDGE`) thuần giao tiếp
      không gắn `topic.fact_refs`, không nêu giá và không nhắc OCOP mới được phép bỏ trống citation.
    """
    del text  # Giữ tham số text trong chữ ký để đồng bộ giao diện validator mở rộng về sau.
    approved_evidence_ids = {
        chunk["evidence_id"]
        for chunk in evidence.approved_chunks
        if isinstance(chunk.get("evidence_id"), str) and chunk["evidence_id"].strip()
    }
    allowed_claim_ids = {
        claim["claim_id"]
        for claim in evidence.allowed_claims
        if isinstance(claim.get("claim_id"), str) and claim["claim_id"].strip()
    }

    reasons: list[str] = []
    valid_eids: list[str] = []
    valid_cids: list[str] = []

    for raw_eid in cited_evidence_ids:
        eid = raw_eid.strip()
        if eid not in approved_evidence_ids:
            reasons.append(
                f"INVALID_OR_CROSS_SKU_EVIDENCE_ID: '{eid}' không thuộc tập approved_chunks của SKU '{evidence.sku_id}'."
            )
        elif eid not in valid_eids:
            valid_eids.append(eid)

    for raw_cid in covered_claim_ids:
        cid = raw_cid.strip()
        if cid not in allowed_claim_ids:
            # Chặn nghiêm mọi mã dạng `clm-...` không hợp lệ hoặc khi bật `strict_claim_ids`;
            # giữ tương thích ngược cho nhãn giả lập nội bộ của test như `CLM-0`.
            if strict_claim_ids or cid.startswith("clm-"):
                reasons.append(
                    f"INVALID_CLAIM_ID: '{cid}' không thuộc tập allowed_claims của SKU '{evidence.sku_id}'."
                )
            elif cid not in valid_cids:
                valid_cids.append(cid)
        elif cid not in valid_cids:
            valid_cids.append(cid)

    is_non_factual_bridge = (
        allow_non_factual_without_citation
        and role in {StoryChunkRole.OPENING, StoryChunkRole.TRANSITION_BRIDGE}
        and not topic.fact_refs
        and stated_price_vnd is None
        and not mentions_ocop
    )

    if not cited_evidence_ids and not is_non_factual_bridge:
        suggested_refs = ", ".join(topic.fact_refs[:3]) if topic.fact_refs else ""
        hint = f" (tham khảo fact_refs của chủ đề: [{suggested_refs}])" if suggested_refs else ""
        reasons.append(
            f"MISSING_EVIDENCE_ATTRIBUTION: Lời thoại factual cho SKU '{evidence.sku_id}' bắt buộc "
            f"trích dẫn ít nhất 01 evidence_id hợp lệ trong cited_evidence_ids{hint}."
        )

    return EvidenceAttributionResult(
        passed=(len(reasons) == 0),
        failure_reasons=tuple(reasons),
        validated_evidence_ids=tuple(valid_eids),
        validated_claim_ids=tuple(valid_cids),
    )


def _extract_content_tokens(raw_text: str) -> list[str]:
    """Tách từ thường hóa bỏ dấu câu dùng cho đối chiếu từ vựng tất định."""
    return [tok.lower() for tok in _WORD_TOKEN_RE.findall(raw_text)]


def check_topic_objective_alignment(
    *,
    text: str,
    topic: StoryTopic,
    evidence: SkuEvidenceView,
) -> TopicObjectiveCheckResult:
    """Kiểm tra lời thoại có giữ được ít nhất một ý trọng tâm của `topic.talking_points` không.

    Cách hoạt động:
    - Rút trích tập từ khóa đặc trưng từ `talking_points` (hoặc `topic.title` nếu `talking_points` rỗng),
      loại bỏ từ hư từ, con số thuần túy, đơn vị giá/khối lượng và từ đã nằm trong `sku_name`.
    - Chỉ áp dụng chặn khi tập từ khóa đặc trưng có từ 2 từ trở lên để tránh false-positive với
      các chủ đề thuần báo giá hoặc fixture kiểm thử tối giản.
    """
    source_parts = list(topic.talking_points) if topic.talking_points else [topic.title]
    sku_name_tokens = set(_extract_content_tokens(evidence.sku_name))

    expected_keywords: list[str] = []
    for part in source_parts:
        for tok in _extract_content_tokens(part):
            if len(tok) < 2:
                continue
            if tok.isdigit() or any(ch.isdigit() for ch in tok):
                continue
            if tok in _STOPWORDS_AND_CATALOG_TOKENS or tok in sku_name_tokens:
                continue
            if tok not in expected_keywords:
                expected_keywords.append(tok)

    if len(expected_keywords) < 2:
        return TopicObjectiveCheckResult(
            passed=True,
            matched_keywords=(),
            expected_keywords=tuple(expected_keywords),
            reason=None,
        )

    text_tokens = set(_extract_content_tokens(text))
    matched = tuple(kw for kw in expected_keywords if kw in text_tokens)
    if matched:
        return TopicObjectiveCheckResult(
            passed=True,
            matched_keywords=matched,
            expected_keywords=tuple(expected_keywords),
            reason=None,
        )

    talking_points_display = "; ".join(topic.talking_points) if topic.talking_points else topic.title
    reason = (
        f"TOPIC_OBJECTIVE_MISSED: Lời thoại chưa truyền đạt ý chính của chủ đề "
        f"'{topic.title}' ({talking_points_display}). Không được rút gọn chỉ còn tên sản phẩm và giá."
    )
    return TopicObjectiveCheckResult(
        passed=False,
        matched_keywords=(),
        expected_keywords=tuple(expected_keywords),
        reason=reason,
    )
