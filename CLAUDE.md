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

> **Validation requirement — Docker end-to-end is mandatory.** Unit tests (`pytest tests/`) are NOT sufficient to accept a change. Every change must be executed end-to-end inside the Docker container and its real results observed before the work is considered done. Build and run the framework via Docker Compose, run the affected command(s) against an actual checked-out/compiled bug, and confirm the output is correct — do not rely on import smoke tests or local reasoning alone:
> ```bash
> docker compose build
> docker compose run --rm apr-framework
> # Inside the container, exercise the actual changed path, e.g.:
> python -m apr_framework bugsinpy setup
> python -m apr_framework bugsinpy test <project> <bug_id>     # checkout + compile + run tests
> python -m apr_framework localize --project <project> --bug <bug_id> [flags exercising the change]
> ```

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
  [--src <pkg>] [--failing_tests "test::id"] [--test-target "test::id"] \
  [--show-raw-output]

# MBFL localization
python -m apr_framework localize --project <project> --bug <bug_id> \
  --mbfl [--granularity statement|function] \
  [--metric metallaxis|muse] [--top-n N] \
  [--mutation-strategy random] [--budget N] [--seed N]

# Hybrid localization (weighted merge of SBFL + MBFL)
python -m apr_framework localize --project <project> --bug <bug_id> \
  --family hybrid [--granularity statement|function] \
  [--sbfl-metric ochiai] [--mbfl-metric metallaxis] \
  [--sbfl-weight 0.5] [--mbfl-weight 0.5] [--top-n N]

python -m apr_framework bugsinpy evaluate-dummy --seed 123

# Template-based repair (Task 1–4)
python -m apr_framework repair --project <project> --bug <bug_id> \
  [--technique template] [--budget N] [--top-n N] \
  [--operators arith,comp,obo,bool,negate,return] [--timeout N] \
  [--stop-on-first] [--no-regression-check] \
  [--fl-mode auto|perfect] [--fl-family sbfl|mbfl|hybrid] \
  [--localization-metric ochiai] [--mbfl-metric metallaxis] \
  [--skip-localize] [--granularity statement|function] \
  [--ranker weighted|none] [--ranker-weights w1,w2,w3] \
  [--runs-dir runs]

# Repair evaluation matrix (Task 5): each bug x {auto, perfect} FL + ranker
python -m apr_framework bugsinpy evaluate-repair \
  [--bugs project:id,project:id,...] [--fl-modes auto,perfect] \
  [--fl-family sbfl|mbfl|hybrid] [--localization-metric ochiai] \
  [--operators ...] [--budget N] [--top-n N] [--ranker weighted|none] \
  [--output-dir experiment_results/repair] [--runs-dir runs]
