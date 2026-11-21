# HOSTRA AI — Frontend Milestone 04 Implementation Report
## Final Frontend QA, Cross-Module UAT & Backend Integration Readiness

- **Ngày hoàn tất:** 21/11/2026
- **Nhánh Git:** `feat/frontend-foundation` *(không tự động commit/push/merge)*
- **Phạm vi chỉnh sửa:** Chỉ trong `apps/web/` và `docs/product/frontend/` *(không động tới `apps/api/`, `experiments/`, `workers/`, `AGENTS.md`, `CLAUDE.md`, hay tài liệu nguồn DOCX/PDF)*
- **Visual Baseline:** **HOSTRA UI Redesign v0.4 — APPROVED** (Light Mode & Dark Mode, tiếng Việt)
- **Kết luận nghiệm thu M04:** **PASS (Frontend Mock MVP — Ready for Backend Integration Handoff)** — *không tuyên bố production-ready khi chưa kết nối backend thật, LiveKit thật và Managed OIDC thật.*

---

## 1. Tóm tắt điều hành (Executive Summary)

Milestone 04 đã hoàn thành kiểm toán toàn diện toàn bộ 12 module frontend (M01 + M02 + M03), xử lý triệt để cả **4 lỗi phát hiện từ review M03 (Gate 1)** bằng sửa đổi ở tầng kiến trúc gốc, xác minh xuyên suốt **12 luồng UAT đa module (Gate 2)** trên cùng canonical mock store, kiểm tra responsive & accessibility ở các breakpoint từ **`320px` đến `1920px` (Gate 3)**, mở rộng bộ kiểm thử tự động đạt **27/27 Vitest + 5/5 Playwright M04 Final QA (Gate 4)**, và hoàn thiện hồ sơ **Backend Integration Readiness + API Contract Gaps + Demo Guide (Gate 5)**.

---

## 2. Kết quả kiểm toán Baseline (Gate 0)

- **Nhánh & cấu trúc:** `feat/frontend-foundation`, cấu trúc feature-based chuẩn trong `apps/web/src/` (`app/`, `components/`, `features/`, `hooks/`, `lib/`, `mocks/`, `services/`, `styles/`, `types/`).
- **Baseline trước M04:** `typecheck` PASS, `lint` PASS (0 lỗi/0 cảnh báo), Vitest 22/22 PASS, `vite build` PASS (`index-*.js` = `394.43 kB`, 0 cảnh báo chunk > 500 kB).
- **4 lỗi xác nhận từ Review M03 + 1 lỗi phụ phát hiện thêm khi chạy Playwright console audit:**
  1. **M04-BUG-01 (High — Responsive):** Tablet `768×1024` Control Room có sidebar bị phình ~228px lúc chụp do `useState(false)` chạy `transition-[width]` sau mount, và thanh điều khiển `fixed ... md:left-[72px] xl:left-[232px]` đè sang vùng sidebar.
  2. **M04-BUG-02 (High — Data Consistency):** Báo cáo Phiên `#013` có timeline/biểu đồ hardcode `07:30–08:30`, mâu thuẫn với Reports History (`19:00–20:32 19-11`, thời lượng `1 giờ 32 phút`).
  3. **M04-BUG-03 (High — Metrics Reconciliation):** Phiên `#013` có KPI Successful Admissions = `86` nhưng tổng 5 cột biểu đồ là `6+11+14+8+4 = 43` (chênh lệch 43 lượt không có giải thích).
  4. **M04-BUG-04 (Medium — UX Messaging):** Reports History hiển thị cứng `"Có thể xuất CSV / PDF"` cho cả Phiên `#015` đang `PREPARING` (`PENDING`) và Phiên `#013` (`PARTIAL`).
  5. **M04-BUG-05 (Low — Asset 404):** Thiếu `<link rel="icon">` trong `apps/web/index.html` gây 1 lỗi `404 Not Found` cho `/favicon.ico` trên browser console.

---

## 3. Phân tích nguyên nhân gốc & Bản sửa đã triển khai (Gate 1)

