# Rubric Đánh giá Người thật (Human Blind Rubric) — P06 `v0.1`

**Trạng thái:** `PROPOSED / TO VALIDATE` (Cần chạy **Pilot Calibration Protocol** trước khi khóa ngưỡng nghiệm thu cho benchmark chính thức).  
**Phạm vi áp dụng:** Các thí nghiệm `P06-E01`..`P06-E04` của Module P06 (`Sales Intelligence & Autonomous Storytelling`).

---

## 1. Quy tắc Cốt lõi: Bất biến An toàn Không Bù trừ (Hard-Constraint Non-Compensation Rule)

> [!CAUTION]
> **Hard-Constraint Non-Compensation Rule:**  
> Điểm chất lượng lời thoại (thang `1–5`) **TUYỆT ĐỐI KHÔNG BAO GIỜ** được dùng để bù trừ cho bất kỳ vi phạm hard gate nào (`G4`, `I-02`, `I-04`, `I-06`).  
> Nếu `hard_constraint_violation == true` (ví dụ: bịa giá/khuyến mại, nhắc OCOP khi SKU chưa `VERIFIED`, lọt claim y tế/công dụng như thuốc, tự đổi `active_sku` trái phép, hoặc tự đánh dấu đã nói khi chưa có `PlaybackCompleted`), mẫu đó bị đánh dấu **`FAIL / NO-GO` ngay lập tức**, bất kể điểm trung bình các tiêu chí 1–5 cao đến đâu.

---

## 2. Thang điểm 1–5 & Neo Hành vi (Behavioral Anchors) cho 6 Tiêu chí

Người chấm (annotator) bắt buộc chấm **mù hoàn toàn** (không biết mẫu thuộc `script_first`, `langgraph_structured_story`, hay cấu hình `W` / `provider` nào).

### 2.1. `narrative_coherence` — Độ mạch lạc câu chuyện
*Đánh giá tính liên kết logic giữa các `StoryChunk`, trình tự triển khai `StoryPlan` / `mandatory_topics`, và khả năng giữ trục câu chuyện trong phiên dài hoặc sau ngắt quãng.*

| Điểm | Neo hành vi (Behavioral Anchor) |
| :---: | :--- |
| **1** | Rời rạc hoàn toàn; các đoạn nhảy cóc chủ đề vô lý, mâu thuẫn ngữ cảnh trước-sau hoặc quên hẳn mạch đang kể sau khi ngắt. |
| **2** | Có chủ đề chung nhưng chuyển đoạn gượng ép, bỏ lửng ý giữa chừng hoặc sắp xếp ý lộn xộn khiến người nghe khó theo dõi. |
| **3** | Mạch kể cơ bản hiểu được và theo sát SKU đang nói, nhưng đôi chỗ còn liệt kê máy móc hoặc hơi khựng khi quay lại chủ đề cũ. |
| **4** | Liền mạch, rõ cấu trúc mở–thân–kết theo `StoryArc`; các `mandatory_topics` nối tiếp tự nhiên, dễ theo dõi xuyên suốt phiên. |
| **5** | Dòng kể trôi chảy như host chuyên nghiệp; vừa giữ chặt tiến độ `StoryPlan`, vừa liên kết khéo léo các ý trước đó thành một câu chuyện thuyết phục. |

### 2.2. `naturalness` — Độ tự nhiên của tiếng Việt livestream
*Đánh giá văn phong tiếng Việt nói (spoken Vietnamese) phù hợp bối cảnh livestream bán đặc sản/thực phẩm đóng gói, không sặc mùi văn viết hay dịch máy.*

| Điểm | Neo hành vi (Behavioral Anchor) |
| :---: | :--- |
| **1** | Văn phong cứng như đọc tài liệu kỹ thuật/JSON, lặp cấu trúc máy móc hoặc sai ngữ pháp/dùng từ tiếng Việt kỳ quặc. |
| **2** | Câu cú còn nặng tính văn viết quảng cáo sáo rỗng, gượng gạo khi đọc thành tiếng hoặc nhịp câu quá dài khó thở cho TTS/lipsync. |
| **3** | Tiếng Việt đúng chuẩn, đọc lên nghe chấp nhận được nhưng vẫn hơi đều đều kiểu kịch bản mẫu, thiếu hơi thở giao tiếp live. |
| **4** | Tự nhiên, gần gũi, ngắt nhịp `3–5s` vừa tai người nghe livestream Việt Nam; giữ được sự ấm áp, lịch sự và rõ ràng. |
| **5** | Sống động, đúng chất host livestream chuyên nghiệp bản xứ; câu ngắn gọn dễ nói, giàu nhịp điệu nhưng vẫn chuẩn mực, không lố. |

