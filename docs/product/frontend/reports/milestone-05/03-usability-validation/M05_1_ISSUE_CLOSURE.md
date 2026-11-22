# HOSTRA AI — Đối chiếu Đóng 22 Vấn đề M05.1 (`UX-01` → `UX-22`)

| Issue ID | Mức độ | Xử lý ở M05.2 | Xác minh ở M05.3 | Bằng chứng | Trạng thái cuối |
| :---: | :---: | :--- | :--- | :--- | :---: |
| **UX-01** | P1 | Sửa toàn bộ biến CSS sai tên ở Reports | Dark Mode Báo cáo không còn viền trắng chói | `02-ui-ux-refinement/screenshots/10-after-session-report-1440-dark.png` | **RESOLVED** |
| **UX-02** | P1 | Gom 4 nút mô phỏng Control Room vào Drawer `Chẩn đoán`, ẩn 2 nút mô phỏng Viewer | `hasMockBtn=false` trên cả 10/10 màn hình; thêm khóa production ở `useScenario.tsx` | `j06c-control-room-diagnostics-drawer-1440-light.png`, `j08-viewer-comment-sent-390-light.png` | **RESOLVED** |
| **UX-03** | P1 | Xếp nút mở rộng Sidebar xuống dưới logo khi thu gọn (`36×36px`) | Đo DOM tại `1024×768`: `expandWidth=36px` | `02-ui-ux-refinement/screenshots/06-after-readiness-1024-light.png` | **RESOLVED** |
| **UX-04** | P1 | Thêm `ButtonLink`, gỡ lồng `<Link><Button>` ở Reports, Readiness, Rights Portal | Sạch (`0`) ở Reports/Readiness/Control Room/Viewer; còn `4` cặp ở `DashboardPage` | `m05_3_results.json` (`1280x800-dashboard: nestedBtnInLink=4`) | **PARTIALLY RESOLVED** *(đưa sang M05.4)* |
| **UX-05** | P1 | Bổ sung Focus Trap, Focus Restoration, khóa body scroll cho `Modal` & `Drawer` | Playwright keyboard test: `focusInsideModal=true`, `focusRestored=true` | `m05_3_results.json` (`accessibility`) | **RESOLVED** |
| **UX-06** | P1 | Dọn `Revision/Epoch/COMMITTED/SR-D2/KC-D1/IM-D3/Time-bucketed SVG` | Giao diện chính thân thiện; còn vài chú thích nhỏ nguồn đo `P04/P09` dưới thẻ KPI | `j06a`, `j11` screenshots | **PARTIALLY RESOLVED** *(chờ PO duyệt ẩn `P04/P09`)* |
| **UX-07** | P1 | Thêm `whitespace-nowrap shrink-0` cho `StatusBadge` | Nhãn `Đã đo` trong 4 thẻ KPI nằm thẳng 1 dòng | `10-after-session-report-1440-dark.png` | **RESOLVED** |
| **UX-08** | P1 | Thêm `<h1>` Viewer LIVE, `loading="eager"`, nút âm thanh `44×44px` | `hasH1=true`, `brokenImgs=0`, nút âm thanh `44×44px` | `j08-viewer-comment-sent-390-light.png` | **RESOLVED** |
| **UX-09** | P2 | Rút gọn thanh trạng thái Control Room còn 1 hàng + dùng `subtle` cho trạng thái ổn định | Thanh trạng thái gọn, Video là tiêu điểm chính | `j06a-control-room-ai-paused-1440-light.png` | **RESOLVED** |
| **UX-10** | P2 | Bỏ lặp nút `Chuyển SKU` trên thẻ Active SKU, giữ 1 nút ở Control Bar | Chỉ còn 1 nút `Chuyển SKU` duy nhất, J06 PASS | `j06b-control-room-pending-switch-1440-light.png` | **RESOLVED** |
| **UX-11** | P2 | Tăng đệm đáy `pb-10` cho Control Room | Đo DOM khi cuộn đáy: `lastSkipBottom=656 < barTop=775` | `m05_3_results.json` (`stickyCheck`) | **RESOLVED** |
| **UX-12** | P2 | Tự động đẩy mục `Bị chặn`/`Đang chờ` lên đầu trang Readiness kèm nền nhấn dịu | Mục chặn hiện đầu tiên tại `1280×800` | `j05-readiness-blocked-1280-light.png` | **RESOLVED** |
| **UX-13** | P2 | Thêm biến thể `subtle` cho `StatusBadge` | Dashboard chưa áp dụng `subtle` cho hết các badge phụ | `01-after-dashboard-1440-light.png` | **PARTIALLY RESOLVED** *(đưa sang M05.4)* |
| **UX-14** | P2 | Ẩn mặc định `DevScenarioBar`, khóa trên domain production | Không hiện `Mock: Owner` ở chế độ mặc định | `01-after-dashboard-1440-light.png` | **RESOLVED** |
| **UX-15** | P2 | Nâng chiều cao tối thiểu nút lọc/đóng modal lên `36–40px` | Một số link văn bản nhỏ ở bảng Products/Dashboard vẫn giữ chiều cao text dòng đơn | `m05_3_results.json` | **PARTIALLY RESOLVED** *(đưa sang M05.4)* |
| **UX-16** | P2 | Bỏ nút `Về Studio` khỏi `RightsConsentPortalPage` | `noStudioLink=true` tại `390×844` | `j10-rights-consent-390-light.png` | **RESOLVED** |
| **UX-17** | P2 | Đổi `Chính sách bất biến (IM-D3)` → `Thông số cố định sau khi tạo` | Không còn chuỗi `IM-D3` trên trang Lời mời | `j07-invites-qr-1440-light.png` | **RESOLVED** |
| **UX-18** | P2 | Giữ cột tài liệu nguồn `sticky top-20` & gỡ mã `(KC-D1–KC-D5)` | Cột nguồn cố định khi cuộn duyệt claim trên Dark Mode | `j03-knowledge-blocked-claim-1440-dark.png` | **RESOLVED** |
| **UX-19** | P3 | Làm dịu `ProductThumb` trên Dark Mode (`dark:opacity-90`) | Hài hòa hơn với nền tối Viewer Room | `09-after-viewer-live-390-dark.png` | **RESOLVED** |
| **UX-20** | P3 | Đổi `Time-bucketed SVG` → `Theo khung 15 phút` | `hasMockBtn=false`, nhãn dễ hiểu | `10-after-session-report-1440-dark.png` | **RESOLVED** |
| **UX-21** | P3 | Đổi `Thiết lập Workspace & Bắt đầu nhanh` → `Thiết lập không gian làm việc` | Xác minh trong J01 | `j01-onboarding-saved-1440-light.png` | **RESOLVED** |
| **UX-22** | P3 | Tăng nút thu gọn Sidebar desktop lên `36×36px` | Đạt `36×36px` | `Sidebar.tsx` | **RESOLVED** |

**Tổng hợp trạng thái 22 issues M05.1:** **18 RESOLVED · 4 PARTIALLY RESOLVED (`UX-04`, `UX-06`, `UX-13`, `UX-15`) · 0 OPEN P0/P1 · 0 NOT VERIFIED**.
