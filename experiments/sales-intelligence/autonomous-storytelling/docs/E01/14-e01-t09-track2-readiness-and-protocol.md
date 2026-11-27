# Báo cáo Sẵn sàng & Giao thức Track 2 — History Window Sensitivity (`P06-E01-T09`)

**Ngày lập báo cáo:** `2026-11-27`  
**Branch:** `research/p06-autonomous-storytelling`  
**Base Commit trước phiên:** `8008f9f` (`research(p06): complete E01 formal benchmark batch 1A`)  
**Module:** `experiments/sales-intelligence/autonomous-storytelling/`  
**Phân loại nhiệm vụ:** **Batch 1B AI-Assisted Eval Import & Offline Track 2 Validation (`0` Gemini API calls)**  
**Trạng thái dừng:** **`AWAITING_FINAL_TRACK2_EXECUTION_APPROVAL`** *(Chưa chạy Track 2 thật trên Gemini API; `overall_gate_status = NOT_EVALUATED`; chưa đóng `P06-E01` là `VALIDATED`)*

---

## 1. Tổng hợp Đánh giá AI-Assisted của Batch 1B (Đã Import & Đối soát)

Hai tệp đánh giá do ChatGPT thực hiện trên toàn bộ `2` transcripts và `37` dòng kiểm toán của **Batch 1B (`brand_storytelling_10m_ext`, `seed=42`)** đã được lưu nguyên vẹn byte-for-byte tại [`runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/ai_assisted_eval/`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/ai_assisted_eval/README.md):

- [`batch1b_ai_assisted_quality.csv`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/ai_assisted_eval/batch1b_ai_assisted_quality.csv) (`SHA-256: e761827cb3de7d9110d580e6ae72cab73518e894b42939960edd280466e95868`, `2` dòng).
- [`batch1b_ai_assisted_factual_semantic.csv`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/ai_assisted_eval/batch1b_ai_assisted_factual_semantic.csv) (`SHA-256: eccd63110a45eee8f9fa309eba9ed9ddd9af839e04f00117fcc911809052260b`, `37` dòng = `36` played turns + `1` `MISSING_TOPIC` ở `Script-first`).
- **Provenance bắt buộc:** **`AI-assisted non-blind evaluation — ChatGPT — Rubric v0.1`** (`evaluator_id = chatgpt_ai_assisted_nonblind_v0.1`).

> [!WARNING]
> Bộ đánh giá này **KHÔNG phải Human Blind Evaluation** và **KHÔNG phải `GoldFactualLabel`**. Toàn bộ `6` tệp chấm mù trong [`track1_brand_storytelling_s42/human_eval/`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/human_eval/blind_eval_sheet.csv) được giữ nguyên `100%` trống; Human Calibration, Human Blind Evaluation và Gold Factual Assessment vẫn ở trạng thái **`PENDING`**.

### 1.1. Điểm Chất lượng Sơ bộ (Rubric `v0.1`, Thang `1–5`)

| Tiêu chí | `Script-first` (`SAMPLE_002 / METHOD_B`) | `LangGraph W=5` (`SAMPLE_001 / METHOD_A`) |
|---|---:|---:|
| `narrative_coherence` | 2 | 3 |
| `naturalness` | 3 | 3 |
| `persuasiveness` | 3 | 3 |
| `context_relevance` | 3 | 4 |
| `transition_quality` | 2 | 2 |
| `repetition_quality` | 2 | 4 |
| **Mean Score** | **2.50** | **3.17** |
| `hard_constraint_violation` *(theo AI audit)* | `true` | `true` |

### 1.2. Độ phủ Ngữ nghĩa (`Semantic Alignment`)

| Nhóm Mẫu số | Phương pháp | `FULL` | `PARTIAL` | `MISS` |
|---|---|---:|---:|---:|
| **Mandatory topics** *(mẫu số `= 12`)* | `Script-first` (`SAMPLE_002`) | `5` | `4` | `3` |
| | `LangGraph W=5` (`SAMPLE_001`) | `7` | `5` | `0` |
| **All planned topics** *(mẫu số `= 18`)* | `Script-first` (`SAMPLE_002`) | `7` | `5` | `6` |
| | `LangGraph W=5` (`SAMPLE_001`) | `12` | `6` | `0` |

### 1.3. Factual Correctness & Evidence Support (`36` Played Turns, `1` `MISSING_TOPIC` Tách riêng)

| Phương pháp | Played Turns | Factual `PASS / FAIL / UNSURE` | Evidence `PASS / FAIL` | Metadata Leak |
|---|---:|---|---|---:|
| `Script-first` (`SAMPLE_002`) | `17` | `16 / 1 / 0` | `13 / 4` | `0` |
| `LangGraph W=5` (`SAMPLE_001`) | `19` | `15 / 3 / 1` | `14 / 5` | `0` |
| **Tổng cộng (`Played Turns`)** | **`36`** | **`31 / 4 / 1`** | **`27 / 9`** | **`0`** |

*(Ghi chú: Dòng `MISSING_TOPIC` trên `topic-ext-brand-honey-pairing` của `SAMPLE_002` được tính là `MISS` ở bảng Semantic Alignment và không đưa vào mẫu số factual/evidence của `36` played turns. Toàn bộ số liệu khớp 100% với hai tệp CSV gốc.)*

---

## 2. Phát hiện Natural Track (`Findings A–H`) & Đề xuất Đóng Phạm vi Natural Track

### 2.1. Tám Phát hiện Chính từ Batch 1B (`Findings A–H`)

