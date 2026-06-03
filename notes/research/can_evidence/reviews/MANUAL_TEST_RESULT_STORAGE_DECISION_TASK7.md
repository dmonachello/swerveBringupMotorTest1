# Manual Test Result Storage Decision

## Purpose

Purpose: define the canonical machine-readable storage home for manual stimulus-response test results so the manual evidence source is reusable by reports, UI, DSL, and later combined analysis.

This is a Task 7 preparation artifact for:

- `docs/TASK_LIST_CAN_EVIDENCE_SOURCE_PREP.md`
- `docs/FEATURE_SPEC_CAN_DEVICE_EVIDENCE_SOURCE_CONTRACTS.md`

## Problem

Manual right-click or operator-triggered tests are some of the highest-value evidence in the system because they provide direct stimulus-response information.

If their results live only in transient UI state or only as human memory, they cannot be reused reliably by:

- top-level analysis
- report generation
- DSL/test surfaces
- later review of a diagnosis session

The project therefore needs one canonical machine-readable home for manual test result records.

## Decision

First-pass recommendation:

- the canonical home for manual stimulus-response results should be a robot-side runtime snapshot attachment and report JSON attachment

In practice:

- the robot owns the authoritative result record
- the result should be attached to the relevant device/runtime snapshot
- the same result should be emitted in canonical report JSON

## Why This Is The Best First-Pass Choice

This choice fits the current architecture direction best because:

- the robot owns the manual command/test execution path
- runtime snapshots are already the common robot-side data-sharing path
- report JSON already exists as a durable machine-readable artifact
- later UI, reports, and analyzers can all consume the same canonical record

This avoids creating a manual-test-only shadow channel.

## Ownership

Authoritative owner:

- robot side

Reason:

- the robot knows the exact test target
- the robot knows the exact command timing window
- the robot can pair the test result with runtime-owned devices and local telemetry

Host-side data may augment the record later, but should not own it.

## Required Surfaces

The manual test result record should be visible through:

- robot runtime snapshot attachments
- canonical report JSON

Optional/additive later surfaces:

- robot-owned NetworkTables subtree
- UI-specific convenience views
- saved case/evidence bundle export

## What Should Not Be Canonical

These should not be the sole source of truth:

- UI-only widget state
- temporary operator messages
- freeform notes only
- host-only ad hoc caches

Those can exist as convenience surfaces, but not as the canonical record.

## Recommended Record Placement

## Device-Level Attachment

Recommended first-pass placement:

- attach a manual-test result attachment to the target device snapshot

This keeps the result close to:

- device identity
- active probe results
- sampled telemetry
- other device-local evidence

## Report JSON

Recommended first-pass behavior:

- include the same attachment data in canonical report JSON

This provides:

- durability
- machine-readable export
- later regression/analysis reuse

## Suggested Attachment Role

The record should represent:

- the latest relevant manual stimulus-response result for that device in the current runtime/session

It may later evolve to support:

- multiple historical test result entries
- session timelines
- grouped test windows

But first pass should stay simple.

## Suggested First-Pass Fields

Recommended core fields:

- `type`
- `sourceType`
- `targetLabel`
- `targetCanId`
- `commandKind`
- `commandValue`
- `outcome`
- `observedLabel`
- `observedBranch`
- `preWindowStartMs`
- `commandStartMs`
- `commandEndMs`
- `postWindowEndMs`
- `operatorNotes`
- `machineEvidence[]`
- `capturedAtMs`

## Relationship To Other Sources

This storage decision supports the source model because:

- the manual test source keeps its own separate result object
- the result can be normalized into the shared source-result contract
- later combined analysis can read it from the same canonical report/runtime data path as other device evidence

## First-Pass Recommendation Summary

Canonical machine-readable home:

- robot-side device/runtime snapshot attachment
- mirrored into canonical report JSON

Authoritative owner:

- robot side

Not canonical by itself:

- UI-only state
- ad hoc host-only caches

## Future Extensions

- add a robot-owned NT subtree for live external consumption
- preserve multiple manual test result entries per session
- add session IDs or test run IDs for cross-source correlation
- allow host-side passive and console augmentation to be linked to the same manual test window
