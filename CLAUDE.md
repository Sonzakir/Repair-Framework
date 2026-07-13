# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

An Automated Program Repair (APR) research framework that integrates the BugsInPy benchmark and FauxPy fault localization tool. The framework runs as a Python CLI (`python -m apr_framework`) inside Docker, controlling a sibling BugsInPy executor container via Docker-in-Docker.

## Commands

### Setup (Docker Compose — required for BugsInPy)
```bash
docker compose build
docker compose run --rm apr-framework
# Inside the container:
python -m apr_framework bugsinpy setup
```

### Local editable install (for unit tests and import checks only — no Docker needed)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

### Lint / format
```bash
pip install -e ".[dev]"
ruff format .
ruff check .
```

### Run tests
```bash
pytest tests/
# Run a single test file:
pytest tests/test_imports.py
# Run a single parametrized test by module name:
pytest "tests/test_imports.py::test_public_modules_import[apr_framework.localization.fauxpy]"
```

The only test file is `tests/test_imports.py`, which parametrizes a smoke-import check over every public module. Integration tests require Docker. CI (`.github/workflows/ci.yml`) runs `pytest -q` on Python 3.10 and 3.12 and builds the sdist/wheel — it does **not** run the Docker end-to-end path, so green CI does not satisfy the validation requirement below.

> **Validation requirement — Docker end-to-end is mandatory.** Unit tests (`pytest tests/`) are NOT sufficient to accept a change. Every change must be executed end-to-end inside the Docker container and its real results observed before the work is considered done. Build and run the framework via Docker Compose, run the affected command(s) against an actual checked-out/compiled bug, and confirm the output is correct — do not rely on import smoke tests or local reasoning alone:
> ```bash
> docker compose build
> docker compose run --rm apr-framework
> # Inside the container, exercise the actual changed path, e.g.:
> python -m apr_framework bugsinpy setup
> python -m apr_framework bugsinpy test <project> <bug_id>     # checkout + compile + run tests
> python -m apr_framework localize --project <project> --bug <bug_id> [flags exercising the change]
> ```

### CLI entry points
```bash
python -m apr_framework <command>
apr-framework <command>         # installed script alias
```

