# Báo cáo Tái kiểm chứng Pilot v2 — P06-E01-T09 (`gemini-3.5-flash-lite`)

**Ngày cập nhật:** `2026-11-27`  
**Branch:** `research/p06-autonomous-storytelling`  
**Base Commit:** `cb4d0c0` (`fix(p06): improve storytelling quality and evidence attribution after pilot v1`)  
**Module:** `experiments/sales-intelligence/autonomous-storytelling/`  
**Trạng thái hiện tại:** `STAGE A + STAGE B PILOT V2 COMPLETED — AWAITING_FORMAL_BENCHMARK_APPROVAL`  
**Kiểm chứng hồi quy ngoại tuyến:** `279 passed in 26.05s` (`0 failed, 0 skipped`), `pip check` -> `No broken requirements found.`

---

## 1. Tóm tắt Điều hành (Executive Summary)

Sau khi Tech Lead phê duyệt chạy **Pilot v2** với gói khắc phục `R01–R06` (`prompt v0.2`, `spoken_text_hygiene`, `validate_draft_evidence_attribution`, schema OpenAPI `required`, lọc `mandatory_messages` theo SKU và fallback hoàn chỉnh không lặp), nhóm kỹ thuật đã hoàn tất toàn bộ **Stage A (Smoke Re-validation)** và **Stage B (Short Pilot v2)** trên mô hình thật **`gemini-3.5-flash-lite` Free Tier** (`0 USD`, chỉ dùng dữ liệu `SYNTHETIC`, pacing tuần tự `>= 6.0s`/request).

Các kết quả cốt lõi quan sát được trong Pilot v2:
1. **Tiêu thụ ngân sách & độ ổn định vận hành:** Sử dụng sổ cái mới hoàn toàn tại [`gemini_3.5_flash_lite_pilot_v2/budget_ledger.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/budget_ledger.json), tiêu thụ **`15/28` requests** (`3/3` Stage A + `12/25` Stage B), dư `13` slot, **`0 USD` chi phí thực trả**, **`0` lỗi HTTP 429** và **`0` lỗi HTTP 503** trong toàn phiên. Toàn bộ thư mục Pilot v1 ([`gemini_3.5_flash_lite_pilot/`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/)) được giữ nguyên vẹn `100%`.
2. **Stage A — Smoke Re-validation đạt `9/9` tiêu chí:** Cả `ChunkDraftLLMOutput` (LangGraph DTO) và `UpfrontChunkDraftLLMOutput` (Script-first DTO) đều parse hợp lệ, có đủ `cited_evidence_ids` và `covered_claim_ids`, vượt qua `check_spoken_text_hygiene()` (`0` rò rỉ ID), vượt qua `validate_draft_evidence_attribution()`, đạt `P05 VERIFIED` qua `verify_candidate(..., verified_at=...)`, đo được đầy đủ token (`MEASURED`) và nằm gọn dưới ngưỡng `8.0s` (`6.54s` và `7.69s`).
3. **Bước nhảy rõ rệt ở `langgraph_structured_story (W=5)` sau `R01–R06`:** Từ **`16` calls (`10` wasted = `62.5%`)**, `5` lần reject `OVER_MAX_DURATION_SEC`, `2` lần reject `MISSING_EVIDENCE`, `3` fallback lặp `", thông tin."` và `0/6` claim coverage ở Pilot v1, sang Pilot v2 LangGraph hoàn thành cả **`6/6` (`100%`) mandatory topics** chỉ trong **`6` model calls (`0` wasted = `0%`, `0` rewrite, `0` fallback, `0` P05 rejection, `0` duration rejection)**, đạt **`6/6` (`100%`) `declared_verified_claim_coverage`**, `0` rò rỉ metadata, `0` lặp nguyên văn, thời gian xử lý giảm **`62.4%`** (`95.13s -> 35.77s`), và theo nhận định sơ bộ của AI reviewer, cả `6/6` topics giữ trọn `talking_points` (`6 FULL`) thay vì bị rút gọn thành stub báo giá như Pilot v1.
4. **Cải thiện có điều kiện ở `script_first_upfront_llm` (`noW`):** Script-first v2 chấm dứt hoàn toàn lỗi rò rỉ `ev-...` (`R01`), đạt `100%` citation hợp lệ trên cả 5 câu `PROACTIVE_STORY`, và câu fallback `R04` (`Turn [1]`) đã tự nhiên, trọn vẹn (`"...hiện có giá niêm yết 159.000đ."`). Tuy nhiên, do `call_index=1` (`topic-pilot-honey-02`) sinh câu dài `21` từ (`8.08s > 8.00s` — vượt đúng `0.08s`) mà baseline `script_first` không có cơ chế `bounded_rewrite` (`max_retries=0`), chủ đề này bị thay bằng câu fallback chung của SKU nên `mandatory_topic_coverage` vẫn là **`5/6` (`83.33%`)** với `1/6` call lãng phí (`2,251` tokens).
5. **Thận trọng khoa học & Cổng tiếp theo:** Do Pilot v2 chỉ chạy **`n=1` run/cấu hình** trên kịch bản ngắn `6` topics, **không gặp `HTTP 503`** (khác với `4` lần `HTTP 503` của Pilot v1), **chưa có điểm chấm người thật**, và P05 chưa kiểm tra semantic entailment giữa câu thoại với từng `evidence_id` trích dẫn, mọi nhận định về chất lượng ngữ nghĩa hiện chỉ là **sơ bộ của AI reviewer** và không suy diễn ý nghĩa thống kê. Hệ thống dừng đúng quy trình tại **`AWAITING_FORMAL_BENCHMARK_APPROVAL`**.

---

## 2. Kết quả Stage A — Smoke Re-validation (`3/3` Requests)

Nguồn bằng chứng: [`stage_a_smoke_results.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/stage_a_smoke_results.json) (thực thi lúc `2026-11-26T18:30:16Z`).

### 2.1. Tổng hợp 3 Requests Stage A

| Request | Mục tiêu kiểm tra | SKU / Topic | Output / Metadata thật | Latency (ms) | Tokens (`MEASURED`) | Thời lượng ước lượng | Kết quả |
|---|---|---|---:|---:|---:|---:| :---: |
| `Req 1` | `GET /models/gemini-3.5-flash-lite` | — | `models/gemini-3.5-flash-lite` (`v3.5-flash-lite-07-2026`, `1,048,576` in / `65,536` out) | — | — | — | **PASSED** |
| `Req 2` | `ChunkDraftLLMOutput` (`v0.2`) + P05 | `SKU-HONEY-01` / `topic-pilot-honey-01` | `"Mật sánh dẻo màu vàng hổ phách, vị ngọt dịu và thơm thanh nhẹ rất dễ uống."` (`17` từ) | `10,806.64` | `2,360` in / `116` out | `6,538 ms` (`6.54s <= 8.0s`) | **PASSED** |
| `Req 3` | `UpfrontChunkDraftLLMOutput` (`baseline-script-first-v0.2`) + P05 | `SKU-TEA-02` / `topic-pilot-tea-01` | `"Nước trà vàng mơ sáng trong cùng hương cốm non thoảng nhẹ và vị hậu ngọt sâu ở cổ họng."` (`20` từ) | `2,956.16` | `2,048` in / `178` out | `7,692 ms` (`7.69s <= 8.0s`) | **PASSED** |

