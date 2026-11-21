"""Thí nghiệm P05-E02 — Benchmark tìm kiếm bằng chứng theo SKU (PostgreSQL FTS vs pgvector).

Mục tiêu:
- Trả lời câu hỏi mở OPEN-2: PostgreSQL FTS (có/không `unaccent`) có đủ Recall trên câu hỏi
  livestream tiếng Việt (có dấu, không dấu/slang, diễn đạt đồng nghĩa) hay cần bổ sung `pgvector`?
- Luôn lọc cứng theo `tenant_id` và `sku_id` TRƯỚC khi tìm kiếm để đảm bảo 0 rò rỉ chéo SKU.
- Đo và báo cáo tách riêng theo từng nhóm câu hỏi: Recall@1, Recall@3, MRR, P50/P95 latency (ms).
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
from typing import Any

import psycopg

BASE_DIR = Path(__file__).resolve().parent.parent
E02_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from schemas import EvidenceChunk, ExperimentManifest

# Chuỗi kết nối tới container PostgreSQL 16 + pgvector chạy cục bộ (docker-compose.yml)
DB_DSN = "postgresql://hostra_poc:hostra_poc_local@127.0.0.1:5439/hostra_p05"

# Từ đệm/hư từ phổ biến trong bình luận livestream tiếng Việt (loại bớt để tránh nhiễu điểm FTS)
VI_STOPWORDS = {
    "la", "là", "cua", "của", "va", "và", "co", "có", "khong", "không", "ko", "k",
    "dc", "đc", "duoc", "được", "nay", "này", "cho", "voi", "với", "thi", "thì",
    "ma", "mà", "vay", "vậy", "a", "ạ", "oi", "ơi", "shop", "ad", "nha", "nhé",
    "nhe", "minh", "mình", "ben", "bên", "ban", "bạn", "hay", "hoac", "hoặc",
    "gi", "gì", "sao", "nao", "nào", "the", "thế", "nhu", "như", "tu", "từ",
    "trong", "ngoai", "ra", "vao", "vào", "di", "đi", "len", "lên", "xuong",
}


def build_or_tsquery(text: str) -> str:
    """Chuyển câu hỏi tự nhiên thành chuỗi tsquery dạng OR (`tu1 | tu2 | ...`).

    Lý do: `plainto_tsquery` mặc định dùng AND giữa MỌI từ trong câu hỏi, khiến các câu
    livestream có thêm từ thừa/slang (`shop ơi`, `ko`, `đc`) bị trả về 0 kết quả.
    """
    tokens = re.findall(r"[^\W_]+", text.lower(), flags=re.UNICODE)
    filtered = [t for t in tokens if len(t) >= 2 and t not in VI_STOPWORDS]
    if not filtered:
        filtered = [t for t in tokens if t]
    # Loại trùng nhưng giữ thứ tự
    unique_tokens = list(dict.fromkeys(filtered))
    return " | ".join(unique_tokens)


def percentile(values: list[float], p: float) -> float:
    """Tính phân vị (ví dụ P50, P95) cho danh sách độ trễ tính bằng mili-giây."""
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return round(ordered[int(k)], 3)
    return round(ordered[f] + (ordered[c] - ordered[f]) * (k - f), 3)


def seed_database(conn: psycopg.Connection, chunks: list[EvidenceChunk]) -> None:
    """Nạp toàn bộ bằng chứng đã duyệt vào bảng `evidence_chunks` trong PostgreSQL."""
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE evidence_chunks;")
        for ch in chunks:
            cur.execute(
                """
                INSERT INTO evidence_chunks (
                    evidence_id, tenant_id, sku_id, section, content,
                    knowledge_version, approval_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    ch.evidence_id,
                    ch.tenant_id,
                    ch.sku_id,
                    ch.section,
                    ch.content,
                    ch.knowledge_version,
                    ch.approval_status.value,
                ),
            )
    conn.commit()


