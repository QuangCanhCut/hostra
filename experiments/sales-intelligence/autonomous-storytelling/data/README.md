# Dữ liệu thí nghiệm P06 (`data/`)

**Trạng thái:** `NOT STARTED` (đang chuẩn bị khung thư mục; chưa sinh hoặc khóa bộ dữ liệu chạy chính thức).

## 1. Nguồn gốc & Phân tách dữ liệu (`synthetic` vs `real`)

- Mọi dữ liệu trong giai đoạn PoC khởi đầu đều phải gắn nhãn rõ `is_synthetic: true` (hoặc nguồn/quyền cụ thể nếu là dữ liệu thật) và khai báo trong `manifest.json` của từng lần chạy.
- Tách biệt hoàn toàn:
  - `products/`: Snapshot thông tin SKU, `ProductFact`, `EvidenceChunk`, `ClaimRegistryEntry`, `EligibilitySnapshot`.
  - `merchant_goals/`: Mục tiêu phiên bán hàng, mandatory topics và ràng buộc merchant.
  - `story_plans/`: `StoryPlan` đã duyệt dùng làm đầu vào cho thử nghiệm.
  - `comments/`: Tập câu hỏi lặp, paraphrase và các tình huống ngắt mạch (`P06-E02`, `P06-E03`).
  - `scenarios/`: Kịch bản định tuyến thời gian, mâu thuẫn tài liệu, lỗi model (`P06-E01`..`P06-E04`).
  - `annotations/`: Nhãn chuẩn hoặc phiếu chấm thủ công (human blind evaluation).

## 2. Lưu ý quan trọng về hạt giống P05 (`catalog_seed.json`)

Khi tái sử dụng dữ liệu từ [`../knowledge-verification/data/catalog_seed.json`](../../knowledge-verification/data/catalog_seed.json):

- `SKU-HONEY-01` và `SKU-TEA-02` có `ocop_status: "VERIFIED"` và `food_safety_verified: true`.
- `SKU-CASHEW-03` có `ocop_status: "PENDING"` (`ocop_code: null`), nên sẽ bị P05 `PublicationGate` chặn các phát ngôn liên quan chứng nhận OCOP.
- **Quy tắc sử dụng:**
  - Các lượt chạy **positive 3-SKU** của `P06-E01` BẮT BUỘC phải dùng **3 SKU tổng hợp đều ở trạng thái `OCOP: VERIFIED`** (bổ sung SKU tổng hợp thứ 3 đạt `VERIFIED`, không dùng nguyên `SKU-CASHEW-03` ở trạng thái `PENDING` cho luồng positive).
  - Giữ lại các SKU có `ocop_status: "PENDING"` hoặc `EXPIRED` cho bộ **negative suites** trong `P06-E04` để kiểm tra hard gate chặn phát ngôn sai điều kiện.

## 3. Quy tắc quyền dữ liệu & Bảo mật

- Tuyệt đối không commit chứng nhận OCOP thật, dữ liệu định danh merchant/viewer thật hoặc tài liệu chưa được cấp quyền lên Git.
- Không sửa hồ sơ thật để trình bày như chứng cứ thật.
- Nếu sử dụng external LLM API trong tương lai, phải kiểm tra quyền gửi dữ liệu trước khi đưa bất kỳ tài sản không phải `synthetic` vào prompt.
