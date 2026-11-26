# Báo cáo Thực nghiệm Gemini Smoke Test & Short Pilot — P06-E01-T09

**Ngày cập nhật:** `2026-11-26`  
**Branch:** `research/p06-autonomous-storytelling`  
**Module:** `experiments/sales-intelligence/autonomous-storytelling/`  
**Trạng thái hiện tại:** `STAGE A + STAGE B PILOT COMPLETED — AWAITING FORMAL BENCHMARK APPROVAL`  
**Kiểm chứng Offline sau cùng:** `261 passed in 66.55s` (`0 failed, 0 skipped`), `pip check` pass (`No broken requirements found.`)

---

## 1. Tóm tắt Điều hành (Executive Summary)

Sau khi nhận phê duyệt chính thức cho **Gemini 3.5 Flash-Lite Free Tier** (`0 USD`, chỉ dùng dữ liệu `SYNTHETIC`, thực thi tuần tự với `>= 6.0s` giữa hai lần bắt đầu request, trần tổng `28` requests) và xác nhận **Tier 2 — Ollama CPU** ở trạng thái **`DEFERRED WITH USER APPROVAL`**, nhóm nghiên cứu đã hoàn thành **Stage A (Smoke Test: `3/3` requests)** và **Stage B (Short Pilot trên `pilot_short_3sku_ext`: `22/25` requests)** với tổng tiêu thụ **`25/28` requests**, **`0 USD` chi phí thực trả**, và **`0` lỗi HTTP 429**.

Các kết quả cốt lõi quan sát được trên Gemini thật:
1. **Khả năng vận hành end-to-end với Gemini 3.5 Flash-Lite (`MINIMAL` thinking):** Sau khi sửa 1 lỗi schema OpenAPI (`exclusiveMinimum` không được Gemini REST chấp nhận) và 1 lỗi typo tham số cục bộ (`at_time=` -> `verified_at=`), cả `script_first_upfront_llm` và `langgraph_structured_story (W=5)` đều chạy hoàn chỉnh trên `pilot_short_3sku_ext` (`3 SKU`, `6 mandatory topics`, mục tiêu `300.0s`).
2. **Đánh đổi Resilience vs Latency/Token trên Free Tier (gặp `HTTP 503 UNAVAILABLE`):** Trong Stage B xuất hiện `4` lỗi tạm thời `HTTP 503 UNAVAILABLE` (`1/6` ở Script-first, `3/16` ở LangGraph). Nhờ bất biến non-advancing fallback (`I-06`), LangGraph đạt `100%` (`6/6`) `mandatory_topic_coverage` dù gặp 3 lần `503` và `2` lần bị P05 từ chối, trong khi Script-first đạt `83.33%` (`5/6`, bỏ lỡ `topic-pilot-tea-02`). Đổi lại, LangGraph tiêu tốn **`16` model calls** (`10` wasted calls), **`95.13s`** tổng thời gian xử lý và **`27,633` input tokens** (trên 13 call HTTP 200), so với **`6` calls** (`1` wasted), **`31.94s`** và **`9,719` input tokens** (trên 5 call HTTP 200) của Script-first.
3. **Phát hiện 4 khiếm khuyết chất lượng cần xử lý trước Benchmark chính thức:**
   - Script-first Turn `[4]` làm rò rỉ nguyên văn raw evidence ID (`(ev-e01-ext-macadamia-harvest, ev-e01-ext-macadamia-sensory)`) vào câu thoại tiếng Việt, nhưng P05 vẫn `ALLOW`.
   - Ngưỡng `8.0s` trên mỗi chunk ở LangGraph gây `4` lần reject `OVER_MAX_DURATION_SEC` (`10.38s–10.77s`), ép LLM rút gọn quá mức thành câu cụt chỉ còn tên SKU + khối lượng + giá (đánh mất lợi ích sản phẩm, chất liệu, phụ kiện).
   - Toàn bộ `6` lượt `PROACTIVE_STORY` của LangGraph xuất `cited_evidence_ids: []` và `covered_claim_ids: []` (`claim_overlap_rate = UNAVAILABLE`), khiến P05 reject `2` lượt đầu (`MISSING_EVIDENCE`) trước khi chấp nhận câu đã rút gọn có SKU + giá.
   - Câu `PREAPPROVED_FALLBACK` kết thúc bằng `", thông tin."` thiếu tự nhiên và bị lặp `3` lần ở LangGraph (`exact_normalized_text_replay_count = 2`).
