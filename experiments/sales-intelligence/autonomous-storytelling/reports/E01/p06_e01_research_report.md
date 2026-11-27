# Báo cáo Nghiên cứu Cuối cùng `P06-E01`: Kể chuyện Bán hàng Tự động Không có Bình luận (`CHANGE`)

**Mã thí nghiệm:** `P06-E01` (*Autonomous Storytelling Without Comments*) · **Dự án:** HOSTRA AI — Module `P06`  
**Quyết định Nghiên cứu Cuối cùng:** **`CHANGE`** *(Phê duyệt bởi Tech Lead, 2026-11-27)*  
**Trạng thái Đánh giá Chính thức (`overall_gate_status`):** **`NOT_EVALUATED`** *(`Human Blind Evaluation`, `Human Calibration` & `GoldFactualLabel`: `PENDING`; **KHÔNG** tuyên bố `VALIDATED` hay sẵn sàng production)*  
**Mô hình & Dữ liệu Khóa:** `gemini-3.5-flash-lite` (`Free Tier`, `0.00 USD`, dữ liệu `SYNTHETIC` 100%)

---

## 1. Tóm tắt Học thuật (`Abstract`)

`P06-E01` nghiên cứu khả năng kể chuyện bán hàng tự động nhiều lượt không có bình luận người xem trên `3` SKU thực phẩm đóng gói mô phỏng trong môi trường cô lập của module `P06`. Qua `2` đợt Pilot (`40` API requests), `10` phiên Formal Benchmark (`317` Gemini API requests, `0.00 USD`, `0` HTTP 429, `8` HTTP 503) và đánh giá sơ bộ theo Rubric `v0.1` bằng **`AI-assisted non-blind evaluation — ChatGPT — Rubric v0.1`** (`240` lượt đã phát và `108` cơ hội lặp kế hoạch), kiến trúc đề xuất **`Structured Story Planner + LangGraph + Dynamic Verified Generation`** thể hiện ưu thế rõ rệt về độ phủ chủ đề xác nhận qua playback ACK trên hai kịch bản tự nhiên (`100%` so với `58.33%–75.00%` ở `Script-first`) với `0` vi phạm bất biến cấu trúc (`structural_hard_gates_status = PASS` `10/10` runs, `0` rò rỉ metadata). Tuy nhiên, đánh giá ngữ nghĩa chỉ ra `16` lỗi factual (`5` ở Track 1, `11` ở Track 2), tỷ lệ logic rewrite vượt trần `15%` do vượt ngưỡng độ dài câu (`8.0s` / `20` từ), hiện tượng lặp lại nguyên văn/lặp ý khi `W < actual_lag` hoặc bế tắc `REPEATED_FACTS` khi `W >= actual_lag` trong kịch bản lặp bắt buộc, và thời lượng mô phỏng tối đa `489.996s` vẫn chưa đạt mục tiêu `10–30` phút. Do đó, quyết định nghiên cứu được chốt là **`CHANGE`**: giữ nguyên trục kiến trúc cốt lõi với cấu hình mặc định tạm thời **`W=5`** cho Natural Storytelling, đóng phạm vi `P06-E01` rút gọn, bảo lưu giới hạn thiếu `Human Blind Evaluation` / `GoldFactualLabel`, và bàn giao trực tiếp sang **`P06-E04`** cùng `P06-E02`/`P06-E03`/`P05`.

---

## 2. Tóm tắt Điều hành (`Executive Summary`)

- **Phạm vi đóng:** Hoàn tất thu thập dữ liệu thực nghiệm theo phạm vi rút gọn đã phê duyệt (`Pilot v1/v2` + `Formal Batch 1A, 1B, Track 2A, Track 2B`); không mở rộng thêm `seed=43`, Track 3 (`30m`) hay chỉnh sửa mã nguồn `src/p06/` trong `E01`.
- **Chi phí & Tính toàn vẹn:** Tổng cộng **`317` formal Gemini API requests** (`94 + 41 + 71 + 111`) chạy trên Free Tier ở chi phí **`0.00 USD`**, `0` HTTP 429, `8` failed calls đều do lỗi API nhất thời `HTTP 503`, `0` rò rỉ API key hay metadata thô (`ev-`/`clm-`/`SKU-`). Toàn bộ `6` tệp CSV đánh giá Track 2 từ `E01_Track2_Final_Evaluation.zip` đã nhập và khớp `SHA-256` 100%, giữ nguyên vẹn toàn bộ `human_eval/` (`PENDING`).
- **Kết quả chính:**
  - **Natural Track (`1A` Product Edu, `1B` Brand Storytelling):** `LangGraph W=5` đạt `100%` (`12/12` mandatory topics, `18/18` planned topics), vượt `Script-first` (`58.33%` ở `1A`, `75.00%` ở `1B`). Nhưng trên AI-assisted Rubric `v0.1`, điểm trung bình chất lượng đạt `3.33` (`1A W=5`) và `3.17` (`1B W=5`) với `transition_quality = 2/5`, chưa vượt ngưỡng đề xuất `3.5/5`.
  - **Track 2 Window Sensitivity (`2A` `lag=6`, `2B` `lag=12`, `min_chunks=2`):** Quan sát hai chế độ đối lập dưới stress `1` claim/topic (`n=1`): `W < lag` (`2A W=5`, `2B W=10`) hoàn tất `100%` (`18/18` và `36/36`) nhưng để lọt `64.81%` (`35/54`) lượt phát lại lặp nguyên văn/gần nguyên văn hoặc lặp ý (`exact_normalized_text_replay` = `2` và `1`); `W > lag` (`2A W=10`, `2B W=20`) kích hoạt `REPEATED_FACTS:SWITCH_TOPIC` liên hoàn, cạn fallback và dừng cứng **`MAX_CONSECUTIVE_ABORTS` (`0%` hoàn tất `>= 2` chunks, `54 NO_OUTPUT`)**.
  - **An toàn ngữ nghĩa (AI-assisted):** Track 2 ghi nhận `104/130` (`80.00%`) Factual `PASS`, `11` (`8.46%`) `FAIL` (`5` mất phạm vi OCOP mô phỏng / dùng *tuyệt đối*, `4` mất điều kiện đổi trả, `2` biến dạng cảnh báo an toàn), `15` (`11.54%`) `UNSURE`, và `100/130` (`76.92%`) Evidence `PASS`.

