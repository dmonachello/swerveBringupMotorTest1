# Bringup Diagnostics System Test Plan

This document provides a step-by-step checklist to verify the complete bringup diagnostics system:
robot code, CAN sniffer tool, NetworkTables publishing, and config generation.

## Terminology
Purpose: prevent "active profile" confusion across host tools and robot runtime.

- Host context: the CLI/topology editor local editing/inspection selection (profiles/groups/tests on disk).
- Robot context: the roboRIO runtime selection used for actuation and tests (active profile, selected test).
- Rule: host context MUST NOT change robot context unless an explicit TCP robot command is executed (for example `profiles activate <name>`).

## Test Setup

Hardware:
- RoboRIO powered and reachable (USB or network).
- CAN bus wired with a PDP (minimum) and optional devices.
- Windows PC connected to RIO (USB or network).
- CANable Pro V2 connected to the CAN bus (CANH, CANL, GND) when using the PC sniffer.
- Xbox controllers are optional for boot, but required for full bringup workflows.

Bare minimum (robot-only bringup):
- RoboRIO + PDP on the CAN bus.
- No CANable required.

Usable minimum (robot + PC diagnostics):
- RoboRIO + PDP on the CAN bus.
- At least one motor controller (REV or CTRE) on the CAN bus.
- CANable Pro V2 connected for the PC sniffer and inventory tooling.
- Two Xbox controllers connected for full bringup/test workflows.

Software on Windows PC:
- Python 3.12 installed and reachable from the command line (`python` or `py`).
- Packages installed:
  - `pynetworktables`
  - `python-can`
  - `pyserial`
- Optional (for PDF/printing from the topology editor):
  - `reportlab`
- Recommended install helper:
  - `.\install_windows.cmd` (installs all Python dependencies).
- Driver Station installed and available to enable the robot.

Helpful tools:
- Device Manager to verify COM ports if auto-detect selects the wrong device.
- Driver Station USB tab to confirm which Xbox controller is controller0 vs controller1 (port 0 vs port 1).

## Weekly Regression Test Plan (RoboRIO + Xbox + Bridge UI + Bridge CLI)
Purpose: validate changes added this week from three perspectives (robot/Xbox, UI, CLI). Topology editor tests are deferred.

### A) RoboRIO + Xbox Controller Perspective
Purpose: validate robot-side behavior, controller bindings, safety guards, and test execution.

1. Boot + startup banner
   - Expected: bringup banner prints once; no command list spam.
   - Notes: screenshot shows banner printed once. Additional warnings observed: loop time overrun, failed to write `bringup_tests.json`, failed to persist enable state, periodic tracer output, and CAN error spike.
2. Disabled state guard
   - Expected: when the robot is not enabled, commands do nothing and no outputs change.
3. Enable robot in Driver Station
   - Expected: robot transitions to enabled state; commands are now allowed to execute.
   - Notes: console shows teleop init timing stats and the bringup banner with the active (inactive) profile summary.
4. Profile toggle (selection only)
   - Action: controller0 `Back` (edge).
   - Expected: profile name changes; no device instantiation; no CAN errors.
   - Notes: console shows repeated `=== Profile Updated ===` blocks cycling through profiles and ending back on `home_030226 (inactive)`.
5. Activate selected profile
   - Action: controller0 `Start` (edge) to add all devices.
   - Expected: devices created once; no duplicate device errors.
   - Notes: `addAll` printed bringup reset, created NEO 25, NEO 550 7, FALCON 9, then printed `Added all configured devices` and the profile summary.
6. Print state
	   - Action: controller0 `B` (edge).
	   - Expected: state shows robot active profile name and expected devices.
   - Notes: examples below assume the selected profile is `home_030226`.
   - Example output:
     `=== Bringup State ===`
     `Build: bringup-core-state-v3`
     `CAN profile: home_030226`
     `NEO:`
     `index 0 CAN 25 ACTIVE`
     `NEO 550:`
     `index 0 CAN 7 ACTIVE`
     `FALCON:`
     `index 0 CAN 9 ACTIVE`
     `Next add will be: REV motor`
     `Virtual devices:`
     `roboRIO CAN 0 PRESENT (no local API)`
     `=====================`
7. Next/prev test selection
   - Action: controller1 `LB`/`RB`.
   - Expected: selected test name updates; no errors.
8. Button binding visibility
   - Action: `printTestsOverview` (controller1 `LS` or UI).
   - Expected: output lists bound button (e.g., `controller1 A (hold)`) for hold-to-run tests.
   - Example output:
     `=== Bringup Tests ===`
     `Active set: default (default: default)`
     `Total: 10 Enabled: 0`
     `Idx Sel En Type Name HoldBtn Motors`
     `0 N composite Rotation only (internal) - SPARKMAX/NEO 25`
     `1 N deadbandSweep Deadband sweep (internal) - SPARKMAX/NEO 25`
     `2 N composite Rotation + Time (t=2.00s) - FALCON 9`
     `3 N composite Time only (t=1.50s) - SPARKMAX/NEO550 7`
     `4 N composite Nudge (0.2 for 0.5s) (t=0.50s) - SPARKMAX/NEO 25`
     `5 N composite Limit switch only - SPARKMAX/NEO550 7`
     `6 N composite Hold to run (unbound) FALCON 9`
     `7 N composite Rotation + Time + Limit (t=2.00s) - SPARKMAX/NEO550 7, SPARKMAX/NEO 25, FALCON 9`
     `8 N composite All checks (t=3.00s) (unbound) SPARKMAX/NEO550 7`
     `9 * N joystick Joystick motor (controller0.leftY) - SPARKMAX/NEO 25, FALCON 9`
     `=====================`
