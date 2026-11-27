# Báo cáo Khắc phục Lỗi Pilot v1 & Kế hoạch Tái kiểm chứng Pilot v2 — P06-E01-T09

**Ngày cập nhật:** `2026-11-27`  
**Branch:** `research/p06-autonomous-storytelling`  
**Base Commit:** `54066da` (sau merge `origin/main` `484afab`)  
**Module:** `experiments/sales-intelligence/autonomous-storytelling/`  
**Quyết định Tech Lead:** `CHANGE BEFORE FORMAL BENCHMARK`  
**Trạng thái hiện tại:** `OFFLINE REMEDIATION COMPLETED — AWAITING_PILOT_V2_EXECUTION_APPROVAL`  
**Kiểm chứng Ngoại tuyến sau cùng:** `279 tests collected in 1.61s`, **`279 passed in 27.57s`** (`0 failed, 0 skipped`), `pip check` -> `No broken requirements found.`

---

## 1. Tóm tắt Điều hành (Executive Summary)

Theo quyết định **`CHANGE BEFORE FORMAL BENCHMARK`** của Tech Lead sau khi rà soát Pilot v1 (`08-e01-t09-gemini-smoke-and-pilot-report.md`) và file `blind_eval_sheet.csv`, nhóm kỹ thuật đã hoàn tất gói khắc phục có trọng tâm **`R01`–`R06`** hoàn toàn ở chế độ ngoại tuyến (**`0` cuộc gọi Gemini API mới**, **`0` model Ollama mới**, bảo toàn nguyên vẹn toàn bộ artifacts của **Pilot v1** tại [`runs/P06-E01/gemini_3.5_flash_lite_pilot/`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/)).

Các kết quả chính đã hoàn thành và kiểm chứng:
1. **Xác minh Git & Đồng bộ `origin/main`:** Nhánh `research/p06-autonomous-storytelling` ở commit `54066da` sạch hoàn toàn, không còn `MERGE_HEAD` hay conflict; bản merge từ `origin/main` không làm thay đổi bất kỳ tệp nào trong `experiments/sales-intelligence/autonomous-storytelling/`, và mốc `261/261` tests ban đầu vượt qua 100%.
2. **Làm rõ mâu thuẫn `blind_eval_sheet.csv`:** Phiếu `product_education_10m` (`5` samples `METHOD_A..METHOD_E` có câu mock cắt cụt) nằm ở tệp dry-run Phase 4 cũ ([`runs/P06-E01/human_eval/blind_eval_sheet.csv`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/human_eval/blind_eval_sheet.csv)). Phiếu chấm mù **đúng cho Pilot v1** đã được xuất chính xác và còn nguyên vẹn tại [`runs/P06-E01/gemini_3.5_flash_lite_pilot/human_eval/blind_eval_sheet.csv`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/human_eval/blind_eval_sheet.csv) (`2` samples trên `pilot_short_3sku_ext`, khớp hai run Gemini thật). Đã gia cố thêm metadata provenance (`dataset_profile`, `prompt_versions`, `exported_at_utc`) trong bảng ánh xạ bí mật `blind_key_mapping.private.json`.
3. **Khắc phục triệt để 6 nhóm vấn đề kỹ thuật (`R01`–`R06`):**
   - `R01`: Bổ sung `check_spoken_text_hygiene()` và chặn mọi rò rỉ `ev-...`, `clm-...`, `SKU-...`, mảnh JSON, tên trường nội bộ ở cả LangGraph (`verify_p05`), `ScriptFirstBaseline`, và `P05KnowledgeAdapter` (phòng thủ chiều sâu) mà không sửa code P05.
   - `R02`: Sửa schema OpenAPI của `ChunkDraftLLMOutput` & `UpfrontChunkDraftLLMOutput` để đưa `"cited_evidence_ids"` và `"covered_claim_ids"` vào `"required"`, bổ sung `validate_draft_evidence_attribution()` chặn mọi câu factual thiếu `cited_evidence_ids` (ngay cả khi có `stated_price_vnd`), vẫn cho phép câu `OPENING`/`TRANSITION_BRIDGE` thuần giao tiếp, và bỏ cơ chế copy mù `topic.allowed_claim_ids` trong `ScriptFirstBaseline`.
   - `R03` & `R05`: Nâng cấp prompt lên `v0.2` (`story_generation.txt`, `rewrite.txt`) và `baseline-script-first-v0.2`, bổ sung ngân sách từ `max_words` (`12–18 từ` cho `8.0s`), lọc `mandatory_messages` theo đúng `active_sku_id`, bỏ yêu cầu lặp tên sản phẩm + giá ở mọi chunk, giữ nguyên trần `8.0s` (`PROPOSED` tại `P-INT`), và thêm `check_topic_objective_alignment()` làm guardrail chẩn đoán (tránh chặn cứng oan các câu paraphrase).
   - `R04`: Sửa lỗi cắt chuỗi `_MAX_FALLBACK_WORDS = 16` gây đuôi cụt `", thông tin."` trong `session_runner.py`, tạo tối đa `2` mẫu câu dự phòng tiếng Việt hoàn chỉnh theo từng SKU (`<= 8.0s`), và truyền `excluded_normalized_texts` qua `SafeFallbackSelector` để không lặp lại fallback máy móc mà rút lui an toàn `SAFE_ABORT_NO_CANDIDATE` khi cạn mẫu hợp lệ.
   - `R06`: Phân tách chi tiết nguyên nhân từng call lãng phí của Pilot v1 (`1/6` ở Script-first; `10/16` ở LangGraph), bổ sung `_summarize_partial_token_usage()` vào `run_gemini_pilot.py` tách rạch ròi `partial_measured_*` tokens với các call `UNAVAILABLE`.
