# Báo cáo Phase 4 — Hệ thống Đánh giá & Experiment Runner Tái lập (`E01-T08`)

**Module:** `P06 — Sales Intelligence & Autonomous Storytelling`  
**Thí nghiệm mục tiêu:** `P06-E01` — *Storytelling Without Comments*  
**Nhiệm vụ hoàn thành:** `E01-T08` (Evaluation Metrics & Reproducible Experiment Runner — **Offline Tier 1 Mock ONLY**)  
**Nhánh Git:** `research/p06-autonomous-storytelling` · **Base Checkpoint Tag:** `p06-checkpoint-04-agent-core` (`272a35b`)  
**Trạng thái hiện tại:** `IN RESEARCH / TO VALIDATE` *(chưa `VALIDATED`; chưa chạy `E01-T09` formal benchmark)*  
**Ngày hoàn thành:** `2026-11-26` · **Owner / Reviewer độc lập:** `PENDING ASSIGNMENT`

> [!IMPORTANT]
> **Nguyên tắc trung thực khoa học (Honest Provenance):** Toàn bộ kết quả chạy trong Phase 4 đều sử dụng **`MockLLMProvider` (`unit_test`)** và dữ liệu synthetic `p06-mock-v0.1`. Các lượt chạy này **chỉ kiểm chứng luồng điều khiển, ràng buộc trạng thái, tính toán chỉ số và khả năng tái lập** — **KHÔNG** phải bằng chứng cho chất lượng kể chuyện tiếng Việt, độ tự nhiên, tính thuyết phục, hay năng lực thực tế của `Ollama`/`Gemini`. Các lượt chạy tiền-sửa-lỗi trước khi vá `BUG-A..C` được giữ nguyên trên đĩa để truy vết lịch sử và được đánh dấu **`SUPERSEDED`** (không dùng làm bằng chứng đánh giá cuối cùng).

---

## 1. Executive Summary

Trong Phase 4 (`E01-T08`), hệ thống **đo lường đánh giá 5 trục (`p06.evaluation`)** và **Experiment Runner tái lập (`p06.runner` + CLI `run_e01.py`)** đã được triển khai, kiểm toán đa tác tử, vá toàn bộ `8` findings từ Independent Review (`BUG-A`, `BUG-B`, `BUG-C`, `NEW-01..05`), chạy lại thực nghiệm ngoại tuyến hậu-sửa-lỗi và xác minh bởi **`249/249` pytest tests pass** (`189` tests Phase 3 + `60` tests Phase 4, `0 failed`, `0 skipped`, `pip check` sạch).

Các kết quả chính đạt được trong phạm vi `E01-T08`:
- **Khắc phục triệt để các điểm mở từ Phase 3 Audit (`F-01..F-12`, `AUD-01..AUD-10`):** Bổ sung `StoryCheckpoint.with_active_sku()`, `SimulatedPlaybackHarness.switch_active_sku()` chuyển mượt giữa 3 SKU trong một phiên, cô lập lỗi `semantic_memory.index_played_turn()`, hoàn chỉnh dấu vết `draft_attempts` / `repetition_checks` / `p05_decisions` / `non_retryable_failure`, xóa hint trong `safe_fallback`, bổ sung parity `max_chunk_duration_sec=8.0` và SKU-scoped `planned_chunk_id`/`candidate_id` cho `ScriptFirstBaseline`.
- **Khung Đánh giá 5 Trục + Chống Đánh giá Vòng tròn (`src/p06/evaluation/`):** Gồm `Coverage`, `Repetition` (đo trên **toàn transcript** độc lập với cửa sổ agent `W`), `Safety` (gắn với nhãn chuẩn độc lập `GoldFactualLabel`, không lấy `P05 ALLOW` làm ground truth), `Reliability` và `Performance`, kèm chính sách dữ liệu thiếu nghiêm ngặt (`None` + `NOT_EVALUATED`/`NOT_APPLICABLE`/`INVALID`, không điền `0` giả).
- **Experiment Runner & Hệ thống 10 Artifact Tái lập (`src/p06/runner/` & `experiments/p06_e01_no_comments/run_e01.py`):** Hỗ trợ đối chiếu công bằng `script_first_deterministic`, `script_first_upfront_llm` (không quét `W`), và `langgraph_structured_story` (`W ∈ {5, 10, 20}`), khóa cứng **Offline Guard** chặn `ollama`/`gemini` khi chưa có `--allow-live-provider`, lưu bất biến 10 tệp mỗi lượt và xuất **phiếu chấm mù 6 tiêu chí (`human_eval_rubric_v0.1.md`)** không rò rỉ danh tính phương pháp hay `W`.
- **Phạm vi chưa thực hiện (thuộc `E01-T09`):** Chưa chạy `Ollama` CPU smoke test, chưa gọi `Gemini API` thật, chưa triển khai formal benchmark `E01-T09`, chưa chấm người thật và **không** nâng trạng thái P06/E01 lên `VALIDATED`.

---

## 2. Multi-Agent Execution Report

Phase 4 được điều phối theo quy trình đa tác tử chuẩn xác minh độc lập với phạm vi sở hữu tệp tách bạch:

| Đợt / Vai trò | Conversation ID / Agent Type | Phạm vi được giao | Kết quả & Bằng chứng chính |
| :--- | :--- | :--- | :--- |
| **Wave A — Scout A** *(Agent, Memory & Simulation Auditor)* | `c02f1795-df6a-4f97-a7a1-fd851d9ddc49` (`hydrogen-scout`, read-only) | `agent/`, `memory/`, `planning/`, `simulation/`, `schemas/`, tests Phase 3 | Rà soát đa lượt, ACK integrity, exact replay ngoài `W`, chuyển 3 SKU -> phát hiện `12` findings **`F-01..F-12`** (`safe_fallback` không xóa hint, thiếu `switch_active_sku`, `draft_attempts` trace chưa lưu đủ, v.v.). |
| **Wave A — Scout B** *(Research Methodology & Evaluation Auditor)* | `34ff5d71-0fed-4612-a17d-2e2af606a916` (`hydrogen-scout`, read-only) | `research/`, `data/`, `baselines/`, `providers/`, `evaluation/`, `configs/` | Phát hiện `10` findings **`AUD-01..AUD-10`** (năng lực 6/9-topic của `e01_story_plans.json` so với mục tiêu 10–30m, parity `max_chunk_duration_sec` ở baseline, SKU-scoped chunk ID, `seeded_variants_by_schema` factory). |
| **Wave C — Executor A** *(Evaluation Metrics Engineer)* | `5d1b7dc2-ed85-40e8-9136-12cb67c9101f` (`hydrogen-executor`) | `src/p06/evaluation/*`, `test_evaluation_metrics.py`, `test_e01_factual_verification_limits.py` | Triển khai 5 trục metric, `evaluator.py`, `comparison.py`, `human_eval.py` và 26 unit/contract tests (`17` metrics + `9` factual verification limits). |
| **Wave C — Executor B** *(Experiment Runner Engineer)* | `7f264097-2017-438d-98da-9f7fcf9bf422` (`hydrogen-executor`) | `src/p06/runner/*`, `experiments/p06_e01_no_comments/run_e01.py`, `test_experiment_runner.py` | Triển khai config, Offline Guard, mock fixtures tách schema, evidence collector, manifest/artifacts, session runner, sweep và CLI + `18` unit tests ban đầu. |
| **Wave E — Reviewer 1** *(Bị gián đoạn quota)* | `a95b413c-0ae5-409f-a66a-79bb0e007a79` (`hydrogen-scout`) | Độc lập rà soát toàn bộ Phase 4 | Dừng giữa chừng với lỗi `RESOURCE_EXHAUSTED (HTTP 429)` trước khi hoàn tất review. Người dùng chuyển tài khoản để tiếp tục phiên. |
| **Wave E — Reviewer 2** *(Independent Phase 4 Reviewer)* | `f2833585-dad0-42fd-a58b-2e8d46cf4ce3` (`hydrogen-scout`, read-only) | Toàn bộ Phase 4 diff, tests, dry-run artifacts & kiểm tra 3 bug nghi ngờ | Xác nhận **`CHANGES_REQUIRED`**: khẳng định **`BUG-A`, `BUG-B`, `BUG-C`** (BLOCKER) và phát hiện thêm **`5` findings mới (`NEW-01` MAJOR; `NEW-02..05` MINOR)**. |
| **Remediation & Re-verification** *(Main Agent)* | Main Execution Thread | Vá toàn bộ 8 findings, viết 8 regression tests, chạy lại 4 dry-runs & full test suite | Đã vá `100%` 8/8 findings, bổ sung test hồi quy, tạo bộ runs hậu-sửa-lỗi mới và xác minh `249/249 passed`. |

