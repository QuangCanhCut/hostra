# HOSTRA AI — Hướng dẫn cấu trúc repository và quy trình phát triển

> **Tài liệu dành cho thành viên dự án.** README này giải thích cách cài đặt nhanh cho thành viên mới, vai trò của **toàn bộ** thư mục trong monorepo `hostra-ai/`, đường đi của dữ liệu và quy tắc phối hợp.
>
> **Nguồn tham chiếu:** `HOSTRA_AI_Solution_Architecture_Baseline_v1.2` (16/11/2026), `HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0` (16/11/2026), `HOSTRA_AI_Technical_Risk_Assessment_v1.1` (16/11/2026). Xem `docs/README.md` và `docs/05-implementation/development-guides/ENVIRONMENT_SETUP_AUDIT.md` để tra cứu trạng thái môi trường.

---

## 0. Hướng dẫn Thiết lập Nhanh cho Thành viên Mới (Quick Start)

### Trạng thái triển khai thực tế hiện tại
- **Đã chạy được ngay (Frontend Mock MVP):** `apps/web/` (React + Vite + TypeScript + MSW — đã hoàn thành M01–M05.2).
- **Đã có code PoC chạy độc lập (Python CPU):** `experiments/sales-intelligence/knowledge-verification/` (P05 E01–E04).
- **Chưa triển khai mã nguồn (mới có thư mục khung):** `apps/api/` (`pyproject.toml` đang trống), `workers/*`, các experiment AI Media GPU (`P01`–`P04`).

### Yêu cầu công cụ
- **Git**
- **Node.js ≥ 20 LTS** (khuyến nghị Node 20 theo tệp `.nvmrc`) và **npm** (repository dùng **npm** + `apps/web/package-lock.json`, **không** dùng pnpm/yarn).
- **Python 3.11 – 3.13** *(chỉ cần khi chạy thí nghiệm P05 trong `experiments/`)* và **Docker Desktop** *(chỉ cần khi chạy P05-E02 PostgreSQL/pgvector)*.

### Bước 1 — Clone repository
```powershell
git clone https://github.com/QuangCanhCut/hostra.git hostra-ai
cd hostra-ai
```

### Bước 2 — Cài đặt & chạy Frontend Mock MVP (`apps/web/`)
> **Lưu ý quan trọng:** `package.json` nằm trong `apps/web/`, **không** nằm ở thư mục gốc. Luôn `cd apps/web` trước khi chạy `npm`.

```powershell
cd apps/web
npm ci          # Hoặc `npm install` nếu cập nhật dependency
npm run dev     # Khởi chạy tại http://localhost:5173 (tự kích hoạt MSW mock)
```

- **Mở bảng công cụ mô phỏng (đổi Owner/Operator, kịch bản, reset mock):** Thêm `?devTools=1` vào URL hoặc nhấn phím tắt **`Ctrl + Shift + D`**.

### Bước 3 — Chạy kiểm tra chất lượng Frontend (Typecheck, Lint, Test, Build)
```powershell
cd apps/web
npm run typecheck   # Kiểm tra kiểu TypeScript (tsc -b --noEmit)
npm run lint        # Kiểm tra ESLint
npm run test        # Chạy toàn bộ unit & integration tests (Vitest)
npm run build       # Build production vào apps/web/dist/
npm run test:e2e    # Chạy Playwright E2E (trên Windows mặc định dùng Google Chrome đã cài sẵn)
```

### Bước 4 — Thiết lập môi trường Python cho thí nghiệm P05 (tùy chọn)
Root `pyproject.toml` hiện **chỉ cấu hình đường dẫn cho Pyrefly/Pyright**, chưa quản lý dependency chung. Để chạy PoC `P05` (`experiments/sales-intelligence/knowledge-verification/`), tạo môi trường ảo riêng tại thư mục gốc:

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Cài tối thiểu cho E03 & E04 (thuần CPU, không cần Docker)
pip install pydantic

# Bổ sung cho E01 (Docling extraction + sinh tài liệu mẫu) và E02 (PostgreSQL)
pip install docling python-docx fpdf2 "psycopg[binary]"

