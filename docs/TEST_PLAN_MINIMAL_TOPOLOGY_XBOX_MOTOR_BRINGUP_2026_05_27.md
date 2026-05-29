# Test Plan: Minimal Topology + Xbox Motor Bringup

## Purpose

Provide a fully procedural first-pass test plan that starts with a minimal topology editor session, creates a tiny test network, creates simple joystick-driven motor tests, updates the robot, and runs the tests.

Topology editor is the primary definition surface in this plan. Use it for as much profile, device, layout, and group authoring work as the current product supports. Use the CLI only for the parts that are not yet fully owned by the topology editor.

This plan is intentionally narrow and explicit. Every shell command and CLI command needed for the current pass is included directly in this document.

## Scope

This plan validates a minimal profile containing:

- 1 roboRIO device
- 1 PDH device
- 1 DIO limit switch on channel `0`
- 1 Spark MAX / NEO device at CAN ID `25`
- 1 Falcon 500 device at CAN ID `9`
- 1 Xbox controller device used for runtime test input

This plan covers:

- topology editor authoring
- topology-editor-first definition of profile devices, layout, and simple group membership
- config save/reload checks
- DSL test creation
- one simple runtime group with one joystick binding
- local validation
- robot config push, selected-profile verification, and explicit runtime activation
- Bringup Control UI live motor actuation checks for both motors
- robot-side test selection and run
- joystick-based behavior validation

## Out Of Scope

This pass does not yet include:

- multiple simultaneous motor tests
- sensors
- deeper live topology overlay behavior beyond using the UI to run the motors
- advanced group workflows beyond one simple `motors` group
- automated regression additions for this exact scenario

## Safety

- Put the robot on blocks or otherwise isolate any moving mechanism.
- Keep output small on the first run.
- Keep Driver Station disable available at all times.
- Return joystick to neutral before each enable/run step.
- If any motor moves unexpectedly, disable immediately and stop the test session.
- If Driver Station is actively in use on the Driver Station PC, do not type interactive CLI commands on that same keyboard.
- Run the CLI over SSH from a second laptop when Driver Station is active, to avoid accidental keyboard-triggered disable or E-Stop events.

## Assumptions

- Repo root is:

```text
C:\Users\dmona\swerveBringupMotorTest1-main
```

- roboRIO host is:

```text
172.22.11.2
```

- REST command server port is:

```text
5805
```

- The topology editor is launched from:

```text
python -m tools.can_topology.can_top_editor
```

- The CLI is launched from:

```text
python -m tools.can_nt.can_nt_bridge --cli --no-can --no-nt --rio 172.22.11.2
```

- The Bringup Control UI is launched from:

```text
python -m tools.can_nt.can_nt_bridge --ui --no-can --rio 172.22.11.2
```

- In this plan:
  - topology editor is the primary authoring tool for profile, device, canvas, and group membership definition
- CLI is used for DSL test import and validation, runtime group binding, robot push, and command-driven runtime checks
  - Bringup Control UI is used for direct live motor actuation checks from the UI
  - Bringup Control UI is also used for explicit runtime activation/deactivation and optional config push/download

- If Driver Station is being used during robot-connected steps, the CLI is run from an SSH session into the Driver Station PC rather than directly from the Driver Station keyboard.

## Driver Station SSH Rule

When Driver Station is active, use the CLI through an SSH session from a second machine.

Reason:

- Driver Station keyboard handling can treat keys like Space or Enter as safety/operator actions.
- Interactive CLI usage on that same keyboard can unintentionally disable or E-Stop the robot.

Reference:

- [SPEC_SSH_DRIVER_STATION_CLI.md](/c:/Users/dmona/swerveBringupMotorTest1-main/docs/SPEC_SSH_DRIVER_STATION_CLI.md:1)

## Test Profile And Test Names

Use these exact names in this procedure:

- Profile: `test_minimal_25_9`
- Limit switch label: `lmtSw0`
- Spark test: `spark25_leftY`
- Spark 25-rotation test: `spark25_move_25_rotations`
- Falcon test: `falcon9_leftY`
- Spark-to-limit test: `spark25_to_limit`
- Falcon-to-limit test: `falcon9_to_limit`
- Both-motors-to-limit test: `motors_to_limit`

## Phase 0: Open Working Shells

### Step 0.1: Open PowerShell in repo root

Run:

```powershell
cd C:\Users\dmona\swerveBringupMotorTest1-main
```

### Step 0.2: Create a working logs folder if needed

Run:

```powershell
New-Item -ItemType Directory -Force tools\can_nt\logs | Out-Null
```

Expected:

- command succeeds without error

### Step 0.3: If Driver Station will be active, prepare SSH access

If the robot-connected phases of this test will be run while Driver Station is active, do this before launching the CLI.

On the Driver Station PC, open Command Prompt and run:

```text
ping <laptop-ip>
```

Example:

```text
ping 192.168.1.50
```

Then from the second laptop, open an SSH session:

```text
ssh sshuser@superspec1
```

If hostname resolution fails:

```text
ssh sshuser@<driver-station-ip>
```

After SSH login, move to the repo root on the Driver Station PC:

```text
cd C:\Users\dmona\swerveBringupMotorTest1-main
```

Expected:

- SSH session opens successfully
- repo root is accessible from the SSH session

## Phase 1: Topology Editor Session

### Step 1.1: Launch the topology editor

From PowerShell:

```powershell
cd C:\Users\dmona\swerveBringupMotorTest1-main
python -m tools.can_topology.can_top_editor
```

Expected:

- the topology editor opens
- no schema/version repair prompt appears on startup

### Step 1.2: Create a new blank profile

In the topology editor:

1. Open `Profiles`
2. Choose `New Blank Profile...`
3. Enter:

```text
test_minimal_25_9
```

Expected:

- the new profile is created
- it becomes the active profile in the editor

### Step 1.3: Add the Xbox controller

In the topology editor:

1. Open `Edit`
2. Choose `Add Xbox Controller...`
3. Set:
   - Count: `1`
   - Starting Port: `0`

Expected:

- `controller0` appears in the left-side list
- it does not appear on the topology canvas

### Step 1.4: Show all config devices in the left list

In the topology editor:

1. Find the `List Scope` dropdown
2. Select:

```text
Full Config
```

Expected:

- full device inventory is visible

### Step 1.5: Add or drag the roboRIO into the profile

Use the left-side full-config list to locate the roboRIO device.

If it already exists in full config:

1. Drag it from the left list onto the canvas

If it does not exist yet:

1. Use the editor’s add-device workflow to create it first
2. Make sure it is a roboRIO device

Expected:

- the roboRIO appears on the canvas
- the device is part of the current profile

### Step 1.6: Add or drag the PDH into the profile

Use the left-side full-config list to locate the PDH device.

If it already exists in full config:

1. Drag it from the left list onto the canvas

If it does not exist yet:

1. Use the editor’s add-device workflow to create it first
2. Make sure it is a PDH device

Expected:

- the PDH appears on the canvas
- the device is part of the current profile

### Step 1.7: Add or drag the Spark MAX motor into the profile

Use the left-side full-config list to locate the Spark MAX motor at CAN ID `25`.

If it already exists in full config:

1. Drag it from the left list onto the canvas

If it does not exist yet:

1. Use the editor’s add-device workflow to create it first
2. Make sure it is a Spark MAX / NEO style motor device
3. Set CAN ID to:

```text
25
```

Expected:

- the Spark device appears on the canvas
- the device is part of the current profile

### Step 1.8: Add or create the limit switch on DIO 0

Use the left-side full-config list to locate the DIO limit switch device.

If it already exists in full config:

1. Drag it from the left list onto the canvas

If it does not exist yet:

1. Use the editor’s add-device workflow to create it first
2. Set interface to:

```text
DIO
```

3. Set type to:

```text
limitSwitch
```

4. Set label to:

```text
lmtSw0
```

5. Set DIO channel to:

```text
0
```

Expected:

- the limit switch appears on the canvas or in the active profile inventory
- label `lmtSw0` is part of the current profile
- DIO channel `0` is assigned

### Step 1.9: Add or drag the Falcon motor into the profile

Use the same process for the Falcon device at CAN ID `9`.

Expected:

- the Falcon device appears on the canvas
- the device is part of the current profile

### Step 1.10: Create a simple readable layout

On the canvas:

- place the roboRIO and PDH visibly on the topology
- place the DIO limit switch so it is visible and identifiable as `lmtSw0`
- place the Spark MAX node visibly apart from the Falcon node
- keep the layout small and readable
- do not create unnecessary extra topology objects

Expected:

- roboRIO is visible
- PDH is visible
- `lmtSw0` is visible
- both motor devices are visible
- basic selection and drag are stable
- no unexpected diagram jumps occur during simple edits

### Step 1.11: Save to deploy

In the topology editor:

1. Open `File`
2. Choose `Save to Deploy`

Expected:

- the deploy-side config is updated
- no save error appears

### Step 1.12: Create the `motors` group in the topology editor

Use the topology editor as the primary authoring surface for group membership.

In the topology editor:

1. Multi-select both motor nodes
2. Open `Groups`
3. Choose `Create Group from Selection...`
4. Enter:

```text
motors
```

Expected:

- group `motors` is created from the selected motor nodes
- both motor labels are members of the group

### Step 1.13: Save to deploy again after group creation

In the topology editor:

1. Open `File`
2. Choose `Save to Deploy`

Expected:

- the group definition is persisted to the deploy-backed config
- no save error appears

### Step 1.14: Reload to prove persistence

In the topology editor:

1. Reopen the same deploy-backed config if needed
2. Reload or restart the editor
3. Reopen profile:

```text
test_minimal_25_9
```

Expected:

- `controller0` is still in the left list
- roboRIO is still present
- PDH is still present
- `lmtSw0` is still present on DIO `0`
- Spark MAX `25` is still present
- Falcon `9` is still present
- group `motors` is still present
- layout is preserved

## Phase 2: Create Joystick-Driven DSL Tests

## Purpose

Topology editor should own as much definition work as possible.

For this pass, the remaining DSL test-definition workflow is still CLI and file based, so the test files are created here outside the topology editor.

If these files are being created from the SSH session on the Driver Station PC, use `nano` so the file contents are edited directly in-place.

`nano` save and exit reminder:

- `Ctrl+O` to write the file
- press `Enter` to confirm the filename
- `Ctrl+X` to exit

### Step 2.1: Create Spark MAX DSL source file with `nano`

From the shell where you are creating the files:

```text
cd C:\Users\dmona\swerveBringupMotorTest1-main
mkdir tools\can_nt\logs 2>nul
nano tools\can_nt\logs\spark25_leftY.dsl
```

In `nano`, enter exactly:

```text
test "spark25_leftY"
device "SPARKMAX/NEO 25"
device "controller0"

main:
    set "SPARKMAX/NEO 25".output_percent_cmd = controller0.leftY deadband 0.08 scaled 0.25 default 0.0
    until timer.elapsed >= 10.0
```

Expected:

- file `tools\can_nt\logs\spark25_leftY.dsl` is created

### Step 2.2: Create Falcon DSL source file with `nano`

From the shell where you are creating the files:

```text
cd C:\Users\dmona\swerveBringupMotorTest1-main
nano tools\can_nt\logs\falcon9_leftY.dsl
```

In `nano`, enter exactly:

```text
test "falcon9_leftY"
device "FALCON 9"
device "controller0"

main:
    set "FALCON 9".output_percent_cmd = controller0.leftY deadband 0.08 scaled 0.25 default 0.0
    until timer.elapsed >= 10.0
```

Expected:

- file `tools\can_nt\logs\falcon9_leftY.dsl` is created

### Step 2.3: Create Spark 25-rotation DSL source file with `nano`

From the shell where you are creating the files:

```text
cd C:\Users\dmona\swerveBringupMotorTest1-main
nano tools\can_nt\logs\spark25_move_25_rotations.dsl
```

In `nano`, enter exactly:

```text
test "spark25_move_25_rotations"
device "SPARKMAX/NEO 25"

main:
    set "SPARKMAX/NEO 25".output_percent_cmd = 0.25
    until "SPARKMAX/NEO 25".position_delta > 25.0
    require "SPARKMAX/NEO 25".velocity_actual > 50
    require "SPARKMAX/NEO 25".current_actual > 0.5
    abort "SPARKMAX/NEO 25".current_actual > 30
```

Expected:

- file `tools\can_nt\logs\spark25_move_25_rotations.dsl` is created

### Step 2.4: Create Spark-to-limit DSL source file with `nano`

From the shell where you are creating the files:

```text
cd C:\Users\dmona\swerveBringupMotorTest1-main
nano tools\can_nt\logs\spark25_to_limit.dsl
```

In `nano`, enter exactly:

```text
test "spark25_to_limit"
device "SPARKMAX/NEO 25"
device "lmtSw0"

main:
    set "SPARKMAX/NEO 25".output_percent_cmd = 0.20
    abort "SPARKMAX/NEO 25".current_actual > 40
    success lmtSw0.pressed
```

Expected:

- file `tools\can_nt\logs\spark25_to_limit.dsl` is created

### Step 2.5: Create Falcon-to-limit DSL source file with `nano`

From the shell where you are creating the files:

```text
cd C:\Users\dmona\swerveBringupMotorTest1-main
nano tools\can_nt\logs\falcon9_to_limit.dsl
```

In `nano`, enter exactly:

```text
test "falcon9_to_limit"
device "FALCON 9"
device "lmtSw0"

main:
    set "FALCON 9".output_percent_cmd = 0.20
    abort "FALCON 9".current_actual > 40
    success lmtSw0.pressed
```

Expected:

- file `tools\can_nt\logs\falcon9_to_limit.dsl` is created

### Step 2.6: Create both-motors-to-limit DSL source file with `nano`

From the shell where you are creating the files:

```text
cd C:\Users\dmona\swerveBringupMotorTest1-main
nano tools\can_nt\logs\motors_to_limit.dsl
```

In `nano`, enter exactly:

```text
test "motors_to_limit"
device "SPARKMAX/NEO 25"
device "FALCON 9"
device "lmtSw0"

main:
    set "SPARKMAX/NEO 25".output_percent_cmd = 0.15
    set "FALCON 9".output_percent_cmd = 0.15
    abort "SPARKMAX/NEO 25".current_actual > 40
    abort "FALCON 9".current_actual > 40
    success lmtSw0.pressed
```

Expected:

- file `tools\can_nt\logs\motors_to_limit.dsl` is created

### Step 2.7: Review the created DSL files

Run:

```powershell
Get-Content tools\can_nt\logs\spark25_leftY.dsl
Get-Content tools\can_nt\logs\falcon9_leftY.dsl
Get-Content tools\can_nt\logs\spark25_move_25_rotations.dsl
Get-Content tools\can_nt\logs\spark25_to_limit.dsl
Get-Content tools\can_nt\logs\falcon9_to_limit.dsl
Get-Content tools\can_nt\logs\motors_to_limit.dsl
```

Expected:

- all files show the expected contents

## Phase 3: Local CLI Validation And Test Import

### Step 3.1: Launch the CLI

From a new PowerShell window:

```powershell
cd C:\Users\dmona\swerveBringupMotorTest1-main
python -m tools.can_nt.can_nt_bridge --cli --no-can --no-nt --rio 172.22.11.2
```

Expected:

- CLI starts
- prompt appears

If Driver Station is active, launch the CLI inside the SSH session instead of using the Driver Station keyboard directly.

After SSH login, run:

```text
cd C:\Users\dmona\swerveBringupMotorTest1-main
python -m tools.can_nt.can_nt_bridge --cli --no-can --no-nt --rio 172.22.11.2
```

Expected:

- CLI starts inside the SSH session
- Driver Station keyboard remains reserved for Driver Station use

### Step 3.2: Enter config mode and select the profile

In the CLI:

```text
configure terminal
profile test_minimal_25_9
```

Expected:

- CLI enters config mode
- host profile context becomes `test_minimal_25_9`

