# HOSTRA AI — Kế hoạch Kiểm thử Khả năng Sử dụng với Người dùng thật (Human Usability Test Plan)

**Trạng thái kế hoạch:** `PLAN READY` *(Đã sẵn sàng tổ chức thực địa theo PO-D04)*  
**Trạng thái thực địa:** `PENDING HUMAN TEST` *(Chưa triển khai phỏng vấn người dùng thật; không có dữ liệu người dùng giả lập trong báo cáo này)*  
**Phiên bản áp dụng:** Frontend Mock MVP Baseline Candidate (sau M05.4)

---

## 1. Mục tiêu kiểm thử với người dùng thật
Xác minh các giả thuyết trải nghiệm mà kiểm thử tự động chưa thể thay thế:
1. Chủ cơ sở đặc sản/OCOP có hiểu rõ ranh giới **Xác minh OCOP độc lập**, **Quyền hình ảnh (Rights Consent)** và **Duyệt Tri thức** mà không cần hướng dẫn dài dòng không?
2. Người dùng có tự tìm thấy hành động ưu tiên trên **Dashboard**, mở **Account Menu**, kiểm tra **Readiness** và vận hành **Tạm dừng AI / Chuyển SKU / Dừng khẩn cấp** trong **Live Control Room** mà không nhầm lẫn giữa `Tạm dừng AI` và `Dừng livestream` không?
3. Khách xem phổ thông trên điện thoại có tự quét/mở link mời, nhập nickname và gửi bình luận thành công trong dưới 60 giây không?
4. Ngôn ngữ tiếng Việt sau tinh chỉnh `PO-D02` (Báo cáo phiên, Readiness, Onboarding) có thực sự dễ hiểu đối với người bán hàng không chuyên kỹ thuật không?

---

## 2. Tiêu chí tuyển chọn người tham gia (5–8 người)

| Nhóm vai trò | Số lượng mục tiêu | Tiêu chí tuyển chọn | Thiết bị kiểm thử |
| :--- | :---: | :--- | :--- |
| **Chủ hộ kinh doanh / HTX đặc sản OCOP (Owner)** | 3–4 người | Đang bán nông sản/thực phẩm đóng gói; từng hoặc muốn bán qua livestream; không chuyên CNTT | Laptop `1280×800` – `1440×900` |
| **Nhân viên vận hành bán hàng (Operator)** | 1–2 người | Thường trực bình luận/chăm sóc khách trong phiên live | Laptop hoặc Tablet `1024×768` |
| **Khách mua hàng phổ thông (Viewer)** | 1–2 người | Thường xem livestream mua hàng trên điện thoại | Điện thoại `375×812` – `390×844` |

---

## 3. Bộ nhiệm vụ kiểm thử (Task Scenarios — 35 phút / người)

| Mã nhiệm vụ | Vai trò | Kịch bản giao cho người dùng | Tiêu chí thành công |
| :--- | :---: | :--- | :--- |
| **T1** | Owner | Mở trang Tổng quan, tìm công việc cần xử lý gấp nhất và mở phần Thiết lập không gian làm việc từ góc tài khoản. | Tìm đúng mục ưu tiên < 30 giây; mở Account Menu và vào đúng `/studio/onboarding`. |
| **T2** | Owner | Kiểm tra danh mục sản phẩm OCOP và cho biết vì sao có sản phẩm chưa sẵn sàng phát live. | Phân biệt được sản phẩm `Chờ xác minh OCOP` với sản phẩm đã xác minh, không nhầm là lỗi hệ thống. |
| **T3** | Owner | Mở trang Kiểm tra sẵn sàng của một phiên bị chặn và xác định bước cần khắc phục. | Đọc hiểu đúng cổng đang `Bị chặn` ở đầu danh sách và bấm đúng nút đi tới trang khắc phục. |
| **T4** | Owner / Operator | Trong Phòng điều khiển livestream, tạm dừng AI trong khi vẫn giữ buổi phát sống, sau đó kiểm tra khu vực bình luận. | Bấm đúng `Tạm dừng AI`, hiểu phiên vẫn đang `LIVE`, không bấm nhầm `Dừng khẩn cấp`. |
| **T5** | Owner | Mở Báo cáo phiên `ses-013`, đọc 5 chỉ số KPI và giải thích vì sao ô "Người xem đồng thời cao nhất" ghi `N/A`. | Hiểu `N/A` là chưa đủ dữ liệu đo chứ không phải 0 người xem; hiểu các nguồn đo tiếng Việt. |
| **T6** | Viewer | Mở liên kết mời trên điện thoại, nhập tên hiển thị và gửi một câu hỏi về sản phẩm đang giới thiệu. | Vào phòng và gửi bình luận thành công < 60 giây, không bị lúng túng tìm nút gửi. |

