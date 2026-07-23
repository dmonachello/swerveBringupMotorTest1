# Swerve Bringup Diagnostics System

**Version 1.0.0** | A comprehensive FRC motor and swerve drive bringup and diagnostics platform with dual robot-side and PC-side tooling.

## Overview

This repository contains an integrated bringup and diagnostics system for FRC robots with two main components:

- **Robot-side**: WPILib Java application (`RobotV2`) that actively runs motors, sensors, and tests on the roboRIO
- **PC-side**: Python tools that passively observe CAN traffic and provide diagnostics

The system is designed to make hardware issues obvious before wasting time on tuning or code bugs.

## Architecture

### Core Components

- **Robot Programs**:
  - `RobotV2.java` - Primary bringup program with full diagnostics and REST API
  - `Robot.java` - Legacy simplified bringup harness (for reference)
  - `BringupCore` - Device lifecycle and test execution engine
  - `BringupRuntime` - Shared state management across Xbox, CLI, and UI commands

- **Command System**:
  - `RobotLocalCommandRegistry` - Canonical command definitions
  - `RobotLocalCommandExecutor` - Command dispatch and execution
  - Xbox controller bindings via `BindingsManager`
  - TCP UI command ingress via `BridgeUiIngressPolicy`

- **CAN Bus**:
  - `CanBusHealth` - roboRIO CAN controller health sampling
  - Passive CAN observation via PC tool (`can_nt_bridge.py`)
  - Device presence and rate monitoring

- **PC-side Tools**:
  - `can_nt_bridge.py` - CAN listener, NT publisher, PCAP capture
  - `can_top_editor.py` - Topology editor GUI
  - `bump_version.py` - Version management helper
  - Regression test runners and config API guards

### Configuration

- `src/main/deploy/bringup_system.json` - Active device registry, profiles, and tests
- `src/main/deploy/bringup_bindings.json` - Xbox controller bindings
- Data-driven profiles enable rapid bringup iteration without recompiling robot code

### Diagnostics

- **Local diagnostics**: Health status, input bindings, device faults
- **CAN diagnostics**: Passive device presence/rates, bus utilization
- **Reports**: JSON snapshots, PCAP capture, NetworkTables publishing
- **Status codes**: Facility-based structured error codes with AI-assisted triage

## Quick Start

### Robot Deployment (roboRIO)

1. Open in WPILib VS Code and deploy as normal
2. Connect an Xbox controller
3. Press `Start` to add all configured devices
4. Press `D-pad Left` for local health checks
5. Press `D-pad Up` for CAN diagnostics report
6. Press `X` to dump `bringup_report.json`

### PC-side Setup (Windows)

1. Install dependencies:
```cmd
py -m pip install --upgrade python-can pyserial pynetworktables pyntcore prompt_toolkit python-docx
```

2. Run the CAN bridge:
```cmd
python tools/can_nt/can_nt_bridge.py --profile demo_home_022326 --interface slcan --channel COM3 --bitrate 1000000 --rio 172.22.11.2 --publish-can-summary
```

3. Optional: View live CAN traffic in Wireshark:
```cmd
wireshark -k -i \\.\pipe\FRC_CAN
python tools/can_nt/can_nt_bridge.py --pcap-pipe FRC_CAN
```

## Key Features

### Incremental Bringup
- Add one device at a time or all at once
- Safe stop controls with Xbox priority
- Device instantiation with vendor-specific diagnostics

### Configuration Management
- Define devices, CAN IDs, attachments, groups, and topology in shared JSON
- Push profiles to running robot over TCP without redeploying
- Profile rotation via gamepad (Press `Back` to cycle)
- In-memory apply; persists on redeploy

### Testing
- Data-driven test definitions in `bringup_system.json`
- Create and run repeatable motor/encoder tests
- Rich DSL support for scripted test flows
- Test authoring via Bridge CLI, UI, or JSON

### Diagnostics & Reporting
- Dual-source evidence: local roboRIO + passive CAN observation
- Real-time health status on NetworkTables
- Streamed console output with throttling (20ms loop friendly)
- JSON report generation with AI assistance
- PCAP/PCAPNG capture + Wireshark dissector support

