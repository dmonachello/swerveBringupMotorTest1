# Test Plan: Group and Targeting V1

## Purpose

Validate the Group and Targeting V1 behavior in the Bridge CLI with deterministic, repeatable checks.

## Scope

This plan covers:

- global namespace and case-insensitive matching
- reserved `active` behavior
- group membership set semantics
- copy model and non-interactive behavior
- add-all and add-next targeting behavior
- delete protections for referenced entities
- active non-persistence without save-time mutation

This plan does not require a robot connection.

## Preconditions

- Windows host with Python on `PATH`
- Working directory at repo root
- Latest code changes present in workspace

## Connection Assumption

For any connected variants of this plan, assume roboRIO USB connection and `172.22.11.x` addressing.

## Device Definition Guardrail

This plan requires valid device definitions.

- Do not use placeholder-only `device <name>` entries.
- Define `deviceInterface` and required fields before group membership tests.
- Group/targeting behavior must be validated on schema-valid devices.

## Quick Automated Validation

Run the regression script first.

Command:

`python tools/can_nt/scripts/bridge_cli_v1_group_targeting_regression.py`

Expected:

- Summary reports zero failures.
- Current baseline target is `passed=35 failed=0`.

## Manual Validation (Focused)

Use CLI in local mode for targeted checks.

Command:

`python tools/can_nt/bridge_cli.py --no-can --no-nt`

Then run these commands in order.

### 1) Enter config mode

`configure terminal`

Expected:

- prompt changes to config mode

### 2) Reserved active context

`group active`

Expected:

- enters group context
- does not create a persisted named group

`exit`

### 3) Case-insensitive uniqueness

`group create intake`

Expected:

- success

`exit`

`group create INTAKE`

Expected:

- fails with name collision

### 4) Member set semantics

`device motor1`

`set deviceInterface CAN`

`set manufacturer 5`

`set deviceType 2`

`set id 25`

`set model "REV NEO"`

`set type motor`

`exit`

`group intake`

`add device motor1`

Expected:

- success

`add device motor1`

Expected:

- warning for duplicate member
- no membership duplication

`remove device motor1`

Expected:

- success

`remove device motor1`

Expected:

- warning for missing member
- no hard failure

`exit`

### 5) Copy semantics and non-interactive safety

`group create shooter`

`exit`

`add all group intake`

`copy group intake active`

Expected:

- active overwritten from intake without prompt

Now run non-interactive copy test using batch script execution.

Expected behavior:

- copy to existing named group fails in non-interactive mode
- destination unchanged

### 6) Delete protections

`group delete active`

Expected:

- fails with reserved active error

For referenced-entity tests, create references first and then delete.

Expected:

- deleting referenced device fails
- deleting test-referenced group fails

### 7) Active preserved on save

`add next group active`

`show group active`

Expected:

- active has at least one member

`save local-config .\tmp_group_v1_config.json --force`

`show group active`

Expected:

- active membership is unchanged after save

## Pass Criteria

- Automated regression script passes.
- Manual checks match expected outcomes above.
- No command silently mutates state when safety rules require failure.

## Troubleshooting

- If `save local-config` fails validation, retry with `--force` for this test plan.
- If CLI parser hints appear unexpectedly, confirm command was entered in config mode.
- If active membership changes unexpectedly on save, capture logs and file a regression.
