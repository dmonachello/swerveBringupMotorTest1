# Real-Robot Bringup Test Plan (CLI + Topology Editor)

Purpose: Validate CLI, topology editor, and CAN diagnostics against a real robot with a blank configuration.

## 1. Introduction

Run a repeatable end-to-end bringup workflow that starts from an empty configuration and adds capability one device at a time.

### 1.1 Guiding Principles

Keep this plan stable and repeatable while driving toward an alpha-quality workflow.

- Prefer one end-to-end “happy path” over many partial paths.
- Add one device and one test at a time; repeat the loop.
- If a step fails, stop and fix the root cause before adding more devices or features.
- Expect a second pass for usability/clarity after the workflow is proven solid.

### 1.2 User Story

This document is primarily a test plan/procedure, not a formal user story backlog item.
It can be treated as a user-story-style acceptance test:

- As an operator, I want to bring up one device at a time and run a known-safe test so I can prove the toolchain works before scaling up to a full robot.

### 1.3 Save and Sync Conventions

The CLI has multiple save commands because they write different scopes (profiles vs tests vs bridgeConfig).
For this plan, standardize on one canonical write plus one sync gate:

- Host save (canonical): `save unified-config data\bringup_system.json --force`
  - Writes profiles + tests + bridgeConfig to the canonical file.
- Host sync to deploy: `python -m tools.validate_sync`
  - Validates canonical and writes `src\main\deploy\bringup_system.json`.

### 1.4 Terminology

Purpose: Prevent "active profile" confusion across host tools and robot runtime.

- Device: A labeled component in the device registry (for example a motor controller) referenced by label in profiles, groups, and tests.
- CAN bus: The physical CAN network on the robot. Host tools must be passive (no CAN transmit).
- Host context: Local editing/inspection state on the Driver Station PC (what profile the CLI/topology editor is operating on on disk).
- Robot context: Runtime state on the roboRIO (active profile, selected test, and any actuation).
- CLI editor: The Bridge CLI running on the PC (can edit local config and can send explicit TCP commands to the robot).
- Topology editor: The PC GUI editor that authors profile devices and diagram metadata into `data\bringup_system.json`.
- Bridge UI: The PC UI that displays runtime state and triggers robot actions via TCP (it does not directly edit config files).
- Canonical config: `data\bringup_system.json` (single source of truth for host tools).
- Deploy copy: `src\main\deploy\bringup_system.json` (derived artifact written by `python -m tools.validate_sync`).
- Rule: host context MUST NOT change robot context unless an explicit TCP robot command is executed (for example `profiles activate <name>`).
- Examples:
  - Host: `show profile`, `show devices`, `show topology`, `show tests`.
  - Robot: `connect`, `show status robot`, `tests select <name>`, `tests run`.
- Offline-only variant: `docs/TESTING_WINDOWS_OFFLINE.md`.

### 1.5 Scope

- CLI config lifecycle, profiles, and bindings.
- Topology editor save/load and neighbor ports.
- Visibility matrix basics (single analyzer acceptable).
- Robot-side interaction safety (no CAN transmit from PC tool).

### 1.6 Pre-Flight Checks

- Robot and Driver Station PC on the same network.
- CANable connected (if using live CAN). For CLI-only testing, use `--no-can`.
- Robot code deployed and enabled to provide NetworkTables and bringup harness.
- If using a blank config, back up existing files first.
- If using SSH to avoid Driver Station keyboard interference, see `docs/SPEC_SSH_DRIVER_STATION_CLI.md`.

### 1.7 Files and Paths

- Canonical profiles/registry/tests: `data\bringup_system.json`
- Deploy copy (robot fallback and tooling default): `src\main\deploy\bringup_system.json`
- Validate + sync gate: `python -m tools.validate_sync`
- Bindings: `src\main\deploy\bringup_bindings.json`
- CLI entry: `python -m tools.can_nt.can_nt_bridge --cli`
- Topology editor: `python -m tools.can_topology.can_top_editor`

### 1.8 Safety Rules

- Do not send CAN frames from the PC tool.
- Keep motors disabled unless explicitly testing motion.
- Use low duty cycles and short durations when you do test.
- Driver Station E-stop: be ready to E-stop immediately for any unexpected motion.

### 1.9 Document Change History

| Version | Initials | Date (YYYY-MM-DD) | Comments        |
| :------ | :------- | :---------------- | :-------------- |
| 0.1     | DRM      | 2026-04-13        | Initial version |

## 2. Phase 1 (Host): Blank Config → home_031226 (Main Test)

