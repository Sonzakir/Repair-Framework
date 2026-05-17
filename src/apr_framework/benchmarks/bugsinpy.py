"""
Initial config object for the bugsinpy
I have decided to use 2 local paths for the BugsinPy
/.tools/bugsinpy -> for the BugsInPy repository/project so that we do not assume that this project is globally available when someone tries to run the APR framework
/.workspace/bugsinpy -> for the checked out buggy project, meaning local copy of the project so that we can work with it
"""

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from os import environ
from pathlib import Path, PurePosixPath

from apr_framework.benchmarks.base import BenchmarkAdapter
from apr_framework.core.exceptions import BenchmarkError, ConfigurationError
from apr_framework.core.models import (
    BugIdentifier,
    BugInfo,
    CheckoutResult,
    TestRunResult,
)

BUGSINPY_REPOSITORY_URL = "https://github.com/Sonzakir/BugsInPy.git"
DEFAULT_BUGSINPY_CONTAINER = "apr-bugsinpy-executor"
DEFAULT_BUGSINPY_IMAGE = "apr-bugsinpy:local"
BUGSINPY_CONTAINER_HOME = PurePosixPath("/home/bugsinpy")
BUGSINPY_CONTAINER_WORKSPACE = PurePosixPath("/home/workspace")
BUGSINPY_PYENV_CACHE_VOLUME = "apr-bugsinpy-pyenv-cache"
BUGSINPY_PYENV_VERSIONS_VOLUME = "apr-bugsinpy-pyenv-versions"


