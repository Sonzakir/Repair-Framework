from abc import ABC, abstractmethod

from apr_framework.core.models import (
    BugIdentifier,
    CheckoutResult,
    LocalizationResult,
    TestRunResult,
)

"""
Abstract base class for fault localization components
#TODO: Currently DRAFT
"""


class FaultLocalizer(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def localize(
        self, bug: BugIdentifier, checkout: CheckoutResult, test_result: TestRunResult
    ) -> LocalizationResult:
        """
        Analyzes the checked-out buggy program and return suspicious code locations

        Receives the bug identity, the checked-out project state, and the result of
        the executed tests, and produces a structured localization result containing
        the ranked suspicious locations and optional metadata.

        Args:
            bug (BugIdentifier): Identifier of the bug being analyzed
            checkout (CheckoutResult): Result of the benchmark checkout operation
            test_result (TestRunResult): Structured result of the executed test run that provides the failure information used for localization

        Returns:
            LocalizationResult: LocalizationResult containing the suspicious locations produced by the localizer.
        """
        raise NotImplementedError
