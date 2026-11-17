# Điều phối hội thoại và phiên live

[Trở về trung tâm nghiên cứu](../README.md)

**Phạm vi:** P08/P09. **Trạng thái khởi tạo:** NOT STARTED, chưa có evidence trong các thư mục con; công nghệ vẫn SELECTED FOR PoC.

## Tổng quan và vai trò trong kiến trúc

Nhóm này nghiên cứu tính đúng của quyết định phát: chọn câu nào, lúc nào, với SKU và phiên bản nào. Simulator cho phép thử các chuỗi sự kiện khó lặp bằng tay trước khi tốn GPU hoặc vận hành live thật.

P08/P09 là một logical owner cho session, Active SKU và command revision. P08 điều phối; P04 là single playout authority. PostgreSQL giữ state/event/outbox, Redis vận chuyển; không đồng nhất hai loại ACK.

## Luồng dữ liệu và phụ thuộc

```text
P07 task + P06 candidate + P09 command + P04 ACK
→ P08/P09 guarded FSM (revision/epoch, queue, TTL, fairness)
→ recheck P05/P09/P11 tại safe boundary → P04 commit
→ PlaybackCompleted → checkpoint/lịch sử; P10 hiển thị snapshot
```

- [Media clock và Playback ACK](../realtime-media/README.md)
- [Task và candidate](../sales-intelligence/README.md)
- [Replay và fault injection](../infrastructure-evaluation/reliability-tests/README.md)

P11 cung cấp kiểm tra quyền/tenant; P09 kiểm OCOP và điều kiện SKU, P05 kiểm claims. Các gate này vẫn áp dụng cho media đã cache và fallback. P10 là giao diện/trải nghiệm cần kiểm tra ở bước tích hợp, không tự quyết định LIVE/APPLIED.

## Bài toán con và nơi bắt đầu

| Hướng nghiên cứu | Module | Mục đích |
| --- | --- | --- |
| [Mô phỏng điều phối hội thoại và trạng thái phiên](scheduling-simulation/README.md) | P08/P09 | Duplicate, out-of-order và crash có tạo double commit hoặc checkpoint đi trước playback không? |

README con có định nghĩa input/output, kiến thức cần học, baseline, từng mã experiment và checklist; trang này tập trung vào phối hợp cả nhóm.

## Rủi ro cần theo dõi

**Mapping:** R03, R04, R06, R08, R10, R12, R14–R17.

R06/R15: mô tả kiến trúc không chứng minh simulator hoặc recovery đã đúng. R03/R04: queue chậm hoặc bỏ đói story. R08/R16/R17: đổi SKU/giá/eligibility sau prepare. R10: tenant khác điều khiển phiên. R12: crash rồi replay một câu đã phát; R14: UI báo áp dụng trước thực tế.

## Thứ tự tìm hiểu

1. Đọc ownership và invariants Stage 01 §5.2/§7, Stage 03 §2 và P08/P09.
2. Liệt kê state/command và expected outcome; dùng fake clock trước services thật.
3. Thử duplicate/out-of-order, Pause/Stop, SKU-switch và crash/epoch.
4. Đối chiếu ACK với nhóm P04; sau đó replay PostgreSQL/Redis thật.
5. Đưa negative OCOP/rights/tenant vào start/switch/commit cùng P05/P11.

Đây là thứ tự đọc/thử đề xuất, không phải timeline bắt buộc. Chạy Kaggle/Colab cho phần phù hợp và ghi rõ phần còn mock; không coi notebook thành công là bằng chứng production hoặc live liên tục.

## Kết quả mong đợi

Transition matrix, kịch bản/event replay, dấu vết seed tái lập lỗi, boundary/ACK contract và báo cáo invariants/fairness/recovery. Kết quả simulator không tự chứng minh độ trễ media tới viewer.

Báo cáo mỗi kết quả với run ID, cấu hình, dataset/quyền, metric, giới hạn và vị trí evidence. Mọi ngưỡng chưa có trong nguồn phải được chốt trước thử nghiệm. Chỉ đổi trạng thái sau review; đọc [quy trình chung](../README.md) để quản lý branch, PR, dữ liệu và chuyển giao.

## Tài liệu cần đọc

- [Architecture Baseline v1.2](../../docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx).
- [Technical Research & PoC Plan v1.0](../../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx).
- [Technical Risk Assessment v1.1](../../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx): R03, R04, R06, R08, R10, R12, R14–R17.

**Mục nên mở:** Stage 01 §5–7, §9; Stage 03 §5 P08/P09, §6 về runtime, §7 về OCOP, §13 gates. Word được dẫn tới file thật; tìm số mục/mã P trong tài liệu, không dùng anchor giả cho DOCX.
