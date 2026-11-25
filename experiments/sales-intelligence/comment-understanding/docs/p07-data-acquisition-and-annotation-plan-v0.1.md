# P07 — Kế hoạch Thu thập & Gán nhãn Bộ dữ liệu Bình luận Tiếng Việt Thực tế

| Thuộc tính | Giá trị |
| :--- | :--- |
| **Mã tài liệu** | `P07-DOC-06` |
| **Phiên bản / Ngày** | `PROPOSED v0.1` — `25/11/2026` |
| **Trạng thái phê duyệt** | `IN REVIEW` *(Các chỉ tiêu quy mô, ngưỡng IAA và phân bổ nguồn dữ liệu đang ở trạng thái `PROPOSED` chờ Owner phê duyệt)* |
| **Mục tiêu vận hành** | Cung cấp quy trình thực địa từ tìm nguồn, xin quyền hợp pháp, tổ chức thu thập, khử PII, gán nhãn 2 lớp độc lập, đến đóng băng tập dữ liệu chống rò rỉ cho `P07-E01..E04` |
| **Tài liệu liên kết** | [p07-problem-and-requirements.md](./p07-problem-and-requirements.md) · [p07-contract-v0.1.md](./p07-contract-v0.1.md) · [p07-annotation-guideline-v0.1.md](./p07-annotation-guideline-v0.1.md) · [p07-dataset-and-evaluation-protocol.md](./p07-dataset-and-evaluation-protocol.md) · [p07-experiment-readiness.md](./p07-experiment-readiness.md) |

> [!IMPORTANT]
> **Nguyên tắc nền tảng:** Không dùng hàng trăm câu hỏi do LLM tự sinh làm bộ dữ liệu chính rồi coi điểm F1 trên đó là bằng chứng mô hình hoạt động ngoài thực tế. Dữ liệu sinh tự động từ một LLM thường đồng nhất về cấu trúc cú pháp, thiếu lỗi gõ bàn phím điện thoại tự nhiên của người Việt và tạo ra độ chính xác ảo (circular benchmark). Kế hoạch này ưu tiên **dữ liệu do con người thật tạo ra có quyền sử dụng hợp lệ (`real_permissioned_commerce` và `human_simulated_live`)**, chỉ dùng `synthetic` có kiểm soát cho các lát cắt ca khó/hiếm và báo cáo hoàn toàn tách biệt.

---

## 1. Dataset Objectives & Requirements

Bộ dữ liệu `v0.1` của P07 phải đáp ứng đồng thời yêu cầu thực nghiệm của 4 bài toán trong `Technical Research & PoC Plan v1.0` (§5 P07, §8.1, §9.2):

1. **Phục vụ `P07-E01` (So sánh Classifier `PhoBERT-base` vs `SetFit` vs `Rules + LLM`):**
   - Đủ độ đa dạng từ vựng tự nhiên trên **9 lớp `primary_intent`** và **4 trạng thái `moderation_status`** để huấn luyện ở các mức `8 / 16 / 32` mẫu/lớp và toàn bộ tập `train`, đồng thời giữ được tập `dev` và `held-out test` hoàn toàn độc lập về cụm diễn đạt và người xem.
2. **Phục vụ `P07-E02` (Độ bền ngôn ngữ khó & Phân giải SKU):**
   - Bắt được hành vi gõ tiếng Việt thực trên thiết bị di động: bỏ dấu hoàn toàn, mất dấu cục bộ do bộ gõ Telex/VNI, viết tắt thương mại điện tử (`bn`, `hsd`, `dc`, `ko`, `ship cod`, `freeship`), câu nối tiếp dùng đại từ theo mạch người xem (`viewer_thread_id`) và câu nhắc nhiều sản phẩm trong danh mục 2–5 SKU.
3. **Phục vụ `P07-E03` (Đánh giá Gom nhóm Ngữ nghĩa & Abstention):**
   - Có các cặp bình luận thực sự hỏi cùng một câu hỏi từ nhiều người xem khác nhau **và** các cặp bẫy dễ gộp nhầm (cùng `primary_intent` và cùng `SKU` nhưng hỏi hai thuộc tính khác nhau như *"hạn sử dụng"* vs *"nhiệt độ nước pha trà"*, hoặc khác SKU, hoặc 1 câu rõ SKU + 1 câu `UNCLEAR`).
4. **Phục vụ `P07-E04` (Mô phỏng Tải dồn dập & Khử trùng):**
   - Có chuỗi dấu thời gian thực tế để mô phỏng nhịp bình luận dồn dập khi host đọc giá/chốt đơn, kết hợp tiêm sự kiện trùng khóa mạng (`external_dedup_key`) và flood từ một tài khoản.

---

## 2. Data Source Strategy (Phân tích & Lựa chọn Nguồn Dữ liệu)

### 2.1 Phân tích 3 Nguồn Dữ liệu Khả thi

#### Source A — Permissioned Real Livestream Comments (`real_permissioned_commerce`)
Bình luận thực tế từ các buổi livestream bán thực phẩm đóng gói, nông sản chế biến, đặc sản OCOP, mật ong, trà, hạt dinh dưỡng, trái cây sấy hoặc cà phê rang xay.

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

