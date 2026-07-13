# Course-Wide Comparison: All Repair Approaches

Every approach built over the course, run on 6 BugsInPy bug(s): traditional template repair, single-shot LLM repair, iterative LLM repair, and the fully LLM-driven pipeline (LLM-FL -> LLM repair with context retrieval -> LLM assessment).

Generated: 2026-07-13 21:08 UTC · model: `gpt-5.4` · per-cell validation budget: 200


**On the metrics.**  **`Exact diff`** counts patches whose diff matches the developer fix byte-for-byte. It is deliberately *not* called *correct*: a semantically correct fix written differently from the developer's scores 0 here, so a 0 in this column is not a claim that the patch is wrong. It is the framework's data-contamination signal, and nothing more. Two graded metrics carry the actual quality judgment, and every cell of every column is measured with both:

- **Assessment quality score** (`0.0`-`1.0`) — the LLM assessor's judgment of whether the patch genuinely fixes the bug or just overfits the test suite. This is the semantic signal the pass/fail oracle cannot give.
- **Context similarity score** (`0.0`-`1.0`) — how close the patch's edit is to the developer's, including the surrounding context lines. `1.00` is a byte-exact match; a high-but-sub-1.0 score is a near-miss that `Exact diff` reports as a flat 0.


## Course-wide comparison (per bug)

### black bug #1

| | A3 (template) | A4 simple | A4 iterative | A5 full LLM |
|---|---|---|---|---|
| FL source | auto/perfect | auto/perfect | auto/perfect | LLM-FL |
| Repair | traditional | LLM | LLM (iterative) | LLM + retrieval |
| Assessment | test pass/fail | test pass/fail | test pass/fail | LLM assessor |
| Plausible patches | 0 (auto) | 0 (auto) | 0 (auto) | 6 |
| Exact-diff matches (not a correctness verdict) | 0 (auto) | 0 (auto) | 0 (auto) | 0 |
| **Best assessment quality score** | — | — | — | 0.93 |
| **Best context similarity score** | — | — | — | 0.39 |
| Time to first plausible | — | — | — | 41.1s |

_Columns whose FL source is auto/perfect were run under every FL mode available for this bug — `auto` is skipped entirely on bugs FauxPy cannot localize, rather than recorded as a zero. The cell shown is the best of those runs, chosen by max exact-diff matches → max plausible → fastest time to first plausible, with the winning FL mode in parentheses. `—` means the approach produced nothing, the cell errored, or its localizer ranked nothing at all (`no_fl_locations`); the per-cell tables below say which._

### black bug #3

| | A3 (template) | A4 simple | A4 iterative | A5 full LLM |
|---|---|---|---|---|
| FL source | auto/perfect | auto/perfect | auto/perfect | LLM-FL |
| Repair | traditional | LLM | LLM (iterative) | LLM + retrieval |
| Assessment | test pass/fail | test pass/fail | test pass/fail | LLM assessor |
| Plausible patches | 0 (auto) | 0 (auto) | 0 (auto) | 4 |
| Exact-diff matches (not a correctness verdict) | 0 (auto) | 0 (auto) | 0 (auto) | 0 |
| **Best assessment quality score** | — | — | — | 0.12 |
| **Best context similarity score** | — | — | — | 0.06 |
| Time to first plausible | — | — | — | 31.0s |

_Columns whose FL source is auto/perfect were run under every FL mode available for this bug — `auto` is skipped entirely on bugs FauxPy cannot localize, rather than recorded as a zero. The cell shown is the best of those runs, chosen by max exact-diff matches → max plausible → fastest time to first plausible, with the winning FL mode in parentheses. `—` means the approach produced nothing, the cell errored, or its localizer ranked nothing at all (`no_fl_locations`); the per-cell tables below say which._

### black bug #7

| | A3 (template) | A4 simple | A4 iterative | A5 full LLM |
|---|---|---|---|---|
| FL source | auto/perfect | auto/perfect | auto/perfect | LLM-FL |
| Repair | traditional | LLM | LLM (iterative) | LLM + retrieval |
| Assessment | test pass/fail | test pass/fail | test pass/fail | LLM assessor |
| Plausible patches | 0 (auto) | 0 (auto) | 0 (auto) | 0 |
| Exact-diff matches (not a correctness verdict) | 0 (auto) | 0 (auto) | 0 (auto) | 0 |
| **Best assessment quality score** | — | — | — | — |
| **Best context similarity score** | — | — | — | — |
| Time to first plausible | — | — | — | — |

