# Task 4 — Implementation Walkthrough (for reading, refactoring, and changing)

This is the working document for the Task-4 code: what exists, where it lives, why it is
shaped that way, what is deliberately *not* touched, and where the rough edges are if you
want to refactor. It complements `Implementation5_4.md` (which is the "what and why" write-up
for the submission); this one is the "how, and how to change it" map.

---

## 1. What Task 4 actually required

Two things, and only two:

1. **A single command** running `LLM-FL → LLM-Repair with retrieval → LLM-Assessment`.
2. **A course-wide comparison** of the four approaches on the same bugs, with artifacts.

Tasks 1–3 already shipped every *component*. What was missing:

| Gap | Symptom |
|---|---|
| **1. `repair` could not select LLM-FL** | `--fl-mode` accepted only `auto` (FauxPy) / `perfect` (oracle). `LLMFaultLocalizer` was reachable *only* from the separate `localize` command. The "full pipeline" needed two commands chained through `--skip-localize`, which picks the newest cached run — and would happily pick up an SBFL run instead. |
| **2. No four-approach comparison existed** | Assignment-3 and Assignment-4 numbers lived in separate result files, and neither carried assessment or similarity scores. |

Everything else the single command needs (`--technique llm`, `--retrieval-budget`, `--assess`,
`--similarity-score`) already existed on the `repair` subparser, and `RepairEvaluationRunner`
already accepted `assessor=` and `score_similarity=`. So Gap 1 is small, and Gap 2 is where
the new code is.

---

## 2. File map

| File | Status | What's in it |
|---|---|---|
| `src/apr_framework/cli/parser.py` | modified, **purely additive** | `--fl-backend` + 3 LLM-FL knobs on `repair` (L954+); new `evaluate-course-comparison` subparser (L551+) |
| `src/apr_framework/cli/app.py` | modified | FL-backend plumbing + the new command's handler |
| `src/apr_framework/evaluation/course_approaches.py` | **new**, ~150 lines | The four approaches as data |
| `src/apr_framework/evaluation/course_comparison_runner.py` | **new**, ~1200 lines | The matrix runner + report renderer |
| `scripts/regenerate_course_comparison_readme.py` | **new** | Re-render the report from committed artifacts, no Docker/API |
| `tests/test_imports.py` | modified | 2 new modules in the smoke-import list |

**Not touched on purpose:** `_LLM_VARIANT_TOGGLES` and `_build_llm_algorithm_for_variant`
(`app.py`). The Assignment-4 `evaluate-llm-repair` matrix must stay retrieval-free to remain a
valid baseline. If you add retrieval there, you invalidate the A4 column.

---

## 3. Gap 1 — the FL-backend axis

### The design decision

`--fl-mode` and `--fl-backend` answer **different questions** and compose:

- `--fl-mode` → *where do locations come from — a tool, or the oracle?* (`auto` | `perfect`)
- `--fl-backend` → *which tool?* (`fauxpy` | `llm`)

The alternative — adding `llm` as a third `--fl-mode` value — would have made
`--fl-mode llm --fl-family sbfl` a syntactically valid but meaningless combination. Keeping
them orthogonal means every combination is meaningful.

### Where it lives (`cli/app.py`)

| Function | Line | Role |
|---|---|---|
| `_is_llm_fault_localization_selected(args)` | 498 | The single predicate. Uses `getattr(args, "fl_backend", "fauxpy")` so namespaces that lack the flag (e.g. `localize`) don't explode. |
| `_build_llm_fault_localizer(args, adapter)` | 937 | **Extracted** from the old `localize`-only builder. Builds `LLMLocalizationConfig` + `OpenAICompatibleClient` + `LLMFaultLocalizer`. |
| `_build_llm_localizer_and_config_data(...)` | 963 | Now just calls the above, then builds its config payload. Same signature as before. |
| `_run_llm_fault_localization_for_repair(...)` | 503 | Logs the model, localizes, logs `files_shown`. Mirrors `_run_perfect_localization_from_developer_fix`. |
| `_localize_for_repair(...)` | 453 | The precedence chain (below). |
| `_resolve_repair_fl_backend_label(args)` | 359 | `"oracle"` / `"llm-fl"` / `args.fl_family` → written as `fl_backend` in result files. |

