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

    return parser
