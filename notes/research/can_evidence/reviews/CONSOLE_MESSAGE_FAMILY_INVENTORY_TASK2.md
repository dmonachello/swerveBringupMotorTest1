# Console Message Family Inventory

## Purpose

Purpose: review the currently observed CAN-health-related console message families from the `test_minimal_25_9` Task 1 runs and classify what each one likely indicates.

This is a Task 2 preparation artifact for:

- `docs/TASK_LIST_CAN_EVIDENCE_SOURCE_PREP.md`
- `docs/FEATURE_SPEC_CAN_DEVICE_EVIDENCE_SOURCE_CONTRACTS.md`

## Source Runs Used

- `2026-06-03_profile_test_minimal_25_9_all_connected_baseline.md`
- `2026-06-03_profile_test_minimal_25_9_pdp_disconnected_startup.md`
- `2026-06-03_profile_test_minimal_25_9_falcon_9_disconnected_startup.md`
- `2026-06-03_profile_test_minimal_25_9_sparkmax_disconnected_startup.md`
- `2026-06-03_profile_test_minimal_25_9_roborio_isolated_from_can_bus.md`

Primary raw source:

- `allDevicesTests.txt`
  - `test 0` = all devices connected
  - `test 1` = PDP disconnected
  - `test 2` = FALCON 9 disconnected
  - `test 3` = SPARKMAX disconnected
  - `test 4` = roboRIO isolated from the CAN bus

## Review Rules

- Treat vendor/HAL-originated fresh messages as high-trust negative evidence unless the message is clearly too generic.
- Distinguish device-local messages from bus/system messages.
- Do not treat absence of a console message as positive proof of health.
- Preserve ambiguity when a message is too broad to identify one device as the root cause.

## Message Families

## 1. `CAN_BUS_UTIL_HIGH`

- Example raw text:
  - `[CAN] High utilization: 99.3%`
  - `[CAN] High utilization: 81.1%`
- Scope: system
- Applies to:
  - operability
- Confidence role:
  - moderate warning
- Likely meaning:
  - the CAN bus is under unusually high traffic pressure
  - can contribute to stale data, delayed status updates, and communication degradation
- What it does **not** prove:
  - that any one device is missing
  - that a specific device is the root fault
- Notes:
  - observed in the all-connected baseline, so this message alone is not sufficient to classify a fault

## 2. `CAN_BUS_UTIL_RECOVER`

- Example raw text:
  - `[CAN] Utilization recovered: 10.8%`
  - `[CAN] Utilization recovered: 6.4%`
- Scope: system
- Applies to:
  - operability
- Confidence role:
  - contextual recovery signal
- Likely meaning:
  - a prior high-utilization condition cleared
- What it does **not** prove:
  - that all devices are healthy
- Notes:
  - important for time-bounded interpretation of `CAN_BUS_UTIL_HIGH`

## 3. `HAL_CAN_RECEIVE_TIMEOUT`

- Example raw text:
  - `HAL: CAN Receive has Timed Out`
- Scope: ambiguous by itself
- Applies to:
  - existence
  - operability
- Confidence role:
  - strong negative only when tied to a specific reader/device context
  - otherwise broad system-level negative evidence
- Likely meaning:
  - a CAN read path timed out
  - communication expected by the caller did not complete in time
- What it does **not** prove by itself:
  - which exact device is the sole root cause
- Notes:
  - should usually be interpreted together with the immediately following reader stack or device-specific timeout line

## 4. `PDP_STATUS_READER_TIMEOUT`

- Example raw text:
  - `Error at frc.robot.manufacturers.ctre.util.PdpStatusReader.snapshot(PdpStatusReader.java:36): HAL: CAN Receive has Timed Out`
  - `Error at frc.robot.manufacturers.ctre.util.PdpStatusReader.snapshot(PdpStatusReader.java:39): HAL: CAN Receive has Timed Out`
  - `Error at frc.robot.manufacturers.ctre.util.PdpStatusReader.snapshot(PdpStatusReader.java:54): HAL: CAN Receive has Timed Out`
- Scope: device
- Applies to:
  - existence
  - operability
- Confidence role:
  - strong negative evidence
- Likely meaning:
  - the roboRIO-side PDP reader attempted to query the PDP and could not retrieve expected data
  - high-confidence indication that the PDP is missing, unreachable, or unreachable from the roboRIO in that window
- What it does **not** prove:
  - whether the PDP itself is physically absent versus electrically isolated upstream
- Notes:
  - very strong in the `pdp_disconnected_startup` case
  - also appears in the `roborio_isolated_from_can_bus` case, so this message family alone cannot distinguish local PDP loss from broader controller-side bus separation

## 5. `SPARK_STATUS_TIMEOUT`

- Example raw text:
  - `[Spark Max] IDs: 25, timed out while waiting for Period Status 0: HAL: CAN Receive has Timed Out`
  - `[Spark Max] IDs: 25, timed out while waiting for Frame Mgr: Period Status 0: HAL: CAN Receive has Timed Out`
- Scope: device
- Applies to:
  - existence
  - operability
  - identity/mapping
- Confidence role:
  - strong negative evidence
