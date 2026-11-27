# Báo cáo Thực thi & Phân tích Formal Benchmark Batch 1B — Brand Storytelling (`P06-E01-T09`)

**Ngày lập báo cáo:** `2026-11-27`  
**Branch:** `research/p06-autonomous-storytelling`  
**Base Commit trước phiên:** `8008f9f` (`research(p06): complete E01 formal benchmark batch 1A`)  
**Module:** `experiments/sales-intelligence/autonomous-storytelling/`  
**Phân loại phiên:** **`Controlled Exploratory Benchmark`** *(Rút gọn Track 1 — `GO FOR BATCH 1B ONLY`)*  
**Trạng thái hiện tại:** **`AWAITING_BATCH_1B_REVIEW_AND_TRACK2_APPROVAL`** *(Không chạy thêm API sau Batch 1B; `overall_gate_status = NOT_EVALUATED` do chờ Human Blind Evaluation & Gold Factual Labels)*

---

## 1. Tóm tắt Điều hành (Executive Summary)

Sau khi review **Batch 1A (`product_education_10m_ext`)** và lưu bộ đánh giá AI-assisted ChatGPT (`77` dòng), Tech Lead đã phê duyệt **Batch 1B (`brand_storytelling_10m_ext`, `seed=42`, `min_chunks_per_topic=1`)** trên hai cấu hình đối chiếu cốt lõi **`script_first_upfront_llm`** (`max_retries=0`) và **`langgraph_structured_story` (`W=5`, `max_retries=2`)** bằng **`gemini-3.5-flash-lite` Free Tier (`0 USD`)** nhằm kiểm tra khả năng tổng quát hóa sang kịch bản kể chuyện thương hiệu và bảo toàn thông tin OCOP/an toàn.

Các kết quả thực nghiệm cốt lõi của Batch 1B:

1. **Tuân thủ ngân sách & vận hành sạch:** Sổ cái [`budget_ledger.json`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/budget_ledger.json) ghi nhận **`41 / 60` requests** (`18` cho `Script-first` + `23` cho `LangGraph W=5`), dư `19` requests, **`0 USD`**, **`0` `HTTP 429`**, **`2` lỗi hạ tầng `HTTP 503`** (`1` ở `Script-first` call `c4`, `1` ở `LangGraph W=5` call `c17`), **`0` rò rỉ API key hay metadata kỹ thuật**, và bảo toàn nguyên vẹn Pilot v1/v2 cùng toàn bộ Batch 1A (`human_eval/` và `ai_assisted_eval/`).
2. **Ưu thế độ phủ của LangGraph tiếp tục lặp lại trên Brand Storytelling (`Objective 1`):**
   - **`LangGraph W=5`** đạt **`100%` (`12/12`) `mandatory_topic_coverage`**, **`100%` (`18/18`) planned topic coverage** và **`100%` (`12/12`) `declared_verified_claim_coverage`**, kết thúc sạch tại `EARLY_COMPLETION` (vượt qua `1` lỗi `HTTP 503` bằng `PREAPPROVED_FALLBACK` và cứu `4/4` lượt vượt `20` từ bằng `bounded_rewrite`).
   - **`Script-first Upfront LLM`** chỉ đạt **`75.00%` (`9/12`) `mandatory_topic_coverage`**, **`66.67%` (`12/18`) planned topic coverage** và **`66.67%` (`8/12`) `declared_verified_claim_coverage`**, kết thúc tại `CONTENT_EXHAUSTED` với `5` lượt sinh vượt `20` từ (`8.08–9.23s`), `1` lượt `HTTP 503` (`c4`), `5` lượt fallback chung và `1` lượt `SAFE_ABORT_NO_CANDIDATE` (`topic-ext-brand-honey-pairing`).
3. **Phát hiện rủi ro an toàn thương mại & rewrite rất giá trị cho `E04` (`Objectives 3 & 4`):**
   - Dù đạt `structural_hard_gates_status = PASS` (`0` replay `chunk_id`, `0` rò rỉ ID, `0` lỗi cross-SKU), kiểm tra câu chữ chi tiết phát hiện **`LangGraph W=5` Turn `[3]` (`honey-ocop`) và `Script-first` Turn `[3]` đều lược mất từ khóa `"mô phỏng"` / `"hồ sơ mô phỏng"`** trong lời thoại dù `talking_points` yêu cầu rõ `"Hồ sơ mô phỏng đạt OCOP 4 sao cấp tỉnh..."`.
   - Đặc biệt, ở `LangGraph W=5` Turn `[18]` (`topic-ext-brand-macadamia-pairing`), vòng `bounded_rewrite` để rút câu `22` từ xuống `18` từ đã biến cụm cảnh báo `", lưu ý tránh dùng cho người dị ứng hạt nhé."` thành **`"hoặc tránh dùng cho người dị ứng hạt nhé."`** — làm lệch/giảm nhẹ ngữ nghĩa cảnh báo an toàn dị ứng.
4. **Độ dài & hiệu năng (`Objectives 5` & `Finding F/G`):** Thời lượng phát mô phỏng vẫn chỉ đạt **`118.08s` (`19.68%`)** ở `Script-first` và **`124.23s` (`20.70%`)** ở `LangGraph W=5` trên mục tiêu `600s`. Số liệu `provider_latency_ms` (`P50 ~5.95s`) vẫn bao gồm thời gian ngủ pacing `6.0s` phía client và `thinking_tokens` vẫn là `UNAVAILABLE` (`null` trên cả `41` calls).
5. **Trạng thái Gate & Đề xuất Track 2:** Đã xuất đủ `6` tệp [`human_eval/`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/human_eval/) (`37` dòng audit), giữ `overall_gate_status = NOT_EVALUATED` (`PENDING`), và lập kế hoạch tối thiểu cho **Track 2 (`lag=12` / đối chứng `lag=6/8`, không gọi API)** để dừng tại **`AWAITING_BATCH_1B_REVIEW_AND_TRACK2_APPROVAL`**.

---

## 2. Phê duyệt Tech Lead & Sửa đổi Giao thức (`DR-P06-012`)

Tech Lead chính thức phê duyệt **`GO FOR BATCH 1B ONLY — CONTROLLED EXPLORATORY BENCHMARK`** với các điều chỉnh phạm vi đã ghi nhận trước execution tại [`DR-P06-012`](../research/decision_log.md), Mục 11 của [`11-e01-t09-formal-benchmark-protocol.md`](./11-e01-t09-formal-benchmark-protocol.md) và [`protocol_amendment_and_criteria_lock.json`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/protocol_amendment_and_criteria_lock.json):

- **Rút gọn Track 1 Natural Storytelling:** Sau Batch 1A (`Product Education`, `Script-first + W=5/10/20`), Batch 1B (`Brand Storytelling`, `seed=42`) chỉ chạy **`script_first_upfront_llm`** và **`langgraph_structured_story (W=5)`**. Không chạy `W=10/W=20`, không chạy `Product Education seed=43`, không chạy Pilot v3/Track 2/Track 3/E02–E04 trong phiên này.
- **Bảo toàn Acceptance Criteria & Công bằng So sánh:** Giữ nguyên 100% các ngưỡng Hard Gates (`0` vi phạm) và Quality/Reliability đã khóa từ Batch 1A (không hạ chuẩn); không gộp `W=10`/`W=20` của Batch 1A vào bảng ghép cặp cross-scenario; không tự diễn giải các cấu hình bị loại là đã thực hiện.
- **Ngân sách riêng Batch 1B:** Trần `30` requests/run, **`60` requests toàn cục**, Free Tier **`0 USD`**, pacing `>= 6.0s`, thực thi tuần tự.

---

## 3. Tổng hợp Kết quả AI-Assisted Evaluation của Batch 1A (Đã Lưu & Đối soát)

Hai tệp đánh giá ChatGPT do Tech Lead cung cấp đã được lưu nguyên vẹn tại [`runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/ai_assisted_eval/`](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/ai_assisted_eval/) ([quality CSV](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/ai_assisted_eval/batch1a_ai_assisted_quality.csv), [factual/semantic CSV](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/ai_assisted_eval/batch1a_ai_assisted_factual_semantic.csv), [README](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/ai_assisted_eval/README.md)) với nhãn nguồn rõ ràng **`AI-assisted non-blind evaluation — ChatGPT — Rubric v0.1`**.

> [!WARNING]
> Bộ dữ liệu này **KHÔNG phải Human Blind Evaluation** và **KHÔNG phải `GoldFactualLabel`**. Các phiếu gốc trong Batch 1A [`human_eval/`](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/human_eval/) được giữ nguyên `100%` trống; Human Calibration và Gold Factual Assessment vẫn ở trạng thái **`PENDING`**.

