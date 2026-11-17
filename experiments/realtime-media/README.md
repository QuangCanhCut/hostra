# Luồng phát và trải nghiệm media realtime

[Trở về trung tâm nghiên cứu](../README.md)

**Phạm vi:** P04; phụ thuộc P08/P10/P12. **Trạng thái khởi tạo:** NOT STARTED, chưa có evidence trong các thư mục con; công nghệ vẫn SELECTED FOR PoC.

## Tổng quan và vai trò trong kiến trúc

Nhóm này nghiên cứu luồng video/audio liên tục, chuyển cảnh và độ trễ người xem. Cần phân biệt clip đã tạo, media đã queued, audio đã output và audio thực sự tới thiết bị viewer.

P04 giữ clock, compositor/encoder, commit horizon, publisher health và Playback ACK. P08 chọn lượt; LiveKit phân phối media; P10 nhận trạng thái và cung cấp player. LLM/TTS không được làm đồng hồ phát dừng theo inference.

## Luồng dữ liệu và phụ thuộc

```text
Lệnh P08 + artifact hợp lệ → P04 clock/compositor/encoder
→ LiveKit ingress RTMP/WHIP → WebRTC → viewer P10
P04 output ACK → P08; viewer probe → báo cáo latency riêng
```

- [Đầu vào video/audio](../ai-presenter-media/README.md)
- [Commit và ACK](../conversation-orchestration/README.md)
- [Placement và độ bền](../infrastructure-evaluation/README.md)

P11 cung cấp kiểm tra quyền/tenant; P09 kiểm OCOP và điều kiện SKU, P05 kiểm claims. Các gate này vẫn áp dụng cho media đã cache và fallback. P10 là giao diện/trải nghiệm cần kiểm tra ở bước tích hợp, không tự quyết định LIVE/APPLIED.

## Bài toán con và nơi bắt đầu

| Hướng nghiên cứu | Module | Mục đích |
| --- | --- | --- |
| [Benchmark phát media liên tục](streaming-benchmarks/README.md) | P04 | GStreamer có chuyển host/product/idle 100 lần mà không làm mất clock hoặc drift A/V không? |

README con có định nghĩa input/output, kiến thức cần học, baseline, từng mã experiment và checklist; trang này tập trung vào phối hợp cả nhóm.

## Rủi ro cần theo dõi

**Mapping:** R03, R06, R07, R12.

R07: publisher online nhưng viewer không nghe, lệch hình/tiếng hoặc rớt frame. R06: ACK sớm và phát lặp sau restart. R03: trễ transport cộng thêm sau render. R12: fallback không an toàn hoặc reconnect làm sai timeline.

## Thứ tự tìm hiểu

1. Đọc Stage 01 §8 và Stage 03 P04; chốt định nghĩa server/viewer timestamps.
2. Chạy test bars/fake speech, kiểm scene switch và media clock trước GPU.
3. Đối chiếu ACK với simulator P08 bằng retry/Pause/crash.
4. So RTMP/WHIP cùng profile, rồi nối P03 và đo fallback.
5. Chạy endurance W3 với browser probe và nhóm reliability khi có môi trường dịch vụ.

Đây là thứ tự đọc/thử đề xuất, không phải timeline bắt buộc. Chạy Kaggle/Colab cho phần phù hợp và ghi rõ phần còn mock; không coi notebook thành công là bằng chứng production hoặc live liên tục.

## Kết quả mong đợi

Cấu hình pipeline tái lập, recording/probe, bảng A/V drift/frame drops/latency, ngữ nghĩa Playback ACK đã đối chiếu và khuyến nghị ingress/fallback có bằng chứng.

Báo cáo mỗi kết quả với run ID, cấu hình, dataset/quyền, metric, giới hạn và vị trí evidence. Mọi ngưỡng chưa có trong nguồn phải được chốt trước thử nghiệm. Chỉ đổi trạng thái sau review; đọc [quy trình chung](../README.md) để quản lý branch, PR, dữ liệu và chuyển giao.

## Tài liệu cần đọc

- [Architecture Baseline v1.2](../../docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx).
- [Technical Research & PoC Plan v1.0](../../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx).
- [Technical Risk Assessment v1.1](../../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx): R03, R06, R07, R12.

**Mục nên mở:** Stage 01 §4–5, §7–8, §11; Stage 03 §5 P04, §8, §13; G1/G3/G5 và trải nghiệm P10. Word được dẫn tới file thật; tìm số mục/mã P trong tài liệu, không dùng anchor giả cho DOCX.
