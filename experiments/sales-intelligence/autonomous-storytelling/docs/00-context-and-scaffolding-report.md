# Báo cáo Session 01 — Khám phá Bối cảnh, Kiến trúc Nghiên cứu & Khởi tạo Khung P06

| Thuộc tính | Giá trị |
| :--- | :--- |
| **Ngày lập báo cáo** | `2026-11-26` |
| **Nhánh Git / Commit gốc** | `research/p06-autonomous-storytelling` (`030682c` — `Merge pull request #5 from QuangCanhCut/feat/frontend-foundation`) |
| **Phạm vi thực hiện** | `Stage 03 — Context Discovery, Research Architecture, Minimal Scaffolding & Agent Documentation` |
| **Module mục tiêu** | `P06 — Sales Intelligence & Autonomous Storytelling` (`experiments/sales-intelligence/autonomous-storytelling/`) |
| **Trạng thái tổng thể** | `COMPLETED (Scaffolding) \| P06-E01..E04: NOT STARTED` *(Chưa có mã thực thi `src/p06/` và chưa có kết quả thực nghiệm `VALIDATED`)* |

---

## 1. Báo cáo Hiểu biết Bối cảnh (Context Understanding Report)

### 1.1. Phạm vi hiện vật đã kiểm tra trực tiếp

**Trên nhánh hiện tại (`research/p06-autonomous-storytelling`, commit `030682c`):**
- Quản trị & quy tắc cấp repo: `AGENTS.md`, `README.md`, `docs/README.md`, `docs/05-implementation/development-guides/ENVIRONMENT_SETUP_AUDIT.md`, `experiments/README.md`, `experiments/sales-intelligence/README.md`.
- Tài liệu kiến trúc, rủi ro & kế hoạch Stage 01–03:
  - `docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx`
  - `docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx`
  - `docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx`
- Tài liệu thiết kế Frontend & type mocks:
  - `docs/product/frontend/DECISIONS.md` cùng các gói `v0.2` (`Story Planner & Live Session`, `Knowledge & Claims`, `Live Control Room`, `Products & OCOP`)
  - `apps/web/src/types/domain.ts`, `apps/web/src/types/m02.ts`, `apps/web/src/types/m03.ts`
- Module anh em cùng nhóm Sales Intelligence (`P05`):
  - `experiments/sales-intelligence/knowledge-verification/schemas.py`
  - `experiments/sales-intelligence/knowledge-verification/publication_gate.py`
  - `experiments/sales-intelligence/knowledge-verification/data/catalog_seed.json`
  - `experiments/sales-intelligence/knowledge-verification/REPORT_P05_POC_v0.1.md`
- Trạng thái P06 trước scaffolding: `experiments/sales-intelligence/autonomous-storytelling/README.md` (115–132 lines gốc) và `.gitkeep`.

**Kiểm tra chỉ-đọc trên nhánh anh em (`research/p07-comment-understanding`, không checkout/merge):**
- Commit `ca95e15`: `experiments/sales-intelligence/comment-understanding/docs/p07-contract-v0.1.md` (`PROPOSED v0.1.3`), cùng bộ tài liệu chuẩn bị P07.
- Commit `a67854b`: `docs/04-technical-design/api/HOSTRA_AI_API_and_Event_Contract_Specification_v1.0_DRAFT.docx` (`HOSTRA-API-001`) và `docs/04-technical-design/data-models/HOSTRA_AI_Database_Design_Specification_v1.0_DRAFT.docx` (`HOSTRA-DB-001`).

### 1.2. Hiện vật bị thiếu hoặc lệch giữa các nhánh