### Tóm tắt 8 Findings từ Independent Review & Cách đã xử lý

1. **`BUG-A` (BLOCKER — Over-redaction `metric_provenance.token_usage`):** `sanitize_mapping_for_artifact()` kiểm tra chuỗi con `"token"` trong `SENSITIVE_SAMPLING_KEYS` khiến `manifest["metric_provenance"]["token_usage"]` bị che thành `"[REDACTED]"` thay vì `"SIMULATED"`/`"UNAVAILABLE"`, đồng thời `"bearer"` chưa nằm trong danh sách nhạy cảm.  
   -> **Đã sửa:** Thêm `"bearer"` vào `SENSITIVE_SAMPLING_KEYS` (`src/p06/providers/base.py`); mở rộng `_SAFE_TOKEN_CONFIG_KEYS` (khớp chính xác tên khóa viết thường trong `src/p06/runner/config.py`) cho các trường đếm/nguồn token phi bí mật (`token_usage`, `token_usage_source`, `input_tokens`, `output_tokens`, `total_tokens`, `wasted_tokens`, `wasted_input_tokens`, `wasted_output_tokens`, `max_tokens`, `max_output_tokens`, `max_input_tokens`, `context_tokens`) trong khi mọi khóa bí mật (`access_token`, `auth_token`, `bearer`, `api_key`, `GEMINI_API_KEY`, `secret`, `password`, `authorization`) vẫn bị thay thế `"[REDACTED]"`.
2. **`BUG-B` (BLOCKER — Trộn Wall-Clock `started_at_utc` với `VirtualClock`):** `compute_coverage_metrics()` lấy `completion_event.occurred_at_utc` (mốc `VirtualClock` 12:00:00Z) trừ `manifest["started_at_utc"]` (wall-clock), làm `time_to_complete_mandatory_topics_sec` nhảy lên ~`11,525–12,018s` thay vì ~`36.9s`.  
   -> **Đã sửa:** Lưu `virtual_clock_start_utc` vào `manifest["simulator_assumptions"]` (`session_runner.py`, `manifest.py`); cập nhật `coverage.py` chỉ trừ trên trục `VirtualClock` (hoặc fallback về `cumulative_played_duration_sec`), **không bao giờ** dùng `started_at_utc`.
3. **`BUG-C` (BLOCKER — Đếm nhầm lượt kết thúc biên SKU sạch vào `safe_abort_count` & `invocation_latency`):** Mỗi lần LangGraph hoàn tất 1 SKU, node cuối phát sinh 1 trace biên sạch (`should_terminate=True`, `non_retryable_failure=None`, `draft_attempts=()`, `p05_decisions=()`, không qua `safe_fallback`), khiến kịch bản 3 SKU tạo ra `9` traces (`6` lượt nói + `3` lượt biên) và `safe_abort_count = 3` (`33.3%`).  
   -> **Đã sửa:** Tạo hàm `is_clean_termination_boundary_trace()` trong `src/p06/evaluation/models.py` (tránh circular import giữa `reliability.py` và `performance.py`), lọc bỏ lượt biên sạch khỏi mẫu số `turns_attempted`, `safe_abort_count`, `safe_abort_rate`, `rewrite_rate`, `fallback_rate`, `attempts_per_turn_*` và `invocation_latency_p50_ms/p95_ms`, đồng thời ghi `termination_boundary_turns_excluded` vào `metadata`. Lượt `SAFE_ABORT_NO_CANDIDATE` thực sự (qua `safe_fallback` hoặc `non_retryable_failure`) vẫn bị đếm nguyên vẹn.
4. **`NEW-01` (MAJOR — Guard giữa SKU của `ScriptFirstBaseline`):** `_run_script_first_loop` chạy hết mọi topic của cả SKU rồi mới check `max_turns` / `target_duration_sec` / `max_consecutive_aborts`, gây lệch giữa `VirtualClock` và transcript khi dừng giữa chừng.  
   -> **Đã sửa:** Thêm tham số `max_turns`, `target_duration_sec`, `max_consecutive_aborts`, `initial_consecutive_aborts` vào `ScriptFirstBaseline.run_session()` để kiểm tra điều kiện dừng **trước khi** tạo và phát từng lượt trong vòng lặp.
5. **`NEW-02` (MINOR — Trùng `candidate_id` giữa các SKU trong `ScriptFirstBaseline`):** `candidate_id` thiếu `{active_sku_id}`, khiến 3 SKU đều sinh `-000`, `-001`.  
   -> **Đã sửa:** Đưa `{active_sku_id}` vào `candidate_id` (`cand-baseline-{plan_id}-r{rev}-{active_sku_id}-{seq:03d}`).
6. **`NEW-03` (MINOR — Lệch ghép telemetry khi `UPFRONT_LLM` vượt `max_chunk_duration_sec`):** Vòng lặp khớp `telemetry_records` bỏ qua lượt lỗi `OVER_MAX_DURATION_SEC`, dồn telemetry sang lượt sau.  
   -> **Đã sửa:** Ghép theo vị trí `1-1` với `session_result.turns` và đọc `discarded_candidates[turn_id]["generation_error"]` để gắn đúng `turn_id`, `is_wasted=True` và `error_type="OVER_MAX_DURATION_SEC"`.
7. **`NEW-04` (MINOR — Sweep nhiều kịch bản gây `compatible=False` toàn cục):** `run_e01_sweep()` với >1 kịch bản gộp chung toàn bộ vào 1 `compare_runs()`.  
   -> **Đã sửa:** Khi `len(scenarios) > 1`, giữ báo cáo tổng hợp và xuất thêm `comparison_{scenario}.{json,csv,md}` cho từng kịch bản (`compatible=True` nội bộ mỗi kịch bản).
8. **`NEW-05` (MINOR — Fallback `pricing` và `attempts_per_turn_*` ở chế độ tất định):** (1) `performance.py` tìm `manifest.get("pricing")` nhưng `manifest.py` lồng dưới `provider_config`; (2) `script_first_deterministic` báo `generation_attempts = 0` nhưng `attempts_per_turn_mean = 1.0`.  
   -> **Đã sửa:** Hoist `pricing` ra cấp gốc `manifest` (và thêm fallback đọc từ `provider_config["pricing"]` trong `performance.py`); trả `MetricStatus.NOT_APPLICABLE` (`value=None`) cho `attempts_per_turn_*` khi `method == "script_first_deterministic"` và `generation_attempts == 0`.

---

## 3. Phase 3 Focused Audit Summary (`F-01..F-12`, `AUD-01..AUD-10`)

Trước khi xây dựng hệ thống đánh giá, Wave A đã kiểm toán toàn diện mã nguồn Phase 3 và sửa dứt điểm các sai lệch quan trọng ngay trong Step 1 (xác nhận bởi `tests/unit/test_phase3_audit_regressions.py`, `5/5 passed`):

