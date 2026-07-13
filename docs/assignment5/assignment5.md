# Automated Debugging and Repair


## Assignment Sheet 05: Advanced LLM-Based APR


## Repository and Submission

We will keep using the same repository as for the previous assignment(s). Simply keep working on it. Submit your work by:

1. pushing your code to the repository, and
2. submitting the final git commit hash/URL, which we should inspect for this submission, via Moodle

Your repository must contain:

- Source code
- README.md that (1) summarizes your solution, (2) provides installation instructions, and (3) demonstrates a usage example.

Hint: have different sections in the README to summarize your solutions for the different assignments.

## Task Overview/Context

This is the final assignment. Over the course of the semester you have built a modular APR framework (Assignment 1), implemented automated fault localization (Assignment 2), developed a traditional repair technique (Assignment 3), and added a single-LLM repair backend with iterative feedback and context enrichment (Assignment 4).

In this assignment you will upgrade all three core pipeline stages – fault localization, patch generation, and patch validation – with LLM-based components, completing a fully LLM-driven repair pipeline. The central theme is moving beyond test-suite adequacy: current APR tools can find plausible patches (patches that pass all tests) but struggle to determine whether those patches are correct (semantically equivalent to the intended fix). LLMs can reason about code in ways that pure test execution cannot, and this assignment asks you to exploit that ability.

You will add three new capabilities to your framework:

1. LLM-based fault localization – use the LLM to identify suspicious lines from failing tests and source code, as an alternative to SBFL/MBFL.
2. LLM-based patch assessment – use the LLM to reason about the semantic quality of plausible patches, beyond pass/fail.
3. Context retrieval for LLM repair – give the LLM the ability to request additional codebase context (callers, class definitions, usage sites) before generating a patch, introducing a lightweight agentic loop into the repair step.

By the end of this assignment, your project should provide:

- An LLM-based FL component returning the same ranked-location format as Assignment 2
- An LLM-based patch assessor that scores and re-ranks plausible patches
- A context retrieval loop that gives the LLM access to relevant codebase context before generating a patch
- A fully assembled LLM pipeline and a course-wide comparison of all four approaches

As in Assignment 4, you will use GPT@RUB[^1] via the openai Python package. Recall that streaming is not supported; use standard completion calls only. Note that you may need a VPN connection to access GPT@RUB outside of the university network.

[^1]: https://gpt.ruhr-uni-bochum.de/app/documentation
Use the OpenAI API as in the Assignment4- if you ran out of token budget at GPT@RUB 

## Task 1: LLM-based Fault Localization

Implement a new fault localization backend that uses the LLM to identify suspicious lines, as an alternative to the FauxPy-based SBFL/MBFL backends from Assignment 2. Your implementation must conform to the fault localization interface defined in Assignment 1.

The LLM should receive, at a minimum:

- The source file(s) relevant to the bug
- The body of the failing test(s) and their error output (traceback, assertion message)
- A clear instruction to identify and rank the lines most likely responsible for the failure

Your implementation must:

- Return a ranked list of suspicious (`file`, `line`) pairs in the same format produced by your Assignment 2 FL component, so it can be consumed as a drop-in replacement anywhere in the pipeline.
- Be selectable via CLI, e.g.:

**Listing 1: CLI Example (no need to exactly follow this)**

```bash
python -m apr_framework localize \
    --backend llm \
    --project pandas \
    --bug 12
```

## Task 2: LLM-based Patch Assessment

Plausible patches pass the test suite, but many are semantically incorrect – they overfit to the tests rather than fixing the underlying bug. Implement an LLM-based patch assessor that reasons about the semantic quality of each plausible patch and produces a quality score used to re-rank them.

For each plausible patch, provide the LLM with:

- The original buggy code (function or region)
- The patch (unified diff or equivalent)
- The failing test(s) that the patch now passes
- A clear instruction to assess whether the patch genuinely fixes the bug or merely satisfies the tests

Your assessor must:

- Return a numerical quality score (e.g., 0–1) and a brief natural-language rationale for each assessed patch.
- Re-rank the list of plausible patches by descending quality score.
- Be integrated into your evaluation runner so that assessment results are recorded in the result JSON files alongside the existing patch metrics.

*Hint: Asking the model to think step-by-step (chain-of-thought) before assigning a score tends to produce more reliable assessments.*

## Task 3: Context Retrieval for LLM Repair

A key limitation of the repair prompts from Assignment 4 is that the LLM only sees a static code snippet around the fault. Real bugs often require understanding how a function interacts with the rest of the codebase – its callers, the class it belongs to, and the types it operates on. This task asks you to give the LLM the ability to request the additional context it needs, introducing a lightweight agentic loop into your repair pipeline.

