# Bridge CLI Feature Specification

## Purpose

Add an interactive Cisco-style CLI mode to the bridge app.

This CLI is not a separate tool. It is a second operator surface inside the bridge app, alongside the Windows UI.

The CLI and GUI must:
- share the same core command/send/receive logic
- share the same runtime state
- not duplicate business logic

## Goals

Provide a live operator console with:
- contextual prompts
- hierarchical modes
- command parsing
- shared bridge command execution
- shared response parsing
- scriptable batch operation
- no prompts in batch mode

## Architecture

### Required layers

- Bridge Core / Session Layer
  - connect / disconnect
  - send command
  - receive ACK / OUT
  - stream output
  - maintain runtime state snapshot

- Shared Operations Layer
  - group operations
  - device membership operations
  - binding operations
  - selected-device operations
  - show/query operations
  - merge/import/export operations

- GUI Front End
  - must call shared operations

- CLI Front End
  - must call same shared operations

- CLI may exist in a separate module, but must remain a thin front end over shared core logic

## CLI Module Separation

The CLI must be implemented as a separate module from the main bridge code and invoked from the existing bridge application.

### Structure

- The CLI module is responsible for:
  - prompt loop
  - mode management (exec/config/group)
  - command parsing and dispatch
  - batch/script execution handling

- The CLI module must invoke the shared operations layer for all functionality.

- The CLI module must use the same bridge session and response-handling logic as the GUI.

### Constraints

The CLI module must not reimplement bridge logic.

Do not:
- duplicate command send/receive logic
- duplicate response parsing
- duplicate runtime state management
- create a parallel bridge implementation inside the CLI module

The CLI is a front end only, not a separate system.

### Constraint

Do not:
- duplicate logic in CLI
- create a separate command path

## CLI Style

Use a Cisco-like CLI:
- hierarchical modes
- contextual prompts
- `show ...` for inspection
- `configure terminal` for config mode
- `group <name>` to enter/create group mode
- `no ...` for removal
- `exit` / `end` for navigation
- Windows EOF: Ctrl+Z then Enter behaves like `exit` (Ctrl+D on POSIX shells).

Do not implement:
- privilege levels
- fuzzy abbreviations

## Modes

### Exec Mode

Prompt:
`bridge>`

Purpose:
- inspection
- connection status
- enter config mode

### Config Mode

Prompt:
`bridge(config)#`

Purpose:
- structural edits
- group entry/creation
- selected-device config
- merge/import/export

### Group Config Mode

Prompt:
`bridge(config-group-<name>)#`

Purpose:
- edit one group
- membership
- bindings
- enable/disable
- run tests

### Batch Mode

Entered via:
`bridge.py --batch`

or script execution.

Rules:
- no prompts
- deterministic behavior
- uses conflict policy

## Batch Conflict Policy

Supported:
- `error` (default)
- `move`

Behavior:

- error
  - warn
  - do not perform action

- move
  - warn
  - perform action automatically

No per-command `--force`. Batch mode replaces it.

## Interactive Prompting

In interactive mode, prompt user for:
- device move between groups
- deleting groups
- clearing groups

Rules:
- default = no
- no partial state changes
- moves must be atomic

No prompting allowed in batch mode.

## Commands

### Common Commands

- `exit`
- `end`
- `help`
- `ping`
- `quit`

### Exec Mode Commands

- `show status`
- `show groups`
- `show group <name>`
- `show devices`
- `show device <name>`
- `show device registry <name>`
- `show bindings`
- `show selected-device`
- `show runtime-state`
- `show config local-raw`
- `show config dirty`
- `show profiles`
- `show profile`
- `show tests`
- `show test <name>`
- `configure terminal`
- `connect`
- `disconnect`

### Config Mode Commands

- `group <name>`
- `no group <name>`
- `profile <name>`
- `selected-device <device>`
- `selected-mode on`
- `selected-mode off`
- `merge config <bringup_system.json>`
- `import config <bringup_system.json>`
- `export runtime-groups <bridgeConfig.json>`
- `save config <bridgeConfig.json>`
- `save local-config <path>`
- `save profiles <path>`
- `save unified-config <path>`
- `rename device <old> <new>`
- `device <name>`
- `device <name> set <field> <value>`
- `validate config [path]`
- `bindings show [controllers|bindings|axes] [--json]`
- `bindings controller add <name> <type> <port>`
- `bindings controller set <name> <field> <value>`
- `bindings controller rename <old> <new>`
- `bindings no controller <name>`
- `bindings binding add <command> <controller> <input> <id> <mode>`
- `bindings binding set <index> <field> <value>`
- `bindings binding delete <index>`
- `bindings axis add <command> <controller> <id> invert <on|off> deadband <value>`
- `bindings axis set <index> <field> <value>`
- `bindings axis delete <index>`
- `bindings load <path>`
- `bindings save <path>`
- `bindings validate [path]`
- `can-mappings show [manufacturers|device-types] [--json]`
- `can-mappings manufacturer set <id> <name>`
- `can-mappings manufacturer delete <id>`
- `can-mappings device-type set <id> <name>`
- `can-mappings device-type delete <id>`
- `can-mappings load <path>`
- `can-mappings save <path>`
- `can-mappings validate [path]`
- `tests templates`
- `tests load <path>`
- `tests load template <name>`
- `tests save`
- `write tests <path>`
- `test set <name>`
- `test create <name>`
- `test delete <name>`
- `test <name>`

