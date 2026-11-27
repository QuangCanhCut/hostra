"""Tiện ích phân tích, tổng hợp bảng và vẽ biểu đồ cho báo cáo cuối `P06-E01`.

Mô-đun này đọc trực tiếp toàn bộ hiện vật đã khóa từ thư mục `runs/P06-E01/`,
tách bạch rạch ròi giữa Tier 1 (`Mock`), Pilot v1/v2, Formal Benchmark (10 runs)
và kết quả `AI-assisted non-blind evaluation (ChatGPT — Rubric v0.1)`, không gọi
Gemini API và không làm thay đổi dữ liệu nguồn hay thư mục `human_eval/`.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import pathlib
from collections import Counter
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

AI_EVAL_PROVENANCE: str = "AI-assisted non-blind evaluation — ChatGPT — Rubric v0.1"

FONT_REGULAR_PATH = pathlib.Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_BOLD_PATH = pathlib.Path(r"C:\Windows\Fonts\segoeuib.ttf")

# Bảng màu chuẩn HOSTRA UI Redesign v0.4 (Navy + Amber + Slate + Semantic accents)
NAVY = "#0F172A"
NAVY_SOFT = "#1E293B"
AMBER = "#F5C430"
AMBER_DARK = "#B45309"
SOFT_YELLOW = "#FBE580"
SLATE_DARK = "#334155"
SLATE_MID = "#64748B"
COOL_GRAY = "#E2E8F0"
BG_LIGHT = "#F8FAFC"
WHITE = "#FFFFFF"
TEAL = "#0F766E"
TEAL_LIGHT = "#14B8A6"
BLUE = "#2563EB"
CRIMSON = "#DC2626"
ROSE = "#F43F5E"
ORANGE = "#EA580C"
INDIGO = "#4F46E5"
GRAY_HATCH = "#CBD5E1"


def find_p06_root(start: pathlib.Path | None = None) -> pathlib.Path:
    """Tìm thư mục gốc của module P06 (`autonomous-storytelling/`)."""
    candidates = []
    if start is not None:
        candidates.append(start.resolve())
    candidates.append(pathlib.Path(__file__).resolve().parent)
    candidates.append(pathlib.Path.cwd().resolve())

    for base in candidates:
        for cur in [base, *base.parents]:
            if (cur / "src" / "p06").is_dir() and (cur / "runs" / "P06-E01").is_dir():
                return cur
            sub = cur / "experiments" / "sales-intelligence" / "autonomous-storytelling"
            if (sub / "src" / "p06").is_dir() and (sub / "runs" / "P06-E01").is_dir():
                return sub
    raise FileNotFoundError("Không tìm thấy thư mục `experiments/sales-intelligence/autonomous-storytelling`.")


def _sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _opt_int(val: Any) -> Any:
    return int(val) if val is not None and not (isinstance(val, float) and math.isnan(val)) else pd.NA


def _opt_float(val: Any, ndigits: int = 4) -> float:
    return round(float(val), ndigits) if val is not None else math.nan


def _read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _read_csv_rows(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    fpath = FONT_BOLD_PATH if bold else FONT_REGULAR_PATH
    if fpath.is_file():
        return ImageFont.truetype(str(fpath), size=size)
    return ImageFont.load_default()


def _batch_metadata() -> list[dict[str, Any]]:
    """Đặc tả thứ tự và ngữ cảnh 4 batch formal benchmark của `P06-E01`."""
    return [
        {
            "batch_code": "1A",
            "batch_dir": "track1_product_edu_s42",
            "track": "Track 1 (Natural)",
            "scenario_label": "Product Education",
            "planned_lag": "N/A (m=1)",
            "yaml_config": "configs/experiments/p06_e01_formal_batch1a.yaml",
            "yaml_global_cap": 120,
            "operational_global_cap": 120,
        },
        {
            "batch_code": "1B",
            "batch_dir": "track1_brand_storytelling_s42",
            "track": "Track 1 (Natural)",
            "scenario_label": "Brand Storytelling",
            "planned_lag": "N/A (m=1)",
            "yaml_config": "configs/experiments/p06_e01_formal_batch1b.yaml",
            "yaml_global_cap": 60,
            "operational_global_cap": 60,
        },
        {
            "batch_code": "2A",
            "batch_dir": "track2a_small_window_lag6_s42",
            "track": "Track 2 (Window Stress)",
            "scenario_label": "Product Edu Stress (lag=6)",
            "planned_lag": 6,
            "yaml_config": "configs/experiments/p06_e01_formal_track2a_w5_w10.yaml",
            "yaml_global_cap": 240,
            "operational_global_cap": 240,
        },
        {
            "batch_code": "2B",
            "batch_dir": "track2b_large_window_lag12_s42",
            "track": "Track 2 (Window Stress)",
            "scenario_label": "Window Stress 12-Lag (lag=12)",
            "planned_lag": 12,
            "yaml_config": "configs/experiments/p06_e01_formal_track2b_w10_w20.yaml",
            "yaml_global_cap": 400,
            "operational_global_cap": 200,
        },
    ]


def _config_short_name(method: str, history_window: Any) -> str:
    if method == "script_first_upfront_llm":
        return "Script-first"
    return f"LangGraph W={int(history_window)}"


def load_pilot_and_mock_inventory(p06_root: pathlib.Path) -> pd.DataFrame:
    """Đọc tách biệt Pilot v1/v2 (Gemini live pre-formal) và các đợt chạy Mock ngoại tuyến."""
    runs_dir = p06_root / "runs" / "P06-E01"
    rows: list[dict[str, Any]] = []

    for pname, stage_desc in [
        ("gemini_3.5_flash_lite_pilot", "Pilot v1 (Smoke + Short Pilot 3-SKU, prompt v0.1)"),
        ("gemini_3.5_flash_lite_pilot_v2", "Pilot v2 (Revalidation Post-R01..R06, prompt v0.2)"),
    ]:
        pdir = runs_dir / pname
        if not pdir.is_dir():
            continue
        led = _read_json(pdir / "budget_ledger.json")
        st_a = _read_json(pdir / "stage_a_smoke_results.json")
        st_b = _read_json(pdir / "stage_b_pilot_summary.json")
        rows.append({
            "phase_dir": pname,
            "provider_tier": "pre_formal_pilot_gemini_live",
            "description": stage_desc,
            "model_id": led.get("model_id", "gemini-3.5-flash-lite"),
            "stage_a_requests": int(led.get("stage_a_requests", 0)),
            "stage_b_requests": int(led.get("stage_b_requests", 0)),
            "total_requests": int(led.get("total_requests", 0)),
            "max_budget": int(led.get("max_total_requests", 0)),
            "stage_a_all_passed": bool(st_a.get("all_passed", False)),
            "stage_b_runs": len(st_b.get("runs", {})),
            "cost_usd": 0.0,
            "included_in_317_formal": False,
        })

    for mdir_name, desc in [
        ("post_fix_sweep_product_education_10m", "Offline E01-T08 Sweep (MockLLMProvider)"),
        ("offline_ext_v1_dryrun", "Offline E01-T09 Readiness Dry-Run (MockLLMProvider)"),
    ]:
        mdir = runs_dir / mdir_name
        if mdir.is_dir():
            rows.append({
                "phase_dir": mdir_name,
                "provider_tier": "unit_test_mock",
                "description": desc,
                "model_id": "deterministic-mock-v0.1",
                "stage_a_requests": 0,
                "stage_b_requests": 0,
                "total_requests": 0,
                "max_budget": 0,
                "stage_a_all_passed": True,
                "stage_b_runs": len([d for d in mdir.iterdir() if d.is_dir()]),
                "cost_usd": 0.0,
                "included_in_317_formal": False,
            })

    return pd.DataFrame(rows)


def load_formal_runs_df(p06_root: pathlib.Path) -> pd.DataFrame:
    """Nạp toàn bộ 10 formal benchmark runs từ raw artifacts bất biến."""
    fb_dir = p06_root / "runs" / "P06-E01" / "formal_benchmark_v1"
    rows: list[dict[str, Any]] = []

    for meta in _batch_metadata():
        bdir = fb_dir / meta["batch_dir"]
        ledger = _read_json(bdir / "budget_ledger.json")
        batch_sum = _read_json(bdir / "batch_summary.json")

        for label, rinfo in batch_sum["runs"].items():
            run_dir = pathlib.Path(rinfo["run_dir"])
            if not run_dir.is_dir():
                run_dir = bdir / rinfo["run_id"]
            manifest = _read_json(run_dir / "manifest.json")
            metrics = _read_json(run_dir / "metrics.json")
            token_usage = _read_json(run_dir / "token_usage.json")
            story_plan = _read_json(run_dir / "story_plan.json")
            transcript = sorted(_read_jsonl(run_dir / "transcript.jsonl"), key=lambda x: x["turn_index"])
            calls = sorted(_read_jsonl(run_dir / "provider_calls.jsonl"), key=lambda x: x["call_index"])
            traces = sorted(_read_jsonl(run_dir / "graph_trace.jsonl"), key=lambda x: x["turn_index"])
            errors = _read_jsonl(run_dir / "errors.jsonl")

            cov = metrics["coverage"]
            rep = metrics["repetition"]
            saf = metrics["safety"]
            rel = metrics["reliability"]
            perf = metrics["performance"]

            planned_topics = [t for arc in story_plan["arcs"] for t in arc["topics"]]
            mandatory_topics = [t for t in planned_topics if t.get("is_mandatory")]
            counts_by_topic = cov["completed_topic_count"]["metadata"].get("played_chunk_counts_by_topic", {})
            min_chunks = int(manifest.get("min_chunks_per_topic", 1))
            completed_planned = sum(1 for t in planned_topics if int(counts_by_topic.get(t["topic_id"], 0)) >= min_chunks)
            completed_mandatory = sum(1 for t in mandatory_topics if int(counts_by_topic.get(t["topic_id"], 0)) >= min_chunks)

            failed_calls = [
                c for c in calls
                if (not c.get("succeeded", True)) or c.get("token_usage_source") != "MEASURED"
            ]
            err_503_turns = {
                e.get("turn_id")
                for e in errors
                if "503" in str(e.get("message", "")) or "UNAVAILABLE" in str(e.get("message", ""))
            }
            err_429_turns = {
                e.get("turn_id")
                for e in errors
                if "429" in str(e.get("message", "")) or "RESOURCE_EXHAUSTED" in str(e.get("message", ""))
            }
            http_503_calls = min(len(err_503_turns), len(failed_calls)) if failed_calls else len(err_503_turns)
            http_429_calls = len(err_429_turns)

            measured_calls = [c for c in calls if c.get("token_usage_source") == "MEASURED"]
            partial_in = sum(int(c.get("input_tokens") or 0) for c in measured_calls)
            partial_out = sum(int(c.get("output_tokens") or 0) for c in measured_calls)
            wasted_calls_list = [c for c in calls if c.get("is_wasted")]
            partial_wasted_tok = sum(
                int(c.get("input_tokens") or 0) + int(c.get("output_tokens") or 0) + int(c.get("thinking_tokens") or 0)
                for c in wasted_calls_list
                if c.get("token_usage_source") == "MEASURED"
            )

            agg_src = str(token_usage.get("token_usage_source", "UNAVAILABLE"))
            agg_in = float(token_usage["input_tokens"]) if (agg_src == "MEASURED" and token_usage.get("input_tokens") is not None) else math.nan
            agg_out = float(token_usage["output_tokens"]) if (agg_src == "MEASURED" and token_usage.get("output_tokens") is not None) else math.nan
            agg_wasted_tok = float(token_usage["wasted_tokens"]) if (agg_src == "MEASURED" and token_usage.get("wasted_tokens") is not None) else math.nan

            rep_cats: Counter[str] = Counter()
            rep_acts: Counter[str] = Counter()
            for tr in traces:
                if tr.get("should_terminate"):
                    continue
                for rc in tr.get("repetition_checks", []):
                    rep_cats[str(rc.get("category"))] += 1
                    rep_acts[str(rc.get("recommended_action"))] += 1

            hw = manifest.get("history_window")
            cfg_name = _config_short_name(str(manifest["method"]), hw)
            full_label = f"{meta['batch_code']} {cfg_name}"

            rows.append({
                "batch_code": meta["batch_code"],
                "batch_dir": meta["batch_dir"],
                "track": meta["track"],
                "scenario": str(manifest["scenario"]),
                "scenario_label": meta["scenario_label"],
                "dataset_profile": str(manifest["dataset_profile"]),
                "min_chunks_per_topic": min_chunks,
                "planned_lag": meta["planned_lag"],
                "run_label": label,
                "config_name": cfg_name,
                "full_label": full_label,
                "run_id": str(manifest["run_id"]),
                "method": str(manifest["method"]),
                "history_window": int(hw) if hw is not None else None,
                "model_id": str(manifest["model_id"]),
                "seed": int(manifest["seed"]),
                "started_at_utc": manifest.get("started_at_utc"),
                "finished_at_utc": manifest.get("finished_at_utc"),
                "termination_reason": str(manifest["termination_reason"]),
                "yaml_global_cap": meta["yaml_global_cap"],
                "operational_global_cap": int(ledger["global_max_requests"]),
                "run_cap": int(rinfo["run_cap"]),
                "requests_attempted": int(rinfo["requests_attempted"]),
                "measured_calls": len(measured_calls),
                "failed_calls": len(failed_calls),
                "http_503_calls": http_503_calls,
                "http_429_calls": http_429_calls,
                "wasted_calls": len(wasted_calls_list),
                "wasted_calls_pct": round(100.0 * len(wasted_calls_list) / len(calls), 2) if calls else 0.0,
                "played_turns": len(transcript),
                "content_traces": sum(1 for tr in traces if not tr.get("should_terminate")),
                "planned_topics_count": len(planned_topics),
                "mandatory_topics_count": len(mandatory_topics),
                "completed_planned_topics": completed_planned,
                "completed_mandatory_topics": completed_mandatory,
                "planned_topic_coverage": round(completed_planned / len(planned_topics), 4) if planned_topics else 0.0,
                "mandatory_topic_coverage": round(float(cov["mandatory_topic_coverage"]["value"]), 4),
                "claim_cov_num": int(cov["declared_verified_claim_coverage"]["numerator"]),
                "claim_cov_den": int(cov["declared_verified_claim_coverage"]["denominator"]),
                "declared_verified_claim_coverage": round(float(cov["declared_verified_claim_coverage"]["value"]), 4),
                "simulated_played_duration_sec": round(float(cov["simulated_played_duration_sec"]["value"]), 3),
                "target_duration_sec": 600.0,
                "duration_fulfillment": round(float(cov["duration_fulfillment"]["value"]), 4),
                "exact_chunk_replay_count": _opt_int(rep["exact_chunk_replay_count"]["value"]),
                "exact_normalized_text_replay_count": _opt_int(rep["exact_normalized_text_replay_count"]["value"]),
                "outside_window_exact_text_replay_count": _opt_int(rep["outside_window_exact_text_replay_count"]["value"]),
                "lexical_repetition_rate": _opt_float(rep["lexical_repetition_rate"]["value"], 4),
                "max_prior_word_jaccard_mean": _opt_float(rep["max_prior_word_jaccard_mean"]["value"], 4),
                "max_prior_ngram3_jaccard_mean": _opt_float(rep["max_prior_ngram3_jaccard_mean"]["value"], 4),
                "win_ngram3_w5": _opt_float(rep["windowed_ngram3_jaccard_mean_w5"]["value"], 4),
                "win_ngram3_w10": _opt_float(rep["windowed_ngram3_jaccard_mean_w10"]["value"], 4),
                "win_ngram3_w20": _opt_float(rep["windowed_ngram3_jaccard_mean_w20"]["value"], 4),
                "distinct_1": _opt_float(rep["distinct_1"]["value"], 4),
                "distinct_2": _opt_float(rep["distinct_2"]["value"], 4),
                "distinct_3": _opt_float(rep["distinct_3"]["value"], 4),
                "claim_overlap_rate": float(rep["claim_overlap_rate"]["value"]) if rep["claim_overlap_rate"]["value"] is not None else math.nan,
                "p05_rejection_count": int(saf["p05_rejection_count"]["value"]),
                "p05_rejection_rate": round(float(saf["p05_rejection_rate"]["value"]), 4),
                "invalid_candidate_playback_count": int(saf["invalid_candidate_playback_count"]["value"]),
                "duplicate_completed_chunk_replay_count": int(saf["duplicate_completed_chunk_replay_count"]["value"]),
                "retry_budget_violations": int(rel["retry_budget_violations"]["value"]),
                "rewrite_count": int(rel["rewrite_count"]["value"]),
                "rewrite_rate": round(float(rel["rewrite_rate"]["value"]), 4),
                "fallback_count": int(rel["fallback_count"]["value"]),
                "fallback_rate": round(float(rel["fallback_rate"]["value"]), 4),
                "safe_abort_count": int(rel["safe_abort_count"]["value"]),
                "safe_abort_rate": round(float(rel["safe_abort_rate"]["value"]), 4),
                "detector_none": rep_cats.get("NONE", 0),
                "detector_lexical_dup": rep_cats.get("LEXICAL_DUPLICATION", 0),
                "detector_repeated_facts": rep_cats.get("REPEATED_FACTS", 0),
                "detector_exact_replay": rep_cats.get("EXACT_REPLAY", 0),
                "detector_legit_cont": rep_cats.get("LEGITIMATE_CONTINUATION", 0),
                "provider_latency_p50_ms": round(float(perf["provider_latency_p50_ms"]["value"]), 1),
                "provider_latency_p95_ms": round(float(perf["provider_latency_p95_ms"]["value"]), 1),
                "token_usage_source": agg_src,
                "input_tokens": agg_in,
                "output_tokens": agg_out,
                "wasted_tokens": agg_wasted_tok,
                "partial_measured_input_tokens": partial_in,
                "partial_measured_output_tokens": partial_out,
                "partial_measured_wasted_tokens": partial_wasted_tok,
                "cost_usd": 0.0,
                "structural_hard_gates_status": str(metrics["structural_hard_gates_status"]),
                "factual_safety_gate_status": str(metrics["factual_safety_gate_status"]),
                "overall_gate_status": str(metrics["overall_gate_status"]),
            })

    return pd.DataFrame(rows)


def load_ai_assisted_eval_dfs(p06_root: pathlib.Path, runs_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Đọc toàn bộ AI-assisted evaluation CSV đã import (giữ nguyên nhãn, tách Human Gold)."""
    fb_dir = p06_root / "runs" / "P06-E01" / "formal_benchmark_v1"
    run_meta_by_id = runs_df.set_index("run_id").to_dict(orient="index")

    specs = [
        ("1A", "track1_product_edu_s42", "batch1a_ai_assisted_quality.csv", "batch1a_ai_assisted_factual_semantic.csv", None, "topic_m1"),
        ("1B", "track1_brand_storytelling_s42", "batch1b_ai_assisted_quality.csv", "batch1b_ai_assisted_factual_semantic.csv", None, "topic_m1"),
        ("2A", "track2a_small_window_lag6_s42", "track2a_ai_assisted_quality.csv", "track2a_ai_assisted_factual_semantic.csv", "track2a_ai_assisted_repetition.csv", "required_slot_m2"),
        ("2B", "track2b_large_window_lag12_s42", "track2b_ai_assisted_quality.csv", "track2b_ai_assisted_factual_semantic.csv", "track2b_ai_assisted_repetition.csv", "required_slot_m2"),
    ]

    qual_rows: list[dict[str, Any]] = []
    sem_rows: list[dict[str, Any]] = []
    fac_rows: list[dict[str, Any]] = []
    rep_rows: list[dict[str, Any]] = []
    raw_fs_all: list[dict[str, Any]] = []

    for bcode, bdir_name, q_fn, fs_fn, rep_fn, cov_unit in specs:
        bdir = fb_dir / bdir_name
        mapping = {
            m["sample_id"]: m
            for m in _read_json(bdir / "human_eval" / "blind_key_mapping.private.json")
        }
        ai_dir = bdir / "ai_assisted_eval"

        # Quality CSV
        q_csv = ai_dir / q_fn
        q_hash = _sha256_file(q_csv)
        for r in _read_csv_rows(q_csv):
            m = mapping[r["sample_id"]]
            rm = run_meta_by_id[m["run_id"]]
            dims = [
                int(r["narrative_coherence"]),
                int(r["naturalness"]),
                int(r["persuasiveness"]),
                int(r["context_relevance"]),
                int(r["transition_quality"]),
                int(r["repetition_quality"]),
            ]
            qual_rows.append({
                "batch_code": bcode,
                "track": rm["track"],
                "full_label": rm["full_label"],
                "config_name": rm["config_name"],
                "sample_id": r["sample_id"],
                "blind_method_id": r["blind_method_id"],
                "run_id": m["run_id"],
                "narrative_coherence": dims[0],
                "naturalness": dims[1],
                "persuasiveness": dims[2],
                "context_relevance": dims[3],
                "transition_quality": dims[4],
                "repetition_quality": dims[5],
                "quality_mean": round(sum(dims) / 6.0, 2),
                "hard_constraint_violation_ai": r.get("hard_constraint_violation", ""),
                "provenance": AI_EVAL_PROVENANCE,
                "human_blind_status": "PENDING",
                "csv_sha256": q_hash,
            })

        # Factual & Semantic CSV
        fs_csv = ai_dir / fs_fn
        fs_hash = _sha256_file(fs_csv)
        fs_list = _read_csv_rows(fs_csv)
        for row in fs_list:
            m = mapping[row["sample_id"]]
            raw_fs_all.append({
                **row,
                "batch_code": bcode,
                "run_id": m["run_id"],
                "full_label": run_meta_by_id[m["run_id"]]["full_label"],
            })

        for sid, m in sorted(mapping.items()):
            rm = run_meta_by_id[m["run_id"]]
            sub = [x for x in fs_list if x["sample_id"] == sid]
            played = [x for x in sub if x["origin"] not in ("MISSING_TOPIC", "MISSING_SECOND_CHUNK")]
            missing = [x for x in sub if x["origin"] in ("MISSING_TOPIC", "MISSING_SECOND_CHUNK")]

            fac_cnt = Counter(x["factual_correctness_PASS_FAIL_UNSURE"] for x in played)
            ev_cnt = Counter(x["evidence_support_PASS_FAIL"] for x in played)
            leak_cnt = sum(1 for x in played if str(x.get("metadata_leak_YES_NO", "")).upper() == "YES")

            played_n = len(played)
            fac_rows.append({
                "batch_code": bcode,
                "track": rm["track"],
                "full_label": rm["full_label"],
                "config_name": rm["config_name"],
                "sample_id": sid,
                "run_id": m["run_id"],
                "audit_rows_total": len(sub),
                "played_turns_denominator": played_n,
                "missing_output_rows_excluded": len(missing),
                "factual_PASS": fac_cnt.get("PASS", 0),
                "factual_FAIL": fac_cnt.get("FAIL", 0),
                "factual_UNSURE": fac_cnt.get("UNSURE", 0),
                "factual_PASS_pct": round(100.0 * fac_cnt.get("PASS", 0) / played_n, 2) if played_n else 0.0,
                "evidence_PASS": ev_cnt.get("PASS", 0),
                "evidence_FAIL": ev_cnt.get("FAIL", 0),
                "evidence_PASS_pct": round(100.0 * ev_cnt.get("PASS", 0) / played_n, 2) if played_n else 0.0,
                "metadata_leak_YES": leak_cnt,
                "provenance": AI_EVAL_PROVENANCE,
                "gold_factual_status": "PENDING",
                "csv_sha256": fs_hash,
            })

            if cov_unit == "topic_m1":
                story_plan = _read_json(p06_root / "runs" / "P06-E01" / "formal_benchmark_v1" / bdir_name / m["run_id"] / "story_plan.json")
                planned_tids = {t["topic_id"] for arc in story_plan["arcs"] for t in arc["topics"]}
                mand_tids = {t["topic_id"] for arc in story_plan["arcs"] for t in arc["topics"] if t.get("is_mandatory")}
                proactive_by_tid = {}
                for x in played:
                    if x["origin"] != "PREAPPROVED_FALLBACK":
                        proactive_by_tid[x["topic_id"]] = x["semantic_alignment_FULL_PARTIAL_MISS"]
                all_c = Counter(proactive_by_tid.get(tid, "MISS") for tid in planned_tids)
                mand_c = Counter(proactive_by_tid.get(tid, "MISS") for tid in mand_tids)
                sem_rows.append({
                    "batch_code": bcode,
                    "track": rm["track"],
                    "full_label": rm["full_label"],
                    "config_name": rm["config_name"],
                    "sample_id": sid,
                    "coverage_unit": "topic_level_m1",
                    "all_denominator": len(planned_tids),
                    "all_FULL": all_c.get("FULL", 0),
                    "all_PARTIAL": all_c.get("PARTIAL", 0),
                    "all_MISS": all_c.get("MISS", 0),
                    "all_FULL_pct": round(100.0 * all_c.get("FULL", 0) / len(planned_tids), 2),
                    "mandatory_denominator": len(mand_tids),
                    "mandatory_FULL": mand_c.get("FULL", 0),
                    "mandatory_PARTIAL": mand_c.get("PARTIAL", 0),
                    "mandatory_MISS": mand_c.get("MISS", 0),
                    "mandatory_FULL_pct": round(100.0 * mand_c.get("FULL", 0) / len(mand_tids), 2),
                    "missing_output_rows": len(missing),
                    "missing_required_slots": len(missing),
                    "topics_both_chunks_FULL": None,
                    "provenance": AI_EVAL_PROVENANCE,
                })
            else:
                all_c = Counter()
                mand_c = Counter()
                by_tid: dict[str, list[str]] = {}
                missing_slots = 0
                for x in sub:
                    orig = x["origin"]
                    sem_lbl = x["semantic_alignment_FULL_PARTIAL_MISS"]
                    if orig == "PREAPPROVED_FALLBACK":
                        continue
                    mult = 2 if orig == "MISSING_TOPIC" else 1
                    if orig in ("MISSING_TOPIC", "MISSING_SECOND_CHUNK"):
                        missing_slots += mult
                    all_c[sem_lbl] += mult
                    if x["is_mandatory"] == "true":
                        mand_c[sem_lbl] += mult
                    by_tid.setdefault(x["topic_id"], []).extend([sem_lbl] * mult)
                both_full = sum(1 for vals in by_tid.values() if len(vals) >= 2 and vals[0] == "FULL" and vals[1] == "FULL")
                all_den = sum(all_c.values())
                mand_den = sum(mand_c.values())
                sem_rows.append({
                    "batch_code": bcode,
                    "track": rm["track"],
                    "full_label": rm["full_label"],
                    "config_name": rm["config_name"],
                    "sample_id": sid,
                    "coverage_unit": "required_slot_m2",
                    "all_denominator": all_den,
                    "all_FULL": all_c.get("FULL", 0),
                    "all_PARTIAL": all_c.get("PARTIAL", 0),
                    "all_MISS": all_c.get("MISS", 0),
                    "all_FULL_pct": round(100.0 * all_c.get("FULL", 0) / all_den, 2) if all_den else 0.0,
                    "mandatory_denominator": mand_den,
                    "mandatory_FULL": mand_c.get("FULL", 0),
                    "mandatory_PARTIAL": mand_c.get("PARTIAL", 0),
                    "mandatory_MISS": mand_c.get("MISS", 0),
                    "mandatory_FULL_pct": round(100.0 * mand_c.get("FULL", 0) / mand_den, 2) if mand_den else 0.0,
                    "missing_output_rows": len(missing),
                    "missing_required_slots": missing_slots,
                    "topics_both_chunks_FULL": f"{both_full}/{len(by_tid)}",
                    "provenance": AI_EVAL_PROVENANCE,
                })

        if rep_fn is not None:
            rep_csv = ai_dir / rep_fn
            rep_hash = _sha256_file(rep_csv)
            rep_list = _read_csv_rows(rep_csv)
            for sid, m in sorted(mapping.items()):
                rm = run_meta_by_id[m["run_id"]]
                sub = [x for x in rep_list if x["sample_id"] == sid]
                rc = Counter(x["semantic_repetition_label"] for x in sub)
                played_rev = sum(1 for x in sub if x["semantic_repetition_label"] != "NO_OUTPUT")
                verbatim_exact = sum(
                    1
                    for x in sub
                    if x["revisit_transcript"] and x["prior_transcript"]
                    and x["prior_transcript"].strip().lower() == x["revisit_transcript"].strip().lower()
                )
                rep_rows.append({
                    "batch_code": bcode,
                    "full_label": rm["full_label"],
                    "config_name": rm["config_name"],
                    "sample_id": sid,
                    "planned_revisits": len(sub),
                    "played_revisits": played_rev,
                    "EXACT_REPETITION": rc.get("EXACT_REPETITION", 0),
                    "exact_verbatim_pairs": verbatim_exact,
                    "UNWANTED_SEMANTIC_REPETITION": rc.get("UNWANTED_SEMANTIC_REPETITION", 0),
                    "LEGITIMATE_CONTINUATION": rc.get("LEGITIMATE_CONTINUATION", 0),
                    "DELIBERATE_RECURRENCE": rc.get("DELIBERATE_RECURRENCE", 0),
                    "UNSURE": rc.get("UNSURE", 0),
                    "NO_OUTPUT": rc.get("NO_OUTPUT", 0),
                    "unwanted_or_exact_played_pct": round(
                        100.0 * (rc.get("EXACT_REPETITION", 0) + rc.get("UNWANTED_SEMANTIC_REPETITION", 0)) / played_rev,
                        2,
                    ) if played_rev else math.nan,
                    "provenance": AI_EVAL_PROVENANCE,
                    "csv_sha256": rep_hash,
                })

    return {
        "quality": pd.DataFrame(qual_rows),
        "semantic": pd.DataFrame(sem_rows),
        "factual": pd.DataFrame(fac_rows),
        "repetition": pd.DataFrame(rep_rows),
        "raw_factual_rows": pd.DataFrame(raw_fs_all),
    }


