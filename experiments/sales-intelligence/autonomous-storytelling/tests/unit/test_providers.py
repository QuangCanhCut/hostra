"""Bộ kiểm thử đơn vị cho tầng trừu tượng LLM Provider 3 tầng (`p06.providers`).

1. File này giải quyết vấn đề gì?
   Xác minh toàn bộ hợp đồng `LLMProvider`, `ProviderTelemetry`, `MockLLMProvider`,
   `OllamaLocalProvider` (qua `httpx.MockTransport`), `GeminiAPIProvider` (qua fake client
   tuân thủ `GeminiClientProtocol`) và `ProviderFactory` hoàn toàn ngoại tuyến.
2. Trách nhiệm chính của module là gì?
   Kiểm tra các bất biến provenance (`is_simulated_metric`, `token_usage_source`), rào chặn
   lộ khóa nhạy cảm, mô phỏng lỗi/retry, ánh xạ lỗi HTTP Ollama, rào `TBD`/API key/phân loại
   dữ liệu của Gemini và tải đầy đủ 4 tệp cấu hình trong `configs/models/*.yaml`.
3. Module này liên kết với các thành phần nào?
   Kiểm thử trực tiếp `p06.providers` và đối chiếu tương thích schema `StoryChunk` từ `p06.schemas`.
4. Input và output chính là gì?
   Input là cấu hình YAML thực tế, request giả lập và mock transport/client;
   Output là kết quả `pytest` tất định 100% không dùng mạng ngoài hay API key thật.
5. Có những constraints hoặc invariants quan trọng nào?
   Không gọi mạng thật, không `time.sleep`, không dùng API key thật và không nới lỏng assertion.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from p06.providers import (
    DEFAULT_OLLAMA_BASE_URL,
    GeminiAPIProvider,
    GeminiProviderConfig,
    GeminiRawResponse,
    GenerationRequest,
    LLMProvider,
    MalformedJsonOutputError,
    MockBehavior,
    MockLLMProvider,
    MockResponseStep,
    OllamaLocalProvider,
    OllamaProviderConfig,
    ProviderAuthError,
    ProviderConfigError,
    ProviderError,
    ProviderFactory,
    ProviderTelemetry,
    ProviderTier,
    ProviderTimeoutError,
    ProviderTransportError,
    SchemaValidationOutputError,
    TokenUsageSource,
)
from p06.schemas import BreakpointType, StoryChunk, StoryChunkRole

P06_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = P06_ROOT / "configs" / "models"


class _DemoOutput(BaseModel):
    """Schema nhỏ gọn phục vụ kiểm thử parse JSON có cấu trúc."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sku_id: str
    pitch_text: str


