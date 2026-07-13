# Implementation Notes — Assignment 5, Task 1: LLM-based Fault Localization

This document explains the LLM-based fault-localization (LLM-FL) backend added for
Assignment 5, Task 1. It is written to help you **read, debug, and refactor** the
code later, so it covers not just *what* was built but *why* each decision was made,
where the tricky parts are, and how to exercise it end-to-end.

---

## 1. Goal and the one hard constraint

Task 1 asks for a fault localizer that uses an LLM instead of FauxPy's SBFL/MBFL, and
that returns results in **exactly** the Assignment-2 format so it is a drop-in
replacement anywhere in the pipeline.

That constraint drove the whole design: the new backend implements the existing
`FaultLocalizer` ABC and emits ordinary `RankedLocation` objects. Nothing downstream
(run writer, reporting, evaluation, repair) had to change to consume it.

```python
# src/apr_framework/localization/base.py  (unchanged interface we conform to)
class FaultLocalizer(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def localize(self, bug, checkout, test_result=None) -> LocalizationResult: ...
```

The mental model: **LLM-FL is just a different *source* of `RankedLocation`s** — like
`PerfectFaultLocalizer`, which reads the developer fix instead of running an analysis.

---

## 2. Files touched / added

| File | Change |
|---|---|
| `src/apr_framework/localization/llm.py` | **New.** The whole backend: config, localizer, source selection, response parsing. |
| `src/apr_framework/localization/prompts/fl_prompt1.txt` | **New.** System prompt instructing strict-JSON output. |
| `src/apr_framework/localization/__init__.py` | Export `LLMFaultLocalizer`, `LLMLocalizationConfig`. |
| `src/apr_framework/repair/llm/client.py` | Added `LLMConnectionConfig` Protocol; decoupled `OpenAICompatibleClient` from the *repair* config. |
| `src/apr_framework/cli/parser.py` | `--backend {fauxpy,llm}` + LLM connection flags on `localize`. |
| `src/apr_framework/cli/app.py` | Refactored `localize` dispatch into `_build_localizer_and_config_data`. |
| `tests/test_llm_fault_localization.py` | **New.** 16 offline unit tests. |
| `tests/test_imports.py` | Added the new module to the smoke-import list. |

---

## 3. Reusing the LLM transport without coupling to *repair*

The Assignment-4 client (`OpenAICompatibleClient`) already handles everything we need:
key-read-at-call-time, `stream=False` (GPT@RUB requirement), the 60 req/min rate
limit, error wrapping, and completion counting. We reuse it.

The only obstacle was that it was typed against `LLMRepairConfig`. Localization should
not depend on a *repair* config full of irrelevant fields (`budget`, `max_patch_count`,
`iterative`, …). So the client now depends on a **narrow structural Protocol** —
exactly the four fields it actually reads:

```python
# src/apr_framework/repair/llm/client.py
@runtime_checkable
class LLMConnectionConfig(Protocol):
    model_name: str
    temperature: float
    base_url: str | None
    api_key_env_var: str

class OpenAICompatibleClient(LLMClient):
    def __init__(self, connection_config: LLMConnectionConfig) -> None:
        self._connection_config = connection_config
        ...
```

**Why a Protocol (structural) instead of a shared base class?** `LLMRepairConfig`
already has those four attributes, so it satisfies the Protocol with **zero changes** —
no risky edits to the working repair path. The new `LLMLocalizationConfig` satisfies it
too. The client is now genuinely task-agnostic.

> **Refactor note:** if you ever add a non-OpenAI client, keep it depending on
> `LLMConnectionConfig`, not on either concrete config. The attribute was renamed
> `_repair_config → _connection_config` inside the client — grep for that if you touch it.

---

## 4. The config

```python
# src/apr_framework/localization/llm.py
@dataclass
class LLMLocalizationConfig:
    model_name: str
    temperature: float = 0.0            # low = stable ranking; gpt-5.* needs 1.0
    base_url: str | None = None         # None -> GPT@RUB default
    api_key_env_var: str = "GPT_AT_RUB_API_KEY"
    llm_provider: str = "openai-compatible"
    system_prompt_name: str = "fl_prompt1"
    top_n: int | None = None
    max_source_lines: int = 400         # cap on numbered source shown to the model
    source_window_lines: int = 40       # context lines above/below each anchor
    timeout_seconds: int = 120          # for the single trigger-test run
```

The first four fields *are* the `LLMConnectionConfig` Protocol, so an instance is passed
straight to `OpenAICompatibleClient`. `__post_init__` validates ranges and, importantly,
**loads the prompt file eagerly** so a bad `--fl-system-prompt` fails immediately rather
than after the (slow) trigger-test run.

---

## 5. The localizer — read it as pseudocode

