# P06-E01-T09 — Phân tích Tổng hợp Nghiên cứu Track 2: History Window Sensitivity (`Track 2A` + `Track 2B`) & Kế hoạch Chuẩn bị Đóng `P06-E01`

**Trạng thái:** `TRACK 2A + 2B LIVE COMPLETED` · **Cổng tổng thể:** `NOT_EVALUATED` *(`Human Blind Evaluation` & `GoldFactualLabel` của Track 2A/2B = `PENDING`; `P06-E01` CHƯA đóng và KHÔNG được đánh dấu `VALIDATED`/`COMPLETED`)*  
**Ngày tổng hợp:** `2026-11-27` · **Nhánh:** `research/p06-autonomous-storytelling` · **Mô hình khóa:** `gemini-3.5-flash-lite` (`Free Tier`, `0.00 USD`, dữ liệu `SYNTHETIC`)

---

## §1. Tóm tắt Điều hành (Executive Summary)

Chuỗi thực nghiệm **Track 2 History Window Sensitivity** (gồm **Track 2A** tại `lag=6` và **Track 2B** tại `lag=12`, tổng cộng **`182` API requests** trên `gemini-3.5-flash-lite` Free Tier ở chi phí **`0.00 USD`**, **`0` HTTP 429**) đã quan sát trong điều kiện stress có kiểm soát (`n=1` mỗi cấu hình) **hai chế độ hành vi đối lập xoay quanh ranh giới `history_window` (`W`) và `actual_lag`**:

1. **Khi `W < planned_lag`** (`W=5` ở `lag=6`; `W=10` ở `lag=12`): Tác nhân hoàn tất **`100.0%` chủ đề với `min_chunks_per_topic >= 2`** (`18/18` planned / `12/12` mandatory ở Track 2A; `36/36` planned & mandatory ở Track 2B) cùng **`0` lần từ chối từ `RepetitionDetector`** — bởi **100% lượt quay lại rơi bên ngoài cửa sổ quan sát `W`**. Hệ quả là để lọt **exact normalized text replay** (`2` ở T2A `W=5`; `1` ở T2B `W=10`), `lexical_repetition_rate` cao (`28.57%` và `32.39%`) và mức nhảy vọt của `windowed_ngram3_jaccard_mean` ngay khi vượt qua ngưỡng `lag` (`0.0028 → 0.2031` tại `w5→w10` ở T2A; `0.0131 → 0.2455` tại `w10→w20` ở T2B).
2. **Khi `W > planned_lag`** (`W=10` ở `lag=6`; `W=20` ở `lag=12`): Ngay tại chu kỳ quay lại đầu tiên (`turn_index = 6..10` ở T2A; `turn_index = 12..16` ở T2B), mọi chủ đề vừa nói của SKU đầu tiên đều còn nằm trong `history_window` và đều chỉ có `1` `allowed_claim_id` duy nhất. `RepetitionDetector` lập tức đánh dấu **`REPEATED_FACTS:SWITCH_TOPIC`** liên hoàn, đốt cạn toàn bộ quỹ `2` lượt `PREAPPROVED_FALLBACK` của SKU rồi kích hoạt `3` lượt `SAFE_ABORT_NO_CANDIDATE` liên tiếp → dừng cứng ở **`MAX_CONSECUTIVE_ABORTS` với `0%` (`0/18` planned / `0/12` mandatory và `0/36`) chủ đề hoàn thành `>= 2` chunks**.
3. **Quan sát tương phản tại `W=10` (không phải so sánh đơn biến):** Cấu hình **`W=10`** dừng ở `0/18` (`MAX_CONSECUTIVE_ABORTS`, `23` calls) trong Track 2A (`lag=6`, `e01_ext_v1`, `18` topics) và hoàn tất `36/36` (`EARLY_COMPLETION`, `83` calls) trong Track 2B (`lag=12`, `e01_formal_v1`, `36` topics). Vì hai Track khác đồng thời **dataset, số lượng/nội dung chủ đề và `lag`**, kết quả này minh họa sự phụ thuộc vào cấu hình bài toán chứ không phải chứng minh nhân quả tổng quát tách riêng biến `lag`; việc cô lập biến `lag` được kiểm chứng độc lập bởi `Fixed-History Detector Check` ngoại tuyến (`tests/unit/test_formal_benchmark_prep.py`).

---

## §2. Câu hỏi Khảo sát Track 2 (`Exploratory Findings`, không phải RQ gốc)

| Mã Khảo sát | Câu hỏi Thực nghiệm Track 2 | Kết quả Quan sát Live (`n=1` mỗi cấu hình) |
|---|---|---|
| `EXP-W1` | Tăng `W` khi `min_chunks_per_topic = 2` có giúp giảm lặp ngôn từ mà vẫn giữ nguyên độ phủ chủ đề không? | **Không đạt trong điều kiện stress 1 claim/topic.** Tăng `W` vượt qua `actual_lag` làm `mandatory_topic_coverage` sụp từ `1.0 → 0.0` do `REPEATED_FACTS` bế tắc. |
| `EXP-W2` | Hành vi đối xứng `W < lag` vs `W > lag` có lặp lại khi tăng quy mô từ `lag=6` (`18` chủ đề) lên `lag=12` (`36` chủ đề) không? | **Có sự tương đồng cấu trúc.** Hành vi ở `(W=5 vs W=10 @ lag=6)` lặp lại theo hướng tương đồng ở `(W=10 vs W=20 @ lag=12)`, tuy nhiên không kết luận thành định luật phổ quát vì `n=1` và khác dataset. |
| `EXP-W3` | Lệch giữa `deterministic mock` và `gemini-3.5-flash-lite` live lớn tới mức nào ở chế độ căng lịch sử? | **Rất lớn ở cấu hình bế tắc.** Mock cho `18/18` ở T2A `W=10` và `35/36` trước abort ở T2B `W=20`, trong khi live dừng ngay tại SKU đầu tiên (`0/18` và `0/36`). |
| `EXP-W4` | Khi `W < lag`, `windowed_ngram3_jaccard_mean` thay đổi ra sao qua ranh giới `lag`? | Bật tăng **`~73.4×`** từ `w5` sang `w10` ở T2A (`0.0028 → 0.2031`, chính xác `73.44×`) và **`~18.8×`** từ `w10` sang `w20` ở T2B (`0.0131 → 0.2455`, chính xác `18.78×`). |

