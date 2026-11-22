# HOSTRA AI — Danh mục Cải tiến Ưu tiên (Improvement Backlog — M05.1)

Các hạng mục cải tiến được chia thành **3 nhóm** rõ ràng để thuận tiện duyệt và triển khai ở M05.2.

---

## Nhóm 1 — Cải tiến Nhanh, Rủi ro Thấp (Quick Wins)

| Mã | Hạng mục | Liên kết Issue | Tiêu chí nghiệm thu (Acceptance Criteria) | Duyệt PO |
| :--- | :--- | :---: | :--- | :---: |
| **QW-01** | Sửa toàn bộ biến CSS sai tên trong `ReportsHistoryPage` và `SessionReportPage` | `UX-01` | Thay `--border-subtle`/`--surface-base`/`--surface-subtle`/`--radius-md` bằng token chuẩn trong `tokens.css`; Dark Mode không còn viền trắng sắc lẻm | Không cần (sửa lỗi hiển thị) |
| **QW-02** | Chống vỡ dòng 2 hàng trên `StatusBadge` (`whitespace-nowrap shrink-0`) | `UX-07` | Nhãn `Đã đo` trong 5 thẻ KPI Báo cáo nằm gọn 1 dòng trên `1440px` và `1280px` | Không cần |
| **QW-03** | Sửa nút `Mở rộng thanh điều hướng` bị ép còn `16×32px` ở `1024×768` | `UX-03`, `UX-22` | Nút thu gọn/mở rộng Sidebar đạt tối thiểu `36×36px` ở cả `1024px` và `1440px`, không đè lên logo `H` | Không cần |
| **QW-04** | Bỏ mã tài liệu nội bộ (`SR-D2`, `SR-D5`, `IM-D3`, `Time-bucketed SVG`) & Việt hóa `"Workspace"` | `UX-17`, `UX-20`, `UX-21` | 0 chuỗi mã tài liệu nội bộ xuất hiện trên giao diện người bán hàng; giữ nguyên ngữ nghĩa cảnh báo | Không cần |
| **QW-05** | Sửa thẻ `<h1>` bị thiếu & ảnh lỗi ở `ViewerLiveRoomPage` + tăng nút âm thanh `44×44px` + dịu nền icon sản phẩm Dark Mode | `UX-08`, `UX-19` | `ViewerLiveRoomPage` trạng thái LIVE có đúng 1 `<h1>`, `brokenImgs === 0`, nút âm thanh `>= 44×44px`, hộp ảnh sản phẩm hài hòa nền tối | Không cần |

---

## Nhóm 2 — Cải tiến Cấu trúc UX (Cần review trước khi triển khai)

| Mã | Hạng mục | Liên kết Issue | Tiêu chí nghiệm thu (Acceptance Criteria) | Duyệt PO |
| :--- | :--- | :---: | :--- | :---: |
| **SUX-01** | Tách toàn bộ 6 nút mô phỏng dev (4 ở Control Room + 2 ở Viewer) vào `DevScenarioBar` / `Dev Inspector` và ẩn mặc định | `UX-02`, `UX-14` | Mở giao diện mặc định không thấy nút `Mô phỏng...` hay `Mock ACK`; vẫn giữ 100% chức năng mô phỏng cho QA/Demo khi mở bảng `Dev Inspector` hoặc qua query param | Cần xác nhận luồng demo |
| **SUX-02** | Tinh gọn thanh trạng thái Phòng điều khiển & bỏ lặp nút `Chuyển SKU` + thêm đệm đáy khi cuộn | `UX-09`, `UX-10`, `UX-11` | Khi hệ thống bình thường, gom Media/Publisher/Đồng bộ vào 1 pill `Hệ thống ổn định` (tự tách màu cảnh báo ngay khi suy giảm/mất kết nối); chỉ còn 1 nút `Chuyển SKU`; cuộn cuối không bị che nội dung | **Cần PO duyệt** |
| **SUX-03** | Áp dụng Từ điển Ngôn ngữ thân thiện cho Control Room, Readiness & Reports | `UX-06` | Thay các nhãn kỹ thuật (`COMMITTED`, `PlaybackCompleted ACK`, `Epoch`, `P04/P09`) bằng tiếng Việt dễ hiểu theo `UX_MICROCOPY_GLOSSARY.md`; giữ nguyên thuật ngữ chuẩn trong Drawer Chẩn đoán & CSV | **Cần PO duyệt** |
| **SUX-04** | Sắp xếp ưu tiên mục `Bị chặn / Đang chờ` lên đầu trang Readiness & ghim cột tài liệu gốc ở Knowledge Review | `UX-12`, `UX-18` | Ở `/readiness`, mục chặn hiện ngay đầu danh sách; ở `/knowledge/:skuId`, cột tài liệu gốc bên trái đứng yên (`sticky`) khi cuộn duyệt các nhóm fact bên phải | **Cần PO duyệt** |
| **SUX-05** | Tinh gọn trang Cổng Xác nhận Quyền (bỏ nút `Về Studio` ngoài ngữ cảnh, bổ sung hướng dẫn thu hồi) | `UX-16` | Người ngoài doanh nghiệp chỉ thấy nội dung xác nhận & cách thu hồi quyền | **Cần PO duyệt** |

---

## Nhóm 3 — Cải tiến Hệ thống Thiết kế & Accessibility (Đa module)

| Mã | Hạng mục | Liên kết Issue | Tiêu chí nghiệm thu (Acceptance Criteria) | Duyệt PO |
| :--- | :--- | :---: | :--- | :---: |
| **DS-01** | Thêm component `ButtonLink` và gỡ toàn bộ mẫu lồng `<Link><Button>` trên 6 trang | `UX-04` | 0 phần tử `<button>` nằm bên trong `<a>` trên toàn ứng dụng; nhấn phím `Tab` đi qua mỗi nút đúng 1 lần | Không cần |
| **DS-02** | Nâng cấp `Modal.tsx` & `Drawer.tsx` với Focus Trap, Focus Restoration và khóa cuộn nền | `UX-05` | Mở Modal/Drawer → `Tab` xoay vòng bên trong, đóng Modal trả focus chính xác về nút đã mở | Không cần |
| **DS-03** | Chuẩn hóa kích thước vùng chạm trên mobile/tablet (`>= 44px`) & thêm biến thể Badge nhẹ giảm nhiễu Dashboard | `UX-13`, `UX-15` | Giảm số badge màu nổi trên Dashboard từ 15 xuống `<= 7`; nút lọc & liên kết hành động trên `<= 768px` đạt vùng chạm dễ bấm | Không cần |
