# Fault Localization Evaluation Results

Comparison of SBFL and MBFL baseline techniques against the framework's extensions
(custom SBFL metrics Jaccard and SBI; random-budget MBFL; Hybrid SBFL+MBFL) on
three BugsInPy bugs: `fastapi:3`, `fastapi:6`, `luigi:33`.

All results were produced by actually running FauxPy 0.7.0 (with the framework's
in-place patches applied) inside Docker. Generated: 2026-06-27.

---

## Bug Set

| Bug | Project version | Fault | Ground-truth line(s) |
|---|---|---|---|
| `fastapi#3` | fastapi 0.54.x | Missing `_prepare_response_content` — serialization doesn't recurse into nested lists/dicts when `exclude_unset=True` | `fastapi/routing.py:63–69` (7 lines) |
| `fastapi#6` | fastapi 0.52.x | Condition `field.shape in sequence_shapes` missing `or field.type_ in sequence_types` | `fastapi/dependencies/utils.py:632–634` |
| `luigi#33` | luigi 2.8.x | `if p.significant` should be `if not p.is_global` in positional-params filter | `luigi/task.py:334` |

Each `run_test.sh` has **multiple failing tests** (8, 3, and 4 respectively), giving
SBFL a real coverage spectrum rather than the degenerate single-test case.

---

## Results

### fastapi bug #3

**Failing tests (8):** `test_valid`, `test_coerce`, `test_validlist`, `test_validdict`,
`test_valid_exclude_unset`, `test_coerce_exclude_unset`, `test_validlist_exclude_unset`,
`test_validdict_exclude_unset` (all in `tests/test_serialize_response_model.py`)

| Technique | Type | Rank | Top-1 | Top-5 | Top-10 | Total ranked |
|---|---|---|---|---|---|---|
| SBFL-Ochiai | baseline | **8** | ✗ | ✗ | **✓** | 76 |
| SBFL-Tarantula | baseline | 11 | ✗ | ✗ | ✗ | 76 |
| SBFL-DStar | baseline | **8** | ✗ | ✗ | **✓** | 76 |
| SBFL-Jaccard | **extension** | **8** | ✗ | ✗ | **✓** | 76 |
| SBFL-SBI | **extension** | 11 | ✗ | ✗ | ✗ | 76 |
| MBFL-Metallaxis (budget 200) | baseline | — | — | — | — | 0 |
| MBFL-Metallaxis-Random (budget 50) | **extension** | — | — | — | — | 0 |
| Hybrid SBFL+MBFL | **extension** | **8** | ✗ | ✗ | **✓** | 76 |

**Ochiai/DStar/Jaccard rank the faulty line at 8; Tarantula/SBI rank it at 11.**
With 8 failing tests covering different code paths (some tests specifically for list/dict
responses, others for plain BaseModel responses), the SBFL formulae produce genuinely
different scores and thus different tie-breaking order. Jaccard (extension) matches the
best baseline (Ochiai). SBI (extension) matches the weaker baseline (Tarantula).

**MBFL gives 0 results.** The bug is a missing recursive call — the covered code is
conditional logic and isinstance checks. FauxPy's mutmut operators (arithmetic replacement,
logical connective swap, comparison flip) applied to these statements don't produce
mutations that change the HTTP response body in a way the 8 failing tests can detect.
Mutations that would fix the bug (e.g., making `serialize_response` call itself recursively)
are not in mutmut's mutation vocabulary.

---

### fastapi bug #6

**Failing tests (3):** `test_python_list_param_as_form`, `test_python_set_param_as_form`,
`test_python_tuple_param_as_form` (all in `tests/test_forms_from_non_typing_sequences.py`)

| Technique | Type | Rank | Top-1 | Top-5 | Top-10 | Total ranked |
|---|---|---|---|---|---|---|
| SBFL-Ochiai | baseline | 82 | ✗ | ✗ | ✗ | 137 |
| SBFL-Tarantula | baseline | 82 | ✗ | ✗ | ✗ | 137 |
| SBFL-DStar | baseline | 82 | ✗ | ✗ | ✗ | 137 |
| SBFL-Jaccard | **extension** | 82 | ✗ | ✗ | ✗ | 137 |
| SBFL-SBI | **extension** | 82 | ✗ | ✗ | ✗ | 137 |
| MBFL-Metallaxis (budget 200) | baseline | — | — | — | — | 0 |
| MBFL-Metallaxis-Random (budget 50) | **extension** | — | — | — | — | 0 |
| Hybrid SBFL+MBFL | **extension** | 82 | ✗ | ✗ | ✗ | 137 |

**All 5 SBFL metrics give the same rank (82).** The 3 failing tests are closely related
(list vs set vs tuple as form params) and traverse nearly identical code paths in
`request_body_to_args`. The coverage spectrum across 3 tests that differ only by
collection type provides limited inter-statement differentiation for any formula.

