root@26bdac3d4644:/workspace# python -m apr_framework bugsinpy compile black 1
Project: black
Bug ID: 1
Prepared: True
Worktree: /workspace/.workspace/bugsinpy/black_1/black
root@26bdac3d4644:/workspace# python -m apr_framework localize \
  --backend fauxpy \
  --project black \
  --bug 1 \
  --src . \
  --metric ochiai \
  --top-n 10 \
  --show-raw-output
Project: black
Bug ID: 1
Backend: fauxpy
Score formula: Ochiai
Ranked locations:
1. tests/test_black.py:81 0.9091
2. tests/test_black.py:80 0.9091
3. tests/test_black.py:78 0.9091
4. tests/test_black.py:77 0.9091
5. tests/test_black.py:76 0.9091
6. tests/test_black.py:162 0.9091
7. tests/test_black.py:161 0.9091
8. tests/test_black.py:160 0.9091
9. tests/test_black.py:159 0.9091
10. tests/test_black.py:158 0.9091

Raw FauxPy output:
============================= test session starts ==============================
platform linux -- Python 3.8.3, pytest-8.3.5, pluggy-1.5.0
rootdir: /home/workspace/black_1/black
configfile: pyproject.toml
plugins: timeout-2.1.0, fauxpy-0.7.0, anyio-4.5.2
collected 1 item

tests/test_black.py F                                                    [100%]

=================================== FAILURES ===================================
__________ BlackTestCase.test_works_in_mono_process_only_environment ___________

self = <tests.test_black.BlackTestCase testMethod=test_works_in_mono_process_only_environment>
mock_executor = <MagicMock name='ProcessPoolExecutor' spec='ProcessPoolExecutor' id='281473667282160'>

    @patch("black.ProcessPoolExecutor", autospec=True)
    def test_works_in_mono_process_only_environment(self, mock_executor) -> None:
        mock_executor.side_effect = OSError()
        mode = black.FileMode()
        with cache_dir() as workspace:
            one = (workspace / "one.py").resolve()
            with one.open("w") as fobj:
                fobj.write("print('hello')")
            two = (workspace / "two.py").resolve()
            with two.open("w") as fobj:
                fobj.write("print('hello')")
            black.write_cache({}, [one], mode)
>           self.invokeBlack([str(workspace)])

tests/test_black.py:1288: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_black.py:162: in invokeBlack
    self.assertEqual(result.exit_code, exit_code, msg=runner.stderr_bytes.decode())
E   AssertionError: 1 != 0 :
=============================== warnings summary ===============================
env/lib/python3.8/site-packages/aiohttp/helpers.py:107
  /home/workspace/black_1/black/env/lib/python3.8/site-packages/aiohttp/helpers.py:107: DeprecationWarning: "@coroutine" decorator is deprecated since Python 3.8, use "async def" instead
    def noop(*args, **kwargs):  # type: ignore

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html


***************************************************
                FauxPy Started!                    
***************************************************

FauxPy: ---> Running SBFL session
FauxPy: ---> Targeted failing tests:
FauxPy: --->   1. tests/test_black.py::BlackTestCase::test_works_in_mono_process_only_environment


==============================
 Dynamic Analysis in Progress 
==============================



--- Dynamic Analysis Complete ---

============================
 Fault Localization Results 
============================

=== Performance ===
Execution Time: 0.4339

