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
2. Check local health (D-pad Left).
3. Check CAN visibility (D-pad Down).
4. Print the CAN diagnostics report (D-pad Up).
5. Capture a PCAP and inspect in Wireshark when needed.
6. Use vendor tools for firmware/config issues.

## HOWTO: Debug CAN Bus Issues
Use this checklist and the CAN Diagnostics Report (D-pad Up) to triage quickly.

Report sections (D-pad Up):
- CAN Bus Diagnostics summary (utilization, RX/TX errors, TX full, bus-off count, sample age)
- PC Tool status + missing/flapping counts and “seen on wire, not local” list
- Device Health (local API): faults/sticky faults, warnings/sticky warnings, lastErr, reset flag, voltage/current/temp

Example report snippet (shortened):
```
=== CAN Diagnostics Report ===
=== CAN Bus Diagnostics ===
Utilization: 73.2%
RX errors: 4 (delta 1)
TX errors: 2 (delta 0)
TX full: 3 (delta 1)
Bus off count: 1 (delta 1)
Sample age: 0.05s
===========================
Bus Health: (see CAN Bus Diagnostics summary above)
PC Tool:
  Heartbeat age: 0.21s
  Open OK: YES
  Frames/sec: 395.8
  Frames total: 68124
  Read errors: 0
  Last frame age: 0.01s
  Missing devices (PC): 1
  Flapping devices (PC): 2
  Seen on wire, not local: 5/2/31 age=0.27s
Device Health (local API):
  NEO CAN 10: present=YES faults=0x0 sticky=0x0 warnings=0x0 stickyWarn=0x0 lastErr=kOk reset=NO busV=11.8 current=6.3 tempC=33.9
  FLEX CAN 3: present=YES faults=0x0 sticky=0x0 warnings=0x40 stickyWarn=0x40 lastErr=kTimeout reset=YES busV=10.9 current=8.1 tempC=38.2
  KRAKEN CAN 11: present=YES fault=0x0 sticky=0x0 lastErr=OK status=OK/OK
  FALCON CAN 5: present=YES fault=0x0 sticky=0x0 lastErr=OK status=OK/OK
  CANCoder CAN 12: present=YES absDeg=187.2 lastErr=OK
==============================
```

Step 1: Validate the bus is healthy (robot data).
1. Press `D-pad Up` to print the CAN Diagnostics Report.
2. If bus utilization is high, TX full is rising, or error counts are rising, fix wiring/termination before touching devices.
3. If bus-off count increases, treat it as a hard wiring failure.

Step 2: Validate the PC tool evidence (driver station data).
1. Confirm the PC tool is running and connected.
2. In the report, check `PC Tool` fields for stale heartbeat or `openOk=NO`.
3. If PC tool is stale, fix the CANable/COM port/bitrate path first.

Step 3: Validate device health (local API).
1. In the report, scan every device row.
2. If a device shows faults/warnings, sticky faults, or `lastErr` issues, fix power or configuration before debugging control.
3. If a device is `present=NO (not added)`, add it in bringup before troubleshooting.

Interpretation table (X = robot, Y = PC tool):
Note: The report prints bus health, PC tool status, and local device health. Some rows below are vendor-tool-only or planned fields (for example last error code and reset flags).

| Signal / Error | Source | Where it runs | What it tells you | Next check |
| --- | --- | --- | --- | --- |
| CAN bus utilization (%) | X | roboRIO CAN controller | High steady value indicates bus saturation or a device spamming frames | Reduce status frame rates; disable unused telemetry; bring up one subsystem at a time |
| CAN transmit error count | X | roboRIO CAN controller | Rising count means the controller cannot transmit frames | Check termination, look for shorts, inspect CAN H/L continuity |
| CAN TX full count | X | roboRIO CAN controller | TX buffer saturation (controller can’t queue more frames) | Reduce status frame rates; check for bus saturation |
| CAN receive error count | X | roboRIO CAN controller | Rising count indicates noise or corruption | Inspect connectors, grounding, twisted pair integrity, crushed cables |
| CAN bus-off count | X | roboRIO CAN controller | Hard failure; bus shut down | Fix wiring and termination before debugging any devices |
| Local device present | X | Vendor API (REV / CTRE) | Robot successfully exchanged CAN frames with the device | Proceed to behavior or configuration debugging |
| Local last error code | X | Vendor API | Timeouts, configuration mismatch, or API bind failures | Verify CAN ID, device type, vendor library version |
| Device current faults | X | Vendor API | Active electrical, thermal, or current-related problems | Resolve the reported fault first; do not debug CAN |
| Device sticky faults/warnings | X | Vendor API | Historical brownout, overcurrent, or reset evidence | Inspect power wiring and connectors even if currently OK |
| Device reset / reboot flags | X | Vendor API | Power interruption or brownout | Measure voltage at device under load; check breakers and crimps |
| Device supply voltage | X | Vendor API | Voltage sag under load | Check PDH channel, wiring gauge, connectors, breaker rating |
| PC tool heartbeat age | Y | Python tool | Stale heartbeat means PC evidence is invalid | Restart Python tool; check NT connection and firewall |
| PC tool open_ok | Y | Python tool | False means CAN interface not connected | Check USB cable, COM port, slcan attach, bitrate |
| PC frames per second | Y | CAN sniffer | Zero means no traffic visible on wire | Verify sniffer wiring, H/L orientation, bitrate, tap location |
| PC frames total | Y | CAN sniffer | Sanity check that traffic exists | If zero, treat as tooling or wiring issue |
| PC read error count | Y | SLCAN / serial layer | Rising count indicates USB or driver issues | Replace USB cable; check drivers; move USB port |
| CAN ID last_seen timestamp | Y | CAN sniffer | Seen on wire but not locally | Check robot config, CAN ID assignment, device type mismatch |
| Missing device count | Derived | Robot logic | Many missing implies bus or tooling issue | Check bus health and PC tool before touching devices |
| Seen / missing flapping rate | Derived | Robot logic | Intermittent wiring or unstable power | Wiggle test connectors; inspect pigtails; check power integrity |