9. Safety latch: disable/enable
   - Action: DS disable/enable.
   - Expected: active test stops on disable; no motors move on enable unless a test is explicitly started.
10. Stop latch behavior
   - Trigger: force a TCP timeout (stop UI keepalive) or explicit TCP stop.
   - Expected: latch blocks tests; Xbox clear latch command works; message indicates how to clear.
11. Run selected test (hold) - disabled case
   - Action: controller1 `A` (hold).
   - Expected: test does not run if disabled.
   - Example output:
     `Command: runTest`
     `Test disabled: Rotation only (internal)`
12. Enable the test
   - Action: controller1 `X` (edge) to toggle enabled on the selected test.
   - Expected: test is now enabled and will run.
   - Example output:
     `=== Bringup Tests ===`
     `Active set: default (default: default)`
     `Total: 10 Enabled: 1`
     `Idx Sel En Type Name HoldBtn Motors`
     `0 * Y composite Rotation only (internal) - SPARKMAX/NEO 25`
     `1 N deadbandSweep Deadband sweep (internal) - SPARKMAX/NEO 25`
     `2 N composite Rotation + Time (t=2.00s) - FALCON 9`
     `3 N composite Time only (t=1.50s) - SPARKMAX/NEO550 7`
     `4 N composite Nudge (0.2 for 0.5s) (t=0.50s) - SPARKMAX/NEO 25`
     `5 N composite Limit switch only - SPARKMAX/NEO550 7`
     `6 N composite Hold to run (unbound) FALCON 9`
     `7 N composite Rotation + Time + Limit (t=2.00s) - SPARKMAX/NEO550 7, SPARKMAX/NEO 25, FALCON 9`
     `8 N composite All checks (t=3.00s) (unbound) SPARKMAX/NEO550 7`
     `9 N joystick Joystick motor (controller0.leftY) - SPARKMAX/NEO 25, FALCON 9`
     `=====================`
13. Run selected test (hold)
   - Action: controller1 `A` (hold).
   - Expected: console prints `Command: runTest`, `Test started #N`, `Test #N`, `Test result #N ... time=...`.
   - Example output (three runs):
     `Test started #1: Rotation only (internal)`
     `Test #1: Rotation only (internal)`
     `Test result #1: Rotation only (internal) = PASS (Reached rotation limit (NEO CAN 25)) time=0.16s`
     `[Spark Max] IDs: 25, timed out while waiting for Period Status 2: HAL: CAN Receive has Timed Out`
     `Command: runTest`
     `Test started #2: Rotation only (internal)`
     `Test #2: Rotation only (internal)`
     `Test result #2: Rotation only (internal) = PASS (Reached rotation limit (NEO CAN 25)) time=0.90s`
     `Command: runTest`
     `Test started #3: Rotation only (internal)`
     `Test #3: Rotation only (internal)`
     `Test result #3: Rotation only (internal) = PASS (Reached rotation limit (NEO CAN 25)) time=0.90s`
14. Run-all tests (multiple enabled)
   - Action: enable 2-3 tests first:
     - Use controller1 `LB`/`RB` to select a test.
     - Press controller1 `X` (edge) to toggle it enabled.
     - Repeat for two more tests.
   - Then press controller1 `B` (edge).
   - Expected: run-all proceeds through enabled tests; prints results with test numbers.
   - Example output:
     `Idx Sel En Type Name HoldBtn Motors`
     `0 Y composite Rotation only (internal) - SPARKMAX/NEO 25`
     `1 N deadbandSweep Deadband sweep (internal) - SPARKMAX/NEO 25`
     `2 Y composite Rotation + Time (t=2.00s) - FALCON 9`
     `3 * Y composite Time only (t=1.50s) - SPARKMAX/NEO550 7`
     `4 N composite Nudge (0.2 for 0.5s) (t=0.50s) - SPARKMAX/NEO 25`
     `5 N composite Limit switch only - SPARKMAX/NEO550 7`
     `6 N composite Hold to run (unbound) FALCON 9`
     `7 N composite Rotation + Time + Limit (t=2.00s) - SPARKMAX/NEO550 7, SPARKMAX/NEO 25, FALCON 9`
     `8 N composite All checks (t=3.00s) (unbound) SPARKMAX/NEO550 7`
     `9 N joystick Joystick motor (controller0.leftY) - SPARKMAX/NEO 25, FALCON 9`
     `=====================`
     `Command: runAllTests`
     `Test started #5: Time only`
     `Test #5: Time only`
     `Test result #5: Time only = PASS (Time limit reached) time=1.52s`
     `Test started #6: Rotation only (internal)`
     `Test #6: Rotation only (internal)`
     `Test result #6: Rotation only (internal) = PASS (Reached rotation limit (NEO CAN 25)) time=0.90s`
     `Test #7: Rotation + Time`
     `Test result #7: Rotation + Time = PASS (Reached rotation limit (FALCON CAN 9)) time=1.66s`
     `Run-all complete.`

### B) Bridge UI Perspective
Purpose: validate UI command routing, output mirroring, keepalive, and profile selection.

1. UI connection + handshake
   - Start UI and connect to the robot.
   - Expected: handshake OK, no repeated handshake spam.
2. Keepalive requirement
   - Leave UI running for >10s.
   - Expected: no TCP timeout stop latch triggered; outputs not spammed.
3. Output mirroring
   - Run `printState`, `printProfileDevices`, `printCANdiag`, `canSweep`, and `runTest`.
   - Expected: all console output also appears in UI Output panel without duplicates.
4. Run selected test from UI
   - Action: click `Run Selected`.
   - Expected: Output panel includes: `Command: runTest (UI)`, `Test started #N`, `Test #N`, `Test result #N ... time=...`.
