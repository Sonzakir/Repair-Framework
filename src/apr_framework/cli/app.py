from datetime import datetime, timezone
from pathlib import Path

from apr_framework.benchmarks.registry import (
    create_bugsinpy_adapter,
    list_benchmark_names,
)
from apr_framework.cli.parser import build_parser
from apr_framework.core.exceptions import (
    APRFrameworkError,
    BenchmarkError,
    ConfigurationError,
)
from apr_framework.core.models import BugIdentifier, CheckoutResult, RepairAttemptResult
from apr_framework.evaluation import DEFAULT_DUMMY_BUGS, DummyEvaluationRunner
from apr_framework.evaluation.run_writer import RunWriter, serialize_localization_result
from apr_framework.evaluation.localization_runner import LocalizationComparisonRunner
from apr_framework.localization import (
    FauxPyConfig,
    FauxPyLocalizer,
    FauxPyToolchain,
    HybridFaultLocalizer,
)
from apr_framework.localization.fauxpy import load_pytest_targets
from apr_framework.core.models import EvaluationResult
from apr_framework.repair import DummyRepairAlgorithm, TemplateRepairAlgorithm, TemplateRepairConfig
from apr_framework.reporting import ArchiveReportGenerator


def main() -> int:
    """
    Execute the APR framework command-line application.

    Returns:
        Process exit code: `0` for success and `1` for handled framework errors.
    """
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
        family = _resolve_localize_family(args)
        _validate_localize_args(args, family)

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

        fauxpy_toolchain = FauxPyToolchain(adapter.toolchain)

        runs_dir = Path(args.runs_dir)
        if not runs_dir.is_absolute():
            runs_dir = project_root / runs_dir
        writer = RunWriter.create(runs_dir)
        started_at = datetime.now(timezone.utc)

        writer.log(f"Started fauxpy localization for {args.project}#{args.bug}")
        effective_metric = args.metric or ("metallaxis" if family == "mbfl" else "ochiai")
        config_data: dict = {
            "runner": "fauxpy-localizer",
            "backend": args.backend,
            "project": args.project,
            "bug_id": args.bug,
            "family": family,
            "granularity": args.granularity,
            "top_n": args.top_n,
            "mutation_strategy": args.mutation_strategy,
            "mutation_budget": args.mutation_budget,
            "mutation_seed": args.seed,
            "started_at": started_at.isoformat(),
        }
        if family == "hybrid":
            config_data["sbfl_metric"] = args.sbfl_metric
            config_data["mbfl_metric"] = args.mbfl_metric
            config_data["sbfl_weight"] = args.sbfl_weight
            config_data["mbfl_weight"] = args.mbfl_weight
        else:
            config_data["metric"] = effective_metric
        writer.write_json("config.json", config_data)

        if family == "hybrid":
            sbfl_config = FauxPyConfig(
                src=src,
                test_targets=test_targets,
                family="sbfl",
                granularity=args.granularity,
                failing_tests=failing_tests,
                top_n=None,
                metric=args.sbfl_metric,
            )
            mbfl_config = FauxPyConfig(
                src=src,
                test_targets=test_targets,
                family="mbfl",
                granularity=args.granularity,
                failing_tests=failing_tests,
                top_n=None,
                mutation_strategy=args.mutation_strategy,
                mutation_budget=args.mutation_budget,
                mutation_seed=args.seed,
                metric=args.mbfl_metric,
            )
            localizer = HybridFaultLocalizer(
                FauxPyLocalizer(sbfl_config, fauxpy_toolchain),
                FauxPyLocalizer(mbfl_config, fauxpy_toolchain),
                sbfl_weight=args.sbfl_weight,
                mbfl_weight=args.mbfl_weight,
                top_n=args.top_n,
            )
        else:
            metric = args.metric or ("metallaxis" if family == "mbfl" else "ochiai")
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
            localizer = FauxPyLocalizer(config, fauxpy_toolchain)

        writer.log("Running localization")
        run_status = "completed"
        result = None
        try:
            result = localizer.localize(checkout.bug, checkout)
            writer.log(f"Localization completed: {len(result.ranked_locations)} ranked locations")
        except Exception as exc:
            run_status = "error"
            writer.log(f"ERROR: {exc}")
            writer.write_json(
                "results.json",
                {
                    "run_id": writer.run_dir.name,
                    "status": run_status,
                    "started_at": started_at.isoformat(),
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "error": f"{type(exc).__name__}: {exc}",
                },
            )
            writer.log(f"Finished run with status {run_status}")
            print(f"Run directory: {writer.run_dir}")
            raise

        finished_at = datetime.now(timezone.utc)
        writer.write_json(
            "results.json",
            {
                "run_id": writer.run_dir.name,
                "status": run_status,
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                **serialize_localization_result(result),
            },
        )
        writer.log(f"Finished run with status {run_status}")

        archive_path = ArchiveReportGenerator().write_summary(
            [EvaluationResult(bug=result.bug, status=run_status, started_at=started_at, finished_at=finished_at)],
            writer.run_dir,
        )
        print(f"Run directory: {writer.run_dir}")
        print(f"Report archive: {archive_path}")
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
        elif args.show_raw_output and result.backend == "hybrid-fauxpy":
            sbfl_raw_output = result.metadata.get("sbfl_metadata", {}).get("raw_output")
            mbfl_raw_output = result.metadata.get("mbfl_metadata", {}).get("raw_output")
            if sbfl_raw_output:
                print("\nRaw FauxPy SBFL output:")
                print(sbfl_raw_output)
            if mbfl_raw_output:
                print("\nRaw FauxPy MBFL output:")
                print(mbfl_raw_output)

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
                report = ArchiveReportGenerator()
                archive_path = report.write_summary(results, runner.last_run_dir)
                print(f"Report archive: {archive_path}")

            for result in results:
                print(
                    f"{result.bug.project} {result.bug.bug_id}: {result.status}"
                )

            return 0

        if args.bugsinpy_command == "evaluate-localization":
            return _run_evaluate_localization(args, project_root, adapter)

    if args.command == "repair":
        adapter = create_bugsinpy_adapter(project_root)
        return handle_repair(args, adapter, project_root)

    return 1


