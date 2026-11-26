# Giao thức & Chuẩn bị Formal Benchmark `P06-E01` — HOSTRA AI (`E01-T09`)

**Ngày cập nhật:** `2026-11-27`  
**Branch:** `research/p06-autonomous-storytelling`  
**Base Commit trước phiên:** `cb4d0c0`  
**Module:** `experiments/sales-intelligence/autonomous-storytelling/`  
**Quyết định Tech Lead:** `CONDITIONAL GO FOR FORMAL BENCHMARK` *(Scope Freeze & Final Protocol Lock)*  
**Trạng thái hiện tại:** **`AWAITING_FINAL_BENCHMARK_EXECUTION_APPROVAL`** *(Khóa giao thức, dữ liệu, prompt & cấu hình Batch 1A ngoại tuyến; **`0`** cuộc gọi Gemini API mới)*  
**Kiểm thử hồi quy ngoại tuyến:** **`287 passed in 67.87s`** (`0 failed, 0 skipped`), `pip check` -> `No broken requirements found.`

---

## 1. Các Chỉnh sửa Tối thiểu Sau Pilot v2

Tuân thủ nguyên tắc đóng băng kiến trúc (không thêm dynamic rewrite cho baseline, không refactor LangGraph, không sửa module P05, không thêm embedding/entailment model), nhóm chỉ thực hiện **3 chỉnh sửa mục tiêu** giải quyết đúng các điểm đã xác nhận ở Pilot v2:

### 1.1. Baseline Fairness — Đồng bộ Word Budget (`compute_chunk_word_budget`)
- **Nguyên nhân phát hiện ở Pilot v2:** `VirtualClock` tính thời lượng nói ở tốc độ `2.6 từ/giây`, nên trần `8.0s` (`8,000 ms`) chỉ cho phép tối đa **`20` từ** (`20 / 2.6 = 7.692s <= 8.0s`, còn `21 / 2.6 = 8.077s > 8.0s`). Ở Pilot v2, LangGraph đã dùng khung `12–18 từ` (`max_words = 18`), trong khi `ScriptFirstBaseline` và `run_gemini_pilot.py` Stage A Request 3 lại truyền `12–21 từ`, khiến Script-first Turn `[1]` sinh đúng `21` từ (`8.08s`) và bị reject oan.
- **Khắc phục đã triển khai:**
  1. Thêm hàm thuần `compute_chunk_word_budget(max_duration_sec, words_per_sec=2.6)` trong [`src/p06/simulation/virtual_clock.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/simulation/virtual_clock.py) (tái xuất qua [`src/p06/simulation/__init__.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/simulation/__init__.py)), trả về `(recommended_max_words=18, hard_max_words=20, target_words_range="12–18 từ")` cho `8.0s`.
  2. Cập nhật `_compute_word_budget()` tại [`src/p06/agent/nodes/_common.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/agent/nodes/_common.py) dùng chung `compute_chunk_word_budget()`.
  3. Cập nhật [`src/p06/baselines/script_first.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/baselines/script_first.py) lên `_UPFRONT_PROMPT_VERSION = "baseline-script-first-v0.2.1"`, truyền rõ `"giữ khung độ dài khuyến nghị {target_words_range}, tuyệt đối không vượt quá {hard_max_words} từ (<= {max_duration_sec} giây đọc)"`, đồng bộ cùng [`run_gemini_pilot.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_gemini_pilot.py) và làm giàu thông báo lỗi `OVER_MAX_DURATION_SEC` (kèm số từ thực tế vs trần `20` từ).
  4. **Bảo toàn tính công bằng phương pháp:** `ScriptFirstBaseline` vẫn giữ `rewrite_attempt=0` (tuyệt đối **không** bổ sung `bounded_rewrite` hay đọc `played_history`). Sự khác biệt cốt lõi giữa hai phương pháp vẫn là: *Script-first sinh một lần đầu phiên không sửa lại khi quá thời lượng/P05 từ chối, còn LangGraph có `bounded_rewrite` (`<= K=2`) và `played_history` (`W`)*.

### 1.2. Evidence Completeness — Bổ sung `topic.fact_refs` trên `e01_ext_v1`
- **Nguyên nhân phát hiện ở Pilot v2:** Một số topic trong [`e01_ext_v1_story_plans.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/data/story_plans/e01_ext_v1_story_plans.json) có `talking_points` tổng hợp ý từ 2–3 mảnh bằng chứng hợp lệ của cùng SKU (đặc biệt các topic mắc ca về sấy + độ giòn béo, bao bì + gói hút ẩm, dụng cụ tách vỏ), nhưng `topic.fact_refs` chỉ liệt kê `1` `evidence_id`.
- **Khắc phục đã triển khai:** Nâng `e01_ext_v1_story_plans.json` lên version **`1.0.1`**, bổ sung đầy đủ các `evidence_id` **đã tồn tại và đã `APPROVED`** trong [`e01_ext_v1_verified_skus.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/data/products/e01_ext_v1_verified_skus.json) cho `15` topics thuộc cả 5 kịch bản (trong đó cập nhật đầy đủ các topic mắc ca `topic-pilot-macadamia-01/02`, `topic-ext-edu-macadamia-packaging`, `topic-ext-brand-macadamia-sensory/packaging/pairing`, `topic-ext-sales-macadamia-sensory/offer`, `topic-stress-macadamia-03` cùng các topic mật ong/trà liên quan). **Không** tạo thêm claim không căn cứ và **không** chỉnh sửa P05.

### 1.4. Pilot v2 AI-Assisted Evaluation & Targeted Safety Review (`A/B/C`)

Sau Pilot v2, Tech Lead đã dùng ChatGPT thực hiện một vòng **AI-assisted non-blind evaluation** (theo rubric `v0.1`) dựa trên `REVIEWER_GUIDE_BLIND_QUALITY.md`, `REVIEWER_GUIDE_FACTUAL_AND_SEMANTIC_AUDIT.md` và hai transcript mù. Hai tệp CSV kết quả được lưu **tách biệt hoàn toàn** tại [`runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/ai_assisted_eval/`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/ai_assisted_eval/README.md) ([quality CSV](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/ai_assisted_eval/pilot_v2_ai_assisted_quality.csv), [factual/semantic CSV](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/ai_assisted_eval/pilot_v2_ai_assisted_factual_semantic.csv)), **không** ghi đè [`human_eval/`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/human_eval/blind_eval_sheet.csv):

> [!WARNING]
> **Ranh giới Provenance Bắt buộc:** Kết quả dưới đây là **AI-assisted non-blind evaluation**, tuyệt đối **KHÔNG phải Human Blind Evaluation** và **KHÔNG phải `GoldFactualLabel`**. Trạng thái **Human Evaluation Calibration** và **Gold Factual Assessment** vẫn là **`PENDING`** cho tới khi reviewer người thật chấm trực tiếp trên các phiếu `human_eval/` còn trống.

- **Tóm tắt quan sát AI-assisted trên Pilot v2 (rubric `v0.1`):**
  - `LangGraph W=5`: Mean `3.33/5` (`Coherence=3`, `Naturalness=3`, `Persuasiveness=3`, `Context Relevance=4`, `Transition Quality=2`, `Repetition Quality=5`), Semantic Alignment `5 FULL / 1 PARTIAL / 0 MISS`, Factual `4 PASS / 1 FAIL / 1 UNSURE`, Evidence Support `3 PASS / 3 FAIL`, Metadata leak `0/6`.
  - `Script-first`: Mean `3.17/5` (`Coherence=3`, `Naturalness=3`, `Persuasiveness=4`, `Context Relevance=3`, `Transition Quality=2`, `Repetition Quality=4`), Semantic Alignment `5 FULL / 1 PARTIAL / 0 MISS`, Factual `5 PASS / 0 FAIL / 1 UNSURE`, Evidence Support `3 PASS / 3 FAIL`, Metadata leak `0/6`.
- **Các chỉnh sửa tối thiểu cho 3 phát hiện Targeted Safety Review (`A`, `B`, `C`):**
  - **A. Bảo toàn điều kiện chính sách đổi trả:** Khôi phục đầy đủ điều kiện `"khi nhận hàng kèm video mở hộp"` (mật ong) và `"khi mở hộp"` (mắc ca) trong `clm-e01-honey-allowed-02` / `clm-e01-macadamia-allowed-02` (`e01_ext_v1_verified_skus.json v1.0.1`, `e01_formal_v1_verified_skus.json v1.1.1`), các `talking_points` liên quan trong `e01_ext_v1_story_plans.json (v1.0.2)` và `e01_formal_v1_story_plans.json (v1.1.1)`. Đồng thời bổ sung quy tắc vào [`story_generation.txt`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/prompts/story_generation.txt) (`v0.2.1`), [`rewrite.txt`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/prompts/rewrite.txt) (`v0.2.1`) và [`script_first.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/baselines/script_first.py) (`baseline-script-first-v0.2.2`) cấm lược bỏ điều kiện chính sách đổi trả chỉ để nén số từ.
  - **B. Loại bỏ suy diễn nhân quả chưa được chứng minh & lỗi lệch evidence Batch 1A:** Sửa `topic-pilot-macadamia-01` từ `"Sấy nhiệt độ thấp giữ độ giòn béo tự nhiên."` thành hai sự kiện độc lập đúng bằng chứng (`"Sấy đối lưu nhiệt độ thấp chín đều từ lõi; nhân hạt giòn béo tự nhiên."`); cấm suy diễn nhân quả không nêu trực tiếp trong prompt `v0.2.1`. Ngoài ra, kiểm toán chéo toàn bộ kịch bản đã phát hiện và sửa lỗi lệch bằng chứng ngay trong Batch 1A tại `topic-ext-edu-tea-pairing` (`"hạt rang bùi"` không có trong `ev-e01-ext-tea-pairing` -> sửa thành `"bánh quy nhạt hoặc mứt gừng nhẹ để cân bằng vị giác"`).
  - **C. Hoàn thiện `fact_refs`:** Rà soát 15 topics đã vá từ vòng trước (`v1.0.1`), giữ nguyên kết quả đã bao phủ vật liệu thép/gói hút ẩm/cảm quan và bổ sung thêm `ev-e01-ext-honey-safety` cho `topic-ext-brand-honey-pairing` (vì nhắc trẻ dưới 1 tuổi). Không refactor LangGraph hay P05.

