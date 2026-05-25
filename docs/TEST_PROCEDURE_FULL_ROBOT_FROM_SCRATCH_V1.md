# Test Procedure: Full Robot Bringup from Scratch (V2)

> Superseded: Use `docs/TEST_PROCEDURE_FULL_ROBOT_FROM_SCRATCH_V3.md`.

## Purpose

Provide a complete, start-to-finish test flow from a clean host setup to an on-robot bringup run, including Group and Targeting V2 validation.

## Scope

This procedure covers:

- host setup and local CLI validation
- profile and group construction from scratch
- save and push workflow
- robot-connected command validation
- execution-time checks for target resolution

## Clean Start Requirement

This procedure is valid only if the host starts from a known-empty working state for groups/tests under the active profile.

- Do not skip the clean-state steps below.
- If existing items are present, reset or explicitly clear them before continuing.

## Safety

- Keep robot wheels off ground or drivetrain secured.
- Keep emergency stop path clear and verified before motion tests.
- Use low duty values for first motion verification.

## Prerequisites

- Windows laptop with Python available
- RoboRIO connected over USB (default assumption for this procedure)
- Repo available locally
- Robot deployed with compatible bringup code
- `src/main/deploy/bringup_bindings.json` present
- CAN hardware connected and powered

## Addressing Assumption

Use USB roboRIO addressing for all connected tests in this document.

- Default robot host examples use `172.22.11.2`.
- Team USB convention is `172.22.11.x`.

## Phase 1: Clean Host Start

### Step 1: Open repo root

Example path:

`C:\Users\dmona\swerveBringupMotorTest\swerveBringupMotorTest1`

### Step 1A: Backup current local artifacts

Create timestamped backups of local config artifacts before destructive reset steps.

Minimum backup targets:

- `data\bringup_system.json`
- `src\main\deploy\bringup_bindings.json`
- `src\main\deploy\can_mappings.json`

### Step 1B: Reset to zero-config baseline

Start CLI and run:

- `reset zero-config --yes`

Optional full workspace clear in the same session:

- `reset zero-config --yes --clear-memory`

Expected:

- canonical/deploy unified config files are removed or reported missing

### Step 1C: Verify empty baseline

In CLI, run:

- `configure terminal`
- `show groups local`
- `show tests local`

Expected:

- no pre-existing named groups
- `active` present with zero members
- baseline tests may exist (profile-seeded defaults are allowed)
- no unexpected extra tests beyond the known baseline for the selected profile

If non-empty, clear before proceeding:

- delete/clear remaining named groups and rerun reset + reload
- if tests are present, verify they match expected profile baseline names/count

Example known baseline after reset (profile-dependent):

- `show groups local` may show only `active (enabled) members=0 bindings=0`
- `show tests local` may show seeded defaults such as `neo25_button` and `all_motors`

### Step 2: Run focused regression first

Command:

`python tools/can_nt/scripts/bridge_cli_v1_group_targeting_regression.py`

Note: script filename still uses `v1`; this procedure treats it as the current V2 regression gate until renamed.

Expected:

- no failures

### Step 3: Start CLI in local mode

Command:

`python tools/can_nt/bridge_cli.py --no-can --no-nt`

## Phase 2: Build Local Config and Groups

### Step 4: Enter config mode

`configure terminal`

### Step 5: Create valid baseline devices

Create at least two fully valid devices so validation and save/push checks are meaningful.

Example:

- `device motor1`
- `deviceInterface CAN`
- `manufacturer 5`
- `deviceType 2`
- `id 25`
- `model "REV NEO"`
- `type motor`
- `exit`
- `device motor2`
- `deviceInterface CAN`
- `manufacturer 4`
- `deviceType 2`
- `id 26`
- `model "CTRE Falcon 500"`
- `type motor`
- `exit`

Expected:

- devices appear in `show devices local`
- `validate all` does not fail due to missing interface/required fields

### Step 6: Create groups

- `group create intake`
- `exit`
- `group create shooter`
- `exit`

Expected:

- each create succeeds once
- duplicate case-variant names fail

### Step 7: Validate `active` behavior

- `group active`
- `show group active`
- `exit`

Expected:

- context entry succeeds
- group exists and is mutable
- group is temporary

### Step 8: Populate groups

- `group member assign intake motor1`
- `group member assign intake motor2`
- `group member assign all shooter`

Expected:

- adds are union-based
- duplicate additions warn and no-op

### Step 9: Copy flow checks

- `copy group intake active`
- `show group active`

Expected:

- active overwritten from intake

### Step 10: Save local config and verify active preservation

- `save bridge-config .\scratch_v1_local.json --force`
- `show group active`

Expected:

- save succeeds
- active membership remains unchanged after save

Note:

- `--force` is still allowed, but should not be required for missing device-interface fields if Step 5 is followed.

## Phase 3: Connect to Robot

### Step 11: Launch connected CLI

Command:

`python tools/can_nt/bridge_cli.py --rio 172.22.11.2`

Use your team IP as needed.

### Step 12: Enter config mode

`configure terminal`

### Step 13: Confirm context parity behavior

- `group active`
- `exit`
- `group intake`

Expected:

- context enter succeeds only for existing groups
- `group <name>` does not implicitly create remote groups

### Step 14: Validate V2 commands while connected

Run and verify:

- `group rename intake intake_v2`
- `copy group intake_v2 active`
- `group clear active`
- `group delete active` (must fail)

Expected:

- same behavior as local mode for V2 semantics

## Phase 4: Push and Runtime Validation

### Step 15: Save sources

`save sources --force`

Expected:

- local source artifacts saved without partial updates

### Step 16: Activate profile and run smoke tests

Example flow:

- `profiles activate <profile-name>`
- `show groups`
- `show group active`
- `run test <known-safe-test>`

Expected:

- target and resolved devices are visible
- empty target groups fail safely with clear error

## Phase 5: End-to-End Success Criteria

All criteria must pass:

- Group and Targeting V2 regression script passes.
- Local and connected CLI behavior is consistent for V2 commands.
- `active` remains non-persistent and is not written to saved config.
- No silent mutation on protected operations.
- Robot command path remains responsive and safe.

## Troubleshooting

- If connected CLI commands fail, verify RIO reachability and TCP UI channel.
- If save blocks on validation, use `--force` for procedure-only verification and log failures.
- If group context fails unexpectedly, verify group exists in current local state.
- If runtime tests do not actuate, confirm selected test and enabled state.