### Step 3.3: Show local devices before importing tests

In the CLI:

```text
show devices local --json --pretty
```

Expected:

- output includes:
  - roboRIO
  - PDH
  - `lmtSw0`
  - Spark MAX / NEO `25`
  - Falcon `9`
  - `controller0`

### Step 3.4: Import the Spark test

In the CLI:

```text
test import spark25_leftY tools/can_nt/logs/spark25_leftY.dsl set default
test validate spark25_leftY --json --pretty
```

Expected:

- import succeeds
- validation succeeds

### Step 3.5: Import the Falcon test

In the CLI:

```text
test import falcon9_leftY tools/can_nt/logs/falcon9_leftY.dsl set default
test validate falcon9_leftY --json --pretty
```

Expected:

- import succeeds
- validation succeeds

### Step 3.6: Import the Spark 25-rotation test

In the CLI:

```text
test import spark25_move_25_rotations tools/can_nt/logs/spark25_move_25_rotations.dsl set default
test validate spark25_move_25_rotations --json --pretty
```

Expected:

- import succeeds
- validation succeeds

### Step 3.7: Import the limit-terminated tests

In the CLI:

```text
test import spark25_to_limit tools/can_nt/logs/spark25_to_limit.dsl set default
test validate spark25_to_limit --json --pretty
test import falcon9_to_limit tools/can_nt/logs/falcon9_to_limit.dsl set default
test validate falcon9_to_limit --json --pretty
test import motors_to_limit tools/can_nt/logs/motors_to_limit.dsl set default
test validate motors_to_limit --json --pretty
```

Expected:

- all three imports succeed
- all three validations succeed

### Step 3.8: Show normalized test definitions

In the CLI:

```text
end
show test spark25_leftY normalized --json --pretty
show test spark25_move_25_rotations normalized --json --pretty
show test falcon9_leftY normalized --json --pretty
show test spark25_to_limit normalized --json --pretty
show test falcon9_to_limit normalized --json --pretty
show test motors_to_limit normalized --json --pretty
```

Expected:

- all tests render normalized JSON
- joystick tests reference the expected motor label and `controller0.leftY`
- the 25-rotation test references Spark MAX `25` with position-based termination
- limit-terminated tests reference `lmtSw0`

### Step 3.9: Validate and sync the full config

From PowerShell:

```powershell
cd C:\Users\dmona\swerveBringupMotorTest1-main
python -m tools.validate_sync
```

Expected:

- validation succeeds
- deploy config is synchronized

## Phase 3A: Create A Simple Motor Group Binding

## Purpose

Bind `controller0.rightY` to the already-authored `motors` group.

Group membership should already have been created in the topology editor.

This CLI phase only adds the runtime binding because the current test-plan target is to keep group definition in the topology editor and use the CLI only for the part the editor does not yet fully own.

### Step 3A.1: Re-enter config mode

In the CLI:

```text
configure terminal
profile test_minimal_25_9
```

Expected:

- CLI is in config mode
- host profile context is `test_minimal_25_9`

### Step 3A.2: Enter the `motors` group context

In the CLI:

```text
group motors
```

Expected:

- group `motors` already exists from the topology editor session
- current config context is the `motors` group

### Step 3A.3: Bind the right Y joystick to the group

In the CLI:

```text
bind controller0.rightY analog
```

Expected:

- the current group gets one analog binding from `controller0.rightY`

### Step 3A.4: Show the group and its bindings

In the CLI:

```text
show group motors local --json --pretty
show bindings local --json --pretty
```

Expected:

- `show group motors local --json --pretty` shows both motor members
- the group shows one binding using:
  - input: `controller0.rightY`
  - kind: `analog`

### Step 3A.5: Save and sync after group binding

In the CLI:

```text
save all --force
end
```

Then from PowerShell:

```powershell
cd C:\Users\dmona\swerveBringupMotorTest1-main
python -m tools.validate_sync
```

Expected:

- config save succeeds
- validation succeeds

### Step 3A.6: Expected group JSON shape

The resulting group should conceptually look like:

```json
{
  "name": "motors",
  "enabled": true,
  "members": [
    { "label": "SPARKMAX/NEO 25", "enabled": true },
    { "label": "FALCON 9", "enabled": true }
  ],
  "bindings": [
    { "input": "controller0.rightY", "kind": "analog" }
  ]
}
```

This is provided as a validation reference only. Use the CLI commands above as the actual authoring path for this plan.

## Phase 4: Push Config To Robot

### Step 4.1: Re-enter the CLI if needed

If the CLI is no longer open:

```powershell
cd C:\Users\dmona\swerveBringupMotorTest1-main
python -m tools.can_nt.can_nt_bridge --cli --no-can --no-nt --rio 172.22.11.2
```

If Driver Station is active, use the SSH session and run:

```text
cd C:\Users\dmona\swerveBringupMotorTest1-main
python -m tools.can_nt.can_nt_bridge --cli --no-can --no-nt --rio 172.22.11.2
```

### Step 4.2: Connect to the robot

In the CLI:

```text
connect
```

Expected:

- connection succeeds

### Step 4.3: Push the config without implicit activation

In the CLI:

```text
configure terminal
config push src/main/deploy/bringup_system.json
end
```

Expected:

- transfer check succeeds
- content validation succeeds
- apply succeeds
- post-apply check succeeds
- selected robot profile becomes `test_minimal_25_9`
- runtime is not implicitly activated by this command

