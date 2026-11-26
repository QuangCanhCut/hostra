"""Phụ thuộc runtime và ngữ cảnh thực thi từng lượt cho đồ thị LangGraph P06 (`agent/`).

1. File này giải quyết vấn đề gì?
   Giữ toàn bộ phụ thuộc hạ tầng (LLMProvider, KnowledgeVerifierPort, RepetitionDetector, VirtualClock)
   và dữ liệu trung gian của một lượt chạy nằm NGOÀI `AgentState` (`extra="forbid"`).
2. Trách nhiệm chính của module là gì?
   Định nghĩa `GraphRuntimeDeps` (bất biến, kiểm định tham số cấu hình), `TurnExecutionContext`
   (scratchpad nội bộ cho một lượt) và `AgentTurnResult` (DTO đầu ra chuẩn hóa sau `from_graph_result`).
3. Module này liên kết với các thành phần nào?
   Sử dụng `AgentState` (`schemas/state.py`), `SkuEvidenceView` / `CandidateVerificationResult`
   (`adapters/interfaces.py`), `RepetitionCheckResult` (`memory/repetition_detector.py`),
   `ProviderTelemetry` (`providers/base.py`), và được dùng bởi tất cả các node trong `agent/nodes/`.
4. Input và output chính là gì?
   Input là các cổng phụ thuộc tiêm vào từ tầng điều phối/thí nghiệm;
   Output là `AgentTurnResult` gồm `final_state` đã tái kiểm định cùng telemetry và gợi ý chuyển tiếp.
5. Có những constraints hoặc invariants quan trọng nào?
   - Tuyệt đối không đưa client/adapter/clock hay scratchpad vào `AgentState`.
   - `max_chunk_duration_sec` phải hữu hạn, không phải `bool`, nằm trong `(0.0, MAX_CHUNK_DURATION_SEC]`.
   - `AgentTurnResult` dùng `ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from p06.adapters.interfaces import (
    CandidateVerificationResult,
    KnowledgeVerifierPort,
    SkuEvidenceView,
)
from p06.memory.repetition_detector import RepetitionCheckResult, RepetitionDetector
from p06.providers.base import LLMProvider, ProviderTelemetry
from p06.schemas.candidate import SpeechCandidate
from p06.schemas.state import AgentState
from p06.schemas.story import (
    MAX_CHUNK_DURATION_SEC,
    NonBlankStr,
    OptionalNonBlankStr,
    StoryTopic,
)
from p06.simulation.virtual_clock import VirtualClock


@dataclass(frozen=True)
class GraphRuntimeDeps:
    """Tập hợp các phụ thuộc runtime tiêm vào đồ thị LangGraph (nằm ngoài `AgentState`)."""

    llm_provider: LLMProvider
    knowledge_verifier: KnowledgeVerifierPort
    repetition_detector: RepetitionDetector
    fallback_candidates: Sequence[SpeechCandidate]
    clock: VirtualClock
    prompts_dir: Optional[Path] = None
    max_chunk_duration_sec: float = 8.0
    session_rights_version: int = 1
    data_classification: str = "SYNTHETIC"
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        """Kiểm định tính hợp lệ của các tham số cấu hình ngay khi khởi tạo."""
        if (
            isinstance(self.max_chunk_duration_sec, bool)
            or not isinstance(self.max_chunk_duration_sec, (int, float))
            or not math.isfinite(float(self.max_chunk_duration_sec))
        ):
            raise ValueError(
                f"max_chunk_duration_sec phải là số thực hữu hạn, nhận được {self.max_chunk_duration_sec!r}."
            )
        numeric_duration = float(self.max_chunk_duration_sec)
        if not (0.0 < numeric_duration <= MAX_CHUNK_DURATION_SEC):
            raise ValueError(
                f"max_chunk_duration_sec phải nằm trong (0.0, {MAX_CHUNK_DURATION_SEC}], "
                f"nhận được {numeric_duration}."
            )
        if isinstance(self.session_rights_version, bool) or not isinstance(
            self.session_rights_version, int
        ) or self.session_rights_version < 1:
            raise ValueError(
                f"session_rights_version phải là số nguyên >= 1, nhận được {self.session_rights_version!r}."
            )
        if not isinstance(self.data_classification, str) or not self.data_classification.strip():
            raise ValueError("data_classification không được rỗng.")
        if self.seed is not None and (isinstance(self.seed, bool) or not isinstance(self.seed, int)):
            raise ValueError("seed phải là số nguyên hoặc None.")
        # Khóa bản sao tuple bất biến để caller bên ngoài không sửa đổi danh sách fallback giữa chừng.
        object.__setattr__(self, "fallback_candidates", tuple(self.fallback_candidates))
        object.__setattr__(self, "max_chunk_duration_sec", numeric_duration)
        object.__setattr__(self, "data_classification", self.data_classification.strip())


@dataclass
class TurnExecutionContext:
    """Ngữ cảnh chạy tạm thời trong nội bộ một lượt đồ thị, tách rời khỏi `AgentState`."""

    turn_id: str
    sequence_index: int = 0
    active_sku_evidence: Optional[SkuEvidenceView] = None
    selected_topic: Optional[StoryTopic] = None
    excluded_topic_ids: set[str] = field(default_factory=set)
    last_repetition_result: Optional[RepetitionCheckResult] = None
    last_verification_result: Optional[CandidateVerificationResult] = None
    last_failed_draft_text: Optional[str] = None
    non_retryable_failure: Optional[str] = None
    should_terminate: bool = False
    termination_reason: Optional[str] = None
    used_fallback: bool = False
    telemetry_records: list[ProviderTelemetry] = field(default_factory=list)
    prompt_hashes: dict[str, str] = field(default_factory=dict)
    covered_claim_ids: tuple[str, ...] = ()
    next_topic_id_hint: Optional[str] = None
    next_arc_id_hint: Optional[str] = None


class AgentTurnResult(BaseModel):
    """Kết quả hoàn chỉnh sau một lượt thực thi LangGraph qua cổng `AgentState.from_graph_result()`.

    Attributes:
        final_state: Trạng thái `AgentState` cuối lượt đã tái kiểm định toàn vẹn.
        should_terminate: `True` khi không còn chủ đề hợp lệ cho `active_sku_id`.
        termination_reason: Lý do kết thúc sạch nếu `should_terminate=True`.
        telemetry_records: Chuỗi `ProviderTelemetry` của mọi lần gọi LLM trong lượt.
        prompt_hashes: Bảng mã SHA-256 chuẩn hóa LF của các prompt đã dùng trong lượt.
        covered_claim_ids: Danh sách `claim_id` gắn với ứng viên thành công (nếu không fallback).
        next_topic_id_hint: Gợi ý `topic_id` cho lượt tiếp theo (chỉ dùng khi harness nhận ACK).
        next_arc_id_hint: Gợi ý `arc_id` tương ứng cho lượt tiếp theo.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    final_state: AgentState
    should_terminate: StrictBool
    termination_reason: OptionalNonBlankStr = None
    telemetry_records: tuple[ProviderTelemetry, ...] = ()
    prompt_hashes: dict[str, NonBlankStr] = Field(default_factory=dict)
    covered_claim_ids: tuple[NonBlankStr, ...] = ()
    next_topic_id_hint: OptionalNonBlankStr = None
    next_arc_id_hint: OptionalNonBlankStr = None
