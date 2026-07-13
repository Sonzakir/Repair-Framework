# CHUNKS — Assignment 5, Task 3: Context Retrieval for LLM Repair

Four self-contained chunks, each written to be handed to a **separate** Claude Code
session. Implement them **in order** (A → B → C → D); later chunks depend on earlier
ones. Every chunk restates the shared conventions below so it can be executed alone.

---

## Shared conventions & constraints (apply to EVERY chunk)

- **Method decomposition — read like pseudocode.** Top-level methods are a short
  sequence of well-named calls; each distinct responsibility becomes a helper whose
  *name alone* states what it does. No umbrella nouns (`context`, `setup`, `state`,
  `handler`, `process`, `env`).
- **No vague abbreviations** — banned: `op`, `src`, `cls`, `val`, `arg`, `tmp`,
  `res`, `obj`, `cfg`, `ctx`, `msg`. Write the full word.
- **No single-letter locals** outside tight math/index loops.
- **Typed suffixes:** counts end `_count`; `Path` vars end `_path`; path strings end
  `_path_str`/`_str`; test-run results end `_run_result`/`_result`; collections of
  domain objects name adjective+noun.
- **Boolean methods** start `is_`/`has_`/`can_`; **factories/builders** start
  `build_`/`create_`/`make_`; other methods are verb phrases.
- **No "Task-3"/"Assignment-5" labels inside `.py` files** (docstrings/comments
  included). Such references are allowed **only** in README/`docs/`.
- **Backward compatibility:** when `--retrieval-budget 0` (the default), prompts,
  conversations, and `repair_results.json` must be **byte-for-byte unchanged**.
- **Docker end-to-end is mandatory** to accept the change — `pytest` alone is NOT
  sufficient (per `CLAUDE.md`). Only Chunk D runs the authoritative Docker check.

## Feature overview (read once, applies to all chunks)

Give the LLM repair backend the ability to **request codebase context before
generating a patch**. The model may emit `RETRIEVE: <tool>("<name>")`; the framework
parses it, runs static analysis over the checked-out project, appends the result as a
conversation turn, and lets the model continue. The loop ends when the model stops
retrieving (ready to patch) or the **retrieval budget** is exhausted.

**Key architectural decision — retrieval is a PRE-PHASE, not an extension of the
iterative loop.** Both the single-shot path (`_generate_patches_for_location`) and the
iterative path (`_run_conversation_for_location`) get their messages from the single
`_build_location_prompt` method in `repair/llm/algorithm.py`. Retrieval hooks in there:
after the initial `[system, user]` messages are built and **before** they are returned,
a bounded RETRIEVE loop appends `assistant(RETRIEVE …)` / `tool(result)` turns. Both
downstream paths consume the enriched messages, so retrieval works with single-shot,
iterative, or neither — fully orthogonal to `--iterative`.

The retrieval loop is **RETRIEVE-only**: it never emits the final patch. When the model
replies with no RETRIEVE command (ready to patch), the loop stops and that reply is
discarded; the existing generate/iterative path then asks for the patch on the enriched
conversation (cost: ≤1 extra LLM call per location — inherent to the text protocol).

Three tools (static analysis over `checkout.worktree`):
- `get_function_definition(name)` — source of a named function/method.
- `get_class_definition(name)` — source of a named class.
- `find_usages(name)` — `(file, line, snippet)` reference sites.

CLI: single `--retrieval-budget N` on the `repair` subparser. `N>0` enables retrieval
with that step budget; `N=0` (default) disables. LLM-technique only (ignored under
`--technique template`). Config field `LLMRepairConfig.retrieval_budget: int = 0`.

---

## CHUNK A — Retrieval core (no algorithm/config/CLI changes)

**Goal:** the retrieval tools, protocol parser, loop, domain models, prompt file, and
offline tests. Fully testable alone with a fixture project + a fake LLM client. Read
the "Shared conventions" and "Feature overview" above before starting.

**Reference implementations to mirror (read first):**
- `src/apr_framework/repair/llm/prompt_builder.py` — `extract_function_source`
  (ast.walk over `FunctionDef`/`AsyncFunctionDef`) and `load_system_prompt`.
- `src/apr_framework/repair/run_loop.py` — precedent for a loop function living
  OUTSIDE the algorithm so it is unit-testable.
- `src/apr_framework/repair/llm/client.py` — `LLMClient` interface
  (`complete(messages)->str`, `completion_count`).

**Tasks:**

