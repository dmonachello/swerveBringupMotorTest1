# 1. Introduction

This document is the full test procedure for the existing code base. Use it to verify robot-only behavior and robot+PC sniffer behavior before any migration work begins.

## 2. Pre-Test Setup
1. Ensure roboRIO image and firmware are current.
2. Confirm vendor libraries installed (REV + CTRE) in the project.
3. Confirm `src/main/deploy/bringup_profiles.json` matches the hardware in front of you.
4. Ensure the Xbox controller is connected and detected.
5. Power the robot with CAN wiring complete and two terminations only.

## 3. Profiles (Required Setup)
Profiles define the hardware configuration the bringup code will control and monitor. Each profile lists the CAN devices, IDs, and labels for a specific robot setup.

Key concepts:
- Multiple profiles can be defined in the file (practice bot, comp bot, bench setup).
- The app can scroll through profiles to select one.
- The selected profile defines the known device list (what devices exist for this test).
- Selecting a profile does not activate any devices.
- Devices become active only when you explicitly activate them (one at a time or all at once).
- Active devices are the ones actually driven/commanded and included in bringup actions.

Purpose:
- Keep hardware configuration data-driven (no code edits).
- Support multiple configurations (practice bot, comp bot, bench setup).
- Ensure reports and diagnostics match the actual hardware on the bus.

Files:
- `src/main/deploy/bringup_profiles.json` (active profiles)
- `src/main/deploy/bringup_profiles.template.json` (starting template)

How to add or change a profile:
1. Open `src/main/deploy/bringup_profiles.json` (or copy the template file to this path).
2. Add a new profile entry with a unique name.
3. Fill in device lists and CAN IDs for your hardware.
4. Set `default_profile` to the profile you want at startup.
5. Deploy to the roboRIO.

File handling notes:
- This file is deployed with the robot code. Any edits require redeploy.
- Keep labels short and unique (used in reports).
- If you remove a device from the profile but it is still on the bus, it will appear as unknown in PC sniffer views (if enabled).

## 4. Build and Deploy
1. Build: `./gradlew build` (or deploy via WPILib VS Code).
2. Deploy to roboRIO.
3. Enable robot in teleop.

## 5. Robot-Only Functional Tests (No PC tool)
### 5.1 Profiles and Device Activation
1. Profile toggle (cycle)
   - Action: Press `Back`.
   - Expected: Profile name changes; the known device list updates.

2. Profile activate (explicit)
   - Action: Use the profile-activate command for the selected profile (if present in the current build).
   - Expected: The selected profile becomes the active profile (activation commands now apply to this profile).

3. Add motor (single)
   - Action: Press `A`.
   - Expected: Activates one device from the selected profile; should move when joystick input is applied.

4. Add all devices
   - Action: Press `Start`.
   - Expected: Activates all devices in the selected profile; verify with joystick input.

### 5.2 Reporting and Health
1. Print bindings
   - Action: Press `Left Bumper`.
   - Expected: Prints current bindings list.
   - Example output:
     ```
     Bindings (Operational):
       A: add motor (alternates SPARK/CTRE)
       Start: add all motors + CANCoders
       Back: toggle CAN profile
       Left Y: NEO/FLEX speed
       Right Y: KRAKEN/FALCON speed
       Left Stick: nudge motors (0.2 for 0.5s)
     Bindings (Status):
       B: print state
       Left Bumper: reprint bindings
       Right Bumper: print CANCoder absolute positions
       D-pad Left: print health status
       D-pad Down: print NetworkTables diagnostics (RobotV2 only)
       D-pad Up: print CAN diagnostics report
       D-pad Right: print speed inputs
       X: dump CAN report JSON
     ```

2. Print health status
   - Action: Press `D-pad Left`.
   - Expected: For each configured device, prints local health (present, faults, warnings, voltage, motorCurrent, temp, cmdDuty/appliedDuty).
   - Verify: present=YES for configured devices, busV ~12V, motorCurrentA near 0 when idle.
   - Example output:
     ```
     === Bringup Health (Local Robot Data) ===
     NEO index 0 CAN 10 faults=0x0 warnings=0x0 busV=12.32V cmdDuty=0.71 appliedDuty=0.71 motorCurrentA=0.92 tempC=26.0 follower=N
     NEO index 1 CAN 25 faults=0x0 warnings=0x0 busV=12.31V cmdDuty=0.71 appliedDuty=0.71 motorCurrentA=1.79 tempC=26.0 follower=N
     FLEX index 0 CAN 11 faults=0x0 warnings=0x0 busV=12.27V cmdDuty=0.71 appliedDuty=0.71 motorCurrentA=0.00 tempC=28.0 follower=N
     roboRIO CAN 0: present=YES (virtual, no API)
     ======================
     ```

3. Print inputs
   - Action: Press `D-pad Right`.
   - Expected: Shows joystick values / requested duty.
   - Example output:
     ```
     Inputs: leftY=0.71 rightY=0.00 deadband=0.05
     cmdDuty: spark=0.71 ctre=0.00
     ```

