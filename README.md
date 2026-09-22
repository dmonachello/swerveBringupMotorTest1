# Swerve Bringup Diagnostics System

## Purpose

This is the top-level guide to the robot bringup harness, the PC-side diagnostics tools, and the operator surfaces supported in this repo.

## Status

This project is in release-candidate stabilization for a first team-wide 1.0 release.

Current direction:

- core robot and host tooling are real and usable
- reliability and shared-state behavior are actively being hardened
- release/productization work is still in progress

See [docs/RELEASE_1_0_READINESS.md](docs/RELEASE_1_0_READINESS.md) for the current release checklist and [docs/RELEASE_STABILIZATION_REVIEW_2026-08-16.md](docs/RELEASE_STABILIZATION_REVIEW_2026-08-16.md) for the current blocker review.

## System Overview

This repository contains one system with two cooperating parts:

- **Robot-side**: a WPILib Java bringup harness on the roboRIO that instantiates devices, runs tests, commands outputs, and reports robot-local health
- **PC-side**: Windows-first Python tools that passively observe CAN traffic,
  consume robot command/log/state over REST, and provide operator-facing
  surfaces

Key safety rule:

- the PC tool is **read-only on CAN**

## Current architecture

The system uses a client/server model:

- the **robot is the server** and owns actuation
- the **PC tools are clients** for commands, logs, and diagnostics
- the **Xbox controller** is a local client of the robot server and has highest priority on control conflicts

Important data boundaries:

- robot-local telemetry comes from vendor APIs on the roboRIO
- CAN-bus telemetry comes from the host-side passive CAN tool
- REST command/log/state is a control and reporting channel, not a replacement for those telemetry sources

Start with [Getting Started](docs/GETTING_STARTED.md). For architecture details,
use the [architecture documentation hub](docs/mocs/architecture.md).

## Main surfaces

These are the operator-facing tools that matter today.

- **Bringup Control UI**
  - Windows-friendly Tk UI for runtime control, logs, live topology, evidence, tests, and CAN visibility
- **Bridge CLI**
  - text-oriented host surface for command execution, config/test workflows, and scripted operation
- **Topology Editor**
  - authors `bringup_system.json` devices, profiles, groups, and diagram metadata
- **Passive CAN Tool**
  - listens through CANable/slcan, publishes host diagnostics, and can capture PCAP/inventory artifacts

Related docs:

- [docs/OPERATOR_SURFACES.md](docs/OPERATOR_SURFACES.md)
- [docs/FEATURE_MATRIX.md](docs/FEATURE_MATRIX.md)

## Main files

These are the main code and config entry points.

### Robot side

- `src/main/java/frc/robot/Robot.java`
- `src/main/java/frc/robot/BringupCore.java`
- `src/main/java/frc/robot/BringupRuntime.java`
- `src/main/java/frc/robot/BridgeUiCommandHandler.java`

### Host side

- `tools/can_nt/bringup_ui.py`
- `tools/can_nt/bridge_cli.py`
- `tools/can_nt/can_nt_bridge.py`
- `tools/can_topology/can_top_editor.py`
- `tools/can_topology/live_topology_view.py`

### Shared config

- `src/main/deploy/bringup_system.json`
- `src/main/deploy/bringup_bindings.json`

## What the system does well today

- staged robot bringup with controlled actuation
- profile-backed device and group configuration
- repeatable DSL-based test execution
- live host-side control through UI and CLI
- passive CAN visibility and evidence capture
- topology-aware live views and editor tooling
- growing regression coverage across shared host behavior

## What to be careful about

- this repo still contains multiple historical workflows and helper paths
- not every feature is equally mature
- the project is not yet packaged as a finished 1.0 operator product
- some docs and feature specs describe in-progress or future work, not always current supported behavior

## Recommended starting path

This is the practical entry path without pretending the release is more finished than it is.

1. Read [Getting Started](docs/GETTING_STARTED.md).
2. Complete [Windows setup](docs/SETUP.md).
3. Follow the [new robot bringup workflow](docs/WORKFLOW_01_NEW_ROBOT_BRINGUP.md).
4. Validate and sync config before using the robot workflow.
5. Use either the Bringup Control UI or Bridge CLI as the main runtime surface.

## Windows-first host workflow

This section covers the host assumptions that matter most.

The PC-side tools are primarily intended for a Windows Driver Station or development laptop.

Common host tasks:

- run the passive CAN tool against a CANable/slcan COM port
- connect the UI or CLI to the robot REST command server
- validate/sync config and tests before robot use
- capture evidence and logs during bringup

See:

- [Windows setup](docs/SETUP.md)
- [Windows offline testing](docs/TESTING_WINDOWS_OFFLINE.md)

## Configuration model

This is the shared config model at a high level.

`src/main/deploy/bringup_system.json` is the main system config file and contains:

- shared device inventory
- one or more profiles
- group definitions
- topology/diagram metadata
- DSL tests under `bridgeConfig`

Rule:

- profiles choose subsets of the shared device inventory
- host context and robot runtime context are intentionally distinct

See:

- [Bringup profiles schema](docs/bringup_profiles_schema.md)
- [Profile schema refactor](docs/PROFILE_SCHEMA_REFACTOR.md)

## Safety model

These are the main safety and ownership rules.

- the robot owns actuation
- the Xbox controller has highest priority over host clients
- stop/disable/abort behavior is safety-critical
- Driver Station stop and E-stop still work as the normal keyboard/operator stop path for tests and motion
- Driver Station disable, E-stop, and explicit robot safety-stop paths stop outputs
- REST stop, disconnect, and timeout cancellation are known stability gaps until
  robot-thread cancellation is implemented and verified
- the PC CAN tool must never transmit by default

See:

- [Architecture documentation hub](docs/mocs/architecture.md)
- [Historical TCP UI protocol](docs/TCP_UI_PROTOCOL.md)

## Current validation commands

These are the repo checks people use most often.

For local Ollama regression reports and automated Git check-ins, use the
[local AI automation user guide](docs/LOCAL_AI_AUTOMATION_USER_GUIDE.md).

### Maintained non-robot regressions

```powershell
python tools/can_nt/scripts/run_regressions.py --suite all
```

### Robot-connected non-motion regression

```powershell
python tools/can_nt/scripts/bridge_cli_robot_non_motion_regression.py --rio 172.22.11.2
```

### Java unit tests

```powershell
.\gradlew.bat test
```

### Local AI regression report

```powershell
.\tools\local-regression-report.ps1
```

### Local AI check-in preview

```powershell
.\tools\local-checkin.ps1 -DryRun
```

### Config validation / sync

```powershell
python -m tools.validate_sync
```

## Documentation index

These are the docs worth opening first.

### Start here

- [Getting Started](docs/GETTING_STARTED.md)
- [Windows setup](docs/SETUP.md)
- [Architecture documentation hub](docs/mocs/architecture.md)
- [Operator surfaces](docs/OPERATOR_SURFACES.md)
- [Testing](docs/TESTING.md)

### Release / readiness

- [Alpha release readiness](docs/ALPHA_RELEASE_READINESS.md)
- [1.0 release readiness](docs/RELEASE_1_0_READINESS.md)

### Contracts / protocols

- [Historical TCP UI protocol](docs/TCP_UI_PROTOCOL.md)
- [Retired NetworkTables contract](docs/NT_CONTRACT.md)
- [Bridge CLI full specification](docs/BRIDGE_CLI_FULL_SPEC.md)

## Notes

This section clarifies what this README is and is not.

This README is intentionally a top-level orientation document.

It does not try to fully describe:

- every feature spec
- every legacy helper path
- every experimental reverse-engineering workflow
- every in-progress architecture refactor

For those, use the detailed docs under `docs/`.