Key commands:
```bash
python -m apr_framework list-benchmarks
python -m apr_framework bugsinpy setup
python -m apr_framework bugsinpy list-projects
python -m apr_framework bugsinpy list-bugs <project>
python -m apr_framework bugsinpy checkout <project> <bug_id>
python -m apr_framework bugsinpy compile <project> <bug_id>
python -m apr_framework bugsinpy test <project> <bug_id>

# SBFL localization (default family)
python -m apr_framework localize --project <project> --bug <bug_id> \
  [--backend fauxpy] [--family sbfl] [--granularity statement|function] \
  [--metric ochiai|tarantula|dstar|jaccard|wsbi] [--wsbi-alpha ALPHA] [--top-n N] \
  [--src <pkg>] [--failing_tests "test::id"] [--test-target "test::id"] \
  [--show-raw-output]

# MBFL localization
python -m apr_framework localize --project <project> --bug <bug_id> \
  --mbfl [--granularity statement|function] \
  [--metric metallaxis|muse] [--top-n N] \
  [--mutation-strategy random] [--budget N] [--seed N]

# Hybrid localization (weighted merge of SBFL + MBFL)
python -m apr_framework localize --project <project> --bug <bug_id> \
  --family hybrid [--granularity statement|function] \
  [--sbfl-metric ochiai] [--mbfl-metric metallaxis] \
  [--sbfl-weight 0.5] [--mbfl-weight 0.5] [--top-n N]

# LLM-based localization (Assignment 5, Task 1)
python -m apr_framework localize --project <project> --bug <bug_id> \
  --backend llm [--model gpt-4.1-2025-04-14] [--temperature 0.0] [--top-n N] \
  [--llm-provider openai-compatible] [--llm-base-url https://api.openai.com/v1] \
  [--llm-api-key-env OPENAI_API_KEY] [--fl-system-prompt fl_prompt1] \
  [--max-source-lines 400] [--source-window 40]

python -m apr_framework bugsinpy evaluate-dummy --seed 123

# Template-based repair (Assignment 3)
python -m apr_framework repair --project <project> --bug <bug_id> \
  [--technique template] [--budget N] [--top-n N] \
  [--operators arith,comp,obo,bool,negate,return] [--timeout N] \
  [--stop-on-first] [--no-regression-check] \
  [--fl-mode auto|perfect] [--fl-family sbfl|mbfl|hybrid] \
  [--localization-metric ochiai] [--mbfl-metric metallaxis] \
  [--skip-localize] [--granularity statement|function] \
  [--ranker weighted|none] [--ranker-weights w1,w2,w3] \
  [--similarity-score | --no-similarity-score] \
  [--runs-dir runs]

# Full LLM pipeline in one command (Assignment 5, Task 4):
# LLM-FL -> LLM repair with context retrieval -> LLM assessment
python -m apr_framework repair --project <project> --bug <bug_id> \
  --technique llm --fl-backend llm --retrieval-budget 3 --assess --similarity-score \
  --model gpt-5.4 --temperature 1.0 \
  --llm-base-url https://api.openai.com/v1 --llm-api-key-env OPENAI_API_KEY

# Course-wide comparison of all four approaches (Assignment 5, Task 4)
# auto-FL-capable bugs (black) take --fl-modes auto,perfect; bugs FauxPy cannot
# localize (tornado:14, scrapy:2) take --fl-modes perfect so no phantom auto cell is scored
python -m apr_framework bugsinpy evaluate-course-comparison \
  [--bugs black:1,black:3] \
  [--approaches a3-template,a4-single-shot,a4-iterative,a5-full-llm] \
  [--fl-modes auto,perfect] [--retrieval-budget 3] \
  [--model gpt-5.4] [--temperature 1.0] \
  [--output-dir experiment_results/course_comparison] [--runs-dir runs]

# Store an LLM API key in the local .env (interactive prompt)
python -m apr_framework configure [--llm-api-key-env OPENAI_API_KEY]

# LLM-based repair (Assignment 4)
# Requires: export OPENAI_API_KEY="<key>"  (or run `configure` above)
python -m apr_framework repair --project <project> --bug <bug_id> \
  --technique llm \
  [--model gpt-4.1-2025-04-14] [--temperature 0.8] [--max-candidates 5] \
  [--llm-provider openai-compatible] [--llm-base-url https://api.openai.com/v1] \
  [--llm-api-key-env OPENAI_API_KEY] [--system-prompt prompt1] \
  [--context-enrichment | --no-context-enrichment] [--few-shot N] \
  [--iterative | --no-iterative] [--max-iterations 5] \
  [--budget N] [--top-n N] [--timeout N] \
  [--stop-on-first] [--no-regression-check] \
  [--fl-mode auto|perfect] [--fl-family sbfl|mbfl|hybrid] \
  [--localization-metric ochiai] [--mbfl-metric metallaxis] \
  [--ranker weighted|none] [--ranker-weights w1,w2,w3] \
  [--similarity-score | --no-similarity-score] \
  [--runs-dir runs]

# Repair evaluation matrix (Task 5): each bug x {auto, perfect} FL + ranker
python -m apr_framework bugsinpy evaluate-repair \
  [--bugs project:id,project:id,...] [--fl-modes auto,perfect] \
  [--fl-family sbfl|mbfl|hybrid] [--localization-metric ochiai] \
  [--operators ...] [--budget N] [--top-n N] [--ranker weighted|none] \
  [--output-dir experiment_results/repair] [--runs-dir runs]
# Multi-technique localization evaluation (compares SBFL/MBFL/Hybrid against ground truth)
python -m apr_framework bugsinpy evaluate-localization \
  [--bugs black:1,black:3,black:7] [--granularity statement|function] \
  [--budget N] [--seed N] [--top-ks 1,5,10] \
  [--output-dir experiment_results]

# LLM repair evaluation matrix (Task 5): bugs x {single-shot, context-enriched, iterative} x {auto, perfect}
python -m apr_framework bugsinpy evaluate-llm-repair \
  [--bugs black:1,tornado:14,scrapy:2,fastapi:3] \
  [--variants single-shot,context-enriched,iterative] \
  [--fl-modes auto,perfect] \
  [--model gpt-5.4] [--temperature 1.0] \
  [--llm-provider openai-compatible] [--llm-base-url https://api.openai.com/v1] \
  [--llm-api-key-env OPENAI_API_KEY] [--system-prompt prompt1] \
  [--max-candidates 3] [--top-n 3] [--max-iterations 5] \
  [--budget 200] [--timeout 120] \
  [--fl-family sbfl|mbfl|hybrid] [--localization-metric ochiai] [--mbfl-metric metallaxis] \
  [--mutation-budget 50] [--seed 0] [--granularity statement|function] \
  [--stop-on-first] [--no-regression-check] \
  [--ranker weighted|none] [--ranker-weights w1,w2,w3] \
  [--output-dir experiment_results/llm_repair/task5] [--runs-dir runs]
```

`--test-target` is repeatable (`action="append"`); pass it once per pytest target. When `--metric` is omitted for SBFL/MBFL the family default applies; for hybrid runs use `--sbfl-metric`/`--mbfl-metric` instead.

`--ranker none` is the default — no ranking, output identical to pre-Task-4 behavior. `--ranker weighted` opts in to ranking; `--ranker-weights` then overrides the three component weights (suspiciousness, simplicity, operator_priority) — only relative magnitudes matter, they are normalised internally. When ranking is off, `ranked_plausible_patches` is absent (`null`) from the JSON. Note `evaluate-llm-repair`'s `--ranker` default is `none`, unlike `evaluate-repair`'s default of `weighted`.

`--similarity-score` is off by default — output is then byte-for-byte identical to a build that never had this metric (the `context_similarity_score`/`similarity_band` keys are omitted from `repair_results.json`, not just `null`). Pass `--similarity-score` to additionally grade each plausible patch's closeness to the developer fix on `[0.0, 1.0]` (see [docs/other_correctness_measurement.md](docs/other_correctness_measurement.md)); this prints a "Similarity scores for plausible patches" block to the terminal and adds `context_similarity_score`/`similarity_band` to every plausible/ranked/assessed/all-results entry in the JSON. It never affects the exact-diff `is_correct`/`correct_count` verdict, which stays the framework's data-contamination signal.
`evaluate-localization` runs all 8 techniques (3 SBFL baselines, 2 SBFL extensions, 1 MBFL baseline, 1 MBFL-random extension, 1 Hybrid) on each specified bug and compares their rankings against the ground-truth faulty lines parsed from `bug_patch.txt`. All bugs must be checked out and compiled before running.

