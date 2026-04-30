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
        capture_output: bool = False,
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
            capture_output=capture_output,
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

    def _project_aliases(self) -> dict[str, str]:
        projects_dir = self._toolchain.repo_dir / "projects"
        aliases: dict[str, str] = {}

        for entry in projects_dir.iterdir():
            if not entry.is_dir() or entry.name.startswith("."):
                continue

            canonical = entry.name
            for alias in {
                canonical,
                canonical.lower(),
                canonical.replace("-", "."),
                canonical.lower().replace("-", "."),
            }:
                aliases.setdefault(alias, canonical)

        return aliases

    def resolve_project(self, project: str) -> str:
        self._toolchain.ensure_installed()
        aliases = self._project_aliases()

        for candidate in (project, project.lower(), project.replace(".", "-")):
            resolved = aliases.get(candidate)
            if resolved:
                return resolved

        raise BenchmarkError(f"Unknown BugsInPy project: {project}")

    def list_projects(self) -> list[str]:
        self._toolchain.ensure_installed()
        return sorted(set(self._project_aliases().values()))

    def list_bugs(self, project: str) -> list[BugInfo]:
        """
        Given project name as a string, returns a list of all bugs in the project
        Args:
            project (str): Project name

        Returns:
            list[BugInfo]: List of bugs for that projects
        """
        canonical_project = self.resolve_project(project)
        bugs_dir = self._toolchain.repo_dir / "projects" / canonical_project / "bugs"
        bug_infos: list[BugInfo] = []

        for entry in sorted(bugs_dir.iterdir(), key=lambda path: path.name):
            if entry.is_dir() and entry.name.isdigit():
                bug_id = int(entry.name)

                identifier = BugIdentifier(
                    benchmark="bugsinpy", project=canonical_project, bug_id=bug_id
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
        canonical_project = self.resolve_project(bug.project)
        canonical_bug = BugIdentifier(
            benchmark=bug.benchmark,
            project=canonical_project,
            bug_id=bug.bug_id,
        )

        destination.mkdir(parents=True, exist_ok=True)

        completed = self._toolchain.run_bugsinpy(
            "bugsinpy-checkout",
            "-p",
            canonical_bug.project,
            "-i",
            str(canonical_bug.bug_id),
            "-v",
            "0",
            "-w",
            str(destination),
        )

        project_dir = destination / canonical_bug.project
        raw_message = "\n".join(
            part
            for part in [
                (completed.stdout or "").strip(),
                (completed.stderr or "").strip(),
            ]
            if part
        )

        if not project_dir.exists():
            raise BenchmarkError(
                f"BugsInPy checkout failed for project '{canonical_bug.project}' "
                f"(requested as '{bug.project}'). Expected worktree at {project_dir}. "
                f"{raw_message}".strip()
            )

        return CheckoutResult(
            bug=canonical_bug,
            worktree=project_dir,
            success=True,
            message=raw_message,
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
            "-w",
            str(checkout.worktree),
            cwd=checkout.worktree,
            check=False,
        )

        checkout.prepared = True

    def run_tests(self, checkout: CheckoutResult) -> TestRunResult:
        PYTEST_SUMMARY_PATTERN = re.compile(
            r"(?:(?P<failed>\d+)\s+failed)?[, ]*"
            r"(?:(?P<passed>\d+)\s+passed)?[, ]*"
            r"(?:(?P<errors>\d+)\s+error[s]?)?"
        )
        UNITTEST_TOTAL_PATTERN = re.compile(r"Ran\s+(?P<total>\d+)\s+test[s]?\s+in")
        UNITTEST_FAILURE_PATTERN = re.compile(r"failures=(?P<failed>\d+)")
        UNITTEST_ERROR_PATTERN = re.compile(r"errors=(?P<errors>\d+)")

        completed = self._toolchain.run_bugsinpy(
            "bugsinpy-test",
            "-w",
            str(checkout.worktree),
            cwd=checkout.worktree,
            check=False,
            capture_output=True,
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
        total = 0

        match = PYTEST_SUMMARY_PATTERN.search(raw_output)
        if match:
            failed = int(match.group("failed") or 0)
            passed = int(match.group("passed") or 0)
            errors = int(match.group("errors") or 0)
            total = failed + passed + errors

        total_match = UNITTEST_TOTAL_PATTERN.search(raw_output)
        if total_match:
            total = int(total_match.group("total"))
            failed_match = UNITTEST_FAILURE_PATTERN.search(raw_output)
            error_match = UNITTEST_ERROR_PATTERN.search(raw_output)
            failed = int(failed_match.group("failed")) if failed_match else 0
            errors = int(error_match.group("errors")) if error_match else 0
            passed = max(total - failed - errors, 0)

        return TestRunResult(
            bug=checkout.bug,
            results=[],
            raw_output=raw_output,
            total_count=total,
            passed_count=passed,
            failed_count=failed,
            error_count=errors,
        )
