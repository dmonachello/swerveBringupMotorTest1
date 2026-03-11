# Test Procedures

Purpose: provide step-by-step, repeatable bringup tests for motors, encoders, and CAN diagnostics.

## Scope
Purpose: describe the tests that can be run during teleop using the existing bringup controls and JSON-driven tests.

This document focuses on robot-side tests and the PC CAN tool usage needed to validate CAN traffic.

## Prerequisites
Purpose: ensure the robot and tooling are ready before testing.

- Robot code deployed with the correct `bringup_profiles.json` and `bringup_tests.json`.
- Optional: select a different test set by changing `default_test_set` in `bringup_tests.json`.
- Xbox controller connected and mapped.
- CAN devices powered and on the bus.
- (Optional) PC CAN tool running if you want NetworkTables diagnostics.

## Test Controls
Purpose: list the standard controller bindings used during test procedures.

- `A`: add motor (alternates SPARK/CTRE)
- `Start`: add all configured devices
- `B`: print state
- `D-pad Left`: print health status
- `Right Bumper`: print CANCoder absolute positions
- (Secondary) `LB`: select previous test
- (Secondary) `RB`: select next test
- (Secondary) `A`: run selected bringup test (hold to satisfy hold-based tests)
- (Secondary) `B`: run all bringup tests
- (Secondary) `X`: toggle selected test enabled
- (Secondary) `D-pad Up/Right/Down/Left`: fixed speed 25/50/75/100
- `D-pad Down`: print NetworkTables diagnostics (RobotV2 only)
- `D-pad Up`: print CAN diagnostics report
- `D-pad Right`: print speed inputs
- `X`: dump CAN report JSON

Controller config:
- File: `src/main/deploy/bringup_bindings.json` (controllers + bindings).
- Add more controllers by appending entries (currently Xbox only).
Binding config:
- File: `src/main/deploy/bringup_bindings.json`
- Controls button/axis to command mapping.

## Test Definitions (JSON)
Purpose: explain how bringup tests are defined and selected.

File: `src/main/deploy/bringup_tests.json`
Override:
- Set `"default_test_set"` inside `bringup_tests.json` to choose the active set.
- Optional: `--bringup-tests=...` loads an alternate JSON file.

Helper:
- `tools/bringup_test_wizard/run_bringup_test_wizard.bat` launches an interactive wizard to append a test entry.
- `tools/test_template_wizard/run_test_template_wizard.bat` copies a template set and prompts for motor/encoder IDs.

Each test entry includes:
- `type`: test type string (`composite` or `joystick`).
- `name`: display name used in console prints.
- `enabled`: whether the test is selectable and runnable.
- `motorKeys`: list of `VENDOR:TYPE:ID` for the device(s) under test.
- `duty`: motor command (-1.0..1.0).
- `rotation`: optional object with `limitRot`, `encoderKey` (`internal`, `through_bore`, or `VENDOR:TYPE:ID`),
  `encoderSource` (`internal`, `sparkmax_alt`, or `external`), `encoderCountsPerRev` (optional), and `encoderMotorIndex` (0-based).
- `time`: optional object with `timeoutSec` and `onTimeout` (`pass` or `fail`).
- `limitSwitch`: optional object with `enabled` and `onHit` (`pass` or `fail`).
- `hold`: optional object with `enabled` and `onRelease` (`pass` or `fail`).

Test set wrapper:
```json
{
  "default_test_set": "default",
  "test_sets": {
    "default": [ { "...": "..." } ],
    "smoke": [ { "...": "..." } ]
  }
}
```

Example (rotation + time + limit):
```json
{
  "type": "composite",
  "name": "NEO rotation + time + limit",
  "enabled": true,
  "motorKeys": ["REV:NEO:10"],
  "duty": 0.2,
  "rotation": { "limitRot": 2.0, "encoderKey": "internal", "encoderMotorIndex": 0 },
  "time": { "timeoutSec": 3.0, "onTimeout": "pass" },
  "limitSwitch": { "enabled": true, "onHit": "pass" }
}
```

