# Hiểu và phân luồng bình luận tiếng Việt

[Nhóm nghiên cứu](../README.md) · [Trung tâm experiments](../../README.md)

**Module:** P07 · **Rủi ro:** R04, R03, R10 · **Gate:** G2, G3 · **Mốc tham chiếu:** M4.

**Tiến độ khởi tạo:** NOT STARTED — chưa có evidence chạy thí nghiệm trong thư mục tại lần kiểm kê này. **Quyết định công nghệ:** SELECTED FOR PoC; tính khả thi và các kết quả vẫn TO VALIDATE. Owner/reviewer cần nhóm phân công.

## 1. Tổng quan bài toán

Bình luận live có tiếng lóng, thiếu dấu, spam và câu hỏi tham chiếu mơ hồ. P07 cần biến chúng thành tác vụ rõ intent/SKU để P08 chọn, tránh trả lời nhầm sản phẩm hoặc để bình luận lặp chiếm hết thời gian kể chuyện.

## 2. Định nghĩa bài toán

- **Đầu vào:** CommentEvent với source, event_id, session_id, viewer_id, timestamp và text; ngữ cảnh phiên được phép sử dụng.
- **Đầu ra:** CommentTask/CommentGroup gồm intent, SKU refs, confidence, priority_hint, TTL và liên kết ngữ cảnh/record gốc.
- **Yêu cầu chức năng, chất lượng và giới hạn:** Chuẩn hóa, dedup, phân loại, resolve SKU và grouping nhưng giữ record của từng viewer. Không chắc SKU thì UNCLEAR. Không coi comment là lệnh hệ thống; không tự kích hoạt mọi job TTS hoặc đổi Active SKU.
- **Phụ thuộc:** P10 nhận/lưu bình luận, P08 quyết định fairness/lịch, P06 trả lời task đã chọn, P09 cung cấp catalog; P11 bảo vệ tenant/session.

## 3. Câu hỏi nghiên cứu

- PhoBERT-base hay SetFit tốt hơn với 8/16/32 mẫu mỗi lớp trên cùng held-out test?
- Tiếng lóng và thiếu dấu làm giảm intent F1/SKU precision bao nhiêu?
- Grouping theo intent/SKU/rules có gom nhầm SKU không, và selective LLM tăng latency/chi phí thế nào?

## 4. Kiến thức nền cần tìm hiểu

- Vietnamese tokenization, fine-tuning và few-shot: so classifier đúng điều kiện dữ liệu.
- Macro F1 và per-class F1: tránh bỏ qua lớp hiếm khi accuracy cao.
- Calibration, abstention, dedup và grouping: phân biệt event trùng với nhiều người hỏi cùng ý.

## 5. Phương pháp và công nghệ

**SELECTED FOR PoC:** rules + Vietnamese NLP classifier + selective LLM; PhoBERT-base và SetFit là hai ứng viên phải benchmark, chưa có bên thắng. Baseline rules + LLM cho tất cả bình luận hợp lệ dễ khởi động nhưng tốn API. Grouping dùng intent/SKU/rules trước; multilingual E5/pgvector chỉ bổ sung khi có bằng chứng cần embeddings. P07 không cần workflow agent nhiều bước.

## 6. Thí nghiệm cần thực hiện

### Chuẩn bị dữ liệu và môi trường

Stage 03 dự kiến 500–1.000 comment v0.1, có nhãn intent/SKU và nguồn dữ liệu. Giữ test thật có quyền riêng, báo riêng synthetic; không chia paraphrase của cùng một câu vào cả train và test. Kaggle/Colab phù hợp train/evaluate classifier; lưu split, seed, revision model và confusion matrix.

