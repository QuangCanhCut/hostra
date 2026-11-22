# HOSTRA AI — Kế hoạch Kiểm thử Khả năng Sử dụng với Người dùng Thật (Human Usability Test Plan)

> **TRẠNG THÁI:** **KẾ HOẠCH CHƯA THỰC THI (PLAN ONLY — CHƯA CÓ DỮ LIỆU NGƯỜI THAM GIA THẬT).** Tuyệt đối không tự điền thời gian thao tác, tỷ lệ hoàn thành hay điểm SUS giả khi chưa tổ chức phiên thử nghiệm thực tế.

---

## 1. Mục tiêu & Quy mô tuyển chọn đề xuất
- **Phương pháp:** Formative Usability Testing (kiểm thử định tính có người điều phối, nghĩ thành tiếng — *Think-Aloud Protocol*).
- **Quy mô đề xuất:** **5–8 người tham gia** đại diện cho 4 nhóm vai trò:
  - 2–3 **Chủ sở hữu (Owner)**: Chủ cơ sở/HTX bán đặc sản, nông sản OCOP (ít kinh nghiệm công cụ kỹ thuật).
  - 1–2 **Vận hành viên (Operator)**: Nhân viên từng trực phiên livestream hoặc chăm sóc khách hàng.
  - 1–2 **Khách xem (Viewer)**: Người mua hàng online trên điện thoại di động.
  - 1 **Chủ thể quyền (Rights Subject)**: Người được đề nghị cấp quyền sử dụng hình ảnh.

---

## 2. Bộ nhiệm vụ thực hành (Không gợi ý đáp án)

### Nhóm A — Chủ sở hữu (Owner)
1. **Nhiệm vụ O1:** Đăng nhập, kiểm tra tình trạng sẵn sàng của *Phiên #015* và cho biết lý do phiên chưa thể bắt đầu.
2. **Nhiệm vụ O2:** Vào xem hồ sơ sản phẩm *Trà thảo mộc Sơn La (ML-003)* và cho biết sản phẩm này đã được phép lên sóng chưa, vì sao.
3. **Nhiệm vụ O3:** Mở *Story Planner* của *Phiên #015*, nhờ Trợ lý AI đề xuất chỉnh sửa, áp dụng vào bản nháp và cho biết kịch bản đã tự động được duyệt chưa.
4. **Nhiệm vụ O4:** Mở báo cáo *Phiên #013*, đọc số lượt vào phòng, số câu AI đã phát và giải thích vì sao mục *Người xem đồng thời cao nhất* hiển thị `N/A`.

### Nhóm B — Vận hành viên (Operator)
1. **Nhiệm vụ OP1:** Mở *Phòng điều khiển Phiên #014*, thực hiện **Tạm dừng AI** và cho biết khách xem có bị ngắt livestream hay không.
2. **Nhiệm vụ OP2:** Gửi yêu cầu chuyển sang sản phẩm *Mật ong rừng Mường Lát* và cho biết sản phẩm đang phát trên sóng đã đổi ngay chưa.
3. **Nhiệm vụ OP3:** Tìm và mở bảng xác nhận **Dừng khẩn cấp**, sau đó hủy bỏ an toàn.

### Nhóm C — Khách xem di động (Viewer)
1. **Nhiệm vụ V1:** Mở liên kết mời trên điện thoại, nhập biệt danh và vào phòng xem.
2. **Nhiệm vụ V2:** Cho biết tên & giá sản phẩm đang được giới thiệu, sau đó gửi 1 câu hỏi bình luận.

### Nhóm D — Chủ thể quyền (Rights Subject)
1. **Nhiệm vụ R1:** Mở trang xác nhận quyền hình ảnh, đọc phạm vi cấp quyền và cho biết quyền hình ảnh có bao gồm quyền nhân bản giọng nói không.

---

## 3. Quy tắc điều phối & Bảo vệ dữ liệu người tham gia
- **Không gợi ý đáp án:** Người điều phối chỉ hỏi mở (*"Anh/chị đang mong đợi điều gì sẽ xảy ra khi bấm vào đây?"*), không chỉ chuột hay đọc tên nút thay người thử nghiệm.
- **Đồng thuận & Bảo mật:** Giải thích rõ đây là bản thử nghiệm giao diện mô phỏng; xin phép trước khi ghi màn hình/giọng nói; mã hóa danh tính người tham gia thành `P1..P8` và xóa bản ghi thô sau khi tổng hợp xong.

---

## 4. Mẫu bảng ghi nhận kết quả *(Để trống — chỉ điền khi có quan sát thật)*

| Người tham gia | Vai trò | Mã nhiệm vụ | Hoàn thành (Đạt / Đạt có gợi ý / Thất bại) | Thời gian (giây) | Số lỗi bấm nhầm | Điểm gây bối rối quan sát được |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| `P1` | *(Chưa thu thập)* | — | — | — | — | — |

---

## 5. Câu hỏi phỏng vấn sau tác vụ & Thang đánh giá SUS
1. Màn hình nào khiến anh/chị cảm thấy dễ hiểu nhất? Màn hình nào gây phân vân nhất?
2. Có từ ngữ nào trên màn hình mà anh/chị thấy khó hiểu hoặc giống ngôn ngữ kỹ thuật không?
3. Khi bấm *Tạm dừng AI* hoặc *Chuyển SKU*, anh/chị có chắc chắn hệ thống đang làm gì tiếp theo không?
4. Đánh giá tổng thể theo thang **System Usability Scale (SUS — 10 câu, thang 1–5)** sau khi hoàn tất phiên.
