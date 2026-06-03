# CAN Evidence Run Note

## Purpose

Purpose: record the exact setup, workflow, and observations for one console evidence capture run.

## Run Identity

- Date: 2026-06-03
- Operator: dmona
- Profile: `test_minimal_25_9`
- Scenario: `falcon_9_disconnected_startup`
- Raw log file: `allDevicesTests.txt` (`test 2`)
- Screenshot reference: `diagram 2.png`

## Physical Setup Before Power-Up

- Connected devices: `SPARKMAX/NEO 25`, `pdp`, `roborio`, `limitSwitch0`, `xboxController0`
- Disconnected device, if any: `FALCON 9`
- Other relevant wiring/setup notes: PDP had been reconnected before this case; FALCON 9 was then intentionally disconnected

## Workflow Used

- Console capture started at: before profile apply/activate and runtime bringup
- Robot booted at: already running; profile was applied and runtime was activated during capture
- Startup idle window length: long enough to capture repeated stale-message and bus-off behavior
- Manual test sequence used: not separately described in the source notes
- Post-test idle window length: not separately timed
- Console capture stopped at: after bus-off and stale-message behavior had been observed repeatedly

## Manual Test Sequence

Record the exact repeated sequence used for this run.

Example:

1. Right-click motor A forward
2. Stop
3. Right-click motor A reverse
4. Stop
5. Right-click motor B forward
6. Stop
7. Right-click motor B reverse
8. Stop

Actual sequence used:

1. Not explicitly captured in the source notes

SID_COMMENT: Future runs should record whether the right-click tests were attempted while FALCON 9 was disconnected and which mechanism behavior was observed.

## Physical Observations

- What physically moved: not recorded in the provided notes
- Whether the correct device responded: not recorded
- Whether any wrong device responded: not recorded
- Any intermittent or degraded behavior: disconnected FALCON 9 case produced bus-health style symptoms

## Console Observations

- Notable console messages:
  - `Loop time of 0.02s overrun`
  - `CAN message is stale, data is valid but old. Check the CAN bus wiring, CAN bus utilization, and power to the device.`
  - `[CAN] BUS OFF event detected! Check wiring/termination/noise.`
  - many repeated stale-message lines
- Approximate timing relative to boot/test/reconnect:
  - bus-off and stale-message behavior occurred after profile activation/runtime activity
  - stale-message warnings repeated densely throughout the capture window
- Whether reconnect produced new console output:
  - reconnect of `FALCON 9` occurred before the next scenario
  - reconnect-specific output was not separately captured here

## Passive/Other Observations

- Any passive CAN visibility observations:
  - screenshot shows `FALCON 9` missing from defined nodes while `SPARK`, `pdp`, and `roboric` remain in the table
  - unrecognized nodes remained visible, implying the bus was not fully silent
- Any UI/runtime observations worth preserving:
  - topology view still shows the expected FALCON location, but the defined-node table dropped it from the visible set

## Initial Interpretation

- Expected device existence impression: moderate-to-strong negative evidence that `FALCON 9` is not reachable
- Expected device operability impression: strong negative evidence that the bus path/device state is unhealthy
- Expected identity/mapping impression: limited identity information; this looks more like a bus-path/device-loss case than a wrong-device case
- Ambiguities or surprises:
  - the dominant console signature is system/bus-health oriented rather than a clean device-local timeout message naming `FALCON 9`
  - this case likely needs passive visibility and topology correlation in addition to console interpretation
