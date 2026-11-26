"""Giao diện trừu tượng và hợp đồng dữ liệu telemetry cho tầng LLM Provider của P06.

1. File này giải quyết vấn đề gì?
   Tách biệt hoàn toàn logic nghiệp vụ kể chuyện (LangGraph nodes, StoryPlanner) khỏi
   nhà cung cấp mô hình cụ thể (Mock, Ollama CPU cục bộ, hoặc Gemini API) theo nguyên lý
   Dependency Inversion (`P06-OPEN-1`), giúp hoán đổi mô hình chỉ qua YAML mà không sửa graph.
2. Trách nhiệm chính của module là gì?
   Định nghĩa lớp cơ sở trừu tượng `LLMProvider`, mô hình `GenerationRequest`, `GenerationResult`,
   bản ghi đo lường `ProviderTelemetry`, các enum phân tầng `ProviderTier` / `TokenUsageSource`,
   cùng hệ phân cấp ngoại lệ có gắn telemetry (`ProviderError` và các lớp con).
3. Module này liên kết với các thành phần nào?
   Tái sử dụng các kiểu kiểm định nghiêm ngặt từ `p06.schemas.story`; được kế thừa bởi
   `mock_provider.py`, `ollama_provider.py`, `gemini_provider.py` và khởi tạo qua `factory.py`.
4. Input và output chính là gì?
   Input là `GenerationRequest` (prompt, metadata, phân loại dữ liệu, tham số sampling)
   cùng lớp `BaseModel` đích (`output_schema`); Output là `GenerationResult[OutputT]` chứa
   đối tượng đã kiểm định, văn bản thô và `ProviderTelemetry` bất biến.
5. Có những constraints hoặc invariants quan trọng nào?
   - Tuyệt đối không đánh đồng `Mock` (`UNIT_TEST`) với `Ollama` (`LOCAL_SMOKE_TEST`)
     và `Gemini` (`FORMAL_EXPERIMENT`); mọi telemetry đều ghi rõ `is_simulated_metric`
     và `token_usage_source` (cấm bịa `0` khi `UNAVAILABLE`).
   - Ngăn rò rỉ khóa bí mật bằng cách từ chối mọi khóa nhạy cảm trong `sampling_params`.
   - Đầu ra của `LLMProvider` chỉ là bản nháp có cấu trúc từ LLM; KHÔNG BAO GIỜ tự động
     được xem là `VERIFIED` bởi P05 (`I-02`) hay `PlaybackCompleted` bởi P04 (`I-03`/`I-06`).
"""

from __future__ import annotations

import json
import math
from abc import ABC, abstractmethod
from enum import Enum
from typing import Annotated, Any, Callable, Final, Generic, Optional, TypeVar

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    ValidationError,
    field_validator,
    model_validator,
)

from p06.schemas.story import (
    NonBlankStr,
    OptionalNonBlankStr,
    StrictNonNegInt,
    StrictPositiveInt,
)

DEFAULT_TIMEOUT_SEC: Final[float] = 30.0

# Danh sách từ khóa nhạy cảm tuyệt đối không được xuất hiện trong sampling_params/log.
SENSITIVE_SAMPLING_KEYS: Final[frozenset[str]] = frozenset(
    {"api_key", "key", "secret", "token", "authorization", "password", "bearer"}
)

# Các tên tham số đếm token chuẩn của LLM không phải bí mật xác thực; ngoại lệ duy nhất cho từ khóa "token".
_SAFE_TOKEN_COUNT_SAMPLING_KEYS: Final[frozenset[str]] = frozenset(
    {"max_tokens", "max_output_tokens"}
)

OutputT = TypeVar("OutputT", bound=BaseModel)


