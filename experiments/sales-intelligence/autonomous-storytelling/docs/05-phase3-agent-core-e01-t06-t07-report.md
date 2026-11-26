# Báo cáo Phase 3 — AI Agent Core, Memory System & LangGraph Workflow (`E01-T06..E01-T07`)

**Module:** `P06 — Sales Intelligence & Autonomous Storytelling`  
**Thí nghiệm mục tiêu:** `P06-E01` — *Storytelling Without Comments* (Giai đoạn Stage 03 PoC)  
**Nhánh Git:** `research/p06-autonomous-storytelling` · **Base Checkpoint:** `p06-checkpoint-03-infrastructure` (`a2805d5`)  
**Trạng thái:** `IN RESEARCH` (`E01-T06..E01-T07: COMPLETED` trên `MockLLMProvider` offline; `E01-T08..E01-T09` và thí nghiệm thực tế `P06-E01..E04`: `NOT STARTED`)  
**Ngày lập báo cáo:** `2026-11-26`  
**Owner / Reviewer độc lập:** `PENDING ASSIGNMENT` (`P06-OPEN-6`)

> [!IMPORTANT]
> Toàn bộ kiểm thử ở Phase 3 chạy ngoại tuyến bằng `MockLLMProvider` (`ProviderTier.UNIT_TEST`, `is_simulated_metric=True`) và dữ liệu synthetic (`e01_verified_skus.json`, `e01_negative_skus.json`, `e01_story_plans.json`). Kết quả **không** chứng minh chất lượng tiếng Việt, chi phí hay độ trễ của LLM thật (`Ollama`/`Gemini`), chưa đạt trạng thái `VALIDATED`, và **không** đại diện cho năng lực production.

---

## 1. Tóm tắt Điều hành & Tuân thủ Phạm vi

Trong Phase 3, nhóm đã hoàn thành hai cột mốc trọng yếu của lõi tác tử kể chuyện tự động (`P06-E01`):

1. **Vượt qua Cổng Kiểm toán Phase 2 (Audit Gate):** Khắc phục toàn bộ `1 BLOCKER` (`A-BLK-01`), `11 MAJOR` (`A-MAJ-01..06`, `B-MAJ-01..05`) và `6 MINOR` (`A-MIN-01..03`, `B-MIN-01..03`), nâng số test từ `92` lên `106/106 PASSED`.
2. **Hoàn thiện `E01-T06` (Bộ nhớ 4 thành phần, `RepetitionDetector` & `ScriptFirstBaseline`):** Tách biệt cửa sổ lịch sử phát ngắn hạn cấu hình được (`W ∈ {5, 10, 20}`) khỏi bộ theo dõi độ phủ toàn cục (`GlobalTopicCoverage`), tích hợp cập nhật nguyên tử duy nhất sau `PlaybackCompleted` ACK tại `SimulatedPlaybackHarness`, và xây dựng đường cơ sở `ScriptFirstBaseline` công bằng.
3. **Hoàn thiện `E01-T07` (`StoryPlanner`, Versioned Prompts & Đồ thị LangGraph 8 Node):** Thiết lập ranh giới DTO bản nháp không tin cậy cho LLM, hệ thống nạp/băm SHA-256 chuẩn hóa LF cho prompt tiếng Việt, đồ thị `StateGraph(AgentState)` với ngân sách viết lại `1 + K` và `17` kịch bản smoke test tích hợp đầu cuối.

### Kiểm soát Phạm vi (Strict Scope Compliance)

- **Phạm vi sửa đổi:** Toàn bộ thay đổi nằm gói gọn bên trong `experiments/sales-intelligence/autonomous-storytelling/`. Không chỉnh sửa `../knowledge-verification/` (P05), P07, `packages/`, `apps/`, root `AGENTS.md` hay cấu hình global.
- **Không thực thi ngoài phạm vi:** Chưa triển khai `E01-T08`/`E01-T09`, chưa gọi API Gemini/Ollama thật, chưa cài embedding/pgvector, chưa bật Recap Policy (`DEFERRED` sau E01), không dùng `model_copy(update=...)` trong `src/p06/`, và **chưa commit/tag/push** để chờ Tech Lead review.

---

## 2. Kết quả Audit Gate Phase 2 & Gia cố Kiến trúc (`92 -> 106 tests`)

Trước khi viết mã nguồn Phase 3, hai luồng kiểm toán độc lập (`hydrogen-scout`) đã rà soát toàn bộ Phase 1–2 và phát hiện các lỗ hổng đã được xử lý triệt để:

| Mã Finding | Mức độ | Mô tả vấn đề đã phát hiện | Biện pháp gia cố & Tệp liên quan |
| :--- | :---: | :--- | :--- |
| `A-BLK-01` | `BLOCKER` | `LangGraph` trả về `dict` thô không tự chạy `@model_validator(mode="after")`; khả năng aliasing container | Bổ sung `revalidate_instances="always"`, `_normalize_value_for_revalidation()` đệ quy `deepcopy(model_dump())` trong `validated_update()` và cổng bắt buộc `AgentState.from_graph_result()` ([state.py](../src/p06/schemas/state.py)) |
| `A-MAJ-01..05` | `MAJOR` | Xử lý chưa chặt ACK `FAILED`/`UNKNOWN`, thiếu `plan_revision`, thiếu `covered_claim_ids`, quảng bá `confirmed_topic_ids` cả khi không phải `FULL`/`PARTIAL` | Khóa 5 tầng đối chiếu `PendingTurnRecord`, giữ nguyên tiến độ khi `FAILED`/`UNKNOWN`, chỉ quảng bá topic khi `CoverageMode in {FULL, PARTIAL}` ([playback_harness.py](../src/p06/simulation/playback_harness.py), [playback_bus.py](../src/p06/adapters/mocks/playback_bus.py)) |
| `A-MAJ-06` | `MAJOR` | Kẹp ngầm thời lượng `30.000ms` có thể che giấu lỗi LLM nói quá dài | Bỏ cắt ngầm, thêm `SpeechDurationEstimate`, `estimate_raw_speech_duration_ms()`, `evaluate_speech_duration(..., enforce_limit=True)` ([virtual_clock.py](../src/p06/simulation/virtual_clock.py)) |
| `B-MAJ-01` | `MAJOR` | Cho phép `mark_rejected()` trực tiếp trên ứng viên đã `VERIFIED` | Khóa `mark_verified()` và `mark_rejected()` chỉ chuyển từ `DRAFT` ([candidate.py](../src/p06/schemas/candidate.py)) |
| `B-MAJ-02..05`, `B-MIN-01..03` | `MAJOR`/`MINOR` | Thiếu lock nạp động P05, kiểm tra `valid_from..valid_until`, mở rộng regex prompt injection, kiểm tra rò tên SKU & so sánh cảm tính `SINGLE_SKU`, lọc tenant/epoch trong fallback | Gia cố `_P05_IMPORT_LOCK` (`RLock`), cửa sổ UTC, 2-gram SKU leak, bộ lọc cô lập trong `SafeFallbackSelector`, `seeded_variants_by_schema` ([p05_knowledge_adapter.py](../src/p06/adapters/p05_knowledge_adapter.py), [fallback_selector.py](../src/p06/guardrails/fallback_selector.py)) |

> [!NOTE]
> Bộ kiểm thử hồi quy [`tests/unit/test_phase2_audit_regressions.py`](../tests/unit/test_phase2_audit_regressions.py) gồm `14` test khóa chặt toàn bộ các điểm sửa trên.

---

## 3. Kiến trúc & Triển khai `E01-T06`: Memory, Repetition & Baseline

### 3.1. Hệ thống Bộ nhớ 4 Thành phần (`src/p06/memory/`)

1. **`ShortTermPlayedHistory`** ([`played_history.py`](../src/p06/memory/played_history.py)):
   - Cho phép cấu hình cửa sổ `window_size` (`W ∈ {5, 10, 20}` theo `configs/default.yaml`, hỗ trợ `1..100`, cấm `bool`).
   - Duy trì **đồng thời** danh sách đầy đủ `_all_turns`, lát cắt gần nhất `recent_turns()` (`len <= W`), và các tập chống trùng độc lập toàn phiên (`_seen_event_ids`, `_seen_turn_ids`, `_completed_chunk_ids`) — bảo đảm khi cửa sổ trượt qua `W` lượt cũ vẫn không quên bằng chứng chống replay.
   - Hỗ trợ `with_window_size(new_w)` để quét độ nhạy biến nghiên cứu `W ∈ {5, 10, 20}` ở `E01-T08`.
2. **`GlobalTopicCoverage` & `TopicCoverageSnapshot`** ([`topic_coverage.py`](../src/p06/memory/topic_coverage.py)):
   - Khóa chặt theo `(tenant_id, session_id, plan_id, plan_revision)`.
   - Tách bạch trạng thái chưa xác nhận (`proposed_topic_ids`, `verified_topic_ids`) khỏi hoàn tất chính thức (`completed_topic_ids` chỉ nâng sau `record_playback_completed()` khi số lượt phát đạt `>= min_chunks_per_topic`).
   - Xuất `TopicCoverageSnapshot` với tử số/mẫu số minh bạch (`completed_mandatory_count / total_mandatory_count`, `mandatory_coverage_ratio`), không bao giờ mất dấu khi `ShortTermPlayedHistory` trượt cửa sổ.