# Chạy thử E03 (Publication Gate) & E04 (TOCTOU)
python experiments/sales-intelligence/knowledge-verification/e03_claims_gate/run_e03.py
python experiments/sales-intelligence/knowledge-verification/e04_toctou/run_e04.py
```

*(Linux/macOS thay bước kích hoạt bằng `source .venv/bin/activate`.)*

### Xử lý các lỗi thường gặp trên Windows
1. **`npm error ENOENT: Could not read package.json` ở thư mục gốc:** Bạn đang đứng ở root `hostra-ai/`. Hãy chạy `cd apps/web` trước rồi mới chạy `npm run dev`.
2. **PowerShell báo lỗi không chạy được `Activate.ps1` (`ExecutionPolicy`):** Chạy 1 lần `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` rồi kích hoạt lại `.venv`.
3. **PowerShell 5.1 báo lỗi ký tự `&&`:** PowerShell 5.1 không hỗ trợ `&&`; hãy tách từng dòng lệnh hoặc dùng `;`.
4. **Playwright báo thiếu Chromium khi chạy `npm run test:e2e`:** `playwright.config.ts` mặc định dùng Google Chrome sẵn trên Windows (`channel: 'chrome'`). Nếu máy không cài Chrome, chạy `npx playwright install chromium` và đặt `PW_CHANNEL=` trống.
5. **Cảnh báo `ExperimentalWarning: localStorage is not available` khi chạy Vitest trên Node 25/26:** Chỉ là cảnh báo của Node.js phiên bản mới (test vẫn chạy qua polyfill trong `tests/setup.ts`); dùng **Node 20 LTS** (theo `.nvmrc`) để không gặp cảnh báo này.

---

## 1. HOSTRA đang xây dựng sản phẩm gì?

**HOSTRA AI** hướng tới nền tảng **livestream bán hàng do AI điều phối**. Trong MVP đang được thiết kế:

- Merchant cung cấp **một ảnh chân dung có quyền sử dụng hợp lệ** (và mẫu giọng có consent riêng nếu sử dụng voice clone). Hệ thống tạo thư viện clip người dẫn **trước** phiên live bằng hướng nghiên cứu **PhotoMaker + Wan2.2 Animate**; clip cần được kiểm duyệt/duyệt trước khi phát.
- Merchant nhập dữ liệu sản phẩm và chứng cứ; phạm vi MVP hiện tại là **2–5 SKU thực phẩm đóng gói**, có **OCOP được xác minh hợp lệ** và đáp ứng yêu cầu thực phẩm áp dụng. Các claims phải được kiểm tra trước khi phát ngôn.
- Trong live, AI chủ động kể chuyện bán hàng, xử lý bình luận, tạo lời đáp có căn cứ, tổng hợp giọng nói và lip-sync; hệ thống media duy trì một luồng phát liên tục và có fallback phù hợp.
- Merchant giám sát/điều khiển phiên qua dashboard; người xem được mời tham gia **private live room**. Tích hợp native TikTok/Shopee, nhiều phiên đồng thời và hoạt động 24/7 **chưa thuộc MVP ban đầu**.

**Phân biệt trạng thái:** Yêu cầu/phạm vi đã được quyết định (**CONFIRMED**) ≠ công nghệ đã chọn để chạy thử (**SELECTED FOR PoC**) ≠ khả năng đã được đo và phê duyệt (**VALIDATED**). Các model, GPU/provider, latency 5–10 giây, chất lượng và chi phí chưa được xem là đạt chỉ vì đã có tên trong kiến trúc.

## 2. Sơ đồ tổng thể của repository

```text
hostra-ai/                         # Thư mục gốc trên máy (repo GitHub có thể tên là hostra)
├── apps/
│   ├── web/                       # P10: React/TypeScript — Merchant Studio + Viewer Live Room
│   └── api/                       # FastAPI — ứng dụng backend chính, modular monolith
│       ├── src/hostra_api/
│       │   ├── main.py            # Entry point FastAPI
│       │   ├── modules/
│       │   │   ├── identity/       # Danh tính/đăng nhập/authorization adapter, không sở hữu mọi rights
│       │   │   ├── catalog/        # SKU, catalog, điều kiện sản phẩm và phối hợp P09
│       │   │   ├── knowledge/      # P05: facts, chứng cứ, RAG, claim/publication checks
│       │   │   ├── sales/          # P06: story plan, sales agent, sinh nội dung có kiểm chứng
│       │   │   ├── conversation/   # P07/P08: comment triage, turn scheduling, story resume
│       │   │   ├── sessions/       # P08/P09: session state, commands, active SKU, readiness
│       │   │   └── rights/         # P11: consent, license scope, revoke, rights registry
│       │   └── infrastructure/    # DB, Redis, object storage, model/provider adapters
│       ├── tests/                 # Unit và API/component tests của backend
│       └── pyproject.toml         # Package/dependencies của API
│
├── workers/
│   ├── presenter/                 # P01: tạo presenter + motion clips trước live
│   ├── voice/                     # P02: TTS/voice profile/audio artifact
│   ├── lipsync/                   # P03: audio-driven lip-sync theo deadline
│   └── media/                     # P04: scene/compositor/playout/streaming/ACK
│
├── packages/
│   └── contracts/                 # Schemas và event/API contracts dùng xuyên module
│
├── tests/
│   ├── integration/               # Kiểm tra phối hợp API–worker–event–storage
│   └── e2e/                       # Kiểm tra luồng người dùng / livestream toàn hệ thống
│
├── experiments/                   # Nghiên cứu, benchmark và PoC chưa promote vào production
│   ├── ai-presenter-media/
│   │   ├── presenter-generation/
│   │   ├── voice-tts/
│   │   └── lipsync/
│   ├── sales-intelligence/
│   │   ├── knowledge-verification/
│   │   ├── autonomous-storytelling/
│   │   └── comment-understanding/
│   ├── conversation-orchestration/
│   │   └── scheduling-simulation/
│   ├── realtime-media/
│   │   └── streaming-benchmarks/
│   └── infrastructure-evaluation/
│       ├── gpu-benchmarks/
│       └── reliability-tests/
│
├── configs/                       # Config mẫu, profile workload, policy không nhạy cảm
├── infra/                         # Docker Compose, image build, deploy, hạ tầng
├── docs/                          # Hồ sơ sản phẩm/kiến trúc/rủi ro/research/design/validation
│   ├── README.md                  # Mục lục và cách quản lý phiên bản tài liệu
│   ├── product/
│   ├── 01-solution-architecture/archive/
│   ├── 02-risk-assessment/archive/
│   ├── 03-technical-research/{decisions,archive}/
│   ├── 04-technical-design/{adr,api,data-models,component-designs}/
│   ├── 05-implementation/{roadmap,work-packages,development-guides}/
│   ├── 06-integration/{integration-plans,integration-reports}/
│   └── 07-validation-and-pilot/{test-plans,benchmark-reports,pilot-reports}/
├── scripts/                       # Script tái sử dụng: setup, lint, test, replay, benchmark
├── .github/                       # Workflow CI, templates, CODEOWNERS
├── AGENTS.md                      # Quy tắc và giới hạn dành cho coding agents
├── Makefile                       # Tập lệnh tiện ích (chỉ hoạt động khi có targets thật)
├── .env.example                   # Tên biến môi trường + giá trị mẫu không nhạy cảm
├── .gitignore                     # Loại trừ secrets, cache, output, artifacts lớn
├── README.md                      # File này
└── pyproject.toml                 # Tooling / workspace Python cấp root, nếu áp dụng
```

> Các nhánh `experiments/` và `docs/` được **bổ sung theo thảo luận tổ chức nhóm**. Cây trên là sơ đồ **mục tiêu**; không tạo nhận định rằng mọi thư mục con đang tồn tại hoặc có code chạy. Cú pháp `{a,b}` trong sơ đồ chỉ là cách viết rút gọn, **không phải tên thư mục thật**.

## 3. Ranh giới quan trọng: `apps` / `workers` / `packages` / `experiments` / `docs`

| Khu vực | Câu hỏi nó trả lời | Chứa gì | Không nên chứa gì |
|---|---|---|---|
| `apps/` | Người dùng và backend **tương tác với hệ thống** thế nào? | Web UI, REST/WebSocket, nghiệp vụ và phối hợp phiên | Notebook nghiên cứu tùy hứng; model weights lớn |
| `workers/` | Tác vụ AI/media **thực thi** thế nào? | Adapter/provider, inference orchestration, artifact jobs, media runtime | Logic quyết định quyền phát speech hay tự thay session state |
| `packages/contracts/` | Các thành phần **trao đổi kiểu dữ liệu và sự kiện** gì? | Schema, versioning, examples, validation | Business logic phụ thuộc framework cụ thể |
| `experiments/` | Phương án nào **có bằng chứng** tốt hơn? | Notebook/script PoC, cấu hình thí nghiệm, benchmark, rubric và kết quả nhỏ được phép lưu | API/worker vận hành chính thức; dữ liệu bí mật |
| `docs/` | **Vì sao** thiết kế như vậy và đã xác minh tới đâu? | Baselines, ADR, báo cáo, runbook, acceptance | File output media lớn, logs/datasets thô |
| `infra/` | Deploy và vận hành các phần trên ra sao? | Container/deployment definitions, networks, volumes, observability setup | Credentials thật hoặc policy business trùng lặp |

**Không đồng nhất modular monolith với microservices:** `apps/api/` có các module nghiệp vụ tách ranh giới nhưng giai đoạn đầu có thể deploy trong **một ứng dụng FastAPI**. Worker AI/media có thể chạy process/container riêng vì GPU, codec hoặc thời hạn thực thi khác nhau; không vì vậy mà mọi module phải là một dịch vụ độc lập.

## 4. `apps/web/` — Giao diện người dùng (P10)

**Vai trò:** React + Vite + TypeScript (stack **SELECTED FOR PoC**) dự kiến phục vụ hai trải nghiệm trong cùng web app, phân quyền theo tuyến:

- **Merchant Studio (`/studio`):** quản lý portrait/voice onboarding và consent, preview presenter, sản phẩm/OCOP, dữ liệu và claims đã duyệt, story plan, tạo/điều khiển phiên, dashboard theo dõi sự kiện, latency/fallback.
- **Viewer Live Room (`/live`):** phòng mời riêng, xem stream video/audio và gửi bình luận; áp dụng invite token/permission.

**Cách dùng:** UI gọi `apps/api/` qua REST/WebSocket để đọc state/gửi command; luồng media realtime đi qua giải pháp streaming chuyên dụng (hướng nghiên cứu hiện tại là LiveKit), **không chạy từng frame video qua FastAPI**. UI chỉ hiển thị trạng thái được backend/media xác nhận, không tự quyết định speech nào đã phát.

**Không đặt ở đây:** API key của TTS/LLM, quyền truy cập bucket nội bộ, quyết định kiểm chứng OCOP/claim ở client, secrets hoặc media gốc riêng tư.

## 5. `apps/api/` — Backend chính và các module nghiệp vụ

### 5.1 `src/hostra_api/main.py`

**Điểm khởi động FastAPI**: tạo app, đăng ký routes, middleware, lifecycle/health và dependency wiring. Nên giữ file này mỏng; không nhét toàn bộ nghiệp vụ, state machine hay model inference vào `main.py`.

### 5.2 `modules/` — Ranh giới nghiệp vụ

| Module | Trách nhiệm dự kiến | Phối hợp với |
|---|---|---|
| `identity/` | Liên kết managed OIDC, user/tenant identity, role và authorization guards; xác thực actor khi gọi API | `rights/`, `sessions/`, storage adapters |
| `catalog/` | Catalog/SKU, phiên bản giá, dữ liệu sản phẩm và eligibility; phối hợp **P09** xác minh OCOP/food gating | `knowledge/`, `sessions/`, `rights/` |
| `knowledge/` | **P05**: structured facts, full-text/RAG khi cần, evidence provenance, Claim Registry, verification và Publication Gate | `sales/`, `conversation/`, `catalog/` |
| `sales/` | **P06**: structured Story Plan, generated speech candidates, sales policy, coverage/repetition tracking dựa trên **played** history | `knowledge/`, `conversation/`, `sessions/` |
| `conversation/` | **P07** comment normalize/triage/grouping; **P08** speech turn queue, semantic breakpoint, bounded batch, resume/checkpoint | `sales/`, `sessions/`, `workers/` |
| `sessions/` | **P08/P09**: create/start/pause/resume/stop, active SKU, command revision, readiness, session/speech state ownership | mọi module, `workers/media/` |
| `rights/` | **P11**: consent/provenance/scope cho portrait, voice, motion assets, license expiry/revocation, quyền truy cập tài sản | `identity/`, `catalog/`, `workers/` |

**Lưu ý ownership:** Sơ đồ thư mục **không** có nghĩa `conversation/` và `sessions/` được ghi cùng một trạng thái tùy ý. Theo baseline, **P08/P09 chia sẻ một logical owner cho session/active SKU/command revision**; thiết kế LLD phải xác định người ghi duy nhất, transaction/version và trách nhiệm từng module. Việc OCOP thuộc P09 theo kiến trúc; `catalog/` chỉ là ranh giới mã nguồn được đề xuất, không tự tạo một chủ trạng thái OCOP thứ hai.

### 5.3 `infrastructure/`

Nơi đặt **adapter triển khai**: PostgreSQL/repositories, Redis Streams, S3-compatible object storage, authentication/provider clients, event outbox, telemetry, retry/circuit-breaker support. Mục tiêu là cô lập phụ thuộc bên ngoài khỏi domain logic.

- **PostgreSQL:** system of record cho state/versions/approved facts.
- **Redis Streams:** kênh vận chuyển event trong hướng nghiên cứu hiện tại; event delivery có thể at-least-once nên handler phải idempotent.
- **Object storage:** chứa asset/artifact theo quyền, version và signed URL phù hợp; không biến repo Git thành kho lưu file khách hàng.

### 5.4 `apps/api/tests/` và `apps/api/pyproject.toml`

- `tests/`: test unit nghiệp vụ, authorization, validation, API và mock adapter của **backend**.
- `pyproject.toml`: dependency/runtime/tool cấu hình riêng cho API. Root `pyproject.toml` có thể quản lý tooling chung nhưng không mặc định thay cho dependency app.

## 6. `workers/` — AI và media runtime

Worker nhận **job đã được phân quyền/hợp lệ theo contract**, tạo artifact và trả kết quả. **Không tự publish** lời nói lên stream, không tự xác nhận một turn đã playback, không tự ghi thay session owner.

### `workers/presenter/` — P01, pre-live

- **Input:** portrait có consent, motion reference hợp lệ, style/config, version.
- **Thử nghiệm được chọn:** PhotoMaker + Wan2.2 Animate → presenter still/motion clips; QC identity, body/hand motion, clip seam, rights/license; merchant approval.
- **Output:** Presenter Video Library và manifest (URI, checksum, version, QC, rights); P03/P04 tiêu thụ.
- **Giới hạn:** không sinh full-body motion mới sau **mỗi** comment trong live; không mặc nhiên dùng clip chưa phê duyệt.

### `workers/voice/` — P02, audio generation

- **Input:** `VerifiedSpeechCandidate`, voice profile/consent, style, deadline, version.
- **Thử nghiệm được chọn:** ElevenLabs Flash v2.5 cho tiếng Việt, TTS/voice cloning có quyền.
- **Output:** audio artifact, duration/sample rate, checksum, metadata; P03 dùng lip-sync, P04 có thể dùng audio trên product scene.
- **Hard rule:** quyền dùng ảnh **không** bao gồm quyền clone giọng; không đọc claim hoặc giá chưa được kiểm chứng.

### `workers/lipsync/` — P03, in-live preparation

- **Input:** clip presenter được duyệt + audio + deadline.
- **Thử nghiệm được chọn:** MuseTalk 1.5, preprocessing/cache và deadline-aware render; benchmark GPU/AV sync.
- **Output:** artifact video lip-sync đủ điều kiện hoặc kết quả quá deadline/lỗi để orchestration chọn fallback.
- **Fallback:** nếu không kịp, phát **product scene + verified audio** sau khi kiểm tra quyền và dữ liệu; **không** để mặt host phát khẩu hình sai.

### `workers/media/` — P04, continuous playout

- **Vai trò:** media controller, scene selection, buffer/timeline, compositor/encoder, streaming adapter, output health, playback ACK.
- **Thử nghiệm được chọn:** Python Media Controller + GStreamer + LiveKit Cloud; FFmpeg hỗ trợ chuyển đổi/chuẩn hóa.
- **Bất biến:** một session chỉ một quyền phát âm thanh; `PlaybackStarted`/`PlaybackCompleted` phải dựa trên **media playout thực**, không dựa vào job LLM/TTS/render đã xong.
- **Khi lỗi:** duy trì cảnh an toàn hoặc kết thúc có kiểm soát nếu không có output hợp lệ. Streaming phải tiếp tục ngay cả khi AI inference bị chậm trong giới hạn thiết kế.

> **D29/P12:** Tách logic GPU pre-live của P01 và GPU warm in-live của P03; chạy cùng/tách máy cho GStreamer là **phương án cần benchmark**, chưa khóa GPU/provider.

## 7. `packages/contracts/` — Hợp đồng dữ liệu xuyên module

Lưu các **schema được version hóa** cho yêu cầu, phản hồi, event và artifact metadata giữa API, worker và frontend. Các ví dụ cần chuẩn hóa trong Stage 04:

- `PortraitAsset`, `PresenterIdentity`, `MotionClip`, `VoiceProfile`, `AudioArtifact` và `rights_version`.
- `Product/SKU`, `ApprovedKnowledgeSnapshot`, `ClaimEvidence`, `VerifiedSpeechCandidate`.
- `CommentReceived`, `SpeechTurn`, `StoryPlan`, `StoryCheckpoint`, `SessionCommand` cùng `expected_revision`/`session_epoch` khi cần.
- `PlaybackStarted`, `PlaybackCompleted`, `PlaybackFailed` và status/health events từ P04.

**Quy tắc:** Schema là **single source of truth** khi được chốt; không tự định nghĩa cùng một event theo ba kiểu khác nhau ở web/API/worker. Mọi thay đổi phá vỡ tương thích cần cập nhật version, consumer, migration/test và tài liệu ở `docs/04-technical-design/`.

**Chưa mặc định:** Ngôn ngữ file/schema cụ thể (Pydantic, JSON Schema, OpenAPI, TypeScript generated types...) và cơ chế generate bindings phải được chốt trong LLD; đây không phải cam kết chúng đã tồn tại.

## 8. `tests/` — Kiểm tra ở cấp toàn hệ thống

- `tests/integration/`: API ↔ database/outbox ↔ Redis/worker ↔ media mock; nhiều module cùng tham gia. Kiểm tra duplicate/out-of-order event, stale revision, cross-SKU/cross-tenant, revoke rights, price update sau TTS, retry/fallback.
- `tests/e2e/`: hành trình merchant onboarding → phê duyệt assets/SKU/claims → start private room → viewer comment → trả lời/tiếp tục story → pause/resume/stop → audit. Endurance/latency/fault injection được chạy trong môi trường phù hợp và có evidence.

**Phân cấp:** unit/component test đặt cạnh module (ví dụ `apps/api/tests/`); integration và end-to-end liên thành phần đặt ở root `tests/`. `P13` là chiến lược đánh giá **xuyên tất cả module**, không nhất thiết phải có một service riêng tên P13.

## 9. `experiments/` — Nghiên cứu kỹ thuật và bằng chứng PoC

Chỉ đặt **thử nghiệm có câu hỏi, phương pháp, dữ liệu hợp lệ, metric, kết quả tái lập và kết luận**. Không dùng đây làm nơi chứa mọi file Python chưa biết xếp đâu.

| Thư mục | Bài toán và đối chiếu P | Sản phẩm đầu ra mong đợi |
|---|---|---|
| `ai-presenter-media/presenter-generation/` | **P01:** PhotoMaker/Wan, identity fidelity, motion continuity, license | QC samples có quyền, manifest, GPU/quality comparison |
| `ai-presenter-media/voice-tts/` | **P02:** phát âm tiếng Việt, voice consistency, latency/cost/consent | Bộ câu test, audio evaluation, latency/cost |
| `ai-presenter-media/lipsync/` | **P03:** MuseTalk trên generated clips, face crop, sync/deadline | Chất lượng/VRAM/P50/P95, fallback evidence |
| `sales-intelligence/knowledge-verification/` | **P05:** facts vs retrieval/RAG, claim grounding, stale information, OCOP gate integration | Negative tests, precision/safety evidence |
| `sales-intelligence/autonomous-storytelling/` | **P06:** story planning, LangGraph, resume, repetition/coverage | Story evaluation, human rubric, trace |
| `sales-intelligence/comment-understanding/` | **P07:** rules, PhoBERT vs SetFit, selective LLM; Vietnamese comments | Label set, Macro F1, SKU resolution, latency |
| `conversation-orchestration/scheduling-simulation/` | **P08/P09:** fake-clock FSM, semantic breakpoint, queues, versioned commands | Deterministic replay, invariant/failure results |
| `realtime-media/streaming-benchmarks/` | **P04:** GStreamer/LiveKit, AV sync, scene changes, streaming | Continuity, playback ACK, endurance/latency |
| `infrastructure-evaluation/gpu-benchmarks/` | **P12:** GPU/provider placement, VRAM, throughput, actual bill | Cost/approved clip và cost/live-hour |
| `infrastructure-evaluation/reliability-tests/` | **P12/P13:** network/worker/GPU faults, recovery, health | Fault-injection matrix, alerts/recovery report |

**P09 OCOP eligibility** và **P11 rights/security** không nên bị quên chỉ vì không có thư mục experiment độc lập trong cấu trúc tối thiểu. Phải có negative tests, policy evidence và review ở `apps/api/tests/`, `tests/integration/`, `docs/07-validation-and-pilot/`; có thể mở thêm experiment track khi thật sự cần. **P10 UI** cũng cần usability/acceptance tests nhưng không bắt buộc tạo thư mục nghiên cứu AI riêng.

**Mẫu nội dung của mỗi experiment (đề xuất):** `README.md` nêu RQ/hypothesis → nguồn và quyền dữ liệu → setup/command → baselines → metrics/pass-fail → hardware/versions/seeds → artifacts (link tới storage riêng) → kết quả/limitations → decision (`GO`, `CHANGE`, `NO-GO`, chưa kết luận). Không upload dữ liệu khuôn mặt/giọng khách hàng, key, weights lớn hoặc clip không có quyền lên Git.

**Khi nghiên cứu thành công:** ghi kết luận và bằng chứng ở `docs/03-technical-research/decisions/` hoặc `docs/07-validation-and-pilot/benchmark-reports/`; cập nhật ADR/contract nếu thay kiến trúc; chuyển phần code đã review vào `workers/` hoặc `apps/`, không đơn giản import nguyên notebook research vào production.

## 10. `configs/` — Cấu hình theo môi trường và workload

Chứa file **không nhạy cảm**: profile local/dev/pilot mẫu, feature flags mặc định, policy threshold dự kiến, scene templates, benchmark W0–W3, lint/test/tool settings khi phù hợp.

- Tách **config** khỏi **secret**. `.env.example` chỉ khai báo tên biến và ví dụ an toàn.
- Secret thật dùng môi trường local không commit hoặc secret manager của môi trường triển khai.
- Giá trị policy như TTL comment, deadline, chunk length là **giá trị khởi điểm/PROPOSED** nếu tài liệu chưa xác nhận; không ghi như SLA đã đạt.
- Không đưa quyền sử dụng asset hoặc OCOP status vào config tĩnh để bỏ qua verification.

## 11. `infra/` — Triển khai, quan sát và vận hành

Chứa Dockerfile/Compose, infra definitions, health checks, resources/network/volumes, deploy manifests, logging/metrics/tracing, CI deployment helpers theo quyết định triển khai.

**Môi trường dự kiến:** phát triển local; GPU on-demand cho presenter pre-live; GPU warm cho lip-sync live; managed core và private streaming cho pilot, **placement/provider chưa được khóa**. Ưu tiên khả năng chạy lại benchmark và phân biệt chi phí pre-live với live-hour.

**Không commit:** cloud keys, `.env` thật, private storage URLs còn hiệu lực, datasets/clip người dùng, checkpoint nặng. Hạ tầng không được coi publisher healthy chỉ vì API còn online; cần đo cả media output/viewer-audible khi chạy nghiệm thu.

## 12. `docs/` — Vòng đời tài liệu Stage 01–07

`docs/README.md` là **mục lục và quy tắc quản lý tài liệu chi tiết**; README root này chỉ định hướng cách tìm. Các stage phản ánh **nhóm công việc**, có thể song song và lặp lại, không phải mọi việc phải làm theo chuỗi cứng.

| Vị trí | Chứa gì / dùng khi nào |
|---|---|
| `docs/product/` | Product overview, phạm vi MVP, chân dung merchant, user journey, giả thuyết kinh doanh |
| `docs/01-solution-architecture/` | **Stage 01:** yêu cầu, ranh giới thành phần, luồng xử lý, invariants, decision register |
| `docs/02-risk-assessment/` | **Stage 02:** R01–R18, P0/P1, failure scenarios, evidence và Go/No-Go criteria |
| `docs/03-technical-research/` | **Stage 03:** P01–P13, mô hình/framework được chọn để PoC, experiment plan, trade-offs |
| `docs/03-technical-research/decisions/` | Kết luận nghiên cứu **có dẫn chứng**, không tự biến lựa chọn thành VALIDATED |
| `docs/04-technical-design/adr/` | **Stage 04:** bản ghi lựa chọn kiến trúc, lý do, alternatives, hệ quả và trạng thái |
| `docs/04-technical-design/api/` | REST/WebSocket/event/API behavior, error codes, auth, contract references |
| `docs/04-technical-design/data-models/` | Entity, tables, constraints, migrations, ownership/version semantics |
| `docs/04-technical-design/component-designs/` | FSM, interfaces, concurrency/race, sequence, retry, failure policy theo module |
| `docs/05-implementation/roadmap/` | **Stage 05:** mốc M0–M7/vertical slices, dependencies và exit criteria |
| `docs/05-implementation/work-packages/` | Epic/feature/task, acceptance criteria, owner, liên kết Issues |
| `docs/05-implementation/development-guides/` | Setup, coding/testing convention, local run và onboarding |
| `docs/06-integration/integration-plans/` | **Stage 06:** thứ tự ghép module, mock interfaces, integration gates |
| `docs/06-integration/integration-reports/` | Test run liên module, defect, change log và kết quả sửa |
| `docs/07-validation-and-pilot/test-plans/` | **Stage 07:** G1–G6, W0–W3, negative tests, acceptance procedures |
| `docs/07-validation-and-pilot/benchmark-reports/` | P50/P95 latency, quality, throughput, fallbacks, GPU và cost evidence |
| `docs/07-validation-and-pilot/pilot-reports/` | Merchant feedback, vấn đề tồn tại, quyết định pilot Go/Change/No-Go |
| `archive/` ở từng stage | Phiên bản đã thay thế; không tự tạo file giả để lấp chỗ trống |

### Bộ tài liệu đang có trong ngữ cảnh dự án

| Tài liệu | Vị trí phù hợp | Ghi chú |
|---|---|---|
| `HOSTRA_AI_Project_Overview_Proposal_v1.0.docx` | `docs/product/` | **Cần cập nhật:** còn mô tả host quay footage thật, chưa đồng bộ ACR-001/002 |
| `HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx` | `docs/01-solution-architecture/` | Baseline đã cập nhật Stage 03; công nghệ vẫn chờ kiểm chứng |
| `HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx` | `docs/02-risk-assessment/` | Risk register để team review; rủi ro chưa tự động là MITIGATED |
| `HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx` | `docs/03-technical-research/` | P01–P13 **SELECTED FOR PoC**, không phải validated |

**Versioning:** trong mỗi stage nên có bản hiện hành và `archive/` cho bản cũ; Git history giúp truy vết commit. Với `.docx`, Git không diff nội dung tiện như `.md`, do đó ADR, API/contract và hướng dẫn phát triển thường nên viết Markdown/YAML. Khi có quyết định mới mâu thuẫn bản cũ, ghi rõ **superseded by** và cập nhật liên kết từ mục lục.

## 13. `scripts/`, `.github/` và file gốc

| Mục | Công dụng | Hướng dẫn |
|---|---|---|
| `scripts/` | Chạy setup, lint, unit test, seeds demo, event replay, benchmark, export report | Script cần chạy lặp lại, idempotent nếu có thể, có help/README và không chứa credential |
| `.github/workflows/` | CI: kiểm tra format/lint/test/schema, build theo phạm vi, secret scanning phù hợp | Không tự coi pipeline passing là G1–G6 đã đạt |
| `.github/PULL_REQUEST_TEMPLATE.md` | Checklist PR: scope, ảnh hưởng contract, test/evidence, security, docs | Đề xuất bổ sung file khi team sẵn sàng |
| `.github/CODEOWNERS` | Người review theo vùng mã nguồn | Chỉ điền khi có owner cụ thể, không đoán tên người |
| `AGENTS.md` | Chỉ dẫn cho coding agents: nguồn sự thật, bất biến, nơi thay code, cách test | Không đặt secret/prompt có quyền vượt RBAC; agent không được tự nhận tính năng validated |
| `Makefile` | Shortcut như `make lint`, `make test`, `make dev` | Chỉ tài liệu hóa targets thực sự được triển khai; Windows có thể dùng WSL/Git Bash hoặc script PowerShell tương ứng |
| `.env.example` | Danh sách biến môi trường (placeholder) | Không giá trị thật; không dùng ảnh/chứng cứ riêng tư làm mẫu |
| `.gitignore` | Bỏ qua `.env`, Python/Node cache, `.venv`, build, logs, local test output, large artifacts | Không thay thế việc thu hồi secret nếu đã lỡ commit |
| `pyproject.toml` root | Tooling Python chung như lint/typecheck/test/workspace nếu team áp dụng | Tránh chồng chéo với `apps/api/pyproject.toml` |
| `README.md` root | Bản đồ repo, onboarding, liên kết đến tài liệu chính | Luôn cập nhật khi cấu trúc hoặc contract thay đổi |

## 14. Hai luồng dữ liệu thực tế của HOSTRA

### 14.1 Pre-live: chuẩn bị trước khi phát

```text
Merchant Studio (apps/web)
  ├─ Portrait + rights/consent ──> API rights/identity ──> P01 presenter worker
  │                                             └─> QC / approval / versioned clip library
  ├─ Voice sample + consent ────> rights registry ──────> P02 voice profile
  └─ Product docs / OCOP ───────> catalog + P09 eligibility
                                  └─> P05 facts / evidence / claim registry
                                       └─> P06 draft Story Plan ──> merchant approval

