"""
Abstract Base Class for Benchmarks
TODO: Documentations must be fixed __description__
"""

from abc import ABC, abstractmethod
from pathlib import Path

from apr_framework.core.models import (
    BugIdentifier,
    BugInfo,
    CheckoutResult,
    TestRunResult,
)


class BenchmarkAdapter(ABC):
    """
    Abstract Base class for benchmark integrations
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the benchmark name used by the framework"""
        raise NotImplementedError

    @abstractmethod
    def list_projects(self) -> list[str]:
        """lists available projects in the benchmark

        Returns:
            list[str]: _description_
        """
        raise NotImplementedError

    #

    @abstractmethod
    def list_bugs(self, project: str) -> list[BugInfo]:
        """
        Returns all known bugs for a given project.
        Args:
            project (str): _description_

        Returns:
            list[BugInfo]: _description_
        """
        raise NotImplementedError

    @abstractmethod
    def checkout(self, bug: BugIdentifier, destination: Path) -> CheckoutResult:
        """
        Checkout a selected buggy program version into the destination directory
        Download and setup this specific buggy version of the code
        Args:
            bug (BugIdentifier): _description_
            destination (Path): _description_

        Returns:
            CheckoutResult: _description_
        """
        raise NotImplementedError

    @abstractmethod
    def prepare_environment(self, checkout: CheckoutResult) -> None:
        """
        Prepare dependencies or environment for the checked out bug.
        Args:
            checkout (CheckoutResult): _description_
        """
        raise NotImplementedError

    @abstractmethod
    def run_tests(self, checkout: CheckoutResult) -> TestRunResult:
        """
        Run tests for the checkout bug and return structured results
        Args:
            checkout (CheckoutResult): _description_
        Returns:
            TestRunResult: _description_
        """
        raise NotImplementedError