- **Chuyển đổi Active SKU an toàn giữa 3 SKU (`I-04`, `I-06`):** Bổ sung `StoryCheckpoint.with_active_sku()` (bảo toàn `last_completed_chunk_id`, `last_playback_event_id`) và `SimulatedPlaybackHarness.switch_active_sku()` (từ chối chuyển khi còn lượt pending, SKU không nằm trong `pinned_sku_ids`, hoặc timestamp lùi; giữ nguyên toàn bộ `played_history`, `completed_topic_ids` và `dedup` của SKU trước).
- **Cô lập lỗi `OptionalSemanticMemory` hậu-commit:** Bao bọc `self._semantic_memory.index_played_turn(summary)` trong `try/except Exception` sau khi ACK đã commit thành công, lưu lỗi vào `PlaybackApplyResult.semantic_index_error` và thuộc tính `harness.semantic_index_errors` để không làm sập phiên phát sóng.
- **Bảo toàn hint & trace chi tiết LangGraph:** `safe_fallback.py` xóa sạch `ctx.next_topic_id_hint = None` và `ctx.next_arc_id_hint = None` để không đẩy nhầm con trỏ chủ đề sau fallback; `TurnExecutionContext` và `AgentTurnResult` bổ sung `DraftAttemptTrace`, `RepetitionAttemptTrace`, `P05AttemptTrace`, `non_retryable_failure`, `excluded_topic_ids` làm nguồn sự thật cho `graph_trace.jsonl`.
- **Công bằng cho `ScriptFirstBaseline` (`AUD-02`, `AUD-04`, `AUD-06`):** Đồng bộ `max_chunk_duration_sec` (runner khóa `8.0s` cho mọi phương pháp), gắn `{active_sku_id}` vào `planned_chunk_id` và `candidate_id`, bổ sung prompt version/SHA-256 và chuyển `seeded_variants_by_schema` qua `ProviderFactory` riêng cho `MockLLMProvider`.

> [!NOTE]
> **Giới hạn dung lượng kịch bản tham chiếu đã được xác nhận (`F-01` / `AUD-01` — giữ nguyên `data/`):** Các kế hoạch trong `data/story_plans/e01_story_plans.json` hiện có **6 chủ đề** (`3 SKU × 2`) cho `product_education_10m` / `brand_storytelling_10m` và **9 chủ đề** (`3 SKU × 3`) cho `sales_presentation_30m`. Với giới hạn `max_chunk_duration_sec = 8.0s` và mỗi topic sinh 1 chunk (~`6.15s`), các kịch bản 10 phút hoàn tất hợp lệ sau `36.924s–39.228s` so với `600s` (`duration_fulfillment ≈ 0.0615–0.0654`), còn kịch bản 30 phút 9 chủ đề hoàn tất sau `~55.386s` so với `1800s` (`duration_fulfillment ≈ 0.0308`, lý do dừng trung thực đều là `EARLY_COMPLETION`). Hệ quả tất yếu là phép quét `W=5` vs `W=10` vs `W=20` đồng nhất trên kịch bản 6–9 lượt này; khả năng bắt lặp ngoài cửa sổ `W=5` được chứng minh độc lập bằng test tích hợp dùng `StoryPlan` 12 chủ đề trong bộ nhớ (`test_time_budget_exhausted_and_outside_window_replay_detection`). Chúng tôi **không tự ý sửa `data/`** để giữ đóng băng bộ dữ liệu tham chiếu E01.

---

## 4. Research Methodology (`P06-E01` Implemented Protocol)

- **Câu hỏi nghiên cứu (Research Questions):**
  - **RQ1 (`Coverage`):** Khi chạy tuần tự qua 3 SKU trong kịch bản không bình luận, LangGraph Agent có đạt `mandatory_topic_coverage = 1.0` dựa hoàn toàn trên `PlaybackCompleted` ACK như baseline `ScriptFirst` hay không, và khi có lỗi ACK/fallback có bảo toàn được tiến trình không?
  - **RQ2 (`Repetition` & `W ∈ {5, 10, 20}`):** Kiến trúc `ShortTermPlayedHistory` cửa sổ `W` + `RepetitionDetector` có ngăn được lặp nguyên văn và giảm trùng lặp n-gram (`lexical_repetition_rate`, `max_prior_ngram3_jaccard`) so với `script_first_deterministic` / `script_first_upfront_llm` không? Chuyện gì xảy ra khi văn bản lặp nằm ngoài cửa sổ `W` (ví dụ turn 6 lặp lại turn 0 khi `W=5`)?
  - **RQ3 (`Safety & Reliability`):** Chu trình `1 + K` bounded rewrite + fail-closed `PREAPPROVED_FALLBACK` + `P05KnowledgeAdapter` giữ được `0` replay chunk đã phát, `0` vượt ngân sách retry và tách bạch lỗi retryable vs non-retryable không?
- **Giả thuyết có thể bác bỏ (Falsifiable Hypotheses):**
  - `H1`: Nếu một lời thoại bị `P05` từ chối hoặc thất bại phát (`FAILED`/`UNKNOWN`), hệ thống tuyệt đối **không** được đánh dấu topic đó hoàn tất trong `GlobalTopicCoverage` hoặc đưa vào `transcript.jsonl`.
  - `H2`: Khi xuất hiện câu lặp vượt ngoài `W` (cách hơn `W` lượt), bộ kiểm tra cục bộ của agent sẽ bỏ lọt nhưng bộ đánh giá toàn phiên (`compute_repetition_metrics` trên toàn `transcript.jsonl`) phải phát hiện chính xác (`outside_window_exact_text_replay_count > 0`) khi `W=5` và chặn được khi `W >= khoảng cách lặp` (ví dụ `W=10`).
- **Ba phương pháp đối chứng (`ExperimentMethod`):**
  1. `script_first_deterministic`: Ghép điểm nhấn từ `talking_points` & `SkuEvidenceView`, `0` gọi LLM (`token_usage_source = UNAVAILABLE`), không quét `W`.
  2. `script_first_upfront_llm`: Gọi LLM sinh toàn bộ kịch bản cho từng SKU ở đầu phiên (`UpfrontChunkDraftLLMOutput`, prompt versioned), không có lịch sử động hay `W`.
  3. `langgraph_structured_story`: Đồ thị LangGraph 8 node có bộ nhớ 4 thành phần (`W ∈ {5, 10, 20}`), kiểm tra lặp, kiểm chứng P05 và bounded rewrite `K = 2`.
- **Biến kiểm soát & Chính sách công bằng:** Cố định `seed = 42`, `max_chunk_duration_sec = 8.0s`, cùng bộ `StoryPlan` + `SkuEvidenceView`, cùng tốc độ đọc mô phỏng `2.6 words/sec` (`min_speech_duration_ms = 1000`), cùng chế độ cô lập 3 tầng provider (`Mock != Ollama != Gemini` — cấm gộp trong `compare_runs()` với mã lỗi `CROSS_TIER_POOLING_PROHIBITED`), và **tuyệt đối không dùng `P05 ALLOW` làm nhãn đúng sai thực tế** (chỉ dùng `GoldFactualLabel` độc lập).

---

## 5. Evaluation Metrics Architecture (`src/p06/evaluation/`)

Mọi chỉ số đều trả về `MetricResult` khóa chặt: khi `status != COMPUTED` (`NOT_EVALUATED`, `NOT_APPLICABLE`, `INVALID`), bắt buộc `value = None` và ghi rõ `missing_reason`, tách rạch ròi 6 loại `MetricProvenance` (`MEASURED_WALL_CLOCK`, `SIMULATED_CLOCK`, `PROVIDER_REPORTED`, `DERIVED_FROM_EVIDENCE`, `ESTIMATED`, `UNAVAILABLE`).

