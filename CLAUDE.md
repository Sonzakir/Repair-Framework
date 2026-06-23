# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

An Automated Program Repair (APR) research framework that integrates the BugsInPy benchmark and FauxPy fault localization tool. The framework runs as a Python CLI (`python -m apr_framework`) inside Docker, controlling a sibling BugsInPy executor container via Docker-in-Docker.

## Commands

### Setup (Docker Compose — required for BugsInPy)
```bash
docker compose build
docker compose run --rm apr-framework
# Inside the container:
python -m apr_framework bugsinpy setup
```

### Local editable install (for unit tests and import checks only — no Docker needed)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

### Run tests
```bash
pytest tests/
# Run a single test file:
pytest tests/test_imports.py
# Run a single parametrized test by module name:
pytest "tests/test_imports.py::test_public_modules_import[apr_framework.localization.fauxpy]"
```

The only test file is `tests/test_imports.py`, which parametrizes a smoke-import check over every public module. Integration tests require Docker.

### CLI entry points
```bash
python -m apr_framework <command>
apr-framework <command>         # installed script alias
```

Key commands:
```bash
python -m apr_framework list-benchmarks
python -m apr_framework bugsinpy setup
python -m apr_framework bugsinpy list-projects
python -m apr_framework bugsinpy list-bugs <project>
python -m apr_framework bugsinpy checkout <project> <bug_id>
python -m apr_framework bugsinpy compile <project> <bug_id>
python -m apr_framework bugsinpy test <project> <bug_id>

# SBFL localization (default family)
python -m apr_framework localize --project <project> --bug <bug_id> \
  [--backend fauxpy] [--family sbfl] [--granularity statement|function] \
  [--metric ochiai|tarantula|dstar|jaccard|sbi] [--top-n N] \
  [--src <pkg>] [--failing_tests "test::id"] [--show-raw-output]

# MBFL localization
python -m apr_framework localize --project <project> --bug <bug_id> \
  --mbfl [--granularity statement|function] \
  [--metric metallaxis|muse] [--top-n N] \
  [--mutation-strategy random] [--budget N] [--seed N]

python -m apr_framework bugsinpy evaluate-dummy --seed 123
```

## Architecture

All source lives under `src/apr_framework/`. Components are decoupled through abstract base classes; implementations are swapped by passing a different concrete class.

```
src/apr_framework/
  core/
    models.py        # shared dataclasses: BugIdentifier, CheckoutResult, TestRunResult,
                     # LocalizationResult, RankedLocation, PatchCandidate, RepairAttemptResult,
                     # EvaluationResult, LocalizationConfig
    exceptions.py    # APRFrameworkError, BenchmarkError, ConfigurationError
  benchmarks/
    base.py          # BenchmarkAdapter ABC (checkout / prepare_environment / run_tests / list_*)
    bugsinpy.py      # BugsInPyAdapter + BugsInPyToolchain (all Docker/shell calls go here)
    registry.py      # create_bugsinpy_adapter(), list_benchmark_names()
  cli/
    parser.py        # argparse grammar (build_parser())
    app.py           # command dispatch (main())
  localization/
    base.py          # FaultLocalizer ABC
    fauxpy.py        # FauxPyLocalizer, FauxPyConfig, FauxPyToolchain, parse_fauxpy_output,
                     # load_pytest_targets, extract_mbfl_tracking_metadata
  repair/
    base.py          # RepairAlgorithm ABC
    dummy.py         # DummyRepairAlgorithm (random ground-truth / no-op)
  evaluation/
    base.py          # EvaluationRunner ABC
    dummy_runner.py  # DummyEvaluationRunner — writes runs/run_NNN/{config,results,execution.log}
  reporting/
    base.py          # ReportGenerator ABC (not yet implemented)
```

### Key design decisions

**Two-container model.** The framework container (Python + Docker CLI) manages a long-lived sibling container named `apr-bugsinpy-executor` that runs BugsInPy commands. The framework never executes BugsInPy commands locally; all subprocess calls are routed through `BugsInPyToolchain`. When `APR_HOST_PROJECT_ROOT` is not set, volume mounts for the executor container will fail.

**Custom BugsInPy fork.** The framework uses a fork of BugsInPy (`https://github.com/Sonzakir/BugsInPy.git`) that adds pyenv-based multi-Python support and a `bugsinpy-safe-compile` wrapper. The original does not support multiple Python versions.

**Shared domain models.** All components communicate through dataclasses from `core/models.py` — not raw strings or dicts. `LocalizationResult.metadata["all_metrics"]` stores every metric table parsed from FauxPy output so later stages (repair, reporting) can consume any metric without re-running FauxPy. For MBFL runs, `metadata` also stores cost-control fields from `extract_mbfl_tracking_metadata` (e.g. `mutants_generated`, `mutants_validated`, `mutation_generation_time_seconds`).

**FauxPy isolation.** `FauxPyLocalizer` implements `FaultLocalizer`; `FauxPyToolchain` handles pinned FauxPy 0.7.0 installation and applies **two** in-place source patches before every localization run:
- *SBFL metric patch* — adds `MetricJaccard` and `MetricSBI` to FauxPy's SQLite schema and ranking pipeline (these metrics are not in stock FauxPy 0.7.0).
- *MBFL selection patch* — injects `--mutation-selection`, `--mutation-budget`, and `--mutation-seed` pytest options so the framework can cap expensive mutant validation.

Both patches use `replace_once` helpers that are idempotent (safe to re-apply). `parse_fauxpy_output` handles both statement rows (`File | Line | Score`) and function rows (`File | Function | Line | Score`).

**`load_pytest_targets`** in `localization/fauxpy.py` converts BugsInPy `run_test.sh` scripts (pytest or `python -m unittest`) into pytest-compatible target strings. It raises `ConfigurationError` for `unittest discover`.

**`FauxPyConfig` metric defaults.** When `--metric` is not supplied, the default is `ochiai` for SBFL and `metallaxis` for MBFL. Validation in `__post_init__` rejects unsupported family/granularity/mutation combinations before any subprocess runs.

### Directory conventions
```
.tools/bugsinpy        # BugsInPy clone (git submodule managed by setup command)
.workspace/bugsinpy/   # checked-out project worktrees (e.g. PySnooper_1/PySnooper/)
runs/run_NNN/          # evaluation outputs: config.json, results.json, execution.log
```

## Troubleshooting

- If the executor container has stale volume mounts: `docker rm -f apr-bugsinpy-executor` then re-run `bugsinpy setup`.
- If running outside Docker Compose: `export APR_HOST_PROJECT_ROOT="$(pwd)"` before setup.
- On Windows: change line endings from CRLF to LF for shell scripts.
- FauxPy localization requires a checked-out and compiled bug. Run `checkout` then `compile` (or `test`, which does both) before `localize`.
- FauxPy currently requires `run_test.sh` to invoke pytest directly. Projects using only `unittest discover` are not supported.
- If FauxPy reports a missing `Jaccard` or `SBI` metric, the framework's SBFL patch was not applied — check that the checkout's virtual environment is intact and re-run `compile`.
- To do a full clean rebuild: `docker compose down --remove-orphans && docker rm -f apr-bugsinpy-executor 2>/dev/null; docker rmi apr-framework:local apr-bugsinpy:local 2>/dev/null; docker compose build --no-cache`.