- **Quy mô người tham gia đề xuất (`PROPOSED`):**
  - **1 người dẫn (Host)** trình bày trực tiếp 3–5 SKU thực phẩm đóng gói (kế thừa bộ 5 SKU chuẩn từ P05: Mật ong hoa cà phê, Trà Shan Tuyết, Hạt điều rang củi, Xoài sấy dẻo, Cà phê rang xay).
  - **6–12 người tham gia đóng vai người xem/buổi** (thành viên mở rộng, bạn cùng lớp/CLB chưa từng đọc bảng từ khóa/luật của mô hình P07), thực hiện **3–4 buổi diễn tập ngắn** (mỗi buổi `20–25` phút), ít nhất 60% người tham gia gõ trên **điện thoại di động** để tạo thói quen viết tắt và lỗi gõ tự nhiên.
- **Thiết kế kịch bản phiên & Đa ngữ cảnh SKU:**
  - Mỗi buổi ghim tổ hợp 3 hoặc 5 SKU khác nhau; người dẫn chuyển `Active SKU` mỗi `5` phút (ghi lại chính xác bảng mốc thời gian chuyển `Active SKU`, ví dụ `00:00–05:00 = SKU-HONEY-01`, `05:00–10:00 = SKU-TEA-02`...).
- **Cách tránh người tham gia chép lại câu hỏi mẫu (Anti-Template Bias):**
  - **Tuyệt đối không phát danh sách câu hỏi mẫu hay tên 9 nhãn Intent** cho người tham gia!
  - Phát cho mỗi người tham gia một **Thẻ Vai diễn & Tình huống Mua hàng (Persona Goal Card)** dạng mục tiêu mở, ví dụ:
    - *Thẻ P1 (Người mua kỹ tính về sức khỏe):* "Mẹ bạn bị mất ngủ và huyết áp hơi cao, bạn đang tìm mua quà biếu dưới 300k; hãy hỏi kỹ xem dùng món nào an toàn và cách dùng."
    - *Thẻ P2 (Người vào trễ, hỏi dồn nhiều lượt):* "Bạn vào phòng lúc phút thứ 7 khi host đang nói về Trà, nhưng bạn nhìn thấy hũ Mật ong ở kệ sau nên hỏi về Mật ong trước, sau đó hỏi tiếp 2 câu ngắn nối đuôi nhau mà không nhắc lại tên sản phẩm."
    - *Thẻ P3 (Người săn mã / lo vỡ hàng khi ship xa):* "Bạn ở tỉnh xa, hay hỏi gộp giá combo + phí ship + lỡ vỡ chai thủy tinh thì đổi thế nào bằng thói quen nhắn tin viết tắt hàng ngày của bạn."
    - *Thẻ P4 (Người xem gây nhiễu thực tế):* "Thỉnh thoảng thả cảm xúc, khen giọng người dẫn, hỏi một món shop không bán (như khô gà/bánh pía), hoặc hỏi trống không `'cái hộp kia bao nhiêu'`."
- **Cách ghi nhận Timestamps & Viewer Threads:**
  - Dùng phòng chat riêng có lưu lịch sử theo giây (ví dụ: giao diện Viewer Mock sẵn có của `apps/web/`, hoặc một biểu mẫu web nội bộ đơn giản / kênh chat riêng cho buổi diễn tập) gắn cho mỗi người một mã phiên ẩn danh cố định suốt buổi (`guest_sim_s01_p01` ... `guest_sim_s01_p12`). Nhờ đối chiếu dấu thời gian từng bình luận với nhật ký đổi món của Host, ta thu được **100% chính xác** `collection_timestamp`, `guest_session_id`, `viewer_thread_id` và `active_sku_at_comment_time`!
- **Sự đồng ý & Bảo vệ người tham gia:** Trước buổi diễn tập, người tham gia tích xác nhận đồng ý đóng góp câu chữ cho tập dữ liệu nghiên cứu HOSTRA AI, được dặn không gõ SĐT/địa chỉ cá nhân thật (nếu diễn cảnh chốt đơn thì gõ chuỗi giả quy ước `0900000000`), và bảng ánh xạ tên người tham gia sang `guest_sim_*` không được lưu vào Git.
- **Ranh giới minh bạch:** `human_simulated_live` là bình luận do con người thật tự nghĩ và tự gõ theo nhịp trực tiếp, vượt trội hơn hẳn LLM synthetic, **nhưng không được trình bày là dữ liệu thương mại thực tế (`real_permissioned_commerce`)**.

#### Source C — Controlled Synthetic Data (`synthetic_seed_template` / `synthetic_llm_human_reviewed`)
Chỉ dùng làm nguồn **bổ trợ có kiểm soát** cho các góc khuất dữ liệu khó thu đủ tự nhiên:
- **Phạm vi sử dụng hợp lệ:** (1) Các câu gài lệnh tấn công hệ thống (`PROMPT_INJECTION` — người xem bình thường hiếm khi gõ nhưng bắt buộc phải test an toàn `TC18`), (2) Các câu gài công dụng chữa bệnh tinh vi đối với thực phẩm đóng gói (`R17`), (3) Tổ hợp so sánh chéo nhiều SKU ít xuất hiện, (4) Các biến thể lỗi gõ cực đoan / mất dấu đồng âm dùng cho `P07-E02`, và (5) Sinh chuỗi lặp gói tin mạng / tải burst cho `P07-E04`.
- **Ràng buộc provenance & human review:** Mỗi mẫu synthetic bắt buộc gắn `template_family_id` (hoặc `prompt_recipe_id`), `paraphrase_cluster_id`, và `reviewed_by` (một thành viên con người duyệt sửa/loại bỏ câu thiếu tự nhiên). **Không bao giờ** dùng `synthetic` làm nguồn chính của tập dữ liệu hoặc trộn vào `test_real` / `test_human_simulated`.

