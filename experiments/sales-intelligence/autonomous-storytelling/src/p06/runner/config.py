"""Cấu hình thực nghiệm bất biến và rào chắn ngoại tuyến cho `p06.runner` (E01-T08).

1. File này giải quyết vấn đề gì?
   Chuẩn hóa toàn bộ tham số của một lượt chạy thí nghiệm P06-E01 (`ExperimentRunConfig`),
   tách bạch phương pháp chạy (`ExperimentMethod`), lý do kết thúc (`RunTerminationReason`),
   nạp YAML cấu hình/kế hoạch từ đĩa và khóa chặt rào chắn cấm gọi provider trực tuyến ngoài ý muốn.
2. Trách nhiệm chính của module là gì?
   Định nghĩa `ExperimentMethod`, `RunTerminationReason`, `ExperimentRunConfig`, cùng các hàm
   `load_experiment_run_config`, `load_e01_story_plan`, `load_yaml_mapping` và
   `build_sanitized_config_snapshot`.
3. Module này liên kết với các thành phần nào?
   Tái sử dụng `RepetitionConfig` (`p06.memory.repetition_detector`), `ProviderConfigError`
   (`p06.providers.base`), `StoryPlan` và các kiểu kiểm định nghiêm ngặt từ `p06.schemas.story`
   và `p06.schemas.state`.
4. Input và output chính là gì?
   Input là đường dẫn YAML cấu hình mặc định/thí nghiệm/mô hình cùng các tham số ghi đè;
   Output là `ExperimentRunConfig` đã kiểm định toàn vẹn và `StoryPlan` đã `APPROVED`.
5. Có những constraints hoặc invariants quan trọng nào?
   - `history_window` bắt buộc nằm trong `[1, 100]` với `LANGGRAPH` và bắt buộc `None` với `SCRIPT_FIRST_*`.
   - Rào chắn ngoại tuyến (`Offline Guard`): ném `ProviderConfigError` ngay nếu `provider` là
     `ollama` hoặc `gemini` khi `allow_live_provider=False`.
   - Tuyệt đối không đưa giá trị biến môi trường hoặc khóa bí mật vào cấu hình xuất ra đĩa.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import Any, Final, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from p06.memory.repetition_detector import RepetitionConfig
from p06.providers.base import (
    SENSITIVE_SAMPLING_KEYS,
    ProviderConfigError,
    StrictNonNegFloat,
    StrictPositiveFloat,
)
from p06.schemas.state import (
    DEFAULT_MAX_REWRITE_RETRIES,
    DEFAULT_PLAYED_HISTORY_WINDOW,
    MAX_PLAYED_HISTORY_WINDOW,
    MAX_REWRITE_RETRIES_LIMIT,
)
from p06.schemas.story import (
    MAX_CHUNK_DURATION_SEC,
    NonBlankStr,
    StoryPlan,
    StrictNonNegInt,
    StrictPositiveInt,
)

# Gốc module P06 (`experiments/sales-intelligence/autonomous-storytelling/`).
DEFAULT_MODULE_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH: Final[Path] = DEFAULT_MODULE_ROOT / "configs" / "default.yaml"
DEFAULT_E01_CONFIG_PATH: Final[Path] = (
    DEFAULT_MODULE_ROOT / "configs" / "experiments" / "p06_e01.yaml"
)
DEFAULT_MOCK_MODEL_CONFIG_PATH: Final[Path] = DEFAULT_MODULE_ROOT / "configs" / "models" / "mock.yaml"
DEFAULT_E01_STORY_PLANS_PATH: Final[Path] = (
    DEFAULT_MODULE_ROOT / "data" / "story_plans" / "e01_story_plans.json"
)
DEFAULT_E01_VERIFIED_SKUS_PATH: Final[Path] = (
    DEFAULT_MODULE_ROOT / "data" / "products" / "e01_verified_skus.json"
)
DEFAULT_E01_EXT_V1_STORY_PLANS_PATH: Final[Path] = (
    DEFAULT_MODULE_ROOT / "data" / "story_plans" / "e01_ext_v1_story_plans.json"
)
DEFAULT_E01_EXT_V1_VERIFIED_SKUS_PATH: Final[Path] = (
    DEFAULT_MODULE_ROOT / "data" / "products" / "e01_ext_v1_verified_skus.json"
)
DEFAULT_PROMPTS_DIR: Final[Path] = DEFAULT_MODULE_ROOT / "prompts"
DEFAULT_RUNS_OUTPUT_DIR: Final[Path] = DEFAULT_MODULE_ROOT / "runs" / "P06-E01"

DEFAULT_MAX_CHUNK_DURATION_SEC: Final[float] = 8.0
DEFAULT_EXPERIMENT_SEED: Final[int] = 42
DEFAULT_MAX_TURNS: Final[int] = 500
DEFAULT_MAX_CONSECUTIVE_ABORTS: Final[int] = 3
DEFAULT_DATASET_PROFILE: Final[str] = "e01"

SCENARIO_DURATIONS_SEC: Final[dict[str, float]] = {
    "product_education_10m": 600.0,
    "brand_storytelling_10m": 600.0,
    "sales_presentation_30m": 1800.0,
}
EXT_V1_SCENARIO_DURATIONS_SEC: Final[dict[str, float]] = {
    "product_education_10m_ext": 600.0,
    "brand_storytelling_10m_ext": 600.0,
    "sales_presentation_30m_ext": 1800.0,
    "pilot_short_3sku_ext": 300.0,
    "window_sensitivity_stress_24t": 600.0,
}
ALL_SCENARIO_DURATIONS_SEC: Final[dict[str, float]] = {
    **SCENARIO_DURATIONS_SEC,
    **EXT_V1_SCENARIO_DURATIONS_SEC,
}
SUPPORTED_SCENARIOS: Final[frozenset[str]] = frozenset(SCENARIO_DURATIONS_SEC.keys())
SUPPORTED_EXT_V1_SCENARIOS: Final[frozenset[str]] = frozenset(EXT_V1_SCENARIO_DURATIONS_SEC.keys())
DATASET_PROFILES: Final[dict[str, dict[str, Any]]] = {
    "e01": {
        "story_plans_path": DEFAULT_E01_STORY_PLANS_PATH,
        "evidence_seed_path": DEFAULT_E01_VERIFIED_SKUS_PATH,
        "scenario_durations": SCENARIO_DURATIONS_SEC,
        "default_min_chunks_per_topic": 1,
    },
    "e01_ext_v1": {
        "story_plans_path": DEFAULT_E01_EXT_V1_STORY_PLANS_PATH,
        "evidence_seed_path": DEFAULT_E01_EXT_V1_VERIFIED_SKUS_PATH,
        "scenario_durations": EXT_V1_SCENARIO_DURATIONS_SEC,
        "default_min_chunks_per_topic": 1,
    },
}
LIVE_PROVIDERS: Final[frozenset[str]] = frozenset({"ollama", "gemini"})
SUPPORTED_PROVIDERS: Final[frozenset[str]] = frozenset({"mock", "ollama", "gemini"})


def resolve_dataset_profile(dataset_profile: str) -> dict[str, Any]:
    """Trả về cấu hình đường dẫn và kịch bản chuẩn cho một `dataset_profile` đã đăng ký."""
    key = dataset_profile.strip()
    if key not in DATASET_PROFILES:
        raise ValueError(
            f"dataset_profile '{dataset_profile}' không hợp lệ. Chỉ hỗ trợ: {sorted(DATASET_PROFILES)}."
        )
    return dict(DATASET_PROFILES[key])

_SAFE_TOKEN_CONFIG_KEYS: Final[frozenset[str]] = frozenset(
    {
        "max_tokens",
        "max_output_tokens",
        "max_input_tokens",
        "context_tokens",
        "token_usage",
        "token_usage_source",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "wasted_tokens",
        "wasted_input_tokens",
        "wasted_output_tokens",
        "thinking_tokens",
    }
)


class ExperimentMethod(str, Enum):
    """Các phương pháp sinh lời thoại được đối chiếu trong thí nghiệm P06-E01."""

    SCRIPT_FIRST_DETERMINISTIC = "script_first_deterministic"
    SCRIPT_FIRST_UPFRONT_LLM = "script_first_upfront_llm"
    LANGGRAPH = "langgraph_structured_story"


class RunTerminationReason(str, Enum):
    """Lý do dừng phiên chạy thực nghiệm được ghi nhận tường minh vào manifest."""

    EARLY_COMPLETION = "EARLY_COMPLETION"
    CONTENT_EXHAUSTED = "CONTENT_EXHAUSTED"
    TIME_BUDGET_EXHAUSTED = "TIME_BUDGET_EXHAUSTED"
    MAX_TURNS_REACHED = "MAX_TURNS_REACHED"
    MAX_CONSECUTIVE_ABORTS = "MAX_CONSECUTIVE_ABORTS"
    BUDGET_LIMIT_REACHED = "BUDGET_LIMIT_REACHED"
    FATAL_ERROR = "FATAL_ERROR"


def sanitize_mapping_for_artifact(mapping: Mapping[str, Any]) -> dict[str, Any]:
    """Loại bỏ hoặc che giấu đệ quy mọi khóa nhạy cảm trước khi lưu cấu hình/manifest xuống đĩa.

    Args:
        mapping: Từ điển cấu hình cần làm sạch.

    Returns:
        dict[str, Any]: Bản sao an toàn không chứa giá trị khóa bí mật.
    """
    cleaned: dict[str, Any] = {}
    for raw_key, value in mapping.items():
        key_str = str(raw_key)
        key_lower = key_str.strip().lower()
        # Giữ nguyên tên biến môi trường tham chiếu (vd: api_key_env, base_url_env) vì đây chỉ là tên khóa.
        is_env_name_ref = key_lower.endswith("_env")
        is_sensitive = (
            not is_env_name_ref
            and key_lower not in _SAFE_TOKEN_CONFIG_KEYS
            and any(sensitive in key_lower for sensitive in SENSITIVE_SAMPLING_KEYS)
        )
        if is_sensitive:
            cleaned[key_str] = "[REDACTED]"
        elif isinstance(value, Mapping):
            cleaned[key_str] = sanitize_mapping_for_artifact(value)
        elif isinstance(value, list):
            cleaned[key_str] = [
                sanitize_mapping_for_artifact(item) if isinstance(item, Mapping) else item
                for item in value
            ]
        else:
            cleaned[key_str] = value
    return cleaned


def load_yaml_mapping(yaml_path: Path) -> dict[str, Any]:
    """Đọc tệp YAML và kiểm định phần tử gốc phải là ánh xạ `dict`.

    Args:
        yaml_path: Đường dẫn tới tệp YAML cần nạp.

    Returns:
        dict[str, Any]: Nội dung YAML dạng từ điển.

    Raises:
        ProviderConfigError: Nếu tệp không tồn tại, lỗi YAML hoặc không phải ánh xạ.
    """
    resolved = Path(yaml_path)
    if not resolved.is_file():
        raise ProviderConfigError(f"Không tìm thấy tệp cấu hình YAML: '{resolved}'.")
    try:
        loaded = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ProviderConfigError(f"Lỗi đọc hoặc phân tích YAML '{resolved}': {exc}") from exc
    if not isinstance(loaded, Mapping):
        raise ProviderConfigError(
            f"Nội dung YAML trong '{resolved}' bắt buộc phải là dict ở cấp gốc."
        )
    return dict(loaded)


class ExperimentRunConfig(BaseModel):
    """Cấu hình bất biến cho một lần chạy thực nghiệm P06-E01.

    Attributes:
        experiment_id: Mã định danh thí nghiệm (mặc định `P06-E01`).
        scenario: Tên kịch bản trong `e01_story_plans.json`.
        method: Phương pháp chạy (`script_first_deterministic`, `script_first_upfront_llm`,
            hoặc `langgraph_structured_story`).
        provider: Tên provider (`mock`, `ollama`, `gemini`).
        model_config_path: Đường dẫn tệp YAML cấu hình model.
        history_window: Kích thước cửa sổ `W` trong `[1, 100]` (chỉ dùng cho `LANGGRAPH`,
            bắt buộc `None` cho `SCRIPT_FIRST_*`).
        seed: Hạt giống tất định cho chạy mô phỏng.
        max_chunk_duration_sec: Giới hạn thời lượng tối đa của một chunk (giây, `<= 30.0`).
        max_rewrite_retries: Ngân sách rewrite tối đa cho mỗi lượt LangGraph (`<= 5`).
        target_duration_sec: Ngân sách thời lượng mô phỏng của kịch bản (`600.0` hoặc `1800.0`).
        max_turns: Số lượt chạy tối đa để chặn vòng lặp vô hạn.
        max_consecutive_aborts: Số lượt `SAFE_ABORT_NO_CANDIDATE` liên tiếp tối đa trước khi dừng.
        output_dir: Thư mục gốc chứa các thư mục `run_id`.
        allow_live_provider: Cờ tường minh cho phép khởi tạo provider trực tuyến (`ollama`/`gemini`).
        repetition_config: Cấu hình ngưỡng phát hiện lặp của `RepetitionDetector`.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    experiment_id: NonBlankStr = "P06-E01"
    dataset_profile: NonBlankStr = DEFAULT_DATASET_PROFILE
    scenario: NonBlankStr
    method: ExperimentMethod
    provider: NonBlankStr = "mock"
    model_config_path: Path
    story_plans_path: Optional[Path] = None
    evidence_seed_path: Optional[Path] = None
    history_window: Optional[int] = None
    min_chunks_per_topic: StrictPositiveInt = 1
    seed: StrictInt = DEFAULT_EXPERIMENT_SEED
    max_chunk_duration_sec: StrictPositiveFloat = DEFAULT_MAX_CHUNK_DURATION_SEC
    max_rewrite_retries: StrictNonNegInt = DEFAULT_MAX_REWRITE_RETRIES
    target_duration_sec: StrictPositiveFloat = 600.0
    max_turns: StrictPositiveInt = DEFAULT_MAX_TURNS
    max_consecutive_aborts: StrictPositiveInt = DEFAULT_MAX_CONSECUTIVE_ABORTS
    max_llm_calls: Optional[StrictPositiveInt] = None
    max_estimated_cost_usd: Optional[StrictNonNegFloat] = None
    output_dir: Path
    allow_live_provider: StrictBool = False
    repetition_config: RepetitionConfig = Field(default_factory=RepetitionConfig)

    @model_validator(mode="before")
    @classmethod
    def _derive_defaults_before_validation(cls, data: Any) -> Any:
        """Tự suy diễn `dataset_profile` và `target_duration_sec` từ `scenario` nếu caller không truyền tường minh."""
        if not isinstance(data, Mapping):
            return data
        copied = dict(data)
        if isinstance(copied.get("provider"), str):
            copied["provider"] = copied["provider"].strip().lower()
        scenario_key = copied["scenario"].strip() if isinstance(copied.get("scenario"), str) else ""
        if copied.get("dataset_profile") is None and scenario_key in EXT_V1_SCENARIO_DURATIONS_SEC:
            copied["dataset_profile"] = "e01_ext_v1"
        if copied.get("target_duration_sec") is None and scenario_key in ALL_SCENARIO_DURATIONS_SEC:
            copied["target_duration_sec"] = ALL_SCENARIO_DURATIONS_SEC[scenario_key]
        return copied

    @model_validator(mode="after")
    def validate_config_invariants(self) -> ExperimentRunConfig:
        """Kiểm định tính hợp lệ của profile, scenario, provider, cửa sổ W và rào chắn ngoại tuyến."""
        profile_cfg = resolve_dataset_profile(self.dataset_profile)
        allowed_scenarios = profile_cfg["scenario_durations"]
        if self.scenario not in allowed_scenarios:
            raise ValueError(
                f"Kịch bản '{self.scenario}' không hợp lệ cho dataset_profile='{self.dataset_profile}'. "
                f"Chỉ hỗ trợ: {sorted(allowed_scenarios.keys())}."
            )
        if self.provider not in SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Provider '{self.provider}' không hợp lệ. Chỉ hỗ trợ: {sorted(SUPPORTED_PROVIDERS)}."
            )
        if self.provider in LIVE_PROVIDERS and not self.allow_live_provider:
            raise ValueError(
                f"Offline Guard: provider '{self.provider}' bị chặn khi allow_live_provider=False."
            )
        if self.max_chunk_duration_sec > MAX_CHUNK_DURATION_SEC:
            raise ValueError(
                f"max_chunk_duration_sec ({self.max_chunk_duration_sec}) vượt giới hạn tối đa "
                f"{MAX_CHUNK_DURATION_SEC}."
            )
        if self.max_rewrite_retries > MAX_REWRITE_RETRIES_LIMIT:
            raise ValueError(
                f"max_rewrite_retries ({self.max_rewrite_retries}) vượt giới hạn tối đa "
                f"{MAX_REWRITE_RETRIES_LIMIT}."
            )

        if self.history_window is not None and isinstance(self.history_window, bool):
            raise ValueError("history_window không được có kiểu bool.")

        if self.method == ExperimentMethod.LANGGRAPH:
            if self.history_window is None:
                raise ValueError(
                    "Phương pháp langgraph_structured_story bắt buộc phải khai báo history_window (1..100)."
                )
            if not (1 <= self.history_window <= MAX_PLAYED_HISTORY_WINDOW):
                raise ValueError(
                    f"history_window phải nằm trong [1, {MAX_PLAYED_HISTORY_WINDOW}], "
                    f"nhận được {self.history_window}."
                )
        else:
            if self.history_window is not None:
                raise ValueError(
                    f"Phương pháp '{self.method.value}' không dùng short_term_played_history "
                    f"nên history_window bắt buộc phải là None, nhận được {self.history_window}."
                )

        return self


