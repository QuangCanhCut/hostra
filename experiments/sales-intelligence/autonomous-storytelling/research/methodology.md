# P06 — Phương pháp luận & Lộ trình thực nghiệm (Methodology)

**Module:** P06 — Sales Intelligence & Autonomous Storytelling  
**Quy chuẩn áp dụng:** `experiments/README.md` (§4, §5, §6, §7) & Stage 03 (`P06.7–P06.12`)  
**Trạng thái:** `IN RESEARCH` *(Đã hiện thực hóa runner & evaluator E01-T08 trong `src/p06/{evaluation,runner}/` — chỉ chạy Mock Tier 1; benchmark `Ollama`/`Gemini` & Human Eval `E01-T09` vẫn `NOT STARTED`)*

---

## 1. Chuẩn thiết kế thí nghiệm 14 mục (14-Point Experiment Design Standard)

Trước khi thực thi bất kỳ thí nghiệm nào trong bộ `P06-E01`..`P06-E04`, thiết kế thí nghiệm phải được ghi thành tài liệu đặc tả đầy đủ 14 mục bắt buộc dưới đây (không bỏ qua mục nào kể cả với kịch bản nhỏ):

1. **Research Question (`RQ`):** Câu hỏi nghiên cứu cụ thể và phạm vi giải quyết.
2. **Hypothesis (`H`):** Giả thuyết có thể bác bỏ và quy tắc quyết định (`GO` / `CHANGE` / `NO-GO` / `INCONCLUSIVE`).
3. **Experimental Scope & Mock Boundaries:** Tuyên bố rõ thành phần nào chạy thật, thành phần nào đang được mock (`P04` ACK, `P05` gate, `P07`/`P08` scheduler, `p06-mock-v0.1`) và giới hạn của môi trường PoC.
4. **Baseline Definition:** Phương pháp đối chiếu (ví dụ `Script-first` hoặc phiên bản không có viewer-context / không có memory window) được khóa cấu hình trước khi chạy.
5. **Independent Variables (Biến thay đổi):** Các tham số/chiến lược thử nghiệm (ví dụ: kích thước cửa sổ `W ∈ {5, 10, 20}`, chế độ rule-based vs. optional embedding, số retry `K`, bật/tắt `viewer_id` history, loại kịch bản lỗi).
6. **Controlled / Fixed Variables (Biến giữ cố định):** Bộ SKU, `StoryPlan`, `EvidenceBundle`, model/checkpoint/revision, `temperature`, system prompt gốc, workload, `contract_version`.
7. **Dataset & Scenario Specification:** Nguồn dữ liệu, quyền sử dụng, số lượng mẫu/kịch bản, phân tách tập (tuyệt đối không để paraphrase cùng nguồn lọt từ tập thiết kế prompt sang tập test), tỷ trọng dữ liệu thật vs synthetic và checksum.
8. **Execution Procedure:** Quy trình từng bước tái lập được (từ khởi tạo state, nạp `EvidenceBundle`, bơm sự kiện comment/ACK, tới lưu trace).
9. **Iteration & Seed Policy:** Số lượt lặp cho mỗi cấu hình, ghi nhận `seed` (nếu provider hỗ trợ) và lý giải tính bất định của LLM.
10. **Metrics & Ground Truth Protocol:** Định nghĩa công thức, đơn vị đo, công cụ tự động vs rubric người chấm mù 6 tiêu chí, và nguồn nhãn chuẩn độc lập.
11. **Hard Gates & Acceptance Rules:** Các cổng an toàn `0 vi phạm` (`G4`, `G3`) được kiểm tra trước tiên; **không dùng điểm chất lượng mềm để bù cho vi phạm quyền/chứng cứ/an toàn**.
12. **Artifact & Logging Schema:** Đường dẫn lưu `manifest.json`, graph trace, transcript, danh sách ứng viên bị loại (`waste`), telemetry đầy đủ và phiếu chấm mù.
13. **Risks & Confounding Factors:** Các yếu tố gây nhiễu (như độ dài câu ảnh hưởng latency, khác biệt giữa TTS giả lập và tốc độ nói thật, phần cứng CPU khi smoke test local) và cách kiểm soát.
14. **Conclusion & Next-Step Template:** Khung ghi nhận kết luận theo đúng bằng chứng thực đo, không suy diễn vượt phạm vi workload đã thử.

