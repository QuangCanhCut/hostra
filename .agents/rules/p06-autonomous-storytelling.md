---
trigger: model_decision
description: "Activate ONLY when working on HOSTRA AI Module P06 (Sales Intelligence & Autonomous Storytelling) or reading/modifying files under experiments/sales-intelligence/autonomous-storytelling/. Do NOT activate for P05, P07, backend, or frontend tasks."
---

# Quy tắc Phạm vi P06 (`autonomous-storytelling`)

Trước khi lập kế hoạch hoặc sửa tệp trong `experiments/sales-intelligence/autonomous-storytelling/`, hãy đọc `experiments/sales-intelligence/autonomous-storytelling/AGENTS.md` và `experiments/sales-intelligence/autonomous-storytelling/README.md` (cùng `docs/01-p06-structure-and-mission-guide.md` khi mới nhận việc).

## Ràng buộc cứng
1. **Phạm vi:** Chỉ sửa trong `experiments/sales-intelligence/autonomous-storytelling/`; không đụng P05, P07, `packages/contracts/`, `apps/` hay rule gốc nếu không được giao rõ ràng.
2. **Tách trạng thái:** `Generated (LLM draft) != Verified (P05 PublicationGate) != Played (P04 PlaybackCompleted ACK)`.
3. **Bất biến:** Không tự duyệt claims/OCOP hoặc tự đổi `active_sku` từ LangGraph (`I-04`).
4. **Provider 3 tầng:** `Mock` (unit tests — không dùng làm bằng chứng chất lượng), `Ollama CPU` (smoke test cục bộ — không gộp với Gemini hay suy diễn latency production), `Gemini Flash/Flash-Lite` (thí nghiệm chính thức — chỉ dùng dữ liệu synthetic/được duyệt; xác minh `model_id`, quota, pricing, DPA trước).
5. **Liêm chính:** Không bịa metrics hoặc gắn nhãn `VALIDATED` cho hạng mục `TO VALIDATE`.
