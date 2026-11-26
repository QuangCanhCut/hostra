"""Bộ phát hiện lặp ý và trùng lặp ngôn từ (`RepetitionDetector`) thuần trạng thái (stateless) cho P06.

1. File này giải quyết vấn đề gì?
   Giảm rủi ro lặp nội dung (`R05`) trong phiên livestream kéo dài 10–30 phút bằng cách phân biệt
   rạch ròi giữa phát lại nguyên xi (`EXACT_REPLAY`), trùng lặp bề mặt câu chữ (`LEXICAL_DUPLICATION`),
   nhai lại cùng dữ kiện (`REPEATED_FACTS`) với trường hợp triển khai tiếp ý mới trên cùng chủ đề
   (`LEGITIMATE_CONTINUATION`).
2. Trách nhiệm chính của module là gì?
   Chuẩn hóa văn bản tiếng Việt (Unicode NFC, chữ thường, bỏ dấu câu, gộp khoảng trắng),
   tính các chỉ số Word Jaccard, N-gram Jaccard (`n=3`), Fact Overlap Ratio, và phân loại 5 trạng thái
   kèm khuyến nghị hành động (`ALLOW`, `REWRITE`, `SWITCH_TOPIC`).
3. Module này liên kết với các thành phần nào?
   Tiêu thụ chuỗi `PlayedTurnSummary` từ `ShortTermPlayedHistory` (`p06.memory.played_history`)
   và `p06.schemas.state`; cung cấp tín hiệu đầu vào cho LangGraph nodes (`agent/nodes/`) và
   metric đánh giá chống lặp trong `evaluation/metrics/`.
4. Input và output chính là gì?
   Input là `candidate_text`, danh sách `played_turns`, tùy chọn `candidate_chunk_id`, `topic_id`,
   `sku_id`, `intent`, `candidate_claim_ids`, `played_chunk_ids`;
   Output là `RepetitionCheckResult` bất biến không làm thay đổi bất kỳ trạng thái nào bên ngoài.
5. Có những constraints hoặc invariants quan trọng nào?
   - `check()` phải thuần hàm / stateless (không tự lưu cache hay ghi vào `played_history`).
   - Mọi ngưỡng số trong `RepetitionConfig` đều mang nhãn `TO VALIDATE` cho đến khi có dữ liệu
     thực nghiệm chứng minh trên người thật (`P06-OPEN-2`).
   - Jaccard bề mặt không phát hiện được paraphrase hoàn toàn khác từ vựng nếu không gắn `claim_id`.
"""

from __future__ import annotations

import math
import unicodedata
from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from enum import Enum
from typing import Annotated, Any, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictBool

from p06.schemas.state import PlayedTurnSummary
from p06.schemas.story import NonBlankStr, OptionalNonBlankStr, StrictPositiveInt


def _validate_open_zero_unit_float(value: Any) -> float:
    """Kiểm định ngưỡng tỷ lệ nằm trong `(0.0, 1.0]` và từ chối kiểu `bool`."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"Ngưỡng tỷ lệ phải là số thực trong (0.0, 1.0], nhận được {type(value).__name__}."
        )
    numeric = float(value)
    if not math.isfinite(numeric) or not (0.0 < numeric <= 1.0):
        raise ValueError(f"Ngưỡng tỷ lệ phải nằm trong (0.0, 1.0], nhận được {value!r}.")
    return numeric


def _validate_closed_unit_float(value: Any) -> float:
    """Kiểm định chỉ số đo nằm trong `[0.0, 1.0]` và từ chối kiểu `bool`."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"Chỉ số đo phải là số thực trong [0.0, 1.0], nhận được {type(value).__name__}."
        )
    numeric = float(value)
    if not math.isfinite(numeric) or not (0.0 <= numeric <= 1.0):
        raise ValueError(f"Chỉ số đo phải nằm trong [0.0, 1.0], nhận được {value!r}.")
    return numeric


