# P07 — Giao thức Dữ liệu, Chống Rò rỉ & Đặc tả Thí nghiệm (E01–E04)

| Thuộc tính | Giá trị |
| :--- | :--- |
| **Mã tài liệu** | `P07-DOC-04` |
| **Phiên bản / Ngày** | `PROPOSED v0.1.3` — `26/11/2026` |
| **Phạm vi** | Giao thức dữ liệu đa dạng sản phẩm, kiểm định tương quan giả & đồ thị chống rò rỉ, `Unseen Product Holdout`, ablation tiền xử lý và đặc tả `P07-E01..E04` |
| **Trạng thái hiện tại** | `NOT STARTED` *(Repository hiện có `0` mẫu dữ liệu P07; tài liệu này thiết lập giao thức chuẩn trước khi chạy Data Acquisition Pilot & thực nghiệm)* |
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
| `real_permissioned_commerce` | `false` | Bình luận thực tế từ phiên livestream bán thực phẩm đóng gói / nông sản / OCOP được chủ sở hữu cấp phép kèm kiểm tra ToS nền tảng & cơ sở pháp lý BVDLCN, đã khử PII cục bộ (`<PHONE>`, `<ADDRESS>`, giả danh hóa người xem). | **Ưu tiên khảo sát số 1 (`Real-First`).** Nếu thu được quy mô đủ lớn từ nhiều shop/phiên độc lập: cấp cho cả `train / dev / test_real` (tách độc lập theo đơn vị shop/phiên); chỉ khi khan hiếm (`~100–300` mẫu ngoài gói Pilot) mới khóa trọn 100% làm `test_real` holdout. |
| `human_simulated_live` | `false` | Bình luận do người thật đóng vai người xem gõ trực tiếp theo thẻ tình huống mở (không chép câu mẫu, không ép định mức số câu/người) trong các buổi diễn tập 2–5 SKU có phiếu đồng ý và gắn `participant_id` ẩn danh xuyên buổi. | **Nguồn bổ sung / dự phòng mở khóa tiến độ** cho `train / dev / test_human_simulated` khi `Source A` hạn chế hoặc khuyết metadata `active_sku`; báo cáo tách biệt hoàn toàn với `test_real`. |
| `synthetic_seed_template` / `synthetic_llm_human_reviewed` | `true` | Dữ liệu tổng hợp có ghi rõ `template_family_id` & `paraphrase_cluster_id`, bắt buộc người thật duyệt từng câu; **chỉ dùng cho ca hiếm/an toàn/stress-test và đối chứng tăng cường dữ liệu**. | Lát cắt chuyên biệt (`E02`/`E03`/`E04` synthetic slices) hoặc nhánh thực nghiệm đối chứng **`train_synthetic_augmented` đặt cạnh `train_real_and_human` / `train_human_only`**; **cấm trộn vào `test_real` hoặc `test_human_simulated`**. |

> **Cấm nhiễm bẩn từ gói Pilot (`Pilot Anti-Contamination Rule`):** Mọi bình luận thuộc gói `Data Acquisition / Annotation Pilot (50–100 mẫu)` đã được nhóm mở ra đọc để sửa định nghĩa nhãn, viết từ điển viết tắt hoặc tinh chỉnh luật phân giải đều gắn cờ `inspected_in_pilot = true` và **tuyệt đối không được đưa vào bất kỳ tập `held-out test` nào**.

