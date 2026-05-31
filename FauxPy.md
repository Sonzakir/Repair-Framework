- Pytest plugin 
- install -> run tests with pytest -> add `--src` to tell FauxPy which source tree to analyze


## Example Output
### Run all tests in package tests `python -m pytest tests`

```bash
 
(env) Soners-MacBook-Pro:fauxpy_example1 fazlisonerkiraz$ python -m pytest tests
===================================================== test session starts ======================================================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fazlisonerkiraz/fauxpy_example1
plugins: anyio-4.12.1, timeout-2.1.0, fauxpy-0.7.0
collected 4 items                                                                                                              

tests/test_equilateral.py F.                                                                                             [ 50%]
tests/test_isosceles.py F.                                                                                               [100%]

=========================================================== FAILURES ===========================================================
_________________________________________________________ test_ea_fail _________________________________________________________

    def test_ea_fail():
        a = 3
        area = equilateral_area(a)
>       assert area == pytest.approx(9 * math.sqrt(3) / 4)
E       assert 9.433012701892219 == 3.8971143170299736 ± 3.9e-06
E         
E         comparison failed
E         Obtained: 9.433012701892219
E         Expected: 3.8971143170299736 ± 3.9e-06

tests/test_equilateral.py:11: AssertionError
________________________________________________________ test_ia_crash _________________________________________________________

    def test_ia_crash():
        leg, base = 9, 4
    
>       area = isosceles_area(leg, base)

tests/test_isosceles.py:11: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
code/isosceles.py:10: in isosceles_area
    area = 0.5 * base * height()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    def height():
        t1, t2 = math.pow(base, 2), math.pow(leg, 2) / 4  # bug
        # t1, t2 = math.pow(leg, 2), math.pow(base, 2) / 4  # patch
>       return math.sqrt(t1 - t2)
E       ValueError: math domain error

code/isosceles.py:8: ValueError
=================================================== short test summary info ====================================================
FAILED tests/test_equilateral.py::test_ea_fail - assert 9.433012701892219 == 3.8971143170299736 ± 3.9e-06
FAILED tests/test_isosceles.py::test_ia_crash - ValueError: math domain error
================================================= 2 failed, 2 passed in 0.05s ==================================================
(env) Soners-MacBook-Pro:fauxpy_example1 fazlisonerkiraz$ 



```


### Running spectrum based fault localization **SBFL**
- In this example the source code of the project is in package `code`  we pass code to --src.

