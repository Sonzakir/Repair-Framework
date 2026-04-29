"""
Initial config object for the bugsinpy
I have decided to use 2 local paths for the BugsinPy
/.tools/bugsinpy -> for the BugsInPy repository/project so that we do not assume that this project is globally available when someone tries to run the APR framework
/.workspace/bugsinpy -> for the checked out buggy project, meaning local copy of the project so that we can work with it
"""

import re
import shutil
import subprocess
from dataclasses import dataclass
from os import environ
from pathlib import Path

from apr_framework.benchmarks.base import BenchmarkAdapter
from apr_framework.core.exceptions import BenchmarkError, ConfigurationError
from apr_framework.core.models import (
    BugIdentifier,
    BugInfo,
    CheckoutResult,
    TestRunResult,
)

BUGSINPY_REPOSITORY_URL = "https://github.com/soarsmu/BugsInPy.git"


@dataclass(frozen=True)
class BugsInPyConfig:
    repo_dir: Path  # Local copy of the BugsInPy project
    workspace_dir: Path  # Checked-out project

    @classmethod
    def from_project_root(cls, project_root: Path) -> "BugsInPyConfig":
        """
        Create a BugsInPyConfig instance from the root directory of a project.

        - repo_dir: the directory where the BugsInPy repository/tooling is stored
        - workspace_dir: the directory where BugsInPy working files are stored

        Args:
            project_root (Path): The root directory of the project

        Returns:
            BugsInPyConfig:  A BugsInPyConfig instance with repo_dir and workspace_dir initialized
        """
        return cls(
            repo_dir=project_root / ".tools" / "bugsinpy",
            workspace_dir=project_root / ".workspace" / "bugsinpy",
        )