Mỗi lượt chạy dùng manifest theo [quy tắc tái lập](../../README.md#5-tái-lập-thí-nghiệm). Các giả thuyết dưới đây là cách diễn đạt để kiểm chứng quyết định Stage 03, **không phải kết quả đã đạt**. Chốt baseline, số lượt lặp và tiêu chí trước khi chạy; báo cả lượt lỗi. Mã Pxx-Eyy giữ theo tài liệu nguồn.

### P07-E01 — So sánh classifier

- **Mục tiêu và giả thuyết:** Một classifier nhỏ có thể giảm chi phí mà giữ chất lượng so baseline LLM.
- **Đầu vào/tình huống và cách làm:** Cùng train/dev/test, so PhoBERT-base/SetFit ở 8/16/32 mẫu mỗi lớp.
- **Đầu ra, metrics và evidence:** Macro/per-class F1, P95, chi phí; lưu split, predictions và confusion matrix.

### P07-E02 — Ngôn ngữ khó

- **Mục tiêu và giả thuyết:** Mô hình đủ ổn định với thiếu dấu/tiếng lóng và nhắc nhiều SKU.
- **Đầu vào/tình huống và cách làm:** Chạy 200 trường hợp khó thật/synthetic có nhãn và tách nguồn.
- **Đầu ra, metrics và evidence:** Intent F1, SKU precision; lưu lỗi theo nhóm ngôn ngữ.

### P07-E03 — Gom nhóm và từ chối suy đoán

- **Mục tiêu và giả thuyết:** Rules theo SKU hạn chế gom sai; abstention xử lý câu mơ hồ.
- **Đầu vào/tình huống và cách làm:** Thử 100 cặp đồng nghĩa cùng các cặp sai SKU, thay ngưỡng trên dev rồi khóa test.
- **Đầu ra, metrics và evidence:** Grouping precision, bad merge, fallback %; lưu cặp và quyết định.

### P07-E04 — Burst và trùng lặp

- **Mục tiêu và giả thuyết:** Dedup và giới hạn hàng đợi giữ tác vụ hợp lệ dưới tải.
- **Đầu vào/tình huống và cách làm:** Mô phỏng 20–100 raw comment/phút, ID lặp và spam người dùng; nối P08 mock.
- **Đầu ra, metrics và evidence:** Không task trùng, queue P95, fairness; lưu event timeline và task IDs.

## 7. Đánh giá và tiêu chí chấp nhận

G2/G3 đánh giá triage/fairness và tính đúng của task. Không gom mất record viewer khác, không lẫn tenant/session, không đoán SKU mơ hồ. F1, confidence/spam/grouping thresholds còn mở và phải khóa trước test. Khi classifier lỗi dùng rules an toàn/selective LLM có quota, hoặc defer/expire theo TTL; không đoán câu trả lời.

Các metric ở mục 6 đo trực tiếp câu hỏi nghiên cứu, phải báo theo từng nhóm đầu vào/cấu hình thay vì chỉ một số trung bình. Phân biệt **ràng buộc đã xác nhận**, **mục tiêu cần benchmark** và **ngưỡng chưa chốt**. Không tự thêm ngưỡng đạt chất lượng hoặc giá. GO chỉ áp dụng cho phạm vi có evidence và reviewer đồng ý; CHANGE khi cần điều chỉnh phương pháp/cấu hình; NO-GO khi vi phạm hard gate. Nếu chưa đủ bằng chứng, ghi INCONCLUSIVE và việc cần làm tiếp. Không dùng điểm chất lượng để bù vi phạm quyền hoặc tính đúng.

## 8. Kết quả cần bàn giao

- Notebook/script nghiên cứu có hướng dẫn chạy lại, cấu hình và dependency versions; đây là đầu ra cần làm sau, chưa được tạo bởi README.
- Manifest, dữ liệu đầu vào có nguồn/quyền và split hoặc kịch bản kiểm thử; log/metrics theo từng mã thí nghiệm ở mục 6.
- Mẫu đầu ra hợp lệ và ví dụ thất bại, rubric/phiếu chấm nếu có đánh giá người thật; asset riêng tư chỉ lưu tham chiếu có kiểm soát.
- Báo cáo so baseline, giới hạn của Kaggle/Colab hoặc mock so với hệ thống thật, lỗi còn mở và khuyến nghị kỹ thuật.
- Kết luận GO/CHANGE/NO-GO hoặc INCONCLUSIVE, phạm vi kết luận, người phụ trách/reviewer và liên kết evidence. Không tạo kết quả giả để điền báo cáo.

## 9. Tích hợp với HOSTRA

CommentTask chỉ mang priority_hint; P08 sở hữu lịch. Giữ event_id, source, viewer/session, SKU refs và ngữ cảnh khi chuyển sang module conversation. TikTok/Shopee connector không nằm trong bằng chứng private-room PoC.

### Điểm cần xác minh

Nguồn comment thật hợp lệ, taxonomy nhãn, confidence thresholds, quota LLM và bên thắng PhoBERT/SetFit cần quyết định từ số liệu.

## 10. Tài liệu tham khảo

- [Architecture Baseline v1.2](../../../docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx): §6–7; D11, D15, D23; ARD-06, ARD-07.
- [Technical Research & PoC Plan v1.0](../../../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx): §4, §5 hồ sơ P07, đặc biệt mục .3/.5/.11–.14; §8–9 về benchmark/evidence, §13–14 về gates và quyết định mở.
- [Technical Risk Assessment v1.1](../../../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx): các mục R04, R03, R10; đọc failure scenario và evidence cần thiết.

Các liên kết ngoài sau được lấy từ hồ sơ Stage 03; đây là điểm bắt đầu đọc nguyên lý và cách chạy, chưa phải xác nhận license, giá hay khả năng tương thích ở thời điểm thực nghiệm:

- [Paper PhoBERT](https://aclanthology.org/2020.findings-emnlp.92/)
- [Mã nguồn PhoBERT](https://github.com/VinAIResearch/PhoBERT)
- [Paper SetFit](https://arxiv.org/abs/2209.11055)
- [Mã nguồn SetFit](https://github.com/huggingface/setfit)
- [Model card multilingual E5](https://huggingface.co/intfloat/multilingual-e5-small)

## 11. Checklist tiến độ nghiên cứu

- [ ] Đọc nguồn và chốt câu hỏi/phạm vi P07, owner và reviewer.
- [ ] Xác minh quyền dữ liệu/model; chuẩn bị bộ test và baseline.
- [ ] Khóa cấu hình, cách đo, rubric và các ngưỡng cần nhóm phê duyệt.
- [ ] Chạy P07-E01, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P07-E02, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P07-E03, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P07-E04, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Kiểm tra hard gates và đối chiếu dependency/contract với nhóm liên quan.
- [ ] Chạy lại được kết quả, review giới hạn và ghi quyết định có bằng chứng.
