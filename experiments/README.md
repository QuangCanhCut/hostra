# HOSTRA AI — Trung tâm nghiên cứu và thí nghiệm

Đây là nơi bắt đầu khi được giao một bài toán nghiên cứu cho HOSTRA. Dự án đang ở giai đoạn thiết kế/nghiên cứu; công việc trước mắt là thử phương pháp trong `experiments/`, chạy phần phù hợp trên Kaggle/Colab và lưu kết quả tái lập. Tài liệu này không xác nhận hệ thống đã được triển khai.

**Phạm vi sản phẩm:** một ảnh chân dung có quyền → PhotoMaker + Wan2.2 Animate tạo clip trước live (ACR-001); MVP có 2–5 SKU thực phẩm đóng gói, OCOP được xác minh và đáp ứng điều kiện thực phẩm áp dụng (ACR-002). Private live room, một phiên đồng thời, host-first với product overlay và fallback có kiểm soát. Filmed-host pipeline, Physical Operator và Digital Human Marketplace không phải kiến trúc MVP hiện tại.

## 1. Mục đích và ranh giới

| Hoạt động | Câu hỏi cần trả lời | Đầu ra điển hình |
| --- | --- | --- |
| Research — nghiên cứu | Phương pháp nào có cơ sở để thử cho HOSTRA? | Câu hỏi, tổng hợp nguồn, trade-off và giả thuyết |
| Experiment — thí nghiệm | Giả thuyết có đúng trong điều kiện đã định không? | Một lượt hoặc chuỗi chạy với config, metric, evidence |
| Proof of Concept — PoC | Một phương án có thể thực hiện luồng tối thiểu không? | Mẫu chạy và giới hạn, có thể dùng mock được khai báo |
| Benchmark — đo đối chiếu | Các cấu hình khác nhau thế nào trên cùng workload? | Bảng chất lượng/thời gian/tài nguyên/chi phí |
| Technical Validation — xác thực kỹ thuật | Evidence có đáp ứng tiêu chí đã chốt trong phạm vi đó không? | Báo cáo và sign-off của reviewer |
| Production Implementation — triển khai chính thức | Làm sao đưa lựa chọn đã review vào hệ thống có contracts, vận hành và kiểm thử? | Code trong apps/workers/packages qua PR riêng |

Notebook chạy một lần không tự chứng minh khả năng realtime, quyền thương mại hay production readiness. `experiments/` giữ mã thử và kết quả nhỏ được phép lưu; [docs](../docs/README.md) giữ quyết định/báo cáo được review. [README repository](../README.md) giải thích ranh giới mã nguồn; [AGENTS.md](../AGENTS.md) quy định các bất biến.

## 2. Năm nhóm nghiên cứu

| Nhóm | Mục tiêu và module | Rủi ro chính | Liên hệ |
| --- | --- | --- | --- |
| [AI Presenter & Media](ai-presenter-media/README.md) | P01–P03: tạo người dẫn, giọng Việt, lip-sync | R01/R02 chất lượng, R03 độ trễ, R09 quyền, R11 GPU | Clip/audio cho P04; deadline từ P08; P11 rights |
| [Sales Intelligence](sales-intelligence/README.md) | P05–P07: evidence, kể chuyện, hiểu comment | R04/R05 ngữ cảnh/lặp, R08 claims, R16/R17 eligibility | Candidate cho P08/P02; P09 SKU/OCOP |
| [Conversation Orchestration](conversation-orchestration/README.md) | P08/P09: FSM, lịch nói, session/SKU | R06 correctness, R03/R04 fairness, R08/R10/R16/R17 | P04 ACK; P05/P11 gates; P10 commands |
| [Realtime Media](realtime-media/README.md) | P04: continuous playout, A/V sync, delivery | R06 ACK/replay, R07 continuity, R12 recovery | P01–P03 media, P08 commit, P10 viewer |
| [Infrastructure Evaluation](infrastructure-evaluation/README.md) | P12/P13: tài nguyên, cost, replay, human QA | R11 tài nguyên, R12 recovery, R15 design/code gap; kiểm tra R01–R18 | Đo xuyên module và tổng hợp G1–G6 |