### 2.2 Bảng Đối sánh Chiến lược 3 Nguồn Dữ liệu

| Source | Availability | Collection Method | Permission Requirements | Cost | Expected Diversity | Domain Relevance | Risks | Recommended Use |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Source A**<br>`real_permissioned_commerce` | Thấp – Trung bình *(phụ thuộc quan hệ đối tác shop/HTX)* | Chủ shop xuất lịch sử chat hợp pháp hoặc ghi chép có phép từ phiên live của đối tác | Văn bản đồng ý của chủ kênh + tuân thủ ToS + khử sạch PII người xem | Thấp (công liên hệ & làm sạch PII) | **Rất cao** *(ngôn ngữ người mua thật, nhịp hỏi tự nhiên)* | **Cao nhất** *(nếu đúng ngành thực phẩm/OCOP)* | Rủi ro lộ SĐT/địa chỉ khách hàng; thiếu metadata `active_sku` chính xác từng giây | **Ưu tiên số 1 làm `Held-out Real Test` (`test_real`)** để đóng `OPEN-1`; chỉ chia sang `train` nếu thu được `> 500` mẫu sạch |
| **Source B**<br>`human_simulated_live` | **Cao** *(nhóm chủ động tổ chức ngay được)* | 3–4 buổi diễn tập live 20–25 phút với 6–12 người dùng thẻ tình huống mở trên điện thoại | Phiếu đồng ý tham gia nội bộ + mã hóa ẩn danh người tham gia | Rất thấp (thời gian tổ chức nội bộ) | **Khá – Cao** *(nếu cấm chép câu mẫu và đa dạng người gõ)* | **Cao** *(khớp chính xác 5 SKU OCOP của HOSTRA & đủ `active_sku`, `viewer_thread`)* | Hơi thiên lệch phong cách sinh viên/người trẻ nếu không phát thẻ vai diễn đa dạng | **Nguồn xương sống cho `train` / `dev` / `test_human_simulated`** trong giai đoạn khởi đầu MVP |
| **Source C**<br>`synthetic_targeted` | Tức thì | Script biến đổi có kiểm soát hoặc LLM phác thảo theo kịch bản + **người thật duyệt từng câu** | Không chứa dữ liệu người thật; kiểm tra điều khoản LLM nếu dùng | Rất thấp | Thấp – Trung bình *(dễ lặp khuôn mẫu cú pháp)* | Trung bình *(phục vụ đúng ca biên kỹ thuật)* | Nguy cơ rò rỉ template và điểm F1 cao giả tạo nếu trộn bừa bãi | **Chỉ dùng bổ trợ ca hiếm/adversarial (`E02/E03/E04`)** & nhánh đối chứng `train_augmented`; **cấm đưa vào holdout người thật** |

### 2.3 Chiến lược Khuyến nghị cho Nhóm Sinh viên / Startup MVP (`PROPOSED`)
Với nguồn lực gọn nhẹ, lộ trình thực tế và trung thực khoa học nhất gồm **2 mũi nhọn song song**:
1. **Chủ động tự chủ tiến độ bằng `Source B` (`human_simulated_live` ~ 70–80% tập cơ sở) + `Source C` có kiểm soát (~ 20–30% chỉ cho ca biên/an toàn):** Tổ chức 3–4 buổi diễn tập nội bộ trên đúng 5 SKU thực phẩm đóng gói để thu về `500–700` bình luận người thật gõ tự nhiên có đầy đủ `viewer_thread_id` và `active_sku_at_comment_time`. Nhờ đó bạn **không bị tê liệt tiến độ** nếu việc xin dữ liệu shop ngoài mất nhiều thời gian.
2. **Dồn toàn bộ `Source A` (`real_permissioned_commerce`) thu được giai đoạn đầu vào Két Kiểm thử Độc lập (`test_real`):** Chỉ cần xin phép hợp pháp được 1–2 buổi live thực tế từ một shop bán trà/mật ong/hạt dinh dưỡng/đặc sản (`150–300` bình luận sau lọc rác trùng), giữ nguyên 100% làm `test_real` độc lập. Nếu tại thời điểm chạy `E01` vòng đầu vẫn chưa tiếp cận được `Source A`, báo cáo kết quả trung thực trên `test_human_simulated` và giữ trạng thái P07 ở `IN EXPERIMENT` (ghi rõ `OPEN-1: Real commerce holdout pending`), tuyệt đối không tuyên bố `real-world VALIDATED`.

---

## 3. Legal / Permission & Privacy Checklist

Trước khi bất kỳ tệp dữ liệu nào được đưa vào `data/annotations/` hoặc commit lên Git, người phụ trách dữ liệu phải tích đạt **100% các mục sau**:

- [ ] **Không thu thập trái phép:** Không có bất kỳ dòng dữ liệu nào được lấy bằng công cụ cào tự động (web scraper/crawler) trái điều khoản nền tảng hoặc từ buổi live chưa có sự đồng ý của chủ sở hữu.
- [ ] **Lưu bằng chứng cấp phép (`permission_ref`):** Mỗi `source_id` có tham chiếu tới phiếu đồng ý của chủ shop (`Source A`) hoặc danh sách xác nhận đồng ý của người tham gia diễn tập (`Source B`) lưu ở thư mục bảo mật nội bộ ngoài Git.
- [ ] **Khử sạch Dữ liệu Cá nhân (`PII Redaction` — tuân thủ Luật BVDLCN `91/2025/QH15`):**
  - Thay thế toàn bộ số điện thoại Việt Nam (`03x/05x/07x/08x/09x/+84`, kể cả viết cách hoặc lẫn dấu chấm) bằng token `<PHONE>`.
  - Thay thế địa chỉ số nhà/ngõ/phường cụ thể bằng `<ADDRESS>`, email bằng `<EMAIL>`, số tài khoản bằng `<ACCOUNT>`, tên cá nhân nhạy cảm bằng `<PERSON>`.
