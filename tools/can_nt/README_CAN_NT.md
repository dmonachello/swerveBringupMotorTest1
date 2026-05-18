# CAN-NT-BRIDGE(1)

NAME
    can_nt_bridge.py - CAN -> NetworkTables bridge for RobotV2

SYNOPSIS
    python tools\\can_nt\\can_nt_bridge.py [options]
    tools\can_nt\run_can_nt.cmd [python.exe] [options]

DESCRIPTION
    Reads FRC CAN traffic from a CANable (SLCAN) and publishes diagnostics
    under bringup/diag for RobotV2. Can optionally write PCAP/PCAPNG or
    stream live PCAPNG into Wireshark via a Windows named pipe.

INSTALL
    py -m pip install pyntcore
    py -m pip install pynetworktables
    py -m pip install python-can
    py -m pip install pyserial
    py -m pip install prompt_toolkit

RUN
    python tools\\can_nt\\can_nt_bridge.py --rio 172.22.11.2

    tools\can_nt\run_can_nt.cmd

    set CAN_NT_PYTHON=C:\Path\To\Python\python.exe
    tools\can_nt\run_can_nt.cmd

    tools\can_nt\run_can_nt.cmd C:\Path\To\Python\python.exe

    tools\can_nt\run_can_nt.cmd --print-summary-period 2 --print-publish

    tools\can_nt\run_can_nt.cmd C:\Path\To\Python\python.exe --verbose --quick-check

    If neither is set, the helper script:
    1) uses the first python in PATH
    2) falls back to %USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe

VERSIONING
    Purpose: Show and update app versions.

    Show bridge version:
        python tools\\can_nt\\can_nt_bridge.py --version

    Show versions inside the CLI:
        show version
        show version --robot

    Update versions:
        python tools\\update_versions.py --set all=1.2.3
        python tools\\update_versions.py --set can_nt_bridge=1.2.3

BRIDGE CLI
    Purpose: Run the Cisco-style CLI front end inside the bridge app.

    Interactive:
        python tools\\can_nt\\can_nt_bridge.py --cli --rio 172.22.11.2

    Batch script:
        python tools\\can_nt\\can_nt_bridge.py --batch --script tools\\can_nt\\scripts\\setup.txt

    Quick smoke (read-only commands):
        python tools\\can_nt\\can_nt_bridge.py --batch --script tools\\can_nt\\scripts\\bridge_cli_smoke.txt

    Help:
        help
        help show
        help group
        help batch

    Notes:
    - CLI uses the TCP UI channel (port 5809 by default).
    - CLI does not require CAN access; use --no-can when running CLI only.
    - add device requires the label to exist in the active profile.
    - device set supports vendor, role, notes, bus, tags, limits.
    - Device identity is label-only; manufacturer/deviceType/deviceId live only in bringup_system.json.
    - validate config [path] checks for group members missing from devices (file or local).
    - batch scripts are linted to ensure devices are defined before add device.
    - show group text output includes members and bindings.
    - show devices (local) lists the full profile-derived device inventory, not only group members.
    - show version prints the bridge_cli version; add --robot to query the roboRIO.
    - Windows EOF uses Ctrl+Z then Enter (Ctrl+D on POSIX shells).
    - Tables push uses TCP only: `profiles push` / `config push` (no NT apply).
    - Tables push applies in-memory on the robot and does not persist to disk.

    Tables push (config mode):
        profiles push <path> [--activate <profile>]
        config push <path> [--activate <profile>]

