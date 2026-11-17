# Giọng nói tiếng Việt và TTS

[Nhóm nghiên cứu](../README.md) · [Trung tâm experiments](../../README.md)

**Module:** P02 · **Rủi ro:** R02, R03, R09 · **Gate:** G1, G2, G4 · **Mốc tham chiếu:** M1.

**Tiến độ khởi tạo:** NOT STARTED — chưa có evidence chạy thí nghiệm trong thư mục tại lần kiểm kê này. **Quyết định công nghệ:** SELECTED FOR PoC; tính khả thi và các kết quả vẫn TO VALIDATE. Owner/reviewer cần nhóm phân công.

## 1. Tổng quan bài toán

AI cần đọc đúng giá, đơn vị và tên sản phẩm OCOP, đồng thời giữ giọng nhất quán khi chuyển từ kể chuyện sang trả lời bình luận. Phát âm sai con số có thể làm lời tư vấn sai dù text đã đúng. Ảnh chân dung không cung cấp quyền hay dữ liệu để clone giọng.

## 2. Định nghĩa bài toán

- **Đầu vào:** VerifiedSpeechCandidate đã kiểm chứng, locale, style, voice_profile_id, rights_version và deadline.
- **Đầu ra:** AudioArtifact với URI, duration, sample_rate, checksum và metadata request TTS.
- **Yêu cầu chức năng, chất lượng và giới hạn:** Chuẩn hóa số/đơn vị mà không đổi nghĩa; kiểm tra quyền mẫu giọng; đo âm lượng và duration thật. Tách first-byte khỏi thời điểm toàn bộ audio sẵn sàng. Không tự phát audio hoặc suy ra playback completion từ TTS completion.
- **Phụ thuộc:** P05 kiểm tra text, P11 xác minh quyền giọng, P03 dùng audio để lip-sync, P04 dùng audio hợp lệ với cảnh sản phẩm và P08 quản lý deadline.

## 3. Câu hỏi nghiên cứu

- Flash v2.5 đọc đúng giá, đơn vị, tên SKU/địa danh tiếng Việt trong bao nhiêu trường hợp?
- Giọng có nhất quán qua story → trả lời → tiếp tục story không?
- Streaming hay batch cho thời gian audio-ready phù hợp hơn với P03, khi tính cả mạng và chuẩn hóa audio?

## 4. Kiến thức nền cần tìm hiểu

- Text normalization: giữ nguyên giá trị số và nghĩa của câu.
- Prosody và voice identity: phân biệt nhịp điệu bán hàng với thay đổi danh tính giọng.
- Latency API và audio codec: phân biệt first-byte, tải xong, xử lý xong và thời điểm phát.

## 5. Phương pháp và công nghệ

**SELECTED FOR PoC:** ElevenLabs Flash v2.5 với voice clone có quyền. Có thể dùng preset được cấp phép làm baseline trước khi thử clone. TTS tự host chỉ là đối chứng khi cần nghiên cứu chi phí/riêng tư, chưa có checkpoint thay thế được chốt. API giảm công vận hành nhưng cần đo chi phí usage, lỗi phát âm và điều kiện xử lý dữ liệu.

## 6. Thí nghiệm cần thực hiện

### Chuẩn bị dữ liệu và môi trường

Chuẩn bị 100 câu tiếng Việt có đáp án cách đọc, gồm giá, SKU, đơn vị và CTA; 3 phong cách, 3 lượt theo Stage 03. Notebook gọi API không cần mặc định thuê GPU; tách thời gian mạng khỏi xử lý audio. Dùng secret store của môi trường, không in key hoặc voice sample riêng tư ra output công khai.

