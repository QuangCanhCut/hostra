# P07 — Giao thức Dữ liệu, Chống Rò rỉ & Đặc tả Thí nghiệm (E01–E04)

| Thuộc tính | Giá trị |
| :--- | :--- |
| **Mã tài liệu** | `P07-DOC-04` |
| **Phiên bản / Ngày** | `PROPOSED v0.1` — `25/11/2026` |
| **Phạm vi** | Quy trình chuẩn bị dữ liệu, kiểm soát chất lượng nhãn, chia tập chống leak và đặc tả thực thi `P07-E01..E04` |
| **Trạng thái hiện tại** | `NOT STARTED` *(Repository hiện có `0` mẫu dữ liệu P07; tài liệu này thiết lập giao thức trước khi tạo dữ liệu & chạy code)* |
| **Nguồn đối chiếu** | `PoC Plan v1.0` (`P07.10–P07.13`, §8.1–8.3, §9.1–9.4, §13); `Baseline v1.2` (§7.3, §11.1–11.5); `experiments/README.md` (§4–7); `P05 REPORT_P05_POC_v0.1.md` |

> [!NOTE]
> **Trung thực về dữ liệu hiện có:** Tại thời điểm lập giao thức này, thư mục `experiments/sales-intelligence/comment-understanding/data/` hoàn toàn trống (chỉ có khung thư mục `raw/`, `annotations/`, `processed/`). Không có bất kỳ tập dữ liệu bình luận thật nào đang nằm trong repository. Mọi ngưỡng định lượng chưa có trong tài liệu gốc được gắn nhãn **`THRESHOLD REQUIRES REVIEW`** — tuyệt đối không tự đặt ngưỡng giả hoặc hợp thức hóa số liệu sau khi chạy.

---

## 1. Giao thức Xây dựng & Quản trị Bộ dữ liệu (`Dataset Protocol`)

### 1.1 Nguồn dữ liệu, Quyền sử dụng & Phân cấp Vai trò (`PoC Plan v1.0` `P07-T02`, `OPEN-1`)
> **Chi tiết vận hành thu thập & gán nhãn thực tế:** Xem kế hoạch đầy đủ tại [p07-data-acquisition-and-annotation-plan-v0.1.md](./p07-data-acquisition-and-annotation-plan-v0.1.md). **Không sử dụng dữ liệu tự sinh hàng loạt bằng LLM làm tập dữ liệu chính.**

Mỗi bản ghi trong `data/` bắt buộc khai báo trường `data_origin` thuộc một trong 3 tầng nguồn sau (sắp xếp từ giá trị thực tiễn cao nhất xuống nguồn bổ trợ có kiểm soát):

| `data_origin` | `is_synthetic` | Mô tả & Điều kiện quyền sử dụng | Vai trò được phép trong đánh giá |
| :--- | :---: | :--- | :--- |
| `real_permissioned_commerce` | `false` | Bình luận thực tế từ phiên livestream bán thực phẩm đóng gói / nông sản / trà / mật ong / hạt điều được chủ kênh/merchant cấp phép sử dụng hợp pháp, đã khử PII (`số điện thoại`, `địa chỉ`, `tên thật`). | **Nguồn ưu tiên cao nhất cho `Held-out Real Test` (`test_real`)** để đóng `P07 OPEN-1`; chỉ đưa vào `train`/`dev` khi quy mô đủ lớn sau khi đã khóa đủ `test_real`. |
| `human_simulated_live` | `false` | Bình luận do người thật đóng vai người xem gõ trực tiếp theo thẻ tình huống (không chép câu mẫu) trong các buổi diễn tập bán hàng 2–5 SKU có sự đồng ý tham gia. | **Nguồn xương sống khả thi cho `train` / `dev` / `test_human_simulated`** khi dữ liệu thương mại thật còn hạn chế; báo cáo hoàn toàn tách biệt với `test_real` (không gọi là real-world validation). |
| `synthetic_seed_template` / `synthetic_llm_human_reviewed` | `true` | Dữ liệu tổng hợp có ghi rõ `template_family_id`, chỉ dùng để **bổ sung lớp hiếm hoặc kiểm thử ca khó/cực đoan** (slang nặng, multi-SKU, ambiguous ref, prompt injection, burst duplicate), bắt buộc có người rà soát từng câu. | Kiểm thử chuyên biệt (`E02`/`E03`/`E04` synthetic slices) hoặc nhánh thử nghiệm tăng cường (`train_augmented` so đối chứng với `train_human_only`); **cấm tuyệt đối trộn vào `test_real` hoặc `test_human_simulated`**. |