StrictThresholdRatio = Annotated[float, BeforeValidator(_validate_open_zero_unit_float)]
StrictUnitScore = Annotated[float, BeforeValidator(_validate_closed_unit_float)]


class RepetitionCategory(str, Enum):
    """Phân loại mức độ lặp của ứng viên lời thoại so với lịch sử đã phát.

    Attributes:
        NONE: Không phát hiện trùng lặp đáng kể.
        EXACT_REPLAY: Trùng `chunk_id` đã phát hoặc trùng nguyên văn bản chuẩn hóa.
        LEXICAL_DUPLICATION: Trùng lặp bề mặt từ vựng/cụm từ vượt ngưỡng Jaccard.
        REPEATED_FACTS: Lặp lại cùng nhóm `claim_id` trên cùng `intent` (và `sku_id`).
        LEGITIMATE_CONTINUATION: Cùng chủ đề đang nói nhưng mở rộng ý/claim mới với từ ngữ mới.
    """

    NONE = "NONE"
    EXACT_REPLAY = "EXACT_REPLAY"
    LEXICAL_DUPLICATION = "LEXICAL_DUPLICATION"
    REPEATED_FACTS = "REPEATED_FACTS"
    LEGITIMATE_CONTINUATION = "LEGITIMATE_CONTINUATION"


class RepetitionAction(str, Enum):
    """Hành động khuyến nghị cho điều phối viên hoặc node viết lại trong LangGraph.

    Attributes:
        ALLOW: Cho phép đi tiếp qua cổng P05 và phát sóng.
        REWRITE: Yêu cầu viết lại câu chữ khác (tiêu thụ 1 lượt trong `RewriteBudgetState`).
        SWITCH_TOPIC: Yêu cầu chuyển sang chủ đề/arc khác vì chunk hoặc nhóm sự thật đã phát rồi.
    """

    ALLOW = "ALLOW"
    REWRITE = "REWRITE"
    SWITCH_TOPIC = "SWITCH_TOPIC"


class RepetitionConfig(BaseModel):
    """Cấu hình các ngưỡng kiểm tra lặp cho `RepetitionDetector`.

    Lưu ý khoa học (`TO VALIDATE`): Toàn bộ các ngưỡng mặc định dưới đây là giá trị khởi điểm
    cho PoC Stage 03 (`TO VALIDATE`), chưa phải ngưỡng tối ưu đã kiểm chứng trên đánh giá người thật.

    Attributes:
        word_jaccard_threshold: (`TO VALIDATE`, mặc định `0.65`) Ngưỡng Word Jaccard `(0, 1]`
            để kết luận `LEXICAL_DUPLICATION`.
        ngram_size: Kích thước cửa sổ từ N-gram (mặc định `3`, >= 1).
        ngram_jaccard_threshold: (`TO VALIDATE`, mặc định `0.45`) Ngưỡng N-gram Jaccard `(0, 1]`
            để bắt trùng cụm từ liên tiếp.
        fact_overlap_threshold: (`TO VALIDATE`, mặc định `0.80`) Ngưỡng tỷ lệ trùng `claim_id`
            `|cand ∩ played| / |cand|` cho `REPEATED_FACTS`.
        continuation_lexical_ceiling: (`TO VALIDATE`, mặc định `0.40`) Trần Word Jaccard tối đa
            để một lượt cùng chủ đề được công nhận là `LEGITIMATE_CONTINUATION`.
        max_recent_turns_to_check: Giới hạn số lượt gần nhất dùng để so khớp (hoặc `None` để quét hết).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    word_jaccard_threshold: StrictThresholdRatio = 0.65
    ngram_size: StrictPositiveInt = 3
    ngram_jaccard_threshold: StrictThresholdRatio = 0.45
    fact_overlap_threshold: StrictThresholdRatio = 0.80
    continuation_lexical_ceiling: StrictThresholdRatio = 0.40
    max_recent_turns_to_check: Optional[StrictPositiveInt] = None


class RepetitionCheckResult(BaseModel):
    """Kết quả bất biến từ một lần kiểm tra chống lặp của `RepetitionDetector`.

    Attributes:
        is_repetitive: `True` nếu phát hiện lặp cần chặn/viết lại/chuyển chủ đề.
        category: Phân loại lặp theo 5 nhóm `RepetitionCategory`.
        recommended_action: Hành động khuyến nghị (`ALLOW`, `REWRITE`, `SWITCH_TOPIC`).
        word_jaccard: Điểm Word Jaccard lớn nhất đo được trên tập lượt đối chiếu `[0.0, 1.0]`.
        ngram_jaccard: Điểm N-gram Jaccard lớn nhất đo được `[0.0, 1.0]`.
        fact_overlap_ratio: Tỷ lệ trùng lặp `claim_id` lớn nhất đo được `[0.0, 1.0]`.
        matched_turn_id: `turn_id` khớp cao nhất gây ra cảnh báo (hoặc tham chiếu continuation).
        matched_chunk_id: `chunk_id` liên quan (nếu có).
        reasons: Danh sách giải thích ngắn gọn phục vụ audit/log và prompt rewrite.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    is_repetitive: StrictBool
    category: RepetitionCategory
    recommended_action: RepetitionAction
    word_jaccard: StrictUnitScore
    ngram_jaccard: StrictUnitScore
    fact_overlap_ratio: StrictUnitScore
    matched_turn_id: OptionalNonBlankStr = None
    matched_chunk_id: OptionalNonBlankStr = None
    reasons: tuple[NonBlankStr, ...] = Field(default_factory=tuple)


