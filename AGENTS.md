# FRC Bringup Diagnostics System (Java roboRIO + Python CANable tool)

This repo is one system with two cooperating parts:
- Robot-side WPILib Java bringup harness that actively runs motors/sensors on the roboRIO.
- PC-side Python tool that passively listens to the robot CAN bus via CANable (slcan over COM port) and publishes diagnostics to NetworkTables for the robot code and dashboards.

Hard rules
- The Python side must be read-only on CAN. Never transmit CAN frames.
- Do not assume how the Java code uses NetworkTables. Before changing any NT keys, first inventory current usage in Java and Python and produce a short report.
- NetworkTables paths are an API contract. If any key path changes, update both sides in the same change and keep backward compatibility for at least one iteration.
- Windows is the primary host for the Python tool (Driver Station laptop). Avoid Linux-only assumptions (SocketCAN, can0, etc) unless explicitly requested.
- Prefer small, reversible diffs. No sweeping refactors unless asked.

What to do first for any task that touches the Java-Python interface
1) Inventory NetworkTables usage:
   - List every path written and read on the Java side.
   - List every path published by the Python tool.
   - Identify overlaps, mismatches, and dead keys.
   Do not edit code in this step.

2) Propose the contract:
   - Which side owns which keys.
   - Update cadence expectations (publish period).
   - Behavior when the Python tool is absent (Java must fail soft).
   Do not edit code in this step.

3) Implement changes:
   - Keep behavior stable unless the task explicitly asks for behavior change.
   - If renaming keys is necessary, mirror old keys for compatibility.

Definition of done
- Java code still builds and deploys via the normal GradleRIO workflow for this repo.
- Python tool still runs on Windows with CANable slcan COM port and FRC bitrate 1,000,000.
- Python tool still publishes bringup/diag keys without breaking existing dashboards/prints.
- PCAP/PCAPNG output (if enabled) still opens in Wireshark.

Where things live
- Java bringup code: src/main/java/... (look for RobotV2 and BringupUtil)
- Python CAN tool: tools/ (entrypoint can_nt_bridge.py)
