"""Bộ điều phối chạy thử Gemini Free Tier (`E01-T09` Stage A Smoke Test & Stage B Short Pilot).

1. File này giải quyết vấn đề gì?
   Cung cấp điểm chạy độc lập cho `Stage A` (Smoke Test <= 3 requests) và `Stage B`
   (Short Pilot `script_first_upfront_llm` vs `langgraph_structured_story W=5` <= 25 requests)
   trên mô hình `gemini-3.5-flash-lite` Free Tier với trần ngân sách tổng `<= 28` requests.
2. Trách nhiệm chính của module là gì?
   Duy trì sổ cái ngân sách `budget_ledger.json` liên phiên, dùng chung một `GeminiRestClient`
   có giãn nhịp tuần tự (>= 6 giây/request), dừng cứng khi gặp HTTP 429 hoặc chạm trần,
   và xuất `comparison.{json,csv,md}` cùng phiếu chấm mù `human_eval/`.
3. Module này liên kết với các thành phần nào?
   Sử dụng `GeminiAPIProvider`, `GeminiRestClient`, `P05KnowledgeAdapter`,
   `ScriptFirstBaseline`, `load_prompt_template`, `run_experiment`, `compare_runs`, và
   `export_blind_human_eval_sheets`.
4. Input và output chính là gì?
   Input là `--stage {smoke,pilot}` và biến môi trường `GEMINI_API_KEY`;
   Output là `budget_ledger.json`, `stage_a_smoke_results.json`, `stage_b_pilot_summary.json`,
   hai thư mục run chuẩn 10 artifacts, bảng đối chiếu và phiếu chấm mù.
5. Có những constraints hoặc invariants quan trọng nào?
   - Tuyệt đối KHÔNG ghi, in hay lưu giá trị `GEMINI_API_KEY` vào log/artifact.
   - Tổng request Stage A + Stage B không vượt quá 28; không retry vô hạn; gặp 429 dừng ngay.
   - Không tự chuyển model khác hoặc fallback sang `MockLLMProvider`.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Optional

import yaml

# Bảo đảm nạp được gói `p06` khi chạy trực tiếp script CLI.
_MODULE_ROOT = Path(__file__).resolve().parents[2]
_SRC_DIR = _MODULE_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from p06.adapters.p05_knowledge_adapter import P05KnowledgeAdapter  # noqa: E402
from p06.agent.nodes._common import (  # noqa: E402
    _compute_word_budget,
    format_untrusted_knowledge_block,
)
from p06.baselines.script_first import (  # noqa: E402
    _UPFRONT_PROMPT_VERSION,
    _UPFRONT_SYSTEM_PROMPT_TEMPLATE,
    UpfrontChunkDraftLLMOutput,
)
from p06.evaluation.comparison import (  # noqa: E402
    compare_runs,
    export_comparison_csv,
    export_comparison_json,
    export_comparison_markdown,
)
from p06.evaluation.human_eval import export_blind_human_eval_sheets  # noqa: E402
from p06.planning.draft_dtos import ChunkDraftLLMOutput  # noqa: E402
from p06.planning.prompt_loader import load_prompt_template, render_prompt_template  # noqa: E402
from p06.providers.base import GenerationRequest, ProviderError  # noqa: E402
from p06.providers.gemini_provider import (  # noqa: E402
    GeminiAPIProvider,
    GeminiProviderConfig,
    GeminiRestClient,
)
from p06.runner.config import (  # noqa: E402
    DEFAULT_E01_EXT_V1_STORY_PLANS_PATH,
    DEFAULT_E01_EXT_V1_VERIFIED_SKUS_PATH,
    DEFAULT_PROMPTS_DIR,
    DEFAULT_RUNS_OUTPUT_DIR,
    ExperimentMethod,
    RunTerminationReason,
    load_e01_story_plan,
    load_experiment_run_config,
)
from p06.runner.session_runner import run_experiment  # noqa: E402
from p06.schemas.candidate import (  # noqa: E402
    CandidateOrigin,
    CandidateVerificationStatus,
    CoverageMode,
    ProposedResponseCoverage,
    SpeechCandidate,
    TargetScopeMode,
)
from p06.simulation.virtual_clock import VirtualClock, compute_chunk_word_budget  # noqa: E402

DEFAULT_MODEL_CONFIG_PATH: Final[Path] = (
    _MODULE_ROOT / "configs" / "models" / "gemini_3.5_flash_lite_free.yaml"
)
DEFAULT_PILOT_OUTPUT_DIR: Final[Path] = (
    DEFAULT_RUNS_OUTPUT_DIR / "gemini_3.5_flash_lite_pilot"
)
MAX_STAGE_A_REQUESTS: Final[int] = 3
MAX_STAGE_B_REQUESTS: Final[int] = 25
MAX_TOTAL_REQUESTS: Final[int] = 28


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_or_init_ledger(ledger_path: Path) -> dict[str, Any]:
    if ledger_path.is_file():
        return dict(json.loads(ledger_path.read_text(encoding="utf-8")))
    return {
        "model_id": "gemini-3.5-flash-lite",
        "billing_tier": "free_tier",
        "max_stage_a_requests": MAX_STAGE_A_REQUESTS,
        "max_stage_b_requests": MAX_STAGE_B_REQUESTS,
        "max_total_requests": MAX_TOTAL_REQUESTS,
        "stage_a_requests": 0,
        "stage_b_requests": 0,
        "total_requests": 0,
        "events": [],
    }


def _save_ledger(ledger_path: Path, ledger: dict[str, Any]) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_gemini_model_config(config_path: Path) -> GeminiProviderConfig:
    raw_yaml = yaml.safe_load(config_path.read_text(encoding="utf-8"))
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
    return GeminiProviderConfig.model_validate(fields)


def _run_stage_a_smoke(output_dir: Path, config_path: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = output_dir / "budget_ledger.json"
    ledger = _load_or_init_ledger(ledger_path)

    remaining_a = min(
        MAX_STAGE_A_REQUESTS - int(ledger["stage_a_requests"]),
        MAX_TOTAL_REQUESTS - int(ledger["total_requests"]),
    )
    if remaining_a <= 0:
        raise SystemExit(
            f"[BUDGET BLOCKED] Ngân sách Stage A đã hết: stage_a={ledger['stage_a_requests']}, "
            f"total={ledger['total_requests']}."
        )

    gem_cfg = _load_gemini_model_config(config_path)
    rest_client = GeminiRestClient(
        api_key_env=gem_cfg.api_key_env,
        thinking_budget=gem_cfg.thinking_budget,
        thinking_level=gem_cfg.thinking_level,
        min_request_interval_sec=gem_cfg.min_request_interval_sec,
        max_requests=remaining_a,
        stop_on_rate_limit=True,
    )
    provider = GeminiAPIProvider(config=gem_cfg, client=rest_client)

    results_path = output_dir / "stage_a_smoke_results.json"
    prior_results: Optional[dict[str, Any]] = None
    if results_path.is_file():
        prior_results = dict(json.loads(results_path.read_text(encoding="utf-8")))

    prior_meta_ok = (
        isinstance(prior_results, dict)
        and isinstance(prior_results.get("checks"), dict)
        and prior_results["checks"].get("request_1_model_metadata", {}).get("status") == "PASSED"
    )
    resume_single_slot = prior_meta_ok and remaining_a == 1

    results: dict[str, Any] = {
        "stage": "Stage A - Gemini Smoke Test",
        "executed_at_utc": _now_utc_iso(),
        "model_id": gem_cfg.model_id,
        "thinking_level": gem_cfg.thinking_level,
        "min_request_interval_sec": gem_cfg.min_request_interval_sec,
        "max_requests_budget": remaining_a,
        "checks": dict(prior_results.get("checks", {})) if prior_results else {},
        "prior_attempts": (
            list(prior_results.get("prior_attempts", []))
            + [{"at_utc": prior_results.get("executed_at_utc"), "checks": prior_results.get("checks")}]
            if prior_results
            else []
        ),
        "requests_attempted": 0,
        "rate_limited": False,
        "all_passed": False,
    }

    try:
        # Request 1: Kiểm tra kết nối, xác thực và metadata model thật (bỏ qua nếu đã PASS ở lượt trước và chỉ còn 1 slot).
        if not resume_single_slot:
            try:
                meta = rest_client.check_model_metadata(gem_cfg.model_id, timeout_sec=gem_cfg.timeout_sec)
                results["checks"]["request_1_model_metadata"] = {
                    "status": "PASSED",
                    "metadata": meta,
                }
            except ProviderError as exc:
                results["checks"]["request_1_model_metadata"] = {
                    "status": "FAILED",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "response_headers": rest_client.last_response_headers,
                }
                return 1

        # Nạp plan & adapter synthetic từ e01_ext_v1.
        plan, _, _ = load_e01_story_plan(
            "pilot_short_3sku_ext",
            story_plans_path=DEFAULT_E01_EXT_V1_STORY_PLANS_PATH,
        )
        adapter = P05KnowledgeAdapter.from_seed_file(DEFAULT_E01_EXT_V1_VERIFIED_SKUS_PATH)
        clock = VirtualClock()

        # Request 2: ChunkDraftLLMOutput + xác minh thật qua P05.
        arc_honey = plan.arcs[0]
        topic_honey = arc_honey.topics[0]
        ev_honey = adapter.get_sku_evidence(plan.tenant_id, "SKU-HONEY-01", at_time=clock.now())
        prompt_tpl = load_prompt_template("story_generation.txt", prompts_dir=DEFAULT_PROMPTS_DIR)
        max_words_lg, target_range_lg = _compute_word_budget(8.0)
        allowed_eids_lg = [
            chunk["evidence_id"]
            for chunk in ev_honey.approved_chunks
            if not topic_honey.fact_refs or chunk["evidence_id"] in set(topic_honey.fact_refs)
        ] or [chunk["evidence_id"] for chunk in ev_honey.approved_chunks]
        allowed_cids_lg = [
            claim["claim_id"]
            for claim in ev_honey.allowed_claims
            if claim.get("claim_id")
            and (not topic_honey.allowed_claim_ids or claim["claim_id"] in set(topic_honey.allowed_claim_ids))
        ] or [claim["claim_id"] for claim in ev_honey.allowed_claims if claim.get("claim_id")]
        user_prompt_lg = render_prompt_template(
            prompt_tpl,
            {
                "active_sku_id": "SKU-HONEY-01",
                "session_goal": plan.session_goal,
                "arc_title": arc_honey.title,
                "topic_id": topic_honey.topic_id,
                "topic_title": topic_honey.title,
                "talking_points": "; ".join(topic_honey.talking_points),
                "allowed_evidence_ids": json.dumps(allowed_eids_lg, ensure_ascii=False),
                "allowed_claim_ids": json.dumps(allowed_cids_lg, ensure_ascii=False),
                "mandatory_messages": "; ".join(plan.mandatory_messages),
                "prohibited_topics": "; ".join(plan.prohibited_topics),
                "max_duration_sec": "8",
                "max_words": str(max_words_lg),
                "target_words_range": target_range_lg,
                "played_history_summary": "(Chưa có lượt nào được phát trong phiên.)",
                "untrusted_knowledge_block": format_untrusted_knowledge_block(ev_honey, topic_honey),
            },
        )
        req_lg = GenerationRequest(
            request_id="smoke-a-02-chunk-draft",
            system_prompt=(
                "Bạn là agent kể chuyện bán hàng tiếng Việt P06 thuộc HOSTRA AI. "
                "Tuân thủ chặt I-02 (chỉ nháp), I-04 (khóa SKU hiện hành) và chỉ xuất JSON thuần túy."
            ),
            user_prompt=user_prompt_lg,
            prompt_version=prompt_tpl.version,
            data_classification="SYNTHETIC",
            seed=42,
        )
        try:
            res_lg = provider.generate_structured(req_lg, ChunkDraftLLMOutput)
            out_lg = res_lg.parsed_output
            dur_ms = VirtualClock.estimate_raw_speech_duration_ms(out_lg.text)
            cand_lg = SpeechCandidate(
                candidate_id="cand-smoke-a-02",
                turn_id="turn-smoke-a-02",
                tenant_id=plan.tenant_id,
                session_id=plan.session_id,
                session_epoch=1,
                origin=CandidateOrigin.PROACTIVE_STORY,
                source_chunk_id="chunk-smoke-a-02",
                scope_mode=TargetScopeMode.SINGLE_SKU,
                sku_refs=["SKU-HONEY-01"],
                sku_bindings=[
                    ev_honey.to_version_binding(
                        cited_evidence_ids=out_lg.cited_evidence_ids,
                        stated_price_vnd=out_lg.stated_price_vnd,
                        mentions_ocop=out_lg.mentions_ocop,
                    )
                ],
                session_rights_version=1,
                intent=f"PROACTIVE_STORY:{topic_honey.topic_id}",
                text=out_lg.text,
                semantic_breakpoint=out_lg.semantic_breakpoint,
                estimated_duration_sec=max(0.5, dur_ms / 1000.0),
                proposed_coverage=ProposedResponseCoverage(
                    covered_topic_ids=[topic_honey.topic_id],
                    covered_intents=[topic_honey.title],
                    coverage_mode=CoverageMode.FULL,
                    is_authoritative=False,
                ),
                verification_status=CandidateVerificationStatus.DRAFT,
                rewrite_attempt=0,
            )
            ver_lg = adapter.verify_candidate(cand_lg, verified_at=clock.now())
            results["checks"]["request_2_chunk_draft_dto"] = {
                "status": "PASSED",
                "parsed_output": out_lg.model_dump(mode="json"),
                "telemetry": res_lg.telemetry.model_dump(mode="json"),
                "p05_verification": {
                    "status": ver_lg.status.value,
                    "gate_decision_id": ver_lg.gate_decision_id,
                    "reasons": list(ver_lg.reasons),
                },
                "response_headers": rest_client.last_response_headers,
            }
        except ProviderError as exc:
            results["checks"]["request_2_chunk_draft_dto"] = {
                "status": "FAILED",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "telemetry": exc.telemetry.model_dump(mode="json") if exc.telemetry else None,
                "response_headers": rest_client.last_response_headers,
            }
            return 1

        if resume_single_slot:
            # Còn đúng 1/3 slot Stage A sau lỗi schema lượt trước: không gửi thêm Request 3 vượt trần Stage A=3.
            results["all_passed"] = True
            return 0

        # Request 3: UpfrontChunkDraftLLMOutput + xác minh thật qua P05.
        arc_tea = plan.arcs[1]
        topic_tea = arc_tea.topics[0]
        ev_tea = adapter.get_sku_evidence(plan.tenant_id, "SKU-TEA-02", at_time=clock.now())
        _, hard_max_sf, target_range_sf = compute_chunk_word_budget(8.0)
        sys_prompt_sf = _UPFRONT_SYSTEM_PROMPT_TEMPLATE.format(
            target_words_range=target_range_sf,
            hard_max_words=hard_max_sf,
            max_duration_sec="8",
        )
        user_payload_sf = {
            "session_goal": plan.session_goal,
            "arc": {"arc_id": arc_tea.arc_id, "position": arc_tea.position, "title": arc_tea.title},
            "topic": {
                "topic_id": topic_tea.topic_id,
                "title": topic_tea.title,
                "fact_refs": list(topic_tea.fact_refs),
                "allowed_claim_ids": list(topic_tea.allowed_claim_ids),
                "talking_points": list(topic_tea.talking_points),
            },
            "sku_evidence": {
                "sku_id": ev_tea.sku_id,
                "sku_name": ev_tea.sku_name,
                "price_vnd": ev_tea.price_vnd,
                "origin": ev_tea.origin,
                "weight_display": ev_tea.weight_display,
                "expiry_display": ev_tea.expiry_display,
                "approved_chunks": list(ev_tea.approved_chunks),
                "allowed_claims": list(ev_tea.allowed_claims),
                "prohibited_claims": list(ev_tea.prohibited_claims),
            },
        }
        req_sf = GenerationRequest(
            request_id="smoke-a-03-upfront-draft",
            system_prompt=sys_prompt_sf,
            user_prompt=json.dumps(user_payload_sf, ensure_ascii=False),
            prompt_version=_UPFRONT_PROMPT_VERSION,
            data_classification="SYNTHETIC",
            seed=42,
        )
        try:
            res_sf = provider.generate_structured(req_sf, UpfrontChunkDraftLLMOutput)
            out_sf = res_sf.parsed_output
            dur_sf_ms = VirtualClock.estimate_raw_speech_duration_ms(out_sf.text)
            cand_sf = SpeechCandidate(
                candidate_id="cand-smoke-a-03",
                turn_id="turn-smoke-a-03",
                tenant_id=plan.tenant_id,
                session_id=plan.session_id,
                session_epoch=1,
                origin=CandidateOrigin.PROACTIVE_STORY,
                source_chunk_id="chunk-smoke-a-03",
                scope_mode=TargetScopeMode.SINGLE_SKU,
                sku_refs=["SKU-TEA-02"],
                sku_bindings=[
                    ev_tea.to_version_binding(
                        cited_evidence_ids=out_sf.cited_evidence_ids,
                        stated_price_vnd=out_sf.stated_price_vnd,
                        mentions_ocop=out_sf.mentions_ocop,
                    )
                ],
                session_rights_version=1,
                intent=f"story_topic:{topic_tea.topic_id}",
                text=out_sf.text,
                semantic_breakpoint=out_sf.semantic_breakpoint,
                estimated_duration_sec=max(0.5, dur_sf_ms / 1000.0),
                proposed_coverage=ProposedResponseCoverage(
                    covered_topic_ids=[topic_tea.topic_id],
                    covered_intents=[f"story_topic:{topic_tea.topic_id}"],
                    coverage_mode=CoverageMode.FULL,
                    is_authoritative=False,
                ),
                verification_status=CandidateVerificationStatus.DRAFT,
                rewrite_attempt=0,
            )
            ver_sf = adapter.verify_candidate(cand_sf, verified_at=clock.now())
            results["checks"]["request_3_upfront_draft_dto"] = {
                "status": "PASSED",
                "parsed_output": out_sf.model_dump(mode="json"),
                "telemetry": res_sf.telemetry.model_dump(mode="json"),
                "p05_verification": {
                    "status": ver_sf.status.value,
                    "gate_decision_id": ver_sf.gate_decision_id,
                    "reasons": list(ver_sf.reasons),
                },
                "response_headers": rest_client.last_response_headers,
            }
        except ProviderError as exc:
            results["checks"]["request_3_upfront_draft_dto"] = {
                "status": "FAILED",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "telemetry": exc.telemetry.model_dump(mode="json") if exc.telemetry else None,
                "response_headers": rest_client.last_response_headers,
            }
            return 1

        results["all_passed"] = True
        return 0
    finally:
        attempted = rest_client.requests_attempted
        results["requests_attempted"] = attempted
        results["rate_limited"] = rest_client.rate_limited
        ledger["stage_a_requests"] = int(ledger["stage_a_requests"]) + attempted
        ledger["total_requests"] = int(ledger["total_requests"]) + attempted
        ledger["events"].append(
            {
                "stage": "stage_a_smoke",
                "at_utc": _now_utc_iso(),
                "requests_attempted": attempted,
                "rate_limited": rest_client.rate_limited,
                "all_passed": results["all_passed"],
            }
        )
        _save_ledger(ledger_path, ledger)
        (output_dir / "stage_a_smoke_results.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def _summarize_partial_token_usage(run_dir: Path) -> dict[str, Any]:
    """Tách bạch số token đo được từ các call thành công và phần thiếu do các call lỗi (R06).

    Tuyệt đối không gọi tổng từng phần (`partial_measured_*`) là tổng token toàn phiên khi
    vẫn còn `failed_calls_count > 0` hoặc `aggregate_token_usage_source == 'UNAVAILABLE'`.
    """
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


def _run_stage_b_pilot(output_dir: Path, config_path: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = output_dir / "budget_ledger.json"
    ledger = _load_or_init_ledger(ledger_path)

    remaining_b = min(
        MAX_STAGE_B_REQUESTS - int(ledger["stage_b_requests"]),
        MAX_TOTAL_REQUESTS - int(ledger["total_requests"]),
    )
    if remaining_b <= 0:
        raise SystemExit(
            f"[BUDGET BLOCKED] Ngân sách Stage B đã hết: stage_b={ledger['stage_b_requests']}, "
            f"total={ledger['total_requests']}."
        )

    gem_cfg = _load_gemini_model_config(config_path)
    rest_client = GeminiRestClient(
        api_key_env=gem_cfg.api_key_env,
        thinking_budget=gem_cfg.thinking_budget,
        thinking_level=gem_cfg.thinking_level,
        min_request_interval_sec=gem_cfg.min_request_interval_sec,
        max_requests=remaining_b,
        stop_on_rate_limit=True,
    )
    shared_provider = GeminiAPIProvider(config=gem_cfg, client=rest_client)

    summary: dict[str, Any] = {
        "stage": "Stage B - Short Pilot Experiment",
        "pilot_label": output_dir.name,
        "executed_at_utc": _now_utc_iso(),
        "model_id": gem_cfg.model_id,
        "dataset_profile": "e01_ext_v1",
        "scenario": "pilot_short_3sku_ext",
        "max_requests_budget": remaining_b,
        "runs": {},
        "requests_attempted_stage_b": 0,
        "rate_limited": False,
        "completed_both": False,
    }
    run_dirs: list[Path] = []
    exit_code = 1

    try:
        # Run 1: Script-first Upfront LLM (không quét W).
        cfg_sf = load_experiment_run_config(
            scenario="pilot_short_3sku_ext",
            dataset_profile="e01_ext_v1",
            method=ExperimentMethod.SCRIPT_FIRST_UPFRONT_LLM,
            provider="gemini",
            model_config_path=config_path,
            min_chunks_per_topic=1,
            seed=42,
            max_turns=20,
            max_llm_calls=remaining_b,
            output_dir=output_dir,
            allow_live_provider=True,
        )
        res_sf = run_experiment(cfg_sf, custom_llm_provider=shared_provider)
        run_dirs.append(res_sf.run_dir)
        spent_after_sf = rest_client.requests_attempted
        summary["runs"]["script_first_upfront_llm"] = {
            "run_id": res_sf.run_id,
            "run_dir": str(res_sf.run_dir),
            "termination_reason": res_sf.termination_reason.value,
            "transcript_turns": len(res_sf.evidence.transcript),
            "api_requests_attempted": spent_after_sf,
            "prompt_versions": dict(res_sf.manifest.get("prompt_versions") or {}),
            "prompt_hashes": dict(res_sf.manifest.get("prompt_hashes") or {}),
            "token_accounting": _summarize_partial_token_usage(res_sf.run_dir),
            "structural_hard_gates_status": (
                res_sf.report.structural_hard_gates_status.value if res_sf.report else None
            ),
            "overall_gate_status": (
                res_sf.report.overall_gate_status.value if res_sf.report else None
            ),
        }

        remaining_after_sf = remaining_b - spent_after_sf
        if (
            rest_client.rate_limited
            or remaining_after_sf <= 0
            or res_sf.termination_reason == RunTerminationReason.FATAL_ERROR
        ):
            return 1

        # Run 2: Dynamic LangGraph Storytelling (W=5).
        cfg_lg = load_experiment_run_config(
            scenario="pilot_short_3sku_ext",
            dataset_profile="e01_ext_v1",
            method=ExperimentMethod.LANGGRAPH,
            provider="gemini",
            model_config_path=config_path,
            history_window=5,
            min_chunks_per_topic=1,
            seed=42,
            max_turns=20,
            max_llm_calls=remaining_after_sf,
            output_dir=output_dir,
            allow_live_provider=True,
        )
        res_lg = run_experiment(cfg_lg, custom_llm_provider=shared_provider)
        run_dirs.append(res_lg.run_dir)
        spent_after_lg = rest_client.requests_attempted - spent_after_sf
        summary["runs"]["langgraph_structured_story_w5"] = {
            "run_id": res_lg.run_id,
            "run_dir": str(res_lg.run_dir),
            "termination_reason": res_lg.termination_reason.value,
            "transcript_turns": len(res_lg.evidence.transcript),
            "api_requests_attempted": spent_after_lg,
            "prompt_versions": dict(res_lg.manifest.get("prompt_versions") or {}),
            "prompt_hashes": dict(res_lg.manifest.get("prompt_hashes") or {}),
            "token_accounting": _summarize_partial_token_usage(res_lg.run_dir),
            "structural_hard_gates_status": (
                res_lg.report.structural_hard_gates_status.value if res_lg.report else None
            ),
            "overall_gate_status": (
                res_lg.report.overall_gate_status.value if res_lg.report else None
            ),
        }

        comp_report = compare_runs(run_dirs)
        export_comparison_json(comp_report, output_dir / "comparison.json")
        export_comparison_csv(comp_report, output_dir / "comparison.csv")
        export_comparison_markdown(comp_report, output_dir / "comparison.md")
        human_paths = export_blind_human_eval_sheets(run_dirs, output_dir / "human_eval", seed=42)
        summary["comparison_compatible"] = comp_report.compatible
        summary["comparison_md"] = str(output_dir / "comparison.md")
        summary["human_eval_files"] = [str(p) for p in human_paths]
        summary["completed_both"] = True
        exit_code = 0 if not rest_client.rate_limited else 1
        return exit_code
    finally:
        attempted = rest_client.requests_attempted
        summary["requests_attempted_stage_b"] = attempted
        summary["rate_limited"] = rest_client.rate_limited
        ledger["stage_b_requests"] = int(ledger["stage_b_requests"]) + attempted
        ledger["total_requests"] = int(ledger["total_requests"]) + attempted
        ledger["events"].append(
            {
                "stage": "stage_b_pilot",
                "at_utc": _now_utc_iso(),
                "requests_attempted": attempted,
                "total_requests_cumulative": ledger["total_requests"],
                "rate_limited": rest_client.rate_limited,
                "completed_both": summary["completed_both"],
            }
        )
        _save_ledger(ledger_path, ledger)
        (output_dir / "stage_b_pilot_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Điểm vào CLI điều phối Stage A và Stage B Pilot."""
    parser = argparse.ArgumentParser(
        description="HOSTRA AI P06-E01-T09 Gemini Free Tier Stage A & Stage B Runner."
    )
    parser.add_argument(
        "--stage",
        required=True,
        choices=["smoke", "pilot"],
        help="Giai đoạn thực thi: 'smoke' (<= 3 requests) hoặc 'pilot' (<= 25 requests).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_MODEL_CONFIG_PATH,
        help="Đường dẫn YAML model Gemini Free Tier.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_PILOT_OUTPUT_DIR,
        help="Thư mục lưu sổ cái ngân sách, kết quả và artifacts pilot.",
    )
    args = parser.parse_args(argv)

    if args.stage == "smoke":
        return _run_stage_a_smoke(args.output_dir.resolve(), args.config.resolve())
    return _run_stage_b_pilot(args.output_dir.resolve(), args.config.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