### 1.2 Kế thừa Danh mục Sản phẩm Chuẩn từ P05 (5 SKU Thực phẩm Đóng gói)
Để đảm bảo tính liên thông giữa `P07 -> P08 -> P05 -> P06`, các buổi diễn tập `human_simulated_live` và kịch bản kiểm thử kế thừa 3 SKU trong `experiments/sales-intelligence/knowledge-verification/data/catalog_seed.json` (`SKU-HONEY-01`, `SKU-TEA-02`, `SKU-CASHEW-03`) và 2 SKU thực phẩm đóng gói từ bộ tài liệu `P05-E01` (`SKU-MANGO-04` Xoài sấy dẻo, `SKU-COFFEE-05` Cà phê rang xay), tạo thành danh mục **5 SKU chuẩn** (`W0/W1/W2`). Với nguồn `real_permissioned_commerce`, giữ đúng ngữ cảnh danh mục sản phẩm thực tế của phiên nguồn (hoặc gắn `"UNKNOWN"` nếu nguồn không cung cấp, tuyệt đối không bịa).

### 1.3 Quy mô Mục tiêu (`PROPOSED` — chờ duyệt) cho Phiên bản `v0.1` (`PoC Plan v1.0` `P07.10–P07.11`, §8.1)
1. **Tập chính `p07_comments_v0.1` (`PROPOSED: 600 – 1.000` bản ghi):** Phủ đủ 9 lớp `primary_intent` và 4 lớp `moderation_status` (`ELIGIBLE`, `SPAM_FLOOD`, `ABUSE_BLOCKED`, `PROMPT_INJECTION`), hướng tới tối thiểu `50–65` mẫu thuộc các thành phần liên thông độc lập cho mỗi lớp Intent để đủ chia `32-shot train` + `dev` + `test`.
2. **Tập kiểm thử độ bền ngôn ngữ `p07_adversarial_slang_v0.1` (`PROPOSED: >= 200` bản ghi cho `E02`):** Báo cáo tách riêng lát cắt người viết (`real` / `human_simulated`) và lát cắt `synthetic`, phủ các nhãn hiện tượng (`no_diacritics`, `heavy_slang_teencode`, `typo_elongation`, `multi_sku_comparison`, `contextual_pronoun_followup`, `ambiguous_sku_trap`, `r17_medical_claim_bait`, `prompt_injection`).
3. **Tập cặp đánh giá gom nhóm `p07_grouping_pairs_v0.1` (`PROPOSED: >= 150` cặp cho `E03`):** Tối thiểu `100` cặp đồng nghĩa hợp lệ (cùng câu hỏi thực chất trên cùng SKU) và `>= 50` cặp bẫy **không được gộp** — bao gồm cả **cặp cùng `primary_intent` và cùng `SKU` nhưng hỏi hai thuộc tính khác nhau** (ví dụ `"hạn sử dụng"` vs `"cách bảo quản"` để kiểm chứng giới hạn của baseline thô `G0`), cặp khác SKU, cặp 1 rõ SKU + 1 `UNCLEAR`, và cặp khác `knowledge_version`.
4. **Tập kịch bản dòng thời gian `p07_burst_traces_v0.1` (cho `E04`):** Các chuỗi sự kiện có dấu thời gian mô phỏng tốc độ `20`, `60`, `100` bình luận thô/phút kèm sự kiện trùng `external_dedup_key` ở Intake, 1 người xem xả `SPAM_FLOOD`, nhiều người hỏi trùng và sự kiện `COMMITTED` khóa nhóm từ `P08MockScheduler`.

### 1.4 Quy trình Gán nhãn & Kiểm soát Chất lượng (Annotation QC)
1. **Bước Pilot Calibration (`50–100` mẫu thu thập đầu tiên):** Dùng để kiểm định độ rõ ràng của [p07-annotation-guideline-v0.1.md](./p07-annotation-guideline-v0.1.md) (lưu ý: đây chỉ là mẫu pilot kiểm tra guideline, không phải toàn bộ tập huấn luyện). Hai người gán nhãn độc lập thực hiện gán nhãn mù.
2. **Đo độ đồng thuận (IAA):** Tính hệ số **Cohen's Kappa (`κ`)** riêng cho `moderation_status` (trên toàn bộ mẫu pilot), `primary_intent` (trên các mẫu cả hai cùng gán `ELIGIBLE`), và `sku_resolution_mode` (trên các mẫu cả hai cùng gán `ELIGIBLE`). Họp phân xử (`adjudication`), tinh chỉnh Guideline và khóa taxonomy `v0.1` trước khi gán nhãn chính thức.
3. **Kiểm tra tự động bằng Schema Validator:** Mọi bản ghi vi phạm quy tắc cấu trúc (ví dụ `moderation_status != "ELIGIBLE"` nhưng `primary_intent` hoặc `sku_resolution_mode` khác `null`; hoặc `sku_resolution_mode` thuộc `{"UNCLEAR", "OUT_OF_CATALOG", "NOT_APPLICABLE"}` nhưng `referenced_sku_ids` không rỗng) bị từ chối đưa vào `data/processed/`.