4. **Cổng Phê duyệt:** `overall_gate_status` giữ nguyên **`NOT_EVALUATED`** (do chưa chấm Human Evaluation mù trong `human_eval/blind_eval_sheet.csv` và đây chỉ là pilot ngắn `3` SKU). Dừng hoàn toàn tại **Formal Benchmark Approval Gate**, chưa chạy `W={5,10,20}` sweep hay kịch bản `10m–30m`.

---

## 2. Xác minh Exact Gemini Model ID & Cấu hình Free Tier

### 2.1. Kết quả kiểm tra API Metadata & Environment

- **Biến môi trường:** Đã xác minh `GEMINI_API_KEY` tồn tại ở cấp Windows User Environment Variables (`USER_KEY=True`); tuyệt đối không in, không lưu vào log, telemetry hay báo cáo.
- **Exact Model ID xác minh từ `GET /models/gemini-3.5-flash-lite`:**
  - `name`: `models/gemini-3.5-flash-lite`
  - `displayName`: `Gemini 3.5 Flash Lite`
  - `version`: `3.5-flash-lite-07-2026`
  - `inputTokenLimit`: `1048576`
  - `outputTokenLimit`: `65536`
  - `supportedGenerationMethods`: `["generateContent", "countTokens", "createCachedContent", "batchGenerateContent"]`
- **HTTP Headers trả về:** Phản hồi từ Gemini API chỉ chứa `content-type` và `date`; API **không trả về header `x-ratelimit-*` hoặc hạn mức RPD còn lại**. Vì vậy, RPD remain vẫn ở trạng thái chưa xác nhận trực tiếp từ header và phải kiểm soát bảo thủ bằng `budget_ledger.json`.
- **Cấu hình Model áp dụng ([`gemini_3.5_flash_lite_free.yaml`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/configs/models/gemini_3.5_flash_lite_free.yaml)):**
  - `provider`: `gemini`, `run_tier`: `formal_experiment`, `status`: `FREE_TIER_PILOT_APPROVED`
  - `data_classification_allowed`: `["SYNTHETIC"]` (`merchant_dpa_status: FREE_TIER_SYNTHETIC_ONLY`)
  - `billing_tier`: `free_tier` (`input_per_1m_usd: 0.0`, `output_per_1m_usd: 0.0`)
  - `thinking_level`: `"MINIMAL"` (tương thích Gemini 3.x; không dùng đồng thời với `thinking_budget`)
  - `min_request_interval_sec`: `6.0` (~10 RPM, thấp hơn giới hạn 15 RPM của AI Studio)
  - `sampling`: `temperature: 0.3`, `top_p: 0.9`, `max_tokens: 1024`, `seed: 42`, `timeout_sec: 30`

### 2.2. Trạng thái Tier 2 — Ollama CPU Local

- **Trạng thái:** **`DEFERRED WITH USER APPROVAL`**.
- **Lý do đã ghi nhận:** Máy cá nhân không có GPU rời và RAM khả dụng thấp (`1.01 GB` free tại thời điểm readiness check); không tải thêm model Ollama và **không** đánh dấu Ollama là đã kiểm nghiệm.

---

## 3. Kiểm soát Quota & Số lượng Requests Đã Dùng