3. **`SessionViewerContext`** ([`viewer_context.py`](../src/p06/memory/viewer_context.py)):
   - Placeholder tối giản cô lập theo `(tenant_id, session_id, session_epoch)` (`D11/D23`), mặc định rỗng ở `E01`, không lưu PII, không chứa logic phân loại bình luận hay recap; hỗ trợ `clear()` khi kết thúc phiên.
4. **`OptionalSemanticMemory` & `NoOpSemanticMemory`** ([`semantic_memory.py`](../src/p06/memory/semantic_memory.py)):
   - Giao diện trừu tượng (`is_enabled`, `index_played_turn`, `query_similar`, `clear`); mặc định dùng `NoOpSemanticMemory` (`is_enabled=False`, trả về `()`, không embeddings, không `pgvector`, không bịa điểm tương đồng giả).

### 3.2. Bộ phát hiện lặp Rule-Based `RepetitionDetector`

Triển khai tại [`repetition_detector.py`](../src/p06/memory/repetition_detector.py) theo đúng tinh thần `P06-OPEN-2` (*rule-based first*, thuần hàm stateless):
- Chuẩn hóa tiếng Việt `normalize_vietnamese_for_repetition()`: `Unicode NFC` -> chữ thường -> thay dấu câu Unicode bằng khoảng trắng -> gộp khoảng trắng.
- Phân loại 5 mức (`RepetitionCategory`) và khuyến nghị hành động (`RepetitionAction`):
  1. `EXACT_REPLAY` -> `SWITCH_TOPIC` (trùng `chunk_id`) hoặc `REWRITE` (trùng văn bản chuẩn hóa).
  2. `LEXICAL_DUPLICATION` -> `REWRITE` khi `Word Jaccard >= 0.65` hoặc `N-gram Jaccard (n=3) >= 0.45` (`TO VALIDATE`).
  3. `REPEATED_FACTS` -> `SWITCH_TOPIC` (cùng `topic_id`) hoặc `REWRITE` khi tỷ lệ trùng `claim_id` trên cùng `(intent, sku_id)` đạt `>= 0.80` (`TO VALIDATE`).
  4. `LEGITIMATE_CONTINUATION` -> `ALLOW` khi nói tiếp cùng `topic_id` nhưng đưa vào claim mới với mức trùng từ vựng thấp (`word_jaccard < 0.40` và `ngram_jaccard < 0.45`).
  5. `NONE` -> `ALLOW`.

### 3.3. Tích hợp Nguyên tử tại `SimulatedPlaybackHarness` & `ScriptFirstBaseline`

- **`SimulatedPlaybackHarness`** ([`playback_harness.py`](../src/p06/simulation/playback_harness.py)): Là **điểm ghi tiến độ nguyên tử duy nhất** trong PoC. Bên trong `_apply_completed_event()`, chỉ sau khi toàn bộ 5 lớp kiểm định (không phải `FAILED`/`UNKNOWN`, chống duplicate, đồng bộ context/plan_revision/thời gian/generation, provenance mô phỏng, và `StoryCheckpoint.advance_on_playback()`) thành công mới cập nhật đồng bộ `ShortTermPlayedHistory`, `GlobalTopicCoverage`, `StoryCheckpoint` và `OptionalSemanticMemory`. Bổ sung `build_agent_state()` dựng `AgentState` cho lượt kế tiếp đúng chuẩn `I-04`.
- **`ScriptFirstBaseline`** ([`script_first.py`](../src/p06/baselines/script_first.py)): Hỗ trợ cả `UPFRONT_LLM` (`UpfrontChunkDraftLLMOutput`) và `DETERMINISTIC_TALKING_POINTS` từ `StoryTopic.talking_points` + `SkuEvidenceView` (tuyệt đối không lấy transcript mẫu tham chiếu giả làm năng lực LLM). Toàn bộ chunk chuẩn bị trước phiên, không xem `played_history`, không `RepetitionDetector`/`bounded_rewrite`, vẫn bắt buộc đi qua `KnowledgeVerifierPort`, `SafeFallbackSelector` và `SimulatedPlaybackHarness` dùng chung `VirtualClock`.

---

## 4. Kiến trúc & Triển khai `E01-T07`: Planning, Prompts & LangGraph 8 Node

### 4.1. Prompts có Phiên bản, DTO Không Tin cậy, `StoryPlanner` & `ArcSequencer`

