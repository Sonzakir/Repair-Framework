"""Diff-level correctness check: compare a plausible patch to the developer fix.

A patch is *plausible* if the patched program passes the test suite; it is
*correct* if it is additionally equivalent to the developer's ground-truth fix.
For this assignment it is sufficient to compare the two at the **diff level**.

The challenge is that our template patches are produced via ``ast.unparse`` which
reformats the whole file (whitespace, redundant parens, quote style, ...), so the
candidate's raw unified diff is full of cosmetic noise and would never match the
developer diff textually. To get a fair comparison we:

  1. Build a *minimal* candidate diff by unparsing the original source the same way
     the patched source was produced (``ast.unparse(ast.parse(original))`` vs
     ``patched_source``). Cosmetic reformatting then appears on *both* sides and
     cancels out, leaving only the operator's real change.
  2. Reduce each diff (candidate and reference) to its set of *changed content
     lines* — the added (``+``) and removed (``-``) lines, whitespace-normalized,
     ignoring file headers, hunk headers and context lines.
  3. Declare the patch correct when, for the file it touches, the candidate's
     (added, removed) normalized line sets equal the reference's.

This is a deliberately strict, purely syntactic check. Known limitations: it does
not recognise semantically-equivalent-but-textually-different fixes, and developer
fixes that span multiple files or hunks (or add whole statements out of operator
reach) will not match a single-location template patch.
"""

import ast
import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path

from apr_framework.core.models import PatchCandidate

_WHITESPACE_RUN = re.compile(r"\s+")


def _normalize_line(line: str) -> str:
    """Strip a leading +/- marker and collapse whitespace for robust comparison."""
    if line and line[0] in "+-":
        line = line[1:]
    return _WHITESPACE_RUN.sub(" ", line).strip()


@dataclass
class ChangedLines:
    """Normalized added/removed content lines for one file in a unified diff."""

    added: set[str] = field(default_factory=set)
    removed: set[str] = field(default_factory=set)

    def is_empty(self) -> bool:
        return not self.added and not self.removed


def parse_unified_diff(diff_text: str) -> dict[str, ChangedLines]:
    """Parse a unified diff into per-file normalized changed-line sets.

    Files are keyed by basename (e.g. ``black.py``) so that the candidate's
    ``a/black.py`` and the reference's ``a/black.py`` line up regardless of path
    prefixes. Header lines (``---``/``+++``/``diff``/``index``), hunk headers
    (``@@``) and context lines are ignored; only true ``+``/``-`` content lines
    are collected.
    """
    by_file: dict[str, ChangedLines] = {}
    current: ChangedLines | None = None

    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            path = raw[4:].strip().split("\t", 1)[0]
            name = Path(path.split(" ", 1)[0]).name
            current = by_file.setdefault(name, ChangedLines())
            continue
        if (
            raw.startswith("--- ")
            or raw.startswith("diff ")
            or raw.startswith("index ")
        ):
            continue
        if raw.startswith("@@"):
            continue
        if current is None:
            continue
        if raw.startswith("+"):
            content = _normalize_line(raw)
            if content:
                current.added.add(content)
        elif raw.startswith("-"):
            content = _normalize_line(raw)
            if content:
                current.removed.add(content)

    return by_file


def _unparse_normalize(source: str) -> str:
    """Round-trip source through the AST so formatting is canonical, if parseable."""
    try:
        return ast.unparse(ast.parse(source))
    except SyntaxError:
        return source


def minimal_candidate_diff(original_source: str, patched_source: str) -> str:
    """Compute a reformatting-neutral unified diff for a candidate patch.

    Both sides go through ``ast.unparse`` so cosmetic differences (whitespace,
    redundant parens, quote style) cancel out, isolating the operator's semantic
    change. In the real pipeline ``patched_source`` is already an unparse result, so
    re-normalizing it is idempotent; doing it explicitly keeps the comparison robust
    to patched sources produced any other way.
    """
    normalized_original = _unparse_normalize(original_source)
    normalized_patched = _unparse_normalize(patched_source)

    if not normalized_original.endswith("\n"):
        normalized_original += "\n"
    if not normalized_patched.endswith("\n"):
        normalized_patched += "\n"

    diff = difflib.unified_diff(
        normalized_original.splitlines(keepends=True),
        normalized_patched.splitlines(keepends=True),
        fromfile="a/source",
        tofile="b/source",
    )
    return "".join(diff)


def is_correct_patch(candidate: PatchCandidate, reference_diff_text: str) -> bool:
    """Return True if the candidate matches the developer fix at the diff level.

    Args:
        candidate: A plausible patch. Uses ``metadata['patched_source']`` and
            ``metadata['source_path']`` to recompute a reformatting-neutral diff.
        reference_diff_text: The developer fix as a unified diff (BugsInPy
            ``bug_patch.txt`` content).

    Returns:
        True iff, for the source file the candidate changes, its normalized added
        and removed line sets equal the reference's for that file.
    """
    patched_source = candidate.metadata.get("patched_source")
    source_path_str = candidate.metadata.get("source_path")
    if not patched_source or not source_path_str or not reference_diff_text:
        return False

    source_path = Path(source_path_str)
    try:
        original_source = source_path.read_text(encoding="utf-8")
    except OSError:
        return False

    candidate_diff = minimal_candidate_diff(original_source, patched_source)
    candidate_changes = parse_unified_diff(candidate_diff)
    reference_changes = parse_unified_diff(reference_diff_text)

    # The candidate touches exactly one synthetic file ("source"); compare it
    # against the reference hunk for the same underlying file (matched by basename).
    candidate_set = next(
        (c for c in candidate_changes.values() if not c.is_empty()), None
    )
    if candidate_set is None:
        return False

    reference_set = reference_changes.get(source_path.name)
    if reference_set is None or reference_set.is_empty():
        return False

    return (
        candidate_set.added == reference_set.added
        and candidate_set.removed == reference_set.removed
    )