Example (rotation only):
```json
{
  "type": "composite",
  "name": "CANCoder external 1 rotation",
  "enabled": true,
  "motorKeys": ["REV:NEO:10"],
  "duty": 0.2,
  "rotation": { "limitRot": 1.0, "encoderKey": "internal", "encoderMotorIndex": 0 }
}
```
Run:
- Secondary `LB`/`RB` select the test by name.
- Secondary `A` (hold) runs the selected test.

CTRE reference (external CAN encoder):
```json
{
  "type": "composite",
  "name": "CTRE rotation (CANCoder)",
  "enabled": true,
  "motorKeys": ["CTRE:FALCON:11"],
  "duty": 0.2,
  "rotation": { "limitRot": 1.0, "encoderKey": "CTRE:CANCoder:12", "encoderSource": "external", "encoderMotorIndex": 0 }
}
```
Run:
- Secondary `LB`/`RB` select the test by name.
- Secondary `A` (hold) runs the selected test.

Example (REV Through-Bore via SPARK MAX data port):
```json
{
  "type": "composite",
  "name": "Through-bore rotation (SparkMax)",
  "enabled": true,
  "motorKeys": ["REV:NEO:10"],
  "duty": 0.2,
  "rotation": {
    "limitRot": 5.0,
    "encoderKey": "through_bore",
    "encoderSource": "sparkmax_alt",
    "encoderCountsPerRev": 8192,
    "encoderMotorIndex": 0
  }
}
```
Run:
- Secondary `LB`/`RB` select the test by name.
- Secondary `A` (hold) runs the selected test.

Notes:
- While a test runs, joystick motor output is ignored for safety.
- Limit switch checks use limit switches configured in `bringup_profiles.json`.
- Hold checks use the current test-run button (secondary `A` in hold mode). Releasing it triggers the hold action.
- Using secondary `X` toggles a test enabled/disabled and persists it to `bringup_tests.json` (the active tests file).
- The former "nudge" action is now a time-only composite test; adjust `duty` and `time.timeoutSec`.

Additional composite examples (each is selectable/run the same way: secondary `LB`/`RB` to select, secondary `A` to run):

Rotation + time + limit:
```json
{
  "type": "composite",
  "name": "Rotation + time + limit",
  "enabled": true,
  "motorKeys": ["REV:NEO:10"],
  "duty": 0.2,
  "rotation": { "limitRot": 10.0, "encoderKey": "internal", "encoderMotorIndex": 0 },
  "time": { "timeoutSec": 2.0, "onTimeout": "fail" },
  "limitSwitch": { "enabled": true, "onHit": "pass" }
}
```

Hold to run:
```json
{
  "type": "composite",
  "name": "Hold to run",
  "enabled": true,
  "motorKeys": ["REV:NEO:10"],
  "duty": 0.2,
  "hold": { "enabled": true, "onRelease": "pass" }
}
```

All checks (rotation + time + limit + hold):
```json
{
  "type": "composite",
  "name": "All checks",
  "enabled": true,
  "motorKeys": ["REV:NEO:10"],
  "duty": 0.2,
  "rotation": { "limitRot": 8.0, "encoderKey": "internal", "encoderMotorIndex": 0 },
  "time": { "timeoutSec": 3.0, "onTimeout": "pass" },
  "limitSwitch": { "enabled": true, "onHit": "pass" },
  "hold": { "enabled": true, "onRelease": "pass" }
}
```

Example (time only):
```json
{
  "type": "composite",
  "name": "Spin motor for 1.5s",
  "enabled": true,
  "motorKeys": ["REV:NEO:10"],
  "duty": 0.2,
  "time": { "timeoutSec": 1.5, "onTimeout": "pass" }
}
```
Run:
- Secondary `LB`/`RB` select the test by name.
- Secondary `A` (hold) runs the selected test.

