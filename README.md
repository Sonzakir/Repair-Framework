# Automated Debugging and Repair Framework


 
- Architectural: benchmark-specific details are hidden behind framework APIs, while repair, localization, evaluation, and reporting are modeled as replaceable/extendable components.

## What is implemented

- General Development/Source Code: Importable Python package under `src/apr_framework`
- Abstract interfaces for:
  - benchmark integrations ``src/apr_framework/benchmarks``
  - fault localization ``src/apr_framework/localization``
  - repair algorithms ``src/apr_framework/repair``
  - evaluation runners ``src/apr_framework/evaluation``
  - report generators ``src/apr_framework/reporting``
- BugsInPy benchmark adapter with support for:
  - listing available projects
  - listing bugs for a project
  - checking out buggy versions
  - preparing the checked-out environment
  - running failing tests
  - returning structured test counts and raw output
- Command-line interface via `python -m apr_framework`
- Docker-based BugsInPy executor container
- FauxPy fault-localization integration with CLI support for:
  - SBFL, MBFL, and weighted hybrid mode selection
  - statement-level and function-level granularity
  - metric selection with `--metric`
  - hybrid SBFL/MBFL metric and weight selection
  - limiting ranked locations with `--top-n`
  - optional failing-test selection with `--failing_tests`
  - parsing all FauxPy metric tables for later reuse
- Generalized FauxPy output parser that supports both `File | Line | Score`
and `File | Function | Line | Score` table formats
- Dummy repair algorithm for three BugsInPy `black` bugs (1/3/23)
- Dummy evaluation runner that creates structured run artifacts:
  - `config.json`
  - `results.json`
  - `execution.log`
  - timestamps and per-bug statuses

## Architecture


- The framework is split by responsibility in order to keep BugsInPy isolated as one adapter and leaves the rest of the system ready for future benchmarks and repair strategies.

```text
src/apr_framework/
  benchmarks/
    base.py          # BenchmarkAdapter interface (checkout/run/list/prepare_env)
    bugsinpy.py      # BugsInPy adapter and Docker-backed toolchain 
    registry.py      # benchmark factory/registry
  cli/
    app.py           # command dispatch
    parser.py        # argparse grammar
  core/
    models.py        # shared dataclasses and status enums
    exceptions.py    # framework-specific exceptions 
  evaluation/
    base.py          # EvaluationRunner interface
    dummy_runner.py  # task 3 evaluation pipeline
  localization/
    base.py          # FaultLocalizer interface
    fauxpy.py        # FauxPy localizer, config, toolchain, and output parser
    hybrid.py        # Weighted SBFL + MBFL result combiner
  repair/
    base.py          # RepairAlgorithm interface
    dummy.py         # random ground-truth/no-op repair component
  reporting/
    base.py          # ReportGenerator interface
```

### Design decisions

- **Shared domain models.** Components exchange `BugIdentifier`, `CheckoutResult`,
`TestRunResult`, `PatchCandidate`, `RepairAttemptResult`, and
`EvaluationResult` objects from `apr_framework.core.models`. This avoids passing
benchmark-specific strings through the whole system. At the same time, these models give the framework stable domain definitions, making further development easier. However, the domain models are still evolving and may change as new implementations and requirements are added.

- **Benchmark commands are hidden.** The public framework code calls
`BenchmarkAdapter.checkout`, `prepare_environment`, and `run_tests`. BugsInPy
commands such as `bugsinpy-checkout`, `bugsinpy-safe-compile`, and
`bugsinpy-test` are encapsulated inside `BugsInPyAdapter` and
`BugsInPyToolchain`.

- **BugsInPy runs in a sibling Docker container.** BugsInPy needs old Python
versions and project-specific environments. Instead of installing those into the
framework environment, the framework controls a separate executor container.
The framework container stays small and only needs Python, Git, and the Docker
CLI.

