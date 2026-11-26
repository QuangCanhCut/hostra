# Quản lý Prompt Templates P06 (`prompts/`)

**Trạng thái:** Đã khởi tạo các template cốt lõi cho `P06-E01` / `P06-E04` (`PROMPT_VERSION: v0.1`). Các template cho luồng bình luận/nối mạch (`comment_response.txt`, `resume_bridge.txt`) đang ở trạng thái `NOT STARTED` cho các wave sau.

## 1. Quy tắc phiên bản hóa & Truy vết (Provenance)

- Dòng đầu tiên của mọi tệp `*.txt` **bắt buộc** khai báo tường minh `PROMPT_VERSION: <version>` (ví dụ `PROMPT_VERSION: v0.1`). Bộ nạp `p06.planning.prompt_loader.load_prompt_template()` sẽ **fail-closed** (`ValueError`) nếu thiếu hoặc để trống header này.
- Hàm `compute_prompt_hashes()` tính **SHA-256** trên nội dung UTF-8 đã chuẩn hóa kết thúc dòng về **LF (`\n`)** (`\r\n` và `\r` -> `\n`) trước khi băm, bảo đảm mã hash đồng nhất tuyệt đối giữa Windows, Linux và macOS để ghi vào `runs/<exp_id>/<run_id>/manifest.json`.
- Không sửa ngầm prompt trong khi so sánh giữa các cấu hình hoặc giữa baseline và phương pháp đề xuất mà không cập nhật version / tạo run mới với hash mới.

## 2. Nguyên tắc tách biệt dữ liệu không tin cậy (Prompt Injection Delimiters)

- Bình luận người xem, văn bản tri thức sản phẩm (`SkuEvidenceView`), tên/mô tả sản phẩm và dữ liệu lịch sử động **không bao giờ được xem là system instructions**.
- Toàn bộ prompt đều bọc dữ liệu tri thức trong cặp thẻ phân tách:
  ```text
  <untrusted_knowledge_data>
  {{untrusted_knowledge_block}}
  </untrusted_knowledge_data>
  ```
- Hàm `render_prompt_template()` thay thế một lượt (single-pass) chỉ các biến dạng `{{variable_name}}`, giữ nguyên cặp ngoặc nhọn đơn `{ ... }` của ví dụ JSON trong prompt và **fail-closed** (`ValueError`) nếu thiếu biến đầu vào hoặc còn sót placeholder `{{...}}` chưa được điền.
- Đầu ra LLM chỉ là bản nháp không tin cậy (`StoryPlanDraftLLMOutput` / `ChunkDraftLLMOutput`), tuyệt đối không chứa các trường thẩm quyền (`tenant_id`, `approval_status`, `verification_status`, `knowledge_version`, ...), và luôn phải qua `P05` `PublicationGate` (`I-02`) trước khi phát sóng.

## 3. Danh sách template và Placeholders

| Tệp template | Phiên bản | Trạng thái | Placeholders bắt buộc (`{{...}}`) |
| :--- | :---: | :---: | :--- |
| `story_planner.txt` | `v0.1` | `ACTIVE (PoC)` | `session_goal`, `pinned_skus`, `mandatory_messages`, `prohibited_topics`, `target_duration_sec`, `untrusted_knowledge_block` |
| `story_generation.txt` | `v0.1` | `ACTIVE (PoC)` | `active_sku_id`, `session_goal`, `arc_title`, `topic_id`, `topic_title`, `talking_points`, `mandatory_messages`, `prohibited_topics`, `max_duration_sec`, `played_history_summary`, `untrusted_knowledge_block` |
| `rewrite.txt` | `v0.1` | `ACTIVE (PoC)` | Toàn bộ biến của `story_generation.txt` + `previous_draft_text`, `failure_reasons`, `retry_attempt`, `max_retries` |
| `comment_response.txt` | — | `NOT STARTED` | Dành cho wave `P06-E02` (trả lời bình luận người xem bám `P07`) |
| `resume_bridge.txt` | — | `NOT STARTED` | Dành cho wave `P06-E03` (câu chuyển tiếp sau ngắt quãng `I-06`) |
