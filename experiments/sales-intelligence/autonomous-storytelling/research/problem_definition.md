# P06 — Định nghĩa bài toán (Problem Definition)

**Module:** P06 — Sales Intelligence & Autonomous Storytelling  
**Nhóm nghiên cứu:** Sales Intelligence (`P05–P07`)  
**Mốc tham chiếu:** `M4` · **Rủi ro chính:** `R05`, `R08`, `R13` · **Gates:** `G2`, `G4`, `G6`  
**Trạng thái tài liệu:** `IN RESEARCH` (bộ tài liệu thiết kế nghiên cứu thuộc Phase 2; chưa có code hay kết quả thực nghiệm trong `P06_ROOT`).

---

## 1. Bối cảnh và Bài toán Kinh doanh (Business Problem)

Trong thương mại phát trực tiếp (livestream commerce) bằng tiếng Việt với phạm vi MVP của HOSTRA AI (một phiên đồng thời trong private live room, thời lượng 1–2 giờ, danh mục 2–5 SKU thực phẩm đóng gói đạt trạng thái `OCOP: VERIFIED` theo `ACR-002`), hành vi bình luận của người xem diễn ra không đều: thường có những khoảng lặng kéo dài xen kẽ với các đợt bùng phát câu hỏi lặp lại (như hỏi giá, phí vận chuyển, hạn sử dụng, nguồn gốc OCOP).

Nếu AI chỉ hoạt động theo cơ chế phản ứng thụ động (chỉ nói khi có bình luận), phiên live sẽ rơi vào trạng thái `HOST_IDLE` trong các khoảng lặng, làm đứt mạch bán hàng và giảm mức độ tin cậy của người xem. Ngược lại, nếu dùng kịch bản soạn sẵn tĩnh (`Script-first`) phát lặp đi lặp lại trong 1–2 giờ:

1. **Giảm trải nghiệm và độ thuyết phục (`R13`):** Người xem nghe thấy các câu thoại rập khuôn, thiếu thích ứng theo ngữ cảnh khi quay lại hỏi cùng một vấn đề hoặc khi vừa bị ngắt mạch bởi bình luận.
2. **Đánh mất niềm tin của merchant (`G6`, `R05`):** Kịch bản cứng có thể bỏ sót các chủ đề bắt buộc mà merchant yêu cầu (mandatory topics), hoặc không chuyển ý tự nhiên khi quay lại giới thiệu sản phẩm sau khi trả lời khách.
3. **Rủi ro tuân thủ và thông tin sai lệch (`R08`, `R16`, `R17`):** Khi thiếu cơ chế kiểm chứng gắn chặt với nguồn dữ liệu đã duyệt, lời nói sinh động có thể bịa công dụng thực phẩm bị cấm, đọc giá cũ hoặc nhắc chứng nhận OCOP không còn hiệu lực.

Do đó, bài toán kinh doanh đặt ra là duy trì được một dòng kể chuyện bán hàng tiếng Việt chủ động, tự nhiên, thuyết phục, bám sát mục tiêu của merchant và tuyệt đối trung thực với dữ liệu sản phẩm đã xác minh suốt phiên live 1–2 giờ.

---

## 2. Bài toán Kỹ thuật (Technical Problem)

Về mặt kỹ thuật, P06 phải thiết kế và kiểm chứng một **Stateful, Bounded AI Agent** (tác tử AI có trạng thái và bị chặn giới hạn thực thi) có khả năng sinh từng đoạn kể chuyện (`StoryChunk`) và câu trả lời bình luận tiếng Việt trên chân trời thời gian dài, đồng thời bảo toàn 4 bất biến kiến trúc cốt lõi:

1. **Tách biệt nghiêm ngặt giữa ba trạng thái *Generated* vs *Verified* vs *Played*:**
   - Lời thoại do LLM sinh ra trong đồ thị LangGraph chỉ là bản nháp (`StoryChunk` / `SpeechCandidate` — *generated*).
   - Bản nháp chỉ trở thành `VerifiedSpeechCandidate` (*verified*) sau khi vượt qua cổng kiểm chứng thực tế và chính sách của P05 (`PublicationGate` → `PublicationStatus.ALLOW`).
   - Một đoạn nội dung chỉ được tính là đã phát (*played*) và cập nhật vào bộ nhớ lịch sử / tiến độ chủ đề khi nhận được xác nhận phát sóng thực tế `PlaybackCompleted` từ Media Controller (`P04`) thông qua điều phối của `P08`. Tuyệt đối không coi checkpoint của LangGraph hay trạng thái hoàn tất TTS (`P02`) là bằng chứng đã phát tới người xem.