---

## §3. Thiết kế Thực nghiệm & Tính Toàn vẹn Giao thức

- **Hai đợt thí nghiệm tuần tự (`LangGraph Structured Story`, `seed=42`, `min_chunks_per_topic=2`, `max_chunk_duration_sec=8.0s`):**
  - **Track 2A (`product_education_10m_ext`):** **`18` chủ đề kế hoạch** (`3` SKU × `6` chủ đề, trong đó **`12` `mandatory` topics** và `6` non-mandatory topics; `planned_lag = 6`, `14` verified claims), so sánh `W=5` (`W < lag`) với `W=10` (`W > lag`), dữ liệu [`e01_ext_v1`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/docs/15-e01-t09-track2a-live-report.md).
  - **Track 2B (`window_stress_12lag_3sku`):** **`36` chủ đề bắt buộc** (`3` SKU × `12` chủ đề, toàn bộ `36` đều `mandatory`; `planned_lag = 12`, `21` verified claims), so sánh `W=10` (`W < lag`) với `W=20` (`W > lag`), dữ liệu [`e01_formal_v1`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/docs/16-e01-t09-track2b-live-report.md).
- **Khóa bất biến & Hard Cap:** Toàn bộ `src/p06/`, `prompts/`, `data/`, `configs/` giữ nguyên **13/13 SHA-256** so với Baseline/Readiness. Ở Track 2B, tệp YAML khóa [`p06_e01_formal_track2b_w10_w20.yaml`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/configs/experiments/p06_e01_formal_track2b_w10_w20.yaml) giữ nguyên `global_max_requests = 400`, còn **operational cap thực tế `<= 200` requests** theo phê duyệt của người dùng được thực thi qua [`budget_ledger.json`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/formal_benchmark_v1/track2b_large_window_lag12_s42/budget_ledger.json) (`global_max_requests = 200`, `max_requests_per_run = 200`) để bảo toàn YAML SHA-256.

---

## §4. Ngân sách, Quota & Nhật ký Vận hành Thực tế

| Đợt chạy | YAML Cap Approved | Operational Cap | Thực Dùng | Quỹ Còn | Thời gian (UTC / Giờ VN) | HTTP 429 | HTTP 503 | Chi phí | Secrets Leak |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| Track 2A | 240 | 240 | **71** (`48 + 23`) | 169 | `2026-11-26T23:15Z–23:23Z` (`06:15–06:23 VN 27/11`) | 0 | 1 (`W=10 [c19]`) | `0.0 USD` | 0 |
| Track 2B | 400 *(YAML khóa)* | **200** *(Ledger cap)* | **111** (`83 + 28`) | 89 | `2026-11-27T03:29Z–03:41Z` (`10:29–10:41 VN 27/11`) | 0 | 1 (`W=20 [c24]`) | `0.0 USD` | 0 |
| **Tổng Track 2** | **640** | **440** | **182** | — | Cả 2 đợt đều chạy trước reset `15:00 VN 27/11` | **0** | **2** *(đơn lẻ)* | **`0.0 USD`** | **0** |

> *Lưu ý quota (đính chính):* Cả Track 2A (`06:15–06:23 VN`) và Track 2B (`10:29–10:41 VN`) đều diễn ra trước mốc reset `15:00 VN 27/11/2026`, nên **không** khẳng định hai đợt chạy thuộc hai chu kỳ quota RPD tách biệt.

---

## §5. Ma trận Số liệu Tổng hợp 4 Phiên Live (`Track 2A` & `Track 2B`)

| Chỉ số | T2A `W=5` (`lag=6`) | T2A `W=10` (`lag=6`) | T2B `W=10` (`lag=12`) | T2B `W=20` (`lag=12`) |
|---|---:|---:|---:|---:|
| **Quan hệ `W` vs `lag`** | **`W < lag`** | **`W > lag`** | **`W < lag`** | **`W > lag`** |
| `termination_reason` | `EARLY_COMPLETION` | `MAX_CONSECUTIVE_ABORTS` | `EARLY_COMPLETION` | `MAX_CONSECUTIVE_ABORTS` |
| `total_model_calls` (`failed`) | `48` (`0`) | `23` (`1` HTTP 503) | `83` (`0`) | `28` (`1` HTTP 503) |
| `played_turns` / `content_traces` | `36` / `36` | **`8` / `11`** | `72` / `72` | `14` / `17` |
| `completed_planned_topics (>= 2)` | **`18 / 18`** (`100%`) | **`0 / 18`** (`0%`) | **`36 / 36`** (`100%`) | **`0 / 36`** (`0%`) |
| `completed_mandatory_topics (>= 2)` | **`12 / 12`** (`1.0000`) | **`0 / 12`** (`0.0000`) | **`36 / 36`** (`1.0000`) | **`0 / 36`** (`0.0000`) |
| `declared_verified_claim_cov` | `14 / 14` (`1.0000`) | `4 / 14` (`0.2857`) | `21 / 21` (`1.0000`) | `7 / 21` (`0.3333`) |
| `simulated_played_duration_sec` | `250.000s` (`41.67%`) | `55.385s` (`9.23%`) | `489.996s` (`81.67%`) | `94.229s` (`15.70%`) |
| `exact_norm_text_replay` (`outside_win`) | **`2`** (`2`) | `0` (`0`) | **`1`** (`1`) | `0` (`0`) |
| `lexical_repetition_rate` | **`0.2857`** (`28.57%`) | `0.0000` | **`0.3239`** (`32.39%`) | `0.0000` |
| `windowed_ngram3` (`w5` / `w10` / `w20`) | `0.0028` / `0.2031` / `0.2031` | `0.0468` / `0.0468` / `0.0468` | `0.0094` / `0.0131` / `0.2455` | `0.0328` / `0.0328` / `0.0354` |
| `detector_NONE / LEX / FACTS` | `36 / 0 / 0` | `6 / 6 / 8` | `72 / 0 / 0` | `12 / 2 / 11` |
| `rewrite_count` / `fallback` / `safe_abort` | `12 / 0 / 0` | `12 / 2 / 3` | `11 / 0 / 0` | `11 / 2 / 3` |
| `wasted_calls` / `total_calls` | `12 / 48` (`25.0%`) | `17 / 23` (`73.9%`) | `11 / 83` (`13.3%`) | `16 / 28` (`57.1%`) |
| `input_tokens` / `output_tokens` | `144,321` / `6,084` | *partial* `67,354` / `2,758` | `281,423` / `9,919` | *partial* `89,237` / `3,185` |
| `structural_hard_gates` / `overall` | `PASS` / `NOT_EVALUATED` | `PASS` / `NOT_EVALUATED` | `PASS` / `NOT_EVALUATED` | `PASS` / `NOT_EVALUATED` |

