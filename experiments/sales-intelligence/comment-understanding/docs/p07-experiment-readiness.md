# P07 — Đánh giá Cổng Sẵn sàng Thực nghiệm (Experiment Readiness Gate)

| Thuộc tính | Giá trị |
| :--- | :--- |
| **Mã tài liệu** | `P07-DOC-05` |
| **Phiên bản / Ngày** | `v0.1.1 (Updated Post-Consistency Review)` — `25/11/2026` |
| **Mục tiêu** | Kiểm tra điều kiện tiên quyết trước khi thu thập dữ liệu (`D0–D6`) và trước khi khởi chạy `P07-E01` |
| **Kết luận hiện tại** | **`DATASET PLAN READY FOR REVIEW` · `E01 EXPERIMENT NOT READY YET`** *(Đã đồng bộ 5 tài liệu kỹ thuật & lập kế hoạch thu thập dữ liệu thực tế; chưa có dataset trong `data/` và chờ Owner phê duyệt các quyết định `PROPOSED`)* |
| **Nguồn tham chiếu** | [p07-problem-and-requirements.md](./p07-problem-and-requirements.md), [p07-contract-v0.1.md](./p07-contract-v0.1.md), [p07-annotation-guideline-v0.1.md](./p07-annotation-guideline-v0.1.md), [p07-data-acquisition-and-annotation-plan-v0.1.md](./p07-data-acquisition-and-annotation-plan-v0.1.md), [p07-dataset-and-evaluation-protocol.md](./p07-dataset-and-evaluation-protocol.md) |

---

## 1. Quy ước Trạng thái Cổng Sẵn sàng

- **`READY`**: Đã có tài liệu/quyết định/cấu trúc hoàn chỉnh và kiểm chứng được ngay trong repository.
- **`NEEDS WORK`**: Đã có đặc tả thiết kế `PROPOSED v0.1`, cần thực hiện bước xây dựng dữ liệu, viết harness kiểm thử hoặc nhận phê duyệt của Owner trước khi chạy `E01`.
- **`BLOCKED`**: Đang bị chặn bởi một quyết định/nguồn lực bên ngoài chưa được chốt.
- **`VALIDATION PENDING`**: Bản chất là câu hỏi nghiên cứu phải chờ kết quả chạy thực nghiệm `E01–E04` mới kết luận được (không chặn việc bắt đầu `E01`).

---

## 2. Bảng Kiểm tra 11 Hạng mục Trước khi Bắt đầu `P07-E01`