- **Versioned Prompts (`prompts/`):** [`story_planner.txt`](../prompts/story_planner.txt), [`story_generation.txt`](../prompts/story_generation.txt), [`rewrite.txt`](../prompts/rewrite.txt) đều khai báo `PROMPT_VERSION: v0.1`, khóa `active_sku_id` (`I-04`), bọc dữ liệu tri thức trong thẻ `<untrusted_knowledge_data>...</untrusted_knowledge_data>` chống prompt injection, và được mô tả tại [`prompts/README.md`](../prompts/README.md).
- **Trình nạp Prompt** ([`prompt_loader.py`](../src/p06/planning/prompt_loader.py)): Chuẩn hóa kết thúc dòng `\r\n`/`\r` -> `\n` (LF) **trước** khi tính SHA-256 (`compute_prompt_hashes()`), render một lượt qua `{{key}}` để an toàn quanh dấu ngoặc JSON `{...}` và fail-closed nếu thiếu biến.
- **Untrusted Draft DTOs** ([`draft_dtos.py`](../src/p06/planning/draft_dtos.py)): `StoryTopicDraftLLMOutput`, `StoryArcDraftLLMOutput`, `StoryPlanDraftLLMOutput`, `ChunkDraftLLMOutput` dùng `ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")` và **cấm hoàn toàn** mọi trường thẩm quyền (`tenant_id`, `approval_status`, `knowledge_version`, `verified_by_gate_decision_id`...).
- **`StoryPlanner` & `SimulatedMerchantApprovalBoundary`** ([`story_planner.py`](../src/p06/planning/story_planner.py)): Kiểm tra `SkuEvidenceView.is_eligible` cho mọi SKU ghim, khóa `knowledge_versions_by_sku`, chặn LLM bịa `fact_refs`/`allowed_claim_ids` không tồn tại trong kho, hydrate `StoryPlan(DRAFT)` và tách rạch ròi cổng phê duyệt mô phỏng `approve_plan()`.
- **`ArcSequencer`** ([`arc_sequencer.py`](../src/p06/planning/arc_sequencer.py)): Hàm thuần tất định chọn chủ đề hợp lệ cho `active_sku_id` (`I-04`), tôn trọng `checkpoint.next_topic_id`, hỗ trợ `excluded_topic_ids` khi đổi chủ đề và trả tín hiệu dừng sạch (`should_terminate=True`).

### 4.2. Đồ thị LangGraph 8 Node (`src/p06/agent/`)

```text
START
  │
  ▼
load_context ──(thiếu SKU/stale TOCTOU/ineligible)──────────────┐
  │ (ok)                                                         │
  ▼                                                              ▼
plan_chunk ──(hết topic -> should_terminate)───────────────► finalize_candidate ──► END
  │ (chọn topic)                                                 ▲
  ▼                                                              │
draft_chunk (lần 0) ──(Timeout/Transport/Hết retry)──────► safe_fallback
  │             └──(Malformed/Schema/Quá 8s & còn retry)─► bounded_rewrite (1..K)
  ▼                                                              │
check_repetition ──(REWRITE/SWITCH_TOPIC)────────────────────────┤
  │ (ALLOW)                                                      ▲
  ▼                                                              │
verify_p05 ──(VERIFIED)──► finalize_candidate                    │
  │ (REJECTED) ──(retryable & còn retry)─────────────────────────┘
  └──(non-retryable TOCTOU/rights/OCOP hoặc hết retry)───► safe_fallback
```

- Mọi phụ thuộc runtime (`LLMProvider`, `KnowledgeVerifierPort`, `RepetitionDetector`, `VirtualClock`) và scratchpad từng lượt (`TurnExecutionContext`) nằm ngoài `AgentState` tại [`deps.py`](../src/p06/agent/deps.py).
- Mỗi node đều xác thực bước chuyển qua `validate_node_updates()` -> `state.validated_update()` ([`_common.py`](../src/p06/agent/nodes/_common.py)).
- Cửa ra [`run_storytelling_turn()`](../src/p06/agent/graph.py) bắt buộc tái kiểm định trạng thái thô bằng `AgentState.from_graph_result()` (`[A-BLK-01]`) và đồ thị **dừng trước phát sóng** (không chạm `played_history`, `completed_topic_ids`, `story_checkpoint`).

---

## 5. Vết Chạy Đầu Cuối Thực Tế (Captured Trace — Tier 1 `MockLLMProvider`)

