# Báo cáo Sẵn sàng Thực nghiệm & Giao thức Phase 5 (`E01-T09`) — HOSTRA AI P06

**Module:** `experiments/sales-intelligence/autonomous-storytelling/` (`P06`)  
**Nhiệm vụ:** `Phase 5 — E01-T09: Offline Readiness & Staged Protocol`  
**Nhánh Git:** `research/p06-autonomous-storytelling` (nền checkpoint `p06-checkpoint-05-evaluation` / commit `8a13a8b`)  
**Trạng thái hiện tại:** `AWAITING_EXECUTION_APPROVAL` *(Đã hoàn tất 100% chuẩn bị ngoại tuyến, xác minh `259/259` tests và `offline_ext_v1_dryrun`; **CHƯA** tải mô hình mới hay gọi Ollama/Gemini thật)*  
**Ngày cập nhật:** `2026-11-26`

---

## 1. Tóm tắt điều hành (Executive Summary)

Báo cáo này ghi nhận toàn bộ công tác chuẩn bị ngoại tuyến, khắc phục các lỗ hổng cổng review từ Phase 4, mở rộng bộ dữ liệu mô phỏng có kiểm soát (`e01_ext_v1`), hoàn thiện hai adapter provider thật (`OllamaLocalProvider`, `GeminiRestClient`), thiết lập rào chắn ngân sách và giao thức thực nghiệm phân tầng cho **`E01-T09`**.

> [!IMPORTANT]
> **Nguyên tắc dừng đúng Cổng Phê duyệt (Real Provider Execution Approval Gate):**
> - Trong phiên chuẩn bị này, toàn bộ kiểm thử chạy **100% ngoại tuyến** (`MockLLMProvider` và `httpx.MockTransport`).
> - Không có cuộc gọi HTTP thật nào tới Ollama hay Gemini, không tải thêm trọng số Ollama, không kích hoạt billing hay sửa đổi bộ fixture đóng băng `data/*/e01_*.json`.
> - Mọi thông số phần cứng, giá API chính thức, khả năng tải mô hình và giới hạn thuật toán đều được báo cáo trung thực kèm rủi ro.

---

## 2. Khắc phục các phát hiện cổng Review Phase 4 ảnh hưởng `E01-T09`

1. **Ngữ nghĩa 3 giá trị cho Hard Gates (`GateStatus`):**
   - Trong [src/p06/evaluation/models.py](../src/p06/evaluation/models.py) và [src/p06/evaluation/evaluator.py](../src/p06/evaluation/evaluator.py), tách rạch ròi `structural_hard_gates_status`, `factual_safety_gate_status` và `overall_gate_status` theo 3 giá trị `PASS | FAIL | NOT_EVALUATED`.
   - Khi thiếu `GoldFactualLabel`, `overall_gate_status` bắt buộc giữ **`NOT_EVALUATED`** (không bao giờ tự động đánh đồng cấu trúc đạt thành `PASS` toàn cục). Chỉ khi có tập nhãn chuẩn `GoldFactualLabel` xác minh cả structural gates lẫn `verifier_false_accept_count == 0`, `overall_gate_status` mới đạt `PASS`.
2. **Kiểm soát biến cố định nghiêm ngặt trong `compare_runs()`:**
   - Trong [src/p06/evaluation/comparison.py](../src/p06/evaluation/comparison.py), nâng `TARGET_DURATION_MISMATCH` lên mức `ERROR` (`compatible=False`), bổ sung đối chiếu `story_plan_sha256`, `max_chunk_duration_sec`, `sku_scheduling_policy`, `min_chunks_per_topic`, `simulator_assumptions` (bỏ qua `virtual_clock_start_utc`), `seed`, `repetition_config`, `rewrite_budget` (giữa các lượt LangGraph), `LLM_PROVIDER_OR_MODEL_MISMATCH` và `SAMPLING_PARAMS_MISMATCH` giữa các lượt dùng LLM (miễn trừ riêng `script_first_deterministic`).