| # | Hạng mục kiểm tra | Trạng thái | Căn cứ hiện có trong Repository | Việc cần hoàn tất để chuyển sang `READY` |
| :-: | :--- | :---: | :--- | :--- |
| 1 | **Problem Definition & Module Boundaries** | `IN REVIEW` *(Thiết kế hoàn chỉnh)* | Đã đặc tả đầy đủ tại [p07-problem-and-requirements.md](./p07-problem-and-requirements.md), tách rõ khử trùng tại Intake, điều duyệt 4 nhãn tại P07 và quyền sở hữu `ResponseGroup` tại `P08/P09`. | Xác nhận của Owner đối với phạm vi P07 (giữ cố định 10 bất biến miền `INV-P07-01..10`). |
| 2 | **Input/Output Semantics & Ownership Alignment** | `NEEDS WORK` *(Chờ duyệt `PROPOSED v0.1`)* | Đã đồng bộ tại [p07-contract-v0.1.md](./p07-contract-v0.1.md): loại bỏ `DUPLICATE_EVENT` khỏi `moderation_status`, dùng `is_idempotent_replay` cho retry cùng `comment_id`, tách `ResponseGroupProposal` (P07) khỏi `AuthoritativeResponseGroup` (`P08/P09` quản lý `QUEUED -> COMMITTED -> PLAYING -> ANSWERED`). | Owner duyệt hợp đồng `PROPOSED v0.1` trước khi hiện thực hóa `src/schemas.py`. |
| 3 | **Intent Taxonomy v0.1 (9 lớp + 4 nhãn Moderation + 7 SKU modes)** | `NEEDS WORK` *(Chờ duyệt & Pilot IAA)* | Đã chuẩn hóa 100% quy tắc `null` và gold examples tại [p07-annotation-guideline-v0.1.md](./p07-annotation-guideline-v0.1.md), phân biệt rạch ròi `UNCLEAR_OR_OTHER` (Intent) và `OUT_OF_CATALOG` (SKU Grounding). | Duyệt bản `PROPOSED v0.1`, chạy Pilot gán nhãn `50–100` mẫu (`D2`) rồi mới khóa cứng (`D3`). |
| 4 | **Annotation Guideline & Acquisition SOP** | `NEEDS WORK` *(Kế hoạch đã có, chưa chạy Pilot)* | Đã ban hành quy trình vận hành thu thập 10 bước, schema thô và SOP gán nhãn chi tiết tại [p07-data-acquisition-and-annotation-plan-v0.1.md](./p07-data-acquisition-and-annotation-plan-v0.1.md). | Thực hiện thu thập lô dữ liệu đầu tiên (`D1`) và chạy Pilot IAA 2 người gán nhãn độc lập (`D2`). |
| 5 | **Dataset v0.1 & Connected-Component Anti-Leakage Splits** | `BLOCKED` *(Chưa thu thập dữ liệu)* | Thư mục `data/{raw,annotations,processed}/` hiện có **`0` mẫu bình luận P07**. Thuật toán chống leak theo thành phần liên thông (`Union-Find` trên `paraphrase_cluster_id`, `viewer_thread_id`, `near_dup_cluster_id`) đã đặc tả tại [p07-dataset-and-evaluation-protocol.md](./p07-dataset-and-evaluation-protocol.md). | Hoàn tất các mốc `D0 -> D6` theo kế hoạch thu thập dữ liệu: thu thập nguồn `real_permissioned` / `human_simulated_live` (+ `synthetic` bổ trợ có kiểm soát), gán nhãn, kiểm tra `0` leak và xuất `dataset_manifest.json` (`SHA-256`). |
| 6 | **Evaluation Metrics & Pre-registered Thresholds** | `NEEDS WORK` | Đã định nghĩa trọn bộ chỉ số (`Macro-F1`, `Wrong-SKU Rate`, `Cross-SKU Bad Merge Rate`, `Subtopic Bad Merge Rate`, `P50/P95 ms`, `Cost`) và quy tắc báo cáo tách riêng từng nguồn (`real` vs `human_simulated` vs `synthetic`). | Hard Gates (`0` leak/bad-merge/provenance-loss/post-committed-merge) đã rõ; các ngưỡng `THRESHOLD REQUIRES REVIEW` cần chốt trước khi mở `held-out test`. |
| 7 | **Baselines (`B0` Rules, `B1` LLM, `G0` Coarse Grouping)** | `NEEDS WORK` | Thư mục `src/baselines/` đang trống; đã làm rõ `G0` (`intent + SKU + version`) chỉ là baseline đối chứng cho `E03`, chưa phải giải pháp gom nhóm đã chứng minh. | Cài đặt `B0`, `G0` trên CPU và thống nhất LLM API/model dùng cho nhánh đối chứng `B1`/`H1` (`VALIDATION PENDING`). |
| 8 | **Experiment Configurations (`E01–E04`)** | `NEEDS WORK` | Đã đặc tả đầy đủ biến kiểm soát, few-shot `8/16/32` × 3 seeds (`42, 100, 2026`), giấy phép `vinai/phobert-base` (MIT) vs `SetFit` tại [p07-dataset-and-evaluation-protocol.md](./p07-dataset-and-evaluation-protocol.md); `configs/` còn trống. | Tạo các tệp cấu hình khóa tham số trong `configs/` sau mốc `D6`. |
| 9 | **Reproducibility & Environment Setup** | `NEEDS WORK` | Đã chuẩn hóa schema `ExperimentManifest`; chưa khóa phiên bản gói NLP và công cụ tách từ tiếng Việt cho `PhoBERT-base`. | Chốt bộ tách từ giấy phép sạch (khuyến nghị `pyvi` MIT) và môi trường chạy trước `E01`. |
| 10 | **Safety & Negative Test Suite** | `NEEDS WORK` | Đã xác định đầy đủ các ca âm tính (cross-tenant, cross-viewer bleed, ambiguous SKU, out-of-catalog, cross-SKU/subtopic merge, post-committed merge, retry dedup vs spam flood, prompt injection); `tests/` đang trống. | Viết bộ `pytest` kiểm tra hợp đồng, validator schema dữ liệu và negative tests trước khi chạy benchmark. |
| 11 | **Integration Assumptions với P08/P09** | `IN REVIEW` *(Thiết kế thí nghiệm đã đồng bộ)* | Đã thống nhất P07 chỉ phát `ResponseGroupProposal`, còn `P08/P09` độc quyền quản lý `ResponseGroup` (`QUEUED -> COMMITTED -> PLAYING -> ANSWERED` chỉ sau `PlaybackCompleted` ACK). | Hiện thực `P08MockScheduler` tuân thủ đúng vòng đời trên khi chạy `P07-E04`. |

