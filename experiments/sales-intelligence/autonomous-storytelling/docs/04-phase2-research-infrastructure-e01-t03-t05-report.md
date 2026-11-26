# Báo cáo Kiểm toán Phase 1 & Triển khai Hạ tầng Nghiên cứu Phase 2 (`E01-T03..E01-T05`)

| Thuộc tính | Giá trị |
| :--- | :--- |
| **Ngày lập báo cáo** | `2026-11-26` |
| **Nhánh Git** | `research/p06-autonomous-storytelling` |
| **Base Checkpoint** | `p06-checkpoint-02-foundation` (`da385bd`) |
| **Phạm vi thực hiện** | `Phase 1 Audit Remediation + Phase 2 (E01-T03, E01-T04, E01-T05) + Wave D Independent Review` |
| **Module mục tiêu** | `P06 — Sales Intelligence & Autonomous Storytelling` (`experiments/sales-intelligence/autonomous-storytelling/`) |
| **Trạng thái hiện tại** | `E01-T01..T05 COMPLETED \| E01-T06..E01-T09 & P06-E01..E04: NOT STARTED` |

---

## 1. Executive Summary (Tóm tắt Điều hành)

Đợt làm việc này tiếp nối từ điểm mốc `p06-checkpoint-02-foundation` (`da385bd`) nhằm kiểm toán toàn diện các hợp đồng dữ liệu Phase 1 trước khi xây dựng hạ tầng nghiên cứu Phase 2 (`E01-T03..E01-T05`), sau đó kiểm định chéo độc lập trước khi chuyển sang tầng trí nhớ và đồ thị LangGraph (`E01-T06..E01-T09`):

1. **Kiểm toán & khắc phục Phase 1 (`E01-T02` Hardening):** Phát hiện và xử lý triệt để **`2 BLOCKER`**, **`3 MAJOR`**, và **`3 MINOR`** trong `src/p06/schemas/` (`A-BLK-01`, `A-BLK-02`, `A-MAJ-01..03`, `A-MIN-01..03`). Bộ test nền tăng từ `28` lên **`33` test cases pass**.
2. **Hoàn tất Phase 2 (`E01-T03`, `E01-T04`, `E01-T05`):**
   - **`E01-T03`:** Triển khai tầng trừu tượng 3-tier `LLMProvider` (`Mock`, `Ollama CPU`, `Gemini`), `ProviderFactory`, `ProviderTelemetry` trung thực và hệ thống ngoại lệ phân cấp.
   - **`E01-T04`:** Tạo bộ dữ liệu synthetic sạch chuẩn `P05`/`P06` gồm 3 SKU `OCOP: VERIFIED` mô phỏng, 4 SKU âm tính (negative fixtures), 3 mục tiêu merchant và 3 `StoryPlan` tham chiếu (`is_mvp_live_eligible() is True`).
   - **`E01-T05`:** Triển khai cổng đọc-chỉ-đọc `P05KnowledgeAdapter` (hỗ trợ đủ 4 `TargetScopeMode` theo `P06-OPEN-5`), các guardrail fail-closed (`ProhibitedEchoGuard`, `SafeFallbackSelector`), đồng hồ ảo `VirtualClock`, bus giả lập cô lập `MockPlaybackAckBus` và `SimulatedPlaybackHarness` kiểm tra toàn vẹn ACK 5 lớp.
3. **Wave D Independent Review & Remediation:** Reviewer độc lập phát hiện **`0 BLOCKER`**, **`0 MAJOR`**, **`5 MINOR`** (`MINOR-01..05`); toàn bộ 5 điểm nhẹ đã được khắc phục triệt để trong `WAVE-D-MINOR-FIXES`.
4. **Xác minh sau chỉnh sửa cuối:**
   - **`92/92` pytest tests pass** (`0 failed`, `0 skipped`, chạy trong `2.05s`).
   - **`pip check`:** Sạch (`No broken requirements found.`).
   - **An toàn dữ liệu & phạm vi:** **`0` secrets/PII**, **`0` tệp bị sửa bên ngoài `autonomous-storytelling/`** (P05/P07/frontend/backend nguyên vẹn 100%).

> [!NOTE]
> Kết quả `92/92` pass là bằng chứng **xác minh logic hợp đồng, kiểm định schema, an toàn fail-closed và điều phối offline** trên `MockLLMProvider` / `httpx.MockTransport` / `GeminiClientProtocol` giả lập. Năng lực sinh tiếng Việt thật của `Ollama` hay `Gemini API` vẫn ở trạng thái **`TO VALIDATE`** ở các pha sau.

---

## 2. Multi-Agent Execution Report (Báo cáo Điều phối Đa Tác tử)

Đợt triển khai sử dụng mô hình điều phối **Main Orchestrator + Bounded Subagents** theo quy trình phân tầng 4 wave (A -> Pre-B -> B -> C -> D), đảm bảo phân tách quyền ghi tệp (disjoint file ownership) và kiểm soát chất lượng tại từng cổng.

### 2.1. Thực tế Runtime Agent Definitions & Routing

- Khi khởi động phiên, hai tệp định nghĩa subagent toàn cục `~/.gemini/config/agents/hydrogen-scout.md` và `~/.gemini/config/agents/hydrogen-executor.md` trả về lỗi `"not found"` do phiên làm việc hiện tại đã được khởi tạo trước thời điểm các tệp này được mount vào cấu hình.
- Để giữ đúng kỷ luật phân tầng model (`Hydrogen` / `flash`) và cô lập ngữ cảnh của Main Agent:
  - **Wave A (Scouting):** Main Agent gọi hai subagent dạng `self` gắn `Model: "flash"`, áp đặt nguyên văn quy tắc chỉ-đọc và báo cáo gọn của `hydrogen-scout.md` (`Scout A`, `Scout B`).
  - **Execution & Review Modes:** Trong Execution Mode, hệ thống định nghĩa tường minh hai kiểu subagent chuyên biệt gắn `Model: "inherit"` (chạy trực tiếp trên `Hydrogen`):
    - `p06-executor` (`EnableWriteTools: true`, `EnableSubagentTools: false`): thực thi sửa mã nguồn và chạy pytest trong phạm vi file được cấp phép.
    - `p06-reviewer` (`EnableWriteTools: true`, `EnableSubagentTools: false` kèm prompt ràng buộc **nghiêm cấm chỉnh sửa file**, chỉ đọc và chạy lệnh kiểm tra): đóng vai trò kiểm định viên độc lập ở Wave D.

### 2.2. Chuỗi Thực thi Theo Từng Wave

