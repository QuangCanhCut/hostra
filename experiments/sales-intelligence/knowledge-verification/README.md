# Tri thức sản phẩm và kiểm chứng lời thoại

[Nhóm nghiên cứu](../README.md) · [Trung tâm experiments](../../README.md)

**Module:** P05 · **Rủi ro:** R08, R16, R17 · **Gate:** G3, G4 · **Mốc tham chiếu:** M4.

**Tiến độ hiện tại:** IN EXPERIMENT — đã hoàn thành vòng chạy PoC đầu tiên cho cả 4 thí nghiệm (`P05-E01..E04`) trên dữ liệu `synthetic` tại local CPU; xem tổng hợp tại [REPORT_P05_POC_v0.1.md](REPORT_P05_POC_v0.1.md). **Quyết định công nghệ:** SELECTED FOR PoC; chưa chuyển sang `VALIDATED` do cần bổ sung tài liệu thật/PDF scan, mở rộng `E02` lên 100–200 câu và chờ reviewer duyệt.

## 1. Tổng quan bài toán

HOSTRA phải nói đúng giá, đúng SKU và chỉ dùng claims có bằng chứng. P05 kết nối tài liệu merchant với lời thoại P06, đồng thời chặn nội dung hết hiệu lực ngay trước phát. Truy xuất được một đoạn văn không chứng minh đoạn đó đúng hay chứng nhận OCOP có thật.

## 2. Định nghĩa bài toán

- **Đầu vào:** Tài liệu merchant, facts sản phẩm, nguồn OCOP có thẩm quyền, SKU và knowledge versions; câu hỏi hoặc speech candidate.
- **Đầu ra:** ProductFacts có cấu trúc, EvidenceBundle, Claim Registry và quyết định kiểm chứng có source/version.
- **Yêu cầu chức năng, chất lượng và giới hạn:** Trích xuất → human review → snapshot đã duyệt; lọc theo SKU trước retrieval; kiểm tra claims và revalidate trước commit. Giá và thời hạn dùng nguồn có cấu trúc, không suy đoán bằng semantic search. OCOP eligibility thuộc P09, độc lập với merchant approval và điều kiện thực phẩm.
- **Phụ thuộc:** P06 tiêu thụ evidence, P08/P04 cần quyết định publication, P09 giữ eligibility, P11 quyền dữ liệu; P13 hỗ trợ đánh giá.

## 3. Câu hỏi nghiên cứu

- FTS có đủ recall trên câu hỏi tiếng Việt có/không dấu, hay embeddings cải thiện được trên cùng bộ test?
- Trích xuất giá, khối lượng, hạn dùng từ tài liệu khác định dạng sai ở đâu?
- Giá/quyền/chứng nhận đổi sau khi sinh audio có làm candidate cũ bị chặn trước commit không?

## 4. Kiến thức nền cần tìm hiểu

- Structured facts và RAG: chọn nguồn có thẩm quyền cho trường chính xác.
- Provenance và versioning: truy được claim về tài liệu, người duyệt và thời điểm.
- TOCTOU và prompt injection: kiểm tra lại khi dùng dữ liệu, không làm theo lệnh trong tài liệu.

## 5. Phương pháp và công nghệ

**SELECTED FOR PoC:** hybrid structured facts + RAG + Claim Registry + Publication Gate; Docling hỗ trợ extraction, PostgreSQL filters/FTS trước, pgvector chỉ khi benchmark cho thấy cần. Baseline structured-only dễ kiểm tra nhưng hạn chế FAQ dài; RAG-first linh hoạt nhưng tăng rủi ro nhầm/stale. Ragas hỗ trợ đo groundedness, không chứng nhận tính xác thực OCOP.

## 6. Thí nghiệm cần thực hiện

### Chuẩn bị dữ liệu và môi trường

Chuẩn bị 10–20 tài liệu hợp lệ và 100–200 câu hỏi có nhãn SKU, đáp án, evidence chuẩn. Tách phiên bản đúng/cũ, trường thiếu và fixture lỗi có nhãn; không sửa hồ sơ thật rồi trình bày như chứng cứ thật. Notebook có thể thử extraction/retrieval; thử transaction/publication cần mock có version rồi môi trường tích hợp.

