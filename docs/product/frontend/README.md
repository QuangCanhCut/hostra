# HOSTRA AI — Frontend Documentation Hub

> **Điểm bắt đầu đọc tài liệu cho toàn bộ Frontend Developers và Coding Agents.**
> Tài liệu này tổng hợp phạm vi MVP, kiến trúc frontend, hệ thống thiết kế đã nghiệm thu, quy tắc trạng thái/an toàn và bản đồ tài liệu nguồn trong `docs/product/frontend/`.
>
> Xem sổ quyết định chính thức theo từng module tại [DECISIONS.md](./DECISIONS.md).

---

## 1. Project Overview

**HOSTRA AI** là nền tảng *autonomous AI-powered livestream commerce* cho phép nhà bán hàng (đặc biệt nhóm thực phẩm đóng gói / sản phẩm OCOP) tạo AI Presenter hợp pháp, chuẩn hóa tri thức sản phẩm đã kiểm chứng, lập kế hoạch kịch bản livestream và vận hành phòng livestream riêng tư với sự hỗ trợ của AI.

Trên phương diện kiến trúc hệ thống, HOSTRA AI đi theo hướng **modular monolith** kết hợp các **async AI & media workers** (`apps/api/`, `apps/web/`, `experiments/`, `docs/`). Frontend web tại `apps/web/` phục vụ 3 nhóm bề mặt chính:

1. **Merchant Studio (Desktop-first, Responsive):** Dashboard, Onboarding, AI Presenter Studio, Products & OCOP, Knowledge & Claims, Story Planner & Live Session Setup, Live Control Room, Invite Management, Members & Permissions, Session Reports & History.
2. **Viewer Live Room (Mobile-first, Responsive):** Cổng vào bằng link/QR + nickname, Waiting Room, phòng xem livestream subscribe-only qua LiveKit, thẻ sản phẩm đang giới thiệu và bình luận trực tiếp.
3. **Rights Subject Consent Portal (Độc lập):** Luồng xác nhận/từ chối/thu hồi quyền hình ảnh/giọng nói riêng biệt cho chủ thể quyền, tách khỏi tài khoản quản trị của merchant.

---

## 2. MVP Scope & Non-goals

### Thuộc phạm vi MVP (Đã chốt)
- **Phòng livestream riêng tư (Private Live Room):** Phát trong phòng web riêng của HOSTRA qua LiveKit, khách mời vào bằng invitation link hoặc QR code + nickname (không cần tài khoản merchant).
- **1 Workspace chính cho mỗi Owner** trong MVP (không làm workspace switcher đa tenant trên UI, nhưng kiến trúc vẫn giữ `workspace_id`).
- **1 phiên LIVE đồng thời** trong MVP (có thể có nhiều phiên ở trạng thái `PREPARING`).
- **2–5 SKU thực phẩm đóng gói đủ điều kiện** trong mỗi phiên livestream (catalog của workspace có thể nhiều hơn).
- **Phân quyền rõ ràng:** Chỉ **Workspace Owner** có quyền `START` livestream và duyệt nội dung (Presenter, Facts/Claims, Story Revision); **nhiều Operator** có thể được phân công vào cùng một phiên để vận hành lệnh runtime (`Pause/Resume AI`, `Switch SKU`, `Skip Pending`, `Stop`, `Emergency Stop`).
- **AI Presenter sinh offline và kiểm duyệt:** 3 style presets (`Chuyên nghiệp`, `Thân thiện`, `Năng động`), mặc định dùng *licensed preset voice* (voice clone bị ẩn/khóa cho đến khi qua PoC + consent riêng + license).
- **Light Mode & Dark Mode** ngay từ MVP (`DS-D3=B`), dựa trên **HOSTRA UI Redesign v0.4 (APPROVED)**.
- **Mock-first Frontend:** Toàn bộ luồng nghiệp vụ và trạng thái ngoại lệ được triển khai và kiểm thử với mock API/WS/LiveKit fixtures trước khi tích hợp backend thật.

### Ngoài phạm vi MVP (Non-goals — Không triển khai nút/luồng giả)
- Không tích hợp phát sóng hoặc đồng bộ **TikTok Shop / Shopee Live / OBS / RTMP** (định hướng sau MVP; nếu nhắc tới roadmap chỉ hiển thị thông tin tĩnh, tuyệt đối không có nút "Connect" hoạt động giả).
- Không xây dựng **native mobile app**.
- Không xây dựng **checkout / giỏ hàng / thanh toán / thống kê GMV & doanh thu** nếu chưa có nguồn dữ liệu thực được phê duyệt.
- Không có **replay / VOD** sau khi phiên livestream kết thúc (`VR-D6=A`).
- Không cho phép **multi-owner approval**, tự cấp quyền Operator, hoặc duyệt OCOP thay cơ quan/reviewer có thẩm quyền.

---

## 3. Documentation Structure

```text
docs/product/frontend/
├── README.md        # Tài liệu này — điểm bắt đầu cho Frontend Dev & Coding Agents
├── DECISIONS.md     # Decision Register chính thức theo từng module + Open/Conflict log
├── blueprint/       # Frontend Design & Implementation Blueprint (hiện ở trạng thái DRAFT)
├── design/          # Visual Redesign v0.4 (APPROVED), PDF review 51 trang & ảnh tổng quan
├── modules/         # 12 gói đặc tả module (v0.2 / Dashboard v0.4) & Cross-Module Audit v0.1
├── reports/         # Báo cáo triển khai & screenshots kiểm thử theo từng milestone (milestone-01..05)
└── archive/         # Lưu trữ phiên bản cũ (hiện trống; không dùng làm nguồn hiện hành)
```

> **Lưu ý dọn dẹp kho tài liệu (đề xuất, chưa tự di chuyển):** Hiện `modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.1.docx` vẫn nằm trong `modules/` dù đã bị thay thế bởi `v0.2.docx`. Nên chuyển `v0.1.docx` sang `archive/` sau khi team xác nhận.

---

## 4. Documentation Index

### 4.1. Tài liệu hiện hành trong `docs/product/frontend/`

