# P06 — Câu hỏi nghiên cứu & Giả thuyết kiểm chứng (Research Questions & Hypotheses)

**Module:** P06 — Sales Intelligence & Autonomous Storytelling  
**Tài liệu đối chiếu:** Stage 03 (`P06.11`, `P06.13`), Stage 02 (`R05`, `R08`, `R13`), Rà soát Tech Lead (`2026-11-26`)  
**Trạng thái:** `IN RESEARCH` — Các câu hỏi và giả thuyết dưới đây được thiết lập để kiểm chứng quyết định `SELECTED FOR PoC`, **không phải** kết quả đã xác thực.

---

## 1. Các câu hỏi nghiên cứu cốt lõi (Core Research Questions)

### `RQ1` — Kể chuyện chủ động khi không có bình luận (`P06-E01`)
> **Câu hỏi:** Trong khoảng thời gian 10–30 phút không có bình luận người xem trên kịch bản 3 SKU, phương pháp `Structured Story Planning + LangGraph` kết hợp bộ nhớ `Short-term Played History` (`W ∈ {5, 10, 20}`) và phát hiện lặp **rule-based vs. tùy chọn embedding cosine similarity** có đạt được mức bao phủ chủ đề bắt buộc (`Mandatory Topic Coverage`) cao hơn, mạch kể tự nhiên (`Narrative Coherence`) tốt hơn và tỷ lệ lặp ngữ nghĩa (`Semantic Repetition Rate`) thấp hơn so với baseline `Script-first` hay không?

- **Phạm vi kiểm chứng:** So sánh đối đầu giữa Baseline (`Script-first`) và kiến trúc đề xuất (`Structured Story Planner + Dynamic Verified Generation` bằng LangGraph) trên cùng bộ 3 SKU thực phẩm đóng gói `OCOP: VERIFIED` và cùng cấu hình `EvidenceBundle`.
- **Ghi chú biến hoãn sau `E01`:** Chính sách **Recap Policy (`P06-OPEN-3`: Periodic Recap + Context-aware Question Response)** được ghi nhận là biến nghiên cứu **hậu `P06-E01`** (không gộp vào phép so sánh lõi của `E01` để cô lập chất lượng kể chuyện chủ động trước, sau đó kiểm chứng trong `P06-E03` / bước kế tiếp).
- **Rủi ro & Gate liên quan:** `R05`, `R13` · `G2`, `G6`.

### `RQ2` — Ngắt mạch & Khôi phục bám sát Playback ACK (`P06-E03`)
> **Câu hỏi:** Khi bình luận người xem xen ngang tại 10 vị trí khác nhau trong một story arc (đầu arc, giữa luận điểm, đang chuyển SKU, gần kết arc...), việc cập nhật `StoryCheckpoint` hoàn toàn từ tín hiệu `PlaybackCompleted` ACK (thay vì checkpoint nội bộ của LangGraph) có đảm bảo **0 lần phát lặp chunk đã hoàn tất** (`Completed Chunk Replay Count = 0`), đồng thời giữ được câu chuyển tiếp (`bridge`) mượt mà về phần nội dung còn dang dở hay không?

- **Phạm vi kiểm chứng:** Mô phỏng 10 kịch bản ngắt/tiếp tục với trạng thái `PlaybackCompleted` ACK xác nhận từng chunk (bao gồm cả tình huống chunk đã sinh/đã gửi nhưng chưa có ACK phát xong trước khi bị ngắt), đồng thời khảo sát sơ bộ chèn `Periodic Recap` căn theo `semantic_breakpoint` (hậu `E01`, `P06-OPEN-3`).
- **Rủi ro & Gate liên quan:** `R05`, `R06` · `G2`, `G3`.

### `RQ3` — Trả lời câu hỏi lặp lại có nhận thức ngữ cảnh người xem & intent (`P06-E02`)
> **Câu hỏi:** Khi nhận 10–20 câu hỏi diễn đạt lại (paraphrase) xoay quanh cùng chủ đề giá hoặc phí vận chuyển (bao gồm trường hợp cùng một người xem hỏi lại nhiều lần), việc theo dõi lịch sử theo `viewer_id` và `intent` trong `Session-scoped Viewer Context` có làm giảm sự lặp lại nguyên văn đơn điệu mà vẫn duy trì độ chính xác tuyệt đối về số liệu/bằng chứng hay không?

- **Phạm vi kiểm chứng:** Đánh giá chất lượng biến thiên cách diễn đạt (`controlled paraphrase`, `repetition_quality`) đối chiếu với yêu cầu không sai lệch `stated_price_vnd` và `cited_evidence_ids` từ `P05` qua hợp đồng mock `p06-mock-v0.1` (`SINGLE_SKU`, `MULTI_SKU_COMPARE`, `SHOP_WIDE_POLICY`, `UNRESOLVED_SKU`).
- **Rủi ro & Gate liên quan:** `R05`, `R08`, `R04` · `G2`, `G4`.

