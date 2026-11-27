"""Điều phối quét thực nghiệm đa cấu hình cho P06-E01 (`sweep.py`).

1. File này giải quyết vấn đề gì?
   Chạy tuần tự có kiểm soát toàn bộ tổ hợp kịch bản (`10m`/`30m`), phương pháp đối chứng
   (`script_first_deterministic`, `script_first_upfront_llm`, `langgraph_structured_story`)
   và cửa sổ bộ nhớ `W in {5, 10, 20}` (chỉ cho LangGraph), sau đó đối chiếu và xuất báo cáo.
2. Trách nhiệm chính của module là gì?
   Định nghĩa `SweepResult` và `run_e01_sweep()`, bảo đảm không quét `W` trên baseline
   script-first, giữ nguyên Offline Guard, gọi `compare_runs()` và xuất `comparison.json`,
   `comparison.csv`, `comparison.md` (cùng phiếu chấm mù tùy chọn).
3. Module này liên kết với các thành phần nào?
   Gọi `load_experiment_run_config()` (`p06.runner.config`), `run_experiment()` (`p06.runner.session_runner`),
   và gọi lười `compare_runs` / `export_human_eval_sheets` từ `p06.evaluation`.
4. Input và output chính là gì?
   Input là danh sách `scenarios`, `methods`, `history_windows`, `provider`, `seed`, `output_dir`;
   Output là `SweepResult` kèm đường dẫn các tệp báo cáo đối chiếu đã ghi xuống đĩa.
5. Có những constraints hoặc invariants quan trọng nào?
   - `script_first_deterministic` và `script_first_upfront_llm` chỉ chạy đúng 1 lần mỗi kịch bản
     với `history_window=None` (cấm quét `W` trên script-first).
   - `langgraph_structured_story` chạy đúng 1 lần cho mỗi giá trị trong `history_windows`.
   - Áp dụng Offline Guard nghiêm ngặt trước khi khởi chạy bất kỳ lượt nào.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Optional

from pydantic import BaseModel, ConfigDict, Field

from p06.evaluation.models import (
    ComparisonReport,
    ComparisonRow,
    EvaluationReport,
    RunEvidence,
)
from p06.providers.base import ProviderConfigError
from p06.runner.config import (
    DEFAULT_DATASET_PROFILE,
    DEFAULT_RUNS_OUTPUT_DIR,
    LIVE_PROVIDERS,
    ExperimentMethod,
    load_experiment_run_config,
)
from p06.runner.session_runner import ExperimentRunnerResult, run_experiment
from p06.schemas.story import NonBlankStr

HISTORY_WINDOW_SWEEP: Final[tuple[int, ...]] = (5, 10, 20)
DEFAULT_E01_SCENARIOS: Final[tuple[str, ...]] = (
    "product_education_10m",
    "brand_storytelling_10m",
    "sales_presentation_30m",
)
DEFAULT_E01_EXT_V1_SCENARIOS: Final[tuple[str, ...]] = (
    "product_education_10m_ext",
    "brand_storytelling_10m_ext",
    "sales_presentation_30m_ext",
)
DEFAULT_E01_FORMAL_V1_SCENARIOS: Final[tuple[str, ...]] = (
    "window_stress_12lag_3sku",
)
DEFAULT_E01_METHODS: Final[tuple[ExperimentMethod, ...]] = (
    ExperimentMethod.SCRIPT_FIRST_DETERMINISTIC,
    ExperimentMethod.SCRIPT_FIRST_UPFRONT_LLM,
    ExperimentMethod.LANGGRAPH,
)


class SweepResult(BaseModel):
    """Kết quả tổng hợp của một lần chạy quét thực nghiệm P06-E01."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    sweep_id: NonBlankStr
    output_dir: Path
    run_results: tuple[ExperimentRunnerResult, ...]
    comparison_report: Optional[ComparisonReport] = None
    comparison_json_path: Optional[Path] = None
    comparison_csv_path: Optional[Path] = None
    comparison_md_path: Optional[Path] = None
    per_scenario_comparison_paths: dict[str, dict[str, Path]] = Field(default_factory=dict)
    human_eval_dir: Optional[Path] = None


