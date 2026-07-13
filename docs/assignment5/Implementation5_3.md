# Implementation Notes — Assignment 5, Task 3: Context Retrieval for LLM Repair

This document explains the context-retrieval pre-phase added to the LLM repair backend.
The goal is to make repair prompts less static: before producing a patch, the model can
ask for focused codebase information such as a function definition, class definition, or
usage sites.

---

## 1. Goal

The previous LLM repair path built one prompt from the suspicious location, the enclosing
function, optional failing-test evidence, and optional few-shot examples. That is often
enough for small local bugs, but some fixes require knowing how a symbol is used outside
the immediate function.

Task 3 adds a bounded retrieval loop:

1. build the normal repair messages,
2. optionally let the model emit `RETRIEVE: <tool>("<name>")`,
3. execute the static-analysis tool over the checked-out BugsInPy worktree,
4. append the retrieval result to the conversation,
5. repeat until the model is ready or the retrieval budget is exhausted,
6. pass the enriched conversation to the existing patch-generation path.

When `--retrieval-budget 0` is used, which is the default, the prompt and behavior remain
unchanged.

---

## 2. Files touched / added

| File | Change |
|---|---|
| `src/apr_framework/core/models.py` | Added `RetrievalStep` and `RetrievalTrace`. |
| `src/apr_framework/repair/llm/retrieval_protocol.py` | Parses `RETRIEVE:` commands and builds tool-result turns. |
| `src/apr_framework/repair/llm/retrieval_tools.py` | Static-analysis tools backed by `ast` and bounded text scanning. |
| `src/apr_framework/repair/llm/retrieval_loop.py` | Bounded pre-phase loop that mutates the messages list in place. |
| `src/apr_framework/repair/llm/prompts/retrieval_instructions.txt` | Prompt section describing the available retrieval protocol. |
| `src/apr_framework/repair/llm/prompt_builder.py` | Optional retrieval-instructions section before the task section. |
| `src/apr_framework/repair/llm/config.py` | Added `retrieval_budget`, validated as nonnegative. |
| `src/apr_framework/repair/llm/algorithm.py` | Runs retrieval from `_build_location_prompt` and stores traces on candidates. |
| `src/apr_framework/evaluation/repair_runner.py` | Serializes per-patch `retrieval` blocks in `repair_results.json`. |
| `src/apr_framework/cli/parser.py` | Added `repair --retrieval-budget`. |
| `src/apr_framework/cli/app.py` | Threads the CLI value into `LLMRepairConfig`, config JSON, and logs. |
| `tests/test_llm_context_retrieval.py` | Offline tests for tools, protocol, loop, prompt compatibility, and serialization. |
| `tests/test_imports.py` | Added the new modules to smoke-import coverage. |

---

## 3. Pre-phase insertion point

Retrieval is implemented as a pre-phase, not as another branch of the iterative repair
loop. The important insertion point is:

```python
LLMRepairAlgorithm._build_location_prompt(...)
```

Both LLM paths already call this method:

- `_generate_patches_for_location(...)` for single-shot repair,
- `_run_conversation_for_location(...)` for iterative repair.

That means retrieval is orthogonal to `--iterative`. Enabling retrieval enriches the
initial conversation before either downstream path asks for a patch.

This placement avoids duplicating retrieval logic and keeps the patch-generation and
validation paths unchanged.

---

## 4. Retrieval tools

The tools operate over `CheckoutResult.worktree` and never intentionally raise to the
caller. Bad files are skipped; tool-level failures are returned as short error strings.
All outputs are capped so one result cannot dominate the prompt.

| Tool | Behavior |
|---|---|
| `get_function_definition(name)` | Walks every Python file under the worktree with `ast` and returns matching `FunctionDef` / `AsyncFunctionDef` source slices. Methods are included because `ast.walk` sees them as function nodes. |
| `get_class_definition(name)` | Returns matching `ClassDef` source slices, including attributes and methods inside the class body. |
| `find_usages(name)` | Collects bounded reference sites from `ast.Name`, `ast.Attribute`, and `ast.Call`; unparsable files fall back to a bounded line scan. |