4. **Dừng tại Cổng Phê duyệt Pilot v2:** Toàn bộ **`279/279` tests pass offline**. Hệ thống sẵn sàng chờ phê duyệt ngân sách mới (`<= 3` Smoke + `<= 25` Pilot v2 = `<= 28` requests) để chạy vào thư mục cô lập `gemini_3.5_flash_lite_pilot_v2`.

---

## 2. Xác minh Git & Ngữ cảnh Đồng bộ từ `origin/main`

| Tiêu chí kiểm tra | Kết quả xác minh thực tế | Ghi chú |
|---|---|---|
| Current branch | `research/p06-autonomous-storytelling` | Theo `git branch --show-current` |
| Commit hiện tại trước sửa | `54066da` | Merge commit đồng bộ từ `origin/main` (`484afab`) |
| Trạng thái merge (`MERGE_HEAD` / conflict) | `MERGE_HEAD=False`, `0` unmerged paths | Merge hoàn tất sạch trước khi bắt đầu |
| Tác động từ `origin/main` tới P06 | `git diff --stat 54066da^1 54066da -- experiments/sales-intelligence/autonomous-storytelling/` -> **trống (`0` tệp)** | Các thay đổi mới trên `main` nằm ở `apps/web/`, docs hệ thống và `p07` |
| Mốc hồi quy đầu phiên | `261 tests collected`, **`261 passed in 23.32s`**, `pip check` -> `No broken requirements found.` | Khớp hoàn toàn mốc trước đó |

---

## 3. Xác minh Artifacts Human Evaluation (`§4`)

Kiểm tra toàn bộ `4` bộ tệp `blind_eval_sheet.csv` hiện có dưới `experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/`:

| Đường dẫn tệp CSV | Scenario | Số mẫu (`blind_method_id`) | Nguồn Run & Model | Tình trạng & Giải thích |
|---|---|---|---|---|
| `runs/P06-E01/human_eval/blind_eval_sheet.csv` (`3,608 B`) | `product_education_10m` | `5` (`METHOD_A..E`) | Dry-run Mock/Deterministic Phase 4 (`2026-11-26T08:40Z`) | **Tệp mock sweep cũ ở cấp gốc**; có câu mock bị `_clamp_word_window(16)` cắt cụt (`"tỉnh Đắk."`). **Không dùng để chấm Pilot Gemini.** |
| `runs/P06-E01/post_fix_sweep_product_education_10m/human_eval/blind_eval_sheet.csv` (`3,608 B`) | `product_education_10m` | `5` (`METHOD_A..E`) | Dry-run Mock/Deterministic Phase 4 (`2026-11-26T08:58Z`) | Bản sao kết xuất Phase 4 sweep (`mock`). |
| `runs/P06-E01/offline_ext_v1_dryrun/human_eval/blind_eval_sheet.csv` (`19,120 B`) | `product_education_10m_ext` | `5` (`METHOD_A..E`) | Dry-run Phase 5 readiness (`mock`) | Thuộc kiểm thử mở rộng `e01_ext_v1` ngoại tuyến. |
| [`runs/P06-E01/gemini_3.5_flash_lite_pilot/human_eval/blind_eval_sheet.csv`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot/human_eval/blind_eval_sheet.csv) (`1,723 B`) | **`pilot_short_3sku_ext`** | **`2` (`METHOD_A`, `METHOD_B`)** | **Pilot v1 Gemini 3.5 Flash-Lite thật** (`...862ba71f` = LangGraph `W=5`, `...cae3af15` = Script-first) | **ĐÂY LÀ FILE CHẤM MÙ ĐÚNG CỦA PILOT v1.** Khớp nguyên văn 9 turns & 6 turns Gemini thật; cột điểm để trống hoàn toàn; không rò tên phương pháp/model. |

