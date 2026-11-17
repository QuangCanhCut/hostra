# HOSTRA AI — Trung tâm tài liệu

> **Phạm vi:** Thư mục này là nơi tập trung bối cảnh sản phẩm, các quyết định kiến trúc, thiết kế kỹ thuật, hướng dẫn triển khai và bằng chứng xác thực của HOSTRA.
>
> **Quan trọng:** Một quyết định được ghi thành tài liệu **không** phải là bằng chứng cho thấy một năng lực đã được triển khai hoặc xác thực. Luôn kiểm tra trạng thái tài liệu và bằng chứng hỗ trợ.

## 1. Mục đích

Thư mục `docs/` giúp mọi thành viên trong nhóm trả lời bốn câu hỏi:

1. **Chúng ta đang xây dựng gì?** — Phạm vi sản phẩm và đường cơ sở kiến trúc hiện tại.
2. **Tại sao chúng ta chọn cách tiếp cận này?** — Rủi ro, nghiên cứu, quyết định và các đánh đổi.
3. **Nên triển khai như thế nào?** — Thiết kế, đặc tả API, hợp đồng dữ liệu và hướng dẫn kỹ thuật.
4. **Làm sao biết nó hoạt động?** — Kiểm thử, benchmark, báo cáo tích hợp và bằng chứng từ triển khai thí điểm.

`docs/` chứa **tài liệu đã được xem xét hoặc tài liệu tham khảo**. Mã thử nghiệm và các kết quả đo trung gian nằm trong `experiments/`; phần triển khai nằm trong `apps/`, `workers/` và `packages/`. Các hợp đồng liên mô-đun được mã nguồn sử dụng trực tiếp thuộc về `packages/contracts/` và được quản lý phiên bản cùng với phần triển khai.

## 2. Sơ đồ thư mục

```text
docs/
├── README.md                         # Mục lục này và các quy tắc tài liệu
├── product/                          # Tổng quan sản phẩm, phạm vi, hành trình người dùng
│
├── 01-solution-architecture/         # Giai đoạn 01 — kiến trúc giải pháp
│   └── archive/                      # Các phiên bản kiến trúc đã được thay thế
│
├── 02-risk-assessment/               # Giai đoạn 02 — rủi ro kiến trúc/kỹ thuật
│   └── archive/                      # Các bản đánh giá rủi ro đã được thay thế
│
├── 03-technical-research/            # Giai đoạn 03 — nghiên cứu và lập kế hoạch PoC
│   ├── decisions/                    # Hồ sơ lựa chọn và kết luận nghiên cứu
│   └── archive/                      # Các kế hoạch nghiên cứu đã được thay thế
│
├── 04-technical-design/              # Giai đoạn 04 — thiết kế chi tiết (LLD)
│   ├── adr/                          # Hồ sơ quyết định kiến trúc
│   ├── api/                          # Đặc tả API/giao diện
│   ├── data-models/                  # Lược đồ, mô hình thực thể, thiết kế lưu trữ
│   └── component-designs/            # Thiết kế chi tiết theo từng hệ thống con
│
├── 05-implementation/                # Giai đoạn 05 — lập kế hoạch và hướng dẫn xây dựng
│   ├── roadmap/                      # Các cột mốc và trình tự bàn giao
│   ├── work-packages/                # Epic, người phụ trách, các phụ thuộc, DoD
│   └── development-guides/           # Thiết lập, quy ước, hướng dẫn viết mã/kiểm thử
│
├── 06-integration/                   # Giai đoạn 06 — tích hợp theo lát cắt dọc
│   ├── integration-plans/            # Kế hoạch tích hợp liên mô-đun
│   └── integration-reports/          # Kết quả và vấn đề tích hợp
│
└── 07-validation-and-pilot/          # Giai đoạn 07 — bằng chứng và mức độ sẵn sàng thí điểm
    ├── test-plans/                   # Chiến lược kiểm thử, tiêu chí nghiệm thu
    ├── benchmark-reports/            # Các phép đo hiệu năng/chất lượng/chi phí
    └── pilot-reports/                # Kết quả thí điểm và quyết định triển khai hay không
```

> Số thứ tự giai đoạn mô tả **nhóm chính trong vòng đời**, không phải thứ tự thực hiện bắt buộc. Nghiên cứu, triển khai, tích hợp và xác thực có thể tiến hành lặp lại và song song.