### Step 4.4: Confirm selected profile before runtime activation

In the CLI:

```text
show profiles robot --json --pretty
show runtime-state robot --json --pretty
```

Expected:

- `selectedProfile` is `test_minimal_25_9`
- `activeRuntimeProfile` is empty or `(none)`
- `runtimeActive` is `false`

### Step 4.5: Stop using the CLI for activation

After `config push` succeeds, do not use the CLI to activate runtime in this phase.

Expected:

- the selected robot profile is already `test_minimal_25_9`
- runtime is still inactive
- the remaining activation handoff will be done from the Bringup Control UI

Note:

- `config push src/main/deploy/bringup_system.json --activate test_minimal_25_9` remains a supported convenience wrapper
- this plan intentionally avoids that shortcut so selection, push, and activation remain visibly separate actions

### Step 4.6: Confirm robot selection state before switching to the UI

In the CLI:

```text
show runtime-state robot --json --pretty
show tests robot --json --pretty
```

Expected:

- runtime-state responds successfully
- `selectedProfile` is `test_minimal_25_9`
- `activeRuntimeProfile` is empty or `(none)`
- `runtimeActive` is `false`
- tests list includes:
  - `spark25_leftY`
  - `spark25_move_25_rotations`
  - `falcon9_leftY`
  - `spark25_to_limit`
  - `falcon9_to_limit`
  - `motors_to_limit`

### Step 4.7: Confirm the `motors` group reached the robot

In the CLI:

```text
show groups robot --json --pretty
show group motors robot --json --pretty
```

Expected:

- group `motors` exists on the robot
- both motor labels are present in the group
- the group binding includes `controller0.rightY`

## Phase 4R: Test REST Directly Without CLI Or UI

## Purpose

Validate the robot REST server directly, without using the bringup CLI or Bringup Control UI as the client surface.

This proves:

- the REST server is reachable
- session ownership works
- inventory and health endpoints work
- direct command submit, status, and output paths work

### Step 4R.1: Make sure CLI and UI are not connected

Operator actions:

1. Close or disconnect the Bringup Control UI if it is open
2. Exit or disconnect the bringup CLI if it is still connected

Expected:

- no other client is holding the REST control session

### Step 4R.2: Check REST health directly

From Command Prompt or PowerShell, use `curl.exe`:

```text
curl.exe http://172.22.11.2:5805/health
```

Expected:

- JSON response returns successfully
- `ok` is true
- `server` is `bringupRest`

### Step 4R.3: Reset the REST session for a clean direct test

Run:

```text
curl.exe -X POST http://172.22.11.2:5805/session/reset -H "Content-Type: application/json" -d "{}"
```

Expected:

- JSON response returns successfully
- session reset is acknowledged
- command ID allocation is reset to a known clean state

### Step 4R.4: Connect a direct REST test client

Run:

```text
curl.exe -X POST http://172.22.11.2:5805/session/connect -H "Content-Type: application/json" -d "{\"clientId\":\"rest-test-client\"}"
```

Expected:

- JSON response returns successfully
- `connected` is true
- `ownerClientId` is `rest-test-client`

### Step 4R.5: Read direct session state

Run:

```text
curl.exe http://172.22.11.2:5805/session
```

Expected:

- JSON response returns successfully
- session owner is `rest-test-client`

### Step 4R.6: Read direct REST command inventory

Run:

```text
curl.exe http://172.22.11.2:5805/inventory/commands
```

Expected:

- JSON response returns successfully
- command inventory is returned

### Step 4R.7: Submit `showDevices` directly over REST

Run:

```text
curl.exe -X POST http://172.22.11.2:5805/commands -H "Content-Type: application/json" -d "{\"clientId\":\"rest-test-client\",\"requestId\":\"rest-req-1\",\"name\":\"showDevices\",\"args\":{}}"
```

Expected:

- JSON response returns successfully
- command is accepted or finished
- after the session reset in Step 4R.3, this command should be `commandId` `1`

### Step 4R.8: Read `showDevices` command status and output

Run:

```text
curl.exe "http://172.22.11.2:5805/commands/1?clientId=rest-test-client"
curl.exe "http://172.22.11.2:5805/commands/1/output?clientId=rest-test-client"
```

Expected:

- status response returns successfully
- output response returns successfully
- output contains device information for the active robot profile

### Step 4R.9: Submit `showRuntimeState` directly over REST

Run:

```text
curl.exe -X POST http://172.22.11.2:5805/commands -H "Content-Type: application/json" -d "{\"clientId\":\"rest-test-client\",\"requestId\":\"rest-req-2\",\"name\":\"showRuntimeState\",\"args\":{}}"
```

Expected:

- JSON response returns successfully
- after the session reset in Step 4R.3, this command should be `commandId` `2`

### Step 4R.10: Read `showRuntimeState` command status and output

Run:

```text
curl.exe "http://172.22.11.2:5805/commands/2?clientId=rest-test-client"
curl.exe "http://172.22.11.2:5805/commands/2/output?clientId=rest-test-client"
```

Expected:

- status response returns successfully
- output response returns successfully
- output contains runtime-state information

### Step 4R.11: Disconnect the direct REST test client

Run:

```text
curl.exe -X POST http://172.22.11.2:5805/session/disconnect -H "Content-Type: application/json" -d "{\"clientId\":\"rest-test-client\"}"
```

Expected:

- JSON response returns successfully
- direct REST test session is released cleanly