Goal: Start empty and build a minimal working profile for `home_031226` without loading any prior config.

### 2.1 Start CLI

```powershell
cd C:\Users\dmona\swerveBringupMotorTest\swerveBringupMotorTest1
python -m tools.can_nt.can_nt_bridge --cli
```

### 2.2 Initialize profiles and create the target host profile

```text
configure terminal
profiles init
profile create home_031226
show profile
show devices
show topology
```

Expected

- Active host profile is `home_031226`.
- Devices are empty.
- Topology shows `(none)`.

### 2.3 Add one device registry entry (start small)

```text
device "SPARKMAX/NEO 25"
set interface CAN
set manufacturer 5
set deviceType 2
set id 25
set model "REV NEO"
set type motor
exit
```

Expected

- `show devices` lists: `SPARKMAX/NEO 25`.

### 2.4 Add topology (use the editor for layout)

```powershell
python -m tools.can_topology.can_top_editor
```

In the editor:

- Select profile `home_031226`.
- Add nodes matching your current device set (start with `SPARKMAX/NEO 25` only).
- Place them on the bus.
- File -> Save to Deploy (writes canonical + deploy copies).

Back in the editor, confirm the topology is present for `home_031226`.

No CLI reload is required for this test. Stay in the editor for topology validation.

### 2.5 Auto-assign or manually set neighbor ports

Notes:

- Neighbor ports are meaningful once the topology has at least two nodes.
- If you only have one device so far, skip this step and return after adding more devices.

```text
conf terminal
topology neighbor-auto all
show topology neighbors
```

Expected

- Neighbor entries exist.

### 2.6 Save host changes (canonical) and sync to deploy

Notes:

- If you used the topology editor “Save to Deploy”, you already wrote canonical + deploy.
- Run these commands if you made additional CLI changes after the editor save (or to re-validate and stamp hashes).

```text
save unified-config data\bringup_system.json --force
end
```

```powershell
python -m tools.validate_sync
```

Expected

- File saved with a backup snapshot created.

## 3. Phase 2 (Host): Topology Editor Round-Trip

Goal: Validate that the editor can open, modify, and save topology without breaking CLI parsing.

### 3.1 Open the editor

```powershell
python -m tools.can_topology.can_top_editor
```

### 3.2 Load, edit, and save the target profile (host/editor context)

- Select profile `home_031226` in the editor and load it.
- Move one node slightly.
- File -> Save to Deploy.

Expected

- Node positions updated in the editor.
- No schema or parse errors on save.

No CLI reload is required for this test. Stay in the editor for topology validation.

## 4. Phase 3 (Host): Neighbor Ports (Manual + Auto)

Goal: Validate neighbor auto-assign and manual overrides.

Notes:

- Neighbor ports are meaningful once the topology has at least two nodes.
- If you only have one device so far, skip this phase and return after adding more devices.

### 4.1 Auto-assign all

```text
conf terminal
topology neighbor-auto all
show topology neighbors
```

### 4.2 Auto-assign only selected labels

```text
topology neighbor-auto all <label1>,<label2>
show topology neighbors
```

### 4.3 Manual override

```text
topology neighbor-ports set <label1> right <label2> left
show topology neighbors
```

Expected

- Neighbor entries exist.
- Manual entries replace conflicting ports for that node.

Note

- For branched wiring, do not use auto-assign beyond the linear segments.

## 5. Phase 4 (Host): CANnect Device Links

Goal: Ensure CANnect links appear as `next/branch1/branch2` neighbor ports.

### 5.1 With CANnect nodes linked in the diagram

```text
show topology neighbors
```

Expected

- Neighbor entries for CANnect port links using `next/branch1/branch2`.

## 6. Phase 5 (Host): Visibility Matrix (Single Analyzer)

Goal: Confirm visibility output format and basic state changes.

### 6.1 Start CLI with live CAN

```powershell
python -m tools.can_nt.can_nt_bridge --cli
```

### 6.2 Show visibility

```text
show visibility
show visibility summary
show visibility <device_label>
```

Expected

- Matrix includes the single source.
- Visible devices show `Y`.
- Missing devices show `N` or `?` depending on source availability.

## 7. Phase 6 (Host): Bindings and Inputs

Goal: Ensure bindings and alias behavior remain consistent.

```text
show bindings
show bindings --all
show binding-usage driver.a
show binding-usage controller0.a
```

Expected

- Usage resolves aliases consistently.
- Local bindings override global when they match the same input.

## 8. Phase 7 (Host): Tests (Create From Scratch)

Goal: Create a minimal test set without loading templates.

### 8.1 Verify bindings exist (controller0 must be present)