```bash
(env) Soners-MacBook-Pro:fauxpy_example1 fazlisonerkiraz$ python -m pytest tests --src code
===================================================== test session starts ======================================================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fazlisonerkiraz/fauxpy_example1
plugins: anyio-4.12.1, timeout-2.1.0, fauxpy-0.7.0
collected 4 items                                                                                                              

tests/test_equilateral.py F.                                                                                             [ 50%]
tests/test_isosceles.py F.                                                                                               [100%]

=========================================================== FAILURES ===========================================================
_________________________________________________________ test_ea_fail _________________________________________________________

    def test_ea_fail():
        a = 3
        area = equilateral_area(a)
>       assert area == pytest.approx(9 * math.sqrt(3) / 4)
E       assert 9.433012701892219 == 3.8971143170299736 ± 3.9e-06
E         
E         comparison failed
E         Obtained: 9.433012701892219
E         Expected: 3.8971143170299736 ± 3.9e-06

tests/test_equilateral.py:11: AssertionError
________________________________________________________ test_ia_crash _________________________________________________________

    def test_ia_crash():
        leg, base = 9, 4
    
>       area = isosceles_area(leg, base)

tests/test_isosceles.py:11: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
code/isosceles.py:10: in isosceles_area
    area = 0.5 * base * height()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    def height():
        t1, t2 = math.pow(base, 2), math.pow(leg, 2) / 4  # bug
        # t1, t2 = math.pow(leg, 2), math.pow(base, 2) / 4  # patch
>       return math.sqrt(t1 - t2)
E       ValueError: math domain error

code/isosceles.py:8: ValueError


***************************************************
                FauxPy Started!                    
***************************************************

FauxPy: ---> Running SBFL session


==============================
 Dynamic Analysis in Progress 
==============================



--- Dynamic Analysis Complete ---

============================
 Fault Localization Results 
============================

=== Performance ===
Execution Time: 0.0821

----------------------------
|   Scores for Tarantula   |
----------------------------
File                | Line | Score 
-----------------------------------
code/equilateral.py |   13 | 1.1000
code/equilateral.py |   11 | 1.1000
code/equilateral.py |   10 | 1.1000
code/isosceles.py   |    8 | 0.6000
code/isosceles.py   |    6 | 0.6000
code/isosceles.py   |    5 | 0.6000
code/isosceles.py   |   10 | 0.6000
code/equilateral.py |    7 | 0.6000
code/equilateral.py |    5 | 0.6000
code/isosceles.py   |   11 | 0.1000
code/equilateral.py |    8 | 0.1000
-----------------------------------

-------------------------
|   Scores for Ochiai   |
-------------------------
File                | Line | Score 
-----------------------------------
code/equilateral.py |   13 | 0.6604
code/equilateral.py |   11 | 0.6604
code/equilateral.py |   10 | 0.6604
code/isosceles.py   |    8 | 0.4762
code/isosceles.py   |    6 | 0.4762
code/isosceles.py   |    5 | 0.4762
code/isosceles.py   |   10 | 0.4762
code/equilateral.py |    7 | 0.4762
code/equilateral.py |    5 | 0.4762
code/isosceles.py   |   11 | 0.0000
code/equilateral.py |    8 | 0.0000
-----------------------------------

------------------------
|   Scores for Dstar   |
------------------------
File                | Line | Score 
-----------------------------------
code/equilateral.py |   13 | 0.9091
code/equilateral.py |   11 | 0.9091
code/equilateral.py |   10 | 0.9091
code/isosceles.py   |    8 | 0.4762
code/isosceles.py   |    6 | 0.4762
code/isosceles.py   |    5 | 0.4762
code/isosceles.py   |   10 | 0.4762
code/equilateral.py |    7 | 0.4762
code/equilateral.py |    5 | 0.4762
code/isosceles.py   |   11 | 0.0000
code/equilateral.py |    8 | 0.0000
-----------------------------------

**************************************************
                FauxPy Ended!                     
**************************************************

=================================================== short test summary info ====================================================
FAILED tests/test_equilateral.py::test_ea_fail - assert 9.433012701892219 == 3.8971143170299736 ± 3.9e-06
FAILED tests/test_isosceles.py::test_ia_crash - ValueError: math domain error
================================================= 2 failed, 2 passed in 0.08s ==================================================
(env) Soners-MacBook-Pro:fauxpy_example1 fazlisonerkiraz$ 
```

### Analyze each bug seperately
- Instead of localizing multiple bugs in one go. 
- Two options:
    - 1. Selecting the test
    - 2. Selecting the failing tests 

#### 1. Selecting the tests
- run fauxpy using only tests in test_equilateral.py. 
    - Since the failing test in test_equilateral.py is related to a single bug => FauxPy only localizes that one bug
    - `python -m pytest tests/test_equilateral.py --src code`