5. Stop latch message visibility
   - Trigger stop latch then run a test.
   - Expected: UI shows error message explaining latch and how to clear.
6. Profile selection in UI
   - Choose profile from dropdown and run `Add All`.
   - Expected: robot adds devices from the selected profile (not a stale one).
7. Profile devices report
   - Action: click `Profile Devices`.
   - Expected: output shows correct profile name and device list.
8. Next test info
   - Action: click `Print Next`.
   - Expected: output shows selected test details including rotation/time/limit blocks.

### C) Bridge CLI Perspective
Purpose: validate test authoring via CLI, grammar support, and JSON output.

1. CLI parser compatibility
   - Commands: `configure terminal`, `test set default`, `test create MyTest1`.
   - Expected: no parse errors; prompt changes to `bridge(config-test-MyTest1)#`.
   - Notes: `conf t` is not accepted; use `configure terminal` to enter config mode.
   - Notes: `test create MyTest1` enters test mode. While already in `bridge(config-test-MyTest1)#`, the `test MyTest1` command is rejected; stay in test mode and continue with `type`, `device`, etc.
   - Notes: `test set <name>` selects the set and creates it if it does not exist.
2. Joystick test authoring
   - Commands:
     - `type joystick`
     - `device add SPARKMAX/NEO 25`
     - `inputSource controller0.leftY`
     - `deadband 0.12`
     - `show`
   - Expected: show output matches settings.
   - Notes: device label must match a profile label (for example `SPARKMAX/NEO 25`).
   - Example output:
     `Test: MyTest1`
     `  type: joystick`
     `  enabled: False`
     `  devices: SPARKMAX/NEO 25`
     `  inputSource: controller0.leftY`
     `  deadband: 0.12`
   - Exit: `end` returns to `bridge(config)#`.
   - Example output (post-exit):
     `bridge(config)# show tests`
     `Active test set: default`
     `- Rotation only (internal) (button) devices=1 enabled=False`
     `- Deadband sweep (internal) (button) devices=1 enabled=False`
     `- Rotation + Time (button) devices=1 enabled=False`
     `- Time only (button) devices=1 enabled=False`
     `- Nudge (0.2 for 0.5s) (button) devices=1 enabled=False`
     `- Limit switch only (button) devices=1 enabled=False`
     `- Hold to run (button) devices=1 enabled=False`
     `- Rotation + Time + Limit (button) devices=3 enabled=False`
     `- All checks (button) devices=1 enabled=False`
     `- Joystick motor (controller0.leftY) (joystick) devices=2 enabled=False`
     `- MyTest1 (joystick) devices=1 enabled=False`
     `bridge(config)# show test MyTest1`
     `Test: MyTest1`
     `  type: joystick`
     `  enabled: False`
     `  devices: SPARKMAX/NEO 25`
     `  inputSource: controller0.leftY`
     `  deadband: 0.12`
3. Button test authoring
   - Commands:
     - `type button`
     - `device add FALCON 9`
     - `inputSource controller1.A`
     - `duty 0.2`
     - `termination hold`
     - `termination time 2.0`
     - `show`
   - Expected: show output includes button binding and termination fields.
4. Validation errors
   - Commands: set `deadband 1.5`, `duty 2.0`, or invalid device label.
   - Expected: CLI rejects invalid values with clear error.
5. Save tests
   - Command: `write tests bringup_tests.json`
   - Expected: file written; schema remains compatible.
6. Backward compatibility
   - After save, deploy and run tests on robot.
   - Expected: robot loads tests normally and runs without schema errors.

## Fast Test Plan
Purpose: the fast test plan confirms minimum health checks for the system.

1. Deploy robot code and enter teleop.
2. Confirm controller detection prints at startup (controller name and type).
3. Scroll through available test configs to choose the desired test config.
4. Controller0: press `Start` to add all configured devices.
5. Controller0: press `B` to print state and confirm devices are present.
6. Controller0: move `Left Y`/`Right Y` to run connected motors, then press `D-pad Right` to confirm inputs.
7. Start the PC tool (default test profile):
   - `%USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --profile example_default --rio 172.22.11.2`
8. Use the smoke test set:
   - In `src/main/deploy/bringup_tests.json`, set `"default_test_set": "smoke"` and deploy.
   - Scroll through tests with the controller1 (`LB`/`RB`).
   - Select which tests run by toggling enable on the controller1 (`X`) while the test is highlighted.
9. Controller0: press `D-pad Down` and confirm `openOk=YES` (PC tool has an active CAN interface and is publishing). Verify the table includes `conf`, `score`, `warn`, `err`, and `fatal` columns and uses dot-padded right-justified formatting.
10. Controller1: press `LB`/`RB` to select a test and confirm the name updates.
11. Controller1: run one enabled test with `A` and confirm PASS/FAIL prints.
12. Controller1: hold `A` during a test with `hold.enabled=true`, then release to confirm the hold termination path.
13. Controller1: press `B` to run all enabled tests and confirm `Run-all complete.` prints.
14. If a joystick test is enabled, confirm its `motorLabels` move together and stop when the test ends.
15. If a rotation test uses `encoderKey: internal`, confirm it uses `encoderMotorIndex`.
16. If a limit switch check is enabled, verify it terminates on switch activation.
17. If Wireshark is needed, run a quick capture and confirm frames appear.
18. Inventory + config generation (quick check):
    - `--profileName` is the label stored in the config metadata (it should match your bringup profile name).
    
    - `%USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --profile example_default --rio 172.22.11.2 --dump-api-inventory tools\can_nt\inv_fast.json --dump-api-inventory-after 5`
    - `%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_inventory\can_inventory.py --generate --input tools\can_nt\inv_fast.json --output tools\can_nt\robot_config_fast.json --profileName example_default`
    - `%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_inventory\can_inventory.py --validate --input tools\can_nt\robot_config_fast.json --inventory tools\can_nt\inv_fast.json`

