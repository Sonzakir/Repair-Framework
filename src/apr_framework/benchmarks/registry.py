from pathlib import Path

from apr_framework.benchmarks.base import BenchmarkAdapter
from apr_framework.benchmarks.bugsinpy import (
    BugsInPyAdapter,
    BugsInPyConfig,
    BugsInPyToolchain,
)


def create_bugsinpy_adapter(project_root: Path) -> BenchmarkAdapter:
    """
    Registry for `BugsInPy`
    Creates the project directory for the BugsInPy and setups required tools for BugsInPy
    Args:
        project_root (Path): Path of the Framework Root

    Returns:
        BenchmarkAdapter: BugsInPyAdapter to use BugsInPy
    """

    config = BugsInPyConfig.from_project_root(project_root)
    toolchain = BugsInPyToolchain(config)
    return BugsInPyAdapter(toolchain)


def list_benchmark_names() -> list[str]:
    """

    Returns:
        list[str]: List of names of the all benchmarks
    """
    return ["bugsinpy"]
