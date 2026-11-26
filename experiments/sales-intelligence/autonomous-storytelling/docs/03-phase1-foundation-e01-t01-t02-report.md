# Báo cáo Phase 1 — Thiết lập Môi trường (`E01-T01`) & Khóa Core Pydantic Schemas `p06-mock-v0.1` (`E01-T02`)

| Thuộc tính | Giá trị |
| :--- | :--- |
| **Ngày lập báo cáo** | `2026-11-26` |
| **Nhánh Git** | `research/p06-autonomous-storytelling` |
| **Base Checkpoint** | `p06-checkpoint-01-scaffold` (`f68c801`) |
| **Phạm vi thực hiện** | `Phase 1 — E01-T01 (Environment Setup) & E01-T02 (Core Pydantic Schemas p06-mock-v0.1)` |
| **Module mục tiêu** | `P06 — Sales Intelligence & Autonomous Storytelling` (`experiments/sales-intelligence/autonomous-storytelling/`) |
| **Trạng thái hiện tại** | `COMPLETED (Phase 1) \| E01-T03..E01-T09: NOT STARTED` |

---

## 1. Tóm tắt Mục tiêu & Kết quả Phase 1

Phase 1 hoàn tất hai nền tảng tiên quyết đầu tiên trong kế hoạch `E01-T01..T09` ([`02-open-decisions-alignment-and-e01-plan.md`](./02-open-decisions-alignment-and-e01-plan.md)):

1. **`E01-T01` — Xác minh môi trường `.venv` & cài đặt editable package `hostra-p06-storytelling`:** Đảm bảo môi trường Python cục bộ cho CPU hoạt động ổn định, không xung đột với các module GPU/backend khác.
2. **`E01-T02` — Khóa hợp đồng dữ liệu lõi Pydantic v2 (`p06-mock-v0.1`):** Triển khai đầy đủ 5 tệp trong `src/p06/schemas/` (`__init__.py`, `story.py`, `candidate.py`, `events.py`, `state.py`) cùng bộ kiểm thử tự động `28/28` test cases pass.

---

## 2. Chi tiết Môi trường & Dependencies (`E01-T01`)

Môi trường thực thi được xác minh trực tiếp trong `.venv` tại repo root (`.\.venv\Scripts\python.exe`):

| Thành phần | Phiên bản xác minh | Ghi chú |
| :--- | :---: | :--- |
| **Python** | `3.13.2` | Phù hợp ràng buộc `>=3.11,<3.14` trong `pyproject.toml` |
| **Package P06 (`hostra-p06-storytelling`)** | `0.1.0` | Cài đặt ở chế độ editable (`src/p06`) |
| **Pydantic** | `2.14.4` | Nền tảng validation cho toàn bộ hợp đồng `p06-mock-v0.1` |
| **LangGraph** | `1.2.24` | Điều phối đồ thị `StateGraph(AgentState)` |
| **langchain-core** | `1.8.5` | Thư viện lõi tích hợp cùng LangGraph |
| **PyYAML** | `6.0.4` | Đọc cấu hình thí nghiệm và model YAML |
| **httpx** | `0.28.1` | Giao tiếp HTTP cho `OllamaLocalProvider` (Tier 2 CPU smoke test) |
| **pytest** | `9.2.0` | Bộ chạy kiểm thử đơn vị và hợp đồng |

---

## 3. Kiến trúc & Hợp đồng Dữ liệu `p06-mock-v0.1` (`E01-T02`)

Toàn bộ schema được xuất khẩu tập trung tại [`src/p06/schemas/__init__.py`](../src/p06/schemas/__init__.py) qua `__all__`, áp dụng `from __future__ import annotations`, `ConfigDict(extra="forbid", validate_assignment=True)`, docstring tiếng Việt giáo dục (5 câu hỏi đầu module + Google-style) và chú thích bảo toàn các bất biến kiến trúc `I-01`–`I-09`:

