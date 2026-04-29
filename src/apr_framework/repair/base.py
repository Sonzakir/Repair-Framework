from abc import ABC, abstractmethod

from apr_framework.core.models import (
    BugIdentifier,
    CheckoutResult,
    PatchCandidate,
    RepairAttemptResult,
)


class RepairAlgorithm(ABC):
    """
    Abstract Base Class for reapir algorithms
    """

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_patches(
        self, bug: BugIdentifier, checkout: CheckoutResult
    ) -> list[PatchCandidate]:
        """
        Patch generation entry proint of a repair algorithm
        Generates candidate patches for the given buggy program version

        It receives the bug identity and the checked-out buggy workspace
            Analyzes the program state
                and returns zero or more candidate patches that may repair the defect.

        Args:
            bug (BugIdentifier): Identifier of the bug for which patches are generated
            checkout (CheckoutResult): Result of the benchmark checkout operation
        Returns:
            list [PatchCandidate]: List of PatchCandidate objects proposed by the repair algorithm.
        """
        raise NotImplementedError

    @abstractmethod
    def validate_patch(
        self, bug: BugIdentifier, checkout: CheckoutResult, patch: PatchCandidate
    ) -> RepairAttemptResult:
        """

        Validates the generated patch candidate for the given bug

        Args:
            bug (BugIdentifier): Identifier of the bug being repaired
            checkout (CheckoutResult): Result of the benchmark checkout operation
            patch (PatchCandidate): Candidate patch to validate

        Returns:
            RepairAttemptResult: RepaitAttemptResult describing the outcome of the validation process for the given patch candidate
        """
        raise NotImplementedError
