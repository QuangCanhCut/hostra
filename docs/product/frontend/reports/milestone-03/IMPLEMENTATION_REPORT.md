# HOSTRA AI — Frontend Milestone 03 Implementation Report
## Livestream Operations, Viewer Experience, Permissions, Invitations, Reports & Post-M02 Addendum

- **Ngày báo cáo:** 21/11/2026
- **Nhánh Git:** `feat/frontend-foundation` *(chưa commit/push/merge tự động)*
- **Phạm vi mã nguồn:** `apps/web/` *(không sửa `apps/api/`, `experiments/`, `workers/`, `AGENTS.md`, `CLAUDE.md`, hoặc tài liệu gốc DOCX/PDF)*
- **Visual Baseline:** **HOSTRA UI Redesign v0.4 — APPROVED** (Light Mode & Dark Mode, tiếng Việt)
- **Môi trường:** **Frontend Mock-First (MSW + Canonical In-Memory Store)** — chưa kết nối backend thực, chưa phát LiveKit thật, không bao gồm TikTok/Shopee/OBS.

---

## 1. Tóm tắt điều hành (Executive Summary)

Milestone 03 đã hoàn thiện toàn bộ 5 module vận hành livestream & hậu kiểm của HOSTRA AI theo kiến trúc feature-based, nối liền mạch với nền tảng Milestone 01 và 6 module chuẩn bị tài sản của Milestone 02, đồng thời xử lý dứt điểm 4 hạng mục trong **M03 Addendum**:

1. **M03-A — Live Control Room (`/studio/sessions/:id/control`):** Bố cục 2 cột 60/40, thanh 5 trục trạng thái độc lập (`SessionLifecycle`, `AiExecutionState`, `MediaHealth`, `PublisherState`, `ConnectionFreshness`), `PAUSE_AI` giữ nguyên `LIVE`, `SWITCH_SKU` tách `ACCEPTED` (Pending) và `APPLIED`, `SKIP_PENDING` chỉ cho phép trước `COMMITTED`, `EMERGENCY_STOP` xác nhận 1 bước tách biệt, mô phỏng `409 Revision Conflict` và `PlaybackCompleted ACK`.
2. **M03-B — Members & Permissions (`/studio/members`):** Danh bạ thành viên, mời Vận hành viên qua email cá nhân có thời hạn, phân công N:N nhiều Vận hành viên trên cùng một phiên (Lan & Bình cùng phụ trách Phiên #014), thu hồi 1 người không ảnh hưởng người còn lại, nhật ký kiểm toán truy cập.
3. **M03-C — Invite Management & Real QR (`/studio/invites`, `/studio/sessions/:id/invites`):** Tạo nhiều liên kết mời đặt tên bất biến kèm thời hạn/giới hạn lượt vào, sinh mã QR thật bằng thư viện `qrcode` gắn đúng đường dẫn mời (không nhúng token nội bộ), tải PNG, thu hồi link ngắt quyền khách đang xem.
4. **M03-D — Viewer Live Room (`/live/:id`):** Giao diện mobile-first (`390×844`, `375×812`) đứng độc lập hoàn toàn **ngoài Merchant AppShell**, nhập biệt danh tham gia, phòng chờ khóa chat trước `LIVE`, bình luận với trạng thái gửi/nhận/từ chối, mô phỏng khôi phục video/chat độc lập, không có điều hướng merchant.
5. **M03-E — Session Reports & History (`/studio/reports`, `/studio/sessions/:id/report`):** Lịch sử phiên theo vai trò, 5 thẻ KPI có nguồn đo (hiển thị trung thực `N/A` + lý do khi thiếu telemetry, không thay bằng `0`), biểu đồ SVG lượt vào theo khung thời gian + dòng thời gian trạng thái, 3 tab chi tiết (`AI & Bình luận` theo `PlaybackCompleted ACK` khử trùng lặp, `Media & Độ ổn định`, `Nhật ký hoạt động`), xuất bất đồng bộ **CSV đã chống Formula Injection (`=`, `+`, `-`, `@`)** và **PDF 1.4 chuẩn** chỉ dành cho Chủ sở hữu.
6. **Addendum #1–#4:** Sửa triệt để lỗi SKU Picker tải bất đồng bộ (`0 SKU`), làm rõ nhãn A/B + disclaimer xem trước tĩnh trên Presenter Detail, thêm kiểm thử hồi quy M02 và tách bundle theo route với `React.lazy` + `Suspense` giảm entry chunk chính từ **564.95 kB xuống 394.43 kB (-30.2%)**.

---

## 2. Gate 0 — Xác minh Milestone 02 & Xử lý Addendum

### 2.1. Kết quả kiểm chứng nguồn M02
- Toàn bộ 6 module M02 (`presenter`, `products`, `knowledge`, `story-planner`, `live-session`, `workspace`) và 9/9 unit tests `tests/m02-workflows.test.tsx` + 7/7 unit tests `tests/dashboard.test.tsx` đều chạy xanh.
- Đã kiểm tra và xác nhận ảnh chân dung AI Presenter chân thực tại `apps/web/public/demo/presenters/{linh,mai,an}.jpg`.

### 2.2. Nguyên nhân gốc & Bản sửa lỗi SKU Picker (Addendum #1)
- **Nguyên nhân gốc (Root Cause):** Trong `apps/web/src/features/live-session/pages/SessionWizardPage.tsx`, màn hình không chờ `useProducts()` / `usePresenters()` hoàn tất tải dữ liệu mock (độ trễ ~60ms) trước khi render phần chọn SKU, nhưng lại tính badge `Đạt số lượng 2–5` dựa trên `selectedSkuIds.length` khởi tạo sẵn. Do đó trong khoảnh khắc tải, UI hiển thị `Kho sản phẩm (0 SKU)`, danh sách đã chọn rỗng, trong khi badge vẫn xanh.
- **Cách khắc phục:**
  - Hiển thị Skeleton tải dữ liệu khi `isLoadingPresenters || isLoadingProducts || (isEditing && isLoadingSession)`.
  - Tính toán số lượng SKU đã chọn và điều kiện hợp lệ `2–5 SKU` dựa trên `selectedProducts.length` thực tế sau khi khớp danh mục sản phẩm.
- **Xác minh:** Unit test `Addendum #1` trong `tests/m03-workflows.test.tsx` PASS và screenshot `01-addendum-sku-picker-fixed-1920-light.png` (`1920×1080`) hiển thị đầy đủ `Kho sản phẩm (5 SKU)` và `Sản phẩm trong phiên (3/5 SKU)`.

### 2.3. Cải thiện Presenter A/B (Addendum #2)
- Cập nhật `apps/web/src/features/presenter/pages/PresenterDetailPage.tsx`: tách rõ nhãn `Bản A · v1` và `Bản B · v2`, bổ sung chú thích minh họa tĩnh (*"Bản xem trước minh họa tĩnh..."*) để tránh hiểu nhầm là video stream thật. Xác minh qua screenshot `02-addendum-presenter-ab-1440-dark.png`.

### 2.4. Tách mã theo route bằng `React.lazy` + `Suspense` (Addendum #4)
Chuyển toàn bộ 23 trang tính năng trong `apps/web/src/app/router.tsx` sang `React.lazy` kèm `RouteFallback` (`apps/web/src/components/shared/RouteFallback.tsx`):

| Chỉ số Production Build (`vite build`) | M02 Baseline (Trước code-splitting) | M03 (Sau code-splitting + 5 module M03 + `qrcode`) | Chênh lệch |
| :--- | :---: | :---: | :---: |
| **Main Entry Chunk (`dist/assets/index-*.js`)** | `564.95 kB` (`156.95 kB` gzip) | **`394.43 kB` (`124.02 kB` gzip)** | **-170.52 kB (-30.2%) / -32.93 kB gzip (-21.0%)** |
| **Cảnh báo chunk > 500 kB của Vite** | Có cảnh báo | **0 cảnh báo** | Đã loại bỏ hoàn toàn |
| **Route Chunks M03 tiêu biểu** | N/A | `LiveControlRoomPage` 26.88 kB · `SessionReportPage` 23.61 kB · `InvitesPage` (+`qrcode`) 36.65 kB · `ViewerLiveRoomPage` 15.03 kB · `MembersPage` 12.06 kB | Tải lười theo tuyến |

---

## 3. Kiến trúc dữ liệu Mock & Đồng bộ trạng thái Canonical

- **Store hợp nhất:** `apps/web/src/mocks/m03.store.ts` liên kết trực tiếp với `getStore(scenario)` của `src/mocks/store.ts`.
  - Thay đổi phân công Operator tại **Members** cập nhật trực tiếp `assignedOperatorIds` trên `core.sessions`, ảnh hưởng ngay quyền thao tác tại **Live Control Room** và phạm vi hiển thị tại **Session Reports**.
  - Khách nhập biệt danh tại **Viewer Live Room** làm tăng `successfulAdmissions` của đúng Invite (idempotent khi refresh cùng `guestSessionId`), và bình luận gửi từ khách xuất hiện ngay trong **Live Control Room**.
  - Lệnh `STOP` / `EMERGENCY_STOP` chuyển trạng thái phiên sang `STOPPED`, cập nhật Viewer sang màn hình kết thúc phiên và phản ánh vào **Session Report**.
- **MSW Handlers:** `apps/web/src/mocks/m03.handlers.ts` đăng ký đầy đủ endpoints REST mock cho Members, Control Room commands/conflict/events, Invites/Revoke, Viewer admission/comments và Reports, đồng thời reset sạch qua `/api/mock/v1/reset` và `tests/setup.ts`.
- **Tiện ích xuất tệp thật:** `apps/web/src/lib/export-utils.ts` cài đặt:
  - `sanitizeCsvCell()` + `buildSanitizedAuditCsv()`: Thêm UTF-8 BOM và vô hiệu hóa mọi ô bắt đầu bằng `=`, `+`, `-`, `@`, `\t`, `\r` bằng dấu nháy đơn dẫn đầu.
  - `buildSummaryPdfBlob()`: Tạo tài liệu PDF 1.4 hợp chuẩn (`%PDF-1.4` ... `xref` ... `%%EOF`) chứa bảng KPI có nguồn đo và phễu `PlaybackCompleted ACK`.

---

## 4. Danh mục tệp đã thêm / chỉnh sửa

### Thêm mới (M03 Core & Features)
- `apps/web/src/types/m03.ts` — Kiểu dữ liệu domain & DTO cho toàn bộ 5 module M03.
- `apps/web/src/lib/export-utils.ts` — Sanitize CSV Formula Injection + trình sinh PDF 1.4 + tải tệp trình duyệt.
- `apps/web/src/mocks/m03.store.ts` & `apps/web/src/mocks/m03.handlers.ts` — Mock state engine & MSW REST handlers.
- `apps/web/src/components/shared/RouteFallback.tsx` — Skeleton fallback cho `Suspense`.
- `apps/web/src/features/members/{services/members.service.ts, hooks/useMembers.ts, pages/MembersPage.tsx}`
- `apps/web/src/features/control-room/{services/control-room.service.ts, hooks/useControlRoom.ts, pages/LiveControlRoomPage.tsx}`
- `apps/web/src/features/invitations/{services/invites.service.ts, hooks/useInvites.ts, components/QrCodePreview.tsx, pages/InvitesPage.tsx}`
- `apps/web/src/features/viewer/{services/viewer.service.ts, hooks/useViewerRoom.ts, pages/ViewerLiveRoomPage.tsx}`
- `apps/web/src/features/reports/{services/reports.service.ts, hooks/useReports.ts, pages/ReportsHistoryPage.tsx, pages/SessionReportPage.tsx}`
- `apps/web/tests/m03-workflows.test.tsx` & `apps/web/tests/e2e/m03-visual-qa.spec.ts`

### Chỉnh sửa (Addendum & Wiring)
- `apps/web/package.json` & `apps/web/package-lock.json` — Thêm `qrcode` và `@types/qrcode`.
- `apps/web/src/mocks/handlers.ts` — Nối `m03Handlers` và `resetM03Store`.
- `apps/web/src/app/router.tsx` — Áp dụng `React.lazy` + `Suspense`, gắn toàn bộ tuyến M03 và `/live/:id` ngoài `AppShell`.
- `apps/web/src/features/live-session/pages/SessionWizardPage.tsx` — Sửa lỗi SKU Picker loading/count sync (Addendum #1).
- `apps/web/src/features/presenter/pages/PresenterDetailPage.tsx` — Nhãn A/B rõ ràng + disclaimer xem trước tĩnh (Addendum #2).
- `apps/web/tests/setup.ts` — Thêm `resetM03Store('happy-path')` trong `afterEach`.

---

## 5. Kết quả kiểm tra chất lượng (Quality Gates)

| Kiểm tra | Lệnh thực thi | Kết quả |
| :--- | :--- | :---: |
| **TypeScript Check** | `npm run typecheck` (`tsc -b --noEmit`) | **PASS (0 lỗi)** |
| **ESLint** | `npm run lint` (`eslint .`) | **PASS (0 lỗi, 0 cảnh báo)** |
| **Unit & Integration Tests (Vitest)** | `npm run test` (`vitest run`) | **PASS (3/3 files · 22/22 tests: 7 M01 + 9 M02 + 6 M03+Addendum)** |
| **Production Build** | `npm run build` (`tsc -b && vite build`) | **PASS (5.55s · 0 cảnh báo chunk size)** |
| **Playwright E2E & Visual QA** | `npx playwright test tests/e2e/m03-visual-qa.spec.ts` | **PASS (6/6 suites · 13/13 screenshots · `overflow <= 2px`, `minCellWidth >= 64px`)** |

---

## 6. Ràng buộc an toàn & Phụ thuộc Backend còn mở (Chưa sẵn sàng Production)

> **Lưu ý quan trọng:** Đây là bản **Frontend Mock-First** chạy với MSW để đánh giá UI/UX và luồng vận hành. **Không tuyên bố đã kết nối backend thật hay sẵn sàng production.**

Các phụ thuộc backend cần chốt ở giai đoạn tích hợp tiếp theo:
1. **LiveKit Media & Subscribe-only Token:** Hiện Control Room & Viewer dùng hình ảnh minh họa tĩnh kèm nhãn `Môi trường mô phỏng (Không phát LiveKit thật)`. Cần backend cấp token LiveKit `subscribe-only` cho Viewer và ngắt kết nối tức thì khi thu hồi Invite (`IM-D4`).
2. **WebSocket Realtime & Command Arbitration:** Cần hợp đồng WS chính thức cho `expected_revision`, `session_epoch`, xử lý `409 Conflict`, và sự kiện `PlaybackCompleted ACK` từ P04 Media Playout.
3. **Auth OIDC & RBAC Enforcement:** Vai trò `OWNER` / `OPERATOR` hiện chuyển đổi qua query/devbar mock; production bắt buộc xác thực qua Managed OIDC và kiểm tra quyền phía server.
4. **Telemetry & Async Export Worker:** Các chỉ số `concurrent_viewers`, `live_duration_seconds` và tác vụ xuất CSV/PDF bất đồng bộ cần dịch vụ báo cáo backend thật (P09/P12).
