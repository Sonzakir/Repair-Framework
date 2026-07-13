# BugsInPy usable bugs manual scan

Scanned through the existing Docker-based CLI path only. A bug is marked usable only when checkout and compile succeeded, the BugsInPy test command ran through the framework, at least one test outcome was parsed, and the buggy checkout exposed a failing/erroring trigger for later repair validation.

Available scope discovered by CLI: 17 projects, 501 bugs.

Commands used:

```bash
docker compose build
docker compose run --rm apr-framework python -m apr_framework bugsinpy setup
docker compose run --rm apr-framework python -m apr_framework bugsinpy list-projects
docker compose run --rm apr-framework python -m apr_framework bugsinpy list-bugs <project>
docker compose run --rm apr-framework python -m apr_framework bugsinpy checkout <project> <bug_id>
docker compose run --rm apr-framework python -m apr_framework bugsinpy compile <project> <bug_id>
docker compose run --rm apr-framework python -m apr_framework bugsinpy test <project> <bug_id>
```

Status semantics: `ok` means the stage command completed successfully through Docker; `fail` means that stage blocked usability; `skip` means an earlier stage failed; `interrupted` means the scan was intentionally stopped during that stage and no usability is claimed. For the `test` column, `ok` requires a parsed test run with a failing/erroring trigger; a dependency/import/collection failure with zero parsed tests is recorded as `fail`.

