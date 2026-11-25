# HOSTRA AI — Frontend Decision Register

> **Sổ đăng ký quyết định chính thức phục vụ triển khai frontend HOSTRA AI.**
> Tổng hợp toàn bộ các quyết định sản phẩm, UX, phân quyền và thị giác đã được xác nhận trong tài liệu nguồn tại `docs/product/frontend/`, đồng thời tách bạch các hạng mục `DRAFT`, `PROPOSED`, `OPEN`, `UNVALIDATED` và `CONFLICT`.
>
> Xem tổng quan kiến trúc và hướng dẫn đọc tài liệu tại [README.md](./README.md).

---

## Quy ước trạng thái (Status Legend)

| Trạng thái | Ý nghĩa |
| :--- | :--- |
| `APPROVED` | Đã có bằng chứng chốt/nghiệm thu rõ ràng trong tài liệu nguồn hoặc xác nhận nghiệm thu của Product Owner. |
| `DRAFT` | Bản nháp tổng hợp, chưa có phê duyệt cuối. |
| `PROPOSED` | Đề xuất kỹ thuật/UX/route/token chưa được khóa chính thức. |
| `OPEN` | Quyết định đang bỏ ngỏ, chưa được chốt — **không được tự suy diễn**. |
| `UNVALIDATED` | Giả định kỹ thuật hoặc dependency chưa qua kiểm chứng PoC/Backend LLD. |
| `CONFLICT` | Có điểm sai lệch giữa các tài liệu nguồn cần lưu ý/xử lý rõ ràng. |
| `PENDING_SOURCE_CONFIRMATION` | Thiếu bằng chứng xác nhận trực tiếp từ tài liệu nguồn. |

---

## 1. Product Scope & Cross-Cutting Governance

| ID | Module | Decision | Status | Source |
| :--- | :--- | :--- | :---: | :--- |
| `Q1–Q17` *(Scope)* | Product Scope | MVP tập trung vào **HOSTRA Private Live Room** (LiveKit riêng, invite-only), chạy **1 phiên LIVE đồng thời** với **2–5 SKU thực phẩm đóng gói** đủ điều kiện mỗi phiên. | `APPROVED` | [Cross-Module Audit v0.1](./modules/HOSTRA_AI_Cross_Module_Audit_Preflight_v0.1.docx), [Blueprint v1.0 DRAFT](./blueprint/HOSTRA_AI_Frontend_Design_Implementation_Blueprint_v1.0_DRAFT.docx) |
| `Q17` | Product Scope | **TikTok Shop / Shopee Live / OBS / RTMP** thuộc định hướng phát triển sau MVP; không có nút kết nối/phát sóng nền tảng ngoài hoạt động trong MVP. | `APPROVED` | [Live Control Room v0.2](./modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.2.docx), [Cross-Module Audit v0.1](./modules/HOSTRA_AI_Cross_Module_Audit_Preflight_v0.1.docx) |
| `SCOPE-NONGOALS` | Product Scope | Không xây dựng native app, checkout/GMV/doanh thu không có nguồn thực, hoặc replay/VOD cho viewer trong MVP. | `APPROVED` | [Viewer Live Room v0.2](./modules/HOSTRA_AI_Viewer_Live_Room_Design_Package_v0.2.docx), [Session Reports v0.2](./modules/HOSTRA_AI_Session_Reports_Design_Package_v0.2.docx), [Blueprint v1.0 DRAFT](./blueprint/HOSTRA_AI_Frontend_Design_Implementation_Blueprint_v1.0_DRAFT.docx) |
| `P1–P2` | Cross-Module Governance | Trong phiên LIVE, **Operator chỉ được đề xuất revision** (giá/facts/story), **Owner phê duyệt**; nếu Owner offline thì revision ở trạng thái chờ duyệt (`Pending Owner`), không tự duyệt thay. | `APPROVED` | [Cross-Module Audit v0.1](./modules/HOSTRA_AI_Cross_Module_Audit_Preflight_v0.1.docx), [Knowledge & Claims v0.2](./modules/HOSTRA_AI_Knowledge_Claims_Design_Package_v0.2.docx), [Live Control Room v0.2](./modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.2.docx) |
| `P3` | Cross-Module Governance | Khi nhiều Operator gửi lệnh đồng thời, **backend phân xử** theo `expected_revision`, `idempotency` và thứ tự ưu tiên (`Safety/Emergency > Stop/Pause > merchant overrides > comments > story`); frontend hiển thị conflict và refetch snapshot. | `APPROVED` | [Cross-Module Audit v0.1](./modules/HOSTRA_AI_Cross_Module_Audit_Preflight_v0.1.docx), [Story Planner v0.2](./modules/HOSTRA_AI_Story_Planner_Live_Session_Design_Package_v0.2.docx), [Members & Permissions v0.2](./modules/HOSTRA_AI_Members_Permissions_Design_Package_v0.2.docx) |
| `Q9 / Q12` | Cross-Module Governance | Chỉ **Workspace Owner** được `START` phiên khi `READY`. **Operator được phân công** có quyền runtime (`Pause/Resume AI`, `Switch SKU`, `Skip Pending`, `Stop`, `Emergency Stop`) kể cả khi Owner offline. | `APPROVED` | [Live Control Room v0.2](./modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.2.docx), [Members & Permissions v0.2](./modules/HOSTRA_AI_Members_Permissions_Design_Package_v0.2.docx) |

---

## 2. Authentication & Workspace

