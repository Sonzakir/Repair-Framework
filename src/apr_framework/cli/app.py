import getpass
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

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
from apr_framework.core.models import BugIdentifier, CheckoutResult
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
    load_dotenv(project_root / ".env")

    # List Integrated Benchmarks in the Framework
    if args.command == "list-benchmarks":
        for name in list_benchmark_names():
            print(name)
        return 0

    # Interactively store an LLM API key in the local .env file
    if args.command == "configure":
        api_key = getpass.getpass(f"Enter value for {args.llm_api_key_env}: ")
        _write_env_var(project_root / ".env", args.llm_api_key_env, api_key)
        print(f"Saved {args.llm_api_key_env} to {project_root / '.env'}")
        return 0

    # -- FauxPy --
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
    

    # --  BugsInPy --
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

        if args.bugsinpy_command == "evaluate-repair":
            return _run_evaluate_repair(args, project_root, adapter)


    # -- Repair -- 

    if args.command == "repair":
        # Currently repair components are working on the BugsInPy Projects 
        adapter = create_bugsinpy_adapter(project_root)
        return handle_repair(args, adapter, project_root)

    return 1


def handle_repair(args, adapter, project_root: Path) -> int:
    """Orchestrate a template-based repair run from CLI arguments.

    Steps:
    1. Verify the project is checked out and compiled.
    2. Run localization (or load a cached result if --skip-localize).
    3. Build TemplateRepairConfig and TemplateRepairAlgorithm.
    4. Delegate the generate-validate-correctness pipeline to
       RepairEvaluationRunner (T-2), which writes repair_results.json (incl.
       the validation metrics) and the plausible-patch artifacts.
    5. Print a human-readable summary.
    """
    import json

    from apr_framework.localization import FauxPyConfig, FauxPyLocalizer, FauxPyToolchain

    project_root = Path(project_root)
    project = args.project
    bug_id = args.bug

    # -- Resolve worktree 
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

    # -- Set up run writer --
    from apr_framework.evaluation.run_writer import RunWriter
    runs_dir = Path(args.runs_dir)
    if not runs_dir.is_absolute():
        runs_dir = project_root / runs_dir
    writer = RunWriter.create(runs_dir)

    started_at = datetime.now(timezone.utc)
    writer.log(f"Started template repair for {canonical_project}#{bug_id}")

    # Common config fields shared by all repair techniques
    config_data = {
        "project": canonical_project,
        "bug_id": bug_id,
        "technique": args.technique,
        "budget": args.budget,
        "top_n_locations": args.top_n,
        "stop_on_first": args.stop_on_first,
        "regression_check": args.regression_check,
        "fl_mode": args.fl_mode,
        "fl_backend": "oracle" if args.fl_mode == "perfect" else args.fl_family,
        "fl_family": args.fl_family,
        "localization_metric": args.localization_metric,
        "mbfl_metric": args.mbfl_metric,
        "granularity": args.granularity,
        "skip_localize": args.skip_localize,
        "started_at": started_at.isoformat(),
    }

    if args.technique == "template":
        enabled_operators = [op.strip() for op in args.operators.split(",") if op.strip()]
        template_repair_config = TemplateRepairConfig(
            budget=args.budget,
            top_n_locations=args.top_n,
            enabled_operators=enabled_operators,
            timeout_per_test=args.timeout,
            stop_on_first=args.stop_on_first,
            regression_check=args.regression_check,
        )
        config_data.update({
            "runner": "template-repair",
            "enabled_operators": template_repair_config.enabled_operators,
            "timeout_per_test": template_repair_config.timeout_per_test,
        })
    elif args.technique == "llm":
        config_data.update({
            "runner": "llm-repair",
            "model": args.model,
            "temperature": args.temperature,
            "max_candidates": args.max_candidates,
            "llm_provider": args.llm_provider,
            "timeout_seconds": args.timeout,
        })
    else:
        raise ConfigurationError(f"Unknown repair technique: {args.technique!r}")

    writer.write_json("config.json", config_data)

    # -- Localization --
    localization_result = None

    # Perfect FL (T-3): bypass any localizer and use the BugsInPy developer-fix
    # lines as the oracle fault location. Ignores --fl-family / --skip-localize.
    if args.fl_mode == "perfect":
        from apr_framework.localization import PerfectFaultLocalizer

        writer.log("Running perfect (oracle) FL from the BugsInPy developer fix")
        localizer = PerfectFaultLocalizer(adapter)
        localization_result = localizer.localize(bug, checkout)
        writer.log(
            f"Perfect FL done: {len(localization_result.ranked_locations)} "
            "oracle location(s) from bug_patch.txt"
        )

    if localization_result is None and args.skip_localize:
        # Look for a cached results.json in the most recent run for this exact bug
        # that has ranked_locations.  Filter on project and bug_id so a cache entry
        # from a different bug is never mistakenly loaded.
        results_files = sorted(runs_dir.glob("run_*/results.json"), reverse=True)
        for rf in results_files:
            try:
                cached = json.loads(rf.read_text(encoding="utf-8"))
                cached_bug = cached.get("bug", {})
                if (
                    "ranked_locations" in cached
                    and cached_bug.get("project") == canonical_project
                    and cached_bug.get("bug_id") == bug_id
                ):
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

        def _make_sbfl() -> FauxPyLocalizer:
            return FauxPyLocalizer(
                FauxPyConfig(
                    src=src,
                    test_targets=bug_test_targets,
                    family="sbfl",
                    granularity=args.granularity,
                    failing_tests=bug_test_ids,
                    metric=args.localization_metric,
                ),
                fauxpy_toolchain,
            )

        def _make_mbfl() -> FauxPyLocalizer:
            return FauxPyLocalizer(
                FauxPyConfig(
                    src=src,
                    test_targets=bug_test_targets,
                    family="mbfl",
                    granularity=args.granularity,
                    failing_tests=bug_test_ids,
                    metric=args.mbfl_metric,
                    mutation_strategy="random",
                    mutation_budget=args.mutation_budget,
                    mutation_seed=args.seed,
                ),
                fauxpy_toolchain,
            )

        if args.fl_family == "sbfl":
            localizer = _make_sbfl()
            writer.log(f"Running SBFL localization (metric={args.localization_metric})")
        elif args.fl_family == "mbfl":
            localizer = _make_mbfl()
            writer.log(f"Running MBFL localization (metric={args.mbfl_metric})")
        else:  # hybrid
            from apr_framework.localization import HybridFaultLocalizer

            localizer = HybridFaultLocalizer(
                _make_sbfl(),
                _make_mbfl(),
                sbfl_weight=args.sbfl_weight,
                mbfl_weight=args.mbfl_weight,
            )
            writer.log(
                f"Running hybrid localization (sbfl={args.localization_metric}@"
                f"{args.sbfl_weight}, mbfl={args.mbfl_metric}@{args.mbfl_weight})"
            )
        try:
            localization_result = localizer.localize(bug, checkout)
            writer.log(
                f"Localization done: {len(localization_result.ranked_locations)} locations ranked"
            )
        except Exception as exc:
            writer.log(f"Localization failed: {exc}")
            raise

    # -- Repair + patch validation pipeline (2) --
    # The RepairEvaluationRunner drives the generate-and-validate loop, compares
    # plausible patches against the developer fix (correctness), records the
    # validation metrics, and writes repair_results.json + patch artifacts.
    from apr_framework.evaluation.repair_runner import RepairEvaluationRunner

    if args.technique == "template":
        algorithm = TemplateRepairAlgorithm(
            localization_result=localization_result,
            adapter=adapter,
            config=template_repair_config,
        )
        writer.log(
            f"Repair started: budget={args.budget}, top_n={args.top_n}, "
            f"operators={template_repair_config.enabled_operators}"
        )
    elif args.technique == "llm":
        algorithm = _build_llm_algorithm(args, localization_result, adapter)
        writer.log(
            f"Repair started: budget={args.budget}, top_n={args.top_n}, "
            f"model={args.model}, temperature={args.temperature}, "
            f"max_candidates={args.max_candidates}"
        )
    else:
        raise ConfigurationError(f"Unknown repair technique: {args.technique!r}")

    ranker = _build_ranker(args)
    if ranker is not None:
        writer.log(f"Patch ranker: {ranker.name}")
        config_data["ranker"] = ranker.name
    else:
        config_data["ranker"] = "none"

    runner = RepairEvaluationRunner(
        project_root=project_root,
        runs_dir=runs_dir,
        budget=args.budget,
        stop_on_first=args.stop_on_first,
        config_data=config_data,
        writer=writer,
        ranker=ranker,
        localization_result=localization_result,
    )
    eval_results = runner.run([bug], adapter, algorithm)
    result = eval_results[0]
    metrics = result.metrics

    writer.log(
        f"Repair finished: status={result.status}, "
        f"candidates_validated={metrics.candidates_validated}, "
        f"elapsed={metrics.total_wall_clock_seconds:.1f}s"
    )

    # -- Print summary --
    ttfp = metrics.time_to_first_plausible_seconds
    ttfp_str = f"{ttfp:.1f}s" if ttfp is not None else "n/a"
    print(f"\nRun directory: {writer.run_dir}")
    print(f"Project:       {canonical_project}")
    print(f"Bug ID:        {bug_id}")
    print(f"Status:        {result.status}")
    print(f"Generated:     {metrics.total_candidates_generated} candidate(s)")
    print(f"Validated:     {metrics.candidates_validated} candidate(s)")
    print(f"Plausible:     {metrics.plausible_count} patch(es)")
    print(f"Correct:       {metrics.correct_count} patch(es)")
    print(f"1st plausible: {ttfp_str}")
    print(f"Total time:    {metrics.total_wall_clock_seconds:.1f}s")
    if ranker is not None:
        rank_str = str(metrics.rank_of_first_correct) if metrics.rank_of_first_correct is not None else "n/a"
        print(f"Rank of 1st correct (ranked): {rank_str}")

    return 0


