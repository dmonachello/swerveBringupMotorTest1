# Test Plan (May 22, 2026)

  

## Purpose

  

Provide an operator-executable, step-by-step regression plan for all major changes landed from May 15, 2026 through May 22, 2026.

  

This document is written so the tester can execute each step verbatim without filling in missing workflow details.

  

## Weekly Change Scope

  

This test plan covers these change areas:

  

- deploy-owned config cutover to `src/main/deploy/`

- removal of legacy `data/` config ownership and runtime fallback assumptions

- topology upgrade and cross-surface topology compatibility

- topology rendering and PDF/export alignment

- CLI visibility, TIU, and bindings diagnostics

- robot-local command modularization

- generated host-UI command metadata

- DSL signal-provider modularization

  

## Commits In Scope

  

- `05b0481` `Unify topology rendering across editor and UI`

- `f1559c0` `Add swerve club test config and feature docs`

- `a1fe22c` `Align topology PDF export with editor scene`

- `1548a4f` `Add CLI visibility, TIU, and bindings diagnostics`

- `92d7b9f` `Remove runtime config fallbacks and document robot base`

- `5d7e439` `Cut over config tooling to deploy-owned files`

- `b1f4db7` `Remove legacy data directory files`

- `5df0dcf` `Merge branch 'topology_upgrade'`

- `8f6dabf` `Modularize robot local commands and DSL signal providers`

  

## Test Modes

  

Run this plan in three layers:

  

1. Local-only Windows tests

2. Local topology-editor manual tests

3. Connected roboRIO non-motion tests

  

If a roboRIO is not available, complete Sections A through F and mark Section G as blocked by hardware.

  

## Preconditions

  

Before starting, verify all of the following:

  

1. You are on a Windows machine.

2. The repo is available at `C:\Users\dmona\swerveBringupMotorTest1-main`.

3. `python` works from PowerShell.

4. `.\gradlew.bat` works from the repo root.

5. If `JAVA_HOME` is set, it points at the JDK root and not the `bin` directory.

6. If you will run connected tests, the roboRIO is reachable at the intended IP and running current bringup code.

  

## Tester Recording Instructions

  

For each numbered step:

  

- mark `PASS` if the expected result occurs exactly or with only trivial cosmetic differences

- mark `FAIL` if the command errors, output is missing, output is wrong, or behavior differs materially

- mark `BLOCKED` only if the step requires hardware or software that is unavailable

  

Record failures with:

  

- step number

- exact command used

- exact observed output

- screenshot or file path when useful

  

## Environment Setup

  

### Step 0.1: Open PowerShell

  

Open a new PowerShell window.

  

Expected:

  

- PowerShell opens successfully.

  

### Step 0.2: Change to repo root

  

Run:

  

```powershell

cd C:\Users\dmona\swerveBringupMotorTest1-main

```

  

Expected:

  

- the shell prompt now shows the repo root

  

### Step 0.3: Confirm Python is available

  

Run:

  

```powershell

python --version

```

  

Expected:

  

- Python prints a version and exits with no error

  

### Step 0.4: Confirm Gradle wrapper is available

  

Run:

  

```powershell

.\gradlew.bat --version

```

  

Expected:

  

- Gradle wrapper prints version information and exits with no error

  

## A. Local Regression Gate

  

Purpose: prove the maintained automated regression surface is still green before manual testing starts.

  

### Step A1: Run the local suite

  

Run:

  

```powershell

python tools\can_nt\scripts\run_regressions.py --suite local

```

  

Expected:

  

- the command exits successfully

- the summary line reports zero failures

- no command in the run references deleted `data\bringup_system.json` or `data\motor_specs.json`

  

### Step A2: Run the DSL suite

  

Run:

  

```powershell

python tools\can_nt\scripts\run_regressions.py --suite dsl

```

  

Expected:

  

- the command exits successfully

- the summary line reports zero failures

  

### Step A3: Run the topology suite

  

Run:

  