CONFIG
    Device lists are loaded from src\main\deploy\bringup_system.json via --profile.
    This keeps the PC tool aligned with the same file the roboRIO deploy uses.

    Labels in profiles must be unique. bridgeConfig.byProfile groups reference
    those labels so CLI groups stay consistent across tools.
    When loading a profiles file, per-profile groups remain scoped to their
    matching profile device list.
    Profiles schema_version is 4 (see docs/PROFILE_SCHEMA_REFACTOR.md).
    Device edits update profiles when a profiles file is loaded; use save profiles.
    save bridge-config writes groups-only output when profiles are loaded.

    If you need a standalone can_nt_config.json-style file for reference or
    external tooling, generate one from a profile:
        python tools\\can_nt\\can_nt_bridge.py --profile demo_club --dump-can-config tools\can_nt\can_nt_config.json

    The legacy tools\can_nt\can_nt_config.json is kept as a sample only (remove after unified config adoption).

EXAMPLES
    Default (USB RIO, auto-detect COM port):
        python tools\\can_nt\\can_nt_bridge.py --rio 172.22.11.2

    Explicit COM port:
        python tools\\can_nt\\can_nt_bridge.py --rio 172.22.11.2 --channel COM21

    More output (summary + device seen/missing messages):
        python tools\\can_nt\\can_nt_bridge.py --rio 172.22.11.2 --print-summary-period 2 --print-publish

    Use a custom config:
        python tools\\can_nt\\can_nt_bridge.py --profile demo_club --dump-can-config tools\can_nt\can_nt_config.json

    Choose a profile from the deploy-owned bringup_system.json:
        python tools\\can_nt\\can_nt_bridge.py --profile demo_club

    Publish unknown devices seen on the bus:
        python tools\\can_nt\\can_nt_bridge.py --profile demo_home_022326 --publish-unknown

    List or dump the published NT keys:
        python tools\\can_nt\\can_nt_bridge.py --profile demo_home_022326 --list-keys
        python tools\\can_nt\\can_nt_bridge.py --profile demo_home_022326 --dump-nt tools\can_nt\nt_keys.json

    List serial ports:
        python tools\\can_nt\\can_nt_bridge.py --list-ports

    Generate a profile from observed CAN traffic:
        python tools\\can_nt\\can_nt_bridge.py --dump-profile tools\can_nt\sniffer_profile.json

    Capture CAN device inventory for later diffing:
        python tools\\can_nt\\can_nt_bridge.py --dump-api-inventory tools\can_nt\inventory_a.json --dump-api-inventory-after 5

    Diff two inventories:
        python tools\\can_nt\\can_nt_bridge.py --diff-inventory tools\can_nt\inventory_a.json tools\can_nt\inventory_b.json

    Live Wireshark capture (Windows named pipe):
        wireshark -k -i \\.\pipe\FRC_CAN
        python tools\\can_nt\\can_nt_bridge.py --pcap-pipe FRC_CAN

    PCAP/PCAPNG file capture:
        python tools\\can_nt\\can_nt_bridge.py --pcap tools\can_nt\logs\robot_run.pcapng

    Reload profiles during a run:
        Press `r` to reload bringup_system.json and refresh labels.

COMMON COMMANDS
    Explicit COM port:
        python tools\\can_nt\\can_nt_bridge.py --channel COM21 --rio 172.22.11.2

    Live Wireshark (named pipe):
        wireshark -k -i \\.\pipe\FRC_CAN
        python tools\\can_nt\\can_nt_bridge.py --pcap-pipe FRC_CAN

    PCAP/PCAPNG file capture:
        python tools\\can_nt\\can_nt_bridge.py --pcap tools\can_nt\logs\robot_run.pcapng

    Summary JSON + console summary prints:
        python tools\\can_nt\\can_nt_bridge.py --publish-can-summary --print-summary-period 2

    Print device seen/missing transitions:
        python tools\\can_nt\\can_nt_bridge.py --print-publish

    Capture only (no NetworkTables):
        python tools\\can_nt\\can_nt_bridge.py --no-nt --pcap tools\can_nt\logs\capture.pcapng

REAL-TIME NOTES (WHY OUTPUT IS THROTTLED)
    The robot runs a 20ms periodic loop. Console printing is slow and can cause overruns.
    Report-like output is intentionally paced and chunked to avoid stalling robot control.
    Expect longer reports to stream over multiple cycles rather than printing all at once.

