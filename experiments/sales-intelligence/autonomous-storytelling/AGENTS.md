# HOSTRA AI — Module P06 (`autonomous-storytelling`) Agent Instructions

> **Phạm vi:** Hướng dẫn tác nghiệp bắt buộc cho mọi AI coding agent (bao gồm Antigravity) làm việc trong module `P06 — Sales Intelligence & Autonomous Storytelling`. Quy tắc cấp repo tại [AGENTS.md](../../../AGENTS.md) luôn có hiệu lực cao hơn khi xảy ra xung đột.

---

## 1. Module Overview

- **Module:** `P06 — Sales Intelligence & Autonomous Storytelling` (`experiments/sales-intelligence/autonomous-storytelling/`).
- **Vòng đời / Cột mốc:** Stage 03 (Technical Research & PoC) · Milestone tham chiếu **`M4`** (Knowledge & Sales Intelligence).
- **Rủi ro trực tiếp:** `R05` (lặp ý / mất mạch sau ngắt), `R08` (bịa thông số, giá, khuyến mãi hoặc claims chưa kiểm chứng), `R13` (độ trễ / chi phí / chất lượng sinh tiếng Việt của LLM).
- **Rủi ro phụ thuộc:** `R03` (budget độ trễ `W1` comment-to-playout P50 <= 7s / P95 <= 10s), `R04` (P07 comment taxonomy), `R06` (`PlaybackCompleted` ACK P04/P08), `R10` (cô lập tenant), `R15` (design/code gap), `R16` (OCOP eligibility P09), `R17` (an toàn thực phẩm & cấm công dụng như thuốc).
- **Gates liên quan:** **`G2`** (kể chuyện không comment, trả lời, grouping, breakpoint, resume), **`G4`** (chặn claims, quyền, OCOP, tenant isolation), **`G6`** (merchant duyệt plan, điều khiển & AI disclosure).

---

## 2. Antigravity Discovery Notice (CRITICAL)

Theo cơ chế phát hiện tùy biến của Antigravity (`agy-customizations`), agent **chỉ quét ngược từ thư mục làm việc hiện tại (`CWD`) lên tới `.git` root** để tự nạp `AGENTS.md` và `.agents/rules/*.md`.

- **Cơ chế kích hoạt từ repo root:** Tệp scoped rule [`.agents/rules/p06-autonomous-storytelling.md`](../../../.agents/rules/p06-autonomous-storytelling.md) với `trigger: model_decision` đã được cấu hình tại repo root để tự động dẫn phiên làm việc về `P06/AGENTS.md` khi ngữ cảnh chạm `autonomous-storytelling/` mà **không sửa global rules** và **không ảnh hưởng `P05`/`P07`** hay làm phình budget rule chung.
- **Quy tắc dự phòng:** Nếu CWD là `hostra-ai/` và rule chưa được nạp, agent làm việc tại P06 **bắt buộc đọc thủ công** tệp `AGENTS.md` này trước khi chỉnh sửa bất kỳ mã nguồn nào (hoặc mở phiên với CWD trong `autonomous-storytelling/`).
- **Giới hạn kỹ thuật:** `AGENTS.md` phải là thuần Markdown (**không** chứa YAML frontmatter) và có kích thước **nghiêm ngặt `< 24,000` bytes** để tránh bị cắt cụt theo dòng.

---

## 3. Project Context (MVP Scope & Constraints)

- **Presenter (`ACR-001` — `CONFIRMED REQUIREMENT`):** **01 ảnh chân dung** có đồng ý hợp lệ của Rights Subject, tạo clip offline bằng **PhotoMaker + Wan2.2 Animate**, đồng bộ khẩu hình khi phát live bằng **MuseTalk 1.5** (`P01–P03`). Không dùng filmed-host, Physical Operator hay Digital Human Marketplace.
- **Sản phẩm (`ACR-002` — `CONFIRMED REQUIREMENT`):** Mỗi phiên giới hạn **2–5 SKU thực phẩm đóng gói** đạt đồng thời `OCOP: VERIFIED` (`P09`) và điều kiện an toàn thực phẩm.
- **Phòng live MVP:** **01 phiên đồng thời**, **HOSTRA Private Live Room** (LiveKit invite-only, viewer subscribe-only), mục tiêu **`720p`, `25–30 FPS`** (`CONFIRMED REQUIREMENT`; năng lực đạt thực tế `TO VALIDATE`). TikTok, Shopee, OBS/RTMP, checkout/GMV là `DEFERRED`.