Đối soát tự động với `77` dòng (`74` played turns + `3` `MISSING_TOPIC`) và `4` mẫu cho thấy **khớp 100% (`0` sai lệch)** với các bảng tổng hợp dưới đây:

### 3.1. Điểm Chất lượng Sơ bộ (Rubric `v0.1`, Thang `1–5`)
| Tiêu chí | `Script-first` | `W=5` | `W=10` | `W=20` |
|---|---:|---:|---:|---:|
| Narrative Coherence | 2 | 3 | 3 | 3 |
| Naturalness | 3 | 3 | 3 | 3 |
| Persuasiveness | 3 | 3 | 3 | 3 |
| Context Relevance | 2 | 4 | 3 | 4 |
| Transition Quality | 2 | 2 | 2 | 2 |
| Repetition Quality | 2 | 5 | 3 | 4 |
| **Mean Score** | **2.33** | **3.33** | **2.83** | **3.17** |

### 3.2. Độ phủ Ngữ nghĩa & An toàn Bằng chứng trên Batch 1A (`74` Played Turns)
| Phương pháp | Mand (`12`): `FULL/PARTIAL/MISS` | Planned (`18`): `FULL/PARTIAL/MISS` | Played Turns | Factual `PASS / FAIL / UNSURE` | Evidence `PASS / FAIL` | Metadata Leak |
|---|---|---|---:|---|---|---:|
| `Script-first` (`SAMPLE_003`) | `2 / 5 / 5` | `4 / 6 / 8` | `15` | `14 / 0 / 1` | `12 / 3` | `0` |
| `LangGraph W=5` (`SAMPLE_004`) | `3 / 9 / 0` | `7 / 11 / 0` | `18` | `14 / 0 / 4` | `13 / 5` | `0` |
| `LangGraph W=10` (`SAMPLE_002`) | `3 / 9 / 0` | `7 / 11 / 0` | `21` | `18 / 1 / 2` | `16 / 5` | `0` |
| `LangGraph W=20` (`SAMPLE_001`) | `3 / 9 / 0` | `5 / 13 / 0` | `20` | `17 / 0 / 3` | `16 / 4` | `0` |
| **Tổng (`Played Turns`)** | — | — | **`74`** | **`63 / 1 / 10`** | **`57 / 17`** | **`0`** |

*(Ghi chú đối soát: Ở các topic có 1 lượt `PREAPPROVED_FALLBACK` do 503 rồi 1 lượt `PROACTIVE_STORY` theo sau trên cùng `topic_id`, bảng `12` mandatory và `18` planned topics lấy mức phủ của lượt `PROACTIVE_STORY` hoàn tất topic đó; `3` dòng `MISSING_TOPIC` chỉ nằm ở `Script-first`, tính là `MISS` ở semantic coverage và không đưa vào mẫu số factual/evidence của `74` played turns.)*

**7 Phát hiện Nghiên cứu Đã Khóa từ Batch 1A (`Findings A–G`):**
- **A (Hiệu quả kiến trúc):** LangGraph đạt `100%` playback-confirmed mandatory coverage (`W=5/10/20`) so với `58.33%` của Script-first nhờ `bounded_rewrite`, nhưng chưa chứng minh memory hoặc LangGraph là nguyên nhân duy nhất.
- **B (Khoảng trống Semantic Coverage):** Playback `100%` ≠ Semantic `100%` — LangGraph chỉ đạt `3/12` (`25%`) mandatory `FULL` do các topic nhồi nhiều talking points vượt khung `<= 20` từ (`8.0s`) khi `min_chunks_per_topic=1`.
- **C (Chất lượng & Mạch kể):** `W=5` cao nhất (`3.33/5`), nhưng cả 4 phương pháp đều yếu ở `transition_quality` (`2/5`), `naturalness` (`3/5`), dẫn nối giữa topic/SKU và chưa đạt chuẩn chấp nhận (`>= 3.5`).
- **D (An toàn & Bằng chứng):** `W=10` Turn `[16]` biến `"không ăn gói hút ẩm"` thành `"giữ gói hút ẩm"` (`Factual FAIL`); `10` turns `UNSURE` (bỏ đơn vị/điều kiện phụ); `17` turns `Evidence FAIL` (trích dẫn thiếu ID hỗ trợ đủ từng chi tiết dù đúng `ProductFact`). `P05 ALLOW` không bảo đảm factual correctness ngữ nghĩa; chuyển tiếp sang E04 và nhóm P05.
- **E (History Window):** `W=5` chỉ là ứng viên mặc định tạm thời, không phải tối ưu; cần Track 2 (`lag=12`).
- **F (Duration):** Chỉ đạt `17.56%–24.17%` của `600s`; không chứng minh được storytelling 10–30 phút.
- **G (Performance Measurement):** Kiểm tra trực tiếp `provider_calls.jsonl` xác nhận chỉ có `latency_ms` tổng (đã gồm client pacing sleep `6.0s`), **không có timestamp bắt đầu/kết thúc HTTP thuần hay trường `sleep_ms`** để tách ngoại tuyến; ghi nhận giới hạn đo lường thay vì sửa telemetry hay suy đoán số liệu.

---

## 4. Xác minh Tiền kiểm & Tái lập (`Preflight & Safety Audit`)

1. **Git & Regression:** Nhánh `research/p06-autonomous-storytelling`, commit gốc `8008f9f`, working tree sạch trước lúc chạy, `0` merge conflict; mốc regression suite xác nhận là **`287 passed`** (`0 failed, 0 skipped`, `pip check` sạch). Toàn bộ tài nguyên Pilot v1/v2 và Batch 1A nguyên vẹn.
2. **Kiểm tra Hashes khóa (`11/11`):** Toàn bộ `9` tệp khóa Batch 1A + `_UPFRONT_PROMPT_SHA256` (`50ed8404...554d4`, `baseline-script-first-v0.2.2`) + `configs/experiments/p06_e01_formal_batch1b.yaml` (`f380892c137606f0277aafa809a4623a904a9f262c10797cf0cb897b42079fd2`) khớp 100%.
3. **Safety Preflight trên `brand_storytelling_10m_ext`:**
   - `plan-e01-ext-brand-storytelling-10m` (`APPROVED`, `3` SKUs, `600s`, **`18` planned topics** = **`12` mandatory** [`origin, harvest, sensory, ocop` × 3] + **`6` optional** [`packaging`, `pairing/brewing` × 3], **`12` distinct `allowed_claim_ids`**).
   - `0` lỗi tham chiếu `fact_refs` / `allowed_claim_ids` / cross-SKU; cả `3/3` SKUs có `ocop_status="VERIFIED"` trong synthetic snapshot; `check_spoken_text_hygiene()` pass trên `SYNTH-OCOP-4S-DL-001`, `SYNTH-OCOP-4S-HG-002`, `SYNTH-OCOP-4S-LD-003`.
   - Hai quan sát biết trước (giữ nguyên không sửa dataset khóa): `topic-ext-brand-macadamia-packaging` dùng `"nắp vặn kín khí"` khi `fact_refs` dẫn `ev-e01-ext-macadamia-packaging` (`"nắp vặn chắc chắn"`), và `brand_storytelling_10m_ext` không có topic riêng về chính sách đổi trả (`ev-e01-tea-shipping` chỉ được gắn ở `topic-ext-brand-tea-packaging` cho chi tiết quà biếu; điều kiện đổi trả nằm ở fallback/shipping chunks).
4. **Offline Mock Dry-Run:** Chạy `run_gemini_formal_batch.py --provider mock` trên `p06_e01_formal_batch1b.yaml` -> `COMPLETED` (`2` runs, `comparison_compatible=True`, `human_eval/` sạch).
5. **Quota & API Key:** `GEMINI_API_KEY` tồn tại trong env (không lộ), `0` tiến trình Python khác chạy nền, project `Default Gemini Project` Free Tier đủ >60 RPD khả dụng (`0 USD`).

---

## 5. Cấu hình Batch 1B & Danh sách Run IDs

- **Cấu hình:** [`configs/experiments/p06_e01_formal_batch1b.yaml`](../configs/experiments/p06_e01_formal_batch1b.yaml) (`gemini-3.5-flash-lite`, `Free Tier`, `0 USD`, `SYNTHETIC`, `e01_ext_v1 v1.0.1/v1.0.2`, `brand_storytelling_10m_ext`, `seed=42`, `min_chunks_per_topic=1`, `max_chunk_duration_sec=8.0`, `max_turns=40`, `temperature=0.3`, `top_p=0.9`, `max_tokens=1024`, `thinking_level=MINIMAL`, `timeout=30s`, `max_requests_per_run=30`, `global_max_requests=60`, `min_request_interval_sec=6.0`).
- **Prompts khóa:** `story_planner.txt (v0.1)`, `story_generation.txt (v0.2.1)`, `rewrite.txt (v0.2.1)`, `baseline-script-first-v0.2.2`.