def handle_repair(args, adapter, project_root: Path) -> int:
    """Orchestrate a template-based repair run from CLI arguments.

    Steps:
    1. Verify the project is checked out and compiled.
    2. Run localization (or load a cached result if --skip-localize).
    3. Build TemplateRepairConfig and TemplateRepairAlgorithm.
    4. Call algorithm.repair() with budget and operators.
    5. Write repair_results.json to the run directory.
    6. Print a human-readable summary.
    """
    import json

    from apr_framework.localization import FauxPyConfig, FauxPyLocalizer, FauxPyToolchain

    project_root = Path(project_root)
    project = args.project
    bug_id = args.bug

    # ── Resolve worktree ────────────────────────────────────────────────
    adapter.toolchain.ensure_installed()
    canonical_project = adapter.resolve_project(project)
    bug = BugIdentifier(benchmark="bugsinpy", project=canonical_project, bug_id=bug_id)

    destination = project_root / ".workspace" / "bugsinpy" / f"{canonical_project}_{bug_id}"
    worktree = destination / canonical_project
    if not worktree.exists():
        raise BenchmarkError(
            f"No checkout found at {worktree}. "
            f"Run `python -m apr_framework bugsinpy checkout {project} {bug_id}` first."
        )

    checkout = CheckoutResult(
        bug=bug,
        worktree=worktree,
        success=True,
        prepared=True,
    )

    # ── Set up run writer ────────────────────────────────────────────────
    from apr_framework.evaluation.run_writer import RunWriter
    runs_dir = Path(args.runs_dir)
    if not runs_dir.is_absolute():
        runs_dir = project_root / runs_dir
    writer = RunWriter.create(runs_dir)

    started_at = datetime.now(timezone.utc)
    writer.log(f"Started template repair for {canonical_project}#{bug_id}")

    enabled_operators = [op.strip() for op in args.operators.split(",") if op.strip()]

    config = TemplateRepairConfig(
        budget=args.budget,
        top_n_locations=args.top_n,
        enabled_operators=enabled_operators,
        timeout_per_test=args.timeout,
        fail_fast=not args.no_fail_fast,
        stop_on_first=args.stop_on_first,
    )

    config_data = {
        "runner": "template-repair",
        "project": canonical_project,
        "bug_id": bug_id,
        "technique": args.technique,
        "budget": config.budget,
        "top_n_locations": config.top_n_locations,
        "enabled_operators": config.enabled_operators,
        "timeout_per_test": config.timeout_per_test,
        "fail_fast": config.fail_fast,
        "stop_on_first": config.stop_on_first,
        "localization_metric": args.localization_metric,
        "granularity": args.granularity,
        "skip_localize": args.skip_localize,
        "started_at": started_at.isoformat(),
    }
    writer.write_json("config.json", config_data)

    # ── Localization ─────────────────────────────────────────────────────
    localization_result = None

    if args.skip_localize:
        # Look for a cached results.json in the most recent run that has ranked_locations.
        results_files = sorted(runs_dir.glob("run_*/results.json"), reverse=True)
        for rf in results_files:
            try:
                cached = json.loads(rf.read_text(encoding="utf-8"))
                if "ranked_locations" in cached:
                    from apr_framework.core.models import LocalizationResult, RankedLocation
                    ranked = [
                        RankedLocation(**{
                            k: v for k, v in loc.items()
                            if k in RankedLocation.__dataclass_fields__
                        })
                        for loc in cached["ranked_locations"]
                    ]
                    localization_result = LocalizationResult(
                        bug=bug,
                        backend=cached.get("backend", "cached"),
                        ranked_locations=ranked,
                        metadata=cached.get("metadata", {}),
                    )
                    writer.log(f"Loaded cached localization from {rf} ({len(ranked)} locations)")
                    break
            except Exception as exc:
                writer.log(f"Could not load cached result from {rf}: {exc}")

        if localization_result is None:
            writer.log("No cached localization found — running fresh localization.")

    if localization_result is None:
        projects_dir = adapter.toolchain.repo_dir / "projects"
        bug_dir = projects_dir / canonical_project / "bugs" / str(bug_id)
        if not bug_dir.is_dir():
            raise BenchmarkError(
                f"No such bug {bug_id} for BugsInPy project {canonical_project}"
            )

        src = _infer_fauxpy_src(worktree, canonical_project)
        bug_test_targets = load_pytest_targets(bug_dir / "run_test.sh")
        bug_test_ids = [t for t in bug_test_targets if not t.startswith("-")]

        fauxpy_toolchain = FauxPyToolchain(adapter.toolchain)
        fl_config = FauxPyConfig(
            src=src,
            test_targets=bug_test_targets,
            family="sbfl",
            granularity=args.granularity,
            failing_tests=bug_test_ids,
            metric=args.localization_metric,
        )
        localizer = FauxPyLocalizer(fl_config, fauxpy_toolchain)

        writer.log(f"Running SBFL localization (metric={args.localization_metric})")
        try:
            localization_result = localizer.localize(bug, checkout)
            writer.log(
                f"Localization done: {len(localization_result.ranked_locations)} locations ranked"
            )
        except Exception as exc:
            writer.log(f"Localization failed: {exc}")
            raise

    # ── Repair ───────────────────────────────────────────────────────────
    algorithm = TemplateRepairAlgorithm(
        localization_result=localization_result,
        adapter=adapter,
        config=config,
    )

    writer.log(
        f"Repair started: budget={config.budget}, top_n={config.top_n_locations}, "
        f"operators={config.enabled_operators}"
    )

    summary_result, all_results = algorithm.repair(bug, checkout)

    finished_at = datetime.now(timezone.utc)
    elapsed_s = (finished_at - started_at).total_seconds()

    writer.log(
        f"Repair finished: status={summary_result.status.value}, "
        f"candidates_validated={len(all_results)}, elapsed={elapsed_s:.1f}s"
    )

    # ── Persist results ──────────────────────────────────────────────────
    plausible = [r for r in all_results if r.status.value == "plausible"]

    def _serialise_result(r: "RepairAttemptResult") -> dict:
        return {
            "patch_id": r.patch.patch_id if r.patch else None,
            "status": r.status.value,
            "summary": r.patch.summary if r.patch else None,
            "validation_summary": r.validation_summary,
            "diff_text": r.patch.diff_text if r.patch else None,
            "metadata": {
                k: v
                for k, v in (r.patch.metadata if r.patch else {}).items()
                if k != "patched_source"  # omit large source blobs
            },
        }

    repair_results_payload = {
        "run_id": writer.run_dir.name,
        "project": canonical_project,
        "bug_id": bug_id,
        "status": summary_result.status.value,
        "validation_summary": summary_result.validation_summary,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "elapsed_seconds": elapsed_s,
        "config": config_data,
        "candidates_validated": len(all_results),
        "plausible_count": len(plausible),
        "plausible_patches": [_serialise_result(r) for r in plausible],
        "all_results": [_serialise_result(r) for r in all_results],
    }
    writer.write_json("repair_results.json", repair_results_payload)

    # ── Print summary ────────────────────────────────────────────────────
    print(f"\nRun directory: {writer.run_dir}")
    print(f"Project:       {canonical_project}")
    print(f"Bug ID:        {bug_id}")
    print(f"Status:        {summary_result.status.value}")
    print(f"Elapsed:       {elapsed_s:.1f}s")
    print(f"Validated:     {len(all_results)} candidate(s)")
    print(f"Plausible:     {len(plausible)} patch(es)")

    if plausible:
        print("\nPlausible patches:")
        for r in plausible:
            if r.patch:
                print(f"  [{r.patch.patch_id}] {r.patch.summary}")
                print(f"    {r.validation_summary}")
    elif all_results:
        print(f"\n{summary_result.validation_summary}")
    else:
        print(f"\n{summary_result.validation_summary}")

    return 0