Theo [`budget_ledger.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/budget_ledger.json):

| Hạng mục | Ngân sách Tối đa Phê duyệt | Thực tế Đã dùng | Còn dư / Ghi chú |
|---|---:|---:|---|
| Stage A — Gemini Smoke Test | `3` | `3` | Dư `0` (1 metadata + 2 structured output) |
| Stage B — Short Pilot (`script_first_upfront_llm` + `langgraph_structured_story`) | `25` | `22` (`6` + `16`) | Dư `3` |
| **Tổng cộng Phiên E01-T09 Pilot** | **`28`** | **`25`** | **Dư `3` (đã dừng an toàn, không gọi thêm)** |
| Số lần gặp HTTP 429 (Rate Limit) | — | `0` | `rate_limited: false`, `completed_both: true` |

> [!NOTE]
> Vì HTTP response header của Gemini API không cung cấp hạn mức RPD còn lại, trước khi chạy Benchmark Chính thức (nếu được phê duyệt), người dùng cần kiểm tra trực tiếp hạn mức RPD trên dashboard Google AI Studio của `Default Gemini Project`.

---

## 4. Kết quả Stage A — Gemini Smoke Test (`3/3` Requests)

Nguồn chứng cứ: [`stage_a_smoke_results.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/stage_a_smoke_results.json).

1. **Request 1 (`GET /models/gemini-3.5-flash-lite`):** **PASSED.** Xác nhận exact model ID `models/gemini-3.5-flash-lite` tồn tại, hỗ trợ `generateContent`, giới hạn `1,048,576` input / `65,536` output tokens.
2. **Request 2 (`ChunkDraftLLMOutput` structured output):** **FAILED (`HTTP 400 INVALID_ARGUMENT`)** với thông báo `Unknown name "exclusiveMinimum" at 'generation_config.response_schema.properties[3].value'`. Nguyên nhân: Pydantic v2 xuất JSON Schema có `exclusiveMinimum` và `minLength` nhưng Gemini REST `responseSchema` chỉ nhận tập con OpenAPI 3.0.
   - **Khắc phục tức thì:** Cập nhật `_sanitize_gemini_response_schema` trong `src/p06/providers/gemini_provider.py` theo strict allowlist `_GEMINI_ALLOWED_SCHEMA_KEYS` (quy đổi `exclusiveMinimum: 0` trên `integer` sang `minimum: 1`, loại bỏ `exclusiveMinimum` / `minLength`), bổ sung regression test trong `tests/unit/test_providers.py` (`26 passed`).
3. **Request 3 (`ChunkDraftLLMOutput` sau khi vá):** **HTTP 200 & Pydantic parse SUCCEEDED** (`thinkingLevel=MINIMAL`), nhưng `run_gemini_pilot.py:295` ném `TypeError: P05KnowledgeAdapter.verify_candidate() got an unexpected keyword argument 'at_time'` trước khi lưu kết quả verify/output của Request 3 (`stage_a_requests=3`, `all_passed=false`). Đã sửa `at_time=` -> `verified_at=` tại `run_gemini_pilot.py:295,392` và nhận phê duyệt chuyển sang Stage B mà không vượt trần 3 requests của Stage A.

---

## 5. Cấu hình Pilot Stage B (`pilot_short_3sku_ext`)

- **Runner:** [`run_gemini_pilot.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_gemini_pilot.py) (thực thi tuần tự, ép `tier=formal_experiment`, chặn vượt ngân sách toàn cục).
- **Kịch bản:** `pilot_short_3sku_ext` trong [`e01_ext_v1_story_plans.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/data/story_plans/e01_ext_v1_story_plans.json) — `3` SKU dữ liệu synthetic (`Mật ong hoa cà phê Đắk Lắk`, `Trà Shan Tuyết cổ thụ Hà Giang`, `Hạt mắc ca sấy đối lưu Lâm Đồng`), tổng **`6` mandatory topics** (`topic-pilot-honey-01`, `topic-pilot-honey-02`, `topic-pilot-tea-01`, `topic-pilot-tea-02`, `topic-pilot-macadamia-01`, `topic-pilot-macadamia-02`), thời lượng mục tiêu `300.0s`.
- **Các phương pháp so sánh:**
  1. `script_first_upfront_llm` (`noW`, `run_id = P06-E01__pilot_short_3sku_ext__script_first_upfront_llm__noW__20261126T103256Z__cae3af15`)
  2. `langgraph_structured_story` (`W=5`, `run_id = P06-E01__pilot_short_3sku_ext__langgraph_structured_story__w5__20261126T103329Z__862ba71f`)