```powershell

python tools\can_nt\scripts\run_regressions.py --suite topology

```

  

Expected:

  

- the command exits successfully

- the summary line reports zero failures

  

### Step A4: Run the cross-surface suite

  

Run:

  

```powershell

python tools\can_nt\scripts\run_regressions.py --suite cross-surface

```

  

Expected:

  

- the command exits successfully

- the summary line reports zero failures

  

### Step A5: Run the CLI suite

  

Run:

  

```powershell

python tools\can_nt\scripts\run_regressions.py --suite cli

```

  

Expected:

  

- the command exits successfully

- the summary line reports zero failures

  

### Step A6: Run the Java suite

  

Run:

  

```powershell

python tools\can_nt\scripts\run_regressions.py --suite java

```

  

Expected:

  

- the command exits successfully

- the summary line reports zero failures

  

### Step A7: Run the changelog guard suite

  

Run:

  

```powershell

python tools\can_nt\scripts\run_regressions.py --suite changelog

```

  

Expected:

  

- the command exits successfully

- the summary line reports zero failures

  

## B. Config Ownership And Local CLI Validation

  

Purpose: validate the deploy-owned config cutover and ensure local tools no longer depend on deleted `data\` config files.

  

### Step B1: Confirm deploy-owned config files exist

  

In PowerShell, run:

  

```powershell

Get-ChildItem src\main\deploy\bringup_system.json

Get-ChildItem src\main\deploy\bringup_bindings.json

```

  

Expected:

  

- both files exist

  

### Step B2: Confirm deleted legacy config files are absent

  

In PowerShell, run:

  

```powershell

Test-Path data\bringup_system.json

Test-Path data\motor_specs.json

```

  

Expected:

  

- both commands print `False`

  

### Step B3: Start the CLI in local-only mode

  

Run:

  

```powershell

python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt

```

  

Expected:

  

- the CLI starts successfully

- a local prompt appears

- the startup output identifies deploy-owned config paths under `src\main\deploy\`

  

### Step B4: Show workspace

  

At the CLI prompt, type:

  

```text

show workspace

```

  

Expected:

  

- the output shows profiles loaded from `src\main\deploy\bringup_system.json`

- the output shows bindings loaded from `src\main\deploy\bringup_bindings.json`

- the output does not point at deleted `data\` config files

  

### Step B5: Enter configure mode

  

At the CLI prompt, type:

  

```text

configure terminal

```

  

Expected:

  

- the prompt changes into config mode

  

### Step B6: Validate config

  

At the CLI prompt, type:

  

```text

validate config

```

  

Expected:

  

- the CLI prints either `OK: Config is valid.` or an exact validation failure

- if invalid, the message identifies the exact offending entity

  

### Step B7: Validate bindings

  

At the CLI prompt, type:

  

```text

bindings validate

```

  

Expected:

  

- the CLI succeeds

- if optional controller bindings are absent, the command fails soft with a clear message rather than crashing

  

### Step B8: Validate CAN mappings

  

At the CLI prompt, type:

  

```text

can-mappings validate

```

  

Expected:

  

- the CLI succeeds and prints either valid or an exact failure

  

### Step B9: Show dirty state

  

At the CLI prompt, type:

  

```text

show config dirty

```

  

Expected:

  

- the CLI prints the local dirty-state block

- the output is readable and source-aware

  

### Step B10: Show tests

  

At the CLI prompt, type:

  

```text

show tests

```

  

Expected:

  

- the CLI prints the current local test set

- the command succeeds without requiring robot connectivity

  

### Step B11: Show CAN mappings

  

At the CLI prompt, type:

  

```text

show can-mappings

```

  

Expected:

  

- the CLI prints local CAN mapping content

- the command succeeds without CAN hardware

  

### Step B12: Exit the CLI

  

At the CLI prompt, type:

  

```text

end

exit

```

  

Expected:

  

- the CLI exits cleanly

  

## C. CLI Visibility, Diagnostics, And Authoring

  

Purpose: validate the CLI changes from the last week with both automated and interactive checks.

  

### Step C1: Run the visibility unit tests

  

In PowerShell, run:

  

```powershell

