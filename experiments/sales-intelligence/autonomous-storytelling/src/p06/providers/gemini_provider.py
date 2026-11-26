"""Nhà cung cấp LLM thí nghiệm chính thức (Tier 3: `GeminiAPIProvider`) kèm lớp rào bảo mật.

1. File này giải quyết vấn đề gì?
   Cung cấp cổng gọi Gemini Flash/Flash-Lite cho các thí nghiệm định lượng chính thức
   (`P06-E01..E04`) với rào chắn nghiêm ngặt chống dùng nhầm `model_id` giữ chỗ (`TBD...`),
   chống thiếu khóa xác thực (`GEMINI_API_KEY`) và chống rò rỉ dữ liệu chưa được cấp phép
   (`MERCHANT_REAL`, `PII`) ra external API (`P06-OPEN-1`).
2. Trách nhiệm chính của module là gì?
   Định nghĩa `GeminiRawResponse`, giao thức tiêm phụ thuộc `GeminiClientProtocol`, cấu hình
   `GeminiProviderConfig` và lớp `GeminiAPIProvider` thực thi kiểm định hai lớp (lúc khởi tạo
   và ngay trước khi gửi yêu cầu) rồi parse JSON có cấu trúc qua `LLMProvider`.
3. Module này liên kết với các thành phần nào?
   Kế thừa `LLMProvider` từ `p06.providers.base`; được khởi tạo bởi `ProviderFactory` từ
   `configs/models/gemini_flash.yaml` (kèm override `model_id` đã xác minh khi chạy thật).
4. Input và output chính là gì?
   Input là `GeminiProviderConfig`, `GeminiClientProtocol` (tùy chọn khi test/gắn SDK Phase 5),
   `GenerationRequest` và `output_schema`; Output là `GenerationResult[OutputT]` gắn
   `ProviderTelemetry(tier=FORMAL_EXPERIMENT, is_simulated_metric=False)`.
5. Có những constraints hoặc invariants quan trọng nào?
   - Tuyệt đối KHÔNG ghi giá trị API key vào log, thông báo lỗi hay telemetry.
   - Tuyệt đối KHÔNG âm thầm fallback về `MockLLMProvider` khi thiếu `client`, thiếu key
     hoặc cấu hình đang là `TBD_VERIFY_BEFORE_USE` (luôn fail-explicit).
   - Mọi lượt gọi chỉ chấp nhận `request.data_classification` thuộc danh sách được phép
     trong cấu hình (mặc định `SYNTHETIC`, `PUBLIC_APPROVED`).
"""

from __future__ import annotations

import os
import time
from typing import Any, Final, Optional, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from p06.providers.base import (
    DEFAULT_TIMEOUT_SEC,
    GenerationRequest,
    GenerationResult,
    LLMProvider,
    ProviderAuthError,
    ProviderConfigError,
    ProviderError,
    ProviderTelemetry,
    ProviderTier,
    ProviderTimeoutError,
    ProviderTransportError,
    StrictPositiveFloat,
    TokenUsageSource,
)
from p06.schemas.story import (
    NonBlankStr,
    OptionalNonBlankStr,
    StrictNonNegInt,
)

OutputT = TypeVar("OutputT", bound=BaseModel)

DEFAULT_GEMINI_API_KEY_ENV: Final[str] = "GEMINI_API_KEY"
DEFAULT_ALLOWED_CLASSIFICATIONS: Final[tuple[str, ...]] = (
    "SYNTHETIC",
    "PUBLIC_APPROVED",
)
_PLACEHOLDER_MODEL_PREFIXES: Final[tuple[str, ...]] = ("TBD", "PLACEHOLDER")