## 3. Nội dung thuộc về đâu?

| Thư mục | Nội dung | **Không** thuộc về đây |
| --- | --- | --- |
| `product/` | Tổng quan sản phẩm, người dùng mục tiêu, phạm vi MVP, hành trình người dùng, các giả định về sản phẩm | Chi tiết API hoặc ghi chú chỉ liên quan đến triển khai |
| `01-solution-architecture/` | Ranh giới hệ thống, các thành phần, trách nhiệm, luồng dữ liệu, các bất biến kiến trúc, quyết định đã được xác nhận | Notebook PoC thô hoặc nhật ký benchmark |
| `02-risk-assessment/` | Danh mục rủi ro, kịch bản lỗi, mức độ nghiêm trọng/ưu tiên, phương án giảm thiểu, câu hỏi xác thực và bằng chứng cần thiết | Khẳng định rằng rủi ro đã được giảm thiểu mà không có bằng chứng |
| `03-technical-research/` | Các ứng viên kỹ thuật, cơ sở lựa chọn, kế hoạch thử nghiệm, các stack được đề xuất hoặc chọn cho PoC, hồ sơ quyết định | Mã worker dùng trong môi trường sản xuất hoặc các lượt chạy thô chưa được xem xét |
| `04-technical-design/` | Thiết kế chi tiết thành phần, máy trạng thái, API, sự kiện, mô hình dữ liệu, xử lý lỗi, ADR | Toàn bộ bản sao mã API client được tạo tự động |
| `05-implementation/` | Lộ trình, backlog/gói công việc, hướng dẫn thiết lập, quy ước kỹ thuật | Bản thân mã nguồn hoặc các GitHub Issue bị sao chép |
| `06-integration/` | Kế hoạch theo lát cắt dọc, xác minh liên mô-đun, kết quả tích hợp | Các tệp triển khai kiểm thử đơn vị |
| `07-validation-and-pilot/` | Kế hoạch kiểm thử, bản tóm tắt benchmark có thể tái lập, kết quả nghiệm thu, báo cáo thí điểm | Tập dữ liệu thô lớn, trọng số hoặc hiện vật đa phương tiện |

### `03-technical-research/decisions/` so với `04-technical-design/adr/`

- **Quyết định nghiên cứu:** Nên nghiên cứu hoặc lựa chọn công nghệ hay cách tiếp cận nào sau khi đánh giá so sánh? Bao gồm các ứng viên, chỉ số, ràng buộc và bằng chứng.
- **ADR:** Cơ sở mã sẽ áp dụng lựa chọn kiến trúc nào, tại sao và hệ quả của lựa chọn đó là gì? Bao gồm trạng thái, các phương án thay thế và giao diện bị ảnh hưởng.

Cùng một quyết định có thể được liên kết từ cả hai nơi, nhưng không nên được duy trì thành hai phiên bản chuẩn mâu thuẫn với nhau.

## 4. Các tài liệu hiện có và trạng thái

Đây là những tài liệu hiện có trong bối cảnh làm việc của HOSTRA. **Chỉ đặt các tệp thực sự tồn tại** vào kho lưu trữ; không tạo các phiên bản lưu trữ giả.

| Tài liệu | Phiên bản | Thư mục đích | Diễn giải |
| --- | --- | --- | --- |
| `HOSTRA_AI_Project_Overview_Proposal_v1.0.docx` | v1.0 | `product/` | **Cần được điều chỉnh cho phù hợp** với các quyết định mới hơn về tạo người dẫn và MVP OCOP |
| `HOSTRA_AI_Solution_Architecture_Baseline_v1.2.docx` | v1.2 | `01-solution-architecture/` | Đường cơ sở kiến trúc đang được sử dụng hiện tại, phù hợp với Giai đoạn 03; đang chờ xác thực công nghệ PoC |
| `HOSTRA_AI_Technical_Risk_Assessment_v1.1.docx` | v1.1 | `02-risk-assessment/` | Bản dự thảo rà soát rủi ro phù hợp với Giai đoạn 03; các rủi ro vẫn còn bỏ ngỏ trong khi chờ bằng chứng |
| `HOSTRA_AI_Technical_Research_and_PoC_Plan_v1.0.docx` | v1.0 | `03-technical-research/` | Sổ tay nghiên cứu và P01–P13 **SELECTED FOR PoC**, chưa được xác thực |