P10 và P11 không có research folder riêng trong cấu trúc này nhưng vẫn cần kiểm thử: P10 onboarding/preview, command states, mobile player/reconnect và quyền viewer; P11 consent, revoke, tenant isolation, storage/provider terms. Mapping thư mục không loại chúng khỏi acceptance.

## 3. Điều hướng nghiên cứu

| Muốn nghiên cứu | Thư mục | Module liên quan | Tài liệu nên đọc |
| --- | --- | --- | --- |
| Tạo người dẫn từ một ảnh chân dung | [presenter-generation](ai-presenter-media/presenter-generation/README.md) | P01 | [Stage 03](../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx) §5 P01; [Stage 02](../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx) R01, R09, R11, R13, R14 |
| Giọng nói tiếng Việt và TTS | [voice-tts](ai-presenter-media/voice-tts/README.md) | P02 | [Stage 03](../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx) §5 P02; [Stage 02](../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx) R02, R03, R09 |
| Lip-sync trên clip người dẫn tổng hợp | [lipsync](ai-presenter-media/lipsync/README.md) | P03 | [Stage 03](../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx) §5 P03; [Stage 02](../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx) R01, R03, R11, R12 |
| Tri thức sản phẩm và kiểm chứng lời thoại | [knowledge-verification](sales-intelligence/knowledge-verification/README.md) | P05 | [Stage 03](../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx) §5 P05; [Stage 02](../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx) R08, R16, R17 |
| Kể chuyện bán hàng chủ động | [autonomous-storytelling](sales-intelligence/autonomous-storytelling/README.md) | P06 | [Stage 03](../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx) §5 P06; [Stage 02](../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx) R05, R08, R13 |
| Hiểu và phân luồng bình luận tiếng Việt | [comment-understanding](sales-intelligence/comment-understanding/README.md) | P07 | [Stage 03](../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx) §5 P07; [Stage 02](../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx) R04, R03, R10 |
| Mô phỏng điều phối hội thoại và trạng thái phiên | [scheduling-simulation](conversation-orchestration/scheduling-simulation/README.md) | P08/P09 | [Stage 03](../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx) §5 P08/P09; [Stage 02](../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx) R03, R04, R06, R08, R10, R12, R14, R15, R16, R17 |
| Benchmark phát media liên tục | [streaming-benchmarks](realtime-media/streaming-benchmarks/README.md) | P04 | [Stage 03](../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx) §5 P04; [Stage 02](../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx) R03, R06, R07, R12 |
| Đánh giá GPU, placement và chi phí | [gpu-benchmarks](infrastructure-evaluation/gpu-benchmarks/README.md) | P12 | [Stage 03](../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx) §5 P12; [Stage 02](../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx) R03, R07, R11, R12, R15 |
| Độ tin cậy, phục hồi và bằng chứng nghiệm thu | [reliability-tests](infrastructure-evaluation/reliability-tests/README.md) | P12/P13 | [Stage 03](../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx) §5 P12/P13; [Stage 02](../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx) R01–R18; trọng tâm R03, R06–R12, R15–R17 |

Mỗi trang con dẫn thêm các mục kiến trúc và papers/repos/docs được trích từ Stage 03. Những liên kết ngoài là nguồn đọc ban đầu, chưa được kiểm chứng lại về giá/license/compatibility hiện tại trong đợt biên soạn này.

**Cách bắt đầu:** chọn một câu hỏi nhỏ trong README con, xác định dữ liệu và quyền, chạy baseline rồi mới mở rộng. P01–P03 và P05–P07 có thể bắt đầu bằng notebook; P08/P09 bằng fake clock trên CPU. Continuous publisher, browser probe, services và endurance cần môi trường tích hợp phù hợp. Kaggle/Colab không mặc định cung cấp GPU hoặc thời gian chạy đủ cho mọi test; ghi giới hạn tài nguyên như một phần kết quả.

## 4. Quy trình nghiên cứu

