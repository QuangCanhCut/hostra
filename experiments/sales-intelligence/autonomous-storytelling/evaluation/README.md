# Khung Đánh giá P06 (`evaluation/`)

**Trạng thái:** `IN RESEARCH` (`E01-T08` khung đánh giá tự động 5 trục + xuất phiếu chấm mù đã triển khai trong `src/p06/evaluation/` và xác minh trên `Mock`; `Human Blind Eval` & `GoldFactualLabel` thực tế với `Ollama`/`Gemini` vẫn `NOT STARTED / TO VALIDATE`).

## 1. Tách biệt Automatic Metrics và Human Blind Rubric

### Automatic Metrics (`src/p06/evaluation/metrics/` & `evaluator.py`, `comparison.py`)
- `coverage.py` (`mandatory_topic_coverage`, `declared_verified_claim_coverage`, `duration_fulfillment`, `time_to_complete_mandatory_topics_sec` trên trục `VirtualClock`, v.v.): Bám hoàn toàn `PlaybackCompleted` & `APPLIED` ACK (loại lượt fallback).
- `repetition.py` (`exact_chunk_replay_count`, `exact_normalized_text_replay_count`, `outside_window_exact_text_replay_count`, `max_prior_{word,ngram3}_jaccard`, `windowed_ngram3_jaccard_mean_w{5,10,20}`, `distinct_{1,2,3}`): Đo trên **toàn bộ `transcript.jsonl`** độc lập với cửa sổ agent `W`.
- `safety.py` (`p05_rejection_*`, Hard Gates `invalid_candidate_playback_count`, `duplicate_completed_chunk_replay_count`, và 5 chỉ số `GoldFactualLabel` độc lập gồm `verifier_false_accept_count`, `verifier_precision`, `verifier_recall`): Trả `NOT_EVALUATED` (`None`) nếu chưa có `gold_labels`, cấm dùng `P05 ALLOW` làm ground truth.
- `reliability.py` (`generation_attempts`, `rewrite_rate`, `retry_budget_violations` = `0`, `fallback_rate`, `safe_abort_count/rate` đã lọc lượt kết thúc biên SKU sạch qua `is_clean_termination_boundary_trace()`).
- `performance.py` (`provider_latency_{p50,p95}_ms`, `invocation_latency_{p50,p95}_ms`, token kể cả `wasted_tokens`, `estimated_llm_cost_usd`): Bảo toàn `None` (`NOT_EVALUATED`) khi thiếu telemetry, `NOT_APPLICABLE` cho Mock cost, tách rạch ròi `run_tier` (`comparison.py` chặn gộp chéo tầng `CROSS_TIER_POOLING_PROHIBITED`).
- `human_eval.py` (`export_blind_human_eval_sheets()`): Xáo trộn tất định và ẩn danh `METHOD_A..E` không lộ danh tính phương pháp hay `W`.

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