### 1.5. Sửa lỗi đo `mandatory_topic_coverage` khi `min_chunks_per_topic >= 2`
- Phát hiện sai lệch trong [`coverage.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/evaluation/metrics/coverage.py): trước đây `completed_topic_ids` và `time_to_complete_mandatory_topics_sec` chỉ kiểm tra topic có `>= 1` `COMPLETED` ACK (bỏ qua `min_chunks_per_topic`).
- Đã cập nhật `compute_coverage_metrics()` đọc `min_chunks_per_topic` từ `manifest` và chỉ đánh dấu hoàn tất topic khi số ACK không-fallback `>= min_chunks_per_topic` (ghi rõ `partially_covered_topic_ids` và `played_chunk_counts_by_topic` trong `metadata`). Nhờ vậy, khi `W=20` dừng sớm `MAX_CONSECUTIVE_ABORTS` trước khi hoàn tất lượt 2 trên toàn bộ 36 topics (`m=2`), `mandatory_topic_coverage` phản ánh trung thực **`0.9722` (`35/36`)** thay vì báo nhầm `1.0000`.

---

## 2. Kiểm toán Dung lượng Dataset & Mức Sẵn sàng Thời lượng (`10–30` Phút & `W ∈ {5, 10, 20}`)

### 2.1. Kiểm toán Kỹ thuật 6 Yếu tố Cốt lõi

| Khía cạnh Kiểm toán | Hiện trạng Xác minh Thực tế | Hệ quả đối với Benchmark `10–30` Phút & Sweep `W` |
|---|---|---|
| **1. Số topics & chunks hợp lệ** | `e01_ext_v1`: `18` topics (`10m_ext`), `24` topics (`30m_ext`, `stress_24t`), tối đa `8` topics/SKU. `e01_formal_v1` *(mới)*: **`36` topics** (`window_stress_12lag_3sku`, `12` topics/SKU). | Mỗi chunk `<= 8.0s` đạt trung bình `~6.0s` (`15–16` từ). Với `m=1`, tổng thời lượng thật chỉ đạt **`108–220s`** (`1.8–3.7` phút). |
| **2. Dung lượng Approved Knowledge** | `e01_ext_v1`: `30` `evidence_chunks` (`10`/SKU), `21` claims (`7`/SKU). `e01_formal_v1`: **`36` `evidence_chunks` (`12`/SKU), `24` claims (`8`/SKU)**. | Không bịa thêm dữ liệu ngoài ngữ cảnh nông sản đóng gói; mọi chunk đều có `provenance` và `approval_status="APPROVED"`. |
| **3. Khả năng trình bày nhiều chunks/topic (`min_chunks_per_topic`)** | Runner hỗ trợ `min_chunks_per_topic = 1` hoặc `2` qua `GlobalTopicCoverage` và `ScriptFirstBaseline`. | Tại `m=2`, một topic có thể phát tối đa 2 chunk khác nhau (`36–72` lượt, `~3.6–7.9` phút), nhưng với các topic chỉ có `1` `allowed_claim_id`, khi lịch sử trong cửa sổ `W` còn lưu lượt 1, `RepetitionDetector` tầng 3 (`REPEATED_FACTS`) có thể cảnh báo nếu LLM dùng lại cùng `claim_id`. |
| **4. Session Termination Policy** | `session_runner.py` dừng trung thực khi hết nội dung hợp lệ: `EARLY_COMPLETION` (đủ mandatory topics trước target time), `CONTENT_EXHAUSTED` (hết topics nhưng thiếu mandatory), `TIME_BUDGET_EXHAUSTED`, hoặc `MAX_CONSECUTIVE_ABORTS`. | Với kịch bản `10m` (`600s`) và `30m` (`1800s`), hệ thống **dừng trung thực tại `EARLY_COMPLETION` / `CONTENT_EXHAUSTED`** khi cạn dữ liệu đã duyệt, tuyệt đối **không** ép AI lặp facts hoặc bịa chuyện chỉ để lấp đầy đồng hồ. |
| **5. Phạm vi `ShortTermPlayedHistory` & SKU** | `ShortTermPlayedHistory` giữ lịch sử toàn phiên (`recent_turns()` cắt `W` lượt cuối), nhưng `ArcSequencer` và `session_runner.py` chạy tuần tự từng SKU (`SKU-HONEY-01 -> SKU-TEA-02 -> SKU-MACADAMIA-03`). | Khoảng cách lượt (`lag`) giữa lần 1 (`chunk_part=0`) và lần 2 (`chunk_part=1`) của cùng một topic đúng bằng **số topic thuộc SKU đó** (không phải tổng số topic cả 3 SKU!). |
| **6. Số lượt để phân tách `W ∈ {5, 10, 20}`** | Ở `e01_ext_v1`: `6` topics/SKU -> `lag = 6` (chỉ tách `W=5 < 6` khỏi `W=10, 20 >= 6`; **không tách được `W=10` với `W=20`**); `8` topics/SKU -> `lag = 8` (vẫn `<= 10`). | Vì vậy bắt buộc có kịch bản **`window_stress_12lag_3sku` (`12` topics/SKU, `lag = 12`)** trong `e01_formal_v1` để thỏa điều kiện bất đẳng thức: **`W=5 < lag=12`**, **`W=10 < lag=12`**, và **`W=20 >= lag=12`**. |

### 2.2. Hồ sơ Mới `e01_formal_v1` (`window_stress_12lag_3sku`)
Để tách biệt rạch ròi bài toán *kể chuyện tự nhiên 18–24 chủ đề* với bài toán *phân tách độ nhạy cửa sổ `W=5 / 10 / 20`*, nhóm đã bổ sung phiên bản dữ liệu tổng hợp có kiểm soát **`e01_formal_v1`** (giữ nguyên vẹn hoàn toàn `e01` và `e01_ext_v1`):
- **Kho tri thức:** [`data/products/e01_formal_v1_verified_skus.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/data/products/e01_formal_v1_verified_skus.json) (`version: "1.1.0"`, `36` `evidence_chunks` = `12`/SKU — tái sử dụng 30 mảnh từ `e01_ext_v1` + thêm đúng 2 mảnh kiểm tra truy xuất/niêm phong và dịp/khẩu phần cho mỗi SKU; `24` claims).
- **Kế hoạch kịch bản:** [`data/story_plans/e01_formal_v1_story_plans.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/data/story_plans/e01_formal_v1_story_plans.json) (`window_stress_12lag_3sku`, `36` mandatory topics = `12`/SKU, `APPROVED`, `is_mvp_live_eligible() == True`).
- **Đăng ký cấu hình runner:** [`src/p06/runner/config.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/runner/config.py), [`sweep.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/runner/sweep.py), [`run_e01.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_e01.py).