## Complete Test Plan
Purpose: the complete test plan verifies major robot and PC tool functionality after large changes.

### Safety (Client/Server)
Purpose: verify TCP safety stop, stop latch, and Xbox priority behavior.

1. TCP timeout safe stop: start a test from the Bringup Control UI or CLI, kill the UI process or unplug the PC network, expect the robot to stop within ~1s with the stop latch set and TCP start commands rejected.
2. TCP stop latch set (command-driven): use a TCP stop command (for example `groupDisable` or `selectedModeSet enabled=false`), expect the stop latch to set and outputs to stop.
3. UI keepalive required: start the UI and confirm it sends `uiPing` every 1s; stop the UI and verify the TCP session is closed after 5 missed keepalives.
4. Xbox clears latch: with latch active, press Xbox `A`/`B` to run a test, expect the latch to clear and the Xbox test to start.
5. UI clears latch: with latch active, press the UI **Clear Stop Latch** button, then re-run the test from the UI.
6. Xbox disconnect: with Xbox connected, start any test and unplug the controller USB, expect an immediate stop with the latch set.
7. Driver Station override: while clients are active, disable the robot or E-stop from Driver Station, expect the robot to remain stopped regardless of TCP/Xbox commands.

### Profiles (Required Setup)
Purpose: profiles match the hardware under test to avoid false diagnostics.

1. Confirm `data/bringup_system.json` matches the CAN IDs on the bus.
2. If you need a new profile:
   - Start from `src/main/deploy/bringup_system.template.json`.
   - Add a new profile entry with unique name and device IDs.
   - Set `default_profile` to the profile you want at startup.
   - Deploy to the roboRIO.
Notes:
- Profiles are deployed with robot code; edits require redeploy.
- Devices become active only when explicitly added (single or add-all).

### Profiles Using CAN Topology Editor
Purpose: generate or edit profiles with the topology editor before testing.

1. Launch the editor:
   - `python tools\can_topology\can_top_editor.py`
2. Load an existing profile or create a new diagram.
3. Add/edit nodes and callouts to match the physical CAN bus.
4. Save the diagram to the active profile (host/editor context).
5. Use **Save to Deploy** to append/replace the profile in `data/bringup_system.json` (syncs to deploy).
6. If needed, check **Set As Default** so the new profile is selected on startup.
7. Deploy robot code so the updated profile is on the roboRIO.

### UI Profile Selection
Purpose: verify UI profile selection and activation behavior.

1. In the UI, pick a profile from the dropdown.
2. Confirm the UI sends `selectProfile` and the robot acknowledges the selection.
3. Run **Add Motor** or **Add All** and confirm devices are added from the selected profile.
4. If a different profile is active on the robot, re-select in the UI and retry.

### Build and Deploy
Purpose: builds and deploys succeed before hardware testing begins.

1. Open the project in VS Code with the WPILib extension installed.
2. Build robot code:
   - Use **WPILib: Build Robot Code** from the command palette.
3. Deploy robot code to the RoboRIO:
   - Use **WPILib: Deploy Robot Code** from the command palette.
Expected:
- Build completes with no errors.
- Deploy reports success and robot code starts.

### A) Robot Bringup Core
Purpose: base robot bringup actions still work under teleop.

1. Deploy robot code and enter teleop.
2. Profile toggle (cycle):
   - Action: Press `Back`.
   - Expected: Profile name changes; the known device list updates.
3. Controller0: press `Start` to add all configured devices.
4. Controller0: press `B` to print state.
Expected:
- All configured devices show `present=YES`.
- No exceptions or missing device errors.

### A1) Device Health Output (Example)
Purpose: provide a reference for expected device health formatting.