3. **Kiểm chứng ranh giới cửa sổ `W` và đính chính tài liệu Phase 4:**
   - Đối chiếu [src/p06/memory/played_history.py](../src/p06/memory/played_history.py) với [src/p06/evaluation/metrics/repetition.py](../src/p06/evaluation/metrics/repetition.py): hai bên đồng nhất toán học (lượt cách đúng `W` bước vẫn nằm trong `_all_turns[-W:]`; chỉ khoảng cách `>= W + 1`, tức `j < i - W`, mới ở ngoài cửa sổ). Đã thêm unit test ranh giới `W-1`, `W`, `W+1` trong [tests/unit/test_evaluation_metrics.py](../tests/unit/test_evaluation_metrics.py).
   - Đã đính chính lại các diễn đạt toán học trong [06-phase4-evaluation-runner-e01-t08-report.md](./06-phase4-evaluation-runner-e01-t08-report.md) (`0.0308` cho `55.386s / 1800s`, ranh giới `j < i - W`, và ghi rõ `script_first_upfront_llm` chuẩn bị upfront theo từng SKU khi chuyển SKU tuần tự).

---

## 3. Bộ dữ liệu Synthetic mở rộng `e01_ext_v1` & Cơ chế `min_chunks_per_topic`

### 3.1 Lý do mở rộng (giữ nguyên bộ gốc `e01` đóng băng)

Bộ fixture `e01` ban đầu chỉ gồm `6–9` topic với `min_chunks_per_topic=1`, kết thúc phiên `10m`/`30m` chỉ sau ~6–9 lượt (`duration_fulfillment ≈ 0.03–0.09`). Số lượt này nhỏ hơn ngưỡng cửa sổ `W = 10` và `W = 20`, nên không thể phân biệt độ nhạy bộ nhớ giữa `W = 5`, `W = 10` và `W = 20` khi chạy mô hình thật.

Giải pháp: giữ **nguyên vẹn tuyệt đối** các tệp `data/*/e01_*.json` và bổ sung hồ sơ mới `dataset_profile: "e01_ext_v1"` (`data/*_ext_v1_*.json`):

| Thành phần | Đường dẫn | Quy mô & Thiết kế |
| :--- | :--- | :--- |
| Kho tri thức SKU | [data/products/e01_ext_v1_verified_skus.json](../data/products/e01_ext_v1_verified_skus.json) | 3 SKU dương tính (`SKU-HONEY-01`, `SKU-TEA-02`, `SKU-MACADAMIA-03`), tổng **30** `evidence_chunks` (`10` mảnh/SKU), đầy đủ `ALLOWED` / `REQUIRES_OFFICIAL_VERIFICATION` / `PROHIBITED` claims; không chứa yếu tố nhạy cảm cross-SKU trong single-SKU mode. |
| Mục tiêu Merchant | [data/merchant_goals/e01_ext_v1_goals.json](../data/merchant_goals/e01_ext_v1_goals.json) | 5 kịch bản mục tiêu tương ứng 1-1 với 5 `StoryPlan`. |
| Kế hoạch StoryPlan | [data/story_plans/e01_ext_v1_story_plans.json](../data/story_plans/e01_ext_v1_story_plans.json) | 5 plan `APPROVED` đạt `is_mvp_live_eligible() == True`: `product_education_10m_ext` (`18` topics), `brand_storytelling_10m_ext` (`18` topics), `sales_presentation_30m_ext` (`24` topics), `pilot_short_3sku_ext` (`6` topics — tách riêng cho pilot), và `window_sensitivity_stress_24t` (`24` topics bắt buộc liên tục). |

### 3.2 Cơ chế `min_chunks_per_topic` & Phát hiện thuật toán từ Dry-run

- Đã nối thông số `min_chunks_per_topic` xuyên suốt `ExperimentRunConfig` -> `GlobalTopicCoverage` -> `SimulatedPlaybackHarness` -> `ScriptFirstBaseline` (xoay vòng `talking_points` và `matching_chunks` theo `chunk_part`) -> `manifest.json` và `compare_runs()`.
- **Quan sát quan trọng khi kiểm thử `min_chunks_per_topic=2`:** Khi một topic chỉ gắn `1` `claim_id` duy nhất, lượt lặp lại topic ở vòng 2 (khi khoảng cách `< W`, ví dụ `W=10` trên 6 topic/SKU) sẽ kích hoạt cảnh báo `REPEATED_FACTS` (`fact_overlap_ratio >= 0.80` trên cùng `intent`) từ `RepetitionDetector` nếu mô hình không mở rộng sang góc nhìn/claim khác hoặc khía cạnh `evidence_id` khác của SKU. Đây là giả thuyết thực nghiệm trực tiếp cần theo dõi khi chạy Gemini thật với `min_chunks_per_topic=2` và với `window_sensitivity_stress_24t` (`min_chunks_per_topic=1`, `24` topic riêng biệt).

---

## 4. Kiểm kê Môi trường, Phần cứng & Mức sẵn sàng 2 Provider thật

