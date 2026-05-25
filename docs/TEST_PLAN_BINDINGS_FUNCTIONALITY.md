# Bindings Test Plan

## Purpose

Define the current test plan for:

- global bindings in `bringup_bindings.json`
- group bindings in profile/group config
- visibility surfaces that show both

This version is current for the unified global bindings schema.

## Current Model

There are two different binding systems:

- Global bindings:
  - stored in `src/main/deploy/bringup_bindings.json`
  - edited with `bindings ...`
  - define controller inventory plus persistent controller mappings
- Group bindings:
  - stored under `bridgeConfig.byProfile.<profile>.groups`
  - edited in group mode with `bind ...`
  - define how a runtime group consumes input

They are related, but they are not the same data.

## Global Bindings Schema

Current expected shape:

```json
{
  "schema_version": 5,
  "controllers": [
    { "name": "driver0", "type": "XBOX", "port": 0 }
  ],
  "bindings": [
    {
      "command": "stop",
      "controller": "driver0",
      "input": "button",
      "id": "A",
      "mode": "edge"
    },
    {
      "command": "leftDrive",
      "controller": "driver0",
      "input": "axis",
      "id": "leftY",
      "mode": "analog",
      "invert": true,
      "deadband": 0.12
    }
  ],
  "inputAliases": {}
}
```

Current rules:

- top-level `axes[]` is not current
- axis rows live in `bindings[]`
- axis rows must use:
  - `input: "axis"`
  - `mode: "analog"`
  - `invert`
  - `deadband`

## Canonical Commands

Current global bindings commands:

- `bindings show`
- `bindings show controllers`
- `bindings show bindings`
- `bindings show --all --json --pretty`
- `bindings controller add <name> <type> <port>`
- `bindings binding add <command> <controller> <input> <id> <mode>`
- `bindings binding add <command> <controller> axis <id> analog invert <on|off> deadband <value>`
- `bindings binding set <index> <field> <value>`
- `bindings binding delete <index>`
- `bindings validate`
- `bindings validate <path>`
- `bindings save <path>`
- `bindings load <path>`

No longer current:

- `bindings axis add ...`
- `bindings axis set ...`
- `bindings axis delete ...`
- `bindings show axes`

## Automated Gate

Run:

```powershell
python tools\can_nt\tests\test_bridge_cli_visibility.py
python tools\common\tests\test_schema_store_profiles.py
```

Expected:

- both commands succeed

## Operator Procedure

### 1. Start local CLI

```powershell
python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt
```

Expected:

- CLI starts successfully

### 2. Validate shipped bindings

At the CLI:

```text
bindings validate
bindings show --all --json --pretty
```

Expected:

- validation succeeds
- output includes `"schema_version": 5`
- output uses `bindings[]`
- no top-level `axes` block is shown

### 3. Create one button binding

At the CLI:

```text
bindings controller add driver0 XBOX 0
bindings binding add stop driver0 button A edge
```

Expected:

- both commands succeed

### 4. Create one axis binding

At the CLI:

```text
bindings binding add leftDrive driver0 axis leftY analog invert on deadband 0.12
```

Expected:

- command succeeds

### 5. Inspect

At the CLI:

```text
bindings show bindings
```

Expected:

- button binding is shown
- axis binding is shown inline with `invert` and `deadband`

### 6. Save and revalidate

At the CLI:

```text
bindings save temp_bindings.json
bindings validate temp_bindings.json
```

Expected:

- save succeeds
- validation succeeds
- saved file contains `schema_version: 5`

### 7. Group binding separation

At the CLI:

```text
configure terminal
group diag
member assign "SPARKMAX/NEO 25"
bind controller0.leftY analog
show bindings
show bindings --all
```

Expected:

- `show bindings` reflects current group binding context
- `show bindings --all` still includes global bindings payload
- the two sources remain distinguishable

## Failure Checks

These must fail clearly:

- axis binding with missing controller
- axis binding with non-`analog` mode
- axis binding with invalid `deadband`
- deleting a controller still referenced by a binding
- loading a legacy file that still depends on top-level `axes[]`

## Pass Criteria

- global bindings validate with schema `5`
- unified axis rows work through `bindings binding ...`
- group bindings remain separate from global bindings
- visibility surfaces remain readable and source-aware

