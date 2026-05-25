SPEC_STATUS: IMPLEMENTED

# Feature Spec: Unified Global Bindings Schema

## Purpose

Define one canonical schema for global controller mappings so button, D-pad, combo, and axis mappings all use the same object shape.

The goal is to remove the current split between `bindings[]` and `axes[]` and replace it with one `bindings[]` collection whose entries always declare:

- `command`
- `controller`
- `input`
- `id`

Axis-specific fields such as `invert` and `deadband` remain available on axis entries.

This is a schema replacement, not an additive compatibility layer.

## Implementation Status

Purpose: record the current state of this spec.

Implemented in the current repo state:

- unified global bindings payload under `bindings[]`
- top-level `axes[]` removed from the supported schema
- root `schema_version` required on `bringup_bindings.json`
- current bindings schema version is `5`
- CLI command surface updated to use unified `bindings binding ...` syntax for axis rows
- robot-side bindings loading updated to read unified axis rows from `bindings[]`
- validator/store updated to reject legacy top-level `axes`

SID_COMMENT:
This spec now describes the implemented hard-cut schema and current command surface.

## Summary

Current global controller config is split across two different arrays:

- `bindings[]` for button-like inputs
- `axes[]` for analog axis inputs

Those arrays do not share the same object shape.

Today:

- `bindings[]` uses `input` to mean input kind such as `button`, `dpad`, or `combo`
- `bindings[]` uses `id` to mean the specific control such as `A` or `UP`
- `axes[]` omits `input` entirely
- `axes[]` uses `id` directly for the axis name such as `leftY`

This spec replaces that split model with one unified binding-entry schema.

Example target shape:

```json
{
  "command": "leftDrive",
  "controller": "controller0",
  "input": "axis",
  "id": "leftY",
  "mode": "analog",
  "invert": true,
  "deadband": 0.12
}
```

## Problem Statement

The current schema is inconsistent in ways that make the system harder to explain, validate, and evolve.

Effects:

- operators must learn two different controller-mapping shapes
- docs must explain two related but different concepts
- validators and CLI editing paths must special-case axis entries
- autocomplete/help cannot treat all global mappings uniformly
- migrations and future input families become harder

The inconsistency is structural, not cosmetic.

## Goals

- Define one canonical data shape for all global controller mappings.
- Use `input` consistently to mean input kind.
- Use `id` consistently to mean the specific control within that kind.
- Move axis mappings into the same collection as button-like mappings.
- Preserve the existing semantic capabilities of global mappings.
- Make the CLI, docs, validator, and robot runtime use the same schema.

## Non-Goals

- Backward compatibility with the old split `axes[]` schema.
- Silent migration at runtime.
- Redesign of group-local `bind ...` syntax in this pass.
- Changes to test DSL syntax in this pass.
- Changes to NetworkTables contracts in this pass.

## Canonical Data Model

Purpose: Define the only supported post-migration JSON shape.

`bringup_bindings.json` must contain:

- `schema_version`
- `controllers`
- `bindings`
- optional `inputAliases`

The `axes` top-level array is removed.

Each binding entry must contain:

- `command`
- `controller`
- `input`
- `id`
- `mode`

Optional fields are allowed only when valid for the chosen input kind.

### Required Fields

- `command`: command name to invoke
- `controller`: declared controller name such as `controller0`
- `input`: input kind
- `id`: input identifier within that kind
- `mode`: activation/evaluation mode

### Supported `input` Kinds

- `button`
- `dpad`
- `combo`
- `axis`

### Supported `mode` Values

This spec preserves existing current mode families and makes axis activation explicit.

- `edge`
- `hold`
- `toggle`
- `analog`

SID_COMMENT:
Current implemented persisted modes for global bindings are `edge`, `hold`, `toggle`, and `analog`.

### Input-Kind Rules

#### `input: "button"`

- `id` must be one of the supported button identifiers such as `A`, `B`, `X`, `Y`, `LB`, `RB`, `LS`, `RS`, `START`, `BACK`
- `mode` must be a button-compatible mode such as `edge`, `hold`, or `toggle`
- `invert` is not allowed
- `deadband` is not allowed

#### `input: "dpad"`

- `id` must be one of `UP`, `RIGHT`, `DOWN`, `LEFT`
- `mode` must be button-compatible
- `invert` is not allowed
- `deadband` is not allowed