| Wave | Tác nhân | Phạm vi & Đầu việc | Kết quả / Cổng kiểm soát |
| :--- | :--- | :--- | :--- |
| **Wave A** | `Scout A` & `Scout B` (`self`, `Model: "flash"`) | Kiểm toán sâu `src/p06/schemas/` đối chiếu LangGraph `1.2.24`, Pydantic `2.14.4`, `P05` và hợp đồng `p06-mock-v0.1` | Phát hiện `2 BLOCKER`, `3 MAJOR`, `3 MINOR` tại Phase 1 |
| **Pre-Wave B** | `p06-executor` | Sửa toàn bộ `A-BLK-01..02`, `A-MAJ-01..03`, `A-MIN-01..03` trong `src/p06/schemas/` và cập nhật test | Audit Gate Pass: `28 -> 33` pytest tests pass |
| **Wave B (Song song)** | `Executor A` (`E01-T03`) & `Executor B` (`E01-T04`) | `Executor A`: `src/p06/providers/` + `test_providers.py`<br>`Executor B`: `data/` (4 JSON fixtures + `data/README.md`) + `test_e01_dataset.py` | Phân tách file rời nhau hoàn toàn; tổng test lên `33 -> 42 (+T04) -> 61 (+T03)` |
| **Wave C** | `Executor C` (`E01-T05`) | Triển khai `src/p06/adapters/`, `adapters/mocks/`, `guardrails/`, `simulation/` + `test_p05_knowledge_adapter.py` + `test_playback_harness_and_guardrails.py` | Cộng thêm `28` test (`61 -> 89` passed) |
| **Wave D** | `p06-reviewer` + `WAVE-D-MINOR-FIXES` + `WAVE-D-DOCS-AND-REPORT` | Review chéo độc lập toàn bộ diff Phase 1–2 (`0 BLOCKER`, `0 MAJOR`, `5 MINOR`), vá `MINOR-01..05`, và đồng bộ tài liệu (`04-...`, `03-...`, `docs/README.md`, `AGENTS.md`, `README.md`) | Đóng mọi finding: `89 -> 92/92` tests pass; `pip check` sạch |

**Vai trò Main Agent:** Đóng vai trò Kiến trúc sư & Điều phối viên — không tự ôm đọc tràn lan hay viết thay subagent; tổng hợp phát hiện từ Wave A, ra quyết định Audit Gate giữa các wave, bảo đảm bất biến `I-01`–`I-09` & `P06-OPEN-1..6`, và xác minh kết quả cuối cùng.

---

## 3. Phase 1 Audit Report (`A-BLK-01..02`, `A-MAJ-01..03`, `A-MIN-01..03`)

Cuộc kiểm toán Phase 1 (Wave A -> Pre-Wave B) đã ngăn chặn sớm các lỗi nghiêm trọng trước khi tầng provider và LangGraph đi vào hoạt động:

| Mã Finding | Mức độ | Mô tả Vấn đề Gốc | Giải pháp Khắc phục (`src/p06/schemas/`) |
| :--- | :---: | :--- | :--- |
| **`A-BLK-01`** | `BLOCKER` | `StateGraph(AgentState).compile().invoke()` trong LangGraph trả về `dict` thô và **bỏ qua** `@model_validator(mode="after")` sau node cuối, có thể để lọt `AgentState` gãy bất biến `I-02`/`I-06`. | Bổ sung `AgentState.from_graph_result()` bắt buộc tái kiểm định bằng `cls.model_validate(...)` ở ranh giới đầu ra của đồ thị và khóa test hồi quy tương ứng. |
| **`A-BLK-02`** | `BLOCKER` | `ConfigDict(validate_assignment=True)` trên các model có khả năng mutate trực tiếp làm hỏng trạng thái object khi gán dở dang bị lỗi, đồng thời chặn chuyển tiếp nguyên tử `DRAFT -> VERIFIED` khi các field kiểm chứng phụ thuộc lẫn nhau. | Chuyển toàn bộ các model cốt lõi sang **`frozen=True`** và cung cấp các phương thức chuyển trạng thái nguyên tử qua `model_validate()`: `StoryPlan.with_approval()`, `SpeechCandidate.mark_verified()`, `SpeechCandidate.mark_rejected()`, `StoryCheckpoint.advance_on_playback()`, và `AgentState.validated_update()`. |
| **`A-MAJ-01`** | `MAJOR` | Pydantic mặc định ép kiểu lỏng (`bool` -> `int` với `True == 1`, hoặc `"true"` / `1` -> `bool`), làm sai lệch phiên bản, số lượt retry và cờ `is_authoritative`. | Áp dụng nghiêm ngặt `StrictInt`, `StrictBool`, `StrictFalse`, `StrictPositiveInt`, `StrictNonNegInt`, `StrictPositiveDurationMs`, `StrictPositivePriceVnd` trên toàn bộ schema. |
| **`A-MAJ-02`** | `MAJOR` | Chuỗi chỉ chứa khoảng trắng (`"   "`) vẫn vượt qua `min_length=1` cho các mã `tenant_id`, `session_id`, `sku_id`, `topic_id`. | Định nghĩa và áp dụng kiểu `NonBlankStr` / `OptionalNonBlankStr` chuẩn hóa kiểm tra không rỗng sau `.strip()`. |
| **`A-MAJ-03`** | `MAJOR` | `AgentState` thiếu kiểm định tham chiếu chéo cho `story_checkpoint.next_topic_id`, `selected_arc_id`, `selected_topic_id`, `draft_chunk` và kích thước `played_history`. | Bổ sung kiểm tra toàn vẹn tham chiếu giữa `story_plan`, `story_checkpoint`, `selected_*`, `draft_chunk` (khớp `plan_id`, `plan_revision`, `arc_id`, `topic_id`, `pinned_sku_ids`) và biên `len(played_history) <= played_history_window_size`. |
| **`A-MIN-01..03`** | `MINOR` | Các chi tiết làm chặt hợp đồng biên, tính nhất quán `CONTRACT_VERSION` / `StoryChunk`, và chuẩn hóa docstring/exports `__all__`. | Chuẩn hóa alias `ContractVersion`, tách `is_mvp_live_eligible()` kiểm tra chuẩn `ACR-002` (`2–5` SKU) vs `W0` single-SKU, và đồng bộ `__all__`. |

> [!WARNING]
> **Lưu ý về giới hạn Python `frozen=True` nông (shallow):** `ConfigDict(frozen=True)` của Pydantic v2 ngăn gán lại thuộc tính cấp top-level (ví dụ `state.active_sku_id = ...`), nhưng **không** tự động đóng băng phần tử bên trong `list` hoặc `dict` lồng nhau (ví dụ `knowledge_versions_by_sku` hay `supporting_fact_ids`). Ở Wave D (`MINOR-01`), trường `AgentState.completed_topic_ids` đã được siết từ `set[str]` sang **`frozenset[NonBlankStr]`** để bất biến thực sự ở runtime; với các `dict`/`list` còn lại, caller vẫn phải dùng `validated_update()` thay vì mutate in-place.

---

## 4. `E01-T03` — Tầng Trừu tượng 3-Tier `LLMProvider` (`src/p06/providers/`)

Thực hiện đầy đủ nguyên tắc `P06-OPEN-1` để LangGraph node và runner hoán đổi giữa kiểm thử offline, CPU smoke test và thí nghiệm chính thức thuần bằng YAML mà không sửa đồ thị.

