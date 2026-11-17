# Đánh giá GPU, placement và chi phí

[Nhóm nghiên cứu](../README.md) · [Trung tâm experiments](../../README.md)

**Module:** P12 · **Rủi ro:** R03, R07, R11, R12, R15 · **Gate:** G5 · **Mốc tham chiếu:** M1/M6.

**Tiến độ khởi tạo:** NOT STARTED — chưa có evidence chạy thí nghiệm trong thư mục tại lần kiểm kê này. **Quyết định công nghệ:** SELECTED FOR PoC; tính khả thi và các kết quả vẫn TO VALIDATE. Owner/reviewer cần nhóm phân công.

## 1. Tổng quan bài toán

GPU tạo clip trước live và GPU xử lý câu nói trong live có yêu cầu khác nhau. P12 phải tìm cấu hình chạy được và chi phí trên đầu ra dùng được; cấu hình nhanh riêng lẻ có thể trễ deadline khi dùng chung encoder hoặc bị tính phí warm/idle.

## 2. Định nghĩa bài toán

- **Đầu vào:** Checkpoint/config đã khóa, job P01/P03, workload media, thông số GPU/provider/network và dữ liệu usage/billing.
- **Đầu ra:** Ma trận VRAM/latency/throughput, artifact và log, cost ledger, khuyến nghị cấu hình kèm giới hạn.
- **Yêu cầu chức năng, chất lượng và giới hạn:** Tách logic pre-live on-demand và warm in-live; so colocated/separate GStreamer. Đo warmup, retry, OOM, transfer và media bị bỏ. Không suy chi phí cloud từ một lượt notebook miễn phí hoặc chỉ FPS inference.
- **Phụ thuộc:** P01/P03 định nghĩa job, P04 cung cấp encoder/live profile, P08 đặt deadline, P11 quyền đưa dữ liệu lên provider, P13 tổng hợp evidence.

## 3. Câu hỏi nghiên cứu

- Wan tạo clip được duyệt tốn thời gian/VRAM/chi phí bao nhiêu khi tính cả clip bị loại?
- MuseTalk P95 và missed deadline thay đổi thế nào khi encoder dùng chung tài nguyên?
- Chi phí mạng của tách node có bù được lợi ích giảm tranh chấp GPU không?

## 4. Kiến thức nền cần tìm hiểu

- GPU memory/precision/offload: hiểu trade-off giữa chạy vừa VRAM và thời gian.
- Cold/warm, throughput và percentiles: so trên workload và số lượt tương đương.
- Unit economics: phân biệt cost/approved clip, live-hour và viewer-hour; tính cả phần bị bỏ.

## 5. Phương pháp và công nghệ

**SELECTED FOR PoC:** Hybrid GPU Workers + Managed Core; generation on-demand, warm lip-sync; nghiên cứu Runpod so Modal/Lambda và chung/tách node. Single GPU VM là baseline đơn giản nhưng dễ tranh chấp; Kubernetes pools chưa được chọn cho MVP. Docker Compose/versioned runtime là hướng môi trường sau này, không tạo Docker trong nhiệm vụ tài liệu này.

## 6. Thí nghiệm cần thực hiện

### Chuẩn bị dữ liệu và môi trường

Stage 03 đề xuất khảo sát Wan 48/80 GB, MuseTalk 24/48 GB khi hỗ trợ; đây là ma trận cần thử, không phải chứng nhận cấu hình tối thiểu. Trên Kaggle/Colab ghi GPU thực cấp và giới hạn phiên, CUDA/driver/model/config; nếu không đủ tài nguyên ghi BLOCKED cho run cụ thể. So provider cần bill và môi trường thật có quyền sử dụng, chưa đặt thuê tài nguyên.

