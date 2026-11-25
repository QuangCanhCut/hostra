# HOSTRA AI — Đề xuất Kế hoạch Triển khai Milestone 05.2 (PROPOSED ONLY)

> **Lưu ý:** Đây là **kế hoạch đề xuất** để Product Owner xem xét và phê duyệt trước khi bắt đầu sửa code ở M05.2. Chưa có bất kỳ thay đổi mã nguồn nào được thực hiện trong M05.1.

---

## Lộ trình chia thành 4 Gói nhỏ dễ nghiệm thu (4 Reviewable Batches)

### Gói 1 — Sửa lỗi Design System, Token & Accessibility nền tảng *(Ưu tiên cao nhất — Không cần chờ duyệt nghiệp vụ)*
- **Mục tiêu:** Giải quyết dứt điểm `UX-01`, `UX-03`, `UX-04`, `UX-05`, `UX-07`, `UX-08`, `UX-19`, `UX-22`.
- **Màn hình / Tệp dự kiến sửa:** `Sidebar.tsx`, `StatusBadge.tsx`, `Modal.tsx`, `Drawer.tsx`, `Button.tsx` (thêm `ButtonLink`), `ReportsHistoryPage.tsx`, `SessionReportPage.tsx`, `ViewerLiveRoomPage.tsx`, 6 trang đang lồng `<Link><Button>`.
- **Rủi ro:** Thấp (không thay đổi luồng nghiệp vụ hay mock store).
- **Kiểm thử cần chạy:** `typecheck`, `lint`, toàn bộ `vitest` (27 tests) + thêm test focus trap Modal & kiểm tra 0 `<button>` trong `<a>`.
- **Ảnh đối chiếu trước/sau:** `10-readiness-1024`, `15-viewer-live-390-dark`, `16-session-report-1440-dark`.

### Gói 2 — Tách công cụ mô phỏng Dev khỏi giao diện người dùng cuối *(Cần chốt cách mở Dev Inspector khi demo)*
- **Mục tiêu:** Giải quyết `UX-02`, `UX-14` — di dời 4 nút mô phỏng ở Control Room và 2 nút mô phỏng ở Viewer Room vào `DevScenarioBar` / ngăn kéo `Dev Inspector` theo ngữ cảnh trang.
- **Màn hình / Tệp dự kiến sửa:** `DevScenarioBar.tsx`, `LiveControlRoomPage.tsx`, `ViewerLiveRoomPage.tsx`, cập nhật selector trong `tests/e2e/m04-final-qa.spec.ts` để mở `Dev Inspector` trước khi bấm mô phỏng `409`.
- **Rủi ro:** Trung bình (cần cập nhật một số test E2E đang bấm trực tiếp nút mô phỏng trên màn hình).
- **Điểm cần PO duyệt:** Xác nhận cách mở `Dev Inspector` khi tự demo (gợi ý: 1 nút nhỏ kín đáo ở góc dưới hoặc phím tắt `Ctrl+Shift+D` / `?devTools=1`).

### Gói 3 — Tinh gọn Ngôn ngữ Tiếng Việt & Mật độ Thông tin *(Cần PO duyệt Microcopy & Layout)*
- **Mục tiêu:** Giải quyết `UX-06`, `UX-09`, `UX-10`, `UX-11`, `UX-13`, `UX-17`, `UX-20`, `UX-21`.
- **Màn hình / Tệp dự kiến sửa:** `LiveControlRoomPage.tsx`, `SessionReportPage.tsx`, `DashboardPage.tsx`, `InvitesPage.tsx`, `OnboardingPage.tsx`, `status-copy.ts`.
- **Rủi ro:** Trung bình (có cập nhật nhãn tiếng Việt nên cần đồng bộ các assertion text trong Vitest/Playwright).
- **Điểm cần PO duyệt:**
  1. Phê duyệt bảng chuyển đổi thuật ngữ trong [UX_MICROCOPY_GLOSSARY.md](./UX_MICROCOPY_GLOSSARY.md).
  2. Phê duyệt việc gom 3 trạng thái ổn định (Media/Publisher/Đồng bộ) thành 1 pill `Hệ thống ổn định` khi bình thường (vẫn tự tách màu cảnh báo ngay khi bất thường).
  3. Chọn giữ 1 nút `Chuyển SKU` duy nhất (trên thanh Control Bar hay trên thẻ Sản phẩm đang giới thiệu).

### Gói 4 — Tối ưu Trải nghiệm Tác nghiệp & Chạm di động *(Polish cuối)*
- **Mục tiêu:** Giải quyết `UX-12`, `UX-15`, `UX-16`, `UX-18`.
- **Màn hình / Tệp dự kiến sửa:** `ReadinessPage.tsx` (đưa mục chặn lên đầu), `KnowledgeReviewPage.tsx` (ghim cột nguồn `sticky`), `ProductsCatalogPage.tsx` & `StoryPlannerPage.tsx` (tăng vùng chạm mobile/tablet), `RightsConsentPortalPage.tsx` (bỏ nút `Về Studio`).
- **Rủi ro:** Thấp.
- **Điểm cần PO duyệt:** Xác nhận ẩn nút `Về Studio` trên trang Cổng Xác nhận Quyền và thứ tự sắp xếp cổng Readiness.

---

## Thứ tự triển khai khuyến nghị
**Gói 1 → Gói 2 → Gói 3 → Gói 4** — mỗi gói chạy trọn bộ `typecheck`, `lint`, `vitest`, `vite build` và chụp ảnh đối chiếu trước/sau trên Playwright trước khi chuyển gói kế tiếp.