**Kiểm tra logic export (`src/p06/evaluation/human_eval.py` & `models.py`):**
- Hàm `export_blind_human_eval_sheets()` không cắt xén text (`[idx + 1] {entry.text}`); hiện tượng câu bị cắt cụt bắt nguồn từ thượng nguồn (`_MAX_FALLBACK_WORDS = 16` trong `session_runner.py` và `_MAX_MOCK_WORDS = 16` trong `mock_fixtures.py`).
- **Gia cố Provenance:** Đã thêm `dataset_profile`, `prompt_versions`, và `exported_at_utc` vào `HumanEvalBlindMapping` (chỉ ghi vào tệp bí mật `blind_key_mapping.private.json`, không đưa vào `blind_eval_sheet.csv` / `.jsonl` để bảo toàn tuyệt đối nguyên tắc chấm mù).

---

## 4. Phân tích Nguyên nhân gốc các Lỗi Pilot v1 (`R01`–`R06`)

### 4.1. Phiên bản Pilot v1 (Baseline Tham chiếu Cố định)
- **Model & Sampling:** `gemini-3.5-flash-lite` (`thinking_level: "MINIMAL"`, `min_request_interval_sec: 6.0`, `temperature: 0.3`, `top_p: 0.9`, `max_tokens: 1024`, `seed: 42`, `timeout_sec: 30`), Free Tier (`0 USD`, `SYNTHETIC` only).
- **Prompt versions Pilot v1:** `story_generation.txt = v0.1`, `rewrite.txt = v0.1`, `story_planner.txt = v0.1`, `baseline_script_first = baseline-script-first-v0.1`.
- **Biến cấu hình Pilot v1:** `dataset_profile = "e01_ext_v1"`, `scenario = "pilot_short_3sku_ext"`, `max_chunk_duration_sec = 8.0`, `min_chunks_per_topic = 1`, `max_turns = 20`, `max_rewrite_retries = 2`.

### 4.2. Nguyên nhân gốc từng lỗi

1. **`R01` — Rò rỉ Metadata Nội bộ (`(ev-e01-ext-macadamia-harvest, ev-e01-ext-macadamia-sensory)` ở Script-first Turn `[4]`):**
   - Prompt `_UPFRONT_SYSTEM_PROMPT_TEMPLATE` (`v0.1`) chỉ yêu cầu *"trích dẫn đúng `evidence_id` từ `approved_chunks`"* mà không cấm rõ việc nhúng mã vào `"text"`; `story_generation.txt` / `rewrite.txt` (`v0.1`) cũng chưa cấm tường minh mẫu `ev-*`, `clm-*`, `SKU-*`, `topic-*`.
   - Không có lớp kiểm tra vệ sinh văn bản (`spoken_text_hygiene`) ở cả khâu tạo draft (`_common.py`, `script_first.py`) lẫn trong `P05KnowledgeAdapter` + `PublicationGate`.
2. **`R02` — Toàn bộ `6` lượt `PROACTIVE_STORY` của LangGraph có `cited_evidence_ids: []` & `covered_claim_ids: []`:**
   - **Không phải lỗi từ `_sanitize_gemini_response_schema`:** Sanitizer trong `gemini_provider.py` giữ nguyên `"required"` và `"minItems"`. Nguyên nhân đầu tiên là `ChunkDraftLLMOutput` (`draft_dtos.py:153,158`) dùng `Field(default_factory=list)` khiến Pydantic v2 sinh JSON Schema với `"required": ["text"]` — bỏ rơi `cited_evidence_ids` và `covered_claim_ids` khỏi danh sách bắt buộc khi chạy `thinkingLevel=MINIMAL`.
   - **Lỗ hổng ở P05 (`publication_gate.py:245-247`):** P05 chỉ chặn `MISSING_EVIDENCE` khi *đồng thời* `cited_evidence_ids` rỗng VÀ `stated_price_vnd is None`. Khi LangGraph chèn giá `159.000đ`/`245.000đ`/`195.000đ` vào câu, `PublicationGate` cho phép `ALLOW` dù `cited_evidence_ids=[]`. (Vì contract P05 ngoài phạm vi chỉnh sửa và đã có test contract `test_case5` khóa hành vi P05, P06 phải tự chặn lỗ hổng này ở tầng candidate/verification của P06.)
   - **Bất cân xứng ở `ScriptFirstBaseline`:** `UpfrontChunkDraftLLMOutput` không có `covered_claim_ids`, và `script_first.py:790` gán mù toàn bộ `tuple(item.topic.allowed_claim_ids)` bất kể LLM có thực sự truyền đạt claim đó hay không.
