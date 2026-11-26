# P06 — Tổng quan tài liệu & Cơ sở lý thuyết (Literature Review)

**Module:** P06 — Sales Intelligence & Autonomous Storytelling  
**Nguồn nền tảng:** Stage 03 (`HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx`, §5 `P06.4–P06.6`) và `P06/README.md` (§10)  
**Trạng thái:** `IN RESEARCH`

> **Lưu ý kiểm chứng:** Các tài liệu, bài báo khoa học và mã nguồn mở được tổng hợp dưới đây xuất phát từ danh mục tham chiếu đã rà soát ở Stage 03. Việc đánh giá benchmark thực nghiệm trên dữ liệu tiếng Việt, kiểm tra chi tiết điều khoản thương mại/license/bảo mật của từng LLM provider cụ thể, và tổng hợp ghi chú đọc sâu từng bài báo đang ở trạng thái **`TODO / IN RESEARCH`**. Sự tồn tại của bài báo khoa học không tự tạo ra license sử dụng thương mại cho sản phẩm.

---

## 1. Lập kế hoạch kể chuyện phân cấp & Kiểm soát diễn ngôn (Hierarchical Story Planning & Discourse Control)

Trong bài toán phát trực tiếp kéo dài 1–2 giờ với sự xen ngang liên tục của người xem, việc sinh lời thoại trực tiếp từ một prompt phẳng (flat prompt) dễ dẫn đến trôi mạch (topic drift), bỏ sót thông tin quan trọng của sản phẩm hoặc lặp lại nội dung đã nói.

- **Nguyên lý áp dụng cho P06:** Phân tách rõ hai tầng điều khiển (xem Stage 03 `P06.4`):
  1. **Tầng cấu trúc vĩ mô (`StoryPlan` & `StoryArc`):** Quy định trình tự các chủ đề lớn (ví dụ: giới thiệu nguồn gốc OCOP → hương vị/thành phần → cách dùng/bảo quản → giá bán và ưu đãi hợp lệ) cùng danh sách `mandatory_topics` không được bỏ sót.
  2. **Tầng hiện thực hóa bề mặt (`StoryChunk`):** Mỗi bước chỉ sinh một đoạn thoại ngắn vừa phải, kết thúc tại một `semantic_breakpoint` (điểm ngắt ngữ nghĩa trọn vẹn).
- **Lợi ích đối với livestream commerce:** Khi bị bình luận chen ngang, hệ thống chỉ cần tạm dừng giữa các chunk tại `semantic_breakpoint`, trả lời bình luận xong rồi đối chiếu `StoryCheckpoint` (được xác nhận bởi `PlaybackCompleted`) để tạo câu `bridge` quay lại đúng phần chưa phủ trong `StoryArc`. Điều này giữ nguyên vẹn coverage ngay cả trong phiên nhiều biến động.

---

## 2. Đồ thị trạng thái có chu trình (LangGraph) vs Chuỗi tuyến tính vs Đa tác tử tự do

Giai đoạn Stage 03 (`P06.5` & `P06.7`) đã đối chiếu ba hướng kiến trúc thực thi cho agent kể chuyện:

| Phương án | Cơ chế vận hành | Ưu điểm | Nhược điểm & Lý do chọn/loại trong HOSTRA |
| :--- | :--- | :--- | :--- |
| **A. Linear Chains / `Script-first`** | Chuỗi xử lý một chiều hoặc ghép các đoạn kịch bản viết sẵn theo thứ tự cố định. | Ổn định, độ trễ và chi phí thấp, dễ dự đoán. | Thiếu vòng lặp kiểm tra–sửa có điều kiện; nhanh chóng gây lặp nhàm chán trong live 1–2 giờ và khó ứng biến khi bị hỏi ngắt quãng. **Dùng làm Baseline đối chiếu.** |
| **B. Stateful Cyclic Graph (`LangGraph`)** | Biểu diễn luồng xử lý dưới dạng `StateGraph` định kiểu rõ ràng (Typed State), có rẽ nhánh có điều kiện (`conditional edges`) và chu trình giới hạn (`load context → plan chunk → draft → P05 verify → bounded rewrite → return`). | Cân bằng giữa tính tự nhiên của LLM và quyền kiểm soát chặt chẽ của backend; trace từng bước dễ audit; giới hạn cứng được số vòng lặp rewrite. | Cần thiết kế rạch ròi giữa `LangGraph checkpoint` (trạng thái sinh) và `Session/Playback state` (do `P08`/`P04` sở hữu). **`SELECTED FOR PoC`.** |
| **C. Unbounded Multi-Agent (Fully Agentic)** | Nhiều agent độc lập (Planner, Critic, Sales, Memory) tự do đối thoại, thương lượng với nhau để quyết định kịch bản và câu nói. | Tiềm năng thích ứng cao trong môi trường mở. | Chi phí token lớn, độ trễ khó kiểm soát (`R03`), khó audit nguyên nhân lỗi phát ngôn (`R08`) và dễ phát sinh vòng lặp đàm phán không xác định. **Không chọn cho MVP (`DEFERRED`).** |