---

## 2. Kiến trúc Thực nghiệm Cốt lõi (Cập nhật `2026-11-26`)

### 2.1. Kiến trúc 3 tầng `LLMProvider` & Quy tắc phân tách thực nghiệm (`DR-P06-004`)

Tất cả lời gọi sinh ngôn ngữ trong P06 đi qua interface trừu tượng `LLMProvider` và `ProviderFactory`, tách biệt nghiêm ngặt **3 tầng môi trường** — **nghiêm cấm** trộn lẫn số liệu giữa các tầng khi báo cáo:

| Tầng | Provider | Mục đích & Phạm vi được phép | Ràng buộc cứng |
| :--- | :--- | :--- | :--- |
| **Tier 1 (`unit_test`)** | `MockLLMProvider` | Kiểm thử tất định luồng trạng thái LangGraph, conditional routing, cấu trúc Pydantic, cơ chế `bounded rewrite` (`K`), xử lý lỗi schema/timeout và `SAFE_FALLBACK`. | **0 tuyên bố về chất lượng kể chuyện tiếng Việt** (`naturalness`, `persuasiveness`, `coherence`); chạy mặc định trong CI không mạng và unit/contract test. |
| **Tier 2 (`local_smoke_test`)** | `OllamaLocalProvider` | Chạy cục bộ trên CPU với **`Qwen3 4B Instruct`** hoặc **`Qwen3 1.7B`** phục vụ phát triển prompt, kiểm tra tính đúng của pipeline và smoke test trước khi tốn quota cloud. | **Không giả định latency production** từ tốc độ CPU local; **tuyệt đối không gộp kết quả Ollama với Gemini** trong bảng so sánh chính thức nếu khác điều kiện/mục tiêu benchmark. |
| **Tier 3 (`formal_experiment`)** | `GeminiAPIProvider` | Chạy thực nghiệm định lượng chính thức trên nhóm model **`Flash` / `Flash-Lite`** cho `P06-E01`..`P06-E04`. | Trước khi chạy phải xác minh **model ID, quota, đơn giá, chất lượng structured output tiếng Việt và privacy/DPA**; chỉ dùng **dữ liệu synthetic hoặc dữ liệu đã được phê duyệt quyền**. |

**Telemetry bắt buộc trên mỗi lượt chạy (`manifest.json` & trace):**
Mỗi lượt chạy benchmark/smoke test đều phải ghi đủ các trường:
`model_id`, `quantization`, `cpu_ram` (`cpu_model`, `ram_gb`), `context_window`, `sampling_params` (`temperature`, `top_p`, `seed`, ...), `prompt_version`, `latency` (cold/warm P50/P95), `token_usage` (`input_tokens`, `output_tokens`, kể cả waste), `provider_config` (tier, endpoint/timeout/retry), và `contract_version` (ví dụ `p06-mock-v0.1`).

---

### 2.2. Kiến trúc Memory 4 thành phần & Anti-Repetition (`DR-P06-006`)

P06 áp dụng kiến trúc bộ nhớ phiên 4 thành phần (tồn tại giới hạn trong `(session_id, session_epoch)` theo `D11`/`D23`) với chiến lược **rule-based detection trước**:

1. **`Short-term Played History`:** Lưu lịch sử các chunk đã thực sự nhận `PlaybackCompleted` ACK trong cửa sổ gần nhất có kích thước cấu hình **`W ∈ {5, 10, 20}`** (cùng cấu hình baseline đối chiếu). Dùng để phát hiện trùng lặp cấu trúc mở câu, khung ý, hoặc cụm diễn đạt gần kề.
2. **`Global Topic Coverage`:** Theo dõi toàn phiên tập các `mandatory_topics`, `sku_id`, `covered_claim_ids` và `evidence_ids` đã được phát hoàn tất qua `PlaybackCompleted` ACK (bất biến theo `P04`, không cập nhật từ graph checkpoint).
3. **`Session-scoped Viewer Context`:** Lưu lịch sử tương tác theo `(viewer_id / guest_session_id, intent, sku_id)` trong phiên để tránh lặp nguyên văn khi cùng người xem hoặc nhiều người xem hỏi lặp cùng một chủ đề giá/ship/nguồn gốc.
4. **`Optional Semantic Memory`:** Thành phần tùy chọn dùng embedding + cosine similarity làm **biến đối chiếu benchmark** (so sánh với rule-based thuần trong `P06-E01`/`P06-E02`). **Không triển khai `pgvector`** trong PoC độc lập này; không khóa trước ngưỡng similarity hay giá trị `W` trước khi có số liệu thực nghiệm.

