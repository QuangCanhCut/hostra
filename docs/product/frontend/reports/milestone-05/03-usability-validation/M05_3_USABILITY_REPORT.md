# HOSTRA AI — Báo cáo Đánh giá Khả năng Sử dụng (M05.3 Usability Report)

## 1. Trả lời 6 câu hỏi trọng tâm của M05.3 (Q1 → Q6)

| Câu hỏi | Kết luận | Bằng chứng thực tế |
| :---: | :---: | :--- |
| **Q1. Hiểu đang ở đâu & bước tiếp theo?** | **ĐẠT TỐT** | Breadcrumb, Sidebar rõ ràng; trang `Readiness` tự đẩy mục `Bị chặn / Đang chờ` lên đầu kèm nút chuyển thẳng tới trang xử lý. |
| **Q2. Hoàn thành trọn vẹn luồng chính từ đầu đến cuối?** | **ĐẠT (trên Mock)** | **11/11 hành trình (`J01`–`J11`) PASS** trên Chromium thật không gặp ngõ cụt (dead-end). |
| **Q3. Hiểu đúng trạng thái hệ thống & kết quả lệnh?** | **ĐẠT TỐT** | `PAUSE_AI` giữ rõ `Đang phát trực tiếp`; `SWITCH_SKU` hiện banner `Đang chờ chuyển sang...` giữ nguyên sản phẩm hiện tại; Báo cáo giữ trung thực `N/A`. |
| **Q4. Nhất quán Desktop / Tablet / Mobile & Light/Dark?** | **ĐẠT TỐT** | **7/7 viewports (`320px`–`1920px`)** có `overflow = 0px`, 0 lỗi console, Dark Mode Báo cáo không còn viền trắng chói. |
| **Q5. Còn lỗi điều hướng, A11y hay microcopy khó hiểu?** | **CÒN 3 ĐIỂM NHỎ (P2/P3)** | Còn 4 cặp `<Link><Button>` trên `DashboardPage`, chưa có Account Menu bấm được ở Avatar góc trên phải, và vài nguồn đo nhỏ ở KPI Báo cáo còn hiện mã `P04/P09`. |
| **Q6. Đủ ổn định để sang M05.4?** | **CÓ — CONDITIONAL GO** | Đủ ổn định về luồng, an toàn nghiệp vụ và responsive để sang **M05.4 (Final Regression & Demo Readiness)** kèm xử lý nốt 3 điểm nhỏ nêu trên. |

---

## 2. Đánh giá Heuristic Usability (8 tiêu chí)

> **Lưu ý trung thực:** Đánh giá dưới đây là **kiểm toán heuristic từ góc nhìn chuyên gia UX kết hợp kiểm thử tự động trên trình duyệt**, **KHÔNG phải** kết quả phỏng vấn người dùng thật (xem [HUMAN_USABILITY_TEST_PLAN.md](./HUMAN_USABILITY_TEST_PLAN.md) cho vòng kiểm thử người thật sắp tới).

| Tiêu chí Heuristic | Đánh giá | Điểm mạnh đã xác minh | Cơ hội cải thiện nhỏ (ưu tiên) |
| :--- | :---: | :--- | :--- |
| **1. Discoverability** (Dễ tìm chức năng) | Tốt | Thanh điều hướng tiếng Việt rõ ràng; Readiness đưa mục bị chặn lên đầu | **P2:** Avatar góc trên phải chưa có menu Đăng xuất / Thiết lập không gian làm việc |
| **2. Learnability** (Dễ hiểu lần đầu) | Khá tốt | Onboarding 4 bước rõ, Control Room & Viewer đã sạch bóng nút mô phỏng dev | **P3:** Một số chú thích nhỏ dưới thẻ KPI Báo cáo vẫn ghi `P04/P09` |
| **3. Task Efficiency** (Ít bước thừa) | Tốt | Lưu nháp nhanh, 1 nút `Chuyển SKU` duy nhất, `Dừng khẩn cấp` 1 bước xác nhận | **P3:** Có thể thêm lối tắt chuyển nhanh giữa Tab Báo cáo và Phòng điều khiển |
| **4. Feedback Clarity** (Phản hồi rõ) | Rất tốt | Phân biệt rõ `Đang chờ chuyển` vs `Đã áp dụng`, `AI tạm dừng` vs `Đang phát trực tiếp` | Giữ nguyên chuẩn hiện tại |
| **5. Error Recovery** (Khôi phục lỗi) | Tốt | Xung đột `409` hiển thị lý do & nút đồng bộ; Readiness dẫn thẳng tới trang sửa | **P2:** Cần kiểm thử thực tế với WebSocket đứt mạng thật khi nối Backend |
| **6. Cognitive Load** (Tải nhận thức) | Tốt | Control Room rút gọn còn 1 hàng trạng thái, 3 nhãn ổn định dùng viền nhẹ `subtle` | **P2:** Dashboard vẫn còn ~15 badge trạng thái, có thể tinh gọn thêm ở M05.4 |
| **7. Navigation Consistency** | Khá tốt | Sidebar `72px` tablet / `232px` desktop mượt; Viewer tách hẳn khỏi AppShell | **P2:** Thay nốt 4 `<Link><Button>` trên `DashboardPage` bằng `ButtonLink` |
| **8. Trust & Safety** | Rất tốt | Không giả lập số liệu `0` thay cho `N/A`; khóa nút Start với Operator; Dev Inspector bị khóa trên domain production | Cần giữ nguyên tuyệt đối khi nối Backend thật |

---

## 3. Các điểm cần Product Owner quyết định

1. **Menu Tài khoản (Account Dropdown) tại Avatar góc trên phải:** Đề xuất bổ sung menu chứa *Thông tin tài khoản*, *Thiết lập không gian làm việc* và *Đăng xuất → `/auth/sign-in`* ở M05.4 để hoàn thiện trải nghiệm demo luồng đăng nhập (`REQUIRES PRODUCT OWNER DECISION`).
2. **Ẩn hẳn mã `P04/P09` ở dòng nguồn đo dưới thẻ KPI Báo cáo:** Xác nhận có muốn thay thành tên tiếng Việt hoàn toàn (*Hệ thống quản lý phiên*, *Xác nhận phát thực tế*) hay giữ mã ngắn để đội kỹ thuật tra cứu.
3. **Tuyển 5–8 người dùng thật cho vòng Formative Usability Test:** Phê duyệt kế hoạch trong [HUMAN_USABILITY_TEST_PLAN.md](./HUMAN_USABILITY_TEST_PLAN.md).
