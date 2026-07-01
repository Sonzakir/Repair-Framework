# CHUNKS.md — LLM Repair Backend (Assignment 4, Task 1)

This file divides the Task 1 implementation into self-contained chunks. Each chunk has a
clear goal, a precise file scope, and a definition of "done" so it can be reviewed and
tested before the next chunk begins.

---

## Design decisions (agreed in discussion)

**Provider-agnostic algorithm.** `LLMRepairAlgorithm` owns prompting and patch parsing.
All provider-specific communication lives in `LLMClient` subclasses. Adding a new provider
means only a new `LLMClient` subclass.

**Prompt construction is delegated to `PromptBuilder`.** The algorithm calls a helper; it
does not inline prompt logic. This keeps `generate_patches()` readable and makes Task 2
(context enrichment) a matter of extending `PromptBuilder`, not editing the algorithm.

**Shared `apply_patch_and_validate` helper (Option B).** Patch *application* is
backend-specific; test *execution* and file *restoration* are shared infrastructure.
Template repair owns its own apply-restore logic (unchanged). New backends — starting with
LLM — use the shared helper from `repair/patch_applier.py`. Design rationale documented
in README.

**`repair()` override for future iterative mode.** For Task 1, `repair()` delegates to
`run_validation_loop` (same as template repair). `LLMRepairConfig` has an `iterative` flag
(default `False`) as a documented hook for Task 3. When Task 3 is implemented,
`LLMRepairAlgorithm.repair()` will be overridden to run a feedback loop; `generate_patches()`
and `validate_patch()` remain untouched.

---

## File map

```
src/apr_framework/repair/
    patch_applier.py              # Chunk 4 — shared apply+validate helper
    llm/
        __init__.py               # Chunk 5
        config.py                 # Chunk 1
        client.py                 # Chunk 1
        prompt_builder.py         # Chunk 2
        patch_extractor.py        # Chunk 3
        algorithm.py              # Chunk 5
src/apr_framework/cli/
    parser.py                     # Chunk 6 (additions to existing file)
    app.py                        # Chunk 6 (additions to existing file)
```

---

## Chunk 1 — `LLMRepairConfig` and `LLMClient`

**Files:** `repair/llm/config.py`, `repair/llm/client.py`, `repair/llm/__init__.py` (stub)

**Goal:** Define the configuration dataclass and the provider abstraction with its first
concrete implementation (`OpenAICompatibleClient`). After this chunk you can instantiate
a client and make a raw completion call against GPT@RUB.

### `LLMRepairConfig` (`repair/llm/config.py`)

```python
@dataclass
class LLMRepairConfig:
    model_name: str
    temperature: float = 0.8
    max_patch_count: int = 5          # LLM calls per suspicious location
    top_n_locations: int = 3          # how many ranked locations to attempt
    llm_provider: str = "openai-compatible"
    base_url: str | None = None       # None → use GPT_AT_RUB_DEFAULT_BASE_URL constant
    api_key_env_var: str = "GPT_AT_RUB_API_KEY"
    timeout_seconds: int = 120
    # Task 3 hook — must be False for Task 1; overriding repair() is not implemented yet
    iterative: bool = False
    max_iterations: int = 5
```

`__post_init__` validates:
- `temperature` in `[0.0, 2.0]`
- `max_patch_count >= 1`
- `top_n_locations >= 1`
- `llm_provider` is one of the registered names (currently only `"openai-compatible"`)
- raises `ConfigurationError` for any violation

### `LLMClient` ABC (`repair/llm/client.py`)

```python
class LLMClient(ABC):
    @abstractmethod
    def complete(self, messages: list[dict[str, str]]) -> str:
        """Send a messages list and return the response text."""
```

Single method. The messages list follows the OpenAI format
(`[{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]`).

### `OpenAICompatibleClient(LLMClient)` (`repair/llm/client.py`)

- Constructor accepts `LLMRepairConfig`.
- `GPT_AT_RUB_DEFAULT_BASE_URL` module-level constant holds the GPT@RUB endpoint URL.
  `config.base_url` overrides it when provided.
- API key is read from `os.environ` at call time (not at construction) so the env var
  can be set after the object is built. Raises `ConfigurationError` if the var is absent.
- Uses `openai.OpenAI(base_url=..., api_key=...)`.
- Calls `client.chat.completions.create(model=..., messages=..., temperature=..., stream=False)`.
  Streaming is explicitly disabled (GPT@RUB does not support it).
- Returns `response.choices[0].message.content` as a string.
- Wraps `openai.OpenAIError` in `APRFrameworkError` with a clear message.

**Dependency:** Add `openai` to `pyproject.toml` under `[project] dependencies`.

**Done when:** A standalone script can instantiate `OpenAICompatibleClient` and call
`complete([{"role": "user", "content": "Say hello."}])` against GPT@RUB successfully.

---

## Chunk 2 — `PromptBuilder`

**Files:** `repair/llm/prompt_builder.py`

**Goal:** Given a `RankedLocation` and the checkout worktree path, extract the buggy
function/region from the source file and produce the ready-to-send messages list. After
this chunk you can generate a prompt from any FL output without touching an LLM.

### Code extraction

```python
def extract_function_source(
    source_file_path: Path,
    target_line: int,
) -> tuple[str, int, int]:
```

- Parses the file with `ast.parse`.
- Walks `ast.FunctionDef` and `ast.AsyncFunctionDef` nodes.
- Finds the *smallest* enclosing function that contains `target_line` (handles nested
  functions by preferring the innermost match).
- Returns `(function_source_text, start_line, end_line)` — 1-indexed, inclusive.
- Fallback: if no enclosing function is found, returns a ±25 line window around
  `target_line` (clamped to file bounds). `start_line` and `end_line` are set to the
  window bounds. This case is logged at WARNING level.
- Raises `ConfigurationError` if the file cannot be read or parsed.

### Prompt assembly

```python
def build_repair_prompt(
    location: RankedLocation,
    function_source_text: str,
    function_start_line: int,
    *,
    # Optional kwargs — unused in Task 1, wired up in Task 2
    failing_test_source: str | None = None,
    error_traceback: str | None = None,
    fl_score_annotation: bool = False,
) -> list[dict[str, str]]:
```

Returns an OpenAI-style messages list with two entries.

**System message content:**
```
You are an automated program repair tool. Your task is to fix a bug in a Python program.
You will be given the buggy code region and the fault location identified by a fault
localization tool. Return ONLY the corrected version of the provided function inside a
Python fenced code block (```python ... ```). Do not include any explanation, commentary,
or code outside the fenced block. Do not change the function signature.
```

**User message content** (assembled in order):

1. **Fault location section:**
   ```
   ## Fault Location
   File: <location.file_path>
   Suspicious line: <location.line> (rank <location.rank>, score <location.score:.4f>)
   ```

