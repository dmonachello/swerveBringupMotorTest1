# Bringup Diagnostics System Testing Guide

## Purpose

Provide the current high-level testing guide for the bringup system.

This guide is intentionally current-only. It does not preserve removed workflows.

## Current Testing Entry Points

Use these documents:

- [TEST_PLAN_CURRENT_SYSTEM_2026_05_23.md](./TEST_PLAN_CURRENT_SYSTEM_2026_05_23.md)
- [TEST_PLAN_TODAY.md](./TEST_PLAN_TODAY.md)
- [TEST_PLAN_BINDINGS_FUNCTIONALITY.md](./TEST_PLAN_BINDINGS_FUNCTIONALITY.md)
- [TESTING_WINDOWS_OFFLINE.md](./TESTING_WINDOWS_OFFLINE.md)

## Terminology

- Host context: local editing and inspection state on the PC
- Robot context: runtime profile/test state on the roboRIO
- Defined device: device exists in `devices[]`
- Profile device: current profile includes that device label
- Instantiated device: runtime created the live device object
- Group member: device label is assigned to a group

These are separate states.

## Current Rules Under Test

- deploy-owned config under `src/main/deploy/`
- multiple profiles may exist in one `bringup_system.json` system config file
- `devices[]` is the shared device inventory in the loaded system config
- each profile selects a subset of those devices
- `bringup_bindings.json` uses `schema_version: 5`
- global axis mappings live in unified `bindings[]`
- DSL import is the current local test authoring path

## Current Automated Gate

Run:

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

- all commands succeed

## Current Manual Areas

- local CLI workspace/config validation
- unified bindings schema checks
- DSL import/validate/show checks
- topology editor round-trip
- connected roboRIO non-motion checks when hardware is available

## Removed Or Obsolete Workflows

These are not current and should not be used as primary test procedures:

- local interactive `test create` / `type` / `inputSource` authoring
- top-level global `axes[]` bindings schema
- `bindings axis ...` commands
- deleted separate `data\` ownership workflows for `bringup_system.json`

## Current Recommendation

If there is any conflict between older examples and the new current-system plan, follow:

- [TEST_PLAN_CURRENT_SYSTEM_2026_05_23.md](./TEST_PLAN_CURRENT_SYSTEM_2026_05_23.md)
