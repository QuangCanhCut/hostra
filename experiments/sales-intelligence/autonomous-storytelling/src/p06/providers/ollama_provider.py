"""Nhà cung cấp LLM cục bộ qua Ollama HTTP API (Tier 2: `OllamaLocalProvider`).

1. File này giải quyết vấn đề gì?
   Cho phép chạy smoke test toàn luồng LangGraph và kiểm tra khả năng sinh JSON/tiếng Việt
   trực tiếp trên máy CPU-only (ví dụ `qwen3:1.7b`, `qwen3:4b`) qua API `/api/chat` của Ollama
   mà không tốn chi phí API hay gửi dữ liệu ra ngoài.
2. Trách nhiệm chính của module là gì?
   Định nghĩa cấu hình `OllamaProviderConfig` và lớp `OllamaLocalProvider` giao tiếp HTTP
   qua `httpx.Client` (hỗ trợ inject `httpx.MockTransport` trong unit test), ánh xạ lỗi mạng/HTTP
   sang hệ ngoại lệ `ProviderError`, và thu thập telemetry trung thực.
3. Module này liên kết với các thành phần nào?
   Kế thừa `LLMProvider` từ `p06.providers.base`; được khởi tạo qua `ProviderFactory` từ
   `configs/models/ollama_qwen3_1.7b.yaml` và `configs/models/ollama_qwen3_4b.yaml`.
4. Input và output chính là gì?
   Input là `OllamaProviderConfig`, `GenerationRequest` và `output_schema`;
   Output là `GenerationResult[OutputT]` kèm `ProviderTelemetry(tier=LOCAL_SMOKE_TEST,
   is_simulated_metric=False)`.
5. Có những constraints hoặc invariants quan trọng nào?
   - KHÔNG thực hiện bất kỳ cuộc gọi HTTP nào trong `__init__`.
   - Độ trễ chạy trên CPU cục bộ tuyệt đối KHÔNG đại diện cho SLA production và KHÔNG BAO GIỜ
     được gộp chung vào bảng benchmark với `GeminiAPIProvider` (`P06-OPEN-1`).
   - Nếu Ollama không trả về `prompt_eval_count` và `eval_count` hợp lệ, bắt buộc ghi
     `token_usage_source=UNAVAILABLE` và để `None` (cấm bịa `0`).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Final, Optional, TypeVar

import httpx
from pydantic import BaseModel, ConfigDict, Field

from p06.providers.base import (
    GenerationRequest,
    GenerationResult,
    LLMProvider,
    ProviderConfigError,
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
    StrictPositiveInt,
)

OutputT = TypeVar("OutputT", bound=BaseModel)

DEFAULT_OLLAMA_BASE_URL: Final[str] = "http://localhost:11434"
DEFAULT_OLLAMA_BASE_URL_ENV: Final[str] = "OLLAMA_BASE_URL"
DEFAULT_OLLAMA_TIMEOUT_SEC: Final[float] = 120.0
DEFAULT_OLLAMA_HARDWARE_PROFILE: Final[str] = "cpu_only_no_dgpu"
_HTTP_OK: Final[int] = 200
_MAX_ERROR_BODY_CHARS: Final[int] = 240


class OllamaProviderConfig(BaseModel):
    """Cấu hình cho nhà cung cấp Ollama cục bộ tầng 2 (`LOCAL_SMOKE_TEST`).

    Attributes:
        model_id: Tên tag mô hình trong Ollama (ví dụ `qwen3:1.7b`, `qwen3:4b`).
        base_url_env: Tên biến môi trường chứa URL máy chủ Ollama cục bộ.
        quantization: Mức lượng tử hóa thực tế (ví dụ `Q4_K_M` hoặc `TBD_RECORD_ACTUAL_TAG`).
        context_window: Kích thước cửa sổ ngữ cảnh `num_ctx` truyền cho Ollama.
        sampling: Các tham số lấy mẫu mặc định (`temperature`, `top_p`, `max_tokens`, `seed`).
        timeout_sec: Thời gian chờ tối đa (giây) cho một yêu cầu HTTP trên CPU.
        hardware_profile: Hồ sơ phần cứng chạy smoke test để truy vết telemetry.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: NonBlankStr
    base_url_env: NonBlankStr = DEFAULT_OLLAMA_BASE_URL_ENV
    quantization: OptionalNonBlankStr = None
    context_window: Optional[StrictPositiveInt] = None
    sampling: dict[str, Any] = Field(default_factory=dict)
    timeout_sec: StrictPositiveFloat = DEFAULT_OLLAMA_TIMEOUT_SEC
    hardware_profile: NonBlankStr = DEFAULT_OLLAMA_HARDWARE_PROFILE