2. **Đảm bảo bao phủ chủ đề bắt buộc (Mandatory Topic Coverage) và chống lặp ngữ nghĩa trên lịch sử đã phát:**
   - Agent phải theo dõi trạng thái bao phủ theo từng arc/topic trong `StoryPlan` (dựa trên dữ liệu *played* thực sự) để tránh lặp lại cùng một luận điểm hoặc lặp nguyên văn trong cửa sổ lịch sử phát gần đây (`5–N` utterances), kể cả khi nhận nhiều câu hỏi paraphrase từ người xem.
   - Chống lặp theo ngữ nghĩa, intent, SKU và facts đã phủ (không chỉ thay đổi vài từ bề mặt nhưng lặp cùng một ý vô ích).

3. **Nhận biết điểm ngắt ngữ nghĩa (Semantic Breakpoint) và khôi phục không mất mát (Lossless Resume):**
   - Mỗi `StoryChunk` sinh ra phải kết thúc tại một ranh giới ý nghĩa hoàn chỉnh (`breakpoint`) để `P08` có thể chen câu trả lời bình luận tại điểm ngắt an toàn.
   - Khi bị ngắt giữa một `StoryArc` bởi `CommentTask`, `StoryCheckpoint` (chỉ tiến lên theo `PlaybackCompleted`) phải giúp P06 tạo câu chuyển tiếp (`bridge`) tự nhiên và quay lại đúng phần nội dung chưa phát — đạt **0 lần phát trùng** các chunk đã hoàn tất (`Completed Chunk Replay Count = 0`).

4. **Viết lại có giới hạn (Bounded Rewrite) và cơ chế Fail-Closed khi lỗi:**
   - Khi ứng viên vi phạm ràng buộc từ P05 (lệch giá, sai SKU, thiếu `evidence_id`, claim bị cấm, lạc chủ đề bắt buộc), luồng LangGraph thực hiện vòng lặp sửa có giới hạn cứng (`max_retries = K`).
   - Nếu vượt quá ngân sách retry/latency, gặp tài liệu mâu thuẫn, prompt injection hoặc timeout từ LLM provider, hệ thống fail-closed: không phát bản nháp chưa kiểm chứng; chỉ fallback về approved pre-generated chunk còn hiệu lực hoặc nhường `P04` chuyển sang `SAFE_FALLBACK` (safe scene) và báo trạng thái suy giảm (`degraded`).

---

## 3. Hợp đồng Đầu vào / Đầu ra (Input / Output Contracts)

Các hợp đồng dưới đây định nghĩa ranh giới dữ liệu giữa P06 và các module lân cận ở giai đoạn PoC (lưu ý: cần đồng bộ schema typed với `P05` trong `knowledge-verification/schemas.py` và contract chính thức khi chuyển sang production).

### 3.1. Đầu vào của P06 (Inputs)

| Đầu vào | Nguồn cung cấp | Vai trò và nội dung chính |
| :--- | :--- | :--- |
| `StoryPlan` | Merchant / `P10` (qua backend `P09`) | Kế hoạch kể chuyện có version (`plan_version`), chứa danh sách `StoryArc`, chủ đề bắt buộc (`mandatory_topics`), mục tiêu bán hàng, ràng buộc phong cách/giới hạn được phép replan (`allowed_replan`). |
| Merchant goals & constraints | `P09` / `P10` | Ràng buộc cấp phiên/SKU: giọng điệu, điều cấm kỵ, tỷ trọng nội dung theo SKU trong phiên (2–5 SKU). |
| `EvidenceBundle` | `P05` | Gói tri thức đã duyệt cho SKU mục tiêu gồm `ProductFact` (giá, khối lượng, xuất xứ, thành phần, hạn dùng, `knowledge_version`), danh sách `EvidenceChunk`, `allowed_claims`, `prohibited_claims`. |
| `PlaybackCompleted` history | `P04` → `P08` | Lịch sử các utterance thực sự đã phát hoàn tất (kèm `chunk_id`, `sku_id`, `intent`, `covered_topics`, `cited_evidence_ids`, timestamp) để cập nhật `RecentSpeechTracker` và `StoryCheckpoint`. |
| `CommentTask` / `AuthoritativeResponseGroup` | `P07` → `P08` | Bình luận hoặc nhóm bình luận đã được `P07` chuẩn hóa, dedup, phân loại intent/SKU và được `P08` chọn xử lý theo TTL/fairness (kèm ngữ cảnh người xem nếu có). |