| ID | Module | Decision | Status | Source |
| :--- | :--- | :--- | :---: | :--- |
| `AW-D1=A` | Auth & Workspace | Sử dụng **Managed OIDC hosted sign-in** (branding HOSTRA nếu provider hỗ trợ); Merchant Studio không tự thu mật khẩu hoặc lưu raw refresh token. *(Lựa chọn nhà cung cấp IdP hiện vẫn `UNVALIDATED`/TBD).* | `APPROVED` | [Auth & Workspace v0.2](./modules/HOSTRA_AI_Authentication_Workspace_Design_Package_v0.2.docx) |
| `AW-D2=A` | Auth & Workspace | **Onboarding Wizard hỗ trợ Save Draft**, cho phép quay về Dashboard và tiếp tục sau; các tác vụ async (Presenter generation / OCOP review) không khóa onboarding. | `APPROVED` | [Auth & Workspace v0.2](./modules/HOSTRA_AI_Authentication_Workspace_Design_Package_v0.2.docx) |
| `AW-D3=A` | Auth & Workspace | MVP có **1 Workspace chính cho mỗi Owner**; không làm workspace switcher đa tenant trên UI, nhưng kiến trúc vẫn giữ `workspace_id`. | `APPROVED` | [Auth & Workspace v0.2](./modules/HOSTRA_AI_Authentication_Workspace_Design_Package_v0.2.docx) |
| `AW-D4=A` | Auth & Workspace | **Operator phân công theo từng Live Session**; Workspace Membership không đồng nghĩa có quyền truy cập mọi session. | `APPROVED` | [Auth & Workspace v0.2](./modules/HOSTRA_AI_Authentication_Workspace_Design_Package_v0.2.docx) |
| `AW-D5=A` | Auth & Workspace | Mời Operator qua **email invitation cá nhân có thời hạn**, thu hồi được và kiểm tra đúng danh tính (identity-bound) khi accept. | `APPROVED` | [Auth & Workspace v0.2](./modules/HOSTRA_AI_Authentication_Workspace_Design_Package_v0.2.docx) |

*Hệ quả triển khai:* Viewer không đi qua Merchant OIDC; Rights Subject đi qua luồng consent độc lập; không render dữ liệu private trước khi có authoritative auth + workspace snapshot.

---

## 3. Merchant Dashboard

| ID | Module | Decision | Status | Source |
| :--- | :--- | :--- | :---: | :--- |
| `D1` | Merchant Dashboard | Dashboard theo hướng **Action-Oriented** (giúp người dùng biết trạng thái hiện tại, việc cần xử lý và bước tiếp theo; không thay thế Control Room hay Readiness). | `APPROVED` | [Merchant Dashboard v0.4](./modules/HOSTRA_AI_Merchant_Dashboard_Design_Package_v0.4.docx) |
| `D2` | Merchant Dashboard | **Dynamic Primary CTA** thay đổi theo vai trò (Owner/Operator) và trạng thái phiên (Onboarding / Preparing / Ready → mở Readiness / LIVE → mở Control Room / Stopped → mở Report). | `APPROVED` | [Merchant Dashboard v0.4](./modules/HOSTRA_AI_Merchant_Dashboard_Design_Package_v0.4.docx) |
| `D3` | Merchant Dashboard | **Shared Layout** giữa Owner và Operator (cùng Application Shell, khác nội dung và capabilities theo quyền). | `APPROVED` | [Merchant Dashboard v0.4](./modules/HOSTRA_AI_Merchant_Dashboard_Design_Package_v0.4.docx) |
| `D4 / D6` | Merchant Dashboard | **Action Center dạng danh sách ưu tiên (Priority List)**, hiển thị tối đa **5 tác vụ** nổi bật + nút View All (thứ tự: Safety critical → Session blocker → Approval theo quyền → Setup thiếu → Info). | `APPROVED` | [Merchant Dashboard v0.4](./modules/HOSTRA_AI_Merchant_Dashboard_Design_Package_v0.4.docx) |
| `D5` | Merchant Dashboard | **Featured Session không có video preview** (không tự subscribe LiveKit khi chỉ mở Dashboard); hiển thị tách biệt `Session Lifecycle`, `AI State` và `Media Health`. | `APPROVED` | [Merchant Dashboard v0.4](./modules/HOSTRA_AI_Merchant_Dashboard_Design_Package_v0.4.docx) |
| `D7` | Merchant Dashboard | **4 Asset Status Cards độc lập** (Presenter, Products/OCOP, Knowledge, Session Prep); không suy diễn tổng số ở workspace thành `Session READY`. | `APPROVED` | [Merchant Dashboard v0.4](./modules/HOSTRA_AI_Merchant_Dashboard_Design_Package_v0.4.docx) |
| `D8` | Merchant Dashboard | **Recent Sessions** hiển thị tối đa **3 phiên gần nhất** + nút View All. | `APPROVED` | [Merchant Dashboard v0.4](./modules/HOSTRA_AI_Merchant_Dashboard_Design_Package_v0.4.docx) |
| `L1=A / H1=A` | Merchant Dashboard | **Bố cục 2 cột** (Action Center ~60% / Featured Session ~40% trên desktop, 1 cột trên mobile) theo **Visual Style A**. | `APPROVED` | [Merchant Dashboard v0.4](./modules/HOSTRA_AI_Merchant_Dashboard_Design_Package_v0.4.docx) |

---

## 4. AI Presenter Studio

