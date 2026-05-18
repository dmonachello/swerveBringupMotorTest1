# Swerve Bringup Diagnostics System

Purpose: Rapid, evidence-based bringup and CAN diagnostics for FRC swerve and other CAN devices.

This repo is one system with two cooperating parts:
- Robot-side WPILib Java bringup harness that actively runs motors and sensors on the roboRIO.
- PC-side Python tool that passively listens to the robot CAN bus via CANable (slcan over COM) and publishes diagnostics to NetworkTables.

## Why This Exists
Purpose: Make hardware issues obvious before you waste time on tuning or code bugs.

Highlights:
- Dual-source diagnostics that keep local roboRIO data separate from CAN-bus observations.
- Safe bringup controls with explicit stop-latch rules and Driver Station priority.
- Report runner that throttles console output to protect the 20ms control loop.
- PCAP/PCAPNG capture + Wireshark dissector for wire-level evidence.
- JSON reports and AI-assisted triage (`bringup_report.json` + `docs/AI_DIAGNOSIS.md`).
- Data-driven hardware profiles shared by robot code and the PC tool.
- Reverse-engineering inventory tooling for CAN traffic classification (additive).
- TCP-only command channel for UI/CLI actions (NetworkTables is diagnostics only).
- TCP registry push (`profiles push` / `config push`) with staged validation on the robot.

## Feature Matrix
Purpose: Show the main feature families, what they do, and which surface owns them today.

| Feature Area | What You Can Do | Main Surfaces | Robot Required | CANable Required |
| --- | --- | --- | --- | --- |
| Incremental bringup control | Add one device at a time, add all devices, stop safely, and exercise hardware in controlled steps | Robot runtime, Bringup UI, Bridge CLI | Yes | No |
| Manual group control | Create profile-scoped groups, bind controller inputs, and enable only selected members for ad hoc motion checks | Bridge CLI, robot runtime, topology editor for group authoring | Yes | No |
| Scripted bringup tests | Create, select, run, and iterate repeatable tests instead of driving hardware manually every time | Robot runtime, Bringup UI, Bridge CLI, config files | Yes | No |
| Robot Test DSL | Define richer scripted test flows with explicit sequencing, conditions, and stop behavior | Robot runtime, Bridge CLI authoring, config files | Yes | No |
| Profiles, devices, and topology | Define devices, CAN IDs, attachments, diagrams, tags, groups, and profile metadata in one shared config | Topology editor, Bridge CLI, shared `bringup_system.json` | No | No |
| Runtime config apply | Push profiles or full config to the robot over TCP without redeploying code | Bridge CLI, robot TCP UI handler | Yes | No |
| Local and robot diagnostics | Inspect local health, inputs, bindings, instantiated devices, faults, and report output | Robot runtime, Bringup UI, Bridge CLI | Yes | No |
| Passive CAN diagnostics | Observe device presence, rates, stale/missing devices, and CAN-side evidence without transmitting frames | CAN tool, NetworkTables, robot diagnostic consumers | No | Yes |
| Evidence capture and reporting | Dump `bringup_report.json`, capture PCAP/PCAPNG, save inventory snapshots, and keep artifacts for later analysis | Robot runtime, CAN tool, host scripts | Partial | Partial |
| Live topology and visibility | View topology overlays, profile structure, and passive visibility evidence against the authored model | Bringup UI live topology, topology editor, CLI show surfaces | No | No |
| Reverse-engineering support | Generate API inventories, top talkers, and byte-level evidence for unknown CAN traffic | CAN tool and analysis scripts | No | Yes |
| Regression and validation tooling | Run maintained local/full regression bundles and cross-surface config checks before shipping changes | Host regression scripts, validation tools | No | No |
| Pit diagnosis direction | Combine robot-local state, passive CAN evidence, topology, and operator clues for fault localization workflows | Specs, reports, topology model, future diagnosis surfaces | Partial | Partial |

## What You Can Do Today
Purpose: Answer the practical question: what jobs this repo already supports.

- Bring up a new robot one component at a time instead of energizing the whole system blindly.
- Define and edit profiles, device registries, groups, topology, and test metadata in a shared config.
- Run quick manual motor checks with group bindings and per-member enable/disable.
- Author repeatable bringup tests, including richer DSL-driven tests, and run them on the robot.
- Push config changes to a running robot over TCP without rebuilding code for every iteration.
- Passively watch the CAN bus from a Windows laptop with a CANable and compare bus evidence against robot-local behavior.
- Capture evidence artifacts such as streamed reports, `bringup_report.json`, PCAP/PCAPNG, and inventory snapshots.
- Use the same repo for authoring, execution, diagnostics, evidence capture, and regression verification.

## Which Tool For Which Job
Purpose: Point operators and developers to the right surface first.

