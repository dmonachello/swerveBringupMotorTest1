# CAN Evidence Run Note

## Purpose

Purpose: record the exact setup, workflow, and observations for one console evidence capture run.

## Run Identity

- Date: 2026-06-03
- Operator: dmona
- Profile: `test_minimal_25_9`
- Scenario: `sparkmax_disconnected_startup`
- Raw log file: `allDevicesTests.txt` (`test 3`)
- Screenshot references: `diagram 3.png`, `diagram 4.png`

## Physical Setup Before Power-Up

- Connected devices: `FALCON 9`, `pdp`, `roborio`, `limitSwitch0`, `xboxController0`
- Disconnected device, if any: `SPARKMAX/NEO 25`
- Other relevant wiring/setup notes: `FALCON 9` had been reconnected before this case; `SPARKMAX/NEO 25` was then intentionally disconnected

## Workflow Used

- Console capture started at: before profile apply/activate and runtime bringup
- Robot booted at: already running; profile was applied and runtime was activated during capture
- Startup idle window length: long enough to capture repeated Spark timeout behavior
- Manual test sequence used: not separately described in the source notes
- Post-test idle window length: not separately timed
- Console capture stopped at: after repeated Spark timeout lines had accumulated

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

SID_COMMENT: Future runs should record whether right-click testing was attempted during the disconnected Spark case and whether the wrong mechanism or no mechanism responded.

## Physical Observations

- What physically moved: not recorded in the provided notes
- Whether the correct device responded: not recorded
- Whether any wrong device responded: not recorded
- Any intermittent or degraded behavior: disconnected Spark case produced both device-specific timeout messages and bus-health warnings

## Console Observations

- Notable console messages:
  - `[CAN] BUS OFF event detected! Check wiring/termination/noise.`
  - `[CAN] Error spike: rx=50 tx=0 (delta rx=50 tx=0)`
  - `CAN message is stale, data is valid but old. Check the CAN bus wiring, CAN bus utilization, and power to the device.`
  - `[Spark Max] IDs: 25, timed out while waiting for Period Status 0: HAL: CAN Receive has Timed Out`
  - `[Spark Max] IDs: 25, timed out while waiting for Frame Mgr: Period Status 0: HAL: CAN Receive has Timed Out`
- Approximate timing relative to boot/test/reconnect:
  - bus-health and Spark timeout messages occurred after profile activation/runtime activity
  - Spark timeout lines repeated densely for the remainder of the capture
- Whether reconnect produced new console output: reconnect behavior was not included in the provided notes

## Passive/Other Observations

- Any passive CAN visibility observations:
  - one screenshot shows `SPARK` still listed in defined nodes with fresh traffic before runtime became inactive
  - later screenshot shows `SPARK` row present but marked `N` in the defined-node visibility column and highlighted red in topology
  - runtime-inactive screenshot indicates the system later stopped active runtime while the Spark disconnect state remained visible in UI
- Any UI/runtime observations worth preserving:
  - bottom banner shows `Runtime inactive. Click Runtime Activate.` in the later screenshot
  - this case produced both device-specific and system-level warnings

## Initial Interpretation

- Expected device existence impression: strong negative evidence that `SPARKMAX/NEO 25` is missing or unreachable
- Expected device operability impression: strong negative evidence for Spark operability
- Expected identity/mapping impression: little evidence of wrong mapping; the console strongly points to the expected Spark ID itself
- Ambiguities or surprises:
  - this case combines very specific device-local evidence with broader bus-health evidence
  - the specific Spark timeout messages are much higher-value for device attribution than the generic stale-message or bus-off lines
