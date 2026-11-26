"""Bộ nạp, băm SHA-256 chuẩn hóa LF và kết xuất an toàn các prompt template của P06.

1. File này giải quyết vấn đề gì?
   Quản lý các tệp prompt có phiên bản trong `prompts/` một cách tái lập giữa các hệ điều hành
   (Windows CRLF vs Linux/macOS LF) và tách biệt an toàn các biến dữ liệu khỏi cú pháp JSON
   ngoặc nhọn đơn `{...}` bên trong hướng dẫn prompt.
2. Trách nhiệm chính của module là gì?
   Định nghĩa model bất biến `PromptTemplate`, hằng số `DEFAULT_PROMPTS_DIR`, hàm nạp & kiểm định
   header `PROMPT_VERSION` (`load_prompt_template`), tính bảng hash (`compute_prompt_hashes`),
   và kết xuất biến một lượt (`render_prompt_template`).
3. Module này liên kết với các thành phần nào?
   Đọc các tệp `*.txt` trong `prompts/` và cung cấp template đã kiểm định cho `story_planner.py`
   cùng các node LangGraph (`agent/nodes/`) ở wave tiếp theo.
4. Input và output chính là gì?
   Input là tên/đường dẫn tệp template và ánh xạ biến `Mapping[str, str]`;
   Output là `PromptTemplate` kèm `sha256` độc lập hệ điều hành, dict hash, hoặc chuỗi prompt đã điền biến.
5. Có những constraints hoặc invariants quan trọng nào?
   - Chuẩn hóa `\r\n` và `\r` về `\n` (LF) TRƯỚC KHI tính `hashlib.sha256` để tái lập đa nền tảng.
   - Fail-closed (`ValueError`) nếu thiếu/rỗng header `PROMPT_VERSION: <ver>`, thiếu biến bắt buộc,
     hoặc còn sót placeholder `{{...}}` chưa được điền trong template.
   - Thay thế một lượt (single-pass) để dữ liệu không tin cậy trong biến (vd `{{x}}` từ bên ngoài)
     không bị diễn giải lại thành placeholder.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Final, Optional, Union

from pydantic import BaseModel, ConfigDict

from p06.schemas.story import NonBlankStr

# Thư mục prompts mặc định nằm tại `experiments/sales-intelligence/autonomous-storytelling/prompts/`.
DEFAULT_PROMPTS_DIR: Final[Path] = Path(__file__).resolve().parents[3] / "prompts"

# Khớp dòng đầu tiên khai báo phiên bản prompt (`PROMPT_VERSION: v0.1`).
_PROMPT_VERSION_LINE_RE: Final[re.Pattern[str]] = re.compile(
    r"^PROMPT_VERSION:\s*(\S.*?)\s*$"
)

# Khớp placeholder dạng `{{...}}` trên nội dung template mà không chạm vào dấu ngoặc đơn `{...}` của JSON.
_PLACEHOLDER_TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"\{\{([^{}]*)\}\}")
_VALID_PLACEHOLDER_NAME_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class PromptTemplate(BaseModel):
    """Mô tả bất biến của một prompt template đã nạp và xác thực phiên bản/hash.

    Attributes:
        name: Tên tệp template (ví dụ `story_planner.txt`).
        version: Mã phiên bản đọc từ header `PROMPT_VERSION: <ver>`.
        path: Đường dẫn tuyệt đối tới tệp template nguồn.
        content: Toàn văn nội dung template đã chuẩn hóa xuống dòng về LF (`\\n`).
        sha256: Mã băm SHA-256 (hex) tính trên byte UTF-8 của `content` chuẩn hóa LF.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    name: NonBlankStr
    version: NonBlankStr
    path: Path
    content: NonBlankStr
    sha256: NonBlankStr