def load_track2_mock_vs_live_df(p06_root: pathlib.Path) -> pd.DataFrame:
    """Đọc bảng đối chiếu Mock vs Live riêng của Track 2A & Track 2B (không gộp tầng)."""
    fb_dir = p06_root / "runs" / "P06-E01" / "formal_benchmark_v1"
    frames = []
    for bcode, bdir_name, lag in [
        ("2A", "track2a_small_window_lag6_s42", 6),
        ("2B", "track2b_large_window_lag12_s42", 12),
    ]:
        df = pd.read_csv(fb_dir / bdir_name / "mock_vs_live_comparison.csv")
        df.insert(0, "planned_lag", lag)
        df.insert(0, "batch_code", bcode)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def load_track2_lag_summary(p06_root: pathlib.Path) -> dict[str, dict[str, Any]]:
    """Tổng hợp actual_lag trên played revisits và rejected candidate attempts của Track 2A & 2B."""
    fb_dir = p06_root / "runs" / "P06-E01" / "formal_benchmark_v1"
    out: dict[str, dict[str, Any]] = {}
    for bcode, bdir_name, w_pass, w_fail in [
        ("2A", "track2a_small_window_lag6_s42", 5, 10),
        ("2B", "track2b_large_window_lag12_s42", 10, 20),
    ]:
        lag_df = pd.read_csv(fb_dir / bdir_name / "actual_lag_analysis.csv")
        opp_df = pd.read_csv(fb_dir / bdir_name / "repetition_opportunity_analysis.csv")
        pass_lags = dict(sorted(Counter(int(x) for x in lag_df[lag_df["history_window"] == w_pass]["actual_lag"]).items()))
        fail_opp = opp_df[opp_df["history_window"] == w_fail]
        fail_att_lags = dict(sorted(Counter(int(x) for x in fail_opp["actual_lag"]).items()))
        out[bcode] = {
            "pass_w": w_pass,
            "fail_w": w_fail,
            "played_revisits_count": int(len(lag_df[lag_df["history_window"] == w_pass])),
            "played_lag_dist": pass_lags,
            "fail_attempted_revisits_count": int(len(fail_opp)),
            "fail_attempted_lag_dist": fail_att_lags,
            "fail_in_window_attempts": int(fail_opp["window_hit"].sum()),
        }
    return out


