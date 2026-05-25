# Robot Base Functionality

## Purpose

Describe the low-level robot-side functionality that remains implemented in code after configuration-driven cleanup.

This document is about the roboRIO runtime itself, not about team-specific devices, profiles, tests, groups, or controller mappings.

## Scope

This layer is the execution engine.

It owns:

- startup and safe-mode behavior
- device lifecycle and runtime services
- command execution infrastructure
- report generation infrastructure
- DSL test execution infrastructure
- hardware-status and diagnostic collection
- controller signal sampling

It does **not** own robot configuration.

These must come from JSON files:

- device inventory
- profiles
- topology
- groups
- tests
- controller bindings
- controller definitions

## Config Structure Assumption

Purpose: state the config model the robot runtime consumes.

- `bringup_system.json` may contain multiple profiles.
- `bringup_system.json` is the system config file, and only one system config file is loaded at a time.
- `devices[]` is the shared device inventory for that loaded system config.
- `profiles.<name>.devices[]` selects which device labels belong to each profile.

So the robot runtime distinguishes:

- a device that is defined in config
- a device that is included in the active profile
- a device that is instantiated at runtime

Those are separate states.

## What Remains In Code

### Safe Startup Behavior

Purpose: keep the robot process alive when config is missing or invalid.

Behavior:

- if `bringup_system.json` fails to load, the robot enters an empty safe mode
- no fallback robot/demo device inventory is synthesized
- no fallback profiles, groups, tests, or bindings are created
- singleton CAN IDs remain disabled

This is failure handling, not alternate configuration.

### Device Runtime

Purpose: create, own, and operate runtime device instances.

Behavior:

- instantiate devices that the active JSON profile requests
- maintain lifecycle state
- expose snapshots and report data
- clear faults
- apply commanded outputs

Important distinction:

- the runtime does not instantiate every device defined in `devices[]`
- it instantiates the devices selected by the active profile

The runtime engine is hardcoded.

The list of devices it creates is JSON-driven.

### Report Runner

Purpose: produce readable output without blowing the 20 ms control loop budget.

Behavior:

- queue report text
- print incrementally across cycles
- throttle batch size and chunk size

All large status/report output must use this path.

### Status And Hardware Commands

Purpose: expose low-level diagnostic/report capabilities.

Examples:

- state
- health
- CAN diagnostics
- NetworkTables diagnostics
- inputs
- bindings
- tests info
- tests overview
- CANcoder report
- dump report
- clear faults
- clear stop latch

The command implementations are in code.

Which button, CLI command, UI action, or automation path invokes them is configuration or surface behavior.

### DSL Test Engine

Purpose: run explicit scripted bringup tests.

Behavior:

- load tests from JSON-backed configuration
- validate test structure
- resolve device/signal references
- execute selected or enabled tests
- manage stop/abort/latch behavior
- expose test status/reporting

The engine is hardcoded.

The actual tests are configuration.

### Group Binding Runtime

Purpose: apply configured group bindings to configured devices.

Behavior:

- evaluate configured binding inputs against a sampled controller snapshot
- apply outputs to enabled group members
- honor selected-device override state
- support analog, hold, toggle, and jog semantics

The binding evaluator is hardcoded.

The groups and bindings it evaluates are configuration.

### Controller Signal Sampling

Purpose: sample raw Xbox controller signals for bindings, groups, and DSL.

Behavior:

- instantiate controller objects that JSON defines
- sample raw button, trigger, stick, and D-pad values
- expose raw controller signals to DSL controller devices
- expose sampled values to the group-binding engine

Important:

- missing or invalid controller/binding JSON now results in **no configured controllers/bindings**
- the robot no longer synthesizes default `controller0..controller5`
- the robot no longer synthesizes default Xbox button bindings
- manual actuation no longer falls back to implicit raw-stick `leftDrive/rightDrive`

## What Must Come From JSON

These are no longer allowed as hidden code defaults:

- fallback robot profiles
- fallback CAN IDs
- fallback demo-board inventories
- fallback controller bindings
- fallback controller inventories
- vendor-wide manual motor commands

Operational examples that must be defined in JSON:

- `leftDrive` / `rightDrive` axis bindings
- status/report button mappings
- controller list such as `controller0` and `controller1`
- group membership such as `krakens` and `neos`
- staged/manual test definitions

## Surface Contract

The robot runtime provides capabilities to higher-level surfaces:

- UI
- CLI
- bindings
- tests

Those surfaces choose how to invoke the capabilities.

The robot runtime should not silently invent missing operator configuration for them.

## Tradeoffs

- Empty safe mode is stricter than old fallback behavior, but it is honest.
- Missing config now disables control paths instead of guessing intent.
- This pushes more responsibility onto JSON authoring, which is the right place for team-specific behavior.

## Future Extensions

- Add explicit robot-side status reporting for `config-valid`, `config-partial`, and `config-empty-safe-mode`.
- Add finer-grained salvage diagnostics for robot-side bindings/controllers, similar to the Python CLI salvage model.
- Add a generated operator-capability summary that reports which runtime capabilities are available under the currently loaded JSON files.