---

## 4. Kịch bản điều phối (Moderator Script — Tóm tắt)
1. **Chào hỏi & Minh bạch bản Mock (3 phút):** Nhấn mạnh *"Chúng tôi đang kiểm thử phần mềm, không kiểm thử anh/chị. Đây là bản mô phỏng giao diện nên video và AI chưa chạy thật; mọi nhận xét dù nhỏ nhất đều rất quý."*
2. **Ký xác nhận đồng thuận (2 phút):** Xin phép ghi chú/ghi hình màn hình phục vụ cải tiến nội bộ.
3. **Thực hiện Think-Aloud (25 phút):** Giao lần lượt T1–T6. Điều phối viên **không** chỉ tay vào nút; chỉ đặt câu hỏi mở (*"Anh/chị kỳ vọng điều gì xảy ra khi bấm vào đây?"*).
4. **Đo SUS & Phỏng vấn ngắn sau phiên (5 phút):** Thu thang điểm SUS 10 câu (thang 1–5) và 3 câu hỏi mở:
   - *Màn hình nào khiến anh/chị cảm thấy rõ ràng nhất?*
   - *Từ ngữ hoặc nút bấm nào khiến anh/chị phải dừng lại suy nghĩ?*
   - *Nếu dùng hằng ngày để bán đặc sản, điều gì anh/chị muốn sửa đầu tiên?*

---

## 5. Mẫu phiếu đồng thuận & Phiếu quan sát

### 5.1. Mẫu xác nhận đồng thuận tham gia (Consent Summary)
- **Mục đích:** Thu thập phản hồi trải nghiệm cho bản mẫu giao diện HOSTRA AI.
- **Dữ liệu thu thập:** Ghi chú thao tác, thời gian hoàn thành, phản hồi phỏng vấn (ẩn danh khi tổng hợp báo cáo).
- **Quyền người tham gia:** Có quyền dừng bất cứ lúc nào và yêu cầu xóa ghi âm/ghi hình nếu có.

### 5.2. Mẫu phiếu quan sát (Observation Sheet — Trống, chờ thực địa)
| Mã người dùng | Vai trò | T1 | T2 | T3 | T4 | T5 | T6 | Điểm SUS | Vấn đề nổi bật & Trích dẫn nguyên văn |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `U-01` | Owner | *(Chờ thực địa)* | — | — | — | — | — | — | — |
| `U-02` | Owner | *(Chờ thực địa)* | — | — | — | — | — | — | — |
| `U-03` | Operator | *(Chờ thực địa)* | — | — | — | — | — | — | — |
| `U-04` | Viewer | *(Chờ thực địa)* | — | — | — | — | — | — | — |

---

## 6. Khung phân loại & ưu tiên phát hiện sau kiểm thử thực địa
- **Mức 1 — Blocker (Sửa ngay trước Pilot):** ≥ 2 người không hoàn thành nhiệm vụ cốt lõi hoặc hiểu sai trạng thái an toàn (`LIVE` vs `PAUSE_AI`, `OCOP`, `N/A`).
- **Mức 2 — High Friction (Sửa trong sprint tích hợp tiếp theo):** Hoàn thành nhiệm vụ nhưng ngập ngừng > 30 giây hoặc nhầm đường dẫn lần đầu.
- **Mức 3 — Polish (Đưa vào backlog cải tiến):** Góp ý nhỏ về cách diễn đạt, bố cục hoặc lối tắt tiện ích.
- **Ngưỡng mục tiêu chất lượng:** Tỷ lệ hoàn thành nhiệm vụ lõi ≥ 85% và điểm SUS trung bình ≥ 75/100.