class _FakeGeminiClient:
    """Client giả tuân thủ `GeminiClientProtocol` dùng cho test ngoại tuyến."""

    def __init__(
        self,
        response: GeminiRawResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self._response = response
        self._error = error
        self.calls: list[dict[str, Any]] = []

    def generate_json(
        self,
        model_id: str,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        sampling: dict[str, Any],
        timeout_sec: float,
    ) -> GeminiRawResponse:
        self.calls.append(
            {
                "model_id": model_id,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "json_schema": json_schema,
                "sampling": sampling,
                "timeout_sec": timeout_sec,
            }
        )
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


def _make_request(
    request_id: str = "req-001",
    data_classification: str = "SYNTHETIC",
    metadata: dict[str, Any] | None = None,
) -> GenerationRequest:
    """Tạo nhanh `GenerationRequest` hợp lệ dùng chung cho các test case."""
    return GenerationRequest(
        request_id=request_id,
        system_prompt="Bạn là trợ lý kể chuyện bán hàng tiếng Việt trung thực.",
        user_prompt="Hãy giới thiệu ngắn về mật ong hoa cà phê Cư M'gar.",
        prompt_version="v0.1",
        data_classification=data_classification,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# 1. Telemetry, Request & Shared Structured Output Validation
# ---------------------------------------------------------------------------


def test_telemetry_rejects_invalid_types_and_provenance_violations() -> None:
    """Kiểm định các bất biến nghiêm ngặt của `ProviderTelemetry`."""
    # Từ chối bool bị ép kiểu thành float trong latency_ms.
    with pytest.raises(ValidationError):
        ProviderTelemetry(
            provider_name="mock",
            model_id="deterministic-mock-v0.1",
            tier=ProviderTier.UNIT_TEST,
            latency_ms=True,  # type: ignore[arg-type]
            is_simulated_metric=True,
            input_tokens=10,
            output_tokens=5,
            token_usage_source=TokenUsageSource.SIMULATED,
            finish_reason="mock_stop",
            raw_response_valid=True,
        )

    # Tầng UNIT_TEST bắt buộc is_simulated_metric=True.
    with pytest.raises(ValidationError):
        ProviderTelemetry(
            provider_name="mock",
            model_id="deterministic-mock-v0.1",
            tier=ProviderTier.UNIT_TEST,
            latency_ms=1.0,
            is_simulated_metric=False,
            input_tokens=10,
            output_tokens=5,
            token_usage_source=TokenUsageSource.SIMULATED,
            finish_reason="mock_stop",
            raw_response_valid=True,
        )

    # Tầng UNIT_TEST không được gắn nhãn MEASURED.
    with pytest.raises(ValidationError):
        ProviderTelemetry(
            provider_name="mock",
            model_id="deterministic-mock-v0.1",
            tier=ProviderTier.UNIT_TEST,
            latency_ms=1.0,
            is_simulated_metric=True,
            input_tokens=10,
            output_tokens=5,
            token_usage_source=TokenUsageSource.MEASURED,
            finish_reason="mock_stop",
            raw_response_valid=True,
        )

    # UNAVAILABLE tuyệt đối không được điền 0 giả cho token counts.
    with pytest.raises(ValidationError):
        ProviderTelemetry(
            provider_name="ollama",
            model_id="qwen3:1.7b",
            tier=ProviderTier.LOCAL_SMOKE_TEST,
            latency_ms=250.0,
            is_simulated_metric=False,
            input_tokens=0,
            output_tokens=None,
            token_usage_source=TokenUsageSource.UNAVAILABLE,
            finish_reason="stop",
            raw_response_valid=True,
        )


@pytest.mark.parametrize(
    "bad_sampling",
    [
        {"api_key": "secret-123"},
        {"gemini_api_key": "secret-123"},
        {"client_secret": "abc"},
        {"access_token": "tok"},
        {"authorization": "Bearer xyz"},
        {"db_password": "pw"},
        {"nested": {"private_key": "k"}},
        {"nested_list": [{"api_key": "secret-in-list"}]},
        {"nested_tuple": ({"auth_token": "secret-in-tuple"},)},
    ],
)
def test_telemetry_rejects_sensitive_sampling_keys(bad_sampling: dict[str, Any]) -> None:
    """Ngăn chặn mọi khóa nhạy cảm lọt vào `sampling_params` của telemetry."""
    with pytest.raises(ValidationError):
        ProviderTelemetry(
            provider_name="gemini",
            model_id="gemini-2.5-flash",
            tier=ProviderTier.FORMAL_EXPERIMENT,
            latency_ms=120.0,
            is_simulated_metric=False,
            input_tokens=50,
            output_tokens=20,
            token_usage_source=TokenUsageSource.MEASURED,
            finish_reason="STOP",
            raw_response_valid=True,
            sampling_params=bad_sampling,
        )


def test_telemetry_allows_safe_max_tokens_sampling_key() -> None:
    """Tham số chuẩn `max_tokens` từ YAML model config vẫn phải được chấp nhận."""
    telemetry = ProviderTelemetry(
        provider_name="ollama",
        model_id="qwen3:1.7b",
        tier=ProviderTier.LOCAL_SMOKE_TEST,
        latency_ms=120.0,
        is_simulated_metric=False,
        input_tokens=None,
        output_tokens=None,
        token_usage_source=TokenUsageSource.UNAVAILABLE,
        finish_reason="stop",
        raw_response_valid=True,
        sampling_params={"temperature": 0.3, "top_p": 0.9, "max_tokens": 1024, "seed": 42},
    )
    assert telemetry.sampling_params["max_tokens"] == 1024


def test_shared_parse_and_validate_structured_errors() -> None:
    """Kiểm tra phân biệt `MalformedJsonOutputError` và `SchemaValidationOutputError`."""
    with pytest.raises(MalformedJsonOutputError):
        LLMProvider.parse_and_validate_structured("{not-json", _DemoOutput)

    with pytest.raises(SchemaValidationOutputError):
        LLMProvider.parse_and_validate_structured('{"sku_id": "SKU-1"}', _DemoOutput)

    parsed = LLMProvider.parse_and_validate_structured(
        '{"sku_id": "SKU-1", "pitch_text": "Mật ong nguyên chất"}',
        _DemoOutput,
    )
    assert parsed == _DemoOutput(sku_id="SKU-1", pitch_text="Mật ong nguyên chất")


# ---------------------------------------------------------------------------
# 2. MockLLMProvider (Tier 1)
# ---------------------------------------------------------------------------


def test_mock_provider_ordered_sequence_for_retry_flow() -> None:
    """Kiểm tra tiêu thụ tuần tự `deque` qua các bước lỗi rồi thành công với `StoryChunk`."""
    valid_chunk_payload = {
        "chunk_id": "chk-01",
        "plan_id": "plan-01",
        "plan_revision": 1,
        "arc_id": "arc-01",
        "topic_id": "topic-01",
        "sequence_index": 0,
        "role": StoryChunkRole.PRODUCT_STORY.value,
        "sku_id": "SKU-HONEY-01",
        "text": "Mật ong hoa cà phê thu hoạch vào mùa hoa nở tại Cư M'gar.",
        "cited_evidence_ids": ["ev-honey-04"],
        "estimated_duration_sec": 8.5,
        "semantic_breakpoint": True,
        "breakpoint_type": BreakpointType.TOPIC_END.value,
    }
    provider = MockLLMProvider(
        response_sequence=[
            MockResponseStep(behavior=MockBehavior.MALFORMED_JSON, payload="{broken"),
            MockResponseStep(
                behavior=MockBehavior.INVALID_SCHEMA,
                payload={"sku_id": "SKU-HONEY-01"},
            ),
            MockResponseStep(
                behavior=MockBehavior.VALID_JSON,
                payload=valid_chunk_payload,
                latency_ms=2.5,
                input_tokens=200,
                output_tokens=80,
            ),
        ]
    )

    req = _make_request()
    start = time.perf_counter()

    with pytest.raises(MalformedJsonOutputError) as exc_malformed:
        provider.generate_structured(req, StoryChunk)
    assert exc_malformed.value.telemetry is not None
    assert exc_malformed.value.telemetry.tier == ProviderTier.UNIT_TEST
    assert exc_malformed.value.telemetry.is_simulated_metric is True
    assert exc_malformed.value.telemetry.token_usage_source == TokenUsageSource.SIMULATED
    assert exc_malformed.value.telemetry.raw_response_valid is False

    with pytest.raises(SchemaValidationOutputError) as exc_schema:
        provider.generate_structured(req, StoryChunk)
    assert exc_schema.value.telemetry is not None
    assert exc_schema.value.telemetry.raw_response_valid is False

    result = provider.generate_structured(req, StoryChunk)
    elapsed_sec = time.perf_counter() - start
    assert elapsed_sec < 1.0  # Mock tuyệt đối không sleep.
    assert isinstance(result.parsed_output, StoryChunk)
    assert result.parsed_output.chunk_id == "chk-01"
    assert result.telemetry.tier == ProviderTier.UNIT_TEST
    assert result.telemetry.is_simulated_metric is True
    assert result.telemetry.token_usage_source == TokenUsageSource.SIMULATED
    assert result.telemetry.raw_response_valid is True
    assert result.telemetry.input_tokens == 200
    assert result.telemetry.output_tokens == 80

    # Cạn hàng đợi phải ném ProviderError tường minh, không tự bịa output mới.
    with pytest.raises(ProviderError) as exc_exhausted:
        provider.generate_structured(req, StoryChunk)
    assert exc_exhausted.value.telemetry is not None
    assert exc_exhausted.value.telemetry.finish_reason == "mock_exhausted"


def test_mock_provider_malformed_json_always_raises_malformed_error() -> None:
    """`MockBehavior.MALFORMED_JSON` luôn ném `MalformedJsonOutputError` kể cả khi payload là JSON hợp lệ."""
    provider = MockLLMProvider(
        response_sequence=[
            MockResponseStep(behavior=MockBehavior.MALFORMED_JSON, payload='{"wrong": 1}'),
            MockResponseStep(
                behavior=MockBehavior.MALFORMED_JSON,
                payload={"sku_id": "SKU-1", "pitch_text": "Valid dict"},
            ),
            MockResponseStep(behavior=MockBehavior.MALFORMED_JSON, payload=None),
        ]
    )
    req = _make_request()
    for _ in range(3):
        with pytest.raises(MalformedJsonOutputError) as exc:
            provider.generate_structured(req, _DemoOutput)
        assert exc.value.telemetry is not None
        assert exc.value.telemetry.raw_response_valid is False


def test_mock_provider_failures_keyed_and_seeded_determinism() -> None:
    """Kiểm tra `TIMEOUT`, `PROVIDER_FAILURE`, `keyed_responses`, `seed` SHA-256 và unconfigured."""
    # Unconfigured phải báo lỗi ngay.
    unconfigured = MockLLMProvider()
    with pytest.raises(ProviderError) as exc_unconf:
        unconfigured.generate_structured(_make_request(), _DemoOutput)
    assert exc_unconf.value.telemetry is not None
    assert exc_unconf.value.telemetry.is_simulated_metric is True

    # Keyed routing theo fixture_key và theo tên schema + mô phỏng timeout/failure.
    keyed = MockLLMProvider(
        keyed_responses={
            "timeout_case": [
                MockResponseStep(
                    behavior=MockBehavior.TIMEOUT,
                    error_message="Simulated timeout",
                )
            ],
            "_DemoOutput": [
                MockResponseStep(
                    behavior=MockBehavior.PROVIDER_FAILURE,
                    error_message="Simulated outage",
                )
            ],
        }
    )
    with pytest.raises(ProviderTimeoutError) as exc_to:
        keyed.generate_structured(
            _make_request(metadata={"fixture_key": "timeout_case"}),
            _DemoOutput,
        )
    assert exc_to.value.telemetry is not None
    assert exc_to.value.telemetry.is_simulated_metric is True

    with pytest.raises(ProviderTransportError) as exc_fail:
        keyed.generate_structured(_make_request(), _DemoOutput)
    assert exc_fail.value.telemetry is not None
    assert exc_fail.value.telemetry.token_usage_source == TokenUsageSource.SIMULATED

    # Seeded selection tất định theo SHA-256 trên hai instance độc lập.
    variants = [
        MockResponseStep(
            behavior=MockBehavior.VALID_JSON,
            payload={"sku_id": "SKU-A", "pitch_text": "Biến thể A"},
        ),
        MockResponseStep(
            behavior=MockBehavior.VALID_JSON,
            payload={"sku_id": "SKU-B", "pitch_text": "Biến thể B"},
        ),
        MockResponseStep(
            behavior=MockBehavior.VALID_JSON,
            payload={"sku_id": "SKU-C", "pitch_text": "Biến thể C"},
        ),
    ]
    seeded_1 = MockLLMProvider(seed=42, seeded_variants=variants)
    seeded_2 = MockLLMProvider(seed=42, seeded_variants=variants)
    res_1 = seeded_1.generate_structured(_make_request(request_id="req-det-1"), _DemoOutput)
    res_2 = seeded_2.generate_structured(_make_request(request_id="req-det-1"), _DemoOutput)
    assert res_1.parsed_output == res_2.parsed_output


# ---------------------------------------------------------------------------
# 3. OllamaLocalProvider (Tier 2 - Offline via httpx.MockTransport)
# ---------------------------------------------------------------------------


def test_ollama_provider_success_and_no_http_in_init(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`OllamaLocalProvider` không gọi mạng khi init và đọc đúng metrics đo thật từ Ollama."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11435/")
    captured_requests: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://127.0.0.1:11435/api/chat"
        assert request.method == "POST"
        body = json.loads(request.content.decode("utf-8"))
        captured_requests.append(body)
        return httpx.Response(
            200,
            json={
                "model": "qwen3:1.7b",
                "message": {
                    "role": "assistant",
                    "content": '{"sku_id": "SKU-HONEY-01", "pitch_text": "Mật ong Dak Lak"}',
                },
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 88,
                "eval_count": 24,
            },
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        provider = OllamaLocalProvider(
            OllamaProviderConfig(
                model_id="qwen3:1.7b",
                quantization="Q4_K_M",
                context_window=8192,
                sampling={"temperature": 0.3, "top_p": 0.9, "max_tokens": 512, "seed": 42},
                timeout_sec=120.0,
            ),
            http_client=client,
        )
        assert provider.base_url == "http://127.0.0.1:11435"
        assert len(captured_requests) == 0  # Không gọi HTTP trong __init__.

        result = provider.generate_structured(_make_request(), _DemoOutput)

    assert len(captured_requests) == 1
    sent = captured_requests[0]
    assert sent["model"] == "qwen3:1.7b"
    assert sent["stream"] is False
    assert sent["format"] == _DemoOutput.model_json_schema()
    assert sent["options"]["num_predict"] == 512
    assert sent["options"]["num_ctx"] == 8192
    assert result.parsed_output == _DemoOutput(sku_id="SKU-HONEY-01", pitch_text="Mật ong Dak Lak")
    assert result.telemetry.tier == ProviderTier.LOCAL_SMOKE_TEST
    assert result.telemetry.is_simulated_metric is False
    assert result.telemetry.token_usage_source == TokenUsageSource.MEASURED
    assert result.telemetry.input_tokens == 88
    assert result.telemetry.output_tokens == 24
    assert result.telemetry.quantization == "Q4_K_M"
    assert result.telemetry.context_window == 8192
    assert result.telemetry.raw_response_valid is True


def test_ollama_provider_missing_token_counts_never_fakes_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Khi Ollama thiếu `prompt_eval_count`/`eval_count`, bắt buộc ghi `UNAVAILABLE` và `None`."""
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "message": {"content": '{"sku_id": "SKU-1", "pitch_text": "OK"}'},
                "done": True,
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = OllamaLocalProvider(
            OllamaProviderConfig(model_id="qwen3:1.7b"),
            http_client=client,
        )
        assert provider.base_url == DEFAULT_OLLAMA_BASE_URL
        result = provider.generate_structured(_make_request(), _DemoOutput)

    assert result.telemetry.token_usage_source == TokenUsageSource.UNAVAILABLE
    assert result.telemetry.input_tokens is None
    assert result.telemetry.output_tokens is None


def test_ollama_provider_error_mappings() -> None:
    """Ánh xạ đầy đủ Timeout, HTTP 404, body lỗi, Malformed JSON và Schema Error."""
    config = OllamaProviderConfig(model_id="qwen3:1.7b")
    req = _make_request()

    # TimeoutException -> ProviderTimeoutError
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with httpx.Client(transport=httpx.MockTransport(timeout_handler)) as client:
        with pytest.raises(ProviderTimeoutError) as exc_to:
            OllamaLocalProvider(config, http_client=client).generate_structured(req, _DemoOutput)
        assert exc_to.value.telemetry is not None
        assert exc_to.value.telemetry.token_usage_source == TokenUsageSource.UNAVAILABLE

    # HTTP 404 (model chưa pull) -> ProviderTransportError
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(404, text='{"error":"model not found"}')
        )
    ) as client:
        with pytest.raises(ProviderTransportError):
            OllamaLocalProvider(config, http_client=client).generate_structured(req, _DemoOutput)

    # Non-JSON HTTP body -> ProviderTransportError
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, text="not-json-body"))
    ) as client:
        with pytest.raises(ProviderTransportError):
            OllamaLocalProvider(config, http_client=client).generate_structured(req, _DemoOutput)

    # Thiếu message.content -> ProviderTransportError
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"done": True}))
    ) as client:
        with pytest.raises(ProviderTransportError):
            OllamaLocalProvider(config, http_client=client).generate_structured(req, _DemoOutput)

    # Malformed JSON bên trong message.content -> MalformedJsonOutputError
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={"message": {"content": "{bad"}, "prompt_eval_count": 10, "eval_count": 2},
            )
        )
    ) as client:
        with pytest.raises(MalformedJsonOutputError) as exc_mal:
            OllamaLocalProvider(config, http_client=client).generate_structured(req, _DemoOutput)
        assert exc_mal.value.telemetry is not None
        assert exc_mal.value.telemetry.raw_response_valid is False

    # JSON sai schema bên trong message.content -> SchemaValidationOutputError
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "message": {"content": '{"sku_id": "SKU-1"}'},
                    "prompt_eval_count": 10,
                    "eval_count": 2,
                },
            )
        )
    ) as client:
        with pytest.raises(SchemaValidationOutputError) as exc_sch:
            OllamaLocalProvider(config, http_client=client).generate_structured(req, _DemoOutput)
        assert exc_sch.value.telemetry is not None
        assert exc_sch.value.telemetry.raw_response_valid is False


# ---------------------------------------------------------------------------
# 4. GeminiAPIProvider (Tier 3 - Offline via GeminiClientProtocol)
# ---------------------------------------------------------------------------


def test_gemini_provider_guards_tbd_missing_key_and_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rào bảo mật từ chối `TBD`, thiếu API key (không lộ key), `MERCHANT_REAL`, và `client=None`."""
    monkeypatch.setenv("GEMINI_API_KEY", "super-secret-dummy-value-do-not-leak")

    # 1. Placeholder model_id -> ProviderConfigError
    with pytest.raises(ProviderConfigError):
        GeminiAPIProvider(GeminiProviderConfig(model_id="TBD_VERIFY_BEFORE_USE"))

    # 2. Thiếu API key -> ProviderAuthError (không bao giờ in key).
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ProviderAuthError) as exc_auth:
        GeminiAPIProvider(GeminiProviderConfig(model_id="gemini-2.5-flash"))
    assert "GEMINI_API_KEY" in str(exc_auth.value)

    # 3. Chặn dữ liệu MERCHANT_REAL / PII TRƯỚC khi gọi client.
    secret_value = "secret-api-key-999"
    monkeypatch.setenv("GEMINI_API_KEY", secret_value)
    fake_client = _FakeGeminiClient(
        response=GeminiRawResponse(
            raw_text='{"sku_id": "SKU-1", "pitch_text": "OK"}',
            input_tokens=10,
            output_tokens=5,
        )
    )
    provider = GeminiAPIProvider(
        GeminiProviderConfig(model_id="gemini-2.5-flash"),
        client=fake_client,
    )
    with pytest.raises(ProviderConfigError):
        provider.generate_structured(
            _make_request(data_classification="MERCHANT_REAL"),
            _DemoOutput,
        )
    with pytest.raises(ProviderConfigError):
        provider.generate_structured(
            _make_request(data_classification="PII"),
            _DemoOutput,
        )
    assert len(fake_client.calls) == 0

    # 4. client=None -> ProviderConfigError rõ ràng, KHÔNG âm thầm fallback về Mock.
    no_client_provider = GeminiAPIProvider(
        GeminiProviderConfig(model_id="gemini-2.5-flash"),
        client=None,
    )
    with pytest.raises(ProviderConfigError) as exc_no_client:
        no_client_provider.generate_structured(_make_request(), _DemoOutput)
    assert secret_value not in str(exc_no_client.value)
    assert "MockLLMProvider" in str(exc_no_client.value)


def test_gemini_provider_success_and_output_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`GeminiAPIProvider` với client hợp lệ trả telemetry `FORMAL_EXPERIMENT` trung thực."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-local-key")
    client = _FakeGeminiClient(
        response=GeminiRawResponse(
            raw_text='{"sku_id": "SKU-HONEY-01", "pitch_text": "Hương hoa cà phê tự nhiên"}',
            input_tokens=150,
            output_tokens=32,
            finish_reason="STOP",
        )
    )
    provider = GeminiAPIProvider(
        GeminiProviderConfig(model_id="gemini-2.5-flash"),
        client=client,
    )
    result = provider.generate_structured(
        _make_request(data_classification="PUBLIC_APPROVED"),
        _DemoOutput,
    )
    assert result.parsed_output == _DemoOutput(
        sku_id="SKU-HONEY-01",
        pitch_text="Hương hoa cà phê tự nhiên",
    )
    assert result.telemetry.tier == ProviderTier.FORMAL_EXPERIMENT
    assert result.telemetry.is_simulated_metric is False
    assert result.telemetry.token_usage_source == TokenUsageSource.MEASURED
    assert result.telemetry.input_tokens == 150
    assert result.telemetry.output_tokens == 32
    assert result.telemetry.raw_response_valid is True

    # Lỗi JSON từ Gemini client -> MalformedJsonOutputError kèm telemetry.
    bad_json_provider = GeminiAPIProvider(
        GeminiProviderConfig(model_id="gemini-2.5-flash"),
        client=_FakeGeminiClient(response=GeminiRawResponse(raw_text="{invalid")),
    )
    with pytest.raises(MalformedJsonOutputError) as exc_bad:
        bad_json_provider.generate_structured(_make_request(), _DemoOutput)
    assert exc_bad.value.telemetry is not None
    assert exc_bad.value.telemetry.token_usage_source == TokenUsageSource.UNAVAILABLE
    assert exc_bad.value.telemetry.raw_response_valid is False


# ---------------------------------------------------------------------------
# 5. ProviderFactory & Real Model YAML Configs
# ---------------------------------------------------------------------------


def test_factory_loads_all_real_model_yamls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Xác minh `ProviderFactory.from_yaml` nạp sạch cả 4 file `configs/models/*.yaml`."""
    # Tier 1: mock.yaml
    mock_provider = ProviderFactory.from_yaml(
        MODELS_DIR / "mock.yaml",
        response_sequence=[
            MockResponseStep(
                behavior=MockBehavior.VALID_JSON,
                payload={"sku_id": "SKU-1", "pitch_text": "Mock OK"},
            )
        ],
    )
    assert isinstance(mock_provider, MockLLMProvider)
    assert mock_provider.tier == ProviderTier.UNIT_TEST
    assert mock_provider.model_id == "deterministic-mock-v0.1"
    mock_res = mock_provider.generate_structured(_make_request(), _DemoOutput)
    assert mock_res.parsed_output.sku_id == "SKU-1"

    # Tier 2: ollama_qwen3_1.7b.yaml & ollama_qwen3_4b.yaml
    ollama_17b = ProviderFactory.from_yaml(MODELS_DIR / "ollama_qwen3_1.7b.yaml")
    assert isinstance(ollama_17b, OllamaLocalProvider)
    assert ollama_17b.tier == ProviderTier.LOCAL_SMOKE_TEST
    assert ollama_17b.model_id == "qwen3:1.7b"

    ollama_4b = ProviderFactory.from_yaml(MODELS_DIR / "ollama_qwen3_4b.yaml")
    assert isinstance(ollama_4b, OllamaLocalProvider)
    assert ollama_4b.tier == ProviderTier.LOCAL_SMOKE_TEST
    assert ollama_4b.model_id == "qwen3:4b"

    # Tier 3: gemini_flash.yaml không có override phải bị chặn vì TBD_VERIFY_BEFORE_USE.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ProviderConfigError):
        ProviderFactory.from_yaml(MODELS_DIR / "gemini_flash.yaml")

    # Có override model_id nhưng thiếu env key -> ProviderAuthError.
    with pytest.raises(ProviderAuthError):
        ProviderFactory.from_yaml(
            MODELS_DIR / "gemini_flash.yaml",
            model_id="gemini-2.5-flash",
        )

    # Đủ override model_id + env key + fake client -> dựng thành công GeminiAPIProvider.
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-test-key")
    gemini_provider = ProviderFactory.from_yaml(
        MODELS_DIR / "gemini_flash.yaml",
        model_id="gemini-2.5-flash",
        client=_FakeGeminiClient(
            response=GeminiRawResponse(
                raw_text='{"sku_id": "SKU-1", "pitch_text": "Gemini OK"}',
                input_tokens=40,
                output_tokens=12,
            )
        ),
    )
    assert isinstance(gemini_provider, GeminiAPIProvider)
    assert gemini_provider.tier == ProviderTier.FORMAL_EXPERIMENT
    assert gemini_provider.model_id == "gemini-2.5-flash"
    gemini_res = gemini_provider.generate_structured(_make_request(), _DemoOutput)
    assert gemini_res.parsed_output.pitch_text == "Gemini OK"


def test_factory_rejects_unknown_provider_and_mismatched_tier() -> None:
    """Từ chối provider lạ, xung đột `(provider, run_tier)` hoặc file cấu hình không tồn tại."""
    with pytest.raises(ProviderConfigError):
        ProviderFactory.from_dict(
            {
                "provider": "openai",
                "run_tier": "formal_experiment",
                "model_id": "gpt-4o",
            }
        )

    with pytest.raises(ProviderConfigError):
        ProviderFactory.from_dict(
            {
                "provider": "ollama",
                "run_tier": "formal_experiment",
                "model_id": "qwen3:1.7b",
            }
        )

    with pytest.raises(ProviderConfigError):
        ProviderFactory.from_dict(
            {
                "provider": "mock",
                "run_tier": "local_smoke_test",
                "model_id": "deterministic-mock-v0.1",
            }
        )

    with pytest.raises(ProviderConfigError):
        ProviderFactory.from_yaml(MODELS_DIR / "does_not_exist.yaml")
