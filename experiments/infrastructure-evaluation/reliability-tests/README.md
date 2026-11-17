# Độ tin cậy, phục hồi và bằng chứng nghiệm thu

[Nhóm nghiên cứu](../README.md) · [Trung tâm experiments](../../README.md)

**Module:** P12/P13 · **Rủi ro:** R01–R18; trọng tâm R03, R06–R12, R15–R17 · **Gate:** G1–G6 · **Mốc tham chiếu:** M0–M7.

**Tiến độ khởi tạo:** NOT STARTED — chưa có evidence chạy thí nghiệm trong thư mục tại lần kiểm kê này. **Quyết định công nghệ:** SELECTED FOR PoC; tính khả thi và các kết quả vẫn TO VALIDATE. Owner/reviewer cần nhóm phân công.

## 1. Tổng quan bài toán

Một model chạy thành công chưa chứng minh toàn bộ buổi live an toàn khi giá đổi, quyền bị thu hồi hoặc worker crash. Track này nối bằng chứng của các nhóm, dùng replay/fault injection và đánh giá người thật để phân biệt lỗi chất lượng với vi phạm bất biến.

## 2. Định nghĩa bài toán

- **Đầu vào:** Dataset/version có quyền, event/media mocks, GPU runs, bảng risk↔gate, cấu hình workload và fault scenario có expected outcome.
- **Đầu ra:** Run manifests, log/video hợp lệ, metrics, phiếu chấm người thật, danh sách lỗi và kết luận GO/CHANGE/NO-GO có reviewer.
- **Yêu cầu chức năng, chất lượng và giới hạn:** Mô phỏng lỗi có kiểm soát trước môi trường tích hợp; kiểm tra recovery không replay mù hoặc dùng cache hết quyền. Đo server và viewer riêng. Không chỉnh threshold sau khi nhìn kết quả mà không ghi revision; không lấy benchmark paper thay nghiệm thu.
- **Phụ thuộc:** P08/P09 cung cấp simulator/state, P04 cung cấp ACK/probe, P05/P11 cung cấp negative gates; P10 phải hiển thị đúng degraded/reconnect; P01–P07 cung cấp artifact/rubric.

## 3. Câu hỏi nghiên cứu

- Sau crash giữa playback, hệ thống có reconcile mà không phát lặp/chồng không?
- Fallback có vẫn kiểm quyền/OCOP/claims khi dịch vụ lỗi liên hoàn không?
- W3 120 phút với ít nhất 2 lỗi có cung cấp bằng chứng continuity, recovery và cost/hour không?

## 4. Kiến thức nền cần tìm hiểu

- Property-based testing và replay: tìm chuỗi sự kiện tối giản phá invariant.
- Fault injection/circuit breaker: đo recovery và giới hạn retry thay vì chỉ thử happy path.
- Human QA và validity: đánh giá mù, ghi dữ liệu thật/synthetic, không lấy điểm trung bình bù hard gate.

## 5. Phương pháp và công nghệ

**SELECTED FOR PoC:** risk-based harness + automated replay + human QA; pytest/Hypothesis cho state, Playwright cho browser, Locust cho tải, Ragas cho P05; DeepEval tùy chọn. Manual demo là baseline quan sát nhưng thiếu fault/replay; continuous evaluation platform chưa là yêu cầu MVP. Tài liệu này mô tả backlog, không khẳng định các công cụ đã được cài.

## 6. Thí nghiệm cần thực hiện

### Chuẩn bị dữ liệu và môi trường

Notebook/local CPU phù hợp replay mock. Endurance cần môi trường publisher/viewer và services ổn định; ghi rõ fault mô phỏng hay thật. Dùng W0 trước, W1 đo latency, W2 burst, W3 120 phút; xem workload chuẩn ở README tổng. Chuẩn bị quyền dữ liệu, reviewer độc lập cho hard gates và phương án dừng có kiểm soát.

