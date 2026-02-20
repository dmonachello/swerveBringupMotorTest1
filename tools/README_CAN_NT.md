# CAN -> NetworkTables bridge (RobotV2)

This script listens to CAN traffic from a CANable PRO (SLCAN mode) and publishes
`bringup/diag` diagnostics for `RobotV2`.

## Install

Use the pure-Python NetworkTables library:

```cmd
py -m pip install pynetworktables
```

Install python-can for the CAN interface:

```cmd
py -m pip install python-can
```

Install pyserial for the slcan interface:

```cmd
py -m pip install pyserial
```

## Run

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
tools\run_can_nt.cmd --verbose --print-summary-period 2
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

# More output (summary + device seen messages)
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --rio 172.22.11.2 --print-summary-period 2 --print-publish

# Quick check (print once and exit)
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --rio 172.22.11.2 --quick-check

# Write CSV log
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --rio 172.22.11.2 --log-csv tools\can_nt_log.csv

# Use a custom config
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --config tools\can_nt_config.json

# List serial ports
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --list-ports
```

Options:
- `--channel` is the CANable COM port (Device Manager shows it). If omitted, the
  script auto-detects the first port whose description contains "USB Serial Device".
- `--interface` defaults to `slcan`.
- `--bitrate` defaults to `1000000` (FRC CAN).
- `--timeout` marks a device missing if no frames arrive in that many seconds.
- `--verbose` prints each received device ID.
- `--print-publish` prints when a device is seen after being missing (uses `--timeout`).
- `--print-summary-period` prints per-device counts/missing every N seconds with timestamps (0 disables).
- `--no-traffic-secs` prints a warning if no CAN frames are seen for N seconds (0 disables).
- `--no-rio-secs` prints a warning if not connected to the RIO for N seconds (0 disables).
- `--log-csv` writes a CSV log file (empty disables).
- `--log-period` sets seconds between CSV rows.
- `--quick-check` prints one summary after `--quick-wait` seconds and exits.
- `--quick-wait` sets the wait time before quick-check output.
- `--device-ids` enables legacy deviceId-only tracking (not recommended for duplicate IDs).
- `--auto-match` sets the substring used to auto-detect the serial device.
- `--no-prompt` disables the port selection prompt when multiple matches are found.
- `--list-ports` prints available serial ports and exits.

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

## Notes

- The script maps device IDs from the lowest 6 bits of the CAN extended ID.
- `RobotV2` prints a table and shows `status=NO_DATA`, `ageSec=-`, and `msgCount=-`
  until a device has been seen at least once.
- The `--device-ids` list should include the CANCoder CAN IDs to track them.
- `msgCount/<deviceId>` reports the total number of frames seen for that ID.
- `RobotV2` reads the composite `dev/<mfg>/<type>/<id>` keys.
