"""
Define the shated domain models (shared dataclasses and enums) used across subsystems
Every other subsystem should be able to exchange data through these models
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


################## Statuses ####################
class TestStatus(str, Enum):
    """
    Outcome of the test execution
    Values:
        PASSED: Test execution succeeded and no failures occurred
        FAILED: Tests ran successfully, but at least one test failed
        ERROR: The test execution broke
    """

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class RepairStatus(str, Enum):
    """
    Outcome of the repair attempt
    Values:
        PLAUSIBLE: A candidate patch passes the available test suite.
        CORRECT: A candidate patch matches the ground-truth fix or is otherwise
            verified as semantically correct.
        FAILED: Candidate patches were generated, but none passed validation.
        NO_PATCH: The repair algorithm did not produce any candidate patch.
    """

    PLAUSIBLE = "plausible"
    CORRECT = "correct"
    FAILED = "failed"
    NO_PATCH = "no_patch"


# TODO: Benchmarks as enums? (Since we have a limited number of benchmarks)

################## Models ######################


@dataclass(frozen=True)
class BugIdentifier:
    """
    Reference to a Bug
    """

    benchmark: str
    project: str
    bug_id: int


@dataclass(frozen=True)
class BugInfo:
    """
    Descriptive metadata for the Bug
    """

    identifier: BugIdentifier
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckoutResult:
    """
    Represents the outcome of a benchmark checkout operation.

    Records whether the checkout succeeded and provides a
    human-readable message about the operation result.
    """

    bug: BugIdentifier
    worktree: Path
    success: bool
    message: str = ""


@dataclass
class TestCaseResult:
    """
    Structured result of a single executed test case

    """

    name: str
    status: TestStatus
    message: str = ""


@dataclass
class TestRunResult:
    """
    Structured result of a complete test execution for a specific bug

    Stores the bug under test, outcomes of the executed test cases and optional textual output produced by the test command
    """

    bug: BugIdentifier
    results: list[TestCaseResult]
    raw_output: str = ""

    @property
    def total(self) -> int:
        """
        Returns:
            int: Total number of executed test cases in this run
        """
        return len(self.results)

    @property
    def passed(self) -> int:
        """
        Returns:
            int: Number of test cases with PASSED status.
        """
        return sum(result.status == TestStatus.PASSED for result in self.results)

    @property
    def failed(self) -> int:
        """
        Returns:
            int: Number of test cases with FAILED status.
        """
        return sum(result.status == TestStatus.FAILED for result in self.results)


@dataclass
class LocalizationResult:
    """Structured result of fault localization, containing the ranked suspicious code locations for a specific bug and optional metadata"""

    bug: BugIdentifier
    ranked_locations: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PatchCandidate:
    """
    One proposed fix produced by a repair algorithm
    """

    bug: BugIdentifier
    patch_id: str
    summary: str
    diff_text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RepairAttemptResult:
    """
    Outcome of validating or applying one PatchCandidate
    """

    bug: BugIdentifier
    patch: PatchCandidate | None
    status: RepairStatus
    validation_summary: str = ""


@dataclass
class EvaluationResult:
    """
    Result of one evaluation run for a specific bug, including its execution status and start/end timestamps
    """

    bug: BugIdentifier
    status: str
    started_at: datetime
    finished_at: datetime
