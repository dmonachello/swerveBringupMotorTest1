# CLI Functional Areas User Guide

Purpose: Explain the Bridge CLI by operator job, not just by command list.

## Overview

The Bridge CLI serves several different jobs:

- inspect robot runtime state
- edit host-side configuration
- manage profiles, groups, and devices
- define input bindings
- author and run tests
- inspect diagnostics and visibility
- manage topology and CAN metadata

The same CLI can talk to two different contexts:

- Host context:
  local files and in-memory working state on the PC
- Robot context:
  live runtime state on the roboRIO over TCP

Rule:

- host-only commands do not change robot state
- robot state changes only through explicit robot commands

Examples:

- Host-only:
  `configure terminal`, `save ...`, `validate ...`, `bindings ...`
- Robot-facing:
  `connect`, `tests select`, `tests toggle`, `tests run`, `profiles activate`

## How To Read The CLI

Purpose: Give a simple mental model before diving into commands.

Think of the CLI as nine functional areas:

1. Session and operator surface
2. Robot runtime control
3. Host config lifecycle
4. Profiles, groups, and devices
5. Bindings and operator input mapping
6. Test authoring and test execution
7. Diagnostics and visibility
8. Topology authoring
9. CAN mappings and passive CAN diagnostics

The rest of this guide follows that structure.

## 1. Session And Operator Surface

Purpose: Start, stop, and navigate the CLI itself.

These commands manage the operator session, not robot behavior:

- `help`
- `help <topic>`
- `?`
- `ping`
- `tiu on`
- `tiu off`
- `exit`
- `end`
- `quit`

What these are for:

- `help` and `?`:
  discover syntax and valid next arguments
- `tiu on|off`:
  switch the terminal into or out of the TIU dashboard mode
- `exit`:
  leave the current submode
- `end`:
  return to exec mode

Example:

```text
help bindings
bindings show ?
tiu on
end
```

## 2. Robot Runtime Control

Purpose: Command the roboRIO bringup harness and inspect live robot state.

This area is about the live robot, not local file editing.

Main commands:

- `connect`
- `disconnect`
- `profiles activate <name>`
- `tests select <name>`
- `tests toggle`
- `tests run`
- `tests run-all`
- `run test [<name>]`

What these do:

- `connect`:
  open the TCP session to the robot
- `profiles activate <name>`:
  switch the robot runtime to a specific profile
- `tests select <name>`:
  choose the currently selected robot-side scripted test
- `tests toggle`:
  enable or disable the currently selected robot test
- `tests run`:
  run the currently selected robot test once
- `tests run-all`:
  run all enabled robot tests
- `run test [<name>]`:
  run a group/default test path directly on the robot

Important distinction:

- `tests toggle` affects robot runtime test enable state
- it does not edit host-side test files

Typical workflow:

```text
connect
show status robot
profiles activate robot_2026_swerve
tests select "Right Drive Test"
tests toggle
tests run
```

## 3. Host Config Lifecycle

Purpose: Control what is loaded, dirty, saved, validated, reverted, and pushed.

This area manages your local working set.

Main commands:

- `configure terminal`
- `merge config <path>`
- `import config <path>`
- `load sources`
- `save all [--prompt]`
- `save config <path>`
- `save bridge-config <path>`
- `save runtime-groups <path>`
- `save profiles [<path>]`
- `save sources`
- `revert`
- `validate config [path] [--all]`
- `validate profiles [robot|local] [--active]`
- `validate tests [--active-set]`
- `validate bindings [path]`
- `validate can-mappings [path]`
- `recover list|last-good|from <tag>`
- `config push <path> [--activate <name>]`
- `profiles push <path> [--activate <name>]`

Key ideas:

- local changes become dirty before they are saved
- `show workspace` and `show config dirty` explain current lifecycle state
- `push` is robot-facing
- `save` is host-facing

Recommended workflow:

```text
configure terminal
merge config src/main/deploy/bringup_system.json
show workspace
show config dirty
validate config --all
save all
config push src/main/deploy/bringup_system.json --activate robot_2026_swerve
```

## 4. Profiles, Groups, And Devices

Purpose: Define the structure of the bringup system.

This area answers:

- what devices exist
- which profile they belong to
- how devices are grouped
- which device is currently selected for certain operations

Main commands:

- `profile <name>`
- `profile create <name>`
- `profile delete <name>`
- `profiles ...`
- `group <name>`
- `no group <name>`
- `add device <name> [group <name>]`
- `remove device <name> [group <name>]`
- `add next`
- `add all`
- `selected-device <device>`
- `selected-mode on|off`
- `device <name>`
- `device <name> set <field> <value>`
- `rename device <old> <new>`

