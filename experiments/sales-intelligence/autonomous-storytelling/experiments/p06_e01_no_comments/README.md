# Thí nghiệm P06-E01 — Kể chuyện không bình luận

**Mã thí nghiệm:** `P06-E01` · **Module:** P06 · **Rủi ro liên quan:** R05, R08 · **Gate:** G2, G6 · **Trạng thái:** `NOT STARTED`

---

## 1. Câu hỏi nghiên cứu (Research Question)

Sau 10–30 phút phát liên tục không có bình luận từ người xem, kiến trúc lập kế hoạch có cấu trúc (`StoryPlan` + theo dõi coverage từ lời thực sự đã phát trên cửa sổ `W ∈ {5, 10, 20}`) có giúp bao phủ đầy đủ các chủ đề bắt buộc (`mandatory_topics`) và tránh lặp ý vô ích so với phương án `script_first` hay không?

## 2. Giả thuyết (Hypothesis)

Việc tách `StoryPlan` phân cấp khỏi bước sinh từng `StoryChunk`, kết hợp chống lặp `rule_based` trên `short_term_played_history` (`W ∈ {5, 10, 20}`) và chỉ cập nhật tiến độ dựa trên `PlaybackCompleted` ACK sẽ giúp duy trì độ phủ chủ đề bắt buộc cao và giảm lặp ngữ nghĩa theo thời gian dài mà không làm đứt mạch kể hoặc vượt ngân sách chi phí/latency cho phép (`TO VALIDATE`).

## 3. Baseline đối chiếu

- **`script_first`:** Kịch bản tuyến tính cố định theo danh sách/vòng lặp định sẵn, không tự tái cấu trúc linh hoạt theo trạng thái phủ chủ đề động.

## 4. Phương pháp đề xuất

- **`langgraph_structured_story` (`SELECTED FOR PoC`):** Structured Story Planner + Dynamic Verified Generation bằng LangGraph, sinh từng `StoryChunk` gắn `SKU`, `intent`, `semantic_breakpoint`, áp dụng chống lặp `rule_based` trước (comparator `embedding_cosine` chỉ đối chiếu tùy chọn nếu cần) và kiểm tra qua P05 `PublicationGate`.
- **Chính sách Recap trong `E01`:** `recap_enabled: false` (biến nghiên cứu recap được tách riêng và hoãn sang các thí nghiệm sau `E01`).

## 5. Bộ dữ liệu & Ràng buộc chuẩn bị

- **Bộ dữ liệu positive:** 3 SKU thực phẩm đóng gói tổng hợp (`is_synthetic: true`), trong đó **cả 3 SKU đều ở trạng thái `OCOP: VERIFIED`** và `food_safety_verified: true`, có `ProductFact`, `EvidenceChunk` và `mandatory_topics` rõ nguồn.
- Lưu ý: Không sử dụng trực tiếp SKU đang ở trạng thái `OCOP: PENDING` (như `SKU-CASHEW-03` trong seed P05) cho lượt positive 3-SKU của `P06-E01`.

## 6. Biến độc lập (Independent Variables)

- Phương pháp sinh lời thoại: `script_first` vs `langgraph_structured_story`.
- Thời lượng mô phỏng phiên phát: `10` phút và `30` phút (`simulated_durations_min: [10, 30]`).
- Kích thước cửa sổ `short_term_played_history`: quét `history_window_sweep: [5, 10, 20]` (`W ∈ {5, 10, 20}`).
- Phương pháp chống lặp: `rule_based` (chính, `SELECTED FOR PoC`); tùy chọn đối chiếu `embedding_cosine` nếu `rule_based` cho thấy dấu hiệu chưa đủ.

## 7. Biến kiểm soát (Controlled Variables)

- Cùng bộ 3 SKU `OCOP: VERIFIED`, cùng `mandatory_topics` và `merchant_goals`.
- Cùng `seed` (`42`), cùng `chunking_policy` (`target_duration_sec: [3, 5]`, `max_duration_sec: 8`), cùng `LLMProvider`, `model_config` và `sampling` (`temperature: 0.3`) trong mỗi cặp so sánh.
- Không chèn `CommentTask` (`comment_events_enabled: false`) và tắt recap (`recap_enabled: false`).

## 8. Quy trình thực thi 3 Tầng (Execution Protocol & 3-Tier Workflow)