1. **`core/models.py`** — add:
   - `@dataclass RetrievalStep`: `tool_name: str`, `argument: str`,
     `result_summary: str` (truncated tool output stored for the JSON record).
   - `@dataclass RetrievalTrace`: `steps: list[RetrievalStep] = field(default_factory=list)`,
     `stop_reason: str = ""` (one of `"model_ready"`, `"budget_exhausted"`,
     `"parse_error"`), plus a `step_count` property returning `len(self.steps)`.

2. **`repair/llm/retrieval_tools.py`** — static analysis over `checkout.worktree`
   (`CheckoutResult`), each returning a formatted, length-capped string; never raise:
   - `get_function_definition(function_name, checkout) -> str` — ast.walk every `*.py`
     under the worktree for `FunctionDef`/`AsyncFunctionDef` named `function_name`;
     return source slice(s) with a `# <relpath>:<lineno>` header. Multiple matches →
     concatenate (bounded). No match → a clear "not found" string.
   - `get_class_definition(class_name, checkout) -> str` — same for `ClassDef`.
   - `find_usages(symbol_name, checkout) -> str` — collect `(relpath, line, snippet)`
     reference sites (ast `Name`/`Attribute`/`Call`, or a bounded grep fallback);
     return a capped list.
   - `execute_retrieval_command(retrieve_command, checkout) -> str` — dispatcher on
     `retrieve_command.tool_name`; unknown tool → error string.
   - Private `_truncate_for_prompt(...)` so no tool blows the token budget. Skip
     virtualenv / `__pycache__` / test-cache directories when walking.

3. **`repair/llm/retrieval_protocol.py`**:
   - `@dataclass(frozen=True) RetrieveCommand`: `tool_name: str`, `argument: str`.
   - `parse_retrieve_command(assistant_text) -> RetrieveCommand | None` — regex
     `RETRIEVE:\s*(get_function_definition|get_class_definition|find_usages)\(\s*["']([^"']+)["']\s*\)`.
     Returns `None` when no command is present (model ready to patch). Parse only the
     **first** command per turn.
   - `build_retrieval_result_message(retrieve_command, result_text) -> dict[str, str]`
     — the `{"role": "user", ...}` turn carrying tool output back to the model.

4. **`repair/llm/retrieval_loop.py`**:
   - `run_retrieval_loop(llm_client, messages, checkout, retrieval_budget) -> RetrievalTrace`.
     Loop up to `retrieval_budget` times: `complete(messages)` →
     `parse_retrieve_command`. `None` → stop (`stop_reason="model_ready"`), discard the
     reply. A command → `execute_retrieval_command`, append `assistant(reply)` + the
     tool-result turn, record a `RetrievalStep`. Budget hit →
     `stop_reason="budget_exhausted"`. Mutates `messages` in place; returns the trace.

5. **`repair/llm/prompts/retrieval_instructions.txt`** — a user-message section telling
   the model it MAY emit `RETRIEVE: get_function_definition("name")` (and the other two
   tools) to fetch context before patching, that it will receive the result and may
   retrieve again, and that when ready it should output the patch as usual.

6. **`tests/test_llm_context_retrieval.py`** (no network) — a `tmp_path` fixture project
   with a couple of functions/classes/usages:
   - each tool finds the right definition/usages and formats output; missing symbol →
     graceful "not found"; output is truncated.
   - `parse_retrieve_command` accepts all three tools + both quote styles; returns
     `None` for a plain patch reply; ignores malformed commands.
   - `run_retrieval_loop` with a fake client: honors budget, stops on `model_ready`,
     records correct `RetrievalStep`s + `stop_reason`, appends turns to `messages`.
   - Register the three new modules in `tests/test_imports.py`.

**Done when:** `pytest tests/test_llm_context_retrieval.py -q` and full `pytest tests/`
are green. No changes to `algorithm.py`, `config.py`, `parser.py`, `app.py`, or
`repair_runner.py` in this chunk.

---

## CHUNK B — Algorithm wiring (depends on A)

**Goal:** wire the retrieval pre-phase into the LLM repair algorithm and config so it
runs when `--retrieval-budget > 0`, with the trace stashed on each patch candidate.
Chunk A (`retrieval_loop.run_retrieval_loop`, `RetrievalTrace`, the prompt file) must
already exist. Read the "Shared conventions" and "Feature overview" above.

**Reference (read first):** `src/apr_framework/repair/llm/algorithm.py` — especially
`_build_location_prompt` (~line 666), `_LocationPrompt`, `_generate_patches_for_location`,
`_run_conversation_for_location`; `repair/llm/config.py`; `repair/llm/prompt_builder.py`
(`build_repair_prompt`).

**Tasks:**

1. **`repair/llm/prompt_builder.py`** — add `retrieval_instructions: str | None = None`
   kwarg to `build_repair_prompt`, rendered by a new
   `_build_retrieval_instructions_section` inserted before the task section. The
   rendered prompt must be **byte-identical when `retrieval_instructions is None`**.

