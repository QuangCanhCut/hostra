# Hiểu và phân luồng bình luận tiếng Việt

[Nhóm nghiên cứu](../README.md) · [Trung tâm experiments](../../README.md)

**Module:** P07 · **Rủi ro:** R04 (chính), R03, R10, R17 · **Gate:** G2, G3, G4 · **Mốc tham chiếu:** M4.

**Trạng thái hiện tại (`26/11/2026`):** `PRE-EXPERIMENT DESIGN IN REVIEW (v0.1.3)` · **Tiến độ chạy thí nghiệm (`E01–E04`):** `NOT STARTED` *(chưa có dữ liệu trong `data/` và chưa có kết quả chạy mô hình)* · **Cổng sẵn sàng:** `Gate 1 (Source Discovery): READY` · `Gate 2 (Data Pilot 50–100): CONDITIONALLY READY` · `Gate 3–4 (Main Dataset / E01): BLOCKED`. **Quyết định công nghệ:** `SELECTED FOR PoC`; mọi ngưỡng chất lượng và phương án tiền xử lý vẫn `PROPOSED / VALIDATION PENDING`.

## Hồ sơ Chuẩn bị Thực nghiệm (`docs/` — `v0.1.3`)

Trước khi thu thập dữ liệu hoặc viết mã huấn luyện, xem bộ 6 tài liệu chuẩn hóa trong `docs/`:

- **Bài toán, ranh giới & 10 bất biến miền:** [p07-problem-and-requirements.md](./docs/p07-problem-and-requirements.md)
- **Hợp đồng tích hợp tối thiểu (`Intake -> P07 -> P08/P09`):** [p07-contract-v0.1.md](./docs/p07-contract-v0.1.md)
- **Intent Taxonomy (`4/9/7`), quy tắc biên & ví dụ chuẩn:** [p07-annotation-guideline-v0.1.md](./docs/p07-annotation-guideline-v0.1.md)
- **Kế hoạch thu thập Real-First & `Quick Start — Data Acquisition Pilot` (`50–100` mẫu):** [p07-data-acquisition-and-annotation-plan-v0.1.md](./docs/p07-data-acquisition-and-annotation-plan-v0.1.md)
- **Giao thức đánh giá, chống rò rỉ, `Unseen Product Holdout` & `E01–E04`:** [p07-dataset-and-evaluation-protocol.md](./docs/p07-dataset-and-evaluation-protocol.md)
- **Đánh giá 4 cổng sẵn sàng (`Gate 1 → Gate 4`):** [p07-experiment-readiness.md](./docs/p07-experiment-readiness.md)

### Cấu trúc thư mục làm việc

- `docs/` — Đặc tả bài toán, hợp đồng `PROPOSED`, hướng dẫn gán nhãn, kế hoạch Pilot & giao thức thí nghiệm.
- `data/{raw,annotations,processed}/` — Dữ liệu đã khử PII / manifest `SHA-256` *(cấm đẩy tệp thô chưa khử PII hoặc dữ liệu đối tác không có quyền chia sẻ lên Git)*.
- `configs/` — Cấu hình khóa tham số cho `P07-E01..E04`.
- `src/{preprocessing,baselines,models,evaluation}/` — Tiền xử lý, baseline (`B0`/`B1`/`G0`), mô hình ứng viên và harness đánh giá.
- `tests/` — Kiểm thử hợp đồng, schema validator và bộ negative tests an toàn.
- `notebooks/` & `results/{metrics,reports}/` — Notebook thực nghiệm, `ExperimentManifest` JSON và báo cáo kết quả.

## 1. Tổng quan bài toán

Bình luận live có tiếng lóng, thiếu dấu, spam và câu hỏi tham chiếu mơ hồ. P07 cần biến chúng thành tác vụ rõ intent/SKU để P08 chọn, tránh trả lời nhầm sản phẩm hoặc để bình luận lặp chiếm hết thời gian kể chuyện.

## 2. Định nghĩa bài toán