### 3.2. Đầu ra của P06 (Outputs)

| Đầu ra | Cấu trúc dữ liệu | Người tiêu dùng (Consumers) & Ràng buộc chuyển tiếp |
| :--- | :--- | :--- |
| `StoryChunk` / `SpeechCandidate` | Chứa `candidate_id`, `tenant_id`, `session_id`, `sku_id`, `text` (tiếng Việt), `intent`, `cited_evidence_ids`, `stated_price_vnd`, `mentions_ocop`, `semantic_breakpoint` (điểm ngắt an toàn), `bridge_metadata` (nếu là câu chuyển tiếp sau ngắt), `rationale`, cùng các phiên bản tham chiếu (`knowledge_version`, `ocop_version`, `rights_version`, `plan_version`). | Gửi tới **`P05` (`PublicationGate`)** để kiểm chứng. **Chưa** được phép gửi sang `P02` TTS hay phát sóng. |
| `VerifiedSpeechCandidate` | Là `SpeechCandidate` đã kèm `PublicationDecision(status=ALLOW)` từ `P05` và metadata checkpoint/breakpoint. | Gửi tới **`P08`** để xếp lịch và commit turn; **`P02`** để tổng hợp giọng nói (chỉ sau khi qua gate `P05` và kiểm tra lại trước commit). |
| Đề xuất điều chỉnh (Advisory only) | Đề xuất chuyển `StoryArc` hoặc gợi ý đổi SKU tiếp theo khi kết thúc arc hiện tại. | Gửi **`P08` / `P09`** xem xét; P06 không có quyền tự thực thi chuyển đổi. |

---

## 4. Ranh giới trách nhiệm & Các điểm KHÔNG thuộc phạm vi P06 (Explicit Non-Goals)

Để giữ nguyên tắc đơn thẩm quyền (Single Authority) và tách biệt rạch ròi giữa AI generation và runtime state ownership:

| Trách nhiệm P06 SỞ HỮU | Điểm KHÔNG thuộc phạm vi P06 (Explicit Non-Goals) |
| :--- | :--- |
| Lập cấu trúc `StoryPlan` theo arcs/topics và quản lý tiến độ narrative nội bộ dựa trên `PlaybackCompleted` ACK. | **KHÔNG sở hữu media playout (`P04`):** Không quyết định frame video, A/V sync, safe scene hay xác nhận `PlaybackCompleted`. |
| Sinh `StoryChunk` tiếng Việt (kể chuyện chủ động, trả lời bình luận, câu bridge sau khi bị ngắt). | **KHÔNG sở hữu lịch nói, session epoch hay Active SKU (`P08` / `P09`):** Không tự đổi `Active SKU`, không tự chuyển scene, không tự commit lượt phát. |
| Theo dõi lịch sử phát (recent played-speech) và thực thi chống lặp ngữ nghĩa / bảo phủ mandatory topics. | **KHÔNG sở hữu phân luồng/hiểu bình luận (`P07`):** Không tự đọc raw chat stream để triage, dedup hay gán TTL. |
| Gọi adapter `P05` để kiểm chứng candidate và thực hiện bounded rewrite khi bị chặn. | **KHÔNG sở hữu thẩm quyền dữ liệu & OCOP (`P05` / `P09` / `P11`):** Không tự phê duyệt claim, không tự xác thực chứng nhận OCOP (`ACR-002`), không bỏ qua kiểm tra quyền. |
| Thử nghiệm phương pháp `Structured Story Planner + Dynamic Verified Generation` bằng LangGraph. | **KHÔNG fine-tune LLM** và **KHÔNG triển khai kiến trúc Fully Agentic Multi-Agent** trong MVP nếu chưa có bằng chứng thực nghiệm chứng minh cần thiết. |