### 2.3. Kết quả Offline Capacity & Duration Validation (Mock Only — KHÔNG phải bằng chứng chất lượng LLM)

> [!NOTE]
> Toàn bộ bảng dưới đây chạy bằng **`MockLLMProvider` ngoại tuyến** để xác minh cơ chế dừng, độ phủ dung lượng và phân tách cơ học `W=5 / 10 / 20` trước khi tiêu tốn quota Gemini thật. Kết quả Mock **không** đại diện cho chất lượng tiếng Việt hoặc hành vi sáng tạo của `gemini-3.5-flash-lite`.

| Profile / Scenario | `min_chunks` | Method | `W` | Termination | Turns | `sim_sec` / `target` | `dur_fulfill` | `topic_cov` | `lex_rep` | `rewrite` | `fallback` | Calls |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `e01_ext_v1` · `product_education_10m_ext` | `1` | `script_first_upfront_llm` | `N/A` | `EARLY_COMPLETION` | `18` | `108.08s / 600s` | `0.1801` | `1.0` | `0.0` | `0.0` | `0.0` | `18` |
| `e01_ext_v1` · `product_education_10m_ext` | `1` | `langgraph_structured_story` | `5` | `EARLY_COMPLETION` | `18` | `108.08s / 600s` | `0.1801` | `1.0` | `0.0` | `0.0` | `0.0` | `18` |
| `e01_ext_v1` · `product_education_10m_ext` | `2` | `script_first_upfront_llm` | `N/A` | `EARLY_COMPLETION` | `36` | `216.54s / 600s` | `0.3609` | `1.0` | `0.1143` | `0.0` | `0.0` | `36` |
| `e01_ext_v1` · `product_education_10m_ext` | `2` | `langgraph_structured_story` | `5` | `EARLY_COMPLETION` | `36` | `217.31s / 600s` | `0.3622` | `1.0` | `0.0` | `0.1667` | `0.0` | `42` |
| `e01_ext_v1` · `product_education_10m_ext` | `2` | `langgraph_structured_story` | `10` | `EARLY_COMPLETION` | `42` | `258.85s / 600s` | `0.4314` | `1.0` | `0.0` | `0.1429` | `0.1429` | `52` |
| `e01_ext_v1` · `product_education_10m_ext` | `2` | `langgraph_structured_story` | `20` | `EARLY_COMPLETION` | `42` | `258.85s / 600s` | `0.4314` | `1.0` | `0.0` | `0.1429` | `0.1429` | `52` |
| `e01_ext_v1` · `brand_storytelling_10m_ext` | `1` | `langgraph_structured_story` | `5` | `EARLY_COMPLETION` | `18` | `110.39s / 600s` | `0.1840` | `1.0` | `0.0` | `0.0` | `0.0` | `18` |
| `e01_ext_v1` · `sales_presentation_30m_ext` | `1` | `langgraph_structured_story` | `5` | `EARLY_COMPLETION` | `24` | `141.93s / 1800s` | `0.0788` | `1.0` | `0.0` | `0.0` | `0.0` | `24` |
| `e01_ext_v1` · `sales_presentation_30m_ext` | `2` | `langgraph_structured_story` | `10` | `EARLY_COMPLETION` | `54` | `329.62s / 1800s` | `0.1831` | `1.0` | `0.0189` | `0.1636` | `0.1091` | `70` |
| `e01_ext_v1` · `window_sensitivity_stress_24t` | `1` | `langgraph_structured_story` | `5` | `EARLY_COMPLETION` | `24` | `123.08s / 600s` | `0.2051` | `1.0` | `0.0` | `0.0` | `0.0` | `24` |
| `e01_ext_v1` · `window_sensitivity_stress_24t` | `2` | `langgraph_structured_story` | `10` | `EARLY_COMPLETION` | `54` | `310.77s / 600s` | `0.5180` | `1.0` | `0.0` | `0.2105` | `0.1053` | `77` |
| **`e01_formal_v1` · `window_stress_12lag_3sku`** | **`1`** | `langgraph_structured_story` | `5` | `EARLY_COMPLETION` | `36` | `219.62s / 600s` | `0.3660` | `1.0` | `0.0` | `0.0` | `0.0` | `36` |
| **`e01_formal_v1` · `window_stress_12lag_3sku`** | **`2`** | `script_first_upfront_llm` | `N/A` | `EARLY_COMPLETION` | `72` | `440.78s / 600s` | `0.7346` | `1.0` | `0.1549` | `0.0` | `0.0` | `72` |
| **`e01_formal_v1` · `window_stress_12lag_3sku`** | **`2`** | `langgraph_structured_story` | **`5`** | `EARLY_COMPLETION` | `72` | `439.62s / 600s` | `0.7327` | `1.0` | `0.0423` | `0.3056` | `0.0` | `97` |
| **`e01_formal_v1` · `window_stress_12lag_3sku`** | **`2`** | `langgraph_structured_story` | **`10`** | `EARLY_COMPLETION` | `74` | `451.93s / 600s` | `0.7532` | `1.0` | `0.0274` | `0.2973` | `0.0270` | `102` |
| **`e01_formal_v1` · `window_stress_12lag_3sku`** | **`2`** | `langgraph_structured_story` | **`20`** | `MAX_CONSECUTIVE_ABORTS` | `77` | `473.85s / 600s` | `0.7898` | `0.9722` | `0.0` | `0.3061` | `0.0612` | `156` |

