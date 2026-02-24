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
- Device tables for `--profile` are loaded from `src/main/deploy/bringup_profiles.json`.

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

# Choose a profile from bringup_profiles.json
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --profile demo_club

# Publish unknown devices seen on the bus
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --profile demo_home_022326 --publish-unknown

# List or dump the published NT keys
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --profile demo_home_022326 --list-keys
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --profile demo_home_022326 --dump-nt tools\nt_keys.json

# List serial ports
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --list-ports
```

Options:
- `--channel` is the CANable COM port (Device Manager shows it). If omitted, the
  script auto-detects the first port whose description contains "USB Serial Device".
- `--interface` defaults to `slcan`.
- `--bitrate` defaults to `1000000` (FRC CAN).
- `--timeout` marks a device missing if no frames arrive in that many seconds.
- `--print-publish` prints when a device is seen or goes missing (uses `--timeout`).
- `--print-summary-period` prints a CAN summary every N seconds (0 disables).
- `--publish-unknown` publishes devices seen on the bus that are not in the profile.
- `--list-keys` prints the NT keys this tool publishes and exits.
- `--dump-nt` writes a JSON list of published NT keys and exits.
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
- `bringup/diag/can/summary/json` (when `--publish-can-summary` is enabled)

## Notes

- The script maps device IDs from the lowest 6 bits of the CAN extended ID.
- `RobotV2` prints a table and shows `status=NO_DATA`, `ageSec=-`, and `msgCount=-`
  until a device has been seen at least once.
- `RobotV2` reads the composite `dev/<mfg>/<type>/<id>` keys.