----------------------------
|   Scores for Tarantula   |
----------------------------
File                | Line | Score 
-----------------------------------
tests/test_black.py |   81 | 1.1000
tests/test_black.py |   80 | 1.1000
tests/test_black.py |   78 | 1.1000
tests/test_black.py |   77 | 1.1000
tests/test_black.py |   76 | 1.1000
tests/test_black.py |  162 | 1.1000
tests/test_black.py |  161 | 1.1000
tests/test_black.py |  160 | 1.1000
tests/test_black.py |  159 | 1.1000
tests/test_black.py |  158 | 1.1000
tests/test_black.py |  130 | 1.1000
tests/test_black.py |  129 | 1.1000
tests/test_black.py | 1288 | 1.1000
tests/test_black.py | 1287 | 1.1000
tests/test_black.py | 1286 | 1.1000
tests/test_black.py | 1285 | 1.1000
tests/test_black.py | 1284 | 1.1000
tests/test_black.py | 1283 | 1.1000
tests/test_black.py | 1282 | 1.1000
tests/test_black.py | 1281 | 1.1000
tests/test_black.py | 1280 | 1.1000
tests/test_black.py |  128 | 1.1000
tests/test_black.py | 1279 | 1.1000
tests/test_black.py | 1278 | 1.1000
tests/test_black.py |  126 | 1.1000
tests/test_black.py |  125 | 1.1000
tests/test_black.py |  124 | 1.1000
tests/test_black.py |  123 | 1.1000
tests/test_black.py |  122 | 1.1000
tests/test_black.py |  118 | 1.1000
tests/test_black.py |  117 | 1.1000
tests/test_black.py |  116 | 1.1000
tests/test_black.py |  115 | 1.1000
tests/test_black.py |  114 | 1.1000
black.py            | 6315 | 1.1000
black.py            | 6314 | 1.1000
black.py            | 6313 | 1.1000
black.py            | 6312 | 1.1000
black.py            | 6311 | 1.1000
black.py            | 6310 | 1.1000
black.py            | 6309 | 1.1000
black.py            | 6288 | 1.1000
black.py            | 6287 | 1.1000
black.py            | 6264 | 1.1000
black.py            |  621 | 1.1000
black.py            |  618 | 1.1000
black.py            |  617 | 1.1000
black.py            |  616 | 1.1000
black.py            | 6091 | 1.1000
black.py            | 6090 | 1.1000
black.py            | 6088 | 1.1000
black.py            | 5780 | 1.1000
black.py            | 5777 | 1.1000
black.py            | 5774 | 1.1000
black.py            | 5771 | 1.1000
black.py            | 5770 | 1.1000
black.py            | 5769 | 1.1000
black.py            | 5767 | 1.1000
black.py            | 5766 | 1.1000
black.py            | 5763 | 1.1000
black.py            | 5750 | 1.1000
black.py            | 5749 | 1.1000
black.py            | 5748 | 1.1000
black.py            | 5747 | 1.1000
black.py            | 5742 | 1.1000
black.py            | 5738 | 1.1000
black.py            | 5737 | 1.1000
black.py            | 5734 | 1.1000
black.py            |  573 | 1.1000
black.py            | 5720 | 1.1000
black.py            | 5719 | 1.1000
black.py            | 5714 | 1.1000
black.py            | 5712 | 1.1000
black.py            | 5711 | 1.1000
black.py            | 5693 | 1.1000
black.py            | 5690 | 1.1000
black.py            | 5689 | 1.1000
black.py            | 5688 | 1.1000
black.py            |  558 | 1.1000
black.py            |  557 | 1.1000
black.py            |  548 | 1.1000
black.py            |  543 | 1.1000
black.py            |  535 | 1.1000
black.py            |  534 | 1.1000
black.py            |  533 | 1.1000
black.py            |  532 | 1.1000
black.py            |  531 | 1.1000
black.py            |  530 | 1.1000
black.py            |  529 | 1.1000
black.py            |  528 | 1.1000
black.py            |  527 | 1.1000
black.py            |  526 | 1.1000
black.py            |  522 | 1.1000
black.py            |  521 | 1.1000
black.py            |  517 | 1.1000
black.py            |  516 | 1.1000
black.py            |  513 | 1.1000
black.py            |  511 | 1.1000
black.py            |  509 | 1.1000
black.py            |  508 | 1.1000
black.py            |  507 | 1.1000
black.py            |  506 | 1.1000
black.py            |  505 | 1.1000
black.py            |  504 | 1.1000
black.py            |  496 | 1.1000
black.py            |  490 | 1.1000
black.py            |  489 | 1.1000
black.py            |  332 | 1.1000
black.py            |  307 | 1.1000
black.py            |  306 | 1.1000
black.py            |  300 | 1.1000
black.py            |  299 | 1.1000
black.py            |  294 | 1.1000
black.py            |  283 | 1.1000
black.py            |  282 | 1.1000
black.py            |  281 | 1.1000
black.py            |  258 | 1.1000
black.py            |  256 | 1.1000
black.py            |  255 | 1.1000
black.py            |  254 | 1.1000
black.py            |  253 | 1.1000
black.py            |  252 | 1.1000
black.py            |  251 | 1.1000
black.py            |  245 | 1.1000
black.py            |  159 | 1.1000
black.py            |  156 | 1.1000
black.py            |  153 | 1.1000
-----------------------------------

