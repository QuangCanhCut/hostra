# Báo cáo Thực thi & Phân tích Formal Benchmark Batch 1A — HOSTRA AI (`P06-E01-T09`)

**Ngày lập báo cáo:** `2026-11-27`  
**Branch:** `research/p06-autonomous-storytelling`  
**Base Commit trước thực thi:** `bad90c9` (`feat(p06): lock E01 formal benchmark protocol and safety corrections`)  
**Module:** `experiments/sales-intelligence/autonomous-storytelling/`  
**Phân loại phiên:** **`Controlled Exploratory Benchmark`** *(Phương án B — Pilot v2 Human Calibration tạm hoãn; Batch 1A Approved Only)*  
**Trạng thái hiện tại:** **`AWAITING_BATCH_1A_REVIEW_AND_NEXT_BATCH_APPROVAL`** *(Không chạy thêm API sau Batch 1A; `overall_gate_status = NOT_EVALUATED` do chờ Human Blind Evaluation & Gold Factual Labels)*

---

## 1. Tóm tắt Điều hành (Executive Summary)

Nhóm kỹ thuật đã hoàn tất thực thi **Formal Benchmark Batch 1A** trên mô hình thật **`gemini-3.5-flash-lite` Free Tier (`0 USD`)** cho kịch bản tự nhiên **`product_education_10m_ext`** (`e01_ext_v1`, `seed=42`, `min_chunks_per_topic=1`, `4` cấu hình tuần tự). Toàn bộ quá trình chạy, thu thập metrics, kiểm tra an toàn và xuất hồ sơ chấm mù đã tuân thủ chặt khóa cấu hình trong [`11-e01-t09-formal-benchmark-protocol.md`](./11-e01-t09-formal-benchmark-protocol.md) và ngân sách phê duyệt.

Các kết quả thực nghiệm cốt lõi từ Batch 1A:

1. **Tuân thủ ngân sách & vận hành an toàn tuyệt đối:** Tổng số yêu cầu API tiêu thụ qua sổ cái toàn cục [`budget_ledger.json`](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/budget_ledger.json) là **`94 / 120` requests** (dư `26` requests, mọi run đều `<= 27 <= 30` req/run), **`0 USD` chi phí thực trả**, **`0` lỗi `HTTP 429`**, **`4` lỗi hạ tầng `HTTP 503`** (`3` ở `W=10`, `1` ở `W=20`), **`0` rò rỉ khóa API hoặc metadata kỹ thuật**, và **`0` ghi đè** lên Pilot v1/v2.
2. **Chênh lệch rõ rệt giữa LangGraph và Script-first trên độ phủ chủ đề (`RQ1`):**
   - Cả **`3/3` cấu hình LangGraph (`W=5`, `W=10`, `W=20`)** đạt **`100%` (`12/12`) `mandatory_topic_coverage`**, **`100%` (`18/18`) độ phủ toàn bộ kế hoạch** và **`100%` (`14/14`) `declared_verified_claim_coverage`**, kết thúc sạch tại `EARLY_COMPLETION` (ngay cả khi `W=10` gặp `3` lần `HTTP 503` và `W=20` gặp `1` lần `HTTP 503` + `1` lần cạn retry).
   - Ngược lại, **`script_first_upfront_llm`** (`max_retries=0`) chỉ đạt **`58.33%` (`7/12`) `mandatory_topic_coverage`**, **`55.56%` (`10/18`) tổng số topic kế hoạch** và **`57.14%` (`8/14`) `declared_verified_claim_coverage`**, kết thúc ở `CONTENT_EXHAUSTED` với **`8/18` (`44.44%`) lượt sinh bị loại ngay đầu phiên** do vượt trần thời lượng `8.0s` (`21–24` từ), kéo theo `5` lượt fallback chung (đọc tên + giá) và `3` lượt hủy an toàn `SAFE_ABORT_NO_CANDIDATE` khi hết tối đa `2` mẫu fallback/SKU.
3. **Cơ chế `bounded_rewrite` (LangGraph) giải quyết điểm nghẽn `8.0s`, nhưng vẫn tiêu tốn `18%–30%` calls logic:** Trên tập chủ đề giàu chi tiết (`2` talking points/topic), `gemini-3.5-flash-lite` vẫn thường xuyên sinh dư `1–5` từ ở lượt đầu (`4/18` lượt ở `W=5`, `4/18` lượt non-503 ở `W=10`, `5/18` chủ đề ở `W=20`). Nhờ `bounded_rewrite` (`<= 2` retries), LangGraph cứu thành công trực tiếp `11/13` lượt vượt độ dài (`4/4` ở `W=5`, `4/4` ở `W=10`, `3/5` ở `W=20`; `2` lượt còn lại ở `W=20` gồm `turn 3` gặp `HTTP 503` khi retry rồi thành công ở `turn 4` và `turn 10` cạn `2` retry fallback rồi thành công ở `turn 11`), qua đó giải thích thực nghiệm vì sao ràng buộc `8.0s` là nút cổ chai vận hành lớn nhất của `Script-first`.
4. **Độ nhạy cửa sổ `W=5/10/20` chưa phân tách trên Track 1 (`RQ3`):** Trên kịch bản tự nhiên `m=1` (`18` chủ đề phân biệt, `0` chủ đề lặp bắt buộc), cả `W=5`, `W=10`, `W=20` đều đạt **`0` exact normalized text replay** và **`0.00%` lexical repetition rate**. Đáng chú ý, trên phiên `18–20` turns này, `W=20` **chưa từng bị cắt đuôi bộ nhớ** (`max_history = 19 < 20`), và ngay cả `W=5` cũng đạt `max_prior_ngram3_jaccard_mean = 0.0037` / `distinct_3 = 0.9930`. Vì vậy, **không kết luận `W` tối ưu chỉ từ Batch 1A**; **Track 2 (`lag=6/8` và `lag=12`, `m=2`) vẫn bắt buộc** nếu muốn kiểm định có kiểm soát cơ chế quên ngoài cửa sổ `W`.
5. **Giới hạn thời lượng thực tế so với mục tiêu 10–30 phút (`E01`):** Thời lượng phát mô phỏng chỉ đạt **`105.385s`–`145.000s` (`17.56%`–`24.17%` của `600s`)**, do giới hạn cứng của `18` chủ đề × `<= 8.0s`/chunk (`~6.7s–7.0s`/chunk). Không có hiện tượng ép lặp hay bịa fluff để kéo dài đồng hồ.
6. **Trạng thái Gate & Đánh giá con người:** `structural_hard_gates_status = PASS` trên cả 4 runs (`0` vi phạm replay `chunk_id`, `0` rò rỉ metadata, `0` sai mã bằng chứng/chéo SKU). Tuy nhiên, **`overall_gate_status` vẫn giữ `NOT_EVALUATED`** vì `Human Blind Evaluation` và `GoldFactualLabel` đang ở trạng thái **`PENDING`**. Kiểm tra sơ bộ của nhóm nghiên cứu phát hiện một vài thiếu sót ý nhỏ (`PARTIAL` trên talking points ở một số lượt do nén `<= 20` từ, đặc biệt `W=10` Turn `[16]` đổi `"không ăn gói hút ẩm"` thành `"giữ gói hút ẩm"`), cần người chấm độc lập thẩm định chính thức trên bộ [`human_eval/`](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/human_eval/).

---

## 2. Phê duyệt Tech Lead, Sai lệch Giao thức & Khóa Tiêu chí

### 2.1. Phạm vi Phê duyệt & Sai lệch Giao thức (Phương án B)
Trước khi gọi API, Tech Lead đã phê duyệt **chỉ thực thi Batch 1A** (`product_education_10m_ext`, `seed=42`) với ngân sách mới tối đa `120` requests (`<= 30` req/run, `0 USD`), không phê duyệt Batch 1B, Track 2, Track 3 hay E02/E03/E04.

Theo quyết định **Phương án B**, phiên này được ghi nhận là **`Controlled Exploratory Benchmark`** với sai lệch giao thức đã khóa trước execution tại [`protocol_deviation_and_criteria_lock.json`](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/protocol_deviation_and_criteria_lock.json) và [`DR-P06-011`](../research/decision_log.md):
- Kết quả đánh giá AI-assisted của ChatGPT trên Pilot v2 tại [`runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/ai_assisted_eval/`](../runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/ai_assisted_eval/) chỉ dùng để **hiệu chỉnh rubric sơ bộ**; tuyệt đối **không** dùng làm `Human Blind Evaluation` hay `GoldFactualLabel`, không gộp vào bảng so sánh Formal Benchmark và không ghi đè phiếu chấm gốc Pilot v2.
- **Human Evaluation Calibration** và **Gold Factual Assessment** giữ nguyên trạng thái **`PENDING`**.
- `overall_gate_status` không được phép đánh dấu `PASS` khi chưa có đủ đánh giá mù độc lập của con người và nhãn factual chuẩn.

### 2.2. Bảng Tiêu chí Chấp nhận Đã Khóa Trước Thực thi (`Acceptance Criteria Lock`)

| Nhóm Tiêu chí | Chỉ số / Cổng | Ngưỡng Khóa Trước Batch 1A |
|---|---|---:|
| **Hard Safety & Structural Gates** *(Không bù trừ)* | Metadata leakage, Incorrect facts, Unsupported claims, Invalid/Incomplete/Cross-SKU evidence, Unsupported causal inference, Missing commercial policy conditions, Prohibited claims, Completed chunk replay, Retry budget violation, Coverage update without valid ACK, Unauthorized SKU/StoryPlan modification | **`0` vi phạm** |
| **Quality & Reliability (Track 1 Natural)** | `mandatory_topic_coverage` | **`>= 95%`** (`0.95`) |
| | `semantic_alignment = FULL` *(Human Audit)* | **`>= 85%`** (`0.85`) |
| | `semantic_alignment = MISS` *(Human Audit)* | **`<= 5%`** (`0.05`) |
| | `exact_normalized_text_replay_count` | **`0`** |
| | `lexical_repetition_rate` | **`<= 5%`** (`0.05`) |
| | `rewrite_rate` do logic agent | **`<= 15%`** (`0.15`) |
| | `fallback_rate` do logic agent | **`<= 5%`** (`0.05`) |
| | `wasted_calls` do logic agent | **`<= 10%`** (`0.10`) |
| | `provider_latency` P50 / P95 *(tham chiếu)* | **`<= 7s` / `<= 10s`** |
| **Human Rubric v0.1 (`1–5`)** | Trung bình từng tiêu chí (`6` trục) trên toàn tập mỗi phương pháp / trên mỗi sample qua các reviewers | **`>= 3.5 / 5.0`** *(từng sample **`>= 3.0 / 5.0`**)* |

---

## 3. Xác minh Tiền kiểm & Khả năng Tái lập (Preflight & Reproducibility)

Toàn bộ 12 điều kiện preflight đã được xác minh trước khi gửi request đầu tiên:

1. **Git & Phạm vi repo:** Nhánh `research/p06-autonomous-storytelling`, commit gốc `bad90c9`, working tree sạch trước lúc chạy, không có `MERGE_HEAD`, không có thay đổi ngoài `experiments/sales-intelligence/autonomous-storytelling/`.
2. **Hồi quy trước khi chạy:** Mốc kiểm thử đã xác nhận tại `bad90c9` là `287 passed, 0 failed, 0 skipped` (`pip check` sạch).
3. **Bảo toàn tài nguyên cũ:** Thư mục Pilot v1 (`gemini_3.5_flash_lite_pilot/`), Pilot v2 (`gemini_3.5_flash_lite_pilot_v2/`) và các phiếu Human Evaluation gốc hoàn toàn nguyên vẹn; thư mục đích `runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/` được khởi tạo mới hoàn toàn với `--output-dir` (giữ nguyên vẹn tệp YAML khóa gốc).
4. **Kiểm tra khóa API & Quota:** `GEMINI_API_KEY` tồn tại trong biến môi trường tiến trình, không ghi ra file/log (`SECRET SCAN: 0 hits`), không có tiến trình `python` chạy nền nào khác. Tech Lead xác nhận Google AI Studio `Default Gemini Project` ở `Free Tier` (`RPM 10/15 peak`, `TPM 21.88K/250K peak`, `RPD 37/500 peak 28 ngày`, `0 USD`).
5. **Khớp 10/10 mã băm SHA-256 tài nguyên khóa:**

| Thành phần Khóa | Phiên bản | SHA-256 Xác minh | Khớp |
|---|---|---|:---:|
| `data/products/e01_ext_v1_verified_skus.json` | `1.0.1` | `6ab12c62...18c64` | PASS |
| `data/story_plans/e01_ext_v1_story_plans.json` | `1.0.2` | `42c446c4...7f020` | PASS |
| `data/products/e01_formal_v1_verified_skus.json` | `1.1.1` | `bd70430b...a71c6` | PASS |
| `data/story_plans/e01_formal_v1_story_plans.json` | `1.1.1` | `f969ec24...055f3` | PASS |
| `prompts/story_planner.txt` *(LF)* | `v0.1` | `f07514cc...dd118` | PASS |
| `prompts/story_generation.txt` *(LF)* | `v0.2.1` | `0f1eb7e8...d5912` | PASS |
| `prompts/rewrite.txt` *(LF)* | `v0.2.1` | `1126789f...c61d5` | PASS |
| `src/p06/baselines/script_first.py` (`_UPFRONT_PROMPT_SHA256`) | `baseline-script-first-v0.2.2` | `50ed8404...554d4` | PASS |
| `configs/models/gemini_3.5_flash_lite_free.yaml` | `free_tier` | `c836c82b...b344b` | PASS |
| `configs/experiments/p06_e01_formal_batch1a.yaml` | `batch1a_s42` | `3792162e...6cfdc` | PASS |

---

## 4. Cấu hình Thực thi & Danh sách Run IDs