| Tài liệu | Phiên bản | Trạng thái | Mục đích chính | Đường dẫn tương đối |
| :--- | :---: | :---: | :--- | :--- |
| Frontend Documentation Hub | v1.0 | `ACTIVE` | Điểm bắt đầu đọc tài liệu frontend & hướng dẫn Coding Agents | [README.md](./README.md) |
| Frontend Decision Register | v1.0 | `ACTIVE` | Tổng hợp toàn bộ quyết định sản phẩm/UX theo module & danh mục Open/Conflict | [DECISIONS.md](./DECISIONS.md) |
| Milestone 1–4 Implementation & QA Reports | M1–M4 | `COMPLETED` | Báo cáo triển khai Foundation, Asset Prep, Live Ops, Final QA & Integration Readiness (xem chi tiết Mục 17) | [reports/milestone-04/FINAL_QA_REPORT.md](./reports/milestone-04/FINAL_QA_REPORT.md) |
| Milestone 5 Final Closure & Demo Readiness | M05.1–M05.4 | `PASS (MOCK MVP)` | Đóng 22/22 vấn đề UI/UX, kiểm thử hồi quy toàn diện, Demo Runbook & bàn giao Frontend Mock MVP | [reports/milestone-05/04-final-regression-demo-readiness/README.md](./reports/milestone-05/04-final-regression-demo-readiness/README.md) |
| Frontend Design & Implementation Blueprint | v1.0 | `DRAFT` | Bản tổng hợp kiến trúc frontend, sitemap, 8 journeys (`PT-01`–`PT-08`), kế hoạch F0–F5 | [blueprint/HOSTRA_AI_Frontend_Design_Implementation_Blueprint_v1.0_DRAFT.docx](./blueprint/HOSTRA_AI_Frontend_Design_Implementation_Blueprint_v1.0_DRAFT.docx) |
| Visual Redesign & Figma Handoff | v0.4 | `APPROVED` | Chuẩn thị giác v0.4 (CTA `#F5C430`, Dark Mode, 6 micro-UI fixes, ranh giới nghiệp vụ) | [design/HOSTRA_Visual_Redesign_and_Figma_Handoff_v0.4.docx](./design/HOSTRA_Visual_Redesign_and_Figma_Handoff_v0.4.docx) |
| UI Redesign Clickable Review (51 trang) | v0.4 | `APPROVED` | Bộ review thị giác 25 màn hình × 2 theme Light/Dark (Desktop + Mobile 390×844) | [design/HOSTRA_UI_Redesign_Clickable_Review_v0.4.pdf](./design/HOSTRA_UI_Redesign_Clickable_Review_v0.4.pdf) |
| Redesign Desktop Overview | v0.4 | `APPROVED` | Bảng tổng quan thị giác 11 màn hình Desktop chính | [design/HOSTRA_Redesign_Desktop_Overview_v0.4.png](./design/HOSTRA_Redesign_Desktop_Overview_v0.4.png) |
| Redesign Mobile Overview | v0.4 | `APPROVED` | Bảng tổng quan thị giác 6 màn hình Viewer Mobile 390×844 | [design/HOSTRA_Redesign_Mobile_Overview_v0.4.png](./design/HOSTRA_Redesign_Mobile_Overview_v0.4.png) |
| Cross-Module Audit Preflight | v0.1 | `APPROVED` | Kiểm toán nhất quán liên module (`AUD-01`–`AUD-20`), ma trận sở hữu state, fixtures `FIX-01`–`FIX-14` | [modules/HOSTRA_AI_Cross_Module_Audit_Preflight_v0.1.docx](./modules/HOSTRA_AI_Cross_Module_Audit_Preflight_v0.1.docx) |
| Global Design System & Prototype Spec | v0.2 | `APPROVED` *(UX decisions)* / `PROPOSED` *(semantic tokens)* | `DS-D1`–`DS-D6`, kiến trúc token, 24 components, `CMP-01`–`CMP-12`, motion, responsive, `PT-01`–`PT-08` | [modules/HOSTRA_AI_Global_Design_System_and_Prototype_Spec_v0.2.docx](./modules/HOSTRA_AI_Global_Design_System_and_Prototype_Spec_v0.2.docx) |
| Authentication & Workspace Design Package | v0.2 | `APPROVED` *(UX decisions)* | `AW-D1`–`AW-D5`, Managed OIDC, Onboarding Wizard Save Draft, single workspace, session-scoped Operator | [modules/HOSTRA_AI_Authentication_Workspace_Design_Package_v0.2.docx](./modules/HOSTRA_AI_Authentication_Workspace_Design_Package_v0.2.docx) |
| Merchant Dashboard Design Package | v0.4 | `APPROVED` *(UX decisions)* | `D1`–`D8`, `L1`, `H1`, Action Center 60% / Featured Session 40%, Asset Cards, 3 Recent Sessions | [modules/HOSTRA_AI_Merchant_Dashboard_Design_Package_v0.4.docx](./modules/HOSTRA_AI_Merchant_Dashboard_Design_Package_v0.4.docx) |
| AI Presenter Studio Design Package | v0.2 | `APPROVED` *(UX decisions)* | `PR-D1`–`PR-D4`, `PR-ADD-1/2`, 3 style presets, Rights Consent riêng, background generation, A/B compare | [modules/HOSTRA_AI_Presenter_Studio_Design_Package_v0.2.docx](./modules/HOSTRA_AI_Presenter_Studio_Design_Package_v0.2.docx) |
| Products & OCOP Design Package | v0.2 | `APPROVED` *(UX decisions)* | `PC-D1`–`PC-D5`, catalog table/cards, wizard 4 bước, detail 4 tabs, OCOP độc lập với Owner approval | [modules/HOSTRA_AI_Products_OCOP_Design_Package_v0.2.docx](./modules/HOSTRA_AI_Products_OCOP_Design_Package_v0.2.docx) |
| Knowledge & Claims Design Package | v0.2 | `APPROVED` *(UX decisions)* | `KC-D1`–`KC-D5`, review 2 cột, 5 nhóm fact/claim, duyệt từng mục + bundle, text preview, Live Revision | [modules/HOSTRA_AI_Knowledge_Claims_Design_Package_v0.2.docx](./modules/HOSTRA_AI_Knowledge_Claims_Design_Package_v0.2.docx) |
| Story Planner & Live Session Design Package | v0.2 | `APPROVED` *(UX decisions; 1 mục OPEN)* | `SS-D1`–`SS-D5`, `SS-X1/X2`, drag-drop 2–5 SKU, timeline arcs, AI edit chat diff, Readiness gate riêng | [modules/HOSTRA_AI_Story_Planner_Live_Session_Design_Package_v0.2.docx](./modules/HOSTRA_AI_Story_Planner_Live_Session_Design_Package_v0.2.docx) |
| Live Control Room Design Package | v0.2 | `APPROVED` *(UX decisions)* | `CR-D1`–`CR-D12`, 2 cột 60/40, Comments+Queue, AI sắp nói, Switch SKU drawer, Emergency quick-confirm | [modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.2.docx](./modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.2.docx) |
| Live Control Room Design Package (Bản cũ) | v0.1 | `SUPERSEDED` | Bản discovery cũ, đã bị thay thế hoàn toàn bởi `v0.2` (đề xuất chuyển sang `archive/`) | [modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.1.docx](./modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.1.docx) |
| Viewer Live Room Design Package | v0.2 | `APPROVED` *(UX decisions)* | `VR-D1`–`VR-D7`, mobile video trên/chat dưới, desktop 2 cột, admission cap, SENDING/ACK, no replay | [modules/HOSTRA_AI_Viewer_Live_Room_Design_Package_v0.2.docx](./modules/HOSTRA_AI_Viewer_Live_Room_Design_Package_v0.2.docx) |
| Members & Permissions Design Package | v0.2 | `APPROVED` *(UX decisions)* | `MP-D1`–`MP-D5`, `MP-N1`, nhiều Operator/session, Member Detail drawer, Audit Log, tách Rights Subject | [modules/HOSTRA_AI_Members_Permissions_Design_Package_v0.2.docx](./modules/HOSTRA_AI_Members_Permissions_Design_Package_v0.2.docx) |
| Invite Management Design Package | v0.2 | `APPROVED` *(UX decisions)* | `IM-D1`–`IM-D6`, nhiều named links bất biến, expiry/cap, QR code theo URL, revoke + eject active viewers | [modules/HOSTRA_AI_Invite_Management_Design_Package_v0.2.docx](./modules/HOSTRA_AI_Invite_Management_Design_Package_v0.2.docx) |
| Session Reports & History Design Package | v0.2 | `APPROVED` *(UX decisions)* | `SR-D1`–`SR-D5`, `SR-ADD-01`, KPI + biểu đồ có nguồn đo, Playback ACK, N/A vs Partial, Owner export CSV/PDF | [modules/HOSTRA_AI_Session_Reports_Design_Package_v0.2.docx](./modules/HOSTRA_AI_Session_Reports_Design_Package_v0.2.docx) |

