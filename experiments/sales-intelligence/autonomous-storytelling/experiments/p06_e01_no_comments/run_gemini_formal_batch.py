"""Bộ điều phối batch Formal Benchmark dùng sổ cái ngân sách toàn cục (`P06-E01-T09`).

1. File này giải quyết vấn đề gì?
   Điều phối chuỗi chạy Formal Benchmark (ví dụ Batch 1A: `script_first_upfront_llm` và
   `langgraph_structured_story W=5/10/20`) trên một ngân sách request toàn cục duy nhất
   (`global_max_requests=120`, `max_requests_per_run=30`) với `0 USD` Free Tier.
2. Trách nhiệm chính của module là gì?
   Đọc tệp YAML cấu hình batch, thực thi Offline Guard (cấm gọi provider trực tuyến nếu
   thiếu `--allow-live-provider`), xác minh cấu hình `free_tier` / `0 USD`, duy trì sổ cái
   `budget_ledger.json` liên lượt chạy qua chung một `GeminiRestClient`, ghi `batch_summary.json`
   kèm mã băm SHA-256 khóa tài nguyên, và xuất `comparison.{json,csv,md}` cùng `human_eval/`.
3. Module này liên kết với các thành phần nào?
   Tái sử dụng `GeminiAPIProvider`, `GeminiProviderConfig`, `GeminiRestClient`,
   `ProviderConfigError`, `compute_prompt_hashes`, `load_experiment_run_config`,
   `resolve_dataset_profile`, `run_experiment`, `compare_runs`, và `export_blind_human_eval_sheets`.
4. Input và output chính là gì?
   Input là đường dẫn YAML batch (`--config`), tùy chọn `--provider` (`gemini`/`mock`),
   `--allow-live-provider`, và `--output-dir`;
   Output là `budget_ledger.json`, `batch_summary.json`, các thư mục run chuẩn 10 artifacts,
   báo cáo đối chiếu `comparison.*` và bộ phiếu chấm mù `human_eval/`.
5. Có những constraints hoặc invariants quan trọng nào?
   - TUYỆT ĐỐI không in, lưu hay rò rỉ `GEMINI_API_KEY`.
   - TUYỆT ĐỐI không gọi Gemini API khi thiếu `--allow-live-provider` hoặc vượt `global_max_requests`.
   - Ngắt an toàn khi `rate_limited=True` (HTTP 429) hoặc `FATAL_ERROR` và bảo toàn bằng chứng
     các lượt đã chạy xong trong `budget_ledger.json` và `batch_summary.json`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Optional

import yaml

# Bảo đảm nạp được gói `p06` khi chạy trực tiếp script CLI.
_MODULE_ROOT = Path(__file__).resolve().parents[2]
_SRC_DIR = _MODULE_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from p06.baselines.script_first import (  # noqa: E402
    _UPFRONT_PROMPT_SHA256,
    _UPFRONT_PROMPT_VERSION,
)
from p06.evaluation.comparison import (  # noqa: E402
    compare_runs,
    export_comparison_csv,
    export_comparison_json,
    export_comparison_markdown,
)
from p06.evaluation.human_eval import export_blind_human_eval_sheets  # noqa: E402
from p06.planning.prompt_loader import compute_prompt_hashes  # noqa: E402
from p06.providers.base import ProviderConfigError  # noqa: E402
from p06.providers.gemini_provider import (  # noqa: E402
    GeminiAPIProvider,
    GeminiProviderConfig,
    GeminiRestClient,
)
from p06.runner.config import (  # noqa: E402
    LIVE_PROVIDERS,
    ExperimentMethod,
    RunTerminationReason,
    load_experiment_run_config,
    resolve_dataset_profile,
)
from p06.runner.session_runner import run_experiment  # noqa: E402

DEFAULT_BATCH_CONFIG_PATH: Final[Path] = (
    _MODULE_ROOT / "configs" / "experiments" / "p06_e01_formal_batch1a.yaml"
)


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_or_init_batch_ledger(
    ledger_path: Path,
    *,
    batch_cfg: Mapping[str, Any],
    provider: str,
) -> dict[str, Any]:
    if ledger_path.is_file():
        return dict(json.loads(ledger_path.read_text(encoding="utf-8")))
    return {
        "batch_id": str(batch_cfg["batch_id"]),
        "experiment_id": str(batch_cfg.get("experiment_id", "P06-E01")),
        "provider": provider,
        "model_id": str(batch_cfg["model_id"]) if provider == "gemini" else "deterministic-mock-v0.1",
        "billing_tier": str(batch_cfg.get("billing_tier", "free_tier")),
        "max_cost_usd": float(batch_cfg.get("max_cost_usd", 0.0)),
        "data_classification": str(batch_cfg.get("data_classification", "SYNTHETIC")),
        "max_requests_per_run": int(batch_cfg["max_requests_per_run"]),
        "global_max_requests": int(batch_cfg["global_max_requests"]),
        "min_request_interval_sec": float(batch_cfg.get("min_request_interval_sec", 6.0)),
        "total_requests": 0,
        "rate_limited": False,
        "status": "INITIALIZED",
        "runs": {},
        "events": [],
    }


def _load_gemini_model_config(config_path: Path) -> tuple[GeminiProviderConfig, dict[str, Any]]:
    raw_yaml = dict(yaml.safe_load(config_path.read_text(encoding="utf-8")) or {})
    fields = {
        k: raw_yaml[k]
        for k in (
            "model_id",
            "api_key_env",
            "data_classification_allowed",
            "merchant_dpa_status",
            "sampling",
            "thinking_budget",
            "thinking_level",
            "min_request_interval_sec",
            "timeout_sec",
        )
        if k in raw_yaml
    }
    return GeminiProviderConfig.model_validate(fields), raw_yaml


def _summarize_partial_token_usage(run_dir: Path) -> dict[str, Any]:
    """Tổng hợp token đo được trên từng call thành công và liệt kê rõ phần thiếu nếu có."""
    token_path = run_dir / "token_usage.json"
    token_doc = json.loads(token_path.read_text(encoding="utf-8")) if token_path.is_file() else {}
    calls_path = run_dir / "provider_calls.jsonl"
    call_rows: list[dict[str, Any]] = []
    if calls_path.is_file():
        call_rows = [
            json.loads(line)
            for line in calls_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    measured_calls = [row for row in call_rows if row.get("token_usage_source") == "MEASURED"]
    missing_calls = [row for row in call_rows if row.get("token_usage_source") != "MEASURED"]
    return {
        "aggregate_token_usage_source": token_doc.get("token_usage_source", "UNAVAILABLE"),
        "aggregate_input_tokens": token_doc.get("input_tokens"),
        "aggregate_output_tokens": token_doc.get("output_tokens"),
        "measured_calls_count": len(measured_calls),
        "failed_calls_count": len(missing_calls),
        "missing_token_call_indices": [row.get("call_index") for row in missing_calls],
        "partial_measured_input_tokens": sum(int(row.get("input_tokens") or 0) for row in measured_calls),
        "partial_measured_output_tokens": sum(int(row.get("output_tokens") or 0) for row in measured_calls),
    }


def _collect_artifact_locks(
    *,
    batch_config_path: Path,
    model_config_path: Optional[Path],
    dataset_profile: str,
) -> dict[str, Any]:
    """Thu thập phiên bản và mã băm SHA-256 của bộ dữ liệu, StoryPlan, prompt và cấu hình khóa."""
    profile_cfg = resolve_dataset_profile(dataset_profile)
    skus_path = Path(profile_cfg["evidence_seed_path"]).resolve()
    plans_path = Path(profile_cfg["story_plans_path"]).resolve()
    skus_meta = json.loads(skus_path.read_text(encoding="utf-8")).get("dataset_meta", {})
    plans_meta = json.loads(plans_path.read_text(encoding="utf-8")).get("dataset_meta", {})
    prompt_hashes = compute_prompt_hashes()

    return {
        "dataset_profile": dataset_profile,
        "verified_skus_path": str(skus_path),
        "verified_skus_version": skus_meta.get("version"),
        "verified_skus_sha256": _file_sha256(skus_path),
        "story_plans_path": str(plans_path),
        "story_plans_version": plans_meta.get("version"),
        "story_plans_sha256": _file_sha256(plans_path),
        "prompt_hashes": prompt_hashes,
        "baseline_upfront_prompt_version": _UPFRONT_PROMPT_VERSION,
        "baseline_upfront_prompt_sha256": _UPFRONT_PROMPT_SHA256,
        "batch_config_path": str(batch_config_path.resolve()),
        "batch_config_sha256": _file_sha256(batch_config_path.resolve()),
        "model_config_path": str(model_config_path.resolve()) if model_config_path else None,
        "model_config_sha256": (
            _file_sha256(model_config_path.resolve()) if model_config_path and model_config_path.is_file() else None
        ),
    }


def load_batch_config(config_path: Path) -> dict[str, Any]:
    """Nạp và kiểm định tối thiểu tệp YAML cấu hình batch Formal Benchmark."""
    resolved = Path(config_path).resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Không tìm thấy tệp cấu hình batch: '{resolved}'.")
    raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise ValueError(f"Cấu hình batch '{resolved}' phải là mapping YAML hợp lệ.")
    required_keys = (
        "batch_id",
        "provider",
        "model_id",
        "dataset_profile",
        "scenario",
        "seed",
        "min_chunks_per_topic",
        "max_chunk_duration_sec",
        "max_requests_per_run",
        "global_max_requests",
        "output_dir",
        "runs",
    )
    missing = [key for key in required_keys if key not in raw]
    if missing:
        raise ValueError(f"Cấu hình batch '{resolved}' thiếu các trường bắt buộc: {missing}.")
    if not isinstance(raw["runs"], list) or not raw["runs"]:
        raise ValueError("Danh sách `runs` trong cấu hình batch không được rỗng.")
    return dict(raw)


def _validate_free_tier_safety(
    batch_cfg: Mapping[str, Any],
    *,
    resolved_provider: str,
    model_raw_yaml: Optional[Mapping[str, Any]],
) -> None:
    """Bảo đảm cấu hình tuân thủ Free Tier 0 USD và dữ liệu SYNTHETIC khi chạy Gemini."""
    if float(batch_cfg.get("max_cost_usd", 0.0)) != 0.0:
        raise ProviderConfigError("Batch Formal Free Tier chỉ cho phép `max_cost_usd == 0.0`.")
    if str(batch_cfg.get("data_classification", "")).strip().upper() != "SYNTHETIC":
        raise ProviderConfigError("Batch Formal Free Tier chỉ cho phép dữ liệu `SYNTHETIC`.")
    if resolved_provider != "gemini":
        return
    if not model_raw_yaml:
        raise ProviderConfigError("Thiếu YAML cấu hình model Gemini.")
    pricing = model_raw_yaml.get("pricing") or {}
    if str(pricing.get("tier", "")).strip() != "free_tier":
        raise ProviderConfigError("Model Gemini chạy batch bắt buộc thuộc `pricing.tier: free_tier`.")
    if float(pricing.get("input_per_1m_usd", -1.0)) != 0.0 or float(
        pricing.get("output_per_1m_usd", -1.0)
    ) != 0.0:
        raise ProviderConfigError("Model Gemini chạy batch bắt buộc có đơn giá 0.0 USD.")


def execute_formal_batch(
    config_path: Path,
    *,
    provider_override: Optional[str] = None,
    allow_live_provider: bool = False,
    output_dir_override: Optional[Path] = None,
    rest_client_factory: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Thực thi tuần tự một batch Formal Benchmark với sổ cái ngân sách toàn cục.

    Args:
        config_path: Đường dẫn tệp YAML cấu hình batch (ví dụ `p06_e01_formal_batch1a.yaml`).
        provider_override: Tùy chọn ghi đè provider (`gemini` hoặc `mock`).
        allow_live_provider: Bắt buộc `True` nếu provider thực tế là `gemini`/`ollama`.
        output_dir_override: Thư mục đích tùy chọn (hữu ích cho kiểm thử ngoại tuyến).
        rest_client_factory: Hàm tạo `GeminiRestClient` tùy chọn cho unit test với fake client.

    Returns:
        dict[str, Any]: Tóm tắt kết quả batch, ngân sách toàn cục và đường dẫn báo cáo đối chiếu.

    Raises:
        ProviderConfigError: Nếu vi phạm Offline Guard hoặc cấu hình Free Tier 0 USD.
        RuntimeError: Nếu ngân sách toàn cục của batch đã cạn trước khi bắt đầu.
    """
    resolved_cfg_path = Path(config_path).resolve()
    batch_cfg = load_batch_config(resolved_cfg_path)
    resolved_provider = (provider_override or str(batch_cfg["provider"])).strip().lower()

    if resolved_provider in LIVE_PROVIDERS and not allow_live_provider:
        raise ProviderConfigError(
            f"Offline Guard: từ chối chạy batch với provider trực tuyến '{resolved_provider}' "
            "khi chưa truyền `--allow-live-provider`."
        )

    model_cfg_path: Optional[Path] = None
    gem_cfg: Optional[GeminiProviderConfig] = None
    model_raw_yaml: Optional[dict[str, Any]] = None
    if resolved_provider == "gemini":
        model_rel = str(batch_cfg.get("model_config_path") or "").strip()
        if not model_rel:
            raise ProviderConfigError("Thiếu `model_config_path` cho provider `gemini`.")
        model_cfg_path = (_MODULE_ROOT / model_rel).resolve()
        gem_cfg, model_raw_yaml = _load_gemini_model_config(model_cfg_path)
        if str(batch_cfg["model_id"]).strip() != gem_cfg.model_id:
            raise ProviderConfigError(
                f"Xung đột model_id: batch='{batch_cfg['model_id']}' vs YAML='{gem_cfg.model_id}'."
            )

    _validate_free_tier_safety(
        batch_cfg,
        resolved_provider=resolved_provider,
        model_raw_yaml=model_raw_yaml,
    )

    output_dir = (
        Path(output_dir_override).resolve()
        if output_dir_override is not None
        else (_MODULE_ROOT / str(batch_cfg["output_dir"])).resolve()
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    ledger_path = output_dir / "budget_ledger.json"
    ledger = _load_or_init_batch_ledger(
        ledger_path,
        batch_cfg=batch_cfg,
        provider=resolved_provider,
    )
    global_cap = int(ledger["global_max_requests"])
    per_run_cap = int(batch_cfg["max_requests_per_run"])
    remaining_global_at_start = global_cap - int(ledger["total_requests"])
    if remaining_global_at_start <= 0:
        ledger["status"] = "BLOCKED_BUDGET"
        _save_json(ledger_path, ledger)
        raise RuntimeError(
            f"[BUDGET BLOCKED] Ngân sách toàn cục của batch đã cạn "
            f"({ledger['total_requests']}/{global_cap})."
        )

    shared_rest_client: Any = None
    shared_gemini_provider: Optional[GeminiAPIProvider] = None
    if resolved_provider == "gemini":
        assert gem_cfg is not None
        client_ctor = rest_client_factory or GeminiRestClient
        shared_rest_client = client_ctor(
            api_key_env=gem_cfg.api_key_env,
            thinking_budget=gem_cfg.thinking_budget,
            thinking_level=gem_cfg.thinking_level,
            min_request_interval_sec=float(
                batch_cfg.get("min_request_interval_sec", gem_cfg.min_request_interval_sec)
            ),
            max_requests=remaining_global_at_start,
            stop_on_rate_limit=bool(batch_cfg.get("stop_on_rate_limit", True)),
        )
        shared_gemini_provider = GeminiAPIProvider(config=gem_cfg, client=shared_rest_client)

    artifact_locks = _collect_artifact_locks(
        batch_config_path=resolved_cfg_path,
        model_config_path=model_cfg_path,
        dataset_profile=str(batch_cfg["dataset_profile"]),
    )
    summary: dict[str, Any] = {
        "batch_id": str(batch_cfg["batch_id"]),
        "experiment_id": str(batch_cfg.get("experiment_id", "P06-E01")),
        "executed_at_utc": _now_utc_iso(),
        "provider": resolved_provider,
        "model_id": ledger["model_id"],
        "billing_tier": ledger["billing_tier"],
        "max_cost_usd": float(batch_cfg.get("max_cost_usd", 0.0)),
        "dataset_profile": str(batch_cfg["dataset_profile"]),
        "scenario": str(batch_cfg["scenario"]),
        "seed": int(batch_cfg["seed"]),
        "min_chunks_per_topic": int(batch_cfg["min_chunks_per_topic"]),
        "max_chunk_duration_sec": float(batch_cfg["max_chunk_duration_sec"]),
        "max_requests_per_run": per_run_cap,
        "global_max_requests": global_cap,
        "artifact_locks": artifact_locks,
        "runs": {},
        "total_requests_attempted_in_session": 0,
        "cumulative_global_requests": int(ledger["total_requests"]),
        "rate_limited": False,
        "status": "RUNNING",
        "comparison_compatible": None,
        "comparison_paths": {},
        "human_eval_files": [],
    }

    completed_run_dirs: list[Path] = []
    attempted_in_session = 0
    aborted_reason: Optional[str] = None

    try:
        for run_spec in batch_cfg["runs"]:
            label = str(run_spec["label"]).strip()
            method = ExperimentMethod(str(run_spec["method"]).strip())
            history_window = run_spec.get("history_window")
            remaining_now = remaining_global_at_start - attempted_in_session
            if remaining_now <= 0:
                aborted_reason = "GLOBAL_BUDGET_EXHAUSTED"
                break

            run_llm_cap = min(per_run_cap, remaining_now)
            cfg = load_experiment_run_config(
                scenario=str(batch_cfg["scenario"]),
                dataset_profile=str(batch_cfg["dataset_profile"]),
                method=method,
                provider=resolved_provider,
                model_config_path=model_cfg_path,
                history_window=history_window,
                min_chunks_per_topic=int(batch_cfg["min_chunks_per_topic"]),
                seed=int(batch_cfg["seed"]),
                max_chunk_duration_sec=float(batch_cfg["max_chunk_duration_sec"]),
                max_turns=int(batch_cfg.get("max_turns", 40)),
                max_llm_calls=run_llm_cap,
                max_estimated_cost_usd=None,
                output_dir=output_dir,
                allow_live_provider=allow_live_provider,
            )

            prev_client_calls = (
                int(shared_rest_client.requests_attempted)
                if shared_rest_client is not None
                else 0
            )
            run_res = run_experiment(cfg, custom_llm_provider=shared_gemini_provider)
            completed_run_dirs.append(run_res.run_dir)

            if shared_rest_client is not None:
                run_attempted = int(shared_rest_client.requests_attempted) - prev_client_calls
                rate_limited_now = bool(shared_rest_client.rate_limited)
            else:
                run_attempted = len(run_res.evidence.provider_calls)
                rate_limited_now = False

            attempted_in_session += run_attempted
            cumulative_total = int(ledger["total_requests"]) + run_attempted
            ledger["total_requests"] = cumulative_total
            ledger["rate_limited"] = bool(ledger["rate_limited"]) or rate_limited_now
            run_entry = {
                "run_id": run_res.run_id,
                "run_dir": str(run_res.run_dir),
                "method": method.value,
                "history_window": history_window,
                "termination_reason": run_res.termination_reason.value,
                "transcript_turns": len(run_res.evidence.transcript),
                "requests_attempted": run_attempted,
                "run_cap": run_llm_cap,
                "rate_limited": rate_limited_now,
                "prompt_versions": dict(run_res.manifest.get("prompt_versions") or {}),
                "prompt_hashes": dict(run_res.manifest.get("prompt_hashes") or {}),
                "token_accounting": _summarize_partial_token_usage(run_res.run_dir),
                "structural_hard_gates_status": (
                    run_res.report.structural_hard_gates_status.value if run_res.report else None
                ),
                "overall_gate_status": (
                    run_res.report.overall_gate_status.value if run_res.report else None
                ),
            }
            summary["runs"][label] = run_entry
            ledger["runs"][label] = {
                "run_id": run_res.run_id,
                "requests_attempted": run_attempted,
                "termination_reason": run_res.termination_reason.value,
                "at_utc": _now_utc_iso(),
            }
            ledger["events"].append(
                {
                    "label": label,
                    "run_id": run_res.run_id,
                    "requests_attempted": run_attempted,
                    "cumulative_total_requests": cumulative_total,
                    "rate_limited": rate_limited_now,
                    "at_utc": _now_utc_iso(),
                }
            )
            _save_json(ledger_path, ledger)

            if rate_limited_now:
                aborted_reason = "HTTP_429_RATE_LIMITED"
                break
            if run_res.termination_reason == RunTerminationReason.FATAL_ERROR:
                aborted_reason = "RUN_FATAL_ERROR"
                break

        if len(completed_run_dirs) >= 2:
            comp_report = compare_runs(completed_run_dirs)
            json_p = export_comparison_json(comp_report, output_dir / "comparison.json")
            csv_p = export_comparison_csv(comp_report, output_dir / "comparison.csv")
            md_p = export_comparison_markdown(comp_report, output_dir / "comparison.md")
            he_paths = export_blind_human_eval_sheets(
                completed_run_dirs,
                output_dir / "human_eval",
                seed=int(batch_cfg["seed"]),
            )
            summary["comparison_compatible"] = comp_report.compatible
            summary["comparison_paths"] = {
                "json": str(json_p),
                "csv": str(csv_p),
                "md": str(md_p),
            }
            summary["human_eval_files"] = [str(p) for p in he_paths]

        all_expected_done = len(summary["runs"]) == len(batch_cfg["runs"]) and aborted_reason is None
        final_status = "COMPLETED" if all_expected_done else "PARTIAL"
        if aborted_reason is not None:
            summary["aborted_reason"] = aborted_reason
        summary["status"] = final_status
        ledger["status"] = final_status
        return summary
    finally:
        summary["total_requests_attempted_in_session"] = attempted_in_session
        summary["cumulative_global_requests"] = int(ledger["total_requests"])
        summary["rate_limited"] = bool(ledger["rate_limited"])
        if summary["status"] == "RUNNING":
            summary["status"] = "PARTIAL"
            ledger["status"] = "PARTIAL"
        _save_json(ledger_path, ledger)
        _save_json(output_dir / "batch_summary.json", summary)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Điểm vào CLI điều phối batch Formal Benchmark với sổ cái toàn cục."""
    parser = argparse.ArgumentParser(
        description="HOSTRA AI P06-E01-T09 Formal Benchmark Global-Ledger Runner."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_BATCH_CONFIG_PATH,
        help="Đường dẫn YAML cấu hình batch Formal Benchmark.",
    )
    parser.add_argument(
        "--provider",
        choices=["gemini", "mock"],
        default=None,
        help="Tùy chọn ghi đè provider (`mock` cho kiểm thử ngoại tuyến).",
    )
    parser.add_argument(
        "--allow-live-provider",
        action="store_true",
        help="Cờ xác nhận cho phép gọi Gemini API thật (bắt buộc khi provider=gemini).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Thư mục lưu sổ cái, runs, comparison và human_eval.",
    )
    args = parser.parse_args(argv)

    summary = execute_formal_batch(
        args.config,
        provider_override=args.provider,
        allow_live_provider=args.allow_live_provider,
        output_dir_override=args.output_dir,
    )
    return 0 if summary.get("status") == "COMPLETED" and not summary.get("rate_limited") else 1


if __name__ == "__main__":
    raise SystemExit(main())
