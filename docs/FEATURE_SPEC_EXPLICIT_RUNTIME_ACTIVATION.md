SPEC_STATUS: PROPOSED

# Feature Spec: Explicit Runtime Activation

## Purpose

Separate profile selection from hardware-affecting runtime activation so the robot does not instantiate devices automatically at boot.

## Problem

Current startup behavior couples these steps:

1. config load
2. profile selection
3. runtime activation
4. device instantiation

That means the robot attempts to bring up the selected default profile immediately during boot. This is risky for bringup work because:

- bad or incomplete profiles can allocate hardware before operator intent
- recovery is harder because boot already changed runtime state
- profile browsing and editing are not cleanly separated from hardware activation
- duplicate vendor allocations can happen earlier than needed

## Goals

- Boot must stop after config load and profile selection.
- Runtime activation must require an explicit command.
- The selected profile must be changeable before any runtime activation.
- The selected profile and the active runtime profile must be modeled separately.
- CLI, REST, UI, and controller-owned runtime logic must all follow the same contract.
- Runtime activation and deactivation must be available through both CLI and REST.
- The UI must use the REST interface for runtime activation rather than a separate internal shortcut.

## Non-Goals

- Redesign the profile schema.
- Change hardware definitions or topology format.
- Automatically activate a profile on Driver Station mode changes.
- Add backward-compatibility behavior that silently reintroduces implicit activation.

## Current Behavior

Current robot boot behavior flows through:

- `RobotV2.robotInit()`
- `RobotV2.activateSelectedProfileForAllSurfaces(...)`
- `BringupRuntime.activateSelectedProfile(...)`
- `BringupRuntime.resetAndInstantiateForProfile(...)`
- `BringupCore.reloadActiveProfileRuntime(...)`

This path activates the selected profile and instantiates all active-profile devices during robot startup.

## Desired Contract

Startup must be split into two phases.

### Phase 1: Selection

Boot performs:

1. config load
2. selected profile resolution
3. stop

After Phase 1:

- config is loaded
- selected profile is known
- no runtime profile is active yet
- no bringup devices are instantiated yet

### Phase 2: Activation

A separate explicit action performs:

1. activate selected profile runtime
2. rebuild runtime state
3. instantiate profile devices
4. refresh aliases, groups, and runtime-owned state

Activation is the only place that may call:

- `resetAndInstantiateForProfile(...)`
- `reloadActiveProfileRuntime(...)`
- add-all or equivalent device instantiation paths

## State Model

The system must expose these distinct concepts.

### Config Loaded

- whether `bringup_system.json` is parsed and accepted

### Selected Profile

- the profile currently chosen by the operator or host
- safe to change without affecting hardware

### Active Runtime Profile

- the profile currently instantiated on hardware
- may be `none`

### Runtime Active

- boolean state indicating whether bringup runtime is currently instantiated

## Required Behavioral Rules

### Boot

On robot boot:

- load config
- resolve selected/default profile
- do not activate runtime
- do not instantiate devices

### Profile Selection

Selecting a profile:

- updates only the selected profile
- does not instantiate devices
- does not clear and rebuild runtime
- does not stop or start devices by itself

### Runtime Activation

Runtime activation:

- activates the currently selected profile unless a command explicitly names another profile
- rebuilds runtime state
- instantiates bringup devices
- becomes the only path that makes the selected profile become the active runtime profile

### Profile Changes While Runtime Is Inactive

When runtime is inactive:

- the operator may switch selected profiles freely
- no hardware action occurs

### Profile Changes While Runtime Is Active

When runtime is active and the selected profile changes:

- the active runtime profile remains unchanged
- the selected profile may now differ from the active runtime profile
- no automatic runtime rebuild occurs
- a later explicit activation applies the selected profile

### Runtime-Inactive Command Handling

Robot-active commands that require instantiated devices must not auto-activate implicitly.

They must fail clearly with a message equivalent to:

- `Runtime inactive. Activate selected profile first.`

This includes at minimum:

- manual device duty commands
- group actuation commands
- test run commands
- report/test commands that require live instantiated devices

Pure config and visibility commands must still work while runtime is inactive.

## Operator Surface Requirements

### CLI

The CLI must distinguish:

- selected profile
- active runtime profile
- runtime active or inactive

The CLI must provide an explicit activation command.