**Điểm không thống nhất đã biết trong tài liệu:** Project Overview v1.0 mô tả một người dẫn thật được quay hình. Các quyết định sau đó trong Architecture Baseline v1.2 / Giai đoạn 03 sử dụng một ảnh chân dung duy nhất đã được đồng ý sử dụng, PhotoMaker + Wan2.2 Animate để tạo trước các đoạn video người dẫn, và MuseTalk để đồng bộ khẩu hình trong khi phát trực tiếp. Định hướng sau đó cũng giới hạn MVP ban đầu ở các SKU thực phẩm đóng gói đủ điều kiện và đã được xác minh OCOP. Cho đến khi bản tổng quan được chỉnh sửa và xem xét, **không** sử dụng riêng tài liệu này làm đặc tả kỹ thuật/sản phẩm hiện tại có tính quyết định.

Khi có bất đồng, hãy tuân theo các quyết định và hồ sơ thay đổi mới hơn đã được phê duyệt rõ ràng, sau đó ghi lại việc thống nhất trong tài liệu hoặc ADR liên quan. Một lựa chọn công nghệ chưa được xác minh vẫn giữ trạng thái **SELECTED FOR PoC** ngay cả khi xuất hiện trong kiến trúc.

## 5. Vòng đời tài liệu và nhãn trạng thái

Sử dụng nhất quán các thuật ngữ sau:

| Trạng thái | Ý nghĩa |
| --- | --- |
| `DRAFT` | Đang thực hiện; chưa được xem xét hoặc chấp nhận |
| `IN REVIEW` | Đang chờ phản hồi/phê duyệt từ những người được chỉ định xem xét |
| `CONFIRMED REQUIREMENT` | Yêu cầu sản phẩm/hệ thống đã được nhóm thống nhất; **không** phải bằng chứng cho thấy nó hoạt động |
| `PROPOSED` | Thiết kế hoặc phương án được đề xuất, vẫn có thể thay đổi |
| `SELECTED FOR PoC` | Được chọn để thử nghiệm; **không** phải xác thực về hiệu năng, giấy phép hoặc khả năng dùng trong môi trường sản xuất |
| `TO VALIDATE` | Vấn đề còn bỏ ngỏ cần bằng chứng đo lường, xem xét hoặc xác minh |
| `VALIDATED` | Đã đáp ứng tiêu chí nghiệm thu với bằng chứng có thể tái lập và sự phê duyệt của người xem xét |
| `DEFERRED` | Được xác định rõ là nằm ngoài phạm vi MVP hiện tại |
| `SUPERSEDED` | Đã được thay thế bằng phiên bản hoặc quyết định mới hơn |

Một tài liệu có thể có trạng thái xem xét tổng thể trong khi các quyết định riêng lẻ có trạng thái kỹ thuật khác nhau. Hãy thể hiện rõ cả hai.

## 6. Quy tắc đặt tên, phiên bản và lưu trữ

### Đặt tên

Đối với các tài liệu Word bàn giao hiện tại, giữ nguyên quy ước hiện có:

```text
HOSTRA_AI_<Document_Title>_vMAJOR.MINOR.docx
```

Đối với tài liệu kỹ thuật, ưu tiên Markdown khi phù hợp:

```text
ADR-0001-single-speech-authority.md
P03-lipsync-benchmark-report.md
session-state-machine.md
```

### Quản lý phiên bản

1. Giữ **một phiên bản hiện tại được chỉ định rõ ràng** của mỗi tài liệu ở cấp cao nhất trong thư mục tương ứng.
2. Chuyển các phiên bản trước vào thư mục `archive/` của nhóm tương ứng **chỉ khi chúng thực sự đã được thay thế** và cần tiếp tục được truy cập.
3. Không bao giờ âm thầm ghi đè một đường cơ sở đã được xem xét trước đó. Ghi lại các thay đổi đáng chú ý và lý do.
4. Lịch sử Git là lịch sử chính của các tài liệu dạng văn bản. Giữ các bản lưu trữ `.docx` khi việc xem xét/phê duyệt hoặc so sánh yêu cầu bản sao bất biến.
5. Ưu tiên liên kết tương đối trong Markdown để việc điều hướng vẫn hoạt động sau khi sao chép kho lưu trữ.
6. Không sao chép một tệp vào nhiều thư mục giai đoạn chỉ vì tệp liên quan đến từng giai đoạn; thay vào đó, hãy liên kết đến vị trí chuẩn của tệp.