For `--technique llm`: `--operators` and `--skip-localize` are ignored (LLM backend generates free-form patches, not AST mutations). All other shared flags (`--budget`, `--top-n`, `--fl-mode`, `--fl-family`, `--ranker`, etc.) behave identically. LLM-specific flags (`--model`, `--temperature`, `--max-candidates`, `--llm-base-url`, `--llm-api-key-env`, `--system-prompt`, `--context-enrichment`, `--few-shot`, `--iterative`, `--max-iterations`) are silently ignored when `--technique template` is selected. `--few-shot N` is independent of `--context-enrichment`/`--iterative` and works in single-shot mode too, but `evaluate-llm-repair`'s three built-in `--variants` (`single-shot`, `context-enriched`, `iterative`) never enable few-shot — it's only reachable via the plain `repair` command.

`localize --backend {fauxpy,llm}` selects the FL backend independently from `--family`/`--metric` (which apply only to `fauxpy`). GPT@RUB vs. OpenAI is not a separate backend — both are `--backend llm`, distinguished purely by `--llm-base-url`/`--llm-api-key-env`/`--model` (omit `--llm-base-url` for the GPT@RUB default). `--top-n` is shared with the FauxPy path; `--fl-system-prompt` selects a file stem under `localization/prompts/`.

> The project's LLM provider is OpenAI (not GPT@RUB) — use `OPENAI_API_KEY`, `--llm-base-url https://api.openai.com/v1`, and a real OpenAI model name. Only `gpt-4.1-2025-04-14`-family models have been confirmed to work end-to-end; `codestral-22b` and similarly-named GPT@RUB-only models are not valid here.

## Architecture

All source lives under `src/apr_framework/`. Components are decoupled through abstract base classes; implementations are swapped by passing a different concrete class.

```
src/apr_framework/
  core/
    models.py        # shared dataclasses: BugIdentifier, CheckoutResult, TestRunResult,
                     # LocalizationResult, RankedLocation, PatchCandidate, RepairAttemptResult,
                     # EvaluationResult, LocalizationConfig, RepairRunMetrics (incl. rank_of_first_correct)
    exceptions.py    # APRFrameworkError, BenchmarkError, ConfigurationError
  benchmarks/
    base.py          # BenchmarkAdapter ABC (checkout / prepare_environment / run_tests / list_*)
    bugsinpy.py      # BugsInPyAdapter + BugsInPyToolchain (all Docker/shell calls go here)
    registry.py      # create_bugsinpy_adapter(), list_benchmark_names()
  cli/
    parser.py        # argparse grammar (build_parser())
    app.py           # command dispatch (main()), _build_ranker()
  localization/
    base.py          # FaultLocalizer ABC
    fauxpy.py        # FauxPyLocalizer, FauxPyConfig, FauxPyToolchain, parse_fauxpy_output,
                     # load_pytest_targets, extract_mbfl_tracking_metadata
    hybrid.py        # HybridFaultLocalizer — weighted normalized merge of SBFL + MBFL rankings
    perfect.py       # PerfectFaultLocalizer — oracle locations from bug_patch.txt (Task 3)
    llm.py           # LLMFaultLocalizer, LLMLocalizationConfig (Assignment 5, Task 1) —
                     # symbol-anchored source selection + parse_llm_fl_response
    prompts/
      fl_prompt1.txt # system prompt for LLMFaultLocalizer (strict-JSON ranked output)
    scripts/         # in-place FauxPy source patches applied by FauxPyToolchain before each run
      fauxpy_sbfl_metrics_patch.py     # adds MetricJaccard + MetricWSBI to FauxPy's schema/pipeline
      fauxpy_mbfl_selection_patch.py   # injects --mutation-selection/-budget/-seed pytest options
  repair/
    base.py          # RepairAlgorithm ABC
    dummy.py         # DummyRepairAlgorithm (random ground-truth / no-op)
    correctness.py   # is_correct_patch — diff-level comparison against developer fix
    regression.py    # build_regression_context, parse_failing_test_ids — regression half of plausibility
    run_loop.py      # run_validation_loop — shared budget loop used by runner and algorithm
    ranking/
      base.py        # PatchRanker ABC
      weighted.py    # WeightedCompositeRanker — suspiciousness + simplicity + operator_priority
      registry.py    # create_ranker() factory
    template/
      algorithm.py   # TemplateRepairAlgorithm
      config.py      # TemplateRepairConfig
      operators.py   # AST mutation operators (arith, comp, obo, bool, negate, return)
      patch_generator.py  # generate_patches_for_location — builds PatchCandidate list
      validator.py   # plausibility check (trigger + regression)
    llm/
      algorithm.py   # LLMRepairAlgorithm — implements RepairAlgorithm ABC; single-shot + iterative repair_loop
      client.py      # LLMClient ABC + OpenAICompatibleClient (OpenAI API, non-streaming);
                     # depends only on the LLMConnectionConfig Protocol (model_name/temperature/
                     # base_url/api_key_env_var), so localization/llm.py's config satisfies it too
      config.py      # LLMRepairConfig — model, temperature, max_patch_count, top_n_locations,
                     # iterative, max_iterations, context_enrichment, few_shot_count, etc.
      patch_extractor.py  # extract_patch_with_source (ExtractedPatch: diff_text + patched_source);
                          # extract_patch_from_llm_response kept as thin diff-only wrapper
      prompt_builder.py   # build_repair_prompt, extract_function_source — system+user message construction
      context_enricher.py # build_failing_test_context — best-effort failing-test source + traceback for the prompt
      few_shot.py          # build_few_shot_examples — buggy→fixed pairs from sibling bugs in the same project
      feedback.py          # build_test_failure_feedback_message, build_format_retry_message,
                           # is_no_improvement_signal — iterative-loop turn construction and stop conditions
      traceback_utils.py   # extract_last_traceback — shared by context_enricher.py and feedback.py
    patch_applier.py # apply_patch_and_validate — shared try/finally helper used by LLM (and future) backends
  evaluation/
    base.py          # EvaluationRunner ABC
    run_writer.py    # RunWriter — creates runs/run_NNN/, writes config.json/results.json/execution.log;
                     # serialize_localization_result() converts LocalizationResult to JSON-safe dict
    dummy_runner.py  # DummyEvaluationRunner — full APR pipeline with checkout/compile/repair/test
    repair_runner.py # RepairEvaluationRunner — drives validation loop, correctness, ranking, JSON output
    ground_truth.py  # GroundTruthLine, parse_bug_patch (parses bug_patch.txt diff → deleted lines),
                     # find_faulty_rank (lowest rank of any ground-truth line in a ranking),
                     # in_top_k, _files_match (flexible relative-path comparison)
    localization_runner.py  # LocalizationComparisonRunner — runs N techniques × M bugs, scores each
                            # against ground truth, writes results.json + README.md;
                            # LocalizationTechniqueResult holds ranked_locations + top_k_hits per run
    course_approaches.py    # CourseApproach + COURSE_APPROACHES — the four course approaches as data
    course_comparison_runner.py  # CourseComparisonRunner — bug x approach x FL-mode matrix; every cell
                                 # runs with the assessor + score_similarity=True; writes the course-wide report
    repair_comparison_runner.py  # RepairComparisonRunner (Task 5) — drives bug x FL-mode repair matrix, aggregates results.json + README.md
    llm_repair_comparison_runner.py  # LLMRepairComparisonRunner — bug x variant x FL-mode matrix for LLM repair,
                                     # tracks llm_query_count/time_to_first_plausible/rank metrics, writes results.json + README.md
  reporting/
    base.py          # ReportGenerator ABC
    archive.py       # ArchiveReportGenerator — writes report.md summary + zips run artifacts
```