def normalize_vietnamese_for_repetition(text: str) -> str:
    """Chuẩn hóa câu tiếng Việt để so sánh bề mặt từ vựng nhất quán.

    Quy trình 4 bước tất định:
    1. Chuẩn hóa Unicode về dạng dựng sẵn `NFC` (tránh sai khác giữa dấu tổ hợp NFD và NFC).
    2. Đưa toàn bộ ký tự về chữ thường (`lower()`).
    3. Thay thế mọi ký tự thuộc nhóm dấu câu Unicode (`unicodedata.category(ch).startswith("P")`)
       bằng khoảng trắng để tránh dính hai từ cạnh nhau (ví dụ `"ngon,bổ"` -> `"ngon bổ"`).
    4. Gộp nhiều khoảng trắng liên tiếp thành một dấu cách duy nhất và cắt hai đầu.

    Ví dụ tiếng Việt:
    - `"Mật ong hoa cà phê Đắk Lắk, chai 500ml!"` -> `"mật ong hoa cà phê đắk lắk chai 500ml"`

    Args:
        text: Chuỗi văn bản đầu vào.

    Returns:
        str: Chuỗi đã chuẩn hóa (có thể rỗng nếu đầu vào chỉ gồm dấu câu/khoảng trắng).

    Raises:
        TypeError: Nếu `text` không phải `str`.
    """
    if not isinstance(text, str):
        raise TypeError(f"text phải là str, nhận được {type(text).__name__}.")
    nfc_lower = unicodedata.normalize("NFC", text).lower()
    without_punct = "".join(
        " " if unicodedata.category(ch).startswith("P") else ch
        for ch in nfc_lower
    )
    return " ".join(without_punct.split())


def _extract_word_shingles(words: list[str], ngram_size: int) -> frozenset[tuple[str, ...]]:
    """Tạo tập cụm `n` từ liên tiếp (word N-gram shingles) và xử lý an toàn văn bản ngắn.

    Lý do kỹ thuật: Khi câu có `0 < len(words) < ngram_size` (ví dụ câu 2 từ `"chào bạn"` với
    `n=3`), nếu trả về tập rỗng thì hai câu ngắn khác nhau đều cho `0.0` nhưng câu giống nhau cũng
    không có shingle. Dùng chính `tuple(words)` làm 1 shingle duy nhất tránh `ZeroDivisionError`
    và tránh phát sinh trùng lặp giả với câu dài hơn.
    """
    if not words:
        return frozenset()
    if len(words) < ngram_size:
        return frozenset((tuple(words),))
    return frozenset(
        tuple(words[idx : idx + ngram_size])
        for idx in range(len(words) - ngram_size + 1)
    )