`localize()` is deliberately a short sequence of well-named calls; open the helpers only
if you need the detail.

```python
def localize(self, bug, checkout, test_result=None) -> LocalizationResult:
    failing_test_source, error_traceback = self._gather_failure_evidence(checkout)
    source_sections = self._select_source_sections(checkout, error_traceback)
    messages = self._build_localization_messages(
        source_sections, failing_test_source, error_traceback
    )
    response_text = self._client.complete(messages)
    known_relative_paths = [rel for rel, _ in source_sections]
    ranked_locations = parse_llm_fl_response(
        response_text, known_relative_paths, self._config.top_n
    )
    return self._build_localization_result(
        bug, ranked_locations, source_sections, error_traceback, response_text
    )
```

Note `test_result` is accepted (ABC compatibility) but **ignored** — the localizer runs
its own trigger test to get a fresh traceback, exactly like `PerfectFaultLocalizer`
ignores it. The localizer takes the **benchmark adapter** in its constructor for that
one test run.

### 5.1 Failure evidence — reused, not reinvented

```python
def _gather_failure_evidence(self, checkout):
    from apr_framework.repair.llm.context_enricher import build_failing_test_context
    failure_context = build_failing_test_context(
        self._adapter, checkout, enabled=True, timeout=self._config.timeout_seconds
    )
    return failure_context.failing_test_source, failure_context.error_traceback
```

`build_failing_test_context` (from the Assignment-4 repair side) already runs the trigger
test once on the unpatched checkout and returns the failing-test source + a trimmed
traceback. We reuse it verbatim. The import is **lazy** (inside the method) so importing
the `localization` package doesn't drag in the Docker/benchmark stack.

> **Layering note:** this makes `localization/` import from `repair/llm/`. That is a
> deliberate, accepted minor inversion (repair normally depends on localization). If a
> grader objects, the fix is mechanical: move `traceback_utils` + the failing-test-source
> extraction into a neutral module and have both sides import from there.

---

## 6. Source selection — the part that actually matters

This is where the real engineering is, and where you should look first if results ever
look wrong.

### 6.1 Why traceback frames alone are not enough

The obvious approach is "show the model the source files in the traceback." That works
for bugs whose failure is an **exception thrown from the source**. It **fails** for
**assertion-style** bugs.

Concrete example — `black#1`: the test patches `black.ProcessPoolExecutor` to raise
`OSError` and asserts the CLI still succeeds. The bug is that the source doesn't catch
that `OSError`. But the failure the test reports is an **assertion** on an exit code, so
the traceback contains only the *test* frame — `black.py` never appears. A traceback-only
localizer sees only `tests/test_black.py` and (correctly, given what it saw) blames test
lines. That was the first end-to-end run (`runs/run_259`).

### 6.2 The fix: symbol-anchored source windows

We combine two signals:

1. **Traceback frames** — project files/lines in the traceback (good for exceptions).
2. **Test-referenced symbols** — the symbols the *failing test method* patches/mocks.
   These are the dependencies the test deliberately manipulates to trigger the bug, so
   their **usage sites in the source** are the fault region.

```python
def _select_source_sections(self, checkout, error_traceback):
    lines_of_interest_by_file = self._collect_project_frames(checkout.worktree, error_traceback)
    self._augment_with_test_referenced_source(lines_of_interest_by_file, checkout.worktree)
    ...
    # render each file as numbered windows around its lines of interest,
    # non-test source first, capped by max_source_lines.
```

For `black#1` this anchors on `ProcessPoolExecutor`, which occurs at `black.py:5, 615,
621` — and **621 is the exact ground-truth buggy line**.

### 6.3 The two subtle traps I hit (read this before refactoring selection)

Both traps are about *noise burying the real anchor past the line budget*:

**Trap 1 — anchoring on too many symbols.** My first version anchored on every
`module.attr` access and every imported name. For a 6,000-line file that produced 40+
anchors spanning the whole file; the ±40 windows merged into one huge block, and the
400-line budget got consumed *before* reaching line 621. **Fix:** anchor **only on
patched/mocked symbols** (`patch("black.ProcessPoolExecutor")`), which is the highest-
signal, lowest-noise cue.

**Trap 2 — reading patches from the whole test file.** A test file has hundreds of
methods, each patching different things. Collecting patch targets from all of them
re-introduced the flood (`CACHE_DIR`, `dump_to_file`, `out`, …). **Fix:** scope patch
extraction to the **failing test method's AST node only** (decorators included):

```python
# Scope patch-target extraction to the *failing* test method only.
failing_method_node = _find_function_node(parsed_test, test_method_name)
patch_search_root = failing_method_node or parsed_test
for node in ast.walk(patch_search_root):
    if isinstance(node, ast.Call) and _is_patch_like_call(node):
        targeted_symbols.update(_patch_target_symbols(node, local_name_to_module_file))
```

