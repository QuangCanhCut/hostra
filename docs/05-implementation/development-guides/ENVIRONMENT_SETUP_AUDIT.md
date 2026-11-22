# HOSTRA AI — Báo cáo Kiểm toán Môi trường Phát triển & Thiết lập Repository

- **Ngày kiểm toán:** 22/11/2026
- **Nhánh Git:** `feat/frontend-foundation`
- **Phạm vi:** Kiểm tra toàn bộ cấu hình gói, lockfile, phiên bản Node.js/Python, `.env.example`, `.gitignore`, `Makefile`, `pyproject.toml`, `apps/web/`, `apps/api/` và các thí nghiệm trong `experiments/`.

---

## 1. Hiện trạng Repository & Công cụ đo thực tế

| Thành phần | Hiện trạng thực tế | Đánh giá |
| :--- | :--- | :--- |
| **Package Manager Frontend** | **`npm`** (`apps/web/package.json` + `apps/web/package-lock.json` đồng bộ; không dùng pnpm/yarn) | **Ổn định — Giữ nguyên `npm`** |
| **Phiên bản Node.js / npm trên máy** | Node `v26.4.0` · npm `11.17.0` · Chưa có `.nvmrc` trước đợt audit | Đã bổ sung `.nvmrc` = `20` (Node 20 LTS) để chuẩn hóa máy sạch & tránh cảnh báo `localStorage` của Node 25/26 |
| **Phiên bản Python** | Python `3.13.2` (không có `uv.lock`) | Khuyến nghị Python `3.11–3.13` cho CPU PoC; lưu ý các model GPU tương lai (MuseTalk/Wan2.2) thường yêu cầu Python `3.10–3.11` + CUDA riêng |
| **Root `pyproject.toml`** | Chỉ có 13 dòng cấu hình `search-path` cho **Pyrefly** và `extraPaths` cho **Pyright** | **KHÔNG quản lý Python dependencies** (không có `[project]` hay `dependencies`) |
| **`apps/api/pyproject.toml`** | Tệp trống (`0 bytes`) | Backend FastAPI chưa triển khai |
| **`.env.example`** | Trước đợt audit là tệp trống (`0 bytes`) | **Đã chuẩn hóa** với đầy đủ tên biến mẫu an toàn cho Frontend, P05 PoC và Backend placeholder |
| **`Makefile`** | Tệp trống (`0 bytes`) | Chưa cần thêm targets giả khi backend/workers chưa tồn tại |
| **`.gitignore`** | Đã loại trừ `.env`, `.venv`, `node_modules/`, `apps/web/dist/`, `apps/web/test-artifacts/`, `playwright-report/`, `*.tsbuildinfo` | **Đạt chuẩn an toàn** (không commit secrets hoặc `node_modules`) |

---

## 2. Phân tích AI Experiments & Chiến lược Quản lý Môi trường Python (Đề xuất chờ duyệt)

### 2.1. Thực trạng mã nguồn PoC hiện có
Chỉ duy nhất **`experiments/sales-intelligence/knowledge-verification/` (P05)** hiện đã có code Python chạy thực tế (`E01`–`E04`), với các thư viện đã xác định từ `import` thực tế:
- **Dùng chung (`schemas.py`, E03, E04):** `pydantic`
- **E01 (`e01_extraction/`):** `docling`, `python-docx`, `fpdf2`
- **E02 (`e02_retrieval/`):** `psycopg[binary]` + dịch vụ PostgreSQL/pgvector (`docker-compose.yml`)

Các thư mục `experiments/ai-presenter-media/` (P01, P02, P03), `experiments/realtime-media/` (P04), `workers/*` và `apps/api/` hiện mới là khung tài liệu (`.gitkeep` + `README.md`).

### 2.2. Đề xuất chiến lược môi trường Python (KHÔNG tự áp đặt trước khi PO/Tech Lead duyệt)
1. **KHÔNG gom chung 1 môi trường Python khổng lồ cho toàn repo**, vì các worker AI GPU (`PhotoMaker`, `Wan2.2 Animate`, `MuseTalk 1.5` cần PyTorch/CUDA/FFmpeg/GStreamer riêng) sẽ xung đột nặng với backend CPU (`FastAPI`, `Docling`, `Pydantic`).
2. **Đề xuất tách thành 3 nhóm môi trường độc lập khi bắt đầu giai đoạn Backend & GPU PoC:**
   - **Nhóm 1 — Backend API (`apps/api/pyproject.toml` + `uv.lock`):** Quản lý bằng `uv` cho FastAPI, SQLAlchemy/psycopg, Redis, Pydantic.
   - **Nhóm 2 — CPU Experiments (`experiments/sales-intelligence/*/pyproject.toml`):** Mỗi track PoC có `pyproject.toml` riêng tối giản (trước mắt có thể bổ sung cho `P05` khi chốt vòng 2 dữ liệu thật).
   - **Nhóm 3 — GPU Media Workers (`workers/{presenter,lipsync,media}`):** Tách môi trường/Dockerfile CUDA độc lập theo từng model AI.
3. **Không cần duy trì song song `requirements.txt` và `pyproject.toml`:** Khi chính thức áp dụng `uv + pyproject.toml`, giữ `pyproject.toml` + `uv.lock` làm nguồn duy nhất để tránh trùng lặp.

---

## 3. Danh sách tệp đã chỉnh sửa / bổ sung trong đợt kiểm toán này

1. [`.nvmrc`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/.nvmrc) *(mới)* — Ghim phiên bản khuyến nghị Node.js `20` (LTS).
2. [`.env.example`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/.env.example) *(cập nhật từ tệp 0 bytes)* — Khai báo đầy đủ biến môi trường mẫu không nhạy cảm cho Frontend, P05 PoC và Backend tương lai.
3. [`README.md`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/README.md) *(cập nhật)* — Bổ sung mục **0. Hướng dẫn Thiết lập Nhanh cho Thành viên Mới (Quick Start)** gồm clone, cài đặt, chạy Frontend Mock MVP, chạy kiểm thử, setup Python P05 và 5 lỗi thường gặp trên Windows.
4. [`docs/05-implementation/development-guides/ENVIRONMENT_SETUP_AUDIT.md`](file:///g:/PTIT%20TL/P_Inovation/hostra-ai/docs/05-implementation/development-guides/ENVIRONMENT_SETUP_AUDIT.md) *(mới)* — Báo cáo kiểm toán này.

---

## 4. Kết quả kiểm chứng & Những bước chưa thể xác minh trên máy hiện tại

### Đã kiểm chứng trực tiếp (PASS)
- `apps/web/package.json` và `apps/web/package-lock.json` đồng bộ; `npm run typecheck`, `npm run lint`, `npm run test` (27/27 tests), `npm run build` đều **PASS** (đã xác minh ở M05.2 ngay trước audit, và không sửa file nào trong `apps/web/`).
- Kiểm chứng `git status` xác nhận không phát sinh xung đột với công việc M05.2.

### Chưa thể xác minh trong phiên sandbox hiện tại
- **`npm ci` từ mạng sạch trên máy mới:** Môi trường sandbox không bật mạng công cộng ra npm registry nên chưa chạy lại `npm ci` từ đầu tải package mới (tuy nhiên `package-lock.json` đã được sinh từ lần `npm install` hợp lệ gần nhất và tương thích với `package.json`).
- **Chạy lại `P05-E02` với Docker PostgreSQL:** Không khởi chạy Docker daemon trong phạm vi audit này; chỉ xác minh mã nguồn và danh sách import của `P05`.