Inside group mode:

- `add device <name>`
- `no device <name>`
- `member <device> enable`
- `member <device> disable`
- `member <device> toggle`
- `enable`
- `disable`
- `clear`

Typical workflow:

```text
configure terminal
profile robot_2026_swerve
group motion
add device "frontLeft Drive Motor"
add device "frontRight Drive Motor"
member "frontLeft Drive Motor" enable
end
show groups
show devices
```

## 5. Bindings And Operator Input Mapping

Purpose: Map human inputs to actions without editing JSON by hand.

There are two different binding systems.

### Global Bindings

Purpose: Define controller inventory and reusable controller/button/axis mappings.

These live in `bringup_bindings.json`.

Commands:

- `bindings show [controllers|bindings|axes] [--all] [--json] [--pretty]`
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

Use this area when you want to declare:

- what controllers exist
- which port they use
- named button mappings
- axis mappings with deadband/invert settings

Example:

```text
bindings controller add driver0 XBOX 0
bindings binding add stop driver0 button A pressed
bindings axis add drive driver0 leftY invert on deadband 0.12
bindings show --all --json --pretty
```

### Group Bindings

Purpose: Define how a specific group responds to an input.

These live in profile/group config, not in `bringup_bindings.json`.

Commands in group mode:

- `bind <input> analog`
- `bind <input> hold <value>`
- `bind <input> toggle <value>`
- `bind <input> jog-forward <value>`
- `bind <input> jog-reverse <value>`
- `no bind`
- `bind list`
- `bind explain <binding>`
- `bind test <binding>`

Use this area when you want to say:

- this group listens to `controller0.leftY`
- that input acts as analog, hold, toggle, or jog

Example:

```text
configure terminal
group motion
bind controller0.leftY analog
bind list
bind explain 1
bind test 1
```

Important distinction:

- `bindings ...` edits the global controller catalog
- `bind ...` edits current-group runtime intent

## 6. Test Authoring And Test Execution

Purpose: Define test content locally and run tests on the robot.

This area has both host-side and robot-side surfaces.

### Host-Side Test Authoring

Purpose: Create and edit test definitions in local configuration.

Main commands:

- `test set <name>`
- `test create <name>`
- `test delete <name>`
- `test import <name> <path>`
- `test export <name> <path>`
- `test validate [<name>] [--json] [--pretty]`
- `show tests`
- `show test <name>`
- `show test sets`

Inside test edit mode, commands define the test:

- `type ...`
- `device ...`
- `input-source ...`
- `deadband ...`
- `duty ...`
- `termination ...`
- `rotation ...`
- `hold ...`
- `limitswitch ...`
- `action ...`
- `color ...`
- `pattern ...`
- `brightness ...`
- `duration ...`

### Robot-Side Test Execution

Purpose: Run selected scripted tests on the roboRIO.

Main commands:

- `tests select <name>`
- `tests toggle`
- `tests run`
- `tests run-all`
- `tests wait [run-id] [--timeout <seconds>]`

Recommended model:

- author locally
- validate locally
- push/activate robot context as needed
- select/toggle/run on the robot

## 7. Diagnostics And Visibility

Purpose: Inspect effective state, provenance, and diagnostic detail.

This area is the main operator observability surface.

Main commands:

- `show status [robot|local|both]`
- `show workspace`
- `show config`
- `show config dirty`
- `show active`
- `show instantiated`
- `show faults`
- `show controllers`
- `show devices`
- `show device <name>`
- `show groups`
- `show group <name>`
- `show bindings`
- `show selected-device`
- `show runtime-state`
- `show runtime-components`
- `show tests`
- `show test <name>`
- `show signals`
- `show signal <device>`
- `diagnose motor <label>`
- `diagnose device <label>`

Use this area when you need answers like:

- what is loaded locally
- what is active on the robot
- which devices are instantiated
- which bindings exist
- which faults are present
- what signals a device supports

Example:

```text
show workspace
show active
show instantiated
show faults
show bindings --all --json --pretty
show signals
show signal "frontLeft Angle Motor"
```

## 8. Topology Authoring

Purpose: Define connectivity and neighborhood relationships.

This area is for topology-aware authoring and inspection.

Commands:

- `topology neighbor-ports set <node> <port> <neighbor> <neighborPort>`
- `topology neighbor-ports delete <node> <port>`
- `topology neighbor-ports clear <node>`
- `topology neighbor-auto all [label1,label2]`
- `topology neighbor-auto node <label>`
- `show topology`
- `show topology neighbors`
- `show neighbors <device>`