3. **`R03` — Giới hạn `8.0s` và Prompt khiến LLM hy sinh `talking_points` để giữ `"<Tên SKU> + <Giá>"`:**
   - `VirtualClock` tính `DEFAULT_SPEECH_WORDS_PER_SEC = 2.6` -> `8.0s` đồng nghĩa trần cứng **`20` từ** (`21/2.6 = 8.08s > 8s`).
   - Trong `v0.1`, LangGraph prompt chỉ truyền `max_duration_sec = "8"` mà không truyền `max_words`; phản hồi `OVER_MAX_DURATION_SEC` không báo số từ thực tế; và `build_base_prompt_variables()` nhồi toàn bộ `mandatory_messages` của **cả 3 SKU** vào mọi lượt. Tên đầy đủ mỗi SKU đã chiếm `7–13` từ, nên khi bị reject cả `OVER_MAX_DURATION_SEC` lẫn `MISSING_EVIDENCE`, LLM cắt sạch `talking_points` để giữ tên + khối lượng + giá nhằm lọt qua cổng.
   - **Đối chiếu kiến trúc chuẩn:** Tài liệu `HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx` §3.4 (`P-INT`) đặt `"Target chunk 3–5s; chunk max 8s"` ở trạng thái **`PROPOSED`** (cấu hình khởi điểm cho simulator, không phải ràng buộc khóa cứng bởi Founder), tương thích với ngưỡng cắt `<= 5s` khi có bình luận P08 chen ngang. Vì vậy trước tiên cần tối ưu trong mức `8.0s` qua prompt/word budget trước khi đề xuất nới lên `10–12s`.
4. **`R04` — Câu fallback `", thông tin."` & lặp `3` lần (`turns 0, 2, 3`):**
   - `session_runner.py:85,173-177` ghép `f"{evidence.sku_name}, giá niêm yết {price_display}, thông tin đã được kiểm chứng."` rồi cắt cứng `words[:16]`. Vì `sku_name` dài `10–11` từ, lát cắt rơi đúng vào giữa cụm thành `", thông tin."`.
   - `_build_default_fallbacks_by_sku()` chỉ tạo **1** fallback/SKU và `SafeFallbackSelector` không kiểm tra các fallback đã phát trước đó trong `played_history`, dẫn đến lặp 3 lần y hệt nhau (`exact_normalized_text_replay_count = 2`).
5. **`R05` — Chênh lệch 4 tầng Coverage trong Pilot v1:**
   - **Script-first (`cae3af15`):** `5/6` (`83.33%`) Playback-confirmed topic coverage (`topic-pilot-tea-02` mất do `HTTP 503`); `5/6` Claim coverage (nhờ copy `allowed_claim_ids`); Thực tế ngữ nghĩa: `4 FULL + 2 PARTIAL` (nhưng Turn `[4]` rò rỉ raw ID `ev-...`).
   - **LangGraph (`862ba71f`):** `6/6` (`100%`) Playback-confirmed topic coverage (do `covered_topic_ids` được gán cứng từ `topic.topic_id` ngay cả khi văn bản chỉ là stub giá); **`0/6` (`0%`)** Claim coverage (`covered_claim_ids=[]`); Thực tế ngữ nghĩa: chỉ `2 FULL + 1 PARTIAL + 3 MISS/stub`; Human-assessed coverage chưa chấm.
6. **`R06` — Phân loại toàn bộ Wasted Calls & Partial Tokens:**
   - **`script_first_upfront_llm` (`6` calls, `1` wasted = `16.7%`):**
     - Calls `0, 1, 2, 4, 5`: Thành công `MEASURED` -> tổng từng phần **`9,719` input + `766` output = `10,485` tokens** (`0` wasted measured tokens).
     - Call `3` (`turn-...0001-n1`, `topic-pilot-tea-02`): Lãng phí do **`HTTP 503 UNAVAILABLE` (`ProviderTransportError`)** (`token_usage_source = UNAVAILABLE`). Vì `max_retries=0` và phát tuần tự tiến tới topic kế tiếp, `topic-pilot-tea-02` bị bỏ lỡ vĩnh viễn.
   - **`langgraph_structured_story` W=5 (`16` calls, `10` wasted = `62.5%`):**
     - `5` calls lãng phí do **`OVER_MAX_DURATION_SEC`**: `call_index = 0` (`10.38s`), `3` (`10.38s`), `8` (`10.38s`), `12` (`10.77s`), `13` (`9.23s`).
     - `3` calls lãng phí do **`HTTP 503 UNAVAILABLE` (`ProviderTransportError`)**: `call_index = 2`, `6`, `7` (`is_retryable=False` -> đi thẳng `safe_fallback` không avançar topic nhờ `I-06`, giúp hồi phục đạt `100%` topic coverage nhưng sinh `3` lượt fallback lặp).
     - `2` calls lãng phí do **P05 `REJECTED: MISSING_EVIDENCE`**: `call_index = 1`, `4` (`cited_evidence_ids=[]` và `stated_price_vnd=null`).
     - `0` calls do lặp từ, `0` calls do schema error.
     - `13/16` calls `MEASURED` cho tổng từng phần **`27,633` input + `847` output = `28,480` tokens** (riêng `7` calls lãng phí đo được tiêu tốn **`14,313` in + `464` out = `14,777` tokens = `51.9%`**). `token_usage.json` tổng hợp giữ nguyên `UNAVAILABLE` cho cả 2 runs do có call lỗi.

