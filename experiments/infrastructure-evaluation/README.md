# Tài nguyên, chi phí và độ tin cậy

[Trở về trung tâm nghiên cứu](../README.md)

**Phạm vi:** P12/P13; kiểm tra xuyên P01–P11. **Trạng thái khởi tạo:** NOT STARTED, chưa có evidence trong các thư mục con; công nghệ vẫn SELECTED FOR PoC.

## Tổng quan và vai trò trong kiến trúc

Nhóm này kiểm tra phương án có chạy được trên tài nguyên thực và tiếp tục an toàn khi lỗi hay không. Phải tính chi phí trên đầu ra dùng được, đồng thời nối kết quả từng module với bằng chứng toàn phiên.

P12 đánh giá pre-live GPU, warm live GPU, placement/monitoring/cost; P13 tổ chức replay, human QA và gate evidence. Không thay thế owner từng module hoặc biến điểm benchmark thành quyền phê duyệt pilot.

## Luồng dữ liệu và phụ thuộc

```text
Job P01/P03 + workload P04/P08 → ma trận GPU/placement → latency/VRAM/cost
Events/faults + artifacts P01–P11 → P13 replay/human QA → evidence G1–G6
Evidence + reviewer → GO/CHANGE/NO-GO hoặc INCONCLUSIVE
```

- [Workload inference](../ai-presenter-media/README.md)
- [Encoding và viewer probe](../realtime-media/README.md)
- [Replay trạng thái](../conversation-orchestration/README.md)

P11 cung cấp kiểm tra quyền/tenant; P09 kiểm OCOP và điều kiện SKU, P05 kiểm claims. Các gate này vẫn áp dụng cho media đã cache và fallback. P10 là giao diện/trải nghiệm cần kiểm tra ở bước tích hợp, không tự quyết định LIVE/APPLIED.

## Bài toán con và nơi bắt đầu

| Hướng nghiên cứu | Module | Mục đích |
| --- | --- | --- |
| [Đánh giá GPU, placement và chi phí](gpu-benchmarks/README.md) | P12 | Wan tạo clip được duyệt tốn thời gian/VRAM/chi phí bao nhiêu khi tính cả clip bị loại? |
| [Độ tin cậy, phục hồi và bằng chứng nghiệm thu](reliability-tests/README.md) | P12/P13 | Sau crash giữa playback, hệ thống có reconcile mà không phát lặp/chồng không? |

README con có định nghĩa input/output, kiến thức cần học, baseline, từng mã experiment và checklist; trang này tập trung vào phối hợp cả nhóm.

## Rủi ro cần theo dõi

**Mapping:** R01–R18; trọng tâm R03, R06–R12, R15–R17.

R11: OOM, warm/idle/retry làm sai dự toán; R03/R07: tranh chấp encoder và truyền mạng. R06/R12: recovery phát lặp hoặc cache stale. R09/R10/R16/R17: fallback vượt gate quyền/tenant/OCOP/claims. R15: coi thiết kế là implementation; các rủi ro còn lại cần evidence từ track sở hữu.

## Thứ tự tìm hiểu

1. Đọc Stage 03 §8–9, §12–14 và risk register.
2. Định nghĩa manifest/workload và timestamp chung với P01/P03/P04.
3. Chạy gpu-benchmarks cho inference; phân biệt dữ liệu notebook với provider thật.
4. Dùng reliability-tests chạy fake-clock/negative suite trước fault tích hợp.
5. Tổng hợp bill, human QA, W1/W3 và sign-off theo từng gate; thiếu bằng chứng giữ trạng thái mở.

Đây là thứ tự đọc/thử đề xuất, không phải timeline bắt buộc. Chạy Kaggle/Colab cho phần phù hợp và ghi rõ phần còn mock; không coi notebook thành công là bằng chứng production hoặc live liên tục.

## Kết quả mong đợi

Ma trận GPU/placement, cost ledger, logs/metrics có provenance, fault/recovery reports, rubric/phiếu chấm và bảng evidence risk→experiment→gate. Chưa có giá, cấu hình thắng hay kết luận đạt được mặc định.

Báo cáo mỗi kết quả với run ID, cấu hình, dataset/quyền, metric, giới hạn và vị trí evidence. Mọi ngưỡng chưa có trong nguồn phải được chốt trước thử nghiệm. Chỉ đổi trạng thái sau review; đọc [quy trình chung](../README.md) để quản lý branch, PR, dữ liệu và chuyển giao.

## Tài liệu cần đọc

- [Architecture Baseline v1.2](../../docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx).
- [Technical Research & PoC Plan v1.0](../../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx).
- [Technical Risk Assessment v1.1](../../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx): R01–R18; trọng tâm R03, R06–R12, R15–R17.

**Mục nên mở:** Stage 01 §10–12; Stage 03 §5 P12/P13, §8–14; G1–G6. Word được dẫn tới file thật; tìm số mục/mã P trong tài liệu, không dùng anchor giả cho DOCX.