1. **`HOSTRA_AI_Project_Overview_Proposal_v1.0.docx` không tồn tại trên toàn bộ lịch sử Git** (`git log --all --full-history -- "*Project_Overview*"` trả rỗng). Khoảng trống này đã được xác nhận trong `experiments/README.md` §9; tuyệt đối không suy đoán nội dung từ tên tệp.
2. **Tài liệu Stage 04 (`HOSTRA-API-001` & `HOSTRA-DB-001` `v1.0 DRAFT`)** hiện chỉ tồn tại trên nhánh `research/p07-comment-understanding` (từ commit `a67854b`), **chưa có** trên nhánh `research/p06-autonomous-storytelling` (`030682c`).
3. **Thư mục quyết định và hợp đồng chung:** `docs/03-technical-research/decisions/`, `docs/04-technical-design/adr/` và `packages/contracts/` mới chỉ có `.gitkeep`, chưa có ADR hay Pydantic/OpenAPI contracts đóng băng liên module.
4. **Các module phụ thuộc (`P08/P09`, `P04`, `P02`):** Các thư mục `scheduling-simulation/`, `streaming-benchmarks/`, `voice-tts/` hiện mới có `README.md`, ở trạng thái `NOT STARTED`.

### 1.3. Phạm vi xác nhận, bất biến (`I-01`–`I-09`), rủi ro & gates

- **Phạm vi MVP đã xác nhận (`CONFIRMED REQUIREMENT`):**
  - `ACR-001`: Presenter tạo offline từ **01 ảnh chân dung** có sự đồng ý hợp lệ của Rights Subject bằng **PhotoMaker + Wan2.2 Animate**, phát live đồng bộ khẩu hình qua **MuseTalk 1.5** (`P01–P03`). Không dùng người dẫn quay trực tiếp (filmed-host), Physical Operator hay Digital Human Marketplace.
  - `ACR-002`: Giới hạn **2–5 SKU thực phẩm đóng gói** mỗi phiên, bắt buộc `OCOP: VERIFIED` (do `P09` xác minh) và đáp ứng điều kiện an toàn thực phẩm.
  - Phòng live: **01 phiên đồng thời**, **HOSTRA Private Live Room** (invite-only qua LiveKit, subscribe-only cho viewer), mục tiêu đầu ra **`720p`, `25–30 FPS`** (`CONFIRMED REQUIREMENT`; năng lực đạt thực tế `TO VALIDATE`). TikTok/Shopee/OBS/checkout thuộc phạm vi `DEFERRED`.
- **Các bất biến cốt lõi áp dụng trực tiếp cho P06 (`I-01`–`I-09`):**
  - `I-01`, `I-04`, `I-07`: `P08/P09` là single logical writer cho `LiveSession`, `Active SKU`, `SpeechTurn` FSM và `StoryCheckpoint`; bình luận nhắc SKU khác (`referenced_sku_id`) không tự đổi `Active SKU`.
  - `I-02`: Mọi lời thoại trước khi tới TTS/playout phải qua `P05 PublicationGate` (fail-closed).
  - `I-03`, `I-06`: `P04` là single playout authority; hoàn thành LLM/TTS/MuseTalk hay LangGraph checkpoint không đồng nghĩa `PlaybackCompleted`.
- **Rủi ro & Gates:**
  - Rủi ro trực tiếp của P06: **`R05`** (kể chuyện lặp ý / mất mạch sau ngắt), **`R08`** (bịa thông số, giá, khuyến mãi hoặc claim cấm), **`R13`** (chất lượng thuyết phục, độ tự nhiên tiếng Việt và overlay).
  - Rủi ro phụ thuộc liên module: **`R03`** (budget latency `W1` server comment-to-playout P50 <= 7s / P95 <= 10s), **`R04`** (phân loại/gom nhóm bình luận P07), **`R06`** (độ đúng ACK/playout P04/P08), **`R10`** (cô lập tenant), **`R15`** (khoảng cách thiết kế/mock với code thật), **`R16`** (xác minh OCOP P09), **`R17`** (cấm gán công dụng thuốc cho thực phẩm).
  - Gates nghiệm thu liên quan: **`G2`**, **`G4`**, **`G6`**.

### 1.4. Hiện vật tái sử dụng từ P05, P07 & Frontend Constraints