python -m unittest tools.can_nt.tests.test_bridge_cli_visibility

```

  

Expected:

  

- the test command exits successfully

  

### Step C2: Run the DSL CLI unit tests

  

In PowerShell, run:

  

```powershell

python -m unittest tools.can_nt.tests.test_bridge_cli_robot_test_dsl_cli

```

  

Expected:

  

- the test command exits successfully

  

### Step C3: Run the facade unit tests

  

In PowerShell, run:

  

```powershell

python -m unittest tools.can_nt.tests.test_bridge_cli_facades

```

  

Expected:

  

- the test command exits successfully

  

### Step C4: Start the CLI again in local-only mode

  

Run:

  

```powershell

python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt

```

  

Expected:

  

- the CLI starts successfully

  

### Step C5: Show topology text view

  

At the CLI prompt, type:

  

```text

show topology

```

  

Expected:

  

- the command succeeds

- the output renders topology from the current shared topology interpretation

  

### Step C6: Show topology JSON view

  

At the CLI prompt, type:

  

```text

show topology json

```

  

Expected:

  

- the command succeeds

- JSON output is printed

  

### Step C7: Show help

  

At the CLI prompt, type:

  

```text

help

```

  

Expected:

  

- help text prints successfully

- the command vocabulary matches current canonical commands

- no removed alias is presented as valid

  

### Step C8: Enter configure mode

  

At the CLI prompt, type:

  

```text

configure terminal

```

  

Expected:

  

- the prompt changes into config mode

  

### Step C9: Select the default test set

  

At the CLI prompt, type:

  

```text

test set default

```

  

Expected:

  

- the command succeeds

  

### Step C10: Create a new test

  

At the CLI prompt, type:

  

```text

test create MySignalTest

```

  

Expected:

  

- the command succeeds

- the prompt changes into test-config mode

  

### Step C11: Set the test type

  

At the CLI prompt, type:

  

```text

type joystick

```

  

Expected:

  

- the command succeeds

  

### Step C12: Add the device

  

At the CLI prompt, type:

  

```text

device add "SPARKMAX/NEO 25"

```

  

Expected:

  

- the command succeeds

  

### Step C13: Set the controller signal input

  

At the CLI prompt, type:

  

```text

inputSource controller0.leftY

```

  

Expected:

  

- the command succeeds

  

### Step C14: Set deadband

  

At the CLI prompt, type:

  

```text

deadband 0.12

```

  

Expected:

  

- the command succeeds

  

### Step C15: Show the test

  

At the CLI prompt, type:

  

```text

show

```

  

Expected:

  

- the output shows:

  - test name `MySignalTest`

  - type `joystick`

  - device `SPARKMAX/NEO 25`

  - input source `controller0.leftY`

  - deadband `0.12`

  

### Step C16: Exit the CLI

  

At the CLI prompt, type:

  

```text

end

exit

```

  

Expected:

  

- the CLI exits cleanly

  

## D. Topology Upgrade And Cross-Surface Manual Retest

  

Purpose: validate the root topology graph, editor behavior, cross-surface compatibility, and shared rendering alignment.

  

### Step D1: Launch the topology editor

  

In PowerShell, run:

  

```powershell

python -m tools.can_topology.can_top_editor

