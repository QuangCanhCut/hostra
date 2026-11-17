# Mô phỏng điều phối hội thoại và trạng thái phiên

[Nhóm nghiên cứu](../README.md) · [Trung tâm experiments](../../README.md)

**Module:** P08/P09 · **Rủi ro:** R03, R04, R06, R08, R10, R12, R14, R15, R16, R17 · **Gate:** G2, G3, G4, G5, G6 · **Mốc tham chiếu:** M3/M4.

**Tiến độ khởi tạo:** NOT STARTED — chưa có evidence chạy thí nghiệm trong thư mục tại lần kiểm kê này. **Quyết định công nghệ:** SELECTED FOR PoC; tính khả thi và các kết quả vẫn TO VALIDATE. Owner/reviewer cần nhóm phân công.

## 1. Tổng quan bài toán

HOSTRA phải vừa kể chuyện vừa chuẩn bị câu trả lời mà không ngắt giữa ý, phát hai câu cùng lúc hoặc chuyển overlay sang SKU mới khi audio còn nói SKU cũ. Mô phỏng giúp kiểm tra quyền cập nhật state, lịch phát và phục hồi trước khi ghép GPU thật.

## 2. Định nghĩa bài toán

- **Đầu vào:** CommentTask, VerifiedSpeechCandidate, MediaArtifactReady, merchant commands, quyền/eligibility, expected_revision và PlaybackEvents.
- **Đầu ra:** PlayoutCommand, SessionState/SessionSnapshot có revision, StoryCheckpoint, ProductContext và command ACCEPTED/REJECTED/APPLIED cùng event trail.
- **Yêu cầu chức năng, chất lượng và giới hạn:** P08/P09 chung một logical state owner; PostgreSQL là system of record, Redis Streams là transport. Quản lý session/AI/SpeechTurn FSM, TTL/fairness/semantic breakpoint và commit horizon. Chỉ PlaybackCompleted cập nhật lịch sử lời đã phát; Stop và safety override ưu tiên hơn story.
- **Phụ thuộc:** P07 cấp task, P05/P11 cấp kiểm tra claims/quyền, P09 kiểm OCOP/food eligibility, P04 sở hữu playout clock/ACK; P10 chỉ chiếu trạng thái đã xác nhận.

## 3. Câu hỏi nghiên cứu

- Duplicate, out-of-order và crash có tạo double commit hoặc checkpoint đi trước playback không?
- Chuẩn bị TTS chậm trong lúc đang nói có giữ được fairness và điểm ngắt đúng nghĩa không?
- Hai lệnh cùng revision hoặc đổi SKU lúc đang nói có gây lost update/sai overlay không?

## 4. Kiến thức nền cần tìm hiểu

- Event-driven FSM và guarded transition: mô tả hành vi có thể kiểm thử bằng fake clock.
- Transaction/outbox, idempotency và epoch fencing: retry transport không được tạo tác động nghiệp vụ lặp.
- Media ACK và reconciliation: phân biệt chưa biết đã phát với chắc chắn chưa phát.
- OCOP/food eligibility và tenant isolation: command hợp lệ còn phải đúng quyền và đúng thời điểm.

## 5. Phương pháp và công nghệ

**SELECTED FOR PoC:** Python Enum/Pydantic/guarded FSM + PostgreSQL + Redis Streams, versioned commands và safe-boundary application. In-process queue là baseline đơn giản cho simulator nhưng chưa chứng minh durable recovery. Temporal là đối chứng, chưa được chọn; CRUD đổi Active SKU ngay lập tức chỉ làm rõ failure case. Không tách P09 thành writer cạnh tranh với P08.

## 6. Thí nghiệm cần thực hiện

### Chuẩn bị dữ liệu và môi trường

Bắt đầu bằng fake media clock và mock P05/P11/P04 có version, ghi seed cho event permutations; chạy CPU/local hoặc notebook. Sau đó replay trên PostgreSQL/Redis thật ở môi trường phù hợp. Mock OCOP pending/expired/revoked và tenant khác; dữ liệu giả không chứng minh việc xác thực hồ sơ OCOP thật.

