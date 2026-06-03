## Purpose

Purpose: define the concrete user-owned preparation tasks that should be completed before implementing `docs/FEATURE_SPEC_CAN_DEVICE_EVIDENCE_SOURCE_CONTRACTS.md`.

This checklist is focused on collecting the real-world evidence, decisions, and validation targets needed to implement the source contracts without guessing.

## How To Use This List

- Treat this as a pre-implementation gate.
- Mark each item complete only when the referenced artifact or decision exists in the repo.
- Prefer small saved artifacts over memory or chat-only conclusions.

## Task 1: Save Real Console Log Corpus

Goal: build a representative corpus of roboRIO console output from normal runs and known fault cases.

Deliverables:

- Save raw console logs from recent tests into a stable repo location.
- Include both normal and failure cases.
- Name files so the scenario is obvious.

Recommended saved scenarios:

- healthy normal startup and idle
- healthy motor/manual test run
- missing device
- wrong CAN ID or wrong device type
- intermittent communication
- bus stress / high utilization
- PDP or PDH timeout-style case

Done when:

- at least one raw log exists for each major scenario already observed in testing
- the files are named well enough that someone else can tell what case they represent

## Task 2: Label Trusted Console Message Families

Goal: decide which console message families are strong evidence and what they mean.

Deliverables:

- A short reviewed inventory of important console message patterns.
- For each pattern, document:
  - example raw text
  - interpreted meaning
  - scope: device or system
  - confidence role: strong negative / moderate hint / weak hint
  - whether it applies to existence, operability, identity/mapping, or multiple

Priority families:

- CAN timeout messages
- Spark timeout / firmware query failures
- wrong-device-type messages
- HAL CAN receive timeout
- PDP and PDH reader failures
- high utilization / error spike patterns

Done when:

- the currently trusted console patterns are documented in one place
- ambiguous patterns are explicitly marked as ambiguous instead of assumed

## Task 3: Define Manual Test Outcome Vocabulary

Goal: create the small structured outcome set for manual stimulus-response tests.

Deliverables:

- A first-pass vocabulary for machine-observed and operator-observed outcomes.
- Clear meanings for each outcome code.

Recommended initial outcomes:

- `correct_response`
- `no_response`
- `wrong_device_response`
- `wrong_branch_response`
- `intermittent_response`
- `degraded_response`
- `operator_uncertain`

Done when:

- each outcome has a one-line meaning
- the list is small enough to be used consistently during testing

## Task 4: Confirm First-Pass Device-Class Coverage

Goal: decide which device classes must be supported in the first implementation wave.

Deliverables:

- A reviewed list of first-pass required classes.
- A separate list of classes explicitly allowed to remain partial or unsupported.

Minimum expected current candidates:

- TalonFX
- SparkMax
- SparkFlex
- PDP
- PDH

Done when:

- the first-pass supported list is explicit
- unsupported or partial classes are called out rather than left implicit

## Task 5: Build Known-Good / Known-Bad Validation Cases

Goal: define the scenarios the implementation must be checked against.

Deliverables:

- A small scenario list covering both good and failure states.
- For each scenario, state what ground truth is believed to be true.

Recommended validation cases:

- expected device present and healthy
- expected device absent
- expected device present but degraded
- wrong device at expected CAN ID
- correct controller but wrong mechanism/mapping responds
- bus-wide pressure or noisy communication
- intermittent failure that later recovers
- PDP or PDH weak-evidence case

Done when:

- there is a saved list of validation cases with expected conclusions
- at least a few cases are backed by real captured logs or test notes

## Task 6: Define Operational Meaning Of High Confidence

Goal: decide what “high confidence” means for this project in practice.

Deliverables:

- A short definition of acceptable confidence behavior for:
  - existence
  - operability
  - identity/mapping

Questions to answer:

- When is `unknown` preferred over a positive or negative claim?
- Which false positive is most dangerous?
- Which false negative is most acceptable?
- Is a wrong mapping claim more serious than an operability miss?

Done when:

- the project has a practical confidence posture rather than only a vague goal

## Task 7: Decide Where Manual Test Results Live

Goal: choose the durable machine-readable storage/surface for manual stimulus-response results.

Deliverables:

- A decision about the canonical storage path or publication surface.
- A note about which surfaces consume it later.

Examples of possible surfaces:

- robot-side runtime snapshot attachment
- report JSON attachment
- dedicated robot-owned NT subtree
- test result artifact persisted with runtime report output

Done when:

- there is one declared canonical home for manual test result records

## Task 8: Save Representative Test Notes And Observations

Goal: preserve the observations that explain how real hardware behaved during recent experiments.

Deliverables:

- Short notes tying a test case to:
  - what was commanded
  - what physically happened
  - what telemetry was seen
  - what console messages were seen
  - what passive visibility did

Done when:

- at least the most important recent test cases are no longer only in memory or chat

## Task 9: Identify Current Source Gaps

Goal: explicitly list what is missing before implementation starts.

Deliverables:

- A short gap list for each source:
  - passive visibility
  - console diagnostics
  - active vendor probe
  - manual stimulus-response

Examples:

- missing parser rules
- unclear freshness threshold
- unsupported device class
- no machine-readable result storage
- no validation scenario

Done when:

- the biggest unknowns are named before code work starts

## Suggested Execution Order

1. Save real console log corpus.
2. Label trusted console message families.
3. Define manual test outcome vocabulary.
4. Confirm first-pass device-class coverage.
5. Build known-good / known-bad validation cases.
6. Decide where manual test results live.
7. Define operational meaning of high confidence.
8. Save representative test notes and observations.
9. Identify current source gaps.

## What This Unlocks

Completing this checklist should make it possible to implement:

- source-specific result schemas
- parser/normalizer logic
- durable manual-test result records
- later combined analysis with less guessing

It does not by itself complete the final high-confidence CAN truth system.

Further work will still be needed for:

- schema implementation
- source normalization code
- result storage
- combined analysis
- threshold tuning
- validation on real hardware fault cases
