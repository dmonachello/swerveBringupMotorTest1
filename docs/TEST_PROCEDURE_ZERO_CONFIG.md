**Purpose**
Define a repeatable bringup procedure that starts from zero config (only `can_mappings.json` and `bringup_bindings.json` exist), then builds the profile one motor at a time via CLI, verifies in the topology editor, syncs to robot, and runs tests locally and remotely.

**Scope**
This procedure uses profile `home_042126V1` and starts with `SPARKMAX/NEO 25`. It also defines a per‑motor button test and a composite “all motors” test that grows as devices are added.

**Preconditions**
Purpose: Ensure a clean starting state.
- `src/main/deploy/can_mappings.json` exists.
- `src/main/deploy/bringup_bindings.json` exists.
- The canonical file `data/bringup_system.json` does not exist (we create it from scratch).
- The deploy copy `src/main/deploy/bringup_system.json` does not exist (it will be generated).

**Robot Reset (Delete All Deploy Files)**
Purpose: Force the robot to load only freshly deployed files.
Run these from PowerShell (NI‑Auth admin login required):
```powershell
ssh admin@172.22.11.2
# After NI-Auth login:
rm -f /home/lvuser/deploy/*.json
find / -name "*.json" -print
exit
```

**Zero Config Reset**
Purpose: Delete existing config so the CLI creates a new one.
```powershell
del .\data\bringup_system.json
del .\src\main\deploy\bringup_system.json
```
Optional: Verify the host files are gone.
```powershell
dir .\data\bringup_system.json
dir .\src\main\deploy\bringup_system.json
```

**Phase 1: Offline CLI Create (Local Only)**
Purpose: Create a new profile and add the first motor.
1. Start CLI offline:
```powershell
cd C:\Users\dmona\swerveBringupMotorTest1-main
python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt
```
Note: If `bringup_system.json` is missing, the CLI will start in **recovery mode**. That is expected for this procedure.
You can continue creating a new profile in config mode, but robot‑facing operations that depend on profiles/tests
will be blocked or unreliable until recovery is cleared. Recovery mode exists to prevent sending robot commands
without a valid local registry (devices/tests/groups). Recovery mode will clear once a valid
`bringup_system.json` is saved and synced to deploy, then the CLI is restarted.
Expected response: Version banner, a warning about missing `bringup_system.json`, and a `bridge>` prompt.
2. Create the profile and select it:
```text
configure terminal
profile create home_042126V1
profile home_042126V1
```
Expected response: `SUCCESS` for each command. Prompt changes from `bridge>` to a config prompt. Example:
`bridge(config-profile-local)#` then after `profile create home_042126V1` becomes
`bridge(config-profile-home_042126V1)#`.
3. Add the first motor device:
```text
device "SPARKMAX/NEO 25"
set manufacturer 5
set deviceType 2
set id 25
set model "REV NEO"
set type motor
set interface CAN
exit
```
Expected response: `SUCCESS` after each `set` with `Updated device ...` messages. `exit` returns to config and may print
`WARNING: Unsaved changes in: profiles.`
4. Verify the device is in the active profile:
```text
show profile home_042126V1
```
Expected response: `SOURCE: local` and a profile payload that includes `SPARKMAX/NEO 25` in the devices list.
Why this works: in profile‑backed configs, entering `device "<label>"` automatically ensures the label is
present in the active profile’s device list.
5. Create a per‑motor button test:
```text
test create neo25_button
type button
device add "SPARKMAX/NEO 25"
inputSource controller0.A
duty 0.25
termination time 2.0
show
exit
```
Expected response: After `test create`, prompt changes to `bridge(config-test-...)#`. `show` prints the test summary.
Use `exit` to return to config mode. Do **not** use `end` here, because `end` returns to exec mode and later
config commands may fail to parse. `exit` may warn: `WARNING: Unsaved changes in: profiles, tests.`
6. Create a composite “all motors” test:
```text
test create all_motors
type composite
device add "SPARKMAX/NEO 25"
inputSource controller0.X
duty 0.25
termination time 2.0
show
exit
```
Expected response: Same as above, with the composite test summary printed by `show`. Use `exit` (not `end`)
to stay in config mode. `exit` may warn: `WARNING: Unsaved changes in: profiles, tests.`
7. Save the unified config locally (do not save legacy test files):
```text
save unified-config data\bringup_system.json
end
```
Expected response: `Wrote unified config to ...` and possible validation warnings if profiles/tests are incomplete.
Use `end` here to return to exec mode.
If you see a warning about mismatched sources or a prompt to overwrite, re-run the command with `--force`.
Optional: Verify the host files were created.
```powershell
dir .\data\bringup_system.json
```
Example output:
```text
C:\Users\dmona\swerveBringupMotorTest1>dir .\data\bringup_system.json
 Volume in drive C is Windows
 Volume Serial Number is CED6-04AC

 Directory of C:\Users\dmona\swerveBringupMotorTest1\data

04/06/2026  03:19 PM             7,333 bringup_system.json
               1 File(s)          7,333 bytes
               0 Dir(s)  488,573,743,104 bytes free

C:\Users\dmona\swerveBringupMotorTest1>
```

