# Thư mục Tài liệu Báo cáo & Onboarding P06 (`docs/`)

**Module:** `P06 — Sales Intelligence & Autonomous Storytelling`  
**Trạng thái:** `IN RESEARCH` (`E01-T01..T08 COMPLETED; E01-T09 Pilot v1 COMPLETED & Offline Remediation COMPLETED (v0.2, 279/279 tests pass) — AWAITING_PILOT_V2_EXECUTION_APPROVAL | Ollama DEFERRED WITH USER APPROVAL`)  
**Cập nhật lần cuối:** `2026-11-27`

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
| [03-phase1-foundation-e01-t01-t02-report.md](./03-phase1-foundation-e01-t01-t02-report.md) | **Báo cáo Phase 1 — Thiết lập Môi trường (`E01-T01`) & Core Pydantic Schemas `p06-mock-v0.1` (`E01-T02`):** Xác minh `.venv` Python `3.13.2`, hoàn thiện `src/p06/schemas/` (`story.py`, `candidate.py`, `events.py`, `state.py`, `__init__.py`) và `28/28` pytest tests pass *(đã bổ sung Audit Addendum Phase 2)* | `IN RESEARCH` *(Phase 1 `E01-T01..T02` hoàn tất + Audit; `E01-T06..T09`: `NOT STARTED`)* | `2026-11-26` | Tech Lead, Reviewer, Coding Agents |
| [04-phase2-research-infrastructure-e01-t03-t05-report.md](./04-phase2-research-infrastructure-e01-t03-t05-report.md) | **Báo cáo Kiểm toán Phase 1 & Hạ tầng Nghiên cứu Phase 2 (`E01-T03..E01-T05`):** Tổng hợp kiểm toán Phase 1 (`2 BLOCKER`, `3 MAJOR`, `3 MINOR` -> `33` tests), 3-tier `LLMProvider` (`E01-T03`), dataset synthetic 3 SKU `OCOP: VERIFIED` mô phỏng + 4 negative fixtures (`E01-T04`), `P05KnowledgeAdapter` 4 chế độ + guardrails + `SimulatedPlaybackHarness` 5 lớp (`E01-T05`), Wave D review (`5 MINOR` resolved), `92/92` tests pass *(đã qua Audit Gate Phase 2 -> `106/106`)* | `IN RESEARCH` *(`E01-T01..T05 COMPLETED`; Audit Gate `106/106` pass)* | `2026-11-26` | Tech Lead, Reviewer, Coding Agents |
| [05-phase3-agent-core-e01-t06-t07-report.md](./05-phase3-agent-core-e01-t06-t07-report.md) | **Báo cáo Phase 3 — AI Agent Core, 4-Part Memory, `ScriptFirstBaseline` & LangGraph 8 Node (`E01-T06..E01-T07`):** Audit Gate Phase 2 (`1 BLOCKER`, `11 MAJOR`, `6 MINOR` resolved), hệ thống bộ nhớ 4 thành phần + `RepetitionDetector` rule-based, `ScriptFirstBaseline`, `StoryPlanner` + prompt versioned SHA-256 LF, đồ thị LangGraph 8 node với `1 + K` bounded rewrite và 17 kịch bản smoke test tích hợp (`189/189` tests pass offline) | `IN RESEARCH` *(`E01-T06..T07 COMPLETED` với Mock)* | `2026-11-26` | Tech Lead, Reviewer, Coding Agents |
| [06-phase4-evaluation-runner-e01-t08-report.md](./06-phase4-evaluation-runner-e01-t08-report.md) | **Báo cáo Phase 4 — Hệ thống Đánh giá 5 Trục & Experiment Runner Tái lập (`E01-T08`):** Audit Phase 3 (`F-01..F-12`, `AUD-01..AUD-10` + 5 tests), 5 nhóm metric (`src/p06/evaluation/`), runner & CLI (`src/p06/runner/`, `run_e01.py`), Independent Review & vá `8/8` findings (`BUG-A..C`, `NEW-01..05`), dry-runs hậu-sửa-lỗi (`post_fix_sweep_product_education_10m`) và `249/249` pytest tests pass offline | `IN RESEARCH` *(`E01-T08 COMPLETED` với Mock; `E01-T09` chuẩn bị ở `07-...`)* | `2026-11-26` | Tech Lead, Reviewer, Coding Agents |
| [07-e01-t09-experiment-readiness-and-protocol.md](./07-e01-t09-experiment-readiness-and-protocol.md) | **Báo cáo Sẵn sàng Thực nghiệm & Giao thức `E01-T09` (Phase 5 — Chuẩn bị Ngoại tuyến):** Vá cổng review (`GateStatus` 3 giá trị, `compare_runs()` nghiêm ngặt), mở rộng dữ liệu `e01_ext_v1` + `min_chunks_per_topic`, `OllamaLocalProvider(think=False)` + `GeminiRestClient` + ngân sách `BUDGET_LIMIT_REACHED`, kiểm kê phần cứng/RAM (`1.01 GB` free), `259/259` tests pass, dry-run `offline_ext_v1_dryrun` và Checklist Phê duyệt Thực thi Real Provider | `COMPLETED` *(đã mở khóa Stage A+B)* | `2026-11-26` | Tech Lead, Researcher, Reviewer |
| [08-e01-t09-gemini-smoke-and-pilot-report.md](./08-e01-t09-gemini-smoke-and-pilot-report.md) | **Báo cáo Thực nghiệm `E01-T09` Stage A (Smoke Test) & Stage B (Short Pilot v1) trên Gemini 3.5 Flash-Lite Free Tier:** `25/28` requests (`3` Stage A + `22` Stage B), `0 USD`, `0` HTTP 429, `4` HTTP 503, full transcripts, metrics comparison, phát hiện lỗi `ev-...` leak & nén câu `8s`, `261/261` tests pass, Ollama `DEFERRED WITH USER APPROVAL` | `COMPLETED` *(bằng chứng Pilot v1)* | `2026-11-26` | Tech Lead, Researcher |
| [09-e01-t09-pilot-remediation-and-revalidation-plan.md](./09-e01-t09-pilot-remediation-and-revalidation-plan.md) | **Báo cáo Khắc phục Lỗi Pilot v1 & Kế hoạch Tái kiểm chứng Pilot v2 (`E01-T09` `R01`–`R06`):** Xác minh merge `origin/main` (`54066da`) và phiếu chấm mù thật, guardrails chống rò rỉ ID (`spoken_text_hygiene`) + trích dẫn bằng chứng (`evidence_attribution`) + fallback hoàn chỉnh không lặp + prompt `v0.2`, `279/279` tests pass offline, đề xuất ngân sách Pilot v2 `28` requests | `IN RESEARCH` *(`AWAITING_PILOT_V2_EXECUTION_APPROVAL`)* | `2026-11-27` | Tech Lead, Researcher, Reviewer |
