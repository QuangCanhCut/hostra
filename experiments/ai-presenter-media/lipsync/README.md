# Lip-sync trên clip người dẫn tổng hợp

[Nhóm nghiên cứu](../README.md) · [Trung tâm experiments](../../README.md)

**Module:** P03 · **Rủi ro:** R01, R03, R11, R12 · **Gate:** G1, G2, G5 · **Mốc tham chiếu:** M1/M2.

**Tiến độ khởi tạo:** NOT STARTED — chưa có evidence chạy thí nghiệm trong thư mục tại lần kiểm kê này. **Quyết định công nghệ:** SELECTED FOR PoC; tính khả thi và các kết quả vẫn TO VALIDATE. Owner/reviewer cần nhóm phân công.

## 1. Tổng quan bài toán

P03 sửa khẩu hình clip đã tạo ở P01 cho phù hợp audio mới của P02, để người dẫn có thể trả lời bình luận. Một video đẹp nhưng hoàn tất sau deadline không giải quyết được tương tác live; thất bại phải dẫn đến fallback có kiểm soát.

## 2. Định nghĩa bài toán

- **Đầu vào:** AudioArtifact, PresenterClip đã duyệt, avatar_cache_id, speech_turn_id, deadline và metadata phiên bản/quyền.
- **Đầu ra:** LipSyncVideoArtifact gồm alignment, duration, FPS, checksum, rights/knowledge version; hoặc tín hiệu lỗi/quá hạn.
- **Yêu cầu chức năng, chất lượng và giới hạn:** Preprocess/cache khuôn mặt, render theo deadline, kiểm tra mux và A/V sync. Không tạo body motion mới; không tự chọn quyền phát. Đo toàn bộ audio-ready → video-ready, không chỉ FPS inference.
- **Phụ thuộc:** P01/P02 cung cấp clip/audio; P08 đặt lịch, P04 thực hiện phát/fallback; P12 đánh giá tranh chấp GPU và truyền artifact; P11 kiểm tra quyền.

## 3. Câu hỏi nghiên cứu

- Face crop có ổn định trên video tổng hợp P01, nhất là góc nghiêng và tay che mặt không?
- Audio dài 3/6/10 giây có tỷ lệ trễ deadline khác nhau thế nào ở cold/warm run?
- Cache giúp giảm thời gian bao nhiêu và có làm dùng nhầm identity/version không?

## 4. Kiến thức nền cần tìm hiểu

- Audio-driven animation và latent inpainting: hiểu vùng model sửa và nguy cơ biến dạng.
- Face detection/crop/mask/cache: ảnh hưởng trực tiếp tới độ ổn định của môi.
- Timebase, mux và deadline: output inference xong chưa phải artifact sẵn sàng phát.

## 5. Phương pháp và công nghệ

**SELECTED FOR PoC:** MuseTalk 1.5, preprocess avatar có cache và render theo deadline. Baseline pre-render toàn bộ câu nói giúp đối chiếu chất lượng nhưng không xử lý được câu hỏi mới. Model lip-sync khác chưa được chọn; không coi LatentSync là quyết định đã chốt. Cache giảm xử lý lặp nhưng phải gắn identity/clip/version.

## 6. Thí nghiệm cần thực hiện

### Chuẩn bị dữ liệu và môi trường

Dùng ≥5 clip P01 × ≥5 audio có quyền; thêm câu 3/6/10 giây, cùng FPS/codec và profile đầu ra. Kaggle/Colab phù hợp đo render offline; lưu GPU, warmup, crop, batch, seed nếu áp dụng. Mô phỏng deadline phải ghi rõ là mô phỏng; chưa thay phép đo live.

