# HOSTRA AI — Báo cáo Kiểm toán UI/UX Tổng thể (M05.1)

## 1. Đánh giá tổng quan độ chín giao diện

Sau 4 milestone (M01–M04), frontend HOSTRA AI đã có **nền tảng kiến trúc và nghiệp vụ rất vững**: tuân thủ tốt bảng màu Navy `#0F172A` / Amber `#F5C430` của **HOSTRA UI Redesign v0.4**, không bị tràn ngang trên cả 8 mức màn hình từ `320px` đến `1920px`, không có lỗi console, và giữ đúng các nguyên tắc an toàn quan trọng (`PAUSE_AI ≠ STOP`, `ACCEPTED ≠ APPLIED`, `OCOP ≠ Knowledge Approved`, hiển thị trung thực `N/A`).

Tuy nhiên, khi nhìn dưới góc độ **người dùng thật không rành kỹ thuật** (chủ hợp tác xã/nhà bán hàng đặc sản OCOP, vận hành viên đang trực phiên live áp lực cao, khách xem trên điện thoại), giao diện hiện tại vẫn mang cảm giác **"bảng quản trị kỹ thuật / bản dựng thử nghiệm"** do 5 nhóm nguyên nhân cốt lõi:

1. **Lộ nhiều nút mô phỏng & thuật ngữ lập trình vào giao diện người dùng cuối:** Nút `Mô phỏng Media suy giảm`, `Mô phỏng xung đột 409`, `Tiến bước phát kế tiếp (Mock ACK)` nằm ngay trong Phòng điều khiển; `Mô phỏng Video Buffering`, `Mô phỏng Mất kết nối bình luận` nằm giữa màn hình Khách xem; các mã tài liệu nội bộ (`SR-D2`, `IM-D3`, `P04`, `P09`, `Time-bucketed SVG`, `Epoch`, `Revision`, `COMMITTED`) xuất hiện dày đặc.
2. **Bùng nổ nhãn trạng thái (Badge Fatigue):** Trang Báo cáo có tới **18 badge màu**, Trang Tổng quan có **15 badge**, Phòng điều khiển có **14 badge** hiển thị cùng lúc — khiến mọi thứ trông đều "cấp bách" như nhau và làm mờ tiêu điểm chính.
3. **Lỗi sai tên biến CSS (Design Token Drift) ở module Báo cáo:** Trang Báo cáo dùng biến chưa định nghĩa (`--border-subtle`, `--surface-base`, `--surface-subtle`, `--radius-md`) khiến Dark Mode xuất hiện các khung viền trắng sắc lẻm lạc tông với phần còn lại của ứng dụng, và nhãn `Đã đo` trong 4 thẻ KPI bị bóp thành 2 dòng hẹp (`Đã` / `đo`).
4. **Một số khiếm khuyết Accessibility & Responsive tinh tế:**
   - Ở màn hình `1024×768`, nút `Mở rộng thanh điều hướng` trên Sidebar bị bóp còn **`16×32px`**.
   - Nhiều trang lồng `<button>` bên trong `<Link>` (`<a>`), gây lặp điểm dừng phím Tab và sai ngữ nghĩa HTML.
   - `Modal.tsx` thiếu focus trap & khôi phục focus khi đóng.
   - Phòng xem khách (`ViewerLiveRoomPage`) khi ở trạng thái LIVE thiếu thẻ `<h1>` ngữ nghĩa và nút `Tắt âm thanh` chỉ `36×36px`.
5. **Mật độ & bố cục lặp lại giữa các module:** Nhiều màn hình chia cột/thẻ giống nhau theo kiểu danh sách card đều nhau, nút `Chuyển SKU` bị lặp 2 lần trong Phòng điều khiển, và thanh `sticky bottom-0` ở màn hình desktop `900px` che phần hộp dự kiến lời thoại khi chưa cuộn hết trang.

---

## 2. Xác minh 8 giả thuyết kiểm toán (H01 → H08)