Simulated example (based on `robot_test1` profile):
```text
Device Health (local API):
  NEO CAN 51: present=YES faults=0x0 warnings=0x0 sticky=0x0 stickyWarn=0x0 lastErr=OK reset=NO specFree=1.3A specStall=105A freeRatio=0.46x busV=12.32V appliedV=5.90V motorCurrentA=0.60A tempC=31.9C
  NEO CAN 11: present=YES faults=0x0 warnings=0x0 sticky=0x0 stickyWarn=0x0 lastErr=OK reset=NO specFree=1.3A specStall=105A freeRatio=0.55x busV=12.30V appliedV=6.10V motorCurrentA=0.72A tempC=33.2C
  NEO CAN 21: present=YES faults=0x0 warnings=0x0 sticky=0x0 stickyWarn=0x0 lastErr=OK reset=NO specFree=1.3A specStall=105A freeRatio=0.41x busV=12.29V appliedV=5.60V motorCurrentA=0.53A tempC=32.1C
  NEO CAN 31: present=YES faults=0x0 warnings=0x0 sticky=0x0 stickyWarn=0x0 lastErr=OK reset=NO specFree=1.3A specStall=105A freeRatio=0.49x busV=12.28V appliedV=5.80V motorCurrentA=0.63A tempC=32.8C
  NEO CAN 41: present=YES faults=0x0 warnings=0x0 sticky=0x0 stickyWarn=0x0 lastErr=OK reset=NO specFree=1.3A specStall=105A freeRatio=0.52x busV=12.27V appliedV=6.00V motorCurrentA=0.68A tempC=34.0C

  KRAKEN CAN 12: present=YES fault=0x0 sticky=0x0 lastErr=OK specFree=2.0A specStall=105A freeRatio=0.48x busV=12.31V appliedDuty=0.45dc appliedV=5.60V motorCurrentA=0.96A tempC=35.2C
  KRAKEN CAN 22: present=YES fault=0x0 sticky=0x0 lastErr=OK specFree=2.0A specStall=105A freeRatio=0.51x busV=12.30V appliedDuty=0.47dc appliedV=5.75V motorCurrentA=1.02A tempC=36.1C
  KRAKEN CAN 32: present=YES fault=0x0 sticky=0x0 lastErr=OK specFree=2.0A specStall=105A freeRatio=0.46x busV=12.29V appliedDuty=0.43dc appliedV=5.40V motorCurrentA=0.92A tempC=34.8C
  KRAKEN CAN 42: present=YES fault=0x0 sticky=0x0 lastErr=OK specFree=2.0A specStall=105A freeRatio=0.50x busV=12.28V appliedDuty=0.46dc appliedV=5.70V motorCurrentA=1.00A tempC=35.6C

  CANCoder CAN 13: present=YES absDeg=182.4 lastErr=OK
  CANCoder CAN 23: present=YES absDeg=91.7 lastErr=OK
  CANCoder CAN 33: present=YES absDeg=275.0 lastErr=OK
  CANCoder CAN 43: present=YES absDeg=44.2 lastErr=OK

  CANdle CAN 2: present=YES

  PDH CAN 1: present=YES voltage=12.38V totalCurrent=64.27A switchable=ON tempC=33.4
    Faults: brownout=NO canWarn=NO hwFault=NO
    Sticky: brownout=NO canWarn=NO busOff=NO hasReset=NO
    Ch 00 current=  1.25A activeFault=NO stickyFault=NO status=OK
    Ch 01 current=  0.00A activeFault=NO stickyFault=NO status=OK
    Ch 02 current=  3.42A activeFault=NO stickyFault=NO status=OK
    Ch 03 current= 12.10A activeFault=NO stickyFault=NO status=OK
    ...

  roboRIO CAN 0: present=YES (virtual, no API)
```

### B) Controller + Bindings (Config-Driven)
Purpose: command bindings resolve from JSON and edge/hold behavior is correct.

Config excerpt (bindings + controllers):
```json
// src/main/deploy/bringup_bindings.json
{
  "controllers": [
    { "type": "XBOX", "port": 0, "name": "controller0" },
    { "type": "XBOX", "port": 1, "name": "controller1" }
  ],
  "bindings": [
    { "command": "addMotor", "controller": "controller0", "input": "button", "id": "A", "mode": "edge" },
    { "command": "addAll", "controller": "controller0", "input": "button", "id": "START", "mode": "edge" },
    { "command": "printState", "controller": "controller0", "input": "button", "id": "B", "mode": "edge" },
    { "command": "printBindings", "controller": "controller0", "input": "button", "id": "LB", "mode": "edge" },
    { "command": "selectTestPrev", "controller": "controller1", "input": "button", "id": "LB", "mode": "edge" },
    { "command": "selectTestNext", "controller": "controller1", "input": "button", "id": "RB", "mode": "edge" },
    { "command": "runTest", "controller": "controller1", "input": "button", "id": "A", "mode": "hold" },
    { "command": "runAllTests", "controller": "controller1", "input": "button", "id": "B", "mode": "edge" }
  ],
  "axes": [
    { "command": "leftDrive", "controller": "controller0", "id": "leftY", "invert": true, "deadband": 0.12 },
    { "command": "rightDrive", "controller": "controller0", "id": "rightY", "invert": true, "deadband": 0.12 }
  ]
}
```

1. Controller0: confirm startup prints the bindings list, then press `LB` to reprint.
2. Controller0: press `A`, `Start`, `B`, `X`, `Y`, `Back`.
3. Controller1: press `LB`, `RB`, `A`, `B`, `X`, `D-pad` (any direction).
Expected:
- Each command prints the expected action.
- No missing/unknown command warnings.

### C) Speed Inputs
Purpose: axis inputs map to left/right drive commands as configured.

Config excerpt (axis bindings):
```json
// src/main/deploy/bringup_bindings.json
{
  "axes": [
    { "command": "leftDrive", "controller": "controller0", "id": "leftY", "invert": true, "deadband": 0.12 },
    { "command": "rightDrive", "controller": "controller0", "id": "rightY", "invert": true, "deadband": 0.12 }
  ]
}
```

1. Controller0: move `Left Y` and `Right Y`.
2. Controller0: press `D-pad Right` to print inputs.
Expected:
- Values match stick movement and deadband/invert settings.

### D) Joystick Motor Control (Non-Test Mode)
Purpose: joystick-driven motor output still works outside tests.

Config excerpt (motors in the robot active profile):
```json
// data/bringup_system.json
{
  "default_profile": "example_default",
  "profiles": {
    "example_default": {
      "neos": [
        { "label": "SPARKMAX 10", "id": 10 },
        { "label": "SPARKMAX 25", "id": 25 }
      ],
      "roborio": { "label": "roboRIO", "id": 0 }
    }
  }
}
```

1. Controller0: add one REV motor and one CTRE motor.
2. Controller0: move `Left Y` and `Right Y`.
Expected:
- Motors respond to their respective axes.
- Output stops when stick returns to center.

### E) Bringup Test Selection + Run
Purpose: test selection, run, and run-all behave correctly.

Existing tests in the active test set (`default_test_set` in `bringup_tests.json`, or in the override file):
- Rotation only (internal)
- Rotation + Time
- Time only
- Nudge (0.2 for 0.5s)
- Limit switch only
- Hold to run
- Rotation + Time + Limit
- All checks
- Joystick motor (controller0.leftY)

Test bindings (controller1):
- `LB` / `RB`: select previous/next test
- `A` (hold): run selected test / hold signal
- `B`: run all enabled tests
- `X`: toggle selected test enabled