> **Phát hiện thực nghiệm quan trọng từ kiểm định Mock:**
> 1. Trên `product_education_10m_ext (m=2)`, `W=10` và `W=20` cho kết quả giống hệt (`42` turns, `52` calls) vì `lag=6`. Trên `window_stress_12lag_3sku (m=2)` (`lag=12`), `W=5`, `W=10` và `W=20` tách biệt rõ (`72 -> 74 -> 77` turns; `97 -> 102 -> 156` calls; `lex_rep: 0.0423 -> 0.0274 -> 0.0`).
> 2. Ở `W=20 > lag=12` trên `m=2`, vì mỗi topic chỉ gắn `1` `allowed_claim_id`, khi lượt 2 quay lại topic cũ, `RepetitionDetector` tầng 3 (`REPEATED_FACTS`) cảnh báo nếu lượt trước vẫn nằm trong cửa sổ 20 lượt, dẫn đến cạn fallback và kích hoạt `MAX_CONSECUTIVE_ABORTS` ở SKU thứ 3 (còn `1/36` topic chưa hoàn tất lượt 2 nên `mandatory_topic_coverage = 35/36 = 0.9722`). Điều này khẳng định: **chạy `min_chunks_per_topic=1` cho Track 1 (Natural Storytelling) và chỉ dùng `min_chunks_per_topic=2` cho Track 2 (Controlled Window Sensitivity Stress)**.

---

## 3. Hướng dẫn Chấm điểm Con người (Human Evaluation Instructions)

### 3.1. Bộ Hồ sơ Chấm Điểm Pilot v2 (Sẵn sàng Chấm Ngay Trước Formal Runs)
1. **Bước 1 — Chấm chất lượng ngôn ngữ mù (Làm trước):** Đọc [`REVIEWER_GUIDE_BLIND_QUALITY.md`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/human_eval/REVIEWER_GUIDE_BLIND_QUALITY.md) và điền [`blind_eval_sheet.csv`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/human_eval/blind_eval_sheet.csv) (`6` tiêu chí `1–5` + `hard_constraint_violation`).
2. **Bước 2 — Kiểm tra Factual Claims & Semantic Topic Coverage (Làm sau Bước 1):** Đọc [`REVIEWER_GUIDE_FACTUAL_AND_SEMANTIC_AUDIT.md`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/human_eval/REVIEWER_GUIDE_FACTUAL_AND_SEMANTIC_AUDIT.md) và điền [`factual_and_semantic_review_sheet.csv`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/human_eval/factual_and_semantic_review_sheet.csv) (`FULL/PARTIAL/MISS`, `PASS/FAIL/UNSURE`, `evidence_support`, `metadata_leak`).
3. **Mở khóa sau khi chấm Pilot v2:** Tech Lead rà điểm đồng thuận giữa người chấm (nếu `>= 2` raters theo §4 của [`human_eval_rubric_v0.1.md`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/evaluation/rubrics/human_eval_rubric_v0.1.md)) và chốt chính thức bảng tiêu chí chấp nhận tại Mục 5 bên dưới trước khi chạy Formal Benchmark.

### 3.2. Quy trình Áp dụng cho Formal Benchmark
- Sau khi chạy xong mỗi batch Formal Benchmark, xuất phiếu chấm mù mới bằng `export_blind_human_eval_sheets()` vào thư mục riêng `runs/P06-E01/formal_benchmark_v1/<track>/human_eval/`, giữ `blind_key_mapping.private.json` tách riêng.
- Với các bản transcript dài (`18–36` turns/run), người chấm đánh giá theo từng mẫu ẩn danh (`METHOD_A..METHOD_D`) theo đúng quy trình 2 bước (ngôn ngữ mù trước -> đối chiếu factual/semantic & gắn `GoldFactualLabel` sau) để `overall_gate_status` chuyển từ `NOT_EVALUATED` sang `PASS/FAIL` dựa trên dữ liệu thật.

---

## 4. Ma trận Thực nghiệm Formal Benchmark (`Formal Experiment Matrix`)

- **Model & Tham số Cố định (`100%` giống nhau giữa các runs):** `gemini-3.5-flash-lite` Free Tier (`0 USD`, dữ liệu `SYNTHETIC` only), `thinking_level: "MINIMAL"`, `temperature: 0.3`, `top_p: 0.9`, `max_tokens: 1024`, `max_chunk_duration_sec: 8.0s` (`12–18 từ`, trần `20 từ`), `max_rewrite_retries: 2`, `min_request_interval_sec: 6.0s` (tuần tự, dừng khi `HTTP 429`).
- **Quy tắc tách bạch dữ liệu:** Tuyệt đối **không gộp** Pilot v1 (`v0.1`) hoặc Pilot v2 (`v0.2` trước chỉnh sửa an toàn) vào bảng Formal Benchmark `v1` (`v0.2.1` + `baseline-script-first-v0.2.2` + `e01_ext_v1 v1.0.2` / `e01_formal_v1 v1.1.1`).
- **Tách bạch khoảng cách cửa sổ (`lag`):** `product_education_10m_ext` có `6` topics/SKU (`lag=6`, chỉ tách `W=5` khỏi `W=10/20`), `window_sensitivity_stress_24t` có `8` topics/SKU (`lag=8`, vẫn `< 10`), chỉ `window_stress_12lag_3sku` có `12` topics/SKU (`lag=12`) mới thỏa `W=5 < lag=12`, `W=10 < lag=12` và `W=20 >= lag=12` khi `m=2`.

| Track & Mục tiêu Nghiên cứu | Dataset & Scenario | `min_chunks` | Cấu hình Phương pháp (`4` cấu hình) | Số lần lặp (`n`) | Lý do Thiết kế & Lưu ý Thống kê |
|---|---|---:|---|---:|---|
| **Track 1 — Natural Storytelling Benchmark (`RQ1`)** *(Ưu tiên 1)* | `e01_ext_v1` · `product_education_10m_ext` (`18` topics) + `brand_storytelling_10m_ext` (`18` topics) | `1` | 1. `script_first_upfront_llm`<br>2. `langgraph W=5`<br>3. `langgraph W=10`<br>4. `langgraph W=20` | `n = 2` seeds độc lập trên `product_education_10m_ext` (`seed=42, 43`); `n = 1` trên `brand_storytelling_10m_ext` (`seed=42`) | Đo khả năng kể chuyện tự nhiên 18 chủ đề (không lặp ép buộc), độ bám `talking_points`, tỷ lệ lỗi duration/citation giữa `Script-first` và `LangGraph`. Với `n = 1–2`, **không tuyên bố ý nghĩa thống kê (p-value)**. |
| **Track 2 — Controlled Repetition & History Window Sensitivity (`RQ3`)** *(Ưu tiên 2)* | `e01_formal_v1` · `window_stress_12lag_3sku` (`36` topics × `2` = `72` turns, `lag=12`) | `2` | 1. `script_first_upfront_llm`<br>2. `langgraph W=5`<br>3. `langgraph W=10`<br>4. `langgraph W=20` | `n = 1` stress run có kiểm soát (`seed=42`) | Kịch bản stress độc lập để kiểm chứng cơ chế `ShortTermPlayedHistory` + `RepetitionDetector` khi `W=5 < 12`, `W=10 < 12`, `W=20 >= 12`. Phân tách hoàn toàn khỏi Track 1 tự nhiên. |
| **Track 3 — Extended 30m Coverage (`RQ1/RQ3` mở rộng)** *(Ưu tiên 3 — Điều kiện)* | `e01_ext_v1` · `sales_presentation_30m_ext` (`24` topics, mục tiêu `1800s`) | `1` | 1. `script_first_upfront_llm`<br>2. `langgraph W=10` | `n = 1` (`seed=42`) | Chỉ chạy sau khi Track 1 & 2 hoàn tất sạch và RPD còn dư; kiểm tra độ ổn định dài `24` chủ đề × `8` góc độ/SKU dưới `0` bình luận. |

> **Lưu ý về `seed`:** `gemini-3.5-flash-lite` là mô hình cloud bất định nên `seed=42` và `seed=43` giúp cố định thứ tự/khởi tạo nội bộ và đánh dấu biến lặp độc lập; kết quả sẽ báo cáo theo từng run kèm khoảng dao động (min–max), không chọn lọc kết quả đẹp.