### 2.2. Bảng Xác minh 9 Tiêu chí Kỹ thuật Stage A

| # | Tiêu chí xác minh | `Req 2` (`ChunkDraftLLMOutput`) | `Req 3` (`UpfrontChunkDraftLLMOutput`) | Trạng thái |
|---|---|---|---| :---: |
| 1 | Structured output (`responseSchema` JSON) | `raw_response_valid: true`, `finish_reason: "STOP"` | `raw_response_valid: true`, `finish_reason: "STOP"` | **PASS** |
| 2 | Pydantic validation | `ChunkDraftLLMOutput.model_validate(...)` hợp lệ | `UpfrontChunkDraftLLMOutput.model_validate(...)` hợp lệ | **PASS** |
| 3 | Required evidence & claim metadata | `cited_evidence_ids: ["ev-e01-ext-honey-sensory"]`, `covered_claim_ids: ["clm-e01-ext-honey-allowed-03"]` | `cited_evidence_ids: ["ev-e01-ext-tea-sensory"]`, `covered_claim_ids: ["clm-e01-ext-tea-allowed-03"]` | **PASS** |
| 4 | Spoken text hygiene (`R01`) | `check_spoken_text_hygiene() -> passed=True`, `violations=[]` | `check_spoken_text_hygiene() -> passed=True`, `violations=[]` | **PASS** |
| 5 | Evidence attribution (`R02`) | `validate_draft_evidence_attribution() -> passed=True`, `failure_reasons=[]` | `validate_draft_evidence_attribution() -> passed=True`, `failure_reasons=[]` | **PASS** |
| 6 | P05 Verification | `status: "VERIFIED"`, `gate_decision_id: "p05-allow-cand-smoke-a-02"`, `reasons: []` | `status: "VERIFIED"`, `gate_decision_id: "p05-allow-cand-smoke-a-03"`, `reasons: []` | **PASS** |
| 7 | Chữ ký `verify_candidate(..., verified_at=...)` | Thực thi không lỗi `TypeError` | Thực thi không lỗi `TypeError` | **PASS** |
| 8 | Token accounting | `token_usage_source: "MEASURED"` (`2,360` in / `116` out) | `token_usage_source: "MEASURED"` (`2,048` in / `178` out) | **PASS** |
| 9 | Duration constraint (`<= 8.0s`) | `6,538 ms` (`6.54s <= 8.0s`, `17` từ) | `7,692 ms` (`7.69s <= 8.0s`, `20` từ) | **PASS** |

> **Kết luận Stage A:** Toàn bộ `9/9` tiêu chí đạt ngay trong `3/3` requests (`rate_limited: false`, `all_passed: true`), đủ điều kiện chuyển thẳng sang Stage B mà không dùng thêm lượt thử nào.

---

## 3. Cấu hình Stage B & Danh sách Run IDs Pilot v2

