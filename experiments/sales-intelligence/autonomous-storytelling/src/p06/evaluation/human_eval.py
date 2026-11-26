"""Trình xuất phiếu chấm mù cho người đánh giá (`human_eval_rubric_v0.1.md`) (`p06.evaluation.human_eval`).

1. File này giải quyết vấn đề gì?
   Sinh bộ phiếu chấm mù (`blind_eval_sheet.csv` và `blind_eval_sheet.jsonl`) kèm bảng giải mã bí mật
   (`blind_key_mapping.private.json`) từ các thư mục lần chạy để chuẩn bị cho Pilot Calibration và
   Human Blind QA (T09), bảo đảm người chấm không biết phương pháp, model hay kích thước cửa sổ `W`.
2. Trách nhiệm chính của module là gì?
   Cung cấp hàm `export_blind_human_eval_sheets(run_dirs, output_dir, *, seed=42)` xáo trộn tất định
   mã định danh ẩn danh (`METHOD_A`, `METHOD_B`, ...) và thứ tự mẫu (`SAMPLE_001`, ...).
3. Module này liên kết với các thành phần nào?
   Sử dụng `load_run_evidence()` (`p06.evaluation.evaluator`), `_accepted_transcript_entries()`
   (`p06.evaluation.metrics.repetition`), và xuất `HumanEvalSheetEntry`, `HumanEvalBlindMapping`
   (`p06.evaluation.models`).
4. Input và output chính là gì?
   Input là danh sách `run_dirs`, `output_dir`, và `seed`;
   Output là bộ 3 đường dẫn `(csv_path, jsonl_path, mapping_path)`.
5. Có những constraints hoặc invariants quan trọng nào?
   - Phiếu chấm mù TUYỆT ĐỐI KHÔNG rò rỉ `run_id`, `method`, `model_id`, `provider_name`, `provider_tier`
     hay `history_window` (`W`).
   - Toàn bộ 6 điểm tiêu chí rubric và `hard_constraint_violation` bắt buộc để trống (`None`),
     cấm điền sẵn điểm giả lập.
"""

from __future__ import annotations

import csv
import json
import random
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from p06.evaluation.evaluator import load_run_evidence
from p06.evaluation.metrics.repetition import _accepted_transcript_entries
from p06.evaluation.models import (
    HumanEvalBlindMapping,
    HumanEvalSheetEntry,
    RunEvidence,
)


def _blind_label_for_index(idx: int) -> str:
    """Sinh nhãn ẩn danh dạng `METHOD_A`..`METHOD_Z`, `METHOD_AA`.. theo chỉ số."""
    if idx < 26:
        return f"METHOD_{chr(ord('A') + idx)}"
    first = idx // 26 - 1
    second = idx % 26
    return f"METHOD_{chr(ord('A') + first)}{chr(ord('A') + second)}"


