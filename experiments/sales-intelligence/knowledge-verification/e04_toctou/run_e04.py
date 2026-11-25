"""Thí nghiệm P05-E04 — Kiểm chứng lỗi TOCTOU khi dữ liệu thay đổi trước thời điểm phát (Hard Gate G3).

Mục tiêu:
- Mô phỏng dòng thời gian thực tế trong phiên live:
  + t0: P06 tạo SpeechCandidate -> P05 duyệt lần 1 (ALLOW) -> gửi sang P02 sinh giọng nói (TTS).
  + t1: Trong lúc chờ TTS/lip-sync, dữ liệu thay đổi (đổi giá / thu hồi OCOP / thu hồi quyền).
  + t2: Ngay trước khi P08 commit lệnh phát sang P04, gọi P05 kiểm tra lại (revalidate).
- Chứng minh: Mọi candidate đã lỗi thời đều bị CHẶN (BLOCK) ở t2, không phát thông tin cũ ra stream,
  và vẫn giữ nguyên dấu vết audit nối từ candidate_id về phiên bản đã kiểm tra.
"""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from publication_gate import PublicationGate, VersionedKnowledgeStore
from schemas import (
    BlockReason,
    ExperimentManifest,
    OcopStatus,
    PublicationStatus,
    RightsStatus,
    SpeechCandidate,
)


def run_toctou_scenarios(base_store: VersionedKnowledgeStore) -> list[dict]:
    """Chạy 4 kịch bản mô phỏng TOCTOU (3 ca đột biến giữa chừng + 1 ca đối chứng ổn định)."""
    scenarios = [
        {
            "scenario_id": "E04-S01",
            "description": "Đổi giá mật ong từ 159.000đ (v1) lên 175.000đ (v2) sau khi TTS xong",
            "candidate": SpeechCandidate(
                candidate_id="cand-toctou-price",
                tenant_id="tenant-demo-01",
                session_id="sess-live-01",
                sku_id="SKU-HONEY-01",
                text="Chai mật ong hoa cà phê 500ml có giá 159.000đ nhé anh chị.",
                cited_evidence_ids=["ev-honey-04"],
                stated_price_vnd=159000,
                mentions_ocop=False,
                knowledge_version=1,
                ocop_version=1,
                rights_version=1,
            ),
            "mutation": lambda s: s.update_price("SKU-HONEY-01", 175000),
            "expected_t2_status": PublicationStatus.BLOCK,
            "expected_t2_reasons": [BlockReason.STALE_KNOWLEDGE_VERSION, BlockReason.PRICE_MISMATCH],
        },
        {
            "scenario_id": "E04-S02",
            "description": "P09 thu hồi chứng nhận OCOP của trà (VERIFIED v1 -> REVOKED v2) trước commit",
            "candidate": SpeechCandidate(
                candidate_id="cand-toctou-ocop",
                tenant_id="tenant-demo-01",
                session_id="sess-live-01",
                sku_id="SKU-TEA-02",
                text="Trà Shan Tuyết Hà Giang đạt chuẩn OCOP 4 sao, hương cốm hậu ngọt sâu.",
                cited_evidence_ids=["ev-tea-03"],
                stated_price_vnd=None,
                mentions_ocop=True,
                knowledge_version=1,
                ocop_version=1,
                rights_version=1,
            ),
            "mutation": lambda s: s.update_ocop_status("SKU-TEA-02", OcopStatus.REVOKED),
            "expected_t2_status": PublicationStatus.BLOCK,
            "expected_t2_reasons": [BlockReason.STALE_OCOP_VERSION, BlockReason.OCOP_NOT_VERIFIED],
        },
        {
            "scenario_id": "E04-S03",
            "description": "P11 thu hồi quyền sử dụng tài sản (ACTIVE v1 -> REVOKED v2) trước commit",
            "candidate": SpeechCandidate(
                candidate_id="cand-toctou-rights",
                tenant_id="tenant-demo-01",
                session_id="sess-live-01",
                sku_id="SKU-HONEY-01",
                text="Mật ong kết tinh tự nhiên ở nhiệt độ thấp, chỉ cần ngâm nước ấm 40 độ C là tan lại.",
                cited_evidence_ids=["ev-honey-02"],
                stated_price_vnd=None,
                mentions_ocop=False,
                knowledge_version=1,
                ocop_version=1,
                rights_version=1,
            ),
            "mutation": lambda s: s.update_rights_status("SKU-HONEY-01", RightsStatus.REVOKED),
            "expected_t2_status": PublicationStatus.BLOCK,
            "expected_t2_reasons": [BlockReason.STALE_RIGHTS_VERSION, BlockReason.RIGHTS_INVALID],
        },
        {
            "scenario_id": "E04-S04",
            "description": "Đối chứng: dữ liệu không đổi giữa t0 và t2 -> vẫn ALLOW hợp lệ",
            "candidate": SpeechCandidate(
                candidate_id="cand-toctou-clean",
                tenant_id="tenant-demo-01",
                session_id="sess-live-01",
                sku_id="SKU-TEA-02",
                text="Trà Shan Tuyết hộp 100g có thể pha được 6 đến 8 lần nước.",
                cited_evidence_ids=["ev-tea-01"],
                stated_price_vnd=None,
                mentions_ocop=False,
                knowledge_version=1,
                ocop_version=1,
                rights_version=1,
            ),
            "mutation": None,
            "expected_t2_status": PublicationStatus.ALLOW,
            "expected_t2_reasons": [],
        },
    ]

    results = []
    for sc in scenarios:
        store = base_store.clone()
        gate = PublicationGate(store)
        cand = sc["candidate"]

        # Mốc t0: Kiểm duyệt lần 1 trước khi gửi sang TTS (P02)
        t0_decision = gate.evaluate(cand)

        # Mốc t1: Giả lập dữ liệu thay đổi trong lúc chờ TTS/lip-sync
        if sc["mutation"] is not None:
            sc["mutation"](store)

        # Mốc t2: Kiểm duyệt lại (Just-in-time Revalidation) ngay trước khi P08 commit sang P04
        t2_decision = gate.evaluate(cand)

        t0_ok = t0_decision.status == PublicationStatus.ALLOW
        t2_status_ok = t2_decision.status == sc["expected_t2_status"]
        t2_reasons_ok = all(r in t2_decision.reasons for r in sc["expected_t2_reasons"])
        audit_ok = (
            t2_decision.candidate_id == cand.candidate_id
            and t2_decision.checked_knowledge_version >= cand.knowledge_version
            and t2_decision.checked_ocop_version >= cand.ocop_version
            and t2_decision.checked_rights_version >= cand.rights_version
        )
        passed = t0_ok and t2_status_ok and t2_reasons_ok and audit_ok

        results.append(
            {
                "scenario_id": sc["scenario_id"],
                "description": sc["description"],
                "t0_pre_tts_status": t0_decision.status.value,
                "t2_pre_commit_status": t2_decision.status.value,
                "t2_reasons": [r.value for r in t2_decision.reasons],
                "t2_details": t2_decision.details,
                "audit_versions": {
                    "candidate": {
                        "knowledge": cand.knowledge_version,
                        "ocop": cand.ocop_version,
                        "rights": cand.rights_version,
                    },
                    "checked_at_t2": {
                        "knowledge": t2_decision.checked_knowledge_version,
                        "ocop": t2_decision.checked_ocop_version,
                        "rights": t2_decision.checked_rights_version,
                    },
                },
                "passed": passed,
            }
        )

    return results