Mỗi lượt chạy dùng manifest theo [quy tắc tái lập](../../README.md#5-tái-lập-thí-nghiệm). Các giả thuyết dưới đây là cách diễn đạt để kiểm chứng quyết định Stage 03, **không phải kết quả đã đạt**. Chốt baseline, số lượt lặp và tiêu chí trước khi chạy; báo cả lượt lỗi. Mã Pxx-Eyy giữ theo tài liệu nguồn.

### P02-E01 — Phát âm

- **Mục tiêu và giả thuyết:** Chuẩn hóa đầu vào giúp đọc đúng thông tin bán hàng.
- **Đầu vào/tình huống và cách làm:** Chạy 100 câu × 3 phong cách × 3 lượt; người nghe đối chiếu bản đọc chuẩn.
- **Đầu ra, metrics và evidence:** Tỷ lệ lỗi phát âm và điểm nghe kiểu MOS; lưu audio hợp lệ, văn bản chuẩn và loại lỗi.

### P02-E02 — Nhất quán giọng

- **Mục tiêu và giả thuyết:** Voice profile có thể giữ màu giọng xuyên các chế độ.
- **Đầu vào/tình huống và cách làm:** Ghép story → trả lời on-demand → resume cùng profile; chấm mù.
- **Đầu ra, metrics và evidence:** Điểm nhất quán/ngữ điệu; lưu chuỗi audio và phiếu đánh giá.

### P02-E03 — Độ trễ và chi phí

- **Mục tiêu và giả thuyết:** Cấu hình gọi API có thể đáp ứng ngân sách thời gian của pipeline.
- **Đầu vào/tình huống và cách làm:** Đo request cold/warm, first-byte, audio-ready, quota/rate limit và retry.
- **Đầu ra, metrics và evidence:** P50/P95, chi phí/1.000 ký tự, số retry; lưu timestamp và usage.

### P02-E04 — Quyền và thu hồi

- **Mục tiêu và giả thuyết:** Thiếu quyền sẽ chặn clone và chặn commit tiếp theo.
- **Đầu vào/tình huống và cách làm:** Giả lập thiếu chứng cứ giọng và revoke giữa phiên; kiểm tra cả cache.
- **Đầu ra, metrics và evidence:** 0 request clone trái quyền, không commit mới từ quyền cũ; lưu quyết định gate.

## 7. Đánh giá và tiêu chí chấp nhận

G1/G2 cần chất lượng và nhất quán giọng, chưa có ngưỡng điểm nghe cuối cùng. G4 yêu cầu consent riêng cho voice, không gửi mẫu cho provider khi thiếu scope. Audio chưa READY không được commit; timeout cần nội dung đã duyệt hoặc safe scene. Chuyển preset phải theo policy và được merchant chấp thuận.

Các metric ở mục 6 đo trực tiếp câu hỏi nghiên cứu, phải báo theo từng nhóm đầu vào/cấu hình thay vì chỉ một số trung bình. Phân biệt **ràng buộc đã xác nhận**, **mục tiêu cần benchmark** và **ngưỡng chưa chốt**. Không tự thêm ngưỡng đạt chất lượng hoặc giá. GO chỉ áp dụng cho phạm vi có evidence và reviewer đồng ý; CHANGE khi cần điều chỉnh phương pháp/cấu hình; NO-GO khi vi phạm hard gate. Nếu chưa đủ bằng chứng, ghi INCONCLUSIVE và việc cần làm tiếp. Không dùng điểm chất lượng để bù vi phạm quyền hoặc tính đúng.

## 8. Kết quả cần bàn giao

- Notebook/script nghiên cứu có hướng dẫn chạy lại, cấu hình và dependency versions; đây là đầu ra cần làm sau, chưa được tạo bởi README.
- Manifest, dữ liệu đầu vào có nguồn/quyền và split hoặc kịch bản kiểm thử; log/metrics theo từng mã thí nghiệm ở mục 6.
- Mẫu đầu ra hợp lệ và ví dụ thất bại, rubric/phiếu chấm nếu có đánh giá người thật; asset riêng tư chỉ lưu tham chiếu có kiểm soát.
- Báo cáo so baseline, giới hạn của Kaggle/Colab hoặc mock so với hệ thống thật, lỗi còn mở và khuyến nghị kỹ thuật.
- Kết luận GO/CHANGE/NO-GO hoặc INCONCLUSIVE, phạm vi kết luận, người phụ trách/reviewer và liên kết evidence. Không tạo kết quả giả để điền báo cáo.

## 9. Tích hợp với HOSTRA

AudioArtifact chuyển cho P03/P04 cùng voice/version/quyền và duration đo được. Revalidate trước commit vì quyền hoặc nội dung có thể thay sau TTS. Đề xuất workers/voice/ sau khi benchmark và review; không gắn logic playout vào notebook TTS.

### Điểm cần xác minh

Provider region/retention/training-use/DPA, giọng theo vùng, chế độ streaming/batch, mức chi phí và rubric nghe cần xác minh.

## 10. Tài liệu tham khảo

- [Architecture Baseline v1.2](../../../docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx): §6–8; D05, D15; ARD-04, ARD-08.
- [Technical Research & PoC Plan v1.0](../../../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx): §4, §5 hồ sơ P02, đặc biệt mục .3/.5/.11–.14; §8–9 về benchmark/evidence, §13–14 về gates và quyết định mở.
- [Technical Risk Assessment v1.1](../../../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx): các mục R02, R03, R09; đọc failure scenario và evidence cần thiết.

Các liên kết ngoài sau được lấy từ hồ sơ Stage 03; đây là điểm bắt đầu đọc nguyên lý và cách chạy, chưa phải xác nhận license, giá hay khả năng tương thích ở thời điểm thực nghiệm:

- [Các model ElevenLabs](https://elevenlabs.io/docs/overview/models/)
- [Voice cloning ElevenLabs](https://elevenlabs.io/docs/overview/capabilities/voices)
- [Trang giá ElevenLabs](https://elevenlabs.io/pricing/api)
- [SDK ElevenLabs](https://github.com/elevenlabs/elevenlabs-python)

## 11. Checklist tiến độ nghiên cứu

- [ ] Đọc nguồn và chốt câu hỏi/phạm vi P02, owner và reviewer.
- [ ] Xác minh quyền dữ liệu/model; chuẩn bị bộ test và baseline.
- [ ] Khóa cấu hình, cách đo, rubric và các ngưỡng cần nhóm phê duyệt.
- [ ] Chạy P02-E01, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P02-E02, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P02-E03, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P02-E04, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Kiểm tra hard gates và đối chiếu dependency/contract với nhóm liên quan.
- [ ] Chạy lại được kết quả, review giới hạn và ghi quyết định có bằng chứng.
