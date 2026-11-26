"""Nhà cung cấp LLM giả lập tất định (Tier 1: `MockLLMProvider`) cho kiểm thử ngoại tuyến.

1. File này giải quyết vấn đề gì?
   Cho phép chạy toàn bộ unit test, contract test và kiểm thử vòng lặp retry/bounded rewrite
   của LangGraph hoàn toàn offline, tức thì (không sleep, không gọi mạng, không cần API key)
   với đầu ra tất định 100%.
2. Trách nhiệm chính của module là gì?
   Định nghĩa `MockBehavior`, `MockResponseStep` và lớp `MockLLMProvider` hỗ trợ hàng đợi
   phản hồi tuần tự (`response_sequence`), phản hồi theo khóa (`keyed_responses`), chọn biến thể
   tất định theo `seed` bằng `hashlib.sha256`, và mô phỏng đầy đủ các kịch bản lỗi.
3. Module này liên kết với các thành phần nào?
   Kế thừa `LLMProvider` từ `p06.providers.base`; được khởi tạo qua `ProviderFactory` từ
   `configs/models/mock.yaml` hoặc trực tiếp trong `tests/`.
4. Input và output chính là gì?
   Input là `GenerationRequest` và `output_schema`; Output là `GenerationResult[OutputT]` gắn
   `ProviderTelemetry(tier=UNIT_TEST, is_simulated_metric=True, token_usage_source=SIMULATED)`,
   hoặc ném ra các ngoại lệ `ProviderError` tương ứng khi giả lập lỗi / cạn hàng đợi.
5. Có những constraints hoặc invariants quan trọng nào?
   - Tuyệt đối KHÔNG tự động bịa ra payload hợp lệ khi chưa cấu hình hoặc đã cạn `deque`
     (phải ném `ProviderError` tường minh).
   - Tuyệt đối KHÔNG dùng `time.sleep` hay `hash()` tích hợp của Python (vốn đổi theo `PYTHONHASHSEED`).
   - Kết quả từ `MockLLMProvider` chỉ chứng minh logic trạng thái/hợp đồng, KHÔNG BAO GIỜ
     là bằng chứng chất lượng tiếng Việt hay năng lực sinh của LLM thật (`P06-OPEN-1`).
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from enum import Enum
from typing import Any, Final, Mapping, Optional, Sequence, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from p06.providers.base import (
    GenerationRequest,
    GenerationResult,
    LLMProvider,
    MalformedJsonOutputError,
    ProviderConfigError,
    ProviderError,
    ProviderTelemetry,
    ProviderTier,
    ProviderTimeoutError,
    ProviderTransportError,
    SchemaValidationOutputError,
    StrictNonNegFloat,
    TokenUsageSource,
)
from p06.schemas.story import NonBlankStr, OptionalNonBlankStr, StrictNonNegInt

OutputT = TypeVar("OutputT", bound=BaseModel)

DEFAULT_MOCK_MODEL_ID: Final[str] = "deterministic-mock-v0.1"
DEFAULT_MOCK_LATENCY_MS: Final[float] = 1.5
DEFAULT_MOCK_INPUT_TOKENS: Final[int] = 120
DEFAULT_MOCK_OUTPUT_TOKENS: Final[int] = 45
DEFAULT_MOCK_FINISH_REASON: Final[str] = "mock_stop"
_DEFAULT_MALFORMED_PAYLOAD: Final[str] = "{malformed_json_from_mock"
_DEFAULT_INVALID_SCHEMA_PAYLOAD: Final[str] = '{"_mock_invalid_schema": true}'


class MockBehavior(str, Enum):
    """Các hành vi mô phỏng được hỗ trợ cho từng bước phản hồi của `MockLLMProvider`.

    Attributes:
        VALID_JSON: Trả về JSON hợp lệ theo `payload` và kiểm định qua `output_schema`.
        MALFORMED_JSON: Mô phỏng LLM sinh chuỗi vỡ cú pháp JSON (`MalformedJsonOutputError`).
        INVALID_SCHEMA: Mô phỏng JSON đúng cú pháp nhưng sai trường/kiểu (`SchemaValidationOutputError`).
        TIMEOUT: Mô phỏng hết thời gian chờ (`ProviderTimeoutError`).
        PROVIDER_FAILURE: Mô phỏng lỗi kết nối hoặc dịch vụ phía provider (`ProviderTransportError`).
    """

    VALID_JSON = "VALID_JSON"
    MALFORMED_JSON = "MALFORMED_JSON"
    INVALID_SCHEMA = "INVALID_SCHEMA"
    TIMEOUT = "TIMEOUT"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"


class MockResponseStep(BaseModel):
    """Một bước phản hồi được lập trình trước cho `MockLLMProvider`.

    Attributes:
        behavior: Kịch bản thành công hoặc loại lỗi cần mô phỏng ở lượt gọi này.
        payload: Dữ liệu JSON (dạng `dict` hoặc `str`) dùng cho bước này.
        latency_ms: Độ trễ giả lập tính bằng ms (chỉ ghi vào telemetry, KHÔNG sleep thật).
        input_tokens: Số token đầu vào giả lập.
        output_tokens: Số token đầu ra giả lập.
        finish_reason: Lý do kết thúc giả lập ghi vào telemetry.
        error_message: Thông điệp lỗi tùy chỉnh khi mô phỏng `TIMEOUT`/`PROVIDER_FAILURE`.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    behavior: MockBehavior
    payload: Optional[Union[dict[str, Any], str]] = None
    latency_ms: StrictNonNegFloat = DEFAULT_MOCK_LATENCY_MS
    input_tokens: StrictNonNegInt = DEFAULT_MOCK_INPUT_TOKENS
    output_tokens: StrictNonNegInt = DEFAULT_MOCK_OUTPUT_TOKENS
    finish_reason: NonBlankStr = DEFAULT_MOCK_FINISH_REASON
    error_message: OptionalNonBlankStr = None