Locked canonical forms:

- `runtime activate`
- `runtime deactivate`

Optional convenience form:

- `runtime activate <profile>`

This may select the named profile and then activate it in one explicit operator action.

### REST

REST must expose explicit runtime activation rather than relying on config push side effects.

Locked transport shape:

- `POST /commands` with `name: "runtimeActivate"`
- `POST /commands` with `name: "runtimeDeactivate"`

REST responses must expose enough state for clients to know:

- selected profile
- active runtime profile
- runtime active or inactive

### UI

The UI must show:

- selected profile
- active runtime profile
- whether runtime is active

The UI must not assume profile selection implies activation.

The UI must offer an explicit activation action.

The UI must invoke activation and deactivation through the REST command surface.

The UI must not use a separate internal shortcut path for these actions.

### Controller-Owned Flows

Controller-owned runtime behavior stays local to Java, but it must use the same runtime state model.

If runtime is inactive:

- controller-driven actuation must remain inactive
- no hidden auto-activation is allowed

## Config Push Semantics

This change affects the meaning of `config push`.

Current docs widely describe:

- `config push <path> --activate <profile>`

Locked command contract:

- `config push <path>`
  - loads config
  - updates selected profile when applicable
  - does not instantiate runtime
- `config push <path> --activate <profile>`
  - is allowed as an explicit convenience wrapper
  - must perform:
    1. config push
    2. profile selection
    3. explicit activation through the same shared activation path used by CLI/REST/UI
  - must not rely on hidden implicit activation semantics

The spec requires:

- push without activation must not instantiate runtime
- any activation behavior must be explicit in the command surface

## Reporting and Visibility

The system should report all three profile-related states clearly:

- config selected profile
- active runtime profile
- runtime active or inactive

Examples of surfaces that should reflect this:

- `show runtime-state`
- `show profile`
- REST session or health payloads
- UI status bar or profile pane

## Failure Semantics

### Activation Failure

If runtime activation fails:

- selected profile remains selected
- previous active runtime profile remains unchanged if one existed
- runtime state must not be left half-switched without an explicit degraded-state marker

### Deactivation

The system should define an explicit deactivation path that:

- stops active runtime-owned actuation
- clears active runtime profile state
- returns the system to selected-but-inactive state

The canonical operator surfaces must include:

- CLI: `runtime deactivate`
- REST: `POST /commands` with `name: "runtimeDeactivate"`

## Implementation Direction

The expected code split is:

### Selection Layer

Owns:

- config load
- default profile resolution
- selected profile mutation

This exists today primarily around:

- `BringupUtil.selectCanProfile(...)`
- profile resolution helpers in `BringupUtil`

### Activation Layer

Owns:

- runtime rebuild
- device instantiation
- alias and group refresh
- active runtime profile transitions

This exists today primarily around:

- `BringupRuntime.activateSelectedProfile(...)`
- `BringupRuntime.resetAndInstantiateForProfile(...)`
- `BringupCore.reloadActiveProfileRuntime(...)`
- `RobotV2.activateSelectedProfileForAllSurfaces(...)`

The main required behavior change is:

- remove automatic activation from `robotInit()`
- preserve explicit activation paths
- make every surface call the same activation layer explicitly

## Migration Requirements

Implementation planning must account for:

- CLI help and grammar updates
- REST command and status updates
- UI activation affordance
- docs that currently assume startup auto-activation
- tests that assume selected profile is immediately active

## Acceptance Criteria

- Boot loads config and selects a profile without instantiating devices.
- After boot, runtime state is inactive until an explicit activation command is issued.
- The operator can change selected profile multiple times before the first activation.
- After activation, the active runtime profile matches the selected profile at activation time.
- Changing selected profile while runtime is active does not auto-rebuild runtime.
- Runtime-dependent commands fail clearly when runtime is inactive.
- CLI, REST, and UI all surface selected profile versus active runtime profile distinctly.

## Tradeoffs

- This adds one more explicit step for operators who want immediate bringup.
- It reduces accidental hardware allocation and makes recovery behavior more predictable.
- It makes the state model more explicit but also slightly more complex, because selected and active profiles may differ temporarily.

## Future Extensions

- add a dedicated runtime deactivate command
- add a staged activation dry-run that validates without instantiating hardware
- allow host tools to warn when selected and active runtime profiles differ