2. **Buggy code section** — the extracted function with line numbers prefixed:
   ```
   ## Buggy Code (lines <start>–<end>)
   ```python
   <start>  def foo(...):
   <start+1>     ...
   <N>  -->  <suspicious line, marked with -->
   ...
   ```
   The suspicious line is marked with ` -->` so the model can locate it at a glance.

3. **Instruction:**
   ```
   ## Task
   Fix the bug at line <location.line>. Return the corrected function in a Python fenced
   code block. Keep the fix minimal — change as few lines as necessary.
   ```

**Design rationale (for README):** Requesting a full corrected function (not a raw diff)
is more robust — the model is less likely to produce malformed diffs, and we generate the
diff ourselves via `difflib`. Prefixing lines with line numbers and marking the suspicious
line helps the model reason about which code to change. The minimal-edit instruction
reduces unnecessary refactoring.

**Extensibility note:** The optional kwargs (`failing_test_source`, `error_traceback`,
`fl_score_annotation`) are the Task 2 enrichment slots. They are present but no-op in
Task 1, so Task 2 only needs to pass values through — not change the signature.

**Done when:** `build_repair_prompt` returns a well-formed messages list for a real
`RankedLocation` from a checked-out BugsInPy project, and the output visually makes sense
when printed.

---

## Chunk 3 — `PatchExtractor`

**Files:** `repair/llm/patch_extractor.py`

**Goal:** Turn an LLM response string into a unified diff string ready for
`PatchCandidate.diff_text`. After this chunk the full generation pipeline (Chunks 1–3)
can be exercised end-to-end without running any tests.

### Main function

```python
def extract_patch_from_llm_response(
    llm_response_text: str,
    source_file_path: Path,
    function_start_line: int,
    function_end_line: int,
) -> str | None:
```

**Steps:**

1. **Extract fenced code block.**
   - Search for ` ```python ... ``` ` first; fall back to ` ``` ... ``` ` if not found.
   - Use a regex that is tolerant of leading/trailing whitespace around the fences.
   - If no fenced block is found, log a WARNING and return `None`.

2. **Validate Python syntax.**
   - Call `ast.parse` on the extracted text.
   - If `SyntaxError`, log a WARNING with the error and return `None`.

3. **Reconstruct the full file.**
   - Read original lines from `source_file_path`.
   - Replace lines `[function_start_line-1 : function_end_line]` (0-indexed slice) with
     the extracted function lines.
   - The result is a list of strings representing the patched file.

4. **Generate unified diff.**
   - Call `difflib.unified_diff(original_lines, patched_lines, fromfile=..., tofile=...)`.
   - Convert to a single string with `"".join(...)`.
   - If the diff is empty (LLM returned identical code), log a WARNING and return `None`.

5. Return the diff string.

Returns `None` for any failure mode. The algorithm treats `None` as a failed generation
attempt — it is logged and skipped, never counted toward the validated-patch budget.

**Done when:** Given a manually constructed LLM response string containing a corrected
function, `extract_patch_from_llm_response` returns a valid unified diff that can be
inspected with `patch --dry-run`.

---

## Chunk 4 — Shared `apply_patch_and_validate` helper

**Files:** `repair/patch_applier.py`

**Goal:** Provide the shared "apply → run tests → restore" infrastructure that all new
repair backends use. Template repair is NOT changed; this helper is introduced for LLM
repair and documented as the intended pattern going forward.

### Design decision (document in README)

> Patch *application* is backend-specific — each backend provides its own `apply_fn` and
> `restore_fn` callables. Patch *validation* (test execution, regression check, file
> restoration guarantee) is shared infrastructure in `repair/patch_applier.py`. New
> backends should use this helper rather than duplicating the try/finally logic.

### Function signature

```python
def apply_patch_and_validate(
    apply_fn: Callable[[], None],
    restore_fn: Callable[[], None],
    adapter: BugsInPyAdapter,
    checkout: CheckoutResult,
    regression_context: RegressionContext,
    timeout_seconds: int,
) -> tuple[bool, TestRunResult]:
    """
    Apply a patch, run the test suite, restore the file unconditionally.

    Calls apply_fn(), then runs the failing tests via adapter. File is always
    restored via restore_fn() even if tests crash, timeout, or raise an exception.

    Returns:
        (is_plausible, test_run_result)
        is_plausible is True only when the test run passes AND no regression is
        detected, matching the plausibility definition used by template repair.
    """
```

**Implementation notes:**
- `apply_fn()` and `restore_fn()` are zero-argument callables; the caller closes over
  whatever state they need (file paths, original content, etc.).
- `restore_fn()` is called inside a `finally` block — restoration is unconditional.
- `is_plausible` logic mirrors `template/validator.py`: trigger tests pass AND (if
  `regression_context` is active) no previously-passing test regresses.

**Done when:** The function can be called with a trivial apply/restore pair (e.g. write
a no-op file and restore it) and returns `(True, test_run_result)` if the test suite
passes.

---

## Chunk 5 — `LLMRepairAlgorithm`

**Files:** `repair/llm/algorithm.py`, `repair/llm/__init__.py`, `repair/__init__.py`

**Goal:** The main algorithm class that assembles Chunks 1–4. After this chunk, the LLM
backend is a fully working `RepairAlgorithm` that can be driven by the existing
`RepairEvaluationRunner` without any further changes.

### Constructor

```python
class LLMRepairAlgorithm(RepairAlgorithm):
    def __init__(
        self,
        localization_result: LocalizationResult,
        adapter: BugsInPyAdapter,
        repair_config: LLMRepairConfig,
        llm_client: LLMClient,
    ) -> None:
```

`llm_client` is injected — not constructed internally — so tests can substitute a stub.
`repair_config` is required (no default); callers must be explicit.

### `name` property

Returns `"llm-repair"`.

### `generate_patches(bug, checkout)`

For each location in `localization_result.ranked_locations[:repair_config.top_n_locations]`:

1. Resolve the source file path (extract `_resolve_source_file_path` from
   `TemplateRepairAlgorithm` into a shared private helper, or duplicate — see note below).
2. Call `extract_function_source(source_file_path, location.line)` → `(function_source_text, start_line, end_line)`.
3. Call `build_repair_prompt(location, function_source_text, start_line)` → `messages`.
4. Repeat `repair_config.max_patch_count` times:
   a. Call `llm_client.complete(messages)` → `llm_response_text`.
   b. Call `extract_patch_from_llm_response(llm_response_text, source_file_path, start_line, end_line)` → `diff_text_or_none`.
   c. If `None`: log WARNING, continue to next attempt.
   d. If valid: construct `PatchCandidate`:
      - `patch_id`: `f"llm-{location.rank}-{attempt_index}"` (unique, traceable)
      - `summary`: `f"LLM patch for {location.file_path}:{location.line} (attempt {attempt_index+1})"`
      - `diff_text`: the unified diff string
      - `metadata`: `{"location_rank": location.rank, "location_score": location.score, "llm_response": llm_response_text, "model": repair_config.model_name}`

Appends all valid `PatchCandidate` objects across all locations to one list and returns it.

**Note on `_resolve_source_file_path`:** `TemplateRepairAlgorithm` has `_resolve_source_path`
as a private method. For now, duplicate this logic inside `LLMRepairAlgorithm` rather than
making it a module-level utility — it is small and the two backends may diverge. Add a
TODO comment flagging this as a candidate for extraction if a third backend appears.

### `validate_patch(bug, checkout, patch_candidate)`

1. Parse the target file path from `patch_candidate.diff_text` (first `--- ` line of the diff).
2. Read the original file content into `original_file_content` (bytes).
3. Define `apply_fn`: write the patched file content (apply the diff using `patch`
   subprocess or Python's `difflib`-based reverse — see implementation note).
4. Define `restore_fn`: write `original_file_content` back to disk.
5. Obtain or establish the regression baseline lazily (same pattern as template repair).
6. Call `apply_patch_and_validate(apply_fn, restore_fn, adapter, checkout, regression_context, repair_config.timeout_seconds)`.
7. Build and return `RepairAttemptResult`:
   - `status=RepairStatus.PLAUSIBLE` if `is_plausible`, else `RepairStatus.FAILED`
   - `validation_summary`: include patch_id, passed/failed counts from `test_run_result`

**Implementation note on diff application:** Use `subprocess.run(["patch", "-p1", ...],
input=patch_candidate.diff_text, ...)` inside the checkout worktree. This is the most
reliable option for applying unified diffs; no Python library required. Capture stderr for
error reporting.

### `repair(bug, checkout)` — Task 1

```python
def repair(self, bug, checkout):
    outcome = run_validation_loop(
        self, bug, checkout,
        budget=self._repair_config.budget,
        stop_on_first=self._repair_config.stop_on_first,
    )
    return outcome.summary, outcome.all_results