-------------------------
|   Scores for Ochiai   |
-------------------------
File                | Line | Score 
-----------------------------------
tests/test_black.py |   81 | 0.9091
tests/test_black.py |   80 | 0.9091
tests/test_black.py |   78 | 0.9091
tests/test_black.py |   77 | 0.9091
tests/test_black.py |   76 | 0.9091
tests/test_black.py |  162 | 0.9091
tests/test_black.py |  161 | 0.9091
tests/test_black.py |  160 | 0.9091
tests/test_black.py |  159 | 0.9091
tests/test_black.py |  158 | 0.9091
tests/test_black.py |  130 | 0.9091
tests/test_black.py |  129 | 0.9091
tests/test_black.py | 1288 | 0.9091
tests/test_black.py | 1287 | 0.9091
tests/test_black.py | 1286 | 0.9091
tests/test_black.py | 1285 | 0.9091
tests/test_black.py | 1284 | 0.9091
tests/test_black.py | 1283 | 0.9091
tests/test_black.py | 1282 | 0.9091
tests/test_black.py | 1281 | 0.9091
tests/test_black.py | 1280 | 0.9091
tests/test_black.py |  128 | 0.9091
tests/test_black.py | 1279 | 0.9091
tests/test_black.py | 1278 | 0.9091
tests/test_black.py |  126 | 0.9091
tests/test_black.py |  125 | 0.9091
tests/test_black.py |  124 | 0.9091
tests/test_black.py |  123 | 0.9091
tests/test_black.py |  122 | 0.9091
tests/test_black.py |  118 | 0.9091
tests/test_black.py |  117 | 0.9091
tests/test_black.py |  116 | 0.9091
tests/test_black.py |  115 | 0.9091
tests/test_black.py |  114 | 0.9091
black.py            | 6315 | 0.9091
black.py            | 6314 | 0.9091
black.py            | 6313 | 0.9091
black.py            | 6312 | 0.9091
black.py            | 6311 | 0.9091
black.py            | 6310 | 0.9091
black.py            | 6309 | 0.9091
black.py            | 6288 | 0.9091
black.py            | 6287 | 0.9091
black.py            | 6264 | 0.9091
black.py            |  621 | 0.9091
black.py            |  618 | 0.9091
black.py            |  617 | 0.9091
black.py            |  616 | 0.9091
black.py            | 6091 | 0.9091
black.py            | 6090 | 0.9091
black.py            | 6088 | 0.9091
black.py            | 5780 | 0.9091
black.py            | 5777 | 0.9091
black.py            | 5774 | 0.9091
black.py            | 5771 | 0.9091
black.py            | 5770 | 0.9091
black.py            | 5769 | 0.9091
black.py            | 5767 | 0.9091
black.py            | 5766 | 0.9091
black.py            | 5763 | 0.9091
black.py            | 5750 | 0.9091
black.py            | 5749 | 0.9091
black.py            | 5748 | 0.9091
black.py            | 5747 | 0.9091
black.py            | 5742 | 0.9091
black.py            | 5738 | 0.9091
black.py            | 5737 | 0.9091
black.py            | 5734 | 0.9091
black.py            |  573 | 0.9091
black.py            | 5720 | 0.9091
black.py            | 5719 | 0.9091
black.py            | 5714 | 0.9091
black.py            | 5712 | 0.9091
black.py            | 5711 | 0.9091
black.py            | 5693 | 0.9091
black.py            | 5690 | 0.9091
black.py            | 5689 | 0.9091
black.py            | 5688 | 0.9091
black.py            |  558 | 0.9091
black.py            |  557 | 0.9091
black.py            |  548 | 0.9091
black.py            |  543 | 0.9091
black.py            |  535 | 0.9091
black.py            |  534 | 0.9091
black.py            |  533 | 0.9091
black.py            |  532 | 0.9091
black.py            |  531 | 0.9091
black.py            |  530 | 0.9091
black.py            |  529 | 0.9091
black.py            |  528 | 0.9091
black.py            |  527 | 0.9091
black.py            |  526 | 0.9091
black.py            |  522 | 0.9091
black.py            |  521 | 0.9091
black.py            |  517 | 0.9091
black.py            |  516 | 0.9091
black.py            |  513 | 0.9091
black.py            |  511 | 0.9091
black.py            |  509 | 0.9091
black.py            |  508 | 0.9091
black.py            |  507 | 0.9091
black.py            |  506 | 0.9091
black.py            |  505 | 0.9091
black.py            |  504 | 0.9091
black.py            |  496 | 0.9091
black.py            |  490 | 0.9091
black.py            |  489 | 0.9091
black.py            |  332 | 0.9091
black.py            |  307 | 0.9091
black.py            |  306 | 0.9091
black.py            |  300 | 0.9091
black.py            |  299 | 0.9091
black.py            |  294 | 0.9091
black.py            |  283 | 0.9091
black.py            |  282 | 0.9091
black.py            |  281 | 0.9091
black.py            |  258 | 0.9091
black.py            |  256 | 0.9091
black.py            |  255 | 0.9091
black.py            |  254 | 0.9091
black.py            |  253 | 0.9091
black.py            |  252 | 0.9091
black.py            |  251 | 0.9091
black.py            |  245 | 0.9091
black.py            |  159 | 0.9091
black.py            |  156 | 0.9091
black.py            |  153 | 0.9091
-----------------------------------

