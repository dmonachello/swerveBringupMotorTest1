# Representative Test Observations

## Purpose

Purpose: preserve the most important real-world observations from the current Task 1 and Task 2 work in one compact place so they are not only implied by logs and screenshots.

This is a Task 8 preparation artifact for:

- `docs/TASK_LIST_CAN_EVIDENCE_SOURCE_PREP.md`
- `docs/FEATURE_SPEC_CAN_DEVICE_EVIDENCE_SOURCE_CONTRACTS.md`

## Scope

This note is not a replacement for raw logs or run notes.

It is a concise preservation layer for the most decision-relevant observations gathered so far.

## Observations From Current Cases

## 1. Healthy baseline can still show transient CAN pressure

Observed in:

- `allDevicesTests.txt` (`test 0`)

Observation:

- the all-connected baseline still showed:
  - `CAN_BUS_UTIL_HIGH`
  - `CAN_BUS_UTIL_RECOVER`

Why it matters:

- not every CAN-health message means a fault case
- startup and activation windows can contain transient pressure even when the system is otherwise healthy

## 2. PDP disconnect produces a highly device-specific console signature

Observed in:

- `allDevicesTests.txt` (`test 1`)

Observation:

- repeated `HAL: CAN Receive has Timed Out`
- repeated `PdpStatusReader.snapshot(...)` failures
- repeated PDP voltage/temperature/current read failures

Why it matters:

- this is strong negative device-local evidence
- it is a good example of a message family the system can trust strongly for one device class

## 3. FALCON disconnect produced broader bus/path symptoms than the PDP case

Observed in:

- `allDevicesTests.txt` (`test 2`)

Observation:

- repeated `CAN message is stale`
- repeated `BUS OFF event`
- loop overrun also appeared

Why it matters:

- not every missing device presents as a neat device-local timeout family
- some failures look more like path-level or bus-level degradation than one isolated missing node

## 4. SPARK disconnect produced both device-specific and bus-level evidence

Observed in:

- `allDevicesTests.txt` (`test 3`)

Observation:

- repeated Spark timeout messages naming CAN ID `25`
- repeated `CAN message is stale`
- `BUS OFF event`
- `CAN_ERROR_SPIKE`

Why it matters:

- this is a good example of multiple evidence layers being useful together
- the Spark timeout is highly device-specific
- the bus-level warnings add context but should not replace the device-local interpretation

## 5. roboRIO isolation produced simultaneous failures across multiple device families

Observed in:

- `allDevicesTests.txt` (`test 4`)

Observation:

- repeated Spark timeout behavior
- repeated PDP reader timeout behavior
- heavy stale-message spam

Why it matters:

- this is the clearest current example of why a single source can mislead
- several device-local timeout families can be consequences of one broader communication separation
- later analysis must not interpret this as multiple unrelated root faults by default

## 6. Current screenshots preserve useful passive/topology distinctions

Observed in:

- `diagram 0.png` through `diagram 4.png`

Observation:

- the visibility/topology views preserved distinctions between:
  - defined nodes
  - unrecognized nodes
  - fresh/aged/missing visibility
  - target device coloring/state changes

Why it matters:

- passive visibility and topology context are already carrying useful evidence that console alone cannot provide

## Current Practical Lessons

- Fresh vendor/HAL console messages are very useful negative evidence.
- Some console families are highly device-local and some are broad/system-level.
- Passive visibility is necessary to separate “controller cannot see” from “bus is fully silent.”
- Manual stimulus-response remains necessary for strong identity/mapping conclusions.
- Broad communication failures can make multiple device-local signatures appear at once.

## Follow-Up Preservation Gaps

Still worth capturing later:

- reconnect recovery cases as their own preserved observations
- explicit physical-response notes from manual right-click tests
- wrong-device and wrong-branch response cases once observed
- a known degraded-but-not-fully-missing case