1. **Định nghĩa bài toán:** chọn P/Risk/Gate, phạm vi và input/output; chỉ định owner/reviewer.
2. **Đọc phương pháp/công nghệ:** đọc mục .4–.7 trong hồ sơ P; kiểm tra nguồn, model revision và quyền trước dùng dữ liệu.
3. **Thiết lập baseline:** chọn phương án đối chiếu đã nêu trong hồ sơ; ghi rõ phương án nào SELECTED FOR PoC, phương án nào chỉ so sánh.
4. **Thiết kế thí nghiệm:** ghi giả thuyết có thể bị bác bỏ, split/scenario, biến giữ cố định, biến thay đổi, số lượt lặp, cách đo và tiêu chí trước khi chạy.
5. **Viết mã thử:** notebook/script tối thiểu trong research folder, khai báo mock và giới hạn; chưa chuyển thành API/worker chính thức.
6. **Chạy benchmark:** dùng cùng đầu vào/workload khi so sánh; lưu cả lỗi, cold/warm, retry và output bị bỏ.
7. **Đánh giá:** đối chiếu hard gate trước, sau đó chất lượng/latency/cost; chấm mù khi cần người thật; không đổi threshold để hợp thức hóa kết quả.
8. **Quyết định kỹ thuật:** GO/CHANGE/NO-GO hoặc INCONCLUSIVE với evidence, giới hạn và việc tiếp theo. Thay đổi lựa chọn kiến trúc cần decision/ADR được review trong nhiệm vụ riêng.

Trước tái sử dụng code cũ phải audit M0: implemented/partial/designed-only dựa trên khả năng chạy thật. Thông tin PoC lịch sử trong tài liệu không chứng minh có code hiện tại. Roadmap M0–M7 là mốc phụ thuộc/evidence, không phải xác nhận đã hoàn thành: M1 media feasibility, M2 continuous playout, M3 FSM, M4 knowledge/sales, M5 Studio/viewer, M6 hardening, M7 acceptance.

## 5. Tái lập thí nghiệm

Mỗi lần chạy có **Experiment ID** theo Stage 03 và **run_id** riêng. Mã experiment giữ ổn định, chạy lại tạo run mới. Tối thiểu cần ghi:

| Nhóm thông tin | Nội dung |
| --- | --- |
| Mục tiêu | Experiment ID, run_id, câu hỏi, giả thuyết, baseline, owner/reviewer, ngày chạy |
| Dữ liệu | Dataset/scenario, nguồn/quyền, số mẫu, split và checksum; phân biệt thật/synthetic |
| Model/môi trường | Model/checkpoint/revision nếu có; OS/runtime/dependency versions, GPU/VRAM/driver/CUDA khi dùng GPU |
| Cấu hình | Parameters, precision/offload/batch/chunk, seed nếu có ngẫu nhiên, workload/concurrency, cold/warm, số lần lặp |
| Mã nguồn | Commit hash chứa mã/config tương ứng; ghi thay đổi chưa commit nếu có, không trình bày như run sạch |
| Đánh giá | Metric, đơn vị, định nghĩa mốc thời gian, threshold đã chốt, rubric, số mẫu/mẫu lỗi |
| Kết quả | Kết quả thực đo, phân bố/P50/P95 khi phù hợp, giới hạn, kết luận và đề xuất tiếp |
| Evidence | URI/đường dẫn và checksum của log/output/phiếu chấm/bill; tham chiếu rights snapshot không nhạy cảm |

Trường không áp dụng ghi **N/A kèm lý do**: test FSM không có model/GPU, deterministic replay không cần seed nếu sequence đã khóa. Không bỏ qua source/scenario hoặc định nghĩa metric vì thí nghiệm nhỏ.

**Kaggle/Colab:** lưu revision notebook và môi trường thực được cấp, khóa dataset/model/config, tách thời gian tải/cài/warmup khỏi inference, lưu manifest/output trước khi phiên kết thúc. Không coi kết quả CPU/mocked service như số đo GPU/real service; không quy đổi quota miễn phí thành chi phí production. Không chia paraphrases cùng nguồn vào cả train và test; báo riêng holdout thật và synthetic.

## 6. Trạng thái tiến độ và mức xác nhận

| Trạng thái tiến độ | Khi nào dùng |
| --- | --- |
| NOT STARTED | Chưa bắt đầu thí nghiệm của phạm vi được giao |
| IN RESEARCH | Đang đọc nguồn, chuẩn bị dữ liệu/baseline và thiết kế thí nghiệm |
| IN EXPERIMENT | Đang chạy thử và thu kết quả |
| IN VALIDATION | Đang chạy acceptance/review evidence theo tiêu chí đã chốt |
| VALIDATED | Phạm vi cụ thể đã đạt tiêu chí với evidence tái lập và reviewer phê duyệt |
| BLOCKED | Không thể tiếp tục một bước vì thiếu quyền/dữ liệu/tài nguyên/dependency; ghi nguyên nhân và điều kiện gỡ |

