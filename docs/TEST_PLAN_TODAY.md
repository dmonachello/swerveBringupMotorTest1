# Test Plan Today - May 23, 2026

## Purpose

Provide the current operator-facing regression plan for this workspace.

This file is the short daily entrypoint.

## Today’s Gate

Run these in order from the repo root:

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
- zero regression failures are reported

## Focus Areas

Today’s plan specifically covers:

- unified global bindings schema
- `bringup_bindings.json` root `schema_version: 5`
- deploy-owned config under `src/main/deploy/`
- removal of legacy local interactive test authoring
- DSL import/validate/show workflow
- robot-local command modularization compatibility

## Current Rules To Check

- `bringup_system.json` and `bringup_bindings.json` are the active config sources
- deleted `data\` config ownership is not referenced by current workflows
- global axis mappings live in `bindings[]` with `input: "axis"` and `mode: "analog"`
- top-level `axes[]` is no longer current
- `bindings axis ...` is no longer current CLI syntax
- `test create`, `type`, `inputSource`, and similar legacy interactive local test authoring commands are no longer current

## If Manual Follow-Up Is Needed

Use the detailed procedures in:

- [TEST_PLAN_BINDINGS_FUNCTIONALITY.md](./TEST_PLAN_BINDINGS_FUNCTIONALITY.md)
- [TESTING_WINDOWS_OFFLINE.md](./TESTING_WINDOWS_OFFLINE.md)
- [TEST_PROCEDURE_FULL_ROBOT_FROM_SCRATCH_V3.md](./TEST_PROCEDURE_FULL_ROBOT_FROM_SCRATCH_V3.md)
