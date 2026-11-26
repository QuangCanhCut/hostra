"""Bộ kiểm thử đơn vị (unit tests) cho bộ dữ liệu tổng hợp E01 (`E01-T04`).

1. File này giải quyết vấn đề gì?
   Kiểm chứng tính toàn vẹn cấu trúc, liên kết khóa ngoại, tương thích với Cổng phát ngôn P05
   và an toàn nội dung (không từ cấm, không PII) của 4 tệp JSON phục vụ thí nghiệm `P06-E01`.
2. Trách nhiệm chính của module là gì?
   Xác minh `e01_verified_skus.json` (3 SKU `OCOP: VERIFIED`), `e01_negative_skus.json` (4 SKU
   âm tính bị P05 chặn), `e01_goals.json` (3 mục tiêu phiên) và `e01_story_plans.json` (3 kế hoạch
   `StoryPlan` hợp lệ chuẩn `p06-mock-v0.1`).
3. Module này liên kết với các thành phần nào?
   Đọc các tệp dữ liệu trong `data/` của P06, kiểm định qua `p06.schemas.StoryPlan` và nạp chỉ-đọc
   `schemas.py` + `publication_gate.py` từ module P05 (`knowledge-verification`).
4. Input và output chính là gì?
   Input là 4 tệp JSON dưới `P06_ROOT/data/`; Output là kết quả kiểm thử deterministic qua `pytest`.
5. Có những constraints hoặc invariants quan trọng nào?
   - Không chỉnh sửa dữ liệu hay mã nguồn của P05; cô lập `sys.modules['schemas']` khi nạp P05.
   - Đảm bảo tách biệt tuyệt đối positive SKUs (`e01_verified_skus.json`) khỏi negative SKUs
     (`e01_negative_skus.json`) và không có tuyên bố y tế bị cấm hay thông tin định danh cá nhân (PII).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from p06.adapters.p05_knowledge_adapter import _load_p05_modules
from p06.schemas import StoryPlan, StoryPlanApprovalStatus

# Định vị gốc P06 và P05 theo đường dẫn tương đối ổn định từ vị trí tệp kiểm thử.
P06_ROOT: Path = Path(__file__).resolve().parents[2]
DATA_ROOT: Path = P06_ROOT / "data"
VERIFIED_SKUS_PATH: Path = DATA_ROOT / "products" / "e01_verified_skus.json"
NEGATIVE_SKUS_PATH: Path = DATA_ROOT / "products" / "e01_negative_skus.json"
GOALS_PATH: Path = DATA_ROOT / "merchant_goals" / "e01_goals.json"
STORY_PLANS_PATH: Path = DATA_ROOT / "story_plans" / "e01_story_plans.json"

P05_DIR: Path = P06_ROOT.parent / "knowledge-verification"

EXPECTED_TENANT_ID: str = "tenant-p06-poc-01"
EXPECTED_VERIFIED_SKUS: tuple[str, ...] = (
    "SKU-HONEY-01",
    "SKU-TEA-02",
    "SKU-MACADAMIA-03",
)
EXPECTED_PLAN_KEYS: tuple[str, ...] = (
    "product_education_10m",
    "brand_storytelling_10m",
    "sales_presentation_30m",
)
EXPECTED_GOAL_IDS: tuple[str, ...] = (
    "goal_e01_product_education",
    "goal_e01_brand_storytelling",
    "goal_e01_sales_presentation",
)

# Biểu thức chính quy phát hiện email và số điện thoại di động Việt Nam để chặn rò rỉ PII.
EMAIL_PATTERN: re.Pattern[str] = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)
VN_PHONE_PATTERN: re.Pattern[str] = re.compile(r"(?<!\d)0[35789]\d{8}(?!\d)")


def _load_json(path: Path) -> dict[str, Any]:
    """Đọc tệp JSON UTF-8 và bảo đảm phần gốc là một đối tượng dict.

    Args:
        path: Đường dẫn tới tệp JSON cần nạp.

    Returns:
        dict[str, Any]: Dữ liệu JSON đã giải mã.

    Raises:
        FileNotFoundError: Nếu tệp không tồn tại.
        ValueError: Nếu dữ liệu gốc không phải `dict`.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Tệp '{path}' phải có JSON object ở cấp gốc.")
    return payload