def export_blind_human_eval_sheets(
    run_dirs: Sequence[Path],
    output_dir: Path,
    *,
    seed: int = 42,
) -> tuple[Path, Path, Path]:
    """Xuất phiếu chấm mù CSV/JSONL và bảng ánh xạ bí mật từ danh sách thư mục lần chạy.

    Args:
        run_dirs: Danh sách thư mục run cần đưa vào lô chấm mù.
        output_dir: Thư mục đích để lưu 3 tệp xuất ra.
        seed: Hạt giống ngẫu nhiên tất định dùng để xáo trộn nhãn `METHOD_*` và thứ tự mẫu.

    Returns:
        tuple[Path, Path, Path]: Bộ `(csv_path, jsonl_path, mapping_path)`.

    Raises:
        ValueError: Nếu `run_dirs` rỗng hoặc có thư mục run không hợp lệ.
    """
    if not run_dirs:
        raise ValueError("run_dirs không được rỗng khi gọi export_blind_human_eval_sheets().")

    loaded_runs: list[RunEvidence] = [load_run_evidence(Path(d)) for d in run_dirs]

    # Nhóm theo cấu hình thực (method, provider_tier, provider_name, model_id, history_window)
    # để cùng một cấu hình nhận chung một `blind_method_id`, rồi xáo trộn bằng seed.
    config_keys: list[tuple[str, str, str, str, int | None]] = []
    seen_configs: set[tuple[str, str, str, str, int | None]] = set()
    for ev in loaded_runs:
        manifest = ev.manifest
        cfg_key = (
            str(manifest["method"]).strip(),
            str(manifest["provider_tier"]).strip(),
            str(manifest["provider_name"]).strip(),
            str(manifest["model_id"]).strip(),
            manifest.get("history_window"),
        )
        if cfg_key not in seen_configs:
            seen_configs.add(cfg_key)
            config_keys.append(cfg_key)

    rng = random.Random(seed)
    shuffled_configs = list(config_keys)
    rng.shuffle(shuffled_configs)
    config_to_blind = {
        cfg: _blind_label_for_index(idx) for idx, cfg in enumerate(shuffled_configs)
    }

    # Xáo trộn thứ tự các mẫu trước khi cấp `SAMPLE_001`, ... để không lộ thứ tự thư mục vào.
    indexed_runs = list(enumerate(loaded_runs))
    rng.shuffle(indexed_runs)

    entries: list[HumanEvalSheetEntry] = []
    mappings: list[HumanEvalBlindMapping] = []

    for sample_num, (_, ev) in enumerate(indexed_runs, start=1):
        manifest = ev.manifest
        cfg_key = (
            str(manifest["method"]).strip(),
            str(manifest["provider_tier"]).strip(),
            str(manifest["provider_name"]).strip(),
            str(manifest["model_id"]).strip(),
            manifest.get("history_window"),
        )
        blind_method_id = config_to_blind[cfg_key]
        sample_id = f"SAMPLE_{sample_num:03d}"

        accepted_transcript = _accepted_transcript_entries(ev)
        if accepted_transcript:
            transcript_text = "\n\n".join(
                f"[{idx + 1}] {entry.text}" for idx, entry in enumerate(accepted_transcript)
            )
        else:
            transcript_text = "[NO_TRANSCRIPT_RECORDED]"

        entries.append(
            HumanEvalSheetEntry(
                sample_id=sample_id,
                blind_method_id=blind_method_id,
                experiment_id=str(manifest["experiment_id"]).strip(),
                scenario=str(manifest["scenario"]).strip(),
                transcript_text=transcript_text,
                evaluator_id=None,
                narrative_coherence=None,
                naturalness=None,
                persuasiveness=None,
                context_relevance=None,
                transition_quality=None,
                repetition_quality=None,
                hard_constraint_violation=None,
                violation_notes="",
                overall_notes="",
            )
        )
        mappings.append(
            HumanEvalBlindMapping(
                sample_id=sample_id,
                blind_method_id=blind_method_id,
                run_id=str(manifest["run_id"]).strip(),
                method=cfg_key[0],
                provider_tier=cfg_key[1],
                provider_name=cfg_key[2],
                model_id=cfg_key[3],
                history_window=cfg_key[4],
                scenario=str(manifest["scenario"]).strip(),
            )
        )

    dest_dir = Path(output_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    csv_path = dest_dir / "blind_eval_sheet.csv"
    jsonl_path = dest_dir / "blind_eval_sheet.jsonl"
    mapping_path = dest_dir / "blind_key_mapping.private.json"

    fieldnames = list(HumanEvalSheetEntry.model_fields.keys())
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for entry in entries:
            row_dict: dict[str, Any] = entry.model_dump(mode="json")
            writer.writerow(row_dict)

    jsonl_lines = [entry.model_dump_json() for entry in entries]
    jsonl_path.write_text("\n".join(jsonl_lines) + "\n", encoding="utf-8")

    mapping_payload = [m.model_dump(mode="json") for m in mappings]
    mapping_path.write_text(
        json.dumps(mapping_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return csv_path, jsonl_path, mapping_path


# Tên bí danh tương thích với tầng điều phối sweep (`p06.runner.sweep`).
export_human_eval_sheets = export_blind_human_eval_sheets

