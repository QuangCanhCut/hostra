# HOSTRA AI — Báo cáo Kiểm thử Hồi quy Toàn diện (Milestone 05.4)

**Ngày thực hiện:** 22/11/2026  
**Môi trường kiểm thử:** Windows · Node.js · Vite 6.4.6 · Vitest 3.2.7 · Chromium (`channel: chrome`, headless) trên bản build production (`apps/web/dist/` phục vụ qua `vite preview`)  
**Phương thức xác minh:** **100% Mock API + Tự động hóa trình duyệt Chromium** *(chưa kết nối Backend thật, LiveKit thật hay OIDC thật)*.

---

## 1. Kết quả kiểm tra chất lượng mã nguồn & Build (`D1`)

| Hạng mục | Lệnh thực thi | Kết quả | Chi tiết |
| :--- | :--- | :---: | :--- |
| TypeScript Typecheck | `npm run typecheck` (`tsc -b --noEmit`) | **PASS** | 0 lỗi kiểu dữ liệu |
| ESLint | `npm run lint` (`eslint .`) | **PASS** | 0 lỗi, 0 cảnh báo |
| Unit & Component Tests | `npm run test` (`vitest run`) | **PASS** | **5/5 tệp, 31/31 test cases PASS** (tăng +4 test mới của M05.4) |
| Production Build | `npm run build` (`tsc -b && vite build`) | **PASS** | Build sạch trong `8.54s`, bundle chính `index-*.js` (`399.76 kB` / gzip `125.22 kB`) |

### Chi tiết 5 bộ kiểm thử Vitest (`31/31 PASS`)
1. `tests/dashboard.test.tsx` — **7/7 PASS** (Owner/Operator RBAC, independent LIVE/AI/Media badges, Action Center, Featured Session, `ButtonLink` Tạo phiên mới).
2. `tests/m02-workflows.test.tsx` — **9/9 PASS** (Presenter A/B compare, AI Editing diff + medical claim guard, SKU Picker 2–5 SKUs & duplicate guard, Readiness blocks Start when OCOP/Story incomplete).
3. `tests/m03-workflows.test.tsx` — **6/6 PASS** (SKU Picker sync, Members N:N RBAC, `PAUSE_AI` giữ `LIVE`, Viewer standalone + nickname admission, CSV Formula Injection neutralization, PDF 1.4 header/EOF, Owner-only Export).
4. `tests/m04-uat-reconciliation.test.tsx` — **5/5 PASS** (Gate 1 & Gate 2 cross-module invariants, `PENDING`/`PARTIAL`/`READY` export messaging).
5. `tests/m05-4-account-and-closure.test.tsx` — **4/4 PASS** (Mới: PO-D01 Account Menu mở/đóng `Escape` + khôi phục focus, điều hướng `/studio/onboarding` & `/auth/sign-in`, UX-04 `0` nested interactive trên Dashboard, PO-D02 nguồn đo tiếng Việt thân thiện trên Reports).

---

## 2. Kết quả kiểm thử hồi quy trên trình duyệt Chromium (`D2–D4`)

Nguồn bằng chứng: [tests/evidence/m05_4_regression_evidence.json](./tests/evidence/m05_4_regression_evidence.json)