UI COMMAND PROTOCOL
    Purpose: Define the TCP command/ack/output flow between the PC UI and the roboRIO.

    Transport:
    - TCP, line-delimited JSON over port 5809 by default (set with --ui-tcp-port).
    - NetworkTables remains in use for state/diagnostics visibility.

    TCP command payload (PC -> roboRIO):
    - type = "cmd"
    - seq (int, monotonic)
    - name (string)
    - args (object, optional)
    - ts (double, seconds)
    - clientId (string, required; unique per UI instance)

    TCP ack payload (roboRIO -> PC):
    - type = "ack"
    - seq (int)
    - name (string)
    - status ("ok" or "error")
    - message (string)
    - ts (double, echo cmd/ts)
    - sessionId (string)
    - state (object: enabled/estopped/mode)

    TCP out payload (roboRIO -> PC):
    - type = "out"
    - seq (int)
    - name (string)
    - text (string)
    - ts (double, echo cmd/ts)
    - json (string, optional structured payload)
    - sessionId (string)
    - state (object: enabled/estopped/mode)

    State/heartbeat (NT, roboRIO -> PC):
    - bringup/ui/state/enabled (bool)
    - bringup/ui/state/estopped (bool)
    - bringup/ui/state/mode (string)
    - bringup/ui/state/lastAckMs (double)
    - bringup/ui_tcp/enabled (bool, when protocol monitor is enabled)
    - bringup/ui_tcp/connected (bool)
    - bringup/ui_tcp/lastSeq (int)
    - bringup/ui_tcp/lastName (string)
    - bringup/ui_tcp/lastStatus (string)
    - bringup/ui_tcp/lastMessage (string)
    - bringup/ui_tcp/activeClientId (string)

    Send/receive rules:
    - Commands are half-duplex: send one, wait for ACK + OUT.
    - Every command produces one ACK and one OUT response.

    UI gating (half-duplex):
    - UI allows only one outstanding command at a time.
    - UI enforces a tight timeout and will retry the last command once after recovery.
    - UI blocks commands when TCP is disconnected.
    - To switch PCs, the active UI must send uiDisconnect or the robot must reboot.

    Notes:
    - The OUT message is a short per-command status, not the full report text.
    - Full reports still print via the roboRIO report runner and console.

    Handshake:
    - Use name = uiHandshake to establish session and seed seq after reconnect.
    - UI may send {"reset": true} to request a session reset.
    - The OUT json payload includes sessionId, lastAckSeq, minNextSeq, protocolVersion.
    - The roboRIO remains authoritative for seq; UI should always use minNextSeq.
    - uiDisconnect releases the active client lock (same clientId only).
    - If state/lastAckMs goes stale, the UI reports \"Robot state stale (code not running?)\".
    - uiMonitorEnable / uiMonitorDisable toggle NT protocol monitoring under bringup/ui_tcp.

UI HELP
    Purpose: Describe the in-app Help content for the Bringup Control UI.
    - Use Help -> Help to open the tabbed reference window.
    - Tabs include Overview, Profiles, Reports, Tests, System, and Troubleshooting.
    - Each tab is scrollable for long descriptions.
    - Command buttons show short hover tooltips for quick reminders.

LIVE TOPOLOGY OVERLAY
    Purpose: Show live device presence and telemetry in the Bringup Control UI.
    - Open the Live Topology tab.
    - Enable Live Overlay to begin polling runtime state.
    - Show Groups toggles bridgeConfig.byProfile group boxes/labels in the live view.
    - Source = tcp uses the UI TCP channel; Source = file loads a JSON snapshot manually.
    - Use Load File... to pick a snapshot, then Reload File to refresh it.
    - Update rate defaults to 5 Hz; adjust in the Live Topology controls.
    - Sample snapshot: tools\can_nt\samples\sample_runtime_state.json
    - Color legend:
        - Green: presenceConfidence >= 0.5 or lastSeen is recent (<~2s).
        - Orange: weak/stale presence (presenceConfidence 0.05..0.5 or lastSeen >~2s).
        - Gray: presenceConfidence <= 0.05.
        - Vendor color only: no live data for this device.