---

### 2.3. Chính sách Recap (`DR-P06-007`, `P06-OPEN-3`)

- Áp dụng mô hình **Periodic Recap + Context-aware Question Response**.
- **Quy tắc cấm:** **KHÔNG BAO GIỜ** kích hoạt recap cho mỗi sự kiện người xem mới vào phòng (`viewer join`).
- Câu recap phải ngắn gọn, căn đúng `semantic_breakpoint` trong `StoryArc` và không làm gián đoạn mạch trình bày tự nhiên.
- Tần suất định kỳ và điều kiện kích hoạt chính xác là **biến nghiên cứu được hoãn qua sau `P06-E01`** (đánh giá từ `P06-E03` trở đi và rà soát cùng Product Owner).

---

### 2.4. Khung đánh giá con người 6 tiêu chí (`DR-P06-008`, `P06-OPEN-4`)

Đánh giá chất lượng kể chuyện sử dụng thang điểm **`1–5`** trên **6 tiêu chí** định nghĩa tại `evaluation/rubrics/human_eval_rubric_v0.1.md`, kết hợp song song với bộ metric tự động:

1. `narrative_coherence` — Độ liền mạch của mạch kể chuyện và logic chuyển ý.
2. `naturalness` — Độ tự nhiên văn phong livestream bán hàng tiếng Việt (không sặc mùi dịch máy hay kịch bản cứng).
3. `persuasiveness` — Tính thuyết phục thương mại gắn với giá trị thực & bằng chứng hợp lệ (không phô trương/sai sự thật).
4. `context_relevance` — Độ bám sát ngữ cảnh bình luận, `Active SKU` / `Referenced SKU` và trạng thái phiên hiện tại.
5. `transition_quality` — Độ mượt của câu chuyển tiếp (`bridge`) khi ngắt mạch trả lời bình luận và nối lại `StoryArc`.
6. `repetition_quality` — Mức độ đa dạng diễn đạt, tránh lặp ý vô ích (bao gồm cách xử lý câu hỏi paraphrase lặp lại).

**Nguyên tắc hiệu chỉnh & không bù trừ:**
- Trước khi chạy formal benchmark ở Phase 4–5, phải thực hiện **pilot calibration** giữa các người chấm để rà soát độ nhất quán và khóa ngưỡng chấp nhận chính thức (`TO VALIDATE`).
- **Tính không bù trừ của Hard Constraints:** Mọi vi phạm Hard Gate (`G3` Replay chunk đã phát, `G4` Sai giá/fact/SKU/claim cấm/OCOP chưa `VERIFIED`/quyền hết hạn) dẫn tới đánh rớt trực tiếp mẫu/cấu hình đó; điểm cao ở 6 tiêu chí mềm tuyệt đối không bù trừ cho vi phạm hard gate.

---

## 3. Trình tự thực hiện thí nghiệm đề xuất (Recommended Execution Sequence)

Mặc dù mã định danh chính thức từ Stage 03 giữ nguyên là `P06-E01`..`P06-E04`, trình tự triển khai và chạy thực nghiệm tối ưu được sắp xếp theo phụ thuộc kỹ thuật để phát hiện rủi ro sớm nhất:

```text
P06-E01 (Core Storytelling Loop & Baseline; W ∈ {5, 10, 20})
   │
   ▼
P06-E04 (Safety Hardening, Bounded Rewrite & Fail-Closed)
   │
   ▼
P06-E03 (Interrupt, Playback-Grounded Checkpoint/Resume & Post-E01 Recap Exploration)
   │
   ▼
P06-E02 (Viewer & Intent-Aware Repeated Q&A; Multi-SKU / Policy / Unresolved Alignment)
   │
   ▼
Integration Readiness Testing (P05 + P07 + P08 + P04 Mock/Real Contract Check)
```