def export_all_tables(
    p06_root: pathlib.Path,
    runs_df: pd.DataFrame,
    pilot_df: pd.DataFrame,
    eval_dfs: dict[str, pd.DataFrame],
    mock_vs_live_df: pd.DataFrame,
) -> dict[str, pathlib.Path]:
    """Xuất đầy đủ 12 bảng CSV chuẩn vào `reports/tables/E01/`."""
    tables_dir = p06_root / "reports" / "tables" / "E01"
    tables_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, pathlib.Path] = {}

    # Table 01: Formal Experiment Inventory (+ Table 01b tách Pilot & Mock)
    t01 = runs_df[[
        "batch_code", "track", "scenario", "dataset_profile", "min_chunks_per_topic",
        "planned_lag", "full_label", "run_id", "method", "history_window",
        "model_id", "seed", "yaml_global_cap", "operational_global_cap",
        "requests_attempted", "failed_calls", "http_503_calls", "http_429_calls",
        "played_turns", "termination_reason", "cost_usd", "overall_gate_status",
    ]]
    p01 = tables_dir / "01_formal_experiment_inventory.csv"
    t01.to_csv(p01, index=False, encoding="utf-8-sig")
    paths["01_formal_experiment_inventory"] = p01

    p01b = tables_dir / "01b_pilot_and_mock_inventory.csv"
    pilot_df.to_csv(p01b, index=False, encoding="utf-8-sig")
    paths["01b_pilot_and_mock_inventory"] = p01b

    # Table 02: Natural Benchmark Comparison (Batch 1A + Batch 1B)
    nat_df = runs_df[runs_df["batch_code"].isin(["1A", "1B"])][[
        "batch_code", "scenario", "full_label", "config_name", "run_id", "termination_reason",
        "completed_mandatory_topics", "mandatory_topics_count", "mandatory_topic_coverage",
        "completed_planned_topics", "planned_topics_count", "planned_topic_coverage",
        "declared_verified_claim_coverage", "simulated_played_duration_sec", "duration_fulfillment",
        "exact_normalized_text_replay_count", "lexical_repetition_rate",
        "rewrite_rate", "fallback_rate", "safe_abort_rate", "wasted_calls", "requests_attempted",
        "input_tokens", "output_tokens", "token_usage_source",
        "structural_hard_gates_status", "overall_gate_status",
    ]]
    p02 = tables_dir / "02_natural_benchmark_comparison.csv"
    nat_df.to_csv(p02, index=False, encoding="utf-8-sig")
    paths["02_natural_benchmark_comparison"] = p02

    # Table 03: Cross-Scenario Comparison (CHỈ paired Script-first vs LangGraph W=5)
    t03 = nat_df[nat_df["config_name"].isin(["Script-first", "LangGraph W=5"])].copy()
    p03 = tables_dir / "03_cross_scenario_comparison.csv"
    t03.to_csv(p03, index=False, encoding="utf-8-sig")
    paths["03_cross_scenario_comparison"] = p03

    # Table 04: Track 2 Comparison (Track 2A & Track 2B)
    t04 = runs_df[runs_df["batch_code"].isin(["2A", "2B"])][[
        "batch_code", "scenario", "dataset_profile", "planned_lag", "full_label", "history_window",
        "run_id", "termination_reason", "completed_planned_topics", "planned_topics_count",
        "completed_mandatory_topics", "mandatory_topics_count", "mandatory_topic_coverage",
        "declared_verified_claim_coverage", "simulated_played_duration_sec", "duration_fulfillment",
        "exact_chunk_replay_count", "exact_normalized_text_replay_count",
        "outside_window_exact_text_replay_count", "lexical_repetition_rate",
        "win_ngram3_w5", "win_ngram3_w10", "win_ngram3_w20",
        "detector_none", "detector_lexical_dup", "detector_repeated_facts", "detector_exact_replay",
        "rewrite_count", "rewrite_rate", "fallback_count", "fallback_rate",
        "safe_abort_count", "safe_abort_rate", "requests_attempted", "wasted_calls",
        "http_503_calls", "token_usage_source", "input_tokens", "output_tokens",
        "partial_measured_input_tokens", "partial_measured_output_tokens",
        "structural_hard_gates_status", "overall_gate_status",
    ]]
    p04 = tables_dir / "04_track2_comparison.csv"
    t04.to_csv(p04, index=False, encoding="utf-8-sig")
    paths["04_track2_comparison"] = p04

    # Table 05: Mock vs Live Comparison
    p05 = tables_dir / "05_mock_vs_live_comparison.csv"
    mock_vs_live_df.to_csv(p05, index=False, encoding="utf-8-sig")
    paths["05_mock_vs_live_comparison"] = p05

    # Table 06..09: AI-assisted Evaluation CSV summaries
    for key, fname in [
        ("quality", "06_ai_assisted_quality_scores.csv"),
        ("semantic", "07_semantic_coverage.csv"),
        ("factual", "08_factual_and_evidence_assessment.csv"),
        ("repetition", "09_revisit_repetition_distribution.csv"),
    ]:
        out_p = tables_dir / fname
        eval_dfs[key].to_csv(out_p, index=False, encoding="utf-8-sig")
        paths[fname.replace(".csv", "")] = out_p

    # Table 10: Budget & Reliability across 10 runs
    t10 = runs_df[[
        "batch_code", "full_label", "run_id", "yaml_global_cap", "operational_global_cap",
        "run_cap", "requests_attempted", "measured_calls", "failed_calls",
        "http_503_calls", "http_429_calls", "wasted_calls", "wasted_calls_pct",
        "rewrite_count", "rewrite_rate", "fallback_count", "fallback_rate",
        "safe_abort_count", "safe_abort_rate", "retry_budget_violations",
        "token_usage_source", "input_tokens", "output_tokens", "wasted_tokens",
        "partial_measured_input_tokens", "partial_measured_output_tokens", "partial_measured_wasted_tokens",
        "provider_latency_p50_ms", "provider_latency_p95_ms", "cost_usd", "termination_reason",
    ]]
    p10 = tables_dir / "10_budget_and_reliability.csv"
    t10.to_csv(p10, index=False, encoding="utf-8-sig")
    paths["10_budget_and_reliability"] = p10

    # Table 11: Acceptance Criteria Assessment (14 criteria — §12)
    t2_fac = eval_dfs["factual"][eval_dfs["factual"]["batch_code"].isin(["2A", "2B"])]
    t2_played = int(t2_fac["played_turns_denominator"].sum())
    t2_fpass = int(t2_fac["factual_PASS"].sum())
    t2_ffail = int(t2_fac["factual_FAIL"].sum())
    t2_funs = int(t2_fac["factual_UNSURE"].sum())
    t2_epass = int(t2_fac["evidence_PASS"].sum())

    t1_fac = eval_dfs["factual"][eval_dfs["factual"]["batch_code"].isin(["1A", "1B"])]
    t1_played = int(t1_fac["played_turns_denominator"].sum())
    t1_fpass = int(t1_fac["factual_PASS"].sum())
    t1_ffail = int(t1_fac["factual_FAIL"].sum())

    nat_lg = runs_df[(runs_df["batch_code"].isin(["1A", "1B"])) & (runs_df["config_name"] != "Script-first")]
    rw_summary = "; ".join(f"{r['full_label']}: {float(r['rewrite_rate'])*100:.1f}%" for _, r in nat_lg.iterrows())
    wst_logic_summary = "; ".join(
        f"{r['full_label']}: {int(r['wasted_calls'])-int(r['failed_calls'])}/{int(r['requests_attempted'])} ({100.0*(int(r['wasted_calls'])-int(r['failed_calls']))/int(r['requests_attempted']):.1f}%)"
        for _, r in nat_lg.iterrows()
    )
    fb_summary = "; ".join(f"{r['full_label']}: {int(r['fallback_count'])} fb ({int(r['http_503_calls'])} 503)" for _, r in nat_lg.iterrows())

    nat_dur_min = float(runs_df[runs_df["batch_code"].isin(["1A", "1B"])]["simulated_played_duration_sec"].min())
    nat_dur_max = float(runs_df[runs_df["batch_code"].isin(["1A", "1B"])]["simulated_played_duration_sec"].max())
    crit_rows = [
        {"criterion_id": 1, "criterion": "Structural invariants (exact_chunk_replay=0, metadata_leak=0, p05_reject=0, retry_viol=0)", "locked_threshold": "0 vi phạm (PASS mọi runs)", "observed_evidence": "10/10 formal runs structural_hard_gates_status = PASS; exact_chunk_replay=0; retry_viol=0; metadata_leak=0/240 played turns", "formal_status": "PASS", "notes": "Structural invariants pass nhưng KHÔNG đồng nghĩa overall gate PASS."},
        {"criterion_id": 2, "criterion": "Natural Track mandatory coverage (playback-confirmed)", "locked_threshold": "LangGraph >= 0.95 (mục tiêu 1.00)", "observed_evidence": "LangGraph 4/4 runs (1A W=5/10/20 & 1B W=5) = 1.0000 (12/12); Script-first = 0.5833 (1A) & 0.7500 (1B)", "formal_status": "PASS", "notes": "Đạt trên phạm vi Track 1 rút gọn; Track 2 là Stress reference."},
        {"criterion_id": 3, "criterion": "Semantic FULL/MISS (AI-assisted preliminary vs Gold PENDING)", "locked_threshold": ">= 0.85 FULL & <= 0.05 MISS trên Track 1 tự nhiên", "observed_evidence": "AI-assisted 1A W=5: 7/18 (38.9% FULL); 1B W=5: 12/18 (66.7% FULL); Human Gold = PENDING", "formal_status": "NOT_EVALUATED", "notes": "AI-assisted sơ bộ dưới ngưỡng 0.85 FULL; kết luận chính thức cần Human Blind/Gold."},
        {"criterion_id": 4, "criterion": "Lexical repetition", "locked_threshold": "<= 0.05 trên Track 1 (m=1); mô tả trên Track 2 (m=2)", "observed_evidence": "Track 1 = 0.0000 (6/6 runs); Track 2 passing runs = 0.2857 (2A W=5) & 0.3239 (2B W=10)", "formal_status": "PASS", "notes": "Đạt trên Track 1; Track 2 bộc lộ lặp từ/ngữ nghĩa cao khi W < actual_lag."},
        {"criterion_id": 5, "criterion": "Exact normalized text replay", "locked_threshold": "= 0 trên Track 1 (m=1)", "observed_evidence": "Track 1 = 0 (6/6 runs); Track 2 outside-window exact text replays = 2 (2A W=5) & 1 (2B W=10)", "formal_status": "PASS", "notes": "Đạt trên Track 1 (m=1); lộ hạn chế ngoài cửa sổ W ở Track 2 (m=2)."},
        {"criterion_id": 6, "criterion": "Rewrite rate (logic agent)", "locked_threshold": "<= 0.15 trên Natural Track (loại trừ HTTP 503)", "observed_evidence": f"{rw_summary}; cả 4 runs LangGraph đều vượt 15% chủ yếu do OVER_MAX_DURATION_SEC", "formal_status": "FAIL", "notes": "Rewrite vì quá giới hạn thời lượng 8.0s thường xuyên vượt trần 15%."},
        {"criterion_id": 7, "criterion": "Fallback rate (logic agent)", "locked_threshold": "<= 0.05 trên Natural Track (loại trừ HTTP 503)", "observed_evidence": f"{fb_summary}; các fallback Natural LangGraph phát sinh liên quan lượt HTTP 503 hoặc kiệt ứng viên cục bộ sau 503/retry", "formal_status": "PASS", "notes": "Natural Track gần như không cần logic fallback khi không có 503 (1A W=5 = 0%); Stress Track 2 W >= lag sụp vào fallback/abort."},
        {"criterion_id": 8, "criterion": "Wasted calls (logic, tách khỏi HTTP 503)", "locked_threshold": "<= 10% tổng calls trên Natural LangGraph", "observed_evidence": f"{wst_logic_summary}", "formal_status": "FAIL", "notes": "Vượt ngưỡng <= 10% do retry vượt thời lượng 8.0s."},
        {"criterion_id": 9, "criterion": "Factual correctness (AI-assisted preliminary; Gold = PENDING)", "locked_threshold": "Hard Gate = 0 sai lệch trên Gold Label", "observed_evidence": f"AI-assisted: Track 1 = {t1_fpass}/{t1_played} PASS ({t1_ffail} FAIL); Track 2 = {t2_fpass}/{t2_played} PASS ({t2_ffail} FAIL, {t2_funs} UNSURE); Gold = PENDING", "formal_status": "NOT_EVALUATED", "notes": "Chưa có GoldFactualLabel; tuy nhiên 16 AI-assisted FAIL xuyên 2 track là tín hiệu rủi ro ngữ nghĩa nghiêm trọng (bắt buộc CHANGE)."},
        {"criterion_id": 10, "criterion": "Evidence support (AI-assisted preliminary; Gold = PENDING)", "locked_threshold": "= 0 lượt thiếu evidence hợp lệ cho chi tiết đã nêu", "observed_evidence": f"AI-assisted: Track 1 = 84/110 (76.4% PASS, 26 FAIL); Track 2 = {t2_epass}/{t2_played} (76.9% PASS, 30 FAIL); Gold = PENDING", "formal_status": "NOT_EVALUATED", "notes": "AI-assisted phát hiện thiếu evidence hỗ trợ ở cả câu đúng catalog."},
        {"criterion_id": 11, "criterion": "Metadata leakage (human/AI audit & automated hygiene)", "locked_threshold": "= 0 lượt rò rỉ ev-/clm-/SKU-/JSON", "observed_evidence": "0 / 240 played turns theo AI-assisted (110 Track 1 + 130 Track 2) & automated hygiene check", "formal_status": "PASS", "notes": "Khắc phục triệt để lỗi Pilot v1 sau Pilot Remediation."},
        {"criterion_id": 12, "criterion": "Quality rubric (Human Blind 6 tiêu chí 1–5)", "locked_threshold": "Mean mỗi trục >= 3.5/5.0, không trục nào < 3.0", "observed_evidence": "Human Blind = PENDING; AI-assisted mean: 1A W=5 (3.33), 1B W=5 (3.17), 2A W=5 (2.50), 2B W=10 (2.33); transition=2.0", "formal_status": "NOT_EVALUATED", "notes": "Thiếu Human Blind Calibration; AI-assisted cho thấy transition_quality & repetition_quality thấp."},
        {"criterion_id": 13, "criterion": "Duration fulfillment (mục tiêu livestream 10–30 phút)", "locked_threshold": "10–30 phút (600s–1800s) không lặp vô ích", "observed_evidence": f"Tối đa = 489.996s (81.67% của 600s tại Track 2B W=10 với 36 chủ đề x 2 lượt, nhiều lặp); Track 1 đạt {nat_dur_min:.3f}s–{nat_dur_max:.3f}s", "formal_status": "FAIL", "notes": "VirtualClock words/2.6 != TTS audio thực tế; chưa đạt 10–30 phút."},
        {"criterion_id": 14, "criterion": "Human Blind Evaluation & Independent Calibration", "locked_threshold": "Hoàn tất chấm mù độc lập & calibration", "observed_evidence": "Chưa thực hiện (0% human_eval điền); Tech Lead chấp thuận đóng E01 với limitation bảo lưu", "formal_status": "NOT_EVALUATED", "notes": "Tất cả human_eval/ giữ nguyên trống; overall_gate_status = NOT_EVALUATED."},
    ]
    p11 = tables_dir / "11_acceptance_criteria_assessment.csv"
    pd.DataFrame(crit_rows).to_csv(p11, index=False, encoding="utf-8-sig")
    paths["11_acceptance_criteria_assessment"] = p11

    return paths