Mỗi lượt chạy dùng manifest theo [quy tắc tái lập](../../README.md#5-tái-lập-thí-nghiệm). Các giả thuyết dưới đây là cách diễn đạt để kiểm chứng quyết định Stage 03, **không phải kết quả đã đạt**. Chốt baseline, số lượt lặp và tiêu chí trước khi chạy; báo cả lượt lỗi. Mã Pxx-Eyy giữ theo tài liệu nguồn.

### P12-E04 — Phục hồi 120 phút

- **Mục tiêu và giả thuyết:** Kiến trúc degraded/recovery có thể giữ media an toàn dưới lỗi.
- **Đầu vào/tình huống và cách làm:** W3 120 phút với ≥2 faults, theo dõi chi phí/health và restart.
- **Đầu ra, metrics và evidence:** Continuity, recovery, cost/hour; lưu thời điểm lỗi, recording và bill.

### P13-E01 — FSM và replay

- **Mục tiêu và giả thuyết:** Retry/crash không tạo overlap hoặc replay không an toàn.
- **Đầu vào/tình huống và cách làm:** Randomize duplicate/crash/restart/Stop/Pause; chạy lại cùng seed.
- **Đầu ra, metrics và evidence:** 0 overlap/unsafe replay trong suite; lưu counterexample và trace.

### P13-E02 — Claims/quyền/OCOP lỗi

- **Mục tiêu và giả thuyết:** Gate vẫn chặn đầu ra không đủ điều kiện khi state thay đổi.
- **Đầu vào/tình huống và cách làm:** Hồ sơ giả/hết hạn/sai SKU, quyền revoke, media stale; đối chiếu quyết định.
- **Đầu ra, metrics và evidence:** 0 false eligibility/unsafe commit; lưu version và audit.

### P13-E03 — Đánh giá mù

- **Mục tiêu và giả thuyết:** Chất lượng có thể được người dùng đánh giá nhất quán theo rubric.
- **Đầu vào/tình huống và cách làm:** Panel chấm presenter/TTS/story, thống nhất threshold trước khi chạy.
- **Đầu ra, metrics và evidence:** Điểm theo tiêu chí và bất đồng reviewer; lưu phiếu chấm ẩn danh.

### P13-E04 — Latency và endurance

- **Mục tiêu và giả thuyết:** Pipeline có thể đáp ứng mục tiêu trong workload định nghĩa.
- **Đầu vào/tình huống và cách làm:** W1: 3 SKU, 5 viewer, khoảng 2–4 comment hợp lệ/phút; W3 120 phút và faults.
- **Đầu ra, metrics và evidence:** Mục tiêu server P50≤7s/P95≤10s, continuity; lưu timestamp từng chặng và probe viewer riêng.

### P13-E05 — Chi phí và tái lập

- **Mục tiêu và giả thuyết:** Evidence đủ để người khác kiểm lại kết luận và chi phí.
- **Đầu vào/tình huống và cách làm:** Đối chiếu GPU/LLM/TTS/LiveKit bills với manifests, runs và artifacts.
- **Đầu ra, metrics và evidence:** Cost/live-hour và khả năng tái lập; lưu ledger, checksum, giới hạn số liệu.

## 7. Đánh giá và tiêu chí chấp nhận

G1 media; G2 tương tác; G3 orchestration; G4 rights/claims/OCOP/tenant; G5 hiệu năng/độ bền; G6 merchant. Vi phạm hard gate → NO-GO cho phạm vi nghiệm thu; chất lượng/hiệu năng chưa đạt nhưng safety nguyên vẹn → CHANGE và chạy lại. Thiếu dữ liệu → INCONCLUSIVE, không ép GO. Mục tiêu latency/endurance chưa được chứng minh; 0 lỗi trong suite không đảm bảo 0 lỗi ngoài thực tế.

Các metric ở mục 6 đo trực tiếp câu hỏi nghiên cứu, phải báo theo từng nhóm đầu vào/cấu hình thay vì chỉ một số trung bình. Phân biệt **ràng buộc đã xác nhận**, **mục tiêu cần benchmark** và **ngưỡng chưa chốt**. Không tự thêm ngưỡng đạt chất lượng hoặc giá. GO chỉ áp dụng cho phạm vi có evidence và reviewer đồng ý; CHANGE khi cần điều chỉnh phương pháp/cấu hình; NO-GO khi vi phạm hard gate. Nếu chưa đủ bằng chứng, ghi INCONCLUSIVE và việc cần làm tiếp. Không dùng điểm chất lượng để bù vi phạm quyền hoặc tính đúng.

## 8. Kết quả cần bàn giao

- Notebook/script nghiên cứu có hướng dẫn chạy lại, cấu hình và dependency versions; đây là đầu ra cần làm sau, chưa được tạo bởi README.
- Manifest, dữ liệu đầu vào có nguồn/quyền và split hoặc kịch bản kiểm thử; log/metrics theo từng mã thí nghiệm ở mục 6.
- Mẫu đầu ra hợp lệ và ví dụ thất bại, rubric/phiếu chấm nếu có đánh giá người thật; asset riêng tư chỉ lưu tham chiếu có kiểm soát.
- Báo cáo so baseline, giới hạn của Kaggle/Colab hoặc mock so với hệ thống thật, lỗi còn mở và khuyến nghị kỹ thuật.
- Kết luận GO/CHANGE/NO-GO hoặc INCONCLUSIVE, phạm vi kết luận, người phụ trách/reviewer và liên kết evidence. Không tạo kết quả giả để điền báo cáo.

## 9. Tích hợp với HOSTRA

Bàn giao evidence cho owner/reviewer từng module và người quyết định pilot; audit nối source → candidate → commit → ACK. Kết quả simulator chỉ là một lớp bằng chứng, cần P04/P10 probe thật. GO controlled private pilot không đồng nghĩa production-ready hoặc được phép tích hợp TikTok/Shopee.

### Điểm cần xác minh

Rubric/threshold chất lượng, mức degraded/recovery, reviewer, dữ liệu thật và quyền thử nghiệm trên môi trường dịch vụ cần nhóm chốt.

## 10. Tài liệu tham khảo

- [Architecture Baseline v1.2](../../../docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx): §10–12; D18, D19, D28; ARD-01, ARD-09, ARD-16.
- [Technical Research & PoC Plan v1.0](../../../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx): §4, §5 hồ sơ P12/P13, đặc biệt mục .3/.5/.11–.14; §8–9 về benchmark/evidence, §13–14 về gates và quyết định mở.
- [Technical Risk Assessment v1.1](../../../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx): các mục R01–R18; trọng tâm R03, R06–R12, R15–R17; đọc failure scenario và evidence cần thiết.

Các liên kết ngoài sau được lấy từ hồ sơ Stage 03; đây là điểm bắt đầu đọc nguyên lý và cách chạy, chưa phải xác nhận license, giá hay khả năng tương thích ở thời điểm thực nghiệm:

- [Mã nguồn pytest](https://github.com/pytest-dev/pytest)
- [Mã nguồn Hypothesis](https://github.com/HypothesisWorks/hypothesis)
- [Mã nguồn Playwright](https://github.com/microsoft/playwright)
- [Mã nguồn Locust](https://github.com/locustio/locust)
- [Mã nguồn Ragas](https://github.com/vibrantlabsai/ragas)
- [Mã nguồn DeepEval](https://github.com/confident-ai/deepeval)
- [Google SRE về SLO](https://sre.google/sre-book/service-level-objectives/)

## 11. Checklist tiến độ nghiên cứu

- [ ] Đọc nguồn và chốt câu hỏi/phạm vi P12/P13, owner và reviewer.
- [ ] Xác minh quyền dữ liệu/model; chuẩn bị bộ test và baseline.
- [ ] Khóa cấu hình, cách đo, rubric và các ngưỡng cần nhóm phê duyệt.
- [ ] Chạy P12-E04, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P13-E01, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P13-E02, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P13-E03, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P13-E04, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P13-E05, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Kiểm tra hard gates và đối chiếu dependency/contract với nhóm liên quan.
- [ ] Chạy lại được kết quả, review giới hạn và ghi quyết định có bằng chứng.