| Tệp Schema | Các thành phần chính | Bất biến & Quy tắc cốt lõi được khóa |
| :--- | :--- | :--- |
| [`story.py`](../src/p06/schemas/story.py) | **Models:** `StoryPlan`, `StoryArc`, `StoryTopic`, `StoryChunk`<br>**Enums:** `StoryPlanApprovalStatus`, `StoryChunkRole`, `BreakpointType`<br>**Constants:** `CONTRACT_VERSION` (`"p06-mock-v0.1"`), `MIN_PINNED_SKUS` (`1`), `MAX_PINNED_SKUS` (`5`), `MAX_CHUNK_DURATION_SEC` (`30.0`), `MAX_ARC_DURATION_SEC` (`3600`) | - `StoryPlan` chỉ hợp lệ ở trạng thái `APPROVED` khi có đủ `approved_by` và `approved_at` (Gate `G6`).<br>- `pinned_sku_ids` giới hạn `1..5` SKU (`ACR-002`), không rỗng, không trùng.<br>- Vị trí `StoryArc` liên tục `1..len(arcs)`; `arc_id` và `topic_id` duy nhất toàn kế hoạch.<br>- `StoryChunk` cấm text rỗng sau `strip()` và kiểm soát thời lượng `<= 30.0s`. |
| [`candidate.py`](../src/p06/schemas/candidate.py) | **Models:** `SkuVersionBinding`, `ProposedResponseCoverage`, `SpeechCandidate`<br>**Enums:** `TargetScopeMode`, `UnresolvedSkuReason`, `CoverageMode`, `CandidateOrigin`, `CandidateVerificationStatus` | - `ProposedResponseCoverage.is_authoritative` luôn là `False` (P06 chỉ đề xuất, P08/P04 mới chốt sau ACK).<br>- Tách biệt nghiêm ngặt `UNRESOLVED_SKU` khỏi `SHOP_WIDE_POLICY` (`P06-OPEN-5`).<br>- Vòng đời kiểm chứng: chỉ `VERIFIED` mới đủ điều kiện phát TTS; tách biệt `DRAFT` vs `VERIFIED` vs `REJECTED` (`I-02`). |
| [`events.py`](../src/p06/schemas/events.py) | **Models:** `PlaybackCompleted`, `StoryCheckpoint`<br>**Enums:** `PlaybackEventSource`, `ResumeMode` | - Tách bạch nguồn phát `SIMULATED_HARNESS` (`is_simulated=True`, có `simulation_run_id`) vs `P04_MEDIA_CONTROLLER` (`is_simulated=False`, có `p04_evidence_ref`).<br>- Bất biến `I-06`: `StoryCheckpoint` chỉ ghi nhận `last_completed_chunk_id` khi kèm `last_playback_event_id` hợp lệ. |
| [`state.py`](../src/p06/schemas/state.py) | **Models:** `AgentState`, `PlayedTurnSummary`, `RewriteBudgetState`<br>**Enum:** `AgentTurnOutcome`<br>**Constants:** `DEFAULT_PLAYED_HISTORY_WINDOW` (`10`), `MAX_PLAYED_HISTORY_WINDOW` (`100`), `DEFAULT_MAX_REWRITE_RETRIES` (`2`), `MAX_REWRITE_RETRIES_LIMIT` (`5`) | - `is_authoritative_session_state` luôn là `False` (`I-01`/`I-04`: LangGraph state không thay thế state phiên của P08/P09).<br>- Đồng nhất `tenant_id`, `session_id`, `session_epoch`, `active_sku_id` giữa `story_plan` và `story_checkpoint`.<br>- Tách `draft_candidate` (không được `VERIFIED`) khỏi `verified_candidate` (bắt buộc `VERIFIED`) và nhất quán với `turn_outcome`. |

---

## 4. Kết quả Kiểm thử Tự động (`pytest`)

Lệnh kiểm thử chạy trực tiếp trên nhánh `research/p06-autonomous-storytelling` tại commit `f68c801`:

```powershell
.\.venv\Scripts\python.exe -m pytest experiments/sales-intelligence/autonomous-storytelling/tests -v
```

**Kết quả quan sát được:** **`28 passed in 3.10s` (`28/28 PASSED`, `0 failed`)**.

