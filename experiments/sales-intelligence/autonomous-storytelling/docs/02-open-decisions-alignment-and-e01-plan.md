# Báo cáo Session 02 — Đồng bộ Định hướng `P06-OPEN-1..6`, Kiến trúc 3 Tầng LLM & Kế hoạch Triển khai `P06-E01`

| Thuộc tính | Giá trị |
| :--- | :--- |
| **Ngày lập báo cáo** | `2026-11-26` |
| **Nhánh Git** | `research/p06-autonomous-storytelling` |
| **Phạm vi** | `Cập nhật định hướng P06-OPEN-1..6, Kiến trúc 3 tầng LLM Provider, Antigravity Scoped Rule & Kế hoạch triển khai chi tiết P06-E01` |
| **Module mục tiêu** | `P06 — Sales Intelligence & Autonomous Storytelling` (`experiments/sales-intelligence/autonomous-storytelling/`) |
| **Trạng thái hiện tại** | `DOCUMENTATION & PLAN UPDATED \| IMPLEMENTATION & BENCHMARKS: NOT STARTED` |

---

## Phần 1 — Tổng hợp Định hướng `P06-OPEN-1..6`

Để tránh đánh đồng giữa ràng buộc kiến trúc, giả thuyết PoC và tham số còn chờ dữ liệu thực nghiệm, toàn bộ 6 điểm mở `P06-OPEN-1..6` được phân tách rạch ròi theo 3 mức trạng thái:

| Mã | Chủ đề | `SELECTED FOR PoC` (Chốt hướng triển khai PoC) | `RESEARCH VARIABLE` (Biến số khảo sát trong thí nghiệm) | `TO VALIDATE / PENDING SIGN-OFF` (Chờ bằng chứng & phê duyệt) |
| :--- | :--- | :--- | :--- | :--- |
| **`P06-OPEN-1`** | **LLM Provider & Latency Budget** | Kiến trúc trừu tượng `LLMProvider` + `ProviderFactory` hỗ trợ 3 tầng tách biệt (`Mock` -> `Ollama CPU Qwen3` -> `Gemini Flash/Flash-Lite`), cấu hình qua `configs/models/*.yaml`. | So sánh cặp model cục bộ (`Qwen3 1.7B` vs `4B`) ở mức smoke test và ứng viên `Gemini Flash` vs `Flash-Lite` ở formal benchmark. | Xác minh model ID chính xác, quota, đơn giá, DPA/terms trước khi dùng dữ liệu thật; chứng minh latency P06 nằm trong budget `W1` (`P50 <= 7s`, `P95 <= 10s` toàn tuyến). |
| **`P06-OPEN-2`** | **Memory 4 phần & Chống lặp** | Tách 4 thành phần: (1) `Short-term Played History`, (2) `Global Topic Coverage`, (3) `Session-scoped Viewer Context` (`D11/D23`), (4) interface `Optional Semantic Memory`. Áp dụng **rule-based first** (không dùng `pgvector` trong PoC standalone). | Sweep kích thước cửa sổ **`W ∈ {5, 10, 20}`** (cấu hình qua YAML, không hard-code); đối chiếu rule-based vs embedding comparator nếu rule-based thiếu nhạy. | Chốt giá trị `W` tối ưu và ngưỡng trùng lặp ngữ nghĩa sau khi có số liệu từ `P06-E01` & `P06-E02`. |
| **`P06-OPEN-3`** | **Chính sách New Viewer Recap** | Chính sách **periodic + context-aware Q&A**; **cấm** recap theo từng sự kiện viewer join phòng; chèn recap phải bám `semantic_breakpoint`. | Chu kỳ phút/số chunk giữa các lần recap và độ dài tóm tắt khi thử nghiệm ở `P06-E03` / `P06-E02`. | **Trì hoãn (`DEFERRED`) qua khỏi `P06-E01`** (Recap = OFF trong `E01`); đánh giá lại trải nghiệm cùng Product Owner (`G2/G6`). |
| **`P06-OPEN-4`** | **Human Evaluation Rubric** | Áp dụng rubric 6 tiêu chí thang **1–5** tại `evaluation/rubrics/human_eval_rubric_v0.1.md`, tách riêng hard constraints khỏi soft quality scores. | Phương pháp chấm mù so sánh `script_first` vs `langgraph_structured_story` trên mẫu transcript. | Thực hiện **pilot calibration** giữa người chấm trước khi khóa ngưỡng chấp nhận; **hard constraints không bao giờ được bù bằng điểm mềm**. |
| **`P06-OPEN-5`** | **Hợp đồng liên module (`CF-P06-01`)** | Dùng hợp đồng mock có phiên bản **`p06-mock-v0.1`** với 4 `TargetScopeMode` (`SINGLE_SKU`, `MULTI_SKU_COMPARE`, `SHOP_WIDE_POLICY`, `UNRESOLVED_SKU`) và `ProposedResponseCoverage`. | Cơ chế kiểm tra `P05` đơn-SKU cho trường hợp `MULTI_SKU_COMPARE` thông qua adapter đọc-chỉ-đọc. | Đồng bộ schema chính thức vào `packages/contracts/` giữa owner `P05`, `P06`, `P07`, `P08` trước Stage 06; xác nhận phạm vi `ProposedResponseCoverage` vs `PlaybackCompleted`. |
| **`P06-OPEN-6`** | **Phân công Owner & Reviewer** | Duy trì tách vai trò giữa người triển khai PoC và người nghiệm thu độc lập hard gates `G2/G4/G6`. | — | **`PENDING ASSIGNMENT`** — Chưa có tên Owner & Reviewer chính thức được gán; chưa thể đóng dấu `VALIDATED`. |

