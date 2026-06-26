"""Template-based APR algorithm: SBFL/MBFL-guided AST mutation repair."""

import logging
import time
from pathlib import Path

from apr_framework.benchmarks.bugsinpy import BugsInPyAdapter
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
from apr_framework.repair.template.config import TemplateRepairConfig
from apr_framework.repair.template.patch_generator import generate_patches
from apr_framework.repair.template.validator import validate_patch

logger = logging.getLogger(__name__)


class TemplateRepairAlgorithm(RepairAlgorithm):
    """SBFL/MBFL-guided template-based repair algorithm.

    Uses ranked suspicious locations from a prior localization run to select
    *where* to apply fix templates, and AST mutation operators to determine
    *what* to try at each location.

    Constructor Args:
        localization_result: Ranked locations from a FauxPy (or hybrid) run.
        adapter:             BugsInPyAdapter used to invoke the test suite.
        config:              Repair configuration (budget, operators, etc.).
    """

    def __init__(
        self,
        localization_result: LocalizationResult,
        adapter: BugsInPyAdapter,
        config: TemplateRepairConfig | None = None,
    ) -> None:
        self._localization_result = localization_result
        self._adapter = adapter
        self._config = config or TemplateRepairConfig()

    @property
    def name(self) -> str:
        return "template-repair"

    # ------------------------------------------------------------------
    # RepairAlgorithm ABC
    # ------------------------------------------------------------------

    def generate_patches(
        self, bug: BugIdentifier, checkout: CheckoutResult
    ) -> list[PatchCandidate]:
        """Generate candidate patches for the top-N suspicious locations.

        Iterates over the top-N ranked locations from the localization result,
        resolves each to an absolute source path inside the checkout worktree,
        and applies all enabled mutation operators.  No test runs occur here.

        Args:
            bug:      Bug identifier.
            checkout: Checkout result containing the project worktree.

        Returns:
            All generated PatchCandidate objects (may be empty).
        """
        config = self._config
        locations = self._localization_result.ranked_locations[: config.top_n_locations]

        all_candidates: list[PatchCandidate] = []
        for location in locations:
            source_path = self._resolve_source_path(location, checkout)
            if source_path is None:
                logger.warning(
                    "Cannot resolve source path for location %s — skipping",
                    location.file_path,
                )
                continue

            target_line = location.line
            if target_line is None:
                logger.warning(
                    "Location %s has no line number — skipping", location.file_path
                )
                continue

            logger.info(
                "Generating patches for %s:%d (rank %d, score %s)",
                source_path,
                target_line,
                location.rank,
                location.score,
            )

            try:
                candidates = generate_patches(
                    source_path=source_path,
                    target_line=target_line,
                    operators=config.enabled_operators,
                    location=location,
                    bug=bug,
                )
            except Exception as exc:
                logger.error(
                    "Patch generation failed for %s:%d: %s",
                    source_path,
                    target_line,
                    exc,
                )
                continue

            logger.info(
                "Generated %d candidate(s) for %s:%d",
                len(candidates),
                source_path.name,
                target_line,
            )
            all_candidates.extend(candidates)

        return all_candidates

    def validate_patch(
        self, bug: BugIdentifier, checkout: CheckoutResult, patch: PatchCandidate
    ) -> RepairAttemptResult:
        """Validate a single patch candidate by applying it and running the test suite.

        Args:
            bug:      Bug identifier.
            checkout: Checkout result containing the target worktree.
            patch:    Candidate patch to validate.

        Returns:
            RepairAttemptResult with status PLAUSIBLE, FAILED, or NO_PATCH.
        """
        try:
            updated_patch, is_plausible = validate_patch(
                candidate=patch,
                checkout=checkout,
                adapter=self._adapter,
                config=self._config,
            )
        except Exception as exc:
            logger.error(
                "Validation raised an unexpected error for %s: %s",
                patch.patch_id,
                exc,
            )
            return RepairAttemptResult(
                bug=bug,
                patch=patch,
                status=RepairStatus.FAILED,
                validation_summary=f"Validation error: {exc}",
            )

        if is_plausible:
            logger.info("Plausible patch found: %s", updated_patch.patch_id)
            return RepairAttemptResult(
                bug=bug,
                patch=updated_patch,
                status=RepairStatus.PLAUSIBLE,
                validation_summary=f"All tests passed with patch {updated_patch.patch_id}.",
            )

        passed = updated_patch.metadata.get("test_passed_count", "?")
        failed = updated_patch.metadata.get("test_failed_count", "?")
        errors = updated_patch.metadata.get("test_error_count", "?")
        return RepairAttemptResult(
            bug=bug,
            patch=updated_patch,
            status=RepairStatus.FAILED,
            validation_summary=(
                f"Patch {updated_patch.patch_id} did not fix all tests "
                f"(passed={passed}, failed={failed}, errors={errors})."
            ),
        )

    # ------------------------------------------------------------------
    # Orchestration — full repair loop with budget
    # ------------------------------------------------------------------

    def repair(
        self, bug: BugIdentifier, checkout: CheckoutResult
    ) -> tuple[RepairAttemptResult, list[RepairAttemptResult]]:
        """Run the full repair loop with budget and optional early stopping.

        1. Generate all candidate patches from top-N locations.
        2. Validate candidates one by one until budget is exhausted.
        3. Collect all per-candidate results.
        4. Return (summary_result, all_results).

        The summary_result uses the first plausible patch (status=PLAUSIBLE),
        or RepairStatus.FAILED if candidates existed but none passed,
        or RepairStatus.NO_PATCH if no candidates were generated.

        Args:
            bug:      Bug identifier.
            checkout: Checkout result for the worktree to repair.

        Returns:
            (summary_result, all_validation_results)
        """
        config = self._config
        started_at = time.monotonic()

        logger.info(
            "Starting template repair for %s#%d — budget=%d, top_n=%d, operators=%s",
            bug.project,
            bug.bug_id,
            config.budget,
            config.top_n_locations,
            config.enabled_operators,
        )

        # Step 1: generate all candidates (no test runs)
        candidates = self.generate_patches(bug, checkout)
        logger.info("Total candidates generated: %d", len(candidates))

        if not candidates:
            elapsed = time.monotonic() - started_at
            logger.info("No candidates generated in %.1fs.", elapsed)
            no_patch_result = RepairAttemptResult(
                bug=bug,
                patch=None,
                status=RepairStatus.NO_PATCH,
                validation_summary="No mutation operators matched at the top suspicious locations.",
            )
            return no_patch_result, []

        # Step 2: validate with budget
        budget_remaining = config.budget
        all_results: list[RepairAttemptResult] = []
        plausible_results: list[RepairAttemptResult] = []

        for candidate in candidates:
            if budget_remaining <= 0:
                logger.info("Budget exhausted — stopping validation loop.")
                break

            op = candidate.metadata.get("operator", "?")
            src = candidate.metadata.get("source_path", "?")
            line = candidate.metadata.get("target_line", "?")
            logger.info(
                "Validating %s (op=%s, file=%s:%s) — budget remaining: %d",
                candidate.patch_id,
                op,
                Path(src).name if src != "?" else src,
                line,
                budget_remaining,
            )

            try:
                result = self.validate_patch(bug, checkout, candidate)
            except Exception as exc:
                logger.error(
                    "Unexpected error validating %s: %s", candidate.patch_id, exc
                )
                result = RepairAttemptResult(
                    bug=bug,
                    patch=candidate,
                    status=RepairStatus.FAILED,
                    validation_summary=f"Unexpected validation error: {exc}",
                )

            all_results.append(result)
            budget_remaining -= 1

            if result.status == RepairStatus.PLAUSIBLE:
                plausible_results.append(result)
                logger.info(
                    "Plausible patch: %s",
                    result.patch.patch_id if result.patch else "?",
                )
                if config.stop_on_first:
                    logger.info("stop_on_first=True — stopping after first plausible patch.")
                    break

        elapsed = time.monotonic() - started_at
        validated_count = len(all_results)
        plausible_count = len(plausible_results)

        logger.info(
            "Repair loop finished in %.1fs: %d validated, %d plausible",
            elapsed,
            validated_count,
            plausible_count,
        )

        if plausible_results:
            best = plausible_results[0]
            summary = RepairAttemptResult(
                bug=bug,
                patch=best.patch,
                status=RepairStatus.PLAUSIBLE,
                validation_summary=(
                    f"Found {plausible_count} plausible patch(es) out of "
                    f"{validated_count} validated (budget: {config.budget}, "
                    f"elapsed: {elapsed:.1f}s). "
                    f"Best: {best.patch.patch_id if best.patch else '?'}."
                ),
            )
        elif validated_count > 0:
            summary = RepairAttemptResult(
                bug=bug,
                patch=None,
                status=RepairStatus.FAILED,
                validation_summary=(
                    f"No plausible patch found. "
                    f"Validated {validated_count}/{len(candidates)} candidates "
                    f"(budget: {config.budget}, elapsed: {elapsed:.1f}s)."
                ),
            )
        else:
            summary = RepairAttemptResult(
                bug=bug,
                patch=None,
                status=RepairStatus.NO_PATCH,
                validation_summary=(
                    f"No candidates could be validated "
                    f"(budget: {config.budget}, elapsed: {elapsed:.1f}s)."
                ),
            )

        return summary, all_results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_source_path(
        self, location: RankedLocation, checkout: CheckoutResult
    ) -> Path | None:
        """Resolve a RankedLocation's file_path to an absolute Path in the worktree.

        FauxPy outputs paths relative to the project root (the checkout worktree),
        sometimes prefixed with `./`.  This method strips the prefix and joins with
        the worktree to produce a concrete, verifiable Path.
        """
        raw = location.file_path
        if not raw:
            return None

        candidate = Path(raw)

        # Absolute path — verify it sits under the worktree.
        if candidate.is_absolute():
            if candidate.exists():
                return candidate
            return None

        # Relative path — join with worktree.
        resolved = (checkout.worktree / candidate).resolve()
        if resolved.exists():
            return resolved

        # Try stripping a leading "./" component that FauxPy sometimes emits.
        parts = candidate.parts
        if parts and parts[0] in (".", "./"):
            stripped = Path(*parts[1:]) if len(parts) > 1 else Path(raw)
            resolved2 = (checkout.worktree / stripped).resolve()
            if resolved2.exists():
                return resolved2

        logger.warning(
            "Source file not found: %s (worktree: %s)", raw, checkout.worktree
        )
        return None
