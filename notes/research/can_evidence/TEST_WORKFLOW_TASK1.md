# Task 1 Workflow: Console Evidence Capture

## Purpose

Purpose: define the standard reusable workflow for collecting Task 1 console logs on profile `test_minimal_25_9`.

## Scope

This workflow is for:

- all-connected working baseline
- one-device-disconnected startup runs
- reconnect recovery runs when reconnect creates observable console output

## Standard Workflow

1. Set the robot/profile context to `test_minimal_25_9`.
2. Record the exact physical state before power-up.
3. Start raw console capture.
4. Power up or reboot the robot.
5. Wait through startup until the robot reaches steady idle.
6. Run the standard manual right-click test sequence.
7. Wait a short post-test idle window.
8. If this is a reconnect case, reconnect the device and continue observing long enough to capture any resulting console output.
9. Stop the console capture.
10. Save the raw log with the standard filename pattern.
11. Fill out a run note from `run_notes/RUN_NOTE_TEMPLATE.md`.

## Standard Test Sequence

Use the same test sequence for every comparable run unless there is a documented reason to change it.

Recommended baseline sequence:

1. Right-click motor A forward
2. Stop
3. Right-click motor A reverse
4. Stop
5. Right-click motor B forward
6. Stop
7. Right-click motor B reverse
8. Stop

If the actual labels differ, write the exact labels used into the run note.

## Scenario Set

Initial planned scenarios:

1. `all_connected_baseline`
2. one disconnected-startup run per device
3. one reconnect-recovery run per device when reconnect produces console output

## Required Metadata Per Run

- date
- scenario name
- raw log filename
- disconnected device, if any
- exact manual test sequence
- what physically happened
- whether reconnect produced new console output
- any ambiguity or unexpected behavior

## Notes

- Prefer one run note per raw log file.
- If a run has to be repeated, save both logs rather than overwriting the first one.
- If a scenario deviates from the standard sequence, record why.
