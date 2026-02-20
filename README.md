# Swerve Bringup Motor Test

Bringup and diagnostics project for swerve motors and other CAN devices.

## Purpose
Use this project to:
- Add motors incrementally or all at once.
- Command NEO and KRAKEN motors from an Xbox controller.
- Print health and CAN sniffer diagnostics.
- Read and verify CANCoder absolute positions.

## Run
Use the normal WPILib workflow to deploy and run the robot code.

## Controller Bindings
Robot and RobotV2 share the same bindings:
- `A`: add motor (alternates NEO/KRAKEN)
- `Start`: add all motors + CANCoders
- `B`: print state
- `X`: print health status
- `Y`: print NetworkTables diagnostics (RobotV2 only)
- `Right Bumper`: print CANCoder absolute positions
- `Left Y`: NEO speed
- `Right Y`: KRAKEN speed

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
C:\Users\dmona\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --rio 172.22.11.2
```

Or use the helper script that pins the Python interpreter:
```cmd
tools\run_can_nt.cmd
```

Config:
- Default settings live in `tools/can_nt_config.json`.
- Override with `--config path\to\file.json`.
- The config supports a `labels` map to name devices by ID.
- The config supports `groups` for summary rollups and `log_csv` defaults.
- By default, `tools/can_nt_config.json` enables CSV logging to `tools\can_nt_log.csv`.

Examples:
```cmd
# Default (USB RIO, auto-detect COM port)
C:\Users\dmona\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --rio 172.22.11.2

# Explicit COM port
C:\Users\dmona\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --rio 172.22.11.2 --channel COM21

# More output (summary + device seen messages)
C:\Users\dmona\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --rio 172.22.11.2 --print-summary-period 2 --print-publish

# Quick check (print once and exit)
C:\Users\dmona\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --rio 172.22.11.2 --quick-check

# Write CSV log
C:\Users\dmona\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --rio 172.22.11.2 --log-csv tools\can_nt_log.csv

# Use a custom config
C:\Users\dmona\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --config tools\can_nt_config.json

# List serial ports
C:\Users\dmona\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --list-ports
```

Published NetworkTables keys:
- `bringup/diag/busErrorCount`
- `bringup/diag/lastSeen/<deviceId>`
- `bringup/diag/missing/<deviceId>`
- `bringup/diag/msgCount/<deviceId>`
- `bringup/diag/type/<deviceId>` (label string: type or custom name)
- `bringup/diag/status/<deviceId>` (OK/STALE/MISSING)
- `bringup/diag/ageSec/<deviceId>` (-1 if missing)

RobotV2 prints these diagnostics when you press `Y`.

Useful run flags:
- `--verbose` prints each received device ID.
- `--print-publish` prints when a device is seen after being missing (uses `--timeout`).
- `--print-summary-period` prints per-device counts/missing every N seconds with timestamps (0 disables).
- `--no-traffic-secs` prints a warning if no CAN frames are seen for N seconds (0 disables).
- `--no-rio-secs` prints a warning if not connected to the RIO for N seconds (0 disables).
- `--log-csv` writes a CSV log file (empty disables).
- `--log-period` sets seconds between CSV rows.
- `--quick-check` prints one summary after `--quick-wait` seconds and exits.
- `--quick-wait` sets the wait time before quick-check output.
- `--list-ports` prints available serial ports and exits.
- `--auto-match` sets the substring used to auto-detect the serial device.
- `--no-prompt` disables the port selection prompt when multiple matches are found.

## CANCoder Test
Press `Right Bumper` to print absolute position for the configured CANCoder IDs.
This test reads absolute position directly from the devices over CAN and prints
rotations and degrees to the console.

Configured CAN IDs live in:
- `src/main/java/frc/robot/BringupUtil.java`

## Future Features
Ideas to consider:
- Set explicit status frame periods for predictable CAN traffic.
- Add a toggle for continuous CANCoder streaming.
- Add per-device firmware/version reporting.
- Add a pit-mode "quick check" summary line.
- Add a UI dashboard to visualize NetworkTables diagnostics.

## Adding New Features
General workflow:
1. Add or update constants in `src/main/java/frc/robot/BringupUtil.java`.
2. Put shared behavior in `src/main/java/frc/robot/BringupCore.java`.
3. Bind controls in both `src/main/java/frc/robot/Robot.java` and
   `src/main/java/frc/robot/RobotV2.java`.
4. If you add CAN sniffer data, update `tools/can_nt_bridge.py` and
   `tools/README_CAN_NT.md`.
5. Update this `README.md` with the new behavior and bindings.
