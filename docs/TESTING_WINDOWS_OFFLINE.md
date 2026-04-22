# Windows Offline Test Plan (No roboRIO)

Purpose: Validate Windows-hosted tools and local configuration workflows without a robot connection.

## Group and Targeting V1 Update (April 20, 2026)

Purpose: ensure offline validation includes finalized group/targeting rules.

- Verify case-insensitive exact name resolution.
- Verify global namespace collisions are blocked across devices and groups.
- Verify `active` exists, is reserved, and is reset on save/commit.
- Verify membership set semantics and warning/no-op behavior.
- Verify delete protections for referenced groups/devices.
- Verify non-interactive copy to existing named group fails without mutation.

## Scope
Purpose: Define what is covered by this plan.
- CLI local config lifecycle (load, edit, validate, save).
- Topology editor open/save of `bringup_system.json`.
- Offline reports for topology, profiles, and visibility (local-only).
- Sanity check of CLI grammar regeneration output (optional).

## Non-Goals
Purpose: Define what is not covered.
- Live CAN capture or NetworkTables publishing.
- TCP UI command path or roboRIO bringup behavior.
- Device motion, motor outputs, or hardware safety tests.

## Preconditions
Purpose: Ensure a stable starting point.
- Windows host with Python available.
- Repo root is the working directory.
- A known-good `bringup_system.json` exists in `src\main\deploy\`.

## Files and Paths
Purpose: List the files used by this plan.
- Profiles and devices table: `src\main\deploy\bringup_system.json`
- Bindings: `src\main\deploy\bringup_bindings.json`
- CLI entry: `python -m tools.can_nt.can_nt_bridge --cli`
- Topology editor: `python -m tools.can_topology.can_top_editor`

## Phase 1: CLI Local-Only Sanity
Purpose: Prove the CLI runs in local mode without NT/CAN.

Steps:
1. Start CLI in offline mode.
```powershell
cd %USERPROFILE%\swerveBringupMotorTest\swerveBringupMotorTest1
python -m tools.can_nt.can_nt_bridge --cli --no-can --no-nt
```

Example Output:
```
%USERPROFILE%\swerveBringupMotorTest\swerveBringupMotorTest1>python -m tools.can_nt.can_nt_bridge --cli --no-can --no-nt
Version
can_nt_bridge: 0.1.1
git: status_codes-2026-04-02-dirty
git-sha: b04255a
git-branch: status_codes
git-dirty: dirty
build-time: 2026-04-02T14:10:52-04:00
Profiles data_version: 2026-04-04_012756
Profiles data_hash: dfdb7d0d17835ab07197d46cab313ee6a55818cb4b5d3043caaf366301052013
Source default disabled; marking unavailable.
Version
bridge_cli: 0.3.0
git: status_codes-2026-04-02-dirty
git-sha: b04255a
git-branch: status_codes
git-dirty: dirty
build-time: 2026-04-02T14:10:52-04:00
Loaded 0 group(s) for profile home_031226 from %USERPROFILE%\swerveBringupMotorTest\swerveBringupMotorTest1\data\bringup_system.json.
WARNING: Robot not connected; local config loaded only.
Loaded default profiles: %USERPROFILE%\swerveBringupMotorTest\swerveBringupMotorTest1\data\bringup_system.json
Loaded bindings: %USERPROFILE%\swerveBringupMotorTest\swerveBringupMotorTest1\src\main\deploy\bringup_bindings.json
Loaded CAN mappings: %USERPROFILE%\swerveBringupMotorTest\swerveBringupMotorTest1\src\main\deploy\can_mappings.json
bridge-profile-home_031226>
```


2. Confirm local workspace and profiles.
```
show workspace
show profiles
show profile
show devices
```
Example Output:
```
bridge-profile-home_031226> show workspace
Profiles: %USERPROFILE%\swerveBringupMotorTest\swerveBringupMotorTest1\data\bringup_system.json (loaded)
Active profile: home_031226
Default profile: home_031226
Active context: source=local profile=home_031226 testSet=(none) selectedDevice=(none) selectedMode=off
Tests: %USERPROFILE%\swerveBringupMotorTest\swerveBringupMotorTest1\data\bringup_system.json (not loaded)
Active set: (none) (default=(none))
Bindings: %USERPROFILE%\swerveBringupMotorTest\swerveBringupMotorTest1\src\main\deploy\bringup_bindings.json (loaded)
Mappings: %USERPROFILE%\swerveBringupMotorTest\swerveBringupMotorTest1\src\main\deploy\can_mappings.json (loaded)
Dirty: profiles=False tests=False bindings=False mappings=False
CLI: messages=beginner echo=off
Recovery mode: OFF
SUCCESS [EXECUTOR.SUCCESS]
DETAIL: Success.
bridge-profile-home_031226> show profiles
SOURCE: local
Local profiles:
  home_031226
SUCCESS [EXECUTOR.SUCCESS]
DETAIL: Success.
bridge-profile-home_031226> show profile home_031226
SOURCE: local
Local profile:
  name=home_031226
  devices=7
    SPARKMAX/NEO 25
    lmtSw1
    SPARKMAX/NEO550 7
    FALCON 9
    candle
    PDH
    roboRIO
SUCCESS [EXECUTOR.SUCCESS]
DETAIL: Success.
bridge-profile-home_031226> show devices
SOURCE: local
Local devices-table entries:
  SPARKMAX/NEO 25
  lmtSw1
  SPARKMAX/NEO550 7
  FALCON 9
  candle
  PDH
  roboRIO
