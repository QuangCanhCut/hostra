# Notebooks nghiên cứu P06 (`notebooks/`)

**Trạng thái:** `NOT STARTED` (chưa tạo file `.ipynb`).

## 1. Quy tắc vệ sinh Notebook (Notebook Hygiene)

- **Chỉ dùng cho khám phá, minh họa và phân tích kết quả:** Toàn bộ logic cốt lõi (`schemas`, `planning`, `agent`, `memory`, `guardrails`, `baselines`, `simulation`) phải nằm trong `src/p06/` và có unit/contract tests trong `tests/`. Notebook chỉ import từ `src/p06/`.
- **Không lưu secrets hoặc dữ liệu nhạy cảm trong output:** Xóa mọi output chứa API key, signed URL, token hoặc asset riêng tư trước khi lưu/commit; không hardcode key trong cell.
- **Ghi rõ giới hạn mock/môi trường:** Nếu chạy với `mock` provider hoặc simulated playback ACK trên CPU/Colab/Kaggle, phải ghi tường minh trong phần mở đầu và báo cáo.

## 2. Lộ trình Notebook dự kiến (`NOT STARTED`)

1. `00_llm_api_exploration.ipynb` — Kiểm tra giao diện `LLMProvider`, structured output tiếng Việt và xử lý lỗi/timeout (`TO VALIDATE`).
2. `01_story_planner_exploration.ipynb` — Thử nghiệm `StoryPlan` phân cấp theo 3 SKU và mandatory topics.
3. `02_langgraph_poc.ipynb` — Thử nghiệm luồng LangGraph, semantic breakpoints và bounded rewrite.
4. `03_memory_and_interrupts.ipynb` — Thử nghiệm cửa sổ `played_history_window_chunks` và cơ chế interrupt/resume theo `PlaybackCompleted`.
5. `04_guardrails_and_p05_gate.ipynb` — Kiểm tra tích hợp fail-closed với P05 `PublicationGate` và các ca negative.
6. `05_results_analysis.ipynb` — Tổng hợp bảng số liệu, biểu đồ và phân tích lỗi từ các thư mục `runs/`.