## Phase 4A: Run Motors From The Bringup Control UI

## Purpose

Validate that each motor can also be actuated from the Bringup Control UI live topology surface, not only through CLI-driven tests and group bindings.

### Step 4A.1: Launch the Bringup Control UI

From PowerShell:

```powershell
cd C:\Users\dmona\swerveBringupMotorTest1-main
python -m tools.can_nt.can_nt_bridge --ui --no-can --rio 172.22.11.2
```

Expected:

- Bringup Control UI opens

### Step 4A.2: Connect the UI to the robot

In the Bringup Control UI:

1. Verify the robot profile field
2. Use the normal connect/handshake flow if needed
3. Verify the profile dropdown is not silently activating anything
4. Open the `Live Topology` tab
5. Set source to:

```text
rest
```

6. Enable live overlay if required

Expected:

- live topology loads
- Spark MAX `25` node is visible
- Falcon `9` node is visible
- the UI is attached to the robot session cleanly before any manual motor actuation is attempted
- the UI still shows runtime inactive until the operator explicitly activates it

### Step 4A.3: Optionally refresh UI config from the robot

In the Bringup Control UI:

1. Click:

```text
Download Current Config
```

Expected:

- the host/UI config model reloads from the robot canonical config
- profile/test/group views refresh cleanly
- selected profile remains `test_minimal_25_9`
- runtime is still inactive after download

### Step 4A.4: Explicitly activate runtime from the UI

In the Bringup Control UI:

1. Confirm the selected profile is:

```text
test_minimal_25_9
```

2. Click:

```text
Runtime Activate
```

Expected:

- activation succeeds
- the UI shows runtime active
- active runtime profile becomes `test_minimal_25_9`
- the UI made runtime active only because of the explicit button press

### Step 4A.5: Verify live runtime telemetry after UI activation

In the Bringup Control UI:

1. Keep `Enable Live Overlay` on
2. Select each motor node once

Expected:

- selection pane begins updating from robot runtime-state
- routine live updates occur at the default `2 Hz` overlay rate unless the operator changes it
- selection pane shows best-effort robot-local telemetry without requiring a CAN sniffer
- live overlay polling remains lighter than full diagnostic polling

### Step 4A.6: Run the Spark motor from the UI

In the `Live Topology` tab:

1. Right-click the Spark MAX motor node
2. In the manual motor popup, move the slider slowly positive
3. Return slider toward zero
4. Left-click the live topology view to clear the manual motor duty

Expected:

- Spark MAX `25` moves when the slider is moved
- Falcon `9` does not move during this step
- left-click clears the manual duty and stops the Spark motor

### Step 4A.7: Run the Falcon motor from the UI

In the `Live Topology` tab:

1. Right-click the Falcon motor node
2. In the manual motor popup, move the slider slowly positive
3. Return slider toward zero
4. Left-click the live topology view to clear the manual motor duty

Expected:

- Falcon `9` moves when the slider is moved
- Spark MAX `25` does not move during this step
- left-click clears the manual duty and stops the Falcon motor

### Step 4A.8: Close or disconnect the UI cleanly

In the Bringup Control UI:

1. Use the disconnect path if the session is still active
2. Close the UI window

Expected:

- the UI session releases cleanly

## Phase 4B: Confirm The Editor-Defined Group And UI Surface Together

## Purpose

Prove that the topology-editor-defined `motors` group and the Bringup Control UI surface are both present in the same configured system before CLI-driven runtime tests begin.

### Step 4B.1: Reopen the UI if needed

If the UI was closed in Phase 4A, relaunch it:

```powershell
cd C:\Users\dmona\swerveBringupMotorTest1-main
python -m tools.can_nt.can_nt_bridge --ui --no-can --rio 172.22.11.2
```

Expected:

- Bringup Control UI opens

### Step 4B.2: Verify the correct profile and live nodes again

In the Bringup Control UI:

1. Confirm the active profile is:

```text
test_minimal_25_9
```

2. Open `Live Topology`
3. Confirm both motor nodes are still visible

Expected:

- the UI still reflects the minimal test profile
- both individual motors are visible in the live topology surface

### Step 4B.3: Disconnect the UI before returning to CLI-driven runtime steps

In the Bringup Control UI:

1. Disconnect the session if it is still connected
2. Close the UI

Expected:

- the REST control session is released for the next CLI-controlled steps

## Phase 5: Run The Spark MAX Test

### Step 5.1: Select the Spark test

In the CLI:

```text
tests select spark25_leftY
```

Expected:

- selected test becomes `spark25_leftY`

### Step 5.2: Prepare for safe motion

Operator actions:

1. Put the robot in a safe enabled test posture
2. Confirm joystick is centered
3. Confirm no motor is moving at neutral

Expected:

- no motion before test run

### Step 5.3: Run the Spark test

In the CLI:

```text
tests run
```

Expected:

- run command succeeds

### Step 5.4: Move the joystick and validate Spark behavior

Operator actions:

1. Move `controller0.leftY` slowly forward
2. Return to neutral
3. Move `controller0.leftY` slowly reverse
4. Return to neutral

Expected:

- Spark MAX motor at `25` responds proportionally
- Falcon motor at `9` does not move
- neutral returns Spark output to zero

### Step 5.5: Validate stop behavior

Operator actions:

1. Return joystick to neutral
2. Disable robot or use the normal stop path if needed

Expected:

- Spark motor stops immediately

## Phase 6: Run The Falcon Test