```

  

Expected:

  

- the topology editor opens successfully

  

### Step D2: Load the `robot_2026_swerve` profile

  

In the topology editor:

  

1. Open the profile/file selection path used by the editor.

2. Load `robot_2026_swerve`.

  

Expected:

  

- the profile loads with no exception

- the scene contains the expected large swerve profile content

  

### Step D3: Verify visible profile content

  

With `robot_2026_swerve` loaded, inspect the scene.

  

Expected:

  

- roboRIO is visible

- PDH is visible

- 4 CANnect nodes are visible

- the expected drive motors and other devices are visible

  

### Step D4: Use Fit to Window

  

In the topology editor, click the `Fit to Window` action.

  

Expected:

  

- the diagram is framed sensibly

- important devices are not off-screen by default

  

### Step D5: Verify blank-space click does not disturb the viewport

  

After using `Fit to Window`, click empty canvas space.

  

Expected:

  

- selection clears if anything was selected

- the viewport does not jump

  

### Step D6: Verify zoom preservation

  

Use the mouse wheel to zoom in.

  

Then click empty canvas space.

  

Expected:

  

- zoom stays where you left it

- the viewport does not reset

  

### Step D7: Verify pan preservation

  

Use middle mouse button drag to pan the canvas.

  

Then click empty canvas space.

  

Expected:

  

- the pan position is preserved

- the viewport does not reset

  

### Step D8: Verify selection clear behavior

  

Perform these actions in order:

  

1. Select one node.

2. Click empty canvas.

3. Shift-select multiple nodes.

4. Click empty canvas.

5. Select a bus segment.

6. Click empty canvas.

  

Expected:

  

- selection clears correctly each time

  

### Step D9: Verify connection filter `None`

  

In the topology editor, open the connection filter control.

  

Then select `None`.

  

Expected:

  

- all connection types disappear

- blue virtual or ethernet-style links disappear too

  

### Step D10: Re-enable all connection filters

  

In the topology editor, re-enable:

  

- CAN

- Power

- DIO

- PWM

- Analog

- Virtual

  

Expected:

  

- each category returns correctly

- no category is stuck hidden

  

### Step D11: Resize a bus segment

  

Perform these actions in order:

  

1. Select a bus segment.

2. Resize it left.

3. Resize it right.

  

Expected:

  

- attached devices follow the segment bounds

- CANnect direct nodes follow the segment bounds

- CANnect inject nodes follow the segment bounds

- linked connectors still line up

  

### Step D12: Edit a device

  

Edit one device in the loaded profile.

  

Change at least these fields:

  

- label

- device ID

- vendor or manufacturer

- device type or model

  

Expected:

  

- the editor accepts the edits

  

### Step D13: Trigger validation messaging

  

Create or edit one generic device so that required vendor/device-type fields are missing.

  

Then trigger save or validation.

  

Expected:

  

- the editor reports a validation failure

- the message names the exact offending device label

  

### Step D14: Save the profile

  

Save the edited profile.

  

Expected:

  

- save succeeds without exception

  

### Step D15: Close the topology editor

  

Quit the topology editor.

  

Expected:

  

- the editor closes cleanly

  

### Step D16: Reopen the topology editor

  

In PowerShell, run again:

  

```powershell

python -m tools.can_topology.can_top_editor

```

  

Expected:

  

- the editor opens successfully

  

### Step D17: Reload `robot_2026_swerve`

  

Load the same profile again.

  

Expected:

  

- the profile opens successfully

- the saved geometry and edits are retained

  

### Step D18: Verify callout retention

  

If you added or edited a callout before save, verify it is still present after reload.

  

Expected:

  

- callout text, placement, and target are retained

  

### Step D19: Close the topology editor

  

Quit the topology editor.

  

Expected:

  

- the editor closes cleanly

  

### Step D20: Run the topology editor regression directly

  

In PowerShell, run:

  

```powershell

python tools\can_nt\scripts\topology_editor_regression.py

```

  

Expected:

  

- the command exits successfully

  

### Step D21: Run the cross-surface regression directly

  

In PowerShell, run:

  

```powershell

python tools\can_nt\scripts\cross_surface_regression.py

```

  

Expected:

  

- the command exits successfully

  

### Step D22: Run topology unit tests

  

In PowerShell, run:

  

```powershell

python -m unittest tools.can_topology.tests.test_can_top_editor_profile_load

python -m unittest tools.can_topology.tests.test_live_topology_view

python -m unittest tools.can_topology.tests.test_validate_profiles_topology

