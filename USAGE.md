# Usage

Run all commands from the repository root. If the package is not installed yet,
install it in your active environment first:

```bash
python -m pip install -e .
```

The framework CLI is available through:

```bash
python -m apr_framework
```

## List Benchmarks

Print the benchmark adapters registered in the framework.

```bash
python -m apr_framework list-benchmarks
```

## BugsInPy Setup

Clone or refresh the local BugsInPy tooling, build the Docker executor image,
create/start the executor container, and prepare the local BugsInPy workspace.

```bash
python -m apr_framework bugsinpy setup
```

This command requires Git, Docker, and a reachable Docker daemon.

## List BugsInPy Projects

Print every BugsInPy project known to the local BugsInPy checkout.

```bash
python -m apr_framework bugsinpy list-projects
```

Run `bugsinpy setup` first if `.tools/bugsinpy` is not available.

## List Bugs For A Project

Print the bug IDs available for one BugsInPy project.

```bash
python -m apr_framework bugsinpy list-bugs PySnooper
```

Replace `PySnooper` with any project returned by `bugsinpy list-projects`.

## Checkout A Bug

Check out one buggy BugsInPy project version into `.workspace/bugsinpy`.

```bash
python -m apr_framework bugsinpy checkout PySnooper 1
```

The checkout path is:

```text
.workspace/bugsinpy/PySnooper_1/PySnooper
```

## Compile A Bug

Prepare the checked-out bug environment using the BugsInPy safe compile step.

```bash
python -m apr_framework bugsinpy compile PySnooper 1
```

Run `bugsinpy checkout PySnooper 1` before this command.

## Run BugsInPy Tests

Check out, prepare, and run the BugsInPy test suite for one bug.

```bash
python -m apr_framework bugsinpy test PySnooper 1
```

This command prints checkout status, preparation status, and passing/failing
test counts. It may mutate the ignored `.workspace/bugsinpy` checkout.

## Run Dummy Evaluation

Run the deterministic dummy repair and dummy evaluation pipeline over the
default BugsInPy bugs: `black 1`, `black 3`, and `black 23`.

```bash
python -m apr_framework bugsinpy evaluate-dummy
```

Use a deterministic seed:

```bash
python -m apr_framework bugsinpy evaluate-dummy --seed 123
```

Write run artifacts to a custom directory:

```bash
python -m apr_framework bugsinpy evaluate-dummy --seed 123 --runs-dir runs
```

Each run creates:

```text
runs/run_###/config.json
runs/run_###/results.json
runs/run_###/execution.log
```

## Localize With FauxPy

Run FauxPy fault localization for a checked-out and compiled BugsInPy bug.

```bash
python -m apr_framework localize --project PySnooper --bug 1
```

The backend flag is optional because `fauxpy` is the only implemented
localization backend.

```bash
python -m apr_framework localize --backend fauxpy --project PySnooper --bug 1
```

Run these commands first:

```bash
python -m apr_framework bugsinpy setup
python -m apr_framework bugsinpy checkout PySnooper 1
python -m apr_framework bugsinpy compile PySnooper 1
```

### Select A Source Root

By default, the framework tries to infer the source root from the project name.
Pass `--src` when the source package is somewhere else.

```bash
python -m apr_framework localize --project PySnooper --bug 1 --src pysnooper
```

For example, BugsInPy's `black 1` keeps `black.py` at the checkout root:

```bash
python -m apr_framework localize --project black --bug 1 --src .
```

### Select A Metric

Choose the FauxPy metric used for the primary ranked locations. The parser also
keeps every metric table in result metadata for later reuse.

```bash
python -m apr_framework localize --project PySnooper --bug 1 --metric ochiai
```

Common FauxPy metric names include `ochiai`, `tarantula`, and `dstar`.
For SBFL runs, the framework also patches FauxPy 0.7.0 inside the prepared
checkout environment so `jaccard` is available:

```bash
python -m apr_framework localize --project PySnooper --bug 1 --metric jaccard
```

### Limit Ranked Output

Print only the top N suspicious locations from the selected metric.

```bash
python -m apr_framework localize --project PySnooper --bug 1 --metric ochiai --top-n 10
```