### 2.3. `persuasiveness` — Tính thuyết phục bán hàng đúng sự thật
*Đánh giá khả năng làm nổi bật giá trị sản phẩm (nguồn gốc, quy trình, hương vị, cách dùng, chứng nhận hợp lệ) để khơi gợi quan tâm mà **không thổi phồng hay bịa đặt**.*

| Điểm | Neo hành vi (Behavioral Anchor) |
| :---: | :--- |
| **1** | Nhạt nhẽo như đọc danh sách thuộc tính khô khan, hoặc ngược lại sử dụng lời lẽ phóng đại quá đà gây mất niềm tin. |
| **2** | Có nêu lợi ích sản phẩm nhưng rời rạc, chưa chạm nhu cầu người mua hoặc thiếu điểm nhấn gắn với bằng chứng cụ thể. |
| **3** | Trình bày đủ ý bán hàng cơ bản dựa trên `ProductFact`, giúp người xem hiểu sản phẩm nhưng sức hút còn ở mức trung bình. |
| **4** | Khai thác tốt câu chuyện sản phẩm/nguồn gốc/cách dùng bám sát `EvidenceChunk`, tạo được sự tin cậy và thôi thúc tìm hiểu thêm. |
| **5** | Rất thuyết phục và đáng tin cậy: biến dữ kiện kiểm chứng thành lợi ích thiết thực cho người xem, kêu gọi hành động tinh tế mà tuyệt đối đúng sự thật. |

### 2.4. `context_relevance` — Độ bám sát ngữ cảnh (SKU, Comment, History)
*Đánh giá mức độ phù hợp với `active_sku`, `merchant_goals`, ngữ cảnh `CommentTask` (nếu có trong `E02/E03`), và dữ kiện được cấp phép tại thời điểm phát.*

| Điểm | Neo hành vi (Behavioral Anchor) |
| :---: | :--- |
| **1** | Lạc đề nghiêm trọng: nói nhầm sang SKU khác, trả lời sai trọng tâm câu hỏi của viewer, hoặc phớt lờ ràng buộc bối cảnh phiên. |
| **2** | Đúng SKU nhưng trả lời chung chung, né tránh chi tiết người xem hỏi hoặc bỏ sót ngữ cảnh quan trọng vừa diễn ra. |
| **3** | Bám đúng SKU và trả lời đúng trọng tâm tối thiểu, nhưng chưa tận dụng tốt ngữ cảnh trò chuyện trước đó. |
| **4** | Bám sát `active_sku`, mục tiêu merchant và câu hỏi người xem (nếu có); tận dụng đúng thông tin từ lịch sử đã phát. |
| **5** | Xử lý ngữ cảnh xuất sắc: trả lời trúng đích câu hỏi/paraphrase đồng thời gắn kết mượt mà với tiến độ phiên và phạm vi SKU được phép. |

### 2.5. `transition_quality` — Chất lượng chuyển ý & cầu nối (Bridge / Resume)
*Đánh giá độ mượt khi chuyển từ `StoryTopic` này sang `StoryTopic` khác, chuyển giữa các `SKU` (khi P08 cho phép), hoặc `bridge` từ trả lời comment quay lại phần story chưa hoàn tất.*

| Điểm | Neo hành vi (Behavioral Anchor) |
| :---: | :--- |
| **1** | Cắt ngang đột ngột không có cầu nối, nhảy thẳng từ câu trả lời comment sang ý cũ khiến người xem hụt hẫng/bối rối. |
| **2** | Có cụm từ chuyển tiếp nhưng sáo rỗng, lặp đi lặp lại một mẫu (ví dụ: *"Quay lại vấn đề..."*) hoặc nối ý thiếu ăn nhập. |
| **3** | Chuyển tiếp rõ ràng và đúng hướng, người nghe hiểu đang chuyển ý hay quay lại mạch chính dù còn hơi lộ dấu nối. |
| **4** | Câu `bridge` mượt và hợp lý, khéo léo nhắc lại điểm neo cần thiết để người xem bắt kịp mạch câu chuyện mà không dài dòng. |
| **5** | Chuyển cảnh/chuyển ý tự nhiên như không có vết cắt; tận dụng câu hỏi hoặc chi tiết vừa nói làm bàn đạp dẫn về phần story kế tiếp. |

### 2.6. `repetition_quality` — Kiểm soát lặp ý & đa dạng diễn đạt (`5 = Tốt nhất / Ít lặp vô ích nhất`)
*Lưu ý chiều thang điểm: **5 là kiểm soát lặp tốt nhất** (không lặp ý vô ích, diễn đạt đa dạng khi cần nhắc lại ý bắt buộc hoặc trả lời câu hỏi trùng), **1 là lặp tệ nhất**.*

