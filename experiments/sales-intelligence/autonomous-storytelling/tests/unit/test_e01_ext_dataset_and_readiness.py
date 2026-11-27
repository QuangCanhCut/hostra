"""Kiểm thử tính hợp lệ của bộ dữ liệu `e01_ext_v1` và mức sẵn sàng thực nghiệm `E01-T09` (100% ngoại tuyến)."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeVar

import pytest
import yaml
from pydantic import BaseModel

from p06.adapters.p05_knowledge_adapter import P05KnowledgeAdapter
from p06.evaluation import GateStatus
from p06.providers.base import (
    GenerationRequest,
    GenerationResult,
    LLMProvider,
    ProviderTelemetry,
    ProviderTier,
    TokenUsageSource,
)
from p06.runner import (
    ExperimentMethod,
    RunTerminationReason,
    load_e01_story_plan,
    load_experiment_run_config,
    run_e01_sweep,
    run_experiment,
)
from p06.schemas.story import StoryPlan

_MODULE_ROOT = Path(__file__).resolve().parents[2]
_DATA_DIR = _MODULE_ROOT / "data"
_T = TypeVar("_T", bound=BaseModel)


@pytest.fixture
def tmp_path() -> Iterator[Path]:
    """Cấp thư mục tạm cô lập trong `.pytest_cache` và dọn sạch sau mỗi test."""
    base_dir = _MODULE_ROOT / ".pytest_cache" / f"ext_tmp_{uuid.uuid4().hex[:10]}"
    base_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield base_dir
    finally:
        shutil.rmtree(base_dir, ignore_errors=True)


def _load_cli_module() -> Any:
    cli_path = _MODULE_ROOT / "experiments" / "p06_e01_no_comments" / "run_e01.py"
    spec = importlib.util.spec_from_file_location("p06_run_e01_ext_cli", cli_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["p06_run_e01_ext_cli"] = mod
    spec.loader.exec_module(mod)
    return mod


class _FakePricedGeminiProvider(LLMProvider):
    """Provider giả tầng Gemini (chạy offline) để kiểm thử ngắt ngân sách USD."""

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_id(self) -> str:
        return "gemini-2.5-flash-lite"

    @property
    def tier(self) -> ProviderTier:
        return ProviderTier.FORMAL_EXPERIMENT

    def generate_structured(
        self,
        request: GenerationRequest,
        output_schema: type[_T],
    ) -> GenerationResult[_T]:
        payload = {
            "text": "Mật ong hoa cà phê Đắk Lắk nguyên chất 500ml giá 159.000 đồng.",
            "cited_evidence_ids": ["ev-e01-honey-origin"],
            "role": "PRODUCT_STORY",
            "stated_price_vnd": 159000,
            "mentions_ocop": False,
            "semantic_breakpoint": True,
            "breakpoint_type": "TOPIC_END",
            "rationale": "Kiểm thử ngân sách ngoại tuyến.",
        }
        if "covered_claim_ids" in output_schema.model_fields:
            payload["covered_claim_ids"] = []
        parsed = output_schema.model_validate(payload)
        telemetry = ProviderTelemetry(
            provider_name="gemini",
            model_id="gemini-2.5-flash-lite",
            tier=ProviderTier.FORMAL_EXPERIMENT,
            latency_ms=10.0,
            is_simulated_metric=False,
            input_tokens=500,
            output_tokens=400,
            thinking_tokens=100,
            token_usage_source=TokenUsageSource.MEASURED,
            finish_reason="STOP",
            raw_response_valid=True,
        )
        return GenerationResult(parsed_output=parsed, raw_text=json.dumps(payload), telemetry=telemetry)


def test_e01_ext_v1_dataset_validates_with_p05_store_and_story_plans() -> None:
    """Kiểm định e01_ext_v1 tương thích P05 store (>= 10 evidence/SKU) và đủ 5 StoryPlan."""
    seed_path = _DATA_DIR / "products" / "e01_ext_v1_verified_skus.json"
    plans_path = _DATA_DIR / "story_plans" / "e01_ext_v1_story_plans.json"
    goals_path = _DATA_DIR / "merchant_goals" / "e01_ext_v1_goals.json"

    adapter = P05KnowledgeAdapter.from_seed_file(seed_path)
    total_chunks = 0
    at_now = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
    for sku_id in ("SKU-HONEY-01", "SKU-TEA-02", "SKU-MACADAMIA-03"):
        view = adapter.get_sku_evidence("tenant-p06-poc-01", sku_id, at_time=at_now)
        assert view.is_eligible is True
        assert len(view.approved_chunks) >= 10
        total_chunks += len(view.approved_chunks)
    assert total_chunks == 30

    raw_plans = json.loads(plans_path.read_text(encoding="utf-8"))
    raw_goals = json.loads(goals_path.read_text(encoding="utf-8"))
    expected_topics = {
        "product_education_10m_ext": 18,
        "brand_storytelling_10m_ext": 18,
        "sales_presentation_30m_ext": 24,
        "pilot_short_3sku_ext": 6,
        "window_sensitivity_stress_24t": 24,
    }
    assert set(raw_plans["plans"].keys()) == set(expected_topics.keys())
    assert set(raw_goals["goals"].keys()) == {
        "goal_e01_ext_product_education",
        "goal_e01_ext_brand_storytelling",
        "goal_e01_ext_sales_presentation",
        "goal_e01_ext_pilot_short",
        "goal_e01_ext_window_stress",
    }
    for sc_name, count in expected_topics.items():
        plan = StoryPlan.model_validate(raw_plans["plans"][sc_name])
        assert plan.is_mvp_live_eligible() is True
        actual_topics = sum(len(arc.topics) for arc in plan.arcs)
        assert actual_topics == count
        loaded, _, _ = load_e01_story_plan(sc_name, story_plans_path=plans_path)
        assert loaded.plan_id == plan.plan_id


def test_e01_ext_v1_min_chunks_per_topic_2_sweep_and_stress_scenario(tmp_path: Path) -> None:
    """Chạy quét offline e01_ext_v1 với min_chunks_per_topic=2 (36 lượt) và stress 24 lượt."""
    sweep_res = run_e01_sweep(
        scenarios=("product_education_10m_ext",),
        dataset_profile="e01_ext_v1",
        min_chunks_per_topic=2,
        history_windows=(5, 10, 20),
        output_dir=tmp_path / "sweep_36t",
    )
    assert len(sweep_res.run_results) == 5
    assert sweep_res.comparison_report is not None
    assert sweep_res.comparison_report.compatible is True
    for run in sweep_res.run_results:
        assert run.termination_reason == RunTerminationReason.EARLY_COMPLETION
        assert len(run.evidence.transcript) >= 36
        assert run.manifest["min_chunks_per_topic"] == 2
        assert run.report is not None
        assert run.report.structural_hard_gates_status == GateStatus.PASS
        assert run.report.overall_gate_status == GateStatus.NOT_EVALUATED

    stress_res = run_e01_sweep(
        scenarios=("window_sensitivity_stress_24t",),
        methods=(ExperimentMethod.LANGGRAPH,),
        dataset_profile="e01_ext_v1",
        min_chunks_per_topic=1,
        history_windows=(5, 10, 20),
        output_dir=tmp_path / "stress_24t",
    )
    assert len(stress_res.run_results) == 3
    assert stress_res.comparison_report is not None
    assert stress_res.comparison_report.compatible is True
    assert all(len(r.evidence.transcript) == 24 for r in stress_res.run_results)


def test_budget_limit_guardrails_trigger_budget_limit_reached(tmp_path: Path) -> None:
    """Kiểm định cả max_llm_calls và max_estimated_cost_usd dừng phiên đúng chuẩn BUDGET_LIMIT_REACHED."""
    cfg_calls = load_experiment_run_config(
        scenario="pilot_short_3sku_ext",
        dataset_profile="e01_ext_v1",
        method=ExperimentMethod.LANGGRAPH,
        history_window=5,
        max_llm_calls=3,
        output_dir=tmp_path / "cap_calls",
    )
    res_calls = run_experiment(cfg_calls)
    assert res_calls.termination_reason == RunTerminationReason.BUDGET_LIMIT_REACHED
    assert len(res_calls.evidence.provider_calls) <= 5

    # Kiểm thử max_estimated_cost_usd bằng YAML có pricing + provider giả lập offline
    priced_yaml = tmp_path / "gemini_priced.yaml"
    priced_yaml.write_text(
        yaml.safe_dump(
            {
                "provider": "gemini",
                "run_tier": "formal_experiment",
                "model_id": "gemini-2.5-flash-lite",
                "pricing": {"input_per_1m_usd": 10.0, "output_per_1m_usd": 100.0},
            }
        ),
        encoding="utf-8",
    )
    cfg_cost = load_experiment_run_config(
        scenario="pilot_short_3sku_ext",
        dataset_profile="e01_ext_v1",
        method=ExperimentMethod.LANGGRAPH,
        provider="gemini",
        model_config_path=priced_yaml,
        history_window=5,
        max_estimated_cost_usd=0.05,
        allow_live_provider=True,
        output_dir=tmp_path / "cap_cost",
    )
    res_cost = run_experiment(cfg_cost, custom_llm_provider=_FakePricedGeminiProvider())
    # Mỗi call: 500/1M*10 + (400+100)/1M*100 = 0.005 + 0.05 = 0.055 >= 0.05 -> dừng sau call đầu tiên!
    assert res_cost.termination_reason == RunTerminationReason.BUDGET_LIMIT_REACHED
    assert len(res_cost.evidence.provider_calls) == 1


def test_cli_allow_live_flag_and_ext_profile_support(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI mặc định vẫn chặn live provider, đồng thời hỗ trợ --dataset-profile e01_ext_v1 với mock."""
    cli = _load_cli_module()
    with pytest.raises(SystemExit):
        cli.main(["--provider", "ollama", "--output-dir", str(tmp_path)])
    with pytest.raises(SystemExit):
        cli.main(["--provider", "gemini", "--output-dir", str(tmp_path)])

    exit_code = cli.main(
        [
            "--provider",
            "mock",
            "--dataset-profile",
            "e01_ext_v1",
            "--scenario",
            "pilot_short_3sku_ext",
            "--method",
            "langgraph_structured_story",
            "--history-window",
            "5",
            "--output-dir",
            str(tmp_path / "cli_ext"),
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["dataset_profile"] == "e01_ext_v1"
    assert payload["termination_reason"] == "EARLY_COMPLETION"
    assert payload["transcript_turns"] == 6