- [ ] **Pseudonymization một chiều cho Người xem:** Trường `guest_session_id` và tên tài khoản gốc đã được băm mặn (`HMAC-SHA256` với khóa cục bộ không commit) hoặc đổi sang mã thứ tự phiên (`guest_s01_004`), không thể suy ngược ra danh tính thật.
- [ ] **Kiểm tra an toàn kho Git:** Tệp gốc chưa khử PII (`unscrubbed_*`) tuyệt đối nằm ngoài Git (hoặc bị chặn cứng trong `.gitignore`); chỉ dữ liệu đã đạt `pii_scrub_status == "SCRUBBED_VERIFIED"` mới được chuyển sang bước gán nhãn.

---

## 4. Collection SOP (Quy trình Thu thập 10 Bước Thực tế)

| Bước | Tên bước | Thao tác thực tế cần làm | Công cụ gợi ý | Đầu ra (File / Trạng thái) | Tiêu chí hoàn thành (Exit Criteria) |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Source Discovery** | Lập danh sách ứng viên nguồn `Source A` (shop thực phẩm/OCOP quen biết) và lên lịch các phiên diễn tập `Source B` (chốt người dẫn, 5 SKU, danh sách 6–12 người tham gia/phiên). | Bảng theo dõi nội bộ (Markdown / Sheet) | Sổ đăng ký nguồn `source_registry` (ngoài Git nếu chứa tên đối tác riêng tư) | Xác định rõ ít nhất 3 buổi `Source B` và danh sách liên hệ `Source A`. |
| **2** | **Permission & Terms Verification** | Ký/xác nhận phiếu đồng ý với chủ shop (`Source A`) hoặc phiếu đồng ý tham gia nghiên cứu với tình nguyện viên (`Source B`); kiểm tra phạm vi được phép lưu trữ. | Google Forms / PDF ký xác nhận | Mã tham chiếu `permission_ref` + `permission_status = "GRANTED"` | `0` nguồn nào chuyển sang Bước 3 nếu `permission_status != "GRANTED"`. |
| **3** | **Collection** | - `Source B`: Chạy phiên diễn tập 20–25 phút, Host ghi mốc đổi SKU, người xem gõ bình luận trực tiếp trên điện thoại/máy tính.<br>- `Source A`: Nhận file xuất hợp lệ từ chủ shop.<br>- `Source C`: Tạo lô nhỏ ca biên theo kịch bản thiếu hụt. | Phòng chat có log thời gian / CSV export | Tệp thô ban đầu (lưu cục bộ vùng kín ngoài Git) | Ghi nhận nguyên vẹn văn bản gốc và dấu thời gian gốc (nếu nguồn có). |
| **4** | **Secure Storage** | Đặt tệp thô chưa khử PII vào thư mục cục bộ được bảo vệ quyền truy cập (không đặt trong nhánh Git sẽ push). Ghi mã băm gốc của tệp nhận về. | Ổ đĩa cục bộ mã hóa / Kho lưu trữ nội bộ có phân quyền | Bản sao lưu gốc chỉ dành cho Data Steward | Kiểm tra `git status` xác nhận tệp thô chưa khử PII không bị theo dõi bởi Git. |
| **5** | **PII Handling & Pseudonymization** | Chạy script regex dò SĐT/email/địa chỉ + **1 người rà soát mắt 100% dòng** để thay bằng `<PHONE>`, `<ADDRESS>`; ánh xạ định danh người xem sang `guest_session_id` ẩn danh (`guest_sXX_pYY`). | Script Python stdlib (`re`, `hmac`) + rà soát thủ công | `data/raw/<source_id>_scrubbed.jsonl` | 100% bản ghi có `pii_scrub_status = "SCRUBBED_VERIFIED"`, `0` SĐT/địa chỉ thật sót lại. |
| **6** | **Initial Quality Screening** | Loại bỏ các dòng lỗi hệ thống không phải bình luận người dùng (ví dụ dòng log `"User joined room"`, dòng hoàn toàn trống `""` do lỗi xuất CSV); giữ nguyên emoji/slang thật của người xem! | Script kiểm tra định dạng dòng | Báo cáo lọc thô ban đầu | Không xóa nhầm bình luận ngắn hoặc spam thật của người xem (vì P07 cần học lọc spam!). |
| **7** | **Exact Event Deduplication** | Khử các bản ghi bị xuất đúp do lỗi mạng/xuất file (cùng `session_id`, cùng `guest_session_id`, cùng `raw_text` trong khoảng `< 2 giây` hoặc trùng khóa sự kiện nguồn). Giữ nguyên trường hợp người xem cố tình xả spam nhiều lần cách nhau hoặc khác người xem! | Script khử trùng chính xác | `data/raw/<source_id>_deduped.jsonl` | Mỗi sự kiện gửi duy nhất có đúng 1 `comment_id` chuẩn. |
| **8** | **Source & Provenance Tagging** | Gắn đầy đủ `data_origin`, `collection_method`, `session_catalog_context`, `active_sku_at_comment_time` (`"UNKNOWN"` nếu nguồn `A` không rõ), nối `viewer_thread_id` theo thứ tự thời gian của từng `guest_session_id` và gắn `paraphrase_cluster_id` ban đầu (nếu là `Source C`). | Script chuẩn hóa schema thô | Bản ghi đạt chuẩn Raw Schema (Mục 5) | 100% bản ghi vượt qua bộ kiểm tra kiểu dữ liệu Raw Schema (`0` trường bịa đặt). |
| **9** | **Annotation Preparation** | Xuất các trường cần thiết cho người gán nhãn (ẩn hoàn toàn nhãn gợi ý của luật/LLM để tránh thiên kiến mỏ neo!), kèm bảng tra cứu nhanh 2–5 SKU của phiên và tối đa 2 bình luận liền trước của chính `guest_session_id` đó. | Xuất sang tệp bảng (`.tsv`/`.xlsx` khóa danh sách chọn) hoặc Label Studio local | `data/annotations/batches/batch_<id>_blind.tsv` | Hai người gán nhãn nhận hai tệp độc lập không nhìn thấy kết quả của nhau. |
| **10** | **Dataset Inventory & Versioning** | Cập nhật sổ kiểm kê tổng số mẫu theo từng nguồn, từng phiên, tính mã băm `SHA-256` cho các tệp trong `data/raw/` (bản đã khử PII) và chuẩn bị bàn giao sang Annotation SOP. | CLI tạo manifest JSON | `data/raw/raw_inventory_v0.1.json` | Khớp tổng số dòng, mã băm `SHA-256` và trạng thái `permission_status == "GRANTED"`. |