### `RQ4` — Viết lại có giới hạn & Chống chịu lỗi Fail-Closed (`P06-E04`)
> **Câu hỏi:** Dưới áp lực đồng thời của chủ đề bắt buộc (`mandatory_topics`), tài liệu sản phẩm mâu thuẫn, mồi nhử phát ngôn bị cấm (`prohibited_claims`), đầu ra LLM sai định dạng (malformed structured output) và tình huống LLM timeout, vòng lặp viết lại có giới hạn (`bounded rewrite` với tối đa `K` lần thử) trong LangGraph có đảm bảo **0 đầu ra vi phạm hoặc chưa kiểm chứng** lọt qua trong giới hạn ngân sách retry/latency và rơi về fallback an toàn (`approved pre-generated chunk` hoặc `SAFE_FALLBACK`) đúng quy định hay không?

- **Phạm vi kiểm chứng:** Chạy bộ kịch bản đối kháng (adversarial/negative cases, bao gồm `UNRESOLVED_SKU` và `prohibited_echo_guard`) và ép lỗi hạ tầng (timeout, schema break) để kiểm tra tính dừng (termination) và tính an toàn fail-closed.
- **Rủi ro & Gate liên quan:** `R08`, `R16`, `R17`, `R03` · `G4`, `G6`.

### `RQ5` — Đánh đổi giữa Cửa sổ bộ nhớ, Cơ chế chống lặp & Ngân sách xử lý (Cross-cutting)
> **Câu hỏi:** Kích thước cửa sổ `Short-term Played History` (`W ∈ {5, 10, 20}` utterances gần nhất), lựa chọn phát hiện lặp **rule-based vs. bổ sung embedding cosine similarity** (`no pgvector` trong PoC độc lập) và ngân sách viết lại (`K` retries) tạo ra sự đánh đổi như thế nào giữa tính tự nhiên / giảm lặp ngữ nghĩa với độ trễ sinh lời thoại (`Generation Latency P50/P95`), lượng token tiêu thụ (`Token Consumption`) và chi phí ước tính (`Estimated LLM Cost`)?

- **Phạm vi kiểm chứng:** Thử nghiệm nhạy cảm tham số (ablation/sweep trên `W ∈ {5, 10, 20}`, rule-based vs. optional embedding cosine similarity, và `K`) xuyên suốt dữ liệu của `P06-E01`..`P06-E04` nhằm cung cấp bằng chứng định lượng giúp nhóm chốt cấu hình vận hành hợp lý cho `W1`/`W3` (không khóa ngưỡng trước khi có dữ liệu). Biến `Recap Policy` (`P06-OPEN-3`) được tách riêng như biến nghiên cứu hậu `E01`.
- **Rủi ro & Gate liên quan:** `R03`, `R05` · `G2`, `G5`.

---

## 2. Giả thuyết có thể bác bỏ (Falsifiable Hypotheses)

Mỗi thí nghiệm gắn với một giả thuyết rõ ràng và điều kiện bác bỏ trước khi chạy (theo quy trình `experiments/README.md` §4 & §7). **Không điều chỉnh ngưỡng để hợp thức hóa kết quả.**

