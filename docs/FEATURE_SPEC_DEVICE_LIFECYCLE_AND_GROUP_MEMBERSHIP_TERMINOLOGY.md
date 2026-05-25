SPEC_STATUS: IMPLEMENTED

# Feature Spec: Device Lifecycle and Group Membership Terminology

## Implementation Status

Purpose: Record what shipped in the current CLI and docs.

- Canonical runtime lifecycle commands are now:
  - `instantiate next motor`
  - `instantiate all devices`
- Canonical group membership commands are now:
  - `member assign <device>`
  - `member remove <device>`
  - `member enable <label>`
  - `member disable <label>`
  - `member toggle <label>`
  - `group member assign <group> <label>`
  - `group member assign all <group>`
  - `group member assign next <group>`
- `export cli-script`, help text, grammar artifacts, and maintained local regressions now emit and test the canonical forms.

SID_COMMENT: Internal helper and transport names are still mixed in older subsystems where renaming would be disruptive. The operator-facing command surface, help text, generated scripts, and current docs now use the canonical terminology, and removed aliases are no longer accepted.

## Purpose

Define one consistent vocabulary for:

- robot-side device instantiation
- logical group membership
- controller/input binding

This spec exists to remove ambiguity caused by overloaded verbs such as `add`, and to carry the distinction through:

- code names
- CLI syntax
- UI command names
- documentation
- help text

## Problem Statement

The current system uses similar language for two different actions:

- creating or activating a live robot-side device instance
- adding a configured device label to a logical group

Those actions are related in operator workflows, but they are not the same operation.

At present, the distinction is not consistently visible in:

- Java runtime method names
- bridge/UI command names
- CLI command syntax
- user documentation
- feature specs

This makes code review, operator training, and future implementation work harder than necessary.

## Goals

- Reserve one verb family for runtime lifecycle actions.
- Reserve one verb family for logical group membership actions.
- Reserve one verb family for controller/input hookups.
- Make the distinction explicit in all user-facing CLI help.
- Make the distinction explicit in implementation-facing code names.
- Keep behavior stable while terminology is corrected.

## Non-Goals

- Redesign the underlying bringup runtime.
- Change NetworkTables contracts.
- Change the persisted JSON schema unless explicitly required by implementation.
- Merge the runtime instantiation subsystem with the group membership subsystem.
- Preserve implementation stability while renaming operator-facing command language.

## Canonical Vocabulary

Purpose: Define the required words for each concept.

### 0. System Config

Use `system config` when you mean the whole loaded `bringup_system.json` document as a unit.

Meaning:

- the entire configuration document
- shared device inventory
- one or more profiles
- related bridge/test/topology data stored in that same file

Recommended related terms:

- `config file`: a specific file on disk
- `loaded system config`: the one config file currently loaded by the system

Avoid when precision matters:

- using bare `config` when you specifically mean the whole file
- using `profile` when you really mean the whole file

### 1. Configured Device

Meaning:

- a device label and definition exists in config
- the device exists in the registry/inventory

Plain-language meaning:

- the loaded system config knows this device exists
- this does not yet say which robot profile uses it

Allowed examples:

- configured device
- device registry entry
- device definition

Non-meaning:

- does not imply runtime instantiation
- does not imply inclusion in every profile in the same system config
- does not imply group membership
- does not imply motion authority

## Config Structure Model

Purpose: Make the system-config/profile relationship explicit.

One system config may contain:

- one shared device inventory
- multiple named profiles

The device inventory defines the available devices once.

Each profile then selects which of those devices belong to that profile.

So the relationship is:

- system config defines devices
- profiles inside that system config include subsets of those devices

Example:

- `devices[]` may define `controller0`, `controller1`, `pdh`, and four drive motors
- profile `robot_2026_swerve` may include all of them
- profile `bench_test` may include only `controller0`, `pdh`, and one motor

In that case:

- `controller1` is still a configured device
- but `controller1` is not in profile `bench_test`

This distinction is required throughout the rest of this spec.

### 2. Device Instantiation

Use `instantiate` for robot-side device lifecycle actions.

Meaning:

- create or activate the live robot-side device object
- make the device available for local control/readout in the runtime

Allowed examples:

- instantiate next motor
- instantiate all devices
- instantiated device
- device instantiation state

Disallowed as the primary term for this concept:

- add motor
- add device
- next device

### 3. Group Membership

Use `assign`, `remove`, `member`, and `membership` for group membership actions.

Meaning:

- include or exclude a configured device label from a logical group
- change targeting/binding participation
- do not imply object creation

