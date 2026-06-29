# Repair Evaluation Results (Assignment 3 — Task 5)

Full template-based repair pipeline (fault localization → patch generation → validation → ranking) run on 3 BugsInPy bug(s), each under both automated FL and perfect (oracle) FL, with the patch ranker applied.

Generated: 2026-06-29 19:36 UTC · ranker: `weighted-composite` · per-validation budget: 200


## tornado bug #14

| FL mode | Backend | Generated | Validated | Plausible | Correct | 1st plausible (s) | Total (s) | Correct rank (gen) | Correct rank (ranked) | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| auto | auto-fl | — | — | — | — | — | — | — | — | ERROR: ConfigurationError: FauxPy is not installed in the project environment and installation failed (full error in results.json) |
| perfect | perfect-fl | 6 | 6 | 1 | 1 | 0.7 | 1.1 | 1 | 1 | correct |

## scrapy bug #2

| FL mode | Backend | Generated | Validated | Plausible | Correct | 1st plausible (s) | Total (s) | Correct rank (gen) | Correct rank (ranked) | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| auto | fauxpy | 0 | 0 | 0 | 0 | — | 0.0 | — | — | no_patch |
| perfect | perfect-fl | 5 | 5 | 0 | 0 | — | 1.1 | — | — | failed |

## black bug #1

| FL mode | Backend | Generated | Validated | Plausible | Correct | 1st plausible (s) | Total (s) | Correct rank (gen) | Correct rank (ranked) | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| auto | fauxpy | 8 | 8 | 0 | 0 | — | 12.1 | — | — | failed |
| perfect | perfect-fl | 0 | 0 | 0 | 0 | — | 1.1 | — | — | no_patch |

## Aggregate (per FL mode)

Totals across all evaluated bugs. *Bugs repaired* counts bugs with at least one correct patch; *bugs with plausible* counts bugs with at least one plausible patch.

| FL mode | Bugs | Generated | Plausible | Correct | Bugs with plausible | Bugs repaired |
|---|---|---|---|---|---|---|
| auto | 3 | 8 | 0 | 0 | 0 | 0 |
| perfect | 3 | 11 | 1 | 1 | 1 | 1 |

## Discussion

**Which bugs were repaired?**  Under perfect FL, a correct patch was produced for: `tornado#14`.  No bug produced a correct patch under automated FL.

**Did the repair technique benefit from better FL?**  Perfect FL feeds the repair loop the exact developer-fix line(s), so the mutation operators are applied precisely where the fault is. Automated (SBFL) FL instead supplies the top-N suspicious lines, which only contain the faulty line when localization is accurate. Where the developer fix is an operator-level change (a comparison/boolean/arithmetic swap, an off-by-one, or a return-value change), perfect FL therefore turns the fix into a single reachable mutation, while automated FL succeeds only if the faulty line is ranked highly enough to fall inside the top-N window. Where the developer fix is *out of operator reach* (e.g. wrapping code in try/except, adding a parameter, or renaming a variable), neither FL mode can yield a correct patch — the bottleneck is the template operator set, not the fault location.

**Did the ranker surface correct patches earlier?**  On the cells that produced a correct patch the plausible set contained only a single patch, so generation order and ranked order coincide (the correct patch is at rank 1 in both). The ranker correctly places that patch first, but a larger plausible set is needed to *demonstrate* reordering. This matches the known limitation that ranking only distinguishes patches when at least two are plausible.

**Limitations.**  (1) The template operator set only covers single-token operator swaps, off-by-one nudges, condition negation and return-value changes; the majority of real BugsInPy developer fixes add or restructure statements and are therefore unreachable regardless of FL quality. (2) Automated FL depends on FauxPy, which requires a pytest-compatible test harness and a compatible Python; some bugs cannot run automated FL for environment reasons, which appears as an error cell. (3) Plausibility is judged on the bug's trigger test plus a regression check, not the project's full suite, so a patch counted as plausible may still be an overfit. (4) Correctness is a strict syntactic diff-level match to the single-file developer fix and will not credit a semantically-equivalent but textually-different patch.