Đây là tiến độ công việc, khác nhãn quyết định: **CONFIRMED** xác nhận yêu cầu sản phẩm; **SELECTED FOR PoC** xác nhận phương án cần thử; **TO VALIDATE** là giả thuyết hoặc mục tiêu chưa có bằng chứng. Không suy từ requirement CONFIRMED ra performance VALIDATED. Các README mới khởi tạo NOT STARTED theo kiểm kê thư mục; điều đó không phủ nhận việc nhóm đã nghiên cứu/thiết kế trong Stage 01–03.

## 7. Workload và quy tắc nghiệm thu

| Workload | Profile Stage 03 | Cách dùng |
| --- | --- | --- |
| W0 | 1–2 SKU, một viewer thử, ít bình luận | Chức năng/contracts và hard invariants |
| W1 | 3 SKU, 5 viewer, khoảng 2–4 bình luận hợp lệ/phút | Luồng đối thoại và latency chuẩn |
| W2 | 5 SKU, burst khoảng 20–100 bình luận thô/phút | Queue, spam/dedup, fairness và deadline |
| W3 | 120 phút, bình luận hỗn hợp, ít nhất 2 lỗi chủ động | Continuity, recovery và cost |

**Mục tiêu chưa được xác thực:** W1 server comment-to-playout P50≤7 giây/P95≤10 giây; không phải SLA đến tai viewer. Output 720p, 25–30 FPS là target đã được xác nhận, chưa là kết quả đạt. W3 120 phút là phép thử, không chứng minh 24/7.

| Gate | Cần bằng chứng |
| --- | --- |
| G1 | Danh tính/chuyển động/voice/lip-sync và đánh giá media bằng người thật |
| G2 | Kể chuyện khi không comment, trả lời, grouping, breakpoint và resume |
| G3 | State/commit/ACK, không phát trùng/chồng/replay không an toàn, revision/epoch |
| G4 | Claims, quyền hình/giọng/motion, OCOP/food eligibility và tenant isolation |
| G5 | Hiệu năng/độ bền, tài nguyên và chi phí có phép đo |
| G6 | Merchant onboarding, duyệt nội dung, điều khiển và AI disclosure |

Vi phạm hard gate về rights/claims/OCOP/tenant hoặc playout correctness → **NO-GO** cho nghiệm thu liên quan. Chất lượng/hiệu năng chưa đạt khi safety còn nguyên → **CHANGE** và thử lại. Thiếu dữ liệu/evidence → **INCONCLUSIVE**. **GO** cần sign-off đúng phạm vi; không đồng nghĩa production-ready hay TikTok/Shopee đã cho phép tích hợp. Mục tiêu 0 vi phạm chỉ áp dụng bộ test đã định nghĩa, không là đảm bảo tuyệt đối ngoài thực tế.

## 8. Cộng tác, PR và quản lý dữ liệu

- Làm trên branch riêng theo quy ước đề xuất của repo, ví dụ `experiment/p03-lipsync-latency`; giữ thay đổi tập trung vào câu hỏi nghiên cứu.
- Tạo draft PR khi cần review thiết kế thử hoặc contract; PR kết quả cần cách chạy lại, config, dataset/quyền, metrics, evidence, giới hạn, reviewer và đề xuất. Không push trực tiếp vào main để thay review.
- Cập nhật README khi phạm vi, input/output, quyết định, cách chạy, trạng thái hoặc vị trí evidence thay đổi; giữ lịch sử kết quả và ghi version thay vì xóa lượt thất bại.
- Báo cáo theo Experiment ID/run_id; liên kết risk→experiment→gate. Bằng chứng dùng chung có một vị trí chuẩn, các track khác dẫn lại.
- Chỉ đề xuất chuyển sang `workers/` hoặc `apps/` khi có evidence/review, contracts có version, kiểm thử consumer và kế hoạch vận hành phù hợp. Đó là PR triển khai riêng; không copy notebook thành worker rồi gọi là hoàn tất.
- Không commit API keys, private assets, dữ liệu người dùng, checkpoint lớn hoặc tài sản thiếu quyền. Dataset/weights/video/audio lớn lưu ở nơi được phê duyệt, repo chỉ giữ manifest/checksum và chỉ dẫn lấy dữ liệu có kiểm soát.
- Không lưu signed URL còn hiệu lực, token hoặc nội dung bí mật trong notebook output/log. Dùng secret store phù hợp, kiểm tra output trước PR. Asset được phép thử không mặc định được phép công khai.
- Việc lựa chọn model phải kiểm tra riêng license code, weights, dependencies, portrait, voice và motion; quyền dùng ảnh không bao gồm clone giọng. Mọi fallback cũng phải qua kiểm tra quyền/claims/SKU.

