# AGENTS.md

Guidance for coding agents working in this repository.

## Scope

This file applies to the whole repository.

## Project Summary

This is a Python automated debugging and repair framework. The package lives
under `src/apr_framework` and exposes a CLI through:

```bash
python -m apr_framework
```

The current implementation centers on a Docker-backed BugsInPy benchmark
adapter, a FauxPy fault-localization integration, dummy repair/evaluation
components, and structured evaluation artifacts under `runs/`.

## Repository Map

- `src/apr_framework/core/`: shared dataclasses, enums, and framework exceptions.
- `src/apr_framework/benchmarks/`: benchmark interfaces, registry, and the
  BugsInPy adapter/toolchain.
- `src/apr_framework/localization/`: fault-localization interface and FauxPy
  implementation.
- `src/apr_framework/repair/`: repair algorithm interface and dummy repair
  implementation.
- `src/apr_framework/evaluation/`: evaluation runner interface and dummy
  end-to-end runner.
- `src/apr_framework/reporting/`: report generation interface.
- `src/apr_framework/cli/`: argparse grammar and command dispatch.
- `tests/`: pytest-based smoke/unit tests.
- `runs/`: structured experiment output; existing runs may be intentional
  artifacts.
- `.tools/bugsinpy`: local BugsInPy checkout, ignored and machine-specific.
- `.workspace/bugsinpy`: checked-out buggy projects and evaluation worktrees,
  ignored and machine-specific.

## Development Commands


Local editable install:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install pytest
```

Run tests:

```bash
python -m pytest -q
```

Build package artifacts:

```bash
python -m pip install build
python -m build
```

Basic CLI smoke check:

```bash
python -m apr_framework list-benchmarks
```

Docker/BugsInPy setup from the repository root:

```bash
export APR_HOST_PROJECT_ROOT="$(pwd)"
docker compose build
docker compose run --rm apr-framework
python -m apr_framework bugsinpy setup
```

The BugsInPy setup command may clone `.tools/bugsinpy`, build the
`apr-bugsinpy:local` image, create/start the `apr-bugsinpy-executor` container,
and populate `.workspace/bugsinpy`.

## Agent Workflow

1. Start by checking `git status --short` and treat existing changes as user
   work. Do not revert or overwrite them unless explicitly asked.
2. Prefer narrow, project-shaped changes. Follow the existing component
   boundaries rather than introducing broad abstractions.
3. Update or add tests for behavioral changes. For interface changes, test the
   public import path and at least one representative implementation.
4. Run `python -m pytest -q` before finishing when code changes are made. If a
   change touches packaging, also run `python -m build` when practical.
5. Do not run Docker, BugsInPy setup, or benchmark evaluation commands unless
   the task requires them. These commands are slower, may require the Docker
   daemon, and can mutate local ignored directories.

## Coding Conventions

- Keep code compatible with Python 3.10+.
- Use standard-library dependencies unless a new runtime dependency is clearly
  necessary and added to `pyproject.toml`.
- Prefer `pathlib.Path` for filesystem paths, matching the existing code.
- Keep benchmark-specific command details inside benchmark adapters/toolchains.
  Higher-level repair, localization, evaluation, and CLI code should exchange
  shared models from `apr_framework.core.models`.
- Raise framework-specific exceptions from `apr_framework.core.exceptions`
  for user-facing configuration, benchmark, or framework errors.
- Keep CLI parsing in `src/apr_framework/cli/parser.py` and command behavior in
  `src/apr_framework/cli/app.py`.
- Keep generated output deterministic when possible. Preserve the seed-driven
  behavior of `DummyRepairAlgorithm` and `DummyEvaluationRunner`.
- Avoid adding broad formatting churn. There is no configured formatter or
  linter in the repository at the moment, so match the surrounding style.

## Architecture Notes

Framework components communicate through domain models in
`apr_framework.core.models`, especially `BugIdentifier`, `CheckoutResult`,
`TestRunResult`, `LocalizationResult`, `PatchCandidate`, and
`EvaluationResult`.

Benchmark integrations implement `BenchmarkAdapter` and should hide external
benchmark commands behind `checkout`, `prepare_environment`, `run_tests`, and
listing methods. BugsInPy-specific commands such as `bugsinpy-checkout`,
`bugsinpy-safe-compile`, and `bugsinpy-test` belong in the BugsInPy adapter or
toolchain, not in repair or evaluation code.

Repair algorithms implement `RepairAlgorithm` and should return
`PatchCandidate` objects. Evaluation runners should validate patches through
the benchmark adapter instead of assuming benchmark internals.

Fault localizers implement `FaultLocalizer`. The FauxPy integration runs inside
the prepared benchmark environment and parses pytest/FauxPy output into ranked
locations.

## Docker And BugsInPy Guardrails

- `.tools/bugsinpy` and `.workspace/bugsinpy` are local state. Do not edit,
  delete, or commit their contents.
- `python -m apr_framework bugsinpy setup` depends on Git, Docker, and a
  reachable Docker daemon.
- When running inside Docker, `APR_HOST_PROJECT_ROOT` must point to this
  repository on the host so the sibling BugsInPy executor can mount the same
  files.
- The default BugsInPy image/container names are `apr-bugsinpy:local` and
  `apr-bugsinpy-executor`. Respect `BUGSINPY_IMAGE` and `BUGSINPY_CONTAINER`
  environment overrides.
- BugsInPy and FauxPy operations may install dependencies into benchmark
  checkouts. Keep those effects inside ignored workspace/tool directories.

## Generated Artifacts

- The dummy evaluation runner creates `runs/run_###/config.json`,
  `runs/run_###/results.json`, and `runs/run_###/execution.log`.
- Do not overwrite or remove existing run directories unless the user asks.
- If adding generated example artifacts, keep them small, deterministic, and
  documented in `README.md`.

## Testing Guidance

- Fast/default validation is `python -m pytest -q`; current tests focus on
  public imports.
- Prefer unit tests that do not require Docker for core models, CLI parsing,
  registry behavior, output parsing, and deterministic dummy repair/evaluation
  logic.
- For BugsInPy or FauxPy behavior, isolate subprocess/Docker interactions with
  fakes or mocks where possible. Reserve real Docker integration tests for
  explicit benchmark-validation work.
- If you cannot run a relevant test because Docker, network access, or a
  benchmark checkout is unavailable, say so clearly in the final response.

## Documentation

Update `README.md` when changing user-facing CLI commands, setup steps,
directory layout, Docker behavior, or evaluation artifact formats.

Keep documentation honest about what is implemented versus planned. This
project is intentionally modular, but not every benchmark, repair strategy, or
report generator exists yet.
