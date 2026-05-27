# TEST_PROCEDURE_ZERO_CONFIG

**Purpose**
Define a repeatable bringup procedure that starts from zero config (only `can_mappings.json` and `bringup_bindings.json` exist), then builds the profile one motor at a time via CLI, verifies in the topology editor, syncs to robot, and runs tests locally and remotely.

**Scope**
This procedure uses profile `home_042126V1` and starts with `SPARKMAX/NEO 25`.
It defines a per-motor button test and a composite "all motors" test that grows as devices are added.
It also uses runtime active-group commands (`active show`, `active add`, `active next`) for explicit
device progression during bringup.

**Actuation Contract (Important)**
Purpose: Prevent unexpected movement during bringup.

- `instantiate all devices` and `instantiate next motor` instantiate devices only; they do not start motor motion.
- Motion occurs only while an explicit test is running (`run test ...` / `run all tests`).
- If no test is active, commands that would directly actuate outputs are blocked.

## Group and Targeting V1 Update (April 20, 2026)

Purpose: keep zero-config procedure checks aligned with finalized targeting behavior.

- Name resolution is exact and case-insensitive.
- Device and group names share one global namespace.
- `active` is reserved, always exists, is not persisted, and resets on save/commit.
- Group members are a set: duplicate add warns/no-op; missing remove warns/no-op.
- Include `show groups` and `show group active` in verification steps.
- `group delete active` must fail.
- `device delete <name>` must fail when referenced by any group/test.
- `group delete <name>` must fail when referenced by tests.
- Non-interactive copy into existing named groups must fail without mutation.

**Preconditions**
Purpose: Ensure a clean starting state.

- `src\main\deploy\can_mappings.json` exists.
- `src\main\deploy\bringup_bindings.json` exists.
- The file `src\main\deploy\bringup_system.json` does not exist (we create it from scratch).

**Zero-Config CLI Command (Recommended)**
Purpose: Perform the zero-config delete with one guarded CLI command.

- Command: `reset zero-config`
- Optional non-interactive: `reset zero-config --yes`
- Behavior: prints warning and target files, then prompts `y/N` before deletion unless `--yes` is provided.

**Robot Reset (Delete All Deploy Files)**
Purpose: Force the robot to load only freshly deployed files.
Run these from PowerShell (NI‑Auth admin login required):

```powershell
ssh admin@172.22.11.2
# After NI-Auth login:
rm -f /home/lvuser/deploy/bringup_system.json
find / -name "*.json" -print
exit

```

**Zero Config Reset**
Purpose: Delete existing config so the CLI creates a new one.

```powershell
del .\src\main\deploy\bringup_system.json

```

Equivalent CLI path from `bridge>`:

```text
reset zero-config
```

Optional: Verify the host files are gone.

```powershell
dir .\src\main\deploy\bringup_system.json

```

**Phase 1: Offline CLI Create (Local Only)**
Purpose: Create a new profile and add the first motor.

1. Start CLI offline:

```powershell
cd %USERPROFILE%\swerveBringupMotorTest1-main
python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt

```

Note: If `bringup_system.json` is missing, the CLI will start in **recovery mode**. That is expected for this procedure.
You can continue creating a new profile in config mode, but robot‑facing operations that depend on profiles/tests
will be blocked or unreliable until recovery is cleared. Recovery mode exists to prevent sending robot commands
without a valid local tables payload (devices/tests/groups). Recovery mode will clear once a valid
`bringup_system.json` is saved and synced to deploy, then the CLI is restarted.
Expected response: Version banner, a warning about missing `bringup_system.json`, and a `bridge>` prompt.

1. Create the profile and select it:

```text
configure terminal
profile create home_042126V1
profile home_042126V1

```

Expected response: `SUCCESS` for each command. Prompt changes from `bridge>` to a config prompt. Example:
`bridge(config-profile-local)#` then after `profile create home_042126V1` becomes
`bridge(config-profile-home_042126V1)#`.

1. Add the first motor device:

```text
device "SPARKMAX/NEO 25"
manufacturer 5
deviceType 2
id 25
model "REV NEO"
type motor
deviceInterface CAN
exit

```

Expected response: `SUCCESS` after each `set` with `Updated device ...` messages. `exit` returns to config and may print
`WARNING: Unsaved changes in: profiles.`

1. Verify the device is in the active profile:

```text
show profile home_042126V1

```

Expected response: `SOURCE: local` and a profile payload that includes `SPARKMAX/NEO 25` in the devices list.
Why this works: in profile‑backed configs, entering `device "<label>"` automatically ensures the label is
present in the active profile’s device list.

1. Import a per-motor button test:

```text
test import neo25_button tools/can_nt/logs/neo25_button.dsl set default
test validate neo25_button --json --pretty
end
show test neo25_button
show test neo25_button normalized --json --pretty
```

Create `tools\can_nt\logs\neo25_button.dsl` with:

