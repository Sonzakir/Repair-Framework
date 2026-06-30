---
name: project-task5-evaluation
description: "Task 5 evaluation — first attempt with black bugs FAILED; second attempt with fastapi+luigi running in Docker"
metadata: 
  node_type: memory
  type: project
  originSessionId: 7758efbd-b695-451a-8856-195a050c4154
---

Task 5 evaluation: first attempt (black:1/3/7) FAILED; second attempt with =>  fastapi:3/6, luigi:33



## Failed attempt (black:1, black:3, black:7)

Results were real (actual FauxPy Docker runs) but  meaningless:
- Single failing test per bug → all 5 SBFL metrics give identical max scores (no differentiation)
- Mutation-inadequate test suites → MBFL gives 0 ranked locations for all bugs
- black:3 fault at module-level decorator → invisible to dynamic coverage

Artifacts saved: `experiment_results/FAILED_EXPERIMENT.md`, `experiment_results/results.json`, `experiment_results/README.md` (old).

## Successful attempt (fastapi:3, fastapi:6, luigi:33) — in progress

**Bug selection:** Multiple failing tests per bug, logic/condition bugs amenable to MBFL.

| Bug | # Failing tests | Fault | Ground truth |
|---|---|---|---|
| fastapi:3 | 8 | Missing recursive serialization for lists/dicts | routing.py faulty lines ~63-69 |
| fastapi:6 | 3 | Missing `or field.type_ in sequence_types` in condition | dependencies/utils.py |
| luigi:33 | 4 | `if p.significant` → `if not p.is_global` | luigi/task.py |

**SBFL probe (fastapi:3, Ochiai):** faulty line `routing.py:63` ranked **8 out of ~300** with score 0.9877 (confirmed real differentiation).

**pydantic issue in fastapi venvs:** pydantic 2.x gets installed (conflict with FauxPy's pyllmut→openai dep). Fixed by `pip install 'pydantic>=1.9,<2.0'` inside executor for fastapi_3 and fastapi_6 venvs.

**Code changes:**
- `src/apr_framework/cli/parser.py`: Added `--traditional-budget` arg (default 200)
- `src/apr_framework/cli/app.py`: `_make_mbfl_traditional` uses `mutation_strategy="random"` + traditional_budget

**Evaluate-localization command:**
```bash
docker compose run --rm apr-framework python -m apr_framework bugsinpy evaluate-localization \
    --bugs "fastapi:3,fastapi:6,luigi:33" \
    --budget 50 --traditional-budget 200 --seed 42 \
    --granularity statement --output-dir experiment_results
```

**How to apply pydantic fix after fresh checkout+compile:**
```bash
docker exec apr-bugsinpy-executor bash -c "
/home/workspace/fastapi_3/fastapi/env/bin/pip install 'pydantic>=1.9,<2.0' -q
/home/workspace/fastapi_6/fastapi/env/bin/pip install 'pydantic>=1.9,<2.0' -q
"
```