### Key design decisions

**Two-container model.** The framework container (Python + Docker CLI) manages a long-lived sibling container named `apr-bugsinpy-executor` that runs BugsInPy commands. The framework never executes BugsInPy commands locally; all subprocess calls are routed through `BugsInPyToolchain`. When `APR_HOST_PROJECT_ROOT` is not set, volume mounts for the executor container will fail.

**Custom BugsInPy fork.** The framework uses a fork of BugsInPy (`https://github.com/Sonzakir/BugsInPy.git`) that adds pyenv-based multi-Python support and a `bugsinpy-safe-compile` wrapper. The original does not support multiple Python versions.

**Shared domain models.** All components communicate through dataclasses from `core/models.py` — not raw strings or dicts. `LocalizationResult.metadata["all_metrics"]` stores every metric table parsed from FauxPy output so later stages (repair, reporting) can consume any metric without re-running FauxPy. For MBFL runs, `metadata` also stores cost-control fields from `extract_mbfl_tracking_metadata` (e.g. `mutants_generated`, `mutants_validated`, `mutation_generation_time_seconds`).

**FauxPy isolation.** `FauxPyLocalizer` implements `FaultLocalizer`; `FauxPyToolchain` handles pinned FauxPy 0.7.0 installation and applies **two** in-place source patches before every localization run:
- *SBFL metric patch* — adds `MetricJaccard` (known literature metric) and `MetricWSBI` (custom **Weighted SBI**) to FauxPy's SQLite schema and ranking pipeline (these metrics are not in stock FauxPy 0.7.0). `MetricWSBI` computes `ef / (ef + alpha * ep)` where `alpha` is configurable via `--wsbi-alpha` (default 0.5). The `_WSBI_ALPHA` value is injected into the patch script at run time and baked into the written `metric_wsbi.py` file.
- *MBFL selection patch* — injects `--mutation-selection`, `--mutation-budget`, and `--mutation-seed` pytest options so the framework can cap expensive mutant validation.

Both patches use `replace_once` helpers that are idempotent (safe to re-apply). `parse_fauxpy_output` handles both statement rows (`File | Line | Score`) and function rows (`File | Function | Line | Score`); for function granularity it also captures the optional end line, populating `RankedLocation.line`, `.end_line`, and `.function`.