**Lý do sắp xếp trình tự:**
1. **`P06-E01` trước tiên:** Xây dựng vòng lặp sinh cốt lõi (`StoryPlanner` + LangGraph + 4-part Memory với `W ∈ {5, 10, 20}`), thiết lập baseline `Script-first` và kiểm chứng khả năng kể chuyện dài hơi khi không có bình luận (chưa bật Periodic Recap).
2. **`P06-E04` ngay bước thứ hai:** Gia cố an toàn (`R08`, `G4`) và chặn vòng lặp vô hạn sớm. Việc xác minh bounded rewrite và fail-closed trước khi thêm logic ngắt mạch phức tạp giúp đảm bảo mọi thử nghiệm về sau đều chạy trên nền graph an toàn.
3. **`P06-E03` ở bước thứ ba:** Khi luồng sinh và kiểm chứng đã ổn định, kiểm tra cơ chế phân đoạn `semantic_breakpoint`, cập nhật `StoryCheckpoint` từ `PlaybackCompleted` ACK, tạo câu `bridge` sau khi bị comment ngắt, và khảo sát biến `Periodic Recap` (hậu `E01`).
4. **`P06-E02` ở bước thứ tư:** Mở rộng bộ nhớ theo `viewer_id` và `intent` để xử lý các đợt câu hỏi paraphrase lặp lại, kết hợp 4 chế độ `TargetScopeMode` và `ProposedResponseCoverage` (`p06-mock-v0.1`) mà không đánh mất độ chính xác thực tế.
5. **Integration Testing cuối cùng:** Kiểm tra tương thích hợp đồng đầu vào/đầu ra với `P05` thật (từ `knowledge-verification`), `P07`, `P08` và `P04` trước khi đề xuất chuyển giao sang backend module.

---

## 4. Khung đánh giá 13 chỉ số (Evaluation Metrics Framework)

Tất cả metric dưới đây phải được báo cáo **theo từng tầng provider, từng nhóm đầu vào và từng cấu hình** (phân bố P50/P95 hoặc trung bình + độ lệch, kèm số lượng mẫu lỗi), không gộp thành một con số duy nhất làm mờ các ca thất bại.

> **Cảnh báo nguyên tắc Ground Truth:** Tuyệt đối **KHÔNG** dùng đầu ra của mock verifier hoặc chính LLM sinh lời thoại làm nguồn chuẩn duy nhất để chấm `Factual Accuracy` hay `Unsupported Claim Rate`. Mọi đánh giá tính đúng đắn phải đối chiếu với bộ nhãn chuẩn được gán độc lập bởi con người (`gold annotation`) trên `ProductFact` và `EvidenceBundle` gốc.

> **Cảnh báo nguyên tắc Ngưỡng (Thresholds):** Các **Hard Safety Gates** yêu cầu tuyệt đối `0` vi phạm trên bộ kịch bản kiểm thử đã định nghĩa. Toàn bộ các ngưỡng về chất lượng, độ trễ và chi phí chưa được phê duyệt trong Stage 03 đều mang trạng thái **`TO VALIDATE`** — **nghiêm cấm** tự bịa đặt con số mục tiêu đạt chuẩn trước khi nhóm hoàn tất pilot calibration và phê duyệt.

