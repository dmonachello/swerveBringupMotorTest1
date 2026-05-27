SPEC_STATUS: PROPOSED

# Explicit Runtime Activation Implementation Plan

## Purpose

Turn [FEATURE_SPEC_EXPLICIT_RUNTIME_ACTIVATION.md](/c:/Users/dmona/swerveBringupMotorTest1-main/docs/FEATURE_SPEC_EXPLICIT_RUNTIME_ACTIVATION.md) into a concrete implementation plan based on the current bringup codebase.

This is a planning document only. It defines the migration shape and execution order. It does not authorize skipping validation or doing out-of-order cleanup.

## Goal

Change bringup startup and operator surfaces so that:

- boot performs config load and profile selection only
- bringup runtime remains inactive after boot
- profile selection is cheap and non-hardware-affecting
- runtime activation is explicit and shared across CLI, REST, UI, and local controller-owned logic

## Inspected Current Structures

### Robot Startup And Activation Path

Inspected files:

- [src/main/java/frc/robot/RobotV2.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/RobotV2.java)
- [src/main/java/frc/robot/BringupRuntime.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BringupRuntime.java)
- [src/main/java/frc/robot/BringupCore.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BringupCore.java)

Observed current behavior:

- `RobotV2.robotInit()` calls `BringupUtil.applyProfileFromArgs()`
- the same `robotInit()` then calls `activateSelectedProfileForAllSurfaces(REASON_STARTUP_PROFILE_LOAD)`
- `activateSelectedProfileForAllSurfaces(...)` triggers:
  - `runtime.activateSelectedProfile(...)`
  - `refreshInputAliases()`
  - `syncDefaultGroup()`
- `BringupRuntime.activateSelectedProfile(...)` triggers:
  - `BringupUtil.prepareActivationForSelectedProfile()`
  - `BringupUtil.activateSelectedProfile()`
  - `resetAndInstantiateForProfile(...)`
- `resetAndInstantiateForProfile(...)` calls `BringupCore.reloadActiveProfileRuntime(...)`
- `reloadActiveProfileRuntime(...)` rebuilds runtime state and instantiates devices

Conclusion:

- startup auto-activation is real and centralized
- the main boot coupling point is `RobotV2.robotInit()`

### Existing Selection Versus Activation Model

Inspected file:

- [src/main/java/frc/robot/BringupUtil.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BringupUtil.java)

Observed current behavior:

- the repo already has separate concepts for:
  - `selectedProfile`
  - `activeProfile`
  - `activeProfileApplied`
- `selectCanProfile(...)` changes only the selected profile
- `selectNextProfile()` advances selection without activation
- `activateSelectedProfile()` applies the selected profile
- `deactivateActiveProfile()` clears active runtime-owned profile state

Conclusion:

- the conceptual split already exists in the core utility layer
- the main problem is not missing primitives
- the main problem is that startup and some surfaces still collapse selection and activation into one flow

### Surface Entry Points

Inspected files:

- [src/main/java/frc/robot/BridgeUiProfileCommands.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiProfileCommands.java)
- [src/main/java/frc/robot/BridgeUiCommandHandler.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiCommandHandler.java)
- [src/main/java/frc/robot/commands/local/RobotLocalCommandRegistry.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandRegistry.java)
- [tools/can_nt/bridge_cli.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_cli.py)
- [tools/can_nt/bridge_ops.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_ops.py)
- [tools/can_nt/bringup_ui.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py)

Observed current behavior:

- robot-local command registry already contains a profile activation command
- CLI and REST-era surfaces still have operator flows and docs that assume activation follows selection or push immediately
- host surfaces do not yet clearly distinguish:
  - selected profile
  - active runtime profile
  - runtime active or inactive
- UI still has opportunities to shortcut robot actions through local assumptions unless explicitly forced through REST for this feature

Conclusion:

- surface alignment is a significant part of this change
- this is not only a `robotInit()` edit

## Structural Mismatches To Resolve

### Mismatch 1: Boot Still Activates Runtime

Current mismatch:

- boot calls activation directly

Target:

- boot selects only

### Mismatch 2: Surface Status Is Too Ambiguous

Current mismatch:

- many status surfaces show only a single “active profile” idea

Target:

- surfaces must expose:
  - selected profile
  - active runtime profile
  - runtime active or inactive

### Mismatch 3: Runtime-Dependent Commands Assume Activation Already Happened

Current mismatch:

- manual actuation, tests, and some runtime commands implicitly assume instantiated devices exist

Target:

- runtime-dependent commands must fail cleanly when runtime is inactive
- no hidden activation is allowed

### Mismatch 4: Command Semantics Around Config Push Are Underspecified

Current mismatch:

- docs and operator habit assume `config push --activate` is the normal path

Target:

- the command contract must explicitly define when selection happens and when activation happens

## Implementation Phases

## Phase 1: Make Boot Selection-Only

### Changes

- remove startup activation call from `RobotV2.robotInit()`
- preserve:
  - config load
  - selected/default profile resolution
  - REST server startup
  - UI/session initialization

### Expected End State

After boot:

- config loaded: yes
- selected profile: yes
- active runtime profile: none
- runtime active: no
- devices instantiated: no

### Files Expected

- [src/main/java/frc/robot/RobotV2.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/RobotV2.java)

## Phase 2: Define And Surface Runtime State Explicitly

### Changes

- standardize robot-visible state queries for:
  - selected profile
  - active runtime profile
  - runtime active boolean
- update reports and status builders to expose all three clearly

### Files Expected