- **Finding A — Cross-scenario Architecture Evidence:** `LangGraph W=5` đạt **`100%`** `playback-confirmed` `mandatory` và `planned` coverage trên cả `Product Education` (`1A`) lẫn `Brand Storytelling` (`1B`), trong khi `Script-first` lần lượt chỉ đạt `58.33%` và `75.00%` mandatory coverage. Đây là **bằng chứng sơ bộ** ủng hộ kiến trúc `Structured Story Planner + Dynamic Verified Generation + Bounded Rewrite`; **không** tuyên bố ý nghĩa thống kê (`statistical significance`) hay ưu thế nhân quả tuyệt đối (`causal superiority`).
- **Finding B — Semantic Coverage & Topic Granularity:** Tỷ lệ `Semantic FULL` mandatory của `LangGraph W=5` tăng từ **`25.00%`** (`3/12` ở `1A`) lên **`58.33%`** (`7/12` ở `1B`), còn `planned FULL` tăng từ `38.89%` (`7/18`) lên `66.67%` (`12/18`). Giả thuyết: các `talking_points` của `Brand Storytelling` cô đọng hơn và vừa khung `12–18` từ tốt hơn `Product Education`; **không** khẳng định quan hệ nhân quả do khác kịch bản.
- **Finding C — OCOP Scope Preservation:** Có **`3` trường hợp thiếu phạm vi synthetic/mô phỏng**:
  1. `Script-first` `turn_index=3` (`topic-ext-brand-honey-ocop`): bỏ mất `"mô phỏng"`.
  2. `LangGraph W=5` `turn_index=3` (`topic-ext-brand-honey-ocop`): bỏ mất `"mô phỏng"`.
  3. `LangGraph W=5` `turn_index=16` (`topic-ext-brand-macadamia-ocop`): chỉ nói `"đạt hồ sơ OCOP 4 sao"`, cụm `"hồ sơ OCOP 4 sao"` **không đủ xác lập bối cảnh mô phỏng**.  
  Cả `3` lượt đều được ghi nhận **`Factual FAIL`** theo AI-assisted reviewer.
- **Finding D — Safety-preserving Rewrite:** `LangGraph W=5` `turn_index=18` (`topic-ext-brand-macadamia-pairing`, `E04-CASE-1B-01`) khi rút gọn đã đổi `", lưu ý tránh dùng..."` thành `"hoặc tránh dùng cho người dị ứng hạt nhé."`, biến cảnh báo dị ứng thành một lựa chọn ngang hàng. Giữ `E04-CASE-1B-01` làm **case study bắt buộc cho `P06-E04`**.
- **Finding E — Evidence Attribution Correction:** Chi tiết `"nắp vặn kín khí"` của mắc ca thực tế có bằng chứng hợp lệ tại **`ev-e01-macadamia-shipping`**, không coi là sai sự thật hoàn toàn. Do đó, `W=5` `turn_index=17` được chấm **`Semantic FULL`, `Factual PASS`, `Evidence FAIL`** vì câu thoại chỉ trích dẫn `ev-e01-ext-macadamia-packaging` mà thiếu `ev-e01-macadamia-shipping` (cho `"kín khí"`) và thiếu `ev-e01-macadamia-quality` (cho `"hạn 12 tháng"`).
- **Finding F — StoryPlan Input Quality:** `topic-ext-brand-honey-pairing` trong `StoryPlan` chỉ ghi `"1-2 thìa"`, trong khi approved usage evidence (`ev-e01-honey-usage`) xác định `"1-2 thìa cà phê"`. Đây là lỗ hổng độ đầy đủ của **StoryPlan đầu vào**, không chỉ lỗi của tầng generation.
- **Finding G — Duration Estimator Limitation:** Việc viết lại các số bằng chữ (`"năm gram"`, `"một trăm năm mươi mi li lít"`) thành ký hiệu số (`"5g"`, `"150ml"`) làm giảm số từ phân tách theo khoảng trắng (`word_count`), nhưng **chưa chắc làm giảm tương ứng thời lượng đọc TTS thực tế**. Ghi nhận giới hạn này cho pha tích hợp `P02`; **không** sửa duration estimator giữa benchmark.
- **Finding H — Commercial Policy Not Revalidated:** `Brand Storytelling` không có topic đổi trả chủ động; vì vậy **không** tuyên bố các lỗi lược bỏ điều kiện đổi trả của Pilot v2 đã được xác minh là khắc phục.

### 2.2. Đề xuất Đóng Natural Storytelling Benchmark theo Phạm vi Rút gọn

| Hạng mục Natural Track | Trạng thái | Ghi chú |
|---|---|---|
| Batch 1A (`product_education_10m_ext`, `s42`, 4 configs) | `COMPLETED` | `94/120` req (`0 USD`) + AI-assisted eval `77` dòng |
| Batch 1B (`brand_storytelling_10m_ext`, `s42`, `SF + W=5`) | `COMPLETED` | `41/60` req (`0 USD`) + AI-assisted eval `37` dòng |
| `Product Education seed=43`, thêm runs `Brand`, `Extended 30m` | `DEFERRED` | Đề xuất hoãn để dồn ngân sách & trọng tâm cho Track 2 |
| `Pilot v3` | `NOT REQUIRED` | Không mở lại vòng pilot |
| Human Calibration, Human Blind Eval & `GoldFactualLabel` | **`PENDING`** | Vẫn chờ người chấm độc lập; **không** đánh dấu `E01` là `VALIDATED` |

---

## 3. Thiết kế Rút gọn Track 2 — History Window Sensitivity (`PLAN ONLY`, Chưa Gọi API)

Thay thế đề xuất Track 2 cũ bằng **hai phép đối chứng ghép cặp trực tiếp (`Reduced Paired-Comparison Design`)**, loại bỏ `Script-first` khỏi stress track vì Natural Track đã đối chứng `Script-first` vs `LangGraph` trên 2 kịch bản, giúp tập trung toàn bộ ngân sách cho biến cửa sổ bộ nhớ `W ∈ {5, 10, 20}` ở `min_chunks_per_topic = 2`:

| Tham số | **Track 2A — Small Window Sensitivity** | **Track 2B — Large Window Sensitivity** |
|---|---|---|
| Mục tiêu đối chứng | **`W=5` vs `W=10`** (`lag < W=10` nhưng `> W=5`) | **`W=10` vs `W=20`** (`lag < W=20` nhưng `> W=10`) |
| Tệp cấu hình khóa | [`p06_e01_formal_track2a_w5_w10.yaml`](../configs/experiments/p06_e01_formal_track2a_w5_w10.yaml) | [`p06_e01_formal_track2b_w10_w20.yaml`](../configs/experiments/p06_e01_formal_track2b_w10_w20.yaml) |
| `dataset_profile` / `scenario` | `e01_ext_v1` / `product_education_10m_ext` | `e01_formal_v1` / `window_stress_12lag_3sku` |
| `planned_topics` / `required_chunks (m=2)` | `18` topics (`3` SKU × `6` topics) -> **`36` base chunks** | `36` topics (`3` SKU × `12` topics) -> **`72` base chunks** |
| `planned_lag` / `planned_revisits` | `lag = 6` (`6 > W=5`, `6 <= W=10`) / `18` revisits | `lag = 12` (`12 > W=10`, `12 <= W=20`) / `36` revisits |
| `seed` / `min_chunks_per_topic` / `max_chunk_duration_sec` | `42` / `2` / `8.0s` | `42` / `2` / `8.0s` |
| `max_turns` *(công bằng giữa các W)* | **`80`** | **`120`** |
| `max_requests_per_run` / `global_max_requests` | **`120`** / **`240`** *(hoặc điều chỉnh sau mục 8)* | **`200`** / **`400`** |

- **Lý do giữ `product_education_10m_ext` (`lag=6`) thay vì `window_sensitivity_stress_24t` (`lag=8`):** Kiểm chứng ngoại tuyến ở Mục 4 chứng minh `product_education_10m_ext` tạo đúng **`18/18` (`100%`) cơ hội lặp ở `lag=6` (khi `0` fallback) và `lag ∈ {6,7,8}` (khi có fallback)** — tức `0/18` lọt vào `W=5` và `18/18` lọt trọn vào `W=10` — trong khi tiết kiệm ~`25%–32%` requests so với `window_sensitivity_stress_24t` (`42/52` Mock calls vs `58/77`).
- **Kỷ luật suy luận:** Đây là **reduced paired-comparison design**, không phải full factorial `2 × 3` trên cùng một kịch bản; **không** tuyên bố giá trị `W` tối ưu toàn cục qua so sánh chéo giữa Track 2A và Track 2B.

---

## 4. Kiểm chứng Ngoại tuyến về `Actual Lag` & Định nghĩa Biên Cửa sổ (`5A`)

### 4.1. Định nghĩa Toán học Không Sai lệch (`Off-by-one Free`)