2. **`repair/llm/config.py`** — add `retrieval_budget: int = 0`; validate `>= 0` in
   `__post_init__`. Eager-load `retrieval_instructions.txt` (via `load_system_prompt`)
   only when `retrieval_budget > 0` (fail fast on a missing file).

3. **`repair/llm/algorithm.py`**:
   - In `__init__`, load the retrieval-instruction text once when
     `repair_config.retrieval_budget > 0`.
   - Add `retrieval_trace: RetrievalTrace | None = None` to `_LocationPrompt`.
   - In `_build_location_prompt`: pass `retrieval_instructions=` into
     `build_repair_prompt` when enabled; then, when `retrieval_budget > 0`, call
     `run_retrieval_loop(self._llm_client, messages, checkout, retrieval_budget)` to
     enrich `messages` and capture the trace; store it on the returned `_LocationPrompt`.
   - In both `_generate_patches_for_location` and `_run_conversation_for_location`,
     stash `prepared_prompt.retrieval_trace` onto each produced
     `PatchCandidate.metadata["retrieval_trace"]`.
   - Do **not** add a new counter — retrieval `complete()` calls already increment
     `client.completion_count`, surfaced by `llm_query_count()`.

**Done when:** full `pytest tests/` is green; with `retrieval_budget=0` the prompt and
behavior are unchanged (add/keep a test asserting the byte-identical prompt).

---

## CHUNK C — Runner serialization + CLI (depends on A + B)

**Goal:** surface the retrieval trace in `repair_results.json` and add the CLI flag.
Read the "Shared conventions" and "Feature overview" above.

**Reference (read first):** `src/apr_framework/evaluation/repair_runner.py` (find the
per-patch serializer, e.g. `_serialise_result`, and note how it filters metadata such
as `patched_source`/`raw_test_output`); `src/apr_framework/cli/parser.py` (the `repair`
subparser); `src/apr_framework/cli/app.py` (`LLMRepairConfig` construction, the
`_build_repair_config_data` helper, and the repair start-log line).

**Tasks:**

1. **`evaluation/repair_runner.py`** — in the per-patch serializer, when
   `metadata["retrieval_trace"]` is present, emit a `retrieval` object:
   `{"steps": [{tool_name, argument, result_summary}, ...], "step_count": N,
   "stop_reason": "..."}`. Absent when retrieval was off (default output unchanged).
   Match the serializer's existing shape/filtering conventions.

2. **`cli/parser.py`** (`repair` subparser) — add `--retrieval-budget` (`type=int`,
   default `0`); help text: `0 = disabled`, LLM-technique only.

3. **`cli/app.py`** — thread `args.retrieval_budget` into `LLMRepairConfig`; record it
   in `_build_repair_config_data`; log the effective budget in the repair start line.
   Ignored under `--technique template`.

**Done when:** full `pytest tests/` is green; a local dry run of the `repair` command
parses `--retrieval-budget` without error.

---

## CHUNK D — Docs + mandatory Docker end-to-end (depends on A + B + C)

**Goal:** documentation and the authoritative Docker verification with committed
artifacts. Read the "Shared conventions" and "Feature overview" above.

**Tasks:**

1. **`docs/task5/Implementation5_3.md`** — in the style of `Implementation5_1.md` /
   `Implementation5_2.md`: goal; the pre-phase seam and why it's orthogonal to
   iterative; the three tools; the RETRIEVE protocol; budget/trace recording; the new
   `retrieval` JSON block; a debugging checklist; exact Docker commands.

2. **`README.md`** — add an "Assignment 5 — Task 3" subsection (summary + usage
   example) and add `--retrieval-budget` to the `repair` command reference.

3. **Mandatory Docker end-to-end** (per `CLAUDE.md` — `pytest` alone is NOT enough):
   - `docker compose build`; ensure `black#1` is checked out/compiled
     (`bugsinpy test black 1`).
   - Run:
     ```bash
     docker compose run --rm apr-framework python -m apr_framework repair \
       --project black --bug 1 --technique llm --retrieval-budget 3 \
       --model gpt-5.4 --llm-base-url https://api.openai.com/v1 \
       --llm-api-key-env OPENAI_API_KEY --temperature 1
     ```
   - Confirm `runs/run_NNN/repair_results.json` contains a `retrieval` block with the
     tools called + `step_count`, and that the execution log shows RETRIEVE turns.
   - Run **once without** `--retrieval-budget` and confirm the output is unchanged.
   - Commit the run artifacts.

**Done when:** both Docker runs behave as described and their artifacts are committed.