| Cấu hình | `W` | Run ID & Đường dẫn | Thời gian UTC | Kết thúc |
|---|---:|---|---|---|
| `script_first_upfront_llm` | `N/A` | [`...script_first_upfront_llm__noW__20261126T215734Z__d96d8d65`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/P06-E01__brand_storytelling_10m_ext__script_first_upfront_llm__noW__20261126T215734Z__d96d8d65/) | `21:57:34 -> 21:59:18` (`103.83s`) | `CONTENT_EXHAUSTED` |
| `langgraph_w5` | `5` | [`...langgraph_structured_story__w5__20261126T215918Z__0382f316`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/P06-E01__brand_storytelling_10m_ext__langgraph_structured_story__w5__20261126T215918Z__0382f316/) | `21:59:18 -> 22:01:37` (`138.40s`) | `EARLY_COMPLETION` |

---

## 6. Toàn bộ Transcript Thực tế (Batch 1B — Nguyên văn)

### 6.1. `script_first_upfront_llm` (`noW` — `17` turns phát, `1` safe abort)

| Turn | Origin | Topic ID *(Mand?)* | Từ / Giây | `cited_evidence_ids` | Lời thoại nguyên văn |
|---:|---|---|---:|---|---|
| `[0]` | `PREAPPROVED_FALLBACK` *(22w/8.46s)* | `honey-origin` *(Có)* | `16` / `6.154s` | `ev-e01-honey-shipping` | Mật ong hoa cà phê Đắk Lắk nguyên chất 500ml hiện có giá niêm yết 159.000đ. |
| `[1]` | `PROACTIVE_STORY` | `honey-harvest` *(Có)* | `16` / `6.154s` | `ev-e01-ext-honey-harvest` | Mật ong quay ly tâm thủ công, lọc lưới mịn giữ trọn hương thơm tự nhiên. |
| `[2]` | `PROACTIVE_STORY` | `honey-sensory` *(Có)* | `19` / `7.308s` | `ev-e01-ext-honey-sensory` | Mật có màu vàng hổ phách trong, sánh dẻo, vị ngọt thanh dịu và không gắt mùi đường khét. |
| `[3]` | `PROACTIVE_STORY` | `honey-ocop` *(Có)* | `17` / `6.538s` | `ev-e01-honey-ocop` | Sản phẩm đạt OCOP bốn sao cấp tỉnh với tem truy xuất rõ ràng trên thân chai. |
| `[4]` | `PREAPPROVED_FALLBACK` *(503)* | `honey-packaging` *(Tùy chọn)* | `20` / `7.692s` | `ev-e01-honey-shipping` | Mật ong hoa cà phê Đắk Lắk nguyên chất 500ml, nguồn gốc Huyện Cư M'gar, tỉnh Đắk Lắk, giá 159.000đ. |
| `—` | `SAFE_ABORT_NO_CANDIDATE` | `honey-pairing` *(Tùy chọn)* | `—` | `—` | *(Loại bởi `OVER_MAX_DURATION_SEC` 24w/9.23s; hết 2 mẫu fallback SKU-HONEY-01)* |
| `[5]` | `PROACTIVE_STORY` | `tea-origin` *(Có)* | `18` / `6.923s` | `ev-e01-tea-origin` | Búp trà Shan Tuyết cổ thụ 1 tôm 2 lá hái thủ công trên 1.300m tại Phìn Hồ. |
| `[6]` | `PROACTIVE_STORY` | `tea-harvest` *(Có)* | `19` / `7.308s` | `ev-e01-ext-tea-harvest` | Trà được làm héo trên nong tre, sao diệt men và vò nhẹ giữ nguyên lớp tuyết trắng mịn. |
| `[7]` | `PROACTIVE_STORY` | `tea-sensory` *(Có)* | `19` / `7.308s` | `ev-e01-ext-tea-sensory` | Nước trà vàng mơ sáng trong, vị chát đầu lưỡi thanh nhẹ và chuyển nhanh sang hậu ngọt sâu. |
| `[8]` | `PROACTIVE_STORY` | `tea-ocop` *(Có)* | `16` / `6.154s` | `ev-e01-tea-ocop` | Trà Shan Tuyết đạt chuẩn OCOP 4 sao mô phỏng, kiểm soát độ ẩm an toàn. |
| `[9]` | `PROACTIVE_STORY` | `tea-packaging` *(Tùy chọn)* | `19` / `7.308s` | `ev-e01-ext-tea-packaging`, `ev-e01-ext-tea-pairing` | Hộp thiếc 200g có túi hút chân không và nắp phụ, hạn dùng 18 tháng, thích hợp tiếp khách. |
| `[10]` | `PREAPPROVED_FALLBACK` *(21w/8.08s)* | `tea-brewing` *(Tùy chọn)* | `16` / `6.154s` | `ev-e01-tea-shipping` | Trà Shan Tuyết cổ thụ Hà Giang hộp thiếc 200g hiện có giá niêm yết 245.000đ. |
| `[11]` | `PROACTIVE_STORY` | `macadamia-origin` *(Có)* | `20` / `7.692s` | `ev-e01-macadamia-origin` | Mắc ca tuyển chọn từ vườn Lâm Hà, thu hái trái chín rụng tự nhiên và phân cỡ kỹ càng. |
| `[12]` | `PREAPPROVED_FALLBACK` *(23w/8.85s)* | `macadamia-harvest` *(Có)* | `16` / `6.154s` | `ev-e01-macadamia-shipping` | Hạt mắc ca sấy nứt vỏ Lâm Đồng hộp 500g hiện có giá niêm yết 195.000đ. |
| `[13]` | `PREAPPROVED_FALLBACK` *(21w/8.08s)* | `macadamia-sensory` *(Có)* | `20` / `7.692s` | `ev-e01-macadamia-shipping` | Hạt mắc ca sấy nứt vỏ Lâm Đồng hộp 500g, nguồn gốc Huyện Lâm Hà, tỉnh Lâm Đồng, giá 195.000đ. |
| `[14]` | `PROACTIVE_STORY` | `macadamia-ocop` *(Có)* | `16` / `6.154s` | `ev-e01-macadamia-ocop` | Sản phẩm sấy tách ẩm ổn định và đạt hồ sơ OCOP 4 sao mô phỏng. |
| `[15]` | `PROACTIVE_STORY` | `macadamia-packaging` *(Tùy chọn)* | `20` / `7.692s` | `ev-e01-ext-macadamia-packaging`, `ev-e01-macadamia-quality` | Hộp PET trong 500g nắp vặn kín khí, kèm thanh tách thép và gói hút ẩm giúp bảo quản tốt. |
| `[16]` | `PROACTIVE_STORY` | `macadamia-pairing` *(Tùy chọn)* | `20` / `7.692s` | `ev-e01-ext-macadamia-pairing`, `ev-e01-macadamia-usage`, `ev-e01-ext-macadamia-safety` | Bạn có thể ăn liền, làm sữa hạt, trộn salad nhưng nhớ tránh dùng cho người dị ứng hạt nhé! |

### 6.2. `langgraph_w5` (`W=5` — `19` turns phát: `18` proactive + `1` fallback do `HTTP 503`)

