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
pytest tests/test_fauxpy_targets.py
# Run a single test:
pytest tests/test_fauxpy_targets.py::test_load_pytest_targets_accepts_direct_pytest
```

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
python -m apr_framework localize --project <project> --bug <bug_id> [--backend fauxpy] [--family sbfl|mbfl] [--granularity statement|function] [--metric ochiai|tarantula|dstar] [--top-n N] [--src <pkg>] [--failing_tests "test::id"]
python -m apr_framework bugsinpy evaluate-dummy --seed 123
```

## Architecture

All source lives under `src/apr_framework/`. Components are decoupled through abstract base classes; implementations are swapped by passing a different concrete class.

```
src/apr_framework/
  core/
    models.py        # shared dataclasses: BugIdentifier, CheckoutResult, TestRunResult,
                     # LocalizationResult, RankedLocation, PatchCandidate, RepairAttemptResult, EvaluationResult
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
                     # load_pytest_targets
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

**Shared domain models.** All components communicate through dataclasses from `core/models.py` — not raw strings or dicts. `LocalizationResult.metadata["all_metrics"]` stores every metric table parsed from FauxPy output so later stages (repair, reporting) can consume any metric without re-running FauxPy.

**FauxPy isolation.** `FauxPyLocalizer` implements `FaultLocalizer`; `FauxPyToolchain` handles FauxPy installation, pytest invocation, and output parsing. `parse_fauxpy_output` handles both statement rows (`File | Line | Score`) and function rows (`File | Function | Line | Score`).

**`load_pytest_targets`** in `localization/fauxpy.py` converts BugsInPy `run_test.sh` scripts (pytest or `python -m unittest`) into pytest-compatible target strings. It raises `ConfigurationError` for `unittest discover`.

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