---

## 4. Source-of-Truth Documents & Governance Precedence

Áp dụng thứ tự ưu tiên sau (không bao giờ vượt rào an toàn/bảo mật):

1. **Root Governance:** [AGENTS.md](../../../AGENTS.md) và [docs/README.md](../../../docs/README.md) (`DRAFT`, `CONFIRMED REQUIREMENT`, `PROPOSED`, `SELECTED FOR PoC`, `TO VALIDATE`, `VALIDATED`, `DEFERRED`).
2. **Stage 01 Architecture Baseline:** [HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx](../../../docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx) (§2–7, `D03`, `D06–D11`, `D16–D17`, `D21`, `D23`, `ACR-001`, `ACR-002`, `ARD-05`, `ARD-06`, `I-01..I-09`).
3. **Stage 02 Risk Assessment:** [HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx](../../../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx) (`R05`, `R08`, `R13` và `R03/R04/R06/R10/R15/R16/R17`).
4. **Stage 03 Technical Research & PoC Plan:** [HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx](../../../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx) (§2, §4, §5 `P06.1–P06.14`, §6, §8–9, §12–14, `W0–W3`, `G1–G6`).
5. **Approved Frontend Packages & Decisions:** [DECISIONS.md](../../../docs/product/frontend/DECISIONS.md) và các gói `v0.2` (`Story Planner & Live Session`, `Knowledge & Claims`, `Live Control Room`, `Products & OCOP`).

> [!WARNING]
> **Khoảng trống tài liệu:** `HOSTRA_AI_Project_Overview_Proposal_v1.0.docx` **không tồn tại** trong repo (không suy đoán). Stage 04 `HOSTRA-API-001` & `HOSTRA-DB-001` (`PROPOSED/DRAFT`) hiện chỉ có trên nhánh `research/p07-comment-understanding`, **chưa có** trên `research/p06-autonomous-storytelling`; phần đối chiếu đã lưu tại [context_and_dependencies.md](./research/context_and_dependencies.md).

---

## 5. Mandatory Reading Order for New Agents

1. Root [AGENTS.md](../../../AGENTS.md) và `P06/AGENTS.md` (tệp này).
2. [docs/01-p06-structure-and-mission-guide.md](./docs/01-p06-structure-and-mission-guide.md), [docs/02-open-decisions-alignment-and-e01-plan.md](./docs/02-open-decisions-alignment-and-e01-plan.md) và [docs/README.md](./docs/README.md).
3. [P06/README.md](./README.md) (bài toán, `P06-E01..E04`, gates, checklist).
4. [research/context_and_dependencies.md](./research/context_and_dependencies.md), [research/problem_definition.md](./research/problem_definition.md) và [research/methodology.md](./research/methodology.md).
5. Hợp đồng P05 tại [schemas.py](../knowledge-verification/schemas.py), [publication_gate.py](../knowledge-verification/publication_gate.py), và [research/decision_log.md](./research/decision_log.md).

---

## 6. Directory Structure & Responsibilities

Khung tài liệu/cấu hình đã sẵn sàng; mã nguồn Python `src/p06/` và các tệp cấu hình/rubric bổ sung được triển khai theo lộ trình `E01-T01..T09`:

```text
autonomous-storytelling/
├── AGENTS.md                 # Quy tắc tác nghiệp P06 (thuần Markdown, không frontmatter, <24KB)
├── README.md                 # Tổng quan module, giả thuyết, checklist & điều hướng
├── pyproject.toml / .env.example
├── docs/
│   ├── README.md
│   ├── 00-context-and-scaffolding-report.md
│   ├── 01-p06-structure-and-mission-guide.md
│   └── 02-open-decisions-alignment-and-e01-plan.md
├── research/                 # problem_definition.md, research_questions.md, methodology.md, context_and_dependencies.md, decision_log.md, literature_review.md
├── configs/
│   ├── default.yaml
│   ├── experiments/          # p06_e01.yaml .. p06_e04.yaml
│   └── models/               # mock.yaml, ollama_qwen3_1.7b.yaml, ollama_qwen3_4b.yaml, gemini_flash.yaml
├── data/                     # Dữ liệu synthetic/curated có provenance (không secret/PII)
├── prompts/                  # Prompt templates có version & SHA-256 hash
├── notebooks/                # CHỈ khám phá/visualize; CẤM chứa core business logic
├── src/p06/                  # Toàn bộ logic tái sử dụng (experiments phải import từ đây)
│   ├── schemas/              # StoryPlan, StoryArc, StoryChunk, SpeechCandidate (p06-mock-v0.1), ProposedResponseCoverage
│   ├── providers/            # base.py, mock_provider.py, ollama_provider.py, gemini_provider.py, factory.py
│   ├── planning/             # StoryPlanner, arc sequencing, mandatory topic coverage tracker
│   ├── agent/nodes/          # LangGraph StateGraph nodes (load, plan, draft, verify_p05, rewrite, bridge)
│   ├── memory/               # 4-part memory: PlayedHistory (W∈{5,10,20}), TopicCoverage, ViewerContext, SemanticMemory
│   ├── guardrails/           # Fail-closed P05 gate adapter, prohibited_echo_guard, fallback selector
│   ├── adapters/mocks/       # Mock P05/P07/P08/P04 adapters (cô lập khỏi production)
│   ├── baselines/            # Script-first baseline đối chiếu công bằng
│   └── simulation/           # Fake clock runner cho kịch bản 10–30 phút & interrupt/resume
├── experiments/              # Runner độc lập cho p06_e01..p06_e04
├── evaluation/
│   ├── metrics/              # Automatic metrics (coverage, repetition, replay_count, latency, tokens)
│   └── rubrics/              # human_eval_rubric_v0.1.md (6 tiêu chí 1–5 + pilot calibration)
├── tests/                    # unit/, contract/, integration/
├── runs/                     # runs/<exp_id>/<run_id>/ (manifest.json + logs + failures/)
└── reports/                  # Báo cáo tổng hợp so baseline & đề xuất GO/CHANGE/NO-GO/INCONCLUSIVE
```

**Quy tắc thư mục bắt buộc:** `notebooks/` tuyệt đối **không** chứa core business logic; các script trong `experiments/` phải import module từ `src/p06/`.

---

## 7. Architectural Boundaries & Invariants (`I-01`–`I-09`)

- **`P05` (Knowledge & Publication Gate):** Sở hữu `ProductFact`, `EvidenceChunk`, `ClaimRegistryEntry`, `PublicationGate`. **P06 tuyệt đối không** tự duyệt claim, nâng trạng thái tri thức hay vượt mặt `PublicationGate` (`I-02`). Draft chưa qua `P05` không bao giờ là `VerifiedSpeechCandidate`.
- **`P06` (Autonomous Storytelling):** Sở hữu lập nháp `StoryPlan`, sinh `StoryChunk` / câu trả lời dự kiến, theo dõi coverage từ lịch sử đã phát, chống lặp, bounded rewrite khi P05 từ chối, và câu chuyển tiếp (`bridge`). **P06 không** điều khiển playout, giữ state phiên chính thức hay tự kích hoạt TTS/live.
- **`P07` (Comment Understanding):** Sở hữu chuẩn hóa, moderation (`4`), intent (`9`), phân giải SKU (`7`) và `ResponseGroupProposal`. P06 không tự phân loại lại raw comment bỏ qua `P07`.
- **`P08/P09` (Session Orchestration):** **Single logical writer** cho `LiveSession`, `Active SKU`, `SpeechTurn` FSM, `ResponseGroup`, `StoryCheckpoint` (`I-01`, `I-04`, `I-07`). LangGraph state **không** thay thế `P08`; `referenced_sku_id` không tự đổi `Active SKU` (`D10`, `I-04`).
- **`P04` (Playout Authority):** Nguồn chân lý duy nhất về phát sóng (`I-03`, `I-06`). LLM/TTS/MuseTalk/LangGraph checkpoint **không đồng nghĩa** `PlaybackCompleted`. P06 chỉ cập nhật `covered_topics`/`played_history` khi nhận `PlaybackCompleted` ACK và không tự replay lượt có trạng thái `UNKNOWN`.

---

## 8. Core P06 Design Rules (`P06-OPEN-1..6` Alignment)

