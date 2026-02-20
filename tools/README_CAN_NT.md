# CAN -> NetworkTables bridge (RobotV2)

This script listens to CAN traffic from a CANable PRO (SLCAN mode) and publishes
`bringup/diag` diagnostics for `RobotV2`.

## Install

Use one of the NetworkTables libraries:

```powershell
py -m pip install ntcore
```

If `ntcore` is unavailable on your machine, use:

```powershell
py -m pip install pynetworktables
```

Install python-can for the CAN interface:

```powershell
py -m pip install python-can
```

## Run

```powershell
py tools\can_nt_bridge.py --rio 172.22.11.2 --channel COM3 --device-ids 2,5,8,11
```

Options:
- `--channel` is the CANable COM port (Device Manager shows it).
- `--interface` defaults to `slcan`.
- `--bitrate` defaults to `1000000` (FRC CAN).
- `--timeout` marks a device missing if no frames arrive in that many seconds.

## Notes

- The script maps device IDs from the lowest 6 bits of the CAN extended ID.
- `RobotV2` prints `NT: no data` until a device has been seen at least once.