- **P05 (`knowledge-verification/` — `IN EXPERIMENT`):** Tái sử dụng trực tiếp `schemas.py` (`ProductFact`, `EvidenceChunk`, `ClaimRegistryEntry`, `EligibilitySnapshot`, `SpeechCandidate`, `PublicationDecision`, `13` mã `BlockReason`), `publication_gate.py` (`PublicationGate`, `VersionedKnowledgeStore`, `DEFAULT_PROHIBITED_PHRASES`), `data/catalog_seed.json`. Đã kiểm chứng **2 bẫy dữ liệu/kiểm duyệt** quan trọng (cùng bẫy đơn SKU `CF-P06-01`):
  1. `SKU-CASHEW-03` trong `catalog_seed.json` cố tình đặt `ocop_status: "PENDING"` (`ocop_code: null`) để phục vụ negative test `P05-E03` — không được lấy thẳng làm SKU positive trong `P06-E01`.
  2. `DEFAULT_PROHIBITED_PHRASES` kiểm tra `phrase in text_lower` theo khớp chuỗi con (ví dụ `"chữa tiểu đường"`, `"chữa bệnh"`). Nếu P06 trả lời từ chối bằng cách lặp lại cụm từ người xem hỏi (*"Trà này không chữa tiểu đường..."*), cổng P05 vẫn chặn (`PROHIBITED_CLAIM`). Bắt buộc xây `prohibited_echo_guard` và prompt từ chối trung tính.
- **P07 (`p07-contract-v0.1.md` — `PROPOSED v0.1.3`):** Phân loại theo kiến trúc **`4 / 9 / 7`**: `4` trạng thái moderation (`ELIGIBLE`, `SPAM_FLOOD`, `ABUSE_BLOCKED`, `PROMPT_INJECTION`), `9` `primary_intent` theo thứ tự ưu tiên + `secondary_intents`/`intent_coverage_scope`, `7` `sku_resolution_mode` (`EXPLICIT_SINGLE`, `CONTEXTUAL_SINGLE`, `MULTI_SKU`, `IMPLICIT_ACTIVE`, `UNCLEAR`, `OUT_OF_CATALOG`, `NOT_APPLICABLE`). P06 nhận `CommentTask` / `AuthoritativeResponseGroup` từ P08, không tự phân loại lại raw comment.
- **Frontend (`Story Planner v0.2` & `Live Control Room v0.2`):** Khóa `SS-D4=A` (chỉnh sửa làm `INVALIDATED` bản duyệt cũ), `SS-X1` (`StoryAiProposal` chỉ trả patch + diff, không tự apply), `CR-D6=A` (vùng "AI sắp nói" chỉ nhận `safeSummary` đã kiểm chứng + nhãn `Dự kiến · Chưa phát`), `CR-D7=A` (queue `Prioritize`/`Skip` chỉ tác động trước `COMMITTED`), `CR-D8=A` (`Active SKU` chỉ đổi sau `APPLIED`).

### 1.5. Bảy (07) mâu thuẫn & sai lệch hợp đồng đã kiểm chứng