1. **3-Tier Provider-Agnostic Testing (`P06-OPEN-1`):**
   - `MockLLMProvider` (`unit_test` only — deterministic offline CI/tests).
   - `OllamaLocalProvider` (`local_smoke_test` trên CPU `Qwen3 1.7B/4B` — kiểm tra luồng & JSON/prompt thực tế trên máy CPU-only).
   - `GeminiAPIProvider` (`formal_experiment` `Flash/Flash-Lite` — bắt buộc xác minh model ID, quota, pricing & DPA/terms trước khi chạy; chỉ gửi dữ liệu synthetic hoặc đã cấp quyền).
   - **Cấm:** Tuyệt đối **không gộp** lượt chạy `Ollama` và `Gemini` vào cùng bảng benchmark; **không coi** kết quả pass trên `MockLLMProvider` là bằng chứng chất lượng tiếng Việt hay hiệu năng LLM. Mọi thay đổi model đi qua `configs/models/*.yaml` + `ProviderFactory`, không sửa graph LangGraph.
2. **4-Part Memory & Rule-Based Repetition (`P06-OPEN-2`):**
   - Bốn thành phần tách bạch: (1) `Short-term Played History` với cửa sổ **`W ∈ {5, 10, 20}`** cấu hình qua YAML (cấm hard-code); (2) `Global Topic Coverage` (theo `StoryPlan`); (3) `Session-scoped Viewer Context` (`D11/D23`, xóa khi kết thúc phiên); (4) `Optional Semantic Memory` (interface mở rộng).
   - **Rule-based first:** Dùng đối chiếu `(intent, sku_id, covered_claim_ids)` + n-gram/lexical overlap trước; chỉ bật embedding comparator khi rule-based không đủ; **không** dùng `pgvector` trong PoC standalone.
3. **Recap Policy (`P06-OPEN-3`):**
   - Áp dụng **periodic + context-aware Q&A**, **tuyệt đối không** recap theo từng sự kiện viewer join phòng, phải bám `semantic_breakpoint` và **trì hoãn (`deferred`) qua khỏi `P06-E01`** (chưa bật trong E01).
4. **Human Evaluation (`P06-OPEN-4`):**
   - Sử dụng rubric 6 tiêu chí thang 1–5 tại [evaluation/rubrics/human_eval_rubric_v0.1.md](./evaluation/rubrics/human_eval_rubric_v0.1.md); bắt buộc **pilot calibration** trước khi khóa ngưỡng chất lượng (`TO VALIDATE`). **Hard constraints** (factual grounding, OCOP, từ cấm, replay `0`) **không bao giờ** được bù trừ bằng điểm chất lượng mềm.
5. **Cross-Module Contract Rules (`P06-OPEN-5`):**
   - Hỗ trợ đủ 4 `TargetScopeMode`: `SINGLE_SKU`, `MULTI_SKU_COMPARE`, `SHOP_WIDE_POLICY`, và `UNRESOLVED_SKU` (**tách biệt nghiêm ngặt** `UNRESOLVED_SKU` khỏi `SHOP_WIDE_POLICY`).
   - P06 chỉ phát hành **`ProposedResponseCoverage`**; trạng thái độ phủ/lịch sử chính thức chỉ cập nhật khi nhận **`P04 PlaybackCompleted`** hợp lệ.
   - Dùng hợp đồng mock có phiên bản **`p06-mock-v0.1`** trong giai đoạn PoC cho tới khi `packages/contracts/` đóng băng.
6. **Ownership (`P06-OPEN-6`):**
   - `Owner` và `Reviewer` độc lập của P06 hiện vẫn giữ trạng thái **`PENDING ASSIGNMENT`**; không tự điền tên hay tự ký duyệt `VALIDATED`.

---

## 9. Dependency Status, Experiment Order & Workflow

- **Phụ thuộc:** `P05` (`IN EXPERIMENT`, gọi qua adapter đọc-chỉ-đọc, không copy/fork), `P07` (`PROPOSED v0.1.3`), `P08/P09`, `P04`, `P02` (`NOT STARTED`). Dùng mock chuẩn hợp đồng `p06-mock-v0.1` trong `src/p06/adapters/mocks/` và tách biệt `Mock != Production Validated`.
- **Thứ tự thí nghiệm:** Giữ mã `P06-E01..E04`, chạy theo phụ thuộc **`E01 -> E04 -> E03 -> E02 -> Integration`**:
  1. `P06-E01` (No-comment 10–30m, sweep `W ∈ {5, 10, 20}`, Recap OFF).
  2. `P06-E04` (Bounded rewrite `<= K` & fail-closed fallback).
  3. `P06-E03` (Interrupt & resume 10 vị trí, `0` replay chunk đã hoàn tất).
  4. `P06-E02` (10–20 paraphrase câu hỏi lặp, đúng facts & chống lặp).