```text
test "neo25_button"
device "SPARKMAX/NEO 25"
device "controller0"

main:
    set "SPARKMAX/NEO 25".output = 0.25
    until timer.elapsed >= 2.0
```

1. Import an “all motors” test:

```text
test import all_motors tools/can_nt/logs/all_motors.dsl set default
test validate all_motors --json --pretty
end
show test all_motors normalized --json --pretty
```

Expected response: Same as above, with normalized imported test output available through `show test ... normalized --json --pretty`.

1. Save the unified config locally (do not save legacy test files):

```text
save config src\main\deploy\bringup_system.json
end

```

Expected response: `Wrote unified config to ...` and possible validation warnings if profiles/tests are incomplete.
Use `end` here to return to exec mode.
If you see a warning about mismatched sources or a prompt to overwrite, re-run the command with `--force`.
Optional: Verify the host files were created.

```powershell
dir .\src\main\deploy\bringup_system.json

```

Example output:

```text
%USERPROFILE%\swerveBringupMotorTest1>dir .\src\main\deploy\bringup_system.json
 Volume in drive C is Windows
 Volume Serial Number is CED6-04AC

 Directory of %USERPROFILE%\swerveBringupMotorTest1\src\main\deploy

04/06/2026  03:19 PM             7,333 bringup_system.json
               1 File(s)          7,333 bytes
               0 Dir(s)  488,573,743,104 bytes free

%USERPROFILE%\swerveBringupMotorTest1>

```

**Phase 2: Topology Editor Check**
Purpose: Verify and optionally tweak the diagram metadata, then save from the editor.

1. Open the editor:

```powershell
cd %USERPROFILE%\swerveBringupMotorTest1-main
python -m tools.can_topology.can_top_editor

```

Expected response: The editor opens with no CLI output unless an error occurs.

1. File → Open → `src\main\deploy\bringup_system.json`.
2. Move the motor node slightly as a visible change.
3. File → Save to Deploy.
4. Close the editor.

**Phase 3: Refresh And Validate The Deploy-Owned Config**
Purpose: Validate and refresh the single deploy-owned config file.
If you used the topology editor **Save to Deploy** in Phase 2, you can skip this step.

```powershell
cd %USERPROFILE%\swerveBringupMotorTest1-main
python -m tools.sync_profiles

```

Expected response: `Synced profiles to src\main\deploy\bringup_system.json (data_version=...)`.
Optional: Verify the deploy file was created.

```powershell
dir .\src\main\deploy\bringup_system.json

```

**Phase 4: Connect, Push, Activate**
Purpose: Push the current config to the robot and activate it.
Driver Station: Disabled (or robot not enabled).
Note: If running the CLI on the Driver Station causes conflicts, run the CLI from another PC by SSH’ing into the host.
See `docs\SPEC_SSH_DRIVER_STATION_CLI.md` for the recommended workflow.

1. Start CLI online:

```powershell
cd %USERPROFILE%\swerveBringupMotorTest1-main
python tools\can_nt\can_nt_bridge.py --cli --rio 172.22.11.2

```

Expected response: Version banner, then `bridge>` prompt.

1. Push + activate:

```text
connect
configure terminal
config push src\main\deploy\bringup_system.json --activate home_042126V1
end

```

Expected response: `Connected.` then `Profiles applied. devices=... active=home_042126V1`. Use `end` to return to exec mode.
Migration note: if the robot reports old profiles after a successful deploy or push, force a disk reload.
Example:

```text
profiles reload
profiles activate home_042126V1

```

Optional: Verify the robot deploy folder has JSON files (NI‑Auth admin login required).

```powershell
ssh admin@172.22.11.2
ls -la /home/lvuser/deploy/*.json
exit

```

**Phase 5: Verify on Robot**
Purpose: Confirm devices and runtime state are visible.
Driver Station: Disabled is OK.

```text
show devices robot --json --pretty
show runtime-state robot --json --pretty

```

Expected response: `SOURCE: robot` plus JSON output containing the device list and active profile.

**Phase 6: Run Tests (Controller)**
Purpose: Run tests from the Xbox controller.
Driver Station: Enabled (teleop).

1. Enable the robot in Driver Station.
2. Press `controller0.A` to run the button test.

**Phase 7: Run Tests (Remote CLI)**
Purpose: Run tests via the CLI.
Driver Station: Enabled (teleop).

```text
instantiate all devices
active show --json
active add
active show
run test neo25_button
active next
active show
run test all_motors
```

Expected response:

- `instantiate all devices` acknowledges device instantiation.
- `active show` prints the runtime `active-group` contents.
- `active add` grows `active-group` with the next ready device.
- `active next` rotates to the next ready device (wrap warning appears when list wraps).
- `run test ...` ACKs and movement only occurs while tests are active.

**Phase 8: Add the Next Motor**
Purpose: Extend the config one motor at a time.
Driver Station: Disabled (or robot not enabled) while editing and syncing. Enable only when running tests.

