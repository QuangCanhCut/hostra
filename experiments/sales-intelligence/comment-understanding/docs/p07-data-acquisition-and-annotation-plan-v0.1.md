# P07 — Kế hoạch Thu thập & Gán nhãn Bộ dữ liệu Bình luận Tiếng Việt Thực tế

| Thuộc tính | Giá trị |
| :--- | :--- |
| **Mã tài liệu** | `P07-DOC-06` |
| **Phiên bản / Ngày** | `PROPOSED v0.1.3` — `26/11/2026` |
| **Trạng thái phê duyệt** | `IN REVIEW — PILOT-READY DRAFT` *(Ưu tiên thực thi `Data Acquisition Pilot` 50–100 bình luận trước; các chỉ tiêu quy mô tập chính mang trạng thái `PROPOSED` sẽ được hiệu chỉnh dựa trên bằng chứng Pilot)* |
| **Mục tiêu vận hành** | Cung cấp quy trình thực địa theo hướng **Real-First**: khảo sát nguồn thật, kiểm tra quyền/pháp lý/PII, chạy Pilot `50–100` mẫu, bổ sung diễn tập người thật khi cần, gán nhãn kép độc lập và chia tập chống rò rỉ cho `P07-E01..E04` |
| **Tài liệu liên kết** | [p07-problem-and-requirements.md](./p07-problem-and-requirements.md) · [p07-contract-v0.1.md](./p07-contract-v0.1.md) · [p07-annotation-guideline-v0.1.md](./p07-annotation-guideline-v0.1.md) · [p07-dataset-and-evaluation-protocol.md](./p07-dataset-and-evaluation-protocol.md) · [p07-experiment-readiness.md](./p07-experiment-readiness.md) |

> [!IMPORTANT]
> **Nguyên tắc nền tảng (Real-First & Evidence-Driven):**
> 1. **Ưu tiên khảo sát dữ liệu livestream thực tế có phép (`Source A — real_permissioned_commerce`) trước tiên**, thay vì ấn định cứng tỷ lệ mô phỏng hay vội vàng thu thập đại trà khi chưa chạm vào dữ liệu thật (`Design → Collect Pilot → Inspect → Refine → Main Dataset → Experiment`).
> 2. **Không dùng hàng trăm câu do LLM tự sinh làm bộ dữ liệu chính** rồi coi điểm F1 trên đó là bằng chứng mô hình hoạt động ngoài thực tế. `Source B` (`human_simulated_live`) đóng vai trò nguồn bổ sung/dự phòng chủ động mở khóa tiến độ, còn `Source C` (`synthetic`) bị giới hạn nghiêm ngặt cho ca hiếm/an toàn/đối chứng tăng cường (`synthetic_augmented` vs `real_and_human` / `human_only`).
> 3. **Tách biệt tuyệt đối dữ liệu Pilot đã dùng để sửa luật/guideline khỏi `Held-out Test`:** Bất kỳ mẫu Pilot nào đã được nhóm mở ra đọc kỹ để chỉnh sửa taxonomy, từ điển viết tắt hoặc luật phân giải đều không được tái sử dụng làm tập kiểm thử độc lập cuối cùng.

---

## 1. Dataset Objectives & Requirements

Bộ dữ liệu `v0.1` của P07 phải đáp ứng đồng thời yêu cầu thực nghiệm của 4 bài toán trong `Technical Research & PoC Plan v1.0` (§5 P07, §8.1, §9.2):

1. **Phục vụ `P07-E01` (So sánh Classifier Độc lập Sản phẩm & Tiền xử lý Ablation):**
   - Đủ độ đa dạng từ vựng tự nhiên, đa dạng mặt hàng, merchant và phiên livestream trên **9 lớp `primary_intent` độc lập sản phẩm (`product-agnostic`)** và **4 trạng thái `moderation_status`** để huấn luyện ở `{8, 16, 32, full}`, so sánh công bằng 4 phương án tiền xử lý (`Raw`, `Normalized`, `Product Masked`, `Normalized + Product Masked` — `PROPOSED / VALIDATION PENDING`), đồng thời đo được khả năng tổng quát hóa trên cả **`Seen-Product Holdout`** lẫn **`Unseen-Product Holdout`** (các sản phẩm chưa từng xuất hiện trong `train/dev`).
2. **Phục vụ `P07-E02` (Độ bền ngôn ngữ khó & Phân giải SKU trên Danh mục Động):**
   - Bắt được hành vi gõ tiếng Việt thực trên thiết bị di động: bỏ dấu hoàn toàn, mất dấu cục bộ do bộ gõ Telex/VNI, viết tắt thương mại điện tử (`bn`, `hsd`, `dc`, `ko`, `ship cod`, `freeship`), câu nối tiếp dùng đại từ theo mạch người xem (`viewer_thread_id`) và câu nhắc nhiều sản phẩm trên nhiều cấu hình danh mục phiên động khác nhau (kể cả danh mục sản phẩm mới chưa từng thấy lúc train).
3. **Phục vụ `P07-E03` (Đánh giá Gom nhóm Ngữ nghĩa & Abstention):**
   - Có các cặp bình luận thực sự hỏi cùng một câu hỏi từ nhiều người xem khác nhau **và** các cặp bẫy dễ gộp nhầm (cùng `primary_intent` và cùng `SKU` nhưng hỏi hai thuộc tính khác nhau như *"hạn sử dụng"* vs *"nhiệt độ nước pha trà"*, hoặc khác SKU, hoặc 1 câu rõ SKU + 1 câu `UNCLEAR`).
4. **Phục vụ `P07-E04` (Mô phỏng Tải dồn dập & Khử trùng):**
   - Có chuỗi dấu thời gian thực tế để mô phỏng nhịp bình luận dồn dập khi host đọc giá/chốt đơn, kết hợp tiêm sự kiện trùng khóa mạng (`external_dedup_key`) và flood từ một tài khoản.

---

## 2. Data Source Strategy (Phân tích & Lựa chọn Nguồn Dữ liệu)

### 2.1 Phân tích 3 Nguồn Dữ liệu Khả thi

#### Source A — Permissioned Real Livestream Comments (`real_permissioned_commerce`)
Bình luận thực tế từ đa dạng các buổi livestream bán hàng thực phẩm đóng gói, nông sản chế biến, đặc sản vùng miền/OCOP, đồ uống, ngũ cốc, gia vị, bánh mứt, thảo mộc... **Tuyệt đối không giới hạn việc thu thập dữ liệu thực tế trong 5 SKU mẫu kế thừa từ P05** (bộ 5 SKU của P05 chỉ dùng làm `controlled integration fixtures` để nối thử `P07 -> P08 -> P05 -> P06`; việc thu thập càng nhiều dòng sản phẩm và merchant khác nhau càng giúp kiểm chứng tính `product-agnostic` và tạo tập `Unseen Product Holdout` chất lượng cao).

- **Các kênh tiếp cận hợp pháp (Không vi phạm Điều khoản Nền tảng):**
  1. **Hợp tác trực tiếp với Chủ shop / Hợp tác xã OCOP quen biết (Ưu tiên số 1):** Liên hệ 1–3 nhà bán hàng nhỏ/hợp tác xã nông sản địa phương, cựu sinh viên khởi nghiệp hoặc đối tác thử nghiệm của nhóm. Chủ kênh tự trích xuất lịch sử bình luận từ công cụ quản lý bán hàng hợp pháp của chính họ hoặc cho phép ghi chép bình luận từ buổi live thuộc sở hữu của họ.
  2. **Buổi Livestream giới thiệu thử nghiệm do chính nhóm HOSTRA tự tổ chức có khách mời ngoài:** Mở phiên live thử nghiệm kín (invite-only) giới thiệu các sản phẩm mẫu hợp lệ với sự tham gia của người xem bên ngoài nhóm phát triển, có thông báo và xác nhận đồng ý trước khi vào phòng.
  3. **Tập dữ liệu học thuật tiếng Việt đã công bố công khai (chỉ dùng phụ trợ nếu khớp miền và giấy phép):** Chỉ sử dụng khi bộ dữ liệu có giấy phép rõ ràng cho phép nghiên cứu/phát triển và đã được kiểm chứng không vi phạm quyền riêng tư; không mặc định thay thế miền livestream OCOP.
- **Cách xin quyền thu thập & sử dụng:** Lập **Phiếu Chấp thuận Cung cấp Dữ liệu Nghiên cứu (1 trang)** nêu rõ: (a) chỉ dùng nội bộ cho nghiên cứu mô hình hiểu câu hỏi của dự án HOSTRA AI, (b) xóa/ẩn danh toàn bộ thông tin cá nhân (SĐT, địa chỉ, tên tài khoản người mua) trước khi lưu vào kho nghiên cứu, (c) không công khai dữ liệu thô hay bí mật kinh doanh của shop lên Internet, (d) quyền yêu cầu xóa dữ liệu bất kỳ lúc nào.
- **Phương pháp lấy dữ liệu hợp lệ:** Nhận tệp xuất (`CSV`/`XLSX`/`JSON`) trực tiếp từ chủ shop hoặc nhập liệu thủ công từ bản ghi buổi live đã được chủ sở hữu cho phép bằng văn bản. **Tuyệt đối cấm** viết bot cào dữ liệu tự động (scraping), chọc API không chính thức hoặc thu thập từ kênh của bên thứ ba chưa cho phép (`Risk R18`).
- **Metadata giữ lại (nếu nguồn có cung cấp):** Nội dung bình luận thô, mốc thời gian tương đối trong phiên (nếu không có ghi `"MISSING"`), mã người bình luận đã băm một chiều (nếu không phân biệt được ghi `"UNKNOWN"`), danh sách sản phẩm bán trong buổi live đó và sản phẩm đang cầm trên tay lúc bình luận (nếu chỉ có danh sách chung mà không rõ thời điểm chuyển món thì ghi `active_sku_at_comment_time = "UNKNOWN"`, **không tự đoán**).
- **Rủi ro quyền riêng tư & bản quyền:** Bình luận chốt đơn ở Việt Nam rất hay chứa **số điện thoại và địa chỉ nhà thật** ngay trong câu chữ (`"chốt 2 hũ mật ong 0912xxxxxx số 15 ngõ..."`). Bắt buộc phải chạy bước quét khử PII trên máy cục bộ an toàn trước khi đưa vào tệp làm việc chung.

#### Source B — Human-Simulated Live Comments (`human_simulated_live`)
Tổ chức các buổi diễn tập livestream bán hàng nội bộ có kịch bản sản phẩm thật nhưng người tham gia đóng vai người xem và gõ bình luận hoàn toàn tự phát theo thời gian thực.

