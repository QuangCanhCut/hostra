"""Tạo định danh lượt chạy, dựng manifest tái lập và lưu 10 tệp artifact (`manifest.py`).

1. File này giải quyết vấn đề gì?
   Bảo đảm mọi lần chạy thí nghiệm P06-E01 đều có đầy đủ siêu dữ liệu môi trường, phiên bản mã,
   SHA-256 dataset/story_plan/prompts, cấu hình mô hình đã làm sạch bí mật, và lưu bất biến
   tất cả 10 tệp bằng chứng xuống đĩa mà không bao giờ ghi đè run cũ.
2. Trách nhiệm chính của module là gì?
   Cung cấp `generate_run_id()`, `build_experiment_manifest()`, `persist_run_artifacts()`,
   cùng các hàm thu thập metadata hệ thống an toàn không dùng thư viện ngoài (`psutil`, v.v.).
3. Module này liên kết với các thành phần nào?
   Sử dụng `compute_prompt_hashes` & `load_prompt_template` (`p06.planning.prompt_loader`),
   `ExperimentRunConfig` & `sanitize_mapping_for_artifact` (`p06.runner.config`),
   `RunEvidence` & `EvaluationReport` (`p06.evaluation.models`), và `VirtualClock` constants.
4. Input và output chính là gì?
   Input là `ExperimentRunConfig`, `RunEvidence`, `EvaluationReport` tùy chọn, `token_usage_summary`;
   Output là `dict[str, Any]` manifest và đường dẫn `output_dir / run_id` chứa đúng 10 tệp chuẩn.
5. Có những constraints hoặc invariants quan trọng nào?
   - Tuyệt đối KHÔNG đọc hoặc ghi `os.environ` hay khóa bí mật (`GEMINI_API_KEY`, v.v.) vào
     `manifest.json` hoặc `config.yaml`.
   - `persist_run_artifacts` tạo thư mục với `exist_ok=False` để cấm ghi đè lịch sử chạy.
   - Băm `dataset_sha256` và `story_plan_sha256` chuẩn hóa kết thúc dòng LF để tái lập đa OS.
"""

from __future__ import annotations

import ctypes
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Optional

import yaml

from p06.evaluation.models import EvaluationReport, RunEvidence
from p06.planning.prompt_loader import DEFAULT_PROMPTS_DIR, compute_prompt_hashes, load_prompt_template
from p06.runner.config import (
    DEFAULT_MODULE_ROOT,
    ExperimentMethod,
    ExperimentRunConfig,
    RunTerminationReason,
    build_sanitized_config_snapshot,
    sanitize_mapping_for_artifact,
)
from p06.schemas.story import CONTRACT_VERSION, StoryPlan
from p06.simulation.virtual_clock import DEFAULT_SPEECH_WORDS_PER_SEC, MIN_SPEECH_DURATION_MS

_SAFE_ID_SEGMENT_RE: Final[re.Pattern[str]] = re.compile(r"[^A-Za-z0-9_-]+")
_TRACKED_PACKAGES: Final[tuple[str, ...]] = ("pydantic", "langgraph", "pyyaml", "pytest")
_BYTES_PER_GIB: Final[int] = 1024**3


def _sanitize_run_segment(value: str) -> str:
    """Chuẩn hóa đoạn chuỗi cho `run_id` chỉ giữ ký tự an toàn trên tên tệp."""
    cleaned = _SAFE_ID_SEGMENT_RE.sub("-", value.strip()).strip("-")
    return cleaned or "unknown"