---

## 3. Bài toán Nghiên cứu (`Research Problem`)

Khi livestream không có bình luận từ người xem trong các khoảng lặng kéo dài, hệ thống bán hàng tự động (`P06`) cần tự chủ duy trì câu chuyện giới thiệu `2–5` SKU thực phẩm đóng gói (`ACR-002`) sao cho: (i) bao phủ đủ các chủ đề bắt buộc trong `StoryPlan` được merchant phê duyệt (`D08`), (ii) bám chặt `ProductFact`, `EvidenceChunk` và điều kiện `OCOP: VERIFIED` / an toàn thực phẩm (`G4`, `R08`, `R16`, `R17`), (iii) tiến trình chỉ cập nhật khi có tín hiệu `PlaybackCompleted` ACK từ `P04` (`I-03`, `I-06`), và (iv) hạn chế lặp từ, lặp ý gây nhàm chán (`R05`) trong giới hạn chi phí/độ trễ của LLM (`R13`).

---

## 4. Mục tiêu & Câu hỏi Nghiên cứu Gốc (`Research Objectives & Questions`)

Báo cáo tuân thủ nguyên tắc **chỉ sử dụng bộ Câu hỏi Nghiên cứu (`RQ1–RQ5`) và Giả thuyết (`H1–H4`) đã đăng ký tại [`research/research_questions.md`](../../research/research_questions.md)**; các câu hỏi đào sâu của Track 2 (`EXP-W1..W4`) được phân loại rõ là **khảo sát mở rộng (exploratory findings)**:

- **`RQ1` (`P06-E01` — Trọng tâm của báo cáo này):** Trong kịch bản không có bình luận trên bộ 3 SKU, kiến trúc `Structured Story Planning + LangGraph` kết hợp bộ nhớ `Short-term Played History` (`W ∈ {5, 10, 20}`) và phát hiện lặp rule-based có đạt `Mandatory Topic Coverage` cao hơn, mạch kể tự nhiên hơn và ít lặp hơn `Script-first` mà không vi phạm hard gate (`Unsupported Claim Rate = 0`) hay không? (**Giả thuyết `H1`**).
- **`RQ5` (Cross-cutting — Kiểm chứng một phần trong `E01`):** Kích thước cửa sổ `W ∈ {5, 10, 20}` và ngân sách viết lại (`K=2`) tạo ra sự đánh đổi như thế nào giữa chống lặp, tỷ lệ viết lại/dừng an toàn, độ trễ và token? *(Lưu ý: Biến `Optional Semantic Memory / embeddings` chưa bật trong E01; `Recap Policy` `P06-OPEN-3` được hoãn hậu E01).*
- **`RQ2` (`P06-E03`), `RQ3` (`P06-E02`), `RQ4` (`P06-E04`):** Thuộc phạm vi các thí nghiệm tiếp theo, chưa chạy trong `P06-E01` (P06 chỉ trích xuất các ca lỗi thực nghiệm để bàn giao).

---

## 5. Kiến trúc Đề xuất (`Proposed Architecture`)

Kiến trúc PoC tại [`src/p06/`](../../src/p06/) tách bạch rạch ròi:
1. **`StoryPlanner` & `ArcSequencer` ([`planning/`](../../src/p06/planning/)):** Điều phối vòng lặp theo SKU (`SKU-HONEY-01 → SKU-TEA-02 → SKU-MACADAMIA-03`) và theo `StoryPlan` nhiều góc nhìn.
2. **Đồ thị LangGraph 8 nodes ([`agent/`](../../src/p06/agent/)):** Chọn chủ đề ưu tiên `mandatory`, sinh draft có cấu trúc (`StoryChunk`), kiểm tra vệ sinh ngôn từ (`spoken_text_hygiene`), đối chiếu lặp qua `RepetitionDetector`, xác minh tri thức qua `P05KnowledgeAdapter`, và vòng lặp **`bounded rewrite` (`<= K=2`)** hoặc rơi về **`PREAPPROVED_FALLBACK` (`<= 2`/SKU) / `SAFE_ABORT_NO_CANDIDATE`**.
3. **Bộ nhớ phiên (`memory/`):** `ShortTermPlayedHistory` (cắt theo `W` lượt gần nhất đã có ACK), `GlobalTopicCoverage` (chỉ tăng khi nhận `PlaybackCompleted` ACK chủ động, loại trừ fallback), và `RepetitionDetector` 3 tầng (`EXACT_REPLAY`, `LEXICAL_DUPLICATION` ở `word_jaccard >= 0.65` hoặc `ngram3_jaccard >= 0.45`, `REPEATED_FACTS` ở `fact_overlap_ratio >= 0.80`).
4. **Hạ tầng mô phỏng cô lập (`adapters/mocks/`, `simulation/`):** `VirtualClock` (`2.6` từ/giây, ngưỡng tối đa `8.0s/chunk`, khuyến nghị `12–18` từ, giới hạn cứng `20` từ = `7.692s`), `SimulatedPlaybackHarness`.

---

## 6. Phương pháp luận Thực nghiệm (`Experimental Methodology`)

