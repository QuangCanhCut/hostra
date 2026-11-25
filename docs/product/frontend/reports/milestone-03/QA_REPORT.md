# HOSTRA AI — Frontend Milestone 03 QA & Visual Verification Report

- **Ngày kiểm thử:** 21/11/2026
- **Nhánh Git:** `feat/frontend-foundation`
- **Công cụ kiểm thử:** Vitest `v3.2.7` + React Testing Library + MSW (`22/22` tests) · Playwright Chromium (`6/6` E2E specs · `13` full-page screenshots)
- **Thư mục minh chứng:** `docs/product/frontend/reports/milestone-03/screenshots/`

---

## 1. Ma trận kiểm thử tự động & Visual QA

| ID | Nhóm / Module | Kịch bản kiểm thử | Viewport & Theme | Vai trò | Kết quả mong đợi | Kết quả thực tế | Trạng thái | Minh chứng |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **QA-01** | Addendum #1 (SKU Picker) | Mở `/studio/sessions/new`, đợi tải catalog mock | `1920×1080` Light | Owner | Hiển thị đủ `Kho sản phẩm (5 SKU)`, không bao giờ hiện `0 SKU`, badge `Đạt số lượng 2–5` khớp 3/5 SKU | Khớp 100%, không overflow | **PASS** | `01-addendum-sku-picker-fixed-1920-light.png` (`1920×1080`) |
| **QA-02** | Addendum #2 (Presenter A/B) | Mở `/studio/presenters/prs-linh-01` | `1440×900` Dark | Owner | Tách rõ `Bản A · v1` / `Bản B · v2` kèm disclaimer xem trước tĩnh | Hiển thị sắc nét, tương phản đạt | **PASS** | `02-addendum-presenter-ab-1440-dark.png` (`1440×900`) |
| **QA-03** | M03-A (Control Room — Light) | Mở `/studio/sessions/ses-014/control`, bấm `Tạm dừng AI` | `1440×900` Light | Owner | Bố cục 60/40, 5 trục trạng thái độc lập; `PAUSE_AI` giữ nguyên `Đang phát trực tiếp`, nút đổi sang `Tiếp tục AI` | Khớp 100%, không tràn ngang | **PASS** | `03-control-room-live-1440-light.png` (`1440×1149`) |
| **QA-04** | M03-A (Control Room — Dark) | Mở `/studio/sessions/ses-014/control` chế độ tối | `1440×900` Dark | Owner | Dark surface `#0B1322`/`#121F32`, nhãn `Môi trường mô phỏng` rõ ràng | Khớp 100% | **PASS** | `04-control-room-live-1440-dark.png` (`1440×1149`) |
| **QA-05** | M03-A (Control Room — Tablet Operator) | Mở `/studio/sessions/ses-014/control` với vai trò Operator | `768×1024` Light | Operator | Operator được phân công xem và thao tác bình thường, layout co giãn 1 cột sạch | Không tràn ngang (`overflow <= 2px`) | **PASS** | `05-control-room-operator-768-light.png` (`768×1624`) |
| **QA-06** | M03-B (Members & Permissions) | Owner xem N:N assignments (Lan & Bình); Operator bị chặn | `1440×900` Light | Owner & Operator | Owner thấy đầy đủ danh bạ & phân công; Operator thấy EmptyState hạn chế quyền | Khớp 100% (Vitest + Playwright) | **PASS** | `06-members-owner-1440-light.png` (`1440×900`) |
| **QA-07** | M03-C (Invites & Real QR) | Owner xem nhiều named links + mã QR thật trên `/studio/sessions/ses-014/invites`; Operator không có nút Tạo/Thu hồi | `1440×900` Light | Owner & Operator | Mã QR sắc nét gắn đúng URL `/live/ses-014?invite=ml014-doitac`, có nút Sao chép & Tải PNG | Khớp 100% | **PASS** | `07-invites-qr-1440-light.png` (`1440×900`) |
| **QA-08** | M03-D (Viewer Entry — Mobile) | Mở `/live/ses-014?invite=ml014-doitac` | `390×844` Light | Viewer | Không có Merchant AppShell, hiển thị form nhập biệt danh & nút `Vào phòng livestream` | Khớp 100%, 0 phần tử điều hướng Studio | **PASS** | `08-viewer-entry-390-light.png` (`390×844`) |
| **QA-09** | M03-D (Viewer Live — Mobile 390) | Nhập biệt danh `Minh Khang` → Vào phòng | `390×844` Light | Viewer | Video trên + Active SKU `OCOP đã xác minh` + luồng bình luận & ô nhập dưới | Khớp 100% | **PASS** | `09-viewer-live-390-light.png` (`390×851`) |
| **QA-10** | M03-D (Viewer Live — Mobile 375 Dark) | Mở phòng xem trên màn hình nhỏ nhất `375×812` Dark Mode | `375×812` Dark | Viewer | Không tràn ngang, nút gửi & chữ tương phản tốt | Khớp 100% | **PASS** | `10-viewer-live-375-dark.png` (`375×842`) |
| **QA-11** | M03-E (Reports History) | Mở `/studio/reports` | `1440×900` Light | Owner | Liệt kê lịch sử phiên kèm bộ lọc trạng thái & badge sẵn sàng báo cáo | Khớp 100% | **PASS** | `11-reports-history-1440-light.png` (`1440×900`) |
| **QA-12** | M03-E (Session Report — PARTIAL & N/A) | Mở `/studio/sessions/ses-013/report` | `1440×900` Light | Owner | Hiển thị `PARTIAL`, thẻ `Người xem đồng thời` hiện `N/A` + lý do (không hiện `0`), biểu đồ SVG + Timeline + phễu `PlaybackCompleted ACK` | Khớp 100% | **PASS** | `12-session-report-owner-1440-light.png` (`1440×1340`) |
| **QA-13** | M03-E (Session Report — Operator Reduced & Export Security) | Mở `/studio/sessions/ses-013/report` (Operator Dark) + unit test CSV/PDF | `1440×900` Dark | Operator & Owner | Operator thấy banner bản rút gọn, không có nút Xuất CSV/PDF; `sanitizeCsvCell` vô hiệu hóa `=,+,-,@`; `buildSummaryPdfBlob` sinh `%PDF-1.4...%%EOF` | Khớp 100% | **PASS** | `13-session-report-operator-1440-dark.png` (`1440×1460`) |
| **QA-14** | Hồi quy M01 & M02 | Chạy toàn bộ `tests/dashboard.test.tsx` (7) và `tests/m02-workflows.test.tsx` (9) | jsdom (Vitest) | Owner & Operator | Không phá vỡ tính năng M01/M02 nào | 16/16 PASS | **PASS** | Vitest log (`22/22 passed`) |