class GeminiRawResponse(BaseModel):
    """Phản hồi thô chuẩn hóa trả về từ adapter/client thực thi Gemini API.

    Attributes:
        raw_text: Chuỗi JSON thô do mô hình Gemini trả về.
        input_tokens: Số token đầu vào đo được từ `usage_metadata` (hoặc `None` nếu thiếu).
        output_tokens: Số token đầu ra đo được từ `usage_metadata` (hoặc `None` nếu thiếu).
        finish_reason: Lý do kết thúc sinh văn bản từ Gemini (mặc định `'STOP'`).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    raw_text: str
    input_tokens: Optional[StrictNonNegInt] = None
    output_tokens: Optional[StrictNonNegInt] = None
    finish_reason: NonBlankStr = "STOP"


@runtime_checkable
class GeminiClientProtocol(Protocol):
    """Giao thức tối thiểu cho client gọi Gemini có cấu trúc (hỗ trợ mock offline và SDK thật)."""

    def generate_json(
        self,
        model_id: str,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        sampling: dict[str, Any],
        timeout_sec: float,
    ) -> GeminiRawResponse:
        """Thực thi gọi Gemini sinh JSON khớp `json_schema`."""


class GeminiProviderConfig(BaseModel):
    """Cấu hình cho nhà cung cấp Gemini tầng 3 (`FORMAL_EXPERIMENT`).

    Attributes:
        model_id: Mã mô hình Gemini đã xác minh (từ chối mọi giá trị bắt đầu bằng `TBD`).
        api_key_env: Tên biến môi trường chứa khóa API (KHÔNG lưu giá trị khóa trong config).
        data_classification_allowed: Danh sách nhãn phân loại dữ liệu được phép gửi lên API.
        merchant_dpa_status: Trạng thái rà soát DPA/terms cho dữ liệu merchant.
        sampling: Tham số lấy mẫu mặc định.
        timeout_sec: Thời gian chờ tối đa (giây) cho một yêu cầu gọi API.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: NonBlankStr
    api_key_env: NonBlankStr = DEFAULT_GEMINI_API_KEY_ENV
    data_classification_allowed: tuple[NonBlankStr, ...] = DEFAULT_ALLOWED_CLASSIFICATIONS
    merchant_dpa_status: OptionalNonBlankStr = "TO_VALIDATE"
    sampling: dict[str, Any] = Field(default_factory=dict)
    timeout_sec: StrictPositiveFloat = DEFAULT_TIMEOUT_SEC


