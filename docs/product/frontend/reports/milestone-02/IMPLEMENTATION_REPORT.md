# HOSTRA AI — Báo cáo triển khai Frontend Milestone 2 (Merchant Studio & Asset Preparation)

| Mục | Thông tin |
| :--- | :--- |
| **Milestone** | Milestone 2 — Merchant Studio & Asset Preparation (Full Mock Implementation) |
| **Nhánh làm việc** | `feat/frontend-foundation` |
| **Phạm vi mã nguồn** | `apps/web/` + bổ sung pattern frontend vào `.gitignore` gốc |
| **Visual Baseline** | **HOSTRA UI Redesign v0.4 — APPROVED** + Global Design System v0.2 |
| **Ngày lập báo cáo** | 21/11/2026 |
| **Trạng thái** | **HOÀN THÀNH MILESTONE 2 — Sẵn sàng Review** *(chưa chuyển sang Milestone 3)* |

---

## 1. Executive Summary & Trạng thái hoàn thành

Milestone 2 đã hoàn thiện toàn bộ các module chuẩn bị tài sản và thiết lập phiên livestream trong `apps/web/` bằng kiến trúc **single canonical mock store + MSW**, kế thừa nguyên vẹn nền tảng M01, sửa triệt để 5 hạng mục tồn đọng của M01 (`M01-FIX-01`–`M01-FIX-05`), và cho phép thao tác xuyên suốt từ **Onboarding → AI Presenter Studio (+ Cổng Chủ thể quyền) → Products & OCOP → Knowledge & Claims → Story Planner → Session Setup → Readiness Checklist**.

| Nhóm công việc | Trạng thái | Ghi chú kiểm chứng |
| :--- | :---: | :--- |
| M01 Fixes (`M01-FIX-01`–`M01-FIX-05`) | **DONE** | Đã kiểm chứng qua Vitest regression + Playwright Tablet/Mobile screenshots |
| M02-A: AI Presenter Studio + Rights Portal | **DONE** | Library, 4-step Wizard (3 styles), Detail/QC/Retry clip/A-B Compare, Rights Portal độc lập |
| M02-B: Products & OCOP | **DONE** | Catalog, 4-step Wizard, Detail 4 tabs, Evidence upload, Owner Submit, P09 Reviewer mock |
| M02-C: Knowledge & Claims | **DONE** | Library, 2-pane Source vs 5 groups, per-item decisions, blocked medical claim, text preview |
| M02-D: Story Planner | **DONE** | 5-arc Timeline, reorder, AI Editing Assistant (diff + unsupported claim guard), Owner approval |
| M02-E: Live Session Setup | **DONE** | Unified `#012`–`#015`, 4-step Wizard, 2-col SKU Picker (2–5 SKUs, drag-drop + buttons) |
| M02-F: Readiness Checklist & Onboarding | **DONE** | 7 cổng kiểm tra tính động từ canonical store, Owner-only mock START (`ACCEPTED → LIVE`) |

---

## 2. Phạm vi thực tế đã triển khai

- **Đã triển khai đầy đủ tương tác mock-first:**
  - Workspace Onboarding (`/studio/onboarding`) với Save Draft & deep-links.
  - AI Presenter Studio (`/studio/presenters`, `/studio/presenters/new`, `/studio/presenters/:id`) và Rights Subject Consent Portal độc lập (`/rights/consent/:requestId`).
  - Products & OCOP (`/studio/products`, `/studio/products/new`, `/studio/products/:skuId?tab=overview|ocop|facts|versions`).
  - Knowledge & Claims (`/studio/knowledge`, `/studio/knowledge/:skuId`).
  - Story Planner (`/studio/sessions/:id/story`).
  - Live Session Setup & Sessions List (`/studio/sessions`, `/studio/sessions/new`, `/studio/sessions/:id`, `/studio/sessions/:id/setup`).
  - Readiness Checklist (`/studio/sessions/:id/readiness`).
- **Thuộc phạm vi Milestone 3 (giữ trang định hướng rõ ràng, không tạo mock realtime giả phức tạp):** Live Control Room, Invite Management, Viewer Live Room, Members & Permissions, Session Reports.

---

## 3. Những lỗi M01 đã sửa (`M01-FIX-01` → `M01-FIX-05`)