| project | bug_id | checkout | compile | test | usable | notes |
|---|---:|---|---|---|---|---|
| PySnooper | 1 | ok | ok | fail | no | test produced no parsed test run: Traceback: E ModuleNotFoundError: No module named 'python_toolbox' ERROR: found no collectors for /home/workspace/PySnooper_1/PySnooper/tests/test_chinese.py::test_chinese |
| PySnooper | 2 | ok | ok | fail | no | test produced no parsed test run: Traceback: E ImportError: cannot import name 'mini_toolbox' from 'tests' (/home/workspace/PySnooper_2/PySnooper/tests/__init__.py) ERROR: found no collectors for /home/workspace/PySnooper_2/PySnooper/tests/test_pysnooper.py::test_custom_repr_single |
| PySnooper | 3 | ok | ok | fail | no | test produced no parsed test run: Traceback: E ModuleNotFoundError: No module named 'python_toolbox' ERROR: found no collectors for /home/workspace/PySnooper_3/PySnooper/tests/test_pysnooper.py::test_file_output |
| ansible | 1 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| ansible | 2 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| ansible | 3 | ok | ok | ok | yes | trigger failure observed: tests=54, failing=1, errors=0 |
| ansible | 4 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| ansible | 5 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| ansible | 6 | ok | ok | ok | yes | trigger failure observed: tests=3, failing=0, errors=1 |
| ansible | 7 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| ansible | 8 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| ansible | 9 | ok | ok | ok | yes | trigger failure observed: tests=13, failing=2, errors=0 |
| ansible | 10 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| ansible | 11 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| ansible | 12 | ok | ok | ok | yes | trigger failure observed: tests=4, failing=4, errors=0 |
| ansible | 13 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=0, errors=1 |
| ansible | 14 | ok | ok | ok | yes | trigger failure observed: tests=2, failing=1, errors=0 |
| ansible | 15 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| ansible | 16 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| ansible | 17 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| ansible | 18 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=0, errors=1 |
| black | 1 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| black | 2 | ok | ok | ok | no | test ran 1 test(s), but no failing/erroring trigger was observed |
| black | 3 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| black | 4 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| black | 5 | ok | ok | ok | no | test ran 1 test(s), but no failing/erroring trigger was observed |
| black | 6 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| black | 7 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| black | 8 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| black | 9 | ok | ok | ok | no | test ran 1 test(s), but no failing/erroring trigger was observed |
| black | 10 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| black | 11 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| black | 12 | ok | ok | ok | no | test ran 1 test(s), but no failing/erroring trigger was observed |
| black | 13 | ok | ok | ok | no | test ran 1 test(s), but no failing/erroring trigger was observed |
| black | 14 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| black | 15 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| black | 16 | ok | ok | ok | no | test ran 1 test(s), but no failing/erroring trigger was observed |
| black | 17 | ok | ok | ok | no | test ran 1 test(s), but no failing/erroring trigger was observed |
| black | 18 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| black | 19 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| black | 20 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| black | 21 | ok | ok | ok | no | test ran 1 test(s), but no failing/erroring trigger was observed |
| black | 22 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| black | 23 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| cookiecutter | 1 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| cookiecutter | 2 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| cookiecutter | 3 | ok | ok | ok | yes | trigger failure observed: tests=4, failing=4, errors=0 |
| cookiecutter | 4 | ok | ok | fail | no | test produced no parsed test run: ERROR: invocation failed (exit code 1), logfile: /home/workspace/cookiecutter_4/cookiecutter/.tox/log/GLOB-0.log Traceback (most recent call last): ERROR: FAIL could not package project - v = InvocationError('/home/workspace/cookiecutter_4/cookiecutter/env/bin/python setup.py sdist --formats=zip --dist-dir /home/workspace/cookiecutter_4/cookiecutter/.tox/dist', 1) |
| fastapi | 1 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| fastapi | 2 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| fastapi | 3 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| fastapi | 4 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| fastapi | 5 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| fastapi | 6 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| fastapi | 7 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| fastapi | 8 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| fastapi | 9 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| fastapi | 10 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| fastapi | 11 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| fastapi | 12 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| fastapi | 13 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| fastapi | 14 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| fastapi | 15 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| fastapi | 16 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| httpie | 1 | ok | ok | ok | yes | trigger failure observed: tests=11, failing=11, errors=0 |
| httpie | 2 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| httpie | 3 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| httpie | 4 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| httpie | 5 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| keras | 1 | ok | ok | fail | no | test produced no parsed test run: Tests run: 0 ImportError while loading conftest '/home/workspace/keras_1/keras/tests/conftest.py'. E ModuleNotFoundError: No module named 'numpy' |
| keras | 10 | ok | ok | fail | no | test produced no parsed test run: Tests run: 0 ImportError while loading conftest '/home/workspace/keras_10/keras/tests/conftest.py'. E ModuleNotFoundError: No module named 'numpy' |
| keras | 11 | ok | ok | fail | no | test produced no parsed test run: Tests run: 0 ImportError while loading conftest '/home/workspace/keras_11/keras/tests/conftest.py'. E ModuleNotFoundError: No module named 'numpy' |
| keras | 12 | ok | ok | fail | no | test produced no parsed test run: E ModuleNotFoundError: No module named 'numpy' ImportError while loading conftest '/home/workspace/keras_12/keras/tests/conftest.py'. E ModuleNotFoundError: No module named 'numpy' |
| keras | 13 | ok | ok | fail | no | test produced no parsed test run: Tests run: 0 ImportError while loading conftest '/home/workspace/keras_13/keras/tests/conftest.py'. E ModuleNotFoundError: No module named 'numpy' |
| keras | 14 | ok | ok | fail | no | test produced no parsed test run: Tests run: 0 ImportError while loading conftest '/home/workspace/keras_14/keras/tests/conftest.py'. E ModuleNotFoundError: No module named 'numpy' |
| keras | 15 | ok | ok | interrupted | no | scan stopped during test after checkout and compile succeeded; rerun this bug when resuming |
| sanic | 1 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| sanic | 2 | ok | ok | ok | no | test ran 1 test(s), but no failing/erroring trigger was observed |
| sanic | 3 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| sanic | 4 | ok | ok | fail | no | test produced no parsed test run: Tests run: 0 Traceback (most recent call last): ModuleNotFoundError: No module named 'requests_async' |
| sanic | 5 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| tqdm | 1 | ok | ok | ok | yes | trigger failure observed: tests=2, failing=1, errors=1 |
| tqdm | 2 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| tqdm | 3 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| tqdm | 4 | ok | ok | ok | yes | trigger failure observed: tests=2, failing=1, errors=1 |
| tqdm | 5 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| tqdm | 6 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| tqdm | 7 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| tqdm | 8 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| tqdm | 9 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| spacy | 1 | ok | ok | fail | no | test produced no parsed test run: Tests run: 0 ImportError while loading conftest '/home/workspace/spacy_1/spacy/spacy/tests/conftest.py'. E ModuleNotFoundError: No module named 'thinc' |
| spacy | 2 | ok | ok | fail | no | test produced no parsed test run: Tests run: 0 ImportError while loading conftest '/home/workspace/spacy_2/spacy/spacy/tests/conftest.py'. E ModuleNotFoundError: No module named 'thinc' |
| spacy | 3 | ok | ok | fail | no | test produced no parsed test run: Tests run: 0 ImportError while loading conftest '/home/workspace/spacy_3/spacy/spacy/tests/conftest.py'. E ModuleNotFoundError: No module named 'thinc' |
| spacy | 4 | ok | ok | fail | no | test produced no parsed test run: Tests run: 0 ImportError while loading conftest '/home/workspace/spacy_4/spacy/spacy/tests/conftest.py'. E ModuleNotFoundError: No module named 'thinc' |
| spacy | 5 | ok | ok | fail | no | test produced no parsed test run: Tests run: 0 ImportError while loading conftest '/home/workspace/spacy_5/spacy/spacy/tests/conftest.py'. E ModuleNotFoundError: No module named 'thinc' |
| spacy | 6 | ok | ok | fail | no | test produced no parsed test run: Tests run: 0 ImportError while loading conftest '/home/workspace/spacy_6/spacy/spacy/tests/conftest.py'. E ModuleNotFoundError: No module named 'thinc' |
| spacy | 7 | ok | ok | fail | no | test produced no parsed test run: Tests run: 0 ImportError while loading conftest '/home/workspace/spacy_7/spacy/spacy/tests/conftest.py'. E ModuleNotFoundError: No module named 'thinc' |
| spacy | 8 | ok | ok | fail | no | test produced no parsed test run: Tests run: 0 ImportError while loading conftest '/home/workspace/spacy_8/spacy/spacy/tests/conftest.py'. E ModuleNotFoundError: No module named 'thinc' |
| spacy | 9 | ok | ok | fail | no | test produced no parsed test run: Tests run: 0 ImportError while loading conftest '/home/workspace/spacy_9/spacy/spacy/tests/conftest.py'. E ModuleNotFoundError: No module named 'thinc' |
| spacy | 10 | ok | ok | fail | no | test produced no parsed test run: Tests run: 0 ImportError while loading conftest '/home/workspace/spacy_10/spacy/spacy/tests/conftest.py'. E ModuleNotFoundError: No module named 'thinc' |
| tornado | 1 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| tornado | 2 | ok | ok | ok | no | test ran 1 test(s), but no failing/erroring trigger was observed |
| tornado | 3 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| tornado | 4 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| tornado | 5 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| tornado | 6 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| tornado | 7 | ok | ok | ok | no | test ran 1 test(s), but no failing/erroring trigger was observed |
| tornado | 8 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| tornado | 9 | ok | ok | ok | no | test ran 1 test(s), but no failing/erroring trigger was observed |
| tornado | 10 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| tornado | 11 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| tornado | 12 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| tornado | 13 | ok | ok | ok | no | test ran 1 test(s), but no failing/erroring trigger was observed |
| tornado | 14 | ok | ok | ok | no | test ran 1 test(s), but no failing/erroring trigger was observed |
| tornado | 15 | ok | ok | ok | no | test ran 1 test(s), but no failing/erroring trigger was observed |
| tornado | 16 | ok | fail | skip | no | compile failed: Error: BugsInPy compile failed for /workspace/.workspace/bugsinpy/tornado_16/tornado. bugsinpy-safe-compile: this is not a checkout project folder: missing bugsinpy_requirements.txt |
| thefuck | 1 | ok | ok | ok | yes | trigger failure observed: tests=2, failing=1, errors=0 |
| thefuck | 2 | ok | ok | ok | yes | trigger failure observed: tests=2, failing=1, errors=0 |
| thefuck | 3 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| thefuck | 4 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| thefuck | 5 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| thefuck | 6 | ok | ok | ok | yes | trigger failure observed: tests=3, failing=1, errors=0 |
| thefuck | 7 | ok | ok | ok | yes | trigger failure observed: tests=2, failing=1, errors=0 |
| thefuck | 8 | ok | ok | ok | yes | trigger failure observed: tests=2, failing=2, errors=0 |
| thefuck | 9 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| thefuck | 10 | ok | ok | ok | yes | trigger failure observed: tests=8, failing=2, errors=0 |
| thefuck | 11 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| thefuck | 12 | ok | ok | ok | yes | trigger failure observed: tests=3, failing=3, errors=0 |
| thefuck | 13 | ok | ok | ok | yes | trigger failure observed: tests=2, failing=1, errors=0 |
| thefuck | 14 | ok | ok | ok | yes | trigger failure observed: tests=4, failing=4, errors=0 |
| thefuck | 15 | ok | ok | ok | yes | trigger failure observed: tests=2, failing=2, errors=0 |
| thefuck | 16 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| thefuck | 17 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| thefuck | 18 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| thefuck | 19 | ok | ok | ok | yes | trigger failure observed: tests=3, failing=3, errors=0 |
| thefuck | 20 | ok | ok | ok | yes | trigger failure observed: tests=4, failing=2, errors=0 |
| thefuck | 21 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| thefuck | 22 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| thefuck | 23 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| thefuck | 24 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| thefuck | 25 | ok | ok | ok | yes | trigger failure observed: tests=3, failing=2, errors=0 |
| thefuck | 26 | ok | ok | ok | yes | trigger failure observed: tests=4, failing=4, errors=0 |
| thefuck | 27 | ok | ok | ok | yes | trigger failure observed: tests=9, failing=3, errors=0 |
| thefuck | 28 | ok | ok | ok | yes | trigger failure observed: tests=22, failing=8, errors=6 |
| thefuck | 29 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| thefuck | 30 | ok | ok | ok | yes | trigger failure observed: tests=20, failing=20, errors=6 |
| thefuck | 31 | ok | ok | ok | yes | trigger failure observed: tests=2, failing=1, errors=0 |
| thefuck | 32 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| luigi | 1 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| luigi | 10 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| luigi | 11 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| luigi | 12 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| luigi | 13 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| luigi | 14 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| luigi | 15 | ok | ok | ok | yes | trigger failure observed: tests=1, failing=1, errors=0 |
| luigi | 16 | ok | interrupted | skip | no | scan stopped during compile after checkout succeeded; rerun this bug when resuming |

