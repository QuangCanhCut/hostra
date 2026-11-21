# HOSTRA AI — Báo cáo triển khai Frontend Milestone 1 (Foundation + Merchant Dashboard)

| Mục | Thông tin |
| :--- | :--- |
| **Milestone** | Milestone 1 — Foundation & Merchant Dashboard |
| **Nhánh làm việc** | `feat/frontend-foundation` |
| **Phạm vi mã nguồn** | `apps/web/` (Frontend mock-first, chưa kết nối backend thật) |
| **Visual Baseline** | **HOSTRA UI Redesign v0.4 — APPROVED** + Global Design System v0.2 |
| **Ngày lập báo cáo** | 21/11/2026 |
| **Trạng thái** | **Sẵn sàng Review Milestone 1** *(chưa chuyển sang Milestone 2)* |

---

## 1. Tổng quan công việc

Milestone 1 hoàn thiện nền tảng ứng dụng frontend tại `apps/web/` theo kiến trúc modular, feature-based, tách biệt tầng trình bày với tầng dữ liệu/mock API (MSW), tuân thủ bộ nhận diện **HOSTRA UI Redesign v0.4** (Light Mode + Dark Mode, tiếng Việt chuẩn) và triển khai hoàn chỉnh màn hình **Merchant Dashboard (`SCR-01`)** cùng luồng **Mock Authentication (`Sign-In`)** và **AppShell** có phân quyền Owner/Operator.

---

## 2. Danh sách chức năng đã triển khai

- **Application Shell & Navigation:**
  - `Sidebar` nền Navy `#0F172A` (desktop `232px`, thu gọn `72px` trên tablet/desktop, drawer trên mobile), lọc mục điều hướng theo capability (`Kế hoạch livestream`, `Thành viên`, `Lời mời xem live` chỉ hiện cho Owner).
  - `Topbar` (`64px`) hiển thị breadcrumb workspace/trang, `ThemeToggle` (Light/Dark Mode), nút chuyển vai trò mô phỏng và thông tin tài khoản hiện tại.
  - Tuân thủ `AW-D3=A`: hiển thị 1 Workspace chính (`Đặc sản Mường Lát`), không dựng multi-workspace switcher trong MVP.
- **Design System & Shared UI Primitives (`components/ui/`):**
  - `Button` (Primary Amber `#F5C430` + chữ Navy `#0F172A`, Secondary, Ghost, Destructive `#DC2626` + chữ trắng), `Card` (`radius 12px`), `StatusBadge` (semantic tone + icon + nhãn tiếng Việt, không bao giờ chỉ dùng màu), `Banner` (persistent warning/danger/info), `Skeleton` (tôn trọng `prefers-reduced-motion`), `EmptyState` (phân biệt Empty / API Error / Forbidden 403).
- **Mock Authentication (`/auth/sign-in`):**
  - Giao diện cổng đăng nhập Managed OIDC mô phỏng, cho phép vào nhanh bằng vai trò **Chủ sở hữu (Owner)** hoặc **Vận hành viên (Operator)**.
- **Merchant Dashboard (`/studio/dashboard`):**
  - **Z02 Page Header:** Tiêu đề + nút `Tạo phiên mới` (chỉ hiển thị cho Owner theo RBAC).
  - **Z03 Critical Alerts & Next Best Action Hero:** Banner cảnh báo nghiêm trọng (khi Media suy giảm / Thu hồi quyền / Xung đột lệnh / Chờ OCOP) + khối Hero đề xuất hành động tiếp theo theo vai trò và trạng thái phiên.
  - **Z04 Two-Column Layout (60% / 40% desktop, 1 cột mobile):**
    - `ActionCenter`: Danh sách tác vụ ưu tiên (tối đa 5 mục + `Xem tất cả`), gắn nhãn `Chờ Chủ sở hữu duyệt` cho các đề xuất của Operator.
    - `FeaturedSessionCard`: Không chứa video player / không subscribe LiveKit (`D5`); hiển thị **độc lập** 3 lớp trạng thái `Session Lifecycle`, `AI State` và `Media Health` + thông tin fallback khi `DEGRADED`.
  - **Z05 Asset Status Grid:** 4 thẻ tài nguyên độc lập (`AI Presenter`, `Sản phẩm & OCOP`, `Tri thức & Claims`, `Phiên đã tạo`) dùng tabular numerals (`02`, `05`, `08`, `04`), ghi rõ không suy diễn thành `Session READY`.
  - **Z06 Recent Sessions:** Tối đa 3 phiên gần nhất (bảng trên desktop, thẻ xếp dọc trên mobile) + liên kết đích theo trạng thái phiên (`Phòng điều khiển` / `Tiếp tục chuẩn bị` / `Xem báo cáo`).
