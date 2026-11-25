# HOSTRA AI — Frontend Mock MVP Demo Guide (Milestone 04)

Hướng dẫn dành cho **Product Owner / Reviewer** tự chạy ứng dụng trên máy cá nhân và trải nghiệm xuyên suốt toàn bộ 16 bước từ chuẩn bị tài sản (M01–M02) đến vận hành livestream, xem trên di động và báo cáo hậu kiểm (M03–M04).

---

## 1. Cài đặt & Khởi chạy trên Localhost

Yêu cầu: **Node.js ≥ 20** và **npm**.

```powershell
# 1. Đi vào thư mục frontend
cd apps/web

# 2. Cài đặt dependencies (chỉ cần chạy lần đầu)
npm install

# 3. Khởi chạy dev server (tự động kích hoạt MSW Mock Service Worker)
npm run dev
```

Mở trình duyệt tại đường dẫn Vite in ra (mặc định `http://localhost:5173`).

---

## 2. Công cụ chuyển đổi vai trò, kịch bản & Reset dữ liệu Mock

Ở góc dưới bên phải màn hình có thanh công cụ **`Mock: Owner / Operator`** (`DevScenarioBar`):
- **Đổi vai trò nhanh:** Chuyển giữa **Chủ sở hữu (`OWNER`)** và **Vận hành viên (`OPERATOR`)** (hoặc gắn query `?role=OWNER` / `?role=OPERATOR`).
- **Đổi kịch bản (Scenario):** `happy-path`, `empty`, `media-degraded`, `invite-expired`, `report-partial`, `conflict-409`.
- **Reset dữ liệu Mock:** Bấm nút **Reset Mock** trên DevScenarioBar để khôi phục toàn bộ dữ liệu về trạng thái ban đầu.
- **Ẩn thanh DevBar khi chụp màn hình:** Thêm `&hideDevBar=1` vào URL.
- **Chuyển Light / Dark Mode:** Bấm biểu tượng Mặt trăng / Mặt trời trên Topbar (hoặc thêm `&theme=dark` / `&theme=light`).

---

## 3. Kịch bản Demo 16 bước xuyên suốt (M01 → M03)

