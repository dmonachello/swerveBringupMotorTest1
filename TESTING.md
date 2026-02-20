# CAN Sniffer Utility Test Plan

This document provides a step-by-step checklist to verify the CAN -> NetworkTables bridge end-to-end with a real CAN bus and RoboRIO.

## Test Setup

Hardware:
- RoboRIO powered and reachable (USB or network).
- CAN bus wired with at least one NEO (SparkMax), one Kraken (TalonFX), and one CANCoder.
- CANable Pro V2 connected to the CAN bus (CANH, CANL, GND).
- Laptop connected to RIO (USB or network).

Software on laptop:
- Python 3.12 installed at `C:\Users\dmona\AppData\Local\Programs\Python\Python312\python.exe`
- Packages installed:
  - `pynetworktables`
  - `python-can`
  - `pyserial`

Helpful tools:
- Driver Station or a way to confirm RIO is powered and reachable.
- Device Manager to view COM ports.

## Preflight Checklist

1. Confirm RIO is powered and reachable.
2. Confirm CANable is detected in Device Manager under **Ports (COM & LPT)**.
3. Confirm the CAN bus has at least one active device sending frames.

## Commands Used (CMD)

Default run:
```cmd
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --rio 172.22.11.2
```

Verbose + summary:
```cmd
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --rio 172.22.11.2 --print-summary-period 2 --print-publish --verbose
```

Quick check:
```cmd
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --rio 172.22.11.2 --quick-check
```

CSV logging:
```cmd
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --rio 172.22.11.2 --log-csv tools\can_nt_log.csv
```

List ports:
```cmd
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --list-ports
```

## Functional Tests

### 1) Auto-detect COM port
Steps:
1. Unplug all USB serial devices except the CANable.
2. Run the default command (no `--channel`).
Expected:
- Startup banner shows `Auto-detected CAN channel: COMx (...)`.
- `CAN: interface=slcan channel=COMx bitrate=1000000` shows the same COM port.

Failure hints:
- If multiple ports match, script should prompt for selection.
- If none match, script should exit with a clear error.

### 2) RIO connection diagnostics
Steps:
1. Run the default command with the RIO connected.
Expected:
- Startup shows `RIO IP: ...` and `NT status: connected to RIO`.
- `NT details:` prints remote/connection info.

Negative test:
1. Disconnect RIO or use a bad `--rio`.
Expected:
- `NT status: NOT connected to RIO`.
- Periodic warning: `Not connected to RIO NetworkTables as of HH:MM:SS.`

### 3) No CAN traffic warning
Steps:
1. Run the tool with CANable connected but CAN bus powered off.
Expected:
- Periodic warning: `No CAN traffic detected as of HH:MM:SS.`

### 4) Device IDs, manufacturer/type, and labels
Steps:
1. Ensure the CAN bus contains devices with IDs defined in `tools/can_nt_config.json`.
2. Run with summaries enabled.
Expected:
- Each device prints its label (e.g., `FR NEO`, `FL KRAK`, `FR CANC`).
- Same numeric IDs across different device types still show as separate entries.
- `status` is `OK` when active; `STALE` after timeout; `MISSING` if never seen.

### 5) `--print-publish` behavior
Steps:
1. Run with `--print-publish`.
2. Power-cycle one CAN device so it drops off the bus and returns.
Expected:
- When it returns after timeout, a line prints:
  `Device seen: mfg=XX type=YY id=ZZ count=NN`

### 6) Summary output formatting
Steps:
1. Run with `--print-summary-period 2`.
Expected:
- Multi-line summary appears every 2 seconds.
- Contains `Pit check` line with seen/missing count, frames/sec, errors/sec.
- Includes group lines if groups are configured.

### 7) Groups rollup
Steps:
1. Check `tools/can_nt_config.json` `groups` section.
2. Run with summary enabled.
Expected:
- Lines like `Group neos: seen=4/4 missing=0`.
- Counts should change as devices drop out or reappear.

### 8) NetworkTables keys
Steps:
1. Run tool and view NT values (e.g., NT client or RobotV2 Y button).
Expected keys under `bringup/diag`:
- `busErrorCount`
- `dev/<mfg>/<type>/<id>/label`
- `dev/<mfg>/<type>/<id>/status`
- `dev/<mfg>/<type>/<id>/ageSec`
- `dev/<mfg>/<type>/<id>/msgCount`
- `dev/<mfg>/<type>/<id>/lastSeen`
- `dev/<mfg>/<type>/<id>/manufacturer`
- `dev/<mfg>/<type>/<id>/deviceType`
- `dev/<mfg>/<type>/<id>/deviceId`
RobotV2 uses the composite `dev/<mfg>/<type>/<id>` keys.

Legacy deviceId-only aggregate keys:
  - `lastSeen/<id>`
  - `missing/<id>`
  - `msgCount/<id>`
  - `type/<id>` (always `Mixed`)
  - `status/<id>` (OK/STALE/MISSING)
  - `ageSec/<id>` (-1 if missing)

### 9) CSV logging
Steps:
1. Run with `--log-csv tools\can_nt_log.csv`.
2. Let it run for at least 5 seconds, then stop.
Expected:
- File `tools\can_nt_log.csv` exists and has a header row.
- Each subsequent row has timestamp, busErrorCount, framesPerSec, errorsPerSec.
- Per-ID columns include count, ageSec, and status.

### 10) Quick check mode
Steps:
1. Run with `--quick-check`.
Expected:
- Tool waits for `--quick-wait` seconds (default 1.0).
- Prints a single summary and exits.

## Troubleshooting

If no frames are received:
- Verify CANable wiring to CANH/CANL/GND.
- Verify bus power and termination.
- Confirm the correct COM port.
- Confirm the CANable firmware is in SLCAN mode.

If NT is not connected:
- Verify RIO IP and connectivity.
- Confirm the RIO is running robot code and NT server is active.

If imports fail:
- Use the explicit Python path shown above.

## Pass/Fail Record

Use this section to record test outcomes:

- Auto-detect COM: PASS / FAIL
- RIO connection: PASS / FAIL
- No CAN traffic warning: PASS / FAIL
- Device labels/status: PASS / FAIL
- Print-publish: PASS / FAIL
- Summary formatting: PASS / FAIL
- Groups rollup: PASS / FAIL
- NetworkTables keys: PASS / FAIL
- CSV logging: PASS / FAIL
- Quick check: PASS / FAIL
