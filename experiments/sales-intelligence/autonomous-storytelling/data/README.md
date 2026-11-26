# Dữ liệu thí nghiệm P06 (`data/`)

**Trạng thái:** `E01-T04 & E01-T09 EXTENDED READY (Synthetic Fixtures)` — Đã giữ nguyên vẹn bộ fixture `e01_*.json` và bổ sung hồ sơ mở rộng `e01_ext_v1_*.json` cho `E01-T09` (chưa có dữ liệu chạy thực tế trên khách hàng thật).

## 1. Nguồn gốc & Phân tách dữ liệu (`synthetic` vs `real`)

- Mọi dữ liệu trong giai đoạn PoC khởi đầu đều bắt buộc gắn nhãn `is_synthetic: true` (hoặc nguồn/quyền cụ thể nếu sau này dùng dữ liệu thật đã ký DPA) và được tham chiếu trong `manifest.json` của từng lần chạy.
- **Tuyên bố miễn trừ trách nhiệm về `OCOP: VERIFIED` mô phỏng:** Toàn bộ mã chứng nhận `SYNTH-OCOP-*` và trạng thái `ocop_status: "VERIFIED"` trong bộ fixture P06 chỉ là **dữ liệu tổng hợp dùng để kiểm thử logic PoC** (`simulated_approval: true`), **KHÔNG phải** chứng nhận OCOP thật từ P09 hay cơ quan nhà nước.
- Phân tách theo thư mục:
  - `products/`: Snapshot thông tin SKU, `ProductFact`, `EvidenceChunk`, `ClaimRegistryEntry`, `EligibilitySnapshot` tương thích trực tiếp với `VersionedKnowledgeStore.from_seed_file(...)` của P05.
  - `merchant_goals/`: Mục tiêu phiên bán hàng, chủ đề bắt buộc (`mandatory_topics`), chủ đề cấm (`prohibited_topics`), thông điệp bắt buộc (`mandatory_messages`).
  - `story_plans/`: `StoryPlan` tham chiếu đã mô phỏng phê duyệt (`APPROVED`) phục vụ đánh giá `P06-E01`.
  - `comments/`: Tập câu hỏi lặp, paraphrase và các tình huống ngắt mạch (`P06-E02`, `P06-E03` — sẽ bổ sung ở các phase sau).
  - `scenarios/`: Kịch bản định tuyến thời gian, mâu thuẫn tài liệu, lỗi model (`P06-E01`..`P06-E04`).
  - `annotations/`: Nhãn chuẩn hoặc phiếu chấm thủ công (`human_eval_rubric_v0.1.md`).

## 2. Danh mục 4 tệp dữ liệu `E01-T04`

| Tệp | Vai trò | Số lượng / Phạm vi | Lưu ý kiểm soát |
| :--- | :--- | :--- | :--- |
| [`products/e01_verified_skus.json`](./products/e01_verified_skus.json) | Bộ 3 SKU thực phẩm đóng gói dương tính (`positive`) cho `P06-E01` | 3 SKU (`SKU-HONEY-01`, `SKU-TEA-02`, `SKU-MACADAMIA-03`), 15 `EvidenceChunk` (5/SKU), `ALLOWED` + `REQUIRES_OFFICIAL_VERIFICATION` + `PROHIBITED` claims | Tất cả 3 SKU đều `OCOP: VERIFIED` mô phỏng, `food_safety_verified: true`, `rights_status: "ACTIVE"`, `approval_status: "APPROVED"`, `tenant_id: "tenant-p06-poc-01"` |
| [`products/e01_negative_skus.json`](./products/e01_negative_skus.json) | Bộ 4 SKU âm tính (`negative`) kiểm thử cơ chế chặn fail-closed của P05 & `P06-E04` | 4 SKU (`SKU-CASHEW-03`, `SKU-COFFEE-EXPIRED-04`, `SKU-GINGER-UNSAFE-05`, `SKU-LOTUS-DRAFT-06`) | Kiểm chứng 4 mã chặn: `OCOP_NOT_VERIFIED`, `RIGHTS_INVALID`, `FOOD_SAFETY_UNVERIFIED`, `UNAPPROVED_FACT` |
| [`merchant_goals/e01_goals.json`](./merchant_goals/e01_goals.json) | 3 kịch bản mục tiêu merchant cho phiên 10 phút & 30 phút | `goal_e01_product_education` (10m), `goal_e01_brand_storytelling` (10m), `goal_e01_sales_presentation` (30m) | Mọi mục tiêu và `expected_mandatory_topic_ids` bám chặt `e01_verified_skus.json` |
| [`story_plans/e01_story_plans.json`](./story_plans/e01_story_plans.json) | 3 `StoryPlan` chuẩn `p06-mock-v0.1` dùng làm fixture tham chiếu đánh giá (đóng băng từ T04) | `product_education_10m`, `brand_storytelling_10m`, `sales_presentation_30m` | Gắn `fixture_role: "reference_evaluation_fixture_not_llm_output"` và `simulated_approval: true`; đạt `is_mvp_live_eligible() is True` |
| [`products/e01_ext_v1_verified_skus.json`](./products/e01_ext_v1_verified_skus.json) | Bộ 3 SKU dương tính mở rộng (`e01_ext_v1`) cho `E01-T09` | 3 SKU tương ứng kèm **30** `EvidenceChunk` (`10`/SKU), `ALLOWED` / `REQUIRES_OFFICIAL_VERIFICATION` / `PROHIBITED` claims | Giữ nguyên `e01_verified_skus.json`; loại bỏ từ khóa dễ nhầm cross-SKU trong single-SKU verification |
| [`merchant_goals/e01_ext_v1_goals.json`](./merchant_goals/e01_ext_v1_goals.json) | 5 mục tiêu phiên mở rộng (`e01_ext_v1`) | `goal_e01_ext_product_education`, `goal_e01_ext_brand_storytelling`, `goal_e01_ext_sales_presentation`, `goal_e01_ext_pilot_short`, `goal_e01_ext_window_stress` | Tách biệt mục tiêu pilot khỏi tập đánh giá chính thức và kịch bản stress `W=5/10/20` |
| [`story_plans/e01_ext_v1_story_plans.json`](./story_plans/e01_ext_v1_story_plans.json) | 5 `StoryPlan` `APPROVED` (`e01_ext_v1`) đạt `is_mvp_live_eligible() == True` | 18t (`product_education_10m_ext`, `brand_storytelling_10m_ext`), 24t (`sales_presentation_30m_ext`, `window_sensitivity_stress_24t`), 6t (`pilot_short_3sku_ext`) | Kết hợp `--min-chunks-per-topic 2` cho phiên dài 36–48 lượt để kiểm tra độ nhạy `W in {5, 10, 20}` |

