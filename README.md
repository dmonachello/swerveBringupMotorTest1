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

## What This App Is For (Debugging)
This project is a bringup and diagnostics harness. It does not fix your code bugs,
but it does give you fast visibility into hardware and CAN bus behavior so you can
isolate issues quickly.

What it gives you:
- Controlled motor bringup (add one or all, known inputs).
- Local roboRIO health checks (bus voltage, applied output, current, temperature, faults).
- CAN-bus diagnostics from the PC tool (seen/missing, age, msgCount, fps).
- Wire-level evidence via PCAP/PCAPNG + Wireshark dissector.
- Unknown device detection (optional publish of unseen IDs).

What it does not do:
- Fix robot logic or tuning.
- Replace vendor tools (REV Hardware Client / CTRE Tuner X).

Typical workflow:
1. Bring up devices (add motor / add all).
2. Check local health (X).
3. Check CAN visibility (Y).
4. Capture a PCAP and inspect in Wireshark when needed.
5. Use vendor tools for firmware/config issues.

## Debugging Procedures
Use these repeatable procedures to isolate issues quickly. Keep local (roboRIO) data and CAN-bus (PC tool) data separate.

### Procedure A: No Motion
1. Ensure the robot is enabled in teleop.
2. Press `Right Stick` to print input values.
3. Press `X` and check:
   - `set` and `applied` match your command.
   - `current` is > 0 when the motor should move.
4. If `applied > 0` but `current = 0`, suspect wiring or motor output terminals.
5. If `set = 0`, inputs are not getting through (deadband, controller, or mode).

### Procedure B: Missing Device on CAN
1. Run the PC tool with `--publish-unknown`.
2. Press `Y` and check the device row:
   - `NO_DATA`/`MISSING` implies no frames seen.
3. Verify CAN ID, wiring, termination, and power.
4. Capture a PCAP and filter for `frccan.device_id == <id>`.

### Procedure C: Unexpected Device Seen
1. Run the PC tool with `--publish-unknown`.
2. Press `Y` and identify `label=UNKNOWN`.
3. Use Wireshark filter `frccan.manufacturer == X && frccan.device_type == Y && frccan.device_id == Z`.
4. Update the profile JSON if the device is expected.

### Procedure D: Low/Zero fps
1. Press `Y` twice, a second apart, and read the `fps` column.
2. If `fps` is 0 but `status=OK`, check that the PC tool is running and seeing traffic.
3. Use Wireshark to confirm frames are present.

### Procedure E: Health vs CAN Mismatch
1. `X` shows local device data; `Y` shows PC tool CAN data.
2. If `X` is OK but `Y` is missing, the PC tool or CANable path is broken.
3. If `Y` is OK but `X` is missing, the device is not instantiated in bringup.

## Debugging Scenarios
- Motor does not move, LED changes.
- Motor moves only after power cycle.
- Device shows `NO_DATA` on `Y`.
- Device shows `MISSING` after a minute.
- CAN bus is silent (no frames).
- CAN bus has unexpected devices.
- CAN fps for one device is far higher than others.
- `ageSec` grows while device is powered.
- RTR requests appear without responses.
- PC tool publishes but robot shows `NO_DATA`.

## Q & A

**Q: How can I see unexpected devices on the CAN bus?**  
A: Run the PC tool with `--publish-unknown` and then press `Y` on the robot to view the table. Unknown devices will show as `label=UNKNOWN`. You can also capture a PCAP and inspect in Wireshark.

**Q: How do I switch CAN profiles at runtime?**  
A: Press `Back` on the Xbox controller. Profiles rotate in the order they appear in `src/main/deploy/bringup_profiles.json`.

**Q: Why does a device show `NO_DATA` in the NetworkTables table?**  
A: The PC tool has not published a valid `lastSeen` for that device yet. Check that the Python bridge is running and connected to the roboRIO, and that the device is on the CAN bus.

**Q: What’s the difference between local health (X) and CAN diagnostics (Y)?**  
A: `X` prints local roboRIO data pulled directly from device APIs (volt/current/temp/faults). `Y` prints CAN-bus data coming from the PC tool via NetworkTables.

**Q: How do I capture a PCAP and view it in Wireshark?**  
A: Run the PC tool with `--pcap logs\run.pcapng`, then open that file in Wireshark. The Lua dissector lives at `tools/wireshark/frc_can_dissector.lua`.

**Q: Why is a device showing `MISSING` even though it’s powered?**  
A: The PC tool isn’t receiving frames for that ID (wiring/ID mismatch/termination), or it’s timing out based on `--timeout`. Verify the CAN ID and wiring.

**Q: How do I see message rate (fps) per device?**  
A: Press `Y` twice a second or two apart. The `fps` column is computed from `msgCount` deltas between prints.

**Q: How do I add a new motor/controller type to a profile?**  
A: Edit `src/main/deploy/bringup_profiles.json` and add entries under `neos`, `flexes`, `krakens`, `falcons`, `cancoders`, `pdh`, `pdp`, `pigeon`, or `roborio`, then redeploy.

**Q: What do the `ageSec` and `msgCount` fields mean?**  
A: `ageSec` is seconds since the last frame seen for that device. `msgCount` is total frames seen for that device.

**Q: Why is one device’s fps higher than another’s?**  
A: Different devices publish status frames at different default rates. Higher fps just means more CAN traffic from that device.

**Q: How do I update the Wireshark dissector?**  
A: Update `tools/wireshark/frc_can_dissector.lua` and copy it to `%APPDATA%\Wireshark\plugins\frc_can_dissector.lua`, then restart Wireshark.

## Install (All Features)

### Required Software
- WPILib 2026 (Java) for build/deploy to roboRIO.
- Vendor libraries:
  - CTRE Phoenix 6
  - REVLib (Spark MAX / Spark Flex)
- Python 3.10+ on the Driver Station laptop for the CAN bridge.
- Wireshark (for PCAP/PCAPNG inspection).
- CTRE Tuner X and REV Hardware Client (firmware/config/diagnostics).

### WPILib + Vendor Libraries
1. Install WPILib 2026.
2. Open this project in VS Code (WPILib).
3. Use **WPILib: Manage Vendor Libraries** and install:
   - `Phoenix6-26.1.1.json` (and Phoenix 5 if needed)
   - `REVLib.json`

### Python CAN Bridge (Driver Station PC)
Install dependencies:
```cmd
py -m pip install --upgrade python-can pyserial pynetworktables pyntcore
```

Run the bridge:
```cmd
python tools\can_nt_bridge.py --profile demo_home_022326 --interface slcan --channel COM3 --bitrate 1000000 --rio 172.22.11.2 --publish-can-summary
```

Optional flags:
- `--print-summary-period N` for console summaries.
- `--print-publish` for seen/missing transitions.
- `--publish-unknown` to publish unknown devices on the bus.
- `--pcap <path>` to write a capture file.

### Wireshark + Dissector
1. Install Wireshark.
2. Copy `tools/wireshark/frc_can_dissector.lua` to:
   - `%APPDATA%\Wireshark\plugins\frc_can_dissector.lua`
3. Restart Wireshark.

### Firmware / Diagnostics Tools
- CTRE Tuner X (Phoenix) for firmware updates and Signal Logger (hoot logs).
- REV Hardware Client for SPARK MAX/Flex firmware/config and diagnostics.

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