## Summary

Attempted bugs: 156
Usable bugs: 117
Unusable bugs: 39
Scan stopped after: interrupted during `luigi:16` compile after checkout succeeded. Resume from `luigi:16`; do not claim it usable until compile and test complete. Completed requested projects through spacy, tornado, thefuck, and luigi:15; remaining requested projects include the rest of luigi, youtube-dl, and pandas.

## Copy-ready usable bug command

```bash
python -m apr_framework bugsinpy evaluate-llm-repair \
  --bugs ansible:1,ansible:2,ansible:3,ansible:4,ansible:5,ansible:6,ansible:7,ansible:8,ansible:9,ansible:10,ansible:11,ansible:12,ansible:13,ansible:14,ansible:15,ansible:16,ansible:17,ansible:18,black:1,black:3,black:4,black:6,black:7,black:8,black:10,black:11,black:14,black:15,black:18,black:19,black:20,black:22,black:23,cookiecutter:1,cookiecutter:2,cookiecutter:3,fastapi:1,fastapi:2,fastapi:3,fastapi:4,fastapi:5,fastapi:6,fastapi:7,fastapi:8,fastapi:9,fastapi:10,fastapi:11,fastapi:12,fastapi:13,fastapi:14,fastapi:15,fastapi:16,httpie:1,httpie:2,httpie:3,httpie:4,httpie:5,sanic:1,sanic:3,sanic:5,tqdm:1,tqdm:2,tqdm:3,tqdm:4,tqdm:5,tqdm:6,tqdm:7,tqdm:8,tqdm:9,tornado:1,tornado:3,tornado:4,tornado:5,tornado:6,tornado:8,tornado:10,tornado:11,tornado:12,thefuck:1,thefuck:2,thefuck:3,thefuck:4,thefuck:5,thefuck:6,thefuck:7,thefuck:8,thefuck:9,thefuck:10,thefuck:11,thefuck:12,thefuck:13,thefuck:14,thefuck:15,thefuck:16,thefuck:17,thefuck:18,thefuck:19,thefuck:20,thefuck:21,thefuck:22,thefuck:23,thefuck:24,thefuck:25,thefuck:26,thefuck:27,thefuck:28,thefuck:29,thefuck:30,thefuck:31,thefuck:32,luigi:1,luigi:10,luigi:11,luigi:12,luigi:13,luigi:14,luigi:15
```