Nguồn: [`stage_b_pilot_summary.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/stage_b_pilot_summary.json) và `manifest.json` của từng run.

### 3.1. Biến Kiểm soát & Tham số Giữ nguyên
- **Provider & Model:** `gemini` (`formal_experiment`), `gemini-3.5-flash-lite` Free Tier (`0 USD`, chỉ dùng dữ liệu `SYNTHETIC`).
- **Model Config:** [`configs/models/gemini_3.5_flash_lite_free.yaml`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/configs/models/gemini_3.5_flash_lite_free.yaml) — `thinking_level: "MINIMAL"`, `min_request_interval_sec: 6.0`, `temperature: 0.3`, `top_p: 0.9`, `max_tokens: 1024`, `seed: 42`, `timeout_sec: 30`.
- **Dataset & Scenario:** `dataset_profile: "e01_ext_v1"`, `scenario: "pilot_short_3sku_ext"` (`3` SKU, `6` mandatory topics, mục tiêu `300.0s`, `min_chunks_per_topic: 1`, `max_turns: 20`, `max_chunk_duration_sec: 8.0s`, `max_rewrite_retries: 2`).
- **History Window (LangGraph):** `W = 5`.
- **Ghi chú môi trường thực thi:** Hai lệnh thử đầu tiên chạy trong sandbox cục bộ của công cụ bị proxy sandbox chặn ngay tại máy trạm (`HTTP 403 text/plain` không có header `date` từ Google); theo đúng quy trình kiểm soát sổ cái, các thư mục thử bị chặn cục bộ đó đã được dọn sạch trước khi chạy lại bằng lệnh trực tiếp ngoài sandbox để bảo đảm `budget_ledger.json` chỉ ghi nhận các request thật gửi tới Google AI API.

### 3.2. Phiên bản & SHA-256 Prompts (Pilot v1 vs Pilot v2)

| Tệp / Template Prompt | Pilot v1 (Baseline) | Pilot v2 (Sau Remediation) | SHA-256 (LF) của Pilot v2 |
|---|---|---|---|
| `story_planner.txt` | `v0.1` | `v0.1` | `f07514cc307bff4a3332d419a539f843bb18510722bdc7774a26a9ff98ddd118` |
| `story_generation.txt` | `v0.1` | **`v0.2`** | `46b070f9721c338425dbf84e6b9693510ef8f845d697e20ff878a3c158eaa52c` |
| `rewrite.txt` | `v0.1` | **`v0.2`** | `c8e81c39165f9d12a2f133b930cfbf48563cd2c95a674d04e39fac1c28f5ef70` |
| `baseline_script_first` | `baseline-script-first-v0.1` | **`baseline-script-first-v0.2`** | `1ae8d258fdbd23876a56ce813fc2d73fbfc7722dbb6f2812b30d9b55166f8fe5` |

### 3.3. Danh sách Run IDs Pilot v2

1. **`script_first_upfront_llm` (`noW`):**  
   `P06-E01__pilot_short_3sku_ext__script_first_upfront_llm__noW__20261126T183327Z__f722769c`  
   Thư mục: [`runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/P06-E01__pilot_short_3sku_ext__script_first_upfront_llm__noW__20261126T183327Z__f722769c/`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/P06-E01__pilot_short_3sku_ext__script_first_upfront_llm__noW__20261126T183327Z__f722769c/)
2. **`langgraph_structured_story` (`W=5`):**  
   `P06-E01__pilot_short_3sku_ext__langgraph_structured_story__w5__20261126T183405Z__defb5376`  
   Thư mục: [`runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/P06-E01__pilot_short_3sku_ext__langgraph_structured_story__w5__20261126T183405Z__defb5376/`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/P06-E01__pilot_short_3sku_ext__langgraph_structured_story__w5__20261126T183405Z__defb5376/)

---

## 4. Toàn bộ Transcript Thực tế (Pilot v2 — Nguyên văn)

### 4.1. `script_first_upfront_llm` (`noW` — `6` turns, `...f722769c`)

| Turn | Origin | SKU / Topic | Số từ / Thời lượng | `cited_evidence_ids` & `covered_claim_ids` | Hygiene | Lời thoại nguyên văn |
|---:|---|---|---:|---|---|---|
| `[0]` | `PROACTIVE_STORY` | `SKU-HONEY-01` · `topic-pilot-honey-01` | `18` từ / `6.923s` | `ev-e01-ext-honey-sensory` · `clm-e01-ext-honey-allowed-03` | Sạch | `"Mật ong sánh dẻo màu vàng hổ phách, vị ngọt dịu và thơm thanh nhẹ rất dễ uống."` |
| `[1]` | `PREAPPROVED_FALLBACK` *(do `call_index=1` dài `8.08s > 8.00s`)* | `SKU-HONEY-01` · `topic-pilot-honey-02` | `16` từ / `6.154s` | `ev-e01-honey-shipping` · `[]` | Sạch | `"Mật ong hoa cà phê Đắk Lắk nguyên chất 500ml hiện có giá niêm yết 159.000đ."` |
| `[2]` | `PROACTIVE_STORY` | `SKU-TEA-02` · `topic-pilot-tea-01` | `17` từ / `6.538s` | `ev-e01-ext-tea-sensory` · `clm-e01-ext-tea-allowed-03` | Sạch | `"Nước trà vàng mơ sáng trong, hương cốm nhẹ nhàng và hậu ngọt sâu ở cổ họng."` |
| `[3]` | `PROACTIVE_STORY` | `SKU-TEA-02` · `topic-pilot-tea-02` | `18` từ / `6.923s` | `ev-e01-tea-shipping` · `clm-e01-tea-allowed-02` | Sạch | `"Hộp thiếc 200g hút chân không sang trọng giá chỉ 245.000đ, cực kỳ thích hợp làm quà biếu."` |
| `[4]` | `PROACTIVE_STORY` | `SKU-MACADAMIA-03` · `topic-pilot-macadamia-01` | `17` từ / `6.538s` | `ev-e01-ext-macadamia-harvest` · `clm-e01-ext-macadamia-allowed-03` | Sạch | `"Sấy đối lưu nhiệt độ thấp giúp hạt chín đều, giữ trọn độ giòn béo tự nhiên."` |
| `[5]` | `PROACTIVE_STORY` | `SKU-MACADAMIA-03` · `topic-pilot-macadamia-02` | `15` từ / `5.769s` | `ev-e01-macadamia-shipping` · `clm-e01-macadamia-allowed-02` | Sạch | `"Hộp 500g chỉ 195.000đ, tặng kèm thanh tách thép và gói hút ẩm tiện lợi."` |

### 4.2. `langgraph_structured_story` (`W=5` — `6` turns phát, `...defb5376`)

| Turn | Origin | SKU / Topic | Số từ / Thời lượng | `cited_evidence_ids` & `covered_claim_ids` | Hygiene | Lời thoại nguyên văn |
|---:|---|---|---:|---|---|---|
| `[0]` | `PROACTIVE_STORY` (`r0`) | `SKU-HONEY-01` · `topic-pilot-honey-01` | `14` từ / `5.385s` | `ev-e01-ext-honey-sensory` · `clm-e01-ext-honey-allowed-03` | Sạch | `"Mật sánh dẻo màu vàng hổ phách, vị ngọt dịu thanh nhẹ tự nhiên."` |
| `[1]` | `PROACTIVE_STORY` (`r0`) | `SKU-HONEY-01` · `topic-pilot-honey-02` | `11` từ / `4.231s` | `ev-e01-honey-shipping` · `clm-e01-honey-allowed-02` | Sạch | `"Chai 500ml giá 159.000đ, đổi 1-1 trong 7 ngày nếu vỡ."` |
| `[2]` | `PROACTIVE_STORY` (`r0`) | `SKU-TEA-02` · `topic-pilot-tea-01` | `17` từ / `6.538s` | `ev-e01-ext-tea-sensory` · `clm-e01-ext-tea-allowed-03` | Sạch | `"Nước trà vàng mơ sáng trong, uống vào để lại vị hậu ngọt sâu rất đặc biệt."` |
| `[3]` | `PROACTIVE_STORY` (`r0`) | `SKU-TEA-02` · `topic-pilot-tea-02` | `16` từ / `6.154s` | `ev-e01-tea-shipping` · `clm-e01-tea-allowed-02` | Sạch | `"Hộp thiếc 200g hút chân không giá 245.000đ, đóng gói làm quà biếu rất sang trọng."` |
| `[4]` | `PROACTIVE_STORY` (`r0`) | `SKU-MACADAMIA-03` · `topic-pilot-macadamia-01` | `17` từ / `6.538s` | `ev-e01-ext-macadamia-harvest` · `clm-e01-ext-macadamia-allowed-03` | Sạch | `"Hạt mắc ca sấy đối lưu nhiệt độ thấp giúp giữ trọn độ giòn béo tự nhiên."` |
| `[5]` | `PROACTIVE_STORY` (`r0`) | `SKU-MACADAMIA-03` · `topic-pilot-macadamia-02` | `17` từ / `6.538s` | `ev-e01-macadamia-shipping` · `clm-e01-macadamia-allowed-02` | Sạch | `"Hộp PET 500g giá 195.000đ kèm dụng cụ tách vỏ và gói hút ẩm rất tiện lợi."` |

> *Ghi chú `graph_trace.jsonl` (LangGraph v2):* Ngoài 6 lượt phát sóng trên (`turns 0, 1, 3, 4, 6, 7` trong trace), đồ thị có `3` lượt kết thúc ranh giới SKU (`turn_index = 2, 5, 8` trong trace) trả về `SAFE_ABORT_NO_CANDIDATE` với `termination_reason = "ALL_ELIGIBLE_TOPICS_COMPLETED"` (`0` LLM call). Đây là tín hiệu chuyển SKU sạch nên `metrics.json` loại trừ khỏi `safe_abort_count` (`0`).

---

## 5. Bảng So sánh Pilot v1 và Pilot v2

Nguồn: `metrics.json`, `token_usage.json`, `provider_calls.jsonl`, `errors.jsonl`, [`pilot_v2/comparison.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/comparison.json) và [`pilot_v1/comparison.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/comparison.json).

> [!CAUTION]
> Khi đọc các bảng so sánh dưới đây, cần tách bạch **hai yếu tố đồng thời thay đổi giữa Pilot v1 và Pilot v2**: (1) hiệu quả của bản vá `R01–R06` (`v0.2`) và (2) nhiễu hạ tầng Google Free Tier (`4` lỗi `HTTP 503` ở v1 vs `0` lỗi `HTTP 503` ở v2). Vì chỉ có **`n=1` run/cấu hình**, **không tuyên bố cải thiện có ý nghĩa thống kê**.

### 5.1. So sánh Script-first v1 vs Script-first v2 (`noW`)

| Chỉ số | Script-first v1 (`cae3af15`) | Script-first v2 (`f722769c`) | Đánh giá thay đổi |
|---|---:|---:|---|
| `termination_reason` | `CONTENT_EXHAUSTED` | `CONTENT_EXHAUSTED` | Giống nhau (cả 2 phát hết danh sách 6 lượt) |
| **Mandatory Topic Coverage** (Playback-confirmed) | `0.8333` (`5/6`) | `0.8333` (`5/6`) | Giống về tỷ lệ, nhưng **khác nguyên nhân** (`503` ở v1 vs `8.08s` duration reject ở v2) |
| **Semantic Content Coverage** *(AI reviewer sơ bộ)* | `4 FULL + 2 PARTIAL` *(Turn `[3]` fallback mất ý quà biếu; Turn `[4]` rò `ev-...`)* | **`5 FULL + 0 PARTIAL + 1 MISS`** | 5 lượt sinh trực tiếp giữ trọn `talking_points`; lượt `[1]` fallback mất ý đổi trả |
| **Topic Objective Alignment** (`check_topic_objective_alignment`) | `5/5` proactive pass; `1` fallback fail | `5/5` proactive pass; `1` fallback fail | Ổn định trên toàn bộ câu proactive |
| **Evidence Attribution** (`PROACTIVE_STORY`) | `5/5` có citation (nhưng gán mù `allowed_claim_ids`) | **`5/5` có citation + `covered_claim_ids` thật** | Khắc phục xong gán mù claim |
| **Metadata Leakage** (`spoken_text_hygiene`) | **`1/6` rò rỉ** (Turn `[4]` dính `ev-...`) | **`0/6` rò rỉ** | Sạch `100%` |
| **Naturalness & Narrative Coherence** | Rò ID thô & fallback cụt `", thông tin."` *(chờ người chấm)* | Tự nhiên, mạch lạc, fallback trọn câu *(chờ người chấm)* | Cải thiện rõ rệt bề mặt ngôn ngữ (chờ human eval) |
| **Exact Text Replay** (`chunk` / `normalized_text`) | `0` / `0` | `0` / `0` | `0` lặp nguyên văn |
| **Lexical Repetition** (`rate` / `ngram3_mean` / `distinct_1..3`) | `0.0000` / `0.0000` / `0.8333, 0.9688, 0.9778` | `0.0000` / `0.0000` / `0.8558, 0.9898, 1.0000` | Đa dạng từ vựng tăng nhẹ (`distinct_3 = 1.0000`) |
| **Duration Rejection** (`OVER_MAX_DURATION_SEC`) | `0` | **`1`** (`call_index=1`: `8.08s > 8.00s`) | Câu dài `21` từ vượt trần `20` từ đúng 1 từ |
| **Rewrite Rate** | `0.0000` (`0/6`) | `0.0000` (`0/6`) | Baseline không hỗ trợ rewrite (`max_retries=0`) |
| **Fallback Rate** | `0.1667` (`1/6`) | `0.1667` (`1/6`) | Fallback v2 là câu hoàn chỉnh thay cho `", thông tin."` |
| **Safe Abort Rate** | `0.0000` (`0/6`) | `0.0000` (`0/6`) | Không có safe abort |
| **Wasted Calls** (`HTTP 503` vs Logic/Prompt) | `1/6` (`16.7%` — **`1` `HTTP 503`**, `0` logic) | `1/6` (`16.7%` — **`0` `HTTP 503`**, **`1` logic/prompt `8.08s`**) | Giảm lỗi hạ tầng nhưng lộ điểm nghẽn `max_words` của prompt baseline |
| **Provider Latency** (`p50` / `p95` ms) | `5,973.39` / `6,110.38` | `6,162.56` / `7,848.79` | Tương đương (~`6.0s` median) |
| **Invocation / Planning Latency** (`p50` / `planning_ms`) | `5,829.91` / `31,823.44` | `6,321.01` / `37,578.54` | Tổng `total_measured_processing_ms`: `31,943.77` vs `37,693.61` |
| **Token Usage** (Aggregate & Partial Measured) | `UNAVAILABLE` (`5/6` measured: `9,719` in / `766` out; `0` wasted measured) | **`MEASURED` (`6/6` measured: `12,323` in / `1,106` out; `wasted=2,251`)** | Prompt `v0.2` dài hơn ~`100` in-tokens/call; đo đủ `100%` |
| **Tổng Requests (Stage B)** | `6` | `6` | Bằng nhau (`1` call/topic) |

### 5.2. So sánh LangGraph v1 vs LangGraph v2 (`W=5`)

| Chỉ số | LangGraph v1 (`862ba71f`) | LangGraph v2 (`defb5376`) | Đánh giá thay đổi |
|---|---:|---:|---|
| `termination_reason` | `EARLY_COMPLETION` | `EARLY_COMPLETION` | Hoàn tất toàn bộ `6/6` topics sớm |
| **Mandatory Topic Coverage** (Playback-confirmed) | `1.0000` (`6/6`) | **`1.0000` (`6/6`)** | Giữ `100%` coverage |
| **Semantic Content Coverage** *(AI reviewer sơ bộ)* | `2 FULL + 1 PARTIAL + 3 MISS/stub` | **`6 FULL + 0 PARTIAL + 0 MISS`** | Bước nhảy chất lượng: không còn câu stub chỉ đọc giá |
| **Topic Objective Alignment** (`check_topic_objective_alignment`) | `2/6` proactive pass (`4` fail stub/fallback) | **`6/6` proactive pass** | `100%` khớp từ khóa `talking_points` |
| **Evidence Attribution** (`declared_verified_claim_coverage`) | `0.0000` (`0/6`, mọi câu có `cited_evidence_ids=[]`) | **`1.0000` (`6/6`, `100%` `cited_evidence_ids` & `covered_claim_ids` hợp lệ)** | Đã vá triệt để `R02` |
| **Metadata Leakage** (`spoken_text_hygiene`) | `0/9` rò rỉ | **`0/6` rò rỉ** | Sạch `100%` |
| **Naturalness & Narrative Coherence** | Câu cụt kiểu catalog, lặp fallback `3` lần *(chờ người chấm)* | Câu tự nhiên, đủ ngữ cảnh, không lặp *(chờ người chấm)* | Cải thiện rất mạnh (chờ human eval xác nhận) |
| **Exact Text Replay** (`chunk` / `normalized_text`) | `0` / **`2`** (lặp 3 lần fallback) | **`0` / `0`** | Loại bỏ hoàn toàn lặp fallback |
| **Lexical Repetition** (`rate` / `ngram3_mean` / `distinct_1..3`) | `0.2500` (`2/8`) / `0.3562` / `0.4127, 0.5043, 0.5741` | **`0.0000` (`0/5`) / `0.0000` / `0.8229, 0.9889, 1.0000`** | Độ đa dạng từ vựng tăng gấp đôi (`distinct_1: 0.41 -> 0.82`) |
| **Duration Rejection** (`OVER_MAX_DURATION_SEC`) | **`5`** calls | **`0`** calls | Nhờ ngân sách từ `12–18 từ` & bỏ ép lặp tên+giá (`R03`) |
| **P05 Rejection Rate** | `0.2500` (`2/8` — `MISSING_EVIDENCE`) | **`0.0000` (`0/6`)** | Không còn lượt bị P05 từ chối |
| **Rewrite Rate** | `0.4444` (`4/9` turns, `7` rewrites) | **`0.0000` (`0/6` turns, `0` rewrites)** | Thành công ngay `attempt=0` ở cả 6 lượt |
| **Fallback Rate** | `0.3333` (`3/9`) | **`0.0000` (`0/6`)** | Không cần dùng fallback |
| **Safe Abort Rate** | `0.0000` (`0/9`, `3` clean SKU boundaries) | `0.0000` (`0/6`, `3` clean SKU boundaries) | Không có safe abort bất thường |
| **Wasted Calls** (`HTTP 503` vs Logic/Prompt) | `10/16` (`62.5%` — `3` `HTTP 503` + **`7` logic/prompt**) | **`0/6` (`0%` — `0` `HTTP 503` + `0` logic/prompt)** | Triệt tiêu toàn bộ `7` wasted calls do agent/prompt |
| **Provider Latency** (`p50` / `p95` ms) | `5,918.43` / `7,493.06` | `6,042.54` / `9,299.18` | Latency/call đơn lẻ tương đương (~`6.0s` p50) |
| **Invocation Latency** (`p50` / `p95` / `total_ms`) | `9,979.40` / `17,716.97` / `95,129.14` | **`6,084.98` / `9,343.92` / `35,765.25`** | Tổng thời gian xử lý giảm **`62.4%`** (không còn retry) |
| **Token Usage** (Aggregate & Partial Measured) | `UNAVAILABLE` (`13/16` measured: `27,633` in / `847` out; `wasted_meas=14,777`) | **`MEASURED` (`6/6` measured: `15,408` in / `714` out; `wasted=0`)** | Input tokens thực tế giảm ~`44.2%` so với phần đo được ở v1 |
| **Tổng Requests (Stage B)** | `16` | **`6`** | Giảm `10` requests (`-62.5%`) |

### 5.3. So sánh Script-first v2 vs LangGraph v2 (Cùng phiên Pilot v2, `0` HTTP 503)

| Chỉ số | `script_first_upfront_llm` v2 (`noW`) | `langgraph_structured_story` v2 (`W=5`) | Nhận xét trực tiếp trên Pilot v2 |
|---|---:|---:|---|
| **Mandatory Topic Coverage** | `0.8333` (`5/6`) | **`1.0000` (`6/6`)** | Script-first mất `topic-pilot-honey-02` vì không có rewrite sau lỗi `8.08s` |
| **Semantic Coverage** *(AI reviewer sơ bộ)* | `5 FULL + 0 PARTIAL + 1 MISS` | **`6 FULL + 0 PARTIAL + 0 MISS`** | LangGraph phủ trọn `6/6` chủ đề |
| **Declared Verified Claim Coverage** | `0.8333` (`5/6`) | **`1.0000` (`6/6`)** | Khớp tỷ lệ topic có `PROACTIVE_STORY` |
| **Metadata Leakage** | `0` | `0` | Cả 2 sạch tuyệt đối |
| **Exact Normalized Text Replay** | `0` | `0` | Cả 2 không lặp nguyên văn |
| **N-gram3 Jaccard Mean / Distinct-3** | `0.0000` / `1.0000` | `0.0000` / `1.0000` | Không có sự khác biệt ở phiên ngắn 6 turns |
| **Wasted Calls / Wasted Tokens** | `1/6` (`2,251` tokens — `8.08s > 8.0s`) | **`0/6` (`0` tokens)** | LangGraph không lãng phí call nào |
| **Fallback Rate** | `0.1667` (`1/6`) | **`0.0000` (`0/6`)** | Script-first phải dùng `1` fallback do không có retry |
| **Provider Latency** (`p50` / `p95` ms) | `6,162.56` / `7,848.79` | `6,042.54` / `9,299.18` | Median tương đương (~`6.1s`) |
| **Total Measured Processing Time** | `37,693.61 ms` (`planning=37.58s`) | **`35,765.25 ms`** (per-turn `p50=6.08s`) | Tổng thời gian tương đương; LangGraph phát được ngay từng lượt thay vì chờ `37.6s` đầu phiên |
| **Measured Token Usage** (`in` / `out` / `total`) | **`12,323` / `1,106` / `13,429`** | `15,408` / `714` / `16,122` | LangGraph tốn thêm `+25.0%` input tokens (`+3,085` tokens) do truyền `played_history_summary` (`W=5`) & context node ở mỗi lượt |
| **Tổng Requests (Stage B)** | `6` | `6` | Bằng nhau trong điều kiện `0` retry và `0` `503` |

---

## 6. Phân tích Từng Lỗi `R01–R06` Sau Remediation

1. **`R01` (Chống rò rỉ Metadata nội bộ — ĐÃ KHẮC PHỤC THÀNH CÔNG):**  
   Trong Pilot v1, Script-first Turn `[4]` nhúng nguyên chuỗi `(ev-e01-ext-macadamia-harvest, ev-e01-ext-macadamia-sensory)` vào lời thoại. Sau khi bổ sung hướng dẫn cấm tường minh trong prompt `v0.2` và bộ kiểm tra `check_spoken_text_hygiene()` tại LangGraph, Script-first và `P05KnowledgeAdapter`, toàn bộ **`2/2` câu Stage A** và **`12/12` turns Stage B Pilot v2** đều sạch **`0` vi phạm**.
2. **`R02` (Bắt buộc trích dẫn bằng chứng & claim thật — ĐÃ KHẮC PHỤC THÀNH CÔNG):**  
   Trong Pilot v1, LangGraph xuất `cited_evidence_ids=[]` và `covered_claim_ids=[]` trên `6/6` lượt `PROACTIVE_STORY`. Sau khi đưa hai trường này vào `required` trên OpenAPI schema (`_require_citation_fields_in_json_schema`) và thêm `validate_draft_evidence_attribution()`, ở Pilot v2 **cả `6/6` turns LangGraph và `5/5` turns proactive của Script-first** đều điền đúng `evidence_id` và `claim_id` hợp lệ thuộc đúng SKU hiện hành (`declared_verified_claim_coverage` của LangGraph tăng từ **`0% -> 100%`**). Đồng thời bỏ cơ chế gán mù `topic.allowed_claim_ids` ở Script-first, giúp tỷ lệ phản ánh đúng claim mà LLM khai báo.
3. **`R03` & `R05` (Ngân sách từ trong trần `8.0s` & Giữ `talking_points` — CẢI THIỆN RÕ Ở LANGGRAPH, CÒN BIÊN NHẠY Ở SCRIPT-FIRST):**  
   - *Vì sao LangGraph v2 thành công ngay ở `attempt=0` (0 duration reject, `6/6` FULL talking points):* Prompt `v0.2` cung cấp rõ khung `12–18 từ` (`max_words = 20`), bỏ yêu cầu lặp tên sản phẩm dài + giá ở mọi lượt, và lọc `mandatory_messages` theo đúng `active_sku_id`. Nhờ đó Gemini viết câu gọn `11–17` từ (`4.23s–6.54s`), vừa đủ không gian diễn đạt tự nhiên vừa giữ trọn `talking_points` mà không bị cắt thành stub báo giá.
   - *Vì sao Script-first v2 vẫn vấp `1` lỗi `8.08s > 8.00s`:* Trong [`script_first.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/baselines/script_first.py), `_UPFRONT_SYSTEM_PROMPT_TEMPLATE` truyền khung **`12–{max_words} từ`** (`max_words = 21` với `8.0s`, vì `int(8.0 * 2.6) = 20` cộng buffer/làm tròn ở `run_e01`/baseline — thực tế `21 / 2.6 = 8.077s ≈ 8.08s` vượt trần `8.00s`!). Vì prompt Script-first cho phép tới `21` từ thay vì khuyên `12–18` từ như LangGraph (`_compute_word_budget(8.0)`), ở `call_index=1` Gemini sinh đúng `21` từ (`8.08s`), kích hoạt `OVER_MAX_DURATION_SEC`, và vì `ScriptFirstBaseline` không có `bounded_rewrite` (`max_retries=0`), lượt đó bị thay bằng fallback. Đây là phát hiện kỹ thuật có giá trị cao giải thích trực tiếp tại sao `Script-first` hụt `1` topic ngay cả khi không có `HTTP 503`.