def _resolve_default_comparator() -> Optional[Callable[[Sequence[Path]], ComparisonReport]]:
    """Nạp lười `p06.evaluation.comparison.compare_runs` nếu đã sẵn sàng."""
    try:
        from p06.evaluation.comparison import compare_runs  # type: ignore[import-not-found]

        return compare_runs
    except ModuleNotFoundError:
        return None


def _resolve_default_human_eval_exporter() -> Optional[Callable[[Sequence[Path], Path], Any]]:
    """Nạp lười `p06.evaluation.human_eval.export_blind_human_eval_sheets` nếu đã sẵn sàng."""
    try:
        from p06.evaluation.human_eval import (
            export_blind_human_eval_sheets,
        )

        return export_blind_human_eval_sheets
    except ModuleNotFoundError:
        return None


def _build_fallback_comparison_report(results: Sequence[ExperimentRunnerResult]) -> ComparisonReport:
    """Dựng `ComparisonReport` tối thiểu từ `ExperimentRunnerResult` khi chưa có `comparison.py`."""
    rows: list[ComparisonRow] = []
    tiers: list[str] = []
    for res in results:
        manifest = res.manifest
        tier = str(manifest.get("provider_tier", "unit_test"))
        if tier not in tiers:
            tiers.append(tier)
        rep = res.report
        rows.append(
            ComparisonRow(
                run_id=res.run_id,
                method=str(manifest.get("method", "unknown")),
                scenario=str(manifest.get("scenario", "unknown")),
                provider_tier=tier,
                provider_name=str(manifest.get("provider_name", "mock")),
                model_id=str(manifest.get("model_id", "unknown")),
                history_window=manifest.get("history_window"),
                termination_reason=res.termination_reason.value,
                hard_gates_passed=rep.hard_gates_passed if rep is not None else True,
            )
        )
    return ComparisonReport(
        compatible=(len(set(tiers)) <= 1),
        grouped_tiers=tuple(tiers),
        rows=tuple(rows),
        notes=("Generated by runner sweep fallback summary.",),
    )


