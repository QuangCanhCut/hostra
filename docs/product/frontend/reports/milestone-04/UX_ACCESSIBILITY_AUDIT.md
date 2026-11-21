# HOSTRA AI — UX & Accessibility Audit Report (Milestone 04)

- **Ngày kiểm toán:** 21/11/2026
- **Chuẩn đối chiếu:** **HOSTRA UI Redesign v0.4 — APPROVED**, **Global Design System v0.2**, **WCAG 2.2 AA**

---

## 1. Kiểm tra Responsive theo Breakpoints

| Breakpoint | Màn hình kiểm tra trọng điểm | Kết quả Overflow (`scrollWidth - clientWidth`) | Đánh giá bố cục |
| :--- | :--- | :---: | :--- |
| **`320×568`** | Viewer Invite Entry (`/live/ses-014`) | `<= 2px` (**PASS**) | Card nhập biệt danh co giãn gọn, nút CTA toàn chiều rộng, không cắt chữ |
| **`360×800`** | Viewer Invite Revoked | `<= 2px` (**PASS**) | Thông báo lỗi thu hồi rõ ràng, dễ đọc |
| **`375×812`** | Viewer Live Room Dark Mode | `<= 2px` (**PASS**) | Video 16:9 giữ nguyên tỷ lệ, Product Card & Comment Composer không che nhau |
| **`390×844`** | Viewer Entry, Waiting Room, LIVE, Ended | `<= 2px` (**PASS**) | Tách hoàn toàn khỏi Merchant AppShell, đạt mục tiêu mobile-first |
| **`768×1024`** | Merchant Dashboard & Live Control Room (Tablet) | `<= 2px` (**PASS**) | **Đã sửa M04-BUG-01:** Sidebar icon-only đúng `72px`, Control Bar `sticky bottom-0` nằm gọn `left=72px, width=696px`, không đè Sidebar |
| **`1024px+` / `1440×900`** | Toàn bộ Merchant Studio (Light & Dark) | `<= 2px` (**PASS**) | Bố cục 2 cột Control Room (60/40), 5 KPI cards Báo cáo, bảng dữ liệu `minCellWidth >= 64px` |
| **`1920×1080`** | Session Wizard SKU Picker | `<= 2px` (**PASS**) | Kho sản phẩm & danh sách chọn hiển thị đầy đủ sau khi tải dữ liệu |

---

## 2. Kiểm tra Accessibility (WCAG 2.2 AA) & Tương tác bàn phím

- **Màu sắc & Tương phản:**
  - Nút chính Primary CTA dùng nền Amber `#F5C430` với chữ Navy `#0F172A` (không dùng chữ trắng trên vàng).
  - Nút Destructive (`Dừng khẩn cấp`, `Xác nhận dừng ngay`) dùng `#DC2626` chữ trắng `#FFFFFF`.
  - Mọi `StatusBadge` đều đi kèm **icon + nhãn tiếng Việt rõ nghĩa** (không dựa duy nhất vào màu sắc).
- **Bàn phím & Dialogs:**
  - Các `Modal` (Emergency Stop, Stop Session, Export Report, Create Invite) hỗ trợ đóng bằng phím `Escape` (đã kiểm chứng bằng Playwright `page.keyboard.press('Escape')`).
  - Nút kéo-thả SKU trong `SessionWizardPage` có sẵn nút lên/xuống/xóa bằng bàn phím (`↑`, `↓`, xóa).
  - Các tab chi tiết trong `SessionReportPage` sử dụng đúng `role="tablist"`, `role="tab"`, `aria-selected`.
- **Console & Tài nguyên:**
  - Đã thêm inline SVG favicon vào `apps/web/index.html`, đạt **0 console errors / 0 404 assets** trên preview build.
- **Tách biệt Debug UI:**
  - `DevScenarioBar` ẩn sạch qua `?hideDevBar=1` và không nhồi thông tin debug vào các thành phần UI nghiệp vụ.

---

## 3. Giới hạn đã biết (Known Limitations — Mock Stage)

- **Bàn phím ảo di động thật (iOS Safari / Android Chrome):** Đã kiểm tra layout cố định tại `320px–390px` trên Chromium headless; hành vi `visualViewport` khi bàn phím ảo mở trên thiết bị iOS/Android vật lý cần kiểm tra bổ sung ở giai đoạn staging.
- **Font Google Fonts khi offline:** Trong môi trường không có internet, trình duyệt fallback mượt về `Inter, system-ui, sans-serif` không gây vỡ layout.