Allowed examples:

- assign device to group
- remove device from group
- group member
- group membership

Disallowed as the primary term for this concept:

- add device
- add next motor
- create device

### 4. Input Binding

Use `bind` and `unbind` only for controller/input hookup semantics.

Meaning:

- connect an input source to a group output behavior or authored test input behavior
- do not imply runtime object creation
- do not imply group membership edits

Allowed examples:

- bind controller0.leftY analog
- unbind group
- test input binding

### 5. Selected Device

Meaning:

- a single explicit device chosen as the selected target in runtime/profile state

Non-meaning:

- not the same as group membership
- not the same as instantiation

### 6. Selected Mode

Meaning:

- a runtime flag that enables selected-device targeting behavior

Non-meaning:

- not a group
- not a lifecycle state

### 7. Motion Authority

Meaning:

- the right for some runtime path to command non-zero output

Important:

- instantiation does not automatically imply motion authority
- group membership does not automatically imply motion authority
- binding presence does not automatically imply motion authority

## State Model

Purpose: Define the distinct states that may exist at the same time.

A configured device may be:

- configured only
- instantiated but not assigned to any group
- assigned to a group but not instantiated
- both instantiated and assigned to one or more groups
- selected but not grouped
- grouped and enabled but not currently commanded

Definitions:

- configured device
  A device label and definition exists in config.
- instantiated device
  The robot runtime has created the live device object.
- grouped device
  The device label is present in one or more logical groups.
- enabled group member
  The device is a group member whose per-member enabled flag is `true`.
- bound group
  A group has one or more input bindings attached.
- commanded device
  The current runtime path is actively applying output/action to the device.

Implementation and documentation must never imply that these states are equivalent.

## Lifecycle Model

Purpose: Show the stages without collapsing them into one term.

### Stage 1: Defined

The device exists in the registry.

Plain-language meaning:

- the loaded system config defines this device in the shared device inventory
- the system knows what the device is
- this still does not say whether the current profile uses it

### Stage 2: In Profile

The device appears in the active profile device list.

Plain-language meaning:

- the currently selected profile chooses to use this device
- this profile-specific device list is a subset of the shared device inventory
- a device can be defined in the loaded system config but absent from the current profile

### Stage 3: Instantiated

The robot runtime has created the live object/service for the device.

### Stage 4: Targeted

The device is currently addressed by some higher-level selection model.

Examples:

- member of a named group
- member of `active`
- selected device while selected mode is on

### Stage 5: Commanded

A currently valid runtime path is applying output/action to the device.

Important:

These stages are not synonyms.

## Architecture Boundary

Purpose: State the system boundary that the naming must preserve.

### Runtime Instantiation Subsystem

Responsibilities:

- choose eligible device instances in runtime order
- create/activate robot-side device objects
- report whether devices are live and ready

Examples in current code:

- `BringupCore`
- `ManufacturerGroup`
- `DeviceTypeBucket`

### Group Membership Subsystem

Responsibilities:

- maintain logical group membership by device label
- maintain per-member enable/disable state
- maintain group bindings
- fan controller-driven output to grouped devices

Examples in current code:

- `BridgeGroupManager`
- bridge group UI/CLI command handlers

### Rule

These two subsystems may coordinate, but they must not be named as if they are the same subsystem.

## Required Naming Rules

Purpose: Define mandatory naming rules for implementation work.

### Java and Python Code

Runtime lifecycle methods must use `instantiate`, `instantiated`, or `activation` terminology.

Examples:

- `instantiateNextMotorCommand`
- `instantiateAllDevicesCommand`
- `isDeviceInstantiated`

Group membership methods must use `assign`, `remove`, `member`, or `membership` terminology.

Examples:

- `assignDeviceToGroup`
- `removeDeviceFromGroup`
- `syncGroupMembership`
- `groupMembers`

Binding methods must use `bind`, `unbind`, or `binding` terminology.

Examples:

- `groupBind`
- `groupUnbind`
- `inputBindings`

### Comments and Documentation Blocks

Every documentation block for touched methods/classes must explicitly state whether the code is about:

- device instantiation
- group membership
- input binding

Do not describe group membership edits as device creation.

Do not describe device instantiation as group assignment.

## CLI Syntax Direction

Purpose: Define the user-facing command language that matches the distinctions.

### 1. Runtime Instantiation Commands

New canonical forms:

```text
instantiate next motor
instantiate all devices
```

Optional shorter aliases may exist, but `instantiate ...` is the canonical documentation form.

These commands mean:

- operate on robot-side runtime lifecycle
- do not edit group membership

### 2. Group Membership Commands

New canonical forms in group context:

```text
member assign <device>
member remove <device>
member enable <label>
member disable <label>
member toggle <label>
```

New canonical forms with explicit group target:

```text
group member assign <group> <label>
group member remove <group> <device>
group member enable <group> <device>
group member disable <group> <device>
group member toggle <group> <device>
```

The implementation may also support a form with named arguments or explicit keywords if that fits the parser better, but the canonical help/manual/spec wording must use `member ...`.

These commands mean:

- edit logical group membership only
- do not instantiate hardware

### 3. Group Convenience Commands

Canonical forms:

```text
member assign all
member assign next
group member assign all <group>
group member assign next <group>
```

Meaning:

- choose device labels by configured order and assign them to a target group
- do not instantiate hardware

If implementation prefers a different token order for grammar reasons, it must still preserve the words `member` and `assign`.

### 4. Binding Commands

Canonical forms remain in the `bind` family:

```text
bind <input> analog
bind <input> hold <value>
bind <input> toggle <value>
bind <input> jog-forward <value>
bind <input> jog-reverse <value>
no bind
```

These commands mean:

- attach or clear controller/input behavior for the current target group
- do not instantiate hardware
- do not change group membership

## Migration

Purpose: Define the completed cutover.

Legacy alias command forms have been removed.

Removed forms:

- `add next`
- `add all`
- `add device <device>`
- `remove device <device>`
- `no device <device>`
- `member <device> enable`
- `member <device> disable`
- `member <device> toggle`

Current behavior:

- help text and manuals present only canonical commands
- grammar and script lint reject removed forms
- exported CLI scripts use canonical commands only

## Documentation Requirements

Purpose: Make the distinctions visible everywhere.

The following docs must be updated in the implementation change:

- CLI spec
- CLI reference manual
- CLI user manual
- group and targeting spec
- testing quick guide
- DSL user/spec docs where they discuss bindings
- any architecture doc that mentions `add` behavior ambiguously

Each relevant document must contain a short terminology section or equivalent wording that distinguishes:

- instantiation
- group membership
- binding

Examples must use canonical commands unless the example is specifically demonstrating backward compatibility.

## Code Change Requirements

Purpose: Define minimum implementation expectations.

An implementation of this spec must include:

- code renames where public/internal names are misleading
- updated doc comments for touched classes and methods
- updated CLI parser/help text
- updated UI/bridge command names where practical
- removal of old CLI forms from help, grammar, and exported scripts

Where a rename would be too disruptive for one pass, an adapter or wrapper name may be introduced first, but the operator-facing and newly-written code paths must use canonical terminology.

## Parser and Generated Artifact Requirements

Purpose: Keep command syntax and generated outputs aligned.

If CLI syntax changes are implemented:

- update `tools/can_nt/bridge_cli_ebnf.txt`
- update parser/help/generated grammar artifacts
- update regression fixtures and expected outputs
- update any generated command/status artifacts required by policy

Do not ship syntax changes with stale grammar or stale help text.

## Regression Requirements

Purpose: Keep the transition safe.

Implementation work for this spec must include regression coverage for:

- canonical runtime instantiation commands
- canonical group membership commands
- canonical binding commands
- rejection of removed alias forms
- help text and error disambiguation

Minimum expectations:

- group targeting regression updates
- CLI parser/help regression updates
- any Java-side command handling tests touched by rename work

## Open Design Constraints

Purpose: Preserve current system behavior while terminology is improved.

- Group membership and device instantiation remain separate subsystems.
- A grouped device is not required to be instantiated.
- An instantiated device is not required to be grouped.
- Bindings may target groups regardless of how device instantiation is managed.
- The DSL remains a declarative test surface and is not required to absorb all runtime workflows.

## Acceptance Criteria

This spec is satisfied when:

- code names consistently distinguish instantiation from membership
- CLI help and manuals consistently distinguish instantiation from membership
- canonical CLI syntax uses different verb families for the two concepts
- removed legacy aliases no longer parse
- regressions cover both canonical and compatibility forms
- no behavior regression is introduced solely from terminology cleanup

## Example Before/After

Purpose: Show the intended user-facing distinction.

Ambiguous old wording:

```text
add next
add device "FALCON 9"
```

Canonical clarified wording:

```text
instantiate next motor
member assign "FALCON 9"
member assign next
bind controller0.leftY analog
```

Those commands now read as three separate concepts:

- instantiate hardware
- assign group membership
- bind controller input
