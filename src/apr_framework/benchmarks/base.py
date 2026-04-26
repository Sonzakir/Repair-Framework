"""
Abstract Base Class for Benchmarks
"""

from abc import ABC, abstractmethod

from apr_framework.core.models import BugInfo


class BenchMarkAdapter(ABC):
    @abstractmethod
    def list_projects(self) -> list[str]:
        """lists available projects in the benchmark

        Returns:
            list[str]: _description_
        """
        ...

    #

    @abstractmethod
    def list_bugs(self, project: str) -> list[BugInfo]: ...

    # list of bugs for a given project

    @abstractmethod
    def checkout(self, project: str, bug_id: int) -> bool: ...

    # checkout a selected bug: Download and setup this specific buggy version of the code

    @abstractmethod
    def run_tests(self, project: str, bug_id: int) -> dict: ...

    # run the tests (failing) and return structured test results