```

  

Expected:

  

- all three test commands exit successfully

  

## E. Robot-Local Command And Generated UI Metadata Checks

  

Purpose: validate the new canonical Java command registry/executor path and generated Python command metadata.

  

### Step E1: Run the robot-local command registry test

  

In PowerShell, run:

  

```powershell

.\gradlew.bat test --tests frc.robot.RobotLocalCommandRegistryTest

```

  

Expected:

  

- the Gradle test command succeeds

  

### Step E2: Run the Bridge UI command executor test

  

In PowerShell, run:

  

```powershell

.\gradlew.bat test --tests frc.robot.BridgeUiCommandExecutorTest

```

  

Expected:

  

- the Gradle test command succeeds

  

### Step E3: Run the Bridge UI runtime commands test

  

In PowerShell, run:

  

```powershell

.\gradlew.bat test --tests frc.robot.BridgeUiRuntimeCommandsTest

```

  

Expected:

  

- the Gradle test command succeeds

  

### Step E4: Run the Bridge UI session commands test

  

In PowerShell, run:

  

```powershell

.\gradlew.bat test --tests frc.robot.BridgeUiSessionCommandsTest

```

  

Expected:

  

- the Gradle test command succeeds

  

### Step E5: Regenerate robot-local command artifacts

  

In PowerShell, run:

  

```powershell

python tools\can_nt\scripts\generate_robot_local_command_artifacts.py

```

  

Expected:

  

- the generator runs successfully

- no unexpected error is printed

  

### Step E6: Check whether the generated file changed unexpectedly

  

In PowerShell, run:

  

```powershell

git diff -- tools/can_nt/generated/robot_local_commands_generated.py

```

  

Expected:

  

- no unexpected diff appears

- if a diff appears, it must be explainable by an intentional registry change

  

### Step E7: Start the Python bringup UI

  

In PowerShell, run the normal UI startup command your team uses for local inspection.

  

If you need the direct entrypoint, use:

  

```powershell

python tools\can_nt\bringup_ui.py

```

  

Expected:

  

- the UI starts successfully

  

### Step E8: Inspect the action surface

  

In the UI, inspect the buttons and sections shown on the action surface.

  

Expected:

  

- the UI shows button groups built from generated metadata

- obvious legacy-only hardcoded sections do not replace generated content

  

### Step E9: Inspect one command’s metadata presentation

  

In the UI, inspect one visible command entry.

  

Expected:

  

- its label is correct

- its section placement is correct

- its description is correct

- its default arguments, if shown, are correct

  

### Step E10: Close the UI

  

Close the Python bringup UI.

  

Expected:

  

- the UI closes cleanly

  

## F. DSL Signal Provider And Runtime Semantics

  

Purpose: validate provider-based DSL signal handling, expanded controller signal support, and explicit clear-failure semantics.

  

### Step F1: Run Python DSL unit tests

  

In PowerShell, run:

  

```powershell

python -m unittest tools.can_nt.tests.test_robot_test_dsl

```

  

Expected:

  

- the test command exits successfully

  

### Step F2: Run device catalog tests

  

In PowerShell, run:

  

```powershell

python -m unittest tools.common.tests.test_device_catalog

```

  

Expected:

  

- the test command exits successfully

  

### Step F3: Run schema-store profile tests

  

In PowerShell, run:

  

```powershell

python -m unittest tools.common.tests.test_schema_store_profiles

```

  

Expected:

  

- the test command exits successfully

  

### Step F4: Run Java DSL runtime tests

  

In PowerShell, run:

  

```powershell

.\gradlew.bat test --tests frc.robot.DslBringupTestTest

```

  

Expected:

  

- the test command succeeds

  

### Step F5: Confirm no unsupported-clear regression appeared

  

Review the output from Step F4.

  

Expected:

  

- no failure indicates that unsupported clear targets are being silently ignored

  

## G. Connected RoboRIO Non-Motion Pass

  

Purpose: validate robot/host integration after the weekly changes without requiring motion-dependent testing.

  

Skip this section only if no roboRIO is available.

  

### Step G1: Confirm roboRIO address

  

Decide the correct roboRIO IP or host for this test run.

  

For the examples below, use:

  

`172.22.11.2`

  

Expected:

  

- the tester knows the correct target IP before running commands

  

### Step G2: Run the direct non-motion regression

  

In PowerShell, run:

  

```powershell