Áp dụng chuẩn 3 tầng provider tách biệt (`DR-P06-004`):
- **Tier 1 (`MockLLMProvider`):** Kiểm chứng tất định luồng trạng thái (`289` tests), dry-run dung lượng/lag, kiểm tra `Fixed-History Detector Check` (`tests/unit/test_formal_benchmark_prep.py`) — không suy diễn chất lượng tiếng Việt.
- **Tier 2 (`OllamaLocalProvider`):** Hoãn theo `DR-P06` phê duyệt do giới hạn RAM/thực thi local.
- **Tier 3 (`GeminiAPIProvider` — Formal):** Chạy tuần tự qua [`run_gemini_formal_batch.py`](../../experiments/p06_e01_no_comments/run_gemini_formal_batch.py) với `gemini-3.5-flash-lite` Free Tier (`temperature=0.3`, `top_p=0.9`, `max_tokens=1024`, `thinking_level=MINIMAL`, `min_request_interval_sec=6.0`, `stop_on_rate_limit=true`, `budget_ledger.json` khóa trần cứng). Các biến `PlaybackCompleted` ACK và `P05KnowledgeAdapter` hoạt động theo hợp đồng mock `p06-mock-v0.1`.

---

## 7. Thiết kế Bộ Dữ liệu & Kịch bản (`Dataset & Scenario Design`)

Toàn bộ dữ liệu mang nhãn `is_synthetic = true`, đóng gói thành 2 phiên bản khóa SHA-256 (`reports/E01/e01_artifact_index.json`):
- **`e01_ext_v1` (`v1.0.1 / v1.0.2`):** `3` SKU (`Mật ong 500ml 159k`, `Trà Shan Tuyết 200g 245k`, `Mắc ca 500g 195k`), `30` `EvidenceChunk` (`10`/SKU), `21` `ClaimRegistryEntry`. Dùng cho `product_education_10m_ext` (`18` planned topics = `12` mandatory + `6` non-mandatory; `lag=6` khi `m=2`) và `brand_storytelling_10m_ext` (`18` planned topics = `12` mandatory + `6` non-mandatory). *Lưu ý:* Kịch bản này không có topic OCOP.
- **`e01_formal_v1` (`v1.1.1`):** Mở rộng lên `36` `EvidenceChunk` (`12`/SKU) và `24` claims (gồm hồ sơ OCOP mô phỏng `SYNTH-OCOP-4S-*` ở `*-10`), phục vụ `window_stress_12lag_3sku` (`36` mandatory topics = `12`/SKU, `planned_lag = 12` khi `m=2`, mỗi chủ đề gắn đúng `1` `allowed_claim_id`).

---

## 8. Các Phương pháp Đối chiếu (`Baseline Methods`)

1. **`script_first_upfront_llm` (`baseline-script-first-v0.2.2`):** Sinh toàn bộ kịch bản đầu phiên từ prompt đồng bộ chung ngưỡng từ (`12–18` khuyến nghị, trần cứng `20` từ), `max_retries = 0`, không đọc `played_history` (`history_window = None`). Khi câu vượt `8.0s` hoặc rớt P05, lượt đó không tự sửa mà dùng `PREAPPROVED_FALLBACK` (`<= 2`/SKU) hoặc `SAFE_ABORT_NO_CANDIDATE`.
2. **`langgraph_structured_story` (`W ∈ {5, 10, 20}`):** Sinh động từng chunk có kiểm soát bộ nhớ `W` lượt gần nhất và vòng `bounded rewrite` tối đa `K=2` lần/turn (prompt `story_planner.txt v0.1`, `story_generation.txt v0.2.1`, `rewrite.txt v0.2.1`).

---

## 9. Khung Đánh giá (`Evaluation Framework`)

Kết hợp 5 trục metric tự động (`coverage`, `repetition`, `safety`, `reliability`, `performance` trong `metrics.json` & `comparison.json`) với phiếu đánh giá theo [`human_eval_rubric_v0.1.md`](../../evaluation/rubrics/human_eval_rubric_v0.1.md) (`6` tiêu chí `1–5` + Hard-Constraint Non-Compensation + Semantic Alignment `FULL/PARTIAL/MISS` + Factual `PASS/FAIL/UNSURE` + Evidence `PASS/FAIL` + Revisit Semantic Repetition). **Phân tách bắt buộc:** AI-assisted non-blind (ChatGPT) dùng cho đánh giá sơ bộ và lưu ở `ai_assisted_eval/`; `human_eval/` và `GoldFactualLabel` giữ trạng thái `PENDING`.

---

## 10. Kết quả Pilot & Sửa lỗi (`Pilot Findings & Remediation`)

- **Pilot v1 (`25` requests):** `Stage A` phát hiện và `Stage B` (`16` calls LangGraph + `6` calls Script-first) bộc lộ lỗi rò rỉ `ev-...` ra lời nói tự nhiên và tỷ lệ rewrite cao (`0.444`) do prompt nén câu chưa đồng bộ.
- **Pilot Remediation (`R01–R06`):** Bổ sung guard `spoken_text_hygiene`, khóa trích dẫn bằng chứng, fallback không lặp, `compute_chunk_word_budget()` (`18` khuyến nghị / `20` cứng), và sửa `coverage.py` cho `min_chunks_per_topic >= 2`.
- **Pilot v2 (`15` requests, `0` HTTP 503):** LangGraph `W=5` đạt `6/6` (`1.0`) topic & claim coverage với **`0` rewrite, `0` wasted calls, `0` leaks** (`exact_text = 0`), mở đường cho Formal Benchmark (`docs/E01/10`, `docs/E01/11`).

---

## 11. Kết quả Formal Natural Benchmark (`Batch 1A` & `Batch 1B`)

Số liệu chi tiết nằm tại [`02_natural_benchmark_comparison.csv`](../tables/E01/02_natural_benchmark_comparison.csv), [`03_cross_scenario_comparison.csv`](../tables/E01/03_cross_scenario_comparison.csv) và [`fig01_natural_mandatory_coverage.png`](../figures/E01/fig01_natural_mandatory_coverage.png):