### 4.1. Kiến trúc Module & Thành phần Đã Triển khai

| Tệp (`src/p06/providers/`) | Thành phần chính | Vai trò & Bất biến cốt lõi |
| :--- | :--- | :--- |
| [`base.py`](../src/p06/providers/base.py) | `LLMProvider(ABC)`, `GenerationRequest`, `GenerationResult[OutputT]`, `ProviderTelemetry`, `ProviderTier`, `TokenUsageSource`, `ProviderError` hierarchy | Khóa giao diện `generate_structured(request, output_schema)`. Cấm tuyệt đối từ khóa nhạy cảm (`SENSITIVE_SAMPLING_KEYS = {"api_key", "key", "secret", "token", "authorization", "password"}`, ngoại lệ duy nhất `max_tokens`/`max_output_tokens`) lọt vào telemetry. Tách 3 giá trị `TokenUsageSource`: `MEASURED`, `SIMULATED`, `UNAVAILABLE`. |
| [`mock_provider.py`](../src/p06/providers/mock_provider.py) | `MockLLMProvider`, `MockBehavior`, `MockResponseStep` | Tier 1 (`UNIT_TEST`): dùng `hashlib.sha256` để chọn biến thể tất định theo `seed` (cấm Python `hash()` vốn đổi theo `PYTHONHASHSEED`). Hỗ trợ `response_sequence` (`deque`) và `keyed_responses` để giả lập `VALID_JSON`, `MALFORMED_JSON`, `INVALID_SCHEMA`, `TIMEOUT`, `PROVIDER_FAILURE`. Gắn `is_simulated_metric=True`, `token_usage_source=SIMULATED`. |
| [`ollama_provider.py`](../src/p06/providers/ollama_provider.py) | `OllamaLocalProvider`, `OllamaProviderConfig` | Tier 2 (`LOCAL_SMOKE_TEST`): gọi `/api/chat` qua `httpx.Client` (cho phép inject `httpx.MockTransport`). Không gọi HTTP trong `__init__`. Khi Ollama không trả `prompt_eval_count`/`eval_count`, bắt buộc ghi `None` + `token_usage_source=UNAVAILABLE` (**không** bịa `0`). |
| [`gemini_provider.py`](../src/p06/providers/gemini_provider.py) | `GeminiAPIProvider`, `GeminiProviderConfig`, `GeminiClientProtocol`, `GeminiRawResponse` | Tier 3 (`FORMAL_EXPERIMENT`): rào kiểm tra 2 lớp (khởi tạo + trước khi gọi) chặn `model_id` giữ chỗ (`TBD...`, `PLACEHOLDER...`), thiếu env `GEMINI_API_KEY`, hoặc dữ liệu ngoài `allowed_data_classifications` (`SYNTHETIC`, `PUBLIC_APPROVED`). Tiêm client qua `GeminiClientProtocol` (structural typing). **Zero silent fallback** sang `MockLLMProvider`. |
| [`factory.py`](../src/p06/providers/factory.py) | `ProviderFactory` | Nạp YAML từ `configs/models/*.yaml` (`from_yaml`, `from_dict`), cưỡng chế khớp 1-1 `(provider, run_tier)`: `mock <-> unit_test`, `ollama <-> local_smoke_test`, `gemini <-> formal_experiment`. |
| [`__init__.py`](../src/p06/providers/__init__.py) | Public exports (`__all__`) | Xuất khẩu sạch toàn bộ DTO, Enum, Provider, Factory và Exceptions mà không gọi mạng lúc import. |

### 4.2. Kiểm thử & Giới hạn Chưa Kiểm chứng

- **Kiểm thử đơn vị (`tests/unit/test_providers.py`):** Ban đầu gồm `19` test case, mở rộng thành **`22` test items** sau Wave D (`9` ca parametrize kiểm tra `SENSITIVE_SAMPLING_KEYS`, kiểm tra lỗi JSON/Schema, sequence retry cho bounded rewrite, deterministic SHA-256 seed, `httpx.MockTransport` cho Ollama, các lớp rào bảo mật của Gemini và tải toàn bộ `configs/models/*.yaml`).
- **Giới hạn chưa kiểm chứng (EXPLICIT UNVERIFIED LIMITS):**
  - **Live Ollama inference:** Chưa chạy gọi mô hình Ollama thật (`qwen3:1.7b` / `qwen3:4b`) trên runtime CPU thực tế; mới kiểm chứng hợp đồng HTTP và xử lý lỗi qua `httpx.MockTransport`.
  - **Live Gemini API:** Chưa gọi Google Gemini API thật, chưa xác minh `model_id` thương mại, quota/pricing và DPA review. Không có bất kỳ kết luận nào về chất lượng tiếng Việt hay độ trễ thật từ `E01-T03`.

---

## 5. `E01-T04` — Bộ Dữ liệu Synthetic Sạch (`data/`)

Bộ fixture của `E01-T04` tuân thủ nghiêm ngặt quy tắc tách bạch **dữ liệu dương tính** (`OCOP: VERIFIED` mô phỏng) và **dữ liệu âm tính** (để kiểm thử fail-closed ở cổng P05 và `P06-E04`).

| Tệp (`data/`) | Nội dung & Quy mô | Quy tắc Kiểm soát & Grounding |
| :--- | :--- | :--- |
| [`products/e01_verified_skus.json`](../data/products/e01_verified_skus.json) | **3 SKU thực phẩm đóng gói:**<br>1. `SKU-HONEY-01`: Mật ong hoa cà phê Đắk Lắk nguyên chất 500ml (`159.000đ`)<br>2. `SKU-TEA-02`: Trà Shan Tuyết cổ thụ Hà Giang hộp thiếc 200g (`245.000đ`)<br>3. `SKU-MACADAMIA-03`: Hạt mắc ca sấy nứt vỏ Lâm Đồng hộp 500g (`195.000đ`)<br>Kèm **15 `EvidenceChunk`** (5/SKU) và 3 nhóm claim (`ALLOWED`, `REQUIRES_OFFICIAL_VERIFICATION`, `PROHIBITED`). | Cả 3 SKU đều `approval_status: "APPROVED"`, `ocop_status: "VERIFIED"`, `food_safety_verified: true`, `rights_status: "ACTIVE"`, `tenant_id: "tenant-p06-poc-01"`. Toàn bộ mang nhãn `is_synthetic: true`. |
| [`products/e01_negative_skus.json`](../data/products/e01_negative_skus.json) | **4 SKU âm tính (cách ly hoàn toàn khỏi tập verified):**<br>1. `SKU-CASHEW-03` (`ocop_status: "PENDING"`)<br>2. `SKU-COFFEE-EXPIRED-04` (`rights_status: "EXPIRED"`)<br>3. `SKU-GINGER-UNSAFE-05` (`food_safety_verified: false`)<br>4. `SKU-LOTUS-DRAFT-06` (`approval_status: "DRAFT"`) | Kiểm chứng đủ 4 mã từ chối chuẩn P05: `OCOP_NOT_VERIFIED`, `RIGHTS_INVALID`, `FOOD_SAFETY_UNVERIFIED`, `UNAPPROVED_FACT`. |
| [`merchant_goals/e01_goals.json`](../data/merchant_goals/e01_goals.json) | **3 mục tiêu phiên bán hàng:** `goal_e01_product_education` (10m), `goal_e01_brand_storytelling` (10m), `goal_e01_sales_presentation` (30m). | Mỗi mục tiêu định nghĩa rõ `mandatory_topics`, `prohibited_topics`, `mandatory_messages` và `expected_mandatory_topic_ids` bám sát 3 SKU verified. |
| [`story_plans/e01_story_plans.json`](../data/story_plans/e01_story_plans.json) | **3 `StoryPlan` tham chiếu chuẩn `p06-mock-v0.1`:** `product_education_10m`, `brand_storytelling_10m`, `sales_presentation_30m`. | Gắn `fixture_role: "reference_evaluation_fixture_not_llm_output"` và `simulated_approval: true`; toàn bộ 3 kế hoạch đạt `plan.is_mvp_live_eligible() is True` (`3` SKU, `APPROVED`). |

