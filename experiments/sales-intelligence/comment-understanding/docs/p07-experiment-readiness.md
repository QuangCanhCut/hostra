# P07 — Đánh giá 4 Cổng Sẵn sàng Thực nghiệm (Staged Readiness Gates)

| Thuộc tính | Giá trị |
| :--- | :--- |
| **Mã tài liệu** | `P07-DOC-05` |
| **Phiên bản / Ngày** | `v0.1.3 (Preflight + Product-Agnostic Generalization)` — `26/11/2026` |
| **Mục tiêu** | Tách bạch các mức độ sẵn sàng theo từng bước thực tế (`Source Discovery -> Data Pilot -> Main Dataset -> E01`) để nhóm triển khai ngay bước khảo sát và thu thập thử mà không bị nghẽn bởi các yêu cầu của giai đoạn sau |
| **Phán quyết tóm tắt** | **`Gate 1 (Source Discovery): READY`** · **`Gate 2 (Data Acquisition Pilot 50–100): CONDITIONALLY READY`** · **`Gate 3 (Main Dataset): BLOCKED (Chờ kết quả Pilot)`** · **`Gate 4 (E01 Run): BLOCKED (Chờ Dataset & E01 Harness)`** |
| **Nguồn tham chiếu** | [p07-problem-and-requirements.md](./p07-problem-and-requirements.md), [p07-contract-v0.1.md](./p07-contract-v0.1.md), [p07-annotation-guideline-v0.1.md](./p07-annotation-guideline-v0.1.md), [p07-data-acquisition-and-annotation-plan-v0.1.md](./p07-data-acquisition-and-annotation-plan-v0.1.md), [p07-dataset-and-evaluation-protocol.md](./p07-dataset-and-evaluation-protocol.md) |

---

## 1. Quy ước Trạng thái & Triết lý Mở khóa Theo Tầng

Thay vì gộp mọi yêu cầu của toàn bộ chuỗi `E01–E04` và tích hợp `P08` thành một hàng rào duy nhất gây tê liệt tiến độ, P07 quản trị mức sẵn sàng qua **4 Cổng tuần tự (`Gate 1` → `Gate 4`)**:

- **`READY`**: Đủ tài liệu, biểu mẫu và quy tắc an toàn trong repository để thực hiện ngay hôm nay.
- **`CONDITIONALLY READY`**: Thiết kế kỹ thuật/SOP trong repo đã hoàn tất; chỉ cần xác nhận vận hành của Owner và kiểm tra quyền sử dụng trên từng nguồn cụ thể trước khi thu dữ liệu.
- **`BLOCKED`**: Chưa thể thực hiện vì phụ thuộc trực tiếp vào dữ liệu thực tế/bằng chứng của cổng liền trước.
- **`PRE-INTEGRATION REQUIRED` / `VALIDATION PENDING`**: Thuộc giai đoạn nối hệ thống production hoặc chờ kết quả benchmark — **tuyệt đối không dùng để chặn việc khảo sát dữ liệu hay chạy `P07-E01`**.

---

## 2. Đánh giá Chi tiết 4 Cổng Sẵn sàng (`Gate 1` → `Gate 4`)

### `Gate 1` — Source Discovery Ready (Khảo sát Nguồn Dữ liệu Thực tế Đa dạng Sản phẩm)
- **Trạng thái hiện tại:** **`READY`** *(Có thể bắt đầu ngay lập tức)*
- **Những gì đã sẵn sàng:**
  - Đã xác định rõ miền khảo sát mở rộng (livestream thực phẩm đóng gói, nông sản chế biến, đặc sản vùng miền/OCOP, đồ uống, ngũ cốc, bánh mứt, gia vị... **không bó hẹp trong 5 SKU mẫu của P05**; bộ 5 SKU của P05 chỉ dùng làm fixture tích hợp tham chiếu).
  - Đã có danh mục kênh tiếp cận hợp pháp (`Source A` ưu tiên số 1 qua nhiều merchant/phiên khác nhau, phiên live kín có phép của HOSTRA, và `Source B` diễn tập đa danh mục sản phẩm), các hành vi bị cấm tuyệt đối (cấm cào tự động/trái ToS), và khuôn mẫu `Source Registry` tại [p07-data-acquisition-and-annotation-plan-v0.1.md](./p07-data-acquisition-and-annotation-plan-v0.1.md) (§2, §3, §11).
- **Lưu ý giải phóng tiến độ:** Nhánh dữ liệu **không cần chờ** viết code phân loại ML, không cần chốt `P08MockScheduler` và không cần đóng băng hợp đồng production để bắt đầu liên hệ shop đối tác khảo sát định dạng log bình luận.

---