---

## Phần 2 — Xác minh Cơ chế Antigravity Rule Discovery & Scoped Rule

Qua kiểm tra tài liệu hệ thống `agy-customizations` (`SKILL.md` và `docs/rules.md`), cơ chế nạp rule của Antigravity hoạt động như sau:

1. **Quét phân cấp theo CWD:** Agent đi ngược từ `CWD` lên tới `.git` root để nạp `AGENTS.md` / `GEMINI.md` và `.agents/rules/*.md`. Do đó, khi mở workspace tại repo root `hostra-ai/`, tệp `experiments/sales-intelligence/autonomous-storytelling/AGENTS.md` không nằm trên đường đi từ `CWD` lên `.git` root nên không tự động nạp nếu không có rule trỏ tới từ root.
2. **Phân biệt 3 chế độ trigger của `.agents/rules/*.md`:**
   - `always_on`: Luôn nạp nguyên văn vào mọi phiên làm việc trong repo, tiêu tốn chung hạn mức `20,000` tokens (`defaultRulesBudget`) — **không phù hợp** cho quy tắc riêng của một module PoC vì làm phình ngữ cảnh của `P05`, `P07`, `apps/web/`, `apps/api/`.
   - `glob`: Kích hoạt theo mẫu đường dẫn tệp đang mở/tác động, phù hợp khi chỉ bám file path cố định nhưng kém linh hoạt khi tác vụ mới ở dạng trao đổi ngữ cảnh P06 từ root.
   - `trigger: model_decision` (**được chọn**): Chỉ đưa tên và mô tả ngắn vào danh sách nhận diện (progressive disclosure); nội dung đầy đủ chỉ nạp khi tác vụ liên quan tới `P06` (`experiments/sales-intelligence/autonomous-storytelling/`).
3. **Cô lập phạm vi & giới hạn `AGENTS.md`:**
   - Scoped rule `.agents/rules/p06-autonomous-storytelling.md` (`trigger: model_decision`) tại repo root chỉ đóng vai trò pointer dẫn về `P06/AGENTS.md` và hướng dẫn P06; **không sửa global rules (`~/.gemini/config/`)** và **không ảnh hưởng** đến quy tắc của `P05`, `P07` hay các module khác.
   - Bản thân `P06/AGENTS.md` phải duy trì thuần Markdown (**không** dùng YAML frontmatter) và giữ kích thước **nghiêm ngặt `< 24,000` bytes** để tuân thủ ngưỡng tối đa mỗi tệp rule của Antigravity.

---

## Phần 3 — Kiến trúc 3 Tầng `LLMProvider` + `ProviderFactory`

Do môi trường phát triển cục bộ hiện là **CPU-only (không có dGPU)**, P06 thiết kế giao diện trừu tượng `LLMProvider` (`src/p06/providers/base.py`) kết hợp `ProviderFactory` (`src/p06/providers/factory.py`) để hoán đổi mô hình thuần bằng YAML trong `configs/models/` mà **không sửa bất kỳ node nào trong LangGraph `StateGraph`**:

| Tầng | Provider Class | Config File | Mục đích sử dụng | Ràng buộc bắt buộc |
| :---: | :--- | :--- | :--- | :--- |
| **Tier 1** | `MockLLMProvider` (`mock_provider.py`) | `configs/models/mock.yaml` | `unit_test`, `contract_test`, `integration_test` tất định, CI offline | **Chỉ dùng cho kiểm thử tự động (`unit_test` / `integration_test`).** Cấm lấy kết quả Mock làm bằng chứng chất lượng tiếng Việt hay năng lực LLM. |
| **Tier 2** | `OllamaLocalProvider` (`ollama_provider.py`) | `configs/models/ollama_qwen3_1.7b.yaml`, `configs/models/ollama_qwen3_4b.yaml` | `local_smoke_test` trên CPU cục bộ (`Qwen3 1.7B` / `4B`) | Chỉ dùng kiểm tra tính thông suốt prompt, JSON parsing và luồng graph cục bộ trên CPU; tốc độ CPU không đại diện cho SLA production. |
| **Tier 3** | `GeminiAPIProvider` (`gemini_provider.py`) | `configs/models/gemini_flash.yaml` | `formal_experiment` (`Gemini Flash` / `Flash-Lite`) cho `P06-E01..E04` | Phải xác minh model ID, quota, pricing & DPA/terms trước khi chạy; chỉ dùng dữ liệu synthetic/được duyệt; không fallback im lặng về Mock khi gọi API thật. |

**Quy tắc Telemetry & Tính toàn vẹn Benchmark:**
- Mọi lượt gọi qua `LLMProvider` bắt buộc trả về chuẩn telemetry thống nhất: `provider_name`, `model_id`, `tier`, `latency_ms`, `input_tokens`, `output_tokens`, `finish_reason`, `raw_response_valid`.
- Tuyệt đối **không gộp** kết quả chạy từ Tier 2 (`OllamaLocalProvider`) và Tier 3 (`GeminiAPIProvider`) vào chung một bảng so sánh định lượng hoặc chỉ số trung bình.

---

## Phần 4 — Tóm tắt Contract `p06-mock-v0.1`

Trong khi `packages/contracts/` và tài liệu Stage 04 trên nhánh chính chưa đóng băng, P06 khóa bộ schema mock nội bộ có phiên bản **`p06-mock-v0.1`** (`src/p06/schemas/`) để cô lập sai lệch hợp đồng (`CF-P06-01`):

1. **Bốn chế độ phạm vi trả lời (`TargetScopeMode`):**
   - `SINGLE_SKU`: Câu chuyện hoặc câu trả lời nhắm vào đúng 01 SKU (`active_sku_id` hoặc `referenced_sku_id` đã phân giải).
   - `MULTI_SKU_COMPARE`: So sánh từ 2 SKU trở lên trong cùng phiên (`sku_refs: list[str]`); adapter `p05_gate_adapter.py` phải kiểm chứng từng SKU qua cổng `P05` đơn-SKU trước khi gộp hợp lệ.
   - `SHOP_WIDE_POLICY`: Câu hỏi chính sách chung của gian hàng (phí vận chuyển, đổi trả, đóng gói, nguồn gốc chung) — hợp lệ khi không gắn SKU cụ thể.
   - `UNRESOLVED_SKU`: Bình luận nhắc sản phẩm mơ hồ hoặc ngoài danh mục (`UNCLEAR` / `OUT_OF_CATALOG` từ `P07`) — **phải tách biệt nghiêm ngặt khỏi `SHOP_WIDE_POLICY`** để P06 trả lời làm rõ/hỏi lại an toàn thay vì bịa chính sách hoặc gắn nhầm sang `Active SKU`.
2. **Độ phủ đề xuất vs Xác nhận phát sóng:**
   - P06 chỉ xuất **`ProposedResponseCoverage`** (danh sách `topic_ids` / `intent_ids` / `claim_ids` dự kiến được đề cập trong `SpeechCandidate`).
   - Toàn bộ trạng thái chính thức (`PlayedHistoryTracker`, `covered_topics`, `StoryCheckpoint`) **chỉ được phép cập nhật** khi nhận sự kiện **`PlaybackCompleted`** từ `P04` (hoặc `MockPlaybackAckBus` trong môi trường mô phỏng PoC).

