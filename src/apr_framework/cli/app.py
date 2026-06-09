from pathlib import Path

from apr_framework.benchmarks.registry import (
    create_bugsinpy_adapter,
    list_benchmark_names,
)
from apr_framework.cli.parser import build_parser
from apr_framework.core.exceptions import APRFrameworkError, BenchmarkError
from apr_framework.core.models import BugIdentifier, CheckoutResult
from apr_framework.evaluation import DEFAULT_DUMMY_BUGS, DummyEvaluationRunner
from apr_framework.localization import FauxPyConfig, FauxPyLocalizer, FauxPyToolchain
from apr_framework.localization.fauxpy import load_pytest_targets
from apr_framework.repair import DummyRepairAlgorithm


def main() -> int:
    try:
        return _run()
    except APRFrameworkError as error:
        print(f"Error: {error}")
        return 1


def _run() -> int:
    parser = build_parser()
    args = parser.parse_args()
    project_root = Path.cwd()

    # BugsInPy
    if args.command == "list-benchmarks":
        for name in list_benchmark_names():
            print(name)
        return 0

    # FauxPy 
    if args.command == "localize":
        # Currently we are running FauxPy only inside the BugsInPy projects
        adapter = create_bugsinpy_adapter(project_root)
        adapter.toolchain.ensure_installed()

        projects_dir = adapter.toolchain.repo_dir / "projects"
        project_dir = projects_dir / args.project
        if not project_dir.is_dir():
            raise BenchmarkError(f"No such BugsInPy project: {args.project}")

        bug_dir = project_dir / "bugs" / str(args.bug)
        if not bug_dir.is_dir():
            raise BenchmarkError(
                f"No such bug {args.bug} for BugsInPy project {args.project}"
            )

        destination = (
            project_root
            / ".workspace"
            / "bugsinpy"
            / f"{args.project}_{args.bug}"
        )
        worktree = destination / args.project
        if not worktree.exists():
            raise BenchmarkError(
                f"No checkout found at {worktree}. "
                f"Run `python -m apr_framework bugsinpy checkout {args.project} {args.bug}` first."
            )

        src = args.src or _infer_fauxpy_src(worktree, args.project)
        bug_test_targets = load_pytest_targets(bug_dir / "run_test.sh")
        # Strip pytest flags (e.g. -q, -s) so only node IDs go into --failing-list.
        bug_test_ids = [t for t in bug_test_targets if not t.startswith("-")]
        test_targets = _parse_fauxpy_test_targets_command(args.test_target) or bug_test_targets
        failing_tests = _parse_fauxpy_failing_tests_command(args.failing_tests) or bug_test_ids
        checkout = CheckoutResult(
            bug=BugIdentifier(
                benchmark="bugsinpy",
                project=args.project,
                bug_id=args.bug,
            ),
            worktree=worktree,
            success=True,
            prepared=True,
        )

        family = "mbfl" if args.mbfl else args.family
        metric = args.metric or ("metallaxis" if family == "mbfl" else "ochiai")

        # create FauxPy-Config Object 
        config = FauxPyConfig(
            src=src,
            test_targets=test_targets,
            family=family,
            granularity=args.granularity, 
            failing_tests=failing_tests,
            top_n=args.top_n,
            mutation_strategy = args.mutation_strategy, 
            mutation_budget = args.mutation_budget , 
            mutation_seed=args.seed,
            metric = metric
        )
        
        # Localize the Faulty Locations 
        localizer = FauxPyLocalizer(config, FauxPyToolchain(adapter.toolchain))
        result = localizer.localize(checkout.bug, checkout)

        print(f"Project: {result.bug.project}")
        print(f"Bug ID: {result.bug.bug_id}")
        print(f"Backend: {result.backend}")
        if result.metadata.get("score_formula"):
            print(f"Score formula: {result.metadata['score_formula']}")
        print("Ranked locations:")
        for location in result.ranked_locations:
            score = "" if location.score is None else f"{location.score:.4f}"
            print(f"{location.rank}. {location.file_path}:{location.line} {score}".rstrip())

        if args.show_raw_output and result.metadata.get("raw_output"):
            print("\nRaw FauxPy output:")
            print(result.metadata["raw_output"])

        return 0
    

    # BugsInPy
    if args.command == "bugsinpy":
        adapter = create_bugsinpy_adapter(project_root)

        if args.bugsinpy_command == "setup":
            adapter.toolchain.bootstrap()
            print("BugsInPy setup successfully")
            return 0

        if args.bugsinpy_command == "list-projects":
            for project in adapter.list_projects():
                print(project)
            return 0

        if args.bugsinpy_command == "list-bugs":
            for bug_info in adapter.list_bugs(args.project):
                print(f"{bug_info.identifier.project} {bug_info.identifier.bug_id}")
            return 0

        if args.bugsinpy_command == "checkout":
            bug = BugIdentifier(
                benchmark="bugsinpy", project=args.project, bug_id=args.bug_id
            )
            destination = (
                project_root
                / ".workspace"
                / "bugsinpy"
                / f"{args.project}_{args.bug_id}"
            )

            result = adapter.checkout(bug, destination)
            print(f"Project: {result.bug.project}")
            print(f"Bug ID: {result.bug.bug_id}")
            print(f"Checkout success: {result.success}")
            print(f"Worktree: {result.worktree}")
            if result.message:
                print(f"Message: {result.message}")

            return 0

        if args.bugsinpy_command == "compile":
            canonical_project = adapter.resolve_project(args.project)
            bug = BugIdentifier(
                benchmark="bugsinpy", project=canonical_project, bug_id=args.bug_id
            )
            destination = (
                project_root
                / ".workspace"
                / "bugsinpy"
                / f"{args.project}_{args.bug_id}"
            )
            worktree = destination / canonical_project
            if not worktree.exists():
                raise BenchmarkError(
                    f"No checkout found at {worktree}. "
                    f"Run `python -m apr_framework bugsinpy checkout {args.project} {args.bug_id}` first."
                )

            checkout = CheckoutResult(bug=bug, worktree=worktree, success=True)
            adapter.prepare_environment(checkout)
            print(f"Project: {checkout.bug.project}")
            print(f"Bug ID: {checkout.bug.bug_id}")
            print(f"Prepared: {checkout.prepared}")
            print(f"Worktree: {checkout.worktree}")
            return 0

        if args.bugsinpy_command == "test":
            bug = BugIdentifier(
                benchmark="bugsinpy", project=args.project, bug_id=args.bug_id
            )
            destination = (
                project_root
                / ".workspace"
                / "bugsinpy"
                / f"{args.project}_{args.bug_id}"
            )
            checkout = adapter.checkout(bug, destination)
            adapter.prepare_environment(checkout)
            test_result = adapter.run_tests(checkout)

            print(f"Project: {checkout.bug.project}")
            print(f"Bug ID: {checkout.bug.bug_id}")
            print(f"Checkout success: {checkout.success}")
            print(f"Prepared: {checkout.prepared}")
            print(f"Tests run: {test_result.total_count}")
            print(f"Passing: {test_result.passed_count}")
            print(f"Failing: {test_result.failed_count}")

            if test_result.raw_output:
                print("\nRaw output:")
                print(test_result.raw_output)

            return 0

        if args.bugsinpy_command == "evaluate-dummy":
            repair = DummyRepairAlgorithm(project_root=project_root, seed=args.seed)
            runner = DummyEvaluationRunner(
                project_root=project_root,
                runs_dir=args.runs_dir,
                seed=args.seed,
            )

            results = runner.run(
                bugs=list(DEFAULT_DUMMY_BUGS),
                benchmark=adapter,
                repair=repair,
            )

            if runner.last_run_dir is not None:
                print(f"Run directory: {runner.last_run_dir}")

            for result in results:
                print(
                    f"{result.bug.project} {result.bug.bug_id}: {result.status}"
                )

            return 0

    return 1