### 4.1 Phần cứng & SDK cục bộ (đo trực tiếp trên workspace)

| Hạng mục | Giá trị đo được thực tế | Tác động & Rủi ro |
| :--- | :--- | :--- |
| Python runtime | `Python 3.13.2` (`.venv`), `pytest 9.2.0`, `httpx 0.28.1` | Không lỗi phụ thuộc (`pip check` sạch). Không cài thêm `google-genai` hay `ollama` SDK; dùng `httpx` trực tiếp. |
| CPU | `18` logical cores (`Intel64 Family 6 Model 170 Stepping 4`) | Suy luận Ollama thuần CPU sẽ có độ trễ lớn (10–40+ giây/lượt); tuyệt đối không gộp độ trễ CPU với Tier 3 Gemini. |
| RAM hệ thống | **`15.50 GB`** tổng, chỉ còn **`1.01 GB` trống** tại thời điểm đo (`93%` load) | **Rủi ro OOM/Swap cao:** nạp `qwen2.5:3b` (`1.9 GB`) hoặc `qwen3:1.7b` (`~1.4 GB`) sẽ gây phân trang nặng nếu không giải phóng RAM trước (`>= 3.5 GB` trống khuyến nghị). |
| Ổ đĩa & Ollama | C trống `86.7 GB`, G trống `211.6 GB`; `ollama 0.40.18` đã cài sẵn `qwen2.5:3b` (`1.9 GB`) | `qwen3:1.7b` và `qwen3:4b` **chưa** được tải. Biến môi trường `GEMINI_API_KEY` và `OLLAMA_BASE_URL` hiện chưa đặt. |

### 4.2 Khả năng sẵn sàng Adapter & Chính sách An toàn (Tier 2 & Tier 3)

- **Tier 2 — `OllamaLocalProvider` ([src/p06/providers/ollama_provider.py](../src/p06/providers/ollama_provider.py)):**
  - Bổ sung `think: Optional[bool]` (đặt `think: false` trong `configs/models/ollama_qwen3_1.7b.yaml` và `ollama_qwen3_4b.yaml`) truyền ở cấp gốc `/api/chat` để tắt luồng suy nghĩ dài của Qwen3 khi ép JSON schema trên CPU.
  - Bổ sung [configs/models/ollama_qwen2.5_3b.yaml](../configs/models/ollama_qwen2.5_3b.yaml) cho mô hình đã có sẵn trên máy.
  - Ánh xạ HTTP `429 -> ProviderRateLimitError`; `estimated_llm_cost_usd` được đánh dấu **`NOT_APPLICABLE`** (suy luận cục bộ không phát sinh phí token API).
- **Tier 3 — `GeminiRestClient` ([src/p06/providers/gemini_provider.py](../src/p06/providers/gemini_provider.py)):**
  - Triển khai qua `httpx.Client` gọi endpoint `generateContent`, đọc lười biến môi trường qua header `x-goog-api-key` (tuyệt đối không đưa khóa vào URL hay thông báo lỗi).
  - Làm sạch Pydantic JSON Schema (`_sanitize_gemini_response_schema`): giải `$ref`/`$defs`, chuyển `anyOf` với `null` sang `nullable: true`, loại bỏ `additionalProperties`/`title`/`default`/`examples` để tương thích OpenAPI `responseSchema` của Gemini.
  - Tách `usageMetadata.thoughtsTokenCount` vào `ProviderTelemetry.thinking_tokens` và cộng `thinking_tokens` vào tổng token đầu ra tính phí (`billable_output_tokens = output_tokens + thinking_tokens`) trong [src/p06/evaluation/metrics/performance.py](../src/p06/evaluation/metrics/performance.py).
  - **Rà soát tài liệu chính thức Gemini API (tại `2026-11-26`):**
    - `gemini-2.5-flash` hiện được đánh dấu định tuyến/khuyến nghị chuyển sang thế hệ mới trong tài liệu chính thức (tham chiếu đơn giá cũ `~$0.30 in / $2.50 out` mỗi 1M token); các ứng viên Flash/Flash-Lite tiết kiệm chi phí hơn gồm `gemini-2.5-flash-lite` (`$0.10 in / $0.40 out` per 1M) và `gemini-3.1-flash-lite-preview` / `gemini-3.5-flash-lite` (`~$0.25 in / $1.50 out`).
    - **Chính sách dữ liệu (Data Privacy):** Theo điều khoản Gemini API, **Free Tier có thể sử dụng prompt/response để cải thiện sản phẩm của Google**, do đó **nghiêm cấm gửi dữ liệu merchant thật hoặc PII**; mọi thực nghiệm `P06-E01` trên Free Tier chỉ được phép chạy dữ liệu `SYNTHETIC`. Trên **Paid Tier 1** (kích hoạt sau khi liên kết billing, có giới hạn chi tiêu theo 10 phút/tháng), dữ liệu không dùng để huấn luyện; tuy vậy vẫn khóa mặc định `SYNTHETIC` cho đến khi có phê duyệt DPA chính thức.