```bash
env) Soners-MacBook-Pro:fauxpy_example1 fazlisonerkiraz$ python -m pytest tests/test_equilateral.py --src code
=================================================================================================== test session starts ===================================================================================================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fazlisonerkiraz/fauxpy_example1
plugins: anyio-4.12.1, timeout-2.1.0, fauxpy-0.7.0
collected 2 items                                                                                                                                                                                                         

tests/test_equilateral.py F.                                                                                                                                                                                        [100%]

======================================================================================================== FAILURES =========================================================================================================
______________________________________________________________________________________________________ test_ea_fail _______________________________________________________________________________________________________

    def test_ea_fail():
        a = 3
        area = equilateral_area(a)
>       assert area == pytest.approx(9 * math.sqrt(3) / 4)
E       assert 9.433012701892219 == 3.8971143170299736 ± 3.9e-06
E         
E         comparison failed
E         Obtained: 9.433012701892219
E         Expected: 3.8971143170299736 ± 3.9e-06

tests/test_equilateral.py:11: AssertionError


***************************************************
                FauxPy Started!                    
***************************************************

FauxPy: ---> Running SBFL session


==============================
 Dynamic Analysis in Progress 
==============================



--- Dynamic Analysis Complete ---

============================
 Fault Localization Results 
============================

=== Performance ===
Execution Time: 0.0611

----------------------------
|   Scores for Tarantula   |
----------------------------
File                | Line | Score 
-----------------------------------
code/equilateral.py |   13 | 1.1000
code/equilateral.py |   11 | 1.1000
code/equilateral.py |   10 | 1.1000
code/equilateral.py |    7 | 0.6000
code/equilateral.py |    5 | 0.6000
code/equilateral.py |    8 | 0.1000
-----------------------------------

-------------------------
|   Scores for Ochiai   |
-------------------------
File                | Line | Score 
-----------------------------------
code/equilateral.py |   13 | 0.9091
code/equilateral.py |   11 | 0.9091
code/equilateral.py |   10 | 0.9091
code/equilateral.py |    7 | 0.6604
code/equilateral.py |    5 | 0.6604
code/equilateral.py |    8 | 0.0000
-----------------------------------

------------------------
|   Scores for Dstar   |
------------------------
File                | Line | Score  
------------------------------------
code/equilateral.py |   13 | 10.0000
code/equilateral.py |   11 | 10.0000
code/equilateral.py |   10 | 10.0000
code/equilateral.py |    7 |  0.9091
code/equilateral.py |    5 |  0.9091
code/equilateral.py |    8 |  0.0000
------------------------------------

**************************************************
                FauxPy Ended!                     
**************************************************

================================================================================================= short test summary info =================================================================================================
FAILED tests/test_equilateral.py::test_ea_fail - assert 9.433012701892219 == 3.8971143170299736 ± 3.9e-06
=============================================================================================== 1 failed, 1 passed in 0.05s ===============================================================================================
(env) Soners-MacBook-Pro:fauxpy_example1 fazlisonerkiraz$ 
```

#### 2. Selecting the Failing Tests 
- Don't look at everything. I know there is a bug, and I know exactly which test is triggering it (test_ea_fail). Just run that one specific failing test and track what the code is doing."
- `python -m pytest tests --src code --failing-list "[tests/test_equilateral.py::test_ea_fail]"`
- For instance, the following command runs fault localization on the project in the current directory, using only test function test_read_file in class Test_IO as failing test:    
```bash
python -m pytest --src . \
       --failing-list "[test/test_common/test_file.py::Test_IO::test_read_file]"
```