Mỗi lượt chạy dùng manifest theo [quy tắc tái lập](../../README.md#5-tái-lập-thí-nghiệm). Các giả thuyết dưới đây là cách diễn đạt để kiểm chứng quyết định Stage 03, **không phải kết quả đã đạt**. Chốt baseline, số lượt lặp và tiêu chí trước khi chạy; báo cả lượt lỗi. Mã Pxx-Eyy giữ theo tài liệu nguồn.

### P05-E01 — Độ chính xác extraction

- **Mục tiêu và giả thuyết:** Các trường quan trọng có thể trích xuất để người duyệt kiểm tra.
- **Đầu vào/tình huống và cách làm:** Chạy 10–20 tài liệu; hai lượt đối chiếu thủ công giá/hạn dùng/khối lượng.
- **Đầu ra, metrics và evidence:** Exact match và nhóm lỗi; lưu bảng field–source–đáp án–prediction.

### P05-E02 — Chất lượng retrieval

- **Mục tiêu và giả thuyết:** FTS là baseline hữu ích; embeddings chỉ được thêm nếu có lợi đo được.
- **Đầu vào/tình huống và cách làm:** Chạy 100–200 câu SKU-scoped trên cùng split; so FTS với nhánh embeddings khi cần.
- **Đầu ra, metrics và evidence:** Recall@k, evidence precision, P95 retrieval; lưu top-k và nhãn đúng.

### P05-E03 — Claims không an toàn

- **Mục tiêu và giả thuyết:** Gate chặn được thông tin thiếu bằng chứng hoặc nhầm SKU.
- **Đầu vào/tình huống và cách làm:** Thử giá đổi, claims sức khỏe thiếu nguồn, OCOP giả, cross-SKU và prompt injection.
- **Đầu ra, metrics và evidence:** 0 unsafe commit trong bộ test định nghĩa; lưu lý do chặn và evidence.

### P05-E04 — Dữ liệu đổi trước phát

- **Mục tiêu và giả thuyết:** Revalidation chặn candidate từng hợp lệ nhưng đã cũ.
- **Đầu vào/tình huống và cách làm:** Sinh TTS, sau đó đổi giá/chứng nhận/quyền trước commit.
- **Đầu ra, metrics và evidence:** Candidate stale bị chặn, audit còn nối được nguồn–turn; lưu timeline version.

## 7. Đánh giá và tiêu chí chấp nhận

G4 chặn claim thiếu source/version, OCOP chưa xác minh và quyền không hợp lệ; G3 bảo vệ phiên bản lúc commit. Không cho OCR/logo hoặc merchant approval tự tạo VERIFIED. Thiếu bằng chứng thì từ chối trả lời/chuyển review. Recall/precision và ngưỡng lợi ích embeddings chưa chốt; báo cả lỗi nguy hiểm dù điểm trung bình cao.

Các metric ở mục 6 đo trực tiếp câu hỏi nghiên cứu, phải báo theo từng nhóm đầu vào/cấu hình thay vì chỉ một số trung bình. Phân biệt **ràng buộc đã xác nhận**, **mục tiêu cần benchmark** và **ngưỡng chưa chốt**. Không tự thêm ngưỡng đạt chất lượng hoặc giá. GO chỉ áp dụng cho phạm vi có evidence và reviewer đồng ý; CHANGE khi cần điều chỉnh phương pháp/cấu hình; NO-GO khi vi phạm hard gate. Nếu chưa đủ bằng chứng, ghi INCONCLUSIVE và việc cần làm tiếp. Không dùng điểm chất lượng để bù vi phạm quyền hoặc tính đúng.

## 8. Kết quả cần bàn giao

- Notebook/script nghiên cứu có hướng dẫn chạy lại, cấu hình và dependency versions; đây là đầu ra cần làm sau, chưa được tạo bởi README.
- Manifest, dữ liệu đầu vào có nguồn/quyền và split hoặc kịch bản kiểm thử; log/metrics theo từng mã thí nghiệm ở mục 6.
- Mẫu đầu ra hợp lệ và ví dụ thất bại, rubric/phiếu chấm nếu có đánh giá người thật; asset riêng tư chỉ lưu tham chiếu có kiểm soát.
- Báo cáo so baseline, giới hạn của Kaggle/Colab hoặc mock so với hệ thống thật, lỗi còn mở và khuyến nghị kỹ thuật.
- Kết luận GO/CHANGE/NO-GO hoặc INCONCLUSIVE, phạm vi kết luận, người phụ trách/reviewer và liên kết evidence. Không tạo kết quả giả để điền báo cáo.

## 9. Tích hợp với HOSTRA

EvidenceBundle cấp cho P06; P05 kiểm draft trước TTS rồi revalidate sát commit phối hợp P09/P11. Giữ source_id, document_version, actor approval và knowledge_version. Khi có PR triển khai, đối chiếu contracts trong packages/contracts/; không tạo một nguồn eligibility cạnh tranh với P09.

### Điểm cần xác minh

Dữ liệu catalog, nguồn OCOP độc lập, chính sách claims nhạy cảm, chi phí human review và ngưỡng retrieval cần chủ sở hữu.

## 10. Tài liệu tham khảo

- [Architecture Baseline v1.2](../../../docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx): §5–7, §9; D06, D07, D21; ARD-05, ARD-14; ACR-002.
- [Technical Research & PoC Plan v1.0](../../../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx): §4, §5 hồ sơ P05, đặc biệt mục .3/.5/.11–.14; §8–9 về benchmark/evidence, §13–14 về gates và quyết định mở.
- [Technical Risk Assessment v1.1](../../../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx): các mục R08, R16, R17; đọc failure scenario và evidence cần thiết.

Các liên kết ngoài sau được lấy từ hồ sơ Stage 03; đây là điểm bắt đầu đọc nguyên lý và cách chạy, chưa phải xác nhận license, giá hay khả năng tương thích ở thời điểm thực nghiệm:

- [Paper RAG](https://arxiv.org/abs/2005.11401)
- [Mã nguồn Docling](https://github.com/docling-project/docling)
- [PostgreSQL FTS](https://www.postgresql.org/docs/current/textsearch.html)
- [Mã nguồn pgvector](https://github.com/pgvector/pgvector)
- [Mã nguồn Ragas](https://github.com/vibrantlabsai/ragas)

## 11. Checklist tiến độ nghiên cứu

- [x] Đọc nguồn và chốt câu hỏi/phạm vi P05 (cần bổ sung tên reviewer khi chốt nghiệm thu).
- [x] Chuẩn bị bộ test `synthetic` và baseline (`schemas.py`, `data/catalog_seed.json`, `e01_extraction/ground_truth.json`, `e02_retrieval/e02_questions.json`).
- [ ] Bổ sung tài liệu merchant thật (gồm PDF scan) và khóa ngưỡng chất lượng cuối cùng với reviewer.
- [x] Chạy P05-E01 (vòng 1 synthetic — 92.5% Exact Match), lưu output/metrics/evidence tại `runs/P05-E01_20261121T073009Z.json`.
- [x] Chạy P05-E02 (vòng 1 synthetic 45 câu — Hybrid RRF R@1=0.822, R@3=1.000, P95=41.3ms), lưu evidence tại `runs/P05-E02_20261121T055725Z.json`.
- [x] Chạy P05-E03 (vòng 1 synthetic — 13/13 PASS, 0 unsafe commits), lưu evidence tại `runs/P05-E03_20261121T050419Z.json`.
- [x] Chạy P05-E04 (vòng 1 synthetic — 4/4 PASS, 0 stale leaks), lưu evidence tại `runs/P05-E04_20261121T050420Z.json`.
- [x] Kiểm tra hard gates G3/G4 trên bộ negative/TOCTOU và lập báo cáo vòng 1 tại [REPORT_P05_POC_v0.1.md](REPORT_P05_POC_v0.1.md).
- [ ] Chạy lại trên dữ liệu thật + PostgreSQL transaction tích hợp P08, review giới hạn và chốt quyết định `VALIDATED`.