**Hybrid localization.** `HybridFaultLocalizer` (`localization/hybrid.py`) runs both the SBFL and MBFL localizers, min-max-normalizes each backend's scores independently, then combines them with normalized `sbfl_weight`/`mbfl_weight` and re-ranks. Ties break toward locations found by *both* backends, then by best per-backend rank. The reusable merge logic lives in the static `HybridFaultLocalizer.combine_rankings`; the combined `LocalizationResult.metadata` records the effective weights and the per-backend score formulas. Selected via `--family hybrid` with `--sbfl-metric`/`--mbfl-metric` (not `--metric`).

**`load_pytest_targets`** in `localization/fauxpy.py` converts BugsInPy `run_test.sh` scripts (pytest or `python -m unittest`) into pytest-compatible target strings. It raises `ConfigurationError` for `unittest discover`.

**`FauxPyConfig` metric defaults.** When `--metric` is not supplied, the default is `ochiai` for SBFL and `metallaxis` for MBFL. Validation in `__post_init__` rejects unsupported family/granularity/mutation combinations before any subprocess runs.

**Template-based repair.** `TemplateRepairAlgorithm` uses six AST mutation operators (`arith`, `comp`, `obo`, `bool`, `negate`, `return`) to generate syntactically valid variants at the top-N suspicious locations from FL. Validation applies each variant to the checkout, runs the test suite in the executor container, and restores the file unconditionally. The generate-and-validate loop lives in `run_loop.py` — not inside the algorithm — so it is shared with `RepairEvaluationRunner` and works unchanged with future backends.

**Perfect fault localization.** `PerfectFaultLocalizer` (`localization/perfect.py`) implements `FaultLocalizer` by parsing the developer fix from `bug_patch.txt` instead of running tests. It produces a `LocalizationResult` with `backend="perfect-fl"` that flows into the same repair pipeline. Selected with `--fl-mode perfect`; the `--fl-family` flag is ignored in this mode.