---

## Phần 5 — Kế hoạch Triển khai Chi tiết `P06-E01` (`E01-T01` → `E01-T09`)

Chuỗi công việc triển khai thí nghiệm đầu tiên `P06-E01` (kể chuyện 3 SKU không bình luận, sweep cửa sổ `W ∈ {5, 10, 20}`, Recap = OFF) được phân rã thành **9 task tuần tự có kiểm soát (`E01-T01..T09`)**:

### `E01-T01` — Xác minh `.venv` & Cài đặt Dependencies Tối thiểu cho CPU
- **Dependencies:** Không (Task khởi đầu sau khi Tech Lead duyệt chuyển sang Phase 1/3).
- **Inputs:** `pyproject.toml`, `docs/05-implementation/development-guides/ENVIRONMENT_SETUP_AUDIT.md`.
- **Target Files:** Môi trường ảo `.venv` cục bộ tại `autonomous-storytelling/.venv/` (không chỉnh sửa repo ngoài trừ khi cần khóa version `pyproject.toml`).
- **Deliverables:** Môi trường Python `3.11–3.13` chạy độc lập với các gói lõi cho CPU (`langgraph`, `pydantic`, `pyyaml`, `pytest`, và `httpx` phục vụ giao tiếp Ollama cục bộ; chỉ thực hiện cài đặt khi được Tech Lead phê duyệt chạy Phase 1/3).
- **Definition of Done:** `python -c "import langgraph, pydantic, yaml, httpx"` và `pytest --version` chạy thành công trong `.venv` mà không đụng chạm môi trường GPU/API khác.

### `E01-T02` — Khóa Versioned Mock Cross-Module & Core P06 Schemas (`p06-mock-v0.1`)
- **Dependencies:** `E01-T01`.
- **Inputs:** `research/context_and_dependencies.md`, `../knowledge-verification/schemas.py`, `P06-OPEN-5`.
- **Target Files:** `src/p06/schemas/__init__.py`, `src/p06/schemas/story.py`, `src/p06/schemas/candidate.py`, `src/p06/schemas/events.py`, `src/p06/schemas/state.py`.
- **Deliverables:** Các model Pydantic v2 gắn `contract_version: Literal["p06-mock-v0.1"]`: `StoryPlan`, `StoryArc`, `StoryChunk`, `SpeechCandidate` (gắn `TargetScopeMode`: `SINGLE_SKU | MULTI_SKU_COMPARE | SHOP_WIDE_POLICY | UNRESOLVED_SKU`), `ProposedResponseCoverage`, `PlaybackCompleted`, và `AgentState`.
- **Definition of Done:** Toàn bộ schema serialize/deserialize JSON sạch, có `from __future__ import annotations`, từ chối nhầm lẫn `UNRESOLVED_SKU` thành `SHOP_WIDE_POLICY` ở tầng validation.

### `E01-T03` — Cài đặt `LLMProvider`, `ProviderFactory` & Cấu hình 3 Tầng
- **Dependencies:** `E01-T02`.
- **Inputs:** `configs/models/{mock,ollama_qwen3_1.7b,ollama_qwen3_4b,gemini_flash}.yaml`, thiết kế 3 tầng tại Phần 3.
- **Target Files:** `src/p06/providers/{__init__.py, base.py, mock_provider.py, ollama_provider.py, gemini_provider.py, factory.py}`, `configs/models/*.yaml`.
- **Deliverables:** Interface `LLMProvider` chuẩn hóa telemetry; `MockLLMProvider` tất định theo seed; skeleton hoàn chỉnh đọc YAML cho `OllamaLocalProvider` (HTTP/httpx tới Ollama local) và `GeminiAPIProvider` (kèm guard kiểm tra API key/model ID); `ProviderFactory.from_config(...)`.
- **Definition of Done:** `ProviderFactory` khởi tạo đúng cả 3 tầng từ YAML; `MockLLMProvider` chạy offline 100% không cần mạng/API key; kiểm tra lỗi rõ ràng khi thiếu key hoặc Ollama chưa chạy (không silent fallback).

