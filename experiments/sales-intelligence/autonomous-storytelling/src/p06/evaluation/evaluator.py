"""Bộ nạp bằng chứng và đánh giá tổng hợp cho một lần chạy thí nghiệm P06 (`p06.evaluation.evaluator`).

1. File này giải quyết vấn đề gì?
   Chuyển đổi thư mục log thô (`runs/<exp_id>/<run_id>/`) hoặc `RunEvidence` trong bộ nhớ
   thành báo cáo đánh giá chuẩn hóa `EvaluationReport` gồm 5 trục tự động, 6 placeholder chấm người thật,
   kiểm tra Hard Gates không bù trừ và bản đồ truy vết `metric_provenance`.
2. Trách nhiệm chính của module là gì?
   Cung cấp `load_run_evidence()`, `evaluate_run()` và `evaluate_run_directory()`.
3. Module này liên kết với các thành phần nào?
   Tổng hợp 5 module trong `p06.evaluation.metrics` và xuất DTO `RunEvidence`, `EvaluationReport`
   từ `p06.evaluation.models`.
4. Input và output chính là gì?
   Input là đường dẫn thư mục run hoặc `RunEvidence` (kèm `gold_labels` tùy chọn);
   Output là `RunEvidence` hoặc `EvaluationReport` bất biến.
5. Có những constraints hoặc invariants quan trọng nào?
   - `manifest.json` hoặc `story_plan.json` thiếu/sai định dạng phải ném `FileNotFoundError`/`ValueError`
     tường minh, tuyệt đối không nuốt lỗi.
   - 6 tiêu chí `human_eval_placeholders` luôn ở trạng thái `NOT_EVALUATED` (`value=None`).
   - Vi phạm bất kỳ Hard Gate nào (`exact_chunk_replay_count`, `duplicate_completed_chunk_replay_count`,
     `invalid_candidate_playback_count`, `retry_budget_violations`, hoặc `verifier_false_accept_count` khi có
     `gold_labels`) đều đặt `hard_gates_passed=False`.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional, TypeVar

from pydantic import BaseModel, ValidationError

from p06.evaluation.metrics import (
    compute_coverage_metrics,
    compute_performance_metrics,
    compute_reliability_metrics,
    compute_repetition_metrics,
    compute_safety_metrics,
)
from p06.evaluation.models import (
    ErrorRecord,
    EvaluationReport,
    GateStatus,
    GoldFactualLabel,
    GraphTraceRecord,
    MetricProvenance,
    MetricResult,
    MetricStatus,
    PlaybackEventRecord,
    ProviderCallRecord,
    RunEvidence,
    TranscriptEntry,
)
from p06.schemas.story import StoryPlan

_ModelT = TypeVar("_ModelT", bound=BaseModel)

_REQUIRED_MANIFEST_STR_FIELDS: tuple[str, ...] = (
    "run_id",
    "experiment_id",
    "method",
    "scenario",
    "provider_tier",
    "provider_name",
    "model_id",
)

_HUMAN_EVAL_CRITERIA: tuple[str, ...] = (
    "narrative_coherence",
    "naturalness",
    "persuasiveness",
    "context_relevance",
    "transition_quality",
    "repetition_quality",
)


def _require_non_blank_manifest_str(manifest: dict[str, Any], key: str) -> str:
    """Trích xuất trường chuỗi bắt buộc từ `manifest` hoặc ném `ValueError` nếu thiếu/rỗng."""
    val = manifest.get(key)
    if not isinstance(val, str) or not val.strip():
        raise ValueError(f"Manifest thiếu hoặc rỗng trường bắt buộc '{key}'.")
    return val.strip()


def _load_jsonl_records(file_path: Path, model_cls: type[_ModelT]) -> tuple[_ModelT, ...]:
    """Đọc tệp JSONL thành tuple các mô hình Pydantic, báo lỗi rõ số dòng nếu hỏng định dạng."""
    if not file_path.exists():
        return ()
    if not file_path.is_file():
        raise ValueError(f"Đường dẫn '{file_path}' không phải tệp JSONL hợp lệ.")
    records: list[_ModelT] = []
    raw_lines = file_path.read_text(encoding="utf-8").splitlines()
    for line_no, raw_line in enumerate(raw_lines, start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            records.append(model_cls.model_validate_json(stripped))
        except (ValidationError, ValueError) as exc:
            raise ValueError(
                f"Lỗi phân tích JSONL tại '{file_path}' dòng {line_no}: {exc}"
            ) from exc
    return tuple(records)


def load_run_evidence(run_dir: Path) -> RunEvidence:
    """Nạp toàn bộ bằng chứng thô từ một thư mục lần chạy (`runs/<exp_id>/<run_id>/`).

    Args:
        run_dir: Đường dẫn thư mục chứa `manifest.json`, `story_plan.json` và các tệp `.jsonl`.

    Returns:
        RunEvidence: Tập hợp bằng chứng thô đã kiểm định schema.

    Raises:
        FileNotFoundError: Nếu `run_dir`, `manifest.json` hoặc `story_plan.json` không tồn tại.
        ValueError: Nếu `manifest.json`, `story_plan.json` hoặc các tệp JSONL sai định dạng/thiếu khóa.
    """
    resolved_dir = Path(run_dir)
    if not resolved_dir.exists() or not resolved_dir.is_dir():
        raise FileNotFoundError(f"Không tìm thấy thư mục lần chạy tại '{resolved_dir}'.")

    manifest_path = resolved_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Thiếu manifest.json tại '{manifest_path}'.")
    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"manifest.json không phải JSON hợp lệ tại '{manifest_path}': {exc}") from exc
    if not isinstance(manifest_data, dict):
        raise ValueError(f"manifest.json tại '{manifest_path}' phải là JSON object.")

    for req_key in _REQUIRED_MANIFEST_STR_FIELDS:
        _require_non_blank_manifest_str(manifest_data, req_key)

    story_plan_path = resolved_dir / "story_plan.json"
    if not story_plan_path.is_file():
        raise FileNotFoundError(f"Thiếu story_plan.json tại '{story_plan_path}'.")
    try:
        story_plan = StoryPlan.model_validate_json(story_plan_path.read_text(encoding="utf-8"))
    except (ValidationError, ValueError) as exc:
        raise ValueError(f"story_plan.json không hợp lệ tại '{story_plan_path}': {exc}") from exc

    transcript = _load_jsonl_records(resolved_dir / "transcript.jsonl", TranscriptEntry)
    playback_events = _load_jsonl_records(
        resolved_dir / "playback_events.jsonl", PlaybackEventRecord
    )
    graph_traces = _load_jsonl_records(resolved_dir / "graph_trace.jsonl", GraphTraceRecord)
    provider_calls = _load_jsonl_records(
        resolved_dir / "provider_calls.jsonl", ProviderCallRecord
    )
    errors = _load_jsonl_records(resolved_dir / "errors.jsonl", ErrorRecord)

    try:
        return RunEvidence(
            manifest=manifest_data,
            story_plan=story_plan,
            transcript=transcript,
            playback_events=playback_events,
            graph_traces=graph_traces,
            provider_calls=provider_calls,
            errors=errors,
            planning_latency_ms=manifest_data.get("planning_latency_ms", 0.0),
            upfront_script_generation_latency_ms=manifest_data.get(
                "upfront_script_generation_latency_ms", 0.0
            ),
            total_measured_processing_ms=manifest_data.get(
                "total_measured_processing_ms", 0.0
            ),
            simulated_elapsed_sec=manifest_data.get("simulated_elapsed_sec", 0.0),
            target_duration_sec=manifest_data.get("target_duration_sec", 600.0),
        )
    except ValidationError as exc:
        raise ValueError(f"Dữ liệu RunEvidence không hợp lệ từ '{resolved_dir}': {exc}") from exc


def _build_human_eval_placeholders() -> dict[str, MetricResult]:
    """Khởi tạo 6 chỉ số giữ chỗ `NOT_EVALUATED` theo `human_eval_rubric_v0.1.md`."""
    return {
        criterion: MetricResult(
            name=criterion,
            status=MetricStatus.NOT_EVALUATED,
            value=None,
            unit="score_1_to_5",
            data_source="human_eval_sheet",
            provenance=MetricProvenance.UNAVAILABLE,
            is_simulated=False,
            missing_reason="Requires blind human evaluation per human_eval_rubric_v0.1.md (T09).",
        )
        for criterion in _HUMAN_EVAL_CRITERIA
    }


def _check_zero_hard_gate(
    metrics: dict[str, MetricResult],
    metric_name: str,
    failures: list[str],
) -> None:
    """Kiểm tra một Hard Gate bắt buộc phải `COMPUTED` với `value == 0`."""
    res = metrics.get(metric_name)
    if res is None:
        failures.append(f"Hard gate '{metric_name}' missing from evaluation metrics.")
        return
    if res.status != MetricStatus.COMPUTED:
        failures.append(
            f"Hard gate '{metric_name}' was not computed (status={res.status.value})."
        )
        return
    if res.value != 0:
        failures.append(f"Hard gate '{metric_name}' violated: expected 0, got {res.value!r}.")


def evaluate_run(
    evidence: RunEvidence,
    *,
    gold_labels: Optional[Sequence[GoldFactualLabel]] = None,
) -> EvaluationReport:
    """Đánh giá đầy đủ một `RunEvidence` thành `EvaluationReport` bất biến.

    Args:
        evidence: Tập bằng chứng thô của một lần chạy.
        gold_labels: Nhãn chuẩn thực tế độc lập `GoldFactualLabel` (tùy chọn).

    Returns:
        EvaluationReport: Báo cáo tổng hợp 5 trục metric, trạng thái Hard Gates và provenance.

    Raises:
        ValueError: Nếu `manifest` thiếu trường định danh bắt buộc hoặc `history_window` sai kiểu.
    """
    manifest = evidence.manifest
    run_id = _require_non_blank_manifest_str(manifest, "run_id")
    experiment_id = _require_non_blank_manifest_str(manifest, "experiment_id")
    method = _require_non_blank_manifest_str(manifest, "method")
    scenario = _require_non_blank_manifest_str(manifest, "scenario")
    provider_tier = _require_non_blank_manifest_str(manifest, "provider_tier")
    provider_name = _require_non_blank_manifest_str(manifest, "provider_name")
    model_id = _require_non_blank_manifest_str(manifest, "model_id")

    raw_window = manifest.get("history_window")
    if raw_window is not None and (
        isinstance(raw_window, bool) or not isinstance(raw_window, int) or raw_window < 1
    ):
        raise ValueError(
            f"history_window trong manifest phải là None hoặc số nguyên dương, nhận được {raw_window!r}."
        )

    coverage = compute_coverage_metrics(evidence)
    repetition = compute_repetition_metrics(evidence)
    safety = compute_safety_metrics(evidence, gold_labels=gold_labels)
    reliability = compute_reliability_metrics(evidence)
    performance = compute_performance_metrics(evidence)
    human_eval_placeholders = _build_human_eval_placeholders()

    term_res = reliability["termination_reason"]
    termination_reason = (
        str(term_res.value)
        if term_res.status == MetricStatus.COMPUTED and term_res.value is not None
        else "UNSPECIFIED"
    )

    structural_failures: list[str] = []
    _check_zero_hard_gate(repetition, "exact_chunk_replay_count", structural_failures)
    _check_zero_hard_gate(safety, "duplicate_completed_chunk_replay_count", structural_failures)
    _check_zero_hard_gate(safety, "invalid_candidate_playback_count", structural_failures)
    _check_zero_hard_gate(reliability, "retry_budget_violations", structural_failures)

    factual_failures: list[str] = []
    not_evaluated_gates: list[str] = []
    structural_status = GateStatus.PASS if not structural_failures else GateStatus.FAIL
    if gold_labels:
        _check_zero_hard_gate(safety, "verifier_false_accept_count", factual_failures)
        factual_status = GateStatus.PASS if not factual_failures else GateStatus.FAIL
    else:
        factual_status = GateStatus.NOT_EVALUATED
        not_evaluated_gates.append("verifier_false_accept_count")

    hard_gate_failures = [*structural_failures, *factual_failures]
    if structural_status == GateStatus.FAIL or factual_status == GateStatus.FAIL:
        overall_gate_status = GateStatus.FAIL
    elif structural_status == GateStatus.PASS and factual_status == GateStatus.PASS:
        overall_gate_status = GateStatus.PASS
    else:
        # Không bao giờ gán PASS tổng thể khi cổng kiểm chứng thực tế độc lập chưa được chấm.
        overall_gate_status = GateStatus.NOT_EVALUATED

    all_groups = (
        coverage,
        repetition,
        safety,
        reliability,
        performance,
        human_eval_placeholders,
    )
    limitations_ordered: list[str] = []
    seen_limitations: set[str] = set()
    provenance_map: dict[str, str] = {}

    for group in all_groups:
        for metric_name, result in group.items():
            provenance_map[metric_name] = result.provenance.value
            for limit_note in result.limitations:
                if limit_note not in seen_limitations:
                    seen_limitations.add(limit_note)
                    limitations_ordered.append(limit_note)

    if provider_tier.lower() == "unit_test" or provider_name.lower() == "mock":
        mock_note = (
            "Mock (unit_test) run validates control flow/contracts ONLY and is NOT evidence of Vietnamese storytelling quality."
        )
        if mock_note not in seen_limitations:
            limitations_ordered.append(mock_note)

    return EvaluationReport(
        run_id=run_id,
        experiment_id=experiment_id,
        method=method,
        scenario=scenario,
        provider_tier=provider_tier,
        provider_name=provider_name,
        model_id=model_id,
        history_window=raw_window,
        termination_reason=termination_reason,
        coverage=coverage,
        repetition=repetition,
        safety=safety,
        reliability=reliability,
        performance=performance,
        human_eval_placeholders=human_eval_placeholders,
        hard_gates_passed=(len(hard_gate_failures) == 0),
        structural_hard_gates_status=structural_status,
        factual_safety_gate_status=factual_status,
        overall_gate_status=overall_gate_status,
        not_evaluated_gates=tuple(not_evaluated_gates),
        hard_gate_failures=tuple(hard_gate_failures),
        limitations=tuple(limitations_ordered),
        metric_provenance=provenance_map,
    )


def evaluate_run_directory(
    run_dir: Path,
    *,
    gold_labels: Optional[Sequence[GoldFactualLabel]] = None,
) -> EvaluationReport:
    """Nạp thư mục bằng chứng và trả về `EvaluationReport` hoàn chỉnh."""
    evidence = load_run_evidence(run_dir)
    return evaluate_run(evidence, gold_labels=gold_labels)
