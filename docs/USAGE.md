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
checkout environment so `jaccard` and `sbi` are available:

```bash
python -m apr_framework localize --project PySnooper --bug 1 --metric jaccard
python -m apr_framework localize --project PySnooper --bug 1 --metric sbi
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
python -m apr_framework localize --project PySnooper --bug 1 --mbfl --granularity statement --metric metallaxis --top-n 10
```

Limit expensive mutant validation with the random selector:

```bash
python -m apr_framework localize --project PySnooper --bug 1 --mbfl --mutation-strategy random --budget 50 --metric metallaxis
```

`--budget` limits how many mutants are validated. Use `--seed` to reproduce the
same random selection; the default seed is `0`.

### Use Hybrid SBFL + MBFL Mode

Run the existing FauxPy SBFL and MBFL paths, normalize both selected metrics,
and print a single weighted ranking.

```bash
python -m apr_framework localize --project PySnooper --bug 1 --family hybrid --sbfl-metric ochiai --mbfl-metric metallaxis --sbfl-weight 0.5 --mbfl-weight 0.5 --mutation-strategy random --budget 50 --top-n 10
```

Hybrid mode uses `--sbfl-metric` and `--mbfl-metric` instead of `--metric`.
`--top-n` is applied after score fusion, and mutation controls apply only to the
MBFL component.

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

- One can use the Jaccard or SBI metric too
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


- MBFL usage 
```bash 
root@92e99d5a1a10:/workspace# python -m apr_framework localize \
  --backend fauxpy \
  --project black \
  --bug 1 \
  --src black.py \
  --test-target tests/test_black.py \
  --mbfl \
  --mutation-strategy random \
  --budget 5 \
  --seed 1 \
  --metric metallaxis \
  --top-n 5 \
  --show-raw-output
Project: black
Bug ID: 1
Backend: fauxpy
Score formula: Metallaxis
Ranked locations:

Raw FauxPy output:
============================= test session starts ==============================
platform linux -- Python 3.8.3, pytest-8.3.5, pluggy-1.5.0
rootdir: /home/workspace/black_1/black
configfile: pyproject.toml
plugins: timeout-2.1.0, fauxpy-0.7.0, anyio-4.5.2
collected 129 items

tests/test_black.py .................................................... [ 40%]
.............................................................F.......... [ 96%]
.....                                                                    [100%]

=================================== FAILURES ===================================
__________ BlackTestCase.test_works_in_mono_process_only_environment ___________

self = <tests.test_black.BlackTestCase testMethod=test_works_in_mono_process_only_environment>
mock_executor = <MagicMock name='ProcessPoolExecutor' spec='ProcessPoolExecutor' id='281473147078928'>

    @patch("black.ProcessPoolExecutor", autospec=True)
    def test_works_in_mono_process_only_environment(self, mock_executor) -> None:
        mock_executor.side_effect = OSError()
        mode = black.FileMode()
        with cache_dir() as workspace:
            one = (workspace / "one.py").resolve()
            with one.open("w") as fobj:
                fobj.write("print('hello')")
            two = (workspace / "two.py").resolve()
            with two.open("w") as fobj:
                fobj.write("print('hello')")
            black.write_cache({}, [one], mode)
>           self.invokeBlack([str(workspace)])

tests/test_black.py:1288: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_black.py:162: in invokeBlack
    self.assertEqual(result.exit_code, exit_code, msg=runner.stderr_bytes.decode())
E   AssertionError: 1 != 0 :
=============================== warnings summary ===============================
env/lib/python3.8/site-packages/aiohttp/helpers.py:107
  /home/workspace/black_1/black/env/lib/python3.8/site-packages/aiohttp/helpers.py:107: DeprecationWarning: "@coroutine" decorator is deprecated since Python 3.8, use "async def" instead
    def noop(*args, **kwargs):  # type: ignore

tests/test_black.py: 12 warnings
  /home/workspace/black_1/black/env/lib/python3.8/site-packages/aiohttp/connector.py:964: DeprecationWarning: The loop argument is deprecated since Python 3.8, and scheduled for removal in Python 3.10.
    hosts = await asyncio.shield(self._resolve_host(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html


***************************************************
                FauxPy Started!                    
***************************************************

FauxPy: ---> Running MBFL session
FauxPy: ---> Targeted failing tests:
FauxPy: --->   1. tests/test_black.py::BlackTestCase::test_works_in_mono_process_only_environment


==============================
 Dynamic Analysis in Progress 
==============================

FauxPy: ---> Candidate mutation locations: 90
FauxPy: ---> Selected mutation locations: 5
FauxPy: ---> Generating mutants using the mutation strategy Traditional for the following module:
FauxPy: --->   /home/workspace/black_1/black/black.py
FauxPy: ---> Number of generated mutants: 8
FauxPy: ---> Total generated mutants: 8
FauxPy: ---> Mutants selected for validation: 5
FauxPy: ---> Mutation generation time: 7.4620
FauxPy: ---> Running 5 Mutants
FauxPy: ---> Running Mutant M0 (1/5)
FauxPy: ---> Timeout or bad mutant
FauxPy: ---> Running Mutant M1 (2/5)
FauxPy: ---> Timeout or bad mutant
FauxPy: ---> Running Mutant M2 (3/5)
FauxPy: ---> Timeout or bad mutant
FauxPy: ---> Running Mutant M3 (4/5)
FauxPy: ---> Timeout or bad mutant
FauxPy: ---> Running Mutant M4 (5/5)
FauxPy: ---> Timeout or bad mutant
FauxPy: ---> Mutant validation time: 0.4838


--- Dynamic Analysis Complete ---

============================
 Fault Localization Results 
============================

=== Performance ===
Execution Time: 59.8703

-----------------------
|   Scores for Muse   |
-----------------------
File | Line | Score
-------------------
-------------------

-----------------------------
|   Scores for Metallaxis   |
-----------------------------
File | Line | Score
-------------------
-------------------

**************************************************
                FauxPy Ended!                     
**************************************************

=========================== short test summary info ============================
FAILED tests/test_black.py::BlackTestCase::test_works_in_mono_process_only_environment
================= 1 failed, 128 passed, 13 warnings in 59.85s ==================
root@92e99d5a1a10:/workspace# 
```

