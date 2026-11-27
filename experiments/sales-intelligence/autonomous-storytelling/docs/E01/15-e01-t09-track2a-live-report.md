# Báo cáo Thực thi & Phân tích Live Track 2A — Small Window Sensitivity (`P06-E01-T09`)

**Ngày lập báo cáo:** `2026-11-27`  
**Branch:** `research/p06-autonomous-storytelling`  
**Base Commit trước phiên:** `0d8a2bd` (`research(p06): complete batch 1B evaluation and lock E01 track 2 protocol`)  
**Module:** `experiments/sales-intelligence/autonomous-storytelling/`  
**Phân loại phiên:** **`Controlled Exploratory Benchmark` — Stress Track 2A (`W=5` vs `W=10`, `lag=6`)**  
**Trạng thái dừng:** **`AWAITING_TRACK2B_QUOTA`** *(Hoàn tất 100% Track 2A; `overall_gate_status = NOT_EVALUATED`; tạm dừng trước Track 2B để chờ chu kỳ reset quota RPD sau `15:00 VN`)*

---

## 1. Tóm tắt Điều hành (`Executive Summary`)

Theo phê duyệt kết hợp **`GO FOR BOTH TRACK 2A AND TRACK 2B — CONTROLLED EXPLORATORY BENCHMARK`**, sau khi xác minh quota khả dụng trước `15:00 VN` còn khoảng `~325–328/500 RPD` (đủ cho trần `240` của Track 2A nhưng không đủ trần `400` cho Track 2B), phiên này đã thực thi tuần tự trọn vẹn **Track 2A (`product_education_10m_ext`, `seed=42`, `min_chunks_per_topic=2`, `W=5` vs `W=10`)** bằng **`gemini-3.5-flash-lite` Free Tier (`0 USD`)**.

Các kết quả thực nghiệm cốt lõi của Track 2A:

1. **Ngân sách & Toàn vẹn Thực thi:** [`budget_ledger.json`](../runs/P06-E01/formal_benchmark_v1/track2a_small_window_lag6_s42/budget_ledger.json) ghi nhận **`71 / 240` requests** (`48` cho `W=5` + `23` cho `W=10`), **`0.00 USD`**, **`0` `HTTP 429`**, **`1` lỗi hạ tầng `HTTP 503`** (`W=10`, `call_index=19`, `turn_index=9`, `attempt=2`), **`0` rò rỉ secret/metadata**, `structural_hard_gates_status = PASS` trên cả 2 runs, `comparison_compatible = True`. Quỹ RPD trong ngày sau Track 2A còn khoảng `~254–257 < 400`, nên phiên dừng sạch tại **`AWAITING_TRACK2B_QUOTA`** theo đúng §5.4 và §23.
2. **Xác nhận Mạnh Mẽ Giả thuyết `H1` (`Small Window Contrast`) & Phát hiện Đánh đổi Cực đoan (`H3`/`H4`):**
   - **`LangGraph W=5` (`actual_lag = 6 > W=5` trên `18/18` revisits):** Kết thúc `EARLY_COMPLETION` với **`18/18` (`100%`)** topics đủ `>= 2` non-fallback ACKs (`12/12` mandatory). Tuy nhiên, vì lượt 1 ở `lag=6` đã **trượt khỏi cửa sổ `W=5` (`0/18` window hit)**, `RepetitionDetector` trả **`36/36` `NONE:ALLOW` (`0` rejections)** -> hệ quả là xuất hiện **`2` lượt lặp nguyên văn chuẩn hóa (`outside_window_exact_text_replay_count = 2`: `honey-pairing` [05]/[11] và `macadamia-harvest` [28]/[34])** và **`lexical_repetition_rate = 28.57%` (`10/35` cặp)** trên common full-session horizon!
   - **`LangGraph W=10` (`actual_lag ∈ {5..8} <= W=10` trên `14/14` candidate revisits):** Vì `W=10` **vẫn giữ lượt 1 trong bộ nhớ**, `RepetitionDetector` kích hoạt ngay trên `SKU-HONEY-01`: **`8` lượt `REPEATED_FACTS:SWITCH_TOPIC`** + **`6` lượt `LEXICAL_DUPLICATION:REWRITE`**. Khi chỉ có `1 allowed_claim_id / topic`, agent thử xoay vòng `honey-usage -> honey-safety -> honey-quality`, dùng hết **`2` câu `PREAPPROVED_FALLBACK` của `SKU-HONEY-01`** (`idx=6, 7`), rồi kẹt ở **`3` lượt `SAFE_ABORT_NO_CANDIDATE` liên tiếp (`idx=8, 9, 10`)** và dừng tại **`MAX_CONSECUTIVE_ABORTS`** chỉ với `8` turns phát (`6` proactive + `2` fallback), **`0/18` topics hoàn thành `>= 2` chunks**, **`0%` lexical repetition**.
