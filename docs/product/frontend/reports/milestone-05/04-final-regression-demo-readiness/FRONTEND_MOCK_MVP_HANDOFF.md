# HOSTRA AI — Tài liệu Bàn giao Frontend Mock MVP (Handoff Package)

**Trạng thái:** `FRONTEND MOCK MVP BASELINE READY`  
**Mục đích:** Chốt ranh giới rõ ràng giữa phần Frontend Mock MVP đã hoàn thiện sau M05.4 và các phụ thuộc Backend / AI / Media cần giải quyết trong Stage 03 (Technical Research & PoC Validation) và giai đoạn tích hợp API sau này.

---

## 1. Ma trận trạng thái theo phân lớp hệ thống

| Phân lớp | Đã xây dựng & Kiểm chứng (Frontend Mock MVP) | Đang mô phỏng (MSW / In-memory Store) | Chưa tích hợp (Ngoài phạm vi M05.4) |
| :--- | :--- | :--- | :--- |
| **Authentication & Workspace** | Màn hình Sign-in, Onboarding lưu nháp, Account Dropdown Menu (`PO-D01`), RBAC guards theo capabilities (`Owner` vs `Operator`) | Chuyển vai trò mock, lưu nháp onboarding trong store | Managed OIDC provider thật, HTTP-only session cookie, CSRF/refresh token |
| **AI Presenter & Rights** | Thư viện Presenter, Wizard 4 bước, so sánh A/B khi ≥2 ứng viên, Cổng xác nhận quyền độc lập (`Rights Subject Portal`), khóa tài sản khi thu hồi | Sinh gói clip chuyển động nền, kết quả QC, xác nhận/thu hồi quyền | AI Avatar/Voice pipeline (P01/P02), định danh & lưu trữ bằng chứng đồng thuận P11 |
| **Products & OCOP** | Danh mục sản phẩm (bảng desktop + thẻ mobile), Wizard 4 bước, trang chi tiết 4 tab, nộp hồ sơ OCOP | Trạng thái xác minh OCOP độc lập (`PENDING_REVIEW`, `VERIFIED`, `REJECTED`, `REVOKED`) | Cổng đối chiếu hồ sơ OCOP / Reviewer backend thật (P09) |
| **Knowledge & Claims** | Thư viện tri thức theo SKU, đối chiếu 2 cột (cột nguồn sticky), duyệt theo nhóm & Owner duyệt gói, bảo vệ claim y tế không bằng chứng | Trích xuất tài liệu (Docling draft), phiên bản hóa gói tri thức | Pipeline trích xuất tài liệu P05, kiểm chứng ngữ nghĩa & Publication Gate thật |
| **Story Planner & Session Setup** | Tạo phiên 2–5 SKU (chống trùng), dòng thời gian Story Arcs, trợ lý biên tập AI có xem trước Diff Before/After, bảng Readiness 7 cổng | Gợi ý biên tập AI, tính toán cổng Readiness | Orchestrator P06/P08, lưu trữ revision có khóa đồng thời trên DB thật |
| **Live Control Room** | Bố cục 2 cột, tách độc lập `Session Lifecycle` / `AI Execution` / `Media Health`, `PAUSE_AI` giữ `LIVE`, hàng đợi bình luận, ngăn kéo Chẩn đoán, Dừng khẩn cấp (confirm + focus trap) | Vòng đời lệnh (`REQUESTED → ACCEPTED → APPLIED/REJECTED`), xung đột 2 Operator (`409`), mất kết nối & đồng bộ lại | FastAPI REST/WebSocket thật, single speech/playout authority P04, LiveKit Publisher |
| **Invites & Viewer Live Room** | Tạo nhiều link mời đặt tên bất biến, sinh & tải QR (hỗ trợ `VITE_PUBLIC_APP_URL`), thu hồi link; Viewer Room mobile-first tách hoàn toàn khỏi AppShell, nhập nickname & bình luận | Cấp lượt vào phòng idempotent, ngắt viewer khi thu hồi, tiếp nhận bình luận | LiveKit subscribe-only guest token & thu hồi token tức thì (`IM-D4`), Comment Intake API thật |
| **Session Reports & Export** | Lịch sử phiên theo quyền, 5 thẻ KPI có nguồn đo tiếng Việt thân thiện, biểu đồ lượt vào phòng, dòng thời gian trạng thái, `N/A` trung thực, xuất CSV (chống Formula Injection) & PDF 1.4 (Owner-only) | Tổng hợp chỉ số, khử trùng lặp `PlaybackCompleted ACK`, job xuất tệp bất đồng bộ | Telemetry đo `concurrent_viewers` thật, worker xuất báo cáo phía server, lưu trữ audit log |

