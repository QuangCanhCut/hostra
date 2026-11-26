"""Factory khởi tạo `LLMProvider` từ tệp YAML hoặc dict cấu hình (`ProviderFactory`).

1. File này giải quyết vấn đề gì?
   Cung cấp điểm khởi tạo tập trung giúp các runner thí nghiệm (`experiments/p06_e01..e04`)
   và LangGraph chuyển đổi giữa 3 tầng (`Mock`, `Ollama CPU`, `Gemini API`) thuần bằng
   cấu hình trong `configs/models/*.yaml` mà không sửa bất kỳ logic đồ thị nào.
2. Trách nhiệm chính của module là gì?
   Đọc YAML/dict cấu hình, kiểm định tính nhất quán giữa cặp `(provider, run_tier)`,
   áp dụng các tham số ghi đè có kiểm soát (`overrides`) và trả về đúng thể hiện
   `LLMProvider` tương ứng mà không thực hiện kết nối mạng lúc khởi tạo.
3. Module này liên kết với các thành phần nào?
   Nhập `MockLLMProvider`, `OllamaLocalProvider`, `GeminiAPIProvider` và các lớp config/lỗi
   tương ứng trong `p06.providers`; đọc các tệp dưới `configs/models/`.
4. Input và output chính là gì?
   Input là đường dẫn YAML (`str | Path`) hoặc `Mapping[str, Any]` cùng các `overrides`;
   Output là một thể hiện `LLMProvider` đã qua kiểm định cấu hình ban đầu.
5. Có những constraints hoặc invariants quan trọng nào?
   - Cặp `(provider, run_tier)` bắt buộc khớp đúng 1-1:
     `mock <-> unit_test`, `ollama <-> local_smoke_test`, `gemini <-> formal_experiment`.
   - Không gọi mạng khi `import` hay khi gọi `from_yaml()`/`from_dict()`.
   - Cấu hình sai, không rõ nhà cung cấp hoặc lệch tầng đều phải ném `ProviderConfigError`
     (tuyệt đối không fallback ngầm sang `MockLLMProvider`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final, Mapping

import yaml
from pydantic import ValidationError

from p06.providers.base import LLMProvider, ProviderConfigError, ProviderTier
from p06.providers.gemini_provider import GeminiAPIProvider, GeminiProviderConfig
from p06.providers.mock_provider import MockLLMProvider
from p06.providers.ollama_provider import OllamaLocalProvider, OllamaProviderConfig

# Bản đồ ràng buộc 1-1 giữa tên provider và tầng chạy cho phép theo P06-OPEN-1.
_EXPECTED_TIER_BY_PROVIDER: Final[dict[str, ProviderTier]] = {
    "mock": ProviderTier.UNIT_TEST,
    "ollama": ProviderTier.LOCAL_SMOKE_TEST,
    "gemini": ProviderTier.FORMAL_EXPERIMENT,
}


class ProviderFactory:
    """Factory tạo `LLMProvider` theo Factory Pattern, tách rời cấu hình YAML khỏi graph."""

    @classmethod
    def from_yaml(
        cls,
        config_path: str | Path,
        **overrides: Any,
    ) -> LLMProvider:
        """Đọc tệp YAML mô hình và khởi tạo `LLMProvider` tương ứng.

        Args:
            config_path: Đường dẫn tới tệp YAML (ví dụ `configs/models/mock.yaml`).
            **overrides: Tham số ghi đè hoặc phụ thuộc tiêm vào (như `http_client`, `client`,
                `model_id`, `response_sequence`).

        Returns:
            LLMProvider: Thể hiện provider đã khởi tạo sẵn sàng dùng.

        Raises:
            ProviderConfigError: Nếu tệp không tồn tại, YAML lỗi cú pháp hoặc cấu hình không hợp lệ.
            ProviderAuthError: Nếu tầng Gemini thiếu biến môi trường API key.
        """
        path = Path(config_path)
        if not path.is_file():
            raise ProviderConfigError(f"Không tìm thấy tệp cấu hình model: '{path}'.")

        try:
            raw_text = path.read_text(encoding="utf-8")
            loaded = yaml.safe_load(raw_text)
        except (OSError, yaml.YAMLError) as exc:
            raise ProviderConfigError(
                f"Không thể đọc hoặc phân tích YAML từ '{path}': {exc}"
            ) from exc

        if not isinstance(loaded, Mapping):
            raise ProviderConfigError(
                f"Nội dung YAML trong '{path}' phải là ánh xạ (dict) ở cấp gốc."
            )

        return cls.from_dict(loaded, **overrides)

    @classmethod
    def from_dict(
        cls,
        config: Mapping[str, Any],
        **overrides: Any,
    ) -> LLMProvider:
        """Khởi tạo `LLMProvider` từ cấu hình dạng `Mapping` kèm tham số ghi đè.

        Lý do kiểm định cặp `(provider, run_tier)` nghiêm ngặt:
            Ngăn lỗi cấu hình nhầm lẫn (ví dụ gán `provider: ollama` với `run_tier: formal_experiment`),
            làm sai lệch phân tách báo cáo giữa CPU smoke test và thí nghiệm Gemini chính thức.

        Args:
            config: Từ điển cấu hình mô hình (thường nạp từ YAML).
            **overrides: Tham số ghi đè hoặc runtime client (`http_client`, `client`, ...).

        Returns:
            LLMProvider: Thể hiện provider tương ứng (`MockLLMProvider`, `OllamaLocalProvider`,
                hoặc `GeminiAPIProvider`).

        Raises:
            ProviderConfigError: Khi thiếu khóa bắt buộc, sai cặp `(provider, run_tier)`,
                provider không được hỗ trợ hoặc schema cấu hình không hợp lệ.
            ProviderAuthError: Khi `GeminiAPIProvider` thiếu API key trong biến môi trường.
        """
        if not isinstance(config, Mapping):
            raise ProviderConfigError("config truyền vào ProviderFactory.from_dict phải là Mapping.")

        merged: dict[str, Any] = dict(config)

        # Tách các phụ thuộc runtime không thuộc từ điển YAML tĩnh.
        runtime_keys = {
            "response_sequence",
            "keyed_responses",
            "seeded_variants",
            "http_client",
            "client",
        }
        runtime_args: dict[str, Any] = {}
        for key, value in overrides.items():
            if key in runtime_keys:
                runtime_args[key] = value
            elif key == "sampling" and isinstance(value, Mapping) and isinstance(
                merged.get("sampling"), Mapping
            ):
                merged["sampling"] = {**merged["sampling"], **value}
            else:
                merged[key] = value

        raw_provider = merged.get("provider")
        if not isinstance(raw_provider, str) or not raw_provider.strip():
            raise ProviderConfigError("Cấu hình model thiếu trường 'provider' hợp lệ.")
        provider_key = raw_provider.strip().lower()

        if provider_key not in _EXPECTED_TIER_BY_PROVIDER:
            raise ProviderConfigError(
                f"Provider '{raw_provider}' không được hỗ trợ. "
                f"Chỉ chấp nhận: {sorted(_EXPECTED_TIER_BY_PROVIDER)}."
            )

        raw_tier = merged.get("run_tier")
        try:
            parsed_tier = ProviderTier(raw_tier)
        except ValueError as exc:
            raise ProviderConfigError(
                f"Trường 'run_tier' không hợp lệ: '{raw_tier}'."
            ) from exc

        expected_tier = _EXPECTED_TIER_BY_PROVIDER[provider_key]
        if parsed_tier != expected_tier:
            raise ProviderConfigError(
                f"Xung đột cấu hình: provider='{provider_key}' bắt buộc đi cùng "
                f"run_tier='{expected_tier.value}', nhận được '{parsed_tier.value}'."
            )

        if provider_key == "mock":
            return cls._build_mock(merged, runtime_args)
        if provider_key == "ollama":
            return cls._build_ollama(merged, runtime_args)
        return cls._build_gemini(merged, runtime_args)

    @staticmethod
    def _build_mock(
        merged: Mapping[str, Any],
        runtime_args: Mapping[str, Any],
    ) -> MockLLMProvider:
        """Khởi tạo `MockLLMProvider` từ cấu hình đã xác thực."""
        if runtime_args.get("http_client") is not None or runtime_args.get("client") is not None:
            raise ProviderConfigError(
                "MockLLMProvider không nhận 'http_client' hoặc 'client'."
            )

        raw_model_id = merged.get("model_id")
        if not isinstance(raw_model_id, str) or not raw_model_id.strip():
            raise ProviderConfigError("Cấu hình mock thiếu trường 'model_id' hợp lệ.")

        seed = merged.get("seed")
        if seed is None and isinstance(merged.get("sampling"), Mapping):
            seed = merged["sampling"].get("seed")

        return MockLLMProvider(
            model_id=raw_model_id.strip(),
            response_sequence=runtime_args.get("response_sequence"),
            keyed_responses=runtime_args.get("keyed_responses"),
            seed=seed,
            seeded_variants=runtime_args.get("seeded_variants"),
        )

    @staticmethod
    def _build_ollama(
        merged: Mapping[str, Any],
        runtime_args: Mapping[str, Any],
    ) -> OllamaLocalProvider:
        """Khởi tạo `OllamaLocalProvider` từ cấu hình đã xác thực."""
        disallowed = [
            key
            for key in ("client", "response_sequence", "keyed_responses", "seeded_variants")
            if runtime_args.get(key) is not None
        ]
        if disallowed:
            raise ProviderConfigError(
                f"OllamaLocalProvider không hỗ trợ tham số override: {disallowed}."
            )

        config_fields: dict[str, Any] = {
            key: merged[key]
            for key in (
                "model_id",
                "base_url_env",
                "quantization",
                "context_window",
                "sampling",
                "timeout_sec",
                "hardware_profile",
            )
            if key in merged
        }
        try:
            ollama_config = OllamaProviderConfig.model_validate(config_fields)
        except ValidationError as exc:
            raise ProviderConfigError(f"Cấu hình Ollama không hợp lệ: {exc}") from exc

        return OllamaLocalProvider(
            config=ollama_config,
            http_client=runtime_args.get("http_client"),
        )

    @staticmethod
    def _build_gemini(
        merged: Mapping[str, Any],
        runtime_args: Mapping[str, Any],
    ) -> GeminiAPIProvider:
        """Khởi tạo `GeminiAPIProvider` kèm các rào kiểm định bảo mật bắt buộc."""
        disallowed = [
            key
            for key in ("http_client", "response_sequence", "keyed_responses", "seeded_variants")
            if runtime_args.get(key) is not None
        ]
        if disallowed:
            raise ProviderConfigError(
                f"GeminiAPIProvider không hỗ trợ tham số override: {disallowed}."
            )

        config_fields: dict[str, Any] = {
            key: merged[key]
            for key in (
                "model_id",
                "api_key_env",
                "data_classification_allowed",
                "merchant_dpa_status",
                "sampling",
                "timeout_sec",
            )
            if key in merged
        }
        try:
            gemini_config = GeminiProviderConfig.model_validate(config_fields)
        except ValidationError as exc:
            raise ProviderConfigError(f"Cấu hình Gemini không hợp lệ: {exc}") from exc

        return GeminiAPIProvider(
            config=gemini_config,
            client=runtime_args.get("client"),
        )