| Turn | Origin | Topic ID *(Mand?)* | Từ / Giây | `cited_evidence_ids` | Lời thoại nguyên văn |
|---:|---|---|---:|---|---|
| `[0]` | `PROACTIVE_STORY` | `honey-origin` *(Có)* | `19` / `7.308s` | `ev-e01-honey-origin` | Mật ong được khai thác chính vụ hoa cà phê Cư M'gar, thu hoạch khi mật chín tự nhiên. |
| `[1]` | `PROACTIVE_STORY` | `honey-harvest` *(Có)* | `17` / `6.538s` | `ev-e01-ext-honey-harvest` | Quay ly tâm thủ công và lọc lưới mịn loại mảnh sáp, giữ hương hoa tự nhiên. |
| `[2]` | `PROACTIVE_STORY` | `honey-sensory` *(Có)* | `17` / `6.538s` | `ev-e01-ext-honey-sensory` | Mật sánh dẻo màu vàng hổ phách, không gắt mùi đường khét với hậu vị thanh dịu. |
| `[3]` | `PROACTIVE_STORY` | `honey-ocop` *(Có)* | `16` / `6.154s` | `ev-e01-honey-ocop` | Sản phẩm đạt chứng nhận OCOP bốn sao với tem truy xuất nguồn gốc rõ ràng. |
| `[4]` | `PROACTIVE_STORY` | `honey-packaging` *(Tùy chọn)* | `12` / `4.615s` | `ev-e01-ext-honey-packaging` | Chai thủy tinh nắp vặn kín chống tràn, hạn dùng 24 tháng. |
| `[5]` | `PROACTIVE_STORY` | `honey-pairing` *(Tùy chọn)* | `20` / `7.692s` | `ev-e01-honey-usage`, `ev-e01-ext-honey-safety` | Pha một đến hai thìa với nước ấm dưới năm mươi độ, lưu ý tránh dùng trẻ dưới một tuổi. |
| `[6]` | `PROACTIVE_STORY` *(RW×1)* | `tea-origin` *(Có)* | `18` / `6.923s` | `ev-e01-tea-origin` | Búp trà hái thủ công 1 tôm 2 lá từ cây cổ thụ trên 1.300m tại Phìn Hồ. |
| `[7]` | `PROACTIVE_STORY` *(RW×1)* | `tea-harvest` *(Có)* | `16` / `6.154s` | `ev-e01-ext-tea-harvest` | Làm héo tự nhiên trên nong tre, sao vò nhẹ giữ nguyên lớp tuyết trắng mịn. |
| `[8]` | `PROACTIVE_STORY` | `tea-sensory` *(Có)* | `13` / `5.000s` | `ev-e01-ext-tea-sensory` | Nước trà vàng mơ sáng trong, chát thanh nhẹ và hậu ngọt sâu. |
| `[9]` | `PROACTIVE_STORY` | `tea-ocop` *(Có)* | `18` / `6.923s` | `ev-e01-tea-ocop` | Sản phẩm đạt OCOP bốn sao mã mô phỏng cùng quy trình sao vò truyền thống an toàn. |
| `[10]` | `PROACTIVE_STORY` | `tea-packaging` *(Tùy chọn)* | `17` / `6.538s` | `ev-e01-ext-tea-packaging` | Bên trong hộp thiếc có túi hút chân không và nắp phụ, hạn dùng mười tám tháng. |
| `[11]` | `PROACTIVE_STORY` *(RW×1)* | `tea-brewing` *(Tùy chọn)* | `15` / `5.769s` | `ev-e01-tea-usage` | Dùng 5g trà với 150ml nước 85-90 độ C, hãm 30-45 giây cho lượt đầu. |
| `[12]` | `PROACTIVE_STORY` | `macadamia-origin` *(Có)* | `19` / `7.308s` | `ev-e01-macadamia-origin` | Mắc ca được tuyển chọn từ vườn Lâm Hà, thu hái trái chín rụng tự nhiên rồi phân cỡ. |
| `[13]` | `PROACTIVE_STORY` | `macadamia-harvest` *(Có)* | `18` / `6.923s` | `ev-e01-ext-macadamia-harvest` | Sấy đối lưu nhiệt độ thấp nhiều giờ giúp hạt chín đều và nứt vỏ vừa tay tách. |
| `[14]` | `PREAPPROVED_FALLBACK` *(503)* | `macadamia-sensory` *(Có)* | `16` / `6.154s` | `ev-e01-macadamia-shipping` | Hạt mắc ca sấy nứt vỏ Lâm Đồng hộp 500g hiện có giá niêm yết 195.000đ. |
| `[15]` | `PROACTIVE_STORY` | `macadamia-sensory` *(Có)* | `20` / `7.692s` | `ev-e01-macadamia-quality`, `ev-e01-ext-macadamia-sensory` | Nhân hạt trắng sữa giòn tan, thơm bơ nhẹ tự nhiên và hoàn toàn không tẩm muối hay hương liệu. |
| `[16]` | `PROACTIVE_STORY` | `macadamia-ocop` *(Có)* | `15` / `5.769s` | `ev-e01-macadamia-ocop` | Sản phẩm được sấy tách ẩm ổn định và đạt hồ sơ OCOP 4 sao. |
| `[17]` | `PROACTIVE_STORY` | `macadamia-packaging` *(Tùy chọn)* | `19` / `7.308s` | `ev-e01-ext-macadamia-packaging` | Hộp PET trong 500g nắp vặn kín khí kèm thanh tách thép và gói hút ẩm, hạn 12 tháng. |
| `[18]` | `PROACTIVE_STORY` *(RW×1)* | `macadamia-pairing` *(Tùy chọn)* | `18` / `6.923s` | `ev-e01-macadamia-usage`, `ev-e01-ext-macadamia-pairing`, `ev-e01-ext-macadamia-safety` | Nhà mình ăn liền, làm sữa hạt, trộn salad hoặc tránh dùng cho người dị ứng hạt nhé. |

---

## 7. So sánh Metrics Trong Batch 1B (`Within-Scenario Comparison`)

| Nhóm | Chỉ số | Ngưỡng Khóa | `Script-first (noW)` | `LangGraph W=5` |
|---|---|---:|---:|---:|
| **A. Coverage** | `mandatory_topic_coverage` (`12`) | `>= 95%` | **75.00%** (`9/12`) | **100%** (`12/12`) |
| | Tổng topic kế hoạch phủ (`18`) | — | 66.67% (`12/18`) | **100%** (`18/18`) |
| | `declared_verified_claim_coverage` (`12`) | — | 66.67% (`8/12`) | **100%** (`12/12`) |
| | `time_to_complete_mandatory_topics_sec` | — | `NOT_EVALUATED` | `109.998s` |
| **B. Repetition** | `exact_chunk_replay_count` / `exact_norm_replay` | `0 / 0` | `0 / 0` | `0 / 0` |
| | `lexical_repetition_rate` *(toàn phiên)* | `<= 5%` | **0.00%** (`0/16`) | **0.00%** (`0/18`) |
| | `max_prior_word_jaccard_mean` *(max)* | — | 0.1728 *(0.5909)* | **0.1093** *(0.2414)* |
| | `max_prior_ngram3_jaccard_mean` *(max)* | — | 0.0612 *(0.3077)* | **0.0061** *(0.0714)* |
| | `distinct_1` / `distinct_2` / `distinct_3` | — | 0.602 / 0.832 / 0.889 | **0.680 / 0.945 / 0.990** |
| | `claim_overlap_rate` | — | 33.33% (`4/12`) | 35.29% (`6/17`) |
| **C. Safety** | `structural_hard_gates_status` / `p05_rejection` | `PASS` / `0` | **PASS** / `0` | **PASS** / `0` |
| | `hygiene_leaks` / `invalid_ev` / `cross_sku` | `0 / 0 / 0` | `0 / 0 / 0` | `0 / 0 / 0` |
| | `overall_gate_status` | `PASS` (hậu human) | `NOT_EVALUATED` | `NOT_EVALUATED` |
| **D. Reliability** | `total_requests` / `successful_candidates` | `<= 30` req | `18 / 12` | `23 / 18` |
| | `HTTP 503` / `HTTP 429` | `0` `429` | `1` *(c4)* / `0` | `1` *(c17)* / `0` |
| | `wasted_calls` **tổng** (`% total`) | — | 33.33% (`6/18`) | **21.74%** (`5/23`) |
| | `wasted_calls` **do logic** (`% total` / `% non-503`) | `<= 10%` | 27.78% / 29.41% (`5/17`) | **17.39% / 18.18%** (`4/22`) |
| | `rewrite_rate` **tổng** / **do logic** | `<= 15%` | `0.00% / 0.00%` | `21.05%` (`4/19`) / `22.22%` (`4/18` non-503) |
| | `fallback_rate` **tổng** / **do logic** | `<= 5%` | `27.78%` (`5/18`) / `22.22%` (`4/18`) | `5.26%` (`1/19`) / **`0.00%`** |
| | `safe_abort_count` (`rate`) | — | `1` (`5.56%`) | **`0`** (`0.00%`) |
| **E. Perf/Tokens** | `provider_latency_p50 / p95` *(gồm pacing 6s)* | `<= 7s / <= 10s` | `5,943.9 / 7,378.7 ms` | `5,951.9 / 8,169.0 ms` |
| | `invocation_latency_p50 / p95` | — | `5,715.9 / 6,022.9 ms` | `5,992.2 / 13,605.5 ms` |
| | Wall-clock runtime / `time_to_first_proactive` | — | `103.83s` / `103.69s` *(upfront)* | `138.40s` / **`5.40s`** (`c0`) |
| | Token source & `measured_calls` | — | `PARTIAL` (`17/18`) | `PARTIAL` (`22/23`) |
| | `input` / `output` / `total` *(partial measured)* | — | `36,470 / 3,174 / 39,644` | `65,319 / 2,707 / 68,026` |
| | `partial_wasted_tokens` / `thinking_tokens` | — | `11,672` *(5 calls)* / `UNAVAILABLE` | `12,948` *(4 calls)* / `UNAVAILABLE` |
| | `tokens_per_accepted_proactive_chunk` *(partial)* | — | `3,303.7` | `3,779.2` |
| | `requests_per_completed_topic` (`planned` / `mand`) | — | `1.50 / 2.00` | **`1.28 / 1.92`** |
| **F. Duration** | `simulated_played_duration_sec` / `600s` | — | `118.077s` (`19.68%`) | `124.229s` (`20.70%`) |
| | `played_chunks_count` / `termination_reason` | — | `17` / `CONTENT_EXHAUSTED` | `19` / `EARLY_COMPLETION` |