---

## 5. Raw & Annotated Dataset Schema (4 Nhóm Trường Rạch ròi)

Mỗi bản ghi bình luận được quản lý xuyên suốt vòng đời qua 4 nhóm trường tách biệt rõ nguồn sinh dữ liệu. **Quy tắc trung thực tuyệt đối:** nếu nguồn thực tế (`Source A`) không có thông tin như `active_sku_at_comment_time` hoặc `guest_session_id`, bắt buộc ghi `"UNKNOWN"` hoặc `"MISSING"`, không tự suy đoán điền bừa!

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
  "external_dedup_key": "sim-msg-0042"
}
```
*(Nếu `Source A` không có timestamp chính xác hoặc không tách được người gửi: cho phép `collection_timestamp = null` kèm `timestamp_status = "MISSING"` và `guest_session_id = "UNKNOWN_VIEWER_SRC_A_0042"` — khi đó không tự nối `viewer_thread_id` đa lượt cho mẫu đó).*

### Nhóm 5.2 — Metadata Ngữ cảnh & Provenance Bổ sung Thủ công / Có Kiểm soát (`Curated Provenance Metadata`)
```json
{
  "permission_status": "GRANTED",
  "permission_ref": "CONSENT-SIM-2026-S01",
  "pii_scrub_status": "SCRUBBED_VERIFIED",
  "session_catalog_context": ["SKU-HONEY-01", "SKU-TEA-02", "SKU-CASHEW-03"],
  "active_sku_at_comment_time": "SKU-HONEY-01",
  "active_sku_confidence": "EXACT_LOGGED",
  "viewer_thread_id": "thread-sim-s01-p07",
  "prior_viewer_comments_in_session": [
    {"comment_id": "p07-raw-s01-0035", "raw_text": "chai mật ong 500ml giá bn shop"}
  ],
  "paraphrase_cluster_id": null,
  "template_family_id": null,
  "synthetic_provenance": null,
  "annotation_status": "READY_FOR_ANNOTATION"
}
```
*(Với `Source C` synthetic, `synthetic_provenance` bắt buộc ghi `{"method": "template_or_llm", "template_family_id": "tpl_crystallization_01", "human_reviewer": "member_01"}` và `paraphrase_cluster_id = "pclust_crystallization_01"`).*

### Nhóm 5.3 — Nhãn Chuẩn do Người Gán nhãn Tạo (`Annotator Gold Labels` — sau phân xử)
```json
{
  "gold_labels": {
    "moderation_status": "ELIGIBLE",
    "primary_intent": "ASK_ORIGIN_OCOP",
    "secondary_intents": ["ASK_SPEC_USAGE"],
    "sku_resolution_mode": "EXPLICIT_SINGLE",
    "referenced_sku_ids": ["SKU-HONEY-01"],
    "phenomenon_tags": ["no_diacritics", "authenticity_doubt"],
    "annotator_a_id": "ann_01",
    "annotator_b_id": "ann_02",
    "adjudicated_by": "lead_01",
    "taxonomy_version": "v0.1"
  }
}
```

### Nhóm 5.4 — Đặc trưng Sinh Tự động ở Tiền xử lý & Chia tập (`Preprocessing / Split Derived Fields`)
```json
{
  "derived_split_meta": {
    "normalized_text": "mật ong này để tủ lạnh bị đóng đường có phải hàng pha không shop",
    "unaccent_fingerprint": "mat ong nay de tu lanh bi dong duong co phai hang pha ko shop",
    "near_dup_cluster_id": "ndup-0038",
    "split_group_id": "sgrp-0019",
    "assigned_split": "train"
  }
}
```

---

## 6. Sampling Strategy (Chiến lược Lấy mẫu Tự nhiên kết hợp Bù đắp Lớp Hiếm)

Tất cả các con số chỉ tiêu dưới đây mang trạng thái **`PROPOSED`** cho tới khi bạn duyệt và hoàn tất bước Pilot `D2`:

### 6.1 Phân biệt Hai Chế độ Lấy mẫu
1. **Natural Stream Sampling (Lấy mẫu giữ nguyên phân phối tự nhiên — ~70% dữ liệu):**
   - Thu toàn bộ luồng bình luận theo đúng trật tự thời gian từ các buổi diễn tập `Source B` và phiên thực tế `Source A` (sau khi khử trùng sự kiện lỗi mạng).
   - **Mục đích:** Phản ánh trung thực tỷ lệ thật của câu hỏi giá/ship so với câu khen xã giao và spam, dùng để đánh giá công bằng trên tải `W1/W2` và hiệu chuẩn xác suất (`calibration`).
2. **Targeted Scenario / Rare-Class Sampling (Lấy mẫu có chủ đích cho lớp thưa — ~30% dữ liệu):**
   - Trong livestream tự nhiên, các lớp `ASK_PRICE_PROMO`, `ASK_SHIPPING_RETURN`, `SOCIAL_CHITCHAT` thường chiếm đa số, trong khi `COMPARE_PRODUCTS`, `ASK_SAFETY_SUITABILITY` (bà bầu/dị ứng/mồi chữa bệnh `R17`), `OUT_OF_CATALOG`, `ABUSE_BLOCKED` và `PROMPT_INJECTION` xuất hiện thưa hơn.
   - **Cách bù đắp đúng phương pháp (Không ép nhãn sai!):** Thay vì sửa nhãn câu mơ hồ cho đủ chỉ tiêu, ta thiết kế thêm **Thẻ Vai diễn chuyên biệt** ở buổi diễn tập `Source B` tiếp theo (ví dụ giao vai khách hàng so sánh 2 món hoặc khách hỏi dị ứng/bà bầu) và bổ sung lô nhỏ `Source C` có kiểm duyệt cho riêng `PROMPT_INJECTION` và `ABUSE_BLOCKED`.

### 6.2 Khung Chỉ tiêu Phân bổ Mục tiêu (`PROPOSED` cho Tập Chính `600–1.000` mẫu)
- **9 lớp `primary_intent` (trên các mẫu `ELIGIBLE`):** Hướng tới tối thiểu **`55 – 80` mẫu thuộc các `split_group_id` độc lập cho mỗi lớp** (tổng ~ `550 – 750` mẫu `ELIGIBLE`), đảm bảo mỗi lớp có đủ `32` nhóm độc lập cho tập `train` (phục vụ `32-shot` trong `P07-E01`), `>= 10–12` mẫu cho `dev` và `>= 15–20` mẫu cho `held-out test`.
- **3 lớp bị chặn ở `moderation_status` (`SPAM_FLOOD`, `ABUSE_BLOCKED`, `PROMPT_INJECTION`):** Hướng tới `100 – 180` mẫu tổng cộng (`~40–70 SPAM_FLOOD`, `~30–50 ABUSE_BLOCKED`, `~30–60 PROMPT_INJECTION`) để đo chính xác `Spam False Positive Rate` và tỷ lệ chặn tấn công chèn lệnh.
- **Độ phủ Ngữ cảnh SKU & Hội thoại:** Phủ tối thiểu **4 cấu hình catalog phiên khác nhau** (2 phiên 3 SKU, 2 phiên 5 SKU), tối thiểu **25–30 người xem độc lập (`guest_session_id`)**, và có đủ cả 7 chế độ `sku_resolution_mode` (đặc biệt tối thiểu `40+` mẫu `CONTEXTUAL_SINGLE` và `40+` mẫu `UNCLEAR` / `OUT_OF_CATALOG`).

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

## 9. Dataset Split & Anti-Leakage Gate

Tuân thủ nghiêm ngặt thuật toán **Đồ thị Thành phần Liên thông (`Connected Components / Union-Find`)** tại [p07-dataset-and-evaluation-protocol.md](./p07-dataset-and-evaluation-protocol.md) (§1.5):

1. **Liên kết Bắc cầu (`Transitive Closure`):** Nối cạnh giữa hai bản ghi bất kỳ nếu chúng trùng `viewer_thread_id` (hoặc cùng `(session_id, guest_session_id)`), trùng `paraphrase_cluster_id`, trùng `template_family_id`, **hoặc** bị bộ quét trùng lặp gần (`unaccent_fingerprint` trùng khít hoặc `char-3gram Jaccard >= 0.85`) phát hiện. Mỗi thành phần liên thông nhận một `split_group_id` duy nhất.
2. **Phân bổ Tập dữ liệu Độc lập:**
   - Mọi mẫu cùng `split_group_id` bắt buộc đi vào cùng một tập (`train`, `dev` hoặc `test`).
   - Tỷ lệ phân bổ đề xuất (`PROPOSED` trên dữ liệu `human_simulated_live`): `60% train / 15% dev / 25% test_human_simulated` theo số lượng mẫu có phân tầng nhãn `primary_intent` và `moderation_status`.
3. **Cách xử lý trung thực khi Dữ liệu Thực tế (`Source A`) còn ít:**
   - Nếu chỉ thu thập được `100 – 300` mẫu `real_permissioned_commerce`, **không xé lẻ** tập nhỏ này vào `train`! Hãy đóng băng toàn bộ `100%` tập `Source A` đó làm **`test_real` (Pure Zero-Leakage Real Holdout)** để kiểm tra khả năng tổng quát hóa thực tế của mô hình được huấn luyện trên `Source B`.
   - Khi báo cáo kết quả, luôn trình bày thành các bảng riêng (`test_real`, `test_human_simulated`, `test_synthetic_adversarial`), ghi rõ kích thước mẫu $N$ của từng lát cắt để người đọc đánh giá đúng khoảng tin cậy.

---

## 10. Data Versioning, Manifests & Evidence

Cấu trúc lưu trữ chuẩn hóa bên trong `experiments/sales-intelligence/comment-understanding/data/`:

```text
data/
├── raw/
│   ├── session_catalog_5sku_v0.1.json      # Danh mục 5 SKU chuẩn kế thừa P05
│   ├── sim_s01_scrubbed_deduped.jsonl      # Đã khử PII + exact dedup (chỉ khi được phép lưu repo)
│   └── raw_inventory_v0.1.json             # Số lượng mẫu, nguồn, permission_ref, SHA-256
├── annotations/
│   ├── pilot_iaa_report_v0.1.json          # Kết quả Cohen's Kappa & biên bản phân xử Pilot
│   └── p07_gold_v0.1.jsonl                 # Toàn bộ mẫu kèm nhãn chuẩn sau phân xử
└── processed/
    ├── train_v0.1.jsonl
    ├── dev_v0.1.jsonl
    ├── test_human_simulated_v0.1.jsonl
    ├── test_real_v0.1.jsonl                # Khi có Source A được cấp phép
    ├── e02_adversarial_v0.1.jsonl
    ├── e03_grouping_pairs_v0.1.jsonl
    ├── e04_burst_traces_v0.1.jsonl
    └── dataset_manifest_v0.1.json          # Khóa SHA-256, thống kê lớp, bằng chứng 0-leakage
