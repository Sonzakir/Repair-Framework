from pathlib import Path

import pytest

from apr_framework.benchmarks.bugsinpy import BugsInPyAdapter
from apr_framework.core.exceptions import BenchmarkError
from apr_framework.core.models import BugIdentifier


class DummyCompletedProcess:
    def __init__(self, stdout: str = "", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


class FakeToolchain:
    def __init__(self, repo_dir: Path) -> None:
        self.repo_dir = repo_dir
        self.commands: list[tuple[str, tuple[str, ...]]] = []

    def ensure_installed(self) -> None:
        return None

    def run_bugsinpy(self, command_name: str, *args: str, **_: object) -> DummyCompletedProcess:
        self.commands.append((command_name, args))
        return DummyCompletedProcess(stdout="checkout complete")


@pytest.fixture
def adapter(tmp_path: Path) -> BugsInPyAdapter:
    repo_dir = tmp_path / "repo"
    (repo_dir / "projects" / "youtube-dl" / "bugs" / "2").mkdir(parents=True)
    (repo_dir / "projects" / "black" / "bugs" / "1").mkdir(parents=True)
    return BugsInPyAdapter(FakeToolchain(repo_dir))


def test_list_bugs_resolves_dotted_project_alias(adapter: BugsInPyAdapter) -> None:
    bugs = adapter.list_bugs("youtube.dl")

    assert [bug.identifier.project for bug in bugs] == ["youtube-dl"]
    assert [bug.identifier.bug_id for bug in bugs] == [2]


def test_checkout_uses_canonical_project_name(adapter: BugsInPyAdapter, tmp_path: Path) -> None:
    destination = tmp_path / "workspace"
    toolchain = adapter.toolchain

    def fake_run_bugsinpy(command_name: str, *args: str, **_: object) -> DummyCompletedProcess:
        toolchain.commands.append((command_name, args))
        (destination / "youtube-dl").mkdir(parents=True)
        return DummyCompletedProcess(stdout="checkout complete")

    toolchain.run_bugsinpy = fake_run_bugsinpy  # type: ignore[method-assign]

    result = adapter.checkout(
        BugIdentifier(benchmark="bugsinpy", project="youtube.dl", bug_id=2),
        destination,
    )

    assert result.bug.project == "youtube-dl"
    assert result.worktree == destination / "youtube-dl"
    assert toolchain.commands == [
        (
            "bugsinpy-checkout",
            ("-p", "youtube-dl", "-i", "2", "-v", "0", "-w", str(destination)),
        )
    ]


def test_checkout_raises_when_worktree_is_missing(
    adapter: BugsInPyAdapter, tmp_path: Path
) -> None:
    destination = tmp_path / "workspace"

    with pytest.raises(BenchmarkError, match="Expected worktree"):
        adapter.checkout(
            BugIdentifier(benchmark="bugsinpy", project="youtube.dl", bug_id=2),
            destination,
        )
