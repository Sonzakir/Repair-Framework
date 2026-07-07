%																	      fazlisonerkiraz@Soners-MacBook-Pro Repair-Framework % docker compose run apr-framework
WARN[0000] Found orphan containers ([repair-framework-apr-framework-run-a30fc4b836f7 repair-framework-apr-framework-run-940f2b0a3c23 repair-framework-apr-framework-run-601a29359eb6]) for this project. If you removed or renamed this service in your compose file, you can run this command with the --remove-orphans flag to clean it up.
[+] create 1/1
 ✔ Network repair-framework_default Created												 0.0s
[+]  1/1
 ✔ Network repair-framework_default Created												 0.0s
Container repair-framework-apr-framework-run-41ac656ca1ea Creating
Container repair-framework-apr-framework-run-41ac656ca1ea Created
root@45ea503ed258:/workspace# APR_LLM_DEBUG_PROMPT=/workspace/runs/prompt_dumps_iter/auto \
python -m apr_framework repair --project black --bug 1 \
  --technique llm --iterative --max-iterations 5 \
  --fl-mode auto --fl-family sbfl --localization-metric ochiai \
  --stop-on-first --runs-dir runs
APR_LLM_DEBUG_PROMPT=/workspace/runs/prompt_dumps_iter/auto \
python -m apr_framework repair --project black --bug 1 \
  --technique llm --iterative --max-iterations 5 \
  --fl-mode auto --fl-family sbfl --localization-metric ochiai \
  --stop-on-first --runs-dir runs

apr-bugsinpy-executor

Run directory: /workspace/runs/run_163
Project:       black
Bug ID:        1
Status:        failed
Generated:     21 candidate(s)
Validated:     21 candidate(s)
Plausible:     0 patch(es)
Correct:       0 patch(es)
1st plausible: n/a
Total time:    45.0s
root@45ea503ed258:/workspace# APR_LLM_DEBUG_PROMPT=/workspace/runs/prompt_dumps_iter/perfect \
python -m apr_framework repair --project black --bug 1 \
  --technique llm --iterative --max-iterations 5 \
  --fl-mode perfect \
  --stop-on-first --runs-dir runs
APR_LLM_DEBUG_PROMPT=/workspace/runs/prompt_dumps_iter/perfect \
python -m apr_framework repair --project black --bug 1 \
  --technique llm --iterative --max-iterations 5 \
  --fl-mode perfect \
  --stop-on-first --runs-dir runs


Run directory: /workspace/runs/run_164
Project:       black
Bug ID:        1
Status:        plausible
Generated:     1 candidate(s)
Validated:     1 candidate(s)
Plausible:     1 patch(es)
Correct:       0 patch(es)
1st plausible: 17.9s
Total time:    17.9s
root@45ea503ed258:/workspace# APR_LLM_DEBUG_PROMPT=/workspace/runs/prompt_dumps_iter/perfect python -m apr_framework repair --project black --bug 1   --technique llm --iterative --max-iterations 5   --fl-mode perfect   --stop-on-first --runs-dir runs

Run directory: /workspace/runs/run_165
Project:       black
Bug ID:        1
Status:        plausible
Generated:     2 candidate(s)
Validated:     2 candidate(s)
Plausible:     1 patch(es)
Correct:       0 patch(es)
1st plausible: 28.8s
Total time:    28.8s
root@45ea503ed258:/workspace# python -m apr_framework bugsinpy test black 8

APR_LLM_DEBUG_PROMPT=/workspace/runs/prompt_dumps_iter/black8_perfect \
python -m apr_framework repair --project black --bug 8 \
  --technique llm --iterative --max-iterations 5 \
  --fl-mode perfect \
  --stop-on-first --runs-dir runs
python -m apr_framework bugsinpy test black 8

APR_LLM_DEBUG_PROMPT=/workspace/runs/prompt_dumps_iter/black8_perfect \
python -m apr_framework repair --project black --bug 8 \
  --technique llm --iterative --max-iterations 5 \
  --fl-mode perfect \
  --stop-on-first --runs-dir runs

Project: black
Bug ID: 8
Checkout success: True
Prepared: True
Tests run: 1
Passing: 0
Failing: 1

Raw output:
python -m unittest -q tests.test_black.BlackTestCase.test_comments7
RUN EVERY COMMAND
0


