# CAN Evidence Run Note

## Purpose

Purpose: record the exact setup, workflow, and observations for one console evidence capture run.

## Run Identity

- Date: 2026-06-03
- Operator: dmona
- Profile: `test_minimal_25_9`
- Scenario: `pdp_disconnected_startup`
- Raw log file: `allDevicesTests.txt` (`test 1`)
- Screenshot reference: `diagram 1.png`

## Physical Setup Before Power-Up

- Connected devices: `SPARKMAX/NEO 25`, `FALCON 9`, `roborio`, `limitSwitch0`, `xboxController0`
- Disconnected device, if any: `pdp`
- Other relevant wiring/setup notes: PDP was intentionally disconnected before the run

## Workflow Used

- Console capture started at: before profile apply/activate and runtime bringup
- Robot booted at: already running; profile was applied and runtime was activated during capture
- Startup idle window length: long enough to capture repeated PDP-related timeout behavior
- Manual test sequence used: not separately described in the source notes
- Post-test idle window length: not separately timed
- Console capture stopped at: after repeated timeout behavior had been observed

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

SID_COMMENT: Future runs should record whether the right-click motor tests were executed during the disconnected-PDP case and what physically happened.

## Physical Observations

- What physically moved: not recorded in the provided notes
- Whether the correct device responded: not recorded
- Whether any wrong device responded: not recorded
- Any intermittent or degraded behavior: PDP was intentionally missing

## Console Observations

- Notable console messages:
  - `HAL: CAN Receive has Timed Out`
  - `Error at frc.robot.manufacturers.ctre.util.PdpStatusReader.snapshot(PdpStatusReader.java:39): HAL: CAN Receive has Timed Out`
  - `Error at frc.robot.manufacturers.ctre.util.PdpStatusReader.snapshot(PdpStatusReader.java:36): HAL: CAN Receive has Timed Out`
  - repeated stack traces through `PowerDistributionJNI.getTemperature`
  - repeated stack traces through `PowerDistributionJNI.getVoltage`
  - `Loop time of 0.02s overrun`
- Approximate timing relative to boot/test/reconnect:
  - timeout behavior started after profile activation/runtime activity
  - repeated throughout the capture window
- Whether reconnect produced new console output:
  - reconnect was performed later, before the next scenario
  - reconnect-specific console output was not separately captured in the provided notes

## Passive/Other Observations

- Any passive CAN visibility observations:
  - screenshot shows `pdp` highlighted red in the topology view
  - defined nodes still listed `pdp` in the expected device set, but the fault coloring indicates loss/problem state
- Any UI/runtime observations worth preserving:
  - the failure surfaced while runtime/device snapshot building was occurring
  - repeated timeout/exception behavior likely contributed to runtime-state churn

## Initial Interpretation

- Expected device existence impression: strong negative evidence that the PDP is missing or unreachable
- Expected device operability impression: strong negative evidence for PDP operability
- Expected identity/mapping impression: no wrong-device evidence; this looks like a direct missing/unreachable PDP case
- Ambiguities or surprises:
  - repeated timeout handling appears expensive enough to contribute to loop-overrun noise
  - this case is more device-specific than the later FALCON/SPARK disconnect cases because the error path names the PDP reader directly
