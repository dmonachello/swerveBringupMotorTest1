# Test Plan (Today)

## Purpose
Validate the new storage layers (JsonStore + Schema Store) and their CLI/UI integrations with explicit commands.

## Preconditions
- Repo root: `C:\Users\dmona\swerveBringupMotorTest\swerveBringupMotorTest1`
- Python available on PATH.
- Use `--no-can --no-nt` for local CLI testing.

## Testing Notes Workflow
Purpose: keep multiple test passes clean while preserving prior results.

- Add new notes under `SID_COMMENT:` during a fresh pass.
- After each pass, replace `SID_COMMENT:` with `TESTING_RESULTS:` to archive the run.
- Leave `TESTING_RESULTS:` blocks in place; only `SID_COMMENT:` should be reused for the next pass.

---

## Updates (Findings + Fixes)
Purpose: capture what was learned and corrected during this test pass.

TESTING_RESULTS:
- A6 requires NT: `diagnose motor` fails in local-only mode; use `--rio` with NT enabled.
- UI requires NT: `--ui --no-nt` is invalid; run UI with `--rio <ip>`.
- Live topology view: `python -m tools.can_topology.live_topology_view` exits (no entrypoint). Removed from today’s plan.
- Topology editor DIO behavior:
  - DIO devices render on a DIO rail (off the CAN bus).
  - DIO wire anchors top-center of roboRIO to top-center of the DIO box.
  - Attachment links use actual box bounds for consistent endpoints.
  - DIO missing attachment/wire warns on save (no longer invalid).
  - DIO drag no longer jumps at drag start or release.
  - DIO layout persistence fixed with `dioFreeYMode` and migration on load.
- Legend: link semantics added (attachment, DIO wire, CAN bus).
- Label rename:
  - CLI `rename device` auto-updates references and prints INFO summary.
  - Topology editor shows a rename confirmation and updates references on accept.

---

## A) CLI Tests (Explicit Commands)

### A1) Start the CLI (local only)
```
cd C:\Users\dmona\swerveBringupMotorTest\swerveBringupMotorTest1
python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt
```

Expected:
- CLI prompt appears.
- No crash.

### A2) Validate local config (Schema Store path)
Commands:
```
configure terminal
validate config
end
```

Expected:
- `OK: Config is valid.` or explicit error list with locations.

TESTING_RESULTS:
Observed: Local CLI config mode enters successfully.

bridge-profile-home_031226> configure terminal
SUCCESS [EXECUTOR.SUCCESS]
DETAIL: Success.
bridge(config-profile-home_031226)# validate config
OK: Config is valid.
SUCCESS [CONFIG.VALID]
DETAIL: Config valid.
bridge(config-profile-home_031226)#


### A3) Validate bindings (Schema Store path)
Commands:
```
configure terminal
bindings validate
end
```

Expected:
- `OK: Config is valid.` or a bindings-specific error list.

TESTING_RESULTS:
Observed: Bindings validation reports OK (both spellings tested).

bridge(config-profile-home_031226)# bindings validate
OK: Config is valid.
SUCCESS [CONFIG.VALID]
DETAIL: Config valid.
bridge(config-profile-home_031226)# validate bindings
OK: Config is valid.
SUCCESS [CONFIG.VALID]
DETAIL: Config valid.
bridge(config-profile-home_031226)#


### A4) Validate CAN mappings (Schema Store path)
Commands:
```
configure terminal
can-mappings validate
end
```

TESTING_RESULTS:
Observed: CAN mappings validation reports OK and show works.

bridge(config-profile-home_031226)# can-mappings validate
OK: Config is valid.
SUCCESS [CONFIG.VALID]
DETAIL: Config valid.
bridge(config-profile-home_031226)# vali can-mappings
OK: Config is valid.
SUCCESS [CONFIG.VALID]
DETAIL: Config valid.
bridge(config-profile-home_031226)# show can-mappings
SOURCE: local
Local CAN mappings:
  manufacturers:
    0=Broadcast
    1=NI
    2=LuminaryMicro
    3=DEKA
    4=CTRE
    5=REV
    6=Grapple
    7=MindSensors
    8=TeamUse
    9=KauaiLabs
    10=Copperforge
    11=PlayingWithFusion
    12=Studica
    13=TheThriftyBot
    14=ReduxRobotics
    15=AndyMark
    16=VividHosting
    17=VertosRobotics
    18=SWYFTRobotics
    19=LumynLabs
    20=BrushlandLabs
  device-types:
    0=BroadcastMessages
    1=RobotController
    2=MotorController
    3=RelayController
    4=GyroSensor
    5=Accelerometer
    6=DistanceSensor
    7=Encoder
    8=PowerDistributionModule
    9=PneumaticsController
    10=Miscellaneous
    11=IOBreakout
    12=ServoController
    13=ColorSensor
    31=FirmwareUpdate