- My metric on SBFL
```bash
root@a9334b533878:/workspace# python -m apr_framework localize \
  --backend fauxpy \
  --project black \
  --bug 1 \
  --family sbfl \
  --src black.py \
  --test-target tests/test_black.py \
  --metric sbi \
  --top-n 20
Project: black
Bug ID: 1
Backend: fauxpy
Score formula: SBI
Ranked locations:
1. black.py:6339 0.2500
2. black.py:5769 0.2500
3. black.py:535 0.2500
4. black.py:534 0.2500
5. black.py:533 0.2500
6. black.py:621 0.1667
7. black.py:618 0.1667
8. black.py:617 0.1667
9. black.py:616 0.1667
10. black.py:558 0.1667
11. black.py:557 0.1667
12. black.py:5750 0.1429
13. black.py:5749 0.1429
14. black.py:5748 0.1429
15. black.py:5747 0.1250
16. black.py:5742 0.1250
17. black.py:5738 0.1250
18. black.py:5737 0.1250
19. black.py:5734 0.1250
20. black.py:5720 0.1111
```



## Template-Based Repair

Apply AST mutation operators to the top-N suspicious locations identified by
fault localization.

### Perfect FL (oracle locations from developer fix)

```bash
python -m apr_framework repair --project black --bug 1 \
  --technique template \
  --fl-mode perfect \
  --budget 200 --top-n 5
```

### Automated SBFL FL

```bash
python -m apr_framework repair --project black --bug 1 \
  --technique template \
  --fl-mode auto --fl-family sbfl --localization-metric ochiai \
  --budget 200 --top-n 5
```

### Select mutation operators

Pass a comma-separated subset of `arith,comp,obo,bool,negate,return`:

```bash
python -m apr_framework repair --project black --bug 1 \
  --technique template \
  --fl-mode perfect \
  --operators comp,obo,negate \
  --budget 100 --top-n 3
```

### Enable patch ranking

Rank plausible patches by a composite score of suspiciousness, patch
simplicity, and operator priority instead of preserving generation order:

```bash
python -m apr_framework repair --project black --bug 1 \
  --technique template --fl-mode perfect \
  --ranker weighted
```

Override component weights (suspiciousness : simplicity : operator_priority):

```bash
python -m apr_framework repair --project black --bug 1 \
  --technique template --fl-mode perfect \
  --ranker weighted --ranker-weights 0.7,0.2,0.1
```

### Stop on first plausible patch

```bash
python -m apr_framework repair --project black --bug 1 \
  --technique template --fl-mode perfect \
  --stop-on-first
```

Run artifacts are written to:

```text
runs/run_###/config.json
runs/run_###/results.json
runs/run_###/execution.log
```

## LLM-Based Repair

Use an LLM to generate candidate patches for the top-N suspicious locations.
The framework calls a GPT@RUB-compatible OpenAI API endpoint.

### Prerequisites

