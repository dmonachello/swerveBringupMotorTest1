# Swerve Bringup Motor Test

Bringup and diagnostics project for swerve motors and other CAN devices.

## Purpose
Use this project to:
- Add motors incrementally or all at once.
- Command NEO, FLEX/VORTEX, KRAKEN, and FALCON motors from an Xbox controller.
- Print health and CAN sniffer diagnostics.
- Read and verify CANCoder absolute positions.

## Run
Use the normal WPILib workflow to deploy and run the robot code.

## CAN Profiles (JSON)
Bringup hardware profiles are defined in `src/main/deploy/bringup_profiles.json`.

- `default_profile` controls the startup profile.
- Profiles are applied in the order they appear in the JSON when you press `Back` to toggle.
- Override at runtime with `--bringup-profile=<name>`.

Supported profile sections include:
- `neos`, `flexes`, `krakens`, `falcons`, `cancoders`
- `pdh`, `pdp`, `pigeon`, `roborio`

Manufacturer/type display names are loaded from `src/main/deploy/can_mappings.json`.

## Controller Bindings
Robot and RobotV2 share the same bindings:
- `A`: add motor (alternates SPARK/CTRE)
- `Start`: add all motors + CANCoders
- `B`: print state
- `X`: print health status
- `Y`: print NetworkTables diagnostics (RobotV2 only)
- `Right Bumper`: print CANCoder absolute positions
- `Back`: toggle CAN profile
- `Left Bumper`: reprint bindings
- `Right Stick`: print speed inputs
- `Left Stick`: nudge motors (0.2 for 0.5s)
- `Left Y`: NEO/FLEX speed
- `Right Y`: KRAKEN/FALCON speed

## CAN Sniffer Bridge (CANable Pro V2)
This project includes a CAN -> NetworkTables bridge for diagnostics.

Install:
```cmd
py -m pip install pynetworktables
py -m pip install python-can
py -m pip install pyserial
```

Run:
```cmd
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --rio 172.22.11.2
```

Or use the helper script that pins the Python interpreter:
```cmd
tools\run_can_nt.cmd
```

Override Python for the helper script:
```cmd
set CAN_NT_PYTHON=C:\Path\To\Python\python.exe
tools\run_can_nt.cmd
```

Or pass the interpreter path as the first argument:
```cmd
tools\run_can_nt.cmd C:\Path\To\Python\python.exe
```

Pass extra flags directly:
```cmd
tools\run_can_nt.cmd --print-summary-period 2 --print-publish
```

If you pass a Python path first, flags can follow:
```cmd
tools\run_can_nt.cmd C:\Path\To\Python\python.exe --verbose --quick-check
```

If neither is set, the script will:
1. Use the first `python` found in `PATH`.
2. Fall back to `%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe`.

Config:
- Default settings live in `tools/can_nt_config.json`.
- Override with `--config path\to\file.json`.
- The config supports a `devices` list with `manufacturer`, `device_type`, and `device_id`.
- The config supports `groups` for summary rollups and `log_csv` defaults.
- By default, `tools/can_nt_config.json` enables CSV logging to `tools\can_nt_log.csv`.

Examples:
```cmd
# Default (USB RIO, auto-detect COM port)
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --rio 172.22.11.2

# Explicit COM port
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --rio 172.22.11.2 --channel COM21

# More output (summary + device seen/missing messages)
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --rio 172.22.11.2 --print-summary-period 2 --print-publish

# Use a custom config
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --config tools\can_nt_config.json

# Publish unknown devices seen on the bus
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --profile demo_home_022326 --publish-unknown

# List or dump the published NT keys
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --profile demo_home_022326 --list-keys
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --profile demo_home_022326 --dump-nt tools\nt_keys.json

# List serial ports
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --list-ports
```

Published NetworkTables keys:
- `bringup/diag/busErrorCount`
- `bringup/diag/dev/<mfg>/<type>/<id>/label`
- `bringup/diag/dev/<mfg>/<type>/<id>/status`
- `bringup/diag/dev/<mfg>/<type>/<id>/ageSec`
- `bringup/diag/dev/<mfg>/<type>/<id>/msgCount`
- `bringup/diag/dev/<mfg>/<type>/<id>/lastSeen`
- `bringup/diag/dev/<mfg>/<type>/<id>/manufacturer`
- `bringup/diag/dev/<mfg>/<type>/<id>/deviceType`
- `bringup/diag/dev/<mfg>/<type>/<id>/deviceId`
- Legacy deviceId-only aggregate keys (for backward compatibility):
  - `bringup/diag/lastSeen/<deviceId>`
  - `bringup/diag/missing/<deviceId>`
  - `bringup/diag/msgCount/<deviceId>`
  - `bringup/diag/type/<deviceId>` (always `Mixed`)
  - `bringup/diag/status/<deviceId>` (OK/STALE/MISSING)
  - `bringup/diag/ageSec/<deviceId>` (-1 if missing)

RobotV2 prints these diagnostics when you press `Y`.
It now reads the composite keys under `bringup/diag/dev/<mfg>/<type>/<id>` so
devices with the same numeric ID but different types are handled correctly.

Useful run flags:
- `--print-publish` prints when a device is seen or goes missing (uses `--timeout`).
- `--print-summary-period` prints a CAN summary every N seconds (0 disables).
- `--publish-unknown` publishes devices seen on the bus that are not in the profile.
- `--list-keys` prints the NT keys this tool publishes and exits.
- `--dump-nt` writes a JSON list of published NT keys and exits.
- `--list-ports` prints available serial ports and exits.
- `--auto-match` sets the substring used to auto-detect the serial device.
- `--no-prompt` disables the port selection prompt when multiple matches are found.

## CANCoder Test
Press `Right Bumper` to print absolute position for the configured CANCoder IDs.
This test reads absolute position directly from the devices over CAN and prints
rotations and degrees to the console.

Configured CAN profiles live in:
- `src/main/deploy/bringup_profiles.json`

## Future Features
Ideas to consider:
- Set explicit status frame periods for predictable CAN traffic.
- Add a toggle for continuous CANCoder streaming.
- Add per-device firmware/version reporting.
- Add a pit-mode "quick check" summary line.
- Add a UI dashboard to visualize NetworkTables diagnostics.

## Adding New Features
General workflow:
1. Add or update profiles in `src/main/deploy/bringup_profiles.json`.
2. Put shared behavior in `src/main/java/frc/robot/BringupCore.java`.
3. Bind controls in both `src/main/java/frc/robot/Robot.java` and
   `src/main/java/frc/robot/RobotV2.java`.
4. If you add CAN sniffer data, update `tools/can_nt_bridge.py` and
   `tools/README_CAN_NT.md`.
5. Update this `README.md` with the new behavior and bindings.
