from abc import ABC, abstractmethod
from pathlib import Path

from apr_framework.core.models import EvaluationResult


class ReportGenerator(ABC):
    """
    Abstract interface for generating run reports
    #TODO: Currently DRAFT
    """

    @property
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def write_summary(self, results: list[EvaluationResult], output_dir: Path) -> Path:
        """
        Writes a summary report for the given evaluation results to the specified output directory
        Args:
            results (list[EvaluationResult]): Evaluation results to include in the summary report
            output_dir (Path): Directory where the summary report should be written
        Returns:
            Path: Path to the generated summary report file
        """
        raise NotImplementedError