# ---------------------------------------------------------------------------
# Bộ công cụ vẽ biểu đồ PIL độ phân giải cao (1600 x 960) chuẩn Unicode tiếng Việt
# ---------------------------------------------------------------------------

def _new_canvas(title: str, subtitle: str, footer: str) -> tuple[Image.Image, ImageDraw.ImageDraw, dict[str, Any]]:
    w, h = 1600, 960
    img = Image.new("RGB", (w, h), BG_LIGHT)
    draw = ImageDraw.Draw(img)

    # Header bar
    draw.rectangle([0, 0, w, 108], fill=NAVY)
    draw.rectangle([0, 104, w, 108], fill=AMBER)

    f_title = _load_font(28, bold=True)
    f_sub = _load_font(17, bold=False)
    f_foot = _load_font(14, bold=False)

    draw.text((48, 22), title, font=f_title, fill=WHITE)
    draw.text((48, 64), subtitle, font=f_sub, fill=SOFT_YELLOW)

    # Footer bar
    draw.rectangle([0, h - 48, w, h], fill=NAVY)
    draw.text((48, h - 33), footer, font=f_foot, fill=COOL_GRAY)

    ctx = {
        "w": w,
        "h": h,
        "f_h2": _load_font(20, bold=True),
        "f_lbl": _load_font(15, bold=True),
        "f_txt": _load_font(15, bold=False),
        "f_sm": _load_font(13, bold=False),
        "f_sm_b": _load_font(13, bold=True),
    }
    return img, draw, ctx


