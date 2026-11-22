# HOSTRA AI — Sổ tay Trình diễn Frontend Mock MVP (Demo Runbook)

**Phiên bản:** M05.4 Baseline Candidate  
**Đối tượng sử dụng:** Product Owner, Tech Lead, thành viên nhóm trình diễn nội bộ  
**Lưu ý quan trọng khi giới thiệu:** Luôn nói rõ với người xem rằng đây là **Frontend Mock MVP** (dữ liệu và luồng trạng thái được mô phỏng chuẩn theo thiết kế để kiểm chứng UX/quy trình trước khi tích hợp Backend, AI và LiveKit thật).

---

## 1. Chuẩn bị môi trường trước buổi demo (3 phút)

```powershell
# 1. Di chuyển vào thư mục frontend
cd apps/web

# 2. Cài đặt dependencies (nếu máy sạch)
npm install

# 3. Khởi chạy máy chủ phát triển cục bộ (trên máy demo)
npm run dev
```

Mở trình duyệt tại: `http://localhost:5173/studio?role=OWNER&scenario=happy-path`

### Cấu hình mã QR quét được bằng điện thoại thật qua mạng LAN (Tùy chọn)
Nếu muốn khán giả hoặc điện thoại thật quét mã QR trong mục **Lời mời xem live**:
1. Kết nối máy tính demo và điện thoại vào **cùng một mạng Wi-Fi**.
2. Kiểm tra địa chỉ IP LAN của máy tính (ví dụ `192.168.1.100` bằng lệnh `ipconfig`).
3. Tạo tệp `apps/web/.env.local` với nội dung:
   ```env
   VITE_PUBLIC_APP_URL=http://192.168.1.100:5173
   ```
4. Chạy dev server lắng nghe mạng LAN:
   ```powershell
   npm run dev -- --host
   ```
5. Nếu chỉ demo trên cùng một máy tính, **không cần** đặt `VITE_PUBLIC_APP_URL` — ứng dụng tự động dùng `http://localhost:5173` và có nút **"Mở thử phòng xem khách (Viewer Room)"** ngay bên dưới mã QR.

---

## 2. Bốn kịch bản trình diễn chuẩn (Scenarios A–D)

### Kịch bản A — Tổng quan Chủ sở hữu, Tài khoản & Chuẩn bị Tài sản (4 phút)
1. **Trang Tổng quan (`/studio/dashboard`):**
   - Giới thiệu bố cục ưu tiên hành động (`Action Center`), thẻ `Phiên gần nhất` tách biệt độc lập 3 trục trạng thái (`Đang phát trực tiếp` · `AI đang hoạt động` · `Media ổn định`), và 4 thẻ `Tài nguyên của bạn`.
   - Bấm **Avatar góc trên bên phải** → mở **Account Dropdown Menu** (`PO-D01`) xem thông tin tài khoản, bấm **Thiết lập không gian làm việc** để minh họa lưu nháp linh hoạt.
   - Bật/tắt **Dark Mode** trên Topbar để minh họa bộ giao diện Light/Dark chuẩn HOSTRA v0.4.
2. **AI Presenter & Quyền hình ảnh (`/studio/presenters`):**
   - Chỉ rõ ranh giới: Quyền của Chủ thể hình ảnh (`Rights Consent`) độc lập với duyệt của Chủ shop; Presenter bị thu hồi quyền lập tức bị khóa sử dụng.
3. **Sản phẩm & OCOP + Tri thức (`/studio/products`, `/studio/knowledge`):**
   - Giải thích: Xác minh OCOP độc lập với Chủ sở hữu duyệt Tri thức; thiếu chứng cứ chỉ ở trạng thái `Chờ xác minh`, không tự quy chụp gian lận.

### Kịch bản B — Kiểm tra sẵn sàng & Vận hành Phòng điều khiển Livestream (4 phút)
1. **Kiểm tra sẵn sàng (`/studio/sessions/ses-014/readiness`):**
   - Trình bày 7 cổng kiểm tra (Quyền hình ảnh, Presenter QC, 2–5 SKU, OCOP, Tri thức, Kịch bản, Hạ tầng phát) với nguồn xác minh tiếng Việt rõ ràng.
   - Nhấn mạnh: Chỉ **Chủ sở hữu (Owner)** mới thấy và bấm được nút bắt đầu phiên.
