# Implementation Notes — Assignment 5, Task 4: End-to-End LLM Pipeline and Course-Wide Comparison

This document explains how the three Assignment-5 components are assembled into one
LLM-driven pipeline runnable from a single command, and how the four approaches built over
the course are compared against each other on the same bugs with the same metrics.

---

## 1. Goal

Tasks 1–3 delivered three independent capabilities: an LLM fault localizer
(`localize --backend llm`), an LLM patch assessor (`repair --assess`), and a context
retrieval loop (`repair --retrieval-budget N`). They could not, however, be chained:

```text
LLM-FL  ->  LLM-Repair with retrieval  ->  LLM-Assessment
```

Task 4 closes two gaps.

**Gap 1 — `repair` could not select LLM-FL.** `--fl-mode` accepted only `auto` (FauxPy) and
`perfect` (the developer-fix oracle), and `_localize_for_repair` hard-wired the `auto`
branch to FauxPy. `LLMFaultLocalizer` was reachable only from the separate `localize`
command, so the fully LLM-driven pipeline needed two commands and an implicit dependency on
the most recent cached run.

**Gap 2 — no command produced the four-approach comparison.** Assignment 3's and
Assignment 4's numbers lived in separate result files, and neither carried the assessment or
similarity metrics.

---

## 2. Files touched / added

| File | Change |
|---|---|
| `src/apr_framework/cli/parser.py` | `repair` gains `--fl-backend {fauxpy,llm}` plus the three LLM-FL knobs (`--fl-system-prompt`, `--max-source-lines`, `--source-window`), reusing the `localize` subparser's dest names. New `bugsinpy evaluate-course-comparison` subcommand. |
| `src/apr_framework/cli/app.py` | Extracted `_build_llm_fault_localizer`; added `_run_llm_fault_localization_for_repair`, `_is_llm_fault_localization_selected`, `_resolve_repair_fl_backend_label`, an LLM branch in `_localize_for_repair`, and the `_run_evaluate_course_comparison` handler. |
| `src/apr_framework/evaluation/course_approaches.py` | **New.** The four approaches as data (`CourseApproach` + `COURSE_APPROACHES`). |
| `src/apr_framework/evaluation/course_comparison_runner.py` | **New.** `CourseComparisonRunner` — runs the matrix, reads each cell's metrics back, renders the course-wide report. |
| `tests/test_imports.py` | Both new modules added to the smoke-import list. |

---

## 3. Design: FL-backend selection is a separate axis from FL mode

`--fl-mode` answers *"where do the fault locations come from — a tool, or the oracle?"*;
`--fl-backend` answers *"which tool?"*. Overloading `--fl-mode` with a third value `llm`
would have conflated the two questions and made `--fl-mode llm --fl-family sbfl` a
nonsensical-but-accepted combination.

`_localize_for_repair` therefore resolves a four-way precedence:

```text
perfect (oracle)  ->  cached (--skip-localize)  ->  llm (--fl-backend llm)  ->  fauxpy
```

`--fl-mode perfect` wins over `--fl-backend llm` (the oracle is strictly better information
than any localizer), and the run logs a line saying so rather than failing — a user
combining both flags gets the oracle and is told. With the default `--fl-backend fauxpy`,
the precedence collapses to the original three-way behavior, so every pre-existing command
line produces byte-identical output.

The FL source that actually ran is recorded as `fl_backend` (`oracle` / `llm-fl` / the
FauxPy family) in `config.json` and `repair_results.json`, so downstream analysis can group
runs by FL source without re-deriving it from flags.

### Why one builder serves both commands

The three LLM-FL knobs use the **same argparse dest names** on the `repair` subparser as on
`localize` (`fl_system_prompt`, `max_source_lines`, `source_window`). That lets the extracted
`_build_llm_fault_localizer(args, adapter)` read one namespace shape and serve `localize`,
`repair`, and the evaluation matrix — no adapter layer, no duplicated construction.

---

## 4. Design: why the comparison re-runs all four approaches

The assignment's table asks only for plausible/correct counts and time-to-first-plausible.
Those three numbers could have been *loaded* from the committed Assignment-3 and
Assignment-4 result files. The runner re-runs everything instead, for one reason: the two
graded metrics this project cares about — **assessment quality score** and **context
similarity score** — cannot be reconstructed after the fact.

`context_similarity_score` needs `patched_source` and the original file to rebuild a
reformatting-neutral diff (`repair/correctness.py`), and `patched_source` is deliberately
stripped from the serialized JSON (it would bloat every result file with whole source
copies). The assessor likewise needs the patch objects, not their summaries. Retro-scoring
the old artifacts is therefore impossible, and a table whose quality/similarity rows read
`—` for three of four columns would defeat the purpose.

So every cell — including the Assignment-3 template cells — runs with the assessor attached
and `score_similarity=True`. All four columns are measured the same way, and the comparison
is honest. The cost is real (28 cells for 4 bugs) but the template cells only pay for
assessor calls, and `results.json` is flushed after every cell so a long run survives an
interruption.