### 4.2. Tài liệu kiến trúc hệ thống cần đối chiếu thêm

| Tài liệu | Mục đích đối chiếu | Đường dẫn tương đối |
| :--- | :--- | :--- |
| Solution Architecture Baseline v1.2 | State machines, module boundaries (P01–P13), hard gates, RBAC, media pipeline | [../../01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx](../../01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx) |
| Technical Risk Assessment v1.1 | Rủi ro R08/R09/R10/R11/R16/R17 và kịch bản lỗi cần chặn | [../../02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx](../../02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx) |
| Technical Research & PoC Plan v1.0 | Công nghệ `SELECTED FOR PoC`, phạm vi P05/P09/P10/P11 và các hạng mục chưa validated | [../../03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx](../../03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx) |

---

## 5. Source of Truth & Documentation Priority

Khi các tài liệu có điểm khác biệt, áp dụng thứ tự ưu tiên sau (theo `AGENTS.md` §4 và Cross-Module Audit):

1. **Nguyên tắc an toàn, bảo mật, phân quyền và thẩm quyền backend** *(không bao giờ được ghi đè bởi tài liệu UX/mockup)*.
2. **Các quyết định sản phẩm/UX đã được phê duyệt mới nhất** (tổng hợp tại [DECISIONS.md](./DECISIONS.md)).
3. **Đặc tả module hiện hành** (`v0.2` của từng module; `v0.4` cho Merchant Dashboard; `Cross-Module Audit v0.1`).
4. **Chuẩn thị giác đã nghiệm thu:** **HOSTRA UI Redesign v0.4 — APPROVED** (ưu tiên hơn các mockup tĩnh cũ trong module package về màu CTA `#F5C430`, Dark Mode và micro-UI).
5. **Kiến trúc hệ thống & hợp đồng kỹ thuật đã xác minh** (`Solution Architecture Baseline v1.2`, `Technical Research & PoC Plan v1.0`).
6. **Frontend Design & Implementation Blueprint v1.0 (`DRAFT`)** — dùng để định hướng triển khai code và kế hoạch delivery, không tự nâng các mục `OPEN`/`PROPOSED` thành `APPROVED`.

**Quy tắc vệ sinh phiên bản (Version Hygiene):**
- Các ghi chú cũ trong `Story Planner v0.2`, `Live Control Room v0.2` và `Viewer Live Room v0.2` nói `KC-D1–KC-D5` còn `OPEN` là **lỗi thời**; `Knowledge & Claims v0.2` và `Cross-Module Audit v0.1` xác nhận `KC-D1–KC-D5 = A` đã **CLOSED/APPROVED**.
- Các file SVG/PNG/PDF v0.4 là **visual references** (chứa dữ liệu minh họa giả lập), không phải native responsive components hoàn chỉnh và không thay thế đặc tả nghiệp vụ/RBAC bằng văn bản.
- Nếu phát hiện mâu thuẫn giữa 2 nguồn có thẩm quyền ngang nhau, **dừng lại và báo cáo mâu thuẫn**, không tự chọn ngầm.

---

## 6. User Roles & Permissions

HOSTRA phân tách nghiêm ngặt **4 miền thẩm quyền độc lập**: (1) *Workspace Membership*, (2) *Session Assignment*, (3) *Asset Rights Consent* và (4) *Official/Internal Verification*. Quyền hiệu lực luôn được backend xác thực theo từng request/command (`actor + workspace membership + resource scope + session grant + capability + authoritative state`); ẩn nút ở frontend chỉ hỗ trợ UX.

| Vai trò | Phạm vi & Trách nhiệm chính | Không được phép |
| :--- | :--- | :--- |
| **Workspace Owner** | Quản lý 1 workspace chính; tạo/duyệt AI Presenter; gửi hồ sơ OCOP; duyệt Knowledge Snapshot & Story Revision; tạo session; **`START` livestream khi `READY`**; mời/phân công/thu hồi Operator; quản lý Invite Link & QR; xem báo cáo đầy đủ & xuất CSV/PDF. | Không tự cấp verdict `OCOP VERIFIED`; không tự ký consent thay Rights Subject khác; không bỏ qua Publication Gate. |
| **Operator** | Thành viên workspace, chỉ truy cập và điều khiển các **session được Owner phân công** (một session có thể có nhiều Operator, một Operator có thể phụ trách nhiều session). Có quyền vận hành runtime (`Pause/Resume AI`, `Switch SKU`, `Skip Pending`, `Prioritize/Skip Comment` pre-commit, `Stop`, `Emergency Stop` kể cả khi Owner offline); tạo draft sản phẩm/upload tài liệu (`PC-D4=B`, `KC-D4=A`); đề xuất Live Revision (`P1`); xem báo cáo rút gọn của phiên được phân công. | Không `START` livestream; không duyệt Presenter/Facts/Story; không Submit xác minh OCOP; không mời/thu hồi thành viên; không tạo/copy/revoke Viewer Invite/QR; không xuất CSV/PDF; không xem session ngoài phân công. *(Quyền sửa pre-live Session Setup/Story của Operator hiện vẫn `OPEN` — mặc định chặn).* |
| **Invited Viewer** | Vào phòng xem riêng tư qua Invite Link / QR + nickname (không cần tài khoản OIDC). Xem video/audio **subscribe-only** qua LiveKit, xem Active Product Card (chỉ public-approved fields) và gửi bình luận khi phiên `LIVE`. | Không truy cập `/studio/*`; không publish mic/camera; không có bất kỳ lệnh điều khiển phiên nào; không xem hồ sơ OCOP/consent nội bộ; không chat trước `LIVE`. |
| **Rights Subject** | Cá nhân sở hữu hình ảnh/giọng nói. Sử dụng **Consent Portal độc lập** (`/rights/consent/...`) để xem mục đích, phạm vi, thời hạn và thực hiện chấp thuận / từ chối / thu hồi quyền của chính mình. | Không có quyền merchant/operator/viewer từ luồng consent. |
| **Vai trò nội bộ (OCOP Reviewer / Safety & Tech Reviewer)** | Xác minh hồ sơ OCOP/thực phẩm có thẩm quyền (P09), xem diagnostics/audit theo chính sách nội bộ. | Không mang quyền quản trị thương mại của Workspace Owner. *(Chi tiết phân quyền nội bộ hiện `OPEN` ở Backend LLD).* |

