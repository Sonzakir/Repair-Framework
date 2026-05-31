import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from apr_framework.core.exceptions import ConfigurationError
from apr_framework.core.models import (
    BugIdentifier,
    CheckoutResult,
    LocalizationResult,
    RankedLocation,
    TestRunResult,
)
from apr_framework.localization.base import FaultLocalizer


def _completed_output(completed: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(
        part
        for part in [
            (completed.stdout or "").strip(),
            (completed.stderr or "").strip(),
        ]
        if part
    )


def _validate_string_list(name: str, values: list[str]) -> None:
    if not isinstance(values, list):
        raise ConfigurationError(f"FauxPy {name} must be a list of strings")
    if any(not isinstance(value, str) for value in values):
        raise ConfigurationError(f"FauxPy {name} must contain only strings.")


def load_pytest_targets(run_test_script: Path) -> list[str]:
    if not run_test_script.exists():
        raise ConfigurationError(f"No BugsInPy test script found at {run_test_script}")

    targets: list[str] = []
    for raw_line in run_test_script.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = shlex.split(line)
        if not parts:
            continue

        if parts[0] == "pytest":
            targets.extend(parts[1:])
            continue

        if len(parts) >= 3 and parts[1:3] == ["-m", "pytest"]:
            targets.extend(parts[3:])
            continue

        raise ConfigurationError(
            "FauxPy localization currently supports BugsInPy run_test.sh lines "
            f"that invoke pytest directly. Unsupported line: {line}"
        )

    if not targets:
        raise ConfigurationError(f"No pytest targets found in {run_test_script}")

    return targets


@dataclass(frozen=True)
class FauxPyConfig:
    family: str = "sbfl"
    src: str = "."
    test_targets: list[str] = field(default_factory=list)
    failing_tests: list[str] = field(default_factory=list)
    top_n: int | None = None

    def __post_init__(self) -> None:
        if self.family != "sbfl":
            raise ConfigurationError("Currently the FauxPy integration supports only SBFL.")
        if not isinstance(self.src, str) or not self.src.strip():
            raise ConfigurationError("FauxPy src must be a non-empty string.")
        if self.top_n is not None:
            if not isinstance(self.top_n, int) or self.top_n <= 0:
                raise ConfigurationError("FauxPy top_n must be a positive integer or None.")

        _validate_string_list("test_targets", self.test_targets)
        _validate_string_list("failing_tests", self.failing_tests)


class DockerCommandRunner(Protocol):
    def run_command(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        check: bool = True,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        ...


class FauxPyToolchain:
    """
    Wraps command execution for FauxPy inside a prepared benchmark environment.
    """

    def __init__(self, runner: DockerCommandRunner) -> None:
        self._runner = runner

    def localize(self, config: FauxPyConfig, checkout: CheckoutResult) -> LocalizationResult:
        python = checkout.worktree / "env" / "bin" / "python"
        if not python.exists():
            raise ConfigurationError(
                f"No prepared virtual environment found at {python}. "
                "Run `python -m apr_framework bugsinpy compile "
                f"{checkout.bug.project} {checkout.bug.bug_id}` first."
            )

        self._ensure_fauxpy_installed(python, checkout.worktree)

        completed = self._runner.run_command(
            [
                str(python),
                "-m",
                "pytest",
                *config.test_targets,
                "--src",
                config.src,
            ],
            cwd=checkout.worktree,
            check=False,
            capture_output=True,
        )
        raw_output = _completed_output(completed)

        if completed.returncode not in {0, 1}:
            raise ConfigurationError(
                "FauxPy localization command failed. "
                f"{raw_output}".strip()
            )

        ranked_locations, formula = parse_fauxpy_sbfl_output(
            raw_output,
            top_n=config.top_n,
        )

        return LocalizationResult(
            bug=checkout.bug,
            backend="fauxpy",
            ranked_locations=ranked_locations,
            metadata={
                "family": config.family,
                "src": config.src,
                "test_targets": list(config.test_targets),
                "score_formula": formula,
                "raw_output": raw_output,
                "returncode": completed.returncode,
            },
        )

    def _ensure_fauxpy_installed(self, python: Path, cwd: Path) -> None:
        show = self._runner.run_command(
            [str(python), "-m", "pip", "show", "fauxpy"],
            cwd=cwd,
            check=False,
            capture_output=True,
        )
        if show.returncode == 0:
            return

        install = self._runner.run_command(
            [str(python), "-m", "pip", "install", "fauxpy"],
            cwd=cwd,
            check=False,
            capture_output=True,
        )
        if install.returncode != 0:
            raise ConfigurationError(
                "FauxPy is not installed in the project environment and installation "
                f"failed. {_completed_output(install)}".strip()
            )


class FauxPyLocalizer(FaultLocalizer):
    def __init__(self, config: FauxPyConfig, toolchain: FauxPyToolchain) -> None:
        self._config = config
        self._toolchain = toolchain

    @property
    def name(self) -> str:
        return "fauxpy"

    def localize(
        self,
        bug: BugIdentifier,
        checkout: CheckoutResult,
        test_result: TestRunResult | None = None,
    ) -> LocalizationResult:
        return self._toolchain.localize(self._config, checkout)


def parse_fauxpy_sbfl_output(
    raw_output: str,
    *,
    top_n: int | None = None,
) -> tuple[list[RankedLocation], str | None]:
    formula: str | None = None
    rows: list[RankedLocation] = []
    in_selected_table = False

    formula_pattern = re.compile(r"Scores for (?P<formula>.+?)\s+\|")
    row_pattern = re.compile(
        r"^(?P<file>.+?)\s+\|\s+(?P<line>\d+)\s+\|\s+(?P<score>-?\d+(?:\.\d+)?)\s*$"
    )

    for raw_line in raw_output.splitlines():
        line = raw_line.rstrip()

        formula_match = formula_pattern.search(line)
        if formula_match:
            if formula is not None and rows:
                break
            formula = formula_match.group("formula").strip()
            in_selected_table = True
            continue

        if not in_selected_table:
            continue

        if not line.strip() or line.lstrip().startswith("-") or line.strip().startswith("|"):
            continue
        if line.strip().startswith("File"):
            continue

        row_match = row_pattern.match(line)
        if row_match is None:
            if rows:
                break
            continue

        file_path = row_match.group("file").strip()
        line_number = int(row_match.group("line"))
        score = float(row_match.group("score"))
        rows.append(
            RankedLocation(
                rank=len(rows) + 1,
                file_path=file_path,
                location=f"{file_path}:{line_number}",
                score=score,
                line=line_number,
                raw_location=line.strip(),
                metadata={"score_formula": formula},
            )
        )

        if top_n is not None and len(rows) >= top_n:
            break

    return rows, formula