1. **`M01-FIX-01` — Đồng bộ session fixtures:** Chuyển sang single canonical mock store (`src/mocks/store.ts`). `FeaturedSessionCard` và `RecentSessionsSection` cùng đọc từ một danh sách `store.sessions` duy nhất — trong `media-degraded` và `ai-paused`, Phiên `#014` hiển thị đồng nhất ở mọi vị trí.
2. **`M01-FIX-02` — Responsive Recent Sessions:** Đổi breakpoint bảng từ `md:` (`768px`) sang `xl:` (`1280px`). Trên Tablet `768×1024`, giao diện chuyển sang lưới **2 cột session cards** thoáng rõ, không còn tình trạng cột bảng bị bóp chữ.
3. **`M01-FIX-03` — Action Center Mobile:** Đổi layout hàng tác vụ sang `flex-col sm:flex-row` ở màn hình hẹp để tiêu đề tiếng Việt hiển thị đầy đủ, không bị cắt dấu ba chấm quá sớm.
4. **`M01-FIX-04` — Đồng nhất KPI Dashboard:** Số lượng trên 4 Asset Status Cards tính trực tiếp từ canonical store (`AI Presenter = 03` khớp 3 bản ghi Linh/Mai/An; `Sản phẩm & OCOP = 05`; `Tri thức & Claims = 04/5 SKU`; `Phiên đã tạo = 04`).
5. **`M01-FIX-05` — Gitignore & Playwright Cross-Platform:**
   - Bổ sung đúng các pattern frontend vào `.gitignore` gốc (`node_modules/`, `apps/web/dist/`, `apps/web/test-artifacts/`, `playwright-report/`, `*.tsbuildinfo`).
   - Cập nhật `apps/web/playwright.config.ts` để dùng `channel: 'chrome'` trên Windows và tự fallback sang Chromium trên Linux/CI (hoặc qua biến `PW_CHANNEL`).
   - Xác minh kích thước pixel thực của từng file PNG bằng Pillow (bảng mục 10).

---

## 4. Kiến trúc và cấu trúc thư mục (`apps/web/src/`)

```text
apps/web/src/
├── app/                     # App.tsx, router.tsx, layouts/ (AppShell, Sidebar, Topbar)
├── components/
│   ├── ui/                  # Button, Card, StatusBadge, Banner, Skeleton, EmptyState, Tabs, Modal, Drawer
│   └── shared/              # BrandLogo, ThemeToggle, DevScenarioBar (+ Reset), PortraitAvatar, ModulePreviewPage
├── features/
│   ├── auth/                # useAuth, SignInPage
│   ├── dashboard/           # DashboardPage + 6 components (đã áp dụng M01 fixes)
│   ├── workspace/           # OnboardingPage
│   ├── presenter/           # PresenterLibraryPage, PresenterWizardPage, PresenterDetailPage, RightsConsentPortalPage
│   ├── products/            # ProductsCatalogPage, ProductWizardPage, ProductDetailPage
│   ├── knowledge/           # KnowledgeLibraryPage, KnowledgeReviewPage
│   ├── story-planner/       # StoryPlannerPage
│   └── live-session/        # SessionsListPage, SessionWizardPage, SessionDetailPage, ReadinessPage
├── mocks/
│   ├── store.ts             # Canonical stateful mock store + dynamic Readiness calculator + Dashboard sync
│   ├── handlers.ts          # MSW REST handlers cho toàn bộ M01 + M02 + RBAC enforcement
│   └── fixtures/            # workspace, catalog, dashboard, m02 fixtures
├── services/                # api-client.ts, auth.service.ts
├── styles/                  # tokens.css (v0.4 Light/Dark), globals.css
├── hooks/                   # useTheme.tsx, useScenario.tsx
├── lib/                     # cn.ts, format.ts, status-copy.ts
└── types/                   # domain.ts, auth.ts, scenario.ts, m02.ts
```

---

## 5. Danh sách Routes, Pages & Components chính

