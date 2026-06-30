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

Jaccard and WSBI are available for SBFL runs through the framework's FauxPy 0.7.0
patch, which is applied inside the prepared checkout environment before localization:

```bash
python -m apr_framework localize --project PySnooper --bug 1 --metric jaccard
python -m apr_framework localize --project PySnooper --bug 1 --metric wsbi
```

- Use `--wsbi-alpha` to control the passing-test weight (default: `0.5`):

```bash
# Default alpha=0.5: passing tests count half as much as failing tests
python -m apr_framework localize --project PySnooper --bug 1 --metric wsbi

# alpha=1.0 reduces to plain SBI (equal weight)
python -m apr_framework localize --project PySnooper --bug 1 --metric wsbi --wsbi-alpha 1.0

# alpha=0.25 further discounts passing-test coverage
python -m apr_framework localize --project PySnooper --bug 1 --metric wsbi --wsbi-alpha 0.25
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





## Experiment Results (Evaluation)

The framework was evaluated on three real BugsInPy bugs: **fastapi#3**, **fastapi#6**, and **luigi#33**. All 8 techniques were compared against the ground-truth faulty line from each bug's patch. Full results are in [`experiment_results/README.md`](experiment_results/README.md).

### Summary table

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
| CLI entry point | `python -m apr_framework` and `apr-framework` script |
| Dummy repair component | `DummyRepairAlgorithm` |
| Evaluation output handling | `runs/run_xxx/config.json`, `results.json`, `execution.log` , `*.zip`|


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
