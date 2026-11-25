"""P05 — Tri thức sản phẩm, kiểm chứng tuyên bố (Claims) và Cổng phát ngôn (Publication Gate).

Bộ schema Pydantic v2 tối thiểu phục vụ các thí nghiệm P05-E01..E04 (giai đoạn Stage 03 / PoC).
Lưu ý: Đây là schema phục vụ nghiên cứu trong `experiments/`, CHƯA phải hợp đồng chính thức
được đưa vào production ở `packages/contracts/`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    """Trạng thái phê duyệt của dữ liệu sản phẩm / bằng chứng / claim."""

    DRAFT = "DRAFT"            # Bản nháp mới trích xuất, chưa qua người duyệt
    APPROVED = "APPROVED"      # Đã được người phụ trách duyệt, được phép dùng
    REJECTED = "REJECTED"      # Bị từ chối, không được sử dụng
    SUPERSEDED = "SUPERSEDED"  # Đã bị thay thế bởi phiên bản mới hơn


class OcopStatus(str, Enum):
    """Trạng thái OCOP chỉ-đọc lấy từ P09 (P05 tuyệt đối không tự xác thực OCOP)."""

    PENDING = "PENDING"        # Đang chờ xác minh hồ sơ từ nguồn độc lập
    VERIFIED = "VERIFIED"      # Đã xác minh hợp lệ bởi P09
    EXPIRED = "EXPIRED"        # Chứng nhận OCOP đã hết hạn
    REVOKED = "REVOKED"        # Chứng nhận OCOP đã bị thu hồi
    UNVERIFIED = "UNVERIFIED"  # Chưa có xác minh hợp lệ


class RightsStatus(str, Enum):
    """Trạng thái bản quyền / chấp thuận chỉ-đọc lấy từ P11 (Rights Registry)."""

    ACTIVE = "ACTIVE"    # Quyền đang còn hiệu lực
    EXPIRED = "EXPIRED"  # Quyền đã hết hạn
    REVOKED = "REVOKED"  # Quyền đã bị thu hồi (phải chặn ngay kể cả cache)


class ClaimCategory(str, Enum):
    """Phân loại chính sách cho từng phát ngôn / tuyên bố (claim) về sản phẩm."""

    ALLOWED = "ALLOWED"                                            # Được phép nói khi có bằng chứng
    PROHIBITED = "PROHIBITED"                                      # Cấm phát ngôn (vd: thổi phồng chữa bệnh cho thực phẩm)
    REQUIRES_OFFICIAL_VERIFICATION = "REQUIRES_OFFICIAL_VERIFICATION"  # Phải có xác minh chính thức (vd: OCOP, VSATTP)


class PublicationStatus(str, Enum):
    """Quyết định cuối cùng của Cổng phát ngôn (Publication Gate)."""

    ALLOW = "ALLOW"  # Hợp lệ, cho phép chuyển sang TTS / phát sóng
    BLOCK = "BLOCK"  # Chặn phát ngôn (nguyên tắc fail-closed)


class BlockReason(str, Enum):
    """Mã lý do chi tiết khi Cổng phát ngôn chặn một lời thoại."""

    MISSING_EVIDENCE = "MISSING_EVIDENCE"                  # Thiếu evidence_id hoặc bằng chứng không tồn tại
    UNAPPROVED_FACT = "UNAPPROVED_FACT"                    # Dữ liệu chưa ở trạng thái APPROVED
    PRICE_MISMATCH = "PRICE_MISMATCH"                      # Giá trong lời thoại không khớp tuyệt đối với ProductFact
    CROSS_SKU_VIOLATION = "CROSS_SKU_VIOLATION"            # Dẫn chứng thuộc SKU khác với SKU đang nói
    PROHIBITED_CLAIM = "PROHIBITED_CLAIM"                  # Chứa nội dung / công dụng bị cấm (R17)
    OCOP_NOT_VERIFIED = "OCOP_NOT_VERIFIED"                # Nhắc đến OCOP khi P09 chưa xác nhận VERIFIED (R16)
    FOOD_SAFETY_UNVERIFIED = "FOOD_SAFETY_UNVERIFIED"      # Chưa đạt điều kiện an toàn thực phẩm áp dụng
    RIGHTS_INVALID = "RIGHTS_INVALID"                      # Quyền sử dụng tài sản đã hết hạn hoặc bị thu hồi (R09)
    STALE_KNOWLEDGE_VERSION = "STALE_KNOWLEDGE_VERSION"    # Lỗi TOCTOU: dữ liệu sản phẩm/giá đã đổi version mới
    STALE_OCOP_VERSION = "STALE_OCOP_VERSION"              # Lỗi TOCTOU: trạng thái OCOP đã đổi version mới
    STALE_RIGHTS_VERSION = "STALE_RIGHTS_VERSION"          # Lỗi TOCTOU: trạng thái quyền đã đổi version mới
    PROMPT_INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"  # Phát hiện dấu hiệu chèn lệnh (prompt injection)
    TENANT_MISMATCH = "TENANT_MISMATCH"                    # Vi phạm cô lập dữ liệu giữa các merchant/tenant (R10)


class Provenance(BaseModel):
    """Nguồn gốc và dấu vết phê duyệt của dữ liệu (truy vết về tài liệu và người duyệt)."""

    source_id: str = Field(description="Mã tài liệu gốc (PDF, DOCX, bảng thông số...)")
    document_version: str = Field(description="Phiên bản của tài liệu gốc, ví dụ: v1.0")
    extracted_by: str = Field(description="Nguồn trích xuất, ví dụ: 'docling', 'manual', 'synthetic_seed'")
    approved_by: Optional[str] = Field(default=None, description="Người kiểm duyệt xác nhận dữ liệu")
    approved_at: Optional[datetime] = Field(default=None, description="Thời điểm phê duyệt (UTC)")


class ProductFact(BaseModel):
    """Thông số sản phẩm có cấu trúc (nguồn chuẩn tuyệt đối — không bao giờ đoán bằng semantic search)."""

    tenant_id: str
    sku_id: str
    sku_name: str
    price_vnd: int = Field(gt=0, description="Giá bán chính thức tính bằng VNĐ")
    weight_display: str = Field(description="Khối lượng / dung tích hiển thị, ví dụ: 500ml")
    expiry_display: str = Field(description="Hạn sử dụng hiển thị")
    origin: str = Field(description="Xuất xứ / vùng nguyên liệu")
    ingredients: list[str] = Field(description="Danh sách thành phần sản phẩm")
    storage_instructions: str = Field(description="Hướng dẫn bảo quản")
    knowledge_version: int = Field(ge=1, description="Số phiên bản tri thức tăng dần mỗi khi cập nhật")
    approval_status: ApprovalStatus
    provenance: Provenance
    valid_from: datetime
    valid_until: Optional[datetime] = None


class EvidenceChunk(BaseModel):
    """Đoạn văn bản bằng chứng gắn chặt theo từng SKU để phục vụ FTS / pgvector."""

    evidence_id: str
    tenant_id: str
    sku_id: str
    section: str = Field(description="Nhóm nội dung, ví dụ: usage, shipping_return, ocop_origin")
    content: str = Field(description="Nội dung bằng chứng đã được kiểm duyệt")
    knowledge_version: int = Field(ge=1)
    approval_status: ApprovalStatus
    provenance: Provenance


class ClaimRegistryEntry(BaseModel):
    """Mục đăng ký tuyên bố (claim) cho biết nội dung nào được phép, cấm hoặc cần xác minh chính thức."""

    claim_id: str
    tenant_id: str
    sku_id: str
    claim_text: str
    category: ClaimCategory
    evidence_ids: list[str] = Field(default_factory=list, description="Danh sách mã bằng chứng đi kèm")
    requires_ocop_verified: bool = Field(
        default=False,
        description="Nếu True, chỉ được phép dùng khi P09 xác nhận OCOP ở trạng thái VERIFIED",
    )
    approval_status: ApprovalStatus
    knowledge_version: int = Field(ge=1)
    provenance: Provenance


class EligibilitySnapshot(BaseModel):
    """Ảnh chụp trạng thái điều kiện bán hàng (chỉ-đọc, do P09 quản lý OCOP/thực phẩm và P11 quản lý quyền)."""

    tenant_id: str
    sku_id: str
    ocop_status: OcopStatus
    ocop_version: int = Field(ge=1)
    ocop_code: Optional[str] = None
    food_safety_verified: bool = Field(description="Đã đạt yêu cầu an toàn thực phẩm áp dụng hay chưa")
    rights_status: RightsStatus
    rights_version: int = Field(ge=1)


class EvidenceBundle(BaseModel):
    """Gói dữ liệu đầu ra của P05 gửi cho P06 (Sales Agent) để sinh lời thoại có căn cứ."""

    bundle_id: str
    tenant_id: str
    sku_id: str
    query: str
    knowledge_version: int = Field(ge=1)
    fact: ProductFact
    chunks: list[EvidenceChunk]
    allowed_claims: list[ClaimRegistryEntry]
    prohibited_claims: list[ClaimRegistryEntry]


class SpeechCandidate(BaseModel):
    """Bản nháp lời thoại do P06 tạo ra, phải qua P05 kiểm chứng trước TTS và kiểm tra lại trước khi phát."""

    candidate_id: str
    tenant_id: str
    session_id: str
    sku_id: str
    text: str
    cited_evidence_ids: list[str] = Field(default_factory=list, description="Các evidence_id mà lời thoại trích dẫn")
    stated_price_vnd: Optional[int] = Field(default=None, description="Mức giá (VNĐ) nếu lời thoại có nhắc đến giá")
    mentions_ocop: bool = Field(default=False, description="Lời thoại có nhắc tới chứng nhận OCOP hay không")
    knowledge_version: int = Field(ge=1, description="Phiên bản tri thức tại thời điểm tạo lời thoại")
    ocop_version: int = Field(ge=1, description="Phiên bản OCOP tại thời điểm tạo lời thoại")
    rights_version: int = Field(ge=1, description="Phiên bản quyền tại thời điểm tạo lời thoại")


class PublicationDecision(BaseModel):
    """Kết quả kiểm duyệt theo nguyên tắc fail-closed trả về từ Cổng phát ngôn P05."""

    candidate_id: str
    status: PublicationStatus
    reasons: list[BlockReason] = Field(default_factory=list)
    details: list[str] = Field(default_factory=list, description="Diễn giải chi tiết lỗi để ghi log / audit")
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    checked_knowledge_version: int
    checked_ocop_version: int
    checked_rights_version: int


class ExperimentManifest(BaseModel):
    """Bản ghi cấu hình và kết quả để tái lập thí nghiệm theo chuẩn experiments/README.md §5."""

    experiment_id: str = Field(description="Mã thí nghiệm, ví dụ: P05-E03")
    run_id: str = Field(description="Mã lần chạy duy nhất")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dataset_source: str = Field(description="Đường dẫn hoặc mã bộ dữ liệu sử dụng")
    is_synthetic: bool = Field(description="True nếu dùng dữ liệu tổng hợp, False nếu dữ liệu thật có quyền")
    environment: dict[str, Any] = Field(default_factory=dict, description="Thông tin CPU/OS/Python/phiên bản thư viện")
    config: dict[str, Any] = Field(default_factory=dict, description="Tham số cấu hình của lần chạy")
    metrics: dict[str, Any] = Field(default_factory=dict, description="Các chỉ số đo được thực tế")
    decision: str = Field(default="INCONCLUSIVE", description="Kết luận: GO / CHANGE / NO-GO / INCONCLUSIVE")
    notes: str = Field(default="", description="Ghi chú giới hạn, lỗi gặp phải và đề xuất bước tiếp theo")