1. **Tầng 1 — `unit_test` (`configs/models/mock.yaml`):** Chạy kiểm thử quyết định với `MockLLMProvider` để xác minh schema, P05 gate fail-closed, cập nhật `played_history` theo `PlaybackCompleted`, và luồng `script_first` vs `langgraph_structured_story` đạt `100%` pass trước khi dùng LLM thật. **Không** dùng kết quả `Mock` làm bằng chứng chất lượng kể chuyện.
2. **Tầng 2 — `local_smoke_test` (`configs/models/ollama_qwen3_1.7b.yaml`):** Smoke test cục bộ trên CPU với Ollama để tinh chỉnh prompt và kiểm tra độ ổn định pipeline đầu-cuối (lưu ý ghi `quantization`, `cpu_model`, `ram_gb`; **không** gộp số liệu vào benchmark Gemini).
3. **Tầng 3 — `formal_experiment` (`configs/models/gemini_flash.yaml`):** Chỉ thực hiện sau khi xác minh `model_id`, quota, pricing, structured output tiếng Việt và DPA trên dữ liệu `SYNTHETIC`/`PUBLIC_APPROVED`:
   - Khởi tạo `StoryPlan` cho 3 SKU từ `configs/experiments/p06_e01.yaml` và `configs/default.yaml`.
   - Chạy vòng lặp mô phỏng cho `simulated_durations_min: [10, 30]` và `history_window_sweep: [5, 10, 20]` với `playback_ack_mode: "simulated_deterministic"` (ghi nhận rõ đây là ACK mô phỏng, không phải playout thật của P04).
   - Chỉ đánh dấu chunk/topic đã hoàn tất khi nhận `PlaybackCompleted` mô phỏng; ghi nhận cả candidate bị chặn hoặc cần rewrite.
   - Lưu toàn bộ 9 artifacts chuẩn + telemetry đầy đủ vào `runs/P06-E01/<run_id>/`.

## 9. Chỉ số đánh giá (Automatic vs Human Metrics)

- **Automatic metrics:**
  - `topic_coverage`: Tỷ lệ `mandatory_topics` được phát hoàn tất (`PlaybackCompleted`).
  - `semantic_repetition`: Mức độ lặp từ/n-gram (`rule_based` chính) hoặc ngữ nghĩa trên cửa sổ lịch sử phát `W`.
  - `completed_chunk_replay_count`: Số lần phát lại chunk đã hoàn tất (mục tiêu `0` khi không có lệnh replay).
  - `rewrite_rate` & `retry_count`: Tần suất phải viết lại candidate và số lần retry.
  - `latency_ms` & `token_usage`: Độ trễ sinh chunk (P50/P95) và mức tiêu thụ token, phân tách theo `run_tier`.
- **Human blind rubric ([`human_eval_rubric_v0.1.md`](../../evaluation/rubrics/human_eval_rubric_v0.1.md)):**
  - Chấm mù 6 tiêu chí thang `1–5`: `narrative_coherence`, `naturalness`, `persuasiveness`, `context_relevance`, `transition_quality`, `repetition_quality` (sau khi chạy Pilot Calibration Protocol và áp dụng Hard-Constraint Non-Compensation Rule).

## 10. Bằng chứng bắt buộc (Evidence Artifacts)

Mỗi lần chạy phải lưu đủ tại `runs/P06-E01/<run_id>/`:
- `manifest.json` (kèm đầy đủ Benchmark Telemetry Fields), `config.yaml`, `story_plan.json`, `transcript.jsonl`, `playback_events.jsonl`, `graph_trace.jsonl`, `metrics.json`, `token_usage.json`, `errors.jsonl`.
- Kèm phiếu chấm mù rubric (nếu thực hiện đánh giá người thật).

## 11. Kế hoạch phân tích lỗi (Error Analysis Plan)

- So sánh mức lặp ý/lặp chuyển đoạn ở mốc `20–30` phút giữa các giá trị `W ∈ {5, 10, 20}` và giữa `script_first` với `langgraph_structured_story`.
- Kiểm tra các `mandatory_topics` bị bỏ sót, trôi thứ tự hoặc bị P05 gate chặn do thiếu trích dẫn `evidence_id`.
- Đối chiếu sự khác biệt giữa candidate đã sinh và nội dung thực sự nhận `PlaybackCompleted`.

## 12. Giới hạn dự kiến (Limitations)

- Dùng `simulated_deterministic` `PlaybackCompleted` ACK nên chưa phản ánh jitter, drop packet hoặc delay phát thực tế của P04.
- Dữ liệu `synthetic` và `mock` / `ollama` CPU smoke test chưa đại diện cho chất lượng/độ trễ production thật của merchant.

## 13. Tiêu chí nghiệm thu & Trạng thái ngưỡng

- **Ràng buộc đã xác nhận (Hard-Constraint Non-Compensation Rule):** `0` vi phạm P05 gate (không bịa giá/OCOP/claim cấm), không tự đổi Active SKU (`I-04`), không tự đánh dấu đã nói khi chưa có `PlaybackCompleted` (`I-06`). Vi phạm bất kỳ điều kiện nào -> **`FAIL / NO-GO`**.
- **Ngưỡng chất lượng (`TO VALIDATE`):** Ngưỡng đạt của `topic_coverage`, `semantic_repetition` và điểm 6 tiêu chí rubric chưa được khóa cố định; cần hoàn tất pilot calibration và đối chiếu baseline với reviewer để kết luận `GO` / `CHANGE` / `NO-GO` / `INCONCLUSIVE`.

## 14. Trạng thái hiện tại

- `NOT STARTED` — Chưa có lượt chạy hoặc kết quả thực đo nào.