---

## §6. Phân tích Cơ chế Ranh giới Quan sát: `W < actual_lag` vs `W >= actual_lag` (Phạm vi Stress)

Dữ liệu thực chứng từ 4 phiên stress (`n=1` mỗi cấu hình) ghi nhận hai cơ chế vận hành trái ngược dưới thiết kế `1` claim/topic và `min_chunks_per_topic = 2`:
- **Chế độ vượt hoàn tất (`W < actual_lag`):** Cả `W=5` (`lag=6`) lẫn `W=10` (`lag=12`) đều giữ khoảng đệm dương (`+1` và `+2` lượt). Khi `ArcSequencer` quay lại chủ đề vòng 2, lượt vòng 1 vừa ra khỏi `history_window`, nên `RepetitionDetector` trả `NONE / ALLOW` trên **100% lượt phát** (`36/36` và `72/72`) — hoàn tất bao phủ nhưng không chống lặp xuyên chu kỳ.
- **Chế độ bế tắc (`W >= actual_lag`):** Khi `W` trùm qua chu kỳ `lag` (`W=10 > 6` và `W=20 > 12`), tại ngay lượt đầu vòng 2 (`tr[6]` ở T2A và `tr[12]` ở T2B), lịch sử giữ lại toàn bộ vòng 1. Do mỗi chủ đề chỉ có `1` `allowed_claim_id`, `RepetitionDetector` đánh dấu `REPEATED_FACTS:SWITCH_TOPIC` liên hoàn cho tới khi cạn fallback và chạm `MAX_CONSECUTIVE_ABORTS`.
- **Phân tích đối chiếu `W=10` giữa Track 2A và Track 2B:** Do Track 2A (`18` topics, `e01_ext_v1`) và Track 2B (`36` topics, `e01_formal_v1`) khác nhau đồng thời về dataset, nội dung và `lag`, cặp chạy `W=10` chỉ đóng vai trò minh họa xuyên kịch bản; bằng chứng cô lập biến `lag` thuần túy nằm ở `Fixed-History Detector Check` (`tests/unit/test_formal_benchmark_prep.py`).

---

## §7. Đối chiếu `Actual Lag` Thực tế (Played vs Attempted)

- **Các phiên hoàn thành (`T2A W=5`, `T2B W=10`):** Phân phối `actual_lag` trên toàn bộ lượt quay lại phát thành công đạt **độ đồng đều 100% theo đúng thiết kế** (`{6: 18}` trên T2A `W=5`; `{12: 36}` trên T2B `W=10`), chứng tỏ `ArcSequencer` giữ nhịp hoàn hảo giữa các SKU khi không bị detector chặn chuyển chủ đề.
- **Các phiên sụp đổ (`T2A W=10`, `T2B W=20`):** Không có lượt quay lại nào được phát (`played = 0`). Tuy nhiên ở cấp độ **attempt bị từ chối**:
  - T2A `W=10`: `14` attempts trên `3` chủ đề đầu tiên của Honey có `actual_lag` phân bổ `{5: 3, 6: 2, 7: 6, 8: 3}` — 100% `in_window (<=10)`.
  - T2B `W=20`: `13` attempts trên `3` chủ đề đầu tiên của Honey có `actual_lag` phân bổ `{11: 1, 12: 5, 13: 3, 14: 4}` — 100% `in_window (<=20)`.
  - Sự mở rộng `actual_lag` từ `12 → 13 → 14` trong T2B `W=20` phản ánh chính xác việc `2` lượt `PREAPPROVED_FALLBACK` (`tr[12..13]`) chèn vào danh sách `played_so_far`, đẩy khoảng cách giữa lượt 1 và các lượt retry sau lên dần nhưng vẫn bị `W=20` bao phủ hết.

---

## §8. Động học Lặp Từ vựng & N-gram Đa Tầng

So sánh trực tiếp trên hai phiên chạy hết kịch bản (`T2A W=5` vs `T2B W=10`):
- **`windowed_ngram3_jaccard_mean` như một "máy dò biên độ trễ":**
  - Ở T2A `W=5`: `w5 = 0.0028` (gần 0 tuyệt đối trong cửa sổ 5) → nhảy **`~73.4×`** (`0.002765 → 0.203056`) lên **`w10 = 0.2031`** (ngay sau ngưỡng `lag=6`) và giữ nguyên ở `w20 = 0.2031`.
  - Ở T2B `W=10`: `w5 = 0.0094` và `w10 = 0.0131` (rất thấp trong cửa sổ 10) → nhảy **`~18.8×`** (`0.013074 → 0.245489`) lên **`w20 = 0.2455`** (ngay sau ngưỡng `lag=12`).