Definition results are formatted like:

```text
# package/module.py:42
def helper(value):
    return value + 1
```

Usage results are formatted like:

```text
Usages of "helper" (up to 50):
package/module.py:84: result = helper(item)
```

Skipped directories include common caches and environments such as `.venv`,
`__pycache__`, `.pytest_cache`, `.tox`, `build`, `dist`, and `site-packages`.

---

## 5. RETRIEVE protocol

The prompt section tells the model it may return exactly one command:

```text
RETRIEVE: get_function_definition("name")
RETRIEVE: get_class_definition("name")
RETRIEVE: find_usages("name")
```

`parse_retrieve_command(...)` accepts single or double quotes and parses only the first
supported command in a model reply. If the model returns no supported command, the
retrieval loop stops and the reply is discarded. The existing patch-generation call then
asks for the patch using the enriched messages.

This is intentional: the retrieval loop is RETRIEVE-only. It does not consume a final
patch. The cost is at most one extra LLM call per location when the model decides it is
ready without using the whole budget.

Stop reasons:

| Stop reason | Meaning |
|---|---|
| `model_ready` | The model returned no `RETRIEVE:` command. |
| `budget_exhausted` | The configured number of retrieval steps was used. |
| `parse_error` | The model appeared to request retrieval but used malformed syntax. |

---

## 6. Budget and trace recording

The CLI flag is:

```bash
--retrieval-budget N
```

`0` disables retrieval and is the default. Positive values enable retrieval for LLM
repair only. Template repair ignores the flag.

Each produced LLM `PatchCandidate` receives:

```python
patch_candidate.metadata["retrieval_trace"] = RetrievalTrace(...)
```

The trace is kept out of serialized `metadata` and emitted as a dedicated per-patch
block instead.

---

## 7. Result JSON

When retrieval is off, no `retrieval` key is written.

When retrieval is on, each serialized candidate carrying a trace gains:

```json
"retrieval": {
  "steps": [
    {
      "tool_name": "find_usages",
      "argument": "helper",
      "result_summary": "package/module.py:84: result = helper(item)"
    }
  ],
  "step_count": 1,
  "stop_reason": "model_ready"
}
```

`result_summary` is truncated separately from the prompt text so JSON artifacts stay
small and readable.

---

## 8. Debugging checklist

- If retrieval never runs, check `config.json` for `"retrieval_budget": 0`.
- If a command is ignored, inspect the model reply in `metadata.llm_response` or prompt
  dumps. The accepted forms require `RETRIEVE: tool("name")`.
- If a tool returns no result, confirm the symbol name is exact and the checkout path is
  the real project root under `.workspace/bugsinpy/<project>_<bug>/<project>`.
- If a result is too long, look for `[truncated after ... characters]`; this is expected.
- If `repair_results.json` has no `retrieval` block, confirm at least one patch candidate
  was generated from a prompt whose retrieval budget was positive.
- Use `APR_LLM_DEBUG_PROMPT=stderr` or a directory path to inspect the messages after
  retrieval-result turns are appended.

---

## 9. Verification commands

Offline tests:

```bash
.venv/bin/python -m pytest tests/test_llm_context_retrieval.py -q
.venv/bin/python -m pytest tests/ -q
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
  --retrieval-budget 3 \
  --model gpt-5.4 \
  --llm-base-url https://api.openai.com/v1 \
  --llm-api-key-env OPENAI_API_KEY \
  --temperature 1
```

Then inspect the newest `runs/run_NNN/repair_results.json` and
`runs/run_NNN/execution.log`. For a run that generated candidates, the JSON should
contain per-patch `retrieval` blocks and the log should show the retrieval stop reason.

Compatibility check:

```bash
docker compose run --rm apr-framework python -m apr_framework repair \
  --project black \
  --bug 1 \
  --technique llm \
  --model gpt-5.4 \
  --llm-base-url https://api.openai.com/v1 \
  --llm-api-key-env OPENAI_API_KEY \
  --temperature 1
```

With the flag omitted, `retrieval_budget` is `0`, no retrieval instructions are inserted,
and no `retrieval` block is serialized.
