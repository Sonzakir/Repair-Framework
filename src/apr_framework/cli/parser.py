"""
To parse Command Line Arguments
Define here:
    What top-level commands exits
    What nested subcommands exits
    What extra arguments each command needs
"""

import argparse


def build_parser() -> argparse.ArgumentParser:
    """
    Creates and configures the CLI grammar of the framework
    Returns:
        argparse.ArgumentParser:
    """
    parser = argparse.ArgumentParser(prog="apr_framework")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-benchmarks")

    # FauxPy CLI commands 
    localize_parser = subparsers.add_parser("localize")
    localize_parser.add_argument("--backend", choices=["fauxpy"], default="fauxpy")
    localize_parser.add_argument("--project", required=True)
    localize_parser.add_argument("--bug", type=int, required=True)
    localize_parser.add_argument("--src", default=None)
    localize_parser.add_argument("--family" , type=str , choices=["sbfl", "mbfl", "hybrid"] ,default="sbfl")
    localize_parser.add_argument("--mbfl", action="store_true")
    localize_parser.add_argument("--granularity" , type=str, default="statement" , choices=["statement" , "function"])
    localize_parser.add_argument("--failing_tests" , type=str , default=None)
    localize_parser.add_argument("--test-target", action="append", default=None)
    localize_parser.add_argument("--top-n", type=int, default=None)
    localize_parser.add_argument("--show-raw-output", action="store_true")
    localize_parser.add_argument(
        "--mutation-strategy",
        "--mutation_strategy",
        dest="mutation_strategy",
        type=str,
        default=None,
    )
    localize_parser.add_argument(
        "--budget",
        "--mutation-budget",
        "--mutation_budget",
        dest="mutation_budget",
        type=int,
        default=None,
    )
    localize_parser.add_argument("--seed", type=int, default=0)
    localize_parser.add_argument("--metric", type=str, default=None)
    localize_parser.add_argument("--sbfl-metric", type=str, default="ochiai")
    localize_parser.add_argument("--mbfl-metric", type=str, default="metallaxis")
    localize_parser.add_argument("--sbfl-weight", type=float, default=0.5)
    localize_parser.add_argument("--mbfl-weight", type=float, default=0.5)
    localize_parser.add_argument("--runs-dir", default="runs")


    

    ### BugsInPy CLI commands
    bugsinpy_parser = subparsers.add_parser("bugsinpy")
    bugsinpy_subparsers = bugsinpy_parser.add_subparsers(
        dest="bugsinpy_command", required=True
    )

    ## bugsinpy-setip
    bugsinpy_subparsers.add_parser("setup")
    bugsinpy_subparsers.add_parser("list-projects")

    ## bugsinpy-list-bugs
    list_bugs_parser = bugsinpy_subparsers.add_parser("list-bugs")
    list_bugs_parser.add_argument("project")

    ## bugsinpy-checkout
    checkout_parser = bugsinpy_subparsers.add_parser("checkout")
    checkout_parser.add_argument("project")
    checkout_parser.add_argument("bug_id", type=int)

    ## bugsinpy-compile (safe compile)
    compile_parser = bugsinpy_subparsers.add_parser("compile")
    compile_parser.add_argument("project")
    compile_parser.add_argument("bug_id", type=int)

    ## bugsinpy-test
    test_parser = bugsinpy_subparsers.add_parser("test")
    test_parser.add_argument("project")
    test_parser.add_argument("bug_id", type=int)

    ## bugsinpy-evaluate-dummy
    evaluate_dummy_parser = bugsinpy_subparsers.add_parser("evaluate-dummy")
    evaluate_dummy_parser.add_argument("--seed", type=int, default=None)
    evaluate_dummy_parser.add_argument("--runs-dir", default="runs")

    ## bugsinpy-evaluate-localization
    eval_loc_parser = bugsinpy_subparsers.add_parser(
        "evaluate-localization",
        help="Run SBFL/MBFL/Hybrid on a set of bugs and compare rankings against ground truth.",
    )
    eval_loc_parser.add_argument(
        "--output-dir",
        default="experiment_results",
        help="Directory to write results.json and README.md (default: experiment_results).",
    )
    eval_loc_parser.add_argument(
        "--top-ks",
        default="1,5,10",
        help="Comma-separated Top-k values to report (default: 1,5,10).",
    )
    eval_loc_parser.add_argument(
        "--budget",
        type=int,
        default=50,
        help="MBFL mutation budget — max mutants per bug (default: 50).",
    )
    eval_loc_parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed for MBFL mutation selection (default: 0).",
    )
    eval_loc_parser.add_argument(
        "--granularity",
        choices=["statement", "function"],
        default="statement",
        help="Localization granularity (default: statement).",
    )
    eval_loc_parser.add_argument(
        "--bugs",
        default=None,
        help=(
            "Comma-separated list of project:bug_id pairs to evaluate "
            "(e.g. black:1,black:3,black:7). "
            "Defaults to black:1,black:3,black:7."
        ),
    )

    # Repair command
    repair_parser = subparsers.add_parser(
        "repair",
        help="Apply template-based APR to a checked-out and localized bug.",
    )
    repair_parser.add_argument("--project", required=True, help="BugsInPy project name")
    repair_parser.add_argument("--bug", type=int, required=True, help="Bug ID")
    repair_parser.add_argument(
        "--technique",
        choices=["template"],
        default="template",
        help="Repair technique (default: template)",
    )
    repair_parser.add_argument(
        "--budget",
        type=int,
        default=200,
        help="Max patch validations (default: 200)",
    )
    repair_parser.add_argument(
        "--top-n",
        dest="top_n",
        type=int,
        default=5,
        help="Top-N suspicious locations to attempt (default: 5)",
    )
    repair_parser.add_argument(
        "--operators",
        type=str,
        default="arith,comp,obo,bool,negate,return",
        help="Comma-separated list of enabled mutation operators (default: all)",
    )
    repair_parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Seconds allowed per test-suite invocation (default: 120)",
    )
    repair_parser.add_argument(
        "--stop-on-first",
        dest="stop_on_first",
        action="store_true",
        help="Stop after the first plausible patch is found",
    )
    repair_parser.add_argument(
        "--no-regression-check",
        dest="regression_check",
        action="store_false",
        help=(
            "Only require the bug's trigger test to pass for plausibility; skip the "
            "regression run that verifies no previously passing test broke (faster)"
        ),
    )
    repair_parser.set_defaults(regression_check=True)
    repair_parser.add_argument(
        "--fl-family",
        dest="fl_family",
        choices=["sbfl", "mbfl", "hybrid"],
        default="sbfl",
        help="Fault-localization family used to rank repair targets (default: sbfl)",
    )
    repair_parser.add_argument(
        "--localization-metric",
        dest="localization_metric",
        type=str,
        default="ochiai",
        help="SBFL metric used when re-running localization (default: ochiai)",
    )
    repair_parser.add_argument(
        "--mbfl-metric",
        dest="mbfl_metric",
        type=str,
        default="metallaxis",
        help="MBFL metric (used for --fl-family mbfl/hybrid; default: metallaxis)",
    )
    repair_parser.add_argument(
        "--mutation-budget",
        dest="mutation_budget",
        type=int,
        default=50,
        help="Max mutants per bug for MBFL/hybrid localization (default: 50)",
    )
    repair_parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed for MBFL mutation selection (default: 0)",
    )
    repair_parser.add_argument(
        "--sbfl-weight",
        dest="sbfl_weight",
        type=float,
        default=0.5,
        help="Weight of the SBFL backend for --fl-family hybrid (default: 0.5)",
    )
    repair_parser.add_argument(
        "--mbfl-weight",
        dest="mbfl_weight",
        type=float,
        default=0.5,
        help="Weight of the MBFL backend for --fl-family hybrid (default: 0.5)",
    )
    repair_parser.add_argument(
        "--skip-localize",
        dest="skip_localize",
        action="store_true",
        help="Skip re-running localization; load a cached result from disk",
    )
    repair_parser.add_argument(
        "--granularity",
        type=str,
        default="statement",
        choices=["statement", "function"],
        help="Localization granularity used when re-running (default: statement)",
    )
    repair_parser.add_argument(
        "--runs-dir",
        dest="runs_dir",
        default="runs",
        help="Directory for run output (default: runs)",
    )

    return parser
