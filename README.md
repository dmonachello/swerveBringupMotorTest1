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
```powershell
py -m pip install pynetworktables
py -m pip install python-can
py -m pip install pyserial
```

Run:
```powershell
C:\Users\dmona\AppData\Local\Programs\Python\Python312\python.exe tools\can_nt_bridge.py --rio 172.22.11.2 --channel COM3
```

Or use the helper script that pins the Python interpreter:
```powershell
.\tools\run_can_nt.ps1
```

If PowerShell blocks scripts, run:
```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_can_nt.ps1
```

Published NetworkTables keys:
- `bringup/diag/busErrorCount`
- `bringup/diag/lastSeen/<deviceId>`
- `bringup/diag/missing/<deviceId>`
- `bringup/diag/msgCount/<deviceId>`

RobotV2 prints these diagnostics when you press `Y`.

Useful run flags:
- `--verbose` prints each received device ID.
- `--print-publish` prints a line each time NetworkTables is updated.
- `--print-summary-period` prints per-device counts/missing every N seconds (0 disables).

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
