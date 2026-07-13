# The second correctness metric: context similarity score

This note explains, intuitively, the second correctness metric added alongside the
existing exact-diff check in
[`repair/correctness.py`](../src/apr_framework/repair/correctness.py). The existing
check (`is_correct_patch`, `RepairStatus.CORRECT`, `correct_count`) is **unchanged**
— this is a purely additive metric that runs alongside it.

## The problem with a yes/no answer

The original correctness check answers one question: *does the candidate patch
reproduce the developer's fix exactly*, ignoring only cosmetic reformatting? The
answer is a boolean — `True` or `False`.

That's a fair check, but it throws away information. Imagine three LLM-generated
patches for the same bug:

1. One that reproduces the developer's fix character-for-character.
2. One that makes the *same* fix but happens to rename a local variable along the
   way.
3. One that fixes the bug in a *completely different* way (different approach,
   different lines touched).

The exact-diff check calls (1) `True` and calls **both (2) and (3) `False`** — it
can't tell "almost the developer's fix" apart from "nothing like the developer's
fix." For understanding *how* an LLM is behaving (is it reasoning its way to a
similar fix, or missing the mark entirely, or suspiciously reciting the fix
verbatim), that distinction matters.

## The idea: measure closeness, not just equality

`context_similarity_score(candidate, reference_diff_text)` returns a number between
`0.0` and `1.0` instead of a boolean:

- **`1.0`** — the candidate's edit is identical to the developer's, in the same
  spot in the file. This is a guarantee, not just a typical outcome: whenever the
  exact-diff check (`is_correct_patch`) already agrees the candidate is an exact
  match, `context_similarity_score` short-circuits to `1.0` rather than trusting
  the hunk-level text comparison. Without that short-circuit, a byte-identical
  reproduction of the developer's fix could score a point or two short of `1.0`
  (observed: `0.94`), because the `ast.unparse` round-trip that cancels cosmetic
  differences on the *changed* lines can also reflow blank-line spacing elsewhere
  in the file, which shifts which *unchanged* lines land inside the fixed-size
  context window the similarity comparison looks at.
- **High, but below `1.0`** — the candidate landed in the right place and made
  essentially the same change, just worded slightly differently.
- **Low** — the candidate's edit has little in common with the developer's fix,
  beyond perhaps sharing some of the same file.

## Why "context" is in the name

A unified diff normally looks like this:

```diff
@@ -10,5 +10,5 @@
 def is_ready(self, count):
     total = count + self.pending
-    if total > self.limit:
+    if total >= self.limit:
         return False
     return True
```

The lines starting with a space (` `) are **context lines** — unchanged code shown
around the edit so a human reader can see where the change sits. The original exact
check throws these away entirely: it only ever looks at the `+`/`-` lines, pooled
together per file.

The new metric keeps the context lines. It treats each edit as a **hunk** — the
`+`/`-` lines *together with* the unchanged lines immediately around them — and
compares the candidate's hunk against the developer's hunk as a whole block of
text. Keeping the context is what lets the score notice "this is basically the same
edit, just a variable got renamed nearby" instead of only being able to say
"the changed line isn't identical."

## How the comparison actually works

0. **Ask the exact check first.** If `is_correct_patch` already says the candidate
   is an exact match, the score is `1.0` immediately — no hunk comparison needed.
   This step exists because step 4 below (`SequenceMatcher` on hunk text) is not
   itself guaranteed to reach `1.0` for a true match, for reasons specific to how
   step 1's normalization works — see step 1.

1. **Normalize both sides the same way the exact check does.** The candidate's
   patched source and the original source are both round-tripped through
   `ast.unparse(ast.parse(...))`, so cosmetic differences (indentation, quote
   style, redundant parentheses) cancel out on both sides. This reuses the exact
   check's existing `minimal_candidate_diff` function — nothing new here. One
   side effect: `ast.unparse` also reformats blank-line spacing *elsewhere* in
   the file (e.g. between unrelated methods), which can shift line offsets
   enough to change which *unchanged* lines fall inside the fixed-size context
   window a later step compares — even when the fix itself is byte-identical.
   Step 0 exists specifically to route around that.