- **Tác động tới lặp toàn phiên & lặp nguyên văn:** Dù không có `RepetitionDetector` can thiệp liên vòng, `T2A W=5` và `T2B W=10` đều ghi nhận `max_prior_word_jaccard_mean` quanh **`0.42–0.44`**, `lexical_repetition_rate` **`28.57%–32.39%`**, đồng thời để lọt **`exact_normalized_text_replay`** đúng ở biên ngoài cửa sổ (`2` lần ở T2A `W=5` `lag=6`; `1` lần ở T2B `W=10` `lag=12` trên `honey-10`). *Lưu ý về `distinct_1/2/3`:* chỉ số giảm từ `0.36/0.65/0.74` (`36` lượt ở T2A `W=5`) xuống `0.28/0.55/0.66` (`72` lượt ở T2B `W=10`) **phụ thuộc vào độ dài transcript và kịch bản khác nhau**, nên **không** kết luận trực tiếp `W` lớn làm giảm lexical diversity.

---

## §9. Giải phẫu Cơ chế Bế tắc `RepetitionDetector` (`REPEATED_FACTS`)

Chuỗi nhân quả tất định dẫn đến `MAX_CONSECUTIVE_ABORTS` trong cả `T2A W=10` lẫn `T2B W=20` gồm đúng **4 mắt xích**:
1. **Cấu hình Plan (`1` `allowed_claim_id` / chủ đề):** Để kiểm soát chặt claim theo chủ đề trong Track 2, mỗi chủ đề chỉ khai báo đúng `1` verified claim (`covered_claim_ids`).
2. **Ngưỡng `RepetitionDetector` (`fact_overlap_threshold = 0.80` → `REPEATED_FACTS:SWITCH_TOPIC`):** Khi lượt 1 của chủ đề đã nằm trong `W` lượt gần nhất, bất kỳ câu sinh mới nào sử dụng đúng claim của chủ đề đó đều cho `fact_overlap_ratio = 1.0 >= 0.80`. Kể cả khi `LEXICAL_DUPLICATION` chỉ yêu cầu `REWRITE` ở `attempt 0–1` (`T2B W=20 tr[12]`), ngay khi phrasing bớt trùng từ vựng mà vẫn giữ nguyên fact, detector lập tức chuyển sang phân loại **`REPEATED_FACTS` (`SWITCH_TOPIC`)**!
3. **`SWITCH_TOPIC` trong vòng lặp SKU đóng:** Việc đổi sang chủ đề tiếp theo của cùng `SKU-HONEY-01` (`honey-01 → 02 → 03`) chỉ nhảy sang một chủ đề **khác cũng vừa mới phát ở vòng 1** (cũng nằm gọn trong `W`!).
4. **Cạn Quỹ Dự phòng & `MAX_CONSECUTIVE_ABORTS`:** Mỗi SKU chỉ có `2` câu `PREAPPROVED_FALLBACK` hợp lệ; khi chúng bị tiêu thụ hết ở `2` lượt đầu vòng 2 (`tr[6..7]` ở T2A; `tr[12..13]` ở T2B), `3` lượt kế tiếp đều cạn ứng viên → `SAFE_ABORT_NO_CANDIDATE` → chạm ngưỡng dừng `3` lần liên tiếp.

---

## §10. Chi phí Thời lượng (`OVER_MAX_DURATION_SEC`) & Lãng phí Rewrite

Ngoài cơ chế lặp, thực nghiệm bóc tách một nguồn lãng phí API độc lập trên cả 2 phiên chạy hết kịch bản:
- **`T2A W=5`:** `12` retries trên `48` calls (`wasted_calls = 25.0%`, `wasted_tokens = 38,562`) do `OVER_MAX_DURATION_SEC` / length budget mặc dù `detector` cho `ALLOW = 36/36`.
- **`T2B W=10`:** **`11 / 11` retries** trên `83` calls (`wasted_calls = 13.25%`, `wasted_tokens = 39,346`) **đều** đến từ `OVER_MAX_DURATION_SEC` (bản nháp dài `21–27` từ / `8.08s–10.38s` > `8.00s`), với `0` lần `RepetitionDetector` từ chối.
- Điều này cho thấy khi câu chuyện phức tạp hơn hoặc có các cảnh báo dài (như `tea-07`, `honey-08`, `honey-03`), LLM thường vượt nhẹ **ngưỡng từ khuyến nghị (`recommended_max_words = 18`, khung `12–18` từ)** hoặc chạm **giới hạn cứng `20` từ (`hard_max_words = 20` ứng với `20 / 2.6 = 7.692s <= 8.0s`)**, tạo thêm ~13–25% chi phí gọi model dù không có xung đột lặp.

---

## §11. Khoảng cách Độ chuẩn Xác giữa Deterministic Mock và Gemini Live

| Cặp so sánh | Mock Calls / Topics / Term | Live Calls / Topics / Term | Nguyên nhân Lệch Chính |
|---|---|---|---|
| T2A `W=5` | `42` / `18/18` / `EARLY_COMPLETION` | `48` / `18/18` / `EARLY_COMPLETION` | Live bị nhiều retry vượt trần `8.0s` hơn (`12` vs `6` rewrites). |
| T2A `W=10` | `52` / `18/18` / `EARLY_COMPLETION` | **`23` / `0/18` / `MAX_CONSECUTIVE_ABORTS`** | Mock thoát được ở lượt lẻ hoặc dùng `6` fallback phân tán; Live cạn `2` fallback ở `tr[6..7]` và chết ở `tr[10]`. |
| T2B `W=10` | `102` / `36/36` / `EARLY_COMPLETION` | **`83` / `36/36` / `EARLY_COMPLETION`** | Live ít vi phạm ngưỡng n-gram/duration cục bộ hơn mock (`11` vs `28` rewrites). |
| T2B `W=20` | `156` / `35/36` / `MAX_CONSECUTIVE_ABORTS` | **`28` / `0/36` / `MAX_CONSECUTIVE_ABORTS`** | Mock kịp lách qua Honey & Tea trước khi abort ở `macadamia-12`; Live bị khóa cứng ngay ở `SKU-HONEY-01` tại `tr[12..16]`. |

