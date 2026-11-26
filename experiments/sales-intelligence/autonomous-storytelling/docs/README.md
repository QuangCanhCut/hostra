# Thư mục Tài liệu Báo cáo & Onboarding P06 (`docs/`)

**Module:** `P06 — Sales Intelligence & Autonomous Storytelling`  
**Trạng thái:** `IN RESEARCH` (Phase 1 `E01-T01..T02` hoàn tất · `E01-T03..T09` & `P06-E01..E04`: `NOT STARTED`)  
**Cập nhật lần cuối:** `2026-11-26`

---

## 1. Mục đích của `autonomous-storytelling/docs/`

Thư mục `docs/` lưu trữ **báo cáo triển khai theo từng phiên làm việc (session/implementation reports)** và **tài liệu hướng dẫn cấu trúc/onboarding** dành riêng cho thành viên mới, Tech Lead, Reviewer và AI Coding Agents khi tiếp quản module `P06`.

Để tránh trùng lặp hoặc lẫn lộn nguồn chân lý, cần phân biệt rạch ròi 3 thư mục tài liệu bên trong `autonomous-storytelling/`:

| Thư mục | Vai trò chính | Thuộc về đây | **KHÔNG** thuộc về đây |
| :--- | :--- | :--- | :--- |
| **`docs/`** | Báo cáo tiến độ/bối cảnh theo từng đợt làm việc, hướng dẫn onboarding, giải thích kiến trúc thư mục và code flow | `00-context-and-scaffolding-report.md`, `01-p06-structure-and-mission-guide.md`, các báo cáo triển khai Phase 1–5 (`02-...`) | Câu hỏi nghiên cứu gốc, bảng metrics thô chưa kiểm chứng, notebook hoặc mã Python |
| **`research/`** | Tài liệu khoa học & thiết kế nghiên cứu cốt lõi của P06 | `problem_definition.md`, `research_questions.md`, `methodology.md`, `literature_review.md`, `context_and_dependencies.md`, `decision_log.md` | Nhật ký scaffolding từng phiên hoặc hướng dẫn đọc file cho người mới |
| **`reports/`** | Kết quả thực nghiệm định lượng/định tính từ `P06-E01`..`P06-E04` và kết luận `GO/CHANGE/NO-GO/INCONCLUSIVE` | `tables/`, `figures/`, `final_report.md` (tạo ở Phase 4–5 khi có evidence chạy thực tế) | Báo cáo khám phá bối cảnh trước khi chạy thí nghiệm |

> **Lưu ý phân cấp repo:** Tài liệu chuẩn cấp hệ thống toàn dự án HOSTRA AI nằm ở [`../../../../docs/`](../../../../docs/README.md) (`docs/01-solution-architecture/`, `docs/02-risk-assessment/`, `docs/03-technical-research/`, `docs/product/frontend/`). Thư mục `autonomous-storytelling/docs/` chỉ phục vụ nội bộ track nghiên cứu PoC của P06.

---

## 2. Quy ước đặt tên & Phiên bản hóa

Các tài liệu trong `docs/` tuân theo quy ước đánh số tăng dần theo trình tự phiên/giai đoạn (`NN-kebab-case-title.md`):

- `00-...`: Báo cáo khám phá bối cảnh, rà soát hợp đồng và khởi tạo khung (`00-context-and-scaffolding-report.md`).
- `01-...`: Tài liệu hướng dẫn cấu trúc thư mục, nhiệm vụ và luồng mã nguồn cho người mới (`01-p06-structure-and-mission-guide.md`).
- `02-...`: Báo cáo đồng bộ định hướng `P06-OPEN-1..6`, kiến trúc 3 tầng LLM và kế hoạch triển khai `P06-E01` (`02-open-decisions-alignment-and-e01-plan.md`).
- `03-...`, `04-...` *(dự kiến cho các phiên kế tiếp)*: Báo cáo triển khai theo từng giai đoạn hoặc từng thí nghiệm, ví dụ:
  - `03-p06-e01-implementation-report.md`
  - `04-p06-e04-safety-hardening-report.md`
  - `05-p06-e03-interrupt-resume-report.md`
  - `06-p06-e02-repeated-questions-report.md`

