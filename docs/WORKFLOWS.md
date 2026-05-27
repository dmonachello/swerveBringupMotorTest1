# Workflows

## Purpose

Provide task-oriented procedures for the most common operator and developer workflows in this repo.

This document is intentionally shorter than the feature catalog. It answers “what should I do?” rather than “what exists?”

## Workflow Index

- First motor bringup
- Staged `robot_2026_swerve` bringup
- Bulk scripted motor test run
- Passive CAN diagnostics
- Topology authoring and validation
- Config push to robot
- Pre-club laptop handoff
- Regression before committing config changes

## First Motor Bringup

### Goal

Move one motor safely and confirm the command path works.

### Preferred path

Use:

- `instantiate next motor`
- one group binding
- one enabled group member

Do not start with `instantiate all devices` unless the hardware is already trusted.

### Steps

1. Start the CLI:

```text
python tools\can_nt\bridge_cli.py --rio 172.22.11.2
```

2. Connect:

```text
connect
```

3. Inspect the profile and groups:

```text
show status
show group krakens
show group neos
```

4. Disable all members in the relevant group.

5. Add the next motor:

```text
instantiate next motor
```

6. Enable only the motor you intend to move.

7. Move the joystick slowly and verify the motor responds.

### Why this path

It minimizes the number of unknowns:

- one motor created
- one motor enabled
- one binding active

## Staged `robot_2026_swerve` Bringup

### Goal

Bring up swerve drive and steering motors incrementally using left and right joystick control.

### Detailed runbook

Use the print-ready runbook:

- [ROBOT_2026_SWERVE_CLUB_TEST_SEQUENCE.md](c:/Users/dmona/swerveBringupMotorTest1-main/docs/ROBOT_2026_SWERVE_CLUB_TEST_SEQUENCE.md)
- [ROBOT_2026_SWERVE_CLUB_TEST_SEQUENCE.pdf](c:/Users/dmona/swerveBringupMotorTest1-main/docs/ROBOT_2026_SWERVE_CLUB_TEST_SEQUENCE.pdf)

### Summary

- `krakens` group bound to `leftDrive`
- `neos` group bound to `rightDrive`
- all group members disabled first
- `instantiate next motor` used in profile order
- one drive motor and one angle motor enabled at a time

### Why this path

It gives staged, joystick-driven manual control without having to write a new test for each motor.

## Bulk Scripted Motor Test Run

### Goal

Run repeatable configured tests rather than ad hoc manual control.

### When to use it

Use this only after the hardware path is already basically trusted.

### Steps

1. Connect:

```text
connect
```

2. Instantiate devices:

```text
instantiate all devices
```

3. Show tests:

```text
show tests
```

4. Select a test:

```text
tests select "<test name>"
```

5. Run it:

```text
tests run
```

### Notes

- scripted tests and group bindings are separate mechanisms
- while a bringup test is running, group bindings do not drive outputs

## Passive CAN Diagnostics

### Goal

Inspect bus activity and diagnostics without transmitting CAN.

### Steps

1. Identify ports:

```text
python -m tools.can_nt.can_nt_bridge --list-ports
```

2. Start the passive tool:

```text
python -m tools.can_nt.can_nt_bridge --rio 172.22.11.2 --channel COM21 --bitrate 1000000
```

3. Open Bringup UI if needed:

```text
python -m tools.can_nt.can_nt_bridge --ui --rio 172.22.11.2
```

4. Use:

- `NT Diagnostics`
- `Visibility`
- `Live Topology`

### Notes

- the CAN tool is passive only
- do not use passive diagnostics as proof that robot-local vendor API reads are correct
- compare robot-local reports and passive visibility when diagnosing disagreements

## Topology Authoring And Validation

### Goal

Edit `bringup_system.json` devices, topology, groups, and layout safely.

### Steps

1. Start the editor:

```text
python -m tools.can_topology.can_top_editor
```

2. Load the target profile.

3. Make device/topology/group changes.

4. Save.

5. Validate and sync:

```text
python -m tools.validate_sync --warnings
python tools/can_topology/validate_profiles.py --path src/main/deploy/bringup_system.json --verbose
```

### Notes

- config source is `src/main/deploy/bringup_system.json`
- the deploy-owned `src/main/deploy/bringup_system.json` file is the shared config source
- use the topology editor for topology-aware work instead of hand-editing layout sections

## Config Push To Robot

### Goal

Apply config changes on the robot without redeploying code.

### Steps

1. Validate locally:

```text
python -m tools.validate_sync --warnings
```

2. Push over TCP:

```text
python tools\can_nt\bridge_cli.py --rio 172.22.11.2
connect
profiles push src\main\deploy\bringup_system.json --activate robot_2026_swerve
```

### Notes

- this applies in-memory on the robot
- it is not a replacement for keeping the repo files correct

## Pre-Club Laptop Handoff

### Goal

Move from one machine to another without wasting robot time on environment problems.

### Steps

1. Make sure current changes are committed or otherwise copied.

2. Ensure the laptop has:

- Python
- repo copy
- correct `bringup_system.json`
- robot network access
- CANable driver/COM port readiness if needed

3. Run the core checks on the laptop:

```text
python -m tools.validate_sync --no-write --warnings
python tools/can_nt/scripts/run_regressions.py --suite topology --no-history
python tools/can_nt/scripts/run_regressions.py --suite cross-surface --no-history
```

4. Start with tooling only before commanding hardware.

### Notes

- the biggest time sink at the club is usually environment drift, not robot logic

## Regression Before Committing Config Changes

### Goal

Prove config and topology changes did not break other surfaces.

### Steps

Run:

```text
python -m tools.validate_sync --warnings
python tools/can_topology/validate_profiles.py --path src/main/deploy/bringup_system.json --verbose
python tools/can_nt/scripts/run_regressions.py --suite topology --no-history
python tools/can_nt/scripts/run_regressions.py --suite cross-surface --no-history
```

If the change is broader, also run:

```text
python tools/can_nt/scripts/run_regressions.py --suite local --no-history
```

### Notes

- `topology` checks editor/live topology/profile behavior
- `cross-surface` checks that topology/config output still works for other consumers
- `local` is broader and may include unrelated failures that still need triage

## Choosing The Right Mechanism

### If the goal is manual movement now

Use:

- `instantiate next motor`
- group bindings
- member enable / disable

### If the goal is a repeatable checked procedure

Use:

- DSL tests
- selected test execution

### If the goal is passive observation

Use:

- CAN tool
- visibility
- NT diagnostics

### If the goal is config authoring

Use:

- topology editor
- CLI config/test authoring
- validation/sync

## Related Documents

- [FEATURE_CATALOG.md](c:/Users/dmona/swerveBringupMotorTest1-main/docs/FEATURE_CATALOG.md)
- [FEATURE_MATRIX.md](c:/Users/dmona/swerveBringupMotorTest1-main/docs/FEATURE_MATRIX.md)
- [ROBOT_2026_SWERVE_CLUB_TEST_SEQUENCE.md](c:/Users/dmona/swerveBringupMotorTest1-main/docs/ROBOT_2026_SWERVE_CLUB_TEST_SEQUENCE.md)