After both fixes: `black#1` anchors reduce to `{ProcessPoolExecutor}` → `black.py:[5,
615, 621]` → ~132 windowed lines (well under the 400 budget) → **621 always shown**.

> **Debugging tip:** the fastest way to see what the model was shown is the
> `files_shown` field in the run's `results.json` metadata, plus `raw_llm_response`.
> If `files_shown` contains only the test file, symbol anchoring found nothing — check
> that (a) the failing test actually patches a project symbol, and (b) the patched
> module resolves to a file under the worktree (`_resolve_module_source_file`).

### 6.4 Rendering: line-numbered windows

Each selected file is rendered as **line-numbered** windows (`  621| ...`) so the model
can cite exact line numbers, with merged/elided windows and a global cap:

```python
def _render_numbered_windows(source_file_path, lines_of_interest, window_lines, max_lines):
    # merge overlapping ±window intervals, emit "NNNNN| <code>" lines,
    # separate non-adjacent regions with "     | ...", stop at max_lines.
```

Non-test source is rendered **before** test source (`_non_test_source_first`) so the
budget favours the actual bug region.

---

## 7. Prompt and response parsing

The system prompt (`localization/prompts/fl_prompt1.txt`) tells the model to think
step-by-step and then emit **only** a JSON array, most-suspicious first:

```json
[{"file": "src/pkg/module.py", "line": 42, "reason": "off-by-one in slice bound"}]
```

Parsing is defensive — a fault localizer must never crash on a chatty model:

```python
def parse_llm_fl_response(response_text, known_relative_paths, top_n) -> list[RankedLocation]:
    parsed_entries = _extract_json_array(response_text)   # whole reply, ```fence```, or [ ... ]
    if parsed_entries is None:
        logger.warning("LLM-FL: could not parse a JSON array ...")
        return []                                          # empty, never raises
    ...
```

Design choices worth knowing:

- **Score is synthetic and rank-based** (`1.0, 0.99, 0.98, …`), matching
  `PerfectFaultLocalizer`. For FL only the *ordering* matters (Top-k), so a synthetic
  score keeps ordering deterministic without trusting a model-invented confidence.
- **Path normalization** (`_normalize_returned_file`): the model's path is matched
  against the paths we actually showed it (exact → strip `a/`/`b/` → longest suffix).
  Ground-truth matching downstream (`_files_match`) is already path-flexible, so this is
  belt-and-suspenders.
- **Malformed entries are skipped, not fatal** — a missing `line` or non-string `file`
  drops that one entry and keeps the rest.
- The model's `reason` is preserved in `RankedLocation.metadata["reason"]` — handy for
  Task 2 (patch assessment) and for human debugging.

---

## 8. CLI wiring

`--backend` now accepts `llm`, and the `localize` dispatch was refactored so the backend
choice is isolated in one place:

```python
def _build_localizer_and_config_data(args, family, adapter, worktree, bug_dir, started_at):
    if args.backend == "llm":
        return _build_llm_localizer_and_config_data(args, adapter, started_at)
    return _build_fauxpy_localizer_and_config_data(args, family, adapter, worktree, bug_dir, started_at)
```

**GPT@RUB vs OpenAI is not a separate backend** — both are `--backend llm`, chosen purely
by `--llm-base-url` / `--llm-api-key-env` / `--model`. The default base URL is GPT@RUB (to
stay assignment-conformant); in this project we pass OpenAI flags because we have no
GPT@RUB budget.

New flags on `localize`: `--model --temperature --llm-provider --llm-base-url
--llm-api-key-env --fl-system-prompt --max-source-lines --source-window`. The existing
`--top-n` is reused.

---

## 9. Timing / performance considerations

- **One trigger-test run per `localize`.** The dominant cost besides the API call is
  running the failing test once (in the executor container) to capture the traceback.
  It is bounded by `timeout_seconds` (default 120s). We never run the *full* suite.
- **One LLM call per `localize`.** Single completion, `stream=False`. Latency is
  model-dependent (gpt-5.4 ≈ a few seconds here).
- **Prompt size is bounded** by `max_source_lines` (default 400) and
  `source_window_lines` (default 40). This is the main lever on token cost/latency. The
  symbol-anchoring design exists largely to keep the prompt *small and on-target* rather
  than dumping whole 6k-line files.
- **Rate limiting** is inherited from `OpenAICompatibleClient` (60 req/min). Irrelevant
  for a single `localize`, relevant if you batch many bugs.
- **Determinism:** `temperature=0.0` is the default for stable rankings. gpt-5.* rejects
  `0.0`, so those runs must pass `--temperature 1` (rankings then vary slightly run-to-run).