Trong nhiệm vụ tạo hướng dẫn này chỉ thêm Markdown trong `experiments/`; chưa tạo notebook, source code, môi trường, dataset hay kết quả chạy và chưa promote implementation.

## 9. Nguồn, điểm chưa đồng bộ và quyết định mở

Đã đối chiếu [README root](../README.md), [AGENTS.md](../AGENTS.md), [mục lục docs](../docs/README.md) và ba nguồn hiện hành:

- [Architecture Baseline v1.2](../docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx): §2–3 phạm vi/D01–D32/ARD/ACR, §4–9 kiến trúc và contracts, §10–12 vận hành/acceptance.
- [Technical Risk Assessment v1.1](../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx): R01–R18, failure scenarios, câu hỏi kiểm chứng và gates.
- [Technical Research & PoC Plan v1.0](../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx): §4 Decision Register, §5 P01–P13, §6 runtime, §7 OCOP, §8–9 benchmark/evidence, §10 rights/license, §11 traceability, §12–14 roadmap/workload/gates/open decisions.

**Thiếu nguồn:** không tìm thấy Project Overview & Proposal v1.0 trong repository khi kiểm kê; không suy đoán nội dung của file thiếu hoặc tạo link tới file không tồn tại. README root/docs có nhắc tài liệu này nhưng không thay thế nguồn gốc.

**Ưu tiên khi đọc:** ACR-001/002 và quyết định mới trong Architecture v1.2/Stage 03 được ưu tiên hơn mô tả cũ về footage/Physical Operator/marketplace. Stage 03 còn nhắc Risk Assessment v1.0 ở một đoạn; hướng dẫn này đối chiếu bản v1.1 hiện có. Một số cách gọi cũ như clone giọng “người trong video” phải đọc cùng P02: cần mẫu audio và consent riêng, không suy giọng từ portrait. Không tự sửa tài liệu nguồn.

**Các việc nhóm cần chốt trước PoC tương ứng:**

- Owner/reviewer, dữ liệu hợp lệ và rubric/ngưỡng chất lượng; chưa có bằng chứng để đóng R01–R18.
- GPU/provider/placement khả dụng, ngân sách thử, quyền đưa dữ liệu lên Kaggle/Colab hoặc API.
- LLM provider; bên thắng PhoBERT/SetFit; nhu cầu embeddings/pgvector, threshold confidence/grouping.
- Commit horizon, deadline/fairness, ACK semantics và quy tắc lệnh đồng thời; mock phải được ghi rõ.
- Nguồn OCOP độc lập, review hồ sơ/food compliance theo SKU; merchant approval hoặc OCR không đủ tạo VERIFIED.
- Consent/revocation, model/weights/motion license, provider terms và AI disclosure; do người phụ trách phù hợp review trước pilot.
- Managed OIDC/storage và thử nghiệm P10/P11 liên quan; TikTok/Shopee là track khả thi riêng, không chặn private-room research ban đầu.

## 10. Checklist bàn giao nghiên cứu

- [ ] Câu hỏi, baseline và tiêu chí được thống nhất trước chạy.
- [ ] Input/dataset có quyền và output contract rõ.
- [ ] Manifest, kết quả thật, mẫu lỗi và giới hạn được lưu.
- [ ] Hard gates liên quan đã kiểm tra, thiếu evidence được ghi rõ.
- [ ] Người khác chạy lại/đối chiếu được kết quả.
- [ ] Reviewer ghi quyết định và phạm vi; cập nhật README cùng liên kết evidence.