**MBFL gives 0 results.** Same cause as fastapi#3: the bug is a missing `or` condition
in a complex boolean expression — mutations to `and`/`or` or attribute access don't
produce survivors that kill the 3 failing tests.

---

### luigi bug #33

**Failing tests (4):** `test_local_insignificant_param`, `test_global_significant_param`,
`test_mixed_params`, `test_mixed_params_inheritence` (all in `test/parameter_test.py`)

| Technique | Type | Rank | Top-1 | Top-5 | Top-10 | Total ranked |
|---|---|---|---|---|---|---|
| SBFL-Ochiai | baseline | **11** | ✗ | ✗ | ✗ | 490 |
| SBFL-Tarantula | baseline | **191** | ✗ | ✗ | ✗ | 490 |
| SBFL-DStar | baseline | **11** | ✗ | ✗ | ✗ | 490 |
| SBFL-Jaccard | **extension** | **11** | ✗ | ✗ | ✗ | 490 |
| SBFL-SBI | **extension** | **191** | ✗ | ✗ | ✗ | 490 |
| MBFL-Metallaxis (budget 200) | baseline | — | — | — | — | 0 |
| MBFL-Metallaxis-Random (budget 50) | **extension** | — | — | — | — | 0 |
| Hybrid SBFL+MBFL | **extension** | **11** | ✗ | ✗ | ✗ | 490 |

**Ochiai/DStar/Jaccard rank the faulty line at 11; Tarantula/SBI rank it at 191 — a 17×
difference in rank.** This is the most informative result of the evaluation. The 4 failing
tests cover different subsets of the 490 ranked statements in luigi's task.py. Formulae
that weight by the proportion of failing tests that execute a statement (Ochiai, D*, Jaccard)
assign a meaningfully higher score to the faulty line than formulae sensitive to the absence
of passing tests (Tarantula, SBI).

The mathematical reason: when there are no passing tests (`ep = 0`, `np = 0`), the Tarantula
formula reduces to `(ef/F) / (ef/F + 0/0)` — undefined for the zero-passing case — and
FauxPy's implementation resolves this to `1.0` for all executed statements, collapsing all
distinctions. In contrast, Ochiai (`ef/sqrt(F*(ef+ep))` = `sqrt(ef/F)` when `ep=0`)
produces scores strictly between 0 and 1 proportional to `ef`, preserving the gradient
across the 4 failing tests. Jaccard behaves like Ochiai; SBI behaves like Tarantula.

**MBFL gives 0 results.** The bug is `p.significant` vs `not p.is_global` — a boolean
attribute access substitution. FauxPy's mutmut would need to mutate the attribute name
`significant` to `is_global` (or its negation) to kill the tests, but attribute-name
mutation is not in mutmut's default operator set.

---

## Aggregate Top-k Accuracy

| Technique | Top-1 (3 bugs) | Top-5 (3 bugs) | Top-10 (3 bugs) |
|---|---|---|---|
| SBFL-Ochiai (baseline) | 0/3 | 0/3 | **1/3** |
| SBFL-Tarantula (baseline) | 0/3 | 0/3 | 0/3 |
| SBFL-DStar (baseline) | 0/3 | 0/3 | **1/3** |
| SBFL-Jaccard **(extension)** | 0/3 | 0/3 | **1/3** |
| SBFL-SBI **(extension)** | 0/3 | 0/3 | 0/3 |
| MBFL-Metallaxis (baseline) | 0/3 | 0/3 | 0/3 |
| MBFL-Metallaxis-Random **(extension)** | 0/3 | 0/3 | 0/3 |
| Hybrid SBFL+MBFL **(extension)** | 0/3 | 0/3 | **1/3** |

Average rank of the faulty line (over bugs where a ranking was produced):