def _validate_strict_non_neg_float(value: Any) -> float:
    """Kiểm định số thực không âm nghiêm ngặt: từ chối `bool`, `str` và `nan`/`inf`.

    Lý do kỹ thuật: Trong Python, `bool` kế thừa `int` nên cần chặn tường minh để
    `True`/`False` không bị ép kiểu ngầm thành `1.0`/`0.0` ms.

    Args:
        value: Giá trị số thực đầu vào (ví dụ `latency_ms`).

    Returns:
        float: Giá trị số thực hữu hạn.

    Raises:
        ValueError: Nếu giá trị là `bool`, không phải `int`/`float`, hoặc không hữu hạn.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"Giá trị số thực phải là int hoặc float thuần túy, nhận được {type(value).__name__}."
        )
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError("Giá trị số thực bắt buộc phải hữu hạn.")
    return numeric


def _validate_strict_positive_float(value: Any) -> float:
    """Kiểm định số thực dương hữu hạn (`> 0.0`): từ chối `bool`, `str` và `nan`/`inf`."""
    numeric = _validate_strict_non_neg_float(value)
    if numeric <= 0.0:
        raise ValueError("Giá trị số thực bắt buộc phải dương (> 0.0).")
    return numeric


def _validate_optional_temperature(value: Any) -> Optional[float]:
    """Kiểm định tham số `temperature` tùy chọn: chỉ nhận `None` hoặc số thực hữu hạn >= 0.

    Args:
        value: Giá trị nhiệt độ lấy mẫu đầu vào.

    Returns:
        Optional[float]: `None` hoặc số thực không âm hữu hạn.

    Raises:
        ValueError: Nếu giá trị sai kiểu (`bool`/`str`), không hữu hạn hoặc `< 0.0`.
    """
    if value is None:
        return None
    numeric = _validate_strict_non_neg_float(value)
    if numeric < 0.0:
        raise ValueError("temperature không được nhỏ hơn 0.0.")
    return numeric


def _find_sensitive_key_in_value(value: Any) -> Optional[str]:
    """Duyệt đệ quy `dict`, `list` và `tuple` để phát hiện khóa nhạy cảm lồng bên trong."""
    if isinstance(value, dict):
        return _contains_sensitive_sampling_key(value)
    if isinstance(value, (list, tuple)):
        for idx, item in enumerate(value):
            nested_violation = _find_sensitive_key_in_value(item)
            if nested_violation is not None:
                return f"[{idx}].{nested_violation}"
    return None


def _contains_sensitive_sampling_key(mapping: dict[str, Any]) -> Optional[str]:
    """Kiểm tra đệ quy xem dict (bao gồm list/tuple lồng nhau) có chứa khóa nhạy cảm hay không.

    Lý do bảo mật: Nếu nhà phát triển vô tình truyền `api_key` hoặc `auth_token` vào
    `sampling_params`, telemetry sẽ được ghi vào `runs/*/manifest.json` và gây lộ bí mật.

    Args:
        mapping: Từ điển tham số cần rà soát.

    Returns:
        Optional[str]: Tên khóa vi phạm đầu tiên nếu phát hiện, ngược lại trả về `None`.
    """
    for raw_key, nested_val in mapping.items():
        key_lower = str(raw_key).strip().lower()
        # Chỉ miễn trừ tên tham số giới hạn độ dài sinh văn bản chuẩn của LLM (`max_tokens`).
        if key_lower not in _SAFE_TOKEN_COUNT_SAMPLING_KEYS:
            for sensitive_sub in SENSITIVE_SAMPLING_KEYS:
                if sensitive_sub in key_lower:
                    return str(raw_key)
        nested_violation = _find_sensitive_key_in_value(nested_val)
        if nested_violation is not None:
            return f"{raw_key}.{nested_violation}"
    return None


StrictNonNegFloat = Annotated[
    float,
    BeforeValidator(_validate_strict_non_neg_float),
    Field(ge=0.0),
]
StrictPositiveFloat = Annotated[
    float,
    BeforeValidator(_validate_strict_positive_float),
    Field(gt=0.0),
]
OptionalTemperature = Annotated[Optional[float], BeforeValidator(_validate_optional_temperature)]


class ProviderTier(str, Enum):
    """Phân tầng thực thi LLM theo chính sách 3 tầng của P06 (`P06-OPEN-1`).

    Attributes:
        UNIT_TEST: Tầng 1 (`MockLLMProvider`), chỉ dùng cho kiểm thử tự động offline.
        LOCAL_SMOKE_TEST: Tầng 2 (`OllamaLocalProvider`), kiểm tra luồng trên CPU cục bộ.
        FORMAL_EXPERIMENT: Tầng 3 (`GeminiAPIProvider`), thí nghiệm định lượng chính thức.
    """

    UNIT_TEST = "unit_test"
    LOCAL_SMOKE_TEST = "local_smoke_test"
    FORMAL_EXPERIMENT = "formal_experiment"


class TokenUsageSource(str, Enum):
    """Nguồn gốc số liệu đếm token nhằm bảo đảm tính trung thực khoa học (provenance).

    Attributes:
        MEASURED: Số token đo thật từ phản hồi của nhà cung cấp LLM.
        SIMULATED: Số token giả lập từ `MockLLMProvider` cho kiểm thử đơn vị.
        UNAVAILABLE: Nhà cung cấp không trả về thống kê token (bắt buộc để `None`, cấm bịa `0`).
    """

    MEASURED = "MEASURED"
    SIMULATED = "SIMULATED"
    UNAVAILABLE = "UNAVAILABLE"


class ProviderTelemetry(BaseModel):
    """Bản ghi đo lường chuẩn hóa cho mọi lượt gọi `LLMProvider` (bất biến).

    Lý do thiết kế: Việc gắn chặt `tier`, `is_simulated_metric` và `token_usage_source`
    giúp pipeline đánh giá tự động phát hiện và từ chối hành vi trộn số liệu Mock/Ollama
    với kết quả thí nghiệm Gemini.

    Attributes:
        provider_name: Tên định danh nhà cung cấp (`mock`, `ollama`, `gemini`).
        model_id: Định danh mô hình thực tế được gọi.
        tier: Tầng thực thi theo chuẩn 3 tầng `P06-OPEN-1`.
        latency_ms: Độ trễ đo được tính bằng mili-giây (`>= 0.0`).
        is_simulated_metric: `True` nếu số liệu là mô phỏng (bắt buộc với `UNIT_TEST`).
        input_tokens: Số token đầu vào (`None` khi `UNAVAILABLE`).
        output_tokens: Số token đầu ra (`None` khi `UNAVAILABLE`).
        token_usage_source: Nguồn gốc thống kê token (`MEASURED`, `SIMULATED`, `UNAVAILABLE`).
        finish_reason: Lý do kết thúc sinh văn bản từ provider.
        raw_response_valid: `True` chỉ khi phản hồi JSON vượt qua kiểm định schema đích.
        quantization: Mức lượng tử hóa thực tế (áp dụng cho mô hình cục bộ như Ollama).
        context_window: Kích thước cửa sổ ngữ cảnh cấu hình cho mô hình.
        sampling_params: Tham số lấy mẫu đã sử dụng (đã lọc khóa nhạy cảm).
        prompt_version: Phiên bản template prompt gắn với lượt gọi.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_name: NonBlankStr
    model_id: NonBlankStr
    tier: ProviderTier
    latency_ms: StrictNonNegFloat
    is_simulated_metric: StrictBool
    input_tokens: Optional[StrictNonNegInt] = None
    output_tokens: Optional[StrictNonNegInt] = None
    token_usage_source: TokenUsageSource
    finish_reason: NonBlankStr
    raw_response_valid: StrictBool
    quantization: OptionalNonBlankStr = None
    context_window: Optional[StrictPositiveInt] = None
    sampling_params: dict[str, Any] = Field(default_factory=dict)
    prompt_version: OptionalNonBlankStr = None

    @field_validator("sampling_params")
    @classmethod
    def reject_sensitive_sampling_keys(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Chặn mọi khóa nhạy cảm lọt vào `sampling_params` trước khi ghi log/manifest.

        Args:
            value: Từ điển tham số lấy mẫu.

        Returns:
            dict[str, Any]: Từ điển đã kiểm định an toàn.

        Raises:
            ValueError: Nếu phát hiện khóa chứa chuỗi con trong `SENSITIVE_SAMPLING_KEYS`.
        """
        violation = _contains_sensitive_sampling_key(value)
        if violation is not None:
            raise ValueError(
                f"sampling_params chứa khóa nhạy cảm bị cấm '{violation}'."
            )
        return value

    @model_validator(mode="after")
    def validate_telemetry_provenance_invariants(self) -> ProviderTelemetry:
        """Bảo toàn bất biến nguồn gốc số liệu giữa tầng chạy, cờ giả lập và token.

        Returns:
            ProviderTelemetry: Bản ghi hợp lệ sau kiểm định liên trường.

        Raises:
            ValueError: Nếu tầng `UNIT_TEST` không đánh dấu giả lập / gán nhầm `MEASURED`,
                hoặc khi `token_usage_source == UNAVAILABLE` nhưng lại điền giá trị token khác `None`.
        """
        if self.tier == ProviderTier.UNIT_TEST:
            if not self.is_simulated_metric:
                raise ValueError(
                    "Telemetry thuộc tier UNIT_TEST bắt buộc có is_simulated_metric=True."
                )
            if self.token_usage_source == TokenUsageSource.MEASURED:
                raise ValueError(
                    "Telemetry thuộc tier UNIT_TEST không được gán token_usage_source=MEASURED."
                )

        if self.token_usage_source == TokenUsageSource.UNAVAILABLE:
            if self.input_tokens is not None or self.output_tokens is not None:
                raise ValueError(
                    "Khi token_usage_source=UNAVAILABLE, input_tokens và output_tokens "
                    "bắt buộc phải là None (tuyệt đối không bịa giá trị 0)."
                )
        return self


class ProviderError(RuntimeError):
    """Ngoại lệ gốc cho toàn bộ lỗi phát sinh tại tầng `LLMProvider`.

    Attributes:
        telemetry: Bản ghi `ProviderTelemetry` gắn kèm thời điểm lỗi (nếu có).
    """

    def __init__(
        self,
        message: str,
        telemetry: Optional[ProviderTelemetry] = None,
    ) -> None:
        super().__init__(message)
        self.telemetry: Optional[ProviderTelemetry] = telemetry


class ProviderConfigError(ProviderError):
    """Lỗi cấu hình provider không hợp lệ, thiếu tham số hoặc vi phạm chính sách dữ liệu."""


class ProviderAuthError(ProviderError):
    """Lỗi xác thực (ví dụ thiếu biến môi trường chứa API key)."""


class ProviderTimeoutError(ProviderError):
    """Lỗi quá thời gian chờ phản hồi từ LLM provider."""


class ProviderTransportError(ProviderError):
    """Lỗi giao vận HTTP/SDK hoặc phản hồi tầng transport không đúng định dạng."""


class StructuredOutputError(ProviderError):
    """Ngoại lệ gốc khi đầu ra văn bản từ LLM không đạt chuẩn cấu trúc mong muốn."""


class MalformedJsonOutputError(StructuredOutputError):
    """LLM trả về chuỗi không phân tích được thành JSON hợp lệ."""


class SchemaValidationOutputError(StructuredOutputError):
    """JSON từ LLM có cú pháp đúng nhưng vi phạm schema Pydantic v2 đích."""


class GenerationRequest(BaseModel):
    """Yêu cầu sinh dữ liệu có cấu trúc gửi tới `LLMProvider`.

    Attributes:
        request_id: Mã định danh duy nhất cho lượt gọi (phục vụ truy vết và seed).
        system_prompt: Chỉ dẫn hệ thống quy định vai trò và ràng buộc an toàn.
        user_prompt: Ngữ cảnh cụ thể của lượt kể chuyện/trả lời.
        prompt_version: Phiên bản template prompt để lưu provenance vào manifest.
        data_classification: Nhãn phân loại dữ liệu (mặc định `SYNTHETIC`).
        temperature: Ghi đè nhiệt độ lấy mẫu nếu khác cấu hình mặc định.
        max_tokens: Ghi đè giới hạn token đầu ra nếu khác cấu hình mặc định.
        seed: Hạt giống ngẫu nhiên (nếu provider hỗ trợ).
        metadata: Dữ liệu phụ trợ cho định tuyến kiểm thử (ví dụ `fixture_key`).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: NonBlankStr
    system_prompt: NonBlankStr
    user_prompt: NonBlankStr
    prompt_version: NonBlankStr = "v0.1"
    data_classification: NonBlankStr = "SYNTHETIC"
    temperature: OptionalTemperature = None
    max_tokens: Optional[StrictPositiveInt] = None
    seed: Optional[StrictInt] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GenerationResult(BaseModel, Generic[OutputT]):
    """Kết quả trả về từ `LLMProvider` kèm đối tượng đã kiểm định và telemetry.

    Lưu ý bất biến kiến trúc quan trọng:
        Kết quả `parsed_output` từ `LLMProvider` CHỈ LÀ BẢN NHÁP NỘI BỘ (`DRAFT`).
        Nó KHÔNG BAO GIỜ tự động mang trạng thái `VERIFIED` của P05 (`I-02`) và KHÔNG
        BAO GIỜ tương đương với `PlaybackCompleted` của P04 (`I-03`/`I-06`).

    Attributes:
        parsed_output: Thực thể Pydantic `OutputT` đã vượt qua kiểm định JSON + schema.
        raw_text: Chuỗi phản hồi gốc do mô hình sinh ra.
        telemetry: Bản ghi đo lường `ProviderTelemetry` gắn với lượt gọi này.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    parsed_output: OutputT
    raw_text: str
    telemetry: ProviderTelemetry


class LLMProvider(ABC):
    """Lớp cơ sở trừu tượng thống nhất giao diện cho cả 3 tầng LLM Provider của P06.

    Lý do chọn `ABC` thay vì `Protocol`:
        Mọi provider cụ thể (`MockLLMProvider`, `OllamaLocalProvider`, `GeminiAPIProvider`)
        đều cần chia sẻ cùng cơ chế kiểm định JSON + Pydantic v2 và gắn `ProviderTelemetry`
        nhất quán vào cả kết quả thành công lẫn ngoại lệ (`MalformedJsonOutputError`,
        `SchemaValidationOutputError`). Việc dùng `ABC` cho phép kế thừa trực tiếp hàm
        `parse_and_validate_structured` và `_parse_and_validate_json` mà không lặp lại mã.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Tên định danh chuẩn của provider (ví dụ `'mock'`, `'ollama'`, `'gemini'`)."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Định danh mô hình đang được provider sử dụng."""

    @property
    @abstractmethod
    def tier(self) -> ProviderTier:
        """Tầng thực thi tương ứng của provider theo chính sách 3 tầng."""

    @abstractmethod
    def generate_structured(
        self,
        request: GenerationRequest,
        output_schema: type[OutputT],
    ) -> GenerationResult[OutputT]:
        """Sinh phản hồi có cấu trúc khớp `output_schema` và trả kèm `ProviderTelemetry`.

        Args:
            request: Yêu cầu đầu vào gồm prompt, phiên bản và phân loại dữ liệu.
            output_schema: Lớp Pydantic `BaseModel` dùng để ép kiểu và kiểm định đầu ra.

        Returns:
            GenerationResult[OutputT]: Đối tượng đã kiểm định, văn bản gốc và telemetry.

        Raises:
            ProviderError: Khi cấu hình, xác thực, kết nối hoặc định dạng đầu ra gặp lỗi.
        """

    @staticmethod
    def parse_and_validate_structured(
        raw_text: str,
        output_schema: type[OutputT],
        telemetry: Optional[ProviderTelemetry] = None,
    ) -> OutputT:
        """Phân tích chuỗi JSON thô và kiểm định theo Pydantic schema đích.

        Args:
            raw_text: Chuỗi JSON thô do LLM trả về.
            output_schema: Lớp `BaseModel` kỳ vọng.
            telemetry: Telemetry tùy chọn để đính kèm vào ngoại lệ nếu kiểm định thất bại.

        Returns:
            OutputT: Đối tượng `output_schema` đã hợp lệ hóa.

        Raises:
            ProviderConfigError: Nếu `output_schema` không phải lớp con của `BaseModel`.
            MalformedJsonOutputError: Nếu `raw_text` không phải JSON hợp lệ.
            SchemaValidationOutputError: Nếu JSON hợp lệ nhưng sai cấu trúc/ràng buộc schema.
        """
        if not (isinstance(output_schema, type) and issubclass(output_schema, BaseModel)):
            raise ProviderConfigError(
                "output_schema bắt buộc phải là một lớp con của Pydantic BaseModel.",
                telemetry=telemetry,
            )

        try:
            decoded = json.loads(raw_text)
        except (json.JSONDecodeError, TypeError) as exc:
            raise MalformedJsonOutputError(
                f"Đầu ra LLM không phải chuỗi JSON hợp lệ: {exc}",
                telemetry=telemetry,
            ) from exc

        try:
            return output_schema.model_validate(decoded)
        except ValidationError as exc:
            raise SchemaValidationOutputError(
                f"Đầu ra JSON không thỏa mãn schema {output_schema.__name__}: {exc}",
                telemetry=telemetry,
            ) from exc

    def _parse_and_validate_json(
        self,
        raw_text: str,
        output_schema: type[OutputT],
        telemetry_builder: Callable[[bool], ProviderTelemetry],
    ) -> OutputT:
        """Kiểm định đầu ra và tự động đính kèm telemetry `raw_response_valid=False` khi lỗi.

        Args:
            raw_text: Chuỗi phản hồi thô từ mô hình.
            output_schema: Lớp `BaseModel` đích.
            telemetry_builder: Hàm nhận `raw_response_valid: bool` và tạo `ProviderTelemetry`.

        Returns:
            OutputT: Thực thể đã kiểm định thành công.

        Raises:
            MalformedJsonOutputError: Khi JSON bị lỗi cú pháp (kèm telemetry lỗi).
            SchemaValidationOutputError: Khi dữ liệu sai schema (kèm telemetry lỗi).
        """
        try:
            return self.parse_and_validate_structured(raw_text, output_schema)
        except MalformedJsonOutputError as exc:
            raise MalformedJsonOutputError(
                str(exc),
                telemetry=telemetry_builder(False),
            ) from exc
        except SchemaValidationOutputError as exc:
            raise SchemaValidationOutputError(
                str(exc),
                telemetry=telemetry_builder(False),
            ) from exc
