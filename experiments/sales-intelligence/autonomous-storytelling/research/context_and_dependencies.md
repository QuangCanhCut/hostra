# P06 — Bối cảnh Kiến trúc, Kiểm kê Tài liệu & Hợp đồng Phụ thuộc

> **Mục đích:** Cung cấp bức tranh đối chiếu chính xác giữa các tài liệu nguồn, mã nguồn hiện có và hợp đồng liên module (`P05`, `P07`, `P08/P09`, `P04`, `P10/Frontend`) cho Module **P06 (`Sales Intelligence & Autonomous Storytelling`)**. Mọi nhận định dưới đây đều được kiểm chứng trực tiếp từ tệp thực tế trong repository, nhánh liên quan và hồ sơ rà soát Tech Lead tại ngày `2026-11-26`.

---

## 1. Kiểm kê Tài liệu Nguồn & Mức độ Sẵn có (Source Document Audit)

| Tài liệu / Hiện vật | Phiên bản / Trạng thái | Vị trí trong Repo / Nhánh | Tình trạng sẵn có cho P06 |
| :--- | :---: | :--- | :--- |
| Root `AGENTS.md` | Hiện hành (`APPROVED`) | `AGENTS.md` | Có sẵn trên nhánh hiện tại (cơ chế tìm ngược lên thư mục cha — upward walk) |
| Scoped P06 Agent Rule | `v0.1` (`SELECTED FOR PoC (Directional)`) | `.agents/rules/p06-autonomous-storytelling.md` | Tệp rule dùng `trigger: model_decision`, giới hạn phạm vi cho P06 (theo `DR-P06-010`) |
| Docs Hub Index | Hiện hành | `docs/README.md` | Có sẵn; quy chuẩn vòng đời & nhãn trạng thái |
| Project Overview & Proposal | `v1.0` *(Cần chỉnh theo ACR-001/002)* | `docs/product/HOSTRA_AI_Project_Overview_Proposal_v1.0.docx` | **KHÔNG TỒN TẠI** trong repo (đã xác nhận thiếu tại `experiments/README.md` §9) |
| Solution Architecture Baseline | `v1.2` (`APPROVED` cho Stage 03) | `docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx` | Có sẵn; khóa `D01–D32`, `ACR-001/002`, `ARD-01..18`, `I-01..I-09` |
| Technical Risk Assessment | `v1.1` (`DRAFT` rà soát Stage 03) | `docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx` | Có sẵn; chứa `R05`, `R08`, `R13` và rủi ro phụ thuộc |
| Technical Research & PoC Plan | `v1.0` (`SELECTED FOR PoC`) | `docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx` | Có sẵn; chứa hồ sơ `P06.1–P06.14`, §6.2, `OPEN-1..3` |
| Research Decisions & Stage 04 ADR | Trống (`.gitkeep`) | `docs/03-technical-research/decisions/`, `docs/04-technical-design/adr/` | Chưa có tệp quyết định/ADR chính thức |
| Stage 04 API & Event Contract Spec (`HOSTRA-API-001`) | `v1.0 DRAFT` (`PROPOSED`) | `docs/04-technical-design/api/HOSTRA_AI_API_and_Event_Contract_Specification_v1.0_DRAFT.docx` | **CHƯA có** trên `research/p06-autonomous-storytelling`; hiện chỉ nằm trên nhánh anh em `research/p07-comment-understanding` (commit `a67854b`) |
| Stage 04 Database Design Spec (`HOSTRA-DB-001`) | `v1.0 DRAFT` (`PROPOSED`) | `docs/04-technical-design/data-models/HOSTRA_AI_Database_Design_Specification_v1.0_DRAFT.docx` | **CHƯA có** trên nhánh hiện tại; nằm trên `research/p07-comment-understanding` (commit `a67854b`) |
| Shared Contracts Package | Trống (`.gitkeep`) | `packages/contracts/` | Chưa đóng băng hợp đồng chính thức liên module |
| Frontend Decision Register & Packages | `v0.2` / `v0.4` (`APPROVED`) | `docs/product/frontend/DECISIONS.md` + `modules/*.docx` | Có sẵn (`Story Planner v0.2`, `Knowledge & Claims v0.2`, `Live Control Room v0.2`, `Products & OCOP v0.2`) |
| Frontend TypeScript Domain & Mock Types | `Mock-first` | `apps/web/src/types/{domain,m02,m03}.ts` | Có sẵn; phản ánh mô hình UI & một số drift cần đối chiếu |
| P05 PoC Code & Seed | `IN EXPERIMENT` | `experiments/sales-intelligence/knowledge-verification/` | Có sẵn tại local (`schemas.py`, `publication_gate.py`, `catalog_seed.json`, `REPORT_P05_POC_v0.1.md`) |
| P07 Contract & Taxonomy | `PROPOSED v0.1.3` | `research/p07-comment-understanding:.../comment-understanding/docs/` | Có sẵn trên nhánh anh em `research/p07-comment-understanding` (commit `ca95e15`) |
| P08/P09 & P04 & P02 PoC Code | `NOT STARTED` | `experiments/conversation-orchestration/scheduling-simulation/`, `realtime-media/streaming-benchmarks/`, `ai-presenter-media/voice-tts/` | Chỉ mới có `README.md`, chưa có mã Python chạy thực |

