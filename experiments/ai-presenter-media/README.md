# Người dẫn AI, giọng nói và khẩu hình

[Trở về trung tâm nghiên cứu](../README.md)

**Phạm vi:** P01–P03. **Trạng thái khởi tạo:** NOT STARTED, chưa có evidence trong các thư mục con; công nghệ vẫn SELECTED FOR PoC.

## Tổng quan và vai trò trong kiến trúc

Nhóm này nghiên cứu cách biến một ảnh chân dung có quyền thành người dẫn có chuyển động, giọng tiếng Việt và khẩu hình phù hợp cho live bán hàng. Giá trị cần chứng minh là hình ảnh/giọng nhất quán và khả năng chuẩn bị câu trả lời đúng hạn, không chỉ tạo một video đẹp.

P01 tạo hình và motion offline; P02 tạo audio từ text đã kiểm chứng; P03 lip-sync clip theo audio mới. P04 ở nhóm realtime-media mới sở hữu quyền phát. Không có bước sinh full-body theo mỗi bình luận trong MVP.

## Luồng dữ liệu và phụ thuộc

```text
Ảnh + quyền/motion → P01 → clip đã QC/duyệt → P03
Text đã qua P05 + quyền giọng → P02 → audio → P03
P03 READY hoặc timeout → P08/P04 → host hoặc product + verified audio
```

- [Phát media và fallback](../realtime-media/README.md)
- [GPU và chi phí](../infrastructure-evaluation/gpu-benchmarks/README.md)

P11 cung cấp kiểm tra quyền/tenant; P09 kiểm OCOP và điều kiện SKU, P05 kiểm claims. Các gate này vẫn áp dụng cho media đã cache và fallback. P10 là giao diện/trải nghiệm cần kiểm tra ở bước tích hợp, không tự quyết định LIVE/APPLIED.

## Bài toán con và nơi bắt đầu

| Hướng nghiên cứu | Module | Mục đích |
| --- | --- | --- |
| [Tạo người dẫn từ một ảnh chân dung](presenter-generation/README.md) | P01 | Một ảnh có giữ được danh tính qua các seed, phong cách và góc nhìn khác nhau không? |
| [Giọng nói tiếng Việt và TTS](voice-tts/README.md) | P02 | Flash v2.5 đọc đúng giá, đơn vị, tên SKU/địa danh tiếng Việt trong bao nhiêu trường hợp? |
| [Lip-sync trên clip người dẫn tổng hợp](lipsync/README.md) | P03 | Face crop có ổn định trên video tổng hợp P01, nhất là góc nghiêng và tay che mặt không? |

README con có định nghĩa input/output, kiến thức cần học, baseline, từng mã experiment và checklist; trang này tập trung vào phối hợp cả nhóm.

## Rủi ro cần theo dõi

**Mapping:** R01–R03, R09, R11–R14.

R01/R02: drift mặt, lỗi tay, khẩu hình và phát âm sai. R03/R11: render không kịp, GPU tranh chấp, chi phí clip bị loại. R09: quyền ảnh không bao gồm quyền giọng/motion; cache cũng chịu revoke. R13/R14: preview/onboarding có thể không đủ thuyết phục hoặc quá khó.

## Thứ tự tìm hiểu

1. Đọc ACR-001 và phạm vi D04/D12/D20/D32 trong kiến trúc.
2. Bắt đầu P01 bằng ảnh → still → một clip có quyền; P02 có thể thử preset hợp lệ độc lập.
3. Đưa clip P01 và audio P02 sang P03 sớm để phát hiện crop/identity không tương thích.
4. Đối chiếu benchmark GPU với P12 và fallback với P04/P08; chưa kết luận end-to-end từ notebook.

Đây là thứ tự đọc/thử đề xuất, không phải timeline bắt buộc. Chạy Kaggle/Colab cho phần phù hợp và ghi rõ phần còn mock; không coi notebook thành công là bằng chứng production hoặc live liên tục.

## Kết quả mong đợi

Thư viện mẫu có quyền, QC/rubric và lỗi tiêu biểu; audio test tiếng Việt; bảng render/VRAM/chi phí; manifest giao P03/P04 và khuyến nghị phạm vi motion/giọng/chunk duration dựa trên evidence.

Báo cáo mỗi kết quả với run ID, cấu hình, dataset/quyền, metric, giới hạn và vị trí evidence. Mọi ngưỡng chưa có trong nguồn phải được chốt trước thử nghiệm. Chỉ đổi trạng thái sau review; đọc [quy trình chung](../README.md) để quản lý branch, PR, dữ liệu và chuyển giao.

## Tài liệu cần đọc

- [Architecture Baseline v1.2](../../docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx).
- [Technical Research & PoC Plan v1.0](../../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx).
- [Technical Risk Assessment v1.1](../../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx): R01–R03, R09, R11–R14.

**Mục nên mở:** Stage 01 §2, §6, §8; Stage 03 §5 P01–P03, §8, §10; gates G1/G2/G4/G5/G6. Word được dẫn tới file thật; tìm số mục/mã P trong tài liệu, không dùng anchor giả cho DOCX.