SUCCESS [EXECUTOR.SUCCESS]
DETAIL: Success.
bridge(config-profile-home_031226)#



Expected:
- `OK: Config is valid.` or a mappings-specific error list.

### A5) Show dirty state
Commands:
```
show config dirty
```

Expected:
- `Local dirty state:` block prints all dirty flags.

TESTING_RESULTS:
Observed: Dirty state is clean after validation-only operations.

bridge(config-profile-home_031226)# show config dirty
SOURCE: local
Local dirty state:
  bindings=false
  can-mappings=false
  groups=false
  profiles=false
  tests=false
  (clean)
SUCCESS [EXECUTOR.SUCCESS]
DETAIL: Success.
bridge(config-profile-home_031226)#


### A6) Diagnose motor (runtime-state required)
Note:
- This step requires a live NetworkTables connection to the roboRIO.
- Do not use `--no-nt` for this step; restart the CLI with NT enabled.

Commands:
```
python tools\can_nt\can_nt_bridge.py --cli --no-can --rio 172.22.11.2
connect
diagnose motor "Drive Motor (id 2)"
```

Expected:
- Prints a `Likely causes:` block with ranked causes.
- If telemetry is missing, prints `UNKNOWN` and a `Missing fields:` list.

---

TESTING_RESULTS:
Observed: Startup prints a warning before `connect` runs.
Explanation: The CLI loads local config first and only connects after you issue `connect`, so the warning is expected until then.

C:\Users\dmona\swerveBringupMotorTest1-main>python tools\can_nt\can_nt_bridge.py --cli --no-can --rio 172.22.11.2
Version
can_nt_bridge: 0.1.1
git: status_codes-2026-04-02-dirty
git-sha: b04255a
git-branch: status_codes
git-dirty: dirty
build-time: 2026-04-02T14:10:52-04:00
Profiles data_version: 2026-04-03_001836
Profiles data_hash: 77d4dadc64d7656ab13d7cfed6d8242254785e990645cf342d28a2090c744374
Version
bridge_cli: 0.3.0
git: status_codes-2026-04-02-dirty
git-sha: b04255a
git-branch: status_codes
git-dirty: dirty
build-time: 2026-04-02T14:10:52-04:00
Loaded 0 group(s) for profile home_031226 from C:\Users\dmona\swerveBringupMotorTest1-main\data\bringup_system.json.
WARNING: Robot not connected; local config loaded only.
Loaded default profiles: C:\Users\dmona\swerveBringupMotorTest1-main\data\bringup_system.json
Loaded bindings: C:\Users\dmona\swerveBringupMotorTest1-main\src\main\deploy\bringup_bindings.json
Loaded CAN mappings: C:\Users\dmona\swerveBringupMotorTest1-main\src\main\deploy\can_mappings.json
bridge-profile-home_031226>


## B) UI Tests

### B1) Bridge UI loads tests from store
Command:
```
cd C:\Users\dmona\swerveBringupMotorTest\swerveBringupMotorTest1
python tools\can_nt\can_nt_bridge.py --ui --no-can --rio 172.22.11.2
```

Expected:
- Test list populates.
- If root `bringup_tests.json` exists, it is preferred over deploy copy.

TESTING_RESULTS:
Observed: UI launches when started with NT enabled (`--rio <ip>`), and the test list populates.

C:\Users\dmona\swerveBringupMotorTest1-main>

## C) Topology Editor Tests

### C1) Open default profile path (store-backed)
Command:
```
cd C:\Users\dmona\swerveBringupMotorTest\swerveBringupMotorTest1
python -m tools.can_topology.can_top_editor
```

Actions:
- File ? Open Profile
- Select `data\bringup_system.json`

Expected:
- Loads without error.
- Device registry and profiles populate.

---

## D) Regression Compile Checks
Command:
```
cd C:\Users\dmona\swerveBringupMotorTest\swerveBringupMotorTest1
python -m py_compile tools\config\json_store.py tools\config\schema_store.py tools\config\config_store.py tools\can_nt\bridge_cli.py tools\can_nt\bringup_ui.py tools\can_topology\live_topology_view.py tools\can_topology\can_top_editor.py
```

Expected:
- No syntax errors.

