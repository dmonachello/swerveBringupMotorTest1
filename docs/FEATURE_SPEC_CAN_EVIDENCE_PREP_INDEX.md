SPEC_STATUS: WORKING

# CAN Evidence Prep Index

## Purpose

Purpose: provide one reference entry point for the preparation artifacts that define and support the upcoming detailed feature spec and implementation spec for CAN device evidence unification and later fusion.

Use this document as the master index for the pre-implementation work.

## Core Spec Documents

- `docs/FEATURE_SPEC_CAN_DEVICE_EVIDENCE_SOURCE_CONTRACTS.md`
  - Main pre-fusion source-contract spec
  - Defines the four source types, common result envelope, ownership, freshness, claim boundaries, consumer contract, and layering

- `docs/TASK_LIST_CAN_EVIDENCE_SOURCE_PREP.md`
  - Concrete preparation checklist
  - Defines the user-owned pre-implementation tasks that need to be completed or advanced before full implementation

## Capture Workspace

- `notes/research/can_evidence/README.md`
  - Workspace overview and naming guidance

- `notes/research/can_evidence/TEST_WORKFLOW_TASK1.md`
  - Standard workflow for Task 1 capture runs

- `notes/research/can_evidence/run_notes/RUN_NOTE_TEMPLATE.md`
  - Reusable template for one capture run note

## Task 1 Run Notes

- `notes/research/can_evidence/run_notes/2026-06-03_profile_test_minimal_25_9_all_connected_baseline.md`
- `notes/research/can_evidence/run_notes/2026-06-03_profile_test_minimal_25_9_pdp_disconnected_startup.md`
- `notes/research/can_evidence/run_notes/2026-06-03_profile_test_minimal_25_9_falcon_9_disconnected_startup.md`
- `notes/research/can_evidence/run_notes/2026-06-03_profile_test_minimal_25_9_sparkmax_disconnected_startup.md`
- `notes/research/can_evidence/run_notes/2026-06-03_profile_test_minimal_25_9_roborio_isolated_from_can_bus.md`

Primary raw source currently referenced by those notes:

- `allDevicesTests.txt`
  - `test 0` = all devices connected
  - `test 1` = PDP disconnected
  - `test 2` = FALCON 9 disconnected
  - `test 3` = SPARKMAX disconnected
  - `test 4` = roboRIO isolated from the CAN bus

## Task 2 Review Artifacts

- `notes/research/can_evidence/reviews/CONSOLE_MESSAGE_FAMILY_INVENTORY_TASK2.md`
  - Reviewed console message families
  - Scope, meaning, confidence role, parser gaps, and interpretation rules

## Task 3 Review Artifacts

- `notes/research/can_evidence/reviews/MANUAL_TEST_OUTCOME_VOCABULARY_TASK3.md`
  - First-pass structured vocabulary for manual stimulus-response outcomes

## Task 4 Review Artifacts

- `notes/research/can_evidence/reviews/FIRST_PASS_DEVICE_CLASS_COVERAGE_TASK4.md`
  - Explicit first-pass device-class coverage and conservative/partial class notes

## Task 5 Review Artifacts

- `notes/research/can_evidence/reviews/VALIDATION_CASE_MATRIX_TASK5.md`
  - First-pass validation scenarios and expected per-source conclusions

## Task 6 Review Artifacts

- `notes/research/can_evidence/reviews/OPERATIONAL_CONFIDENCE_POLICY_TASK6.md`
  - Practical confidence posture, downgrade rules, and `unknown` preference guidance

## Task 7 Review Artifacts

- `notes/research/can_evidence/reviews/MANUAL_TEST_RESULT_STORAGE_DECISION_TASK7.md`
  - Canonical machine-readable storage decision for manual stimulus-response results

## Task 8 Review Artifacts

- `notes/research/can_evidence/reviews/REPRESENTATIVE_TEST_OBSERVATIONS_TASK8.md`
  - Consolidated real-world observations worth preserving from the current corpus

## Task 9 Review Artifacts

- `notes/research/can_evidence/reviews/SOURCE_GAP_INVENTORY_TASK9.md`
  - Explicit current gap list by source and cross-source area

## How To Use This Index

When starting the detailed feature spec and implementation spec, use this order:

1. Read `FEATURE_SPEC_CAN_DEVICE_EVIDENCE_SOURCE_CONTRACTS.md`.
2. Check `TASK_LIST_CAN_EVIDENCE_SOURCE_PREP.md` for unresolved prep items.
3. Review the Task 1 run notes and `allDevicesTests.txt` for real observed behavior.
4. Review the Task 2 console inventory for trusted console evidence semantics.
5. Review the Task 3 manual outcome vocabulary for the manual-test source contract.

## Intended Future Documents

This index is meant to support later creation of:

- a detailed feature spec for unified CAN device evidence
- a detailed implementation spec for source normalization and storage
- a later fusion/combined-analysis spec
- parser implementation tasks and regression artifacts

## Adding New Device Types

Expected difficulty:

- moderate when the new device fits an existing vendor/source pattern
- higher when the device has unique API, console, passive, or stimulus-response semantics

Adding a new device type should be mostly additive if the architecture is followed.

Typical expected touch points:

- device-specific adapter or hook code
- source-specific normalization rules
- coverage/config tables
- validation-case additions
- console parser rules when the vendor emits unique messages

What should usually stay unchanged:

- shared source-result interface
- normalized result store
- top-level analyzer shape
- consumer surfaces that read normalized results

This is an important architectural expectation for the later implementation spec.

## Current Status

Preparation artifacts now exist for:

- source-contract definition
- prep checklist
- real initial console evidence cases
- console message-family review
- manual test outcome vocabulary
- first-pass device-class coverage
- validation-case matrix
- operational confidence policy
- manual test result storage decision
- representative test observations
- source-gap inventory

Preparation artifacts still needed or still evolving:

- additional recovery/degraded/wrong-target real cases over time