class MockLLMProvider(LLMProvider):
    """Triển khai `LLMProvider` tầng 1 (`UNIT_TEST`) hoàn toàn tất định và ngoại tuyến.

    Lý do tách biệt khỏi Ollama/Gemini:
        `MockLLMProvider` luôn gắn `tier=ProviderTier.UNIT_TEST`, `is_simulated_metric=True`,
        và `token_usage_source=TokenUsageSource.SIMULATED` trên cả kết quả hợp lệ lẫn ngoại lệ,
        nhờ đó tầng đánh giá không bao giờ nhầm số liệu mô phỏng với kết quả thí nghiệm thật.
    """

    def __init__(
        self,
        model_id: str = DEFAULT_MOCK_MODEL_ID,
        response_sequence: Optional[Sequence[MockResponseStep]] = None,
        keyed_responses: Optional[Mapping[str, Sequence[MockResponseStep]]] = None,
        seed: Optional[int] = None,
        seeded_variants: Optional[Sequence[MockResponseStep]] = None,
        seeded_variants_by_schema: Optional[Mapping[str, Sequence[MockResponseStep]]] = None,
    ) -> None:
        """Khởi tạo `MockLLMProvider` với các kịch bản phản hồi được khai báo tường minh.

        Args:
            model_id: Tên định danh mô hình giả lập (lấy từ `mock.yaml` hoặc mặc định).
            response_sequence: Chuỗi bước phản hồi tiêu thụ tuần tự qua `deque` cho test retry.
            keyed_responses: Bản đồ các hàng đợi bước phản hồi theo `fixture_key` hoặc tên schema.
            seed: Hạt giống tất định dùng với `hashlib.sha256` khi chọn từ `seeded_variants`.
            seeded_variants: Tập các bước phản hồi để chọn tất định theo `(seed, request_id, schema)`.
            seeded_variants_by_schema: Tập biến thể theo tên `output_schema.__name__` để chọn tất định.

        Raises:
            ProviderConfigError: Nếu `model_id` rỗng hoặc `seed` sai kiểu (`bool`/`str`).
        """
        if not isinstance(model_id, str) or not model_id.strip():
            raise ProviderConfigError("model_id của MockLLMProvider không được rỗng.")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
            raise ProviderConfigError("seed của MockLLMProvider phải là số nguyên hoặc None.")

        self._model_id: str = model_id.strip()
        self._sequence: deque[MockResponseStep] = deque(response_sequence or ())
        self._has_sequence_configured: bool = response_sequence is not None
        self._keyed_queues: dict[str, deque[MockResponseStep]] = {
            key: deque(steps) for key, steps in (keyed_responses or {}).items()
        }
        self._seed: Optional[int] = seed
        self._seeded_variants: tuple[MockResponseStep, ...] = tuple(seeded_variants or ())
        self._seeded_variants_by_schema: dict[str, tuple[MockResponseStep, ...]] = {
            schema_name: tuple(steps)
            for schema_name, steps in (seeded_variants_by_schema or {}).items()
            if steps
        }

    @property
    def provider_name(self) -> str:
        """Trả về tên chuẩn `'mock'` của nhà cung cấp tầng 1."""
        return "mock"

    @property
    def model_id(self) -> str:
        """Trả về mã mô hình giả lập đã cấu hình."""
        return self._model_id

    @property
    def tier(self) -> ProviderTier:
        """Khẳng định cứng tầng thực thi luôn là `ProviderTier.UNIT_TEST`."""
        return ProviderTier.UNIT_TEST

    def _build_telemetry(
        self,
        *,
        request: GenerationRequest,
        latency_ms: float,
        input_tokens: int,
        output_tokens: int,
        finish_reason: str,
        raw_response_valid: bool,
    ) -> ProviderTelemetry:
        """Tạo `ProviderTelemetry` gắn nhãn mô phỏng thống nhất cho mọi kết quả/lỗi."""
        sampling_params: dict[str, Any] = {}
        effective_seed = request.seed if request.seed is not None else self._seed
        if effective_seed is not None:
            sampling_params["seed"] = effective_seed
        if request.temperature is not None:
            sampling_params["temperature"] = request.temperature
        if request.max_tokens is not None:
            sampling_params["max_tokens"] = request.max_tokens

        return ProviderTelemetry(
            provider_name=self.provider_name,
            model_id=self._model_id,
            tier=self.tier,
            latency_ms=latency_ms,
            is_simulated_metric=True,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            token_usage_source=TokenUsageSource.SIMULATED,
            finish_reason=finish_reason,
            raw_response_valid=raw_response_valid,
            sampling_params=sampling_params,
            prompt_version=request.prompt_version,
        )

    def _select_seeded_variant(
        self,
        request: GenerationRequest,
        output_schema: type[BaseModel],
        variants: Optional[Sequence[MockResponseStep]] = None,
    ) -> MockResponseStep:
        """Chọn một `MockResponseStep` tất định từ tập biến thể bằng SHA-256.

        Lý do dùng `hashlib.sha256` thay vì `hash()` tích hợp của Python:
            Hàm `hash()` của Python bị ngẫu nhiên hóa giữa các tiến trình bởi `PYTHONHASHSEED`,
            làm mất tính tái lập của kiểm thử; `SHA-256` bảo đảm cùng `(seed, request_id, schema)`
            luôn chọn đúng một biến thể trên mọi máy và mọi phiên bản Python.
        """
        pool = variants if variants is not None else self._seeded_variants
        effective_seed = request.seed if request.seed is not None else self._seed
        seed_material = f"{effective_seed}:{request.request_id}:{output_schema.__name__}"
        digest = hashlib.sha256(seed_material.encode("utf-8")).digest()
        index = int.from_bytes(digest[:8], byteorder="big", signed=False) % len(pool)
        return pool[index]

    def _resolve_next_step(
        self,
        request: GenerationRequest,
        output_schema: type[BaseModel],
    ) -> MockResponseStep:
        """Lấy bước phản hồi kế tiếp theo thứ tự ưu tiên: fixture_key -> schema -> sequence -> seeded_by_schema -> seeded."""
        fixture_key = request.metadata.get("fixture_key")
        if isinstance(fixture_key, str) and fixture_key in self._keyed_queues:
            queue = self._keyed_queues[fixture_key]
            if not queue:
                telemetry = self._build_telemetry(
                    request=request,
                    latency_ms=0.0,
                    input_tokens=0,
                    output_tokens=0,
                    finish_reason="mock_exhausted",
                    raw_response_valid=False,
                )
                raise ProviderError(
                    f"Hàng đợi mock cho fixture_key='{fixture_key}' đã cạn.",
                    telemetry=telemetry,
                )
            return queue.popleft()

        schema_key = output_schema.__name__
        if schema_key in self._keyed_queues:
            queue = self._keyed_queues[schema_key]
            if not queue:
                telemetry = self._build_telemetry(
                    request=request,
                    latency_ms=0.0,
                    input_tokens=0,
                    output_tokens=0,
                    finish_reason="mock_exhausted",
                    raw_response_valid=False,
                )
                raise ProviderError(
                    f"Hàng đợi mock cho schema '{schema_key}' đã cạn.",
                    telemetry=telemetry,
                )
            return queue.popleft()

        if self._has_sequence_configured:
            if not self._sequence:
                telemetry = self._build_telemetry(
                    request=request,
                    latency_ms=0.0,
                    input_tokens=0,
                    output_tokens=0,
                    finish_reason="mock_exhausted",
                    raw_response_valid=False,
                )
                raise ProviderError(
                    "response_sequence của MockLLMProvider đã cạn; từ chối tự bịa dữ liệu mới.",
                    telemetry=telemetry,
                )
            return self._sequence.popleft()

        schema_variants = self._seeded_variants_by_schema.get(schema_key)
        if schema_variants:
            return self._select_seeded_variant(request, output_schema, variants=schema_variants)

        if self._seeded_variants:
            return self._select_seeded_variant(request, output_schema, variants=self._seeded_variants)

        telemetry = self._build_telemetry(
            request=request,
            latency_ms=0.0,
            input_tokens=0,
            output_tokens=0,
            finish_reason="mock_unconfigured",
            raw_response_valid=False,
        )
        raise ProviderError(
            "MockLLMProvider chưa được cấu hình response_sequence, keyed_responses, "
            "seeded_variants_by_schema hoặc seeded_variants.",
            telemetry=telemetry,
        )

    @staticmethod
    def _serialize_payload(payload: Union[dict[str, Any], str]) -> str:
        """Chuyển `dict` sang chuỗi JSON chuẩn hoặc giữ nguyên `str`."""
        if isinstance(payload, dict):
            return json.dumps(payload, ensure_ascii=False)
        return payload

    def generate_structured(
        self,
        request: GenerationRequest,
        output_schema: type[OutputT],
    ) -> GenerationResult[OutputT]:
        """Thực thi một bước mô phỏng trên `MockLLMProvider` mà không ngủ hay gọi mạng.

        Args:
            request: Yêu cầu sinh dữ liệu đầu vào.
            output_schema: Schema Pydantic v2 dùng để kiểm định đầu ra.

        Returns:
            GenerationResult[OutputT]: Kết quả đã kiểm định kèm telemetry mô phỏng.

        Raises:
            ProviderError: Khi hàng đợi đã cạn hoặc provider chưa được cấu hình.
            ProviderTimeoutError: Khi bước mô phỏng chọn `MockBehavior.TIMEOUT`.
            ProviderTransportError: Khi bước mô phỏng chọn `MockBehavior.PROVIDER_FAILURE`.
            MalformedJsonOutputError: Khi bước mô phỏng tạo JSON vỡ cú pháp.
            SchemaValidationOutputError: Khi bước mô phỏng tạo JSON sai cấu trúc schema.
        """
        step = self._resolve_next_step(request, output_schema)

        def _telemetry_for(valid: bool) -> ProviderTelemetry:
            return self._build_telemetry(
                request=request,
                latency_ms=step.latency_ms,
                input_tokens=step.input_tokens,
                output_tokens=step.output_tokens,
                finish_reason=step.finish_reason,
                raw_response_valid=valid,
            )

        if step.behavior == MockBehavior.TIMEOUT:
            raise ProviderTimeoutError(
                step.error_message or "MockLLMProvider mô phỏng lỗi hết thời gian chờ (TIMEOUT).",
                telemetry=_telemetry_for(False),
            )

        if step.behavior == MockBehavior.PROVIDER_FAILURE:
            raise ProviderTransportError(
                step.error_message
                or "MockLLMProvider mô phỏng lỗi giao vận/dịch vụ (PROVIDER_FAILURE).",
                telemetry=_telemetry_for(False),
            )

        if step.behavior == MockBehavior.MALFORMED_JSON:
            raw_text = (
                step.payload
                if isinstance(step.payload, str)
                else _DEFAULT_MALFORMED_PAYLOAD
            )
            try:
                if isinstance(step.payload, str):
                    self._parse_and_validate_json(raw_text, output_schema, _telemetry_for)
            except SchemaValidationOutputError as exc:
                raise MalformedJsonOutputError(
                    step.error_message
                    or "MockBehavior.MALFORMED_JSON bắt buộc kích hoạt lỗi JSON không hợp lệ.",
                    telemetry=_telemetry_for(False),
                ) from exc
            raise MalformedJsonOutputError(
                step.error_message
                or "MockBehavior.MALFORMED_JSON bắt buộc kích hoạt lỗi JSON không hợp lệ.",
                telemetry=_telemetry_for(False),
            )

        if step.behavior == MockBehavior.INVALID_SCHEMA:
            raw_text = (
                self._serialize_payload(step.payload)
                if step.payload is not None
                else _DEFAULT_INVALID_SCHEMA_PAYLOAD
            )
            self._parse_and_validate_json(raw_text, output_schema, _telemetry_for)
            raise SchemaValidationOutputError(
                step.error_message
                or "MockBehavior.INVALID_SCHEMA bắt buộc kích hoạt lỗi vi phạm schema.",
                telemetry=_telemetry_for(False),
            )

        # Nhánh MockBehavior.VALID_JSON: bắt buộc có payload tường minh, cấm tự bịa nội dung.
        if step.payload is None:
            raise ProviderConfigError(
                "MockBehavior.VALID_JSON yêu cầu payload tường minh, không được để None.",
                telemetry=_telemetry_for(False),
            )

        raw_text = self._serialize_payload(step.payload)
        parsed = self._parse_and_validate_json(raw_text, output_schema, _telemetry_for)
        return GenerationResult[OutputT](
            parsed_output=parsed,
            raw_text=raw_text,
            telemetry=_telemetry_for(True),
        )