Mỗi lượt chạy dùng manifest theo [quy tắc tái lập](../../README.md#5-tái-lập-thí-nghiệm). Các giả thuyết dưới đây là cách diễn đạt để kiểm chứng quyết định Stage 03, **không phải kết quả đã đạt**. Chốt baseline, số lượt lặp và tiêu chí trước khi chạy; báo cả lượt lỗi. Mã Pxx-Eyy giữ theo tài liệu nguồn.

### P08-E01 — Tính đúng của state

- **Mục tiêu và giả thuyết:** Guarded FSM loại được transition/commit bất hợp lệ.
- **Đầu vào/tình huống và cách làm:** Sinh thứ tự Stop/Pause/ACK/video trễ ngẫu nhiên và replay cùng seed.
- **Đầu ra, metrics và evidence:** 0 transition sai/double commit; lưu sequence tối giản gây lỗi.

### P08-E02 — Chuẩn bị khi đang nói

- **Mục tiêu và giả thuyết:** Chuẩn bị song song không cần cắt ngang câu.
- **Đầu vào/tình huống và cách làm:** Mock TTS/lip-sync chậm và batch bình luận; thông số 3 câu/20 giây trong tài liệu chỉ là ví dụ.
- **Đầu ra, metrics và evidence:** Ngắt giữa câu, airtime và fairness; lưu lịch prepare/commit/play.

### P08-E03 — Crash và epoch

- **Mục tiêu và giả thuyết:** Worker cũ không được phát lại sau restart.
- **Đầu vào/tình huống và cách làm:** Restart giữa playback, lặp Redis event, chuyển epoch và query P04.
- **Đầu ra, metrics và evidence:** Không replay turn chưa rõ outcome, chặn epoch cũ; lưu recovery trace.

### P08-E04 — Resume và SKU tham chiếu

- **Mục tiêu và giả thuyết:** Câu hỏi về B không tự đổi Active SKU A.
- **Đầu vào/tình huống và cách làm:** Đang kể A, trả lời tham chiếu B rồi tiếp tục story.
- **Đầu ra, metrics và evidence:** Active SKU/checkpoint đúng; lưu snapshot và ACK.

### P09-E01 — Lệnh đồng thời

- **Mục tiêu và giả thuyết:** Revision/idempotency ngăn lost update và áp dụng trùng.
- **Đầu vào/tình huống và cách làm:** Hai lệnh cùng revision, lặp command ID; kiểm tra quyết định.
- **Đầu ra, metrics và evidence:** Không lost update, một tác động nghiệp vụ; lưu command ledger.

### P09-E02 — Chuyển SKU đang nói

- **Mục tiêu và giả thuyết:** APPLIED chỉ xảy ra sau boundary và scene đồng bộ.
- **Đầu vào/tình huống và cách làm:** Yêu cầu A→B giữa câu đọc giá A, quan sát scene/audio.
- **Đầu ra, metrics và evidence:** 0 mismatch SKU overlay/audio; lưu timeline.

### P09-E03 — Hồ sơ OCOP lỗi

- **Mục tiêu và giả thuyết:** Eligibility không bị cấp từ chứng cứ sai hoặc hết hiệu lực.
- **Đầu vào/tình huống và cách làm:** Thử logo giả, sai SKU/chủ thể, hết hạn/thu hồi; đối chiếu kết quả review.
- **Đầu ra, metrics và evidence:** 0 false VERIFIED/eligible trong suite; lưu nguồn/decision.

### P09-E04 — Lease và tenant

- **Mục tiêu và giả thuyết:** Một runtime lease và kiểm tra actor ngăn chiếm phiên.
- **Đầu vào/tình huống và cách làm:** Hai phiên tranh lease; tenant khác gửi Stop; lặp epoch cũ.
- **Đầu ra, metrics và evidence:** Một live lease, 0 tác động trái quyền; lưu authorization/lease trace.

## 7. Đánh giá và tiêu chí chấp nhận

G3 yêu cầu không overlap/double play/unsafe replay; G4 chặn claims/quyền/OCOP/tenant sai. Không coi Redis XACK hay render done là PlaybackCompleted. Pending hồ sơ nghĩa là chưa đủ chứng cứ, không mặc định hồ sơ giả. Khi state chưa rõ phải reconcile và safe scene; Redis lỗi chặn commit mới. Commit horizon, TTL/fairness và thứ tự supersede lệnh còn phải chốt.

Các metric ở mục 6 đo trực tiếp câu hỏi nghiên cứu, phải báo theo từng nhóm đầu vào/cấu hình thay vì chỉ một số trung bình. Phân biệt **ràng buộc đã xác nhận**, **mục tiêu cần benchmark** và **ngưỡng chưa chốt**. Không tự thêm ngưỡng đạt chất lượng hoặc giá. GO chỉ áp dụng cho phạm vi có evidence và reviewer đồng ý; CHANGE khi cần điều chỉnh phương pháp/cấu hình; NO-GO khi vi phạm hard gate. Nếu chưa đủ bằng chứng, ghi INCONCLUSIVE và việc cần làm tiếp. Không dùng điểm chất lượng để bù vi phạm quyền hoặc tính đúng.

## 8. Kết quả cần bàn giao

- Notebook/script nghiên cứu có hướng dẫn chạy lại, cấu hình và dependency versions; đây là đầu ra cần làm sau, chưa được tạo bởi README.
- Manifest, dữ liệu đầu vào có nguồn/quyền và split hoặc kịch bản kiểm thử; log/metrics theo từng mã thí nghiệm ở mục 6.
- Mẫu đầu ra hợp lệ và ví dụ thất bại, rubric/phiếu chấm nếu có đánh giá người thật; asset riêng tư chỉ lưu tham chiếu có kiểm soát.
- Báo cáo so baseline, giới hạn của Kaggle/Colab hoặc mock so với hệ thống thật, lỗi còn mở và khuyến nghị kỹ thuật.
- Kết luận GO/CHANGE/NO-GO hoặc INCONCLUSIVE, phạm vi kết luận, người phụ trách/reviewer và liên kết evidence. Không tạo kết quả giả để điền báo cáo.

## 9. Tích hợp với HOSTRA

Đối chiếu P04 ACK thật trước tích hợp; P08/P09 giữ single writer, revision/epoch, transaction/outbox và command ledger. P10 nhận APPLIED từ backend sau xác nhận boundary. Chuyển logic đã review sang modules conversation/sessions và contracts chung, không đưa model inference vào FSM.

### Điểm cần xác minh

Ngữ nghĩa ACK thực, độ dài horizon, chính sách lệnh đồng thời và phạm vi nguồn OCOP/food review cần chốt với owner.

## 10. Tài liệu tham khảo

- [Architecture Baseline v1.2](../../../docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx): §5.2, §6–7, §9; D10, D16–D18; ARD-01, ARD-06, ARD-07, ARD-16; ACR-002.
- [Technical Research & PoC Plan v1.0](../../../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx): §4, §5 hồ sơ P08/P09, đặc biệt mục .3/.5/.11–.14; §8–9 về benchmark/evidence, §13–14 về gates và quyết định mở.
- [Technical Risk Assessment v1.1](../../../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx): các mục R03, R04, R06, R08, R10, R12, R14, R15, R16, R17; đọc failure scenario và evidence cần thiết.

Các liên kết ngoài sau được lấy từ hồ sơ Stage 03; đây là điểm bắt đầu đọc nguyên lý và cách chạy, chưa phải xác nhận license, giá hay khả năng tương thích ở thời điểm thực nghiệm:

- [Redis Streams](https://redis.io/docs/latest/develop/data-types/streams/)
- [PostgreSQL transactions](https://www.postgresql.org/docs/current/transaction-iso.html)
- [Mã nguồn pytransitions](https://github.com/pytransitions/transitions)
- [Mã nguồn Temporal Python](https://github.com/temporalio/sdk-python)
- [NIST RBAC](https://csrc.nist.gov/projects/role-based-access-control)

## 11. Checklist tiến độ nghiên cứu

- [ ] Đọc nguồn và chốt câu hỏi/phạm vi P08/P09, owner và reviewer.
- [ ] Xác minh quyền dữ liệu/model; chuẩn bị bộ test và baseline.
- [ ] Khóa cấu hình, cách đo, rubric và các ngưỡng cần nhóm phê duyệt.
- [ ] Chạy P08-E01, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P08-E02, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P08-E03, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P08-E04, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P09-E01, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P09-E02, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P09-E03, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P09-E04, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Kiểm tra hard gates và đối chiếu dependency/contract với nhóm liên quan.
- [ ] Chạy lại được kết quả, review giới hạn và ghi quyết định có bằng chứng.