---

## 6. Toàn bộ Transcript Nguyên văn (Full Verbatim Transcripts)

### 6.1. `script_first_upfront_llm` (`noW` — 6 turns)

1. **`[0]` `topic-pilot-honey-01` (`PROACTIVE_STORY`):**  
   > `"Mật ong vàng hổ phách, lọc mịn không gia nhiệt giữ vị ngọt dịu."`
2. **`[1]` `topic-pilot-honey-02` (`PROACTIVE_STORY`):**  
   > `"Chai 500ml giá 159.000đ, bọc chống sốc hai lớp và đổi 1-1 trong 7 ngày nếu vỡ."`
3. **`[2]` `topic-pilot-tea-01` (`PROACTIVE_STORY`):**  
   > `"Nước trà vàng mơ sáng trong, thoảng hương cốm non và hậu ngọt sâu."`
4. **`[3]` `topic-pilot-tea-02` (`PREAPPROVED_FALLBACK` — do `HTTP 503 UNAVAILABLE` ở call_index `3`):**  
   > `"Trà Shan Tuyết cổ thụ Hà Giang hộp thiếc 200g, giá niêm yết 245.000đ, thông tin."`
5. **`[4]` `topic-pilot-macadamia-01` (`PROACTIVE_STORY` — rò rỉ evidence ID thô):**  
   > `"Mắc ca sấy đối lưu nhiệt độ thấp giúp nhân chín đều, thơm bơ nhẹ và giòn tan (ev-e01-ext-macadamia-harvest, ev-e01-ext-macadamia-sensory)."`
6. **`[5]` `topic-pilot-macadamia-02` (`PROACTIVE_STORY`):**  
   > `"Hộp 500g giá 195.000đ kèm dụng cụ tách thép."`

### 6.2. `langgraph_structured_story` (`W=5` — 9 turns)

> Lưu ý: Mọi `PROACTIVE_STORY` turns dưới đây đều có `cited_evidence_ids: []` và `covered_claim_ids: []` trong output thực tế.

1. **`[0]` `PREAPPROVED_FALLBACK`** *(attempt 0 bị reject `10.38s > 8s`, attempt 1 bị P05 reject `MISSING_EVIDENCE`, attempt 2 gặp `HTTP 503`)*:  
   > `"Mật ong hoa cà phê Đắk Lắk nguyên chất 500ml, giá niêm yết 159.000đ, thông tin."`
2. **`[1]` `topic-pilot-honey-01` (`PROACTIVE_STORY`, `r2`):**  
   > `"Mật ong hoa cà phê Đắk Lắk 500ml giá 159.000đ."`
3. **`[2]` `PREAPPROVED_FALLBACK`** *(attempt 0 gặp `HTTP 503`)*:  
   > `"Mật ong hoa cà phê Đắk Lắk nguyên chất 500ml, giá niêm yết 159.000đ, thông tin."`
4. **`[3]` `PREAPPROVED_FALLBACK`** *(attempt 0 gặp `HTTP 503`)*:  
   > `"Mật ong hoa cà phê Đắk Lắk nguyên chất 500ml, giá niêm yết 159.000đ, thông tin."`
5. **`[4]` `topic-pilot-honey-02` (`PROACTIVE_STORY`, `r1` — attempt 0 bị reject `10.38s > 8s`):**  
   > `"Chai 500ml giá 159.000đ, đổi 1-1 trong 7 ngày nếu vỡ."`
6. **`[5]` `topic-pilot-tea-01` (`PROACTIVE_STORY`, `r0`):**  
   > `"Trà Shan Tuyết 200g giá niêm yết 245.000đ, khi pha cho nước vàng mơ sáng trong và hậu ngọt sâu."`