### The precedence chain (`_localize_for_repair`, L453)

```
perfect (oracle)  →  cached (--skip-localize)  →  llm (--fl-backend llm)  →  fauxpy
```

`--fl-mode perfect` **wins** over `--fl-backend llm` (the oracle is strictly better information
than any localizer) and the run *logs a line saying so* rather than erroring — a user who
passes both gets the oracle and is told. With the default `--fl-backend fauxpy` the chain
collapses to the original three-way behavior, so every pre-existing command line is
byte-identical. This is the property to preserve if you refactor here.

### Why one builder serves three commands

The three LLM-FL knobs deliberately reuse the **same argparse dest names** on `repair` as on
`localize`: `fl_system_prompt`, `max_source_lines`, `source_window`. That's why
`_build_llm_fault_localizer(args, adapter)` can read one namespace shape and serve `localize`,
`repair`, and the matrix — no adapter layer, no duplicated construction. **If you rename a dest
on one subparser, rename it on all of them**, or the builder silently reads a default.

---

## 4. Gap 2 — the comparison

### 4a. Approaches are data (`course_approaches.py`)

```python
@dataclass(frozen=True)
class CourseApproach:
    label, column_title, technique,
    uses_llm_fault_localization, context_enrichment, iterative,
    retrieval_budget, repair_description
```

| Label | Technique | FL source | Toggles |
|---|---|---|---|
| `a3-template` | template | auto / perfect | — |
| `a4-single-shot` | llm | auto / perfect | no enrichment, no retrieval |
| `a4-iterative` | llm | auto / perfect | iterative loop, no retrieval |
| `a5-full-llm` | llm | **LLM-FL** | enrichment on, retrieval budget N |

The key rule, in **one** place (`CourseComparisonRunner._resolve_fl_modes_for_approach`, L172):
an approach with `uses_llm_fault_localization=True` has exactly **one** FL source, so it ignores
the `--fl-modes` axis and yields one cell per bug. The others yield one cell per FL mode. That's
why the matrix is 7 cells/bug, not 8.

**To add a fifth approach:** add one `CourseApproach` entry (L67) and one entry to the
`--approaches` default/help string in `parser.py`. Nothing else. `resolve_course_approaches`
(L115) validates labels against the same dict, so the CLI error message updates itself.

### 4b. The runner (`course_comparison_runner.py`)

It **only orchestrates**. Each cell is executed by the existing `RepairEvaluationRunner`, whose
constructor already took `assessor=` and `score_similarity=` — no changes were needed there.
Every cell gets its own `runs/run_NNN/` (config, log, retrieval traces, patch diffs).

```
run()                              L129   bug × approach × fl_mode; flush results.json after EVERY cell
 └─ _run_one_cell()                L180   localize → repair → read back; errors become error cells
     ├─ localization_provider(bug, approach, fl_mode)    ← injected by the CLI
     ├─ _build_cell_config_data()  L251
     ├─ RepairEvaluationRunner(assessor=assessor_factory(), score_similarity=True, ...)
     └─ _build_cell_from_run_dir_and_localization()      L279
```

Three **factories** are injected rather than constructed inside, because both the LLM client and
the assessor count their queries **on the instance** — sharing one across cells would smear
`llm_query_count` / `assessment_query_count` across the whole matrix:

- `localization_provider(bug, approach, fl_mode)`
- `repair_algorithm_factory(approach, localization_result)`
- `assessor_factory()` → fresh assessor per cell

An exception from the localization provider is caught and recorded as an **error cell**, not
propagated — one uninstallable FauxPy must not abort a 28-cell run. `results.json` is flushed
after every cell for the same reason.

### 4c. Reading metrics back

Cells are reconstructed from the cell's own `repair_results.json` by three pure summarisers
(bottom of the file — easy to unit-test in isolation):