def _run_evaluate_localization(args, project_root: Path, adapter) -> int:
    """Run the localization comparison evaluation and write results."""
    from apr_framework.core.models import CheckoutResult
    from apr_framework.localization import FauxPyConfig, FauxPyLocalizer, FauxPyToolchain, HybridFaultLocalizer

    bugs = _parse_bug_list(args.bugs or "black:1,black:3,black:7")
    top_ks = tuple(int(k.strip()) for k in args.top_ks.split(",") if k.strip())
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = project_root / output_dir
    granularity = args.granularity

    fauxpy_toolchain = FauxPyToolchain(adapter.toolchain)
    projects_dir = adapter.toolchain.repo_dir / "projects"

    # Validate bugs and build checkouts
    checkouts: dict = {}
    for bug in bugs:
        worktree = (
            project_root
            / ".workspace"
            / "bugsinpy"
            / f"{bug.project}_{bug.bug_id}"
            / bug.project
        )
        if not worktree.exists():
            raise BenchmarkError(
                f"No checkout found for {bug.project} #{bug.bug_id} at {worktree}. "
                f"Run `python -m apr_framework bugsinpy checkout {bug.project} {bug.bug_id}` "
                "and then `compile` before evaluating."
            )
        checkouts[bug] = CheckoutResult(
            bug=bug,
            worktree=worktree,
            success=True,
            prepared=True,
        )

    def patch_dir(bug: BugIdentifier) -> Path:
        return projects_dir / bug.project / "bugs" / str(bug.bug_id)

    def _src(bug: BugIdentifier) -> str:
        worktree = checkouts[bug].worktree
        return _infer_fauxpy_src(worktree, bug.project)

    def _make_sbfl(bug: BugIdentifier, metric: str) -> FauxPyLocalizer:
        bug_dir = patch_dir(bug)
        test_targets = load_pytest_targets(bug_dir / "run_test.sh")
        test_ids = [t for t in test_targets if not t.startswith("-")]
        return FauxPyLocalizer(
            FauxPyConfig(
                src=_src(bug),
                test_targets=test_targets,
                family="sbfl",
                granularity=granularity,
                failing_tests=test_ids,
                metric=metric,
            ),
            fauxpy_toolchain,
        )

    def _make_mbfl(bug: BugIdentifier) -> FauxPyLocalizer:
        bug_dir = patch_dir(bug)
        test_targets = load_pytest_targets(bug_dir / "run_test.sh")
        test_ids = [t for t in test_targets if not t.startswith("-")]
        return FauxPyLocalizer(
            FauxPyConfig(
                src=_src(bug),
                test_targets=test_targets,
                family="mbfl",
                granularity=granularity,
                failing_tests=test_ids,
                metric="metallaxis",
                mutation_strategy="random",
                mutation_budget=args.budget,
                mutation_seed=args.seed,
            ),
            fauxpy_toolchain,
        )

    def _make_hybrid(bug: BugIdentifier) -> HybridFaultLocalizer:
        bug_dir = patch_dir(bug)
        test_targets = load_pytest_targets(bug_dir / "run_test.sh")
        test_ids = [t for t in test_targets if not t.startswith("-")]
        sbfl_cfg = FauxPyConfig(
            src=_src(bug),
            test_targets=test_targets,
            family="sbfl",
            granularity=granularity,
            failing_tests=test_ids,
            metric="ochiai",
        )
        mbfl_cfg = FauxPyConfig(
            src=_src(bug),
            test_targets=test_targets,
            family="mbfl",
            granularity=granularity,
            failing_tests=test_ids,
            metric="metallaxis",
            mutation_strategy="random",
            mutation_budget=args.budget,
            mutation_seed=args.seed,
        )
        return HybridFaultLocalizer(
            FauxPyLocalizer(sbfl_cfg, fauxpy_toolchain),
            FauxPyLocalizer(mbfl_cfg, fauxpy_toolchain),
        )

    techniques = _build_techniques(_make_sbfl, _make_mbfl, _make_hybrid)

    runner = LocalizationComparisonRunner(top_ks=top_ks)

    print(f"Evaluating {len(bugs)} bug(s) with {len(techniques)} technique(s)...")
    eval_results = runner.run(
        bugs=bugs,
        techniques=techniques,
        checkouts=checkouts,
        patch_dir_fn=patch_dir,
    )

    readme_path = runner.write_results(eval_results, output_dir)
    print(f"\nResults written to: {output_dir}")
    print(f"README: {readme_path}")

    # Print a compact summary table to stdout
    _print_summary(eval_results, top_ks)
    return 0