Concretely, you will implement a small set of code retrieval tools that the LLM can invoke before generating a patch:

- `get_function_definition(name)` – returns the source of a named function or method found anywhere in the project.
- `get_class_definition(name)` – returns the source of a named class, including its attributes and method signatures.
- `find_usages(name)` – returns a list of call sites (file, line, snippet) where a given function or variable is used.

You do not need to use an LLM function-calling API for this; a simple text-based protocol is sufficient. In the first turn, instruct the model that it may request any of the tools above by emitting a structured command (e.g., `RETRIEVE: get_function_definition("foo")`). Your framework parses the response, executes the retrieval, appends the result to the conversation, and invites the model to continue. The loop ends when the model emits a patch or a configurable retrieval budget (maximum number of retrieval steps) is exhausted.

**Listing 2: Schematic of the retrieval loop**

```text
[user]      Here is the buggy code and fault location.
            You may call RETRIEVE: <tool>(<args>) to fetch
            more context before proposing a fix.
[assistant] RETRIEVE: get_function_definition("_validate_input")
[tool]      def _validate_input(x): ...
[assistant] RETRIEVE: find_usages("_validate_input")
[tool]      pandas/core/frame.py:342 self._validate_input(val)
[assistant] --- a/pandas/core/frame.py
            +++ b/pandas/core/frame.py
            ...
```

Your implementation must:

- Implement the three retrieval tools backed by static analysis of the checked-out BugsInPy project (e.g., using the ast module or grep).
- Run the retrieval loop and record which tools were called and how many retrieval steps were taken per repair attempt.
- Expose the retrieval budget as a configurable CLI parameter.

## Task 4: End-to-End LLM Pipeline and Course-Wide Comparison

Assemble the fully LLM-driven repair pipeline by chaining the components from this and previous assignments:

```text
LLM-FL → LLM-Repair with Context Retrieval → LLM-Assessment
```

This complete pipeline must be runnable via a single CLI command, for example:

**Listing 3: CLI Example for the full LLM pipeline (no need to exactly follow this)**

```bash
python -m apr_framework repair \
    --project pandas --bug 12 \
    --fl-backend llm \
    --technique llm \
    --retrieval-budget 3 \
    --assess
```

Run this pipeline on at least two BugsInPy bugs – the same bugs used in Assignments 4. Then produce a course-wide comparison across all four assignment approaches on those bugs:

|  | A3 | A4 simple | A4 iterative | A5 full LLM |
|---|---|---|---|---|
| FL source | auto/perfect | auto/perfect | auto/perfect | LLM-FL |
| Repair | traditional | LLM | LLM | LLM |
| Assessment | test pass/fail | test pass/fail | test pass/fail | LLM assessor |
| Plausible patches |  |  |  |  |
| Correct patches |  |  |  |  |
| Time to first plausible |  |  |  |  |

In the README or a dedicated results/README.md, discuss: Where did the full LLM pipeline improve over prior approaches? Where did it regress or fail? Did LLM-FL outperform SBFL/MBFL, and in what situations? Did patch assessment and context retrieval help surface correct patches or reduce overfitting?

Add all experiment artifacts (result JSONs, logs, retrieval traces) to the repository.

## Submission Checklist

Before submitting, verify:

- [ ] Code is pushed to the GitHub Classroom repository
- [ ] README is included and updated (with a section for Assignment 5)
- [ ] LLM-FL backend is implemented and returns results in the Assignment 2 format
- [ ] LLM-based patch assessor is implemented and integrated into the evaluation runner
- [ ] Context retrieval tools (`get_function_definition`, `get_class_definition`, `find_usages`) are implemented
- [ ] Retrieval loop is implemented with a configurable budget and records tool calls per repair attempt
- [ ] Full LLM pipeline is runnable via a single CLI command
- [ ] Course-wide comparison table is included in the results
- [ ] Results discussion addresses FL quality, impact of context retrieval, assessment quality, and overall pipeline performance
- [ ] All experiment artifacts (JSONs, logs) are added to the repository
- [ ] Code is documented
- [ ] Repository is clean and organized

## Grading

In total, this sheet gives 10 points:

- 8 points – functionality
  - Task 1 (LLM-based fault localization): 2 points
  - Task 2 (LLM-based patch assessment): 2 points
  - Task 3 (Context retrieval for LLM repair): 2 points
  - Task 4 (End-to-end pipeline & course-wide comparison): 2 points
- 1 point – usability and maintainability
- 1 point – code readability and its documentation

