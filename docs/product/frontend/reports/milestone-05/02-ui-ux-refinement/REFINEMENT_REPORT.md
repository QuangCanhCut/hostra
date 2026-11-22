# HOSTRA AI — Báo cáo Triển khai Tinh chỉnh UI/UX (Milestone 05.2)

## 1. Danh sách tệp & thành phần đã chỉnh sửa

### Hệ thống Component dùng chung & Accessibility
- `apps/web/src/components/ui/Button.tsx` — Bổ sung component `ButtonLink` (tránh lồng `<button>` trong `<a>`), đồng bộ vòng focus `focus-visible:ring-2` cho mọi biến thể.
- `apps/web/src/components/ui/StatusBadge.tsx` — Thêm `whitespace-nowrap shrink-0` chống vỡ chữ 2 dòng (`Đã` / `đo`) và bổ sung biến thể `subtle` giảm nhiễu màu.
- `apps/web/src/components/ui/Modal.tsx` & `apps/web/src/components/ui/Drawer.tsx` — Bổ sung **Focus Trap**, **khôi phục focus** khi đóng, khóa cuộn `body` và tăng nút đóng lên `40×40px`.
- `apps/web/src/app/layouts/Sidebar.tsx` — Sửa layout header khi thu gọn (`72px`) ở `1024px`, đặt nút mở rộng xuống dưới logo đạt tròn `36×36px` (không còn bị ép còn `16×32px`).
- `apps/web/src/hooks/useScenario.tsx` — Ẩn mặc định `DevScenarioBar`, chỉ bật khi truyền `?devTools=1` hoặc nhấn phím tắt `Ctrl+Shift+D`.
- `apps/web/src/components/shared/PortraitAvatar.tsx` — Đổi ảnh chân dung sang `loading="eager"` (loại bỏ `brokenImgs: 1`) và làm dịu khung icon sản phẩm trên Dark Mode.

### Các màn hình nghiệp vụ
- `apps/web/src/features/control-room/pages/LiveControlRoomPage.tsx` — Dọn sạch subtitle kỹ thuật và 4 nút mô phỏng dev vào ngăn kéo **Chẩn đoán**, tinh gọn thanh trạng thái còn 1 hàng (dùng `subtle` cho trạng thái ổn định), bỏ lặp nút `Chuyển SKU`, Việt hóa `Nội dung AI sắp nói` & `Chỉ bỏ qua trước khi AI bắt đầu đọc`, tăng đệm đáy `pb-10`.
- `apps/web/src/features/viewer/pages/ViewerLiveRoomPage.tsx` — Gỡ 2 nút mô phỏng dev khỏi màn hình Khách xem (chỉ hiện khi bật `devTools`), bổ sung thẻ `<h1>` ngữ nghĩa, tăng nút âm thanh lên `44×44px`.
- `apps/web/src/features/reports/pages/SessionReportPage.tsx` & `ReportsHistoryPage.tsx` — Sửa 100% biến CSS sai tên (`--border-subtle` → `--border-default`, `--surface-base` → `--bg-surface`, `--surface-subtle` → `--bg-subtle`, `--radius-md` → `--radius-input`, `--status-*`), bỏ `Time-bucketed SVG` → `Theo khung 15 phút`, bỏ mã `(SR-D2)`/`(SR-D5)`, thay `<Link><Button>` bằng `ButtonLink`, dùng `tabular-nums`.
- `apps/web/src/features/live-session/pages/ReadinessPage.tsx` — Tự động đưa các cổng `Bị chặn` → `Đang chờ` lên đầu danh sách kèm nền nhấn dịu, thay `<Link><Button>` bằng `ButtonLink`.
- `apps/web/src/features/knowledge/pages/KnowledgeReviewPage.tsx` — Gỡ mã tài liệu nội bộ `(KC-D1–KC-D5)` và `P09` khỏi thông báo người bán hàng.
- `apps/web/src/features/invitations/pages/InvitesPage.tsx` — Đổi `Chính sách bất biến (IM-D3)` → `Thông số cố định sau khi tạo`.
- `apps/web/src/features/presenter/pages/RightsConsentPortalPage.tsx` — Gỡ nút `Về Studio` ngoài ngữ cảnh dành cho Chủ thể quyền.
- `apps/web/src/features/workspace/pages/OnboardingPage.tsx` — Việt hóa tiêu đề sang `Thiết lập không gian làm việc`.
- `apps/web/tests/e2e/m04-final-qa.spec.ts` — Cập nhật bước mở ngăn kéo `Chẩn đoán` trước khi bấm `Mô phỏng xung đột 409`.

