# HOSTRA AI — Backend Integration Readiness Matrix (Gate 5)

> **Lưu ý quan trọng:** Đây là **hồ sơ chuẩn bị tích hợp phía Frontend**, phân biệt rõ giữa `MOCK` (đang chạy MSW), `PROPOSED` (đề xuất từ frontend), `OPEN` (chưa chốt), và `VERIFIED` (đã có trong Solution Architecture Baseline v1.2). **Không xác nhận backend đã sẵn sàng triển khai.**

---

## 1. Bảng ánh xạ Mock Endpoints → Backend Modules

| Frontend Feature | Mock Endpoint / Event (`MOCK`) | Backend Module (Baseline v1.2) | Request DTO | Response DTO | Error Cases | Trạng thái xác nhận |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **Auth & Workspace** | `GET /api/mock/v1/auth/me`, `GET/PUT /api/mock/v1/workspace/onboarding` | Identity / Managed OIDC + Workspace | `OnboardingDraftPayload` | `AuthSessionSnapshot`, `OnboardingDraft` | `401`, `403`, `422` | `UNVALIDATED` (OIDC provider TBD) |
| **Merchant Dashboard** | `GET /api/mock/v1/dashboard` | BFF / P09 Session Read Model | Query `role` (mock only) | `DashboardSnapshot` | `401`, `403`, `500` | `PROPOSED` |
| **AI Presenter Studio** | `GET/POST /api/mock/v1/presenters`, `POST /:id/approve`, `GET/POST /api/mock/v1/rights/consent/:reqId` | P01/P02 Presenter Gen + P11 Rights Service | `PresenterCreatePayload`, `RightsDecisionPayload` | `PresenterDetail`, `RightsConsentStatus` | `403`, `409`, `422` | `PARTIAL` (Rights flow `OPEN`) |
| **Products & OCOP** | `GET/POST /api/mock/v1/products`, `POST /:skuId/ocop-submit`, `POST /:skuId/ocop-decision` | P09 Catalog + OCOP Verification | `ProductDraftPayload`, `OcopSubmitPayload` | `ProductDetail` | `403`, `409`, `422` | `PARTIAL` (OCOP authority `OPEN`) |
| **Knowledge & Claims** | `GET /api/mock/v1/knowledge`, `PATCH /:skuId/facts/:factId`, `POST /:skuId/approve` | P05 Knowledge & Publication Gate | `FactDecisionPayload`, `expectedRevision` | `KnowledgePackageDetail` | `403`, `409`, `422` | `PROPOSED` |
| **Story Planner & Setup** | `GET/POST/PUT /api/mock/v1/sessions`, `GET/PUT /:id/story`, `POST /:id/story/ai-edit`, `POST /:id/story/approve` | P06 Story Planner + P09 Sessions | `SessionSetupPayload`, `StoryAiPromptPayload` | `SessionDetail`, `StoryPlanDetail` | `403`, `409`, `422` | `PROPOSED` |
| **Session Readiness & Start** | `GET /api/mock/v1/sessions/:id/readiness`, `POST /:id/start` | P09 Readiness Gate + P04 Playout | `{ expectedRevision, commandId }` | `ReadinessSnapshot`, `CommandRecord` | `403` (Operator), `409`, `412` (Gate blocked) | `PROPOSED` |
| **Members & Permissions** | `GET /api/mock/v1/members`, `POST /members/invite`, `PUT /members/:id/assignments` | IAM / Workspace RBAC | `{ email }`, `{ assignedSessionIds, expectedRevision }` | `MembersResponse`, `WorkspaceMember` | `403` (Operator), `409`, `422` | `PROPOSED` |
| **Live Control Room** | `GET /api/mock/v1/sessions/:id/control`, `POST /:id/control/commands`, `POST /:id/control/advance-speech` | P09 Command Authority + P04/P07/P08 + WS | `{ type, commandId, expectedRevision, targetSkuId?, commentId? }` | `{ command, snapshot }` | `403`, `409` (Stale rev), `422` (Skip after COMMITTED) | `BLOCKED` (Cần WS + LiveKit thật) |
| **Invite Management & QR** | `GET/POST /api/mock/v1/invites`, `POST /invites/:id/revoke` | P09 Invite Service + LiveKit Token Service | `{ sessionId, label, usageCap, expiresAt }` | `ViewerInviteRecord`, `{ invite, ejectedCount }` | `403`, `404`, `409` | `BLOCKED` (Cần ngắt LiveKit guest `IM-D4`) |
| **Viewer Live Room** | `GET /api/mock/v1/viewer/:sessionId`, `POST /viewer/:sessionId/admit`, `POST /viewer/:sessionId/comments` | P09 Viewer Admission + Comment Intake + LiveKit | `{ inviteToken, nickname }`, `{ guestSessionId, body, clientSubmissionId }` | `ViewerRoomSnapshot`, `{ receiptStatus, commentId }` | `400` (Pre-LIVE), `403` (Revoked), `410` (Expired/Exhausted), `422` (Moderation) | `BLOCKED` (Cần LiveKit subscribe-only) |
| **Session Reports & Exports** | `GET /api/mock/v1/reports/:sessionId` | P09/P12 Analytics & Export Worker | Path `sessionId` | `SessionReportDetail` | `403` (Unassigned), `404`, `409` (Not READY) | `PARTIAL` (Telemetry & Async Export `OPEN`) |

