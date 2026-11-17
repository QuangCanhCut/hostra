# Benchmark phát media liên tục

[Nhóm nghiên cứu](../README.md) · [Trung tâm experiments](../../README.md)

**Module:** P04 · **Rủi ro:** R03, R06, R07, R12 · **Gate:** G1, G3, G5 · **Mốc tham chiếu:** M2.

**Tiến độ khởi tạo:** NOT STARTED — chưa có evidence chạy thí nghiệm trong thư mục tại lần kiểm kê này. **Quyết định công nghệ:** SELECTED FOR PoC; tính khả thi và các kết quả vẫn TO VALIDATE. Owner/reviewer cần nhóm phân công.

## 1. Tổng quan bài toán

Luồng phát phải tiếp tục ngay khi AI/TTS/lip-sync chưa tạo xong nội dung. P04 là nơi duy nhất thực thi playout và xác nhận phần audio đã phát; video offline hoặc API Start thành công chưa chứng minh một phiên live hoạt động.

## 2. Định nghĩa bài toán

- **Đầu vào:** PlayoutCommand/turn_id, media đã duyệt, scene plan, commit horizon, versions/epoch và readiness.
- **Đầu ra:** Publisher track, PlaybackStarted/Completed, playback position cùng health/failure events.
- **Yêu cầu chức năng, chất lượng và giới hạn:** Giữ media clock liên tục, compositor/encoder và scene switch đúng boundary. Mục tiêu output 720p, 25–30 FPS; tách server playout khỏi viewer-audible. Không kéo từng frame qua FastAPI và không coi queued buffer là âm thanh đã phát.
- **Phụ thuộc:** P08 quyết định turn; P01/P02/P03 cấp media; P05/P09/P11 kiểm quyền/nội dung/SKU; LiveKit phân phối tới P10 viewer; P12 theo dõi tài nguyên.

## 3. Câu hỏi nghiên cứu

- GStreamer có chuyển host/product/idle 100 lần mà không làm mất clock hoặc drift A/V không?
- RTMP và WHIP khác nhau thế nào về độ trễ tới viewer trên cùng profile?
- ACK được phát từ điểm nào để phản ánh output thật và giúp recovery không phát lại?

## 4. Kiến thức nền cần tìm hiểu

- Codec, timestamps và media clock: hiểu A/V sync và cách tính played_until.
- GStreamer graph/backpressure: tách inference chậm khỏi đường phát.
- RTMP/WHIP/WebRTC và client probe: đo từng phần mạng/encode/player.

## 5. Phương pháp và công nghệ

**SELECTED FOR PoC:** Python Media Controller + GStreamer + LiveKit Cloud, FFmpeg hỗ trợ chuẩn hóa/chuyển đổi. Xuất MP4 offline là baseline chất lượng, không thay live; OBS-centric automation có thể demo nhanh nhưng khó kiểm soát commit/ACK như yêu cầu. RTMP hay WHIP chưa được chốt từ benchmark.

## 6. Thí nghiệm cần thực hiện

### Chuẩn bị dữ liệu và môi trường

Khởi đầu bằng test bars/audio và fake speech có timestamp, chưa cần GPU model. Notebook chỉ hỗ trợ xử lý clip hoặc mô phỏng; continuous publisher, LiveKit và browser probe cần môi trường có mạng/codec phù hợp. Ghi encoder, bitrate, FPS, server/viewer timestamps và cấu hình ingress; không coi disconnect của notebook là lỗi model.