- **Quy mô người tham gia & Thiết kế Đa dạng Danh mục Sản phẩm (`PROPOSED` — hiệu chỉnh lại sau Pilot):**
  - **Không bó hẹp trong 5 SKU của P05:**
    - *Nhóm phiên Fixture Tham chiếu (`Reference Integration Sessions`):* Sử dụng bộ 5 SKU chuẩn kế thừa từ P05 (Mật ong hoa cà phê, Trà Shan Tuyết, Hạt điều rang củi, Xoài sấy dẻo, Cà phê rang xay) để có bộ fixture kiểm thử xuyên suốt `P07 -> P08 -> P05 -> P06`.
    - *Nhóm phiên Đa dạng & Sản phẩm Chưa từng thấy (`Diverse & Unseen-Product Sessions`):* Ghim các danh mục sản phẩm hoàn toàn khác biệt không trùng tên/nhóm hàng với tập `train` (ví dụ: bánh pía sầu riêng, viên tinh bột nghệ, nước mắm truyền thống, rong biển kẹp hạt, yến mạch ngũ cốc, đông trùng hạ thảo sấy...) với người tham gia (`participant_id`) tách rời nhằm xây dựng tập **`Unseen Product Holdout`** sạch rò rỉ.
  - Tham chiếu khởi điểm: nhiều buổi diễn tập ngắn (`20–25` phút/buổi) với nhóm người tham gia đóng vai người xem độc lập (ưu tiên mở rộng nhiều người tham gia khác nhau giữa các buổi thay vì dùng đi dùng lại một nhóm nhỏ), ít nhất 60% gõ trên **điện thoại di động**. Số lượng buổi và số người tham gia chính thức được tính toán lại dựa trên tốc độ bình luận tự nhiên quan sát được ở vòng Pilot.
  - **Cấm ép định mức số lượng bình luận trên mỗi người (`No Forced Comment Quota`):** Tuyệt đối **không** yêu cầu mỗi người tham gia phải gõ đủ $X$ bình luận/buổi (việc ép chỉ tiêu khiến người gõ bịa câu lặp khuôn mẫu nhân tạo). Người tham gia chỉ bình luận tự nhiên theo nhu cầu vai diễn và nhịp nói của Host; nếu cần thêm dữ liệu thì tăng số buổi hoặc mời thêm người mới.
- **Thiết kế kịch bản phiên & Đa ngữ cảnh SKU:**
  - Mỗi buổi ghim tổ hợp 3 hoặc 5 SKU khác nhau; người dẫn chuyển `Active SKU` mỗi `5` phút (ghi lại chính xác bảng mốc thời gian chuyển `Active SKU`, ví dụ `00:00–05:00 = SKU-HONEY-01`, `05:00–10:00 = SKU-TEA-02`...).
- **Cách tránh người tham gia chép lại câu hỏi mẫu (Anti-Template Bias):**
  - **Tuyệt đối không phát danh sách câu hỏi mẫu hay tên 9 nhãn Intent** cho người tham gia!
  - Phát cho mỗi người tham gia một **Thẻ Vai diễn & Tình huống Mua hàng (Persona Goal Card)** dạng mục tiêu mở, ví dụ:
    - *Thẻ P1 (Người mua kỹ tính về sức khỏe):* "Mẹ bạn bị mất ngủ và huyết áp hơi cao, bạn đang tìm mua quà biếu dưới 300k; hãy hỏi kỹ xem dùng món nào an toàn và cách dùng."
    - *Thẻ P2 (Người vào trễ, hỏi dồn nhiều lượt):* "Bạn vào phòng lúc phút thứ 7 khi host đang nói về Trà, nhưng bạn nhìn thấy hũ Mật ong ở kệ sau nên hỏi về Mật ong trước, sau đó hỏi tiếp 2 câu ngắn nối đuôi nhau mà không nhắc lại tên sản phẩm."
    - *Thẻ P3 (Người săn mã / lo vỡ hàng khi ship xa):* "Bạn ở tỉnh xa, hay hỏi gộp giá combo + phí ship + lỡ vỡ chai thủy tinh thì đổi thế nào bằng thói quen nhắn tin viết tắt hàng ngày của bạn."
    - *Thẻ P4 (Người xem gây nhiễu thực tế):* "Thỉnh thoảng thả cảm xúc, khen giọng người dẫn, hỏi một món shop không bán (như khô gà/bánh pía), hoặc hỏi trống không `'cái hộp kia bao nhiêu'`."
- **Cách ghi nhận Timestamps, Viewer Threads & Mã Người tham gia Xuyên buổi (`participant_id`):**
  - Dùng phòng chat riêng có lưu lịch sử theo giây gắn cho mỗi người trong phiên một `guest_session_id` theo phạm vi phiên (`guest_sim_s01_p01` ... `guest_sim_s01_p12`). Đồng thời, nếu một tình nguyện viên tham gia nhiều hơn 1 buổi diễn tập, Data Steward gắn một mã nghiên cứu ẩn danh xuyên buổi **`participant_id`** (ví dụ `part_01` — chỉ tồn tại trong Offline Research Schema để thuật toán chia tập chống lộ văn phong cá nhân giữa `train` và `test`, tuyệt đối không đưa vào hợp đồng runtime của sản phẩm). Nhờ đối chiếu dấu thời gian từng bình luận với nhật ký đổi món của Host, ta thu được chính xác `collection_timestamp`, `guest_session_id`, `viewer_thread_id` và `active_sku_at_comment_time`.
- **Sự đồng ý & Bảo vệ người tham gia:** Trước buổi diễn tập, người tham gia tích xác nhận đồng ý đóng góp câu chữ cho tập dữ liệu nghiên cứu HOSTRA AI, được dặn không gõ SĐT/địa chỉ cá nhân thật (nếu diễn cảnh chốt đơn thì gõ chuỗi giả quy ước `0900000000`), và bảng ánh xạ tên thật sang `participant_id` / `guest_sim_*` lưu cục bộ ngoài Git.
- **Ranh giới minh bạch:** `human_simulated_live` là bình luận do con người thật tự nghĩ và tự gõ theo nhịp trực tiếp, vượt trội hơn hẳn LLM synthetic, **nhưng không được trình bày là dữ liệu thương mại thực tế (`real_permissioned_commerce`)**.

#### Source C — Controlled Synthetic Data (`synthetic_seed_template` / `synthetic_llm_human_reviewed`)
Chỉ dùng làm nguồn **bổ trợ có kiểm soát chặt chẽ** cho các ca biên hiếm/an toàn và thí nghiệm đối chứng tăng cường dữ liệu:
- **Phạm vi sử dụng hợp lệ duy nhất:** (1) Các câu gài lệnh tấn công hệ thống (`PROMPT_INJECTION` — bắt buộc test an toàn `TC18`), (2) Các câu mồi công dụng chữa bệnh tinh vi đối với thực phẩm đóng gói (`R17`), (3) Tổ hợp so sánh chéo nhiều SKU hoặc cặp bẫy khác thuộc tính rất thưa trong tự nhiên, (4) Các biến thể lỗi gõ cực đoan / mất dấu đồng âm cho lát cắt stress-test ở `P07-E02`, (5) Kịch bản bơm sự kiện trùng khóa/burst cho `P07-E04`, và (6) Nhánh thực nghiệm đối chứng **`synthetic_augmented` so sánh trực tiếp với `real_and_human` / `human_only`** trong `P07-E01`.
- **Ràng buộc provenance & human review:** Mỗi mẫu synthetic bắt buộc gắn `template_family_id` (hoặc `prompt_recipe_id`), `paraphrase_cluster_id`, và `reviewed_by` (người thật duyệt từng câu). **Không ấn định tỷ lệ phần trăm cứng cho `Source C` trước Pilot, không dùng làm nguồn chính của dataset, và cấm tuyệt đối trộn vào `test_real` hay `test_human_simulated`**.

### 2.2 Bảng Đối sánh Chiến lược 3 Nguồn Dữ liệu (Real-First)

| Source | Availability | Collection Method | Permission & Governance | Cost | Expected Diversity | Domain Relevance | Risks | Vai trò theo Bằng chứng Thực tế |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Source A (`Ưu tiên #1`)**<br>`real_permissioned_commerce` | Phụ thuộc khảo sát đối tác shop/HTX & live demo | Xuất lịch sử chat hợp pháp theo ToS từ chủ shop hoặc phiên live thử nghiệm có thông báo | Chấp thuận văn bản + kiểm tra ToS nền tảng & cơ sở pháp lý BVDLCN + khử PII cục bộ | Thấp | **Rất cao** *(ngôn ngữ mua hàng thật)* | **Cao nhất** *(đúng ngành thực phẩm/OCOP)* | Chứa PII thật; hay khuyết `active_sku` từng giây hoặc danh mục đầy đủ | **Ưu tiên khảo sát & thu thập trước tiên.** Nếu đủ lớn & đa dạng nhiều shop/phiên: cấp cho cả `train / dev / test_real` (tách độc lập theo shop/phiên); nếu khan hiếm (`~100–300` mẫu): khóa 100% làm `test_real` holdout. |
| **Source B (`Bổ sung / Dự phòng`)**<br>`human_simulated_live` | **Cao** *(chủ động tổ chức nội bộ)* | Diễn tập live 20–25 phút với thẻ tình huống mở trên điện thoại (không ép quota câu/người) | Phiếu đồng ý tham gia nghiên cứu + ẩn danh `participant_id` | Rất thấp | **Khá – Cao** *(khi đa dạng người tham gia, sản phẩm & cấm chép mẫu)* | **Cao** *(bao phủ cả 5 SKU fixture liên thông P05 lẫn các danh mục sản phẩm mới cho `Unseen Product Holdout`, đủ 100% `active_sku` & `viewer_thread`)* | Lệch phong cách nhóm sinh viên nếu ít người tham gia; trùng `participant_id` xuyên buổi | **Nguồn mở khóa song song & bù đắp ngữ cảnh đầy đủ** cho `train / dev / test_human_simulated` (gồm cả lát cắt `seen_product` và `unseen_product`). |
| **Source C (`Giới hạn chặt`)**<br>`synthetic_targeted` | Tức thì | Luật biến đổi / LLM sinh theo ca biên + **100% người thật duyệt** | Không chứa PII thật; tuân thủ điều khoản model | Rất thấp | Thấp – Trung bình *(dễ lặp khuôn cú pháp)* | Trung bình *(đúng ca biên kỹ thuật)* | Độ chính xác ảo nếu trộn vào tập đánh giá chung | **Chỉ dùng cho lớp hiếm/an toàn/stress-test** và nhánh đối chứng `synthetic_augmented` vs `real_and_human` / `human_only`. |