**Phần đầu tài liệu được đề xuất:** Tiêu đề · Phiên bản · Ngày · Người phụ trách · Trạng thái xem xét · Trạng thái quyết định · Thay thế · Tài liệu liên quan · Liên kết bằng chứng.

## 7. Quy trình thêm hoặc cập nhật tài liệu

1. **Chọn thư mục phụ trách** bằng cách sử dụng sơ đồ thư mục ở trên.
2. **Tạo tài liệu** và chỉ định người phụ trách, phiên bản, ngày và trạng thái.
3. **Liên kết bằng chứng** (ID lượt chạy thử nghiệm, SHA commit, manifest benchmark, báo cáo kiểm thử) mỗi khi khẳng định một kỹ thuật đã vượt qua bước xác thực.
4. **Yêu cầu xem xét** từ người phụ trách hệ thống con và người xem xét tích hợp/sản phẩm có liên quan.
5. **Công bố phiên bản đã được chấp nhận**, lưu trữ bản đã được thay thế khi phù hợp và cập nhật mục lục này.
6. **Cập nhật các tham chiếu ở bước tiếp theo** (ADR, gói công việc, kiểm thử) nếu quyết định ảnh hưởng đến việc triển khai hoặc nghiệm thu.

### Ví dụ: Nghiên cứu đồng bộ khẩu hình P03

- Mã thử nghiệm và kết quả đo: `experiments/ai-presenter-media/lipsync/`
- Cơ sở lựa chọn PoC: `docs/03-technical-research/decisions/`
- Giao diện worker chi tiết và thiết kế vận hành: `docs/04-technical-design/component-designs/`
- Phần triển khai đã được chấp nhận: `workers/lipsync/`
- Benchmark tóm tắt và bằng chứng cho quyết định triển khai hay không: `docs/07-validation-and-pilot/benchmark-reports/`

## 8. Ranh giới kho lưu trữ và tài liệu nhạy cảm

Không commit trực tiếp vào `docs/` các thông tin bí mật, khóa API, tài liệu khách hàng riêng tư, bằng chứng nhận dạng liên quan đến sự đồng ý, mẫu giọng nói thô, ảnh chân dung riêng tư, tài sản nhận dạng được tạo ra, tập dữ liệu lớn hoặc trọng số mô hình. Lưu các hiện vật được bảo vệ tại một vị trí hạn chế đã được phê duyệt và liên kết bằng các định danh không nhạy cảm cùng các tham chiếu được kiểm soát quyền truy cập.

Trước khi chia sẻ tài liệu ra ngoài nhóm, hãy xem xét quyền riêng tư, quyền đối với người dẫn/giọng nói, giấy phép của nhà cung cấp, thông tin người bán và mọi khẳng định chưa được xác minh về hiệu năng hoặc tích hợp nền tảng.

## 9. Các bước tiếp theo hiện tại

- [ ] Sao chép bốn tài liệu hiện có vào các thư mục chuẩn tương ứng.
- [ ] Đánh dấu `product/HOSTRA_AI_Project_Overview_Proposal_v1.0.docx` là cần được điều chỉnh cho phù hợp với ACR-001/ACR-002.
- [ ] Liệt kê các phiên bản lưu trữ thực tế, nếu có; nếu không, để trống `archive/`.
- [ ] Chỉ định người phụ trách xem xét cho các Giai đoạn 01–03 và xác định các quyết định còn bỏ ngỏ.
- [ ] Tạo mẫu ADR và thiết kế thành phần cho Giai đoạn 04 trước khi triển khai chi tiết.
- [ ] Thêm liên kết đến bằng chứng PoC được đo lường khi các thử nghiệm hoàn tất; không đánh dấu P01–P13 là `VALIDATED` chỉ dựa trên việc đã được lựa chọn.

---

**Quy tắc bảo trì:** Khi thêm, đổi tên hoặc di chuyển tài liệu, hãy cập nhật `docs/README.md` này trong cùng một pull request.
