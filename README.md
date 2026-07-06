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
- **Custom SBFL metric extensions** (patched into FauxPy 0.7.0 at runtime):
  - **Jaccard** — set-intersection scoring: `ef / (ef + ep + fn)`
  - **WSBI (Weighted SBI)** — novel custom metric: `ef / (ef + alpha × ep)` with configurable `alpha` (default `0.5`). Reduces to plain SBI at `alpha=1`; smaller alpha makes the metric more aggressive by discounting passing-test coverage
- **Hybrid SBFL+MBFL localizer** — min-max normalises and combines scores from both families with configurable weights; locations found by both backends receive a tiebreak bonus
- **MBFL random-budget extension** — caps expensive mutant validation at `--budget N` mutants using random selection, making MBFL practical on large projects
- **`evaluate-localization` command** — runs all 8 techniques (5 SBFL, 2 MBFL, 1 Hybrid) on a configurable set of BugsInPy bugs, ranks the ground-truth faulty line for each, and writes `experiment_results/results.json` and `experiment_results/README.md`
- **Template-based repair backend** (`--technique template`) — AST mutation operators driven by FL, with patch ranking and an evaluation matrix (Assignment 3)
- **LLM-based repair backend** (`--technique llm`) — FL-guided prompting against GPT@RUB, with context enrichment and few-shot examples (Assignment 4 — Tasks 1–2) and an **iterative test-failure feedback loop** (`--iterative`) that revises failed patches across a multi-turn conversation, feeding each failure's traceback back to the model (Assignment 4 — Task 3)
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
Jaccard, WSBI, and other emitted tables available for later repair or reporting
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
pytest directly. The examples below use `black 1`, whose BugsInPy test script
is pytest-based.

- Prepare the bug first:

```bash
python -m apr_framework bugsinpy setup
python -m apr_framework bugsinpy checkout black 1
python -m apr_framework bugsinpy compile black 1
```

- Run localization with the default FauxPy backend:

```bash
python -m apr_framework localize --project black --bug 1
```

- The backend flag is available too. At the moment, `fauxpy` is the only
implemented localization backend:

```bash
python -m apr_framework localize --backend fauxpy --project black --bug 1
```

- Choose the source root when automatic inference is not enough:

```bash
python -m apr_framework localize --project black --bug 1 --src black or .
```

- Select the metric used for the primary ranking:

```bash
python -m apr_framework localize --project black --bug 1 --metric ochiai
```

Jaccard and WSBI are available for SBFL runs through the framework's FauxPy 0.7.0
patch, which is applied inside the prepared checkout environment before localization:

```bash
python -m apr_framework localize --project black --bug 1 --metric jaccard
python -m apr_framework localize --project black --bug 1 --metric wsbi
```

- Use `--wsbi-alpha` to control the passing-test weight (default: `0.5`):

```bash
# Default alpha=0.5: passing tests count half as much as failing tests
python -m apr_framework localize --project black --bug 1 --metric wsbi

# alpha=1.0 reduces to plain SBI (equal weight)
python -m apr_framework localize --project black --bug 1 --metric wsbi --wsbi-alpha 1.0

# alpha=0.25 further discounts passing-test coverage
python -m apr_framework localize --project black --bug 1 --metric wsbi --wsbi-alpha 0.25
```

Implementation note: FauxPy normally computes Tarantula, Ochiai, and DStar for
SBFL. The framework adds Jaccard and WSBI (a custom
weighted metric) by patching the installed FauxPy copy in the bug checkout's
virtual environment before running localization. The patch adds `MetricJaccard`
and `MetricWSBI` formulas, registers them with FauxPy's SBFL metric list,
extends FauxPy's local SQLite score table, and lets the existing output parser
select the emitted `Scores for Jaccard` or `Scores for WSBI` tables with
`--metric`.

**WSBI — Weighted SBI (custom metric):** Unlike standard SBI (`ef / (ef + ep)`),
the framework's WSBI uses a weighted denominator:

```
score = ef / (ef + alpha * ep)    where alpha ∈ (0, 1], default 0.5
```

The intuition is that a passing test covering a statement is weaker evidence
of innocence than a failing test is evidence of guilt. With `alpha = 0.5`,
passing tests count half as much as failing tests — making the metric more
sensitive to failing-test coverage while still penalizing statements that are
also covered by many passing tests. Setting `alpha = 1` recovers plain SBI;
smaller values of alpha make the metric increasingly aggressive.

- Limit the number of ranked locations printed:

```bash
python -m apr_framework localize --project black --bug 1 --metric ochiai --top-n 10
```

- Run function-level localization:

```bash
python -m apr_framework localize --project black --bug 1 --granularity function --metric ochiai --top-n 10
```

- Pass a failing test list to FauxPy:

```bash
python -m apr_framework localize --project black --bug 1 --failing_tests "tests/test_chinese.py::test_chinese"
```

- Run MBFL mode:

```bash
python -m apr_framework localize --project black --bug 1 --mbfl --granularity statement --metric metallaxis --top-n 10
```

- Limit expensive MBFL mutant validation runs with the random mutation selector:

```bash
python -m apr_framework localize --project black --bug 1 --mbfl --mutation-strategy random --budget 50 --metric metallaxis
```

  - `--budget` limits how many generated mutants are validated, which is the
    expensive part of MBFL.
  - `--seed` can be supplied to make random selection reproducible; it defaults
    to `0`.

- Run weighted hybrid SBFL + MBFL localization:

```bash
python -m apr_framework localize --project black --bug 1 --family hybrid --sbfl-metric ochiai --mbfl-metric metallaxis --sbfl-weight 0.5 --mbfl-weight 0.5 --mutation-strategy random --budget 50 --top-n 10
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





## Experiment Results (Evaluation)

The framework was evaluated on three real BugsInPy bugs: **fastapi#3**, **fastapi#6**, and **luigi#33**. All 8 techniques were compared against the ground-truth faulty line from each bug's patch. Full results are in [`experiment_results/README.md`](experiment_results/README.md).

### Output

`repair_results.json` always contains `plausible_patches` in generation order.
When a ranker is active, it also contains `ranked_plausible_patches` -> the same
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
# 3- Traditional APR

## Template-based APR repair 



### Technique overview

The `repair` command implements a **template-based APR** strategy guided by SBFL/MBFL fault localization:

1. **Where to fix** -> the top-N suspicious locations produced by `localize` (ranked by suspiciousness score) are used as repair targets.
2. **What to try** -> AST mutation operators generate syntactically valid program variants at each suspicious line.
3. **Which variants pass** -> each mutated variant is applied to the checkout worktree, the BugsInPy test suite is executed inside the executor container, and the file is restored unconditionally.

A patch is **plausible** only when the test command exits cleanly
(`return_code == 0`), reports zero failures and zero errors, **and** at least one
test actually passed. The exit-code and passed-count guards reject patches that
break test collection/import (which otherwise look like "0 failed, 0 error"). See: regression suites

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
python -m apr_framework repair --project black --bug 1

# Cap budget to 20 validations, try top 3 locations only:
python -m apr_framework repair --project black --bug 1 --budget 20 --top-n 3

# Only apply arithmetic and comparison operators:
python -m apr_framework repair --project tornado --bug 14 --operators arith,comp --fl-mode perfect

# Stop as soon as the first plausible patch is found:
python -m apr_framework repair --project black --bug 1 --stop-on-first

# Choose the fault-localization family that drives the repair targets:
python -m apr_framework repair --project black --bug 1 --fl-family mbfl --mbfl-metric metallaxis
python -m apr_framework repair --project black --bug 1 --fl-family hybrid --sbfl-weight 0.5 --mbfl-weight 0.5

# Skip re-running localization; load the most recent cached result:
python -m apr_framework repair --project black --bug 1 --skip-localize

# Use a different SBFL metric for localization:
python -m apr_framework repair --project black --bug 1 --localization-metric tarantula

# Full sequence from scratch:
python -m apr_framework bugsinpy setup
python -m apr_framework bugsinpy test black 1       # checkout + compile + test
python -m apr_framework localize --project black --bug 1 --metric ochiai --top-n 10
python -m apr_framework repair --project black --bug 1 --budget 20 --top-n 3 --skip-localize
```

### Key design decisions

**AST-based vs text-based mutations.**
Mutations are performed on the Python AST using `ast.NodeTransformer` subclasses and `ast.unparse()` (Python 3.9+) to reconstruct source text. The advantage is syntactic validity => every generated variant parses correctly. The trade-off is that `ast.unparse()` reformats the entire file (normalises whitespace, removes redundant parentheses), so the unified diff includes cosmetic changes beyond the actual mutation. The `patched_source` stored in `PatchCandidate.metadata` is written directly to avoid re-parsing.

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

- Only projects whose `run_test.sh` invokes pytest directly are supported (same restriction as the `localize` command).
- Requires Python 3.9+ inside the framework container (for `ast.unparse()`).

## 3.2) Patch validation pipeline 

Task 2 turns repair into a proper **patch-validation pipeline** with two levels of
judgment and a set of tracked metrics, all surfaced in the structured JSON output.

### Two levels of judgment

- **Plausible** — both halves of the spec definition are enforced
  ([`repair/template/validator.py`](src/apr_framework/repair/template/validator.py)):
  1. *the failing test now passes* -> the bug's trigger test command exits cleanly
     with zero failures/errors and >= 1 passing test (the return-code and
     passed-count guards also reject patches that break import/collection); **and**
  2. *no previously passing test is broken* — a regression run of the bug's whole
     `test_file` introduces no new failures
     ([`repair/regression.py`](src/apr_framework/repair/regression.py)).
     - ==> trigger_passed + regression_ok
- **Correct** -> a *plausible* patch that also matches the developer fix
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
never match. So we build a **reformatting-neutral minimal diff** -> both the original
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

## 3.3) - FL-guided repair & perfect FL baselinex

Repair quality depends heavily on the fault location it is given. To separate the
repair algorithm's strength from the localizer's, the `repair` command runs under
**two FL conditions**, selected with `--fl-mode`:

| Mode | Flag | Fault location source |
|---|---|---|
| **Automated FL** | `--fl-mode auto` (default) | the (modified) FauxPy localizer chosen by `--fl-family {sbfl,mbfl,hybrid}` |
| **Perfect FL** | `--fl-mode perfect` | the BugsInPy developer fix (`bug_patch.txt`) — the *oracle* fault location, no localizer runs |

```bash
# Automated FL (e.g. SBFL/Ochiai) drives the repair targets:
python -m apr_framework repair --project black --bug 1 --fl-mode auto --fl-family sbfl

# Perfect FL (oracle): repair targets are the exact lines the developer changed.
python -m apr_framework repair --project tornado --bug 14 --fl-mode perfect
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

> Note: perfect FL is an *upper bound on localization*, not on operator reach -> a bug
> whose fix is out of the mutation operators' reach (e.g. black#1's `try/except`
> wrapper) still yields `correct=0` even with perfect locations.

## 3.4) - Patch ranking   

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
| `suspiciousness` | FL score of the targeted line (`patch.metadata["suspiciousness_score"]`), min-max normalised across the plausible batch (`(score − min) / (max − min)`) | The most evidence-based signal — comes from running the actual tests |
| `patch_simplicity` | `1 − (changed_lines − min_changed_lines) / (max_changed_lines − min_changed_lines)` (min-max normalised, then inverted) — a two-line template change scores higher than a multi-line one | Smaller patches overfit less; simpler is more trustworthy |
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




## 3.5) - Evaluation and comparison

Task 5 runs the **whole repair pipeline** (fault localization → patch generation ->
validation -> ranking) across a matrix of *bugs × FL modes* and aggregates the
outcome. It adds no new repair capability -> it exercises everything Tasks 1–4 built
and reports the metrics side by side so automated FL and perfect FL can be compared
directly.

The matrix is driven by `bugsinpy evaluate-repair`. Each *(bug, FL mode)* cell is a
complete repair run executed by the existing `RepairEvaluationRunner` (so every cell
gets its own `runs/run_NNN/` with logs and patch diffs); `RepairComparisonRunner`
only orchestrates the matrix and aggregates. A localization failure in one cell
(e.g. FauxPy uninstallable for a bug's Python) is recorded as an **error cell**
rather than aborting the whole run.

### CLI

Each bug must be checked out and compiled first (the runner does not re-check-out):

```bash
# EX: Checkout and Compile on multiple bugs
for b in "tornado 14" "scrapy 2" "black 1"; do
  python -m apr_framework bugsinpy checkout $b
  python -m apr_framework bugsinpy compile  $b