3. **Phát hiện Kiến trúc Trọng yếu cho `E04` (`Turn-Scoped Excluded Topics Trap`):** Phân tích `graph_trace.jsonl` cho thấy `ctx.excluded_topic_ids` trong [`TurnExecutionContext`](../src/p06/agent/deps.py) chỉ tồn tại trong phạm vi **1 lượt (`per-turn`)**. Sau khi fallback hết cho `SKU-HONEY-01`, mỗi lượt tiếp theo (`idx=8, 9, 10`) đều bắt đầu lại ở `honey-usage` -> `SWITCH_TOPIC` sang `honey-safety` -> cạn rewrite -> abort tại cùng một cặp chủ đề trước khi từng chạm tới `SKU-TEA-02` hay `SKU-MACADAMIA-03`.

---

## 2. Phê duyệt Tech Lead, Preflight & Tái lập (`0d8a2bd`)

- **Phê duyệt:** `GO FOR BOTH TRACK 2A AND TRACK 2B — CONTROLLED EXPLORATORY BENCHMARK` (`4` formal runs, trần tổng `640` req: `240` cho Track 2A + `400` cho Track 2B, `0 USD` Free Tier, dữ liệu `SYNTHETIC`, chạy tuần tự).
- **Preflight trước Track 2A:**
  - Branch `research/p06-autonomous-storytelling`, commit `0d8a2bd`, working tree sạch, `0` merge conflict.
  - Regression suite: **`289 passed`**. Toàn bộ `13/13` locked SHA-256 hashes khớp `100%`.
  - Pilot v1/v2, Batch 1A (`human_eval/` & `ai_assisted_eval/`), Batch 1B (`human_eval/` & `ai_assisted_eval/`) còn nguyên vẹn; `0` tiến trình Python cạnh tranh quota.
- **Cấu hình Khóa Track 2A:** [`configs/experiments/p06_e01_formal_track2a_w5_w10.yaml`](../configs/experiments/p06_e01_formal_track2a_w5_w10.yaml) (`SHA-256: d52a17b1c832093490e5b0092921c56d2e09488e8d7335088156ae41a23e5ae7`, `dataset_profile=e01_ext_v1`, `product_education_10m_ext`, `seed=42`, `min_chunks_per_topic=2`, `max_chunk_duration_sec=8.0s`, `max_turns=80`, `max_requests_per_run=120`, `global_max_requests=240`, `model=gemini-3.5-flash-lite`, `temperature=0.3`, `top_p=0.9`, `max_tokens=1024`, `thinking_level=MINIMAL`).

---

## 3. Sổ cái Ngân sách & Tình trạng Quota (`Track 2A` vs `Track 2B`)