| STT | Tên Metric | Phương pháp đo | Đơn vị / Công thức | Nguồn Ground Truth | Trạng thái Ngưỡng |
| :-: | :--- | :--- | :--- | :--- | :--- |
| 1 | `Mandatory Topic Coverage` | Tự động + Kiểm tra lại thủ công | `% = (Số mandatory topics đã có PlaybackCompleted ACK / Tổng số mandatory topics trong StoryPlan) × 100` | Danh sách `mandatory_topics` trong `StoryPlan` + đối chiếu transcript đã phát | `TO VALIDATE` (Cần chốt với Product/Owner) |
| 2 | `Semantic Repetition Rate` | Tự động (rule-based n-gram/intent/claim + optional embedding cosine similarity trên cửa sổ `W ∈ {5, 10, 20}`) & Human Blind Rubric (`repetition_quality`) | `% số chunk hoặc cặp câu trong cửa sổ W bị đánh dấu lặp ý vô ích / Tổng số chunk phát` | Nhãn đánh giá mù của người chấm & log `intent/SKU/covered_claims` | `TO VALIDATE` |
| 3 | `Factual Accuracy` | Human / Independent Gold Annotation | `% số lời thoại khớp hoàn toàn với ProductFact & EvidenceChunk (giá, khối lượng, xuất xứ, thành phần, HSD)` | Bộ nhãn chuẩn độc lập (`gold annotation`) trích từ `ProductFact` & tài liệu gốc | **Hard Gate (0 sai lệch giá/SKU/fact trên bộ test định nghĩa)** |
| 4 | `Unsupported Claim Rate` | Independent Gold Annotation + Audit đối chiếu `P05` | `% số speech candidates chứa claim không có `evidence_id` hợp lệ, sai SKU, hoặc thuộc `PROHIBITED` / OCOP chưa `VERIFIED`` | Danh mục `ClaimRegistryEntry` & `EligibilitySnapshot` chuẩn | **Hard Gate: 0 lọt qua cổng publish (`G4`)** |
| 5 | `Completed Chunk Replay Count` | Tự động (Event/ACK Audit) | `Số nguyên (Count)`: Số lần một `chunk_id` đã nhận `PlaybackCompleted` ACK bị xếp lịch/sinh lặp lại nguyên trạng | Nhật ký `PlaybackCompleted` ACK & log quyết định của `StoryCheckpoint` | **Hard Gate: `= 0` (`G3`, `P06-E03`)** |
| 6 | `Resume Correctness` | Tự động + Human Rubric (`transition_quality`, `context_relevance`) | `% số kịch bản ngắt mạch quay lại đúng topic/điểm dở trong StoryPlan (không nhảy cóc, không lặp ý đã nói)` | Bản đồ `StoryArc` chuẩn và trạng thái ACK trước thời điểm ngắt | `TO VALIDATE` (Kỳ vọng không bỏ sót/nhảy sai phần chưa phát) |
| 7 | `Narrative Coherence` | Human Blind Rubric (thang `1–5`, `evaluation/rubrics/human_eval_rubric_v0.1.md`) | Điểm thang `1–5` cho `narrative_coherence` (kết hợp `transition_quality` khi có ngắt mạch) | Phiếu chấm mù của người đánh giá (không biết cấu hình nào sinh ra transcript) | `TO VALIDATE` *(Khóa ngưỡng sau pilot calibration)* |
| 8 | `Naturalness` | Human Blind Rubric (thang `1–5`, `evaluation/rubrics/human_eval_rubric_v0.1.md`) | Điểm thang `1–5` cho `naturalness` (và các trục bổ trợ `persuasiveness`, `context_relevance` trong rubric 6 tiêu chí) | Phiếu chấm mù của người bản ngữ / reviewer thương mại | `TO VALIDATE` *(Khóa ngưỡng sau pilot calibration)* |
| 9 | `Rewrite Rate` | Tự động (Graph Trace) | `% = (Số lượt sinh cần ít nhất 1 vòng rewrite sau kiểm tra P05 / Tổng số lượt sinh) × 100` | Log chuyển trạng thái node trong LangGraph | `TO VALIDATE` |
| 10 | `Retry Count` | Tự động (Graph Trace) | Phân bố số lần lặp `rewrite` trên mỗi turn (Min / Median / P95 / Max, đối chiếu trần `K`) | Log vòng lặp trong LangGraph state | `TO VALIDATE` (Cần bị chặn cứng bởi trần `K`) |
| 11 | `Generation Latency P50/P95` | Tự động (Wall-clock timer) | `giây (s)` hoặc `ms` tính từ khi nhận yêu cầu sinh tại P06 tới khi xuất `VerifiedSpeechCandidate` (tách riêng cold/warm và thời gian rewrite, tách theo tier `OllamaLocal` vs `GeminiAPI`) | Timestamp hệ thống trong trace (tách biệt với thời gian mock network/TTS) | `TO VALIDATE` (Đóng góp vào budget toàn luồng `W1`: P50 ≤ 7s, P95 ≤ 10s) |
| 12 | `Token Consumption` | Tự động (Provider usage metadata) | Số lượng `input_tokens` và `output_tokens` trên mỗi turn (bao gồm cả token của các lần retry/draft bị loại bỏ) | API usage response từ LLM adapter | `TO VALIDATE` |
| 13 | `Estimated LLM Cost` | Tự động (Tính toán từ Token & Bảng giá công khai tại ngày chạy) | `USD / 1000 turns` và `USD / phiên 60–120 phút` (ghi rõ ngày tham chiếu bảng giá; `0 USD` chỉ tính riêng phần API đối với local smoke test) | Token log × đơn giá model công bố tại thời điểm chạy | `TO VALIDATE` |