| ID | Module | Decision | Status | Source |
| :--- | :--- | :--- | :---: | :--- |
| `PR-D1=A` | AI Presenter Studio | **Wizard 4 bước có Save Draft / Back / Resume** (`Portrait → Rights → Style + Voice → Generate & Preview`), tách bản nháp với generation job. | `APPROVED` | [Presenter Studio v0.2](./modules/HOSTRA_AI_Presenter_Studio_Design_Package_v0.2.docx) |
| `PR-D2=A` | AI Presenter Studio | Mặc định dùng **licensed preset voice**; voice clone bị ẩn/disabled cho đến khi đạt consent giọng nói riêng + kiểm chứng kỹ thuật + license. | `APPROVED` | [Presenter Studio v0.2](./modules/HOSTRA_AI_Presenter_Studio_Design_Package_v0.2.docx) |
| `PR-D3=A` | AI Presenter Studio | **Duyệt gói clip (versioned pack) sau khi qua machine QC**; clip lỗi được yêu cầu tạo lại riêng (`Needs Rework`) và tạo pack revision mới để QC lại toàn pack trước khi Owner duyệt. | `APPROVED` | [Presenter Studio v0.2](./modules/HOSTRA_AI_Presenter_Studio_Design_Package_v0.2.docx) |
| `PR-D4=A` | AI Presenter Studio | **Generation chạy nền** — rời màn hình không hủy job; theo dõi tiến độ theo stage từ backend tại Library/Job view (không hiển thị % hoặc ETA giả). | `APPROVED` | [Presenter Studio v0.2](./modules/HOSTRA_AI_Presenter_Studio_Design_Package_v0.2.docx) |
| `PR-ADD-1` | AI Presenter Studio | Chọn đúng **1 trong 3 style presets** trước khi generate: **`Chuyên nghiệp`**, **`Thân thiện`**, **`Năng động`** (không dùng free-prompt editor). *(Hiệu năng/chất lượng thực tế của 3 style vẫn `UNVALIDATED` ở PoC).* | `APPROVED` | [Presenter Studio v0.2](./modules/HOSTRA_AI_Presenter_Studio_Design_Package_v0.2.docx) |
| `PR-ADD-2` | AI Presenter Studio | **Preview & So sánh trước/sau:** Lần tạo đầu so sánh *ảnh chân dung gốc ↔ video v1* (không tạo A/B giả); chỉ mở chế độ **so sánh video A ↔ video B** cùng motion template khi có ít nhất 2 phiên bản candidate. | `APPROVED` | [Presenter Studio v0.2](./modules/HOSTRA_AI_Presenter_Studio_Design_Package_v0.2.docx) |
| `PR-RIGHTS / REUSE` | AI Presenter Studio | **Rights Consent độc lập** do Rights Subject tự xác nhận (Owner không tự tick hộ); thu hồi/hết hạn quyền vô hiệu hóa asset & cache ngay lập tức. Phiên bản mới tạo lại không tự thay thế bản đã duyệt; các phiên cũ giữ snapshot version bất biến. | `APPROVED` | [Presenter Studio v0.2](./modules/HOSTRA_AI_Presenter_Studio_Design_Package_v0.2.docx) |

---

## 5. Products & OCOP

| ID | Module | Decision | Status | Source |
| :--- | :--- | :--- | :---: | :--- |
| `PC-D1=A` | Products & OCOP | **Product Catalog:** Bảng dữ liệu trên desktop, chuyển thành **product cards trên mobile** (cùng dữ liệu và phân quyền; tách biệt các cột/nhãn OCOP, Knowledge và Session Eligibility). | `APPROVED` | [Products & OCOP v0.2](./modules/HOSTRA_AI_Products_OCOP_Design_Package_v0.2.docx) |
| `PC-D2=A` | Products & OCOP | **Product Wizard 4 bước có Save Draft** (`Product basics → OCOP dossier → Food documents → Review & save/submit`), cho phép lưu dở và quay lại mà không tự động gửi xác minh. | `APPROVED` | [Products & OCOP v0.2](./modules/HOSTRA_AI_Products_OCOP_Design_Package_v0.2.docx) |
| `PC-D3=A` | Products & OCOP | **Product Detail gồm 4 tabs có deep-link:** `Overview`, `OCOP`, `Facts`, `Versions`. | `APPROVED` | [Products & OCOP v0.2](./modules/HOSTRA_AI_Products_OCOP_Design_Package_v0.2.docx) |
| `PC-D4=B` | Products & OCOP | **Operator được tạo/sửa draft sản phẩm và upload tài liệu** trong phạm vi được cấp, nhưng **không** được Submit xác minh OCOP hay duyệt tri thức. | `APPROVED` | [Products & OCOP v0.2](./modules/HOSTRA_AI_Products_OCOP_Design_Package_v0.2.docx) |
| `PC-D5=A` | Products & OCOP | **Chỉ Owner thực hiện hành động `Submit for Verification` tường minh** (tách biệt với thao tác upload/extract, có hộp thoại xác nhận phiên bản hồ sơ). | `APPROVED` | [Products & OCOP v0.2](./modules/HOSTRA_AI_Products_OCOP_Design_Package_v0.2.docx) |
| `PC-OCOP-GATE` | Products & OCOP | **OCOP Verification thuộc thẩm quyền P09**, độc lập với Owner Approval. Upload logo/ảnh giấy chứng nhận không tự tạo `VERIFIED`; thiếu chứng cứ trả về `PENDING_REVIEW` trung tính (không quy chụp giả mạo). | `APPROVED` | [Products & OCOP v0.2](./modules/HOSTRA_AI_Products_OCOP_Design_Package_v0.2.docx) |

---

## 6. Knowledge & Claims

| ID | Module | Decision | Status | Source |
| :--- | :--- | :--- | :---: | :--- |
| `KC-D1=A` | Knowledge & Claims | **Review theo từng SKU với bố cục 2 vùng:** Tài liệu nguồn (evidence) bên trái, danh sách Facts/Claims bên phải trên desktop; mobile dùng full-screen evidence viewer/drawer. | `APPROVED` | [Knowledge & Claims v0.2](./modules/HOSTRA_AI_Knowledge_Claims_Design_Package_v0.2.docx), [Cross-Module Audit v0.1](./modules/HOSTRA_AI_Cross_Module_Audit_Preflight_v0.1.docx) |
| `KC-D2=A` | Knowledge & Claims | Phân loại Facts/Claims thành **5 nhóm:** `Giá`, `Thông số`, `Nguồn gốc`, `Chính sách`, `Marketing Claims` (kèm bộ đếm và trạng thái từng nhóm). | `APPROVED` | [Knowledge & Claims v0.2](./modules/HOSTRA_AI_Knowledge_Claims_Design_Package_v0.2.docx) |
| `KC-D3=A` | Knowledge & Claims | **Duyệt từng mục bắt buộc**, sau đó **Owner phê duyệt 1 gói phiên bản (Knowledge Snapshot)** hợp lệ; không có nút "duyệt mù cả tài liệu"; claim bị chặn/thiếu chứng cứ phải bị loại rõ ràng khỏi gói. | `APPROVED` | [Knowledge & Claims v0.2](./modules/HOSTRA_AI_Knowledge_Claims_Design_Package_v0.2.docx) |
| `KC-D4=A` | Knowledge & Claims | **Operator được tải tài liệu và soạn/đề xuất draft**; **chỉ Owner có quyền phê duyệt** Knowledge Snapshot và Live Revision. | `APPROVED` | [Knowledge & Claims v0.2](./modules/HOSTRA_AI_Knowledge_Claims_Design_Package_v0.2.docx) |
| `KC-D5=A` | Knowledge & Claims | **AI Speech Preview dạng văn bản (text-only) kèm nhãn trích dẫn nguồn**; không yêu cầu sinh audio/TTS để duyệt tri thức trong MVP. | `APPROVED` | [Knowledge & Claims v0.2](./modules/HOSTRA_AI_Knowledge_Claims_Design_Package_v0.2.docx) |