------------------------
|   Scores for Dstar   |
------------------------
File                | Line | Score  
------------------------------------
tests/test_black.py |   81 | 10.0000
tests/test_black.py |   80 | 10.0000
tests/test_black.py |   78 | 10.0000
tests/test_black.py |   77 | 10.0000
tests/test_black.py |   76 | 10.0000
tests/test_black.py |  162 | 10.0000
tests/test_black.py |  161 | 10.0000
tests/test_black.py |  160 | 10.0000
tests/test_black.py |  159 | 10.0000
tests/test_black.py |  158 | 10.0000
tests/test_black.py |  130 | 10.0000
tests/test_black.py |  129 | 10.0000
tests/test_black.py | 1288 | 10.0000
tests/test_black.py | 1287 | 10.0000
tests/test_black.py | 1286 | 10.0000
tests/test_black.py | 1285 | 10.0000
tests/test_black.py | 1284 | 10.0000
tests/test_black.py | 1283 | 10.0000
tests/test_black.py | 1282 | 10.0000
tests/test_black.py | 1281 | 10.0000
tests/test_black.py | 1280 | 10.0000
tests/test_black.py |  128 | 10.0000
tests/test_black.py | 1279 | 10.0000
tests/test_black.py | 1278 | 10.0000
tests/test_black.py |  126 | 10.0000
tests/test_black.py |  125 | 10.0000
tests/test_black.py |  124 | 10.0000
tests/test_black.py |  123 | 10.0000
tests/test_black.py |  122 | 10.0000
tests/test_black.py |  118 | 10.0000
tests/test_black.py |  117 | 10.0000
tests/test_black.py |  116 | 10.0000
tests/test_black.py |  115 | 10.0000
tests/test_black.py |  114 | 10.0000
black.py            | 6315 | 10.0000
black.py            | 6314 | 10.0000
black.py            | 6313 | 10.0000
black.py            | 6312 | 10.0000
black.py            | 6311 | 10.0000
black.py            | 6310 | 10.0000
black.py            | 6309 | 10.0000
black.py            | 6288 | 10.0000
black.py            | 6287 | 10.0000
black.py            | 6264 | 10.0000
black.py            |  621 | 10.0000
black.py            |  618 | 10.0000
black.py            |  617 | 10.0000
black.py            |  616 | 10.0000
black.py            | 6091 | 10.0000
black.py            | 6090 | 10.0000
black.py            | 6088 | 10.0000
black.py            | 5780 | 10.0000
black.py            | 5777 | 10.0000
black.py            | 5774 | 10.0000
black.py            | 5771 | 10.0000
black.py            | 5770 | 10.0000
black.py            | 5769 | 10.0000
black.py            | 5767 | 10.0000
black.py            | 5766 | 10.0000
black.py            | 5763 | 10.0000
black.py            | 5750 | 10.0000
black.py            | 5749 | 10.0000
black.py            | 5748 | 10.0000
black.py            | 5747 | 10.0000
black.py            | 5742 | 10.0000
black.py            | 5738 | 10.0000
black.py            | 5737 | 10.0000
black.py            | 5734 | 10.0000
black.py            |  573 | 10.0000
black.py            | 5720 | 10.0000
black.py            | 5719 | 10.0000
black.py            | 5714 | 10.0000
black.py            | 5712 | 10.0000
black.py            | 5711 | 10.0000
black.py            | 5693 | 10.0000
black.py            | 5690 | 10.0000
black.py            | 5689 | 10.0000
black.py            | 5688 | 10.0000
black.py            |  558 | 10.0000
black.py            |  557 | 10.0000
black.py            |  548 | 10.0000
black.py            |  543 | 10.0000
black.py            |  535 | 10.0000
black.py            |  534 | 10.0000
black.py            |  533 | 10.0000
black.py            |  532 | 10.0000
black.py            |  531 | 10.0000
black.py            |  530 | 10.0000
black.py            |  529 | 10.0000
black.py            |  528 | 10.0000
black.py            |  527 | 10.0000
black.py            |  526 | 10.0000
black.py            |  522 | 10.0000
black.py            |  521 | 10.0000
black.py            |  517 | 10.0000
black.py            |  516 | 10.0000
black.py            |  513 | 10.0000
black.py            |  511 | 10.0000
black.py            |  509 | 10.0000
black.py            |  508 | 10.0000
black.py            |  507 | 10.0000
black.py            |  506 | 10.0000
black.py            |  505 | 10.0000
black.py            |  504 | 10.0000
black.py            |  496 | 10.0000
black.py            |  490 | 10.0000
black.py            |  489 | 10.0000
black.py            |  332 | 10.0000
black.py            |  307 | 10.0000
black.py            |  306 | 10.0000
black.py            |  300 | 10.0000
black.py            |  299 | 10.0000
black.py            |  294 | 10.0000
black.py            |  283 | 10.0000
black.py            |  282 | 10.0000
black.py            |  281 | 10.0000
black.py            |  258 | 10.0000
black.py            |  256 | 10.0000
black.py            |  255 | 10.0000
black.py            |  254 | 10.0000
black.py            |  253 | 10.0000
black.py            |  252 | 10.0000
black.py            |  251 | 10.0000
black.py            |  245 | 10.0000
black.py            |  159 | 10.0000
black.py            |  156 | 10.0000
black.py            |  153 | 10.0000
------------------------------------

**************************************************
                FauxPy Ended!                     
**************************************************

=========================== short test summary info ============================
FAILED tests/test_black.py::BlackTestCase::test_works_in_mono_process_only_environment
========================= 1 failed, 1 warning in 0.43s =========================
root@26bdac3d4644:/workspace# 