---

## 5. Bảng phân loại trạng thái (Status Classification Table)

| Hạng mục | Phân loại trạng thái | Diễn giải cụ thể |
| :--- | :--- | :--- |
| Yêu cầu hỗ trợ 2–5 SKU thực phẩm đóng gói `OCOP: VERIFIED`, 1–2h live private room (`ACR-002`) | `CONFIRMED REQUIREMENT` | Phạm vi sản phẩm đã chốt trong Architecture Baseline v1.2 và Stage 03. |
| Tách biệt generated (`P06`) vs verified (`P05`) vs played (`P04` ACK); không dùng LangGraph checkpoint làm `PlaybackCompleted` | `CONFIRMED REQUIREMENT` | Ràng buộc cứng về kiến trúc và hard gates (`G3`, `G4`). |
| Quy tắc fail-closed: không đưa draft chưa qua P05 vào TTS/commit; fallback sang approved chunk hoặc `SAFE_FALLBACK` | `CONFIRMED REQUIREMENT` | Hard gate bảo vệ tính đúng của giá, SKU, claims và OCOP (`R08`, `G4`). |
| Kiến trúc `Structured Story Planner + Dynamic Verified Generation` với `LangGraph` ngay từ PoC đầu | `SELECTED FOR PoC` | Phương án kỹ thuật được chọn trong Stage 03 để kiểm chứng ở giai đoạn PoC. |
| Chống lặp theo rules (intent, SKU, covered facts, cửa sổ `5–N` utterances đã phát) + Pydantic typed contracts | `SELECTED FOR PoC` | Cơ chế mặc định ở PoC trước khi cân nhắc embeddings. |
| Mô phỏng `PlaybackCompleted` ACK và mock `P05`/`P07`/`P08` cho các thí nghiệm độc lập `P06-E01`..`P06-E04` | `PROPOSED` | Được thiết kế trong Phase 2 để cô lập kiểm thử P06 trước tích hợp. |
| Bổ sung embeddings cho phát hiện lặp ngữ nghĩa; `DSPy` cho tối ưu prompt sau khi có dataset | `PROPOSED` | Chỉ đưa vào thử nghiệm đối chiếu khi rule-based tracking hoặc prompt cơ bản chưa đạt. |
| Mức độ đạt được về coverage, semantic repetition, naturalness, P50/P95 latency, token cost, kích thước cửa sổ memory (`5–N`) và retry budget (`K`) | `TO VALIDATE` | Các giả thuyết và chỉ số hiệu năng cần đo đạc thực nghiệm; chưa có số đo thực tế. |
| Lựa chọn LLM provider cho tiếng Việt structured output (`OPEN-1`), rubric đánh giá người thật | `TO VALIDATE` | Cần benchmark so sánh có kiểm soát chi phí/license trước khi chốt. |
| Kết quả kiểm chứng năng lực mô hình / PoC (`P06-E01`..`P06-E04`) | `VALIDATED` | **None yet** — Hiện tại chưa có hạng mục nào đạt trạng thái `VALIDATED` trong P06. |
| Tích hợp native publishing lên TikTok/Shopee, chạy đa phiên đồng thời (multi-session concurrency), fine-tune LLM, kiến trúc fully agentic multi-agent, tối ưu conversion thương mại sớm | `DEFERRED` | Ngoài phạm vi MVP; trì hoãn tới các giai đoạn sau khi có đủ điều kiện kỹ thuật và pháp lý. |

---

## 6. Ánh xạ Rủi ro và Cổng nghiệm thu (Risk & Gate Mapping)

### 6.1. Rủi ro trực tiếp của P06

