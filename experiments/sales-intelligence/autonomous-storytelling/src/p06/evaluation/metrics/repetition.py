"""Nhóm chỉ số chống lặp bề mặt, lặp theo cửa sổ `W` và độ đa dạng từ vựng cho P06 (`p06.evaluation.metrics.repetition`).

1. File này giải quyết vấn đề gì?
   Đo lường khách quan hiện tượng phát lại chunk, lặp nguyên văn, lặp bề mặt từ vựng/3-gram
   trên TOÀN BỘ transcript đã phát (khác với `RepetitionDetector` chỉ kiểm tra trong cửa sổ `W`),
   qua đó đánh giá hiệu quả của `W ∈ {5, 10, 20}` và phát hiện lỗi quên ngoài cửa sổ `W`.
2. Trách nhiệm chính của module là gì?
   Tái sử dụng hàm chuẩn hóa tiếng Việt và tách shingle từ `p06.memory.repetition_detector`
   để tính nhóm chỉ số lặp chính xác, Jaccard toàn phiên, Jaccard theo cửa sổ `w ∈ {5, 10, 20}`,
   tỷ lệ lặp claim cùng SKU, `distinct_1/2/3`, và placeholder chấm người thật.
3. Module này liên kết với các thành phần nào?
   Tái sử dụng `normalize_vietnamese_for_repetition`, `_extract_word_shingles`, `_jaccard_similarity`
   từ `p06.memory.repetition_detector`, `compute_percentile` từ `p06.evaluation.metrics.performance`,
   và `_deduplicated_completed_events` để lọc đúng transcript đã phát.
4. Input và output chính là gì?
   Input là `RunEvidence` và `lookback_windows=(5, 10, 20)`; Output là `dict[str, MetricResult]`.
5. Có những constraints hoặc invariants quan trọng nào?
   - Chỉ đánh giá trên các lượt đã thực sự phát thành công (`transcript` khớp ACK hợp lệ).
   - `exact_chunk_replay_count` là Hard Gate (`== 0`).
   - `lexical_repetition_rate` sử dụng ngưỡng `TO VALIDATE` (`word_jaccard >= 0.65` hoặc `ngram3_jaccard >= 0.45`)
     và chỉ đo trùng bề mặt từ vựng, KHÔNG đồng nghĩa phát hiện lặp ngữ nghĩa (paraphrase).
"""

from __future__ import annotations

from p06.evaluation.metrics.performance import (
    _deduplicated_completed_events,
    compute_percentile,
)
from p06.evaluation.models import (
    MetricProvenance,
    MetricResult,
    MetricStatus,
    RunEvidence,
    TranscriptEntry,
)
from p06.memory.repetition_detector import (
    _extract_word_shingles,
    _jaccard_similarity,
    normalize_vietnamese_for_repetition,
)

_LEXICAL_WORD_JACCARD_THRESHOLD = 0.65
_LEXICAL_NGRAM3_JACCARD_THRESHOLD = 0.45
_CLAIM_OVERLAP_THRESHOLD = 0.80


def _accepted_transcript_entries(evidence: RunEvidence) -> list[TranscriptEntry]:
    """Lấy danh sách `TranscriptEntry` đã phát hợp lệ theo thứ tự `turn_index`."""
    if not evidence.transcript:
        return []
    ordered = sorted(evidence.transcript, key=lambda item: item.turn_index)
    if not evidence.playback_events:
        return ordered
    accepted_turn_ids = {
        ev.turn_id for ev in _deduplicated_completed_events(evidence.playback_events)
    }
    rejected_only_turn_ids = {
        ev.turn_id for ev in evidence.playback_events if ev.turn_id not in accepted_turn_ids
    }
    return [entry for entry in ordered if entry.turn_id not in rejected_only_turn_ids]