**Phase 2: Topology Editor Check**
Purpose: Verify and optionally tweak the diagram metadata, then save from the editor.
1. Open the editor:
```powershell
cd C:\Users\dmona\swerveBringupMotorTest1-main
python -m tools.can_topology.can_top_editor
```
Expected response: The editor opens with no CLI output unless an error occurs.
2. File → Open → `data/bringup_system.json`.
3. Move the motor node slightly as a visible change.
4. File → Save to Deploy (this writes canonical + deploy).
5. Close the editor.

**Phase 3: Sync Canonical to Deploy**
Purpose: Keep canonical and deploy copies identical.
```powershell
cd C:\Users\dmona\swerveBringupMotorTest1-main
python -m tools.sync_profiles
```
Expected response: `Synced profiles to src\main\deploy\bringup_system.json (data_version=...)`.
Optional: Verify the deploy file was created.
```powershell
dir .\src\main\deploy\bringup_system.json
```

**Phase 4: Connect, Push, Activate**
Purpose: Push the canonical config to the robot and activate it.
1. Start CLI online:
```powershell
cd C:\Users\dmona\swerveBringupMotorTest1-main
python tools\can_nt\can_nt_bridge.py --cli --rio 172.22.11.2
```
Expected response: Version banner, then `bridge>` prompt.
2. Push + activate:
```text
connect
configure terminal
config push data\bringup_system.json --activate home_042126V1
end
```
Expected response: `Connected.` then `Profiles applied. devices=... active=home_042126V1`. Use `end` to return to exec mode.
Optional: Verify the robot deploy folder has JSON files (NI‑Auth admin login required).
```powershell
ssh admin@172.22.11.2
ls -la /home/lvuser/deploy/*.json
exit
```

**Phase 5: Verify on Robot**
Purpose: Confirm devices and runtime state are visible.
```text
show devices robot --json --pretty
show runtime-state robot --json --pretty
```
Expected response: `SOURCE: robot` plus JSON output containing the device list and active profile.

**Phase 6: Run Tests (Controller)**
Purpose: Run tests from the Xbox controller.
1. Enable the robot in Driver Station.
2. Press `controller0.A` to run the button test.

**Phase 7: Run Tests (Remote CLI)**
Purpose: Run tests via the CLI.
```text
configure terminal
group testgroup
add device "SPARKMAX/NEO 25"
enable
run test neo25_button
run test all_motors
end
```
Expected response: `SUCCESS` for group setup, then `run test` ACKs from the robot. Use `end` to return to exec mode.

**Phase 8: Add the Next Motor**
Purpose: Extend the config one motor at a time.
1. Add the new device (same pattern as Phase 1, step 3).
2. Add it to the profile device list.
3. Edit `all_motors` and add the new device:
```text
test all_motors
device add "<NEW MOTOR LABEL>"
show
exit
```
4. Save unified config.
5. Sync profiles.
6. Push + activate.
7. Verify and run tests.

**Phase 9: Add Limit Switch (Later)**
Purpose: Add limit switch when ready.
```text
configure terminal
device "lmtSw0"
set type limitSwitch
set interface DIO
set dio 0
set invert true
end
profile device add "lmtSw0"
save unified-config data\bringup_system.json
end
```
Expected response: `SUCCESS` for each `set`, and `Wrote unified config` on save. Use `end` to return to exec mode.
If you see an overwrite warning, re-run with `--force`.

**Acceptance Checks**
Purpose: Confirm the system is consistent after each cycle.
1. `data/bringup_system.json` matches `src/main/deploy/bringup_system.json`.
2. `config push` succeeds and reports `active=home_042126V1`.
3. `show devices robot` includes the new device.
4. Both `neo25_button` and `all_motors` execute without safety stops.
