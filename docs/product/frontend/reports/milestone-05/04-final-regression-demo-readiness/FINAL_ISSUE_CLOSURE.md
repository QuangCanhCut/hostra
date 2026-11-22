# HOSTRA AI — Báo cáo Đóng Vấn đề UI/UX Cuối cùng (UX-01 → UX-22)

**Nguồn gốc danh sách:** [ISSUE_REGISTER.md](../01-ui-ux-audit/ISSUE_REGISTER.md) (M05.1 — 22 vấn đề: `0 P0 · 8 P1 · 10 P2 · 4 P3`)  
**Trạng thái tổng hợp sau M05.4:** **22/22 RESOLVED (100%)**  

> [!IMPORTANT]
> **Hiệu đính tính nhất quán từ M05.3:** Trong báo cáo Exit Gate M05.3 trước đây, 4 vấn đề còn lại (`UX-04`, `UX-06`, `UX-13`, `UX-15`) từng bị mô tả chung là P2/P3, trong khi `ISSUE_REGISTER.md` gốc phân loại **`UX-04` là P1** và **`UX-06` là P1**. Tài liệu này khôi phục và giữ nguyên **100% mức độ nghiêm trọng gốc** của cả 22 vấn đề, đồng thời chỉ đánh dấu `RESOLVED` sau khi có bằng chứng kiểm thử tự động và ảnh chụp xác minh thực tế trong M05.4.

---

## Bảng tổng hợp theo mức độ nghiêm trọng gốc

| Mức độ gốc (M05.1) | Tổng số | Đã đóng ở M05.2–M05.3 | Đã đóng hoàn tất ở M05.4 | Còn mở |
| :---: | :---: | :---: | :---: | :---: |
| **P0 (Blocker)** | 0 | 0 | 0 | 0 |
| **P1 (Critical UX/A11y)** | 8 | 6 | 2 (`UX-04`, `UX-06`) | **0** |
| **P2 (Major UX)** | 10 | 8 | 2 (`UX-13`, `UX-15`) | **0** |
| **P3 (Minor Polish)** | 4 | 4 | 0 | **0** |
| **Tổng cộng** | **22** | **18** | **4** | **0** |

---

## Chi tiết trạng thái đóng từng vấn đề (`UX-01` → `UX-22`)