Example configs (match the test titles above):
- See sections F-I for per-test JSON examples and run sequences.

Steps:
1. Enable 2+ tests in `bringup_tests.json` (or the active override), deploy.
2. Controller1: press `LB`/`RB` to cycle tests.
3. Controller1: press `A` to run the selected test.
4. Controller1: press `B` to run all enabled tests.
Expected:
- Test names print on selection.
- PASS/FAIL prints after each run.
- Run-all prints `Run-all complete.`.

### F) Composite Test Checks
Purpose: rotation/time/limit/hold checks work independently and combined.

Rotation only (internal):
```json
{
  "type": "composite",
  "name": "Rotation only (internal)",
  "enabled": true,
  "motorLabels": ["SPARKMAX/NEO 10"],
  "duty": 0.2,
  "rotation": { "limitRot": 5.0, "encoderKey": "internal", "encoderMotorIndex": 0 }
}
```
Run: controller1 `LB`/`RB` select, controller1 `A` (hold) run.

Time only:
```json
{
  "type": "composite",
  "name": "Time only",
  "enabled": true,
  "motorLabels": ["SPARKMAX/NEO 10"],
  "duty": 0.3,
  "time": { "timeoutSec": 1.5, "onTimeout": "pass" }
}
```
Run: controller1 `LB`/`RB` select, controller1 `A` (hold) run.

Limit switch only:
```json
{
  "type": "composite",
  "name": "Limit switch only",
  "enabled": true,
  "motorLabels": ["SPARKMAX/NEO 10"],
  "duty": 0.2,
  "limitSwitch": { "enabled": true, "onHit": "pass" }
}
```
Run: controller1 `LB`/`RB` select, controller1 `A` (hold) run.

Hold to run:
```json
{
  "type": "composite",
  "name": "Hold to run",
  "enabled": true,
  "motorLabels": ["SPARKMAX/NEO 10"],
  "duty": 0.2,
  "hold": { "enabled": true, "onRelease": "pass" }
}
```
Run: controller1 `LB`/`RB` select, controller1 `A` (hold) run.

Combined (rotation + time + limit + hold):
```json
{
  "type": "composite",
  "name": "All checks",
  "enabled": true,
  "motorLabels": ["SPARKMAX/NEO 10"],
  "duty": 0.2,
  "rotation": { "limitRot": 8.0, "encoderKey": "internal", "encoderMotorIndex": 0 },
  "time": { "timeoutSec": 3.0, "onTimeout": "pass" },
  "limitSwitch": { "enabled": true, "onHit": "pass" },
  "hold": { "enabled": true, "onRelease": "pass" }
}
```
Run: controller1 `LB`/`RB` select, controller1 `A` (hold) run.
Expected:
- Each check terminates the test per its condition.
- Combined test stops on the first triggered condition.

### G) External Encoder Tests
Purpose: external encoders are selected correctly via `encoderKey`.

CTRE reference (external CAN encoder):
```json
{
  "type": "composite",
  "name": "CTRE rotation (CANCoder)",
  "enabled": true,
  "motorLabels": ["FALCON 11"],
  "duty": 0.2,
  "rotation": { "limitRot": 5.0, "encoderKey": "CANCoder 12", "encoderSource": "external", "encoderMotorIndex": 0 }
}
```
Run: controller1 `LB`/`RB` select, controller1 `A` (hold) run.