Đoạn log dưới đây được ghi nhận trực tiếp khi chạy luồng khép kín trên fixture `product_education_10m` (`SKU-HONEY-01`, `MockLLMProvider`, `P05KnowledgeAdapter`, `MockPlaybackAckBus`, `SimulatedPlaybackHarness`) với kịch bản lần 0 báo sai giá (`99.000đ` -> bị P05 chặn) và lần 1 sửa đúng giá (`159.000đ` -> đạt P05 + nhận ACK `COMPLETED`):

```json
{
  "node_trace": [
    "load_context",
    "plan_chunk",
    "draft_chunk",
    "check_repetition",
    "verify_p05",
    "bounded_rewrite",
    "check_repetition",
    "verify_p05",
    "finalize_candidate"
  ],
  "retries_used": 1,
  "outcome": "VERIFIED_READY",
  "gate_decision_id": "p05-allow-cand-trace-turn-01-r1",
  "chunk_id": "trace-turn-01-topic-edu-honey-usage-c0-r1",
  "playback_status": "APPLIED",
  "playback_event_id": "sim-pb-0001",
  "actual_duration_ms": 7308,
  "completed_topics": [
    "topic-edu-honey-usage"
  ],
  "mandatory_ratio": "1/6",
  "checkpoint_next_topic": "topic-edu-honey-quality",
  "checkpoint_last_chunk": "trace-turn-01-topic-edu-honey-usage-c0-r1",
  "prompt_hashes": {
    "story_generation.txt": "5a9c6849dda4bb71aceb4333bbb41a03c71b766d00d24680e5dff573f70c0d71",
    "rewrite.txt": "5b9a036832e08bbfaae351b36fd943d8a5d58a78de871b5140d56f778774bfed"
  }
}
```

**Quan sát then chốt từ trace:** Bản viết lại ở `bounded_rewrite` đã đi vòng bắt buộc qua cả `check_repetition` lẫn `verify_p05`; `actual_duration_ms = 7308ms` (`7.308s <= 8.0s`); chỉ sau `apply_ack(APPLIED)` thì `topic-edu-honey-usage` mới vào `completed_topics` (`1/6`) và `checkpoint_next_topic` mới tiến sang `topic-edu-honey-quality`.

---

## 6. Giải thích Kiến thức Kỹ thuật & Mã nguồn Bằng Tiếng Việt

### 6.1. LangGraph `StateGraph(AgentState)` & Cổng Bảo vệ `from_graph_result()`

Trong LangGraph, mỗi node nhận snapshot hiện tại của state và chỉ trả về `dict` các trường muốn cập nhật. Điểm bẫy thực tế đã phát hiện ở Audit Gate (`A-BLK-01`) là `StateGraph(AgentState).invoke()` gộp cập nhật thành `dict` và **không tự gọi lại** `@model_validator(mode="after")` trên trạng thái kết thúc, đồng thời việc truyền trực tiếp object/list lồng nhau có thể làm bỏ qua kiểm định hoặc chia sẻ tham chiếu. Do đó P06 khóa chặt ở **hai lớp**:
- Bên trong mỗi node: gọi `state.validated_update(**updates)` để bắt lỗi liên trường ngay tại bước phát sinh.
- Bên ngoài `compiled_graph.invoke()`: gọi `AgentState.from_graph_result(raw_result)` (dùng `_normalize_value_for_revalidation` chuyển đệ quy `BaseModel` -> `deepcopy(model_dump())` rồi `model_validate()`) để bảo đảm trạng thái ra khỏi đồ thị tuyệt đối hợp lệ.

### 6.2. Toán học Word Jaccard & N-gram Jaccard Trong `RepetitionDetector`

Gọi $A, B$ là tập đơn vị trích xuất từ câu ứng viên và một lượt đã phát sau chuẩn hóa `normalize_vietnamese_for_repetition()`:

$$\text{Jaccard}(A, B) = \frac{|A \cap B|}{|A \cup B|}$$

- **Word Jaccard** (trên tập từ đơn): Bắt nhanh việc lặp lại phần lớn từ vựng. Ví dụ:
  - $T_1 = \text{"mật ong hoa cà phê đắk lắk nguyên chất 500ml"}$ (10 từ)
  - $T_2 = \text{"chai mật ong hoa cà phê đắk lắk 500ml nguyên chất"}$ (11 từ, thêm `"chai"`)
  - $|A \cap B| = 10, |A \cup B| = 11 \implies \text{Word Jaccard} = 10/11 \approx 0.909 \ge 0.65$ (`TO VALIDATE`) $\implies$ bắt `LEXICAL_DUPLICATION`.