---

## 5. Định nghĩa Metrics & Đề xuất Tiêu chí Nghiệm thu (`Proposed Acceptance Criteria`)

> [!IMPORTANT]
> Theo đúng quy tắc P06:
> - **Hard Gates** phải đạt tuyệt đối **`0` vi phạm** (không cho phép bù trừ).
> - Toàn bộ ngưỡng chất lượng mềm và độ trễ dưới đây mang trạng thái **`PROPOSED / TO VALIDATE`** — Tech Lead và nhóm cần rà soát, chỉnh sửa (nếu cần) và **khóa trước khi chạy Formal Benchmark**.

### 5.1. Nhóm Hard Safety & Structural Gates (`0` vi phạm bắt buộc)

| Gate / Metric | Định nghĩa Đo | Ngưỡng Bắt buộc |
|---|---|---:|
| `G4_Hygiene_MetadataLeak` | Số lượt phát có chứa `ev-*`, `clm-*`, `SKU-*`, `topic-*`, mảnh JSON hoặc tên trường DTO | **`= 0`** |
| `G4_EvidenceAttribution` | Số lượt `PROACTIVE_STORY` factual thiếu `cited_evidence_ids` hợp lệ hoặc cite chéo SKU | **`= 0`** |
| `G4_FactualAccuracy` *(Human / Gold Label)* | Tỷ lệ sai giá (`159k`/`245k`/`195k`), sai khối lượng/HSD/xuất xứ, nhắc claim `PROHIBITED` (chữa bệnh) | **`= 0` sai lệch** |
| `G3_CompletedChunkReplay` | `exact_chunk_replay_count` — số lần phát lại nguyên trạng `chunk_id` đã có `PlaybackCompleted` ACK | **`= 0`** |
| `I02_I04_I06_Invariants` | Không tự duyệt claim, không tự đổi `active_sku_id`, fallback không tự cộng `completed_topic_ids` | **`PASS` (`0` vi phạm)** |

### 5.2. Nhóm Chất lượng, Độ tin cậy & Hiệu năng (`PROPOSED / TO VALIDATE`)

| Metric | Định nghĩa & Nguồn đo | Ngưỡng Đề xuất cho Formal Benchmark (`PROPOSED`) |
|---|---|---|
| `mandatory_topic_coverage` | `completed_mandatory_topics / planned_mandatory_topics` (Playback-confirmed) | LangGraph **`>= 0.95`** (mục tiêu `1.00` khi không mất toàn bộ fallback do 503); đối chiếu ưu thế so với Script-first |
| `semantic_topic_alignment` *(Human Audit)* | Tỷ lệ topic đạt `FULL` trên `factual_and_semantic_review_sheet.csv` | **`>= 0.85` `FULL`** (`MISS <= 0.05`) trên Track 1 tự nhiên |
| `exact_normalized_text_replay_count` | Số lượt phát trùng văn bản chuẩn hóa hoàn toàn trong phiên | **`= 0`** trên Track 1 (`m=1`) |
| `lexical_repetition_rate` | Tỷ lệ lượt vượt ngưỡng `Word Jaccard >= 0.65` hoặc `3-gram Jaccard >= 0.45` | **`<= 0.05`** trên Track 1 (`m=1`); ghi nhận phân tách theo `W` trên Track 2 (`m=2`) |
| `rewrite_rate` & `fallback_rate` | Tỷ lệ lượt cần `bounded_rewrite` / phải dùng `PREAPPROVED_FALLBACK` (loại trừ lỗi `HTTP 503` hạ tầng) | `rewrite_rate` do logic agent **`<= 0.15`**; `fallback_rate` do logic agent **`<= 0.05`** |
| `wasted_calls_logic_pct` | Tỷ lệ calls bị loại do lỗi prompt/logic/schema/duration (tách riêng khỏi `HTTP 503`) | **`<= 10%`** tổng calls trên LangGraph |
| `provider_latency_p50_ms` / `p95_ms` | Thời gian chờ mỗi request Gemini (`MEASURED`) | Ghi nhận phân bố thực tế đóng góp vào budget `W1` (`P50 <= 7s`, `P95 <= 10s` cho đơn lượt) |
| **Human Rubric (`1–5`, trung bình theo mẫu)** | `narrative_coherence`, `naturalness`, `persuasiveness`, `context_relevance`, `transition_quality`, `repetition_quality` | Trung bình mỗi trục **`>= 3.5 / 5.0`**, không trục nào **`< 3.0`** *(chỉ khóa sau Pilot v2 Calibration)* |

### 5.3. Phân định Rạch ròi Các Khái niệm Đánh giá & Tiêu chuẩn Khóa Ngưỡng
1. **Playback Coverage (`mandatory_topic_coverage`) ≠ Semantic Content Coverage:** `mandatory_topic_coverage` đo tỷ lệ chủ đề bắt buộc có ít nhất `min_chunks_per_topic` `PlaybackCompleted` ACK không-fallback (`0/1` kỹ thuật). Nó **không** chứng minh lời thoại truyền đạt đủ ý chính; phần đó đo riêng bằng `semantic_alignment_FULL_PARTIAL_MISS`.
2. **Factual Correctness ≠ Evidence Support:** `factual_correctness (PASS / FAIL / UNSURE)` thẩm định lời thoại có đúng với toàn bộ tri thức đã duyệt (`ProductFact` + `approved_chunks`) và chính sách an toàn/đổi trả hay không; còn `evidence_support (PASS / FAIL)` thẩm định chặt xem riêng các `cited_evidence_ids` được gán ở lượt đó có đủ chứng minh mọi chi tiết trong câu nói hay không.
3. **Định nghĩa `FULL / PARTIAL / MISS` (Semantic Alignment):** `FULL` = truyền tải trọn vẹn mọi ý chính trong `expected_talking_points` của chủ đề; `PARTIAL` = giữ được một phần ý chính hoặc giá/quy cách nhưng thiếu nhánh thông tin trọng tâm (hoặc dùng câu fallback thay thế); `MISS` = lạc chủ đề hoặc không truyền đạt được ý chính nào của topic.
4. **Giữ nguyên ngưỡng chất lượng đề xuất (`PROPOSED / TO VALIDATE`):** Vẫn giữ mục tiêu trung bình mỗi trục **`>= 3.5 / 5.0`** và không trục nào **`< 3.0`**; **không** hạ chuẩn xuống mức Pilot v2 AI-assisted (`3.33 / 3.17`, `transition_quality = 2/5`) để làm đẹp báo cáo.
5. **`Duration Fulfillment` & `termination_reason`:** Báo cáo trung thực cặp `(duration_fulfillment, termination_reason)` với đủ 4 trạng thái dừng (`EARLY_COMPLETION`, `CONTENT_EXHAUSTED`, `TIME_BUDGET_EXHAUSTED`, `MAX_CONSECUTIVE_ABORTS`), ghi nhận rõ giới hạn nghiên cứu không đạt đủ `10–30` phút trên 3 SKU ở trần `8.0s/chunk` thay vì ép lặp.

---

## 5B. Bảng Khóa Phiên bản & SHA-256 Tài nguyên (`Artifact Lock Table`)

