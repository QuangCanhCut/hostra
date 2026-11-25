# HOSTRA AI — Báo cáo Triển khai Milestone 05.4

**Milestone:** M05.4 — Final Regression, UX Issue Closure & Frontend Demo Readiness  
**Ngày cập nhật:** 22/11/2026  
**Nhánh Git:** `feat/frontend-foundation`  
**Phạm vi thay đổi:** Chỉ chỉnh sửa Frontend Mock MVP (`apps/web/`), biến môi trường mẫu (`.env.example`) và tài liệu báo cáo (`docs/product/frontend/`). Không thay đổi `apps/api/`, `experiments/` hay logic nghiệp vụ lõi.

---

## 1. Thực thi 4 quyết định đã duyệt của Product Owner

### 1.1. PO-D01 — Menu Tài khoản trên Avatar góc trên bên phải
- **Tệp chỉnh sửa:** [Topbar.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/app/layouts/Topbar.tsx)
- **Thay đổi:**
  - Chuyển khối Avatar tĩnh thành nút tương tác chuẩn truy cập (`<button aria-haspopup="menu" aria-expanded={accountMenuOpen}>`), kích thước vùng bấm tối thiểu `min-h-10`, hiển thị gọn trên mobile (avatar + mũi tên) và đầy đủ trên desktop (avatar + tên + mũi tên).
  - Bổ sung hộp thoại thả xuống (`role="menu"`) gồm:
    1. **Thông tin tài khoản hiện tại:** tên hiển thị (`actor.displayName`), email (`actor.email`), vai trò (`actor.roleLabel`) và tên không gian làm việc (`workspace.displayName`), có giá trị dự phòng an toàn.
    2. **Thiết lập không gian làm việc** (`role="menuitem"`): điều hướng trực tiếp tới `/studio/onboarding`.
    3. **Đăng xuất** (`role="menuitem"`): đăng xuất mô phỏng điều hướng về `/auth/sign-in`, **không xóa** dữ liệu sản phẩm/phiên/kịch bản đang lưu trong mock store để thuận tiện chuyển vai trò khi demo.
  - Hỗ trợ đầy đủ đóng bằng phím `Escape` (tự động khôi phục focus về nút Avatar), đóng khi bấm ra ngoài, tương thích hoàn toàn cả Light Mode và Dark Mode.

### 1.2. PO-D02 — Ngôn ngữ thân thiện với người bán & ẩn mã kỹ thuật nội bộ (Đóng `UX-06`)
- **Tệp chỉnh sửa:**
  - [m03.store.ts](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/mocks/m03.store.ts)
  - [store.ts](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/mocks/store.ts)
  - [SessionReportPage.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/features/reports/pages/SessionReportPage.tsx)
  - [OnboardingPage.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/features/workspace/pages/OnboardingPage.tsx)
  - [InvitesPage.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/features/invitations/pages/InvitesPage.tsx)
- **Thay đổi cụ thể:**
  - Trên **Báo cáo phiên**: Thay toàn bộ nhãn nguồn KPI kỹ thuật (`P09 Session Lifecycle + Publisher Intervals`, `Invite Admission API`, `Comment Intake API receipts`, `P04 PlaybackCompleted ACK (deduplicated)`, `LiveKit Presence Telemetry`) bằng nhãn tiếng Việt dễ hiểu (`Hệ thống quản lý phiên phát`, `Hệ thống ghi nhận lượt vào phòng`, `Hệ thống tiếp nhận bình luận`, `Xác nhận nội dung đã phát tới người xem`, `Dữ liệu theo dõi người xem trực tiếp`). Đổi tiêu đề biểu ngữ báo cáo chưa đầy đủ sang tiếng Việt rõ ràng thay vì hiện mã thô `PARTIAL`/`PENDING`. Giữ nguyên thuật toán KPI, giữ nguyên `N/A` (không đổi thành `0`), giữ nguyên giải thích nguyên tắc `PlaybackCompleted ACK` khác với TTS.
  - Trên **Kiểm tra sẵn sàng (Readiness)**: Thay `P11 · Rights Registry`, `P01 · Presenter Studio`, `P09 · OCOP Eligibility`, `P05 · Knowledge & Claims`, `P06 · Story Planner`, `P04 · Media Controller` bằng nhãn tiếng Việt thân thiện (`Hệ thống xác nhận quyền hình ảnh (Mô phỏng)`, `Thư viện AI Presenter`, `Hệ thống xác minh OCOP`, `Kho Tri thức & Claims`, `Kế hoạch nội dung`, `Hạ tầng phát sóng (Mô phỏng)`).
  - Trên **Thiết lập không gian làm việc** & **Lời mời xem live**: Gỡ bỏ mã nội bộ `AW-D2` và `IM-D3` khỏi dòng phụ đề giao diện.

### 1.3. PO-D03 — Tinh gọn mật độ badge trên Dashboard (Đóng `UX-13`)
- **Tệp chỉnh sửa:**
  - [FeaturedSessionCard.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/features/dashboard/components/FeaturedSessionCard.tsx)
  - [AssetStatusGrid.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/features/dashboard/components/AssetStatusGrid.tsx)
  - [RecentSessionsSection.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/features/dashboard/components/RecentSessionsSection.tsx)
  - [ActionCenter.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/features/dashboard/components/ActionCenter.tsx)