| Batch & Kịch bản | Cấu hình | Calls (`503`) | Kết thúc | Mandatory (`%/12`) | Planned (`%/18`) | Claim Cov | Lex Rep | Logic Rewrite (`%`) | Duration (`s`) |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| `1A` Product Edu | `Script-first` | `18` (`0`) | `CONTENT_EXHAUSTED` | `58.3%` (`7/12`) | `55.6%` (`10/18`) | `57.1%` | `0.0%` | `0.0%` | `105.385s` |
| `1A` Product Edu | `LangGraph W=5` | `22` (`0`) | `EARLY_COMPLETION` | **`100.0%`** | **`100.0%`** | `100.0%` | `0.0%` | `22.2%` | `124.231s` |
| `1A` Product Edu | `LangGraph W=10` | `27` (`3`) | `EARLY_COMPLETION` | **`100.0%`** | **`100.0%`** | `100.0%` | `0.0%` | `19.1%` | `145.000s` |
| `1A` Product Edu | `LangGraph W=20` | `27` (`1`) | `EARLY_COMPLETION` | **`100.0%`** | **`100.0%`** | `100.0%` | `0.0%` | `25.0%` | `134.615s` |
| `1B` Brand Story | `Script-first` | `18` (`1`) | `CONTENT_EXHAUSTED` | `75.0%` (`9/12`) | `66.7%` (`12/18`) | `66.7%` | `0.0%` | `0.0%` | `118.077s` |
| `1B` Brand Story | `LangGraph W=5` | `23` (`1`) | `EARLY_COMPLETION` | **`100.0%`** | **`100.0%`** | `100.0%` | `0.0%` | `21.1%` | `124.229s` |

Trên cả 2 kịch bản tự nhiên (`m=1`), LangGraph đạt độ phủ tuyệt đối `100%` và `0` exact/lexical replay (bởi mọi chủ đề chỉ nói 1 lượt). Đối chiếu ghép cặp xuyên kịch bản (`Script-first` vs `W=5`) khẳng định cơ chế bounded rewrite là nguyên nhân trực tiếp giúp LangGraph phục hồi các nháp quá `20` từ mà `Script-first` bị đánh rớt.

---

## 12. Phân tích Độ nhạy Cửa sổ Lịch sử (`Track 2A` & `Track 2B`)

Chi tiết tại [`04_track2_comparison.csv`](../tables/E01/04_track2_comparison.csv), [`05_mock_vs_live_comparison.csv`](../tables/E01/05_mock_vs_live_comparison.csv), [`fig04`](../figures/E01/fig04_window_completion_vs_repetition_tradeoff.png) và [`fig05`](../figures/E01/fig05_actual_lag_and_window_membership.png):

- **Track 2A (`lag=6`, `18` planned / `12` mandatory topics, `71/240` cap):**
  - `W=5` (`48` calls, `EARLY_COMPLETION`): hoàn tất `18/18` (`100%`), `actual_lag = {6: 18}` (100% ngoài `W=5`), `0` detector rejects, lọt **`2` outside-window exact text replays** (`28.57%` lexical rep), `win_ngram3` bật `~73.4×` (`0.0028 → 0.2031`).
  - `W=10` (`23` calls, `1` `HTTP 503` `[c19]`, `MAX_CONSECUTIVE_ABORTS`): dừng ngay chu kỳ 2 của `SKU-HONEY-01` (`0/18` đạt `>= 2` chunks, `8` turns đã phát), `8` `REPEATED_FACTS:SWITCH_TOPIC` + `6` `LEXICAL_DUP:REWRITE` (`actual_lag` attempts `{5:3, 6:2, 7:6, 8:3}` đều `<= 10`), `73.91%` wasted calls.
- **Track 2B (`lag=12`, `36` planned & mandatory topics, `111/200` operational cap vs `400` YAML cap):**
  - `W=10` (`83` calls, `EARLY_COMPLETION`): hoàn tất `36/36` (`100%`), `actual_lag = {12: 36}` (100% ngoài `W=10`), `0` detector rejects (`11/11` retries do `OVER_MAX_DURATION_SEC`), lọt **`1` outside-window exact replay** (`honey-10`), `32.39%` lexical rep, `win_ngram3` bật `~18.8×` (`0.0131 → 0.2455`).
  - `W=20` (`28` calls, `1` `HTTP 503` `[c24]`, `MAX_CONSECUTIVE_ABORTS`): dừng tại `tr[12..16]` (`0/36` đạt `>= 2` chunks, `14` turns đã phát), `11` `REPEATED_FACTS:SWITCH_TOPIC` (`actual_lag` attempts `{11..14}` đều `<= 20`), `57.14%` wasted calls.
- **Diễn giải thận trọng:** Hai lần chạy `W=10` (`2A` sụp `0/18` vs `2B` đạt `36/36`) khác nhau đồng thời về dataset, số chủ đề và `lag` (`n=1` mỗi config). Do đó đây là bằng chứng thực nghiệm có điều kiện về sự tương tác giữa `(W, lag, 1-claim/topic)` chứ **không** phát biểu thành định luật tổng quát tách riêng biến `lag`.

---

## 13. Kết quả Đánh giá Cuối cùng AI-Assisted (`ChatGPT — Rubric v0.1`)

Toàn bộ kết quả tổng hợp trực tiếp từ CSV tại [`06_ai_assisted_quality_scores.csv`](../tables/E01/06_ai_assisted_quality_scores.csv), [`07_semantic_coverage.csv`](../tables/E01/07_semantic_coverage.csv), [`08_factual_and_evidence_assessment.csv`](../tables/E01/08_factual_and_evidence_assessment.csv), [`09_revisit_repetition_distribution.csv`](../tables/E01/09_revisit_repetition_distribution.csv) và [`fig03`](../figures/E01/fig03_ai_assisted_storytelling_quality.png), [`fig06`](../figures/E01/fig06_semantic_repetition_distribution.png), [`fig07`](../figures/E01/fig07_factual_and_evidence_assessment.png):