| STT | Điểm sai lệch / Mâu thuẫn | Tài liệu / Mã nguồn đối chiếu | Hướng xử lý trong PoC P06 |
| :---: | :--- | :--- | :--- |
| 1 | **Version cross-ref drift:** Stage 03 nhắc `Risk Assessment v1.0` ở một đoạn trong khi repo dùng `v1.1`; `docs/README.md` §4 dẫn `Project Overview Proposal v1.0` nhưng tệp thiếu hoàn toàn trong Git history. | `experiments/README.md` §9, `docs/README.md` §4 | Tuân thủ `Baseline v1.2`, `Risk Assessment v1.1` và `PoC Plan v1.0`; không tạo link tới tệp thiếu. |
| 2 | **Baseline Appendix C.1 legacy Presenter glossary:** Bảng thuật ngữ C.1 định nghĩa *Presenter* là *"Người thật có footage/voice được cấp phép; không có mặt khi live"*, mâu thuẫn với `ACR-001`. | `Baseline v1.2` App. C.1 vs §8.1 (`ACR-001`) | Ưu tiên `ACR-001` (01 portrait + PhotoMaker + Wan2.2 Animate + MuseTalk 1.5); chỉ đọc C.1 như thuật ngữ lịch sử. |
| 3 | **`VerifiedSpeechCandidate` vs `SpeechTurn` (và đơn SKU vs `MULTI_SKU`):** Stage 03 §6.2 dùng `VerifiedSpeechCandidate.sku_refs: list[str]`; `P05 schemas.py` chỉ có `SpeechCandidate.sku_id: str` (chặn `CROSS_SKU_VIOLATION` nếu trộn SKU); `P08`/`m03.ts` quản lý `SpeechTurn`. | `PoC Plan v1.0` §6.2 vs `P05/schemas.py` vs `HOSTRA-API-001` & `m03.ts` | Tạo `guardrails/p05_gate_adapter.py` để giữ nguyên P05 đơn SKU và kiểm chứng tách từng SKU cho `COMPARE_PRODUCTS`/`MULTI_SKU` (`P06-OPEN-5` / `CF-P06-01`). |
| 4 | **`SessionCommand` set mismatch:** `HOSTRA-API-001` §7 (`PROPOSED`) có 8 lệnh gồm `START` và `REQUEST_LIVE_REVISION`; `apps/web/src/types/m03.ts` (`RuntimeCommandType`) thiếu `START`, `REQUEST_LIVE_REVISION` nhưng thêm `PRIORITIZE_COMMENT` (`CR-D7=A`); `Story Planner`/tài liệu cũ nhắc `FORCE_NEXT_TOPIC`. | `HOSTRA-API-001` §7 vs `m03.ts` (`RuntimeCommandType`) vs `DECISIONS.md` | Adapter P06 nhận `PAUSE_AI`, `RESUME_AI`, `SWITCH_SKU`, `SKIP_PENDING`, `REQUEST_LIVE_REVISION`; `PRIORITIZE_COMMENT` xử lý tại tầng queue trước `COMMITTED`. |
| 5 | **`SpeechTurn` vs `SpeechTurnPhase` enum drift:** `HOSTRA-DB-001` (`PROPOSED`) dùng 9 trạng thái (`PROPOSED..COMPLETED`, `CANCELLED`, `EXPIRED`) vs `m03.ts` (`SpeechTurnPhase`) dùng `PLANNING`, `VERIFYING`, `PREPARING_AUDIO`, `LIP_SYNC`, `READY`, `COMMITTED`, `PLAYING`, `PLAYBACK_COMPLETED`, `CANCELLED`. | `HOSTRA-DB-001` vs `m03.ts` (dòng 55–64) | P06 chỉ xuất `SpeechCandidate` trước `COMMITTED` và lắng nghe `PlaybackCompleted`; mọi chuyển đổi enum đặt trong `adapters/mocks/`. |
| 6 | **REST / WebSocket envelope drift:** `HOSTRA-API-001` §9 định nghĩa canonical event envelope (`event_id`, `event_type`, `schema_version`, `scope`, `aggregate`, `session_epoch`, `correlation_id`, `causation_id`, `occurred_at`, `payload`), còn Frontend mocks dùng flat snapshot/command DTO (`ControlRoomSnapshot`, `StartCommandResult` kèm `isMockRuntime: true`). | `HOSTRA-API-001` §9 vs `apps/web/src/types/m03.ts` & `m02.ts` | P06 định nghĩa schema nội bộ sạch theo Pydantic v2; không ép mock envelope Frontend làm chuẩn backend. |
| 7 | **Ghi chú lỗi thời về `KC-D1..D5`:** `Story Planner v0.2`, `Live Control Room v0.2` và `Viewer Live Room v0.2` còn ghi `KC-D1–KC-D5` là `OPEN`. | `docs/product/frontend/DECISIONS.md` (`CONF-03`, dòng 103 & 219) | Theo `Knowledge & Claims v0.2` & `DECISIONS.md`, `KC-D1–KC-D5 = A` đã `CLOSED/APPROVED`. |