### 1.5 Chiến lược Chia Tập Chống Rò rỉ Dữ liệu bằng Đồ thị Liên thông (`Connected-Component Anti-Leakage Split` — `PoC Plan v1.0` §9.2)
Việc chỉ kiểm tra rời rạc từng trường riêng lẻ vẫn có thể gây rò rỉ bắc cầu (ví dụ bình luận $c_1$ và $c_2$ cùng `viewer_thread_id`, còn $c_2$ và $c_3$ của người xem khác lại cùng `paraphrase_cluster_id` → nếu tách $c_1, c_2$ vào `train` và $c_3$ vào `test` thì cụm diễn đạt của $c_2$ đã lộ sang `test`). Quy trình chia tập bắt buộc thực hiện 6 bước nghiêm ngặt:

1. **Xây dựng Đồ thị Liên kết Rò rỉ $G = (V, E)$:** Mỗi đỉnh là một bản ghi bình luận duy nhất sau bước khử trùng chính xác. Tạo cạnh nối vô hướng giữa hai bản ghi $(c_i, c_j)$ nếu chúng thỏa mãn **bất kỳ** điều kiện nào sau đây:
   - Cùng `paraphrase_cluster_id` hoặc cùng `template_family_id` (đối với mẫu có nguồn gốc kịch bản/template);
   - Cùng `viewer_thread_id` hoặc cùng cặp `(session_id, guest_session_id)`;
   - **Phát hiện trùng lặp gần (`Automated Near-Duplicate Link`):** Trùng khớp chính xác sau khi bỏ dấu tiếng Việt + chuẩn hóa chữ thường/khoảng trắng/ký tự lặp (`unaccent_fingerprint`), hoặc có độ tương đồng Jaccard ký tự 3-gram / chồng lấp từ chuẩn hóa vượt ngưỡng kiểm soát (`PROPOSED: char-3gram Jaccard >= 0.85`) nhằm bắt các câu gần như giống hệt nhau chưa được gắn chung `paraphrase_cluster_id`.
2. **Tìm Thành phần Liên thông (`Union-Find / Connected Components`):** Mọi bản ghi liên thông trực tiếp hoặc bắc cầu trên đồ thị $G$ được gán chung một mã **`split_group_id` bất biến**.
3. **Stratified Group Split trên `split_group_id`:** Phân bổ toàn bộ một `split_group_id` vào duy nhất một trong ba tập `train`, `dev` hoặc `held-out test` (giao của `split_group_id`, `paraphrase_cluster_id`, `viewer_thread_id` và `template_family_id` giữa mọi cặp split bắt buộc bằng `∅`). Chạy kiểm toán hậu kiểm (`post-split leakage audit`) đo độ tương đồng gần nhất giữa mọi mẫu `test` với `train ∪ dev`.
4. **Nguyên tắc Bất khả Xâm phạm của `Held-out Test`:** Tập `test` **tuyệt đối không** được dùng để mở rộng từ điển slang/regex, chọn đặc trưng, dừng sớm (`early stopping`), chọn mô hình thắng (`PhoBERT-base` vs `SetFit`), hay tinh chỉnh ngưỡng `τ_conf` / `τ_sim`. Toàn bộ việc chọn mô hình và ngưỡng chỉ được thực hiện trên `train` và `dev`.
5. **Tách bạch Tuyệt đối Nguồn Dữ liệu khi Đánh giá & Báo cáo:**
   - Không gộp chung `real_permissioned_commerce`, `human_simulated_live` và `synthetic_*` thành một điểm số tổng hợp duy nhất.
   - Kết quả phải báo cáo thành các cột/bảng riêng: `test_real` (nếu đã thu thập được), `test_human_simulated`, và `test_synthetic_adversarial`. Tuyệt đối không đưa mẫu `synthetic` vào `test_real` hay `test_human_simulated`.
6. **Tạo Few-Shot Subsets (`k ∈ {8, 16, 32}` mẫu/lớp cho `E01`):** Chỉ lấy mẫu con từ tập `train` đã khóa với **3 random seeds (`42`, `100`, `2026`)** (ưu tiên lấy mỗi mẫu từ một `split_group_id` khác nhau trong `train` để tránh 8 mẫu của một lớp đều là biến thể của 1 câu); giữ cố định `dev` và `test` cho mọi mô hình.