def _jaccard_similarity(left: AbstractSet[Any], right: AbstractSet[Any]) -> float:
    """Tính hệ số tương đồng Jaccard `|A ∩ B| / |A ∪ B|` với bảo vệ mẫu số bằng 0."""
    if not left or not right:
        return 0.0
    union_size = len(left | right)
    if union_size == 0:
        return 0.0
    return len(left & right) / union_size


class RepetitionDetector:
    """Bộ phát hiện lặp 5 tầng kết hợp đối chiếu từ vựng, cụm N-gram và độ phủ sự thật (`claim_id`).

    Phương pháp tính toán và giải thích kỹ thuật:
    1. **Word Jaccard (`|A ∩ B| / |A ∪ B|`)**:
       Đo tỷ lệ giao nhau trên hợp của hai tập từ đã chuẩn hóa.
       - Ví dụ:
         `A = "mật ong hoa cà phê đắk lắk nguyên chất 500ml"` (10 từ)
         `B = "chai mật ong hoa cà phê đắk lắk 500ml nguyên chất"` (11 từ, thêm `"chai"`)
         `|A ∩ B| = 10`, `|A ∪ B| = 11` -> `Word Jaccard = 10/11 ≈ 0.909 >= 0.65` (`TO VALIDATE`).
    2. **N-gram Jaccard (`n = 3`)**:
       Đo tỷ lệ giao nhau trên hợp của các bộ 3 từ liên tiếp (trigram) để bắt các câu đảo trật tự nhẹ
       nhưng giữ nguyên cụm ngữ nghĩa dài.
       - Ví dụ với `A` và `B` trên: các cụm 3 từ như `("mật", "ong", "hoa")`, `("ong", "hoa", "cà")`,
         `("hoa", "cà", "phê")`, `("cà", "phê", "đắk")`, `("phê", "đắk", "lắk")` trùng phần lớn -> điểm cao.
    3. **Fact Overlap (`|cand_claims ∩ played_claims| / |cand_claims|`)**:
       Xử lý trường hợp hai câu dùng từ ngữ khác nhau nhưng cùng một `intent` (và cùng `sku_id`)
       để lặp lại y hệt một tập `claim_id` đã nói trước đó.
    4. **Giới hạn ngữ nghĩa (`P06-OPEN-2`)**:
       Đo đạc Jaccard dựa trên bề mặt từ vựng nên KHÔNG bắt được hai câu paraphrase hoàn toàn khác từ
       (ví dụ `"Hương vị ngọt thanh tự nhiên"` vs `"Vị dịu nhẹ không gắt cổ"`) nếu thiếu `claim_id`.
       Giới hạn này được ghi nhận mở ở `P06-OPEN-2` để đối chiếu thực nghiệm với `OptionalSemanticMemory`.
    """

    def __init__(self, config: Optional[RepetitionConfig] = None) -> None:
        """Khởi tạo bộ phát hiện lặp với cấu hình ngưỡng `RepetitionConfig`."""
        self._config: RepetitionConfig = config if config is not None else RepetitionConfig()

    @property
    def config(self) -> RepetitionConfig:
        """Cấu hình ngưỡng hiện hành của bộ phát hiện lặp."""
        return self._config

    def check(
        self,
        candidate_text: str,
        played_turns: Sequence[PlayedTurnSummary],
        *,
        candidate_chunk_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        sku_id: Optional[str] = None,
        intent: Optional[str] = None,
        candidate_claim_ids: Sequence[str] = (),
        played_chunk_ids: AbstractSet[str] = frozenset(),
    ) -> RepetitionCheckResult:
        """Kiểm tra mức độ lặp của ứng viên lời thoại đối chiếu với lịch sử đã phát (stateless).

        Thứ tự ưu tiên phân loại:
        1. `EXACT_REPLAY`: Trùng `chunk_id` (`SWITCH_TOPIC`) hoặc trùng văn bản chuẩn hóa (`REWRITE`).
        2. `LEXICAL_DUPLICATION`: Word Jaccard hoặc N-gram Jaccard đạt ngưỡng (`REWRITE`).
        3. `REPEATED_FACTS`: Trùng `>= fact_overlap_threshold` các `claim_id` ở cùng `intent` & `sku_id`
           (`SWITCH_TOPIC` nếu cùng `topic_id`, ngược lại `REWRITE`).
        4. `LEGITIMATE_CONTINUATION`: Cùng `topic_id` đang nói, đưa vào `claim_id` mới (hoặc chưa
           trùng claim), và độ trùng bề mặt dưới trần cho phép (`ALLOW`).
        5. `NONE`: Không có dấu hiệu lặp đáng kể (`ALLOW`).

        Args:
            candidate_text: Văn bản lời thoại ứng viên cần kiểm tra.
            played_turns: Chuỗi `PlayedTurnSummary` gần nhất từ cửa sổ lịch sử.
            candidate_chunk_id: Mã `StoryChunk` nguồn của ứng viên (nếu có).
            topic_id: Mã `StoryTopic` mục tiêu của ứng viên (nếu có).
            sku_id: Mã SKU chính của ứng viên (nếu có).
            intent: Ý định giao tiếp của ứng viên (nếu có).
            candidate_claim_ids: Tập `claim_id` mà ứng viên dự kiến đề cập.
            played_chunk_ids: Tập toàn bộ `chunk_id` đã phát từ đầu phiên (ngoài cửa sổ `W`).

        Returns:
            RepetitionCheckResult: Kết quả phân loại, hành động khuyến nghị và các chỉ số đo chi tiết.

        Raises:
            TypeError: Nếu `candidate_text` không phải `str`.
        """
        norm_candidate = normalize_vietnamese_for_repetition(candidate_text)
        cand_words_list = norm_candidate.split()
        cand_word_set = frozenset(cand_words_list)
        cand_ngram_set = _extract_word_shingles(cand_words_list, self._config.ngram_size)
        cand_claims = frozenset(
            claim.strip() for claim in candidate_claim_ids if isinstance(claim, str) and claim.strip()
        )
        clean_chunk_id = (
            candidate_chunk_id.strip()
            if isinstance(candidate_chunk_id, str) and candidate_chunk_id.strip()
            else None
        )
        clean_topic_id = (
            topic_id.strip() if isinstance(topic_id, str) and topic_id.strip() else None
        )
        clean_sku_id = sku_id.strip() if isinstance(sku_id, str) and sku_id.strip() else None
        clean_intent = intent.strip() if isinstance(intent, str) and intent.strip() else None

        turns = (
            list(played_turns[-self._config.max_recent_turns_to_check :])
            if self._config.max_recent_turns_to_check is not None
            else list(played_turns)
        )

        # Tính trước các chỉ số bề mặt & fact overlap trên các lượt đối chiếu để mọi kết quả đều đầy đủ số liệu.
        max_word_jaccard = 0.0
        max_ngram_jaccard = 0.0
        best_lexical_turn: Optional[PlayedTurnSummary] = None
        best_lexical_score = -1.0

        exact_text_turn: Optional[PlayedTurnSummary] = None
        exact_chunk_turn: Optional[PlayedTurnSummary] = None

        max_fact_overlap = 0.0
        best_fact_turn: Optional[PlayedTurnSummary] = None
        matched_fact_turns: list[PlayedTurnSummary] = []

        for turn in turns:
            if clean_chunk_id is not None and turn.chunk_id == clean_chunk_id and exact_chunk_turn is None:
                exact_chunk_turn = turn

            norm_turn = normalize_vietnamese_for_repetition(turn.spoken_text)
            if norm_candidate and norm_turn == norm_candidate and exact_text_turn is None:
                exact_text_turn = turn

            turn_words_list = norm_turn.split()
            word_jaccard = _jaccard_similarity(cand_word_set, frozenset(turn_words_list))
            ngram_jaccard = _jaccard_similarity(
                cand_ngram_set,
                _extract_word_shingles(turn_words_list, self._config.ngram_size),
            )

            if word_jaccard > max_word_jaccard:
                max_word_jaccard = word_jaccard
            if ngram_jaccard > max_ngram_jaccard:
                max_ngram_jaccard = ngram_jaccard

            turn_lexical_score = max(word_jaccard, ngram_jaccard)
            if turn_lexical_score > best_lexical_score:
                best_lexical_score = turn_lexical_score
                best_lexical_turn = turn

            if (
                clean_intent is not None
                and turn.intent == clean_intent
                and (clean_sku_id is None or clean_sku_id in turn.sku_refs)
                and cand_claims
                and turn.covered_claim_ids
            ):
                overlap_ratio = len(cand_claims & set(turn.covered_claim_ids)) / len(cand_claims)
                if overlap_ratio > max_fact_overlap:
                    max_fact_overlap = overlap_ratio
                    best_fact_turn = turn
                if overlap_ratio >= self._config.fact_overlap_threshold:
                    matched_fact_turns.append(turn)

        # Tầng 1: Phát lại chính xác chunk_id hoặc nguyên văn bản chuẩn hóa.
        if clean_chunk_id is not None and (clean_chunk_id in played_chunk_ids or exact_chunk_turn is not None):
            return RepetitionCheckResult(
                is_repetitive=True,
                category=RepetitionCategory.EXACT_REPLAY,
                recommended_action=RepetitionAction.SWITCH_TOPIC,
                word_jaccard=max_word_jaccard,
                ngram_jaccard=max_ngram_jaccard,
                fact_overlap_ratio=max_fact_overlap,
                matched_turn_id=exact_chunk_turn.turn_id if exact_chunk_turn is not None else None,
                matched_chunk_id=clean_chunk_id,
                reasons=(
                    f"chunk_id '{clean_chunk_id}' đã được xác nhận phát trước đó trong phiên.",
                ),
            )

        if exact_text_turn is not None:
            return RepetitionCheckResult(
                is_repetitive=True,
                category=RepetitionCategory.EXACT_REPLAY,
                recommended_action=RepetitionAction.REWRITE,
                word_jaccard=max_word_jaccard,
                ngram_jaccard=max_ngram_jaccard,
                fact_overlap_ratio=max_fact_overlap,
                matched_turn_id=exact_text_turn.turn_id,
                matched_chunk_id=exact_text_turn.chunk_id,
                reasons=(
                    f"Nội dung chuẩn hóa trùng hoàn toàn với lượt '{exact_text_turn.turn_id}'.",
                ),
            )

        # Tầng 2: Trùng lặp bề mặt từ vựng hoặc cụm N-gram liên tiếp.
        if (
            max_word_jaccard >= self._config.word_jaccard_threshold
            or max_ngram_jaccard >= self._config.ngram_jaccard_threshold
        ):
            reasons: list[str] = []
            if max_word_jaccard >= self._config.word_jaccard_threshold:
                reasons.append(
                    f"word_jaccard={max_word_jaccard:.3f} >= ngưỡng {self._config.word_jaccard_threshold:.3f}."
                )
            if max_ngram_jaccard >= self._config.ngram_jaccard_threshold:
                reasons.append(
                    f"ngram_jaccard={max_ngram_jaccard:.3f} >= ngưỡng {self._config.ngram_jaccard_threshold:.3f}."
                )
            return RepetitionCheckResult(
                is_repetitive=True,
                category=RepetitionCategory.LEXICAL_DUPLICATION,
                recommended_action=RepetitionAction.REWRITE,
                word_jaccard=max_word_jaccard,
                ngram_jaccard=max_ngram_jaccard,
                fact_overlap_ratio=max_fact_overlap,
                matched_turn_id=best_lexical_turn.turn_id if best_lexical_turn is not None else None,
                matched_chunk_id=best_lexical_turn.chunk_id if best_lexical_turn is not None else None,
                reasons=tuple(reasons),
            )

        # Tầng 3: Lặp lại phần lớn dữ kiện/claim đã nói trên cùng intent & phạm vi SKU.
        if matched_fact_turns:
            same_topic_matched = clean_topic_id is not None and any(
                clean_topic_id in turn.topic_ids for turn in matched_fact_turns
            )
            action = (
                RepetitionAction.SWITCH_TOPIC
                if same_topic_matched
                else RepetitionAction.REWRITE
            )
            return RepetitionCheckResult(
                is_repetitive=True,
                category=RepetitionCategory.REPEATED_FACTS,
                recommended_action=action,
                word_jaccard=max_word_jaccard,
                ngram_jaccard=max_ngram_jaccard,
                fact_overlap_ratio=max_fact_overlap,
                matched_turn_id=best_fact_turn.turn_id if best_fact_turn is not None else None,
                matched_chunk_id=best_fact_turn.chunk_id if best_fact_turn is not None else None,
                reasons=(
                    f"fact_overlap_ratio={max_fact_overlap:.3f} >= ngưỡng {self._config.fact_overlap_threshold:.3f} "
                    f"trên cùng intent '{clean_intent}'.",
                ),
            )

        # Tầng 4: Triển khai tiếp cùng chủ đề với thông tin/claim mới và cách diễn đạt khác biệt.
        if clean_topic_id is not None:
            same_topic_turns = [
                turn
                for turn in turns
                if clean_topic_id in turn.topic_ids
                and (clean_sku_id is None or clean_sku_id in turn.sku_refs)
            ]
            if same_topic_turns:
                covered_in_topic = {
                    claim_id
                    for turn in same_topic_turns
                    for claim_id in turn.covered_claim_ids
                }
                introduces_new_claims = bool(cand_claims - covered_in_topic) if cand_claims else True
                if (
                    introduces_new_claims
                    and max_word_jaccard < self._config.continuation_lexical_ceiling
                    and max_ngram_jaccard < self._config.ngram_jaccard_threshold
                ):
                    latest_topic_turn = same_topic_turns[-1]
                    return RepetitionCheckResult(
                        is_repetitive=False,
                        category=RepetitionCategory.LEGITIMATE_CONTINUATION,
                        recommended_action=RepetitionAction.ALLOW,
                        word_jaccard=max_word_jaccard,
                        ngram_jaccard=max_ngram_jaccard,
                        fact_overlap_ratio=max_fact_overlap,
                        matched_turn_id=latest_topic_turn.turn_id,
                        matched_chunk_id=latest_topic_turn.chunk_id,
                        reasons=(
                            f"Tiếp nối hợp lệ chủ đề '{clean_topic_id}' với nội dung mới và "
                            f"trùng lặp từ vựng thấp (word_jaccard={max_word_jaccard:.3f}).",
                        ),
                    )

        # Tầng 5: Không phát hiện lặp.
        return RepetitionCheckResult(
            is_repetitive=False,
            category=RepetitionCategory.NONE,
            recommended_action=RepetitionAction.ALLOW,
            word_jaccard=max_word_jaccard,
            ngram_jaccard=max_ngram_jaccard,
            fact_overlap_ratio=max_fact_overlap,
            matched_turn_id=None,
            matched_chunk_id=None,
            reasons=(),
        )