- **Chất lượng Kể chuyện (`Quality Mean`, thang `1–5`):** `1A W=5` dẫn đầu đạt **`3.33`** (`W=20`: `3.17`, `W=10`: `2.83`, `Script-first`: `2.33`); `1B W=5` đạt **`3.17`** (`Script-first`: `2.50`); Track 2 giảm xuống `2.50` (`2A W=5`), `2.17` (`2A W=10`), `2.33` (`2B W=10` & `W=20`). Tiêu chí `Transition Quality` đứng ở `2/5` trên toàn bộ `10/10` mẫu, và `Repetition Quality` rớt xuống `1/5` ở `2A W=5` và `2B W=10`.
- **Semantic Coverage (Tách đơn vị đo):**
  - *Track 1 (`topic-level`, `18` planned topics):* `1A W=5` đạt `7 FULL / 11 PARTIAL / 0 MISS` (`Script-first`: `4/6/8`); `1B W=5` đạt `12 FULL / 6 PARTIAL / 0 MISS` (`Script-first`: `7/5/6`).
  - *Track 2 (`required-slot`, `36` hoặc `72` slots):* `2A W=5` đạt `9 FULL / 27 PARTIAL / 0 MISS` (`3/18` topics `BOTH_FULL`); `2A W=10` `1/5/30` (`0/18`); `2B W=10` `59/13/0` (`28/36` `BOTH_FULL`); `2B W=20` `8/4/60` (`0/36`). `54` missing rows ở `2A W=10` (`18`) + `2B W=20` (`36`) tương ứng **`90` missing required slots**.
- **Factual & Evidence trên `played_turns`:**
  - *Track 1 (`110` played turns):* Factual `94 PASS` (`85.45%`), `5 FAIL`, `11 UNSURE`; Evidence `84 PASS` (`76.36%`). *(Trong đó `1A`: **`63/74` PASS**, `1` FAIL, `10` UNSURE; `1B`: `31/36` PASS, `4` FAIL, `1` UNSURE).*
  - *Track 2 (`130` played turns):* Factual **`104 PASS` (`80.00%`), `11 FAIL` (`8.46%`), `15 UNSURE` (`11.54%`)**; Evidence **`100 PASS` (`76.92%`, `30 FAIL`)**; Metadata leakage **`0/130`**.
- **Semantic Repetition Track 2 (`108` planned revisits):** `54 NO_OUTPUT` (ở `2A W=10` & `2B W=20` — **không** phải chống lặp thành công) và `54` phát thực sự (`19 EXACT_REPETITION` [gồm `3` cặp trùng nguyên văn + `16` cặp gần nguyên văn], `16 UNWANTED_SEMANTIC_REPETITION`, `13 LEGITIMATE_CONTINUATION` [`24.07%`], `5 DELIBERATE_RECURRENCE`, `1 UNSURE`). Như vậy **`35/54` (`64.81%`)** lặp nguyên văn/gần nguyên văn hoặc lặp ý không bổ sung giá trị.

---

## 14. Phân tích Tổng hợp Xuyên Thí nghiệm (`Cross-Experiment Analysis`)

Tổng hợp xuyên `4` formal batches (`10` runs, `317` requests) chỉ ra tính nhất quán hành vi của hệ thống ở ba khía cạnh:
1. **Structural Playback Coverage vs Semantic Completeness:** Trong mọi kịch bản hợp lệ khi `W` không xung đột `lag` (Track 1 mọi `W`, Track 2 khi `W < lag`), LangGraph luôn đạt `100%` `mandatory_topic_coverage`. Nhưng do ràng buộc nén `<= 20` từ (`8.0s`), một phần đáng kể lượt nói rơi vào `PARTIAL` (`11/18` ở `1A W=5`, `27/36` slots ở `2A W=5`) hoặc cắt mất điều kiện phụ.
2. **Sự phân kỳ Mock vs Live:** `MockLLMProvider` che giấu cả vấn đề vượt trần `20` từ của Gemini thật (dẫn tới logic rewrite `19%–25%` ở Track 1) lẫn cú sụp `MAX_CONSECUTIVE_ABORTS` ngay chu kỳ đầu ở Track 2 (`Mock` qua `18/18` ở `2A W=10` và `35/36` ở `2B W=20`, còn Live dừng ở `0/18` và `0/36`).
3. **Thứ bậc `Natural` vs `Stress`:** Kết quả thất bại ở Track 2 (`W=10` ở `2A`, `W=20` ở `2B`) xuất phát từ thiết kế bài toán stress `m=2` với `1` claim/topic, **không** phủ nhận hiệu quả điều phối cơ bản của LangGraph trên Natural Track (`m=1`).

---

## 15. An toàn, Căn cứ Bằng chứng & Kiểm soát Rò rỉ (`Safety & Grounding`)

- **Thành tựu từ Pilot Remediation:** Toàn bộ `10/10` runs đạt **`structural_hard_gates_status = PASS`** và `0 / 240` played turns bị rò rỉ metadata kỹ thuật (`ev-`, `clm-`, `SKU-`, JSON).
- **Lỗ hổng Ngữ nghĩa còn Tồn tại (`P05 ALLOW != Semantic Safety PASS`):** Đánh giá AI-assisted phát hiện `11` ca Factual `FAIL` ở Track 2 (và `5` ca ở Track 1) lọt qua cổng P05 hiện tại:
  - **`5` ca OCOP & an toàn tuyệt đối (`2B` `*-10`):** Bỏ chữ *"hồ sơ mô phỏng"* hoặc khẳng định *"an toàn thực phẩm tuyệt đối"* vượt quá bằng chứng (`2B S1 t9`, `S2 t9`, `S2 t21`, `S2 t33`, `S2 t69`).
  - **`4` ca thiếu điều kiện đổi trả (`2B` `*-09`):** Thiếu cụm điều kiện bắt buộc *"khi nhận hàng"* hoặc *"khi mở hộp"* dù đã có `v0.2.1` (`2B S1 t8`, `S2 t8`, `S2 t20`, `S2 t68`).
  - **`2` ca biến dạng / thiếu cảnh báo an toàn:** `2A S2 t25` (`macadamia-safety` cắt mất cụm *"tránh dùng nếu"* khi rewrite `21→18` từ) và `2B S2 t42` (`tea-07` lượt 2 nhắc người nhạy cảm caffeine nhưng bỏ chỉ dẫn *"tránh uống lúc đói / sát giờ ngủ"*).