done

# EX: Run the evalutation pipeline on multiple bugs
python -m apr_framework bugsinpy evaluate-repair \
    --bugs "tornado:14,scrapy:2,black:1" \
    --fl-modes "auto,perfect" \
    --fl-family sbfl --localization-metric ochiai \
    --ranker weighted \
    --output-dir experiment_results/repair
```

Every per-cell flag of the `repair` command is also accepted here (`--budget`,
`--top-n`, `--operators`, `--timeout`, `--granularity`, `--ranker-weights`, and the
MBFL/hybrid knobs).

### Reported metrics

Per cell, written to `experiment_results/repair/results.json`:

| Field | Meaning |
|---|---|
| `total_candidates_generated` | Patches the template generator produced. |
| `candidates_validated` | Patches actually run against the test suite (≤ budget). |
| `plausible_count` | Patched programs that passed the trigger test + regression check. |
| `correct_count` | Plausible patches that also match the developer fix at the diff level. |
| `time_to_first_plausible_seconds` | Wall-clock to the first plausible patch, or `null`. |
| `total_wall_clock_seconds` | Wall-clock for the whole cell. |
| `generation_rank_of_first_correct` | 1-based position of the first correct patch in **generation order** (unranked baseline). |
| `ranked_rank_of_first_correct` | 1-based position of the first correct patch after the **ranker** reorders. |

### Results

The numbers below are the real output of one `evaluate-repair` run over
`tornado:14, scrapy:2, black:1` (committed under `experiment_results/repair/`).

**Per bug:**

| Bug | FL mode | Generated | Plausible | Correct | Correct rank (gen → ranked) | Time to 1st plausible | Total | Outcome |
|---|---|---|---|---|---|---|---|---|
| tornado#14 | auto | — | — | — | — | — | — | **error** — FauxPy 0.7.0 cannot install on Python 3.7.0 (openai dependency issue) |
| tornado#14 | perfect | 6 | 1 | **1** | 1 → 1 | 0.65s | 1.14s | **correct** |
| scrapy#2 | auto | 0 | 0 | 0 | — | — | ~0s | no operator-reachable node in the SBFL top-N |
| scrapy#2 | perfect | 5 | 0 | 0 | — | — | 1.12s | 5 candidates at the oracle line, none plausible |
| black#1 | auto | 8 | 0 | 0 | — | — | 12.09s | SBFL ran; 8 candidates, none plausible |
| black#1 | perfect | 0 | 0 | 0 | — | — | 1.08s | developer fix (try/except) is out of operator reach |

**Aggregate per FL mode:**

| FL mode | Generated | Plausible | Correct | Bugs repaired |
|---|---|---|---|---|
| auto | 8 | 0 | 0 | 0 |
| perfect | 11 | 1 | 1 | 1 |

### Discussion

**Which bugs were repaired?** One: `tornado#14`, under perfect FL. Its developer fix
is `if IOLoop.current(instance=False) is None:` -> `... is not None:` -> a single
`Is`→`IsNot` swap, exactly what the `comp` operator emits. With the oracle pointing at
the fault line, the generator produces the developer fix verbatim, it passes
validation, and the diff-level check confirms correctness (patch preserved under
`run_artifacts/`). No bug was repaired under automated FL.

**Did the technique benefit from better FL?** The effect is real but **mediated by
operator reach**, and the three bugs show all three cases:

- `tornado#14` is the clearest case: perfect FL turns the fix into a single reachable
  mutation and yields a correct patch, while automated FL never even runs (FauxPy is
  uninstallable on its Python 3.7.0).
- `scrapy#2` shows better FL producing *more attempts*: perfect FL targets the
  operator-reachable oracle line and generates 5 candidates, whereas automated FL
  surfaces no reachable node in its top-N and generates 0.
- `black#1` shows the reverse: its developer fix wraps code in
  `try/except` (unreachable by any operator), so perfect FL generates 0 candidates
  while automated FL's top-N happens to include operator-reachable lines and generates
  8 -> none correct.

Observation: for the bugs whose fix restructures control flow / or the bugs who makes calls to external services the
single-operator template technique produces no plausible patch. We believe that the LLM-based repair
backend introduced in the next assignment is expected to handle this class of bug
better.

The takeaway: FL quality decides *whether the fault line is even attempted*, but the
**template operator set is the dominant bottleneck**. When the real fix is not an
operator-level edit, no FL mode can repair it.

**Did the ranker surface correct patches earlier?** On the only cell that produced a
correct patch (`tornado#14`, perfect FL), the plausible set had a single element, so
generation order and ranked order coincide (rank 1 in both). The ranker correctly
places that patch first, but *demonstrating reordering* needs ≥2 plausible patches in
one cell, which none of these bugs produced — consistent with the Task-4 limitation
that ranking only distinguishes patches when at least two are plausible.

### Limitations

- **Operator reach dominates.** The six operators only match fixes that are themselves
  single operator-level edits; most BugsInPy developer fixes add or restructure
  statements and are unreachable regardless of FL. Across the packaged benchmark,
  `tornado#14` is effectively the only pure-operator-swap fix — which is why it is the
  single repaired bug.
- **Automated FL is environment-sensitive.** FauxPy 0.7.0 depends (transitively via
  `pyllmut` -> `openai`) on Python ≥ 3.7.1, so it cannot install for bugs pinned to
  Python 3.7.0. Such cells are reported honestly as error cells; perfect FL has no such
  dependency and always runs.
- **Correctness is strict and syntactic.** It is a diff-level match of the normalized
  added/removed lines against the single-file developer fix;

### Artifacts

```
experiment_results/repair/
  results.json                 # machine-readable matrix (one row per cell)
  README.md                    # generated per-bug tables + aggregate
  run_artifacts/run_NNN/       # per-cell logs, config, repair_results.json, patch diffs
```
---

