# Khung Đánh giá P06 (`evaluation/`)

**Trạng thái:** `NOT STARTED` (khung rubric người thật `v0.1` đã khởi tạo ở mức `PROPOSED / TO VALIDATE`; chưa có dữ liệu chấm thực tế hoặc kết quả metrics chạy thật).

## 1. Tách biệt Automatic Metrics và Human Blind Rubric

### Automatic Metrics (`evaluation/metrics/`)
- `topic_coverage`: Tỷ lệ chủ đề bắt buộc (`mandatory_topics`) trong `StoryPlan` được xác nhận hoàn tất qua `PlaybackCompleted`.
- `semantic_repetition`: Mức độ lặp từ/n-gram (`rule_based` là phương pháp chính `SELECTED FOR PoC`) hoặc lặp ngữ nghĩa trên cửa sổ lịch sử phát `W ∈ {5, 10, 20}` (comparator `embedding_cosine` chỉ dùng đối chiếu nếu cần).
- `completed_chunk_replay_count`: Số lần phát trùng chunk đã hoàn tất (kiểm tra tính đúng của checkpoint/resume).
- `rewrite_rate` và `retry_count`: Tỷ lệ candidate phải rewrite và phân bố số lần retry (kiểm tra bounded rewrite).
- `latency`: Độ trễ xử lý theo từng bước (P50/P95), **bắt buộc phân tách theo `run_tier` / `provider`** (`ollama` CPU smoke test vs `gemini` formal experiment).
- `token_cost`: Số token đầu vào/đầu ra và số lần gọi model.

### Human Blind Rubric (`evaluation/rubrics/human_eval_rubric_v0.1.md`)
Sử dụng rubric thang `1–5` gồm **6 tiêu chí** với neo hành vi cụ thể:
1. `narrative_coherence`: Độ mạch lạc của mạch kể khi dẫn dài (`10–30` phút) hoặc sau khi ngắt/trả lời bình luận.
2. `naturalness`: Độ tự nhiên của lời thoại tiếng Việt trong ngữ cảnh livestream bán hàng.
3. `persuasiveness`: Tính thuyết phục bán hàng bám sát dữ kiện kiểm chứng, không thổi phồng.
4. `context_relevance`: Độ bám sát `active_sku`, mục tiêu merchant, ngữ cảnh `CommentTask` và lịch sử đã phát.
5. `transition_quality`: Chất lượng câu chuyển ý giữa các chủ đề và câu `bridge` quay lại mạch kể sau ngắt quãng.
6. `repetition_quality`: Mức độ kiểm soát lặp ý và đa dạng diễn đạt (`5` = tốt nhất / ít lặp vô ích nhất).

- Bắt buộc **chấm mù** (`blind_method_id` ẩn danh `script_first` vs `langgraph_structured_story` và giá trị `W`), thực hiện **Pilot Calibration Protocol** để kiểm tra độ đồng thuận giữa người chấm và khóa tiêu chí nghiệm thu **trước khi** chạy benchmark chính thức.
- Lưu toàn bộ phiếu chấm và kết quả hiệu chỉnh làm bằng chứng đánh giá.

## 2. Quy trình Kiểm thử 3 Tầng (3-Tier Provider Testing Workflow)

1. **Tầng 1 — `Mock` (`unit_test`, `configs/models/mock.yaml`):** Chỉ dùng cho kiểm thử đơn vị, hợp đồng DTO, vòng lặp LangGraph, retry và fallback. **Tuyệt đối không** dùng đầu ra `Mock` làm bằng chứng chất lượng kể chuyện hay tự nhiên tiếng Việt.
2. **Tầng 2 — `Ollama CPU` (`local_smoke_test`, `configs/models/ollama_qwen3_1.7b.yaml` / `4b`):** Chỉ dùng để khám phá cục bộ, tinh chỉnh prompt và smoke test pipeline đầu-cuối trên CPU. **Tuyệt đối không** gộp số liệu vào bảng benchmark chính thức với `Gemini` và không suy diễn độ trễ CPU thành năng lực production.
3. **Tầng 3 — `Gemini Flash/Flash-Lite` (`formal_experiment`, `configs/models/gemini_flash.yaml`):** Chỉ dùng cho thí nghiệm đối chiếu chính thức trên dữ liệu `SYNTHETIC` hoặc `PUBLIC_APPROVED` sau khi xác minh `model_id`, quota, pricing, structured output tiếng Việt và trạng thái DPA.

## 3. Nguyên tắc Liêm chính Đánh giá

- **Không dùng đầu ra của mock verifier hoặc mock generator làm nguồn chân lý (ground truth) duy nhất** cho tính đúng sự thật của phát ngôn; các ca kiểm tra factual correctness phải đối chiếu với dữ liệu gốc có nguồn (`ProductFact`, `EvidenceChunk`, `ClaimRegistryEntry`, `EligibilitySnapshot`) và review của con người khi cần.
- **Hard-Constraint Non-Compensation Rule:** Mọi vi phạm **Safety hard gates** (`0` vi phạm trên negative suites: không bịa giá, không nhắc OCOP khi chưa `VERIFIED`, không lọt claim cấm, không tự đổi Active SKU, không replay chunk đã hoàn tất ngoài ý muốn) đều dẫn tới **`FAIL / NO-GO` ngay lập tức** — điểm 1–5 cao không bao giờ bù trừ được lỗi an toàn/quyền.
- **Quality & performance thresholds:** Hiện đang ở trạng thái **`TO VALIDATE`** — không tự bịa hoặc tự khóa ngưỡng đạt trước khi hoàn tất pilot calibration, phân tích baseline và có phê duyệt của reviewer.
- Báo cáo đầy đủ theo từng nhóm đầu vào/cấu hình (ví dụ theo `W ∈ {5, 10, 20}`, theo `run_tier`, bao gồm cả lượt lỗi), thay vì chỉ báo một giá trị trung bình.