def search_fts(
    conn: psycopg.Connection,
    tenant_id: str,
    sku_id: str,
    query: str,
    use_unaccent: bool,
    top_k: int = 5,
) -> list[tuple[str, str, float]]:
    """Tìm kiếm SKU-scoped bằng PostgreSQL Full-Text Search (raw hoặc unaccent)."""
    or_query = build_or_tsquery(query)
    if not or_query:
        return []

    if use_unaccent:
        sql = """
            WITH q AS (
                SELECT to_tsquery('simple', immutable_unaccent(%s)) AS tsq
            )
            SELECT e.evidence_id, e.sku_id, ts_rank_cd(e.tsv_unaccent, q.tsq) AS score
            FROM evidence_chunks e, q
            WHERE e.tenant_id = %s
              AND e.sku_id = %s
              AND e.approval_status = 'APPROVED'
              AND e.tsv_unaccent @@ q.tsq
            ORDER BY score DESC, e.evidence_id ASC
            LIMIT %s;
        """
    else:
        sql = """
            WITH q AS (
                SELECT to_tsquery('simple', %s) AS tsq
            )
            SELECT e.evidence_id, e.sku_id, ts_rank_cd(e.tsv_raw, q.tsq) AS score
            FROM evidence_chunks e, q
            WHERE e.tenant_id = %s
              AND e.sku_id = %s
              AND e.approval_status = 'APPROVED'
              AND e.tsv_raw @@ q.tsq
            ORDER BY score DESC, e.evidence_id ASC
            LIMIT %s;
        """

    with conn.cursor() as cur:
        cur.execute(sql, (or_query, tenant_id, sku_id, top_k))
        return [(row[0], row[1], float(row[2])) for row in cur.fetchall()]