| Route | Page | Vai trò & Quyền |
| :--- | :--- | :--- |
| `/studio/onboarding` | `OnboardingPage` | Owner lưu nháp; Operator chỉ xem |
| `/studio/presenters` | `PresenterLibraryPage` | Owner quản lý + tạo mới; Operator xem theo scope |
| `/studio/presenters/new` | `PresenterWizardPage` | Owner-only (4 bước, 3 style presets, Licensed Voice) |
| `/studio/presenters/:id` | `PresenterDetailPage` | Owner generate/retry clip/duyệt; Operator chỉ xem |
| `/rights/consent/:requestId` | `RightsConsentPortalPage` | Rights Subject độc lập (Đồng ý / Từ chối / Thu hồi) |
| `/studio/products` | `ProductsCatalogPage` | Owner & Operator (desktop table `xl:` / mobile+tablet cards) |
| `/studio/products/new` | `ProductWizardPage` | Operator lưu nháp; Owner-only Gửi xác minh OCOP |
| `/studio/products/:skuId` | `ProductDetailPage` | 4 tabs (`overview`, `ocop`, `facts`, `versions`) + P09 mock panel |
| `/studio/knowledge` | `KnowledgeLibraryPage` | Owner & Operator |
| `/studio/knowledge/:skuId` | `KnowledgeReviewPage` | 2-pane Source vs 5 groups; Owner-only duyệt mục & gói |
| `/studio/sessions` | `SessionsListPage` | Owner toàn workspace; Operator chỉ phiên được phân công |
| `/studio/sessions/new` & `/:id/setup` | `SessionWizardPage` | Owner-only (4 bước, SKU Picker 2–5 SKU kéo-thả + nút) |
| `/studio/sessions/:id` | `SessionDetailPage` | Tổng hợp phiên bản Presenter/SKU/Story/Readiness |
| `/studio/sessions/:id/story` | `StoryPlannerPage` | Timeline 5 arcs, AI Editing Assistant (diff), Owner duyệt |
| `/studio/sessions/:id/readiness` | `ReadinessPage` | 7 cổng kiểm tra độc lập; Owner-only mock `START` |

---

## 6. Mock Data, Scenarios và Mutations

- **Dataset nhất quán với M01:** Workspace `Đặc sản Mường Lát`, Owner `Nguyễn Minh Quân`, 2 Operators (`Trần Ngọc Lan`, `Lê Thanh Bình`), 3 Presenters (`Linh` v2 đã duyệt + 2 candidates để so A/B, `Mai` v1 có 1 clip lỗi QC cho phép retry clip, `An` đang chờ quyền), 5 SKUs (`ML-001`–`ML-005`), 4 Sessions (`#012`–`#015`).
- **13 Global Scenarios** giữ nguyên từ M01 + nút **`Đặt lại dữ liệu mô phỏng`** (`POST /api/mock/v1/reset`) ngay trong `DevScenarioBar`.
- **Mutations có liên kết xuyên module:**
  - `POST /api/mock/v1/presenters`, `/generate`, `/retry-clip`, `/approve`
  - `POST /api/mock/v1/rights/:requestId/decision` *(thu hồi quyền lập tức khóa Presenter và chặn Readiness các phiên liên quan)*
  - `POST /api/mock/v1/products`, `/:skuId/evidence`, `/:skuId/submit-ocop`, `/:skuId/mock-reviewer-verdict` *(cập nhật OCOP tự động tính lại Readiness)*
  - `POST /api/mock/v1/knowledge/:skuId/items/:itemId/decision`, `/:skuId/approve-bundle`
  - `PUT /api/mock/v1/sessions/:id/story`, `POST .../story/ai-suggest`, `.../story/ai-apply`, `.../story/approve`
  - `POST /api/mock/v1/sessions`, `PUT /api/mock/v1/sessions/:id` *(đổi SKU làm `INVALIDATED` Story Plan)*, `POST /api/mock/v1/sessions/:id/start` *(vòng đời `ACCEPTED (STARTING) → APPLIED (LIVE)`)*

---

## 7. Các User Flows đã hoạt động