- **Evidence Support:** Khoảng `23%` số lượt phát (`26/110` Track 1, `30/130` Track 2) chứa chi tiết hợp catalog nhưng không nằm đủ trong chính danh sách `cited_evidence_ids` được gán cho lượt đó.

---

## 16. Độ tin cậy & Hiệu quả Tài nguyên (`Reliability & Resource Efficiency`)

Xem [`10_budget_and_reliability.csv`](../tables/E01/10_budget_and_reliability.csv) và [`fig08`](../figures/E01/fig08_reliability_waste_and_duration.png):
- **Tài nguyên API & Chi phí:** Tổng **`317` formal requests** (`0 USD`, `0` `HTTP 429`). `8 / 317` (`2.52%`) lỗi đều là `HTTP 503 UNAVAILABLE` đơn lẻ từ provider. Do có `HTTP 503`, `6/10` runs đánh dấu `token_usage_source = UNAVAILABLE` ở tổng hợp (`4/10` runs đạt `MEASURED`: `1A Script-first` `42,170`, `1A W=5` `67,856`, `2A W=5` `150,405`, `2B W=10` `291,342` total tokens). Phần `partial_measured` được ghi nhận minh bạch mà không điền `0` giả.
- **Thuế Rewrite do Độ dài (`OVER_MAX_DURATION_SEC`):** Trên 4 runs LangGraph hoàn tất toàn kịch bản không bị kẹt fact (`1A` `W=5/10/20`, `1B W=5`, `2A W=5`, `2B W=10`), chi phí lãng phí thuần logic dao động từ **`13.25%`** (`11/83` ở `2B W=10`, 100% do `OVER_MAX_DURATION_SEC` `21–27` từ) đến **`29.63%`** (`1A W=20`), vượt ngưỡng mục tiêu `<= 10%`.
- **Lưu ý Độ trễ:** `provider_latency_p50_ms` (`5,903ms–6,017ms` ở Track 2; `~5.94s–6.00s` ở Track 1) bao gồm cơ chế client pacing `min_request_interval_sec = 6.0` và chi phí vòng HTTP tuần tự, không thể coi là inference latency thuần túy của Gemini.

---

## 17. Mức độ Đáp ứng Thời lượng (`Duration Fulfillment`)

Phiên dài nhất là **`2B LangGraph W=10`** (`72` lượt phát trên `36` chủ đề × `2` vòng), đạt **`489.996s`** (`81.67%` so với mốc `600s`), trong đó vòng lặp lại chứa tỷ lệ cao câu lặp nguyên văn/lặp ý (`26/36` revisits). Các phiên Natural (`18` chủ đề) đạt **`105.385s–145.000s`** (`17.6%–24.2%` của `600s`). Hơn nữa, `VirtualClock` (`words / 2.6`) là bộ đếm proxy chữ viết, chưa đo trên chữ số tiếng Việt đọc thành lời qua TTS (`P02`). **Kết luận trung thực: Mục tiêu kể chuyện liên tục `10–30` phút chưa được chứng minh (`FAIL`).**

---

## 18. Đánh giá Acceptance Criteria Cuối cùng (`14` Tiêu chí)

Đối soát trực tiếp [`11_acceptance_criteria_assessment.csv`](../tables/E01/11_acceptance_criteria_assessment.csv) giữ nguyên toàn bộ ngưỡng khóa trước benchmark:

| # | Tiêu chí | Ngưỡng Khóa | Trạng thái | Tóm tắt Bằng chứng |
|---:|---|---| :---: |---|
| 1 | Structural invariants (`G3/G4` structural) | `0` vi phạm | **`PASS`** | `10/10` runs `PASS`, `0` chunk replay, `0` P05 reject, `0` retry viol |
| 2 | Natural Track mandatory coverage | LangGraph `>= 95%` | **`PASS`** | LangGraph `4/4` runs = **`100%`** (`Script-first` = `58.3%` & `75.0%`) |
| 3 | Semantic `FULL / MISS` | `>= 85% FULL`, `<= 5% MISS` | **`NOT_EVALUATED`** | Gold `PENDING`; AI-assisted sơ bộ: `1A W=5` `38.9% FULL`, `1B W=5` `66.7% FULL` |
| 4 | Lexical repetition (Natural) | `<= 5%` (`m=1`) | **`PASS`** | Track 1 = `0.0%` (`6/6` runs); Track 2 Stress = `28.57%` & `32.39%` |
| 5 | Exact normalized replay (Natural) | `= 0` (`m=1`) | **`PASS`** | Track 1 = `0` (`6/6` runs); Track 2 ngoài `W` = `2` (`2A`) & `1` (`2B`) |
| 6 | Logic rewrite rate (Natural) | `<= 15%` | **`FAIL`** | `1A`: `22.2%`, `19.1%`, `25.0%`; `1B`: `21.1%` (chính do `> 8.0s`) |
| 7 | Logic fallback rate (Natural) | `<= 5%` | **`PASS`** | Gần `0%` logic trên Natural (chỉ phát sinh quanh HTTP 503 / `1` ca `1A W=20`) |
| 8 | Logic wasted calls (Natural) | `<= 10%` | **`FAIL`** | `1A`: `18.2%`, `22.2%`, `29.6%`; `1B`: `17.4%` (`OVER_MAX_DURATION_SEC`) |
| 9 | Factual correctness (Hard Gate) | `0` sai lệch (Gold) | **`NOT_EVALUATED`** | Gold `PENDING`; AI-assisted: **`5 FAIL`** (Track 1) + **`11 FAIL`** (Track 2) + `UNSURE` |
| 10 | Evidence support | `0` thiếu evidence | **`NOT_EVALUATED`** | Gold `PENDING`; AI-assisted: `76.4%` Track 1, `76.9%` Track 2 PASS |
| 11 | Metadata leakage | `= 0` | **`PASS`** | `0 / 240` played turns (`110` Track 1 + `130` Track 2) |
| 12 | Quality rubric (`1–5`) | Mean `>= 3.5`, min `>= 3.0` | **`NOT_EVALUATED`** | Human Blind `PENDING`; AI-assisted max `3.33` (`1A W=5`), `transition=2.0` |
| 13 | Duration fulfillment (`10–30m`) | `600s–1800s` | **`FAIL`** | Max `489.996s` (`2B W=10` có lặp); Natural `105–145s`; `VirtualClock != TTS` |
| 14 | Human Blind & Calibration | Hoàn tất & đồng thuận | **`NOT_EVALUATED`** | Giữ nguyên `PENDING` theo phê duyệt đóng E01 rút gọn (`CHANGE`) |