```

`--test-target` is repeatable (`action="append"`); pass it once per pytest target. When `--metric` is omitted for SBFL/MBFL the family default applies; for hybrid runs use `--sbfl-metric`/`--mbfl-metric` instead.

`--ranker none` is the default — no ranking, output identical to pre-Task-4 behavior. `--ranker weighted` opts in to ranking; `--ranker-weights` then overrides the three component weights (suspiciousness, simplicity, operator_priority) — only relative magnitudes matter, they are normalised internally. When ranking is off, `ranked_plausible_patches` is absent (`null`) from the JSON.

## Architecture

All source lives under `src/apr_framework/`. Components are decoupled through abstract base classes; implementations are swapped by passing a different concrete class.

```
src/apr_framework/
  core/
    models.py        # shared dataclasses: BugIdentifier, CheckoutResult, TestRunResult,
                     # LocalizationResult, RankedLocation, PatchCandidate, RepairAttemptResult,
                     # EvaluationResult, LocalizationConfig, RepairRunMetrics (incl. rank_of_first_correct)
    exceptions.py    # APRFrameworkError, BenchmarkError, ConfigurationError
  benchmarks/
    base.py          # BenchmarkAdapter ABC (checkout / prepare_environment / run_tests / list_*)
    bugsinpy.py      # BugsInPyAdapter + BugsInPyToolchain (all Docker/shell calls go here)
    registry.py      # create_bugsinpy_adapter(), list_benchmark_names()
  cli/
    parser.py        # argparse grammar (build_parser())
    app.py           # command dispatch (main()), _build_ranker()
  localization/
    base.py          # FaultLocalizer ABC
    fauxpy.py        # FauxPyLocalizer, FauxPyConfig, FauxPyToolchain, parse_fauxpy_output,
                     # load_pytest_targets, extract_mbfl_tracking_metadata
    hybrid.py        # HybridFaultLocalizer — weighted normalized merge of SBFL + MBFL rankings
    perfect.py       # PerfectFaultLocalizer — oracle locations from bug_patch.txt (Task 3)
  repair/
    base.py          # RepairAlgorithm ABC
    dummy.py         # DummyRepairAlgorithm (random ground-truth / no-op)
    correctness.py   # is_correct_patch — diff-level comparison against developer fix
    regression.py    # build_regression_context, parse_failing_test_ids — regression half of plausibility
    run_loop.py      # run_validation_loop — shared budget loop used by runner and algorithm
    ranking/
      base.py        # PatchRanker ABC
      weighted.py    # WeightedCompositeRanker — suspiciousness + simplicity + operator_priority
      registry.py    # create_ranker() factory
    template/
      algorithm.py   # TemplateRepairAlgorithm
      config.py      # TemplateRepairConfig
      operators.py   # AST mutation operators (arith, comp, obo, bool, negate, return)
      patch_generator.py  # generate_patches_for_location — builds PatchCandidate list
      validator.py   # plausibility check (trigger + regression)
  evaluation/
    base.py          # EvaluationRunner ABC
    dummy_runner.py  # DummyEvaluationRunner — writes runs/run_NNN/{config,results,execution.log}
    repair_runner.py # RepairEvaluationRunner — drives validation loop, correctness, ranking, JSON output
    run_writer.py    # RunWriter — manages run_NNN directory, log, JSON writes
    ground_truth.py  # ground-truth helpers for perfect FL
    localization_runner.py  # LocalizationComparisonRunner for evaluate-localization
    repair_comparison_runner.py  # RepairComparisonRunner (Task 5) — drives bug x FL-mode repair matrix, aggregates results.json + README.md
  reporting/
    base.py          # ReportGenerator ABC
    archive.py       # ArchiveReportGenerator — writes report.md summary + zips run artifacts
```

### Key design decisions

**Two-container model.** The framework container (Python + Docker CLI) manages a long-lived sibling container named `apr-bugsinpy-executor` that runs BugsInPy commands. The framework never executes BugsInPy commands locally; all subprocess calls are routed through `BugsInPyToolchain`. When `APR_HOST_PROJECT_ROOT` is not set, volume mounts for the executor container will fail.

**Custom BugsInPy fork.** The framework uses a fork of BugsInPy (`https://github.com/Sonzakir/BugsInPy.git`) that adds pyenv-based multi-Python support and a `bugsinpy-safe-compile` wrapper. The original does not support multiple Python versions.

**Shared domain models.** All components communicate through dataclasses from `core/models.py` — not raw strings or dicts. `LocalizationResult.metadata["all_metrics"]` stores every metric table parsed from FauxPy output so later stages (repair, reporting) can consume any metric without re-running FauxPy. For MBFL runs, `metadata` also stores cost-control fields from `extract_mbfl_tracking_metadata` (e.g. `mutants_generated`, `mutants_validated`, `mutation_generation_time_seconds`).

**FauxPy isolation.** `FauxPyLocalizer` implements `FaultLocalizer`; `FauxPyToolchain` handles pinned FauxPy 0.7.0 installation and applies **two** in-place source patches before every localization run:
- *SBFL metric patch* — adds `MetricJaccard` and `MetricSBI` to FauxPy's SQLite schema and ranking pipeline (these metrics are not in stock FauxPy 0.7.0).
- *MBFL selection patch* — injects `--mutation-selection`, `--mutation-budget`, and `--mutation-seed` pytest options so the framework can cap expensive mutant validation.