REV Through-Bore via SPARK MAX data port:
```json
{
  "type": "composite",
  "name": "Through-bore rotation (SparkMax)",
  "enabled": true,
  "motorLabels": ["SPARKMAX/NEO 10"],
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
Run: controller1 `LB`/`RB` select, controller1 `A` (hold) run.
Expected:
- Encoder output changes and test terminates at `limitRot`.

### H) Multi-Motor Tests
Purpose: `motorLabels` drives multiple motors together.

Joystick motor (controller0.leftY):
```json
{
  "type": "joystick",
  "name": "Joystick motor (controller0.leftY)",
  "enabled": true,
  "motorLabels": ["SPARKMAX/NEO 10", "SPARKMAX/NEO550 7"],
  "deadband": 0.12,
  "inputSource": "controller0.leftY"
}
```
Run: controller1 `LB`/`RB` select, controller1 `A` (hold) run. Control: controller0 `Left Y`.
Expected:
- All motors respond together; stop together on test end.

### I) Limit Switch Integration
Purpose: limit switches clamp motion and terminate tests as configured.

Limit switch test:
```json
{
  "type": "composite",
  "name": "Limit switch only",
  "enabled": true,
  "motorLabels": ["SPARKMAX/NEO 10"],
  "duty": 0.2,
  "limitSwitch": { "enabled": true, "onHit": "pass" }
}
```
Run: controller1 `LB`/`RB` select, controller1 `A` (hold) run.

Steps:
1. Configure `limits` for a motor in `bringup_system.json`.
2. Run the test above with `limitSwitch.enabled=true`.
Expected:
- Motor output clamps on closed limit.
- Test ends and reports PASS/FAIL per `onHit`.
- The check triggers when any selected motor reports a closed forward or reverse limit.

### J) PC CAN Tool - Basic
Purpose: the PC sniffer runs and publishes NetworkTables diagnostics.

1. Run the PC tool:
   - `%USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --profile <profile> --rio 172.22.11.2`
2. Controller0: press `D-pad Down`.
Expected:
- `openOk=YES`, heartbeat updates, and device table matches CAN traffic.
- Device table columns include `conf`, `score`, `warn`, `err`, and `fatal` with dot-padded right-justified formatting.

### K) PC CAN Tool - Wireshark
Purpose: live pipe and file captures produce valid PCAP/PCAPNG.

1. Live pipe: start Wireshark `-k -i \\.\pipe\FRC_CAN`.
2. Run the tool with `--pcap-pipe FRC_CAN`:
   - `%USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --profile <profile> --rio 172.22.11.2 --pcap-pipe FRC_CAN`
3. File: run `--pcap tools\can_nt\logs\run.pcapng`:
   - `%USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --profile <profile> --rio 172.22.11.2 --pcap tools\can_nt\logs\run.pcapng`
Expected:
- Wireshark shows live frames via pipe.
- PCAPNG opens and decodes.

### L) PC CAN Tool - Inventory + Diff
Purpose: inventory capture and diff outputs are correct.

1. Run:
   - `%USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --profile <profile> --rio 172.22.11.2 --dump-api-inventory tools\can_nt\inv_a.json --dump-api-inventory-after 5`
2. Run again after a different stimulus into `inv_b.json`.
3. Run:
   - `%USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --diff-inventory tools\can_nt\inv_a.json tools\can_nt\inv_b.json`
Expected:
- Inventory files are created.
- Diff prints new/missing pairs and rate deltas.

### M) Config Generator + Validator
Purpose: config generation, validation, and hash update workflow is correct.

1. Capture inventory:
   - `%USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --profile <profile> --rio 172.22.11.2 --dump-api-inventory tools\can_nt\inv_gen.json --dump-api-inventory-after 5`
2. Generate config:
   - `%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_inventory\can_inventory.py --generate --input tools\can_nt\inv_gen.json --output tools\can_nt\robot_config.json --profileName <profile>`
3. Validate config against the inventory:
   - `%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_inventory\can_inventory.py --validate --input tools\can_nt\robot_config.json --inventory tools\can_nt\inv_gen.json`
4. Edit the config and leave one placeholder name or a missing required parameter to trigger errors.
5. Validate again and confirm errors are reported.
6. Update hash after manual review:
   - `%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_inventory\can_inventory.py --validate --input tools\can_nt\robot_config.json --inventory tools\can_nt\inv_gen.json --update-hash`
Expected:
- Generated device names use the device label from the inventory.
- Validation fails on placeholder names or missing required parameters.
- Hash update rewrites `metadata.inventory_hash` and `metadata.inventory_source`.

### N) PC Tool Config Auto-Gen
Purpose: can_nt_config.json generation matches the selected `--profile` argument.

1. Run:
   - `%USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --profile <profile> --dump-can-config tools\can_nt\can_nt_config.json`
Expected:
- File is created and lists devices matching the selected profile.

## Dashboard (Realtime - Implement Later)
Purpose: dashboard runtime info is defined for future display.

- PC tool status: `openOk`, `heartbeat`, `framesPerSec`, `lastFrameAgeSec`
- CAN summary: `bringup/diag/can/summary/json`
- Missing devices count (PC tool)
- Selected test name + enabled state
- Active test status (RUNNING/PASS/FAIL + reason)
- Local device health rollup (fault/warn counts)

## Preflight Checklist

1. Confirm RIO is powered and reachable.
2. Confirm CANable is detected in Device Manager under **Ports (COM & LPT)**.
3. Confirm the CAN bus has at least one active device sending frames.

## Commands Used (CMD)

Default run:
```cmd
%USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --rio 172.22.11.2
```

Verbose + summary:
```cmd
%USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --rio 172.22.11.2 --print-summary-period 2 --print-publish --verbose
```

Quick check:
```cmd
%USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --rio 172.22.11.2 --quick-check
```

CSV logging:
```cmd
%USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --rio 172.22.11.2 --log-csv tools\can_nt\can_nt_log.csv
```

List ports:
```cmd
%USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --list-ports
```

## Functional Tests

### 1) Auto-detect COM port
Steps:
1. Unplug all USB serial devices except the CANable.
2. Run the default command (no `--channel`).
Expected:
- Startup banner shows `Auto-detected CAN channel: COMx (...)`.
- `CAN: interface=slcan channel=COMx bitrate=1000000` shows the same COM port.

Failure hints:
- If multiple ports match, script should prompt for selection.
- If none match, script should exit with a clear error.

### 2) RIO connection diagnostics
Steps:
1. Run the default command with the RIO connected.
Expected:
- Startup shows `RIO IP: ...` and `NT status: connected to RIO`.
- `NT details:` prints remote/connection info.

Negative test:
1. Disconnect RIO or use a bad `--rio`.
Expected:
- `NT status: NOT connected to RIO`.
- Periodic warning: `Not connected to RIO NetworkTables as of HH:MM:SS.`

### 3) No CAN traffic warning
Steps:
1. Run the tool with CANable connected but CAN bus powered off.
Expected:
- Periodic warning: `No CAN traffic detected as of HH:MM:SS.`

### 4) Device labels and status
Steps:
1. Ensure the CAN bus contains devices with labels defined in the selected bringup profile.
2. Run with summaries enabled.
Expected:
- Each device prints its label (e.g., `FR NEO`, `FL KRAK`, `FR CANC`).
- `status` is `OK` when active; `STALE` after timeout; `MISSING` if never seen.

### 5) `--print-publish` behavior
Steps:
1. Run with `--print-publish`.
2. Power-cycle one CAN device so it drops off the bus and returns.
Expected:
- When it returns after timeout, a line prints:
  `Device seen: label=<LABEL> count=NN`

### 6) Summary output formatting
Steps:
1. Run with `--print-summary-period 2`.
Expected:
- Multi-line summary appears every 2 seconds.
- Contains `Pit check` line with seen/missing count, frames/sec, errors/sec.
- Includes group lines if groups are configured.

### 7) Groups rollup
Steps:
1. Check the selected bringup profile device groups or group defaults.
2. Run with summary enabled.
Expected:
- Lines like `Group neos: seen=4/4 missing=0`.
- Counts should change as devices drop out or reappear.

### 8) NetworkTables keys
Steps:
1. Run tool and view NT values (e.g., NT client or RobotV2 Y button).
Expected keys under `bringup/diag`:
- `busErrorCount`
- `dev/<labelKey>/label`
- `dev/<labelKey>/status`
- `dev/<labelKey>/ageSec`
- `dev/<labelKey>/msgCount`
- `dev/<labelKey>/lastSeen`
RobotV2 uses the composite `dev/<labelKey>` keys.

### 8a) NT Contract Sanity (Robot <-> PC)
Purpose: RobotV2 consumes bringup/diag keys without missing data.

1. Run the PC tool with NT publishing enabled.
2. On the robot, trigger the diagnostics print (`printNTdiag` binding).
Expected:
- The diagnostics report prints without key-not-found errors.
- The PC tool status block shows heartbeat, frames/sec, and last frame age.


### 9) CSV logging
Steps:
1. Run with `--log-csv tools\can_nt\can_nt_log.csv`.
2. Let it run for at least 5 seconds, then stop.
Expected:
- File `tools\can_nt\can_nt_log.csv` exists and has a header row.
- Each subsequent row has timestamp, busErrorCount, framesPerSec, errorsPerSec.
- Per-ID columns include count, ageSec, and status.

### 10) Quick check mode
Steps:
1. Run with `--quick-check`.
Expected:
- Tool waits for `--quick-wait` seconds (default 1.0).
- Prints a single summary and exits.

### 11) DIO limit switch reporting
Steps:
1. Add `limits` to a device entry in `data/bringup_system.json`, for example:
   `{ "label": "FL KRAK", "id": 2, "limits": { "fwdDio": 0, "revDio": 1, "invert": false } }`
2. Wire limit switches to the specified DIO ports.
3. Deploy and run the robot code.
4. Controller0: press `D-pad Left` to print health status.
Expected:
- The device row includes `limits=fwd:DIO0=OPEN/ CLOSED,rev:DIO1=OPEN/ CLOSED`.
- Toggling the limit switch updates the reported state.
- When a limit is CLOSED, motor output in that direction is clamped to 0.0.
- If your switch is normally closed, set `"invert": true` in the profile entry.

### 12) Non-motor device test action
Steps:
1. Ensure a CANdle is in the profile (`candles` list).
2. Deploy and run the robot code.
3. Controller1: press `A` to run the non-motor test action.
Expected:
- The CANdle toggles between OFF and BLUE.
- Console prints `Test: <label> (CANdle) [toggle_led]`.

## Create New Tests
Purpose: add data-driven tests without code changes.

1. Launch the CLI in local-only mode:
   - `python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt`
2. Enter config mode: `configure terminal`.
3. Select or create a test set: `test set <name>`.
4. Create a test: `test create <name>` (enters test mode).
5. Configure the test:
  - `type joystick|button|composite|deadbandSweep|deviceAction`
   - `device add <label>`
   - `inputSource <controller>.<inputId>` for joystick/button/composite
   - `deadband <value>` for joystick
   - `duty <value>` for button/composite
   - `termination hold|time <sec>|rotation <rot>|limitswitch` for button/composite
6. Exit test mode: `end`.
7. Save tests: `write tests bringup_tests.json`.
8. Copy the file to `src/main/deploy/bringup_tests.json` and deploy the robot code.
9. In teleop, use controller1 `LB`/`RB` to select the test and `A` to run it.

Current test types:
- `composite`: duty + checks (rotation/time/limitSwitch/hold).
- `joystick`: live joystick control of configured motors.
- `deadbandSweep`: sweep duty to find deadband threshold.

Example (composite with rotation + time + hold):
```json
{
  "type": "composite",
  "name": "Rotation + Time + Hold",
  "enabled": true,
  "duty": 0.2,
  "rotation": { "limitRot": 5.0, "encoderKey": "internal", "encoderMotorIndex": 0 },
  "time": { "timeoutSec": 2.0, "onTimeout": "fail" },
  "hold": { "enabled": true, "onRelease": "pass" },
  "motorLabels": ["SPARKMAX/NEO 25"]
}
```

Example (joystick):
```json
{
  "type": "joystick",
  "name": "Joystick motor (controller0.leftY)",
  "enabled": true,
  "motorLabels": ["SPARKMAX/NEO 25"],
  "deadband": 0.12,
  "inputSource": "controller0.leftY"
}
```

Notes:
- Hold checks use the run-test binding (controller1 `A`, hold).
- Tests run only against motors that are instantiated via add/add-all.

## Troubleshooting

If no frames are received:
- Verify CANable wiring to CANH/CANL/GND.
- Verify bus power and termination.
- Confirm the correct COM port.
- Confirm the CANable firmware is in SLCAN mode.

If NT is not connected:
- Verify RIO IP and connectivity.
- Confirm the RIO is running robot code and NT server is active.

If imports fail:
- Use the explicit Python path shown above.
- If you see `bringup_system.json load failed: Profile data_hash mismatch`, run `sync_profiles.cmd` from the repo root to update the profile hash.

## Pass/Fail Record

Use this section to record test outcomes:

- Auto-detect COM: PASS / FAIL
- RIO connection: PASS / FAIL
- No CAN traffic warning: PASS / FAIL
- Device labels/status: PASS / FAIL
- Print-publish: PASS / FAIL
- Summary formatting: PASS / FAIL
- Groups rollup: PASS / FAIL
- NetworkTables keys: PASS / FAIL
- CSV logging: PASS / FAIL
- Quick check: PASS / FAIL