def _extract_turn_ngrams(words: list[str], n: int) -> list[tuple[str, ...]]:
    """Trích xuất danh sách `n`-gram liên tiếp trong một lượt thoại (không nối chéo ranh giới lượt)."""
    if len(words) < n:
        return []
    return [tuple(words[idx : idx + n]) for idx in range(len(words) - n + 1)]


def compute_repetition_metrics(
    evidence: RunEvidence,
    *,
    lookback_windows: tuple[int, ...] = (5, 10, 20),
) -> dict[str, MetricResult]:
    """Tính toàn bộ nhóm chỉ số chống lặp và đa dạng ngôn từ trên transcript đã phát.

    Công thức chính:
    1. `exact_chunk_replay_count = len(chunk_ids) - len(set(chunk_ids))` (bỏ qua `chunk_id is None`).
       - Hard Gate: Bắt buộc bằng `0`.
    2. `exact_normalized_text_replay_count`: Số lượt `i >= 1` có văn bản chuẩn hóa
       `normalize_vietnamese_for_repetition(t_i)` xuất hiện trong `0..i-1`.
    3. `outside_window_exact_text_replay_count`: Với `W = manifest.get("history_window")`:
       Nếu `W` là số nguyên dương, đếm số lượt `i >= 1` có văn bản chuẩn hóa khớp với một lượt
       `j < i - W` và KHÔNG xuất hiện trong cửa sổ `[max(0, i - W), i)`.
       - Trường hợp biên: `W is None` (ví dụ `script_first`) -> `NOT_APPLICABLE` (`value=None`).
    4. Các chỉ số Jaccard theo cặp (khi `len(transcript) >= 2`, ngược lại `NOT_EVALUATED`):
       - Với mỗi `i in 1..N-1`:
         `w_i = max_{0 <= j < i} Jaccard(words_i, words_j)`,
         `g3_i = max_{0 <= j < i} Jaccard(shingles3_i, shingles3_j)`.
       - Tính `mean`, `p95`, `max` cho cả Word Jaccard và 3-gram Jaccard.
       - `windowed_ngram3_jaccard_mean_w{w_eval}`: Trung bình `max_{max(0, i-w_eval) <= j < i} Jaccard_3(i, j)`.
       - `lexical_repetition_rate`: Tỷ lệ lượt `i >= 1` có `w_i >= 0.65` hoặc `g3_i >= 0.45` (`TO VALIDATE`).
    5. `claim_overlap_rate`: Trên các lượt `i >= 1` có `covered_claim_ids` khác rỗng, tỷ lệ lượt có
       ít nhất một lượt trước `j < i` cùng `sku_id` đạt `|C_i ∩ C_j| / |C_i| >= 0.80`.
       - Trường hợp biên: Không có lượt nào gắn `covered_claim_ids` ở `i >= 1` -> `NOT_EVALUATED`.
    6. `distinct_1`, `distinct_2`, `distinct_3`: `|unique n-grams| / |total n-grams|` trên toàn transcript.
       - Trường hợp biên: Tổng n-gram bằng `0` -> `NOT_EVALUATED`.
    7. `human_unnecessary_semantic_repetition`: Luôn là `NOT_EVALUATED` (`value=None`) chờ T09.

    Ví dụ tính tay:
        3 lượt văn bản giống nhau từng cặp ở lượt 0 và lượt 2 (`"mật ong ngon lắm bạn ơi"`,
        `"trà shan tuyết cổ thụ hà giang"`, `"mật ong ngon lắm bạn ơi"`), `W = 1`:
        `exact_normalized_text_replay_count = 1`, `outside_window_exact_text_replay_count = 1`
        (vì `i=2, i-W=1`, khớp `j=0 < 1` và không khớp `[1, 2)`).

    Args:
        evidence: Tập bằng chứng thô của lần chạy.
        lookback_windows: Các kích thước cửa sổ đánh giá hồi cứu (mặc định `(5, 10, 20)`).

    Returns:
        dict[str, MetricResult]: Từ điển các chỉ số lặp và đa dạng ngôn từ.
    """
    results: dict[str, MetricResult] = {}
    transcript = _accepted_transcript_entries(evidence)

    # 1. Đếm phát lại nguyên chunk_id (Hard Gate)
    if transcript:
        chunk_ids = [entry.chunk_id for entry in transcript if entry.chunk_id is not None]
        chunk_source = "transcript"
    else:
        accepted_events = _deduplicated_completed_events(evidence.playback_events)
        chunk_ids = [ev.chunk_id for ev in accepted_events if ev.chunk_id is not None]
        chunk_source = "playback_events"

    exact_chunk_replays = len(chunk_ids) - len(set(chunk_ids))
    results["exact_chunk_replay_count"] = MetricResult(
        name="exact_chunk_replay_count",
        status=MetricStatus.COMPUTED,
        value=exact_chunk_replays,
        unit="counts",
        data_source=chunk_source,
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
    )

    # Chuẩn hóa từng lượt thoại một lần duy nhất để tái sử dụng cho mọi phép đo bề mặt.
    normalized_texts = [normalize_vietnamese_for_repetition(entry.text) for entry in transcript]
    words_per_turn = [norm.split() for norm in normalized_texts]
    word_sets = [frozenset(words) for words in words_per_turn]
    ngram3_sets = [_extract_word_shingles(words, 3) for words in words_per_turn]

    # 2. Lặp nguyên văn chuẩn hóa toàn phiên
    seen_norms: set[str] = set()
    exact_text_replays = 0
    for norm in normalized_texts:
        if norm and norm in seen_norms:
            exact_text_replays += 1
        if norm:
            seen_norms.add(norm)

    results["exact_normalized_text_replay_count"] = MetricResult(
        name="exact_normalized_text_replay_count",
        status=MetricStatus.COMPUTED,
        value=exact_text_replays,
        unit="counts",
        data_source="transcript",
        provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
        is_simulated=False,
    )

    # 3. Lặp nguyên văn nằm ngoài cửa sổ history_window W
    history_window = evidence.manifest.get("history_window")
    if (
        isinstance(history_window, int)
        and not isinstance(history_window, bool)
        and history_window > 0
    ):
        outside_replays = 0
        for idx in range(1, len(normalized_texts)):
            cur = normalized_texts[idx]
            if not cur:
                continue
            cutoff = idx - history_window
            if cutoff <= 0:
                continue
            in_window = any(
                normalized_texts[j] == cur for j in range(max(0, cutoff), idx)
            )
            before_window = any(normalized_texts[j] == cur for j in range(0, cutoff))
            if before_window and not in_window:
                outside_replays += 1
        results["outside_window_exact_text_replay_count"] = MetricResult(
            name="outside_window_exact_text_replay_count",
            status=MetricStatus.COMPUTED,
            value=outside_replays,
            unit="counts",
            data_source="transcript+manifest",
            provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
            is_simulated=False,
            metadata={"history_window": history_window},
        )
    else:
        results["outside_window_exact_text_replay_count"] = MetricResult(
            name="outside_window_exact_text_replay_count",
            status=MetricStatus.NOT_APPLICABLE,
            value=None,
            unit="counts",
            data_source="transcript+manifest",
            provenance=MetricProvenance.UNAVAILABLE,
            is_simulated=False,
            missing_reason="history_window is None or not applicable (e.g. script_first baseline).",
        )

    # 4. Chỉ số Jaccard theo cặp toàn phiên & theo cửa sổ hồi cứu
    lexical_limitation = (
        "Thresholds (word>=0.65, ngram3>=0.45) are TO VALIDATE; lexical overlap does not detect pure paraphrases."
    )
    if len(transcript) < 2:
        reason = "Transcript has fewer than 2 played chunks."
        for name in (
            "max_prior_word_jaccard_mean",
            "max_prior_word_jaccard_p95",
            "max_prior_word_jaccard_max",
            "max_prior_ngram3_jaccard_mean",
            "max_prior_ngram3_jaccard_p95",
            "max_prior_ngram3_jaccard_max",
            *(f"windowed_ngram3_jaccard_mean_w{w}" for w in lookback_windows),
            "lexical_repetition_rate",
        ):
            results[name] = MetricResult(
                name=name,
                status=MetricStatus.NOT_EVALUATED,
                value=None,
                unit="ratio",
                data_source="transcript",
                provenance=MetricProvenance.UNAVAILABLE,
                is_simulated=False,
                missing_reason=reason,
                limitations=(lexical_limitation,) if name == "lexical_repetition_rate" else (),
            )
    else:
        max_word_scores: list[float] = []
        max_ngram3_scores: list[float] = []
        windowed_scores: dict[int, list[float]] = {w: [] for w in lookback_windows}
        lexical_rep_count = 0

        for idx in range(1, len(transcript)):
            cur_words = word_sets[idx]
            cur_ngrams = ngram3_sets[idx]

            best_w = max(_jaccard_similarity(cur_words, word_sets[j]) for j in range(0, idx))
            best_g3 = max(
                _jaccard_similarity(cur_ngrams, ngram3_sets[j]) for j in range(0, idx)
            )
            max_word_scores.append(best_w)
            max_ngram3_scores.append(best_g3)

            if (
                best_w >= _LEXICAL_WORD_JACCARD_THRESHOLD
                or best_g3 >= _LEXICAL_NGRAM3_JACCARD_THRESHOLD
            ):
                lexical_rep_count += 1

            for w_eval in lookback_windows:
                start = max(0, idx - w_eval)
                win_best = max(
                    _jaccard_similarity(cur_ngrams, ngram3_sets[j])
                    for j in range(start, idx)
                )
                windowed_scores[w_eval].append(win_best)

        pair_count = len(max_word_scores)
        results["max_prior_word_jaccard_mean"] = MetricResult(
            name="max_prior_word_jaccard_mean",
            status=MetricStatus.COMPUTED,
            value=sum(max_word_scores) / pair_count,
            unit="ratio",
            data_source="transcript",
            provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
            is_simulated=False,
        )
        results["max_prior_word_jaccard_p95"] = MetricResult(
            name="max_prior_word_jaccard_p95",
            status=MetricStatus.COMPUTED,
            value=compute_percentile(max_word_scores, 0.95),
            unit="ratio",
            data_source="transcript",
            provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
            is_simulated=False,
        )
        results["max_prior_word_jaccard_max"] = MetricResult(
            name="max_prior_word_jaccard_max",
            status=MetricStatus.COMPUTED,
            value=max(max_word_scores),
            unit="ratio",
            data_source="transcript",
            provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
            is_simulated=False,
        )
        results["max_prior_ngram3_jaccard_mean"] = MetricResult(
            name="max_prior_ngram3_jaccard_mean",
            status=MetricStatus.COMPUTED,
            value=sum(max_ngram3_scores) / pair_count,
            unit="ratio",
            data_source="transcript",
            provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
            is_simulated=False,
        )
        results["max_prior_ngram3_jaccard_p95"] = MetricResult(
            name="max_prior_ngram3_jaccard_p95",
            status=MetricStatus.COMPUTED,
            value=compute_percentile(max_ngram3_scores, 0.95),
            unit="ratio",
            data_source="transcript",
            provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
            is_simulated=False,
        )
        results["max_prior_ngram3_jaccard_max"] = MetricResult(
            name="max_prior_ngram3_jaccard_max",
            status=MetricStatus.COMPUTED,
            value=max(max_ngram3_scores),
            unit="ratio",
            data_source="transcript",
            provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
            is_simulated=False,
        )
        for w_eval in lookback_windows:
            w_scores = windowed_scores[w_eval]
            metric_name = f"windowed_ngram3_jaccard_mean_w{w_eval}"
            results[metric_name] = MetricResult(
                name=metric_name,
                status=MetricStatus.COMPUTED,
                value=sum(w_scores) / len(w_scores),
                unit="ratio",
                data_source="transcript",
                provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
                is_simulated=False,
                metadata={"lookback_window": w_eval},
            )
        results["lexical_repetition_rate"] = MetricResult(
            name="lexical_repetition_rate",
            status=MetricStatus.COMPUTED,
            value=lexical_rep_count / pair_count,
            unit="ratio",
            numerator=float(lexical_rep_count),
            denominator=float(pair_count),
            data_source="transcript",
            provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
            is_simulated=False,
            limitations=(lexical_limitation,),
        )

    # 5. Tỷ lệ lặp lại claim trên cùng SKU
    eligible_claim_turns = 0
    overlapping_claim_turns = 0
    for idx in range(1, len(transcript)):
        cur_claims = frozenset(transcript[idx].covered_claim_ids)
        if not cur_claims:
            continue
        eligible_claim_turns += 1
        cur_sku = transcript[idx].sku_id
        has_overlap = any(
            (len(cur_claims & frozenset(transcript[j].covered_claim_ids)) / len(cur_claims))
            >= _CLAIM_OVERLAP_THRESHOLD
            for j in range(0, idx)
            if transcript[j].sku_id == cur_sku and transcript[j].covered_claim_ids
        )
        if has_overlap:
            overlapping_claim_turns += 1

    if eligible_claim_turns == 0:
        results["claim_overlap_rate"] = MetricResult(
            name="claim_overlap_rate",
            status=MetricStatus.NOT_EVALUATED,
            value=None,
            unit="ratio",
            data_source="transcript",
            provenance=MetricProvenance.UNAVAILABLE,
            is_simulated=False,
            missing_reason="No turns at index >= 1 have non-empty covered_claim_ids.",
        )
    else:
        results["claim_overlap_rate"] = MetricResult(
            name="claim_overlap_rate",
            status=MetricStatus.COMPUTED,
            value=overlapping_claim_turns / eligible_claim_turns,
            unit="ratio",
            numerator=float(overlapping_claim_turns),
            denominator=float(eligible_claim_turns),
            data_source="transcript",
            provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
            is_simulated=False,
        )

    # 6. Độ đa dạng từ vựng Distinct-1 / Distinct-2 / Distinct-3
    for n in (1, 2, 3):
        all_ngrams: list[tuple[str, ...]] = [
            gram for words in words_per_turn for gram in _extract_turn_ngrams(words, n)
        ]
        metric_name = f"distinct_{n}"
        if not all_ngrams:
            results[metric_name] = MetricResult(
                name=metric_name,
                status=MetricStatus.NOT_EVALUATED,
                value=None,
                unit="ratio",
                data_source="transcript",
                provenance=MetricProvenance.UNAVAILABLE,
                is_simulated=False,
                missing_reason=f"Total {n}-grams in transcript is 0.",
            )
        else:
            unique_count = len(set(all_ngrams))
            results[metric_name] = MetricResult(
                name=metric_name,
                status=MetricStatus.COMPUTED,
                value=unique_count / len(all_ngrams),
                unit="ratio",
                numerator=float(unique_count),
                denominator=float(len(all_ngrams)),
                data_source="transcript",
                provenance=MetricProvenance.DERIVED_FROM_EVIDENCE,
                is_simulated=False,
            )

    # 7. Placeholder chấm lặp ngữ nghĩa bởi người thật
    results["human_unnecessary_semantic_repetition"] = MetricResult(
        name="human_unnecessary_semantic_repetition",
        status=MetricStatus.NOT_EVALUATED,
        value=None,
        unit="score_1_to_5",
        data_source="human_eval_sheet",
        provenance=MetricProvenance.UNAVAILABLE,
        is_simulated=False,
        missing_reason="Requires human blind annotation per human_eval_rubric_v0.1.md (T09).",
    )

    return results
