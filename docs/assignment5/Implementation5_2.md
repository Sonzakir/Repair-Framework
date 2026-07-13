# Implementation Notes — Assignment 5, Task 2: LLM-based Patch Assessment

This document explains the LLM-based patch assessor added for Assignment 5, Task 2.
The goal is to help future debugging: what was added, why it is separate from the
existing ranker, where the result JSON changes happen, and how to verify the path.

---

## 1. Goal

The repair pipeline already distinguishes:

1. **plausible** patches — candidates that pass the test suite, and
2. **correct** patches — plausible candidates whose diff matches the BugsInPy developer fix.

Task 2 adds a third, optional judgment: an LLM score for semantic patch quality. The
assessor receives each plausible patch, the buggy code region when available, the
candidate diff, the failing test, and the original failure traceback. It returns:

- `quality_score` in `[0, 1]`
- `assessment_rationale`
- an assessment-ranked plausible-patch list

The feature is opt-in through `repair --assess`. With assessment disabled,
`repair_results.json` stays on the previous schema.

---

## 2. Files touched / added

| File | Change |
|---|---|
| `src/apr_framework/core/models.py` | Added `PatchAssessment` and optional assessment metrics on `RepairRunMetrics`. |
| `src/apr_framework/repair/assessment/base.py` | New `PatchAssessor` ABC. |
| `src/apr_framework/repair/assessment/config.py` | `LLMAssessmentConfig`, including prompt loading and validation. |
| `src/apr_framework/repair/assessment/response_parser.py` | Defensive JSON-object parser for LLM replies. |
| `src/apr_framework/repair/assessment/llm.py` | `LLMPatchAssessor` and prompt construction. |
| `src/apr_framework/repair/assessment/prompts/assess_prompt1.txt` | System prompt for strict JSON patch judgments. |
| `src/apr_framework/evaluation/repair_runner.py` | Runs the assessor after plausibility and correctness; serializes assessment results only when enabled. |
| `src/apr_framework/cli/parser.py` | Added `--assess`, `--assess-max-patches`, and `--assess-system-prompt`. |
| `src/apr_framework/cli/app.py` | Builds the assessor from CLI flags and passes it into `RepairEvaluationRunner`. |
| `tests/test_llm_patch_assessment.py` | Offline tests for parser, config, prompt, and assessment ordering. |
| `tests/test_imports.py` | Adds assessment modules to import smoke coverage. |

---

## 3. Why a separate `PatchAssessor` ABC?

The existing `PatchRanker` is heuristic and local: it combines suspiciousness, patch
simplicity, and operator priority. The LLM assessor is different in both cost and
semantics:

- it makes network calls,
- it needs failing-test evidence,
- it produces a rationale,
- it should be usable with or without the weighted ranker.

For that reason the runner now accepts both optional collaborators:

```python
RepairEvaluationRunner(..., ranker=ranker, assessor=assessor)
```

`ranked_plausible_patches` and `assessed_plausible_patches` are written independently.
This keeps comparisons clear: generation order, heuristic rank order, and LLM
assessment order can all be inspected in the same run.

---

## 4. Prompt and response shape

The prompt asks the model to analyze internally whether the patch fixes the root cause
or merely satisfies the visible test, then output only:

```json
{"quality_score": 0.0, "rationale": "one or two concise sentences"}
```

The user message contains these sections:

1. `## Original Buggy Code` when `source_path` and `target_line` are present in patch metadata
2. `## Candidate Patch` with the unified diff
3. `## Previously Failing Test` when recoverable from `bugsinpy_run_test.sh`
4. `## Original Failure Traceback` from the unpatched trigger test
5. `## Assessment Task`

The original-code section is best-effort. Template and LLM patches already store
`source_path` and `target_line`, so `LLMPatchAssessor` uses
`extract_function_source(...)` to include the enclosing function. If extraction fails,
the diff and failing-test evidence are still enough to run assessment.