- **Dev-only Mock Scenario Switcher (`DevScenarioBar`):**
  - Cho phép chuyển nhanh 13 kịch bản mock và 2 vai trò (`Owner` / `Operator`), tự ẩn trong bản production hoặc khi truyền `?hideDevBar=1`.
- **Routing cho Milestone 2 & 3:**
  - Đã đăng ký đầy đủ route `/studio/presenters`, `/studio/products`, `/studio/knowledge`, `/studio/sessions/new`, `/studio/sessions`, `/studio/members`, `/studio/invites`, `/studio/reports` với trang mô tả phạm vi triển khai rõ ràng và nút quay lại Tổng quan.

---

## 3. Cấu trúc source code (`apps/web/`)

```text
apps/web/
├── index.html                           # Be Vietnam Pro + Inter, lang="vi"
├── package.json / package-lock.json     # Dependencies & scripts
├── tsconfig*.json / vite.config.ts / vitest.config.ts / playwright.config.ts / eslint.config.js
├── public/mockServiceWorker.js          # MSW service worker
├── src/
│   ├── main.tsx                         # Khởi động MSW trước khi render App
│   ├── vite-env.d.ts
│   ├── styles/
│   │   ├── tokens.css                   # Semantic tokens Light + Dark theo UI v0.4
│   │   └── globals.css                  # Tailwind v4, font stack, tabular-nums, reduced-motion
│   ├── types/                           # domain.ts, auth.ts, scenario.ts
│   ├── lib/                             # cn.ts, format.ts, status-copy.ts
│   ├── hooks/                           # useTheme.tsx, useScenario.tsx
│   ├── services/                        # api-client.ts, auth.service.ts
│   ├── mocks/
│   │   ├── browser.ts / server.ts / handlers.ts
│   │   └── fixtures/                    # workspace.fixtures.ts, catalog.fixtures.ts, dashboard.fixtures.ts
│   ├── components/
│   │   ├── ui/                          # Button, Card, StatusBadge, Banner, Skeleton, EmptyState
│   │   └── shared/                      # BrandLogo, ThemeToggle, DevScenarioBar, ModulePreviewPage
│   ├── app/
│   │   ├── App.tsx / router.tsx
│   │   └── layouts/                     # AppShell.tsx, Sidebar.tsx, Topbar.tsx
│   └── features/
│       ├── auth/                        # hooks/useAuth.ts, pages/SignInPage.tsx
│       └── dashboard/                   # types/, services/, hooks/, components/ (6 files), pages/DashboardPage.tsx
└── tests/
    ├── setup.ts                         # Vitest + MSW + jsdom polyfills
    ├── dashboard.test.tsx               # 7 unit/component tests
    └── e2e/visual-qa.spec.ts            # Playwright visual QA (5 viewports, Light/Dark, scenarios)
```

---

## 4. Mock Data và 13 Mock Scenarios

Dữ liệu mô phỏng tiếng Việt tự nhiên, ổn định (không random lại mỗi lần render) xoay quanh workspace mẫu **Đặc sản Mường Lát** (`Owner: Nguyễn Minh Quân`, 2 Operators: `Trần Ngọc Lan` & `Lê Thanh Bình`, 3 AI Presenters, 5 sản phẩm thực phẩm/OCOP `ML-001`–`ML-005`, 4 phiên `#012`–`#015`).

Toàn bộ **13 scenarios** đều truy cập được qua `DevScenarioBar` hoặc query string (`?scenario=<key>&role=OWNER|OPERATOR&theme=light|dark`):

