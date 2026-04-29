from abc import ABC, abstractmethod

from apr_framework.benchmarks.base import BenchmarkAdapter
from apr_framework.core.models import BugIdentifier, EvaluationResult
from apr_framework.localization.base import FaultLocalizer
from apr_framework.repair.base import RepairAlgorithm


class EvaluationRunner(ABC):
    """
    Abstract base class for experiment execution
    # TODO: Currently Draft
    """

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def run(
        self,
        bugs: list[BugIdentifier],
        benchmark: BenchmarkAdapter,
        repair: RepairAlgorithm,
        localizer: FaultLocalizer | None = None,
    ) -> list[EvaluationResult]:
        """
        Executes the evaluation pipeline for the given bugs and returns one EvaluationResult per processed bug.
        Args:
            bugs (list[BugIdentifier]): List of bugs to be processed in the pipeline
            benchmark (BenchmarkAdapter): Benchmark adapter used to access bug data, checkout buggy versions, and return tests
            repair (RepairAlgorithm): Repair component for generating and validating candidate patches
            localizer (FaultLocalizer | None, optional): Fault localization component used to identify suspicious code locations before repair. Defaults to None.

        Returns:
            list[EvaluationResult]: _description_
        """
        raise NotImplementedError