def generate_run_id(
    experiment_id: str,
    scenario: str,
    method: ExperimentMethod | str,
    history_window: Optional[int],
    *,
    at_utc: Optional[datetime] = None,
) -> str:
    """Sinh mã `run_id` duy nhất, an toàn cho hệ thống tệp, kèm dấu thời gian UTC và UUID ngắn.

    Args:
        experiment_id: Mã thí nghiệm (vd: `P06-E01`).
        scenario: Tên kịch bản (vd: `product_education_10m`).
        method: Phương pháp chạy thực nghiệm.
        history_window: Kích thước cửa sổ `W` (hoặc `None` với baseline).
        at_utc: Mốc UTC tùy chọn phục vụ kiểm thử tất định.

    Returns:
        str: Định danh `run_id` duy nhất không chứa ký tự đặc biệt.
    """
    method_str = method.value if isinstance(method, ExperimentMethod) else str(method)
    ts = (at_utc or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    window_tag = f"w{history_window}" if history_window is not None else "noW"
    short_uuid = uuid.uuid4().hex[:8]
    return (
        f"{_sanitize_run_segment(experiment_id)}__"
        f"{_sanitize_run_segment(scenario)}__"
        f"{_sanitize_run_segment(method_str)}__"
        f"{window_tag}__"
        f"{ts}__{short_uuid}"
    )


def _compute_normalized_file_sha256(file_path: Path) -> str:
    """Tính SHA-256 trên nội dung UTF-8 chuẩn hóa LF để đồng nhất giữa Windows và Linux."""
    raw_text = file_path.read_bytes().decode("utf-8")
    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _compute_combined_dataset_sha256(paths: Sequence[Path]) -> Optional[str]:
    """Tính SHA-256 tổng hợp theo thứ tự xác định cho một hoặc nhiều tệp dữ liệu nguồn."""
    existing = [Path(path) for path in paths if Path(path).is_file()]
    if not existing:
        return None
    hasher = hashlib.sha256()
    for path in sorted(existing, key=lambda item: item.name):
        hasher.update(path.name.encode("utf-8"))
        hasher.update(b"\n")
        hasher.update(_compute_normalized_file_sha256(path).encode("utf-8"))
        hasher.update(b"\n")
    return hasher.hexdigest()


def _compute_story_plan_sha256(story_plan: StoryPlan) -> str:
    """Tính SHA-256 chuẩn tắc của `StoryPlan` sau khi tuần tự hóa khóa sắp xếp."""
    canonical = json.dumps(
        story_plan.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _detect_git_metadata(repo_dir: Path) -> tuple[str, Optional[bool]]:
    """Truy vấn commit hash và trạng thái dirty của git bằng subprocess an toàn."""
    try:
        commit_proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if commit_proc.returncode != 0 or not commit_proc.stdout.strip():
            return "UNKNOWN", None
        commit_hash = commit_proc.stdout.strip()

        status_proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if status_proc.returncode != 0:
            return commit_hash, None
        return commit_hash, bool(status_proc.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN", None


def _collect_package_versions() -> dict[str, Optional[str]]:
    """Thu thập phiên bản các thư viện cốt lõi qua `importlib.metadata`."""
    versions: dict[str, Optional[str]] = {}
    for pkg in _TRACKED_PACKAGES:
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            versions[pkg] = None
    return versions


def _detect_cpu_model() -> str:
    """Lấy thông tin CPU chỉ dùng stdlib `platform` / `os` mà không phụ thuộc gói ngoài."""
    proc = platform.processor().strip()
    machine = platform.machine().strip()
    cores = os.cpu_count()
    parts = [part for part in (proc, machine) if part]
    label = " / ".join(dict.fromkeys(parts)) if parts else "UNKNOWN"
    if cores is not None:
        return f"{label} ({cores} logical cores)"
    return label


class _MemoryStatusEx(ctypes.Structure):
    """Cấu trúc Win32 `MEMORYSTATUSEX` dùng tra cứu dung lượng RAM bằng `ctypes` chuẩn."""

    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _detect_ram_gb() -> Optional[float]:
    """Lấy tổng dung lượng RAM vật lý (GiB) chỉ bằng stdlib, trả `None` nếu hệ thống không hỗ trợ."""
    if hasattr(os, "sysconf"):
        try:
            page_size = os.sysconf("SC_PAGE_SIZE")
            phys_pages = os.sysconf("SC_PHYS_PAGES")
            if isinstance(page_size, int) and isinstance(phys_pages, int) and page_size > 0 and phys_pages > 0:
                return round((page_size * phys_pages) / _BYTES_PER_GIB, 2)
        except (ValueError, OSError):
            pass

    if os.name == "nt":
        try:
            stat = _MemoryStatusEx()
            stat.dwLength = ctypes.sizeof(_MemoryStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):  # type: ignore[attr-defined]
                return round(stat.ullTotalPhys / _BYTES_PER_GIB, 2)
        except (AttributeError, OSError):
            pass

    return None


def _collect_prompt_provenance(
    prompts_dir: Optional[Path],
    extra_prompt_version: Optional[str] = None,
    extra_prompt_sha256: Optional[str] = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Thu thập bảng phiên bản và SHA-256 chuẩn hóa LF cho toàn bộ prompt template."""
    target_dir = (prompts_dir or DEFAULT_PROMPTS_DIR).resolve()
    versions: dict[str, str] = {}
    hashes: dict[str, str] = {}
    if target_dir.is_dir():
        hashes = compute_prompt_hashes(target_dir)
        for filename in sorted(hashes.keys()):
            tmpl = load_prompt_template(filename, prompts_dir=target_dir)
            versions[filename] = tmpl.version

    if extra_prompt_version is not None:
        versions["baseline_script_first"] = extra_prompt_version
    if extra_prompt_sha256 is not None:
        hashes["baseline_script_first"] = extra_prompt_sha256

    return versions, hashes


def build_experiment_manifest(
    *,
    run_id: str,
    config: ExperimentRunConfig,
    story_plan: StoryPlan,
    model_yaml: Mapping[str, Any],
    provider_name: str,
    provider_tier: str,
    model_id: str,
    started_at_utc: datetime,
    finished_at_utc: datetime,
    termination_reason: RunTerminationReason,
    token_usage_summary: Mapping[str, Any],
    planning_latency_ms: float = 0.0,
    upfront_script_generation_latency_ms: float = 0.0,
    total_measured_processing_ms: float = 0.0,
    simulated_elapsed_sec: float = 0.0,
    virtual_clock_start_utc: Optional[datetime] = None,
    dataset_meta: Optional[Mapping[str, Any]] = None,
    dataset_files: Sequence[Path] = (),
    prompts_dir: Optional[Path] = None,
    extra_prompt_version: Optional[str] = None,
    extra_prompt_sha256: Optional[str] = None,
) -> dict[str, Any]:
    """Xây dựng từ điển `manifest.json` đầy đủ trường truy vết tái lập cho một lần chạy.

    Args:
        run_id: Mã lần chạy duy nhất.
        config: Cấu hình chạy thực nghiệm đã kiểm định.
        story_plan: Kế hoạch kể chuyện của lượt chạy.
        model_yaml: Nội dung YAML cấu hình model (sẽ được lọc sạch khóa nhạy cảm).
        provider_name: Tên nhà cung cấp thực tế (`mock`, `ollama`, `gemini`).
        provider_tier: Tầng thực thi (`unit_test`, `local_smoke_test`, `formal_experiment`).
        model_id: Định danh model thực tế.
        started_at_utc: Thời điểm bắt đầu (UTC).
        finished_at_utc: Thời điểm kết thúc (UTC).
        termination_reason: Lý do kết thúc phiên chạy.
        token_usage_summary: Bản tổng hợp từ `EvidenceCollector.build_token_usage_summary()`.
        dataset_meta: Metadata từ `e01_story_plans.json` (tùy chọn).
        dataset_files: Danh sách tệp dữ liệu nguồn dùng để tính `dataset_sha256`.
        prompts_dir: Thư mục chứa prompt template (mặc định `prompts/`).
        extra_prompt_version: Phiên bản prompt inline của baseline (nếu có).
        extra_prompt_sha256: Mã băm prompt inline của baseline (nếu có).

    Returns:
        dict[str, Any]: Từ điển manifest an toàn, sẵn sàng tuần tự hóa JSON.
    """
    git_commit, git_dirty = _detect_git_metadata(DEFAULT_MODULE_ROOT)
    prompt_versions, prompt_hashes = _collect_prompt_provenance(
        prompts_dir,
        extra_prompt_version=extra_prompt_version,
        extra_prompt_sha256=extra_prompt_sha256,
    )
    sanitized_model_cfg = sanitize_mapping_for_artifact(model_yaml)
    raw_sampling = sanitized_model_cfg.get("sampling", {})
    sampling_params = dict(raw_sampling) if isinstance(raw_sampling, Mapping) else {}

    meta_dict = dict(dataset_meta or {})
    dataset_version = str(meta_dict.get("dataset_id", "p06-e01-synthetic-v0.1"))
    dataset_sha256 = _compute_combined_dataset_sha256(dataset_files)
    run_status = "FAILED" if termination_reason == RunTerminationReason.FATAL_ERROR else "COMPLETED"

    manifest: dict[str, Any] = {
        "run_id": run_id,
        "experiment_id": config.experiment_id,
        "method": config.method.value,
        "scenario": config.scenario,
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "python_version": platform.python_version(),
        "package_versions": _collect_package_versions(),
        "cpu_model": _detect_cpu_model(),
        "ram_gb": _detect_ram_gb(),
        "dataset_version": dataset_version,
        "dataset_sha256": dataset_sha256,
        "is_synthetic": bool(story_plan.is_synthetic),
        "story_plan_id": story_plan.plan_id,
        "story_plan_revision": story_plan.plan_revision,
        "story_plan_sha256": _compute_story_plan_sha256(story_plan),
        "prompt_versions": prompt_versions,
        "prompt_hashes": prompt_hashes,
        "provider_name": provider_name,
        "provider_tier": provider_tier,
        "provider_config": sanitized_model_cfg,
        "model_id": model_id,
        "quantization": sanitized_model_cfg.get("quantization"),
        "context_window": sanitized_model_cfg.get("context_window"),
        "sampling_params": sampling_params,
        "seed": config.seed,
        "history_window": config.history_window,
        "repetition_config": config.repetition_config.model_dump(mode="json"),
        "rewrite_budget": (
            config.max_rewrite_retries if config.method == ExperimentMethod.LANGGRAPH else 0
        ),
        "max_chunk_duration_sec": config.max_chunk_duration_sec,
        "simulator_assumptions": {
            "words_per_sec": DEFAULT_SPEECH_WORDS_PER_SEC,
            "min_speech_duration_ms": MIN_SPEECH_DURATION_MS,
            "playback_ack_mode": "simulated_deterministic",
            "target_duration_sec": config.target_duration_sec,
            "max_turns": config.max_turns,
            "max_consecutive_aborts": config.max_consecutive_aborts,
            "virtual_clock_start_utc": (
                virtual_clock_start_utc.astimezone(timezone.utc).isoformat()
                if virtual_clock_start_utc is not None
                else None
            ),
        },
        **(
            {"pricing": dict(sanitized_model_cfg["pricing"])}
            if isinstance(sanitized_model_cfg.get("pricing"), Mapping)
            else {}
        ),
        "contract_version": CONTRACT_VERSION,
        "run_status": run_status,
        "started_at_utc": started_at_utc.astimezone(timezone.utc).isoformat(),
        "finished_at_utc": finished_at_utc.astimezone(timezone.utc).isoformat(),
        "termination_reason": termination_reason.value,
        "planning_latency_ms": float(planning_latency_ms),
        "upfront_script_generation_latency_ms": float(upfront_script_generation_latency_ms),
        "total_measured_processing_ms": float(total_measured_processing_ms),
        "simulated_elapsed_sec": float(simulated_elapsed_sec),
        "target_duration_sec": float(config.target_duration_sec),
        "metric_provenance": {
            "simulated_clock": "SIMULATED_CLOCK",
            "processing_latency": "MEASURED_WALL_CLOCK",
            "token_usage": str(token_usage_summary.get("token_usage_source", "UNAVAILABLE")),
            "provider_tier": provider_tier,
        },
    }
    return sanitize_mapping_for_artifact(manifest)


def _write_json_file(path: Path, payload: Any) -> None:
    """Ghi đối tượng JSON với thụt lề chuẩn và UTF-8."""
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_jsonl_file(path: Path, records: Sequence[Any]) -> None:
    """Ghi danh sách Pydantic model hoặc dict thành tệp JSONL chuẩn UTF-8."""
    lines: list[str] = []
    for item in records:
        data = item.model_dump(mode="json") if hasattr(item, "model_dump") else item
        lines.append(json.dumps(data, ensure_ascii=False))
    content = ("\n".join(lines) + "\n") if lines else ""
    path.write_text(content, encoding="utf-8")


def persist_run_artifacts(
    *,
    output_dir: Path,
    run_id: str,
    manifest: Mapping[str, Any],
    config: ExperimentRunConfig,
    model_yaml: Mapping[str, Any],
    evidence: RunEvidence,
    report: Optional[EvaluationReport],
    token_usage_summary: Mapping[str, Any],
) -> Path:
    """Tạo thư mục `output_dir / run_id` (cấm ghi đè) và ghi đầy đủ 10 tệp artifact.

    Args:
        output_dir: Thư mục gốc chứa các lượt chạy.
        run_id: Mã lần chạy duy nhất dùng làm tên thư mục con.
        manifest: Từ điển `manifest.json` đã hoàn chỉnh.
        config: Cấu hình chạy thực nghiệm.
        model_yaml: Cấu hình model YAML gốc (sẽ được làm sạch trước khi ghi `config.yaml`).
        evidence: Toàn bộ bằng chứng thô `RunEvidence`.
        report: Báo cáo đánh giá `EvaluationReport` (hoặc `None` nếu chưa chạy evaluator).
        token_usage_summary: Tóm tắt tiêu thụ token cho `token_usage.json`.

    Returns:
        Path: Đường dẫn tuyệt đối tới thư mục chứa 10 tệp artifact vừa tạo.

    Raises:
        FileExistsError: Nếu thư mục `output_dir / run_id` đã tồn tại trước đó.
    """
    base_dir = Path(output_dir).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    run_dir = base_dir / run_id
    # Tuyệt đối không ghi đè thư mục run cũ để bảo toàn tính bất biến lịch sử thực nghiệm.
    run_dir.mkdir(parents=False, exist_ok=False)

    _write_json_file(run_dir / "manifest.json", sanitize_mapping_for_artifact(manifest))

    config_snapshot = build_sanitized_config_snapshot(config, model_yaml)
    (run_dir / "config.yaml").write_text(
        yaml.safe_dump(config_snapshot, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    _write_json_file(run_dir / "story_plan.json", evidence.story_plan.model_dump(mode="json"))
    _write_jsonl_file(run_dir / "transcript.jsonl", evidence.transcript)
    _write_jsonl_file(run_dir / "playback_events.jsonl", evidence.playback_events)
    _write_jsonl_file(run_dir / "graph_trace.jsonl", evidence.graph_traces)
    _write_jsonl_file(run_dir / "provider_calls.jsonl", evidence.provider_calls)

    metrics_payload: Any = (
        report.model_dump(mode="json")
        if report is not None
        else {
            "status": "NOT_EVALUATED",
            "reason": "No evaluator provided or evaluation module unavailable.",
        }
    )
    _write_json_file(run_dir / "metrics.json", metrics_payload)
    _write_json_file(run_dir / "token_usage.json", dict(token_usage_summary))
    _write_jsonl_file(run_dir / "errors.jsonl", evidence.errors)

    return run_dir