| Hạng mục Ngân sách / Quota | Giá trị Quan sát | Ghi chú |
|---|---:|---|
| `LangGraph W=5` (`...w5__20261126T231540Z__cba0dd8b`) | **`48 / 120`** req | `48` `MEASURED`, `0` `HTTP 503/429`, `0.00 USD` |
| `LangGraph W=10` (`...w10__20261126T232023Z__a2ecd346`) | **`23 / 120`** req | `22` `MEASURED` + `1` `HTTP 503` (`call_index=19`), `0` `HTTP 429`, `0.00 USD` |
| **Tổng Track 2A ([`budget_ledger.json`](../runs/P06-E01/formal_benchmark_v1/track2a_small_window_lag6_s42/budget_ledger.json))** | **`71 / 240`** req | Hoàn tất `COMPLETED`, dư `169` slot không chuyển qua Track 2B |
| Tổng đã dùng trong chu kỳ `500 RPD` hiện tại *(trước `15:00 VN`)* | `~243–246 / 500` | Google AI Studio hiển thị `172/500` (hoặc `175` theo ledgers trước) + `71` (Track 2A) |
| **Quota khả dụng còn lại cho Track 2B (`global cap = 400`)** | **`~254–257 < 400`** | **Không đủ `>= 400` -> Dừng tại `AWAITING_TRACK2B_QUOTA` tới sau `15:00 VN 27/11/2026`** |

---

## 4. Kết quả Thực nghiệm Track 2A (`Common Full-Session Evaluation Horizon`)

| Nhóm | Chỉ số | `LangGraph W=5` | `LangGraph W=10` |
|---|---|---:|---:|
| **Chung** | `termination_reason` | **`EARLY_COMPLETION`** | **`MAX_CONSECUTIVE_ABORTS`** |
| | Wall-clock (`total_measured_processing_ms`) | `283.60s` (`4m 44s`) | `141.54s` (`2m 22s`) |
| **Coverage (`§10`)** | `completed_topic_count` *(>=2 non-FB ACKs)* | **`18 / 18` (`100%`)** | **`0 / 18` (`0.00%`)** |
| | `partially_covered_topic_ids` *(1 chunk)* / `missing` *(0 chunk)* | `0` / `0` | **`6` *(Honey)* / `12` *(Tea + Macadamia)*** |
| | `mandatory_topic_coverage` (`12`) | **`100%` (`12/12`)** | **`0.00%` (`0/12`)** |
| | `declared_verified_claim_coverage` (`14`) | **`100%` (`14/14`)** | `28.57%` (`4/14`) |
| | `simulated_played_duration_sec` / `600s` | `250.000s` (`41.67%`) | `55.385s` (`9.23%`) |
| **Repetition (`§9`)** | `exact_chunk_replay_count` (`Hard Gate == 0`) | `0` | `0` |
| | `exact_normalized_text_replay_count` *(toàn phiên)* | **`2`** | **`0`** |
| | `outside_window_exact_text_replay_count` | **`2`** | `0` |
| | `lexical_repetition_rate` *(toàn phiên)* | **`28.57%` (`10/35`)** | **`0.00%` (`0/7`)** |
| | `word_jaccard` `mean / p95 / max` | `0.4204 / 0.9300 / 1.0000` | `0.2028 / 0.4458 / 0.5417` |
| | `ngram3_jaccard` `mean / p95 / max` | `0.2031 / 0.9222 / 1.0000` | `0.0468 / 0.2168 / 0.2963` |
| | `windowed_ngram3_mean` (`w5 / w10 / w20`) | `0.0028 / 0.2031 / 0.2031` | `0.0468 / 0.0468 / 0.0468` |
| | `claim_overlap_rate` | `62.86%` (`22/35`) | `40.00%` (`2/5`) |
| | `distinct_1 / distinct_2 / distinct_3` | `0.363 / 0.646 / 0.736` | **`0.674 / 0.871 / 0.931`** |
| **Safety (`§11`)** | `structural_hard_gates_status` / `p05_rejection` | **`PASS`** / `0` | **`PASS`** / `0` |
| | `retry_budget_violations` / `metadata_leaks` | `0` / `0` | `0` / `0` |
| | `overall_gate_status` | **`NOT_EVALUATED`** | **`NOT_EVALUATED`** |
| **Reliability (`§12`)** | `total_requests` / `successful_candidate_count` | `48` / `36` | `23` / `6` |
| | `HTTP 503` / `HTTP 429` | `0` / `0` | `1` *(c19, turn 9 att 2)* / `0` |
| | `wasted_calls` tổng (`%`) / thuần logic (`% non-503`) | `12/48` (`25.00%`) / `25.00%` | `17/23` (`73.91%`) / `69.57%` (`72.73%`) |
| | `rewrite_rate` (`sum retries`) | `33.33%` (`12/36`, `sum=12`) | `63.64%` (`7/11`, `sum=12`) |
| | `fallback_rate` (`count`) | `0.00%` (`0`) | `18.18%` (`2` turns) |
| | `safe_abort_rate` (`count`, đã lọc boundary sạch) | `0.00%` (`0`) | **`27.27%` (`3` turns)** |
| **Tokens / Perf** | Token source & measured calls | **`MEASURED` (`48/48`)** | `UNAVAILABLE` (`22/23`, thiếu c19) |
| | `input / output / total / wasted` *(measured)* | `144,321 / 6,084 / 150,405 / 38,562` | `67,354 / 2,758 / 70,112 / 52,786` |
| | `thinking_tokens` | `0` | `None` *(thiếu c19)* |
| | `provider_latency p50 / p95` *(gồm pacing 6s)* | `5,927.4 / 6,573.2 ms` | `6,016.8 / 8,276.2 ms` |
| | `invocation_latency p50 / p95` / `c0_ms` | `6,239.4 / 12,510.3 ms` / `4,052.6` | `11,974.9 / 19,835.1 ms` / `5,422.6` |

