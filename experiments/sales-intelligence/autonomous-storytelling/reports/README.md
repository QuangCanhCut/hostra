# Báo cáo & Quyết định Kỹ thuật P06 (`reports/`)

**Trạng thái:** `NOT STARTED` (`final_report.md` được hoãn đến khi có dữ liệu chạy thực tế ở Phase 4–5).

## 1. Nguyên tắc báo cáo & ra quyết định

Mọi báo cáo kết quả cho `P06-E01`..`P06-E04` phải tuân thủ [quy chuẩn Stage 03](../../../README.md#7-workload-và-quy-tắc-nghiệm-thu) và chỉ sử dụng 4 nhãn kết luận sau:

- **`GO`:** Chỉ áp dụng trong phạm vi cụ thể đã có evidence tái lập, vượt qua toàn bộ safety hard gates (`0` vi phạm trên bộ test định nghĩa) và được reviewer phê duyệt. Không đồng nghĩa đã sẵn sàng production.
- **`CHANGE`:** Safety hard gates còn nguyên nhưng chất lượng, latency hoặc chi phí chưa đạt mục tiêu — cần điều chỉnh phương pháp/prompt/cấu hình và thử lại.
- **`NO-GO`:** Vi phạm hard gate về claims, OCOP, quyền dữ liệu, Active SKU (`I-04`) hoặc playout correctness (`I-06`).
- **`INCONCLUSIVE`:** Thiếu dữ liệu, thiếu evidence hoặc điều kiện môi trường chưa đủ để kết luận; phải ghi rõ việc cần làm tiếp.

## 2. Khai báo giới hạn bắt buộc (Mock vs Real Disclosure)

Mọi bảng tổng hợp (`reports/tables/`) và biểu đồ (`reports/figures/`) phải tách biệt và công bố rõ:
- Dữ liệu chạy là `synthetic` hay dữ liệu thật có quyền.
- Lượt chạy dùng `mock` provider hay real LLM API (kèm `model_id` và phạm vi thời điểm).
- Cơ chế phát sử dụng simulated `PlaybackCompleted` ACK hay luồng tích hợp P04/P08 thật.

## 3. Kế hoạch bàn giao (`NOT STARTED`)

- `reports/tables/` — Bảng đối chiếu metrics theo từng mã thí nghiệm và cấu hình.
- `reports/figures/` — Biểu đồ độ phủ chủ đề, mức lặp ngữ nghĩa, latency/retry.
- `reports/final_report.md` — Hoãn tạo cho tới khi hoàn tất các lượt chạy Phase 4–5 và có evidence thực đo đầy đủ.
