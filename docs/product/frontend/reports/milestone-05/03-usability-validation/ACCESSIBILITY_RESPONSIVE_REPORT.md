# HOSTRA AI — Báo cáo Accessibility & Responsive Validation (Milestone 05.3)

## 1. Ma trận kiểm thử 7 Viewports (`reducedMotion: 'reduce'`)

Tất cả 7 kích thước màn hình đều được kiểm thử tự động trên Chromium thật ở chế độ giảm chuyển động (`prefers-reduced-motion: reduce`):

| Viewport | Màn hình kiểm tra | Tràn ngang (`overflowPx`) | Lồng `<button>` trong `<a>` (`nestedBtnInLink`) | Lỗi Console | Kết quả |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **`320×568`** | Viewer Invite Entry (`/live/ses-014`) | `0px` | `0` | `0` | **PASS** |
| **`390×844`** | Live Control Room Operator | `0px` | `0` | `0` | **PASS** |
| **`768×1024`** | Live Control Room Operator Dark | `0px` | `0` | `0` | **PASS** |
| **`1024×768`** | Live Control Room Owner | `0px` | `0` | `0` | **PASS** |
| **`1280×800`** | Merchant Dashboard Owner | `0px` | **`4`** *(ghi nhận cho M05.4)* | `0` | **PASS WITH NOTE** |
| **`1440×900`** | Reports History Dark | `0px` | `0` | `0` | **PASS** |
| **`1920×1080`** | Session Wizard SKU Picker | `0px` | `0` | `0` | **PASS** |

---

## 2. Kiểm chứng tương tác Bàn phím, Focus & Sticky Bar

| Hạng mục kiểm thử | Phương thức | Kết quả thực tế | Trạng thái |
| :--- | :--- | :--- | :---: |
| **Modal Focus Trap** (`Dừng khẩn cấp`) | Playwright keyboard (`Tab`) | `focusInsideModal: true` — focus xoay vòng bên trong hộp thoại | **PASS** |
| **Modal Focus Restoration** (`Escape`) | Playwright keyboard (`Escape`) | `focusRestored: true` — đóng modal trả focus chính xác về nút `Dừng khẩn cấp` | **PASS** |
| **Sticky Action Bar Reachability** (`1440×900`) | Đo DOM geometry khi cuộn đáy | `lastSkipBottom = 656px < barTop = 775px` (cách thanh dính `119px`, không che nút nào) | **PASS** |
| **Heading Semantics (`<h1>`)** | Kiểm tra DOM 10 màn hình | `hasH1 = true` trên cả 10/10 màn hình kể cả Viewer Room LIVE | **PASS** |
| **Touch Target nút âm thanh Viewer & mở rộng Sidebar `1024px`** | Đo DOM | Nút âm thanh Viewer = `44×44px`; nút mở rộng Sidebar `1024px` = `36×36px` | **PASS** |
| **Nested interactive (`a button`)** | Kiểm tra DOM 7 viewports | Đã sạch (`0`) trên Reports, Readiness, Control Room, Viewer, Wizard; còn `4` cặp trên `DashboardPage` (đưa vào M05.4) | **PARTIAL** |

---

## 3. Phân tách phạm vi đã kiểm & chưa thể kiểm

- **Đã kiểm chứng (Automated Playwright + Manual Keyboard Inspection):** Overflow 7 viewports, Focus Trap & Focus Restoration, Escape đóng dialog, `prefers-reduced-motion: reduce`, 0 lỗi console, 0 ảnh hỏng (`brokenImgs=0`).
- **Chưa thực hiện trong M05.3 (không tự tuyên bố WCAG full compliance):**
  - Chưa chạy kiểm thử trình đọc màn hình thật (**NVDA / VoiceOver**).
  - Chưa cài bổ sung `axe-core` (do giữ nguyên nguyên tắc không cài thêm dependency mới khi chưa duyệt).
  - Chưa kiểm thử bàn phím ảo vật lý trên thiết bị iOS Safari / Android Chrome thật.