---

## 5. Kết quả Kiểm toán Độc lập từ Subagents (Scout A & Scout B)

Phiên đã kích hoạt song song 2 read-only Scouts để cô lập phân tích bằng chứng:
- **Scout A (Generation & Safety Reviewer):** Xác nhận cơ chế lỗ hổng `publication_gate.py:245-247`, chứng minh `_sanitize_gemini_response_schema` không xóa `required`/`minItems`, tìm ra phép cắt `words[:16]` ở `session_runner.py:175-177`, kiểm tra tính chất `PROPOSED` của `P-INT` (`8s`) trong kiến trúc baseline v1.2, và định vị các đường dẫn prompt/validator dùng chung.
- **Scout B (Evaluation & Research Reviewer):** Kiểm kê toàn bộ `4` tệp `blind_eval_sheet.csv` phân định rạch ròi tệp mock sweep cũ với tệp Pilot thật, lập bảng phân rã `6 + 16` model calls theo từng `call_index`, đối chiếu từng `talking_points` của 6 topics trên `pilot_short_3sku_ext`, và phát hiện `0` regression tests từng kiểm tra trực tiếp `run_gemini_pilot.py` hay chữ ký `verify_candidate`.

---

## 6. Các Thay đổi Mã nguồn & Prompt Đã Triển khai

| Nhóm | Tệp thay đổi / tạo mới | Mô tả kỹ thuật chính xác |
|---|---|---|
| Guardrails `R01` | [`src/p06/guardrails/spoken_text_hygiene.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/guardrails/spoken_text_hygiene.py) *(mới)* | `check_spoken_text_hygiene()` phát hiện mã `ev-*`/`clm-*`/`topic-*`/`arc-*`/`SKU-*`, mảnh JSON và tên trường DTO nội bộ; không âm thầm sửa câu chữ |
| Guardrails `R02/R05` | [`src/p06/guardrails/evidence_attribution.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/guardrails/evidence_attribution.py) *(mới)* | `validate_draft_evidence_attribution()` bắt buộc `cited_evidence_ids` hợp lệ cho lời thoại factual (kể cả khi có giá), chặn ID sai/chéo SKU, hỗ trợ non-factual bridge; `check_topic_objective_alignment()` chẩn đoán mất `talking_points` |
| Guardrails Export | [`src/p06/guardrails/__init__.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/guardrails/__init__.py) | Tái xuất các hàm và model kết quả guardrail mới |
| Guardrails `R04` | [`src/p06/guardrails/fallback_selector.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/guardrails/fallback_selector.py) | Thêm `normalize_fallback_text()` và `excluded_normalized_texts` vào `SafeFallbackSelector.select_safe_fallback()` để bỏ qua fallback đã phát |
| Schemas DTO `R02` | [`src/p06/planning/draft_dtos.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/planning/draft_dtos.py) | Thêm `_require_citation_fields_in_json_schema` đưa `"cited_evidence_ids"` và `"covered_claim_ids"` vào `required` trên OpenAPI schema của `ChunkDraftLLMOutput` |
| Prompts `v0.2` | [`prompts/story_generation.txt`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/prompts/story_generation.txt), [`prompts/rewrite.txt`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/prompts/rewrite.txt) | Nâng lên `PROMPT_VERSION: v0.2`; thêm `{{max_words}}`, `{{target_words_range}}`, `{{allowed_evidence_ids}}`, `{{allowed_claim_ids}}`; ưu tiên `talking_points`, cấm lặp tên+giá thừa, cấm đưa ID nội bộ vào `"text"` |
| LangGraph `R01..R05` | [`src/p06/agent/nodes/_common.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/agent/nodes/_common.py), [`verify_p05.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/agent/nodes/verify_p05.py), [`safe_fallback.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/agent/nodes/safe_fallback.py) | Lọc `mandatory_messages` theo SKU, tính `max_words`, làm giàu thông báo `OVER_MAX_DURATION_SEC`; chạy kiểm tra `R01`/`R02` trong `verify_p05` (giữ `check_topic_objective_alignment` làm guardrail chẩn đoán); truyền `excluded_normalized_texts` từ `played_history` trong `safe_fallback` |
| P05 Adapter Defense | [`src/p06/adapters/p05_knowledge_adapter.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/adapters/p05_knowledge_adapter.py) | Gọi `check_spoken_text_hygiene()` ở `SINGLE_SKU`, `MULTI_SKU_COMPARE`, `UNRESOLVED_SKU` (`INTERNAL_METADATA_LEAK`), không sửa module P05 gốc |
| Script-First `v0.2` | [`src/p06/baselines/script_first.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/baselines/script_first.py) | Nâng `_UPFRONT_PROMPT_VERSION = "baseline-script-first-v0.2"`, thêm `covered_claim_ids` + `required` schema, kiểm tra `R01`/`R02` ở `_build_upfront_item()`, ghi nhận `declared_claim_ids` thật (bỏ gán mù `topic.allowed_claim_ids`), tránh lặp fallback qua `excluded_normalized_texts` |
| Fallback Builder `R04` | [`src/p06/runner/session_runner.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/runner/session_runner.py) | Thay phép cắt `_MAX_FALLBACK_WORDS=16` bằng `_select_complete_fallback_texts()` sinh tối đa `2` câu tiếng Việt hoàn chỉnh, sạch, `<= 8.0s` từ `ProductFact` |
| Human Eval & Runner | [`src/p06/evaluation/models.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/evaluation/models.py), [`human_eval.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/src/p06/evaluation/human_eval.py), [`experiments/p06_e01_no_comments/run_gemini_pilot.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_gemini_pilot.py) | Thêm `dataset_profile`, `prompt_versions`, `exported_at_utc` vào `blind_key_mapping.private.json`; cập nhật biến prompt `v0.2` ở Stage A và thêm `_summarize_partial_token_usage()` + `prompt_versions` vào `stage_b_pilot_summary.json` |