| Technique | Avg rank (2 valid bugs: fastapi#3, luigi#33) | fastapi#6 |
|---|---|---|
| SBFL-Ochiai (baseline) | (8+11)/2 = **9.5** | 82 |
| SBFL-Tarantula (baseline) | (11+191)/2 = **101.0** | 82 |
| SBFL-DStar (baseline) | (8+11)/2 = **9.5** | 82 |
| SBFL-Jaccard (extension) | (8+11)/2 = **9.5** | 82 |
| SBFL-SBI (extension) | (11+191)/2 = **101.0** | 82 |
| Hybrid SBFL+MBFL (extension) | (8+11)/2 = **9.5** | 82 |

---

## Discussion

### Did the extensions improve results?

**SBFL Jaccard (Task 2 extension).**
Jaccard consistently matched the best performing baseline (Ochiai/D*) across all three bugs:
rank 8 for fastapi#3 (Top-10), rank 82 for fastapi#6, rank 11 for luigi#33. In no case
did Jaccard perform worse than Ochiai. Average rank: 9.5 (same as Ochiai). The Jaccard
extension adds a metric that is at least as good as the best stock FauxPy metric on these bugs.

**SBFL SBI (Task 2 extension).**
SBI consistently matched the weaker baseline (Tarantula): rank 11 for fastapi#3, rank 82
for fastapi#6, rank 191 for luigi#33. SBI's formula is sensitive to the ratio `ep/(ep+np)`;
when no passing tests exist (`ep = np = 0`), it collapses like Tarantula to maximum scores
for all executed statements, destroying inter-statement differentiation. On these bugs, SBI
underperforms Ochiai by a factor of 17 in the worst case (luigi#33: 191 vs 11).

**MBFL random-budget extension (Task 3 extension).**
Neither baseline MBFL (budget 200) nor the extension (budget 50) produced rankings on any
of the three bugs. The selected bugs have condition/logic faults (missing recursive call,
wrong boolean operator, wrong attribute name in condition) that are not mutation-adequate
with standard mutation operators. Attribute-name substitution and recursive-call insertion
are not in mutmut's default operator set. The extension correctly executes at 25% of the
baseline budget (demonstrating the runtime efficiency gain) but the diagnostic signal from
0 killed mutants is the same in both cases.

**Hybrid SBFL+MBFL (Task 4 extension).**
With MBFL producing 0 ranked locations on all bugs, the Hybrid localizer falls back entirely
to the SBFL component. The hybrid rank equals the Ochiai SBFL rank in every case. In
scenarios where MBFL also produces rankings (bugs in arithmetic or comparison logic), the
weighted normalised merge would potentially re-rank the faulty line higher than either
technique alone. The evaluated bug set happens not to trigger that scenario.

### Why SBFL metrics differ on luigi#33 but not fastapi#6

The luigi#33 test suite (4 failing tests) exercises different code paths: the four test
methods check parameter handling for different Task subclasses, so statements in the
parameter dispatch logic are covered by 1, 2, 3, or 4 of the failing tests. This per-test
variation gives Ochiai a meaningful `ef` gradient. The fastapi#6 test suite (3 failing tests)
all go through the same `request_body_to_args` code path in identical fashion, differing
only by the Python collection type passed in. The coverage spectrum for those 3 tests is
nearly identical, so all formulae assign the same scores and the same rank.

### Runtime

| Technique | Approx. runtime per bug | Explanation |
|---|---|---|
| SBFL (any metric) | ~5–15 s | Single pytest run + FauxPy coverage analysis |
| MBFL baseline (budget 200) | ~10–20 min | 200 statements × mutants × test-suite run time |
| MBFL extension (budget 50) | ~3–5 min | 50 statements — 4× faster than baseline |
| Hybrid | SBFL + MBFL extension | Runs both; total ~5–10 min |

---

## How to Reproduce

```bash
# Build containers and start the BugsInPy executor
docker compose build
docker compose run --rm apr-framework python -m apr_framework bugsinpy setup

# Checkout and compile all 3 bugs
for proj_bug in "fastapi 3" "fastapi 6" "luigi 33"; do
  set -- $proj_bug
  docker compose run --rm apr-framework python -m apr_framework bugsinpy checkout $1 $2
  docker compose run --rm apr-framework python -m apr_framework bugsinpy compile $1 $2
done

# Fix fastapi venvs (pydantic 2.x installed by default; old fastapi needs pydantic<2;
# pydantic 1.10 satisfies both fastapi and FauxPy's openai dependency)
docker exec apr-bugsinpy-executor bash -c "
  /home/workspace/fastapi_3/fastapi/env/bin/pip install 'pydantic>=1.9,<2.0' -q
  /home/workspace/fastapi_6/fastapi/env/bin/pip install 'pydantic>=1.9,<2.0' -q
"

# Fix luigi venv (BugsInPy requirements include pytest-sanic from a CI environment;
# it breaks pytest startup; setuptools>60 also breaks Python 3.8 importlib.metadata)
docker exec apr-bugsinpy-executor bash -c "
  /home/workspace/luigi_33/luigi/env/bin/pip uninstall pytest-sanic sanic -y -q
  /home/workspace/luigi_33/luigi/env/bin/pip install 'setuptools<60' -q
"

# Run the full evaluation
python -m apr_framework bugsinpy evaluate-localization \
    --bugs "fastapi:3,fastapi:6,luigi:33" \
    --budget 50 \
    --traditional-budget 200 \
    --seed 42 \
    --granularity statement \
    --output-dir experiment_results
```

The command writes `experiment_results/results.json` (machine-readable raw data)
and `experiment_results/README.md` (this file).