```text
show bindings
```

### 8.2 Create a simple motor pulse test

```text
conf terminal
test create neoPulse
type button
device add "SPARKMAX/NEO 25"
inputSource controller0.A
duty 0.1
termination time 1.0
exit
```

### 8.3 Create a reverse-direction pulse test

```text
test create neoReversePulse
type button
device add "SPARKMAX/NEO 25"
inputSource controller0.B
duty -0.1
termination time 1.0
exit
```

### 8.4 Show and save tests

```text
show tests
save unified-config data\bringup_system.json --force
```

Expected

- Two tests exist and are listed (`neoPulse`, `neoReversePulse`).

## 9. Phase 8 (Host): Add a Limit Switch + Limit-Switch Test

Goal: Add a DIO limit switch device to the profile and create a motor test that terminates when the switch is hit.

Notes:

- Start with a single limit switch device and a single motor.
- Use low duty and include a time-based fallback termination so the motor stops even if the switch wiring is wrong.

### 9.1 Add a limit switch device (DIO)

Hardware:

- Wire the limit switch to a roboRIO DIO port (example: DIO 0).
- Choose `invert` based on the switch type (normally-open vs normally-closed).

In the CLI:

```text
conf terminal
device "lmSw1"
set interface DIO
set type limitSwitch
set dio 0
set invert true
exit
```

Expected

- `show devices` includes `lmSw1`.

### 9.2 Create a limit-switch stop test

In the CLI:

```text
conf terminal
test create neoLimitStop
type button
device add "SPARKMAX/NEO 25"
inputSource controller0.X
duty 0.1
termination limitswitch 0
termination time 2.0
time onTimeout fail
limitswitch onHit pass
limitswitch id 0
exit
```

Save:

```text
save unified-config data\bringup_system.json --force
```

Expected

- `show tests` lists `neoLimitStop`.

### 9.3 Validate the limit switch behavior (host-side smoke check)

Goal: Confirm the limit switch wiring/invert setting before running motion tests.

- Use any available host visibility/diagnostics views that surface DIO/limit-switch state.
- If the state is inverted (pressed reads as released), flip `invert` for `lmSw1`, save again, and re-check.

## 10. Phase 9 (Robot): Execute Tests (Robot + Bridge UI)

Goal: Run the tests on the robot and verify motion/behavior and UI updates.

### 10.1 Ensure robot is enabled and safety is clear

- Confirm the mechanism is safe to move and the area is clear.
- Ensure Driver Station is ready to E-stop immediately.

### 10.2 Run from CLI (robot context; requires TCP connection)

```text
connect
show status robot
tests select neoPulse
tests run
tests select neoReversePulse
tests run
tests select neoLimitStop
tests run
```

Expected

- NEO motor pulses at low duty.
- NEO motor pulses in reverse at low duty (neoReversePulse).
- NEO motor runs at low duty until the limit switch is hit (neoLimitStop), then stops.

### 10.3 Run from Bridge UI (robot side)

Goal: Run tests from the Bridge UI without typing CLI commands.

- Open the Bridge UI.
- Select `neoPulse`, click Run.
- Select `neoReversePulse`, click Run.
- Select `neoLimitStop`, click Run.
- Run All Tests (if available).

Expected

- UI reflects active test and status changes.
- Robot behavior matches test definitions.

### 10.4 Run directly on the robot using the Xbox controller

Goal: Prove you can run the same tests without the CLI/UI by using the configured `inputSource` buttons.

- With the robot enabled, press:
  - `controller0.A` to trigger `neoPulse`
  - `controller0.B` to trigger `neoReversePulse`
  - `controller0.X` to trigger `neoLimitStop`
- For `neoLimitStop`, press and release the limit switch by hand and confirm the motor stops immediately.

Expected

- The motor stops immediately when the limit switch is hit.

## 11. Phase 10 (Host): Save and Validate

Goal: Confirm save and validation paths run clean.

```text
validate profiles local --active
save unified-config data\bringup_system.json --force
end
```

Then sync canonical -> deploy:

```powershell
python -m tools.validate_sync
```

Expected

- Validation should not crash. Any errors should be actionable.
- Save produces a backup snapshot and writes the file.

## 12. Phase 11: Pass/Fail Summary

Log the following:

- CLI startup and profile load success.
- Topology editor save/load success.
- Neighbor ports auto/manual behavior.
- CANnect neighbor port mapping.
- Visibility output format and sanity.
- Binding usage correctness.
- Validation and save success.

If any step fails, capture:

- The exact command.
- The CLI output.
- Which profile was active.
