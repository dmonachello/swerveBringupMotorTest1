# Setup

## Purpose

Get the robot (Java, roboRIO) and PC tool (Python, Windows CANable) running with a repeatable workflow that does not turn setup into guesswork.

## Scope

- Windows host PC (Driver Station laptop): Python tools, CANable sniffer, optional UI/CLI.
- roboRIO: WPILib Java bringup harness.
- Preferred host-to-robot connection for setup: USB to the roboRIO using `172.22.11.2`.

## Get the repo

If you do not already have the project on disk, clone it from GitHub first.

```powershell
git clone https://github.com/dmonachello/swerveBringupMotorTest1.git
cd swerveBringupMotorTest1
```

If you downloaded a ZIP instead, extract it and open the extracted folder in your terminal before continuing.

## Repo quickstart (Windows)

Use this to verify the tooling works before you touch robot hardware.

1. Install Python deps:

```powershell
.\install_windows.cmd
```

2. Validate config:

```powershell
python -m tools.validate_sync
```

3. Sanity-check the PC tool starts (offline):

```powershell
python -m tools.can_nt.can_nt_bridge --version
python -m tools.can_nt.can_nt_bridge --cli --no-can
```

## PC tool setup (Windows)

Use this section to run passive CAN sniffing and host-side diagnostics on Windows.

### Hardware

- CANable (slcan firmware, COM port).
- CAN bus bitrate: 1,000,000 (FRC).

### Install dependencies

This keeps setup consistent across laptops.

- Preferred: `.\install_windows.cmd`
- Alternative (manual): `python -m pip install -r <requirements>` is not currently provided; the repo uses `install_windows.ps1` dependency list.

What `.\install_windows.cmd` changes on your system:

- Runs `install_windows.ps1` through PowerShell with `-ExecutionPolicy Bypass` for that invocation.
- Uses `python -m pip install --upgrade pip` to upgrade `pip` for the selected Python interpreter.
- Installs or upgrades these Python packages into that interpreter's environment:
  - `python-can==4.4.2`
  - `pyserial==3.5`
  - `prompt_toolkit==3.0.51`
  - `reportlab==4.2.2`
  - `lark==1.2.2`
- Creates these repo-local directories if they do not already exist:
  - `tools/can_nt/logs`
  - `tools/can_nt/captures`

What it does not do:

- Does not clone the repo.
- Does not install WPILib or the JDK.
- Does not build or deploy robot code.
- Does not edit system environment variables.
- Does not install a global Windows service or scheduled task.
- Does not transmit CAN traffic.

### Common invocations

Use module-based entrypoints. They travel better on Windows.

- List COM ports:

```powershell
python -m tools.can_nt.can_nt_bridge --list-ports
```

- Run with CAN + host diagnostics:

```powershell
python -m tools.can_nt.can_nt_bridge --rio 172.22.11.2
```

- Run UI (if enabled in this repo version):

```powershell
python -m tools.can_nt.can_nt_bridge --ui --rio 172.22.11.2
```

Notes:
- The PC tool is read-only on CAN by design.
- If the CANable is connected, the tool can autodetect the serial channel by description.
- For first setup, prefer a direct USB connection to the roboRIO and use `--rio 172.22.11.2`.
- If CAN is unavailable, you can use `--no-can` for offline validation.

## Robot setup (WPILib Java, roboRIO)

Build and deploy the bringup harness with the standard GradleRIO workflow.

The robot Java app uses the current WPILib/FRC VS Code installation as its expected development environment.

### Requirements

- WPILib installed (matching the season / project).
- Current WPILib/FRC VS Code environment installed and working.
- JDK per WPILib requirements.
- If Java tests run on Windows, `JAVA_HOME` should point at the JDK root, not the `bin` directory.

### Build

Command-line build:

```powershell
.\gradlew.bat build
```

What this build does:

- Runs the normal Gradle/WPILib Java compile pipeline for the robot app.
- Runs the Java unit test task as part of the build.
- Regenerates build metadata before Java compilation.
- Produces the build outputs used by the normal GradleRIO workflow.

What it does not do automatically:

- It does not run the maintained Python regression bundles.
- It does not run the connected robot regression.
- It does not deploy code to the roboRIO.

WPILib VS Code build path:

1. Open the repo in the current WPILib/FRC VS Code environment.
2. Open the command palette.
3. Run the WPILib build command for robot code.
4. Use that when you want the standard WPILib editor workflow instead of the terminal.

Recommended follow-up verification after a successful build:

- Run the maintained local regression bundle:

```powershell
python tools/can_nt/scripts/run_regressions.py --suite local
```

- If you only changed Java code and want the narrow Java surface first:

```powershell
python tools/can_nt/scripts/run_regressions.py --suite java
```

- If you need the connected robot REST/UI regression after deploying to a real roboRIO:

```powershell
python tools/can_nt/scripts/run_regressions.py --suite robot-non-motion --rio 172.22.11.2
```

### Deploy

Push robot code and deploy JSON config files.

- Deploy from VS Code through the WPILib deploy command, or:

```powershell
.\gradlew.bat deploy
```

Typical deploy flow:

1. Connect to the roboRIO over USB.
2. Confirm the roboRIO is reachable at `172.22.11.2`.
3. Build first.
4. Deploy from VS Code or run `.\gradlew.bat deploy`.
5. After deploy, run the connected non-motion regression if the change touched robot command/UI behavior.

Notes:
- `src/main/deploy/bringup_system.json` is the active host and roboRIO config file.
- `backup_data/backups/` stores timestamped snapshots created by save operations.

## Device config + tests authoring (happy path)

This is the fastest path that is still hard to mess up.

1. Edit devices table + profiles:
   - Topology editor: `python -m tools.can_topology.can_top_editor`
2. Create/update bringup tests:
   - Bridge CLI/UI authoring (primary), or
   - Smoke generation wizard (motors): `py -m tools.bringup_test_wizard.gen_bringup_tests --profile <name> --test-set smoke --replace`
3. Validate:

```powershell
python -m tools.validate_sync
```

## Troubleshooting

Short, practical fixes.

- `--version` crashes:
  - Run `python tools\\can_nt\\gen_bridge_cli_parser.py` to regenerate CLI constants/grammar.
- Can’t open COM port:
  - Confirm the CANable shows up in Device Manager and use `--list-ports`.
- “data_hash mismatch”:
  - Run `python -m tools.validate_sync`.
