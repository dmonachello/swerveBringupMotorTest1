**Reverse Engineering Guide**

1. Introduction
Use the full bringup system (robot + PC tool + captures) to reverse engineer FRC CAN protocols with repeatable experiments, in-stream markers, and analyzable outputs.

Revision Table
Version | Initials | Comment
1.0 | DRM | origin


1.1 Components
Purpose: Briefly introduce the moving parts used together for reverse engineering.

1.1.1 Software
- Py script: PC-side capture and analysis tool that writes pcapng with markers and publishes summaries to the robot.
- Robot: Bringup harness used to apply controlled stimuli and print diagnostics.
- Wireshark dissector: Lua plugin for decoding FRC CAN identifiers and aiding inspection.

1.1.2 Hardware
- robot
- CAN bus devices
- CAN Bs sniffer

2. Py Script
Purpose: Capture CAN traffic on the PC, add in-stream markers, publish summary diagnostics to the robot, and produce artifacts for analysis.

2.1 Reverse Engineering Features:
2.1.1 Marker Capture
Purpose: Embed keyboard markers into the capture timeline so stimuli are visible inside the pcapng.

- The tool writes real CAN frames plus synthetic marker frames into the same `.pcapng`.
- Marker frames are not transmitted on the CAN bus.

Marker frame format:
- Extended arbitration ID `0x1FFC0D00` by default.
- DLC 8, payload bytes:
  - `0..3` ASCII `MARK` (`4D 41 52 4B`)
  - `4` key code (`ord(key) & 0xFF`)
  - `5` marker counter (wraps at 255)
  - `6..7` extra info (currently `0`)

2.1.2 CLI Flags (Markers)
Purpose: Customize marker behavior from the command line for repeatable runs.

2.1.2.1 Flags:
- py script
- `--pcap <path>` capture file (use `.pcapng` for markers)
- `--enable-markers` or `--disable-markers`
- `--marker-id 0x1FFC0D00`
- `--capture-note "text"`

2.1.2.2 Example run:
```cmd
%USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --pcap tools\can_nt\logs\run_with_markers.pcapng --rio 172.22.11.2
```

2.2 Py Script Controls
Marker keys:
- `1` `2` `3` `4` stimulus levels (stored as key only)
- `0` stop
- `m` generic marker
- `h` reprint help banner
- `q` quit cleanly

2.3 Capture Metadata
Purpose: Preserve capture context (time, interface, bitrate, notes) inside the pcapng itself.

Notes:
- The section header includes a short comment with start time, interface, channel, bitrate, and optional note.
- Pass `--capture-note "text"` to include a device-under-test note.

3. Robot
Purpose: Drive controlled robot stimuli that produce observable CAN changes.

3.1 Robot xbox/console commands
- `Back`: toggle CAN profile
- `B`: print state
- `D-pad Left`: print health status
- `D-pad Down`: print NetworkTables diagnostics
- `D-pad Up`: print CAN diagnostics report
- `D-pad Right`: print speed inputs
- `Left Bumper`: reprint bindings
- `Right Bumper`: print CANCoder absolute positions
- (Secondary) `A`: run non-motor test
- `Left Stick`: nudge motors (0.2 for 0.5s)
- `Right Stick`: clear device faults
- `X`: dump CAN report JSON
- `Y`: toggle dashboard/shuffleboard updates
- `Left Y`: NEO/FLEX speed
- `Right Y`: KRAKEN/FALCON speed
- Controller 2 `A/B/X/Y`: fixed speed 0.25/0.50/0.75/1.00 for motor tests

4. Wireshark Dissector
Purpose: Review capture data, isolate markers, and decode known FRC CAN fields.

4.1 Dissector Features:
- Decodes common FRC extended ID fields into readable manufacturer, device type, API class, and API index.
- Presents decoded fields in the packet details tree for quick inspection.
- Works alongside raw CAN bytes for unknown frames.