**Quy tắc cập nhật:** Khi sửa cấu trúc thư mục, thêm thí nghiệm hoặc hoàn tất một pha triển khai, phải cập nhật bảng mục lục bên dưới trong cùng đợt thay đổi và giữ nguyên nhãn trạng thái chuẩn (`CONFIRMED REQUIREMENT`, `SELECTED FOR PoC`, `PROPOSED`, `TO VALIDATE`, `VALIDATED`, `DEFERRED`, `NOT STARTED`, `IN RESEARCH`).

---

## 3. Mục lục tài liệu (`docs/`)

| Tài liệu | Tiêu đề & Nội dung | Trạng thái | Ngày | Đối tượng đọc |
| :--- | :--- | :---: | :---: | :--- |
| [00-context-and-scaffolding-report.md](./00-context-and-scaffolding-report.md) | **Báo cáo Bối cảnh, Rà soát Hợp đồng & Khởi tạo Khung P06 (Session 01):** Tổng hợp kiểm kê tài liệu trên `030682c` & `research/p07-comment-understanding`, 7 sai lệch hợp đồng, `P06-OPEN-1..6`, cấu trúc scaffold và kế hoạch `P06-E01` (`E01-T01..T08`) | `IN RESEARCH` *(Scaffolding xong; `E01..E04`: `NOT STARTED`)* | `2026-11-26` | Tech Lead, Reviewer, Coding Agents |
| [01-p06-structure-and-mission-guide.md](./01-p06-structure-and-mission-guide.md) | **Hướng dẫn Nhiệm vụ P06 & Cấu trúc Thư mục cho Thành viên Mới:** Giải thích bài toán kinh doanh/kỹ thuật, 3 trạng thái `Generated ≠ Verified ≠ Played`, kiến trúc 3 tầng provider, memory 4 thành phần, `p06-mock-v0.1`, rubric và lộ trình đọc 5 phút | `IN RESEARCH` *(Tài liệu hướng dẫn hiện hành)* | `2026-11-26` | Thành viên mới, Product Owner, Dev/AI Engineers |
| [02-open-decisions-alignment-and-e01-plan.md](./02-open-decisions-alignment-and-e01-plan.md) | **Báo cáo Session 02 — Đồng bộ `P06-OPEN-1..6`, Kiến trúc 3 Tầng LLM & Kế hoạch `P06-E01`:** Phân tách `SELECTED FOR PoC` vs `RESEARCH VARIABLE` vs `TO VALIDATE`, cơ chế Antigravity `.agents/rules/p06-autonomous-storytelling.md`, contract `p06-mock-v0.1` và kế hoạch chi tiết `E01-T01..T09` | `IN RESEARCH` *(Kế hoạch E01 hiện hành; `E01-T03..T09` & Runs: `NOT STARTED`)* | `2026-11-26` | Tech Lead, Reviewer, Coding Agents |
| [03-phase1-foundation-e01-t01-t02-report.md](./03-phase1-foundation-e01-t01-t02-report.md) | **Báo cáo Phase 1 — Thiết lập Môi trường (`E01-T01`) & Core Pydantic Schemas `p06-mock-v0.1` (`E01-T02`):** Xác minh `.venv` Python `3.13.2`, hoàn thiện `src/p06/schemas/` (`story.py`, `candidate.py`, `events.py`, `state.py`, `__init__.py`) và `28/28` pytest tests pass | `IN RESEARCH` *(Phase 1 `E01-T01..T02` hoàn tất; `E01-T03..T09`: `NOT STARTED`)* | `2026-11-26` | Tech Lead, Reviewer, Coding Agents |