---

## 2. Đánh giá mức độ sẵn sàng tích hợp theo Module

| Module | Frontend State | Trạng thái Tích hợp | Phụ thuộc chặn chính (Blocking Dependency) | Nhóm phụ trách |
| :--- | :--- | :---: | :--- | :--- |
| **01. Auth & Onboarding** | Hoàn tất Mock | `UNVALIDATED` | Chốt nhà cung cấp Managed OIDC, cookie/session security | Platform / Security |
| **02. Merchant Dashboard** | Hoàn tất Mock | `READY` (cho BFF) | Chốt endpoint tổng hợp Dashboard read model | Backend Core |
| **03. AI Presenter & Rights** | Hoàn tất Mock | `PARTIAL` | Quy trình xác minh danh tính Rights Subject (P11) & worker gen clip (P01/P02) | AI Media + Legal/P11 |
| **04. Products & OCOP** | Hoàn tất Mock | `PARTIAL` | Quy trình thẩm định OCOP có thẩm quyền (P09) & object storage upload | Backend Core |
| **05. Knowledge & Claims** | Hoàn tất Mock | `READY` (cho API) | Hợp đồng Docling extraction & Publication Gate (P05) | AI Knowledge (P05) |
| **06. Story Planner & Setup** | Hoàn tất Mock | `READY` (cho API) | Hợp đồng AI Editing Assistant diff/patch & revision lock (P06) | AI Dialogue (P06) |
| **07. Members & Permissions** | Hoàn tất Mock | `READY` (cho API) | Server-side RBAC enforcement + Cross-tenant isolation + Audit Log | Backend IAM |
| **08. Live Control Room** | Hoàn tất Mock | `BLOCKED` | WebSocket event bus, command arbitration (`expected_revision`, `session_epoch`), P04 `PlaybackCompleted ACK` | Realtime + Media (P04/P09) |
| **09. Invite & Viewer Live Room** | Hoàn tất Mock | `BLOCKED` | LiveKit subscribe-only guest token + instant kick on invite revoke (`IM-D4`) | Media / LiveKit |
| **10. Session Reports & Export** | Hoàn tất Mock | `PARTIAL` | Presence telemetry (`concurrent_viewers`) + Async CSV/PDF Unicode worker (P12) | Data / Backend (P12) |

---

## 3. Yêu cầu bắt buộc về Auth, Security & Media phía Backend

1. **Auth & RBAC (Frontend guards KHÔNG đủ cho production):** Backend bắt buộc xác thực OIDC token, kiểm tra `tenant_id`, vai trò `OWNER`/`OPERATOR`, danh sách `assignedSessionIds`, và chặn tuyệt đối Viewer truy cập `/api/*/studio/*`.
2. **Media & LiveKit:** Viewer chỉ nhận token **subscribe-only** (cấm tuyệt đối `canPublish` mic/camera). Khi Owner thu hồi Invite (`POST /invites/:id/revoke`), backend phải lập tức gọi LiveKit Server API `removeParticipant` để ngắt kết nối khách đang xem từ link đó.
3. **Single Speech Authority:** Chỉ `PlaybackCompleted ACK` phát sinh từ P04 Media Playout (có `playback_ack_id` để khử trùng lặp) mới được phép tiến Story Checkpoint và tăng bộ đếm câu AI đã phát.
