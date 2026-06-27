# Failed Experiment Report: black:1, black:3, black:7

**Status:** FAILED — Results are not scientifically meaningful; do not use as artifact.

**Date:** 2026-06-27

---

## What Was Attempted

Ran FauxPy 0.7.0 inside Docker for three BugsInPy bugs from the `black` Python formatter
(`black:1`, `black:3`, `black:7`) to compare five SBFL metrics, two MBFL variants, and
the Hybrid technique against ground-truth faulty lines.

Results were real (produced by actual FauxPy runs inside Docker), but the bug selection
was fatally wrong. See `results.json` and `README.md` for the raw data.

---

## Why the Experiment Failed

### Root Cause 1: Single Failing Test Per Bug

Every BugsInPy `run_test.sh` for the selected black bugs contained exactly ONE failing test:

| Bug | Failing test |
|---|---|
| `black:1` | `test_works_in_mono_process_only_environment` |
| `black:3` | `test_invalid_config_return_code` |
| `black:7` | test for `testlist_star_expr` parenthesis normalisation |

When there is a single failing test and no passing tests are run, **every SBFL formula
collapses to the same ranking**. The mathematical reason:

For any statement covered by the failing test:
- `ef = 1`, `ep = 0`, `nf = 0`, `np = 0`
- Ochiai = `ef / sqrt((ef+nf)*(ef+ep))` = `1 / sqrt(1*1)` = **1.0**
- Tarantula = `(ef/(ef+nf)) / (ef/(ef+nf) + ep/(ep+np))` = `1 / (1+0)` = **1.0**
- D* = `ef² / ((nf+ep)·…)` = **maximum**
- Jaccard = **maximum**; SBI = **maximum**

All five SBFL metrics assign the same maximum score to every covered statement.
Ranking is then determined only by FauxPy's internal tie-breaking (line number order),
which has nothing to do with actual fault suspicion. The extensions (Jaccard, SBI) appear
identical to the baselines (Ochiai, Tarantula, D*) — a structural tie, not a real result.

**Observed outcome:** All 5 SBFL metrics gave `rank=11` for black:1 and `rank=165` for
black:7 — identical across all metrics because the single-test condition makes the SBFL
formula irrelevant.

### Root Cause 2: Mutation-Inadequate Test Suites (MBFL gives 0 rankings)

FauxPy MBFL generates mutants for the covered statements and validates them by running
the test suite on each mutant. A mutant is "killed" only when a test changes outcome
(passing → failing, or failing → passing).

For all three black bugs, **every generated mutant survived the test suite**:

- **black:1** — The failing test checks that multiprocessing is *disabled*. Cosmic Ray /
  mutmut mutations to the `ProcessPoolExecutor` constructor (lines 621/636/646) use
  arithmetic and logical substitution operators, not process-spawning logic. No mutation
  changes whether multiprocessing is disabled.

- **black:3** — The faulty line (`click.Path(exists=False)`) is evaluated at **module
  import time** (it is a decorator argument). FauxPy's statement-level coverage never
  records it. With zero coverage for that line, no mutants are generated for it.

- **black:7** — The failing test checks the final formatted string output. Mutations to
  the covered 536 statements (mostly temporary variables, branches, helper calls) do not
  affect the output string. Random-budget selection of 200 (baseline) and 50 (extension)
  statements did not reach the critical output-altering lines.

**Observed outcome:** MBFL returned 0 ranked locations for all 3 bugs, for both the
baseline (budget 200) and the extension (budget 50).

### Root Cause 3: Module-Level Fault (black:3 is invisible to SBFL)

The fault in `black:3` (`click.Path(exists=False)`) is a decorator argument that Python
evaluates **during module import**, before any test runs. FauxPy's dynamic coverage
instrumentation only records lines executed *during test execution*. Line 397 never
appears in any coverage trace, so it cannot be ranked by either SBFL or MBFL.

**Observed outcome:** SBFL ranked only 13 statements (function bodies reached during the
test); line 397 was not among them. `faulty_rank = null`.

---

## What a Correct Experiment Requires

### SBFL: Multiple Failing Tests

SBFL formulae only differentiate suspicion scores when statements are covered by
**different subsets of the failing tests**. With a single failing test per bug:
- `ef ∈ {0, 1}` for every statement
- Ochiai and all other formulae reduce to a binary covered/not-covered indicator
- All covered statements tie at the maximum score

**Minimum requirement:** Bugs whose `run_test.sh` lists ≥ 2 failing tests that exercise
different code paths within the faulty module.

### MBFL: Mutation-Adequate Test Suites

MBFL can only locate faults where mutations *change test outcomes*. The ideal fault:
- Is in a **function called directly by the failing tests**
- Involves arithmetic, comparison, or boolean logic that mutation operators can change
- Has tests that **check the return value or observable side-effect** of the faulty call

Bugs in string parsing with no direct value assertion, or bugs in decorator/class-level
metadata, are generally mutation-inadequate.

### Identified Replacement Candidates

The following BugsInPy bugs meet both requirements:

| Bug | # Failing tests | Fault type | Why MBFL should work |
|---|---|---|---|
| `fastapi:3` | 8 | Missing recursive serialization for nested lists/dicts | Tests directly check JSON response body; `exclude_unset`/`by_alias` conditions are mutation-eligible |
| `fastapi:6` | 3 | `field.shape in sequence_shapes` missing `or field.type_ in sequence_types` | Boolean operator mutation (`or`→`and`) directly changes which fields are treated as sequences |
| `fastapi:11` | 6 | `is_scalar_field` not checking `field.sub_fields` | Multiple tests cover Union body types; early-return condition is mutation-eligible |

All three use Python 3.8.3 (compatible with FauxPy 0.7.0), pure pytest, and have no
binary dependencies (unlike pandas/numpy or keras/tensorflow).

---

## Command to Reproduce the Failed Results

```bash
# These commands reproduce the failed evaluation (real FauxPy results, wrong bug selection)
docker compose build
docker compose run --rm apr-framework python -m apr_framework bugsinpy setup
python -m apr_framework bugsinpy compile black 1
python -m apr_framework bugsinpy compile black 3
python -m apr_framework bugsinpy compile black 7
python -m apr_framework bugsinpy evaluate-localization \
    --bugs "black:1,black:3,black:7" \
    --budget 50 --traditional-budget 200 --seed 42 \
    --granularity statement --output-dir experiment_results
```

The results in `results.json` and `README.md` were produced by exactly this sequence.

---

## Lessons Learned

1. **Check run_test.sh before selecting bugs.** Any bug with exactly one entry in
   `run_test.sh` is a poor SBFL benchmark unless the full project test suite is also run
   as `test_targets`, providing passing tests that share code with the faulty function.

2. **Check the fault type before running MBFL.** Module-level faults (decorator args,
   class attributes), string-content bugs, and infrastructure bugs (process spawning,
   file locking) are unlikely to be mutation-adequate with standard mutation operators.

3. **Avoid all-formatter-style projects.** Code formatters like `black` have large
   monolithic files and test suites where each bug test is a single input/output check.
   The high-level "format this code" assertion is insensitive to most mutations.

4. **Prefer modular API projects.** Projects like fastapi, where each failing test
   exercises a specific endpoint/response-model path, give SBFL real differentiation
   (8 tests cover different response shapes) and MBFL real signal (mutations to the
   serialization condition change response values that tests directly assert).