- **!!Important Disclaimer!!**: The original BugsInPy implementation is tied to a single Python version. For this project, I used my own BugsInPy branch, which adds support for multiple Python versions inside the same Docker environment. The same changes were also submitted as a pull request to the main BugsInPy repository [link](https://github.com/soarsmu/BugsInPy/pull/110).
  - In summary, my implementation: Replaces the fixed python:3.12-slim-trixie base image. Adds pyenv to the Docker image, allowing multiple Python versions to be installed and selected in one container. Installs Python versions lazily, only when a checked-out project is compiled. Adds a new wrapper script: `bugsinpy-safe-compile`.The bugsinpy-safe-compile wrapper: Reads the required Python version from the current checkout’s bugsinpy_bug.info. Sets the checkout-local Python version via .python-version. Runs the existing bugsinpy-compile command (safely, without python version issues!). 

- **Local paths separate tools from experiments.**

```text
.tools/bugsinpy       # local BugsInPy clone and metadata
.workspace/bugsinpy   # checked-out buggy projects and evaluation worktrees
runs/                 # structured experiment outputs
```

- **Repair is replaceable.** The dummy repair algorithm implements the same
`RepairAlgorithm` interface that a later different repair components can implement.

- **FauxPy is isolated behind the localization interface.** `FauxPyLocalizer`
implements `FaultLocalizer`, while `FauxPyToolchain` handles command execution,
FauxPy installation checks, pytest invocation, and output parsing. The rest of
the framework consumes structured `LocalizationResult` and `RankedLocation`
objects instead of parsing FauxPy output directly.

- **FauxPy metrics are reusable.** The configured metric is used as the primary
ranking shown by the CLI, and every metric table parsed from FauxPy output is
stored in `metadata["all_metrics"]`. This keeps Tarantula, Ochiai, DStar,
Jaccard, SBI, and other emitted tables available for later repair or reporting
components.

## Requirements

- Python 3.10 or newer
- Docker with a reachable Docker daemon
  - Docker is required for the BugsInPy integration because the framework builds and
controls a BugsInPy executor container.
- Git


## Installation

### Recommended: Docker Compose

- From the repository root (!not inside src!):

```bash
# (OPTIONAL) export APR_HOST_PROJECT_ROOT="$(pwd)"
docker compose build
docker compose run --rm apr-framework
```

- Inside the framework container, install/bootstrap BugsInPy:

```bash
python -m apr_framework bugsinpy setup
```

`bugsinpy setup` clones BugsInPy ([my branch](https://github.com/Sonzakir/BugsInPy.git)) into `.tools/bugsinpy` if needed, normalizes the
helper scripts, builds the local `apr-bugsinpy:local` image, and starts the
long-lived executor container named `apr-bugsinpy-executor`.

#### (OPTIONAL) Local editable install

- For import checks and framework development without running BugsInPy:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

- The local install is enough for unit tests and package imports. BugsInPy
commands still require Docker and a completed `bugsinpy setup`.

## CLI usage 

- List registered benchmarks:

```bash
python -m apr_framework list-benchmarks
# Currently expected output is bugsinpy
```


- Set up BugsInPy:  

```bash
python -m apr_framework bugsinpy setup
```

- List BugsInPy projects:

```bash
python -m apr_framework bugsinpy list-projects
```

- List bugs for a project: 
  - example: for black 

```bash
python -m apr_framework bugsinpy list-bugs black
```

- Check out a buggy version:

```bash
python -m apr_framework bugsinpy checkout black 1
```

- Prepare/compile an existing checkout (optional/not needed if we want to run "test" command):

```bash
python -m apr_framework bugsinpy compile black 1
```

- Check out, prepare, and run the failing tests:

```bash
python -m apr_framework bugsinpy test black 1
```

- Example output shape :
  - and optionally with the raw output for debugging purposes (since all bugs in BugsInPy are not reproducible due to missing requirements etc.) 

```text
Project: black
Bug ID: 1
Checkout success: True
Prepared: True
Tests run: 1
Passing: 0
Failing: 1
```

### FauxPy fault localization

- The sprint added a `localize` command backed by FauxPy. It runs FauxPy inside
the prepared BugsInPy checkout, parses the suspicious-location tables, and prints
ranked locations for the selected metric.

- FauxPy localization currently expects BugsInPy `run_test.sh` files that invoke
pytest directly. The examples below use `PySnooper 1`, whose BugsInPy test script
is pytest-based.

- Prepare the bug first:

```bash
python -m apr_framework bugsinpy setup
python -m apr_framework bugsinpy checkout PySnooper 1
python -m apr_framework bugsinpy compile PySnooper 1
```

- Run localization with the default FauxPy backend:

```bash
python -m apr_framework localize --project PySnooper --bug 1
```

- The backend flag is available too. At the moment, `fauxpy` is the only
implemented localization backend:

```bash
python -m apr_framework localize --backend fauxpy --project PySnooper --bug 1
```

- Choose the source root when automatic inference is not enough:

```bash
python -m apr_framework localize --project PySnooper --bug 1 --src pysnooper
```

- Select the metric used for the primary ranking:

```bash
python -m apr_framework localize --project PySnooper --bug 1 --metric ochiai
```

Jaccard and SBI are available for SBFL runs through the framework's FauxPy 0.7.0
patch, which is applied inside the prepared checkout environment before localization:

```bash
python -m apr_framework localize --project PySnooper --bug 1 --metric jaccard
python -m apr_framework localize --project PySnooper --bug 1 --metric sbi
```

Implementation note: FauxPy normally computes Tarantula, Ochiai, and DStar for
SBFL. The framework adds Jaccard and SBI by patching the installed FauxPy copy
in the bug checkout's virtual environment before running localization. The patch
adds `MetricJaccard` and `MetricSBI` formulas, registers them with FauxPy's
SBFL metric list, extends FauxPy's local SQLite score table, and lets the
existing output parser select the emitted `Scores for Jaccard` or
`Scores for SBI` tables with `--metric`.

- Limit the number of ranked locations printed:

```bash
python -m apr_framework localize --project PySnooper --bug 1 --metric ochiai --top-n 10
```

- Run function-level localization:

```bash
python -m apr_framework localize --project PySnooper --bug 1 --granularity function --metric ochiai --top-n 10
```

- Pass a failing test list to FauxPy:

```bash
python -m apr_framework localize --project PySnooper --bug 1 --failing_tests "tests/test_chinese.py::test_chinese"
```

- Run MBFL mode:

```bash
python -m apr_framework localize --project PySnooper --bug 1 --mbfl --granularity statement --metric metallaxis --top-n 10
```

- Limit expensive MBFL mutant validation runs with the random mutation selector:

```bash
python -m apr_framework localize --project PySnooper --bug 1 --mbfl --mutation-strategy random --budget 50 --metric metallaxis
```

  - `--budget` limits how many generated mutants are validated, which is the
    expensive part of MBFL.
  - `--seed` can be supplied to make random selection reproducible; it defaults
    to `0`.

- Run weighted hybrid SBFL + MBFL localization:

```bash
python -m apr_framework localize --project PySnooper --bug 1 --family hybrid --sbfl-metric ochiai --mbfl-metric metallaxis --sbfl-weight 0.5 --mbfl-weight 0.5 --mutation-strategy random --budget 50 --top-n 10
```

Hybrid mode runs SBFL and MBFL through the existing FauxPy adapter, normalizes
each selected metric, combines them with the configured weights, and applies
`--top-n` after the combined ranking is produced. MBFL mutation controls apply
only to the MBFL half of the hybrid run.

- What changed internally:
  - `FauxPyConfig` now carries the localization family, granularity, metric,
  failing tests, excludes, and MBFL selection options.
  - `FauxPyToolchain` installs pinned FauxPy 0.7.0 when needed, applies the
  Jaccard SBFL patch, and builds the pytest/FauxPy command from that config.
  - `parse_fauxpy_output` parses all metric tables when `metric_filter=None`.
  - `parse_fauxpy_output` returns only one metric's ranked rows when
  `metric_filter` is set.
  - The parser supports statement rows (`File | Line | Score`) and function rows
  (`File | Function | Line | Score`).
  - `LocalizationResult.metadata["all_metrics"]` stores the full metric map for
  later reuse.
  - `HybridFaultLocalizer` combines SBFL and MBFL `LocalizationResult` objects
  into one `hybrid-fauxpy` result while preserving component scores and ranks in
  each location's metadata.

- See `USAGE.md` for a compact command reference with the same runnable command
examples.

## Dummy repair evaluation

- Currently the project support Dummy Repair components

- `DummyRepairAlgorithm`
- `DummyEvaluationRunner`
- default bugs:
  - `bugsinpy:black:1`
  - `bugsinpy:black:3`
  - `bugsinpy:black:23`

- The dummy repair algorithm randomly chooses one of two outcomes for each
supported bug:
  - use the BugsInPy ground-truth patch from `bug_patch.txt`
  - keep the original buggy code unchanged

- Run the evaluation:
  - The seed controls the dummy repair algorithm's randomness, making Python's random choices deterministic and reproducible.

```bash
python -m apr_framework bugsinpy evaluate-dummy --seed 123
```

- The runner creates the next available run directory:
  - Example xxx'th evaluation 

```text
runs/
  run_xxx/
    config.json
    results.json
    execution.log
```

- `config.json` stores the runner, repair algorithm, benchmark, seed, timestamp,
and selected bugs. 
- `results.json` stores one structured entry per bug with
baseline tests, final tests, selected patch metadata, patch-apply output, and
status. 
- `execution.log` records the step-by-step execution timeline.

- After the run, the `ReportGenerator` implementation `ArchiveReportGenerator`
(`src/apr_framework/reporting/archive.py`) renders a human-readable `report.md`
summary into the run directory and bundles all run artifacts into a single
`runs/run_xxx.zip` archive. The archive path is printed at the end of the run.

## Template-based APR repair (Assignment 3 — Task 1)

> A standalone, learn-by-reading write-up of this technique (design decisions,
> file map, verification) lives in
> [`assignment3_task1_implementation.md`](assignment3_task1_implementation.md).

### Technique overview

The `repair` command implements a **template-based APR** strategy guided by SBFL/MBFL fault localization:

1. **Where to fix** — the top-N suspicious locations produced by `localize` (ranked by suspiciousness score) are used as repair targets.
2. **What to try** — AST mutation operators generate syntactically valid program variants at each suspicious line.
3. **Which variants pass** — each mutated variant is applied to the checkout worktree, the BugsInPy test suite is executed inside the executor container, and the file is restored unconditionally.

A patch is **plausible** only when the test command exits cleanly
(`return_code == 0`), reports zero failures and zero errors, **and** at least one
test actually passed. The exit-code and passed-count guards reject patches that
break test collection/import (which otherwise look like "0 failed, 0 error").

### Mutation operators

| Key | Description |
|---|---|
| `arith` | Swaps arithmetic operators in `BinOp` nodes: `+↔−`, `*↔/`, `//↔%` |
| `comp` | Swaps comparison operators in `Compare` nodes: `>↔>=`, `<↔<=`, `==↔!=`, `is↔is not`, `in↔not in` |
| `obo` | Off-by-one: emits `n+1` and `n-1` variants for integer constants and the upper bound of `range(n)` calls |
| `bool` | Swaps `and↔or` in `BoolOp` nodes |
| `negate` | Wraps the `test` of `if`/`while` statements in `not (...)` |
| `return` | Mutates `return True → return False` (and vice versa), and `return <expr> → return None` |

All operators accept a `target_line` parameter and restrict mutations to AST nodes whose source range covers that line — ensuring surgical, one-location-at-a-time mutations.

### Example invocations

```bash
# Full repair run (localize + repair) with default settings:
python -m apr_framework repair --project PySnooper --bug 1

# Cap budget to 20 validations, try top 3 locations only:
python -m apr_framework repair --project PySnooper --bug 1 --budget 20 --top-n 3

# Only apply arithmetic and comparison operators:
python -m apr_framework repair --project PySnooper --bug 1 --operators arith,comp

# Stop as soon as the first plausible patch is found:
python -m apr_framework repair --project PySnooper --bug 1 --stop-on-first

# Choose the fault-localization family that drives the repair targets:
python -m apr_framework repair --project PySnooper --bug 1 --fl-family mbfl --mbfl-metric metallaxis
python -m apr_framework repair --project PySnooper --bug 1 --fl-family hybrid --sbfl-weight 0.5 --mbfl-weight 0.5

# Skip re-running localization; load the most recent cached result:
python -m apr_framework repair --project PySnooper --bug 1 --skip-localize

# Use a different SBFL metric for localization:
python -m apr_framework repair --project PySnooper --bug 1 --localization-metric tarantula

# Full sequence from scratch:
python -m apr_framework bugsinpy setup
python -m apr_framework bugsinpy test PySnooper 1       # checkout + compile + test
python -m apr_framework localize --project PySnooper --bug 1 --metric ochiai --top-n 10
python -m apr_framework repair --project PySnooper --bug 1 --budget 20 --top-n 3 --skip-localize
```

### Key design decisions

**AST-based vs text-based mutations.**
Mutations are performed on the Python AST using `ast.NodeTransformer` subclasses and `ast.unparse()` (Python 3.9+) to reconstruct source text. The advantage is syntactic validity — every generated variant parses correctly. The trade-off is that `ast.unparse()` reformats the entire file (normalises whitespace, removes redundant parentheses), so the unified diff includes cosmetic changes beyond the actual mutation. The `patched_source` stored in `PatchCandidate.metadata` is written directly to avoid re-parsing.

**Line-to-AST-node mapping.**
Every operator checks `node.lineno <= target_line <= node.end_lineno` before mutating. This maps the SBFL/MBFL statement-level line number to the precise AST sub-tree covering that line, avoiding mutations on unrelated parts of the file.

**Cost control: budget, stop-on-first, timeout.**
`--budget` caps the total number of patch validations — each `adapter.run_tests()`
call counts as one. Generation (AST mutation) is free; validation (test execution)
is expensive. `--stop-on-first` halts as soon as a plausible patch is found.
`--timeout` is a *real* per-test-run wall-clock limit: it threads down to the
Docker `exec` call, and a timed-out run is treated as a failed (non-plausible)
candidate (exit code 124) instead of hanging the loop.

**Fault-localization family is selectable.**
`--fl-family sbfl|mbfl|hybrid` chooses which Assignment-2 localizer ranks the repair
targets (SBFL via `--localization-metric`, MBFL via `--mbfl-metric`/`--mutation-budget`/`--seed`,
or a weighted `HybridFaultLocalizer` via `--sbfl-weight`/`--mbfl-weight`).

**No changes to `RepairAlgorithm` ABC.**
`TemplateRepairAlgorithm` implements `generate_patches(bug, checkout)` (generate candidates without testing) and `validate_patch(bug, checkout, patch)` (apply + test + revert one candidate) from the existing ABC without modification. An additional non-ABC convenience method `repair(bug, checkout)` orchestrates the full budget loop. As of Task 2 the CLI drives the pipeline through `RepairEvaluationRunner` instead (see the Task 2 section); both share the single loop in `run_validation_loop`.

### Output

The command creates the next `runs/run_NNN/` directory and writes:

- `config.json` — all configuration parameters
- `repair_results.json` — per-candidate validation outcomes (valid unified diffs,
  test counts incl. `test_return_code`) and the plausible-patch list
- `execution.log` — timestamped step log
- `patches/<patch_id>.diff` and `patches/<patch_id>.patched.py` — written for each
  **plausible** patch so the fix is recoverable outside the JSON

### Known limitations

- `ast.unparse()` reformats entire files, so diffs include cosmetic whitespace changes. The patched file is identical in behaviour but may differ in style.
- Multi-line expressions split across lines are still targeted by the operator at the opening line; operators at the target line may produce no variants if the key AST node starts on a different line.
- Decorators, f-strings with complex expressions, and type-annotated assignments may be reformatted in unexpected ways by `ast.unparse()`.
- Only projects whose `run_test.sh` invokes pytest directly are supported (same restriction as the `localize` command).
- Requires Python 3.9+ inside the framework container (for `ast.unparse()`).

## Patch validation pipeline (Assignment 3 — Task 2)

Task 2 turns repair into a proper **patch-validation pipeline** with two levels of
judgment and a set of tracked metrics, all surfaced in the structured JSON output.

### Two levels of judgment

- **Plausible** — both halves of the spec definition are enforced
  ([`repair/template/validator.py`](src/apr_framework/repair/template/validator.py)):
  1. *the failing test now passes* — the bug's trigger test command exits cleanly
     with zero failures/errors and ≥1 passing test (the return-code and
     passed-count guards also reject patches that break import/collection); **and**
  2. *no previously passing test is broken* — a regression run of the bug's whole
     `test_file` introduces no new failures
     ([`repair/regression.py`](src/apr_framework/repair/regression.py)).
- **Correct** — a *plausible* patch that also matches the developer fix
  (BugsInPy ground truth) at the **diff level**. Implemented in
  [`repair/correctness.py`](src/apr_framework/repair/correctness.py).

#### Regression check (the "no previously passing test broken" half)

BugsInPy's `run_test.sh` usually contains only the single bug-triggering test, so
running it alone cannot detect a patch that fixes the trigger but breaks something
else. To enforce the second half of plausibility, the framework:

1. once per repair run, runs the bug's whole regression suite (the `test_file` from
   `bugsinpy_bug.info`, broadened from the trigger command) on the **unpatched**
   checkout and records the **baseline failing set**;
2. for a candidate that already passes the trigger, runs the same suite **with the
   patch** and records its failing set;
3. accepts the patch only if its failing set is a **subset** of the baseline — i.e.
   it introduces no new failure.

Comparing failing **sets** (not counts) is what makes this correct: a patch that
fixes the trigger but breaks a different, previously passing test has the same
failure *count* as the baseline but a non-subset failing *set*, so it is rejected.
The baseline run is established once and reused for every candidate; the same
prepared environment is reused by temporarily swapping the checkout's
`bugsinpy_run_test.sh` (`BugsInPyAdapter.run_tests(..., command=...)`). The check is
on by default and can be skipped for speed with `--no-regression-check`, in which
case plausibility falls back to the trigger test only.

The correctness check compares the candidate to the reference fix
(`projects/<project>/bugs/<id>/bug_patch.txt`, read via
`BugsInPyAdapter.get_reference_patch`). Because the template generator reconstructs
source with `ast.unparse` (which reformats whole files), a raw textual diff would
never match. So we build a **reformatting-neutral minimal diff** — both the original
and the patched source are round-tripped through `ast.unparse`, so cosmetic noise
cancels out — then reduce each side (candidate and reference) to its set of
whitespace-normalized added/removed lines and require them to be equal for the
touched file. This is a deliberately strict, purely syntactic check.

### Tracked metrics

Every repair run records these in `repair_results.json` under a `"metrics"` block
(and the headline counts at the top level):

| Metric | Meaning |
|---|---|
| `total_candidates_generated` | candidate patches produced before budget capping |
| `candidates_validated` | candidates actually run against the test suite |
| `plausible_count` | candidates whose patched program passed all tests |
| `correct_count` | plausible candidates that match the developer fix |
| `time_to_first_plausible_seconds` | wall-clock to the first plausible patch (`null` if none) |
| `total_wall_clock_seconds` | wall-clock for the whole repair run |

Each entry in `all_results` / `plausible_patches` also carries an `is_correct` flag.

### Architecture: `RepairEvaluationRunner`

The pipeline is implemented as a dedicated
[`RepairEvaluationRunner`](src/apr_framework/evaluation/repair_runner.py) that
implements the Assignment-1 `EvaluationRunner` ABC. It drives the shared
generate-and-validate loop ([`repair/run_loop.py`](src/apr_framework/repair/run_loop.py)),
runs the correctness check on plausible patches, assembles the metrics
(`RepairRunMetrics` in `core/models.py`), and writes all run artifacts.

> **Interface note (API decision).** The budget/early-stop validation loop was
> extracted from `TemplateRepairAlgorithm.repair()` into the standalone
> `run_validation_loop`, which uses **only** the `RepairAlgorithm` ABC methods
> (`generate_patches` / `validate_patch`). Both the algorithm's convenience
> `repair()` and the runner call it, so there is a single loop implementation and a
> future LLM repair backend works with the runner unchanged. `RepairStatus.CORRECT`
> (already defined in Assignment 1) is now actually used.

No new CLI flags are required — `python -m apr_framework repair ...` now prints and
persists the validation metrics, e.g.:

```text
Generated:     2 candidate(s)
Validated:     2 candidate(s)
Plausible:     0 patch(es)
Correct:       0 patch(es)
1st plausible: n/a
Total time:    1.0s
```

## FL-guided repair & perfect FL baseline (Assignment 3 — Task 3)

Repair quality depends heavily on the fault location it is given. To separate the
repair algorithm's strength from the localizer's, the `repair` command runs under
**two FL conditions**, selected with `--fl-mode`:

| Mode | Flag | Fault location source |
|---|---|---|
| **Automated FL** | `--fl-mode auto` (default) | the Assignment-2 localizer chosen by `--fl-family {sbfl,mbfl,hybrid}` |
| **Perfect FL** | `--fl-mode perfect` | the BugsInPy developer fix (`bug_patch.txt`) — the *oracle* fault location, no localizer runs |

```bash
# Automated FL (e.g. SBFL/Ochiai) drives the repair targets:
python -m apr_framework repair --project black --bug 1 --fl-mode auto --fl-family sbfl

# Perfect FL (oracle): repair targets are the exact lines the developer changed.
python -m apr_framework repair --project black --bug 1 --fl-mode perfect
```

**How perfect FL works.** `PerfectFaultLocalizer`
(`src/apr_framework/localization/perfect.py`) implements the same `FaultLocalizer`
interface as the FauxPy localizers, so it is a drop-in replacement. Instead of
analysing the program, it reads the developer fix via
`BugsInPyAdapter.get_reference_patch` and parses the unified diff's **buggy-side**
line numbers (`derive_oracle_locations`): each hunk header `@@ -old_start,… @@`
anchors a counter that walks the hunk body, so every `-` (changed/removed) line
becomes a ranked oracle location, and pure insertions are anchored to their
insertion point. The resulting `LocalizationResult` (`backend="perfect-fl"`) flows
into the *unchanged* repair/validation pipeline — perfect FL is just a different
*source* of suspicious locations.

For black#1, perfect FL yields exactly the three developer-fix lines:

```text
rank 1: black.py:621   rank 2: black.py:636   rank 3: black.py:646
```

The selected mode is recorded in the result files: `config.json` and each bug's
`config` block in `repair_results.json` carry `fl_mode` (`auto`/`perfect`) and
`fl_backend` (the FL family, or `oracle`), so Task-5 comparisons can group runs by
mode. `--fl-mode perfect` ignores `--fl-family` and `--skip-localize` (no FL is run),
and raises a clear error if the bug has no `bug_patch.txt`.

> Note: perfect FL is an *upper bound on localization*, not on operator reach — a bug
> whose fix is out of the mutation operators' reach (e.g. black#1's `try/except`
> wrapper) still yields `correct=0` even with perfect locations. See the design notes
> in [`docs/assignment3/assignment3_task3_implementation.md`](docs/assignment3/assignment3_task3_implementation.md).

## Patch ranking (Assignment 3 — Task 4)

> A detailed write-up of design decisions and refactoring pointers lives in
> [`docs/assignment3/assignment3_task4_implementation.md`](docs/assignment3/assignment3_task4_implementation.md).

When a repair run produces more than one plausible patch, the order in which
patches are shown to a developer matters. Task 4 adds a **patch ranker** that
reorders plausible patches by a composite score before they appear in the output,
while keeping the original generation-order list as a baseline so the two orderings
can be compared.

### Ranking formula

```
ranking_score = w1 * suspiciousness + w2 * patch_simplicity + w3 * operator_priority
```

All three components are normalised to `[0, 1]` before weighting. Higher score means
the patch is surfaced first.

| Component | Source | Rationale |
|---|---|---|
| `suspiciousness` | FL score of the targeted line (`patch.metadata["suspiciousness_score"]`), normalised by the max across the plausible batch | The most evidence-based signal — comes from running the actual tests |
| `patch_simplicity` | `1 − (changed_lines / max_changed_lines)` — a two-line template change scores higher than a multi-line one | Smaller patches overfit less; simpler is more trustworthy |
| `operator_priority` | Fixed tier per operator key (`obo`=1.0, `comp`=0.9, `bool`=0.7, `negate`=0.6, `arith`=0.5, `return`=0.4) | Off-by-one and comparison bugs are the most common single-statement Python fix patterns |

Default weights: **w1 = 0.6, w2 = 0.25, w3 = 0.15**. These are normalised internally,
so only relative magnitudes matter — `--ranker-weights 6,2.5,1.5` is identical to
the defaults.

### CLI

```bash
# Default: no ranking — generation order, identical to pre-Task-4 behavior
python -m apr_framework repair --project black --bug 1

# Opt in to ranking with default weights (0.6 / 0.25 / 0.15)
python -m apr_framework repair --project black --bug 1 --ranker weighted

# Custom weights
python -m apr_framework repair --project black --bug 1 \
    --ranker weighted --ranker-weights 0.7,0.2,0.1
```

When a ranker is active, the CLI summary prints an extra line:

```text
Rank of 1st correct (ranked): 2
```

### Output

`repair_results.json` always contains `plausible_patches` in generation order.
When a ranker is active, it also contains `ranked_plausible_patches` — the same
patches reordered, each annotated with `rank_position` and per-patch
`ranking_score` / `ranking_score_components` inside `metadata`.
`rank_of_first_correct` (1-indexed) appears at both the top level and inside the
`metrics` block, so Task-5 comparison scripts can read it directly.

### Architecture

The ranker is a fully optional component. `RepairEvaluationRunner` accepts
`ranker: PatchRanker | None = None` in its constructor. When `None`, the pipeline
is identical to pre-Task-4 behavior. The `PatchRanker` ABC lives in
`repair/ranking/base.py`; `WeightedCompositeRanker` is the single current
implementation. `create_ranker("weighted", ...)` is the factory entry point for
adding more strategies later.

---

## Included evaluation artifact

- This repository includes an example completed evaluation run at
`runs/run_004`.

- Configuration:

```text
runner: dummy-evaluation-runner
repair: dummy-repair
benchmark: bugsinpy
seed: 123
bugs: black 1, black 3, black 23
```

Result summary:

| Bug | Dummy choice | Baseline | Final | Status |
| --- | --- | --- | --- | --- |
| `black 1` | ground-truth patch | 0 passing, 1 failing | 1 passing, 0 failing | `correct` |
| `black 3` | original unchanged | 0 passing, 1 failing | 0 passing, 1 failing | `no_patch` |
| `black 23` | ground-truth patch | 0 passing, 1 failing | 1 passing, 0 failing | `correct` |

The result demonstrates both branches required by the assignment: successful
ground-truth repair and unchanged/no-patch behavior.



## Troubleshooting

- If Docker Compose cannot infer the host repository path, set it explicitly:

```bash
export APR_HOST_PROJECT_ROOT="$(pwd)"
```

- If the framework runs inside Docker and `APR_HOST_PROJECT_ROOT` is missing,
BugsInPy setup will fail because the sibling executor container cannot mount the
same repository files.

- If the executor container was created with stale mounts, remove it and run setup
again:

```bash
docker rm -f apr-bugsinpy-executor
python -m apr_framework bugsinpy setup
```
- For windows machines Change the end of the line sequence: CRLF -> LF 
## Summary

| Content | Implementation |
| --- | --- |
| Benchmark interface | `BenchmarkAdapter` |
| Fault localization interface | `FaultLocalizer` |
| Repair interface | `RepairAlgorithm` |
| Evaluation interface | `EvaluationRunner` |
| Report interface | `ReportGenerator` |
| BugsInPy list projects/bugs | `bugsinpy list-projects`, `bugsinpy list-bugs` |
| BugsInPy checkout | `bugsinpy checkout` |
| BugsInPy prepare environment | Safe compilation via `bugsinpy-safe-compile` and internal evaluation setup |
| BugsInPy run tests | `bugsinpy test` |
| Structured test results | `TestRunResult` with counts and raw output |
| FauxPy localization CLI | `localize --backend fauxpy --project <project> --bug <id>` |
| FauxPy metric selection | `localize --metric ochiai`, `localize --metric jaccard` |
| Hybrid localization | `localize --family hybrid --sbfl-metric ochiai --mbfl-metric metallaxis` |
| FauxPy granularity selection | `localize --granularity statement` and `localize --granularity function` |
| FauxPy output parser | `parse_fauxpy_output` parses all metrics or one selected metric |
| FauxPy result metadata | `LocalizationResult.metadata["all_metrics"]` stores every parsed metric table |
| CLI entry point | `python -m apr_framework` and `apr-framework` script |
| Dummy repair component | `DummyRepairAlgorithm` |
| Evaluation output handling | `runs/run_xxx/config.json`, `results.json`, `execution.log` , `*.zip`|
| Patch ranking | `WeightedCompositeRanker` via `--ranker weighted` (`--ranker-weights` to override) |
| Rank of first correct patch | `rank_of_first_correct` in `repair_results.json` metrics block |


## Starting the application in clean ubuntu 24.04 Container 

```bash
docker run -it --rm \
  -v "$(pwd)":/repo -w /repo \
  -v /var/run/docker.sock:/var/run/docker.sock \
  ubuntu:24.04 bash
```

```bash
apt-get update && apt-get install -y docker.io docker-compose-v2
```

```bash
export APR_HOST_PROJECT_ROOT=/path/to/project

docker compose build
docker compose run --rm apr-framework
```


```bash
# One-time: clone BugsInPy, build apr-bugsinpy:local, start the executor
python -m apr_framework bugsinpy setup

# Sanity checks
python -m apr_framework list-benchmarks
python -m apr_framework bugsinpy list-projects
python -m apr_framework bugsinpy list-bugs black

# Run a bug end-to-end
python -m apr_framework bugsinpy checkout black 1
python -m apr_framework bugsinpy test black 1

# Dummy repair evaluation (writes runs/run_xxx/)
python -m apr_framework bugsinpy evaluate-dummy --seed 123
````

---

## 2 - Commands 

```bash
docker compose down --remove-orphans
docker rm -f apr-bugsinpy-executor 2>/dev/null || true
docker rmi apr-framework:local apr-bugsinpy:local 2>/dev/null || true

docker compose build --no-cache
docker compose run --rm repair-framework bash
```

```bash
python -m apr_framework bugsinpy setup
python -m apr_framework bugsinpy checkout black 1
python -m apr_framework bugsinpy compile black 1

python -m apr_framework localize \
  --backend fauxpy \
  --project black \
  --bug 1 \
  --src . \
  --metric ochiai \
  --top-n 10 \
  --show-raw-output
```
