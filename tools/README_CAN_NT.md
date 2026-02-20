# CAN -> NetworkTables bridge (RobotV2)

This script listens to CAN traffic from a CANable PRO (SLCAN mode) and publishes
`bringup/diag` diagnostics for `RobotV2`.

## Install

Use the pure-Python NetworkTables library:

```powershell
py -m pip install pynetworktables
```

Install python-can for the CAN interface:

```powershell
py -m pip install python-can
```

Install pyserial for the slcan interface:

```powershell
py -m pip install pyserial
```

## Run

```powershell
py tools\can_nt_bridge.py --rio 172.22.11.2 --channel COM3 --device-ids 2,5,8,11,12,3,9,6
```

Or use the helper script that pins the Python interpreter:
```powershell
.\tools\run_can_nt.ps1
```

If PowerShell blocks scripts, run:
```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_can_nt.ps1
```

Options:
- `--channel` is the CANable COM port (Device Manager shows it).
- `--interface` defaults to `slcan`.
- `--bitrate` defaults to `1000000` (FRC CAN).
- `--timeout` marks a device missing if no frames arrive in that many seconds.

## Notes

- The script maps device IDs from the lowest 6 bits of the CAN extended ID.
- `RobotV2` prints `NT: no data` until a device has been seen at least once.
- The `--device-ids` list should include the CANCoder CAN IDs to track them.
- `msgCount/<deviceId>` reports the total number of frames seen for that ID.