def main() -> None:
    seed_path = BASE_DIR / "data" / "catalog_seed.json"
    base_store = VersionedKnowledgeStore.from_seed_file(seed_path)
    results = run_toctou_scenarios(base_store)

    print("=== CHẠY THÍ NGHIỆM P05-E04: KIỂM CHỨNG CHỐNG LỖI TOCTOU TRƯỚC KHI PHÁT ===")
    passed = 0
    stale_leaks = 0
    for r in results:
        if r["passed"]:
            passed += 1
        if r["scenario_id"] != "E04-S04" and r["t2_pre_commit_status"] == PublicationStatus.ALLOW.value:
            stale_leaks += 1
        marker = "PASS" if r["passed"] else "FAIL"
        reasons_str = ", ".join(r["t2_reasons"]) if r["t2_reasons"] else "NONE"
        print(
            f"[{marker}] {r['scenario_id']} | t0={r['t0_pre_tts_status']} -> t2={r['t2_pre_commit_status']} "
            f"| reasons=[{reasons_str}] | {r['description']}"
        )

    total = len(results)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    decision_label = "GO" if (stale_leaks == 0 and passed == total) else "NO-GO"

    manifest = ExperimentManifest(
        experiment_id="P05-E04",
        run_id=run_id,
        dataset_source="data/catalog_seed.json (p05-synthetic-catalog-v0.1)",
        is_synthetic=True,
        environment={
            "python": platform.python_version(),
            "os": platform.platform(),
            "processor": platform.processor(),
        },
        config={"total_scenarios": total, "revalidation_mode": "just_in_time_version_check"},
        metrics={
            "total_scenarios": total,
            "passed_scenarios": passed,
            "stale_candidate_leaks": stale_leaks,
            "scenario_results": results,
        },
        decision=decision_label,
        notes=(
            "Mô phỏng TOCTOU trên bộ lưu trữ phiên bản trong bộ nhớ (in-memory mock). "
            "Cần kiểm chứng lại trên transaction PostgreSQL thật khi tích hợp với P08 ở Stage 06."
        ),
    )

    runs_dir = BASE_DIR / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    out_path = runs_dir / f"P05-E04_{run_id}.json"
    out_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

    print(
        f"\nTỔNG KẾT P05-E04: {passed}/{total} PASS | "
        f"stale_candidate_leaks={stale_leaks} | decision={decision_label}"
    )
    print(f"Đã lưu manifest tại: {out_path}")

    if stale_leaks > 0 or passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