*Lưu ý vệ sinh tài liệu:* `KC-D1–KC-D5` đã được khóa (`CLOSED/APPROVED`) trong bản `v0.2`; các ghi chú cũ ở module khác nói `KC-D1–KC-D5` còn `OPEN` không còn hiệu lực.

---

## 7. Story Planner & Live Session Setup

| ID | Module | Decision | Status | Source |
| :--- | :--- | :--- | :---: | :--- |
| `SS-D1=A` | Story Planner & Setup | **Session Setup Wizard 4 bước + Save Draft** (`Assets & SKU → Goal & Constraints → Story Plan → Review & Submit`); tách riêng trang Readiness sau wizard. | `APPROVED` | [Story Planner & Live Session v0.2](./modules/HOSTRA_AI_Story_Planner_Live_Session_Design_Package_v0.2.docx) |
| `SS-D2=A` | Story Planner & Setup | **Timeline Story Arcs** (có thể sắp xếp thứ tự arc và mở panel chi tiết), không dùng một văn bản kịch bản dài bất biến. | `APPROVED` | [Story Planner & Live Session v0.2](./modules/HOSTRA_AI_Story_Planner_Live_Session_Design_Package_v0.2.docx) |
| `SS-D3=A` | Story Planner & Setup | **Text preview kèm nguồn facts đã duyệt**; không bắt buộc TTS preview. | `APPROVED` | [Story Planner & Live Session v0.2](./modules/HOSTRA_AI_Story_Planner_Live_Session_Design_Package_v0.2.docx) |
| `SS-D4=A` | Story Planner & Setup | **Review từng arc rồi Owner duyệt toàn bộ Story Revision** gắn với phiên bản Presenter/SKU/Knowledge cụ thể; mọi chỉnh sửa mới làm vô hiệu approval cũ. | `APPROVED` | [Story Planner & Live Session v0.2](./modules/HOSTRA_AI_Story_Planner_Live_Session_Design_Package_v0.2.docx) |
| `SS-D5=A` | Story Planner & Setup | **Readiness Checklist là màn hình riêng** hiển thị từng gate độc lập (`PASS`/`PENDING`/`BLOCKED`), deep-link sửa lỗi và nút **`START` chỉ dành cho Owner**. | `APPROVED` | [Story Planner & Live Session v0.2](./modules/HOSTRA_AI_Story_Planner_Live_Session_Design_Package_v0.2.docx) |
| `SS-X1` | Story Planner & Setup | **AI Editing Assistant (chat chỉnh Story Plan):** AI chỉ trả về đề xuất patch + diff Before/After + nguồn facts; người dùng chủ động nhấn *Apply to Draft*, không tự approve hoặc áp dụng thẳng lên phiên LIVE. | `APPROVED` | [Story Planner & Live Session v0.2](./modules/HOSTRA_AI_Story_Planner_Live_Session_Design_Package_v0.2.docx) |
| `SS-X2` | Story Planner & Setup | **Kéo-thả 2–5 SKU** từ catalog vào phiên và sắp xếp thứ tự 1–5; bắt buộc có nút thay thế cho mobile/keyboard (`+ Thêm`, `Đưa lên/Đưa xuống`); "đã chọn SKU" không đồng nghĩa đủ điều kiện Start. | `APPROVED` | [Story Planner & Live Session v0.2](./modules/HOSTRA_AI_Story_Planner_Live_Session_Design_Package_v0.2.docx) |
| `SS-OP-PRELIVE` | Story Planner & Setup | Quyền **Operator tạo/sửa cấu hình pre-live Session Setup & Story Plan**. | `OPEN` | [Story Planner & Live Session v0.2](./modules/HOSTRA_AI_Story_Planner_Live_Session_Design_Package_v0.2.docx) *(§01, §08, §15 — mặc định chỉ Owner cho tới khi có quyết định)* |

---

## 8. Live Control Room