---

## 8. Đối chiếu Liên Kịch bản (`Cross-Scenario Comparison`: Batch 1A vs Batch 1B)

> [!NOTE]
> Theo đúng quy tắc ghép cặp (Mục 12): chỉ so sánh ghép cặp hai phương pháp cùng tồn tại ở cả hai kịch bản là **`script_first_upfront_llm`** và **`langgraph_w5`** (`W=10` và `W=20` của Batch 1A bị loại khỏi bảng ghép cặp; không gộp Pilot v1/v2). Hai kịch bản đại diện cho kiểm chứng **tổng quát hóa theo nội dung (generalization across scenarios)** chứ không phải hai lần lặp độc lập cùng điều kiện.

### 8.1. `Script-first Upfront LLM` — Product Education (1A) vs Brand Storytelling (1B)
| Chỉ số | Product Education (`1A`) | Brand Storytelling (`1B`) | Nhận xét Chênh lệch |
|---|---:|---:|---|
| `mandatory_topic_coverage` (`12`) | 58.33% (`7/12`) | **75.00%** (`9/12`) | Brand tăng `+16.67%` (`+2` mand topics) do ít câu nhồi thông số/số liệu hơn Edu |
| `planned_topic_coverage` (`18`) | 55.56% (`10/18`) | **66.67%** (`12/18`) | Tăng `+2` topics thành công (`10 -> 12`) |
| `declared_verified_claim_coverage` | 57.14% (`8/14`) | **66.67%** (`8/12`) | Tỷ lệ tăng do mẫu số claim của Brand ít hơn (`12` vs `14`) |
| `HTTP 503` / Logic `OVER_MAX_DURATION` | `0` / **`8`** (`44.4%`) | `1` / **`5`** (`27.8%`) | Lỗi quá 20 từ giảm từ `8` xuống `5` ở Brand |
| `fallback_count` / `safe_abort_count` | `5` / `3` | `5` / **`1`** | Vẫn cạn mẫu fallback ở SKU-HONEY-01 (`1` abort) |
| `simulated_played_duration_sec` | `105.385s` (`17.56%`) | `118.077s` (`19.68%`) | Cao hơn `+12.69s` nhờ chơi `17` turns thay vì `15` |
| `tokens_per_accepted_proactive_chunk` | `4,217.0` (`18/18`) | `3,303.7` *(`17/18` partial)* | Hiệu suất token cải thiện khi số lỗi dài giảm từ `8` xuống `5` |

### 8.2. `LangGraph W=5` — Product Education (1A) vs Brand Storytelling (1B)
| Chỉ số | Product Education (`1A`) | Brand Storytelling (`1B`) | Nhận xét Chênh lệch |
|---|---:|---:|---|
| `mandatory_topic_coverage` (`12`) | **100%** (`12/12`) | **100%** (`12/12`) | Ổn định tuyệt đối ở cả hai kịch bản |
| `planned_topic_coverage` (`18`) | **100%** (`18/18`) | **100%** (`18/18`) | Ổn định tuyệt đối dù 1B gặp `1` lỗi `HTTP 503` |
| `declared_verified_claim_coverage` | **100%** (`14/14`) | **100%** (`12/12`) | Hoàn thành `100%` ở cả 2 kịch bản |
| `HTTP 503` / Logic rewrite turns | `0` / `4/18` (`22.22%`) | `1` / `4/18` non-503 (`21.05%` tổng) | Tỷ lệ vượt `20` từ lượt đầu gần như không đổi (`4` lượt trên cả 1A và 1B) |
| `fallback_rate` (Tổng / Logic) | `0.00%` / `0.00%` | `5.26%` (`1/19` do 503) / **`0.00%`** | `0%` fallback do logic trên cả 2 kịch bản |
| `max_prior_ngram3_jaccard_mean` | **0.0037** | 0.0061 | Đều cực thấp (`< 0.01`, `0%` lexical repetition) |
| `distinct_1` / `distinct_3` | `0.638 / 0.993` | **`0.680`** / `0.990` | Từ vựng kể chuyện thương hiệu phong phú hơn nhẹ ở `distinct_1` |
| `simulated_played_duration_sec` | `124.231s` (`20.71%`) | `124.229s` (`20.70%`) | Gần như đồng nhất (`~124.2s`) |
| `tokens_per_accepted_proactive_chunk` | `3,769.8` (`22/22`) | `3,779.2` *(`22/23` partial)* | Tiêu thụ token ổn định gần như hệt nhau (`~3.77K` / chunk) |
| `requests_per_completed_topic` (`18`) | `1.22` (`22/18`) | `1.28` (`23/18`, gồm `+1` 503) | Khi trừ `1` lỗi 503, đều đúng `22/18 = 1.22` req/topic |

---

## 9. Phân tích Kể chuyện & Độ phủ Ngữ nghĩa (`Objectives 1 & 2`)

1. **Khả năng tổng quát hóa (`Objective 1`):** Xu hướng từ Batch 1A lặp lại nhất quán trên Batch 1B: `LangGraph W=5` phủ trọn `100%` (`12/12` mandatory, `18/18` planned), trong khi `Script-first` tụt xuống `75.00%` mandatory (`9/12`) và `66.67%` planned (`12/18`). Lý do không phải chất lượng kiến thức khác biệt, mà vì `Script-first` (`max_retries=0`) không có khả năng tự rút gọn khi `gemini-3.5-flash-lite` sinh `21–24` từ.
2. **Chất lượng kể chuyện thương hiệu (`Objective 2`):**
   - Vì mỗi chủ đề trong `brand_storytelling_10m_ext` thường tập trung `1` talking point cô đọng hơn so với `product_education_10m_ext`, số câu bị lược ý phụ có phần giảm bớt (nhiều lượt giữ khá trọn vẹn `origin`, `harvest`, `sensory`), giúp `distinct_1` của `W=5` tăng từ `0.638` lên `0.680`.
   - Tuy nhiên, điểm yếu cấu trúc từ Batch 1A vẫn giữ nguyên: các câu vẫn ngắn (`12–20` từ, trung bình `17.0` từ ở `W=5`), **thiếu câu nối chuyển cảnh khi chuyển sang sản phẩm mới** (ví dụ từ Turn `[5]` mật ong nhảy thẳng sang Turn `[6]` *"Búp trà hái thủ công..."*, và từ Turn `[11]` trà nhảy sang Turn `[12]` *"Mắc ca được tuyển chọn..."*), đồng thời `W=5` Turn `[14]` có câu fallback báo giá `195.000đ` chen giữa `macadamia-harvest` và `macadamia-sensory` khi gặp `HTTP 503`.
   - Đánh giá chính thức `FULL/PARTIAL/MISS` và `6` tiêu chí Rubric `v0.1` đang chờ người chấm trên [`human_eval/`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/human_eval/).

---

## 10. Phân tích An toàn Thương mại, OCOP & Bằng chứng (`Objective 3`)

Kiểm toán toàn bộ `36` lượt phát (`17` `Script-first` + `19` `LangGraph W=5`) trên [`e01_ext_v1_verified_skus.json`](../data/products/e01_ext_v1_verified_skus.json) `v1.0.1`:

