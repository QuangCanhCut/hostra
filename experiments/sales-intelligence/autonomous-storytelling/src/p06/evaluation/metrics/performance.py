"""Nhóm chỉ số hiệu năng, độ trễ, tiêu thụ token và chi phí ước tính cho P06 (`p06.evaluation.metrics.performance`).

1. File này giải quyết vấn đề gì?
   Đo lường trung thực độ trễ gọi LLM, độ trễ xử lý từng lượt đồ thị, thời lượng lời thoại
   mô phỏng, lượng token tiêu thụ (bao gồm cả token lãng phí do rewrite/reject) và chi phí ước tính,
   đồng thời ngăn chặn việc ngụy tạo số `0` khi thiếu telemetry token hoặc dùng Mock provider.
2. Trách nhiệm chính của module là gì?
   Cung cấp hàm thuần `compute_percentile()` (nội suy tuyến tính) và `compute_performance_metrics()`
   trả về từ điển `dict[str, MetricResult]` chuẩn hóa theo provenance.
3. Module này liên kết với các thành phần nào?
   Đọc `RunEvidence` và xuất `MetricResult`, `MetricStatus`, `MetricProvenance` từ `p06.evaluation.models`.
   Hàm `compute_percentile()` cũng được tái sử dụng bởi `repetition.py` và `reliability.py`.
4. Input và output chính là gì?
   Input là `RunEvidence`; Output là ánh xạ tên metric -> `MetricResult`.
5. Có những constraints hoặc invariants quan trọng nào?
   - Nếu `total_model_calls == 0` hoặc BẤT KỲ `ProviderCallRecord` nào có `token_usage_source == "UNAVAILABLE"`
     hoặc `input_tokens is None` / `output_tokens is None`, thì `input_tokens`, `output_tokens` và
     `wasted_tokens` BẮT BUỘC trả về `MetricStatus.NOT_EVALUATED` (`value=None`), cấm trả `0`.
   - `estimated_llm_cost_usd` trả `NOT_APPLICABLE` cho `unit_test`/`mock`/token mô phỏng, và `NOT_EVALUATED`
     nếu thiếu bảng giá `pricing` trong `manifest`.
   - Tách bạch `MEASURED_WALL_CLOCK`, `SIMULATED_CLOCK`, `PROVIDER_REPORTED` và `ESTIMATED`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Optional

from p06.evaluation.models import (
    MetricProvenance,
    MetricResult,
    MetricStatus,
    PlaybackEventRecord,
    RunEvidence,
    is_clean_termination_boundary_trace,
)


def compute_percentile(values: Sequence[float], q: float) -> Optional[float]:
    """Tính phân vị thứ `q` (`0.0 <= q <= 1.0`) bằng nội suy tuyến tính thuần Python.

    Công thức toán học (Type-7 linear interpolation):
        Với dãy đã sắp tăng `xs = [x_0, ..., x_{n-1}]`:
        - Nếu `n == 0`: trả về `None`.
        - Nếu `n == 1`: trả về `xs[0]`.
        - Đặt `pos = q * (n - 1)`, `lo = floor(pos)`, `hi = ceil(pos)`:
          `P_q = xs[lo] + (pos - lo) * (xs[hi] - xs[lo])`.

    Ví dụ tính tay:
        `values = [10.0, 20.0, 30.0, 40.0]`, `q = 0.50`:
        `pos = 0.50 * 3 = 1.5`, `lo = 1`, `hi = 2` -> `20.0 + 0.5 * (30.0 - 20.0) = 25.0`.

    Args:
        values: Chuỗi giá trị số thực cần tính phân vị.
        q: Tỷ lệ phân vị trong đoạn `[0.0, 1.0]` (ví dụ `0.50` cho P50, `0.95` cho P95).

    Returns:
        Optional[float]: Giá trị phân vị hoặc `None` nếu `values` rỗng.

    Raises:
        ValueError: Nếu `q` nằm ngoài `[0.0, 1.0]` hoặc không phải số hữu hạn.
    """
    if isinstance(q, bool) or not isinstance(q, (int, float)) or not math.isfinite(float(q)):
        raise ValueError(f"q phải là số thực hữu hạn trong [0.0, 1.0], nhận được {q!r}.")
    q_float = float(q)
    if not (0.0 <= q_float <= 1.0):
        raise ValueError(f"q phải nằm trong [0.0, 1.0], nhận được {q!r}.")

    if not values:
        return None
    xs = sorted(float(v) for v in values)
    n = len(xs)
    if n == 1:
        return xs[0]
    pos = q_float * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    return xs[lo] + (pos - lo) * (xs[hi] - xs[lo])


def _deduplicated_completed_events(
    playback_events: Sequence[PlaybackEventRecord],
) -> list[PlaybackEventRecord]:
    """Lọc các sự kiện playback `applied=True` và `outcome=='COMPLETED'` không trùng lặp ACK."""
    ordered = sorted(playback_events, key=lambda ev: ev.sequence_index)
    seen_event_ids: set[str] = set()
    seen_turn_ids: set[str] = set()
    accepted: list[PlaybackEventRecord] = []
    for ev in ordered:
        if not ev.applied or ev.outcome != "COMPLETED":
            continue
        if ev.playback_event_id is not None and ev.playback_event_id in seen_event_ids:
            continue
        if ev.turn_id in seen_turn_ids:
            continue
        if ev.playback_event_id is not None:
            seen_event_ids.add(ev.playback_event_id)
        seen_turn_ids.add(ev.turn_id)
        accepted.append(ev)
    return accepted


def compute_performance_metrics(evidence: RunEvidence) -> dict[str, MetricResult]:
    """Tính toàn bộ nhóm chỉ số hiệu năng, độ trễ, token và chi phí ước tính từ `RunEvidence`.

    Công thức chính:
    1. `provider_latency_p50_ms`, `provider_latency_p95_ms`:
       Phân vị P50 và P95 trên `[c.latency_ms for c in evidence.provider_calls]`.
       - Ý nghĩa: Phản ánh độ trễ gọi LLM thuần (tách khỏi TTS/lipsync).
       - Trường hợp biên: 0 calls -> `NOT_EVALUATED` (`value=None`).
       - Giới hạn: Nếu `c.is_simulated_metric=True`, gắn `is_simulated=True` và không đại diện API thật.
    2. `invocation_latency_p50_ms`, `invocation_latency_p95_ms`:
       Phân vị P50 và P95 trên `[t.invocation_latency_ms for t in evidence.graph_traces]`.
       - Ý nghĩa: Thời gian đồng hồ tường (`MEASURED_WALL_CLOCK`) toàn chu trình 1 lượt graph/baseline.
    3. `planning_latency_ms`, `upfront_script_generation_latency_ms`, `total_measured_processing_ms`:
       Đọc trực tiếp từ `RunEvidence` với provenance `MEASURED_WALL_CLOCK`.
    4. `simulated_speech_duration_sec`:
       `sum(ev.actual_duration_ms / 1000.0)` trên các sự kiện playback `applied=True & outcome=='COMPLETED'`
       đã khử trùng ACK (`0.0` nếu chưa có sự kiện hoàn tất nào).
       - Giới hạn: Là thời lượng phát âm thanh mô phỏng (`SIMULATED_CLOCK`), không phải audio TTS thật.
    5. `total_model_calls`, `input_tokens`, `output_tokens`, `wasted_tokens`:
       - `total_model_calls = len(evidence.provider_calls)`.
       - `input_tokens = sum(c.input_tokens)`, `output_tokens = sum(c.output_tokens)`,
         `wasted_tokens = sum(c.input_tokens + c.output_tokens for c in calls if c.is_wasted)`.
       - Bất biến: Nếu `total_model_calls == 0` hoặc có bất kỳ call nào thiếu token /
         `token_usage_source == 'UNAVAILABLE'`, trả `NOT_EVALUATED` (`value=None`), tuyệt đối không điền `0`.
    6. `estimated_llm_cost_usd`:
       `(input_tokens / 1e6) * input_per_1m_usd + (output_tokens / 1e6) * output_per_1m_usd`.
       - Trả `NOT_APPLICABLE` cho tier `unit_test` / provider `mock` / token mô phỏng / 0 calls;
       - Trả `NOT_EVALUATED` nếu thiếu `pricing` trong `manifest` hoặc thiếu số liệu token.

    Ví dụ tính tay:
        2 calls có `latency_ms = [100.0, 200.0]`, `input_tokens = [50, 70]`, `output_tokens = [20, 30]`,
        call thứ 2 có `is_wasted = True`:
        `provider_latency_p50_ms = 150.0`, `input_tokens = 120`, `output_tokens = 50`,
        `wasted_tokens = 70 + 30 = 100`.

    Args:
        evidence: Tập bằng chứng thô bất biến của một lần chạy.

    Returns:
        dict[str, MetricResult]: Từ điển các chỉ số hiệu năng chuẩn hóa.
    """
    results: dict[str, MetricResult] = {}

    # 1. Độ trễ gọi LLMProvider
    calls = evidence.provider_calls
    if not calls:
        for name in ("provider_latency_p50_ms", "provider_latency_p95_ms"):
            results[name] = MetricResult(
                name=name,
                status=MetricStatus.NOT_EVALUATED,
                value=None,
                unit="ms",
                data_source="provider_calls",
                provenance=MetricProvenance.UNAVAILABLE,
                is_simulated=False,
                missing_reason="No LLM provider calls recorded in provider_calls.",
            )
    else:
        latencies = [float(c.latency_ms) for c in calls]
        any_sim_latency = any(c.is_simulated_metric for c in calls)
        lat_prov = (
            MetricProvenance.SIMULATED_CLOCK
            if any_sim_latency
            else MetricProvenance.MEASURED_WALL_CLOCK
        )
        p50 = compute_percentile(latencies, 0.50)
        p95 = compute_percentile(latencies, 0.95)
        results["provider_latency_p50_ms"] = MetricResult(
            name="provider_latency_p50_ms",
            status=MetricStatus.COMPUTED,
            value=p50,
            unit="ms",
            data_source="provider_calls",
            provenance=lat_prov,
            is_simulated=any_sim_latency,
            limitations=(
                ("Includes simulated mock latencies; not indicative of real LLM latency.",)
                if any_sim_latency
                else ()
            ),
        )
        results["provider_latency_p95_ms"] = MetricResult(
            name="provider_latency_p95_ms",
            status=MetricStatus.COMPUTED,
            value=p95,
            unit="ms",
            data_source="provider_calls",
            provenance=lat_prov,
            is_simulated=any_sim_latency,
            limitations=(
                ("Includes simulated mock latencies; not indicative of real LLM latency.",)
                if any_sim_latency
                else ()
            ),
        )

    # 2. Độ trễ thực thi từng lượt graph/baseline (wall-clock), loại lượt kết thúc biên SKU sạch
    all_traces = evidence.graph_traces
    content_traces = [t for t in all_traces if not is_clean_termination_boundary_trace(t)]
    excluded_boundary_count = len(all_traces) - len(content_traces)
    if not content_traces:
        for name in ("invocation_latency_p50_ms", "invocation_latency_p95_ms"):
            results[name] = MetricResult(
                name=name,
                status=MetricStatus.NOT_EVALUATED,
                value=None,
                unit="ms",
                data_source="graph_traces",
                provenance=MetricProvenance.UNAVAILABLE,
                is_simulated=False,
                missing_reason="No substantive graph traces recorded in graph_traces.",
                metadata={"termination_boundary_turns_excluded": excluded_boundary_count},
            )
    else:
        inv_latencies = [float(t.invocation_latency_ms) for t in content_traces]
        results["invocation_latency_p50_ms"] = MetricResult(
            name="invocation_latency_p50_ms",
            status=MetricStatus.COMPUTED,
            value=compute_percentile(inv_latencies, 0.50),
            unit="ms",
            data_source="graph_traces",
            provenance=MetricProvenance.MEASURED_WALL_CLOCK,
            is_simulated=False,
            metadata={"termination_boundary_turns_excluded": excluded_boundary_count},
        )
        results["invocation_latency_p95_ms"] = MetricResult(
            name="invocation_latency_p95_ms",
            status=MetricStatus.COMPUTED,
            value=compute_percentile(inv_latencies, 0.95),
            unit="ms",
            data_source="graph_traces",
            provenance=MetricProvenance.MEASURED_WALL_CLOCK,
            is_simulated=False,
            metadata={"termination_boundary_turns_excluded": excluded_boundary_count},
        )

    # 3. Các mốc thời gian đồng hồ tường cấp phiên
    results["planning_latency_ms"] = MetricResult(
        name="planning_latency_ms",
        status=MetricStatus.COMPUTED,
        value=float(evidence.planning_latency_ms),
        unit="ms",
        data_source="run_evidence",
        provenance=MetricProvenance.MEASURED_WALL_CLOCK,
        is_simulated=False,
    )
    results["upfront_script_generation_latency_ms"] = MetricResult(
        name="upfront_script_generation_latency_ms",
        status=MetricStatus.COMPUTED,
        value=float(evidence.upfront_script_generation_latency_ms),
        unit="ms",
        data_source="run_evidence",
        provenance=MetricProvenance.MEASURED_WALL_CLOCK,
        is_simulated=False,
    )
    results["total_measured_processing_ms"] = MetricResult(
        name="total_measured_processing_ms",
        status=MetricStatus.COMPUTED,
        value=float(evidence.total_measured_processing_ms),
        unit="ms",
        data_source="run_evidence",
        provenance=MetricProvenance.MEASURED_WALL_CLOCK,
        is_simulated=False,
    )

    # 4. Thời lượng lời thoại mô phỏng từ ACK hoàn tất
    accepted_events = _deduplicated_completed_events(evidence.playback_events)
    simulated_speech_sec = sum(
        (ev.actual_duration_ms or 0) / 1000.0 for ev in accepted_events
    )
    results["simulated_speech_duration_sec"] = MetricResult(
        name="simulated_speech_duration_sec",
        status=MetricStatus.COMPUTED,
        value=simulated_speech_sec,
        unit="sec",
        data_source="playback_events",
        provenance=MetricProvenance.SIMULATED_CLOCK,
        is_simulated=True,
        limitations=("Derived from simulated playback durations, not actual TTS/MuseTalk audio.",),
    )

    # 5. Số lượng lời gọi mô hình và thống kê token
    total_calls = len(calls)
    results["total_model_calls"] = MetricResult(
        name="total_model_calls",
        status=MetricStatus.COMPUTED,
        value=total_calls,
        unit="calls",
        data_source="provider_calls",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
    )

    any_unavailable_tokens = any(
        c.token_usage_source == "UNAVAILABLE" or c.input_tokens is None or c.output_tokens is None
        for c in calls
    )
    total_input: Optional[int] = None
    total_output: Optional[int] = None
    any_simulated_tokens = any(
        c.token_usage_source == "SIMULATED" or c.is_simulated_metric for c in calls
    )

    if total_calls == 0:
        reason = "No LLM model calls executed (e.g. deterministic talking points mode)."
        for name in ("input_tokens", "output_tokens", "wasted_tokens"):
            results[name] = MetricResult(
                name=name,
                status=MetricStatus.NOT_EVALUATED,
                value=None,
                unit="tokens",
                data_source="provider_calls",
                provenance=MetricProvenance.UNAVAILABLE,
                is_simulated=False,
                missing_reason=reason,
            )
    elif any_unavailable_tokens:
        reason = "At least one provider call reported token_usage_source=UNAVAILABLE or null token counts."
        for name in ("input_tokens", "output_tokens", "wasted_tokens"):
            results[name] = MetricResult(
                name=name,
                status=MetricStatus.NOT_EVALUATED,
                value=None,
                unit="tokens",
                data_source="provider_calls",
                provenance=MetricProvenance.UNAVAILABLE,
                is_simulated=any_simulated_tokens,
                missing_reason=reason,
            )
    else:
        total_input = sum(int(c.input_tokens or 0) for c in calls)
        total_output = sum(int(c.output_tokens or 0) for c in calls)
        total_thinking = sum(int(c.thinking_tokens or 0) for c in calls)
        total_wasted = sum(
            int(c.input_tokens or 0) + int(c.output_tokens or 0) + int(c.thinking_tokens or 0)
            for c in calls
            if c.is_wasted
        )
        token_prov = (
            MetricProvenance.SIMULATED_CLOCK
            if any_simulated_tokens
            else MetricProvenance.PROVIDER_REPORTED
        )
        token_limits = (
            ("Token counts are simulated by MockLLMProvider, not real tokenizer outputs.",)
            if any_simulated_tokens
            else ()
        )
        results["input_tokens"] = MetricResult(
            name="input_tokens",
            status=MetricStatus.COMPUTED,
            value=total_input,
            unit="tokens",
            data_source="provider_calls",
            provenance=token_prov,
            is_simulated=any_simulated_tokens,
            limitations=token_limits,
        )
        results["output_tokens"] = MetricResult(
            name="output_tokens",
            status=MetricStatus.COMPUTED,
            value=total_output,
            unit="tokens",
            data_source="provider_calls",
            provenance=token_prov,
            is_simulated=any_simulated_tokens,
            limitations=token_limits,
            metadata={"thinking_tokens": total_thinking},
        )
        results["wasted_tokens"] = MetricResult(
            name="wasted_tokens",
            status=MetricStatus.COMPUTED,
            value=total_wasted,
            unit="tokens",
            data_source="provider_calls",
            provenance=token_prov,
            is_simulated=any_simulated_tokens,
            limitations=token_limits,
        )

    # 6. Chi phí LLM ước tính (USD)
    tier = str(evidence.manifest.get("provider_tier", "")).strip().lower()
    provider_name = str(evidence.manifest.get("provider_name", "")).strip().lower()
    if tier == "unit_test" or provider_name == "mock" or any_simulated_tokens:
        results["estimated_llm_cost_usd"] = MetricResult(
            name="estimated_llm_cost_usd",
            status=MetricStatus.NOT_APPLICABLE,
            value=None,
            unit="usd",
            data_source="manifest+provider_calls",
            provenance=MetricProvenance.UNAVAILABLE,
            is_simulated=True,
            missing_reason="Mock tokens are simulated and incur no real LLM API cost.",
        )
    elif tier == "local_smoke_test" or provider_name == "ollama":
        results["estimated_llm_cost_usd"] = MetricResult(
            name="estimated_llm_cost_usd",
            status=MetricStatus.NOT_APPLICABLE,
            value=None,
            unit="usd",
            data_source="manifest+provider_calls",
            provenance=MetricProvenance.UNAVAILABLE,
            is_simulated=False,
            missing_reason="Local Ollama CPU inference runs locally and incurs no per-token API cost.",
        )
    elif total_calls == 0:
        results["estimated_llm_cost_usd"] = MetricResult(
            name="estimated_llm_cost_usd",
            status=MetricStatus.NOT_APPLICABLE,
            value=None,
            unit="usd",
            data_source="manifest+provider_calls",
            provenance=MetricProvenance.UNAVAILABLE,
            is_simulated=False,
            missing_reason="No LLM model calls were executed.",
        )
    elif total_input is None or total_output is None:
        results["estimated_llm_cost_usd"] = MetricResult(
            name="estimated_llm_cost_usd",
            status=MetricStatus.NOT_EVALUATED,
            value=None,
            unit="usd",
            data_source="manifest+provider_calls",
            provenance=MetricProvenance.UNAVAILABLE,
            is_simulated=False,
            missing_reason="Token counts are unavailable; cannot estimate LLM API cost.",
        )
    else:
        pricing = evidence.manifest.get("pricing")
        if not isinstance(pricing, Mapping):
            provider_cfg = evidence.manifest.get("provider_config")
            if isinstance(provider_cfg, Mapping):
                pricing = provider_cfg.get("pricing")
        if (
            isinstance(pricing, Mapping)
            and isinstance(pricing.get("input_per_1m_usd"), (int, float))
            and not isinstance(pricing.get("input_per_1m_usd"), bool)
            and isinstance(pricing.get("output_per_1m_usd"), (int, float))
            and not isinstance(pricing.get("output_per_1m_usd"), bool)
        ):
            rate_in = float(pricing["input_per_1m_usd"])
            rate_out = float(pricing["output_per_1m_usd"])
            billable_output_tokens = total_output + sum(int(c.thinking_tokens or 0) for c in calls)
            est_cost = (total_input / 1_000_000.0) * rate_in + (
                billable_output_tokens / 1_000_000.0
            ) * rate_out
            results["estimated_llm_cost_usd"] = MetricResult(
                name="estimated_llm_cost_usd",
                status=MetricStatus.COMPUTED,
                value=est_cost,
                unit="usd",
                data_source="manifest+provider_calls",
                provenance=MetricProvenance.ESTIMATED,
                is_simulated=False,
                metadata={
                    "pricing": dict(pricing),
                    "billable_output_tokens": billable_output_tokens,
                    "thinking_tokens_included_in_output": sum(int(c.thinking_tokens or 0) for c in calls),
                },
            )
        else:
            results["estimated_llm_cost_usd"] = MetricResult(
                name="estimated_llm_cost_usd",
                status=MetricStatus.NOT_EVALUATED,
                value=None,
                unit="usd",
                data_source="manifest+provider_calls",
                provenance=MetricProvenance.UNAVAILABLE,
                is_simulated=False,
                missing_reason="Pricing metadata missing in manifest; cannot estimate LLM cost.",
            )

    return results