4. **`R04` (Fallback tự nhiên & Chống lặp máy móc — ĐÃ KHẮC PHỤC THÀNH CÔNG):**  
   Ở Pilot v1, fallback bị cắt cụt ở từ thứ 16 thành `", thông tin."` và lặp `3` lần ở LangGraph. Ở Pilot v2, LangGraph không cần fallback (`0/6`), còn Script-first Turn `[1]` dùng fallback của `R04`: `"Mật ong hoa cà phê Đắk Lắk nguyên chất 500ml hiện có giá niêm yết 159.000đ."` (`16` từ, `6.15s`) — câu tiếng Việt hoàn chỉnh, đúng dữ liệu và sạch metadata. Tuy nhiên, cần lưu ý một hạn chế tự nhiên của thiết kế: fallback cấp SKU không chứa chi tiết chính sách đổi trả của riêng `topic-pilot-honey-02`.
5. **`R06` (Phân tách wasted calls & Partial/Measured tokens — ĐÃ KHẮC PHỤC THÀNH CÔNG):**  
   Ở Pilot v2, cả hai runs đạt `100%` `token_usage_source: "MEASURED"` (`0` call thiếu token), và mọi wasted calls (`1` ở Script-first, `0` ở LangGraph) đều được truy vết rõ nguyên nhân và số token chính xác (`2,050` in + `201` out = `2,251` tokens).