> **Ý nghĩa của `Common Evaluation Horizon` (`§9.1`):** Ở `W=5`, nếu chỉ đo trong cửa sổ `w5`, `windowed_ngram3_mean_w5 = 0.0028` gần như bằng `0` và tạo ảo giác "không lặp". Chỉ khi đánh giá cùng trên horizon toàn phiên (`>= 10`), ta mới thấy `max_prior_ngram3_jaccard_mean = 0.2031`, `lexical_repetition_rate = 28.57%` và `2` lượt trùng nguyên văn (`outside_window_exact_text_replay_count = 2`).

---

## 5. Phân tích `Actual Lag`, Revisit & Detector theo Tầng (`§8` & `§9`)

Chi tiết đầy đủ đã được xuất ra [`actual_lag_analysis.csv`](../runs/P06-E01/formal_benchmark_v1/track2a_small_window_lag6_s42/actual_lag_analysis.csv), [`repetition_opportunity_analysis.csv`](../runs/P06-E01/formal_benchmark_v1/track2a_small_window_lag6_s42/repetition_opportunity_analysis.csv) và [`detector_outcome_analysis.csv`](../runs/P06-E01/formal_benchmark_v1/track2a_small_window_lag6_s42/detector_outcome_analysis.csv).

### 5.1. Planned vs Attempted / Played / Rejected / Aborted / Missing Revisits (`§8.1`)