def _draw_legend(draw: ImageDraw.ImageDraw, x: int, y: int, items: list[tuple[str, str]], font: Any, cols: int = 4) -> None:
    cur_x = x
    cur_y = y
    col_w = 340
    for idx, (label, color) in enumerate(items):
        if idx > 0 and idx % cols == 0:
            cur_x = x
            cur_y += 28
        draw.rectangle([cur_x, cur_y + 3, cur_x + 18, cur_y + 19], fill=color, outline=NAVY)
        draw.text((cur_x + 26, cur_y), label, font=font, fill=NAVY)
        cur_x += col_w


def _draw_axes_grid(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    y_min: float,
    y_max: float,
    ticks: list[float],
    fmt_fn: Any,
    y_title: str,
    ctx: dict[str, Any],
) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle([x0, y0, x1, y1], fill=WHITE, outline=COOL_GRAY, width=2)
    for t in ticks:
        frac = (t - y_min) / (y_max - y_min)
        py = int(round(y1 - frac * (y1 - y0)))
        draw.line([(x0, py), (x1, py)], fill="#E2E8F0", width=1)
        lbl = fmt_fn(t)
        draw.text((x0 - 12 - draw.textlength(lbl, font=ctx["f_sm"]), py - 9), lbl, font=ctx["f_sm"], fill=SLATE_DARK)
    draw.line([(x0, y1), (x1, y1)], fill=NAVY, width=2)
    draw.line([(x0, y0), (x0, y1)], fill=NAVY, width=2)
    draw.text((x0, y0 - 28), y_title, font=ctx["f_lbl"], fill=NAVY)


def _y_px(val: float, y_min: float, y_max: float, y0: int, y1: int) -> int:
    frac = max(0.0, min(1.0, (val - y_min) / (y_max - y_min)))
    return int(round(y1 - frac * (y1 - y0)))


def _draw_wrapped_center(draw: ImageDraw.ImageDraw, cx: int, y: int, lines: list[str], font: Any, fill: str = NAVY) -> None:
    cur_y = y
    for line in lines:
        tw = draw.textlength(line, font=font)
        draw.text((cx - tw / 2, cur_y), line, font=font, fill=fill)
        cur_y += 19