class GeminiAPIProvider(LLMProvider):
    """Triển khai `LLMProvider` tầng 3 (`FORMAL_EXPERIMENT`) với các rào bảo mật Fail-Closed.

    Lý do tách biệt khỏi Mock và Ollama:
        `GeminiAPIProvider` là tầng duy nhất dùng cho thí nghiệm định lượng chính thức
        (`P06-E01..E04`). Việc kiểm tra chặt `model_id`, biến môi trường API key và
        `data_classification_allowed` ở cả `__init__` lẫn trước khi gửi bảo đảm không
        bao giờ chạy nhầm cấu hình chưa xác minh hoặc tự ý fallback về `MockLLMProvider`.
    """

    def __init__(
        self,
        config: GeminiProviderConfig,
        client: Optional[GeminiClientProtocol] = None,
    ) -> None:
        """Khởi tạo `GeminiAPIProvider` và chạy ngay rào kiểm định cấu hình/xác thực.

        Args:
            config: Cấu hình `GeminiProviderConfig`.
            client: Adapter tuân thủ `GeminiClientProtocol` (bắt buộc để gọi sinh văn bản;
                nếu `None`, `generate_structured` sẽ báo lỗi cấu hình rõ ràng ở Phase 3).

        Raises:
            ProviderConfigError: Nếu `model_id` rỗng hoặc còn là giá trị giữ chỗ `TBD...`.
            ProviderAuthError: Nếu biến môi trường `config.api_key_env` bị thiếu hoặc rỗng.
        """
        self._config: GeminiProviderConfig = config
        self._client: Optional[GeminiClientProtocol] = client
        self._validate_runtime_guards()

    @property
    def provider_name(self) -> str:
        """Trả về tên chuẩn `'gemini'` của nhà cung cấp tầng 3."""
        return "gemini"

    @property
    def model_id(self) -> str:
        """Trả về mã mô hình Gemini đã xác minh."""
        return self._config.model_id

    @property
    def tier(self) -> ProviderTier:
        """Khẳng định cứng tầng thực thi luôn là `ProviderTier.FORMAL_EXPERIMENT`."""
        return ProviderTier.FORMAL_EXPERIMENT

    def _validate_runtime_guards(self) -> None:
        """Kiểm tra `model_id` đã xác minh và sự tồn tại của API key trong biến môi trường."""
        normalized_model_id = self._config.model_id.strip()
        upper_model_id = normalized_model_id.upper()
        if not normalized_model_id or any(
            upper_model_id.startswith(prefix) for prefix in _PLACEHOLDER_MODEL_PREFIXES
        ):
            raise ProviderConfigError(
                f"Gemini model_id '{self._config.model_id}' chưa được xác minh (giá trị giữ chỗ "
                "TBD/PLACEHOLDER). Phải xác minh exact model ID, quota, pricing và DPA trước khi chạy."
            )

        # Chỉ kiểm tra sự tồn tại khác rỗng; tuyệt đối không lưu hay đưa giá trị khóa vào lỗi/log.
        api_key = os.environ.get(self._config.api_key_env)
        if not isinstance(api_key, str) or not api_key.strip():
            raise ProviderAuthError(
                f"Thiếu khóa xác thực Gemini tại biến môi trường '{self._config.api_key_env}'."
            )

    def _resolve_sampling_params(self, request: GenerationRequest) -> dict[str, Any]:
        """Hợp nhất tham số lấy mẫu từ config và request hiện tại."""
        merged: dict[str, Any] = dict(self._config.sampling)
        if request.temperature is not None:
            merged["temperature"] = request.temperature
        if request.max_tokens is not None:
            merged["max_tokens"] = request.max_tokens
        if request.seed is not None:
            merged["seed"] = request.seed
        return merged

    def _build_telemetry(
        self,
        *,
        latency_ms: float,
        input_tokens: Optional[int],
        output_tokens: Optional[int],
        token_usage_source: TokenUsageSource,
        finish_reason: str,
        raw_response_valid: bool,
        sampling_params: dict[str, Any],
        prompt_version: str,
    ) -> ProviderTelemetry:
        """Tạo `ProviderTelemetry` cho lượt gọi Gemini tầng 3 (không bao giờ đánh dấu giả lập)."""
        return ProviderTelemetry(
            provider_name=self.provider_name,
            model_id=self._config.model_id,
            tier=self.tier,
            latency_ms=latency_ms,
            is_simulated_metric=False,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            token_usage_source=token_usage_source,
            finish_reason=finish_reason,
            raw_response_valid=raw_response_valid,
            sampling_params=sampling_params,
            prompt_version=prompt_version,
        )

    def generate_structured(
        self,
        request: GenerationRequest,
        output_schema: type[OutputT],
    ) -> GenerationResult[OutputT]:
        """Kiểm tra rào bảo mật và gọi Gemini client sinh JSON khớp `output_schema`.

        Args:
            request: Yêu cầu đầu vào kèm nhãn `data_classification`.
            output_schema: Schema Pydantic v2 đích.

        Returns:
            GenerationResult[OutputT]: Đối tượng đã kiểm định cùng telemetry tầng 3.

        Raises:
            ProviderConfigError: Nếu `model_id` chưa xác minh, `data_classification` bị cấm,
                `output_schema` không hợp lệ, hoặc `client is None` (SDK thật chờ Phase 5 `E01-T09`).
            ProviderAuthError: Nếu biến môi trường API key bị thiếu hoặc rỗng trước lúc gửi.
            ProviderTimeoutError: Nếu client gặp lỗi timeout.
            ProviderTransportError: Nếu client gặp lỗi giao vận/SDK.
            MalformedJsonOutputError: Nếu chuỗi trả về không phải JSON hợp lệ.
            SchemaValidationOutputError: Nếu JSON trả về sai cấu trúc `output_schema`.
        """
        # Chạy lại guard trước lúc gửi để bắt trường hợp biến môi trường bị xóa sau khi khởi tạo.
        self._validate_runtime_guards()

        if not (isinstance(output_schema, type) and issubclass(output_schema, BaseModel)):
            raise ProviderConfigError(
                "output_schema bắt buộc phải là một lớp con của Pydantic BaseModel."
            )

        if request.data_classification not in self._config.data_classification_allowed:
            raise ProviderConfigError(
                f"Từ chối gửi dữ liệu phân loại '{request.data_classification}' lên Gemini API; "
                f"chỉ cho phép {list(self._config.data_classification_allowed)}."
            )

        if self._client is None:
            raise ProviderConfigError(
                "GeminiAPIProvider chưa được gắn client thực thi (`client=None`): thực thi trực tiếp "
                "qua google-genai SDK đang tắt ở giai đoạn hiện tại và cần binding client đã xác minh "
                "ở Phase 5 (`E01-T09`). Không tự động fallback về MockLLMProvider."
            )

        sampling_params = self._resolve_sampling_params(request)
        json_schema = output_schema.model_json_schema()
        start_ts = time.perf_counter()

        try:
            raw_response = self._client.generate_json(
                model_id=self._config.model_id,
                system_prompt=request.system_prompt,
                user_prompt=request.user_prompt,
                json_schema=json_schema,
                sampling=sampling_params,
                timeout_sec=self._config.timeout_sec,
            )
        except ProviderError as exc:
            latency_ms = max(0.0, (time.perf_counter() - start_ts) * 1000.0)
            if exc.telemetry is not None:
                raise
            telemetry = self._build_telemetry(
                latency_ms=latency_ms,
                input_tokens=None,
                output_tokens=None,
                token_usage_source=TokenUsageSource.UNAVAILABLE,
                finish_reason="provider_error",
                raw_response_valid=False,
                sampling_params=sampling_params,
                prompt_version=request.prompt_version,
            )
            raise type(exc)(str(exc), telemetry=telemetry) from exc
        except TimeoutError as exc:
            latency_ms = max(0.0, (time.perf_counter() - start_ts) * 1000.0)
            raise ProviderTimeoutError(
                f"Quá thời gian chờ phản hồi từ Gemini ({self._config.timeout_sec}s).",
                telemetry=self._build_telemetry(
                    latency_ms=latency_ms,
                    input_tokens=None,
                    output_tokens=None,
                    token_usage_source=TokenUsageSource.UNAVAILABLE,
                    finish_reason="timeout",
                    raw_response_valid=False,
                    sampling_params=sampling_params,
                    prompt_version=request.prompt_version,
                ),
            ) from exc
        except Exception as exc:
            latency_ms = max(0.0, (time.perf_counter() - start_ts) * 1000.0)
            # Chỉ ghi loại ngoại lệ, tránh vô tình in thông điệp thô có thể chứa header xác thực.
            raise ProviderTransportError(
                f"Lỗi giao vận khi gọi Gemini client: {type(exc).__name__}.",
                telemetry=self._build_telemetry(
                    latency_ms=latency_ms,
                    input_tokens=None,
                    output_tokens=None,
                    token_usage_source=TokenUsageSource.UNAVAILABLE,
                    finish_reason="transport_error",
                    raw_response_valid=False,
                    sampling_params=sampling_params,
                    prompt_version=request.prompt_version,
                ),
            ) from exc

        latency_ms = max(0.0, (time.perf_counter() - start_ts) * 1000.0)
        if not isinstance(raw_response, GeminiRawResponse):
            raise ProviderTransportError(
                "Gemini client trả về kiểu không khớp GeminiRawResponse.",
                telemetry=self._build_telemetry(
                    latency_ms=latency_ms,
                    input_tokens=None,
                    output_tokens=None,
                    token_usage_source=TokenUsageSource.UNAVAILABLE,
                    finish_reason="invalid_client_response",
                    raw_response_valid=False,
                    sampling_params=sampling_params,
                    prompt_version=request.prompt_version,
                ),
            )

        if raw_response.input_tokens is not None and raw_response.output_tokens is not None:
            input_tokens: Optional[int] = raw_response.input_tokens
            output_tokens: Optional[int] = raw_response.output_tokens
            token_source = TokenUsageSource.MEASURED
        else:
            input_tokens = None
            output_tokens = None
            token_source = TokenUsageSource.UNAVAILABLE

        def _telemetry_for(valid: bool) -> ProviderTelemetry:
            return self._build_telemetry(
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                token_usage_source=token_source,
                finish_reason=raw_response.finish_reason,
                raw_response_valid=valid,
                sampling_params=sampling_params,
                prompt_version=request.prompt_version,
            )

        parsed = self._parse_and_validate_json(
            raw_response.raw_text,
            output_schema,
            _telemetry_for,
        )
        return GenerationResult[OutputT](
            parsed_output=parsed,
            raw_text=raw_response.raw_text,
            telemetry=_telemetry_for(True),
        )