---

## 7. Frontend Modules & Dependencies

| # | Module | Trách nhiệm chính | Phụ thuộc chính | User Flows chính | Tài liệu nguồn |
| :-: | :--- | :--- | :--- | :--- | :--- |
| 01 | **Global Design System** | Brand & semantic tokens, Light/Dark mode, typography, AppShell, component library (`CMP-01`–`CMP-12`), feedback, motion, a11y | — *(nền tảng chung)* | Tất cả `PT-01`–`PT-08` | [Global Design System v0.2](./modules/HOSTRA_AI_Global_Design_System_and_Prototype_Spec_v0.2.docx), [Visual Redesign v0.4](./design/HOSTRA_Visual_Redesign_and_Figma_Handoff_v0.4.docx) |
| 02 | **Authentication & Workspace** | Hosted OIDC sign-in/callback, khởi tạo 1 workspace chính, Onboarding Wizard Save Draft/Resume, nhận lời mời email Operator, route guards | Design System, OIDC/P11 | `AW-F01`–`AW-F06`, `PT-01` | [Auth & Workspace v0.2](./modules/HOSTRA_AI_Authentication_Workspace_Design_Package_v0.2.docx) |
| 03 | **Merchant Dashboard** | Action Center ưu tiên (tối đa 5 item + View All), Featured Session (không video preview), 4 Asset Status Cards độc lập, 3 Recent Sessions | Auth, Sessions, Presenter, Products, Knowledge | `DF-01`–`DF-07`, `PT-01` | [Merchant Dashboard v0.4](./modules/HOSTRA_AI_Merchant_Dashboard_Design_Package_v0.4.docx) |
| 04 | **Members & Permissions** | Danh bạ thành viên (table/cards), mời Operator qua email có hạn, Member Detail drawer, phân công N:N nhiều Operator/session, thu hồi & Audit Log | Auth, Sessions, P09/P11 | `MP-F01`–`MP-F09`, `PT-07` | [Members & Permissions v0.2](./modules/HOSTRA_AI_Members_Permissions_Design_Package_v0.2.docx) |
| 05 | **AI Presenter Studio** | Thư viện Presenter, Wizard 4 bước (Save Draft), 3 style presets, Licensed Voice mặc định, Rights Consent portal độc lập, background generation, QC & A/B compare, Owner approval | Auth, Rights Service/P11, P01/P02 | `PF-01`–`PF-05`, `PT-02` | [Presenter Studio v0.2](./modules/HOSTRA_AI_Presenter_Studio_Design_Package_v0.2.docx) |
| 06 | **Products & OCOP** | Catalog desktop table / mobile cards, Wizard 4 bước Save Draft, Product Detail 4 tabs (`Overview`/`OCOP`/`Facts`/`Versions`), upload hồ sơ, Owner Submit xác minh OCOP | Auth, P09 (OCOP), P05 (Knowledge) | Catalog, Wizard, OCOP review, `PT-03` | [Products & OCOP v0.2](./modules/HOSTRA_AI_Products_OCOP_Design_Package_v0.2.docx) |
| 07 | **Knowledge & Claims** | Thư viện tri thức theo SKU, Extraction Review (Docling draft), Review 2 cột (nguồn trái / 5 nhóm fact-claim phải), duyệt từng mục + Owner duyệt bundle, Text Speech Preview, Revision Inbox | Products & OCOP, P05, P09 | `KNC-F01`–`KNC-F06`, `PT-03` | [Knowledge & Claims v0.2](./modules/HOSTRA_AI_Knowledge_Claims_Design_Package_v0.2.docx) |
| 08 | **Story Planner & Live Session Setup** | Danh sách phiên, Wizard 4 bước Save Draft, kéo-thả 2–5 SKU (+ nút keyboard/mobile), Timeline Story Arcs, AI Editing Assistant (diff/patch), Owner duyệt toàn revision, Readiness Checklist riêng & Owner-only `START` | Presenter, Products/OCOP, Knowledge, P06/P08/P09 | `SES-F01`–`SES-F07`, `PT-04`, `PT-05` | [Story Planner & Live Session v0.2](./modules/HOSTRA_AI_Story_Planner_Live_Session_Design_Package_v0.2.docx) |
| 09 | **Live Control Room** | Màn hình vận hành 2 cột 60/40 (LiveKit preview + Active/Next/Referenced SKU trái; Comments + Queue + AI Activity phải), Status Bar gọn + Diagnostics drawer, AI sắp nói (`Dự kiến · Chưa phát`), Switch SKU drawer, Command conflict log, Stop & Emergency quick-confirm | Story/Session, Members, Knowledge, P04/P07/P08/P09 | `CR-F01`–`CR-F08`, `PT-05`, `PT-07` | [Live Control Room v0.2](./modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.2.docx) |
| 10 | **Invite Management** | Tab Invitations trong Session Detail, tạo nhiều named links bất biến (expiry presets/custom + usage cap), sinh & tải QR theo đúng URL, shortcut Copy Owner-only ở Control Room, thu hồi link + ngắt viewer đang xem | Sessions, Members/RBAC, Viewer Room | `INV-F01`–`INV-F09`, `PT-06` | [Invite Management v0.2](./modules/HOSTRA_AI_Invite_Management_Design_Package_v0.2.docx) |
| 11 | **Viewer Live Room** | Invite Entry (validate + nickname), Waiting Room (khóa chat trước LIVE), Live Room mobile-first (video trên, product card, comments dưới; desktop 2 cột), SENDING/RECEIVED/REJECTED, Recovery độc lập video/chat, Session Ended (no replay) | Invite Management, Live Control/P09, LiveKit | `VF-01`–`VF-06`, `PT-06` | [Viewer Live Room v0.2](./modules/HOSTRA_AI_Viewer_Live_Room_Design_Package_v0.2.docx) |
| 12 | **Session Reports & History** | Lịch sử phiên theo quyền, KPI cards, biểu đồ admissions/concurrency & state timeline có provenance, 3 tabs (`AI & Comments`, `Media & Health`, `Activity & Audit`), Playback ACK, N/A vs Partial, Owner export CSV/PDF | Sessions, Control Room, P04/P09/P12 | `RPT-F01`–`RPT-F10`, `PT-08` | [Session Reports v0.2](./modules/HOSTRA_AI_Session_Reports_Design_Package_v0.2.docx) |

---

## 8. Information Architecture & Main User Flows

### 8.1. Sitemap & Proposed Frontend Routes (`PROPOSED` — chưa phải backend URL contract)

- **Auth & Onboarding:** `/auth/sign-in` *(hoặc `/login`)*, `/auth/callback`, `/studio/onboarding`, `/studio/invitations/accept`, `/studio/no-access`
- **Merchant Studio Core:** `/studio/dashboard`, `/studio/presenters`, `/studio/presenters/new`, `/studio/presenters/:id`, `/studio/products`, `/studio/products/new`, `/studio/products/:skuId` *(tabs: `overview`, `ocop`, `facts`, `versions`)*, `/studio/knowledge` *(sub-views: extraction, review, versions, preview, changes)*
- **Sessions & Live Ops:** `/studio/sessions`, `/studio/sessions/new`, `/studio/sessions/:id`, `/studio/sessions/:id/story`, `/studio/sessions/:id/readiness`, `/studio/sessions/:id/control`, `/studio/sessions/:id/invites`, `/studio/sessions/:id/report`
- **Workspace Admin:** `/studio/members` *(drawer Detail + Assignments + Invitations + Audit)*
- **Rights Portal (Độc lập):** `/rights/consent/:requestId` *(hoặc `:token`)*
- **Viewer Public/Private Entry:** `/live/:id` *(với invite parameter/token; không dẫn vào `/studio/*`)*