7. **`[6]` `topic-pilot-tea-02` (`PROACTIVE_STORY`, `r0`):**  
   > `"Trà Shan Tuyết 200g giá niêm yết 245.000đ."`
8. **`[7]` `topic-pilot-macadamia-01` (`PROACTIVE_STORY`, `r2` — attempt 0 `10.77s` và attempt 1 `9.23s` bị reject `OVER_MAX_DURATION_SEC`):**  
   > `"Mắc ca sấy đối lưu Lâm Đồng hộp 500g giá 195.000đ."`
9. **`[8]` `topic-pilot-macadamia-02` (`PROACTIVE_STORY`, `r0`):**  
   > `"Hạt mắc ca 500g giá niêm yết 195.000đ."`

---

## 7. Bảng So sánh Metrics (`comparison.json` & `metrics.json`)

Nguồn: [`comparison.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/comparison.json) (`compatible: true`, `grouped_tiers: ["formal_experiment"]`) và `metrics.json` từng run.

| Metric | `script_first_upfront_llm` (`noW`) | `langgraph_structured_story` (`W=5`) | Ghi chú quan sát |
|---|---|---|---|
| `termination_reason` | `CONTENT_EXHAUSTED` | `EARLY_COMPLETION` | Script-first hụt 1 topic do `503` |
| `mandatory_topic_coverage` | `0.8333` (`5/6`) | `1.0000` (`6/6`) | LangGraph giữ progress nhờ fallback |
| `duration_fulfillment` | `0.1154` (`34.616s / 300s`) | `0.1487` (`44.616s / 300s`) | Kịch bản pilot 3 SKU rất ngắn |
| `exact_chunk_replay_count` | `0` | `0` | — |
| `exact_normalized_text_replay_count` | `0` | `2` | Lặp 3 lần câu fallback ở turns `0, 2, 3` |
| `outside_window_exact_text_replay_count` | `null` (`noW`) | `0` | — |
| `max_prior_ngram3_jaccard_mean` | `0.0000` | `0.3562` | Lặp cấu trúc câu tên + giá + fallback |
| `lexical_repetition_rate` | `0.0000` | `0.2500` (`2/8`) | — |
| `p05_rejection_rate` | `0.0000` | `0.2500` (`2/8`) | `MISSING_EVIDENCE` ở `turn-0000-r1`, `turn-0001-r1` |
| `rewrite_rate` | `0.0000` | `0.4444` (`4/9`) | Do duration + P05 + 503 retries |
| `attempts_per_turn_mean` | `1.00` | `1.7778` (`max=3`) | — |
| `fallback_rate` | `0.1667` (`1/6`) | `0.3333` (`3/9`) | Gắn trực tiếp với `1` vs `3` lần `503` |
| `safe_abort_count` / `rate` | `0` / `0.0` | `0` / `0.0` | `3` clean SKU boundaries excluded |
| `claim_overlap_rate` | `UNAVAILABLE` | `UNAVAILABLE` | LangGraph xuất `cited_evidence_ids: []` |
| `total_model_calls` (`wasted`) | `6` (`1`) | `16` (`10`) | Tỉ lệ wasted: `16.7%` vs `62.5%` |
| `struct_gates` | `PASS` | `PASS` | — |
| `overall_gate_status` | `NOT_EVALUATED` | `NOT_EVALUATED` | Thiếu Human Eval & chưa đủ mẫu |

---

## 8. Đánh giá Factual Correctness, P05 Verification & Giới hạn An toàn

Phân tích thủ công toàn bộ 15 turns thật cho thấy **tự động hóa P05 hiện tại không đủ để kết luận chất lượng thực tế**:

1. **Rò rỉ định danh nội bộ (`ev-...`) nhưng lọt P05 (Script-first Turn `[4]`):** Gemini chèn thẳng chuỗi `(ev-e01-ext-macadamia-harvest, ev-e01-ext-macadamia-sensory)` vào lời thoại MC. Vì P05 chỉ kiểm tra sự mâu thuẫn sự thật/giá/claim cấm, câu này vẫn nhận `ALLOW`. Đây là lỗi trải nghiệm nghiêm trọng nếu đưa lên TTS.
2. **Mất chi tiết sản phẩm do ép ngưỡng `8.0s` (LangGraph Turns `[1], [6], [7], [8]`):** Ràng buộc cứng `<= 8.0s` (~20 từ tiếng Việt) kết hợp prompt bắt giữ tên + giá khiến Gemini sau khi bị `OVER_MAX_DURATION_SEC` (`10.38s–10.77s`) đã **xóa sạch nội dung chuyên biệt của topic** (hộp thiếc/hút chân không, dụng cụ tách thép, gói hút ẩm, hương vị giòn tan) để giữ khung `"<Tên SKU> <Khối lượng> giá [niêm yết] <Giá>"`. Nói cách khác, `100%` `mandatory_topic_coverage` đạt được trên lý thuyết nhưng **chất lượng ngữ nghĩa bị suy giảm thành câu lặp giá**.
3. **Bỏ trống `cited_evidence_ids: []` & `covered_claim_ids: []` ở LangGraph:** Vì Pydantic schema không đặt `minItems: 1` (trên OpenAPI) cho `cited_evidence_ids`, Gemini trả về mảng rỗng ở toàn bộ `6/6` `PROACTIVE_STORY` turns. Sau `2` lần bị P05 từ chối `MISSING_EVIDENCE` trên mật ong, các turns còn lại vẫn có `cited_evidence_ids: []` nhưng lọt P05 nhờ câu chữ có tên SKU + giá niêm yết trùng dữ liệu ground-truth. Điều này cũng làm chỉ số `claim_overlap_rate` rơi về `UNAVAILABLE`.
4. **Câu fallback `", thông tin."` thiếu tự nhiên & lặp lại:** Ở LangGraph Turns `0, 2, 3`, cùng một câu fallback lặp 3 lần làm tăng `exact_normalized_text_replay_count = 2`.
5. **Human Evaluation:** Phiếu chấm mù đã tạo sạch tại [`blind_eval_sheet.csv`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/human_eval/blind_eval_sheet.csv) (`SAMPLE_001` = `METHOD_A`, `SAMPLE_002` = `METHOD_B`, không rò tên thuật toán hay `run_id`, cột điểm để trống cho reviewer thật chấm).

---

## 9. Token Usage & Độ trễ (Latency)

Do bất biến **honest provenance**: chỉ cần `>= 1` call trong run bị lỗi (`HTTP 503`), `token_usage.json` tổng hợp bắt buộc ghi `token_usage_source: "UNAVAILABLE"` để không báo cáo con số tổng thiếu hụt như dữ liệu đầy đủ. Dưới đây là số liệu tách riêng hai phần từ `provider_calls.jsonl` và `metrics.json`:

| Chỉ số | `script_first_upfront_llm` (`noW`) | `langgraph_structured_story` (`W=5`) |
|---|---|---|
| `token_usage.json` tổng hợp | `UNAVAILABLE` (có `1` call 503 ở `call_index=3`) | `UNAVAILABLE` (có `3` calls 503 ở `call_index=2, 6, 7`) |
| Tổng tokens trên các calls HTTP 200 (`MEASURED`) | `9,719` input / `766` output (`5/6` calls) | `27,633` input / `847` output (`13/16` calls) |
| `thinking_tokens` (`thinkingLevel=MINIMAL`) | `null` (API không tách riêng field) | `null` (API không tách riêng field) |
| `provider_latency_p50_ms` / `p95_ms` | `5,973.39 ms` / `6,110.38 ms` | `5,918.43 ms` / `7,493.06 ms` |
| `invocation_latency_p50_ms` / `p95_ms` | `5,829.91 ms` / `6,104.10 ms` | `9,979.40 ms` / `17,716.97 ms` |
| `planning_latency_ms` | `31,823.44 ms` | `—` (per-turn graph) |
| `total_measured_processing_ms` | `31,943.77 ms` | `95,129.14 ms` |

> Ghi nhận quan trọng: Mỗi call Gemini mất ~`5.9s` median thuần túy ở phía provider (chưa tính sleep pacing `6.0s` giữa hai lần bắt đầu request kế tiếp). Với LangGraph `invocation_latency_p95 = 17.72s`, việc sinh động theo lượt + retry sẽ chạm ngưỡng timeout/dead-air thực tế của livestream nếu không có prefetch/buffer hoặc giảm tỉ lệ reject (`44.44%` rewrite rate).

---

## 10. Lỗi Đã Gặp & Khắc Phục Trong Phiên

| Lỗi gặp phải | Giai đoạn | Biện pháp xử lý đã thực hiện | Trạng thái |
|---|---|---|---|
| `HTTP 400 INVALID_ARGUMENT` (`exclusiveMinimum`) từ Gemini REST `responseSchema` | Stage A Req 2 | Đưa `_sanitize_gemini_response_schema` về strict allowlist OpenAPI 3.0 (`exclusiveMinimum: 0` -> `minimum: 1`, loại `minLength`/`exclusiveMinimum`); thêm test hồi quy | **FIXED & TESTED** |
| `TypeError: P05KnowledgeAdapter.verify_candidate() got an unexpected keyword argument 'at_time'` | Stage A Req 3 (local script) | Sửa `at_time=` -> `verified_at=` trong `run_gemini_pilot.py:295,392` | **FIXED** |
| `4` lần `HTTP 503 UNAVAILABLE` (high demand phía Google) | Stage B (`1` Script-first, `3` LangGraph) | Giữ nguyên kết quả thực nghiệm thật (không làm giả dữ liệu); Script-first mất `topic-pilot-tea-02`; LangGraph fallback để giữ progress | **RECORDED AS REAL OBSERVATION** |
| Không gặp `HTTP 429` nào | Stage A & B | Nhờ sequential pacing `>= 6.0s` và `budget_ledger.json` | **CONTROLLED** |

---

## 11. Kiểm chứng Hồi quy (Regression Tests & Environment Check)

Chạy kiểm chứng toàn bộ sau lần chỉnh sửa code và chạy pilot cuối cùng:
- `pytest experiments/sales-intelligence/autonomous-storytelling/tests --collect-only -q` -> **`261 tests collected in 7.91s`**
- `pytest experiments/sales-intelligence/autonomous-storytelling/tests -q` -> **`261 passed in 66.55s` (`0 failed, 0 skipped`)**
- `pip check` -> **`No broken requirements found.`**

---

## 12. Danh sách Run IDs & Đường dẫn Artifacts

- Thư mục gốc pilot: [`runs/P06-E01/gemini_3.5_flash_lite_pilot/`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/)
- Budget ledger: [`budget_ledger.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/budget_ledger.json)
- Stage A results: [`stage_a_smoke_results.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/stage_a_smoke_results.json)
- Stage B summary: [`stage_b_pilot_summary.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/stage_b_pilot_summary.json)
- Comparison: [`comparison.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/comparison.json), [`comparison.csv`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/comparison.csv), [`comparison.md`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/comparison.md)
- Human Eval mù: [`blind_eval_sheet.csv`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/human_eval/blind_eval_sheet.csv), [`blind_eval_sheet.jsonl`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/human_eval/blind_eval_sheet.jsonl), [`blind_key_mapping.private.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/human_eval/blind_key_mapping.private.json)
- Run 1 (`script_first_upfront_llm`): `P06-E01__pilot_short_3sku_ext__script_first_upfront_llm__noW__20261126T103256Z__cae3af15`
- Run 2 (`langgraph_structured_story`, `W=5`): `P06-E01__pilot_short_3sku_ext__langgraph_structured_story__w5__20261126T103329Z__862ba71f`

