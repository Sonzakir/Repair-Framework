# Implementation Plan — Assignment 5, Task 2: LLM-based Patch Assessment

> On approval, this document is written to the repo as **`Implementation_Plan.md`**,
> and a companion **`CHUNKS.md`** (the same steps regrouped as self-contained
> briefs for separate Claude Code sessions) is generated from it. Task 2 itself is
> **not** implemented in this session.

---

## 1. Context

Assignment 5 Task 2 asks for an LLM component that judges the **semantic quality**
of each *plausible* patch (one that passes the test suite) — distinguishing genuine
fixes from patches that merely overfit the tests. For every plausible patch it must:

- emit a **numerical quality score (0–1)** and a **brief natural-language rationale**,
- **re-rank** the plausible patches by descending score,
- be **integrated into the evaluation runner** so results land in
  `repair_results.json` beside the existing patch metrics,
- be **selectable from the CLI** (`--assess`).

The design mirrors the successful shape of Task 1's LLM-FL backend: implement a
parallel ABC as a drop-in, reuse `OpenAICompatibleClient` through the narrow
`LLMConnectionConfig` Protocol, eager-load the prompt file in `__post_init__`, and
parse the model reply **defensively — never crash**.

## 2. Confirmed design decisions

1. **New independent `PatchAssessor` ABC** in a new `repair/assessment/` package,
   selected by `--assess`, **orthogonal to the existing `--ranker`** (the weighted
   composite ranker is untouched; both may run in the same repair run).
2. Assessment **reuses the repair connection flags** (`--model`, `--temperature`,
   `--llm-base-url`, `--llm-api-key-env`). No `--assess-model`. Only the prompt
   stem is assessment-specific.
3. **Task 2 only.** Tasks 3 (context retrieval) & 4 (end-to-end pipeline) later.
4. **Assess all plausible patches by default**, with a configurable
   `--assess-max-patches N` cap (default `None` = all).

## 3. Coding conventions & constraints (MUST hold for every step)

These are enforced in review; apply them to every name and method written.

- **Method decomposition — read like pseudocode.** Top-level methods are a short
  sequence of well-named calls; extract each distinct responsibility into a helper
  whose *name alone* states what it does. No umbrella nouns (`context`, `setup`,
  `state`, `handler`, `process`, `env`).
- **No vague abbreviations** — banned: `op`, `src`, `cls`, `val`, `arg`, `tmp`,
  `res`, `obj`, `cfg`, `ctx`, `msg`. Write the full word.
- **No single-letter locals** outside tight math/index loops.
- **Typed suffixes:** counts end `_count`; `Path` vars end `_path`; path strings
  end `_path_str`/`_str`; test-run results end `_run_result`/`_result`; collections
  of domain objects name adjective+noun (`plausible_results`, not `plausible`).
- **Boolean methods** start `is_`/`has_`/`can_`; **factories/builders** start
  `build_`/`create_`/`make_`; other methods are verb phrases describing what they
  return/do.
- **No "Task-2"/"Assignment-5" labels inside `.py` files** (docstrings/comments
  included). Such references are allowed **only** in README/`docs/`.
- **Docker end-to-end is mandatory** to accept the change — `pytest` alone is NOT
  sufficient (per `CLAUDE.md`).
- **Backward compatibility:** when `--assess` is off, `repair_results.json` and all
  existing keys are byte-for-byte unchanged.

## 4. Reused building blocks (do not reinvent)

| Need | Reuse | Location |
|---|---|---|
| LLM transport | `OpenAICompatibleClient(connection_config)`, `client.complete(messages)->str` | `repair/llm/client.py` |
| Connection typing | `LLMConnectionConfig` Protocol (4 fields) | `repair/llm/client.py` |
| Prompt loading | `load_fl_system_prompt` / `load_system_prompt` pattern | `localization/llm.py`, `repair/llm/prompt_builder.py` |
| Defensive JSON parse | `_extract_json_array` / `_json_array_candidates` (adapt to `{}`/`dict`) | `localization/llm.py` |
| Failing-test source + traceback | `build_failing_test_context(adapter, checkout, enabled=True, timeout=...)` | `repair/llm/context_enricher.py` |
| Enclosing-function source (optional enrichment) | `extract_function_source(path, line)->(text,start,end)` | `repair/llm/prompt_builder.py` |
| CLI wiring template | `_build_ranker` + `ranker=` threading | `cli/app.py` (`_run_repair_evaluation_and_write_results`) |

Per-patch data available: `PatchCandidate.diff_text` (unified diff = buggy region
`-` + fix `+`, backend-agnostic), `.summary`, `.metadata` (`patched_source` for LLM
patches; `operator`/`suspiciousness_score` for template patches).