| Mã | Giả thuyết ban đầu | Kết quả xác minh thực tế | Bằng chứng cụ thể |
| :---: | :--- | :---: | :--- |
| **H01** | Quá nhiều badge trạng thái cùng lúc | **XÁC NHẬN (P1/P2)** | Báo cáo `#013`: **18 badges**; Tổng quan: **15 badges**; Phòng điều khiển: **14 badges** (5 badge trạng thái + 3 nút mô phỏng ngay trên đầu video). |
| **H02** | Lộ thuật ngữ kỹ thuật hướng lập trình viên | **XÁC NHẬN (P1)** | Phòng điều khiển lộ **9 thuật ngữ** (`PlaybackCompleted ACK`, `COMMITTED`, `Epoch`, `Revision`, `Publisher`, `LiveKit`, `Mock ACK`, `409`, `Mô phỏng`); Báo cáo lộ **10 thuật ngữ** (cả `Time-bucketed SVG`, `SR-D2`, `P04`, `P09`). |
| **H03** | Mật độ Phòng điều khiển quá dày | **XÁC NHẬN (P1)** | Trên màn hình `1440×900`, phần đầu trang chiếm tới 3 tầng (Tiêu đề + 4 nút hành động + hộp 5 badge + hàng 3 nút mô phỏng) đẩy khung Video xuống sâu; nút `Chuyển SKU` bị lặp 2 lần. |
| **H04** | Thanh điều khiển ghim đáy đè nội dung/sidebar | **ĐÃ SỬA ĐÈ SIDEBAR, CÒN CHE NHẸ NỘI DUNG KHI CUỘN (P2)** | Bản sửa M04 đã giải quyết triệt để lỗi đè Sidebar ở `768×1024` (`asideRight=72px`, `barLeft=72px`). Tuy nhiên khi cuộn giữa trang (`11-control-room...` và `12-control-room...`), thanh `sticky` vẫn che nửa cuối thẻ `Hoạt động AI` hoặc dòng bình luận cuối viewport. |
| **H05** | Báo cáo quá tải thông tin & lỗi hiển thị | **XÁC NHẬN (P1)** | 4 thẻ KPI bị bóp badge `Đã đo` thành 2 dòng; sai tên biến CSS `--border-subtle` làm viền trắng chói ở Dark Mode; nhãn `Time-bucketed SVG` không có ý nghĩa với người bán hàng. |
| **H06** | Giao diện lặp lại kiểu quản trị chung chung | **XÁC NHẬN (P2)** | Nhiều trang dùng cùng 1 mẫu Header + Card lưới phẳng tương đương nhau; thiếu điểm nhấn thị giác riêng cho vai trò từng trang (ví dụ trang Kiểm tra sẵn sàng dùng 7 thẻ đồng hạng, không nổi bật ngay 2 mục đang chặn lên đầu). |
| **H07** | Khoảng cách & mật độ chưa đồng đều | **XÁC NHẬN (P2)** | Trang `Duyệt tri thức` cao `1839px` (cuộn dài, 16 nút nhỏ `<40px`), trong khi một số nút phụ có kích thước khác nhau (`27px`, `32px`, `34px`, `36px`). |
| **H08** | Nút mô phỏng/debug lộ rõ cho người dùng cuối | **XÁC NHẬN (P1)** | 4 nút mô phỏng nằm thẳng trong `LiveControlRoomPage`, 2 nút mô phỏng nằm ngay giữa `ViewerLiveRoomPage` di động, và `DevScenarioBar` mặc định bật trên mọi trang. |

---

## 3. Đánh giá theo góc nhìn 4 vai trò người dùng thật

### 3.1. Chủ sở hữu (Owner — Nhà bán hàng đặc sản/OCOP)
- **Điểm tốt:** Dễ hiểu quy trình tổng quan nhờ thanh bên tiếng Việt rõ ràng; luồng chọn 2–5 SKU và kiểm tra Readiness giúp tránh phát nhầm sản phẩm chưa đủ hồ sơ OCOP.
- **Điểm gây lúng túng:** Khi vào Kiểm tra sẵn sàng và Báo cáo, chủ shop gặp các từ như `P09 · OCOP Eligibility`, `P04 PlaybackCompleted ACK (deduplicated)`, `SR-D2`, `Time-bucketed SVG`, `Revision v42 · Epoch 3` — tạo cảm giác phức tạp và lo ngại bấm nhầm. Các mục đang **Bị chặn / Đang chờ** ở trang Readiness nằm xen kẽ giữa 5 mục đã Đạt thay vì được gom lên đầu.

