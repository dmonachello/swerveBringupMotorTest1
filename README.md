# Swerve Bringup Diagnostics System

## Purpose

Provide a current top-level guide to the robot bringup harness, PC-side diagnostics tools, and the supported operator surfaces in this repository.

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
- **PC-side**: Windows-first Python tools that passively observe CAN traffic, consume robot command/log/state over REST/TCP, and provide operator-facing surfaces

Key safety rule:

- the PC tool is **read-only on CAN**

## Current Architecture

The current architecture is a client/server model:

- the **robot is the server** and owns actuation
- the **PC tools are clients** for commands, logs, and diagnostics
- the **Xbox controller** is a local client of the robot server and has highest priority on control conflicts

Important data boundaries:

- robot-local telemetry comes from vendor APIs on the roboRIO
- CAN-bus telemetry comes from the host-side passive CAN tool
- REST command/log/state is a control and reporting channel, not a replacement for those telemetry sources

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the detailed architecture.

## Main Surfaces

Purpose: list the operator-facing tools that matter today.

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

## Main Files

Purpose: identify the primary code and config entry points.

### Robot Side

- `src/main/java/frc/robot/RobotV2.java`
- `src/main/java/frc/robot/BringupCore.java`
- `src/main/java/frc/robot/BringupRuntime.java`
- `src/main/java/frc/robot/BridgeUiCommandHandler.java`

### Host Side

- `tools/can_nt/bringup_ui.py`
- `tools/can_nt/bridge_cli.py`
- `tools/can_nt/can_nt_bridge.py`
- `tools/can_topology/can_top_editor.py`
- `tools/can_topology/live_topology_view.py`

### Shared Config

- `src/main/deploy/bringup_system.json`
- `src/main/deploy/bringup_bindings.json`

## What The System Does Well Today

- staged robot bringup with controlled actuation
- profile-backed device and group configuration
- repeatable DSL-based test execution
- live host-side control through UI and CLI
- passive CAN visibility and evidence capture
- topology-aware live views and editor tooling
- growing regression coverage across shared host behavior

## What To Be Careful About

- this repo still contains multiple historical workflows and helper paths
- not every feature is equally mature
- the project is not yet packaged as a finished 1.0 operator product
- some docs and feature specs describe in-progress or future work, not always current supported behavior

## Recommended Starting Path

Purpose: give a practical current entry path without pretending the release is more finished than it is.

1. Read [docs/SETUP.md](docs/SETUP.md).
2. Read [docs/USER_GUIDE.md](docs/USER_GUIDE.md).
3. Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) if you need the system model.
4. Validate/sync config before using the robot workflow.
5. Use either the Bringup Control UI or Bridge CLI as the main runtime surface.

## Windows-First Host Workflow

Purpose: describe the most relevant host assumptions.

The PC-side tools are primarily intended for a Windows Driver Station or development laptop.

Common host tasks:

- run the passive CAN tool against a CANable/slcan COM port
- connect the UI or CLI to the robot REST command server
- validate/sync config and tests before robot use
- capture evidence and logs during bringup

See:

- [docs/SETUP.md](/abs/path/c:/Users/dmona/swerve3/docs/SETUP.md)
- [docs/TESTING_WINDOWS_OFFLINE.md](/abs/path/c:/Users/dmona/swerve3/docs/TESTING_WINDOWS_OFFLINE.md)

## Configuration Model

Purpose: explain the core shared config at a high level.

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

- [docs/bringup_profiles_schema.md](/abs/path/c:/Users/dmona/swerve3/docs/bringup_profiles_schema.md)
- [docs/PROFILE_SCHEMA_REFACTOR.md](/abs/path/c:/Users/dmona/swerve3/docs/PROFILE_SCHEMA_REFACTOR.md)

## Safety Model

Purpose: summarize the main safety and ownership rules.

- the robot owns actuation
- the Xbox controller has highest priority over host clients
- stop/disable/abort behavior is safety-critical
- Driver Station stop and E-stop still work as the normal keyboard/operator stop path for tests and motion
- host disconnect or stale session paths must fail safe
- the PC CAN tool must never transmit by default

See:

- [docs/ARCHITECTURE.md](/abs/path/c:/Users/dmona/swerve3/docs/ARCHITECTURE.md)
- [docs/TCP_UI_PROTOCOL.md](/abs/path/c:/Users/dmona/swerve3/docs/TCP_UI_PROTOCOL.md)

## Current Validation Commands

Purpose: list the current commonly used repo checks.

### Python Regressions

```powershell
python tools/can_nt/scripts/bridge_cli_v1_group_targeting_regression.py
python tools/can_nt/scripts/bridge_cli_group_targeting_4m2g3t_regression.py
```

### Robot-Connected Non-Motion Regression

```powershell
python tools/can_nt/scripts/bridge_cli_robot_non_motion_regression.py --rio 172.22.11.2
```

### Java Unit Tests

```powershell
.\gradlew.bat test
```

### Config Validation / Sync

```powershell
python -m tools.validate_sync
```

## Documentation Index

Purpose: point to the most important docs first.

### Start Here

- [docs/SETUP.md](/abs/path/c:/Users/dmona/swerve3/docs/SETUP.md)
- [docs/USER_GUIDE.md](/abs/path/c:/Users/dmona/swerve3/docs/USER_GUIDE.md)
- [docs/ARCHITECTURE.md](/abs/path/c:/Users/dmona/swerve3/docs/ARCHITECTURE.md)
- [docs/OPERATOR_SURFACES.md](/abs/path/c:/Users/dmona/swerve3/docs/OPERATOR_SURFACES.md)
- [docs/TESTING.md](/abs/path/c:/Users/dmona/swerve3/docs/TESTING.md)

### Release / Readiness

- [docs/ALPHA_RELEASE_READINESS.md](/abs/path/c:/Users/dmona/swerve3/docs/ALPHA_RELEASE_READINESS.md)
- [docs/RELEASE_1_0_READINESS.md](/abs/path/c:/Users/dmona/swerve3/docs/RELEASE_1_0_READINESS.md)

### Contracts / Protocols

- [docs/TCP_UI_PROTOCOL.md](/abs/path/c:/Users/dmona/swerve3/docs/TCP_UI_PROTOCOL.md)
- [docs/NT_CONTRACT.md](/abs/path/c:/Users/dmona/swerve3/docs/NT_CONTRACT.md)
- [docs/BRIDGE_CLI_FULL_SPEC.md](/abs/path/c:/Users/dmona/swerve3/docs/BRIDGE_CLI_FULL_SPEC.md)

## Notes

Purpose: clarify what this README is and is not.

This README is intentionally a current top-level orientation document.

It does not try to fully describe:

- every feature spec
- every legacy helper path
- every experimental reverse-engineering workflow
- every in-progress architecture refactor

For those, use the detailed docs under `docs/`.