- **Rào chắn ngân sách & Opt-in:**
  - CLI [run_e01.py](../experiments/p06_e01_no_comments/run_e01.py) giữ mặc định chặn provider ngoài (`[T08 BLOCKED]`) trừ khi truyền tường minh **`--allow-live-provider`**.
  - `ExperimentRunConfig` và `session_runner.py` thực thi `max_llm_calls` và `max_estimated_cost_usd`, dừng phiên an toàn với mã **`RunTerminationReason.BUDGET_LIMIT_REACHED`**.

---

## 5. Xác minh Ngoại tuyến & Kết quả Dry-run trước Cổng Thực thi

| Hạng mục kiểm tra | Lệnh thực thi | Kết quả quan sát được |
| :--- | :--- | :--- |
| Thu thập tests | `.\.venv\Scripts\python.exe -m pytest experiments/sales-intelligence/autonomous-storytelling/tests --collect-only -q` | **`259 tests collected in 4.12s`** |
| Toàn bộ unit/contract/integration suite | `.\.venv\Scripts\python.exe -m pytest experiments/sales-intelligence/autonomous-storytelling/tests -q` | **`259 passed in 39.37s`** (`0 failed, 0 skipped`) |
| Kiểm tra phụ thuộc | `.\.venv\Scripts\python.exe -m pip check` | **`No broken requirements found.`** |
| Sweep dry-run `e01_ext_v1` | `run_e01.py --provider mock --dataset-profile e01_ext_v1 --scenario product_education_10m_ext --min-chunks-per-topic 2 --sweep --export-human-eval` | **Thành công** (`sweep_20261126T095539Z`): `compatible=True`, `tier=unit_test`, **5/5 runs** đạt `EARLY_COMPLETION`, `struct_gates=PASS`, `overall_gates=NOT_EVALUATED`, `topic_cov=1.0000`, `p05_rej_rate=0.0000`; đã xuất đủ 3 tệp chấm mù trong `human_eval/`. |

**Tóm tắt số liệu `offline_ext_v1_dryrun` (Mock-only — chỉ kiểm chứng luồng logic, KHÔNG đại diện chất lượng tiếng Việt):**

| Phương pháp | W | Kết thúc | Số lượt | `topic_cov` | `dur_fulfill` | `ngram3_mean` | `lex_rep_rate` | `rewrite_rate` | `struct_gates` | `overall_gates` |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `script_first_deterministic` | N/A | `EARLY_COMPLETION` | 36 | `1.0000` | `0.3577` | `0.8936` | `0.8571` | `0.0000` | `PASS` | `NOT_EVALUATED` |
| `script_first_upfront_llm` | N/A | `EARLY_COMPLETION` | 36 | `1.0000` | `0.3609` | `0.2289` | `0.0857` | `0.0000` | `PASS` | `NOT_EVALUATED` |
| `langgraph_structured_story` | 5 | `EARLY_COMPLETION` | 36 | `1.0000` | `0.3628` | `0.1569` | `0.0000` | `0.1667` | `PASS` | `NOT_EVALUATED` |
| `langgraph_structured_story` | 10 | `EARLY_COMPLETION` | 40 | `1.0000` | `0.4039` | `0.2014` | `0.0513` | `0.1250` | `PASS` | `NOT_EVALUATED` |
| `langgraph_structured_story` | 20 | `EARLY_COMPLETION` | 40 | `1.0000` | `0.4039` | `0.2014` | `0.0513` | `0.1250` | `PASS` | `NOT_EVALUATED` |

*(Ghi chú lý do `W=10` và `W=20` có `40` lượt: 4 lượt có overlap bị chuyển sang `FALLBACK_PREAPPROVED`, không cộng điểm phủ `topic_id`, nên `GlobalTopicCoverage` tiếp tục yêu cầu đủ 36 chunk `VERIFIED_READY` mới báo `EARLY_COMPLETION`.)*

---

## 6. Giao thức Thực nghiệm Phân tầng & Ngân sách Dự kiến (`configs/experiments/p06_e01_t09_readiness.yaml`)