---

## 2. Danh mục công cụ đã chuyển vào chế độ Dev-Only / Chẩn đoán

| Công cụ mô phỏng / thông số kỹ thuật | Vị trí trước M05.2 | Vị trí sau M05.2 |
| :--- | :--- | :--- |
| `Mô phỏng Media suy giảm`, `Mô phỏng mất kết nối`, `Mô phỏng xung đột 409`, `Tiến bước phát kế tiếp (Mock ACK)` | Nằm lộ thiên trong frame chính Control Room | Đã gom vào ngăn kéo **Chẩn đoán** (mục *Công cụ mô phỏng — Chỉ dành cho kiểm thử*) |
| `Revision v42 · Epoch 3 · Môi trường mô phỏng` | Tiêu đề phụ ngay đầu Control Room | Chuyển vào ngăn kéo **Chẩn đoán** |
| `Mô phỏng Video Buffering`, `Mô phỏng Mất kết nối bình luận` | Nằm giữa màn hình di động của Khách xem | Chỉ hiện khi bật `?devTools=1` hoặc phím tắt `Ctrl+Shift+D` |
| Thanh nổi `Mock: Owner / Operator` (`DevScenarioBar`) | Nổi cố định mặc định trên mọi trang | Ẩn mặc định; bật nhanh bằng `?devTools=1` hoặc phím tắt `Ctrl+Shift+D` |

---

## 3. Các điểm còn cần Product Owner review thêm (nếu muốn tinh chỉnh sâu hơn ở vòng sau)

1. **Nhãn nguồn đo trong thẻ KPI Báo cáo:** Hiện vẫn giữ tên hệ thống ngắn (`P09 Session Lifecycle`, `P04 PlaybackCompleted ACK`) trong chú thích nhỏ ở đáy thẻ để giữ tính truy xuất kiểm toán; nếu PO muốn ẩn hẳn mã `P04/P09` vào tooltip thì có thể tinh gọn thêm 1 bước nhẹ.
2. **Mật độ badge ở Dashboard (`DashboardPage`):** Đã chuẩn hóa `StatusBadge` không vỡ dòng và có biến thể `subtle`; có thể tiếp tục giảm thêm số badge phụ trên bảng Phiên gần đây nếu PO muốn tối giản hơn nữa.

---

## 4. Kết quả kiểm tra chất lượng

| Kiểm tra | Lệnh thực thi | Kết quả |
| :--- | :--- | :---: |
| **TypeScript** | `npm run typecheck` | **PASS (0 lỗi)** |
| **ESLint** | `npm run lint` | **PASS (0 lỗi, 0 cảnh báo)** |
| **Unit & Integration Tests** | `npm run test` (Vitest) | **PASS — 4/4 files · 27/27 tests** |
| **Production Build** | `npm run build` (`vite build`) | **PASS** (`index-D3apqgf0.js` = `395.20 kB` / `124.23 kB` gzip · 0 cảnh báo chunk) |
| **Kiểm chứng trình duyệt 10 màn hình After** | `m05_2_after_capture.mjs` (Chromium) | **PASS — 10/10 màn hình: 0 lỗi console, `overflowPx=0`, `brokenImgs=0`, `hasH1=true`, `hasMockBtn=false`** |