- Likely meaning:
  - the expected Spark at CAN ID `25` is not returning required status frames to the roboRIO-side code
  - high-confidence device-local communication failure for the named CAN ID
- What it does **not** prove:
  - whether the Spark is physically missing versus isolated by a broader upstream bus break
- Notes:
  - very strong in the `sparkmax_disconnected_startup` case
  - also appears in the `roborio_isolated_from_can_bus` case, so later combined analysis must check whether multiple device families failed together

## 6. `CAN_MESSAGE_STALE`

- Example raw text:
  - `CAN message is stale, data is valid but old. Check the CAN bus wiring, CAN bus utilization, and power to the device.`
- Scope: ambiguous, usually system or path-level
- Applies to:
  - operability
- Confidence role:
  - moderate negative evidence
- Likely meaning:
  - data freshness guarantees are being violated
  - a device, path, or the bus as a whole is no longer delivering timely updates
- What it does **not** prove:
  - which device is the root cause
  - whether the stale data is caused by one missing node or a broader network issue
- Notes:
  - appears heavily in the disconnected FALCON case and the roboRIO-isolated case
  - should be added as an explicit parser rule

## 7. `BUS_OFF_EVENT`

- Example raw text:
  - `[CAN] BUS OFF event detected! Check wiring/termination/noise.`
- Scope: system
- Applies to:
  - operability
- Confidence role:
  - strong system-level negative evidence
- Likely meaning:
  - severe CAN bus communication fault condition
  - likely wiring, termination, or noise issue, or a severe bus-path disruption
- What it does **not** prove:
  - which exact device caused the condition
- Notes:
  - appears in disconnected FALCON and disconnected Spark cases
  - should be added as an explicit parser rule

## 8. `CAN_ERROR_SPIKE`

- Example raw text:
  - `[CAN] Error spike: rx=50 tx=0 (delta rx=50 tx=0)`
- Scope: system
- Applies to:
  - operability
- Confidence role:
  - moderate system-level negative evidence
- Likely meaning:
  - a burst of CAN receive-side errors occurred
  - useful corroboration for bus-health degradation
- What it does **not** prove:
  - which device is the root fault
- Notes:
  - observed in the disconnected Spark case

## 9. `LOOP_OVERRUN`

- Example raw text:
  - `Loop time of 0.02s overrun`
  - `Warning at edu.wpi.first.wpilibj.IterativeRobotBase.printLoopOverrunMessage(...)`
- Scope: system
- Applies to:
  - operability
- Confidence role:
  - weak-to-moderate secondary evidence
- Likely meaning:
  - robot loop timing budget was exceeded
  - may be a consequence of repeated timeout handling, stack trace printing, or a broader runtime stall
- What it does **not** prove:
  - any CAN device fault directly
- Notes:
  - should not be treated as a primary CAN-device diagnosis signal

## 10. `MISSING_MOTOR_SPEC_WARNING`

- Example raw text:
  - `Warning: missing motor spec for FALCON 9`
- Scope: configuration/runtime setup
- Applies to:
  - none of the three target questions directly
- Confidence role:
  - not a CAN-health signal
- Likely meaning:
  - configuration metadata is incomplete for the named device
- Notes:
  - should not be mixed into CAN presence/operability evidence

## 11. `DUPLICATE_CAN_ID_WARNING`

- Example raw text:
  - `Warning: duplicate CAN ID: 0`
  - `Warning: duplicate CAN IDs can cause bringup confusion.`
- Scope: configuration/runtime setup
- Applies to:
  - identity/mapping indirectly
- Confidence role:
  - contextual setup warning
- Likely meaning:
  - duplicate configured CAN IDs exist in the system model
- What it does **not** prove:
  - that the current disconnect fault is caused by this warning
- Notes:
  - relevant background, but not part of the controlled disconnect signatures

## Current Trust Summary

Highest-value device-specific families so far:

- `PDP_STATUS_READER_TIMEOUT`
- `SPARK_STATUS_TIMEOUT`

Highest-value system/path families so far:

- `BUS_OFF_EVENT`
- `HAL_CAN_RECEIVE_TIMEOUT`
- `CAN_MESSAGE_STALE`
- `CAN_ERROR_SPIKE`

Contextual but lower-value families:

- `CAN_BUS_UTIL_HIGH`
- `CAN_BUS_UTIL_RECOVER`
- `LOOP_OVERRUN`

Non-CAN-health setup warnings:

- `MISSING_MOTOR_SPEC_WARNING`
- `DUPLICATE_CAN_ID_WARNING`

## Immediate Parser Gaps

These message families should be added or formalized in the parser:

- `BUS_OFF_EVENT`
- `CAN_MESSAGE_STALE`

These message families should remain clearly separated from CAN-health evidence:

- `MISSING_MOTOR_SPEC_WARNING`
- `DUPLICATE_CAN_ID_WARNING`

## Important Interpretation Rule

When multiple device families time out together in the same window, later combined analysis must avoid blaming the named devices independently without checking for broader controller-side or bus-path isolation.

The `roborio_isolated_from_can_bus` case is the clearest example:

- Spark timeout messages appear
- PDP timeout messages appear
- stale-message spam appears

That pattern is stronger evidence for broad roboRIO-to-bus separation than for two unrelated simultaneous device-local failures.
