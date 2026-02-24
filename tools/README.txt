FRC CAN Bringup Diagnostics (Python)
Version: 0.1.0-2026-02-22

What this is
- Reads live FRC CAN traffic (via python-can)
- Publishes device presence/age/count to NetworkTables under /bringup/diag/...
- Optionally publishes a CAN arbitration-ID summary (as JSON)
- Optionally writes a Wireshark-readable capture (.pcapng preferred)

Folder contents
- can_nt_bridge.py        Main program (run this)
- can_profiles.py         Profile device tables loaded from src/main/deploy/bringup_profiles.json
- can_analyzer.py         Tracks arbitration IDs: rates, stale/missing, changing bytes
- can_logging.py          PCAP/PCAPNG logging wrapper
- can_nt_publish.py       NetworkTables publishing helpers
- run_can_robot.bat       Convenience runner (robot profile)
- run_can_demo.bat        Convenience runner (demo_club profile)
- install_deps.bat        Installs Python dependencies via pip
- VERSION                 Version stamp

Requirements (Windows Driver Station)
- Python 3.10+ recommended
- python-can
- pyserial (only needed if you later add auto-port detection; safe to install anyway)
- NetworkTables client:
    - pyntcore (preferred; NT4)
    - pynetworktables (fallback; older NT2/NT3)

Wireshark capture
- Use --pcap logs\run.pcapng
- Open the file in Wireshark

Wireshark display filters (FRC CAN)
- Extended CAN frames only:
  can.flags.extended == 1
- By device ID (example 11):
  frccan.device_id == 11
- By manufacturer (REV=5, CTRE=4):
  frccan.manufacturer == 5
  frccan.manufacturer == 4
- By device type (Motor=2, Encoder=7, PDM=8):
  frccan.device_type == 2
  frccan.device_type == 7
  frccan.device_type == 8
- Full device match (mfg/type/id):
  frccan.manufacturer == 5 && frccan.device_type == 2 && frccan.device_id == 11
- Broadcast messages:
  frccan.device_type == 0 && frccan.manufacturer == 0
- Motor controller API class/index:
  frccan.device_type == 2 && frccan.api_class == 1
  frccan.device_type == 2 && frccan.api_class == 1 && frccan.api_index == 2
- Specific arbitration ID:
  can.id == 0x0205B80B

Quick start
1) Put this folder somewhere (example: C:\frc\can_tools)
2) Run install_deps.bat once
3) Plug in your CANable and note the COM port (Device Manager)
4) Double-click run_can_robot.bat (auto-detects COM port)

Typical commands
Robot run with capture:
  python can_nt_bridge.py --profile robot --interface slcan --channel COM3 --bitrate 1000000 --rio 172.22.11.2 --publish-can-summary --pcap logs\robot_run.pcapng

Dump observed arbitration IDs and exit:
  python can_nt_bridge.py --profile robot --interface slcan --channel COM3 --bitrate 1000000 --dump-can-expected-ids robot_seen_ids.json --dump-after 3.0 --pcap logs\seen_ids.pcapng

Notes
- This tool is read-only; it does not transmit on CAN.
- If your robot uses mDNS names, you can pass --rio roborio-####-frc.local