**LLM-based fault localization (Assignment 5, Task 1).** `LLMFaultLocalizer` (`localization/llm.py`) implements `FaultLocalizer` and emits ordinary `RankedLocation`s (`backend="llm-fl"`), so it is a drop-in replacement anywhere the pipeline consumes a `LocalizationResult` — same mental model as `PerfectFaultLocalizer`, just a different source of rankings. `localize()` runs the trigger test once (via the repair-side `build_failing_test_context`, imported lazily) to capture a traceback, then decides which project source to show the model with two combined signals: traceback frames (good for exceptions) and, importantly, the symbols the *failing test method* patches/mocks via `unittest.mock.patch` (recovered by walking only that method's AST node — scoping to the whole test file re-floods the anchor set with irrelevant symbols). Each anchored file is rendered as line-numbered, merged/elided windows capped by `max_source_lines`, non-test source first, so the token budget favors the actual fault region over the test file. `parse_llm_fl_response` defensively extracts a JSON array (raw reply, fenced block, or bracket-delimited substring) into `RankedLocation`s with synthetic descending scores (`1.0, 0.99, …`, matching `PerfectFaultLocalizer`) — malformed entries are dropped, not fatal, and an unparsable reply yields an empty list rather than raising. `OpenAICompatibleClient` (`repair/llm/client.py`) is reused unmodified for the transport; it was decoupled from `LLMRepairConfig` onto the narrow `LLMConnectionConfig` Protocol specifically so `LLMLocalizationConfig` could satisfy it without either config depending on the other's unrelated fields. Selected with `--backend llm`; debugging notes (why anchoring is scoped the way it is, what `files_shown`/`raw_llm_response` in `results.json` metadata tell you) are in [docs/Implementation5_1.md](docs/Implementation5_1.md).

**End-to-end LLM pipeline and the course-wide comparison (Assignment 5, Task 4).** `repair --fl-backend {fauxpy,llm}` selects the FL *backend* independently of `--fl-mode` (which selects the FL *source*: a tool vs. the `bug_patch.txt` oracle). `_localize_for_repair` (`cli/app.py`) resolves a four-way precedence — **perfect → cached (`--skip-localize`) → llm (`--fl-backend llm`) → fauxpy** — so `--fl-mode perfect` wins over `--fl-backend llm` (and logs that it did) and the default `--fl-backend fauxpy` reproduces the original three-way behavior byte-for-byte. `_build_llm_fault_localizer(args, adapter)` was extracted out of the `localize`-only builder and is shared by `localize`, `repair`, and the evaluation matrix; this works because the `repair` subparser reuses the *same argparse dest names* as `localize` (`fl_system_prompt`, `max_source_lines`, `source_window`). Chaining `--technique llm --fl-backend llm --retrieval-budget N --assess` gives the full pipeline (LLM-FL → LLM repair with retrieval → LLM assessment) in one command. `bugsinpy evaluate-course-comparison` runs `bugs × approaches × fl_modes`, where the approaches are data (`evaluation/course_approaches.py`), not branches; an approach with `uses_llm_fault_localization=True` has one FL source and so ignores the `--fl-modes` axis. **Every cell runs with the assessor attached and `score_similarity=True`** — that is why the command *re-runs* all four approaches instead of loading the committed Assignment-3/4 JSONs: `context_similarity_score` needs `patched_source` (deliberately stripped from serialized results) and the assessor needs the patch objects, so neither metric can be retro-computed from the old artifacts. `_LLM_VARIANT_TOGGLES` / `_build_llm_algorithm_for_variant` must stay untouched — the Assignment-4 `evaluate-llm-repair` matrix has to remain retrieval-free to stay a valid baseline.

**Which bugs FauxPy can actually localize (and why the bug set is what it is).** The `auto` FL mode is only worth running where FauxPy works, and three distinct failure modes disqualify a bug:
- **Python 3.7 pins** — FauxPy 0.7.0 (via `cosmic-ray` 8.3.5) cannot install at all (`tornado:14`, `youtube-dl:12`).
- **Dependency conflict with the project's own pins** — installing FauxPy drags in `cosmic-ray`, whose unpinned `pydantic` resolves to 2.x and overrides e.g. fastapi's `pydantic==1.5.1`, after which every fastapi test module fails to import (pydantic 2 also demands `email-validator>=2`). Reasserting the project's pins does **not** fix it: that downgrades `typing_extensions`, and FauxPy's own chain (`pyllmut` → `openai`) needs `typing_extensions>=4.5` to import, so the plugin dies instead. The two dependency sets are irreconcilable — **fastapi bugs cannot be localized with FauxPy 0.7.0**, and no toolchain patch changes that. (An earlier attempt to reinstall `bugsinpy_requirements.txt` after the FauxPy install was reverted for exactly this reason; don't re-add it.)
- **Silent empty ranking** — FauxPy installs, exits 0, and ranks nothing (`scrapy:2`; report dirs exist on disk with empty score tables).

In practice `black` bugs are the reliable auto-FL set. A cell with no ranked location generates no candidate, so its zeros describe the *localizer*, not the repair approach; comparing them against a cell that ran is meaningless. `CourseComparisonRunner` short-circuits such a cell to `NO_FL_LOCATIONS_STATUS` (`no_fl_locations`) instead of running repair against an empty ranking and reporting `no_patch`, and `_is_cell_usable` keeps those cells out of every cross-approach comparison. Bugs FauxPy cannot reach are run with `--fl-modes perfect` (no auto cell is created at all) rather than being scored as a zero. Before adding a bug to the auto set, run `localize --project P --bug N` and confirm ranked locations come back — cached FauxPy reports under `.workspace/` are *not* proof, since a later `compile` can rot the venv.

**Auto-FL-capable and repairable are nearly disjoint in this benchmark.** `black` localizes reliably but resists repair — it lints its own source, so any patch that is not black-formatted passes the trigger test and then fails the regression check (see [[reference_black_self_lint]]). The bugs that actually yield plausible/exact-diff patches (`tornado:14`, `scrapy:2`) are precisely the ones FauxPy cannot localize. Expect a course-comparison report to carry both kinds of bug for that reason; a set chosen only for auto-FL capability will be almost all zeros.

**The exact-diff column is not a correctness verdict.** `correct_count` counts patches whose diff matches the developer fix byte-for-byte, so a semantically correct fix written differently scores 0. The report renders it as **`Exact diff`** / "Exact-diff matches", never "Correct" — the graded `quality_score` (LLM assessor) and `context_similarity_score` carry the actual quality judgment. Keep that wording when touching the report; calling it "correct" overstates what the metric measures.

**Patch ranking is optional and non-destructive.** `RepairEvaluationRunner` accepts an optional `ranker: PatchRanker | None`. When provided, it reorders plausible results after the correctness check and writes both orderings into `repair_results.json`: `plausible_patches` (generation order, the baseline) and `ranked_plausible_patches` (ranked order). `rank_of_first_correct` (1-indexed) is stored in `RepairRunMetrics` and emitted at the top level of each bug's JSON payload. The `PatchRanker` ABC lives in `repair/ranking/base.py`; the only current implementation is `WeightedCompositeRanker` (`repair/ranking/weighted.py`), which combines a suspiciousness score, patch simplicity, and operator priority using a configurable weighted sum. Enabled by default with `--ranker weighted`; disabled with `--ranker none`.

**Repair evaluation matrix (Task 5).** `bugsinpy evaluate-repair` runs the full repair pipeline on a set of bugs under both `auto` and `perfect` FL with the ranker applied, then writes an aggregated `experiment_results/repair/{results.json,README.md}` (per-bug tables, aggregate, generated discussion). `RepairComparisonRunner` (`evaluation/repair_comparison_runner.py`) only orchestrates the matrix and aggregates — each (bug, FL mode) cell is executed by the existing `RepairEvaluationRunner` and gets its own `runs/run_NNN` directory (logs + patch diffs preserved as artifacts). A localization failure for one cell (e.g. FauxPy uninstallable on a bug's Python) is captured as an error cell rather than aborting the matrix. This mirrors the `evaluate-localization` / `LocalizationComparisonRunner` pattern.

**LLM repair evaluation matrix (Assignment 4, Task 5).** `bugsinpy evaluate-llm-repair` runs the same style of matrix as `evaluate-repair` but over `bugs × variants × fl_modes`, where `variants` ∈ `{single-shot, context-enriched, iterative}` map to `LLMRepairConfig` toggle presets in `_LLM_VARIANT_TOGGLES` (`cli/app.py`) — none of the three enable few-shot, since few-shot is only reachable via the plain `repair --few-shot N` flag. `LLMRepairComparisonRunner` (`evaluation/llm_repair_comparison_runner.py`) builds a fresh `LLMRepairAlgorithm` + `OpenAICompatibleClient` per cell (keeps each cell's `llm_query_count` isolated), writes incremental `results.json` after every cell (crash-safe against long LLM runs), and generates a `README.md` with per-bug tables plus three auto-written analyses: iterative-vs-single-shot effect, context-enrichment effect, and a side-by-side comparison against the Assignment-3 template results. Output defaults to `experiment_results/llm_repair/task5/`.
**`LocalizationComparisonRunner`** (`evaluation/localization_runner.py`) runs the full 8-technique comparison matrix and emits a markdown report with per-bug tables, an aggregate Top-k accuracy table, and an auto-generated discussion section. The technique list is built in `app._build_techniques()` and covers: SBFL (Ochiai/Tarantula/D*/Jaccard/WSBI), MBFL-Metallaxis (exhaustive baseline), MBFL-Metallaxis-Random (budget-capped extension), and Hybrid. Ground-truth matching via `_files_match` is path-flexible — it handles FauxPy's short relative paths against git-diff absolute paths by comparing suffixes and, as a last resort, filenames.

**LLM-based repair (Assignment 4).** `LLMRepairAlgorithm` (`repair/llm/algorithm.py`) implements the `RepairAlgorithm` ABC and plugs into the same `RepairEvaluationRunner` pipeline as the template backend, but still generates and validates **whole-function** replacements, not SEARCH/REPLACE edit blocks (`patch_extractor.py` has no edit-block support — a SEARCH/REPLACE format was explored but never landed; no plan doc for it survives in the repo). The algorithm iterates over the top-N FL locations, calls `extract_function_source` to isolate the enclosing function (with a ±25-line window fallback), builds a structured system + user prompt via `build_repair_prompt` (optionally injecting failing-test context and few-shot examples — see below), and samples up to `max_patch_count` candidate patches from the LLM. `extract_patch_with_source` finds a fenced code block in the response, validates its syntax with `ast.parse`, splices the replacement into the original file lines, and returns an `ExtractedPatch` (`diff_text` + `patched_source`, the latter stashed in `PatchCandidate.metadata["patched_source"]` so `is_correct_patch` can diff LLM patches). Validation uses `subprocess.run(["patch", "-p0"], ...)` (absolute paths require `-p0`, not `-p1`) inside the shared `apply_patch_and_validate` helper (`repair/patch_applier.py`), which guarantees file restoration in a `try/finally` block regardless of test outcome. `OpenAICompatibleClient` (`repair/llm/client.py`) reads the API key from the environment at call time and uses `stream=False`. Selected via `--technique llm`; the client is constructed in `_build_llm_algorithm_and_log_start` in `cli/app.py`.

**`repair_loop` extension point (Assignment 4, Task 3).** `RepairAlgorithm.repair_loop(bug, checkout, *, budget, stop_on_first) -> LoopOutcome` (`repair/base.py`) is a non-abstract hook whose default implementation delegates to the shared `run_validation_loop` — every existing backend (template, single-shot LLM) inherits this unchanged. `LLMRepairAlgorithm.repair_loop` overrides it only when `LLMRepairConfig.iterative=True`, dispatching to `_run_iterative_loop`, which walks the top-N FL locations and runs one multi-turn `[system, user, assistant, user, ...]` conversation per location via `_run_conversation_for_location` (up to `max_iterations` turns), sharing one global `budget` (test-suite executions) across all locations. A failed turn appends `build_test_failure_feedback_message` (from `feedback.py`, branching on trigger vs. regression failure) as the next user turn; `is_no_improvement_signal` and unparsable-reply retries (capped at 2) end a location's conversation early. Both loop shapes converge on the same `build_loop_summary` helper, so downstream JSON output is shape-independent. `RepairAlgorithm.llm_query_count() -> int | None` (default `None`) lets backends report how many LLM calls a run made; the runner surfaces it in evaluation output.

**Context enrichment and few-shot (Assignment 4, Task 2).** `LLMRepairConfig.context_enrichment` (default `True`) and `.few_shot_count` (default `0`) are independent toggles consumed inside `_build_location_prompt`, shared by both the single-shot and iterative paths. `context_enricher.build_failing_test_context` reads the trigger test's source from the checkout and runs it once unpatched to capture a traceback (via `extract_last_traceback`); any failure degrades to an empty context rather than raising. `few_shot.build_few_shot_examples` reconstructs up to N buggy→fixed pairs from *other* bugs in the same BugsInPy project by parsing their `bug_patch.txt` diffs — deterministic, offline, and independent of the current bug's checkout state.

### Directory conventions
```
.tools/bugsinpy        # BugsInPy clone (git submodule managed by setup command)
.workspace/bugsinpy/   # checked-out project worktrees (e.g. PySnooper_1/PySnooper/)
runs/run_NNN/          # single-localization run outputs: config.json, results.json, execution.log
experiment_results/    # evaluate-localization outputs: results.json + README.md comparison report
```

### Regenerating experiment results without Docker
`scripts/generate_experiment_results.py` rebuilds `experiment_results/{results.json,README.md}` from FauxPy CSV files already cached under `.workspace/` by prior Docker runs — it reuses `LocalizationComparisonRunner` (the same code path as `evaluate-localization`) but runs no containers. Use it to refresh the report after tweaking scoring/reporting logic; it cannot produce results for bugs whose CSVs were never generated in Docker.
```bash
python scripts/generate_experiment_results.py   # run from repo root
```

## Naming conventions

These rules apply to every variable and method name written or modified in this codebase. They are enforced during code review and must be respected when generating new code.

### Variable naming rules

**No single-letter variables** outside of math/index contexts (`i`, `j`, `k` in tight loops are acceptable; `r`, `x`, `v`, `n` as standalone locals are not).

**No vague abbreviations.** Forbidden: `op`, `src`, `cls`, `val`, `arg`, `tmp`, `res`, `obj`, `cfg`, `ctx`, `msg`. Write the full word or a precise compound.

**No misleading names** that imply more than the variable actually holds. Example: do not call a variable `best` if it is merely the first item in a list.

**No generic nouns without qualifying context.** Words like `result`, `data`, `info`, `item`, `value`, `output`, `working`, `trigger`, `baseline`, `candidate` are only acceptable when the surrounding type already makes the content unambiguous, and even then a more precise compound is preferred.

**Count variables must say they are counts.** Append `_count`:
- `passed` → `passed_count`, `plausible` → `plausible_count`

**Variables holding `Path` objects or path strings must say so.** Append `_path` (for `Path`) or `_path_str` / `_str` (for raw strings):
- `raw` holding a file-path string → `file_path_str`
- `candidate` holding a `Path` → `candidate_file_path`

**Variables holding collections of domain objects must name both the adjective and the noun.** A list of plausible `RepairAttemptResult` objects → `plausible_results`, not `plausible`. A list of ranked locations → `ranked_locations`, not `locations`.

**Variables holding test-run results must say so.** Suffix with `_run_result` or `_result`:
- `baseline` holding a `TestRunResult` → `baseline_run_result`
- `regression` holding a `TestRunResult` → `regression_run_result`

### Method naming rules

**Methods must describe what they return or do, not just what they touch.** Prefer verb phrases:
- `get_patch()` → `generate_patch()` or `fetch_patch()` depending on whether it computes or retrieves
- `process()` → name the specific action: `validate_candidates()`, `normalise_scores()`

**Boolean-returning methods must start with `is_`, `has_`, or `can_`.** Examples: `is_plausible()`, `has_reference_patch()`, `can_derive_suite_command()`.

**Factory and builder methods** that construct and return an object must start with `build_`, `create_`, or `make_`:
- `regression_context()` → `build_regression_context()`

**Private helpers** (single leading underscore) follow the same rules. The leading underscore does not relax the clarity requirement.

**A name must let the reader understand the method by reading only the name — not the body.** If a method does two or more distinct things (e.g. parses CLI args *and* resolves a path), name all of them rather than reaching for an umbrella noun. Reject vague wrapper nouns like `context`, `state`, `setup`, `env`, `handler` unless the surrounding type already disambiguates what they hold:
- `_build_cli_context()` (parses args, resolves project root, loads `.env`) → `parse_args_and_resolve_project_root()`
- `_setup_run()` → name every step it performs, or split it into the steps and give the caller a short sequence of clearly named calls instead of one opaque one.

### Concrete examples from this codebase

| Was | Now | Rule violated |
|-----|-----|---------------|
| `trigger` (NameError — undefined) | `trigger_command_content` | wrong name, variable didn't exist |
| `r for r in self.all_results` | `attempt_result for attempt_result in self.all_results` | single-letter variable |
| `op`, `src`, `line` (logging locals) | `operator_key`, `source_path_str`, `target_line_str` | vague abbreviations |
| `plausible` (list of results) | `plausible_results` | generic noun without noun qualifier |
| `first_plausible` (a result object) | `first_plausible_result` | incomplete compound |
| `cls` (holds a class type) | `operator_class` | vague abbreviation in the explicit banned list |
| `raw` (file-path string) | `file_path_str` | no `_str` suffix for path string |
| `stripped` (a `Path`) | `stripped_file_path` | no `_path` suffix for `Path` object |
| `_build_cli_context()` (returns args + project root) | `parse_args_and_resolve_project_root()` | vague umbrella noun (`context`) hid what the method actually returns |

## Troubleshooting

- If the executor container has stale volume mounts: `docker rm -f apr-bugsinpy-executor` then re-run `bugsinpy setup`.
- If running outside Docker Compose: `export APR_HOST_PROJECT_ROOT="$(pwd)"` before setup.
- On Windows: change line endings from CRLF to LF for shell scripts.
- FauxPy localization requires a checked-out and compiled bug. Run `checkout` then `compile` (or `test`, which does both) before `localize`.
- FauxPy currently requires `run_test.sh` to invoke pytest directly. Projects using only `unittest discover` are not supported.
- If FauxPy reports a missing `Jaccard` or `WSBI` metric, the framework's SBFL patch was not applied — check that the checkout's virtual environment is intact and re-run `compile`.
- If `localize --backend llm` ranks only test-file lines, symbol anchoring found nothing — check `results.json → metadata.files_shown`; the failing test likely doesn't `patch()`/mock a project symbol, or the patched module didn't resolve to a file under the worktree.
- To do a full clean rebuild: `docker compose down --remove-orphans && docker rm -f apr-bugsinpy-executor 2>/dev/null; docker rmi apr-framework:local apr-bugsinpy:local 2>/dev/null; docker compose build --no-cache`.
