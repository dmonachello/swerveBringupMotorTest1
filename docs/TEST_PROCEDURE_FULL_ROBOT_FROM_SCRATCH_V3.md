# Test Procedure: Full Robot Bringup from Scratch (V3)

## Purpose

Provide a complete, start-to-finish test flow from a clean host setup to an on-robot bringup run, including Group and Targeting validation with canonical CLI commands.

## Scope

This procedure covers:

- host setup and local CLI validation
- profile and group construction from scratch
- save and push workflow
- robot-connected command validation
- execution-time checks for target resolution

## Version Notes

- This is the current from-scratch procedure.
- Command examples use canonical CLI forms only (`show`, `profile`, `configure terminal`, `validate`).
- Alias forms (`ls`, `prof`, `cfg`, `val`, `show session`) are removed and hard-error.

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

From PowerShell, start CLI:

```powershell
cd %USERPROFILE%\swerveBringupMotorTest1-main
python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt
```

Then in CLI, run:

```text
reset zero-config --yes
```

Optional full workspace clear in the same session:

```text
reset zero-config --yes --clear-memory
```

Expected:

- canonical/deploy unified config files are removed or reported missing

### Step 1C: Verify empty baseline

In CLI, run:

```text
configure terminal
show groups local
show tests local
```

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

```powershell
python tools/can_nt/scripts/bridge_cli_v1_group_targeting_regression.py
```

Note: script filename still uses `v1`; this procedure treats it as the current regression gate until renamed.

Expected:

- no failures

### Step 3: Start CLI in local mode

Command:

```powershell
python tools/can_nt/bridge_cli.py --no-can --no-nt
```

## Phase 2: Build Local Config and Groups

### Step 4: Enter config mode

```text
configure terminal
```

### Step 5: Create valid baseline devices

Create at least two fully valid devices so validation and save/push checks are meaningful.

Example:

```text
device motor1
deviceInterface CAN
manufacturer 5
deviceType 2
id 25
model "REV NEO"
type motor
exit
device motor2
deviceInterface CAN
manufacturer 4
deviceType 2
id 9
model "CTRE Falcon 500"
type motor
exit
```

Expected:

- devices appear in `show devices local`
- `validate all` does not fail due to missing interface/required fields

### Step 6: Create groups

```text
group create intake
exit
group create shooter
exit
```

Expected:

- each create succeeds once
- duplicate case-variant names fail

### Step 7: Validate `active` behavior

```text
group active
show group active
exit
```

Expected:

- context entry succeeds
- group exists and is mutable
- group is temporary

### Step 8: Populate groups

```text
group member assign intake motor1
group member assign intake motor2
group member assign all shooter
```

Expected:

- adds are union-based
- duplicate additions warn and no-op

### Step 9: Copy flow checks

```text
copy group intake active
show group active
```

Expected:

- active overwritten from intake

### Step 10: Save local config and verify active preservation

```text
save bridge-config .\scratch_v1_local.json --force
show group active
```

Expected:

- save succeeds
- active membership remains unchanged after save

Note:

- `--force` is still allowed, but should not be required for missing device-interface fields if Step 5 is followed.

## Phase 3: Connect to Robot

### Step 11: Launch connected CLI

Command:

```powershell
python tools/can_nt/bridge_cli.py --rio 172.22.11.2
```

Use your team IP as needed.

### Step 12: Enter config mode

```text
configure terminal
```

### Step 13: Confirm context parity behavior

```text
group active
exit
group intake
```

Expected:

- context enter succeeds only for existing groups
- `group <name>` does not implicitly create remote groups

### Step 14: Validate connected commands

Run and verify:

```text
group rename intake intake_v2
copy group intake_v2 active
group clear active
group delete active
```

Expected failure in this block:

```text
group delete active
```

Expected:

- same behavior as local mode for current semantics

## Phase 4: Push and Runtime Validation

### Step 15: Save sources

```text
save sources --force
```

Expected:

- local source artifacts saved without partial updates

### Step 16: Activate profile and run smoke tests

Example flow:

```text
profiles activate <profile-name>
show groups
show group active
run test <known-safe-test>
```

Expected:

- target and resolved devices are visible
- empty target groups fail safely with clear error

## Status Message Notes

The CLI status system supports template placeholders in canonical messages (for example `{arg}`).

- If a handler provides placeholder args, output is fully resolved.
- If a handler does not provide args, fallback rendering substitutes placeholder names to avoid raw braces in operator output.

## Phase 5: End-to-End Success Criteria

All criteria must pass:

- Group and Targeting regression script passes.
- Local and connected CLI behavior is consistent for canonical commands.
- `active` remains non-persistent and is not written to saved config.
- No silent mutation on protected operations.
- Robot command path remains responsive and safe.

## Troubleshooting

- If connected CLI commands fail, verify RIO reachability and TCP UI channel.
- If save blocks on validation, use `--force` for procedure-only verification and log failures.
- If group context fails unexpectedly, verify group exists in current local state.
- If runtime tests do not actuate, confirm selected test and enabled state.