### 2.1. Kiểm tra chức năng & hành trình trọng yếu
| Nhóm kiểm tra | Kết quả | Minh chứng |
| :--- | :---: | :--- |
| **PO-D01** Account Dropdown Menu (mở, đóng `Escape`, khôi phục focus về nút Avatar) | **PASS** | `accountMenuEscapeFocusRestore.pass = true`, [01-account-menu-open.png](./screenshots/01-account-menu-open.png) |
| **PO-D01** Điều hướng `Thiết lập không gian làm việc` & `Đăng xuất` mô phỏng → `/auth/sign-in` | **PASS** | `accountMenuSignOut.pass = true`, không xóa dữ liệu mock store |
| **PO-D02 / UX-06** Microcopy thân thiện trên Reports, Readiness & Onboarding (không lộ `P04`, `P09`, `P11`, `AW-D2`, `LiveKit Presence Telemetry`) | **PASS** | `reportFriendlyMicrocopy.pass = true`, `readinessFriendlyMicrocopy.pass = true`, `onboardingNoAwD2.pass = true` |
| **B1** Live Control Room Sticky Action Bar hiển thị trong viewport khi cuộn cuối trang | **PASS** | `controlRoomStickyBar.pass = true`, [06-control-room-m054.png](./screenshots/06-control-room-m054.png) |
| **B3** Viewer Live Room (`375×812`) nhập nickname, gửi bình luận & không có nút điều khiển merchant | **PASS** | `viewerCommentAndNoMerchantControls.pass = true`, [07-viewer-mobile-m054.png](./screenshots/07-viewer-mobile-m054.png) |
| **B4** Lời mời & Mã QR khớp origin hiện tại (`http://127.0.0.1:4181/live/...`) | **PASS** | `invitesQrOriginMatch.pass = true`, [08-invites-qr-m054.png](./screenshots/08-invites-qr-m054.png) |
| Chuyển đổi Light Mode ↔ Dark Mode (`data-theme="dark"`) | **PASS** | `darkModeToggle.pass = true`, [02-dashboard-light-m054.png](./screenshots/02-dashboard-light-m054.png) & [03-dashboard-dark-m054.png](./screenshots/03-dashboard-dark-m054.png) |
| Zoom 200% (`640×400` reflow) & `prefers-reduced-motion: reduce` | **PASS** | `zoom200Overflow = 0px`, `prefersReduced = true` |
| Ảnh vỡ (`brokenImages`) trên 12 tuyến trang | **PASS** | **`0`** ảnh lỗi |
| Lỗi ứng dụng trên Console & PageError | **PASS** | **`0`** lỗi ứng dụng *(ghi nhận 27 cảnh báo `ERR_NAME_NOT_RESOLVED` do sandbox chạy ngoại tuyến không tải được Google Fonts — font fallback hiển thị bình thường)* |

### 2.2. Kiểm toán phần tử tương tác lồng nhau (`UX-04`) trên 12 tuyến trang
| Tuyến trang | `a button, button a, a a, button button` | Ảnh lỗi | Kết quả |
| :--- | :---: | :---: | :---: |
| `/studio` (Dashboard) | `0` | `0` | **PASS** |
| `/studio/presenters` | `0` | `0` | **PASS** |
| `/studio/products` | `0` | `0` | **PASS** |
| `/studio/knowledge` | `0` | `0` | **PASS** |
| `/studio/sessions` | `0` | `0` | **PASS** |
| `/studio/sessions/ses-014/setup` | `0` | `0` | **PASS** |
| `/studio/sessions/ses-014/readiness` | `0` | `0` | **PASS** |
| `/studio/sessions/ses-014/control` | `0` | `0` | **PASS** |
| `/studio/sessions/ses-013/report` | `0` | `0` | **PASS** |
| `/studio/members` | `0` | `0` | **PASS** |
| `/studio/invites` | `0` | `0` | **PASS** |
| `/live/ses-014?invite=ml014-doitac` | `0` | `0` | **PASS** |

### 2.3. Ma trận kiểm thử Responsive trên 7 kích thước màn hình (`320px` → `1920px`)
| Viewport | Tuyến trang | Tràn ngang (`overflowPx`) | Kết quả |
| :--- | :--- | :---: | :---: |
| `320×568` (Mobile nhỏ) | Dashboard & Viewer Live Room | `0px` | **PASS** |
| `375×812` (iPhone tiêu chuẩn) | Dashboard & Viewer Live Room | `0px` | **PASS** |
| `390×844` (Mobile chuẩn thiết kế) | Dashboard | `0px` | **PASS** |
| `768×1024` (Tablet dọc) | Dashboard | `0px` | **PASS** |
| `1024×768` (Tablet ngang / Laptop nhỏ) | Dashboard | `0px` | **PASS** |
| `1280×800` (Laptop tiêu chuẩn) | Dashboard | `0px` | **PASS** |
| `1920×1080` (Desktop lớn) | Dashboard | `0px` | **PASS** |

---

## 3. Hạng mục chưa thuộc phạm vi kiểm thử tự động M05.4
- **Kiểm thử người dùng thật (Human Usability Testing):** Chưa thực hiện với chủ shop OCOP thật (`PENDING HUMAN TEST` — xem kế hoạch tại [HUMAN_USABILITY_TEST_PLAN.md](./HUMAN_USABILITY_TEST_PLAN.md)).
- **Trình duyệt ngoài Chromium (Firefox, Safari iOS thật):** Chưa kiểm thử tự động trong môi trường Windows sandbox hiện tại; khuyến nghị kiểm tra thủ công trước khi mở rộng pilot thực tế.
- **Tích hợp Backend, AI Pipeline, LiveKit & OIDC thật:** Chưa tồn tại trong phạm vi Frontend Mock MVP.