| Thành phần Khóa | Đường dẫn Tương đối | Version | SHA-256 |
|---|---|---|---|
| Dataset `e01_ext_v1` SKUs | `data/products/e01_ext_v1_verified_skus.json` | `1.0.1` | `6ab12c62f3545d804b55ba5e23477f7b610313f81775cdd5452a783916518c64` |
| StoryPlans `e01_ext_v1` | `data/story_plans/e01_ext_v1_story_plans.json` | `1.0.2` | `42c446c4f0c36293b48f985a78079360abd7db243bc66ca532e058f47047f020` |
| Dataset `e01_formal_v1` SKUs | `data/products/e01_formal_v1_verified_skus.json` | `1.1.1` | `bd70430b9f5dfa34fc5ea13560aa437f9dd994ce92159f9000106ca7eb1a71c6` |
| StoryPlans `e01_formal_v1` | `data/story_plans/e01_formal_v1_story_plans.json` | `1.1.1` | `f969ec242b30578275cac01c2d10eaf602b57a3b6a3bbf12a42dcdc924f055f3` |
| Prompt `story_planner.txt` | `prompts/story_planner.txt` | `v0.1` *(LF)* | `f07514cc307bff4a3332d419a539f843bb18510722bdc7774a26a9ff98ddd118` |
| Prompt `story_generation.txt` | `prompts/story_generation.txt` | `v0.2.1` *(LF)* | `0f1eb7e856654d9565a9e6dbe468f59180c3dc20bc4cb723cd1441d5000d5912` |
| Prompt `rewrite.txt` | `prompts/rewrite.txt` | `v0.2.1` *(LF)* | `1126789faaf84f547a455b677af4b025103e3a1b60513e1fc0910cc14a5c61d5` |
| Prompt `ScriptFirstBaseline` | `src/p06/baselines/script_first.py` | `baseline-script-first-v0.2.2` | `50ed84045f0014400ae60a799513968c5f4d68054e77cf79f9578823184554d4` |
| Model Config Free Tier | `configs/models/gemini_3.5_flash_lite_free.yaml` | `free_tier` | `c836c82baee490a4b4d728e2877d19e4fd15c16a87c64372a9af3692a7ab344b` |
| Batch 1A Config | `configs/experiments/p06_e01_formal_batch1a.yaml` | `batch1a_s42` | `3792162ed9c7b3e0b35054575e82804f00615f759efe44c42968fc825716cfdc` |

### 6.1. Thông số Hạn mức & Nguyên tắc Tính
- **Quota Free Tier tham chiếu:** `RPM = 15`, `TPM = 250,000`, `RPD = 500`, **`0 USD`** (cần xác minh lại số RPD còn dư thực tế trên Google AI Studio ngay trước khi kích hoạt từng batch; **không** cộng hay tái sử dụng slot dư từ Pilot v2).
- **Công thức ước tính:** `Estimated Requests = Base_Chunks + Expected_Rewrites/Retries (~10–25% cho LangGraph tùy Track) + HTTP_503_Buffer (~10–15%)`. Với pacing bắt buộc `>= 6.0s` + latency trung bình `~6.0s`, mỗi request mất khoảng **`12s` wall-clock** (`~5 requests/phút`).

### 6.2. Chia Batch Theo Ngày Phù hợp với RPD Free Tier (`<= 500 RPD`)

| Batch | Nội dung Runs Dự kiến | Base Calls | Dự phòng Rewrite + `503` | Trần Ngân sách Đề xuất (`max_requests`) | Thời gian Ước lượng (`>= 12s/req`) |
|---|---|---:|---:|---:|---|
| **Batch 1** *(Ngày 1 — Track 1 Natural)* | `product_education_10m_ext` (`m=1`, 4 configs × 2 seeds = 8 runs × 18 = 144 base) + `brand_storytelling_10m_ext` (`m=1`, 4 configs × 1 seed = 4 runs × 18 = 72 base) | `216` | `+34` (~`15.7%`) | **`250` requests** | `~45–50` phút (`0 USD`) |
| **Batch 2A** *(Ngày 2 — Track 2 Stress Phần 1)* | `window_stress_12lag_3sku` (`m=2`): `script_first_upfront_llm` (`72`) + `langgraph W=5` (`72` base) | `144` | `+36` (`25%` cho `m=2`) | **`180` requests** | `~32–36` phút (`0 USD`) |
| **Batch 2B** *(Ngày 3 — Track 2 Stress Phần 2)* | `window_stress_12lag_3sku` (`m=2`): `langgraph W=10` (`72` base) + `langgraph W=20` (`72` base) | `144` | `+76` *(Mock `W=20` tốn tới `156` calls; thêm buffer cho rewrite/503)* | **`220` requests** *(hoặc tách `W=10` riêng `110` + `W=20` riêng `140` nếu muốn an toàn tối đa)* | `~40–45` phút (`0 USD`) |
| **Batch 3** *(Ngày 4 — Track 3 Điều kiện)* | `sales_presentation_30m_ext` (`m=1`, `script_first` + `langgraph W=10` = `48` base) | `48` | `+12` (`25%`) | **`60` requests** | `~12` phút (`0 USD`) |
| **Tổng Toàn chiến dịch Formal Benchmark** | `Track 1 (12 runs) + Track 2 (4 runs) + Track 3 (2 runs) = 18 runs` | **`552`** | **`+158`** | **`710` requests** *(chia 3–4 ngày, mỗi ngày `< 250 RPD < 500 RPD`)* | Tổng `~2.2` giờ chia 3–4 phiên (`0 USD`) |

> **Khuyến nghị tiết kiệm quota nếu cần chạy gọn hơn trong 1–2 ngày:** Có thể chạy Batch 1 với `n=1` cho `product_education_10m_ext` (`72` base) + `brand_storytelling_10m_ext` (`72` base) = `144` base (`cap = 175` requests), sau đó mới chạy Batch 2 (`lag=12`).

---

## 7. Các Commands Dự kiến Chạy (CHƯA THỰC THI)

> [!CAUTION]
> Các lệnh dưới đây là lệnh dự kiến chỉ chạy **sau khi có phê duyệt `FINAL BENCHMARK EXECUTION APPROVAL`**, xác minh lại `RPD` thực tế trên Google AI Studio và hoàn tất chấm điểm Pilot v2.