SUCCESS [EXECUTOR.SUCCESS]
DETAIL: Success.
bridge-profile-home_031226>
```

3. Validate local profiles.
```
validate profiles local --active
```

Example Output:
```
This command must be in configure mode to work:
bridge-profile-home_031226> configure terminal
SUCCESS [EXECUTOR.SUCCESS]
DETAIL: Success.
bridge(config-profile-home_031226)# validate profiles local --active
OK: Config is valid.
SUCCESS [CONFIG.VALID]
DETAIL: Config valid.
bridge(config-profile-home_031226)#
```


Expected:
- CLI starts without NT or CAN errors.
- `show profiles` lists profiles from `bringup_system.json`.
- `validate profiles local --active` succeeds.

## Phase 2: Local Config Edit and Save
Purpose: Verify local-only edits and persistence.

Steps:
1. Enter the group context and add a member + binding.
```
group test_group
add device "SPARKMAX/NEO 25"
bind controller0.A hold 0.2
show group test_group local
exit
```
2. Export to a local file.
```
export runtime-groups local tools\can_nt\logs\offline_groups.json
```

Example Output:
```
bridge(config-profile-home_031226-group-test_group)# show group test_group local
SOURCE: local
Local group test_group (profile (none)):
  enabled=true
  members=1
  bindings=1
  members:
    SPARKMAX/NEO 25 (enabled)
SUCCESS [EXECUTOR.SUCCESS]
DETAIL: Success.
bridge(config-profile-home_031226-group-test_group)# exit
WARNING: Unsaved changes in: groups.
SUCCESS [EXECUTOR.SUCCESS]
DETAIL: Success.
bridge(config-profile-home_031226)# export runtime-groups local tools\can_nt\logs\offline_groups.json
Wrote runtime groups to tools\can_nt\logs\offline_groups.json.
SUCCESS [EXECUTOR.SUCCESS]
DETAIL: Success.
bridge(config-profile-home_031226)#
```

3. Save bridge-config only.
```
save bridge-config tools\can_nt\logs\offline_local_config.json
```
Example Output:
```
bridge(config-profile-home_031226)# save bridge-config tools\can_nt\logs\offline_local_config.json
Snapshot created: %USERPROFILE%\swerveBringupMotorTest\swerveBringupMotorTest1\data\backups\offline_local_config.20260407_195312.json
Wrote groups config to tools\can_nt\logs\offline_local_config.json.
Action: save scope=bridge-config persistence=disk source=local
SUCCESS [EXECUTOR.SUCCESS]
DETAIL: Success.
bridge(config-profile-home_031226)#
```

Notes:
- `group create <name>` is not valid syntax in this CLI.
- While in a group context, use `add device "<label>"` (not `add-device`).
- `group <name>` selects the local group context; it creates a local group if missing.

Expected:
- Group appears in local-only outputs.
- Exported JSON files are created and non-empty.

## Phase 3: Topology Editor Round-Trip
Purpose: Ensure diagram metadata survives open/save.

Steps:
1. Launch the editor and open `src\main\deploy\bringup_system.json`.
2. Make a small visible edit (move a node or add a callout).
3. Save to a new file, for example `tools\can_topology\save\offline_roundtrip.json`.
4. Reopen the saved file to confirm the edit persists.

Expected:
- Editor opens without validation errors.
- Saved file includes diagram metadata and passes re-open.

## Phase 4: Visibility Matrix (Local-Only)
Purpose: Confirm local visibility reporting runs without a robot.

Steps:
1. In CLI, run:
```
show visibility summary local
```

Example Output:
```
bridge(config-profile-home_031226)# show visibility summary local
SOURCE: local
Sources: 1
Devices shown: 0
Visible at all sources: 0
Visible at some sources only: 0
Visible at no sources: 0
SUCCESS [EXECUTOR.SUCCESS]
DETAIL: Success.
bridge(config-profile-home_031226)# show visibility local
SOURCE: local
Device  default
Scope: both
Visibility timeout: 1000 ms
Unavailable sources: 1
Legend: Y=visible, N=not visible, ?=source unavailable
SUCCESS [EXECUTOR.SUCCESS]
DETAIL: Success.
bridge(config-profile-home_031226)#
```

Expected:
- Commands return a local visibility matrix and summary, even without live sources.

## Phase 5: Optional Grammar Regeneration Sanity
Purpose: Ensure the grammar pipeline still works offline.

Steps:
1. Regenerate parser artifacts.
```powershell
tools\can_nt\regen_cli_parser.ps1
```
2. Run the local batch sanity test.
```powershell
python -m tools.can_nt.can_nt_bridge --no-can --no-nt --batch --script tools\can_nt\tmp_cli_mixed.txt
```

Expected:
- Parser generation completes.
- Batch script runs without parser errors.

## Example Output Checks
Purpose: Provide quick checks to confirm success.

Examples:
- `show workspace` includes `local` source details and paths.
- `show devices local` lists devices from the devices table filtered by profile context.
- `validate profiles local --active` prints a success message.

## Tradeoffs
Purpose: Document limitations of offline-only testing.
- Offline tests cannot validate live NT/CAN behavior.
- Visibility summaries are based on static local config, not live traffic.

## Future Extensions
Purpose: List safe follow-on improvements.
- Add a canned offline fixture to validate visibility counts deterministically.
- Add a local-only test script that covers every CLI show target.