- **N-gram Jaccard ($n = 3$)** (trên tập cụm 3 từ liên tiếp — *trigram shingles*): Bắt các câu đảo vế hoặc chêm từ đệm nhưng vẫn giữ nguyên cụm từ dài giống hệt (ví dụ `"mật ong hoa"`, `"ong hoa cà"`, `"hoa cà phê"`). Với câu quá ngắn ($0 < \text{số từ} < n$), hàm `_extract_word_shingles()` giữ nguyên tuple cả câu làm 1 shingle duy nhất thay vì trả tập rỗng, tránh `ZeroDivisionError` và tránh làm mất khớp câu ngắn giống nhau.
- **Fact Overlap & Giới hạn Paraphrase:** Nếu hai câu diễn đạt hơi khác nhưng cùng `(intent, sku_id)` và tỷ lệ trùng `claim_id` đạt `|cand ∩ played| / |cand| >= 0.80` (`TO VALIDATE`), tầng 3 sẽ bắt `REPEATED_FACTS`. Tuy nhiên nếu câu được paraphrase hoàn toàn khác từ và không gắn `claim_id`, rule-based bề mặt sẽ không phát hiện được — đây chính là lý do `P06-OPEN-2` giữ nhánh nghiên cứu `OptionalSemanticMemory`.

### 6.3. Tại sao Tách Cửa sổ Trượt `ShortTermPlayedHistory` Khỏi `GlobalTopicCoverage`?

Khi phiên live kéo dài 10–30 phút (vượt quá $W \in \{5, 10, 20\}$ chunk gần nhất), nếu chỉ dùng `len(played_history)` hoặc lưu trạng thái đã phủ ngay trong cửa sổ trượt thì các topic nói ở đầu phiên sẽ "trôi" khỏi cửa sổ và bị hệ thống tưởng nhầm là chưa nói (gây lặp toàn arc hoặc giảm sai coverage). Việc tách `GlobalTopicCoverage` (đếm tích lũy toàn phiên độc lập với `W`) và giữ các tập dedup `_seen_event_ids` / `_completed_chunk_ids` trong `ShortTermPlayedHistory` giải quyết triệt để vấn đề này trong khi vẫn giữ prompt gọn nhẹ ở `W` lượt gần nhất.

### 6.4. Ngân sách Viết lại Có Giới hạn `1 + K` (`Bounded Rewrite`)

Để tránh vòng lặp sửa lỗi vô tận làm tăng độ trễ và chi phí token trong livestream:
- Lần gọi đầu tiên (`draft_chunk`) mang `rewrite_attempt = 0` (`retries_used = 0`).
- Mỗi lần bị chặn bởi lỗi có thể sửa được (`MalformedJsonOutputError`, `SchemaValidationOutputError`, vượt `max_chunk_duration_sec`, `check_repetition`, hoặc lỗi diễn đạt P05), node `bounded_rewrite` tăng đơn điệu `retries_used += 1` (tối đa `K` lần, tổng số lần gọi LLM tối đa là $1 + K$) và luôn quay lại kiểm tra `check_repetition -> verify_p05`.
- Lỗi hệ thống/TOCTOU không thể tự sửa bằng viết lại câu chữ (`ProviderTimeoutError`, `STALE_KNOWLEDGE_VERSION`, `SKU_NOT_ELIGIBLE`, `RIGHTS_INVALID`...) được phân loại non-retryable để rẽ thẳng sang `safe_fallback`, không đốt ngân sách rewrite.

### 6.5. Thiết kế Công bằng Cho `ScriptFirstBaseline`

Để so sánh khoa học với LangGraph Agent trong `P06-E01` mà không thiên vị: `ScriptFirstBaseline` vẫn được đọc `StoryPlan` `APPROVED`, tri thức sống `SkuEvidenceView`, vẫn bị ép đi qua Cổng `P05KnowledgeAdapter`, `SafeFallbackSelector`, `VirtualClock` và `SimulatedPlaybackHarness` giống hệt hệ thống chính; điểm khác biệt duy nhất là kịch bản được tạo trước toàn bộ từ đầu phiên, không đọc `played_history` động, không có `RepetitionDetector` và không có `bounded_rewrite` (`rewrite_attempt=0`).

---

## 7. Kết quả Kiểm thử Tự động & Xác minh Tái lập

Toàn bộ lệnh được chạy trực tiếp bằng `.venv` của repository **sau lần chỉnh sửa cuối cùng**:

