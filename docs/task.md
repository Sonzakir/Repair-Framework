# Automated Debugging and Repair


## Assignment Sheet 04: LLM-Based APR

## Repository and Submission

We will keep using the same repository as for the previous assignment(s). Simply keep working on it.

Submit your work by:

1. pushing your code to the repository, and

2. submitting the final git commit hash/URL, which we should inspect for this submission, via Moodle

Your repository must contain:

- Source code

- README.md that (1) summarizes your solution, (2) provides installation instructions, and (3) demonstrates a usage example.

*Hint: have different sections in the README to summarize your solutions for the different assignments.*

1

## Task Overview/Context

This assignment builds on top of Assignments 1, 2, and 3. You have designed a modular APR framework, implemented automated fault localization, and built a traditional repair technique. It is now time to add a fundamentally different kind of repair backend: one driven by a Large Language Model (LLM).

You will implement a single-LLM-based repair approach and integrate it into your existing framework as a new repair backend. For inspiration, look at two representative techniques from the literature:

- **AlphaRepair**1 – a zero-shot, cloze-style approach that asks the LLM to fill in a masked-out buggy line using the surrounding code as context.

- **ChatRepair**2 – a conversational approach that feeds failed patch attempts and their test-failure messages back to the LLM in a multi-turn dialogue, enabling self-correction.

You do not need to re-implement either technique exactly; use them as design inspiration when making your own choices.

For LLM access, you will use **GPT@RUB**, the university’s LLM API service. Documentation and API access are available at https://gpt.ruhr-uni-bochum.de/app/documentation. The API follows the OpenAI specification and is compatible with the openai Python package. Note that **streaming is not supported**; use standard (non-streaming) completion calls only.

By the end of this assignment, your project should provide:

- An LLM-based repair backend integrated into your framework

- A thoughtfully designed prompt with configurable context

- An iterative repair loop that incorporates test-failure feedback

- Evaluation on BugsInPy bugs under automated FL and perfect FL modes

- A comparison of the LLM-based approach against your Assignment 3 technique

## Task 1: LLM Repair Backend

Implement an LLM-based repair backend that conforms to the Repair Algorithm interface you defined in Assignment 1. If that interface needs to be extended to accommodate LLM-specific behavior (e.g., token budgets, conversation history), update it and document the change in the README.

Your implementation must:

- Connect to the GPT@RUB API using the openai Python package pointed at the GPT@RUB endpoint.

- Accept a fault location (ranked list of suspicious statements/lines from Assignment 2 or a perfect FL oracle) as input.

- Construct a prompt that includes, at a minimum: the buggy function or code region around the suspected fault, the fault location (e.g., the suspicious line and its rank), and a clear instruction to produce a repaired version.

1 https://doi.org/10.1145/3540250.3549101

2 https://doi.org/10.1145/3650212.3680323

2

- Return candidate patches in the same unified-diff or structured format as your Assignment 3 technique.

- Be configurable via CLI flags and/or a config file, covering at least: model name, temperature, and maximum number of patch candidates to generate.

A minimal CLI interaction could look like this:

Listing 1: CLI Example (no need to exactly follow this)

    python -m apr_framework repair \
        --project pandas \
        --bug 12 \
        --technique llm \
        --model codestral-22b \
        --fl-mode perfect

Document your prompt design (structure, role of each section, design rationale) in the README.

## Task 2: Context Enrichment

The quality of an LLM-generated patch depends heavily on what information is included in the prompt. Your baseline prompt from Task 1 provides the buggy code and FL ranking. This task asks you to systematically enrich that context and measure the effect (Note: the evaluation will happen in Task 5).

Design and implement **at least two** context enrichment strategies. Choose from the list below, or invent your own:

- **Relevant test cases:** Include the body of one or more failing tests so the model understands what behavior is expected.

- **Error message and traceback:** Add the full exception traceback from the failing test run.

- **Code context window:** Expand beyond the single suspicious function and include caller/callee signatures or the full surrounding class.

- **Fix examples (few-shot):** Prepend one or two examples of (buggy code → fixed code) pairs from other bugs to guide the model’s output format and reasoning style.

- **FL score annotation:** Annotate each line in the provided code snippet with its suspiciousness score as an inline comment, so the model can reason about uncertainty directly.

For each enrichment strategy you should add a CLI flag or config key to toggle it on or off independently. A possible CLI interface:

Listing 2: CLI Example for context enrichment (no need to exactly follow this)

    python -m apr_framework repair \
        --technique llm \
        --project pandas --bug 12 \
        --context failing-tests error-traceback

