# HOSTRA AI — Nhật ký Sửa lỗi & Hồi quy (M05.3 Fix Log)

Tuân thủ nguyên tắc **TEST-FIRST** của M05.3, chỉ thực hiện đúng 1 chỉnh sửa bảo vệ nhỏ có bằng chứng từ Phase 1.2 và bổ sung 1 bộ test E2E hành trình lâu dài:

| Tệp thay đổi | Lý do sửa | Issue / Yêu cầu liên quan | Kết quả hồi quy |
| :--- | :--- | :--- | :--- |
| `apps/web/src/hooks/useScenario.tsx` | Bổ sung hàm `isDevInspectorAllowed()`: chỉ cho phép bật `DevScenarioBar` (bằng `?devTools=1` hoặc `Ctrl+Shift+D`) trên môi trường `DEV`, `localhost`/`127.0.0.1` hoặc khi biến `VITE_ENABLE_MOCK_SWITCHER=true` được cấu hình chủ động — chặn việc tự ý bật chế độ mô phỏng qua URL/phím tắt ở domain production thật | Phase 1.2 (Mục 4.2) & `UX-02` / `UX-14` | `typecheck` PASS, `lint` PASS, `vitest` 27/27 PASS, `vite build` PASS |
| `apps/web/tests/e2e/m05-user-journeys.spec.ts` *(mới)* | Bổ sung bộ test Playwright E2E hồi quy phủ 11 hành trình người dùng (`J01`–`J11`), Focus Trap và quyền Owner/Operator/Viewer | Phase 2 & Phase 5 | Thực thi xác minh 11/11 PASS trên Chromium |

## Những thay đổi CHƯA thực hiện trong M05.3 (đưa sang M05.4 / chờ PO duyệt)
1. Thay nốt 4 cặp `<Link><Button>` còn lại trong `DashboardPage.tsx` bằng `ButtonLink` (`UX-04` phần còn lại).
2. Bổ sung **Account Dropdown Menu** ở Avatar góc trên bên phải (`Topbar.tsx`) kèm nút **Đăng xuất → `/auth/sign-in`** (`REQUIRES PRODUCT OWNER DECISION`).
3. Rút gọn thêm nhãn phụ trên bảng Dashboard (`UX-13`) và xác nhận với PO xem có ẩn nốt mã `P04/P09` trong dòng nguồn đo nhỏ dưới thẻ KPI Báo cáo không (`UX-06`).
