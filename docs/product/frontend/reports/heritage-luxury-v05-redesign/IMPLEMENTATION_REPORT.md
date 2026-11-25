# HOSTRA AI — Báo cáo triển khai thiết kế lại giao diện Heritage Luxury v0.5

- **Phạm vi:** Toàn bộ ứng dụng Frontend `apps/web/` (Design System, AppShell, Dashboard và toàn bộ 11 module nghiệp vụ)
- **Tài liệu bàn giao tham chiếu:** `docs/product/frontend/design/hostra-heritage-handoff/`
- **Định hướng thị giác:** HOSTRA Heritage Luxury v0.5 (Dark Espresso `#14110e` / Bronze `#503e2d`–`#896641` / Champagne Gold `#f2c47d` làm chủ đạo + Light Parchment `#f6f1e9` / Deep Bronze `#8b571e`)
- **Nhánh thực hiện:** `feat/frontend-foundation`
- **Trạng thái:** Hoàn tất triển khai & QA tự động + trực quan (MSW Mock Frontend; chưa kết nối backend thực tế)

---

## 1. Tóm tắt mục tiêu & nguyên tắc bảo toàn

Nhiệm vụ chuyển đổi toàn bộ lớp hiển thị của `apps/web/` từ chuẩn màu cũ v0.4 (`#0F172A` Navy / `#F5C430` Amber) sang phong cách **HOSTRA Heritage Luxury v0.5** mà **không xây dựng lại dự án từ đầu** và **không thay đổi bất kỳ hành vi nghiệp vụ nào**:

- **Giữ nguyên 100% nghiệp vụ & hợp đồng dữ liệu:** Không sửa `apps/api/`, `experiments/`, các MSW handlers/stores, state management, React Router paths hay cấu trúc phân quyền RBAC.
- **Giữ nguyên toàn bộ bất biến an toàn (Safety Invariants):**
  - Chỉ Chủ sở hữu (Workspace Owner) mới được quyền `START` livestream, phê duyệt Presenter/Tri thức/Story, quản lý Thành viên và Lời mời.
  - Vận hành viên (Operator) chỉ điều khiển các phiên được phân công; hỗ trợ phân công N:N và nút **Dừng khẩn cấp (Emergency Stop)** xác nhận 1 bước độc lập.
  - Tách biệt rõ `ACCEPTED ≠ APPLIED`, `STARTING ≠ LIVE`, `PAUSE_AI ≠ STOP`, và giữ nguyên cơ chế xác nhận `PlaybackCompleted ACK`.
  - Tách biệt cổng xác minh OCOP, Tri thức/Claims, Quyền chủ thể hình ảnh (Rights Subject) và Kiểm tra sẵn sàng (Readiness).
  - Phòng xem khách (`/live/:id`) chạy độc lập ngoài `AppShell`, chỉ xem & bình luận (subscribe-only), không bật camera/micro, không hiển thị điều khiển của nhà bán hàng.
- **Không dùng ảnh chụp toàn màn hình làm background:** Chỉ trích xuất và sử dụng 8 tài nguyên trang trí rời trong `apps/web/public/heritage/`.
- **Mặc định giao diện:** Chế độ Tối (Dark Mode) là mặc định khi chưa có cấu hình người dùng, đồng thời hỗ trợ chuyển đổi đầy đủ sang Chế độ Sáng (Light Mode) với tương phản đạt chuẩn WCAG AA.

---

## 2. Kiến trúc triển khai theo giai đoạn