## LLM-Based Repair (Assignment 4 — Task 1)

This section documents the LLM-based repair backend introduced in Assignment 4.
It conforms to the same `RepairAlgorithm` ABC as the template backend and slots
into the existing `RepairEvaluationRunner` pipeline without any changes.

### How it works

1. **Fault location** — the top-N suspicious locations from the FL step (automated or perfect) are used as repair targets, identical to template repair.
2. **Prompt construction** — for each location the algorithm extracts the enclosing function from the source file via `ast.parse`, then builds a structured prompt asking the LLM to return a corrected version of that function.
3. **Patch extraction** — the LLM response is scanned for a fenced code block (` ```python … ``` `, falling back to a generic ` ``` … ``` ` block), the extracted code is validated for Python syntax, and a `difflib` unified diff is generated against the original file.
4. **Validation** — each diff is applied to the checkout with `patch -p0`, the test suite is executed inside the executor container, and the file is restored unconditionally — identical to the template repair validation flow.

### Prompt design

The prompt is structured as a two-message OpenAI-style conversation.

**System message** (fixed, not shown to the model as user turn):

```
You are an automated program repair tool. Your task is to fix a bug in a Python program.
You will be given the buggy code region and the fault location identified by a fault
localization tool. You may also be given the failing test and the traceback it produces
on the current code; when present, use them to infer the behaviour the fix must satisfy
and the concrete failure to eliminate. Return ONLY the corrected version of the provided function inside a
Python fenced code block (```python ... ```). Do not include any explanation, commentary,
or code outside the fenced block. Do not change the function signature.
```

> The last two sentences of the "may also be given …" clause are exercised by the Task 2
> context-enrichment step below; without it the prompt behaves exactly as in Task 1.

**User message** (assembled per location, three sections):

```
## Fault Location
File: <location.file_path>
Suspicious line: <location.line> (rank <location.rank>, score <score:.4f>)

## Buggy Code (lines <start>–<end>)
```python
<start>      def foo(x, y):
<start+1>        …
<N>  -->         <suspicious line, marked with -->
…
```

## Task
Fix the bug at line <location.line>. Return the corrected function in a Python fenced
code block. Keep the fix minimal — change as few lines as necessary.
```

**Design rationale:**

| Choice | Reason |
|---|---|
| Return the full corrected function (not a diff) | Raw diffs generated by LLMs are frequently malformed; requesting a complete function lets us generate the diff ourselves via `difflib`, which is always well-formed. |
| Line-number prefix on every line | Anchors the model to the exact line number from the fault location, reducing the risk of off-by-one confusion. |
| `-->` marker on the suspicious line | Directs the model's attention without removing the surrounding context it needs to reason about the fix. |
| Minimal-edit instruction | Reduces unnecessary refactoring; smaller patches are easier to review and less likely to introduce new bugs. |
| Structured `##`-headed sections | Clear separation makes it easy to extend the prompt in Task 2 (context enrichment) by inserting new sections without changing the existing ones. |

The optional kwargs `failing_test_source`, `error_traceback`, and `fl_score_annotation`
are present in `build_repair_prompt`'s signature as enrichment slots. In Task 1 they are
accepted but unused, so the rendered prompt contains only the three sections above.
`failing_test_source` and `error_traceback` are wired up in Task 2 (see the next section);
`fl_score_annotation` remains reserved.

### Example invocations

```bash
# LLM repair with perfect FL (oracle locations):
python -m apr_framework repair \
    --project black \
    --bug 1 \
    --technique llm \
    --model codestral-22b \
    --fl-mode perfect \
    --max-candidates 3 \
    --temperature 0.8

# LLM repair with automated SBFL localization:
python -m apr_framework repair \
    --project black \
    --bug 1 \
    --technique llm \
    --model codestral-22b \
    --fl-mode auto \
    --fl-family sbfl \
    --localization-metric ochiai \
    --top-n 3 \
    --max-candidates 5 \
    --budget 30

# Use a custom API endpoint and API key variable:
python -m apr_framework repair \
    --project black \
    --bug 1 \
    --technique llm \
    --model codestral-22b \
    --llm-base-url https://my.endpoint/api \
    --llm-api-key-env MY_LLM_KEY \
    --fl-mode perfect
```

**Required environment variable** (default name, overridable with `--llm-api-key-env`):

```bash
export GPT_AT_RUB_API_KEY="<your-key>"
```

### CLI flags (LLM-specific)

| Flag | Default | Description |
|---|---|---|
| `--technique llm` | — | Selects the LLM backend (use alongside all existing FL/budget flags) |
| `--model` | `codestral-22b` | Model name sent to the API |
| `--temperature` | `0.8` | Sampling temperature in `[0.0, 2.0]` |
| `--max-candidates` | `5` | LLM calls per suspicious location (total candidates ≤ `top-n × max-candidates`) |
| `--llm-provider` | `openai-compatible` | Client implementation; only `openai-compatible` currently |
| `--llm-base-url` | *(GPT@RUB endpoint)* | Override the API endpoint URL |
| `--llm-api-key-env` | `GPT_AT_RUB_API_KEY` | Environment variable name holding the API key |
| `--context-enrichment` / `--no-context-enrichment` | *enabled* | Include the failing test's source + traceback in each prompt (Task 2); disable for the Task-1 prompt |
| `--few-shot N` | `0` | Prepend N `(buggy → fixed)` example pairs from other bugs of the same project (Task 2); `0` disables. Independent of `--context-enrichment` |

All existing flags (`--fl-mode`, `--fl-family`, `--budget`, `--top-n`, `--timeout`,
`--stop-on-first`, `--no-regression-check`, `--ranker`, etc.) work identically for
both `--technique template` and `--technique llm`.

### Architecture

```
repair/llm/
    config.py          # LLMRepairConfig dataclass (model, temperature, budget, …)
    client.py          # LLMClient ABC + OpenAICompatibleClient (GPT@RUB / OpenAI)
    prompt_builder.py  # extract_function_source + build_repair_prompt
    context_enricher.py# failing-test source + traceback gathering (Task 2)
    few_shot.py        # (buggy → fixed) example pairs from sibling bugs (Task 2)
    patch_extractor.py # extract_patch_from_llm_response → unified diff or None
    algorithm.py       # LLMRepairAlgorithm (implements RepairAlgorithm ABC)
repair/
    patch_applier.py   # apply_patch_and_validate — shared apply/test/restore helper
```