1. **Dashboard tổng quan (`/studio/dashboard`):** Đăng nhập mặc định vai trò `Owner`, xem Action Center, Phiên nổi bật (`Phiên #014`), 4 thẻ tài sản đồng bộ số lượng.
2. **AI Presenter Studio (`/studio/presenters`):** Xem thư viện 3 AI Presenter (`Linh`, `Mai`, `An`), mở chi tiết `Linh` để xem so sánh `Bản A · v1` / `Bản B · v2` và tạo mới qua Wizard 4 bước (3 phong cách).
3. **Rights Subject Consent (`/rights/consent/req-consent-an-03`):** Mở cổng xác nhận quyền hình ảnh độc lập cho `An` và thử Xác nhận / Từ chối.
4. **Products & OCOP (`/studio/products`):** Xem `ML-001`, `ML-002`, `ML-004` (`OCOP đã xác minh`) và `ML-003` (`Chờ xác minh OCOP` dù Knowledge đã `APPROVED`).
5. **Knowledge & Claims (`/studio/knowledge/sku-ml-001`):** Kiểm tra màn hình duyệt 2 cột (tài liệu gốc bên trái / 5 nhóm Facts & Claims bên phải) và cảnh báo chặn claim chữa bệnh.
6. **Tạo phiên & chọn 2–5 SKU (`/studio/sessions/new`):** Kiểm tra `Kho sản phẩm (5 SKU)` tải đầy đủ, sắp xếp thứ tự SKU bằng nút lên/xuống hoặc kéo-thả, lưu bản nháp.
7. **Story Planner & Trợ lý AI (`/studio/sessions/ses-015/story`):** Gửi yêu cầu sửa kịch bản, xem Before/After Diff và cơ chế duyệt revision bởi Chủ sở hữu.
8. **Session Readiness Gate (`/studio/sessions/ses-015/readiness`):** Xem các cổng chặn (OCOP / Story chưa duyệt). Chuyển vai trò sang `OPERATOR` để xác nhận nút `Bắt đầu livestream` bị ẩn.
9. **Thành viên & Phân quyền N:N (`/studio/members`):** Xem `Trần Ngọc Lan` và `Lê Thanh Bình` cùng được phân công vào `Phiên #014`; thử mời email Operator mới hoặc thu hồi 1 người.
10. **Lời mời xem livestream & Mã QR (`/studio/sessions/ses-014/invites`):** Xem 4 liên kết đặt tên bất biến (`Đối tác phân phối`, `Nhóm dùng thử`, `Sự kiện trải nghiệm`, `Truyền thông nội bộ (Đã thu hồi)`), tạo link mới, tải mã QR PNG thật, bấm **Mở thử phòng xem khách**.
11. **Phòng xem khách di động (`/live/ses-014?invite=ml014-doitac`):** Thu nhỏ cửa sổ về di động (`390×844` hoặc DevTools Mobile), kiểm tra không có thanh điều hướng Merchant, nhập biệt danh và bấm **Vào phòng livestream**. Thử thêm `&demo=waiting` (phòng chờ khóa chat) và `&demo=ended` (phiên kết thúc, không replay).
12. **Khách gửi bình luận:** Nhập bình luận ở Viewer Room và gửi.
13. **Phòng điều khiển livestream (`/studio/sessions/ses-014/control`):** Mở lại bằng vai trò `OWNER` hoặc `OPERATOR`, xác nhận bình luận khách vừa gửi xuất hiện trong hàng đợi; bấm **Ưu tiên** hoặc **Tiến bước phát kế tiếp (Mock ACK)** để xem tiến trình `PlaybackCompleted ACK`.
14. **Vận hành an toàn & Xung đột:** Thử **Tạm dừng AI** (phiên vẫn giữ `Đang phát trực tiếp`), **Chuyển SKU** (`ACCEPTED` chờ safe boundary trước `APPLIED`), **Mô phỏng xung đột 409**, và mở modal **Dừng khẩn cấp** 1 bước (nhấn `Escape` để đóng an toàn).
15. **Kết thúc phiên:** Bấm **Kết thúc phiên** → xác nhận phiên chuyển sang `STOPPED` và khách ở Viewer Room chuyển sang `Phiên đã kết thúc`.
16. **Báo cáo phiên & Xuất CSV/PDF (`/studio/reports`):**
    - Mở **Phiên #013** (`PARTIAL`): xác nhận thời gian `19:00–20:32 19-11`, 7 cột biểu đồ tổng `86 === KPI 86`, thẻ Người xem đồng thời hiển thị `N/A` kèm lý do.
    - Mở **Phiên #012** (`READY`): bấm **Xuất báo cáo (CSV / PDF)** để tải tệp CSV (đã vô hiệu hóa công thức bảng tính) và PDF 1.4 thật về máy. Đổi sang `OPERATOR` để xác nhận chế độ xem rút gọn không có nút xuất.

---

## 4. Giới hạn của bản Mock & Xử lý sự cố (Troubleshooting)

- **Giới hạn:** Không phát video WebRTC/LiveKit thật, không chạy AI model thật, dữ liệu lưu trong bộ nhớ trình duyệt (MSW) nên tải lại toàn bộ trang (hard reload) sẽ giữ dữ liệu trong cùng phiên worker hoặc reset khi khởi động lại tab mới.
- **Lỗi chạy `npm run dev` ở thư mục gốc repo:** Phải `cd apps/web` trước khi chạy `npm run dev` vì `package.json` của frontend nằm trong `apps/web/`.
- **Mã QR trên `localhost`:** Mã QR mã hóa đúng URL của origin hiện tại (`http://localhost:5173/live/...`); điện thoại ngoài chỉ quét mở trực tiếp được khi dev server mở qua địa chỉ LAN (`npm run dev -- --host`).