> [!IMPORTANT]
> **Tuyên bố miễn trừ trách nhiệm về `OCOP: VERIFIED` mô phỏng:** Toàn bộ mã `SYNTH-OCOP-*` và trạng thái `ocop_status: "VERIFIED"` trong `e01_verified_skus.json` chỉ là dữ liệu tổng hợp phục vụ kiểm thử logic PoC P06 (`simulated_approval: true`), **KHÔNG phải** chứng nhận OCOP hợp pháp từ hệ thống P09 hay cơ quan quản lý nhà nước.

- **Kiểm thử dữ liệu (`tests/unit/test_e01_dataset.py`):** **`9/9` test items pass** — xác nhận tính duy nhất ID, 3 SKU dương tính đi qua `PublicationGate` của P05, 4 SKU âm tính bị chặn đúng mã lý do, `StoryPlan` khớp `fact_refs` với `EvidenceChunk` trong kho P05, đồng bộ `e01_goals.json`, và không chứa từ khóa cấm y tế hay PII.

---

## 6. `E01-T05` — Adapter Tri thức P05, Guardrails & Simulated Playback (`adapters/`, `guardrails/`, `simulation/`)

`E01-T05` khóa chặt hai ranh giới an toàn sống còn của HOSTRA AI: **không phát ngôn khi chưa qua Cổng P05 (`I-02`)** và **không tính tiến độ khi chưa có `PlaybackCompleted` ACK (`I-03`, `I-06`)**.

### 6.1. Giao tiếp Chỉ-Đọc với P05 & Hỗ trợ 4 `TargetScopeMode` (`P06-OPEN-5`)

- **Nạp động cô lập (`_load_p05_modules`):** Sử dụng `importlib.util.spec_from_file_location` để nạp trực tiếp `schemas.py` và `publication_gate.py` từ `experiments/sales-intelligence/knowledge-verification/` mà **không sao chép, fork hay sửa bất kỳ byte nào của P05**. Vì `publication_gate.py` của P05 dùng `from schemas import ...`, hàm lưu cache theo `Path.resolve()` và tạm gán `sys.modules["schemas"] = p05_schemas` trong khối `try ... finally` để khôi phục nguyên trạng, triệt tiêu xung đột với `p06.schemas`.
- **`P05KnowledgeAdapter` (`src/p06/adapters/p05_knowledge_adapter.py`):** Triển khai `KnowledgeVerifierPort` cho đủ 4 chế độ `TargetScopeMode`:
  1. **`SINGLE_SKU`:** Kiểm tra cô lập tenant (`R10`), đối chiếu chống TOCTOU qua `SkuVersionBinding` (`knowledge_version`, `ocop_version`, `rights_version`, `price_vnd`), chạy `ProhibitedEchoGuard` và ủy quyền kiểm duyệt cuối cho `PublicationGate.verify()`.
  2. **`MULTI_SKU_COMPARE`:** Kiểm chứng đồng thời danh sách `target_sku_ids` qua `PublicationGate`, tách câu/mệnh đề để **quy chiếu giá đúng từng SKU (clause price attribution)** (chặn hoán đổi giá giữa các SKU hoặc giá trôi nổi không gắn tên SKU), hỗ trợ phủ định đa từ tiếng Việt khi kiểm tra, và **fail-closed** trước các cụm so sánh cảm tính (`tốt hơn`, `ngon hơn`, `đáng mua hơn`, `rẻ nhất`...) trừ khi có claim/evidence `APPROVED` tường minh.
  3. **`SHOP_WIDE_POLICY`:** Hiện tại `PublicationGate` của P05 mới hỗ trợ kiểm chứng theo đơn-SKU và chưa có cổng tri thức cấp shop. Adapter tuân thủ nghiêm nguyên tắc **fail-closed**, từ chối phát hành với mã `UNSUPPORTED_SHOP_POLICY_VERIFICATION` thay vì tự ý cho qua (xem mục 11 về khoảng trống P05).
  4. **`UNRESOLVED_SKU`:** Tách biệt nghiêm ngặt khỏi `SHOP_WIDE_POLICY`. Áp dụng bộ bảo vệ zero-leak: chỉ cho phép câu hỏi làm rõ trung tính; lập tức chặn nếu phát hiện rò rỉ tên/mã SKU (`SKU-...`), giá bán (`159.000đ`), nhắc tới `OCOP`, cụm từ cấm y tế, hay mẫu prompt injection (`ignore all previous instructions...`).

### 6.2. Guardrails & Mô phỏng Phát sóng 5 Lớp (`I-03`, `I-06`)