Both patches use `replace_once` helpers that are idempotent (safe to re-apply). `parse_fauxpy_output` handles both statement rows (`File | Line | Score`) and function rows (`File | Function | Line | Score`); for function granularity it also captures the optional end line, populating `RankedLocation.line`, `.end_line`, and `.function`.

**Hybrid localization.** `HybridFaultLocalizer` (`localization/hybrid.py`) runs both the SBFL and MBFL localizers, min-max-normalizes each backend's scores independently, then combines them with normalized `sbfl_weight`/`mbfl_weight` and re-ranks. Ties break toward locations found by *both* backends, then by best per-backend rank. The reusable merge logic lives in the static `HybridFaultLocalizer.combine_rankings`; the combined `LocalizationResult.metadata` records the effective weights and the per-backend score formulas. Selected via `--family hybrid` with `--sbfl-metric`/`--mbfl-metric` (not `--metric`).

**`load_pytest_targets`** in `localization/fauxpy.py` converts BugsInPy `run_test.sh` scripts (pytest or `python -m unittest`) into pytest-compatible target strings. It raises `ConfigurationError` for `unittest discover`.

**`FauxPyConfig` metric defaults.** When `--metric` is not supplied, the default is `ochiai` for SBFL and `metallaxis` for MBFL. Validation in `__post_init__` rejects unsupported family/granularity/mutation combinations before any subprocess runs.

**Template-based repair.** `TemplateRepairAlgorithm` uses six AST mutation operators (`arith`, `comp`, `obo`, `bool`, `negate`, `return`) to generate syntactically valid variants at the top-N suspicious locations from FL. Validation applies each variant to the checkout, runs the test suite in the executor container, and restores the file unconditionally. The generate-and-validate loop lives in `run_loop.py` — not inside the algorithm — so it is shared with `RepairEvaluationRunner` and works unchanged with future backends.

**Perfect fault localization.** `PerfectFaultLocalizer` (`localization/perfect.py`) implements `FaultLocalizer` by parsing the developer fix from `bug_patch.txt` instead of running tests. It produces a `LocalizationResult` with `backend="perfect-fl"` that flows into the same repair pipeline. Selected with `--fl-mode perfect`; the `--fl-family` flag is ignored in this mode.

**Patch ranking is optional and non-destructive.** `RepairEvaluationRunner` accepts an optional `ranker: PatchRanker | None`. When provided, it reorders plausible results after the correctness check and writes both orderings into `repair_results.json`: `plausible_patches` (generation order, the baseline) and `ranked_plausible_patches` (ranked order). `rank_of_first_correct` (1-indexed) is stored in `RepairRunMetrics` and emitted at the top level of each bug's JSON payload. The `PatchRanker` ABC lives in `repair/ranking/base.py`; the only current implementation is `WeightedCompositeRanker` (`repair/ranking/weighted.py`), which combines a suspiciousness score, patch simplicity, and operator priority using a configurable weighted sum. Enabled by default with `--ranker weighted`; disabled with `--ranker none`.