---

## 7. Ví dụ Trước / Sau từ Offline Fixtures (KHÔNG PHẢI LLM THẬT)

> [!IMPORTANT]
> Các ví dụ "Sau khi vá" dưới đây được kiểm chứng bằng **fixture `MockLLMProvider` và bộ sinh fallback tất định hoàn toàn ngoại tuyến** để minh họa hành vi kiểm soát của code/validator mới — **KHÔNG phải** kết quả sinh từ `gemini-3.5-flash-lite` thật (sẽ kiểm chứng ở Pilot v2 sau khi được phê duyệt).

| Lỗi Pilot v1 (Dữ liệu thật v1) | Hành vi Sau khi vá trên **Offline Mock/Fixture (NOT REAL LLM)** | Kết quả Kiểm soát |
|---|---|---|
| `R01` Script-first `[4]`: `"...giòn tan (ev-e01-ext-macadamia-harvest, ev-e01-ext-macadamia-sensory)."` -> P05 `ALLOW` | `check_spoken_text_hygiene` + `P05KnowledgeAdapter` + `verify_p05` bắt `INTERNAL_METADATA_LEAK`; LangGraph buộc rewrite loại bỏ `ev-...`, Script-first hủy candidate rò rỉ | **Đã chặn 100% ở cả 2 phương pháp** |
| `R02` LangGraph: `cited_evidence_ids: []`, `covered_claim_ids: []`, `stated_price_vnd: 159000` -> `ALLOW` | OpenAPI Schema đưa cả 2 mảng vào `required`; `validate_draft_evidence_attribution` từ chối `MISSING_EVIDENCE_ATTRIBUTION` nếu factual còn trống citation | **Khép lỗ hổng thiếu citation** |
| `R03/R05` LangGraph `[6]`: `"Trà Shan Tuyết 200g giá niêm yết 245.000đ."` (mất "quà biếu" & "hút chân không") | `OVER_MAX_DURATION_SEC` phản hồi rõ số từ vs `12–18 từ` & giữ `talking_points`; `check_topic_objective_alignment` gắn cờ `TOPIC_OBJECTIVE_MISSED` trên stub giá | **Hướng dẫn bảo toàn ngữ nghĩa chủ đề** |
| `R04` Fallback: `"...giá niêm yết 159.000đ, thông tin."` lặp 3 lần (`turns 0, 2, 3`) | `_build_default_fallbacks_by_sku` sinh 2 câu hoàn chỉnh (vd: `"Mật ong hoa cà phê Đắk Lắk nguyên chất 500ml hiện có giá niêm yết 159.000đ."` và biến thể nguồn gốc/giá niêm yết); hết mẫu mới sẽ sang `SAFE_ABORT_NO_CANDIDATE` | **Không cắt cụt câu, không lặp máy móc** |

---

## 8. Kiểm thử Hồi quy Ngoại tuyến (Regression Tests)

Đã viết mới [`tests/unit/test_pilot_remediation.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/tests/unit/test_pilot_remediation.py) (`18` test cases) và cập nhật [`tests/unit/test_planning_and_prompts.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/tests/unit/test_planning_and_prompts.py), [`tests/unit/test_script_first_baseline.py`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/tests/unit/test_script_first_baseline.py).