- Example output:
```bash
(env) Soners-MacBook-Pro:fauxpy_example1 fazlisonerkiraz$ python -m pytest tests --src code --failing-list "[tests/test_equilateral.py::test_ea_fail]"
=================================================================================================== test session starts ===================================================================================================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fazlisonerkiraz/fauxpy_example1
plugins: anyio-4.12.1, timeout-2.1.0, fauxpy-0.7.0
collected 4 items                                                                                                                                                                                                         

tests/test_equilateral.py F.                                                                                                                                                                                        [ 50%]
tests/test_isosceles.py F.                                                                                                                                                                                          [100%]

======================================================================================================== FAILURES =========================================================================================================
______________________________________________________________________________________________________ test_ea_fail _______________________________________________________________________________________________________

    def test_ea_fail():
        a = 3
        area = equilateral_area(a)
>       assert area == pytest.approx(9 * math.sqrt(3) / 4)
E       assert 9.433012701892219 == 3.8971143170299736 ± 3.9e-06
E         
E         comparison failed
E         Obtained: 9.433012701892219
E         Expected: 3.8971143170299736 ± 3.9e-06

tests/test_equilateral.py:11: AssertionError
______________________________________________________________________________________________________ test_ia_crash ______________________________________________________________________________________________________

    def test_ia_crash():
        leg, base = 9, 4
    
>       area = isosceles_area(leg, base)

tests/test_isosceles.py:11: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
code/isosceles.py:10: in isosceles_area
    area = 0.5 * base * height()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def height():
        t1, t2 = math.pow(base, 2), math.pow(leg, 2) / 4  # bug
        # t1, t2 = math.pow(leg, 2), math.pow(base, 2) / 4  # patch
>       return math.sqrt(t1 - t2)
E       ValueError: math domain error

code/isosceles.py:8: ValueError


***************************************************
                FauxPy Started!                    
***************************************************

FauxPy: ---> Running SBFL session
FauxPy: ---> Targeted failing tests:
FauxPy: --->   1. tests/test_equilateral.py::test_ea_fail


==============================
 Dynamic Analysis in Progress 
==============================



--- Dynamic Analysis Complete ---

============================
 Fault Localization Results 
============================

=== Performance ===
Execution Time: 0.0706

----------------------------
|   Scores for Tarantula   |
----------------------------
File                | Line | Score 
-----------------------------------
code/equilateral.py |   13 | 1.1000
code/equilateral.py |   11 | 1.1000
code/equilateral.py |   10 | 1.1000
code/equilateral.py |    7 | 0.7562
code/equilateral.py |    5 | 0.7562
code/isosceles.py   |    8 | 0.1000
code/isosceles.py   |    6 | 0.1000
code/isosceles.py   |    5 | 0.1000
code/isosceles.py   |   11 | 0.1000
code/isosceles.py   |   10 | 0.1000
code/equilateral.py |    8 | 0.1000
-----------------------------------

-------------------------
|   Scores for Ochiai   |
-------------------------
File                | Line | Score 
-----------------------------------
code/equilateral.py |   13 | 0.9091
code/equilateral.py |   11 | 0.9091
code/equilateral.py |   10 | 0.9091
code/equilateral.py |    7 | 0.6604
code/equilateral.py |    5 | 0.6604
code/isosceles.py   |    8 | 0.0000
code/isosceles.py   |    6 | 0.0000
code/isosceles.py   |    5 | 0.0000
code/isosceles.py   |   11 | 0.0000
code/isosceles.py   |   10 | 0.0000
code/equilateral.py |    8 | 0.0000
-----------------------------------

------------------------
|   Scores for Dstar   |
------------------------
File                | Line | Score  
------------------------------------
code/equilateral.py |   13 | 10.0000
code/equilateral.py |   11 | 10.0000
code/equilateral.py |   10 | 10.0000
code/equilateral.py |    7 |  0.9091
code/equilateral.py |    5 |  0.9091
code/isosceles.py   |    8 |  0.0000
code/isosceles.py   |    6 |  0.0000
code/isosceles.py   |    5 |  0.0000
code/isosceles.py   |   11 |  0.0000
code/isosceles.py   |   10 |  0.0000
code/equilateral.py |    8 |  0.0000
------------------------------------

**************************************************
                FauxPy Ended!                     
**************************************************

================================================================================================= short test summary info =================================================================================================
FAILED tests/test_equilateral.py::test_ea_fail - assert 9.433012701892219 == 3.8971143170299736 ± 3.9e-06
FAILED tests/test_isosceles.py::test_ia_crash - ValueError: math domain error
=============================================================================================== 2 failed, 2 passed in 0.06s ===============================================================================================
(env) Soners-MacBook-Pro:fauxpy_example1 fazlisonerkiraz$ 
```


### Running mutation-based fault localization (**MBFL**)

- To run MBFL techniques --> pass option `--family mbfl`
- Example command and output:
```bash
python -m pytest tests --src code --family mbfl --failing-list "[tests/test_equilateral.py::test_ea_fail]"
```

