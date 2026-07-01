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

    ## configure — interactively store an LLM API key in the local .env file
    configure_parser = subparsers.add_parser(
        "configure",
        help="Interactively store an LLM API key in the local .env file.",
    )
    configure_parser.add_argument(
        "--llm-api-key-env",
        dest="llm_api_key_env",
        type=str,
        default="GPT_AT_RUB_API_KEY",
        help="Environment variable name to store the key under (default: GPT_AT_RUB_API_KEY)",
    )

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

    ## bugsinpy-evaluate-repair (Task 5: repair pipeline comparison)
    eval_repair_parser = bugsinpy_subparsers.add_parser(
        "evaluate-repair",
        help=(
            "Run the full repair pipeline on a set of bugs under both automated FL "
            "and perfect FL, apply the ranker, and write an aggregated comparison "
            "(Assignment 3 Task 5)."
        ),
    )
    eval_repair_parser.add_argument(
        "--bugs",
        default=None,
        help=(
            "Comma-separated project:bug_id pairs to evaluate "
            "(e.g. tornado:14,scrapy:2,black:1). "
            "Defaults to tornado:14,scrapy:2,black:1."
        ),
    )
    eval_repair_parser.add_argument(
        "--fl-modes",
        dest="fl_modes",
        default="auto,perfect",
        help="Comma-separated FL modes to run per bug (default: auto,perfect).",
    )
    eval_repair_parser.add_argument(
        "--fl-family",
        dest="fl_family",
        choices=["sbfl", "mbfl", "hybrid"],
        default="sbfl",
        help="Fault-localization family used in automated FL mode (default: sbfl).",
    )
    eval_repair_parser.add_argument(
        "--localization-metric",
        dest="localization_metric",
        default="ochiai",
        help="SBFL metric used in automated FL mode (default: ochiai).",
    )
    eval_repair_parser.add_argument(
        "--mbfl-metric",
        dest="mbfl_metric",
        default="metallaxis",
        help="MBFL metric for automated FL mode (default: metallaxis).",
    )
    eval_repair_parser.add_argument(
        "--mutation-budget",
        dest="mutation_budget",
        type=int,
        default=50,
        help="Max mutants per bug for MBFL/hybrid automated FL (default: 50).",
    )
    eval_repair_parser.add_argument(
        "--seed", type=int, default=0, help="Random seed for MBFL mutation selection."
    )
    eval_repair_parser.add_argument(
        "--operators",
        default="arith,comp,obo,bool,negate,return",
        help="Comma-separated enabled mutation operators (default: all).",
    )
    eval_repair_parser.add_argument(
        "--budget", type=int, default=200, help="Max patch validations per cell (default: 200)."
    )
    eval_repair_parser.add_argument(
        "--top-n", dest="top_n", type=int, default=5,
        help="Top-N suspicious locations to attempt (default: 5).",
    )
    eval_repair_parser.add_argument(
        "--granularity", choices=["statement", "function"], default="statement",
        help="Localization granularity for automated FL (default: statement).",
    )
    eval_repair_parser.add_argument(
        "--timeout", type=int, default=120,
        help="Seconds allowed per test-suite invocation (default: 120).",
    )
    eval_repair_parser.add_argument(
        "--stop-on-first", dest="stop_on_first", action="store_true",
        help="Stop validating a cell after the first plausible patch.",
    )
    eval_repair_parser.add_argument(
        "--no-regression-check", dest="regression_check", action="store_false",
        help="Skip the regression half of plausibility (faster).",
    )
    eval_repair_parser.set_defaults(regression_check=True)
    eval_repair_parser.add_argument(
        "--ranker", choices=["weighted", "none"], default="weighted",
        help="Patch ranking strategy applied to plausible patches (default: weighted).",
    )
    eval_repair_parser.add_argument(
        "--ranker-weights", dest="ranker_weights", default=None,
        help="Comma-separated weights for the weighted ranker (default: 0.6,0.25,0.15).",
    )
    eval_repair_parser.add_argument(
        "--output-dir", default="experiment_results/repair",
        help="Directory for results.json and README.md (default: experiment_results/repair).",
    )
    eval_repair_parser.add_argument(
        "--runs-dir", dest="runs_dir", default="runs",
        help="Directory for per-cell run artifacts (default: runs).",
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
        choices=["template", "llm"],
        default="template",
        help="Repair technique: 'template' for AST mutation, 'llm' for LLM-based repair (default: template)",
    )
    repair_parser.add_argument(
        "--llm-provider",
        dest="llm_provider",
        type=str,
        default="openai-compatible",
        help="LLM client implementation to use (default: openai-compatible)",
    )
    repair_parser.add_argument(
        "--model",
        type=str,
        default="codestral-22b",
        help="LLM model name sent to the API (default: codestral-22b)",
    )
    repair_parser.add_argument(
        "--temperature",
        type=float,
        default=0.8,
        help="LLM sampling temperature in [0.0, 2.0] (default: 0.8)",
    )
    repair_parser.add_argument(
        "--max-candidates",
        dest="max_candidates",
        type=int,
        default=5,
        help="Max LLM patch candidates generated per suspicious location (default: 5)",
    )
    repair_parser.add_argument(
        "--llm-base-url",
        dest="llm_base_url",
        type=str,
        default=None,
        help="Override the LLM API endpoint URL (default: GPT@RUB endpoint)",
    )
    repair_parser.add_argument(
        "--llm-api-key-env",
        dest="llm_api_key_env",
        type=str,
        default="GPT_AT_RUB_API_KEY",
        help="Environment variable name holding the LLM API key (default: GPT_AT_RUB_API_KEY)",
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
        "--fl-mode",
        dest="fl_mode",
        choices=["auto", "perfect"],
        default="auto",
        help=(
            "Fault-localization mode: 'auto' runs the FauxPy localizer "
            "(see --fl-family); 'perfect' uses the BugsInPy developer-fix lines as "
            "the oracle fault location, ignoring --fl-family and --skip-localize "
            "(default: auto)"
        ),
    )
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
    repair_parser.add_argument(
        "--ranker",
        choices=["weighted", "none"],
        default="none",
        help=(
            "Patch ranking strategy applied to plausible patches after validation. "
            "'weighted' uses a composite score of suspiciousness, simplicity, and "
            "operator priority; 'none' preserves generation order (default: none)"
        ),
    )
    repair_parser.add_argument(
        "--ranker-weights",
        dest="ranker_weights",
        type=str,
        default=None,
        help=(
            "Comma-separated weights for the weighted ranker: "
            "suspiciousness_weight,simplicity_weight,operator_priority_weight "
            "(default: 0.6,0.25,0.15). Only used when --ranker weighted."
        ),
    )

    return parser
