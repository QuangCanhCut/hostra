"""Bộ sinh phản hồi giả lập tất định và an toàn theo schema cho P06-E01 (`mock_fixtures.py`).

1. File này giải quyết vấn đề gì?
   Cung cấp bộ `MockLLMProvider` dựng động từ `StoryPlan` và `P05KnowledgeAdapter` (chỉ đọc từ
   `e01_verified_skus.json`) để chạy kiểm thử end-to-end hoàn toàn ngoại tuyến mà không hardcode
   bất kỳ văn bản thương mại hay kịch bản cố định nào trong mã nguồn.
2. Trách nhiệm chính của module là gì?
   Định nghĩa hàm `build_e01_mock_provider()` sinh các `MockResponseStep` hợp lệ cho từng
   `topic_id`, `topic_id:r1`, `topic_id:r2` và fallback `seeded_variants_by_schema` khớp đúng
   `ChunkDraftLLMOutput` hoặc `UpfrontChunkDraftLLMOutput`.
3. Module này liên kết với các thành phần nào?
   Sử dụng `P05KnowledgeAdapter` (`p06.adapters.p05_knowledge_adapter`), `MockLLMProvider` /
   `MockResponseStep` / `MockBehavior` (`p06.providers.mock_provider`) và `StoryPlan` (`p06.schemas.story`).
4. Input và output chính là gì?
   Input là `StoryPlan`, `P05KnowledgeAdapter`, `seed`, `include_claim_ids` và tùy chọn `response_sequence`;
   Output là `MockLLMProvider` sẵn sàng chạy cho cả `LangGraph` lẫn `ScriptFirstBaseline`.
5. Có những constraints hoặc invariants quan trọng nào?
   - Văn bản tiếng Việt sinh ra dài 10–16 từ (<= 8.0 giây ở 2.6 từ/giây), trích dẫn đúng
     `evidence_id` thuộc `approved_chunks`, đúng `price_vnd`, không rò rỉ chéo SKU.
   - Khi `include_claim_ids=False` (cho `UpfrontChunkDraftLLMOutput` với `extra="forbid"`), tuyệt
     đối không gắn trường `covered_claim_ids` vào `keyed_responses`.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Final, Optional

from p06.adapters.interfaces import SkuEvidenceView
from p06.adapters.p05_knowledge_adapter import P05KnowledgeAdapter
from p06.providers.mock_provider import (
    DEFAULT_MOCK_MODEL_ID,
    MockBehavior,
    MockLLMProvider,
    MockResponseStep,
)
from p06.schemas.story import StoryArc, StoryPlan, StoryTopic

_MIN_MOCK_WORDS: Final[int] = 10
_MAX_MOCK_WORDS: Final[int] = 16
_PRIMARY_QUEUE_DEPTH: Final[int] = 5
_REWRITE_QUEUE_DEPTH: Final[int] = 3


def _format_vnd_price(price_vnd: int) -> str:
    """Định dạng giá VNĐ theo dấu chấm ngăn cách hàng nghìn phục vụ lời thoại tiếng Việt."""
    return f"{price_vnd:,}".replace(",", ".") + "đ"


def _clamp_word_window(text: str, *, min_words: int = _MIN_MOCK_WORDS, max_words: int = _MAX_MOCK_WORDS) -> str:
    """Điều chỉnh số từ nằm gọn trong `[min_words, max_words]` để luôn dưới ngưỡng 8.0s."""
    words = text.strip().split()
    if len(words) > max_words:
        trimmed = " ".join(words[:max_words]).rstrip(",;:")
        if trimmed and trimmed[-1] not in ".!?":
            trimmed = f"{trimmed}."
        return trimmed
    if len(words) < min_words:
        cleaned = text.strip().rstrip(".!?")
        padded = f"{cleaned} đúng chuẩn thông tin đã được duyệt."
        padded_words = padded.split()
        if len(padded_words) > max_words:
            padded = " ".join(padded_words[:max_words]).rstrip(",;:") + "."
        return padded
    cleaned = text.strip()
    if cleaned and cleaned[-1] not in ".!?":
        cleaned = f"{cleaned}."
    return cleaned


def _resolve_topic_sku_id(story_plan: StoryPlan, arc: StoryArc, topic: StoryTopic) -> str:
    """Xác định SKU mục tiêu cho một chủ đề theo thứ tự ưu tiên topic -> arc -> pinned_sku_ids[0]."""
    if topic.sku_id is not None:
        return topic.sku_id
    if arc.sku_id is not None:
        return arc.sku_id
    return story_plan.pinned_sku_ids[0]


def _resolve_valid_evidence_ids(topic: StoryTopic, evidence: SkuEvidenceView) -> list[str]:
    """Lấy danh sách `evidence_id` hợp lệ thuộc `approved_chunks` ưu tiên khớp `topic.fact_refs`."""
    approved_ids = [chunk["evidence_id"] for chunk in evidence.approved_chunks]
    approved_set = set(approved_ids)
    matched = [eid for eid in topic.fact_refs if eid in approved_set]
    if matched:
        return matched
    if approved_ids:
        return [approved_ids[0]]
    return list(topic.fact_refs)


def _extract_source_snippets(topic: StoryTopic, evidence: SkuEvidenceView, cited_ids: Sequence[str]) -> list[str]:
    """Trích các mảnh nội dung đã duyệt từ `talking_points` và `approved_chunks` khớp chủ đề."""
    chunks_by_id = {chunk["evidence_id"]: chunk["content"] for chunk in evidence.approved_chunks}
    snippets: list[str] = []
    for point in topic.talking_points:
        clean_point = point.strip()
        if clean_point:
            snippets.append(clean_point)
    for eid in cited_ids:
        content = chunks_by_id.get(eid)
        if content:
            for sentence in content.split("."):
                clean_sentence = sentence.strip()
                if clean_sentence:
                    snippets.append(clean_sentence)
    if not snippets:
        snippets.append(topic.title.strip())
    return snippets


def _build_variant_texts(
    topic: StoryTopic,
    evidence: SkuEvidenceView,
    cited_ids: Sequence[str],
    *,
    count: int,
    variant_prefix: str = "",
) -> list[str]:
    """Sinh `count` biến thể câu tiếng Việt ngắn gọn (10–16 từ) khác nhau để tránh lặp Jaccard."""
    snippets = _extract_source_snippets(topic, evidence, cited_ids)
    price_display = _format_vnd_price(evidence.price_vnd)
    short_origin = evidence.origin.split(",")[-1].strip()
    base_templates = (
        f"{variant_prefix}Điểm nhấn {short_origin}: {snippets[0]}",
        f"{variant_prefix}Thông tin chuẩn {price_display}: {snippets[1 % len(snippets)]}",
        f"{variant_prefix}Hướng dẫn chi tiết: {snippets[2 % len(snippets)]}",
        f"{variant_prefix}{evidence.sku_name} giá {price_display}, {snippets[0]}",
        f"{variant_prefix}Lưu ý sử dụng chuẩn: {snippets[-1]}",
    )
    results: list[str] = []
    for idx in range(count):
        raw_candidate = base_templates[idx % len(base_templates)]
        if idx >= len(base_templates):
            raw_candidate = f"Lượt bổ sung {idx + 1}: {raw_candidate}"
        results.append(_clamp_word_window(raw_candidate))
    return results


def _build_step_payload(
    *,
    text: str,
    cited_evidence_ids: Sequence[str],
    evidence: SkuEvidenceView,
    covered_claim_ids: Sequence[str],
    include_claim_ids: bool,
    rationale: str,
) -> dict[str, Any]:
    """Đóng gói JSON payload chuẩn cho `ChunkDraftLLMOutput` hoặc `UpfrontChunkDraftLLMOutput`."""
    mentions_ocop = ("ocop" in text.lower()) and (evidence.ocop_status == "VERIFIED")
    payload: dict[str, Any] = {
        "text": text,
        "role": "PRODUCT_STORY",
        "cited_evidence_ids": list(cited_evidence_ids),
        "stated_price_vnd": evidence.price_vnd,
        "mentions_ocop": mentions_ocop,
        "semantic_breakpoint": True,
        "breakpoint_type": "TOPIC_END",
        "rationale": rationale,
    }
    if include_claim_ids:
        payload["covered_claim_ids"] = list(covered_claim_ids)
    return payload


def build_e01_mock_provider(
    story_plan: StoryPlan,
    evidence_adapter: P05KnowledgeAdapter,
    *,
    seed: int = 42,
    model_id: str = DEFAULT_MOCK_MODEL_ID,
    at_time: Optional[datetime] = None,
    response_sequence: Optional[Sequence[MockResponseStep]] = None,
    include_claim_ids: bool = True,
) -> MockLLMProvider:
    """Khởi tạo `MockLLMProvider` tất định từ `StoryPlan` và kho bằng chứng đã duyệt P05.

    Lý do thiết kế:
        Tách riêng `include_claim_ids` vì `ChunkDraftLLMOutput` (LangGraph) nhận `covered_claim_ids`,
        còn `UpfrontChunkDraftLLMOutput` (Script-First Upfront LLM) bật `extra="forbid"` và cấm
        trường này. Đồng thời nạp cả `seeded_variants_by_schema` cho hai schema để fallback an toàn.

    Args:
        story_plan: Kế hoạch kể chuyện đã `APPROVED` làm nguồn danh sách chủ đề và SKU.
        evidence_adapter: Bộ đọc tri thức P05 (`P05KnowledgeAdapter`) để trích xuất fact/evidence hợp lệ.
        seed: Hạt giống tất định dùng cho chọn biến thể SHA-256.
        model_id: Mã định danh model giả lập ghi vào telemetry.
        at_time: Mốc thời gian ảo dùng khi truy vấn `get_sku_evidence`.
        response_sequence: Chuỗi bước phản hồi tường minh (nếu caller muốn kiểm thử lỗi/retry cụ thể).
        include_claim_ids: Nếu `True`, payload trong `keyed_responses` chứa `covered_claim_ids`
            cho LangGraph; nếu `False`, lược bỏ để khớp `UpfrontChunkDraftLLMOutput`.

    Returns:
        MockLLMProvider: Provider tầng 1 (`UNIT_TEST`) sẵn sàng chạy ngoại tuyến.
    """
    if response_sequence is not None:
        # Khi test truyền chuỗi bước tuần tự tường minh, không nạp keyed_responses để giữ đúng thứ tự tiêu thụ.
        return MockLLMProvider(
            model_id=model_id,
            response_sequence=response_sequence,
            seed=seed,
        )

    evidence_by_sku: dict[str, SkuEvidenceView] = {}
    for sku_id in story_plan.pinned_sku_ids:
        evidence_by_sku[sku_id] = evidence_adapter.get_sku_evidence(
            story_plan.tenant_id,
            sku_id,
            at_time=at_time,
        )

    keyed_responses: dict[str, list[MockResponseStep]] = {}
    chunk_schema_variants: list[MockResponseStep] = []
    upfront_schema_variants: list[MockResponseStep] = []

    for arc in sorted(story_plan.arcs, key=lambda item: item.position):
        for topic in arc.topics:
            sku_id = _resolve_topic_sku_id(story_plan, arc, topic)
            evidence = evidence_by_sku.get(sku_id)
            if evidence is None:
                evidence = evidence_adapter.get_sku_evidence(
                    story_plan.tenant_id,
                    sku_id,
                    at_time=at_time,
                )
                evidence_by_sku[sku_id] = evidence

            cited_ids = _resolve_valid_evidence_ids(topic, evidence)
            claim_ids = list(topic.allowed_claim_ids)

            primary_texts = _build_variant_texts(
                topic,
                evidence,
                cited_ids,
                count=_PRIMARY_QUEUE_DEPTH,
            )
            keyed_responses[topic.topic_id] = [
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=_build_step_payload(
                        text=text,
                        cited_evidence_ids=cited_ids,
                        evidence=evidence,
                        covered_claim_ids=claim_ids,
                        include_claim_ids=include_claim_ids,
                        rationale=f"Mock E01 cho chủ đề {topic.topic_id} biến thể {idx}.",
                    ),
                )
                for idx, text in enumerate(primary_texts)
            ]

            for retry_idx in (1, 2):
                retry_key = f"{topic.topic_id}:r{retry_idx}"
                retry_texts = _build_variant_texts(
                    topic,
                    evidence,
                    cited_ids,
                    count=_REWRITE_QUEUE_DEPTH,
                    variant_prefix=f"Diễn đạt mới vòng {retry_idx}: ",
                )
                keyed_responses[retry_key] = [
                    MockResponseStep(
                        behavior=MockBehavior.VALID_JSON,
                        payload=_build_step_payload(
                            text=text,
                            cited_evidence_ids=cited_ids,
                            evidence=evidence,
                            covered_claim_ids=claim_ids,
                            include_claim_ids=include_claim_ids,
                            rationale=f"Mock rewrite vòng {retry_idx} cho {topic.topic_id}.",
                        ),
                    )
                    for text in retry_texts
                ]

            if not chunk_schema_variants:
                chunk_schema_variants.append(
                    MockResponseStep(
                        behavior=MockBehavior.VALID_JSON,
                        payload=_build_step_payload(
                            text=primary_texts[0],
                            cited_evidence_ids=cited_ids,
                            evidence=evidence,
                            covered_claim_ids=claim_ids,
                            include_claim_ids=True,
                            rationale=f"Seeded fallback ChunkDraftLLMOutput cho {topic.topic_id}.",
                        ),
                    )
                )
                upfront_schema_variants.append(
                    MockResponseStep(
                        behavior=MockBehavior.VALID_JSON,
                        payload=_build_step_payload(
                            text=primary_texts[0],
                            cited_evidence_ids=cited_ids,
                            evidence=evidence,
                            covered_claim_ids=claim_ids,
                            include_claim_ids=False,
                            rationale=f"Seeded fallback UpfrontChunkDraftLLMOutput cho {topic.topic_id}.",
                        ),
                    )
                )

    return MockLLMProvider(
        model_id=model_id,
        keyed_responses=keyed_responses,
        seed=seed,
        seeded_variants_by_schema={
            "ChunkDraftLLMOutput": chunk_schema_variants,
            "UpfrontChunkDraftLLMOutput": upfront_schema_variants,
        },
    )
