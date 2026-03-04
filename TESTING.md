# CAN Sniffer Utility Test Plan

This document provides a step-by-step checklist to verify the CAN -> NetworkTables bridge end-to-end with a real CAN bus and RoboRIO.

## Full Functional Test Plan (End-to-End)
Purpose: verify all major robot + PC tool functionality after large changes.

## Smoke Test (Pit-Friendly)
Purpose: run the minimum set of checks to confirm the system is healthy.

1. Deploy robot code and enter teleop.
2. Press `Start` to add all configured devices.
3. Press `B` to print state and confirm devices are present.
4. Move `Left Y` and `Right Y`, then press `D-pad Right` to confirm inputs.
5. Run one enabled test with secondary `A` and confirm PASS/FAIL prints.
6. If the PC tool is running, press `D-pad Down` and confirm `openOk=YES`.
7. If Wireshark is needed, run a quick capture and confirm frames appear.

### A) Robot Bringup Core
Purpose: ensure base robot bringup actions still work.

1. Deploy robot code and enter teleop.
2. Press `Start` to add all configured devices.
3. Press `B` to print state.
Expected:
- All configured devices show `present=YES`.
- No exceptions or missing device errors.

### B) Controller + Bindings (Config-Driven)
Purpose: verify command bindings resolve from JSON and edge/hold works.

1. Confirm the startup prints the bindings list (LB).
2. Press `LB` to reprint bindings.
3. Press `A`, `Start`, `B`, `X`, `Y`, `Back`.
Expected:
- Each command prints the expected action.
- No missing/unknown command warnings.

### C) Speed Inputs
Purpose: verify axis inputs map to left/right drive commands.

1. Move `Left Y` and `Right Y`.
2. Press `D-pad Right` to print inputs.
Expected:
- Values match stick movement and deadband/invert settings.

### D) Joystick Motor Control (Non-Test Mode)
Purpose: verify the standard joystick-driven motor output still works.

1. Add one REV motor and one CTRE motor.
2. Move `Left Y` and `Right Y`.
Expected:
- Motors respond to their respective axes.
- Output stops when stick returns to center.

### E) Bringup Test Selection + Run
Purpose: verify test list, selection, run, and run-all.

1. Enable 2+ tests in `bringup_tests.json`, deploy.
2. Press secondary `LB`/`RB` to cycle tests.
3. Press secondary `A` to run the selected test.
4. Press secondary `B` to run all enabled tests.
Expected:
- Test names print on selection.
- PASS/FAIL prints after each run.
- Run-all prints `Run-all complete.`.

### F) Composite Test Checks
Purpose: verify rotation/time/limit/hold checks independently and combined.

1. Rotation only: `rotation` set with `encoderKey=internal`.
2. Time only: `time.timeoutSec` + `onTimeout`.
3. Limit only: `limitSwitch.enabled=true`.
4. Hold only: `hold.enabled=true`.
5. Combined: rotation + time + limit + hold.
Expected:
- Each check terminates the test per its condition.
- Combined test stops on the first triggered condition.

### G) External Encoder Tests
Purpose: verify `encoderKey` external device selection.

1. Use a test with `encoderKey=CTRE:CANCoder:<id>`.
2. Run the test and confirm rotation tracking.
Expected:
- Encoder output changes and test terminates at `limitRot`.

### H) Multi-Motor Tests
Purpose: verify `motorKeys` list drives multiple motors.

1. Use a composite or joystick test with 2+ `motorKeys`.
2. Run it.
Expected:
- All motors respond together; stop together on test end.

### I) Limit Switch Integration
Purpose: verify limit switches clamp motion and can terminate tests.

1. Configure `limits` for a motor in `bringup_profiles.json`.
2. Run a test with `limitSwitch.enabled=true`.
Expected:
- Motor output clamps on closed limit.
- Test ends and reports PASS/FAIL per `onHit`.

### J) PC CAN Tool – Basic
Purpose: verify the PC sniffer runs and publishes NT.

1. Run the PC tool with `--profile`.
2. Press `D-pad Down` on robot.
Expected:
- `openOk=YES`, heartbeat updates, and device table matches CAN traffic.

### K) PC CAN Tool – Wireshark
Purpose: verify live pipe and file captures.

1. Live pipe: start Wireshark `-k -i \\.\pipe\FRC_CAN`.
2. Run the tool with `--pcap-pipe FRC_CAN`.
3. File: run `--pcap tools\logs\run.pcapng`.
Expected:
- Wireshark shows live frames via pipe.
- PCAPNG opens and decodes.

### L) PC CAN Tool – Inventory + Diff
Purpose: verify reverse engineering outputs.

1. Run `--dump-api-inventory tools\inv_a.json --dump-api-inventory-after 5`.
2. Run again after a different stimulus into `inv_b.json`.
3. Run `--diff-inventory tools\inv_a.json tools\inv_b.json`.
Expected:
- Inventory files are created.
- Diff prints new/missing pairs and rate deltas.

### M) PC Tool Config Auto-Gen
Purpose: verify can_nt_config.json generation from profile.

1. Run `--profile demo_club --dump-can-config tools\can_nt_config.json`.
Expected:
- File is created and lists devices matching the selected profile.

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

### 11) DIO limit switch reporting
Steps:
1. Add `limits` to a device entry in `src/main/deploy/bringup_profiles.json`, for example:
   `{ "label": "FL KRAK", "id": 2, "limits": { "fwdDio": 0, "revDio": 1, "invert": false } }`
2. Wire limit switches to the specified DIO ports.
3. Deploy and run the robot code.
4. Press `D-pad Left` to print health status.
Expected:
- The device row includes `limits=fwd:DIO0=OPEN/ CLOSED,rev:DIO1=OPEN/ CLOSED`.
- Toggling the limit switch updates the reported state.
- When a limit is CLOSED, motor output in that direction is clamped to 0.0.
- If your switch is normally closed, set `"invert": true` in the profile entry.

### 12) Non-motor device test action
Steps:
1. Ensure a CANdle is in the profile (`candles` list).
2. Deploy and run the robot code.
3. Press secondary `A` to run the non-motor test action.
Expected:
- The CANdle toggles between OFF and BLUE.
- Console prints `Test: <label> (CANdle) [toggle_led]`.

## Runtime Verification Checklist (Robot Tests)
Purpose: verify the bringup test framework behaves correctly on real hardware.

- Confirm controller detection prints at startup (controller name and type).
- Press `B` to print state and verify devices are instantiated.
- Use secondary `LB`/`RB` to change the selected test and confirm the name updates.
- Run the selected test with secondary `A` and confirm PASS/FAIL and reason.
- Hold secondary `A` during a test that has `hold.enabled=true`; release to trigger the hold action.
- Press secondary `B` to run all enabled tests in order; verify `Run-all complete.` prints at the end.
- If a joystick test is enabled, confirm the listed `motorKeys` move together and stop when the test ends.
- If a rotation test uses `encoderKey: internal`, confirm it uses the motor index given by `encoderMotorIndex`.
- If a limit switch check is enabled, verify the test ends on switch activation and the result matches `onHit`.
- If the PC tool is running, press `D-pad Down` and confirm PC diagnostics show `openOk=YES`.

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