- [src/main/java/frc/robot/BringupUtil.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BringupUtil.java)
- [src/main/java/frc/robot/BridgeUiCommandHandler.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiCommandHandler.java)
- [src/main/java/frc/robot/rest/BringupRestServer.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/rest/BringupRestServer.java)
- any report helpers that still flatten selection and activation into one label

### Expected End State

- operator surfaces can tell whether a profile is merely selected or actually active

## Phase 3: Make Runtime Activation Explicit And Canonical

### Changes

- choose one canonical activation command form
- ensure all surfaces invoke the same activation path
- avoid multiple surface-specific activation implementations

### Locked command surface

CLI must expose:

- `runtime activate`
- `runtime deactivate`

REST must expose:

- `POST /commands` with `name: "runtimeActivate"`
- `POST /commands` with `name: "runtimeDeactivate"`

UI must:

- call the REST interface for activation and deactivation
- not use a separate internal shortcut path for these actions

Shared robot-side semantic action:

- activate selected profile runtime
- deactivate active runtime

### Files Expected

- [src/main/java/frc/robot/commands/local/RobotLocalCommandRegistry.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandRegistry.java)
- [src/main/java/frc/robot/BridgeUiProfileCommands.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiProfileCommands.java)
- [tools/can_nt/bridge_cli.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_cli.py)
- [tools/can_nt/bridge_ops.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_ops.py)
- [tools/can_nt/bringup_ui.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py)

## Phase 4: Guard Runtime-Dependent Commands

### Changes

- audit commands that need live instantiated devices
- add a shared runtime-inactive guard
- return clear failures instead of:
  - silent no-op
  - hidden activation
  - partial allocation side effects

### Commands To Audit First

- manual device duty commands
- group run/bind-driven actuation commands
- test selection/run commands that need live hardware
- report commands that operate on instantiated devices rather than config data

### Files Expected

- [src/main/java/frc/robot/BridgeUiCommandHandler.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiCommandHandler.java)
- [src/main/java/frc/robot/BringupCore.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BringupCore.java)
- [src/main/java/frc/robot/BringupRuntime.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BringupRuntime.java)
- local command groups under `src/main/java/frc/robot/commands/local/`

## Phase 5: Align Config Push Semantics

### Changes

- make `config push` and profile activation behavior explicit in code and docs
- ensure plain push does not instantiate runtime
- define whether `--activate` remains an explicit convenience

### Recommended Steady-State Contract

- `config push <path>`
  - loads config and updates selection only
- `config push <path> --activate <profile>`
  - still allowed as an explicit one-step convenience
  - must be implemented as:
    - push
    - select profile
    - explicit REST/robot-local activation
  - not as hidden side-effect behavior

This contract is locked for implementation.

### Files Expected

- [tools/can_nt/bridge_cli.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_cli.py)
- [tools/can_nt/bridge_ops.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_ops.py)
- [src/main/java/frc/robot/BridgeUiProfileCommands.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiProfileCommands.java)
- docs that currently assume push implies immediate active runtime

## Phase 6: Add Deactivation Contract

### Changes

- define and implement explicit runtime deactivation
- ensure it:
  - stops bringup-owned actuation
  - clears active runtime profile state
  - preserves selected profile

### Locked contract

Add canonical explicit operator actions:

- CLI: `runtime deactivate`
- REST command: `runtimeDeactivate`

This is preferable to relying only on resets and side effects.

### Files Expected

- [src/main/java/frc/robot/BringupUtil.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BringupUtil.java)
- [src/main/java/frc/robot/BringupRuntime.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BringupRuntime.java)
- relevant CLI/REST/UI command surfaces

## Ordered Chunk List

1. Remove `robotInit()` startup activation and preserve selection-only boot.
2. Add or standardize runtime-state reporting fields and helpers.
3. Wire one canonical explicit activation command across robot, CLI, REST, and UI.
4. Guard runtime-dependent commands against inactive runtime.
5. Split `config push` semantics cleanly from activation semantics.
6. Add explicit runtime deactivation through CLI and REST and make UI use REST for it.
7. Update docs, grammar, help text, and user flows.
8. Run connected validation across CLI/UI/REST.

## Validation Plan

### Java

- `.\gradlew.bat test`

### Python

- relevant CLI/UI unit tests after command-surface changes

### Connected Robot Validation

Minimum required:

1. Boot robot and confirm:
   - selected profile is shown
   - runtime is inactive
   - no bringup devices are instantiated yet
2. Change selected profile twice before activation.
3. Activate runtime explicitly and confirm only then:
   - devices instantiate
   - aliases/groups refresh
   - runtime commands work
4. Change selected profile while runtime is active and confirm:
   - active runtime profile remains unchanged
   - no rebuild occurs
5. Deactivate runtime and confirm:
   - actuation stops
   - selected profile remains
   - runtime returns to inactive state

## Risks

- some current code paths may rely on active runtime being present during or immediately after boot
- some reports may currently derive “active profile” text from `getActiveCanProfileLabel()` and need disambiguation
- connected test and actuation flows may need careful soft-failure handling to avoid regression in operator experience

## Definition Of Done

- robot no longer activates bringup runtime at boot
- selected profile and active runtime profile are distinct and visible
- runtime activation is explicit across all operator surfaces
- CLI activation/deactivation commands exist
- REST activation/deactivation commands exist
- UI uses the REST activation/deactivation path instead of a separate shortcut
- runtime-dependent commands fail clearly while runtime is inactive
- `config push` no longer relies on hidden auto-activation semantics
- docs, grammar, and help text match the new contract
