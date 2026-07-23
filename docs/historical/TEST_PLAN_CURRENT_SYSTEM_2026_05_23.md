# Current System Test Plan

## Purpose

Provide one current, code-aligned test plan for the repository state as of May 23, 2026.

This document is based on the current code paths and the regression commands that were actually run against this workspace.

## What This Plan Covers

- deploy-owned config model
- shared device inventory plus multi-profile config structure
- unified global bindings schema
- `schema_version: 5`
- current DSL import-based local test authoring
- robot-local command modularization compatibility
- local CLI/group/test regressions
- Java test coverage

## Current Model Summary

### Config structure

- one `bringup_system.json` file can contain multiple profiles
- `devices[]` is the shared device inventory
- `profiles.<name>.devices[]` selects which device labels belong to each profile

### Bindings structure

- `bringup_bindings.json` is a separate config file
- it now carries `schema_version: 5`
- global button and axis mappings both live in `bindings[]`
- axis rows use:
  - `input: "axis"`
  - `mode: "analog"`
  - `invert`
  - `deadband`

### Test authoring

- current local path is DSL file plus `test import`
- legacy local interactive `test create` / `type` / `inputSource` workflow is not current

## Preconditions

1. Use Windows.
2. Open PowerShell in the repo root.
3. Confirm `python` works.
4. Confirm `.\gradlew.bat` works.
5. If connected validation is planned, confirm roboRIO reachability.

## Section A: Automated Gate

Run these exactly:

```powershell
python tools\common\tests\test_schema_store_profiles.py
python tools\common\tests\test_device_catalog.py
python tools\can_nt\tests\test_bridge_cli_visibility.py
python tools\can_nt\tests\test_bridge_cli_robot_test_dsl_cli.py
.\gradlew.bat test
python tools\can_nt\scripts\bridge_cli_v1_group_targeting_regression.py
python tools\can_nt\scripts\bridge_cli_group_targeting_4m2g3t_regression.py
```

Expected:

- every command exits successfully
- both local regression scripts report zero failures

## Section B: Local Config And Workspace Validation

### Step B1

Run:

```powershell
Get-ChildItem src\main\deploy\bringup_system.json
Get-ChildItem src\main\deploy\bringup_bindings.json
```

Expected:

- both files exist

### Step B2

Run:

```powershell
python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt
```

Expected:

- CLI starts

### Step B3

At the CLI:

```text
show workspace
```

Expected:

- output points to `src/main/deploy/...`
- output does not depend on deleted `data\` config ownership

### Step B4

At the CLI:

```text
show profiles
show profile
show devices
```

Expected:

- profiles load successfully
- device list is shown from the shared inventory

### Step B5

At the CLI:

```text
configure terminal
validate profiles local --active
```

Expected:

- validation succeeds

## Section C: Unified Global Bindings Schema

### Step C1

At the CLI:

```text
bindings validate
bindings show --all --json --pretty
```

Expected:

- validation succeeds
- JSON output includes `schema_version`
- JSON output uses unified `bindings[]`
- no top-level `axes[]` block is treated as current

### Step C2

At the CLI:

```text
bindings controller add driver0 XBOX 0
bindings binding add stop driver0 button A edge
bindings binding add leftDrive driver0 axis leftY analog invert on deadband 0.12
bindings show bindings
```

Expected:

- all commands succeed
- axis row is shown inline with `invert` and `deadband`

### Step C3

At the CLI:

```text
bindings save temp_bindings.json
bindings validate temp_bindings.json
```

Expected:

- save succeeds
- saved payload validates
- saved payload carries `schema_version: 5`

### Step C4

Negative checks:

- invalid axis mode must fail
- invalid deadband must fail
- deleting a referenced controller must fail

## Section D: Group Bindings And Visibility

### Step D1

At the CLI:

```text
group diag
member assign "SPARKMAX/NEO 25"
bind controller0.leftY analog
show bindings
show bindings --all
```

Expected:

- local group binding is visible
- global bindings remain visible separately in `show bindings --all`

### Step D2

At the CLI:

```text
end
exit
```

Expected:

- CLI exits cleanly

## Section E: Current DSL Test Authoring Path

### Step E1

Create a file named `temp_test.dsl` with:

```text
test "MyTest1"
device "SPARKMAX/NEO 25"
device "controller0"

main:
    set "SPARKMAX/NEO 25".output = controller0.leftY deadband 0.12 scaled 0.25 default 0.0
    until timer.elapsed >= 3.0
```

### Step E2

Start the local CLI again:

```powershell
python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt
```

### Step E3

At the CLI:

```text
configure terminal
test import MyTest1 temp_test.dsl set default
test validate MyTest1 --json --pretty
end
show test MyTest1
show test MyTest1 normalized --json --pretty
```

Expected:

- import succeeds
- validation succeeds
- normalized output reflects the DSL source semantics

### Step E4

Verify removed workflow is not treated as current:

- do not use `test create`
- do not use `type`
- do not use interactive `inputSource`
- do not use interactive `deadband`

## Section F: Optional Connected Validation

If a roboRIO is available, run connected non-motion validation:

```powershell
python tools\can_nt\scripts\bridge_cli_robot_non_motion_regression.py --rio 172.22.11.2
```

Expected:

- command succeeds when hardware is available

If hardware is unavailable:

- mark this section `BLOCKED`

## Pass Criteria

This plan passes when:

- the automated gate is green
- local config validation is green
- bindings validate under schema `5`
- unified axis rows work through `bindings binding ...`
- DSL import/validate/show works
- no current procedure depends on removed `data\` config ownership
- no current procedure depends on removed interactive local test authoring

