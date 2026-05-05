# Feature Spec: Test Creation DSL Post-V1 Scope

## Purpose

Record DSL features intentionally deferred beyond the first unified DSL release.

This document exists to keep the v1 scope small and explicit while preserving the agreed direction for later work.

## V1 Boundary

V1 includes:

- One unified DSL-based test model
- No legacy test types
- Flat single-body test definitions
- Configured device binding with `device add`
- Built-in `timer` and optional created `TestTimer` pseudo-devices
- Signal-based commands and conditions
- Global `abort`
- `until`, `expect`, and `success`
- `passive true|false`
- `manual_stop true|false`
- Test-wide input bindings with defaults and optional shaping

V1 does not include staged execution.

## Deferred Features

## Explicit Step Blocks

Purpose: Support multi-stage tests inside one test definition.

Deferred syntax direction:

```text
step "<name>"
  command ...
  until ...
  expect ...
  success ...
```

Reason deferred:

- Adds parser, validator, serializer, and runtime complexity
- Not needed for the first unified DSL release
- Rare compared with single-body tests

## Staged Procedures

Purpose: Support tests that intentionally change commands over time within one run.

Examples:

- Ramped output tests
- Multi-phase bringup checks
- Search procedures that advance until a threshold is found

Reason deferred:

- Requires explicit step semantics first
- Not needed for the initial replacement of `composite`, most `button`, most `joystick`, and signal-based `deviceAction`

## Deadband Sweep Replacement

Purpose: Re-express the old `deadbandSweep` behavior in the unified DSL.

Expected future form:

- Implemented as a staged procedure using explicit steps
- Not retained as a separate test type

Reason deferred:

- Deadband sweep is the only currently known feature that clearly requires staged execution
- It is acceptable to omit this capability from v1

## Step-Local Abort

Purpose: Allow `abort` conditions scoped to a specific step instead of the whole test.

Expected future behavior:

- Test-level `abort` remains global
- Step-local `abort` may be added only if real usage justifies it

Reason deferred:

- Global `abort` covers current safety needs
- Step-local abort introduces extra precedence and scope rules

## Non-Goals For This Deferred Document

This document does not define:

- A migration path from legacy test types
- Temporary presets or compatibility shims
- Branching or looping execution
- Runtime implementation details

## Current Product Decision

The product direction is:

- one DSL
- one test model
- no long-term separate test types

Features deferred from v1 are postponed because they add execution complexity, not because they require preserving the old type system.

## Entry Criteria For Post-V1 Work

Post-v1 staged execution work should begin only when at least one of these is true:

- A real test workflow cannot be expressed as a flat single-body test
- Deadband characterization becomes a required operator workflow
- Multi-phase execution is needed often enough that splitting into separate tests is no longer acceptable

## Exit Criteria For Post-V1 Work

A post-v1 staged execution release should not be considered complete until it defines:

- Exact `step` syntax
- Legal statements at test scope versus step scope
- Step transition rules
- Interaction with global `abort`
- Validation errors for invalid step structure
- CLI authoring, persistence, and runtime behavior