### Ghi chú cơ chế Antigravity Rule Discovery (`P06-OPEN-6`)
- Hệ thống nạp quy tắc từ hai nguồn đã được xác minh:
  1. `AGENTS.md`: được tìm theo cơ chế đi ngược lên thư mục cha (upward walk) từ workspace hiện tại.
  2. `.agents/rules/*.md`: hỗ trợ cơ chế kích hoạt có phạm vi như `trigger: model_decision` và `glob` (khác với `always_on` vốn nạp vào ngữ cảnh ở mọi tác vụ).
- Để tránh làm phình ngữ cảnh và rò rỉ quy ước riêng của P06 sang các module khác (P05, P07, Frontend), P06 sử dụng tệp quy tắc riêng `.agents/rules/p06-autonomous-storytelling.md` với **`trigger: model_decision`** giới hạn chặt cho phạm vi nghiên cứu và mã nguồn P06 (`DR-P06-010`).

---

## 2. Ma trận Sở hữu & Ranh giới Liên Module (Module Ownership & Boundary Matrix)

| Module | Trách nhiệm sở hữu chính thức | P06 được phép làm | P06 TUYỆT ĐỐI CẤM |
| :--- | :--- | :--- | :--- |
| **`P05` Knowledge & Gate** | Trích xuất `ProductFact`, `EvidenceChunk`, `ClaimRegistryEntry`; thực thi fail-closed `PublicationGate.evaluate()` | Đọc `EvidenceBundle` đã duyệt; gửi `SpeechCandidate` sang P05 kiểm chứng; kích hoạt bounded rewrite khi bị `BLOCK` | Tự duyệt fact/claim; tự hạ chuẩn gate; lặp lại nguyên văn cụm từ cấm khi từ chối câu hỏi y tế |
| **`P06` Storytelling** | Lập nháp `StoryPlan` (`StoryArc`), sinh `StoryChunk` / câu đáp, theo dõi `played_history`, rewrite có giới hạn, đề xuất `bridge` & `ProposedResponseCoverage` | Quản lý prompt, `StoryPlanner`, trạng thái đồ thị LangGraph tạm thời trong phạm vi 1 lần sinh candidate | Điều khiển playout; tự đổi `Active SKU`; tự cập nhật `StoryCheckpoint` từ graph checkpoint; tự commit trạng thái `ANSWERED` |
| **`P07` Comment Triage** | Chuẩn hóa text, moderation (`4` lớp), phân loại intent (`9` lớp), phân giải SKU (`7` chế độ), đề xuất gom nhóm (`ResponseGroupProposal`) | Nhận `CommentTask` đã qua triage từ P07/P08 (qua adapter), đọc `primary_intent`, `secondary_intents`, `referenced_sku_ids`, `sku_resolution_mode` | Tự xây bộ phân loại comment cạnh tranh với P07; tự đoán SKU khi P07 trả `UNCLEAR` hoặc `OUT_OF_CATALOG` |
| **`P08/P09` Orchestration** | Single logical writer cho `LiveSession`, `Active SKU`, `SpeechTurn` FSM, `ResponseGroup`, `StoryCheckpoint`, eligibility OCOP | Đề xuất candidate + metadata breakpoint + `ProposedResponseCoverage`; nhận ngữ cảnh (`active_sku_id`, `story_checkpoint`, `session_epoch`) | Thay thế P08 bằng LangGraph state; đổi `Active SKU` theo `referenced_sku_ids` trong comment |
| **`P04` Playout Runtime** | Single playout authority; phát âm thanh/video lên LiveKit; phát `PlaybackStarted` / `PlaybackCompleted` | Chỉ cập nhật `played_history` / `covered_topics` / `StoryCheckpoint` sau khi nhận `PlaybackCompleted` hợp lệ | Coi LLM xong / TTS xong / MuseTalk xong / LangGraph checkpoint là đã phát tới người xem |
| **`P02` Voice TTS** | Tổng hợp giọng nói tiếng Việt có kiểm soát (`VerifiedSpeechCandidate -> audio`) | Cung cấp text sạch dấu, đúng `sku_refs` và style tag hợp lệ sau khi qua P05 | Gửi candidate chưa qua P05 tới `P02` |
| **`P10` Studio & Viewer UI** | UI `Story Planner`, `Live Control Room`, `Viewer Live Room` | Cung cấp cấu trúc arc/diff cho AI Editing Assistant (`SS-X1`) và `safeSummary` cho vùng "AI sắp nói" (`CR-D6=A`) | Tự apply bản sửa StoryPlan khi Owner chưa bấm *Apply*/duyệt; lộ raw unverified claims lên UI |
| **`P11` Rights & Isolation** | Consent Rights Subject, `RightsStatus` (`ACTIVE/EXPIRED/REVOKED`), tenant isolation | Truyền đủ `tenant_id`, `rights_version` trong mọi truy vấn & `SpeechCandidate` | Cache hoặc phát lại nội dung khi quyền đã đổi version/thu hồi |