4.2 Dissector:
- Lua dissector path: `tools/can_nt/wireshark/frc_can_dissector.lua`
- Install location: `%APPDATA%\Wireshark\plugins\frc_can_dissector.lua`
- Reload via `Analyze` -> `Reload Lua Plugins` after copying.
- Verify it is active by selecting a CAN frame and checking the packet details tree for decoded FRC CAN fields.
- If you see only raw CAN bytes, reload the Lua plugins and reopen the capture.

4.3 Wireshark filters:
Purpose: Isolate marker frames and then zoom in on CAN traffic around each stimulus change.

How to use:
- Start with a marker filter to find the exact timeline points you annotated.
- Click a marker, then clear the filter to inspect neighboring frames.
- Use narrow filters to compare "before" and "after" ranges for the same arbitration IDs.

Examples:
- Marker frames by ID:
  `can.id == 0x1FFC0D00`
- Marker frames by payload prefix:
  `can.data contains 4d:41:52:4b`
- Experiment window around the first forward step (select marker, then filter by the motor's CAN ID):
  `can.id == 0x0B` 
- Focus on a single device's status frames while you vary `Left Y`:
  `can.id == 0x0B || can.id == 0x0C`
- Find frames with any payload changes between markers (use with "Analyze -> Compare Packet Lists"):
  `can.data`

5. Test Procedures
Purpose: Execute a full capture run with markers and repeatable motor stimuli.

5.1 Prereqs:
- CANable connected and visible as a COM port.
- Robot code deployed and profile set (example: `reverse_eng_min1`).

5.2 Mode 1: Full setup (roboRIO + bringup)
Purpose: Run the full system unchanged and use robot-side stimuli.

Setup:
- Select profile on the robot (`Back` until it shows `reverse_eng_min1`).
- Start the bridge with capture enabled:
```cmd
%USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --profile reverse_eng_min1 --interface slcan --channel COM3 --bitrate 1000000 --rio 172.22.11.2 --pcap tools\can_nt\logs\reveng_min1.pcapng --publish-can-summary
```
- Replace `COM3` with your CANable port.
- Press `D-pad Right` to print speed inputs so you can see the live `Left Y` value.

Experiment A: Idle baseline:
- Press `m`.
- Wait 5 seconds.
- Press `m`.


Experiment A.1: Confirm the marker pipeline and capture integrity before deeper analysis.

Checks:
- Press `m` three times then `q`:
  - Three marker frames appear with `MARK` payload prefix.
  - Marker timestamps are strictly increasing.
- Press `1`, wait 2 seconds, press `2`, wait 2 seconds, press `0`, then `q`:
  - Marker spacing matches the pauses.
  - Normal CAN traffic is still present.

Experiment B: Forward step (0.25):
- Press `m`.
- Set `Left Y` to 0.25 or use Controller 2 `A` for a fixed 0.25.
- Press `1`.
- Press `D-pad Right` to confirm the input.
- Hold 5 seconds.
- Return `Left Y` to 0 or release Controller 2 `A`.
- Press `0`.
- Press `D-pad Right` to confirm the input.
- Press `m`.

Experiment C: Higher step (0.50):
- Press `m`.
- Set `Left Y` to 0.50 or use Controller 2 `B` for a fixed 0.50.
- Press `2`.
- Press `D-pad Right` to confirm the input.
- Hold 5 seconds.
- Return `Left Y` to 0 or release Controller 2 `B`.
- Press `0`.
- Press `D-pad Right` to confirm the input.
- Press `m`.

Experiment D: Reverse step (-0.25):
- Press `m`.
- Set `Left Y` to -0.25.
- Press `1`.
- Press `D-pad Right` to confirm the input.
- Hold 5 seconds.
- Return `Left Y` to 0.
- Press `0`.
- Press `D-pad Right` to confirm the input.
- Press `m`.

Finish:
- Press `q` to stop capture cleanly.
- Open the capture in Wireshark.
- Filter markers with `can.id == 0x1FFC0D00`.
- Inspect IDs and byte changes around each marker range.

5.3 Mode 2: Vendor apps (no roboRIO in hardware config)
Purpose: Drive devices directly with vendor tools and keep the PC capture path identical.

Setup:
- Remove or disable the roboRIO from the hardware config for this run.
- Use vendor tools to command devices (e.g., REV Hardware Client). CTRE Tuner X requires a roboRIO and is not used in this mode.
- Start the bridge with capture enabled and disable NT publishing: add `--no-nt`.
  Example:
  ```cmd
  %USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --profile reverse_eng_min1 --interface slcan --channel COM3 --bitrate 1000000 --rio 172.22.11.2 --pcap tools\can_nt\logs\reveng_min1.pcapng --no-nt
  ```
- Use marker keys to annotate each vendor action (set output, stop, reverse).
- Do not use the robot command interface for this mode; the vendor apps are the sole stimulus source.

5.4 Mode 3: Vendor apps with roboRIO (no robot software stimulus)
Purpose: Use vendor tools that require a roboRIO (e.g., CTRE Tuner X) without using robot-side commands.

Setup:
- Keep the roboRIO connected and powered.
- Disable or avoid any robot-side stimulus commands for this run.
- Use CTRE Tuner X (or other vendor tools that require the roboRIO) to command devices.
- Start the bridge with capture enabled and disable NT publishing: add `--no-nt`.
  Example:
  ```cmd
  %USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --profile reverse_eng_min1 --interface slcan --channel COM3 --bitrate 1000000 --rio 172.22.11.2 --pcap tools\can_nt\logs\reveng_min1.pcapng --no-nt
  ```
- Use marker keys to annotate each vendor action (set output, stop, reverse).

Optional inventory diff:
- Idle:
  ```cmd
  %USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --profile reverse_eng_min1 --interface slcan --channel COM3 --bitrate 1000000 --rio 172.22.11.2 --dump-api-inventory tools\can_nt\inventory_idle.json --dump-api-inventory-after 5
  ```
- Running:
  ```cmd
  %USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --profile reverse_eng_min1 --interface slcan --channel COM3 --bitrate 1000000 --rio 172.22.11.2 --dump-api-inventory tools\can_nt\inventory_run.json --dump-api-inventory-after 5
  ```
- Diff:
  ```cmd
  %USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools\\can_nt\\can_nt_bridge.py --diff-inventory tools\can_nt\inventory_idle.json tools\can_nt\inventory_run.json
  ```
Explanation:
- `--dump-api-inventory` writes a snapshot of observed `(mfg,type,id,apiClass,apiIndex)` pairs with counts and computed fps.
- `--diff-inventory A.json B.json` compares two snapshots and prints:
  - New pairs: frames that appear in `B` but not in `A` (often command-like or mode-specific traffic).
  - Missing pairs: frames present in `A` but not in `B` (often status that disappears when a device is disabled).
  - Biggest rate changes: pairs with the largest fps delta between runs.
- Use the diff output to identify candidate command frames, then inspect those IDs around markers in Wireshark.

6. Design Notes

Purpose: Call out limitations that affect capture fidelity and portability.

- Keyboard input is Windows-only (`msvcrt`), aligned with Driver Station usage.
- Markers require `.pcapng` to avoid mixing formats and to keep metadata available.
- Synthetic frames can be filtered easily but are not real bus traffic.
- Doc export: `powershell -ExecutionPolicy Bypass -File tools\md_to_docx\md_to_docx.ps1 -Input reverse_eng.md`

7. Future Extensions
Purpose: Outline next steps that extend capability without breaking the workflow.

- Add optional label indices in marker bytes `6..7`.
- Add a replay mode that re-emits markers during offline analysis.
- Add a decoder registry with confidence scoring for inferred fields.

