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

# Generate a profile from observed CAN traffic (writes a bringup_profiles.json file)
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --dump-profile tools\sniffer_profile.json

# Capture API class/index inventory for later diffing
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --dump-api-inventory tools\inventory_a.json --dump-api-inventory-after 5

# Diff two inventories
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --diff-inventory tools\inventory_a.json tools\inventory_b.json
```

Marker capture (pcapng):
- See `reverse_eng.md` for marker usage, key map, and Wireshark filtering.

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
- `--dump-profile` writes a bringup_profiles.json file generated from observed CAN IDs.
- `--dump-profile-name` sets the profile name inside the generated file (default: `sniffer_YYYYMMDD_HHMMSS`).
- `--dump-profile-after` seconds to wait before writing `--dump-profile` output (default: `3.0`).
- `--dump-profile-include-unknown` includes unclassified devices in the output.
- `--dump-api-inventory` writes a JSON inventory of apiClass/apiIndex counts and exits.
- `--dump-api-inventory-after` seconds to wait before writing the inventory (default: `3.0`).
- `--diff-inventory` diffs two inventory JSON files and prints new/missing/changed pairs.
- `--diff-top` number of rows to print for each diff section (default: `10`).
- `--pcap <path>` writes a capture file (use `.pcapng` to enable markers).
- `--enable-markers` or `--disable-markers` toggles keyboard marker injection.
- `--marker-id 0x1FFC0D00` sets the marker arbitration ID (extended).
- `--capture-note "text"` adds a pcapng section header comment.
- `--no-nt` disables all NetworkTables publishing (capture/logging only).

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
- `bringup/diag/can/pc/heartbeat`
- `bringup/diag/can/pc/openOk`
- `bringup/diag/can/pc/framesPerSec`
- `bringup/diag/can/pc/framesTotal`
- `bringup/diag/can/pc/readErrors`
- `bringup/diag/can/pc/lastFrameAgeSec`

## Notes

- The script maps device IDs from the lowest 6 bits of the CAN extended ID.
- Inventory snapshots key on `(manufacturer, device_type, apiClass, apiIndex, device_id)` so
  you can diff experiments and identify command-like vs status frames.
- `--dump-profile` guesses device families from CAN manufacturer/type and cannot
  distinguish NEO vs FLEX or Kraken vs Falcon; it puts those into `neos` and
  `krakens` by default for easy hand edits.
- `RobotV2` prints a table and shows `status=NO_DATA`, `ageSec=-`, and `msgCount=-`
  until a device has been seen at least once.
- `RobotV2` reads the composite `dev/<mfg>/<type>/<id>` keys.
- `can/pc/heartbeat` increments once per publish; `can/pc/lastFrameAgeSec` is seconds since the last frame.
- CANable Pro V2 ships with `slcan` firmware by default; an optional `candlelight` firmware enables `gs_usb` for native CAN on Linux (Cangaroo is a common Windows viewer for candlelight; cantact-app works with slcan).