### `Gate 2` — Data Acquisition Pilot Ready (Thu thập & Kiểm tra Thử `50–100` Bình luận)
- **Trạng thái hiện tại:** **`CONDITIONALLY READY`** *(Tài liệu & biểu mẫu đã sẵn sàng; cần chốt vận hành nội bộ trước khi nhận file)*
- **Những gì đã sẵn sàng trong bộ tài liệu `v0.1.2`:**
  - Cẩm nang tác nghiệp 12 bước **`Quick Start — Data Acquisition Pilot`** và đủ 4 khuôn mẫu bảng (`Source Registry`, `Raw Comment Collection Sheet`, `Pilot Data Quality Report`, `Annotation Sheet`) tại [p07-data-acquisition-and-annotation-plan-v0.1.md](./p07-data-acquisition-and-annotation-plan-v0.1.md) (§11).
  - Schema nghiên cứu offline hỗ trợ cờ khuyết ngữ cảnh (`metadata_availability`, `evaluation_eligibility`, `NOT_EVALUABLE`), quy tắc 3 mức khử trùng (bỏ luật xóa `< 2s` sai lầm) và bộ 6 quy tắc biên trong [p07-annotation-guideline-v0.1.md](./p07-annotation-guideline-v0.1.md) (§2.4).
- **3 điều kiện tác nghiệp cần tích đạt ngay trước khi thu `50–100` bình luận:**
  1. Owner duyệt bộ tài liệu hiệu chỉnh `v0.1.2` này và chỉ định rõ **Data Steward** + **2 người gán nhãn độc lập (`Annotator A`, `Annotator B`)**.
  2. Nguồn được chọn chạy Pilot phải hoàn tất xác minh điều khoản nền tảng & văn bản đồng ý (`permission_status == "GRANTED"`).
  3. Tạo thư mục lưu trữ cục bộ ngoài Git (hoặc cấu hình `.gitignore` chặn cứng `*unscrubbed*`, `permission_records/`) trước khi tải tệp bình luận gốc về máy.

---

### `Gate 3` — Main Dataset Acquisition Ready (Thu thập & Gán nhãn Tập Chính `D4–D6`)
- **Trạng thái hiện tại:** **`BLOCKED`** *(Chờ bằng chứng thực tế từ `Gate 2`)*
- **Điều kiện bắt buộc để mở khóa `Gate 3`:**
  1. Hoàn thành thu thập thử `50–100` bình luận đã khử sạch PII (`SCRUBBED_VERIFIED`) và gán nhãn mù 2 người ở `Gate 2`.
  2. Có **`Pilot Data Quality Report`** trả lời bằng số liệu thật: tỷ lệ khuyết `active_sku` / `catalog` của nguồn thật là bao nhiêu, các lớp Intent nào bị thiếu tự nhiên, tần suất câu siêu ngắn lặp mặt chữ là bao nhiêu, và độ đồng thuận `κ` đạt mức nào.
  3. Họp phân xử các dòng lệch ở Pilot, tinh chỉnh quy tắc biên lần cuối, **đóng băng Taxonomy `v0.1`**, cách ly gói Pilot (`inspected_in_pilot = true`, không đưa vào `held-out test`), và hiệu chỉnh lại con số quy mô phiên/người tham gia/số mẫu mục tiêu cho tập chính.
  4. Chuẩn bị xong các công cụ kiểm định dữ liệu bằng Python (`schema & eligibility validator`, `PII check`, `Cohen's kappa`, kiểm toán tương quan giả `Product × Intent`, và `Guarded Union-Find splitter` tách được cả `test_seen_product` và `test_unseen_product` mà không vi phạm bất kỳ ràng buộc chống rò rỉ nào).

---

### `Gate 4` — `P07-E01` Experiment Execution Ready (So sánh Classifier Độc lập Sản phẩm & Tiền xử lý Ablation)
- **Trạng thái hiện tại:** **`BLOCKED`** *(Chờ hoàn tất `Gate 3` và harness `E01`)*
- **Điều kiện bắt buộc để mở khóa `Gate 4`:**
  1. Tập dữ liệu chính đã qua kiểm định đồ thị chống rò rỉ (`0` rò rỉ `split_group_id` / `viewer_thread_id` / `participant_id` / `paraphrase_cluster_id` / `template_family_id`, đã kiểm tra tương quan giả `Product × Intent`), tách rõ `test_seen_product` và **`test_unseen_product`**, khóa mã băm `SHA-256` trong `dataset_manifest_v0.1.json` và tạo sẵn các tập con `{8, 16, 32} × 3 seeds`.
  2. Chốt công cụ tách từ tiếng Việt giấy phép thương mại sạch cho `vinai/phobert-base` (MIT, ví dụ `pyvi` MIT; cấm dùng `phobert-base-v2` AGPLv3) và cấu hình LLM đối chứng cho `B1`/`H1`.
  3. Hiện thực xong mã cơ sở của riêng `E01`: 4 biến thể tiền xử lý (`Raw`, `Normalized`, `Product Masked`, `Normalized + Product Masked` — `PROPOSED / VALIDATION PENDING`), baseline `B0_rules_only`, `B1_rules_plus_llm_all`, runner đo `Seen-Product Macro-F1`, `Unseen-Product Macro-F1`, `Generalization Gap`, độ trễ `batch_size = 1` và trình xuất `ExperimentManifest` (`hard_gates` khởi tạo `"NOT_RUN"`).
  4. Chủ nhiệm nghiên cứu chốt các ngưỡng đánh giá đang gắn nhãn `THRESHOLD REQUIRES REVIEW` trước khi mở két `held-out test`.