- **Thay đổi:**
  - Áp dụng biến thể `StatusBadge subtle` cho các trạng thái bình thường/phụ (`AI đang hoạt động`, `Media ổn định`, `Đang quản lý`, `Đã kiểm chứng`, `Đang tạo`) để giảm nhiễu thị giác mà vẫn giữ nguyên cấu trúc bố cục Dashboard đã duyệt và không gộp trạng thái độc lập.
  - Các trạng thái quan trọng (`Đang phát trực tiếp`, `Cần phê duyệt`, `Đang chờ tài liệu`, `Media suy giảm`, `AI đang tạm dừng`, `Bị chặn`) giữ nguyên sắc độ nổi bật để chủ shop quét nhanh trong 3 giây.

### 1.4. PO-D04 — Kế hoạch Kiểm thử Người dùng thật (`PLAN READY`)
- Hoàn thiện bộ tài liệu [HUMAN_USABILITY_TEST_PLAN.md](./HUMAN_USABILITY_TEST_PLAN.md) đầy đủ tiêu chí tuyển chọn 5–8 người dùng mục tiêu, kịch bản điều phối, mẫu đồng thuận, phiếu quan sát, thang điểm SUS và khung ưu tiên phát hiện.
- Trạng thái thực địa được ghi nhận trung thực là **`PENDING HUMAN TEST`** (không có bất kỳ dữ liệu giả lập người dùng thật nào).

---

## 2. Đóng triệt để các vấn đề UX còn tồn đọng (`UX-04`, `UX-15`) & Gia cố vận hành (`B1–B4`)

### 2.1. Loại bỏ toàn bộ phần tử tương tác lồng nhau (`UX-04` — P1)
- Chuyển toàn bộ các cặp `<Link><Button>` và `<a><Button>` sang sử dụng `ButtonLink` từ `@/components/ui/Button` (hoặc thẻ `<a>` tạo kiểu nút trực tiếp đối với neo `#action-center`) trên:
  - [DashboardPage.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/features/dashboard/pages/DashboardPage.tsx)
  - [DashboardHero.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/features/dashboard/components/DashboardHero.tsx)
  - [FeaturedSessionCard.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/features/dashboard/components/FeaturedSessionCard.tsx)
  - [PresenterLibraryPage.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/features/presenter/pages/PresenterLibraryPage.tsx)
  - [ProductsCatalogPage.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/features/products/pages/ProductsCatalogPage.tsx)
  - [SessionsListPage.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/features/live-session/pages/SessionsListPage.tsx)
  - [QrCodePreview.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/features/invitations/components/QrCodePreview.tsx)
- **Kết quả kiểm toán DOM tự động:** **`0`** phần tử `a button, button a, a a, button button` trên toàn bộ **12/12 tuyến trang** trọng yếu.

### 2.2. Cải thiện vùng chạm/bấm cho liên kết & nút nhỏ (`UX-15` — P2)
- Mở rộng vùng bấm (`min-h-9 px-2.5 py-1.5 rounded-[8px]`) cho các liên kết hành động trong [RecentSessionsSection.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/features/dashboard/components/RecentSessionsSection.tsx), [ActionCenter.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/features/dashboard/components/ActionCenter.tsx), [SessionReportPage.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/features/reports/pages/SessionReportPage.tsx) và nút Avatar trong [Topbar.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/app/layouts/Topbar.tsx) (`min-h-10`), đảm bảo không gây tràn ngang ở mọi viewport.

### 2.3. Gia cố URL công khai cho Lời mời & Mã QR (`B4`)
- Bổ sung biến môi trường tùy chọn `VITE_PUBLIC_APP_URL` trong [InvitesPage.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/src/features/invitations/pages/InvitesPage.tsx) và [.env.example](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/.env.example). Khi để trống, hệ thống tự động dùng `window.location.origin`; khi chạy demo qua mạng LAN hoặc bản xem trước triển khai, người demo có thể cấu hình địa chỉ công khai để điện thoại quét QR truy cập trực tiếp.

---

## 3. Kiểm thử tự động bổ sung

- Tạo mới bộ kiểm thử [m05-4-account-and-closure.test.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/tests/m05-4-account-and-closure.test.tsx) (4 test cases) xác minh:
  1. Mở/đóng Account Dropdown Menu bằng chuột và phím `Escape`, khôi phục focus về nút Avatar.
  2. Điều hướng sang `Thiết lập không gian làm việc` (`/studio/onboarding`) và `Đăng xuất` mô phỏng (`/auth/sign-in`).
  3. Xác nhận `0` phần tử tương tác lồng nhau trên Dashboard.
  4. Xác nhận nguồn đo KPI tiếng Việt thân thiện trên Báo cáo phiên.
- Cập nhật 1 assertion trong [dashboard.test.tsx](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/apps/web/tests/dashboard.test.tsx) từ `getByRole('button', { name: /Tạo phiên mới/i })` sang `getByRole('link', { name: /Tạo phiên mới/i })` do `Tạo phiên mới` đã được chuẩn hóa thành `ButtonLink` đúng ngữ nghĩa HTML5 (`UX-04`).