---

## 3. Kiểm tra Hợp đồng Chi tiết & Phân tích Sai lệch (Contract Inspection & Drift Analysis)

### 3.1. Hợp đồng P05 (`schemas.py` & `publication_gate.py` & `catalog_seed.json`)

Các lớp Pydantic v2 đang chạy thực tại [schemas.py](../knowledge-verification/schemas.py) và [publication_gate.py](../knowledge-verification/publication_gate.py):

- **Dữ liệu nguồn & tri thức:** `ProductFact` (`price_vnd`, `weight_display`, `expiry_display`, `origin`, `ingredients`, `storage_instructions`, `knowledge_version`, `approval_status`, `provenance`), `EvidenceChunk` (`evidence_id`, `sku_id`, `section`, `content`, `knowledge_version`, `approval_status`), `ClaimRegistryEntry` (`claim_id`, `category`: `ALLOWED` | `PROHIBITED` | `REQUIRES_OFFICIAL_VERIFICATION`, `requires_ocop_verified`), `EligibilitySnapshot` (`ocop_status`: `PENDING` | `VERIFIED` | `EXPIRED` | `REVOKED` | `UNVERIFIED`, `ocop_version`, `food_safety_verified`, `rights_status`: `ACTIVE` | `EXPIRED` | `REVOKED`, `rights_version`), và `EvidenceBundle`.
- **Giao diện kiểm duyệt:** `SpeechCandidate` (`candidate_id`, `tenant_id`, `session_id`, `sku_id`, `text`, `cited_evidence_ids`, `stated_price_vnd`, `mentions_ocop`, `knowledge_version`, `ocop_version`, `rights_version`) đi qua `PublicationGate(store).evaluate(candidate)` trả về `PublicationDecision` (`ALLOW` | `BLOCK`) kèm `13` mã `BlockReason`:
  `MISSING_EVIDENCE`, `UNAPPROVED_FACT`, `PRICE_MISMATCH`, `CROSS_SKU_VIOLATION`, `PROHIBITED_CLAIM`, `OCOP_NOT_VERIFIED`, `FOOD_SAFETY_UNVERIFIED`, `RIGHTS_INVALID`, `STALE_KNOWLEDGE_VERSION`, `STALE_OCOP_VERSION`, `STALE_RIGHTS_VERSION`, `PROMPT_INJECTION_DETECTED`, `TENANT_MISMATCH`.
- **Kho phiên bản PoC:** `VersionedKnowledgeStore.from_seed_file(...)` hỗ trợ `clone()`, `update_price()`, `update_ocop_status()`, `update_rights_status()` phục vụ kiểm thử TOCTOU (`t0` trước TTS -> `t1` đổi dữ liệu -> `t2` sát commit).

**Ba bẫy tích hợp đã kiểm chứng trong code P05 hiện tại:**

1. **Bẫy 1 — `SpeechCandidate` đơn SKU vs. `COMPARE_PRODUCTS` / `MULTI_SKU` (`CF-P06-01` / `P06-OPEN-5`):**
   `schemas.py` hiện định nghĩa `SpeechCandidate.sku_id: str` (1 SKU duy nhất) và `PublicationGate.evaluate()` kiểm tra `chunk.sku_id != candidate.sku_id` -> lập tức trả `CROSS_SKU_VIOLATION`! Trong khi đó, Stage 03 §06.2 mô tả `VerifiedSpeechCandidate.sku_refs: list[str]`, còn P07 có `COMPARE_PRODUCTS` và `MULTI_SKU` (`referenced_sku_ids: list[str]`) lẫn câu hỏi chính sách chung cấp shop (`NOT_APPLICABLE`, `referenced_sku_ids = []`) và ca không xác định được SKU (`UNCLEAR` / `OUT_OF_CATALOG`).
   *Cách xử lý trong P06 PoC:* Chuẩn hóa hợp đồng mock có phiên bản `p06-mock-v0.1` tại adapter `guardrails/p05_gate_adapter.py` (xem chi tiết tại **Mục 4**); giữ nguyên tuyệt đối `../knowledge-verification/schemas.py`.