3

## Task 3: Iterative Repair with Test-Failure Feedback

A single LLM query often produces a patch that does not pass all tests. Inspired by ChatRepair, implement an *iterative repair loop*: after each failed patch attempt, feed the test-failure output back to the LLM as part of the ongoing conversation, and ask it to try again.

Your implementation must:

- Maintain a multi-turn conversation history (list of user/assistant message pairs) across repair attempts.

- After a failed patch validation, append a user message containing the relevant test-failure output (e.g., the failing test name, the assertion error, or the exception traceback) and a prompt asking the model to revise its fix.

- Stop the loop when a plausible patch is found, the conversation budget (maximum number of turns) is exhausted, or the model signals it cannot improve further.

- Expose the maximum number of iterations as a configurable parameter.

Listing 3: CLI Example for iterative mode (no need to exactly follow this)

    python -m apr_framework repair \
        --project pandas \
        --bug 12 \
        --technique llm \
        --iterative \
        --max-iterations 5

In the README, briefly reflect on what information in the test-failure output turned out to be most useful to include in the feedback message.

## Task 4: FL-Guided Repair and Perfect Fault Localization Baseline

As in Assignment 3, evaluate your LLM-based repair technique under two fault localization conditions:

1. **Automated FL:** Use the output of your Assignment 2 fault localization implementation to provide the suspicious location(s) to the LLM prompt. You may choose which FL technique (SBFL, MBFL, or hybrid) to use.

2. **Perfect FL:** Use the ground-truth fault location from BugsInPy (the exact line(s) changed in the developer fix), bypassing the FL step entirely.

Both modes must be accessible via CLI (see the example in Task 1). Record which FL mode was used in all result files.

## Task 5: Evaluation and Comparison

Run your full LLM-based repair pipeline on at least **two** BugsInPy bugs – ideally the *same* bugs you used in Assignment 3, so a direct comparison is possible. For each bug, execute:

- LLM single-shot repair (Task 1) with automated FL

- LLM single-shot repair (Task 1) with perfect FL

4

- At least one context-enriched variant (Task 2) with automated FL

- At least one context-enriched variant (Task 2) with perfect FL

- LLM iterative repair (Task 3) with automated FL

- LLM iterative repair (Task 3) with perfect FL

Report the following metrics per bug and in aggregate, using the same format as Assignment 3 so a side-by-side comparison is straightforward:

- Number of LLM queries made, number of candidate patches generated

- Number of plausible patches and correct patches

- Time to first plausible patch and total repair time

- Effect of iterative repair: did the loop recover patches that the single-shot approach missed?

- Effect of context enrichment: which additions helped, and which did not?

- Comparison with Assignment 3: where does the LLM-based approach outperform the traditional technique, and where does it fall short?

Include a brief discussion in the README or a dedicated results/README.md. Add all experiment artifacts (result JSONs, logs) to the repository, e.g., in a results/ directory or as a .zip archive.

5

## What Comes Next

The final assignment will take LLM-based repair one step further by moving from single-LLM pipelines to more advanced LLM-based repair workflows. The clean repair-backend interface you maintain now will remain the integration point, so keep it well-abstracted.

## Submission Checklist

Before submitting, verify:

□ Code is pushed to the GitHub Classroom repository

□ README is included and updated (with a section for Assignment 4)

□ GPT@RUB API integration is working

□ LLM repair backend conforms to the existing Repair Algorithm interface

□ Prompt design is documented in the README

□ At least two context enrichment strategies are implemented and toggleable via CLI

□ Iterative repair loop with test-failure feedback is implemented

□ Automated FL and perfect FL modes are both supported via CLI

□ Evaluation on at least two bugs is included (same bugs as Assignment 3 preferred)

□ Comparison with Assignment 3 technique is documented

□ Results (JSON files, logs) are added to the repository

□ Code is documented

□ Repository is clean and organized

## Grading

In total, this sheet gives 10 points:

- 8 points – functionality

  - Task 1 (LLM repair backend): 2 points
  - Task 2 (Context enrichment): 2 points
  - Task 3 (Iterative repair with test-failure feedback): 2 points
  - Task 4 (FL-guided repair & perfect FL baseline): 0.5 points
  - Task 5 (Evaluation and comparison): 1.5 points

- 1 point – usability and maintainability

- 1 point – code readability and its documentation

The grade is determined after inspecting the code submission and the in-person checkoff.


