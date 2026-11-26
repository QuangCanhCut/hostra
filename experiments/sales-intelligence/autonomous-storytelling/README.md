# Kể chuyện bán hàng chủ động

[Nhóm nghiên cứu](../README.md) · [Trung tâm experiments](../../README.md)

**Module:** P06 · **Rủi ro:** R05, R08, R13 · **Gate:** G2, G4, G6 · **Mốc tham chiếu:** M4.

**Tiến độ khởi tạo:** NOT STARTED — chưa có evidence chạy thí nghiệm trong thư mục tại lần kiểm kê này. **Quyết định công nghệ:** SELECTED FOR PoC; tính khả thi và các kết quả vẫn TO VALIDATE. Owner/reviewer cần nhóm phân công.

## 1. Tổng quan bài toán

Không có bình luận, HOSTRA vẫn cần dẫn dắt nội dung về sản phẩm; có câu hỏi thì trả lời và quay lại mạch nói chưa hoàn tất. Bài toán là tạo lời tự nhiên trong kế hoạch đã duyệt, tránh lặp ý và bịa thông tin. P06 không sở hữu lịch phát.

## 2. Định nghĩa bài toán

- **Đầu vào:** StoryPlan, mục tiêu/ràng buộc merchant, EvidenceBundle từ P05, lịch sử PlaybackCompleted và CommentTask đã được chọn.
- **Đầu ra:** StoryChunk/candidate có intent, tham chiếu SKU, breakpoint và lý do; chỉ trở thành VerifiedSpeechCandidate sau kiểm chứng P05.
- **Yêu cầu chức năng, chất lượng và giới hạn:** Lập kế hoạch có cấu trúc, theo dõi coverage từ lời đã phát, sinh từng chunk, rewrite có giới hạn và resume. Không tự đổi Active SKU, scene hoặc đánh dấu đã nói từ checkpoint LangGraph.
- **Phụ thuộc:** P05 cung cấp và kiểm chứng facts; P07/P08 cung cấp câu hỏi đã chọn và lịch sử phát; P02 tổng hợp lời hợp lệ; P10 merchant duyệt kế hoạch.

## 3. Câu hỏi nghiên cứu

- Sau 10–30 phút không bình luận, nội dung có bao phủ các chủ đề bắt buộc và tránh lặp ý không?
- Khi câu hỏi xen ngang ở các đoạn khác nhau, resume có bỏ sót hoặc lặp phần đã phát không?
- Cửa sổ played-history và rewrite budget ảnh hưởng thế nào tới tính tự nhiên, latency và chi phí?

## 4. Kiến thức nền cần tìm hiểu

- Hierarchical planning: tách story arc khỏi câu nói để theo dõi coverage.
- LangGraph và bounded rewrite: kiểm soát đường sinh/kiểm chứng, không tạo vòng sửa vô hạn.
- Semantic repetition và played history: nội dung đã tạo chưa chắc đã đến người xem.

## 5. Phương pháp và công nghệ

**SELECTED FOR PoC:** Structured Story Planner + Dynamic Verified Generation bằng LangGraph ngay từ PoC đầu; chống lặp theo intent/SKU/lời thực sự đã phát. Baseline script-first ổn định, ít chi phí nhưng kém thích ứng; fully agentic multi-agent là phương án đối chiếu trong tài liệu, không được chọn cho MVP. Embeddings chống lặp và DSPy chỉ là lựa chọn nghiên cứu khi cần, không thay quyết định LangGraph.

## 6. Thí nghiệm cần thực hiện

### Chuẩn bị dữ liệu và môi trường

Chuẩn bị 3 SKU, facts có nguồn, mandatory topics và 10 tình huống ngắt/tiếp tục. Dùng fake playback ACK trong notebook để kiểm soát lịch sử; ghi rõ đây là mô phỏng. LLM provider chưa chốt: cố định model/config cho mỗi lượt so sánh, ghi token, thời gian và quyền gửi dữ liệu.