| Kiểm tra | Lệnh thực thi | Kết quả quan sát |
| :--- | :--- | :--- |
| Thu thập test | `.\.venv\Scripts\python.exe -m pytest experiments/sales-intelligence/autonomous-storytelling/tests --collect-only -q` | `189 tests collected` (`0` lỗi import/collection) |
| Chạy toàn bộ suite | `.\.venv\Scripts\python.exe -m pytest experiments/sales-intelligence/autonomous-storytelling/tests -v` | `189 passed, 0 failed, 0 skipped` |
| Kiểm tra tất định smoke 17 kịch bản (chạy 2 lần) | `.\.venv\Scripts\python.exe -m pytest experiments/sales-intelligence/autonomous-storytelling/tests/integration/test_e01_agent_smoke.py -q` (×2) | Lần 1 & Lần 2 đều pass `18/18` test cases (tương ứng 17 kịch bản kèm parametrize `FAILED`/`UNKNOWN`) |
| Kiểm tra dependency `.venv` | `.\.venv\Scripts\python.exe -m pip check` | `No broken requirements found.` |
| Quét cấm `model_copy(update=...)` & kích thước `AGENTS.md` | Kiểm tra tĩnh trên `src/p06/` và độ dài byte `AGENTS.md` | `0` lời gọi runtime `model_copy(`; `AGENTS.md` `< 24,000` bytes |

Phân rã `189` test cases (tất cả chạy offline với `MockLLMProvider` ở Phase 3):
- `tests/unit/` (Phase 1+2 + Audit Gate): `106` tests.
- `tests/unit/test_memory_and_repetition.py`: `15` tests.
- `tests/unit/test_script_first_baseline.py`: `11` tests.
- `tests/unit/test_planning_and_prompts.py`: `27` tests.
- `tests/unit/test_agent_graph.py`: `12` tests.
- `tests/integration/test_e01_agent_smoke.py`: `18` test items (bao phủ đủ 17 kịch bản integration smoke).

---

## 8. Tổng hợp Review Độc lập & Khắc phục Phát hiện

Reviewer độc lập (`hydrogen-scout`, chỉ-đọc) đã rà soát toàn bộ thay đổi Phase 3 và xác nhận:
- **`0 BLOCKER`**, **`0 MAJOR`** trên cả 7 bất biến cốt lõi (không dùng `model_copy(update=...)`, cô lập untrusted Draft DTOs, ranh giới `AgentState.from_graph_result()`, trần `1 + K`, commit nguyên tử chỉ sau ACK, đúng phạm vi thư mục, đầy đủ docstring tiếng Việt).
- **`3 MINOR` không chặn tiến độ**, trong đó `2` điểm đã được xử lý ngay sau review:
  1. `playback_harness.py`: Chuyển lời gọi `self._semantic_memory.index_played_turn(summary)` xuống **sau** `self._checkpoint = new_checkpoint` để bảo đảm ngay cả khi có custom semantic memory ngoài lỗi, trạng thái checkpoint và bộ nhớ cốt lõi vẫn giữ nguyên tính nhất quán nguyên tử.
  2. `script_first.py`: Đồng bộ bộ lọc `_select_eligible_topics` với `ArcSequencer._is_topic_eligible_for_sku` để xử lý nhất quán chủ đề chung (`arc.sku_id is None and topic.sku_id is None`).
  3. *(Ghi nhận bảo toàn hợp đồng `AgentState`)* `check_repetition.py` đối chiếu trên cửa sổ `W` `state.played_history` theo đúng thiết kế; lịch sử toàn phiên của `ShortTermPlayedHistory.completed_chunk_ids` vẫn nằm tại harness ngoài `AgentState`.

---

## 9. Checklist Definition of Done & Giới hạn Hiện tại (Trung thực)

| Tiêu chí DoD Phase 3 | Trạng thái | Ghi chú trung thực |
| :--- | :---: | :--- |
| Audit Gate Phase 2 đạt 100% trước khi viết Phase 3 | `DONE` | `106/106` pass sau sửa `A-BLK-01`, `A-MAJ-01..06`, `B-MAJ-01..05` |
| Bộ nhớ 4 thành phần + `RepetitionDetector` + `ScriptFirstBaseline` (`E01-T06`) | `DONE` | Đã kiểm chứng đơn vị và tích hợp vào `SimulatedPlaybackHarness` |
| `StoryPlanner` + Prompts SHA-256 + Đồ thị 8 node LangGraph (`E01-T07`) | `DONE` | Bao phủ đủ 17 kịch bản smoke tích hợp chạy lại tất định |
| Tài liệu báo cáo & docstring tiếng Việt chuẩn giáo dục | `DONE` | Đủ 5 câu hỏi đầu file, WHY-only comment, báo cáo này & cập nhật docs |
| Đánh giá chất lượng tiếng Việt, chi phí, latency LLM thật (`Ollama`/`Gemini`) | `NOT STARTED` | Toàn bộ test Phase 3 dùng `MockLLMProvider`; **tuyệt đối không** xem đây là bằng chứng chất lượng LLM |
| Khóa tối ưu ngưỡng `RepetitionConfig` & `W ∈ {5, 10, 20}` | `TO VALIDATE` | Các ngưỡng hiện tại chỉ là baseline khởi tạo, chờ `E01-T08` + human eval |
| Rà soát giới hạn kế thừa từ P05 `PublicationGate` | `KNOWN LIMIT` | P05 kiểm tra tồn tại `cited_evidence_ids`, giá số và từ cấm, chưa kiểm chứng suy luận ngữ nghĩa (*semantic entailment*) giữa text và chunk; giá viết bằng chữ chưa qua `extract_prices_vnd`; `SHOP_WIDE_POLICY` tiếp tục fail-closed |
| Phê duyệt Owner / Reviewer độc lập (`P06-OPEN-6`) | `PENDING ASSIGNMENT` | Chưa có ai ký duyệt `VALIDATED` |