### 5.1. Trục Coverage (`src/p06/evaluation/metrics/coverage.py` — 14 chỉ số)
- **Công thức chính:**
  - `mandatory_topic_coverage` = $|\text{completed\_non\_fallback\_topics} \cap \text{expected\_mandatory}| / |\text{expected\_mandatory}|$ (mẫu số `0` -> `NOT_EVALUATED`).
  - `declared_verified_claim_coverage` = $|\text{covered\_allowed\_claims} \cap \text{allowed\_claims}| / |\text{allowed\_claims}|$ (chỉ từ lượt `VERIFIED`, không fallback).
  - `simulated_played_duration_sec` = $\sum (\text{actual\_duration\_ms} / 1000.0)$ trên ACK `COMPLETED & APPLIED` đã khử trùng theo `playback_event_id`.
  - `duration_fulfillment` = $\min(\text{played\_sec} / \text{target\_duration\_sec}, 1.0)$ (`INVALID` nếu `target <= 0`).
  - `simulated_idle_sec` = $\max(0.0, \text{simulated\_elapsed\_sec} - \text{played\_sec})$.
  - `time_to_complete_mandatory_topics_sec` = $(\text{completion\_occurred\_at} - \text{virtual\_clock\_start\_utc})$ tính thuần trên `VirtualClock` (`time_basis = "virtual_clock"`), hoặc tổng thời lượng phát tích lũy (`cumulative_played_duration_sec`) nếu thiếu `virtual_clock_start_utc`.
- **Ví dụ tính tay:** 6 mandatory topics, mỗi topic 1 chunk dài `6154 ms` trên `VirtualClock` từ `12:00:00Z` -> hoàn tất tại `12:00:36.924Z`: `mandatory_topic_coverage = 6/6 = 1.0`, `simulated_played_duration_sec = 36.924s`, `time_to_complete_mandatory_topics_sec = 36.924s`, `duration_fulfillment = 36.924 / 600.0 = 0.06154`.
- **Giới hạn & Kiểm thử:** `declared_verified_claim_coverage` mới kiểm chứng khai báo ID qua `P05`, chưa chứng minh suy luận ngữ nghĩa câu chữ; `human_assessed_fact_coverage` luôn `NOT_EVALUATED` cho tới `T09`. Kiểm thử bởi `TestCoverageMetrics` (`tests/unit/test_evaluation_metrics.py`).

### 5.2. Trục Repetition (`src/p06/evaluation/metrics/repetition.py` — 18 chỉ số)
- **Công thức chính (đo trên toàn `transcript.jsonl`, độc lập với `W`):**
  - `exact_chunk_replay_count`: Số lần `chunk_id` xuất hiện trùng lặp.
  - `exact_normalized_text_replay_count`: Số lượt có chuẩn hóa chữ thường/bỏ dấu câu trùng hệt một lượt bất kỳ trước đó.
  - `outside_window_exact_text_replay_count`: Số lượt trùng text chuẩn hóa mà lần xuất hiện gần nhất trước đó cách $> W$ lượt (tức khoảng cách chỉ số $\ge W + 1$, nghĩa là $j < i - W$, khớp với cửa sổ `W` lượt gần nhất của `ShortTermPlayedHistory`; `NOT_APPLICABLE` nếu `history_window is None`).
  - `max_prior_word_jaccard_{mean, p95, max}` và `max_prior_ngram3_jaccard_{mean, p95, max}`: Với mỗi lượt $i \ge 1$, lấy $\max_{j < i} \text{Jaccard}(S_i, S_j)$, trong đó $\text{Jaccard}(A, B) = \frac{|A \cap B|}{|A \cup B|}$.
  - `windowed_ngram3_jaccard_mean_w{5,10,20}`: Cùng công thức nhưng $j \in [\max(0, i-K), i-1]$.
  - `distinct_k` ($k \in \{1, 2, 3\}$) = $\frac{|\text{unique } k\text{-grams across transcript}|}{|\text{total } k\text{-grams}|}$.
  - `lexical_repetition_rate`: Tỷ lệ lượt $i \ge 1$ vượt ngưỡng `word_jaccard >= 0.65` hoặc `ngram3_jaccard >= 0.45`.
- **Ví dụ tính tay (`distinct_1` & Jaccard):** Câu 0: `"a b c d"` (`{a,b,c,d}`), câu 1: `"a b e f"` (`{a,b,e,f}`): $\text{WordJaccard} = |\{a,b\}| / |\{a,b,c,d,e,f\}| = 2/6 = 0.3333$; `distinct_1` = $6 / 8 = 0.75$.
- **Giới hạn & Kiểm thử:** Trùng lặp từ vựng không bắt được paraphrase đồng nghĩa hoàn toàn; `human_unnecessary_semantic_repetition` giữ `NOT_EVALUATED`. Kiểm thử bởi `TestRepetitionMetrics` + `test_time_budget_exhausted_and_outside_window_replay_detection`.

### 5.3. Trục Safety (`src/p06/evaluation/metrics/safety.py` — 10 chỉ số)
- **Công thức chính:**
  - `p05_rejection_count`, `p05_rejection_rate`, `p05_rejection_reason_distribution`: Đọc từ `graph_traces[*].p05_decisions`.
  - **Hard Gates từ bằng chứng thô:** `invalid_candidate_playback_count` (phát khi không có `VERIFIED` hoặc thiếu `gate_decision_id`), `duplicate_completed_chunk_replay_count` (cùng `chunk_id` áp dụng `APPLIED` > 1 lần).
  - **Chỉ số cần nhãn chuẩn độc lập (`GoldFactualLabel`):** `unsupported_claim_rate`, `verifier_false_accept_count` (Hard Gate = `0` khi có `gold_labels`), `verifier_false_reject_count`, `verifier_precision` = $\frac{TP}{TP + FP}$, `verifier_recall` = $\frac{TP}{TP + FN}$. Khi không truyền `gold_labels`, **tất cả 5 chỉ số trả `NOT_EVALUATED` (`None`)**.
- **Chứng minh giới hạn thực nghiệm của P05 (`tests/contract/test_e01_factual_verification_limits.py` — 9 tests):** Xác minh 8 tình huống thực tế: chặn sai giá số (`169.000đ` vs `159.000đ`), phát hiện điểm mù chữ viết giá (`"một trăm sáu mươi chín nghìn"` -> lọt P05 nhưng bị `GoldFactualLabel` bắt làm `false_accept=1`), phát hiện điểm mù claim bịa gắn kèm `evidence_id` thật (`false_accept=1`), chặn rò rỉ tên SKU khác, thiếu evidence, cấm câu chữa bệnh, TOCTOU quyền/giá hết hạn, và prompt injection.

### 5.4. Trục Reliability (`src/p06/evaluation/metrics/reliability.py` — 17 chỉ số)
- **Công thức chính:** Lọc `content_traces` (loại bỏ các lượt kết thúc biên SKU/phiên sạch qua `is_clean_termination_boundary_trace()`):
  - `turns_attempted = len(content_traces)`; `generation_attempts` = tổng `len(draft_attempts)` (hoặc `len(provider_calls)` nếu baseline upfront).
  - `rewrite_rate` = $\text{count}(\text{retries\_used} > 0) / \text{turns\_attempted}$; `retry_budget_violations` = $\text{count}(\text{retries\_used} > \text{max\_retries})$ (**Hard Gate = `0`**).
  - `fallback_rate` = $\text{fallback\_count} / \text{turns\_attempted}$; `safe_abort_rate` = $\text{safe\_abort\_count} / \text{turns\_attempted}$ (chỉ đếm lượt `SAFE_ABORT_NO_CANDIDATE` thực sự).
  - `attempts_per_turn_{mean, p50, p95, max}`: Trả `NOT_APPLICABLE` cho `script_first_deterministic` (vì `0` lần gọi LLM).
  - Phân bố lỗi từ `errors.jsonl` (`retryable_failure_distribution`, `non_retryable_failure_distribution`) và `provider_calls.jsonl` (`provider_error_distribution`), kèm `termination_reason`.

