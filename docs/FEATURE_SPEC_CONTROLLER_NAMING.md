SPEC_STATUS: PARTIALLY_IMPLEMENTED

# Feature Spec: Controller Naming + Unified Input Sources

## Purpose

Make controller selection explicit and consistent across robot control, UI, and CLI. Allow multiple named controllers, with a unified `inputSource` syntax for both buttons and axes.

## Goals

- Allow up to 6 controllers with explicit names.
- Standardize on `leftY/rightY/leftX/rightX` for axes.
- Use a single `inputSource` format for both axes and buttons: `name.leftY` or `name.A`.
- Work consistently across:
  - `bringup_bindings.json`
  - Robot control bindings
  - UI
  - CLI test authoring
- Default controller names are `controller0`..`controller5` when `controllers` is omitted.

## Non-Goals

- Redesign existing controller mappings or button layouts.
- Preserve legacy controller naming or input syntax.

## Controller Model

- Controllers are defined in `bringup_bindings.json`.
- Each controller has:
  - `name` (string, required, case-sensitive)
  - `type` (e.g., `XBOX`)
  - `port` (0-9)
- Maximum controllers: 6.
- If `name` is omitted, default to `controller0`..`controller5` based on port index.

### Example

```json
{
  "controllers": [
    { "name": "controller0", "type": "XBOX", "port": 0 },
    { "name": "controller1", "type": "XBOX", "port": 1 },
    { "name": "controller2", "type": "XBOX", "port": 2 }
  ]
}
```

## Unified Input Source Syntax

### Format

```
inputSource = <controllerName>.<inputId>
```

### Inputs

- Axes (WPILib naming): `leftX`, `leftY`, `rightX`, `rightY`, `leftTrigger`, `rightTrigger`
- Buttons (WPILib naming): `A`, `B`, `X`, `Y`, `LB`, `RB`, `LS`, `RS`, `START`, `BACK`, `D_UP`, `D_DOWN`, `D_LEFT`, `D_RIGHT`

### Examples

- `inputSource controller0.leftY`
- `inputSource controller1.A`
- `inputSource controller2.D_LEFT`

## CLI Behavior

- New command: `inputSource <controller>.<inputId>`
- Applies to button tests and joystick tests.
- CLI `show` output must print the resolved `inputSource`.

## JSON Schema (Tests)

### Joystick Test

```json
{
  "type": "joystick",
  "name": "Joystick motor (controller0.leftY)",
  "enabled": true,
  "motorLabels": ["SPARKMAX/NEO 25"],
  "deadband": 0.12,
  "inputSource": "controller0.leftY"
}
```

### Button Test

```json
{
  "type": "composite",
  "name": "Hold to run",
  "enabled": true,
  "motorLabels": ["FALCON 9"],
  "duty": 0.2,
  "termination": { "hold": true },
  "inputSource": "controller1.A"
}
```

## Robot Behavior

- Resolve controller names from `bringup_bindings.json`.
- `inputSource` is required for joystick and button tests (no defaults).
- If a controller name is missing or disconnected, treat input as inactive (no action).

## UI Behavior

- Display controller names wherever input bindings appear.
- Allow selecting controller names in UI when creating or editing test input bindings.
- If multiple controllers are defined, show them in dropdowns.

## Validation Rules

- Controller names must be unique and case-sensitive.
- Max controllers: 6.
- `inputSource` is required and must be `name.inputId`.
- `name` must match a configured controller or a default `controllerN` name.
- `inputId` must be one of the defined axes or buttons.

## Grammar / EBNF Updates (Required)

- Add `inputSource` command to the CLI grammar.
- Allow `inputSource <controller>.<inputId>` in test authoring mode.
- Update parser constants and regenerate the grammar outputs.

## Backward Compatibility

- Existing JSON and CLI commands must be updated to include `inputSource`.
- Legacy `primary`/`secondary` names are removed in favor of `controller0..controller5`.

## Open Questions (Resolved)

- Standard axes: `leftY/rightY/leftX/rightX` (confirmed).
- Single unified `inputSource` syntax for axes + buttons (confirmed).