| ID | Module | Decision | Status | Source |
| :--- | :--- | :--- | :---: | :--- |
| `CR-D1=A` | Live Control Room | **Bố cục 2 cột trên desktop (~60/40):** Video preview & Product Context (Active/Next/Referenced SKU) bên trái; Comments, Queue & AI Activity bên phải. | `APPROVED` | [Live Control Room v0.2](./modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.2.docx) |
| `CR-D2=A` | Live Control Room | **Comments + Pending Queue luôn hiển thị** trên desktop; **AI Activity dạng expandable** panel. | `APPROVED` | [Live Control Room v0.2](./modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.2.docx) |
| `CR-D3=A` | Live Control Room | **Runtime Control Bar cố định phía dưới**; nhóm lệnh nguy hiểm (`Stop` / `Emergency Stop`) tách riêng khỏi thao tác vận hành thường. | `APPROVED` | [Live Control Room v0.2](./modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.2.docx) |
| `CR-D4=A` | Live Control Room | **Status Bar gọn** tách biệt `Session`, `AI`, `Media`, `Publisher`, `Freshness`; **Media Diagnostics mở trong drawer riêng**. | `APPROVED` | [Live Control Room v0.2](./modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.2.docx) |
| `CR-D5=A` | Live Control Room | `Stop` yêu cầu hộp thoại xác nhận; `Emergency Stop` có cơ chế bảo vệ nhanh, không đợi Owner online và luôn ghi audit. | `APPROVED` | [Live Control Room v0.2](./modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.2.docx) |
| `CR-D6=A` | Live Control Room | **Khu vực "AI sắp nói":** Chỉ hiển thị tóm tắt an toàn kèm nhãn **`Dự kiến · Chưa phát`**; không hiển thị raw unverified claims hoặc cam kết chắc chắn sẽ phát. | `APPROVED` | [Live Control Room v0.2](./modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.2.docx) |
| `CR-D7=A` | Live Control Room | **Queue Controls:** Hỗ trợ `Prioritize` / `Skip` chỉ cho comment/task **chưa `COMMITTED`** + `View All` (không bypass moderation/claim gate). | `APPROVED` | [Live Control Room v0.2](./modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.2.docx) |
| `CR-D8=A` | Live Control Room | **Switch SKU qua Drawer:** Kiểm tra eligibility, gửi lệnh kèm `expected_revision`, theo dõi trạng thái Pending Switch; **Active SKU chỉ đổi khi backend trả `APPLIED`** tại safe boundary. | `APPROVED` | [Live Control Room v0.2](./modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.2.docx) |
| `CR-D9=A` | Live Control Room | **Media `DEGRADED`:** Hiển thị banner cảnh báo, chế độ fallback thực tế đang chạy, hướng xử lý và nút mở Diagnostics (không đổi Session `LIVE` thành `STOPPED`). | `APPROVED` | [Live Control Room v0.2](./modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.2.docx) |
| `CR-D10=A` | Live Control Room | **Operator Conflict Handling:** Hiển thị Toast + Activity Log ghi rõ `command_id`, actor, loại lệnh, outcome, lý do và revision hiện tại; refetch snapshot thay vì silent overwrite. | `APPROVED` | [Live Control Room v0.2](./modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.2.docx) |
| `CR-D11=B` | Live Control Room | **Emergency Stop dùng Modal xác nhận nhanh 1 bước** (không bắt buộc nhấn giữ / long-press, không cần Owner online); nút xác nhận đỏ đặc `#DC2626`/chữ trắng. | `APPROVED` | [Live Control Room v0.2](./modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.2.docx), [Visual Redesign v0.4](./design/HOSTRA_Visual_Redesign_and_Figma_Handoff_v0.4.docx) |
| `CR-D12=A` | Live Control Room | **Mobile Control Room:** Chuyển `Comments` và `Queue` bằng tabs; `AI Activity` dạng expandable; thanh điều khiển tách nhóm nguy hiểm. | `APPROVED` | [Live Control Room v0.2](./modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.2.docx) |

---

## 9. Viewer Live Room

| ID | Module | Decision | Status | Source |
| :--- | :--- | :--- | :---: | :--- |
| `Q3` | Viewer Live Room | Viewer tham gia bằng **Invitation Link / QR + Nickname**, không yêu cầu tài khoản merchant; media ở chế độ **subscribe-only** qua LiveKit. | `APPROVED` | [Viewer Live Room v0.2](./modules/HOSTRA_AI_Viewer_Live_Room_Design_Package_v0.2.docx) |
| `VR-D1=B` | Viewer Live Room | **Mobile-first Layout:** Video ở trên, Product Card và bình luận ở dưới; **không để bình luận đè lên video presenter**. | `APPROVED` | [Viewer Live Room v0.2](./modules/HOSTRA_AI_Viewer_Live_Room_Design_Package_v0.2.docx) |
| `VR-D2=A` | Viewer Live Room | **Desktop Layout 2 cột:** Video + Active Product Card bên trái (60–65%), Comments + Composer bên phải (35–40%), không có điều khiển merchant. | `APPROVED` | [Viewer Live Room v0.2](./modules/HOSTRA_AI_Viewer_Live_Room_Design_Package_v0.2.docx) |
| `VR-D3=A` | Viewer Live Room | **Waiting Room khóa bình luận trước khi `LIVE`** (kể cả khi `STARTING`, chỉ mở composer khi backend xác nhận `LIVE`). | `APPROVED` | [Viewer Live Room v0.2](./modules/HOSTRA_AI_Viewer_Live_Room_Design_Package_v0.2.docx) |
| `VR-D4=A` | Viewer Live Room | **Active Product Card nằm dưới player** (không overlay che video), chỉ hiển thị thông tin public đã được duyệt theo authoritative `active_sku`. | `APPROVED` | [Viewer Live Room v0.2](./modules/HOSTRA_AI_Viewer_Live_Room_Design_Package_v0.2.docx) |
| `VR-D5=A` | Viewer Live Room | **Tính lượt invite cap theo admission thành công;** refresh trong cùng guest session không cộng thêm lượt. *(Cơ chế guest identity & atomic concurrency cần Backend LLD).* | `APPROVED` | [Viewer Live Room v0.2](./modules/HOSTRA_AI_Viewer_Live_Room_Design_Package_v0.2.docx) |
| `VR-D6=A` | Viewer Live Room | **Session Ended:** Khi `STOPPED` chuyển màn hình kết thúc + nút Thoát, tắt composer & unsubscribe media; **không có replay/VOD** trong MVP. | `APPROVED` | [Viewer Live Room v0.2](./modules/HOSTRA_AI_Viewer_Live_Room_Design_Package_v0.2.docx) |
| `VR-D7=A` | Viewer Live Room | **Trạng thái bình luận:** Hiện local `SENDING` (chỉ người gửi thấy) → chuyển `RECEIVED` hoặc `REJECTED` theo server receipt (không hứa AI sẽ trả lời). Trạng thái video buffering và mất kết nối chat hiển thị độc lập. | `APPROVED` | [Viewer Live Room v0.2](./modules/HOSTRA_AI_Viewer_Live_Room_Design_Package_v0.2.docx) |

---

## 10. Invite Management