**Bài học phương pháp luận:** Nếu chỉ dựa vào `unit_test_mock` ở T2A (`18/18`) và T2B (`35/36`), nhóm kỹ sư có thể lầm tưởng `W > lag` vẫn vận hành gần như bình thường. Chỉ khi chạy **Gemini Live** mới thấy sự sụp đổ xảy ra **ngay tại SKU đầu tiên** (`0%` hoàn tất).

---

## §12. Hạch toán Token & Đặc tính Độ trễ Provider

- Hai phiên chạy hoàn tất cho dữ liệu hạch toán chính xác (`aggregate_token_usage_source = MEASURED`):
  - **T2A `W=5`:** `144,321` input + `6,084` output = **`150,405` tokens** (`38,562` wasted, ~`3,133` total tokens/call).
  - **T2B `W=10`:** `281,423` input + `9,919` output = **`291,342` tokens** (`39,346` wasted, ~`3,510` total tokens/call). *Lưu ý:* do T2A và T2B khác đồng thời scenario, dataset (`product_education_10m_ext` vs `window_stress_12lag_3sku`) và độ dài phiên, **không** quy toàn bộ chênh lệch token/call (`~3,007 → ~3,391` input tokens/call) cho riêng tham số `W`.
- Hai phiên `MAX_CONSECUTIVE_ABORTS` mang nhãn `UNAVAILABLE` ở tổng hợp vì đúng 1 lỗi `HTTP 503` mỗi phiên (`T2A W=10 [c19]`, `T2B W=20 [c24]`), nhưng phần `measured` chiếm `22/23` và `27/28` calls (`67,354/2,758` và `89,237/3,185`). Tỷ lệ `wasted_tokens` trên phần đo được vọt lên **`75.3%`** (T2A `W=10`) và **`59.6%`** (T2B `W=20`).
- **Độ trễ provider (`provider_latency_p50_ms`):** Dao động hẹp quanh **`5,903ms – 6,017ms`** ở cả 4 phiên. **Quan trọng:** số đo này **có thể bao gồm độ trễ pacing phía client (`min_request_interval_sec = 6.0`)** hoặc chi phí vòng gọi HTTP tuần tự, do đó **không** được diễn giải là pure model inference latency.

---

## §13. Cổng An toàn Cấu trúc & Spot-Check Factual Xuyên Track

- Toàn bộ `4 / 4` runs đều đạt **`structural_hard_gates_status = PASS`** (`p05_rejection_count = 0`, `invalid_candidate_playback_count = 0`, `duplicate_completed_chunk_replay_count = 0`, `retry_budget_violations = 0`, `0` metadata leaks).
- **Spot-check nội dung an toàn trên T2A `W=5` & T2B `W=10`:** Các cảnh báo an toàn cốt lõi (*không dùng mật ong cho trẻ dưới 1 tuổi*, *không ăn gói hút ẩm / dị ứng hạt cây*, *tránh hãm trà 100°C / uống sát giờ ngủ*) đều được giữ lại qua cả 2 vòng lặp.
- **Điểm tồn đọng cần Human/Audit xác nhận ở bước đóng E01:** Ở các chủ đề `*-10` (hồ sơ OCOP giả lập), giống như đã thấy tại Batch 1A và Batch 1B, LLM thỉnh thoảng lược bỏ từ `"mô phỏng"` hoặc chèn `"an toàn thực phẩm tuyệt đối"` (`T2B W=10 honey-10` còn lặp nguyên văn câu này cả 2 lượt). Do chưa hoàn tất đánh giá mù & `GoldFactualLabel`, trạng thái **`overall_gate_status = NOT_EVALUATED`** phải giữ nguyên tuyệt đối.

---

## §14. Tổng hợp Liên Pha: Track 1 (Natural Storytelling) + Track 2 (Window Sensitivity)

| Chiều So Sánh | Track 1 — Batch 1A & 1B (`min_chunks=1`, `W=5`) | Track 2A & 2B (`min_chunks=2`, `W ∈ {5,10,20}`) |
|---|---|---|
| **Mục tiêu thực nghiệm** | `LangGraph W=5` vs `Script-first` trên `Product Edu` (`1A`) & `Brand Storytelling` (`1B`). | Độ nhạy `history_window` dưới áp lực lặp bắt buộc tại `lag=6` (`2A`) và `lag=12` (`2B`). |
| **Phủ chủ đề playback-confirmed** | `W=5`: **100%** bắt buộc & toàn kế hoạch trên cả `1A` và `1B`; `Script-first`: hụt chủ đề/dàn ý (`Findings A–D`). | Khi `W < lag` (`W=5 @ 6`, `W=10 @ 12`): **100%**. Khi `W > lag` (`W=10 @ 6`, `W=20 @ 12`): **0%** (`MAX_CONSECUTIVE_ABORTS`). |
| **Chất lượng & Factual (AI-assisted)** | `1B`: Quality mean `W=5 = 3.17` vs `Script-first = 2.50`; factual PASS **`1A`: `63/74`** (`1 FAIL, 10 UNSURE`; evidence `57/74`) và **`1B`: `31/36`** (`4 FAIL, 1 UNSURE`; evidence `27/36`). | Track 2 `human_eval/` giữ nguyên **`PENDING`**; đánh giá AI-assisted ChatGPT cho Track 2 (`130` played turns) ghi nhận `104/130` factual PASS (`11 FAIL, 15 UNSURE`), xác nhận các điểm rơi OCOP/đổi trả/an toàn ở `*-10`, `*-09`, `*-07`. |
| **Kết luận Kiến trúc P06-E01** | `LangGraph` vượt trội `Script-first` về độ phủ & kiểm soát luồng, nhưng **P05 deterministic + rule-based detector chưa đủ** để tự ngăn drift ngữ nghĩa nhỏ hoặc bài toán lặp chủ đích. | Cần tách bạch **"cửa sổ chống lặp nguyên văn/câu chữ"** với **"chính sách quản lý claim cho phép khi revisit chủ đề có chủ đích"**. |