#### `input: "combo"`

- `id` must be a `+`-joined list of supported button identifiers such as `LB+X` or `LB+RB`
- `mode` must be button-compatible
- `invert` is not allowed
- `deadband` is not allowed

#### `input: "axis"`

- `id` must be one of the supported axis identifiers such as `leftX`, `leftY`, `rightX`, `rightY`, `leftTrigger`, `rightTrigger`
- `mode` must be `analog`
- `invert` is required
- `deadband` is required

### Unified Examples

Button:

```json
{
  "command": "runAllTests",
  "controller": "controller1",
  "input": "button",
  "id": "B",
  "mode": "edge"
}
```

D-pad:

```json
{
  "command": "printCANdiag",
  "controller": "controller0",
  "input": "dpad",
  "id": "UP",
  "mode": "edge"
}
```

Combo:

```json
{
  "command": "printState",
  "controller": "controller0",
  "input": "combo",
  "id": "LB+X",
  "mode": "edge"
}
```

Axis:

```json
{
  "command": "leftDrive",
  "controller": "controller0",
  "input": "axis",
  "id": "leftY",
  "mode": "analog",
  "invert": true,
  "deadband": 0.12
}
```

## Current-to-Target Mapping

Purpose: Define exactly how current data maps into the new schema.

Current button-like entry:

```json
{
  "command": "runTest",
  "controller": "controller1",
  "input": "button",
  "id": "A",
  "mode": "hold"
}
```

Target entry:

- unchanged

Current axis entry:

```json
{
  "command": "leftDrive",
  "controller": "controller0",
  "id": "leftY",
  "invert": true,
  "deadband": 0.12
}
```

Target entry:

```json
{
  "command": "leftDrive",
  "controller": "controller0",
  "input": "axis",
  "id": "leftY",
  "mode": "analog",
  "invert": true,
  "deadband": 0.12
}
```

## Migration Policy

Purpose: Define how existing repo data is converted.

This change uses a hard cutover.

- No backward compatibility is provided.
- No mixed old/new schema files are supported.
- No runtime compatibility reader is retained after migration.
- The robot, CLI, validator, and docs all move to the new schema together.

### Migration Inputs

Existing data sources to convert:

- `src/main/deploy/bringup_bindings.json`
- any checked-in regression fixtures containing global bindings payloads
- docs that show `axes[]`
- tests that build or assert old-style bindings payloads

### Migration Transform

For each legacy `axes[]` entry:

1. Copy `command`
2. Copy `controller`
3. Set `input` to `"axis"`
4. Copy `id`
5. Set `mode` to `"analog"`
6. Copy `invert`
7. Copy `deadband`
8. Append the new object to `bindings[]`

After all axis entries are converted:

1. Delete the top-level `axes` array
2. Re-run validation
3. Update expected outputs and docs

### Example Migration

Before:

```json
{
  "controllers": [
    { "name": "controller0", "type": "XBOX", "port": 0 }
  ],
  "bindings": [
    { "command": "runTest", "controller": "controller1", "input": "button", "id": "A", "mode": "hold" }
  ],
  "axes": [
    { "command": "leftDrive", "controller": "controller0", "id": "leftY", "invert": true, "deadband": 0.12 }
  ]
}
```

After:

```json
{
  "schema_version": 5,
  "controllers": [
    { "name": "controller0", "type": "XBOX", "port": 0 }
  ],
  "bindings": [
    { "command": "runTest", "controller": "controller1", "input": "button", "id": "A", "mode": "hold" },
    { "command": "leftDrive", "controller": "controller0", "input": "axis", "id": "leftY", "mode": "analog", "invert": true, "deadband": 0.12 }
  ]
}
```

## Validation Rules

Purpose: Define post-migration validation requirements.

Validation must reject:

- any top-level `axes` key
- any binding entry missing `input`
- `input: "axis"` without `invert`
- `input: "axis"` without `deadband`
- `input: "axis"` with any mode other than `analog`
- non-axis entries that include `invert`
- non-axis entries that include `deadband`
- unknown `input` kinds
- unknown `id` values for the given `input` kind
- unknown controller names

Validation must continue to enforce:

- `schema_version` must equal `5`
- controller declaration required before use
- deadband range `0.0..1.0`
- command/controller/id/mode must be non-empty strings