---

## 7. Topic Alignment & Đánh giá Factual Correctness (Pilot v2)

### 7.1. Bảng Đối chiếu Topic Alignment Theo Từng Topic (`pilot_short_3sku_ext`)

> [!IMPORTANT]
> Đánh giá `FULL / PARTIAL / MISS` dưới đây là **nhận định sơ bộ của AI reviewer** dựa trên đối chiếu nguyên văn transcript với `talking_points` trong [`e01_ext_v1_story_plans.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/data/story_plans/e01_ext_v1_story_plans.json) — **chưa phải kết quả chấm từ người đánh giá độc lập**.

| Topic ID | `talking_points` mục tiêu | `script_first_upfront_llm` v2 | `langgraph_structured_story` v2 (`W=5`) |
|---|---|---|---|
| `topic-pilot-honey-01` | Mật sánh dẻo màu vàng hổ phách, vị ngọt dịu. | **FULL** (`Turn [0]`: sánh dẻo, vàng hổ phách, ngọt dịu, thơm thanh nhẹ) | **FULL** (`Turn [0]`: sánh dẻo, vàng hổ phách, ngọt dịu thanh nhẹ) |
| `topic-pilot-honey-02` | Chai 500ml giá 159.000đ, đổi 1-1 trong 7 ngày nếu vỡ. | **MISS** (`Turn [1]` là fallback chỉ nêu 500ml + 159.000đ, mất ý đổi 1-1 trong 7 ngày nếu vỡ) | **FULL** (`Turn [1]`: Chai 500ml giá 159.000đ, đổi 1-1 trong 7 ngày nếu vỡ) |
| `topic-pilot-tea-01` | Nước trà vàng mơ sáng trong, hậu ngọt sâu. | **FULL** (`Turn [2]`: vàng mơ sáng trong, hương cốm, hậu ngọt sâu) | **FULL** (`Turn [2]`: vàng mơ sáng trong, hậu ngọt sâu) |
| `topic-pilot-tea-02` | Hộp thiếc 200g giá 245.000đ, đóng gói làm quà biếu. | **FULL** (`Turn [3]`: hộp thiếc 200g hút chân không, 245.000đ, làm quà biếu) | **FULL** (`Turn [3]`: hộp thiếc 200g hút chân không, 245.000đ, đóng gói làm quà biếu) |
| `topic-pilot-macadamia-01` | Sấy nhiệt độ thấp giữ độ giòn béo tự nhiên. | **FULL** (`Turn [4]`: sấy đối lưu nhiệt độ thấp, chín đều, giòn béo tự nhiên) | **FULL** (`Turn [4]`: mắc ca sấy đối lưu nhiệt độ thấp, giòn béo tự nhiên) |
| `topic-pilot-macadamia-02` | Giá 195.000đ hộp 500g, kèm thanh tách thép và gói hút ẩm. | **FULL** (`Turn [5]`: hộp 500g 195.000đ, thanh tách thép, gói hút ẩm) | **FULL** (`Turn [5]`: hộp PET 500g 195.000đ, dụng cụ tách vỏ, gói hút ẩm — *nói "dụng cụ tách vỏ" thay cho "thanh tách thép"*) |
| **Tổng kết sơ bộ (AI Reviewer)** | `6` mandatory topics | **`5 FULL · 0 PARTIAL · 1 MISS`** | **`6 FULL · 0 PARTIAL · 0 MISS`** |

### 7.2. Nguyên tắc Tách biệt Coverage & Factual Correctness (Các Giới hạn Quan sát được)

1. **Không đánh đồng Playback-Confirmed Coverage với Semantic Coverage:**  
   Chỉ số `mandatory_topic_coverage` (`5/6` và `6/6`) chỉ xác nhận lượt gán với `topic_id` đã nhận `PlaybackCompleted (APPLIED)`. Ở Pilot v1, LangGraph đạt `100%` (`6/6`) `mandatory_topic_coverage` nhưng thực tế ngữ nghĩa có tới `3` câu stub thiếu nội dung. Sang Pilot v2, việc đạt `6/6 FULL` cho thấy khoảng cách giữa hai tầng coverage trên LangGraph đã thu hẹp rõ ở kịch bản ngắn này, nhưng vẫn cần con người xác nhận trên phiếu `factual_and_semantic_review_sheet.csv`.
2. **Citation hợp lệ và P05 `ALLOW` KHÔNG phải bằng chứng tuyệt đối về factual correctness hoặc semantic entailment:**  
   Kiểm tra thủ công từng câu trong Pilot v2 phát hiện các tình huống thực tế mà P05 cho `VERIFIED` (`ALLOW`) và `validate_draft_evidence_attribution()` thông qua, nhưng mức độ bao phủ của `cited_evidence_ids` chưa khớp `1-1` ở mức câu văn:
   - **LangGraph Turn `[4]` (`topic-pilot-macadamia-01`)** & **Script-first Turn `[4]`**: Cả hai chỉ trích dẫn `["ev-e01-ext-macadamia-harvest"]` (chỉ mô tả *hong gió giảm ẩm, sấy đối lưu nhiệt độ thấp để chín đều từ lõi và nứt vỏ*), trong khi câu nói đều nhắc thêm `"giòn béo tự nhiên"` (thực chất thuộc `ev-e01-macadamia-quality` và `talking_points`, không sai sự thật với SKU nhưng không nằm trong chunk được cite).
   - **LangGraph Turn `[5]` & Script-first Turn `[5]` (`topic-pilot-macadamia-02`)**: Cả hai chỉ trích dẫn `["ev-e01-macadamia-shipping"]` (chỉ nhắc *giá 195.000đ, hộp PET 500g, dụng cụ tách vỏ, đổi trả 7 ngày*), nhưng câu nói đều thêm `"gói hút ẩm"` (thực tế đúng trong `ev-e01-macadamia-quality` / `ev-e01-ext-macadamia-packaging`). Đây là hiệu ứng của `topic.fact_refs` chỉ liệt kê 1 chunk trong khi `talking_points` tổng hợp ý từ 2 chunk.
   - **Sắc thái ngôn ngữ bán hàng ở Script-first Turn `[3]` & `[5]`:** Cụm từ `"giá chỉ 245.000đ"`, `"chỉ 195.000đ, tặng kèm thanh tách thép"` giữ đúng số tiền niêm yết và phụ kiện có thật trong catalog, nhưng mang giọng văn khuyến khích mua (`"chỉ"`, `"tặng kèm"` — riêng `"tặng kèm"` có xuất hiện trong `ev-e01-macadamia-usage`). Người chấm thật cần rà soát xem mức diễn đạt này có phù hợp guideline P05/G6 hay cần tiết chế ở phiên chính thức.
3. **Không suy diễn ý nghĩa thống kê từ `n=1`:**  
   Mỗi cấu hình chỉ chạy đúng `1` lần trên `6` topics; không thể kết luận khác biệt có ý nghĩa thống kê trước khi chạy lặp hoặc mở rộng trên tập kịch bản dài `10–30` phút.

---

## 8. Wasted Calls, Token Usage và Latency

### 8.1. Phân loại Rạch ròi Wasted Calls (`HTTP 503` vs Agent Logic/Prompt)

| Run | Tổng Calls | Thành công (`HTTP 200` + chấp nhận) | Wasted do Hạ tầng (`HTTP 503`) | Wasted do Logic/Prompt Agent | Chi tiết Wasted Calls |
|---|---:|---:|---:|---:|---|
| Script-first v1 (`cae3af15`) | `6` | `5` | `1` (`16.7%`) | `0` | `call_index=3`: `HTTP 503 UNAVAILABLE` |
| LangGraph v1 (`862ba71f`) | `16` | `6` | `3` (`18.8%`) | **`7`** (`43.8%`) | `5` `OVER_MAX_DURATION_SEC` (`9.23s–10.77s`) + `2` `MISSING_EVIDENCE` (`cited_evidence_ids=[]`) |
| **Script-first v2 (`f722769c`)** | `6` | `5` | **`0`** (`0%`) | **`1`** (`16.7%`) | `call_index=1` (`topic-pilot-honey-02`): `OVER_MAX_DURATION_SEC` (`8.08s > 8.00s`, `2,050` in + `201` out = `2,251` tokens) |
| **LangGraph v2 (`defb5376`)** | `6` | **`6`** | **`0`** (`0%`) | **`0`** (`0%`) | Không có call nào bị lỗi hay bị loại |

### 8.2. Token Usage & Latency Thực tế (Pilot v2 vs Pilot v1)

| Chỉ số | Script-first v1 | Script-first v2 | LangGraph v1 | LangGraph v2 |
|---|---:|---:|---:|---:|
| `token_usage_source` tổng hợp | `UNAVAILABLE` (`5/6` measured) | **`MEASURED` (`6/6`)** | `UNAVAILABLE` (`13/16` measured) | **`MEASURED` (`6/6`)** |
| Input tokens (Partial ở v1 / Full ở v2) | `9,719` *(partial 5/6)* | **`12,323`** | `27,633` *(partial 13/16)* | **`15,408`** |
| Output tokens (Partial ở v1 / Full ở v2) | `766` *(partial 5/6)* | **`1,106`** | `847` *(partial 13/16)* | **`714`** |
| Wasted tokens đo được | `0` *(1 call 503 `UNAVAILABLE`)* | **`2,251`** (`2,050` in + `201` out) | `14,777` *(7/10 wasted calls)* | **`0`** |
| `provider_latency_p50_ms` | `5,973.39 ms` | `6,162.56 ms` | `5,918.43 ms` | `6,042.54 ms` |
| `provider_latency_p95_ms` | `6,110.38 ms` | `7,848.79 ms` | `7,493.06 ms` | `9,299.18 ms` |
| `invocation_latency_p50_ms` | `5,829.91 ms` | `6,321.01 ms` | `9,979.40 ms` | **`6,084.98 ms`** |
| `invocation_latency_p95_ms` | `6,104.10 ms` | `6,458.02 ms` | `17,716.97 ms` | **`9,343.92 ms`** |
| `total_measured_processing_ms` | `31,943.77 ms` | `37,693.61 ms` | `95,129.14 ms` | **`35,765.25 ms`** |

> **Giải thích kiến trúc về Latency & Token:**  
> - Ở Pilot v2, `provider_latency_p50` của cả hai phương pháp đều quanh `6.04s–6.16s` (nằm gọn trong ngưỡng `W1` P50 `<= 7s` cho một lần gọi đơn lẻ), nhưng `p95` đạt `7.85s–9.30s` (gần ngưỡng P95 `<= 10s` ngay cả khi **chưa có retry**). Nếu một lượt phát sinh 1 lần rewrite (`2` calls * ~`6s` + `6s` pacing), độ trễ đầu-cuối sẽ vượt `12–18s`.  
> - `langgraph_structured_story` dùng nhiều input token hơn Script-first (`15,408` vs `12,323`, tức `+25.0%`) vì mỗi lượt nạp lại `played_history_summary` (`W=5`) và hệ thống nhắc khung LangGraph; bù lại, output gọn hơn (`714` vs `1,106` vì không sinh field `rationale` dài) và có khả năng tự sửa/khôi phục khi bị từ chối.

---

## 9. Budget Ledger (Sổ cái Ngân sách Pilot v2)

Nguồn: [`gemini_3.5_flash_lite_pilot_v2/budget_ledger.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/budget_ledger.json). Không sử dụng lại 3 slot dư của Pilot v1.

