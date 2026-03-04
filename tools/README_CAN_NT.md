# CAN-NT-BRIDGE(1)

NAME
    can_nt_bridge.py - CAN -> NetworkTables bridge for RobotV2

SYNOPSIS
    python tools\can_nt_bridge.py [options]
    tools\run_can_nt.cmd [python.exe] [options]

DESCRIPTION
    Reads FRC CAN traffic from a CANable (SLCAN) and publishes diagnostics
    under bringup/diag for RobotV2. Can optionally write PCAP/PCAPNG or
    stream live PCAPNG into Wireshark via a Windows named pipe.

INSTALL
    py -m pip install pynetworktables
    py -m pip install python-can
    py -m pip install pyserial

RUN
    python tools\can_nt_bridge.py --rio 172.22.11.2

    tools\run_can_nt.cmd

    set CAN_NT_PYTHON=C:\Path\To\Python\python.exe
    tools\run_can_nt.cmd

    tools\run_can_nt.cmd C:\Path\To\Python\python.exe

    tools\run_can_nt.cmd --print-summary-period 2 --print-publish

    tools\run_can_nt.cmd C:\Path\To\Python\python.exe --verbose --quick-check

    If neither is set, the helper script:
    1) uses the first python in PATH
    2) falls back to %USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe

CONFIG
    Device lists are loaded from src\main\deploy\bringup_profiles.json via --profile.
    This keeps the PC tool aligned with robot profiles.

    If you need a standalone can_nt_config.json-style file for reference or
    external tooling, generate one from a profile:
        python tools\can_nt_bridge.py --profile demo_club --dump-can-config tools\can_nt_config.json

    The legacy tools\can_nt_config.json is kept as a sample only.

EXAMPLES
    Default (USB RIO, auto-detect COM port):
        python tools\can_nt_bridge.py --rio 172.22.11.2

    Explicit COM port:
        python tools\can_nt_bridge.py --rio 172.22.11.2 --channel COM21

    More output (summary + device seen/missing messages):
        python tools\can_nt_bridge.py --rio 172.22.11.2 --print-summary-period 2 --print-publish

    Use a custom config:
        python tools\can_nt_bridge.py --profile demo_club --dump-can-config tools\can_nt_config.json

    Choose a profile from bringup_profiles.json:
        python tools\can_nt_bridge.py --profile demo_club

    Publish unknown devices seen on the bus:
        python tools\can_nt_bridge.py --profile demo_home_022326 --publish-unknown

    List or dump the published NT keys:
        python tools\can_nt_bridge.py --profile demo_home_022326 --list-keys
        python tools\can_nt_bridge.py --profile demo_home_022326 --dump-nt tools\nt_keys.json

    List serial ports:
        python tools\can_nt_bridge.py --list-ports

    Generate a profile from observed CAN traffic:
        python tools\can_nt_bridge.py --dump-profile tools\sniffer_profile.json

    Capture API class/index inventory for later diffing:
        python tools\can_nt_bridge.py --dump-api-inventory tools\inventory_a.json --dump-api-inventory-after 5

    Diff two inventories:
        python tools\can_nt_bridge.py --diff-inventory tools\inventory_a.json tools\inventory_b.json

    Live Wireshark capture (Windows named pipe):
        wireshark -k -i \\.\pipe\FRC_CAN
        python tools\can_nt_bridge.py --pcap-pipe FRC_CAN

    PCAP/PCAPNG file capture:
        python tools\can_nt_bridge.py --pcap tools\logs\robot_run.pcapng

COMMON COMMANDS
    Explicit COM port:
        python tools\can_nt_bridge.py --channel COM21 --rio 172.22.11.2

    Live Wireshark (named pipe):
        wireshark -k -i \\.\pipe\FRC_CAN
        python tools\can_nt_bridge.py --pcap-pipe FRC_CAN

    PCAP/PCAPNG file capture:
        python tools\can_nt_bridge.py --pcap tools\logs\robot_run.pcapng

    Summary JSON + console summary prints:
        python tools\can_nt_bridge.py --publish-can-summary --print-summary-period 2

    Print device seen/missing transitions:
        python tools\can_nt_bridge.py --print-publish

    Capture only (no NetworkTables):
        python tools\can_nt_bridge.py --no-nt --pcap tools\logs\capture.pcapng

    List serial ports:
        python tools\can_nt_bridge.py --list-ports

    List NT keys it publishes:
        python tools\can_nt_bridge.py --list-keys

    Dump NT key inventory to JSON:
        python tools\can_nt_bridge.py --dump-nt tools\nt_keys.json

    Publish unknown devices seen on bus:
        python tools\can_nt_bridge.py --publish-unknown

    Dump observed arbitration IDs:
        python tools\can_nt_bridge.py --dump-can-expected-ids tools\seen_ids.json --dump-after 3.0

    Generate a profile from observed traffic:
        python tools\can_nt_bridge.py --dump-profile tools\sniffer_profile.json

    Dump API inventory for later diff:
        python tools\can_nt_bridge.py --dump-api-inventory tools\inventory_a.json --dump-api-inventory-after 5

    Dump a can_nt_config.json-style file from a profile:
        python tools\can_nt_bridge.py --profile demo_club --dump-can-config tools\can_nt_config.json

    Diff two inventories:
        python tools\can_nt_bridge.py --diff-inventory tools\inventory_a.json tools\inventory_b.json

    Use a specific profile from bringup_profiles.json:
        python tools\can_nt_bridge.py --profile demo_club