- **Đầu vào:** CommentEvent với source, event_id, session_id, viewer_id, timestamp và text; ngữ cảnh phiên được phép sử dụng.
- **Đầu ra:** CommentTask/CommentGroup gồm intent, SKU refs, confidence, priority_hint, TTL và liên kết ngữ cảnh/record gốc.
- **Yêu cầu chức năng, chất lượng và giới hạn:** Chuẩn hóa, dedup, phân loại, resolve SKU và grouping nhưng giữ record của từng viewer. Không chắc SKU thì UNCLEAR. Không coi comment là lệnh hệ thống; không tự kích hoạt mọi job TTS hoặc đổi Active SKU.
- **Phụ thuộc:** P10 nhận/lưu bình luận, P08 quyết định fairness/lịch, P06 trả lời task đã chọn, P09 cung cấp catalog; P11 bảo vệ tenant/session.

## 3. Câu hỏi nghiên cứu

- PhoBERT-base (`vinai/phobert-base`, MIT; cấm `v2` AGPLv3) hay SetFit tốt hơn với 8/16/32 mẫu mỗi lớp và toàn tập `train` trên cùng `Seen-Product` & `Unseen-Product Holdout`?
- Trong 4 biến thể tiền xử lý (`Raw Text`, `Normalized Text`, `Product Entity Masked Text`, `Normalized + Product Masked Text` — `PROPOSED / VALIDATION PENDING`), phương án nào cho `Unseen-Product Macro-F1` và `Generalization Gap` tốt nhất mà không làm mất ngữ cảnh?
- Tiếng lóng, thiếu dấu và danh mục SKU động chưa từng thấy làm ảnh hưởng tới `Intent F1`, `Unseen-Product SKU Resolution Accuracy` và `Wrong-SKU Rate` bao nhiêu?
- Grouping có bảo vệ `product_version_id + knowledge_snapshot_id` và `secondary_intents` (`G0` vs `G1` vs `G2`) giảm tỷ lệ gom sai thuộc tính thế nào, và selective LLM tăng latency/chi phí ra sao?

## 4. Kiến thức nền cần tìm hiểu

- Vietnamese tokenization, fine-tuning và few-shot: so classifier đúng điều kiện dữ liệu.
- Macro F1 và per-class F1: tránh bỏ qua lớp hiếm khi accuracy cao.
- Calibration, abstention, dedup và grouping: phân biệt event trùng với nhiều người hỏi cùng ý.

## 5. Phương pháp và công nghệ

**SELECTED FOR PoC:** rules + Vietnamese NLP classifier + selective LLM; PhoBERT-base và SetFit là hai ứng viên phải benchmark, chưa có bên thắng. Baseline rules + LLM cho tất cả bình luận hợp lệ dễ khởi động nhưng tốn API. Grouping dùng intent/SKU/rules trước; multilingual E5/pgvector chỉ bổ sung khi có bằng chứng cần embeddings. P07 không cần workflow agent nhiều bước.

## 6. Thí nghiệm cần thực hiện

### Chuẩn bị dữ liệu và môi trường

Áp dụng lộ trình **Real-First & Pilot-First** ([kế hoạch chi tiết](./docs/p07-data-acquisition-and-annotation-plan-v0.1.md)): khảo sát đa dạng sản phẩm/merchant (không bó hẹp trong 5 SKU fixture của P05), chạy `Data Acquisition Pilot` `50–100` bình luận trước, kiểm tra tương quan giả `Product × Intent`, giữ nguyên các ràng buộc chống rò rỉ (`Guarded Connected-Component Split` theo `viewer_thread_id`, `participant_id`, `paraphrase_cluster_id`, `template_family_id`, `source_id`) khi tách `test_seen_product` và `test_unseen_product`. Báo cáo tách riêng từng nguồn (`real`, `human_simulated`, `synthetic`). Kaggle/Colab phù hợp train/evaluate classifier; lưu split, seed, revision model và confusion matrix.

