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

import json
import os
import time
from collections.abc import Mapping
from typing import Any, Final, Optional, Protocol, TypeVar, runtime_checkable

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from p06.providers.base import (
    DEFAULT_TIMEOUT_SEC,
    GenerationRequest,
    GenerationResult,
    LLMProvider,
    ProviderAuthError,
    ProviderConfigError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTelemetry,
    ProviderTier,
    ProviderTimeoutError,
    ProviderTransportError,
    StrictNonNegFloat,
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
DEFAULT_GEMINI_BASE_URL: Final[str] = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_ALLOWED_CLASSIFICATIONS: Final[tuple[str, ...]] = (
    "SYNTHETIC",
    "PUBLIC_APPROVED",
)
_PLACEHOLDER_MODEL_PREFIXES: Final[tuple[str, ...]] = ("TBD", "PLACEHOLDER")
_ALLOWED_THINKING_LEVELS: Final[frozenset[str]] = frozenset({"MINIMAL", "LOW", "MEDIUM", "HIGH"})
_HTTP_OK: Final[int] = 200
_MAX_ERROR_BODY_CHARS: Final[int] = 240
_GEMINI_ALLOWED_SCHEMA_KEYS: Final[frozenset[str]] = frozenset(
    {
        "type",
        "format",
        "description",
        "nullable",
        "enum",
        "items",
        "properties",
        "required",
        "minimum",
        "maximum",
        "minItems",
        "maxItems",
        "anyOf",
        "propertyOrdering",
    }
)


def _sanitize_gemini_response_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Chuyển đổi Pydantic JSON Schema sang tập con OpenAPI 3.0 tương thích Gemini `responseSchema`."""
    defs: dict[str, Any] = {}
    for defs_key in ("$defs", "definitions"):
        raw_defs = schema.get(defs_key)
        if isinstance(raw_defs, Mapping):
            for k, v in raw_defs.items():
                if isinstance(v, Mapping):
                    defs[str(k)] = dict(v)

    def _clean(node: Any, seen_refs: frozenset[str] = frozenset()) -> Any:
        if isinstance(node, list):
            return [_clean(item, seen_refs) for item in node]
        if not isinstance(node, Mapping):
            return node

        working = dict(node)
        ref = working.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/"):
            ref_name = ref.rsplit("/", 1)[-1]
            if ref_name in defs and ref_name not in seen_refs:
                resolved = dict(defs[ref_name])
                for key, val in working.items():
                    if key != "$ref" and key not in resolved:
                        resolved[key] = val
                return _clean(resolved, seen_refs | {ref_name})

        # Chuyển anyOf chứa null (Optional[T] trong Pydantic v2) thành nullable=True.
        any_of = working.get("anyOf")
        if isinstance(any_of, list):
            non_null = [
                opt
                for opt in any_of
                if not (isinstance(opt, Mapping) and opt.get("type") == "null")
            ]
            has_null = len(non_null) < len(any_of)
            if len(non_null) == 1 and isinstance(non_null[0], Mapping):
                cleaned_inner = _clean(non_null[0], seen_refs)
                if isinstance(cleaned_inner, dict) and has_null:
                    cleaned_inner["nullable"] = True
                return cleaned_inner

        out: dict[str, Any] = {}
        if "const" in working and "enum" not in working:
            out["enum"] = [working["const"]]

        node_type = working.get("type")
        if (
            node_type == "integer"
            and isinstance(working.get("exclusiveMinimum"), int)
            and not isinstance(working.get("exclusiveMinimum"), bool)
            and "minimum" not in working
        ):
            out["minimum"] = working["exclusiveMinimum"] + 1
        if (
            node_type == "integer"
            and isinstance(working.get("exclusiveMaximum"), int)
            and not isinstance(working.get("exclusiveMaximum"), bool)
            and "maximum" not in working
        ):
            out["maximum"] = working["exclusiveMaximum"] - 1

        for key, value in working.items():
            if key not in _GEMINI_ALLOWED_SCHEMA_KEYS:
                continue
            if key == "properties" and isinstance(value, Mapping):
                out["properties"] = {
                    str(prop_k): _clean(prop_v, seen_refs)
                    for prop_k, prop_v in value.items()
                }
            elif key == "items":
                out["items"] = _clean(value, seen_refs)
            elif key == "anyOf" and isinstance(value, list):
                out["anyOf"] = [_clean(opt, seen_refs) for opt in value]
            else:
                out[key] = _clean(value, seen_refs)
        return out

    cleaned = _clean(schema)
    return cleaned if isinstance(cleaned, dict) else {}


class GeminiRawResponse(BaseModel):
    """Phản hồi thô chuẩn hóa trả về từ adapter/client thực thi Gemini API.

    Attributes:
        raw_text: Chuỗi JSON thô do mô hình Gemini trả về.
        input_tokens: Số token đầu vào đo được từ `usage_metadata` (hoặc `None` nếu thiếu).
        output_tokens: Số token đầu ra đo được từ `usage_metadata` (hoặc `None` nếu thiếu).
        thinking_tokens: Số token suy luận nội bộ (`thoughtsTokenCount`) nếu có.
        finish_reason: Lý do kết thúc sinh văn bản từ Gemini (mặc định `'STOP'`).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    raw_text: str
    input_tokens: Optional[StrictNonNegInt] = None
    output_tokens: Optional[StrictNonNegInt] = None
    thinking_tokens: Optional[StrictNonNegInt] = None
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
    thinking_budget: Optional[StrictNonNegInt] = None
    thinking_level: OptionalNonBlankStr = None
    min_request_interval_sec: StrictNonNegFloat = 0.0
    timeout_sec: StrictPositiveFloat = DEFAULT_TIMEOUT_SEC

    @model_validator(mode="before")
    @classmethod
    def _normalize_thinking_level(cls, data: Any) -> Any:
        """Chuẩn hóa `thinking_level` sang chữ hoa trước khi kiểm định."""
        if isinstance(data, Mapping) and isinstance(data.get("thinking_level"), str):
            copied = dict(data)
            stripped = copied["thinking_level"].strip()
            copied["thinking_level"] = stripped.upper() if stripped else stripped
            return copied
        return data

    @model_validator(mode="after")
    def validate_thinking_config(self) -> GeminiProviderConfig:
        """Kiểm định tham số thinking tương thích Gemini 2.5 (`thinkingBudget`) vs 3.x (`thinkingLevel`)."""
        if self.thinking_budget is not None and self.thinking_level is not None:
            raise ValueError(
                "Không được cấu hình đồng thời cả thinking_budget (Gemini 2.5) "
                "và thinking_level (Gemini 3.x)."
            )
        if self.thinking_level is not None and self.thinking_level not in _ALLOWED_THINKING_LEVELS:
            raise ValueError(
                f"thinking_level '{self.thinking_level}' không hợp lệ. "
                f"Chỉ chấp nhận: {sorted(_ALLOWED_THINKING_LEVELS)}."
            )
        return self


class GeminiRestClient(GeminiClientProtocol):
    """Client REST chuẩn dùng `httpx.Client` gọi endpoint `generateContent` của Gemini API.

    Lý do thiết kế:
        Không mở kết nối mạng trong `__init__` và đọc khóa API lười từ biến môi trường khi gọi;
        đồng thời ánh xạ `401/403 -> ProviderAuthError`, `429 -> ProviderRateLimitError`,
        `timeout -> ProviderTimeoutError`, hỗ trợ `thinkingLevel`/`thinkingBudget`, pacing
        theo RPM và trần cứng `max_requests` liên phiên.
    """

    def __init__(
        self,
        *,
        api_key_env: str = DEFAULT_GEMINI_API_KEY_ENV,
        base_url: str = DEFAULT_GEMINI_BASE_URL,
        thinking_budget: Optional[int] = None,
        thinking_level: Optional[str] = None,
        min_request_interval_sec: float = 0.0,
        max_requests: Optional[int] = None,
        stop_on_rate_limit: bool = True,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._api_key_env = api_key_env
        self._base_url = base_url.rstrip("/")
        self._thinking_budget = thinking_budget
        self._thinking_level = (
            thinking_level.strip().upper()
            if isinstance(thinking_level, str) and thinking_level.strip()
            else None
        )
        self._min_request_interval_sec = max(0.0, float(min_request_interval_sec))
        self._max_requests = max_requests
        self._stop_on_rate_limit = stop_on_rate_limit
        self._http_client = http_client
        self._requests_attempted: int = 0
        self._last_request_start_monotonic: Optional[float] = None
        self._rate_limited: bool = False
        self._last_response_headers: dict[str, str] = {}

    @property
    def requests_attempted(self) -> int:
        """Tổng số yêu cầu HTTP thật đã bắt đầu gửi qua client này."""
        return self._requests_attempted

    @property
    def rate_limited(self) -> bool:
        """`True` nếu client từng gặp HTTP 429 trong phiên hiện tại."""
        return self._rate_limited

    @property
    def last_response_headers(self) -> dict[str, str]:
        """Các HTTP response header an toàn (đã lọc khóa) từ lần gọi gần nhất."""
        return dict(self._last_response_headers)

    def _require_api_key(self) -> str:
        api_key = os.environ.get(self._api_key_env)
        if not isinstance(api_key, str) or not api_key.strip():
            raise ProviderAuthError(
                f"Thiếu khóa xác thực Gemini tại biến môi trường '{self._api_key_env}'."
            )
        return api_key.strip()

    def _preflight_and_pace(self) -> None:
        """Kiểm tra rào rate-limit/budget toàn cục và giãn nhịp giữa hai request liên tiếp."""
        if self._stop_on_rate_limit and self._rate_limited:
            raise ProviderRateLimitError(
                "Đã dừng an toàn sau lỗi HTTP 429 trước đó; không gửi thêm request."
            )
        if self._max_requests is not None and self._requests_attempted >= self._max_requests:
            raise ProviderConfigError(
                f"GLOBAL_REQUEST_BUDGET_EXCEEDED: Đã chạm trần {self._max_requests} API requests."
            )
        if self._min_request_interval_sec > 0.0 and self._last_request_start_monotonic is not None:
            elapsed = time.monotonic() - self._last_request_start_monotonic
            wait_sec = self._min_request_interval_sec - elapsed
            if wait_sec > 0.0:
                time.sleep(wait_sec)
        self._requests_attempted += 1
        self._last_request_start_monotonic = time.monotonic()

    @staticmethod
    def _extract_safe_headers(response: httpx.Response) -> dict[str, str]:
        safe: dict[str, str] = {}
        for k, v in response.headers.items():
            kl = k.lower()
            if kl.startswith("x-ratelimit") or kl in {"retry-after", "date", "content-type"}:
                safe[kl] = v
        return safe

    def check_model_metadata(self, model_id: str, timeout_sec: float = 15.0) -> dict[str, Any]:
        """Kiểm tra metadata model thực tế từ Gemini `/models/{model_id}` dưới các rào ngân sách."""
        api_key = self._require_api_key()
        self._preflight_and_pace()
        url = f"{self._base_url}/models/{model_id}"
        headers = {"x-goog-api-key": api_key}
        try:
            if self._http_client is not None:
                response = self._http_client.get(url, headers=headers, timeout=timeout_sec)
            else:
                with httpx.Client(timeout=timeout_sec) as client:
                    response = client.get(url, headers=headers)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"Quá thời gian chờ kiểm tra metadata model '{model_id}' ({timeout_sec}s)."
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderTransportError(
                f"Lỗi kết nối HTTP khi kiểm tra metadata model '{model_id}': {type(exc).__name__}."
            ) from exc

        self._last_response_headers = self._extract_safe_headers(response)
        if response.status_code in (401, 403):
            raise ProviderAuthError(
                f"Gemini API từ chối xác thực (HTTP {response.status_code}) khi kiểm tra model '{model_id}'."
            )
        if response.status_code == 429:
            self._rate_limited = True
            raise ProviderRateLimitError(
                f"Gemini API vượt giới hạn tần suất hoặc hạn mức (HTTP 429) cho model '{model_id}'."
            )
        if response.status_code == 404:
            raise ProviderConfigError(
                f"Model '{model_id}' không tồn tại hoặc không khả dụng (HTTP 404)."
            )
        if response.status_code != _HTTP_OK:
            snippet = response.text[:_MAX_ERROR_BODY_CHARS].strip()
            raise ProviderTransportError(
                f"Gemini API trả về HTTP {response.status_code} khi kiểm tra model '{model_id}': {snippet}"
            )
        try:
            body = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise ProviderTransportError(
                f"Phản hồi metadata Gemini không phải JSON hợp lệ: {type(exc).__name__}."
            ) from exc
        return {
            "name": body.get("name"),
            "displayName": body.get("displayName"),
            "version": body.get("version"),
            "inputTokenLimit": body.get("inputTokenLimit"),
            "outputTokenLimit": body.get("outputTokenLimit"),
            "supportedGenerationMethods": body.get("supportedGenerationMethods", []),
            "response_headers": self.last_response_headers,
        }

    def generate_json(
        self,
        model_id: str,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        sampling: dict[str, Any],
        timeout_sec: float,
    ) -> GeminiRawResponse:
        """Gửi yêu cầu HTTP POST tới Gemini `generateContent` và chuẩn hóa phản hồi."""
        api_key = self._require_api_key()
        self._preflight_and_pace()

        clean_schema = _sanitize_gemini_response_schema(json_schema)
        generation_config: dict[str, Any] = {
            "responseMimeType": "application/json",
            "responseSchema": clean_schema,
        }
        if sampling.get("temperature") is not None:
            generation_config["temperature"] = sampling["temperature"]
        if sampling.get("top_p") is not None:
            generation_config["topP"] = sampling["top_p"]
        if sampling.get("max_tokens") is not None:
            generation_config["maxOutputTokens"] = sampling["max_tokens"]
        if sampling.get("seed") is not None:
            generation_config["seed"] = sampling["seed"]
        if self._thinking_level is not None:
            generation_config["thinkingConfig"] = {"thinkingLevel": self._thinking_level}
        elif self._thinking_budget is not None:
            generation_config["thinkingConfig"] = {"thinkingBudget": self._thinking_budget}

        payload: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": generation_config,
        }
        url = f"{self._base_url}/models/{model_id}:generateContent"
        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        }

        try:
            if self._http_client is not None:
                response = self._http_client.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=timeout_sec,
                )
            else:
                with httpx.Client(timeout=timeout_sec) as client:
                    response = client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"Quá thời gian chờ phản hồi từ Gemini ({timeout_sec}s) cho model '{model_id}'."
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderTransportError(
                f"Lỗi kết nối HTTP tới Gemini API cho model '{model_id}': {type(exc).__name__}."
            ) from exc

        self._last_response_headers = self._extract_safe_headers(response)
        if response.status_code in (401, 403):
            raise ProviderAuthError(
                f"Gemini API từ chối xác thực (HTTP {response.status_code}) cho model '{model_id}'."
            )
        if response.status_code == 429:
            self._rate_limited = True
            raise ProviderRateLimitError(
                f"Gemini API vượt giới hạn tần suất hoặc hạn mức (HTTP 429) cho model '{model_id}'."
            )
        if response.status_code != _HTTP_OK:
            snippet = response.text[:_MAX_ERROR_BODY_CHARS].strip()
            raise ProviderTransportError(
                f"Gemini API trả về HTTP {response.status_code} cho model '{model_id}': {snippet}"
            )

        try:
            body = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise ProviderTransportError(
                f"Phản hồi Gemini API không phải JSON hợp lệ: {type(exc).__name__}."
            ) from exc

        candidates = body.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ProviderTransportError("Phản hồi Gemini API thiếu danh sách 'candidates'.")

        first_candidate = candidates[0] if isinstance(candidates[0], Mapping) else {}
        content = first_candidate.get("content")
        parts = content.get("parts") if isinstance(content, Mapping) else None
        text_segments: list[str] = []
        if isinstance(parts, list):
            for part in parts:
                if isinstance(part, Mapping) and not part.get("thought", False):
                    part_text = part.get("text")
                    if isinstance(part_text, str):
                        text_segments.append(part_text)
        raw_text = "".join(text_segments)

        raw_finish = first_candidate.get("finishReason")
        finish_reason = (
            raw_finish.strip()
            if isinstance(raw_finish, str) and raw_finish.strip()
            else "STOP"
        )

        usage = body.get("usageMetadata")
        in_tok: Optional[int] = None
        out_tok: Optional[int] = None
        think_tok: Optional[int] = None
        if isinstance(usage, Mapping):
            raw_in = usage.get("promptTokenCount")
            raw_out = usage.get("candidatesTokenCount")
            raw_think = usage.get("thoughtsTokenCount")
            if isinstance(raw_in, int) and not isinstance(raw_in, bool) and raw_in >= 0:
                in_tok = raw_in
            if isinstance(raw_out, int) and not isinstance(raw_out, bool) and raw_out >= 0:
                out_tok = raw_out
            if isinstance(raw_think, int) and not isinstance(raw_think, bool) and raw_think >= 0:
                think_tok = raw_think

        return GeminiRawResponse(
            raw_text=raw_text,
            input_tokens=in_tok,
            output_tokens=out_tok,
            thinking_tokens=think_tok,
            finish_reason=finish_reason,
        )


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
        thinking_tokens: Optional[int] = None,
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
            thinking_tokens=thinking_tokens,
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
                thinking_tokens=raw_response.thinking_tokens,
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