2. **Bẫy 2 — Khớp chuỗi con (Substring Matching) trong `DEFAULT_PROHIBITED_PHRASES`:**
   `publication_gate.py` kiểm tra `phrase in text_lower` theo khớp chuỗi con (ví dụ `"chữa khỏi"`, `"chữa bệnh"`, `"chữa đau dạ dày"`, `"chữa tiểu đường"`, `"phòng ngừa ung thư"`, `"chữa ung thư"`, `"thay thế thuốc"`). Nếu khách hỏi mồi `"uống trà này chữa tiểu đường đúng không?"` (`ASK_SAFETY_SUITABILITY`) và P06 trả lời lịch sự kiểu *"Sản phẩm này không có tác dụng chữa tiểu đường..."*, `PublicationGate` **vẫn CHẶN** (`PROHIBITED_CLAIM`) vì chứa nguyên chuỗi `"chữa tiểu đường"`!
   *Cách xử lý trong P06:* Prompt và guardrail bắt buộc diễn đạt từ chối trung tính, **tuyệt đối không lặp lại nguyên văn cụm từ y tế cấm** (ví dụ: *"Đây là thực phẩm tự nhiên dùng hằng ngày, không phải sản phẩm điều trị y khoa; khách hàng có bệnh lý nền vui lòng tham khảo ý kiến bác sĩ."*), đồng thời bổ sung unit test cho `prohibited_echo_guard`.
3. **Bẫy 3 — `SKU-CASHEW-03` trong `catalog_seed.json` đang `OCOP PENDING`:**
   Trong `knowledge-verification/data/catalog_seed.json`, `SKU-HONEY-01` và `SKU-TEA-02` có `ocop_status: "VERIFIED"`, nhưng **`SKU-CASHEW-03` có `ocop_status: "PENDING"`** (có chủ đích để test negative gate `P05-E03`). Nếu P06 lấy trực tiếp `catalog_seed.json` chạy kịch bản kể chuyện `3` SKU đủ điều kiện, `SKU-CASHEW-03` sẽ bị `PublicationGate` chặn với `OCOP_NOT_VERIFIED`.
   *Cách xử lý:* P06 phải tách rõ fixture kịch bản hợp lệ (cả 3 SKU đều `VERIFIED` trong bản sao fixture riêng cho test tích cực của P06) và fixture negative test giữ `SKU-CASHEW-03` ở `PENDING` để kiểm chứng chặn đúng `G4`.

---

### 3.2. Hợp đồng P07 (`p07-contract-v0.1.md` — `PROPOSED v0.1.3`)

Trích xuất từ `research/p07-comment-understanding` (commit `ca95e15`):

- **Input/Output Boundary:** `AcceptedCommentEnvelope` + `SessionTriageContext` (chứa `active_sku_id`, `pinned_catalog` 2–5 SKU có `product_version_id` & `knowledge_snapshot_id`, `viewer_thread_state` tách theo `guest_session_id`, `open_queued_groups`) -> `TriageProcessResponse` gồm `CommentTriageRecord` + `ResponseGroupProposal` (chứa `proposal_id` tất định, `partition_guard_key`, `intent_coverage_scope`, `secondary_intents`, `priority_hint`, `proposed_expires_at`).
- **Bộ phân loại `4 / 9 / 7` (`PROPOSED v0.1.3`):**
  - `moderation_status` (`4`): `ELIGIBLE` | `SPAM_FLOOD` | `ABUSE_BLOCKED` | `PROMPT_INJECTION` (ưu tiên `PROMPT_INJECTION > ABUSE_BLOCKED > SPAM_FLOOD > ELIGIBLE`).
  - `primary_intent` (`9`, theo thứ tự ưu tiên giảm dần khi đa ý): `COMPARE_PRODUCTS` > `ASK_SAFETY_SUITABILITY` > `ASK_PRICE_PROMO` > `ASK_ORIGIN_OCOP` > `ASK_SPEC_USAGE` > `ASK_SHIPPING_RETURN` > `PURCHASE_INTENT_CTA` > `SOCIAL_CHITCHAT` > `UNCLEAR_OR_OTHER`. Các ý phụ được bảo toàn trong `secondary_intents` và hợp lại thành `intent_coverage_scope`.
  - `sku_resolution_mode` (`7`): `EXPLICIT_SINGLE`, `CONTEXTUAL_SINGLE`, `MULTI_SKU`, `IMPLICIT_ACTIVE`, `UNCLEAR`, `OUT_OF_CATALOG`, `NOT_APPLICABLE`. Với `UNCLEAR` / `OUT_OF_CATALOG` / `NOT_APPLICABLE`, `referenced_sku_ids` bắt buộc rỗng `[]`.