def load_experiment_run_config(
    *,
    scenario: str,
    method: ExperimentMethod | str,
    dataset_profile: str = DEFAULT_DATASET_PROFILE,
    provider: str = "mock",
    model_config_path: Optional[Path] = None,
    default_config_path: Optional[Path] = None,
    experiment_config_path: Optional[Path] = None,
    story_plans_path: Optional[Path] = None,
    evidence_seed_path: Optional[Path] = None,
    history_window: Optional[int] = None,
    min_chunks_per_topic: Optional[int] = None,
    seed: Optional[int] = None,
    max_chunk_duration_sec: Optional[float] = None,
    max_rewrite_retries: Optional[int] = None,
    target_duration_sec: Optional[float] = None,
    max_turns: int = DEFAULT_MAX_TURNS,
    max_consecutive_aborts: int = DEFAULT_MAX_CONSECUTIVE_ABORTS,
    max_llm_calls: Optional[int] = None,
    max_estimated_cost_usd: Optional[float] = None,
    output_dir: Optional[Path] = None,
    allow_live_provider: bool = False,
    repetition_config: Optional[RepetitionConfig] = None,
) -> ExperimentRunConfig:
    """Nạp cấu hình thực nghiệm từ YAML mặc định, YAML thí nghiệm và YAML mô hình kèm Offline Guard.

    Args:
        scenario: Tên kịch bản trong `e01_story_plans.json`.
        method: Phương pháp thực nghiệm (`ExperimentMethod` hoặc chuỗi tương ứng).
        provider: Tên provider mục tiêu (`mock`, `ollama`, `gemini`).
        model_config_path: Đường dẫn YAML model (mặc định suy từ `default.yaml` theo tier).
        default_config_path: Đường dẫn `configs/default.yaml`.
        experiment_config_path: Đường dẫn `configs/experiments/p06_e01.yaml`.
        history_window: Kích thước cửa sổ `W` (mặc định đọc từ `default.yaml` cho `LANGGRAPH`,
            bắt buộc `None` cho `SCRIPT_FIRST_*`).
        seed: Hạt giống ngẫu nhiên (mặc định lấy từ `default.yaml`).
        max_chunk_duration_sec: Ngưỡng thời lượng chunk (mặc định lấy từ `default.yaml`).
        max_rewrite_retries: Số lần rewrite tối đa (mặc định lấy từ `default.yaml`).
        target_duration_sec: Thời lượng mô phỏng mục tiêu (mặc định suy từ `scenario`).
        max_turns: Giới hạn số lượt chạy tối đa.
        max_consecutive_aborts: Giới hạn số lượt abort liên tiếp.
        output_dir: Thư mục lưu các lần chạy (mặc định `runs/P06-E01`).
        allow_live_provider: Cờ cho phép nạp provider trực tuyến (`ollama`/`gemini`).
        repetition_config: Cấu hình `RepetitionConfig` tùy chọn.

    Returns:
        ExperimentRunConfig: Cấu hình đã kiểm định đầy đủ và sẵn sàng cho `run_experiment`.

    Raises:
        ProviderConfigError: Nếu vi phạm Offline Guard, tệp YAML thiếu/sai định dạng hoặc
            `provider` lệch với `model_config_path`.
        ValueError: Nếu tham số `scenario`, `method`, hoặc `history_window` không hợp lệ.
    """
    if isinstance(history_window, bool):
        raise ValueError("history_window không được có kiểu bool.")

    resolved_method = (
        method if isinstance(method, ExperimentMethod) else ExperimentMethod(method.strip())
    )
    normalized_provider = provider.strip().lower() if isinstance(provider, str) else ""
    if normalized_provider not in SUPPORTED_PROVIDERS:
        raise ProviderConfigError(
            f"Provider '{provider}' không được hỗ trợ. Chỉ chấp nhận: {sorted(SUPPORTED_PROVIDERS)}."
        )

    # Rào chắn ngoại tuyến tầng 1: chặn provider trực tuyến trước khi đụng tới YAML/SDK.
    if normalized_provider in LIVE_PROVIDERS and not allow_live_provider:
        raise ProviderConfigError(
            f"Offline Guard: từ chối cấu hình provider trực tuyến '{normalized_provider}' "
            f"vì allow_live_provider=False."
        )

    default_yaml = load_yaml_mapping(default_config_path or DEFAULT_CONFIG_PATH)
    exp_yaml = load_yaml_mapping(experiment_config_path or DEFAULT_E01_CONFIG_PATH)

    if model_config_path is None:
        tiers = default_yaml.get("provider", {}).get("tiers", {})
        tier_key_by_provider = {
            "mock": "unit_test",
            "ollama": "local_smoke_test",
            "gemini": "formal_experiment",
        }
        rel_path = tiers.get(tier_key_by_provider[normalized_provider])
        if not isinstance(rel_path, str) or not rel_path.strip():
            raise ProviderConfigError(
                f"Không tìm thấy đường dẫn model_config mặc định cho provider '{normalized_provider}'."
            )
        resolved_model_path = (DEFAULT_MODULE_ROOT / rel_path.strip()).resolve()
    else:
        resolved_model_path = Path(model_config_path).resolve()

    model_yaml = load_yaml_mapping(resolved_model_path)
    yaml_provider = str(model_yaml.get("provider", "")).strip().lower()
    if yaml_provider in LIVE_PROVIDERS and not allow_live_provider:
        raise ProviderConfigError(
            f"Offline Guard: tệp model '{resolved_model_path}' khai báo provider '{yaml_provider}' "
            f"nhưng allow_live_provider=False."
        )
    if yaml_provider != normalized_provider:
        raise ProviderConfigError(
            f"Xung đột provider: yêu cầu '{normalized_provider}' nhưng '{resolved_model_path}' "
            f"khai báo '{yaml_provider}'."
        )

    resolved_seed = (
        seed
        if seed is not None
        else int(default_yaml.get("experiment", {}).get("seed", DEFAULT_EXPERIMENT_SEED))
    )
    resolved_max_chunk_sec = (
        float(max_chunk_duration_sec)
        if max_chunk_duration_sec is not None
        else float(
            default_yaml.get("chunking_policy", {}).get(
                "max_duration_sec", DEFAULT_MAX_CHUNK_DURATION_SEC
            )
        )
    )
    resolved_max_retries = (
        max_rewrite_retries
        if max_rewrite_retries is not None
        else int(default_yaml.get("guardrails", {}).get("max_rewrite_retries", DEFAULT_MAX_REWRITE_RETRIES))
    )

    if resolved_method == ExperimentMethod.LANGGRAPH:
        resolved_window = (
            history_window
            if history_window is not None
            else int(
                default_yaml.get("memory_policy", {})
                .get("short_term_played_history", {})
                .get("window_chunks", DEFAULT_PLAYED_HISTORY_WINDOW)
            )
        )
    else:
        if history_window is not None:
            raise ValueError(
                f"Không được truyền history_window={history_window} cho phương pháp "
                f"'{resolved_method.value}' (chỉ dùng cho langgraph_structured_story)."
            )
        resolved_window = None

    profile_cfg = resolve_dataset_profile(dataset_profile)
    allowed_durations: dict[str, float] = profile_cfg["scenario_durations"]
    resolved_scenario = scenario.strip()
    if resolved_scenario not in allowed_durations:
        raise ValueError(
            f"Kịch bản '{resolved_scenario}' không hợp lệ cho dataset_profile='{dataset_profile}'. "
            f"Chỉ hỗ trợ: {sorted(allowed_durations.keys())}."
        )
    resolved_target_duration = (
        float(target_duration_sec)
        if target_duration_sec is not None
        else allowed_durations[resolved_scenario]
    )
    resolved_story_plans_path = (
        Path(story_plans_path).resolve()
        if story_plans_path is not None
        else Path(profile_cfg["story_plans_path"]).resolve()
    )
    resolved_evidence_seed_path = (
        Path(evidence_seed_path).resolve()
        if evidence_seed_path is not None
        else Path(profile_cfg["evidence_seed_path"]).resolve()
    )
    resolved_min_chunks = (
        min_chunks_per_topic
        if min_chunks_per_topic is not None
        else int(profile_cfg.get("default_min_chunks_per_topic", 1))
    )

    experiment_id = str(exp_yaml.get("experiment_id", "P06-E01")).strip() or "P06-E01"
    resolved_output_dir = (
        Path(output_dir).resolve()
        if output_dir is not None
        else DEFAULT_RUNS_OUTPUT_DIR.resolve()
    )

    return ExperimentRunConfig(
        experiment_id=experiment_id,
        dataset_profile=dataset_profile.strip(),
        scenario=resolved_scenario,
        method=resolved_method,
        provider=normalized_provider,
        model_config_path=resolved_model_path,
        story_plans_path=resolved_story_plans_path,
        evidence_seed_path=resolved_evidence_seed_path,
        history_window=resolved_window,
        min_chunks_per_topic=resolved_min_chunks,
        seed=resolved_seed,
        max_chunk_duration_sec=resolved_max_chunk_sec,
        max_rewrite_retries=resolved_max_retries,
        target_duration_sec=resolved_target_duration,
        max_turns=max_turns,
        max_consecutive_aborts=max_consecutive_aborts,
        max_llm_calls=max_llm_calls,
        max_estimated_cost_usd=max_estimated_cost_usd,
        output_dir=resolved_output_dir,
        allow_live_provider=allow_live_provider,
        repetition_config=repetition_config or RepetitionConfig(),
    )