| Chỉ số đơn vị Topic / Lượt | `W=5` | `W=10` |
|---|---:|---:|
| Planned revisits (`min_chunks_per_topic=2`) | `18` | `18` |
| Unique topics attempted cho chunk #2 | **`18`** (`100%`) | **`3`** (`honey-usage`, `honey-safety`, `honey-quality`) |
| Content turns có thử revisit (`attempted_turns`) | `18` | `5` (`turn_index = 6, 7, 8, 9, 10`) |
| Successfully played proactive revisits (`played_revisits`) | **`18 / 18`** | **`0 / 18`** |
| Fallback-replaced revisit turns | `0` | `2` (`turn_index = 6, 7`) |
| Safe-aborted revisit turns | `0` | `3` (`turn_index = 8, 9, 10`) |
| Unattempted / Missing revisits (tới hết phiên) | `0` | **`15`** chưa từng thử (`3` Honey còn lại + `12` Tea/Macadamia) |
| **Candidate-level revisit attempts kiểm tra lặp** | **`18` attempts** | **`14` attempts** *(không cộng thành planned opportunities)* |
| Phân bố **`actual_lag = L - j`** *(trên candidate/played)* | `{6: 18}` | `{5: 3, 6: 2, 7: 6, 8: 3}` *(mọi attempt đều `<= 10`)* |
| **Window Hit (`actual_lag <= W`)** | **`0 / 18` (`0%`)** | **`14 / 14` (`100%`)** *(nhưng `0/18` played revisit completion)* |

### 5.2. Phân bố Kết quả `RepetitionDetector` trên Toàn bộ Checks (`detector_outcome_analysis.csv`)