### Safety Model
- Robot is the server; Xbox and TCP are clients
- Xbox always wins on conflicts
- Stop latch prevents unintended motion
- Driver Station E-stop overrides all

## Repository Structure

```
src/main/
  java/frc/robot/
    RobotV2.java              # Primary bringup program
    Robot.java                # Legacy simplified harness
    BringupCore.java          # Device lifecycle engine
    BringupRuntime.java       # Shared runtime state
    commands/local/           # Local command system
    input/                    # Controller input handling
    rest/                     # TCP UI REST API
    telemetry/                # Sampling and telemetry
    tests/                    # Test registry and execution
  deploy/
    bringup_system.json       # Active config (devices, profiles, tests)
    bringup_bindings.json     # Xbox controller bindings

tools/
  can_nt/
    can_nt_bridge.py          # PC-side CAN listener
    scripts/                  # Regression runners, CI helpers
  can_topology/
    can_top_editor.py         # Topology editor GUI
  status_codes/               # Status code generation
  common/                     # Shared Python utilities
  bump_version.py             # Version management
  add_journal_note.py         # Development notes helper

docs/
  ARCHITECTURE.md             # System design overview
  SETUP.md                    # Installation and configuration
  USER_GUIDE.md               # Usage workflows
  OPERATOR_SURFACES.md        # UI/CLI/topology editor reference
  TESTING.md                  # Test authoring and execution
  AI_DIAGNOSIS.md             # AI-assisted error triage
  CAN_BACKGROUND.md           # CAN protocol primer
```

## Workflow

### 2-Minute Pit Checklist

1. Enable robot in teleop
2. Press `Start` to instantiate all devices
3. Press `D-pad Left` → resolve local faults first
4. Press `D-pad Up` → resolve CAN bus errors
5. Press `D-pad Down` → verify passive visibility (if PC tool running)
6. Press `X` → dump report and use `docs/AI_DIAGNOSIS.md`

### Extended Debugging

1. Use Bridge CLI for config edits and test authoring
2. Push updates over TCP with `profiles push` / `config push`
3. Run scripted tests via Xbox or UI
4. Capture PCAP evidence with `--pcap` flag
5. Cross-reference topology, local state, and bus evidence

## Version Management

- **Robot app**: See `src/main/java/frc/robot/AppVersion.java`
- **PC tools**: Manage with `bump show <tool>`, `bump bump <tool> <field>`
- **Git metadata**: Stamp with `gitver` (builds build info into robot binary)

## Key Limitations

- Does not transmit CAN frames from PC (read-only by design)
- Does not persist config after TCP apply (in-memory only; redeploy to persist)
- Requires disciplined hardware isolation during bringup
- Some legacy docs/helpers in repo may not reflect latest workflows

## Documentation

See `docs/` directory for detailed guides:
- `ARCHITECTURE.md` - Design patterns and system contracts
- `SETUP.md` - Dependencies and configuration
- `USER_GUIDE.md` - End-to-end workflows
- `TESTING.md` - Test authoring DSL and execution
- `OPERATOR_SURFACES.md` - UI, CLI, and topology editor reference
- `ProfileRegistryPushSpec.md` - TCP config push protocol
- `FEATURE_SPEC_*.md` - Major feature design documents

## Development

### Build and Deploy

```bash
# Build robot code
./gradlew build

# Deploy to roboRIO
./gradlew deploy

# Run local Windows scripts
./cli.bat                    # Bridge CLI
./topo.bat                   # Topology editor
./ui.bat                     # Bringup Control UI (with CAN)
./uiNoCan.bat                # Bringup Control UI (offline mode)
```

### Run Regression Tests

```bash
# Local regression suite (no robot required)
python -m tools.can_nt.scripts.run_regressions local

# Full suite with robot
python -m tools.can_nt.scripts.run_regressions full --rio 172.22.11.2

# Topology-only regression
python -m tools.can_nt.scripts.topology_editor_regression
```

### Validate Config

```bash
# Validate profile schema and sync
python -m tools.validate_sync
```

## Notes

This is a living project with ongoing development. See `notes/planning/` for design intent and future work. Legacy documentation and helpers remain in the repo for reference but may not reflect the current workflow model.

For issues or questions, refer to the documentation or explore the Java/Python test suites for working examples.