- **Flow A — Presenter:** Library → Wizard 4 bước (3 styles) → Cổng Rights Subject xác nhận → Generate / Retry clip lỗi → So sánh A/B (khi ≥2 candidates) → Owner phê duyệt.
- **Flow B — Products & OCOP:** Catalog → Product Wizard → Upload tài liệu OCOP → Owner Submit → Mô phỏng kết quả P09 Reviewer → Đồng bộ Eligibility.
- **Flow C — Knowledge:** Library → Đối chiếu tài liệu nguồn & 5 nhóm Facts/Claims → Loại bỏ claim chữa bệnh bị chặn → Duyệt từng mục bắt buộc → Owner duyệt gói → Xem trước lời AI văn bản kèm nguồn.
- **Flow D — Story Planner:** Timeline 5 đoạn → Đổi thứ tự / Đánh dấu rà soát → Chat Trợ lý AI → Xem diff Trước/Sau (tự chặn claim chữa bệnh) → Áp dụng vào bản nháp → Owner duyệt toàn bộ phiên bản.
- **Flow E — Session & Readiness:** Tạo phiên → Chọn Presenter + 2–5 SKU (chặn trùng & SKU thứ 6) → Goal → Story → Readiness Checklist → Xử lý từng điểm chặn → Owner Start (`ACCEPTED → STARTING → LIVE`).
- **Flow F — Operator Restrictions:** Ẩn mục Owner-only trên Sidebar/Dashboard/Readiness; cho phép Operator tạo nháp & tải tài liệu sản phẩm nhưng chặn Submit OCOP, Approve Knowledge/Story và Start (cả UI và MSW handler trả 403).
- **Flow G — Cross-module Invalidation:** Thu hồi quyền Presenter hoặc đổi SKU / hạ OCOP lập tức làm Readiness chuyển sang `BLOCKED` và khóa nút `Bắt đầu livestream`.

---

## 8. RBAC & Safety Rules đã kiểm thử

- Owner-only: Tạo/duyệt Presenter, Submit OCOP, duyệt mục/gói Knowledge, sửa/duyệt Story pre-live, tạo phiên và `START` livestream.
- Operator: Chỉ xem phiên được phân công, tạo bản nháp & tải tài liệu sản phẩm (`PC-D4=B`), không tự phê duyệt hay `START`.
- Rights Subject: Luồng độc lập `/rights/consent/:requestId`, tách biệt ảnh/video với voice cloning.
- OCOP Verification: Merchant không tự đặt `VERIFIED`; tách riêng bảng mô phỏng P09 Reviewer.
- Command & State Safety: `ACCEPTED` (`STARTING`) tách khỏi `APPLIED` (`LIVE`); claim y tế bị chặn không thể duyệt.

---

## 9. Kết quả Typecheck, Lint, Unit Tests, E2E & Build

| Kiểm tra | Lệnh | Kết quả | Chi tiết |
| :--- | :--- | :---: | :--- |
| Type-check | `npm run typecheck` | **PASS** | `0` lỗi TypeScript (`strict: true`) |
| Lint | `npm run lint` | **PASS** | `0` lỗi, `0` cảnh báo |
| Unit / Component Test | `npm run test` | **PASS** | `16 / 16` tests pass (`7` M01 regression + `9` M02 workflows) |
| Production Build | `npm run build` | **PASS** | Build thành công trong `6.04s` (`dist/`) |
| Playwright E2E + Layout Health | `npx playwright test tests/e2e/m02-visual-qa.spec.ts` | **PASS** | `4 / 4` suites pass, `0` overflow ngang, `0` cột bảng bị bóp `< 64px`, `13` screenshots |

---

## 10. Screenshots minh chứng (kèm Viewport & Kích thước ảnh thực tế)

Lưu tại [docs/product/frontend/reports/milestone-02/screenshots/](./screenshots/):