| Run | `NONE (ALLOW)` | `LEGIT_CONT (ALLOW)` | `EXACT_REPLAY` | `LEXICAL_DUP (REWRITE)` | `REPEATED_FACTS (SWITCH_TOPIC)` |
|---|---:|---:|---:|---:|---:|
| `W=5` (`36` checks) | **`36`** | `0` | `0` | `0` | `0` |
| `W=10` (`20` checks = `6` chunk-#1 + `14` revisit attempts) | `6` | `0` | `0` | **`6`** | **`8`** |

- **Kiểm chứng Giả thuyết `H1–H5` & Đối chiếu `Fixed-History` (`§9.3`):**
  - **`H1` ĐƯỢC XÁC NHẬN:** Khi `actual_lag = 6` (`W=5` ngoài cửa sổ vs `W=10` trong cửa sổ), `W=5` cho qua `100%` và sinh `2` exact text replays + `28.57%` lexical repetition; `W=10` phát hiện `14/14` attempts lặp (`8` `REPEATED_FACTS` + `6` `LEXICAL_DUPLICATION`).
  - **`H3` & `H4` ĐƯỢC XÁC NHẬN CỰC ĐOAN:** Do mỗi topic chỉ có `1 allowed_claim_id` và Gemini luôn điền đúng `claim_id` đó (khác Mock đặt `curr_claims=[]` ở `attempt=0`), `W=10` chặn ngay từ `attempt=0` bằng `REPEATED_FACTS:SWITCH_TOPIC`. Kết hợp `fallback` cạn sau `2` lượt/SKU và `excluded_topic_ids` reset theo lượt, `W=10` dừng ở `MAX_CONSECUTIVE_ABORTS` với `73.91%` wasted calls (`0/18` topics xong).
  - **Đối chiếu Fixed-History (`test_fixed_history_detector_memory_contrast_lag6_lag8_lag12`):** Fixed-history test cô lập cơ chế cửa sổ ở trạng thái tĩnh; Live Track 2A chứng minh hệ quả **phân kỳ quỹ đạo hệ thống (`system divergence`)**: chỉ cần một topic bị `REPEATED_FACTS:SWITCH_TOPIC` + `FALLBACK`, `actual_lag` thay đổi và vòng lặp abort kích hoạt sớm trước khi đi sang SKU khác.

---

## 6. Đối chiếu Mock vs Live (`mock_vs_live_comparison.csv`, Không Gộp Tầng)

| `W` | Tier / Model | Calls | `HTTP 503` | `REPEATED_FACTS` | `LEXICAL_DUP` | `EXACT_REPLAY` | Rewrite (`sum`) | Fallbacks | Safe Aborts | Completed (`>=2`) | Termination |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `5` | `unit_test_mock` | `42` | `0` | `0` | `2` | `4` | `6` | `0` | `0` | `18/18` (`1.0`) | `EARLY_COMPLETION` |
| `5` | **`gemini_live` (`3.5-flash-lite`)** | **`48`** | `0` | `0` | `0` | `0` | **`12`** *(duration)* | `0` | `0` | `18/18` (`1.0`) | `EARLY_COMPLETION` |
| `10` | `unit_test_mock` | `52` | `0` | `10` | `2` | `4` | `12` | `6` | `0` | `18/18` (`1.0`) | `EARLY_COMPLETION` |
| `10` | **`gemini_live` (`3.5-flash-lite`)** | **`23`** | `1` | **`8`** | **`6`** | `0` | **`12`** | `2` | **`3`** | **`0/18` (`0.0`)** | **`MAX_CONSECUTIVE_ABORTS`** |

**Trả lời 9 câu hỏi phân tích Mock vs Live (`§14`):**
1. Live `W=5` giữ đúng `actual_lag = 6` trên `18/18` lượt như Mock; Live `W=10` giữ `lag ∈ {5..8} <= 10` trước khi dừng.
2. **Điểm phân kỳ cốt lõi (Câu 2 & 3):** Mock `idx=1` đặt `covered_claim_ids = []` giúp `W=10` vượt qua ở `attempt=0` (chỉ gặp `REPEATED_FACTS` nếu bị rewrite); ngược lại Gemini thật điền đúng `covered_claim_ids = [claim_id duy nhất]`, làm **`REPEATED_FACTS` kích hoạt ngay `attempt=0`** ở Live `W=10`.
3. `W=5` Live tăng rewrite so với Mock (`12` vs `6` calls) nhưng toàn bộ `12/12` đều do **`OVER_MAX_DURATION_SEC` (`21–24` từ)**, không phải repetition.
4. `W=10` Live không tìm được `LEGITIMATE_CONTINUATION` nào (`0`) do topic chỉ có `1 claim_id`.
5. `PREAPPROVED_FALLBACK` (`idx=6, 7`) dịch chuyển `lag` từ `6` -> `7` -> `8` nhưng vẫn nằm trong `W=10`.
6. Ở `W=5`, `lexical_repetition_rate` là `28.57%` nhưng bằng mắt thường còn nhiều lượt khác dù Jaccard `< 0.65` vẫn lặp ý sát nhau (sẽ kiểm bằng `revisit_repetition_review_sheet.csv`).
7. `W` lớn giảm lexical/exact replay về `0`, nhưng trong điều kiện thiếu claim mới lại làm giảm completion (`18/18 -> 0/18`) và tăng waste (`25.00% -> 73.91%`).

---

## 7. An toàn, Câu chữ & Hồ sơ E04 (`E04 Candidate Failure Cases`)

### 7.1. Quan sát An toàn & Factual Sơ bộ trên Transcript *(Chờ Human/Semantic Audit)*
- `structural_hard_gates_status = PASS` trên cả 2 runs (`0` leak mã `ev-/SKU-`, `0` chunk replay, `0` P05 rejection).
- **Các điểm cần reviewer kiểm tra kỹ trong Bước 2:**
  - `W=5` `[00]` & `[06]`, `W=10` `[00]`: `honey-usage` vẫn nói `"một đến hai thìa"` / `"1-2 thìa"` (thiếu `"cà phê"` — lặp lại Finding F của StoryPlan).
  - `W=5` `[25]` (`macadamia-safety` sau rewrite `21w -> 18w`): *"Xoay nhẹ thanh tách theo rãnh nứt, tránh ăn gói hút ẩm và người dị ứng hạt cây."* — nén câu bỏ động từ *"tránh dùng cho"* trước *"người dị ứng hạt cây"*.
  - `W=5` `[06]` (`honey-usage`) trích thêm `ev-e01-ext-honey-pairing` (`"chanh tươi"` hợp lệ) nhưng `W=5` `[15]` (`tea-packaging`) nói *"giữ trà khô suốt 18 tháng"* và `W=5` `[19]` (`tea-safety`) trích thêm `ev-e01-tea-quality`.
  - Dataset `product_education_10m_ext` không có topic OCOP nên `0` ca thiếu `"mô phỏng"`.

### 7.2. Trích xuất Case Thất bại Bàn giao `P06-E04` *(Không triển khai E04)*

| Case ID | Trace & Topic | Diễn biến (`Initial -> Reject -> Rewrite/Outcome`) | Nguyên nhân Sơ bộ & Hướng nghiên cứu `E04` |
|---|---|---|---|
| **`E04-CASE-2A-01`** | `W=10` `idx=6..10` (`honey-usage -> honey-safety`) | `att=0` (`honey-usage`, `lag=6..8`) bị **`REPEATED_FACTS:SWITCH_TOPIC`** (`fo=1.0`), `bounded_rewrite` chuyển sang `honey-safety`, bị **`LEXICAL_DUPLICATION:REWRITE`** (`wj=0.778–0.933`) rồi dừng `FALLBACK` (`idx=6,7`) và `SAFE_ABORT` (`idx=8,9,10` -> `MAX_CONSECUTIVE_ABORTS`). | **`ctx.excluded_topic_ids` chỉ sống theo từng lượt**, làm vòng lặp liên tiếp đụng cùng cặp chủ đề của SKU đầu tiên và khóa cứng tiến trình sang `SKU-TEA-02` / `SKU-MACADAMIA-03`. |
| **`E04-CASE-2A-02`** | `W=10` `idx=9 att=2` (`honey-safety`) | Đang ở giữa vòng rewrite `att=2` sau `REPEATED_FACTS -> LEXICAL_DUPLICATION` thì gặp **`HTTP 503 UNAVAILABLE`** (`c19`), kích hoạt ngay `NON_RETRYABLE_FAILURE` -> `SAFE_ABORT_NO_CANDIDATE` (#2/3). | Thiếu chính sách phân biệt lỗi hạ tầng `503` thoáng qua với lỗi logic nội dung trong bộ đếm `consecutive_aborts`. |
| **`E04-CASE-2A-03`** | `W=5` `idx=27` (`macadamia-safety`) | `att=0` (`21w`): *"Bạn xoay nhẹ thanh tách theo rãnh nứt, không ăn gói hút ẩm và tránh dùng nếu dị ứng hạt cây."* -> `att=1` (`18w`): *"...tránh ăn gói hút ẩm và người dị ứng hạt cây."* | `bounded_rewrite` cắt 3 từ đã bỏ cụm *"tránh dùng nếu"*, làm câu tối nghĩa ở cảnh báo dị ứng (tương đồng `E04-CASE-1B-01`). |
| **`E04-CASE-2A-04`** | `W=5` `idx=5` vs `idx=11` & `idx=28` vs `idx=34` | Ở `lag=6 > W=5`, `W=5` sinh **hai cặp câu giống hệt từng chữ** ở `honey-pairing` và `macadamia-harvest`, `Allow` hoàn toàn dù semantic/lexical trùng `100%`. | Cho thấy `W=5` không bao phủ đủ ngay cả chu kỳ `6` chủ đề trong cùng 1 SKU nếu `min_chunks_per_topic=2`. |

---

## 8. Bộ Phiếu Đánh giá Con người & Kế hoạch Hoàn tất `E01`

### 8.1. Hồ sơ `human_eval/` Track 2A (`7` Tệp Sạch, `0` Rò rỉ)
Đã xuất và kiểm định tự động tại [`runs/P06-E01/formal_benchmark_v1/track2a_small_window_lag6_s42/human_eval/`](../runs/P06-E01/formal_benchmark_v1/track2a_small_window_lag6_s42/human_eval/blind_eval_sheet.csv):
1. `blind_eval_sheet.csv` & `blind_eval_sheet.jsonl` (`2` samples: `SAMPLE_001` = `METHOD_A` [`W=10`, `8` turns], `SAMPLE_002` = `METHOD_B` [`W=5`, `36` turns]).
2. `factual_and_semantic_review_sheet.csv` (`62` dòng = `8 + 6 MISSING_SECOND_CHUNK + 12 MISSING_TOPIC` cho `SAMPLE_001` và `36` played turns cho `SAMPLE_002`, toàn bộ cột reviewer trống).
3. `revisit_repetition_review_sheet.csv` (`36` dòng = `18` cặp revisit cho mỗi sample, ẩn hoàn toàn `W` và detector actions).
4. `blind_key_mapping.private.json` *(tệp giải mã tách riêng)*.
5. `REVIEWER_GUIDE_BLIND_QUALITY.md` & `REVIEWER_GUIDE_FACTUAL_AND_SEMANTIC_AUDIT.md`.

### 8.2. Tình trạng Bàn giao Track 2B & Lộ trình Đóng `P06-E01` (`Plan Only`)
- **Bước kế tiếp ngay sau `15:00 VN 27/11/2026`:** Khi quota RPD reset và xác nhận đủ `>= 400` requests khả dụng, chạy **Track 2B** theo đúng phê duyệt hiện có bằng lệnh đã khóa tại [`docs/14-...`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/docs/14-e01-t09-track2-readiness-and-protocol.md) Mục 12, rồi xuất `docs/16-e01-t09-track2b-live-report.md` và `docs/17-e01-t09-combined-track2-research-analysis.md`.
- **Sau Track 2B + Human/AI-assisted Evaluation:** Tổng hợp [`notebooks/06_e01_results_analysis.ipynb`](../notebooks/), `reports/tables/`, `reports/figures/` và `reports/p06_e01_research_report.md` để trả lời đầy đủ `RQ1–RQ5` bằng kết luận `GO / CHANGE / NO-GO / INCONCLUSIVE` (hiện tại `P06-E01` **CHƯA** được đánh dấu `VALIDATED` hoặc `COMPLETED`).

---

## 9. Kiểm chứng Hồi quy & Review Độc lập

- **`pytest experiments/sales-intelligence/autonomous-storytelling/tests -q`:** **`289 passed, 0 failed, 0 skipped`** (`45.24s`).
- **`pip check`:** **`No broken requirements found`**.
- **Kích thước `AGENTS.md`:** **`22,228` bytes** (`< 24,000` bytes), không YAML frontmatter.
- **Locked SHA-256 (`13/13` tài nguyên khóa):** **`100%` khớp**.
- **Phạm vi thư mục & Git:** `runs/P06-E01/formal_benchmark_v1/` chỉ gồm `track1_product_edu_s42`, `track1_brand_storytelling_s42`, và `track2a_small_window_lag6_s42` (`0` thư mục live Track 2B). `git status --short` xác nhận `0` thay đổi ngoài `experiments/sales-intelligence/autonomous-storytelling/`, không sửa `src/p06/`, `prompts/`, `data/`, `configs/`, Pilot v1/v2 hay Batch 1A/1B.
- **Đánh giá độc lập read-only (`hydrogen-scout`, `8d7fd30d`):** **PASS** toàn bộ artifact completeness (`9` tệp top-level + `2 × 10` tệp run + `human_eval/`), **PASS** blind integrity (`7` tệp `human_eval/`, `0` rò rỉ trên `6` tệp công khai, toàn bộ cột người chấm trống, `0` secrets), **PASS** bảo toàn tài nguyên trước đó; `1` sai lệch nhỏ ở Mục 5.1 (`{5: 3, 6: 3, 7: 5, 8: 3}` vs `{5: 3, 6: 2, 7: 6, 8: 3}` trong `repetition_opportunity_analysis.csv`) đã được đính chính chính xác.

---

**Trạng thái dừng:** **`AWAITING_TRACK2B_QUOTA`**