| # | Scenario Key | Trạng thái mô phỏng |
| :-: | :--- | :--- |
| 1 | `happy-path` | Mặc định: Phiên `#014` đang LIVE ổn định + 3 việc cần xử lý + tài nguyên đầy đủ |
| 2 | `empty` | Workspace mới trống, hiển thị hướng dẫn thiết lập ban đầu |
| 3 | `loading` | Skeleton loading giữ nguyên cấu trúc bố cục Dashboard |
| 4 | `error` | Lỗi HTTP 503 khi tải snapshot + nút `Thử tải lại` |
| 5 | `permission-denied` | Lỗi HTTP 403 ngoài phạm vi phân công |
| 6 | `session-live` | Phiên `#014` LIVE + AI ACTIVE + Media HEALTHY |
| 7 | `ai-paused` | Phiên `#014` vẫn LIVE nhưng AI đang `PAUSED` (kèm banner giải thích) |
| 8 | `media-degraded` | Phiên `#014` LIVE + `Media suy giảm` + cảnh sản phẩm dự phòng |
| 9 | `command-conflict` | Banner + tác vụ đối chiếu xung đột lệnh giữa 2 Vận hành viên |
| 10 | `rights-revoked` | Banner đỏ thu hồi quyền Presenter Linh + khóa thẻ tài nguyên Presenter |
| 11 | `verification-pending` | Phiên `#015` bị chặn Start vì chờ xác minh OCOP dù Tri thức đã duyệt |
| 12 | `report-partial` | Phiên `#013` đã kết thúc, báo cáo tổng hợp một phần (thiếu concurrent telemetry) |
| 13 | `invite-expired` | Cảnh báo liên kết mời xem live đã hết hạn |

---

## 5. Hướng dẫn chạy localhost và kiểm thử

```bash
cd apps/web
npm install           # (chỉ cần chạy lần đầu sau khi clone)
npm run dev           # Mở http://127.0.0.1:5173
```

Các lệnh kiểm thử chất lượng:

```bash
cd apps/web
npm run typecheck     # Kiểm tra TypeScript strict
npm run lint          # Kiểm tra ESLint
npm run test          # Chạy Vitest + Testing Library + MSW
npm run build         # Build production bundle
npm run test:e2e      # Chạy Playwright Visual QA & chụp screenshot
```

---

## 6. Kết quả Type-check, Lint, Test và Build

| Kiểm tra | Lệnh | Kết quả | Chi tiết |
| :--- | :--- | :---: | :--- |
| Type-check | `npm run typecheck` | **PASS** | `0` lỗi TypeScript (`strict: true`) |
| Lint | `npm run lint` | **PASS** | `0` lỗi, `0` cảnh báo |
| Unit / Component Test | `npm run test` | **PASS** | `7 / 7` test cases pass (`dashboard.test.tsx`) |
| Production Build | `npm run build` | **PASS** | Build thành công trong `5.09s` (`dist/`) |
| Playwright Visual QA | `npm run test:e2e` | **PASS** | `4 / 4` suites pass, `0` overflow ngang trên cả 5 viewport, xuất đủ 9 screenshots |

---

## 7. Screenshots minh chứng (`screenshots/`)

Toàn bộ ảnh chụp được lưu tại [docs/product/frontend/reports/milestone-01/screenshots/](./screenshots/):

1. [01-dashboard-desktop-1440-light.png](./screenshots/01-dashboard-desktop-1440-light.png) — Desktop `1440×900`, Light Mode, Owner (`happy-path`)
2. [02-dashboard-desktop-1440-dark.png](./screenshots/02-dashboard-desktop-1440-dark.png) — Desktop `1440×900`, Dark Mode, Owner (`happy-path`)
3. [03-dashboard-operator-1920-light.png](./screenshots/03-dashboard-operator-1920-light.png) — Desktop `1920×1080`, Light Mode, Operator (ẩn các mục Owner-only)
4. [04-dashboard-media-degraded-dark.png](./screenshots/04-dashboard-media-degraded-dark.png) — Desktop `1440×900`, Dark Mode, trạng thái `media-degraded`
5. [05-dashboard-tablet-768-light.png](./screenshots/05-dashboard-tablet-768-light.png) — Tablet `768×1024`, Light Mode (sidebar tự thu gọn `72px`)
6. [06-dashboard-mobile-390-light.png](./screenshots/06-dashboard-mobile-390-light.png) — Mobile `390×844`, Light Mode (1 cột, menu drawer, thẻ phiên)
7. [07-dashboard-empty-mobile-375-dark.png](./screenshots/07-dashboard-empty-mobile-375-dark.png) — Mobile `375×812`, Dark Mode, trạng thái `empty`
8. [08-dashboard-error-light.png](./screenshots/08-dashboard-error-light.png) — Desktop `1440×900`, Light Mode, trạng thái lỗi API 503
9. [09-auth-signin-light.png](./screenshots/09-auth-signin-light.png) — Desktop `1440×900`, Light Mode, màn hình đăng nhập OIDC mô phỏng

---

## 8. So sánh giao diện triển khai với HOSTRA UI Redesign v0.4