def generate_all_figures(
    p06_root: pathlib.Path,
    runs_df: pd.DataFrame,
    eval_dfs: dict[str, pd.DataFrame],
    lag_summary: dict[str, dict[str, Any]],
) -> dict[str, pathlib.Path]:
    """Sinh 8 biểu đồ PNG chất lượng cao từ số liệu đã phân tích vào `reports/figures/E01/`."""
    fig_dir = p06_root / "reports" / "figures" / "E01"
    fig_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, pathlib.Path] = {}

    # ------------------------------------------------------------------
    # Fig 01: Natural Track Mandatory vs Planned Coverage (Batch 1A & 1B)
    # ------------------------------------------------------------------
    nat = runs_df[runs_df["batch_code"].isin(["1A", "1B"])].copy()
    img, draw, ctx = _new_canvas(
        "Hình 01 — Natural Track: Độ Phủ Chủ Đề Bắt Buộc & Toàn Kế Hoạch (Playback-Confirmed)",
        "Batch 1A (Product Edu, m=1, n=1/config) & Batch 1B (Brand Storytelling, m=1, n=1/config) | Mẫu số: 12 mandatory / 18 planned topics",
        "Nguồn: metrics.json & story_plan.json (6 Natural formal runs, 135 requests). Lưu ý: Playback coverage = 100% không đồng nghĩa semantic content FULL = 100%.",
    )
    box = (110, 195, 1520, 790)
    _draw_axes_grid(draw, box, 0, 110, [0, 25, 50, 75, 95, 100], lambda v: f"{int(v)}%", "Độ phủ (%) trên số chủ đề kế hoạch", ctx)
    y_95 = _y_px(95, 0, 110, box[1], box[3])
    draw.line([(box[0], y_95), (box[2], y_95)], fill=CRIMSON, width=2)
    div_x = box[0] + 4 * ((box[2] - box[0]) // len(nat))
    draw.text((div_x + 16, y_95 - 22), "Ngưỡng khóa Natural >= 95%", font=ctx["f_sm_b"], fill=CRIMSON)
    _draw_legend(draw, 110, 130, [("Mandatory Topics Coverage (%/12)", NAVY), ("All Planned Topics Coverage (%/18)", AMBER)], ctx["f_lbl"], cols=2)

    x_step = (box[2] - box[0]) // len(nat)
    for i, (_, r) in enumerate(nat.iterrows()):
        cx = box[0] + int((i + 0.5) * x_step)
        mand_pct = float(r["mandatory_topic_coverage"]) * 100.0
        plan_pct = float(r["planned_topic_coverage"]) * 100.0
        bw = 54
        # Mandatory bar
        xm0, xm1 = cx - bw - 4, cx - 4
        ym0 = _y_px(mand_pct, 0, 110, box[1], box[3])
        draw.rectangle([xm0, ym0, xm1, box[3]], fill=NAVY)
        lbl_m = f"{mand_pct:.1f}%"
        draw.text((xm0 + (bw - draw.textlength(lbl_m, font=ctx["f_sm_b"])) / 2, ym0 - 20), lbl_m, font=ctx["f_sm_b"], fill=NAVY)
        # Planned bar
        xp0, xp1 = cx + 4, cx + 4 + bw
        yp0 = _y_px(plan_pct, 0, 110, box[1], box[3])
        draw.rectangle([xp0, yp0, xp1, box[3]], fill=AMBER, outline=NAVY)
        lbl_p = f"{plan_pct:.1f}%"
        draw.text((xp0 + (bw - draw.textlength(lbl_p, font=ctx["f_sm_b"])) / 2, yp0 - 20), lbl_p, font=ctx["f_sm_b"], fill=AMBER_DARK)

        term_short = "EXHAUSTED" if "EXHAUSTED" in r["termination_reason"] else "EARLY_COMP"
        _draw_wrapped_center(draw, cx, box[3] + 14, [r["full_label"], f"({r['scenario_label'][:16]})", term_short], ctx["f_sm_b"])
    # Divider between 1A and 1B
    div_x = box[0] + 4 * x_step
    draw.line([(div_x, box[1]), (div_x, box[3] + 75)], fill=SLATE_MID, width=2)
    p01 = fig_dir / "fig01_natural_mandatory_coverage.png"
    img.save(p01)
    paths["fig01_natural_mandatory_coverage"] = p01

    # ------------------------------------------------------------------
    # Fig 02: Structural vs Semantic Coverage (Split by Denominator)
    # ------------------------------------------------------------------
    sem = eval_dfs["semantic"]
    img, draw, ctx = _new_canvas(
        "Hình 02 — Structural Playback Coverage vs AI-Assisted Semantic Coverage (Tách Biệt Mẫu Số)",
        "Trái: Natural Track (mẫu số 18 chủ đề) | Phải: Stress Track 2 (mẫu số 36 hoặc 72 required slots) | AI-assisted ChatGPT",
        "Lưu ý: Không gộp trực tiếp Topic Coverage (Track 1) với Required-Slot Coverage (Track 2). Missing outputs ở 2A W=10 (30 slots) & 2B W=20 (60 slots) đều tính MISS.",
    )
    _draw_legend(draw, 110, 128, [
        ("Playback Structural Coverage (%)", SLATE_MID),
        ("Semantic FULL (%)", TEAL),
        ("Semantic PARTIAL (%)", AMBER),
        ("Semantic MISS (%)", CRIMSON),
    ], ctx["f_lbl"], cols=4)

    for panel_idx, (unit, pbox, ptitle) in enumerate([
        ("topic_m1_panel", (95, 210, 860, 790), "Natural Track (Đơn vị: 18 Planned Topics)"),
        ("slot_m2_panel", (940, 210, 1525, 790), "Stress Track 2 (Đơn vị: 36 hoặc 72 Required Slots)"),
    ]):
        _draw_axes_grid(draw, pbox, 0, 110, [0, 25, 50, 75, 100], lambda v: f"{int(v)}%", ptitle, ctx)
        sub_runs = runs_df[runs_df["batch_code"].isin(["1A", "1B"] if panel_idx == 0 else ["2A", "2B"])]
        step = (pbox[2] - pbox[0]) // len(sub_runs)
        for i, (_, rr) in enumerate(sub_runs.iterrows()):
            srow = sem[sem["full_label"] == rr["full_label"]].iloc[0]
            cx = pbox[0] + int((i + 0.5) * step)
            bw = 36
            struct_pct = float(rr["planned_topic_coverage"]) * 100.0
            den = int(srow["all_denominator"])
            f_pct = 100.0 * int(srow["all_FULL"]) / den
            p_pct = 100.0 * int(srow["all_PARTIAL"]) / den
            m_pct = 100.0 * int(srow["all_MISS"]) / den

            # Bar 1: Structural Playback
            xb0 = cx - bw - 3
            ys = _y_px(struct_pct, 0, 110, pbox[1], pbox[3])
            draw.rectangle([xb0, ys, xb0 + bw, pbox[3]], fill=SLATE_MID)
            draw.text((xb0 + 2, ys - 18), f"{struct_pct:.0f}%", font=ctx["f_sm_b"], fill=SLATE_DARK)

            # Bar 2: Stacked Semantic FULL + PARTIAL + MISS
            xs0 = cx + 3
            cur_bottom = pbox[3]
            for val, col in [(f_pct, TEAL), (p_pct, AMBER), (m_pct, CRIMSON)]:
                if val > 0:
                    y_top = _y_px(val + (100.0 - (cur_bottom - pbox[1]) * 110.0 / (pbox[3] - pbox[1])) if False else 0, 0, 110, pbox[1], pbox[3])
                    bar_h = int(round(val / 110.0 * (pbox[3] - pbox[1])))
                    draw.rectangle([xs0, cur_bottom - bar_h, xs0 + bw, cur_bottom], fill=col)
                    cur_bottom -= bar_h
            draw.text((xs0 - 4, cur_bottom - 18), f"F:{f_pct:.0f}%", font=ctx["f_sm_b"], fill=TEAL)
            _draw_wrapped_center(draw, cx, pbox[3] + 10, [rr["batch_code"], rr["config_name"].replace("LangGraph ", "LG "), f"(n={den})"], ctx["f_sm_b"])

    p02 = fig_dir / "fig02_structural_vs_semantic_coverage.png"
    img.save(p02)
    paths["fig02_structural_vs_semantic_coverage"] = p02

    # ------------------------------------------------------------------
    # Fig 03: AI-assisted Storytelling Quality (Rubric v0.1, Scale 1-5)
    # ------------------------------------------------------------------
    qdf = eval_dfs["quality"]
    img, draw, ctx = _new_canvas(
        "Hình 03 — Chất Lượng Kể Chuyện Theo Rubric v0.1 (AI-Assisted Non-Blind — ChatGPT)",
        "Điểm trung bình 6 tiêu chí (thang 1–5) & Mean theo từng mẫu trong Batch 1A, 1B, Track 2A & Track 2B",
        "Hạn chế: AI-assisted non-blind evaluation (KHÔNG phải Human Blind / Calibration). Đường nét đứt 3.5 là ngưỡng đề xuất ban đầu (PROPOSED / TO VALIDATE).",
    )
    box = (110, 195, 1520, 785)
    _draw_axes_grid(draw, box, 0, 5.5, [1, 2, 3, 3.5, 4, 5], lambda v: f"{v:.1f}", "Điểm Rubric v0.1 (Thang 1–5)", ctx)
    y_35 = _y_px(3.5, 0, 5.5, box[1], box[3])
    draw.line([(box[0], y_35), (box[2], y_35)], fill=CRIMSON, width=2)
    draw.text((box[2] - 250, y_35 - 22), "Ngưỡng đề xuất 3.5 / 5.0", font=ctx["f_sm_b"], fill=CRIMSON)
    _draw_legend(draw, 110, 128, [
        ("Quality Mean (6 tiêu chí)", NAVY),
        ("Transition Quality (1–5)", BLUE),
        ("Repetition Quality (1–5)", AMBER),
    ], ctx["f_lbl"], cols=3)

    step = (box[2] - box[0]) // len(qdf)
    for i, (_, qr) in enumerate(qdf.iterrows()):
        cx = box[0] + int((i + 0.5) * step)
        bw = 26
        vals = [
            (float(qr["quality_mean"]), NAVY, f"{qr['quality_mean']:.2f}"),
            (float(qr["transition_quality"]), BLUE, f"{int(qr['transition_quality'])}"),
            (float(qr["repetition_quality"]), AMBER, f"{int(qr['repetition_quality'])}"),
        ]
        offsets = [-bw - 16, -bw // 2, 16]
        for (v, col, txt_v), off in zip(vals, offsets):
            x_b0 = cx + off
            y_b0 = _y_px(v, 0, 5.5, box[1], box[3])
            draw.rectangle([x_b0, y_b0, x_b0 + bw, box[3]], fill=col)
            draw.text((x_b0, y_b0 - 18), txt_v, font=ctx["f_sm_b"], fill=NAVY)
        _draw_wrapped_center(draw, cx, box[3] + 12, [qr["batch_code"], qr["config_name"].replace("LangGraph ", "LG ")], ctx["f_sm_b"])
    p03 = fig_dir / "fig03_ai_assisted_storytelling_quality.png"
    img.save(p03)
    paths["fig03_ai_assisted_storytelling_quality"] = p03

    # ------------------------------------------------------------------
    # Fig 04: Track 2 Window Completion vs Repetition Trade-off
    # ------------------------------------------------------------------
    t2 = runs_df[runs_df["batch_code"].isin(["2A", "2B"])].copy()
    img, draw, ctx = _new_canvas(
        "Hình 04 — Track 2 Stress: Đánh Đổi Giữa Hoàn Tất Chủ Đề (>=2 chunks) & Lặp Khi W Vượt Lag",
        "Track 2A (lag=6, 18 topics, n=1) & Track 2B (lag=12, 36 topics, n=1) | Thiết kế 1 allowed_claim_id/topic",
        "Lưu ý: Không quy thành định luật tổng quát. W=10 ở 2A và W=10 ở 2B khác nhau đồng thời về dataset, số chủ đề và lag. W >= lag sụp về 0% do REPEATED_FACTS.",
    )
    box = (110, 195, 1520, 785)
    _draw_axes_grid(draw, box, 0, 115, [0, 25, 50, 75, 100], lambda v: f"{int(v)}%", "Tỷ lệ (%) — Hoàn tất / Lặp từ vựng", ctx)
    _draw_legend(draw, 110, 128, [
        ("Chủ đề đạt >= 2 chunks (%)", TEAL),
        ("Lexical Repetition Rate (%)", AMBER),
        ("Tỷ lệ lượt lãng phí / tổng calls (%)", CRIMSON),
    ], ctx["f_lbl"], cols=3)

    step = (box[2] - box[0]) // len(t2)
    for i, (_, r) in enumerate(t2.iterrows()):
        cx = box[0] + int((i + 0.5) * step)
        bw = 54
        comp_pct = float(r["planned_topic_coverage"]) * 100.0
        lex_pct = float(r["lexical_repetition_rate"]) * 100.0
        wst_pct = float(r["wasted_calls_pct"])
        for val, col, off, lbl in [
            (comp_pct, TEAL, -86, f"{comp_pct:.0f}%"),
            (lex_pct, AMBER, -27, f"{lex_pct:.1f}%"),
            (wst_pct, CRIMSON, 32, f"{wst_pct:.1f}%"),
        ]:
            x0 = cx + off
            y0 = _y_px(val, 0, 115, box[1], box[3])
            draw.rectangle([x0, y0, x0 + bw, box[3]], fill=col)
            draw.text((x0 + 4, y0 - 18), lbl, font=ctx["f_sm_b"], fill=NAVY)
        rel_str = "W < lag" if int(r["history_window"]) < int(r["planned_lag"]) else "W > lag (ABORT)"
        replays = int(r["outside_window_exact_text_replay_count"])
        _draw_wrapped_center(draw, cx, box[3] + 12, [r["full_label"], f"{rel_str} | Exact replay={replays}"], ctx["f_sm_b"])
    draw.line([(box[0] + 2 * step, box[1]), (box[0] + 2 * step, box[3] + 65)], fill=SLATE_MID, width=2)
    p04 = fig_dir / "fig04_window_completion_vs_repetition_tradeoff.png"
    img.save(p04)
    paths["fig04_window_completion_vs_repetition_tradeoff"] = p04

    # ------------------------------------------------------------------
    # Fig 05: Actual Lag & Windowed N-gram3 Jump Across Lag Boundary
    # ------------------------------------------------------------------
    img, draw, ctx = _new_canvas(
        "Hình 05 — Phân Bổ Actual Lag Thực Tế & Bước Nhảy N-gram3 Có Cửa Sổ Qua Ngưỡng Lag",
        "Trái: So sánh Actual Lag vs Cửa sổ W (Played vs Rejected Attempts) | Phải: Windowed N-gram3 Jaccard Mean (w5 / w10 / w20)",
        "Nguồn: actual_lag_analysis.csv, repetition_opportunity_analysis.csv, metrics.json. 100% lượt quay lại phát thành công rơi ngoài cửa sổ W; 100% attempts trong W bị chặn.",
    )
    # Left panel: Actual Lag vs W
    lbox = (110, 200, 820, 785)
    _draw_axes_grid(draw, lbox, 0, 22, [0, 5, 6, 10, 12, 15, 20], lambda v: f"{int(v)}", "Số lượt (W và Actual Lag)", ctx)
    _draw_legend(draw, 110, 128, [
        ("Cửa sổ History W (lượt)", BLUE),
        ("Actual Lag (Played thành công)", TEAL),
        ("Actual Lag (Attempt bị chặn)", CRIMSON),
    ], ctx["f_lbl"], cols=3)
    lag_items = [
        ("2A W=5", 5, 6, TEAL, "lag=6 (18/18 ngoài W)"),
        ("2A W=10", 10, 8, CRIMSON, "att lag 5–8 (trong W)"),
        ("2B W=10", 10, 12, TEAL, "lag=12 (36/36 ngoài W)"),
        ("2B W=20", 20, 14, CRIMSON, "att lag 11–14 (trong W)"),
    ]
    lstep = (lbox[2] - lbox[0]) // 4
    for i, (lbl, wv, max_lag, lcol, note) in enumerate(lag_items):
        cx = lbox[0] + int((i + 0.5) * lstep)
        yw = _y_px(wv, 0, 22, lbox[1], lbox[3])
        yl = _y_px(max_lag, 0, 22, lbox[1], lbox[3])
        draw.rectangle([cx - 42, yw, cx - 4, lbox[3]], fill=BLUE)
        draw.rectangle([cx + 4, yl, cx + 42, lbox[3]], fill=lcol)
        draw.text((cx - 34, yw - 18), f"W={wv}", font=ctx["f_sm_b"], fill=BLUE)
        draw.text((cx + 6, yl - 18), f"max={max_lag}", font=ctx["f_sm_b"], fill=lcol)
        _draw_wrapped_center(draw, cx, lbox[3] + 12, [lbl, note], ctx["f_sm"])

    # Right panel: Windowed N-gram3 Jaccard jump on passing runs
    rbox = (930, 200, 1525, 785)
    _draw_axes_grid(draw, rbox, 0, 0.30, [0.0, 0.05, 0.10, 0.15, 0.20, 0.25], lambda v: f"{v:.2f}", "Windowed 3-gram Jaccard Mean", ctx)
    t2a_w5 = runs_df[runs_df["full_label"] == "2A LangGraph W=5"].iloc[0]
    t2b_w10 = runs_df[runs_df["full_label"] == "2B LangGraph W=10"].iloc[0]
    x_pts = [rbox[0] + 100, rbox[0] + 295, rbox[0] + 490]
    for series_lbl, vals, col, y_offs in [
        ("2A W=5 (lag=6): 0.0028 -> 0.2031 (~73.4x)", [float(t2a_w5["win_ngram3_w5"]), float(t2a_w5["win_ngram3_w10"]), float(t2a_w5["win_ngram3_w20"])], BLUE, [10, -24, -24]),
        ("2B W=10 (lag=12): 0.0131 -> 0.2455 (~18.8x)", [float(t2b_w10["win_ngram3_w5"]), float(t2b_w10["win_ngram3_w10"]), float(t2b_w10["win_ngram3_w20"])], ORANGE, [-26, -26, -24]),
    ]:
        pts = [(xp, _y_px(v, 0, 0.30, rbox[1], rbox[3])) for xp, v in zip(x_pts, vals)]
        draw.line(pts, fill=col, width=4)
        for (px, py), v, dy in zip(pts, vals, y_offs):
            draw.ellipse([px - 7, py - 7, px + 7, py + 7], fill=col, outline=WHITE)
            draw.text((px - 22, py + dy), f"{v:.4f}", font=ctx["f_sm_b"], fill=col)
    draw.text((955, 220), "2A W=5 (lag=6) — nhảy tại w10", font=ctx["f_sm_b"], fill=BLUE)
    draw.text((955, 244), "2B W=10 (lag=12) — nhảy tại w20", font=ctx["f_sm_b"], fill=ORANGE)
    for xp, wlbl in zip(x_pts, ["Cửa sổ w5", "Cửa sổ w10", "Cửa sổ w20"]):
        _draw_wrapped_center(draw, xp, rbox[3] + 14, [wlbl], ctx["f_sm_b"])
    p05 = fig_dir / "fig05_actual_lag_and_window_membership.png"
    img.save(p05)
    paths["fig05_actual_lag_and_window_membership"] = p05

    # ------------------------------------------------------------------
    # Fig 06: Semantic Repetition Distribution (Including NO_OUTPUT Warning)
    # ------------------------------------------------------------------
    rdf = eval_dfs["repetition"]
    img, draw, ctx = _new_canvas(
        "Hình 06 — Phân Bố Nhãn Lặp Ngữ Nghĩa Trên 108 Planned Revisits (AI-Assisted — ChatGPT)",
        "Track 2A (18 revisits/run) & Track 2B (36 revisits/run) | Tổng: 54 phát thành công + 54 NO_OUTPUT",
        "CẢNH BÁO DIỄN GIẢI: NO_OUTPUT (2A W=10 & 2B W=20) là hệ quả MAX_CONSECUTIVE_ABORTS (0% hoàn tất), TUYỆT ĐỐI KHÔNG phải chống lặp thành công!",
    )
    box = (110, 210, 1520, 785)
    _draw_axes_grid(draw, box, 0, 108, [0, 25, 50, 75, 100], lambda v: f"{int(v)}%", "Tỷ lệ (%) trên Tổng Revisit Kế Hoạch", ctx)
    cats = [
        ("EXACT_REPETITION (gồm gần nguyên văn)", "EXACT_REPETITION", CRIMSON),
        ("UNWANTED_SEMANTIC_REPETITION", "UNWANTED_SEMANTIC_REPETITION", ORANGE),
        ("DELIBERATE_RECURRENCE", "DELIBERATE_RECURRENCE", AMBER),
        ("LEGITIMATE_CONTINUATION", "LEGITIMATE_CONTINUATION", TEAL),
        ("UNSURE", "UNSURE", BLUE),
        ("NO_OUTPUT (Dừng sớm / Abort)", "NO_OUTPUT", GRAY_HATCH),
    ]
    _draw_legend(draw, 110, 122, [(c[0], c[2]) for c in cats], ctx["f_sm_b"], cols=3)

    step = (box[2] - box[0]) // len(rdf)
    for i, (_, rr) in enumerate(rdf.iterrows()):
        cx = box[0] + int((i + 0.5) * step)
        bw = 110
        tot = int(rr["planned_revisits"])
        cur_y = box[3]
        for _, col_key, fill_c in cats:
            cnt = int(rr[col_key])
            if cnt <= 0:
                continue
            bh = int(round((100.0 * cnt / tot) / 108.0 * (box[3] - box[1])))
            draw.rectangle([cx - bw // 2, cur_y - bh, cx + bw // 2, cur_y], fill=fill_c, outline=WHITE)
            if bh >= 18:
                t_lbl = f"{cnt} ({100*cnt/tot:.0f}%)"
                draw.text((cx - draw.textlength(t_lbl, font=ctx["f_sm_b"]) / 2, cur_y - bh // 2 - 8), t_lbl, font=ctx["f_sm_b"], fill=NAVY)
            cur_y -= bh
        sub_note = "ABORT: 0% phát vòng 2" if int(rr["NO_OUTPUT"]) > 0 else f"Phát đủ: lặp/gần = {int(rr['EXACT_REPETITION'])+int(rr['UNWANTED_SEMANTIC_REPETITION'])}/{tot}"
        _draw_wrapped_center(draw, cx, box[3] + 12, [rr["full_label"] + f" (n={tot})", sub_note], ctx["f_sm_b"])
    p06 = fig_dir / "fig06_semantic_repetition_distribution.png"
    img.save(p06)
    paths["fig06_semantic_repetition_distribution"] = p06

    # ------------------------------------------------------------------
    # Fig 07: Factual Correctness & Evidence Support on Played Turns
    # ------------------------------------------------------------------
    fdf = eval_dfs["factual"]
    img, draw, ctx = _new_canvas(
        "Hình 07 — Kiểm Toán Factual Correctness & Evidence Support Trên Played Turns (AI-Assisted)",
        "Natural Track (110 played turns) & Stress Track 2 (130 played turns) | Tổng = 240 played turns | Metadata leakage = 0/240",
        "Ghi chú: Mẫu số CHỈ gồm played turns (gồm fallback đã phát), KHÔNG tính missing output. UNSURE KHÔNG phải PASS. Human GoldFactualLabel = PENDING.",
    )
    box = (110, 200, 1520, 785)
    _draw_axes_grid(draw, box, 0, 108, [0, 25, 50, 75, 100], lambda v: f"{int(v)}%", "Tỷ lệ (%) trên Played Turns", ctx)
    _draw_legend(draw, 110, 128, [
        ("Factual PASS (%)", TEAL),
        ("Factual UNSURE (%)", AMBER),
        ("Factual FAIL (%)", CRIMSON),
        ("Evidence PASS (%)", BLUE),
    ], ctx["f_lbl"], cols=4)

    step = (box[2] - box[0]) // len(fdf)
    for i, (_, fr) in enumerate(fdf.iterrows()):
        cx = box[0] + int((i + 0.5) * step)
        den = int(fr["played_turns_denominator"])
        bw = 36
        # Factual stack
        cur_y = box[3]
        for cnt_k, col in [("factual_PASS", TEAL), ("factual_UNSURE", AMBER), ("factual_FAIL", CRIMSON)]:
            pct = 100.0 * int(fr[cnt_k]) / den
            if pct <= 0:
                continue
            bh = int(round(pct / 108.0 * (box[3] - box[1])))
            draw.rectangle([cx - bw - 3, cur_y - bh, cx - 3, cur_y], fill=col)
            cur_y -= bh
        draw.text((cx - bw - 3, cur_y - 18), f"{float(fr['factual_PASS_pct']):.0f}%", font=ctx["f_sm_b"], fill=TEAL)

        # Evidence PASS bar
        epct = float(fr["evidence_PASS_pct"])
        ye = _y_px(epct, 0, 108, box[1], box[3])
        draw.rectangle([cx + 3, ye, cx + 3 + bw, box[3]], fill=BLUE)
        draw.text((cx + 3, ye - 18), f"{epct:.0f}%", font=ctx["f_sm_b"], fill=BLUE)

        _draw_wrapped_center(draw, cx, box[3] + 12, [fr["batch_code"], fr["config_name"].replace("LangGraph ", "LG "), f"n={den}"], ctx["f_sm"])
    p07 = fig_dir / "fig07_factual_and_evidence_assessment.png"
    img.save(p07)
    paths["fig07_factual_and_evidence_assessment"] = p07

    # ------------------------------------------------------------------
    # Fig 08: Wasted Calls Breakdown & Simulated Duration Fulfillment
    # ------------------------------------------------------------------
    img, draw, ctx = _new_canvas(
        "Hình 08 — Độ Tin Cậy (Wasted Calls / HTTP 503) & Thời Lượng Mô Phỏng 10 Phiên Formal",
        "Trái: Cơ cấu Calls (Valid vs Wasted/HTTP 503) | Phải: Thời lượng mô phỏng VirtualClock (giây) so với mục tiêu 600s",
        "Lưu ý: VirtualClock (2.6 từ/giây) KHÔNG phải audio TTS thực tế; mức cao nhất 489.996s (2B W=10) chưa chứng minh mục tiêu livestream 10–30 phút.",
    )
    lbox = (95, 200, 820, 785)
    rbox = (910, 200, 1525, 785)
    _draw_axes_grid(draw, lbox, 0, 95, [0, 20, 40, 60, 80], lambda v: f"{int(v)}", "Số Gemini API Calls (Tổng = 317)", ctx)
    _draw_axes_grid(draw, rbox, 0, 660, [0, 150, 300, 450, 600], lambda v: f"{int(v)}s", "Thời lượng mô phỏng VirtualClock (s)", ctx)
    y600 = _y_px(600, 0, 660, rbox[1], rbox[3])
    draw.line([(rbox[0], y600), (rbox[2], y600)], fill=CRIMSON, width=2)
    draw.text((rbox[0] + 12, y600 - 22), "Mục tiêu tối thiểu 10 phút = 600s (Đạt tối đa 490.0s)", font=ctx["f_sm_b"], fill=CRIMSON)
    _draw_legend(draw, 95, 128, [
        ("Calls hữu ích (Played Primary)", TEAL),
        ("Wasted Logic Calls (Rewrite/Abort)", AMBER),
        ("Failed Calls (HTTP 503)", CRIMSON),
        ("Simulated Played Duration (s)", BLUE),
    ], ctx["f_sm_b"], cols=4)

    n_runs = len(runs_df)
    lstep = (lbox[2] - lbox[0]) // n_runs
    rstep = (rbox[2] - rbox[0]) // n_runs
    for i, (_, r) in enumerate(runs_df.iterrows()):
        tot_c = int(r["requests_attempted"])
        fail_c = int(r["failed_calls"])
        wst_c = max(0, int(r["wasted_calls"]) - fail_c)
        val_c = max(0, tot_c - wst_c - fail_c)

        cx_l = lbox[0] + int((i + 0.5) * lstep)
        bw = 42
        cur_y = lbox[3]
        for cnt, col in [(val_c, TEAL), (wst_c, AMBER), (fail_c, CRIMSON)]:
            if cnt <= 0:
                continue
            bh = int(round(cnt / 95.0 * (lbox[3] - lbox[1])))
            draw.rectangle([cx_l - bw // 2, cur_y - bh, cx_l + bw // 2, cur_y], fill=col)
            cur_y -= bh
        draw.text((cx_l - 12, cur_y - 18), f"{tot_c}", font=ctx["f_sm_b"], fill=NAVY)
        _draw_wrapped_center(draw, cx_l, lbox[3] + 10, [r["batch_code"], r["config_name"].replace("LangGraph ", "LG ").replace("Script-first", "SF")], ctx["f_sm"])

        cx_r = rbox[0] + int((i + 0.5) * rstep)
        dur = float(r["simulated_played_duration_sec"])
        yd = _y_px(dur, 0, 660, rbox[1], rbox[3])
        draw.rectangle([cx_r - 18, yd, cx_r + 18, rbox[3]], fill=BLUE)
        draw.text((cx_r - 20, yd - 18), f"{dur:.0f}s", font=ctx["f_sm_b"], fill=BLUE)
        _draw_wrapped_center(draw, cx_r, rbox[3] + 10, [r["batch_code"], r["config_name"].replace("LangGraph ", "LG ").replace("Script-first", "SF")], ctx["f_sm"])

    p08 = fig_dir / "fig08_reliability_waste_and_duration.png"
    img.save(p08)
    paths["fig08_reliability_waste_and_duration"] = p08

    return paths


def export_artifact_index(
    p06_root: pathlib.Path,
    runs_df: pd.DataFrame,
    eval_dfs: dict[str, pd.DataFrame],
    table_paths: dict[str, pathlib.Path],
    figure_paths: dict[str, pathlib.Path],
    git_info: dict[str, Any],
) -> pathlib.Path:
    """Xuất `reports/E01/e01_artifact_index.json` ghi nhận đầy đủ provenance, hash và bảng ánh xạ di chuyển."""
    fb_dir = p06_root / "runs" / "P06-E01" / "formal_benchmark_v1"

    locked_rel = [
        "data/products/e01_ext_v1_verified_skus.json",
        "data/story_plans/e01_ext_v1_story_plans.json",
        "data/products/e01_formal_v1_verified_skus.json",
        "data/story_plans/e01_formal_v1_story_plans.json",
        "prompts/story_planner.txt",
        "prompts/story_generation.txt",
        "prompts/rewrite.txt",
        "configs/models/gemini_3.5_flash_lite_free.yaml",
        "configs/experiments/p06_e01_formal_batch1a.yaml",
        "configs/experiments/p06_e01_formal_batch1b.yaml",
        "configs/experiments/p06_e01_formal_track2a_w5_w10.yaml",
        "configs/experiments/p06_e01_formal_track2b_w10_w20.yaml",
    ]
    locked_hashes = {rel: _sha256_file(p06_root / rel) for rel in locked_rel if (p06_root / rel).is_file()}

    ai_hashes: dict[str, dict[str, str]] = {}
    for rel in [
        "track1_product_edu_s42/ai_assisted_eval/batch1a_ai_assisted_quality.csv",
        "track1_product_edu_s42/ai_assisted_eval/batch1a_ai_assisted_factual_semantic.csv",
        "track1_brand_storytelling_s42/ai_assisted_eval/batch1b_ai_assisted_quality.csv",
        "track1_brand_storytelling_s42/ai_assisted_eval/batch1b_ai_assisted_factual_semantic.csv",
        "track2a_small_window_lag6_s42/ai_assisted_eval/track2a_ai_assisted_quality.csv",
        "track2a_small_window_lag6_s42/ai_assisted_eval/track2a_ai_assisted_factual_semantic.csv",
        "track2a_small_window_lag6_s42/ai_assisted_eval/track2a_ai_assisted_repetition.csv",
        "track2b_large_window_lag12_s42/ai_assisted_eval/track2b_ai_assisted_quality.csv",
        "track2b_large_window_lag12_s42/ai_assisted_eval/track2b_ai_assisted_factual_semantic.csv",
        "track2b_large_window_lag12_s42/ai_assisted_eval/track2b_ai_assisted_repetition.csv",
        "combined_track2_ai_assisted_eval/track2_ai_assisted_summary.json",
        "combined_track2_ai_assisted_eval/track2_final_evaluation_README.md",
    ]:
        fp = fb_dir / rel
        if fp.is_file():
            ai_hashes[rel] = {
                "sha256": _sha256_file(fp),
                "provenance": AI_EVAL_PROVENANCE,
            }

    payload = {
        "experiment_id": "P06-E01",
        "final_research_decision": "CHANGE",
        "closure_status": {
            "research_execution_reduced_scope": "COMPLETE",
            "ai_assisted_evaluation": "COMPLETE",
            "human_blind_evaluation": "PENDING",
            "human_calibration": "DEFERRED / PENDING",
            "gold_factual_assessment": "PENDING",
            "overall_acceptance_gate": "NOT_EVALUATED",
            "research_decision": "CHANGE",
            "production_validation": "NOT VALIDATED",
            "additional_e01_benchmark": "NOT REQUIRED under approved scope",
        },
        "git_context": git_info,
        "gitignore_raw_runs_notice": "Thư mục `runs/*/*` nằm trong `.gitignore` của P06 nên toàn bộ raw run logs & `ai_assisted_eval/` KHÔNG được lưu trực tiếp trong Git commit.",
        "model_locked": "gemini-3.5-flash-lite (Free Tier, 0 USD, SYNTHETIC only)",
        "prompt_versions": {"story_planner.txt": "v0.1", "story_generation.txt": "v0.2.1", "rewrite.txt": "v0.2.1", "baseline_upfront": "baseline-script-first-v0.2.2"},
        "dataset_versions": {"e01_ext_v1": "1.0.1 / 1.0.2", "e01_formal_v1": "1.1.1"},
        "locked_source_sha256": locked_hashes,
        "formal_batches": [
            {
                "batch_code": m["batch_code"],
                "batch_dir": f"runs/P06-E01/formal_benchmark_v1/{m['batch_dir']}",
                "yaml_global_cap": m["yaml_global_cap"],
                "operational_global_cap": m["operational_global_cap"],
                "total_requests_used": int(_read_json(fb_dir / m["batch_dir"] / "budget_ledger.json")["total_requests"]),
                "budget_ledger_sha256": _sha256_file(fb_dir / m["batch_dir"] / "budget_ledger.json"),
                "operational_cap_note": (
                    "User approved operational cap <= 200 applied at ledger initialization without altering locked YAML (cap 400)."
                    if m["batch_code"] == "2B"
                    else "Matches locked YAML cap."
                ),
            }
            for m in _batch_metadata()
        ],
        "formal_run_ids": runs_df[["batch_code", "full_label", "run_id", "requests_attempted", "termination_reason"]].to_dict(orient="records"),
        "ai_assisted_eval_hashes": ai_hashes,
        "deliverables": {
            "notebook": "notebooks/E01/06_e01_results_analysis.ipynb",
            "analysis_utility": "notebooks/E01/e01_analysis_utils.py",
            "research_report": "reports/E01/p06_e01_research_report.md",
            "signoff_doc": "docs/E01/18-e01-t09-final-research-report-and-signoff.md",
            "tables": {k: str(v.relative_to(p06_root)).replace("\\", "/") for k, v in table_paths.items()},
            "figures": {k: str(v.relative_to(p06_root)).replace("\\", "/") for k, v in figure_paths.items()},
        },
        "path_migration_mapping": {
            "docs/03..18-*.md": "docs/E01/03..18-*.md",
            "notebooks/06_e01_results_analysis.ipynb": "notebooks/E01/06_e01_results_analysis.ipynb",
            "notebooks/e01_analysis_utils.py": "notebooks/E01/e01_analysis_utils.py",
            "reports/p06_e01_research_report.md": "reports/E01/p06_e01_research_report.md",
            "reports/e01_artifact_index.json": "reports/E01/e01_artifact_index.json",
            "reports/tables/*.csv": "reports/tables/E01/*.csv",
            "reports/figures/*.png": "reports/figures/E01/*.png",
        },
    }
    out_p = p06_root / "reports" / "E01" / "e01_artifact_index.json"
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_p
