# Báo cáo kết quả thí nghiệm PoC — Module P05 (Product Knowledge, Claims & Publication Gate)

| Mục | Thông tin |
| :--- | :--- |
| **Mã module** | P05 — Tri thức sản phẩm, kiểm chứng tuyên bố (Claims) & Cổng phát ngôn (Publication Gate) |
| **Phiên bản báo cáo** | v0.1 (Vòng PoC đầu tiên trên dữ liệu `synthetic`) |
| **Ngày thực hiện** | 21/11/2026 |
| **Trạng thái tiến độ** | `IN EXPERIMENT` *(đã chạy đủ 4/4 thí nghiệm vòng 1; chưa nâng lên `VALIDATED` do chờ dữ liệu thật & reviewer duyệt)* |
| **Rủi ro liên quan** | R08 (Claims/giá sai), R16 (OCOP giả/chưa xác minh), R17 (Thực phẩm đóng gói / công dụng chữa bệnh) |
| **Gate liên quan** | Hard Gate G3 (Tính đúng phiên bản khi commit), Hard Gate G4 (An toàn claims, quyền, OCOP, cô lập tenant) |
| **Mốc tham chiếu** | M4 |

---

## 1. Tóm tắt điều hành (Executive Summary)

Vòng thí nghiệm PoC đầu tiên của **P05** đã triển khai và đo đạc đầy đủ cả 4 bài toán **P05-E01, P05-E02, P05-E03 và P05-E04** trên máy local không có GPU rời (**Intel Core Ultra 5 125H, CPU-only**) kết hợp container **PostgreSQL 16 + `pgvector`** qua Docker:

* **Hard Gate G3 & G4 (`P05-E03`, `P05-E04`):** Đạt **100% PASS** (`0 unsafe commits`, `0 false positives`, `0 stale candidate leaks`). Cổng phát ngôn *fail-closed* đã chặn thành công toàn bộ 10 kịch bản độc hại (sai giá, giấu giá sai trong câu, claim chữa bệnh, OCOP `PENDING`, chéo SKU, thiếu bằng chứng, prompt injection, lệch tenant, thu hồi quyền) và chặn 100% các câu thoại bị lỗi thời do đổi giá/OCOP/quyền giữa lúc sinh TTS và lúc phát (TOCTOU).
* **Retrieval (`P05-E02`):** Đã có bằng chứng định lượng rõ ràng cho câu hỏi mở **OPEN-2**. Phương pháp kết hợp **Hybrid (`postgres_fts_unaccent` + `pgvector` `intfloat/multilingual-e5-small` qua RRF)** đạt kết quả cao nhất (**Recall@1 = 0.822**, **Recall@3 = 1.000**, **MRR = 0.907**, **0 rò rỉ chéo SKU**) với độ trễ P95 chỉ **41.27 ms** trên CPU.
* **Extraction (`P05-E01`):** **Docling** đạt **92.5% Exact Match** (37/40 trường) trên 10 tài liệu đa định dạng (5 DOCX + 5 PDF tiếng Việt). Đáng chú ý, 3 trường thương mại/pháp lý nhạy cảm nhất (`price_vnd`, `weight`, `expiry`) đạt **100% (10/10)**; toàn bộ 3 lỗi đều rơi vào trường text tự do `origin` trên PDF do khác biệt cách xuất bảng/gộp dòng Markdown — khẳng định sự cần thiết của luồng **`Docling -> DRAFT -> Human Review`**.

---

## 2. Môi trường thực nghiệm & Khả năng tái lập

| Thành phần | Cấu hình thực tế |
| :--- | :--- |
| **Phần cứng** | Laptop Windows 11, CPU Intel Core Ultra 5 125H (không sử dụng GPU rời) |
| **Python / Venv** | Python `3.13.2` trong `.venv` riêng |
| **Thư viện chính** | `pydantic 2.14.4`, `psycopg[binary] 3.3.9`, `pgvector 0.5.1`, `torch 2.15.0+cpu`, `sentence-transformers 6.3.0`, `docling 2.151.1` |
| **Cơ sở dữ liệu** | Docker image `pgvector/pgvector:pg16` (cổng local `5439`, kích hoạt `unaccent` và `vector`) |
| **Nguồn dữ liệu** | 100% dữ liệu tổng hợp gắn nhãn `synthetic_for_poc_validation` (`is_synthetic: true`) |

