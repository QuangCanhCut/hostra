"""Pipeline đối chiếu đa cấu hình và kiểm tra cô lập tầng cho P06 (`p06.evaluation.comparison`).

1. File này giải quyết vấn đề gì?
   So sánh công bằng giữa các phương pháp (`script_first` vs `langgraph_structured_story`)
   và kích thước cửa sổ (`W ∈ {5, 10, 20}`), đồng thời phát hiện và gắn cờ lỗi nghiêm trọng nếu
   người dùng cố tình gộp số liệu giữa các tầng khác nhau (`mock` vs `ollama` vs `gemini`) hoặc
   lệch `scenario`, `dataset_sha256`, `story_plan`, `contract_version`.
2. Trách nhiệm chính của module là gì?
   Cung cấp `compare_runs()` cùng 3 hàm xuất báo cáo `export_comparison_json()`,
   `export_comparison_csv()`, và `export_comparison_markdown()`.
3. Module này liên kết với các thành phần nào?
   Sử dụng `load_run_evidence()` và `evaluate_run()` (`p06.evaluation.evaluator`),
   xuất `ComparisonReport`, `ComparisonRow`, `CompatibilityIssue` (`p06.evaluation.models`).
4. Input và output chính là gì?
   Input là danh sách đường dẫn thư mục run; Output là `ComparisonReport` và các tệp JSON/CSV/Markdown.
5. Có những constraints hoặc invariants quan trọng nào?
   - Nghiêm cấm gộp số liệu giữa `unit_test` (`mock`), `local_smoke_test` (`ollama`), và
     `formal_experiment` (`gemini`): vi phạm sẽ đặt `compatible=False` kèm mã `CROSS_TIER_POOLING_PROHIBITED`.
   - Mọi metric `NOT_EVALUATED` / `NOT_APPLICABLE` / `INVALID` giữ nguyên `None` (hiển thị `N/A` trong
     Markdown/CSV), tuyệt đối không thay bằng `0`.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional

from p06.evaluation.evaluator import evaluate_run, load_run_evidence
from p06.evaluation.models import (
    ComparisonReport,
    ComparisonRow,
    CompatibilityIssue,
    EvaluationReport,
    MetricResult,
    MetricStatus,
    RunEvidence,
)

_ISOLATED_PROVIDERS = frozenset({"mock", "ollama", "gemini"})


def _computed_float(group: dict[str, MetricResult], name: str) -> Optional[float]:
    """Lấy giá trị `float` nếu metric có trạng thái `COMPUTED`, ngược lại trả `None`."""
    res = group.get(name)
    if res is None or res.status != MetricStatus.COMPUTED or res.value is None:
        return None
    return float(res.value)


def _computed_int(group: dict[str, MetricResult], name: str) -> Optional[int]:
    """Lấy giá trị `int` nếu metric có trạng thái `COMPUTED`, ngược lại trả `None`."""
    res = group.get(name)
    if res is None or res.status != MetricStatus.COMPUTED or res.value is None:
        return None
    return int(res.value)


def _collect_missing_metric_names(report: EvaluationReport) -> tuple[str, ...]:
    """Thu thập tên mọi metric không ở trạng thái `COMPUTED` (trừ nhóm placeholder chấm tay)."""
    missing: list[str] = []
    for group in (
        report.coverage,
        report.repetition,
        report.safety,
        report.reliability,
        report.performance,
    ):
        for name, res in group.items():
            if res.status != MetricStatus.COMPUTED:
                missing.append(name)
    return tuple(sorted(missing))


def compare_runs(run_dirs: Sequence[Path]) -> ComparisonReport:
    """Nạp, đánh giá và kiểm tra tính tương thích thực nghiệm trên nhiều thư mục lần chạy.

    Args:
        run_dirs: Danh sách các thư mục run cần đối chiếu.

    Returns:
        ComparisonReport: Báo cáo đối chiếu kèm danh sách lỗi tương thích nếu có.

    Raises:
        ValueError: Nếu `run_dirs` rỗng hoặc có thư mục run chứa manifest/schema không hợp lệ.
    """
    if not run_dirs:
        raise ValueError("run_dirs không được rỗng khi gọi compare_runs().")

    evidences: list[RunEvidence] = []
    reports: list[EvaluationReport] = []
    for run_dir in run_dirs:
        ev = load_run_evidence(Path(run_dir))
        rep = evaluate_run(ev)
        evidences.append(ev)
        reports.append(rep)

    run_ids = tuple(rep.run_id for rep in reports)
    issues: list[CompatibilityIssue] = []
    compatible = True

    distinct_tiers = sorted({rep.provider_tier for rep in reports})
    distinct_providers = sorted({rep.provider_name.strip().lower() for rep in reports})
    isolated_mix = len(set(distinct_providers) & _ISOLATED_PROVIDERS) > 1
    if len(distinct_tiers) > 1 or isolated_mix:
        compatible = False
        issues.append(
            CompatibilityIssue(
                severity="ERROR",
                code="CROSS_TIER_POOLING_PROHIBITED",
                message=(
                    f"Cấm gộp kết quả giữa các tầng/provider khác nhau: "
                    f"tiers={distinct_tiers}, providers={distinct_providers}."
                ),
                run_ids=run_ids,
            )
        )

    distinct_scenarios = sorted({rep.scenario for rep in reports})
    if len(distinct_scenarios) > 1:
        compatible = False
        issues.append(
            CompatibilityIssue(
                severity="ERROR",
                code="SCENARIO_MISMATCH",
                message=f"Các lần chạy không cùng kịch bản (scenario): {distinct_scenarios}.",
                run_ids=run_ids,
            )
        )

    dataset_hashes = [ev.manifest.get("dataset_sha256") for ev in evidences]
    if any(h is not None for h in dataset_hashes) and len(set(dataset_hashes)) > 1:
        compatible = False
        issues.append(
            CompatibilityIssue(
                severity="ERROR",
                code="DATASET_SHA256_MISMATCH",
                message=f"dataset_sha256 không đồng nhất giữa các lần chạy: {dataset_hashes}.",
                run_ids=run_ids,
            )
        )

    plan_sigs = sorted(
        {(ev.story_plan.plan_id, ev.story_plan.plan_revision) for ev in evidences}
    )
    if len(plan_sigs) > 1:
        compatible = False
        issues.append(
            CompatibilityIssue(
                severity="ERROR",
                code="STORY_PLAN_MISMATCH",
                message=f"StoryPlan (plan_id, plan_revision) không khớp: {plan_sigs}.",
                run_ids=run_ids,
            )
        )

    contract_versions = sorted(
        {
            str(ev.manifest.get("contract_version") or ev.story_plan.contract_version)
            for ev in evidences
        }
    )
    if len(contract_versions) > 1:
        compatible = False
        issues.append(
            CompatibilityIssue(
                severity="ERROR",
                code="CONTRACT_VERSION_MISMATCH",
                message=f"contract_version không đồng nhất: {contract_versions}.",
                run_ids=run_ids,
            )
        )

    target_durations = sorted({float(ev.target_duration_sec) for ev in evidences})
    if len(target_durations) > 1:
        issues.append(
            CompatibilityIssue(
                severity="WARNING",
                code="TARGET_DURATION_MISMATCH",
                message=f"target_duration_sec khác nhau giữa các lần chạy: {target_durations}.",
                run_ids=run_ids,
            )
        )

    rows: list[ComparisonRow] = []
    for rep in reports:
        rows.append(
            ComparisonRow(
                run_id=rep.run_id,
                method=rep.method,
                scenario=rep.scenario,
                provider_tier=rep.provider_tier,
                provider_name=rep.provider_name,
                model_id=rep.model_id,
                history_window=rep.history_window,
                termination_reason=rep.termination_reason,
                hard_gates_passed=rep.hard_gates_passed,
                mandatory_topic_coverage=_computed_float(
                    rep.coverage, "mandatory_topic_coverage"
                ),
                duration_fulfillment=_computed_float(
                    rep.coverage, "duration_fulfillment"
                ),
                exact_chunk_replay_count=_computed_int(
                    rep.repetition, "exact_chunk_replay_count"
                ),
                exact_normalized_text_replay_count=_computed_int(
                    rep.repetition, "exact_normalized_text_replay_count"
                ),
                outside_window_exact_text_replay_count=_computed_int(
                    rep.repetition, "outside_window_exact_text_replay_count"
                ),
                max_prior_ngram3_jaccard_mean=_computed_float(
                    rep.repetition, "max_prior_ngram3_jaccard_mean"
                ),
                lexical_repetition_rate=_computed_float(
                    rep.repetition, "lexical_repetition_rate"
                ),
                p05_rejection_rate=_computed_float(rep.safety, "p05_rejection_rate"),
                rewrite_rate=_computed_float(rep.reliability, "rewrite_rate"),
                fallback_rate=_computed_float(rep.reliability, "fallback_rate"),
                safe_abort_rate=_computed_float(rep.reliability, "safe_abort_rate"),
                provider_latency_p50_ms=_computed_float(
                    rep.performance, "provider_latency_p50_ms"
                ),
                provider_latency_p95_ms=_computed_float(
                    rep.performance, "provider_latency_p95_ms"
                ),
                input_tokens=_computed_int(rep.performance, "input_tokens"),
                output_tokens=_computed_int(rep.performance, "output_tokens"),
                wasted_tokens=_computed_int(rep.performance, "wasted_tokens"),
                total_model_calls=_computed_int(rep.performance, "total_model_calls"),
                estimated_llm_cost_usd=_computed_float(
                    rep.performance, "estimated_llm_cost_usd"
                ),
                missing_or_not_evaluated=_collect_missing_metric_names(rep),
            )
        )

    notes: list[str] = []
    if any(t == "unit_test" for t in distinct_tiers) or "mock" in distinct_providers:
        notes.append(
            "Mock (unit_test) runs verify state/contract logic only and are NOT evidence of Vietnamese storytelling quality."
        )
    if not compatible:
        notes.append(
            "Compatibility checks FAILED: do not interpret pooled aggregates across incompatible tiers or experimental conditions."
        )

    return ComparisonReport(
        compatible=compatible,
        compatibility_issues=tuple(issues),
        grouped_tiers=tuple(distinct_tiers),
        rows=tuple(rows),
        notes=tuple(notes),
    )


def export_comparison_json(report: ComparisonReport, output_path: Path) -> Path:
    """Xuất `ComparisonReport` ra tệp JSON chuẩn hóa."""
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return dest


def export_comparison_csv(report: ComparisonReport, output_path: Path) -> Path:
    """Xuất bảng `ComparisonRow` ra tệp CSV UTF-8 (giữ rỗng cho giá trị `None`)."""
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(ComparisonRow.model_fields.keys())
    with dest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report.rows:
            raw: dict[str, Any] = row.model_dump(mode="json")
            raw["missing_or_not_evaluated"] = ";".join(row.missing_or_not_evaluated)
            writer.writerow(raw)
    return dest


def _fmt_cell(value: Any, *, digits: int = 4) -> str:
    """Định dạng ô bảng Markdown, hiển thị `N/A` khi thiếu số liệu."""
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def export_comparison_markdown(report: ComparisonReport, output_path: Path) -> Path:
    """Xuất `ComparisonReport` ra báo cáo Markdown kèm cảnh báo tương thích."""
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        "# P06 Experiment Comparison Report",
        "",
        f"- **Compatible:** `{report.compatible}`",
        f"- **Grouped Tiers:** `{list(report.grouped_tiers)}`",
        "",
    ]
    if report.compatibility_issues:
        lines.append("## Compatibility Issues")
        lines.append("")
        for issue in report.compatibility_issues:
            lines.append(
                f"- **[{issue.severity}] `{issue.code}`:** {issue.message} "
                f"(runs: {', '.join(issue.run_ids)})"
            )
        lines.append("")

    headers = [
        "run_id",
        "method",
        "tier",
        "model_id",
        "W",
        "hard_gates",
        "topic_cov",
        "dur_fulfill",
        "chunk_replay",
        "ngram3_mean",
        "lex_rep_rate",
        "p05_rej_rate",
        "rewrite_rate",
        "p50_ms",
        "input_tok",
        "output_tok",
        "wasted_tok",
        "est_cost_usd",
    ]
    lines.append("## Run Summary")
    lines.append("")
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in report.rows:
        cells = [
            row.run_id,
            row.method,
            row.provider_tier,
            row.model_id,
            _fmt_cell(row.history_window, digits=0),
            _fmt_cell(row.hard_gates_passed),
            _fmt_cell(row.mandatory_topic_coverage),
            _fmt_cell(row.duration_fulfillment),
            _fmt_cell(row.exact_chunk_replay_count, digits=0),
            _fmt_cell(row.max_prior_ngram3_jaccard_mean),
            _fmt_cell(row.lexical_repetition_rate),
            _fmt_cell(row.p05_rejection_rate),
            _fmt_cell(row.rewrite_rate),
            _fmt_cell(row.provider_latency_p50_ms, digits=2),
            _fmt_cell(row.input_tokens, digits=0),
            _fmt_cell(row.output_tokens, digits=0),
            _fmt_cell(row.wasted_tokens, digits=0),
            _fmt_cell(row.estimated_llm_cost_usd, digits=6),
        ]
        lines.append("| " + " | ".join(cells) + " |")

    if report.notes:
        lines.extend(["", "## Notes", ""])
        for note in report.notes:
            lines.append(f"- {note}")

    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest
