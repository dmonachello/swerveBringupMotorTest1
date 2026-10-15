# FRC Bringup Diagnostics System

## Purpose

This repository contains one integrated bringup system for FRC robots with two cooperating parts:

- Robot-side WPILib Java harness on the roboRIO that actively runs motors, sensors, and staged bringup actions.
- Host-side Python diagnostics on a Windows Driver Station or dev laptop that passively listens to the CAN bus via CANable/slcan, exposes host-local visibility, and supports REST-driven diagnostics and control via a full robot REST server implementation.
- Shared docs and specs that define CLI behavior, architecture, operator workflows, and pit-side diagnosis guidance.

The supported bringup workflow now uses a full REST server implementation on the robot; host tooling combines passive CAN observation with REST APIs to request commands, logs, and runtime state rather than relying on NetworkTables-only plumbing.

## Current architecture

### Robot side

The Java code lives under `src/main/java/frc/robot/` and is the active bringup harness for the roboRIO. The main runtime pieces include:

- `src/main/java/frc/robot/Robot.java`
- `src/main/java/frc/robot/BringupCore.java`
- `src/main/java/frc/robot/BringupRuntime.java`
- `src/main/java/frc/robot/BridgeUiCommandHandler.java`

This code owns the 20 ms robot loop, scheduler execution, motor control, and operator-driven bringup actions.

### Host side

The active host-side diagnostics tooling is in `tools/` and is primarily Windows-first.

- `tools/can_nt/` — passive CAN listener, CLI, local UI/bootstrap surfaces, REST plumbing, and host diagnostics
- `tools/can_topology/` — topology/editor and live topology views
- `tools/common/` — shared support code and common host logic
- `tools/status_codes/` — status/command status metadata and generated artifacts

The most relevant entry points include:

- `tools/can_nt/can_nt_bridge.py`
- `tools/can_nt/bridge_cli.py`
- `tools/can_nt/bringup_ui.py`
- `tools/validate_sync.py`
- `tools/sync_profiles.py`

### Shared config and generated artifacts

The repo includes both static robot config and generated artifacts used by the toolchain:

- `src/main/deploy/bringup_system.json`
- `src/main/deploy/bringup_bindings.json`
- generated command/status artifacts under `tools/status_codes/`
- formal grammar artifacts for CLI parsing under `tools/can_nt/bridge_cli_ebnf.txt` and linked generated outputs

## Safety and data-boundary rules

These are the operating rules that matter most for current code:

- The PC-side CAN tool is read-only on CAN. It must never transmit frames during supported bringup diagnostics.
- The only transmission exception is the isolated experimental package `tools/can_tx_poc/`, which must be explicit per invocation, off by default, and used only on a lab bus.
- Robot-local data and host-side CAN data are intentionally separate. Do not mix or conflate them in logging, diagnostics, or API output.
- NetworkTables is retired for supported bringup flows. If a reference remains, it is treated as historical, compatibility-only, or a regression unless explicitly justified.
- Windows is the primary host environment; Linux-only assumptions like `can0` are not the default design target for the supported workflows.

## Real-time reporting discipline

The robot loop runs on a 20 ms scheduler cycle. Console printing is intentionally avoided in large bursts because it stalls the control loop and risks missed behavior.

Current behavior is to route report-like output through a shared report runner that:

- queues output incrementally across cycles
- limits per-cycle work and print chunk size
- keeps reporting readable without starving the scheduler
- prevents direct print bursts in new report code

Any new report path should use the shared runner rather than emitting large console dumps directly.

## Repository layout

```text
.
├── docs/                          # architecture, specs, operator docs
├── gradlew, gradlew.bat           # Java build entry points
├── src/                           # WPILib robot code and deploy config
├── tools/                         # Python diagnostics, automation, generators
├── AGENTS.md                      # repo-level task rules and architecture constraints
├── build.gradle                   # Java project build configuration
├── settings.gradle                # Gradle project settings
├── README.md                      # project overview (this file)
├── profile.json                   # current team profile/config snapshot
├── bringup_tests.json             # bringup test definitions
├── can_table.txt                  # CAN inventory/lookup reference
├── cli.bat / ui.bat / uiNoCan.bat # common host-launch wrappers
├── requirements-windows.txt       # Windows Python dependencies
└── docs/GENERATED_ARTIFACTS_POLICY.md
```

## Common workflows

For day-to-day use, the main flows are:

1. Follow the setup and bringup docs under `docs/`.
2. Use the robot harness to run real actuation and bringup tests.
3. Run the host-side CAN tool on a CANable/slcan COM port to observe passive bus traffic.
4. Validate config and synchronization with the shared validation tooling.
5. Use the CLI/UI as the operator-facing surfaces for tests, control, and evidence capture.

## Recommended entry points

- Start here: `docs/GETTING_STARTED.md`
- Windows setup: `docs/SETUP.md`
- Architecture hub: `docs/mocs/architecture.md`
- Operator surfaces: `docs/OPERATOR_SURFACES.md`
- Testing: `docs/TESTING.md`
- AI diagnosis: `docs/AI_DIAGNOSIS.md`
- Current runtime rules baseline: `Current UI And Runtime Rules - V2.md`

## Current status

The repo is active and the project is centered on a real, working robot + PC bringup system rather than a conceptual prototype. The codebase emphasizes:

- hardened robot-side bringup behavior
- passively observed CAN diagnostics on Windows
- shared CLI/UI contracts
- data-driven device and profile configuration
- doc/spec discipline for generated artifacts and operator behavior

## Notes

This README is intentionally a top-level orientation guide. For detailed behavior, architecture context, data contracts, and supported workflows, use the docs under `docs/` and the active code under `src/` and `tools/`.