**Mã nguồn & Dữ liệu chính:**
* Hợp đồng dữ liệu PoC: [schemas.py](schemas.py)
* Logic Cổng phát ngôn & Kho tri thức có phiên bản: [publication_gate.py](publication_gate.py)
* Bộ dữ liệu nền: [data/catalog_seed.json](data/catalog_seed.json), [data/eval_questions.json](data/eval_questions.json)

---

## 3. Kết quả chi tiết 4 thí nghiệm

### 3.1. `P05-E01` — Độ chính xác trích xuất tài liệu (Docling)
* **Cách chạy:** `.venv\Scripts\python.exe e01_extraction/generate_sample_docs.py` $\to$ `.venv\Scripts\python.exe e01_extraction/run_e01.py`
* **Dữ liệu:** 10 tài liệu sản phẩm thực phẩm đóng gói (5 DOCX + 5 PDF tiếng Việt có dấu Unicode, nhiều kiểu bố cục bảng, văn xuôi, gạch đầu dòng, nhãn bao bì và định dạng giá khác nhau).
* **Bằng chứng (Manifest):** [runs/P05-E01_20261121T073009Z.json](runs/P05-E01_20261121T073009Z.json)

| Trường dữ liệu | Exact Match | Ghi chú |
| :--- | :---: | :--- |
| `price_vnd` (Giá bán) | **10 / 10 (100.0%)** | Nhận diện đúng cả `159.000 đ`, `245,000 VNĐ`, `185k`, `95k` |
| `weight` (Khối lượng / dung tích) | **10 / 10 (100.0%)** | Nhận diện đúng `500ml`, `100g`, `0.5 kg`, `500 gram` |
| `expiry` (Hạn sử dụng) | **10 / 10 (100.0%)** | Nhận diện đúng `12 tháng`, `18 tháng`, `24 tháng` |
| `origin` (Xuất xứ) | **7 / 10 (70.0%)** | 3 lỗi chỉ xuất hiện trên PDF (DOCX đạt 5/5) |
| **Tổng cộng** | **37 / 40 (92.5%)** | **DOCX: 100.0% (0.09–0.30s/file)** \| **PDF: 85.0% (3.44–15.28s warm)** |

* **Phân tích 3 lỗi trên PDF (mức độ thấp — không phải lỗi hệ thống nghiêm trọng):**
  1. `doc06_honey_spec.pdf` & `doc09_ginger_tea.pdf`: `origin` ra `None` do cách Docling xuất bảng 2 cột không có dòng tiêu đề khác mẫu regex tìm cột Markdown.
  2. `doc08_cashew_label.pdf`: Docling gộp dòng `- Xuất xứ: Bình Phước` và `- Chi tiết: ...` thành cùng một đoạn, khiến regex đọc tràn chữ.
  * *Đánh giá:* Không ảnh hưởng Hard Gate vì mọi bản trích xuất đều bị khóa ở trạng thái `ApprovalStatus.DRAFT` chờ người duyệt. Ở vòng sau nên đọc trực tiếp cấu trúc `doc.tables` của Docling thay vì chỉ dùng regex trên Markdown phẳng.
  * *Lưu ý hiệu năng:* File PDF đầu tiên mất `97.57s` do *cold start* (lần đầu tải model `docling-layout-heron` & `docling-models`); các file PDF sau chạy *warm* chỉ mất `3.44s–15.28s` trên CPU.

---