## CLI Contract Changes

Purpose: Define the required CLI changes for the new schema.

The global-bindings command surface must become schema-aligned.

### Removed Command Family

Remove:

```text
bindings axis add <command> <controller> <id> invert <on|off> deadband <value>
bindings axis set <index> <field> <value>
bindings axis delete <index>
bindings show axes
```

### Canonical Replacement

Use only:

```text
bindings binding add <command> <controller> axis <id> analog invert <on|off> deadband <value>
bindings binding set <index> <field> <value>
bindings binding delete <index>
bindings show bindings
```

SID_COMMENT:
The implemented CLI keeps one `bindings binding add ...` command family and uses optional trailing axis fields for `input=axis`.

### Show Output

`show bindings` and `bindings show` must present axis entries in the same list as all other global bindings.

Axis entries must display:

- `input=axis`
- `id=<axisId>`
- `mode=analog`
- `invert=<bool>`
- `deadband=<value>`

## Robot Runtime Contract Changes

Purpose: Define how robot-side loading changes.

The robot bindings loader must:

- stop reading `axes[]`
- read only unified `bindings[]`
- interpret `input: "axis"` entries as the old axis-control path
- preserve current runtime behavior for analog control semantics

This is a loader/schema rewrite, not a behavior redesign.

Expected semantic preservation:

- existing drive-axis behavior remains the same
- existing deadband handling remains the same
- existing invert handling remains the same
- existing button/D-pad/combo bindings remain the same

## Documentation Changes

Purpose: Keep operator and developer docs aligned with the cutover.

Update all current docs that describe global bindings to:

- remove the idea of a separate `axes[]` collection
- define `axis` as a valid `input` kind
- explain `mode=analog` for axis entries
- replace `bindings axis ...` CLI examples with unified `bindings binding ...` examples

Docs updated for the cutover included at minimum:

- `docs/CLI_USER_MANUAL.md`
- `docs/CLI_REFERENCE_MANUAL.md`
- `docs/CLI_FUNCTIONAL_AREAS_USER_GUIDE.md`
- `docs/CLI_Spec.md`
- `docs/BRIDGE_CLI_FULL_SPEC.md`
- `docs/TESTING.md`

## Testing Strategy

Purpose: Define the minimum coverage required for the cutover.

### Schema Store Tests

- loading a unified bindings payload with axis entries succeeds
- loading any payload with top-level `axes` fails
- axis entries missing `mode=analog` fail
- axis entries missing `invert` or `deadband` fail
- non-axis entries with axis-only fields fail

### CLI Tests

- `bindings binding add ... axis ... analog invert ... deadband ...` succeeds
- `bindings binding set` can edit axis entries
- `bindings show` prints axis entries inline with others
- old `bindings axis ...` commands fail clearly
- help text and suggestions show `axis` as a valid input kind

### Robot Tests

- unified axis entry loads and drives the same runtime path as the old `axes[]` entry
- button, D-pad, combo entries remain unaffected

### Regression Updates

- update CLI regression fixtures to the unified schema
- update any expected exported config scripts
- update docs/tests that inspect `show workspace` or bindings payloads if they mention `axes`

## Rollout Summary

Purpose: record the execution order that was completed.

Completed order:

1. Updated schema-store validation and sanitizer.
2. Updated robot-side bindings loader.
3. Updated CLI parsing, editing, help, and grammar.
4. Migrated checked-in JSON data.
5. Updated regression fixtures and tests.
6. Updated current docs.
7. Removed old `axes` code paths.

Result:

- old and new schema shapes are not both supported on `main`
- legacy top-level `axes[]` is rejected

## Tradeoffs

Purpose: Record the main tradeoffs of the hard cutover.

- The unified schema is easier to understand and extend.
- The migration is simpler because there is one canonical target shape.
- The hard cutover avoids long-term dual-schema maintenance.
- The cost is a synchronized update across robot, CLI, validator, tests, and docs.
- Old JSON files stop working immediately after the cutover unless migrated.

## Future Extensions

Purpose: Identify safe follow-on work once the unified schema exists.

- add richer axis metadata if needed, such as response curves
- unify local group-bind metadata around the same input-kind vocabulary
- add machine-generated migration tooling for future schema rewrites
- add schema version markers if future hard-cut schema changes become more likely