| Thành phần | Tệp | Cơ chế bảo vệ cốt lõi |
| :--- | :--- | :--- |
| **`ProhibitedEchoGuard`** | [`prohibited_echo_guard.py`](../src/p06/guardrails/prohibited_echo_guard.py) | Lớp phòng thủ **defense-in-depth** chuẩn hóa khoảng trắng/chữ thường (`" ".join(text.lower().split())`) để bắt lỗi lặp cụm từ công dụng như thuốc từ bình luận khách hoặc chèn khoảng trắng lách lọc (`"chữa   bệnh"`). Ghi rõ cảnh báo không thay thế `PublicationGate`. |
| **`SafeFallbackSelector`** | [`fallback_selector.py`](../src/p06/guardrails/fallback_selector.py) | Khi cạn ngân sách viết lại (`P06-E04`), lọc đúng ứng viên `PREAPPROVED_FALLBACK`, gọi `_reset_candidate_to_draft()` xóa dấu vết duyệt cũ rồi **tái kiểm định trực tiếp (live re-verification)** qua `KnowledgeVerifierPort.verify_candidate()` nhằm chống TOCTOU. Trả `None` nếu toàn bộ trượt -> kích hoạt `SAFE_ABORT_NO_CANDIDATE`. |
| **`VirtualClock`** | [`virtual_clock.py`](../src/p06/simulation/virtual_clock.py) | Đồng hồ UTC tất định (`DEFAULT_VIRTUAL_START_AT`), ước lượng thời lượng nói tiếng Việt (`~2.6 từ/giây`, kẹp `[1000ms, 30000ms]`), chạy phiên 10–30 phút trong vài mili-giây CPU thật **không dùng `time.sleep()`**, cấm lùi thời gian, cấm `bool`/`NaN`/`Inf`. |
| **`MockPlaybackAckBus`** | [`playback_bus.py`](../src/p06/adapters/mocks/playback_bus.py) | Cô lập hoàn toàn trong `adapters/mocks/`. Từ chối phát ứng viên chưa `VERIFIED`, sinh `PlaybackAckResult` cho cả 3 trạng thái `COMPLETED` / `FAILED` / `UNKNOWN`, bắt buộc gắn `SIMULATED_HARNESS` (`is_simulated=True`, `p04_evidence_ref=None`) và `auto_replay_permitted=False`. |
| **`SimulatedPlaybackHarness`** | [`playback_harness.py`](../src/p06/simulation/playback_harness.py) | Thực thi **kiểm tra toàn vẹn ACK 5 lớp**: (1) chặn `FAILED`/`UNKNOWN` (`auto_replay_permitted=False`); (2) **Idempotency** chống xử lý trùng `playback_event_id` và kết thúc lại `turn_id`; (3) đối chiếu đồng bộ `tenant_id`, `session_id`, `session_epoch`, `plan_revision`, `candidate_id`, `chunk_id` và `occurred_at` đơn điệu không giảm; (4) kiểm tra provenance mô phỏng vs `P04_MEDIA_CONTROLLER`; (5) cập nhật nguyên tử `StoryCheckpoint`, `played_history` (cắt theo cửa sổ `W`) và `completed_topic_ids` (`frozenset`). |

### 6.3. Khắc phục Các Điểm Nhẹ Từ Wave D (`MINOR-01..05`)

Sau khi `p06-reviewer` rà soát độc lập, cả 5 điểm nhẹ đã được xử lý và kiểm thử hồi quy:
- **`MINOR-01`:** Chuyển `AgentState.completed_topic_ids` sang `frozenset[NonBlankStr]` để chống mutate ngầm làm gãy bất biến bất biến (`frozen=True`).
- **`MINOR-02`:** Làm chặt kiểm định `MockLLMProvider` khi cấu hình lỗi/hàng đợi và bảo đảm nhất quán telemetry.
- **`MINOR-03`:** Siết chuẩn hóa `ProviderTelemetry` và khóa nhạy cảm trong `sampling_params` (kèm test kiểm tra ngoại lệ an toàn cho `max_tokens`/`max_output_tokens`).
- **`MINOR-04`:** Gia cố kiểm tra `UNRESOLVED_SKU` / `MULTI_SKU_COMPARE` trong `P05KnowledgeAdapter` trước chuỗi có dấu câu số học (`159.000đ`) và biến thể injection/leaks.
- **`MINOR-05`:** Hoàn thiện kiểm tra biên chứng thực trong `SimulatedPlaybackHarness` và `SafeFallbackSelector` khi tái kiểm định live.

---

## 7. Giải thích Kiến thức Kỹ thuật Cốt lõi (Technical Knowledge Explanation)

Phần này hệ thống hóa 15 khái niệm kỹ thuật Agent Engineering xuất hiện trực tiếp trong `src/p06/` kèm ví dụ ngắn từ chính mã nguồn P06 để thành viên mới và sinh viên Data Science nắm vững bản chất:

1. **Dependency Inversion (Đảo ngược Phụ thuộc):** Module nghiệp vụ cấp cao (LangGraph nodes, `SafeFallbackSelector`) không phụ thuộc vào thư viện cụ thể (`httpx`, SDK Gemini, file `publication_gate.py` của P05), mà phụ thuộc vào lớp trừu tượng (`LLMProvider`, `KnowledgeVerifierPort`, `PlaybackAckBusPort`).
   - *Ví dụ P06:* `SafeFallbackSelector.select_safe_fallback(verifier: KnowledgeVerifierPort, ...)` không cần biết `verifier` là `P05KnowledgeAdapter` hay mock test.
2. **Adapter Pattern (Mẫu Bộ chuyển đổi):** Chuyển đổi giao diện của hệ thống ngoài (`P05 PublicationGate` đơn-SKU) sang giao diện chuẩn mà P06 cần (`KnowledgeVerifierPort` hỗ trợ 4 `TargetScopeMode`) mà không sửa mã nguồn bên ngoài.
   - *Ví dụ P06:* `P05KnowledgeAdapter` bọc `VersionedKnowledgeStore` + `PublicationGate` của P05 (`../knowledge-verification/`), quy đổi `EligibilitySnapshot` + `ProductFact` thành `SkuEvidenceView`.
3. **Factory Pattern (Mẫu Nhà máy Khởi tạo):** Tập trung hóa logic khởi tạo đối tượng phức tạp theo cấu hình tại một điểm duy nhất.
   - *Ví dụ P06:* `ProviderFactory.from_yaml("configs/models/mock.yaml")` tự kiểm tra cặp `(provider, run_tier)` và trả về `MockLLMProvider`, `OllamaLocalProvider` hoặc `GeminiAPIProvider`.
4. **ABC vs Protocol (Kế thừa Tường minh vs Định kiểu Cấu trúc):**
   - `ABC` (`LLMProvider(ABC)`, `KnowledgeVerifierPort(ABC)`) yêu cầu lớp con kế thừa tường minh và cài đặt mọi `@abstractmethod`.
   - `Protocol` (`@runtime_checkable class GeminiClientProtocol(Protocol)`) dùng *structural typing* (duck typing an toàn kiểu): bất kỳ client nào có hàm `generate_json(...) -> GeminiRawResponse` đều lắp vừa `GeminiAPIProvider` mà không cần kế thừa lớp cha của P06.
5. **Structured Output (Đầu ra Có Cấu trúc):** Thay vì nhận chuỗi văn bản tự do khó kiểm soát, mô hình phải sinh JSON tuân thủ schema Pydantic v2 (`output_schema: type[OutputT]`).
   - *Ví dụ P06:* `LLMProvider.parse_and_validate(raw_text, output_schema)` phân tách rạch ròi lỗi vỡ JSON (`MalformedJsonOutputError`) với lỗi sai schema (`SchemaValidationOutputError`) để điều khiển retry có chủ đích.
6. **Deterministic Mock (Giả lập Tất định):** Cùng một đầu vào và cấu hình phải trả về kết quả giống nhau 100% qua mọi lần chạy CI, không phụ thuộc ngẫu nhiên hệ thống hay `PYTHONHASHSEED`.
   - *Ví dụ P06:* `MockLLMProvider` băm khóa bằng `hashlib.sha256(seed_input.encode("utf-8")).digest()` để chọn biến thể, thay cho hàm `hash()` tích hợp của Python.
