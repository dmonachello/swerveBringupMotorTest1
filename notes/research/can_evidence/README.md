# CAN Evidence Capture Workspace

## Purpose

Purpose: store the raw logs, run notes, and structured review artifacts used to prepare implementation of the CAN device evidence source contracts.

Primary spec:

- `docs/FEATURE_SPEC_CAN_DEVICE_EVIDENCE_SOURCE_CONTRACTS.md`

Preparation checklist:

- `docs/TASK_LIST_CAN_EVIDENCE_SOURCE_PREP.md`

## Folder Layout

- `raw_console_logs/`
  - raw console captures from real runs
- `run_notes/`
  - one markdown note per capture/session
- `reviews/`
  - reviewed summaries such as trusted console message families

## Current Task 1 Focus

Profile:

- `test_minimal_25_9`

Planned first capture set:

1. all-connected working baseline
2. one-device-disconnected startup case for each device
3. reconnect recovery case when reconnect causes observable console output

## Naming Guidance

Recommended raw log filename pattern:

`YYYY-MM-DD_profile_test_minimal_25_9_<scenario>.log`

Recommended run note filename pattern:

`YYYY-MM-DD_profile_test_minimal_25_9_<scenario>.md`

Examples:

- `2026-06-03_profile_test_minimal_25_9_all_connected_baseline.log`
- `2026-06-03_profile_test_minimal_25_9_fl_drive_disconnected_startup.md`

## Standard Scenario Labels

Recommended scenario labels:

- `all_connected_baseline`
- `<device_label>_disconnected_startup`
- `<device_label>_reconnected_recovery`

Use lowercase with underscores for consistency.
