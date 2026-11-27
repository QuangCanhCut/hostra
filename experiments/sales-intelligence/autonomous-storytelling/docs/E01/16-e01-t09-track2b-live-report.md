# P06-E01-T09 — Báo cáo Thực thi & Phân tích Live Track 2B: Large Window Sensitivity (`W=10` vs `W=20`, `lag=12`)

**Trạng thái:** `TRACK 2B LIVE COMPLETED` · **Cổng tổng thể:** `NOT_EVALUATED` *(`Human Blind Evaluation` & `GoldFactualLabel` = `PENDING`)* · **Mốc tiếp theo:** `AWAITING_COMBINED_TRACK2_REVIEW_AND_E01_FINALIZATION`  
**Ngày thực thi:** `2026-11-27` (`03:29:57Z → 03:41:00Z`) · **Nhánh:** `research/p06-autonomous-storytelling` · **Mô hình:** `gemini-3.5-flash-lite` (Free Tier, `0.00 USD`, dữ liệu `SYNTHETIC`)

---

## 1. Tóm tắt Điều hành

Phiên chạy **Live Track 2B — Large Window Sensitivity** kiểm tra giả thuyết biên đối xứng ở quy mô lớn hơn (`planned_lag = 12`, `min_chunks_per_topic = 2`, `36` chủ đề bắt buộc qua `3` SKU thuộc `window_stress_12lag_3sku`, `seed = 42`) trên cặp **`langgraph_w10`** (`W=10 < lag=12`) so với **`langgraph_w20`** (`W=20 > lag=12`).

Thực nghiệm sử dụng tổng cộng **`111 / 200` API requests** (tuân thủ nghiêm ngặt operational hard cap `<= 200` requests của người dùng thông qua `budget_ledger.json` khởi tạo trước khi chạy mà **không** chỉnh sửa tệp YAML cấu hình đã khóa SHA-256), chi phí thực tế **`0.00 USD`**, **`0` HTTP 429** (`rate_limited = false`), **`1` HTTP 503** đơn lẻ ở `W=20` (`call_index = 24`) và **`0` secret leak**.

Kết quả lặp lại **đối xứng hoàn toàn** quy luật chuyển pha cấu trúc của Track 2A:
- **`W=10` (`< lag=12`):** Hoàn tất **`36 / 36` chủ đề** (`100.0%` `mandatory_topic_coverage`, `72` lượt phát, `83` requests, `EARLY_COMPLETION`), `100%` lượt lặp lại rơi đúng ở **`actual_lag = 12` (`0` lượt lọt vào cửa sổ `W=10`)**, dẫn đến `0` lần `RepetitionDetector` từ chối nhưng để lọt **`1` exact normalized text replay** ngoài cửa sổ (`lag=12`) và **`32.39%` `lexical_repetition_rate`**, khiến `windowed_ngram3_jaccard_mean` nhảy vọt **~18.8×** (`18.78×` trên giá trị thô) từ **`0.0131` (`w10`)** lên **`0.2455` (`w20`)**.
- **`W=20` (`> lag=12`):** Đổ vỡ ngay tại lần quay lại đầu tiên của `SKU-HONEY-01` (`turn_index = 12..16`), dừng sớm ở **`28` requests** với **`MAX_CONSECUTIVE_ABORTS`** (`0 / 36` chủ đề đạt >= 2 chunks, `12` chủ đề Honey dừng ở 1 chunk, `24` chủ đề Tea & Macadamia chưa kịp chạm tới), phát sinh `11` lần `REPEATED_FACTS:SWITCH_TOPIC`, `2` lần `LEXICAL_DUPLICATION:REWRITE`, cạn cả `2` lượt `PREAPPROVED_FALLBACK` của Honey tại `tr[12..13]` và `3` lượt `SAFE_ABORT_NO_CANDIDATE` liên tiếp tại `tr[14..16]`.

---

## 2. Tuân thủ Giao thức, Cap `200` Requests & Ngân sách Telemetry