### 1.6. Các quyết định đang mở (`P06-OPEN-1..6`)

Chi tiết đầy đủ nằm tại [`../research/decision_log.md`](../research/decision_log.md) Phần C:
- **`P06-OPEN-1`:** Lựa chọn LLM provider, model ID, độ ổn định structured output tiếng Việt, ngân sách latency (`~1.5–3s` trong budget `W1` P50 <= 7s / P95 <= 10s) và DPA/terms.
- **`P06-OPEN-2`:** Kích thước cửa sổ `played_history` (`5–N` chunks) và việc có cần bổ sung embedding similarity ngoài rule-based hay không.
- **`P06-OPEN-3`:** Chính sách *new viewer recap* (tần suất/độ dài) tránh gây lặp cho người xem cũ.
- **`P06-OPEN-4`:** Khóa bộ `human evaluation rubric` và ngưỡng chất lượng (`TO VALIDATE`) cùng Product Owner/Tech Lead.
- **`P06-OPEN-5`:** Thống nhất hợp đồng `SpeechCandidate` đa SKU (`CF-P06-01`) & báo cáo độ phủ một phần câu hỏi đa ý (`covered_intents` / `unanswered_intents`).
- **`P06-OPEN-6`:** Phân công Owner thực thi và Reviewer độc lập cho module P06.

---

## 2. Tóm tắt Kiến trúc P06 & Ranh giới Phụ thuộc

### 2.1. Lựa chọn phương pháp thực thi (`P06-ARCH`)

| Phương án | Phân loại | Lý do lựa chọn / đối chiếu / loại bỏ |
| :--- | :---: | :--- |
| **Phương án B — `Structured Story Planner + Dynamic Verified Generation` (`LangGraph`)** | `SELECTED FOR PoC` | Dùng `StateGraph` có kiểu rõ ràng, conditional edges, chu trình sửa có giới hạn (`bounded rewrite <= K`), trace từng node để audit và kiểm chứng qua P05 trước khi xuất candidate. |
| **Phương án A — `Script-first` (Tuyến tính cố định)** | **Baseline đối chiếu** | Ổn định, chi phí thấp nhưng rập khuôn trong phiên 1–2 giờ và khó ứng biến khi ngắt/trả lời lặp. Bắt buộc cài đặt trong `src/p06/baselines/` để đối chiếu công bằng. |
| **Phương án C — `Fully Agentic Multi-Agent`** | `DEFERRED` *(Loại khỏi MVP)* | Nhiều agent tự thương lượng làm tăng vọt độ trễ (`R03`), chi phí token và khó truy vết/kiểm soát phát ngôn an toàn (`R08`, `G4`). |

### 2.2. Ma trận Sở hữu Liên Module

| Module | Sở hữu chính thức | Giao tiếp với P06 |
| :--- | :--- | :--- |
| **`P05`** | `ProductFact`, `EvidenceChunk`, `ClaimRegistryEntry`, `PublicationGate` | P06 đọc `EvidenceBundle` đã duyệt và gửi `SpeechCandidate` qua adapter tới `PublicationGate.evaluate()` |
| **`P06`** | `StoryPlan` (`StoryArc`), `StoryChunk`, `PlayedHistoryTracker`, bounded rewrite, câu `bridge` | Xuất `SpeechCandidate` / `VerifiedSpeechCandidate` và `safeSummary` (`CR-D6=A`) |
| **`P07`** | Moderation (`4` lớp), Intent (`9` lớp), SKU (`7` chế độ), `ResponseGroupProposal` | P06 nhận `CommentTask` đã qua triage từ P07/P08, không tự phân loại raw chat |
| **`P08/P09`** | Single logical writer cho `LiveSession`, `Active SKU`, `SpeechTurn` FSM, `StoryCheckpoint`, OCOP eligibility | Cấp `active_sku_id`, `story_checkpoint`, `session_epoch`, lệnh `SessionCommand`; nhận candidate trước `COMMITTED` |
| **`P04`** | Single playout authority, LiveKit output, `PlaybackStarted` / `PlaybackCompleted` | P06 chỉ cập nhật `played_history` & `covered_topics` khi nhận `PlaybackCompleted` |
| **`P02`** | Voice TTS tiếng Việt | Chỉ nhận candidate đã qua P05 (`ALLOW`) |
| **`P10`** | UI `Story Planner`, `Live Control Room`, `Viewer Live Room` | Nhận `StoryAiProposal` diff (chờ Owner apply) & `safeSummary` (`Dự kiến · Chưa phát`) |
| **`P11`** | Rights Subject consent, `RightsStatus`, tenant isolation | Ràng buộc `tenant_id` và `rights_version` trong mọi truy vấn/candidate |

