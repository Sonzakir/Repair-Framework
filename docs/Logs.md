- LLMRepair-1.1.md
    - Patch Generation
    - Problem: Correct Patches are found but not written in the Terminal 
    - See the run_148 diffs to see plausible patches 



---
# Command to record the terminal


Use this workflow:

```bash
script -q -a terminal.raw
```

Then after `exit`:

```bash
perl -pe 's/\e\[[0-?]*[ -\/]*[@-~]//g; s/\e\][^\a]*(\a|\e\\)//g; s/\r//g; s/\a//g' terminal.raw | col -b > terminal-log.md
```

The file type can stay `.md`; the issue is the raw terminal escape codes.

-- 