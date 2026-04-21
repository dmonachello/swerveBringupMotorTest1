# Setup

## Purpose
Get the robot (Java, roboRIO) and PC tool (Python, Windows CANable) running with a repeatable, low-friction workflow.

## Scope
- Windows host PC (Driver Station laptop): Python tools, CANable sniffer, optional UI/CLI.
- roboRIO: WPILib Java bringup harness.

## Repo Quickstart (Windows)
Purpose: Verify the tooling works without touching robot hardware.

1. Install Python deps:
```powershell
.\install_windows.cmd
```

2. Validate + sync config to deploy:
```powershell
python -m tools.validate_sync
```

3. Sanity-check the PC tool starts (offline):
```powershell
python -m tools.can_nt.can_nt_bridge --version
python -m tools.can_nt.can_nt_bridge --cli --no-can --no-nt
```

## PC Tool Setup (Windows)
Purpose: Run passive CAN sniffing and publish diagnostics to NetworkTables.

### Hardware
- CANable (slcan firmware, COM port).
- CAN bus bitrate: 1,000,000 (FRC).

### Install Dependencies
Purpose: Avoid “works on one laptop” installs.

- Preferred: `.\install_windows.cmd`
- Alternative (manual): `python -m pip install -r <requirements>` is not currently provided; the repo uses `install_windows.ps1` dependency list.

### Common Invocations
Purpose: Use module-based entrypoints (portable on Windows).

- List COM ports:
```powershell
python -m tools.can_nt.can_nt_bridge --list-ports
```

- Run with CAN + NT:
```powershell
python -m tools.can_nt.can_nt_bridge --rio 10.xx.yy.2 --port COM5
```

- Run UI (if enabled in this repo version):
```powershell
python -m tools.can_nt.can_nt_bridge --ui --rio 10.xx.yy.2 --port COM5
```

Notes:
- The PC tool is read-only on CAN by design.
- If CAN or NT are unavailable, you can use `--no-can` and/or `--no-nt` for offline validation.

## Robot Setup (WPILib Java, roboRIO)
Purpose: Build and deploy the bringup harness using the standard GradleRIO workflow.

### Requirements
- WPILib installed (matching the season / project).
- JDK per WPILib requirements.

### Build
```powershell
.\gradlew.bat build
```

### Deploy
Purpose: Push robot code and deploy JSON config files.

- Deploy from VS Code (WPILib extension) or:
```powershell
.\gradlew.bat deploy
```

Notes:
- `src/main/deploy/bringup_system.json` is the deploy copy used by the roboRIO.
- Keep it in sync with the canonical `data/bringup_system.json` by running `python -m tools.validate_sync`.

## Device Config + Tests Authoring (Happy Path)
Purpose: Make edits fast and hard to mess up.

1. Edit devices table + profiles:
   - Topology editor: `python -m tools.can_topology.can_top_editor`
2. Create/update bringup tests:
   - Bridge CLI/UI authoring (primary), or
   - Smoke generation wizard (motors): `py -m tools.bringup_test_wizard.gen_bringup_tests --profile <name> --test-set smoke --replace`
3. Validate + sync:
```powershell
python -m tools.validate_sync
```

## Troubleshooting
Purpose: Short, practical fixes.

- `--version` crashes:
  - Run `python tools\\can_nt\\gen_bridge_cli_parser.py` to regenerate CLI constants/grammar.
- Can’t open COM port:
  - Confirm the CANable shows up in Device Manager and use `--list-ports`.
- “data_hash mismatch”:
  - Run `python -m tools.validate_sync`.