| ID | Module | Decision | Status | Source |
| :--- | :--- | :--- | :---: | :--- |
| `IM-D1=A` | Invite Management | Hỗ trợ **nhiều named invite links** trong cùng một phiên (mỗi link có label, usage cap, expiry, trạng thái và audit riêng). | `APPROVED` | [Invite Management v0.2](./modules/HOSTRA_AI_Invite_Management_Design_Package_v0.2.docx) |
| `IM-D2=A` | Invite Management | Hỗ trợ **Expiry presets + custom** với timezone rõ ràng và validation tại backend; usage limit phải là số nguyên dương. | `APPROVED` | [Invite Management v0.2](./modules/HOSTRA_AI_Invite_Management_Design_Package_v0.2.docx) |
| `IM-D3=A` | Invite Management | **Invite link bất biến sau khi phát hành** (không chỉnh sửa expiry/cap; muốn đổi phải tạo link mới và revoke link cũ nếu cần). | `APPROVED` | [Invite Management v0.2](./modules/HOSTRA_AI_Invite_Management_Design_Package_v0.2.docx) |
| `IM-D4=A` | Invite Management | **Revoke link chặn join mới và thu hồi/ngắt kết nối các viewer đang xem** đã vào từ link đó (không ảnh hưởng viewer từ link khác). *(Cơ chế kick LiveKit tức thì cần Backend/Media sign-off).* | `APPROVED` | [Invite Management v0.2](./modules/HOSTRA_AI_Invite_Management_Design_Package_v0.2.docx) |
| `IM-D5=A` | Invite Management | Quản lý tập trung tại **tab Invitations trong Session Detail** (Owner-only); có **shortcut Copy ở Control Room** cũng chỉ dành cho Owner (phải chọn link nếu có nhiều link active). | `APPROVED` | [Invite Management v0.2](./modules/HOSTRA_AI_Invite_Management_Design_Package_v0.2.docx) |
| `IM-D6` | Invite Management | **QR Code đi kèm từng link:** Mã hóa đúng HTTPS invitation URL do backend cấp (tuyệt đối không nhúng raw LiveKit token hay secret); cho tải QR (đề xuất PNG) sau khi server xác nhận tạo link. | `APPROVED` | [Invite Management v0.2](./modules/HOSTRA_AI_Invite_Management_Design_Package_v0.2.docx) |

---

## 11. Members & Permissions

| ID | Module | Decision | Status | Source |
| :--- | :--- | :--- | :---: | :--- |
| `MP-D1=A` | Members & Permissions | **Member Directory** dạng bảng trên desktop, card trên mobile; mở **Member Detail bằng Drawer**. | `APPROVED` | [Members & Permissions v0.2](./modules/HOSTRA_AI_Members_Permissions_Design_Package_v0.2.docx) |
| `MP-D2=A` | Members & Permissions | **Chỉ Workspace Owner** có quyền mời, cấp quyền, chỉnh sửa phân công và thu hồi quyền Operator. | `APPROVED` | [Members & Permissions v0.2](./modules/HOSTRA_AI_Members_Permissions_Design_Package_v0.2.docx) |
| `MP-D3=A` | Members & Permissions | Owner thực hiện **phân công session (Session Assignments)** ngay trong tab của Member Detail Drawer (multi-select + diff trước khi Save với `expected_revision`). | `APPROVED` | [Members & Permissions v0.2](./modules/HOSTRA_AI_Members_Permissions_Design_Package_v0.2.docx) |
| `MP-D4=A` | Members & Permissions | **Thu hồi quyền (Revoke)** bắt buộc có hộp thoại xác nhận hậu quả, chờ kết quả authoritative từ backend và ghi **Audit Log**; thu hồi Operator B không ảnh hưởng Operator A. | `APPROVED` | [Members & Permissions v0.2](./modules/HOSTRA_AI_Members_Permissions_Design_Package_v0.2.docx) |
| `MP-D5=A` | Members & Permissions | **Rights Subject có consent portal riêng** tách biệt hoàn toàn với Member Directory; Owner chỉ thấy trạng thái tóm tắt trong Presenter Studio, không xem raw private consent evidence. | `APPROVED` | [Members & Permissions v0.2](./modules/HOSTRA_AI_Members_Permissions_Design_Package_v0.2.docx) |
| `MP-N1` | Members & Permissions | **Quan hệ N:N (Multiple Operators):** Một Live Session có thể được phân công **nhiều Operator**, và một Operator có thể được phân công nhiều session khác nhau (mỗi cặp `(session_id, operator_id)` có grant độc lập). | `APPROVED` | [Members & Permissions v0.2](./modules/HOSTRA_AI_Members_Permissions_Design_Package_v0.2.docx) |

---

## 12. Session Reports & History

| ID | Module | Decision | Status | Source |
| :--- | :--- | :--- | :---: | :--- |
| `SR-D1=A` | Session Reports | **Bố cục Report Overview:** KPI Summary Cards ở trên + **3 tabs chi tiết** (`AI & Comments`, `Media & Health`, `Activity & Audit`). | `APPROVED` | [Session Reports v0.2](./modules/HOSTRA_AI_Session_Reports_Design_Package_v0.2.docx) |
| `SR-D2=A` | Session Reports | **Phân quyền xem báo cáo:** Owner xem toàn bộ workspace; **Operator chỉ xem báo cáo rút gọn** (masked actors/audit) của các phiên được phân công và **không có quyền Export**. | `APPROVED` | [Session Reports v0.2](./modules/HOSTRA_AI_Session_Reports_Design_Package_v0.2.docx) |
| `SR-D3=A` | Session Reports | **Owner được xuất CSV Event Log + PDF Summary** khi báo cáo ở trạng thái `REPORT_READY` (async job, link tải có hạn, CSV chống formula injection `= + - @`). | `APPROVED` | [Session Reports v0.2](./modules/HOSTRA_AI_Session_Reports_Design_Package_v0.2.docx) |
| `SR-D4=A` | Session Reports | **Playback ACK semantics:** Chỉ đếm câu trả lời/lượt nói AI đã phát dựa trên **`PlaybackCompleted ACK`** từ P04 (không đếm theo LLM hay TTS completion; không suy diễn server ACK thành viewer-audible). | `APPROVED` | [Session Reports v0.2](./modules/HOSTRA_AI_Session_Reports_Design_Package_v0.2.docx) |
| `SR-D5=A` | Session Reports | **Data Completeness trung thực:** Số liệu thiếu nguồn hiển thị **`N/A` hoặc `Partial`** kèm nguồn đo và lý do; tuyệt đối không điền `0` giả hoặc bịa số liệu. | `APPROVED` | [Session Reports v0.2](./modules/HOSTRA_AI_Session_Reports_Design_Package_v0.2.docx) |
| `SR-ADD-01` | Session Reports | **Biểu đồ livestream, tổng thời lượng và lượt xem:** Gồm biểu đồ `New successful admissions` theo bucket 5/10/15 phút, `State timeline` (LIVE / AI PAUSED / MEDIA DEGRADED) và `Concurrent viewers` *(chỉ hiển thị khi có telemetry presence đo được, nếu thiếu hiện N/A)*. | `APPROVED` | [Session Reports v0.2](./modules/HOSTRA_AI_Session_Reports_Design_Package_v0.2.docx) |