1. Add the new device (same pattern as Phase 1, step 3).
2. Add it to the profile device list.
3. Edit `all_motors` and add the new device:

```text
test all_motors
device add "<NEW MOTOR LABEL>"
show
exit

```

1. Save unified config.
2. Sync profiles.
3. Push + activate.
4. Verify and run tests.
5. Refresh runtime active-group membership:

```text
instantiate all devices
active add
active show
```

Expected response: `active add` selects the next ready device; `active show` prints updated membership.

**Phase 9: Add Limit Switch (Later)**
Purpose: Add limit switch when ready.

```text
configure terminal
device "lmtSw0"
type limitSwitch
deviceInterface DIO
dio 0
invert true
end
profile device add "lmtSw0"
save config src\main\deploy\bringup_system.json
end

```

Expected response: `SUCCESS` for each `set`, and `Wrote unified config` on save. Use `end` to return to exec mode.
If you see an overwrite warning, re-run with `--force`.

**Acceptance Checks**
Purpose: Confirm the system is consistent after each cycle.

1. `src\main\deploy\bringup_system.json` is the current saved config.
2. `config push` succeeds and reports `active=home_042126V1`.
3. `show devices robot` includes the new device.
4. `instantiate all devices` does not cause motor motion before a test starts.
5. `active show`, `active add`, and `active next` update/print `active-group` as expected.
6. Both `neo25_button` and `all_motors` execute without safety stops.

---

## Appendix A: Quick Command Sequence (Current Safe Flow)

Purpose: Provide a compact, copy-friendly command runbook aligned to the current zero-config and active-group flow.

Assumption: `src\main\deploy\bringup_system.json` already exists and contains profile `home_042126V1`.

### A1) Start CLI and connect

```powershell
cd %USERPROFILE%\swerveBringupMotorTest1-main
python tools\can_nt\can_nt_bridge.py --cli --rio 172.22.11.2
```

```text
connect
configure terminal
config push src\main\deploy\bringup_system.json --activate home_042126V1
end
```

Expected: `Connected.` and profile activation ACK.

### A2) Verify robot state

```text
show devices robot --json --pretty
show runtime-state robot --json --pretty
```

Expected: `SOURCE: robot` payloads with active profile and devices.

### A3) Instantiate and inspect active-group

```text
instantiate all devices
active show --json
active add
active show
active next
active show
```

Expected:

- `instantiate all devices` instantiates devices only (no motion by itself).
- `active add` adds the next ready device to `active-group`.
- `active next` rotates to the next ready device.
- Wrap emits warning: `WARNING: device list wrapped to first entry.`

### A4) Run tests (only motion path)

```text
run test neo25_button
run test all_motors
```

Expected: Test ACKs and motion only while tests are active.

### A5) Quick reset assertion

Rule: `reset zero-config` must always print warning + y/N prompt before deleting files.

---

## Appendix B: Quick Workflow Procedure

Purpose: Provide a short bringup cycle checklist for repeated iterations.

1. Start clean (optional):
   - In CLI exec mode: `reset zero-config`.
   - Non-interactive option: `reset zero-config --yes`.

2. Build/update config locally:
   - Start offline CLI: `python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt`.
   - Enter config mode, update profile/devices/tests.
   - Save: `save config src\main\deploy\bringup_system.json`, then `end`.

3. Refresh the deploy-owned config file:
   - Run `python -m tools.sync_profiles`.

4. Push and activate on robot:
   - Start online CLI: `python tools\can_nt\can_nt_bridge.py --cli --rio <robot-ip>`.
   - `connect` → `configure terminal` → `config push src\main\deploy\bringup_system.json --activate <profile>` → `end`.

5. Verify robot state:
   - `show devices robot --json --pretty`.
   - `show runtime-state robot --json --pretty`.

6. Runtime selection and test execution:
   - `instantiate all devices`.
   - `active show --json`.
   - `active add` (grow active-group) and `active next` (rotate active focus).
   - `run test <test_name>` (or use controller binding).

7. Iterate per new device:
   - Add device, update test membership, save, sync, push, verify, run tests.

---

## Appendix C: Copy/Paste Command Block (Current Values)

Purpose: Provide a ready-to-run command sequence using current team values.

- Robot IP: `172.22.11.2`
- Profile: `home_042126V1`

Start CLI online:

```powershell
python tools\can_nt\can_nt_bridge.py --cli --rio 172.22.11.2
```

Then at `bridge>`:

```text
connect
configure terminal
config push src\main\deploy\bringup_system.json --activate home_042126V1
end

show devices robot --json --pretty
show runtime-state robot --json --pretty

instantiate all devices
active show --json
active add
active show
active next
active show

run test neo25_button
run test all_motors
```

Optional clean reset before rebuilding from scratch:

```text
reset zero-config
```

Non-interactive reset option:

```text
reset zero-config --yes
```