Độ phủ kiểm thử xác nhận đạt toàn bộ 12 nhóm yêu cầu (`§7`):
1. Chặn raw evidence/claim/SKU IDs & mảnh JSON ở `spoken_text_hygiene`, LangGraph, ScriptFirst và `P05KnowledgeAdapter`.
2. Từ chối thiếu `cited_evidence_ids` trên câu factual kể cả khi có `stated_price_vnd` (giữ nguyên hợp đồng `test_case5` của P05).
3. Chặn ID sai hoặc chéo SKU ở `cited_evidence_ids` và mã `clm-...` giả ở `covered_claim_ids`.
4. Cho phép `OPENING` / `TRANSITION_BRIDGE` phi dữ kiện (`fact_refs=[]`, `stated_price_vnd=None`, `mentions_ocop=False`) với `cited_evidence_ids=[]`.
5. `check_topic_objective_alignment()` nhận diện stub báo giá mất `talking_points` và vượt qua khi có câu viết lại bám chủ đề; `OVER_MAX_DURATION_SEC` chứa số từ + ngân sách từ + giữ `talking_points`; `build_base_prompt_variables` lọc `mandatory_messages` theo `active_sku_id`.
6. `_build_default_fallbacks_by_sku()` tạo câu tiếng Việt hoàn chỉnh, sạch, `<= 8.0s`, qua kiểm định sống P05.
7. `SafeFallbackSelector` loại trừ fallback đã phát; hết fallback hợp lệ dẫn tới `SAFE_ABORT_NO_CANDIDATE`.
8. Bất biến `I-06` & `I-02`: fallback và safe abort không làm tăng `completed_topic_ids`.
9. `export_blind_human_eval_sheets()` ghi `dataset_profile`, `prompt_versions`, `exported_at_utc` vào `blind_key_mapping.private.json` mà không rò sang CSV/JSONL.
10. `_sanitize_gemini_response_schema` giữ `"cited_evidence_ids"` và `"covered_claim_ids"` trong `required`, loại `exclusiveMinimum` cho cả `ChunkDraftLLMOutput` và `UpfrontChunkDraftLLMOutput`.
11. Kiểm thử ngoại tuyến `run_gemini_pilot.py` bằng `FakeGeminiRestClient` (`GeminiRawResponse`): xác minh Stage A gọi đúng `verify_candidate(..., verified_at=...)`, `_summarize_partial_token_usage` tách rạch ròi `partial_measured_*` tokens với failed calls, và cô lập `--output-dir`.
12. Dry-run toàn bộ `pilot_short_3sku_ext` cho cả `ScriptFirstBaseline (UPFRONT_LLM)` và `LangGraph (W=5)` trong `tmp_path`.

**Kết quả chạy thực tế sau chỉnh sửa cuối cùng:**
- `.\.venv\Scripts\python.exe -m pytest experiments/sales-intelligence/autonomous-storytelling/tests --collect-only -q` -> **`279 tests collected in 1.61s`**
- `.\.venv\Scripts\python.exe -m pytest experiments/sales-intelligence/autonomous-storytelling/tests -q` -> **`279 passed in 27.57s`** (`0 failed, 0 skipped`)
- `.\.venv\Scripts\python.exe -m pip check` -> **`No broken requirements found.`**

---

## 9. Xác minh Bất biến Kiến trúc (`I-02`, `I-04`, `I-06`, `P-INT 8s`)

- **`I-02` (`Generated != Verified != Played`):** Mọi output từ LLM tiếp tục khởi tạo ở `DRAFT`, qua kiểm tra P05 sống trước khi phát và chỉ cập nhật tiến độ sau `PlaybackCompleted (APPLIED)`.
- **`I-04` (Khóa `active_sku_id` & `mandatory_messages`):** Bộ lọc `mandatory_messages` mới chỉ thu hẹp ngữ cảnh prompt về đúng `active_sku_id`, không làm thay đổi quyền hay khả năng chuyển SKU của `ArcSequencer`.
- **`I-06` (Non-advancing fallback & no mechanical replay):** `FALLBACK_PREAPPROVED` vẫn giữ `covered_topic_ids=[]` (`next_topic_id_hint=None`), nay bổ sung thêm chống lặp máy móc để tránh spam câu dự phòng giống hệt nhau.
- **Ràng buộc `P-INT = 8.0s`:** Hiện giữ nguyên `8.0s` (`12–18 từ` khuyến nghị, trần `20` từ) để đồng bộ `P-INT` (`PROPOSED`) và đảm bảo điểm ngắt bình luận P08 (`<= 5s`). Nếu sau Pilot v2 thực tế trên Gemini vẫn ghi nhận tỷ lệ cắt câu hoặc `OVER_MAX_DURATION_SEC` cao do đặc thù câu tiếng Việt có tên SKU dài, báo cáo Pilot v2 sẽ trình phương án thử nghiệm A/B `8s` vs `10–12s` (`26–31` từ) xin phê duyệt rõ ràng trước khi điều chỉnh hằng số liên module.

---

## 10. Giao thức Tái kiểm chứng Pilot v2 (`gemini_3.5_flash_lite_pilot_v2`)