7. **Dependency Injection (Tiêm Phụ thuộc):** Truyền phụ thuộc (`http_client`, `client`, `clock`, `verifier`) từ bên ngoài vào hàm khởi tạo (`__init__`) thay vì tạo cứng bên trong.
   - *Ví dụ P06:* `OllamaLocalProvider(config, http_client=httpx.Client(transport=httpx.MockTransport(...)))` cho phép test toàn bộ logic HTTP/timeout/4xx/5xx mà không cần bật server Ollama.
8. **HTTP Client Abstraction (Trừu tượng hóa Giao tiếp HTTP):** Tách tầng vận chuyển HTTP (`httpx.Client` / `MockTransport`) khỏi logic đóng gói payload và ánh xạ lỗi nghiệp vụ.
   - *Ví dụ P06:* `OllamaLocalProvider` tách hàm xây dựng payload `/api/chat` và phân loại `httpx.TimeoutException` -> `ProviderTimeoutError`, lỗi status HTTP -> `ProviderTransportError`.
9. **Telemetry (Đo lường Minh bạch & An toàn Bí mật):** Ghi nhận độ trễ, số token, model, tier chạy một cách trung thực và không rò rỉ thông tin xác thực.
   - *Ví dụ P06:* `ProviderTelemetry` tách `TokenUsageSource.MEASURED` (Gemini/Ollama trả về thật), `SIMULATED` (Mock), và `UNAVAILABLE` (khi Ollama thiếu count -> giữ `None`, **không bịa `0`**); đồng thời chặn `SENSITIVE_SAMPLING_KEYS`.
10. **Versioned Knowledge (Tri thức Theo Phiên bản & Chống TOCTOU):** Mọi fact, quyền, OCOP và giá đều gắn số phiên bản tăng dần; trước khi phát phải kiểm tra xem dữ liệu lúc phát có bị cũ hơn thời điểm lập nháp (*Time-Of-Check to Time-Of-Use*) hay không.
    - *Ví dụ P06:* `SkuEvidenceView.to_version_binding()` khóa `knowledge_version`, `ocop_version`, `rights_version`, `price_vnd`; nếu giá trên kho tăng giữa chừng, `P05KnowledgeAdapter.verify_candidate()` lập tức chặn.
11. **Evidence-grounded Generation (Sinh Thoại Bám Bằng chứng):** Mọi phát ngôn sản phẩm phải truy vết được về `supporting_fact_ids` / `EvidenceChunk` đã `APPROVED` và loại trừ cụm từ cấm.
    - *Ví dụ P06:* Trong `e01_story_plans.json`, mỗi `StoryTopic` gắn `fact_refs` trỏ thẳng tới `evidence_id` trong `e01_verified_skus.json` (ví dụ `ev-e01-honey-usage`).
12. **Event-driven Architecture (Kiến trúc Hướng Sự kiện):** Các thành phần giao tiếp bằng sự kiện bất biến thay vì giả định đồng bộ ngầm.
    - *Ví dụ P06:* Sinh lời thoại xong (`SpeechCandidate` `VERIFIED`) **chưa** cập nhật lịch sử; chỉ khi nhận sự kiện `PlaybackCompleted` từ `PlaybackAckBusPort`, `SimulatedPlaybackHarness` mới tịnh tiến `StoryCheckpoint`.
13. **Fake Clock (Đồng hồ Ảo Tất định):** Thay thế thời gian thực (`time.time()`, `time.sleep()`) bằng đối tượng đồng hồ điều khiển được theo từng mili-giây.
    - *Ví dụ P06:* `VirtualClock.advance_sec(...)` mô phỏng trọn phiên live 30 phút (`1800s`) chỉ trong tích tắc CPU với mốc UTC lặp lại chính xác 100%.
14. **Idempotency (Tính Lũy đẳng):** Xử lý một sự kiện lặp lại nhiều lần (do network retry hoặc duplicate message) phải cho ra đúng trạng thái như xử lý đúng 1 lần đầu, không ghi trùng dữ liệu.
    - *Ví dụ P06:* `SimulatedPlaybackHarness` lưu tập `playback_event_id` và `turn_id` đã xử lý; nếu nhận lại cùng `playback_event_id`, hàm trả `AckApplyStatus.REJECTED_DUPLICATE_EVENT` và giữ nguyên `StoryCheckpoint`.
15. **Fail-closed Behavior (Đóng An toàn Khi Thiếu Căn cứ):** Khi gặp trường hợp chưa rõ, thiếu dữ liệu, sai ngữ cảnh hoặc lỗi kiểm tra, hệ thống mặc định **từ chối/chặn** thay vì cho qua.
    - *Ví dụ P06:* `SHOP_WIDE_POLICY` bị từ chối với `UNSUPPORTED_SHOP_POLICY_VERIFICATION`; `UNRESOLVED_SKU` chặn mọi chuỗi rò tên SKU/giá; `SafeFallbackSelector` trả `None` nếu toàn bộ fallback trượt kiểm định live.

---

## 8. Testing Report (Báo cáo Kiểm thử Tự động & Giới hạn)

### 8.1. Diễn tiến Số lượng Kiểm thử Qua Các Giai đoạn

```text
28 (Phase 1 pre-audit) -> 33 (Phase 1 post-audit, +5) -> 42 (+T04, +9) -> 61 (+T03, +19) -> 89 (+T05, +28) -> 92/92 (Wave D minor fixes, +3)
```

### 8.2. Kết quả Xác minh Sau Chỉnh sửa Cuối (`92/92 PASSED`)

Lệnh chạy kiểm thử thực tế tại repo root:

```powershell
.\.venv\Scripts\python.exe -m pytest experiments/sales-intelligence/autonomous-storytelling/tests -q
.\.venv\Scripts\python.exe -m pip check
```

- **Pytest:** **`92 passed in 2.05s` (`92/92 PASSED`, `0 failed`, `0 skipped`)**.
- **`pip check`:** **`No broken requirements found.`**
- **Quét bảo mật/PII:** **`0` secrets, `0` API keys, `0` PII** trong mã nguồn và bộ dữ liệu synthetic.