### 1.6 Quản lý Phiên bản, Tái lập & Quyền riêng tư
- Lưu dữ liệu theo cấu trúc sẵn có của thư mục:
  - `data/raw/`: Dữ liệu thô ban đầu (chỉ lưu nếu không chứa PII và có quyền lưu Git; nếu nhạy cảm chỉ lưu manifest tham chiếu).
  - `data/annotations/`: Dữ liệu gán nhãn và biên bản tính IAA.
  - `data/processed/`: Các tập `train.jsonl`, `dev.jsonl`, `test_*.jsonl`, `e02_adversarial.jsonl`, `e03_pairs.jsonl`, `e04_burst_traces.jsonl` kèm tệp `dataset_manifest.json` ghi mã băm **`SHA-256`** của từng tệp.
- Tuyệt đối không đưa số điện thoại thật, địa chỉ nhà, tài khoản mạng xã hội cá nhân hoặc khóa API vào bất kỳ tệp nào trong `data/` hay `results/`.

---

## 2. Đặc tả Thực thi Chi tiết 4 Thí nghiệm (`P07-E01` đến `P07-E04`)

### 2.1 Thí nghiệm `P07-E01` — So sánh Công bằng Mô hình Phân loại Ý định (Intent Model Fair Comparison)

1. **Research Question:** Trên cùng tập kiểm thử tiếng Việt livestream cố định, mô hình phân loại nhỏ nào (`PhoBERT-base` hay `SetFit`) đạt chất lượng phân loại ý định tốt hơn ở các mức dữ liệu ít (`8 / 16 / 32` mẫu/lớp) và toàn bộ tập `train`, đồng thời giảm được bao nhiêu độ trễ và chi phí so với gọi LLM cho mọi bình luận hợp lệ? (`PoC Plan v1.0` `P07-E01`).
2. **Hypothesis:** Ở mức dữ liệu rất ít (`8–16` mẫu/lớp), `SetFit` có thể hội tụ ổn định hơn; khi tăng số mẫu (`32` mẫu/lớp đến full `train`), `PhoBERT-base` (kèm chuẩn hóa + tách từ tiếng Việt) hoặc `SetFit` kết hợp `Rules + Selective LLM` có thể tiệm cận chất lượng của baseline `Rules + LLM all eligible` nhưng với độ trễ P95 trên CPU/GPU thấp hơn đáng kể và chi phí API giảm mạnh.
3. **Input Datasets:** Tập `train` (với các tập con `8`, `16`, `32` mẫu/lớp × 3 seeds + `full train`), tập `dev` (chọn siêu tham số/ngưỡng), và tập `held-out test` đã khóa mã băm `SHA-256`.
4. **Baselines & Candidate Approaches:**
   - `B0_rules_only`: Chuẩn hóa + từ điển từ khóa/regex xác định.
   - `B1_rules_plus_llm_all`: Tầng lọc luật cơ bản + gọi LLM có cấu trúc cho tất cả bình luận `ELIGIBLE` (`PoC Plan v1.0` `P07.5` Phương án A).
   - `C1_phobert_base`: Chuẩn hóa + tách từ tiếng Việt + fine-tune `vinai/phobert-base` (giấy phép **MIT**; **cấm** dùng `phobert-base-v2` AGPLv3).
   - `C2_setfit_multilingual`: Chuẩn hóa + huấn luyện `SetFit` trên backbone đa ngữ có giấy phép thương mại hợp lệ (ví dụ `intfloat/multilingual-e5-small` MIT hoặc `paraphrase-multilingual-mpnet-base-v2` MIT).
   - `H1_hybrid_selective_llm`: `Rules` + mô hình thắng giữa `C1`/`C2` + gọi `Selective LLM` khi `intent_confidence < τ_conf` (trong đó `τ_conf` được hiệu chuẩn trên `dev`).
5. **Biến độc lập & Biến phụ thuộc:**
   - *Độc lập:* Kiến trúc mô hình (`B0`, `B1`, `C1`, `C2`, `H1`), kích thước tập huấn luyện mỗi lớp (`8`, `16`, `32`, `full`), `random_seed` (`42`, `100`, `2026`), môi trường chạy (`CPU` vs `GPU`).
   - *Phụ thuộc:* `Macro-F1` (trung bình ± độ lệch chuẩn qua 3 seeds), `Per-class F1`, tỷ lệ lỗi tự tin cao (`High-Confidence Error Rate`), độ trễ `P50 / P95` (ms, tách thời gian tách từ + inference), RAM/VRAM đỉnh, tỷ lệ gọi LLM (`%`) và chi phí ước tính / 1.000 bình luận.