| Summariser | Line | Reads | Produces |
|---|---|---|---|
| `_summarise_assessment_from_patches` | 995 | `assessed_plausible_patches` (already quality-sorted) | best/mean `quality_score`, rank of first correct, `is_top_patch_correct`, **`quality_score_of_first_correct`** |
| `_summarise_similarity_from_patches` | 1030 | `plausible_patches` | best/mean `context_similarity_score`, band of best |
| `_summarise_retrieval_from_patches` | 1055 | **`all_results`** | total steps, per-tool call counts, prompts that retrieved |

Note the retrieval one reads `all_results`, **not** `plausible_patches`: the retrieval happened
for every prompt, including the ones whose patch failed validation, and its cost should be
reported.

`quality_score_of_first_correct` exists specifically to detect **assessor false negatives** — a
low score on a patch that *is* the developer fix. That is the finding on tornado#14 (quality
0.12 on an exact-match patch), and the report says so out loud instead of averaging it away.

---

## 5. Why the command re-runs all four approaches

This is the design choice most worth understanding before you change anything.

The assignment's table needs only plausible/correct/time — which *could* have been loaded from
the committed A3/A4 result files. It re-runs everything instead because **the two graded metrics
cannot be reconstructed after the fact**:

- `context_similarity_score` (`repair/correctness.py`) needs `metadata["patched_source"]` to
  rebuild a reformatting-neutral diff — and `patched_source` is **deliberately stripped** from
  serialized results (`repair_runner.py::_serialise_result`) to stop every result file carrying
  whole source copies.
- The assessor needs the patch objects, not their JSON summaries.

So a table whose quality/similarity rows read `—` for three of four columns was the only
alternative, which defeats the purpose. Re-running is the only way to measure all four columns
the same way.

**Consequence you must keep in the docs:** the re-run numbers will *not* reproduce the committed
A3/A4 reports exactly (temperature 1.0). The new report is self-contained and says so; the older
reports are untouched.

**Cost lever:** `--fl-modes perfect` roughly halves the LLM spend. The auto-FL cells produced 0
plausible patches on this bug set, so they are largely a fidelity cost.

---

## 6. The report

`_build_readme` (L441) → per-bug course-wide table, per-cell audit table, four analyses.

**The collapse rule** (`_select_best_cell_for_approach`, L1115): an approach spanning
auto/perfect produces two cells but occupies one column, so the better one represents it —
**max correct → max plausible → fastest time-to-first-plausible**, annotated with the winning FL
mode (`1 (perfect)`). Errored cells lose to any successful cell. The rule is footnoted in the
report *and* every individual cell is printed underneath, so the collapse is auditable rather
than a hidden judgment.

The four analyses are generated from the cells, not hand-written:

| Analysis | Line | Notable behavior |
|---|---|---|
| `_build_llm_fl_quality_analysis` | 632 | Checks `_has_llm_fault_localization_misfired` **first** (L1083): an empty ranking is a *failure*, not a quiet zero, and must never be dressed up as "LLM-FL ran". |
| `_build_retrieval_effect_analysis` | 728 | Zero retrieval is a *result* (self-contained fault region), not a bug. |
| `_build_assessment_quality_analysis` | 780 | Reports overfitting flags, near-misses, **and assessor false negatives**; caveats "ranked first" when the cell held only one patch. |
| `_build_overall_pipeline_analysis` | 890 | Improvements and regressions vs. the best prior approach. |

---

## 7. Cheap iteration loop (use this, don't re-run the matrix)

Every matrix cell costs LLM calls and test-suite runs. To change wording, tables, or an analysis
and see the result against the **real** numbers:

```bash
python scripts/regenerate_course_comparison_readme.py
```

It reloads `experiment_results/course_comparison/results.json`, **re-derives every summary field
from the committed `run_artifacts/*/repair_results.json`** (so a newly added metric field works
without a re-run), and calls the same `write_results` the live command uses. No Docker, no API
key. This is how `quality_score_of_first_correct` was backfilled into an already-completed run.