def load_e01_story_plan(
    scenario: str,
    *,
    story_plans_path: Optional[Path] = None,
) -> tuple[StoryPlan, dict[str, Any], Path]:
    """Nạp `StoryPlan` đã `APPROVED` và metadata dataset cho một kịch bản E01.

    Args:
        scenario: Khóa kịch bản trong `e01_story_plans.json`.
        story_plans_path: Đường dẫn tệp JSON kế hoạch (mặc định `data/story_plans/e01_story_plans.json`).

    Returns:
        tuple[StoryPlan, dict[str, Any], Path]: Bộ gồm `StoryPlan`, `dataset_meta`, và đường dẫn đã đọc.

    Raises:
        FileNotFoundError: Nếu tệp kế hoạch không tồn tại.
        KeyError: Nếu không tìm thấy khóa `scenario` trong `plans`.
    """
    resolved_path = (story_plans_path or DEFAULT_E01_STORY_PLANS_PATH).resolve()
    if not resolved_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy tệp StoryPlan E01: '{resolved_path}'.")
    raw = json.loads(resolved_path.read_text(encoding="utf-8"))
    plans = raw.get("plans", {})
    if scenario not in plans:
        raise KeyError(
            f"Không tìm thấy kịch bản '{scenario}' trong '{resolved_path}'. "
            f"Các kịch bản hiện có: {sorted(plans.keys())}."
        )
    plan = StoryPlan.model_validate(plans[scenario])
    dataset_meta = dict(raw.get("dataset_meta", {}))
    return plan, dataset_meta, resolved_path