| ID | Mức độ gốc | Mô tả tóm tắt | Milestone đóng | Bằng chứng xác minh cuối cùng (M05.4) | Trạng thái |
| :--- | :---: | :--- | :---: | :--- | :---: |
| **UX-01** | **P1** | Token Dark Mode bị thiếu trên Session Reports | M05.2 | Đã dùng toàn bộ `--border-default`, `--bg-surface`, `--bg-subtle`; xác minh trên Chromium Dark Mode | `RESOLVED` |
| **UX-02** | **P1** | Nút mô phỏng/debug lộ thẳng trong Control Room & Viewer Room | M05.2 + M05.3 | Tách vào `DevScenarioBar` / `Dev Inspector`, kiểm soát bằng `isDevInspectorAllowed()` | `RESOLVED` |
| **UX-03** | **P1** | Nút mở rộng Sidebar bị ép `16×32px` tại `1024px` | M05.2 | Kích thước chuẩn `36×36px`, không đè logo ở `1024×768` | `RESOLVED` |
| **UX-04** | **P1** | Lồng `<button>` trong `<a>` (`<Link><Button>`) trên Dashboard & các danh sách | **M05.4** | Chuyển toàn bộ sang `ButtonLink`; kiểm toán DOM trên 12 tuyến trang: **`totalNestedInteractive = 0`** (`m05_4_regression_evidence.json` & Vitest `m05-4-account-and-closure.test.tsx`) | `RESOLVED` |
| **UX-05** | **P1** | Thiếu Focus Trap & Focus Restoration trên Modal/Drawer | M05.2 + M05.3 | Đã xác minh giữ focus trong Modal/Drawer và trả focus về nút mở khi nhấn `Escape` | `RESOLVED` |
| **UX-06** | **P1** | Lộ mã kỹ thuật nội bộ (`P04`, `P09`, `P11`, `AW-D2`, `IM-D3`, `LiveKit Presence Telemetry`) | **M05.4** | Đã thay bằng tiếng Việt thân thiện trên Reports, Readiness, Onboarding, Invites (`PO-D02`); xác minh bằng Vitest + Chromium + [04-report-friendly-m054.png](./screenshots/04-report-friendly-m054.png) & [05-readiness-friendly-m054.png](./screenshots/05-readiness-friendly-m054.png) | `RESOLVED` |
| **UX-07** | **P1** | Nhãn `Đã đo` trong KPI Reports bị vỡ xuống 2 dòng | M05.2 | `StatusBadge` dùng `whitespace-nowrap shrink-0`; xác minh tại [04-report-friendly-m054.png](./screenshots/04-report-friendly-m054.png) | `RESOLVED` |
| **UX-08** | **P1** | Viewer Room thiếu `<h1>`, có ảnh lỗi, nút âm thanh nhỏ `<44px` | M05.2 | Có `<h1>`, `brokenImageCount = 0`, nút âm thanh `h-11 w-11` (`44×44px`); xác minh tại [07-viewer-mobile-m054.png](./screenshots/07-viewer-mobile-m054.png) | `RESOLVED` |
| **UX-09** | **P2** | Quá nhiều badge trạng thái ở thanh trên Control Room | M05.2 | Gom trạng thái ổn định thành pill gọn, tự bung cảnh báo khi `DEGRADED`/`STALE` | `RESOLVED` |
| **UX-10** | **P2** | Lặp nút `Chuyển SKU` 2 lần trong Control Room | M05.2 | Giữ 1 điểm kích hoạt rõ ràng trên thanh Control Bar | `RESOLVED` |
| **UX-11** | **P2** | Sticky Control Bar che nội dung cuối trang khi cuộn | M05.2 + M05.3 | Đã bổ sung khoảng đệm đáy và kiểm chứng vị trí sticky tại [06-control-room-m054.png](./screenshots/06-control-room-m054.png) | `RESOLVED` |
| **UX-12** | **P2** | Readiness không đưa mục Bị chặn / Đang chờ lên đầu | M05.2 | Sắp xếp ưu tiên `BLOCKED` → `PENDING` → `PASS` | `RESOLVED` |
| **UX-13** | **P2** | Mật độ badge màu quá dày (15 badge) trên Dashboard | **M05.4** | Áp dụng `StatusBadge subtle` cho trạng thái bình thường/phụ (`PO-D03`); xác minh trực quan ở [02-dashboard-light-m054.png](./screenshots/02-dashboard-light-m054.png) & [03-dashboard-dark-m054.png](./screenshots/03-dashboard-dark-m054.png) | `RESOLVED` |
| **UX-14** | **P2** | Thanh `DevScenarioBar` mặc định hiện đè góc phải màn hình | M05.2 + M05.3 | Mặc định ẩn, chỉ bật qua `?devTools=1` hoặc `Ctrl+Shift+D` trong môi trường cho phép | `RESOLVED` |
| **UX-15** | **P2** | Vùng chạm/bấm nhỏ trên các nút/liên kết hành động phụ | **M05.4** | Nâng vùng bấm tối thiểu `min-h-9`/`min-h-10` kèm padding trên Dashboard, Reports, Topbar, Products, Knowledge, Story; `0px` tràn ngang trên 7 viewport | `RESOLVED` |
| **UX-16** | **P2** | Cổng xác nhận quyền (`Rights Subject Portal`) có nút `Về Studio` không phù hợp | M05.2 | Đã gỡ nút `Về Studio`, bổ sung hướng dẫn quyền thu hồi rõ ràng | `RESOLVED` |
| **UX-17** | **P2** | Lặp chuỗi kỹ thuật `IM-D3` trên trang Lời mời | M05.2 + **M05.4** | Đã gỡ sạch `IM-D3` trên cả danh sách thẻ lẫn phụ đề Drawer tạo lời mời | `RESOLVED` |
| **UX-18** | **P2** | Cột tài liệu nguồn trên Knowledge Review bị trôi khi cuộn | M05.2 | Đặt cột nguồn `lg:sticky lg:top-20` dễ đối chiếu | `RESOLVED` |
| **UX-19** | **P3** | Hộp icon sản phẩm quá chói trên Dark Mode Viewer Room | M05.2 | Chuyển sang `var(--bg-subtle)` hài hòa nền tối | `RESOLVED` |
| **UX-20** | **P3** | Badge kỹ thuật `Time-bucketed SVG` trên biểu đồ Reports | M05.2 | Đổi thành `"Theo khung 15 phút"` | `RESOLVED` |
| **UX-21** | **P3** | Tiêu đề Onboarding trộn tiếng Anh/Việt | M05.2 + **M05.4** | Đổi thành `"Thiết lập không gian làm việc"` và bỏ `AW-D2` | `RESOLVED` |
| **UX-22** | **P3** | Nút thu gọn Sidebar desktop chỉ `32×32px` | M05.2 | Tăng kích thước lên `36×36px` (`h-9 w-9`) | `RESOLVED` |
