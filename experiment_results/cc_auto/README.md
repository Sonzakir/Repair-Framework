# Course-Wide Comparison: All Repair Approaches

Every approach built over the course, run on 2 BugsInPy bug(s): traditional template repair, single-shot LLM repair, iterative LLM repair, and the fully LLM-driven pipeline (LLM-FL -> LLM repair with context retrieval -> LLM assessment).

Generated: 2026-07-13 21:33 UTC · model: `gpt-5.4` · per-cell validation budget: 200


**On the metrics.**  **`Exact diff`** counts patches whose diff matches the developer fix byte-for-byte. It is deliberately *not* called *correct*: a semantically correct fix written differently from the developer's scores 0 here, so a 0 in this column is not a claim that the patch is wrong. It is the framework's data-contamination signal, and nothing more. Two graded metrics carry the actual quality judgment, and every cell of every column is measured with both:

- **Assessment quality score** (`0.0`-`1.0`) — the LLM assessor's judgment of whether the patch genuinely fixes the bug or just overfits the test suite. This is the semantic signal the pass/fail oracle cannot give.
- **Context similarity score** (`0.0`-`1.0`) — how close the patch's edit is to the developer's, including the surrounding context lines. `1.00` is a byte-exact match; a high-but-sub-1.0 score is a near-miss that `Exact diff` reports as a flat 0. It is scored on **every candidate an approach generated, plausible or not**, so an approach whose patches all failed the test suite still reports how close it came — otherwise its column would be empty and it could not be compared at all.


## Course-wide comparison (per bug)

### black bug #1

| | A3 (template) | A4 simple | A4 iterative | A5 full LLM |
|---|---|---|---|---|
| FL source | auto/perfect | auto/perfect | auto/perfect | LLM-FL |
| Repair | traditional | LLM | LLM (iterative) | LLM + retrieval |
| Assessment | test pass/fail | test pass/fail | test pass/fail | LLM assessor |
| Plausible patches | 0 (auto) | 0 (auto) | 0 (auto) | 9 |
| Exact-diff matches (not a correctness verdict) | 0 (auto) | 0 (auto) | 0 (auto) | 0 |
| **Best assessment quality score** | — | — | — | 0.88 |
| **Best context similarity score** (any candidate) | 0.13 | 0.18 | 0.18 | 0.38 |
| Time to first plausible | — | — | — | 39.3s |

_Columns whose FL source is auto/perfect were run under every FL mode available for this bug — `auto` is skipped entirely on bugs FauxPy cannot localize, rather than recorded as a zero. The cell shown is the best of those runs, chosen by max exact-diff matches → max plausible → fastest time to first plausible, with the winning FL mode in parentheses. `—` means the approach produced nothing, the cell errored, or its localizer ranked nothing at all (`no_fl_locations`); the per-cell tables below say which._

### black bug #3

| | A3 (template) | A4 simple | A4 iterative | A5 full LLM |
|---|---|---|---|---|
| FL source | auto/perfect | auto/perfect | auto/perfect | LLM-FL |
| Repair | traditional | LLM | LLM (iterative) | LLM + retrieval |
| Assessment | test pass/fail | test pass/fail | test pass/fail | LLM assessor |
| Plausible patches | 0 (auto) | 0 (auto) | 0 (auto) | 3 |
| Exact-diff matches (not a correctness verdict) | 0 (auto) | 0 (auto) | 0 (auto) | 0 |
| **Best assessment quality score** | — | — | — | 0.20 |
| **Best context similarity score** (any candidate) | 0.03 | 0.03 | 0.05 | 0.06 |
| Time to first plausible | — | — | — | 29.2s |

_Columns whose FL source is auto/perfect were run under every FL mode available for this bug — `auto` is skipped entirely on bugs FauxPy cannot localize, rather than recorded as a zero. The cell shown is the best of those runs, chosen by max exact-diff matches → max plausible → fastest time to first plausible, with the winning FL mode in parentheses. `—` means the approach produced nothing, the cell errored, or its localizer ranked nothing at all (`no_fl_locations`); the per-cell tables below say which._