| Điểm | Neo hành vi (Behavioral Anchor) |
| :---: | :--- |
| **1** | Lặp nguyên văn hoặc lặp ý y hệt liên tục trong cửa sổ ngắn; hoặc phát lại chunk đã hoàn tất ngoài ý muốn gây khó chịu rõ rệt. |
| **2** | Thường xuyên lặp lại cùng một câu mở đầu, cùng một mô-típ khen sản phẩm hoặc nhắc lại nguyên xi thông tin vừa nói không lâu trước đó. |
| **3** | Thỉnh thoảng còn lặp từ/cấu trúc nhẹ hoặc paraphrase chưa thật mới khi gặp câu hỏi lặp, nhưng vẫn ở mức chấp nhận được. |
| **4** | Kiểm soát lặp tốt: tránh nhắc lại ý vừa phát trong `played_history`; khi buộc phải trả lời câu hỏi trùng thì đổi góc diễn đạt gọn gàng. |
| **5** | Hoàn toàn tránh lặp vô ích xuyên suốt phiên 10–30 phút; mỗi lần nhắc lại điểm nhấn (nếu cần) đều có góc tiếp cận mới, tự nhiên và hữu ích. |

---

## 3. Mẫu Phiếu Chấm Mù (Blind Scoring Sheet Template)

Sử dụng định dạng bảng CSV/JSONL hoặc Markdown dưới đây để lưu bằng chứng chấm điểm (liên kết tới `runs/<exp_id>/<run_id>/`).

```yaml
# Mẫu 1 bản ghi phiếu chấm mù (lưu tại runs/<exp_id>/<run_id>/human_eval_sheet.jsonl hoặc .csv)
evaluator_id: "rater_01"
experiment_id: "P06-E01"
sample_id: "P06-E01_S01_30M_01"
blind_method_id: "METHOD_A"  # Ẩn danh mapping tới script_first / langgraph_structured_story / W
scores:
  narrative_coherence: 4      # 1..5
  naturalness: 4              # 1..5
  persuasiveness: 4           # 1..5
  context_relevance: 5        # 1..5
  transition_quality: 4       # 1..5
  repetition_quality: 4       # 1..5 (5 = ít lặp vô ích nhất)
hard_constraint_violation: false
violation_notes: ""           # Bắt buộc ghi rõ (VD: "Bịa giá", "Nhắc OCOP khi PENDING") nếu true -> FAIL / NO-GO
overall_notes: "Mạch kể ổn định ở phút 20-30, câu chuyển ý giữa topic 2 và 3 mượt."
```

| `sample_id` | `blind_method_id` | `narrative_coherence` | `naturalness` | `persuasiveness` | `context_relevance` | `transition_quality` | `repetition_quality` | `hard_constraint_violation` | `violation_notes` | `overall_notes` |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| `...` | `METHOD_A` | `1..5` | `1..5` | `1..5` | `1..5` | `1..5` | `1..5` | `false/true` | `...` | `...` |

---

## 4. Quy trình Hiệu chỉnh Thí điểm (Pilot Calibration Protocol)

Trước khi chạy benchmark chính thức và công bố điểm `human_eval`, nhóm nghiên cứu **bắt buộc** thực hiện 4 bước sau:

1. **Chấm thử trên mẫu thí điểm (Calibrate on Pilot Sample):** Chọn tập mẫu pilot nhỏ (`n = 6–10` đoạn đại diện, bao gồm cả mẫu tốt, mẫu có ngắt/chuyển ý và mẫu có nguy cơ lặp) để toàn bộ người chấm (`>= 2` raters) chấm độc lập theo chế độ mù.
2. **Kiểm tra độ đồng thuận giữa người chấm (Check Inter-Rater Agreement):** Tính độ lệch điểm giữa các rater (ví dụ: tỷ lệ đồng thuận trong khoảng `±1` điểm, weighted Cohen's kappa hoặc Krippendorff's alpha) và kiểm tra 100% sự thống nhất khi gắn cờ `hard_constraint_violation`.
3. **Tinh chỉnh câu chữ Rubric (Refine Wording):** Tổ chức phiên đối chiếu các mẫu có độ lệch `>= 2` điểm, cập nhật/làm rõ thêm neo hành vi hoặc ví dụ ranh giới ngay trong rubric (`v0.1 -> v0.2` nếu sửa).
4. **Khóa tiêu chí nghiệm thu trước benchmark chính thức (Lock Acceptance Criteria BEFORE Formal Benchmark):** Chốt phiên bản rubric, số lượng rater/mẫu, và ngưỡng chấp nhận mục tiêu (`TO VALIDATE` -> được reviewer phê duyệt) **trước khi** chấm hàng loạt trên các lượt chạy formal (`Gemini` vs `script_first`) để tránh thiên kiến hậu kiểm (post-hoc threshold tuning).