### Giai đoạn 1 — Design System, AppShell & Dashboard (đã nghiệm thu riêng)
- **Tokens & Typography:**
  - Cập nhật `apps/web/index.html` nạp thêm `Noto Serif` (600, 700) kết hợp `Be Vietnam Pro` & `Inter`; cấu hình chuỗi fallback tiếng Việt đầy đủ (`'Noto Serif', 'Cambria', 'Times New Roman', Georgia, serif`) để không lỗi dấu tiếng Việt (như `ầ`, `ệ`) khi chạy offline.
  - Viết lại `apps/web/src/styles/tokens.css` (cả `[data-theme='dark']` và `[data-theme='light']`) và `apps/web/src/styles/globals.css` (nền radial glow ấm, `.font-display`, `.heritage-card`, mask chuyển sắc sidebar/resource, `prefers-reduced-motion`).
  - Bảo toàn alias biến cũ (`--brand-amber`, `--brand-navy`, `--brand-danger`, ...) nhằm tránh đứt gãy chéo.
  - Cập nhật `apps/web/src/hooks/useTheme.tsx` đặt mặc định ban đầu là `'dark'`.
- **Thư viện UI dùng chung:**
  - Nâng cấp: `Button`, `Card` (thêm prop `featured`), `StatusBadge`, `Banner`, `Tabs`, `Modal`, `Drawer`, `BrandLogo`, `ThemeToggle` (thêm prop `tone?: 'adaptive' | 'on-dark'`), `DevScenarioBar`, `PortraitAvatar`.
  - Bổ sung mới: `PageHeader`, `FormField` (`FormField`, `TextInput`, `SelectInput`, `TextareaInput`), `Stepper`, `DataTable` (`DataTable`, `TABLE_HEAD_ROW_CLASS`, `TABLE_BODY_CLASS`, `TABLE_ROW_HOVER_CLASS`).
- **AppShell & Dashboard:**
  - Sidebar espresso cố định rộng `248px` (thu gọn `72px`), hiệu ứng thanh mục đang chọn đồng ánh kim, ảnh ruộng bậc thang mờ đáy `sidebar-landscape.webp`, drawer mobile hỗ trợ trap focus & `Escape`.
  - Topbar `60px` tích hợp breadcrumb, `ThemeToggle` và Account Dropdown Menu (`PO-D01`).
  - Dashboard gồm `DashboardHero` (`hero.webp`), `ActionCenter`, `FeaturedSessionCard` (dùng ảnh chân dung thật `/demo/presenters/{linh,mai,an}.jpg`, không có nút play giả), `AssetStatusGrid` (4 thẻ tài nguyên kèm ảnh WebP trang trí), và `RecentSessionsSection`.

### Giai đoạn 2 & 3 — Đồng bộ toàn bộ 11 module còn lại
1. **Auth & Onboarding:** `SignInPage`, `OnboardingPage`.
2. **AI Presenter & Cổng Chủ thể quyền:** `PresenterLibraryPage`, `PresenterWizardPage`, `PresenterDetailPage`, `RightsConsentPortalPage`.
3. **Sản phẩm & OCOP:** `ProductsCatalogPage`, `ProductWizardPage`, `ProductDetailPage`.
4. **Tri thức & Claims:** `KnowledgeLibraryPage`, `KnowledgeReviewPage` (trình xem tài liệu nguồn dạng trang giấy parchment `--doc-paper-bg` đặt cạnh danh sách duyệt claim).
5. **Phiên livestream, Story Planner & Readiness:** `SessionsListPage`, `SessionWizardPage`, `SessionDetailPage`, `StoryPlannerPage`, `ReadinessPage`.
6. **Phòng điều khiển Live & Phòng xem khách:** `LiveControlRoomPage`, `ViewerLiveRoomPage` (đầy đủ 6 trạng thái: lỗi link, đã kết thúc, nhập tên, phòng chờ, đang phát LIVE, mô phỏng buffering/mất chat).
7. **Lời mời & Mã QR, Thành viên, Báo cáo:** `InvitesPage`, `QrCodePreview` (mã QR mực espresso `#21160C` trên nền trắng sắc nét), `MembersPage`, `ReportsHistoryPage`, `SessionReportPage` (biểu đồ cột chuyển sắc vàng đồng + biểu đồ người xem đồng thời + dòng thời gian trạng thái + xuất CSV/PDF an toàn).