---

## 13. Global Design System & Visual Redesign v0.4

| ID | Module | Decision | Status | Source |
| :--- | :--- | :--- | :---: | :--- |
| `DS-D1=A` | Global Design System | **Typography:** Font chính **`Be Vietnam Pro`**, fallback **`Inter, sans-serif`**; ưu tiên hiển thị chuẩn dấu tiếng Việt và dùng tabular numerals cho số liệu. | `APPROVED` | [Global Design System v0.2](./modules/HOSTRA_AI_Global_Design_System_and_Prototype_Spec_v0.2.docx), [Visual Redesign v0.4](./design/HOSTRA_Visual_Redesign_and_Figma_Handoff_v0.4.docx) |
| `DS-D2=A` | Global Design System | **Visual Style:** Premium minimal SaaS, ít trang trí, bo góc card `~12px`, ưu tiên viền nhẹ thay vì shadow nặng. | `APPROVED` | [Global Design System v0.2](./modules/HOSTRA_AI_Global_Design_System_and_Prototype_Spec_v0.2.docx) |
| `DS-D3=B` | Global Design System | **Light Mode + Dark Mode ngay trong MVP**, chia sẻ cùng information architecture, nhãn và phân quyền. | `APPROVED` | [Global Design System v0.2](./modules/HOSTRA_AI_Global_Design_System_and_Prototype_Spec_v0.2.docx), [Visual Redesign v0.4](./design/HOSTRA_Visual_Redesign_and_Figma_Handoff_v0.4.docx) |
| `DS-D4=A` | Global Design System | **Navigation:** Sidebar cố định trên desktop (`232px` mở rộng / `72px` thu gọn ở viewport hẹp), chuyển sang drawer trên mobile. | `APPROVED` | [Global Design System v0.2](./modules/HOSTRA_AI_Global_Design_System_and_Prototype_Spec_v0.2.docx) |
| `DS-D5=A` | Global Design System | **Feedback Pattern:** Kết hợp Inline field validation + Success Toast (chỉ sau xác nhận backend) + Persistent Critical Banner (không auto-dismiss). | `APPROVED` | [Global Design System v0.2](./modules/HOSTRA_AI_Global_Design_System_and_Prototype_Spec_v0.2.docx) |
| `DS-D6=A` | Global Design System | **Figma Handoff Target:** Hướng tới Figma editable components (variables, variants, Auto Layout) + interactive prototype cho 8 flows `PT-01`–`PT-08`. *(Hiện mới có visual references v0.4 và prototype một phần).* | `APPROVED` *(yêu cầu)* / `OPEN` *(bàn giao)* | [Global Design System v0.2](./modules/HOSTRA_AI_Global_Design_System_and_Prototype_Spec_v0.2.docx), [Blueprint v1.0 DRAFT](./blueprint/HOSTRA_AI_Frontend_Design_Implementation_Blueprint_v1.0_DRAFT.docx) |
| `VR-V04-PALETTE` | Visual Redesign v0.4 | **Chuẩn màu & bề mặt v0.4 đã nghiệm thu:** Brand Navy `#0F172A`, **Primary CTA Amber `#F5C430`** (chữ Navy), Soft Yellow `#FBE580` (accent/tint), White `#FFFFFF`, Cool Gray `#E2E8F0`, Destructive `#DC2626` (chữ trắng); Light canvas `#F7F9FC`, Dark canvas `#0B1322` / card `#121F32` / nested `#19283E`. | `APPROVED` | [Visual Redesign v0.4](./design/HOSTRA_Visual_Redesign_and_Figma_Handoff_v0.4.docx), [AGENTS.md](../../../AGENTS.md) |
| `DS-MOTION` | Global Design System | **Interaction Motion:** Chuyển động tối giản có chủ đích (`120–240ms`), tôn trọng `prefers-reduced-motion`, không làm chậm trạng thái LIVE/Emergency. *(Giá trị ms cụ thể là `PROPOSED`).* | `APPROVED` *(nguyên tắc)* / `PROPOSED` *(thông số)* | [Global Design System v0.2](./modules/HOSTRA_AI_Global_Design_System_and_Prototype_Spec_v0.2.docx), [Visual Redesign v0.4](./design/HOSTRA_Visual_Redesign_and_Figma_Handoff_v0.4.docx) |
| `DS-TOKENS-SEMANTIC` | Global Design System | Bảng mã hex chi tiết cho semantic tokens (`success`/`warning`/`error`/`info`, focus ring) và kích thước breakpoint cụ thể. | `PROPOSED` | [Global Design System v0.2](./modules/HOSTRA_AI_Global_Design_System_and_Prototype_Spec_v0.2.docx) *(§3.2, §04 — cần kiểm contrast trực quan trước khi khóa release)* |

---

## Open Decisions / Conflicts / Unvalidated Assumptions

### A. Conflicts & Sai lệch giữa các tài liệu cần lưu ý

