# Windows Offline Test Plan

## Purpose

Validate current Windows-hosted tooling and local config workflows without a roboRIO.

## Scope

- local CLI lifecycle
- local config validation
- topology editor open/save round-trip
- current bindings schema validation
- DSL import-based test authoring

## Preconditions

- Windows host
- repo root is current directory
- `python` works
- `src/main/deploy/bringup_system.json` exists
- `src/main/deploy/bringup_bindings.json` exists

## Current Config Rules

- one `bringup_system.json` file may contain multiple profiles
- `devices[]` is the shared device inventory
- each profile includes a subset of those device labels
- `bringup_bindings.json` is now a versioned document
- current bindings schema version is `5`
- global axis mappings live in `bindings[]`, not top-level `axes[]`

## Phase 1: Automated Offline Gate

Run:

```powershell
python tools\common\tests\test_schema_store_profiles.py
python tools\common\tests\test_device_catalog.py
python tools\can_nt\tests\test_bridge_cli_visibility.py
python tools\can_nt\tests\test_bridge_cli_robot_test_dsl_cli.py
.\gradlew.bat test
```

Expected:

- all commands succeed

## Phase 2: Local CLI Sanity

### 1. Start CLI

```powershell
python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt
```

Expected:

- CLI starts without robot, CAN, or NT dependency

### 2. Inspect workspace

At the CLI:

```text
show workspace
show profiles
show profile
show devices
```

Expected:

- profiles load from `src/main/deploy/bringup_system.json`
- bindings load from `src/main/deploy/bringup_bindings.json`

### 3. Validate local config

At the CLI:

```text
configure terminal
validate profiles local --active
bindings validate
can-mappings validate
```

Expected:

- all validations succeed

### 4. Validate current bindings syntax

At the CLI:

```text
bindings show --all --json --pretty
bindings controller add driver0 XBOX 0
bindings binding add stop driver0 button A edge
bindings binding add leftDrive driver0 axis leftY analog invert on deadband 0.12
bindings validate
```

Expected:

- commands succeed
- output reflects unified `bindings[]` rows

### 5. Validate current test authoring path

At the CLI:

```text
test import MyTest1 temp_test.dsl set default
test validate MyTest1 --json --pretty
show test MyTest1 normalized --json --pretty
```

Expected:

- import and validation succeed

No longer current:

- legacy local interactive test authoring
- `bindings axis ...`

## Phase 3: Topology Editor Round-Trip

1. Open `src/main/deploy/bringup_system.json`
2. Make a visible change
3. Save to a new file
4. Reopen the saved file

Expected:

- file opens cleanly
- save succeeds
- reopen succeeds

## Pass Criteria

- current local CLI flows succeed
- current bindings schema validates
- current DSL import flow works
- no offline workflow depends on deleted `data\` config ownership