def _write_comparison_artifacts(
    report: ComparisonReport,
    output_dir: Path,
    *,
    filename_prefix: str = "comparison",
) -> tuple[Path, Path, Path]:
    """Ghi `{filename_prefix}.json`, `.csv` và `.md` vào `output_dir`."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{filename_prefix}.json"
    csv_path = output_dir / f"{filename_prefix}.csv"
    md_path = output_dir / f"{filename_prefix}.md"

    try:
        from p06.evaluation.comparison import (
            export_comparison_csv,
            export_comparison_json,
            export_comparison_markdown,
        )

        export_comparison_json(report, json_path)
        export_comparison_csv(report, csv_path)
        export_comparison_markdown(report, md_path)
        return json_path, csv_path, md_path
    except ModuleNotFoundError:
        pass

    json_path.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    fieldnames = list(ComparisonRow.model_fields.keys())
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report.rows:
            row_dict = row.model_dump(mode="json")
            row_dict["missing_or_not_evaluated"] = ";".join(row.missing_or_not_evaluated)
            writer.writerow(row_dict)

    md_lines = [
        "# P06-E01 Comparison Report",
        "",
        f"- Compatible: `{report.compatible}`",
        f"- Provider Tiers: `{', '.join(report.grouped_tiers)}`",
        "",
        "| run_id | method | scenario | W | termination | hard_gates | coverage | duration_fulfillment |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report.rows:
        w_val = str(row.history_window) if row.history_window is not None else "N/A"
        cov = f"{row.mandatory_topic_coverage:.3f}" if row.mandatory_topic_coverage is not None else "N/A"
        dur = f"{row.duration_fulfillment:.3f}" if row.duration_fulfillment is not None else "N/A"
        md_lines.append(
            f"| {row.run_id} | {row.method} | {row.scenario} | {w_val} | "
            f"{row.termination_reason} | {row.hard_gates_passed} | {cov} | {dur} |"
        )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return json_path, csv_path, md_path


def run_e01_sweep(
    *,
    scenarios: Optional[Sequence[str]] = None,
    methods: Sequence[ExperimentMethod | str] = DEFAULT_E01_METHODS,
    history_windows: Sequence[int] = HISTORY_WINDOW_SWEEP,
    dataset_profile: str = DEFAULT_DATASET_PROFILE,
    provider: str = "mock",
    model_config_path: Optional[Path] = None,
    min_chunks_per_topic: Optional[int] = None,
    seed: int = 42,
    max_turns: int = 500,
    max_llm_calls: Optional[int] = None,
    max_estimated_cost_usd: Optional[float] = None,
    output_dir: Optional[Path] = None,
    allow_live_provider: bool = False,
    export_human_eval: bool = False,
    evaluator: Optional[Callable[[RunEvidence], EvaluationReport]] = None,
    comparator: Optional[Callable[[Sequence[Path]], ComparisonReport]] = None,
    human_eval_exporter: Optional[Callable[[Sequence[Path], Path], Any]] = None,
) -> SweepResult:
    """Chạy toàn bộ tổ hợp đối chứng P06-E01 và xuất báo cáo `comparison.{json,csv,md}`.

    Args:
        scenarios: Danh sách kịch bản E01 cần chạy.
        methods: Danh sách phương pháp cần đối chiếu.
        history_windows: Danh sách kích thước cửa sổ `W` áp dụng RIÊNG cho `LANGGRAPH`.
        provider: Nhà cung cấp mô hình (`mock`, `ollama`, `gemini`).
        model_config_path: Đường dẫn YAML model tùy chọn.
        seed: Hạt giống cố định dùng chung cho toàn bộ sweep.
        max_turns: Giới hạn số lượt tối đa mỗi phiên chạy.
        output_dir: Thư mục lưu các thư mục run và báo cáo so sánh.
        allow_live_provider: Cờ cho phép gọi provider trực tuyến (`ollama`/`gemini`).
        export_human_eval: Nếu `True`, xuất thêm bộ phiếu chấm mù rubric.
        evaluator: Hàm đánh giá tiêm từ ngoài (tùy chọn).
        comparator: Hàm so sánh tiêm từ ngoài (tùy chọn).
        human_eval_exporter: Hàm xuất phiếu chấm mù tiêm từ ngoài (tùy chọn).

    Returns:
        SweepResult: Tập kết quả các lượt chạy và đường dẫn báo cáo so sánh.

    Raises:
        ProviderConfigError: Nếu vi phạm Offline Guard (`ollama`/`gemini` khi `allow_live_provider=False`).
        ValueError: Nếu `scenarios` hoặc `methods` rỗng hoặc `history_windows` rỗng khi chạy LangGraph.
    """
    normalized_provider = provider.strip().lower()
    if normalized_provider in LIVE_PROVIDERS and not allow_live_provider:
        raise ProviderConfigError(
            f"Offline Guard: từ chối chạy sweep với provider '{normalized_provider}' "
            f"vì allow_live_provider=False."
        )
    resolved_scenarios: tuple[str, ...] = (
        tuple(scenarios)
        if scenarios is not None
        else (
            DEFAULT_E01_EXT_V1_SCENARIOS
            if dataset_profile.strip() == "e01_ext_v1"
            else (
                DEFAULT_E01_FORMAL_V1_SCENARIOS
                if dataset_profile.strip() == "e01_formal_v1"
                else DEFAULT_E01_SCENARIOS
            )
        )
    )
    if not resolved_scenarios:
        raise ValueError("Danh sách scenarios trong run_e01_sweep không được rỗng.")
    if not methods:
        raise ValueError("Danh sách methods trong run_e01_sweep không được rỗng.")

    resolved_methods = [
        m if isinstance(m, ExperimentMethod) else ExperimentMethod(str(m).strip())
        for m in methods
    ]
    if ExperimentMethod.LANGGRAPH in resolved_methods and not history_windows:
        raise ValueError("history_windows không được rỗng khi chạy langgraph_structured_story.")

    resolved_output_dir = (output_dir or DEFAULT_RUNS_OUTPUT_DIR).resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    sweep_id = f"sweep_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    run_results: list[ExperimentRunnerResult] = []
    for scenario in resolved_scenarios:
        for method in resolved_methods:
            if method == ExperimentMethod.LANGGRAPH:
                windows_to_run: tuple[Optional[int], ...] = tuple(history_windows)
            else:
                # Script-First baseline tuyệt đối không quét W vì không sử dụng short_term_played_history.
                windows_to_run = (None,)

            for window_val in windows_to_run:
                run_cfg = load_experiment_run_config(
                    scenario=scenario,
                    method=method,
                    dataset_profile=dataset_profile,
                    provider=normalized_provider,
                    model_config_path=model_config_path,
                    history_window=window_val,
                    min_chunks_per_topic=min_chunks_per_topic,
                    seed=seed,
                    max_turns=max_turns,
                    max_llm_calls=max_llm_calls,
                    max_estimated_cost_usd=max_estimated_cost_usd,
                    output_dir=resolved_output_dir,
                    allow_live_provider=allow_live_provider,
                )
                result = run_experiment(run_cfg, evaluator=evaluator)
                run_results.append(result)

    run_dirs = [res.run_dir for res in run_results]
    resolved_comparator = comparator if comparator is not None else _resolve_default_comparator()
    if resolved_comparator is not None:
        comparison_report = resolved_comparator(run_dirs)
    else:
        comparison_report = _build_fallback_comparison_report(run_results)

    json_path, csv_path, md_path = _write_comparison_artifacts(
        comparison_report,
        resolved_output_dir,
    )

    per_scenario_paths: dict[str, dict[str, Path]] = {}
    if len(resolved_scenarios) > 1:
        # Khi chạy nhiều kịch bản, xuất thêm báo cáo đối chiếu riêng từng kịch bản để bảo đảm compatible=True nội bộ.
        for sc_name in resolved_scenarios:
            sc_results = [r for r in run_results if r.manifest.get("scenario") == sc_name]
            if not sc_results:
                continue
            sc_dirs = [r.run_dir for r in sc_results]
            sc_report = (
                resolved_comparator(sc_dirs)
                if resolved_comparator is not None
                else _build_fallback_comparison_report(sc_results)
            )
            sc_json, sc_csv, sc_md = _write_comparison_artifacts(
                sc_report,
                resolved_output_dir,
                filename_prefix=f"comparison_{sc_name}",
            )
            per_scenario_paths[sc_name] = {
                "json": sc_json,
                "csv": sc_csv,
                "md": sc_md,
            }

    human_eval_dir: Optional[Path] = None
    if export_human_eval:
        human_eval_dir = resolved_output_dir / "human_eval"
        exporter = (
            human_eval_exporter
            if human_eval_exporter is not None
            else _resolve_default_human_eval_exporter()
        )
        if exporter is None:
            raise RuntimeError(
                "Không tìm thấy module p06.evaluation.human_eval để xuất phiếu chấm mù."
            )
        exporter(run_dirs, human_eval_dir)

    return SweepResult(
        sweep_id=sweep_id,
        output_dir=resolved_output_dir,
        run_results=tuple(run_results),
        comparison_report=comparison_report,
        comparison_json_path=json_path,
        comparison_csv_path=csv_path,
        comparison_md_path=md_path,
        per_scenario_comparison_paths=per_scenario_paths,
        human_eval_dir=human_eval_dir,
    )