### 3.2. Vận hành viên (Operator — Người trực phiên live dưới áp lực thời gian)
- **Điểm tốt:** Phân quyền chặt chẽ (ẩn nút tạo/quản lý thành viên, ẩn xuất file báo cáo, nút `Dừng khẩn cấp` màu đỏ tách riêng dễ nhận biết).
- **Điểm gây áp lực:** Khu vực phía trên Video có quá nhiều chip màu và nút mô phỏng trộn lẫn với trạng thái thật. Nút `Chuyển SKU` xuất hiện ở 2 nơi khác nhau (gây phân vân không biết 2 nút có khác nhau không). Trên máy tính bảng `1024px`, nút mở rộng thanh bên bị bóp còn `16px` rất khó chạm.

### 3.3. Chủ thể quyền hình ảnh (Rights Subject — Người cho phép dùng khuôn mặt/giọng nói)
- **Điểm tốt:** Trang xác nhận quyền (`/rights/consent/:requestId`) rất gọn gàng, sạch sẽ trên điện thoại `390×844` (chỉ 1 badge, không lộ thuật ngữ kỹ thuật, không tràn ngang).
- **Điểm cần bổ sung:** Có nút `Về Studio` ở đầu trang dẫn vào Merchant Studio (không cần thiết và có thể gây bối rối cho người ngoài công ty khi bấm vào chỉ mở màn hình không có quyền); cần làm rõ hơn hướng dẫn cách thu hồi quyền về sau.

### 3.4. Khách xem livestream (Viewer — Khách hàng trên điện thoại)
- **Điểm tốt:** Tách hoàn toàn khỏi giao diện quản trị Merchant, màn hình nhập tên ở `320×568` gọn đẹp, không tràn ngang, phòng chờ khóa chat rõ ràng.
- **Điểm cần cải thiện ngay:** 2 nút `Mô phỏng Video Buffering` và `Mô phỏng Mất kết nối bình luận` nằm ngay giữa màn hình làm hỏng trải nghiệm khách thật; nút bật/tắt tiếng chỉ `36×36px` hơi nhỏ khi dùng 1 tay; trên nền tối khung ảnh sản phẩm nền trắng hơi chói; thiếu thẻ `<h1>` ngữ nghĩa khi đã vào phòng LIVE.

---

## 4. Tóm tắt số lượng vấn đề theo mức độ ưu tiên

- **P0 — Nghiêm trọng (Critical):** **0** *(không có lỗi rò rỉ phân quyền, không đánh đồng `ACCEPTED=APPLIED` hay `PAUSE_AI=STOP`, không có thao tác phá hủy không xác nhận).*
- **P1 — Cao (High):** **8 vấn đề** (lỗi CSS token trang Báo cáo, nút debug lộ thiên trên Control Room & Viewer, nút mở rộng Sidebar `16×32px` tại `1024px`, lồng `<button>` trong `<a>`, thiếu focus trap ở Modal, thuật ngữ kỹ thuật dày đặc, badge `Đã đo` bị vỡ 2 dòng trong KPI Báo cáo, thiếu `<h1>` + `brokenImgs` ở Viewer Room).
- **P2 — Trung bình (Medium):** **10 vấn đề** (quá tải 14–18 badge, lặp nút `Chuyển SKU`, mật độ 3 tầng trên đầu Video Control Room, thanh sticky che dòng cuối khi cuộn giữa, Readiness chưa gom mục chặn lên đầu, touch target `<44px` trên di động, nút `Về Studio` trên cổng Rights Subject, `DevScenarioBar` mặc định nổi, Knowledge Review quá dài, thiếu phân tách thị giác giữa nhóm hành động).
- **P3 — Thấp (Low):** **4 vấn đề** (khung ảnh sản phẩm nền trắng chói ở Dark Mode, nhãn `Time-bucketed SVG`, tiêu đề phụ dài dễ xuống dòng, nút thu gọn sidebar desktop `32×32px`).

**Tổng cộng:** **22 vấn đề có bằng chứng kiểm chứng đầy đủ** (chi tiết trong [ISSUE_REGISTER.md](./ISSUE_REGISTER.md)).