Session readiness: kiểm tra rights + presenter/media + verified OCOP/SKU + knowledge
```

Mọi clip, voice profile và knowledge snapshot phải giữ metadata phiên bản/quyền; không dùng kết quả generator làm bằng chứng quyền hợp lệ. OCOP không được xác minh chỉ bằng logo/hình chụp chứng chỉ hoặc chỉ bởi merchant tự xác nhận.

### 14.2 In-live: trả lời comment mà không đứt luồng phát

```text
Viewer comment (apps/web)
  → API receive / durable comment_id
  → P07 triage, grouping, intent/SKU
  → P08 queue/priority + semantic breakpoint
  → P05 approved facts/evidence
  → P06 candidate answer
  → P05 verification / publication gate
  → P02 voice/audio artifact
  → P03 lip-sync nếu kịp deadline
  → P08 quyết định speech turn hợp lệ / recheck revisions, rights, SKU
  → P04 media playout: HOST_SPEAKING hoặc PRODUCT_SHOWCASE + verified audio
  → playback ACK → P08/P06 cập nhật played history / story checkpoint

Song song: P04 tiếp tục truyền stream, kể cả lúc P05/P06/P02/P03 xử lý.
```

**Nguyên tắc quan trọng:** Comment về SKU B không tự đổi `active_sku` đang là A; không phát chồng hai lời nói; không phát asset bị revoke; không coi job done là played; không tự replay turn khi trạng thái phát chưa rõ. Nếu lip-sync trễ, chuyển cảnh phù hợp **trước** khi phát audio, không đổi host giữa câu tùy tiện.

## 15. Quy tắc phối hợp nhóm và thay đổi code

1. **Trước khi làm việc:** đọc root `README.md`, `docs/README.md`, kiến trúc v1.2, các điều khoản P/risks liên quan; xác nhận mục tiêu và contract của phần mình.
2. **Trước khi sửa API/event:** xác định owner duy nhất, thiết kế input/output, version, authorization, error/fallback; cập nhật `packages/contracts/` cùng test consumer.
3. **Khi làm PoC:** đặt trong `experiments/`, lưu setup/metric/evidence; đừng claim production-ready vì demo đơn lẻ đã chạy.
4. **Khi promote code:** PR sang `apps/`/`workers/`, kèm test, benchmark liên quan và decision/ADR nếu thay thiết kế.
5. **Khi tích hợp:** ưu tiên vertical slices có mock, playback ACK thật hoặc fake-clock đã kiểm soát; test duplication, concurrency, stale versions.
6. **Khi review PR:** xem bảo vệ rights, OCOP/claim, tenant isolation, no-overlap playback; yêu cầu evidence cho phát biểu về latency/quality/cost.
7. **Khi cập nhật docs:** chỉ rõ version, ngày, owner/reviewer, thay thế bản nào, nhãn CONFIRMED/PROPOSED/SELECTED FOR PoC/TO VALIDATE/VALIDATED và link bằng chứng.

### Gợi ý nhánh và commit (quy ước đề xuất)

- Branch: `feature/p07-comment-triage`, `experiment/p03-lipsync-latency`, `docs/stage04-session-fsm`, `fix/p04-playback-ack`.
- Commit: `feat: add comment normalization`, `test: cover duplicate playback events`, `docs: record P03 benchmark decision`.
- Dùng Pull Request và review thay vì đẩy trực tiếp vào `main` khi có nhiều người cùng làm. Thiết lập bảo vệ branch theo quyền GitHub hiện có của nhóm.

## 16. Checklist trước khi gọi một phần là hoàn thành

- [ ] Có owner, phạm vi và interface/contract rõ ràng.
- [ ] Có kiểm thử đúng mức (unit, integration, E2E hoặc benchmark) và tái lập được.
- [ ] Không vi phạm quyền hình/giọng, OCOP eligibility, claims, cross-tenant hoặc publication gate.
- [ ] State ownership, event idempotency, playback ACK và fallback đã được kiểm chứng ở các chỗ liên quan.
- [ ] Có số liệu latency/quality/cost nếu công bố hiệu năng; phân biệt server-side và viewer-audible.
- [ ] Có tài liệu decision, runbook và thay đổi contract liên quan.
- [ ] Trạng thái chuyển sang `VALIDATED` **chỉ khi** reviewer chấp thuận evidence theo acceptance criteria; nếu chưa, vẫn để `SELECTED FOR PoC`/`TO VALIDATE`.

## 17. Bước triển khai trước mắt và cách đọc roadmap

**Theo Stage 03:** M0 kiểm tra code PoC cũ **đang thực sự có gì** (`implemented` / `partial` / `designed only`), chạy test và lập inventory; tiếp theo là các track có thể chạy song song để kiểm chứng presenter + voice/lip-sync, fake media/continuous playout, orchestration, facts/OCOP/rights, và vertical slice comment → verified speech → playback. M1–M7, W0–W3 và G1–G6 được mô tả chi tiết trong Technical Research & PoC Plan; **không suy diễn** timeline hoặc nghiệm thu đã đạt từ cấu trúc repo.

**Ưu tiên ban đầu được đề xuất:**

1. Kiểm kê repo và chốt contract tối thiểu (`M0`) trước khi tái sử dụng code cũ.
2. Chạy P01→P03 smoke test trên clip có quyền; song song P04/P08 fake-clock/fake media để chứng minh continuity và playback semantics.
3. Xây một vertical slice nhỏ: comment → P07 → P05/P06 → P02 → P04 verified audio với product scene → ACK; sau đó mở rộng P03/host scene.
4. Bổ sung merchant Studio, onboarding, OCOP/rights/safety gates, test đầy đủ rồi mới cân nhắc controlled merchant pilot.

---

## 18. Tra cứu nhanh: Tôi cần chỉnh ở đâu?

| Tôi muốn... | Hãy bắt đầu tại... |
|---|---|
| Đổi layout Merchant Studio hoặc Viewer Room | `apps/web/` |
| Thêm endpoint/authorization/business rule | `apps/api/src/hostra_api/modules/` |
| Thay cách tạo presenter hoặc QC motion | `experiments/ai-presenter-media/presenter-generation/` → `workers/presenter/` sau review |
| Benchmark giọng, MuseTalk hoặc streaming | `experiments/ai-presenter-media/`, `experiments/realtime-media/` |
| Thay RAG/claim verification | `experiments/sales-intelligence/knowledge-verification/` + `modules/knowledge/` |
| Thay storytelling/comment classifier | `experiments/sales-intelligence/` + `modules/sales/` / `modules/conversation/` |
| Sửa semantic breakpoint, queue, active SKU | `modules/conversation/`, `modules/sessions/`, `experiments/conversation-orchestration/` |
| Sửa stream/scene/ACK | `workers/media/` + integration tests |
| Thay kiểu event hoặc hợp đồng giữa worker và API | `packages/contracts/` + `docs/04-technical-design/` |
| Tìm lý do chọn model hoặc đánh giá rủi ro | `docs/02-risk-assessment/`, `docs/03-technical-research/` |
| Tìm thiết kế LLD/ADR mới | `docs/04-technical-design/` |
| Tìm kết quả nghiệm thu, pilot và benchmark được review | `docs/07-validation-and-pilot/` |
| Thiết lập local/cloud/CI | `infra/`, `scripts/`, `.github/`, `configs/` |

**Nguyên tắc cuối cùng:** `docs/` cho biết **chúng ta định làm gì, vì sao và bằng chứng nào ủng hộ quyết định**; `experiments/` kiểm tra **liệu phương án có khả thi**; `apps/`, `workers/` và `packages/` chứa **phần triển khai đã được đưa vào codebase**; `tests/` giúp chứng minh **chúng phối hợp đúng**. Đừng để tên folder hoặc trạng thái một issue thay thế kết quả kiểm chứng thực tế.