### 8.2. 8 Critical End-to-End User Journeys (`PT-01` → `PT-08`)

1. **`PT-01` — First Owner Onboarding:** Sign-in OIDC → Workspace Draft (Save Draft/Resume) → Dashboard Action Center → Next Best Action.
2. **`PT-02` — Presenter & Rights Exception:** Upload portrait → Rights Pending → Rights Subject Consent Portal → Revoked/Blocked Generation → Generate 3 styles → QC & A/B compare → Owner Approve.
3. **`PT-03` — OCOP & Knowledge Governance:** Product draft → Upload OCOP/food evidence → Owner Submit → Pending/Verified (độc lập) → Docling Extraction → Review 5 nhóm Facts/Claims → Owner Approve bundle.
4. **`PT-04` — Story Planner & AI Edit:** Chọn/kéo-thả 2–5 SKU → Timeline arcs → Chat AI Editing Assistant → Diff + Fact provenance → Apply to Draft → Review từng arc → Owner Approve revision.
5. **`PT-05` — Live Control & Safety:** Readiness Checklist → Owner `START` → `STARTING` → `LIVE` → `Pause AI` / `Switch SKU` (Pending → Applied) / Concurrent Conflict → Emergency Stop (quick confirm).
6. **`PT-06` — QR Viewer Journey:** Owner tạo Invite + QR → Viewer quét/nhập nickname → Waiting Room (khóa chat) → `LIVE` (video trên, card, comments SENDING → RECEIVED) → Buffering / Chat reconnect độc lập → Revoked hoặc Session Ended.
7. **`PT-07` — Multi-Operator Control:** Owner mời email Operator → Assign 2 Operator vào cùng 1 phiên → Gửi lệnh song song & conflict resolution → Revoke Operator B (Operator A vẫn hoạt động) → Audit Log.
8. **`PT-08` — Truthful Session Reports:** Phiên `STOPPED` → `PENDING` / `PARTIAL` (N/A có lý do) / `READY` → KPI theo Playback ACK + biểu đồ có nguồn đo → Owner Export CSV/PDF (Operator xem rút gọn, không export).

---

## 9. Approved Design System

**Visual Baseline:** **HOSTRA UI Redesign v0.4 — APPROVED**, kết hợp đặc tả hệ thống thành phần từ **Global Design System v0.2**.

- **Brand & Surface Palette (v0.4 APPROVED):**
  - Brand Navy: `#0F172A` (Sidebar, typography chính trên Light, chữ trên nút vàng).
  - Primary CTA Amber: `#F5C430` (chữ Navy `#0F172A` — **tuyệt đối không dùng chữ trắng trên vàng**).
  - Soft Yellow Accent: `#FBE580` (tint, highlight, mục đang chọn).
  - White: `#FFFFFF` · Cool Gray: `#E2E8F0` · Destructive Red: `#DC2626` (chữ trắng `#FFFFFF`, nút xác nhận Emergency Stop).
  - **Light Mode (v0.4):** Nền `#F7F9FC`, card `#FFFFFF`, border `#E6ECF3`, secondary text `#475569`.
  - **Dark Mode (v0.4):** Nền `#0B1322`, card `#121F32`, nested surface `#19283E`, border `#273952`, text sáng độ tương phản cao.
  - **Semantic Status Colors:** Xanh/vàng/đỏ/xanh dương tách biệt khỏi màu brand, **luôn đi kèm text + icon** (không chỉ dùng màu). *(Các mã hex semantic chi tiết trong GDS v0.2 đang ở mức `PROPOSED`, cần kiểm contrast thực tế trước release).*
- **Typography:** Primary `Be Vietnam Pro`, fallback `Inter, sans-serif`; heading line-height `1.25–1.3`; dùng **tabular numerals** cho KPI, giá tiền, thời lượng, mốc thời gian.
- **Layout & Density:** Phong cách Premium Minimal SaaS, spacing gốc 4px/8px (`8/16/24/32px`), border radius `8px` input / `12px` card / `16px` modal, ưu tiên viền mảnh thay vì đổ bóng nặng; sidebar desktop `232px` (thu gọn `72px`), mobile dùng drawer; Viewer Room thiết kế mobile-first (`390×844`).
- **Feedback & Motion:** Inline field validation + Success Toast (chỉ sau xác nhận authoritative) + Persistent Critical Banner (không tự đóng). Motion tiết chế `120–240ms`, tôn trọng `prefers-reduced-motion`, không trì hoãn trạng thái LIVE/Emergency.
- **Accessibility:** Mục tiêu WCAG 2.2 AA (contrast ≥ 4.5:1 văn bản thường), focus ring rõ ở cả Light/Dark, focus trap cho modal/drawer, touch target mục tiêu `≥ 44×44px` trên mobile, hỗ trợ zoom ≥ 200%, mọi tương tác kéo-thả SKU có nút keyboard/touch thay thế.
- **Ngôn ngữ UI:** Tiếng Việt chuẩn cho toàn bộ nhãn merchant-facing và viewer-facing (trừ thuật ngữ kỹ thuật chuẩn như `SKU`, `OCOP`, `LIVE`, `QR`, `CSV`, `PDF`).

---

## 10. Frontend Architecture & Tech Stack

| Hạng mục | Trạng thái | Lựa chọn / Đề xuất | Ghi chú & Ranh giới |
| :--- | :---: | :--- | :--- |
| Core Framework | `SELECTED FOR PoC` | React + TypeScript + Vite SPA | Triển khai tại `apps/web/` |
| Routing | `PROPOSED` | React Router | Guard theo capabilities từ server snapshot |
| Server State & Cache | `SELECTED FOR PoC` / `PROPOSED` | TanStack Query | REST authoritative snapshots + cache invalidation sau WS event |
| Mock API Layer | `PROPOSED` | Mock Service Worker (MSW) + deterministic fixtures | Tách adapter để thay bằng REST/WS thật mà không sửa UI logic |
| Media (Viewer & Preview) | `SELECTED FOR PoC` | LiveKit React SDK (`subscribe-only`) | Video/audio đi qua LiveKit, **không** stream frame qua WebSocket |
| Testing | `SELECTED FOR PoC` / `PROPOSED` | Vitest (unit/component) + Playwright (E2E `PT-01`–`PT-08`) | Phủ happy path + failure/permission/a11y cases |
| Backend Transport | `UNVALIDATED` *(API chưa chốt)* | FastAPI REST + Versioned WebSocket | Chưa có OpenAPI/WS schema chính thức; không hardcode endpoint như contract đã duyệt |
| Managed OIDC Provider | `UNVALIDATED` *(TBD)* | Hosted OIDC (provider chưa chọn) | Studio không tự xử lý password hay lưu raw refresh token |