def populate_embeddings_and_search_fn(
    conn: psycopg.Connection,
    chunks: list[EvidenceChunk],
    model_name: str = "intfloat/multilingual-e5-small",
):
    """Tải model embedding (nếu đã cài) để nạp vector vào `pgvector` và trả về hàm tìm kiếm."""
    try:
        from pgvector.psycopg import register_vector
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None, None

    register_vector(conn)
    print(f"Đang nạp model embedding '{model_name}' trên CPU...")
    model = SentenceTransformer(model_name, device="cpu")

    # Theo khuyến nghị của họ model E5: thêm tiền tố 'passage: ' cho đoạn văn bản
    passages = [f"passage: {c.content}" for c in chunks]
    vectors = model.encode(passages, normalize_embeddings=True)

    with conn.cursor() as cur:
        for ch, vec in zip(chunks, vectors):
            cur.execute(
                "UPDATE evidence_chunks SET embedding = %s WHERE evidence_id = %s;",
                (vec.tolist(), ch.evidence_id),
            )
    conn.commit()

    def search_dense(
        tenant_id: str, sku_id: str, query: str, top_k: int = 5
    ) -> list[tuple[str, str, float]]:
        # Tiền tố 'query: ' theo chuẩn E5
        q_vec = model.encode([f"query: {query}"], normalize_embeddings=True)[0].tolist()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT evidence_id, sku_id, 1 - (embedding <=> %s::vector) AS score
                FROM evidence_chunks
                WHERE tenant_id = %s
                  AND sku_id = %s
                  AND approval_status = 'APPROVED'
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector ASC
                LIMIT %s;
                """,
                (q_vec, tenant_id, sku_id, q_vec, top_k),
            )
            return [(row[0], row[1], float(row[2])) for row in cur.fetchall()]

    def search_hybrid_rrf(
        tenant_id: str, sku_id: str, query: str, top_k: int = 5, rrf_k: int = 60
    ) -> list[tuple[str, str, float]]:
        """Kết hợp thứ hạng FTS (unaccent) và Dense (pgvector) bằng Reciprocal Rank Fusion."""
        fts_hits = search_fts(conn, tenant_id, sku_id, query, use_unaccent=True, top_k=top_k)
        dense_hits = search_dense(tenant_id, sku_id, query, top_k=top_k)

        scores: dict[str, float] = {}
        sku_map: dict[str, str] = {}
        for rank, (eid, sid, _) in enumerate(fts_hits, start=1):
            scores[eid] = scores.get(eid, 0.0) + 1.0 / (rrf_k + rank)
            sku_map[eid] = sid
        for rank, (eid, sid, _) in enumerate(dense_hits, start=1):
            scores[eid] = scores.get(eid, 0.0) + 1.0 / (rrf_k + rank)
            sku_map[eid] = sid

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [(eid, sku_map[eid], score) for eid, score in ranked]

    return search_dense, search_hybrid_rrf


def evaluate_method(
    method_name: str,
    questions: list[dict[str, Any]],
    search_fn,
    tenant_id: str = "tenant-demo-01",
) -> dict[str, Any]:
    """Chấm điểm một phương pháp truy xuất trên toàn bộ câu hỏi và tách theo từng nhóm."""
    latencies_ms: list[float] = []
    cross_sku_leaks = 0
    group_stats: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []

    for q in questions:
        grp = q["group"]
        if grp not in group_stats:
            group_stats[grp] = {"n": 0, "hit_at_1": 0, "hit_at_3": 0, "mrr_sum": 0.0, "latencies": []}

        t0 = time.perf_counter()
        hits = search_fn(tenant_id, q["target_sku_id"], q["query"], top_k=5)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(elapsed_ms)

        # Kiểm tra bất biến: tuyệt đối không được trả về bằng chứng thuộc SKU khác
        for _, hit_sku, _ in hits:
            if hit_sku != q["target_sku_id"]:
                cross_sku_leaks += 1

        gold = set(q["gold_evidence_ids"])
        hit_ids = [eid for eid, _, _ in hits]

        hit1 = 1 if (hit_ids and hit_ids[0] in gold) else 0
        hit3 = 1 if any(eid in gold for eid in hit_ids[:3]) else 0
        rr = 0.0
        for rank, eid in enumerate(hit_ids, start=1):
            if eid in gold:
                rr = 1.0 / rank
                break

        st = group_stats[grp]
        st["n"] += 1
        st["hit_at_1"] += hit1
        st["hit_at_3"] += hit3
        st["mrr_sum"] += rr
        st["latencies"].append(elapsed_ms)

        if hit1 == 0:
            failures.append(
                {
                    "qid": q["qid"],
                    "group": grp,
                    "sku_id": q["target_sku_id"],
                    "query": q["query"],
                    "gold": list(gold),
                    "top3_predicted": hit_ids[:3],
                }
            )

    total_n = len(questions)
    summary_by_group = {}
    for grp, st in group_stats.items():
        n = st["n"]
        summary_by_group[grp] = {
            "count": n,
            "recall_at_1": round(st["hit_at_1"] / n, 4),
            "recall_at_3": round(st["hit_at_3"] / n, 4),
            "mrr": round(st["mrr_sum"] / n, 4),
            "p95_ms": percentile(st["latencies"], 95),
        }

    overall_r1 = round(sum(s["hit_at_1"] for s in group_stats.values()) / total_n, 4)
    overall_r3 = round(sum(s["hit_at_3"] for s in group_stats.values()) / total_n, 4)
    overall_mrr = round(sum(s["mrr_sum"] for s in group_stats.values()) / total_n, 4)

    return {
        "method": method_name,
        "overall": {
            "count": total_n,
            "recall_at_1": overall_r1,
            "recall_at_3": overall_r3,
            "mrr": overall_mrr,
            "p50_ms": percentile(latencies_ms, 50),
            "p95_ms": percentile(latencies_ms, 95),
            "cross_sku_leaks": cross_sku_leaks,
        },
        "by_group": summary_by_group,
        "miss_at_1_count": len(failures),
        "sample_misses": failures[:10],
    }


def main() -> None:
    seed_raw = json.loads((BASE_DIR / "data" / "catalog_seed.json").read_text(encoding="utf-8"))
    chunks = [EvidenceChunk(**c) for c in seed_raw["evidence_chunks"]]

    q_raw = json.loads((E02_DIR / "e02_questions.json").read_text(encoding="utf-8"))
    questions = q_raw["questions"]

    print("=== CHẠY THÍ NGHIỆM P05-E02: BENCHMARK RETRIEVAL (POSTGRESQL FTS VS PGVECTOR) ===")
    with psycopg.connect(DB_DSN) as conn:
        seed_database(conn, chunks)
        print(f"Đã nạp {len(chunks)} bằng chứng vào PostgreSQL (port 5439). Tổng số câu hỏi: {len(questions)}.")

        results: list[dict[str, Any]] = []

        # 1. Baseline A: PostgreSQL FTS gốc (không unaccent)
        res_fts_raw = evaluate_method(
            "postgres_fts_raw",
            questions,
            lambda tid, sid, q, top_k=5: search_fts(conn, tid, sid, q, use_unaccent=False, top_k=top_k),
        )
        results.append(res_fts_raw)

        # 2. Baseline B: PostgreSQL FTS + unaccent (xử lý tiếng Việt không dấu)
        res_fts_unaccent = evaluate_method(
            "postgres_fts_unaccent",
            questions,
            lambda tid, sid, q, top_k=5: search_fts(conn, tid, sid, q, use_unaccent=True, top_k=top_k),
        )
        results.append(res_fts_unaccent)

        # 3. Ứng viên C & D: pgvector Dense & Hybrid RRF (nếu đã cài sentence-transformers + pgvector)
        search_dense, search_hybrid = populate_embeddings_and_search_fn(conn, chunks)
        pgvector_ran = False
        if search_dense is not None and search_hybrid is not None:
            pgvector_ran = True
            results.append(evaluate_method("pgvector_e5_small_dense", questions, search_dense))
            results.append(evaluate_method("hybrid_fts_unaccent_plus_pgvector_rrf", questions, search_hybrid))
        else:
            print(
                "[LƯU Ý] Chưa cài `sentence-transformers` hoặc `pgvector` trong Python, "
                "tạm bỏ qua nhánh Embeddings và chỉ báo cáo PostgreSQL FTS."
            )

    print("\n--- BẢNG SO SÁNH TỔNG QUAN ---")
    print(f"{'Phương pháp':40s} | {'R@1':6s} | {'R@3':6s} | {'MRR':6s} | {'P95(ms)':8s} | {'CrossSKU':8s}")
    print("-" * 88)
    for r in results:
        ov = r["overall"]
        print(
            f"{r['method']:40s} | {ov['recall_at_1']:6.3f} | {ov['recall_at_3']:6.3f} | "
            f"{ov['mrr']:6.3f} | {ov['p95_ms']:8.2f} | {ov['cross_sku_leaks']:8d}"
        )

    print("\n--- PHÂN TÁCH THEO NHÓM CÂU HỎI (Recall@1) ---")
    for r in results:
        grp_str = " | ".join(
            f"{g}: R@1={st['recall_at_1']:.3f} (R@3={st['recall_at_3']:.3f})"
            for g, st in r["by_group"].items()
        )
        print(f"- {r['method']}: {grp_str}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest = ExperimentManifest(
        experiment_id="P05-E02",
        run_id=run_id,
        dataset_source="e02_retrieval/e02_questions.json (45 câu) + data/catalog_seed.json (9 chunks)",
        is_synthetic=True,
        environment={
            "python": platform.python_version(),
            "os": platform.platform(),
            "processor": platform.processor(),
            "postgres_image": "pgvector/pgvector:pg16",
        },
        config={
            "top_k": 5,
            "sku_scoped_filter": True,
            "pgvector_enabled": pgvector_ran,
            "embedding_model": "intfloat/multilingual-e5-small" if pgvector_ran else None,
        },
        metrics={"methods": results},
        decision="INCONCLUSIVE" if not pgvector_ran else "TO_REVIEW",
        notes=(
            "Benchmark trên 45 câu hỏi synthetic (3 nhóm: có dấu, không dấu/slang, diễn đạt đồng nghĩa). "
            "Cần mở rộng lên 100-200 câu và bổ sung tài liệu thật trước khi chốt quyết định OPEN-2."
        ),
    )

    runs_dir = BASE_DIR / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    out_path = runs_dir / f"P05-E02_{run_id}.json"
    out_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    print(f"\nĐã lưu manifest tại: {out_path}")


if __name__ == "__main__":
    main()