Expected tree:
file_input
  simple_stmt
    import_from
      NAME 'from'
      DOT ' ' '.'
      NAME 'config'
      NAME ' ' 'import'
      LPAR ' ' '('
      import_as_names
	NAME '\n    ' 'Any'
	COMMA ','
	NAME '\n    ' 'Bool'
	COMMA ','
	NAME '\n    ' 'ConfigType'
	COMMA ','
	NAME '\n    ' 'ConfigTypeAttributes'
	COMMA ','
	NAME '\n    ' 'Int'
	COMMA ','
	NAME '\n    ' 'Path'
	COMMA ','
      /import_as_names
      RPAR '\n	  #  String,\n	  #  resolve_to_config_type,\n	  #  DEFAULT_TYPE_ATTRIBUTES,\n' ')'
    /import_from
    NEWLINE '\n'
  /simple_stmt
  simple_stmt
    import_from
      NAME '\n\n' 'from'
      DOT ' ' '.'
      NAME 'config'
      NAME ' ' 'import'
      LPAR ' ' '('
      import_as_names
	NAME '\n    ' 'Any'
	COMMA ','
	NAME '\n    ' 'Bool'
	COMMA ','
	NAME '\n    ' 'ConfigType'
	COMMA ','
	NAME '\n    ' 'ConfigTypeAttributes'
	COMMA ','
	NAME '\n    ' 'Int'
	COMMA ','
	NAME '\n    ' 'no_comma_here_yet'
	COMMA ','
      /import_as_names
      RPAR '\n	  #  and some comments,\n    #	resolve_to_config_type,\n    #	DEFAULT_TYPE_ATTRIBUTES,\n' ')'
    /import_from
    NEWLINE '\n'
  /simple_stmt
  ENDMARKER ''
/file_input
Actual tree:
Cannot parse: 11:4:	,
======================================================================
FAIL: test_comments7 (tests.test_black.BlackTestCase)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/root/.pyenv/versions/3.8.3/lib/python3.8/unittest/mock.py", line 1325, in patched
    return func(*newargs, **newkeywargs)
  File "/home/workspace/black_8/black/tests/test_black.py", line 395, in test_comments7
    self.assertFormatEqual(expected, actual)
  File "/home/workspace/black_8/black/tests/test_black.py", line 159, in assertFormatEqual
    self.assertEqual(expected, actual)
AssertionError: 'from[181 chars]ES,\n)\n\n\nfrom .config import (\n    Any,\n [179 chars]n)\n' != 'from[181 chars]ES,\n    ,\n)\n\n\nfrom .config import (\n	[192 chars]n)\n'
  from .config import (
      Any,
      Bool,
      ConfigType,
      ConfigTypeAttributes,
      Int,
      Path,
      #  String,
      #  resolve_to_config_type,
      #  DEFAULT_TYPE_ATTRIBUTES,
+     ,
  )


  from .config import (
      Any,
      Bool,
      ConfigType,
      ConfigTypeAttributes,
      Int,
-     no_comma_here_yet,
?		       -
+     no_comma_here_yet
      #  and some comments,
      #  resolve_to_config_type,
      #  DEFAULT_TYPE_ATTRIBUTES,
+     ,
  )


----------------------------------------------------------------------
Ran 1 test in 0.002s

FAILED (failures=1)
LLM response for black.py contains invalid Python syntax: closing parenthesis ']' does not match opening parenthesis '(' on line 2393 (<unknown>, line 2394)
LLM response for black.py contains invalid Python syntax: closing parenthesis ']' does not match opening parenthesis '(' on line 2393 (<unknown>, line 2394)
Giving up on black.py:2408 after 2 unparsable replies
LLM response for black.py contains invalid Python syntax: closing parenthesis ']' does not match opening parenthesis '(' on line 2393 (<unknown>, line 2394)
LLM response for black.py contains invalid Python syntax: closing parenthesis ']' does not match opening parenthesis '(' on line 2393 (<unknown>, line 2394)
Giving up on black.py:2410 after 2 unparsable replies

Run directory: /workspace/runs/run_166
Project:       black
Bug ID:        8
Status:        failed
Generated:     7 candidate(s)
Validated:     7 candidate(s)
Plausible:     0 patch(es)
Correct:       0 patch(es)
1st plausible: n/a
Total time:    24.9s
root@45ea503ed258:/workspace# exit
exit
%																	      fazlisonerkiraz@Soners-MacBook-Pro Repair-Framework % exit



root@61dd51806391:/workspace# python -m apr_framework repair     --project black     --bug 1     --technique llm     --model gpt-5.4     --llm-base-url https://api.openai.com/v1     --llm-api-key-env OPENAI_API_KEY     --fl-mode perfect     --temperature 1

Run directory: /workspace/runs/run_224
Project:       black
Bug ID:        1
Status:        plausible
Generated:     15 candidate(s)
Validated:     15 candidate(s)
Plausible:     6 patch(es)
Correct:       0 patch(es)
1st plausible: 63.3s
Total time:    142.7s



root@61dd51806391:/workspace# python -m apr_framework repair \
    --project black \
    --bug 1 \
    --technique llm \
    --model gpt-5.4 \
    --llm-base-url https://api.openai.com/v1 \
    --llm-api-key-env OPENAI_API_KEY \
    --fl-mode perfect \
    --temperature 1 \
    --stop-on-first

Run directory: /workspace/runs/run_226
Project:       black
Bug ID:        1
Status:        plausible
Generated:     15 candidate(s)
Validated:     1 candidate(s)
Plausible:     1 patch(es)
Correct:       0 patch(es)
1st plausible: 62.9s
Total time:    62.9s