Example (joystick test):
```json
{
  "type": "joystick",
  "name": "Joystick motor (primary axis)",
  "enabled": true,
  "motorKeys": ["REV:NEO:10", "REV:NEO550:7"],
  "deadband": 0.12,
  "inputAxis": "primary"
}
```
Run:
- Secondary `LB`/`RB` select the test by name.
- Secondary `A` (hold) runs the selected test.
Control:
- Primary `Left Y` (primary axis) drives the joystick test output.

## Procedure A: Basic Bringup (Add + Health)
Purpose: verify the bus and devices before motion tests.

1. Press `Start` to add all configured devices.
2. Press `B` to print state and confirm devices are instantiated.
3. Press `D-pad Left` to print local health (faults, currents, temps).
4. If faults or missing devices appear, stop and fix wiring/config.

## Procedure B: Rotation Limit Test (Single)
Purpose: confirm encoder feedback and basic motion with a fixed rotation target.

1. Enable the desired test in `bringup_tests.json` (or use `--bringup-tests=...`) and deploy.
2. Press secondary `LB`/`RB` until the test name prints.
3. Press secondary `A` to run it.
4. Confirm the console shows PASS/FAIL and the reason.

## Procedure C: Rotation Limit Tests (Run All)
Purpose: execute multiple tests in a defined order.

1. Enable multiple tests in `bringup_tests.json` (or use `--bringup-tests=...`).
2. Press secondary `B` to run all enabled tests in order.
3. Watch for `Test result` lines after each test and `Run-all complete.` at the end.

## Procedure D: CANCoder Absolute Position Print
Purpose: verify absolute encoder reads without moving the robot.

1. Press `Right Bumper`.
2. Verify `absRot` and `absDeg` values print for each configured CANCoder.

## Procedure E: CAN Diagnostics Report
Purpose: cross-check local device health and CAN bus status.

1. Press `D-pad Up` for the CAN diagnostics report.
2. Check bus utilization, error counts, and device health rows.
3. If the PC tool is running, verify the PC tool section is present and healthy.

## Procedure F: NetworkTables Diagnostics (RobotV2)
Purpose: confirm the PC CAN tool is publishing to NetworkTables.

1. Run the PC tool on the Driver Station.
2. Press `D-pad Down` to print NetworkTables diagnostics.
3. Check for stale heartbeat, missing devices, or `openOk=NO`.

## Runtime Verification Checklist
Purpose: validate that the bringup test system and bindings behave correctly on real hardware.

- Confirm controller detection prints at startup (controller name and type).
- Press `B` to print state and verify devices are instantiated.
- Use secondary `LB`/`RB` to change the selected test and confirm the name updates.
- Run the selected test with secondary `A` and confirm PASS/FAIL and reason.
- Hold secondary `A` during a test that has `hold.enabled=true`; release to trigger the hold action.
- Press secondary `B` to run all enabled tests in order; verify `Run-all complete.` prints at the end.
- If a joystick test is enabled, confirm the listed `motorKeys` move together and stop when the test ends.
- If a rotation test uses `encoderKey: internal`, confirm it uses the motor index given by `encoderMotorIndex`.
- If a limit switch check is enabled, verify the test ends on switch activation and the result matches `onHit`.
- If the PC tool is running, press `D-pad Down` and confirm PC diagnostics show `openOk=YES`.

## Failure Interpretation
Purpose: define common outcomes and the next corrective action.

- `Timeout`: encoder not changing or motor not moving. Check wiring, CAN ID, and sensor source.
- `Encoder read failed`: wrong encoder config or device not present/instantiated.
- `Motor not found`: profile/test mismatch for vendor/type/id.

## Data Products
Purpose: record where test artifacts are produced.

- Console: pass/fail and status text.
- JSON report: `bringup_report.json` (when `X` is pressed).
- PCAP/PCAPNG: from the PC tool when enabled.

## Change Checklist
Purpose: keep test configuration and code in sync.

- Update `bringup_tests.json` when adding/removing tests (or your override file).
- Keep `bringup_profiles.json` aligned with device IDs in tests.
- Update this document when bindings or test types change.