**Repair evaluation matrix (Task 5).** `bugsinpy evaluate-repair` runs the full repair pipeline on a set of bugs under both `auto` and `perfect` FL with the ranker applied, then writes an aggregated `experiment_results/repair/{results.json,README.md}` (per-bug tables, aggregate, generated discussion). `RepairComparisonRunner` (`evaluation/repair_comparison_runner.py`) only orchestrates the matrix and aggregates — each (bug, FL mode) cell is executed by the existing `RepairEvaluationRunner` and gets its own `runs/run_NNN` directory (logs + patch diffs preserved as artifacts). A localization failure for one cell (e.g. FauxPy uninstallable on a bug's Python) is captured as an error cell rather than aborting the matrix. This mirrors the `evaluate-localization` / `LocalizationComparisonRunner` pattern.

### Directory conventions
```
.tools/bugsinpy        # BugsInPy clone (git submodule managed by setup command)
.workspace/bugsinpy/   # checked-out project worktrees (e.g. PySnooper_1/PySnooper/)
runs/run_NNN/          # evaluation outputs: config.json, results.json, execution.log
```

## Naming conventions

These rules apply to every variable and method name written or modified in this codebase. They are enforced during code review and must be respected when generating new code.

### Variable naming rules

**No single-letter variables** outside of math/index contexts (`i`, `j`, `k` in tight loops are acceptable; `r`, `x`, `v`, `n` as standalone locals are not).

**No vague abbreviations.** Forbidden: `op`, `src`, `cls`, `val`, `arg`, `tmp`, `res`, `obj`, `cfg`, `ctx`, `msg`. Write the full word or a precise compound.

**No misleading names** that imply more than the variable actually holds. Example: do not call a variable `best` if it is merely the first item in a list.

**No generic nouns without qualifying context.** Words like `result`, `data`, `info`, `item`, `value`, `output`, `working`, `trigger`, `baseline`, `candidate` are only acceptable when the surrounding type already makes the content unambiguous, and even then a more precise compound is preferred.

**Count variables must say they are counts.** Append `_count`:
- `passed` → `passed_count`, `plausible` → `plausible_count`

**Variables holding `Path` objects or path strings must say so.** Append `_path` (for `Path`) or `_path_str` / `_str` (for raw strings):
- `raw` holding a file-path string → `file_path_str`
- `candidate` holding a `Path` → `candidate_file_path`

**Variables holding collections of domain objects must name both the adjective and the noun.** A list of plausible `RepairAttemptResult` objects → `plausible_results`, not `plausible`. A list of ranked locations → `ranked_locations`, not `locations`.

**Variables holding test-run results must say so.** Suffix with `_run_result` or `_result`:
- `baseline` holding a `TestRunResult` → `baseline_run_result`
- `regression` holding a `TestRunResult` → `regression_run_result`

### Method naming rules

**Methods must describe what they return or do, not just what they touch.** Prefer verb phrases:
- `get_patch()` → `generate_patch()` or `fetch_patch()` depending on whether it computes or retrieves
- `process()` → name the specific action: `validate_candidates()`, `normalise_scores()`

**Boolean-returning methods must start with `is_`, `has_`, or `can_`.** Examples: `is_plausible()`, `has_reference_patch()`, `can_derive_suite_command()`.

**Factory and builder methods** that construct and return an object must start with `build_`, `create_`, or `make_`:
- `regression_context()` → `build_regression_context()`

**Private helpers** (single leading underscore) follow the same rules. The leading underscore does not relax the clarity requirement.

### Concrete examples from this codebase

| Was | Now | Rule violated |
|-----|-----|---------------|
| `trigger` (NameError — undefined) | `trigger_command_content` | wrong name, variable didn't exist |
| `r for r in self.all_results` | `attempt_result for attempt_result in self.all_results` | single-letter variable |
| `op`, `src`, `line` (logging locals) | `operator_key`, `source_path_str`, `target_line_str` | vague abbreviations |
| `plausible` (list of results) | `plausible_results` | generic noun without noun qualifier |
| `first_plausible` (a result object) | `first_plausible_result` | incomplete compound |
| `cls` (holds a class type) | `operator_class` | vague abbreviation in the explicit banned list |
| `raw` (file-path string) | `file_path_str` | no `_str` suffix for path string |
| `stripped` (a `Path`) | `stripped_file_path` | no `_path` suffix for `Path` object |

## Troubleshooting

- If the executor container has stale volume mounts: `docker rm -f apr-bugsinpy-executor` then re-run `bugsinpy setup`.
- If running outside Docker Compose: `export APR_HOST_PROJECT_ROOT="$(pwd)"` before setup.
- On Windows: change line endings from CRLF to LF for shell scripts.
- FauxPy localization requires a checked-out and compiled bug. Run `checkout` then `compile` (or `test`, which does both) before `localize`.
- FauxPy currently requires `run_test.sh` to invoke pytest directly. Projects using only `unittest discover` are not supported.
- If FauxPy reports a missing `Jaccard` or `SBI` metric, the framework's SBFL patch was not applied — check that the checkout's virtual environment is intact and re-run `compile`.
- To do a full clean rebuild: `docker compose down --remove-orphans && docker rm -f apr-bugsinpy-executor 2>/dev/null; docker rmi apr-framework:local apr-bugsinpy:local 2>/dev/null; docker compose build --no-cache`.