| Mã lỗi | Nguyên nhân gốc (Root Cause) | Giải pháp kiến trúc đã triển khai | Tệp thay đổi |
| :--- | :--- | :--- | :--- |
| **M04-BUG-01** | `AppShell` khởi tạo `collapsed=false` rồi mới `setCollapsed(true)` trong `useEffect`, kích hoạt `transition-[width] 200ms` từ `232px→72px`. Thanh Control Bar dùng `position: fixed` với breakpoint cứng `md:left-[72px] xl:left-[232px]` lệch với trạng thái collapse thực tế. | Chuyển `collapsed` sang lazy initializer `useState(() => matchMedia(...).matches)`, gắn CSS variable `--sidebar-width` trên root `AppShell`, và chuyển Control Bar sang `sticky bottom-0` nằm gọn bên trong `<main>`. Đo DOM thực tế tại `768×1024`: `asideWidth=72px`, `asideRight=72px`, `barLeft=72px`, `barWidth=696px`. | `AppShell.tsx`, `LiveControlRoomPage.tsx` |
| **M04-BUG-02** | `buildSessionReport()` trong `m03.store.ts` hardcode mốc `'07:30'..'08:30'` thay vì tính từ `session.startedAt` / `session.stoppedAt` trong canonical store; `formatShortTime` không cố định `timeZone`. | Chuẩn hóa `src/lib/format.ts` dùng múi giờ hiển thị nhất quán `Asia/Ho_Chi_Minh` (`formatShortTime`, `formatClockTime`, `computeDurationMinutes`, `formatDurationMinutesVi`). `buildSessionReport()` tạo mọi mốc biểu đồ & timeline trực tiếp từ `session.startedAt`/`stoppedAt` dạng ISO UTC. Phiên `#013` đồng bộ hoàn toàn `19:00–20:32 19-11`. | `src/lib/format.ts`, `src/types/m03.ts`, `src/mocks/m03.store.ts`, `SessionReportPage.tsx` |
| **M04-BUG-03** | `intervalChart` của `ses-013` bị hardcode 5 cột tổng `43`, không khớp KPI `86`. | Áp dụng Phương án A (Full-session aggregation): `ses-013` gồm 7 khung 15 phút (`19:00–20:30`) với `[10, 16, 22, 15, 11, 8, 4]` → **Tổng = 86 === KPI 86**; `ses-012` 5 khung tổng **54 === KPI 54**; `ses-014` phân bổ động từ `totalAdmissions` thực tế sao cho `sum === KPI`. Không suy luận `concurrent_viewers` từ `admissions` (vẫn hiện `N/A` khi thiếu presence telemetry). | `src/mocks/m03.store.ts`, `SessionReportPage.tsx` |
| **M04-BUG-04** | `ReportsHistoryPage.tsx` hardcode chuỗi `"Có thể xuất CSV / PDF"` theo `role === 'OWNER'`, bỏ qua `reportStatus`. | Dùng chung hàm `resolveSessionReportStatus()` giữa History & Report Detail; phân tách rõ 4 trạng thái `PENDING` (`Chưa sẵn sàng xuất (phiên chưa phát)`), `PARTIAL` (`Dữ liệu một phần · Chưa mở xuất file`), `READY` (`Sẵn sàng xuất CSV / PDF`), `FAILED` (`Lỗi tổng hợp · Không thể xuất`), và Operator (`Bản rút gọn`). | `src/mocks/m03.store.ts`, `ReportsHistoryPage.tsx` |
| **M04-BUG-05** | `index.html` không khai báo favicon. | Thêm inline SVG favicon logo chữ `H` chuẩn màu brand HOSTRA (`#F5C430` / `#0F172A`), đạt **0 console errors**. | `apps/web/index.html` |

---

## 4. Kết quả kiểm thử & Đo lường hiệu năng (Gate 4)

| Kiểm tra | Lệnh thực thi | Kết quả |
| :--- | :--- | :---: |
| **TypeScript** | `npm run typecheck` | **PASS (0 lỗi)** |
| **ESLint** | `npm run lint` | **PASS (0 lỗi, 0 cảnh báo)** |
| **Vitest (Unit & Cross-Module UAT)** | `npm run test` | **PASS — 4/4 files · 27/27 tests** (`dashboard.test.tsx`: 7, `m02-workflows.test.tsx`: 9, `m03-workflows.test.tsx`: 6, `m04-uat-reconciliation.test.tsx`: 5) |
| **Production Build** | `npm run build` | **PASS (5.70s)** · Main entry `index-Bzhme1G6.js`: **`394.66 kB`** (`124.08 kB` gzip) · **0 cảnh báo chunk > 500 kB** (giảm **30.1%** so với baseline M02 `564.95 kB`) |
| **Playwright M04 Final QA** | `npx playwright test tests/e2e/m04-final-qa.spec.ts` | **PASS — 5/5 suites · 10/10 PNG screenshots · 0 console/page errors** |

---

## 5. Vấn đề còn mở & Ranh giới tích hợp Backend

- **PDF tiếng Việt có dấu Unicode đầy đủ:** Client-side PDF 1.4 generator hiện chuẩn hóa ASCII không dấu (Type1 Helvetica) để tránh nhúng font TrueType ~400KB vào bundle frontend; khi nối backend, dịch vụ xuất PDF phía server (P12) sẽ render font `Be Vietnam Pro` UTF-8 đầy đủ.
- **Distributed Concurrency & LiveKit WebRTC:** MSW in-memory mô phỏng deterministic arbitration cho 1 trình duyệt; kiểm thử đồng thời thực tế giữa nhiều thiết bị/browser contexts và ngắt kết nối LiveKit tức thì khi revoke invite sẽ thực hiện khi backend REST/WS & LiveKit Server sẵn sàng (xem chi tiết tại `INTEGRATION_READINESS_MATRIX.md` và `API_CONTRACT_GAPS.md`).
