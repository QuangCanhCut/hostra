# HOSTRA AI — Milestone 05.1: Kiểm toán UI/UX Toàn diện (CHỈ KIỂM TOÁN)

- **Ngày thực hiện:** 22/11/2026
- **Nhánh Git:** `feat/frontend-foundation` *(không chỉnh sửa bất kỳ mã nguồn nào trong `apps/web/`)*
- **Phạm vi:** Toàn bộ 14 nhóm màn hình Frontend Mock MVP (M01–M04) ở chế độ Sáng/Tối (Light/Dark), 4 vai trò người dùng (Chủ sở hữu, Vận hành viên, Chủ thể quyền hình ảnh, Khách xem), các kích thước màn hình từ `320px` đến `1920px`.
- **Chế độ thực hiện:** **AUDIT ONLY** — chỉ kiểm tra mã nguồn, chạy ứng dụng thực tế bằng Chromium (Playwright), đo đạc DOM/khả năng truy cập, chụp 16 ảnh minh chứng tươi mới và đề xuất lộ trình nâng cấp cho M05.2.

---

## 1. Mục tiêu của đợt kiểm toán

Đánh giá trung thực, dựa trên bằng chứng thực tế để trả lời câu hỏi: **Giao diện HOSTRA AI hiện tại cần cải thiện những gì để mang lại cảm giác của một sản phẩm SaaS thương mại tinh gọn, đáng tin cậy, dễ hiểu cho nhà bán hàng nông sản/OCOP Việt Nam — thay vì một bảng quản trị kỹ thuật dày đặc thông số?**

---

## 2. Phương pháp kiểm toán & Bằng chứng

1. **Đối chiếu tài liệu chuẩn:** Đọc và giữ nguyên thứ tự ưu tiên theo `AGENTS.md`, `DECISIONS.md`, **HOSTRA UI Redesign v0.4 (APPROVED)**, Global Design System v0.2 và các Design Package v0.2.
2. **Kiểm toán mã nguồn tĩnh (`apps/web/src/`):** Rà soát `tokens.css`, `AppShell`, `Sidebar`, `Button`, `Card`, `Modal`, `StatusBadge`, `DevScenarioBar` và các trang nghiệp vụ.
3. **Kiểm toán trình duyệt thực tế (Chromium + Vite Preview):** Chạy script kiểm toán tự động trên bản build thực (`apps/web/dist`) qua **16 màn hình đại diện**, đo trực tiếp:
   - Độ tràn ngang (`overflowPx`), tổng chiều cao cuộn (`scrollHeight`).
   - Số lượng badge hiển thị đồng thời trên 1 màn hình.
   - Các thuật ngữ kỹ thuật/nội bộ bị lộ ra giao diện người dùng.
   - Kích thước vùng chạm (`touch target < 40px` / `< 44px`), cấu trúc heading `<h1>`, ảnh lỗi, lỗi console và xung đột lớp phủ (`DevScenarioBar` vs `Control Bar`).
4. **Kiểm tra trực quan 16 ảnh chụp mới** tại thư mục [`screenshots/`](./screenshots/).

---

## 3. Danh mục hồ sơ báo cáo M05.1

| Tệp báo cáo | Nội dung chính |
| :--- | :--- |
| [UI_UX_AUDIT_REPORT.md](./UI_UX_AUDIT_REPORT.md) | Đánh giá tổng thể UI/UX, xác minh 8 giả thuyết H01–H08, phân tích góc nhìn 4 vai trò người dùng |
| [SCREEN_BY_SCREEN_REVIEW.md](./SCREEN_BY_SCREEN_REVIEW.md) | Đánh giá chi tiết từng màn hình trong 14 module kèm tuyến đường, điểm mạnh, vấn đề & ảnh minh chứng |
| [ISSUE_REGISTER.md](./ISSUE_REGISTER.md) | Sổ đăng ký **22 vấn đề** phân loại `P0/P1/P2/P3`, mức độ nỗ lực `S/M/L`, rủi ro hồi quy & yêu cầu duyệt PO |
| [DESIGN_SYSTEM_AUDIT.md](./DESIGN_SYSTEM_AUDIT.md) | Kiểm toán hệ thống thiết kế: lỗi token CSS bị thiếu ở trang Báo cáo, chữ, màu sắc, nút, thẻ, badge, Light/Dark |
| [RESPONSIVE_ACCESSIBILITY_AUDIT.md](./RESPONSIVE_ACCESSIBILITY_AUDIT.md) | Kiểm toán Responsive (`320px`–`1920px`) & WCAG 2.2 AA (focus trap, lồng `<button>` trong `<a>`, thiếu `<h1>`, touch target) |
| [UX_MICROCOPY_GLOSSARY.md](./UX_MICROCOPY_GLOSSARY.md) | Từ điển chuyển đổi thuật ngữ kỹ thuật sang tiếng Việt thân thiện cho nhà bán hàng (giữ nguyên ngữ nghĩa an toàn) |
| [IMPROVEMENT_BACKLOG.md](./IMPROVEMENT_BACKLOG.md) | Danh mục hạng mục cải tiến theo 3 nhóm: Quick Wins, Cải tiến cấu trúc UX, Cải tiến Design System |
| [PROPOSED_M05_2_PLAN.md](./PROPOSED_M05_2_PLAN.md) | Đề xuất kế hoạch triển khai M05.2 chia theo các gói nhỏ dễ nghiệm thu (chỉ là đề xuất, chưa thực thi) |
| [`screenshots/`](./screenshots/) | 16 ảnh chụp thực tế từ ứng dụng đang chạy |

---

## 4. Giới hạn của đợt kiểm toán

- Kiểm toán chạy trên bản **Frontend Mock MVP** (MSW in-memory) trên trình duyệt Chromium desktop/mobile emulation; chưa đo hành vi bàn phím ảo vật lý trên thiết bị iOS Safari / Android Chrome thật.
- Tương phản màu được đánh giá theo bảng màu token chuẩn (`tokens.css`) và kiểm tra trực quan; khi chuyển sang M05.2 nên chạy thêm kiểm tra tự động `axe-core` cho toàn bộ các trạng thái tương tác.