| # | File | Viewport đặt | Kích thước PNG thực | Nội dung |
| :-: | :--- | :---: | :---: | :--- |
| 1 | [01-dashboard-m01fix-tablet-768-light.png](./screenshots/01-dashboard-m01fix-tablet-768-light.png) | `768×1024` | `768×1877` | Dashboard Tablet Light — sửa bảng thành cards + đồng bộ `Media suy giảm` + KPI `03` |
| 2 | [02-dashboard-m01fix-mobile-390-light.png](./screenshots/02-dashboard-m01fix-mobile-390-light.png) | `390×844` | `390×2462` | Dashboard Mobile Light — sửa cắt tiêu đề Action Center |
| 3 | [03-presenter-library-1440-light.png](./screenshots/03-presenter-library-1440-light.png) | `1440×900` | `1440×900` | AI Presenter Library — Card grid 4:3 đồng đều, Light Mode |
| 4 | [04-presenter-wizard-styles-1440-light.png](./screenshots/04-presenter-wizard-styles-1440-light.png) | `1440×900` | `1440×900` | Presenter Wizard — 3 style presets (`Chuyên nghiệp`, `Thân thiện`, `Năng động`) & Licensed Voice |
| 5 | [05-presenter-ab-compare-1440-dark.png](./screenshots/05-presenter-ab-compare-1440-dark.png) | `1440×900` | `1440×900` | Presenter Detail Dark — So sánh Video A/B + QC + Owner Approval |
| 6 | [06-rights-consent-portal-1440-light.png](./screenshots/06-rights-consent-portal-1440-light.png) | `1440×900` | `1440×900` | Cổng xác nhận Chủ thể quyền độc lập (`/rights/consent/...`) |
| 7 | [07-products-catalog-1440-light.png](./screenshots/07-products-catalog-1440-light.png) | `1440×900` | `1440×900` | Danh mục Sản phẩm & OCOP — tách biệt cột OCOP, Tri thức & Điều kiện phiên |
| 8 | [08-product-ocop-evidence-1440-light.png](./screenshots/08-product-ocop-evidence-1440-light.png) | `1440×900` | `1440×900` | Chi tiết sản phẩm Tab OCOP — Dropzone, checklist thiếu chứng cứ & mô phỏng P09 |
| 9 | [09-knowledge-review-1440-dark.png](./screenshots/09-knowledge-review-1440-dark.png) | `1440×900` | `1440×1839` | Knowledge Review Dark — 2 cột nguồn/facts, 5 nhóm, claim chữa bệnh bị chặn, speech preview |
| 10 | [10-story-planner-ai-diff-1440-light.png](./screenshots/10-story-planner-ai-diff-1440-light.png) | `1440×900` | `1440×1197` | Story Planner Light — 5 Story Arcs + Trợ lý AI tạo diff Trước/Sau |
| 11 | [11-session-sku-picker-1920-light.png](./screenshots/11-session-sku-picker-1920-light.png) | `1920×1080` | `1920×1080` | Session Setup SKU Picker 2 cột (kéo-thả + nút sắp xếp 2–5 SKU) |
| 12 | [12-readiness-blocked-1440-dark.png](./screenshots/12-readiness-blocked-1440-dark.png) | `1440×900` | `1440×1015` | Readiness Checklist Dark — 7 cổng độc lập, chặn Start khi còn điểm chờ/chặn |
| 13 | [13-readiness-operator-mobile-375-light.png](./screenshots/13-readiness-operator-mobile-375-light.png) | `375×812` | `375×1865` | Readiness Mobile `375px` — vai trò Operator (không có nút Bắt đầu livestream) |

---

## 11. So sánh giao diện với HOSTRA UI Redesign v0.4

- Giữ đúng bảng màu v0.4 (`#0F172A`, `#F5C430`, `#FBE580`, `#DC2626`, Light `#F7F9FC`/`#FFFFFF`, Dark `#0B1322`/`#121F32`/`#19283E`), font `Be Vietnam Pro`, bo góc `12px`, icon vector Lucide, OCOP badge nằm ngoài thumbnail, và ảnh Presenter tỷ lệ 4:3 đồng nhất không pillarbox.
- Từng module có bố cục đặc thù đúng như thiết kế (Card Grid 4:3 cho Presenter, 2-pane Evidence/Facts cho Knowledge, Timeline + AI Diff Panel cho Story Planner, 2-column SKU Picker cho Session Setup, Checklist độc lập cho Readiness).

---

## 12. Các khác biệt có chủ đích so với Design

- Sử dụng minh họa SVG cục bộ (`PortraitAvatar.tsx`) thay cho ảnh chân dung/video thực để đảm bảo 100% không vỡ ảnh khi chạy offline/CI và không vướng vấn đề bản quyền ảnh người thật.
- Hiển thị bảng mô phỏng kết quả **Reviewer / Hệ thống P09 (Dev)** tách biệt rõ ở Tab OCOP để người review có thể tự bấm kiểm thử luồng `PENDING_REVIEW → VERIFIED / REVOKED` và quan sát Readiness tự tính lại theo thời gian thực.

---

## 13. Blockers, Technical Debt & Unvalidated Assumptions

- **Chưa kết nối backend / AI thật:** Toàn bộ generation, Docling extraction, P09 OCOP verdict, AI Editing Assistant và lệnh `START` là mô phỏng deterministic qua MSW.
- **Quyền Operator sửa pre-live Session/Story (`SS-OP-PRELIVE`):** Vẫn đang `OPEN` trong tài liệu — tạm khóa chỉ cho Owner và ghi rõ trong UI.
- **Bundle size Vite:** `dist/assets/index-*.js` đạt `565.88 kB` (`157.29 kB` gzip); nên bổ sung `React.lazy` code-splitting theo từng feature route ở Milestone 3 để giảm kích thước chunk ban đầu xuống dưới `500 kB`.