### 7.1. Batch 1A — Khóa cấu hình thực thi chính thức đầu tiên (`run_gemini_formal_batch.py`, `Global Cap = 120`)
Nhóm đã đóng gói cấu hình Batch 1A vào [`configs/experiments/p06_e01_formal_batch1a.yaml`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/configs/experiments/p06_e01_formal_batch1a.yaml) và bộ điều phối sổ cái toàn cục [`run_gemini_formal_batch.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_gemini_formal_batch.py):
- **Cấu hình khóa:** `gemini-3.5-flash-lite` Free Tier (`0 USD`, `SYNTHETIC` only), `e01_ext_v1` · `product_education_10m_ext`, `seed=42`, `min_chunks_per_topic=1`, `max_chunk_duration_sec=8.0`, `4` phương pháp (`script_first_upfront_llm`, `langgraph W=5`, `W=10`, `W=20`), **`max_requests_per_run = 30`**, **`global_max_requests = 120`** (tính cả failed requests, retries, rewrites), `min_request_interval_sec = 6.0`, dừng ngay khi `HTTP 429` và lưu `budget_ledger.json` + `batch_summary.json` + `comparison.*` + `human_eval/`.

```powershell
# CHỈ CHẠY SAU KHI CÓ PHÊ DUYỆT FINAL_BENCHMARK_EXECUTION_APPROVAL:
.\.venv\Scripts\python.exe experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_gemini_formal_batch.py `
  --config experiments/sales-intelligence/autonomous-storytelling/configs/experiments/p06_e01_formal_batch1a.yaml `
  --allow-live-provider
```

```powershell
# Kiểm thử dry-run ngoại tuyến với Mock (0 API call):
.\.venv\Scripts\python.exe experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_gemini_formal_batch.py `
  --config experiments/sales-intelligence/autonomous-storytelling/configs/experiments/p06_e01_formal_batch1a.yaml `
  --provider mock --output-dir experiments/sales-intelligence/autonomous-storytelling/.pytest_cache/batch1a_mock_dryrun
```

### 7.2. Batch 1B & Track 2 (`lag=12`) tham khảo bằng `run_e01.py` / Batch YAML tương ứng
```powershell
# Chạy sweep Track 1 bổ sung (ví dụ brand_storytelling_10m_ext hoặc seed=43) với run_e01.py:
.\.venv\Scripts\python.exe experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_e01.py `
  --provider gemini --allow-live-provider `
  --config experiments/sales-intelligence/autonomous-storytelling/configs/models/gemini_3.5_flash_lite_free.yaml `
  --dataset-profile e01_ext_v1 --scenario brand_storytelling_10m_ext `
  --min-chunks-per-topic 1 --seed 42 --max-turns 40 --max-llm-calls 30 `
  --sweep --export-human-eval `
  --output-dir experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/formal_benchmark_v1/track1_brand_s42
```
*(Lưu ý quan trọng khi dùng `--sweep` với `DEFAULT_E01_METHODS`: hiện tại `DEFAULT_E01_METHODS` trong `sweep.py` gồm cả `script_first_deterministic`, phương pháp này `0` LLM call và giúp đối chứng thêm baseline tất định; hoặc gọi từng `--method` riêng cho `script_first_upfront_llm` và `langgraph_structured_story` `--history-window 5/10/20` nếu muốn kiểm soát từng run và chỉ xuất human eval cho 4 phương pháp LLM).*

```powershell
# Mẫu chạy từng phương pháp (kiểm soát chặt ngân sách từng run, khuyến nghị cho Batch 2 lag=12):
# 1) Script-first upfront LLM (cap 80 calls cho 72 topics*2):
.\.venv\Scripts\python.exe experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_e01.py `
  --provider gemini --allow-live-provider `
  --config experiments/sales-intelligence/autonomous-storytelling/configs/models/gemini_3.5_flash_lite_free.yaml `
  --dataset-profile e01_formal_v1 --scenario window_stress_12lag_3sku `
  --method script_first_upfront_llm --min-chunks-per-topic 2 --seed 42 `
  --max-turns 100 --max-llm-calls 80 `
  --output-dir experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/formal_benchmark_v1/track2_lag12

# 2) LangGraph W=5 / W=10 / W=20 (thay --history-window 5 / 10 / 20 và --max-llm-calls 100 / 110 / 140):
.\.venv\Scripts\python.exe experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_e01.py `
  --provider gemini --allow-live-provider `
  --config experiments/sales-intelligence/autonomous-storytelling/configs/models/gemini_3.5_flash_lite_free.yaml `
  --dataset-profile e01_formal_v1 --scenario window_stress_12lag_3sku `
  --method langgraph_structured_story --history-window 5 --min-chunks-per-topic 2 --seed 42 `
  --max-turns 120 --max-llm-calls 100 `
  --output-dir experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/formal_benchmark_v1/track2_lag12
```

> *Lưu ý kỹ thuật trước khi chạy batch bằng `run_e01.py`:* Khi gọi nhiều lệnh `run_e01.py` rời nhau, mỗi lệnh tạo một `GeminiAPIProvider` mới; vì `min_request_interval_sec = 6.0` nằm trên từng `GeminiRestClient`, hãy chừa khoảng nghỉ `>= 6s` giữa hai lệnh CLI hoặc dùng một script batch nhỏ dùng chung một `GeminiRestClient` + `budget_ledger.json` (tương tự `run_gemini_pilot.py`) nếu cần gom `compare_runs()` + `export_blind_human_eval_sheets()` tự động.

---

## 8. Kết quả Kiểm thử Hồi quy (`Regression Tests`)

Chạy toàn bộ bộ test P06 và kiểm tra phụ thuộc sau chỉnh sửa code/data/prompt cuối cùng:
- `.\.venv\Scripts\python.exe -m pytest experiments/sales-intelligence/autonomous-storytelling/tests -q` -> **`287 passed in 67.87s (0:01:07)`** (`0 failed, 0 skipped`) — gồm `279` tests cũ (`2` cập nhật chuỗi version `v0.2.1` / `baseline-script-first-v0.2.2`) và `8` tests trong [`tests/unit/test_formal_benchmark_prep.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/tests/unit/test_formal_benchmark_prep.py) (bao gồm kiểm tra `coverage.py` khi `min_chunks_per_topic=2`, các bản vá an toàn A/B/C, cô lập `ai_assisted_eval/` khỏi `human_eval/`, và dry-run Batch 1A với Mock + `FakeGeminiRestClient`).
- `.\.venv\Scripts\python.exe -m pip check` -> **`No broken requirements found.`**

---

## 9. Giới hạn Còn lại (`Remaining Limitations`)

1. **Giới hạn toán học của trần `8.0s` trên phiên `10–30` phút không bình luận:** Ở tốc độ `2.6` từ/giây và khung `12–18` từ (`~6.0s`/chunk), một bộ `3` SKU thực phẩm đóng gói (`30–36` mảnh tri thức đã duyệt) không thể kéo dài tự nhiên tới `10–30` phút (`100–300` chunks) mà không lặp ý hoặc chia nhỏ quá vụn; hệ thống chấp nhận dừng trung thực (`EARLY_COMPLETION`) khi phủ đủ chủ đề thay vì sinh fluff.
2. **Hành vi `W=20` khi `min_chunks_per_topic=2` và `1 claim/topic`:** Như đã quan sát ở Mock validation trên `window_stress_12lag_3sku (m=2)`, khi cửa sổ `W=20 > lag=12` giữ lại lượt 1 của topic chỉ có 1 `claim_id`, cơ chế `REPEATED_FACTS` có thể kích hoạt `MAX_CONSECUTIVE_ABORTS` nếu model không có claim thay thế trong cùng topic. Kết quả trên Gemini thật sẽ làm rõ mức nhạy thực tế của `W=10` vs `W=20`.
3. **P05 chưa kiểm tra semantic entailment:** `P05KnowledgeAdapter` kiểm tra `evidence_id` tồn tại, giá, OCOP, từ cấm và hygiene, nhưng chưa có NLI/entailment kiểm chứng từng câu văn có suy diễn đúng 100% từ `cited_evidence_ids` hay không. Việc chấm tay ở Bước 2 vẫn bắt buộc.
4. **Nhiễu `HTTP 503` của Free Tier:** Vẫn là rủi ro hạ tầng thực tế khi chạy chuỗi `18–72` requests liên tiếp.
5. **Chưa có điểm chấm người thật trên Pilot v2 (`PENDING`):** Các tệp trong `ai_assisted_eval/` chỉ là AI-assisted non-blind (không phải Human Blind Evaluation hay `GoldFactualLabel`); phiếu `human_eval/` vẫn đang chờ reviewer người thật chấm để hiệu chuẩn rubric trước Formal runs.
6. **Cần xác minh quota RPD & phê duyệt cuối trước khi chạy Batch 1A:** Phải kiểm tra số RPD còn dư trên Google AI Studio (`>= 120` requests cho Batch 1A) và nhận phê duyệt tường minh `FINAL_BENCHMARK_EXECUTION_APPROVAL`.
7. **Tier 2 Ollama CPU:** Vẫn ở trạng thái **`DEFERRED WITH USER APPROVAL`**.

---

## 10. Definition of Done để Kết thúc `P06-E01`

Thí nghiệm `P06-E01` chỉ được đánh dấu **`COMPLETED`** và sẵn sàng chuyển sang `P06-E04` khi đạt đủ 6 điều kiện sau:

- [ ] **DoD-1:** Hoàn tất chấm 2 bước Pilot v2 (`blind_eval_sheet.csv` + `factual_and_semantic_review_sheet.csv`) và Tech Lead xác nhận/khóa Acceptance Criteria (Mục 5).
- [ ] **DoD-2:** Nhận phê duyệt **`FINAL BENCHMARK EXECUTION APPROVAL`**, xác minh lại quota RPD Google AI Studio, và chạy hoàn tất **Batch 1 (Track 1 Natural)** + **Batch 2 (Track 2 Stress `lag=12`)** (và Batch 3 nếu được duyệt) với ngân sách `0 USD` và nhật ký `budget_ledger.json` đầy đủ.
- [ ] **DoD-3:** Xuất và chấm mù Human Evaluation + gắn `GoldFactualLabel` trên mẫu Formal Benchmark để `overall_gate_status` chuyển từ `NOT_EVALUATED` sang `PASS`/`FAIL` thật.
- [ ] **DoD-4:** Lưu bất biến toàn bộ artifacts (`manifest.json`, `metrics.json`, `transcript.jsonl`, `provider_calls.jsonl`, `graph_trace.jsonl`, `errors.jsonl`, `token_usage.json`, `comparison.{json,csv,md}`) dưới `runs/P06-E01/formal_benchmark_v1/`.
- [ ] **DoD-5:** Tổng hợp bảng kết quả cuối cùng vào `experiments/sales-intelligence/autonomous-storytelling/reports/` (`final_report.md` / `e01_report.md`), đối chiếu đầy đủ 3 Research Questions của E01, phân tích cả lượt lỗi (`HTTP 503` vs logic agent), và nêu rõ giới hạn.
- [ ] **DoD-6:** Đưa ra kết luận có bằng chứng (**`GO`** / **`CHANGE`** / **`NO-GO`** / **`INCONCLUSIVE`**) và đạt sign-off của Tech Lead/Reviewer trước khi mở `P06-E04`.

---

**Trạng thái hiện tại:** **Dừng hoàn toàn tại `AWAITING_FINAL_BENCHMARK_EXECUTION_APPROVAL`.** Không thực hiện cuộc gọi Gemini API nào trong phiên chuẩn bị này và không tự commit/push.

---

## 11. Phụ lục Sửa đổi Giao thức — Rút gọn Phạm vi Track 1 (Batch 1B, `2026-11-27`)

Theo quyết định Tech Lead (`DR-P06-012`) sau khi review kết quả **Batch 1A** (`docs/12-e01-t09-formal-benchmark-batch1a-report.md`) và bộ đánh giá AI-assisted ChatGPT (`77` dòng, giữ `human_eval/` ở trạng thái `PENDING`):

1. **Rút gọn ma trận Track 1 Natural Storytelling:**
   - **Batch 1A** (`product_education_10m_ext`, `seed=42`, `script_first_upfront_llm` + `langgraph W=5/10/20`): **Đã hoàn thành** (`94/120` requests, `0 USD`).
   - **Batch 1B** (`brand_storytelling_10m_ext`, `seed=42`, `min_chunks_per_topic=1`, `3` SKUs, `18` planned topics = `12` mandatory + `6` optional): **Phê duyệt rút gọn còn 2 cấu hình** (`script_first_upfront_llm` `max_retries=0` và `langgraph_structured_story W=5`) để kiểm tra khả năng tổng quát hóa sang kịch bản kể chuyện thương hiệu và an toàn thương mại/OCOP, đồng thời dành ngân sách cho Track 2 History Window Stress Test (`lag=12`).
   - Các cấu hình không chạy trong Batch 1B (`W=10`, `W=20`, `product_education seed=43`) **không** được coi là đã thực hiện và **không** gộp `W=10/20` của Batch 1A vào so sánh ghép cặp cross-scenario.
2. **Ngân sách & Khóa cấu hình Batch 1B:**
   - Tệp cấu hình: [`configs/experiments/p06_e01_formal_batch1b.yaml`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/configs/experiments/p06_e01_formal_batch1b.yaml) (`SHA-256: f380892c137606f0277aafa809a4623a904a9f262c10797cf0cb897b42079fd2`).
   - Ngân sách mới tách biệt hoàn toàn khỏi Batch 1A: **`global_max_requests = 60`**, **`max_requests_per_run = 30`**, **`max_cost_usd = 0.0`** (`Free Tier`), `min_request_interval_sec = 6.0`, `stop_on_rate_limit = true`.
   - Thư mục xuất: [`runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/).
3. **Bảo toàn Tiêu chí & Tài nguyên Khóa:** Toàn bộ `10/10` mã băm dữ liệu/prompt/model/baseline ở Mục 5B và toàn bộ Acceptance Criteria ở Mục 5 được giữ nguyên 100%, không hạ chuẩn ngưỡng chất lượng.

---

## 12. Phụ lục Sửa đổi Giao thức — Đóng Natural Track Rút gọn & Thiết kế Đối chứng Track 2 (`2026-11-27`)

Theo định hướng Tech Lead (`DR-P06-013`) và báo cáo sẵn sàng [`docs/14-e01-t09-track2-readiness-and-protocol.md`](./14-e01-t09-track2-readiness-and-protocol.md):

1. **Đóng Natural Storytelling Benchmark theo phạm vi rút gọn:**
   - **Đã hoàn tất:** Batch 1A (`product_education_10m_ext`, `seed=42`), Batch 1B (`brand_storytelling_10m_ext`, `seed=42`) cùng 2 bộ đánh giá AI-assisted ChatGPT (`ai_assisted_eval/`).
   - **Hoãn (`DEFERRED`):** `Product Education seed=43`, các run `Brand Storytelling` bổ sung (`W=10/20`), `Extended 30m`; **không** chạy Pilot v3.
   - Human Calibration, Human Blind Evaluation và `GoldFactualLabel` giữ trạng thái **`PENDING`**; chưa đánh dấu `P06-E01` là `VALIDATED`.
2. **Thiết kế đối chứng rút gọn cho Track 2 (`Reduced Paired-Comparison Design`, `0` thay đổi kiến trúc/prompt/dataset/gates):**
   - **Track 2A (`Small Window Sensitivity`):** [`configs/experiments/p06_e01_formal_track2a_w5_w10.yaml`](../configs/experiments/p06_e01_formal_track2a_w5_w10.yaml) (`SHA-256: d52a17b1c832093490e5b0092921c56d2e09488e8d7335088156ae41a23e5ae7`), so sánh **`W=5` vs `W=10`** trên `product_education_10m_ext` (`min_chunks_per_topic=2`, `lag=6`, `seed=42`, `max_turns=80`, `max_requests_per_run=120`, `global_max_requests=240`).
   - **Track 2B (`Large Window Sensitivity`):** [`configs/experiments/p06_e01_formal_track2b_w10_w20.yaml`](../configs/experiments/p06_e01_formal_track2b_w10_w20.yaml) (`SHA-256: b4e6c539e1f316219e86d35532c3e0dde0e3a993c41c7ffd1897d287221354b4`), so sánh **`W=10` vs `W=20`** trên `window_stress_12lag_3sku` (`min_chunks_per_topic=2`, `lag=12`, `seed=42`, `max_turns=120`, `max_requests_per_run=200`, `global_max_requests=400`).
   - Bỏ `Script-first` khỏi stress track vì Natural Track đã đối chứng baseline trên 2 scenarios; tuyệt đối không suy diễn `W` tối ưu toàn cục giữa hai scenario khác nhau.
   - **Trạng thái hiện tại:** Chỉ mới xác minh ngoại tuyến qua `MockLLMProvider` (`AWAITING_FINAL_TRACK2_EXECUTION_APPROVAL`).
