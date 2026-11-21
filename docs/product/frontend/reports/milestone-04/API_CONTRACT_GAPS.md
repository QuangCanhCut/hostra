# HOSTRA AI — API & Realtime Event Contract Gaps (Gate 5)

Tài liệu này liệt kê các khoảng trống hợp đồng API/Event giữa Frontend Mock MVP hiện tại (`apps/web/src/mocks/`) và Backend mục tiêu để đội ngũ Backend ký duyệt trước khi triển khai tích hợp.

---

## 1. Realtime WebSocket Event Envelope (`PROPOSED`)

Mọi sự kiện realtime gửi từ Backend về Control Room và Viewer Room cần tuân thủ phong bì chuẩn hóa (các trường đánh dấu `PROPOSED` cần Backend xác nhận tên trường chính thức):

```json
{
  "event_id": "evt_01J...",
  "event_type": "SESSION_LIFECYCLE_CHANGED",
  "tenant_id": "ws-muong-lat-01",
  "session_id": "ses-014",
  "session_epoch": 3,
  "revision": 43,
  "command_id": "cmd_01J... (optional)",
  "actor_id": "usr-op-01 (optional)",
  "occurred_at": "2026-11-21T07:45:12.340Z",
  "payload": {}
}
```

### Danh mục `event_type` cần hỗ trợ (`PROPOSED`)
1. `SESSION_LIFECYCLE_CHANGED` — Chuyển trạng thái `STARTING → LIVE → STOPPING → STOPPED / FAILED`.
2. `AI_EXECUTION_CHANGED` — `ACTIVE ↔ PAUSE_REQUESTED → PAUSED → RESUMING / BLOCKED`.
3. `MEDIA_HEALTH_CHANGED` — `HEALTHY ↔ DEGRADED / FAILED` kèm `fallback_mode_label`.
4. `PUBLISHER_STATE_CHANGED` — `CONNECTED / DEGRADED / DISCONNECTED`.
5. `ACTIVE_SKU_CHANGED` — Chỉ phát sau khi safe boundary áp dụng (`APPLIED`).
6. `COMMAND_STATUS_CHANGED` — `REQUESTED → ACCEPTED → APPLIED | REJECTED` kèm `reason` & `actor_name`.
7. `COMMENT_RECEIVED` — Bình luận hợp lệ sau moderation xuất hiện trong Control Room & Viewer Room.
8. `SPEECH_TURN_UPDATED` — Cập nhật giai đoạn lượt nói (`PLANNING → VERIFYING → PREPARING_AUDIO → LIP_SYNC → READY → COMMITTED → PLAYING`).
9. `PLAYBACK_COMPLETED_ACK` — Xác nhận phát thật từ P04 kèm `playback_ack_id` duy nhất.
10. `INVITATION_REVOKED` — Thông báo thu hồi liên kết mời; buộc client viewer liên quan thoát phòng ngay.
11. `MEMBER_GRANT_REVOKED` — Thông báo thu hồi quyền Operator trên phiên; vô hiệu hóa thanh điều khiển ngay lập tức.
12. `SNAPSHOT_RESYNC_REQUIRED` — Yêu cầu client refetch REST authoritative snapshot khi gap sequence quá lớn.

### Quy tắc đồng bộ phía Client
- **Ordering & Deduplication:** Bỏ qua event có `session_epoch < currentEpoch` hoặc `(session_epoch === currentEpoch && revision < currentRevision)`; khử trùng lặp theo `event_id` và `playback_ack_id`.
- **Reconnect:** Khi WS mất kết nối (`STALE`/`RECONNECTING`), client khóa nút gửi lệnh nhạy cảm; ngay khi nối lại phải gọi REST `GET /sessions/:id/control` (hoặc `/viewer/:id`) để đồng bộ snapshot mới nhất, **không tự động replay các lệnh runtime cũ**.
- **Conflict Rejection (`409`):** Mọi mutation gửi kèm `expected_revision` + `command_id` (idempotency key); khi nhận `409`, UI giữ nguyên trạng thái authoritative, hiển thị banner xung đột và refetch snapshot.

---

## 2. Danh sách Contract Gaps & Open Decisions cần Backend/PO chốt

| Mã Gap | Hạng mục | Hiện trạng ở Mock | Cần chốt trước tích hợp | Mức ưu tiên |
| :--- | :--- | :--- | :--- | :---: |
| **GAP-01** | Managed OIDC & Session Cookie | Chuyển role bằng query `?role=OWNER|OPERATOR` | Chọn provider OIDC, cơ chế HTTP-only cookie / CSRF, endpoint `/auth/me` & logout | **P0** |
| **GAP-02** | REST Path Prefix & OpenAPI Schema | `/api/mock/v1/*` | Ban hành OpenAPI spec chính thức cho `apps/api/` để thay adapter trong `src/services/api-client.ts` | **P0** |
| **GAP-03** | LiveKit Subscribe-Only & Instant Kick (`IM-D4`) | Ảnh minh họa tĩnh + kiểm tra `guest.revoked` qua poll | Cơ chế cấp LiveKit token subscribe-only cho guest và gọi `removeParticipant` tức thì khi revoke invite | **P0** |
| **GAP-04** | Rights Subject Identity Verification (P11) | Trang `/rights/consent/:requestId` xác nhận 1 chạm | Cơ chế xác thực OTP/eKYC hoặc signed token 1 lần cho Rights Subject độc lập | **P0** |
| **GAP-05** | Safe Boundary cho Live Revision (P04/P05/P08) | Đổi giá/facts/story cập nhật store ngay trên mock | Chính sách áp dụng revision mới khi đang LIVE và hủy TTS/clip lỗi thời | **P0** |
| **GAP-06** | PDF Export Tiếng Việt Unicode (P12) | Client-side PDF 1.4 tối giản chuẩn hóa ASCII không dấu | Worker xuất PDF phía server nhúng font `Be Vietnam Pro` UTF-8 + signed download URL ngắn hạn | **P1** |
| **GAP-07** | Quyền Operator sửa Pre-live Setup/Story | Mặc định Owner-only (theo `DECISIONS.md`) | Chốt chính thức với PO nếu muốn mở quyền cho Operator ở một số bước pre-live | **P1** |
| **GAP-08** | Retention quyền xem Report sau khi thu hồi Operator (`RPT-O6`) | Thu hồi assignment → mất quyền xem report phiên đó | Xác nhận chính sách audit/retention với PO & Backend IAM | **P1** |
