# Activation Membership Modes

## Purpose

Define how controlled lifecycle activation should treat unavailable members when the operator activates a device group or a selected test scope.

## Problem

The current controlled lifecycle model is effectively all-or-nothing.

That behavior is too restrictive for troubleshooting:

- one unavailable motor can block the entire active group
- a selected test can become unrunnable even when some required devices are still healthy
- operators lose the ability to probe what still works while isolating a fault

This was an unexpected product limitation. In practice, the common debugging case is that one device is down and the operator still needs to run the remaining healthy devices.

## Design Goal

Keep the existing safety principle that unavailable devices should not normally be treated as runnable, while adding explicit operator-selectable membership policies for group activation.

## Terminology

### Activation Mode

Existing access policy:

- `PROBE_ONLY`
- `READ_ONLY`
- `ACTUATION_ALLOWED`

This answers:

- what level of interaction is allowed once a lifecycle session is active

### Activation Membership Mode

New membership-selection policy:

- `STRICT`
- `PARTIAL`
- `FORCE`

This answers:

- which requested devices should actually be attempted during activation

These are separate concepts and must remain separate in code, JSON, and UI.

## Modes

### `STRICT`

All requested members must be runnable now.

Behavior:

- if any requested device is not runnable, activation fails
- no partial session is created
- unavailable members are reported as blocked members

Use cases:

- formal bringup
- subsystem validation
- regression confirmation

### `PARTIAL`

Attempt only devices that current lifecycle evidence says are runnable.

Behavior:

- runnable members are activated
- unavailable members are skipped
- skipped members are reported explicitly
- if no requested members are runnable, activation fails

Use cases:

- pit troubleshooting
- fault isolation
- running what still works while investigating a failure

### `FORCE`

Attempt all requested devices even if current lifecycle evidence says some are unavailable.

Behavior:

- all requested members are passed through for activation
- no members are pre-skipped by lifecycle evidence
- actual device creation may still fail at runtime

Use cases:

- challenge a suspected false negative in the evidence model
- verify whether lifecycle interpretation is wrong
- deliberately probe reality beyond the current data model

## Defaults

### Robot command parser default

If `membershipMode` is omitted from a lifecycle activation command, the robot must default to `STRICT`.

Rationale:

- preserve backward compatibility for existing callers
- avoid silent behavior changes for command senders that do not know about the new field

### Host UI default

The top-bar activation selector in the PC bringup UI should default to `PARTIAL`.

Rationale:

- the main operator workflow is troubleshooting
- partial activation is the least frustrating mode when one device is down
- healthy devices should remain usable by default during diagnosis

## Command Contract

## Request

Lifecycle activation requests may include:

- `mode`
- `membershipMode`

Example:

```json
{
  "label": "active-group",
  "mode": "READ_ONLY",
  "membershipMode": "PARTIAL"
}
```

Selected-test activation follows the same pattern:

```json
{
  "mode": "READ_ONLY",
  "membershipMode": "FORCE"
}
```

## Response

Activation results must include:

- `mode`
- `membershipMode`
- `requestedDeviceLabels`
- `instantiatedDeviceLabels`
- `failedDeviceLabels`
- `skippedDeviceLabels`

`skippedDeviceLabels` is primarily meaningful for `PARTIAL`.

## Robot-Side Semantics

Membership filtering is applied before activation-manager device creation.

### `STRICT`

- determine which requested devices are runnable now
- if any are not runnable, fail activation
- return those devices in `skippedDeviceLabels`

### `PARTIAL`

- determine which requested devices are runnable now
- activate only runnable devices
- return unavailable devices in `skippedDeviceLabels`
- if no devices are runnable, fail activation

### `FORCE`

- bypass pre-filtering
- attempt all requested devices
- do not pre-populate `skippedDeviceLabels`

## UI Behavior

## Top Bar

The top bar must expose an explicit `Activation Mode` selector with:

- `PARTIAL`
- `STRICT`
- `FORCE`

The selector applies to:

- `Activate Group`
- selected-test lifecycle activation

## Output

The UI command log should echo the selected membership mode in the activation command text.

Example:

```text
CMD lifecycleActivate "active-group" mode=READ_ONLY membershipMode=PARTIAL
```

## Success Messages

When `PARTIAL` activates successfully with exclusions, the success message should report excluded members.

Example:

```text
active-group active - ready to run excluded: SPARKMAX/NEO 25
```

## Tradeoffs

### Benefits

- healthy devices remain usable during troubleshooting
- lifecycle behavior matches pit-side diagnosis needs better
- operators can choose how strongly to trust the evidence model

### Risks

- more operator choice can be confusing if unlabeled or hidden
- `FORCE` can attempt devices that current evidence believes are unavailable
- `STRICT` remains useful, but should no longer be the only workflow

## Acceptance Criteria

### Scenario: one device down in active-group

Requested members:

- `FALCON 9`
- `SPARKMAX/NEO 25`

Current lifecycle evidence:

- `FALCON 9` runnable
- `SPARKMAX/NEO 25` unavailable

Expected behavior:

- `STRICT`
  - activation fails
  - blocked member is reported
- `PARTIAL`
  - `FALCON 9` activates
  - `SPARKMAX/NEO 25` is reported in `skippedDeviceLabels`
- `FORCE`
  - both members are attempted
  - any later failure is a real activation/runtime failure, not a pre-filter rejection

### Scenario: selected test requires two devices and one is unavailable

Expected behavior:

- `PARTIAL` allows the healthy subset to activate if at least one requested device is runnable
- `STRICT` rejects the activation
- `FORCE` attempts the full requested set

## Future Extensions

- remember the last chosen membership mode per UI session
- optionally persist a preferred mode per operator workflow
- add a visible result panel that lists:
  - requested members
  - activated members
  - skipped members
  - force-attempted members