- **Phased Workflow:** `Phase 1 (Contract Audit)` -> `Phase 2 (Dataset, Prompts, Rubric)` -> `Phase 3 (src/p06/ + Tier 1 tests)` -> `Phase 4 (E01->E04->E03->E02 runs)` -> `Phase 5 (Blind QA, G2/G4/G6, reports/)`.

---

## 10. Testing, Reproducibility & Coding Conventions

- **Phân tầng test:** `tests/unit/`, `tests/contract/` (tương thích DTO P05/P07/P08 `p06-mock-v0.1`), `tests/integration/` (`MockLLMProvider`). **Tier 1 deterministic tests (`MockLLMProvider`) phải pass 100% trước khi gọi Ollama hay Gemini API.**
- **Reproducibility:** Mọi lượt chạy xuất `runs/<exp_id>/<run_id>/` gồm `manifest.json`, logs và toàn bộ `failures/`.
- **Stack & Bảo mật:** Python `3.11–3.13`, `from __future__ import annotations`, **Pydantic v2** cho boundary schemas, type hints đầy đủ. Tuyệt đối không commit `.env`, API keys, PII hay gửi dữ liệu merchant thật khi chưa xong DPA/terms review.

---

## 11. Allowed vs Prohibited Actions (12 Mandatory Rules)

1. **Bắt buộc đọc** `AGENTS.md` (root + P06) và `README.md` trước khi chỉnh sửa mã nguồn.
2. **Xác định rõ** mã thí nghiệm mục tiêu (`P06-E01..E04`) trước khi viết mã mới.
3. **Đọc trước** `methodology.md` và contracts liên quan (`P05/P07/P08`) trước khi sửa schema/node.
4. **Không sửa** tệp ngoài phạm vi `autonomous-storytelling/` trừ khi được giao nhiệm vụ rõ ràng.
5. **Không âm thầm thay đổi** quyết định kiến trúc đã khóa (bỏ LangGraph, tự sửa Active SKU, tự duyệt claim).
6. **Không bịa đặt** kết quả thí nghiệm, metrics, điểm chấm người thật hay điền `0` giả cho chỉ số thiếu.
7. **Không gắn nhãn `VALIDATED`** khi chưa có manifest tái lập và sign-off của reviewer độc lập (`PENDING ASSIGNMENT`).
8. **Không commit** API keys, credentials, secrets hoặc dữ liệu riêng tư thiếu quyền sử dụng.
9. **Giữ mã nguồn** đơn giản, rõ kiểu (`typed`), module hóa; không tạo wrapper thừa hoặc `.py` rỗng giữ chỗ.
10. **Giữ mỗi thí nghiệm** chạy lại được độc lập qua cấu hình (`configs/`) và manifest rõ ràng.
11. **Ghi nhận quyết định kỹ thuật** và giả định mở vào [research/decision_log.md](./research/decision_log.md).
12. **Cô lập hoàn toàn** `src/p06/adapters/mocks/` khỏi logic có thể promote sang production.

---

## 12. Current Research Progress & Definition of Done

| Hạng mục | Trạng thái | Ghi chú |
| :--- | :---: | :--- |
| Tài liệu nền, `P06-OPEN-1..6`, Rubric v0.1, Model configs & Kế hoạch E01 (`02-...`) | `IN RESEARCH` | Hoàn tất alignment tài liệu & kế hoạch `E01-T01..T09` |
| Phase 3 (`src/p06/` core, 3-tier providers, LangGraph, P05 adapter, Mocks, Tests) | `NOT STARTED` | Triển khai theo `E01-T01..T08` |
| `P06-E01`, `P06-E04`, `P06-E03`, `P06-E02` & Phase 5 Handoff `M4` | `NOT STARTED` | Chưa có manifest trong `runs/`; Owner/Reviewer `PENDING ASSIGNMENT` |

- **Done một thí nghiệm:** Runner tái lập, tests pass, đủ `manifest.json` + logs + `failures/` trong `runs/`, đối chiếu baseline & giới hạn mock/synthetic; kết luận `GO/CHANGE/NO-GO/INCONCLUSIVE` theo bằng chứng thật.
- **Promote (`M4` -> Stage 06):** Reviewer duyệt `GO`, bỏ toàn bộ mock, đóng băng `packages/contracts/` thay `p06-mock-v0.1`, chuyển logic thuần sang `apps/api/src/hostra_api/modules/sales/` có consumer contract tests.