### 2.3 Lộ trình Nguồn Dữ liệu Thích ứng & Tách biệt 4 Giai đoạn Dữ liệu (`PROPOSED`)

Thay vì khóa cứng tỷ lệ phần trăm giữa các nguồn khi chưa khảo sát thực địa, nhóm vận hành theo **4 giai đoạn dữ liệu tách bạch nghiêm ngặt**:

1. **Giai đoạn 1 — `Data Acquisition Pilot` (`50–100` bình luận thực tế/có phép):**
   - Khảo sát tiếp cận nguồn `Source A` (hoặc phiên live giới thiệu có khách mời thật) để kiểm tra quy trình xin phép, định dạng xuất dữ liệu, tỷ lệ khuyết `active_sku` / `pinned_catalog`, đặc điểm ngôn ngữ thật và độ khớp sơ bộ với 9 lớp Intent (xem chi tiết tại **Mục 11 — Quick Start**).
2. **Giai đoạn 2 — `Annotation Pilot` (`50–100` bình luận gán nhãn mù 2 người):**
   - Dùng gói dữ liệu Pilot để đo độ đồng thuận `κ`, phát hiện câu mơ hồ biên và tinh chỉnh Guideline trước khi khóa Taxonomy `v0.1`.
   - **Quy tắc chống nhiễm bẩn `Held-out Test`:** Toàn bộ các bình luận trong Pilot đã được nhóm mở ra phân tích lỗi, sửa định nghĩa nhãn hoặc viết luật từ điển **bắt buộc gắn cờ `inspected_in_pilot = true` và CẤM đưa vào bất kỳ tập `held-out test` nào** (chỉ được lưu riêng làm `pilot_calibration_set` hoặc đưa vào `train` nếu nhãn tương thích hoàn toàn sau khi khóa Guideline).
3. **Giai đoạn 3 — `Main Development Dataset` (`train` + `dev`):**
   - Tỷ trọng thực tế giữa `Source A` và `Source B` được quyết định ngay sau báo cáo Pilot:
     - *Kịch bản A1 (`Source A` dồi dào, `>= 4` phiên / `>= 2` shop độc lập):* Chia các phiên/shop độc lập của `Source A` vào cả `train`, `dev` và giữ riêng tối thiểu 1 shop / 1–2 phiên hoàn toàn độc lập làm `test_real`; bổ sung `Source B` cho các kịch bản đa SKU/ngữ cảnh nối tiếp nếu `Source A` khuyết `active_sku`.
     - *Kịch bản A2 (`Source A` khan hiếm, chỉ thu được `100–300` bình luận sạch):* Giữ nguyên 100% các phiên `Source A` độc lập (ngoài gói Pilot đã soi) làm `test_real`, và dùng `Source B` làm tập phát triển chính `train / dev / test_human_simulated`.
     - *Kịch bản A3 (Chưa tiếp cận được `Source A` đúng hạn):* Dùng `Source B` để triển khai thực nghiệm kỹ thuật trên `test_human_simulated`, báo cáo trung thực `OPEN-1: Real commerce holdout pending` và không tuyên bố `VALIDATED` cho môi trường thương mại thật.
   - Mọi thử nghiệm có bổ sung `Source C` vào tập huấn luyện bắt buộc báo cáo song song **2 dòng kết quả**: `train_human_or_real_only` đối chiếu với `train_synthetic_augmented`.
4. **Giai đoạn 4 — `Held-out Evaluation Dataset` (`test_real`, `test_human_simulated`, `test_adversarial`):**
   - Đóng băng hoàn toàn độc lập về phiên/shop (`Source A`), người tham gia (`participant_id` ở `Source B`) và cụm câu (`split_group_id`); chỉ mở ra chấm điểm sau khi đã khóa mô hình và ngưỡng trên `train/dev`.

---

## 3. Legal, Permission, Privacy & Data Governance Checklist

> [!WARNING]
> **Nguyên tắc trung thực pháp lý & bảo vệ dữ liệu cá nhân:**
> - **Sự đồng ý của chủ shop KHÔNG tự động tạo ra toàn quyền pháp lý tuyệt đối đối với dữ liệu cá nhân của người xem:** Khi làm việc với `Source A`, ngoài văn bản đồng ý của chủ kênh/merchant, nhóm bắt buộc phải kiểm tra: (1) chủ kênh trích xuất dữ liệu bằng tính năng hợp lệ không vi phạm Điều khoản Dịch vụ (`ToS`) của nền tảng livestream, (2) cơ sở pháp lý và giới hạn mục đích nghiên cứu nội bộ theo Luật Bảo vệ Dữ liệu Cá nhân Việt Nam (`91/2025/QH15`), và (3) phạm vi được phép lưu trữ, chia sẻ nội bộ và thời hạn xóa.
> - **Pseudonymization (Giả danh hóa) ≠ Anonymization (Ẩn danh hóa hoàn toàn không thể đảo ngược):** Việc thay tên tài khoản bằng mã băm `HMAC-SHA256` hoặc mã `guest_s01_p04` chỉ là **giả danh hóa**, vì nội dung câu chat đặc thù, chi tiết đơn hàng hoặc chuỗi dấu thời gian vẫn có nguy cơ suy đoán ngược danh tính nếu đối chiếu với nguồn ngoài. Vì vậy, dữ liệu đã giả danh hóa vẫn phải được quản trị bảo mật chặt chẽ!

Trước khi bất kỳ tệp dữ liệu nào được đưa vào quy trình gán nhãn, phải kiểm tra đạt **100% các mục quản trị sau**:

- [ ] **1. Cấm thu thập trái phép & Kiểm tra ToS nền tảng:** Không dùng bot cào tự động (web scraping/crawling), không gọi API nội bộ trái phép, không ghi hình/thu thập lén phòng live chưa được phép (`Risk R18`). Chỉ nhận dữ liệu từ kênh xuất hợp lệ của chủ sở hữu hoặc phiên do nhóm tự tổ chức có thông báo rõ ràng.
- [ ] **2. Xác minh phạm vi quyền sử dụng (`permission_ref` & `usage_scope`):** Mỗi `source_id` phải ghi rõ phạm vi được phép: chỉ dùng nội bộ cho nghiên cứu P07 của HOSTRA AI, có cho phép chia sẻ giữa các thành viên gán nhãn trong nhóm hay không, và tuyệt đối không phát tán công khai tập dữ liệu thô ra bên ngoài.
- [ ] **3. Khử PII trên máy cục bộ trước khi chia sẻ (`Local PII Redaction`):**
  - Quét tự động kết hợp **rà soát mắt 100% dòng** trên máy cục bộ của Data Steward để thay số điện thoại (`<PHONE>`), địa chỉ cụ thể (`<ADDRESS>`), email (`<EMAIL>`), tài khoản ngân hàng/mã đơn (`<ACCOUNT>`), họ tên cá nhân nhạy cảm (`<PERSON>`).
  - Giả danh hóa định danh người xem sang mã phiên (`guest_sXX_pYY`); khóa muối (`HMAC salt`) hoặc bảng ánh xạ `participant_id` phải tách rời hoàn toàn khỏi thư mục dự án.
- [ ] **4. Phân quyền truy cập, Không đẩy lên Cloud bên thứ ba chưa được phép:**
  - Tệp gốc chưa khử PII chỉ do Data Steward giữ trong thư mục bảo mật cục bộ.
  - **Cấm tải dữ liệu thô hoặc dữ liệu đối tác chưa cho phép xử lý ngoài lên các nền tảng gán nhãn đám mây công cộng hay khung chat web của LLM bên thứ ba.** Quá trình gán nhãn ưu tiên dùng bảng tính cục bộ (`.xlsx`/`.tsv`) hoặc Label Studio chạy `localhost`.
- [ ] **5. Thời hạn lưu trữ & Xử lý yêu cầu xóa lan truyền (`Retention & Cascading Deletion`):**
  - Ghi rõ `retention_until` cho từng nguồn trong `source_registry`. Nếu đối tác `Source A` hoặc tình nguyện viên `Source B` rút lại sự đồng ý, Data Steward phải xóa bản ghi gốc **đồng thời lọc bỏ toàn bộ `comment_id` dẫn xuất tương ứng** khỏi `annotations/`, `processed/` splits và cập nhật lại `dataset_manifest.json`.
- [ ] **6. Hàng rào an toàn kho Git (`Zero Raw/Unpermitted Data in Git`):**
  - Cấm tuyệt đối commit tệp chưa khử PII (`*unscrubbed*`), hồ sơ chấp thuận chứa tên thật (`permission_records/`) hoặc dữ liệu `Source A` chỉ cấp quyền lưu máy cục bộ lên GitHub. Git chỉ lưu mã nguồn, schema, tài liệu và tệp manifest chứa mã băm `SHA-256` / thống kê tổng hợp.

---

## 4. Collection SOP (Quy trình Thu thập 10 Bước Thực tế)

