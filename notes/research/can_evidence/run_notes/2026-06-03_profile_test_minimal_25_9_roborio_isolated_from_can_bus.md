# CAN Evidence Run Note

## Purpose

Purpose: record the exact setup, workflow, and observations for one console evidence capture run.

## Run Identity

- Date: 2026-06-03
- Operator: dmona
- Profile: `test_minimal_25_9`
- Scenario: `roborio_isolated_from_can_bus`
- Raw log file: `allDevicesTests.txt` (`test 4`)

## Physical Setup Before Power-Up

- Connected devices: downstream CAN devices remained on the CAN segment
- Disconnected device, if any: the roboRIO was disconnected from the rest of the CAN bus
- Other relevant wiring/setup notes: this is an isolation-of-controller case rather than one device being removed from the bus

## Workflow Used

- Console capture started at: before the isolation state was exercised
- Robot booted at: already running; runtime-state capture was active while the fault was observed
- Startup idle window length: not separately timed
- Manual test sequence used: not explicitly recorded in the source notes
- Post-test idle window length: not separately timed
- Console capture stopped at: after the repeated stale, Spark timeout, and PDP timeout behavior had been observed

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

SID_COMMENT: Future runs should record whether right-click tests were attempted while the roboRIO was isolated and what physical behavior, if any, occurred downstream.

## Physical Observations

- What physically moved: not recorded in the provided notes
- Whether the correct device responded: not recorded
- Whether any wrong device responded: not recorded
- Any intermittent or degraded behavior: broad CAN communication loss from the roboRIO perspective

## Console Observations

- Notable console messages:
  - many repeated `CAN message is stale, data is valid but old. Check the CAN bus wiring, CAN bus utilization, and power to the device.`
  - repeated `[Spark Max] IDs: 25, timed out while waiting for Period Status 0: HAL: CAN Receive has Timed Out`
  - repeated `HAL: CAN Receive has Timed Out`
  - repeated `Error at frc.robot.manufacturers.ctre.util.PdpStatusReader.snapshot(...)`
  - one `Loop time of 0.02s overrun`
  - repeated stack traces through PDP voltage and current read paths
- Approximate timing relative to boot/test/reconnect:
  - stale-message behavior began immediately and remained dense throughout the capture
  - Spark timeout and PDP timeout behavior were both present during the same fault window
- Whether reconnect produced new console output: not captured in the provided notes

## Passive/Other Observations

- Any passive CAN visibility observations: not provided in the source notes for this case
- Any UI/runtime observations worth preserving:
  - runtime-state building continued attempting device snapshots while the roboRIO-side CAN isolation existed
  - repeated snapshot-time failures likely contributed to runtime pressure and the observed loop overrun

## Initial Interpretation

- Expected device existence impression:
  - weak for any single downstream device when using console alone
  - strong evidence that the roboRIO lost communication with multiple downstream CAN devices at once
- Expected device operability impression:
  - strong negative evidence for overall roboRIO-to-bus communication health
  - strong negative evidence for both Spark and PDP operability from the roboRIO point of view during this window
- Expected identity/mapping impression:
  - little useful identity/mapping evidence
  - this case reads like controller-side bus isolation, not a wrong-device or wrong-branch response case
- Ambiguities or surprises:
  - this case combines multiple device-specific timeout families in the same window
  - unlike the single-device disconnect cases, the console evidence here points to a broader communication separation rather than one isolated missing device
  - this is a high-value scenario for later multi-source analysis because passive observation may still see downstream traffic while the roboRIO cannot
