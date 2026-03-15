# User Guide

## Purpose
Explain how the FRC bringup diagnostics system fits together and how to plan, bring up, and troubleshoot a robot.

## System Overview
Purpose: Summarize the major pieces and their roles.
- Robot bringup harness (Java, roboRIO) actively exercises motors/sensors.
- PC CAN listener (Python, CANable) passively captures CAN traffic and publishes diagnostics.
- Topology editor (Python/Tkinter) defines and documents device layouts and profiles.

## Major Pieces
Purpose: Describe the core components and where they live.

### Robot Bringup Harness (Java, roboRIO)
Purpose: Actively run devices and publish robot-side diagnostics.
- Location: `src/main/java/...` (notably `RobotV2` and `BringupUtil`).
- Runs on the WPILib 20ms loop, with report output throttled via a report runner.
- Publishes robot-side diagnostics to NetworkTables.
- Includes report commands users run to diagnose issues (e.g., inventory, limits, device state).

### PC CAN Listener (Python, CANable)
Purpose: Passively observe CAN traffic and publish bus diagnostics.
- Location: `tools/can_nt/can_nt_bridge.py`.
- Uses slcan on a Windows COM port at 1,000,000 bps.
- Hard rule: read-only on CAN (no frame transmit).
- Can emit PCAPNG captures and inventory JSON for offline analysis.

### Topology Editor (Python/Tkinter)
Purpose: Author and maintain device profiles and layouts.
- Location: `tools/can_topology/` (entry: `can_top_editor.py`).
- Edits `bringup_profiles.json` plus editor-only diagram metadata.
- Supports tags, filters, layout tools, and bulk edits to keep diagrams organized.

## Data Flow
Purpose: Describe how data moves between parts.
- `bringup_profiles.json` is the shared configuration source.
- The editor writes it; robot and PC tools consume it.
- Diagram metadata is editor-only and ignored by robot/PC tools.
- The robot publishes local diagnostics; the PC publishes CAN-bus diagnostics.
- Local robot data and PC CAN data are kept separate by design.

## Workflow
Purpose: Show how a user plans, brings up, and troubleshoots a robot.

### 1) Plan the Robot (Offline)
Purpose: Define a clear, shareable device layout.
- Open the topology editor: `tools/can_topology/can_top_editor.py`.
- Build or update the team profile in `bringup_profiles.json`.
- Use tags to group devices (e.g., `swerve`, `intake`, `left`, `right`).
- Use tidy/align tools to keep columns clean and readable.

### 2) Bring Up the Robot (Active on roboRIO)
Purpose: Exercise devices in controlled steps.
- Deploy the Java bringup harness (GradleRIO workflow).
- Select the intended profile.
- Enable specific devices and verify their behavior.
- Report output is throttled so the 20ms control loop stays responsive.
- Run built-in reports to capture snapshots of device configuration and state.

### 3) Observe Live CAN (Passive on PC)
Purpose: Independently verify bus traffic.
- Run `tools/can_nt/can_nt_bridge.py` with a CANable.
- Passively capture and publish CAN diagnostics to NetworkTables.
- Optionally save PCAPNG and inventory JSON for later diffing.

### 4) Troubleshoot Issues
Purpose: Isolate wiring, configuration, and device problems.
- Compare expected devices (profile) vs. observed devices (PC tool).
- Use tags to filter to the affected subsystem.
- Look for missing IDs, unexpected rates, or mismatched device types.
- Diff inventories between known-good and failing sessions to pinpoint changes.
- Use bringup reports to validate configuration (limits, inversion, device state) on the roboRIO side.

## How It Fits Together
Purpose: Explain why this architecture helps debugging.
- The profile is the shared source of truth for device identity and intent.
- The bringup harness provides controlled stimuli.
- The PC tool provides an independent, passive view of actual CAN traffic.
- The separation clarifies whether issues are wiring/configuration vs. control logic.

## Comparison
Purpose: Compare this system with related FRC tools.

### WPILib RobotBuilder
Purpose: Contrast code-structure generation vs. hardware bringup.
- RobotBuilder is a WPILib tool for creating robot programs using WPILib components. ?cite?turn1search0?
- This system focuses on validating real CAN hardware and wiring with live diagnostics, not code scaffolding.

### Vendor Device Tools
Purpose: Contrast vendor-specific configuration with multi-vendor bringup.
- Phoenix Tuner (including Tuner X) is a companion application used to configure, analyze, update, and control CTRE devices. ?cite?turn1search12?
- REV Hardware Client manages REV devices and provides device software updates. ?cite?turn1search1?
- This system provides a vendor-agnostic profile and passive CAN diagnostics across mixed devices.

### Dashboards and Log Viewers
Purpose: Contrast visualization-only tools with bringup workflows.
- Shuffleboard is a customizable driveteam-focused dashboard. ?cite?turn5search0?
- Glass is a dashboard and robot data visualization tool aimed at programmer debugging. ?cite?turn2search0?
- AdvantageScope is a data visualization tool for NetworkTables and WPILib/Driver Station logs. ?cite?turn6search1?
- FRC Dashboard is an extendable, web-based driving interface for FRC robots. ?cite?turn3search1?
- pynetworktables2js forwards NetworkTables key/value data over WebSocket for HTML/JavaScript dashboards. ?cite?turn3search3?
- This system adds profile-driven planning, bringup actions, and passive CAN inventory/diffing in addition to visualization.

### NetworkTables Inspection
Purpose: Contrast low-level NT debugging with profile-driven diagnostics.
- OutlineViewer is a utility for viewing, modifying, and adding NetworkTables values during debugging. ?cite?turn3search0?
- This system uses NetworkTables as a diagnostics transport but focuses on higher-level bringup workflows.

### Path Planning Tools
Purpose: Contrast motion planning tools with hardware bringup.
- PathWeaver is the WPILib tool used to draw the paths for a robot to follow. ?cite?turn2search2?
- PathPlanner is a motion profile generator for FRC robots. ?cite?turn3search2?
- These focus on autonomous trajectory planning rather than CAN device bringup.

### Control System Utilities
Purpose: Contrast system setup tools with bringup diagnostics.
- The FRC Game Tools installer includes the roboRIO Imaging Tool and images. ?cite?turn4search3?
- The roboRIO Imaging Tool is used to image a roboRIO with the latest software. ?cite?turn4search4?
- This system assumes the control system is already imaged and focuses on device-level validation.
## Notes
Purpose: Call out key rules and constraints.
- The PC CAN tool must never transmit CAN frames.
- NetworkTables keys are an API contract; changes must be coordinated.
- Diagram metadata is editor-only and must not be consumed by robot/PC tools.