### Step 6.1: Select the Falcon test

In the CLI:

```text
tests select falcon9_leftY
```

Expected:

- selected test becomes `falcon9_leftY`

### Step 6.2: Run the Falcon test

In the CLI:

```text
tests run
```

Expected:

- run command succeeds

### Step 6.3: Move the joystick and validate Falcon behavior

Operator actions:

1. Move `controller0.leftY` slowly forward
2. Return to neutral
3. Move `controller0.leftY` slowly reverse
4. Return to neutral

Expected:

- Falcon motor at `9` responds proportionally
- Spark MAX motor at `25` does not move during this test
- neutral returns Falcon output to zero

### Step 6.4: Validate stop behavior

Operator actions:

1. Return joystick to neutral
2. Disable robot or use the normal stop path if needed

Expected:

- Falcon motor stops immediately

## Phase 6A: Run The `motors` Group From The Right Y Joystick

### Step 6A.1: Prepare for group-binding validation

Operator actions:

1. Confirm no DSL test is currently running
2. Confirm joystick is centered
3. Confirm both motors are stopped

Expected:

- no motion at neutral

### Step 6A.2: Move the right Y joystick slowly

Operator actions:

1. Move `controller0.rightY` slowly forward
2. Return to neutral
3. Move `controller0.rightY` slowly reverse
4. Return to neutral

Expected:

- both motors respond together because both are members of group `motors`
- joystick neutral returns both outputs to zero
- movement is proportional and controlled

### Step 6A.3: Validate stop behavior for the group binding

Operator actions:

1. Return `controller0.rightY` to neutral
2. Disable the robot if needed

Expected:

- both motors stop immediately
- no motor continues running after neutral or disable

## Phase 6AA: Run The Spark 25-Rotation Test

### Step 6AA.1: Select the Spark 25-rotation test

In the CLI:

```text
tests select spark25_move_25_rotations
```

Expected:

- selected test becomes `spark25_move_25_rotations`

### Step 6AA.2: Prepare for a controlled rotation run

Operator actions:

1. Confirm the Spark mechanism can safely rotate at least 25 turns
2. Confirm there is enough clearance for the full travel
3. Confirm the robot is in a safe enabled test posture

Expected:

- the mechanism can complete the travel safely

### Step 6AA.3: Run the Spark 25-rotation test

In the CLI:

```text
tests run
```

Expected:

- run command succeeds

### Step 6AA.4: Validate fixed-duty rotation termination

Operator actions:

1. Observe the Spark motor run at fixed duty
2. Allow it to continue until the test terminates on its own

Expected:

- Spark MAX `25` runs at `0.25` duty
- the test terminates after roughly 25 rotations of the Spark mechanism
- Spark motion stops when the rotation target is reached
- Falcon `9` does not move during this test

## Phase 6B: Run The Spark-To-Limit Test

### Step 6B.1: Select the Spark-to-limit test

In the CLI:

```text
tests select spark25_to_limit
```

Expected:

- selected test becomes `spark25_to_limit`

### Step 6B.2: Prepare the limit switch

Operator actions:

1. Confirm `lmtSw0` is not pressed before starting
2. Confirm the robot is in a safe enabled test posture
3. Confirm the Spark mechanism can reach the physical limit safely

Expected:

- test can start with the switch open

### Step 6B.3: Run the Spark-to-limit test

In the CLI:

```text
tests run
```

Expected:

- run command succeeds

### Step 6B.4: Trigger the limit switch and validate termination

Operator actions:

1. Allow the Spark motor to move toward the limit
2. Trigger the physical limit switch on DIO `0`

Expected:

- Spark MAX `25` runs at low duty
- the test ends successfully when `lmtSw0` becomes pressed
- Spark motion stops immediately after the success termination
- Falcon `9` does not move

## Phase 6C: Run The Falcon-To-Limit Test

### Step 6C.1: Select the Falcon-to-limit test

In the CLI:

```text
tests select falcon9_to_limit
```

Expected:

- selected test becomes `falcon9_to_limit`

### Step 6C.2: Run the Falcon-to-limit test

In the CLI:

```text
tests run
```

Expected:

- run command succeeds

### Step 6C.3: Trigger the limit switch and validate termination

Operator actions:

1. Allow the Falcon motor to move toward the limit
2. Trigger the physical limit switch on DIO `0`

Expected:

- Falcon `9` runs at low duty
- the test ends successfully when `lmtSw0` becomes pressed
- Falcon motion stops immediately after the success termination
- Spark MAX `25` does not move

## Phase 6D: Run The Both-Motors-To-Limit Test

### Step 6D.1: Select the both-motors-to-limit test

In the CLI:

```text
tests select motors_to_limit
```

Expected:

- selected test becomes `motors_to_limit`

### Step 6D.2: Run the both-motors-to-limit test

In the CLI:

```text
tests run
```

Expected:

- run command succeeds

### Step 6D.3: Trigger the limit switch and validate termination

Operator actions:

1. Allow both motors to move at low duty
2. Trigger the physical limit switch on DIO `0`

Expected:

- both motors move at low duty
- the test ends successfully when `lmtSw0` becomes pressed
- both motors stop immediately after the success termination

## Phase 7: Re-Run After Restart Or Update

### Step 7.1: Restart robot code or power-cycle as needed

Use the normal robot restart path.

Expected:

- robot comes back cleanly

### Step 7.2: Reconnect and re-verify

In the CLI:

```text
connect
show profiles robot --json --pretty
show runtime-state robot --json --pretty
show devices robot --json --pretty
show tests robot --json --pretty
```

Expected:

- selected profile is still `test_minimal_25_9`
- runtime is inactive immediately after restart until explicitly activated
- profile, devices, and tests are still present

### Step 7.3: Reactivate runtime after restart

Preferred UI path:

1. Open the Bringup Control UI
2. Click:

```text
Runtime Activate
```

3. Verify runtime state from the UI or CLI

CLI fallback:

```text
runtime activate test_minimal_25_9
show runtime-state robot --json --pretty
```

Expected:

- runtime activation succeeds
- `activeRuntimeProfile` becomes `test_minimal_25_9`
- `runtimeActive` is `true`

### Step 7.4: Re-run both tests briefly

In the CLI:

```text
tests select spark25_leftY
tests run
tests select falcon9_leftY
tests run
tests select spark25_move_25_rotations
tests run
tests select spark25_to_limit
tests run
```

Expected:

- the selected tests still run
- behavior matches the first pass

### Step 7.5: Deactivate runtime at the end of the session

In the CLI:

```text
runtime deactivate
show runtime-state robot --json --pretty
disconnect
```

Expected:

- runtime deactivation succeeds
- `runtimeActive` is `false`
- selected profile remains `test_minimal_25_9`
- session disconnect succeeds

## Evidence To Capture

Capture all of the following:

- screenshot of topology editor canvas with roboRIO, PDH, `lmtSw0`, Spark `25`, and Falcon `9`
- screenshot of topology editor group creation result for `motors`
- screenshot of Bringup Control UI live topology showing both motor nodes
- screenshot of Bringup Control UI runtime controls showing:
  - selected profile
  - active runtime profile
  - runtime active state
- screenshot or saved output of:

```text
curl.exe http://172.22.11.2:5805/health
curl.exe http://172.22.11.2:5805/inventory/commands
curl.exe "http://172.22.11.2:5805/commands/1?clientId=rest-test-client"
curl.exe "http://172.22.11.2:5805/commands/1/output?clientId=rest-test-client"
curl.exe "http://172.22.11.2:5805/commands/2?clientId=rest-test-client"
curl.exe "http://172.22.11.2:5805/commands/2/output?clientId=rest-test-client"
show devices local --json --pretty
show profiles robot --json --pretty
show runtime-state robot --json --pretty
show devices robot --json --pretty
show tests robot --json --pretty
show group motors robot --json --pretty
```

- notes for Spark test:
  - forward
  - reverse
  - neutral stop
- notes for Falcon test:
  - forward
  - reverse
  - neutral stop
- notes for Spark 25-rotation test:
  - fixed duty run
  - approximate completed rotations
  - automatic stop at target
- notes for Spark-to-limit test:
  - initial motion
  - switch trip
  - immediate stop
- notes for Falcon-to-limit test:
  - initial motion
  - switch trip
  - immediate stop
- notes for both-motors-to-limit test:
  - both moving
  - switch trip
  - both stopped
- notes for UI manual Spark motor run
- notes for UI manual Falcon motor run
- note whether `Download Current Config` refreshed the UI model correctly
- note whether `Runtime Activate` from the UI succeeded without returning to CLI
- note whether direct REST calls succeeded without using CLI or UI
- note that profile, devices, and group membership were defined in the topology editor first, with CLI used only for binding/test/import/push/runtime steps
- note whether robot-connected CLI steps were run:
  - directly on a host shell
  - or from an SSH session while Driver Station was active

## Acceptance Criteria

This test plan passes only if:

- `test_minimal_25_9` can be created and saved
- `controller0` is present in the profile
- roboRIO is present in the profile
- PDH is present in the profile
- `lmtSw0` is present in the profile on DIO `0`
- Spark MAX `25` is present in the profile
- Falcon `9` is present in the profile
- group `motors` is created from topology editor selection and persists after reload
- both DSL tests import and validate successfully
- Spark 25-rotation DSL test imports and validates successfully
- all limit-terminated DSL tests import and validate successfully
- config push succeeds without implicit runtime activation
- explicit runtime activation succeeds
- Bringup Control UI can activate runtime explicitly after config push
- Bringup Control UI can download current config without activating runtime
- robot reports the expected devices and tests
- direct REST health, inventory, command status, and command output calls succeed without CLI or UI
- Bringup Control UI live topology can manually run Spark `25`
- Bringup Control UI live topology can manually run Falcon `9`
- Spark test moves only Spark `25`
- Falcon test moves only Falcon `9`
- Spark 25-rotation test runs Spark `25` at `0.25` duty and stops at about 25 rotations
- Spark-to-limit test stops on `lmtSw0`
- Falcon-to-limit test stops on `lmtSw0`
- both-motors-to-limit test stops both motors on `lmtSw0`
- group `motors` exists with both motors as members
- `controller0.rightY` drives the `motors` group
- neutral and disable stop motion reliably
- the same behavior still works after restart/reconnect, with runtime remaining inactive until explicitly reactivated

## Failure Recording

For any failure, record:

- exact phase and step number
- exact command that was run
- exact output text or screenshot
- whether failure is:
  - topology editor
  - local validation
  - config push
  - robot runtime
  - joystick behavior

## Future Extensions

Later revisions should add:

- more motors
- richer topology-editor-owned group binding workflows
- sensor checks
- live topology checks
- automated regression steps
- config recovery and failure injection