```

*(Lưu ý bảo mật: Nếu một nguồn `Source A` chỉ cho phép dùng nội bộ trên máy cá nhân mà không cho đẩy văn bản bình luận lên kho Git chung, tệp `.jsonl` của nguồn đó được đặt vào danh sách loại trừ `.gitignore`, và Git chỉ lưu `dataset_manifest_v0.1.json` chứa mã băm `SHA-256`, phân phối nhãn và hướng dẫn nạp từ kho bảo mật của nhóm).*

---

## 11. Execution Roadmap (`D0` → `D6`)

Thiết kế cho quy mô nhóm gọn (`1 Research/Tech Lead + 1–2 thành viên phối hợp gán nhãn + 6–10 tình nguyện viên tham gia buổi diễn tập ngắn`), sắp theo thứ tự phụ thuộc mà không áp đặt ngày lịch cứng:

| Mốc | Công việc cụ thể | Phụ trách đề xuất | Phụ thuộc | Deliverables | Acceptance Criteria | Rủi ro & Phương án dự phòng |
| :-: | :--- | :--- | :---: | :--- | :--- | :--- |
| **`D0`**<br>*Source & Permission Planning* | Chốt 5 SKU diễn tập (từ P05), soạn Thẻ Vai diễn mở, mẫu Phiếu Đồng ý (`Source A` & `B`), cấu hình nơi ghi log buổi diễn tập và liên hệ thử 1–3 shop đối tác. | Research Lead (bạn) | Duyệt kế hoạch này | Mẫu phiếu đồng ý, `session_catalog_5sku_v0.1.json`, bộ 10–12 Thẻ Vai diễn | Không có câu hỏi mẫu lộ trong Thẻ Vai diễn; chốt danh sách người tham gia buổi 1. | *Rủi ro:* Shop ngoài phản hồi chậm.<br>*Dự phòng:* Chạy ngay `Source B` không chờ `Source A`. |
| **`D1`**<br>*Initial Data Collection* | Tổ chức buổi diễn tập `Source B` đầu tiên (20–25 phút, 6–10 người) + nhận lô `Source A` đầu tiên (nếu có); chạy SOP Bước 4–8 (khử PII, exact dedup, gắn ngữ cảnh SKU/thread). | Research Lead + Tình nguyện viên | `D0` | Lô dữ liệu sạch đầu tiên (`>= 120–150` bình luận đã khử PII) + `raw_inventory` | `100%` `pii_scrub_status == "SCRUBBED_VERIFIED"`, `0` lỗi định dạng Raw Schema. | *Rủi ro:* Người tham gia gõ quá lịch sự/đầy đủ dấu.<br>*Dự phòng:* Yêu cầu gõ trên điện thoại ở tốc độ nghe trực tiếp. |
| **`D2`**<br>*Annotation Pilot (50–100 samples)* | Trích `50–100` mẫu từ `D1` làm gói mù; 2 người gán nhãn độc lập theo Guideline; chạy tính Cohen's `κ` trên cả 3 chiều. | Annotator A + Annotator B | `D1` | 2 tệp gán nhãn độc lập + `pilot_iaa_report_v0.1.json` | Đo xong `κ_moderation`, `κ_primary_intent`, `κ_sku_mode` và liệt kê toàn bộ dòng lệch nhau. | *Rủi ro:* `κ` thấp ở cặp `ASK_SPEC_USAGE` vs `ASK_SAFETY_SUITABILITY`.<br>*Dự phòng:* Bổ sung quy tắc ranh giới cụ thể ở `D3`. |
| **`D3`**<br>*Guideline Refinement & Taxonomy Freeze v0.1* | Họp phân xử các ca bất đồng ở `D2`, cập nhật ví dụ ranh giới vào [p07-annotation-guideline-v0.1.md](./p07-annotation-guideline-v0.1.md) và chính thức đóng băng Taxonomy `v0.1`. | Research Lead + Annotators | `D2` | Guideline `v0.1` đã khóa + nhãn chuẩn của gói Pilot | Không còn cặp nhãn mơ hồ về định nghĩa; Owner ký xác nhận khóa Taxonomy `v0.1`. | *Rủi ro:* Muốn tách/gộp nhãn.<br>*Dự phòng:* Quyết định dứt điểm tại `D3` để không phải gán lại ở `D4`. |
| **`D4`**<br>*Main Dataset Acquisition & Annotation* | Tổ chức thêm 2–3 buổi `Source B` (có thẻ vai diễn bù lớp thưa) + thu `Source A` (nếu có) + tạo lô nhỏ `Source C` cho ca biên (`E02/E03/E04`); gán nhãn chính thức và kiểm định chéo `>= 20%`. | Cả nhóm | `D3` | `data/annotations/p07_gold_v0.1.jsonl` + cặp `e03_grouping_pairs` | Đạt quy mô mục tiêu đã duyệt, đủ đại diện 9 lớp Intent, `100%` pass Structural Validator. | *Rủi ro:* Thiếu mẫu ở lớp hiếm (`COMPARE_PRODUCTS`, `PROMPT_INJECTION`).<br>*Dự phòng:* Bổ sung có mục tiêu theo Mục 6.1. |
| **`D5`**<br>*Quality Control & Leakage-Safe Split* | Chạy quét trùng lặp gần (`near-duplicate`), dựng đồ thị `Union-Find` tạo `split_group_id`, chia `train / dev / test_*` và chạy kiểm toán hậu kiểm `0` rò rỉ. | Research Lead | `D4` | Các tệp split trong `data/processed/` + báo cáo kiểm toán chống rò rỉ | Giao của `split_group_id`, `paraphrase_cluster_id`, `viewer_thread_id` giữa mọi split bằng `∅`. | *Rủi ro:* Một thành phần liên thông quá lớn làm lệch tỷ lệ lớp.<br>*Dự phòng:* Kiểm tra nguyên nhân nối bắc cầu và điều chỉnh phân bổ nhóm. |
| **`D6`**<br>*Dataset Freeze & E01 Readiness* | Xuất `dataset_manifest_v0.1.json` kèm mã băm `SHA-256` cho mọi tệp, tạo sẵn các tập con few-shot `{8, 16, 32} × 3 seeds` từ `train`, cập nhật `p07-experiment-readiness.md`. | Research Lead | `D5` | `dataset_manifest_v0.1.json` đã khóa + khóa két `held-out test` | Sẵn sàng 100% về mặt dữ liệu để mở khóa thực thi `P07-E01`. | *Rủi ro:* Vô tình sửa tệp sau khi chạy model.<br>*Dự phòng:* Mọi script thí nghiệm bắt buộc kiểm tra khớp `SHA-256` trước khi chạy. |

---

## 12. Open Decisions & Action Checklist (Cần Bạn Duyệt để Khởi động `D0`)

### A. Các lựa chọn cần bạn chốt (`PROPOSED` -> Quyết định)
1. **Phối thức Nguồn Dữ liệu Khởi điểm (`D0`):** Bạn đồng ý đi theo chiến lược kép — **tổ chức ngay 3–4 buổi diễn tập `Source B` (`human_simulated_live` trên 5 SKU P05) làm xương sống chủ động**, song song tìm kiếm 1–2 phiên `Source A` (`real_permissioned_commerce`) để dành riêng làm `test_real` chứ? (Bạn hiện đã có mối liên hệ với shop thực phẩm/nông sản nào có thể xin phép log bình luận chưa?)
2. **Quy mô Mục tiêu Tập `v0.1` và Ngưỡng Đồng thuận Pilot IAA:** Bạn có đồng ý giữ chỉ tiêu khởi điểm `600–1.000` bình luận cho tập chính (`>= 55` nhóm độc lập/lớp Intent), gói Pilot `50–100` mẫu và mục tiêu tham chiếu `κ >= 0.70–0.80` ở Mục 6 & Mục 8 không?
3. **Nhân sự Gán nhãn Độc lập:** Trong nhóm hiện tại của bạn có sẵn **ít nhất 2 người** để đóng vai `Annotator A` và `Annotator B` cho vòng Pilot `50–100` mẫu không, và bạn muốn dùng **Bảng tính khóa Dropdown (`.xlsx`/Sheets)** hay **Label Studio local** để chuẩn bị mẫu ở Bước 9?

### B. Checklist Hành động Ngay khi Bắt đầu `D0`
- [ ] Duyệt chốt 5 tài liệu thiết kế + kế hoạch thu thập dữ liệu này.
- [ ] Tạo tệp danh mục `data/raw/session_catalog_5sku_v0.1.json` (kế thừa 5 SKU từ P05) và bộ 10–12 Thẻ Vai diễn mở cho buổi diễn tập `Source B` số 1.
- [ ] Thiết lập quy tắc `.gitignore` bảo vệ các tệp thô chưa khử PII (`*unscrubbed*`, `permission_records/`) và viết bộ script Python kiểm tra Raw Schema + khử PII + tính Cohen's `κ` trước khi thu lô dữ liệu đầu tiên (`D1`).