---

## 5. Step-by-step implementation

### STEP 1 — Domain model (`core/models.py`)
- Add `@dataclass PatchAssessment` with:
  `patch_id: str`, `quality_score: float`, `rationale: str`, `raw_response: str = ""`.
- Extend `RepairRunMetrics` with two optional fields (default `None`):
  `rank_of_first_correct_by_assessment: int | None` and
  `assessment_query_count: int | None`.

### STEP 2 — Package skeleton (`repair/assessment/`)
Create `repair/assessment/__init__.py`, `base.py`, `config.py`,
`response_parser.py`, `llm.py`, `prompts/assess_prompt1.txt`.

**`base.py` — `PatchAssessor` ABC:**
```python
class PatchAssessor(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def assess(
        self,
        plausible_results: list[RepairAttemptResult],
        checkout: CheckoutResult,
        localization_result: LocalizationResult | None = None,
    ) -> list[RepairAttemptResult]:
        """Return plausible_results re-ordered by descending quality_score.
        Side effect: write `quality_score` and `assessment_rationale` into each
        assessed patch.metadata (mirrors PatchRanker's metadata-side-effect contract)."""

    def llm_query_count(self) -> int | None:
        return None
```

**`config.py` — `LLMAssessmentConfig`:** 4 connection fields **first** (so it
satisfies `LLMConnectionConfig`): `model_name`, `temperature`, `base_url`,
`api_key_env_var`; then `system_prompt_name="assess_prompt1"`,
`max_patches_assessed: int | None = None`, `timeout_seconds: int = 120`.
`__post_init__` validates ranges and **eagerly loads** the prompt (fail fast on a
bad stem), using the `load_*_system_prompt` pattern with a new
`load_assessment_system_prompt(stem)` resolving `prompts/{stem}.txt`.

### STEP 3 — Prompt (`prompts/assess_prompt1.txt`)
System prompt instructing the model to (a) reason **step-by-step** (chain-of-
thought) about whether the patch fixes the root cause vs. overfits the failing
test, then (b) output **only** a strict JSON object:
```json
{"quality_score": 0.0, "rationale": "one or two sentences"}
```
State the 0–1 scale meaning (1 = clearly correct root-cause fix; 0 = clearly
overfit/incorrect).

### STEP 4 — Response parser (`response_parser.py`)
`parse_assessment_response(response_text: str) -> PatchAssessment` (patch_id filled
by caller): adapt `_extract_json_array` to extract a JSON **object** — candidates in
order: raw stripped, each ```-fenced block, then the `{`…`}` substring; first that
`json.loads` to a `dict` wins. Clamp `quality_score` to `[0, 1]`; coerce missing/
non-numeric score to `0.0`; missing rationale → `""`. On a wholly unparseable reply,
return `quality_score=0.0`, `rationale=<raw text>` and **log a warning — never raise.**

### STEP 5 — Assessor (`llm.py`)
`LLMPatchAssessor(PatchAssessor)`, ctor `(config, client, adapter)`. `assess()` reads
like pseudocode:
```python
def assess(self, plausible_results, checkout, localization_result=None):
    if not plausible_results:
        return []
    failing_test_source, error_traceback = self._gather_failure_evidence(checkout)
    patches_to_assess = self._select_patches_within_cap(plausible_results)
    for attempt_result in patches_to_assess:
        assessment = self._assess_one_patch(attempt_result, failing_test_source, error_traceback)
        self._attach_assessment_to_patch_metadata(attempt_result, assessment)
    return self._reorder_by_descending_quality(plausible_results)