def _build_techniques(make_sbfl, make_mbfl, make_hybrid):
    """Return (name, per-bug-localizer) pairs for all techniques."""

    class _BugLocalizer:
        def __init__(self, factory):
            self._factory = factory

        def localize(self, bug, checkout, test_result=None):
            return self._factory(bug).localize(bug, checkout, test_result)

    return [
        ("SBFL-Ochiai (baseline)", _BugLocalizer(lambda bug: make_sbfl(bug, "ochiai"))),
        ("SBFL-Tarantula (baseline)", _BugLocalizer(lambda bug: make_sbfl(bug, "tarantula"))),
        ("SBFL-DStar (baseline)", _BugLocalizer(lambda bug: make_sbfl(bug, "dstar"))),
        ("SBFL-Jaccard (extension)", _BugLocalizer(lambda bug: make_sbfl(bug, "jaccard"))),
        ("SBFL-SBI (extension)", _BugLocalizer(lambda bug: make_sbfl(bug, "sbi"))),
        ("MBFL-Metallaxis (baseline)", _BugLocalizer(make_mbfl)),
        ("Hybrid SBFL+MBFL (extension)", _BugLocalizer(make_hybrid)),
    ]


def _parse_bug_list(spec: str) -> list[BugIdentifier]:
    bugs: list[BugIdentifier] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            raise ConfigurationError(
                f"Invalid bug specification {part!r} — expected project:bug_id"
            )
        project, bug_id_str = part.rsplit(":", 1)
        try:
            bug_id = int(bug_id_str)
        except ValueError:
            raise ConfigurationError(
                f"Invalid bug ID {bug_id_str!r} in {part!r} — must be an integer"
            )
        bugs.append(BugIdentifier(benchmark="bugsinpy", project=project, bug_id=bug_id))
    if not bugs:
        raise ConfigurationError("No bugs specified for evaluate-localization.")
    return bugs