def _build_ranker(args):
    """Construct a PatchRanker from CLI args, or return None if ranking is disabled."""
    if args.ranker == "none":
        return None
    from apr_framework.repair.ranking import create_ranker

    ranker_kwargs: dict = {}
    if args.ranker_weights:
        weight_parts = [part.strip() for part in args.ranker_weights.split(",")]
        if len(weight_parts) != 3:
            raise ConfigurationError(
                "--ranker-weights must be exactly three comma-separated numbers: "
                "suspiciousness_weight,simplicity_weight,operator_priority_weight"
            )
        try:
            ranker_kwargs = {
                "suspiciousness_weight": float(weight_parts[0]),
                "simplicity_weight": float(weight_parts[1]),
                "operator_priority_weight": float(weight_parts[2]),
            }
        except ValueError:
            raise ConfigurationError(
                "--ranker-weights values must be numeric (e.g. 0.6,0.25,0.15)"
            )
    return create_ranker(args.ranker, **ranker_kwargs)


def _build_llm_algorithm(args, localization_result, adapter):
    """Construct an LLMRepairAlgorithm from CLI arguments."""
    from apr_framework.repair.llm import (
        LLMRepairAlgorithm,
        LLMRepairConfig,
        OpenAICompatibleClient,
    )

    repair_config = LLMRepairConfig(
        model_name=args.model,
        temperature=args.temperature,
        max_patch_count=args.max_candidates,
        top_n_locations=args.top_n,
        llm_provider=args.llm_provider,
        base_url=args.llm_base_url,
        api_key_env_var=args.llm_api_key_env,
        timeout_seconds=args.timeout,
        budget=args.budget,
        stop_on_first=args.stop_on_first,
        regression_check=args.regression_check,
    )
    llm_client = OpenAICompatibleClient(repair_config)
    return LLMRepairAlgorithm(
        localization_result=localization_result,
        adapter=adapter,
        repair_config=repair_config,
        llm_client=llm_client,
    )