2. **Slice each diff into hunks, keeping context.** A new helper, `extract_hunks`,
   walks a unified diff and cuts it into contiguous blocks — one block per `@@ ...
   @@` section — keeping every line in that block (context, added, and removed),
   and dropping only the file-header lines and the `@@` marker itself (its line
   numbers are noise here, since the candidate's synthetic diff and the real
   reference diff won't share the same numbering).

3. **Whitespace-normalize each line, but remember whether it's `+`, `-`, or
   context.** Each line's leading marker (`+`, `-`, or a plain space) is preserved
   so an *added* line is never confused with a *removed* or *context* line, while
   the rest of the line has its whitespace collapsed the same way the exact check
   does.

4. **Compare hunks with `difflib.SequenceMatcher`.** This is Python's standard
   "how similar are these two blocks of text?" tool — the same family of algorithm
   behind tools like `diff`. It returns a ratio from `0.0` (nothing alike) to `1.0`
   (identical). Every candidate hunk is compared against every reference hunk, and
   the **best-matching pair** is kept as the final score.

5. **Why hunk-to-hunk, not whole-file-to-whole-file?** Comparing entire files would
   drown out a one-line fix inside a 2,000-line file — the files would be ~99.9%
   identical regardless of whether the fix itself was any good. Comparing just the
   hunks (edit + immediate neighborhood) keeps the score sensitive to the part that
   actually matters.

## A worked example

Developer fix: change `>` to `>=` in a bounds check.

| Candidate | Exact-diff check | Context similarity score |
|---|:---:|:---:|
| Reproduces the fix exactly | `True` | `1.00` |
| Same `>=` fix, but a local variable got renamed nearby | `False` | `~0.85` |
| A different, unrelated way of fixing the same bug (e.g. an early-return guard) | `False` | `~0.71` |

The exact check can't distinguish the second row from the third — both are just
`False`. The similarity score separates them clearly.

## Why this matters for studying LLM behavior

The exact-diff check is deliberately strict, and that strictness is itself useful:
if an LLM reproduces the developer's fix byte-for-byte over and over, that's a
signal of **overfitting to, or memorization (data contamination) of, the
benchmark's fixes** — since BugsInPy bugs are old, public GitHub commits that may
already be in a model's training data — rather than genuine reasoning.

The similarity score complements that signal instead of replacing it:

- A **cluster of scores at exactly `1.0`** looks like memorization/recitation.
- A **spread of high-but-not-perfect scores** (`0.7`–`0.95`, say) looks more like a
  model that is genuinely reasoning its way toward the right fix without having
  seen it verbatim.

So the two metrics answer two different questions side by side: *"did it recite the
answer?"* (exact-diff) versus *"how close did it get, structurally?"* (context
similarity).

## Opt-in via `--similarity-score`

Scoring is off by default. A plain `repair` run produces output identical to a
build that never had this metric at all — no `context_similarity_score` field
anywhere, no extra terminal output. The `is_correct`/`correct_count`
data-contamination signal described above is completely unaffected either way,
since scoring is purely additive when it does run.

Pass `--similarity-score` (or `--no-similarity-score` to be explicit about leaving
it off) to turn it on:

```bash
python -m apr_framework repair --project <project> --bug <bug_id> \
  --technique llm --fl-mode perfect --similarity-score
```

## Where the numbers show up

With `--similarity-score` enabled, every plausible patch's score is attached to
[`repair_results.json`](../src/apr_framework/evaluation/repair_runner.py) as two
top-level fields, right next to the existing `is_correct` boolean:

- `context_similarity_score` — the raw float, `0.0`–`1.0`.
- `similarity_band` — a human-readable label for that float (`"identical to the
  developer fix"`, `"very similar (nearly the same edit)"`,
  `"similar (recognizable overlap)"`, `"loosely similar"`, or
  `"different (little in common)"`), so the number doesn't have to be eyeballed
  cold.

The CLI also prints a summary block after the usual run summary:

```
Similarity scores for plausible patches (closeness to the developer fix, 0.0-1.0):
  1.00        identical to the developer fix
  0.85-0.99   very similar (nearly the same edit)
  0.60-0.84   similar (recognizable overlap)
  0.30-0.59   loosely similar
  0.00-0.29   different (little in common)
  Patch 1 (llm-1-0) -> 0.84  (similar (recognizable overlap))
  Patch 2 (llm-1-1) -> 0.84  (similar (recognizable overlap))
  Patch 3 (llm-1-2) -> 0.92  (very similar (nearly the same edit))
```

No existing field, status, or count changes when the flag is on — this is purely
an additional column of information about patches that were already being
tracked.