def _resolve_template_path(
    name_or_path: Union[str, Path],
    prompts_dir: Optional[Path] = None,
) -> Path:
    """Phân giải tên template hoặc đường dẫn thành `Path` tồn tại trên đĩa."""
    if isinstance(name_or_path, str):
        if not name_or_path.strip():
            raise ValueError("Tên hoặc đường dẫn prompt template không được rỗng.")
        raw_path = Path(name_or_path.strip())
    elif isinstance(name_or_path, Path):
        raw_path = name_or_path
    else:
        raise TypeError(
            f"name_or_path phải là str hoặc Path, nhận được {type(name_or_path).__name__}."
        )

    base_dir = prompts_dir if prompts_dir is not None else DEFAULT_PROMPTS_DIR

    if raw_path.is_absolute():
        target = raw_path
    elif prompts_dir is not None:
        target = base_dir / raw_path
        if not target.exists() and raw_path.suffix == "":
            target_with_ext = base_dir / f"{raw_path.as_posix()}.txt"
            if target_with_ext.exists():
                target = target_with_ext
    else:
        candidate_in_default = base_dir / raw_path
        if candidate_in_default.exists() and candidate_in_default.is_file():
            target = candidate_in_default
        elif raw_path.suffix == "" and (base_dir / f"{raw_path.as_posix()}.txt").is_file():
            target = base_dir / f"{raw_path.as_posix()}.txt"
        elif raw_path.exists() and raw_path.is_file():
            target = raw_path
        else:
            target = candidate_in_default

    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"Không tìm thấy tệp prompt template tại '{target}'.")
    return target.resolve()


def _parse_prompt_version(normalized_content: str, template_name: str) -> str:
    """Trích xuất `PROMPT_VERSION` từ dòng đầu tiên và fail-closed nếu thiếu hoặc rỗng."""
    first_line = normalized_content.split("\n", 1)[0]
    match = _PROMPT_VERSION_LINE_RE.match(first_line)
    if match is None:
        raise ValueError(
            f"Prompt template '{template_name}' thiếu header 'PROMPT_VERSION: <ver>' hợp lệ ở dòng đầu tiên."
        )
    version = match.group(1).strip()
    if not version:
        raise ValueError(f"Prompt template '{template_name}' có header PROMPT_VERSION rỗng.")
    return version


def load_prompt_template(
    name_or_path: Union[str, Path],
    prompts_dir: Optional[Path] = None,
) -> PromptTemplate:
    """Nạp prompt template UTF-8, chuẩn hóa LF, băm SHA-256 và kiểm định header `PROMPT_VERSION`.

    Args:
        name_or_path: Tên tệp (ví dụ `'story_planner.txt'` hoặc `'story_planner'`) hay đường dẫn tới tệp.
        prompts_dir: Thư mục chứa prompts tùy chọn (mặc định dùng `DEFAULT_PROMPTS_DIR`).

    Returns:
        PromptTemplate: Đối tượng bất biến mang nội dung chuẩn hóa LF, phiên bản và SHA-256.

    Raises:
        FileNotFoundError: Nếu không tìm thấy tệp template.
        ValueError: Nếu tên rỗng, nội dung rỗng, hoặc thiếu/sai header `PROMPT_VERSION`.
        UnicodeDecodeError: Nếu tệp không đọc được theo mã hóa UTF-8.
    """
    resolved_path = _resolve_template_path(name_or_path, prompts_dir=prompts_dir)
    raw_text = resolved_path.read_bytes().decode("utf-8")

    # Chuẩn hóa kết thúc dòng về LF trước khi băm để Windows và Linux cho cùng một SHA-256.
    normalized_content = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized_content.strip():
        raise ValueError(f"Prompt template '{resolved_path.name}' không được rỗng.")

    version = _parse_prompt_version(normalized_content, resolved_path.name)
    sha256_hex = hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()

    return PromptTemplate(
        name=resolved_path.name,
        version=version,
        path=resolved_path,
        content=normalized_content,
        sha256=sha256_hex,
    )


