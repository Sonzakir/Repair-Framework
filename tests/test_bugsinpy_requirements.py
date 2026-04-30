import hashlib
from pathlib import Path

from apr_framework.benchmarks.bugsinpy import BugsInPyAdapter


class FakeToolchain:
    def __init__(self, repo_dir: Path) -> None:
        self.repo_dir = repo_dir

    def ensure_installed(self) -> None:
        return None


def _adapter(tmp_path: Path) -> BugsInPyAdapter:
    repo_dir = tmp_path / "repo"
    (repo_dir / "projects" / "black" / "bugs" / "1").mkdir(parents=True)
    return BugsInPyAdapter(FakeToolchain(repo_dir))


def test_conda_env_name_decodes_utf16_requirements(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path)
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    requirements = worktree / "bugsinpy_requirements.txt"
    requirements.write_text(
        "# comment\r\npytest==8.0.0\r\n\r\nclick==8.1.7\r\n",
        encoding="utf-16",
    )

    env_name = adapter._conda_env_name(worktree, "3.10")

    expected_normalized = "pytest==8.0.0\nclick==8.1.7\n"
    expected = hashlib.md5(f"3.10\n{expected_normalized}".encode()).hexdigest()

    assert env_name == expected
    assert requirements.read_text(encoding="utf-8") == expected_normalized