2. **Phòng điều khiển livestream (`/studio/sessions/ses-014/control`):**
   - Minh họa bấm **Tạm dừng AI**: chứng minh `PAUSE_AI` **không dừng livestream** (phiên vẫn `LIVE` ở cảnh sản phẩm an toàn, có nút `Tiếp tục AI`).
   - Minh họa chuyển SKU & xem ngăn kéo **Chẩn đoán** (nơi lưu thông số kỹ thuật chi tiết thay vì bày bừa trên màn hình chính).
   - Minh họa nút **Dừng khẩn cấp** (hộp thoại xác nhận nhanh, nhấn `Escape` để đóng an toàn và trả focus).

### Kịch bản C — Trải nghiệm Khách xem Di động qua Lời mời & Mã QR (3 phút)
1. Mở **Lời mời xem live (`/studio/invites`)**: chọn liên kết `Đối tác phân phối`, hiển thị mã QR và các thông số bất biến sau khi tạo (thời hạn, giới hạn lượt, số khách đang xem).
2. Bấm **"Mở thử phòng xem khách (Viewer Room)"** (hoặc mở tab mới `/live/ses-014?invite=ml014-doitac` và thu nhỏ/bật chế độ di động `375×812`).
3. Nhập tên hiển thị bất kỳ → bấm **Vào phòng livestream**:
   - Chỉ rõ giao diện **chỉ xem & bình luận** (không có thanh điều hướng quản trị, không có nút dừng phiên hay điều khiển AI).
   - Nhập một bình luận sản phẩm → bấm gửi và quan sát trạng thái tiếp nhận bình luận.

### Kịch bản D — Phân quyền Vận hành viên & Báo cáo Trung thực (3 phút)
1. Chuyển sang vai trò **Vận hành viên (Operator)**: bấm Avatar → **Đăng xuất** → chọn **Tiếp tục với vai trò Vận hành viên (Operator)** (hoặc dùng phím tắt `Ctrl+Shift+D` để mở thanh chuyển nhanh `DevScenarioBar`).
2. Minh họa **RBAC**: Vận hành viên không thấy nút `Tạo phiên mới`, không vào được `Thành viên`, `Lời mời xem live` và không xuất được CSV/PDF.
3. Mở **Báo cáo phiên (`/studio/sessions/ses-013/report`)**:
   - Minh họa tính trung thực dữ liệu: chỉ số chưa đủ mẫu hiển thị **`N/A`** kèm lý do rõ ràng (không điền `0` giả); phân biệt rõ lượt AI đã phát xong theo `PlaybackCompleted ACK` với hoàn tất giọng nói TTS.
   - Quay lại vai trò **Owner** trên phiên `ses-014` để bấm thử **Xuất báo cáo (CSV / PDF)** — tệp CSV tự động chống Formula Injection (`=`, `+`, `-`, `@`) và PDF 1.4 tải thật về máy.

---

## 3. Đặt lại trạng thái & Xử lý sự cố khi demo

| Tình huống | Cách xử lý nhanh |
| :--- | :--- |
| Muốn đặt lại toàn bộ dữ liệu mô phỏng về trạng thái ban đầu | Nhấn `Ctrl+Shift+D` mở `DevScenarioBar` → chọn lại kịch bản `Happy Path` hoặc tải lại trang (`F5`). |
| Muốn chuyển nhanh giữa Owner / Operator hoặc kịch bản `Media Degraded` / `Blocked` | Nhấn `Ctrl+Shift+D` (hoặc thêm `?devTools=1` vào URL). Khi thuyết trình xong, nhấn lại `Ctrl+Shift+D` để ẩn thanh công cụ cho giao diện gọn sạch. |
| Khách xem bấm nhầm link đã thu hồi hoặc hết lượt | Màn hình tự động hiển thị thông báo từ chối hợp lệ; quay lại `/studio/invites` để chọn liên kết đang hoạt động (`ml014-doitac`). |
| Điện thoại không quét vào được link `localhost:5173` | Do `localhost` chỉ truy cập được trên chính máy tính chạy server. Xem hướng dẫn cấu hình `VITE_PUBLIC_APP_URL` + `--host` ở Mục 1. |

---

## 4. Các giới hạn của bản Mock Demo cần nêu minh bạch
- Không có luồng video/âm thanh LiveKit thật (sử dụng chân dung tĩnh và mô phỏng trạng thái media).
- Không có đăng nhập OIDC thật (màn hình `/auth/sign-in` chuyển đổi phiên mô phỏng Owner/Operator).
- Không có suy luận AI/LLM/TTS hay xác minh OCOP từ cơ quan chức năng thật.
- Dữ liệu thay đổi chỉ tồn tại trong bộ nhớ trình duyệt (`in-memory mock store`), làm mới trang sẽ quay về bộ dữ liệu mẫu ban đầu.