- **Topology editor**: use when you are defining devices, CAN IDs, attachments, tags, layout, or groups in the shared config.
- **Bridge CLI**: use when you want text-driven config edits, group bindings, test authoring, push/apply commands, or scriptable workflows.
- **Bringup Control UI**: use when you want clickable control of reports, profile/test selection, and robot-connected bringup actions.
- **Robot runtime on the roboRIO**: use when you need actual device instantiation, actuation, test execution, and local vendor-API diagnostics.
- **CAN tool (`can_nt_bridge.py`)**: use when you need passive CAN visibility, NT publishing, PCAP capture, or reverse-engineering inventories.
- **Validation and regression scripts**: use when you changed behavior and need confidence that config, CLI, topology, DSL, and shared contracts still hold.

## What It Does Not Do
Purpose: Avoid confusion about scope and current limits.

- It does not replace vendor-specific setup and firmware tools.
- It does not transmit CAN frames from the PC side.
- It does not make robot config persistent on the roboRIO after a TCP apply; apply is in-memory.
- It does not eliminate the need for disciplined hardware isolation and safety checks during bringup.
- It does not mean every legacy helper or old doc in the repo has already been cleaned up to the newest workflow model.

## Quick Start
Purpose: Get a first bringup run in minutes.

Robot-side (roboRIO):
- Open in WPILib VS Code and deploy as normal.
- Connect an Xbox controller.
- Press `Start` to add all configured devices.
- Press `D-pad Left` for local health.
- Press `D-pad Up` for the CAN Diagnostics Report.
- Press `X` to dump `bringup_report.json`.

PC-side (Driver Station Windows PC):
- Install dependencies:
```cmd
py -m pip install --upgrade python-can pyserial pynetworktables pyntcore prompt_toolkit
```
- Run the CAN bridge:
```cmd
python tools\can_nt\can_nt_bridge.py --profile demo_home_022326 --interface slcan --channel COM3 --bitrate 1000000 --rio 172.22.11.2 --publish-can-summary
```

**Pit Flow (2-Minute Checklist)**
Purpose: Rapid triage before deeper debugging.

1. Enable the robot in teleop.
2. Press `Start` to add all configured devices.
3. Press `D-pad Left` and resolve any local faults or warnings.
4. Press `D-pad Up` and resolve bus errors or high utilization first.
5. If the PC tool is running, press `D-pad Down` and confirm devices are seen.
6. Press `X` to dump `bringup_report.json` and use `docs/AI_DIAGNOSIS.md`.

## Core Workflow
Purpose: A short, repeatable sequence for pit debugging.

1. Check local health (`D-pad Left`). Fix faults and warnings first.
2. Check CAN report (`D-pad Up`). Fix bus errors before touching devices.
3. Check CAN visibility (`D-pad Down`) if the PC tool is running.
4. Dump `bringup_report.json` (`X`) and use `docs/AI_DIAGNOSIS.md`.
5. Only then debug behavior and tuning.

## Safety Model (Client/Server)
Purpose: Keep actuation deterministic and safe.

- The robot is the server and owns actuation authority.
- PC tools are clients; Xbox is a local client with highest priority.
- Xbox always wins on conflicts.
- Stop/disable/abort sets a stop latch.
- Stop latch can be set by TCP or Xbox; only Xbox clears it.
- When stop latch is set, TCP start/enable/run commands are rejected.
- TCP loss or Xbox disconnect triggers a safe stop and sets the latch.
- Driver Station enable/disable/E-stop overrides all client commands.
- NetworkTables is diagnostics/state only; TCP is command/log output only.

## TCP Registry Push
Purpose: Update profiles and device registry without redeploying robot code.

- CLI commands: `profiles push <path> [--activate <profile>]`, `config push <path> [--activate <profile>]`
- TCP-only; NetworkTables is not used for apply.
- Robot validates payload, applies in-memory only, and reports per-stage status.
- Activation happens only when requested and only after validation passes.
- Runtime apply does not persist files on the roboRIO; redeploy or another push is still needed after reboot.

## Host vs Robot Active Profile
Purpose: Avoid confusing host-local editing context with robot runtime state.

- Host context (PC CLI/topology editor): which profile you are editing/inspecting locally.
- Robot context (roboRIO runtime): which profile is active for device instantiation and tests.
- Host context does not change the robot unless you run an explicit TCP command.

Examples:
- `profile <name>` selects host context (editing) only.
- `profiles activate <name>` selects robot context (runtime) over TCP.
- `show workspace` is host-only; `show status robot` inspects the robot.

## Real-Time Printing Model
Purpose: Prevent console output from breaking the 20ms control loop.

- WPILib runs a 20ms periodic loop.
- Console printing is slow and blocking.
- All report output uses a shared report runner:
- Reports are queued and printed incrementally across cycles.
- Batch size and chunk size are limited per cycle.

## Hardware Profiles (Data-Driven)
Purpose: Keep configuration easy to edit without code changes.