| Giai đoạn | Ngân sách Phê duyệt Tối đa | Thực tế Đã dùng (Google AI API thật) | Còn dư | HTTP 429 | Chi phí Thực trả |
|---|---:|---:|---:|---:|---:|
| Stage A — Smoke Re-validation | `3` | **`3`** (`1` metadata + `2` DTOs) | `0` | `0` | `0 USD` |
| Stage B — Short Pilot v2 | `25` | **`12`** (`6` Script-first + `6` LangGraph) | `13` | `0` | `0 USD` |
| **Tổng cộng Pilot v2** | **`28`** | **`15`** | **`13`** | **`0`** | **`0 USD`** |

*(Toàn vẹn Pilot v1: [`gemini_3.5_flash_lite_pilot/budget_ledger.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/budget_ledger.json) giữ nguyên `3 + 22 = 25/28` requests, không bị ghi đè).*

---

## 10. Đường dẫn Artifacts Human Evaluation & Kiểm chứng Chấm mù

Toàn bộ artifacts Human Evaluation của Pilot v2 được xuất từ đúng 2 runs Gemini Pilot v2 trên kịch bản `pilot_short_3sku_ext`:

- **Phiếu chấm mù 6 tiêu chí (CSV):** [`runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/human_eval/blind_eval_sheet.csv`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/human_eval/blind_eval_sheet.csv)
- **Phiếu chấm mù 6 tiêu chí (JSONL):** [`runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/human_eval/blind_eval_sheet.jsonl`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/human_eval/blind_eval_sheet.jsonl)
- **Bảng đối chiếu Factual Claims & Semantic Topic Coverage cho reviewer thật (MỚI):** [`runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/human_eval/factual_and_semantic_review_sheet.csv`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/human_eval/factual_and_semantic_review_sheet.csv)
- **Bảng ánh xạ bí mật (tách riêng, KHÔNG đưa cho người chấm):** [`runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/human_eval/blind_key_mapping.private.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/human_eval/blind_key_mapping.private.json)

**Kết quả xác minh tính toàn vẹn chấm mù:**
1. Có đúng **`2` samples** (`SAMPLE_001` = `METHOD_A`, `SAMPLE_002` = `METHOD_B`) trên đúng `scenario = "pilot_short_3sku_ext"`; phiếu chi tiết có đúng **`12` rows** (`6` turns x `2` samples).
2. Nội dung khớp nguyên văn 100% transcript Gemini Pilot v2 thật (`0` dữ liệu `MockLLMProvider`).
3. Kiểm tra tự động không phát hiện rò rỉ từ khóa nhạy cảm (`script_first`, `langgraph`, `gemini`, `flash-lite`, `w=5`, `w5`, `now`, `f722769c`, `defb5376`, `mock`) trong cả `blind_eval_sheet.csv` và `factual_and_semantic_review_sheet.csv` (`leaks=[]`).
4. Toàn bộ các cột điểm số và cột nhận xét của người chấm đều **để trống hoàn toàn** (`0` điểm human evaluation giả).

---

## 11. Kết quả Kiểm thử Hồi quy (Regression Tests)

Chạy kiểm chứng toàn bộ bộ test trước phiên chạy Pilot v2 (không sửa thêm mã nguồn `src/` hay `prompts/` trong phiên chạy Pilot v2):
- `.\.venv\Scripts\python.exe -m pytest experiments/sales-intelligence/autonomous-storytelling/tests -q` -> **`279 passed in 26.05s`** (`0 failed, 0 skipped`).
- `.\.venv\Scripts\python.exe -m pip check` -> **`No broken requirements found.`**

---

## 12. Giới hạn Còn lại (Remaining Limitations)

1. **Cỡ mẫu ngắn & chưa đánh giá độ dài `10–30` phút (`W ∈ {5, 10, 20}`):** `pilot_short_3sku_ext` chỉ có `6` topics (`~35–39s` nội dung phát sóng), chưa kích hoạt áp lực quên ngữ cảnh hoặc lặp ý giữa các lượt xa nhau của `W=5` vs `W=10` vs `W=20`.
2. **Chưa có điểm đánh giá từ người thật:** Cả `blind_eval_sheet.csv` và `factual_and_semantic_review_sheet.csv` đang chờ reviewer độc lập chấm (`overall_gate_status: NOT_EVALUATED`).
3. **Biên độ `8.0s` trên `ScriptFirstBaseline` rất sát trần:** `ScriptFirstBaseline` dùng `max_words = 21` (`8.08s > 8.00s` khi đụng 21 từ) và không có rewrite, nên chỉ lệch 1 từ là rớt về fallback generic của SKU.
4. **Khoảng trống kiểm chứng ngữ nghĩa ở P05:** P05 chưa có `GoldFactualLabel` hoặc cơ chế kiểm tra entailment giữa `text` và từng `cited_evidence_ids` cụ thể (như trường hợp cite 1 chunk nhưng nhắc thêm thuộc tính từ chunk liền kề của cùng SKU).
5. **Biến động hạ tầng Free Tier (`HTTP 503`):** Dù Pilot v2 không gặp `503`, xác suất `503` trên Free Tier vẫn tồn tại ở phiên dài (`18–24` calls/run khi chạy Formal Benchmark).
6. **Tier 2 Ollama CPU:** Vẫn giữ trạng thái **`DEFERRED WITH USER APPROVAL`**.

---

## 13. Khuyến nghị Sẵn sàng cho Formal Benchmark (`GO WITH PRE-EXECUTION CONDITIONS`)

### 13.1. Vì sao AI hoạt động tốt (và điểm nào vẫn cần dè chừng)?
- **Điểm AI làm tốt trong Pilot v2:** Khi được cung cấp rõ ràng (1) ngân sách từ cụ thể `12–18 từ` tương thích trần `8.0s`, (2) danh sách `allowed_evidence_ids` & `allowed_claim_ids` gắn `required` trên OpenAPI schema, (3) `mandatory_messages` lọc đúng theo `active_sku_id`, và (4) quy tắc không phải lặp lại tên dài + giá ở mọi lượt, `gemini-3.5-flash-lite` (`thinkingLevel=MINIMAL`) thể hiện khả năng tuân thủ cấu trúc và viết tiếng Việt tự nhiên rất tốt: **`0` lỗi schema, `0` rò rỉ ID, `100%` citation hợp lệ và `6/6` turns LangGraph giữ trọn ý chính ngay lần thử đầu tiên (`0` rewrite, `0` wasted calls)**.
- **Điểm vẫn chưa triệt để:** `ScriptFirstBaseline` có `max_words=21` (khớp `8.08s > 8.00s` ở ngưỡng `2.6` từ/giây), dẫn tới `1` lỗi vượt thời lượng ở Turn `[1]` và tụt coverage xuống `5/6` vì fallback generic không mang thông điệp đổi trả `1-1`. Đồng thời `p95` độ trễ provider lên tới `9.30s` trên câu đơn, đòi hỏi theo dõi kỹ khi chạy phiên `10–30` phút.

### 13.2. Khuyến nghị Quyết định
- **Khuyến nghị:** **`GO FOR FORMAL BENCHMARK WITH PRE-EXECUTION CONDITIONS`** (Đủ độ ổn định kỹ thuật của agent LangGraph & guardrails để chuẩn bị chạy `P06-E01` Formal Benchmark `W ∈ {5, 10, 20}`, nhưng **chỉ kích hoạt sau khi hoàn tất 3 điều kiện cổng**):
  1. **Hoàn tất Human Blind Calibration trên Pilot v2:** Tech Lead / Reviewer độc lập chấm [`blind_eval_sheet.csv`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/human_eval/blind_eval_sheet.csv) và [`factual_and_semantic_review_sheet.csv`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/human_eval/factual_and_semantic_review_sheet.csv) để chốt xem chất lượng ngôn ngữ `8.0s` (`11–18` từ) đã đạt kỳ vọng chưa hay cần mở phép thử A/B `8.0s` vs `10–12s` ở giai đoạn tiếp theo.
  2. **Chốt xử lý biên `21` từ của `ScriptFirstBaseline` (tùy chọn nhỏ trước Formal Benchmark):** Nếu muốn so sánh công bằng `ScriptFirst` ở `8.0s`, cân nhắc đồng bộ ngưỡng nhắc từ của `ScriptFirst` về `12–18 từ` (tối đa `20` từ, `<= 7.69s`) giống LangGraph trước khi chạy Formal Benchmark (hoặc giữ nguyên như một giới hạn thực nghiệm đã ghi nhận của baseline nếu muốn đóng băng code v0.2).
  3. **Phê duyệt ngân sách RPD theo đợt cho Formal Benchmark:** Vì kịch bản `10–30` phút (`18–24` topics/run × `4` cấu hình `Script-first + LangGraph W∈{5,10,20}`) cần khoảng `75–120` requests (chưa tính retry/503), cần chia batch theo ngày trên Free Tier `500 RPD` với pacing `>= 6.0s` và phê duyệt riêng.

**Trạng thái hiện tại:** **Dừng tại `AWAITING_FORMAL_BENCHMARK_APPROVAL`.** Không thực thi Formal Benchmark, không chạy sweep `W`, không sửa code thêm và không tự commit/push khi chưa có quyết định của Tech Lead.