Mỗi lượt chạy dùng manifest theo [quy tắc tái lập](../../README.md#5-tái-lập-thí-nghiệm) và khuôn mẫu `ExperimentManifest` trong [giao thức P07](./docs/p07-dataset-and-evaluation-protocol.md). Các giả thuyết dưới đây là cách diễn đạt để kiểm chứng quyết định Stage 03, **không phải kết quả đã đạt**. Chốt baseline, số lượt lặp và tiêu chí trước khi chạy; báo cả lượt lỗi. Mã Pxx-Eyy giữ theo tài liệu nguồn.

### P07-E01 — So sánh classifier độc lập sản phẩm & Ablation tiền xử lý

- **Mục tiêu và giả thuyết:** Một classifier nhỏ (`product-agnostic`, 9 lớp Intent cố định không chứa SKU) có thể giảm chi phí/độ trễ mà giữ chất lượng tổng quát hóa sang sản phẩm mới so với baseline LLM.
- **Đầu vào/tình huống và cách làm:** Cùng `train/dev/test_seen_product/test_unseen_product`, so `PhoBERT-base` / `SetFit` ở `{8, 16, 32, full}` kết hợp ablation 4 biến thể tiền xử lý (`Raw`, `Normalized`, `Product Masked`, `Normalized + Product Masked`).
- **Đầu ra, metrics và evidence:** `Seen-Product Macro-F1`, `Unseen-Product Macro-F1`, `Generalization Gap`, `Per-class F1`, `Moderation FPR`, `P95`, chi phí; lưu split, predictions và confusion matrix.

### P07-E02 — Ngôn ngữ khó & Phân giải SKU động (`Seen` vs `Unseen Products`)

- **Mục tiêu và giả thuyết:** Pipeline chuẩn hóa + `SessionScopedSkuResolver` chạy trên `pinned_catalog` động giữ `Wrong-SKU Rate` tối thiểu ngay cả với thiếu dấu/tiếng lóng, đa SKU và sản phẩm chưa từng thấy lúc train.
- **Đầu vào/tình huống và cách làm:** Chạy `>= 200` trường hợp khó thật/diễn tập/synthetic có nhãn và tách nguồn + lát cắt `seen` vs `unseen product`.
- **Đầu ra, metrics và evidence:** `Intent F1`, `Unseen-Product SKU Resolution Accuracy`, `Wrong-SKU Rate`, `Cross-Viewer Bleed = 0`; lưu lỗi theo nhóm ngôn ngữ.

### P07-E03 — Gom nhóm và từ chối suy đoán

- **Mục tiêu và giả thuyết:** Rules theo SKU hạn chế gom sai; abstention xử lý câu mơ hồ.
- **Đầu vào/tình huống và cách làm:** Thử 100 cặp đồng nghĩa cùng các cặp sai SKU, thay ngưỡng trên dev rồi khóa test.
- **Đầu ra, metrics và evidence:** Grouping precision, bad merge, fallback %; lưu cặp và quyết định.

### P07-E04 — Burst và trùng lặp

- **Mục tiêu và giả thuyết:** Dedup và giới hạn hàng đợi giữ tác vụ hợp lệ dưới tải.
- **Đầu vào/tình huống và cách làm:** Mô phỏng 20–100 raw comment/phút, ID lặp và spam người dùng; nối P08 mock.
- **Đầu ra, metrics và evidence:** Không task trùng, queue P95, fairness; lưu event timeline và task IDs.

## 7. Đánh giá và tiêu chí chấp nhận

G2/G3 đánh giá triage/fairness và tính đúng của task. Không gom mất record viewer khác, không lẫn tenant/session, không đoán SKU mơ hồ. F1, confidence/spam/grouping thresholds còn mở và phải khóa trước test. Khi classifier lỗi dùng rules an toàn/selective LLM có quota, hoặc defer/expire theo TTL; không đoán câu trả lời.

Các metric ở mục 6 đo trực tiếp câu hỏi nghiên cứu, phải báo theo từng nhóm đầu vào/cấu hình thay vì chỉ một số trung bình. Phân biệt **ràng buộc đã xác nhận**, **mục tiêu cần benchmark** và **ngưỡng chưa chốt**. Không tự thêm ngưỡng đạt chất lượng hoặc giá. GO chỉ áp dụng cho phạm vi có evidence và reviewer đồng ý; CHANGE khi cần điều chỉnh phương pháp/cấu hình; NO-GO khi vi phạm hard gate. Nếu chưa đủ bằng chứng, ghi INCONCLUSIVE và việc cần làm tiếp. Không dùng điểm chất lượng để bù vi phạm quyền hoặc tính đúng.

## 8. Kết quả cần bàn giao

- Notebook/script nghiên cứu có hướng dẫn chạy lại, cấu hình và dependency versions; đây là đầu ra cần làm sau, chưa được tạo bởi README.
- Manifest, dữ liệu đầu vào có nguồn/quyền và split hoặc kịch bản kiểm thử; log/metrics theo từng mã thí nghiệm ở mục 6.
- Mẫu đầu ra hợp lệ và ví dụ thất bại, rubric/phiếu chấm nếu có đánh giá người thật; asset riêng tư chỉ lưu tham chiếu có kiểm soát.
- Báo cáo so baseline, giới hạn của Kaggle/Colab hoặc mock so với hệ thống thật, lỗi còn mở và khuyến nghị kỹ thuật.
- Kết luận GO/CHANGE/NO-GO hoặc INCONCLUSIVE, phạm vi kết luận, người phụ trách/reviewer và liên kết evidence. Không tạo kết quả giả để điền báo cáo.

## 9. Tích hợp với HOSTRA

CommentTask chỉ mang priority_hint; P08 sở hữu lịch. Giữ event_id, source, viewer/session, SKU refs và ngữ cảnh khi chuyển sang module conversation. TikTok/Shopee connector không nằm trong bằng chứng private-room PoC.

### Điểm cần xác minh

Nguồn comment thật hợp lệ, taxonomy nhãn, confidence thresholds, quota LLM và bên thắng PhoBERT/SetFit cần quyết định từ số liệu.

## 10. Tài liệu tham khảo

- [Architecture Baseline v1.2](../../../docs/01-solution-architecture/HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx): §6–7; D11, D15, D23; ARD-06, ARD-07.
- [Technical Research & PoC Plan v1.0](../../../docs/03-technical-research/HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx): §4, §5 hồ sơ P07, đặc biệt mục .3/.5/.11–.14; §8–9 về benchmark/evidence, §13–14 về gates và quyết định mở.
- [Technical Risk Assessment v1.1](../../../docs/02-risk-assessment/HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx): các mục R04, R03, R10; đọc failure scenario và evidence cần thiết.

Các liên kết ngoài sau được lấy từ hồ sơ Stage 03; đây là điểm bắt đầu đọc nguyên lý và cách chạy, chưa phải xác nhận license, giá hay khả năng tương thích ở thời điểm thực nghiệm:

- [Paper PhoBERT](https://aclanthology.org/2020.findings-emnlp.92/)
- [Mã nguồn PhoBERT](https://github.com/VinAIResearch/PhoBERT)
- [Paper SetFit](https://arxiv.org/abs/2209.11055)
- [Mã nguồn SetFit](https://github.com/huggingface/setfit)
- [Model card multilingual E5](https://huggingface.co/intfloat/multilingual-e5-small)

## 11. Checklist tiến độ nghiên cứu

- [x] Đọc nguồn Stage 01–04 và hoàn thiện bộ hồ sơ chuẩn bị thực nghiệm `v0.1.3` trong `docs/` *(đang chờ Owner duyệt chốt)*.
- [ ] **Gate 1–2:** Khảo sát nguồn đa dạng sản phẩm (`Source Discovery`), xác minh quyền/ToS và chạy `Data Acquisition Pilot` (`50–100` bình luận) + gán nhãn kép IAA.
- [ ] **Gate 3:** Hiệu chỉnh quy mô sau Pilot, khóa Taxonomy `v0.1`, thu thập tập chính, kiểm tra tương quan giả `Product × Intent` và chia tập chống rò rỉ gồm cả `Unseen Product Holdout`.
- [ ] **Gate 4:** Khóa cấu hình, công cụ tách từ, baseline (`B0`/`B1`), 4 biến thể tiền xử lý và các ngưỡng cần nhóm phê duyệt trước khi mở `held-out test`.
- [ ] Chạy P07-E01, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P07-E02, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P07-E03, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Chạy P07-E04, lưu output/metrics/evidence và ghi cả trường hợp thất bại.
- [ ] Kiểm tra hard gates và đối chiếu dependency/contract với nhóm liên quan.
- [ ] Chạy lại được kết quả, review giới hạn và ghi quyết định có bằng chứng.