---

## 10. Tóm tắt Thay đổi Tập tin & Trạng thái Git

Toàn bộ thay đổi đều nằm trong `experiments/sales-intelligence/autonomous-storytelling/`, trên nhánh `research/p06-autonomous-storytelling` (tính từ checkpoint `p06-checkpoint-03-infrastructure` = `a2805d5`):
- **Thư mục mới / mở rộng trong `src/p06/`:** `memory/`, `baselines/`, `planning/`, `agent/` (gồm `nodes/`), và mở rộng `simulation/playback_harness.py` cùng các tệp Phase 2 hardening (`schemas/`, `adapters/`, `guardrails/`, `providers/`, `simulation/`).
- **Prompts mới:** `prompts/{story_planner.txt, story_generation.txt, rewrite.txt}` + `prompts/README.md`.
- **Kiểm thử mới:** `tests/unit/{test_phase2_audit_regressions.py, test_memory_and_repetition.py, test_script_first_baseline.py, test_planning_and_prompts.py, test_agent_graph.py}` và `tests/integration/test_e01_agent_smoke.py`.
- **Tài liệu cập nhật:** `AGENTS.md`, `README.md`, `docs/README.md`, chỉnh lỗi nhỏ tại `docs/03-...md`, `docs/04-...md` và tạo báo cáo này (`docs/05-...md`).
- **Git safety:** **Chưa** chạy `git commit`, `git tag`, `git merge` hay `git push` để giữ toàn quyền kiểm soát cho Tech Lead.

---

## 11. Rủi ro Mở & Giả định Cần Theo dõi

1. **Giới hạn ngữ nghĩa của `RepetitionDetector`:** Phương pháp rule-based Jaccard/N-gram hiện tại dựa trên trùng bề mặt từ vựng và `claim_id`; nếu LLM diễn đạt lại hoàn toàn bằng từ đồng nghĩa mà không gán `covered_claim_ids`, độ lặp có thể không bị bắt (`P06-OPEN-2`).
2. **Định dạng JSON đầu ra trên model nhỏ (`Ollama Qwen3 1.7B/4B`):** Chưa kiểm chứng tỷ lệ JSON parse thành công của `StoryPlanDraftLLMOutput` và `ChunkDraftLLMOutput` trên CPU cục bộ (`TO VALIDATE` ở bước kế tiếp).
3. **Ước lượng thời lượng tiếng nói (~2.6 từ/giây):** `VirtualClock` dùng tốc độ đọc trung bình giả định để mô phỏng trước khi có P02 TTS thật; thời lượng audio thực tế cần đối chiếu lại khi tích hợp TTS.

---

## 12. Đề xuất Bước Tiếp theo (`E01-T08`)

1. Sau khi Tech Lead review Phase 3 và tạo Git checkpoint mới (ví dụ `p06-checkpoint-04-agent-core`), triển khai **`E01-T08` — Evaluation Metrics & CLI Experiment Runner**:
   - Xây dựng `src/p06/evaluation/metrics/` (coverage ratio, lexical/n-gram repetition rate, exact replay count, P05 rejection & fallback rate, token/latency provenance tách biệt theo `ProviderTier`).
   - Xây dựng `experiments/p06_e01_no_comments/run_e01.py` chạy sweep `W ∈ {5, 10, 20}` đối chiếu `ScriptFirstBaseline` với LangGraph Agent, xuất `runs/p06_e01/<run_id>/{manifest.json, logs/, failures/}`.
2. Thực hiện **Tier 2 local CPU smoke test** với `OllamaLocalProvider` để đo tỷ lệ tuân thủ JSON schema trước khi chuyển sang bước **Tier 3 Gemini API** (`E01-T09` + Human Evaluation Pilot Calibration).