---

## 3. Kết quả kiểm thử & xác minh kỹ thuật

| Hạng mục kiểm tra | Lệnh thực thi | Kết quả |
|---|---|---|
| TypeScript Typecheck | `npm --prefix apps/web run typecheck` | **PASS** — 0 lỗi |
| ESLint | `npm --prefix apps/web run lint` | **PASS** — 0 lỗi, 0 cảnh báo |
| Unit & Component Tests | `npm --prefix apps/web run test -- --fileParallelism=false` | **PASS — 5/5 files, 31/31 tests** (`dashboard`, `m02-workflows`, `m03-workflows`, `m04-uat-reconciliation`, `m05-4-account-and-closure`) |
| Production Build | `npm --prefix apps/web run build` | **PASS** — `tsc -b && vite build` (2063 modules, 5.80s) |
| Quét màu legacy v0.4 | Quét regex toàn bộ `apps/web/src/**/*.tsx` | **PASS** — 0 mã màu/class cũ v0.4 còn sót (`#0F172A`, `#0B1322`, `#F5C430`, `#0EA5E9`, `slate-*`, `bg-[var(--bg-hero)]`, `dark:`) |
| Visual QA Playwright | Chụp kiểm tra trên `vite preview` qua 4 độ phân giải (`1440`, `1024`, `768`, `390`) & Dark/Light | **PASS — 24/24 ảnh chụp** (`overflow: 0`, `brokenImgs: []`, `errors: []`) |

---

## 4. Các vấn đề phát hiện và đã khắc phục trong quá trình QA

1. **Lỗi dấu tiếng Việt (`ầ`) khi chạy offline:** Fallback font `'Noto Serif', Georgia, serif` rơi về `Georgia` vốn thiếu glyph tiếng Việt mở rộng. Đã chuyển sang `'Noto Serif', 'Cambria', 'Times New Roman', Georgia, serif`.
2. **Nút play mờ gắn sẵn trong ảnh crop `presenter-heritage.webp`:** Vi phạm quy tắc không có biểu tượng phát giả trên thẻ xem trước. Đã chuyển `FeaturedSessionCard` dùng trực tiếp ảnh chân dung sạch `/demo/presenters/{linh,mai,an}.jpg`.
3. **Khoảng trống dưới Sidebar ở Light Mode khi cuộn dài:** Đã bổ sung `bg-[var(--bg-sidebar-solid)]` cho khung `<aside>` ngoài cùng của `Sidebar.tsx`.
4. **Tràn ngang 4px tại Phòng điều khiển (1440px):** Thanh sticky runtime bar dùng `lg:-mx-8` lệch 4px so với `lg:px-7` của `AppShell`. Đã đồng bộ về `lg:-mx-7 lg:px-7` → `overflow: 0`.
5. **Chấm màu dòng thời gian bị ẩn trên `SessionReportPage` (lỗi có sẵn trước redesign):** Đã sửa biến CSS `--status-success/warning/danger` thành `--status-success-fg/warning-fg/danger-fg`.
6. **Bộ lọc báo cáo dùng `dark:` media query thay vì `data-theme="dark"`:** Đã thay bằng token chủ đề thích ứng trên `ReportsHistoryPage`.
7. **Tinh chỉnh cuối sau vòng soi ảnh Phase 4:**
   - Sửa biến nền nút Play ở màn hình vào phòng xem khách sang `--cta-primary-bg` / `--cta-primary-fg`.
   - Thêm `tone="on-dark"` cho `ThemeToggle` trên header tối của `ViewerLiveRoomPage`.
   - Đưa biểu tượng `Download` của nút xuất báo cáo trên `SessionReportPage` vào prop `leftIcon` để căn ngang 1 hàng.

---

## 5. Bộ ảnh chụp nghiệm thu trực quan (`./screenshots/`)