## Debugging Procedures
Use these repeatable procedures to isolate issues quickly. Keep local (roboRIO) data and CAN-bus (PC tool) data separate.

### Procedure A: No Motion
1. Ensure the robot is enabled in teleop.
2. Press `D-pad Right` to print input values.
3. Press `D-pad Left` and check:
   - `set` and `applied` match your command.
   - `current` is > 0 when the motor should move.
4. If `applied > 0` but `current = 0`, suspect wiring or motor output terminals.
5. If `set = 0`, inputs are not getting through (deadband, controller, or mode).

### Procedure B: Missing Device on CAN
1. Run the PC tool with `--publish-unknown`.
2. Press `D-pad Down` and check the device row:
   - `NO_DATA`/`MISSING` implies no frames seen.
3. Verify CAN ID, wiring, termination, and power.
4. Capture a PCAP and filter for `frccan.device_id == <id>`.

### Procedure C: Unexpected Device Seen
1. Run the PC tool with `--publish-unknown`.
2. Press `D-pad Down` and identify `label=UNKNOWN`.
3. Use Wireshark filter `frccan.manufacturer == X && frccan.device_type == Y && frccan.device_id == Z`.
4. Update the profile JSON if the device is expected.

### Procedure D: Low/Zero fps
1. Press `D-pad Down` twice, a second apart, and read the `fps` column.
2. If `fps` is 0 but `status=OK`, check that the PC tool is running and seeing traffic.
3. Use Wireshark to confirm frames are present.

### Procedure E: Health vs CAN Mismatch
1. `D-pad Left` shows local device data; `D-pad Down` shows PC tool CAN data.
2. If `D-pad Left` is OK but `D-pad Down` is missing, the PC tool or CANable path is broken.
3. If `D-pad Down` is OK but `D-pad Left` is missing, the device is not instantiated in bringup.

## Debugging Scenarios
- Motor does not move, LED changes.
- Motor moves only after power cycle.
- Device shows `NO_DATA` on `D-pad Down`.
- Device shows `MISSING` after a minute.
- CAN bus is silent (no frames).
- CAN bus has unexpected devices.
- CAN fps for one device is far higher than others.
- `ageSec` grows while device is powered.
- RTR requests appear without responses.
- PC tool publishes but robot shows `NO_DATA`.

## Q & A

**Q: How can I see unexpected devices on the CAN bus?**  
A: Run the PC tool with `--publish-unknown` and then press `D-pad Down` on the robot to view the table. Unknown devices will show as `label=UNKNOWN`. You can also capture a PCAP and inspect in Wireshark.

**Q: How do I switch CAN profiles at runtime?**  
A: Press `Back` on the Xbox controller. Profiles rotate in the order they appear in `src/main/deploy/bringup_profiles.json`.

**Q: Why does a device show `NO_DATA` in the NetworkTables table?**  
A: The PC tool has not published a valid `lastSeen` for that device yet. Check that the Python bridge is running and connected to the roboRIO, and that the device is on the CAN bus.

**Q: What’s the difference between local health (D-pad Left) and CAN diagnostics (D-pad Down)?**  
A: `D-pad Left` prints local roboRIO data pulled directly from device APIs (volt/current/temp/faults). `D-pad Down` prints CAN-bus data coming from the PC tool via NetworkTables.

**Q: How do I capture a PCAP and view it in Wireshark?**  
A: Run the PC tool with `--pcap logs\run.pcapng`, then open that file in Wireshark. The Lua dissector lives at `tools/wireshark/frc_can_dissector.lua`.

