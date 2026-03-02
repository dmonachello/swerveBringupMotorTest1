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
- Keep hardware configuration easy to customize: prefer data-driven profiles and ensure changes are documented for teams to update their device list quickly.
- The JSON report exposes telemetry under `devices[].attachments` (e.g., `type=revMotor` / `ctreMotor`) with fields such as `cmdDuty`, `appliedDuty`, and `motorCurrentA`.
- AI diagnosis guidance lives in `AI_DIAGNOSIS.md`.

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

Reverse engineering support on robot side (new work)

Purpose
- Robot code provides controlled, repeatable stimuli to make CAN traffic meaning observable.
- Reverse engineering depends on consistent "actions" whose start/stop times are clear.

Guidelines
- Keep bringup actions discrete and easy to repeat:
  - one device at a time
  - fixed setpoints (ex: +0.2, +0.4, -0.2)
  - fixed durations (ex: 2 seconds run, 1 second stop)
- Ensure there is always an immediate stop action that zeros outputs.
- When adding new bringup actions, print a clear console marker:
  - EXP_START <name>
  - EXP_STOP <name>
  Include device identity (NEO/Kraken/CANCoder + CAN ID) in the marker.

Preferred additions (optional, additive)
- Add a "scripted experiment mode" that runs a predefined sequence:
  - spin one motor forward, stop, reverse, stop
  - repeat for each device in the current profile
- This mode should be triggered by a single operator action (one key/button).
- Do not require Python to be running. If Python is present, it will capture; if not, robot still runs.

Non-negotiable
- Do not change CAN ID tables without updating the tools/ profile tables in the same change.
