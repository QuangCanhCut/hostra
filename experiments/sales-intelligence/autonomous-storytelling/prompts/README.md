# Quản lý Prompt Templates P06 (`prompts/`)

**Trạng thái:** `NOT STARTED` (chưa tạo các tệp template `.txt`).

## 1. Quy tắc phiên bản hóa & Truy vết

- Mỗi prompt template phải gắn mã phiên bản rõ ràng và được tính **SHA-256 hash** để ghi vào `manifest.json` của từng lần chạy trong `runs/`, đảm bảo tái lập thí nghiệm.
- Không sửa ngầm prompt trong khi so sánh giữa các cấu hình hoặc giữa baseline và phương pháp đề xuất mà không tạo run mới/hash mới.

## 2. Nguyên tắc tách biệt dữ liệu không tin cậy (Untrusted Input Separation)

- Bình luận người xem (`CommentTask`), văn bản thô từ tài liệu OCR và các chuỗi đầu vào động tuyệt đối **không được coi là system instructions**.
- Mọi prompt template phải phân tách rõ vùng chỉ dẫn hệ thống (`system`) với vùng dữ liệu ngữ cảnh/bình luận (`user` / delimited data blocks) và luôn dựa vào `guardrails` + P05 `PublicationGate` để chặn prompt injection trước phát sóng.

## 3. Danh sách template dự kiến (`NOT STARTED`)

- `story_planner.txt` — Lập cấu trúc `StoryPlan` theo mục tiêu merchant và mandatory topics.
- `story_generation.txt` — Sinh từng `StoryChunk` ngắn có breakpoint tự nhiên và trích dẫn `evidence_id`.
- `comment_response.txt` — Trả lời `CommentTask` ngắn gọn bám sát `EvidenceBundle` và lịch sử đã phát.
- `resume_bridge.txt` — Tạo câu chuyển tiếp (bridge) tự nhiên khi quay lại phần `StoryPlan` chưa phát.
- `rewrite.txt` — Sửa lại candidate bị từ chối hoặc lặp ý trong giới hạn `max_rewrite_retries`.