def _write_env_var(env_file_path: Path, key_name: str, value: str) -> None:
    """Set `key_name=value` in the given .env file, replacing an existing entry or appending a new one."""
    existing_lines = (
        env_file_path.read_text().splitlines() if env_file_path.exists() else []
    )
    updated_lines = []
    key_written = False
    for line in existing_lines:
        if line.startswith(f"{key_name}="):
            updated_lines.append(f"{key_name}={value}")
            key_written = True
        else:
            updated_lines.append(line)
    if not key_written:
        updated_lines.append(f"{key_name}={value}")
    env_file_path.write_text("\n".join(updated_lines) + "\n")


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


def _run_evaluate_repair(args, project_root: Path, adapter) -> int:
    """Run the Task-5 repair comparison: each bug under both FL modes + ranker."""
    from apr_framework.core.models import CheckoutResult
    from apr_framework.evaluation.repair_comparison_runner import RepairComparisonRunner
    from apr_framework.localization import (
        FauxPyConfig,
        FauxPyLocalizer,
        FauxPyToolchain,
        HybridFaultLocalizer,
        PerfectFaultLocalizer,
    )
    from apr_framework.repair import TemplateRepairAlgorithm, TemplateRepairConfig

    adapter.toolchain.ensure_installed()
    bugs = _parse_bug_list(args.bugs or "tornado:14,scrapy:2,black:1")
    fl_modes = [mode.strip() for mode in args.fl_modes.split(",") if mode.strip()]
    for fl_mode in fl_modes:
        if fl_mode not in ("auto", "perfect"):
            raise ConfigurationError(
                f"Invalid FL mode {fl_mode!r} — expected 'auto' or 'perfect'."
            )

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = project_root / output_dir
    runs_dir = Path(args.runs_dir)
    if not runs_dir.is_absolute():
        runs_dir = project_root / runs_dir

    fauxpy_toolchain = FauxPyToolchain(adapter.toolchain)
    projects_dir = adapter.toolchain.repo_dir / "projects"

    # Resolve and validate every bug's checkout up front, keyed by canonical bug.
    canonical_bug_list: list[BugIdentifier] = []
    checkouts: dict[BugIdentifier, CheckoutResult] = {}
    for bug in bugs:
        canonical_project = adapter.resolve_project(bug.project)
        canonical_bug = BugIdentifier(
            benchmark="bugsinpy", project=canonical_project, bug_id=bug.bug_id
        )
        worktree = (
            project_root
            / ".workspace"
            / "bugsinpy"
            / f"{canonical_project}_{bug.bug_id}"
            / canonical_project
        )
        if not worktree.exists():
            raise BenchmarkError(
                f"No checkout found for {bug.project} #{bug.bug_id} at {worktree}. "
                f"Run `python -m apr_framework bugsinpy checkout {bug.project} {bug.bug_id}` "
                "and then `compile` before evaluating."
            )
        canonical_bug_list.append(canonical_bug)
        checkouts[canonical_bug] = CheckoutResult(
            bug=canonical_bug, worktree=worktree, success=True, prepared=True
        )

    def _auto_localizer(canonical_bug: BugIdentifier):
        worktree = checkouts[canonical_bug].worktree
        source_package = _infer_fauxpy_src(worktree, canonical_bug.project)
        bug_dir = projects_dir / canonical_bug.project / "bugs" / str(canonical_bug.bug_id)
        bug_test_targets = load_pytest_targets(bug_dir / "run_test.sh")
        bug_test_ids = [target for target in bug_test_targets if not target.startswith("-")]

        def _make_sbfl() -> FauxPyLocalizer:
            return FauxPyLocalizer(
                FauxPyConfig(
                    src=source_package,
                    test_targets=bug_test_targets,
                    family="sbfl",
                    granularity=args.granularity,
                    failing_tests=bug_test_ids,
                    metric=args.localization_metric,
                ),
                fauxpy_toolchain,
            )

        def _make_mbfl() -> FauxPyLocalizer:
            return FauxPyLocalizer(
                FauxPyConfig(
                    src=source_package,
                    test_targets=bug_test_targets,
                    family="mbfl",
                    granularity=args.granularity,
                    failing_tests=bug_test_ids,
                    metric=args.mbfl_metric,
                    mutation_strategy="random",
                    mutation_budget=args.mutation_budget,
                    mutation_seed=args.seed,
                ),
                fauxpy_toolchain,
            )

        if args.fl_family == "sbfl":
            return _make_sbfl()
        if args.fl_family == "mbfl":
            return _make_mbfl()
        return HybridFaultLocalizer(_make_sbfl(), _make_mbfl())

    perfect_localizer = PerfectFaultLocalizer(adapter)

    def localization_provider(canonical_bug: BugIdentifier, fl_mode: str):
        checkout = checkouts[canonical_bug]
        if fl_mode == "perfect":
            return perfect_localizer.localize(canonical_bug, checkout)
        return _auto_localizer(canonical_bug).localize(canonical_bug, checkout)

    enabled_operators = [
        operator_key.strip()
        for operator_key in args.operators.split(",")
        if operator_key.strip()
    ]
    repair_config = TemplateRepairConfig(
        budget=args.budget,
        top_n_locations=args.top_n,
        enabled_operators=enabled_operators,
        timeout_per_test=args.timeout,
        stop_on_first=args.stop_on_first,
        regression_check=args.regression_check,
    )

    def repair_algorithm_factory(localization_result):
        return TemplateRepairAlgorithm(
            localization_result=localization_result,
            adapter=adapter,
            config=repair_config,
        )

    ranker = _build_ranker(args)
    repair_config_data = {
        "technique": "template",
        "budget": repair_config.budget,
        "top_n_locations": repair_config.top_n_locations,
        "enabled_operators": repair_config.enabled_operators,
        "timeout_per_test": repair_config.timeout_per_test,
        "stop_on_first": repair_config.stop_on_first,
        "regression_check": repair_config.regression_check,
        "fl_family": args.fl_family,
        "localization_metric": args.localization_metric,
        "granularity": args.granularity,
    }

    runner = RepairComparisonRunner(
        project_root=project_root,
        runs_dir=runs_dir,
        ranker=ranker,
        repair_config_data=repair_config_data,
        budget=repair_config.budget,
        stop_on_first=repair_config.stop_on_first,
    )

    print(
        f"Evaluating {len(bugs)} bug(s) x {len(fl_modes)} FL mode(s) "
        f"({', '.join(fl_modes)}) with ranker={ranker.name if ranker else 'none'}..."
    )
    cells = runner.run(
        bugs=canonical_bug_list,
        fl_modes=fl_modes,
        benchmark=adapter,
        localization_provider=localization_provider,
        repair_algorithm_factory=repair_algorithm_factory,
    )

    readme_path = runner.write_results(cells, output_dir)
    print(f"\nResults written to: {output_dir}")
    print(f"README: {readme_path}")
    _print_repair_summary(cells)
    return 0


