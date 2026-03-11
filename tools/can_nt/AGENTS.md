# tools/ : Python CANable -> NetworkTables bridge + logging

Purpose
- Passive CAN listener for FRC bringup diagnostics.
- Reads CAN frames from CANable (slcan interface, COMx channel on Windows).
- Decodes FRC extended arbitration IDs into manufacturer/device_type/api_class/api_index/device_id.
- Tracks last-seen, msg counts, and stale/missing.
- Publishes diagnostics to NetworkTables under bringup/diag.
- Optionally logs CAN traffic to PCAP/PCAPNG for Wireshark and/or CSV.

Hard rules
- Never transmit CAN frames. Read-only only.
- Preserve existing CLI flags and NT key paths unless explicitly asked to change them.
- Keep profiles data-driven. Demo vs robot should be selectable by command line.
- Keep Windows slcan workflow working.
- Keep hardware configuration easy to customize: profiles and device lists should be simple to edit and documented for quick team updates.
- The JSON report exposes telemetry under `devices[].attachments` (e.g., `type=revMotor` / `ctreMotor`) with fields such as `cmdDuty`, `appliedDuty`, and `motorCurrentA`.
- AI diagnosis guidance lives in `AI_DIAGNOSIS.md`.

Entry points and usage
- Main script: tools/can_nt/can_nt_bridge.py
- Run helpers: tools/can_nt/run_can_nt.cmd (or the provided .bat/.cmd wrappers)
- Dependency bootstrap: tools/can_nt/install_deps.bat

Change discipline
- If editing publishing keys, also update Java consumers in the same repo change.
- If adding new publish content, prefer additive keys rather than changing existing ones.
- Avoid cleverness. Prefer readable code and comments over micro-optimizations.

Testing checklist for tool changes
- Script starts and can open the CAN bus.
- Script can connect to the roboRIO NetworkTables server (or fails with clear message).
- Periodic summary output still works.
- PCAP/PCAPNG logging still produces a Wireshark-readable file when enabled.