---

## 13. Bài học Kỹ thuật Rút ra

1. **Gemini 3.x OpenAPI Schema Sanitization là bắt buộc:** Không thể truyền thẳng `model_json_schema()` của Pydantic v2 lên Gemini `responseSchema`; sanitizer phải theo strict allowlist.
2. **Ngưỡng `8.0s` / chunk đang làm méo hành vi LLM:** Khi bắt buộc đồng thời tên SKU, giá niêm yết và giới hạn `<= 8.0s`, Gemini bị ép hy sinh giá trị thuyết minh cốt lõi để tránh `OVER_MAX_DURATION_SEC`. Cần rà lại độ dài mục tiêu mỗi chunk (hoặc số từ/topic) trước benchmark chính thức.
3. **P05 verification hiện chưa chặn rò rỉ ID nội bộ và mảng `cited_evidence_ids` rỗng:** Cần thêm rule từ chối chuỗi dạng `ev-[a-z0-9-]+` trong spoken text và siết ràng buộc citation để `claim_overlap_rate` đo được thay vì `UNAVAILABLE`.
4. **Hành vi `HTTP 503` trên Free Tier là hiện hữu:** Thiết kế fallback của LangGraph cho thấy lợi thế rõ về độ bền tiến độ (`6/6` vs `5/6`), nhưng tốn `2.67x` số calls và `2.98x` tổng thời gian xử lý trên đoạn pilot ngắn.

