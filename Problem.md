- I am currently following problem, i will descirbe you my problem and then you are going to inspect my code and the original bugsInPy project (whuch is under ./tools/bugsinpy) and then you are going to tell me where exactly i am making a problem, and how can i fix this problem:
- Firstly the in original BugsInPy they are using Python 3.12 in the docker, and when i build / and run the container with the following command 
```bash
bugsinpy-checkout -p youtube-dl -v 0 -i 2 -w /home/workspace
root@c7930f83768d:/home/workspace/youtube-dl# bugsinpy-compile
root@c7930f83768d:/home/workspace/youtube-dl# bugsinpy-test
```
- It successfully gives the following output 
```bash
python -m unittest -q test.test_InfoExtractor.TestInfoExtractor.test_parse_mpd_formats
RUN EVERY COMMAND
0


/home/workspace/youtube-dl/youtube_dl/extractor/pandatv.py:39: SyntaxWarning: "is not" with 'int' literal. Did you mean "!="?
  if error_code is not 0:
======================================================================
FAIL: test_parse_mpd_formats (test.test_InfoExtractor.TestInfoExtractor.test_parse_mpd_formats)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/workspace/youtube-dl/test/test_InfoExtractor.py", line 668, in test_parse_mpd_formats
    expect_value(self, formats, expected_formats, None)
  File "/home/workspace/youtube-dl/test/helper.py", line 137, in expect_value
    self.assertEqual(
AssertionError: 7 != 6 : Expect a list of length 7, but got a list of length 6 for field None

----------------------------------------------------------------------
Ran 1 test in 0.025s

FAILED (failures=1)
```

- In my current projet i wanted to develop a wrapper around the BugsInPy
- My environment has python 3.12 and my docker uses python 3.12 as in the original BugsInPy project.
    - However when i try to run the same command in my project i get following failure:
```bash
(.venv) soner@SonerXPS:~/repair-framework-Sonzakir$ python -m apr_framework bugsinpy test youtube.dl 2
this is the command ==> ['/usr/bin/bash', '/home/soner/repair-framework-Sonzakir/.tools/bugsinpy/framework/bin/bugsinpy-checkout', '-p', 'youtube.dl', '-i', '2', '-v', '0', '-w', '/home/soner/repair-framework-Sonzakir/.workspace/bugsinpy/youtube.dl_2']
PROJECT_NAME: youtube.dl
BUG_ID: 2
VERSION_ID: 0
WORK_DIR: /home/soner/repair-framework-Sonzakir/.workspace/bugsinpy/youtube.dl_2
Project youtube.dl does not exist, please check the project name
We have reached here
this is the command ==> ['/usr/bin/bash', '/home/soner/repair-framework-Sonzakir/.tools/bugsinpy/framework/bin/bugsinpy-compile', '-w', '/home/soner/repair-framework-Sonzakir/.workspace/bugsinpy/youtube.dl_2/youtube.dl']
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/soner/repair-framework-Sonzakir/src/apr_framework/__main__.py", line 9, in <module>
    raise SystemExit(main())
                     ^^^^^^
  File "/home/soner/repair-framework-Sonzakir/src/apr_framework/cli/app.py", line 14, in main
    return _run()
           ^^^^^^
  File "/home/soner/repair-framework-Sonzakir/src/apr_framework/cli/app.py", line 80, in _run
    adapter.prepare_environment(checkout)
  File "/home/soner/repair-framework-Sonzakir/src/apr_framework/benchmarks/bugsinpy.py", line 244, in prepare_environment
    self._toolchain.run_bugsinpy(
  File "/home/soner/repair-framework-Sonzakir/src/apr_framework/benchmarks/bugsinpy.py", line 141, in run_bugsinpy
    return subprocess.run(
           ^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/subprocess.py", line 548, in run
    with Popen(*popenargs, **kwargs) as process:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/subprocess.py", line 1026, in __init__
    self._execute_child(args, executable, preexec_fn, close_fds,
  File "/usr/lib/python3.12/subprocess.py", line 1955, in _execute_child
    raise child_exception_type(errno_num, err_msg, err_filename)
FileNotFoundError: [Errno 2] No such file or directory: PosixPath('/home/soner/repair-framework-Sonzakir/.workspace/bugsinpy/youtube.dl_2/youtube.dl')
```