### 3.2. `P05-E02` — Benchmark Retrieval (PostgreSQL FTS vs `pgvector`)
* **Cách chạy:** `docker compose -f e02_retrieval/docker-compose.yml up -d` $\to$ `.venv\Scripts\python.exe e02_retrieval/run_e02.py`
* **Dữ liệu:** 9 `EvidenceChunk` của 3 SKU (lọc cứng `WHERE tenant_id = ... AND sku_id = ...` trước khi tìm kiếm), kiểm thử trên **45 câu hỏi** chia đều 3 nhóm (15 có dấu chuẩn, 15 không dấu/slang livestream, 15 diễn đạt đồng nghĩa ít trùng từ khóa).
* **Bằng chứng (Manifest):** [runs/P05-E02_20261121T055725Z.json](runs/P05-E02_20261121T055725Z.json)

| Phương pháp | Recall@1 | Recall@3 | MRR | P95 (ms) | Cross-SKU Leaks |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `postgres_fts_raw` | 0.733 | 0.867 | 0.800 | **2.48 ms** | **0** |
| `postgres_fts_unaccent` | 0.778 | 0.978 | 0.878 | **2.80 ms** | **0** |
| `pgvector_e5_small_dense` | 0.778 | **1.000** | 0.885 | 42.80 ms | **0** |
| **`hybrid_fts_unaccent_plus_pgvector_rrf`** | **0.822** | **1.000** | **0.907** | 41.27 ms | **0** |

**Phân tách Recall@1 theo nhóm câu hỏi:**
* **Có dấu chuẩn (`diacritics`):** `fts_raw` đạt `0.933`; cả 3 phương pháp còn lại đạt `0.867` (`R@3 = 1.000`).
* **Không dấu & slang (`no_diacritics_slang`):** `fts_raw` tụt mạnh xuống `0.600`; **`fts_unaccent` nhảy vọt lên `0.933`**; thuần `pgvector` chỉ đạt `0.667`.
* **Diễn đạt đồng nghĩa (`semantic_paraphrase`):** `fts_unaccent` giảm xuống `0.533`; **`pgvector` vọt lên `0.800`**.
* **Kết luận cho OPEN-2:** Không dùng `fts_raw` và không thay hoàn toàn FTS bằng thuần `pgvector`. Nếu mỗi SKU chỉ có rất ít đoạn bằng chứng và P06 nhận `top-3`, `postgres_fts_unaccent` (`R@3 = 0.978`, `2.8 ms`) là baseline cực gọn nhẹ. Khi kho bằng chứng dày hơn và nhiều câu đồng nghĩa, **Hybrid RRF (`fts_unaccent` + `pgvector`)** cho độ chính xác cao nhất (`R@1 = 0.822`, `MRR = 0.907`, `R@3 = 1.000`) với độ trễ CPU ~41 ms (rất nhỏ so với ngân sách 7–10 giây toàn luồng W1).

---

### 3.3. `P05-E03` — Kiểm chứng chặn Claims không an toàn (Hard Gate G4)
* **Cách chạy:** `python e03_claims_gate/run_e03.py`
* **Dữ liệu:** 13 kịch bản (3 ca hợp lệ `ALLOW` + 10 ca độc hại/tấn công `BLOCK`).
* **Bằng chứng (Manifest):** [runs/P05-E03_20261121T050419Z.json](runs/P05-E03_20261121T050419Z.json)
* **Kết quả:** **13/13 PASS** | `unsafe_commits = 0` | `false_positives = 0`.
  * Chặn thành công: sai giá khai báo (`120.000đ`), giấu `stated_price_vnd=None` nhưng đọc sai giá `99k` trong câu, claim chữa đau dạ dày/tiểu đường/ung thư (R17), phát ngôn cho SKU `OCOP PENDING` (R16), trích dẫn chéo SKU, thiếu bằng chứng, prompt injection, lệch tenant (R10) và thu hồi quyền tài sản (R09).

---