1. **Structural Hard Gates & Cross-SKU (`0` vi phạm):** `0` metadata leak, `0` chunk replay, `0` sai mã bằng chứng, `0` cross-SKU attribution, `0` bịa giá (`159.000đ` / `245.000đ` / `195.000đ`) hay công dụng chữa bệnh.
2. **Chất lượng bảo toàn chứng nhận OCOP mô phỏng (`3` SKUs):**
   - `SKU-TEA-02` (`Turn [8]` Script-first / `Turn [9]` W=5) và `SKU-MACADAMIA-03` (`Turn [14]` Script-first / `Turn [16]` W=5) đều giữ được chữ `"mô phỏng"` hoặc `"hồ sơ OCOP 4 sao"`.
   - **Phát hiện cần lưu ý ở `SKU-HONEY-01` (`topic-ext-brand-honey-ocop`):** Cả `Script-first` Turn `[3]` (*"Sản phẩm đạt OCOP bốn sao cấp tỉnh với tem truy xuất rõ ràng trên thân chai."*) và **`LangGraph W=5` Turn `[3]` (*"Sản phẩm đạt chứng nhận OCOP bốn sao với tem truy xuất nguồn gốc rõ ràng."*) đều bỏ mất cụm `"hồ sơ mô phỏng"`** có trong `talking_points` và `ev-e01-honey-ocop`! Điều này làm lời thoại đọc lên giống như khẳng định chứng nhận OCOP thật nếu tách khỏi ngữ cảnh dữ liệu synthetic PoC — cần reviewer người thật đánh dấu rõ ở Bước 2.
3. **Điều kiện thương mại & Cảnh báo an toàn:**
   - Không có lượt `PROACTIVE_STORY` nào nhắc chính sách đổi trả (vì kịch bản không có topic đổi trả riêng), nên không phát sinh lỗi bỏ điều kiện video mở hộp; các lượt fallback dùng `ev-*-shipping` chỉ nêu tên, xuất xứ và giá đúng chuẩn.
   - Ở `topic-ext-brand-honey-pairing`, `W=5` Turn `[5]` giữ đúng cảnh báo `"lưu ý tránh dùng trẻ dưới một tuổi"` (trong khi `Script-first` bị `SAFE_ABORT_NO_CANDIDATE` mất hoàn toàn topic này).
   - Ở `topic-ext-brand-macadamia-pairing`, **`W=5` Turn `[18]` bị lỗi biến dạng ngữ nghĩa sau rewrite**: đổi `", lưu ý tránh dùng cho người dị ứng hạt"` thành **`"...trộn salad hoặc tránh dùng cho người dị ứng hạt nhé."`** (chi tiết ở Mục 15).
4. **Evidence Support (`P05 ALLOW` ≠ `100%` hỗ trợ trích dẫn):** Tương tự Batch 1A, ở `topic-ext-brand-macadamia-packaging`, cả `Script-first` Turn `[15]` và `W=5` Turn `[17]` đều dùng `"nắp vặn kín khí"` (xuất phát từ `talking_points`, nhưng `ev-e01-ext-macadamia-packaging` ghi `"nắp vặn chắc chắn"`), riêng `W=5` Turn `[17]` còn nhắc `"hạn 12 tháng"` mà không dẫn `ev-e01-macadamia-quality` (dù `ev-e01-macadamia-quality` nằm trong `fact_refs` của topic).

---

## 11. Phân tích Rewrite, Fallback & Độ tin cậy (`Objective 4`)

- **Tỷ lệ tổng thể vs tỷ lệ thuần logic (loại trừ `HTTP 503`):**
  - `Script-first`: `wasted_calls` tổng = `33.33%` (`6/18`), trong đó `HTTP 503` = `1/18` (`5.56%`) và **logic `OVER_MAX_DURATION_SEC` = `5/18` (`27.78%` tổng; `29.41%` trên non-503)**. `fallback_rate` tổng = `27.78%` (`5/18`), **logic fallback = `22.22%` (`4/18`)**, `safe_abort` = `5.56%` (`1/18`).
  - `LangGraph W=5`: `wasted_calls` tổng = `21.74%` (`5/23`), trong đó `HTTP 503` = `1/23` (`4.35%`) và **logic `OVER_MAX_DURATION_SEC` = `4/23` (`17.39%` tổng; `18.18%` trên non-503)**. `rewrite_rate` tổng = `21.05%` (`4/19` turns), `fallback_rate` tổng = `5.26%` (`1/19` do `HTTP 503`), và **`logic fallback = 0.00%`** (`0/19`).
- **Trả lời Objective 4:** `bounded_rewrite` tiếp tục giúp LangGraph hoàn thành `100%` `StoryPlan` (`4/4` lượt vượt độ dài đều sửa thành công ngay lần `retry=1`), và nhìn chung giữ tốt các ý chính ở `3/4` lượt rewrite (`tea-origin`, `tea-harvest`, `tea-brewing`), nhưng vẫn có **`1/4` lượt (`macadamia-pairing`) làm biến dạng ngữ pháp cảnh báo dị ứng khi nén câu**.

---

## 12. Sử dụng Token, Độ trễ & Sổ cái Ngân sách (`Objective 5`)

1. **Sổ cái Ngân sách ([`budget_ledger.json`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/budget_ledger.json)):**
   - Run 1 (`script_first_upfront_llm`): `18 / 30` req (`0` `HTTP 429`, `1` `HTTP 503` tại `c4`), `0.00 USD`.
   - Run 2 (`langgraph_w5`): `23 / 30` req (`0` `HTTP 429`, `1` `HTTP 503` tại `c17`), `0.00 USD`.
   - **Tổng Batch 1B:** **`41 / 60` requests** (`dư 19`), `rate_limited = false`, **`0.00 USD`**.
2. **Token Usage (`PARTIAL MEASURED` trên cả 2 runs):**
   - Do mỗi run có đúng `1` lỗi `HTTP 503` không trả về `usageMetadata`, tổng hợp trong `token_usage.json` đều là **`UNAVAILABLE`**, và `thinking_tokens` là **`UNAVAILABLE`** (`null` trên `41/41` calls).
   - Trên các call đo được: `Script-first` (`17/18` calls) dùng `36,470` in / `3,174` out (`39,644` total, trong đó `11,672` tokens lãng phí ở `5` calls quá `20` từ = `3,303.7` tokens/accepted chunk); `LangGraph W=5` (`22/23` calls) dùng `65,319` in / `2,707` out (`68,026` total, trong đó `12,948` tokens lãng phí ở `4` calls rewrite = `3,779.2` tokens/accepted chunk).
3. **Độ trễ & Giới hạn đo lường (`Finding G`):**
   - `provider_latency_ms` P50 là `5,943.9 ms` (`Script-first`) và `5,951.9 ms` (`W=5`), P95 là `7,378.7 ms` và `8,169.0 ms`. Như đã xác minh ở `Finding G`, **chỉ số này đã bao gồm client pacing sleep `6.0s`**, còn `provider_calls.jsonl` không lưu `sleep_ms` tách riêng; khi không bị ngủ điều tiết (`c0` của `Script-first = 1,777.9 ms`, `c20` của `W=5 = 3,341.1 ms`), độ trễ HTTP thô ở mức `~1.78s–3.73s`. Do đó không kết luận đây là độ trễ inference thuần túy hay tốc độ realtime production.
   - `Time-to-First-Candidate`: `Script-first` mất **`103.69s`** sinh xong toàn bộ upfront trước khi phát câu đầu, trong khi `LangGraph W=5` sẵn sàng phát câu đầu sau **`5.40s`** (`c0`).

---

## 13. Thời lượng Phiên & Các Giới hạn Nghiên cứu

- **Duration Fulfillment (`Finding F`):** `Script-first` đạt **`118.08s / 600s` (`19.68%`)**, `LangGraph W=5` đạt **`124.23s / 600s` (`20.70%`)**. Độ dài `18` chủ đề × `<= 8.0s` không thể kéo dài tới `10–30` phút mà không lặp hoặc bịa fluff; thời lượng mô phỏng từ `words / 2.6` chưa phải audio TTS/lip-sync thật.
- **Giới hạn khác:** `n=1` mỗi phương pháp trên mỗi kịch bản (`seed=42`, mô hình cloud bất định); chưa chạy `W=10/W=20` trên Brand Storytelling (theo phạm vi rút gọn `DR-P06-012`); `Human Blind Evaluation` và `GoldFactualLabel` của cả Batch 1A lẫn 1B vẫn đang `PENDING`; tỷ lệ `wasted_calls` do vượt `20` từ (`18%–29%`) vẫn cao hơn ngưỡng mục tiêu `10%`.

---

## 14. Hồ sơ Đánh giá Con người Batch 1B (`human_eval/`)

Bộ `6` tệp chấm mù từ đúng `2` runs thật của Batch 1B đã được xuất và kiểm tra sạch `100%` tại [`runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/human_eval/`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/human_eval/):