Mỗi lượt chạy dùng manifest theo [quy tắc tái lập](../../README.md#5-tái-lập-thí-nghiệm). Các giả thuyết dưới đây là cách diễn đạt để kiểm chứng quyết định Stage 03, **không phải kết quả đã đạt**. Chốt baseline, số lượt lặp và tiêu chí trước khi chạy; báo cả lượt lỗi. Mã Pxx-Eyy giữ theo tài liệu nguồn.

### P06-E01 — Kể chuyện không bình luận

- **Mục tiêu và giả thuyết:** Story Plan giúp duy trì nội dung có coverage mà không lặp vô ích.
- **Đầu vào/tình huống và cách làm:** Chạy 3 SKU trong 10–30 phút không comment; đánh dấu chủ đề đã phát bằng ACK mô phỏng.
- **Đầu ra, metrics và evidence:** Coverage, lặp từ/ngữ nghĩa và mạch kể; lưu plan, transcript và phiếu chấm.

### P06-E02 — Câu hỏi lặp

- **Mục tiêu và giả thuyết:** History theo viewer/intent giúp trả lời đúng mà tránh lặp không cần thiết.
- **Đầu vào/tình huống và cách làm:** Đưa 10–20 paraphrase hỏi giá/ship, gồm người xem hỏi lại.
- **Đầu ra, metrics và evidence:** Đúng facts và mức lặp; lưu mapping câu hỏi–history–câu đáp.

### P06-E03 — Ngắt rồi tiếp tục

- **Mục tiêu và giả thuyết:** Checkpoint dựa trên playback giữ mạch kể đúng.
- **Đầu vào/tình huống và cách làm:** Chèn comment tại 10 vị trí trong arc; tiếp tục từ phần chưa phát.
- **Đầu ra, metrics và evidence:** Độ mạch lạc, 0 lặp chunk đã hoàn tất; lưu ACK và checkpoint.

### P06-E04 — Đổi kế hoạch có giới hạn

- **Mục tiêu và giả thuyết:** Rewrite có thể giữ ràng buộc và dừng khi model lỗi.
- **Đầu vào/tình huống và cách làm:** Thử mandatory topics, tài liệu mâu thuẫn và model timeout.
- **Đầu ra, metrics và evidence:** 0 lệch chủ đề bị cấm, retry có giới hạn, latency; lưu graph trace và lý do kết thúc.

## 7. Đánh giá và tiêu chí chấp nhận

G2/G6 đánh giá mạch kể, coverage và trải nghiệm merchant; rubric tự nhiên và mức lặp chấp nhận còn mở. G4 chặn bịa giá/khuyến mại/OCOP/tồn kho và draft chưa qua P05. LLM lỗi chỉ dùng approved chunk còn hiệu lực; không có nội dung hợp lệ thì safe scene. Graph checkpoint không chứng minh PlaybackCompleted.

Các metric ở mục 6 đo trực tiếp câu hỏi nghiên cứu, phải báo theo từng nhóm đầu vào/cấu hình thay vì chỉ một số trung bình. Phân biệt **ràng buộc đã xác nhận**, **mục tiêu cần benchmark** và **ngưỡng chưa chốt**. Không tự thêm ngưỡng đạt chất lượng hoặc giá. GO chỉ áp dụng cho phạm vi có evidence và reviewer đồng ý; CHANGE khi cần điều chỉnh phương pháp/cấu hình; NO-GO khi vi phạm hard gate. Nếu chưa đủ bằng chứng, ghi INCONCLUSIVE và việc cần làm tiếp. Không dùng điểm chất lượng để bù vi phạm quyền hoặc tính đúng.

## 8. Kết quả cần bàn giao

- Notebook/script nghiên cứu có hướng dẫn chạy lại, cấu hình và dependency versions; đây là đầu ra cần làm sau, chưa được tạo bởi README.
- Manifest, dữ liệu đầu vào có nguồn/quyền và split hoặc kịch bản kiểm thử; log/metrics theo từng mã thí nghiệm ở mục 6.
- Mẫu đầu ra hợp lệ và ví dụ thất bại, rubric/phiếu chấm nếu có đánh giá người thật; asset riêng tư chỉ lưu tham chiếu có kiểm soát.
- Báo cáo so baseline, giới hạn của Kaggle/Colab hoặc mock so với hệ thống thật, lỗi còn mở và khuyến nghị kỹ thuật.
- Kết luận GO/CHANGE/NO-GO hoặc INCONCLUSIVE, phạm vi kết luận, người phụ trách/reviewer và liên kết evidence. Không tạo kết quả giả để điền báo cáo.

## 9. Tích hợp với HOSTRA

P06 trả candidate cho P05/P08; P08 lập lịch, P04 xác nhận phát. Bảo toàn StoryPlan version, StoryCheckpoint, references và played-history khi chuyển sang module sales; không đưa quyền commit vào LangGraph.

### Điểm cần xác minh

LLM provider, structured output tiếng Việt, cửa sổ memory, cách recap cho người xem mới và rubric người chấm cần xác định.

## 10. Tài liệu tham khảo

- [Architecture Baseline v1.2](../../../docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx): §6–7; D08–D11; ARD-02, ARD-05, ARD-06.
- [Technical Research & PoC Plan v1.0](../../../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx): §4, §5 hồ sơ P06, đặc biệt mục .3/.5/.11–.14; §8–9 về benchmark/evidence, §13–14 về gates và quyết định mở.
- [Technical Risk Assessment v1.1](../../../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx): các mục R05, R08, R13; đọc failure scenario và evidence cần thiết.

Các liên kết ngoài sau được lấy từ hồ sơ Stage 03; đây là điểm bắt đầu đọc nguyên lý và cách chạy, chưa phải xác nhận license, giá hay khả năng tương thích ở thời điểm thực nghiệm:

- [Paper ReAct](https://arxiv.org/abs/2210.03629)
- [Paper Self-Refine](https://arxiv.org/abs/2303.17651)
- [Paper Reflexion](https://arxiv.org/abs/2303.11366)
- [Mã nguồn LangGraph](https://github.com/langchain-ai/langgraph)
- [Tài liệu LangGraph](https://docs.langchain.com/oss/python/langgraph/overview)
- [Mã nguồn DSPy](https://github.com/stanfordnlp/dspy)

## 11. Checklist tiến độ nghiên cứu

- [ ] Đọc nguồn và chốt câu hỏi/phạm vi P06, owner và reviewer.
- [ ] Xác minh quyền dữ liệu/model; chuẩn bị bộ test và baseline.
- [ ] Khóa cấu hình, cách đo, rubric và các ngưỡng cần nhóm phê duyệt.
- [ ] Chạy P06-E01, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P06-E02, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P06-E03, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P06-E04, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Kiểm tra hard gates và đối chiếu dependency/contract với nhóm liên quan.
- [ ] Chạy lại được kết quả, review giới hạn và ghi quyết định có bằng chứng.

## 12. Cấu trúc thư mục nghiên cứu & Điều hướng tài liệu

**Trạng thái hiện tại:** `E01-T01..T08: COMPLETED` (`249/249` offline Mock pytest tests pass: Core Schemas, 3-Tier Providers, Datasets/P05/Harness, 4-Part Memory + `ScriptFirstBaseline` + 8-Node LangGraph Core, và **Phase 4 Evaluation Metrics + Reproducible Experiment Runner**); `E01-T09` (Ollama CPU smoke, Gemini formal benchmark, Human Blind Pilot Calibration) và các lượt chạy thực nghiệm live `P06-E01`..`P06-E04` vẫn ở trạng thái `NOT STARTED` (`TO VALIDATE`).

> **Chạy thử ngoại tuyến (`E01-T08`, Mock only):**  
> `python experiments/p06_e01_no_comments/run_e01.py --provider mock --sweep --scenario product_education_10m --export-human-eval`

- **Quy tắc chung repository:** [AGENTS.md](../../../AGENTS.md) · **Quy tắc module P06:** [P06 AGENTS.md](AGENTS.md)
- **Tài liệu báo cáo & Hướng dẫn dự án (`docs/`):**
  - [Mục lục tài liệu P06](docs/README.md) (`docs/README.md`)
  - [Báo cáo bối cảnh & khởi tạo khung (Session 01)](docs/00-context-and-scaffolding-report.md) (`00-context-and-scaffolding-report.md`)
  - [Hướng dẫn nhiệm vụ & cấu trúc thư mục P06](docs/01-p06-structure-and-mission-guide.md) (`01-p06-structure-and-mission-guide.md`)
  - [Đồng bộ `P06-OPEN-1..6`, Kiến trúc 3 tầng LLM & Kế hoạch `P06-E01` (Session 02)](docs/02-open-decisions-alignment-and-e01-plan.md) (`02-open-decisions-alignment-and-e01-plan.md`)
  - [Báo cáo Phase 1 — Môi trường (`E01-T01`) & Core Schemas `p06-mock-v0.1` (`E01-T02`)](docs/03-phase1-foundation-e01-t01-t02-report.md) (`03-phase1-foundation-e01-t01-t02-report.md`)
  - [Báo cáo Kiểm toán Phase 1 & Hạ tầng Phase 2 (`E01-T03..E01-T05`)](docs/04-phase2-research-infrastructure-e01-t03-t05-report.md) (`04-phase2-research-infrastructure-e01-t03-t05-report.md`)
  - [Báo cáo Phase 3 — AI Agent Core, Memory System & 8-Node LangGraph (`E01-T06..E01-T07`)](docs/05-phase3-agent-core-e01-t06-t07-report.md) (`05-phase3-agent-core-e01-t06-t07-report.md`)
  - [Báo cáo Phase 4 — Hệ thống Đánh giá & Experiment Runner (`E01-T08`)](docs/06-phase4-evaluation-runner-e01-t08-report.md) (`06-phase4-evaluation-runner-e01-t08-report.md`)
- **Tài liệu nghiên cứu (`research/`):**
  - [Định nghĩa bài toán](research/problem_definition.md) (`problem_definition.md`)
  - [Câu hỏi nghiên cứu](research/research_questions.md) (`research_questions.md`)
  - [Phương pháp luận](research/methodology.md) (`methodology.md`)
  - [Ngữ cảnh & Phụ thuộc](research/context_and_dependencies.md) (`context_and_dependencies.md`)
  - [Nhật ký quyết định](research/decision_log.md) (`decision_log.md`)
  - [Tổng quan tài liệu](research/literature_review.md) (`literature_review.md`)
- **Cấu hình (`configs/`):** [configs/default.yaml](configs/default.yaml) · [configs/experiments/p06_e01.yaml](configs/experiments/p06_e01.yaml) · [configs/models/](configs/models/) (`mock.yaml`, `ollama_qwen3_1.7b.yaml`, `ollama_qwen3_4b.yaml`, `gemini_flash.yaml`)
- **Dữ liệu, Prompt & Notebook:** [data/README.md](data/README.md) · [prompts/README.md](prompts/README.md) · [notebooks/README.md](notebooks/README.md)
- **Kịch bản thí nghiệm & Đánh giá:** [experiments/p06_e01_no_comments/README.md](experiments/p06_e01_no_comments/README.md) · [evaluation/README.md](evaluation/README.md) · [evaluation/rubrics/human_eval_rubric_v0.1.md](evaluation/rubrics/human_eval_rubric_v0.1.md)
- **Nhật ký chạy & Báo cáo:** [runs/README.md](runs/README.md) · [reports/README.md](reports/README.md)