6. **Evaluation Metrics:** `Macro-F1` (chính), `Per-class Precision/Recall/F1`, `Confusion Matrix` 9×9, `Spam False Positive Rate` (cho tầng lọc), `Warm Latency P50/P95 (ms)` (so với mục tiêu ngân sách khởi điểm `≤ 300ms` — `Baseline v1.2` §11.2), `Tokens & Cost / 1k comments`.
7. **Experimental Procedure:**
   - Khóa `dataset_manifest.json` và chạy kiểm tra `0` rò rỉ cụm câu giữa các split.
   - Đánh giá `B0` và `B1` trên `dev` và `test`.
   - Huấn luyện `C1` và `C2` trên từng cấu hình `{8, 16, 32, full} × 3 seeds`, chỉ dùng `dev` để dừng sớm (`early stopping`) và chọn ngưỡng `τ_conf` cho `H1`.
   - Đo độ trễ với `warmup_runs >= 20` câu trước khi bấm giờ `steady-state` từng câu lẻ (`batch_size = 1`, mô phỏng đúng bình luận đến theo thời gian thực).
8. **Failure Analysis:** Xuất toàn bộ các mẫu dự đoán sai trên `test`, nhóm theo cặp nhầm lẫn lớn nhất trên Confusion Matrix (ví dụ nhầm giữa `ASK_SAFETY_SUITABILITY` và `ASK_SPEC_USAGE`, hoặc nhầm `PURCHASE_INTENT_CTA` với `SOCIAL_CHITCHAT`).
9. **Evidence to Save:** `results/metrics/P07-E01_<run_id>.json` (theo chuẩn `ExperimentManifest`), ma trận nhầm lẫn dạng JSON/CSV, tệp dự đoán từng mẫu trên `test`, phiên bản checkpoint và giấy phép kiểm tra.
10. **Acceptance Criteria:**
    - Không rò rỉ dữ liệu giữa `train`/`dev`/`test` (`0` cluster overlap — **Hard Criterion**).
    - Độ trễ P95 đường nóng hướng tới ngân sách khởi điểm `≤ 300 ms` (`PROPOSED / TO VALIDATE` — `Baseline v1.2` §11.2).
    - Ngưỡng `Macro-F1` tối thiểu và mức chi phí chấp nhận được: **`THRESHOLD REQUIRES REVIEW`** *(chốt cùng Reviewer trước khi tuyên bố `VALIDATED`)*.
11. **Decision Rule:** Chọn ứng viên (`PhoBERT-base` hoặc `SetFit`) có sự cân bằng tốt nhất giữa `Macro-F1`, độ ổn định ít mẫu, `P95 latency` và giấy phép sạch để đưa sang `E02–E04`; nếu dữ liệu chỉ mới là `synthetic`, giữ trạng thái tối đa ở `IN EXPERIMENT` (chưa nâng lên `VALIDATED` cho tới khi có `held-out real test`).
12. **Dependencies & Blockers:** Phụ thuộc việc khóa [p07-annotation-guideline-v0.1.md](./p07-annotation-guideline-v0.1.md), hoàn tất bộ dữ liệu `v0.1` và cấu hình adapter cho nhánh LLM đối chứng (`B1`/`H1`).

---

### 2.2 Thí nghiệm `P07-E02` — Độ bền Ngôn ngữ Khó & Phân giải Đa SKU (Slang, No-Accent & Multi-SKU)

1. **Research Question:** Tiếng Việt không dấu, viết tắt/slang nặng, câu hỏi nối tiếp theo ngữ cảnh người xem và câu nhắc nhiều SKU làm suy giảm `Intent Macro-F1` và độ chính xác phân giải SKU (`SKU Precision / Wrong-SKU Rate`) bao nhiêu phần trăm? (`PoC Plan v1.0` `P07-E02`).
2. **Hypothesis:** Bộ chuẩn hóa tiền xử lý kết hợp bộ phân giải thực thể theo phạm vi phiên (`Session-Scoped SKU Resolver`) giữ được tỷ lệ gán nhầm sang SKU khác ở mức tối thiểu bằng cách chuyển các ca mơ hồ về `UNCLEAR`, và cho thấy rõ điểm yếu tách từ của `PhoBERT-base` trên câu mất dấu so với `SetFit` subword.
3. **Input Datasets:** Tập `p07_adversarial_slang_v0.1` (`>= 200` mẫu khó có nhãn nguồn và nhãn hiện tượng ngôn ngữ, kèm `SessionTriageContext` 3–5 SKU và `viewer_thread_state`).
4. **Baselines & Candidate Approaches:**
   - So sánh có/không có bước chuẩn hóa slang (`Raw` vs `Normalized`) × (`C1_phobert_base` vs `C2_setfit_multilingual` vs `H1_hybrid_selective_llm`) kết hợp cùng `SessionScopedSkuResolver`.
   - Đối chứng ngây thơ (`Naive Baseline` — chỉ dùng để chứng minh rủi ro): gán mặc định mọi câu thiếu tên sản phẩm vào `active_sku_id`.
