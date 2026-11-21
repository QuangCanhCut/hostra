# Dữ liệu thử nghiệm P05 (`knowledge-verification/data/`)

> **Cảnh báo nguồn dữ liệu:** Toàn bộ dữ liệu hiện có trong thư mục này được gắn nhãn `synthetic_for_poc_validation` (`is_synthetic: true`). Không sử dụng làm bằng chứng OCOP thật hoặc dữ liệu khách hàng thật.

## Danh sách file

- `catalog_seed.json`: Bộ dữ liệu mẫu cho 3 SKU thực phẩm đóng gói (trong phạm vi 2–5 SKU của MVP):
  - `SKU-HONEY-01`: Mật ong hoa cà phê Đắk Lắk (`OCOP: VERIFIED`, `food_safety_verified: true`)
  - `SKU-TEA-02`: Trà Shan Tuyết cổ thụ Hà Giang (`OCOP: VERIFIED`, `food_safety_verified: true`)
  - `SKU-CASHEW-03`: Hạt điều rang củi Bình Phước (`OCOP: PENDING` — dùng để test chặn phát ngôn OCOP chưa xác minh)
- `eval_questions.json`: Bộ 20 câu hỏi khởi đầu chia theo 5 nhóm (`structured_fact`, `faq_diacritics`, `faq_no_diacritics_slang`, `adversarial_unsafe_claim`, `adversarial_ocop_pending`, `adversarial_prompt_injection`) để chạy nhanh trước khi mở rộng lên 100–200 câu cho benchmark `P05-E02`.

## Quy tắc quản lý dữ liệu

1. Luôn tách rõ dữ liệu `synthetic` và tài liệu merchant thật (khi có) trong manifest.
2. Không commit chứng nhận thật chứa thông tin nhạy cảm hoặc chưa có quyền sử dụng lên Git.
3. Không sửa chứng cứ thật thành dữ liệu giả.