---

## 2. Kiến trúc Frontend bàn giao (`apps/web/`)

- **Stack đã xác minh:** React 19 + TypeScript + Vite 6 + React Router + TanStack Query + Tailwind CSS + Lucide Icons + MSW + Vitest + Playwright.
- **Design System:** Chuẩn hóa theo **HOSTRA UI Redesign v0.4** (Light Mode + Dark Mode qua CSS variables trong `src/styles/tokens.css`, font `Be Vietnam Pro` / `Inter`, bảng màu Navy `#0F172A` & Amber `#F5C430`).
- **Tách biệt tầng dữ liệu:** Toàn bộ cuộc gọi API đi qua `src/services/api-client.ts` và các hooks TanStack Query theo từng feature (`features/*/hooks/`), giúp thay thế tầng mock (`src/mocks/`) bằng REST/WebSocket thật trong tương lai mà không phải viết lại giao diện.
- **Chất lượng nền tảng bàn giao:**
  - `typecheck`: 0 lỗi · `eslint`: 0 lỗi/cảnh báo · `vitest`: 31/31 PASS · `vite build`: PASS.
  - `22/22` vấn đề UI/UX từ M05.1 đã đóng hoàn toàn (`0` nested interactive elements trên 12 tuyến trang, `0px` tràn ngang trên 7 viewport từ `320px` đến `1920px`).

---

## 3. Danh mục phụ thuộc Backend / AI / Media cần xử lý ở giai đoạn tiếp theo

Tham chiếu đầy đủ chi tiết hợp đồng còn thiếu tại [API_CONTRACT_GAPS.md](../../milestone-04/API_CONTRACT_GAPS.md) và [INTEGRATION_READINESS_MATRIX.md](../../milestone-04/INTEGRATION_READINESS_MATRIX.md). Các đầu mục ưu tiên hàng đầu:

1. **P0 — Hợp đồng REST & WebSocket chính thức:** Chốt schema endpoint, mã trạng thái chuẩn (`canonical enums`), cơ chế `expected_revision` / `session_epoch` và đồng bộ lại snapshot sau mất kết nối.
2. **P0 — Managed OIDC & Phân quyền máy chủ:** Chốt nhà cung cấp OIDC, luồng callback bảo mật và kiểm tra quyền tuyệt đối ở backend (không tin cậy state từ client).
3. **P0 — LiveKit Media & Thu hồi quyền khách xem:** Xác thực luồng `subscribe-only` cho Viewer và cơ chế ngắt kết nối ngay lập tức khi Owner thu hồi lời mời.
4. **P0 — Single Playout Authority & PlaybackCompleted ACK (P04):** Đảm bảo chỉ tính câu AI đã phát xong sau khi nhận ACK từ bộ phát thực tế, không dùng sự kiện hoàn tất TTS.
5. **P0 — Xác minh độc lập OCOP (P09) & Quyền hình ảnh (P11):** Xây dựng luồng lưu trữ bằng chứng và quy trình thẩm định tách biệt khỏi tài khoản merchant.
6. **P1 — Thực thi Human Usability Testing:** Triển khai kiểm thử thực địa với 5–8 người dùng mục tiêu theo [HUMAN_USABILITY_TEST_PLAN.md](./HUMAN_USABILITY_TEST_PLAN.md) song song hoặc trước khi tích hợp pilot.