5. **Biến độc lập & Biến phụ thuộc:**
   - *Độc lập:* Nhóm hiện tượng ngôn ngữ (`no_diacritics`, `slang`, `multi_sku`, `contextual_followup`, `ambiguous_sku`, `prompt_injection`), bật/tắt chuẩn hóa từ viết tắt, lựa chọn mô hình.
   - *Phụ thuộc:* Độ sụt giảm `Intent Macro-F1` (`ΔF1` so với câu có dấu chuẩn), `SKU Exact Match`, `SKU Precision`, **`Wrong-SKU Attribution Rate`**, `Prompt Injection Block Rate`, `Cross-Viewer Bleed Count`.
6. **Evaluation Metrics:** Báo cáo phân rã bắt buộc theo từng lát cắt ngôn ngữ (`slice-by-slice metrics`), không chỉ báo trung bình cộng toàn tập.
7. **Experimental Procedure:** Chạy các checkpoint đã khóa từ `E01` (không huấn luyện lại trên tập `E02`!) qua từng lát cắt của 200+ ca khó; kiểm tra riêng các ca bẫy ngữ cảnh Viewer A vs Viewer B (`EC04`).
8. **Failure Analysis:** Thống kê top các từ viết tắt/không dấu gây gãy bộ tách từ hoặc làm nhầm tên sản phẩm (ví dụ `"trà"` vs `"trả hàng"`, `"điều"` trong `"hạt điều"` vs `"điều kiện đổi trả"`!).
9. **Evidence to Save:** `results/metrics/P07-E02_<run_id>.json`, bảng điểm theo từng nhóm ngôn ngữ và danh sách toàn bộ ca gán sai SKU (nếu có).
10. **Acceptance Criteria:**
    - `Cross-Viewer Context Bleed = 0` và `Cross-Tenant/Session Accept = 0` trên bộ negative tests xác định (**Hard Gate G3/G4**).
    - Ngưỡng chấp nhận cho `Intent F1` trên câu không dấu và `SKU Precision`: **`THRESHOLD REQUIRES REVIEW`**.
11. **Decision Rule:** Nếu `PhoBERT-base` tụt F1 mạnh trên câu không dấu do lỗi word segmentation trong khi `SetFit` giữ vững (hoặc ngược lại), dùng bằng chứng này để chốt kiến trúc thắng (`ADR-013`); cập nhật quy tắc chặn từ đồng âm (`"điều"`, `"trà"`) trong `SkuResolver`.
12. **Dependencies & Blockers:** Cần checkpoint từ `E01` và tập `p07_adversarial_slang_v0.1`.

---

### 2.3 Thí nghiệm `P07-E03` — Gom nhóm Ngữ nghĩa & Chính sách Từ chối Đoán mò (Grouping & Abstention)

1. **Research Question:** Baseline gom nhóm thô `G0` theo khóa `(primary_intent, canonical_sku_scope, knowledge_version_scope)` để lọt bao nhiêu phần trăm trường hợp **gộp sai thuộc tính hỏi** (hai câu cùng intent và cùng SKU nhưng hỏi hai khía cạnh khác nhau), và việc bổ sung luật tách thuộc tính (`G1`) hoặc tương đồng vector `intfloat/multilingual-e5-small` (`G2`) cùng chính sách từ chối đoán (`UNCLEAR` / confidence abstention) cải thiện độ chính xác gom nhóm như thế nào? (`PoC Plan v1.0` `P07-E03`).
2. **Hypothesis:** Ràng buộc phân vùng theo `referenced_sku_ids` + `knowledge_version` là điều kiện cần giúp chặn lỗi gộp chéo sản phẩm, nhưng **`G0` chưa phải là giải pháp gom nhóm đủ đúng** vì có thể gộp nhầm các câu hỏi khác thuộc tính trong cùng một lớp rộng như `ASK_SPEC_USAGE` (ví dụ *"hạn sử dụng"* vs *"cách bảo quản"*); `G1` hoặc `G2` sẽ giảm đáng kể tỷ lệ gộp sai thuộc tính (`Subtopic Bad Merge Rate`).
3. **Input Datasets:** Tập `p07_grouping_pairs_v0.1` (`PROPOSED: >= 100` cặp đồng nghĩa thực sự + `>= 50` cặp bẫy gồm: cặp cùng `intent` + cùng `SKU` nhưng khác thuộc tính hỏi, cặp khác SKU, cặp 1 rõ SKU + 1 `UNCLEAR`, cặp khác `knowledge_version`), chia thành `dev_pairs` (chọn ngưỡng) và `test_pairs` (khóa đánh giá, không dùng để dò ngưỡng).
4. **Baselines & Candidate Approaches:**
   - `G0_intent_sku_key` *(Coarse Baseline — chưa được coi là giải pháp đã xác thực)*: Gom thuần theo `(primary_intent, referenced_sku_ids, knowledge_version)`.
   - `G1_subtopic_rule_key`: Ràng buộc cứng `(referenced_sku_ids, knowledge_version)` + `primary_intent` + tách khe thuộc tính hỏi bằng từ khóa/luật (`expiry` vs `storage` vs `usage` vs `weight` vs `ingredients`).
   - `G2_sku_guarded_e5`: Ràng buộc cứng `(referenced_sku_ids, knowledge_version)` trước, sau đó kiểm tra cosine similarity bằng `intfloat/multilingual-e5-small` `>= τ_sim` (chọn `τ_sim` duy nhất trên `dev_pairs`).
