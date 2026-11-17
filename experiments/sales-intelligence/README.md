# Tri thức, nội dung bán hàng và hiểu bình luận

[Trở về trung tâm nghiên cứu](../README.md)

**Phạm vi:** P05–P07. **Trạng thái khởi tạo:** NOT STARTED, chưa có evidence trong các thư mục con; công nghệ vẫn SELECTED FOR PoC.

## Tổng quan và vai trò trong kiến trúc

Nhóm này nghiên cứu cách để AI hiểu câu hỏi tiếng Việt và chủ động nói về sản phẩm với bằng chứng. Mục tiêu là nội dung đúng, tự nhiên, không lặp vô ích và không nhầm SKU trong phạm vi 2–5 sản phẩm thực phẩm đóng gói đủ điều kiện.

P05 sở hữu evidence/claims, P06 lập kế hoạch và sinh candidate, P07 tạo task từ bình luận. P08 chọn lượt, P09 giữ Active SKU/OCOP eligibility. LLM không trở thành nguồn sự thật hoặc có quyền tự phát.

## Luồng dữ liệu và phụ thuộc

```text
Tài liệu + review → P05 → facts/evidence có version → P06 Story Plan/candidate
Bình luận P10 → P07 intent/SKU/group → P08 chọn → P06
P06 draft → P05 verify → P02/P03 prepare → P08/P04 recheck/commit
P04 PlaybackCompleted → P08/P06 cập nhật lịch sử
```

- [Điều phối và played-history](../conversation-orchestration/README.md)
- [Text hợp lệ sang TTS](../ai-presenter-media/voice-tts/README.md)

P11 cung cấp kiểm tra quyền/tenant; P09 kiểm OCOP và điều kiện SKU, P05 kiểm claims. Các gate này vẫn áp dụng cho media đã cache và fallback. P10 là giao diện/trải nghiệm cần kiểm tra ở bước tích hợp, không tự quyết định LIVE/APPLIED.

## Bài toán con và nơi bắt đầu

| Hướng nghiên cứu | Module | Mục đích |
| --- | --- | --- |
| [Tri thức sản phẩm và kiểm chứng lời thoại](knowledge-verification/README.md) | P05 | FTS có đủ recall trên câu hỏi tiếng Việt có/không dấu, hay embeddings cải thiện được trên cùng bộ test? |
| [Kể chuyện bán hàng chủ động](autonomous-storytelling/README.md) | P06 | Sau 10–30 phút không bình luận, nội dung có bao phủ các chủ đề bắt buộc và tránh lặp ý không? |
| [Hiểu và phân luồng bình luận tiếng Việt](comment-understanding/README.md) | P07 | PhoBERT-base hay SetFit tốt hơn với 8/16/32 mẫu mỗi lớp trên cùng held-out test? |

README con có định nghĩa input/output, kiến thức cần học, baseline, từng mã experiment và checklist; trang này tập trung vào phối hợp cả nhóm.

## Rủi ro cần theo dõi

**Mapping:** R03–R05, R08, R10, R13, R16, R17.

R08/R16/R17: claim thiếu chứng cứ, dữ liệu cũ, OCOP giả hoặc điều kiện thực phẩm chưa đạt. R04/R10: nhầm SKU/viewer/tenant, grouping làm mất record. R05: lặp ý, bỏ mạch kể; R03: chi phí/latency LLM tăng khi có burst. R13: câu nói đúng nhưng trải nghiệm thiếu thuyết phục.

## Thứ tự tìm hiểu

1. Đọc Stage 01 §6–7 và ACR-002; hiểu khác biệt facts, evidence và eligibility.
2. Chuẩn bị bộ SKU/FAQ có nguồn ở knowledge-verification trước khi đánh giá câu trả lời.
3. Nghiên cứu comment classifier trên split có nhãn; kết nối task với P08 mock.
4. Thử storytelling không comment rồi ngắt/resume, dùng played-history từ ACK mô phỏng.
5. Kết nối P05→P06→P05 và negative cases trước khi chuyển text sang TTS.

Đây là thứ tự đọc/thử đề xuất, không phải timeline bắt buộc. Chạy Kaggle/Colab cho phần phù hợp và ghi rõ phần còn mock; không coi notebook thành công là bằng chứng production hoặc live liên tục.

## Kết quả mong đợi

Dataset có nhãn/quyền, baseline retrieval/classifier, ma trận lỗi claims/SKU, transcript/rubric storytelling, benchmark chất lượng/latency/chi phí và đề xuất có bằng chứng cho các quyết định mở.

Báo cáo mỗi kết quả với run ID, cấu hình, dataset/quyền, metric, giới hạn và vị trí evidence. Mọi ngưỡng chưa có trong nguồn phải được chốt trước thử nghiệm. Chỉ đổi trạng thái sau review; đọc [quy trình chung](../README.md) để quản lý branch, PR, dữ liệu và chuyển giao.

## Tài liệu cần đọc

- [Architecture Baseline v1.2](../../docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx).
- [Technical Research & PoC Plan v1.0](../../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx).
- [Technical Risk Assessment v1.1](../../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx): R03–R05, R08, R10, R13, R16, R17.

**Mục nên mở:** Stage 01 §5–7, §9; Stage 03 §5 P05–P07, §7 về OCOP, §8–9; gates G2/G3/G4/G6. Word được dẫn tới file thật; tìm số mục/mã P trong tài liệu, không dùng anchor giả cho DOCX.