---

## 10. Debugging & refactoring checklist

- **"It ranked test lines"** → symbol anchoring found nothing. Inspect
  `results.json → metadata.files_shown`. Likely the failing test doesn't patch a project
  symbol, or the module didn't resolve to a worktree file.
- **"The buggy line wasn't shown"** → the anchor set is too large again; check
  `max_source_lines` vs. the number of anchors (`_grep_symbol_lines`) and confirm patch
  extraction is scoped to the failing method (`_find_function_node`).
- **Prompt inspection** → set `APR_LLM_DEBUG_PROMPT=stderr` (or a directory) to dump the
  exact messages sent; this is the client's built-in debug hook and is a no-op otherwise.
- **Where the LLM-FL-specific logic lives** — everything is in `localization/llm.py`.
  The class method chain (Section 5) is the map; the module-level helpers below the class
  are pure functions (easy to unit-test, which is why `tests/test_llm_fault_localization.py`
  hits them directly with no network).
- **Adding a new prompt** → drop `localization/prompts/<name>.txt` and pass
  `--fl-system-prompt <name>`. A missing name fails fast in `__post_init__`.

---

## 11. Exact CLI commands for Docker testing

All commands assume the framework is built and the bug is checked out/compiled (the repo
already has `black_1` under `.workspace/`). From the repo root:

### 11.1 Build (once, or after dependency changes)

```bash
docker compose build
```
*Expected:* the `apr-framework` image builds successfully. Source is live-mounted at
`/workspace`, so ordinary code edits do **not** require a rebuild.

### 11.2 Ensure the bug is checked out + compiled (skip if already present)

```bash
docker compose run --rm apr-framework python -m apr_framework bugsinpy test black 1
```
*Expected:* checks out and compiles `black#1`, runs its test — the trigger test
`test_works_in_mono_process_only_environment` **fails** (that is the bug). This confirms
the environment is ready for localization.

### 11.3 LLM-FL — the main Task-1 command (OpenAI / gpt-5.4)

```bash
docker compose run --rm apr-framework python -m apr_framework localize \
  --backend llm --project black --bug 1 \
  --model gpt-5.4 --llm-base-url https://api.openai.com/v1 \
  --llm-api-key-env OPENAI_API_KEY --temperature 1 --top-n 10
```
*Expected:* `Backend: llm-fl` and a ranked list led by the true fault:
```
1. black.py:621 1.0000
2. black.py:612 0.9900
3. black.py:623 0.9800
...
```
`black.py:621` (rank 1) is the exact ground-truth line; the rest cluster in the changed
`reformat_many` region. Full artifacts land in `runs/run_NNN/` (`config.json`,
`results.json` with `metadata.files_shown` + `raw_llm_response`, `execution.log`) and a
zipped report.

### 11.4 Same command against GPT@RUB (assignment default provider)

```bash
docker compose run --rm apr-framework python -m apr_framework localize \
  --backend llm --project black --bug 1 \
  --model gpt-4.1-2025-04-14 --llm-api-key-env GPT_AT_RUB_API_KEY --temperature 0
```
*Expected:* identical shape of output. Omitting `--llm-base-url` uses the GPT@RUB
endpoint by default. (Requires a funded `GPT_AT_RUB_API_KEY` and possibly VPN.)

### 11.5 Regression check — FauxPy backend still works

```bash
docker compose run --rm apr-framework python -m apr_framework localize \
  --project black --bug 1 --family sbfl --metric ochiai --top-n 5
```
*Expected:* `Backend: fauxpy`, an Ochiai-ranked list. On `black#1` SBFL ranks lines
`6311–6315` — it **misses** the fault, which is a useful contrast: on this bug LLM-FL
clearly outperforms SBFL (a data point for the Task-4 course-wide comparison).

### 11.6 Inspect the prompt that was sent (debugging)

```bash
docker compose run --rm -e APR_LLM_DEBUG_PROMPT=stderr apr-framework \
  python -m apr_framework localize --backend llm --project black --bug 1 \
  --model gpt-5.4 --llm-base-url https://api.openai.com/v1 \
  --llm-api-key-env OPENAI_API_KEY --temperature 1 --top-n 10
```
*Expected:* same ranking as 11.3, plus the full system+user messages dumped to stderr —
you can confirm `black.py` (with line 621) is in the "Source files" section.

### 11.7 Offline unit tests (no Docker, no network)

```bash
pytest tests/test_llm_fault_localization.py -q
```
*Expected:* all tests pass. These cover JSON parsing, path normalization, config
validation, CLI parsing, and — most importantly — that symbol anchoring is scoped to the
failing method and lands on the right source line.
