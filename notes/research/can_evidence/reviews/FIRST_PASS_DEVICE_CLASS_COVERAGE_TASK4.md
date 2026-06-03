# First-Pass Device-Class Coverage

## Purpose

Purpose: define the explicit first-pass device-class coverage for the CAN device evidence work so implementation does not have to infer scope from scattered notes.

This is a Task 4 preparation artifact for:

- `docs/TASK_LIST_CAN_EVIDENCE_SOURCE_PREP.md`
- `docs/FEATURE_SPEC_CAN_DEVICE_EVIDENCE_SOURCE_CONTRACTS.md`
- `docs/FEATURE_SPEC_ACTIVE_DEVICE_PRESENCE_CONFIDENCE.md`

## Coverage Goal

The first implementation wave should support the device classes already central to the current bringup and evidence work, while making conservative limitations explicit where the evidence quality is weaker.

This document defines:

- required first-pass classes
- conservative/partial classes
- currently out-of-scope classes

## Required First-Pass Classes

These classes are considered required for the first implementation wave.

## 1. `TalonFX`

- Vendor: CTRE
- Role:
  - active vendor probe
  - passive visibility
  - console diagnostics
  - manual stimulus-response evidence
- First-pass expectation:
  - strong existence coverage
  - moderate-to-strong operability coverage
  - weak-to-moderate identity/mapping coverage until manual-test evidence is fused

## 2. `SparkMax`

- Vendor: REV
- Role:
  - active vendor probe
  - passive visibility
  - console diagnostics
  - manual stimulus-response evidence
- First-pass expectation:
  - strong existence coverage
  - strong device-local console evidence coverage
  - moderate-to-strong operability coverage
  - weak-to-moderate identity/mapping coverage until manual-test evidence is fused

## 3. `SparkFlex`

- Vendor: REV
- Role:
  - active vendor probe
  - passive visibility
  - console diagnostics
  - manual stimulus-response evidence
- First-pass expectation:
  - intended to follow the same general REV communication model as `SparkMax`
  - should be included in first-pass implementation scope
- Current caution:
  - validation depth may lag `SparkMax` until equivalent real-hardware cases are collected

## 4. `PDP`

- Vendor: CTRE
- Role:
  - active vendor probe
  - passive visibility
  - console diagnostics
- First-pass expectation:
  - strong negative console evidence when PDP reader timeouts occur
  - conservative active-probe interpretation
  - useful passive presence context

## 5. `PDH`

- Vendor: REV
- Role:
  - active vendor probe
  - passive visibility
  - console diagnostics
- First-pass expectation:
  - analogous treatment to `PDP`
  - include in scope, but keep classification conservative where direct evidence is weak

## Conservative / Partial First-Pass Classes

These classes are in scope, but their source-level claims must be limited.

## `PDP`

- Reason for conservative handling:
  - direct API evidence is weaker for confident absence calls than for motor controllers
- First-pass rule:
  - do not overclaim `absent` from weak API-only evidence
  - rely more heavily on timely console evidence and corroborating sources

## `PDH`

- Reason for conservative handling:
  - same practical concern as `PDP`
- First-pass rule:
  - do not overclaim `absent` from weak API-only evidence
  - rely more heavily on timely console evidence and corroborating sources

## `SparkFlex`

- Reason for partial caution:
  - intended to be first-pass supported, but current evidence/validation depth may be lighter than `SparkMax`
- First-pass rule:
  - implement under the REV model, but treat real-hardware validation as still needing explicit confirmation

## Device Types Not Yet Guaranteed In First Pass

The following are not yet promised for the first implementation wave unless later explicitly added.

- `CANCoder`
- `Pigeon`
- other CTRE sensor/controller classes not already covered above
- other REV device classes not already covered above
- non-power, non-motor CAN classes without established source semantics
- arbitrary future device classes not yet exercised by current bringup/runtime paths

These classes may still appear in passive visibility outputs, but they are not guaranteed to have full first-pass source-contract support across all evidence sources.

## Non-CAN Or Non-Target Classes

These are relevant to the system overall but are not part of the main first-pass CAN device evidence target set.

- `roboRIO`
- `limitSwitch`
- `xboxController`

Notes:

- `roboRIO` is operationally central and should appear in topology/runtime context, but it is not a normal downstream CAN device in the same sense as the motor/power classes above.
- DIO and USB devices may still matter to workflows, but they are not part of the core first-pass CAN evidence classification target set.

## Coverage Intent By Source

| Class | Passive | Console | Active Probe | Manual Stimulus |
| --- | --- | --- | --- | --- |
| TalonFX | Yes | Yes | Yes | Yes |
| SparkMax | Yes | Yes | Yes | Yes |
| SparkFlex | Yes | Expected Yes | Yes | Yes |
| PDP | Yes | Yes | Yes, conservative | Usually not primary manual target |
| PDH | Yes | Yes | Yes, conservative | Usually not primary manual target |

## Current Recommendation

Treat the following as the required first-pass supported CAN device classes:

- `TalonFX`
- `SparkMax`
- `SparkFlex`
- `PDP`
- `PDH`

With these explicit cautions:

- `PDP` and `PDH` must remain conservative for absence classification
- `SparkFlex` is in scope, but needs explicit validation depth comparable to `SparkMax`
- other device classes are not assumed to have first-pass full evidence support

## What This Unlocks

Making this list explicit allows the next implementation specs to:

- define per-class source hooks without open-ended scope creep
- set realistic done criteria
- separate “supported now” from “visible but not fully classified”
- avoid accidental claims for unsupported device classes