**Key design decisions:**

**Provider-agnostic `LLMClient` ABC.** All provider-specific HTTP calls live in
`OpenAICompatibleClient`. Adding a new LLM provider requires only a new `LLMClient`
subclass — `LLMRepairAlgorithm` is unchanged.

**`PromptBuilder` is a separate module.** `generate_patches` calls it; it does not
inline prompt logic. This keeps the algorithm readable and makes Task 2 context
enrichment a matter of extending `prompt_builder.py`, not editing the algorithm.

**Shared `apply_patch_and_validate` helper.** The try/finally restoration guarantee and
the two-half plausibility check (trigger test + regression) are shared infrastructure in
`repair/patch_applier.py`. Template repair is left unchanged (it predates this helper);
new backends use the helper rather than duplicating the logic. The caller provides
backend-specific `apply_fn` and `restore_fn` callables.

**`patch -p0` for diff application.** Diffs are generated by `difflib.unified_diff` with
the absolute source path as `fromfile`/`tofile`. `patch -p0` applies them without any
path-component stripping, which is correct for absolute paths. (`-p1` would strip the
leading `/` and fail to locate the file.)

**Injected `LLMClient`.** The client is passed into `LLMRepairAlgorithm.__init__` rather
than constructed internally, so tests can substitute a stub without touching the network.

**`repair()` delegates to `run_validation_loop`.** Identical pattern to
`TemplateRepairAlgorithm.repair()`. When Task 3 (iterative repair) is implemented, only
`repair()` needs to be overridden; `generate_patches` and `validate_patch` remain
untouched.

---

## Context enrichment (Assignment 4 — Task 2)

### Why this was needed

The Task-1 prompt shows the model only the **buggy function** and a `-->` marker on the
suspicious line. It never states *what is actually failing*. For any bug whose fix cannot
be inferred from otherwise clean-looking code, this leaves the model guessing.

This is not hypothetical — it is exactly what we observed on **black#1** under perfect FL.
The developer fix wraps a call in a `try/except OSError` and falls back to a mono-process
executor:

```python
try:
    executor = ProcessPoolExecutor(max_workers=worker_count)
except OSError:
    executor = None          # system has no multiprocessing (e.g. AWS Lambda)
```

The failing test (`test_works_in_mono_process_only_environment`) forces that `OSError`. But
nothing in the buggy function *looks* wrong without knowing the failure mode, so across a
full run of 15 candidates the model produced only cosmetic edits (`os.cpu_count() or 1`,
making a parameter `Optional`) — **not one** candidate contained the `except OSError`
fallback. The pipeline worked end-to-end; the model simply could not know what to fix.

The root cause was diagnostic, not mechanical: **the prompt withheld the failure**. Task 2
closes that gap by making the failure observable to the model.

### What was added

Two new prompt sections, rendered only when their data is available:

| Section | Content | Why it helps |
|---|---|---|
| `## Failing Test` | Source of the bug-triggering test function | Shows the *behaviour the fix must satisfy* — the contract the model is repairing against |
| `## Failure Traceback` | The traceback that test produces on the **unpatched** checkout | Shows the *concrete failure mode* (e.g. `OSError` from `ProcessPoolExecutor`) so the model targets the real defect |

Both are gathered by a new isolated module,
[`repair/llm/context_enricher.py`](src/apr_framework/repair/llm/context_enricher.py):

- **Failing-test source** — the bug's `run_test.sh` is converted to a pytest node id via the
  existing `load_pytest_targets`; the test file and method name are parsed from it, and the
  method's source is AST-extracted from the worktree.
- **Failure traceback** — the trigger test is run **once** on the unpatched checkout (cached
  for the whole repair run, like the regression baseline), and the last `Traceback …` block
  is extracted from its output (capped in length).

Gathering happens once per run in `LLMRepairAlgorithm._failing_test_context_for`, mirroring
the existing lazy `_regression_context` pattern, and the two fields are forwarded into
`build_repair_prompt`.

### Why the change is safe (isolation)

Context enrichment was deliberately built so it cannot regress the Task-1 path or the
template backend:

- **Best-effort, degrade to `None`.** Every gather step (missing `run_test.sh`, unsupported
  test runner, absent traceback) logs a warning and returns `None` rather than aborting the
  repair.
- **Byte-identical when off.** `build_repair_prompt` appends a section *only* when its value
  is non-`None`. With `--no-context-enrichment` (or when nothing could be gathered), the
  rendered prompt is identical to Task 1.
- **No shared code touched.** The enricher runs its own trigger-test call instead of
  extending the shared `repair/regression.py`, so the template backend is completely
  unaffected.

### CLI

Enrichment is **on by default** (it is the intended improvement) and can be turned off for
A/B comparison:

```bash
# Default: enriched prompt (failing test + traceback included)
python -m apr_framework repair --project black --bug 1 --technique llm --fl-mode perfect

# Original Task-1 prompt (buggy function only) — for comparison
python -m apr_framework repair --project black --bug 1 --technique llm --fl-mode perfect \
    --no-context-enrichment
```

The effective setting is recorded as `context_enrichment` in each run's `config.json`.

> **Cost note.** Enrichment adds exactly **one** extra test run per repair run (the trigger
> traceback capture), not one per candidate — negligible next to validating N candidates.

### Second strategy — few-shot fix examples (`--few-shot N`)

Task 2 asks for **at least two** context-enrichment strategies, toggleable independently.
The second one is the *fix examples* strategy: prepend `N` real `(buggy → fixed)` pairs
from **other bugs of the same project** so the model sees how bugs in this codebase are
typically fixed (style, size, output format) before tackling the current one.

It is controlled by its own flag, **independently** of `--context-enrichment`:

