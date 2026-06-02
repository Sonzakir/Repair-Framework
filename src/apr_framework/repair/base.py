from abc import ABC, abstractmethod

from apr_framework.core.models import (
    BugIdentifier,
    CheckoutResult,
    PatchCandidate,
    RepairAttemptResult,
)


class RepairAlgorithm(ABC):
    """
    Interface for repair algorithms that generate and validate candidate patches.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Stable repair algorithm name used in logs, reports, and run metadata.
        """
        raise NotImplementedError

    @abstractmethod
    def generate_patches(
        self, bug: BugIdentifier, checkout: CheckoutResult
    ) -> list[PatchCandidate]:
        """
        Generate candidate patches for a checked-out buggy program.

        Args:
            bug: Identifier of the bug for which patches are generated.
            checkout: Checkout result containing the buggy project worktree.

        Returns:
            Candidate patches proposed by the repair algorithm. An empty list
            means the algorithm did not produce a patch for this bug.
        """
        raise NotImplementedError

    @abstractmethod
    def validate_patch(
        self, bug: BugIdentifier, checkout: CheckoutResult, patch: PatchCandidate
    ) -> RepairAttemptResult:
        """
        Validate a generated patch candidate for a checked-out bug.

        Args:
            bug: Identifier of the bug being repaired.
            checkout: Checkout result containing the target worktree.
            patch: Candidate patch to validate.

        Returns:
            Validation outcome for the given candidate patch.
        """
        raise NotImplementedError
