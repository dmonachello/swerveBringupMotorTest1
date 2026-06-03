# CAN Evidence Run Note

## Purpose

Purpose: record the exact setup, workflow, and observations for one console evidence capture run.

## Run Identity

- Date: 2026-06-03
- Operator: dmona
- Profile: `test_minimal_25_9`
- Scenario: `all_connected_baseline`
- Raw log file: `allDevicesTests.txt` (`test 0`)
- Screenshot reference: `diagram 0.png`

## Physical Setup Before Power-Up

- Connected devices: `SPARKMAX/NEO 25`, `FALCON 9`, `pdp`, `roborio`, `limitSwitch0`, `xboxController0`
- Disconnected device, if any: none
- Other relevant wiring/setup notes: baseline working system with all expected devices connected

## Workflow Used

- Console capture started at: before profile apply/activate and runtime bringup
- Robot booted at: already running; profile was applied and runtime was activated during capture
- Startup idle window length: long enough to capture profile update, device creation, and early CAN-health messages
- Manual test sequence used: right-click tests on the two motors
- Post-test idle window length: not separately timed
- Console capture stopped at: after the working baseline observations were complete

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

1. Right-click test on one motor
2. Stop
3. Right-click test on the second motor
4. Stop

SID_COMMENT: Exact motor labels and exact forward/reverse steps were not written down in the source notes and should be captured explicitly on future runs.

## Physical Observations

- What physically moved: working device setup; user described this as the all-devices-connected working case
- Whether the correct device responded: assumed yes for this baseline
- Whether any wrong device responded: none noted
- Any intermittent or degraded behavior: none noted at the mechanism level

## Console Observations

- Notable console messages:
  - `=== Bringup reset ...`
  - `Warning: missing motor spec for FALCON 9`
  - `Warning: duplicate CAN ID: 0`
  - `Device created: NEO index 0 CAN 25`
  - `Device created: FALCON index 0 CAN 9`
  - `Device created: PDP index 0 CAN 20`
  - `[CAN] High utilization: 99.3%`
  - `[CAN] Utilization recovered: 10.8%`
  - `[CAN] High utilization: 81.1%`
  - `[CAN] Utilization recovered: 6.4%`
- Approximate timing relative to boot/test/reconnect:
  - profile/device creation messages occurred during startup/profile activation
  - utilization spikes occurred during early startup/initialization window
- Whether reconnect produced new console output: not applicable

## Passive/Other Observations

- Any passive CAN visibility observations:
  - defined nodes visible in the UI included `FALCON 9`, `SPARK`, `pdp`, and `roboric`
  - visibility table showed recent traffic for all expected CAN nodes
- Any UI/runtime observations worth preserving:
  - `Probe` and `Probe Score` fields were still unset
  - runtime was active during the baseline visibility screenshot

## Initial Interpretation

- Expected device existence impression: all expected CAN devices appear present
- Expected device operability impression: no console evidence of device-local failure in this baseline run
- Expected identity/mapping impression: no evidence of wrong-device or wrong-branch response in this run
- Ambiguities or surprises:
  - transient high-utilization events occurred even in the all-good case
  - startup warnings about missing motor spec for `FALCON 9` and duplicate CAN ID `0` are present but appear unrelated to the controlled disconnect cases