### 5.5. Trục Performance (`src/p06/evaluation/metrics/performance.py` — 13 chỉ số)
- **Công thức chính (Type-7 percentile & tách provenance):**
  - Cho dãy tăng dần $x_0 \le \dots \le x_{n-1}$, vị trí nội suy $h = q(n - 1)$, $i = \lfloor h \rfloor$, $f = h - i$: $P_q = x_i + f \cdot (x_{i+1} - x_i)$.
  - Độ trễ: `provider_latency_{p50, p95}_ms` (`SIMULATED_CLOCK` với Mock), `invocation_latency_{p50, p95}_ms` (`MEASURED_WALL_CLOCK`, đã lọc lượt biên sạch), `planning_latency_ms`, `upfront_script_generation_latency_ms`, `total_measured_processing_ms`, `simulated_speech_duration_sec`.
  - Token & Chi phí: `total_model_calls`, `input_tokens`, `output_tokens`, `wasted_tokens` (**bắt buộc `NOT_EVALUATED` nếu có bất kỳ call nào `UNAVAILABLE`**); `estimated_llm_cost_usd` = $\frac{\text{in}}{10^6} \cdot r_{\text{in}} + \frac{\text{out}}{10^6} \cdot r_{\text{out}}$ (trả `NOT_APPLICABLE` cho Mock, `NOT_EVALUATED` nếu thiếu `pricing` ở gốc `manifest` hoặc `provider_config.pricing`).

### 5.6. Tổng hợp, Đối chiếu & Phiếu chấm mù (`evaluator.py`, `comparison.py`, `human_eval.py`)
- `evaluate_run()` kiểm tra `5` Hard Gates không bù trừ (`exact_chunk_replay_count == 0`, `duplicate_completed_chunk_replay_count == 0`, `invalid_candidate_playback_count == 0`, `retry_budget_violations == 0`, và `verifier_false_accept_count == 0` nếu có `gold_labels`), luôn giữ `6` placeholder chấm người ở `NOT_EVALUATED`.
- `compare_runs()` gắn `compatible=False` ngay nếu trộn tier/provider (`CROSS_TIER_POOLING_PROHIBITED`), lệch `scenario`, `dataset_sha256`, `story_plan` hoặc `contract_version`.
- `export_blind_human_eval_sheets()` xáo trộn tất định (`seed`), thay bằng `SAMPLE_001..N` và `METHOD_A..E`, xóa hoàn toàn `method`, `W`, `run_id`, `model_id` trong `blind_eval_sheet.csv`/`.jsonl` (giữ khóa ánh xạ riêng tại `blind_key_mapping.private.json`) và để trống toàn bộ cột điểm `1–5`.

---

## 6. Experiment Runner Architecture (`src/p06/runner/` & CLI)

- **Cấu hình & Offline Guard (`config.py`):** `load_experiment_run_config()` kết hợp `configs/default.yaml`, `configs/experiments/p06_e01.yaml`, `configs/models/*.yaml`; khóa `history_window ∈ [1, 100]` cho `LANGGRAPH` và `None` cho `SCRIPT_FIRST_*`. Rào chắn `Offline Guard` từ chối ngay (`ProviderConfigError` hoặc `SystemExit` mã `2` ở CLI `run_e01.py`) nếu dùng `ollama`/`gemini` (kể cả khi chỉ truyền `--config configs/models/gemini_flash.yaml`) mà không có cờ tường minh `--allow-live-provider`. Hàm `sanitize_mapping_for_artifact()` che đệ quy khóa bí mật (`[REDACTED]`) trong khi bảo toàn các trường provenance/token telemetry phi bí mật.
- **Điều phối phiên chạy & Ranh giới 3 SKU (`session_runner.py`):**
  - Khởi tạo hoàn toàn cô lập cho mỗi run: `VirtualClock`, `P05KnowledgeAdapter`, `StoryCheckpoint`, `ShortTermPlayedHistory(W)`, `GlobalTopicCoverage`, `OptionalSemanticMemory`, `RepetitionDetector`, `SimulatedPlaybackHarness`, `MockPlaybackAckBus`, `EvidenceCollector`.
  - **Baseline (`_run_script_first_loop`):** Lặp qua `pinned_sku_ids`, gọi `harness.switch_active_sku()` ở ranh giới chuyển SKU, chạy `ScriptFirstBaseline.run_session(...)` với ngưỡng dừng từng lượt (`max_turns`, `target_duration_sec`, `max_consecutive_aborts`).
  - **LangGraph (`_run_langgraph_loop`):** Từng lượt chuyển `AgentState.from_harness(...)` -> gọi `run_storytelling_turn(...)` -> ghi `graph_trace.jsonl`. Khi `turn_res.should_terminate` bật ở cuối một SKU, runner chuyển sang SKU kế tiếp qua `harness.switch_active_sku()`, hoặc kết thúc phiên với 1 trong 6 lý do chuẩn `RunTerminationReason`: `EARLY_COMPLETION`, `CONTENT_EXHAUSTED`, `TIME_BUDGET_EXHAUSTED`, `MAX_TURNS_REACHED`, `MAX_CONSECUTIVE_ABORTS`, `FATAL_ERROR`.
  - Mọi lỗi playback `FAILED`/`UNKNOWN`, `P05` reject, JSON vỡ, non-retryable failure đều được `EvidenceCollector` ghi vào `errors.jsonl` và gắn `is_wasted=True` trong `provider_calls.jsonl`; **tuyệt đối chỉ ghi `transcript.jsonl` khi `PlaybackCompleted` ACK trả `APPLIED`** (`I-06`).

---

## 7. Artifact & Reproducibility System

Mỗi lần chạy tạo duy nhất một thư mục bất biến `output_dir / run_id` (`mkdir(exist_ok=False)` cấm ghi đè) gồm đúng **10 tệp**:
`manifest.json`, `config.yaml`, `story_plan.json`, `transcript.jsonl`, `playback_events.jsonl`, `graph_trace.jsonl`, `provider_calls.jsonl`, `metrics.json`, `token_usage.json`, `errors.jsonl`.

- **Định dạng `run_id`:** `{experiment_id}__{scenario}__{method}__{wTag}__{YYYYMMDDTHHMMSSZ}__{uuid8}` (ví dụ `w5` hoặc `noW`).
- **Tính tái lập tất định logic (`test_logical_determinism_across_identical_mock_runs`):** Khi cố định `seed`, `StoryPlan`, `EvidenceBundle` và `MockLLMProvider`, 2 lần chạy độc lập cho ra chuỗi `transcript`, `covered_claim_ids`, `simulated_elapsed_sec` và toàn bộ metrics đánh giá giống hệt nhau `100%` (chỉ khác `run_id`, wall-clock timestamps và latency đo tường).

### Danh sách Các Lượt Chạy Tiền-Sửa-Lỗi (`SUPERSEDED`)

8 thư mục run tiền-sửa-lỗi vẫn được bảo toàn trên đĩa tại `runs/P06-E01/` để phục vụ audit trail (kèm `runs/P06-E01/comparison.*` và `runs/P06-E01/human_eval/` tiền-sửa-lỗi), **KHÔNG được dùng làm số liệu báo cáo** vì mang `BUG-A`, `BUG-B`, `BUG-C` đã vá:

| Run ID (`runs/P06-E01/<run_id>`) | Trạng thái | Lý do bị thay thế (`Superseded`) |
| :--- | :---: | :--- |
| `P06-E01__product_education_10m__script_first_deterministic__noW__20261126T083945Z__0973c628` | `SUPERSEDED` | `BUG-A` (token provenance bị `[REDACTED]`), `BUG-B` (`time_to_complete` dùng `started_at_utc`), thiếu SKU-scoped `candidate_id` (`NEW-02`) |
| `P06-E01__product_education_10m__script_first_upfront_llm__noW__20261126T083952Z__a4661a84` | `SUPERSEDED` | `BUG-A`, `BUG-B`, `NEW-02` |
| `P06-E01__product_education_10m__langgraph_structured_story__w5__20261126T084019Z__2c9f0da1` | `SUPERSEDED` | `BUG-A`, `BUG-B`, `BUG-C` (`safe_abort_count = 3` do 3 lượt biên SKU) |
| Sweep `sweep_20261126T084023Z` (5 runs: `43a51e2d`, `a99db43f`, `86811c4d`, `516e2c96`, `a0db9af7`) | `SUPERSEDED` | Chứa các lỗi `BUG-A`, `BUG-B`, `BUG-C` trước bản vá Phase 4; đã được thay thế bởi `post_fix_sweep_product_education_10m` (`sweep_20261126T085820Z`) |