### Group Config Mode Commands

- `show`
- `show members`
- `show binding`
- `add device <device>`
- `no device <device>`
- `member <device> enable`
- `member <device> disable`
- `member <device> toggle`
- `bind <input> analog`
- `bind <input> hold <value>`
- `bind <input> toggle <value>`
- `bind <input> jog-forward <value>`
- `bind <input> jog-reverse <value>`
- `no bind`
- `enable`
- `disable`
- `run test`
- `run test <name>`

### Output Notes

- `show group` text output includes member names and bindings.
- `show devices` (local) lists the full profile-derived device inventory, not only group members.
- `show device` text output includes label-based metadata from bringup_system.json.
- `show device registry` returns the full device registry entry (local only).
- CLI auto-imports `data/bringup_system.json` on startup when present (replaces groups).
- merge config is only allowed when the incoming profiles hash matches the loaded profiles; otherwise use import config.

## Control Identifiers

Examples:
- `controller0.leftY`
- `controller0.rightY`
- `controller1.leftY`
- `controller1.rightY`
- `controller0.A`
- `controller0.B`
- `controller0.X`
- `controller0.Y`
- `controller0.LB`
- `controller0.RB`
- `controller1.A`
- `controller1.B`
- `controller1.X`
- `controller1.Y`
- `controller1.LB`
- `controller1.RB`
- `ui.slider1`
- `ui.slider2`
- `ui.Button1`
- `ui.Button2`

## Binding Rules

### Behaviors

- `analog`
- `hold`
- `toggle`
- `jog-forward`
- `jog-reverse`

### Rules

- analog
  - uses live value
  - no fixed value

- button-based
  - must specify value

### Semantics

- hold
  - output = value while pressed, else 0

- toggle
  - toggles value on/off

- jog-forward
  - +value while pressed

- jog-reverse
  - -value while pressed

Value belongs to the binding, not device or group.

## Device Ownership Rule

A device belongs to one group only.

When adding:

### Interactive mode
- warn
- prompt y/n

### Batch mode
- error -> fail
- move -> auto move

Never allow multiple group membership.

## Per-Member Enable

Commands:
- `member <device> enable`
- `member <device> disable`
- `member <device> toggle`

Effects:
- controls participation
- does not change membership

## Selected Device Mode

Commands:
- `selected-device <device>`
- `selected-mode on`
- `selected-mode off`

Rules:
- overrides group control for that device
- group output suppressed for selected device

## Response Handling

CLI must use same logic as GUI.

Display:
- `CMD`
- `ACK`
- `OUT`
- `CONSOLE`

No separate protocol.

## Help System

Support:
- `help`
- `help <command>`

Later:
- optional `?`

## Error Handling

Errors must be specific.

Good:
- `unknown device FL_DRIEV, did you mean FL_DRIVE?`
- `hold binding requires value`
- `device already in group swerve_drive`

Bad:
- `syntax error`

## Batch / Script Support

### Execution

`bridge.py --batch --script setup.txt`

### Rules
- no prompts
- deterministic behavior
- uses conflict policy

### Example Script

```text
configure terminal
group swerve_drive
add device FL_DRIVE
add device FR_DRIVE
bind controller0.leftY analog
enable
end

Structured Output

Support machine-readable output: --json

For:

show status

show groups

show group <name>

show devices

show device <name>

show bindings

show selected-device

show runtime-state


Do not require parsing human text.

Non-Goals

Do not implement:

separate CLI application

privilege system

fuzzy parsing

DSL / scripting language

duplicated logic

per-command --force flags


Implementation Plan

1. Core Layer

session

send/receive

state snapshot


2. Operations Layer

all domain logic


3. CLI Shell

prompt loop

mode tracking

command dispatch


4. GUI Integration

reuse operations


Prompts

bridge>

bridge(config)#

bridge(config-group-swerve_drive)#


Example Session

bridge> show groups
bridge> configure terminal
bridge(config)# group swerve_drive
bridge(config-group-swerve_drive)# add device FL_DRIVE
bridge(config-group-swerve_drive)# member FR_DRIVE disable
bridge(config-group-swerve_drive)# bind controller0.leftY analog
bridge(config-group-swerve_drive)# enable
bridge(config-group-swerve_drive)# exit
bridge(config)# selected-device FL_DRIVE
bridge(config)# selected-mode on
bridge(config)# end
bridge> show group swerve_drive

Summary

Implement a Cisco-style CLI inside the bridge app that:

shares all logic with the GUI

supports interactive and batch modes

avoids prompts in batch mode

uses structured output for automation

remains simple, predictable, and operator-friendly