def _collect_all_strings(node: Any) -> list[str]:
    """Duyệt đệ quy mọi giá trị chuỗi trong cấu trúc JSON để kiểm tra PII.

    Args:
        node: Nút dữ liệu JSON bất kỳ (`dict`, `list`, `str`, số...).

    Returns:
        list[str]: Danh sách toàn bộ chuỗi lá xuất hiện trong cấu trúc.
    """
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        collected: list[str] = []
        for item in node:
            collected.extend(_collect_all_strings(item))
        return collected
    if isinstance(node, dict):
        collected = []
        for value in node.values():
            collected.extend(_collect_all_strings(value))
        return collected
    return []


def test_e01_verified_skus_structure_and_uniqueness() -> None:
    """Xác minh cấu trúc, metadata mô phỏng và tính duy nhất ID trong `e01_verified_skus.json`."""
    raw = _load_json(VERIFIED_SKUS_PATH)

    meta = raw["dataset_meta"]
    assert meta["dataset_id"] == "p06-e01-verified-catalog-v0.1"
    assert meta["is_synthetic"] is True
    assert meta["data_origin"] == "synthetic_evaluation_fixture_for_p06_e01"
    assert meta["tenant_id"] == EXPECTED_TENANT_ID
    assert meta["sku_count"] == 3
    assert "KHÔNG phải chứng nhận OCOP thực tế" in meta["ocop_verification_note"]

    facts = raw["product_facts"]
    snapshots = raw["eligibility_snapshots"]
    chunks = raw["evidence_chunks"]
    claims = raw["claim_registry"]

    assert [item["sku_id"] for item in facts] == list(EXPECTED_VERIFIED_SKUS)
    assert [item["sku_id"] for item in snapshots] == list(EXPECTED_VERIFIED_SKUS)

    # Kiểm tra trùng lặp ID toàn tệp để tránh ghi đè ngầm khi nạp vào dict theo ID.
    evidence_ids = [item["evidence_id"] for item in chunks]
    claim_ids = [item["claim_id"] for item in claims]
    assert len(set(evidence_ids)) == len(evidence_ids)
    assert len(set(claim_ids)) == len(claim_ids)

    for fact, snap in zip(facts, snapshots, strict=True):
        assert fact["tenant_id"] == EXPECTED_TENANT_ID
        assert fact["approval_status"] == "APPROVED"
        assert fact["knowledge_version"] == 1
        assert fact["provenance"]["extracted_by"] == "synthetic_seed"
        assert fact["provenance"]["approved_by"] == "synthetic-owner-01"
        assert snap["tenant_id"] == EXPECTED_TENANT_ID
        assert snap["ocop_status"] == "VERIFIED"
        assert snap["ocop_code"] and snap["ocop_code"].startswith("SYNTH-OCOP-")
        assert snap["food_safety_verified"] is True
        assert snap["rights_status"] == "ACTIVE"

    # Mỗi SKU phải có tối thiểu 4 chunk APPROVED và đủ cả claim hợp lệ lẫn claim PROHIBITED.
    evidence_set = set(evidence_ids)
    for sku_id in EXPECTED_VERIFIED_SKUS:
        sku_chunks = [c for c in chunks if c["sku_id"] == sku_id and c["approval_status"] == "APPROVED"]
        assert len(sku_chunks) >= 4, f"SKU {sku_id} phải có ít nhất 4 chunk APPROVED."

        sku_claims = [c for c in claims if c["sku_id"] == sku_id]
        allowed_or_ocop = [
            c for c in sku_claims if c["category"] in ("ALLOWED", "REQUIRES_OFFICIAL_VERIFICATION")
        ]
        prohibited = [c for c in sku_claims if c["category"] == "PROHIBITED"]
        assert len(allowed_or_ocop) >= 2, f"SKU {sku_id} thiếu claim ALLOWED/OCOP."
        assert len(prohibited) >= 1, f"SKU {sku_id} thiếu claim PROHIBITED cho test P05/E04."

        for claim in allowed_or_ocop:
            assert len(claim["evidence_ids"]) >= 1
            for eid in claim["evidence_ids"]:
                assert eid in evidence_set


def test_e01_verified_skus_pass_p05_publication_gate() -> None:
    """Xác minh cả 3 SKU trong `e01_verified_skus.json` đều đạt `ALLOW` qua P05 `PublicationGate`."""
    p05_schemas, p05_gate = _load_p05_modules(P05_DIR)
    store = p05_gate.VersionedKnowledgeStore.from_seed_file(VERIFIED_SKUS_PATH)
    gate = p05_gate.PublicationGate(store)

    assert set(store.facts.keys()) == set(EXPECTED_VERIFIED_SKUS)

    sample_texts = {
        "SKU-HONEY-01": (
            "ev-e01-honey-ocop",
            "Mật ong hoa cà phê Đắk Lắk chai 500ml giá 159.000đ, đạt chuẩn OCOP 4 sao mô phỏng.",
        ),
        "SKU-TEA-02": (
            "ev-e01-tea-ocop",
            "Trà Shan Tuyết cổ thụ Hà Giang hộp thiếc 200g giá 245.000đ, đạt OCOP 4 sao mô phỏng.",
        ),
        "SKU-MACADAMIA-03": (
            "ev-e01-macadamia-ocop",
            "Hạt mắc ca sấy nứt vỏ Lâm Đồng hộp 500g giá 195.000đ, đạt OCOP 4 sao mô phỏng.",
        ),
    }

    for sku_id, (evidence_id, speech_text) in sample_texts.items():
        fact = store.facts[sku_id]
        elig = store.eligibilities[sku_id]
        candidate = p05_schemas.SpeechCandidate(
            candidate_id=f"cand-allow-{sku_id}",
            tenant_id=EXPECTED_TENANT_ID,
            session_id="sess-e01-dataset-verify",
            sku_id=sku_id,
            text=speech_text,
            cited_evidence_ids=[evidence_id],
            stated_price_vnd=fact.price_vnd,
            mentions_ocop=True,
            knowledge_version=fact.knowledge_version,
            ocop_version=elig.ocop_version,
            rights_version=elig.rights_version,
        )
        decision = gate.evaluate(candidate)
        assert decision.status == p05_schemas.PublicationStatus.ALLOW, (
            f"SKU {sku_id} bị chặn ngoài ý muốn: {decision.reasons} - {decision.details}"
        )
        assert decision.reasons == []

        # Đồng thời kiểm tra claim PROHIBITED của chính SKU đó phải bị P05 chặn cứng.
        prohibited_claim = next(
            c
            for c in store.claims
            if c.sku_id == sku_id and c.category == p05_schemas.ClaimCategory.PROHIBITED
        )
        bad_candidate = p05_schemas.SpeechCandidate(
            candidate_id=f"cand-prohibited-{sku_id}",
            tenant_id=EXPECTED_TENANT_ID,
            session_id="sess-e01-dataset-verify",
            sku_id=sku_id,
            text=f"{fact.sku_name}: {prohibited_claim.claim_text}",
            cited_evidence_ids=[evidence_id],
            stated_price_vnd=None,
            mentions_ocop=False,
            knowledge_version=fact.knowledge_version,
            ocop_version=elig.ocop_version,
            rights_version=elig.rights_version,
        )
        bad_decision = gate.evaluate(bad_candidate)
        assert bad_decision.status == p05_schemas.PublicationStatus.BLOCK
        assert p05_schemas.BlockReason.PROHIBITED_CLAIM in bad_decision.reasons


@pytest.mark.parametrize(
    ("sku_id", "evidence_id", "expected_reason_name"),
    [
        ("SKU-CASHEW-03", "ev-neg-cashew-01", "OCOP_NOT_VERIFIED"),
        ("SKU-COFFEE-EXPIRED-04", "ev-neg-coffee-01", "RIGHTS_INVALID"),
        ("SKU-GINGER-UNSAFE-05", "ev-neg-ginger-01", "FOOD_SAFETY_UNVERIFIED"),
        ("SKU-LOTUS-DRAFT-06", "ev-neg-lotus-01", "UNAPPROVED_FACT"),
    ],
)
def test_e01_negative_skus_blocked_by_p05_publication_gate(
    sku_id: str,
    evidence_id: str,
    expected_reason_name: str,
) -> None:
    """Xác minh cả 4 SKU âm tính trong `e01_negative_skus.json` đều bị P05 chặn đúng mã lỗi."""
    p05_schemas, p05_gate = _load_p05_modules(P05_DIR)
    store = p05_gate.VersionedKnowledgeStore.from_seed_file(NEGATIVE_SKUS_PATH)
    gate = p05_gate.PublicationGate(store)

    fact = store.facts[sku_id]
    elig = store.eligibilities[sku_id]
    candidate = p05_schemas.SpeechCandidate(
        candidate_id=f"cand-neg-{sku_id}",
        tenant_id=EXPECTED_TENANT_ID,
        session_id="sess-e01-negative-verify",
        sku_id=sku_id,
        text=f"{fact.sku_name} có giá {fact.price_vnd:,}đ.",
        cited_evidence_ids=[evidence_id],
        stated_price_vnd=fact.price_vnd,
        mentions_ocop=False,
        knowledge_version=fact.knowledge_version,
        ocop_version=elig.ocop_version,
        rights_version=elig.rights_version,
    )

    decision = gate.evaluate(candidate)
    expected_reason = getattr(p05_schemas.BlockReason, expected_reason_name)
    assert decision.status == p05_schemas.PublicationStatus.BLOCK
    assert expected_reason in decision.reasons


def test_e01_story_plans_validate_and_ground_against_verified_store() -> None:
    """Xác minh 3 `StoryPlan` hợp lệ theo Pydantic v2 và tham chiếu đúng facts/claims P05."""
    p05_schemas, p05_gate = _load_p05_modules(P05_DIR)
    store = p05_gate.VersionedKnowledgeStore.from_seed_file(VERIFIED_SKUS_PATH)
    claims_by_id = {claim.claim_id: claim for claim in store.claims}

    plans_raw = _load_json(STORY_PLANS_PATH)
    meta = plans_raw["dataset_meta"]
    assert meta["fixture_role"] == "reference_evaluation_fixture_not_llm_output"
    assert meta["simulated_approval"] is True
    assert meta["is_synthetic"] is True

    plans_dict = plans_raw["plans"]
    assert set(plans_dict.keys()) == set(EXPECTED_PLAN_KEYS)

    # Bảo đảm ID duy nhất xuyên suốt cả 3 kế hoạch để tránh va chạm khi nạp chung registry test.
    seen_plan_ids: set[str] = set()
    seen_session_ids: set[str] = set()
    seen_arc_ids: set[str] = set()
    seen_topic_ids: set[str] = set()

    for key in EXPECTED_PLAN_KEYS:
        plan = StoryPlan.model_validate(plans_dict[key])
        assert plan.approval_status == StoryPlanApprovalStatus.APPROVED
        assert plan.is_mvp_live_eligible() is True
        assert plan.tenant_id == EXPECTED_TENANT_ID
        assert len(plan.pinned_sku_ids) == 3
        assert set(plan.pinned_sku_ids) == set(EXPECTED_VERIFIED_SKUS)
        assert plan.plan_id not in seen_plan_ids
        assert plan.session_id not in seen_session_ids
        seen_plan_ids.add(plan.plan_id)
        seen_session_ids.add(plan.session_id)

        expected_versions = {sku: store.facts[sku].knowledge_version for sku in plan.pinned_sku_ids}
        assert plan.knowledge_versions_by_sku == expected_versions

        for arc in plan.arcs:
            assert arc.arc_id not in seen_arc_ids
            seen_arc_ids.add(arc.arc_id)
            assert arc.reviewed_by_merchant is True

            for topic in arc.topics:
                assert topic.topic_id not in seen_topic_ids
                seen_topic_ids.add(topic.topic_id)
                assert topic.sku_id is not None
                assert len(topic.fact_refs) >= 1
                assert len(topic.allowed_claim_ids) >= 1

                for eid in topic.fact_refs:
                    assert eid in store.chunks, f"Thiếu evidence_id '{eid}' trong verified store."
                    chunk = store.chunks[eid]
                    assert chunk.sku_id == topic.sku_id
                    assert chunk.approval_status == p05_schemas.ApprovalStatus.APPROVED

                for cid in topic.allowed_claim_ids:
                    assert cid in claims_by_id, f"Thiếu claim_id '{cid}' trong verified store."
                    claim = claims_by_id[cid]
                    assert claim.sku_id == topic.sku_id
                    assert claim.approval_status == p05_schemas.ApprovalStatus.APPROVED
                    assert claim.category != p05_schemas.ClaimCategory.PROHIBITED


