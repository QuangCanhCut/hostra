# Notebooks nghiên cứu P06 (`notebooks/`)

**Trạng thái:** `E01 COMPLETED` — Đã hoàn tất và chạy thông [`E01/06_e01_results_analysis.ipynb`](./E01/06_e01_results_analysis.ipynb) + [`E01/e01_analysis_utils.py`](./E01/e01_analysis_utils.py) (`17` code cells, `0` lỗi, không gọi Gemini API) cho `P06-E01`; các notebook của `E02..E04` tách riêng vào `E02/`, `E03/`, `E04/` (đã chuẩn bị `.gitkeep`).

## 1. Quy tắc vệ sinh Notebook (Notebook Hygiene)

- **Chỉ dùng cho khám phá, minh họa và phân tích kết quả:** Toàn bộ logic cốt lõi (`schemas`, `planning`, `agent`, `memory`, `guardrails`, `baselines`, `simulation`) phải nằm trong `src/p06/` và có unit/contract tests trong `tests/`. Notebook chỉ import từ `src/p06/`.
- **Không lưu secrets hoặc dữ liệu nhạy cảm trong output:** Xóa mọi output chứa API key, signed URL, token hoặc asset riêng tư trước khi lưu/commit; không hardcode key trong cell.
- **Ghi rõ giới hạn mock/môi trường:** Nếu chạy với `mock` provider hoặc simulated playback ACK trên CPU/Colab/Kaggle, phải ghi tường minh trong phần mở đầu và báo cáo.

## 2. Quy chuẩn Thư mục Theo Experiment (`<EXPERIMENT_ID>`)

Mọi notebook và script tiện ích phục vụ riêng từng thí nghiệm **bắt buộc** đặt trong thư mục con `notebooks/<EXPERIMENT_ID>/` (`E01/`, `E02/`, `E03/`, `E04/`), đồng bộ với `docs/<EXPERIMENT_ID>/`, `reports/<EXPERIMENT_ID>/`, `reports/tables/<EXPERIMENT_ID>/` và `reports/figures/<EXPERIMENT_ID>/`:

- **`notebooks/E01/` (`COMPLETED`):** [`06_e01_results_analysis.ipynb`](./E01/06_e01_results_analysis.ipynb), [`e01_analysis_utils.py`](./E01/e01_analysis_utils.py).
- **`notebooks/E02/`, `notebooks/E03/`, `notebooks/E04/` (`NOT STARTED`):** Đã chuẩn bị sẵn (`.gitkeep`) cho các pha thực nghiệm kế tiếp (`P06-E04` là nhiệm vụ tiếp theo).
- *(Các notebook thăm dò `00..04` trước kia trong lộ trình khởi tạo đã được thay thế bằng quy trình script/tests tái lập trong `src/p06/` & `experiments/`.)*