UI SCREENSHOT
    Purpose: Provide a visual reference for the Bringup Control UI layout.
    - Screenshot: ![Bringup Control UI](../docs/images/bringup_ui_tests.png)

UI OUTPUT EXAMPLES
    Purpose: Show typical UI output blocks (shortened).
    Example (Tests Info):
        15:57:32 CMD printTestsInfo
        15:57:32 ACK 470 printTestsInfo ok OK
        15:57:32 OUT 470 printTestsInfo
        === Bringup Tests Info ===
        Resolved path: /home/lvuser/deploy/bringup_system.json (bridgeConfig.byProfile.<profile>.tests)
        Test count: 10
        ==========================

    Example (Run Selected Test):
        Command: runTest (UI)
        Test started: Rotation only (internal)
        Test: Rotation only (internal)
        Test result: Rotation only (internal) = PASS (Reached rotation limit (NEO CAN 25))

    List serial ports:
        python tools\\can_nt\\can_nt_bridge.py --list-ports

    List NT keys it publishes:
        python tools\\can_nt\\can_nt_bridge.py --list-keys

    Dump NT key inventory to JSON:
        python tools\\can_nt\\can_nt_bridge.py --dump-nt tools\can_nt\nt_keys.json

    Publish unknown devices seen on bus:
        python tools\\can_nt\\can_nt_bridge.py --publish-unknown

    Dump observed labels:
        python tools\\can_nt\\can_nt_bridge.py --dump-can-expected-ids tools\can_nt\seen_ids.json --dump-after 3.0

    Generate a profile from observed traffic:
        python tools\\can_nt\\can_nt_bridge.py --dump-profile tools\can_nt\sniffer_profile.json

    Dump CAN inventory for later diff:
        python tools\\can_nt\\can_nt_bridge.py --dump-api-inventory tools\can_nt\inventory_a.json --dump-api-inventory-after 5

    Dump a can_nt_config.json-style file from a profile:
        python tools\\can_nt\\can_nt_bridge.py --profile demo_club --dump-can-config tools\can_nt\can_nt_config.json

    Diff two inventories:
        python tools\\can_nt\\can_nt_bridge.py --diff-inventory tools\can_nt\inventory_a.json tools\can_nt\inventory_b.json

    Use a specific profile from bringup_system.json:
        python tools\\can_nt\\can_nt_bridge.py --profile demo_club

WIRESHARK
    Marker capture (pcapng):
        See reverse_eng.md for marker usage, key map, and filters.

    Live pipe (Windows):
        Start Wireshark with -k -i \\.\pipe\FRC_CAN before running --pcap-pipe FRC_CAN.