---

## 8. Actual Offline Dry-Run Evidence (Hậu Sửa Lỗi)

Sau khi vá toàn bộ 8 findings và thông qua regression tests, đã thực thi lại 4 lệnh CLI ngoại tuyến hoàn toàn mới (`seed=42`, `provider=mock`, `scenario=product_education_10m`, `target_duration_sec=600.0`):

```powershell
# 1. Script-First Deterministic (no W)
.\.venv\Scripts\python.exe experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_e01.py --provider mock --method script_first_deterministic --scenario product_education_10m

# 2. Script-First Upfront LLM (no W)
.\.venv\Scripts\python.exe experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_e01.py --provider mock --method script_first_upfront_llm --scenario product_education_10m

# 3. LangGraph Structured Story (W=5)
.\.venv\Scripts\python.exe experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_e01.py --provider mock --method langgraph_structured_story --scenario product_education_10m --history-window 5

# 4. Full Sweep (5 cấu hình) + Phiếu chấm mù vào thư mục sạch hậu-sửa-lỗi
.\.venv\Scripts\python.exe experiments/sales-intelligence/autonomous-storytelling/experiments/p06_e01_no_comments/run_e01.py --provider mock --sweep --scenario product_education_10m --export-human-eval --output-dir experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/post_fix_sweep_product_education_10m
```

### Kết quả 3 lượt chạy đơn lẻ hậu-sửa-lỗi (`runs/P06-E01/`)

| Hạng mục kiểm tra | `script_first_deterministic` (`bb842cf3`) | `script_first_upfront_llm` (`52632fcf`) | `langgraph_structured_story` W=5 (`b45acebe`) |
| :--- | :---: | :---: | :---: |
| `provider_tier` / `model_id` | `unit_test` / `deterministic-talking-points-v0.1` | `unit_test` / `deterministic-mock-v0.1` | `unit_test` / `deterministic-mock-v0.1` |
| `metric_provenance.token_usage` (`BUG-A` check) | `UNAVAILABLE` | `SIMULATED` | `SIMULATED` |
| `simulator_assumptions.virtual_clock_start_utc` | `2026-11-26T12:00:00+00:00` | `2026-11-26T12:00:00+00:00` | `2026-11-26T12:00:00+00:00` |
| `termination_reason` & `hard_gates_passed` | `EARLY_COMPLETION` / `True` | `EARLY_COMPLETION` / `True` | `EARLY_COMPLETION` / `True` |
| `transcript_turns` / `completed_topic_count` | `6` / `6` (`3 SKU`) | `6` / `6` (`3 SKU`) | `6` / `6` (`3 SKU`) |
| `mandatory_topic_coverage` | `1.0` (`6/6`) | `1.0` (`6/6`) | `1.0` (`6/6`) |
| `simulated_played_duration_sec` / `duration_fulfillment` | `39.228s` / `0.06538` | `36.924s` / `0.06154` | `36.924s` / `0.06154` |
| `time_to_complete_mandatory_topics_sec` (`BUG-B` check) | `39.228s` (`virtual_clock`) | `36.924s` (`virtual_clock`) | `36.924s` (`virtual_clock`) |
| `safe_abort_count` / `safe_abort_rate` (`BUG-C` check) | `0` / `0.0` (`excluded=0`) | `0` / `0.0` (`excluded=0`) | `0` / `0.0` (`excluded=3`) |
| `invocation_latency_p50_ms` (`BUG-C` check) | `1.564 ms` | `1.438 ms` | `13.193 ms` (`excluded=3`) |
| `total_measured_processing_ms` | `27.090 ms` | `24.157 ms` | `130.357 ms` |
| `exact_normalized_text_replay_count` | `3` *(lặp theo cặp trong mỗi SKU)* | `0` | `0` |
| `lexical_repetition_rate` / `max_prior_ngram3_jaccard_mean` | `0.6000` / `0.6067` | `0.0000` / `0.0868` | `0.0000` / `0.0868` |
| `attempts_per_turn_mean` | `NOT_APPLICABLE` (`None`) | `1.0` | `1.0` |
| `input_tokens` / `output_tokens` / `wasted_tokens` | `None` / `None` / `None` (`NOT_EVALUATED`) | `720` / `270` / `0` (`SIMULATED`) | `720` / `270` / `0` (`SIMULATED`) |

### Kết quả Sweep 5 cấu hình hậu-sửa-lỗi (`sweep_20261126T085820Z`)

Thư mục: `runs/P06-E01/post_fix_sweep_product_education_10m/` (`compatible = True`, `grouped_tiers = ["unit_test"]`):

| `run_id` (hậu-sửa-lỗi) | `method` | `W` | `hard_gates` | `topic_cov` | `dur_fulfill` | `exact_text_replay` | `ngram3_mean` | `lex_rep_rate` | `safe_abort_rate` | `input_tok` / `output_tok` |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `...__script_first_deterministic__noW__20261126T085820Z__9d79c231` | `script_first_deterministic` | `N/A` | `PASS` | `1.0000` | `0.0654` | `3` | `0.6067` | `0.6000` | `0.0000` | `N/A` / `N/A` |
| `...__script_first_upfront_llm__noW__20261126T085821Z__42945e7d` | `script_first_upfront_llm` | `N/A` | `PASS` | `1.0000` | `0.0615` | `0` | `0.0868` | `0.0000` | `0.0000` | `720` / `270` |
| `...__langgraph_structured_story__w5__20261126T085821Z__43c1c7fd` | `langgraph_structured_story` | `5` | `PASS` | `1.0000` | `0.0615` | `0` | `0.0868` | `0.0000` | `0.0000` | `720` / `270` |
| `...__langgraph_structured_story__w10__20261126T085821Z__ea7532d0` | `langgraph_structured_story` | `10` | `PASS` | `1.0000` | `0.0615` | `0` | `0.0868` | `0.0000` | `0.0000` | `720` / `270` |
| `...__langgraph_structured_story__w20__20261126T085821Z__2e1859c7` | `langgraph_structured_story` | `20` | `PASS` | `1.0000` | `0.0615` | `0` | `0.0868` | `0.0000` | `0.0000` | `720` / `270` |

- **Xuất phiếu chấm mù (`post_fix_sweep_product_education_10m/human_eval/`):** Tạo đủ `blind_eval_sheet.csv`, `blind_eval_sheet.jsonl` và `blind_key_mapping.private.json` gồm `SAMPLE_001..SAMPLE_005` ánh xạ ngẫu nhiên theo `seed=42` (`METHOD_A..E`); toàn bộ cột điểm `1–5` đều rỗng và không lộ tên phương pháp/`W`/`run_id` trong file CSV/JSONL phát cho người chấm.
- **Nhận xét trung thực:** Trên `MockLLMProvider`, `script_first_upfront_llm` và `langgraph_structured_story` (`W=5, 10, 20`) cho kết quả giống nhau vì cả 6 chủ đề đều dùng biến thể cố định của mock và kế hoạch chỉ có 6 lượt (`< 10`, `< 20`); đồng thời `script_first_deterministic` tự nhiên bộc lộ nhược điểm lặp cứng 2 lần/SKU (`exact_normalized_text_replay_count = 3`) do cùng mẫu ghép tiêu đề SKU.

---

## 9. Giải thích Kiến thức Kỹ thuật & Khoa học Thực nghiệm (Tiếng Việt)

