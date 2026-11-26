"""Gói xuất khẩu công khai cho tầng trừu tượng LLM Provider 3 tầng (`p06.providers`).

1. File này giải quyết vấn đề gì?
   Cung cấp điểm nhập thống nhất (`from p06.providers import ...`) cho giao diện trừu tượng,
   ba nhà cung cấp theo tầng (`Mock`, `Ollama CPU`, `Gemini`), các model telemetry và
   `ProviderFactory`.
2. Trách nhiệm chính của module là gì?
   Tái xuất đầy đủ các lớp, enum, hằng số, protocol và hệ phân cấp ngoại lệ qua `__all__`.
3. Module này liên kết với các thành phần nào?
   Tổng hợp từ `base.py`, `mock_provider.py`, `ollama_provider.py`, `gemini_provider.py`,
   và `factory.py`; phục vụ `planning/`, `agent/`, `experiments/` và `tests/`.
4. Input và output chính là gì?
   Không xử lý logic runtime hay gọi mạng khi import; cung cấp không gian tên công khai.
5. Có những constraints hoặc invariants quan trọng nào?
   Không thực hiện kết nối mạng, đọc `.env` ẩn danh hoặc khởi tạo provider mặc định lúc import.
"""

from __future__ import annotations

from p06.providers.base import (
    DEFAULT_TIMEOUT_SEC,
    GenerationRequest,
    GenerationResult,
    LLMProvider,
    MalformedJsonOutputError,
    ProviderAuthError,
    ProviderConfigError,
    ProviderError,
    ProviderTelemetry,
    ProviderTier,
    ProviderTimeoutError,
    ProviderTransportError,
    SENSITIVE_SAMPLING_KEYS,
    SchemaValidationOutputError,
    StructuredOutputError,
    TokenUsageSource,
)
from p06.providers.factory import ProviderFactory
from p06.providers.gemini_provider import (
    GeminiAPIProvider,
    GeminiClientProtocol,
    GeminiProviderConfig,
    GeminiRawResponse,
)
from p06.providers.mock_provider import (
    MockBehavior,
    MockLLMProvider,
    MockResponseStep,
)
from p06.providers.ollama_provider import (
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_TIMEOUT_SEC,
    OllamaLocalProvider,
    OllamaProviderConfig,
)

__all__ = [
    # Constants
    "DEFAULT_OLLAMA_BASE_URL",
    "DEFAULT_OLLAMA_TIMEOUT_SEC",
    "DEFAULT_TIMEOUT_SEC",
    "SENSITIVE_SAMPLING_KEYS",
    # Enums
    "MockBehavior",
    "ProviderTier",
    "TokenUsageSource",
    # Contracts, Telemetry & Protocols
    "GeminiClientProtocol",
    "GeminiProviderConfig",
    "GeminiRawResponse",
    "GenerationRequest",
    "GenerationResult",
    "MockResponseStep",
    "OllamaProviderConfig",
    "ProviderTelemetry",
    # Providers & Factory
    "GeminiAPIProvider",
    "LLMProvider",
    "MockLLMProvider",
    "OllamaLocalProvider",
    "ProviderFactory",
    # Exceptions
    "MalformedJsonOutputError",
    "ProviderAuthError",
    "ProviderConfigError",
    "ProviderError",
    "ProviderTimeoutError",
    "ProviderTransportError",
    "SchemaValidationOutputError",
    "StructuredOutputError",
]
