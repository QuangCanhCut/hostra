# HOSTRA AI — Kiểm toán Responsive & Khả năng Truy cập (Accessibility — M05.1)

## 1. Ma trận kiểm thử Responsive (`320px` → `1920px`)

| Kích thước | Màn hình kiểm thử thực tế | Tràn ngang (`overflowPx`) | Lỗi bố cục / chạm ghi nhận | Đánh giá |
| :--- | :--- | :---: | :--- | :---: |
| **`320×568`** | Viewer Invite Entry (`/live/ses-014`) | `0px` | Không lỗi, 0 nút `<40px`, không cắt chữ | **Đạt** |
| **`360×800`** | Viewer Invite Revoked *(M04)* | `0px` | Hiển thị rõ thông báo thu hồi | **Đạt** |
| **`375×812`** | Viewer Live Room Dark *(M03/M04)* | `0px` | Ô nhập bình luận vừa vặn | **Đạt** |
| **`390×844`** | Rights Consent Portal & Viewer Live Room Dark | `0px` | Nút `Tắt âm thanh` ở Viewer chỉ **`36×36px`** (`<44px`); 2 nút mô phỏng dev (`27px`) chèn giữa màn hình; thiếu `<h1>` ở trạng thái LIVE (`UX-02`, `UX-08`) | **Cần sửa (P1)** |
| **`768×1024`** | Products Catalog & Control Room (cuộn giữa trang) | `0px` | Sidebar `72px` & Control Bar `left=72px` không còn đè Sidebar. Tuy nhiên ở Products có 8 vùng chạm `<40px` (`16px–36px`); ở Control Room thanh sticky che nhẹ dòng bình luận cuối khi cuộn giữa (`UX-11`, `UX-15`) | **Cần sửa (P2)** |
| **`1024×768`** | Session Readiness Blocked | `0px` | **Lỗi rõ rệt (`UX-03`):** Sidebar đang `collapsed` (`72px`) nhưng nút `Mở rộng thanh điều hướng` bật ở `lg:flex` bị ép sát logo `H` còn **`16×32px`** | **Cần sửa (P1)** |
| **`1440×900`** | Auth, Onboarding, Dashboard, Presenter, Knowledge, Story, Control Room, Members, Reports | `0px` | Control Room có 3 tầng chip trên đầu Video; Reports Dark Mode bị viền trắng do sai token CSS & chữ `Đã đo` bị bẻ 2 dòng (`UX-01`, `UX-07`, `UX-09`) | **Cần sửa (P1)** |
| **`1920×1080`** | Session Wizard SKU Picker *(M03/M04)* | `0px` | Hiển thị cân đối nhờ `max-w-[1440px]` | **Đạt** |

---

## 2. Kiểm toán Accessibility (WCAG 2.2 AA)

| Tiêu chí WCAG 2.2 AA | Kết quả thực tế | Chi tiết & Mã vấn đề |
| :--- | :---: | :--- |
| **HTML Semantics (Không lồng interactive)** | **CHƯA ĐẠT (P1)** | 6 trang dùng `<Link><Button>...</Button></Link>` lồng `<button>` trong `<a>`, gây 2 lần dừng phím `Tab` trên cùng 1 nút (`UX-04`). |
| **Cấu trúc tiêu đề (`<h1>`)** | **CHƯA ĐẠT (P1)** | `ViewerLiveRoomPage` khi đã vào phòng LIVE trả về `h1Text: ""` — thiếu thẻ `<h1>` chính của trang (`UX-08`). Các trang còn lại đều có đúng 1 `<h1>`. |
| **Quản lý Focus trong Modal/Drawer** | **CHƯA ĐẠT (P1)** | `Modal.tsx` hỗ trợ đóng bằng `Escape` và có `role="dialog" aria-modal="true"`, nhưng chưa có **focus trap** và chưa **trả focus về nút mở** khi đóng (`UX-05`). |
| **Kích thước vùng chạm (Target Size)** | **CẦN CẢI THIỆN (P2)** | Nút mở rộng Sidebar tại `1024px` chỉ `16×32px` (`UX-03`); nút âm thanh trên Viewer mobile `36×36px` (`UX-08`); nhiều link bảng/nút lọc trên tablet cao `16px–36px` (`UX-15`). |
| **Tương phản & Chỉ báo không phụ thuộc màu** | **ĐẠT CƠ BẢN** | Mọi `StatusBadge` đều có icon + chữ; nút vàng dùng chữ Navy `#0F172A`. Riêng trang Báo cáo Dark Mode cần sửa lỗi token viền trắng chói (`UX-01`). |
| **Giảm chuyển động (`prefers-reduced-motion`)** | **ĐẠT** | Chuyển động tiết chế `150–200ms`, không lạm dụng animation gây chóng mặt. |
| **Lỗi Console & Ảnh hỏng** | **CẦN KIỂM TRA 1 ẢNH** | **0 console errors** trên cả 16 màn hình. Riêng `15-viewer-live-390-dark` ghi nhận `brokenImgs: 1` (cần kiểm tra ảnh avatar/fallback trong `ViewerLiveRoomPage`, `UX-08`). |