- **Hợp đồng `AuthoritativeResponseGroup` (sở hữu bởi P08/P09):** Khi `P08` giao việc cho `P06`, nhóm đã chuyển sang `COMMITTED` với danh sách `member_comment_ids` bị khóa cứng và bắt buộc truyền `required_intent_coverage` + `CommentTriageRecord` thành viên (không chỉ câu đại diện đơn lẻ) để tránh rơi ý định phụ (ví dụ ý `ASK_SAFETY_SUITABILITY` hoặc `ASK_SHIPPING_RETURN`).
- **Ranh giới Adapter tại P06:** P06 định nghĩa `CommentTask` adapter nhận trực tiếp output đã qua triage/nhóm (không nhận raw comment để phân loại lại). Nếu P06 chỉ đáp được một phần câu hỏi đa ý (vì 1 phần thiếu dữ liệu/bị gate chặn), P06 phải trả về `ProposedResponseCoverage` rõ ràng (`covered_intents` / `uncovered_intents`) cho P08/P09 (`PRE-INTEGRATION REQUIRED`, chi tiết tại **Mục 4**).

---

### 3.3. Hợp đồng P08/P09 & Sai lệch với Stage 04 `DRAFT` / Frontend Mocks

Đối chiếu giữa `HOSTRA-API-001` & `HOSTRA-DB-001` (`v1.0 DRAFT`, commit `a67854b` trên nhánh `research/p07-comment-understanding`) với `apps/web/src/types/{domain,m02,m03}.ts`:

1. **Các trục trạng thái độc lập của `LiveSession` (`domain.ts` khớp kiến trúc):**
   `SessionLifecycle` (`CREATED..CANCELLED`), `AiExecutionState` (`ACTIVE`, `PAUSE_REQUESTED`, `PAUSED`, `RESUMING`, `BLOCKED`), `MediaHealthState` (`HEALTHY`, `DEGRADED`, `FAILED`), `DialogueSubstate` (`PLAYING_SCRIPT`, `INTERRUPT_PENDING`, `ANSWERING_COMMENT`, `RESUMING`, `IDLE`). `PAUSE_AI` không dừng stream (`I-05`).
2. **Sai lệch Enum `SpeechTurn` (`HOSTRA-DB-001` vs. Frontend `m03.ts`):**
   - `HOSTRA-DB-001` (`PROPOSED`) dùng 9 trạng thái: `PROPOSED` -> `VALIDATED` -> `PREPARING` -> `READY` -> `COMMITTED` -> `PLAYING` -> `COMPLETED` (hoặc `CANCELLED`, `EXPIRED`).
   - Frontend mock `apps/web/src/types/m03.ts` (`SpeechTurnPhase`) dùng: `PLANNING`, `VERIFYING`, `PREPARING_AUDIO`, `LIP_SYNC`, `READY`, `COMMITTED`, `PLAYING`, `PLAYBACK_COMPLETED`, `CANCELLED`.
   *Quy ước cho P06:* P06 chỉ xuất `SpeechCandidate` (tương ứng giai đoạn trước `COMMITTED`) và lắng nghe kết quả `COMPLETED` / `PlaybackCompleted`; mọi mapping giữa `Stage 04 DRAFT` và `m03.ts` phải nằm trong `adapters/mocks/`, không khóa cứng enum Frontend làm chuẩn backend.
3. **Sai lệch `SessionCommand` (`HOSTRA-API-001` vs. Frontend `m03.ts` / Design Packages):**
   - `HOSTRA-API-001` (§7 `PROPOSED`) liệt kê 8 lệnh: `START`, `PAUSE_AI`, `RESUME_AI`, `SWITCH_SKU`, `SKIP_PENDING`, `STOP`, `EMERGENCY_STOP`, `REQUEST_LIVE_REVISION`.
   - `m03.ts` (`RuntimeCommandType`) có thêm `PRIORITIZE_COMMENT` (được `CR-D7=A` phê duyệt cho hàng đợi pre-commit) và trong `Story Planner` / tài liệu cũ còn nhắc ý tưởng điều hướng topic (`FORCE_NEXT_TOPIC`).
   *Quy ước cho P06:* Hỗ trợ nhận tín hiệu `PAUSE_AI`/`RESUME_AI`, `SWITCH_SKU` (chỉ áp dụng khi P08 báo `APPLIED` tại safe boundary), `SKIP_PENDING`, và `REQUEST_LIVE_REVISION` (tạo bản nháp mới, chờ Owner duyệt).
4. **Khoảng trống SQL DDL trong `HOSTRA-DB-001 v1.0 DRAFT`:**
   `HOSTRA-DB-001` đã liệt kê các thực thể `story_plans`, `story_revisions`, `story_checkpoints` (và `story_turns_played`) trong sơ đồ quan niệm, nhưng phần DDL SQL nền tảng ở §6 chưa cung cấp bảng vật lý cho 3 thực thể Story này. P06 PoC sẽ định nghĩa schema Pydantic v2 chuẩn mực cho `StoryPlan`, `StoryRevision`, `StoryCheckpoint` để làm đầu vào cho đợt hoàn thiện `HOSTRA-DB-001` ở Stage 04/06.

---