| ID | Mô tả mâu thuẫn / sai lệch | Nguồn liên quan | Hướng xử lý hiện tại |
| :--- | :--- | :--- | :--- |
| `CONF-01` | **Màu Primary CTA & Dark surface tokens:** GDS v0.2 dùng `#FBE580` cho CTA và Dark `#0B1220`/`#111C2E`; Visual Redesign v0.4 tinh chỉnh Primary CTA thành Amber **`#F5C430`** (giữ `#FBE580` làm soft accent) và Dark **`#0B1322`/`#121F32`/`#19283E`**. | GDS v0.2 (§3.1–3.2) vs Visual Redesign v0.4 (§2b, §8) & `AGENTS.md` §6 | **Áp dụng Visual Redesign v0.4** làm chuẩn thị giác; chốt lại bảng semantic token đầy đủ ở bước F0. |
| `CONF-02` | **WorkspaceSwitcher trong Dashboard v0.4 vs Single Workspace MVP (`AW-D3=A`):** Dashboard v0.4 (§07) liệt kê component `WorkspaceSwitcher`, nhưng Auth & Workspace v0.2 (`AW-D3=A`) và Members v0.2 khóa MVP chỉ có **1 Workspace chính cho mỗi Owner, không làm multi-workspace switcher**. | Dashboard v0.4 vs Auth & Workspace v0.2 / Members v0.2 | **Ưu tiên `AW-D3=A`** (chỉ hiển thị tên workspace hiện tại trong MVP, không làm switcher đa tenant; giữ `workspace_id` trong data model). |
| `CONF-03` | **Ghi chú lỗi thời về `KC-D1–KC-D5`:** Story Planner v0.2, Live Control Room v0.2 và Viewer Live Room v0.2 còn ghi `KC-D1–KC-D5` là `OPEN`. | Story/Control/Viewer v0.2 vs Knowledge v0.2 & Audit v0.1 (`AUD-02`) | **`KC-D1–KC-D5 = A` đã CLOSED/APPROVED** theo Knowledge & Claims v0.2 và Cross-Module Audit. |
| `CONF-04` | **Đặt tên Frontend Route chưa thống nhất tuyệt đối:** `/auth/sign-in` vs `/login`; `/live/:id` vs `/live/:inviteToken`; `/rights/consent/:requestId` vs `/rights/consent/:token`; `/studio/products/:skuId` vs `/studio/products/:id?tab=...`. | Blueprint v1.0 DRAFT, Audit v0.1, Auth v0.2, Presenter v0.2, Products v0.2, Invites v0.2 | Tất cả route hiện là `PROPOSED`; thống nhất bảng route nội bộ ở Phase F0 trước khi nối API. |
| `CONF-05` | **Bản cũ `Live Control Room v0.1` còn trong `modules/`:** Chứa đề xuất `CR-D1`–`CR-D5` ở trạng thái `OPEN`, đã bị `v0.2` thay thế. | `modules/HOSTRA_AI_Live_Control_Room_Design_Package_v0.1.docx` vs `v0.2.docx` | Chỉ đọc `v0.2.docx`; đề xuất user chuyển `v0.1.docx` vào `archive/`. |

### B. Open Product / UX Decisions

| ID | Nội dung còn mở | Trạng thái | Ghi chú |
| :--- | :--- | :---: | :--- |
| `OPEN-UX-01` | Quyền **Operator tạo/sửa pre-live Session Setup & Story Plan** | `OPEN` | Mặc định chỉ Owner cho đến khi Product Owner chốt (`Story Planner v0.2` §08, §15). |
| `OPEN-UX-02` | Chính sách **lưu giữ lựa chọn Theme (Light/Dark/System)** phía client hay backend profile | `OPEN` | Ghi nhận trong GDS v0.2 (`CMP-12`). |
| `OPEN-UX-03` | Chính sách **giữ hay thu hồi quyền xem Report lịch sử** sau khi Operator bị gỡ khỏi session assignment | `OPEN` | Mặc định thu hồi cùng assignment trừ khi có retention policy riêng (`Session Reports v0.2` §10, `RPT-O6`). |
| `OPEN-UX-04` | **Frontend Blueprint v1.0** và **Figma native editable library / 8 clickable flows (`PT-01`–`PT-08`)** | `DRAFT` / `OPEN` | Blueprint v1.0 đang ở trạng thái `DRAFT`; file `HOSTRA_Figma_Visual_Redesign_Kit_v0.4.zip` được nêu trong Handoff v0.4 hiện chưa có trong repo. |

### C. Unvalidated Technical Dependencies (Chặn Backend Integration, không chặn UI Mock-first)

| Priority | Hạng mục chưa được kiểm chứng / sign-off | Owner dự kiến | Trạng thái |
| :---: | :--- | :--- | :---: |
| `P0` | Lựa chọn **Managed OIDC provider**, luồng callback, cookie/token security & invite TTL policy | Backend / Security | `UNVALIDATED` |
| `P0` | **Canonical REST & WebSocket contracts:** Endpoints, state enums, `expected_revision`, `session_epoch`, event ordering/replay, idempotency | Backend / Realtime | `UNVALIDATED` |
| `P0` | **LiveKit guest token revocation & active-viewer ejection** khi revoke invite (`IM-D4`); atomic invite cap & refresh same guest session (`VR-D5`) | Media / Security | `UNVALIDATED` |
| `P0` | **Rights Subject identity verification / consent evidence retention** (P11) và **nguồn xác minh OCOP có thẩm quyền** (P09) | Legal / Product / Backend | `UNVALIDATED` |
| `P0` | **Live revision safe boundary**, vô hiệu hóa speech/TTS lỗi thời (P04/P05/P08) và chất lượng/giới hạn **AI Editing Assistant patch** (P06) | AI / Media / Backend | `UNVALIDATED` |
| `P1` | Chất lượng thực tế & license của **3 Presenter style presets**, motion templates, clip QC pass rate và thời gian render (P01/P02) | AI / Product | `UNVALIDATED` |
| `P1` | **Telemetry & Metric Dictionary:** Định nghĩa biên `live_duration_seconds`, độ tin cậy đo `concurrent_viewers`, export worker CSV/PDF & signed URL expiry (`RPT-O1`–`RPT-O6`) | Analytics / Backend | `UNVALIDATED` |
| `P1` | Phương thức sinh **QR Code** (client-side từ HTTPS URL hay server-side) và chính sách upload/storage/mime limits cho tài liệu | Backend / Frontend | `UNVALIDATED` |
