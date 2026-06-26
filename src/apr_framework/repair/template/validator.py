"""Apply a patch candidate to the worktree, run tests, and revert unconditionally."""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from apr_framework.benchmarks.bugsinpy import BugsInPyAdapter
from apr_framework.core.models import CheckoutResult, PatchCandidate, TestRunResult
from apr_framework.repair.template.config import TemplateRepairConfig

logger = logging.getLogger(__name__)


@contextmanager
def patched_file(source_path: Path, new_source: str) -> Generator[None, None, None]:
    """Apply new_source to source_path, yield, then restore the original unconditionally."""
    original = source_path.read_text(encoding="utf-8")
    try:
        source_path.write_text(new_source, encoding="utf-8")
        yield
    finally:
        source_path.write_text(original, encoding="utf-8")


def validate_patch(
    candidate: PatchCandidate,
    checkout: CheckoutResult,
    adapter: BugsInPyAdapter,
    config: TemplateRepairConfig,
    failing_tests: list[str] | None = None,
) -> tuple[PatchCandidate, bool]:
    """Apply candidate to the worktree, run tests, revert, and return plausibility.

    A patch is considered plausible when the test suite reports zero failures and
    zero errors (i.e. all tests pass).

    The patched_file context manager guarantees the source file is always restored
    to its original content even if an exception occurs during testing.

    Args:
        candidate:     Patch candidate whose metadata["patched_source"] holds the
                       modified file content and metadata["source_path"] the target.
        checkout:      Checked-out worktree to test against.
        adapter:       BugsInPyAdapter used to invoke the test suite.
        config:        Repair configuration (fail_fast, timeout_per_test).
        failing_tests: Originally-failing test IDs (informational; used with fail_fast).

    Returns:
        (updated_candidate, is_plausible) — is_plausible is True iff all tests pass.
    """
    patched_source: str | None = candidate.metadata.get("patched_source")
    source_path_str: str | None = candidate.metadata.get("source_path")

    if patched_source is None or source_path_str is None:
        logger.warning(
            "Candidate %s is missing patched_source or source_path in metadata — skipping",
            candidate.patch_id,
        )
        return candidate, False

    source_path = Path(source_path_str)
    if not source_path.exists():
        logger.warning(
            "Source path %s does not exist — skipping candidate %s",
            source_path,
            candidate.patch_id,
        )
        return candidate, False

    test_result: TestRunResult | None = None
    is_plausible = False

    with patched_file(source_path, patched_source):
        try:
            test_result = adapter.run_tests(checkout)
        except Exception as exc:
            logger.error(
                "Test run failed for candidate %s: %s", candidate.patch_id, exc
            )
            return candidate, False

        # A plausible patch produces zero failures and zero errors.
        is_plausible = (
            test_result.failed_count == 0 and test_result.error_count == 0
        )

        if config.fail_fast and not is_plausible:
            logger.debug(
                "fail_fast: candidate %s still has failures (%d failed, %d error) — skipping",
                candidate.patch_id,
                test_result.failed_count,
                test_result.error_count,
            )

    # Attach the test outcome to the candidate's metadata for reporting.
    updated_metadata = dict(candidate.metadata)
    if test_result is not None:
        updated_metadata["test_passed_count"] = test_result.passed_count
        updated_metadata["test_failed_count"] = test_result.failed_count
        updated_metadata["test_error_count"] = test_result.error_count
        updated_metadata["test_total_count"] = test_result.total_count
        updated_metadata["is_plausible"] = is_plausible

    updated_candidate = PatchCandidate(
        bug=candidate.bug,
        patch_id=candidate.patch_id,
        summary=candidate.summary,
        diff_text=candidate.diff_text,
        metadata=updated_metadata,
    )
    return updated_candidate, is_plausible