| Tệp Kiểm thử | Số test (`--collect-only`) | Phân loại | Nội dung Kiểm chứng Chính |
| :--- | :---: | :---: | :--- |
| [`tests/unit/test_story_schemas.py`](../tests/unit/test_story_schemas.py) | `13` | `Unit` | `StoryPlan` / `StoryArc` / `StoryTopic` / `StoryChunk`, `StrictInt`/`StrictBool`/`NonBlankStr`, `with_approval()` atomic, `is_mvp_live_eligible()` |
| [`tests/unit/test_candidate_and_events.py`](../tests/unit/test_candidate_and_events.py) | `9` | `Unit` | 4 `TargetScopeMode`, khóa `is_authoritative=False`, `mark_verified`/`mark_rejected`, `PlaybackCompleted`, `StoryCheckpoint.advance_on_playback()` |
| [`tests/unit/test_agent_state.py`](../tests/unit/test_agent_state.py) | `9` | `Unit` | `AgentState` invariants, `frozenset` immutability (`completed_topic_ids`), `validated_update()`, `StateGraph` + `AgentState.from_graph_result()` (`A-BLK-01`) |
| [`tests/unit/test_providers.py`](../tests/unit/test_providers.py) | `22` | `Unit` | `ProviderTelemetry` (`SENSITIVE_SAMPLING_KEYS` 9 ca + ngoại lệ `max_tokens`), `MockLLMProvider` sequence/SHA-256, `OllamaLocalProvider` (`MockTransport`, `UNAVAILABLE` tokens), `GeminiAPIProvider` guards, `ProviderFactory` YAML |
| [`tests/unit/test_e01_dataset.py`](../tests/unit/test_e01_dataset.py) | `9` | `Unit` | 3 SKU verified qua P05 `PublicationGate`, 4 SKU negative bị chặn đúng 4 mã lý do, `StoryPlan` grounding, đồng bộ `e01_goals.json`, quét cấm y tế/PII |
| [`tests/unit/test_playback_harness_and_guardrails.py`](../tests/unit/test_playback_harness_and_guardrails.py) | `12` | `Unit` | `ProhibitedEchoGuard`, `SafeFallbackSelector` live re-verification, `VirtualClock` 30m không `sleep()`, `MockPlaybackAckBus` + 8 kịch bản `SimulatedPlaybackHarness` |
| [`tests/contract/test_p05_contract_alignment.py`](../tests/contract/test_p05_contract_alignment.py) | `2` | `Contract` | Đối chiếu hợp đồng P05 allow/block và phát hiện TOCTOU trên `SkuVersionBinding` |
| [`tests/contract/test_p05_knowledge_adapter.py`](../tests/contract/test_p05_knowledge_adapter.py) | `16` | `Contract` | Cô lập tenant, TOCTOU giá/OCOP/rights, `SINGLE_SKU`, `MULTI_SKU_COMPARE` (clause price attribution + chặn so sánh cảm tính), `SHOP_WIDE_POLICY` fail-closed, `UNRESOLVED_SKU` zero-leak (6 ca injection/leak) |
| **Tổng cộng** | **`92`** | **100% Pass** | **`92 passed`, `0 failed`, `0 skipped`** |

### 8.3. Danh sách Kiểm tra Cố ý Không Chạy (`NOT RUN`)

- **`ruff` / `mypy`:** Chưa cài đặt trong `.venv` hiện tại -> **`NOT RUN`** (chỉ kiểm tra qua Pydantic strict types + review mã nguồn).
- **Ollama live inference (`qwen3:1.7b` / `qwen3:4b`):** **`NOT RUN`** — cần máy chủ Ollama cục bộ và thuộc giai đoạn smoke test ở `E01-T08`/`E01-T09`.
- **Gemini live API calls:** **`NOT RUN`** — chưa xác minh model ID, quota, pricing và DPA/terms review (`P06-OPEN-1`).

---

## 9. Definition of Done (DoD) Review cho `E01-T03..E01-T05`

| Hạng mục | Tiêu chí DoD trong Kế hoạch E01 | Trạng thái | Bằng chứng / Ghi chú |
| :--- | :--- | :---: | :--- |
| **`E01-T03`** | Giao diện `LLMProvider` + `ProviderFactory` + 3 provider + YAML binding + unit tests lỗi/telemetry | `COMPLETED` *(Offline Tier)* | Đủ 6 file trong `src/p06/providers/`, `22` test items pass; nạp được cả 4 YAML trong `configs/models/` |
| **`E01-T03`** *(Live)* | Kiểm chứng sinh tiếng Việt thật & độ trễ thực tế trên Ollama CPU và Gemini Flash | `TO VALIDATE` | Chủ ý chưa chạy ở Phase 2 (`P06-OPEN-1`) |
| **`E01-T04`** | 3 SKU `OCOP: VERIFIED` mô phỏng + 4 SKU negative tách riêng + 3 goals + 3 reference `StoryPlan`s qua P05 gate | `COMPLETED` *(Synthetic)* | 4 tệp JSON dưới `data/` + `data/README.md` + `9/9` tests pass; đã gắn tuyên bố miễn trừ OCOP mô phỏng |
| **`E01-T05`** | Adapter đọc-chỉ-đọc sang P05 hỗ trợ đủ 4 `TargetScopeMode` + Guardrails + `VirtualClock` + `MockPlaybackAckBus` + `SimulatedPlaybackHarness` | `COMPLETED` *(PoC Simulation)* | 9 file Python trong `adapters/`, `guardrails/`, `simulation/` + `28` test items (`16` contract + `12` unit) pass; P05 nguyên vẹn |
| **Quản trị & An toàn** | Không sửa module ngoài P06, không secret/PII, không gắn nhãn `VALIDATED` sai thẩm quyền | `COMPLETED` | `0` file ngoài `autonomous-storytelling/`, `pip check` sạch, `Owner`/`Reviewer` giữ `PENDING ASSIGNMENT` |

---

## 10. Git Change Summary (Tóm tắt Thay đổi Git)

- **Nhánh làm việc:** `research/p06-autonomous-storytelling`
- **Commit gốc (Base Checkpoint):** `p06-checkpoint-02-foundation` (`da385bd`)
- **Phạm vi ngoài P06 (`apps/`, `docs/` gốc, `P05`, `P07`, `.agents/`):** **`0` tệp bị sửa đổi**.

### 10.1. Tệp Hiện có Được Chỉnh sửa (Modified)

- **Phase 1 Audit Hardening (`src/p06/` & `tests/`):**
  - `src/p06/__init__.py`, `src/p06/schemas/__init__.py`, `src/p06/schemas/story.py`, `src/p06/schemas/candidate.py`, `src/p06/schemas/events.py`, `src/p06/schemas/state.py`
  - `tests/unit/test_story_schemas.py`, `tests/unit/test_candidate_and_events.py`, `tests/unit/test_agent_state.py`, `tests/contract/test_p05_contract_alignment.py`
- **Tài liệu Dữ liệu & Điều hướng (`docs/`, `AGENTS.md`, `README.md`):**
  - `data/README.md`, `docs/03-phase1-foundation-e01-t01-t02-report.md`, `docs/README.md`, `AGENTS.md`, `README.md`

### 10.2. Tệp Mới Được Tạo (New / Untracked)