WIRESHARK
    Marker capture (pcapng):
        See reverse_eng.md for marker usage, key map, and filters.

    Live pipe (Windows):
        Start Wireshark with -k -i \\.\pipe\FRC_CAN before running --pcap-pipe FRC_CAN.

OPTIONS
    --channel COMx            CANable COM port. If omitted, auto-detects the
                              first port whose description contains "USB Serial Device".
    --interface slcan         CAN interface (default slcan).
    --bitrate 1000000         Bitrate (default 1000000 for FRC CAN).
    --timeout SECONDS         Device missing timeout.
    --print-publish           Print when a device is seen or goes missing.
    --print-summary-period N  Print CAN summary every N seconds (0 disables).
    --publish-unknown         Publish devices not in profile as UNKNOWN.
    --list-keys               Print published NT keys and exit.
    --dump-nt PATH            Write JSON list of published NT keys and exit.
    --auto-match TEXT         Substring used to auto-detect the serial device.
    --no-prompt               Disable port selection prompt when multiple matches.
    --list-ports              Print available serial ports and exit.
    --dump-profile PATH       Write a bringup_profiles.json from observed CAN IDs.
    --dump-profile-name NAME  Profile name inside generated file (default sniffer_YYYYMMDD_HHMMSS).
    --dump-profile-after SEC  Delay before writing --dump-profile (default 3.0).
    --dump-profile-include-unknown  Include unknown devices in generated profile.
    --dump-api-inventory PATH Write apiClass/apiIndex inventory JSON and exit.
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

PUBLISHED KEYS
    bringup/diag/busErrorCount
    bringup/diag/dev/<mfg>/<type>/<id>/label
    bringup/diag/dev/<mfg>/<type>/<id>/status
    bringup/diag/dev/<mfg>/<type>/<id>/presenceSource
    bringup/diag/dev/<mfg>/<type>/<id>/presenceConfidence
    bringup/diag/dev/<mfg>/<type>/<id>/ageSec
    bringup/diag/dev/<mfg>/<type>/<id>/trafficAgeSec
    bringup/diag/dev/<mfg>/<type>/<id>/statusAgeSec
    bringup/diag/dev/<mfg>/<type>/<id>/msgCount
    bringup/diag/dev/<mfg>/<type>/<id>/lastSeen
    bringup/diag/dev/<mfg>/<type>/<id>/manufacturer
    bringup/diag/dev/<mfg>/<type>/<id>/deviceType
    bringup/diag/dev/<mfg>/<type>/<id>/deviceId
    bringup/diag/can/summary/json
    bringup/diag/can/pc/heartbeat
    bringup/diag/can/pc/openOk
    bringup/diag/can/pc/framesPerSec
    bringup/diag/can/pc/framesTotal
    bringup/diag/can/pc/readErrors
    bringup/diag/can/pc/lastFrameAgeSec

NOTES
    - Device IDs use the lowest 6 bits of the CAN extended ID.
    - Inventory snapshots key on (manufacturer, device_type, apiClass, apiIndex, device_id).
    - Presence is derived from vendor-specific status-frame heuristics when available:
      - REV motor controllers: api_class=6 (periodic status).
      - CTRE devices: PF/PS 0xFF/0x00..0x07 (status), 0xEF (control-only).
      These are unverified heuristics aligned with the Wireshark dissector.
    - --dump-profile cannot distinguish NEO vs FLEX or Kraken vs Falcon.
    - RobotV2 prints status=NO_DATA, ageSec=-, msgCount=- until a device is seen.
    - can/pc/heartbeat increments once per publish; can/pc/lastFrameAgeSec is seconds since last frame.
    - CANable Pro V2 ships with slcan firmware by default.