| Bộ kiểm thử | Số test | Trạng thái | Nội dung kiểm chứng chính |
| :--- | :---: | :---: | :--- |
| `tests/unit/test_story_schemas.py` | `11` | `PASSED` | Cấu trúc phân cấp `StoryPlan` / `StoryArc` / `StoryTopic` / `StoryChunk`, JSON roundtrip, `extra="forbid"`, giới hạn `pinned_sku_ids`, liên tục vị trí arc, provenance khi `APPROVED`, chặn chunk rỗng/quá thời lượng |
| `tests/unit/test_candidate_and_events.py` | `8` | `PASSED` | Khóa `ProposedResponseCoverage.is_authoritative == False`, phân tách 4 `TargetScopeMode` (ngăn `UNRESOLVED_SKU` lẫn sang `SHOP_WIDE_POLICY`), vòng đời `DRAFT/VERIFIED/REJECTED`, phân biệt `PlaybackCompleted` thật vs mô phỏng, bất biến `StoryCheckpoint` `I-06` |
| `tests/unit/test_agent_state.py` | `7` | `PASSED` | Chuyển đổi `PlayedTurnSummary.from_playback_completed`, biên `RewriteBudgetState`, bất biến `AgentState` (`is_authoritative_session_state == False`, đồng bộ `StoryPlan`/`StoryCheckpoint`, tách `draft` vs `verified`), tương thích khởi tạo `StateGraph(AgentState)` của LangGraph |
| `tests/contract/test_p05_contract_alignment.py` | `2` | `PASSED` | Căn chỉnh hợp đồng P06 với `P05` (`allow` SKU mật ong, `block` SKU điều `PENDING`) và phát hiện lỗi TOCTOU khi giá/knowledge version bị cũ (`SkuVersionBinding`) |

---

## 5. Ghi chú Mở & Bước Tiếp theo

- **Trạng thái Git tag:** Tag `p06-checkpoint-01-scaffold` đang nằm tại commit `f68c801`; tag `p06-checkpoint-02-pre-implementation` hiện **không tồn tại** trong repository.
- **Phạm vi còn lại:** Các task triển khai `E01-T03..E01-T09` (3-tier `LLMProvider`, dataset synthetic 3 SKU `OCOP: VERIFIED`, `P05KnowledgeAdapter`, memory 4 thành phần + `ScriptFirstBaseline`, LangGraph nodes & CLI runner) cùng toàn bộ lượt chạy thí nghiệm chính thức `P06-E01..E04` vẫn đang ở trạng thái **`NOT STARTED`**.
- **Quản trị mở (`P06-OPEN-6`):** `Owner` và `Reviewer` độc lập của P06 vẫn ở trạng thái **`PENDING ASSIGNMENT`**; kết quả Phase 1 là nền tảng schema/unit/contract test và **chưa** chứng minh năng lực sinh tiếng Việt hay mức độ sẵn sàng production.

---

## 6. Phase 2 Audit Addendum (`2026-11-26`)

> [!NOTE]
> Trước khi triển khai Phase 2 (`E01-T03..T05`), các schema `p06-mock-v0.1` của Phase 1 đã được kiểm toán lại (Wave A -> Pre-Wave B) và gia cố: khắc phục `2 BLOCKER` (`A-BLK-01`: thêm `AgentState.from_graph_result()` ở ranh giới đầu ra LangGraph; `A-BLK-02`: chuyển sang `frozen=True` + chuyển trạng thái nguyên tử `with_approval`/`mark_verified`/`mark_rejected`/`advance_on_playback`/`validated_update`), `3 MAJOR` (`StrictInt`/`StrictBool`, `NonBlankStr`, kiểm định tham chiếu `next_topic_id`/`selected_*`/`draft_chunk`/`played_history`), và `3 MINOR` (sau đó Wave D bổ sung `completed_topic_ids: frozenset`). Bộ test nền Phase 1 tăng từ `28/28` lên `33/33` (tổng toàn bộ P06 sau Phase 2 đạt `92/92`). Chi tiết đầy đủ xem tại [`04-phase2-research-infrastructure-e01-t03-t05-report.md`](./04-phase2-research-infrastructure-e01-t03-t05-report.md).