def _completed_output(completed: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(
        part
        for part in [
            (completed.stdout or "").strip(),
            (completed.stderr or "").strip(),
        ]
        if part
    )


def _completed_returncode(completed: subprocess.CompletedProcess[str]) -> int:
    return getattr(completed, "returncode", 0)


@dataclass(frozen=True)
class BugsInPyConfig:
    repo_dir: Path  # Local copy of the BugsInPy project
    workspace_dir: Path  # Checked-out project
    project_root: Path | None = None  # Repair framework root as seen by this process

    def __post_init__(self) -> None:
        if self.project_root is not None:
            return

        if self.repo_dir.name == "bugsinpy" and self.repo_dir.parent.name == ".tools":
            project_root = self.repo_dir.parent.parent
        else:
            project_root = self.repo_dir.parent

        object.__setattr__(self, "project_root", project_root)

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
        project_root = project_root.resolve()
        return cls(
            repo_dir=project_root / ".tools" / "bugsinpy",
            workspace_dir=project_root / ".workspace" / "bugsinpy",
            project_root=project_root,
        )


class BugsInPyDockerExecutor:
    """
    Runs BugsInPy commands inside a long-lived sibling Docker container.
    """

    def __init__(self, config: BugsInPyConfig) -> None:
        self._config = config
        self._docker = environ.get("DOCKER", "docker")
        self._image = environ.get("BUGSINPY_IMAGE", DEFAULT_BUGSINPY_IMAGE)
        self._container = environ.get(
            "BUGSINPY_CONTAINER", DEFAULT_BUGSINPY_CONTAINER
        )

    @property
    def image(self) -> str:
        return self._image

    @property
    def container(self) -> str:
        return self._container

    @property
    def _project_root(self) -> Path:
        if self._config.project_root is None:
            raise ConfigurationError("BugsInPy project root is not configured.")
        return self._config.project_root

    def ensure_ready(self) -> None:
        self._ensure_docker_available()
        self._ensure_image()
        self._ensure_container()
        self._smoke_check()

    def run_bugsinpy(
        self,
        command_name: str,
        *args: str,
        cwd: Path | None = None,
        check: bool = True,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        self._ensure_docker_available()
        if not self._container_exists():
            raise BenchmarkError(
                "The BugsInPy executor container is not available. "
                "Run `python -m apr_framework bugsinpy setup` first."
            )

        if not self._container_running():
            self._run_docker(["start", self.container], check=True)

        container_cwd = (
            self._to_container_path(cwd)
            if cwd is not None
            else str(BUGSINPY_CONTAINER_WORKSPACE)
        )
        translated_args = [self._translate_argument(arg) for arg in args]
        command_path = str(BUGSINPY_CONTAINER_HOME / "framework" / "bin" / command_name)

        return self._run_docker(
            [
                "exec",
                "-w",
                container_cwd,
                self.container,
                "bash",
                command_path,
                *translated_args,
            ],
            check=check,
            capture_output=capture_output,
        )

    def _ensure_docker_available(self) -> None:
        if shutil.which(self._docker) is None:
            raise ConfigurationError(
                "Docker CLI is required to run BugsInPy in its executor container. "
                "Use the provided repair-framework container or install Docker CLI."
            )

        completed = self._run_docker(
            ["version", "--format", "{{.Server.Version}}"],
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            raise ConfigurationError(
                "Docker daemon is not reachable from the repair-framework container. "
                "Mount /var/run/docker.sock and make sure Docker is running. "
                f"{_completed_output(completed)}".strip()
            )

    def _ensure_image(self) -> None:
        if self._image_exists():
            return

        dockerfile = self._config.repo_dir / "Dockerfile"
        if not dockerfile.exists():
            raise BenchmarkError(
                f"Cannot build BugsInPy image: expected Dockerfile at {dockerfile}"
            )

        self._run_docker(
            [
                "build",
                "-t",
                self.image,
                "-f",
                str(dockerfile),
                str(self._config.repo_dir),
            ],
            check=True,
        )

    def _ensure_container(self) -> None:
        if self._container_exists() and not self._container_has_expected_mounts():
            self._run_docker(["rm", "-f", self.container], check=True)

        if not self._container_exists():
            self._create_container()

        if not self._container_running():
            self._run_docker(["start", self.container], check=True)

    def _create_container(self) -> None:
        host_project_root = self._host_project_root()
        host_bugsinpy_repo = host_project_root / ".tools" / "bugsinpy"
        host_bugsinpy_workspace = host_project_root / ".workspace" / "bugsinpy"

        self._run_docker(
            [
                "create",
                "--name",
                self.container,
                "-w",
                str(BUGSINPY_CONTAINER_WORKSPACE),
                "-e",
                "BUGSINPY_HOME=/home/bugsinpy",
                "-e",
                "PYENV_ROOT=/root/.pyenv",
                "-v",
                f"{host_bugsinpy_repo / 'framework'}:/home/bugsinpy/framework",
                "-v",
                f"{host_bugsinpy_repo / 'projects'}:/home/bugsinpy/projects",
                "-v",
                f"{host_bugsinpy_workspace}:/home/workspace",
                "-v",
                f"{BUGSINPY_PYENV_VERSIONS_VOLUME}:/root/.pyenv/versions",
                "-v",
                f"{BUGSINPY_PYENV_CACHE_VOLUME}:/root/.pyenv/cache",
                self.image,
                "sleep",
                "infinity",
            ],
            check=True,
        )

    def _smoke_check(self) -> None:
        completed = self._run_docker(
            [
                "exec",
                self.container,
                "test",
                "-x",
                "/home/bugsinpy/framework/bin/bugsinpy-checkout",
            ],
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            raise BenchmarkError(
                "The BugsInPy executor container is running, but its mounted "
                "BugsInPy checkout is not usable. Remove the stale container "
                f"`{self.container}` and run setup again. {_completed_output(completed)}".strip()
            )

    def _image_exists(self) -> bool:
        return (
            self._run_docker(
                ["image", "inspect", self.image],
                check=False,
                capture_output=True,
            ).returncode
            == 0
        )

    def _container_exists(self) -> bool:
        return (
            self._run_docker(
                ["container", "inspect", self.container],
                check=False,
                capture_output=True,
            ).returncode
            == 0
        )

    def _container_running(self) -> bool:
        completed = self._run_docker(
            [
                "container",
                "inspect",
                "-f",
                "{{.State.Running}}",
                self.container,
            ],
            check=False,
            capture_output=True,
        )
        return completed.returncode == 0 and completed.stdout.strip() == "true"

    def _container_has_expected_mounts(self) -> bool:
        completed = self._run_docker(
            [
                "container",
                "inspect",
                "-f",
                "{{json .Mounts}}",
                self.container,
            ],
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            return False

        try:
            mounts = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return False

        destinations = {
            mount.get("Destination")
            for mount in mounts
            if isinstance(mount, dict)
        }
        return {
            "/home/bugsinpy/framework",
            "/home/bugsinpy/projects",
            "/home/workspace",
        }.issubset(destinations)

    def _host_project_root(self) -> Path:
        configured = environ.get("APR_HOST_PROJECT_ROOT")
        if configured:
            return Path(configured).expanduser().resolve()

        if Path("/.dockerenv").exists():
            raise ConfigurationError(
                "APR_HOST_PROJECT_ROOT must be set when the repair framework runs "
                "inside Docker. It must point to this repository on the host so "
                "the sibling BugsInPy container can mount the same files."
            )

        return self._project_root.resolve()

    def _translate_argument(self, arg: str) -> str:
        path = Path(arg)
        if not path.is_absolute():
            return arg

        try:
            return self._to_container_path(path)
        except ConfigurationError:
            return arg

    def _to_container_path(self, path: Path) -> str:
        resolved = path.resolve()

        try:
            relative = resolved.relative_to(self._config.workspace_dir.resolve())
            return str(BUGSINPY_CONTAINER_WORKSPACE / PurePosixPath(relative.as_posix()))
        except ValueError:
            pass

        try:
            relative = resolved.relative_to(self._config.repo_dir.resolve())
            return str(BUGSINPY_CONTAINER_HOME / PurePosixPath(relative.as_posix()))
        except ValueError:
            pass

        try:
            relative = resolved.relative_to(self._project_root.resolve())
        except ValueError as exc:
            raise ConfigurationError(
                f"Cannot pass path {path} into the BugsInPy container because it is "
                f"outside the project root {self._project_root}."
            ) from exc

        return str(PurePosixPath("/workspace") / PurePosixPath(relative.as_posix()))

    def _run_docker(
        self,
        args: list[str],
        check: bool,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                [self._docker, *args],
                check=check,
                text=True,
                capture_output=capture_output,
            )
        except FileNotFoundError as exc:
            raise ConfigurationError(
                "Docker CLI is required to run BugsInPy in its executor container."
            ) from exc


class BugsInPyToolchain:
    """
    Toolchain wrapper to interact with the BugsInPy installation and setup
    """

    def __init__(self, config: BugsInPyConfig) -> None:
        self._config = config
        self._executor = BugsInPyDockerExecutor(config)

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

        if not self.is_installed():
            self._clone_repository()

        self._normalize_command_scripts()
        self._executor.ensure_ready()

    def _clone_repository(self) -> None:
        if self.repo_dir.exists() and any(self.repo_dir.iterdir()):
            raise ConfigurationError(
                f"{self.repo_dir} exists but does not look like a BugsInPy clone. "
                "Move it away or remove it before running setup again."
            )

        git_executable = shutil.which("git")
        if git_executable is None:
            raise ConfigurationError("Git is required to bootstrap BugsInPy")

        self.repo_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [git_executable, "clone", BUGSINPY_REPOSITORY_URL, str(self.repo_dir)],
            check=True,
            text=True,
        )

    def _normalize_command_scripts(self) -> None:
        bin_dir = self.repo_dir / "framework" / "bin"
        if not bin_dir.exists():
            return

        for script in bin_dir.glob("bugsinpy-*"):
            if not script.is_file():
                continue

            content = script.read_bytes()
            normalized = content.replace(b"\r\n", b"\n")
            if normalized != content:
                script.write_bytes(normalized)

            script.chmod(script.stat().st_mode | 0o111)

    def ensure_installed(self) -> None:
        if not self.is_installed():
            raise BenchmarkError(
                "BugsInPy is not installed. Run `python -m apr_framework bugsinpy setup` first."
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
        return self._executor.run_bugsinpy(
            command_name,
            *args,
            cwd=cwd,
            check=check,
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
            check=False,
            capture_output=True,
        )

        project_dir = destination / canonical_bug.project
        raw_message = _completed_output(completed)

        if _completed_returncode(completed) != 0:
            raise BenchmarkError(
                f"BugsInPy checkout failed for project '{canonical_bug.project}' "
                f"(requested as '{bug.project}'). {raw_message}".strip()
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
        See: .tools\bugsinpy\framework\bin\bugsinpy-safe-compile
        Args:
            checkout (CheckoutResult): _description_
        """
        completed = self._toolchain.run_bugsinpy(
            "bugsinpy-safe-compile",
            cwd=checkout.worktree,
            check=False,
            capture_output=True,
        )
        if _completed_returncode(completed) != 0:
            raise BenchmarkError(
                f"BugsInPy compile failed for {checkout.worktree}. "
                f"{_completed_output(completed)}".strip()
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
            cwd=checkout.worktree,
            check=False,
            capture_output=True,
        )

        raw_output = _completed_output(completed)

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