---

## 5. Defensive parsing

`parse_assessment_response(...)` never raises for malformed model output. It tries, in
order:

1. the raw stripped response,
2. each fenced code block,
3. the substring from the first `{` to the last `}`.

The first JSON object wins. Non-numeric or missing scores become `0.0`; numeric scores
are clamped to `[0, 1]`; missing rationales become `""`. A fully unparseable reply
becomes a zero-score assessment whose rationale is the raw reply.

---

## 6. Where assessment sits in the runner

`RepairEvaluationRunner._run_one_bug(...)` keeps the original order:

1. run the repair loop and collect plausible patches,
2. mark plausible patches as `CORRECT` when they match the developer fix,
3. optionally run the weighted ranker,
4. optionally run the LLM assessor,
5. serialize all views.

Assessment uses the already-mutated `RepairAttemptResult` objects, so `quality_score`
and `assessment_rationale` naturally appear inside each patch's serialized metadata.

When enabled, `repair_results.json` adds:

- `assessed_plausible_patches` — the plausible patches in assessment order, each
  patch's `metadata` carrying `quality_score` and `assessment_rationale`
- `metrics.assessment_query_count`

When disabled, these keys are not written.

The assessor operates purely on the *plausible* patch set — it scores and
re-ranks those patches by semantic quality. It deliberately does **not** emit a
"rank of first correct" metric: correctness here means an exact diff match
against the developer fix, which is orthogonal to what the assessor measures
(overfit vs. genuine fix among plausible candidates).

---

## 7. CLI

```bash
python -m apr_framework repair \
  --project black \
  --bug 1 \
  --technique llm \
  --assess \
  --assess-max-patches 3 \
  --assess-system-prompt assess_prompt1 \
  --model gpt-5.4 \
  --llm-base-url https://api.openai.com/v1 \
  --llm-api-key-env OPENAI_API_KEY \
  --temperature 1
```

The assessor reuses the repair LLM connection flags:

- `--model`
- `--temperature`
- `--llm-base-url`
- `--llm-api-key-env`
- `--llm-provider`

There is no separate assessment model flag.

---

## 8. Debugging checklist

- If `--assess` fails before any LLM call, check `--assess-system-prompt`; config
  eagerly loads `repair/assessment/prompts/<stem>.txt`.
- If the score is always `0.0`, inspect `metadata.assessment_raw_response` in
  `repair_results.json`; the model may not have returned parseable JSON.
- If the original buggy code is missing from the prompt, check that the patch metadata
  has `source_path` and `target_line`.
- Use `APR_LLM_DEBUG_PROMPT=stderr` or a directory path to inspect the exact assessment
  prompts, because assessment uses the same `OpenAICompatibleClient` prompt-dump hook.
- If `metrics.assessment_query_count` is lower than `plausible_count`, check
  `--assess-max-patches`.

---

## 9. Verification commands

Offline tests:

```bash
.venv/bin/pytest tests/test_llm_patch_assessment.py tests/test_imports.py -q
.venv/bin/pytest tests/ -q
```

Mandatory Docker path:

```bash
docker compose build
docker compose run --rm apr-framework python -m apr_framework bugsinpy setup
docker compose run --rm apr-framework python -m apr_framework bugsinpy test black 1
docker compose run --rm apr-framework python -m apr_framework repair \
  --project black \
  --bug 1 \
  --technique llm \
  --assess \
  --model gpt-5.4 \
  --llm-base-url https://api.openai.com/v1 \
  --llm-api-key-env OPENAI_API_KEY \
  --temperature 1
```

After the Docker repair run, inspect the newest `runs/run_NNN/repair_results.json`.
For a run that produced plausible patches, it should contain
`assessed_plausible_patches`, per-patch `metadata.quality_score`, per-patch
`metadata.assessment_rationale`, and `metrics.assessment_query_count`.