| Mã Rủi ro | Mức ưu tiên | Gate liên quan | Cơ chế tác động đến P06 | Biện pháp giảm thiểu & Bằng chứng cần thu thập |
| :--- | :--- | :--- | :--- | :--- |
| **`R05`** — Storytelling liên tục, ít lặp và bounded autonomy | `P0` | `G2`, `G6` | Trong phiên 1–2 giờ, AI có thể lặp lại luận điểm, bỏ quên mandatory topics khi bị comment ngắt, hoặc tự ý chuyển SKU gây loạn mạch kể. | Dùng `StoryPlan` có version, `StoryCheckpoint` chỉ cập nhật theo `PlaybackCompleted`, tracking intent/SKU/covered claims trong cửa sổ `5–N`. Kiểm chứng qua `P06-E01`, `P06-E02`, `P06-E03` và chấm mù bởi người thật. |
| **`R08`** — Claim safety, stale facts và Product/SKU integrity | `P0` | `G3`, `G4` | P06 có thể bịa công dụng thực phẩm, nhắc OCOP chưa xác minh, đọc giá cũ hoặc lấy fact của SKU A gán cho SKU B khi sinh câu trả lời nhanh. | Bắt buộc trích dẫn `evidence_id` từ `EvidenceBundle` của `P05`, kèm `knowledge_version` / `ocop_version` / `rights_version`; mọi candidate đều qua `P05 PublicationGate` và bounded rewrite; recheck trước commit (`P08`). Hard Gate: 0 vi phạm trong `P06-E04` và negative tests. |
| **`R13`** — Product overlay và độ thuyết phục của trải nghiệm bán hàng | `P1` | `G1`, `G6` | Dù văn bản đúng sự thật, câu thoại không tự nhiên, dài dòng hoặc không khớp với bố cục host-first + product overlay sẽ khiến người xem thiếu tin cậy. | Tạo `StoryChunk` gọn theo semantic breakpoint, phối hợp độ dài phù hợp nhịp nói host-first; đánh giá thông qua Human Blind Rubric (Naturalness, Narrative Coherence) với merchant/viewer thử nghiệm. |

### 6.2. Rủi ro phụ thuộc liên module (Dependency Risks)

| Mã Rủi ro | Mức ưu tiên | Gate | Module sở hữu chính | Ảnh hưởng tới P06 |
| :--- | :--- | :--- | :--- | :--- |
| **`R03`** | `P0` | `G2`, `G5` | Integration + `P02`/`P03`/`P04`/`P06` | Độ trễ sinh văn bản (kể cả khi bounded rewrite) cộng vào comment-to-speech latency tổng (`W1` mục tiêu P50/P95); bắt buộc giới hạn `K` retries và timeout fail-closed. |
| **`R04`** | `P0` | `G2`, `G3` | `P07` + `P08` | Nếu `P07` gộp nhóm (`AuthoritativeResponseGroup`) hoặc gắn sai SKU/intent, P06 sẽ trả lời lạc ngữ cảnh hoặc bỏ sót câu hỏi hợp lệ. |
| **`R06`** | `P0` | `G3`, `G5` | `P08` + `P04` | Lỗi duplicate/out-of-order event hoặc ACK giả từ `P04`/`P08` sẽ làm `RecentSpeechTracker` và `StoryCheckpoint` của P06 cập nhật sai, gây lặp lại chunk đã phát. |
| **`R10`** | `P0` | `G4`, `G6` | Backend / `P11` | Rò rỉ dữ liệu giữa các tenant hoặc lỗi phân quyền cho phép caller không hợp lệ chỉnh sửa `StoryPlan` / constraints giữa phiên live. |
| **`R15`** | `P0` | `G2`, `G3` | Technical Integration Owner | Khoảng cách giữa mock PoC (fake `PlaybackCompleted`, mock `P05`/`P08`) và hệ thống thật khi chuyển tích hợp sang `apps/api/`. |
| **`R16`** | `P0` | `G4`, `G6` | `P09` + `P05` + `P11` | Trạng thái OCOP thay đổi (hết hạn/thu hồi) giữa phiên nhưng P06 vẫn sử dụng `StoryPlan` hoặc chunk cache chứa claim OCOP cũ. |
| **`R17`** | `P0` | `G4`, `G6` | `P05` + `P09` + Legal | Phát ngôn thổi phồng công dụng chữa bệnh cho thực phẩm đóng gói (vi phạm pháp lý thực phẩm); P06 phải tuyệt đối tuân thủ danh sách `prohibited_claims` và fail-closed. |