---

## 8. Rough edges — honest list of what I'd refactor

Ordered by how much they'd bother a reviewer.

1. **`_run_evaluate_course_comparison` (app.py:1932) is ~200 lines** and duplicates the FauxPy
   localizer construction (`_build_auto_localizer`) almost verbatim from
   `_run_evaluate_llm_repair` (L1750ish). That closure is the obvious extraction: a shared
   `build_fauxpy_localizer_for_bug(args, adapter, checkouts, projects_dir)` used by both
   evaluation commands. I left it duplicated to avoid touching the A4 command, but it is
   copy-paste and should be unified.

2. **The `assessor_factory` hack.** `_build_assessor` (L881) gates on `args.assess`, so the
   course command fakes it:
   ```python
   return _build_assessor(argparse.Namespace(**{**vars(args), "assess": True}), adapter)
   ```
   Cleaner: give `_build_assessor` explicit parameters (model, temperature, base_url, prompt,
   max_patches, timeout) and let each caller decide whether to call it at all. This is the
   change I'd make first.

3. **`CourseCellResult` has ~25 flat fields.** It could be three nested dataclasses
   (`assessment` / `similarity` / `retrieval`). I kept it flat because `_write_json` emits a
   flat row and flat JSON is much easier to grep and to load into a dataframe. If you nest it,
   keep the JSON flat.

4. **`_build_per_cell_detail_tables` (L605)** scans `index.items()` inside a double loop — O(n²)
   and dependent on dict insertion order for row ordering. Fine at 28 cells; replace with an
   explicit grouping if the matrix ever grows.

5. **`replace_retrieval_budget` (course_approaches.py:145)** exists because the spec carries a
   placeholder budget (3) that the CLI then overrides. Slightly awkward. Alternative: drop
   `retrieval_budget` from the spec entirely and keep a boolean `uses_retrieval`, letting the
   algorithm builder read `args.retrieval_budget` directly.

6. **The all-zero tie in the collapse rule.** When both FL cells produce 0/0, `max()` keeps the
   first (`auto`), so the table shows `0 (auto)`. Harmless, but arguably `perfect` should be
   preferred as the more informative baseline. One line in `ranking_key` (L1136).

7. **`similarity_score` in `config.json`** was previously missing (it was set *after*
   `config.json` was written). I fixed it in `_build_repair_config_data` (L368); the late
   mutation at ~L724 is now redundant and could be removed.

---

## 9. Guardrails — things that will silently break something

- **Don't add retrieval to `_LLM_VARIANT_TOGGLES`.** It invalidates the A4 baseline column.
- **Don't rename an LLM-FL argparse dest on only one subparser.** `_build_llm_fault_localizer`
  reads them by name across three commands; a mismatch silently yields the default.
- **Don't run bare `ruff format .`** in this repo. It reformats 209 files including committed
  `.patched.py` experiment artifacts (they are *evidence*, not source). Scope it:
  `ruff format <the files you changed>`.
- **Keep the default `--fl-backend fauxpy` path byte-identical.** It is the regression contract
  for every pre-existing command line.
- **No `Task-X` / `Assignment-X` labels inside `.py` files** (project rule) — docs/README only.

---

## 10. Verification actually performed

| Check | Result |
|---|---|
| Single command, black#1 (Docker, real API) | 8 plausible; assessor separated 3 patches it flagged *"likely overfit to the mocked test"* (0.18) from genuine fixes (0.95); similarity scores emitted |
| Full 28-cell matrix (Docker, real API) | exit 0; 6 error cells (FauxPy uninstallable), all recorded not fatal |
| Regression: `repair --technique template --fl-mode perfect` (tornado#14) | still `correct` — matches the committed Iteration-3 result |
| Regression: `localize --backend llm` (black#1) | unchanged after the builder extraction; ranks `black.py:621` first |
| `pytest tests/` | 40 passed |
| `ruff check` on all touched files | clean |

Artifacts: `experiment_results/course_comparison/{results.json, README.md, run_artifacts/}`.