Trong [`SimulatedPlaybackHarness._apply_completed_event`](../src/p06/simulation/playback_harness.py#L815-L833), **mọi lượt nhận `PlaybackCompleted` ACK** (gồm cả `PROACTIVE_STORY` lẫn `PREAPPROVED_FALLBACK`) đều được nạp vào `ShortTermPlayedHistory._all_turns`. Khi đồ thị dựng `AgentState` ở lượt hiện tại, giả sử tổng số lượt đã phát trước đó là `L = len(_all_turns)`, còn lượt `PROACTIVE_STORY` gần nhất của cùng `topic_id` nằm tại chỉ số `j` (`0 <= j < L`):

$$\text{actual\_lag} = L - j$$

Hàm [`ShortTermPlayedHistory.recent_turns()`](../src/p06/memory/played_history.py#L225-L227) cắt lát `self._all_turns[-W:]`, tức bao phủ đúng `W` chỉ số `[max(0, L - W), ..., L - 1]`. Do `j >= L - W ⇔ L - j <= W`, điều kiện lọt cửa sổ nhớ là chính xác tuyệt đối:

- **`IN WINDOW`:** `actual_lag <= W` (ví dụ `lag = 5` nằm **TRONG** `W=5`; `lag = 10` nằm **TRONG** `W=10`; `lag = 20` nằm **TRONG** `W=20`).
- **`OUTSIDE WINDOW`:** `actual_lag > W` (ví dụ `lag = 6` nằm **NGOÀI** `W=5`; `lag = 12` nằm **NGOÀI** `W=10`).

### 4.2. Phân bố `Actual Lag` Thực nghiệm từ Trace Ngoại tuyến (`MockLLMProvider`)

| Phép thử / Kịch bản | `W` | `planned_revisits` | `actual_revisits` *(Played)* | Phân bố `actual_lag` quan sát | `In Window` (`<= W`) | `Outside Window` (`> W`) | Ghi chú dịch chuyển `lag` |
|---|---:|---:|---:|---|---:|---:|---|
| **Track 2A (`product_education_10m_ext`)** | `5` | `18` | `18 / 18` | `{6: 18}` | **`0`** (`0%`) | **`18`** (`100%`) | `0` fallback -> `lag = 6` đều tuyệt đối |
| **Track 2A (`product_education_10m_ext`)** | `10` | `18` | `18 / 18` | `{6: 9, 7: 5, 8: 4}` | **`18`** (`100%`) | **`0`** (`0%`) | `6` lượt `PREAPPROVED_FALLBACK` chèn vào history làm `lag` tăng lên `7–8`, vẫn `<= 10` |
| *(Đối chứng `24t`: `window_sensitivity_stress_24t`)* | `5` | `24` | `24 / 24` | `{8: 24}` | **`0`** (`0%`) | **`24`** (`100%`) | Chuẩn `lag = 8` |
| *(Đối chứng `24t`: `window_sensitivity_stress_24t`)* | `10` | `24` | `24 / 24` | `{8: 9, 9: 6, 10: 9}` | **`24`** (`100%`) | **`0`** (`0%`) | `6` fallback đẩy `lag` tối đa tới `10` (`= W`) — sát biên `W=10` |
| **Track 2B (`window_stress_12lag_3sku`)** | `10` | `36` | `36 / 36` | `{12: 34, 13: 2}` | **`0`** (`0%`) | **`36`** (`100%`) | `2` fallback ở cuối/giữa đẩy `2` topic lên `lag=13 > 10` |
| **Track 2B (`window_stress_12lag_3sku`)** | `20` | `36` | `35 / 36` | `{12: 3, 13: 3, 14: 29}` | **`35`** (`100%`) | **`0`** (`0%`) | `6` fallback đẩy đa số revisit sang `lag=14 <= 20`; `topic-formal-macadamia-12` dừng trước lần 2 do `MAX_CONSECUTIVE_ABORTS` |

> **Kết luận `5A`:** Trong Track 2A (`lag=6`), **100% cơ hội lặp nằm ngoài `W=5` và 100% nằm trong `W=10`**. Trong Track 2B (`lag=12`), **100% cơ hội lặp nằm ngoài `W=10` và 100% nằm trong `W=20`**. Nếu một chuỗi `PREAPPROVED_FALLBACK` dày hơn trên Gemini thực đẩy vài topic ở `24t` (`lag=8 -> 11 > W=10`), ta càng thấy `product_education_10m_ext` (`lag=6 -> max 8 <= 10`) có biên an toàn (`safety margin`) tốt hơn hẳn cho Track 2A!

### 4.3. Ví dụ Trace Cấp Lượt (`Topic ID`, `SKU`, `Claims`, `Lag`, `Window Hit`, `Detector`)

- **Track 2A (`W=5` vs `W=10`) — Topic `topic-ext-edu-honey-usage` (`SKU-HONEY-01`):**
  - Lượt 1: `turn-...-0000` (`pos=0`, `prior_claims=['clm-e01-ext-honey-allowed-04']`).
  - Lượt 2: `turn-...-0006` (`pos=6`, **`actual_lag = 6 - 0 = 6`**):
    - Ở `W=5`: `in_window = False` -> `RepetitionDetector` trả `NONE:ALLOW` (không thấy `turn-0000`).
    - Ở `W=10`: `in_window = True` -> `RepetitionDetector` thấy `turn-0000`, phân loại **`LEGITIMATE_CONTINUATION:ALLOW`** (do mock `idx=1` dùng `curr_claims=[]` và `word_jaccard=0.192 < 0.40`).
- **Track 2A (`W=10`) — Topic `topic-ext-edu-honey-harvest` (`turn_index=9`):** `attempt=0` gặp `EXACT_REPLAY -> REWRITE`; sang `attempt=1` (`r1` có `curr_claims=['clm-e01-ext-honey-allowed-03']`), vì lượt 1 vẫn ở trong `W=10`, detector chặn ngay **`REPEATED_FACTS:SWITCH_TOPIC` (`fact_overlap_ratio=1.000`)** -> sang `attempt=2` vẫn `REPEATED_FACTS:SWITCH_TOPIC` -> rơi sang `PREAPPROVED_FALLBACK` (đẩy `lag` các topic sau từ `6` lên `7`).
- **Track 2B (`W=10` vs `W=20`) — Topic `topic-formal-honey-01` (`SKU-HONEY-01`, `pos=0 -> pos=12`, `actual_lag=12`):**
  - Ở `W=10`: `in_window = False` -> `NONE:ALLOW` (`turn-0000` ngoài cửa sổ 10).
  - Ở `W=20`: `in_window = True` -> thấy `turn-0000` (`word_jaccard=0.107`), khi retry/dùng lại `claim_id` trong SKU sẽ kích hoạt `REPEATED_FACTS:SWITCH_TOPIC` và dẫn tới `MAX_CONSECUTIVE_ABORTS` sau khi hết fallback.

---

## 5. Controlled Memory Contrast & Fixed-History Detector Check (`5B`, `5C`, `5E`)

### 5.1. Cơ chế Từ chối theo Tầng của `RepetitionDetector` trên Offline Traces (`5B`)

- **Tách biệt *nhớ nội dung* vs *chắc chắn reject*:** Khi lượt 1 nằm trong `W` (`actual_lag <= W`), `RepetitionDetector` có thể phân loại 1 trong 4 nhánh sau tùy candidate:
  1. `EXACT_REPLAY` (`SWITCH_TOPIC` nếu trùng `chunk_id`, `REWRITE` nếu trùng text chuẩn hóa).
  2. `LEXICAL_DUPLICATION` (`word_jaccard >= 0.65` hoặc `ngram3_jaccard >= 0.45` -> `REWRITE`).
  3. `REPEATED_FACTS` (`fact_overlap_ratio >= 0.80` cùng `intent` & `sku_id` -> `SWITCH_TOPIC` nếu cùng `topic_id`, `REWRITE` nếu khác `topic_id`).
  4. `LEGITIMATE_CONTINUATION` / `NONE` -> `ALLOW` (chỉ cho phép khi không trùng text và có `claim_id` mới hoặc `curr_claims = []` với `word_jaccard < 0.40`).
- **Lưu ý quan trọng về `mock_fixtures.py`:** Trên bước `idx=1` (`attempt=0`), `build_e01_mock_provider(..., min_chunks_per_topic=2)` đặt `curr_claims = []` và lấy evidence phụ từ `alt_pool` của cùng SKU; chỉ từ bước retry (`attempt>=1`, `step_i=0`) mock mới giữ nguyên `covered_claim_ids = topic.allowed_claim_ids`. Do đó trên Mock, lượt 2 ở `attempt=0` chỉ kích hoạt `REPEATED_FACTS` sau khi bị `EXACT/LEXICAL` đẩy sang `rewrite`, **còn trên Gemini thật**, vì mỗi topic trong stress plan chỉ có **1 `allowed_claim_id` duy nhất**, LLM thường điền `covered_claim_ids = [claim_id đó]` ngay ở `attempt=0`!

### 5.2. Fixed-History Detector Check (`5C` — Cô lập `W` khỏi Biến thiên LLM & Phân kỳ Lịch sử)

Đã bổ sung bài test tự động `test_fixed_history_detector_memory_contrast_lag6_lag8_lag12` vào [`tests/unit/test_formal_benchmark_prep.py`](../tests/unit/test_formal_benchmark_prep.py), kiểm thử cùng 1 lượt đích tại index `0` và cùng 4 ứng viên trên toàn bộ dải biên `lag ∈ {5, 6, 8, 10, 11, 12, 20, 21}` đối chiếu qua `W ∈ {5, 10, 20}`:

| `actual_lag` | Vị trí trong `W=5 / W=10 / W=20` | `EXACT_TEXT` | `LEXICAL_NEAR` (`wj >= 0.65`) | `PARAPHRASE_SAME_CLAIM` (`fo=1.0`) | `NEW_CLAIM_CONTINUATION` |
|---:|:---:|---|---|---|---|
| `lag = 5` | **IN / IN / IN** | `EXACT_REPLAY:REWRITE` × 3 | `LEXICAL_DUPLICATION:REWRITE` × 3 | `REPEATED_FACTS:SWITCH_TOPIC` × 3 | `LEGITIMATE_CONTINUATION:ALLOW` × 3 |
| **`lag = 6`** *(Track 2A)* | **OUT / IN / IN** | `W=5`: `NONE:ALLOW`<br>`W=10,20`: **`EXACT_REPLAY`** | `W=5`: `NONE:ALLOW`<br>`W=10,20`: **`LEXICAL_DUP`** | `W=5`: `NONE:ALLOW`<br>`W=10,20`: **`REPEATED_FACTS`** | `W=5`: `NONE:ALLOW`<br>`W=10,20`: `LEGIT_CONT:ALLOW` |
| `lag = 8` *(24t)* | **OUT / IN / IN** | `W=5`: `NONE:ALLOW` \| `W=10,20`: reject | `W=5`: `NONE:ALLOW` \| `W=10,20`: reject | `W=5`: `NONE:ALLOW` \| `W=10,20`: reject | `ALLOW` (cả 3) |
| `lag = 10` | **OUT / IN / IN** | `W=5`: `NONE:ALLOW` \| `W=10,20`: reject | `W=5`: `NONE:ALLOW` \| `W=10,20`: reject | `W=5`: `NONE:ALLOW` \| `W=10,20`: reject | `ALLOW` (cả 3) |
| `lag = 11` | **OUT / OUT / IN** | `W=5,10`: `NONE` \| `W=20`: reject | `W=5,10`: `NONE` \| `W=20`: reject | `W=5,10`: `NONE` \| `W=20`: reject | `ALLOW` (cả 3) |
| **`lag = 12`** *(Track 2B)* | **OUT / OUT / IN** | `W=5,10`: `NONE:ALLOW`<br>`W=20`: **`EXACT_REPLAY`** | `W=5,10`: `NONE:ALLOW`<br>`W=20`: **`LEXICAL_DUP`** | `W=5,10`: `NONE:ALLOW`<br>`W=20`: **`REPEATED_FACTS`** | `W=5,10`: `NONE:ALLOW`<br>`W=20`: `LEGIT_CONT:ALLOW` |
| `lag = 20` | **OUT / OUT / IN** | `W=5,10`: `NONE` \| `W=20`: reject | `W=5,10`: `NONE` \| `W=20`: reject | `W=5,10`: `NONE` \| `W=20`: reject | `ALLOW` (cả 3) |
| `lag = 21` | **OUT / OUT / OUT** | `NONE:ALLOW` × 3 | `NONE:ALLOW` × 3 | `NONE:ALLOW` × 3 | `NONE:ALLOW` × 3 |

### 5.3. Cách Diễn giải Stress Scenario (`5E`)

Mỗi chủ đề trong `product_education_10m_ext` và `window_stress_12lag_3sku` cố ý chỉ có **1 `allowed_claim_id`** và **không** được thiết kế cho 2 lượt mang 2 nhóm sự thật hoàn toàn độc lập. Vì vậy, khi `W` đủ lớn để nhớ lượt 1 (`W=10` ở `lag=6` hoặc `W=20` ở `lag=12`), `RepetitionDetector` **cố ý có thể chặn chunk thứ hai bằng `REPEATED_FACTS:SWITCH_TOPIC`** dẫn tới `PREAPPROVED_FALLBACK` hoặc `MAX_CONSECUTIVE_ABORTS`. Đây là **controlled stress condition** chứng minh bộ nhớ `W` đang **hoạt động đúng chức năng phát hiện lặp sự thật**, **tuyệt đối không** suy diễn rằng `W=20` "kém hơn" `W=10` trong mọi kịch bản livestream tự nhiên (nơi `min_chunks_per_topic=1` hoặc mỗi topic có nhiều claims khác nhau).

---

## 6. Kết quả Chi tiết Ngoại tuyến trên `MockLLMProvider` (`Offline Dry-Run`)

| Nhóm / Chỉ số | Track 2A `W=5` (`lag=6`) | Track 2A `W=10` (`lag=6..8`) | Alt `24t` `W=5` (`lag=8`) | Alt `24t` `W=10` (`lag=8..10`) | Track 2B `W=10` (`lag=12..13`) | Track 2B `W=20` (`lag=12..14`) |
|---|---:|---:|---:|---:|---:|---:|
| **Termination** | `EARLY_COMPLETION` | `EARLY_COMPLETION` | `EARLY_COMPLETION` | `EARLY_COMPLETION` | `EARLY_COMPLETION` | `MAX_CONSECUTIVE_ABORTS` |
| **Compatibility Check** | `PASS` | `PASS` | — | — | `PASS` | `PASS` |
| **Total Requests (`Base + Rewrite`)** | `42` (`36 + 6`) | `52` (`42 + 10`) | `58` (`48 + 10`) | `77` (`57 + 20`) | `102` (`74 + 28`) | `156` (`98 + 58`) |
| **Failed Calls / Wasted Calls** | `0` / `6` | `0` / `16` | `0` / `10` | `0` / `29` | `0` / `30` | `0` / `85` |
| **Played Turns** | `36` | `42` | `48` | `54` | `74` | `77` |
| **Fallback Count (`Rate`)** | `0` (`0.00%`) | `6` (`14.29%`) | `0` (`0.00%`) | `6` (`10.53%`) | `2` (`2.70%`) | `6` (`6.12%`) |
| **True Safe Aborts (`Rate`)** | `0` (`0.00%`) | `0` (`0.00%`) | `0` (`0.00%`) | `3` (`5.26%`) | `0` (`0.00%`) | `21` (`21.43%`) |
| **Rewrite Turns `rate` (`sum retries`)** | `16.67%` (`6`) | `14.29%` (`12`) | `16.67%` (`10`) | `21.05%` (`21`) | `29.73%` (`28`) | `30.61%` (`58`) |
| **Detector Rejects: `EXACT / LEX / FACTS`** | `4 / 2 / 0` | `4 / 2 / 10` | `5 / 5 / 0` | `7 / 9 / 13` | `7 / 23 / 0` | `8 / 44 / 33` |
| **Detector Actions: `REWRITE / SWITCH`** | `6 / 0` | `6 / 10` | `10 / 0` | `16 / 13` | `30 / 0` | `52 / 33` |
| **Required Chunk Completion (`>=2` ACK)** | `18/18` (`100%`) | `18/18` (`100%`) | `24/24` (`100%`) | `24/24` (`100%`) | `36/36` (`100%`) | **`35/36` (`97.22%`)** |
| **`mandatory_topic_coverage`** | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `1.0000` | **`0.9722`** |
| **Exact Chunk / Exact Text Replay** | `0` / `0` | `0` / `0` | `0` / **`2`** | `0` / `0` | `0` / `0` | `0` / `0` |
| **`outside_window_exact_text_replay`** | `0` | `0` | **`2`** | `0` | `0` | `0` |
| **`lexical_repetition_rate`** | `0.0000` | `0.0000` | `0.0426` | `0.0000` | `0.0274` | `0.0000` |
| **`max_prior_ngram3_jaccard_mean`** | `0.1527` | `0.1656` | `0.1988` | `0.1693` | `0.1756` | `0.1691` |
| **`windowed_ngram3_mean (w5/w10/w20)`** | `.133/.148/.152` | `.149/.162/.164` | `.149/.194/.198` | `.158/.162/.169` | `.147/.152/.174` | `.150/.162/.166` |
| **`claim_overlap_rate`** | `0.4348` | `0.2353` | `0.5484` | `0.3913` | `0.6364` | `0.4286` |
| **`distinct_1 / distinct_2 / distinct_3`** | `.359/.579/.697` | `.316/.542/.663` | `.346/.592/.685` | `.324/.579/.689` | `.287/.554/.667` | `.280/.555/.674` |
| **Simulated Tokens (`in / out / wasted`)** | `5040/1890/990` | `6240/2340/2640` | `6960/2610/1650` | `9240/3465/4785` | `12240/4590/4950` | `18720/7020/14025` |

---

## 7. Kiểm chứng Tính đúng đắn của `coverage.py` & `reliability.py` (`5D`)

Kiểm tra trực tiếp mã nguồn [`coverage.py`](../src/p06/evaluation/metrics/coverage.py#L106-L135) và [`reliability.py`](../src/p06/evaluation/metrics/reliability.py#L70-L95) cùng dữ liệu chạy Track 2 xác nhận:

1. **Đếm đủ `>= 2` non-fallback `PlaybackCompleted` ACKs:** Trong Track 2A `W=10` dù có `6` lượt `PREAPPROVED_FALLBACK` hoàn tất phát sóng, `fallback_turn_ids` bị loại hoàn toàn trước khi đếm `played_chunk_counts_by_topic` -> chỉ `18/18` topics có `>= 2` ACK chủ động mới tính vào `completed_topic_count`.
2. **Tách rạch ròi topic mới xong 1 chunk:** Trong Track 2B `W=20`, khi `topic-formal-macadamia-12` mới phát xong `1` chunk trước khi cạn `MAX_CONSECUTIVE_ABORTS = 3`, `completed_topic_count = 35`, `mandatory_topic_coverage = 35/36 = 0.9722`, và `partially_covered_topic_ids = ["topic-formal-macadamia-12"]` được ghi nhận trung thực, không bao giờ báo khống `1.0`.
3. **Không đếm nhầm lượt chuyển SKU sạch là `safe_abort`:** Các lượt biên `should_terminate=True` khi `ArcSequencer` báo hết chủ đề cho SKU hiện tại (`turn_index=12, 25, 38` ở 2A `W=5`) bị lọc bởi `is_clean_termination_boundary_trace()`, giúp `safe_abort_count` giữ chính xác bằng `0` (2A) và `21` (2B `W=20`, phát sinh trên SKU cạn fallback trước khi dừng ở ngưỡng `3` consecutive aborts).

---

## 8. Phân tích Ngân sách & Công bằng Thực thi Thật (`Budget & Fairness`)

### 8.1. Ước lượng Ngân sách Thực tế cho Live Gemini Free Tier

Dựa trên kết quả Mock thực tế (Mục 6) kết hợp hai đặc trưng đã đo trên Gemini Batch 1A/1B: (i) tỷ lệ duration rewrite (`>20` từ) khoảng **`20%–22%`** ở lượt đầu, (ii) tỷ lệ `HTTP 503` ~`4%–6%`, và (iii) khả năng `W=10` (Track 2A) / `W=20` (Track 2B) gặp `REPEATED_FACTS` ở chunk #2 khiến mỗi topic chạm `REPEATED_FACTS` tiêu tốn `min(3 calls -> fallback/abort)` thay vì dừng ở `1` call:

| Track | Cấu hình | Mock `calls` | Dự báo Gemini Thực *(khoảng an toàn)* | Cap/Run Đề xuất | Global Cap | Thời gian (~6s/req) | % Quota `500 RPD` |
|---|---|---:|---|---:|---:|---:|---:|
| **Track 2A** *(Ngày 1)* | `W=5` (`lag=6`) | `42` | `~48–60` req *(36 base + ~8–12 duration/lexical rw + 503)* | **`120`** | **`240`** | `~14–22 phút` | `~25%–32%` *(trần `48%`)* |
| | `W=10` (`lag=6..8`) | `52` | `~65–110` req *(tùy số topic chạm `REPEATED_FACTS` hoặc tự paraphrase không khai báo trùng `claim_id`)* | **`120`** | | | |
| **Track 2B** *(Ngày 2)* | `W=10` (`lag=12..13`) | `102` | `~95–125` req *(72 base + ~16–20 duration/lexical rw + 503)* | **`200`** | **`400`** | `~35–55 phút` | `~55%–75%` *(trần `80%`)* |
| | `W=20` (`lag=12..14`) | `156` | `~115–190` req *(nếu bị `REPEATED_FACTS` sớm sẽ chạm `MAX_CONSECUTIVE_ABORTS` quanh `105–150` req; nếu qua được bằng paraphrase + lexical rewrite có thể tới `170–190` req)* | **`200`** | | | |

- **Công bằng & Ràng buộc:** Cùng `max_turns` và cùng `max_requests_per_run` giữa hai cấu hình trong mỗi scenario (`80/120` cho 2A; `120/200` cho 2B). Chạy riêng **Track 2A vào Ngày 1** và **Track 2B vào Ngày 2** để mỗi ngày giữ dưới ngưỡng `500 RPD` của Google AI Studio Free Tier (`0 USD`). Giữ sequential requests, pacing `>= 6.0s`, `budget_ledger.json` mới (không dùng lại dư của 1A/1B) và `stop_on_rate_limit = true`.
- *Phương án rút gọn nếu quota Free Tier thấp (`<250 RPD`):* Có thể chạy riêng `Track 2A` trước (`~140 req`), hoặc tách `Track 2B W=10` (~110 req) và `W=20` (~160 req) thành hai phiên cách ngày nếu không đủ `300+ RPD` trong một ngày (không khuyến nghị gộp 2 ngày khác RPD vào `budget_ledger` mà chỉ tách run nếu buộc phải tránh 429).

---

## 9. Tài nguyên Khóa & Bảng SHA-256 (`13/13` Tệp Khóa)

Giữ nguyên `100%` mô hình (`gemini-3.5-flash-lite` Free Tier), sampling (`temperature=0.3, top_p=0.9, max_tokens=1024, thinking_level=MINIMAL`), prompts (`v0.1 / v0.2.1 / baseline-v0.2.2`), datasets (`e01_ext_v1 v1.0.2`, `e01_formal_v1 v1.1.1`), P05/guardrails/retry/duration (`8.0s`), và bổ sung 2 tệp Track 2:

| Tài nguyên | Đường dẫn (trong `autonomous-storytelling/`) | Phiên bản | SHA-256 |
|---|---|---|---|
| Dataset `e01_ext_v1` SKUs | `data/products/e01_ext_v1_verified_skus.json` | `1.0.1` | `6ab12c62f3545d804b55ba5e23477f7b610313f81775cdd5452a783916518c64` |
| StoryPlans `e01_ext_v1` | `data/story_plans/e01_ext_v1_story_plans.json` | `1.0.2` | `42c446c4f0c36293b48f985a78079360abd7db243bc66ca532e058f47047f020` |
| Dataset `e01_formal_v1` SKUs | `data/products/e01_formal_v1_verified_skus.json` | `1.1.1` | `bd70430b9f5dfa34fc5ea13560aa437f9dd994ce92159f9000106ca7eb1a71c6` |
| StoryPlans `e01_formal_v1` | `data/story_plans/e01_formal_v1_story_plans.json` | `1.1.1` | `f969ec242b30578275cac01c2d10eaf602b57a3b6a3bbf12a42dcdc924f055f3` |
| Prompt `story_planner.txt` | `prompts/story_planner.txt` | `v0.1` | `f07514cc307bff4a3332d419a539f843bb18510722bdc7774a26a9ff98ddd118` |
| Prompt `story_generation.txt` | `prompts/story_generation.txt` | `v0.2.1` | `0f1eb7e856654d9565a9e6dbe468f59180c3dc20bc4cb723cd1441d5000d5912` |
| Prompt `rewrite.txt` | `prompts/rewrite.txt` | `v0.2.1` | `1126789faaf84f547a455b677af4b025103e3a1b60513e1fc0910cc14a5c61d5` |
| Prompt `ScriptFirstBaseline` | `src/p06/baselines/script_first.py` (`_UPFRONT_PROMPT_SHA256`) | `baseline-script-first-v0.2.2` | `50ed84045f0014400ae60a799513968c5f4d68054e77cf79f9578823184554d4` |
| Model Config Free Tier | `configs/models/gemini_3.5_flash_lite_free.yaml` | `free_tier` | `c836c82baee490a4b4d728e2877d19e4fd15c16a87c64372a9af3692a7ab344b` |
| Batch 1A Config | `configs/experiments/p06_e01_formal_batch1a.yaml` | `batch1a_s42` | `3792162ed9c7b3e0b35054575e82804f00615f759efe44c42968fc825716cfdc` |
| Batch 1B Config | `configs/experiments/p06_e01_formal_batch1b.yaml` | `batch1b_s42` | `f380892c137606f0277aafa809a4623a904a9f262c10797cf0cb897b42079fd2` |
| **Track 2A Config (Mới)** | [`configs/experiments/p06_e01_formal_track2a_w5_w10.yaml`](../configs/experiments/p06_e01_formal_track2a_w5_w10.yaml) | `track2a_lag6_s42` | **`d52a17b1c832093490e5b0092921c56d2e09488e8d7335088156ae41a23e5ae7`** |
| **Track 2B Config (Mới)** | [`configs/experiments/p06_e01_formal_track2b_w10_w20.yaml`](../configs/experiments/p06_e01_formal_track2b_w10_w20.yaml) | `track2b_lag12_s42` | **`b4e6c539e1f316219e86d35532c3e0dde0e3a993c41c7ffd1897d287221354b4`** |

---

## 10. Khung Đánh giá & Khả năng Áp dụng Acceptance Criteria cho Track 2 (`§8`)

### 10.1. Bảy nhóm / 17 Chỉ số Bắt buộc cho Báo cáo Track 2

Khi chạy Track 2 thật, báo cáo kết quả bắt buộc trình bày đủ `17` hạng mục sau, đồng thời **tách biệt internal window `W` (ngưỡng nhìn của `RepetitionDetector`) với common evaluation horizon (toàn phiên)** và **tách riêng *deliberate recurrence* (do thiết kế `m=2`) với *unwanted repetition***:

1. `planned_repetition_opportunities` (`18` cho 2A; `36` cho 2B).
2. `actual_repetition_opportunities` (trên playback-confirmed history).
3. `actual_lag_distribution` (`lag = L - j`, minh bạch ảnh hưởng của fallback).
4. `window_hit_vs_miss` (`in_window <=> actual_lag <= W`).
5. `detector_rejection_by_reason` (`EXACT_REPLAY`, `LEXICAL_DUPLICATION`, `REPEATED_FACTS` và action `REWRITE` / `SWITCH_TOPIC`).
6. `exact_chunk_replay_count` & `exact_normalized_text_replay_count` & `outside_window_exact_text_replay_count`.
7. `lexical_repetition_rate` toàn phiên + `windowed_ngram3_jaccard_mean_w{5,10,20}`.
8. `semantic_repetition_assessment` (đánh giá paraphrase/lặp ý, không dùng `lexical_repetition == 0` làm bằng chứng duy nhất cho hiệu quả memory).
9. `repeated_facts` (`claim_overlap_rate` + số lượt bị `REPEATED_FACTS`).
10. `required_chunk_completion` (`topics_with_>=2_non_fallback_acks / planned_topics`).
11. `mandatory_topic_coverage` (từ `coverage.py` với `min_chunks_per_topic = 2`).
12. `rewrite_rate` (tổng và thuần logic).
13. `wasted_calls` (tổng và thuần logic, tách khỏi `HTTP 503`).
14. `fallback_rate` (tổng và thuần logic).
15. `safe_abort_count` / `MAX_CONSECUTIVE_ABORTS`.
16. `token_usage` (`measured / partial` + `wasted_tokens`).
17. `termination_reason`.

### 10.2. Phân loại Khả năng Áp dụng Acceptance Criteria (Không thay đổi Ngưỡng Natural Track)

| Nhóm Tiêu chí (Khóa ở `docs/11-...`) | Áp dụng cho **Stress Track 2** | Giải thích Khoa học |
|---|---|---|
| **Hard Safety Gates (`0` vi phạm):** `exact_chunk_replay == 0`, `hygiene_leaks == 0`, `invalid_evidence == 0`, `cross_sku == 0`, `retry_budget_violations == 0` | **ÁP DỤNG BẮT BUỘC (`PASS/FAIL`)** | Bất biến an toàn & kỷ luật retry áp dụng mọi điều kiện, kể cả stress |
| **`outside_window_exact_text_replay_count`, `detector_rejects`, `lexical/semantic repetition`** | **ÁP DỤNG ĐỊNH LƯỢNG ĐỐI CHIẾU (`W` Sensitivity)** | Đây là biến phụ thuộc chính đo hiệu quả ghi nhớ theo khoảng `lag` |
| **Natural Track Soft/Reliability Thresholds:** `mandatory_topic_coverage >= 95%`, `logic rewrite <= 15%`, `logic fallback <= 5%`, `logic wasted <= 10%` | **CHỈ MANG Ý NGHĨA MÔ TẢ (`DESCRIPTIVE ONLY`)** | Trong stress `m=2` với 1 claim/topic, `W=10` (2A) hay `W=20` (2B) nhớ lượt 1 và từ chối hợp lý (`REPEATED_FACTS`) có thể gây tăng `rewrite`, `fallback` hoặc dừng `MAX_CONSECUTIVE_ABORTS` (<95%). Không dùng các ngưỡng Natural Track để kết luận `W` lớn "thất bại" |

---

## 11. Giới hạn Nghiên cứu của Track 2

1. **Thiết kế 1 claim/topic trong stress scenario:** Không đo khả năng triển khai góc nhìn mới (`LEGITIMATE_CONTINUATION`) mà chủ yếu đo phản ứng nhớ-và-chặn lặp khi bắt buộc quay lại cùng chủ đề.
2. **Độ lệch Mock vs Live Gemini:** Như đã chỉ ra ở Mục 5.1, `MockLLMProvider` bỏ `covered_claim_ids` ở lượt `idx=1` primary còn Gemini thật có thể tự điền `covered_claim_ids` ngay `attempt=0` (kích hoạt `REPEATED_FACTS` sớm hơn) hoặc paraphrase không khai báo trùng `claim_id` (lọt `RepetitionDetector` nhưng sẽ lộ khi audit semantic repetition).
3. **Khác biệt `seed=42`, `n=1` và mô hình bất định:** Mỗi cặp `W` chạy 1 lần trên `gemini-3.5-flash-lite` Free Tier; `provider_latency_ms` tiếp tục bao gồm client pacing `6.0s` và proxy thời lượng dùng `words/2.6` chứ chưa phải TTS audio thật.
4. **Human Blind Evaluation & `GoldFactualLabel`:** Vẫn đang `PENDING` ở Batch 1A và 1B.

---

## 12. Lệnh Thực thi Đề xuất (CHỈ CHẠY SAU KHI TECH LEAD PHÊ DUYỆT)

> [!IMPORTANT]
> Tuyệt đối **KHÔNG** tự ý chạy các lệnh dưới đây trước khi nhận được **Final Track 2 Execution Approval** và xác nhận quota RPD khả dụng (`0 USD`).

```powershell
# Track 2A (Ngày 1 — Small Window Sensitivity W=5 vs W=10, lag=6, cap 240 req):
.\.venv\Scripts\python.exe experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_gemini_formal_batch.py `
  --config experiments/sales-intelligence/autonomous-storytelling/configs/experiments/p06_e01_formal_track2a_w5_w10.yaml `
  --allow-live-provider

# Track 2B (Ngày 2 — Large Window Sensitivity W=10 vs W=20, lag=12, cap 400 req):
.\.venv\Scripts\python.exe experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_gemini_formal_batch.py `
  --config experiments/sales-intelligence/autonomous-storytelling/configs/experiments/p06_e01_formal_track2b_w10_w20.yaml `
  --allow-live-provider
```

---

## 13. Công việc Còn lại để Đóng `P06-E01` & Kiểm chứng Phiên Hiện tại

| Hạng mục DoD (`P06-E01`) | Trạng thái | Bước Tiếp theo |
|---|---|---|
| **DoD-1 & DoD-2 (Natural Track 1A + 1B)** | `COMPLETED (Reduced Scope)` | Batch 1A + 1B + AI-assisted evals đã lưu đủ; `seed=43` / `30m` deferred |
| **DoD-2 (History Window Track 2A + 2B)** | **`READY — AWAITING APPROVAL`** | Chờ Tech Lead duyệt ngân sách/quota để chạy live `Track 2A` & `Track 2B` |
| **DoD-3 (Human Blind Eval & Gold Labels)** | `PENDING` | Chờ chấm mù người thật trên mẫu formal trước khi kết thúc `E01` |
| **DoD-4..DoD-6 (`reports/` & Kết luận `E01`)** | `PENDING` | Sau Track 2 + Human Eval: chạy `notebooks/` và viết `reports/final_report.md` / `e01_report.md` kết thúc E01 |

**Trạng thái dừng:** **`AWAITING_FINAL_TRACK2_EXECUTION_APPROVAL`**