class BugsInPyToolchain:
    """
    Toolchain wrapper to interact with the BugsInPy installation and setup
    """

    def __init__(self, config: BugsInPyConfig) -> None:
        self._config = config

    @property
    def repo_dir(self) -> Path:
        return self._config.repo_dir

    @property
    def workspace_dir(self) -> Path:
        return self._config.workspace_dir

    def is_installed(self) -> bool:
        """
        Boolean method to check whether the BugsInPy project is locally installed
        In BugsInPy /framework/bin contains required executable scripts (checkout,compile,test...)
        Returns:
            bool: True if the project is installed in repository directory
        """
        return (self.repo_dir / "framework" / "bin").exists()

    def command_path(self, command_name: str) -> Path:
        """
        Method to return path of the BugsInPy command
        Args:
            command_name (str): command name (buginpy-checkout/compile/test...)

        Returns:
            Path: Path of the command (for example .tools/bugsinpy/framework/bin/bugsinpy-checkout)
        """
        return self.repo_dir / "framework" / "bin" / command_name

    def bootstrap(self) -> None:
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        if self.is_installed():
            return

        # git configurations
        git_executable = shutil.which("git")
        if git_executable is None:
            raise ConfigurationError("Git is required to bootstrap BugsInPy")

        # clone the repository
        subprocess.run(
            [git_executable, "clone", BUGSINPY_REPOSITORY_URL, str(self.repo_dir)],
            check=True,
            text=True,
        )

    def ensure_installed(self) -> None:
        if not self.is_installed():
            raise BenchmarkError(
                "BugsInPy is not installed. Run `python -m apr_framework bugsinpy setup` first."
            )

    def resolve_bash(self) -> str:
        configured = environ.get("BUGSINPY_BASH")
        if configured:
            return configured

        candidate = shutil.which("bash")
        if candidate:
            return candidate

        raise ConfigurationError(
            "A working `bash` executable is required to run BugsInPy commands. "
            "Run the framework in the provided Docker environment or from a shell where `bash` is on PATH."
        )

    def run_bugsinpy(
        self,
        command_name: str,
        *args: str,
        cwd: Path | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        self.ensure_installed()
        command = [
            self.resolve_bash(),
            str(self.command_path(command_name)),
            *args,
        ]
        return subprocess.run(
            command,
            cwd=cwd,
            check=check,
            text=True,
            # capture_output=True,
        )


class BugsInPyAdapter(BenchmarkAdapter):
    def __init__(self, toolchain: BugsInPyToolchain) -> None:
        self._toolchain = toolchain

    @property
    def name(self) -> str:
        return "bugsinpy"

    @property
    def toolchain(self) -> BugsInPyToolchain:
        """
        Getter on BugsinPy Toolchain
        """
        return self._toolchain

    def list_projects(self) -> list[str]:
        self._toolchain.ensure_installed()
        projects_dir = self._toolchain.repo_dir / "projects"
        return sorted(
            entry.name
            for entry in projects_dir.iterdir()
            if entry.is_dir() and not entry.name.startswith(".")
        )

    def list_bugs(self, project: str) -> list[BugInfo]:
        """
        Given project name as a string, returns a list of all bugs in the project
        Args:
            project (str): Project name

        Returns:
            list[BugInfo]: List of bugs for that projects
        """
        self._toolchain.ensure_installed()
        bugs_dir = self._toolchain.repo_dir / "projects" / project / "bugs"
        if not bugs_dir.exists():
            raise BenchmarkError(f"Unknown BugsInPy project: {project}")
        bug_infos: list[BugInfo] = []

        for entry in sorted(bugs_dir.iterdir(), key=lambda path: path.name):
            if entry.is_dir() and entry.name.isdigit():
                bug_id = int(entry.name)

                identifier = BugIdentifier(
                    benchmark="bugsinpy", project=project, bug_id=bug_id
                )

                bug_infos.append(BugInfo(identifier=identifier, description=""))

        return bug_infos

    def checkout(self, bug: BugIdentifier, destination: Path) -> CheckoutResult:
        """
        Wrapper around the BugsInPy's bugsinpy-checkout command.
        Gets the buggy source code onto disk
        See: .tools\bugsinpy\framework\bin\bugsinpy-checkout
        Args:
            bug (BugIdentifier): A BugIdentifier model that contains benchmark name, project name , id of this specific bug
            destination (Path): Working directory of the checked out project

        Returns:
            CheckoutResult:  Outcome of a benchmark checkout operation
        """
        destination.mkdir(parents=True, exist_ok=True)

        completed = self._toolchain.run_bugsinpy(
            "bugsinpy-checkout",
            "-p",
            bug.project,
            "-i",
            str(bug.bug_id),
            "-v",
            "0",
            "-w",
            str(destination),
        )

        project_dir = destination / bug.project

        return CheckoutResult(
            bug=bug,
            worktree=project_dir,
            success=True,
            message=(completed.stdout or "").strip(),
        )

    def prepare_environment(self, checkout: CheckoutResult) -> None:
        """
        Makes checked-out buggy project runnable and testable before the framework executes tests or repair steps.
        See: .tools\bugsinpy\framework\bin\bugsinpy-compile
        Args:
            checkout (CheckoutResult): _description_
        """

        self._toolchain.run_bugsinpy(
            "bugsinpy-compile",
            cwd=checkout.worktree,
        )

        checkout.prepared = True

    def run_tests(self, checkout: CheckoutResult) -> TestRunResult:
        SUMMARY_PATTERN = re.compile(
            r"(?:(?P<failed>\d+)\s+failed)?[, ]*"
            r"(?:(?P<passed>\d+)\s+passed)?[, ]*"
            r"(?:(?P<errors>\d+)\s+error[s]?)?"
        )

        completed = self._toolchain.run_bugsinpy(
            "bugsinpy-test",
            cwd=checkout.worktree,
            check=False,
        )

        raw_output = "\n".join(
            part
            for part in [
                (completed.stdout or "").strip(),
                (completed.stderr or "").strip(),
            ]
            if part
        )

        failed = passed = errors = 0
        match = SUMMARY_PATTERN.search(raw_output)
        if match:
            failed = int(match.group("failed") or 0)
            passed = int(match.group("passed") or 0)
            errors = int(match.group("errors") or 0)

        return TestRunResult(
            bug=checkout.bug,
            results=[],
            raw_output=raw_output,
            total_count=failed + passed + errors,
            passed_count=passed,
            failed_count=failed,
            error_count=errors,
        )