```

Identical pattern to `TemplateRepairAlgorithm.repair()`. When Task 3 is implemented,
this method will be overridden for iterative mode; the ABC and `generate_patches` /
`validate_patch` are unchanged.

### Exports

Update `repair/llm/__init__.py`:
```python
from .algorithm import LLMRepairAlgorithm
from .config import LLMRepairConfig
from .client import LLMClient, OpenAICompatibleClient
__all__ = ["LLMRepairAlgorithm", "LLMRepairConfig", "LLMClient", "OpenAICompatibleClient"]
```

Update `repair/__init__.py` to add `LLMRepairAlgorithm` and `LLMRepairConfig` to imports
and `__all__`.

**Done when:** `LLMRepairAlgorithm` can be instantiated with a stub `LLMClient` that
returns a hardcoded response, and `generate_patches()` returns at least one valid
`PatchCandidate` for a checked-out BugsInPy bug.

---

## Chunk 6 — CLI wiring

**Files:** `cli/parser.py`, `cli/app.py`

**Goal:** Expose the LLM backend via `--technique llm` and route CLI arguments through
to `LLMRepairAlgorithm`. After this chunk the complete end-to-end command works.

### New flags in `parser.py` (added to the `repair` subcommand)

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--technique` | str | `"template"` | Extended to accept `"llm"` as a valid value |
| `--llm-provider` | str | `"openai-compatible"` | `LLMClient` implementation to use |
| `--model` | str | `"codestral-22b"` | LLM model name passed to the client |
| `--temperature` | float | `0.8` | Sampling temperature |
| `--max-candidates` | int | `5` | Max patch candidates generated per suspicious location |
| `--llm-base-url` | str | `None` | Override the API endpoint (defaults to GPT@RUB constant) |
| `--llm-api-key-env` | str | `"GPT_AT_RUB_API_KEY"` | Name of the env var holding the API key |

### Routing in `app.py` — `handle_repair()`

After the localization block (which is unchanged), replace the hard-coded
`TemplateRepairAlgorithm(...)` construction with a branch:

```python
if args.technique == "llm":
    algorithm = _build_llm_algorithm(args, localization_result, adapter)
elif args.technique == "template":
    algorithm = TemplateRepairAlgorithm(...)
else:
    raise ConfigurationError(f"Unknown repair technique: {args.technique!r}")
```

Add a new private helper (same pattern as `_build_ranker`):

```python
def _build_llm_algorithm(
    args,
    localization_result: LocalizationResult,
    adapter: BugsInPyAdapter,
) -> LLMRepairAlgorithm:
    from apr_framework.repair.llm import (
        LLMRepairAlgorithm, LLMRepairConfig, OpenAICompatibleClient
    )
    repair_config = LLMRepairConfig(
        model_name=args.model,
        temperature=args.temperature,
        max_patch_count=args.max_candidates,
        top_n_locations=args.top_n,
        llm_provider=args.llm_provider,
        base_url=args.llm_base_url,
        api_key_env_var=args.llm_api_key_env,
        timeout_seconds=args.timeout,
    )
    llm_client = OpenAICompatibleClient(repair_config)
    return LLMRepairAlgorithm(
        localization_result=localization_result,
        adapter=adapter,
        repair_config=repair_config,
        llm_client=llm_client,
    )
```

Update `config_data` written to `config.json` to include LLM-specific fields when
`args.technique == "llm"` (model, temperature, max_candidates, provider).

The rest of `handle_repair()` — `RunWriter`, `RepairEvaluationRunner`, summary printing —
is untouched. The LLM backend conforms to `RepairAlgorithm` and slots in identically.

### Example CLI invocation (for README)

```bash
python -m apr_framework repair \
    --project black \
    --bug 1 \
    --technique llm \
    --model codestral-22b \
    --fl-mode perfect \
    --max-candidates 3 \
    --temperature 0.8
```

**Done when:** The above command runs end-to-end inside Docker, produces a `run_NNN`
directory with `config.json`, `repair_results.json`, and at least one logged LLM API call.

---

## Dependency order

```
Chunk 1 (LLMRepairConfig + LLMClient)
    │
    ├── Chunk 2 (PromptBuilder)       ← no new imports, uses core models only
    │
    ├── Chunk 3 (PatchExtractor)      ← no new imports, stdlib only
    │
    └── Chunk 4 (patch_applier)       ← uses existing adapter/checkout/regression

All four feed into:
    Chunk 5 (LLMRepairAlgorithm)
        │
        └── Chunk 6 (CLI wiring)
```

Chunks 1–4 are independent of each other and can be implemented in any order. Chunk 5
requires all four to be done. Chunk 6 requires Chunk 5.
