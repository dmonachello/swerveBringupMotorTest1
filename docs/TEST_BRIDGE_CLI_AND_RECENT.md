# Bridge CLI And Recent Changes Test Plan

## Purpose

Provide a current regression checklist for the recent CLI-facing changes.

This document is current for:

- deploy-owned config
- unified global bindings schema
- schema version `5`
- DSL import-based local test authoring

## Current Preconditions

- repo root is the working directory
- `src/main/deploy/bringup_system.json` exists
- `src/main/deploy/bringup_bindings.json` exists
- no current workflow depends on a separate `data\` copy of `bringup_system.json`

## Offline Current-State Checks

### 1. CLI visibility + bindings

Run:

```powershell
python tools\can_nt\tests\test_bridge_cli_visibility.py
```

Expected:

- test succeeds

### 2. DSL CLI behavior

Run:

```powershell
python tools\can_nt\tests\test_bridge_cli_robot_test_dsl_cli.py
```

Expected:

- test succeeds

### 3. Local group targeting regressions

Run:

```powershell
python tools\can_nt\scripts\bridge_cli_v1_group_targeting_regression.py
python tools\can_nt\scripts\bridge_cli_group_targeting_4m2g3t_regression.py
```

Expected:

- both scripts pass

### 4. Java regression

Run:

```powershell
.\gradlew.bat test
```

Expected:

- Java tests pass

## Manual CLI Checks

### 1. Start local-only CLI

```powershell
python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt
```

### 2. Confirm current config ownership

At the CLI:

```text
show workspace
```

Expected:

- paths point to `src/main/deploy/...`
- no deleted `data\` config path is treated as active

### 3. Confirm current bindings schema

At the CLI:

```text
bindings validate
bindings show --all --json --pretty
```

Expected:

- validation succeeds
- output includes `schema_version`
- output does not rely on top-level `axes[]`

### 4. Confirm current local test authoring path

Create a temporary DSL file and import it:

```text
configure terminal
test import MyTest1 temp_test.dsl set default
test validate MyTest1 --json --pretty
end
show test MyTest1 normalized --json --pretty
```

Expected:

- import succeeds
- validation succeeds
- normalized output matches DSL semantics

No longer current:

- `test create`
- `type`
- `inputSource`
- `deadband` as interactive local test-edit commands

## Connected Optional Checks

If a roboRIO is available:

- connect with CLI or UI
- run non-motion profile/test visibility checks
- confirm no stop-latch or profile-selection regression

Use [TEST_PLAN_CURRENT_SYSTEM_2026_05_23.md](./TEST_PLAN_CURRENT_SYSTEM_2026_05_23.md) for the full connected procedure.