Use this area when you want to:

- describe wiring adjacency
- inspect neighbor structure
- support topology-based diagnosis features

## 9. CAN Mappings And Passive CAN Diagnostics

Purpose: Manage host-side CAN metadata and passive CAN understanding.

This project has a PC-side read-only CAN tool. The CLI surfaces some of that host-side metadata.

Commands:

- `can-mappings show`
- `can-mappings show manufacturers`
- `can-mappings show device-types`
- `can-mappings manufacturer ...`
- `can-mappings device-type ...`
- `can-mappings load <path>`
- `can-mappings save <path>`
- `can-mappings validate [path]`

Use this area when you need to:

- maintain manufacturer/device-type lookup tables
- validate CAN mapping data
- support display and diagnostics layers

Important rule:

- the PC-side CAN tool is passive and must never transmit CAN

## Show Commands By Area

Purpose: Provide a quick lookup from command to functional area.

### Session And Surface

- `help`
- `?`
- `tiu on|off`
- `exit`
- `end`

### Robot Runtime Control

- `connect`
- `disconnect`
- `profiles activate`
- `tests select|toggle|run|run-all`
- `run test`

### Host Config Lifecycle

- `merge config`
- `import config`
- `save ...`
- `load sources`
- `validate ...`
- `recover ...`
- `config push`
- `profiles push`
- `revert`

### Profiles, Groups, Devices

- `profile ...`
- `profiles ...`
- `group ...`
- `device ...`
- `selected-device`
- `selected-mode`
- `add next`
- `add all`
- `member ...`

### Bindings

- `bindings ...`
- `bind ...`
- `bind list`
- `bind explain`
- `bind test`

### Tests

- `test ...`
- `tests ...`
- `show tests`
- `show test ...`

### Diagnostics And Visibility

- `show ...`
- `diagnose ...`
- `show signals`
- `show signal ...`

### Topology

- `topology ...`
- `show topology`
- `show neighbors ...`

### CAN Metadata

- `can-mappings ...`

## Recommended Operator Workflows

Purpose: Show realistic end-to-end usage across areas.

### Workflow 1: Inspect A Live Robot

```text
connect
show status robot
show active
show instantiated
show faults
show bindings
```

### Workflow 2: Edit Local Bringup Structure

```text
configure terminal
merge config src/main/deploy/bringup_system.json
profile robot_2026_swerve
group motion
add device "frontLeft Drive Motor"
bind controller0.leftY analog
show binding
end
show workspace
save all
```

### Workflow 3: Edit Global Controller Bindings

```text
configure terminal
bindings controller add driver0 XBOX 0
bindings axis add drive driver0 leftY invert on deadband 0.12
bindings binding add stop driver0 button A pressed
bindings validate
bindings save src/main/deploy/bringup_bindings.json
```

### Workflow 4: Author Then Run A Test

```text
configure terminal
test create "Right Drive Test"
show tests
end
connect
tests select "Right Drive Test"
tests toggle
tests run
```

## Common Mistakes

Purpose: Clarify the most common operator confusions.

- Mistake:
  assuming `bindings ...` and `bind ...` are the same thing
  Correct:
  `bindings ...` is global controller config, `bind ...` is current-group behavior

- Mistake:
  assuming host edits change the robot immediately
  Correct:
  host edits stay local until explicit robot commands are issued

- Mistake:
  assuming `tests toggle` edits local test files
  Correct:
  it toggles the currently selected robot-side test enabled state

- Mistake:
  assuming every `show ...` is live robot truth
  Correct:
  some `show` commands are local-only, some are robot/local/both

- Mistake:
  assuming TIU changes semantics
  Correct:
  TIU changes presentation, not command behavior

## When To Use The Reference Manual

Purpose: Distinguish this guide from the full command reference.

Use this guide when you want:

- the major capability areas
- the operator mental model
- example workflows
- the difference between host and robot surfaces

Use [CLI_REFERENCE_MANUAL.md](/c:/Users/dmona/swerveBringupMotorTest/swerveBringupMotorTest1/docs/CLI_REFERENCE_MANUAL.md) when you want:

- exact command syntax
- every command permutation
- machine-precise usage details

## Notes

Purpose: Record a few stable rules that apply across all areas.

- The robot is authoritative for actuation and runtime execution.
- The PC-side CAN tool is passive and read-only on CAN.
- NetworkTables is used for diagnostics/state visibility, not as the main CLI command transport.
- TCP is the main command channel for robot-facing CLI actions.
- When in doubt, ask first:
  is this command editing host state, or commanding robot state?