---

## 2. Xác minh kích thước thực tế 13 ảnh minh chứng PNG

Tất cả 13 ảnh PNG trong `docs/product/frontend/reports/milestone-03/screenshots/` đã được kiểm tra header PNG thực tế:
- `01-addendum-sku-picker-fixed-1920-light.png`: `1920×1080` (132.0 KB)
- `02-addendum-presenter-ab-1440-dark.png`: `1440×900` (248.2 KB)
- `03-control-room-live-1440-light.png`: `1440×1149` (441.9 KB)
- `04-control-room-live-1440-dark.png`: `1440×1149` (446.6 KB)
- `05-control-room-operator-768-light.png`: `768×1624` (278.4 KB)
- `06-members-owner-1440-light.png`: `1440×900` (89.5 KB)
- `07-invites-qr-1440-light.png`: `1440×900` (107.6 KB)
- `08-viewer-entry-390-light.png`: `390×844` (23.7 KB)
- `09-viewer-live-390-light.png`: `390×851` (130.0 KB)
- `10-viewer-live-375-dark.png`: `375×842` (122.3 KB)
- `11-reports-history-1440-light.png`: `1440×900` (101.1 KB)
- `12-session-report-owner-1440-light.png`: `1440×1340` (178.0 KB)
- `13-session-report-operator-1440-dark.png`: `1440×1460` (186.3 KB)

---

## 3. Ghi nhận quan sát nhỏ (Minor Visual Observations — Không chặn nghiệm thu)
- **Sticky Control Bar trong ảnh chụp toàn trang (`fullPage: true`):** Trên `03-control-room-live-1440-light.png` và `04-control-room-live-1440-dark.png`, thanh điều khiển ghim đáy (`position: fixed; bottom: 0`) xuất hiện ở vị trí `900px` (mép dưới viewport đầu tiên) khi Playwright ghép ảnh toàn trang cao `1149px`. Khi cuộn thực tế trên trình duyệt, thanh ghim luôn cố định sát mép dưới màn hình đúng thiết kế `CR-D3`.
- **Hạn chế phạm vi Mock:** Các kiểm thử đều chạy trên MSW mock API; các kiểm thử tích hợp LiveKit WebRTC, OIDC thực và concurrency trên nhiều kết nối WebSocket thực sẽ được thực hiện ở giai đoạn nối backend.