### 2.3. Ma trận Cô lập: Độc lập vs Mock vs Tích hợp thật

- **Độc lập trong P06 PoC:** `schemas/`, `planning/`, `agent/` (LangGraph), `memory/` (`PlayedHistoryTracker`), `guardrails/` (`prohibited_echo_guard`, `fallback`), `baselines/` (`script_first`), `evaluation/`.
- **Dùng adapter đọc-chỉ-đọc tới code P05 local:** `guardrails/p05_gate_adapter.py` gọi trực tiếp `PublicationGate` & `VersionedKnowledgeStore` từ `../knowledge-verification/` (không sửa hoặc fork code P05).
- **Mock bắt buộc trong `src/p06/adapters/mocks/`:** `MockLLMProvider` (mặc định cho unit/CI), `MockCommentTaskFeed` (chuẩn P07 `4/9/7`), `MockSessionOrchestrator` (chuẩn P08), `MockPlaybackAckBus` (phát `PlaybackCompleted` theo seed).
- **Tích hợp thật (`M4 -> Stage 06`):** `GeminiProvider` (hoặc LLM provider được duyệt `P06-OPEN-1`), P05 PostgreSQL/pgvector, P07 -> P08 outbox/stream, P04 GStreamer/LiveKit playout clock, P02 TTS trong budget `W1`.

---

## 3. Hiện vật Khởi tạo Khung & Tài liệu Agent (Deliverables)

### 3.1. Cây thư mục đã khởi tạo và các điều chỉnh có chủ đích

```text
autonomous-storytelling/
├── .env.example
├── .gitignore
├── .gitkeep
├── AGENTS.md
├── pyproject.toml
├── README.md
├── docs/                          # (Mới ở đợt hoàn thiện tài liệu) Báo cáo & Onboarding
│   ├── README.md
│   ├── 00-context-and-scaffolding-report.md
│   └── 01-p06-structure-and-mission-guide.md
├── research/
│   ├── context_and_dependencies.md
│   ├── decision_log.md
│   ├── literature_review.md
│   ├── methodology.md
│   ├── problem_definition.md
│   └── research_questions.md
├── configs/
│   ├── default.yaml
│   ├── experiments/{.gitkeep, p06_e01.yaml}
│   └── models/.gitkeep
├── data/{README.md, annotations/.gitkeep, comments/.gitkeep, merchant_goals/.gitkeep, products/.gitkeep, scenarios/.gitkeep, story_plans/.gitkeep}
├── prompts/README.md
├── notebooks/README.md
├── src/p06/
│   ├── __init__.py
│   ├── adapters/mocks/.gitkeep
│   ├── agent/nodes/.gitkeep
│   ├── baselines/.gitkeep
│   ├── guardrails/.gitkeep
│   ├── memory/.gitkeep
│   ├── planning/.gitkeep
│   ├── providers/.gitkeep
│   ├── schemas/.gitkeep
│   └── simulation/.gitkeep
├── experiments/
│   ├── p06_e01_no_comments/README.md
│   ├── p06_e02_repeated_questions/.gitkeep
│   ├── p06_e03_interrupt_resume/.gitkeep
│   └── p06_e04_bounded_rewrite/.gitkeep
├── evaluation/{README.md, metrics/.gitkeep, rubrics/.gitkeep}
├── tests/{unit/.gitkeep, contract/.gitkeep, integration/.gitkeep}
├── runs/README.md
└── reports/{README.md, figures/.gitkeep, tables/.gitkeep}
```