### 3.4. Hợp đồng P04 Playout & Giao diện Frontend Story Planner / Control Room

- **Story Planner (`Story Planner v0.2` & `m02.ts`):**
  - `StoryPlanDetail` chứa `planRevision`, `approvedRevision`, `approvalStatus` (`DRAFT` | `REVIEW_REQUIRED` | `APPROVED` | `INVALIDATED`), `dirtyReason`, `arcs: StoryArcItem[]` (`position`, `title`, `durationMin`, `skuId`, `topic`, `previewText`, `factRefs`, `reviewed`).
  - **Quy tắc Owner Approval & Dirty-Draft Invalidation (`SS-D4=A`):** Mọi chỉnh sửa mới (thủ công hoặc bấm *Apply to Draft* từ `StoryAiProposal` theo `SS-X1`) đều làm mất hiệu lực bản duyệt cũ (`INVALIDATED`), buộc Owner duyệt lại `StoryRevision` gắn với phiên bản Presenter/SKU/Knowledge cụ thể.
- **Live Control Room (`Live Control Room v0.2` & `CR-D6=A`):**
  - Vùng **"AI sắp nói"** chỉ hiển thị `safeSummary` đã kiểm chứng an toàn + `sourceRef` kèm nhãn **`Dự kiến · Chưa phát`** (`CR-D6=A`), tuyệt đối không hiển thị text nháp chưa qua P05 hoặc cam kết chắc chắn sẽ phát.
- **Playout Boundary (`P04`):** `StoryCheckpoint` và `covered_topics` trong P06 **chỉ tiến lên** khi nhận sự kiện `media.playback_completed` (`PlaybackCompleted`) khớp `(session_id, session_epoch, turn_id)`. Nếu `P04` báo lỗi / `UNKNOWN` / `DEGRADED`, P06 không tự replay và chuyển sang dùng approved pre-generated chunk còn hiệu lực hoặc nhường `P04 SAFE_FALLBACK`.

---

## 4. Đặc tả Căn chỉnh Hợp đồng Liên Mô-đun (`P06-OPEN-5`, `p06-mock-v0.1`)

Để tháo gỡ độ vênh hợp đồng giữa `P05 schemas.py`, `Stage 03 §06.2 VerifiedSpeechCandidate`, `Stage 04 DRAFT` và `P07 p07-contract-v0.1.md` **mà không chỉnh sửa mã nguồn của các module ngoài**, P06 định nghĩa bộ hợp đồng mock có phiên bản **`contract_version = "p06-mock-v0.1"`** (theo `DR-P06-009`).

### 4.1. Bảng đối chiếu sai lệch giữa các hợp đồng nguồn

| Chiều đối chiếu | `P05 schemas.py` (Local PoC) | `Stage 03 §06.2` (`VerifiedSpeechCandidate`) | `P07 p07-contract-v0.1.md` (`PROPOSED v0.1.3`) | `Stage 04 DRAFT` (`HOSTRA-API/DB-001`) | Giải pháp căn chỉnh trong `p06-mock-v0.1` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tham chiếu SKU** | `sku_id: str` (đơn SKU bắt buộc) | `sku_refs: list[str]` | `sku_resolution_mode` (`7` mode) + `referenced_sku_ids: list[str]` | `SpeechTurn` / `ResponseGroup` cần hỗ trợ ngữ cảnh phiên & SKU | Định nghĩa `TargetScopeMode` (`4` biến thể) + `sku_refs: list[str]` tại P06 adapter; map từng SKU sang `P05` khi kiểm tra |
| **Câu hỏi so sánh đa SKU** | Khác `candidate.sku_id` -> `CROSS_SKU_VIOLATION` | Cho phép `len(sku_refs) >= 2` | `MULTI_SKU` / `COMPARE_PRODUCTS` | Cần xác minh nhiều SKU cùng lượt | Dùng `MULTI_SKU_COMPARE` với per-SKU `EvidenceBundle` map & claim-to-SKU attribution |
| **Câu hỏi chính sách chung cấp shop** | Chưa có nhánh `sku_id` rỗng hợp lệ | `sku_refs = []` | `NOT_APPLICABLE`, `referenced_sku_ids = []` | Chính sách giao hàng/đổi trả ở cấp shop/session | Dùng `SHOP_WIDE_POLICY` với `sku_refs = []` + policy bundle cấp workspace/session |
| **Câu hỏi không rõ / ngoài catalog** | Chưa phân biệt với policy chung | Cần tránh bịa thông số sản phẩm | `UNCLEAR` / `OUT_OF_CATALOG`, `referenced_sku_ids = []` | Cần xử lý từ chối/làm rõ an toàn | Dùng `UNRESOLVED_SKU` **tách biệt hoàn toàn** với `SHOP_WIDE_POLICY` |
| **Độ phủ câu hỏi đa ý & gộp nhóm** | Không quản lý độ phủ comment | Chưa đặc tả map chi tiết | `AuthoritativeResponseGroup` + `required_intent_coverage` | `ResponseGroup` chuyển trạng thái qua P08 | P06 xuất `ProposedResponseCoverage`; P08/P09 chỉ commit `ANSWERED` khi có `P04 PlaybackCompleted` |