def _print_repair_summary(cells) -> None:
    print("\n=== Repair comparison summary ===")
    header = (
        f"{'Bug':<16} {'FL':<8} {'Gen':>4} {'Plaus':>6} {'Corr':>5} "
        f"{'GenRank':>8} {'RankRank':>9}"
    )
    print(header)
    print("-" * len(header))
    for cell in cells:
        bug_label = f"{cell.bug.project}#{cell.bug.bug_id}"
        if cell.error:
            short_error = " ".join(
                part.strip() for part in cell.error.splitlines() if part.strip()
            )
            if len(short_error) > 120:
                short_error = short_error[:120].rstrip() + " …"
            print(f"{bug_label:<16} {cell.fl_mode:<8} ERROR: {short_error}")
            continue
        generation_rank = (
            str(cell.generation_rank_of_first_correct)
            if cell.generation_rank_of_first_correct is not None
            else "-"
        )
        ranked_rank = (
            str(cell.ranked_rank_of_first_correct)
            if cell.ranked_rank_of_first_correct is not None
            else "-"
        )
        print(
            f"{bug_label:<16} {cell.fl_mode:<8} {cell.total_candidates_generated:>4} "
            f"{cell.plausible_count:>6} {cell.correct_count:>5} "
            f"{generation_rank:>8} {ranked_rank:>9}"
        )


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