| Bước | Tên bước | Thao tác thực tế cần làm | Công cụ gợi ý | Đầu ra (File / Trạng thái) | Tiêu chí hoàn thành (Exit Criteria) |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Source Discovery** | Khảo sát đa dạng nguồn `Source A` qua nhiều merchant, mặt hàng và phiên live khác nhau (không giới hạn ở 5 SKU P05); song song chuẩn bị danh mục phiên cho `Source B` (gồm cả fixture 5 SKU P05 lẫn các danh mục sản phẩm độc lập cho `Unseen Product Holdout`). | Bảng theo dõi nội bộ (Markdown / Sheet) | Sổ đăng ký nguồn `source_registry` (ngoài Git nếu chứa tên đối tác riêng tư) | Xác định danh sách nguồn `Source A` đa dạng mặt hàng và phương án dự phòng `Source B`. |
| **2** | **Permission & Terms Verification** | Ký/xác nhận phiếu đồng ý với chủ shop (`Source A`) hoặc phiếu đồng ý tham gia nghiên cứu với tình nguyện viên (`Source B`); kiểm tra phạm vi được phép lưu trữ. | Google Forms / PDF ký xác nhận | Mã tham chiếu `permission_ref` + `permission_status = "GRANTED"` | `0` nguồn nào chuyển sang Bước 3 nếu `permission_status != "GRANTED"`. |
| **3** | **Collection** | - `Source B`: Chạy phiên diễn tập 20–25 phút, Host ghi mốc đổi SKU, người xem gõ bình luận trực tiếp trên điện thoại/máy tính.<br>- `Source A`: Nhận file xuất hợp lệ từ chủ shop.<br>- `Source C`: Tạo lô nhỏ ca biên theo kịch bản thiếu hụt. | Phòng chat có log thời gian / CSV export | Tệp thô ban đầu (lưu cục bộ vùng kín ngoài Git) | Ghi nhận nguyên vẹn văn bản gốc và dấu thời gian gốc (nếu nguồn có). |
| **4** | **Secure Storage** | Đặt tệp thô chưa khử PII vào thư mục cục bộ được bảo vệ quyền truy cập (không đặt trong nhánh Git sẽ push). Ghi mã băm gốc của tệp nhận về. | Ổ đĩa cục bộ mã hóa / Kho lưu trữ nội bộ có phân quyền | Bản sao lưu gốc chỉ dành cho Data Steward | Kiểm tra `git status` xác nhận tệp thô chưa khử PII không bị theo dõi bởi Git. |
| **5** | **PII Handling & Pseudonymization** | Chạy script regex dò SĐT/email/địa chỉ + **1 người rà soát mắt 100% dòng** để thay bằng `<PHONE>`, `<ADDRESS>`; ánh xạ định danh người xem sang `guest_session_id` ẩn danh (`guest_sXX_pYY`). | Script Python stdlib (`re`, `hmac`) + rà soát thủ công | `data/raw/<source_id>_scrubbed.jsonl` | 100% bản ghi có `pii_scrub_status = "SCRUBBED_VERIFIED"`, `0` SĐT/địa chỉ thật sót lại. |
| **6** | **Initial Quality Screening** | Loại bỏ các dòng lỗi hệ thống không phải bình luận người dùng (ví dụ dòng log `"User joined room"`, dòng hoàn toàn trống `""` do lỗi xuất CSV); giữ nguyên emoji/slang thật của người xem! | Script kiểm tra định dạng dòng | Báo cáo lọc thô ban đầu | Không xóa nhầm bình luận ngắn hoặc spam thật của người xem (vì P07 cần học lọc spam!). |
| **7** | **Event Deduplication vs. User Repeats** | **Cấm xóa bình luận dựa trên cửa sổ thời gian ngắn (`< 2s`)!** Phân tách chính xác 3 trường hợp:<br>1. *Exact Event Duplicate:* Trùng khóa sự kiện nguồn có thẩm quyền (`external_dedup_key`) trong cùng `(source_id, session_id)` → gộp thành 1 bản ghi, cộng `duplicate_delivery_count` và lưu log provenance.<br>2. *Repeated User Comments:* Khác mã sự kiện nguồn nhưng cùng người xem/cùng câu chữ (kể cả cách nhau `< 1s`) → **bắt buộc giữ nguyên** từng bản ghi để Moderation học chặn `SPAM_FLOOD` và để test `E04`.<br>3. *Suspected Duplicate (thiếu Event ID):* Nguồn xuất thiếu mã sự kiện mà trùng hệt người gửi + câu chữ + giây → **không tự xóa**, giữ bản ghi và gắn `dedup_flag = "SUSPECTED_DUPLICATE"`. | Script kiểm tra khóa sự kiện nguồn | `data/raw/<source_id>_deduped.jsonl` | `0` bình luận lặp hành vi bị xóa nhầm; mọi dòng thiếu mã sự kiện lặp sát giờ được gắn cờ minh bạch. |
| **8** | **Provenance & Eligibility Tagging** | Gắn đầy đủ `data_origin`, `participant_id` (nếu `Source B`), `session_catalog_context`, `active_sku_at_comment_time` (`"UNKNOWN"` nếu nguồn `A` không rõ), nối `viewer_thread_id` (chỉ khi có `guest_session_id` thật) và tính các cờ `metadata_availability` + `evaluation_eligibility` theo từng tác vụ. | Script chuẩn hóa Offline Research Schema | Bản ghi đạt chuẩn Research Schema (Mục 5) | 100% bản ghi khai báo rõ tác vụ nào đủ điều kiện chấm điểm (`0` trường ngữ cảnh bịa đặt). |
| **9** | **Annotation Preparation** | Xuất các trường cần thiết cho người gán nhãn (ẩn hoàn toàn nhãn gợi ý của luật/LLM để tránh thiên kiến mỏ neo!), kèm bảng tra cứu nhanh 2–5 SKU của phiên và tối đa 2 bình luận liền trước của chính `guest_session_id` đó. | Xuất sang tệp bảng (`.tsv`/`.xlsx` khóa danh sách chọn) hoặc Label Studio local | `data/annotations/batches/batch_<id>_blind.tsv` | Hai người gán nhãn nhận hai tệp độc lập không nhìn thấy kết quả của nhau. |
| **10** | **Dataset Inventory & Versioning** | Cập nhật sổ kiểm kê tổng số mẫu theo từng nguồn, từng phiên, tính mã băm `SHA-256` cho các tệp trong `data/raw/` (bản đã khử PII) và chuẩn bị bàn giao sang Annotation SOP. | CLI tạo manifest JSON | `data/raw/raw_inventory_v0.1.json` | Khớp tổng số dòng, mã băm `SHA-256` và trạng thái `permission_status == "GRANTED"`. |

---

## 5. Offline Research Dataset Schema (Tách biệt với Production Runtime Contract)

> [!NOTE]
> Schema dưới đây là **Offline Research Dataset Schema** phục vụ lưu trữ dữ liệu thu thập, gán nhãn và lọc điều kiện đánh giá cho từng bài toán (`E01–E04`). Nó được tách biệt rõ với **Production Integration Contract** tại [p07-contract-v0.1.md](./p07-contract-v0.1.md) (§1.2) thông qua một lớp chuyển đổi mỏng (`Dataset-to-Fixture Adapter`). Nhờ thiết kế cờ `metadata_availability` và `evaluation_eligibility`, các bình luận livestream thực tế (`Source A`) bị khuyết `active_sku` hoặc danh mục sản phẩm **vẫn sử dụng hoàn toàn hợp lệ cho Moderation & Intent Classification (`E01`)**, đồng thời tự động được loại khỏi mẫu số chấm điểm SKU Grounding thay vì phải vứt bỏ cả tập dữ liệu thật hoặc đoán bừa nhãn SKU!

### Nhóm 5.1 — Metadata Thu thập Thực tế (`Collected Metadata`)
```json
{
  "comment_id": "p07-raw-s01-0042",
  "raw_text": "mat ong nay de tu lanh bi dong duong co phai hang pha ko shop",
  "source_id": "src-sim-20261127-s01",
  "data_origin": "human_simulated_live",
  "collection_method": "internal_rehearsal_chat_log",
  "collection_timestamp": "2026-11-27T13:14:22.410Z",
  "session_id": "sim-ses-01",
  "guest_session_id": "guest_s01_p07",
  "participant_id": "part_07",
  "external_dedup_key": "sim-msg-0042",
  "duplicate_delivery_count": 1,
  "dedup_flag": "NONE",
  "inspected_in_pilot": false
}
```
*(Nếu `Source A` không có mã sự kiện nguồn, timestamp hoặc không phân biệt được người gửi: đặt `external_dedup_key = null`, `collection_timestamp = null`, `guest_session_id = "UNKNOWN"`, `participant_id = null` — khi đó tuyệt đối không tự nối `viewer_thread_id` hay tạo cạnh liên thông trên giá trị `"UNKNOWN"`).*

### Nhóm 5.2 — Ngữ cảnh Phiên, Trạng thái Đủ Metadata & Điều kiện Đánh giá (`Provenance & Task Eligibility`)
```json
{
  "permission_status": "GRANTED",
  "permission_ref": "CONSENT-SIM-2026-S01",
  "pii_scrub_status": "SCRUBBED_VERIFIED",
  "merchant_or_channel_id": "merch_sim_01",
  "session_catalog_context": ["SKU-HONEY-01", "SKU-TEA-02", "SKU-CASHEW-03"],
  "session_product_families": ["honey", "herbal_tea", "cashew_nut"],
  "active_sku_at_comment_time": "SKU-HONEY-01",
  "viewer_thread_id": "thread-sim-s01-p07",
  "prior_viewer_comments_in_session": [
    {"comment_id": "p07-raw-s01-0035", "raw_text": "chai mật ong 500ml giá bn shop"}
  ],
  "metadata_availability": {
    "has_source_event_id": true,
    "has_timestamp": true,
    "has_viewer_id": true,
    "has_complete_session_catalog": true,
    "has_exact_active_sku": true
  },
  "evaluation_eligibility": {
    "moderation_evaluable": true,
    "intent_evaluable": true,
    "sku_grounding_evaluable": true,
    "grouping_evaluable": true,
    "temporal_replay_evaluable": true
  },
  "paraphrase_cluster_id": null,
  "template_family_id": null,
  "synthetic_provenance": null,
  "annotation_status": "READY_FOR_ANNOTATION"
}
```
*(Quy tắc suy dẫn `evaluation_eligibility`: Nếu một mẫu `Source A` chỉ có văn bản bình luận mà không rõ danh mục đầy đủ của buổi live (`has_complete_session_catalog = false`), thì `moderation_evaluable = true` và `intent_evaluable = true`, nhưng `sku_grounding_evaluable = false` — tuyệt đối không được gán `OUT_OF_CATALOG` trên danh mục không đầy đủ!)*

### Nhóm 5.3 — Nhãn Chuẩn do Người Gán nhãn Tạo (`Annotator Gold Labels` — sau phân xử)
```json
{
  "gold_labels": {
    "moderation_status": "ELIGIBLE",
    "secondary_moderation_flags": [],
    "primary_intent": "ASK_ORIGIN_OCOP",
    "secondary_intents": ["ASK_SPEC_USAGE"],
    "sku_grounding_eval_status": "EVALUABLE",
    "sku_resolution_mode": "EXPLICIT_SINGLE",
    "referenced_sku_ids": ["SKU-HONEY-01"],
    "phenomenon_tags": ["no_diacritics", "authenticity_doubt"],
    "annotator_a_id": "ann_01",
    "annotator_b_id": "ann_02",
    "adjudicated_by": "lead_01",
    "taxonomy_version": "v0.1.2"
  }
}
```

### Nhóm 5.4 — Đặc trưng Sinh Tự động ở Tiền xử lý & Chia tập (`Preprocessing / Split Derived Fields`)
```json
{
  "derived_split_meta": {
    "normalized_text": "mật ong này để tủ lạnh bị đóng đường có phải hàng pha không shop",
    "unaccent_fingerprint": "mat ong nay de tu lanh bi dong duong co phai hang pha ko shop",
    "is_short_generic_utterance": false,
    "near_dup_cluster_id": "ndup-0038",
    "split_group_id": "sgrp-0019",
    "product_holdout_stratum": "SEEN_PRODUCT_POOL",
    "assigned_split": "train"
  }
}
```