### 4.2. Đặc tả 4 biến thể `TargetScopeMode` và Bất biến Kiểm chứng (Invariants)

Mọi đầu vào sinh lời thoại từ `CommentTask` hoặc `StoryArc` trong P06 được chuẩn hóa sang một trong 4 giá trị `TargetScopeMode`:

| `TargetScopeMode` | Quy tắc `sku_refs` | Ngữ cảnh / Nguồn dữ liệu bắt buộc | Bất biến (Invariants) & Quy tắc Guardrail |
| :--- | :--- | :--- | :--- |
| **`SINGLE_SKU`** | `sku_refs = [sku_id]` (`len == 1`) | Đúng `1` `EvidenceBundle` thuộc `sku_id` (được phép là `Active SKU` hoặc `Referenced SKU`, **không** tự đổi `Active SKU`). | Kiểm tra nghiêm ngặt `price_vnd`, `ocop_status == VERIFIED`, `food_safety_verified`, `rights_status == ACTIVE`, `knowledge_version` và `cited_evidence_ids` đúng `sku_id` trực tiếp qua `P05 PublicationGate`. |
| **`MULTI_SKU_COMPARE`** | `sku_refs = [sku_a, sku_b, ...]` (`len >= 2`) | **Per-SKU `EvidenceBundle` map** (`dict[sku_id, EvidenceBundle]`) cho toàn bộ SKU có mặt trong `sku_refs`. | Bắt buộc **claim-to-SKU attribution**: mỗi nhận định/giá/chứng nhận OCOP trong `SpeechCandidate` phải gắn đúng với `sku_id` và `evidence_id` tương ứng trong map; adapter tách kiểm chứng P05 theo từng SKU + kiểm tra chéo không trộn thuộc tính giữa SKU A và SKU B, tránh lỗi giả `CROSS_SKU_VIOLATION` của P05 đơn-SKU. |
| **`SHOP_WIDE_POLICY`** | `sku_refs = []` (`len == 0`) | **Verified workspace/session policy bundle** (chính sách vận chuyển, đổi trả, quy định chung của shop đã được merchant duyệt & còn hiệu lực version). | Hợp lệ để trả lời sự thật (`factual answer`) dựa trên `policy_evidence_ids` đã duyệt; không được gán nhầm thông số của `Active SKU` nếu câu hỏi là chính sách chung, và không được bịa chính sách ngoài policy bundle. |
| **`UNRESOLVED_SKU`** | `sku_refs = []` (`len == 0`) | Bắt buộc đi kèm `unresolved_reason` ∈ `{AMBIGUOUS_SKU, OUT_OF_CATALOG, MISSING_CONTEXT}` (tương ứng `P07 UNCLEAR` / `OUT_OF_CATALOG` hoặc thiếu ngữ cảnh). | **Tách biệt tuyệt đối khỏi `SHOP_WIDE_POLICY`!** Cấm tuyệt đối trích dẫn thông số kỹ thuật, giá bán, khuyến mãi hay trạng thái OCOP của bất kỳ sản phẩm nào (kể cả `Active SKU` nếu chưa xác định người xem đang hỏi SKU đó). **CHỈ** cho phép: (a) hỏi làm rõ lịch sự (`CLARIFICATION_ONLY`), hoặc (b) chuyển hướng an toàn khi sản phẩm nằm ngoài danh mục phiên (`OUT_OF_CATALOG` redirect). |

### 4.3. Giao thức Độ phủ Phản hồi Một phần & Ánh xạ Comment-to-Candidate (`ProposedResponseCoverage`)

Khi P08 giao một `AuthoritativeResponseGroup` gồm nhiều bình luận thành viên hoặc câu hỏi đa ý (`required_intent_coverage`), P06 có thể chỉ trả lời được một phần do thiếu bằng chứng hoặc một ý phụ bị cổng P05 chặn. Khi đó P06 bắt buộc xuất kèm đối tượng **`ProposedResponseCoverage`**:

- **`response_group_id`**: Định danh nhóm bình luận do P08 cấp.
- **`covered_comment_ids: list[str]`**: Tập các `comment_id` thành viên thực sự được phản hồi trong `SpeechCandidate`.
- **`covered_intents: list[str]`**: Các intent trong `required_intent_coverage` đã được đáp ứng kèm bằng chứng hợp lệ.
- **`uncovered_intents: list[str]`**: Các intent còn thiếu bằng chứng, bị `BLOCK` tại P05, hoặc chủ đích tách sang lượt sau.
- **`coverage_mode`**:
  - `FULL`: Phủ toàn bộ `covered_comment_ids` và `required_intent_coverage` (`uncovered_intents == []`).
  - `PARTIAL`: Chỉ phủ được một phần intent/comment có bằng chứng hợp lệ; phần còn lại được khai báo tường minh trong `uncovered_intents`.
  - `CLARIFICATION_ONLY`: Áp dụng cho `UNRESOLVED_SKU` (`AMBIGUOUS_SKU` / `MISSING_CONTEXT`) — chỉ hỏi lại làm rõ, không khẳng định fact/giá/OCOP.
  - `ABSTAIN_NO_EVIDENCE`: Không có bằng chứng/quyền hợp lệ hoặc gặp ca `OUT_OF_CATALOG` / từ chối an toàn — không phát biểu fact chưa kiểm chứng.

> **Bất biến Sở hữu Trạng thái (`ARD-06` & `P04` Boundary):** `ProposedResponseCoverage` chỉ là **đề xuất** do P06 đính kèm vào `SpeechCandidate`. P06 **không được phép** đánh dấu comment hay nhóm bình luận là `ANSWERED`. Chỉ **`P08/P09`** mới có quyền commit trạng thái `ANSWERED` / cập nhật độ phủ chính thức, và **CHỈ SAU KHI** nhận sự kiện **`P04 PlaybackCompleted`** hợp lệ khớp `(session_id, session_epoch, turn_id)`.

### 4.4. Giới hạn của Hợp đồng Mock `p06-mock-v0.1`

- `p06-mock-v0.1` là **hợp đồng mock nội bộ phục vụ PoC P06** (`SELECTED FOR PoC (Directional)`), **KHÔNG phải** hợp đồng đóng băng trong `packages/contracts/` và chưa thay thế `HOSTRA-API-001` / `HOSTRA-DB-001`.
- Mọi bản ghi chạy (`manifest.json`) bắt buộc ghi rõ `contract_version = "p06-mock-v0.1"`.
- Trước Stage 06 hoặc trước khi tích hợp thật vào `apps/api/`, các owner **`P05`, `P06`, `P07`, `P08`** phải ký duyệt hợp đồng canonical thống nhất cho `TargetScopeMode` / `sku_refs` và `ProposedResponseCoverage` (`P06-OPEN-5`).

---

## 5. Ma trận Phụ thuộc: Mock trong PoC vs. Tích hợp Thật

| Thành phần phụ thuộc | Trạng thái trong P06 PoC (`M4` Research) | Cách mock / kết nối trong `src/p06/` | Yêu cầu cho Tích hợp Thật (`M3/M4/M7`) |
| :--- | :--- | :--- | :--- |
| **LLM Provider** | `SELECTED FOR PoC (Directional)` (`P06-OPEN-1`) | Kiến trúc 3 tầng qua `LLMProvider` + `ProviderFactory`: `MockLLMProvider` (`unit_test`), `OllamaLocalProvider` (`local_smoke_test` CPU `Qwen3 1.7B/4B`), `GeminiAPIProvider` (`formal_experiment` `Flash`/`Flash-Lite`) | Chốt model ID, quota, latency P95, structured output tiếng Việt, ngân sách & duyệt DPA/privacy |
| **P05 Knowledge & Gate** | `IN EXPERIMENT` (CPU local) | Import/gọi `PublicationGate` & `VersionedKnowledgeStore` qua `p05_gate_adapter.py`; hỗ trợ `TargetScopeMode` theo `p06-mock-v0.1` | PostgreSQL FTS/pgvector thật + đồng bộ schema `sku_refs` / đa SKU (`P06-OPEN-5`) |
| **P07 Comment Understanding** | `PROPOSED v0.1.3` (nhánh `p07`) | `MockCommentTaskFeed` phát `CommentTask` chuẩn theo `ResponseGroupProposal` (`4/9/7`) & `p06-mock-v0.1` | Kết nối queue/port P07 -> P08 thật với `RequiredIntentCoverage` |
| **P08/P09 Orchestrator** | `NOT STARTED` | `MockSessionOrchestrator` với fake clock, cung cấp `active_sku_id`, safe boundary, `StoryCheckpoint` & xử lý `ProposedResponseCoverage` | PostgreSQL transactional outbox, Redis Streams, single-writer FSM & epoch fencing |
| **P04 Media Playout** | `NOT STARTED` | `MockPlaybackAckBus` phát giả lập `PlaybackCompleted` / timeout / interrupt có seed | Event `media.playback_completed` từ GStreamer/LiveKit playout clock thật |
| **P02 Voice TTS** | `NOT STARTED` | Không gọi TTS thật trong vòng PoC (ước lượng độ dài phát theo tốc độ đọc ký tự/giây trong simulator) | Tích hợp streaming/batch TTS deadline trong budget `W1` (P50 <= 7s / P95 <= 10s) |
