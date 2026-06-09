# DSL Testing Improvements

## Purpose

Capture the next round of improvements for robot-side DSL testing after the recent stabilization pass.

This document is intentionally focused on:

- test authoring ergonomics
- validation quality
- runtime result quality
- UI/operator understanding
- remaining workflow traps

It is not a replacement for the core DSL language specs. It is a follow-on product/spec note for practical testing improvements.

## Current State

Recent work materially improved DSL testing:

- profile-scoped DSL import behavior is safer
- host/robot DSL catalog sync is less error-prone
- validation warnings are more specific
- triggered condition values now appear in test results
- Output tab handling for test lifecycle and report streaming is more coherent

The DSL is more trustworthy than it was, especially for:

- understanding why a test passed
- verifying that the intended condition fired
- avoiding accidental cross-profile test-set confusion

## Main Remaining Gaps

### Semantics Are Powerful But Not Ergonomic

The current `require`, `until`, `success`, and `abort` model is expressive, but easy to misuse.

Examples of repeated confusion:

- `until timer.elapsed ...` without proof requirements
- using `success` where `require` was actually intended
- wanting a target condition and a timeout condition, both with different semantic meaning

The language currently supports these cases, but the intent is not always easy to express clearly.

### Validation Explains Risk But Not Intent

Current validation can detect risky structures, but it does not go far enough in suggesting likely repairs.

Example:

- `until without require -> may pass without proof`

This is useful, but often the more helpful message would be:

- what likely went wrong
- what the author probably meant
- which alternative pattern fits the stated intent

### Final Result Summaries Are Still Thin

Adding the triggered condition value was a good step.

But final result summaries still do not fully answer:

- which `require` clauses were satisfied
- which exit condition fired first
- what the peak observed values were during the run
- whether fallback/default-signal behavior was active

### Run-All Reporting Is Still Mostly Text Stream

`runAllTests` currently gives useful streamed output, but not a strong structured final summary payload.

That makes operator review harder than it needs to be.

### UI Still Exposes Some Testing Concepts Indirectly

The DSL workflow is better, but still has room to improve around:

- showing the active test set clearly
- showing profile ownership clearly
- showing why a test passed in a compact UI form

## Improvement Areas

## 1. Semantics Ergonomics

### Goal

Reduce common authoring mistakes without weakening the existing execution model.

### Candidate Improvements

- Add syntax sugar for common `require + until + timeout` patterns.
- Add a clearer first-class notion of “good exit condition.”
- Add a more readable idiom for “target reached is best outcome; timeout is acceptable but lower confidence.”
- Add canonical timeout helpers or recommended forms.

### Constraint

Do not change existing DSL runtime behavior casually.

Preferred direction:

- new syntax should compile to the existing model
- old syntax should remain valid

### Discussion

The current model is technically correct:

- `abort` = bad exit
- `success` = immediate good exit
- `until` = normal stop condition
- `require` = proof obligation

But common testing intent often feels verbose when expressed in that model.

## 2. Validation Improvements

### Goal

Move validation from “detect risky structure” toward “diagnose likely author intent.”

### Candidate Improvements

- For `until` without `require`, include likely repair suggestions.
- Detect suspicious `success` clauses that probably terminate too early.
- Detect tests that can pass with too little device proof.
- Detect profile/test-set mismatches with a direct explanation instead of only device-not-found cascades.
- Distinguish hard validation errors from lint-style warnings more clearly.

### Example Direction

Instead of only:

- `until without require -> may pass without proof`

Prefer something closer to:

- `Timer until has no proof requirement. If timeout should only stop the test, add require ...`
- `Success clause may terminate before target condition is reached. Consider require instead.`

## 3. Final Result Quality

### Goal

Make every DSL result line and result payload more useful for pit-side diagnosis and test review.

### Candidate Improvements

- Include the fired condition value, which is already done.
- Include the reference name in the value text, not just `value=...`.
- Record which `require` clauses ended satisfied or unsatisfied.
- Record the first terminal condition that fired.
- Preserve peak or max-observed values for key signals.
- Preserve whether signal fallback/default behavior was active during the run.

### Example Future Result

Possible future result format:

`PASS (until until_1: FALCON 9.position_delta > 150.0 observed=150.218 requires=1/1 maxCurrent=18.2A time=6.25s)`

This is not a required format yet. It is an example of the information density we want.

## 4. Run-All Summary Quality

### Goal

Give `runAllTests` a structured completion summary in addition to the streamed printer output.

### Candidate Improvements

- final structured summary payload
- counts:
  - total
  - passed
  - failed
  - aborted
  - interrupted
- per-test terminal condition summary
- total elapsed run-all time

### Rationale

The streamed text is good for live visibility, but a structured summary is better for:

- UI post-run review
- CLI automation
- saved test evidence

## 5. UI / Operator Experience

### Goal

Make the meaning of DSL testing clearer from the UI without requiring users to infer language semantics.

### Candidate Improvements

- show the active DSL test set prominently
- show profile ownership of imported tests
- show “why this passed” in a compact panel:
  - exit condition
  - observed value
  - proof conditions satisfied
- show a clearer distinction between:
  - test management
  - test execution
  - test source inspection

### Related Work

The recent action-button regrouping already moved in this direction.

This area should continue to align with:

- `Run Tests`
- `Manage DSL Tests`

as separate operator tasks.

## 6. Test Templates and Authoring Guidance

### Goal

Reduce repeated authoring mistakes by giving canonical examples.

### Candidate Improvements

- provide templates/snippets for:
  - move until limit
  - move to target with timeout
  - joystick-driven manual run
  - current-limit abort
  - minimum acceptable motion before timeout
- expose these in docs and, if practical later, in UI authoring flows

### Rationale

Many DSL questions are not really language failures. They are missing-pattern failures.

## 7. Runtime Performance Awareness

### Goal

Keep DSL improvements from hiding robot-loop cost issues.

### Discussion

The DSL itself is more solid now, but the robot still shows significant loop overruns.

That means future DSL testing work should continue to consider:

- test execution cost
- report printing cost
- UI/REST command cost
- per-loop safety under sustained diagnostics activity

This is adjacent to DSL work, but important enough to keep visible.

## Prioritized Next Steps

## Priority 1

Improve validator guidance.

Most practical next value:

- better intent-oriented warning text
- likely repair suggestions
- clearer distinction between lint warnings and hard errors

## Priority 2

Improve final run summaries.

Most practical next value:

- include richer condition/proof summary in result payloads
- add structured final summary for `runAllTests`

## Priority 3

Design a syntax-shortcut proposal for common testing patterns.

Most practical next value:

- make common “target + timeout + minimum proof” tests easier to author correctly

## Open Questions

SID_QUESTION: Should the next syntax ergonomics step be pure sugar over the current model, or is there appetite for a small semantic expansion if it greatly improves author clarity?

SID_QUESTION: Should validator “suggested fix” text be purely descriptive, or should it offer near-copy-paste replacement snippets?

SID_QUESTION: For run-all structured summaries, should the result be surfaced only in REST/UI, or also preserved in the robot-side printed output in a compact form?

## Tradeoffs

- More DSL syntax convenience improves authoring speed, but can make the language less minimal.
- Richer validation is helpful, but too much “smart guessing” can become noisy.
- Richer test summaries improve diagnosis, but can bloat output if not carefully scoped.

## Future Extensions

- DSL authoring wizard for common patterns
- per-test result history with searchable structured metadata
- saved test baselines for comparing runs over time
- profile-aware DSL library of reusable snippets

