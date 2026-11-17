# Tạo người dẫn từ một ảnh chân dung

[Nhóm nghiên cứu](../README.md) · [Trung tâm experiments](../../README.md)

**Module:** P01 · **Rủi ro:** R01, R09, R11, R13, R14 · **Gate:** G1, G4, G6 · **Mốc tham chiếu:** M1.

**Tiến độ khởi tạo:** NOT STARTED — chưa có evidence chạy thí nghiệm trong thư mục tại lần kiểm kê này. **Quyết định công nghệ:** SELECTED FOR PoC; tính khả thi và các kết quả vẫn TO VALIDATE. Owner/reviewer cần nhóm phân công.

## 1. Tổng quan bài toán

HOSTRA cần tạo thư viện người dẫn trước buổi live từ một ảnh có quyền sử dụng. Người dẫn phải giữ danh tính và chuyển động đủ tự nhiên khi lặp hoặc nối clip; lỗi mặt, tay hoặc tư thế làm giảm độ tin cậy của buổi bán hàng. P01 chỉ tạo hình và chuyển động offline, còn khẩu hình theo câu nói mới thuộc P03.

## 2. Định nghĩa bài toán

- **Đầu vào:** PortraitAsset, consent_ref, cấu hình trang phục/phong cách, MotionTemplate có quyền, seed và cấu hình model.
- **Đầu ra:** PresenterIdentity, ảnh đã duyệt, MotionClip, URI/checksum, phiên bản model và rights_version, kết quả QC và phê duyệt.
- **Yêu cầu chức năng, chất lượng và giới hạn:** Kiểm tra quyền và chất lượng ảnh trước sinh; tạo ảnh → chuyển động → QC → merchant duyệt. So sánh danh tính giữa clip, độ tự nhiên, tỷ lệ clip dùng được và chi phí. Không sinh toàn thân theo từng bình luận; không mặc định hình thể được suy ra từ một ảnh là hình thể thật.
- **Phụ thuộc:** P11 cung cấp quyền ảnh/motion; P03 dùng clip để lip-sync; P04 phát clip đã đủ điều kiện; P10 phục vụ preview và P12 đo tài nguyên.

## 3. Câu hỏi nghiên cứu

- Một ảnh có giữ được danh tính qua các seed, phong cách và góc nhìn khác nhau không?
- Motion template nào có tỷ lệ clip dùng được cao và ít lỗi tay/mặt tại điểm nối?
- Clip được đánh giá tốt ở P01 có giữ crop ổn định khi đưa sang MuseTalk không?

## 4. Kiến thức nền cần tìm hiểu

- Diffusion và identity conditioning: hiểu khác biệt giữa ảnh đẹp và ảnh đúng danh tính.
- Motion transfer và temporal consistency: kiểm tra chuyển động, drift và điểm nối qua nhiều khung.
- PyTorch, xử lý video và VRAM: tái lập seed/config, chuẩn hóa FPS/codec và đo chi phí cả retry.

## 5. Phương pháp và công nghệ

**SELECTED FOR PoC:** PhotoMaker → Wan2.2 Animate, dùng Motion Library có quyền và QC offline. Baseline đối chứng trong tài liệu là footage người thật, chỉ để hiểu trade-off; đây không phải pipeline MVP hiện tại. MimicMotion là đối chứng nghiên cứu, không được mặc định có quyền thương mại cho weights. Phương án đã chọn giảm compute trong live nhưng có rủi ro drift, lỗi tay/cơ thể và chi phí sinh clip. License phải kiểm tra theo checkpoint và tài sản cụ thể trước thử nghiệm.

## 6. Thí nghiệm cần thực hiện

### Chuẩn bị dữ liệu và môi trường

Chuẩn bị ít nhất 5 chân dung có quyền, ít nhất 3 seed/người, 2 phong cách và ít nhất 5 motion template theo kế hoạch Stage 03. Kaggle/Colab dùng để thử inference nếu tài nguyên phù hợp; ghi GPU thực được cấp, precision/offload và phiên bản checkpoint. Không khẳng định GPU notebook đủ chạy Wan; lỗi OOM cũng phải được ghi nhận.