OPTIONS
    --version                Print version and exit.
    --channel COMx            CANable COM port. If omitted, auto-detects the
                              first port whose description contains "USB Serial Device".
    --interface slcan         CAN interface (default slcan).
    --bitrate 1000000         Bitrate (default 1000000 for FRC CAN).
    --sources PATH            Multi-analyzer sources config (JSON).
    --visibility-timeout-ms N Visibility timeout for source visibility (ms).
    --observed-retention-ms N Retention for observed-but-unexpected devices (ms).
    --timeout SECONDS         Device missing timeout.
    --print-publish           Print when a device is seen or goes missing.
    --print-summary-period N  Print CAN summary every N seconds (0 disables).
    --publish-unknown         Publish devices not in profile as UNKNOWN.
    --list-keys               Print published NT keys and exit.
    --dump-nt PATH            Write JSON list of published NT keys and exit.
    --auto-match TEXT         Substring used to auto-detect the serial device.
    --no-prompt               Disable port selection prompt when multiple matches.
    --list-ports              Print available serial ports and exit.
    --dump-profile PATH       Write a bringup_system.json from observed CAN IDs.
    --dump-profile-name NAME  Profile name inside generated file (default sniffer_YYYYMMDD_HHMMSS).
    --dump-profile-after SEC  Delay before writing --dump-profile (default 3.0).
    --dump-profile-include-unknown  Include unknown devices in generated profile.
    --dump-api-inventory PATH Write CAN device inventory JSON and exit.
    --dump-api-inventory-after SEC  Delay before writing inventory (default 3.0).
    --dump-can-config PATH    Write a can_nt_config.json-style file from --profile and exit.
    --diff-inventory A B      Diff two inventory JSON files.
    --diff-top N              Rows to show for each diff section (default 10).
    --pcap PATH               Write capture file (.pcapng enables markers).
    --pcap-pipe NAME          Write live pcapng to Windows named pipe.
                              Wireshark can open \\.\pipe\<NAME>.
    --enable-markers          Enable keyboard marker injection (pcapng only).
    --disable-markers         Disable keyboard marker injection.
    --marker-id 0x1FFC0D00    Marker arbitration ID (extended).
    --capture-note TEXT       Pcapng section header comment.
    --no-nt                   Disable NetworkTables publishing (capture only).
    --cli                     Launch the interactive bridge CLI.
    --batch                   Run the bridge CLI in batch mode (requires --script).
    --script PATH             Script file to execute in batch mode.
    --conflict-policy POLICY  Device ownership policy: error (default) or move.

PUBLISHED KEYS
    bringup/diag/busErrorCount
    bringup/diag/dev/<labelKey>/label
    bringup/diag/dev/<labelKey>/status
    bringup/diag/dev/<labelKey>/presenceSource
    bringup/diag/dev/<labelKey>/presenceConfidence
    bringup/diag/dev/<labelKey>/ageSec
    bringup/diag/dev/<labelKey>/trafficAgeSec
    bringup/diag/dev/<labelKey>/statusAgeSec
    bringup/diag/dev/<labelKey>/msgCount
    bringup/diag/dev/<labelKey>/lastSeen
    bringup/diag/can/summary/json
    bringup/diag/can/pc/heartbeat
    bringup/diag/can/pc/openOk
    bringup/diag/can/pc/framesPerSec
    bringup/diag/can/pc/framesTotal
    bringup/diag/can/pc/readErrors
    bringup/diag/can/pc/lastFrameAgeSec
    bringup/diag/console/(dynamic keys per rule/device)
    bringup/diag/console/reset
    bringup/diag/console/system/warnCount
    bringup/diag/console/system/errorCount
    bringup/diag/console/system/fatalCount
    bringup/diag/console/devices/<labelKey>/warnCount
    bringup/diag/console/devices/<labelKey>/errorCount
    bringup/diag/console/devices/<labelKey>/fatalCount

NOTES
- Device identity is label-only in NT and inventory outputs; bringup_system.json is the
  source of CAN ID metadata when needed.
- `labelKey` is the percent-encoded label (UTF-8, safe chars `-_.~`).
    - Presence is derived from vendor-specific status-frame heuristics when available:
      - REV motor controllers: api_class=6 (periodic status).
      - CTRE devices: PF/PS 0xFF/0x00..0x07 (status), 0xEF (control-only).
      These are unverified heuristics aligned with the Wireshark dissector.
    - presenceConfidence values: HIGH, LOW, NONE (PC tool). The roboRIO report may compute a separate
      score/label using console warn/error/fatal counters.
    - --dump-profile cannot distinguish NEO vs FLEX or Kraken vs Falcon.
    - RobotV2 prints status=NO_DATA, ageSec=-, msgCount=- until a device is seen.
    - can/pc/heartbeat increments once per publish; can/pc/lastFrameAgeSec is seconds since last frame.
    - CANable Pro V2 ships with slcan firmware by default.