Để so sánh công bằng tác động của gói sửa lỗi `v0.2` so với Pilot v1 (`v0.1`), Pilot v2 giữ cố định mọi biến kiểm soát:
- **Model Config:** [`configs/models/gemini_3.5_flash_lite_free.yaml`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/configs/models/gemini_3.5_flash_lite_free.yaml) (`gemini-3.5-flash-lite`, Free Tier, `thinking_level=MINIMAL`, `min_request_interval_sec=6.0`, `temperature=0.3`, `seed=42`, `SYNTHETIC` only).
- **Dataset & Scenario:** `e01_ext_v1` / `pilot_short_3sku_ext` (`3` SKU, `6` mandatory topics, target `300s`).
- **Thư mục cô lập riêng:** `experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2/` (tuyệt đối không ghi đè Pilot v1).
- **Lệnh thực thi dự kiến (CHỈ CHẠY SAU KHI CÓ PHÊ DUYỆT `PILOT V2`):**
  1. Stage A Smoke v2 (`<= 3` requests):  
     `.\.venv\Scripts\python.exe experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_gemini_pilot.py --stage smoke --output-dir experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2`
  2. Stage B Pilot v2 (`<= 25` requests):  
     `.\.venv\Scripts\python.exe experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_gemini_pilot.py --stage pilot --output-dir experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/gemini_3.5_flash_lite_pilot_v2`

---

## 11. Đề xuất Ngân sách Request & Điều kiện Phê duyệt Pilot v2

- **Ngân sách đề xuất mới (sổ cái mới tại `gemini_3.5_flash_lite_pilot_v2/budget_ledger.json`, KHÔNG dùng lại 3 slot dư của Pilot v1):**
  - Smoke Re-validation (Stage A v2): tối đa **`3` requests**.
  - Pilot v2 (Stage B v2 — gồm cả `failed calls`, `retries`, `rewrites`): tối đa **`25` requests**.
  - **Tổng đề xuất tối đa:** **`28` requests mới** (`0 USD`, Free Tier, tuần tự `>= 6.0s` / request, dừng ngay khi gặp `HTTP 429`).
- **Điều kiện trước khi kích hoạt:**
  1. Tech Lead xác nhận còn đủ hạn mức **RPD** trong ngày trên Google AI Studio (`Default Gemini Project`) và **RPM = 15**, **TPM = 250,000**.
  2. Không gộp lẫn kết quả Pilot v1 (`v0.1`) và Pilot v2 (`v0.2`) thành cùng một bảng benchmark chính thức.
- **Trạng thái cổng:** **`AWAITING_PILOT_V2_EXECUTION_APPROVAL`**.

---

## 12. Giới hạn Còn lại & Khoảng trống Chờ Benchmark Chính thức

Những vấn đề vẫn chưa được giải quyết trong phạm vi phiên remediation này (theo đúng `SCOPE FREEZE`):
1. **Chưa kiểm chứng trên Gemini thật sau bản vá `v0.2`:** Các khẳng định chất lượng tiếng Việt, độ bám `talking_points` và tỷ lệ citation thật vẫn chờ kết quả Pilot v2.
2. **Độ dài dataset cho phiên `10–30` phút & độ nhạy History Window `W`:** Chưa chạy thực nghiệm dài để đo suy giảm/lặp khi `W ∈ {5, 10, 20}`.
3. **Lỗ hổng ngữ nghĩa P05:** Chưa có nhãn factual độc lập (`GoldFactualLabel`) và chưa kiểm tra entailment cho claim paraphrased (không cho phép coi `P05 ALLOW` là chân lý tuyệt đối).
4. **Hiệu chỉnh Human Rubric & Acceptance Criteria:** Phiếu Pilot v1 chưa được con người chấm; ngưỡng chấp nhận benchmark chính thức chưa được khóa.
5. **Nhiễu `HTTP 503` từ hạ tầng Free Tier Google:** Cần tách bạch rõ call lỗi do `HTTP 503` với lỗi suy luận của agent khi phân tích hiệu quả thuật toán.
6. **Tier 2 Ollama CPU:** Vẫn ở trạng thái **`DEFERRED WITH USER APPROVAL`**.

---

## 13. Tóm tắt Thay đổi Git (`research/p06-autonomous-storytelling`)

- **Phạm vi thay đổi:** `100%` nằm trong `experiments/sales-intelligence/autonomous-storytelling/` (`16` tệp sửa + `3` tệp mới về code/tests trước khi thêm báo cáo này và cập nhật `docs/README.md` + `AGENTS.md`).
- **Toàn vẹn dữ liệu & bằng chứng cũ:** `runs/P06-E01/gemini_3.5_flash_lite_pilot/` (Pilot v1), `data/*/e01_*.json`, `configs/models/gemini_flash.yaml`, module P05 (`knowledge-verification/`), `apps/`, `packages/` không bị chỉnh sửa.
- **Không tự ý commit, push, merge hoặc tag.**