**Kiến trúc thư mục đề xuất (`Blueprint v1.0 DRAFT`, `PROPOSED`):**
`app/` (routing, providers, theme, auth bootstrap) · `features/<module>/` (pages, view models, hooks, tests) · `shared/ui/` · `shared/api/` · `shared/realtime/` (WS reconciler, reconnect, resync) · `shared/auth/` · `mocks/` · `tests/`.

---

## 11. Domain States & Safety Rules

Frontend **tuyệt đối không gộp** các trục trạng thái độc lập sau và **không dùng optimistic state** cho `LIVE`, `APPLIED`, `VERIFIED`, `CONSENT` hay `Playback COMPLETED`:

| Miền trạng thái | Tập trạng thái chuẩn / đề xuất | Quy tắc bất biến trên UI |
| :--- | :--- | :--- |
| **Session Lifecycle** *(Canonical)* | `CREATED` → `PREPARING` → `READY` → `STARTING` → `LIVE` → `STOPPING` → `STOPPED` (`FAILED` / `CANCELLED`) | **`STARTING` ≠ `LIVE`**. Chỉ báo `LIVE` sau xác nhận authoritative của backend/publisher. |
| **AI Execution** *(Canonical)* | `ACTIVE`, `PAUSE_REQUESTED`, `PAUSED`, `RESUMING`, `BLOCKED` | **`PAUSE_AI` ≠ `STOP` livestream**. Stream vẫn có thể `LIVE` (safe scene) khi AI đang `PAUSED`. |
| **Media Health** *(Canonical)* | `HEALTHY`, `DEGRADED`, `FAILED` | `DEGRADED` phải hiện fallback thực tế đang dùng & mở Diagnostics; không tự đổi Session thành `STOPPED`. |
| **Dialogue Substate** *(Canonical)* | `PLAYING_SCRIPT`, `INTERRUPT_PENDING`, `ANSWERING_COMMENT`, `RESUMING`, `IDLE` | Minh bạch hoạt động AI; không thay thế Playback ACK. |
| **Command Lifecycle** *(Canonical)* | `REQUESTED` → `ACCEPTED` → `APPLIED` \| `REJECTED` | **`ACCEPTED` / HTTP 200 ≠ `APPLIED`**. Active SKU chỉ đổi sau khi nhận `APPLIED` tại safe boundary. Luôn gửi `command_id` + `expected_revision`; xử lý 409 conflict bằng refetch. |
| **Speech Turn** *(Canonical)* | `PROPOSED`, `VALIDATED`, `PREPARING`, `READY`, `COMMITTED`, `PLAYING`, `COMPLETED` | **TTS completion ≠ Playback completion**. Chỉ `PlaybackCompleted ACK` (P04) mới được tính là đã phát và tiến Story Checkpoint. `SKIP_PENDING` chỉ hợp lệ trước `COMMITTED`. |
| **Product & OCOP** *(Độc lập)* | `PENDING_REVIEW`, `VERIFIED`, `REJECTED`, `EXPIRED`, `REVOKED` | **OCOP Verification ≠ Merchant Approval**. Upload ảnh/logo không tự thành `VERIFIED`; thiếu chứng cứ là `PENDING_REVIEW`, không quy chụp làm giả. |
| **Knowledge Approval** *(Độc lập)* | `DRAFT`, `PENDING_OWNER`, `APPROVED`, `INVALIDATED`, `SUPERSEDED` | **Knowledge Approved ≠ Publication Gate pass** và không cấp `OCOP VERIFIED`. Đổi giá/facts/story khi live cần revision + Owner approval + safe boundary. |
| **Rights Consent** *(Độc lập)* | `MISSING`, `PENDING`, `VERIFYING`, `VERIFIED`, `DECLINED`, `EXPIRED`, `REVOKED` | Độc lập hoàn toàn với tài khoản Owner. Thu hồi/hết hạn lập tức vô hiệu hóa asset & cache liên quan. |
| **Invitation & Viewer** *(Proposed)* | `CREATING`, `ACTIVE`, `EXPIRED`, `EXHAUSTED`, `REVOKED`, `INVALID` | Link bất biến; tính lượt theo admission thành công (refresh cùng guest không tăng). Revoke chặn join mới và ngắt viewer đang xem. |
| **Frontend Sync & UI** *(Client)* | `LOADING`, `EMPTY`, `ERROR`, `STALE`, `RECONNECTING`, `FORBIDDEN`, `PARTIAL/N-A` | Không nhầm `ERROR`/`FORBIDDEN` thành `EMPTY`; không tính `N/A` là `0`; sau reconnect luôn refetch authoritative snapshot, không tự replay lệnh cũ. |

---

## 12. Mock-first Development Strategy

- Toàn bộ 12 module được phát triển bằng **typed adapters + MSW mock handlers** trước khi backend hoàn thiện API thật.
- **Không hardcode mock data vào reusable UI components**; dữ liệu giả lập nằm ở tầng `mocks/` với các scenario fixtures có thể chuyển đổi deterministic (tham chiếu `FIX-01`–`FIX-14` trong Cross-Module Audit và fixtures của từng module).
- **Kịch bản mock bắt buộc phải phủ:** Workspace mới trống; Onboarding Draft; Presenter chờ quyền / quyền bị thu hồi giữa job / lỗi tạo clip / so sánh A-B; OCOP `PENDING_REVIEW` / `REJECTED` / `EXPIRED` khi Facts đã `APPROVED`; Readiness bị chặn; `STARTING` vs `LIVE`; `LIVE` + `AI PAUSED`; `Media DEGRADED`; 2 Operator gửi lệnh xung đột (`409`); Switch SKU đang `Pending`; Viewer buffering trong khi chat còn sống & mất chat trong khi video còn chạy; Invite hết hạn / hết lượt / bị thu hồi khi đang xem; Report `PENDING` / `PARTIAL` (thiếu concurrent telemetry) / `READY` & lỗi Export.
- **Ranh giới tích hợp backend:** Các view models trong tài liệu là yêu cầu phía frontend (`PROPOSED`), không phải OpenAPI/DB schema đã khóa. Tuyệt đối không tuyên bố frontend đã kết nối backend thật hoặc đã *production-ready* khi mới chạy bằng mock.

---

## 13. Recommended Implementation Order

Theo lộ trình đề xuất trong `Blueprint v1.0 DRAFT` (§14):

