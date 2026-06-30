"""Prompt construction for LLM-based repair.

Two public functions:
  extract_function_source  — AST-based extraction of the enclosing function
  build_repair_prompt      — assembles the OpenAI-style messages list
"""

import ast
import logging
from pathlib import Path

from apr_framework.core.exceptions import ConfigurationError
from apr_framework.core.models import RankedLocation

logger = logging.getLogger(__name__)

_FALLBACK_WINDOW_LINES = 25

_SYSTEM_MESSAGE = (
    "You are an automated program repair tool. Your task is to fix a bug in a Python program.\n"
    "You will be given the buggy code region and the fault location identified by a fault\n"
    "localization tool. Return ONLY the corrected version of the provided function inside a\n"
    "Python fenced code block (```python ... ```). Do not include any explanation, commentary,\n"
    "or code outside the fenced block. Do not change the function signature."
)


def extract_function_source(
    source_file_path: Path,
    target_line: int,
) -> tuple[str, int, int]:
    """Extract the smallest enclosing function that contains target_line.

    Parses the file with ast.parse and walks all FunctionDef / AsyncFunctionDef
    nodes. Among those whose span contains target_line, returns the one with the
    narrowest span (innermost / most-nested match).

    Falls back to a ±25-line window around target_line when no enclosing function
    is found (logged at WARNING level).

    Args:
        source_file_path: Absolute path to the Python source file.
        target_line:      1-indexed line number of the suspicious location.

    Returns:
        (function_source_text, start_line, end_line) — all 1-indexed, inclusive.

    Raises:
        ConfigurationError: If the file cannot be read or contains a syntax error.
    """
    try:
        source_text = source_file_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigurationError(
            f"Cannot read source file {source_file_path}: {error}"
        ) from error

    try:
        tree = ast.parse(source_text, filename=str(source_file_path))
    except SyntaxError as error:
        raise ConfigurationError(
            f"Cannot parse {source_file_path}: {error}"
        ) from error

    source_lines = source_text.splitlines(keepends=True)

    # Find the innermost (smallest-span) function node enclosing target_line.
    best_node: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    best_span = float("inf")

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        # ast guarantees end_lineno is set for Python 3.8+
        node_start: int = node.lineno
        node_end: int = node.end_lineno  # type: ignore[assignment]
        if node_start <= target_line <= node_end:
            span = node_end - node_start
            if span < best_span:
                best_span = span
                best_node = node

    if best_node is not None:
        start_line: int = best_node.lineno
        end_line: int = best_node.end_lineno  # type: ignore[assignment]
        extracted_text = "".join(source_lines[start_line - 1 : end_line])
        return extracted_text, start_line, end_line

    # Fallback: ±25-line window
    logger.warning(
        "No enclosing function found for %s:%d — falling back to ±%d line window",
        source_file_path,
        target_line,
        _FALLBACK_WINDOW_LINES,
    )
    total_lines = len(source_lines)
    start_line = max(1, target_line - _FALLBACK_WINDOW_LINES)
    end_line = min(total_lines, target_line + _FALLBACK_WINDOW_LINES)
    extracted_text = "".join(source_lines[start_line - 1 : end_line])
    return extracted_text, start_line, end_line


def build_repair_prompt(
    location: RankedLocation,
    function_source_text: str,
    function_start_line: int,
    *,
    # Task 2 enrichment slots — present but no-op in Task 1
    failing_test_source: str | None = None,
    error_traceback: str | None = None,
    fl_score_annotation: bool = False,
) -> list[dict[str, str]]:
    """Build the OpenAI-style messages list for a single repair attempt.

    The user message has three sections (in order):
      1. Fault location — file path, suspicious line, rank, and score.
      2. Buggy code     — the extracted function with 1-indexed line numbers;
                          the suspicious line is marked with ``-->`` so the model
                          can locate it at a glance.
      3. Task instruction — asks for a minimal fix inside a fenced code block.

    The optional kwargs (failing_test_source, error_traceback, fl_score_annotation)
    are Task 2 context-enrichment slots.  They are accepted here so Task 2 can pass
    values through without changing the signature, but they are not used in Task 1.

    Args:
        location:              Suspicious location from the FL result.
        function_source_text:  Source text of the enclosing function (or window).
        function_start_line:   1-indexed line number of the first line of
                               function_source_text inside the original file.
        failing_test_source:   (Task 2) Body of a relevant failing test.
        error_traceback:       (Task 2) Exception traceback from the failing run.
        fl_score_annotation:   (Task 2) Whether to annotate each line with its
                               suspiciousness score as an inline comment.

    Returns:
        Two-entry list: [system message dict, user message dict].
    """
    user_content = "\n\n".join([
        _build_fault_location_section(location),
        _build_buggy_code_section(location, function_source_text, function_start_line),
        _build_task_section(location),
    ])

    return [
        {"role": "system", "content": _SYSTEM_MESSAGE},
        {"role": "user", "content": user_content},
    ]


# ---------------------------------------------------------------------------
# Private section builders
# ---------------------------------------------------------------------------

def _build_fault_location_section(location: RankedLocation) -> str:
    score_str = f"{location.score:.4f}" if location.score is not None else "n/a"
    return (
        "## Fault Location\n"
        f"File: {location.file_path}\n"
        f"Suspicious line: {location.line} (rank {location.rank}, score {score_str})"
    )


def _build_buggy_code_section(
    location: RankedLocation,
    function_source_text: str,
    function_start_line: int,
) -> str:
    code_lines = function_source_text.splitlines()
    end_line = function_start_line + len(code_lines) - 1

    numbered_lines: list[str] = []
    for line_offset, code_line in enumerate(code_lines):
        current_line_number = function_start_line + line_offset
        if current_line_number == location.line:
            numbered_lines.append(f"{current_line_number}  -->  {code_line}")
        else:
            numbered_lines.append(f"{current_line_number}      {code_line}")

    numbered_code = "\n".join(numbered_lines)
    return (
        f"## Buggy Code (lines {function_start_line}–{end_line})\n"
        f"```python\n{numbered_code}\n```"
    )


def _build_task_section(location: RankedLocation) -> str:
    return (
        f"## Task\n"
        f"Fix the bug at line {location.line}. Return the corrected function in a Python fenced\n"
        "code block. Keep the fix minimal — change as few lines as necessary."
    )