**Các điều chỉnh có chủ đích so với cấu trúc lý thuyết ban đầu:**
1. **`pyproject.toml` đặt cục bộ trong `autonomous-storytelling/`:** Tuân thủ `ENVIRONMENT_SETUP_AUDIT.md` §2.2 (root `pyproject.toml` chỉ cấu hình search-path Pyrefly/Pyright, không gộp dependencies giữa CPU PoC và GPU workers).
2. **Dùng `.gitkeep` thay cho `.py`/`.ipynb` rỗng:** Theo `DR-P06-005` và quy tắc trong `AGENTS.md` §13 mục 9, tránh sinh mã giả rỗng khi chưa bắt đầu Phase 3; chỉ tạo `src/p06/__init__.py` tối giản để đánh dấu package.
3. **Loại trừ `runs/*/*` trong `.gitignore`:** Tránh đẩy log chạy thô và artifacts lớn lên Git trong khi vẫn giữ `runs/README.md` và cấu trúc thư mục.
4. **Bảo toàn nguyên trạng phần đầu `README.md` (dòng 1–115) và `.gitkeep` ở root:** Chỉ mở rộng Section 12 điều hướng của `README.md` mà không sửa giả thuyết/checklist gốc đã kiểm kê.

### 3.2. Tóm tắt bộ tài liệu Agent & Nghiên cứu

- **`AGENTS.md`:** Bản hướng dẫn tác nghiệp thuần Markdown (không YAML frontmatter, `< 24,000` bytes), khóa 12 quy tắc bắt buộc, ranh giới `I-01`–`I-09`, thứ tự đọc và Definition of Done.
- **Lưu ý cơ chế quét Antigravity (`agy-customizations`):** Antigravity chỉ quét ngược từ `CWD` lên `.git` root để tự nạp `AGENTS.md`. Khi mở IDE tại repo root `hostra-ai/`, `autonomous-storytelling/AGENTS.md` không tự nạp nên agent làm việc ở P06 bắt buộc đọc thủ công. Để hỗ trợ kích hoạt tự động từ root trong một nhiệm vụ được duyệt riêng sau này, có thể cân nhắc bổ sung pointer rule ở `.agents/rules/p06-autonomous-storytelling.md` *(đề xuất tham khảo, chưa áp dụng ra ngoài `P06_ROOT`)*:
  ```markdown
  ---
  trigger: model_decision
  description: Load when working on HOSTRA AI Module P06 (experiments/sales-intelligence/autonomous-storytelling/)
  ---
  Read `experiments/sales-intelligence/autonomous-storytelling/AGENTS.md` and `docs/01-p06-structure-and-mission-guide.md` before modifying any P06 files.
  ```
- **`research/*.md`:** Đã hoàn thiện 6 tài liệu chuẩn hóa (`problem_definition.md`, `research_questions.md`, `methodology.md`, `literature_review.md`, `context_and_dependencies.md`, `decision_log.md`).
- **`configs/*` & Operational `README.md`s:** Khóa các cờ an toàn trong `configs/default.yaml` (`advance_only_on_playback_completed: true`, `fail_closed_on_unverified_claim: true`, `allow_active_sku_mutation: false`), kịch bản `configs/experiments/p06_e01.yaml`, cùng hướng dẫn vận hành tại `data/`, `prompts/`, `notebooks/`, `evaluation/`, `runs/`, `reports/` và `experiments/p06_e01_no_comments/`.

---