Mỗi lượt chạy dùng manifest theo [quy tắc tái lập](../../README.md#5-tái-lập-thí-nghiệm). Các giả thuyết dưới đây là cách diễn đạt để kiểm chứng quyết định Stage 03, **không phải kết quả đã đạt**. Chốt baseline, số lượt lặp và tiêu chí trước khi chạy; báo cả lượt lỗi. Mã Pxx-Eyy giữ theo tài liệu nguồn.

### P01-E01 — Giữ danh tính

- **Mục tiêu và giả thuyết:** Danh tính có thể giữ ổn định qua seed/phong cách.
- **Đầu vào/tình huống và cách làm:** Chạy bộ chân dung × seed × phong cách; đánh giá ẩn tên phương pháp.
- **Đầu ra, metrics và evidence:** Điểm giống danh tính, tỷ lệ loại, thiên lệch theo pose/nhóm dữ liệu; lưu ảnh, seed và phiếu chấm.

### P01-E02 — Thư viện chuyển động

- **Mục tiêu và giả thuyết:** Một tập motion giới hạn có thể nối thành lời dẫn tự nhiên.
- **Đầu vào/tình huống và cách làm:** Chạy ≥5 template; xem riêng rồi nối speaking–idle–speaking.
- **Đầu ra, metrics và evidence:** Tỷ lệ clip dùng được, lỗi nối/10 lần chuyển, điểm chuyển động; lưu chuỗi video và vị trí lỗi.

### P01-E03 — Chi phí tạo clip

- **Mục tiêu và giả thuyết:** Cấu hình GPU có thể tạo clip đạt QC trong ngân sách sẽ được nhóm xác định.
- **Đầu vào/tình huống và cách làm:** Giữ đầu vào cố định, so GPU/config; tính cả warmup, retry và clip bị loại.
- **Đầu ra, metrics và evidence:** P50/P95 thời gian, peak VRAM, OOM, chi phí/clip được duyệt; lưu log và hóa đơn nếu có.

### P01-E04 — Tương thích P03

- **Mục tiêu và giả thuyết:** Clip đạt QC còn phù hợp với MuseTalk.
- **Đầu vào/tình huống và cách làm:** Đưa clip đã duyệt qua P03 với 5 câu tiếng Việt.
- **Đầu ra, metrics và evidence:** Độ ổn định crop, chất lượng môi, tổng chi phí; lưu cặp trước/sau.

### P01-E05 — Chặn nguồn thiếu quyền

- **Mục tiêu và giả thuyết:** Quyền hết hạn/thu hồi ngăn tạo và phát clip liên quan.
- **Đầu vào/tình huống và cách làm:** Dùng quyền mock hết hạn/thu hồi và motion chưa duyệt; quan sát quyết định gate.
- **Đầu ra, metrics và evidence:** Số hành động không hợp lệ phải bằng 0 trong bộ kiểm thử; lưu dấu vết từ chối.

## 7. Đánh giá và tiêu chí chấp nhận

G1 đánh giá danh tính/chuyển động, G6 đánh giá preview/onboarding; ngưỡng fidelity và chất lượng còn phải chốt với reviewer. G4 chặn nguồn thiếu quyền, clip chưa QC/approval và clip đã bị thu hồi quyền kể cả có cache. Nếu chất lượng kém, ghi CHANGE và thử giới hạn motion/góc nhìn; không âm thầm thay danh tính.

Các metric ở mục 6 đo trực tiếp câu hỏi nghiên cứu, phải báo theo từng nhóm đầu vào/cấu hình thay vì chỉ một số trung bình. Phân biệt **ràng buộc đã xác nhận**, **mục tiêu cần benchmark** và **ngưỡng chưa chốt**. Không tự thêm ngưỡng đạt chất lượng hoặc giá. GO chỉ áp dụng cho phạm vi có evidence và reviewer đồng ý; CHANGE khi cần điều chỉnh phương pháp/cấu hình; NO-GO khi vi phạm hard gate. Nếu chưa đủ bằng chứng, ghi INCONCLUSIVE và việc cần làm tiếp. Không dùng điểm chất lượng để bù vi phạm quyền hoặc tính đúng.

## 8. Kết quả cần bàn giao

- Notebook/script nghiên cứu có hướng dẫn chạy lại, cấu hình và dependency versions; đây là đầu ra cần làm sau, chưa được tạo bởi README.
- Manifest, dữ liệu đầu vào có nguồn/quyền và split hoặc kịch bản kiểm thử; log/metrics theo từng mã thí nghiệm ở mục 6.
- Mẫu đầu ra hợp lệ và ví dụ thất bại, rubric/phiếu chấm nếu có đánh giá người thật; asset riêng tư chỉ lưu tham chiếu có kiểm soát.
- Báo cáo so baseline, giới hạn của Kaggle/Colab hoặc mock so với hệ thống thật, lỗi còn mở và khuyến nghị kỹ thuật.
- Kết luận GO/CHANGE/NO-GO hoặc INCONCLUSIVE, phạm vi kết luận, người phụ trách/reviewer và liên kết evidence. Không tạo kết quả giả để điền báo cáo.

## 9. Tích hợp với HOSTRA

P03/P04 chỉ nhận clip đã duyệt, có checksum và rights_version; bảo toàn provenance và cơ chế vô hiệu hóa cache. Các tên contract là tham chiếu thiết kế, chưa khẳng định schema đã có. Khi đủ bằng chứng mới đề xuất chuyển pipeline sang workers/presenter/ qua PR riêng.

### Điểm cần xác minh

Rubric danh tính, độ đa dạng dữ liệu, quyền motion/base-model, GPU khả dụng và tương thích MuseTalk cần người phụ trách và reviewer.

## 10. Tài liệu tham khảo

- [Architecture Baseline v1.2](../../../docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx): §2, §6 WF01, §8.1; D04, D20, D32; ACR-001.
- [Technical Research & PoC Plan v1.0](../../../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx): §4, §5 hồ sơ P01, đặc biệt mục .3/.5/.11–.14; §8–9 về benchmark/evidence, §13–14 về gates và quyết định mở.
- [Technical Risk Assessment v1.1](../../../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx): các mục R01, R09, R11, R13, R14; đọc failure scenario và evidence cần thiết.

Các liên kết ngoài sau được lấy từ hồ sơ Stage 03; đây là điểm bắt đầu đọc nguyên lý và cách chạy, chưa phải xác nhận license, giá hay khả năng tương thích ở thời điểm thực nghiệm:

- [Paper PhotoMaker](https://arxiv.org/abs/2312.04461)
- [Mã nguồn PhotoMaker](https://github.com/TencentARC/PhotoMaker)
- [Model card PhotoMaker](https://huggingface.co/TencentARC/PhotoMaker)
- [Mã nguồn Wan2.2](https://github.com/Wan-Video/Wan2.2)
- [Model card Wan2.2 Animate](https://huggingface.co/Wan-AI/Wan2.2-Animate-14B)
- [Mã nguồn MimicMotion](https://github.com/Tencent/MimicMotion)
- [License weights MimicMotion](https://huggingface.co/tencent/MimicMotion/blob/main/LICENSE)

## 11. Checklist tiến độ nghiên cứu

- [ ] Đọc nguồn và chốt câu hỏi/phạm vi P01, owner và reviewer.
- [ ] Xác minh quyền dữ liệu/model; chuẩn bị bộ test và baseline.
- [ ] Khóa cấu hình, cách đo, rubric và các ngưỡng cần nhóm phê duyệt.
- [ ] Chạy P01-E01, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P01-E02, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P01-E03, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P01-E04, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P01-E05, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Kiểm tra hard gates và đối chiếu dependency/contract với nhóm liên quan.
- [ ] Chạy lại được kết quả, review giới hạn và ghi quyết định có bằng chứng.