---

## 6. Sampling Strategy & Tính Khả thi Toán học của Các Đơn vị Độc lập (`PROPOSED`)

Tất cả các con số quy mô dưới đây mang trạng thái **`PROPOSED`** và phải được hiệu chỉnh lại dựa trên báo cáo thực tế của vòng **Data Acquisition Pilot** (Mục 11).

### 6.1 Phân biệt Rạch ròi 5 Đơn vị Đếm (Tránh Nhầm lẫn Toán học khi Chia Split)
Khi áp dụng thuật toán chống rò rỉ theo thành phần liên thông (`Union-Find`), cần phân biệt rõ 5 đại lượng hoàn toàn khác nhau:
1. **`Comment records` (Bản ghi bình luận):** Từng bình luận hợp lệ sau khử trùng sự kiện mạng (ví dụ mục tiêu tham chiếu `PROPOSED: 600–1.000` bản ghi).
2. **`Unique participants` (`participant_id`):** Số con người độc lập tham gia tạo dữ liệu xuyên các buổi diễn tập `Source B` cộng số tài khoản người xem độc lập ở `Source A`.
3. **`Viewer threads` (`viewer_thread_id` = `(session_id, guest_session_id)`):** Chuỗi bình luận của một người xem trong một phiên. *Lưu ý toán học quan trọng:* Nếu chỉ tổ chức 3–4 buổi diễn tập với 8–10 người/buổi và nối toàn bộ bình luận của cùng một người vào chung một thành phần liên thông, toàn bộ tập dữ liệu chỉ có tối đa `24–40` thành phần liên thông — **không bao giờ** tạo ra được hàng trăm nhóm độc lập!
4. **`Paraphrase / Template clusters` (`paraphrase_cluster_id`):** Cụm các câu sinh từ cùng một kịch bản gốc/mẫu câu (chủ yếu ở `Source C` hoặc câu dài gần trùng nhau).
5. **`Independent split groups` (`split_group_id`):** Các thành phần liên thông độc lập thực sự trên đồ thị rò rỉ dùng để chia vào `train`, `dev` và `test`.

### 6.2 Quy tắc Khả thi cho `8 / 16 / 32-shot` và Khung Chỉ tiêu Tham chiếu (`PROPOSED`)
1. **Hiểu đúng `k-shot` (`8 / 16 / 32` mẫu/lớp) trong `P07-E01`:**
   - `32-shot` nghĩa là lấy **32 bản ghi bình luận huấn luyện (`comment records`) cho mỗi lớp** từ tập `train` (tập `train` đã được cách ly hoàn toàn `0` chồng lấp `split_group_id` với `dev` và `test`), **không phải** đòi hỏi mỗi lớp phải có đủ 32 `split_group_id` riêng biệt trong `train`!
   - **Thuật toán lấy mẫu ưu tiên đa dạng nhóm (`Group-Diverse Round-Robin Sampling`):** Khi rút `k` mẫu của một lớp từ `train`, thuật toán đi vòng tròn lấy mỗi `split_group_id` tối đa 1 mẫu trước; chỉ khi số `split_group_id` chứa lớp đó trong `train` nhỏ hơn `k` mới lấy đến mẫu thứ 2 trong cùng nhóm, đồng thời bắt buộc ghi rõ chỉ số **`effective_unique_split_groups`** cạnh `k` trong `ExperimentManifest`.
   - **Xử lý trung thực khi thiếu mẫu lớp hiếm:** Nếu một lớp hiếm trong `train` có tổng số bản ghi `< k` (ví dụ `< 32`), **tuyệt đối không rút mẫu từ `dev`/`test` và không nhân bản (duplicate) câu cũ cho đủ 32**; ô thực nghiệm `(lớp, k)` đó phải được ghi nhận trung thực là **`INSUFFICIENT DATA`** (hoặc gắn cờ **`LIMITED GROUP DIVERSITY`** nếu số nhóm độc lập `< 5`).
2. **Cách đảm bảo đủ `split_group_id` để chia `train / dev / test` công bằng:**
   - Mỗi một trong 9 lớp `primary_intent` và 4 lớp `moderation_status` cần xuất hiện ở **ít nhất `>= 3` (khuyến nghị `PROPOSED: >= 12–20`) `split_group_id` độc lập trên toàn bộ tập dữ liệu** để cả 3 tập `train`, `dev`, `test` đều có mẫu đại diện độc lập.
   - Để đạt độ đa dạng nhóm này một cách tự nhiên: ưu tiên thu từ nhiều người xem độc lập trên `Source A` + khi tổ chức `Source B` thì mời nhiều tình nguyện viên khác nhau giữa các buổi (thay vì lặp lại cùng 6 người qua mọi buổi và ép họ gõ thật nhiều câu).
3. **Khung phân bổ tham chiếu (`PROPOSED` cho Tập Chính `600–1.000` bản ghi — hiệu chỉnh sau Pilot):**
   - **Natural Stream Sampling:** Giữ nguyên toàn bộ dòng bình luận tự nhiên theo thời gian từ các phiên `Source A` / `Source B` để phản ánh phân phối thật và kiểm định `calibration` / tải `W1–W2`.
   - **Targeted Scenario Sampling (bù lớp thưa):** Bổ sung thẻ vai diễn mở ở các buổi `Source B` tiếp theo cho các lớp tự nhiên ít gặp (`COMPARE_PRODUCTS`, `ASK_SAFETY_SUITABILITY`, `OUT_OF_CATALOG`) và lô nhỏ `Source C` có người duyệt cho `PROMPT_INJECTION` / `ABUSE_BLOCKED` (~`100–180` bản ghi cho 3 lớp bị chặn).
