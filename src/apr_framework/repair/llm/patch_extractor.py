"""Convert an LLM response string into a unified diff for PatchCandidate.diff_text.

Pipeline:
  1. Extract the fenced code block from the response text.
  2. Validate Python syntax of the extracted code.
  3. Reconstruct the full file with the function region replaced.
  4. Generate a unified diff between original and patched file.

All failure modes return None and log a WARNING; they are never propagated as
exceptions so the algorithm can silently skip bad generations.
"""

import ast
import difflib
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Try an explicit ```python fence first; fall back to any generic ``` fence.
# [ \t]* tolerates trailing spaces/tabs on the opening fence line.
_PYTHON_FENCE_RE = re.compile(r"```python[ \t]*\n(.*?)```", re.DOTALL)
_GENERIC_FENCE_RE = re.compile(r"```[ \t]*\n(.*?)```", re.DOTALL)


def extract_patch_from_llm_response(
    llm_response_text: str,
    source_file_path: Path,
    function_start_line: int,
    function_end_line: int,
) -> str | None:
    """Turn an LLM completion into a unified diff ready for PatchCandidate.diff_text.

    Args:
        llm_response_text:  Raw text returned by the LLM.
        source_file_path:   Absolute path to the original Python source file.
        function_start_line: 1-indexed first line of the region to replace
                             (as returned by extract_function_source).
        function_end_line:   1-indexed last line of the region to replace
                             (inclusive).

    Returns:
        A unified diff string, or None if extraction fails for any reason.
    """
    extracted_code = _extract_code_block(llm_response_text, source_file_path)
    if extracted_code is None:
        return None

    if not _has_valid_syntax(extracted_code, source_file_path):
        return None

    original_lines = _read_source_lines(source_file_path)
    if original_lines is None:
        return None

    patched_lines = _splice_replacement(
        original_lines, extracted_code, function_start_line, function_end_line
    )

    return _compute_diff(original_lines, patched_lines, source_file_path)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _extract_code_block(
    llm_response_text: str, source_file_path: Path
) -> str | None:
    """Return the content of the first fenced code block, or None."""
    match = _PYTHON_FENCE_RE.search(llm_response_text)
    if match is None:
        match = _GENERIC_FENCE_RE.search(llm_response_text)
    if match is None:
        logger.warning(
            "No fenced code block found in LLM response for %s",
            source_file_path.name,
        )
        return None
    return match.group(1)


def _has_valid_syntax(code_text: str, source_file_path: Path) -> bool:
    """Return True if code_text parses as valid Python, else log and return False."""
    try:
        ast.parse(code_text)
    except SyntaxError as error:
        logger.warning(
            "LLM response for %s contains invalid Python syntax: %s",
            source_file_path.name,
            error,
        )
        return False
    return True


def _read_source_lines(source_file_path: Path) -> list[str] | None:
    """Read the file and return its lines (with endings), or None on I/O error."""
    try:
        return source_file_path.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError as error:
        logger.warning("Cannot read source file %s: %s", source_file_path, error)
        return None


def _splice_replacement(
    original_lines: list[str],
    extracted_code: str,
    function_start_line: int,
    function_end_line: int,
) -> list[str]:
    """Replace the function region in original_lines with extracted_code.

    The slice [function_start_line-1 : function_end_line] (0-indexed) is
    replaced with the lines of extracted_code.  The last replacement line is
    guaranteed to end with '\\n' so the surrounding context stitches cleanly.
    """
    replacement_lines = extracted_code.splitlines(keepends=True)
    if replacement_lines and not replacement_lines[-1].endswith("\n"):
        replacement_lines[-1] += "\n"

    return (
        original_lines[: function_start_line - 1]
        + replacement_lines
        + original_lines[function_end_line:]
    )


def _compute_diff(
    original_lines: list[str],
    patched_lines: list[str],
    source_file_path: Path,
) -> str | None:
    """Generate a unified diff string, or None if the code is unchanged."""
    source_path_str = str(source_file_path)
    diff_text = "".join(
        difflib.unified_diff(
            original_lines,
            patched_lines,
            fromfile=source_path_str,
            tofile=source_path_str,
        )
    )
    if not diff_text:
        logger.warning(
            "LLM returned code identical to the original for %s — no diff produced",
            source_file_path.name,
        )
        return None
    return diff_text