### 5.1. Tổng quan (Dashboard) — Desktop, Compact, Tablet, Mobile (Dark & Light)

| Màn hình & Chế độ | Ảnh chụp |
|---|---|
| Dashboard Desktop `1440px` — Dark | ![Dashboard 1440 Dark](./screenshots/01-dashboard-1440-dark.png) |
| Dashboard Desktop `1440px` — Light | ![Dashboard 1440 Light](./screenshots/02-dashboard-1440-light.png) |
| Dashboard Compact `1024px` — Dark | ![Dashboard 1024 Dark](./screenshots/05-dashboard-1024-dark.png) |
| Dashboard Tablet `768px` — Light | ![Dashboard 768 Light](./screenshots/06-dashboard-768-light.png) |
| Dashboard Mobile `390px` — Dark | ![Dashboard 390 Dark](./screenshots/03-dashboard-390-dark.png) |
| Dashboard Mobile `390px` — Light | ![Dashboard 390 Light](./screenshots/04-dashboard-390-light.png) |

### 5.2. Đăng nhập, AI Presenter & Cổng xác nhận Chủ thể quyền

| Màn hình & Chế độ | Ảnh chụp |
|---|---|
| Đăng nhập `1440px` — Dark | ![Login 1440 Dark](./screenshots/07-login-1440-dark.png) |
| Đăng nhập `1440px` — Light | ![Login 1440 Light](./screenshots/08-login-1440-light.png) |
| Thư viện AI Presenter `1440px` — Dark | ![Presenters 1440 Dark](./screenshots/09-presenters-1440-dark.png) |
| Cổng xác nhận quyền `1440px` — Dark | ![Consent Portal 1440 Dark](./screenshots/10-consent-1440-dark.png) |

### 5.3. Sản phẩm & OCOP, Duyệt Tri thức, Story Planner & Readiness

| Màn hình & Chế độ | Ảnh chụp |
|---|---|
| Sản phẩm & Hồ sơ OCOP `1440px` — Dark | ![Products 1440 Dark](./screenshots/11-products-1440-dark.png) |
| Duyệt Tri thức & Claims `1440px` — Dark | ![Knowledge Review 1440 Dark](./screenshots/12-knowledge-review-1440-dark.png) |
| Duyệt Tri thức & Claims `1440px` — Light | ![Knowledge Review 1440 Light](./screenshots/13-knowledge-review-1440-light.png) |
| Lập kế hoạch nội dung (Story Planner) `1440px` — Dark | ![Story Planner 1440 Dark](./screenshots/14-story-1440-dark.png) |
| Kiểm tra sẵn sàng (Readiness) `1440px` — Dark | ![Readiness 1440 Dark](./screenshots/15-readiness-1440-dark.png) |

### 5.4. Phòng điều khiển Live & Phòng xem riêng của khách (Viewer Live Room)

| Màn hình & Chế độ | Ảnh chụp |
|---|---|
| Phòng điều khiển `1440px` — Dark | ![Control Room 1440 Dark](./screenshots/16-control-room-1440-dark.png) |
| Phòng điều khiển `390px` — Dark | ![Control Room 390 Dark](./screenshots/17-control-room-390-dark.png) |
| Viewer Room (Nhập tên) `390px` — Dark | ![Viewer Entry 390 Dark](./screenshots/18-viewer-entry-390-dark.png) |
| Viewer Room (Đang LIVE) `1440px` — Dark | ![Viewer Live 1440 Dark](./screenshots/19-viewer-live-1440-dark.png) |
| Viewer Room (Đang LIVE) `390px` — Light | ![Viewer Live 390 Light](./screenshots/20-viewer-live-390-light.png) |

### 5.5. Lời mời & Mã QR, Thành viên & Báo cáo chi tiết phiên