def _infer_fauxpy_src(worktree: Path, project: str) -> str:
    package_name = project.replace("-", "_")

    # Enumerate real names to handle case-sensitive filesystems inside Docker.
    try:
        entries = {e.name: e for e in worktree.iterdir()}
    except OSError:
        return "."

    for candidate in [package_name, project, package_name.lower(), project.lower()]:
        entry = entries.get(candidate)
        if entry is not None and entry.is_dir():
            return candidate

    for candidate in [
        f"{package_name}.py",
        f"{project}.py",
        f"{package_name.lower()}.py",
    ]:
        entry = entries.get(candidate)
        if entry is not None and entry.is_file():
            return candidate

    return "."


def _parse_fauxpy_failing_tests_command(value:str | None) -> list[str]:
    if value is None:
        return []
    
    stripped = value.strip()
    if not stripped:
        return []
    if stripped.startswith("[") and stripped.endswith("]"):
        stripped = stripped[1:-1]

    return [
        item.strip()
        for item in stripped.split(",")
        if item.strip()
    ]


def _parse_fauxpy_test_targets_command(values: list[str] | None) -> list[str]:
    if not values:
        return []

    targets: list[str] = []
    for value in values:
        targets.extend(item.strip() for item in value.split(",") if item.strip())
    return targets