| Giai đoạn | Mục tiêu & Kịch bản | Provider / Model | Cấu hình kiểm soát | Ngân sách & Điều kiện dừng |
| :--- | :--- | :--- | :--- | :--- |
| **Stage 1: Local CPU Smoke Pilot** | Kiểm chứng end-to-end JSON schema + tiếng Việt với `pilot_short_3sku_ext` (6 topics) | Tier 2 Ollama (`qwen2.5:3b` sẵn trên máy; hoặc `qwen3:1.7b` với `think=false` nếu user đồng ý pull) | `min_chunks=1`, `W=5`, `seed=42`, chỉ chạy khi RAM trống `>= 3.5 GB` | `max_turns=8`, `max_llm_calls=12`, `$0.00` (local), tách bảng riêng khỏi Gemini |
| **Stage 2: Gemini Pilot Calibration** | Hiệu chuẩn latency, `thoughtsTokenCount`, chi phí/1K tokens trên `pilot_short_3sku_ext` | Tier 3 Gemini (exact `model_id` được user chọn & verify, vd. `gemini-2.5-flash-lite`) | `min_chunks=1`, `langgraph W=5` + `script_first_upfront_llm`, dữ liệu `SYNTHETIC` | `max_turns=10`, `max_llm_calls=25`, `max_estimated_cost_usd=0.25` |
| **Stage 3: Formal Sweep Matrix** | Đánh giá định lượng so sánh 5 cấu hình/kịch bản trên `e01_ext_v1` | Tier 3 Gemini cùng 1 `model_id` + `sampling_params` cố định cho mọi lượt LLM | `product_education_10m_ext`, `brand_storytelling_10m_ext`, `sales_presentation_30m_ext` (`min_chunks=2`) + `window_sensitivity_stress_24t` (`min_chunks=1`, `W in {5,10,20}`) | Ngắt cứng mỗi run `max_estimated_cost_usd=0.25`; tổng sweep trần `< $5.00`; chỉ kết luận khi `compare_runs().compatible == True` |
| **Stage 4: Human Eval & GoldFactualLabel** | Chấm mù 6 trục rubric + dán nhãn factual độc lập | Phiếu `human_eval_rubric_v0.1.md` + `GoldFactualLabel` | `blind_eval_sheet.{csv,jsonl}` trộn thứ tự ẩn danh | `overall_gate_status` chuyển từ `NOT_EVALUATED` sang `PASS`/`FAIL` theo dữ liệu thật |

---

## 7. Real Provider Execution Approval Checklist (Đề nghị Tech Lead / User phê duyệt)

Trước khi chuyển sang phiên chạy thật `E01-T09`, vui lòng xác nhận từng mục sau:

- [ ] **Phê duyệt Tier 2 (Ollama CPU):** Đã giải phóng RAM trống trên máy (`>= 3.5 GB` so với `1.01 GB` hiện tại); chọn dùng `qwen2.5:3b` sẵn có hay cấp phép chạy `ollama pull qwen3:1.7b`.
- [ ] **Phê duyệt Tier 3 (Gemini API):** Xác nhận exact `model_id` (ví dụ `gemini-2.5-flash-lite` hay `gemini-3.1-flash-lite-preview`), xác nhận Free Tier (chỉ `SYNTHETIC`) hay Paid Tier 1, giá tham chiếu cho `pricing` trong YAML, và cấu hình biến môi trường `GEMINI_API_KEY` ngoài Git.
- [ ] **Phê duyệt Ngân sách Thực thi:** Xác nhận trần `max_llm_calls` / `max_estimated_cost_usd` cho Stage 2 Pilot (`<= $0.25/run`) và Stage 3 Formal Matrix (`<= $5.00` tổng).
- [ ] **Lệnh mở khóa chạy thử Stage 1 / Stage 2 sau khi được duyệt:**
  ```powershell
  # Ví dụ Stage 1 Local Smoke Pilot (chỉ chạy khi đã giải phóng RAM & được phê duyệt):
  .\.venv\Scripts\python.exe experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_e01.py `
    --provider ollama --allow-live-provider `
    --config experiments/sales-intelligence/autonomous-storytelling/configs/models/ollama_qwen2.5_3b.yaml `
    --dataset-profile e01_ext_v1 --scenario pilot_short_3sku_ext `
    --method langgraph_structured_story --history-window 5 `
    --max-turns 8 --max-llm-calls 12 `
    --output-dir experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/stage1_ollama_pilot
  ```
