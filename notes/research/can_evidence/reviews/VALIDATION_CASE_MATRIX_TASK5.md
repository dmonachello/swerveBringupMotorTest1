# Validation Case Matrix

## Purpose

Purpose: define the first-pass validation scenarios and expected conclusions for CAN device evidence work so later implementation can be checked against concrete cases rather than intuition.

This is a Task 5 preparation artifact for:

- `docs/TASK_LIST_CAN_EVIDENCE_SOURCE_PREP.md`
- `docs/FEATURE_SPEC_CAN_DEVICE_EVIDENCE_SOURCE_CONTRACTS.md`

## Scope

This matrix captures the current known scenarios from `allDevicesTests.txt` and the linked Task 1 run notes.

For each case, it records:

- intended ground truth
- expected source behavior
- expected question-level conclusions for:
  - existence
  - operability
  - identity/mapping

## Source Keys

- `passive`
- `console`
- `active_probe`
- `manual_test`

## Question Keys

- `existence`
- `operability`
- `identity`

## Case 0: All Devices Connected

- Raw source:
  - `allDevicesTests.txt` (`test 0`)
- Scenario:
  - all expected devices connected on `test_minimal_25_9`
- Intended ground truth:
  - `SPARKMAX/NEO 25` present
  - `FALCON 9` present
  - `PDP 20` present
  - roboRIO connected to the CAN bus

### Expected Source Conclusions

#### passive

- existence:
  - expected devices visible with fresh traffic
- operability:
  - no strong negative evidence
- identity:
  - weak positive only; passive alone does not prove correct response mapping

#### console

- existence:
  - no strong negative evidence
- operability:
  - no device-local timeout evidence
  - transient high utilization may appear, but should not trigger a missing/failed device claim by itself
- identity:
  - unknown

#### active_probe

- existence:
  - expected to classify supported devices as present
- operability:
  - expected to classify supported devices as operable or healthy enough for first pass
- identity:
  - weak-to-moderate positive only

#### manual_test

- existence:
  - expected positive if correct devices respond
- operability:
  - expected strong positive if correct motors respond normally
- identity:
  - expected strong positive if the intended target responds and no wrong target responds

## Case 1: PDP Disconnected

- Raw source:
  - `allDevicesTests.txt` (`test 1`)
- Scenario:
  - `PDP 20` disconnected
- Intended ground truth:
  - PDP missing or unreachable from roboRIO
  - other core devices still expected to be present

### Expected Source Conclusions

#### passive

- existence:
  - should eventually show PDP missing/stale if passive observation distinguishes it cleanly
- operability:
  - weak negative for PDP
- identity:
  - unknown

#### console

- existence:
  - strong negative for PDP due to repeated PDP reader timeout behavior
- operability:
  - strong negative for PDP
- identity:
  - not a mapping case

#### active_probe

- existence:
  - should not confidently classify PDP as present
- operability:
  - should classify PDP as failed/unknown rather than healthy
- identity:
  - unknown

#### manual_test

- existence:
  - usually not primary for PDP
- operability:
  - may remain not applicable for this class in first pass
- identity:
  - not primary

## Case 2: FALCON 9 Disconnected

- Raw source:
  - `allDevicesTests.txt` (`test 2`)
- Scenario:
  - `FALCON 9` disconnected
- Intended ground truth:
  - FALCON 9 missing or unreachable from roboRIO
  - broader path health may also be degraded

### Expected Source Conclusions

#### passive

- existence:
  - should show FALCON 9 missing/stale from the expected set
- operability:
  - weak-to-moderate negative
- identity:
  - unknown

#### console

- existence:
  - moderate negative for FALCON 9 specifically
  - strong negative for path/bus health during the fault window
- operability:
  - strong negative
- identity:
  - little direct mapping evidence

#### active_probe

- existence:
  - should fail to confirm FALCON 9 presence
- operability:
  - should classify the target as failed/unknown rather than present/healthy
- identity:
  - unknown or weak

#### manual_test

- existence:
  - no response from the intended Falcon target would support a negative conclusion
- operability:
  - strong negative if command produces no response
- identity:
  - strong negative only if a wrong device responds instead

## Case 3: SPARKMAX Disconnected

- Raw source:
  - `allDevicesTests.txt` (`test 3`)
- Scenario:
  - `SPARKMAX/NEO 25` disconnected
- Intended ground truth:
  - Spark device at CAN ID `25` missing or unreachable from roboRIO

### Expected Source Conclusions

#### passive

- existence:
  - should show Spark missing/stale from the expected set
- operability:
  - weak-to-moderate negative
- identity:
  - unknown

#### console

- existence:
  - strong negative for Spark ID `25`
- operability:
  - strong negative for Spark ID `25`
- identity:
  - moderate negative only in the sense that the named expected ID is the failing target, not a wrong-target mapping event

#### active_probe

- existence:
  - should fail to confirm Spark presence
- operability:
  - should classify Spark as failed/unknown rather than healthy
- identity:
  - unknown or weak

#### manual_test

- existence:
  - no response from the intended Spark target would support a negative conclusion
- operability:
  - strong negative if no response occurs
- identity:
  - strong negative only if a wrong target responds

## Case 4: roboRIO Isolated From The CAN Bus

- Raw source:
  - `allDevicesTests.txt` (`test 4`)
- Scenario:
  - roboRIO disconnected from the rest of the CAN bus
- Intended ground truth:
  - controller-side communication to multiple downstream devices is broken
  - not necessarily multiple independent device-local faults

### Expected Source Conclusions

#### passive

- existence:
  - depends heavily on observer placement
  - passive may still see downstream traffic even while the roboRIO cannot
- operability:
  - should help reveal the observer/controller disagreement
- identity:
  - weak

#### console

- existence:
  - weak for any one device considered alone
  - strong for broad communication loss pattern
- operability:
  - strong negative for roboRIO-to-bus communication health
- identity:
  - unknown

#### active_probe

- existence:
  - likely to fail across multiple downstream classes
- operability:
  - strong negative across multiple queried downstream classes
- identity:
  - not useful for mapping in this scenario

#### manual_test

- existence:
  - likely negative or inconclusive from roboRIO command path
- operability:
  - strong negative from the roboRIO control perspective
- identity:
  - likely not informative unless an unexpected path still responds

## Important Validation Rule

Case 4 must not be scored as “multiple independent missing devices” by default.

The expected correct interpretation is:

- broad roboRIO-to-bus communication isolation
- multiple device-local timeout symptoms as a consequence

This is a key anti-false-certainty case for the later combined analyzer.

## Current Validation Coverage

Covered now:

- healthy baseline
- power-distribution missing case
- CTRE motor-controller missing case
- REV motor-controller missing case
- controller isolated from downstream CAN bus

Still desirable later:

- wrong device responds
- wrong branch responds
- intermittent recovery case
- degraded but not fully missing case
- reconnect recovery cases
- SparkFlex-specific real-hardware case
- PDH-specific real-hardware case

## Current Recommendation

Use these five cases as the first validation baseline.

Do not treat them as the final complete matrix.

They are strong enough to validate:

- console parser semantics
- source-specific negative-evidence handling
- distinction between single-device failure and broad communication isolation