- Source of truth: `src/main/deploy/bringup_system.json`.
- Bindings source: `src/main/deploy/bringup_bindings.json`.
- Snapshots: `backup_data/backups/`.
- Validation helper: `python -m tools.validate_sync`.
- GUI editor: `tools/can_topology/can_top_editor.py`.
- CLI editor: `python -m tools.can_nt.can_nt_bridge --cli --no-can --no-nt`.
- Profiles apply in file order; press `Back` to rotate.
- Runtime override: `--bringup-profile=<name>`.

## CAN Bridge (PC Tool)
Purpose: Passive CAN sniffing and diagnostics on Windows.

- Hardware: CANable Pro V2 (slcan firmware by default).
- Read-only by design. Never transmits CAN frames.
- Publishes diagnostics to NetworkTables under `bringup/diag/...`.
- Can run CLI and UI surfaces without CAN access for local config/test authoring.
- Optional PCAP/PCAPNG capture and named pipe for Wireshark.
- Windows is the primary host; default workflows use slcan over a COM port.

Useful flags:
- `--print-publish` for seen/missing transitions.
- `--print-summary-period N` for periodic summaries.
- `--publish-unknown` to surface unknown devices.
- `--pcap <path>` to capture PCAPNG.
- `--list-ports` to enumerate COM ports.

Live Wireshark (Windows named pipe):
```cmd
wireshark -k -i \\.\pipe\FRC_CAN
python tools\can_nt\can_nt_bridge.py --pcap-pipe FRC_CAN
```

## Versioning
Purpose: Track and update app versions consistently.

- Version source: `tools/common/app_versions.py`.
Version helper (preferred):
- Show version: `bump show bridge_cli`
- Bump minor: `bump bump bridge_cli minor`
- Set version: `bump set bridge_cli 0.4.1`
- Field-set patch: `bump field-set bridge_cli patch 7`

Build metadata (git):
- Stamp git build info: `gitver`
- Dry-run: `gitver --dry-run`

Underlying script (still available):
- Update all apps: `python tools/update_versions.py --set all=1.2.3`
- Update one app: `python tools/update_versions.py --set can_nt_bridge=1.2.3`
- Show versions:
- `python tools\can_nt\can_nt_bridge.py --version`
- Bridge CLI: `show version` (bridge_cli only)
- CAN Topology Editor: `python tools\can_topology\can_top_editor.py --version`
- Bringup Control UI: Help -> About

## Bringup Control UI
Purpose: Fast command access and readable console output from the roboRIO.

Screenshot:
![Bringup Control UI](docs/images/bringup_ui_tests.png)

Annotated example (shortened):
```text
15:57:32 CMD printTestsInfo      -> UI command sent
15:57:32 ACK 470 printTestsInfo  -> Robot accepted command
15:57:32 OUT 470 printTestsInfo  -> Robot output begins
=== Bringup Tests Info ===
Resolved path: /home/lvuser/deploy/bringup_system.json (bridgeConfig.byProfile.<profile>.tests)
Test count: 10
==========================
```

## Bringup Tests
Purpose: Manual, data-driven tests for motors and encoders.

- Tests live in `bringup_system.json` under `bridgeConfig.byProfile.<profile>.tests`.
  - Active file: `src/main/deploy/bringup_system.json`
- Test sets are selected via `default_test_set` inside that per-profile tests block.
- Authoring:
  - Use the Bridge CLI/UI test authoring workflow (see `docs/CLI_TEST_AUTHORING_USER_GUIDE.md`).
  - Generate safe smoke tests (optional):
    - `py -m tools.bringup_test_wizard.gen_bringup_tests --profile <name> --test-set smoke --replace`
  - Apply a test template into `bringup_system.json` (optional):
    - `py -m tools.test_template_wizard.copy_test_template --template <file> --profile <name>`
  - After edits, run the validation helper:
    - `python -m tools.validate_sync`
  - `bringup_tests.json`-only workflows are legacy and not used by the robot.

## Current Boundaries
Purpose: Call out the most important present-day constraints.

- `src/main/deploy/` is the active config location for host tools and roboRIO deploys.
- `backup_data/backups/` is for snapshots only; it is not a live config source.
- Some older helper scripts and low-traffic docs still use legacy `data/` wording.
- The maintained regression bundle passes against the current deploy-only workflow.

## Documentation Index
Purpose: Find deep details without cluttering the README.

- `docs/ARCHITECTURE.md`
- `docs/SETUP.md`
- `docs/USER_GUIDE.md`
- `docs/OPERATOR_SURFACES.md`
- `docs/TESTING.md`
- `docs/TESTING_WINDOWS_OFFLINE.md`
- `docs/ALPHA_RELEASE_READINESS.md`
- `docs/AI_DIAGNOSIS.md`
- `docs/CAN_BACKGROUND.md`
- `docs/ProfileRegistryPushSpec.md`
- `docs/FEATURE_SPEC_BYTE_FINGERPRINTING.md`
- `tools/can_nt/README_CAN_NT.md`

## Notes
Purpose: Point to intent and planning.

- `notes/planning/PROJECT_INTENT.md`