1. [`blind_eval_sheet.csv`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/human_eval/blind_eval_sheet.csv) & [`blind_eval_sheet.jsonl`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/human_eval/blind_eval_sheet.jsonl): `2` mẫu (`SAMPLE_001` = `METHOD_A`, `SAMPLE_002` = `METHOD_B`), toàn bộ điểm để trống, `0` rò rỉ nhãn thật.
2. [`factual_and_semantic_review_sheet.csv`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/human_eval/factual_and_semantic_review_sheet.csv): `37` dòng (`SAMPLE_001`: `19` lượt; `SAMPLE_002`: `17` lượt + `1` dòng `MISSING_TOPIC` cho `topic-ext-brand-honey-pairing`), toàn bộ `5` cột reviewer để trống.
3. [`blind_key_mapping.private.json`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/human_eval/blind_key_mapping.private.json): Tệp giải mã tách riêng.
4. [`REVIEWER_GUIDE_BLIND_QUALITY.md`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/human_eval/REVIEWER_GUIDE_BLIND_QUALITY.md): Hướng dẫn Bước 1 (Rubric `v0.1`).
5. [`REVIEWER_GUIDE_FACTUAL_AND_SEMANTIC_AUDIT.md`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/human_eval/REVIEWER_GUIDE_FACTUAL_AND_SEMANTIC_AUDIT.md): Hướng dẫn Bước 2 kèm `ProductFact`, `EligibilitySnapshot` (`SYNTH-OCOP-4S-*`), `30` `EvidenceChunk`, `expected_talking_points`, quy tắc chấm `MISSING_TOPIC`, OCOP mô phỏng và cảnh báo an toàn/chính sách.

---

## 15. Các Trường hợp Lỗi Rewrite Giá trị cho `P06-E04` (`E04 Candidate Failure Cases`)

Trích xuất từ `graph_trace.jsonl` của Batch 1B (cùng đối chiếu Batch 1A), phục vụ chuẩn bị nghiên cứu `P06-E04` *(chưa triển khai trong phiên này)*:

| Case ID | Trace & Topic | Candidate Lượt đầu (`att[0]`) & Feedback | Candidate Sau Rewrite (`att[1]`) | Phân tích Evidence, Talking Points & Safety | Kết quả |
|---|---|---|---|---|---|
| **`E04-CASE-1B-01`** | `W=5` `turn 20` (`macadamia-pairing`) | `22` từ (`8.46s`), `ev=['ev-e01-macadamia-usage', 'ev-e01-ext-macadamia-safety']`: *"Nhà mình có thể ăn liền, làm sữa hạt hoặc trộn salad, **lưu ý tránh dùng cho người dị ứng hạt nhé**."* -> Feedback: `OVER_MAX_DURATION_SEC`, rút về `12–18` từ, giữ talking points. | `18` từ (`6.92s`), `ev=[...usage, pairing, safety]`: *"Nhà mình ăn liền, làm sữa hạt, trộn salad **hoặc tránh dùng cho người dị ứng hạt nhé**."* | Bổ sung đủ `ev-e01-ext-macadamia-pairing`, nhưng để cắt `4` từ, LLM thay **`, lưu ý`** bằng **`hoặc`** — làm biến dạng cảnh báo an toàn dị ứng thành lựa chọn song song! P05 vẫn `VERIFIED`. | `ACCEPTED` *(Rủi ro ngữ nghĩa an toàn -> bài test trọng tâm cho E04)* |
| **`E04-CASE-1B-02`** | `W=5` `turn 12` (`tea-brewing`) | `28` từ (`10.77s`), `ev=['ev-e01-tea-usage']`: viết chữ toàn bộ số (`"năm gram"`, `"một trăm năm mươi mi li lít"`, `"tám lăm đến chín mươi"`, `"ba mươi đến bốn mươi lăm"`). | `15` từ (`5.77s`), `ev=['ev-e01-tea-usage']`: *"Dùng **5g** trà với **150ml** nước **85-90** độ C, hãm **30-45** giây cho lượt đầu."* | Bảo toàn `100%` talking points, đơn vị đo (`g`, `ml`, `độ C`, `giây`) và `cited_evidence_ids` bằng cách chuyển chữ sang ký hiệu số. | `ACCEPTED` *(Rewrite mẫu mực)* |
| **`E04-CASE-1B-03`** | `W=5` `turn 7` (`tea-origin`) | `22` từ (`8.46s`), `ev=['ev-e01-tea-origin']`: viết `"một tôm hai lá"`, `"một nghìn ba trăm mét"`. | `18` từ (`6.92s`), `ev=['ev-e01-tea-origin']`: *"Búp trà hái thủ công **1 tôm 2 lá** từ cây cổ thụ trên **1.300m** tại Phìn Hồ."* | Bảo toàn `100%` nội dung, địa danh Phìn Hồ và trích dẫn chỉ nhờ đổi số viết chữ thành số. | `ACCEPTED` *(Rewrite mẫu mực)* |
| **`E04-CASE-1B-04`** | `W=5` `turn 8` (`tea-harvest`) | `21` từ (`8.08s`), `ev=['ev-e01-ext-tea-harvest']`: *"Búp trà làm héo tự nhiên trên nong tre, sao diệt men và vò nhẹ giữ nguyên lớp tuyết trắng mịn."* | `16` từ (`6.15s`), `ev=['ev-e01-ext-tea-harvest']`: *"Làm héo tự nhiên trên nong tre, sao vò nhẹ giữ nguyên lớp tuyết trắng mịn."* | Bỏ chữ `"Búp trà"` và gộp `"sao diệt men và vò nhẹ"` -> `"sao vò nhẹ"` khớp `talking_points`; giữ nguyên trích dẫn. | `ACCEPTED` *(Lược nhẹ vế phụ)* |
| **`E04-CASE-1B-05`** | `Script-first` `turn 5` (`honey-pairing`) | `24` từ (`9.23s`), `max_retries=0` -> bị loại vì `OVER_MAX_DURATION_SEC` sau khi SKU-HONEY-01 đã cạn 2 fallback (`turn 0` & `turn 4`). | *(Không có rewrite)* | Chủ đề bị hủy an toàn (`0` candidate, `0` vi phạm), chứng minh giới hạn của baseline không có rewrite + kho fallback cố định `2` câu/SKU. | `SAFE_ABORT_NO_CANDIDATE` |
| *(Tham chiếu 1A)* | `W=10` `turn 18` (`macadamia-safety`) & `W=20` `turn 10` (`tea-quality`) | Batch 1A: `W=10` đổi `"không ăn gói hút ẩm"` thành `"giữ gói hút ẩm"` sau `2` retries (`FAIL`); `W=20` `tea-quality` kẹt ở `22 -> 21 -> 21` từ cạn `2` retries. | Xem chi tiết trong `12-...` Mục 8 & Mục 11. | Cho thấy `bounded_rewrite` chịu áp lực `<= 20` từ có thể làm rơi cảnh báo an toàn hoặc cạn retry dù chỉ dư `1` từ. | `ACCEPTED (FAIL)` / `FALLBACK` |

---

## 16. Đề xuất Thí nghiệm Tối thiểu cho Track 2 — History Window Stress Test (`PLAN ONLY`, `0` API calls)

Mục tiêu của **Track 2 (`RQ3` / `RQ5`)** là kiểm chứng **cơ chế phát hiện lặp và cửa sổ bộ nhớ `W ∈ {5, 10, 20}`** trong điều kiện có nội dung lặp lại bắt buộc (`min_chunks_per_topic=2`), **không** phải mô phỏng chất lượng storytelling tự nhiên.

### 16.1. Thiết kế Tối thiểu Phân tách Đủ Cả Ba Cửa sổ `W=5 / 10 / 20`
Do `ArcSequencer` chạy tuần tự theo từng SKU, khoảng cách lặp (`lag`) giữa lần phát 1 và lần phát 2 của cùng một topic đúng bằng **số topic/SKU**:
- Kịch bản `e01_formal_v1 · window_stress_12lag_3sku` có **`12` topics/SKU (`36` topics × `min_chunks_per_topic=2` = `72` base turns, `lag = 12`)**, thỏa đồng thời **`W=5 < 12`**, **`W=10 < 12`**, và **`W=20 >= 12`**.
- **Phương án Tối thiểu Khuyến nghị (Gọn nhất — `1` Kịch bản Stress Chính, `4` Runs):** Chạy **`window_stress_12lag_3sku` (`lag=12`, `m=2`, `seed=42`)** trên `4` cấu hình (`script_first_upfront_llm`, `langgraph W=5`, `W=10`, `W=20`). Phương án này phân biệt trực tiếp `W=20` (vẫn nhớ lượt 1 khi sang lượt 2, kích hoạt `RepetitionDetector`) với `W=5` và `W=10` (đều quên lượt 1 ở `lag=12`), mà không phải tốn thêm ~200+ calls cho `lag=6/8`.
- **Tùy chọn Bổ sung Nếu Cần Tách Riêng `W=5` vs `W=10`:** Nếu sau khi xem kết quả `lag=12` vẫn cần bằng chứng tách biệt trực tiếp `W=5` khỏi `W=10`, mới chạy bổ sung gọn **`product_education_10m_ext` (`lag=6`, `m=2`, `36` base turns)** hoặc **`window_sensitivity_stress_24t` (`lag=8`, `m=2`, `48` base turns)** chỉ cho `W=5` vs `W=10` (khoảng `95–130` req).

