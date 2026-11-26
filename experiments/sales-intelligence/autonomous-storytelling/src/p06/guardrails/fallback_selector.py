"""Bộ chọn câu dự phòng an toàn theo nguyên tắc fail-closed (`SafeFallbackSelector`).

1. File này giải quyết vấn đề gì?
   Khi LLM vượt quá ngân sách viết lại (`rewrite_budget`) hoặc gặp sự cố (P06-E04), P06 cần
   chọn một câu dự phòng đã phê duyệt trước (`PREAPPROVED_FALLBACK`) nhưng vẫn phải bảo đảm
   câu đó còn hiệu lực tri thức, OCOP và bản quyền tại đúng thời điểm hiện tại.
2. Trách nhiệm chính của module là gì?
   Duyệt qua các ứng viên `PREAPPROVED_FALLBACK`, đưa từng ứng viên về trạng thái `DRAFT` và
   gọi kiểm định trực tiếp qua `KnowledgeVerifierPort.verify_candidate(...)` trên trạng thái
   kho hiện hành; trả về ứng viên `VERIFIED` hợp lệ đầu tiên hoặc `None` nếu toàn bộ thất bại.
3. Module này liên kết với các thành phần nào?
   Phụ thuộc vào `KnowledgeVerifierPort` (`adapters/interfaces.py`) và `SpeechCandidate`
   (`schemas/candidate.py`); kết quả `None` sẽ dẫn Graph sang `SAFE_ABORT_NO_CANDIDATE` (safe scene).
4. Input và output chính là gì?
   Input là `KnowledgeVerifierPort`, danh sách `SpeechCandidate` dự phòng và `verified_at` tùy chọn;
   Output là `SpeechCandidate` ở trạng thái `VERIFIED` hoặc `None` (fail-closed).
5. Có những constraints hoặc invariants quan trọng nào?
   - Tuyệt đối không tin cậy trạng thái `VERIFIED` lưu sẵn trên fallback cũ (chống TOCTOU);
     mọi fallback đều bắt buộc tái kiểm định trực tiếp tại thời điểm chọn.
   - Chỉ chấp nhận ứng viên có `origin == CandidateOrigin.PREAPPROVED_FALLBACK`.
   - Không bao giờ trả về ứng viên chưa qua xác minh hoặc bị lỗi: nếu tất cả đều trượt, trả về `None`.
"""

from __future__ import annotations

import copy
from collections.abc import Sequence
from datetime import datetime
from typing import Optional

from p06.adapters.interfaces import KnowledgeVerifierPort
from p06.schemas.candidate import (
    CandidateOrigin,
    CandidateVerificationStatus,
    SpeechCandidate,
)


def _reset_candidate_to_draft(candidate: SpeechCandidate) -> SpeechCandidate:
    """Đưa ứng viên về trạng thái `DRAFT` để buộc tái kiểm định trực tiếp qua P05.

    Lý do kỹ thuật (TOCTOU): Một câu dự phòng có thể từng được đánh dấu `VERIFIED` ở đầu phiên,
    nhưng sau đó giá/OCOP/quyền sản phẩm có thể đã thay đổi hoặc bị thu hồi. Đưa về `DRAFT`
    giúp ngăn mọi đường tắt bỏ qua `PublicationGate`.

    Args:
        candidate: Ứng viên dự phòng đầu vào.

    Returns:
        SpeechCandidate: Bản sao mới ở trạng thái `DRAFT` không mang dấu vết duyệt cũ.
    """
    if candidate.verification_status == CandidateVerificationStatus.DRAFT:
        return candidate
    payload = copy.deepcopy(candidate.model_dump())
    payload["verification_status"] = CandidateVerificationStatus.DRAFT
    payload["verified_by_gate_decision_id"] = None
    payload["verified_at"] = None
    payload["rejection_reasons"] = []
    return SpeechCandidate.model_validate(payload)


class SafeFallbackSelector:
    """Bộ chọn câu dự phòng an toàn với cơ chế tái kiểm định trực tiếp và fail-closed."""

    @staticmethod
    def select_safe_fallback(
        verifier: KnowledgeVerifierPort,
        candidates: Sequence[SpeechCandidate],
        verified_at: Optional[datetime] = None,
        tenant_id: Optional[str] = None,
        session_id: Optional[str] = None,
        session_epoch: Optional[int] = None,
        require_empty_covered_topics: bool = False,
    ) -> Optional[SpeechCandidate]:
        """Chọn ứng viên dự phòng đầu tiên vượt qua kiểm định trực tiếp trên kho tri thức hiện hành.

        Args:
            verifier: Cổng kiểm chứng tri thức P05 hiện hành (`KnowledgeVerifierPort`).
            candidates: Danh sách ứng viên dự phòng theo thứ tự ưu tiên.
            verified_at: Mốc thời gian kiểm định tùy chọn (hữu ích cho chạy với `VirtualClock`).
            tenant_id: Bộ lọc tùy chọn chỉ nhận fallback khớp đúng `tenant_id`.
            session_id: Bộ lọc tùy chọn chỉ nhận fallback khớp đúng `session_id`.
            session_epoch: Bộ lọc tùy chọn chỉ nhận fallback khớp đúng `session_epoch`.
            require_empty_covered_topics: Nếu `True`, chỉ chọn fallback không tự đánh dấu phủ topic.

        Returns:
            Optional[SpeechCandidate]: Ứng viên đã `VERIFIED` sẵn sàng phát TTS, hoặc `None` nếu
                không có ứng viên hợp lệ nào (kích hoạt `SAFE_ABORT_NO_CANDIDATE` / P04 safe scene).
        """
        for candidate in candidates:
            # Chỉ cho phép ứng viên được đánh dấu rõ ràng là fallback đã duyệt trước.
            if candidate.origin != CandidateOrigin.PREAPPROVED_FALLBACK:
                continue
            if tenant_id is not None and candidate.tenant_id != tenant_id:
                continue
            if session_id is not None and candidate.session_id != session_id:
                continue
            if session_epoch is not None and candidate.session_epoch != session_epoch:
                continue
            if require_empty_covered_topics and candidate.proposed_coverage.covered_topic_ids:
                continue

            fresh_draft = _reset_candidate_to_draft(candidate)
            result = verifier.verify_candidate(fresh_draft, verified_at=verified_at)
            if (
                result.status == CandidateVerificationStatus.VERIFIED
                and result.candidate.is_ready_for_tts()
            ):
                return result.candidate

        # Fail-closed: không bao giờ trả về fallback lỗi thời hoặc chưa qua kiểm định.
        return None
