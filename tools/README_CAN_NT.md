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
- `--auto-match` sets the substring used to auto-detect the serial device.
- `--no-prompt` disables the port selection prompt when multiple matches are found.
- `--list-ports` prints available serial ports and exits.

Published NetworkTables keys:
- `bringup/diag/busErrorCount`
- `bringup/diag/lastSeen/<deviceId>`
- `bringup/diag/missing/<deviceId>`
- `bringup/diag/msgCount/<deviceId>`
- `bringup/diag/type/<deviceId>` (label string: type or custom name)
- `bringup/diag/status/<deviceId>` (OK/STALE/MISSING)
- `bringup/diag/ageSec/<deviceId>` (-1 if missing)

## Notes

- The script maps device IDs from the lowest 6 bits of the CAN extended ID.
- `RobotV2` prints `NT: no data` until a device has been seen at least once.
- The `--device-ids` list should include the CANCoder CAN IDs to track them.
- `msgCount/<deviceId>` reports the total number of frames seen for that ID.