---

## 19. Phân tích Nguyên nhân Gốc (`Root Cause Analysis`)

1. **Xung đột Chính sách Tái thăm (`Revisit Policy Conflict`):** Khi `1` chủ đề chỉ có `1` `allowed_claim_id` nhưng kịch bản đòi hỏi `min_chunks_per_topic = 2`, quy tắc `fact_overlap_threshold >= 0.80 → REPEATED_FACTS:SWITCH_TOPIC` chặn mọi nỗ lực sinh lượt 2 nếu lượt 1 còn nằm trong `W`. Kết hợp với `excluded_topic_ids` chỉ tồn tại trong phạm vi 1 lượt (`turn-scoped`) và quỹ `2` fallback/SKU, hệ thống tự đẩy vào `MAX_CONSECUTIVE_ABORTS`.
2. **Đứt gãy Ngữ nghĩa khi Bounded Rewrite Cắt Giảm Từ:** Prompt yêu cầu đồng thời giữ hết ý talking points, đơn vị, điều kiện đổi trả, cảnh báo an toàn và giới hạn `12–18` từ (`<= 20` từ). Khi bị `OVER_MAX_DURATION_SEC`, LLM cắt đúng phần điều kiện (*"khi mở hộp"*, *"hồ sơ mô phỏng"*, *"tránh dùng nếu"*) để cứu độ dài mà bộ kiểm tra deterministic của P05 không phát hiện được.
3. **Khoảng cách Mock vs Live:** Fixture `mock_fixtures.py` bỏ trống `covered_claim_ids` ở lượt tái thăm chính (`attempt=0`), che khuất xung đột `REPEATED_FACTS` vốn kích hoạt ngay ở `attempt=0` trên Gemini thật.

---

## 20. Đe dọa tới Tính Hợp lệ (`Threats to Validity`)

- **`Human Blind Evaluation`, `Human Calibration`, `GoldFactualLabel = PENDING`:** Rà soát ngữ nghĩa dựa hoàn toàn vào `AI-assisted non-blind (ChatGPT)` — mang tính bảo thủ sơ bộ, không có thẩm quyền phê chuẩn sản xuất.
- **Số lần lặp (`n = 1` mỗi cấu hình):** Không đủ cơ sở kiểm định ý nghĩa thống kê hay vẽ error bars.
- **Nhân tố nhiễu chéo Track:** Không thể coi `Track 2A W=10` vs `Track 2B W=10` là thí nghiệm đơn biến theo `lag` do khác đồng thời dataset, nội dung và số lượng topic.
- **Lỗi `HTTP 503` hạ tầng (`8/317` calls):** Làm `6/10` runs chuyển `token_usage_source = UNAVAILABLE` và cộng thêm nhịp abort vào chuỗi `MAX_CONSECUTIVE_ABORTS` đang xảy ra sẵn.
- **Biên giới mô phỏng:** Toàn bộ `P05` gate, `P04` playback ACK (`VirtualClock`) và dữ liệu sản phẩm đều là mock/synthetic.

---

## 21. Kết luận Nghiên cứu & Chốt Tham số `History Window`

- **Khuyến nghị Tham số `History Window`:**
  - **`W = 5` — Provisional Default cho Natural Storytelling:** Đạt `100%` coverage ổn định trên `1A` và `1B`, tiêu thụ ít ngữ cảnh hơn, không cần fallback nội bộ khi không gặp HTTP 503 (`W` không phải tối ưu toàn cục và giữ nguyên cấu hình khóa hiện tại).
  - **`W = 10`** (`research comparison configuration`) và **`W = 20`** (`stress comparison configuration`).
- **Kiến trúc Memory Đề xuất cho Phase Sau *(CHƯA validated, KHÔNG triển khai trong E01)*:**
  1. `Session-level exact text hash memory`: chặn trùng nguyên văn O(1) toàn phiên độc lập với `W`.
  2. `Short-term context history`: giữ `W` lượt gần nhất cho mạch kể tự nhiên và chống lặp từ vựng cục bộ.
  3. `Claim / Topic / Angle progress memory`: theo dõi khía cạnh (`angle`) cho phép tái thăm chủ đề có thông tin mới thay vì chặn cứng bằng `fact_overlap`.

---

## 22. Khuyến nghị Cải tiến Kiến trúc (`Architecture Recommendations`)