_Columns whose FL source is auto/perfect were run under every FL mode available for this bug — `auto` is skipped entirely on bugs FauxPy cannot localize, rather than recorded as a zero. The cell shown is the best of those runs, chosen by max exact-diff matches → max plausible → fastest time to first plausible, with the winning FL mode in parentheses. `—` means the approach produced nothing, the cell errored, or its localizer ranked nothing at all (`no_fl_locations`); the per-cell tables below say which._

### black bug #11

| | A3 (template) | A4 simple | A4 iterative | A5 full LLM |
|---|---|---|---|---|
| FL source | auto/perfect | auto/perfect | auto/perfect | LLM-FL |
| Repair | traditional | LLM | LLM (iterative) | LLM + retrieval |
| Assessment | test pass/fail | test pass/fail | test pass/fail | LLM assessor |
| Plausible patches | 0 (auto) | 0 (auto) | 0 (auto) | 0 |
| Exact-diff matches (not a correctness verdict) | 0 (auto) | 0 (auto) | 0 (auto) | 0 |
| **Best assessment quality score** | — | — | — | — |
| **Best context similarity score** | — | — | — | — |
| Time to first plausible | — | — | — | — |

_Columns whose FL source is auto/perfect were run under every FL mode available for this bug — `auto` is skipped entirely on bugs FauxPy cannot localize, rather than recorded as a zero. The cell shown is the best of those runs, chosen by max exact-diff matches → max plausible → fastest time to first plausible, with the winning FL mode in parentheses. `—` means the approach produced nothing, the cell errored, or its localizer ranked nothing at all (`no_fl_locations`); the per-cell tables below say which._

### tornado bug #14

| | A3 (template) | A4 simple | A4 iterative | A5 full LLM |
|---|---|---|---|---|
| FL source | perfect only (auto: FauxPy cannot localize) | perfect only (auto: FauxPy cannot localize) | perfect only (auto: FauxPy cannot localize) | LLM-FL |
| Repair | traditional | LLM | LLM (iterative) | LLM + retrieval |
| Assessment | test pass/fail | test pass/fail | test pass/fail | LLM assessor |
| Plausible patches | 1 (perfect) | 3 (perfect) | 1 (perfect) | 9 |
| Exact-diff matches (not a correctness verdict) | 1 (perfect) | 3 (perfect) | 1 (perfect) | 9 |
| **Best assessment quality score** | 0.18 | 0.99 | 0.99 | 1.00 |
| **Best context similarity score** | 1.00 | 1.00 | 1.00 | 1.00 |
| Time to first plausible | 0.7s | 5.9s | 1.8s | 14.5s |

_Columns whose FL source is auto/perfect were run under every FL mode available for this bug — `auto` is skipped entirely on bugs FauxPy cannot localize, rather than recorded as a zero. The cell shown is the best of those runs, chosen by max exact-diff matches → max plausible → fastest time to first plausible, with the winning FL mode in parentheses. `—` means the approach produced nothing, the cell errored, or its localizer ranked nothing at all (`no_fl_locations`); the per-cell tables below say which._

### scrapy bug #2

| | A3 (template) | A4 simple | A4 iterative | A5 full LLM |
|---|---|---|---|---|
| FL source | perfect only (auto: FauxPy cannot localize) | perfect only (auto: FauxPy cannot localize) | perfect only (auto: FauxPy cannot localize) | LLM-FL |
| Repair | traditional | LLM | LLM (iterative) | LLM + retrieval |
| Assessment | test pass/fail | test pass/fail | test pass/fail | LLM assessor |
| Plausible patches | 0 (perfect) | 1 (perfect) | 2 (perfect) | 9 |
| Exact-diff matches (not a correctness verdict) | 0 (perfect) | 0 (perfect) | 0 (perfect) | 0 |
| **Best assessment quality score** | — | 0.98 | 0.98 | 0.98 |
| **Best context similarity score** | — | 0.92 | 0.92 | 0.92 |
| Time to first plausible | — | 7.6s | 3.1s | 14.7s |

_Columns whose FL source is auto/perfect were run under every FL mode available for this bug — `auto` is skipped entirely on bugs FauxPy cannot localize, rather than recorded as a zero. The cell shown is the best of those runs, chosen by max exact-diff matches → max plausible → fastest time to first plausible, with the winning FL mode in parentheses. `—` means the approach produced nothing, the cell errored, or its localizer ranked nothing at all (`no_fl_locations`); the per-cell tables below say which._


## Every cell (per bug × approach × FL mode)

### black bug #1