python tools\can_nt\scripts\bridge_cli_robot_non_motion_regression.py --rio 172.22.11.2

```

  

Expected:

  

- the command exits successfully

- handshake succeeds

- session behavior remains stable

- no motion-dependent failure occurs

  

### Step G3: Run the named regression suite form

  

In PowerShell, run:

  

```powershell

python tools\can_nt\scripts\run_regressions.py --suite robot-non-motion --rio 172.22.11.2

```

  

Expected:

  

- the command exits successfully

- the summary line reports zero failures

  

### Step G4: Start the connected CLI

  

In PowerShell, run:

  

```powershell

python tools\can_nt\can_nt_bridge.py --cli --rio 172.22.11.2 --no-can

```

  

Expected:

  

- the CLI starts successfully

- the robot connection succeeds

  

### Step G5: Show status

  

At the CLI prompt, type:

  

```text

show status

```

  

Expected:

  

- the command succeeds

- status output is returned from the connected robot path

  

### Step G6: Show groups

  

At the CLI prompt, type:

  

```text

show groups

```

  

Expected:

  

- the command succeeds

- group information is returned

  

### Step G7: Exit the connected CLI

  

At the CLI prompt, type:

  

```text

exit

```

  

Expected:

  

- the CLI exits cleanly

  

## H. Optional Live Bringup Operator Check

  

Purpose: run a short live operator pass only if controller bindings, tests, or runtime command behavior were part of the work being validated.

  

Skip this section if the robot is unavailable or if motion testing is not permitted.

  

### Step H1: Prepare the robot safely

  

Before enabling the robot:

  

1. Put drivetrain wheels off the floor or otherwise secure the robot.

2. Verify an emergency stop path is available.

3. Keep the test area clear.

  

Expected:

  

- the robot is safe for limited bringup actions

  

### Step H2: Start the standard bringup UI or controller workflow

  

Use the team’s standard workflow for bringup.

  

Expected:

  

- the workflow starts successfully

  

### Step H3: Verify profile select versus activate behavior

  

Perform the standard operator action that changes the selected profile.

  

Then perform the standard action that activates the selected profile.

  

Expected:

  

- selection alone does not activate the robot profile

- explicit activation changes the robot runtime profile

  

### Step H4: Verify `addAll`

  

Run the standard `addAll` action for the selected profile.

  

Expected:

  

- devices are added successfully

- no duplicate-creation behavior appears unexpectedly

  

### Step H5: Verify state and tests reporting

  

Run the standard actions for:

  

- `printState`

- `printTestsOverview`

- profile-device reporting

  

Expected:

  

- each report prints successfully

- output remains readable and consistent with the active profile

  

### Step H6: Verify test execution controls

  

Run the standard actions for:

  

- one selected hold-to-run test

- one run-all or multi-test path if available

  

Expected:

  

- test execution starts and stops correctly

- disable and stop-latch behavior remain safe

  

## Exit Criteria

  

The weekly test plan passes when all of the following are true:

  

1. Sections A through F pass with no unexplained failures.

2. Section G passes, or is marked `BLOCKED` due to missing hardware.

3. No active workflow still depends on deleted `data\` config ownership.

4. Topology editor save/load and cross-surface behavior match the shared topology contract.

5. Generated robot-local command metadata remains aligned with the Java registry.

6. DSL signal-provider behavior remains stable in both Python and Java test surfaces.

  

## Results

  

TESTING_RESULTS:

- Date:

- Tester:

- Branch:

- Commit:

- Section A result:

- Section B result:

- Section C result:

- Section D result:

- Section E result:

- Section F result:

- Section G result:

- Section H result:

- Open failures: