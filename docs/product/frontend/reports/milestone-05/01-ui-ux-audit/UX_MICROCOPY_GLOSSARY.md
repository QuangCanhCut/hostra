# HOSTRA AI — Từ điển Ngôn ngữ Giao diện (UX Microcopy Glossary — M05.1)

Nguyên tắc cốt lõi: **Thân thiện, tự nhiên với nhà bán hàng nông sản/OCOP Việt Nam, tuyệt đối KHÔNG làm sai lệch ngữ nghĩa an toàn kiến trúc.** Các thuật ngữ kỹ thuật chuyên sâu chỉ giữ lại trong ngăn kéo **Chẩn đoán kỹ thuật** hoặc phần **Chi tiết nguồn đo** (thu gọn theo nhu cầu).

---

## 1. Bảng chuyển đổi thuật ngữ kỹ thuật → Tiếng Việt dễ hiểu

| Thuật ngữ hiện tại trên UI | Vị trí xuất hiện | Đề xuất thay thế cho người bán hàng | Nơi giữ nguyên thuật ngữ kỹ thuật (nếu cần) |
| :--- | :--- | :--- | :--- |
| `Revision v42 · Epoch 3 · Môi trường mô phỏng` | Tiêu đề phụ Control Room | `Phiên bản trạng thái #42` *(ẩn Epoch & nhãn mô phỏng vào Chẩn đoán / Dev Inspector)* | Ngăn kéo **Chẩn đoán kỹ thuật** & Nhật ký lệnh |
| `PlaybackCompleted ACK` / `Playback ACK` | Control Room, Báo cáo phiên | `Đã phát xong tới người xem` *(chú thích phụ: xác nhận phát thực tế, không tính lúc mới tạo giọng)* | Tooltip nguồn đo & tệp xuất CSV kiểm toán |
| `Chỉ can thiệp trước khi COMMITTED` | Hàng đợi câu hỏi (Control Room) | `Chỉ bỏ qua trước khi AI bắt đầu đọc` | Nhật ký lệnh kỹ thuật |
| `Publisher ổn định` | Thanh trạng thái Control Room | `Đường truyền phát ổn định` | Ngăn kéo **Chẩn đoán kỹ thuật** |
| `Đồng bộ realtime` | Thanh trạng thái Control Room | `Kết nối điều khiển ổn định` | Ngăn kéo **Chẩn đoán kỹ thuật** |
| `Time-bucketed SVG` | Thẻ biểu đồ Báo cáo | `Theo khung 15 phút` *(hoặc bỏ badge)* | Không cần hiển thị trên UI |
| `Báo cáo hoàn chỉnh (READY)` / `Dữ liệu một phần (PARTIAL)` / `Đang tổng hợp (PENDING)` | Trang Báo cáo | `Báo cáo đã hoàn chỉnh` / `Báo cáo đang thiếu một phần dữ liệu` / `Đang tổng hợp báo cáo` | Cột mã trạng thái trong CSV xuất ra |
| `Chính sách bất biến (IM-D3)` | Quản lý Lời mời | `Thông số cố định sau khi tạo` | Tài liệu kỹ thuật (không cần trên UI) |
| `(SR-D2)`, `(SR-D5)`, `(VR-D3)` | Banner trang Báo cáo & Viewer | **Gỡ hoàn toàn mã tài liệu nội bộ** khỏi câu thông báo người dùng | Tài liệu thiết kế / test cases |
| `Nguồn kiểm tra: P04 · Media Controller`, `P09 · OCOP Eligibility`, `P11 · Rights Registry` | Trang Kiểm tra sẵn sàng & Báo cáo | `Nguồn kiểm tra: Hạ tầng phát sóng`, `Hệ thống xác minh OCOP`, `Hệ thống xác nhận quyền hình ảnh` | Tooltip kỹ thuật / Chẩn đoán |
| `Thiết lập Workspace & Bắt đầu nhanh` | Trang Onboarding | `Thiết lập không gian làm việc` | Không cần tiếng Anh |
| `Tiến bước phát kế tiếp (Mock ACK)` | Control Room | Di dời toàn bộ vào **Dev Inspector** (không hiện trong giao diện merchant) | Chỉ trong `DevScenarioBar` / Dev Inspector |
| `Mô phỏng Media suy giảm`, `Mô phỏng xung đột 409`, `Mô phỏng Video Buffering` | Control Room & Viewer Room | Di dời toàn bộ vào **Dev Inspector** | Chỉ trong `DevScenarioBar` / Dev Inspector |

---

## 2. Nguyên tắc không được phép đánh đổi khi Việt hóa

1. Không được rút gọn làm người dùng hiểu nhầm **`Tạm dừng AI`** là **`Dừng phiên livestream`** — luôn giữ rõ 2 trạng thái tách biệt: *"Phiên đang phát trực tiếp"* và *"AI đang tạm dừng"*.
2. Không được hiển thị **`Đã gửi yêu cầu chuyển sản phẩm`** như thể sản phẩm đang bán đã đổi ngay — phải ghi rõ *"Đang chờ chuyển sang [Tên sản phẩm] sau câu hiện tại"*.
3. Không được thay **`N/A`** bằng số **`0`** hoặc xóa lý do thiếu dữ liệu — phải viết dễ hiểu: *"Chưa có dữ liệu (N/A) — Chưa đủ tín hiệu đo trong phiên này"*.