## 3. Quy tắc đối chiếu với hạt giống P05 (`catalog_seed.json`)

Khi đối chiếu với [`../knowledge-verification/data/catalog_seed.json`](../../knowledge-verification/data/catalog_seed.json):

- Trong `catalog_seed.json` của P05, `SKU-HONEY-01` và `SKU-TEA-02` có `ocop_status: "VERIFIED"`, còn `SKU-CASHEW-03` có `ocop_status: "PENDING"` (`ocop_code: null`).
- **Quy tắc tách bạch cho `P06-E01`:**
  - Luồng chạy **positive 3-SKU** (`e01_verified_skus.json`) bổ sung `SKU-MACADAMIA-03` (*Hạt mắc ca sấy nứt vỏ Lâm Đồng*, `195.000đ`, `500g`, `OCOP: VERIFIED` mô phỏng) và chỉnh quy cách `SKU-TEA-02` sang hộp `200g` (`245.000đ`) theo đặc tả E01.
  - Tuyệt đối **không trộn** `SKU-CASHEW-03` (`PENDING`) hay các SKU lỗi quyền/VSATTP/DRAFT vào `e01_verified_skus.json`; toàn bộ 4 ca âm tính được đặt riêng tại `e01_negative_skus.json`.

## 4. Hướng dẫn nạp & kiểm định bằng Python

```python
from pathlib import Path
import json
from p06.schemas import StoryPlan

data_root = Path("experiments/sales-intelligence/autonomous-storytelling/data")

# 1. Nạp StoryPlan và kiểm định theo schema p06-mock-v0.1
plans_raw = json.loads((data_root / "story_plans/e01_story_plans.json").read_text(encoding="utf-8"))
for key, payload in plans_raw["plans"].items():
    plan = StoryPlan.model_validate(payload)
    assert plan.is_mvp_live_eligible() is True, f"Plan {key} chưa đủ điều kiện live MVP"

# 2. Nạp sản phẩm qua VersionedKnowledgeStore của P05 (chỉ-đọc)
# Tham khảo helper `_load_p05_modules()` trong tests/unit/test_e01_dataset.py
# store = p05_gate.VersionedKnowledgeStore.from_seed_file(data_root / "products/e01_verified_skus.json")
```

## 5. Quy tắc quyền dữ liệu & Bảo mật

- Tuyệt đối không commit chứng nhận OCOP thật, dữ liệu định danh merchant/viewer thật (email, số điện thoại, địa chỉ cá nhân) hoặc tài liệu chưa được cấp quyền lên Git.
- Không sửa hồ sơ mô phỏng để trình bày như chứng cứ thật.
- Nếu sử dụng external LLM API trong các bước thực nghiệm sau, phải kiểm tra quyền gửi dữ liệu và chỉ dùng dữ liệu `is_synthetic: true` hoặc đã hoàn tất DPA/terms review.