> The re-run numbers will not match the committed Assignment-3/4 reports exactly — the LLM
> is sampled at temperature 1.0. The new report is self-contained and says so; the older
> reports are left untouched.

---

## 5. Design: approaches as data, not branches

`course_approaches.py` holds the matrix axis as a frozen dataclass list:

| Approach | Technique | FL source | Toggles |
|---|---|---|---|
| `a3-template` | template | auto / perfect | — |
| `a4-single-shot` | llm | auto / perfect | no enrichment, no retrieval |
| `a4-iterative` | llm | auto / perfect | iterative loop, no retrieval |
| `a5-full-llm` | llm | **LLM-FL** | enrichment on, retrieval budget N |

An approach that localizes with the LLM has exactly one FL source, so it ignores the
`--fl-modes` axis and contributes one cell per bug; the others are run once per requested FL
mode. That rule lives in one place (`_resolve_fl_modes_for_approach`), so the matrix shape
follows from the specs rather than from nested conditionals at the call site.

The existing `_LLM_VARIANT_TOGGLES` and `_build_llm_algorithm_for_variant` (used by
`evaluate-llm-repair`) are **untouched** — the Assignment-4 matrix must stay retrieval-free
to remain a valid baseline.

---

## 6. Runner design

`CourseComparisonRunner` mirrors `LLMRepairComparisonRunner`: it only orchestrates the
matrix. Each cell is executed by the existing `RepairEvaluationRunner`, whose constructor
already accepted `assessor=` and `score_similarity=` — no changes were needed there. Every
cell gets its own `runs/run_NNN/` (config, log, patch diffs, retrieval traces), and a
localization failure in one cell is recorded as an error cell rather than aborting the run.

A **fresh assessor and a fresh LLM client are built per cell** (via factories passed into
`run`), because both count their own queries on the instance; sharing them would smear one
cell's `llm_query_count` / `assessment_query_count` across the matrix.

Each cell's metrics are read back from its `repair_results.json` by three summarisers:

- `_summarise_assessment_from_patches` — over `assessed_plausible_patches` (already sorted by
  descending quality): best/mean `quality_score`, the rank of the first correct patch after
  assessment re-ranking, and whether the **top-assessed patch is the correct one**.
- `_summarise_similarity_from_patches` — over `plausible_patches`: best/mean
  `context_similarity_score` and the band of the best.
- `_summarise_retrieval_from_patches` — over `all_results` (not just the plausible ones: the
  retrieval happened for every prompt and its cost should be reported): total steps, per-tool
  call counts, and how many prompts retrieved anything.

---

## 7. The report

`experiment_results/course_comparison/README.md` contains, per bug, the assignment's table
with two extra rows:

```text
| | A3 (template) | A4 simple | A4 iterative | A5 full LLM |
| FL source | auto/perfect | auto/perfect | auto/perfect | LLM-FL |
| Repair | traditional | LLM | LLM (iterative) | LLM + retrieval |
| Assessment | test pass/fail | test pass/fail | test pass/fail | LLM assessor |
| Plausible patches | … | … | … | … |
| Correct patches (exact diff) | … | … | … | … |
| Best assessment quality score | … | … | … | …|   <- added
| Best context similarity score | … | … | … | …|   <- added
| Time to first plausible | … | … | … | … |
```

Columns spanning the auto/perfect axis produce two cells but occupy one column, so the
better cell represents them, chosen by **max correct → max plausible → fastest time to first
plausible**, annotated with the winning FL mode. The rule is footnoted in the report and
every individual cell is also printed in a per-cell table underneath, so the collapse is
auditable rather than a hidden judgment call.

Four discussion sections are generated from the cells: LLM-FL vs. SBFL/MBFL quality, the
effect of context retrieval, the usefulness of assessment (does the top-assessed patch
coincide with the correct one? does a low quality score flag test-suite overfitting?), and
where the full pipeline improved or regressed overall.

---

## 8. Debugging notes

- **`fl_files_shown` is the LLM-FL misfire signal.** The localizer anchors on traceback
  frames and on the symbols the failing test mocks. When that anchor set is empty, the only
  source it can show the model is the test file — and the ranking then points at test code,
  so repair targets the test instead of the bug. The runner records `fl_files_shown` per
  cell and the report calls the case out explicitly rather than burying it. If an LLM-FL
  cell produces nothing, check that field first.
- **A zero retrieval count is a result, not a bug.** With a non-zero budget the model may
  still decline to retrieve; on self-contained fault regions that is the correct call. The
  report distinguishes "retrieved nothing" from "retrieval unavailable".
- **`--fl-mode perfect --fl-backend llm`** is not an error; the oracle wins and the run logs
  why. Verify with the `fl_backend` field in `config.json` (`oracle`, not `llm-fl`).