| Mã Giả thuyết | Thí nghiệm | Phát biểu Giả thuyết | Điều kiện Bác bỏ / Quyết định (`CHANGE` / `NO-GO`) |
| :--- | :--- | :--- | :--- |
| **`H1`** | `P06-E01` | Phương pháp `Structured Story Planner + LangGraph` với bộ nhớ 4 thành phần (`W ∈ {5, 10, 20}`) đạt `Mandatory Topic Coverage` cao hơn và `Semantic Repetition Rate` thấp hơn đáng kể so với `Script-first` trong phiên 10–30 phút không bình luận, mà không phát sinh vi phạm hard gate (`Unsupported Claim Rate = 0`). | **NO-GO** nếu xuất hiện bất kỳ vi phạm fact/claim/SKU nào lọt qua cổng kiểm chứng (`> 0`). **CHANGE** nếu coverage hoặc mức độ lặp/tự nhiên không cải thiện so với `Script-first` hoặc chi phí/latency vượt khả năng chấp nhận cho phiên live. |
| **`H2`** | `P06-E02` | Việc đưa ngữ cảnh `viewer_id` + `intent` history vào `Session-scoped Viewer Context` giúp giảm lặp nguyên văn ở các câu hỏi giá/ship lặp lại mà vẫn giữ `Factual Accuracy` tuyệt đối với `ProductFact` và `EvidenceBundle`. | **NO-GO** nếu xuất hiện sai lệch giá, sai SKU hoặc trích dẫn sai `evidence_id` khi paraphrase (`> 0`). **CHANGE** nếu câu trả lời vẫn lặp rập khuôn theo nhận xét rubric mù (`repetition_quality`) hoặc làm mất tính rõ ràng của thông tin giá/ship. |
| **`H3`** | `P06-E03` | Cập nhật `StoryCheckpoint` chỉ từ `PlaybackCompleted` ACK kết hợp ranh giới `semantic_breakpoint` cho phép ngắt và nối mạch (`bridge`) qua 10 tình huống mà đạt `Completed Chunk Replay Count = 0` và duy trì `Narrative Coherence` / `transition_quality` đạt chuẩn rubric. | **NO-GO** nếu có bất kỳ chunk nào đã nhận `PlaybackCompleted` bị phát lại (`> 0`) hoặc làm mất nội dung bắt buộc phải phát (`mandatory_topics`) do lệch checkpoint. **CHANGE** nếu câu chuyển tiếp (`bridge`) gượng gạo hoặc làm đứt mạch hiểu của người nghe theo đánh giá mù. |
| **`H4`** | `P06-E04` | Vòng lặp `bounded rewrite` (giới hạn `K` retries) kết hợp cổng kiểm chứng `P05` chặn được 100% nội dung bị cấm/sai tài liệu trong bộ kiểm thử định nghĩa, đồng thời chấm dứt vòng lặp đúng hạn và kích hoạt fallback an toàn khi LLM timeout/lỗi schema. | **NO-GO** nếu có bất kỳ phát ngôn bị cấm, sai sự thật do tài liệu mâu thuẫn, hoặc draft chưa kiểm chứng lọt ra ngoài (`> 0`), hoặc graph rơi vào vòng lặp vô hạn / không fallback khi timeout. **CHANGE** nếu tỷ lệ phải hủy về fallback quá cao khiến phiên live rơi vào `SAFE_FALLBACK` thường xuyên. |

---

## 3. Các câu hỏi nghiên cứu mở (Open Research Questions — Stage 03 `P06.13` & Review `2026-11-26`)

Các câu hỏi dưới đây đã được định hướng thực nghiệm ở mức PoC (`SELECTED FOR PoC (Directional)`), nhưng **chưa đóng (`TO VALIDATE`)** và cần bằng chứng thực nghiệm + ký duyệt trước khi chuyển `VALIDATED`:

1. **`OPEN-1` (`P06-OPEN-1`) — Lựa chọn LLM Provider & Structured Output cho tiếng Việt:**
   - *Định hướng PoC:* Áp dụng kiến trúc 3 tầng (`MockLLMProvider` cho `unit_test`, `OllamaLocalProvider` với CPU `Qwen3 1.7B/4B` cho `local_smoke_test`, và `GeminiAPIProvider` nhóm `Flash`/`Flash-Lite` cho `formal_experiment`).
   - *Phần `TO VALIDATE`:* Xác minh model ID, quota, chi phí, độ ổn định structured output tiếng Việt trong ngân sách `W1` (`P50 ≤ 7s`, `P95 ≤ 10s` toàn luồng), và duyệt **privacy/DPA** trước khi gửi dữ liệu thật.

2. **`OPEN-2` (`P06-OPEN-2`, `P06-OPEN-3`) — Kích thước cửa sổ bộ nhớ chống lặp, Embeddings & Chính sách Recap hậu `E01`:**
   - *Định hướng PoC:* Bộ nhớ 4 thành phần (`W ∈ {5, 10, 20}`), phát hiện lặp **rule-based trước**, embedding cosine similarity chỉ là biến đối chiếu tùy chọn (`no pgvector` trong PoC độc lập); **Recap Policy** theo mô hình `Periodic Recap + Context-aware Question Response`, cấm recap mỗi viewer join.
   - *Phần `TO VALIDATE`:* Đo đạc giá trị `W` tối ưu và nhu cầu embedding qua `RQ1`/`RQ5`; khảo sát tần suất/điều kiện **Periodic Recap** ở giai đoạn **sau `P06-E01`** và rà soát cùng Product Owner (`G2/G6`).

3. **`OPEN-3` (`P06-OPEN-4`) — Bộ tiêu chí đánh giá con người & Ngưỡng chấp nhận thực chất:**
   - *Định hướng PoC:* Thang điểm `1–5` trên **6 tiêu chí** (`narrative_coherence`, `naturalness`, `persuasiveness`, `context_relevance`, `transition_quality`, `repetition_quality`) trong `evaluation/rubrics/human_eval_rubric_v0.1.md`, đi kèm nguyên tắc **Hard Gates không thể bù trừ** bởi điểm mềm.
   - *Phần `TO VALIDATE`:* Thực hiện **pilot calibration** để chốt ngưỡng chấp nhận định lượng chính thức và phân công `Owner` / `Reviewer` (`P06-OPEN-6`) trước khi chạy formal benchmark & blind rating ở Phase 5.