### 3.4. `P05-E04` — Kiểm chứng chống lỗi TOCTOU trước thời điểm phát (Hard Gate G3)
* **Cách chạy:** `python e04_toctou/run_e04.py`
* **Dữ liệu:** 4 kịch bản dòng thời gian `t0 (duyệt trước TTS) -> t1 (đổi dữ liệu) -> t2 (kiểm tra lại sát commit)`.
* **Bằng chứng (Manifest):** [runs/P05-E04_20261121T050420Z.json](runs/P05-E04_20261121T050420Z.json)
* **Kết quả:** **4/4 PASS** | `stale_candidate_leaks = 0`.
  * `E04-S01`: Đổi giá mật ong `159.000đ (v1) -> 175.000đ (v2)` sau khi TTS xong $\to$ bị chặn ở `t2` với `[STALE_KNOWLEDGE_VERSION, PRICE_MISMATCH]`.
  * `E04-S02`: P09 thu hồi OCOP (`VERIFIED v1 -> REVOKED v2`) $\to$ bị chặn ở `t2` với `[STALE_OCOP_VERSION, OCOP_NOT_VERIFIED]`.
  * `E04-S03`: P11 thu hồi quyền (`ACTIVE v1 -> REVOKED v2`) $\to$ bị chặn ở `t2` với `[STALE_RIGHTS_VERSION, RIGHTS_INVALID]`.
  * `E04-S04`: Đối chứng không đổi dữ liệu $\to$ `t0 = ALLOW`, `t2 = ALLOW`, giữ nguyên dấu vết audit nối version.

---

## 4. Giới hạn còn mở & Điều kiện để chuyển sang `VALIDATED`

Theo nguyên tắc Stage 03, các kết quả trên **chưa đủ để đánh dấu P05 là `VALIDATED`**. Những giới hạn cần đóng tiếp trước khi đưa vào `apps/api/src/hostra_api/modules/knowledge/`:

1. **Dữ liệu thật (OPEN-1):** Toàn bộ 4 thí nghiệm vòng 1 dùng dữ liệu `synthetic`. Cần chạy lại `P05-E01` trên 10–20 tài liệu thật của merchant (bao gồm **PDF scan / ảnh chụp nhãn thực phẩm** cần OCR) để đo độ chính xác thực tế và chi phí human review.
2. **Quy mô bộ test Retrieval (OPEN-2):** `P05-E02` mới chạy trên 9 chunks / 45 câu hỏi nên `Recall@3` chạm trần (`0.978–1.000`). Cần mở rộng lên **100–200 câu hỏi thật** trên kho tài liệu dày hơn để chốt dứt khoát giữa `postgres_fts_unaccent` và `Hybrid RRF`.
3. **Lớp kiểm tra ngữ nghĩa & Tích hợp thật (OPEN-3):** `P05-E03` hiện kiểm tra lớp *deterministic fail-closed*; cần đánh giá thêm lớp kiểm tra groundedness (vd: LLM/Ragas) cho các câu nói bịa tinh vi không rơi vào danh sách từ cấm. `P05-E04` cần kiểm chứng lại trên **PostgreSQL transaction thật** khi tích hợp với P08 ở Stage 06.
4. **Phê duyệt độc lập:** Cần reviewer rà soát 4 manifest và chính sách xác minh nguồn OCOP độc lập từ P09 trước khi ký duyệt `GO` ở mức hệ thống.

---

## 5. Đề xuất quyết định vòng PoC v0.1

* **Trạng thái khuyến nghị:** **TIẾP TỤC HƯỚNG THIẾT KẾ HIỆN TẠI (`PROCEED / IN EXPERIMENT`)** — kiến trúc *Hybrid Structured Facts + PostgreSQL FTS (`unaccent`) / Optional `pgvector` Hybrid RRF + Fail-Closed Versioned Publication Gate* hoạt động đúng như kỳ vọng trên CPU local, chưa phát hiện điểm nghẽn kiến trúc nào buộc phải đổi phương án.
* **Bước tiếp theo ưu tiên:** Giữ nguyên hợp đồng `schemas.py` làm chuẩn giao tiếp sang **P06 (Autonomous Storytelling)** và **P08/P09 (Orchestration & OCOP Eligibility)**; bổ sung bộ tài liệu thật và nâng cấp parser `doc.tables` cho `P05-E01` ở vòng kiểm định tiếp theo.