---

## §15. Tổng hợp Nguyên nhân Gốc (Root Cause Synthesis)

1. **Nguyên nhân gốc của Deadlock (`W > lag`):** Sự kết hợp giữa `(a)` mỗi chủ đề trong plan chỉ có `1` `allowed_claim_id` và `(b)` rule cứng trong `RepetitionDetector` coi mọi lần xuất hiện lại của cùng claim trong `W` lượt là `REPEATED_FACTS:SWITCH_TOPIC` bất kể ngữ cảnh là tái thăm chủ đề có chủ đích (`min_chunks_per_topic >= 2`).
2. **Nguyên nhân gốc của Exact Replay (`W < lag`):** Khi `W < actual_lag`, `RepetitionDetector` không còn thấy phát biểu vòng 1, đẩy gánh nặng đa dạng hóa hoàn toàn về stochastic sampling của LLM (`temperature`) vốn thỉnh thoảng hội tụ về đúng một câu ngắn tối ưu trên những topic có ít dữ liệu đầu vào như `*-10`.
3. **Nguyên nhân tồn đọng P05 / Factual:** P05 kiểm tra cấu trúc, giá, đơn vị định danh chính và từ khóa cấm cơ bản tốt (`0` metadata leak), nhưng chưa bắt được khẳng định mạnh hóa (*"tuyệt đối"*) hay việc thiếu từ rào (*"mô phỏng"*) ở claim OCOP.

---

## §16. Hệ quả Thiết kế & Kiến trúc cho Giai đoạn Sau `P06-E01`

*(Chỉ là khuyến nghị nghiên cứu cho phase sau, **KHÔNG** chỉnh sửa code P06 trong phạm vi E01 hiện tại)*:
1. **Tách `lexical/exact window` khỏi `semantic/claim revisit policy`:** Khi `min_chunks_per_topic >= 2`, ở lượt 2 cần cho phép dùng lại `allowed_claim_id` **nếu** lượt 2 khai thác góc nhìn mới (`LEGITIMATE_CONTINUATION` hoặc `revisit_angle`) và không vượt ngưỡng n-gram/word Jaccard, thay vì ép `REPEATED_FACTS:SWITCH_TOPIC`.
2. **Mở rộng kho `EvidenceChunk` & `angle` cho các chủ đề thiết kế >= 2 lượt:** Để lượt 2 thực sự mang giá trị thông tin mới thay vì paraphrase cùng 1 mảnh chứng cứ.
3. **Nâng cấp P05 / Verifier (`E02`/`E03`):** Bổ sung kiểm tra qualifier bắt buộc (như nhãn *"mô phỏng"*, cấm từ cực đoan *"tuyệt đối"*, kiểm định alignment theo `evidence_id` cụ thể của từng turn).
4. **Cơ chế chống replay ngoài cửa sổ gọn nhẹ:** Lưu hash câu đã phát toàn phiên riêng cho bước kiểm tra **exact-match only** (O(1)), độc lập với `W` ngữ nghĩa.

---

## §17. Danh mục Các Ca Nghiên cứu `E04` Đã Ghi nhận (`Track 2A` + `Track 2B`)