### Use Function Granularity

Ask FauxPy to rank suspicious functions instead of statement-level locations.

```bash
python -m apr_framework localize --project PySnooper --bug 1 --granularity function --metric ochiai --top-n 10
```

### Select Failing Tests

Pass a comma-separated failing test list to FauxPy.

```bash
python -m apr_framework localize --project PySnooper --bug 1 --failing_tests "tests/test_chinese.py::test_chinese"
```

For multiple tests:

```bash
python -m apr_framework localize --project PySnooper --bug 1 --failing_tests "tests/test_chinese.py::test_chinese,tests/test_pysnooper.py::test_file_output"
```

### Run Broader Test Targets

By default, BugsInPy localization runs the relevant test target from
`run_test.sh`. To match FauxPy's broader-suite pattern, pass one or more
`--test-target` values. If `--failing_tests` is omitted, the BugsInPy relevant
test is still passed to FauxPy as the targeted failing test.

```bash
python -m apr_framework localize --project black --bug 1 --src black.py --test-target tests/test_black.py --metric ochiai --top-n 10
```

Use `--show-raw-output` only when you need the complete pytest/FauxPy stream for
debugging.

### Use MBFL Mode

Run FauxPy in mutation-based fault localization mode.

```bash
python -m apr_framework localize --project PySnooper --bug 1 --family mbfl --granularity statement --metric ochiai --top-n 10
```

The CLI also accepts mutation strategy and budget values:

```bash
python -m apr_framework localize --project PySnooper --bug 1 --family mbfl --mutation_strategy first_order --mutation_budget 50 --metric ochiai
```

## Typical End-To-End Flow

This sequence prepares BugsInPy, checks out `PySnooper 1`, compiles it, runs tests,
and localizes the top 10 Ochiai-ranked locations.

```bash
python -m apr_framework bugsinpy setup
python -m apr_framework bugsinpy checkout PySnooper 1
python -m apr_framework bugsinpy compile PySnooper 1
python -m apr_framework bugsinpy test PySnooper 1
python -m apr_framework localize --project PySnooper --bug 1 --metric ochiai --top-n 10
```





```bash
root@71fe3e2ad45d:/workspace# python -m apr_framework localize --project black --bug 1 --family sbfl --src black.py --test-target tests/test_black.py --metric ochiai --top-n 20
Project: black
Bug ID: 1
Backend: fauxpy
Score formula: Ochiai
Ranked locations:
1. black.py:6339 0.4762
2. black.py:5769 0.4762
3. black.py:535 0.4762
4. black.py:534 0.4762
5. black.py:533 0.4762
6. black.py:621 0.3922
7. black.py:618 0.3922
8. black.py:617 0.3922
9. black.py:616 0.3922
10. black.py:558 0.3922
11. black.py:557 0.3922
12. black.py:5750 0.3642
13. black.py:5749 0.3642
14. black.py:5748 0.3642
15. black.py:5747 0.3415
16. black.py:5742 0.3415
17. black.py:5738 0.3415
18. black.py:5737 0.3415
19. black.py:5734 0.3415
20. black.py:5720 0.3226
```

- One can use the Jaccard metric too
```bash 
root@71fe3e2ad45d:/workspace# python -m apr_framework localize --project black --bug 1 --family sbfl --src black.py --test-target tests/test_black.py --metric jaccard --top-n 20
Project: black
Bug ID: 1
Backend: fauxpy
Score formula: Jaccard
Ranked locations:
1. black.py:6339 0.2439
2. black.py:5769 0.2439
3. black.py:535 0.2439
4. black.py:534 0.2439
5. black.py:533 0.2439
6. black.py:621 0.1639
7. black.py:618 0.1639
8. black.py:617 0.1639
9. black.py:616 0.1639
10. black.py:558 0.1639
11. black.py:557 0.1639
12. black.py:5750 0.1408
13. black.py:5749 0.1408
14. black.py:5748 0.1408
15. black.py:5747 0.1235
16. black.py:5742 0.1235
17. black.py:5738 0.1235
18. black.py:5737 0.1235
19. black.py:5734 0.1235
20. black.py:5720 0.1099
```