### `E01-T04` — Chuẩn bị Bộ Dữ liệu Tổng hợp 3 SKU `OCOP: VERIFIED`
- **Dependencies:** `E01-T02`, `../knowledge-verification/data/catalog_seed.json`.
- **Inputs:** `ACR-002`, `data/README.md`, bẫy `SKU-CASHEW-03` (`PENDING`) từ `context_and_dependencies.md`.
- **Target Files:** `data/products/e01_verified_skus.json`, `data/merchant_goals/e01_goals.json`, `data/story_plans/e01_story_plans.json`, `data/README.md` (cập nhật manifest provenance nếu cần).
- **Deliverables:** Bộ dữ liệu 3 SKU thực phẩm đóng gói đều đạt `OCOP: VERIFIED` (tách biệt hoàn toàn khỏi `SKU-CASHEW-03` `PENDING` của P05), kèm `EvidenceChunk`, `ProductFact`, `MerchantGoal`, và `mandatory_topics` gắn nhãn `is_synthetic: true` và nguồn provenance rõ ràng.
- **Definition of Done:** Kiểm tra tự động xác nhận cả 3 SKU đều qua được eligibility check của P05, không chứa PII/dữ liệu thật chưa cấp quyền, không chứa claim y tế/công dụng thuốc.

### `E01-T05` — `P05KnowledgeAdapter` & `SimulatedPlaybackHarness`
- **Dependencies:** `E01-T02`, `E01-T04`.
- **Inputs:** `../knowledge-verification/publication_gate.py`, `../knowledge-verification/schemas.py`, Invariant `I-02` & `I-06`.
- **Target Files:** `src/p06/guardrails/{__init__.py, p05_gate_adapter.py, prohibited_echo_guard.py, fallback_selector.py}`, `src/p06/adapters/mocks/{__init__.py, playback_bus.py, knowledge_store.py}`, `src/p06/simulation/{__init__.py, session_simulator.py}`.
- **Deliverables:** Adapter đọc-chỉ-đọc nối thẳng `PublicationGate.evaluate()` (không copy/fork logic P05), guard chống lặp chuỗi con từ cấm (`prohibited_echo_guard`), `fallback_selector` fail-closed, và `SimulatedPlaybackHarness` dùng fake clock phát sự kiện `PlaybackCompleted`.
- **Definition of Done:** Có unit/contract test chứng minh nếu không phát `PlaybackCompleted` (hoặc ACK thất bại/UNKNOWN) thì `PlayedHistory` và `StoryCheckpoint` tuyệt đối không tiến.

### `E01-T06` — Hệ thống Memory 4 Thành phần, `RepetitionDetector` & `ScriptFirstBaseline`
- **Dependencies:** `E01-T02`, `E01-T05`.
- **Inputs:** `P06-OPEN-2`, `configs/default.yaml`, `research/methodology.md`.
- **Target Files:** `src/p06/memory/{__init__.py, played_history.py, topic_coverage.py, viewer_context.py, semantic_memory.py, repetition_detector.py}`, `src/p06/baselines/{__init__.py, script_first.py}`.
- **Deliverables:**
  - 4 lớp bộ nhớ: `ShortTermPlayedHistory` (nhận tham số `window_size ∈ {5, 10, 20}` từ config), `GlobalTopicCoverage`, `SessionViewerContext`, và interface `OptionalSemanticMemory` (tắt hoặc no-op theo mặc định ở E01).
  - Rule-based `RepetitionDetector` (trùng `intent`, `sku_id`, `covered_claim_ids`, lexical/n-gram overlap).
  - `ScriptFirstBaseline` đi qua cùng `EvidenceBundle` và `P05KnowledgeAdapter` để so sánh công bằng với LangGraph.
- **Definition of Done:** Đổi `window_size` giữa `5`, `10`, `20` làm thay đổi hành vi phát hiện lặp đúng như kỳ vọng trong unit test mà không cần sửa code Python.