Phần này tổng hợp hệ thống khái niệm khoa học thực nghiệm AI/ML được áp dụng trực tiếp trong `P06-E01` để hỗ trợ đọc hiểu và đào tạo nghiên cứu:

1. **Research Question (`RQ`) & Hypothesis (`H`):** `RQ` là câu hỏi nghiên cứu trung tâm (ví dụ: *"Cửa sổ `W` nhỏ có làm tăng lặp ngoài cửa sổ ở phiên dài không?"*); `Hypothesis` là giả thuyết có thể **kiểm chứng và bác bỏ** bằng dữ liệu (ví dụ: nếu giữ lặp ở `W=5`, tỷ lệ lặp ngoài cửa sổ sẽ $> 0$).
2. **Experimental Design (Thiết kế thực nghiệm):** Là bản thiết kế kiểm soát các biến để đo tác động nhân quả của phương pháp AI. Trong P06-E01, ta thiết kế ma trận `Method × W × Scenario` cùng bảng `CompatibilityIssue` tự động bắt sai lệch trước khi so sánh.
3. **Biến Độc lập, Phụ thuộc & Kiểm soát (Independent / Dependent / Controlled Variables):**
   - *Biến độc lập (`IV`, thứ ta chủ động thay đổi):* Phương pháp (`script_first_deterministic`, `script_first_upfront_llm`, `langgraph_structured_story`) và kích thước cửa sổ `W ∈ {5, 10, 20}`.
   - *Biến phụ thuộc (`DV`, thứ ta đo):* `mandatory_topic_coverage`, `lexical_repetition_rate`, `outside_window_exact_text_replay_count`, `p05_rejection_rate`, `rewrite_rate`, `token_usage`.
   - *Biến kiểm soát (`CV`, bắt buộc giữ cố định):* `StoryPlan`, `dataset_sha256`, `seed`, `max_chunk_duration_sec = 8.0s`, tốc độ đọc `2.6 words/sec`, `contract_version`, và `provider_tier`.
4. **Baseline (Đường cơ sở đối chiếu):** Là hệ thống đơn giản hơn để biết mô hình phức tạp (LangGraph) có thực sự mang lại giá trị gia tăng không. P06 dùng 2 baseline tách bạch: `script_first_deterministic` (0 LLM, chi phí 0, dễ lặp) và `script_first_upfront_llm` (sinh sẵn toàn bộ các chủ đề của từng SKU ngay đầu phân đoạn SKU đó trong `_run_script_first_loop`, không dùng bộ nhớ động).
5. **Ablation & Sensitivity Analysis (Nghiên cứu cắt bỏ & Độ nhạy):** Ablation là giữ nguyên toàn bộ kiến trúc và chỉ thay đổi từng thành phần (ví dụ tắt/bật bộ nhớ động giữa `upfront_llm` và `langgraph`, hoặc quét độ nhạy `W ∈ {5, 10, 20}`) để đo đóng góp thực của thành phần đó.
6. **Data Provenance (Truy vết nguồn gốc dữ liệu):** Là cơ chế gắn nhãn nguồn sinh cho từng con số (`SIMULATED_CLOCK` cho thời gian phát mô phỏng vs `MEASURED_WALL_CLOCK` cho thời gian CPU thực thi, `UNAVAILABLE` cho token ở chế độ deterministic) nhằm tránh đánh tráo thời gian giả lập thành độ trễ thật (như `BUG-B` đã từng gặp).
7. **Circular Evaluation / Evaluation Leakage (Đánh giá vòng tròn / Rò rỉ đánh giá):** Xảy ra khi dùng chính thành phần cần đánh giá làm thước đo cho chính nó — ví dụ dùng quyết định `P05 ALLOW` để kết luận phát ngôn *"đúng 100% sự thật"*. P06 chặn hiện tượng này bằng `tests/contract/test_e01_factual_verification_limits.py`: tách rời `declared_verified_claim_coverage` khỏi `human_assessed_fact_coverage` và bắt buộc `GoldFactualLabel` độc lập cho `verifier_precision/recall`.
8. **Ground Truth (Nhãn chuẩn độc lập):** Là dữ liệu chuẩn được gán độc lập từ tài liệu nguồn (`ProductFact` + `EvidenceChunk` + kiểm định của con người) để đối chiếu độ chính xác thực của hệ thống.
9. **Verifier Precision & Recall:** Với hệ thống kiểm chứng P05 coi trường hợp **chặn (`BLOCK/REJECT`)** là lớp dương (Positive — phát hiện sai phạm), ta có:
   - $\text{Precision} = \frac{TP}{TP + FP}$ (trong các câu bị P05 chặn, có bao nhiêu câu thực sự sai? Precision thấp nghĩa là chặn oan nhiều -> đẩy `fallback_rate` lên cao).
   - $\text{Recall} = \frac{TP}{TP + FN}$ (trong các câu thực sự sai, P05 bắt được bao nhiêu câu? $FN$ chính là `verifier_false_accept_count` — câu sai lọt ra ngoài livestream, là **Hard Gate = `0`**!).
10. **Percentile `P50` / `P95` (Phân vị nội suy Type-7):** Trong hệ thống thời gian thực, trung bình (`mean`) dễ bị che giấu bởi vài điểm ngoại lai chậm (`tail latency`), nên ta đo `P50` (trung vị — 50% lượt nhanh hơn mức này) và `P95` (95% lượt nhanh hơn mức này). Công thức cho dãy sắp tăng $x_0 \le \dots \le x_{n-1}$: $h = q(n-1)$, $P_q = x_{\lfloor h \rfloor} + (h - \lfloor h \rfloor)(x_{\lfloor h \rfloor + 1} - x_{\lfloor h \rfloor})$.
11. **Reproducibility (Tính tái lập):** Khả năng một người khác lấy cùng mã nguồn, `seed`, `configs/` và `data/` có thể chạy lại và kiểm chứng đúng kết quả ghi trong `manifest.json` (`git_commit`, `dataset_sha256`, `prompt_hashes`, `package_versions`, `story_plan_sha256`).
12. **Experimental Validity (Giá trị hiệu lực thực nghiệm):** Gồm *Internal Validity* (bắt buộc đúng logic, không bị lỗi như `BUG-B`/`BUG-C` làm méo số đo) và *External Validity* (mức độ tổng quát ra thực tế). Hiện tại kết quả `Mock` đạt Internal Validity cao cho pipeline phần mềm, nhưng **External Validity cho tiếng Việt thực tế = 0** cho tới khi chạy `Ollama`/`Gemini` và chấm người thật (`T09`).

---

## 10. Testing Report & Verification Matrix

- **Tổng số tests tăng từ `189` (Phase 3 baseline) -> `249` tests (`+60` tests Phase 4):**
  - `tests/unit/test_phase3_audit_regressions.py`: **`5`** tests (SKU transition, `safe_fallback` hints, trace attempts, `semantic_memory` isolation, `ProviderFactory` variants).
  - `tests/unit/test_evaluation_metrics.py`: **`17`** tests (`15` tests 5 trục + evaluator + comparison + blind eval + `2` regression tests cho `BUG-B`, `BUG-C`, `NEW-05`).
  - `tests/contract/test_e01_factual_verification_limits.py`: **`9`** tests (8 negative/blind-spot cases thực tế của P05 + `GoldFactualLabel` precision/recall/`false_accept`).
  - `tests/unit/test_experiment_runner.py`: **`23`** tests (`18` tests config/Offline Guard/artifacts/termination/sweep + `5` regression tests cho `BUG-A`, `NEW-01..04`).
  - `tests/integration/test_e01_runner_and_reproducibility.py`: **`6`** tests (3-SKU end-to-end 3 methods, 30m 9-topic plan, `TIME_BUDGET_EXHAUSTED` + `W=5` vs `W=10` outside-window replay, error logging, CLI Offline Guard + cross-tier rejection, logical determinism).