- **Cơ chế áp cap `<= 200` requests:** Trước khi kích hoạt `run_gemini_formal_batch.py --allow-live-provider`, tệp [`budget_ledger.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/formal_benchmark_v1/track2b_large_window_lag12_s42/budget_ledger.json) được khởi tạo với `global_max_requests = 200` và `max_requests_per_run = 200`, giữ nguyên khóa SHA-256 của [`p06_e01_formal_track2b_w10_w20.yaml`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/configs/experiments/p06_e01_formal_track2b_w10_w20.yaml) (`b4e6c539e1f316219e86d35532c3e0dde0e3a993c41c7ffd1897d287221354b4`).
- **Tình trạng thực thi tuần tự (`sequential`, `min_request_interval_sec = 6.0`):**

| Thứ tự | Nhãn Run | Run ID (rút gọn) | Cửa sổ `W` | Requests Attempted | Run Cap Còn Lại | Kết thúc | HTTP 429 | HTTP 503 | Chi phí |
|---:|---|---|---:|---:|---:|---|---:|---:|---:|
| 1 | `langgraph_w10` | `...__w10__...__601e3e7a` | 10 | **83** | 200 | `EARLY_COMPLETION` | 0 | 0 | `0.0 USD` |
| 2 | `langgraph_w20` | `...__w20__...__c0cbfff5` | 20 | **28** | 117 | `MAX_CONSECUTIVE_ABORTS` | 0 | 1 (`[c24]`) | `0.0 USD` |
| **Tổng** | **Track 2B Live** | `track2b_large_window_lag12_s42` | — | **111 / 200** | còn `89` | `COMPLETED` | **0** | **1** | **`0.0 USD`** |

---

## 3. So sánh Đối cặp Live Track 2B (`W=10` vs `W=20`, `lag=12`)

Số liệu đối soát trực tiếp từ `comparison.json`, `metrics.json`, `token_usage.json`, `provider_calls.jsonl` và `graph_trace.jsonl`:

| Nhóm Metric | Chỉ số | `langgraph_w10` (`W=10`) | `langgraph_w20` (`W=20`) |
|---|---|---:|---:|
| **Bao phủ & Thời lượng** | `termination_reason` | `EARLY_COMPLETION` | `MAX_CONSECUTIVE_ABORTS` |
| | `completed_topics (>=2 chunks)` | **`36 / 36`** (`12` Honey, `12` Tea, `12` Macadamia) | **`0 / 36`** (`12` Honey partial 1; `24` missing) |
| | `mandatory_topic_coverage` | **`1.0000`** (`36/36`) | **`0.0000`** (`0/36`) |
| | `declared_verified_claim_coverage` | **`1.0000`** (`21/21`) | **`0.3333`** (`7/21`) |
| | `transcript_turns` / `content_traces` | `72` / `72` | `14` / `17` |
| | `simulated_played_duration_sec` (`% of 600s`) | **`489.996s`** (`81.67%`) | **`94.229s`** (`15.70%`) |
| **Lặp & Đa dạng** | `exact_chunk_replay_count` | `0` | `0` |
| | `exact_normalized_text_replay_count` | **`1`** | `0` |
| | `outside_window_exact_text_replay_count` | **`1`** (`lag=12`) | `0` |
| | `lexical_repetition_rate` | **`0.3239`** (`32.39%`) | `0.0000` *(chỉ phát lượt đầu + fallback)* |
| | `max_prior_word_jaccard` (mean / p95 / max) | `0.4428` / `0.8997` / `1.0000` | `0.1386` / `0.3722` / `0.5417` |
| | `max_prior_ngram3_jaccard` (mean / p95 / max) | `0.2466` / `0.7256` / `1.0000` | `0.0354` / `0.1399` / `0.2963` |
| | `windowed_ngram3_jaccard_mean` (`w5` / `w10` / `w20`) | `0.0094` / **`0.0131`** / **`0.2455`** | `0.0328` / `0.0328` / `0.0354` |
| | `distinct_1` / `distinct_2` / `distinct_3` | `0.2776` / `0.5519` / `0.6629` | `0.6534` / `0.8650` / `0.9327` |
| | `claim_overlap_rate` | `0.7183` (`71.83%`) | `0.4545` (`45.45%`) |
| **Độ tin cậy & An toàn** | `total_model_calls` (`measured` / `failed`) | `83` (`83` / `0`) | `28` (`27` / `1` HTTP 503 `[c24]`) |
| | `wasted_calls` / `total_calls` | `11 / 83` (`13.25%`) | **`16 / 28`** (`57.14%`) |
| | `rewrite_count` (`rewrite_rate`) | `11` (`0.1528`) *(100% `OVER_MAX_DURATION_SEC`)* | `11` (`0.4118`) |
| | `fallback_count` (`fallback_rate`) | `0` (`0.0000`) | `2` (`0.1176`) |
| | `safe_abort_count` (`safe_abort_rate`) | `0` (`0.0000`) | **`3`** (`0.1765`) |
| | `p05_rejection_count` / `retry_budget_violations` | `0` / `0` | `0` / `0` |
| | `structural_hard_gates_status` / `overall_gate_status` | `PASS` / `NOT_EVALUATED` | `PASS` / `NOT_EVALUATED` |
| **Hiệu năng & Token** | `provider_latency` `p50` / `p95` (`ms`) | `5,903.3` / `6,465.4` | `5,934.1` / `7,391.3` |
| | `aggregate_token_usage_source` | **`MEASURED`** | **`UNAVAILABLE`** *(`1` failed call)* |
| | `input_tokens` / `output_tokens` *(measured)* | **`281,423`** / **`9,919`** (`291,342` tổng) | *partial* `89,237` / `3,185` (`92,422` trên `27/28` calls) |
| | `wasted_tokens` *(measured)* | `39,346` | *partial* `55,044` (`15` wasted measured calls) |

---

## 4. Phân tích `Actual Lag`, Cơ chế Ranh giới `W` và Vòng xoáy Bế tắc `W=20`

1. **Ở `W=10`:** Cả `36 / 36` lượt quay lại chủ đề đều phát thành công ở **`actual_lag = 12`** (`lag_dist = {12: 36}`, mỗi SKU `12` chủ đề đi hết vòng 1 từ `pos 0..11`, `24..35`, `48..59` rồi quay lại vòng 2 ở `pos 12..23`, `36..47`, `60..71`). Do `actual_lag = 12 > W = 10` trên **100% số cặp**, `RepetitionDetector` ghi nhận `NONE / ALLOW = 72/72` (`0` lần từ chối). Hệ quả trực tiếp:
   - Câu thoại `topic-formal-honey-10` ở `t[9]` và `t[21]` lặp **nguyên văn** (*`"Sản phẩm đạt chứng nhận OCOP 4 sao và an toàn thực phẩm tuyệt đối."`*, `exact_normalized_text_replay_count = 1`, `outside_window_exact_text_replay_count = 1`, `lag = 12`).
   - `windowed_ngram3_jaccard_mean` giữ ở mức thấp `0.0094` (`w5`) và `0.0131` (`w10`), rồi bật tăng **~18.8×** (`0.013074 → 0.245489`) lên **`0.2455` (`w20`)** ngay khi cửa sổ quan sát mở rộng qua ngưỡng `lag=12`.
   - Toàn bộ `11` lần retry trong `W=10` (`tr[7], tr[8], tr[14], tr[20], tr[31], tr[36], tr[40], tr[43], tr[48], tr[51], tr[68]`) đều **không** do lặp mà **11/11** xuất phát từ `OVER_MAX_DURATION_SEC` (bản nháp dài `21–27` từ / `8.08s–10.38s` > ngưỡng `8.00s`), tiêu tốn `39,346` `wasted_tokens`.

2. **Ở `W=20`:** `12` lượt đầu (`tr[0..11]`) hoàn tất trọn vẹn chunk 1 của `SKU-HONEY-01`. Nhưng kể từ `tr[12]`, cả `12` chủ đề Honey đã nói ở `tr[0..11]` đều nằm trong `history_window = 20` (`actual_lag = 11..14 <= 20`) và mỗi chủ đề chỉ có đúng `1` `allowed_claim_id`. Vòng xoáy sụp đổ diễn ra trong đúng `5` turns:
   - **`tr[12]` (`honey-01`):** `attempt 0..1` bị `LEXICAL_DUPLICATION:REWRITE` (`fact_overlap = 1.0`, `word_jaccard = 0.682 / 0.500`), `attempt 2` bị `REPEATED_FACTS:SWITCH_TOPIC` (`fact_overlap = 1.0`) → rơi vào `PREAPPROVED_FALLBACK` #1 (`159.000đ`).
   - **`tr[13]` (`honey-01 → 02 → 03`):** cả `3` attempts đều bị `REPEATED_FACTS:SWITCH_TOPIC` (`fact_overlap = 1.0`) → rơi vào `PREAPPROVED_FALLBACK` #2 (cạn toàn bộ quỹ `2` fallback của `SKU-HONEY-01`).
   - **`tr[14]` (`SAFE_ABORT` #1):** `3` attempts (`honey-01, 02, 03`) đều `REPEATED_FACTS:SWITCH_TOPIC`; hết fallback → `SAFE_ABORT_NO_CANDIDATE`.
   - **`tr[15]` (`SAFE_ABORT` #2):** `attempt 0` (`honey-01`) bị `REPEATED_FACTS:SWITCH_TOPIC`; `attempt 1` (`honey-02`, `call_index = 24`) gặp lỗi nhất thời `HTTP 503 UNAVAILABLE` từ API → `NON_RETRYABLE_FAILURE` → `SAFE_ABORT_NO_CANDIDATE`.
   - **`tr[16]` (`SAFE_ABORT` #3):** `3` attempts (`honey-01, 02, 03`) đều `REPEATED_FACTS:SWITCH_TOPIC` → `SAFE_ABORT_NO_CANDIDATE` → chạm ngưỡng **`MAX_CONSECUTIVE_ABORTS`** (`3` abort liên tiếp), khóa cứng ở `0 / 36` chủ đề hoàn thành.

---

## 5. So sánh Unit-Test Mock vs Gemini Live (`mock_vs_live_comparison.csv`)

| Cửa sổ `W` | Nguồn | Total Calls | HTTP 503 | `REPEATED_FACTS` | `LEXICAL_DUP` | `EXACT_REPLAY` | Rewrites | Fallbacks | Safe Aborts | Topics >=2 | Termination |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 10 | `unit_test_mock` | 102 | 0 | 0 | 23 | 7 | 28 | 2 | 0 | `36/36` | `EARLY_COMPLETION` |
| 10 | `gemini_live` | **83** | 0 | 0 | **0** | **0** | **11** | **0** | **0** | **`36/36`** | `EARLY_COMPLETION` |
| 20 | `unit_test_mock` | 156 | 0 | 33 | 44 | 8 | 58 | 6 | 21 | `35/36` | `MAX_CONSECUTIVE_ABORTS` |
| 20 | `gemini_live` | **28** | 1 | **11** | **2** | **0** | **11** | **2** | **3** | **`0/36`** | `MAX_CONSECUTIVE_ABORTS` |

Deterministic Mock ở `W=20` đi được `156` calls (`35/36` trước khi abort ở `macadamia-12`), trong khi **Gemini Live ở `W=20` sụp sớm ngay tại `28` calls (`0/36`)**. Nguyên nhân nhất quán với Track 2A: LLM thật bám sát đúng `covered_claim_ids` nên ở `tr[12..13]` kích hoạt ngay `REPEATED_FACTS` (`fact_overlap = 1.0`) trên cả `3` lần thử liên tiếp, tiêu hết quỹ `2` fallback của SKU đầu tiên ngay lập tức rồi `SAFE_ABORT` `3` lượt liền nhau. *(Lưu ý: `HTTP 503` tại `tr[15]` đẩy nhanh thêm 1 nhịp trong chuỗi 3 aborts đang xảy ra sẵn sau `2` fallbacks + `tr[14]`, không phải nguyên nhân gốc).*

---

## 6. Spot-check An toàn, Dữ kiện & Các Ca E04 (`E04-CASE-2B-01..04`)

- **Structural & Repo Safety:** `structural_hard_gates_status = PASS`, `p05_rejection_count = 0`, `invalid_candidate_playback_count = 0`, `duplicate_completed_chunk_replay_count = 0`, `0` secret leak, `0` metadata leak thô (`ev-`/`clm-`/`SKU-`), `overall_gate_status = NOT_EVALUATED`.
- **Spot-check các chủ đề nhạy cảm ở `W=10`:**
  - `topic-formal-honey-07` (`t[6]`, `t[18]`): Cả hai lượt đều giữ nguyên *"thìa khô sạch"* và *"không dùng cho trẻ dưới một tuổi"*.
  - `topic-formal-tea-07` (`t[30]`, `t[42]`): Giữ đủ cảnh báo nhiệt độ 100°C và caffeine / sát giờ ngủ ở cả 2 lượt.
  - `topic-formal-macadamia-07` (`t[54]`, `t[66]`): Cả hai lượt đều giữ đầy đủ *"không ăn gói hút ẩm"* và *"tránh dùng nếu [bị] dị ứng hạt cây"*.
  - **Cảnh báo OCOP & khẳng định tuyệt đối (`*-10`):** `topic-formal-honey-10` (`t[9]`, `t[21]`) lặp nguyên văn *"Sản phẩm đạt chứng nhận OCOP 4 sao và an toàn thực phẩm **tuyệt đối**."* (bỏ chữ *"mô phỏng"* và dùng từ tuyệt đối); `tea-10` (`t[33]`) dùng *"mô phỏng"* nhưng thêm *"tuyệt đối"*; `macadamia-10` (`t[69]`) bỏ *"mô phỏng"*. Những dòng này đạt `PASS` về cấu trúc runtime nhưng **bắt buộc** đưa qua kiểm toán factual/blind trước khi kết luận E01.

| Mã Ca | Tên Ca | Tín hiệu Quan sát được trong Track 2B Live |
|---|---|---|
| `E04-CASE-2B-01` | **Window-Boundary Blindness at `lag=12` (`W=10`)** | `36/36` lượt quay lại có `actual_lag = 12 > W=10` → `0` từ chối từ detector, `1` exact normalized text replay (`honey-10`), `32.39%` lexical rep, `windowed_ngram3` bật `0.0131 → 0.2455`. |
| `E04-CASE-2B-02` | **First-Cycle `REPEATED_FACTS` Deadlock (`W=20`)** | Khi `W=20 > lag=12`, toàn bộ `12` chủ đề Honey còn nằm trong lịch sử tại `tr[12..16]` → `11` `REPEATED_FACTS:SWITCH_TOPIC`, cạn `2` fallback ở `tr[12..13]` và `3` `SAFE_ABORT_NO_CANDIDATE` → `MAX_CONSECUTIVE_ABORTS` tại `28` calls (`0/36`). |
| `E04-CASE-2B-03` | **Duration-Gate Retry Tax (`W=10`)** | `11/11` retries ở `W=10` không do lặp mà do vượt ngưỡng `8.00s` (`21–27` từ / `8.08s–10.38s`), làm tiêu hao `39,346` `wasted_tokens`. |
| `E04-CASE-2B-04` | **OCOP Mock-Label & Absolute-Safety Drift (`*-10`)** | P05 không chặn được việc lược bỏ nhãn `"hồ sơ mô phỏng"` hoặc dùng cụm `"an toàn thực phẩm tuyệt đối"` ở `honey-10`, `tea-10`, `macadamia-10`. |

---

## 7. Gói Đánh giá Mù 7 Tệp (`human_eval/`) — Trạng thái `PENDING`

Thư mục [`human_eval/`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/formal_benchmark_v1/track2b_large_window_lag12_s42/human_eval/) đã xuất đủ `7` tệp với `0` vi phạm leak mù qua kiểm tra tự động:
- `blind_key_mapping.private.json` *(giữ riêng)*: `SAMPLE_001` / `METHOD_A` = `langgraph_w20` (`c0cbfff5`); `SAMPLE_002` / `METHOD_B` = `langgraph_w10` (`601e3e7a`).
- `blind_eval_sheet.csv` & `blind_eval_sheet.jsonl` (`2` mẫu, cột chấm để trống hoàn toàn).
- `factual_and_semantic_review_sheet.csv` (**`122` dòng** = `86` lượt phát [`72` `W=10` + `14` `W=20`] + `36` dòng thiếu [`12` `MISSING_SECOND_CHUNK` + `24` `MISSING_TOPIC` ở `W=20`]).
- `revisit_repetition_review_sheet.csv` (**`72` dòng** = `36` cặp quay lại cho mỗi mẫu).
- `REVIEWER_GUIDE_BLIND_QUALITY.md` & `REVIEWER_GUIDE_FACTUAL_AND_SEMANTIC_AUDIT.md`.

---

## 8. Tệp CSV Phân tích Đã Xuất & Kết quả Kiểm chứng (`track2b_large_window_lag12_s42/`)

- `actual_lag_analysis.csv` (`36` dòng revisit của `W=10`), `repetition_opportunity_analysis.csv` (`49` dòng opportunity/attempts), `detector_outcome_analysis.csv` (`16` dòng), `mock_vs_live_comparison.csv` (`4` dòng), `comparison.{json,csv,md}`.
- **Kiểm chứng kỹ thuật & độc lập:**
  - `pytest experiments/sales-intelligence/autonomous-storytelling/tests -q`: **`289 passed` (`0` failed, `0` skipped)**.
  - `pip check`: **`No broken requirements found`**.
  - Khóa SHA-256 trên bộ hiện vật Track 2B (`verified_skus`, `story_plans`, `batch_cfg`, `model_cfg`, `prompts/*.txt`): khớp 100%, `0` secret leak, `0` leak mù trên 6 tệp công khai của `human_eval/`.
  - `AGENTS.md`: `22,410 bytes` (`< 24,000`), không có YAML frontmatter; rà soát độc lập bởi `hydrogen-scout` (`flash`).