**Q: Why is a device showing `MISSING` even though it’s powered?**  
A: The PC tool isn’t receiving frames for that ID (wiring/ID mismatch/termination), or it’s timing out based on `--timeout`. Verify the CAN ID and wiring.

**Q: How do I see message rate (fps) per device?**  
A: Press `D-pad Down` twice a second or two apart. The `fps` column is computed from `msgCount` deltas between prints.

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

Hardware profile schema (single source of truth):
- This JSON is the shared, data-driven hardware configuration used by both robot code and the PC tool.
- Each profile can include these sections:
- `neos`, `flexes`, `krakens`, `falcons`, `cancoders` as arrays of `{ "label": "...", "id": <can_id> }`.
- `pdh`, `pigeon`, `roborio` as single objects `{ "label": "...", "id": <can_id> }`.
- Omit any section you don’t use.

Quick start template:
- Copy `src/main/deploy/bringup_profiles.template.json` and edit it for your robot.

Step-by-step: Add your hardware
1. Open `src/main/deploy/bringup_profiles.template.json`.
2. Save a copy as `src/main/deploy/bringup_profiles.json` (or edit the existing file).
3. Set `default_profile` to your profile name.
4. Fill in your device lists and CAN IDs; keep labels short and unique.
5. Deploy to the roboRIO.
6. Use `Back` to cycle profiles and verify the device list is correct.

Supported profile sections include:
- `neos`, `flexes`, `krakens`, `falcons`, `cancoders`
- `pdh`, `pdp`, `pigeon`, `roborio`

Manufacturer/type display names are loaded from `src/main/deploy/can_mappings.json`.

## Controller Bindings
Robot and RobotV2 share the same bindings, grouped by purpose.

Operational controls:
- `A`: add motor (alternates SPARK/CTRE)
- `Start`: add all motors + CANCoders
- `Back`: toggle CAN profile
- `Left Y`: NEO/FLEX speed
- `Right Y`: KRAKEN/FALCON speed
- `X`: nudge motors (0.2 for 0.5s)

Status printouts:
- `B`: print state
- `Left Bumper`: reprint bindings
- `Right Bumper`: print CANCoder absolute positions
- `D-pad Left`: print health status
- `D-pad Down`: print NetworkTables diagnostics (RobotV2 only)
- `D-pad Up`: print CAN diagnostics report
- `D-pad Right`: print speed inputs

## CAN Sniffer Bridge (CANable Pro V2)
This project includes a CAN -> NetworkTables bridge for diagnostics.

### Hardware Notes (CANable Pro V2)
- The CANable Pro is an isolated USB-to-CAN adapter with additional ESD protection and a bootloader button for firmware updates.
- It includes a termination jumper and uses a 3‑pin terminal for CANH/CANL/GND; it supports CAN 2.0 A/B up to 1 Mbit/s.

### Firmware / Driver Options
CANable devices ship with **slcan** firmware by default (serial‑line CAN). This enumerates as a standard serial device on Windows, macOS, and Linux.

There is an alternative **candlelight** firmware that exposes a native CAN interface using the `gs_usb` protocol (no `slcand` on Linux). It provides higher performance by bypassing the serial‑line path and is the recommended option for Linux SocketCAN workflows.

On Windows, candlelight presents as a generic USB device; Cangaroo is a common viewer for candlelight, while the stock slcan firmware works with cantact‑app.

### Possible Project Improvements (Non‑Breaking)
These are additive ideas to support alternate drivers without changing current Windows‑first behavior:
- Add a `--interface` preset for `gs_usb` (candlelight) and `socketcan` (Linux) alongside today’s `slcan`.
- Provide a short OS‑specific quick‑start table (Windows slcan vs Linux candlelight).
- Add a “firmware mode” note to the tool output (`slcan` vs `candlelight`) to reduce confusion in pits.
- Add a small troubleshooting note when `openOk=NO` that suggests checking firmware mode/driver.

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
- `bringup/diag/can/summary/json` (when `--publish-can-summary` is enabled)
- `bringup/diag/can/pc/heartbeat`
- `bringup/diag/can/pc/openOk`
- `bringup/diag/can/pc/framesPerSec`
- `bringup/diag/can/pc/framesTotal`
- `bringup/diag/can/pc/readErrors`
- `bringup/diag/can/pc/lastFrameAgeSec`
- Legacy deviceId-only aggregate keys (for backward compatibility):
  - `bringup/diag/lastSeen/<deviceId>`
  - `bringup/diag/missing/<deviceId>`
  - `bringup/diag/msgCount/<deviceId>`
  - `bringup/diag/type/<deviceId>` (always `Mixed`)
  - `bringup/diag/status/<deviceId>` (OK/STALE/MISSING)
  - `bringup/diag/ageSec/<deviceId>` (-1 if missing)

RobotV2 prints these diagnostics when you press `D-pad Down`.
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