| Mã Ca | Phiên | Bản chất Hành vi |
|---|---|---|
| `E04-CASE-2A-01` | T2A `W=10` | `idx=6..10`: `REPEATED_FACTS:SWITCH_TOPIC` + `turn-scoped excluded_topic_ids` + cạn `2` `PREAPPROVED_FALLBACK` → khóa cứng SKU đầu tiên (`MAX_CONSECUTIVE_ABORTS`, `0/18`). |
| `E04-CASE-2A-02` | T2A `W=10` | `idx=9 att=2`: Lỗi nhất thời **`HTTP 503 UNAVAILABLE` (`c19`)** giữa vòng rewrite bị gộp thành `SAFE_ABORT_NO_CANDIDATE` (#2/3) trong bộ đếm `consecutive_aborts`. |
| `E04-CASE-2A-03` | T2A `W=5` | `idx=27` (`macadamia-safety`): Bounded rewrite nén `21→18` từ cắt mất cụm *"tránh dùng nếu"*, làm tối nghĩa cảnh báo dị ứng hạt cây. |
| `E04-CASE-2A-04` | T2A `W=5` | `idx=5 vs 11` & `28 vs 34`: Outside-window verbatim replays ở `lag=6 > W=5` (`0` detector rejects, `windowed_ngram3` bật `~73.4×` `0.0028 → 0.2031`). |
| `E04-CASE-2B-01` | T2B `W=10` | Window blindness đối xứng ở `lag=12 > W=10`: `36/36` pass bao phủ nhưng `1` exact replay (`honey-10`), `32.39%` lexical rep, `windowed_ngram3` bật `~18.8×` (`0.0131 → 0.2455`). |
| `E04-CASE-2B-02` | T2B `W=20` | First-cycle `REPEATED_FACTS` deadlock (`tr[12..16]`): `11` `SWITCH_TOPIC`, cạn `2` fallback ở `tr[12..13]`, `3` aborts (`1` HTTP 503 `[c24]`) → `0/36` (`MAX_CONSECUTIVE_ABORTS`). |
| `E04-CASE-2B-03` | T2B `W=10` | Duration-gate retry tax độc lập với lặp (`11/11` retries đều là `OVER_MAX_DURATION_SEC`, `39,346` wasted tokens). |
| `E04-CASE-2B-04` | T2B `W=10` | Trôi nhãn `"hồ sơ mô phỏng"` / thêm `"tuyệt đối"` ở chủ đề OCOP `*-10` dù `p05_rejection_count = 0`. |

---

## §18. Đe dọa tới Tính Hợp lệ & Giới hạn Nghiên cứu (Threats to Validity)

1. **Giới hạn hạt giống (`seed = 42`):** Mỗi cấu hình trong Track 2 chỉ chạy `1` phiên live để bảo toàn quota Free Tier; kết luận định lượng ở mức đơn hạt giống cho từng cặp, bù lại sự đối xứng cấu trúc giữa Track 2A và Track 2B củng cố mạnh tính lặp lại cơ chế.
2. **Tác động của lỗi `HTTP 503` đơn lẻ trong 2 phiên fail:** Cả T2A `W=10` (`[c19]` ở `tr[9]`) và T2B `W=20` (`[c24]` ở `tr[15]`) đều có đúng `1` lỗi API `HTTP 503` ngay giữa chuỗi abort. Tuy nhiên log `graph_trace.jsonl` chứng minh **cơ chế cạn fallback và abort đầu tiên đã xảy ra TRƯỚC lỗi `HTTP 503`** (`tr[6..8]` ở T2A và `tr[12..14]` ở T2B) và lượt sau lỗi (`tr[10]` / `tr[16]`) cũng tự `REPEATED_FACTS:SWITCH_TOPIC` ở cả 3 lần thử.
3. **Đánh giá Factual/Human chưa khép kín cho Track 2:** Các bảng `human_eval/` của T2A và T2B đang `PENDING`, nên chưa thể công bố tỷ lệ `unsupported_claim_rate` hay `Human Blind Quality` cho Track 2.

---

## §19. Tình trạng Gói Đánh giá Mù (`human_eval/`) Toàn Track 2

| Đợt chạy | Thư mục `human_eval/` | `SAMPLE_001` (`METHOD_A`) | `SAMPLE_002` (`METHOD_B`) | `audit_rows` | `revisit_rows` | Leak Check | Trạng thái |
|---|---|---|---|---:|---:|---|---|
| Track 2A | [`track2a_small_window_lag6_s42/human_eval/`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/formal_benchmark_v1/track2a_small_window_lag6_s42/human_eval/) | `W=10` (`a2ecd346`) | `W=5` (`cba0dd8b`) | 62 (`44` played [`36+8`] + `18` gap) | 36 | `0` hits | **`PENDING`** |
| Track 2B | [`track2b_large_window_lag12_s42/human_eval/`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/formal_benchmark_v1/track2b_large_window_lag12_s42/human_eval/) | `W=20` (`c0cbfff5`) | `W=10` (`601e3e7a`) | 122 (`86 + 36` gap) | 72 | `0` hits | **`PENDING`** |

---

## §20. Kiểm kê Hiện vật & Tính Toàn vẹn SHA-256

- Toàn bộ `13/13` tệp khóa (`verified_skus` & `story_plans` cho `e01_formal_v1`, `e01_ext_v1`; `prompts/*.txt`; `configs/models/*.yaml`; `configs/experiments/*.yaml`) đều giữ nguyên SHA-256.
- Các thư mục benchmark đã chốt nguyên vẹn và tách biệt:
  - [`track1_product_edu_s42/`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/formal_benchmark_v1/track1_product_edu_s42/) (Batch 1A + `ai_assisted_eval/`)
  - [`track1_brand_storytelling_s42/`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/formal_benchmark_v1/track1_brand_storytelling_s42/) (Batch 1B + `ai_assisted_eval/`)
  - [`track2a_small_window_lag6_s42/`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/formal_benchmark_v1/track2a_small_window_lag6_s42/) (`71/240` req + `4` CSV + `7` tệp `human_eval/`)
  - [`track2b_large_window_lag12_s42/`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/formal_benchmark_v1/track2b_large_window_lag12_s42/) (`111/200` req + `4` CSV + `7` tệp `human_eval/`)

---

## §21. Các Quyết định Mở Cần Tech Lead Phê duyệt

1. **Phương thức đánh giá Track 2 (`T2A` + `T2B`):** Dùng `Human Blind Evaluation` trực tiếp trên 2 gói `human_eval/` (`36 + 72 = 108` revisit rows, `62 + 122 = 184` audit rows), hay tiếp tục thực hiện trước `AI-assisted Evaluation` (giữ riêng vào `ai_assisted_eval/` như Batch 1A/1B) rồi Tech Lead mới quyết định chốt `GoldFactualLabel`? *(Đã hoàn tất phương án AI-assisted ChatGPT và khóa quyết định `CHANGE` trong `docs/18-...`.)*
2. **Phạm vi đóng `P06-E01`:** Xác nhận dừng thu thập thêm mẫu live (không chạy Track 3 Extended 30m / seed 43) và chuyển thẳng sang pha Tổng hợp Kết luận Nghiên cứu Cuối cùng `P06-E01` sau bước đánh giá Track 2.

---

## §22. Kế hoạch Chuẩn bị Đóng `P06-E01` (Final E01 Preparation Plan)

Để kết thúc chính thức thực nghiệm `P06-E01` đúng chuẩn khoa học và không trộn lẫn nhãn mù/bán tự động:

1. **Bước 1 — Review & Phê duyệt Cổng Đánh giá Track 2:** Tech Lead rà soát [`15-...`](./15-e01-t09-track2a-live-report.md), [`16-...`](./16-e01-t09-track2b-live-report.md) và báo cáo tổng hợp `17-...` này; quyết định phương thức chấm cho `human_eval/` của T2A & T2B.
2. **Bước 2 — Nhập Kết quả Đánh giá Track 2 (Tách Provenance):**
   - Nếu chạy AI-assisted review (ví dụ ChatGPT theo `REVIEWER_GUIDE_*`): lưu riêng vào `track2a_small_window_lag6_s42/ai_assisted_eval/` và `track2b_large_window_lag12_s42/ai_assisted_eval/`, **tuyệt đối không** ghi đè `human_eval/` hay gán nhãn `GoldFactualLabel`.
   - Nếu/khi có Human Blind reviewer điền `human_eval/`: đối soát không làm méo nhãn gốc và chốt `GoldFactualLabel`.
3. **Bước 3 — Tổng hợp Kết luận Nghiên cứu `P06-E01` (`docs/18-...`):** Hợp nhất bằng chứng từ Pilot v1/v2, Batch 1A (`Product Edu`), Batch 1B (`Brand Storytelling`), Track 2A & Track 2B thành báo cáo kết luận cuối cùng của `P06-E01`, trả lời trọn vẹn bộ Research Questions ban đầu và bàn giao backlog sửa kiến trúc (`REPEATED_FACTS` revisit policy, `P05` OCOP/absolute qualifier checks, duration-gate efficiency) sang `P06-E02` / `P06-E03`.
4. **Ngoài phạm vi đóng `P06-E01`:** Không sửa mã nguồn `src/p06/`, `prompts/`, `data/`, không chạy lại các batch cũ đã khóa, không thực hiện Track 3 hay thay đổi cấu hình model trong bước chuẩn bị này.

---

## §23. Kiểm chứng Kỹ thuật & Tình trạng Kho Mã

- **Regression Suite (`pytest`):** `289 passed in 120.24s` (`0` failed, `0` skipped) qua `.venv\Scripts\python.exe -m pytest experiments/sales-intelligence/autonomous-storytelling/tests -q`.
- **Dependency Hygiene (`pip check`):** `No broken requirements found.`
- **Khóa Hiện vật (`SHA-256`):** Toàn bộ hiện vật khóa của Track 2A/2B (`e01_formal_v1`, `e01_ext_v1`, `p06_e01_formal_track2a/2b`, `gemini_3.5_flash_lite_free.yaml`, `prompts/*.txt`) khớp `Match=True`.
- **Kích thước & Cấu trúc `AGENTS.md`:** `22,410 bytes` (`< 24,000`), `NO_FRONTMATTER`.
- **Rà soát Độc lập (`hydrogen-scout`, `flash`):** Xác nhận tính toàn vẹn 7 tệp mù (`0` leak), `0` secret leak, phạm vi bất biến (`src/p06/`, `prompts/`, `data/`, `configs/`, `run_gemini_formal_batch.py`, Batch 1A/1B, Track 2A đều nguyên vẹn qua `git status --short`), và đã hiệu chỉnh toàn bộ sai khác đối soát (`8/11` `W=10` T2A, `fact_overlap_threshold = 0.80`, ánh xạ & `62` dòng `audit_rows` của Track 2A).

---

## §24. Đính chính Nghiên cứu Sau Rà soát Tech Lead (`Errata & ID Mapping`, `2026-11-27`)

Theo rà soát của Tech Lead khi đóng `P06-E01` (`E01-T09` Final Evaluation), `12` điểm sau trong bản `docs/17` ban đầu đã được đính chính công khai mà **không** sửa đổi raw artifacts hay reviewer labels:

| # | Điểm Đính chính | Nội dung Bản đầu → Nội dung Chuẩn Đã Sửa |
|---:|---|---|
| 1 | Diễn đạt nhân quả/định luật | Bỏ `"định luật chuyển pha"` / `"chứng minh"` tổng quát → mô tả theo quan sát thực nghiệm trong phạm vi `n=1` stress test. |
| 2 | So sánh `W=10` giữa 2A & 2B | Không nói `lag` là biến duy nhất thay đổi; nêu rõ 2A & 2B khác dataset, số topic (`18` vs `36`), nội dung & `lag` (`tests/` `Fixed-History` mới cô lập `lag`). |
| 3 | Batch 1A factual PASS (§14) | `56/60` → **`63/74`** (`63 PASS, 1 FAIL, 10 UNSURE`; `57/74` evidence PASS trên `74` played turns). |
| 4 | Track 2A audit rows (§21) | Thống nhất **`62`** dòng audit cho Track 2A (`62 + 122 = 184`), bỏ con số nhầm `58`. |
| 5 | Track 2A mandatory vs planned (§3/§5) | Track 2A có **`12` mandatory topics** và **`18` planned topics** (không phải `18` mandatory). |
| 6 | Mapping `E04-CASE-2A-01..04` | Giữ ID chuẩn theo `docs/15`: bản v1 của `docs/17` từng đánh số tạm `[2A-01: outside-win replay, 2A-02: REPEATED_FACTS, 2A-03: mock vs live, 2A-04: ngram jump]` → ánh xạ lại đúng ID gốc `docs/15`: `2A-01` (deadlock `excl_ids`), `2A-02` (`HTTP 503` in abort counter), `2A-03` (`macadamia-safety` rewrite drop), `2A-04` (outside-window verbatim replay). |
| 7 | Quota cycles (§4) | Cả T2A (`06:15–06:23 VN`) và T2B (`10:29–10:41 VN`) đều trước `15:00 VN 27/11/2026` → bỏ nhận định `"2 chu kỳ quota tách biệt"`. |
| 8 | Track 2B budget cap provenance | Ghi rõ YAML khóa là **`400`**, còn cap vận hành **`200`** được áp qua `budget_ledger.json` theo chỉ đạo người dùng (giữ YAML SHA-256). |
| 9 | Word budget (`18` vs `20`) | Ghi rõ `12–18` từ là **khuyến nghị**, còn **`20` từ** mới là **hard word limit** (`20/2.6 = 7.692s <= 8.0s`). |
| 10 | Provider latency (§12) | Nêu rõ `provider_latency_p50_ms` (`~5.9–6.0s`) có thể bao gồm client pacing (`6.0s`), không phải pure model inference latency. |
| 11 | Chênh lệch token/call (§12) | Bỏ quy toàn bộ chênh lệch `input_tokens/call` giữa T2A và T2B cho `W` vì dataset & scenario khác nhau. |
| 12 | `distinct_1/2/3` (§8) | Nêu rõ `distinct-n` phụ thuộc độ dài transcript (`36` vs `72` lượt), không kết luận `W` làm giảm lexical diversity. |