## 4. Kế hoạch Triển khai Tiếp theo (`P06-E01` Tasks `E01-T01..T08`)

Để triển khai và chạy tái lập thí nghiệm đầu tiên `P06-E01` (theo chuỗi `Phase 1–4`), lộ trình công việc kế tiếp được chia thành 8 tác vụ:

| Mã Task | Tên đầu việc | Phạm vi tệp dự kiến | Kết quả đầu ra (Verification) |
| :---: | :--- | :--- | :--- |
| **`E01-T01`** | Khóa Pydantic v2 Domain & Boundary Schemas | `src/p06/schemas/` | `StoryPlan`, `StoryArc`, `StoryChunk`, `SpeechCandidate`, `VerifiedSpeechCandidate`, `StoryCheckpoint`, `PlaybackCompletedEvent` đạt unit tests. |
| **`E01-T02`** | Cài đặt `LLMProvider` & `MockLLMProvider` | `src/p06/providers/` | Interface trừu tượng + mock provider tất định theo seed, ghi `token_usage` & `latency_ms`. |
| **`E01-T03`** | Cài đặt P05 Gate Adapter & `prohibited_echo_guard` | `src/p06/guardrails/` | Bọc `PublicationGate` đọc-chỉ-đọc từ `../knowledge-verification/`, xử lý bẫy substring & single-SKU (`contract` tests với P05). |
| **`E01-T04`** | Xây dựng `StoryPlanner` & `PlayedHistoryTracker` | `src/p06/planning/`, `src/p06/memory/` | Theo dõi `mandatory_topics` & cửa sổ `5–N` chỉ tiến khi nhận `PlaybackCompleted` ACK (`I-06`). |
| **`E01-T05`** | Xây dựng LangGraph `StateGraph` & `Script-first` Baseline | `src/p06/agent/`, `src/p06/baselines/` | Graph `load_context -> plan_chunk -> draft -> verify_p05 -> bounded_rewrite` + baseline tuyến tính đối chiếu công bằng. |
| **`E01-T06`** | Chuẩn bị Dataset 3-SKU Positive & Playback Simulator | `data/`, `prompts/`, `src/p06/simulation/`, `src/p06/adapters/mocks/` | Bộ 3 SKU thực phẩm đóng gói đều `OCOP: VERIFIED` (`is_synthetic: true`), prompt hashable và fake clock ACK `10` & `30` phút. |
| **`E01-T07`** | Cài đặt Metrics & Runner `P06-E01` | `evaluation/metrics/`, `experiments/p06_e01_no_comments/run.py` | Tính `topic_coverage`, `semantic_repetition`, `completed_chunk_replay_count`, `rewrite_rate`, `latency`, `token_cost`; xuất đủ 9 file vào `runs/P06-E01/<run_id>/`. |
| **`E01-T08`** | Kiểm thử End-to-End & Chạy thực nghiệm `P06-E01` | `tests/`, `runs/P06-E01/`, `reports/` | 100% `unit` + `contract` + `integration` tests với `MockLLMProvider` PASS trước khi benchmark LLM thật (`P06-OPEN-1`). |

---

## 5. Tóm tắt Xác minh Git (Git Verification Summary)

- **Nhánh làm việc:** `research/p06-autonomous-storytelling` (nền commit `030682c`).
- **Kiểm tra phạm vi:** Toàn bộ tệp tạo mới và chỉnh sửa đều nằm gọn trong `experiments/sales-intelligence/autonomous-storytelling/`. Không có tệp nào ngoài `P06_ROOT` (như `apps/api/`, `apps/web/`, `knowledge-verification/`, `docs/` cấp repo) bị chỉnh sửa.
- **An toàn nhánh:** Việc đọc đối chiếu tài liệu Stage 04 và `p07-contract-v0.1.md` từ `research/p07-comment-understanding` được thực hiện hoàn toàn ở chế độ chỉ-đọc (`git ls-tree` / `git show`), không thực hiện `checkout`, `merge`, `commit` hay `push`.