1. **Phase F0 — Repo & Design Tokens:** Khởi tạo Vite + React + TypeScript tại `apps/web/`, setup Router, TanStack Query, theme Light/Dark theo v0.4, AppShell, mock auth context, MSW, lint & test harness.
2. **Phase F1 — Core Workspace:** Authentication/Onboarding Wizard (Save Draft), Merchant Dashboard, Members & Permissions (multi-operator assignments), role/capability route guards, reusable UI library (`shared/ui/`).
3. **Phase F2 — Asset Preparation:** AI Presenter Studio (+ Rights Consent Portal mock), Products & OCOP (catalog + 4-step wizard + 4-tab detail), Knowledge & Claims (2-pane review + 5 groups + text preview), Story Planner & Session Setup (SKU drag-drop + timeline + AI edit diff).
4. **Phase F3 — Session Launch & Live Operations:** Session Readiness Gate (Owner-only Start), Live Control Room (2-col layout, command lifecycle, pending SKU, conflict resolution, diagnostics, Emergency quick-confirm, mock WS reconnect).
5. **Phase F4 — Viewer & Analytics:** Invite Management (named links + QR + revoke), Viewer Live Room (mobile-first + desktop 2-col + independent video/chat recovery), Session Reports & History (KPIs, charts, Playback ACK, N/A/Partial, Owner CSV/PDF export).
6. **Phase F5 — QA & Integration Readiness:** E2E Playwright cho đủ `PT-01`–`PT-08` (happy + failure paths), kiểm thử Light/Dark & responsive, accessibility audit, bàn giao danh mục API adapter & sign-off.

---

## 14. Testing & Definition of Done

### Yêu cầu kiểm thử
- **Unit & Component Tests (Vitest):** State projections, role/capability guards, form validations, command lifecycle (`REQUESTED`→`ACCEPTED`→`APPLIED`/`REJECTED`), version conflict handling, metric `N/A`/`Partial` rendering.
- **End-to-End Tests (Playwright trên mock):** Phủ đủ 8 hành trình `PT-01`–`PT-08`, mỗi flow có ít nhất **1 happy path + 1 failure/permission path**.
- **Visual, Responsive & A11y Checks:** Kiểm tra cả Light & Dark Mode trên Desktop (`≥1200px`), Tablet (`768–1199px`), Mobile (`390×844` / `<768px`); kiểm tra keyboard navigation, focus trap, contrast WCAG 2.2 AA, zoom 200% và `prefers-reduced-motion`.

### Definition of Done (theo `AGENTS.md` §10)
Một tính năng frontend chỉ hoàn thành khi:
1. Khớp đúng yêu cầu sản phẩm đã duyệt trong [DECISIONS.md](./DECISIONS.md) và module spec tương ứng.
2. Tuân thủ chuẩn thị giác **HOSTRA UI Redesign v0.4** (Light + Dark Mode, tiếng Việt).
3. Chạy ổn định với mock API/WS fixtures; tách biệt business logic khỏi presentation components.
4. Xử lý đầy đủ `loading`, `empty`, `error`, `permission/forbidden`, `stale/reconnect` và conflict states.
5. Pass toàn bộ unit/component tests và xác minh các tương tác quan trọng (không làm hỏng module khác).
6. Ghi rõ các backend dependencies còn mở; không tuyên bố production-ready khi chưa tích hợp backend thật.

---

## 15. Open Questions & Unvalidated Dependencies