4. **Đa dạng Sản phẩm, Merchant, Phiên & Kiểm tra Tương quan Giả (`Spurious Product–Intent Correlation Audit`):**
   - **Ưu tiên độ rộng sản phẩm & phong cách diễn đạt:** Thu thập trải rộng nhiều dòng sản phẩm, nhiều quy cách bao bì (`chai`, `hũ`, `hộp thiếc`, `túi zip`, `gói`, `set quà`), nhiều merchant/người dẫn và nhiều phiên live khác nhau; dành riêng tối thiểu **`>= 2–3` dòng sản phẩm / phiên độc lập hoàn toàn** làm **`Unseen Product Holdout`** (không xuất hiện trong bất kỳ catalog nào của `train` hay `dev`).
   - **Chặn học vẹt đường tắt (`Shortcut Learning` giữa Tên sản phẩm và Nhãn Intent):** Trước khi đóng băng tập `train`, bắt buộc lập ma trận chéo `product_family (hoặc sku_id) × primary_intent` và đo chỉ số phụ thuộc thống kê (Cramér's $V$ và `Normalized Mutual Information`). Nếu phát hiện lệch cục bộ mạnh (ví dụ 80% câu nhắc `"mật ong"` trong `train` đều thuộc lớp `ASK_SAFETY_SUITABILITY` còn 80% câu nhắc `"hạt điều"` đều thuộc `ASK_PRICE_PROMO`), mô hình sẽ học vẹt tên sản phẩm thay vì cấu trúc câu hỏi! Khi đó phải bổ sung kịch bản câu hỏi cân bằng chéo các Intent trên từng nhóm sản phẩm trước khi huấn luyện.

---

## 7. Annotation SOP (Quy trình Gán nhãn Thực tế từ Pilot đến Gold Labels)

### 7.1 Công cụ & Phân công Nhân sự Đề xuất (Phù hợp nhóm 2–4 người)
- **Công cụ nhẹ, chạy ngay không tốn hạ tầng:** Sử dụng **Label Studio chạy local** hoặc **Bảng tính chuẩn hóa (`.xlsx` / Google Sheets nội bộ không chứa PII) có khóa Data Validation Dropdowns** cho từng cột enum để triệt tiêu 100% lỗi gõ sai tên nhãn.
- **Phân vai tối thiểu:**
  - `Annotator A` và `Annotator B`: 2 người gán nhãn độc lập (không thảo luận trong lúc gán cùng một lô).
  - `Adjudicator` (Người phân xử — có thể là bạn / Research Lead): Phân xử các dòng bất đồng và khóa nhãn chuẩn (`gold_labels`). *Nếu nhóm chỉ có 2 người, 2 người gán độc lập trước rồi cùng họp phân xử có ghi biên bản từng ca bất đồng.*

### 7.2 Quy trình 6 Bước Thực thi Gán nhãn
1. **Chuẩn bị gói Pilot (`50–100` bình luận đầu tiên — Mốc `D2`):** Chọn ngẫu nhiên có phân tầng `50–100` bình luận đã thu thập từ buổi diễn tập đầu tiên / nguồn thực tế. *(Lưu ý: `50–100` mẫu này dùng để kiểm định độ chặt của Guideline, không phải toàn bộ tập huấn luyện!).*
2. **Gán nhãn mù độc lập (`Blind Dual Annotation`):** `Annotator A` và `Annotator B` đọc duy nhất [p07-annotation-guideline-v0.1.md](./p07-annotation-guideline-v0.1.md) và điền vào hai tệp riêng biệt.
3. **Chấm độ đồng thuận IAA (Cohen's `κ`):** Chạy script đối chiếu hai tệp để tìm các cặp nhãn hay bị nhầm nhất.
4. **Phân xử & Khóa Taxonomy `v0.1` (`Adjudication & Freeze` — Mốc `D3`):** Họp rà soát 100% các dòng lệch nhau ở Pilot, bổ sung quy tắc biên vào Guideline và **đóng băng danh sách nhãn `v0.1`**.
5. **Gán nhãn Chính thức (`Main Batch Annotation` — Mốc `D4`):** Chia thành các lô `150–200` bình luận/lô để tránh mỏi mắt. Tối thiểu **20% số mẫu (hoặc toàn bộ 100% tập `held-out test` ứng viên!)** bắt buộc tiếp tục được gán nhãn kép độc lập bởi cả 2 người để duy trì chất lượng.
6. **Kiểm tra Tự động & Xuất `gold.jsonl`:** Chạy bộ kiểm tra ràng buộc cấu trúc, giải quyết hết các dòng gắn cờ `needs_discussion` và xuất ra `data/annotations/p07_gold_v0.1.jsonl`.

### 7.3 Thiết kế Bảng Cột Gán nhãn Cụ thể & Ví dụ Điền Mẫu

**Các cột ngữ cảnh chỉ-đọc (Cột `A` → `G`, khóa không cho sửa):**
`comment_id` | `session_id` | `pinned_skus_display` | `active_sku_at_time` | `guest_session_id` | `prior_2_comments_same_viewer` | `raw_text`

**Các cột do Annotator điền (Cột `H` → `N`):**
`moderation_status` | `primary_intent` | `secondary_intents_pipe` | `sku_resolution_mode` | `referenced_sku_ids_pipe` | `ambiguous_flag` | `annotator_note`

#### Ví dụ 4 dòng điền chuẩn trên bảng gán nhãn:
| `comment_id` | `active_sku_at_time` | `prior_2_comments_same_viewer` | `raw_text` | `moderation_status` | `primary_intent` | `secondary_intents_pipe` | `sku_resolution_mode` | `referenced_sku_ids_pipe` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `s01-012` | `SKU-HONEY-01` | *(trống)* | `trà shan tuyết hộp 100g giá bn, mấy hộp freeship shop` | `ELIGIBLE` | `ASK_PRICE_PROMO` | `ASK_SHIPPING_RETURN` | `EXPLICIT_SINGLE` | `SKU-TEA-02` |
| `s01-015` | `SKU-HONEY-01` | `[s01-012]: trà shan tuyết hộp 100g giá bn...` | `thế bà bầu uống buổi sáng đc ko shop` | `ELIGIBLE` | `ASK_SAFETY_SUITABILITY` | *(trống)* | `CONTEXTUAL_SINGLE` | `SKU-TEA-02` |
| `s01-019` | `SKU-HONEY-01` | *(trống — người xem mới)* | `hộp kia bao nhiêu tiền vậy ạ` *(phiên có hộp Trà & hộp Điều)* | `ELIGIBLE` | `ASK_PRICE_PROMO` | *(trống)* | `UNCLEAR` | *(trống)* |
| `s01-024` | `SKU-TEA-02` | *(trống)* | `😂😂😂🔥🔥🔥 111111` | `SPAM_FLOOD` | `null` | *(trống)* | `null` | *(trống)* |

*(Khi chuyển sang JSONL: ô trống ở `secondary_intents_pipe` và `referenced_sku_ids_pipe` được chuẩn hóa thành mảng rỗng `[]`, chuỗi `"null"` chuyển thành giá trị JSON `null`).*

---

## 8. Annotation Quality Control (Kiểm soát Chất lượng Gán nhãn)

1. **Đo Cohen's Kappa (`κ`) theo từng chiều phù hợp:**
   - `κ_moderation`: Tính trên toàn bộ các mẫu được gán kép (4 lớp).
   - `κ_primary_intent`: Tính trên tập con các mẫu mà **cả hai người cùng gán `moderation_status == "ELIGIBLE"`** (9 lớp).
   - `κ_sku_mode`: Tính trên tập con cùng `ELIGIBLE` (7 chế độ phân giải SKU).
   - Độ khớp tập hợp `Exact-Set Match %` (và Jaccard trung bình) cho `referenced_sku_ids` và `secondary_intents`.
   - **Ngưỡng kỳ vọng tham chiếu (`PROPOSED / THRESHOLD REQUIRES REVIEW`):** Mục tiêu hướng tới `κ_moderation >= 0.80`, `κ_sku_mode >= 0.75`, và `κ_primary_intent >= 0.70` trước khi chuyển từ Pilot `D2` sang gán nhãn đại trà `D4`. Nếu thấp hơn, **không ép chạy tiếp** mà phải làm rõ lại định nghĩa lớp gây nhiễu trong Guideline.
2. **Kiểm tra Nhất quán Logic Tự động (`Automated Structural Gate`):**
   - Quy tắc 1: `moderation_status != "ELIGIBLE"` $\iff$ `primary_intent is None and sku_resolution_mode is None and secondary_intents == [] and referenced_sku_ids == []`.
   - Quy tắc 2: `sku_resolution_mode in {"EXPLICIT_SINGLE", "CONTEXTUAL_SINGLE", "IMPLICIT_ACTIVE"}` $\implies$ `len(referenced_sku_ids) == 1` và mã SKU phải nằm trong `session_catalog_context`.
   - Quy tắc 3: `sku_resolution_mode == "MULTI_SKU"` $\implies$ `len(referenced_sku_ids) >= 2`, các mã SKU phân biệt, đã sắp xếp tăng dần và đều thuộc `session_catalog_context`.
   - Quy tắc 4: `sku_resolution_mode in {"UNCLEAR", "OUT_OF_CATALOG", "NOT_APPLICABLE"}` $\implies$ `referenced_sku_ids == []`.
   - Quy tắc 5: `primary_intent` không được xuất hiện lặp lại bên trong `secondary_intents`.

---

## 9. Dataset Split & Anti-Leakage Gate (Đồng bộ 5 Chốt chặn với `P07-DOC-04` §1.5)

Tuân thủ nghiêm ngặt thuật toán **Đồ thị Thành phần Liên thông Có Kiểm soát (`Guarded Connected Components / Union-Find`)** tại [p07-dataset-and-evaluation-protocol.md](./p07-dataset-and-evaluation-protocol.md) (§1.5):

1. **Cấm nối cạnh trên giá trị Rỗng / Khuyết (`Null/UNKNOWN Non-Linking`):** Tuyệt đối bỏ qua `null`, `""`, `"UNKNOWN"`, `"MISSING"`, `"NONE"` khi tạo cạnh. Hai bản ghi `Source A` cùng thiếu mã người xem (`"UNKNOWN"`) không bao giờ bị gom nhầm vào một nhóm.
2. **Chống suy biến Thành phần Liên thông Khổng lồ (`Giant Component Guard` cho câu ngắn phổ biến):**
   - Nối cạnh bắt buộc khi: cùng `viewer_thread_id` (hợp lệ), cùng `participant_id` (người tham gia diễn tập xuyên buổi ở `Source B`), cùng `paraphrase_cluster_id` / `template_family_id`, **hoặc** trùng lặp gần trên **câu cụ thể/dài** (`>= 5` từ hoặc có chứa tên/bí danh SKU/thuộc tính đặc thù với cùng `unaccent_fingerprint` hoặc `char-3gram Jaccard >= 0.85`).
   - Với các **câu ngắn tự nhiên siêu phổ biến không chứa thực thể riêng** (`<= 4` từ và không nhắc tên SKU, ví dụ `"giá bn"`, `"ship ko"`, `"chốt 1"`, `"bao nhiêu vậy"`, `"chào shop"` do những người xem độc lập khác nhau gõ tự nhiên): gắn cờ `is_short_generic_utterance = true` và **không nối bắc cầu xuyên người xem/phiên**, tránh làm sập toàn bộ đồ thị thành 1 cụm duy nhất; bù lại, báo cáo kiểm toán bắt buộc thống kê tỷ lệ trùng bề mặt câu ngắn giữa `test` và `train` kèm điểm `Unseen-Surface Macro-F1`.
3. **Chẩn đoán Khả thi Đồ thị Trước khi Chia Tập (`Pre-Split Feasibility Diagnostics`):** Xuất thống kê tổng số `split_group_id`, kích thước cụm lớn nhất (`cảnh báo nếu > 5% tổng số mẫu`), phân phối số cụm trên từng lớp Intent và khả năng đáp ứng `{8, 16, 32}` mẫu/lớp trước khi chốt tỷ lệ chia.
4. **Phân bổ Tập dữ liệu Thích ứng, Thiết lập `Unseen Product Holdout` & Bất biến Ưu tiên Chống Rò rỉ:**
   - Gói Pilot đã mở ra tinh chỉnh Guideline/luật (`inspected_in_pilot = true`) không bao giờ được đưa vào `test_*`.
   - Tập kiểm thử được tách tường minh thành **`test_seen_product`** (các phiên độc lập bán những dòng sản phẩm đã có mặt trong `train`) và **`test_unseen_product`** (các phiên/merchant độc lập bán các dòng sản phẩm hoàn toàn mới chưa từng xuất hiện trong `train ∪ dev`), báo cáo riêng theo từng nguồn (`real` vs `human_simulated`).
   - **Quy tắc bất khả xâm phạm khi tạo `Unseen Product Holdout`:** Việc tách `test_unseen_product` bắt buộc thực hiện ở **cấp độ nguyên phiên / nguyên merchant kết hợp nguyên thành phần liên thông `split_group_id`**, bảo toàn **100% ràng buộc chống rò rỉ** theo `viewer_thread_id`, `participant_id`, `paraphrase_cluster_id`, `template_family_id` và `source_id`. **Tuyệt đối không được xé lẻ một `split_group_id`, một chuỗi hội thoại viewer hay một người tham gia diễn tập (`participant_id`) giữa `train/dev` và `test_unseen_product` chỉ để gom đủ mẫu sản phẩm mới!** Nếu một thành phần liên thông có bất kỳ cạnh nối nào dính tới `train ∪ dev`, toàn bộ thành phần đó bị loại khỏi `test_unseen_product`.
5. **Kiểm soát Gia phả Xuyên Thí nghiệm (`E01` → `E04`):** Các tập `E02` (adversarial), `E03` (`test_pairs`) và `E04` tuyệt đối không được lấy mẫu đánh giá độ chính xác từ các `split_group_id` đã nằm trong `E01 train ∪ dev` hay `E03 dev_pairs`.

---

## 10. Data Versioning, Manifests & Evidence

Cấu trúc lưu trữ chuẩn hóa bên trong `experiments/sales-intelligence/comment-understanding/data/`:

```text
data/
├── raw/
│   ├── p05_reference_fixture_5sku.json     # Bộ 5 SKU P05 (chỉ dùng làm integration fixture tham chiếu)
│   ├── session_catalogs_v0.1.json          # Danh mục SKU động theo từng phiên/merchant (seen & unseen)
│   ├── sim_s01_scrubbed_deduped.jsonl      # Đã khử PII + exact dedup (chỉ khi được phép lưu repo)
│   └── raw_inventory_v0.1.json             # Số lượng mẫu, nguồn, dòng sản phẩm, permission_ref, SHA-256
├── annotations/
│   ├── pilot_iaa_report_v0.1.json          # Kết quả Cohen's Kappa & biên bản phân xử Pilot
│   └── p07_gold_v0.1.jsonl                 # Toàn bộ mẫu kèm nhãn chuẩn sau phân xử
└── processed/
    ├── train_v0.1.jsonl
    ├── dev_v0.1.jsonl
    ├── test_seen_product_v0.1.jsonl        # Holdout các sản phẩm đã xuất hiện trong train (tách theo nguồn)
    ├── test_unseen_product_v0.1.jsonl      # Holdout các sản phẩm mới 0% xuất hiện ở train/dev (0-leakage)
    ├── e02_adversarial_v0.1.jsonl
    ├── e03_grouping_pairs_v0.1.jsonl
    ├── e04_burst_traces_v0.1.jsonl
    └── dataset_manifest_v0.1.json          # SHA-256, thống kê lớp, tương quan giả Product×Intent, 0-leakage
```

*(Lưu ý bảo mật: Nếu một nguồn `Source A` chỉ cho phép dùng nội bộ trên máy cá nhân mà không cho đẩy văn bản bình luận lên kho Git chung, tệp `.jsonl` của nguồn đó được đặt vào danh sách loại trừ `.gitignore`, và Git chỉ lưu `dataset_manifest_v0.1.json` chứa mã băm `SHA-256`, phân phối nhãn và hướng dẫn nạp từ kho bảo mật của nhóm).*

---

## 11. Quick Start — Data Acquisition Pilot (`50–100` Bình luận Đầu tiên)

> [!IMPORTANT]
> **Mục đích đúng của Data Acquisition Pilot (`Design → Collect → Inspect → Refine → Experiment`):**
> Gói Pilot thu thập thử **`50–100` bình luận thực tế/được cấp phép** nhằm kiểm chứng khả năng tiếp cận nguồn thật, đo tỷ lệ có sẵn của metadata (`active_sku`, `viewer_id`, `catalog`), quan sát đặc tính tiếng Việt livestream thực địa, kiểm tra độ khớp với 9 lớp Intent + quy tắc biên của Guideline, và hiệu chỉnh lại quy mô tập dữ liệu chính. **Gói Pilot này KHÔNG phải là toàn bộ tập huấn luyện, KHÔNG được dùng lại làm `held-out test` độc lập, và KHÔNG dùng để kết luận hiệu năng mô hình.**

### 11.1 Quy trình Tác nghiệp 12 Mục cho Thành viên Phụ trách Dữ liệu
1. **Nhóm nguồn ứng viên khảo sát ngay (Ưu tiên đa dạng sản phẩm & merchant — không bó hẹp trong 5 SKU P05):**
   - *(1a)* Các chủ shop nhỏ / hợp tác xã OCOP / cựu sinh viên bán đa dạng ngành hàng thực phẩm đóng gói, nông sản chế biến, đồ uống, gia vị, bánh mứt, ngũ cốc, thảo mộc... có lưu lịch sử bình luận buổi live trên phần mềm quản lý bán hàng hợp pháp của chính họ.
   - *(1b)* Một buổi giới thiệu sản phẩm mẫu qua livestream phòng kín (`invite-only`, 15–20 phút) do nhóm HOSTRA tự đứng ra tổ chức với người xem thật ngoài nhóm code (có thông báo thu thập nghiên cứu ngay đầu phòng).
   - *(1c — chỉ dùng bổ sung song song nếu nguồn `1a/1b` chờ phản hồi > 3–5 ngày)* Một phiên diễn tập ngắn `Source B` với tình nguyện viên gõ điện thoại theo thẻ vai diễn mở.
2. **Kiểm tra Quyền & Điều khoản trước khi nhận dữ liệu:** Xác nhận bằng văn bản/form với chủ nguồn về mục đích nghiên cứu nội bộ HOSTRA AI, đảm bảo chủ nguồn trích xuất bằng tính năng hợp pháp không vi phạm ToS nền tảng, thống nhất không công khai dữ liệu thô và quyền yêu cầu xóa.
3. **Phương thức thu thập Được phép vs. Bị cấm:**
   - *Được phép:* Nhận file xuất (`CSV`/`XLSX`/`JSON`) do chủ kênh tự xuất hợp lệ; ghi chép/xuất log từ phiên live đã có văn bản đồng ý của chủ sở hữu; xuất log từ phòng live thử nghiệm của chính HOSTRA.
   - *Bị cấm tuyệt đối:* Viết crawler/scraper cào bình luận tự động, can thiệp API trái phép, hoặc thu âm/ghi chép bình luận từ kênh của bên thứ ba chưa đồng ý.
4. **Metadata cần ghi nhận ở mức Nguồn và mức Bình luận:**
   - *Mức nguồn (`Source Registry`):* Loại mặt hàng, số SKU bán trong phiên, danh sách tên/giá/quy cách SKU (nếu biết), cách xuất file, có dấu thời gian hay không, có mã người bình luận hay không, trạng thái quyền sử dụng.
   - *Mức bình luận:* Mã dòng gốc/mã sự kiện (nếu có), dấu thời gian (nếu có), mã người xem đã giả danh hóa, `raw_text`, sản phẩm đang giới thiệu lúc đó (nếu xác định được).
5. **Cách xử lý trung thực khi Khuyết Metadata:** Nếu nguồn shop thực tế không nhớ/không có mốc giờ đổi món hoặc thiếu danh mục đầy đủ, ghi thẳng `"UNKNOWN"` hoặc `"MISSING"` và đánh dấu `sku_grounding_evaluable = false` (vẫn giữ bình luận để kiểm tra Moderation và Intent; **tuyệt đối không tự đoán SKU đang live hay gán bừa `OUT_OF_CATALOG`**).
6. **Khử PII & Giả danh hóa cục bộ ngay khi nhận file:** Lưu file gốc vào thư mục kín ngoài Git (`*unscrubbed*`); chạy quét + đọc rà mắt 100% dòng trên máy cục bộ để thay SĐT → `<PHONE>`, địa chỉ → `<ADDRESS>`, tên tài khoản → `guest_pilot_pXX` trước khi gửi cho người gán nhãn thứ hai.
7. **Quy mô mục tiêu của Pilot:** Đúng **`50–100` bình luận hợp lệ sau bước lọc dòng trống hệ thống** (ưu tiên lấy liền mạch theo thời gian từ 1–2 đoạn phiên live dài 10–15 phút để thấy rõ cả mạch hội thoại nối tiếp và câu lặp tự nhiên).
8. **Gán nhãn Thăm dò Độc lập (`Exploratory Dual Pass`):** Hai thành viên (`Annotator A` và `Annotator B`) đọc [p07-annotation-guideline-v0.1.md](./p07-annotation-guideline-v0.1.md) và điền độc lập vào 2 bản `Annotation Sheet` mà không trao đổi trước.
9. **Các chỉ số thực tế bắt buộc kiểm tra sau Pilot:**
   - Tỷ lệ `%` bình luận có đủ timestamp, có đủ `viewer_id`, có xác định được `active_sku` và danh mục phiên;
   - Tỷ lệ bình luận chứa PII thật đã phải che (`%`);
   - Phân phối tự nhiên của 4 nhãn Moderation & 9 lớp Intent (lớp nào chiếm áp đảo, lớp nào bằng `0`);
   - Tỷ lệ bình luận không khớp tốt vào 9 lớp hiện tại hoặc gây tranh cãi biên (`%` dòng `ambiguous_flag = true`);
   - Tỷ lệ câu siêu ngắn trùng mặt chữ (`"giá bn"`, `"chốt"`, `"."`) và tỷ lệ câu ghép đa ý (`secondary_intents != []`);
   - Hệ số đồng thuận sơ bộ Cohen's `κ` trên 3 chiều (`moderation`, `primary_intent`, `sku_mode`).
10. **Tiêu chí Thành công của Pilot (`Pilot Success Criteria`):** Có bằng chứng quyền sử dụng hợp lệ (`GRANTED`), `0` PII lọt sang file gán nhãn, thu đủ `50–100` bình luận thật/có phép, lập xong bảng chẩn đoán chất lượng dữ liệu và liệt kê rõ mọi điểm vênh của Guideline.
11. **Tiêu chí Dừng / Chuyển hướng (`Stop / Pivot Criteria`):**
    - Nếu một nguồn đối tác không rõ ràng về quyền xuất dữ liệu hoặc vi phạm ToS → **dừng ngay không nhận nguồn đó**, chuyển sang tổ chức phiên live kín `invite-only` của HOSTRA hoặc `Source B` trong lúc tìm đối tác khác.
    - Nếu `κ_primary_intent < 0.65` hoặc `> 15%` bình luận thực tế bị dồn vào `UNCLEAR_OR_OTHER` vì thiếu nhãn nghiệp vụ → **dừng chưa thu thập/gán nhãn đại trà**, họp chỉnh sửa Guideline/Taxonomy trước.
12. **Bộ 4 Sản phẩm Bàn giao của Pilot (`Pilot Deliverables`):**
    - (1) Bảng `Source Registry` cập nhật trạng thái các nguồn đã khảo sát;
    - (2) Tệp `pilot_raw_scrubbed` (`50–100` dòng đã khử sạch PII, lưu đúng phạm vi quyền);
    - (3) Hai bảng `Annotation Sheet` độc lập của `Annotator A` & `Annotator B`;
    - (4) Báo cáo 1 trang `Pilot Data Quality & Feasibility Report` để chốt quy mô tập chính.

### 11.2 Bốn Khuôn mẫu Bảng Tác nghiệp (`Templates` cho Pilot)

#### Template 1 — `Source Registry` (Sổ Đăng ký & Thẩm định Nguồn Dữ liệu)
| `source_id` | `source_type` (`A_REAL` / `B_SIM`) | `product_category` | `sku_count` | `export_method` | `tos_and_legal_check` | `permission_status` | `permission_ref` | `has_timestamps` | `has_viewer_ids` | `has_active_sku_log` | `git_storage_allowed` | `retention_until` | `notes` |
| :--- | :---: | :--- | :-: | :--- | :---: | :---: | :--- | :-: | :-: | :-: | :-: | :--- | :--- |
| `src-pilot-01` | `A_REAL` | Mật ong & Trà thảo mộc | `3` | Chủ shop xuất CSV từ phần mềm quản lý live | `VERIFIED` | `GRANTED` | `CONSENT-2026-P01` | `YES` | `YES` | `PARTIAL` | `NO (Local only)` | `2027-06-30` | Chỉ lưu manifest SHA-256 trên Git |

#### Template 2 — `Raw Comment Collection Sheet` (Bảng Thu thập & Tiền xử lý Đã Khử PII)
| `comment_id` | `source_id` | `session_id` | `source_event_id` | `collection_timestamp` | `guest_session_id` | `raw_text_scrubbed` | `pii_scrub_status` | `dedup_flag` | `session_catalog_context` | `active_sku_at_time` | `sku_grounding_evaluable` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :--- | :--- | :---: |
| `plt-001` | `src-pilot-01` | `ses-real-01` | `evt-99201` | `2026-11-26T20:05:12Z` | `guest_p01_04` | `mật ong hoa cà phê 500ml giá bn shop, ship về <ADDRESS> mấy ngày` | `SCRUBBED_VERIFIED` | `NONE` | `SKU-HONEY-01\|SKU-TEA-02` | `SKU-HONEY-01` | `TRUE` |

#### Template 3 — `Pilot Data Quality Report` (Khung Báo cáo Chẩn đoán Sau Pilot)
| Nhóm chỉ số chẩn đoán | Giá trị đo trên Pilot (`N = ...`) | Nhận xét thực tế & Tác động lên Kế hoạch Tập Chính |
| :--- | :--- | :--- |
| **1. Tổng số dòng thô / Số dòng hợp lệ sau Exact Dedup / Số dòng `SUSPECTED_DUPLICATE`** | `... / ... / ...` | Đánh giá tỷ lệ nhiễu xuất file và tốc độ bình luận thực tế mỗi phút |
| **2. Tỷ lệ dòng chứa PII thật đã phải khử (`<PHONE>`, `<ADDRESS>`...)** | `... %` | Kiểm chứng độ đủ của regex khử PII tiếng Việt |
| **3. Độ đầy đủ Metadata (`has_timestamp` / `has_viewer_id` / `sku_grounding_evaluable`)** | `... % / ... % / ... %` | Quyết định tỷ trọng mẫu `Source A` dùng được cho `E02` (SKU) so với chỉ `E01` (Intent) |
| **4. Phân phối 4 lớp Moderation, 9 lớp Intent & Độ lệch `Product × Intent`** | Liệt kê số lượng & bảng chéo | Xác định lớp thưa và phát hiện sớm hiện tượng một sản phẩm bị gắn lệch vào một nhãn Intent duy nhất |
| **5. Tỷ lệ câu siêu ngắn trùng lặp (`<= 4` từ) & câu đa ý (`secondary_intents`)** | `... % / ... %` | Kiểm chứng nguy cơ Giant Component và tần suất câu ghép đa ý |
| **6. Độ đồng thuận Pilot IAA (`κ_moderation` / `κ_primary_intent` / `κ_sku_mode`)** | `... / ... / ...` | Liệt kê top 3 cặp nhãn bất đồng để chốt Guideline `v0.1` trước mốc `D4` |

#### Template 4 — `Annotation Sheet` (Bảng Gán nhãn Mù cho `Annotator A` / `Annotator B`)
| `comment_id` | `pinned_skus_display` | `active_sku_at_time` | `guest_session_id` | `prior_2_comments_same_viewer` | `raw_text_scrubbed` | `sku_grounding_eval_status` | `moderation_status` | `secondary_mod_flags` | `primary_intent` | `secondary_intents_pipe` | `sku_resolution_mode` | `referenced_sku_ids_pipe` | `ambiguous_flag` | `annotator_note` |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| `plt-001` | `SKU-HONEY-01 (Mật ong 500ml); SKU-TEA-02 (Trà 100g)` | `SKU-HONEY-01` | `guest_p01_04` | *(trống)* | `mật ong hoa cà phê 500ml giá bn shop, ship về <ADDRESS> mấy ngày` | `EVALUABLE` | `ELIGIBLE` | *(trống)* | `ASK_PRICE_PROMO` | `ASK_SHIPPING_RETURN` | `EXPLICIT_SINGLE` | `SKU-HONEY-01` | `FALSE` | Hỏi gộp giá + thời gian giao |

---

## 12. Execution Roadmap (`D0` → `D6` — Hiệu chỉnh theo Hướng Real-First & Pilot-First)

| Mốc | Công việc cụ thể | Phụ trách đề xuất | Phụ thuộc | Deliverables | Acceptance Criteria | Rủi ro & Phương án dự phòng |
| :-: | :--- | :--- | :---: | :--- | :--- | :--- |
| **`D0`**<br>*Source Discovery & Pilot Prep* | Khảo sát ngay 1–3 nguồn `Source A` (shop thực phẩm/OCOP hoặc phiên live thử nghiệm có khách mời), kiểm tra quyền/ToS, chuẩn bị thư mục cục bộ ngoài Git và 4 bảng mẫu Mục 11.2. | Phụ trách Dữ liệu + Research Lead | Duyệt bản `v0.1.2` | `Source Registry` điền thực tế + mẫu phiếu đồng ý + quy tắc `.gitignore` | Xác nhận ít nhất 1 nguồn đủ điều kiện `permission_status = "GRANTED"` để thu Pilot. | *Rủi ro:* Shop đối tác chưa kịp xuất log.<br>*Dự phòng:* Mở 1 phiên live giới thiệu mẫu có phép hoặc 1 buổi mini `Source B`. |
| **`D1`**<br>*Data Acquisition Pilot (50–100 comments)* | Thu thập thử `50–100` bình luận đầu tiên; chạy SOP khử PII cục bộ + phân loại 3 mức dedup + gắn cờ `metadata_availability` & `evaluation_eligibility`. | Phụ trách Dữ liệu | `D0` | `pilot_raw_scrubbed` (`50–100` bình luận sạch PII, gắn cờ `inspected_in_pilot = true`) | `100%` `SCRUBBED_VERIFIED`, `0` dòng bị đoán bừa ngữ cảnh SKU khi nguồn thiếu log. | *Rủi ro:* Nguồn `A` khuyết `active_sku`.<br>*Dự phòng:* Giữ cho `E01` và lên lịch `Source B` có log đổi món cho `E02`. |
| **`D2`**<br>*Annotation Pilot & Quality Inspection* | 2 người gán nhãn độc lập trên `50–100` mẫu Pilot; lập `Pilot Data Quality Report` (tỷ lệ khuyết metadata, phân phối lớp thật, `κ` trên 3 chiều). | Annotator A + Annotator B | `D1` | 2 `Annotation Sheet` độc lập + `Pilot Data Quality Report` | Đo xong `κ_moderation`, `κ_primary_intent`, `κ_sku_mode` và thống kê xong các câu biên. | *Rủi ro:* Xuất hiện kiểu hỏi thực tế khó phân ranh.<br>*Dự phòng:* Đưa vào phiên phân xử ở `D3`. |
| **`D3`**<br>*Guideline Freeze & Main Plan Calibration* | Họp phân xử bất đồng Pilot, cập nhật quy tắc biên vào Guideline, **khóa Taxonomy `v0.1`** và chốt con số quy mô/phối thức `Source A + B (+ C hạn chế)` dựa trên số liệu Pilot. | Research Lead + Annotators | `D2` | Guideline `v0.1` đã khóa + kế hoạch quy mô `D4` đã hiệu chỉnh thực chứng | Đạt đồng thuận quy tắc biên; gói Pilot được cách ly không đưa vào `held-out test`. | *Rủi ro:* Số cụm độc lập mỗi lớp thấp.<br>*Dự phòng:* Mở rộng người tham gia mới giữa các buổi `Source B` (không ép quota câu/người). |
| **`D4`**<br>*Main Dataset Acquisition & Annotation* | Thu thập tập chính theo phối thức đã chốt sau `D3`; bổ sung thẻ tình huống lớp thưa (`Source B`) và ca an toàn có kiểm soát (`Source C`); gán nhãn chính thức (gán kép `>= 20%` và `100%` ứng viên `held-out test`). | Cả nhóm | `D3` | `data/annotations/p07_gold_v0.1.jsonl` + tập chuyên biệt `E02/E03/E04` | Đạt đủ điều kiện đại diện lớp, `100%` pass Structural & Eligibility Validator. | *Rủi ro:* Mỏi mắt khi gán lô lớn.<br>*Dự phòng:* Chia lô `150–200` câu và kiểm tra chéo định kỳ. |
| **`D5`**<br>*Diagnostics & Guarded Anti-Leakage Split* | Chạy **Pre-Split Feasibility Diagnostics** (kiểm tra kích thước thành phần liên thông, chống Giant Component câu ngắn, liên kết `participant_id`), chia `train / dev / test_*` và kiểm toán hậu kiểm. | Research Lead | `D4` | Các tệp split trong `data/processed/` + báo cáo chẩn đoán đồ thị & overlap | Giao `split_group_id` / `participant_id` / `paraphrase_cluster_id` giữa các split bằng `∅`; không có cụm khổng lồ bất thường. | *Rủi ro:* Lớp hiếm không đủ `32` mẫu trong `train`.<br>*Dự phòng:* Ghi nhận trung thực `INSUFFICIENT DATA` / `LIMITED GROUP DIVERSITY`, tuyệt đối không lấy từ `dev/test`. |
| **`D6`**<br>*Dataset Freeze & Gate 4 Handover* | Xuất `dataset_manifest_v0.1.json` kèm `SHA-256`, tạo tập con `{8, 16, 32} × 3 seeds` theo thuật toán round-robin đa dạng nhóm từ `train`, khóa két `held-out test`. | Research Lead | `D5` | `dataset_manifest_v0.1.json` đã khóa | Đóng xong `Gate 3`, chuyển sang mở khóa `Gate 4` (`P07-E01`). | *Rủi ro:* Chỉnh sửa nhầm tệp sau khi chạy.<br>*Dự phòng:* Mọi lượt chạy kiểm tra khớp `SHA-256` đầu vào. |

---

## 13. Open Decisions Phân theo Thời điểm Chốt (Không Chặn Việc Khởi động Pilot!)

1. **Cần chốt TRƯỚC KHI thu `Data Acquisition Pilot` (`Gate 2`):**
   - Phân công rõ **ai là Data Steward** giữ tệp gốc chưa khử PII trên máy cục bộ và **2 thành viên nào** làm `Annotator A` / `Annotator B` cho `50–100` mẫu Pilot.
   - Xác nhận danh sách 1–3 nguồn ứng viên `Source A` sẽ liên hệ đầu tiên và mẫu văn bản xin phép / kiểm tra ToS.
2. **Chỉ chốt SAU KHI xem dữ liệu `Pilot` (`Gate 3` — Không đoán mò từ bây giờ):**
   - Tỷ trọng thực tế giữa `Source A` và `Source B` trong `train / dev / test`, số buổi diễn tập `Source B` cần bổ sung, và việc có cần tinh chỉnh định nghĩa 9 lớp Intent / quy tắc biên hay không.
3. **Chốt TRƯỚC KHI chạy `P07-E01` (`Gate 4`):**
   - Công cụ tách từ tiếng Việt giấy phép sạch cho `PhoBERT-base` (đề xuất `pyvi` MIT), model LLM đối chứng cho `B1`/`H1`, và các ngưỡng chấp nhận đang gắn nhãn `THRESHOLD REQUIRES REVIEW`.