def test_e01_goals_align_with_story_plans() -> None:
    """Xác minh 3 mục tiêu merchant trong `e01_goals.json` khớp chặt với `e01_story_plans.json`."""
    goals_raw = _load_json(GOALS_PATH)
    plans_raw = _load_json(STORY_PLANS_PATH)

    assert goals_raw["is_synthetic"] is True
    assert goals_raw["tenant_id"] == EXPECTED_TENANT_ID
    assert goals_raw["pinned_sku_ids"] == list(EXPECTED_VERIFIED_SKUS)

    goals = goals_raw["goals"]
    assert set(goals.keys()) == set(EXPECTED_GOAL_IDS)

    for goal_id in EXPECTED_GOAL_IDS:
        goal = goals[goal_id]
        plan = StoryPlan.model_validate(plans_raw["plans"][goal["story_plan_key"]])
        assert goal["tenant_id"] == plan.tenant_id
        assert goal["pinned_sku_ids"] == plan.pinned_sku_ids
        assert goal["session_goal"] == plan.session_goal
        assert goal["prohibited_topics"] == plan.prohibited_topics
        assert goal["mandatory_messages"] == plan.mandatory_messages

        expected_ids = goal["expected_mandatory_topic_ids"]
        assert len(set(expected_ids)) == len(expected_ids)
        assert set(expected_ids) == plan.mandatory_topic_ids()
        assert [t["topic_id"] for t in goal["mandatory_topics"]] == expected_ids


def test_e01_dataset_contains_no_prohibited_phrases_or_pii() -> None:
    """Bảo đảm không có cụm từ cấm y tế trong nội dung hợp lệ và không có PII ở cả 4 tệp JSON."""
    _, p05_gate = _load_p05_modules(P05_DIR)
    prohibited_phrases: tuple[str, ...] = p05_gate.DEFAULT_PROHIBITED_PHRASES

    verified_raw = _load_json(VERIFIED_SKUS_PATH)
    negative_raw = _load_json(NEGATIVE_SKUS_PATH)
    goals_raw = _load_json(GOALS_PATH)
    plans_raw = _load_json(STORY_PLANS_PATH)

    # 1. Kiểm tra mọi văn bản hợp lệ (chunk, claim không phải PROHIBITED, goals, story plans).
    safe_texts: list[str] = []
    for catalog in (verified_raw, negative_raw):
        for chunk in catalog["evidence_chunks"]:
            safe_texts.append(chunk["content"])
        for claim in catalog["claim_registry"]:
            if claim["category"] != "PROHIBITED":
                safe_texts.append(claim["claim_text"])

    for goal in goals_raw["goals"].values():
        safe_texts.append(goal["session_goal"])
        safe_texts.extend(goal["mandatory_messages"])
        safe_texts.extend(t["title"] for t in goal["mandatory_topics"])

    for plan_payload in plans_raw["plans"].values():
        safe_texts.append(plan_payload["session_goal"])
        safe_texts.extend(plan_payload["mandatory_messages"])
        for arc in plan_payload["arcs"]:
            safe_texts.append(arc["title"])
            if arc.get("preview_text"):
                safe_texts.append(arc["preview_text"])
            for topic in arc["topics"]:
                safe_texts.append(topic["title"])
                safe_texts.extend(topic["talking_points"])

    for text in safe_texts:
        text_lower = text.lower()
        for phrase in prohibited_phrases:
            assert phrase not in text_lower, (
                f"Phát hiện cụm từ công dụng bị cấm '{phrase}' trong nội dung hợp lệ: {text}"
            )

    # 2. Kiểm tra rò rỉ PII (email, số điện thoại di động VN) trên toàn bộ 4 tệp.
    for path, payload in (
        (VERIFIED_SKUS_PATH, verified_raw),
        (NEGATIVE_SKUS_PATH, negative_raw),
        (GOALS_PATH, goals_raw),
        (STORY_PLANS_PATH, plans_raw),
    ):
        for text in _collect_all_strings(payload):
            assert not EMAIL_PATTERN.search(text), f"Phát hiện email dạng PII trong {path}: {text}"
            assert not VN_PHONE_PATTERN.search(text), f"Phát hiện số điện thoại PII trong {path}: {text}"