```bash
# Few-shot only (2 sibling examples), no failing-test/traceback enrichment:
python -m apr_framework repair --project black --bug 1 --technique llm --fl-mode perfect \
    --few-shot 2 --no-context-enrichment

# Both strategies together:
python -m apr_framework repair --project black --bug 1 --technique llm --fl-mode perfect \
    --few-shot 2
```

`--few-shot 0` (the default) disables it. The value is recorded as `few_shot_count` in
each run's `config.json`.

**How the examples are built** ([`repair/llm/few_shot.py`](src/apr_framework/repair/llm/few_shot.py)):

- The project's other bug ids are listed and taken in **ascending order** (deterministic,
  reproducible), with the bug under repair **excluded** so no answer leaks into the prompt.
- Each candidate's developer fix is read **offline** from its `bugs/<id>/bug_patch.txt` via
  `get_reference_patch` — **no checkout, compile, or test run**, so this strategy is free of
  side effects and adds no execution cost.
- The `(buggy, fixed)` snippets are reconstructed from the diff hunks (context+`-` lines →
  buggy, context+`+` lines → fixed) and rendered as a prepended `## Reference Fixes From
  This Project` section.
- Examples whose diff changes more than 40 lines are **skipped** (poor, prompt-bloating
  examples), and long snippets are trimmed, so the loop keeps scanning until it has `N`
  usable examples. If none can be built it degrades to no section (prompt unchanged).

Like the failing-test context, the examples are built **once per run** and cached
(`LLMRepairAlgorithm._few_shot_examples_for`). The two strategies are fully independent:
`--few-shot` and `--context-enrichment` can each be on or off in any combination.

> Example: `--few-shot 2` on black#1 selects black#3 and black#4 — it **skips black#2**
> because that fix exceeds the 40-line example cap, which is the deterministic
> skip-oversized behaviour in action.

### Inspecting the exact prompt (debugging)

To see **exactly** what is sent to the LLM (system + user message, including any
enrichment and few-shot sections), set the `APR_LLM_DEBUG_PROMPT` environment variable.
It is **off by default** and a strict no-op when unset — it never alters the messages,
the request, or the result, so it is safe to leave in place.

The following run writes every prompt to `runs/prompt_dumps/prompt_NNNN.txt`
(assumes `black 1` is already checked out/compiled and `GPT_AT_RUB_API_KEY` is exported):

```bash
APR_LLM_DEBUG_PROMPT=runs/prompt_dumps \
python -m apr_framework repair --project black --bug 1 \
  --technique llm \
  --fl-mode perfect \
  --model gpt-4.1-2025-04-14 \
  --few-shot 2 \
  --max-candidates 5 --top-n 3 --budget 100
```

Then inspect the captured prompts:

```bash
ls runs/prompt_dumps/                                              # prompt_0001.txt, ...
grep -l "Reference Fixes From This Project" runs/prompt_dumps/*.txt   # few-shot present
cat runs/prompt_dumps/prompt_0001.txt                             # the full prompt
```

To stream the prompts to the terminal instead of files, use `APR_LLM_DEBUG_PROMPT=stderr`.

> **Important — put the variable on the same line as the command.** A bare
> `APR_LLM_DEBUG_PROMPT=runs/prompt_dumps` on its own line does **not** apply to the next
> command (it is set and immediately discarded). Either prefix it inline with a trailing
> `\` as above, or `export APR_LLM_DEBUG_PROMPT=runs/prompt_dumps` first so it persists for
> the whole shell session. Verify with `echo "$APR_LLM_DEBUG_PROMPT"` (empty = not set).

| `APR_LLM_DEBUG_PROMPT` value | Effect |
|---|---|
| *(unset / empty)* | Nothing — normal behaviour |
| `1`, `stderr`, `true`, `yes` | Print each prompt to **stderr** |
| any other value | Treat it as a **directory**; write one `prompt_NNNN.txt` per LLM call |

The hook lives at the single send choke point in
[`repair/llm/client.py`](src/apr_framework/repair/llm/client.py) (`OpenAICompatibleClient._dump_prompt_if_debugging`),
so it captures the real messages for every call — enriched, few-shot, or plain. A failed
write (e.g. a bad path) is logged and ignored, never aborting the repair run.

---

## Iterative Repair with Test-Failure Feedback (Assignment 4 — Task 3)

### Why a single LLM query often isn't enough

A one-shot LLM query frequently produces a patch that is syntactically valid but still
fails the test suite — the model guessed wrong, or fixed only part of the fault. It has no
way to learn from that failure because it never sees it. Inspired by **ChatRepair**, this
task turns the single query into a *conversation*: after a patch fails validation, the
exact test-failure output is fed back to the model as the next turn, and it is asked to
revise its fix. The model can then react to the concrete failure (the assertion that
tripped, the exception raised) instead of guessing blind a second time.

### How it works

Iterative mode runs **one fresh multi-turn conversation per FL location** (symmetric with
single-shot mode, which already queries the top-N locations independently). Each location
starts from the same `[system, user]` repair prompt as Task 1/2 (all enrichment flags
still apply), then extends turn by turn:

1. Ask the model for a corrected function; extract the patch and validate it.
2. If it fails, append the model's reply **and** a structured test-failure feedback turn
   (see below), then ask again.
3. Repeat until the location's conversation ends (stop conditions below), then move on to
   the next location if the global budget allows.

**Two independent counters** govern how long the loop runs:

| Counter | Flag | Scope | Meaning |
|---|---|---|---|
| **Conversation budget** | `--max-iterations` | **Per location** | Max conversation turns (LLM calls) spent on one location before giving up on it. Format-retry turns count toward this, so a location can never loop forever. |
| **Validation budget** | `--budget` | **Global** | Max test-suite executions across the whole bug (same meaning as template and single-shot LLM repair). Decremented only when a syntactically valid patch is actually validated. |

**Interface extension — the `repair_loop` ABC method (documented change).** The assignment
sheet asks that any interface change needed to accommodate LLM-specific behavior be made
and documented. Here is why one was necessary. The real evaluation path
(`RepairEvaluationRunner`) does **not** call an algorithm's `repair()`; it called the
module-level `run_validation_loop(repair, …)` **directly**. That function generates *all*
candidates up front and then validates them one by one — a split that iterative repair
breaks by construction, because generating turn *N+1* requires knowing why turn *N*
failed. Overriding `repair()` alone would therefore have been invisible to the actual
evaluation and CLI path.

The fix is a **one-method extension of the `RepairAlgorithm` ABC**: a non-abstract
`repair_loop(bug, checkout, *, budget, stop_on_first) -> LoopOutcome`. Its default
implementation simply delegates to `run_validation_loop`, so the template backend and
non-iterative LLM runs are **byte-for-byte unchanged**. `LLMRepairAlgorithm` overrides
`repair_loop` only when `--iterative` is set; otherwise it too falls back to the default.
`RepairEvaluationRunner` now calls `repair.repair_loop(...)` instead of the module
function. `generate_patches()` and `validate_patch()` remain the untouched primitives that
every backend still implements and that both loop shapes reuse.

### Feedback message design

Every turn after the first carries the previous attempt's failure. The feedback is a
structured prompt section (built by [`repair/llm/feedback.py`](src/apr_framework/repair/llm/feedback.py)),
styled like the other `##`-headed sections so the conversation reads consistently:

```
## Previous Attempt Failed (turn 2 of 5)
Your last fix did not pass validation — passed=12, failed=1, errors=0.

Traceback:
```
Traceback (most recent call last):
  File ".../test_foo.py", line 42, in test_bar
    assert result == 3
AssertionError: assert 4 == 3
```

Please analyze this failure and provide a revised fix. Return the corrected function
in a Python fenced code block, as before.
```

The traceback is extracted from the failed run's raw pytest output by the shared
`extract_last_traceback` helper (the same one Task 2 uses for the unpatched-code
traceback). When no traceback is present the message still carries the pass/fail/error
counts. The raw output is passed in-memory from `validate_patch` to the loop via the
candidate's metadata; it is filtered out of `repair_results.json` so it never bloats the
run artifacts.

**Two failure kinds, two messages.** A patch can fail validation either because the
bug-triggering test still fails (**trigger** failure) or because the patch *fixes* the
target test but breaks a previously-passing one (**regression** failure). The plausibility
helper only returns the trigger run, which for a regression failure shows all-green — its
counts and (absent) traceback would mislead the model. `validate_patch` therefore
classifies the failure (`_classify_failure_kind`) and the feedback adapts: trigger failures
get the traceback/counts shown above; regression failures instead get an explicit note that
a previously-passing test was broken and a request to fix the bug *without* changing other
behavior. (A fuller variant that names the specific regressed tests would require plumbing
the regression run's output out of the shared validation helper — noted as follow-up work.)

### Stop conditions

A location's conversation ends as soon as **any** of these holds — matching the
assignment's Task 3 bullet list:

- **A plausible patch is found** (all tests pass, no regressions).
- **`--max-iterations` is exhausted** (conversation-turn budget for this location).
- **`--budget` is exhausted** (global test-suite execution budget).
- **The model signals it cannot improve further**, detected by two cheap, explainable
  heuristics (a documented heuristic, not a semantic judgment):
  - **Identical diff twice in a row** — the model is repeating itself and making no
    progress.
  - **Refusal phrase** — a small case-insensitive substring list (e.g. *"cannot fix"*,
    *"unable to fix"*, *"no further changes"*) matched against the response text.

Additionally, an **unparsable reply** (no fenced code block) triggers one bounded
*format-retry* turn — a short "please reply with a valid fenced code block" nudge — up to
2 consecutive times before giving up on the location, so prose-wrapped answers don't waste
the whole `--max-iterations` budget. Every early exit is logged at INFO/WARNING level with
its reason, so `runs/run_NNN/execution.log` explains why each conversation ended.

### CLI flags (Task 3)

| Flag | Default | Description |
|---|---|---|
| `--iterative` / `--no-iterative` | *disabled* | Enable the multi-turn feedback loop. Ignored when `--technique template`. |
| `--max-iterations N` | `5` | Max conversation turns per FL location before giving up on it. Only meaningful with `--iterative`. |

These compose with **all** the Task 1/2 LLM flags (`--model`, `--temperature`,
`--max-candidates`, `--context-enrichment`, `--few-shot`, `--llm-base-url`,
`--llm-api-key-env`) and all shared flags (`--fl-mode`, `--fl-family`, `--budget`,
`--top-n`, `--timeout`, `--stop-on-first`, `--no-regression-check`, `--ranker`). Both
`--iterative` and `--max-iterations` are recorded in each run's `config.json` and embedded
`repair_results.json` config, so every result file records which mode produced it.

> Note: `--max-candidates` (turns per location in single-shot mode) and `--max-iterations`
> (turns per location in iterative mode) are distinct: single-shot mode generates
> `--max-candidates` independent patches per location, while iterative mode runs up to
> `--max-iterations` *dependent* turns, each reacting to the last failure. In iterative
> runs, `--max-candidates` is not used for the conversation length.

### Example invocations

```bash
# Iterative repair with automated FL:
python -m apr_framework repair --project black --bug 1 --technique llm \
    --iterative --max-iterations 5 --fl-mode auto

# Iterative repair with perfect FL, capped test-suite budget:
python -m apr_framework repair --project black --bug 1 --technique llm \
    --iterative --max-iterations 5 --fl-mode perfect --budget 20

# Iterative combined with context enrichment and few-shot (Task 2 flags still apply):
python -m apr_framework repair --project black --bug 1 --technique llm \
    --iterative --max-iterations 5 --context-enrichment --few-shot 2
```

Patches produced in iterative mode carry an `llm-iter-<rank>-<turn>` `patch_id` (vs.
`llm-<rank>-<attempt>` for single-shot), so run artifacts and logs make the mode visually
obvious.

### Reflection — what test-failure information helps most

> **⚠️ Draft, to be revisited once Task 5's empirical evaluation runs are available.**
> The points below are grounded in the *design intent*; a firm answer requires observing
> real multi-turn iterations on actual bugs, which is the separate Task 5 evaluation.

Design expectation: the **traceback** — specifically the final exception type and message
and the failing test's assertion line — should be the highest-value piece of the feedback.
It names the concrete symptom (`AssertionError: assert 4 == 3`, an `IndexError`, a
`TypeError`) that a bare *"passed=12, failed=1"* count cannot convey, and it points the
model at the exact expected-vs-actual mismatch. The pass/fail/error **counts** are expected
to be secondary but still useful as a coarse progress signal (did the last edit fix some
tests while breaking others?). The full pytest transcript is deliberately **not** forwarded
verbatim — it is large and mostly noise; only the last traceback block (capped at 60 lines)
is included, on the hypothesis that the trailing failure is the actionable one. Whether the
model actually benefits more from the assertion line than from the counts, and whether
truncating to a single traceback loses useful cross-test signal, are the questions Task 5's
observed iterations will answer.

---

## Included evaluation artifact
| Bug | Technique | Type | Rank | Top-10 |
|---|---|---|---|---|
| fastapi#3 | SBFL-Ochiai | baseline | 8 | ✓ |
| fastapi#3 | SBFL-Tarantula | baseline | 11 | ✗ |
| fastapi#3 | SBFL-DStar | baseline | 8 | ✓ |
| fastapi#3 | SBFL-Jaccard | **extension** | 8 | ✓ |
| fastapi#3 | SBFL-WSBI | **extension** | 11 | ✗ |
| fastapi#3 | MBFL-Metallaxis | baseline | 18 | ✗ |
| fastapi#3 | MBFL-Metallaxis-Random | **extension** | 11 | ✗ |
| fastapi#3 | Hybrid SBFL+MBFL | **extension** | 11 | ✗ |
| fastapi#6 | SBFL-Ochiai | baseline | 82 | ✗ |
| fastapi#6 | SBFL-DStar | baseline | 82 | ✗ |
| fastapi#6 | SBFL-Jaccard | **extension** | 82 | ✗ |
| fastapi#6 | MBFL-Metallaxis | baseline | 6 | ✓ |
| fastapi#6 | MBFL-Metallaxis-Random | **extension** | — | ✗ |
| fastapi#6 | **Hybrid SBFL+MBFL** | **extension** | **3** | **✓ (top-5)** |
| luigi#33 | SBFL-Ochiai | baseline | 11 | ✗ |
| luigi#33 | SBFL-Tarantula | baseline | 191 | ✗ |
| luigi#33 | SBFL-DStar | baseline | 11 | ✗ |
| luigi#33 | SBFL-Jaccard | **extension** | 11 | ✗ |
| luigi#33 | SBFL-WSBI | **extension** | 191 | ✗ |
| luigi#33 | MBFL-Metallaxis | baseline | — | ✗ |
| luigi#33 | Hybrid SBFL+MBFL | **extension** | 26 | ✗ |

### Key findings

**Jaccard (extension) matches the best SBFL baseline on fastapi#3.** Ochiai, D*, and Jaccard all rank the faulty line at position 8. Tarantula and WSBI fall to rank 11, showing that formula choice matters.

**Hybrid reaches rank 3 on fastapi#6** — the only technique to enter the top 5. SBFL alone is stuck at rank 82 for this bug; MBFL alone reaches rank 6. Combining both via the weighted hybrid further improves to rank 3, demonstrating the value of the extension.

**WSBI degenerates on luigi#33** (rank 191, same as Tarantula). Luigi#33 has no passing tests — when `ep = 0`, WSBI and SBI both assign score `1.0` to every executed line with no differentiation. Ochiai (`sqrt(ef/F)`) preserves a gradient across the four failing tests and correctly ranks the faulty line at 11. This is an honest limitation of the WSBI metric and motivates future work on handling the zero-passing-test edge case.







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

- **GPT@RUB API is only reachable from within the RUB network/VPN.** If `--technique llm`
  fails with a connection error/timeout, connect to the RUB VPN before running the command
  (the container inherits the host's network path). Generate the access token in your
  GPT@RUB account settings and export it via `--llm-api-key-env` (default `GPT_AT_RUB_API_KEY`).

- **GPT@RUB caps external-API calls at 60 requests/minute.** `OpenAICompatibleClient`
  (`repair/llm/client.py`) tracks its own request timestamps in a sliding 60-second window
  and sleeps as needed before each call to stay under the cap, so large `--max-candidates`
  / `--top-n` runs won't get rejected by the server for exceeding the rate limit.

## Summary



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
```

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
| Repair evaluation matrix | `bugsinpy evaluate-repair --bugs "tornado:14,scrapy:2,black:1" --fl-modes "auto,perfect"` |
| Repair evaluation output | `experiment_results/repair/results.json` + `README.md` + per-cell `run_artifacts/` |



## Quick Reference Table

| Feature | Implementation |
| --- | --- |
| BugsInPy run tests | `bugsinpy test` |
| Structured test results | `TestRunResult` with counts and raw output |
| FauxPy localization CLI | `localize --backend fauxpy --project <project> --bug <id>` |
| FauxPy metric selection | `localize --metric ochiai`, `localize --metric jaccard`, `localize --metric wsbi --wsbi-alpha 0.5` |
| Custom SBFL metrics | Jaccard and WSBI (Weighted SBI) added via runtime patch to FauxPy 0.7.0 |
| WSBI configurable alpha | `localize --metric wsbi --wsbi-alpha 0.5` (default); range (0, 1] |
| Hybrid localization | `localize --family hybrid --sbfl-metric ochiai --mbfl-metric metallaxis` |
| MBFL random-budget extension | `localize --mbfl --mutation-strategy random --budget 50` |
| Multi-technique evaluation | `bugsinpy evaluate-localization --bugs "fastapi:3,fastapi:6,luigi:33"` |
| Evaluation output | `experiment_results/results.json` and `experiment_results/README.md` |
| FauxPy granularity selection | `localize --granularity statement` and `localize --granularity function` |
| FauxPy output parser | `parse_fauxpy_output` parses all metrics or one selected metric |
| FauxPy result metadata | `LocalizationResult.metadata["all_metrics"]` stores every parsed metric table |
| CLI entry point | `python -m apr_framework` and `apr-framework` script |
| Dummy repair component | `DummyRepairAlgorithm` |
| Evaluation output handling | `runs/run_xxx/config.json`, `results.json`, `execution.log` |

## Commands 

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

python -m apr_framework repair --project black --bug 1
```