- **Tham chiếu công nghệ:**
  - Mã nguồn LangGraph: [`github.com/langchain-ai/langgraph`](https://github.com/langchain-ai/langgraph) (License công bố: MIT — cần đối chiếu lại phiên bản khi đóng băng dependency).
  - Tài liệu LangGraph: [`docs.langchain.com/oss/python/langgraph/overview`](https://docs.langchain.com/oss/python/langgraph/overview) — trọng tâm đọc: mô hình `StateGraph`, `conditional paths`, cơ chế persistence và ranh giới giữa graph state với session state bên ngoài.

---

## 3. Các mẫu hình suy luận và tự sửa lỗi của Agent (Agent Reasoning & Self-Correction Patterns)

### 3.1. ReAct (Yao et al., ICLR 2023)
- **Tham chiếu:** [`arxiv:2210.03629`](https://arxiv.org/abs/2210.03629) — *ReAct: Synergizing Reasoning and Acting in Language Models*.
- **Nguyên lý:** Kết hợp xen kẽ bước suy luận (`Reasoning`) với hành động gọi công cụ (`Acting`) để truy xuất thông tin từ môi trường ngoài thay vì chỉ dựa vào tri thức tham số nội tại của LLM.
- **Áp dụng & Ràng buộc trong P06:** P06 vận dụng tư duy tiếp cận ngữ cảnh động bằng cách chỉ cho phép agent truy cập dữ liệu sản phẩm thông qua `EvidenceBundle` do `P05` cung cấp (truy vấn có kiểm soát), đồng thời ghi lý do (`rationale`) và trích dẫn `cited_evidence_ids`. Khác với ReAct tự do, tập hành động (tool space) của P06 bị khóa chặt: không được tự do gọi API ngoài, không tự đổi SKU hay ghi đè dữ liệu `P05`.

### 3.2. Self-Refine (Madaan et al., NeurIPS 2023)
- **Tham chiếu:** [`arxiv:2303.17651`](https://arxiv.org/abs/2303.17651) — *Self-Refine: Iterative Refinement with Self-Feedback*.
- **Nguyên lý:** Mô hình tự tạo bản nháp ban đầu, tự sinh phản hồi phê bình (self-feedback), và lặp lại bước chỉnh sửa (refinement) dựa trên phản hồi đó.
- **Phân tích giới hạn trong thương mại thực phẩm (`R08`, `G4`):** Các nghiên cứu và đặc thù bài toán tuân thủ cho thấy **LLM tự phê bình một mình (self-critique alone) KHÔNG đủ độ tin cậy** để đảm bảo tính đúng đắn về giá bán, trạng thái chứng nhận `OCOP: VERIFIED` hay các quy định cấm thổi phồng công dụng thực phẩm (`R17`), vì mô hình có thể tự hợp lý hóa ảo giác (hallucination) của chính nó.
- **Thiết kế bắt buộc ở P06:** Phản hồi sửa lỗi trong vòng `bounded rewrite` của P06 **phải bắt nguồn từ bộ kiểm chứng xác định bên ngoài (`P05 PublicationGate`)** trả về mã lỗi tường minh (`BlockReason` như `PRICE_MISMATCH`, `CROSS_SKU_VIOLATION`, `PROHIBITED_CLAIM`, `MISSING_EVIDENCE`, `OCOP_NOT_VERIFIED`), kết hợp ngân sách thử lại cứng (`max_retries = K`).

### 3.3. Reflexion (Shinn et al., 2023)
- **Tham chiếu:** [`arxiv:2303.11366`](https://arxiv.org/abs/2303.11366) — *Reflexion: Language Agents with Verbal Reinforcement Learning*.
- **Nguyên lý:** Lưu trữ phản hồi dạng ngôn ngữ vào bộ nhớ tình huống (episodic memory) qua các lần thử thất bại để cải thiện hành vi ở các lượt tiếp theo mà không cần cập nhật trọng số mô hình.
- **Áp dụng có kiểm soát tại P06:** Phân tách thành hai lớp bộ nhớ:
  1. *Bộ nhớ phản hồi trong lượt (Intra-turn feedback):* Chuyển thông điệp lỗi từ `P05` vào node `rewrite` của lượt hiện tại, nhưng phải có giới hạn số bước `K` để ngăn bùng nổ độ trễ (`R03`) và phình ngữ cảnh (context bloat).
  2. *Bộ nhớ lịch sử xuyên lượt (`RecentSpeechTracker`):* Chỉ lưu nhận thức về những nội dung đã thực sự phát qua `PlaybackCompleted` ACK (intent, SKU, covered facts, `5–N` utterances gần nhất), tuyệt đối không biến thành hệ thống đa tác tử tự suy ngẫm kéo dài.

---

## 4. Phát hiện lặp ngữ nghĩa (Semantic Repetition Detection)

Trong hội thoại bán hàng tiếng Việt, chỉ kiểm tra trùng chuỗi ký tự (exact string matching) hoặc n-gram thuần túy là chưa đủ: mô hình có thể đổi vài từ nối ("Dạ sản phẩm này giá..." sang "Dạ em báo giá sản phẩm này...") nhưng vẫn lặp cùng một ý bán hàng gây khó chịu (`R05`).

- **Chiến lược phân tầng của P06 (`SELECTED FOR PoC`):**
  - *Lớp 1 — Rule-based & Structured Ledger (Mặc định):* Theo dõi bộ ba `(sku_id, intent, covered_claim_ids / covered_topics)` và lịch sử `viewer_id` trên cửa sổ `5–N` utterances đã có `PlaybackCompleted` ACK. Hướng dẫn LLM thực hiện *controlled paraphrase* (đổi góc tiếp cận hoặc bổ sung giá trị phụ trợ đã duyệt khi phải nhắc lại giá/ship cho người xem mới).
  - *Lớp 2 — Embedding Cosine Similarity (`PROPOSED / TO VALIDATE`):* Chỉ kích hoạt và benchmark so sánh nếu kết quả thực nghiệm (`P06-E01`, `P06-E02`) cho thấy lớp 1 chưa phát hiện được các trường hợp lặp ngữ nghĩa tinh vi trong tiếng Việt.

---

## 5. Công cụ đối chiếu tối ưu Prompt (DSPy Comparator)

- **Tham chiếu:** [`github.com/stanfordnlp/dspy`](https://github.com/stanfordnlp/dspy) (License công bố: MIT).
- **Vai trò chính xác trong P06:** Được xếp loại là **công cụ nghiên cứu đối chiếu tùy chọn (Optional Comparator)** sau khi đã hoàn thiện tập dữ liệu đánh giá chuẩn (evaluation dataset) và hệ thống metric ở Phase 2–4.
- **Ranh giới kiến trúc:** Nếu thử nghiệm, `DSPy` chỉ dùng để tối ưu hóa chỉ dẫn/few-shot prompt bên trong các node sinh văn bản (như node draft hoặc rewrite), **tuyệt đối không** thay thế kiến trúc đồ thị trạng thái `LangGraph`, hợp đồng `Pydantic` hay ranh giới kiểm chứng `P05`/`P08`.

---

## 6. Trạng thái rà soát mở (`TODO / IN RESEARCH`)

Các đầu mục dưới đây đang chờ triển khai đọc sâu và kiểm chứng thực nghiệm trong các bước tiếp theo:
- [ ] Ghi chú đọc sâu chi tiết thuật toán & failure modes của `ReAct`, `Self-Refine`, `Reflexion` áp dụng vào domain tiếng Việt.
- [ ] Khảo sát và kiểm tra điều khoản sử dụng / quyền dữ liệu thương mại / bảng giá (license & privacy gate) của các LLM provider ứng viên (`OPEN-1`).
- [ ] Thử nghiệm benchmark độ ổn định structured JSON/Pydantic output tiếng Việt trên các mô hình ứng viên.
- [ ] Kiểm chứng thực tế nhu cầu dùng embedding similarity cho chống lặp tiếng Việt so với chi phí vận hành (`OPEN-2`).