1. Tách bài toán **chống lặp nguyên văn/câu chữ** khỏi **chính sách tái sử dụng claim theo góc nhìn mới** (`E02`).
2. Nâng cấp **P05 / Semantic Verifier** để bắt thiếu qualifier bắt buộc (*mô phỏng*, điều kiện đổi trả, cảnh báo sức khỏe/dị ứng, cấm từ *tuyệt đối*) và kiểm định từng `evidence_id` cụ thể.
3. Tách riêng **lỗi hạ tầng tạm thời (`HTTP 503`)** với **lỗi cạn ứng viên logic** trong bộ đếm `consecutive_aborts` (`E04`), đồng thời cho phép `excluded_topic_ids` hoặc trạng thái exhausted topic bảo lưu đúng phạm vi trước khi cạn vòng SKU.
4. Chuẩn hóa **ngân sách độ dài theo độ phức tạp topic** thay vì ép cứng cùng trần `20` từ cho các chủ đề chứa nhiều cảnh báo bắt buộc.

---

## 23. Bàn giao cho `P06-E04`, `E03`, `E02`, `P05` & Tích hợp `P02`

*(Toàn bộ danh mục dưới đây là phạm vi nghiên cứu tiếp theo, KHÔNG triển khai trước khi đóng E01)*:
- **`P06-E04` (Bounded Rewrite & Fail-Closed Recovery — Nhiệm vụ Tiếp theo):** Xử lý trực tiếp các ca lỗi thực nghiệm đã định danh gồm [`E04-CASE-1B-01..05`](../../docs/E01/13-e01-t09-formal-benchmark-batch1b-report.md), [`E04-CASE-2A-01..04`](../../docs/E01/15-e01-t09-track2a-live-report.md), [`E04-CASE-2B-01..04`](../../docs/E01/16-e01-t09-track2b-live-report.md) cùng `11` ca factual FAIL của Track 2 (mất qualifier khi rewrite, topic deadlock với `turn-scoped excluded_topic_ids`, cạn 2-slot fallback, và gộp `HTTP 503` vào `MAX_CONSECUTIVE_ABORTS`).
- **`P06-E03` (Interrupt & Resume):** Kiểm chứng ngắt mạch và khôi phục bám `PlaybackCompleted` ACK tại 10 điểm ngắt arc, bảo toàn topic progress và history không replay chunk đã phát (E01 chưa kiểm chứng interruption).
- **`P06-E02` (Repeated Questions & Controlled Paraphrase):** Xử lý `EXACT_REPLAY` ngoài cửa sổ `W`, phân biệt `UNWANTED_SEMANTIC_REPETITION` vs `LEGITIMATE_CONTINUATION` vs `DELIBERATE_RECURRENCE`, thiết kế `Session-level exact text hash` và chính sách novelty theo `angle`.
- **`P05` (Knowledge & Verification):** Bổ sung rule/verifier kiểm tra evidence completeness, scope OCOP mô phỏng, từ cực đoan, cảnh báo y tế/an toàn và điều kiện thương mại.
- **`P02` (TTS Integration):** Kiểm định `VirtualClock` (`words / 2.6`) so với audio duration thực tế của tiếng Việt chứa số liệu, đơn vị đo và tên riêng.

---

## 24. Hướng dẫn Tái lập & Sao lưu Hiện vật (`Reproducibility Instructions`)

- **Tái tạo toàn bộ bảng & biểu đồ ngoại tuyến (`0` API calls):**
  ```powershell
  .\.venv\Scripts\python.exe -c "import pathlib, sys; sys.path.insert(0, 'experiments/sales-intelligence/autonomous-storytelling/notebooks/E01'); import e01_analysis_utils as u; root = u.find_p06_root(); r = u.load_formal_runs_df(root); p = u.load_pilot_and_mock_inventory(root); e = u.load_ai_assisted_eval_dfs(root, r); m = u.load_track2_mock_vs_live_df(root); l = u.load_track2_lag_summary(root); tp = u.export_all_tables(root, r, p, e, m); u.generate_all_figures(root, r, e, l)"
  ```
- **Lưu ý `.gitignore` đối với `runs/`:** Thư mục `runs/*/*` nằm trong [`autonomous-storytelling/.gitignore`](../../.gitignore), nên toàn bộ 10 thư mục run thô và `ai_assisted_eval/` **không** nằm trong Git commit (chỉ có bảng tổng hợp, biểu đồ, `reports/E01/e01_artifact_index.json`, notebook và báo cáo được theo dõi bởi Git). Khi cần lưu trữ dài hạn, tạo bản sao lưu local của `runs/P06-E01/` **sau khi** chạy kiểm tra không chứa biến môi trường `.env` hay API keys; **tuyệt đối không** upload private artifacts lên dịch vụ bên ngoài hay sửa `.gitignore` để force-add `runs/`.

---

## 25. Quyết định Nghiên cứu Cuối cùng (`Final Research Decision`)

**Quyết định chính thức:** **`CHANGE`** — *Giữ hướng kiến trúc cốt lõi đã có bằng chứng ủng hộ (`Structured Story Planner + LangGraph + Dynamic Verified Generation + Playback-confirmed Progress`), nhưng cần sửa các cơ chế semantic preservation, rewrite/recovery và revisit policy trong `P06-E04`/`E02`/`P05` trước khi nghiệm thu MVP.*

| Trục Đánh giá | Trạng thái Cuối cùng |
|---|---|
| `Research execution — reduced scope` | **`COMPLETE`** |
| `AI-assisted evaluation` | **`COMPLETE`** *(non-blind ChatGPT — Rubric v0.1)* |
| `Human Blind Evaluation` | **`PENDING`** *(bảo lưu làm giới hạn nghiên cứu)* |
| `Human Calibration` | **`DEFERRED / PENDING`** |
| `Gold Factual Assessment` | **`PENDING`** |
| `Overall acceptance gate` | **`NOT_EVALUATED`** |
| `Research decision` | **`CHANGE`** |
| `Production validation` | **`NOT VALIDATED`** |
| `Additional E01 benchmark` | **`NOT REQUIRED under approved scope`** |

**Trạng thái Đóng `P06-E01`:** **`E01_RESEARCH_CLOSED_CHANGE — AWAITING_FINAL_GIT_CHECKPOINT`**