def compute_prompt_hashes(prompts_dir: Optional[Path] = None) -> dict[str, str]:
    """Tính ánh xạ `{template_filename: sha256}` sắp xếp theo tên cho toàn bộ `*.txt` trong thư mục.

    Args:
        prompts_dir: Thư mục chứa các tệp `*.txt` (mặc định `DEFAULT_PROMPTS_DIR`).

    Returns:
        dict[str, str]: Từ điển đã sắp xếp theo tên tệp chứa mã SHA-256 chuẩn hóa LF.

    Raises:
        FileNotFoundError: Nếu `prompts_dir` không tồn tại hoặc không phải thư mục.
        ValueError: Nếu có tệp `*.txt` vi phạm chuẩn `PROMPT_VERSION`.
    """
    base_dir = (prompts_dir if prompts_dir is not None else DEFAULT_PROMPTS_DIR).resolve()
    if not base_dir.exists() or not base_dir.is_dir():
        raise FileNotFoundError(f"Thư mục prompts không tồn tại: '{base_dir}'.")

    template_files = sorted(
        (path for path in base_dir.iterdir() if path.is_file() and path.suffix == ".txt"),
        key=lambda path: path.name,
    )
    return {
        path.name: load_prompt_template(path, prompts_dir=base_dir).sha256
        for path in template_files
    }


def render_prompt_template(
    template: PromptTemplate,
    variables: Mapping[str, str],
) -> str:
    """Điền các biến `{{key}}` vào `template.content` an toàn quanh cặp ngoặc JSON `{...}`.

    Lý do thiết kế:
        Dùng regex `{{...}}` một lượt thay vì `str.format()` để không xung đột với các khối JSON
        mẫu chứa `{` và `}` trong prompt, đồng thời ngăn dữ liệu không tin cậy trong `variables`
        bị diễn giải thành placeholder ở lượt thứ hai.

    Args:
        template: Đối tượng `PromptTemplate` đã nạp hợp lệ.
        variables: Ánh xạ tên biến sang giá trị chuỗi cần điền.

    Returns:
        str: Chuỗi prompt hoàn chỉnh đã thay thế toàn bộ placeholder.

    Raises:
        ValueError: Nếu thiếu biến trong `variables`, giá trị biến không phải `str`,
            hoặc còn sót cú pháp `{{...` chưa được điền.
    """
    matches = list(_PLACEHOLDER_TOKEN_RE.finditer(template.content))
    missing_keys: list[str] = []
    invalid_tokens: list[str] = []

    for match in matches:
        raw_key = match.group(1)
        if not _VALID_PLACEHOLDER_NAME_RE.match(raw_key):
            invalid_tokens.append(match.group(0))
            continue
        if raw_key not in variables:
            if raw_key not in missing_keys:
                missing_keys.append(raw_key)
            continue
        if not isinstance(variables[raw_key], str):
            raise ValueError(
                f"Giá trị biến prompt '{raw_key}' phải là str, nhận được "
                f"{type(variables[raw_key]).__name__}."
            )

    if invalid_tokens:
        raise ValueError(
            f"Template '{template.name}' chứa placeholder không hợp lệ chưa thể kết xuất: "
            f"{invalid_tokens}."
        )
    if missing_keys:
        raise ValueError(
            f"Thiếu biến bắt buộc khi kết xuất prompt '{template.name}': {sorted(missing_keys)}."
        )

    # Kiểm tra xem có chuỗi `{{` bị mở nhưng không đóng thành placeholder hợp lệ hay không.
    stripped_valid_placeholders = _PLACEHOLDER_TOKEN_RE.sub("", template.content)
    if "{{" in stripped_valid_placeholders:
        raise ValueError(
            f"Template '{template.name}' còn sót dấu '{{{{' chưa được đóng/kết xuất hợp lệ."
        )

    return _PLACEHOLDER_TOKEN_RE.sub(
        lambda match: variables[match.group(1)],
        template.content,
    )