---

## 5. Lộ trình triển khai 5 giai đoạn (5-Phase Implementation Roadmap)

| Giai đoạn | Tên giai đoạn | Các đầu việc trọng tâm | Trạng thái hiện tại |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **Technical Exploration** | Khảo sát `GeminiAPIProvider` (`Flash`/`Flash-Lite`) & `OllamaLocalProvider` (`Qwen3 1.7B/4B`) cho structured output tiếng Việt; thiết kế Pydantic schemas (`StoryPlan`, `StoryChunk`, `SpeechCandidate`, `StoryCheckpoint`, `p06-mock-v0.1`); xây dựng mẫu LangGraph `StateGraph`, conditional edges, bounded retry cycle. | `NOT STARTED` |
| **Phase 2** | **Research Preparation** | Hoàn thiện tài liệu nghiên cứu (`research/`), khóa rubric `human_eval_rubric_v0.1.md`, chuẩn bị bộ dữ liệu 3–5 SKU có nguồn/quyền, kịch bản 10 tình huống ngắt mạch, 10–20 câu hỏi paraphrase; xây dựng baseline `Script-first`, mock dependencies (`P05`/`P07`/`P08`/`P04`) theo `p06-mock-v0.1`. | `IN PROGRESS / PARTIAL` *(Tài liệu `research/` đã rà soát `2026-11-26`; mã nguồn dataset/baseline/mock `NOT STARTED`)* |
| **Phase 3** | **Agent Core Development** | Phát triển `ProviderFactory` 3 tầng, `StoryPlanner`, luồng LangGraph đầy đủ, bộ nhớ 4 thành phần (`W ∈ {5, 10, 20}` + coverage tracker bám `PlaybackCompleted` ACK), `ClaimVerificationAdapter` hỗ trợ `TargetScopeMode`, cơ chế `bounded rewrite` + fail-closed fallback, và playback simulator. | `COMPLETED (Mock Offline)` *(`189/189` tests Phase 3)* |
| **Phase 4** | **Evaluation & Runner (`E01-T08`)** | Triển khai hệ thống đánh giá 5 trục (`src/p06/evaluation/`), Runner tái lập 10 artifacts + CLI `run_e01.py` (`src/p06/runner/`), tách bạch `VirtualClock` vs wall-clock, lọc lượt kết thúc biên SKU sạch (`is_clean_termination_boundary_trace`), xuất phiếu chấm mù và khô-chạy Mock. *(Lưu ý: `e01_story_plans.json` hiện có 6–9 topics nên dừng `EARLY_COMPLETION` sau ~37–56s; phép thử `W=5` vs `W=10` ngoài cửa sổ kiểm chứng bằng fixture 12-topic trong integration test).* | `COMPLETED (E01-T08 Mock)` *(`249/249` tests pass; live `E01-T09`: `NOT STARTED`)* |
| **Phase 5** | **Formal Benchmark & Handoff (`E01-T09+`)** | Chạy `P06-E01`..`P06-E02` trên `Ollama` CPU smoke & `Gemini` formal benchmark, pilot calibration & Human Blind QA 6 tiêu chí, `GoldFactualLabel` độc lập, phân tích latency/chi phí, xuất `reports/final_report.md` và quyết định `GO/CHANGE/NO-GO`. | `NOT STARTED` |

---

## 6. Quy tắc tái lập & Ghi nhận lỗi (Reproducibility & Failure-Logging Rules)

Tuân thủ chặt chẽ quy chuẩn lưu trữ tại `experiments/README.md` (§5 & §8):

