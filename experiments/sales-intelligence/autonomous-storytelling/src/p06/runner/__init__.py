"""Gói điều phối thực nghiệm tái lập cho P06 (`p06.runner`).

1. File này giải quyết vấn đề gì?
   Cung cấp điểm nhập công khai duy nhất cho cấu hình chạy, mock fixture, bộ thu thập
   bằng chứng, tạo manifest, chạy phiên cô lập và chạy quét đa cấu hình P06-E01.
2. Trách nhiệm chính của module là gì?
   Xuất đầy đủ các kiểu dữ liệu và hàm điều phối từ `config`, `mock_fixtures`,
   `evidence_collector`, `manifest`, `session_runner` và `sweep`.
3. Module này liên kết với các thành phần nào?
   Phục vụ CLI `experiments/p06_e01_no_comments/run_e01.py`, `tests/unit/test_experiment_runner.py`
   và tầng đánh giá `p06.evaluation`.
4. Input và output chính là gì?
   Input là `ExperimentRunConfig` hoặc tham số quét;
   Output là `ExperimentRunnerResult` / `SweepResult` cùng 10 tệp artifact bất biến mỗi lần chạy.
5. Có những constraints hoặc invariants quan trọng nào?
   - Không chạy live provider (`ollama`/`gemini`) nếu không vượt qua Offline Guard tường minh.
   - Không ghi đè thư mục run đã tồn tại và không làm rò rỉ khóa bí mật vào artifact.
"""

from __future__ import annotations

from p06.runner.config import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_E01_CONFIG_PATH,
    DEFAULT_E01_STORY_PLANS_PATH,
    DEFAULT_E01_VERIFIED_SKUS_PATH,
    DEFAULT_MOCK_MODEL_CONFIG_PATH,
    DEFAULT_MODULE_ROOT,
    DEFAULT_PROMPTS_DIR,
    DEFAULT_RUNS_OUTPUT_DIR,
    LIVE_PROVIDERS,
    SCENARIO_DURATIONS_SEC,
    SUPPORTED_PROVIDERS,
    SUPPORTED_SCENARIOS,
    ExperimentMethod,
    ExperimentRunConfig,
    RunTerminationReason,
    build_sanitized_config_snapshot,
    load_e01_story_plan,
    load_experiment_run_config,
    load_yaml_mapping,
    sanitize_mapping_for_artifact,
)
from p06.runner.evidence_collector import EvidenceCollector
from p06.runner.manifest import (
    build_experiment_manifest,
    generate_run_id,
    persist_run_artifacts,
)
from p06.runner.mock_fixtures import build_e01_mock_provider
from p06.runner.session_runner import ExperimentRunnerResult, run_experiment
from p06.runner.sweep import (
    DEFAULT_E01_METHODS,
    DEFAULT_E01_SCENARIOS,
    HISTORY_WINDOW_SWEEP,
    SweepResult,
    run_e01_sweep,
)

__all__ = [
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_E01_CONFIG_PATH",
    "DEFAULT_E01_METHODS",
    "DEFAULT_E01_SCENARIOS",
    "DEFAULT_E01_STORY_PLANS_PATH",
    "DEFAULT_E01_VERIFIED_SKUS_PATH",
    "DEFAULT_MOCK_MODEL_CONFIG_PATH",
    "DEFAULT_MODULE_ROOT",
    "DEFAULT_PROMPTS_DIR",
    "DEFAULT_RUNS_OUTPUT_DIR",
    "EvidenceCollector",
    "ExperimentMethod",
    "ExperimentRunConfig",
    "ExperimentRunnerResult",
    "HISTORY_WINDOW_SWEEP",
    "LIVE_PROVIDERS",
    "RunTerminationReason",
    "SCENARIO_DURATIONS_SEC",
    "SUPPORTED_PROVIDERS",
    "SUPPORTED_SCENARIOS",
    "SweepResult",
    "build_e01_mock_provider",
    "build_experiment_manifest",
    "build_sanitized_config_snapshot",
    "generate_run_id",
    "load_e01_story_plan",
    "load_experiment_run_config",
    "load_yaml_mapping",
    "persist_run_artifacts",
    "run_e01_sweep",
    "run_experiment",
    "sanitize_mapping_for_artifact",
]
