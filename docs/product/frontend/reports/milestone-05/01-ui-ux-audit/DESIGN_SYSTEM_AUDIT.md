# HOSTRA AI — Kiểm toán Hệ thống Thiết kế (Design System Audit — M05.1)

Đối chiếu trực tiếp `apps/web/src/styles/tokens.css` và các component dùng chung với **HOSTRA UI Redesign v0.4 (APPROVED)** & **Global Design System v0.2**.

---

## 1. Bảng màu & Chế độ Sáng / Tối (Light & Dark Mode)

- **Tuân thủ nền tảng thương hiệu v0.4:** Đạt 100% các mã màu cốt lõi: Navy `#0F172A`, Amber CTA `#F5C430` (chữ Navy `#0F172A`, tuyệt đối không dùng chữ trắng trên vàng), Soft Yellow `#FBE580`, Destructive `#DC2626` (chữ trắng `#FFFFFF`), Light Canvas `#F7F9FC`, Dark Canvas `#0B1322`, Dark Card `#121F32`.
- **Phát hiện sai lệch Token nghiêm trọng (`UX-01` — P1):**
  - `tokens.css` định nghĩa bộ tên chuẩn: `--bg-surface`, `--bg-subtle`, `--border-default`, `--border-strong`, `--radius-card`, `--radius-input`, `--status-warning-fg`, `--status-danger-fg`, `--status-success-fg`.
  - Tuy nhiên `ReportsHistoryPage.tsx` và `SessionReportPage.tsx` lại tham chiếu các biến **chưa từng tồn tại** trong `tokens.css`: `--border-subtle`, `--surface-base`, `--surface-subtle`, `--radius-md`, `--radius-lg`, `--status-warning`, `--status-danger`, `--status-success`.
  - **Hệ quả thực tế (thấy rõ trên `16-session-report-owner-1440-dark-partial.png`):** Ở Dark Mode, khung banner `PARTIAL` và 5 ô phễu `AI & Bình luận` bị trình duyệt fallback viền về màu chữ trắng sáng chói, phá vỡ độ êm mắt của nền tối `#121F32`.
- **Lạm dụng màu vàng / màu trạng thái:** Màu vàng thương hiệu `#F5C430` được dùng đúng tiết chế cho CTA chính và biểu đồ cột. Tuy nhiên mật độ badge màu (xanh/vàng/đỏ/xanh dương) lên tới **14–18 badge/trang** ở Dashboard, Control Room và Reports làm phân tán sự chú ý.

---

## 2. Chữ viết & Phân cấp Typography

- **Phông chữ:** Sử dụng `Be Vietnam Pro` làm phông chính, fallback `Inter, sans-serif` — dấu tiếng Việt hiển thị đẹp, không lệch dòng.
- **Số liệu:** Đã dùng `tabular-nums` ở nhiều bảng và bộ đếm thời gian, nhưng nên áp dụng đồng nhất cho toàn bộ giá trị KPI ở trang Báo cáo và giá tiền sản phẩm.
- **Lỗi xuống dòng hẹp (`UX-07` — P1):** Trong `SessionReportPage.tsx`, lưới 5 cột KPI ở `1440px` khiến mỗi thẻ chỉ rộng ~210px; `StatusBadge` không có `whitespace-nowrap shrink-0` nên chữ `Đã đo` bị bẻ thành 2 dòng (`Đã` / `đo`) trông méo mó.

---

## 3. Thành phần dùng chung (Buttons, Cards, Badges, Modals, Drawers)

| Thành phần | Hiện trạng | Vấn đề cần chuẩn hóa ở M05.2 |
| :--- | :--- | :--- |
| **`Button.tsx`** | 4 biến thể (`primary`, `secondary`, `ghost`, `destructive`), 3 kích thước (`sm=36px`, `md=40px`, `lg=44px`), có `loading` và `disabled` | Thiếu biến thể/component `ButtonLink` dẫn đến tình trạng nhiều trang bọc `<Link><Button>` sai ngữ nghĩa HTML (`UX-04`). Trên mobile, `sm` (`36px`) hơi nhỏ cho thao tác chạm |
| **`StatusBadge.tsx`** | Luôn kèm icon + text, đủ 5 tone ngữ nghĩa | Thiếu `whitespace-nowrap shrink-0` làm vỡ dòng khi đặt trong thẻ hẹp (`UX-07`). Cần thêm biến thể `subtle` (không nền đặc) để giảm nhiễu thị giác trên trang có nhiều trạng thái |
| **`Card.tsx`** | Thống nhất `rounded-[12px]`, viền mảnh `--border-default`, bóng nhẹ | Một số màn hình (Reports, Control Room) lồng card trong card với viền tương đương nhau làm giảm phân cấp chính/phụ |
| **`Modal.tsx` & `Drawer.tsx`** | Có `role="dialog"`, `aria-modal="true"`, hỗ trợ đóng bằng phím `Escape` | Thiếu **focus trap**, thiếu **khôi phục focus** khi đóng và chưa khóa cuộn `body` (`UX-05`) |
| **`DevScenarioBar.tsx`** | Tách riêng tốt về mặt kiến trúc, hỗ trợ đổi role/scenario/reset | Mặc định hiển thị nổi góc dưới phải khi không truyền `?hideDevBar=1`; đồng thời nhiều nút mô phỏng khác lại bị viết rải rác trong Control Room và Viewer Room thay vì gom hết vào đây (`UX-02`, `UX-14`) |