1. **Cấu trúc thư mục lưu trữ kết quả chạy:**
   Mọi lần chạy thí nghiệm (kể cả lần chạy thất bại) phải lưu bất biến tại:
   `runs/<exp_id>/<run_id>/` (ví dụ: `runs/P06-E01/P06-E01_20261126T040000Z/`).
   Thư mục run tối thiểu phải chứa: `manifest.json`, `traces.jsonl` (chi tiết từng node LangGraph), `transcript.json` (lời thoại phát thực tế qua ACK), `discarded_candidates.jsonl` (nhật ký các ứng viên bị hủy/rewrite) và `metrics_summary.json`.

2. **Nội dung bắt buộc trong `manifest.json`:**
   - Định danh: `experiment_id`, `run_id`, `created_at` (UTC), `owner`, `reviewer`, `git_commit_hash` (ghi rõ `dirty=true` nếu có thay đổi chưa commit).
   - Dữ liệu & Hợp đồng: `dataset_source`, `dataset_checksum`, `is_synthetic` (phân tách rõ dữ liệu thật có quyền và dữ liệu tổng hợp), `contract_version` (ví dụ `"p06-mock-v0.1"`).
   - Môi trường & Phần cứng (`cpu_ram`): `python_version`, phiên bản `langgraph`/`pydantic`, `cpu_ram` (`cpu_model`, `ram_gb`).
   - Provider & Model Telemetry: `provider_config` (tier `unit_test` | `local_smoke_test` | `formal_experiment`, provider class, timeout), `model_id`, `quantization` (nếu chạy local Ollama, hoặc `"api_managed"` nếu cloud), `context_window`, `sampling_params` (`temperature`, `seed`, ...), `prompt_version`.
   - Cấu hình thuật toán: `max_retries` (`K`), `memory_window_size` (`W ∈ {5, 10, 20}`), `semantic_memory_enabled` (`true`/`false`), `timeout_seconds`, `workload_profile` (`W0`–`W3`).
   - Kết quả & Telemetry tổng hợp: `latency` (`p50_ms`, `p95_ms`, cold/warm), `token_usage` (`input_tokens`, `output_tokens`, `wasted_tokens`), `metrics`, `hard_gate_passed` (`true`/`false`), `decision` (`GO` / `CHANGE` / `NO-GO` / `INCONCLUSIVE`), `notes` (giới hạn, giả lập đang dùng).

3. **Xử lý tính bất định của LLM (Non-Determinism Caveats):**
   - Khóa `sampling_params` (`temperature` ở mức thấp hoặc khai báo rõ trong cấu hình so sánh) và ghi `seed` nếu provider hỗ trợ.
   - Vì LLM API thương mại vẫn có sai số ngẫu nhiên ngay cả khi truyền `seed`, mỗi thí nghiệm so sánh phải lặp lại tối thiểu nhiều lượt theo kế hoạch đã chốt trước khi chạy, báo cáo đầy đủ khoảng dao động thay vì chọn một lượt chạy đẹp nhất (no cherry-picking).

4. **Theo dõi lãng phí (Waste Tracking):**
   - Không chỉ tính token của câu nói cuối cùng phát ra; mọi `SpeechCandidate` bị cổng `P05` chặn, bị vòng `bounded rewrite` loại bỏ, hoặc bị hủy do hết TTL / bị comment chen ngang phải được ghi vào `discarded_candidates.jsonl` kèm lý do (`BlockReason`) và lượng token tiêu tốn. Đây là dữ liệu đầu vào bắt buộc cho bài toán chi phí (`R03`) và đánh giá hiệu quả prompt/planner.

5. **Ranh giới Mock vs Real (Mock vs Real Boundary):**
   - Trong `P06` độc lập, `PlaybackCompleted` ACK được mô phỏng bằng playback simulator; `P07`/`P08` là mock scheduler theo hợp đồng `p06-mock-v0.1`; `P05` có thể chạy bản rule/gate từ module `knowledge-verification` qua adapter.
   - Mọi báo cáo kết quả từ môi trường mock phải ghi chú tường minh giới hạn: **kết quả mock chứng minh tính đúng logic của P06 trong kịch bản cô lập, KHÔNG đồng nghĩa với chứng minh khả năng realtime end-to-end (TTS `P02` + Lip-sync `P03` + Playout `P04`) hay sẵn sàng production**.