- **Lệnh thực thi:**
  ```powershell
  .\.venv\Scripts\python.exe experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_gemini_formal_batch.py `
    --config experiments/sales-intelligence/autonomous-storytelling/configs/experiments/p06_e01_formal_batch1a.yaml `
    --allow-live-provider `
    --output-dir experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42
  ```
- **Lưu ý quan trọng về cấu trúc `product_education_10m_ext`:** Kịch bản này có **`18` planned topics** (`6` topics/SKU × `3` SKU), trong đó có **`12` chủ đề bắt buộc (`is_mandatory=true`)** (`4`/SKU) và **`6` chủ đề tùy chọn (`is_mandatory=false`)** (`2`/SKU: `harvest` và `pairing` của mỗi SKU). Cả `Script-first` và `LangGraph` đều duyệt toàn bộ `18` chủ đề theo tuần tự arc (`SKU-HONEY-01 -> SKU-TEA-02 -> SKU-MACADAMIA-03`), nên kỳ vọng cơ sở là `18 × 4 = 72` base calls. Trong báo cáo này, chúng tôi tách bạch cả **`mandatory_topic_coverage` (mẫu số `12`)** lẫn **tổng độ phủ chủ đề kế hoạch (mẫu số `18`)** để tránh nhầm lẫn.
- **Tham số khóa:** `gemini-3.5-flash-lite`, `Free Tier (0 USD)`, `SYNTHETIC`, `thinking_level=MINIMAL`, `temperature=0.3`, `top_p=0.9`, `max_tokens=1024`, `timeout=30s`, `seed=42`, `min_chunks_per_topic=1`, `max_chunk_duration_sec=8.0s` (`12–18` từ, trần cứng `20` từ ở `2.6` từ/giây), `max_rewrite_retries=2` (LangGraph) vs `0` (Script-first), `min_request_interval_sec=6.0s`, thực thi tuần tự.

| Cấu hình | `W` | Run ID & Đường dẫn | Thời gian UTC | Kết thúc |
|---|---:|---|---|---|
| `script_first_upfront_llm` | `N/A` | [`...script_first_upfront_llm__noW__20261126T211445Z__3103d050`](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/P06-E01__product_education_10m_ext__script_first_upfront_llm__noW__20261126T211445Z__3103d050/) | `21:14:45 -> 21:16:29` (`103.53s`) | `CONTENT_EXHAUSTED` |
| `langgraph_w5` | `5` | [`...langgraph_structured_story__w5__20261126T211629Z__b0e6e86e`](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/P06-E01__product_education_10m_ext__langgraph_structured_story__w5__20261126T211629Z__b0e6e86e/) | `21:16:29 -> 21:18:41` (`131.31s`) | `EARLY_COMPLETION` |
| `langgraph_w10` | `10` | [`...langgraph_structured_story__w10__20261126T211841Z__71bed1ea`](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/P06-E01__product_education_10m_ext__langgraph_structured_story__w10__20261126T211841Z__71bed1ea/) | `21:18:41 -> 21:21:24` (`162.70s`) | `EARLY_COMPLETION` |
| `langgraph_w20` | `20` | [`...langgraph_structured_story__w20__20261126T212124Z__f93dd907`](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/P06-E01__product_education_10m_ext__langgraph_structured_story__w20__20261126T212124Z__f93dd907/) | `21:21:24 -> 21:24:06` (`161.64s`) | `EARLY_COMPLETION` |

---

## 5. Toàn bộ Transcript Thực tế (Batch 1A — Nguyên văn)

### 5.1. `script_first_upfront_llm` (`noW` — `15` turns phát, `3` safe aborts)

| Turn | Origin | Topic ID *(Mand?)* | Từ / Giây | `cited_evidence_ids` | Lời thoại nguyên văn |
|---:|---|---|---:|---|---|
| `[0]` | `PREAPPROVED_FALLBACK` | `honey-usage` *(Có)* | `16` / `6.154s` | `ev-e01-honey-shipping` | Mật ong hoa cà phê Đắk Lắk nguyên chất 500ml hiện có giá niêm yết 159.000đ. |
| `[1]` | `PROACTIVE_STORY` | `honey-safety` *(Có)* | `19` / `7.308s` | `ev-e01-ext-honey-safety`, `ev-e01-honey-usage` | Lưu ý không dùng mật ong cho trẻ dưới 1 tuổi và nhớ dùng thìa khô sạch lấy mật. |
| `[2]` | `PREAPPROVED_FALLBACK` | `honey-quality` *(Có)* | `20` / `7.692s` | `ev-e01-honey-shipping` | Mật ong hoa cà phê Đắk Lắk nguyên chất 500ml, nguồn gốc Huyện Cư M'gar, tỉnh Đắk Lắk, giá 159.000đ. |
| `[3]` | `PROACTIVE_STORY` | `honey-packaging` *(Có)* | `19` / `7.308s` | `ev-e01-ext-honey-packaging` | Chai thủy tinh 500ml nắp vặn kín ghi rõ ngày sản xuất, hạn dùng 24 tháng và mã lô. |
| `—` | `SAFE_ABORT_NO_CANDIDATE` | `honey-harvest` *(Tùy chọn)* | `—` | `—` | *(Loại bởi `OVER_MAX_DURATION_SEC` 21w/8.08s; hết 2 mẫu fallback SKU-HONEY-01)* |
| `[4]` | `PROACTIVE_STORY` | `honey-pairing` *(Tùy chọn)* | `19` / `7.308s` | `ev-e01-ext-honey-pairing` | Bạn có thể phết mật ong lên bánh mì nướng hoặc rưới lên sữa chua không đường rất ngon. |
| `[5]` | `PROACTIVE_STORY` | `tea-brewing` *(Có)* | `19` / `7.308s` | `ev-e01-tea-usage` | Pha 5g trà với nước 85-90 độ C, hãm 30-45 giây lượt đầu, bền hương 6 đến 8 nước. |
| `[6]` | `PROACTIVE_STORY` | `tea-safety` *(Có)* | `20` / `7.692s` | `ev-e01-ext-tea-safety`, `ev-e01-tea-quality` | Nên dùng muỗng khô lấy trà, không hãm nước sôi 100 độ quá lâu và tránh uống sát giờ ngủ. |
| `[7]` | `PROACTIVE_STORY` | `tea-quality` *(Có)* | `18` / `6.923s` | `ev-e01-tea-quality` | Búp trà phủ lớp lông tơ trắng mịn tự nhiên, cho nước vàng sánh và hậu ngọt sâu. |
| `[8]` | `PROACTIVE_STORY` | `tea-packaging` *(Có)* | `17` / `6.538s` | `ev-e01-ext-tea-packaging`, `ev-e01-tea-quality` | Túi hút chân không giúp trà giữ khô suốt 18 tháng, kết hợp nắp phụ đậy kín. |
| `[9]` | `PREAPPROVED_FALLBACK` | `tea-harvest` *(Tùy chọn)* | `16` / `6.154s` | `ev-e01-tea-shipping` | Trà Shan Tuyết cổ thụ Hà Giang hộp thiếc 200g hiện có giá niêm yết 245.000đ. |
| `[10]` | `PROACTIVE_STORY` | `tea-pairing` *(Tùy chọn)* | `19` / `7.308s` | `ev-e01-ext-tea-pairing` | Thưởng trà buổi sáng hoặc tiếp khách gia đình, dùng kèm bánh quy nhạt giúp cân bằng vị giác. |
| `[11]` | `PROACTIVE_STORY` | `macadamia-usage` *(Có)* | `18` / `6.923s` | `ev-e01-macadamia-usage` | Hạt mắc ca sấy nứt vỏ kèm thanh tách thép, ăn trực tiếp, làm sữa hoặc trộn salad. |
| `[12]` | `PREAPPROVED_FALLBACK` | `macadamia-safety` *(Có)* | `16` / `6.154s` | `ev-e01-macadamia-shipping` | Hạt mắc ca sấy nứt vỏ Lâm Đồng hộp 500g hiện có giá niêm yết 195.000đ. |
| `[13]` | `PREAPPROVED_FALLBACK` | `macadamia-quality` *(Có)* | `20` / `7.692s` | `ev-e01-macadamia-shipping` | Hạt mắc ca sấy nứt vỏ Lâm Đồng hộp 500g, nguồn gốc Huyện Lâm Hà, tỉnh Lâm Đồng, giá 195.000đ. |
| `—` | `SAFE_ABORT_NO_CANDIDATE` | `macadamia-packaging` *(Có)* | `—` | `—` | *(Loại bởi `OVER_MAX_DURATION_SEC` 23w/8.85s; hết 2 mẫu fallback SKU-MACADAMIA-03)* |
| `—` | `SAFE_ABORT_NO_CANDIDATE` | `macadamia-harvest` *(Tùy chọn)* | `—` | `—` | *(Loại bởi `OVER_MAX_DURATION_SEC` 24w/9.23s; hết 2 mẫu fallback SKU-MACADAMIA-03)* |
| `[14]` | `PROACTIVE_STORY` | `macadamia-pairing` *(Tùy chọn)* | `18` / `6.923s` | `ev-e01-ext-macadamia-pairing` | Hạt mắc ca phù hợp ăn vặt văn phòng, làm sữa hạt hoặc trộn yến mạch rất ngon. |

### 5.2. `langgraph_w5` (`W=5` — `18` turns phát, `0` fallback)

| Turn | Origin | Topic ID *(Mand?)* | Từ / Giây | `cited_evidence_ids` | Lời thoại nguyên văn |
|---:|---|---|---:|---|---|
| `[0]` | `PROACTIVE_STORY` *(RW×1)* | `honey-usage` *(Có)* | `14` / `5.385s` | `ev-e01-honey-usage` | Pha một đến hai thìa mật ong với 150ml nước ấm dưới 50 độ. |
| `[1]` | `PROACTIVE_STORY` | `honey-safety` *(Có)* | `16` / `6.154s` | `ev-e01-honey-usage`, `ev-e01-ext-honey-safety` | Nhớ dùng thìa khô sạch lấy mật và không dùng cho trẻ dưới một tuổi nhé. |
| `[2]` | `PROACTIVE_STORY` | `honey-quality` *(Có)* | `19` / `7.308s` | `ev-e01-honey-quality` | Mật ong không pha đường hay chất bảo quản, lạnh kết tinh nhẹ nên ngâm nước ấm 40 độ. |
| `[3]` | `PROACTIVE_STORY` *(RW×1)* | `honey-packaging` *(Có)* | `20` / `7.692s` | `ev-e01-ext-honey-packaging` | Chai thủy tinh 500ml nắp vặn kín chống tràn, ghi rõ hạn dùng 24 tháng và mã lô kiểm soát. |
| `[4]` | `PROACTIVE_STORY` | `honey-harvest` *(Tùy chọn)* | `20` / `7.692s` | `ev-e01-ext-honey-harvest` | Mật ong quay ly tâm và lọc thô nhiều tầng không gia nhiệt cao để giữ hương hoa cà phê. |
| `[5]` | `PROACTIVE_STORY` | `honey-pairing` *(Tùy chọn)* | `19` / `7.308s` | `ev-e01-ext-honey-pairing` | Bạn có thể phết mật ong lên bánh mì nướng, rưới lên sữa chua hoặc pha nước chanh ấm. |
| `[6]` | `PROACTIVE_STORY` | `tea-brewing` *(Có)* | `17` / `6.538s` | `ev-e01-tea-usage` | Tráng ấm bằng nước sôi, dùng 5g trà cho ấm 150ml với nước 85 đến 90 độ. |
| `[7]` | `PROACTIVE_STORY` *(RW×1)* | `tea-safety` *(Có)* | `16` / `6.154s` | `ev-e01-ext-tea-safety` | Dùng muỗng khô xúc trà, tránh hãm nước sôi lâu và không uống sát giờ ngủ. |
| `[8]` | `PROACTIVE_STORY` | `tea-quality` *(Có)* | `20` / `7.692s` | `ev-e01-tea-quality` | Búp trà 1 tôm 2 lá phủ lông tơ trắng mịn, cho nước vàng sánh và hương cốm ngọt sâu. |
| `[9]` | `PROACTIVE_STORY` | `tea-packaging` *(Có)* | `19` / `7.308s` | `ev-e01-ext-tea-packaging` | Túi hút chân không giúp giữ trà khô suốt 18 tháng và nắp phụ đậy kín tránh ẩm mốc. |
| `[10]` | `PROACTIVE_STORY` *(RW×1)* | `tea-harvest` *(Tùy chọn)* | `16` / `6.154s` | `ev-e01-ext-tea-harvest` | Búp hái tay héo nong tre, sao diệt men và vò nhẹ giữ nguyên tuyết trắng. |
| `[11]` | `PROACTIVE_STORY` | `tea-pairing` *(Tùy chọn)* | `17` / `6.538s` | `ev-e01-ext-tea-pairing` | Trà hợp thưởng thức buổi sáng hoặc tiếp khách phòng trà gia đình cùng bánh quy nhạt. |
| `[12]` | `PROACTIVE_STORY` | `macadamia-usage` *(Có)* | `17` / `6.538s` | `ev-e01-macadamia-usage` | Hạt sấy nứt vỏ kèm thanh thép giúp bạn ăn trực tiếp hoặc trộn salad mỗi ngày. |
| `[13]` | `PROACTIVE_STORY` | `macadamia-safety` *(Có)* | `20` / `7.692s` | `ev-e01-macadamia-usage`, `ev-e01-ext-macadamia-safety` | Xoay nhẹ thanh tách theo rãnh nứt, không ăn gói hút ẩm và tránh dùng cho người dị ứng hạt. |
| `[14]` | `PROACTIVE_STORY` | `macadamia-quality` *(Có)* | `19` / `7.308s` | `ev-e01-macadamia-quality` | Nhân trắng sữa giòn béo tự nhiên, không tẩm muối hay hương liệu và hạn sử dụng 12 tháng. |
| `[15]` | `PROACTIVE_STORY` | `macadamia-packaging` *(Có)* | `19` / `7.308s` | `ev-e01-ext-macadamia-packaging` | Hộp PET trong 500g nắp vặn kín khí giúp nhìn rõ nhân hạt và đi kèm thanh tách vỏ. |
| `[16]` | `PROACTIVE_STORY` | `macadamia-harvest` *(Tùy chọn)* | `19` / `7.308s` | `ev-e01-ext-macadamia-harvest` | Hạt được hong gió giảm ẩm rồi sấy đối lưu nhiệt độ thấp giúp nhân chín đều từ lõi. |
| `[17]` | `PROACTIVE_STORY` | `macadamia-pairing` *(Tùy chọn)* | `16` / `6.154s` | `ev-e01-ext-macadamia-pairing` | Bạn có thể ăn vặt buổi xế văn phòng hoặc giã nhỏ rắc lên yến mạch. |

*(Ghi chú kiểm tra trace `W=5`: `4` lượt rewrite gồm Turn `[0]`, Turn `[3]`, và 2 lượt trong trà `tea-safety` [Turn 7] & `tea-harvest` [Turn 10] — đều sửa thành công ngay lần `retry=1`.)*

### 5.3. `langgraph_w10` (`W=10` — `21` turns phát: `18` proactive + `3` fallback do `HTTP 503`)

| Turn | Origin | Topic ID *(Mand?)* | Từ / Giây | `cited_evidence_ids` | Lời thoại nguyên văn |
|---:|---|---|---:|---|---|
| `[0]` | `PREAPPROVED_FALLBACK` *(503)* | `honey-usage` *(Có)* | `16` / `6.154s` | `ev-e01-honey-shipping` | Mật ong hoa cà phê Đắk Lắk nguyên chất 500ml hiện có giá niêm yết 159.000đ. |
| `[1]` | `PREAPPROVED_FALLBACK` *(503)* | `honey-usage` *(Có)* | `20` / `7.692s` | `ev-e01-honey-shipping` | Mật ong hoa cà phê Đắk Lắk nguyên chất 500ml, nguồn gốc Huyện Cư M'gar, tỉnh Đắk Lắk, giá 159.000đ. |
| `[2]` | `PROACTIVE_STORY` | `honey-usage` *(Có)* | `17` / `6.538s` | `ev-e01-honey-usage` | Pha 1 đến 2 thìa cà phê mật ong với 150ml nước ấm dưới 50 độ C. |
| `[3]` | `PROACTIVE_STORY` | `honey-safety` *(Có)* | `19` / `7.308s` | `ev-e01-honey-usage`, `ev-e01-ext-honey-safety` | Lưu ý không dùng mật ong cho trẻ dưới 1 tuổi và luôn dùng thìa khô sạch lấy mật. |
| `[4]` | `PROACTIVE_STORY` | `honey-quality` *(Có)* | `19` / `7.308s` | `ev-e01-honey-quality` | Mật ong không pha đường hay chất bảo quản, lạnh kết tinh nhẹ, ngâm nước ấm 40 độ C. |
| `[5]` | `PROACTIVE_STORY` | `honey-packaging` *(Có)* | `16` / `6.154s` | `ev-e01-ext-honey-packaging` | Chai thủy tinh dày 500ml nắp vặn kín chống tràn, ghi rõ hạn dùng 24 tháng. |
| `[6]` | `PROACTIVE_STORY` *(RW×1)* | `honey-harvest` *(Tùy chọn)* | `18` / `6.923s` | `ev-e01-ext-honey-harvest` | Quay ly tâm từng đợt hoa cà phê, lọc lưới nhiều tầng không gia nhiệt cao giữ hương. |
| `[7]` | `PROACTIVE_STORY` | `honey-pairing` *(Tùy chọn)* | `19` / `7.308s` | `ev-e01-ext-honey-pairing` | Bạn có thể phết mật ong lên bánh mì nướng, rưới lên sữa chua hoặc pha cùng nước chanh. |
| `[8]` | `PROACTIVE_STORY` | `tea-brewing` *(Có)* | `18` / `6.923s` | `ev-e01-tea-usage` | Tráng ấm bằng nước sôi, dùng 5g trà cho ấm 150ml với nước 85 đến 90 độ C. |
| `[9]` | `PREAPPROVED_FALLBACK` *(503)* | `tea-safety` *(Có)* | `16` / `6.154s` | `ev-e01-tea-shipping` | Trà Shan Tuyết cổ thụ Hà Giang hộp thiếc 200g hiện có giá niêm yết 245.000đ. |
| `[10]` | `PROACTIVE_STORY` | `tea-safety` *(Có)* | `20` / `7.692s` | `ev-e01-tea-quality`, `ev-e01-ext-tea-safety` | Dùng muỗng khô xúc trà, không hãm nước sôi 100 độ C quá lâu và tránh uống sát giờ ngủ. |
| `[11]` | `PROACTIVE_STORY` *(RW×2)* | `tea-quality` *(Có)* | `19` / `7.308s` | `ev-e01-tea-quality` | Búp 1 tôm 2 lá phủ lông tơ trắng mịn, nước vàng sánh, hương cốm và hậu vị ngọt. |
| `[12]` | `PROACTIVE_STORY` | `tea-packaging` *(Có)* | `19` / `7.308s` | `ev-e01-ext-tea-packaging` | Túi hút chân không giúp giữ trà khô suốt 18 tháng và nắp phụ đậy kín tránh ẩm mốc. |
| `[13]` | `PROACTIVE_STORY` *(RW×1)* | `tea-harvest` *(Tùy chọn)* | `17` / `6.538s` | `ev-e01-ext-tea-harvest` | Búp hái tay làm héo nong tre, sao diệt men và vò nhẹ giữ nguyên tuyết trắng. |
| `[14]` | `PROACTIVE_STORY` | `tea-pairing` *(Tùy chọn)* | `16` / `6.154s` | `ev-e01-ext-tea-pairing` | Trà rất hợp thưởng thức buổi sáng tại gia đình hay dùng kèm bánh quy nhạt. |
| `[15]` | `PROACTIVE_STORY` | `macadamia-usage` *(Có)* | `18` / `6.923s` | `ev-e01-macadamia-usage` | Bạn dùng thanh thép tách vỏ sấy nứt sẵn để ăn trực tiếp hoặc trộn salad rất ngon. |
| `[16]` | `PROACTIVE_STORY` *(RW×2)* | `macadamia-safety` *(Có)* | `20` / `7.692s` | `ev-e01-macadamia-usage`, `ev-e01-ext-macadamia-safety` | Xoay nhẹ thanh tách theo rãnh nứt, giữ gói hút ẩm và tránh dùng cho người dị ứng hạt cây. |
| `[17]` | `PROACTIVE_STORY` | `macadamia-quality` *(Có)* | `19` / `7.308s` | `ev-e01-macadamia-quality` | Nhân trắng sữa giòn béo tự nhiên, không tẩm muối hay hương liệu và hạn sử dụng 12 tháng. |
| `[18]` | `PROACTIVE_STORY` | `macadamia-packaging` *(Có)* | `17` / `6.538s` | `ev-e01-ext-macadamia-packaging` | Hộp PET trong 500g nắp vặn giúp quan sát rõ từng hạt, kèm sẵn thanh tách vỏ. |
| `[19]` | `PROACTIVE_STORY` | `macadamia-harvest` *(Tùy chọn)* | `15` / `5.769s` | `ev-e01-ext-macadamia-harvest` | Hạt được hong gió giảm ẩm và sấy đối lưu chậm giúp nhân chín đều. |
| `[20]` | `PROACTIVE_STORY` | `macadamia-pairing` *(Tùy chọn)* | `19` / `7.308s` | `ev-e01-ext-macadamia-pairing` | Bạn có thể ăn vặt buổi xế văn phòng, xay làm sữa hạt hoặc giã nhỏ rắc yến mạch. |

### 5.4. `langgraph_w20` (`W=20` — `20` turns phát: `18` proactive + `2` fallback [`1` `503` + `1` cạn retry])

| Turn | Origin | Topic ID *(Mand?)* | Từ / Giây | `cited_evidence_ids` | Lời thoại nguyên văn |
|---:|---|---|---:|---|---|
| `[0]` | `PROACTIVE_STORY` *(RW×1)* | `honey-usage` *(Có)* | `14` / `5.385s` | `ev-e01-honey-usage` | Pha một đến hai thìa mật ong với 150ml nước ấm dưới 50 độ. |
| `[1]` | `PROACTIVE_STORY` | `honey-safety` *(Có)* | `16` / `6.154s` | `ev-e01-honey-usage`, `ev-e01-ext-honey-safety` | Nhớ dùng thìa khô sạch lấy mật và không dùng cho trẻ dưới một tuổi nhé. |
| `[2]` | `PROACTIVE_STORY` | `honey-quality` *(Có)* | `19` / `7.308s` | `ev-e01-honey-quality` | Mật ong không pha đường hay chất bảo quản, lạnh kết tinh nhẹ nên ngâm nước ấm 40 độ. |
| `[3]` | `PREAPPROVED_FALLBACK` *(RW×1+503)* | `honey-packaging` *(Có)* | `16` / `6.154s` | `ev-e01-honey-shipping` | Mật ong hoa cà phê Đắk Lắk nguyên chất 500ml hiện có giá niêm yết 159.000đ. |
| `[4]` | `PROACTIVE_STORY` | `honey-packaging` *(Có)* | `16` / `6.154s` | `ev-e01-ext-honey-packaging` | Chai thủy tinh dày 500ml nắp vặn kín chống tràn, ghi rõ hạn dùng 24 tháng. |
| `[5]` | `PROACTIVE_STORY` | `honey-harvest` *(Tùy chọn)* | `18` / `6.923s` | `ev-e01-ext-honey-harvest` | Mật ong quay ly tâm và lọc thô nhiều tầng không gia nhiệt cao giữ trọn hương vị. |
| `[6]` | `PROACTIVE_STORY` | `honey-pairing` *(Tùy chọn)* | `16` / `6.154s` | `ev-e01-ext-honey-pairing` | Phết mật ong lên bánh mì nướng hoặc rưới sữa chua không đường đều rất ngon. |
| `[7]` | `PROACTIVE_STORY` | `tea-brewing` *(Có)* | `18` / `6.923s` | `ev-e01-tea-usage` | Tráng ấm bằng nước sôi, dùng năm gam trà pha với nước tám lăm đến chín mươi độ. |
| `[8]` | `PROACTIVE_STORY` | `tea-safety` *(Có)* | `18` / `6.923s` | `ev-e01-tea-quality`, `ev-e01-ext-tea-safety` | Dùng muỗng khô xúc trà, tránh hãm nước sôi quá lâu và hạn chế uống sát giờ ngủ. |
| `[9]` | `PREAPPROVED_FALLBACK` *(RW×2 cạn)* | `tea-quality` *(Có)* | `16` / `6.154s` | `ev-e01-tea-shipping` | Trà Shan Tuyết cổ thụ Hà Giang hộp thiếc 200g hiện có giá niêm yết 245.000đ. |
| `[10]` | `PROACTIVE_STORY` | `tea-quality` *(Có)* | `19` / `7.308s` | `ev-e01-tea-quality` | Búp trà phủ lớp lông tơ trắng mịn, nước vàng sánh, hương cốm nhẹ và hậu vị ngọt sâu. |
| `[11]` | `PROACTIVE_STORY` *(RW×1)* | `tea-packaging` *(Có)* | `20` / `7.692s` | `ev-e01-ext-tea-packaging` | Túi hút chân không giữ trà khô suốt 18 tháng. Đậy kín nắp phụ, tránh ẩm và mùi gia vị. |
| `[12]` | `PROACTIVE_STORY` | `tea-harvest` *(Tùy chọn)* | `17` / `6.538s` | `ev-e01-ext-tea-harvest` | Búp hái tay buổi sớm được làm héo trên nong tre, sao diệt men giữ tuyết trắng. |
| `[13]` | `PROACTIVE_STORY` | `tea-pairing` *(Tùy chọn)* | `17` / `6.538s` | `ev-e01-ext-tea-pairing` | Trà thích hợp thưởng thức buổi sáng hoặc tiếp khách phòng trà, dùng kèm bánh quy nhạt. |
| `[14]` | `PROACTIVE_STORY` | `macadamia-usage` *(Có)* | `19` / `7.308s` | `ev-e01-macadamia-usage` | Mỗi hộp đều có sẵn thanh tách vỏ bằng thép, bạn dùng ăn trực tiếp hoặc trộn salad nhé. |
| `[15]` | `PROACTIVE_STORY` *(RW×2)* | `macadamia-safety` *(Có)* | `20` / `7.692s` | `ev-e01-macadamia-usage`, `ev-e01-ext-macadamia-safety` | Xoay nhẹ thanh tách theo rãnh nứt, không ăn gói hút ẩm và tránh dùng nếu dị ứng hạt cây. |
| `[16]` | `PROACTIVE_STORY` | `macadamia-quality` *(Có)* | `17` / `6.538s` | `ev-e01-macadamia-quality` | Nhân hạt màu trắng sữa giòn béo tự nhiên, hoàn toàn không tẩm muối hay hương liệu. |
| `[17]` | `PROACTIVE_STORY` | `macadamia-packaging` *(Có)* | `19` / `7.308s` | `ev-e01-ext-macadamia-packaging` | Hộp PET trong 500g nắp vặn kín giúp nhìn rõ nhân hạt và đi kèm thanh tách vỏ thép. |
| `[18]` | `PROACTIVE_STORY` | `macadamia-harvest` *(Tùy chọn)* | `17` / `6.538s` | `ev-e01-ext-macadamia-harvest` | Hạt được hong gió giảm ẩm và sấy đối lưu nhiệt độ thấp giúp nhân chín đều. |
| `[19]` | `PROACTIVE_STORY` | `macadamia-pairing` *(Tùy chọn)* | `18` / `6.923s` | `ev-e01-ext-macadamia-pairing` | Sản phẩm hợp làm món ăn vặt buổi xế văn phòng hoặc giã nhỏ rắc lên yến mạch. |

---

## 6. Bảng Đối chiếu Metrics Toàn Diện (Batch 1A — Không gộp Pilot)

> [!NOTE]
> Bảng dưới đây chỉ tổng hợp `4` lượt chạy chính thức của **Batch 1A** (`gemini-3.5-flash-lite`, `formal_experiment`, `seed=42`). Toàn bộ giá trị trích trực tiếp từ `metrics.json`, `token_usage.json`, `provider_calls.jsonl`, `graph_trace.jsonl` và `manifest.json`.

| Nhóm | Chỉ số | Ngưỡng Khóa | `Script-first (noW)` | `LangGraph W=5` | `LangGraph W=10` | `LangGraph W=20` |
|---|---|---:|---:|---:|---:|---:|
| **A. Coverage** | `mandatory_topic_coverage` (`12`) | `>= 95%` | **58.33%** (`7/12`) | **100%** (`12/12`) | **100%** (`12/12`) | **100%** (`12/12`) |
| | Tổng topic kế hoạch phủ (`18`) | — | 55.56% (`10/18`) | **100%** (`18/18`) | **100%** (`18/18`) | **100%** (`18/18`) |
| | `declared_verified_claim_coverage` (`14`) | — | 57.14% (`8/14`) | **100%** (`14/14`) | **100%** (`14/14`) | **100%** (`14/14`) |
| | `time_to_complete_mandatory_topics_sec` | — | `NOT_EVALUATED` | `110.769s` | `131.923s` | `121.154s` |
| | `semantic_topic_alignment` *(Human)* | `>= 85% FULL` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |
| **B. Repetition** | `exact_chunk_replay_count` | `0` | **0** | **0** | **0** | **0** |
| | `exact_normalized_text_replay_count` | `0` | **0** | **0** | **0** | **0** |
| | `outside_window_exact_text_replay_count` | — | `N/A` | **0** | **0** | **0** |
| | `lexical_repetition_rate` *(toàn phiên)* | `<= 5%` | **0.00%** (`0/14`) | **0.00%** (`0/17`) | **0.00%** (`0/20`) | **0.00%** (`0/19`) |
| | `max_prior_word_jaccard_mean` *(max)* | — | 0.1855 *(0.5909)* | 0.1333 *(0.2609)* | 0.1550 *(0.5417)* | **0.1261** *(0.2400)* |
| | `max_prior_ngram3_jaccard_mean` *(max)* | — | 0.0640 *(0.3077)* | **0.0037** *(0.0333)* | 0.0236 *(0.2963)* | 0.0076 *(0.1111)* |
| | `distinct_1` / `distinct_2` / `distinct_3` | — | 0.613 / 0.835 / 0.889 | **0.638 / 0.954 / 0.993** | 0.598 / 0.906 / 0.962 | 0.634 / 0.946 / 0.984 |
| | `claim_overlap_rate` | — | 20.00% (`2/10`) | 23.53% (`4/17`) | 22.22% (`4/18`) | 23.53% (`4/17`) |
| | History window max / mean / turns bị cắt | — | `N/A` | `5 / 4.17 / 12` | `10 / 7.38 / 10` | `19 / 9.50 / 0` |
| **C. Safety** | `structural_hard_gates_status` | `PASS` (`0` vi phạm) | **PASS** | **PASS** | **PASS** | **PASS** |
| | Hygiene leaks / Invalid EV / Cross-SKU | `0` | `0 / 0 / 0` | `0 / 0 / 0` | `0 / 0 / 0` | `0 / 0 / 0` |
| | `p05_rejection_count` | — | `0` | `0` | `0` | `0` |
| | `overall_gate_status` | `PASS` (hậu human) | `NOT_EVALUATED` | `NOT_EVALUATED` | `NOT_EVALUATED` | `NOT_EVALUATED` |
| **D. Reliability** | `total_requests` / `successful_candidates` | `<= 30` req | `18 / 10` | `22 / 18` | `27 / 18` | `27 / 18` |
| | `HTTP 503` / `HTTP 429` | `0` `429` | `0 / 0` | `0 / 0` | `3 / 0` | `1 / 0` |
| | `wasted_calls` **tổng** (`% total calls`) | — | **44.44%** (`8/18`) | **18.18%** (`4/22`) | 33.33% (`9/27`) | 33.33% (`9/27`) |
| | `wasted_calls` **do logic** (`% total` / `% non-503`) | `<= 10%` | **44.44% / 44.44%** | **18.18% / 18.18%** | **22.22% / 25.00%** | **29.63% / 30.77%** |
| | `rewrite_rate` **tổng** / **do logic** | `<= 15%` | `0.00% / 0.00%` | `22.22% / 22.22%` | `19.05% / 19.05%` | `25.00% / 25.00%` |
| | `fallback_rate` **tổng** / **do logic** | `<= 5%` | `27.78% / 27.78%` | **`0.00% / 0.00%`** | `14.29%` / **`0.00%`** | `10.00%` / `5.00%` |
| | `safe_abort_count` (`rate`) | — | `3` (`16.67%`) | **`0`** (`0.00%`) | **`0`** (`0.00%`) | **`0`** (`0.00%`) |
| **E. Perf/Tokens** | `provider_latency_p50_ms` *(gồm pacing 6s)* | `<= 7,000 ms` | `5,967.2 ms` | **`5,953.2 ms`** | `5,999.3 ms` | `5,958.1 ms` |
| | `provider_latency_p95_ms` *(gồm pacing 6s)* | `<= 10,000 ms` | **`6,238.7 ms`** | `7,387.2 ms` | `8,141.4 ms` | `6,794.5 ms` |
| | `invocation_latency_p50 / p95` | — | `5,936.9 / 6,012.2 ms` | `6,135.8 / 12,048.1 ms` | `6,271.0 / 17,630.0 ms` | `6,131.7 / 18,208.3 ms` |
| | `total_measured_processing_ms` / Wall-clock | — | `103.53s` / `103.53s` | `131.31s` / `131.31s` | `162.70s` / `162.70s` | `161.64s` / `161.64s` |
| | `time_to_first_candidate` *(tổng lat. tới proactive đầu)* | — | `103,394 ms` *(upfront)* | **`11,255.4 ms`** *(c0+c1)* | `18,052.4 ms` *(2×503+c2)* | `11,580.7 ms` *(c0+c1)* |
| | Token source & `measured_calls` | — | `MEASURED` (`18/18`) | `MEASURED` (`22/22`) | `PARTIAL` (`24/27`) | `PARTIAL` (`26/27`) |
| | `input_tokens` / `output_tokens` *(đo được)* | — | `38,845 / 3,325` | `65,225 / 2,631` | `80,689 / 3,002` *(partial)* | `90,419 / 3,110` *(partial)* |
| | `thinking_tokens` *(provider)* | — | `UNAVAILABLE` *(null)* | `UNAVAILABLE` *(null)* | `UNAVAILABLE` *(null)* | `UNAVAILABLE` *(null)* |
| | `tokens_per_accepted_proactive_chunk` | — | `4,217.0` | **`3,769.8`** | `4,649.5` *(partial)* | `5,196.1` *(partial)* |
| | `requests_per_completed_topic` (`18` / `12` mand) | — | `1.80 / 2.57` | **`1.22 / 1.83`** | `1.50 / 2.25` | `1.50 / 2.25` |
| **F. Duration** | `simulated_played_duration_sec` / `600s` | — | `105.385s` (`17.56%`) | `124.231s` (`20.71%`) | `145.000s` (`24.17%`) | `134.615s` (`22.44%`) |
| | `played_chunks_count` | — | `15` | `18` | `21` | `20` |
| | `termination_reason` | — | `CONTENT_EXHAUSTED` | `EARLY_COMPLETION` | `EARLY_COMPLETION` | `EARLY_COMPLETION` |

---

## 7. Phân tích Kể chuyện & Độ phủ Ngữ nghĩa (`RQ1`)

### 7.1. So sánh Độ phủ & Khả năng Phục hồi
Trên `product_education_10m_ext`, dữ liệu chứng minh cơ chế phản hồi tuần tự của **LangGraph vượt trội rõ rệt so với Script-first** về độ tin cậy hoàn thành kế hoạch:
- **`Script-first` thất bại ở `8/18` chủ đề (`44.44%`)** không phải do bịa hay P05 từ chối, mà vì sinh vượt `20` từ (`21–24` từ) ở lần gọi duy nhất (`max_retries=0`). Do mỗi SKU chỉ có tối đa `2` mẫu fallback hợp lệ, `SKU-HONEY-01` và `SKU-MACADAMIA-03` bị cạn fallback khi có tới `3–4` chủ đề lỗi cùng một SKU, dẫn tới `3` lượt `SAFE_ABORT_NO_CANDIDATE` (gồm cả `topic-ext-edu-macadamia-packaging` là chủ đề bắt buộc!).
- **`LangGraph`** dù cũng gặp tỷ lệ vượt `20` từ ở lần nháp đầu tương đương (`4–5/18` topics = `22%–28%`), nhưng đã dùng `bounded_rewrite` để rút gọn còn `14–20` từ và hoàn thành `100%` toàn bộ `18` chủ đề ở cả 3 giá trị `W`.

### 7.2. Mạch kể, Tính tự nhiên & Chuyển tiếp (Trả lời sơ bộ RQ1)
- **Điểm yếu chuyển tiếp giữa các lượt từ Pilot v2 vẫn còn hiện diện:** Do `story_generation.txt` sinh từng chunk độc lập dưới `20` từ và tập trung hoàn toàn vào thông tin sản phẩm của topic hiện tại, giữa hai chủ đề kế tiếp hoặc khi chuyển từ `SKU-HONEY-01 -> SKU-TEA-02 -> SKU-MACADAMIA-03` **vẫn chưa có câu nối chuyển ý/chuyển sản phẩm tự nhiên** (ví dụ từ `honey-pairing` sang `tea-brewing` lập tức nhảy vào `"Tráng ấm bằng nước sôi..."`). Các câu fallback khi gặp `HTTP 503` (như `W=10` Turn `[0]`, `[1]` đọc giá 2 lần trước khi Turn `[2]` mới hướng dẫn pha mật ong) cũng làm đứt mạch tự nhiên — đây là đánh đổi an toàn bắt buộc của cơ chế fail-closed.
- **Đánh đổi giữa trần `20` từ và độ đầy đủ ngữ nghĩa (`PARTIAL` vs `FULL`):** Kiểm tra định tính sơ bộ của nhóm nghiên cứu *(chưa phải `GoldFactualLabel`)* cho thấy để nén 2 `talking_points` vào `<= 20` từ, mô hình thỉnh thoảng lược bớt vế phụ: ví dụ `honey-packaging` ở `W=10 [5]` & `W=20 [4]` bỏ `"ngày sản xuất"` và `"mã lô"`; `macadamia-usage` ở cả 4 cấu hình bỏ `"xay sữa hạt"` (chuyển hoặc chỉ nhắc lại ở `macadamia-pairing`); `macadamia-pairing` ở `W=5 [17]` và `W=20 [19]` bỏ `"làm sữa hạt"`; `W=5 [0],[6]` & `W=20 [0]` lược chữ `"C"` sau `"50 độ"`, `"85 đến 90 độ"`. Tổng thể nhận định sơ bộ cho thấy LangGraph giữ được tính liên tục cao hơn hẳn Script-first vì không có khoảng trống fallback/abort chen ngang, nhưng đánh giá chính thức về `narrative_coherence`, `naturalness`, `transition_quality` và tỷ lệ `FULL/PARTIAL/MISS` phải chờ kết quả chấm mù của con người.

---

## 8. Phân tích An toàn, Bằng chứng & Tính Đúng Sự thật (`Hard Gates`)

Kiểm toán toàn bộ `74` lượt phát thực tế (`15 + 18 + 21 + 20`) đối chiếu với [`e01_ext_v1_verified_skus.json`](../data/products/e01_ext_v1_verified_skus.json) `v1.0.1`:

1. **Structural Hard Gates (`0` vi phạm):**
   - `Metadata Leakage`: **`0`** (`check_spoken_text_hygiene()` pass `74/74` lượt, không có `ev-*`, `clm-*`, `SKU-*`, `topic-*`, JSON).
   - `Unauthorized Completed Chunk Replay`: **`0`** trên cả 4 runs.
   - `Retry Budget Violation`: **`0`** (`retries_used <= 2` ở LangGraph, `0` ở Script-first).
   - `Coverage Update Without Valid PlaybackCompleted ACK`: **`0`** (`cross_check_consistent = True`; các lượt `PREAPPROVED_FALLBACK` hoàn toàn không làm tăng `completed_topic_ids`).
   - `Unauthorized SKU/StoryPlan Modification`: **`0`**.
2. **Evidence Attribution & Cross-SKU (`0` vi phạm kỹ thuật):**
   - `100%` lượt `PROACTIVE_STORY` (`64/64`) đều gắn `cited_evidence_ids` hợp lệ tồn tại trong `v1.0.1` và khớp đúng `sku_id` của lượt đó (`0` cross-SKU). Toàn bộ `10` lượt `PREAPPROVED_FALLBACK` đều trích đúng `ev-*-shipping` của đúng SKU và nêu đúng giá niêm yết (`159.000đ`, `245.000đ`, `195.000đ`).
3. **Kiểm toán Factual, Causal Inference, Policy Conditions & Evidence Support *(Sơ bộ — chờ Human Gold Label)*:**
   - **Prohibited claims / sai giá / sai khối lượng / sai HSD:** **`0`** phát hiện sai con số ở cả `74` lượt.
   - **Commercial Policy Conditions:** `0` vi phạm (vì kịch bản `product_education_10m_ext` không có chủ đề đổi trả nên không có lượt `PROACTIVE_STORY` nào nhắc chính sách đổi trả bị thiếu điều kiện).
   - **Unsupported Causal Inference:** `0` lỗi bịa nhân quả rõ rệt (các cụm `"không gia nhiệt cao để giữ hương"`, `"sấy đối lưu nhiệt độ thấp giúp nhân chín đều từ lõi"` bám sát trực tiếp `ev-e01-ext-honey-harvest` và `ev-e01-ext-macadamia-harvest`).
   - **Hai điểm cần reviewer chú ý đặc biệt ở Bước 2:**
     - **`W=10` Turn `[16]` (`topic-ext-edu-macadamia-safety`):** Lời thoại sinh ra là *"Xoay nhẹ thanh tách theo rãnh nứt, **giữ gói hút ẩm** và tránh dùng cho người dị ứng hạt cây."* Trong khi `talking_points` và `ev-e01-ext-macadamia-safety` yêu cầu cảnh báo **"không ăn gói hút ẩm"** (còn `"giữ gói hút ẩm"` là từ `mandatory_messages`/`storage_instructions`). Câu này không sai sự thật về bảo quản, nhưng **làm mất cảnh báo an toàn `"không ăn gói hút ẩm"`** của chủ đề mục tiêu (ít nhất là `PARTIAL` về semantic alignment, và `evidence_support` chỉ theo `ev-e01-macadamia-usage` + `ev-e01-ext-macadamia-safety` sẽ không có chữ `"giữ gói hút ẩm"`, mà chữ đó nằm ở `ev-e01-macadamia-quality`).
     - **`W=5` Turn `[15]` (`topic-ext-edu-macadamia-packaging`):** Dùng cụm `"nắp vặn kín khí"` khi chỉ trích `ev-e01-ext-macadamia-packaging` (tài liệu này ghi `"nắp vặn chắc chắn"`, còn cụm `"nắp vặn kín khí"` nằm ở `ev-e01-macadamia-shipping` và trong `talking_points` của topic). Điều này minh họa đúng nguyên tắc **P05 ALLOW ≠ chứng minh `evidence_support` 100%** ở mức câu chữ.

---

## 9. Phân tích Chống lặp & Độ nhạy Cửa sổ Lịch sử (`RQ3`)

Để so sánh công bằng `W=5 / 10 / 20` và `Script-first`, toàn bộ chỉ số lặp được tính trên **cùng một evaluation horizon là toàn bộ transcript đã phát** (không dùng riêng cửa sổ nội bộ từng run):

- **Không xuất hiện lặp bề mặt đáng kể ở bất kỳ cấu hình nào trên Track 1:**
  - `exact_normalized_text_replay_count = 0` trên cả `4/4` runs.
  - `lexical_repetition_rate = 0.00%` trên cả `4/4` runs (`< 5%` threshold).
  - Trong `graph_trace.jsonl`, **`0` lượt nào kích hoạt `RepetitionDetector` reject/rewrite** trên cả `W=5`, `W=10`, và `W=20`! (Tất cả `15` lượt rewrite thêm across `W=5/10/20` đều do `OVER_MAX_DURATION_SEC`, không có lượt nào do trùng lặp).
- **Mức độ sử dụng cửa sổ bộ nhớ (`History Window Utilization`):**
  - `W=5` (`18` turns): tối đa `5` lượt nhớ gần nhất, trung bình `4.17` lượt, `12/18` turns có lịch sử bị cắt đuôi.
  - `W=10` (`21` turns): tối đa `10` lượt nhớ gần nhất, trung bình `7.38` lượt, `10/21` turns có lịch sử bị cắt đuôi.
  - `W=20` (`20` turns): tối đa **`19` lượt nhớ**, trung bình `9.50` lượt, **`0/20` turns bị cắt đuôi** (vì tổng số turns `< 20`).
- **Trả lời RQ3 trên Batch 1A:**
  - Các khác biệt nhỏ về `max_prior_ngram3_jaccard_mean` (`W=5: 0.0037`, `W=20: 0.0076`, `W=10: 0.0236`, `Script-first: 0.0640`) **không phải do hiệu ứng bộ nhớ `W` dài hơn tốt hơn**. Cụ thể, giá trị `0.0236` và `max_prior_word_jaccard_max = 0.5417` của `W=10` (và `0.0640` / `0.5909` của `Script-first`) đến từ việc **các lượt `PREAPPROVED_FALLBACK` lặp cấu trúc/từ khóa tên sản phẩm và `"hiện có giá niêm yết ..."`** (trên `W=10` Turn `[0]` và `[1]` là 2 fallback liên tiếp cùng `SKU-HONEY-01` do 2 lỗi `HTTP 503`, nên chỉ trong 1 bước đã có `Word Jaccard = 0.5417`!). Khi loại các fallback từ lỗi 503, khác biệt tự nhiên giữa `W=5`, `W=10` và `W=20` là nhiễu ngẫu nhiên của LLM trên `18` chủ đề phân biệt (`n=1`).
  - Cần phân biệt **đa dạng từ vựng (`Distinct-n`) với đa dạng ngữ nghĩa**: `W=5` đạt `Distinct-3 = 0.993` rất cao chủ yếu vì mỗi lượt nói về một khía cạnh khác nhau của `StoryPlan` (`usage`, `safety`, `quality`, `packaging`, `harvest`, `pairing`), chứ chưa phải chứng minh `W=5` kiểm soát lặp ngữ nghĩa tốt hơn `W=10/20` khi kịch bản quay lại cùng chủ đề.
  - **Kết luận cho RQ3:** **Không rút ra `W` tối ưu từ Batch 1A.** **Track 2 (`lag=6/8` và `lag=12` với `min_chunks_per_topic=2`) vẫn bắt buộc** để kích hoạt xung đột trí nhớ thật sự.

---

## 10. Thời lượng Phiên & Hành vi Kết thúc (`Duration Fulfillment`)

| Cấu hình | Target (`s`) | Simulated Played (`s`) | Fulfillment | Played Chunks | Termination | Nguyên nhân Dừng |
|---|---:|---:|---:|---:|---|---|
| `script_first_upfront_llm` | `600.0` | `105.385` | `17.56%` | `15` | `CONTENT_EXHAUSTED` | Đi hết 18 topics nhưng 3 topic bị abort (`0` chunk) & 5 topic chỉ phát fallback ngắn -> thiếu 5/12 mandatory |
| `langgraph_w5` | `600.0` | `124.231` | `20.71%` | `18` | `EARLY_COMPLETION` | Phủ đủ 12/12 mandatory + 6 optional tại `124.23s` rồi dừng sạch |
| `langgraph_w10` | `600.0` | `145.000` | `24.17%` | `21` | `EARLY_COMPLETION` | Phủ đủ 18/18 topics (`+3` chunk fallback do 503 đẩy thời lượng lên `145s`) |
| `langgraph_w20` | `600.0` | `134.615` | `22.44%` | `20` | `EARLY_COMPLETION` | Phủ đủ 18/18 topics (`+2` chunk fallback đẩy thời lượng lên `134.6s`) |

- **Giải thích trung thực giới hạn `10–30` phút (`E01`):** Mục tiêu nghiên cứu gốc của E01 là livestream `10–30` phút (`600–1800s`) không bình luận trên 3 SKU. Trong Batch 1A, độ dài trung bình mỗi chunk chấp nhận là `6.73s–7.03s` (`17.5–18.3` từ ở tốc độ mô phỏng `2.6` từ/giây), nên `18` chủ đề (`m=1`) chỉ tạo ra tối đa `~2.1` phút nội dung (`20.71%` mục tiêu `10` phút).
- Hệ thống **không** ép AI sinh fluff, bịa chi tiết ngoài catalog hoặc lặp lại fact chỉ để kéo dài thời gian. Do đó, **Batch 1A chứng minh khả năng phủ `100%` `StoryPlan` trong `2` phút, KHÔNG chứng minh được khả năng duy trì storytelling liên tục `10` phút** với dung lượng tri thức hiện có. Ngoài ra, toàn bộ thời lượng trên là **mô phỏng từ độ dài từ (`VirtualClock`)**, khác với thời lượng audio TTS (`P02`) và lip-sync (`P03`) thật.

---

## 11. Độ trễ, Token & Hiệu quả Tài nguyên (`RQ2` / `RQ5`)

Phân tích theo `research/research_questions.md` (`RQ5`) và các trục đánh đổi hiệu năng/chi phí/độ ổn định (`RQ2` trong chỉ dẫn Batch 1A):

1. **Khả năng sinh candidate hợp lệ & tỷ lệ rewrite/wasted calls do logic:**
   - Tỷ lệ chủ đề đạt ngay ở lượt sinh đầu không cần rewrite/fallback: `Script-first = 10/18 (55.56%)`, `LangGraph W=5 = 14/18 (77.78%)`, `W=10 = 14/18 (77.78%)`, `W=20 = 13/18 (72.22%)` *(tính theo số lượt chạy thực tế ở lần thử `attempt 0`: `W=5` đạt `14/18 = 77.78%`, `W=10` đạt `14/21 = 66.67%` gồm `3` lượt `HTTP 503` hoặc `14/18 = 77.78%` trên lượt non-503, và `W=20` đạt `15/20 = 75.00%` vì lượt `4` và `11` chạy lại sau fallback đã đạt ngay ở `attempt 0`)*.
   - **So với ngưỡng khóa `<= 15%` logic rewrite và `<= 10%` logic wasted calls:** Cả `3` cấu hình LangGraph đều **vượt ngưỡng mục tiêu** (`logic rewrite_rate = 19.05%–25.00%`, `logic wasted_calls = 18.18%–30.77%`), hoàn toàn do lỗi `OVER_MAX_DURATION_SEC` (`21–25` từ vs trần `20` từ). Đáng chú ý, trên `W=20`, riêng `topic-ext-edu-tea-quality` ở `turn 10` tốn tới `3` calls (`22 -> 21 -> 21` từ) mà vẫn vượt 1 từ rồi rơi vào fallback logic (`1/20 = 5.00%` lượt non-boundary; sau đó `turn 11` sinh lại đạt ngay). Ngược lại, `P05` không từ chối lượt nào (`p05_rejection_rate = 0.00%`).
2. **Độ trễ (`Provider Latency` vs `Invocation Latency` vs `Time-to-First-Candidate`):**
   - `Provider Latency` P50 ở cả 4 cấu hình rất đồng đều (`5,953–5,999 ms`, P95 `6,238.7–8,141.4 ms`, đạt ngưỡng tham chiếu `<= 7,000 ms` / `<= 10,000 ms`). Tuy nhiên, kiểm tra mã nguồn [`gemini_provider.py`](../src/p06/providers/gemini_provider.py) xác nhận `generate_structured()` bắt đầu bấm `time.perf_counter()` **trước** khi gọi `GeminiRestClient.generate_json()`, tức là **`provider_latency_ms` đã bao gồm thời gian ngủ điều tiết phía client (`min_request_interval_sec = 6.0s`)**. Khi không chịu ngủ điều tiết (call đầu tiên hoặc ngay sau một call kéo dài `> 6.0s`, ví dụ `script_first c0 = 1,919.2 ms`, `w5 c19 = 2,194.5 ms`, `w10 c4 = 2,363.2 ms`, `w10 c11 = 2,524.1 ms`, `w20 c4 = 3,554.3 ms`), độ trễ HTTP thực tế chỉ khoảng **`1.92s–3.55s`**. Cụm P50 quanh `~5.96s` chủ yếu phản ánh ngưỡng giãn nhịp Free Tier `6.0s` chứ không phải thời gian xử lý thuần của máy chủ Gemini.
   - Khi cộng thêm `1–2` vòng rewrite (mỗi vòng kèm pacing `6.0s`), **`Invocation Latency` P95 của LangGraph tăng lên `12.05s` (`W=5`) – `18.21s` (`W=20`)**.
   - Về **thời gian ra candidate đầu tiên (`Time-to-First-Candidate`)**: `Script-first` mất **`103.39s` (`1.72` phút)** vì phải sinh xong toàn bộ `18` lượt trước khi phát lượt `[0]`; trong khi `LangGraph W=5` và `W=20` chỉ mất **`11.26s`** / **`11.58s`** tổng `provider_latency` (`c0+c1`, do lượt `[0]` phải rewrite 1 lần vì dài `21` từ; ~`11.8s–12.0s` nếu tính đủ nhịp giãn `6.0s`), còn `W=10` mất **`18.05s`** tổng `provider_latency` (`c0+c1+c2`) để có proactive chunk đầu tiên (nhưng đã phát được câu fallback an toàn ngay sau lượt `503` đầu tiên ở giây `~5.64s`).
3. **Sử dụng Token (`MEASURED` vs `PARTIAL` vs `UNAVAILABLE`):**
   - **Tính trung thực của số liệu token:** `Script-first` (`18/18` calls) và `LangGraph W=5` (`22/22` calls) có `token_usage_source = MEASURED`. `LangGraph W=10` (`24/27` calls, thiếu `c0, c1, c10` do `503`) và `W=20` (`26/27` calls, thiếu `c5` do `503`) có tổng hợp ở trạng thái **`UNAVAILABLE`** trong `token_usage.json`, và chỉ báo cáo **`PARTIAL MEASURED`** trên các call thành công.
   - **`thinking_tokens`:** Gemini 3.5 Flash-Lite (`thinking_level: MINIMAL`) **không trả về trường `thoughtsTokenCount`** trong `usageMetadata` trên bất kỳ call nào (`0/94` non-null). Do đó, báo cáo ghi nhận `thinking_tokens` là **`UNAVAILABLE` từ provider** (khắc phục cách cộng mặc định `0` trong `token_usage.json` của `w5`/`script_first`).
   - **Chi phí prompt tăng theo `W`:** Input token trung bình mỗi call tăng đều theo kích thước lịch sử đưa vào prompt: `~2,158` in/call (`Script-first`, không history) -> `~2,965` (`W=5`) -> `~3,362` (`W=10`) -> `~3,478` (`W=20`). Nhờ hoàn thành nhiều topic hơn và ít wasted calls hơn `W=10/20`, **`LangGraph W=5` đạt hiệu suất token tốt nhất trong 4 cấu hình: `3,769.8` tokens / accepted proactive chunk** (so với `4,217.0` của Script-first, `4,649.5` partial của `W=10` và `5,196.1` partial của `W=20`), đồng thời tốn ít request nhất trên mỗi chủ đề hoàn tất (`1.22` req/topic).
   - Lưu ý tách bạch: tổng thời gian xử lý (`103.5s–162.7s`) là thời gian wall-clock chạy API tuần tự có pacing `6.0s`, **không** phải thời lượng phát livestream.

---

## 12. Phân tích Lỗi & Sổ cái Ngân sách (`Failure Analysis & Budget Ledger`)

### 12.1. Phân loại 5 Nhóm Lỗi Toàn Batch (`94` calls)

| Nhóm Nguyên nhân | `Script-first` | `LangGraph W=5` | `LangGraph W=10` | `LangGraph W=20` | Chi tiết Thực nghiệm |
|---|---:|---:|---:|---:|---|
| **1. Provider / Infrastructure (`HTTP 503`)** | `0` | `0` | **`3`** *(c0, c1, c10)* | **`1`** *(c5)* | Lỗi `503 UNAVAILABLE` phía Google AI Studio (`high demand`); LangGraph fallback an toàn không mất topic. |
| **2. Agent Logic Failures** | `0` | `0` | `0` | `0` | `0` retry budget violation, `0` lỗi định tuyến/lặp vô hạn, `0` sai trạng thái ACK. |
| **3. Prompt / Generation (`OVER_MAX_DURATION_SEC`)** | **`8`** *(44.4%)* | **`4`** *(18.2%)* | **`6`** *(22.2%)* | **`8`** *(29.6%)* | Toàn bộ `26` call bị loại do thuật toán/prompt đều là sinh `21–25` từ (> trần `20` từ / `8.0s`). `0` lỗi JSON schema. |
| **4. Evidence / Safety Failures** | `0` | `0` | `0` | `0` | `0` lỗi `P05` rejection, `0` lỗi hygiene, `0` lỗi missing evidence attribution. |
| **5. Budget-related Termination** | `0` | `0` | `0` | `0` | `0` run bị cắt do hết cap `30` req/run hoặc `120` req toàn batch; `0` `HTTP 429`. |

### 12.2. Đối soát Sổ cái Ngân sách (`budget_ledger.json`)

| Thứ tự | Cấu hình | Requests Attempted | Cumulative | Cap Run / Global | Rate Limited | Chi phí (USD) |
|---:|---|---:|---:|---:|:---:|---:|
| 1 | `script_first_upfront_llm` | `18` | `18` | `30 / 120` | `False` | `0.00` |
| 2 | `langgraph_w5` | `22` | `40` | `30 / 120` | `False` | `0.00` |
| 3 | `langgraph_w10` | `27` | `67` | `30 / 120` | `False` | `0.00` |
| 4 | `langgraph_w20` | `27` | **`94`** | `30 / 120` | `False` | **`0.00`** |

Ngân sách dư sau Batch 1A (`26` requests) **không** được tự động sử dụng cho batch khác.

---

## 13. Mức Sẵn sàng Đánh giá Con người (`Human Evaluation Readiness`)

Bộ hồ sơ chấm mù cho `4` mẫu thật của Batch 1A (`SAMPLE_001`–`SAMPLE_004` tương ứng `METHOD_A`–`METHOD_D`) đã được xuất và kiểm tra sạch `100%` tại [`runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/human_eval/`](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/human_eval/):

1. [`blind_eval_sheet.csv`](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/human_eval/blind_eval_sheet.csv) & [`blind_eval_sheet.jsonl`](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/human_eval/blind_eval_sheet.jsonl): `4` mẫu thật Batch 1A đã xáo trộn theo `seed=42`, toàn bộ cột điểm để trống, `0` rò rỉ `method`, `model_id`, `W` hay `run_id`.
2. [`factual_and_semantic_review_sheet.csv`](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/human_eval/factual_and_semantic_review_sheet.csv): `77` dòng đánh giá (`SAMPLE_001=20`, `SAMPLE_002=21`, `SAMPLE_003=18` gồm `15` lượt phát + `3` dòng `MISSING_TOPIC`, `SAMPLE_004=18`), toàn bộ 5 cột chấm điểm và `GoldFactualLabel` để trống hoàn toàn.
3. [`blind_key_mapping.private.json`](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/human_eval/blind_key_mapping.private.json): Khóa giải mã tách riêng.
4. [`REVIEWER_GUIDE_BLIND_QUALITY.md`](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/human_eval/REVIEWER_GUIDE_BLIND_QUALITY.md): Hướng dẫn Bước 1 (Rubric `v0.1` 6 tiêu chí, quy tắc không bù trừ, 4 bản transcript ẩn danh).
5. [`REVIEWER_GUIDE_FACTUAL_AND_SEMANTIC_AUDIT.md`](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/human_eval/REVIEWER_GUIDE_FACTUAL_AND_SEMANTIC_AUDIT.md): Hướng dẫn Bước 2 (đầy đủ `ProductFact`, `30` `EvidenceChunk` `v1.0.1`, `expected_talking_points`, `cited_evidence_ids`, quy tắc chấm `MISSING_TOPIC` và điều kiện chính sách).

**Trạng thái hiện tại:** **`PENDING HUMAN BLIND EVALUATION & GOLD FACTUAL ASSESSMENT`**.

---

## 14. Các Giới hạn Nghiên cứu Còn lại

1. **Cỡ mẫu `n=1` (`seed=42`) & tính bất định của Cloud API:** Batch 1A chỉ có `1` lượt mỗi cấu hình trên `1` kịch bản (`product_education_10m_ext`). Với `n=1` và xác suất `HTTP 503` ngẫu nhiên (`3` lần ở `W=10`, `1` lần ở `W=20`, `0` lần ở `W=5`/`Script-first`), không thể tuyên bố ý nghĩa thống kê hay kết luận quan hệ nhân quả cho các khác biệt nhỏ giữa `W=5/10/20`.
2. **Trần `20` từ / `8.0s` và hiện tượng vượt độ dài lượt đầu:** `22%–44%` lượt sinh đầu tiên trên `gemini-3.5-flash-lite` vượt `20` từ, làm tăng `wasted_calls` lên `18.18%–30.77%` và khiến `Invocation Latency P95` đạt `12–18s`.
3. **Không đạt thời lượng `10–30` phút trên 3 SKU (`17.6%–24.2%` của 600s):** Do giới hạn thực tế của `18` chủ đề không bình luận và tốc độ đọc mô phỏng `2.6` từ/giây.
4. **P05 chưa kiểm tra suy diễn ngữ nghĩa (NLI/Entailment):** P05 chỉ kiểm tra ID tồn tại, giá, từ cấm và hygiene; việc câu nói có đánh rơi ý chính/cảnh báo an toàn (như `W=10 [16]` đổi `"không ăn gói hút ẩm"` thành `"giữ gói hút ẩm"`) hay suy diễn ngoài `cited_evidence_ids` vẫn phụ thuộc hoàn toàn vào Bước 2 Human Audit.
5. **Chưa có audio TTS (`P02`) / lip-sync (`P03`) thật:** Thời lượng nói là mô phỏng tuyến tính `words / 2.6`, chưa phản ánh tốc độ phát âm tiếng Việt thật hoặc độ trễ pipeline media.
6. **Chưa chứng minh được độ nhạy cửa sổ `W=5/10/20`:** Do Track 1 không có lặp chủ đề bắt buộc và chỉ dài `18–20` lượt (`W=20` chưa bao giờ đầy).
7. **Chưa có Human Blind Ratings:** Kết luận chất lượng mềm và `overall_gate_status` vẫn chưa đóng.

---

## 15. Đề xuất cho Các Thí nghiệm Còn lại của `P06-E01` & Kế hoạch Tổng hợp

Dựa trực tiếp trên bằng chứng Batch 1A *(với mục tiêu tối ưu hóa ngân sách thực nghiệm vừa đủ, tránh chạy toàn bộ `710` requests máy móc)*:

### 15.1. Trả lời Các Câu hỏi Thiết kế Batch Tiếp theo
1. **Có cần chạy `product_education_10m_ext` với `seed=43` không?**  
   **Khuyến nghị: `CÓ` (hoặc chạy rút gọn `Script-first` + `LangGraph W=5`), ưu tiên trung bình.** Batch 1A đã cho thấy sự sụp đổ rõ của `Script-first` (`58.33%`) so với `LangGraph` (`100%`), nhưng do `W=10` chịu `3` lỗi `HTTP 503` còn `W=5` chịu `0` lỗi, một lần lặp `seed=43` giúp kiểm chứng độ ổn định của `LangGraph` trước nhiễu `503` và tỷ lệ vượt `20` từ (`~22%`). Nếu ngân sách RPD eo hẹp, có thể ưu tiên `Brand Storytelling` + `Track 2` trước, hoặc chỉ chạy `seed=43` cho `Script-first` + `LangGraph W=10` (`~45` req).
2. **Có cần chạy `brand_storytelling_10m_ext` (`Batch 1B`) không?**  
   **Khuyến nghị: `CÓ — ƯU TIÊN CAO` (phạm vi gọn `2` hoặc `4` cấu hình, `seed=42`).** Lý do quan trọng: `product_education_10m_ext` **không có chủ đề chính sách đổi trả và chứng nhận OCOP**, nên Batch 1A chưa kiểm nghiệm trực tiếp được Targeted Safety Review **A** (giữ nguyên điều kiện `"khi nhận hàng kèm video mở hộp"` / `"khi mở hộp"` khi nén `<= 20` từ) và **B** (câu chuyện vùng nguyên liệu/chế biến không suy diễn nhân quả). `brand_storytelling_10m_ext` là kịch bản duy nhất trong `e01_ext_v1` kiểm chứng trực tiếp các rủi ro an toàn thương mại và OCOP này.
3. **Phạm vi tối thiểu cho Track 2 — History Window Stress Test (`RQ3`):**  
   - **Chọn kịch bản nào?** Chọn **`window_stress_12lag_3sku` (`lag=12`, `e01_formal_v1`, `36` topics × `min_chunks_per_topic=2` = `72` base turns)** vì chỉ `lag=12` mới thỏa đồng thời `W=5 < 12`, `W=10 < 12` và `W=20 >= 12`, trong khi `lag=6/8` không tách được `W=10` với `W=20`. (Hoặc chạy thêm 1 run `lag=6` chỉ nếu muốn đối chứng độ dốc khi `W=10, 20 > lag=6`, nhưng tối thiểu chỉ cần `lag=12` để phân biệt cả 3 giá trị `W`.)
   - **Công bằng tham số:** Cố định **cùng `max_turns` (vd `120`) và cùng `max_requests_per_run`** cho cả `W=5`, `W=10`, `W=20` (không đặt trần riêng cho từng `W` làm thiên lệch số topic hoàn thành).
   - **Ngân sách thực tế cho `W` trên Track 2:** Đề xuất cũ `220` requests cho `W=10 + W=20` là **chưa đủ căn cứ** vì Mock validation trước đó đã tốn tới `258` calls (`102` cho `W=10` + `156` cho `W=20`), chưa kể trên Gemini thật tỷ lệ vượt `20` từ còn thêm `~20%–25%` rewrite calls! Do đó, khuyến nghị chia Track 2 thành **các run độc lập** hoặc 2 ngày: `Script-first` (`cap 80`), `W=5` (`cap 110`), `W=10` (`cap 120`), và `W=20` (`cap 160`, chuẩn bị tinh thần `W=20` có thể chạm `MAX_CONSECUTIVE_ABORTS` ở SKU thứ 3 do `REPEATED_FACTS` khi `lag=12 < 20`).
4. **Có cần Track 3 (`Extended 30m` — `sales_presentation_30m_ext`) không?**  
   **Khuyến nghị: `HOÃN / KHÔNG CẦN THIẾT` cho E01 hiện tại.** Lý do: `sales_presentation_30m_ext` chỉ có `24` topics (`~2.4` phút thực tế), vẫn không đạt được `30` phút với `m=1`, không giải quyết thêm câu hỏi nghiên cứu mới nào ngoài `Brand Storytelling` + `Track 2 lag=12`. Chỉ nên xem xét Track 3 nếu mở rộng bài toán hoặc còn dư RPD sau khi hoàn tất Track 1 (`Brand`) và Track 2 (`lag=12`).
5. **Bằng chứng còn thiếu để đóng `P06-E01`:**
   - (a) **Human Blind Evaluation + Gold Factual Labels** trên Batch 1A (`human_eval/`) và các batch tiếp theo để chuyển `overall_gate_status` khỏi `NOT_EVALUATED`.
   - (b) **Batch 1B (`brand_storytelling_10m_ext`)** để kiểm chứng điều kiện chính sách đổi trả, OCOP mô phỏng và suy diễn nhân quả trên dữ liệu thật.
   - (c) **Track 2 (`window_stress_12lag_3sku`, `m=2`)** để trả lời thực chứng `RQ3` (`W=5 vs 10 vs 20`).

### 15.2. Kế hoạch Phân tích Notebook & Báo cáo Nghiên cứu Cuối (`Phase 5`)
Sau khi hoàn tất các batch được duyệt tiếp theo và có đủ điểm Human Evaluation, tổng hợp kết quả theo đúng kiến trúc P06:
- **`notebooks/06_e01_results_analysis.ipynb`:** Chỉ đọc artifacts bất biến từ `runs/P06-E01/formal_benchmark_v1/`, tính bảng đối chiếu theo track (`Natural` vs `Stress`), phân tích phân bố latency/tokens/Jaccard, tương quan metric tự động với điểm người chấm (chỉ từ dữ liệu thực tế).
- **`reports/tables/` & `reports/figures/`:** Xuất các bảng CSV/Markdown chuẩn hóa (Coverage & Gates, Reliability Logic-vs-503, Latency/Token Trade-offs, Human Rubric `6` trục) và biểu đồ (Topic Coverage vs Wasted Calls, Word/3-gram Jaccard across `W`, Latency P50/P95 & Time-to-First-Candidate).
- **`reports/p06_e01_research_report.md`:** Báo cáo tổng kết toàn bộ `P06-E01` (`RQ1`, `RQ3`, `RQ5`, kết luận `GO / CHANGE / NO-GO / INCONCLUSIVE` có sign-off của Reviewer độc lập).

---

## 16. Git Diff & Kiểm chứng Hồi quy Hậu Thực thi

- **Các tệp thêm/sửa mới trong phiên Batch 1A** *(tất cả nằm trong `experiments/sales-intelligence/autonomous-storytelling/`)*:
  - Tạo mới thư mục kết quả bất biến `runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/` (`protocol_deviation_and_criteria_lock.json`, `budget_ledger.json`, `batch_summary.json`, `comparison.{json,csv,md}`, `4` thư mục run đầy đủ artifacts, và `6` tệp `human_eval/`).
  - Cập nhật [`research/decision_log.md`](../research/decision_log.md) (`DR-P06-011`).
  - Tạo [`docs/12-e01-t09-formal-benchmark-batch1a-report.md`](./12-e01-t09-formal-benchmark-batch1a-report.md) (báo cáo này) và cập nhật [`docs/README.md`](./README.md), [`AGENTS.md`](../AGENTS.md).
  - **Không sửa** bất kỳ mã nguồn nào trong `src/p06/`, `configs/`, `prompts/`, `data/`, Pilot v1/v2 hay các module ngoài P06.
- **Kiểm thử hồi quy & kiểm tra độc lập:**
  - `.\.venv\Scripts\python.exe -m pytest experiments/sales-intelligence/autonomous-storytelling/tests -q` -> **`287 passed in 37.32s`** (`0 failed, 0 skipped`).
  - `.\.venv\Scripts\python.exe -m pip check` -> **`No broken requirements found.`**
  - `AGENTS.md`: **`22,425` bytes** (`< 24,000` bytes).
  - Rà soát độc lập (`hydrogen-scout`, chỉ-đọc): Xác nhận `52/52` tệp artifact đầy đủ, `0` rò rỉ khóa API/nhãn mù, `77` dòng `factual_and_semantic_review_sheet.csv` để trống hợp lệ, `94/120` requests (`0 USD`), Pilot v1/v2 nguyên vẹn, `10/10` locked hashes khớp và đã cập nhật 2 chi tiết đếm lượt văn bản tại Mục 1 & Mục 11.1.

---

**Trạng thái dừng:** **`AWAITING_BATCH_1A_REVIEW_AND_NEXT_BATCH_APPROVAL`**  
*(Không thực hiện thêm cuộc gọi Gemini API, không chạy Batch 1B/Track 2/E04 và không tự đánh dấu toàn bộ `P06-E01` là `VALIDATED` hay `COMPLETED`.)*