| Màn hình & Chế độ | Ảnh chụp |
|---|---|
| Lời mời & Mã QR `1440px` — Dark | ![Invites 1440 Dark](./screenshots/21-invites-1440-dark.png) |
| Thành viên & Phân quyền `1440px` — Dark | ![Members 1440 Dark](./screenshots/22-members-1440-dark.png) |
| Báo cáo chi tiết phiên `1440px` — Dark | ![Session Report 1440 Dark](./screenshots/23-session-report-1440-dark.png) |
| Báo cáo chi tiết phiên `1440px` — Light | ![Session Report 1440 Light](./screenshots/24-session-report-1440-light.png) |

---

## 6. Danh mục tệp nguồn đã chỉnh sửa / tạo mới

### Tài nguyên & Nền tảng Design System
- `apps/web/public/heritage/` (`logo.svg`, `hero.webp`, `sidebar-landscape.webp`, `presenter-heritage.webp`, `microphone.webp`, `plums.webp`, `knowledge-book.webp`, `camera.webp`)
- `apps/web/index.html`
- `apps/web/src/styles/tokens.css`
- `apps/web/src/styles/globals.css`
- `apps/web/src/hooks/useTheme.tsx`

### UI Components dùng chung
- **Tạo mới:** `apps/web/src/components/ui/PageHeader.tsx`, `FormField.tsx`, `Stepper.tsx`, `DataTable.tsx`
- **Nâng cấp:** `apps/web/src/components/ui/Button.tsx`, `Card.tsx`, `StatusBadge.tsx`, `Banner.tsx`, `Tabs.tsx`, `Modal.tsx`, `Drawer.tsx`
- **Shared:** `apps/web/src/components/shared/BrandLogo.tsx`, `ThemeToggle.tsx`, `DevScenarioBar.tsx`, `PortraitAvatar.tsx`

### AppShell & Các module nghiệp vụ
- **Layout:** `apps/web/src/app/layouts/AppShell.tsx`, `Sidebar.tsx`, `Topbar.tsx`
- **Dashboard:** `DashboardPage.tsx`, `DashboardHero.tsx`, `ActionCenter.tsx`, `FeaturedSessionCard.tsx`, `AssetStatusGrid.tsx`, `RecentSessionsSection.tsx`, `DashboardSkeleton.tsx`
- **Auth & Onboarding:** `SignInPage.tsx`, `OnboardingPage.tsx`
- **Presenter & Consent:** `PresenterLibraryPage.tsx`, `PresenterWizardPage.tsx`, `PresenterDetailPage.tsx`, `RightsConsentPortalPage.tsx`
- **Products & OCOP:** `ProductsCatalogPage.tsx`, `ProductWizardPage.tsx`, `ProductDetailPage.tsx`
- **Knowledge & Claims:** `KnowledgeLibraryPage.tsx`, `KnowledgeReviewPage.tsx`
- **Sessions, Story & Readiness:** `SessionsListPage.tsx`, `SessionWizardPage.tsx`, `SessionDetailPage.tsx`, `StoryPlannerPage.tsx`, `ReadinessPage.tsx`
- **Control Room & Viewer:** `LiveControlRoomPage.tsx`, `ViewerLiveRoomPage.tsx`
- **Invites, Members & Reports:** `InvitesPage.tsx`, `QrCodePreview.tsx`, `MembersPage.tsx`, `ReportsHistoryPage.tsx`, `SessionReportPage.tsx`

---

## 7. Phụ thuộc còn lại (Backend Integration)

- Giao diện hiện vận hành hoàn chỉnh trên **MSW mock APIs** (`apps/web/src/mocks/`), phục vụ kiểm thử UX/UI, phân quyền và luồng trạng thái.
- Chưa kết nối API thực từ `apps/api/`, hệ thống OIDC thật, dịch vụ TTS/lip-sync hay phòng phát LiveKit thực tế; do đó không khẳng định trạng thái production readiness cho tới khi hoàn tất tích hợp backend và kiểm thử end-to-end với dịch vụ thật.