### `E01-T07` — `StoryPlanner`, Versioned Prompts & LangGraph Workflow
- **Dependencies:** `E01-T03`, `E01-T05`, `E01-T06`.
- **Inputs:** `prompts/README.md`, `configs/experiments/p06_e01.yaml`.
- **Target Files:** `prompts/story_planner.txt`, `prompts/story_generation.txt`, `src/p06/planning/{__init__.py, story_planner.py, arc_sequencer.py}`, `src/p06/agent/{__init__.py, graph.py, nodes/load_context.py, nodes/plan_chunk.py, nodes/draft_chunk.py, nodes/verify_p05.py, nodes/bounded_rewrite.py, nodes/finalize_candidate.py}`.
- **Deliverables:** Prompt templates tách riêng file text (tính SHA-256 hash vào manifest), `StoryPlanner`, và đồ thị LangGraph `load -> plan -> draft -> verify_p05 -> bounded_rewrite -> finalize` tôn trọng `max_rewrite_retries` (`<= K`) và phát hành `ProposedResponseCoverage`.
- **Definition of Done:** Graph chạy end-to-end với `MockLLMProvider`, ép kịch bản P05 từ chối dừng đúng số lần `K` rồi fallback an toàn; trace từng node được ghi đầy đủ.

### `E01-T08` — Tier 1 Deterministic Tests, Metrics & Reproducible Runner `P06-E01`
- **Dependencies:** `E01-T07`.
- **Inputs:** `configs/experiments/p06_e01.yaml`, `evaluation/README.md`, `runs/README.md`, `experiments/p06_e01_no_comments/README.md`.
- **Target Files:** `evaluation/metrics/{__init__.py, story_metrics.py}`, `experiments/p06_e01_no_comments/run.py`, `tests/unit/*.py`, `tests/contract/*.py`, `tests/integration/test_e01_graph.py`.
- **Deliverables:** Bộ test Tier 1 (`unit` + `contract` + `integration` dùng `MockLLMProvider`), module tính metrics (`topic_coverage`, `semantic_repetition`, `completed_chunk_replay_count`, `rewrite_rate`, `latency`, `token_cost`), và runner `run.py` hỗ trợ sweep `W ∈ {5, 10, 20}` (với `Recap = OFF`) xuất đủ 9 tệp chuẩn vào `runs/P06-E01/<run_id>/` kèm `failures/`.
- **Definition of Done:** `pytest` đạt **100% pass** hoàn toàn offline; chạy thử `run.py` với `mock.yaml` qua 3 giá trị `W ∈ {5, 10, 20}` cho 10 và 30 phút tái lập cùng kết quả theo seed và sinh đầy đủ `manifest.json` (có commit hash, prompt hashes, `is_synthetic: true`).

### `E01-T09` — Tier 2 CPU Smoke Test, Pilot Rubric Calibration & Tier 3 Formal Experiment
- **Dependencies:** `E01-T08` đạt 100% pass; phê duyệt của Tech Lead cho quota/DPA và pilot calibration.
- **Inputs:** `configs/models/ollama_qwen3_1.7b.yaml`, `configs/models/ollama_qwen3_4b.yaml`, `configs/models/gemini_flash.yaml`, `evaluation/rubrics/human_eval_rubric_v0.1.md`.
- **Target Files:** `runs/P06-E01/<run_id>/` (lưu local theo `.gitignore`), `reports/tables/`, `reports/e01_summary.md` *(khi có kết quả thật)*.
- **Deliverables:**
  1. **Tier 2 CPU Smoke Test:** Chạy ngắn trên `Ollama Qwen3 1.7B/4B` (nếu RAM máy cho phép) để kiểm tra khả năng sinh JSON/tiếng Việt thực tế; ghi nhận riêng biệt.
  2. **Pilot Calibration (`human_eval_rubric_v0.1.md`):** Chấm thử một lô mẫu nhỏ để hiệu chỉnh mức đồng thuận giữa người chấm trước khi khóa ngưỡng chất lượng.
  3. **Tier 3 Formal Experiment:** Sau khi xác minh model ID, quota, pricing và DPA/terms, chạy `P06-E01` bằng `Gemini Flash/Flash-Lite` đối chiếu `ScriptFirstBaseline` trên `W ∈ {5, 10, 20}`, lưu đủ transcript, failure cases và bảng so sánh tách biệt khỏi Tier 2.
- **Definition of Done:** Hoàn tất các lượt chạy tái lập, không trộn kết quả Tier 2 và Tier 3, có phiếu chấm pilot calibration và bảng phân tích theo từng cấu hình `W`, sẵn sàng đưa Reviewer (`PENDING ASSIGNMENT`) kiểm tra cho `G2/G6` trước khi chuyển sang `P06-E04`.