```bash
(env) Soners-MacBook-Pro:fauxpy_example1 fazlisonerkiraz$ python -m pytest tests --src code --family mbfl --failing-list "[tests/test_equilateral.py::test_ea_fail]"
=================================================================================================== test session starts ===================================================================================================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fazlisonerkiraz/fauxpy_example1
plugins: anyio-4.12.1, timeout-2.1.0, fauxpy-0.7.0
collected 4 items                                                                                                                                                                                                         

tests/test_equilateral.py F.                                                                                                                                                                                        [ 50%]
tests/test_isosceles.py F.                                                                                                                                                                                          [100%]

======================================================================================================== FAILURES =========================================================================================================
______________________________________________________________________________________________________ test_ea_fail _______________________________________________________________________________________________________

    def test_ea_fail():
        a = 3
        area = equilateral_area(a)
>       assert area == pytest.approx(9 * math.sqrt(3) / 4)
E       assert 9.433012701892219 == 3.8971143170299736 ± 3.9e-06
E         
E         comparison failed
E         Obtained: 9.433012701892219
E         Expected: 3.8971143170299736 ± 3.9e-06

tests/test_equilateral.py:11: AssertionError
______________________________________________________________________________________________________ test_ia_crash ______________________________________________________________________________________________________

    def test_ia_crash():
        leg, base = 9, 4
    
>       area = isosceles_area(leg, base)

tests/test_isosceles.py:11: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
code/isosceles.py:10: in isosceles_area
    area = 0.5 * base * height()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def height():
        t1, t2 = math.pow(base, 2), math.pow(leg, 2) / 4  # bug
        # t1, t2 = math.pow(leg, 2), math.pow(base, 2) / 4  # patch
>       return math.sqrt(t1 - t2)
E       ValueError: math domain error

code/isosceles.py:8: ValueError


***************************************************
                FauxPy Started!                    
***************************************************

FauxPy: ---> Running MBFL session
FauxPy: ---> Targeted failing tests:
FauxPy: --->   1. tests/test_equilateral.py::test_ea_fail


==============================
 Dynamic Analysis in Progress 
==============================

FauxPy: ---> Generating mutants using the mutation strategy Traditional for the following module:
FauxPy: --->   /Users/fazlisonerkiraz/fauxpy_example1/code/equilateral.py
FauxPy: ---> Number of generated mutants: 32
FauxPy: ---> Running 32 Mutants
FauxPy: ---> Running Mutant M0 (1/32)
FauxPy: ---> Running Mutant M1 (2/32)
FauxPy: ---> Running Mutant M2 (3/32)
FauxPy: ---> Running Mutant M3 (4/32)
FauxPy: ---> Running Mutant M4 (5/32)
FauxPy: ---> Running Mutant M5 (6/32)
FauxPy: ---> Running Mutant M6 (7/32)
FauxPy: ---> Running Mutant M7 (8/32)
FauxPy: ---> Running Mutant M8 (9/32)
FauxPy: ---> Running Mutant M9 (10/32)
FauxPy: ---> Running Mutant M10 (11/32)
FauxPy: ---> Running Mutant M11 (12/32)
FauxPy: ---> Running Mutant M12 (13/32)
FauxPy: ---> Running Mutant M13 (14/32)
FauxPy: ---> Running Mutant M14 (15/32)
FauxPy: ---> Running Mutant M15 (16/32)
FauxPy: ---> Running Mutant M16 (17/32)
FauxPy: ---> Running Mutant M17 (18/32)
FauxPy: ---> Running Mutant M18 (19/32)
FauxPy: ---> Running Mutant M19 (20/32)
FauxPy: ---> Running Mutant M20 (21/32)
FauxPy: ---> Running Mutant M21 (22/32)
FauxPy: ---> Running Mutant M22 (23/32)
FauxPy: ---> Running Mutant M23 (24/32)
FauxPy: ---> Running Mutant M24 (25/32)
FauxPy: ---> Running Mutant M25 (26/32)
FauxPy: ---> Running Mutant M26 (27/32)
FauxPy: ---> Running Mutant M27 (28/32)
FauxPy: ---> Running Mutant M28 (29/32)
FauxPy: ---> Running Mutant M29 (30/32)
FauxPy: ---> Running Mutant M30 (31/32)
FauxPy: ---> Running Mutant M31 (32/32)


--- Dynamic Analysis Complete ---

============================
 Fault Localization Results 
============================

=== Performance ===
Execution Time: 14.0966

-----------------------
|   Scores for Muse   |
-----------------------
File                | Line | Score  
------------------------------------
code/equilateral.py |   11 | +0.1818
code/equilateral.py |   10 | +0.0000
code/equilateral.py |    7 | -0.0793
code/equilateral.py |    5 | -0.1110
------------------------------------

-----------------------------
|   Scores for Metallaxis   |
-----------------------------
File                | Line | Score 
-----------------------------------
code/equilateral.py |   10 | 0.7071
code/equilateral.py |   11 | 0.7071
code/equilateral.py |    7 | 0.7071
code/equilateral.py |    5 | 0.5000
-----------------------------------

**************************************************
                FauxPy Ended!                     
**************************************************

================================================================================================= short test summary info =================================================================================================
FAILED tests/test_equilateral.py::test_ea_fail - assert 9.433012701892219 == 3.8971143170299736 ± 3.9e-06
FAILED tests/test_isosceles.py::test_ia_crash - ValueError: math domain error
============================================================================================== 2 failed, 2 passed in 14.09s ===============================================================================================
(env) Soners-MacBook-Pro:fauxpy_example1 fazlisonerkiraz$ 
```