- **`E01-T03` (`src/p06/providers/` & `tests/`):** `__init__.py`, `base.py`, `mock_provider.py`, `ollama_provider.py`, `gemini_provider.py`, `factory.py`, `tests/unit/test_providers.py`
- **`E01-T04` (`data/` & `tests/`):** `data/products/e01_verified_skus.json`, `data/products/e01_negative_skus.json`, `data/merchant_goals/e01_goals.json`, `data/story_plans/e01_story_plans.json`, `tests/unit/test_e01_dataset.py`
- **`E01-T05` (`src/p06/{adapters,guardrails,simulation}/` & `tests/`):**
  - `src/p06/adapters/{__init__.py,interfaces.py,p05_knowledge_adapter.py}`
  - `src/p06/adapters/mocks/{__init__.py,playback_bus.py}`
  - `src/p06/guardrails/{__init__.py,prohibited_echo_guard.py,fallback_selector.py}`
  - `src/p06/simulation/{__init__.py,virtual_clock.py,playback_harness.py}`
  - `tests/contract/test_p05_knowledge_adapter.py`, `tests/unit/test_playback_harness_and_guardrails.py`
- **Báo cáo đợt làm việc (`docs/`):** `docs/04-phase2-research-infrastructure-e01-t03-t05-report.md`

**Các tệp trọng tâm khuyến nghị người dùng / Tech Lead ưu tiên review:**
1. [`src/p06/schemas/state.py`](../src/p06/schemas/state.py) (`from_graph_result`, `validated_update`, `frozenset`)
2. [`src/p06/providers/base.py`](../src/p06/providers/base.py) & [`factory.py`](../src/p06/providers/factory.py)
3. [`src/p06/adapters/p05_knowledge_adapter.py`](../src/p06/adapters/p05_knowledge_adapter.py) (4-mode verification & multi-SKU price attribution)
4. [`src/p06/simulation/playback_harness.py`](../src/p06/simulation/playback_harness.py) (5-layer ACK integrity)
5. [`data/products/e01_verified_skus.json`](../data/products/e01_verified_skus.json) & [`e01_negative_skus.json`](../data/products/e01_negative_skus.json)

---

## 11. Open Issues & Decisions (`P06-OPEN-1..6` & Khoảng trống Kỹ thuật)

| Hạng mục | Thực trạng hiện tại | Hành động / Quyết định Cần có |
| :--- | :--- | :--- |
| **`P06-OPEN-1` (Gemini & Ollama)** | Giao diện 3-tier hoàn tất; `gemini_flash.yaml` vẫn giữ `TBD_VERIFY_BEFORE_USE` | Trước Phase 4 chạy thật: chốt `model_id` Gemini chính xác, quota/cost và hoàn tất DPA/terms review; chạy smoke test Ollama CPU cục bộ |
| **`P06-OPEN-2` (4-Part Memory)** | Mới có `PlayedTurnSummary` & `played_history_window_size` trong schema; chưa cài đặt module `memory/` | Triển khai đầy đủ tại **`E01-T06`** (`W ∈ {5, 10, 20}`, rule-based repetition trước) |
| **`P06-OPEN-3` (Recap Policy)** | Giữ `OFF` trong `P06-E01` | Hoãn sang `P06-E03` và đánh giá cùng PO |
| **`P06-OPEN-4` (Human Eval)** | Có `human_eval_rubric_v0.1.md`, chưa pilot calibration | Thực hiện pilot calibration trước Phase 5 blind rating |
| **`P06-OPEN-5` & Khoảng trống `SHOP_WIDE_POLICY` trên P05** | `P05 PublicationGate` hiện chỉ verify đơn-SKU (`ProductFact`/`ClaimRegistryEntry`). `P05KnowledgeAdapter` đang **fail-closed** (`UNSUPPORTED_SHOP_POLICY_VERIFICATION`) khi gặp `SHOP_WIDE_POLICY`. | Cần thống nhất liên module (`P05`/`P06`/`P07`/`P08`) bổ sung `ShopPolicyGate` hoặc bảng chính sách shop đã phê duyệt vào hợp đồng canonical trước Stage 06 |
| **`P06-OPEN-6` (Ownership)** | `Owner` & `Reviewer` vẫn là **`PENDING ASSIGNMENT`** | Tech Lead / PM phân công chính thức trước khi chạy formal experiment |
| **Shallow `frozen=True` trên `dict`/`list` lồng nhau** | Pydantic v2 `frozen=True` không đóng băng sâu `dict`/`list` bên trong model (trừ `completed_topic_ids` đã đổi sang `frozenset`) | Duy trì kỷ luật không mutate in-place các container lồng nhau trong `E01-T06..T09`; dùng `validated_update()` |
| **Công cụ lint/type tĩnh (`ruff`, `mypy`)** | Chưa cài trong `.venv` | Tech Lead quyết định có bổ sung `ruff` & `mypy` vào `pyproject.toml` (dev dependencies) trước Phase 3 hay không |

---

## 12. Đề xuất Pha Tiếp theo (`E01-T06` & `E01-T07`)

Sau khi commit checkpoint Phase 2 sạch sẽ, lộ trình tiếp theo được đề xuất triển khai tuần tự theo đúng kế hoạch `02-open-decisions-alignment-and-e01-plan.md`:

1. **`E01-T06` — Bộ nhớ 4 Thành phần (`src/p06/memory/`), `RepetitionDetector` & `ScriptFirstBaseline` (`src/p06/baselines/`):**
   - Xây dựng 4 thành phần bộ nhớ tách bạch: `ShortTermPlayedHistory` (nhận tham số `W ∈ {5, 10, 20}` từ YAML, **tuyệt đối không** hard-code), `GlobalTopicCoverage` (chỉ cập nhật qua ACK hợp lệ từ `SimulatedPlaybackHarness`), `SessionViewerContext` (`D11`/`D23`), và interface mở rộng `OptionalSemanticMemory`.
   - Cài đặt `RepetitionDetector` theo hướng **rule-based trước**: khớp `(intent, sku_id, covered_claim_ids)` kết hợp lexical/n-gram overlap trên cửa sổ `W` đã phát.
   - Cài đặt `ScriptFirstBaseline` (Phương án A) chạy cùng `P05KnowledgeAdapter` và `SimulatedPlaybackHarness` để bảo đảm đối chiếu công bằng (fair baseline) với Phương án B (LangGraph).
2. **`E01-T07` — `StoryPlanner` (`src/p06/planning/`), Versioned Prompts (`prompts/`) & LangGraph Workflow (`src/p06/agent/`):**
   - Thiết kế prompt template cho `StoryPlanner` và `ChunkDrafter` kèm version + SHA-256 hash trong `prompts/` (chỉ nạp từ dữ liệu `APPROVED` và `EvidenceChunk` của `SkuEvidenceView`).
   - Dựng đồ thị `StateGraph(AgentState)` với các node (`load_context`, `plan_or_select_topic`, `draft_chunk`, `verify_p05`, `bounded_rewrite`, `safe_fallback`, `bridge`), luôn gọi **`AgentState.from_graph_result(...)`** ở ranh giới đầu ra (`A-BLK-01`), và kiểm thử toàn luồng bằng `MockLLMProvider` (`tests/integration/`).