- **Làm rõ quan trọng để không làm nghẽn `E01`:**
  > Việc khởi chạy **`P07-E01` KHÔNG yêu cầu** phải hoàn thành trước bộ dữ liệu nhiễu chuyên biệt của `E02`, bộ cặp câu `E03`, bộ mô phỏng tải `E04` (`P08MockScheduler`), hay cơ chế Transactional Outbox / tích hợp `P08` thực tế (`PRE-INTEGRATION REQUIRED`). Sau khi `Gate 3` khóa tập dữ liệu cốt lõi, `E01` có thể chạy ngay lập tức trong khi các phần mở rộng của `E02–E04` được hoàn thiện cuốn chiếu.

---

## 3. Bảng Tra cứu Nhanh Trạng thái 12 Hạng mục Kỹ thuật P07

| # | Hạng mục | Cổng áp dụng | Trạng thái hiện tại | Ghi chú hành động |
| :-: | :--- | :---: | :---: | :--- |
| 1 | Định nghĩa bài toán & 10 Bất biến miền (`INV-P07-01..10`) | `Gate 1–4` | `IN REVIEW` (`v0.1.2`) | Đã làm rõ gom nhóm đa viewer cùng phiên vs cô lập ngữ cảnh cá nhân (`INV-P07-08`). |
| 2 | Sổ đăng ký nguồn, quy tắc ToS/BVDLCN & khử PII cục bộ | `Gate 1–2` | `READY FOR PILOT` | Đã hiệu chỉnh trung thực giới hạn quyền của chủ shop và giả danh hóa. |
| 3 | Cẩm nang `Quick Start — Data Acquisition Pilot` & 4 Templates | `Gate 2` | `READY FOR PILOT` | Đủ 12 mục vận hành để bàn giao ngay cho nhánh dữ liệu thu `50–100` mẫu. |
| 4 | Offline Research Schema (`metadata_availability` & `evaluation_eligibility`) | `Gate 2–3` | `IN REVIEW` (`v0.1.2`) | Giữ được mẫu thực tế khuyết SKU cho `E01` (`NOT_EVALUABLE` ≠ `UNCLEAR`). |
| 5 | Taxonomy 4/9/7 & 6 Quy tắc biên (`Annotation Guideline v0.1.2`) | `Gate 2–3` | `PROPOSED FOR PILOT` | Chạy thử trên `50–100` mẫu Pilot trước khi đóng băng ở mốc `D3`. |
| 6 | Hợp đồng `P07-DOC-02 v0.1.2` (`secondary_intents` + khôi phục `proposal_id`) | `Gate 4` / `E03–E04` | `PROPOSED` | Đã sửa JSON example, thêm `session_epoch`, `knowledge_snapshot_ids` và recovery khi retry. |
| 7 | Tập dữ liệu Pilot (`50–100` bình luận) & Báo cáo chất lượng | `Gate 2 -> 3` | `NOT STARTED` | Bắt đầu ngay sau khi Owner duyệt bản `v0.1.2` này. |
| 8 | Tập dữ liệu chính `v0.1`, `Unseen Product Holdout` & Chia tập `Guarded Union-Find` | `Gate 3 -> 4` | `BLOCKED` | Chờ kết quả Pilot `Gate 2`; bảo toàn 100% chống rò rỉ khi tách `test_unseen_product` và kiểm tra tương quan giả `Product × Intent`. |
| 9 | Công cụ kiểm định dữ liệu (Validator, PII, Kappa, Diagnostics, Spurious Check) | `Gate 2–3` | `NEEDS WORK` | Nhánh kỹ thuật có thể viết song song trong lúc nhánh dữ liệu đi khảo sát nguồn. |
| 10 | Baselines (`B0`, `B1`), 4-Way Preprocessing Ablation (`V0..V3`) & Harness `P07-E01` | `Gate 4` | `NEEDS WORK` | Không mặc định `Product Masking` tốt nhất trước khi đo trên `Seen` vs `Unseen Products`. |
| 11 | Bộ cặp `E03` & `P08MockScheduler` cho `E04` | Sau `E01` (`E03–E04`) | `DEFERRED TO E03/E04` | Không chặn `Gate 1`, `Gate 2`, `Gate 3` hay `Gate 4 (E01)`. |
| 12 | Transactional Outbox & Đối chiếu nội dung đa ý `P06↔P08` | Production Stage | `PRE-INTEGRATION REQUIRED` | Giải quyết khi tích hợp vào `apps/api/`, không chặn nghiên cứu PoC. |