5. **Biến độc lập & Biến phụ thuộc:**
   - *Độc lập:* Chiến lược gom nhóm (`G0`, `G1`, `G2`), ngưỡng tương đồng `τ_sim`, ngưỡng từ chối `τ_conf`.
   - *Phụ thuộc:* `Grouping Precision`, `Grouping Recall`, **`Cross-SKU Bad Merge Rate`**, `Subtopic Bad Merge Rate` (gộp `"hạn dùng"` với `"cách pha"` làm P06 dễ trả lời sót ý), `Abstention / Fallback %`, độ trễ tăng thêm khi chạy `E5-small` trên CPU.
6. **Evaluation Metrics:** `Pairwise Precision / Recall / F1`, `Cross-SKU Bad Merge Rate`, `False Abstention Rate` vs `High-Confidence Error Rate`, `P95 Grouping Latency (ms)`.
7. **Experimental Procedure:** Quét ngưỡng `τ_conf` và `τ_sim` trên `dev_pairs` để vẽ đường cong đánh đổi; khóa một cấu hình duy nhất rồi chạy 1 lần trên `test_pairs`.
8. **Failure Analysis:** Kiểm tra cụ thể các cặp `G0` gộp quá rộng (cùng `ASK_SPEC_USAGE` nhưng khác thuộc tính hỏi) so với chi phí độ trễ của `G1` và `G2`.
9. **Evidence to Save:** `results/metrics/P07-E03_<run_id>.json`, bảng quyết định trên từng cặp và đường cong chọn ngưỡng trên `dev`.
10. **Acceptance Criteria:**
    - **`Cross-SKU Bad Merge Rate = 0`** và **`Provenance Loss = 0`** (không mất `comment_id` thành viên nào) trên bộ kiểm thử xác định (**Hard Invariants `INV-P07-05`, `INV-P07-06`**).
    - Ngưỡng `Grouping Precision` tối thiểu và `Fallback %` tối đa: **`THRESHOLD REQUIRES REVIEW`** (`PoC Plan v1.0` §14 `P1`).
11. **Decision Rule:** Chỉ đề xuất đưa `multilingual-e5-small` vào pipeline nếu `G2` giảm đáng kể `Subtopic Bad Merge Rate` so với `G1` mà vẫn giữ độ trễ CPU nằm gọn trong ngân sách Triage (`PoC Plan v1.0` `P07.7`).
12. **Dependencies & Blockers:** Phụ thuộc đầu ra phân loại/SKU của `E01–E02` và bộ cặp `p07_grouping_pairs_v0.1`.

---

### 2.4 Thí nghiệm `P07-E04` — Chịu tải Dồn dập, Khử trùng & Công bằng Hàng đợi (Burst & Duplicates)

1. **Research Question:** Dưới tải dồn dập `W2` (`20–100` bình luận thô/phút) có chứa sự kiện gửi trùng ID, một người xem spam liên tục và nhiều người hỏi cùng câu hỏi, pipeline `P07 -> P08MockScheduler` có đảm bảo `0` tác vụ trùng lặp, giữ độ trễ hàng đợi ổn định và phân bổ công bằng giữa các người xem/SKU không? (`PoC Plan v1.0` `P07-E04`).
2. **Hypothesis:** Khử trùng sự kiện ở Intake theo `external_dedup_key` (và idempotency theo `comment_id` tại P07), lọc `SPAM_FLOOD` theo `guest_session_id`, phát `ResponseGroupProposal` sang `P08MockScheduler` để gộp vào `ResponseGroup` đang ở trạng thái `QUEUED`, và khóa cứng không gộp thêm ngay khi nhóm chuyển sang `COMMITTED` giúp nén mạnh số lượng task mà không đánh mất bình luận hợp lệ của người xem khác.
3. **Input Datasets:** Tập `p07_burst_traces_v0.1` với 3 mức tải (`20`, `60`, `100` raw comments/phút trong 5–10 phút thời gian mô phỏng), bao gồm: (a) 25% gói tin lặp `external_dedup_key`, (b) 1 guest xả 30 câu spam/phút, (c) 15 guest hỏi trùng giá `SKU-HONEY-01` cùng lúc với 3 guest hỏi hạn dùng `SKU-TEA-02`, (d) sự kiện giả mạo từ `tenant_id` khác và sự kiện `COMMITTED` từ `P08MockScheduler`.
4. **Baselines & Candidate Approaches:**
   - `U0_unbounded_fifo` *(Đối chứng lỗi)*: Đẩy từng bình luận hợp lệ thành task riêng không gom nhóm, không chặn flood theo viewer.
   - `T1_full_p07_triage`: Đầy đủ Exact Dedup + Per-Guest Flood Guard + Classifier/SKU Resolver + Open-Group Merge nối với `P08MockScheduler` (mô phỏng batch 3 nhóm / 20s airtime và cờ `COMMITTED`).
