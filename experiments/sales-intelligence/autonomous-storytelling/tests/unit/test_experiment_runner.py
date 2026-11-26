"""Bộ kiểm thử đơn vị cho `p06.runner` và CLI `run_e01.py` (`E01-T08`).

1. File này giải quyết vấn đề gì?
   Xác minh toàn diện logic cấu hình, rào chắn ngoại tuyến (`Offline Guard`), sinh fixture
   tách schema, thu thập bằng chứng trung thực (`I-06`, không bịa `0` cho `UNAVAILABLE`),
   lưu 10 tệp artifact bất biến không ghi đè, các điều kiện dừng phiên và sweep đối chứng.
2. Trách nhiệm chính của module là gì?
   Kiểm thử cô lập `config.py`, `mock_fixtures.py`, `evidence_collector.py`, `manifest.py`,
   `session_runner.py`, `sweep.py` và `experiments/p06_e01_no_comments/run_e01.py`.
3. Module này liên kết với các thành phần nào?
   Nhập các API công khai từ `p06.runner`, DTO từ `p06.evaluation.models`, và CLI `run_e01.py`.
4. Input và output chính là gì?
   Input là cấu hình synthetic trong `configs/` và `data/` cùng `MockLLMProvider`;
   Output là xác nhận pass 100% các bất biến runner hoàn toàn ngoại tuyến.
5. Có những constraints hoặc invariants quan trọng nào?
   - Không bao giờ gọi Ollama hay Gemini API; mọi test chạy 100% với `MockLLMProvider`.
   - Dùng `tmp_path` cô lập thư mục ghi artifact giữa các test case.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from p06.adapters.p05_knowledge_adapter import P05KnowledgeAdapter
from p06.baselines.script_first import UpfrontChunkDraftLLMOutput
from p06.evaluation.models import (
    ComparisonReport,
    ComparisonRow,
    EvaluationReport,
    MetricStatus,
    RunEvidence,
)
from p06.planning.draft_dtos import ChunkDraftLLMOutput
from p06.providers.base import (
    GenerationRequest,
    GenerationResult,
    LLMProvider,
    ProviderConfigError,
    ProviderTelemetry,
    ProviderTier,
    TokenUsageSource,
)
from p06.providers.mock_provider import MockBehavior, MockLLMProvider, MockResponseStep
from p06.runner import (
    DEFAULT_E01_VERIFIED_SKUS_PATH,
    DEFAULT_MOCK_MODEL_CONFIG_PATH,
    DEFAULT_MODULE_ROOT,
    ExperimentMethod,
    ExperimentRunConfig,
    RunTerminationReason,
    build_e01_mock_provider,
    load_e01_story_plan,
    load_experiment_run_config,
    persist_run_artifacts,
    run_e01_sweep,
    run_experiment,
)
from p06.runner.config import sanitize_mapping_for_artifact
from p06.schemas.events import PlaybackOutcomeStatus

_EXPECTED_ARTIFACT_FILES: frozenset[str] = frozenset(
    {
        "manifest.json",
        "config.yaml",
        "story_plan.json",
        "transcript.jsonl",
        "playback_events.jsonl",
        "graph_trace.jsonl",
        "provider_calls.jsonl",
        "metrics.json",
        "token_usage.json",
        "errors.jsonl",
    }
)


@pytest.fixture
def tmp_path() -> Iterator[Path]:
    """Cấp thư mục tạm cô lập trong `.pytest_cache` (đã gitignore) và dọn sạch sau mỗi test."""
    base_dir = DEFAULT_MODULE_ROOT / ".pytest_cache" / f"runner_tmp_{uuid.uuid4().hex[:10]}"
    base_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield base_dir
    finally:
        shutil.rmtree(base_dir, ignore_errors=True)


def _dummy_evaluator(evidence: RunEvidence) -> EvaluationReport:
    """Bộ đánh giá giả lập nhẹ dùng để kiểm tra tích hợp runner độc lập với `evaluator.py`."""
    manifest = evidence.manifest
    return EvaluationReport(
        run_id=str(manifest["run_id"]),
        experiment_id=str(manifest["experiment_id"]),
        method=str(manifest["method"]),
        scenario=str(manifest["scenario"]),
        provider_tier=str(manifest["provider_tier"]),
        provider_name=str(manifest["provider_name"]),
        model_id=str(manifest["model_id"]),
        history_window=manifest.get("history_window"),
        termination_reason=str(manifest["termination_reason"]),
        hard_gates_passed=True,
        metric_provenance={"dummy": MetricStatus.COMPUTED.value},
    )


def _dummy_comparator(run_dirs: list[Path] | tuple[Path, ...]) -> ComparisonReport:
    """Bộ so sánh giả lập nhẹ tạo `ComparisonReport` từ `manifest.json` trên đĩa."""
    rows: list[ComparisonRow] = []
    tiers: list[str] = []
    for run_dir in run_dirs:
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        tier = str(manifest["provider_tier"])
        if tier not in tiers:
            tiers.append(tier)
        rows.append(
            ComparisonRow(
                run_id=str(manifest["run_id"]),
                method=str(manifest["method"]),
                scenario=str(manifest["scenario"]),
                provider_tier=tier,
                provider_name=str(manifest["provider_name"]),
                model_id=str(manifest["model_id"]),
                history_window=manifest.get("history_window"),
                termination_reason=str(manifest["termination_reason"]),
                hard_gates_passed=True,
            )
        )
    return ComparisonReport(
        compatible=True,
        grouped_tiers=tuple(tiers),
        rows=tuple(rows),
    )


def _load_cli_module() -> Any:
    """Nạp động module CLI `experiments/p06_e01_no_comments/run_e01.py` để kiểm thử."""
    cli_path = DEFAULT_MODULE_ROOT / "experiments" / "p06_e01_no_comments" / "run_e01.py"
    spec = importlib.util.spec_from_file_location("p06_e01_run_cli", cli_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["p06_e01_run_cli"] = module
    spec.loader.exec_module(module)
    return module


class _UnavailableTokenMockProvider(LLMProvider):
    """Provider giả lập trả về văn bản hợp lệ nhưng gắn `token_usage_source=UNAVAILABLE`."""

    def __init__(self, inner: MockLLMProvider) -> None:
        self._inner = inner

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_id(self) -> str:
        return "mock-unavailable-tokens"

    @property
    def tier(self) -> ProviderTier:
        return ProviderTier.UNIT_TEST

    def generate_structured(self, request: GenerationRequest, output_schema: type[Any]) -> GenerationResult[Any]:
        res = self._inner.generate_structured(request, output_schema)
        tel = ProviderTelemetry(
            provider_name="mock",
            model_id=self.model_id,
            tier=ProviderTier.UNIT_TEST,
            latency_ms=res.telemetry.latency_ms,
            is_simulated_metric=True,
            input_tokens=None,
            output_tokens=None,
            token_usage_source=TokenUsageSource.UNAVAILABLE,
            finish_reason=res.telemetry.finish_reason,
            raw_response_valid=res.telemetry.raw_response_valid,
            sampling_params=res.telemetry.sampling_params,
            prompt_version=res.telemetry.prompt_version,
        )
        return GenerationResult(
            parsed_output=res.parsed_output,
            raw_text=res.raw_text,
            telemetry=tel,
        )


class TestRunnerConfigAndOfflineGuard:
    """Kiểm định nạp cấu hình, ràng buộc `history_window` và Offline Guard."""

    def test_load_config_validates_history_window_per_method(self, tmp_path: Path) -> None:
        lg_cfg = load_experiment_run_config(
            scenario="sales_presentation_30m",
            method=ExperimentMethod.LANGGRAPH,
            history_window=20,
            output_dir=tmp_path,
        )
        assert lg_cfg.history_window == 20
        assert lg_cfg.target_duration_sec == 1800.0

        det_cfg = load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.SCRIPT_FIRST_DETERMINISTIC,
            output_dir=tmp_path,
        )
        assert det_cfg.history_window is None
        assert det_cfg.target_duration_sec == 600.0

        with pytest.raises(ValueError, match="history_window"):
            load_experiment_run_config(
                scenario="product_education_10m",
                method=ExperimentMethod.SCRIPT_FIRST_UPFRONT_LLM,
                history_window=10,
                output_dir=tmp_path,
            )

        with pytest.raises(ValidationError):
            ExperimentRunConfig(
                scenario="product_education_10m",
                method=ExperimentMethod.LANGGRAPH,
                provider="mock",
                model_config_path=DEFAULT_MOCK_MODEL_CONFIG_PATH,
                history_window=None,
                output_dir=tmp_path,
            )

    def test_offline_guard_blocks_ollama_and_gemini(self, tmp_path: Path) -> None:
        with pytest.raises(ProviderConfigError, match="Offline Guard"):
            load_experiment_run_config(
                scenario="product_education_10m",
                method=ExperimentMethod.LANGGRAPH,
                provider="ollama",
                history_window=10,
                output_dir=tmp_path,
            )

        with pytest.raises(ProviderConfigError, match="Offline Guard"):
            load_experiment_run_config(
                scenario="product_education_10m",
                method=ExperimentMethod.LANGGRAPH,
                provider="gemini",
                history_window=10,
                output_dir=tmp_path,
            )

        gemini_yaml = DEFAULT_MODULE_ROOT / "configs" / "models" / "gemini_flash.yaml"
        with pytest.raises(ProviderConfigError, match="Offline Guard"):
            load_experiment_run_config(
                scenario="product_education_10m",
                method=ExperimentMethod.LANGGRAPH,
                provider="mock",
                model_config_path=gemini_yaml,
                history_window=10,
                output_dir=tmp_path,
            )

        # Kiểm tra cả khi tạo trực tiếp ExperimentRunConfig cũng bị chặn nếu không bật allow_live_provider.
        with pytest.raises(ValidationError):
            ExperimentRunConfig(
                scenario="product_education_10m",
                method=ExperimentMethod.LANGGRAPH,
                provider="gemini",
                model_config_path=gemini_yaml,
                history_window=10,
                output_dir=tmp_path,
                allow_live_provider=False,
            )


class TestMockFixturesSchemaIsolation:
    """Kiểm định tách schema giữa `ChunkDraftLLMOutput` và `UpfrontChunkDraftLLMOutput`."""

    def test_mock_provider_matches_exact_method_schema(self) -> None:
        plan, _, _ = load_e01_story_plan("product_education_10m")
        adapter = P05KnowledgeAdapter.from_seed_file(DEFAULT_E01_VERIFIED_SKUS_PATH)
        first_topic = plan.arcs[0].topics[0]

        upfront_provider = build_e01_mock_provider(plan, adapter, include_claim_ids=False)
        upfront_req = GenerationRequest(
            request_id="req-upfront-01",
            system_prompt="sys",
            user_prompt="user",
            metadata={"fixture_key": first_topic.topic_id},
        )
        upfront_res = upfront_provider.generate_structured(upfront_req, UpfrontChunkDraftLLMOutput)
        assert isinstance(upfront_res.parsed_output, UpfrontChunkDraftLLMOutput)
        assert len(upfront_res.parsed_output.text.split()) <= 16

        langgraph_provider = build_e01_mock_provider(plan, adapter, include_claim_ids=True)
        lg_req = GenerationRequest(
            request_id="req-lg-01",
            system_prompt="sys",
            user_prompt="user",
            metadata={"fixture_key": first_topic.topic_id},
        )
        lg_res = langgraph_provider.generate_structured(lg_req, ChunkDraftLLMOutput)
        assert isinstance(lg_res.parsed_output, ChunkDraftLLMOutput)
        assert lg_res.parsed_output.covered_claim_ids == list(first_topic.allowed_claim_ids)


class TestSessionRunnerManifestAndArtifacts:
    """Kiểm định chạy đầy đủ 3 SKU, manifest không lộ bí mật, và lưu 10 tệp bất biến."""

    @pytest.mark.parametrize(
        "method",
        [
            ExperimentMethod.SCRIPT_FIRST_DETERMINISTIC,
            ExperimentMethod.SCRIPT_FIRST_UPFRONT_LLM,
            ExperimentMethod.LANGGRAPH,
        ],
    )
    def test_end_to_end_3sku_run_persists_all_10_artifacts_without_secrets(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        method: ExperimentMethod,
    ) -> None:
        secret_sentinel = "secret-gemini-value-should-never-appear-in-artifacts"
        monkeypatch.setenv("GEMINI_API_KEY", secret_sentinel)

        cfg = load_experiment_run_config(
            scenario="product_education_10m",
            method=method,
            history_window=10 if method == ExperimentMethod.LANGGRAPH else None,
            output_dir=tmp_path,
        )
        res = run_experiment(cfg, evaluator=_dummy_evaluator)

        assert res.termination_reason == RunTerminationReason.EARLY_COMPLETION
        assert res.run_dir.is_dir()
        actual_files = {p.name for p in res.run_dir.iterdir() if p.is_file()}
        assert actual_files == _EXPECTED_ARTIFACT_FILES

        # Kiểm tra không có bất kỳ bí mật nào trong manifest.json hoặc config.yaml.
        manifest_text = (res.run_dir / "manifest.json").read_text(encoding="utf-8")
        config_text = (res.run_dir / "config.yaml").read_text(encoding="utf-8")
        assert secret_sentinel not in manifest_text
        assert secret_sentinel not in config_text

        manifest = json.loads(manifest_text)
        required_keys = {
            "run_id",
            "experiment_id",
            "method",
            "scenario",
            "git_commit",
            "git_dirty",
            "python_version",
            "package_versions",
            "cpu_model",
            "ram_gb",
            "dataset_version",
            "dataset_sha256",
            "is_synthetic",
            "story_plan_id",
            "story_plan_revision",
            "story_plan_sha256",
            "prompt_versions",
            "prompt_hashes",
            "provider_name",
            "provider_tier",
            "provider_config",
            "model_id",
            "quantization",
            "context_window",
            "sampling_params",
            "seed",
            "history_window",
            "repetition_config",
            "rewrite_budget",
            "max_chunk_duration_sec",
            "simulator_assumptions",
            "contract_version",
            "run_status",
            "started_at_utc",
            "finished_at_utc",
            "termination_reason",
            "metric_provenance",
        }
        assert required_keys.issubset(manifest.keys())
        assert manifest["contract_version"] == "p06-mock-v0.1"
        assert manifest["is_synthetic"] is True

        # Đã chạy hết cả 3 SKU trong kế hoạch.
        skus_spoken = {entry.sku_id for entry in res.evidence.transcript}
        assert skus_spoken == {"SKU-HONEY-01", "SKU-TEA-02", "SKU-MACADAMIA-03"}
        assert len(res.evidence.transcript) == 6

        token_usage = json.loads((res.run_dir / "token_usage.json").read_text(encoding="utf-8"))
        if method == ExperimentMethod.SCRIPT_FIRST_DETERMINISTIC:
            assert token_usage["total_model_calls"] == 0
            assert token_usage["token_usage_source"] == "UNAVAILABLE"
            assert token_usage["input_tokens"] is None
            assert token_usage["output_tokens"] is None
            assert token_usage["total_tokens"] is None
        else:
            assert token_usage["total_model_calls"] == 6
            assert token_usage["token_usage_source"] == "SIMULATED"
            assert token_usage["input_tokens"] > 0

        # Cấm ghi đè run_dir đã tồn tại.
        with pytest.raises(FileExistsError):
            persist_run_artifacts(
                output_dir=tmp_path,
                run_id=res.run_id,
                manifest=res.manifest,
                config=cfg,
                model_yaml=yaml.safe_load(DEFAULT_MOCK_MODEL_CONFIG_PATH.read_text(encoding="utf-8")),
                evidence=res.evidence,
                report=res.report,
                token_usage_summary=token_usage,
            )

    def test_unavailable_tokens_preserve_none_never_fake_zero(self, tmp_path: Path) -> None:
        plan, _, _ = load_e01_story_plan("product_education_10m")
        adapter = P05KnowledgeAdapter.from_seed_file(DEFAULT_E01_VERIFIED_SKUS_PATH)
        inner = build_e01_mock_provider(plan, adapter, include_claim_ids=True)
        cfg = load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.LANGGRAPH,
            history_window=5,
            output_dir=tmp_path,
        )
        res = run_experiment(
            cfg,
            evaluator=_dummy_evaluator,
            custom_llm_provider=_UnavailableTokenMockProvider(inner),
        )
        token_usage = json.loads((res.run_dir / "token_usage.json").read_text(encoding="utf-8"))
        assert token_usage["total_model_calls"] == 6
        assert token_usage["token_usage_source"] == "UNAVAILABLE"
        assert token_usage["input_tokens"] is None
        assert token_usage["output_tokens"] is None
        assert token_usage["total_tokens"] is None
        assert token_usage["wasted_tokens"] is None

    def test_failed_playback_ack_excluded_from_transcript_and_wasted_rewrite_tracked(
        self,
        tmp_path: Path,
    ) -> None:
        plan, _, _ = load_e01_story_plan("product_education_10m")
        adapter = P05KnowledgeAdapter.from_seed_file(DEFAULT_E01_VERIFIED_SKUS_PATH)
        evidence_honey = adapter.get_sku_evidence(plan.tenant_id, "SKU-HONEY-01")
        # Lượt 0 gặp 1 bước INVALID_SCHEMA rồi thành công ở :r1 -> lượt gọi đầu tiên phải là is_wasted=True.
        first_topic = plan.arcs[0].topics[0]
        base_mock = build_e01_mock_provider(plan, adapter, include_claim_ids=True)
        # Chèn bước lỗi JSON vỡ cú pháp cho lượt đầu của topic đầu tiên.
        base_mock._keyed_queues[first_topic.topic_id].appendleft(  # noqa: SLF001
            MockResponseStep(behavior=MockBehavior.MALFORMED_JSON)
        )
        assert evidence_honey.is_eligible

        cfg = load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.LANGGRAPH,
            history_window=10,
            output_dir=tmp_path,
        )
        # Ép ACK của lượt 0 bị FAILED -> lượt 0 không được vào transcript và chủ đề 0 chạy lại ở lượt 1.
        res = run_experiment(
            cfg,
            evaluator=_dummy_evaluator,
            custom_llm_provider=base_mock,
            outcome_overrides={0: PlaybackOutcomeStatus.FAILED},
        )
        assert res.termination_reason == RunTerminationReason.EARLY_COMPLETION
        # Có 7 playback events (1 FAILED + 6 COMPLETED), nhưng transcript chỉ có đúng 6 COMPLETED!
        assert len(res.evidence.playback_events) == 7
        assert res.evidence.playback_events[0].outcome == "FAILED"
        assert res.evidence.playback_events[0].applied is False
        assert len(res.evidence.transcript) == 6
        assert all(entry.turn_id != res.evidence.playback_events[0].turn_id for entry in res.evidence.transcript)

        # Kiểm tra cuộc gọi lỗi đầu tiên bị đánh dấu is_wasted=True, cuộc gọi thắng sau đó is_wasted=False.
        wasted_calls = [c for c in res.evidence.provider_calls if c.is_wasted]
        winning_calls = [c for c in res.evidence.provider_calls if not c.is_wasted]
        assert len(wasted_calls) == 1
        assert wasted_calls[0].raw_response_valid is False
        assert len(winning_calls) == 7

    def test_fallback_does_not_advance_next_topic_id(self, tmp_path: Path) -> None:
        plan, _, _ = load_e01_story_plan("product_education_10m")
        adapter = P05KnowledgeAdapter.from_seed_file(DEFAULT_E01_VERIFIED_SKUS_PATH)
        first_topic = plan.arcs[0].topics[0]
        mock_provider = build_e01_mock_provider(plan, adapter, include_claim_ids=True)
        # Ép lượt 0 hỏng cả attempt 0 lẫn 2 lần rewrite -> rơi vào FALLBACK_PREAPPROVED.
        mock_provider._keyed_queues[first_topic.topic_id].appendleft(  # noqa: SLF001
            MockResponseStep(behavior=MockBehavior.MALFORMED_JSON)
        )
        mock_provider._keyed_queues[f"{first_topic.topic_id}:r1"].appendleft(  # noqa: SLF001
            MockResponseStep(behavior=MockBehavior.MALFORMED_JSON)
        )
        mock_provider._keyed_queues[f"{first_topic.topic_id}:r2"].appendleft(  # noqa: SLF001
            MockResponseStep(behavior=MockBehavior.MALFORMED_JSON)
        )

        cfg = load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.LANGGRAPH,
            history_window=10,
            max_rewrite_retries=2,
            output_dir=tmp_path,
        )
        res = run_experiment(cfg, evaluator=_dummy_evaluator, custom_llm_provider=mock_provider)
        assert res.termination_reason == RunTerminationReason.EARLY_COMPLETION
        # Lượt 0 là fallback, lượt 1 phải nói lại đúng topic_id đầu tiên vì fallback không được nhảy cóc topic.
        assert res.evidence.graph_traces[0].turn_outcome == "FALLBACK_PREAPPROVED"
        assert res.evidence.graph_traces[0].selected_topic_id == first_topic.topic_id
        assert res.evidence.graph_traces[1].turn_outcome == "VERIFIED_READY"
        assert res.evidence.graph_traces[1].selected_topic_id == first_topic.topic_id
        assert len(res.evidence.transcript) == 7

    def test_deterministic_reproducibility_by_seed(self, tmp_path: Path) -> None:
        cfg_a = load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.LANGGRAPH,
            history_window=10,
            seed=42,
            output_dir=tmp_path / "run_a",
        )
        cfg_b = load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.LANGGRAPH,
            history_window=10,
            seed=42,
            output_dir=tmp_path / "run_b",
        )
        res_a = run_experiment(cfg_a, evaluator=_dummy_evaluator)
        res_b = run_experiment(cfg_b, evaluator=_dummy_evaluator)
        assert [t.text for t in res_a.evidence.transcript] == [
            t.text for t in res_b.evidence.transcript
        ]
        assert [t.actual_duration_ms for t in res_a.evidence.transcript] == [
            t.actual_duration_ms for t in res_b.evidence.transcript
        ]
        assert res_a.evidence.simulated_elapsed_sec == res_b.evidence.simulated_elapsed_sec

    def test_sales_presentation_30m_completes_all_9_topics(self, tmp_path: Path) -> None:
        cfg = load_experiment_run_config(
            scenario="sales_presentation_30m",
            method=ExperimentMethod.LANGGRAPH,
            history_window=20,
            output_dir=tmp_path,
        )
        res = run_experiment(cfg, evaluator=_dummy_evaluator)
        assert res.termination_reason == RunTerminationReason.EARLY_COMPLETION
        assert len(res.evidence.transcript) == 9
        assert {t.sku_id for t in res.evidence.transcript} == {
            "SKU-HONEY-01",
            "SKU-TEA-02",
            "SKU-MACADAMIA-03",
        }


class TestTerminationGuards:
    """Kiểm định 4 cơ chế dừng bảo vệ của `session_runner.py`."""

    def test_time_budget_exhausted_guard(self, tmp_path: Path) -> None:
        cfg = load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.LANGGRAPH,
            history_window=10,
            target_duration_sec=5.0,
            output_dir=tmp_path,
        )
        res = run_experiment(cfg, evaluator=_dummy_evaluator)
        assert res.termination_reason == RunTerminationReason.TIME_BUDGET_EXHAUSTED
        assert res.evidence.simulated_elapsed_sec >= 5.0

    def test_max_turns_reached_guard(self, tmp_path: Path) -> None:
        cfg = load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.LANGGRAPH,
            history_window=10,
            max_turns=2,
            output_dir=tmp_path,
        )
        res = run_experiment(cfg, evaluator=_dummy_evaluator)
        assert res.termination_reason == RunTerminationReason.MAX_TURNS_REACHED
        assert len(res.evidence.graph_traces) == 2

    def test_max_consecutive_aborts_guard(self, tmp_path: Path) -> None:
        failing_provider = MockLLMProvider(
            response_sequence=[
                MockResponseStep(behavior=MockBehavior.TIMEOUT),
                MockResponseStep(behavior=MockBehavior.TIMEOUT),
                MockResponseStep(behavior=MockBehavior.TIMEOUT),
            ]
        )
        cfg = load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.LANGGRAPH,
            history_window=10,
            max_consecutive_aborts=2,
            output_dir=tmp_path,
        )
        res = run_experiment(
            cfg,
            evaluator=_dummy_evaluator,
            custom_llm_provider=failing_provider,
            fallback_candidates=(),
        )
        assert res.termination_reason == RunTerminationReason.MAX_CONSECUTIVE_ABORTS
        assert len(res.evidence.graph_traces) == 2
        assert len(res.evidence.transcript) == 0
        assert len(res.evidence.errors) >= 2

    def test_content_exhausted_when_script_first_playback_fails(self, tmp_path: Path) -> None:
        cfg = load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.SCRIPT_FIRST_DETERMINISTIC,
            output_dir=tmp_path,
        )
        res = run_experiment(
            cfg,
            evaluator=_dummy_evaluator,
            outcome_overrides={0: PlaybackOutcomeStatus.FAILED},
        )
        assert res.termination_reason == RunTerminationReason.CONTENT_EXHAUSTED
        assert len(res.evidence.transcript) == 5


class TestSweepAndCLISafeguard:
    """Kiểm định `run_e01_sweep` (không quét W trên script-first) và rào chắn CLI T08."""

    def test_sweep_single_scenario_produces_5_runs_and_comparison_files(self, tmp_path: Path) -> None:
        sweep_res = run_e01_sweep(
            scenarios=("product_education_10m",),
            history_windows=(5, 10, 20),
            output_dir=tmp_path,
            evaluator=_dummy_evaluator,
            comparator=_dummy_comparator,
        )
        # 1x deterministic + 1x upfront_llm + 3x langgraph (W=5, 10, 20) = 5 lượt chạy.
        assert len(sweep_res.run_results) == 5
        windows_by_method = [
            (res.manifest["method"], res.manifest["history_window"])
            for res in sweep_res.run_results
        ]
        assert windows_by_method == [
            ("script_first_deterministic", None),
            ("script_first_upfront_llm", None),
            ("langgraph_structured_story", 5),
            ("langgraph_structured_story", 10),
            ("langgraph_structured_story", 20),
        ]
        assert sweep_res.comparison_json_path is not None and sweep_res.comparison_json_path.is_file()
        assert sweep_res.comparison_csv_path is not None and sweep_res.comparison_csv_path.is_file()
        assert sweep_res.comparison_md_path is not None and sweep_res.comparison_md_path.is_file()

    def test_sweep_integrates_with_real_evaluation_and_blind_human_eval(
        self,
        tmp_path: Path,
    ) -> None:
        sweep_res = run_e01_sweep(
            scenarios=("product_education_10m",),
            history_windows=(5, 10, 20),
            output_dir=tmp_path,
            export_human_eval=True,
        )
        assert len(sweep_res.run_results) == 5
        assert all(res.report is not None for res in sweep_res.run_results)
        assert all(res.report.hard_gates_passed for res in sweep_res.run_results if res.report)
        assert sweep_res.comparison_report is not None
        assert sweep_res.comparison_report.compatible is True
        assert len(sweep_res.comparison_report.rows) == 5
        assert sweep_res.human_eval_dir is not None and sweep_res.human_eval_dir.is_dir()
        assert any(sweep_res.human_eval_dir.iterdir())

    def test_cli_blocks_live_providers_and_runs_mock_single_mode(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        cli_mod = _load_cli_module()

        with pytest.raises(SystemExit):
            cli_mod.main(["--provider", "ollama", "--output-dir", str(tmp_path)])

        with pytest.raises(SystemExit):
            cli_mod.main(["--provider", "gemini", "--output-dir", str(tmp_path)])

        gemini_cfg = DEFAULT_MODULE_ROOT / "configs" / "models" / "gemini_flash.yaml"
        with pytest.raises(SystemExit):
            cli_mod.main(
                ["--provider", "mock", "--config", str(gemini_cfg), "--output-dir", str(tmp_path)]
            )

        exit_code = cli_mod.main(
            [
                "--provider",
                "mock",
                "--method",
                "langgraph_structured_story",
                "--scenario",
                "product_education_10m",
                "--history-window",
                "10",
                "--output-dir",
                str(tmp_path),
            ]
        )
        assert exit_code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["mode"] == "single"
        assert out["termination_reason"] == "EARLY_COMPLETION"
        assert Path(out["run_dir"]).is_dir()


class TestPhase4ReviewRegressions:
    """Các kiểm thử hồi quy cho 8 phát hiện từ Independent Phase 4 Review (BUG-A..C, NEW-01..05)."""

    def test_artifact_redaction_preserves_token_provenance_and_redacts_secrets(self, tmp_path: Path) -> None:
        """Hồi quy BUG-A: giữ metric_provenance.token_usage và các bộ đếm token, nhưng vẫn che khóa bí mật."""
        payload = {
            "metric_provenance": {"token_usage": "SIMULATED", "provider_tier": "unit_test"},
            "input_tokens": 120,
            "output_tokens": 45,
            "total_tokens": 165,
            "wasted_tokens": 12,
            "max_output_tokens": 1024,
            "access_token": "sec-access-123",
            "auth_token": "sec-auth-456",
            "bearer": "Bearer secret-tok",
            "bearer_token": "bt-789",
            "api_key": "ak-111",
            "GEMINI_API_KEY": "gk-222",
            "client_secret": "cs-333",
            "db_password": "pw-444",
            "authorization": "Bearer hdr-555",
            "api_key_env": "GEMINI_API_KEY",
        }
        cleaned = sanitize_mapping_for_artifact(payload)
        assert cleaned["metric_provenance"]["token_usage"] == "SIMULATED"
        assert cleaned["input_tokens"] == 120
        assert cleaned["output_tokens"] == 45
        assert cleaned["total_tokens"] == 165
        assert cleaned["wasted_tokens"] == 12
        assert cleaned["max_output_tokens"] == 1024
        assert cleaned["api_key_env"] == "GEMINI_API_KEY"
        for secret_key in (
            "access_token",
            "auth_token",
            "bearer",
            "bearer_token",
            "api_key",
            "GEMINI_API_KEY",
            "client_secret",
            "db_password",
            "authorization",
        ):
            assert cleaned[secret_key] == "[REDACTED]"

        # Xác nhận manifest thật trên đĩa giữ nguyên metric_provenance.token_usage + virtual_clock_start_utc
        cfg = load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.SCRIPT_FIRST_UPFRONT_LLM,
            output_dir=tmp_path,
        )
        res = run_experiment(cfg)
        assert res.manifest["metric_provenance"]["token_usage"] == "SIMULATED"
        assert res.manifest["simulator_assumptions"]["virtual_clock_start_utc"] is not None

    def test_script_first_mid_sku_budget_guard_prevents_phantom_clock_advance(self, tmp_path: Path) -> None:
        """Hồi quy NEW-01: ScriptFirst dừng giữa SKU khi chạm target_duration_sec/max_turns, không trượt clock."""
        cfg = load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.SCRIPT_FIRST_DETERMINISTIC,
            target_duration_sec=5.0,
            output_dir=tmp_path,
        )
        res = run_experiment(cfg, evaluator=_dummy_evaluator)
        assert res.termination_reason == RunTerminationReason.TIME_BUDGET_EXHAUSTED
        assert len(res.evidence.transcript) == 1
        assert len(res.evidence.playback_events) == 1
        played_sec = (res.evidence.playback_events[0].actual_duration_ms or 0) / 1000.0
        assert res.evidence.simulated_elapsed_sec == pytest.approx(played_sec)

    def test_script_first_multi_sku_candidate_ids_unique(self, tmp_path: Path) -> None:
        """Hồi quy NEW-02: candidate_id của baseline gắn sku_id nên duy nhất qua cả 3 SKU."""
        cfg = load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.SCRIPT_FIRST_DETERMINISTIC,
            output_dir=tmp_path,
        )
        res = run_experiment(cfg, evaluator=_dummy_evaluator)
        cand_ids = [entry.candidate_id for entry in res.evidence.transcript]
        assert len(cand_ids) == 6
        assert len(set(cand_ids)) == 6
        assert any("SKU-HONEY-01" in cid for cid in cand_ids)
        assert any("SKU-TEA-02" in cid for cid in cand_ids)
        assert any("SKU-MACADAMIA-03" in cid for cid in cand_ids)

    def test_baseline_over_max_duration_telemetry_aligned_and_marked_wasted(self, tmp_path: Path) -> None:
        """Hồi quy NEW-03: lượt UPFRONT_LLM vượt max_chunk_duration_sec gắn đúng turn_id và is_wasted=True."""
        plan, _, _ = load_e01_story_plan("product_education_10m")
        adapter = P05KnowledgeAdapter.from_seed_file(DEFAULT_E01_VERIFIED_SKUS_PATH)
        first_topic = plan.arcs[0].topics[0]
        provider = build_e01_mock_provider(plan, adapter, include_claim_ids=False)
        # Lượt 0 vượt quá giới hạn 8.0s (~35 từ > 30 từ), kích hoạt OVER_MAX_DURATION_SEC
        too_long_text = " ".join(["mật", "ong", "hoa", "cà", "phê"] * 10)
        provider._keyed_queues[first_topic.topic_id][0] = MockResponseStep(  # noqa: SLF001
            behavior=MockBehavior.VALID_JSON,
            payload={
                "text": too_long_text,
                "cited_evidence_ids": ["ev-e01-honey-origin"],
                "role": "OPENING",
                "stated_price_vnd": None,
                "mentions_ocop": False,
                "semantic_breakpoint": True,
                "breakpoint_type": "TOPIC_END",
                "rationale": "Vượt độ dài để kiểm thử liên kết telemetry.",
            },
        )
        cfg = load_experiment_run_config(
            scenario="product_education_10m",
            method=ExperimentMethod.SCRIPT_FIRST_UPFRONT_LLM,
            max_chunk_duration_sec=8.0,
            output_dir=tmp_path,
        )
        res = run_experiment(cfg, evaluator=_dummy_evaluator, custom_llm_provider=provider)
        assert len(res.evidence.provider_calls) == 6
        first_call = res.evidence.provider_calls[0]
        second_call = res.evidence.provider_calls[1]
        assert first_call.is_wasted is True
        assert first_call.error_type == "OVER_MAX_DURATION_SEC"
        assert first_call.turn_id == res.evidence.graph_traces[0].turn_id
        assert second_call.is_wasted is False
        assert second_call.turn_id == res.evidence.graph_traces[1].turn_id

    def test_multi_scenario_sweep_emits_compatible_per_scenario_comparisons(self, tmp_path: Path) -> None:
        """Hồi quy NEW-04: Sweep đa kịch bản tạo thêm comparison_{scenario}.* tương thích nội bộ."""
        sweep_res = run_e01_sweep(
            scenarios=("product_education_10m", "brand_storytelling_10m"),
            methods=(ExperimentMethod.SCRIPT_FIRST_DETERMINISTIC, ExperimentMethod.LANGGRAPH),
            history_windows=(5,),
            output_dir=tmp_path,
        )
        assert sweep_res.comparison_report is not None
        assert sweep_res.comparison_report.compatible is False
        for sc in ("product_education_10m", "brand_storytelling_10m"):
            assert sc in sweep_res.per_scenario_comparison_paths
            sc_json = json.loads(
                sweep_res.per_scenario_comparison_paths[sc]["json"].read_text(encoding="utf-8")
            )
            assert sc_json["compatible"] is True
            assert len(sc_json["rows"]) == 2
