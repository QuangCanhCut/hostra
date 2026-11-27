# Báo cáo & Quyết định Kỹ thuật P06 (`reports/`)

**Trạng thái:** **`E01 CLOSED — Decision: CHANGE`** (`overall_gate_status = NOT_EVALUATED`, `Human Blind / Gold = PENDING`, **`NOT VALIDATED`**). Đã xuất [`E01/p06_e01_research_report.md`](./E01/p06_e01_research_report.md), [`E01/e01_artifact_index.json`](./E01/e01_artifact_index.json), `12` bảng CSV trong `tables/E01/` và `8` biểu đồ PNG trong `figures/E01/`.

## 1. Nguyên tắc báo cáo & ra quyết định

Mọi báo cáo kết quả cho `P06-E01`..`P06-E04` phải tuân thủ [quy chuẩn Stage 03](../../../README.md#7-workload-và-quy-tắc-nghiệm-thu) và chỉ sử dụng 4 nhãn kết luận sau:

- **`GO`:** Chỉ áp dụng trong phạm vi cụ thể đã có evidence tái lập, vượt qua toàn bộ safety hard gates (`0` vi phạm trên bộ test định nghĩa) và được reviewer phê duyệt. Không đồng nghĩa đã sẵn sàng production.
- **`CHANGE`:** Safety hard gates còn nguyên nhưng chất lượng, latency hoặc chi phí chưa đạt mục tiêu — cần điều chỉnh phương pháp/prompt/cấu hình và thử lại.
- **`NO-GO`:** Vi phạm hard gate về claims, OCOP, quyền dữ liệu, Active SKU (`I-04`) hoặc playout correctness (`I-06`).
- **`INCONCLUSIVE`:** Thiếu dữ liệu, thiếu evidence hoặc điều kiện môi trường chưa đủ để kết luận; phải ghi rõ việc cần làm tiếp.

## 2. Khai báo giới hạn bắt buộc (Mock vs Real Disclosure)

Mọi bảng tổng hợp (`reports/tables/<EXPERIMENT_ID>/`) và biểu đồ (`reports/figures/<EXPERIMENT_ID>/`) phải tách biệt và công bố rõ:
- Dữ liệu chạy là `synthetic` hay dữ liệu thật có quyền.
- Lượt chạy dùng `mock` provider hay real LLM API (kèm `model_id` và phạm vi thời điểm).
- Cơ chế phát sử dụng simulated `PlaybackCompleted` ACK hay luồng tích hợp P04/P08 thật.

## 3. Quy chuẩn Lưu trữ Theo Experiment (`E01..E04`)

Tài liệu chỉ mục cấp module giữ `reports/README.md` ở thư mục gốc; toàn bộ báo cáo, chỉ mục, bảng và biểu đồ của từng thí nghiệm **bắt buộc** lưu trong thư mục `<EXPERIMENT_ID>/`:

- **`reports/E01/` (`CLOSED — CHANGE`):** [`p06_e01_research_report.md`](./E01/p06_e01_research_report.md), [`e01_artifact_index.json`](./E01/e01_artifact_index.json), `tables/E01/` (`12` CSV), `figures/E01/` (`8` PNG).
- **`reports/E02/`, `reports/E03/`, `reports/E04/` (`NOT STARTED`):** Cùng với `figures/{E02,E03,E04}/` và `tables/{E02,E03,E04}/` đã chuẩn bị sẵn (`.gitkeep`) cho các đợt thực nghiệm kế tiếp.
