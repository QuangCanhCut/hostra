# HOSTRA AI — Milestone 05.4: Final Regression, UX Issue Closure & Frontend Demo Readiness

**Trạng thái:** `PASS — FRONTEND MOCK MVP BASELINE READY`  
**Ngày hoàn tất:** 22/11/2026  
**Phạm vi xác nhận:** Frontend Mock MVP (`apps/web/`) sẵn sàng làm nền tảng demo nội bộ và bàn giao trước giai đoạn Stage 03 Technical Research & PoC Validation.  
**Lưu ý ranh giới:** M05.4 **KHÔNG** tuyên bố Backend Integration Ready, Production Ready hay Pilot Ready.

---

## Mục lục hồ sơ M05.4

| # | Tài liệu | Mục đích |
| :---: | :--- | :--- |
| 1 | [M05_4_IMPLEMENTATION_REPORT.md](./M05_4_IMPLEMENTATION_REPORT.md) | Tổng hợp các thay đổi mã nguồn thực thi 4 quyết định PO (`PO-D01`–`PO-D04`), đóng 4 vấn đề UX còn lại và gia cố cấu hình URL mời/QR. |
| 2 | [FINAL_ISSUE_CLOSURE.md](./FINAL_ISSUE_CLOSURE.md) | Bảng đóng toàn bộ 22 vấn đề `UX-01` → `UX-22` từ M05.1, khôi phục đúng mức độ nghiêm trọng gốc (`P1/P2/P3`) và sửa điểm chưa nhất quán của M05.3. |
| 3 | [FINAL_REGRESSION_REPORT.md](./FINAL_REGRESSION_REPORT.md) | Kết quả kiểm thử hồi quy toàn diện (`typecheck`, `lint`, `vitest 31/31`, `vite build`, Chromium 12 tuyến trang, 7 viewport `320px–1920px`, Light/Dark, Zoom 200%, Reduced Motion). |
| 4 | [FRONTEND_DEMO_RUNBOOK.md](./FRONTEND_DEMO_RUNBOOK.md) | Kịch bản demo nội bộ (Scenarios A–D), cấu hình mạng LAN/QR (`VITE_PUBLIC_APP_URL`), hướng dẫn đặt lại trạng thái & xử lý sự cố khi trình diễn. |
| 5 | [FRONTEND_MOCK_MVP_HANDOFF.md](./FRONTEND_MOCK_MVP_HANDOFF.md) | Tài liệu bàn giao ranh giới Frontend Mock MVP: đã xây dựng, đang mô phỏng, chưa tích hợp và danh mục phụ thuộc Backend/AI/Media. |
| 6 | [HUMAN_USABILITY_TEST_PLAN.md](./HUMAN_USABILITY_TEST_PLAN.md) | Kế hoạch kiểm thử khả năng sử dụng với người dùng thật (`PLAN READY`, thực địa `PENDING HUMAN TEST`, không bịa dữ liệu người dùng). |
| 7 | [M05_4_EXIT_GATE.md](./M05_4_EXIT_GATE.md) | Thẩm định cổng nghiệm thu cuối cùng của Frontend Mock MVP Baseline Candidate. |

---

## Bằng chứng kiểm thử & Ảnh chụp M05.4

- **Bằng chứng kiểm thử tự động (JSON):** [tests/evidence/m05_4_regression_evidence.json](./tests/evidence/m05_4_regression_evidence.json)
- **Bộ ảnh chụp sau M05.4 (`screenshots/`):**
  - [01-account-menu-open.png](./screenshots/01-account-menu-open.png) — Account Dropdown Menu (`PO-D01`) đang mở từ Avatar góc trên bên phải
  - [02-dashboard-light-m054.png](./screenshots/02-dashboard-light-m054.png) — Dashboard Light Mode sau tinh gọn badge (`PO-D03` / `UX-13`) & loại bỏ nested interactive (`UX-04`)
  - [03-dashboard-dark-m054.png](./screenshots/03-dashboard-dark-m054.png) — Dashboard Dark Mode sau tinh gọn badge
  - [04-report-friendly-m054.png](./screenshots/04-report-friendly-m054.png) — Báo cáo phiên với nguồn đo tiếng Việt thân thiện (`PO-D02` / `UX-06`)
  - [05-readiness-friendly-m054.png](./screenshots/05-readiness-friendly-m054.png) — Kiểm tra sẵn sàng phiên với nguồn xác minh tiếng Việt thân thiện (`PO-D02` / `UX-06`)
  - [06-control-room-m054.png](./screenshots/06-control-room-m054.png) — Phòng điều khiển livestream với thanh điều khiển ghim đáy ổn định
  - [07-viewer-mobile-m054.png](./screenshots/07-viewer-mobile-m054.png) — Phòng xem khách di động (`375×812`) gửi bình luận & tách biệt quyền merchant
  - [08-invites-qr-m054.png](./screenshots/08-invites-qr-m054.png) — Quản lý lời mời & mã QR đồng bộ URL
