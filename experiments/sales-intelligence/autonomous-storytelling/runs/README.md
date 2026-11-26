# Quy chuẩn Lưu trữ Lần chạy P06 (`runs/`)

**Trạng thái:** `NOT STARTED` (chưa có dữ liệu chạy nào được ghi nhận).

## 1. Cấu trúc thư mục chuẩn cho mỗi lần chạy

Mỗi lượt chạy thực nghiệm được lưu tại `runs/<exp_id>/<run_id>/` (ví dụ: `runs/P06-E01/<run_id>/`) với đầy đủ 9 tệp sau:

| Tệp artifact | Mục đích & Nội dung tối thiểu |
| :--- | :--- |
| `manifest.json` | Metadata tái lập chuẩn theo [`experiments/README.md` §5](../../../README.md#5-tái-lập-thí-nghiệm) và tương thích P05 `ExperimentManifest` (`experiment_id`, `run_id`, `created_at`, `dataset_source`, `is_synthetic`, `environment`, `config`, `metrics`, `decision`, `notes`, cộng thêm `commit_hash`, `prompt_hashes`, `seed`, và đầy đủ **Benchmark Telemetry Fields** ở mục 2). |
| `config.yaml` | Bản sao cấu hình đầy đủ đã dùng cho lần chạy (`default.yaml` hợp nhất cùng `provider_config` và config riêng của experiment). |
| `story_plan.json` | `StoryPlan` đầu vào/được lập kế hoạch kèm version và danh sách `mandatory_topics`. |
| `transcript.jsonl` | Chuỗi từng candidate/chunk theo thứ tự thời gian kèm `sku_id`, `intent`, `cited_evidence_ids` và kết quả P05 gate. |
| `playback_events.jsonl` | Chuỗi sự kiện `PlaybackCompleted` (mô phỏng hoặc thật) dùng để cập nhật `played_history` và checkpoint. |
| `graph_trace.jsonl` | Dấu vết chuyển trạng thái qua các node LangGraph, số lần retry/rewrite và lý do dừng. |
| `metrics.json` | Toàn bộ automatic metrics đo được theo nhóm đầu vào/cấu hình (không tự bịa số liệu), kèm `latency_ms` (P50/P95). |
| `token_usage.json` | Thống kê số lượng request, `prompt_tokens`, `completion_tokens`, tổng `token_usage` và lỗi/timeout theo từng model/provider. |
| `errors.jsonl` | Nhật ký lỗi, candidate bị P05 gate chặn, timeout hoặc lý do dừng bất thường. |

## 2. Trường Telemetry Bắt buộc (Benchmark Telemetry Fields)

Mỗi `manifest.json` / bản ghi benchmark bắt buộc ghi rõ đầy đủ các trường telemetry sau để đảm bảo tái lập và đối chiếu công bằng:

- `run_tier`: `"unit_test"` (`mock`) | `"local_smoke_test"` (`ollama`) | `"formal_experiment"` (`gemini`).
- `provider`: Tên provider thực thi (`"mock"`, `"ollama"`, `"gemini"`).
- `model_id`: Mã model cụ thể (ví dụ `"deterministic-mock-v0.1"`, `"qwen3:1.7b"`, hoặc Gemini model ID đã xác minh).
- `quantization`: Tag lượng tử hóa thực tế (bắt buộc với Ollama CPU, ví dụ `"q4_K_M"`, hoặc `null` với API/Mock).
- `cpu_model`: Tên/dòng CPU của máy chạy benchmark/smoke test (đặc biệt bắt buộc cho Ollama CPU).
- `ram_gb`: Dung lượng RAM hệ thống (GB).
- `context_window`: Kích thước cửa sổ ngữ cảnh cấu hình cho lượt chạy (ví dụ `8192`).
- `sampling_params`: Các tham số lấy mẫu (`temperature`, `top_p`, `max_tokens`, `seed`).
- `prompt_version`: Phiên bản / hash của bộ prompt template đã dùng.
- `latency_ms`: Thống kê độ trễ theo mili-giây (`p50`, `p95`, `mean`, tách theo bước và tổng lượt).
- `token_usage`: Tổng hợp `prompt_tokens`, `completion_tokens`, `total_tokens`, số request thành công/thất bại.
- `provider_config`: Đường dẫn tệp cấu hình model đã dùng (ví dụ `configs/models/ollama_qwen3_1.7b.yaml`).
- `contract_version`: Phiên bản hợp đồng schema/DTO của P06–P05–P07–P08 áp dụng trong lượt chạy.

## 3. Quy tắc Cô lập Tầng Provider (Cross-Tier Isolation Rules)

- **CẤM gộp (pool) số liệu benchmark giữa `Ollama CPU` (`local_smoke_test`) và `Gemini` (`formal_experiment`):** Mọi bảng tổng hợp, đồ thị và báo cáo `reports/` phải tách riêng nhóm theo `run_tier`, `provider` và `model_id`.
- **KHÔNG dùng lượt chạy `Mock` (`unit_test`) làm bằng chứng chất lượng:** `Mock` chỉ chứng minh tính đúng đắn của state machine, hợp đồng DTO, bounded rewrite và fallback logic — không đại diện cho chất lượng tiếng Việt, độ tự nhiên hay khả năng chống lặp của LLM.
- **Không suy diễn hiệu năng CPU sang Production:** Số liệu `latency_ms` trên `Ollama CPU` (không dGPU) chỉ phản ánh chi phí smoke test cục bộ.

## 4. Quy tắc Git & Tái lập

- Thư mục con chi tiết `runs/*/*` được loại trừ trong `.gitignore` để giữ repository gọn và tránh lọt log tạm.
- Khi tổng hợp kết quả để review PR, trích xuất các bảng/manifest đã rà soát sạch dữ liệu nhạy cảm vào `reports/tables/`.
- Không xóa các lượt chạy thất bại khi ghi nhận lịch sử; đánh dấu rõ trạng thái và lý do lỗi trong `manifest.json` và `errors.jsonl`.
