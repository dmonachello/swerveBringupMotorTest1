# Java robot bringup harness (WPILib)

Purpose
- This code actively tests real robot hardware on the roboRIO during bringup:
  - create and command motors/sensors
  - incrementally enable devices
  - stop outputs immediately on command
  - print device health and sensor readings
- It also consumes diagnostics from the PC-side Python tool via NetworkTables under bringup/diag.

Hard rules
- Safety first: ensure there is always a clear, immediate way to stop all outputs.
- Do not change CAN IDs or device tables without updating the Python tool profile tables in tools/ in the same change.
- Do not change NetworkTables paths without coordinated update with tools/ publisher.
- If the Python publisher is not running, Java code must behave sensibly (no crashes, no blocking).

Interface contract discipline
- Before altering any NT paths, search the codebase for all occurrences of:
  - NetworkTable / NetworkTables
  - SmartDashboard
  - Shuffleboard
  - bringup
  - diag
  Produce a short summary of current usage before editing.

Change discipline
- Keep changes small and testable.
- Prefer explicit code paths over abstract frameworks for bringup code.
- Keep operator controls and printouts stable unless asked to redesign them.