class OllamaLocalProvider(LLMProvider):
    """Triển khai `LLMProvider` tầng 2 (`LOCAL_SMOKE_TEST`) giao tiếp qua Ollama `/api/chat`.

    Lý do tách biệt khỏi Mock và Gemini:
        Ollama CPU smoke test có phân bố độ trễ và lượng tử hóa cục bộ rất khác cloud API,
        nên mọi telemetry đều gắn `tier=ProviderTier.LOCAL_SMOKE_TEST`, `is_simulated_metric=False`,
        cùng `quantization` và `context_window` để tách bảng phân tích với Gemini.
    """

    def __init__(
        self,
        config: OllamaProviderConfig,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        """Khởi tạo `OllamaLocalProvider` mà KHÔNG thực hiện bất kỳ kết nối mạng nào.

        Args:
            config: Cấu hình `OllamaProviderConfig` đã kiểm định.
            http_client: Client `httpx.Client` tùy chọn (dùng `httpx.MockTransport` khi test).

        Raises:
            ProviderConfigError: Nếu URL đọc từ biến môi trường không dùng scheme `http`/`https`.
        """
        raw_base_url = os.environ.get(config.base_url_env)
        resolved_base_url = (
            raw_base_url.strip()
            if isinstance(raw_base_url, str) and raw_base_url.strip()
            else DEFAULT_OLLAMA_BASE_URL
        ).rstrip("/")

        if not (
            resolved_base_url.startswith("http://")
            or resolved_base_url.startswith("https://")
        ):
            raise ProviderConfigError(
                f"URL Ollama từ biến môi trường '{config.base_url_env}' không hợp lệ: "
                f"'{resolved_base_url}'."
            )

        self._config: OllamaProviderConfig = config
        self._base_url: str = resolved_base_url
        self._http_client: Optional[httpx.Client] = http_client

    @property
    def provider_name(self) -> str:
        """Trả về tên chuẩn `'ollama'` của nhà cung cấp tầng 2."""
        return "ollama"

    @property
    def model_id(self) -> str:
        """Trả về mã mô hình Ollama đã cấu hình."""
        return self._config.model_id

    @property
    def tier(self) -> ProviderTier:
        """Khẳng định cứng tầng thực thi luôn là `ProviderTier.LOCAL_SMOKE_TEST`."""
        return ProviderTier.LOCAL_SMOKE_TEST

    @property
    def base_url(self) -> str:
        """Địa chỉ máy chủ Ollama đã phân giải từ biến môi trường."""
        return self._base_url

    def _resolve_options_and_telemetry_sampling(
        self,
        request: GenerationRequest,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Hợp nhất tham số sampling từ config và request thành `options` cho Ollama và telemetry."""
        telemetry_sampling: dict[str, Any] = dict(self._config.sampling)
        if request.temperature is not None:
            telemetry_sampling["temperature"] = request.temperature
        if request.max_tokens is not None:
            telemetry_sampling["max_tokens"] = request.max_tokens
        if request.seed is not None:
            telemetry_sampling["seed"] = request.seed

        ollama_options: dict[str, Any] = {}
        for key in ("temperature", "top_p", "seed"):
            if key in telemetry_sampling:
                ollama_options[key] = telemetry_sampling[key]
        if "max_tokens" in telemetry_sampling:
            # Ollama dùng khóa `num_predict` thay cho `max_tokens`.
            ollama_options["num_predict"] = telemetry_sampling["max_tokens"]
        if self._config.context_window is not None:
            ollama_options["num_ctx"] = self._config.context_window

        return ollama_options, telemetry_sampling

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
        """Tạo `ProviderTelemetry` trung thực cho lượt gọi Ollama."""
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
            quantization=self._config.quantization,
            context_window=self._config.context_window,
            sampling_params=sampling_params,
            prompt_version=prompt_version,
        )

    def _post_chat(self, payload: dict[str, Any]) -> httpx.Response:
        """Gửi yêu cầu HTTP POST tới `/api/chat` qua client được inject hoặc client tạm thời."""
        endpoint = f"{self._base_url}/api/chat"
        if self._http_client is not None:
            # Không đóng client được caller inject để cho phép tái sử dụng pool kết nối / MockTransport.
            return self._http_client.post(
                endpoint,
                json=payload,
                timeout=self._config.timeout_sec,
            )

        with httpx.Client(timeout=self._config.timeout_sec) as client:
            return client.post(endpoint, json=payload)

    @staticmethod
    def _extract_token_usage(
        body: dict[str, Any],
    ) -> tuple[Optional[int], Optional[int], TokenUsageSource]:
        """Trích xuất số token đo thật từ Ollama; trả `UNAVAILABLE` + `None` nếu thiếu."""
        prompt_eval_count = body.get("prompt_eval_count")
        eval_count = body.get("eval_count")
        has_valid_counts = (
            isinstance(prompt_eval_count, int)
            and not isinstance(prompt_eval_count, bool)
            and prompt_eval_count >= 0
            and isinstance(eval_count, int)
            and not isinstance(eval_count, bool)
            and eval_count >= 0
        )
        if has_valid_counts:
            return prompt_eval_count, eval_count, TokenUsageSource.MEASURED
        return None, None, TokenUsageSource.UNAVAILABLE

    def generate_structured(
        self,
        request: GenerationRequest,
        output_schema: type[OutputT],
    ) -> GenerationResult[OutputT]:
        """Gọi Ollama `/api/chat` với JSON schema cưỡng bức và kiểm định kết quả đầu ra.

        Args:
            request: Yêu cầu sinh dữ liệu đầu vào.
            output_schema: Lớp Pydantic `BaseModel` đích để sinh `format` JSON schema.

        Returns:
            GenerationResult[OutputT]: Kết quả đã kiểm định kèm telemetry thật từ Ollama.

        Raises:
            ProviderConfigError: Nếu `output_schema` không phải `BaseModel`.
            ProviderTimeoutError: Khi quá thời gian chờ `timeout_sec`.
            ProviderTransportError: Khi lỗi kết nối, HTTP khác 200 hoặc body thiếu `message.content`.
            MalformedJsonOutputError: Khi `message.content` không phải JSON hợp lệ.
            SchemaValidationOutputError: Khi JSON trả về không khớp `output_schema`.
        """
        if not (isinstance(output_schema, type) and issubclass(output_schema, BaseModel)):
            raise ProviderConfigError(
                "output_schema bắt buộc phải là một lớp con của Pydantic BaseModel."
            )

        options, telemetry_sampling = self._resolve_options_and_telemetry_sampling(request)
        payload: dict[str, Any] = {
            "model": self._config.model_id,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "stream": False,
            "format": output_schema.model_json_schema(),
            "options": options,
        }

        start_ts = time.perf_counter()
        try:
            response = self._post_chat(payload)
        except httpx.TimeoutException as exc:
            latency_ms = max(0.0, (time.perf_counter() - start_ts) * 1000.0)
            raise ProviderTimeoutError(
                f"Hết thời gian chờ Ollama ({self._config.timeout_sec}s) cho model '{self._config.model_id}': {exc}",
                telemetry=self._build_telemetry(
                    latency_ms=latency_ms,
                    input_tokens=None,
                    output_tokens=None,
                    token_usage_source=TokenUsageSource.UNAVAILABLE,
                    finish_reason="timeout",
                    raw_response_valid=False,
                    sampling_params=telemetry_sampling,
                    prompt_version=request.prompt_version,
                ),
            ) from exc
        except httpx.HTTPError as exc:
            latency_ms = max(0.0, (time.perf_counter() - start_ts) * 1000.0)
            raise ProviderTransportError(
                f"Lỗi kết nối HTTP tới Ollama tại '{self._base_url}': {exc}",
                telemetry=self._build_telemetry(
                    latency_ms=latency_ms,
                    input_tokens=None,
                    output_tokens=None,
                    token_usage_source=TokenUsageSource.UNAVAILABLE,
                    finish_reason="transport_error",
                    raw_response_valid=False,
                    sampling_params=telemetry_sampling,
                    prompt_version=request.prompt_version,
                ),
            ) from exc

        latency_ms = max(0.0, (time.perf_counter() - start_ts) * 1000.0)

        if response.status_code != _HTTP_OK:
            snippet = response.text[:_MAX_ERROR_BODY_CHARS].strip()
            raise ProviderTransportError(
                f"Ollama trả về HTTP {response.status_code} cho model '{self._config.model_id}': {snippet}",
                telemetry=self._build_telemetry(
                    latency_ms=latency_ms,
                    input_tokens=None,
                    output_tokens=None,
                    token_usage_source=TokenUsageSource.UNAVAILABLE,
                    finish_reason=f"http_{response.status_code}",
                    raw_response_valid=False,
                    sampling_params=telemetry_sampling,
                    prompt_version=request.prompt_version,
                ),
            )

        try:
            body = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise ProviderTransportError(
                f"Thân phản hồi HTTP từ Ollama không phải JSON hợp lệ: {exc}",
                telemetry=self._build_telemetry(
                    latency_ms=latency_ms,
                    input_tokens=None,
                    output_tokens=None,
                    token_usage_source=TokenUsageSource.UNAVAILABLE,
                    finish_reason="invalid_http_json",
                    raw_response_valid=False,
                    sampling_params=telemetry_sampling,
                    prompt_version=request.prompt_version,
                ),
            ) from exc

        if not isinstance(body, dict):
            raise ProviderTransportError(
                "Thân phản hồi JSON từ Ollama bắt buộc phải là đối tượng (dict).",
                telemetry=self._build_telemetry(
                    latency_ms=latency_ms,
                    input_tokens=None,
                    output_tokens=None,
                    token_usage_source=TokenUsageSource.UNAVAILABLE,
                    finish_reason="invalid_http_body",
                    raw_response_valid=False,
                    sampling_params=telemetry_sampling,
                    prompt_version=request.prompt_version,
                ),
            )

        message = body.get("message")
        raw_content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(raw_content, str):
            raise ProviderTransportError(
                "Phản hồi Ollama thiếu trường 'message.content' dạng chuỗi.",
                telemetry=self._build_telemetry(
                    latency_ms=latency_ms,
                    input_tokens=None,
                    output_tokens=None,
                    token_usage_source=TokenUsageSource.UNAVAILABLE,
                    finish_reason="missing_message_content",
                    raw_response_valid=False,
                    sampling_params=telemetry_sampling,
                    prompt_version=request.prompt_version,
                ),
            )

        input_tokens, output_tokens, token_source = self._extract_token_usage(body)
        raw_done_reason = body.get("done_reason")
        if isinstance(raw_done_reason, str) and raw_done_reason.strip():
            finish_reason = raw_done_reason.strip()
        elif body.get("done") is True:
            finish_reason = "stop"
        else:
            finish_reason = "unknown"

        def _telemetry_for(valid: bool) -> ProviderTelemetry:
            return self._build_telemetry(
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                token_usage_source=token_source,
                finish_reason=finish_reason,
                raw_response_valid=valid,
                sampling_params=telemetry_sampling,
                prompt_version=request.prompt_version,
            )

        parsed = self._parse_and_validate_json(raw_content, output_schema, _telemetry_for)
        return GenerationResult[OutputT](
            parsed_output=parsed,
            raw_text=raw_content,
            telemetry=_telemetry_for(True),
        )
