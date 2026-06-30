"""LLM-based repair algorithm implementation."""

import logging
import subprocess
from pathlib import Path

from apr_framework.benchmarks.bugsinpy import BugsInPyAdapter
from apr_framework.core.exceptions import APRFrameworkError
from apr_framework.core.models import (
    BugIdentifier,
    CheckoutResult,
    LocalizationResult,
    PatchCandidate,
    RankedLocation,
    RepairAttemptResult,
    RepairStatus,
)
from apr_framework.repair.base import RepairAlgorithm
from apr_framework.repair.llm.client import LLMClient
from apr_framework.repair.llm.config import LLMRepairConfig
from apr_framework.repair.llm.patch_extractor import extract_patch_from_llm_response
from apr_framework.repair.llm.prompt_builder import (
    build_repair_prompt,
    extract_function_source,
)
from apr_framework.repair.patch_applier import apply_patch_and_validate
from apr_framework.repair.regression import RegressionContext, build_regression_context
from apr_framework.repair.run_loop import run_validation_loop

logger = logging.getLogger(__name__)


class LLMRepairAlgorithm(RepairAlgorithm):
    """LLM-based repair algorithm: FL-guided prompting with unified-diff output.

    For each suspicious location the algorithm asks the LLM to return a
    corrected version of the enclosing function.  The response is parsed into
    a unified diff and validated against the test suite.  The generate /
    validate steps conform to the RepairAlgorithm ABC so the algorithm slots
    into RepairEvaluationRunner without any changes.

    Constructor Args:
        localization_result: Ranked suspicious locations from a prior FL run.
        adapter:             BugsInPyAdapter used to invoke the test suite.
        repair_config:       LLM-specific repair configuration (required).
        llm_client:          Injected LLM client; substitute a stub in tests.
    """

    def __init__(
        self,
        localization_result: LocalizationResult,
        adapter: BugsInPyAdapter,
        repair_config: LLMRepairConfig,
        llm_client: LLMClient,
    ) -> None:
        self._localization_result = localization_result
        self._adapter = adapter
        self._repair_config = repair_config
        self._llm_client = llm_client
        # Regression baseline is established once, lazily, on the first
        # validate_patch call; reused for every subsequent candidate.
        self._regression: RegressionContext | None = None

    @property
    def name(self) -> str:
        return "llm-repair"

    # ------------------------------------------------------------------
    # RepairAlgorithm ABC
    # ------------------------------------------------------------------

    def generate_patches(
        self, bug: BugIdentifier, checkout: CheckoutResult
    ) -> list[PatchCandidate]:
        """Query the LLM for every top-N suspicious location.

        For each location, extracts the enclosing function, builds the repair
        prompt, and calls the LLM up to max_patch_count times.  Only responses
        that yield a valid, non-empty unified diff become PatchCandidates.

        Args:
            bug:      Bug identifier.
            checkout: Checkout result containing the project worktree.

        Returns:
            All generated PatchCandidate objects across all locations.
        """
        top_locations = self._localization_result.ranked_locations[
            : self._repair_config.top_n_locations
        ]
        all_patch_candidates: list[PatchCandidate] = []

        for location in top_locations:
            location_candidates = self._generate_patches_for_location(
                bug, checkout, location
            )
            all_patch_candidates.extend(location_candidates)

        logger.info(
            "LLM generated %d patch candidate(s) across %d location(s)",
            len(all_patch_candidates),
            len(top_locations),
        )
        return all_patch_candidates

    def validate_patch(
        self,
        bug: BugIdentifier,
        checkout: CheckoutResult,
        patch_candidate: PatchCandidate,
    ) -> RepairAttemptResult:
        """Apply a diff candidate to the worktree, run tests, and revert.

        Parses the target file path from the diff header, applies the patch
        with the system ``patch`` utility, delegates the test-run and
        regression check to ``apply_patch_and_validate``, then restores
        the file unconditionally.

        Args:
            bug:             Bug identifier.
            checkout:        Checkout result containing the target worktree.
            patch_candidate: Candidate patch whose diff_text holds a unified diff
                             with an absolute ``fromfile`` path.

        Returns:
            RepairAttemptResult with status PLAUSIBLE or FAILED.
        """
        source_file_path = _parse_source_file_path_from_diff(patch_candidate.diff_text)
        if source_file_path is None:
            logger.warning(
                "Cannot parse source path from diff for %s", patch_candidate.patch_id
            )
            return RepairAttemptResult(
                bug=bug,
                patch=patch_candidate,
                status=RepairStatus.FAILED,
                validation_summary=(
                    f"Cannot parse source path from diff for {patch_candidate.patch_id}."
                ),
            )

        try:
            original_file_content = source_file_path.read_bytes()
        except OSError as read_error:
            logger.error(
                "Cannot read %s for candidate %s: %s",
                source_file_path,
                patch_candidate.patch_id,
                read_error,
            )
            return RepairAttemptResult(
                bug=bug,
                patch=patch_candidate,
                status=RepairStatus.FAILED,
                validation_summary=(
                    f"Cannot read source file {source_file_path}: {read_error}"
                ),
            )

        diff_text = patch_candidate.diff_text

        def apply_fn() -> None:
            # Diffs use absolute paths so -p0 is correct (no path-component stripping).
            proc = subprocess.run(
                ["patch", "-p0"],
                input=diff_text,
                capture_output=True,
                text=True,
                cwd=checkout.worktree,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"patch -p0 failed for {patch_candidate.patch_id}: "
                    f"{proc.stderr.strip()}"
                )

        def restore_fn() -> None:
            source_file_path.write_bytes(original_file_content)

        regression_context = self._regression_context(checkout)

        is_plausible, test_run_result = apply_patch_and_validate(
            apply_fn,
            restore_fn,
            self._adapter,
            checkout,
            regression_context,
            self._repair_config.timeout_seconds,
        )

        passed_count = test_run_result.passed_count
        failed_count = test_run_result.failed_count
        error_count = test_run_result.error_count

        if is_plausible:
            logger.info("Plausible patch found: %s", patch_candidate.patch_id)
            return RepairAttemptResult(
                bug=bug,
                patch=patch_candidate,
                status=RepairStatus.PLAUSIBLE,
                validation_summary=(
                    f"All tests passed with patch {patch_candidate.patch_id}."
                ),
            )

        return RepairAttemptResult(
            bug=bug,
            patch=patch_candidate,
            status=RepairStatus.FAILED,
            validation_summary=(
                f"Patch {patch_candidate.patch_id} did not fix all tests "
                f"(passed={passed_count}, failed={failed_count}, errors={error_count})."
            ),
        )

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def repair(
        self, bug: BugIdentifier, checkout: CheckoutResult
    ) -> tuple[RepairAttemptResult, list[RepairAttemptResult]]:
        """Run the full repair loop with budget and optional early stopping.

        Delegates to run_validation_loop (the shared backend-agnostic loop),
        identical to TemplateRepairAlgorithm.repair().  When Task 3 is
        implemented this method will be overridden for iterative mode;
        generate_patches() and validate_patch() remain untouched.

        Args:
            bug:      Bug identifier.
            checkout: Checkout result for the worktree to repair.

        Returns:
            (summary_result, all_validation_results)
        """
        logger.info(
            "Starting LLM repair for %s#%d — budget=%d, top_n=%d, model=%s",
            bug.project,
            bug.bug_id,
            self._repair_config.budget,
            self._repair_config.top_n_locations,
            self._repair_config.model_name,
        )
        outcome = run_validation_loop(
            self,
            bug,
            checkout,
            budget=self._repair_config.budget,
            stop_on_first=self._repair_config.stop_on_first,
        )
        return outcome.summary, outcome.all_results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_patches_for_location(
        self,
        bug: BugIdentifier,
        checkout: CheckoutResult,
        location: RankedLocation,
    ) -> list[PatchCandidate]:
        """Query the LLM up to max_patch_count times for one suspicious location."""
        if location.line is None:
            logger.warning(
                "Location %s has no line number — skipping", location.file_path
            )
            return []

        source_file_path = self._resolve_source_file_path(location, checkout)
        if source_file_path is None:
            logger.warning(
                "Cannot resolve source path for %s — skipping", location.file_path
            )
            return []

        try:
            function_source_text, function_start_line, function_end_line = (
                extract_function_source(source_file_path, location.line)
            )
        except Exception as extraction_error:
            logger.error(
                "Function extraction failed for %s:%d: %s",
                source_file_path,
                location.line,
                extraction_error,
            )
            return []

        messages = build_repair_prompt(location, function_source_text, function_start_line)

        logger.info(
            "Querying LLM for %s:%d (rank %d, score %s) — up to %d attempt(s)",
            source_file_path.name,
            location.line,
            location.rank,
            location.score,
            self._repair_config.max_patch_count,
        )

        location_patch_candidates: list[PatchCandidate] = []

        for attempt_index in range(self._repair_config.max_patch_count):
            try:
                llm_response_text = self._llm_client.complete(messages)
            except APRFrameworkError as llm_error:
                logger.warning(
                    "LLM call failed for %s:%d attempt %d: %s",
                    source_file_path.name,
                    location.line,
                    attempt_index,
                    llm_error,
                )
                continue

            diff_text = extract_patch_from_llm_response(
                llm_response_text,
                source_file_path,
                function_start_line,
                function_end_line,
            )

            if diff_text is None:
                logger.warning(
                    "No valid diff extracted from LLM response for %s:%d attempt %d",
                    source_file_path.name,
                    location.line,
                    attempt_index,
                )
                continue

            patch_candidate = PatchCandidate(
                bug=bug,
                patch_id=f"llm-{location.rank}-{attempt_index}",
                summary=(
                    f"LLM patch for {location.file_path}:{location.line} "
                    f"(attempt {attempt_index + 1})"
                ),
                diff_text=diff_text,
                metadata={
                    "location_rank": location.rank,
                    "location_score": location.score,
                    "llm_response": llm_response_text,
                    "model": self._repair_config.model_name,
                    # Used by run_validation_loop for progress logging
                    "source_path": str(source_file_path),
                    "target_line": location.line,
                },
            )
            location_patch_candidates.append(patch_candidate)

        logger.info(
            "Generated %d valid patch candidate(s) for %s:%d",
            len(location_patch_candidates),
            source_file_path.name,
            location.line,
        )
        return location_patch_candidates

    def _regression_context(self, checkout: CheckoutResult) -> RegressionContext:
        """Return the regression baseline, establishing it once on first use."""
        if self._regression is None:
            self._regression = build_regression_context(
                self._adapter,
                checkout,
                enabled=self._repair_config.regression_check,
                timeout=self._repair_config.timeout_seconds,
            )
        return self._regression

    # TODO: If a third repair backend is added, extract this into a module-level
    # utility shared by all backends (currently duplicated from TemplateRepairAlgorithm).
    def _resolve_source_file_path(
        self, location: RankedLocation, checkout: CheckoutResult
    ) -> Path | None:
        """Resolve a RankedLocation's file_path to an absolute Path in the worktree."""
        file_path_str = location.file_path
        if not file_path_str:
            return None

        file_path = Path(file_path_str)

        if file_path.is_absolute():
            if file_path.exists():
                return file_path
            return None

        resolved_file_path = (checkout.worktree / file_path).resolve()
        if resolved_file_path.exists():
            return resolved_file_path

        # FauxPy sometimes emits a leading "./" component — strip and retry.
        parts = file_path.parts
        if parts and parts[0] in (".", "./"):
            stripped_file_path = (
                Path(*parts[1:]) if len(parts) > 1 else Path(file_path_str)
            )
            worktree_stripped_path = (
                checkout.worktree / stripped_file_path
            ).resolve()
            if worktree_stripped_path.exists():
                return worktree_stripped_path

        logger.warning(
            "Source file not found: %s (worktree: %s)", file_path_str, checkout.worktree
        )
        return None


def _parse_source_file_path_from_diff(diff_text: str) -> Path | None:
    """Extract the absolute source file path from the first '--- ' line of a diff."""
    for diff_line in diff_text.splitlines():
        if diff_line.startswith("--- "):
            # Strip the '--- ' prefix; handle optional tab-delimited timestamp.
            raw_path = diff_line[4:].split("\t")[0].strip()
            if raw_path:
                return Path(raw_path)
    return None