Mỗi lượt chạy dùng manifest theo [quy tắc tái lập](../../README.md#5-tái-lập-thí-nghiệm). Các giả thuyết dưới đây là cách diễn đạt để kiểm chứng quyết định Stage 03, **không phải kết quả đã đạt**. Chốt baseline, số lượt lặp và tiêu chí trước khi chạy; báo cả lượt lỗi. Mã Pxx-Eyy giữ theo tài liệu nguồn.

### P04-E01 — Luồng liên tục

- **Mục tiêu và giả thuyết:** Media clock độc lập giữ được stream khi chuyển cảnh.
- **Đầu vào/tình huống và cách làm:** Chạy 20–30 phút test bars/audio, chuyển cảnh 100 lần.
- **Đầu ra, metrics và evidence:** Frame drops, disconnect, A/V drift; lưu recording và pipeline log.

### P04-E02 — Ngữ nghĩa commit/ACK

- **Mục tiêu và giả thuyết:** ACK có thể bám output thay vì trạng thái queued.
- **Đầu vào/tình huống và cách làm:** Fake clock với Pause/overlap/retry, kiểm tra probe trên đường truyền/player.
- **Đầu ra, metrics và evidence:** 0 duplicate/overlap, played_until đúng; lưu timestamp đối chiếu.

### P04-E03 — RTMP so với WHIP

- **Mục tiêu và giả thuyết:** Có thể lựa chọn ingress từ số đo công bằng.
- **Đầu vào/tình huống và cách làm:** Cùng profile media, đo hai ingress tới cùng điều kiện viewer.
- **Đầu ra, metrics và evidence:** P50/P95 viewer-audible, CPU/bitrate; lưu network/profile và probe.

### P04-E04 — Độ bền

- **Mục tiêu và giả thuyết:** Fallback và reconnect giữ trạng thái đúng khi gặp lỗi.
- **Đầu vào/tình huống và cách làm:** Chạy W3 120 phút, tiêm ít nhất 2 lỗi; kiểm tra recovery.
- **Đầu ra, metrics và evidence:** Continuity, publisher health và recovery; lưu video/event/log lỗi.

## 7. Đánh giá và tiêu chí chấp nhận

G3 chặn overlap, unsafe replay, stale epoch và asset không đủ quyền/gate. G5 kiểm 720p/25–30 FPS như mục tiêu output đã xác nhận; mức đạt thực tế vẫn TO VALIDATE. Không báo LIVE nếu chỉ API thành công. Video trễ dùng product + verified audio; thiếu speech an toàn dùng cảnh trung tính; không còn cảnh hợp lệ thì controlled stop. Ngưỡng drift/drop/recovery và lựa chọn ingress còn mở.

Các metric ở mục 6 đo trực tiếp câu hỏi nghiên cứu, phải báo theo từng nhóm đầu vào/cấu hình thay vì chỉ một số trung bình. Phân biệt **ràng buộc đã xác nhận**, **mục tiêu cần benchmark** và **ngưỡng chưa chốt**. Không tự thêm ngưỡng đạt chất lượng hoặc giá. GO chỉ áp dụng cho phạm vi có evidence và reviewer đồng ý; CHANGE khi cần điều chỉnh phương pháp/cấu hình; NO-GO khi vi phạm hard gate. Nếu chưa đủ bằng chứng, ghi INCONCLUSIVE và việc cần làm tiếp. Không dùng điểm chất lượng để bù vi phạm quyền hoặc tính đúng.

## 8. Kết quả cần bàn giao

- Notebook/script nghiên cứu có hướng dẫn chạy lại, cấu hình và dependency versions; đây là đầu ra cần làm sau, chưa được tạo bởi README.
- Manifest, dữ liệu đầu vào có nguồn/quyền và split hoặc kịch bản kiểm thử; log/metrics theo từng mã thí nghiệm ở mục 6.
- Mẫu đầu ra hợp lệ và ví dụ thất bại, rubric/phiếu chấm nếu có đánh giá người thật; asset riêng tư chỉ lưu tham chiếu có kiểm soát.
- Báo cáo so baseline, giới hạn của Kaggle/Colab hoặc mock so với hệ thống thật, lỗi còn mở và khuyến nghị kỹ thuật.
- Kết luận GO/CHANGE/NO-GO hoặc INCONCLUSIVE, phạm vi kết luận, người phụ trách/reviewer và liên kết evidence. Không tạo kết quả giả để điền báo cáo.

## 9. Tích hợp với HOSTRA

P04 gửi PlaybackEvents theo clock cho P08 và health cho P10/P12. Giữ single playout authority; validate version/epoch trước commit, return host tại speech boundary. Chỉ đề xuất workers/media/ sau khi trace và player probe thống nhất.

### Điểm cần xác minh

Điểm phát ACK, sai lệch tới viewer, codec/ingress, chi phí transcoding và placement cùng/tách MuseTalk cần đo.

## 10. Tài liệu tham khảo

- [Architecture Baseline v1.2](../../../docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx): §4–5, §7–8, §11; D12–D14, D16, D31; ARD-09, ARD-13.
- [Technical Research & PoC Plan v1.0](../../../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx): §4, §5 hồ sơ P04, đặc biệt mục .3/.5/.11–.14; §8–9 về benchmark/evidence, §13–14 về gates và quyết định mở.
- [Technical Risk Assessment v1.1](../../../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx): các mục R03, R06, R07, R12; đọc failure scenario và evidence cần thiết.

Các liên kết ngoài sau được lấy từ hồ sơ Stage 03; đây là điểm bắt đầu đọc nguyên lý và cách chạy, chưa phải xác nhận license, giá hay khả năng tương thích ở thời điểm thực nghiệm:

- [Tài liệu GStreamer](https://gstreamer.freedesktop.org/documentation/)
- [LiveKit Ingress](https://docs.livekit.io/transport/media/ingress-egress/ingress/)
- [Tài liệu FFmpeg](https://ffmpeg.org/documentation.html)
- [Mã nguồn LiveKit](https://github.com/livekit/livekit)
- [Đặc tả WebRTC](https://www.w3.org/TR/webrtc/)

## 11. Checklist tiến độ nghiên cứu

- [ ] Đọc nguồn và chốt câu hỏi/phạm vi P04, owner và reviewer.
- [ ] Xác minh quyền dữ liệu/model; chuẩn bị bộ test và baseline.
- [ ] Khóa cấu hình, cách đo, rubric và các ngưỡng cần nhóm phê duyệt.
- [ ] Chạy P04-E01, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P04-E02, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P04-E03, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P04-E04, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Kiểm tra hard gates và đối chiếu dependency/contract với nhóm liên quan.
- [ ] Chạy lại được kết quả, review giới hạn và ghi quyết định có bằng chứng.