| Approach | FL mode | Queries | Generated | Plausible | Exact diff | Best quality | Best similarity | Retrieval steps | 1st plausible (s) | Total (s) | Outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a3-template | auto | — | 4 | 0 | 0 | — | — | 0 | — | 10.3 | failed |
| a3-template | perfect | — | 0 | 0 | 0 | — | — | 0 | — | 1.2 | no_patch |
| a4-single-shot | auto | 9 | 9 | 0 | 0 | — | — | 0 | — | 27.4 | failed |
| a4-single-shot | perfect | 9 | 9 | 0 | 0 | — | — | 0 | — | 31.1 | failed |
| a4-iterative | auto | 15 | 15 | 0 | 0 | — | — | 0 | — | 37.0 | failed |
| a4-iterative | perfect | 15 | 15 | 0 | 0 | — | — | 0 | — | 50.3 | failed |
| a5-full-llm | llm-fl | 13 | 7 | 6 | 0 | 0.93 | 0.39 | 1 | 41.1 | 80.9 | plausible |

### black bug #3

| Approach | FL mode | Queries | Generated | Plausible | Exact diff | Best quality | Best similarity | Retrieval steps | 1st plausible (s) | Total (s) | Outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a3-template | auto | — | 1 | 0 | 0 | — | — | 0 | — | 7.3 | failed |
| a3-template | perfect | — | 10 | 0 | 0 | — | — | 0 | — | 23.2 | failed |
| a4-single-shot | auto | 9 | 9 | 0 | 0 | — | — | 0 | — | 22.4 | failed |
| a4-single-shot | perfect | 3 | 0 | 0 | 0 | — | — | 0 | — | 25.2 | no_patch |
| a4-iterative | auto | 15 | 15 | 0 | 0 | — | — | 0 | — | 39.7 | failed |
| a4-iterative | perfect | 2 | 0 | 0 | 0 | — | — | 0 | — | 11.2 | no_patch |
| a5-full-llm | llm-fl | 12 | 9 | 4 | 0 | 0.12 | 0.06 | 0 | 31.0 | 68.9 | plausible |

### black bug #7

| Approach | FL mode | Queries | Generated | Plausible | Exact diff | Best quality | Best similarity | Retrieval steps | 1st plausible (s) | Total (s) | Outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a3-template | auto | — | 4 | 0 | 0 | — | — | 0 | — | 2.0 | failed |
| a3-template | perfect | — | 5 | 0 | 0 | — | — | 0 | — | 2.0 | failed |
| a4-single-shot | auto | 9 | 6 | 0 | 0 | — | — | 0 | — | 24.5 | failed |
| a4-single-shot | perfect | 6 | 6 | 0 | 0 | — | — | 0 | — | 23.1 | failed |
| a4-iterative | auto | 12 | 10 | 0 | 0 | — | — | 0 | — | 34.2 | failed |
| a4-iterative | perfect | 8 | 6 | 0 | 0 | — | — | 0 | — | 27.9 | failed |
| a5-full-llm | llm-fl | 8 | 6 | 0 | 0 | — | — | 0 | — | 29.7 | failed |

### black bug #11

| Approach | FL mode | Queries | Generated | Plausible | Exact diff | Best quality | Best similarity | Retrieval steps | 1st plausible (s) | Total (s) | Outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a3-template | auto | — | 6 | 0 | 0 | — | — | 0 | — | 2.4 | failed |
| a3-template | perfect | — | 4 | 0 | 0 | — | — | 0 | — | 1.9 | failed |
| a4-single-shot | auto | 9 | 9 | 0 | 0 | — | — | 0 | — | 19.0 | failed |
| a4-single-shot | perfect | 9 | 9 | 0 | 0 | — | — | 0 | — | 30.2 | failed |
| a4-iterative | auto | 15 | 15 | 0 | 0 | — | — | 0 | — | 28.4 | failed |
| a4-iterative | perfect | 15 | 15 | 0 | 0 | — | — | 0 | — | 51.0 | failed |
| a5-full-llm | llm-fl | 12 | 9 | 0 | 0 | — | — | 0 | — | 37.5 | failed |

### tornado bug #14

| Approach | FL mode | Queries | Generated | Plausible | Exact diff | Best quality | Best similarity | Retrieval steps | 1st plausible (s) | Total (s) | Outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a3-template | perfect | — | 6 | 1 | 1 | 0.18 | 1.00 | 0 | 0.7 | 1.2 | correct |
| a4-single-shot | perfect | 3 | 3 | 3 | 3 | 0.99 | 1.00 | 0 | 5.9 | 6.5 | correct |
| a4-iterative | perfect | 1 | 1 | 1 | 1 | 0.99 | 1.00 | 0 | 1.8 | 1.8 | correct |
| a5-full-llm | llm-fl | 12 | 9 | 9 | 9 | 1.00 | 1.00 | 0 | 14.5 | 17.2 | correct |

### scrapy bug #2

