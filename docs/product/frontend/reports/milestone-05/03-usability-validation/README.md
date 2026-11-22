# HOSTRA AI — Milestone 05.3: Kiểm thử Khả năng Sử dụng & Xác minh Hành trình Người dùng

- **Ngày thực hiện:** 22/11/2026
- **Nhánh Git tham chiếu:** `feat/frontend-foundation`
- **Phạm vi:** Kiểm chứng thực tế khả năng sử dụng của Frontend Mock MVP sau M05.2 trên 11 hành trình người dùng (`J01`–`J11`), 7 kích thước màn hình (`320×568` đến `1920×1080`), Light/Dark Mode, Keyboard/Focus Trap, Sticky Bar reachability và đối chiếu đóng toàn bộ 22 issues M05.1.
- **Lưu ý ranh giới Mock:** Mọi kết quả dưới đây được xác minh bằng **Playwright + Chromium + Vitest trên MSW Mock Store**, **chưa phải** xác minh Backend thật, LiveKit WebRTC thật, Managed OIDC thật hay dữ liệu người dùng thật.

---

## Cách chạy lại toàn bộ bộ kiểm thử

```powershell
cd apps/web
npm run typecheck
npm run lint
npm run test
npm run build
npx playwright test tests/e2e/m05-user-journeys.spec.ts
```

---

## Danh mục 8 báo cáo & minh chứng M05.3

| # | Tệp báo cáo | Nội dung |
| :-: | :--- | :--- |
| 1 | [M05_3_USABILITY_REPORT.md](./M05_3_USABILITY_REPORT.md) | Đánh giá usability theo 8 tiêu chí heuristic, trả lời 6 câu hỏi Q1–Q6 và các điểm cần PO duyệt |
| 2 | [USER_JOURNEY_TEST_MATRIX.md](./USER_JOURNEY_TEST_MATRIX.md) | Ma trận kiểm thử chi tiết 11 hành trình (`J01`–`J11`) kèm tiền điều kiện, thực tế và ảnh minh chứng |
| 3 | [ACCESSIBILITY_RESPONSIVE_REPORT.md](./ACCESSIBILITY_RESPONSIVE_REPORT.md) | Ma trận 7 viewports, Focus Trap, Focus Restoration, Sticky Bar, Reduced Motion & giới hạn chưa test |
| 4 | [M05_1_ISSUE_CLOSURE.md](./M05_1_ISSUE_CLOSURE.md) | Bảng đối chiếu trạng thái đóng của toàn bộ 22 issues `UX-01` → `UX-22` |
| 5 | [HUMAN_USABILITY_TEST_PLAN.md](./HUMAN_USABILITY_TEST_PLAN.md) | Kế hoạch thử nghiệm với 5–8 người dùng thật (chưa thực thi, không bịa dữ liệu giả) |
| 6 | [M05_3_FIX_LOG.md](./M05_3_FIX_LOG.md) | Nhật ký các chỉnh sửa nhỏ được phép trong M05.3 & kết quả hồi quy |
| 7 | [M05_3_EXIT_GATE.md](./M05_3_EXIT_GATE.md) | Kết luận cổng nghiệm thu M05.3 (`CONDITIONAL GO TO M05.4`) dựa trên bằng chứng |
| 8 | [`screenshots/`](./screenshots/) | 12 ảnh chụp các trạng thái tương tác thực tế (`J01`–`J11`) |
