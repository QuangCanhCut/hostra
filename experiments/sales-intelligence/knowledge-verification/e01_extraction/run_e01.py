"""Thí nghiệm P05-E01 — Đo độ chính xác trích xuất tài liệu sản phẩm với Docling.

Mục tiêu:
- Đưa 10 tài liệu sản phẩm đa định dạng (5 DOCX + 5 PDF tiếng Việt có dấu) qua Docling.
- Bóc tách 4 trường cứng quan trọng: `price_vnd`, `weight`, `expiry`, `origin` thành bản nháp
  ở trạng thái bắt buộc `ApprovalStatus.DRAFT` (tuyệt đối không tự duyệt thành `APPROVED`).
- Đo Exact Match theo từng trường, tách báo cáo DOCX vs PDF, đo tốc độ P50/P95 trên CPU,
  và lưu bảng đối chiếu đầy đủ vào `runs/P05-E01_<run_id>.json`.
"""

from __future__ import annotations

import json
import math
import platform
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from docling.document_converter import DocumentConverter

BASE_DIR = Path(__file__).resolve().parent.parent
E01_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from publication_gate import extract_prices_vnd
from schemas import ApprovalStatus, ExperimentManifest


def percentile(values: list[float], p: float) -> float:
    """Tính phân vị (P50/P95) cho thời gian xử lý (giây)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return round(ordered[int(k)], 3)
    return round(ordered[f] + (ordered[c] - ordered[f]) * (k - f), 3)


def normalize_text(val: Optional[str]) -> str:
    """Chuẩn hóa khoảng trắng và chữ thường để so khớp Exact Match công bằng."""
    if not val:
        return ""
    return re.sub(r"\s+", " ", val.strip().lower())


def parse_fields_from_markdown(md_text: str) -> dict[str, Any]:
    """Bóc tách 4 trường cứng từ văn bản Markdown mà Docling trả về.

    Hỗ trợ cả dạng bảng Markdown (`| Nhãn | Giá trị |`) lẫn văn xuôi (`Nhãn: Giá trị`).
    """
    # 1. Trích xuất giá VNĐ (tái sử dụng hàm chuẩn đã kiểm chứng trong publication_gate.py)
    prices = extract_prices_vnd(md_text)
    price_vnd: Optional[int] = prices[0] if prices else None

    # 2. Trích xuất khối lượng / dung tích (ml, g, kg, gram)
    weight_match = re.search(
        r"(?:khối lượng(?:\s*tịnh|\s*/\s*dung tích)?)\s*[:|]\s*\|?\s*([0-9]+(?:[.,][0-9]+)?\s*(?:ml|kg|gram|g)\b)",
        md_text,
        flags=re.IGNORECASE,
    )
    if not weight_match:
        weight_match = re.search(
            r"\b([0-9]+(?:[.,][0-9]+)?\s*(?:ml|kg|gram|g))\b",
            md_text,
            flags=re.IGNORECASE,
        )
    weight = weight_match.group(1).strip() if weight_match else None

    # 3. Trích xuất hạn sử dụng (ví dụ: "24 tháng", "18 tháng", "12 tháng")
    expiry_match = re.search(
        r"(?:hạn sử dụng|hsd)\s*[:|]\s*\|?\s*([0-9]+\s*(?:tháng|năm|ngày))",
        md_text,
        flags=re.IGNORECASE,
    )
    if not expiry_match:
        expiry_match = re.search(
            r"\b([0-9]+\s*(?:tháng|năm))\b",
            md_text,
            flags=re.IGNORECASE,
        )
    expiry = expiry_match.group(1).strip() if expiry_match else None

    # 4. Trích xuất xuất xứ (đọc giá trị đứng sau "Xuất xứ:" hoặc cột bảng "| Xuất xứ | ... |")
    origin: Optional[str] = None
    origin_table_match = re.search(
        r"xuất xứ\s*\|\s*([^|\n]+)",
        md_text,
        flags=re.IGNORECASE,
    )
    if origin_table_match:
        origin = origin_table_match.group(1).strip().rstrip(".")
    else:
        origin_colon_match = re.search(
            r"xuất xứ\s*:\s*([^\n.|]+)",
            md_text,
            flags=re.IGNORECASE,
        )
        if origin_colon_match:
            origin = origin_colon_match.group(1).strip().rstrip(".")

    return {
        "price_vnd": price_vnd,
        "weight": weight,
        "expiry": expiry,
        "origin": origin,
        # Mọi kết quả từ Docling chỉ là DRAFT chờ người kiểm duyệt (bất biến P05)
        "approval_status": ApprovalStatus.DRAFT.value,
    }


def main() -> None:
    gt_path = E01_DIR / "ground_truth.json"
    docs_dir = E01_DIR / "sample_docs"
    gt_data = json.loads(gt_path.read_text(encoding="utf-8"))
    docs = gt_data["documents"]

    print("=== CHẠY THÍ NGHIỆM P05-E01: ĐO ĐỘ CHÍNH XÁC EXTRACTION VỚI DOCLING ===")
    print(f"Tổng số tài liệu kiểm thử: {len(docs)} (5 DOCX + 5 PDF). Đang khởi tạo Docling...")
    converter = DocumentConverter()

    fields = ("price_vnd", "weight", "expiry", "origin")
    field_hits = {f: 0 for f in fields}
    format_stats = {
        "docx": {"docs": 0, "field_total": 0, "field_hits": 0, "latencies_s": []},
        "pdf": {"docs": 0, "field_total": 0, "field_hits": 0, "latencies_s": []},
    }
    all_latencies_s: list[float] = []
    comparison_rows: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []

    for item in docs:
        doc_path = docs_dir / item["doc_id"]
        fmt = item["format"]
        gold = item["gold"]

        t0 = time.perf_counter()
        conv_result = converter.convert(str(doc_path))
        md_text = conv_result.document.export_to_markdown()
        elapsed_s = round(time.perf_counter() - t0, 3)

        all_latencies_s.append(elapsed_s)
        format_stats[fmt]["docs"] += 1
        format_stats[fmt]["latencies_s"].append(elapsed_s)

        pred = parse_fields_from_markdown(md_text)

        doc_matches = 0
        for f in fields:
            format_stats[fmt]["field_total"] += 1
            if f == "price_vnd":
                is_match = pred[f] == gold[f]
            else:
                is_match = normalize_text(pred[f]) == normalize_text(gold[f])

            if is_match:
                field_hits[f] += 1
                format_stats[fmt]["field_hits"] += 1
                doc_matches += 1
            else:
                error_rows.append(
                    {
                        "doc_id": item["doc_id"],
                        "format": fmt,
                        "layout": item["layout"],
                        "field": f,
                        "gold": gold[f],
                        "prediction": pred[f],
                    }
                )

            comparison_rows.append(
                {
                    "doc_id": item["doc_id"],
                    "format": fmt,
                    "field": f,
                    "gold": gold[f],
                    "prediction": pred[f],
                    "exact_match": is_match,
                }
            )

        status_icon = "PASS" if doc_matches == len(fields) else "MISS"
        print(
            f"[{status_icon}] {item['doc_id']:28s} ({fmt:4s}) | {doc_matches}/{len(fields)} trường đúng "
            f"| {elapsed_s:5.2f}s | draft_status={pred['approval_status']}"
        )

    total_docs = len(docs)
    exact_match_by_field = {f: round(field_hits[f] / total_docs, 4) for f in fields}
    overall_field_acc = round(sum(field_hits.values()) / (total_docs * len(fields)), 4)

    summary_by_format = {}
    for fmt, st in format_stats.items():
        summary_by_format[fmt] = {
            "docs": st["docs"],
            "field_exact_match": round(st["field_hits"] / st["field_total"], 4) if st["field_total"] else 0.0,
            "p50_sec": percentile(st["latencies_s"], 50),
            "p95_sec": percentile(st["latencies_s"], 95),
        }

    print("\n--- TỔNG KẾT EXACT MATCH THEO TRƯỜNG ---")
    for f, acc in exact_match_by_field.items():
        print(f"- {f:10s}: {field_hits[f]}/{total_docs} ({acc * 100:.1f}%)")
    print(f"=> Tổng Exact Match toàn bộ trường: {overall_field_acc * 100:.1f}%")
    print(
        f"=> Thời gian xử lý trên CPU: P50={percentile(all_latencies_s, 50):.2f}s | "
        f"P95={percentile(all_latencies_s, 95):.2f}s"
    )
    print(
        f"=> Theo định dạng: DOCX={summary_by_format['docx']['field_exact_match']*100:.1f}% "
        f"(P95={summary_by_format['docx']['p95_sec']:.2f}s) | "
        f"PDF={summary_by_format['pdf']['field_exact_match']*100:.1f}% "
        f"(P95={summary_by_format['pdf']['p95_sec']:.2f}s)"
    )

    if error_rows:
        print("\n--- DANH SÁCH LỖI TRÍCH XUẤT ---")
        for err in error_rows:
            print(f"  * {err['doc_id']} [{err['field']}]: gold={err['gold']!r} vs pred={err['prediction']!r}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    decision_label = "GO" if overall_field_acc >= 0.9 else "CHANGE"

    manifest = ExperimentManifest(
        experiment_id="P05-E01",
        run_id=run_id,
        dataset_source="e01_extraction/ground_truth.json (10 tài liệu synthetic: 5 DOCX + 5 PDF)",
        is_synthetic=True,
        environment={
            "python": platform.python_version(),
            "os": platform.platform(),
            "processor": platform.processor(),
            "device": "cpu",
        },
        config={
            "extractor": "docling.DocumentConverter",
            "output_approval_status": ApprovalStatus.DRAFT.value,
            "fields_evaluated": list(fields),
        },
        metrics={
            "total_documents": total_docs,
            "overall_field_exact_match": overall_field_acc,
            "exact_match_by_field": exact_match_by_field,
            "by_format": summary_by_format,
            "latency_sec": {
                "p50": percentile(all_latencies_s, 50),
                "p95": percentile(all_latencies_s, 95),
            },
            "error_count": len(error_rows),
            "errors": error_rows,
            "comparison_table": comparison_rows,
        },
        decision=decision_label,
        notes=(
            "Chạy trên 10 tài liệu synthetic dạng text/table (DOCX + PDF Unicode). "
            "Chưa bao gồm ảnh chụp nhãn sản phẩm bị nghiêng/mờ cần OCR nặng; cần bổ sung kiểm thử "
            "trên tài liệu scan thực tế của merchant trước khi chốt VALIDATED."
        ),
    )

    runs_dir = BASE_DIR / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    out_path = runs_dir / f"P05-E01_{run_id}.json"
    out_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    print(f"\nĐã lưu manifest tại: {out_path}")


if __name__ == "__main__":
    main()
