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
  - SBFL and MBFL mode selection
  - statement-level and function-level granularity
  - metric selection with `--metric`
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
stored in `metadata["all_metrics"]`. This keeps Tarantula, Ochiai, DStar, and
other emitted tables available for later repair or reporting components.

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
python -m apr_framework localize --project PySnooper --bug 1 --family mbfl --granularity statement --metric ochiai --top-n 10
```

- The CLI also accepts mutation strategy and budget values for MBFL:

```bash
python -m apr_framework localize --project PySnooper --bug 1 --family mbfl --mutation_strategy first_order --mutation_budget 50 --metric ochiai
```

- What changed internally:
  - `FauxPyConfig` now carries the localization family, granularity, metric,
  failing tests, excludes, and MBFL options.
  - `FauxPyToolchain` builds the pytest/FauxPy command from that config.
  - `parse_fauxpy_output` parses all metric tables when `metric_filter=None`.
  - `parse_fauxpy_output` returns only one metric's ranked rows when
  `metric_filter` is set.
  - The parser supports statement rows (`File | Line | Score`) and function rows
  (`File | Function | Line | Score`).
  - `LocalizationResult.metadata["all_metrics"]` stores the full metric map for
  later reuse.

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
| Clean Python project structure | `src/apr_framework` package with reusable modules |
| Type hints and documented public classes/functions | Dataclasses, interfaces, and component docstrings |
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
| FauxPy metric selection | `localize --metric ochiai` |
| FauxPy granularity selection | `localize --granularity statement` and `localize --granularity function` |
| FauxPy output parser | `parse_fauxpy_output` parses all metrics or one selected metric |
| FauxPy result metadata | `LocalizationResult.metadata["all_metrics"]` stores every parsed metric table |
| CLI entry point | `python -m apr_framework` and `apr-framework` script |
| Dummy repair component | `DummyRepairAlgorithm` |
| Evaluation output handling | `runs/run_xxx/config.json`, `results.json`, `execution.log` |


