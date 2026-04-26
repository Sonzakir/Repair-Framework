"""
Initial config object for the bugsinpy
I have decided to use 2 local paths for the BugsinPy
/.tools/bugsinpy -> for the BugsInPy repository/project so that we do not assume that this project is globally available when someone tries to run the APR framework
/.workspace/bugsinpy -> for the checked out buggy project, meaning local copy of the project so that we can work with it
"""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from apr_framework.benchmarks.base import BenchmarkAdapter
from apr_framework.core.models import BugIdentifier, BugInfo, CheckoutResult

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
            repo_dir=project_root / ".tools" / ".bugsinpy",
            workspace_dir=project_root / ".workspace" / ".bugsinpy",
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
            raise RuntimeError("Git is required to bootstrap BugsInPy")

        # clone the repository
        subprocess.run(
            [git_executable, "clone", BUGSINPY_REPOSITORY_URL, str(self.repo_dir)],
            check=True,
            text=True,
        )


class BugsInPyAdapter(BenchmarkAdapter):
    def __init__(self, toolchain: BugsInPyToolchain) -> None:
        self._toolchain = toolchain

    @property
    def name(self) -> str:
        return "bugsinpy"

    def list_projects(self) -> list[str]:
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
        bugs_dir = self._toolchain.repo_dir / "projects" / project / "bugs"
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
        Wrapper around the BugsInPy's bugsinpy-checkout command
        See: .tools\bugsinpy\framework\bin\bugsinpy-checkout
        Args:
            bug (BugIdentifier): A BugIdentifier model that contains benchmark name, project name , id of this specific bug
            destination (Path): Working directory of the checked out project

        Returns:
            CheckoutResult:  Outcome of a benchmark checkout operation
        """
        destination.mkdir(parents=True, exist_ok=True)

        command = [
            "bash",
            str(self._toolchain.command_path("bugsinpy-checkout")),
            "-p",  # The name of the project
            bug.project,
            "-i",  # ID of the Bug from this project
            str(bug.bug_id),
            "-v",
            "0",  # TODO: Currently always checked-out buggy version
            "w",  # Working directory
            str(destination),
        ]

        completed = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True,
        )

        project_dir = destination / bug.project

        return CheckoutResult(
            bug=bug,
            worktree=project_dir,
            success=True,
            message=completed.stdout.strip(),
        )