| Approach | FL mode | Queries | Generated | Plausible | Exact diff | Best quality | Best similarity | Retrieval steps | 1st plausible (s) | Total (s) | Outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a3-template | perfect | — | 5 | 0 | 0 | — | — | 0 | — | 1.2 | failed |
| a4-single-shot | perfect | 6 | 6 | 1 | 0 | 0.98 | 0.92 | 0 | 7.6 | 8.0 | plausible |
| a4-iterative | perfect | 3 | 3 | 2 | 0 | 0.98 | 0.92 | 0 | 3.1 | 4.8 | plausible |
| a5-full-llm | llm-fl | 12 | 9 | 9 | 0 | 0.98 | 0.92 | 0 | 14.7 | 17.7 | plausible |


## Analysis

**Which cells actually had a fault location to repair?**  Every cell that was run did. No cell errored and no localizer came back empty, so each column's numbers reflect the *repair* approach rather than a missing or broken localizer. Automated FL was **not run at all** on `tornado#14`, `scrapy#2`: FauxPy 0.7.0 cannot localize those bugs (Python 3.7 pins it cannot install on, or a dependency conflict with the project's own pins). Those bugs are reported under perfect FL and LLM-FL only — an approach that cannot run is left out, not scored as a zero.

**Did LLM-FL outperform SBFL/MBFL?**  Comparing the LLM-FL cell against the automated-FL (FauxPy) cells for the same bug:

- `black#1`: LLM-FL reached **6 plausible** patch(es) vs 0 under automated FL.
- `black#3`: LLM-FL reached **4 plausible** patch(es) vs 0 under automated FL.
  - Caveat for `black#3`: the only source shown to the localizer was test code (['tests/test_black.py']), so its ranking could not point at project source — symbol anchoring found no target.
- `black#7`: LLM-FL and automated FL reached the same outcome (0 plausible).
- `black#11`: LLM-FL and automated FL reached the same outcome (0 plausible).
- `tornado#14`: automated (FauxPy) FL **was not run** — this bug is outside FauxPy 0.7.0's reach (see the bug-set note in the repository README), so there is no SBFL/MBFL baseline to compare against. LLM-FL localized it and reached 9 plausible / 9 exact-diff match(es); that the LLM localizer runs at all here is itself the difference.
- `scrapy#2`: automated (FauxPy) FL **was not run** — this bug is outside FauxPy 0.7.0's reach (see the bug-set note in the repository README), so there is no SBFL/MBFL baseline to compare against. LLM-FL localized it and reached 9 plausible / 0 exact-diff match(es); that the LLM localizer runs at all here is itself the difference.

**Did context retrieval help?**  The model spent **1 retrieval step(s)** across 1 cell(s) (`get_function_definition` ×1), which produced 6 plausible patch(es) and 0 exact-diff match(es). Retrieval pays off only when the fault region depends on code the model cannot already see; for self-contained regions it correctly declines to retrieve and patches directly.

- `black#1` (a5-full-llm): 1 retrieval step(s) across 1 prompt(s) — `get_function_definition` ×1; 6 plausible, 0 exact-diff.

**Was patch assessment useful?**  The assessor scored 36 plausible patch(es) across 9 cell(s).

In 4 of 4 cell(s) that contained an exact-diff match, the assessor ranked that patch **first**. That is weak evidence, though: 2 of those cell(s) held only a single plausible patch, so ranking it first was unavoidable rather than a judgment.

**The assessor is not itself an oracle.** It scored *below 0.5* a patch that exactly reproduces the developer fix in: `tornado#14` (a3-template, quality 0.18). A low quality score is therefore evidence, not a verdict: the model judges a fix on how the edit reads in isolation, and a terse single-operator change (the kind template repair emits) can look unconvincing to it even when it is precisely what the developer wrote. This is the honest limit of LLM-based assessment, and the reason the exact-diff verdict is retained rather than replaced.

The assessor flagged likely **test-suite overfitting** — patches that pass every test yet score below 0.5 on semantic quality — in: `black#3` (a5-full-llm, best quality 0.12). The pass/fail oracle rates these identically to a genuine fix; the assessor does not.

The similarity score also caught **near-misses the strict verdict hides**: `scrapy#2` (a4-single-shot, similarity 0.92), `scrapy#2` (a4-iterative, similarity 0.92), `scrapy#2` (a5-full-llm, similarity 0.92) scored ≥0.85 against the developer fix while still counting as 0 exact-diff matches — the fix landed in the right place, in nearly the right form.

**Where did the full LLM pipeline improve, and where did it regress?**  It improved on the best prior approach for: `black#1` (plausible 0 → 6); `black#3` (plausible 0 → 4); `tornado#14` (exact-diff 3 → 9); `scrapy#2` (plausible 2 → 9). 
