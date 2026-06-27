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
    eval_loc_parser.add_argument(
        "--traditional-budget",
        dest="traditional_budget",
        type=int,
        default=200,
        help=(
            "Mutation budget for the MBFL baseline technique (default: 200). "
            "Stock FauxPy MBFL is exhaustive but impractical on large projects; "
            "this caps the baseline at a larger budget than --budget (the extension) "
            "so both complete in reasonable time while preserving the comparison."
        ),
    )

    return parser