### 16.2. Ràng buộc Công bằng & Ngân sách Thực tế cho Track 2 (`lag=12`, `m=2`)
- **Công bằng tham số tuyệt đối:** Giữ **cùng `max_turns = 120`** và **cùng `max_requests_per_run`** cho cả `W=5`, `W=10`, `W=20` trong cùng scenario (tuyệt đối không cấp cap khác nhau cho từng `W` rồi so sánh như cùng điều kiện).
- **Ước lượng ngân sách dựa trên bằng chứng Mock + Gemini thật:**
  - Kết quả Mock trước đó trên `lag=12 (m=2)` đã tiêu tốn: `Script-first = 72`, `W=5 = 97`, `W=10 = 102`, `W=20 = 156` calls (tổng `427` calls; riêng `W=10 + W=20 = 258` calls, nên đề xuất `220` cũ là thiếu).
  - Trên Gemini thật (cộng thêm ~`20%` duration rewrite quan sát được ở 1A/1B và ~`5–10%` dự phòng `HTTP 503`): ước tính thực tế `Script-first ~72`, `W=5 ~115–130`, `W=10 ~120–135`, `W=20 ~170–190` (hoặc dừng sớm ở `MAX_CONSECUTIVE_ABORTS`).
  - **Đề xuất chia ngày phù hợp `500 RPD` Free Tier (`0 USD`):** Cố định chung **`max_requests_per_run = 200`** và **`max_turns = 120`** cho mọi cấu hình LangGraph (`Script-first` cũng dùng `max_requests_per_run = 200`, tự nhiên chỉ gọi tối đa `72` upfront calls):
    - **Batch 2A (Ngày 1):** `script_first_upfront_llm` (`~72` calls) + `langgraph W=5` (`~125` calls) -> `global_max_requests = 250` (`~40–45` phút).
    - **Batch 2B (Ngày 2):** `langgraph W=10` (`~130` calls) -> `global_max_requests = 200`.
    - **Batch 2C (Ngày 3):** `langgraph W=20` (`~180` calls, dừng an toàn nếu chạm `MAX_CONSECUTIVE_ABORTS` hoặc `200` req) -> `global_max_requests = 200`.
- **Chỉ số bắt buộc báo cáo ở Track 2:** `lag` thực tế trên `ShortTermPlayedHistory`, tỷ lệ hoàn tất đủ `2` chunks/topic (`required_chunk_completion` từ `coverage.py`), số cơ hội lặp (`repetition_opportunities`), số lần `RepetitionDetector` từ chối theo tầng (`EXACT/LEXICAL/REPEATED_FACTS`), số rewrite, `safe_abort` / `MAX_CONSECUTIVE_ABORTS`, tách biệt **internal detection window `W`** với **evaluation horizon toàn phiên**, và ghi rõ đây là stress test cơ chế chống lặp.

---

## 17. Các Công việc Còn lại & Definition of Done của `P06-E01`

| Hạng mục DoD (`docs/11-...`) | Trạng thái Hiện tại | Công việc Còn lại |
|---|---|---|
| **DoD-1:** Calibration & Acceptance Criteria Lock | `APPROVED OPTION B` | Hoàn tất chấm mù chính thức trên mẫu Batch 1A & 1B (`PENDING`) |
| **DoD-2:** Thực thi Formal Benchmark | `1A + 1B COMPLETED` | Chờ phê duyệt & thực thi **Track 2 (`lag=12`, `m=2`)** (Track 3 đang khuyến nghị hoãn) |
| **DoD-3:** Human Blind Eval & Gold Factual Labels | **`PENDING`** | Người chấm độc lập điền `human_eval/` của Batch 1A, Batch 1B (và Track 2 sau đó) |
| **DoD-4:** Lưu trữ bất biến toàn bộ artifacts | `COMPLETED (1A + 1B)` | Lưu bổ sung thư mục Track 2 sau khi chạy |
| **DoD-5:** Tổng hợp `notebooks/` & `reports/` | `NOT STARTED` | Chạy `notebooks/06_e01_results_analysis.ipynb`, xuất `reports/{tables,figures}` & `reports/p06_e01_research_report.md` |
| **DoD-6:** Kết luận `GO/CHANGE/NO-GO/INCONCLUSIVE` | `PENDING` | Tổng hợp đủ bằng chứng 1A + 1B + Track 2 + Human Eval và xin sign-off Reviewer độc lập |

---

## 18. Git Diff & Kiểm chứng Hồi quy Hậu Thực thi

- **Các tệp thêm/sửa mới trong phiên Batch 1B** *(100% nằm trong `experiments/sales-intelligence/autonomous-storytelling/`)*:
  - Tạo [`configs/experiments/p06_e01_formal_batch1b.yaml`](../configs/experiments/p06_e01_formal_batch1b.yaml).
  - Cập nhật [`research/decision_log.md`](../research/decision_log.md) (`DR-P06-012`) và phụ lục Mục 11 của [`docs/11-e01-t09-formal-benchmark-protocol.md`](./11-e01-t09-formal-benchmark-protocol.md).
  - Lưu [`runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/ai_assisted_eval/`](../runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/ai_assisted_eval/) (Batch 1A AI-assisted evaluation).
  - Tạo thư mục kết quả bất biến [`runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/`](../runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/) (`protocol_amendment_and_criteria_lock.json`, `budget_ledger.json`, `batch_summary.json`, `comparison.{json,csv,md}`, `2` thư mục run đầy đủ artifacts, và `6` tệp `human_eval/`).
  - Tạo [`docs/13-e01-t09-formal-benchmark-batch1b-report.md`](./13-e01-t09-formal-benchmark-batch1b-report.md) và cập nhật [`docs/README.md`](./README.md), [`AGENTS.md`](../AGENTS.md).
  - **Không sửa** `src/p06/`, `prompts/`, `data/`, `configs/models/`, `p06_e01_formal_batch1a.yaml`, Pilot v1/v2 hay Batch 1A `human_eval/`.
- **Kiểm thử hồi quy & kiểm tra độc lập:**
  - `pytest experiments/sales-intelligence/autonomous-storytelling/tests -q`: **287 passed, 0 failed, 0 skipped** (`59.30s`).
  - `pip check`: **No broken requirements found**.
  - Kiểm tra `AGENTS.md`: **22,469 bytes** (`< 24,000` bytes), không YAML frontmatter.
  - Kiểm tra **10/10** SHA-256 locked artifacts trong [`11-e01-t09-formal-benchmark-protocol.md`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/docs/11-e01-t09-formal-benchmark-protocol.md) và `p06_e01_formal_batch1b.yaml` (`f380892c137606f0277aafa809a4623a904a9f262c10797cf0cb897b42079fd2`): **100% khớp**.
  - Kiểm tra phạm vi Git (`git status --short`, `git diff --stat`): chỉ thay đổi trong `experiments/sales-intelligence/autonomous-storytelling/`, không sửa `src/p06/`, `prompts/`, `data/`, `configs/models/`, `p06_e01_formal_batch1a.yaml` hay `scripts/run_gemini_formal_batch.py`.
  - Đánh giá độc lập read-only (`hydrogen-scout`, `b1e4963c`): **PASS** cho Batch 1A `ai_assisted_eval/` (3 tệp) và `human_eval/` nguyên vẹn (6 tệp); **PASS** cho gói `human_eval/` Batch 1B (6 tệp, `0` rò rỉ nhãn phương pháp trên 5 tệp công khai, `37` dòng review rỗng hoàn toàn, `0` secrets); **PASS** đối chiếu 100% số liệu, trường hợp E04 và bảng cross-scenario trong báo cáo với raw JSON/JSONL; xác nhận đủ 10 tệp chuẩn trong mỗi thư mục run của Batch 1B khớp schema Batch 1A (`config.yaml`, `errors.jsonl`, `graph_trace.jsonl`, `manifest.json`, `metrics.json`, `playback_events.jsonl`, `provider_calls.jsonl`, `story_plan.json`, `token_usage.json`, `transcript.jsonl`).

---

**Trạng thái dừng:** **`AWAITING_BATCH_1B_REVIEW_AND_TRACK2_APPROVAL`**  
*(Không gọi thêm Gemini API, không tự chạy Track 2 và không đánh dấu `P06-E01` là `VALIDATED` hoặc `COMPLETED`.)*