---

## 3. Kết luận Sẵn sàng (Readiness Verdict) & Lộ trình Mở khóa `P07-E01`

### Phán quyết hiện tại:
- **Mức sẵn sàng cho Kế hoạch Thu thập & Gán nhãn Dữ liệu (`D0`):** **`PLANNING-COMPLETE / IN REVIEW`** — Đã có đầy đủ SOP thu thập, quy tắc pháp lý/PII, schema dữ liệu thô, kịch bản diễn tập `human_simulated_live` và SOP gán nhãn tại [p07-data-acquisition-and-annotation-plan-v0.1.md](./p07-data-acquisition-and-annotation-plan-v0.1.md) để bạn duyệt và bắt đầu `D0/D1`.
- **Mức sẵn sàng để chạy Huấn luyện/Benchmark `P07-E01`:** **`NOT READY TO RUN E01 YET` (`BLOCKED` bởi dữ liệu chưa thu thập `D0–D6` và mã cơ sở chưa viết)**.

### Ba điều kiện bắt buộc để mở khóa `P07-E01`
1. **Blocker A1 — Phê duyệt Hồ sơ Thiết kế & Kế hoạch Dữ liệu `v0.1`:** Bạn review và chốt các lựa chọn `PROPOSED` (nguồn dữ liệu ưu tiên ở `D0`, bộ 9 lớp Intent, chỉ tiêu số lượng mẫu và công cụ gán nhãn).
2. **Blocker A2 — Thực thi Lộ trình Dữ liệu `D0 -> D6`:** Thu thập dữ liệu có quyền sử dụng/đồng ý hợp lệ, khử PII, chạy Pilot gán nhãn `50–100` mẫu (`D2`), khóa taxonomy (`D3`), hoàn tất gán nhãn chính thức (`D4`), và chạy chia tập chống rò rỉ theo thành phần liên thông (`D5–D6`).
3. **Blocker A3 — Xây dựng Harness Kiểm thử & Baseline trên CPU:** Hiện thực schema validator, kiểm toán chống rò rỉ dữ liệu, bộ chuẩn hóa/phân giải SKU, baseline `B0` và chốt công cụ tách từ tiếng Việt (`pyvi` MIT) cùng LLM adapter cho `B1`/`H1`.

### Các việc có thể làm song song ngay sau khi chốt `D0`
- **Nhánh Dữ liệu (`D1 -> D4`):** Liên hệ xin phép nguồn thực tế (`Source A`) song song với việc tổ chức các phiên diễn tập nội bộ 5 SKU (`Source B`) và gán nhãn Pilot.
- **Nhánh Công cụ Kiểm định Dữ liệu (Không cần model ML):** Viết trước script kiểm tra schema JSONL, khử PII bán tự động, tính Cohen's `κ` và thuật toán `Union-Find` chia split chống rò rỉ để dùng ngay ở các mốc `D2` và `D5`.