5. **Biến độc lập & Biến phụ thuộc:**
   - *Độc lập:* Mức tải (`20`, `60`, `100` bình luận/phút), tỷ lệ retry trùng khóa, hạn mức gọi `Selective LLM` mỗi phút (`quota`).
   - *Phụ thuộc:* `Duplicate Task Count`, `Task Compression Ratio`, `Triage Processing P95 (ms)`, `Queue Wait P95 (ms)` trên đồng hồ mô phỏng, `Unique Viewers Served Ratio` (chỉ số công bằng), `Post-Committed Illegal Merge Count`.
6. **Evaluation Metrics:** `Duplicate Task Count` (`= 0`), `Cross-Tenant Leak Count` (`= 0`), `Provenance Integrity` (`100%`), `Processing P50/P95`, `Fairness Share` (tỷ lệ câu hỏi hợp lệ của viewer không spam được xếp lịch trước khi hết `TTL`).
7. **Experimental Procedure:** Phát lại (`deterministic replay`) cùng một chuỗi sự kiện với đồng hồ giả lập (`fake_clock`) và cả chế độ bấm giờ thực trên CPU cho bước inference để đo thông lượng thực tế.
8. **Failure Analysis:** Kiểm tra hiện tượng nghẽn hàng đợi khi `Selective LLM` bị gọi quá nhiều trong đợt burst, chứng minh cơ chế cắt quota (`circuit breaker / quota cap`) hoạt động đúng.
9. **Evidence to Save:** `results/metrics/P07-E04_<run_id>.json`, nhật ký dòng thời gian sự kiện (`event_timeline.jsonl`) đối chiếu `comment_id -> response_group_id -> mock_schedule_decision`.
10. **Acceptance Criteria:**
    - **`Duplicate Task Count = 0`**, **`Post-Committed Merge Count = 0`**, **`Cross-Tenant/Session Leak = 0`**, **`Lost Viewer Record = 0`** (**Hard Gates G2/G3/G4**).
    - Ngưỡng `Queue P95` và chỉ số `Fairness`: **`THRESHOLD REQUIRES REVIEW`**.
11. **Decision Rule:** Xác nhận hợp đồng `P07 -> P08` hoạt động trơn tru dưới tải `W2` trước khi bàn giao sang simulator `P08/P09` và tích hợp `apps/api/modules/conversation/`.
12. **Dependencies & Blockers:** Phụ thuộc pipeline từ `E01–E03` và module `P08MockScheduler` viết theo đúng [p07-contract-v0.1.md](./p07-contract-v0.1.md).

---

## 3. Khuôn mẫu Lưu Bằng chứng Tái lập (`ExperimentManifest`)

Mọi lượt chạy `P07-E01..E04` bắt buộc xuất tệp JSON vào `results/metrics/` tuân thủ chuẩn tái lập của `experiments/README.md` (§5) và đồng bộ với `P05`:

```json
{
  "experiment_id": "P07-E01",
  "run_id": "20261126T000000Z_seed42",
  "created_at": "2026-11-26T00:00:00Z",
  "git_commit_hash": "<commit_sha>",
  "dirty_worktree": false,
  "dataset_source": "data/processed/dataset_manifest.json",
  "dataset_sha256": "<sha256>",
  "is_synthetic": true,
  "model_info": {
    "candidate_name": "C1_phobert_base",
    "checkpoint_id": "vinai/phobert-base",
    "checkpoint_revision": "<hf_commit_hash>",
    "license": "MIT",
    "word_segmenter": "<tool_name_and_version_or_NA>"
  },
  "environment": {
    "python": "3.13.x",
    "os": "Windows-11 / Linux-Colab",
    "accelerator": "CPU-only | <GPU_SKU>",
    "packages": {}
  },
  "config": {
    "shots_per_class": 16,
    "seed": 42,
    "warmup_runs": 20
  },
  "metrics": {},
  "hard_gates": {
    "zero_split_cluster_leak": true,
    "zero_cross_sku_bad_merge": true,
    "zero_provenance_loss": true,
    "zero_cross_tenant_accept": true
  },
  "decision": "INCONCLUSIVE",
  "reviewer": null,
  "notes": "Template minh họa cấu trúc lưu bằng chứng; chưa chạy thực nghiệm."
}
```