Mỗi lượt chạy dùng manifest theo [quy tắc tái lập](../../README.md#5-tái-lập-thí-nghiệm). Các giả thuyết dưới đây là cách diễn đạt để kiểm chứng quyết định Stage 03, **không phải kết quả đã đạt**. Chốt baseline, số lượt lặp và tiêu chí trước khi chạy; báo cả lượt lỗi. Mã Pxx-Eyy giữ theo tài liệu nguồn.

### P12-E01 — Chi phí Wan

- **Mục tiêu và giả thuyết:** Có thể tìm cấu hình cho chi phí/clip đạt QC phù hợp.
- **Đầu vào/tình huống và cách làm:** Cùng clip/config trên GPU ứng viên, tính cả warmup/retry và QC.
- **Đầu ra, metrics và evidence:** Thời gian/clip, peak VRAM, cost/approved clip; lưu manifest, log, QC và bill.

### P12-E02 — Deadline MuseTalk

- **Mục tiêu và giả thuyết:** Warm worker có thể đáp ứng deadline khi encoder cùng chạy.
- **Đầu vào/tình huống và cách làm:** Audio 3/6/10 giây với media encoding đồng thời; so baseline riêng.
- **Đầu ra, metrics và evidence:** P50/P95 readiness, missed deadline; lưu contention/timeline và phần media bỏ.

### P12-E03 — Placement

- **Mục tiêu và giả thuyết:** Tách node có thể giảm tranh chấp nhưng tăng transfer.
- **Đầu vào/tình huống và cách làm:** Cùng workload trên colocated/separate; đo network và compute.
- **Đầu ra, metrics và evidence:** Latency, GPU contention, egress; lưu topology/config và bill.

## 7. Đánh giá và tiêu chí chấp nhận

G5 yêu cầu evidence hiệu năng/chi phí, chưa có cost cap hoặc GPU/provider thắng. P01 background không được phá deadline policy đã duyệt của live; epoch cũ không được sử dụng sau restart. Không chứa secret/private asset trong image/log và không báo publisher lỗi là LIVE. Nếu chưa có bill chỉ báo resource/time, không bịa giá.

Các metric ở mục 6 đo trực tiếp câu hỏi nghiên cứu, phải báo theo từng nhóm đầu vào/cấu hình thay vì chỉ một số trung bình. Phân biệt **ràng buộc đã xác nhận**, **mục tiêu cần benchmark** và **ngưỡng chưa chốt**. Không tự thêm ngưỡng đạt chất lượng hoặc giá. GO chỉ áp dụng cho phạm vi có evidence và reviewer đồng ý; CHANGE khi cần điều chỉnh phương pháp/cấu hình; NO-GO khi vi phạm hard gate. Nếu chưa đủ bằng chứng, ghi INCONCLUSIVE và việc cần làm tiếp. Không dùng điểm chất lượng để bù vi phạm quyền hoặc tính đúng.

## 8. Kết quả cần bàn giao

- Notebook/script nghiên cứu có hướng dẫn chạy lại, cấu hình và dependency versions; đây là đầu ra cần làm sau, chưa được tạo bởi README.
- Manifest, dữ liệu đầu vào có nguồn/quyền và split hoặc kịch bản kiểm thử; log/metrics theo từng mã thí nghiệm ở mục 6.
- Mẫu đầu ra hợp lệ và ví dụ thất bại, rubric/phiếu chấm nếu có đánh giá người thật; asset riêng tư chỉ lưu tham chiếu có kiểm soát.
- Báo cáo so baseline, giới hạn của Kaggle/Colab hoặc mock so với hệ thống thật, lỗi còn mở và khuyến nghị kỹ thuật.
- Kết luận GO/CHANGE/NO-GO hoặc INCONCLUSIVE, phạm vi kết luận, người phụ trách/reviewer và liên kết evidence. Không tạo kết quả giả để điền báo cáo.

## 9. Tích hợp với HOSTRA

P01/P03/P04 dùng cấu hình đề xuất, P13 dùng cost ledger để đánh giá; phải giữ model revision, concurrency, workload và rights snapshot. W3/recovery P12-E04 được phụ trách tại [kiểm thử độ tin cậy](../reliability-tests/README.md) để tránh hai báo cáo chuẩn mâu thuẫn.

### Điểm cần xác minh

GPU/provider khả dụng, ngân sách, vị trí xử lý dữ liệu, ngưỡng deadline và lựa chọn colocated/separate cần quyết định sau benchmark.

## 10. Tài liệu tham khảo

- [Architecture Baseline v1.2](../../../docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx): §8, §10–12; D24–D27, D29; ARD-08, ARD-11, ARD-12.
- [Technical Research & PoC Plan v1.0](../../../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx): §4, §5 hồ sơ P12, đặc biệt mục .3/.5/.11–.14; §8–9 về benchmark/evidence, §13–14 về gates và quyết định mở.
- [Technical Risk Assessment v1.1](../../../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx): các mục R03, R07, R11, R12, R15; đọc failure scenario và evidence cần thiết.

Các liên kết ngoài sau được lấy từ hồ sơ Stage 03; đây là điểm bắt đầu đọc nguyên lý và cách chạy, chưa phải xác nhận license, giá hay khả năng tương thích ở thời điểm thực nghiệm:

- [Tài liệu Runpod](https://docs.runpod.io/)
- [Tài liệu Modal](https://modal.com/docs)
- [Tài liệu Lambda](https://docs.lambda.ai/)
- [Docker Compose](https://docs.docker.com/compose/)
- [OpenTelemetry Python](https://github.com/open-telemetry/opentelemetry-python)
- [NVIDIA DCGM Exporter](https://github.com/NVIDIA/dcgm-exporter)

## 11. Checklist tiến độ nghiên cứu

- [ ] Đọc nguồn và chốt câu hỏi/phạm vi P12, owner và reviewer.
- [ ] Xác minh quyền dữ liệu/model; chuẩn bị bộ test và baseline.
- [ ] Khóa cấu hình, cách đo, rubric và các ngưỡng cần nhóm phê duyệt.
- [ ] Chạy P12-E01, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P12-E02, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P12-E03, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Kiểm tra hard gates và đối chiếu dependency/contract với nhóm liên quan.
- [ ] Chạy lại được kết quả, review giới hạn và ghi quyết định có bằng chứng.
