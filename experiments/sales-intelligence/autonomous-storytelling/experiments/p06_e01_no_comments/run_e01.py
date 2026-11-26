"""Giao diện dòng lệnh (CLI) chạy thí nghiệm ngoại tuyến P06-E01 (`run_e01.py`).

1. File này giải quyết vấn đề gì?
   Cung cấp điểm khởi chạy chuẩn cho thí nghiệm P06-E01 (chạy đơn lẻ hoặc chạy quét sweep
   đa phương pháp / đa cửa sổ W) từ dòng lệnh với đầu ra artifact tái lập.
2. Trách nhiệm chính của module là gì?
   Phân tích tham số CLI (`argparse`), thực thi rào chắn cứng chặn hoàn toàn provider
   trực tuyến (`ollama`, `gemini`) trong giai đoạn T08, và điều phối gọi `run_experiment()`
   hoặc `run_e01_sweep()`.
3. Module này liên kết với các thành phần nào?
   Nhập trực tiếp từ `p06.runner` (`load_experiment_run_config`, `run_experiment`,
   `run_e01_sweep`, `load_yaml_mapping`).
4. Input và output chính là gì?
   Input là các cờ CLI (`--provider`, `--method`, `--scenario`, `--history-window`, `--seed`,
   `--config`, `--output-dir`, `--sweep`, `--export-human-eval`);
   Output là thông báo tóm tắt JSON hoặc mã lỗi `SystemExit` khi vi phạm rào chắn.
5. Có những constraints hoặc invariants quan trọng nào?
   - Trong T08, MỌI yêu cầu dùng `ollama` hoặc `gemini` (qua `--provider` hoặc trong tệp
     `--config`) đều bị từ chối cứng ngay ở tầng CLI để tránh gọi mô hình ngoài ý muốn.
   - Không truyền `history_window` cho `script_first_*` (mặc định `10` chỉ cho `langgraph`).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

# Bảo đảm nạp được gói `p06` khi chạy trực tiếp tệp CLI từ thư mục gốc module hoặc repo.
_MODULE_ROOT = Path(__file__).resolve().parents[2]
_SRC_DIR = _MODULE_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from p06.providers.base import ProviderConfigError  # noqa: E402
from p06.runner.config import (  # noqa: E402
    DEFAULT_MOCK_MODEL_CONFIG_PATH,
    DEFAULT_RUNS_OUTPUT_DIR,
    LIVE_PROVIDERS,
    SUPPORTED_SCENARIOS,
    ExperimentMethod,
    load_experiment_run_config,
    load_yaml_mapping,
)
from p06.runner.session_runner import run_experiment  # noqa: E402
from p06.runner.sweep import DEFAULT_E01_SCENARIOS, HISTORY_WINDOW_SWEEP, run_e01_sweep  # noqa: E402


def build_arg_parser() -> argparse.ArgumentParser:
    """Tạo bộ phân tích đối số dòng lệnh chuẩn cho thí nghiệm P06-E01."""
    parser = argparse.ArgumentParser(
        description="HOSTRA AI P06-E01 Offline Experiment Runner (Mock-only in T08)."
    )
    parser.add_argument(
        "--provider",
        default="mock",
        help="LLM provider (T08 chỉ cho phép 'mock'; 'ollama'/'gemini' bị chặn cứng).",
    )
    parser.add_argument(
        "--method",
        default=ExperimentMethod.LANGGRAPH.value,
        choices=[m.value for m in ExperimentMethod],
        help="Phương pháp chạy đơn lẻ.",
    )
    parser.add_argument(
        "--scenario",
        default=None,
        choices=sorted(SUPPORTED_SCENARIOS),
        help=(
            "Tên kịch bản E01 trong data/story_plans/e01_story_plans.json "
            "(mặc định product_education_10m khi chạy đơn, hoặc toàn bộ 3 kịch bản khi --sweep)."
        ),
    )
    parser.add_argument(
        "--history-window",
        type=int,
        default=None,
        help="Kích thước cửa sổ W (chỉ dùng cho langgraph_structured_story, vd: 5, 10, 20).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Hạt giống tất định cho chạy mô phỏng.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Đường dẫn tệp YAML cấu hình model (mặc định configs/models/mock.yaml).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_RUNS_OUTPUT_DIR,
        help="Thư mục lưu kết quả các lượt chạy và bảng so sánh.",
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Chạy toàn bộ sweep (script_first_* 1x/kịch bản + langgraph W in {5,10,20}).",
    )
    parser.add_argument(
        "--export-human-eval",
        action="store_true",
        help="Xuất thêm phiếu chấm mù rubric khi chạy sweep.",
    )
    return parser


def _enforce_t08_offline_safeguard(provider: str, config_path: Optional[Path]) -> None:
    """Rào chắn cứng tầng CLI của T08: từ chối tuyệt đối mọi provider trực tuyến."""
    normalized = provider.strip().lower()
    if normalized in LIVE_PROVIDERS or normalized != "mock":
        raise SystemExit(
            f"[T08 BLOCKED] Live provider '{provider}' bị chặn cứng trong E01-T08. "
            f"Chỉ được phép chạy ngoại tuyến với --provider mock."
        )
    resolved_cfg = (config_path or DEFAULT_MOCK_MODEL_CONFIG_PATH).resolve()
    try:
        model_yaml = load_yaml_mapping(resolved_cfg)
    except ProviderConfigError as exc:
        raise SystemExit(f"[CONFIG ERROR] {exc}") from exc
    yaml_provider = str(model_yaml.get("provider", "")).strip().lower()
    if yaml_provider in LIVE_PROVIDERS or yaml_provider != "mock":
        raise SystemExit(
            f"[T08 BLOCKED] Tệp cấu hình '{resolved_cfg}' khai báo provider '{yaml_provider}'. "
            f"E01-T08 chặn hoàn toàn Ollama và Gemini."
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Điểm vào chính của CLI `run_e01.py`."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    _enforce_t08_offline_safeguard(args.provider, args.config)

    if args.sweep:
        sweep_scenarios = (args.scenario,) if args.scenario is not None else DEFAULT_E01_SCENARIOS
        sweep_res = run_e01_sweep(
            scenarios=sweep_scenarios,
            history_windows=HISTORY_WINDOW_SWEEP,
            provider="mock",
            model_config_path=args.config,
            seed=args.seed,
            output_dir=args.output_dir,
            allow_live_provider=False,
            export_human_eval=args.export_human_eval,
        )
        summary = {
            "mode": "sweep",
            "sweep_id": sweep_res.sweep_id,
            "scenarios": list(sweep_scenarios),
            "total_runs": len(sweep_res.run_results),
            "output_dir": str(sweep_res.output_dir),
            "comparison_json": str(sweep_res.comparison_json_path),
            "comparison_csv": str(sweep_res.comparison_csv_path),
            "comparison_md": str(sweep_res.comparison_md_path),
            "human_eval_dir": str(sweep_res.human_eval_dir) if sweep_res.human_eval_dir else None,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    selected_scenario = args.scenario or "product_education_10m"
    method = ExperimentMethod(args.method)
    try:
        run_cfg = load_experiment_run_config(
            scenario=selected_scenario,
            method=method,
            provider="mock",
            model_config_path=args.config,
            history_window=args.history_window,
            seed=args.seed,
            output_dir=args.output_dir,
            allow_live_provider=False,
        )
    except (ProviderConfigError, ValueError) as exc:
        raise SystemExit(f"[CONFIG ERROR] {exc}") from exc

    result = run_experiment(run_cfg)
    summary = {
        "mode": "single",
        "run_id": result.run_id,
        "run_dir": str(result.run_dir),
        "method": result.manifest["method"],
        "scenario": result.manifest["scenario"],
        "history_window": result.manifest["history_window"],
        "termination_reason": result.termination_reason.value,
        "transcript_turns": len(result.evidence.transcript),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
