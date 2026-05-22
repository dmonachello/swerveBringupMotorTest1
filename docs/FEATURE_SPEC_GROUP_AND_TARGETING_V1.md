SPEC_STATUS: IMPLEMENTED

# Group and Targeting Spec (V1 Final)

## 1. Goal

Provide a simple, consistent system to:

- organize devices into groups
- operate on devices or groups
- support fast bringup workflows
- allow both ad hoc and persistent use

The system must be:

- explicit
- predictable
- consistent across all interfaces
- safe from accidental mutation

## 2. Global Namespace

All named entities share a single global namespace:

- device names
- group names
- reserved names

Rules:

- names must be globally unique
- no collisions allowed
- resolution is exact match only (case-insensitive)
- no fallback or guessing

## 3. Groups

A group is a named set of device names.

## 4. Group Types

### 4.1 Active Group (reserved)

Name: `active`

Properties:

- always exists
- starts empty at config save/commit boundary
- not persisted
- mutable
- used for fast workflows
- default target when no CLI context is active

### 4.2 Named Groups (user-defined)

Properties:

- created explicitly
- persisted in config
- mutable
- used by saved tests

### 4.3 Internal Groups

Not part of V1.

## 5. Group Membership

- membership is a set of device names
- no duplicates allowed

Behavior:

- adding an existing device warns and no-ops
- removing a non-member warns and no-ops

Devices may belong to multiple groups.

## 6. Copy Model (No Aliasing)

Groups never reference other groups.

All reuse is via copying.

Examples:

`copy group intake active`

`copy group active intake_v2`

Rules:

- copying into `active` always overwrites, no prompt
- copying into existing named group prompts y/n in interactive CLI
- copying into existing named group fails in non-interactive mode
- copying into new named group creates it
- copying group to itself errors

## 7. CLI Context Model

CLI is context-based.

### 7.1 Enter group context

`group <name>`

Example:

`group intake`

`(config-group-intake)#`

### 7.2 Context precedence

- current group context wins
- `active` used only when no context is active

### 7.3 Exit context

`exit`

`end`

## 8. CLI Commands

### 8.1 Show

`show groups`

`show group <name>`

Output must include:

- all named groups
- `active`

Example:

Groups:

`active [temp] (3 devices)`

`intake (2 devices)`

`shooter (0 devices)`

### 8.2 Create group

`group create <name>`

Rules:

- fails if name exists
- cannot be `active`
- enters group context on success

### 8.3 Delete group

`group delete <name>`

Rules:

- cannot delete `active`
- fails if referenced by tests

### 8.4 Rename group

`group rename <old> <new>`

Rules:

- cannot rename `active`
- must update all references
- must validate full config
- must commit atomically

### 8.5 Add device

`add device <device>`

`add device <device> group <name>`

Target:

- context group if in context
- otherwise `active`

### 8.6 Remove device

`remove device <device>`

`remove device <device> group <name>`

### 8.7 Clear group

`group clear`

`group clear <name>`

Target:

- context group if in context
- otherwise `active`

Rules:

- always allowed
- user responsible

### 8.8 Copy group

`copy group <source> <dest>`

### 8.9 Convenience Commands

#### 8.9.1 add all

`add all`

`add all group <name>`

Behavior:

- adds all devices to target group

Target selection:

- group context: current group
- no context: `active`
- explicit override allowed

Membership semantics:

- union operation (no replacement)

Duplicates:

- warn and no-op

Non-destructive:

- does not remove existing members

#### 8.9.2 add next

`add next`

`add next group <name>`

Behavior:

- adds one selected/next device

Target:

- same rules as `add all`

Rules:

- already present warns
- no device available errors
- device order must be deterministic and cyclic

## 9. Targeting Model

A test defines:

`target: "<name>"`

Where `<name>` resolves to:

- device
- group
- `active`

## 10. Execution Behavior

At runtime:

- resolve target
- expand to device list
- execute

## 11. Empty Target Behavior

If group resolves to empty:

`Target: intake (group)`

`Resolved devices: []`

`ERR target group is empty`

Behavior:

- print message
- fail test
- no execution

## 12. Runtime Visibility

Execution must show:

`Target: intake (group)`

`Resolved devices:`

- `device1`
- `device2`

## 13. Rename Semantics

Applies to groups and devices.

Rules:

- update all references:
  - group membership
  - test targets
- validate config
- commit atomically

## 14. Device Delete

`device delete <name>`

Rules:

- fails if referenced by:
  - any group
  - any test

## 15. Persistence Model

Persisted:

- named groups
- tests

Not persisted:

- `active`

## 16. Config Model

- host local config is authoritative
- CLI and TUI modify in-memory config immediately
- persistence happens via commit/save
- `active` resets to empty at save/commit
- robot receives updates only on push
- cross-surface conflicts use last write wins

## 17. Surfaces

CLI:

- full control

TUI:

- interactive group editing
- device selection

Topology Editor:

- display and modify groups

Bridge UI:

- display groups only

## 18. Safety Rules

- no silent mutation
- no implicit fallback
- no aliasing
- no duplicate membership
- no partial commits

## 19. Error Behavior

Examples:

`ERR group "active" cannot be deleted`

`ERR group "intake" referenced by test intake_test`

`ERR device "motor1" not found`

`ERR name "intake" already exists`

`ERR source and destination are the same`

## Appendix A - Example Workflow

### A.1 Build group

`active` starts empty

`add next`

`add next`

### A.2 Save group

`copy group active intake`

### A.3 Modify safely

`copy group intake active`

`add device device3`

`copy group active intake_v2`

### A.4 Edit directly

`group intake`

`add device device4`

### A.5 Run test

`target: "intake"`

`TEST RUN intake_test`

### A.6 Run using active

`target: "active"`

### A.7 Empty group failure

`group clear intake`

`TEST RUN intake_test`

Output:

`ERR target group is empty`