Export the API key before running any LLM repair command:

```bash
export GPT_AT_RUB_API_KEY="your-api-key-here"
```

The key is read at call time from the environment variable named by
`--llm-api-key-env` (default: `GPT_AT_RUB_API_KEY`).

### Perfect FL (oracle locations)

```bash
python -m apr_framework repair --project black --bug 1 \
  --technique llm \
  --fl-mode perfect \
  --model codestral-22b \
  --max-candidates 5 --top-n 3 --budget 200
```

### Automated SBFL FL

```bash
python -m apr_framework repair --project black --bug 1 \
  --technique llm \
  --fl-mode auto --fl-family sbfl --localization-metric ochiai \
  --model codestral-22b \
  --max-candidates 5 --top-n 5 --budget 200
```

### Adjust temperature

Higher temperature increases output diversity; lower values make responses more
deterministic. Valid range: `[0.0, 2.0]`.

```bash
python -m apr_framework repair --project black --bug 1 \
  --technique llm --fl-mode perfect \
  --temperature 1.0 --max-candidates 10
```

### Use a different model

```bash
python -m apr_framework repair --project black --bug 1 \
  --technique llm --fl-mode perfect \
  --model gpt-4o
```

### Override the API endpoint

Point the client at any OpenAI-compatible endpoint:

```bash
python -m apr_framework repair --project black --bug 1 \
  --technique llm --fl-mode perfect \
  --llm-base-url https://api.openai.com/v1 \
  --llm-api-key-env OPENAI_API_KEY
```

### LLM repair flag reference

| Flag | Default | Description |
|------|---------|-------------|
| `--technique llm` | — | Selects the LLM repair backend |
| `--model` | `codestral-22b` | Model name sent to the API |
| `--temperature` | `0.8` | Sampling temperature `[0.0, 2.0]` |
| `--max-candidates` | `5` | Patch candidates generated per suspicious location |
| `--llm-provider` | `openai-compatible` | Client implementation to use |
| `--llm-base-url` | GPT@RUB endpoint | Override the API base URL |
| `--llm-api-key-env` | `GPT_AT_RUB_API_KEY` | Env-var name holding the API key |

Flags shared with template repair (`--budget`, `--top-n`, `--stop-on-first`,
`--no-regression-check`, `--fl-mode`, `--fl-family`, `--localization-metric`,
`--ranker`, `--runs-dir`) work identically for both techniques.

### Typical end-to-end LLM repair flow

```bash
# 1. One-time setup (builds Docker images, starts executor container)
python -m apr_framework bugsinpy setup

# 2. Prepare the bug
python -m apr_framework bugsinpy checkout black 1
python -m apr_framework bugsinpy compile black 1

# 3. Export API key
export GPT_AT_RUB_API_KEY="your-api-key-here"

# 4. Run LLM repair with perfect FL
python -m apr_framework repair --project black --bug 1 \
  --technique llm \
  --fl-mode perfect \
  --model gpt-4.1-2025-04-14 \
  --max-candidates 5 --top-n 3 --budget 100

# 5. Run LLM repair with automated SBFL FL
python -m apr_framework repair --project black --bug 1 \
  --technique llm \
  --fl-mode auto --fl-family sbfl --localization-metric ochiai \
  --src black.py \
  --model codestral-22b \
  --max-candidates 5 --top-n 5 --budget 200
```

Run artifacts (config, patch diffs, results JSON, execution log) are written to
`runs/run_###/` as with template repair.

## Hybrid SBFL + MBFL 
- The typical command and the output looks as follows
```bash
root@5c7c7e708541:/workspace# python -m apr_framework localize \
  --project black \
  --bug 1 \
  --family hybrid \
  --src black.py \
  --test-target tests/test_black.py \
  --sbfl-metric ochiai \
  --mbfl-metric metallaxis \
  --sbfl-weight 0.5 \
  --mbfl-weight 0.5 \
  --mutation-strategy random \
  --budget 50 \
  --seed 0 \
  --top-n 10
apr-bugsinpy-executor
Project: black
Bug ID: 1
Backend: hybrid-fauxpy
Score formula: 0.5000 * normalized(Ochiai) + 0.5000 * normalized(Metallaxis)
Ranked locations:
1. black.py:6339 0.5000
2. black.py:5769 0.5000
3. black.py:535 0.5000
4. black.py:534 0.5000
5. black.py:533 0.5000
6. black.py:621 0.4118
7. black.py:618 0.4118
8. black.py:617 0.4118
9. black.py:616 0.4118
10. black.py:558 0.4118
root@5c7c7e708541:/workspace# 
```