Mỗi lượt chạy dùng manifest theo [quy tắc tái lập](../../README.md#5-tái-lập-thí-nghiệm). Các giả thuyết dưới đây là cách diễn đạt để kiểm chứng quyết định Stage 03, **không phải kết quả đã đạt**. Chốt baseline, số lượt lặp và tiêu chí trước khi chạy; báo cả lượt lỗi. Mã Pxx-Eyy giữ theo tài liệu nguồn.

### P03-E01 — Tương thích clip tổng hợp

- **Mục tiêu và giả thuyết:** MuseTalk giữ được danh tính trên clip P01.
- **Đầu vào/tình huống và cách làm:** Chạy ma trận ≥5 clip × ≥5 audio; kiểm tra crop và biến dạng.
- **Đầu ra, metrics và evidence:** Điểm tự nhiên môi, drift, lỗi tracking; lưu cặp input/output và đánh dấu khung lỗi.

### P03-E02 — Deadline

- **Mục tiêu và giả thuyết:** Warm model và cache có thể giảm tỷ lệ render trễ.
- **Đầu vào/tình huống và cách làm:** So cold/warm với câu 3/6/10 giây; tính cả mux và chuyển artifact.
- **Đầu ra, metrics và evidence:** P50/P95 audio-ready → video-ready, tỷ lệ miss deadline; lưu timeline và config.

### P03-E03 — Đồng bộ và nối cảnh

- **Mục tiêu và giả thuyết:** Clip sau mux có thể chuyển speaking–idle–speaking ổn định.
- **Đầu vào/tình huống và cách làm:** Tạo 3 chuỗi, kiểm tra video và bản ghi trình duyệt ở bước tích hợp.
- **Đầu ra, metrics và evidence:** Độ lệch A/V theo ms, số lỗi nối, jitter; lưu recording và phương pháp đo.

### P03-E04 — Fallback

- **Mục tiêu và giả thuyết:** Video trễ không bị phát lại hoặc chồng với câu khác.
- **Đầu vào/tình huống và cách làm:** Cố tình trì hoãn render; theo dõi audio/cảnh được chọn trong mô phỏng rồi tích hợp P04.
- **Đầu ra, metrics và evidence:** 0 commit video quá hạn, 0 chồng tiếng; lưu sự kiện và timeline cảnh.

## 7. Đánh giá và tiêu chí chấp nhận

G1 đánh giá môi/danh tính; G2/G5 đánh giá deadline và trải nghiệm. Ngưỡng chất lượng môi, A/V offset và tỷ lệ fallback còn cần chốt. Sai identity/quyền, worker epoch cũ hay video quá hạn không được phát. Nếu audio hợp lệ nhưng video trễ, P04 chuyển PRODUCT_SHOWCASE trước audio; thiếu audio an toàn thì SAFE_FALLBACK. Không quay lại host giữa câu.

Các metric ở mục 6 đo trực tiếp câu hỏi nghiên cứu, phải báo theo từng nhóm đầu vào/cấu hình thay vì chỉ một số trung bình. Phân biệt **ràng buộc đã xác nhận**, **mục tiêu cần benchmark** và **ngưỡng chưa chốt**. Không tự thêm ngưỡng đạt chất lượng hoặc giá. GO chỉ áp dụng cho phạm vi có evidence và reviewer đồng ý; CHANGE khi cần điều chỉnh phương pháp/cấu hình; NO-GO khi vi phạm hard gate. Nếu chưa đủ bằng chứng, ghi INCONCLUSIVE và việc cần làm tiếp. Không dùng điểm chất lượng để bù vi phạm quyền hoặc tính đúng.

## 8. Kết quả cần bàn giao

- Notebook/script nghiên cứu có hướng dẫn chạy lại, cấu hình và dependency versions; đây là đầu ra cần làm sau, chưa được tạo bởi README.
- Manifest, dữ liệu đầu vào có nguồn/quyền và split hoặc kịch bản kiểm thử; log/metrics theo từng mã thí nghiệm ở mục 6.
- Mẫu đầu ra hợp lệ và ví dụ thất bại, rubric/phiếu chấm nếu có đánh giá người thật; asset riêng tư chỉ lưu tham chiếu có kiểm soát.
- Báo cáo so baseline, giới hạn của Kaggle/Colab hoặc mock so với hệ thống thật, lỗi còn mở và khuyến nghị kỹ thuật.
- Kết luận GO/CHANGE/NO-GO hoặc INCONCLUSIVE, phạm vi kết luận, người phụ trách/reviewer và liên kết evidence. Không tạo kết quả giả để điền báo cáo.

## 9. Tích hợp với HOSTRA

P03 chỉ báo artifact READY hoặc lỗi; P08/P04 revalidate và commit. TTS/render completion không phải PlaybackCompleted. Giữ nguyên metadata version, alignment, epoch/deadline trong adapter đề xuất cho workers/lipsync/.

### Điểm cần xác minh

Crop tối ưu, chunk duration, ngưỡng chất lượng, mức cache và placement chung/tách GStreamer cần benchmark.

## 10. Tài liệu tham khảo

- [Architecture Baseline v1.2](../../../docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx): §7–8; D12, D14, D27; ARD-08, ARD-13.
- [Technical Research & PoC Plan v1.0](../../../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx): §4, §5 hồ sơ P03, đặc biệt mục .3/.5/.11–.14; §8–9 về benchmark/evidence, §13–14 về gates và quyết định mở.
- [Technical Risk Assessment v1.1](../../../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx): các mục R01, R03, R11, R12; đọc failure scenario và evidence cần thiết.

Các liên kết ngoài sau được lấy từ hồ sơ Stage 03; đây là điểm bắt đầu đọc nguyên lý và cách chạy, chưa phải xác nhận license, giá hay khả năng tương thích ở thời điểm thực nghiệm:

- [Mã nguồn MuseTalk](https://github.com/TMElyralab/MuseTalk)
- [Paper MuseTalk](https://arxiv.org/abs/2410.10122)
- [License MuseTalk](https://github.com/TMElyralab/MuseTalk/blob/main/LICENSE)
- [Tài liệu FFmpeg](https://ffmpeg.org/documentation.html)

## 11. Checklist tiến độ nghiên cứu

- [ ] Đọc nguồn và chốt câu hỏi/phạm vi P03, owner và reviewer.
- [ ] Xác minh quyền dữ liệu/model; chuẩn bị bộ test và baseline.
- [ ] Khóa cấu hình, cách đo, rubric và các ngưỡng cần nhóm phê duyệt.
- [ ] Chạy P03-E01, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P03-E02, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P03-E03, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P03-E04, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Kiểm tra hard gates và đối chiếu dependency/contract với nhóm liên quan.
- [ ] Chạy lại được kết quả, review giới hạn và ghi quyết định có bằng chứng.