- **Khớp hoàn toàn với v0.4:**
  - Bảng màu thương hiệu và bề mặt: Sidebar `#0F172A`, Primary CTA `#F5C430` chữ Navy `#0F172A`, Light canvas `#F7F9FC` / card `#FFFFFF`, Dark canvas `#0B1322` / card `#121F32` / nested `#19283E`.
  - Font `Be Vietnam Pro` hiển thị đầy đủ dấu tiếng Việt, số liệu KPI dùng `tabular-nums`, icon vector đồng nhất từ `lucide-react` (không lỗi glyph).
  - Cấu trúc phân cấp thông tin Dashboard: Hero banner → 2 cột Action Center (60%) / Featured Session (40%, không video preview) → 4 Asset Cards → 3 Recent Sessions.
  - Phân quyền RBAC thể hiện trực quan giữa Owner và Operator.
- **Khác biệt nhỏ / điều chỉnh có chủ đích:**
  - Trong `FeaturedSessionCard`, dùng biểu tượng vector đại diện phiên thay vì ảnh nhân vật tĩnh để tuân thủ chặt `D5` (không gây hiểu nhầm có live video preview trên Dashboard).
  - Bổ sung bảng `Phiên livestream gần đây` (Z06) rõ ràng ngay dưới 4 Asset Cards để khớp đầy đủ đặc tả `Dashboard v0.4` (`D8`).

---

## 9. Các vấn đề tồn đọng ghi nhận sau Visual QA

1. **Đồng bộ badge bảng Recent Sessions trong scenario `media-degraded`:** Trong ảnh `04-dashboard-media-degraded-dark.png`, thẻ `Phiên gần nhất` hiển thị đúng `Media suy giảm`, nhưng dòng `#014` trong bảng `Phiên livestream gần đây` vẫn tham chiếu bản gốc `SESSION_LIVE_014` (`Media ổn định`). Cần đồng bộ mảng `recentSessions` với `featuredSession` trong `dashboard.fixtures.ts` ở lượt polish tiếp theo.
2. **Micro-UI trên Mobile `390px`:** Các dòng `ActionCenter` có tiêu đề dài bị cắt dấu ba chấm (`...`) khi đứng cùng hàng với badge trạng thái; trên mobile nên cho badge xuống dòng gọn hơn và đặt `whitespace-nowrap` hợp lý cho badge trạng thái ở thẻ phiên.
3. **Cấu hình môi trường repo (đã nêu ở Dependency Audit):** Cần cập nhật `.gitignore` gốc để chặn `apps/web/node_modules/`, `apps/web/dist/`, `apps/web/test-artifacts/` trước khi commit, và bổ sung fallback Chromium trong `playwright.config.ts` cho môi trường Linux/CI.

---

## 10. Checklist nghiệm thu Milestone 1 & Đề xuất bước tiếp theo

- [x] Chạy được trên localhost (`vite dev` / `vite preview`) với dữ liệu mock thực tế qua MSW.
- [x] Kiến trúc modular theo feature (`app/`, `components/`, `features/`, `mocks/`, `services/`, `styles/`), không dồn code vào một file.
- [x] Light Mode & Dark Mode chuẩn HOSTRA UI v0.4.
- [x] Responsive đạt yêu cầu trên Desktop (`1440`, `1920`), Tablet (`768`), Mobile (`390`, `375`), `0` overflow ngang.
- [x] Phân quyền Owner vs Operator và tách biệt trạng thái `LIVE` / `AI PAUSED` / `MEDIA DEGRADED` đúng đặc tả.
- [x] `typecheck`, `lint`, `vitest` (7/7), `vite build` và Playwright Visual QA (9 screenshots) đều PASS.
- [x] Không chỉnh sửa `apps/api/`, `experiments/`, `workers/`, không tự commit/push/merge.

**Đề xuất bước tiếp theo (chờ bạn review Milestone 1 trước khi triển khai):**
1. Xử lý nhanh 2 điểm polish nhỏ ở mục 9 (đồng bộ `recentSessions` cho `media-degraded` + bố cục badge mobile 390px) và cập nhật `.gitignore` cho `apps/web/`.
2. Chuyển sang **Milestone 2 — Merchant Asset Preparation:** triển khai đầy đủ giao diện tương tác mock-first cho **AI Presenter Studio**, **Products & OCOP**, **Knowledge & Claims**, **Story Planner**, **Live Session Setup** và **Readiness Checklist**.