## Every cell (per bug × approach × FL mode)

### black bug #1

| Approach | FL mode | Queries | Generated | Plausible | Exact diff | Best quality | Best similarity (any cand.) | Retrieval steps | 1st plausible (s) | Total (s) | Outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a3-template | auto | — | 4 | 0 | 0 | — | 0.13 | 0 | — | 10.1 | failed |
| a3-template | perfect | — | 0 | 0 | 0 | — | — | 0 | — | 1.2 | no_patch |
| a4-single-shot | auto | 9 | 9 | 0 | 0 | — | 0.18 | 0 | — | 25.4 | failed |
| a4-single-shot | perfect | 9 | 9 | 0 | 0 | — | 0.45 | 0 | — | 30.1 | failed |
| a4-iterative | auto | 15 | 15 | 0 | 0 | — | 0.18 | 0 | — | 39.3 | failed |
| a4-iterative | perfect | 15 | 15 | 0 | 0 | — | 0.45 | 0 | — | 48.7 | failed |
| a5-full-llm | llm-fl | 12 | 9 | 9 | 0 | 0.88 | 0.38 | 0 | 39.3 | 104.9 | plausible |

### black bug #3

| Approach | FL mode | Queries | Generated | Plausible | Exact diff | Best quality | Best similarity (any cand.) | Retrieval steps | 1st plausible (s) | Total (s) | Outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a3-template | auto | — | 1 | 0 | 0 | — | 0.03 | 0 | — | 7.4 | failed |
| a3-template | perfect | — | 10 | 0 | 0 | — | 0.21 | 0 | — | 23.5 | failed |
| a4-single-shot | auto | 9 | 9 | 0 | 0 | — | 0.03 | 0 | — | 22.1 | failed |
| a4-single-shot | perfect | 3 | 0 | 0 | 0 | — | — | 0 | — | 26.7 | no_patch |
| a4-iterative | auto | 15 | 15 | 0 | 0 | — | 0.05 | 0 | — | 34.4 | failed |
| a4-iterative | perfect | 2 | 0 | 0 | 0 | — | — | 0 | — | 13.3 | no_patch |
| a5-full-llm | llm-fl | 12 | 9 | 3 | 0 | 0.20 | 0.06 | 0 | 29.2 | 49.0 | plausible |


## Analysis

**Which cells actually had a fault location to repair?**  Every cell that was run did. No cell errored and no localizer came back empty, so each column's numbers reflect the *repair* approach rather than a missing or broken localizer.

**Did LLM-FL outperform SBFL/MBFL?**  Comparing the LLM-FL cell against the automated-FL (FauxPy) cells for the same bug:

- `black#1`: LLM-FL reached **9 plausible** patch(es) vs 0 under automated FL.
- `black#3`: LLM-FL reached **3 plausible** patch(es) vs 0 under automated FL.
  - Caveat for `black#3`: the only source shown to the localizer was test code (['tests/test_black.py']), so its ranking could not point at project source — symbol anchoring found no target.

**Did context retrieval help?**  The model requested **no** retrieval steps in any cell. With a non-zero budget available, declining to retrieve is itself a signal: the fault regions in this bug set were self-contained enough that the model judged the prompt sufficient.

**Was patch assessment useful?**  The assessor scored 12 plausible patch(es) across 2 cell(s).

No cell produced an exact-diff match, so the assessor's ability to rank one first could not be tested directly on this bug set.

The assessor flagged likely **test-suite overfitting** — patches that pass every test yet score below 0.5 on semantic quality — in: `black#3` (a5-full-llm, best quality 0.20). The pass/fail oracle rates these identically to a genuine fix; the assessor does not.

**Where did the full LLM pipeline improve, and where did it regress?**  It improved on the best prior approach for: `black#1` (plausible 0 → 9); `black#3` (plausible 0 → 3). 