Chi tiết đầy đủ nằm tại mục cuối của [DECISIONS.md](./DECISIONS.md#open-decisions--conflicts--unvalidated-assumptions). Các điểm chặn chính cần lưu ý:

- **P0 — Chặn tích hợp Backend (không chặn dựng UI mock-first):**
  1. Lựa chọn nhà cung cấp Managed OIDC, luồng callback & bảo mật session/cookie.
  2. Hợp đồng REST/WS canonical (endpoints, state enums, `expected_revision`, `session_epoch`, event ordering/replay).
  3. Cơ chế LiveKit guest token revocation & ngắt kết nối viewer đang xem tức thì khi revoke invite (`IM-D4`).
  4. Quy trình xác minh danh tính Rights Subject (P11) và nguồn xác minh OCOP có thẩm quyền (P09).
  5. Safe boundary áp dụng Live Revision & vô hiệu hóa speech/TTS lỗi thời (P04/P05/P08).
- **P1 — Sản phẩm / UX / Thiết kế còn mở:**
  1. Quyền **Operator tạo/sửa pre-live Session Setup & Story Plan** đang `OPEN` (mặc định Owner-only).
  2. Bộ **Figma native editable components / Auto Layout / clickable prototype đủ 8 flows (`PT-01`–`PT-08`)** mới hoàn thành một phần; file `HOSTRA_Figma_Visual_Redesign_Kit_v0.4.zip` được nhắc trong Handoff v0.4 hiện chưa có trong repo.
  3. Chốt bảng mã hex semantic tokens (hiện `PROPOSED` trong GDS v0.2) và kiểm tra contrast cuối cùng trên Light/Dark.
  4. Định nghĩa chi tiết telemetry cho `concurrent_viewers`, `live_duration_seconds`, worker xuất CSV/PDF và chính sách giữ quyền đọc report sau khi thu hồi assignment (`RPT-O1`–`RPT-O6`).
  5. `Frontend Blueprint v1.0` hiện vẫn ở trạng thái `DRAFT`, chưa có sign-off cuối.

---

## 16. Instructions for Coding Agents

Trước khi viết bất kỳ dòng code frontend nào trong `apps/web/`, Coding Agent **bắt buộc** thực hiện đúng trình tự sau:

1. **Đọc tài liệu nền tảng:**
   - [AGENTS.md](../../../AGENTS.md) (quy tắc repository, kiến trúc, git safety).
   - File này ([README.md](./README.md)) và [DECISIONS.md](./DECISIONS.md).
2. **Đọc tài liệu thiết kế hệ thống & kiểm toán:**
   - [HOSTRA_Visual_Redesign_and_Figma_Handoff_v0.4.docx](./design/HOSTRA_Visual_Redesign_and_Figma_Handoff_v0.4.docx) + ảnh/PDF v0.4 tương ứng.
   - [HOSTRA_AI_Global_Design_System_and_Prototype_Spec_v0.2.docx](./modules/HOSTRA_AI_Global_Design_System_and_Prototype_Spec_v0.2.docx).
   - [HOSTRA_AI_Cross_Module_Audit_Preflight_v0.1.docx](./modules/HOSTRA_AI_Cross_Module_Audit_Preflight_v0.1.docx).
3. **Đọc đúng Design Package của module sắp triển khai** (từ bảng mục 4.1) và mục tương ứng trong [Blueprint v1.0 DRAFT](./blueprint/HOSTRA_AI_Frontend_Design_Implementation_Blueprint_v1.0_DRAFT.docx).
4. **Đối chiếu kiến trúc hệ thống** trong `docs/01-solution-architecture/` khi đụng tới state transitions, RBAC, Publication Gate hoặc media/LiveKit.
5. **Tuân thủ kỷ luật triển khai:**
   - Không tự ý thiết kế lại UI v0.4; không thêm tính năng ngoài MVP (TikTok/Shopee/OBS/checkout/replay).
   - Không tự nâng hạng mục `OPEN`/`DRAFT`/`PROPOSED` thành `APPROVED`; nếu gặp điểm mơ hồ hoặc mâu thuẫn, báo cáo rõ cho người dùng.
   - Luôn tách biệt mock adapter khỏi UI component, hỗ trợ cả Light & Dark Mode, kiểm tra đầy đủ role guards và trạng thái lỗi/reconnect trước khi báo hoàn thành.

---

## 17. Frontend Milestone Reports

- **Milestone 01 (Foundation & Merchant Dashboard):** [IMPLEMENTATION_REPORT.md](./reports/milestone-01/IMPLEMENTATION_REPORT.md)
- **Milestone 02 (Merchant Studio & Asset Preparation):** [IMPLEMENTATION_REPORT.md](./reports/milestone-02/IMPLEMENTATION_REPORT.md)
- **Milestone 03 (Livestream Operations, Viewer Experience, Permissions, Invitations, Reports & Addendum):**
  - [IMPLEMENTATION_REPORT.md](./reports/milestone-03/IMPLEMENTATION_REPORT.md)
  - [QA_REPORT.md](./reports/milestone-03/QA_REPORT.md)
  - Screenshots: [reports/milestone-03/screenshots/](./reports/milestone-03/screenshots/)
- **Milestone 04 (Final Frontend QA, Cross-Module UAT & Backend Integration Readiness):**
  - [IMPLEMENTATION_REPORT.md](./reports/milestone-04/IMPLEMENTATION_REPORT.md)
  - [FINAL_QA_REPORT.md](./reports/milestone-04/FINAL_QA_REPORT.md)
  - [UX_ACCESSIBILITY_AUDIT.md](./reports/milestone-04/UX_ACCESSIBILITY_AUDIT.md)
  - [CROSS_MODULE_UAT_MATRIX.md](./reports/milestone-04/CROSS_MODULE_UAT_MATRIX.md)
  - [INTEGRATION_READINESS_MATRIX.md](./reports/milestone-04/INTEGRATION_READINESS_MATRIX.md)
  - [API_CONTRACT_GAPS.md](./reports/milestone-04/API_CONTRACT_GAPS.md)
  - [DEMO_GUIDE.md](./reports/milestone-04/DEMO_GUIDE.md)
  - Screenshots: [reports/milestone-04/screenshots/](./reports/milestone-04/screenshots/)
- **Milestone 05.1 (Comprehensive Frontend UI/UX Audit — Audit Only):**
  - [README.md](./reports/milestone-05/01-ui-ux-audit/README.md) · [UI_UX_AUDIT_REPORT.md](./reports/milestone-05/01-ui-ux-audit/UI_UX_AUDIT_REPORT.md)
  - [SCREEN_BY_SCREEN_REVIEW.md](./reports/milestone-05/01-ui-ux-audit/SCREEN_BY_SCREEN_REVIEW.md) · [ISSUE_REGISTER.md](./reports/milestone-05/01-ui-ux-audit/ISSUE_REGISTER.md)
  - [DESIGN_SYSTEM_AUDIT.md](./reports/milestone-05/01-ui-ux-audit/DESIGN_SYSTEM_AUDIT.md) · [RESPONSIVE_ACCESSIBILITY_AUDIT.md](./reports/milestone-05/01-ui-ux-audit/RESPONSIVE_ACCESSIBILITY_AUDIT.md)
  - [UX_MICROCOPY_GLOSSARY.md](./reports/milestone-05/01-ui-ux-audit/UX_MICROCOPY_GLOSSARY.md) · [IMPROVEMENT_BACKLOG.md](./reports/milestone-05/01-ui-ux-audit/IMPROVEMENT_BACKLOG.md)
  - [PROPOSED_M05_2_PLAN.md](./reports/milestone-05/01-ui-ux-audit/PROPOSED_M05_2_PLAN.md)
  - Screenshots: [reports/milestone-05/01-ui-ux-audit/screenshots/](./reports/milestone-05/01-ui-ux-audit/screenshots/)
- **Milestone 05.2 (UI/UX Refinement Implementation):**
  - [README.md](./reports/milestone-05/02-ui-ux-refinement/README.md) · [REFINEMENT_REPORT.md](./reports/milestone-05/02-ui-ux-refinement/REFINEMENT_REPORT.md) · [BEFORE_AFTER_COMPARISON.md](./reports/milestone-05/02-ui-ux-refinement/BEFORE_AFTER_COMPARISON.md)
  - Screenshots: [reports/milestone-05/02-ui-ux-refinement/screenshots/](./reports/milestone-05/02-ui-ux-refinement/screenshots/)
- **Milestone 05.3 (Usability Testing & End-to-End User Journey Validation):**
  - [README.md](./reports/milestone-05/03-usability-validation/README.md) · [M05_3_USABILITY_REPORT.md](./reports/milestone-05/03-usability-validation/M05_3_USABILITY_REPORT.md)
  - [USER_JOURNEY_TEST_MATRIX.md](./reports/milestone-05/03-usability-validation/USER_JOURNEY_TEST_MATRIX.md) · [ACCESSIBILITY_RESPONSIVE_REPORT.md](./reports/milestone-05/03-usability-validation/ACCESSIBILITY_RESPONSIVE_REPORT.md)
  - [M05_1_ISSUE_CLOSURE.md](./reports/milestone-05/03-usability-validation/M05_1_ISSUE_CLOSURE.md) · [HUMAN_USABILITY_TEST_PLAN.md](./reports/milestone-05/03-usability-validation/HUMAN_USABILITY_TEST_PLAN.md)
  - [M05_3_FIX_LOG.md](./reports/milestone-05/03-usability-validation/M05_3_FIX_LOG.md) · [M05_3_EXIT_GATE.md](./reports/milestone-05/03-usability-validation/M05_3_EXIT_GATE.md)
  - Screenshots: [reports/milestone-05/03-usability-validation/screenshots/](./reports/milestone-05/03-usability-validation/screenshots/)
- **Milestone 05.4 (Final Regression, UX Issue Closure & Frontend Demo Readiness — `PASS — FRONTEND MOCK MVP BASELINE READY`):**
  - [README.md](./reports/milestone-05/04-final-regression-demo-readiness/README.md) · [M05_4_IMPLEMENTATION_REPORT.md](./reports/milestone-05/04-final-regression-demo-readiness/M05_4_IMPLEMENTATION_REPORT.md)
  - [FINAL_ISSUE_CLOSURE.md](./reports/milestone-05/04-final-regression-demo-readiness/FINAL_ISSUE_CLOSURE.md) · [FINAL_REGRESSION_REPORT.md](./reports/milestone-05/04-final-regression-demo-readiness/FINAL_REGRESSION_REPORT.md)
  - [FRONTEND_DEMO_RUNBOOK.md](./reports/milestone-05/04-final-regression-demo-readiness/FRONTEND_DEMO_RUNBOOK.md) · [FRONTEND_MOCK_MVP_HANDOFF.md](./reports/milestone-05/04-final-regression-demo-readiness/FRONTEND_MOCK_MVP_HANDOFF.md)
  - [HUMAN_USABILITY_TEST_PLAN.md](./reports/milestone-05/04-final-regression-demo-readiness/HUMAN_USABILITY_TEST_PLAN.md) · [M05_4_EXIT_GATE.md](./reports/milestone-05/04-final-regression-demo-readiness/M05_4_EXIT_GATE.md)
  - Evidence & Screenshots: [tests/evidence/m05_4_regression_evidence.json](./reports/milestone-05/04-final-regression-demo-readiness/tests/evidence/m05_4_regression_evidence.json) · [screenshots/](./reports/milestone-05/04-final-regression-demo-readiness/screenshots/)