```
- `_gather_failure_evidence` reuses `build_failing_test_context` **once** per bug.
- `_assess_one_patch` calls `build_assessment_prompt(diff_text, failing_test_source,
  error_traceback)` → `self._client.complete(messages)` → `parse_assessment_response`.
- `build_assessment_prompt` assembles `[system, user]`; user sections = the unified
  diff (buggy + fix), the failing test(s) + traceback, and the assess instruction.
- `_reorder_by_descending_quality` is a **stable** sort on `quality_score`; capped/
  unassessed patches (no score) sort to the tail keeping original order.
- `llm_query_count()` returns the client-call count made during `assess`.
Export public names from `__init__.py`.

### STEP 6 — Runner integration (`evaluation/repair_runner.py`)
- `__init__`: add `assessor: PatchAssessor | None = None` → `self._assessor`.
- `_BugRunResult`: add `assessed_plausible_results: list[RepairAttemptResult] = field(default_factory=list)`.
- `_run_one_bug`, **after** the correctness loop and **independent of** the ranker
  block: if `self._assessor is not None`, call
  `assessed_plausible_results = self._assessor.assess(outcome.plausible_results, checkout, self._localization_result)`,
  compute `rank_of_first_correct_by_assessment` (1-based position of first
  `CORRECT` in that order), and set the two new `RepairRunMetrics` fields
  (`assessment_query_count = self._assessor.llm_query_count()`).
- `_serialise_bug`: when the assessor ran, add `assessed_plausible_patches`
  (each = `_serialise_result(...)` + `rank_position`) and a top-level
  `rank_of_first_correct_by_assessment`; add `assessment_query_count` to the nested
  `metrics` only when not `None`. `quality_score`/`assessment_rationale` already flow
  through `_serialise_result` via `metadata` (no serializer change needed there).
- No changes to output when `self._assessor is None`.

### STEP 7 — CLI parser (`cli/parser.py`, `repair` subparser)
Add, reusing the existing connection flags:
- `--assess` (`argparse.BooleanOptionalAction`, default `False`).
- `--assess-max-patches` (`type=int`, default `None`).
- `--assess-system-prompt` (default `"assess_prompt1"`).

### STEP 8 — CLI app wiring (`cli/app.py`)
- Add `_build_assessor(args, adapter) -> PatchAssessor | None` (mirrors
  `_build_ranker`): returns `None` unless `args.assess`; else build
  `LLMAssessmentConfig` from the reused connection flags + assess flags,
  `OpenAICompatibleClient(config)`, `LLMPatchAssessor(config, client, adapter)`.
- In `_run_repair_evaluation_and_write_results`: build the assessor beside the
  ranker, log its name, record assess flags into `config_data`
  (`_build_repair_config_data`), and pass `assessor=` into `RepairEvaluationRunner`.
- Add an assessment line to the repair summary print.
- `--assess` must work with **both** `--technique template` and `--technique llm`
  (assessor is diff-based, backend-agnostic).

### STEP 9 — Offline tests (`tests/test_llm_patch_assessment.py` + `tests/test_imports.py`)
Cover with **no network** (fake `LLMClient`): object-JSON parse (raw/fenced/bracket
+ malformed→fallback), score clamping, config validation + missing-prompt fail-fast,
`build_assessment_prompt` structure, and **re-rank ordering** (higher score first;
ties and capped patches stable). Add the new module to the `test_imports.py`
parametrization.

### STEP 10 — Docs & README
- `docs/Implementation5_2.md` in the style of `Implementation5_1.md`: goal, files
  touched, why a separate ABC (vs. `PatchRanker`), prompt/CoT rationale, defensive
  parsing, where assessment sits in the pipeline, the new JSON fields, debugging
  checklist, exact Docker commands.
- README: new "Assignment 5 — Task 2" subsection (summary + install note + usage
  example) and the `--assess*` flags added to the `repair` command reference.

### STEP 11 — Mandatory Docker end-to-end verification
- `docker compose build`; ensure `black#1` is checked out/compiled
  (`bugsinpy test black 1`).
- Run:
  ```bash
  docker compose run --rm apr-framework python -m apr_framework repair \
    --project black --bug 1 --technique llm --assess \
    --model gpt-5.4 --llm-base-url https://api.openai.com/v1 \
    --llm-api-key-env OPENAI_API_KEY --temperature 1
  ```
- Confirm `runs/run_NNN/repair_results.json` contains `assessed_plausible_patches`
  with per-patch `quality_score` + `assessment_rationale`, and a top-level
  `rank_of_first_correct_by_assessment`. Commit the run artifacts.

---

## 6. Chunk grouping for `CHUNKS.md`

Four self-contained chunks handed to separate sessions (each restates the STEP 3
conventions/constraints and its dependency):

- **Chunk A — Assessment package** (STEPS 1–5, 9): the whole `repair/assessment/`
  package + `PatchAssessment` model + offline tests. No runner/CLI. Fully testable
  alone.
- **Chunk B — Runner integration** (STEP 6): `repair_runner.py` + `RepairRunMetrics`.
  Depends on A.
- **Chunk C — CLI wiring** (STEPS 7–8): `parser.py` + `app.py`. Depends on A+B.
- **Chunk D — Docs + Docker e2e** (STEPS 10–11): `Implementation5_2.md`, README,
  authoritative Docker run + committed artifacts. Depends on A+B+C.

## 7. Verification summary

- Offline: `pytest tests/test_llm_patch_assessment.py -q` and full `pytest tests/`
  green (imports + no regressions).
- Authoritative: the Docker `repair … --assess` run on `black#1` (already cached
  under `.workspace/`, with a known Assignment-4 LLM plausible patch), inspecting
  `repair_results.json`.