- **Kết quả kiểm tra sau lần sửa code & test cuối cùng:**
  - `.\.venv\Scripts\python.exe -m pytest experiments/sales-intelligence/autonomous-storytelling/tests --collect-only -q`: **`249 tests collected in 1.74s`**.
  - `.\.venv\Scripts\python.exe -m pytest experiments/sales-intelligence/autonomous-storytelling/tests -v`: **`249 passed in 32.93s`** (`0 failed`, `0 skipped`).
  - `.\.venv\Scripts\python.exe -m pip check`: **`No broken requirements found.`**
  - Static scans: `0` lời gọi `model_copy(update=...)` trong `src/p06/`; `0` thao tác đọc/ghi `os.environ` trong `runner/` và `evaluation/`.

- **Các hạng mục CHƯA CHẠY (`NOT RUN` — đúng phạm vi đóng băng `E01-T08`):**
  - `Ollama CPU` live inference (`local_smoke_test`) — `NOT RUN` (chưa thực hiện theo chỉ thị chỉ dùng `MockLLMProvider`).
  - `Gemini API` live inference (`formal_experiment`) — `NOT RUN`.
  - Chấm điểm con người thực tế (`Human Blind Evaluation` 6 tiêu chí `1–5`) và `GoldFactualLabel` toàn phiên trên output LLM thật — `NOT RUN` (giữ `NOT_EVALUATED`, thuộc `E01-T09`).

---

## 11. Definition of Done & Git Summary

### Checklist Definition of Done (`E01-T08`)
- [x] Khắc phục các lỗi cấu trúc Phase 3 (`F-01..F-12`, `AUD-01..AUD-10`) không phá vỡ backward compatibility.
- [x] Hoàn thiện 5 nhóm chỉ số tự động (`src/p06/evaluation/metrics/`), `evaluator.py`, `comparison.py`, `human_eval.py`.
- [x] Hoàn thiện Experiment Runner & CLI ngoại tuyến (`src/p06/runner/`, `experiments/p06_e01_no_comments/run_e01.py`).
- [x] Khắc phục 100% `8/8` findings từ Independent Review (`BUG-A..C`, `NEW-01..05`) kèm regression tests.
- [x] Chạy lại offline CLI dry-runs với run IDs mới, bảo toàn lịch sử runs tiền-sửa-lỗi (`SUPERSEDED`).
- [x] `249/249` pytest tests pass, `pip check` sạch, `0` `model_copy(update=...)`, `0` rò rỉ secrets.
- [x] Không chỉnh sửa file ngoài `experiments/sales-intelligence/autonomous-storytelling/`.
- [ ] Không commit, push, tag hoặc merge (dừng lại để Tech Lead review).

### Tổng kết Git Working Tree (Phạm vi 100% nội bộ P06)
- **Tệp đã sửa (Modified Source — 12 files code + docs):**
  - `src/p06/adapters/interfaces.py`, `src/p06/agent/{deps,graph}.py`, `src/p06/agent/nodes/{_common,check_repetition,safe_fallback,verify_p05}.py`, `src/p06/baselines/script_first.py`, `src/p06/providers/{base,factory}.py`, `src/p06/schemas/events.py`, `src/p06/simulation/playback_harness.py`.
  - Tài liệu đồng bộ: `README.md`, `AGENTS.md`, `docs/README.md`, `evaluation/README.md`, `research/methodology.md`.
- **Tệp/thư mục tạo mới (Untracked):**
  - `src/p06/evaluation/` (`__init__.py`, `models.py`, `evaluator.py`, `comparison.py`, `human_eval.py`, `metrics/{__init__,coverage,repetition,safety,reliability,performance}.py`)
  - `src/p06/runner/` (`__init__.py`, `config.py`, `mock_fixtures.py`, `evidence_collector.py`, `manifest.py`, `session_runner.py`, `sweep.py`)
  - `experiments/p06_e01_no_comments/run_e01.py`
  - `tests/unit/{test_phase3_audit_regressions,test_evaluation_metrics,test_experiment_runner}.py`, `tests/contract/test_e01_factual_verification_limits.py`, `tests/integration/test_e01_runner_and_reproducibility.py`
  - `docs/06-phase4-evaluation-runner-e01-t08-report.md` (tài liệu này)
  - `runs/P06-E01/*` (đã được `.gitignore` loại trừ khỏi git tracking)
- **Thống kê code diff trước cập nhật tài liệu:** `12 files changed, 592 insertions(+), 30 deletions(-)` (phần code sửa trên các tệp cũ).

### Danh sách File Trọng tâm để Tech Lead Review
1. `experiments/sales-intelligence/autonomous-storytelling/src/p06/evaluation/metrics/{coverage,repetition,safety,reliability,performance}.py`
2. `experiments/sales-intelligence/autonomous-storytelling/src/p06/evaluation/{models,evaluator,comparison,human_eval}.py`
3. `experiments/sales-intelligence/autonomous-storytelling/src/p06/runner/{config,manifest,evidence_collector,session_runner,sweep}.py`
4. `experiments/sales-intelligence/autonomous-storytelling/src/p06/baselines/script_first.py` & `src/p06/simulation/playback_harness.py`
5. `experiments/sales-intelligence/autonomous-storytelling/tests/contract/test_e01_factual_verification_limits.py` & `tests/integration/test_e01_runner_and_reproducibility.py`
6. `experiments/sales-intelligence/autonomous-storytelling/runs/P06-E01/post_fix_sweep_product_education_10m/{comparison.md,human_eval/blind_eval_sheet.csv}`

---

## 12. Open Issues & Next Phase Recommendation (`E01-T09`)

1. **Vấn đề mở về dung lượng kịch bản (`e01_story_plans.json`):** Hiện tại các kế hoạch tham chiếu chỉ có 6–9 chủ đề (~`37–56s` lời thoại ở `8s/chunk`), chưa đủ kéo dài để kích hoạt khác biệt `W=5` vs `W=10` vs `W=20` hay mô phỏng trọn 10–30 phút thực chiến. Ở `E01-T09`, cần quyết định mở rộng bộ `StoryPlan` synthetic (hoặc cho phép nhiều chunk mỗi topic) *trước khi* chạy formal benchmark.
2. **Owner & Reviewer độc lập (`P06-OPEN-6`):** Hiện vẫn ở trạng thái **`PENDING ASSIGNMENT`**; cần phân công chính thức trước khi tiến hành ký duyệt nghiệm thu.
3. **Lộ trình đề xuất cho `E01-T09` (KHÔNG triển khai trong phiên này):**
   - **Bước 1:** Phân công Owner & Independent Reviewer cho P06.
   - **Bước 2:** Chạy `Ollama CPU` smoke test (`configs/models/ollama_qwen3_1.7b.yaml` / `4b`) để kiểm tra JSON schema & khả năng sinh tiếng Việt của local model (giữ tách biệt tuyệt đối ở tier `local_smoke_test`).
   - **Bước 3:** Xác minh model ID, hạn mức quota, bảng giá `pricing` và thỏa thuận dữ liệu (DPA/terms) cho `GeminiAPIProvider` (`configs/models/gemini_flash.yaml`), sau đó khóa giao thức formal benchmark nhiều `seed`/lặp.
   - **Bước 4:** Mở rộng dung lượng kịch bản `10–30m` để phép quét `W ∈ {5, 10, 20}` thực sự phân biệt được hành vi nhớ dài hạn.
   - **Bước 5:** Tổ chức **Pilot Calibration** cho rubric 6 tiêu chí (`human_eval_rubric_v0.1.md`), gán nhãn chuẩn độc lập `GoldFactualLabel` để đo `verifier_precision`, `verifier_recall`, `human_assessed_fact_coverage`, phân tích độ trễ P50/P95 & chi phí `USD` thật, rồi mới trình chốt cổng `GO / CHANGE / NO-GO`.