def build_sanitized_config_snapshot(
    config: ExperimentRunConfig,
    model_yaml: Mapping[str, Any],
) -> dict[str, Any]:
    """Tạo bản chụp YAML an toàn để lưu thành `config.yaml` trong thư mục run.

    Args:
        config: Cấu hình chạy thực nghiệm.
        model_yaml: Nội dung YAML model đã nạp.

    Returns:
        dict[str, Any]: Từ điển cấu hình đã lọc sạch mọi thông tin nhạy cảm.
    """
    raw_snapshot = {
        "experiment_id": config.experiment_id,
        "dataset_profile": config.dataset_profile,
        "scenario": config.scenario,
        "method": config.method.value,
        "provider": config.provider,
        "model_config_path": str(config.model_config_path),
        "story_plans_path": str(config.story_plans_path) if config.story_plans_path else None,
        "evidence_seed_path": str(config.evidence_seed_path) if config.evidence_seed_path else None,
        "model_config": sanitize_mapping_for_artifact(model_yaml),
        "history_window": config.history_window,
        "min_chunks_per_topic": config.min_chunks_per_topic,
        "seed": config.seed,
        "max_chunk_duration_sec": config.max_chunk_duration_sec,
        "max_rewrite_retries": config.max_rewrite_retries,
        "target_duration_sec": config.target_duration_sec,
        "max_turns": config.max_turns,
        "max_consecutive_aborts": config.max_consecutive_aborts,
        "max_llm_calls": config.max_llm_calls,
        "max_estimated_cost_usd": config.max_estimated_cost_usd,
        "output_dir": str(config.output_dir),
        "allow_live_provider": config.allow_live_provider,
        "repetition_config": config.repetition_config.model_dump(mode="json"),
    }
    return sanitize_mapping_for_artifact(raw_snapshot)