## Function Level Granularity
- Pass the option `--granularity function`
    - which overrides the default `--granularity statement`

- Example command and the output
```bash
python -m pytest tests --src code --family sbfl --granularity function --failing-list "[tests/test_isosceles.py::test_ia_crash]"
```

```bash
=================================================================================================== test session starts ===================================================================================================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fazlisonerkiraz/fauxpy_example1
plugins: anyio-4.12.1, timeout-2.1.0, fauxpy-0.7.0
collected 4 items                                                                                                                                                                                                         

tests/test_equilateral.py F.                                                                                                                                                                                        [ 50%]
tests/test_isosceles.py F.                                                                                                                                                                                          [100%]

======================================================================================================== FAILURES =========================================================================================================
______________________________________________________________________________________________________ test_ea_fail _______________________________________________________________________________________________________

    def test_ea_fail():
        a = 3
        area = equilateral_area(a)
>       assert area == pytest.approx(9 * math.sqrt(3) / 4)
E       assert 9.433012701892219 == 3.8971143170299736 ± 3.9e-06
E         
E         comparison failed
E         Obtained: 9.433012701892219
E         Expected: 3.8971143170299736 ± 3.9e-06

tests/test_equilateral.py:11: AssertionError
______________________________________________________________________________________________________ test_ia_crash ______________________________________________________________________________________________________

    def test_ia_crash():
        leg, base = 9, 4
    
>       area = isosceles_area(leg, base)

tests/test_isosceles.py:11: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
code/isosceles.py:10: in isosceles_area
    area = 0.5 * base * height()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def height():
        t1, t2 = math.pow(base, 2), math.pow(leg, 2) / 4  # bug
        # t1, t2 = math.pow(leg, 2), math.pow(base, 2) / 4  # patch
>       return math.sqrt(t1 - t2)
E       ValueError: math domain error

code/isosceles.py:8: ValueError


***************************************************
                FauxPy Started!                    
***************************************************

FauxPy: ---> Running SBFL session
FauxPy: ---> Targeted failing tests:
FauxPy: --->   1. tests/test_isosceles.py::test_ia_crash


==============================
 Dynamic Analysis in Progress 
==============================



--- Dynamic Analysis Complete ---

============================
 Fault Localization Results 
============================

=== Performance ===
Execution Time: 0.0689

----------------------------
|   Scores for Tarantula   |
----------------------------
File                | Function         | Line | Score 
------------------------------------------------------
code/isosceles.py   | isosceles_area   | 4-11 | 0.7562
code/isosceles.py   | height           | 5-8  | 0.7562
code/equilateral.py | equilateral_area | 4-13 | 0.1000
------------------------------------------------------

-------------------------
|   Scores for Ochiai   |
-------------------------
File                | Function         | Line | Score 
------------------------------------------------------
code/isosceles.py   | isosceles_area   | 4-11 | 0.6604
code/isosceles.py   | height           | 5-8  | 0.6604
code/equilateral.py | equilateral_area | 4-13 | 0.0000
------------------------------------------------------

------------------------
|   Scores for Dstar   |
------------------------
File                | Function         | Line | Score 
------------------------------------------------------
code/isosceles.py   | isosceles_area   | 4-11 | 0.9091
code/isosceles.py   | height           | 5-8  | 0.9091
code/equilateral.py | equilateral_area | 4-13 | 0.0000
------------------------------------------------------

**************************************************
                FauxPy Ended!                     
**************************************************

================================================================================================= short test summary info =================================================================================================
FAILED tests/test_equilateral.py::test_ea_fail - assert 9.433012701892219 == 3.8971143170299736 ± 3.9e-06
FAILED tests/test_isosceles.py::test_ia_crash - ValueError: math domain error
=============================================================================================== 2 failed, 2 passed in 0.06s ===============================================================================================

```