def _print_summary(
    results,
    top_ks: tuple[int, ...],
) -> None:
    print("\n=== Summary ===")
    header = f"{'Bug':<20} {'Technique':<30} {'Rank':>6}  " + "  ".join(
        f"Top-{k}" for k in sorted(top_ks)
    )
    print(header)
    print("-" * len(header))
    for r in results:
        bug_label = f"{r.bug.project}#{r.bug.bug_id}"
        rank_str = str(r.faulty_rank) if r.faulty_rank is not None else "—"
        top_k_str = "  ".join(
            ("✓" if r.top_k_hits.get(k) else "✗") for k in sorted(top_ks)
        )
        note = f"  ERROR: {r.error}" if r.error else ""
        print(f"{bug_label:<20} {r.technique:<30} {rank_str:>6}  {top_k_str}{note}")


def _resolve_localize_family(args) -> str:
    return "mbfl" if args.mbfl else args.family


def _validate_localize_args(args, family: str) -> None:
    if family == "hybrid" and args.metric is not None:
        raise ConfigurationError(
            "Use --sbfl-metric and --mbfl-metric for hybrid localization; "
            "--metric is only for single-family SBFL or MBFL runs."
        )
    if family == "hybrid":
        if args.sbfl_weight < 0 or args.mbfl_weight < 0:
            raise ConfigurationError(
                "Hybrid localization weights must be non-negative."
            )
        if args.sbfl_weight == 0 and args.mbfl_weight == 0:
            raise ConfigurationError("Hybrid localization weights cannot both be zero.")


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