### 1.2 Đa dạng Sản phẩm Mở (`Open-Product Diversity`), Vai trò Fixture của 5 SKU P05 & Kiểm tra Tương quan Giả
1. **Không giới hạn Dataset trong 5 SKU của P05:** Bộ 5 SKU kế thừa từ `P05` (`SKU-HONEY-01`, `SKU-TEA-02`, `SKU-CASHEW-03`, `SKU-MANGO-04`, `SKU-COFFEE-05`) **chỉ được dùng làm `controlled integration fixtures` và kịch bản kiểm thử tham chiếu** khi đối chiếu liên thông `P07 -> P08 -> P05 -> P06`. Dữ liệu thu thập thực tế (`Source A`) và diễn tập mở rộng (`Source B`) bắt buộc mở rộng sang nhiều mặt hàng, nhóm sản phẩm, merchant và phiên livestream khác nhau để đảm bảo `Intent Classifier` học biểu diễn **độc lập sản phẩm (`product-agnostic`)** còn `SKU Resolver` được kiểm chứng trên **danh mục phiên động (`dynamic session catalog`)**.
2. **Kiểm toán Tương quan Giả giữa Sản phẩm và Nhãn Intent (`Spurious Product–Intent Correlation Check`):** Trước khi khóa tập `train`, bắt buộc kiểm tra bảng phân phối đồng thời `product_family / sku_id × primary_intent` (tính hệ số Cramér's $V$ và `Normalized Mutual Information`). Nếu tồn tại tương quan giả cao (ví dụ một mặt hàng hầu như chỉ đi kèm một loại câu hỏi duy nhất), mô hình phân loại sẽ học đường tắt theo tên mặt hàng và suy giảm mạnh trên sản phẩm mới; báo cáo kiểm toán phải công bố chỉ số này và cân bằng lại kịch bản thu thập nếu cần.
3. **Tận dụng dữ liệu thực tế khuyết ngữ cảnh mà không đoán mò (`Task-Specific Eligibility`):** Bình luận từ `real_permissioned_commerce` bị thiếu `active_sku_at_comment_time` hoặc thiếu danh mục đầy đủ của buổi live được gắn `sku_grounding_evaluable = false` (`sku_grounding_eval_status = "NOT_EVALUABLE"`), **vẫn hợp lệ 100% để huấn luyện/chấm điểm Moderation & Intent ở `P07-E01` (`moderation_evaluable = true`, `intent_evaluable = true`)**, và tự động loại khỏi mẫu số chấm SKU Grounding ở `P07-E02`. Tuyệt đối không nhầm lẫn cờ khuyết dữ liệu `NOT_EVALUABLE` với nhãn nghiệp vụ `UNCLEAR` (ngữ cảnh đã biết đủ nhưng câu hỏi của khách mơ hồ) và cấm gán `OUT_OF_CATALOG` khi bản thân danh mục phiên chưa biết đầy đủ.
4. **Phân tách 3 mức Khử trùng ở Tiền xử lý Dataset:** Chỉ gộp khử trùng các **Exact Event Duplicates** (cùng khóa sự kiện nguồn `external_dedup_key` trong cùng phiên, bảo lưu `duplicate_delivery_count`); **bắt buộc giữ nguyên** các bình luận người dùng gửi lặp khác mã sự kiện (để đánh giá `SPAM_FLOOD` và `E04`); nếu nguồn xuất thiếu mã sự kiện mà trùng người gửi + câu chữ + giây thì giữ nguyên bản ghi kèm cờ `dedup_flag = "SUSPECTED_DUPLICATE"` (tuyệt đối không tự xóa bằng luật `< 2s`).

### 1.3 Quy mô Mục tiêu (`PROPOSED` — hiệu chỉnh sau Pilot) & Tính Khả thi Nhóm Độc lập
1. **Tập chính `p07_comments_v0.1` (`PROPOSED: 600 – 1.000` bản ghi bình luận, hiệu chỉnh sau Pilot):** Phủ đủ 9 lớp `primary_intent` và 4 lớp `moderation_status`. Phân biệt rõ **số bản ghi bình luận (`comment records`)** với **số nhóm chia tập độc lập (`split_group_id`)**: mỗi lớp cần xuất hiện ở tối thiểu `>= 3` (mục tiêu `PROPOSED: >= 12–20`) `split_group_id` độc lập trên toàn tập để chia được vào cả `train`, `dev` và `test`. Trong `P07-E01`, cấu hình `32-shot` là **32 bản ghi huấn luyện/lớp trong `train`** được rút theo phương pháp ưu tiên đa dạng `split_group_id` (ghi nhận `effective_unique_split_groups`), không đòi hỏi phải có 32 thành phần liên thông riêng cho từng lớp trong `train`. Nếu lớp hiếm trong `train` có `< k` bản ghi, bắt buộc gắn trạng thái **`INSUFFICIENT DATA`** (hoặc **`LIMITED GROUP DIVERSITY`** nếu `< 5` nhóm độc lập), tuyệt đối không rút bù từ `dev`/`test` hay nhân bản câu cũ.
2. **Tập kiểm thử độ bền ngôn ngữ `p07_adversarial_slang_v0.1` (`PROPOSED: >= 200` bản ghi cho `E02`):** Báo cáo tách riêng lát cắt người viết (`real` / `human_simulated`) và lát cắt `synthetic` / biến đổi có kiểm soát (`perturbation`), phủ đủ `no_diacritics`, `heavy_slang_teencode`, `typo_elongation`, `multi_sku_comparison`, `multi_sku_bundle_non_compare`, `contextual_pronoun_followup`, `ambiguous_sku_trap`, `r17_medical_claim_bait`, `prompt_injection`.
3. **Tập cặp đánh giá gom nhóm `p07_grouping_pairs_v0.1` (`PROPOSED: >= 150` cặp cho `E03`):** Gồm `>= 100` cặp đồng nghĩa hợp lệ và `>= 50` cặp bẫy **không được gộp** — bao gồm: (a) cặp cùng `primary_intent` + cùng `SKU` nhưng hỏi hai thuộc tính khác nhau (*"hạn sử dụng"* vs *"cách bảo quản"*), (b) **cặp chồng lấp một phần ý định phụ** (*"Trà giá bao nhiêu?"* vs *"Trà giá bao nhiêu và phí ship thế nào?"* để kiểm tra không làm rơi `secondary_intents`), (c) cặp khác SKU, (d) cặp 1 rõ SKU + 1 `UNCLEAR`/`NOT_APPLICABLE`, và (e) cặp khác `product_version_id` / `knowledge_snapshot_id`.
4. **Tập kịch bản dòng thời gian `p07_burst_traces_v0.1` (cho `E04`):** Chuỗi sự kiện có dấu thời gian mô phỏng tốc độ `20`, `60`, `100` bình luận thô/phút kèm: sự kiện trùng `external_dedup_key` ở Intake, worker retry khi `proposal_delivery_status == "PENDING_DELIVERY"` (kiểm tra khôi phục đề xuất không tạo task đúp nhờ `proposal_id`), 1 người xem xả `SPAM_FLOOD`, nhiều người xem khác nhau hỏi trùng và sự kiện `COMMITTED` khóa nhóm từ `P08MockScheduler`.

### 1.4 Quy trình Gán nhãn & Kiểm soát Chất lượng (Annotation QC)
1. **Bước Pilot Calibration (`50–100` mẫu thu thập đầu tiên):** Dùng để kiểm định độ rõ ràng của [p07-annotation-guideline-v0.1.md](./p07-annotation-guideline-v0.1.md) (lưu ý: đây chỉ là mẫu pilot kiểm tra guideline, không phải toàn bộ tập huấn luyện). Hai người gán nhãn độc lập thực hiện gán nhãn mù.
2. **Đo độ đồng thuận (IAA):** Tính hệ số **Cohen's Kappa (`κ`)** riêng cho `moderation_status` (trên toàn bộ mẫu pilot), `primary_intent` (trên các mẫu cả hai cùng gán `ELIGIBLE`), và `sku_resolution_mode` (trên các mẫu cả hai cùng gán `ELIGIBLE`). Họp phân xử (`adjudication`), tinh chỉnh Guideline và khóa taxonomy `v0.1` trước khi gán nhãn chính thức.
3. **Kiểm tra tự động bằng Schema Validator:** Mọi bản ghi vi phạm quy tắc cấu trúc (ví dụ `moderation_status != "ELIGIBLE"` nhưng `primary_intent` hoặc `sku_resolution_mode` khác `null`; hoặc `sku_resolution_mode` thuộc `{"UNCLEAR", "OUT_OF_CATALOG", "NOT_APPLICABLE"}` nhưng `referenced_sku_ids` không rỗng) bị từ chối đưa vào `data/processed/`.

### 1.5 Chiến lược Chia Tập Chống Rò rỉ Có Kiểm soát trên Đồ thị Liên thông (`Guarded Connected-Component Split` — `PoC Plan v1.0` §9.2)
Việc kiểm tra rời rạc từng trường riêng lẻ dễ để lọt rò rỉ bắc cầu, nhưng ngược lại nếu nối cạnh mù quáng trên giá trị `"UNKNOWN"` hoặc trên các câu ngắn tự nhiên phổ biến (`"giá bn"`, `"ship ko"`) thì toàn bộ dữ liệu sẽ bị hút vào một **Thành phần Liên thông Khổng lồ (`Giant Connected Component`)** không thể chia tập được. Do đó, thuật toán xây dựng đồ thị $G = (V, E)$ bắt buộc tuân thủ **5 chốt chặn kỹ thuật**:

1. **Chốt chặn 1 — Cấm nối cạnh trên Giá trị Khuyết / Placeholder (`Null & Placeholder Guard`):**
   - Bỏ qua tuyệt đối mọi giá trị `null`, chuỗi rỗng `""`, `"UNKNOWN"`, `"MISSING"`, `"NONE"`, `"N/A"` hoặc tiền tố giả `"UNKNOWN_VIEWER_*"` khi xét cạnh nối. Hai bình luận cùng thiếu định danh người xem hoặc cùng `paraphrase_cluster_id = null` không bao giờ được nối cạnh vì lý do đó.
2. **Chốt chặn 2 — Phân biệt Rò rỉ Thực sự vs. Câu Ngắn Phổ biến Tự nhiên (`Short Generic Utterance Guard`):**
   - **Tạo cạnh nối bắt buộc (`Must-Link Edges`)** giữa hai bản ghi $(c_i, c_j)$ khi có ít nhất một điều kiện hợp lệ khác rỗng sau:
     - Cùng `paraphrase_cluster_id` hoặc cùng `template_family_id` (mẫu chung gốc biến thể/template);
     - Cùng `viewer_thread_id` hoặc cùng `(session_id, guest_session_id)` xác thực;
     - Cùng mã người tham gia diễn tập xuyên buổi **`participant_id`** (chỉ trong schema nghiên cứu offline của `Source B`, ngăn lộ thói quen gõ cá nhân giữa `train` và `test` mà không làm thay đổi ngữ nghĩa `guest_session_id` theo phiên ở hợp đồng sản phẩm);
     - **Trùng lặp gần trên câu dài / có thực thể đặc thù (`Specific Near-Duplicate`):** Khi câu chuẩn hóa có **`>= 5` từ (tokens) HOẶC chứa tên/bí danh SKU / con số quy cách / cụm đặt hàng chi tiết**, và hai bản ghi trùng khít `unaccent_fingerprint` hoặc có `char-3gram Jaccard >= 0.85`.
   - **Quy tắc cho câu ngắn chung tự nhiên (`is_short_generic_utterance = true`):** Các bình luận tự nhiên có **`<= 4` từ VÀ không chứa tên/bí danh SKU hay thực thể hiếm** (ví dụ `"giá bn"`, `"ship ko"`, `"chốt 1"`, `"bao nhiêu vậy"`, `"chào shop"`) xuất hiện độc lập từ những người xem khác nhau ở các phiên khác nhau là tần suất ngôn ngữ tự nhiên của thương mại điện tử, **không nối cạnh xuyên người xem/phiên** để tránh sập đồ thị thành Giant Component.
   - **Báo cáo Độ chồng lấp Bề mặt & Độ nhạy (`Lexical Overlap Sensitivity`):** Để minh bạch 100% ảnh hưởng của các câu ngắn trùng mặt chữ lên điểm số, báo cáo kiểm toán bắt buộc công bố: (a) `%` mẫu `test` có `normalized_text` xuất hiện y hệt trong `train ∪ dev`, và (b) cả hai chỉ số **`Overall Test Macro-F1`** lẫn **`Unseen-Surface Test Macro-F1`** (tính riêng trên tập con các câu `test` chưa từng xuất hiện mặt chữ trong `train`).
3. **Chốt chặn 3 — Chẩn đoán Khả thi Đồ thị & Tương quan Giả Trước khi Chia Tập (`Pre-Split Diagnostics`):**
   - Trước khi chạy phân chia tập, script bắt buộc xuất báo cáo chẩn đoán vào manifest gồm:
     - Tổng số bản ghi $N$ và tổng số thành phần liên thông `split_group_id`;
     - Kích thước thành phần lớn nhất (`max_component_size`) và phân vị `P50 / P90 / P99` *(nếu 1 thành phần chiếm `> 5%` tổng dataset, phải dừng kiểm tra nguyên nhân nối bắc cầu trước khi chia)*;
     - Số lượng `split_group_id` độc lập có mặt trên từng lớp trong 9 lớp `primary_intent` và 4 lớp `moderation_status`;
     - Chỉ số tương quan giả `Product Family × Primary Intent` (`Cramér's V`, `NMI`) và số phiên / dòng sản phẩm hoàn toàn độc lập đủ điều kiện làm `Unseen Product Holdout`;
     - Kiểm tra tính khả thi lấy mẫu `{8, 16, 32}` trên `train` và khả năng phân tầng đủ lớp cho cả `train`, `dev`, `test_seen_product`, `test_unseen_product`.
4. **Chốt chặn 4 — Stratified Group Split, `Unseen Product Holdout` & Bất biến Ưu tiên Chống Rò rỉ:**
   - Toàn bộ một `split_group_id` chỉ đi vào duy nhất một tập (`train`, `dev`, `test_seen_product` hoặc `test_unseen_product`).
   - **Thiết kế `Unseen Product Holdout` (`test_unseen_product`):** Tách riêng các phiên/merchant độc lập bán **các dòng sản phẩm (`product_family` & `sku_id`) chưa từng xuất hiện trong bất kỳ catalog hay câu huấn luyện nào của `train ∪ dev`**, đồng thời giữ lại một phần phiên độc lập bán các dòng sản phẩm đã biết làm **`test_seen_product`** để đo chính xác độ sụt giảm tổng quát hóa (`Generalization Gap`).
   - **Quy tắc Bất khả Xâm phạm (Không phá vỡ Chống Rò rỉ để lấy Product Holdout):** Ràng buộc chống rò rỉ theo `viewer_thread_id`, `participant_id`, `paraphrase_cluster_id`, `template_family_id` và `source_id` / `session_id` có quyền ưu tiên tuyệt đối. **Cấm tách rời các mẫu cùng `split_group_id`, cùng người tham gia `participant_id`, cùng luồng hội thoại viewer hoặc cùng cụm biến thể câu giữa `train/dev` và `test_unseen_product`!** Nếu một thành phần liên thông chạm vào cả sản phẩm đã thấy lẫn sản phẩm chưa thấy, thành phần đó không được đưa vào `test_unseen_product`.
   - Kết quả luôn báo cáo tách riêng theo nguồn (`real` vs `human_simulated` vs `synthetic_adversarial`), theo mức độ thấy sản phẩm (`seen_product` vs `unseen_product`), và nhánh đối chứng `train_human_or_real_only` vs `train_synthetic_augmented`.
   - Khi rút `{8, 16, 32}` mẫu/lớp × 3 seeds (`42`, `100`, `2026`) từ `train`, dùng lấy mẫu vòng tròn đa dạng `split_group_id` (`round-robin across groups`) và ghi nhận `INSUFFICIENT DATA` / `LIMITED GROUP DIVERSITY` thay vì nhân bản mẫu hay rút lậu từ `dev`/`test`.
5. **Chốt chặn 5 — Kiểm soát Gia phả Dữ liệu Xuyên suốt `E01` → `E04` (`Cross-Experiment Lineage`):**
   - **`E01` (`train / dev / test`):** Tập gốc phân hoạch chuẩn (`split_group_id` rời nhau từng đôi một).
   - **`E02` (`p07_adversarial_slang`):** Chỉ lấy mẫu tự nhiên từ các `split_group_id` thuộc `test` hoặc các nhóm mới hoàn toàn chưa từng nằm trong `E01 train ∪ dev` (`0` overlap với `train ∪ dev`). Nếu tạo lát cắt biến đổi có kiểm soát (ví dụ xóa dấu từ câu chuẩn của `test` để đo độ tụt `ΔF1`), phải báo cáo tách biệt dưới nhãn **`Controlled Perturbation Stress Test`**, không gộp chung vào điểm tổng quát hóa tự nhiên.
   - **`E03` (`dev_pairs` vs `test_pairs`):** Mọi bình luận tạo nên `dev_pairs` chỉ được lấy từ `E01 dev` (hoặc kho `dev` riêng), và mọi bình luận trong `test_pairs` chỉ được lấy từ `E01 test` (hoặc kho `test` riêng) — **giao của `comment_id` và `split_group_id` giữa `(E01 train ∪ E01 dev ∪ E03 dev_pairs)` với `E03 test_pairs` bắt buộc bằng `∅`!**
   - **`E04` (`p07_burst_traces`):** Tách rõ phép đo hệ thống xác định (**`System Throughput, Dedup, Idempotency & Queue Fairness Benchmark`**) khỏi các tuyên bố về độ chính xác ngữ nghĩa trên câu chưa từng thấy.

---

### 1.7 Kỷ luật Chọn Mô hình, Quản trị Tập `Held-out Test` & Định nghĩa Mẫu số Chỉ số (`Metric Denominators`)

1. **Kỷ luật Chọn Mô hình & Cấm Tái sử dụng `Test` Sau Phân tích Lỗi (`Test-Set Governance`):**
   - Toàn bộ việc thiết kế từ điển viết tắt, luật regex, chọn bộ tách từ, dừng sớm (`early stopping`), chọn kiến trúc thắng (`PhoBERT-base` vs `SetFit`) và chọn ngưỡng `τ_conf`, `τ_sim` **chỉ được phép thực hiện trên `train` và `dev`**.
   - Tập `held-out test` chỉ được chạy đánh giá sau khi đã đóng băng mã nguồn, trọng số và siêu tham số.
   - **Quy tắc hậu phân tích lỗi (`Post-Failure-Analysis Rule`):** Việc xem ma trận nhầm lẫn và các câu đoán sai trên `held-out test` chỉ mang tính **mô tả trung thực giới hạn của phiên bản đã đóng băng (`v0.1`)**. Nếu nhóm dùng chính các ca lỗi trên `held-out test` đó để viết thêm luật sửa lỗi, thêm từ khóa hay huấn luyện lại phiên bản `v0.2`, tập `test` cũ lập tức bị coi là **đã lộ (`dev-contaminated`)** và mọi tuyên bố cải thiện của `v0.2` bắt buộc phải kiểm chứng trên một tập đánh giá độc lập mới!
2. **Năm Phạm vi Đánh giá & Mẫu số Toán học Rạch ròi (Tránh Nhập nhèm Điểm F1):**
   *Lưu ý: Một mình chỉ số `Macro-F1` của 9 lớp Intent **không bao giờ** đủ để kết luận P07 đạt yêu cầu. Mọi báo cáo kết quả phải xuất đủ các phạm vi có mẫu số tường minh sau:*

   | Phạm vi đánh giá | Tập mẫu số xác định (`Denominator`) | Các chỉ số bắt buộc & Quy tắc xử lý ca biên |
   | :--- | :--- | :--- |
   | **1. Tầng Điều duyệt (`Moderation Eval`)** | Mọi bản ghi không trùng mã sự kiện có `moderation_evaluable == true` ($N_{\text{mod}}$) | `Moderation 4-Class Macro-F1`, `Recall` từng lớp độc hại (`PROMPT_INJECTION`, `ABUSE_BLOCKED`, `SPAM_FLOOD`), và **`Moderation False Positive Rate`** $= \frac{\text{Số mẫu Gold ELIGIBLE bị chặn nhầm}}{\text{Tổng số mẫu Gold ELIGIBLE}}$. |
   | **2. Phân loại Ý định Có Điều kiện (`Conditional Intent Eval` — trọng tâm `E01`)** | Tập con có **Gold `moderation_status == "ELIGIBLE"` $\cap$ `intent_evaluable == true`** ($N_{\text{elig}}$) | `9-Class Primary Intent Macro-F1` (trung bình không trọng số qua 9 lớp), `Per-class Precision/Recall/F1`, và `Unseen-Surface Macro-F1`. *(Nếu chạy ở chế độ tích hợp mà bộ lọc chặn nhầm một câu Gold `ELIGIBLE`, mẫu đó vẫn giữ nguyên trong mẫu số $N_{\text{elig}}$ và tính là dự đoán sai — tuyệt đối không loại khỏi mẫu số để làm đẹp điểm!)* |
   | **3. Toàn tuyến Triage (`End-to-End Pipeline Eval`)** | Mọi bản ghi có `moderation_evaluable == true` $\cap$ `intent_evaluable == true` ($N_{\text{e2e}}$), và tập con có `sku_grounding_evaluable == true` ($N_{\text{sku}}$) | - `End-to-End 12-Outcome Macro-F1` (3 trạng thái chặn + 9 lớp Intent hợp lệ trên $N_{\text{e2e}}$).<br>- Trên $N_{\text{sku}}$ (Gold `ELIGIBLE` đủ ngữ cảnh SKU): `SKU Mode Accuracy`, `SKU Exact-Set Match`, và **`Wrong-SKU Attribution Rate`** $= \frac{\text{Số mẫu xuất } \text{referenced\_sku\_ids} \neq \emptyset \text{ nhưng sai so với Gold}}{N_{\text{sku}}}$ *(bao gồm cả lỗi gán bừa SKU khi Gold là `UNCLEAR`, `OUT_OF_CATALOG` hoặc `NOT_APPLICABLE`!)*. |
   | **4. Đa Ý định & Đa SKU (`Secondary Intent & Multi-SKU Eval`)** | Lát cắt câu có `gold.secondary_intents != []` ($N_{\text{sec}}$) và lát cắt `gold.sku_resolution_mode == "MULTI_SKU"` ($N_{\text{msku}}$) | `Full Intent-Set Exact Match` (`{primary} ∪ secondary`), `Secondary Intent Recall` (đặc biệt tỷ lệ giữ lại nhãn an toàn `ASK_SAFETY_SUITABILITY`), và `Multi-SKU Jaccard / Exact Match`. |
   | **5. Từ chối Đoán mò & Chi phí Chọn lọc (`Abstention / Risk–Coverage`)** | $N_{\text{elig}}$ (cho Intent) và $N_{\text{sku}}$ (cho SKU) | Đường cong **`Coverage` (`%` câu trả lời tự động không abstain)** đối chiếu với **`Selective Error Rate` (`High-Confidence Error Rate` trên phần không abstain)**, kèm `Selective LLM Escalation Rate (%)` và chi phí / 1.000 bình luận. |
   | **6. Tổng quát hóa Sản phẩm Mới (`Seen` vs `Unseen Product Generalization`)** | - `test_seen_product`: $N_{\text{seen, elig}}$<br>- `test_unseen_product`: $N_{\text{unseen, elig}}$ và tập con đủ ngữ cảnh SKU $N_{\text{unseen, sku}}$ | - **`Seen-Product Macro-F1` ($\text{F1}_{\text{seen}}$):** 9-class Intent `Macro-F1` trên $N_{\text{seen, elig}}$.<br>- **`Unseen-Product Macro-F1` ($\text{F1}_{\text{unseen}}$):** 9-class Intent `Macro-F1` trên $N_{\text{unseen, elig}}$ (các sản phẩm `0` lần xuất hiện ở `train ∪ dev`).<br>- **`Generalization Gap` ($\Delta \text{F1}_{\text{prod}}$):** $\Delta \text{F1}_{\text{prod}} = \text{F1}_{\text{seen}} - \text{F1}_{\text{unseen}}$.<br>- **`Unseen-Product SKU Resolution Accuracy`:** Tỷ lệ khớp chính xác đồng thời `(sku_resolution_mode, referenced_sku_ids)` trên $N_{\text{unseen, sku}}$ khi cấp `pinned_catalog` động của sản phẩm mới.<br>- **`Unseen-Product Wrong-SKU Rate`:** Tỷ lệ gán sai `referenced_sku_ids != []` trên $N_{\text{unseen, sku}}$. |

### 1.6 Quản lý Phiên bản, Tái lập & Quyền riêng tư
- Lưu dữ liệu theo cấu trúc sẵn có của thư mục:
  - `data/raw/`: Dữ liệu thô ban đầu (chỉ lưu nếu không chứa PII và có quyền lưu Git; nếu nhạy cảm chỉ lưu manifest tham chiếu).
  - `data/annotations/`: Dữ liệu gán nhãn và biên bản tính IAA.
  - `data/processed/`: Các tập `train.jsonl`, `dev.jsonl`, `test_*.jsonl`, `e02_adversarial.jsonl`, `e03_pairs.jsonl`, `e04_burst_traces.jsonl` kèm tệp `dataset_manifest.json` ghi mã băm **`SHA-256`** của từng tệp.
- Tuyệt đối không đưa số điện thoại thật, địa chỉ nhà, tài khoản mạng xã hội cá nhân hoặc khóa API vào bất kỳ tệp nào trong `data/` hay `results/`.

---

## 2. Đặc tả Thực thi Chi tiết 4 Thí nghiệm (`P07-E01` đến `P07-E04`)

### 2.1 Thí nghiệm `P07-E01` — So sánh Công bằng Mô hình Phân loại Ý định Độc lập Sản phẩm & Nghiên cứu Ablation Tiền xử lý

1. **Research Question:** Trên tập kiểm thử tiếng Việt livestream cố định (gồm cả `Seen-Product Holdout` và `Unseen-Product Holdout`), kiến trúc phân loại nhỏ nào (`PhoBERT-base` hay `SetFit`) kết hợp với phương án biểu diễn văn bản đầu vào nào đạt khả năng tổng quát hóa ý định tốt nhất ở `{8, 16, 32, full}` mẫu/lớp mà không học vẹt theo tên sản phẩm, đồng thời giảm được bao nhiêu độ trễ và chi phí so với gọi LLM cho mọi bình luận hợp lệ? (`PoC Plan v1.0` `P07-E01`).
2. **Hypothesis (`PROPOSED / VALIDATION PENDING`):**
   - Ở mức dữ liệu ít (`8–16` mẫu/lớp), `SetFit` có thể hội tụ ổn định hơn; khi tăng số mẫu (`32` mẫu/lớp đến `full`), `PhoBERT-base` hoặc `SetFit` kết hợp `Rules + Selective LLM` có thể tiệm cận chất lượng của `B1` với độ trễ P95 và chi phí API thấp hơn đáng kể.
   - **Giả thuyết mở về Ablation Tiền xử lý (`Không mặc định trước khi đo`):** Chuẩn hóa tiếng lóng (`Normalized Text`) có thể cải thiện tách từ và khớp từ vựng; việc che thực thể sản phẩm theo danh mục phiên động (`Product Entity Masked Text` thay tên/bí danh sản phẩm bằng `<PRODUCT>` hoặc `<PRODUCT_1>`, `<PRODUCT_2>`) *có thể* thu hẹp `Generalization Gap` trên `Unseen Products` nhờ chặn học vẹt tên mặt hàng, **nhưng cũng có thể làm giảm độ chính xác** nếu bộ dò thực thể che nhầm từ đồng âm mất dấu (`"trà"` vs `"trả"`, `"điều"` vs `"điều kiện"`) hoặc xóa mất ngữ cảnh gắn với đặc tính vật lý sản phẩm. Chỉ kết quả thực nghiệm trên `dev` và `test_unseen_product` mới quyết định phương án được chọn!
3. **Input Datasets:** Tập `train` (`{8, 16, 32} × 3 seeds` + `full train`), tập `dev` (chọn siêu tham số, chọn biến thể tiền xử lý và ngưỡng `τ_conf`), cùng hai tập kiểm thử độc lập đã khóa `SHA-256`: **`test_seen_product`** và **`test_unseen_product`**.
4. **Baselines, Candidate Models & 4-Way Preprocessing Ablation (`PROPOSED / VALIDATION PENDING`):**
   - *Kiến trúc mô hình (9 lớp đầu ra cố định độc lập sản phẩm — tuyệt đối không chứa mã SKU):*
     - `B0_rules_only`: Chuẩn hóa + từ điển từ khóa/regex xác định.
     - `B1_rules_plus_llm_all`: Tầng lọc luật cơ bản + gọi LLM có cấu trúc cho tất cả bình luận `ELIGIBLE` (`PoC Plan v1.0` `P07.5` Phương án A).
     - `C1_phobert_base`: Tách từ tiếng Việt + fine-tune `vinai/phobert-base` (giấy phép **MIT**; **cấm** dùng `phobert-base-v2` AGPLv3).
     - `C2_setfit_multilingual`: Huấn luyện `SetFit` trên backbone đa ngữ giấy phép sạch (ví dụ `intfloat/multilingual-e5-small` MIT).
     - `H1_hybrid_selective_llm`: `Rules` + tổ hợp `(Model, Preprocessing)` thắng trên `dev` + gọi `Selective LLM` khi `intent_confidence < τ_conf`.
   - *4 Biến thể Tiền xử lý Đầu vào (`Input Preprocessing Ablation` — đánh giá cho `C1` và `C2`):*
     1. **`V0_raw_text` (`Raw Text`):** Văn bản gốc chỉ chuẩn hóa Unicode `NFC` an toàn tối thiểu.
     2. **`V1_normalized_text` (`Normalized Text`):** Unicode `NFC` + chuẩn hóa khoảng trắng, rút gọn ký tự kéo dài và chuẩn hóa viết tắt/slang phổ biến.
     3. **`V2_product_masked_text` (`Product Entity Masked Text`):** Đối chiếu với `SessionTriageContext.pinned_catalog` của phiên để thay thế các span khớp tên/bí danh sản phẩm trong văn bản gốc bằng token `<PRODUCT>` (hoặc `<PRODUCT_1>`, `<PRODUCT_2>` khi câu nhắc nhiều sản phẩm phân biệt nhằm bảo toàn tín hiệu so sánh).
     4. **`V3_normalized_plus_product_masked` (`Normalized + Product Masked Text`):** Thực hiện chuẩn hóa `V1` trước, sau đó áp dụng bước che thực thể sản phẩm động theo `pinned_catalog` như `V2`.
5. **Biến độc lập & Biến phụ thuộc:**
   - *Độc lập:* Kiến trúc mô hình (`B0`, `B1`, `C1`, `C2`, `H1`), biến thể tiền xử lý (`V0`, `V1`, `V2`, `V3`), kích thước tập huấn luyện mỗi lớp (`8`, `16`, `32`, `full`), `random_seed` (`42`, `100`, `2026`), môi trường chạy (`CPU` vs `GPU`).
   - *Phụ thuộc:* **`Seen-Product Macro-F1`**, **`Unseen-Product Macro-F1`**, **`Generalization Gap` ($\text{F1}_{\text{seen}} - \text{F1}_{\text{unseen}}$)**, `Per-class F1`, `Unseen-Surface Macro-F1`, `Moderation FPR`, `High-Confidence Error Rate`, độ trễ `P50 / P95` (ms, tính cả thời gian chuẩn hóa/masking + tách từ + inference), RAM/VRAM đỉnh, tỷ lệ gọi LLM (`%`) và chi phí / 1.000 bình luận.
6. **Evaluation Metrics:** Đầy đủ các chỉ số thuộc Phạm vi 1, 2, 5 và **Phạm vi 6 (`Seen` vs `Unseen Product Generalization`)** tại Mục 1.7, `Confusion Matrix` 9×9 tách riêng trên `test_seen_product` và `test_unseen_product`, `Warm Latency P50/P95 (ms)`, `Tokens & Cost / 1k comments`.
7. **Experimental Procedure:**
   - Khóa `dataset_manifest_v0.1.json`, kiểm tra `0` rò rỉ cụm câu/người tham gia và ghi nhận chỉ số tương quan giả `Product × Intent`.
   - Huấn luyện `C1` và `C2` qua các biến thể `{V0, V1, V2, V3}` (có thể chạy ma trận đầy đủ trên `16-shot` & `full train`, và chạy biến thể tốt nhất trên toàn bộ `{8, 16, 32, full} × 3 seeds` theo lựa chọn trên `dev`); **chỉ dùng `dev` (gồm cả lát cắt sản phẩm giữ lại trong `dev` nếu có) để chọn biến thể tiền xử lý và ngưỡng `τ_conf`**, tuyệt đối không nhìn `test_seen_product` hay `test_unseen_product` để chọn biến thể!
   - Đo độ trễ với `warmup_runs >= 20` câu trước khi bấm giờ `steady-state` từng câu lẻ (`batch_size = 1`).
8. **Failure Analysis:** Đối chiếu trực tiếp lỗi của `V0/V1` (liệu mô hình có đoán sai Intent khi gặp tên sản phẩm lạ ở `test_unseen_product` không?) với lỗi của `V2/V3` (liệu bước che `<PRODUCT>` có che nhầm từ đồng âm hoặc làm mất ngữ cảnh câu hỏi thông số/cách dùng không?).
9. **Evidence to Save:** `results/metrics/P07-E01_<run_id>.json` (theo chuẩn `ExperimentManifest`), ma trận nhầm lẫn dạng JSON/CSV, tệp dự đoán từng mẫu trên `test`, phiên bản checkpoint và giấy phép kiểm tra.
10. **Acceptance Criteria:**
    - Không rò rỉ dữ liệu giữa `train`/`dev`/`test` (`0` cluster overlap — **Hard Criterion**).
    - Độ trễ P95 đường nóng hướng tới ngân sách khởi điểm `≤ 300 ms` (`PROPOSED / TO VALIDATE` — `Baseline v1.2` §11.2).
    - Ngưỡng `Macro-F1` tối thiểu và mức chi phí chấp nhận được: **`THRESHOLD REQUIRES REVIEW`** *(chốt cùng Reviewer trước khi tuyên bố `VALIDATED`)*.
11. **Decision Rule:** Chọn ứng viên (`PhoBERT-base` hoặc `SetFit`) có sự cân bằng tốt nhất giữa `Macro-F1`, độ ổn định ít mẫu, `P95 latency` và giấy phép sạch để đưa sang `E02–E04`; nếu dữ liệu chỉ mới là `synthetic`, giữ trạng thái tối đa ở `IN EXPERIMENT` (chưa nâng lên `VALIDATED` cho tới khi có `held-out real test`).
12. **Dependencies & Blockers:** Phụ thuộc việc khóa [p07-annotation-guideline-v0.1.md](./p07-annotation-guideline-v0.1.md), hoàn tất bộ dữ liệu `v0.1` và cấu hình adapter cho nhánh LLM đối chứng (`B1`/`H1`).

---

### 2.2 Thí nghiệm `P07-E02` — Độ bền Ngôn ngữ Khó & Phân giải Đa SKU Động trên Cả `Seen` và `Unseen Products`

1. **Research Question:** Tiếng Việt không dấu, viết tắt/slang nặng, câu hỏi nối tiếp theo ngữ cảnh người xem và câu nhắc nhiều SKU làm suy giảm `Intent Macro-F1` (qua các biến thể tiền xử lý `V0..V3`) và độ chính xác phân giải SKU (`Seen` vs **`Unseen-Product SKU Resolution Accuracy` / `Wrong-SKU Rate`**) bao nhiêu phần trăm khi cấp danh mục `pinned_catalog` động tại thời điểm chạy? (`PoC Plan v1.0` `P07-E02`).
2. **Hypothesis:** Bộ phân giải thực thể theo phạm vi phiên động (`Session-Scoped SKU Resolver`) đối chiếu trực tiếp tên, bí danh và quy cách của `SessionTriageContext.pinned_catalog` nên duy trì được **`Unseen-Product SKU Resolution Accuracy` cao và `Unseen-Product Wrong-SKU Rate` tối thiểu** mà không cần huấn luyện lại mô hình trên SKU mới, nhờ chuyển mọi ca mơ hồ về `UNCLEAR`.
3. **Input Datasets:** Tập `p07_adversarial_slang_v0.1` (`>= 200` mẫu khó tách rõ lát cắt **`Seen-Product Catalogs`** — gồm fixture 5 SKU P05 — và **`Unseen-Product Catalogs`** — các phiên bán mặt hàng mới chưa từng xuất hiện ở `train/dev`, kèm `viewer_thread_state`).
4. **Baselines & Candidate Approaches:**
   - Tổ hợp biến thể tiền xử lý (`V0_raw`, `V1_norm`, `V2_prod_masked`, `V3_norm_plus_prod_masked`) × (`C1_phobert_base`, `C2_setfit_multilingual`, `H1_hybrid_selective_llm`) kết hợp cùng `SessionScopedSkuResolver` chạy trên `pinned_catalog` động.
   - Đối chứng ngây thơ (`Naive Baseline` — chỉ dùng để chứng minh rủi ro): gán mặc định mọi câu thiếu tên sản phẩm vào `active_sku_id`.
5. **Biến độc lập & Biến phụ thuộc:**
   - *Độc lập:* Nhóm hiện tượng ngôn ngữ (`no_diacritics`, `slang`, `multi_sku`, `contextual_followup`, `ambiguous_sku`, `prompt_injection`), trạng thái sản phẩm (`seen_product` vs `unseen_product`), biến thể tiền xử lý (`V0..V3`), lựa chọn mô hình.
   - *Phụ thuộc:* Độ sụt giảm `Intent Macro-F1` (`ΔF1` không dấu vs có dấu, và `Generalization Gap` giữa `seen` vs `unseen`), `Seen-Product SKU Resolution Accuracy`, **`Unseen-Product SKU Resolution Accuracy`**, **`Unseen-Product Wrong-SKU Attribution Rate`**, `Prompt Injection Block Rate`, `Cross-Viewer Bleed Count`.
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
    - **`Cross-SKU Bad Merge Rate = 0`**, **`Secondary-Intent Silent Drop Rate = 0`** (không gộp câu đa ý vào nhóm đơn ý làm mất câu hỏi phụ) và **`Provenance Loss = 0`** (không mất `comment_id` thành viên nào) trên bộ kiểm thử xác định (**Hard Invariants `INV-P07-05`, `INV-P07-06`**).
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
    - **`Duplicate Task Count = 0`**, **`Lost Unacked Proposal Count = 0`** (khôi phục đúng `ResponseGroupProposal` khi retry trước lúc P08 ACK mà không nhân đôi task), **`Post-Committed Merge Count = 0`**, **`Cross-Tenant/Session/Epoch Leak = 0`**, **`Lost Viewer Record = 0`** (**Hard Gates G2/G3/G4**).
    - Ngưỡng `Queue P95` và chỉ số `Fairness`: **`THRESHOLD REQUIRES REVIEW`**.
11. **Decision Rule:** Xác nhận hợp đồng `P07 -> P08` hoạt động trơn tru dưới tải `W2` trước khi bàn giao sang simulator `P08/P09` và tích hợp `apps/api/modules/conversation/`.
12. **Dependencies & Blockers:** Phụ thuộc pipeline từ `E01–E03` và module `P08MockScheduler` viết theo đúng [p07-contract-v0.1.md](./p07-contract-v0.1.md).

---

## 3. Khuôn mẫu Lưu Bằng chứng Tái lập (`ExperimentManifest`)

Mọi lượt chạy `P07-E01..E04` bắt buộc xuất tệp JSON vào `results/metrics/` tuân thủ chuẩn tái lập của `experiments/README.md` (§5).

> [!CAUTION]
> **Quy tắc trung thực của `hard_gates` trong `ExperimentManifest`:**
> Mỗi cổng kiểm tra cứng chỉ được nhận một trong 4 trạng thái chuỗi tường minh: **`"NOT_RUN"` \| `"PASS"` \| `"FAIL"` \| `"NOT_APPLICABLE"`**.
> - Trong khuôn mẫu cấu hình/khởi tạo trước khi chạy, mọi cổng trong phạm vi thí nghiệm bắt buộc để mặc định là **`"NOT_RUN"`** (tuyệt đối không gán cứng `true` trước khi kiểm thử thực tế!).
> - Mỗi thí nghiệm chỉ chấm `"PASS"` / `"FAIL"` cho các cổng thực sự được đo trong thí nghiệm đó; các cổng thuộc thí nghiệm khác (ví dụ `zero_post_committed_merge` không nằm trong phạm vi `P07-E01`) phải ghi **`"NOT_APPLICABLE"`**.

```json
{
  "experiment_id": "P07-E01",
  "run_id": "TEMPLATE_NOT_EXECUTED",
  "created_at": null,
  "git_commit_hash": "<commit_sha>",
  "dirty_worktree": false,
  "dataset_provenance": {
    "manifest_path": "data/processed/dataset_manifest_v0.1.json",
    "manifest_sha256": "<sha256>",
    "train_subset_id": "train_16shot_seed42",
    "evaluated_split_name": "test_real | test_human_simulated",
    "evaluated_split_sha256": "<sha256>",
    "data_origins_in_train": ["real_permissioned_commerce", "human_simulated_live"],
    "data_origins_in_eval": ["real_permissioned_commerce"],
    "contains_synthetic_in_eval": false,
    "permission_and_pii_scrub_verified": false
  },
  "model_info": {
    "candidate_name": "C1_phobert_base",
    "checkpoint_id": "vinai/phobert-base",
    "checkpoint_revision": "<hf_commit_hash>",
    "checkpoint_license": "MIT",
    "word_segmenter": "<tool_name_and_version_or_NA>",
    "word_segmenter_license": "<license_or_NA>"
  },
  "environment": {
    "python_version": "3.13.x",
    "os_platform": "<os_version>",
    "cpu_model": "<cpu_model>",
    "gpu_model": "<gpu_sku_or_NONE>",
    "packages": {
      "torch": "<version>",
      "transformers": "<version>",
      "setfit": "<version_or_NA>",
      "scikit-learn": "<version>"
    }
  },
  "config_provenance": {
    "config_path": "configs/e01_phobert_base.yaml",
    "config_sha256": "<sha256>",
    "preprocessing_variant": "V0_raw | V1_norm | V2_prod_masked | V3_norm_plus_prod_masked",
    "shots_per_class": 16,
    "effective_unique_split_groups_min": null,
    "insufficient_data_classes": [],
    "seed": 42,
    "warmup_runs": 20
  },
  "metrics": {
    "moderation_eval": {},
    "conditional_intent_eval": {},
    "unseen_product_generalization_eval": {},
    "end_to_end_eval": {},
    "secondary_intent_eval": {},
    "selective_abstention_eval": {},
    "latency_and_cost": {}
  },
  "hard_gates": {
    "zero_split_cluster_leak": "NOT_RUN",
    "zero_anti_leakage_violation_in_product_holdout": "NOT_RUN",
    "zero_pilot_in_heldout_test": "NOT_RUN",
    "zero_agpl_checkpoint": "NOT_RUN",
    "spurious_product_intent_audit_logged": "NOT_RUN",
    "zero_cross_viewer_context_bleed": "NOT_APPLICABLE",
    "zero_cross_sku_bad_merge": "NOT_APPLICABLE",
    "zero_secondary_intent_silent_drop": "NOT_APPLICABLE",
    "zero_provenance_loss": "NOT_APPLICABLE",
    "zero_post_committed_merge": "NOT_APPLICABLE",
    "zero_duplicate_or_lost_proposal": "NOT_APPLICABLE",
    "zero_cross_tenant_or_epoch_accept": "NOT_APPLICABLE"
  },
  "decision": "NOT_RUN",
  "reviewer": null,
  "notes": "Khuôn mẫu chuẩn hóa trước thực nghiệm; toàn bộ cổng kiểm tra đang ở trạng thái NOT_RUN / NOT_APPLICABLE."
}
```