---

## 14. Đề xuất Giao thức & Ngân sách cho Benchmark Chính thức (Formal Benchmark Approval Gate)

### 14.1. Đã chứng minh vs Chưa chứng minh

- **Đã chứng minh:** Kết nối hợp lệ với `models/gemini-3.5-flash-lite` Free Tier (`0 USD`); structured output Pydantic hoạt động sau khi sanitize; pacing `6.0s` tránh được HTTP 429; cơ chế fallback + budget cap hoạt động đúng thiết kế; offline suite `261/261` tests pass.
- **Chưa chứng minh:**
  1. Chất lượng thuyết minh thực tế qua **Human Evaluation** (chưa chấm `blind_eval_sheet.csv`).
  2. Độ ổn định chống lặp khi thời lượng dài (`10m–30m`, `W={5,10,20}`).
  3. Tính ưu việt của `langgraph_structured_story` so với `script_first_upfront_llm` (vì LangGraph hiện đang bị cụt câu do ngưỡng `8.0s` và lặp fallback).
  4. Tier 2 Ollama local CPU (`DEFERRED WITH USER APPROVAL`).

### 14.2. Checklist Điều kiện Trước Khi Chạy Formal Benchmark

1. **Chấm điểm mù Human Eval trên Pilot:** Người dùng/reviewer chấm [`blind_eval_sheet.csv`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/human_eval/blind_eval_sheet.csv) theo rubric để chốt có cần sửa prompt/duration ngay không.
2. **Sửa 4 điểm nghẽn chất lượng trước khi đốt RPD chính thức** (nếu được phê duyệt):
   - Chặn raw ID (`ev-...`) trong spoken text tại validator/prompt.
   - Bổ sung hướng dẫn & kiểm tra `cited_evidence_ids` non-empty (hoặc map claim chính xác).
   - Rà soát ngưỡng `max_chunk_duration_sec` / định mức từ mỗi chunk để giữ talking points.
   - Làm tự nhiên câu `PREAPPROVED_FALLBACK` (bỏ đuôi `", thông tin."`).
3. **Xác nhận RPD quota trên Google AI Studio** và phê duyệt ngân sách request riêng cho Formal Benchmark (ví dụ tách từng sweep/scenario thay vì chạy dồn trong 1 ngày nếu RPD Free Tier giới hạn thấp).

**Trạng thái hiện tại:** **Dừng tại Cổng Phê duyệt Benchmark Chính thức (`AWAITING FORMAL BENCHMARK APPROVAL`).** Không thực hiện thêm bất kỳ request Gemini nào cho tới khi có phê duyệt mới.