4. Print CAN diagnostics report (robot data only)
   - Action: Press `D-pad Up`.
   - Expected: CAN bus health section prints utilization, RX/TX errors, TX full, bus-off, sample age.
   - Verify: counts stable (no rapid increase).
   - Example output:
     ```
     === CAN Diagnostics Report ===
     === CAN Bus Diagnostics ===
     Utilization: 10.5%
     RX errors: 0 (delta 0)
     TX errors: 0 (delta 0)
     TX full: 0 (delta 0)
     Bus off count: 0 (delta 0)
     Sample age: 0.02s
     ===========================
     Bus Health: (see CAN Bus Diagnostics summary above)
     Device Health (local API):
       NEO CAN 10: present=YES faults=0x0 sticky=0x0 warnings=0x0 stickyWarn=0x40 lastErr=kOk reset=YES busV=12.61 motorCurrentA=0.00 tempC=26.0
       FLEX CAN 11: present=YES faults=0x0 sticky=0x0 warnings=0x0 stickyWarn=0x40 lastErr=kOk reset=YES busV=12.49 motorCurrentA=0.00 tempC=27.0
     ==============================
     ```

5. Dump JSON report (robot)
   - Action: Press `X`.
   - Expected: JSON printed to console and written to `/home/lvuser/bringup_report.json`.
   - Verify: file exists on roboRIO after test.
   - Example output:
     ```
     {"timestamp":1.772000000000E9,"bus":{"valid":true,"utilizationPct":10.5,"rxErrors":0,"txErrors":0,"busOff":0},"pc":{"openOk":false,"heartbeatAgeSec":-1.0},"devices":[{"type":"NEO","id":10,"present":true,"faultsRaw":0,"warningsRaw":0,"busV":12.61,"motorCurrentA":0.0,"tempC":26.0}]}
     ```

6. Nudge motors
   - Action: Press `Left Stick`.
   - Expected: Motors briefly nudge at low duty.
   - Verify: applied duty > 0 and motorCurrentA > 0.

7. CANCoder read
   - Action: Press `Right Bumper`.
   - Expected: Prints absolute position (rotations/degrees).
   - Example output:
     ```
     CANCoder CAN 12: absRot=0.521 absDeg=187.6 lastErr=OK
     ```

8. Print state
   - Action: Press `B`.
   - Expected: Prints the current robot bringup state summary.
   - Example output:
     ```
     State: profile=club_022426 activeDevices=3 mode=TELEOP enabled=YES
     Motors: spark=2 ctre=1 cancoder=1 candle=0
     ```

9. Toggle dashboard updates
   - Action: Press `Y`.
   - Expected: Toggles dashboard/shuffleboard updates on/off (no change to motor behavior).
   - Example output:
     ```
     Dashboard updates: OFF
     ```

10. Teleop disable behavior
    - Action: Disable robot in Driver Station, then re-enable.
    - Expected: Motors stop while disabled. Profile selection remains but outputs are inactive until re-enabled.

## 6. PC Tool Tests (With CAN Sniffer)
Preconditions: CANable connected, slcan configured, PC tool installed.

1. Start PC bridge
   - Command: `python tools/can_nt_bridge.py --rio <robot_ip> --profile <profile> --publish-can-summary --publish-unknown`
   - Expected: Bridge connects and prints a summary.

2. Print PC diagnostics
   - Action: Press `D-pad Down`.
   - Expected: Table with ageSec, msgCount, status, etc.
   - Verify: openOk=YES, heartbeat age small, fps > 0, devices show OK with recent lastSeen.
   - Example output:
     ```
     PC Tool: openOk=YES heartbeatAge=0.12s fps=395.8 total=68124 readErr=0 lastFrameAge=0.01s
     dev 5/2/10 label=NEO 10 status=OK ageSec=0.05 msgCount=18234
     dev 4/2/11 label=FLEX 11 status=OK ageSec=0.06 msgCount=18102
     dev 1/7/12 label=CANCoder 12 status=OK ageSec=0.10 msgCount=9123
     ```

3. Print CAN diagnostics report
   - Action: Press `D-pad Up`.
   - Expected: Includes PC tool status in report, with frames/sec, total, etc.
   - Example output:
     ```
     PC Tool:
       Status: OK
       Heartbeat age: 0.12s
       Open OK: YES
       Frames/sec: 395.8
       Frames total: 68124
       Read errors: 0
       Last frame age: 0.01s
       Missing devices (PC): 0
       Flapping devices (PC): 0
     ```

4. Unknown device detection
   - Expected: Unknown device shows label=UNKNOWN in D-pad Down table when publish-unknown is enabled.

## 7. JSON + AI Report Test
1. Press `X` (dump JSON).
2. Copy `/home/lvuser/bringup_report.json` to PC.
3. Confirm file is valid JSON and includes:
   - bus section
   - pc section (if tool running)
   - devices list
   - Example output:
     ```
     {
       "timestamp": 1.772000000000E9,
       "bus": { "valid": true, "utilizationPct": 10.5, "rxErrors": 0, "txErrors": 0, "busOff": 0 },
       "pc": { "openOk": false, "heartbeatAgeSec": -1.0 },
       "devices": [ { "type": "NEO", "id": 10, "present": true, "faultsRaw": 0 } ]
     }
     ```

## 8. Negative / Error Conditions (Optional)
1. Remove a device from the profile but leave it physically on CAN.
   - Expected: D-pad Down shows it as unknown if publish-unknown is enabled.

2. Disconnect PC tool.
   - Expected: pc.openOk=false, heartbeat stale, PC fields show NaN or missing.

3. Duplicate CAN ID (if safe to test).
   - Expected: devices may flap or show missing; bus errors might rise.

## 9. Pass / Fail Criteria
- All bindings trigger the correct output.
- Health report matches actual hardware state.
- JSON report is generated and valid.
- PC tool diagnostics appear only when tool is running.
- No unexpected crashes or exceptions.