---

## 14. Hướng dẫn chạy Frontend trên Localhost

```powershell
cd apps/web
npm install           # (chỉ cần lần đầu sau khi clone)
npm run dev           # Mở http://127.0.0.1:5173
```

Gợi ý luồng trải nghiệm nhanh trên localhost:
1. Dùng nút **`Mock: Owner`** (góc dưới phải) để chuyển vai trò `Owner` / `Operator`, đổi 13 scenarios hoặc bấm **`Đặt lại dữ liệu mô phỏng`**.
2. Đi từ `AI Presenter` → bấm **`Cổng quyền`** của Presenter An → cấp quyền → quay lại tạo clip.
3. Vào `Sản phẩm & OCOP` → mở `ML-003` → Tab `Hồ sơ OCOP` → bấm `P09: Xác minh đạt` → mở `Phiên #015` → `Story Planner` → rà soát 5 đoạn và duyệt → vào `Readiness Checklist` để thấy toàn bộ 7 cổng chuyển `Đạt` và kích hoạt nút **`Bắt đầu livestream`**.

---

## 15. Checklist nghiệm thu từng module Milestone 2

- [x] `M01-FIX-01..05`: Đồng bộ `media-degraded`, Tablet 768 cards, Mobile Action Center, KPI Presenter `03`, `.gitignore` + Playwright portable.
- [x] `M02-A`: Presenter Library, 4-step Wizard (3 style presets + Licensed Voice), Rights Portal độc lập, Retry clip lỗi, A/B compare chỉ khi ≥2 candidates, Owner Approve.
- [x] `M02-B`: Products Catalog (desktop table / tablet+mobile cards), 4-step Wizard, 4-tab Detail, Evidence upload, Owner-only Submit OCOP, P09 mock verdict.
- [x] `M02-C`: Knowledge Library, 2-pane Source vs 5 groups, mobile evidence drawer, chặn claim y tế, duyệt từng mục + Owner duyệt gói, Text Speech Preview có nguồn.
- [x] `M02-D`: Story Planner 5 arcs, reorder, AI Editing Assistant (diff Trước/Sau + chặn claim thiếu nguồn), Owner duyệt toàn phiên bản.
- [x] `M02-E`: Sessions List (`#012`–`#015`), 4-step Session Wizard, 2-col SKU Picker (kéo-thả + nút, 2–5 SKU, chặn trùng/SKU thứ 6), Session Detail.
- [x] `M02-F`: Readiness Checklist tách riêng (7 cổng tính động), Owner-only mock START (`ACCEPTED → STARTING → LIVE`), Workspace Onboarding Save Draft.
- [x] `typecheck`, `lint`, `vitest` (`16/16`), `vite build` và Playwright Visual QA (`4/4`, `13` screenshots) PASS; không sửa `apps/api/`, `experiments/`, `workers/`, không tự commit/push.

---

## 16. Phạm vi đề xuất cho Milestone 3

1. **Live Control Room (`/studio/sessions/:id/control`):** 2 cột 60/40, mô phỏng LIVE / AI PAUSED / Pending SKU Switch / Media DEGRADED / Concurrent Command Conflict / Emergency Stop quick-confirm 1 bước + Diagnostics drawer.
2. **Invite Management (`/studio/sessions/:id/invites`) & Viewer Live Room (`/live/:id`):** Named links bất biến + QR code + Revoke ngắt viewer; Viewer Mobile-first (390×844) với Waiting Room, LIVE comments (`SENDING → RECEIVED`), buffering & chat reconnect độc lập, Session Ended.
3. **Members & Permissions (`/studio/members`):** Mời email Operator, phân công nhiều Operator/session (N:N), thu hồi & Audit Log.
4. **Session Reports (`/studio/sessions/:id/report`):** 4 KPIs theo Playback ACK, biểu đồ lượt vào & state timeline có provenance, trạng thái `PARTIAL`/`N/A`, Owner export CSV/PDF.
5. **Tối ưu hiệu năng:** Lazy-loading route chunks (`React.lazy`) cho từng module.
