# CLI Reference Manual

Purpose: Provide a complete reference for every Bridge CLI command and permutation.

## Command List
Purpose: Enumerate every supported command by mode. Every command may be suffixed with `?` to show valid next arguments.

### Common (All Modes)
- `help`
- `help <topic>`
- `ping`
- `exit`
- `end`
- `quit`

### Exec Mode (`bridge>`)
- `show status [robot|local|both] [--json] [--pretty]`
- `show groups [robot|local|both] [--json] [--pretty]`
- `show group <name> [robot|local|both] [--json] [--pretty]`
- `show devices [robot|local|both] [--json] [--pretty]`
- `show device <name> [local] [--json] [--pretty]`
- `show device-group <name> [robot|local|both] [--json] [--pretty]`
- `show bindings [robot|local|both] [--json] [--pretty]`
- `show selected-device [robot|local|both] [--json] [--pretty]`
- `show runtime-state [robot|local|both] [--json] [--pretty]`
- `show runtime-components [local] [--json] [--pretty]`
- `show config [robot|local|both] [--json] [--pretty]`
- `show config local-raw [local] [--json] [--pretty]`
- `show config dirty [local] [--json] [--pretty]`
- `show profiles [local] [--json] [--pretty]`
- `show profile [local] [--json] [--pretty]`
- `show profile <name> [local] [--json] [--pretty]`
- `show topology [local] [--json] [--pretty]`
- `show topology neighbors [local] [--json] [--pretty]`
- `show visibility [local] [--json] [--pretty]`
- `show visibility summary [local] [--json] [--pretty]`
- `show visibility <device> [local] [--json] [--pretty]`
- `show tests [--json] [--pretty]`
- `show test <name> [--json] [--pretty]`
- `tests select <name>`
- `tests toggle`
- `tests run`
- `tests run-all`
- `show workspace [--json] [--pretty]`
- `show session [--json] [--pretty]`
- `show controllers [--json] [--pretty]`
- `diagnose motor <label>`
- `diagnose device <label>`
- `configure terminal`
- `connect`
- `disconnect`

### Config Mode (`bridge(config-...)#`)
- `group <name>`
- `no group <name>`
- `profile <name>`
- `diagnose motor <label>`
- `diagnose device <label>`
- `selected-device <device>`
- `selected-mode on`
- `selected-mode off`
- `merge config <path>`
- `import config <path>`
- `export runtime-groups <path>`
- `export cli-script <path>`
- `save all [--prompt]`
- `save config <path>`
- `save local-config <path>`
- `save profiles <path>`
- `save unified-config <path>`
- `rename device <old> <new>`
- `device <name>`
- `device <name> set <field> <value>`
- `topology neighbor-ports set <node> <port> <neighbor> <neighborPort>`
- `topology neighbor-ports delete <node> <port>`
- `topology neighbor-ports clear <node>`
- `topology neighbor-auto all [label1,label2]`
- `topology neighbor-auto node <label>`
- `validate config [path] [--all]`
- `validate profiles [robot|local] [--active]`
- `validate tests [--active-set]`
- `show <target> [robot|local|both] [--json] [--pretty]`
- `bindings show [controllers|bindings|axes] [--json] [--pretty]`
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
- `can-mappings show [manufacturers|device-types] [--json] [--pretty]`
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

### Group Mode (`bridge(config-...-group-...)#`)
- `show`
- `show members`
- `show binding`
- `show <target> [robot|local|both] [--json] [--pretty]`
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
- `write tests <path>`

### Device Mode (`bridge(config-device-...)#`)
- `show`
- `show <target> [robot|local|both] [--json] [--pretty]`
- `set <field> <value>`
- `no <field>`
- `write tests <path>`

### Test Mode (`bridge(config-test-...)#`)
- `show`
- `type joystick`
- `type button`
- `type composite`
- `type deadbandSweep`
- `type deviceAction`
- `device add <name>`
- `no device <name>`
- `inputSource <controller>.<inputId>`
- `deadband <value>`
- `duty <value>`
- `action toggle_led|set_color`
- `color #RRGGBB`
- `pattern solid`
- `brightness <value>`
- `duration <seconds>`
- `rotation limit <value>`
- `rotation encoderKey <label|internal>`
- `rotation encoderSource <internal|sparkmax_alt|external>`
- `rotation encoderMotorIndex <index>`
- `rotation encoderCountsPerRev <value>`
- `time timeout <seconds>`
- `time onTimeout <pass|fail>`
- `hold onRelease <pass|fail>`
- `limitswitch onHit <pass|fail>`
- `limitswitch id <id>`
- `deadbandSweep startDuty <value>`
- `deadbandSweep maxDuty <value>`
- `deadbandSweep stepDuty <value>`
- `deadbandSweep stepHoldSec <value>`
- `deadbandSweep motionThresholdRot <value>`
- `deadbandSweep requiredSamples <value>`
- `deadbandSweep encoderKey <label|internal>`
- `deadbandSweep encoderSource <internal|sparkmax_alt|external>`
- `deadbandSweep encoderMotorIndex <index>`
- `deadbandSweep encoderCountsPerRev <value>`
- `enabled true|false|on|off`
- `termination hold`
- `termination time <seconds>`
- `termination rotation <value>`
- `termination limitswitch [id]`
- `write tests <path>`
## Command Details
Purpose: Provide UNIX-style man page entries for every command.

### help

NAME

help - Display help for the CLI or a specific topic.

SYNOPSIS

help

DESCRIPTION

Display help for the CLI or a specific topic. This command is valid in Common (All Modes).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`help`

EXAMPLE OUTPUT
Available commands: ...

### help <topic>

NAME

help <topic> - Display help for the CLI or a specific topic.

SYNOPSIS

help <topic>

DESCRIPTION

Display help for the CLI or a specific topic. This command is valid in Common (All Modes).

PARAMETERS

- <topic>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`help tests`

EXAMPLE OUTPUT
Available commands: ...

### ping

NAME

ping - Emit a connectivity check and report current status.

SYNOPSIS

ping

DESCRIPTION

Emit a connectivity check and report current status. This command is valid in Common (All Modes).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`ping`

EXAMPLE OUTPUT
OK

### exit

NAME

exit - Exit the CLI.

SYNOPSIS

exit

DESCRIPTION

Exit the CLI. This command is valid in Common (All Modes).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`exit`

EXAMPLE OUTPUT
(no output)

### end

NAME

end - Exit the current sub-mode and return to the previous mode.

SYNOPSIS

end

DESCRIPTION

Exit the current sub-mode and return to the previous mode. This command is valid in Common (All Modes).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`end`

EXAMPLE OUTPUT
(no output)

### quit

NAME

quit - Exit the CLI.

SYNOPSIS

quit

DESCRIPTION

Exit the CLI. This command is valid in Common (All Modes).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`quit`

EXAMPLE OUTPUT
(no output)

### show status [robot|local|both] [--json] [--pretty]

NAME

show status [robot|local|both] [--json] [--pretty] - Display the requested information.

SYNOPSIS

show status [robot|local|both] [--json] [--pretty]

DESCRIPTION

Display the requested information. This command is valid in Exec Mode (`bridge>`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show status both --json`

EXAMPLE OUTPUT
SOURCE: local
Local status:
  robotConnected=false
  canConnected=false
  ntConnected=false
  activeProfile=home_030226

### show groups [robot|local|both] [--json] [--pretty]

NAME

show groups [robot|local|both] [--json] [--pretty] - Display the requested information.

SYNOPSIS

show groups [robot|local|both] [--json] [--pretty]

DESCRIPTION

Display the requested information. This command is valid in Exec Mode (`bridge>`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show groups [robot|local|both] [--json] [--pretty]`

EXAMPLE OUTPUT
SOURCE: local
Local groups (profile home_030226):
  motors (enabled)

### show group <name> [robot|local|both] [--json] [--pretty]

NAME

show group <name> [robot|local|both] [--json] [--pretty] - Display the requested information.

SYNOPSIS

show group <name> [robot|local|both] [--json] [--pretty]

DESCRIPTION

Display the requested information. This command is valid in Exec Mode (`bridge>`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show group motors local --json`

EXAMPLE OUTPUT
SOURCE: local
Local group motors (profile home_030226):
  enabled=true
  members=3
  bindings=0
  members:
    SPARKMAX/NEO 25 (enabled)
    SPARKMAX/NEO550 7 (enabled)
    FALCON 9 (enabled)

### show devices [robot|local|both] [--json] [--pretty]

NAME

show devices [robot|local|both] [--json] [--pretty] - Display the requested information.

SYNOPSIS

show devices [robot|local|both] [--json] [--pretty]

DESCRIPTION

Display the requested information. This command is valid in Exec Mode (`bridge>`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show devices [robot|local|both] [--json] [--pretty]`

EXAMPLE OUTPUT
SOURCE: local
Local devices:
  SPARKMAX/NEO 25
  SPARKMAX/NEO550 7 limit fwd
  SPARKMAX/NEO550 7
  FALCON 9
  cancoder 44
  pdp
  roboRIO

### show device <name> [local] [--json] [--pretty]

NAME

show device <name> [local] [--json] [--pretty] - Display the requested information.

SYNOPSIS

show device <name> [local] [--json] [--pretty]

DESCRIPTION

Display the device definition from the profiles registry. This command is valid in Exec Mode (`bridge>`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show device <name> [local] [--json] [--pretty]`

EXAMPLE OUTPUT
SOURCE: local
Local registry device SPARKMAX/NEO 25:
  interface=CAN
  manufacturer=5
  deviceType=2
  id=25

### show device-group <name> [robot|local|both] [--json] [--pretty]

NAME

show device-group <name> [robot|local|both] [--json] [--pretty] - Display the requested information.

SYNOPSIS

show device-group <name> [robot|local|both] [--json] [--pretty]

DESCRIPTION

Display the device group membership/usage information. This command is valid in Exec Mode (`bridge>`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show device-group "SPARKMAX/NEO 25" --json`

EXAMPLE OUTPUT
SOURCE: local
Local device-group SPARKMAX/NEO 25:
  label=SPARKMAX/NEO 25
  interface=CAN
  manufacturer=5 (REV)
  deviceType=2 (MotorController)
  id=25
  model=REV NEO
  type=motor

### show bindings [robot|local|both] [--json] [--pretty]

NAME

show bindings [robot|local|both] [--json] [--pretty] - Display the requested information.

SYNOPSIS

show bindings [robot|local|both] [--json] [--pretty]

DESCRIPTION

Display the requested information. This command is valid in Exec Mode (`bridge>`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show bindings [robot|local|both] [--json] [--pretty]`

EXAMPLE OUTPUT
SOURCE: local
Local bindings:
  controllers=0
  bindings=0
  axes=0

### show selected-device [robot|local|both] [--json] [--pretty]

NAME

show selected-device [robot|local|both] [--json] [--pretty] - Display the requested information.

SYNOPSIS

show selected-device [robot|local|both] [--json] [--pretty]

DESCRIPTION

Display the requested information. This command is valid in Exec Mode (`bridge>`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show selected-device [robot|local|both] [--json] [--pretty]`

EXAMPLE OUTPUT
SOURCE: local
Local selected-device:
  enabled=false
  device=

### show runtime-state [robot|local|both] [--json] [--pretty]

NAME

show runtime-state [robot|local|both] [--json] [--pretty] - Display the requested information.

SYNOPSIS

show runtime-state [robot|local|both] [--json] [--pretty]

DESCRIPTION

Display the requested information. This command is valid in Exec Mode (`bridge>`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show runtime-state [robot|local|both] [--json] [--pretty]`

EXAMPLE OUTPUT
SOURCE: local
Local runtime-state:
  present=false

### show runtime-components [local] [--json] [--pretty]

NAME

show runtime-components [local] [--json] [--pretty] - Display runtime threads and component status.

SYNOPSIS

show runtime-components [local] [--json] [--pretty]

DESCRIPTION

Display local runtime threads and component status. This command is valid in Exec Mode (`bridge>`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

None.

ERRORS

Reports invalid syntax or missing runtime provider when applicable.

NOTES

Always local; ignores robot source flags.

EXAMPLE

`show runtime-components --json`

EXAMPLE OUTPUT
Local runtime-components:
  components:
    cli: running
    sniffer: running
    session: connected (handshake=done)
    visibility: enabled
    pcap: disabled
    console-monitor: disabled
    sources: enabled (count=1 available=1)
    source:default: available (enabled)
  threads:
    sniffer id=1234 daemon=true alive=true

### show config [robot|local|both] [--json] [--pretty]

NAME

show config [robot|local|both] [--json] [--pretty] - Display the requested information.

SYNOPSIS

show config [robot|local|both] [--json] [--pretty]

DESCRIPTION

Display the requested information. This command is valid in Exec Mode (`bridge>`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show config [robot|local|both] [--json] [--pretty]`

EXAMPLE OUTPUT
SOURCE: local
Local config: groups=1 devices=7 profile=home_030226

### show config local-raw [local] [--json] [--pretty]

NAME

show config local-raw [local] [--json] [--pretty] - Display the requested information.

SYNOPSIS

show config local-raw [local] [--json] [--pretty]

DESCRIPTION

Display the requested information. This command is valid in Exec Mode (`bridge>`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show config local-raw [local] [--json] [--pretty]`

EXAMPLE OUTPUT
SOURCE: local
Local raw config (byProfile):
  home_030226: groups=1 selectedDevice=disabled

### show config dirty [local] [--json] [--pretty]

NAME

show config dirty [local] [--json] [--pretty] - Display the requested information.

SYNOPSIS

show config dirty [local] [--json] [--pretty]

DESCRIPTION

Display the requested information. This command is valid in Exec Mode (`bridge>`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show config dirty [local] [--json] [--pretty]`

EXAMPLE OUTPUT
SOURCE: local
Local config dirty: false

### show profiles [local] [--json] [--pretty]

NAME

show profiles [local] [--json] [--pretty] - Display the requested information.

SYNOPSIS

show profiles [local] [--json] [--pretty]

DESCRIPTION

Display the requested information. This command is valid in Exec Mode (`bridge>`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show profiles [local] [--json] [--pretty]`

EXAMPLE OUTPUT
SOURCE: local
Profiles (default=home_030226):
  home_030226
  home_031226
  robot_2026
  robot_test1
  demo_home_022326

### show profile [local] [--json] [--pretty]

NAME

show profile [local] [--json] [--pretty] - Display the requested information.

SYNOPSIS

show profile [local] [--json] [--pretty]

DESCRIPTION

Display the requested information. This command is valid in Exec Mode (`bridge>`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show profile [local] [--json] [--pretty]`

EXAMPLE OUTPUT
SOURCE: local
Profile home_030226:
  devices=6
  SPARKMAX/NEO 25
  roboRIO
  FALCON 9
  cancoder 44
  pdp
  roboRIO

### show profile <name> [local] [--json] [--pretty]

NAME

show profile <name> [local] [--json] [--pretty] - Display the requested information.

SYNOPSIS

show profile <name> [local] [--json] [--pretty]

DESCRIPTION

Display the requested information. This command is valid in Exec Mode (`bridge>`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show profile <name> [local] [--json] [--pretty]`

### show topology [local] [--json] [--pretty]

show topology [local] [--json] [--pretty] - Display diagram nodes for the active profile.

show topology [local] [--json] [--pretty]

Notes:
- Output includes diagram-only nodes (for example analyzers) and device nodes.
- Callouts are excluded.
- JSON output includes `neighborPorts` when present.

`show topology [local] [--json] [--pretty]`

EXAMPLE OUTPUT
SOURCE: local
Topology nodes:
  PDH nodeType=device category=pdh id=1 bus=2 row=0 tags=(none)
  roboRIO nodeType=device category=roborio id=0 bus=2 row=1 tags=(none)

### show topology neighbors [local] [--json] [--pretty]

show topology neighbors [local] [--json] [--pretty] - Display neighbor port assignments for the active profile.

show topology neighbors [local] [--json] [--pretty]

Notes:
- Only neighbor ports are shown; no device list.
- JSON output includes `neighborPorts` plus the node list.

`show topology neighbors [local] [--json] [--pretty]`

EXAMPLE OUTPUT
SOURCE: local
Topology neighbors:
  PDH left -> roboRIO right

### topology neighbor-ports set/delete/clear

topology neighbor-ports set/delete/clear - Edit neighbor ports for the active profile (config mode).

topology neighbor-ports set <node> <port> <neighbor> <neighborPort>  
topology neighbor-ports delete <node> <port>  
topology neighbor-ports clear <node>

Notes:
- Enforces same bus segment and adjacency by x-order.

### topology neighbor-auto all|node

topology neighbor-auto all|node - Auto-assign left/right neighbors from x-order (config mode).

topology neighbor-auto all [label1,label2]  
topology neighbor-auto node <label>

Notes:
- Overwrites existing neighborPorts for the target node(s).
- If label1,label2 is provided, only those labels are updated; omit to update all nodes.
- Provide the label list as a single token (comma-separated) or wrap it in quotes if it includes spaces.
- CANnect device links populate `next/branch1/branch2` entries.

### show visibility [local] [--json] [--pretty]

show visibility [local] [--json] [--pretty] - Display the multi-analyzer visibility matrix.

show visibility [local] [--json] [--pretty]

`show visibility [local] [--json] [--pretty]`

### show visibility summary [local] [--json] [--pretty]

show visibility summary [local] [--json] [--pretty] - Display visibility summary counts.

show visibility summary [local] [--json] [--pretty]

`show visibility summary [local] [--json] [--pretty]`

### show visibility <device> [local] [--json] [--pretty]

show visibility <device> [local] [--json] [--pretty] - Display per-source visibility for one device.

show visibility <device> [local] [--json] [--pretty]

`show visibility <device> [local] [--json] [--pretty]`

### show tests [--json] [--pretty]

NAME

show tests [--json] [--pretty] - Display the requested information.

SYNOPSIS

show tests [--json] [--pretty]

DESCRIPTION

Display the requested information. This command is valid in Exec Mode (`bridge>`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show tests [--json] [--pretty]`

EXAMPLE OUTPUT
SOURCE: local
Tests (set=default):
  Rotation only (internal)
  Deadband sweep (internal)
  Rotation + Time
  Time only
  Nudge (0.2 for 0.5s)
  Limit switch only
  Hold to run
  Rotation + Time + Limit
  All checks
  Joystick motor (controller0.leftY)

### show test <name> [--json] [--pretty]

NAME

show test <name> [--json] [--pretty] - Display the requested information.

SYNOPSIS

show test <name> [--json] [--pretty]

DESCRIPTION

Display the requested information. This command is valid in Exec Mode (`bridge>`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show test <name> [--json] [--pretty]`

EXAMPLE OUTPUT
SOURCE: local
Test Rotation only (internal):
  type=composite
  duty=0.2
  rotation.limitRot=15.0
  motorLabels=[SPARKMAX/NEO 25]

### configure terminal

NAME

configure terminal - Enter configuration mode.

SYNOPSIS

configure terminal

DESCRIPTION

Enter configuration mode. This command is valid in Exec Mode (`bridge>`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`configure terminal`

EXAMPLE OUTPUT
Entering configuration mode.

### connect

NAME

connect - Connect to the robot/NT back end when available.

SYNOPSIS

connect

DESCRIPTION

Connect to the robot/NT back end when available. This command is valid in Exec Mode (`bridge>`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`connect`

EXAMPLE OUTPUT
Connected.

### disconnect

NAME

disconnect - Disconnect from the robot/NT back end.

SYNOPSIS

disconnect

DESCRIPTION

Disconnect from the robot/NT back end. This command is valid in Exec Mode (`bridge>`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`disconnect`

EXAMPLE OUTPUT
Disconnected.

### diagnose motor <label>

NAME

diagnose motor <label> - Diagnose a motor using runtime telemetry.

SYNOPSIS

diagnose motor <label>

DESCRIPTION

Fetch runtime-state telemetry and produce a ranked list of likely causes for a motor not running.
This command is valid in Exec Mode (`bridge>`) and Config Mode (`bridge(config-...)#`).

PARAMETERS

- <label>: Device label of the motor to diagnose.

RETURNS

Prints diagnosis output to the console; errors are reported inline.

SIDE EFFECTS

Requests runtime-state data from the robot.

ERRORS

Reports connection errors, missing devices, or ambiguous labels.

NOTES

If telemetry is missing, the output will include `UNKNOWN` plus a missing-fields list.

EXAMPLE

`diagnose motor "Drive Motor (id 2)"`

EXAMPLE OUTPUT
Likely causes:
1) NO_MOTION (medium)
  Evidence: appliedV=2.4, velRpm=0.0

### diagnose device <label>

NAME

diagnose device <label> - Diagnose a motor using runtime telemetry (alias).

SYNOPSIS

diagnose device <label>

DESCRIPTION

Alias for `diagnose motor <label>`.

PARAMETERS

- <label>: Device label of the motor to diagnose.

RETURNS

Prints diagnosis output to the console; errors are reported inline.

SIDE EFFECTS

Requests runtime-state data from the robot.

ERRORS

Reports connection errors, missing devices, or ambiguous labels.

NOTES

If telemetry is missing, the output will include `UNKNOWN` plus a missing-fields list.

EXAMPLE

`diagnose device "Drive Motor (id 2)"`

EXAMPLE OUTPUT
Likely causes:
1) UNKNOWN (low)
Missing fields:
  appliedV, motorCurrentA, velRpm

### group <name>

NAME

group <name> - Enter group configuration mode for the named group, creating it if needed.

SYNOPSIS

group <name>

DESCRIPTION

Enter group configuration mode for the named group, creating it if needed. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`group motors`

EXAMPLE OUTPUT
Group selected.

### no group <name>

NAME

no group <name> - Delete the named group from the active profile.

SYNOPSIS

no group <name>

DESCRIPTION

Delete the named group from the active profile. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`no group <name>`

EXAMPLE OUTPUT
Group deleted.

### profile <name>

NAME

profile <name> - Select the active profile context.

SYNOPSIS

profile <name>

DESCRIPTION

Select the active profile context. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`profile home_030226`

EXAMPLE OUTPUT
Active profile: <name>

### selected-device <device>

NAME

selected-device <device> - Set the selected device override for the active profile.

SYNOPSIS

selected-device <device>

DESCRIPTION

Set the selected device override for the active profile. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <device>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`selected-device <device>`

EXAMPLE OUTPUT
Selected device set.

### selected-mode on

NAME

selected-mode on - Enable or disable selected-device override behavior.

SYNOPSIS

selected-mode on

DESCRIPTION

Enable or disable selected-device override behavior. This command is valid in Config Mode (`bridge(config-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`selected-mode on`

EXAMPLE OUTPUT
Selected mode updated.

### selected-mode off

NAME

selected-mode off - Enable or disable selected-device override behavior.

SYNOPSIS

selected-mode off

DESCRIPTION

Enable or disable selected-device override behavior. This command is valid in Config Mode (`bridge(config-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`selected-mode off`

EXAMPLE OUTPUT
Selected mode updated.

### merge config <path>

NAME

merge config <path> - Merge config from a file into the current local config.

SYNOPSIS

merge config <path>

DESCRIPTION

Merge config from a file into the current local config. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <path>: Filesystem path to a JSON file.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`merge config <path>`

EXAMPLE OUTPUT
Merge complete.

### import config <path>

NAME

import config <path> - Import config from a file, replacing local config where applicable.

SYNOPSIS

import config <path>

DESCRIPTION

Import config from a file, replacing local config where applicable. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <path>: Filesystem path to a JSON file.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`import config <path>`

EXAMPLE OUTPUT
Import complete.

### export runtime-groups <path>

NAME

export runtime-groups <path> - Export runtime group data to a JSON file.

SYNOPSIS

export runtime-groups <path>

DESCRIPTION

Export runtime group data to a JSON file. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <path>: Filesystem path to a JSON file.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`export runtime-groups <path>`

EXAMPLE OUTPUT
Exported runtime groups.

### export cli-script <path>

NAME

export cli-script <path> - Export the current config as a CLI script.

SYNOPSIS

export cli-script <path>

DESCRIPTION

Export the current config as a CLI script. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <path>: Filesystem path to a JSON file.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`export cli-script <path>`

EXAMPLE OUTPUT
Exported CLI script.

### save config <path>

NAME

save config <path> - Write the current configuration state to a file.

SYNOPSIS

save config <path>

DESCRIPTION

Write the current configuration state to a file. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <path>: Filesystem path to a JSON file.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`save config <path>`

EXAMPLE OUTPUT
Saved.

### save local-config <path>

NAME

save local-config <path> - Write the current configuration state to a file.

SYNOPSIS

save local-config <path>

DESCRIPTION

Write the current configuration state to a file. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <path>: Filesystem path to a JSON file.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`save local-config <path>`

EXAMPLE OUTPUT
Saved.

### save profiles <path>

NAME

save profiles <path> - Write the current configuration state to a file.

SYNOPSIS

save profiles <path>

DESCRIPTION

Write the current configuration state to a file. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <path>: Filesystem path to a JSON file.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`save profiles data/bringup_system.json`

EXAMPLE OUTPUT
Saved.

### save unified-config <path>

NAME

save unified-config <path> - Write the current configuration state to a file.

SYNOPSIS

save unified-config <path>

DESCRIPTION

Write the current configuration state to a file. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <path>: Filesystem path to a JSON file.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`save unified-config <path>`

EXAMPLE OUTPUT
Saved.

### rename device <old> <new>

NAME

rename device <old> <new> - Rename a device label everywhere in the local config.

SYNOPSIS

rename device <old> <new>

DESCRIPTION

Rename a device label everywhere in the local config. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <old>: Command parameter.

- <new>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`rename device <old> <new>`

EXAMPLE OUTPUT
Device renamed.

### device <name>

NAME

device <name> - Enter device configuration mode for the named device, creating it if needed.

SYNOPSIS

device <name>

DESCRIPTION

Enter device configuration mode for the named device, creating it if needed. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`device "SPARKMAX/NEO 25"`

EXAMPLE OUTPUT
Device updated.

### device <name> set <field> <value>

NAME

device <name> set <field> <value> - Set a field on a device definition.

SYNOPSIS

device <name> set <field> <value>

DESCRIPTION

Set a field on a device definition. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

- <field>: Field name to update in the current object.

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`device "SPARKMAX/NEO 25"`

EXAMPLE OUTPUT
Device updated.

### validate config [path]

NAME

validate config [path] - Validate the current config or the provided file.

SYNOPSIS

validate config [path]

DESCRIPTION

Validate the current config or the provided file. This command is valid in Config Mode (`bridge(config-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`validate config [path]`

EXAMPLE OUTPUT
OK

### show <target> [robot|local|both] [--json] [--pretty]

NAME

show <target> [robot|local|both] [--json] [--pretty] - Display the requested information.

SYNOPSIS

show <target> [robot|local|both] [--json] [--pretty]

DESCRIPTION

Display the requested information. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <target>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show <target> [robot|local|both] [--json] [--pretty]`

EXAMPLE OUTPUT
SOURCE: local
{...json...}

### bindings show [controllers|bindings|axes] [--json] [--pretty]

NAME

bindings show [controllers|bindings|axes] [--json] [--pretty] - Configure or validate controller bindings.

SYNOPSIS

bindings show [controllers|bindings|axes] [--json] [--pretty]

DESCRIPTION

Configure or validate controller bindings. This command is valid in Config Mode (`bridge(config-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bindings show [controllers|bindings|axes] [--json] [--pretty]`

EXAMPLE OUTPUT
Bindings updated.

### bindings controller add <name> <type> <port>

NAME

bindings controller add <name> <type> <port> - Configure or validate controller bindings.

SYNOPSIS

bindings controller add <name> <type> <port>

DESCRIPTION

Configure or validate controller bindings. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

- <type>: Type name, command type, or test type, depending on context.

- <port>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bindings controller add driver xbox 0`

EXAMPLE OUTPUT
Bindings updated.

### bindings controller set <name> <field> <value>

NAME

bindings controller set <name> <field> <value> - Configure or validate controller bindings.

SYNOPSIS

bindings controller set <name> <field> <value>

DESCRIPTION

Configure or validate controller bindings. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

- <field>: Field name to update in the current object.

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bindings controller set <name> <field> <value>`

EXAMPLE OUTPUT
Bindings updated.

### bindings controller rename <old> <new>

NAME

bindings controller rename <old> <new> - Configure or validate controller bindings.

SYNOPSIS

bindings controller rename <old> <new>

DESCRIPTION

Configure or validate controller bindings. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <old>: Command parameter.

- <new>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bindings controller rename <old> <new>`

EXAMPLE OUTPUT
Bindings updated.

### bindings no controller <name>

NAME

bindings no controller <name> - Configure or validate controller bindings.

SYNOPSIS

bindings no controller <name>

DESCRIPTION

Configure or validate controller bindings. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bindings no controller <name>`

EXAMPLE OUTPUT
Bindings updated.

### bindings binding add <command> <controller> <input> <id> <mode>

NAME

bindings binding add <command> <controller> <input> <id> <mode> - Configure or validate controller bindings.

SYNOPSIS

bindings binding add <command> <controller> <input> <id> <mode>

DESCRIPTION

Configure or validate controller bindings. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <command>: CLI command name used as a binding target.

- <controller>: Controller label (as defined in bindings).

- <input>: Input name (button/axis name) for a controller.

- <id>: Numeric identifier (controller id, device id, or limit switch id) depending on command context.

- <mode>: Binding mode (hold/toggle/jog/etc) depending on command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bindings binding add "group motors" driver button A hold`

EXAMPLE OUTPUT
Bindings updated.

### bindings binding set <index> <field> <value>

NAME

bindings binding set <index> <field> <value> - Configure or validate controller bindings.

SYNOPSIS

bindings binding set <index> <field> <value>

DESCRIPTION

Configure or validate controller bindings. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <index>: Zero-based index into the current list of bindings/axes.

- <field>: Field name to update in the current object.

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bindings binding set <index> <field> <value>`

EXAMPLE OUTPUT
Bindings updated.

### bindings binding delete <index>

NAME

bindings binding delete <index> - Configure or validate controller bindings.

SYNOPSIS

bindings binding delete <index>

DESCRIPTION

Configure or validate controller bindings. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <index>: Zero-based index into the current list of bindings/axes.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bindings binding delete <index>`

EXAMPLE OUTPUT
Bindings updated.

### bindings axis add <command> <controller> <id> invert <on|off> deadband <value>

NAME

bindings axis add <command> <controller> <id> invert <on|off> deadband <value> - Configure or validate controller bindings.

SYNOPSIS

bindings axis add <command> <controller> <id> invert <on|off> deadband <value>

DESCRIPTION

Configure or validate controller bindings. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <command>: CLI command name used as a binding target.

- <controller>: Controller label (as defined in bindings).

- <id>: Numeric identifier (controller id, device id, or limit switch id) depending on command context.

- <on|off>: Command parameter.

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bindings axis add "group motors" driver 1 invert off deadband 0.1`

EXAMPLE OUTPUT
Bindings updated.

### bindings axis set <index> <field> <value>

NAME

bindings axis set <index> <field> <value> - Configure or validate controller bindings.

SYNOPSIS

bindings axis set <index> <field> <value>

DESCRIPTION

Configure or validate controller bindings. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <index>: Zero-based index into the current list of bindings/axes.

- <field>: Field name to update in the current object.

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bindings axis set <index> <field> <value>`

EXAMPLE OUTPUT
Bindings updated.

### bindings axis delete <index>

NAME

bindings axis delete <index> - Configure or validate controller bindings.

SYNOPSIS

bindings axis delete <index>

DESCRIPTION

Configure or validate controller bindings. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <index>: Zero-based index into the current list of bindings/axes.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bindings axis delete <index>`

EXAMPLE OUTPUT
Bindings updated.

### bindings load <path>

NAME

bindings load <path> - Configure or validate controller bindings.

SYNOPSIS

bindings load <path>

DESCRIPTION

Configure or validate controller bindings. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <path>: Filesystem path to a JSON file.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bindings load <path>`

EXAMPLE OUTPUT
Bindings updated.

### bindings save <path>

NAME

bindings save <path> - Configure or validate controller bindings.

SYNOPSIS

bindings save <path>

DESCRIPTION

Configure or validate controller bindings. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <path>: Filesystem path to a JSON file.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bindings save <path>`

EXAMPLE OUTPUT
Bindings updated.

### bindings validate [path]

NAME

bindings validate [path] - Configure or validate controller bindings.

SYNOPSIS

bindings validate [path]

DESCRIPTION

Configure or validate controller bindings. This command is valid in Config Mode (`bridge(config-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bindings validate [path]`

EXAMPLE OUTPUT
Bindings updated.

### can-mappings show [manufacturers|device-types] [--json] [--pretty]

NAME

can-mappings show [manufacturers|device-types] [--json] [--pretty] - Configure or validate CAN mappings.

SYNOPSIS

can-mappings show [manufacturers|device-types] [--json] [--pretty]

DESCRIPTION

Configure or validate CAN mappings. This command is valid in Config Mode (`bridge(config-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`can-mappings show [manufacturers|device-types] [--json] [--pretty]`

EXAMPLE OUTPUT
Mappings updated.

### can-mappings manufacturer set <id> <name>

NAME

can-mappings manufacturer set <id> <name> - Configure or validate CAN mappings.

SYNOPSIS

can-mappings manufacturer set <id> <name>

DESCRIPTION

Configure or validate CAN mappings. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <id>: Numeric identifier (controller id, device id, or limit switch id) depending on command context.

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`can-mappings manufacturer set <id> <name>`

EXAMPLE OUTPUT
Mappings updated.

### can-mappings manufacturer delete <id>

NAME

can-mappings manufacturer delete <id> - Configure or validate CAN mappings.

SYNOPSIS

can-mappings manufacturer delete <id>

DESCRIPTION

Configure or validate CAN mappings. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <id>: Numeric identifier (controller id, device id, or limit switch id) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`can-mappings manufacturer delete <id>`

EXAMPLE OUTPUT
Mappings updated.

### can-mappings device-type set <id> <name>

NAME

can-mappings device-type set <id> <name> - Configure or validate CAN mappings.

SYNOPSIS

can-mappings device-type set <id> <name>

DESCRIPTION

Configure or validate CAN mappings. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <id>: Numeric identifier (controller id, device id, or limit switch id) depending on command context.

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`can-mappings device-type set <id> <name>`

EXAMPLE OUTPUT
Mappings updated.

### can-mappings device-type delete <id>

NAME

can-mappings device-type delete <id> - Configure or validate CAN mappings.

SYNOPSIS

can-mappings device-type delete <id>

DESCRIPTION

Configure or validate CAN mappings. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <id>: Numeric identifier (controller id, device id, or limit switch id) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`can-mappings device-type delete <id>`

EXAMPLE OUTPUT
Mappings updated.

### can-mappings load <path>

NAME

can-mappings load <path> - Configure or validate CAN mappings.

SYNOPSIS

can-mappings load <path>

DESCRIPTION

Configure or validate CAN mappings. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <path>: Filesystem path to a JSON file.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`can-mappings load <path>`

EXAMPLE OUTPUT
Mappings updated.

### can-mappings save <path>

NAME

can-mappings save <path> - Configure or validate CAN mappings.

SYNOPSIS

can-mappings save <path>

DESCRIPTION

Configure or validate CAN mappings. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <path>: Filesystem path to a JSON file.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`can-mappings save <path>`

EXAMPLE OUTPUT
Mappings updated.

### can-mappings validate [path]

NAME

can-mappings validate [path] - Configure or validate CAN mappings.

SYNOPSIS

can-mappings validate [path]

DESCRIPTION

Configure or validate CAN mappings. This command is valid in Config Mode (`bridge(config-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`can-mappings validate [path]`

EXAMPLE OUTPUT
Mappings updated.

### tests templates

NAME

tests templates - Operate on test templates or test files.

SYNOPSIS

tests templates

DESCRIPTION

Operate on test templates or test files. This command is valid in Config Mode (`bridge(config-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`tests templates`

EXAMPLE OUTPUT
Tests updated.

### tests load <path>

NAME

tests load <path> - Operate on test templates or test files.

SYNOPSIS

tests load <path>

DESCRIPTION

Operate on test templates or test files. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <path>: Filesystem path to a JSON file.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`tests load <path>`

EXAMPLE OUTPUT
Tests updated.

### tests load template <name>

NAME

tests load template <name> - Operate on test templates or test files.

SYNOPSIS

tests load template <name>

DESCRIPTION

Operate on test templates or test files. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`tests load template hold_only`

EXAMPLE OUTPUT
Tests updated.

### tests save

NAME

tests save - Operate on test templates or test files.

SYNOPSIS

tests save

DESCRIPTION

Operate on test templates or test files. This command is valid in Config Mode (`bridge(config-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`tests save`

EXAMPLE OUTPUT
Tests updated.

### write tests <path>

NAME

write tests <path> - Deprecated: export standalone tests JSON (legacy).

SYNOPSIS

write tests <path>

DESCRIPTION

Deprecated export. Writes the current tests to a standalone JSON file. The robot consumes tests from `bringup_system.json` under `bridgeConfig.byProfile.<profile>.tests`; for deployable output, use `save unified-config <path>`.

PARAMETERS

- <path>: Filesystem path to a JSON file.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`save unified-config data/bringup_system.json`

EXAMPLE OUTPUT
Wrote tests.

### test set <name>

NAME

test set <name> - Select an existing test set by name.

SYNOPSIS

test set <name>

DESCRIPTION

Select an existing test set by name. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`test motorPulse`

EXAMPLE OUTPUT
Active test set: <name>

### test create <name>

NAME

test create <name> - Create a new test and enter test edit mode.

SYNOPSIS

test create <name>

DESCRIPTION

Create a new test and enter test edit mode. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`test create motorPulse`

EXAMPLE OUTPUT
Test created.

### test delete <name>

NAME

test delete <name> - Delete the named test from the current test set.

SYNOPSIS

test delete <name>

DESCRIPTION

Delete the named test from the current test set. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`test motorPulse`

EXAMPLE OUTPUT
Test deleted.

### test <name>

NAME

test <name> - Enter test edit mode for an existing test.

SYNOPSIS

test <name>

DESCRIPTION

Enter test edit mode for an existing test. This command is valid in Config Mode (`bridge(config-...)#`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`test motorPulse`

EXAMPLE OUTPUT
Test selected.

### show

NAME

show - Execute the command.

SYNOPSIS

show

DESCRIPTION

Execute the command. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show`

EXAMPLE OUTPUT
SOURCE: local
<summary>

### show members

NAME

show members - Display the requested information.

SYNOPSIS

show members

DESCRIPTION

Display the requested information. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show members`

EXAMPLE OUTPUT
Members:
  SPARKMAX/NEO 25 (enabled)
  SPARKMAX/NEO550 7 (enabled)
  FALCON 9 (enabled)

### show binding

NAME

show binding - Display the requested information.

SYNOPSIS

show binding

DESCRIPTION

Display the requested information. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show binding`

EXAMPLE OUTPUT
Bindings: (none)

### show <target> [robot|local|both] [--json] [--pretty]

NAME

show <target> [robot|local|both] [--json] [--pretty] - Display the requested information.

SYNOPSIS

show <target> [robot|local|both] [--json] [--pretty]

DESCRIPTION

Display the requested information. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

PARAMETERS

- <target>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show <target> [robot|local|both] [--json] [--pretty]`

EXAMPLE OUTPUT
SOURCE: local
{...json...}

### add device <device>

NAME

add device <device> - Add a device to the current group.

SYNOPSIS

add device <device>

DESCRIPTION

Add a device to the current group. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

PARAMETERS

- <device>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`add device <device>`

EXAMPLE OUTPUT
Device added.

### no device <device>

NAME

no device <device> - Remove a device from the current group.

SYNOPSIS

no device <device>

DESCRIPTION

Remove a device from the current group. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

PARAMETERS

- <device>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`no device <device>`

EXAMPLE OUTPUT
Device removed.

### member <device> enable

NAME

member <device> enable - Enable, disable, or toggle a group member.

SYNOPSIS

member <device> enable

DESCRIPTION

Enable, disable, or toggle a group member. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

PARAMETERS

- <device>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`member <device> enable`

EXAMPLE OUTPUT
Member updated.

### member <device> disable

NAME

member <device> disable - Enable, disable, or toggle a group member.

SYNOPSIS

member <device> disable

DESCRIPTION

Enable, disable, or toggle a group member. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

PARAMETERS

- <device>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`member <device> disable`

EXAMPLE OUTPUT
Member updated.

### member <device> toggle

NAME

member <device> toggle - Enable, disable, or toggle a group member.

SYNOPSIS

member <device> toggle

DESCRIPTION

Enable, disable, or toggle a group member. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

PARAMETERS

- <device>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`member <device> toggle`

EXAMPLE OUTPUT
Member updated.

### bind <input> analog

NAME

bind <input> analog - Bind a controller input to a group action.

SYNOPSIS

bind <input> analog

DESCRIPTION

Bind a controller input to a group action. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

PARAMETERS

- <input>: Input name (button/axis name) for a controller.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bind <input> analog`

EXAMPLE OUTPUT
Binding set.

### bind <input> hold <value>

NAME

bind <input> hold <value> - Bind a controller input to a group action.

SYNOPSIS

bind <input> hold <value>

DESCRIPTION

Bind a controller input to a group action. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

PARAMETERS

- <input>: Input name (button/axis name) for a controller.

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bind <input> hold <value>`

EXAMPLE OUTPUT
Binding set.

### bind <input> toggle <value>

NAME

bind <input> toggle <value> - Bind a controller input to a group action.

SYNOPSIS

bind <input> toggle <value>

DESCRIPTION

Bind a controller input to a group action. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

PARAMETERS

- <input>: Input name (button/axis name) for a controller.

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bind <input> toggle <value>`

EXAMPLE OUTPUT
Binding set.

### bind <input> jog-forward <value>

NAME

bind <input> jog-forward <value> - Bind a controller input to a group action.

SYNOPSIS

bind <input> jog-forward <value>

DESCRIPTION

Bind a controller input to a group action. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

PARAMETERS

- <input>: Input name (button/axis name) for a controller.

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bind <input> jog-forward <value>`

EXAMPLE OUTPUT
Binding set.

### bind <input> jog-reverse <value>

NAME

bind <input> jog-reverse <value> - Bind a controller input to a group action.

SYNOPSIS

bind <input> jog-reverse <value>

DESCRIPTION

Bind a controller input to a group action. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

PARAMETERS

- <input>: Input name (button/axis name) for a controller.

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`bind <input> jog-reverse <value>`

EXAMPLE OUTPUT
Binding set.

### no bind

NAME

no bind - Remove all bindings from the current group.

SYNOPSIS

no bind

DESCRIPTION

Remove all bindings from the current group. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`no bind`

EXAMPLE OUTPUT
Bindings cleared.

### enable

NAME

enable - Enable or disable the current group.

SYNOPSIS

enable

DESCRIPTION

Enable or disable the current group. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`enable`

EXAMPLE OUTPUT
OK

### disable

NAME

disable - Enable or disable the current group.

SYNOPSIS

disable

DESCRIPTION

Enable or disable the current group. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`disable`

EXAMPLE OUTPUT
OK

### run test

NAME

run test - Run a test by name or the group test if defined.

SYNOPSIS

run test

DESCRIPTION

Run a test by name or the group test if defined. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`run test`

EXAMPLE OUTPUT
Test started.

### run test <name>

NAME

run test <name> - Run a test by name or the group test if defined.

SYNOPSIS

run test <name>

DESCRIPTION

Run a test by name or the group test if defined. This command is valid in Group Mode (`bridge(config-...-group-...)#`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`run test <name>`

EXAMPLE OUTPUT
Test started.

### write tests <path>

NAME

write tests <path> - Deprecated: export standalone tests JSON (legacy).

SYNOPSIS

write tests <path>

DESCRIPTION

Deprecated export. Writes the current tests to a standalone JSON file. Exit to Config Mode first, then use `save unified-config <path>` to persist tests in `bringup_system.json` under `bridgeConfig.byProfile.<profile>.tests`.

PARAMETERS

- <path>: Filesystem path to a JSON file.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`save unified-config data/bringup_system.json`

EXAMPLE OUTPUT
Wrote tests.

### show

NAME

show - Execute the command.

SYNOPSIS

show

DESCRIPTION

Execute the command. This command is valid in Device Mode (`bridge(config-device-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show`

EXAMPLE OUTPUT
SOURCE: local
<summary>

### show <target> [robot|local|both] [--json] [--pretty]

NAME

show <target> [robot|local|both] [--json] [--pretty] - Display the requested information.

SYNOPSIS

show <target> [robot|local|both] [--json] [--pretty]

DESCRIPTION

Display the requested information. This command is valid in Device Mode (`bridge(config-device-...)#`).

PARAMETERS

- <target>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show <target> [robot|local|both] [--json] [--pretty]`

EXAMPLE OUTPUT
SOURCE: local
{...json...}

### set <field> <value>

NAME

set <field> <value> - Set a field in the current device context.

SYNOPSIS

set <field> <value>

DESCRIPTION

Set a field in the current device context. This command is valid in Device Mode (`bridge(config-device-...)#`).

PARAMETERS

- <field>: Field name to update in the current object.

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`set <field> <value>`

EXAMPLE OUTPUT
Updated.

### no <field>

NAME

no <field> - Clear a field in the current device context.

SYNOPSIS

no <field>

DESCRIPTION

Clear a field in the current device context. This command is valid in Device Mode (`bridge(config-device-...)#`).

PARAMETERS

- <field>: Field name to update in the current object.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`no <field>`

EXAMPLE OUTPUT
Cleared.

### write tests <path>

NAME

write tests <path> - Deprecated: export standalone tests JSON (legacy).

SYNOPSIS

write tests <path>

DESCRIPTION

Deprecated export. Writes the current tests to a standalone JSON file. Exit to Config Mode first, then use `save unified-config <path>` to persist tests in `bringup_system.json` under `bridgeConfig.byProfile.<profile>.tests`.

PARAMETERS

- <path>: Filesystem path to a JSON file.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`save unified-config data/bringup_system.json`

EXAMPLE OUTPUT
Wrote tests.

### show

NAME

show - Execute the command.

SYNOPSIS

show

DESCRIPTION

Execute the command. This command is valid in Test Mode (`bridge(config-test-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`show`

EXAMPLE OUTPUT
SOURCE: local
<summary>

### type joystick

NAME

type joystick - Set the test type for the current test.

SYNOPSIS

type joystick

DESCRIPTION

Set the test type for the current test. This command is valid in Test Mode (`bridge(config-test-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`type joystick`

EXAMPLE OUTPUT
Test type set.

### type button

NAME

type button - Set the test type for the current test.

SYNOPSIS

type button

DESCRIPTION

Set the test type for the current test. This command is valid in Test Mode (`bridge(config-test-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`type button`

EXAMPLE OUTPUT
Test type set.

### type composite

NAME

type composite - Set the test type for the current test.

SYNOPSIS

type composite

DESCRIPTION

Set the test type for the current test. This command is valid in Test Mode (`bridge(config-test-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`type composite`

EXAMPLE OUTPUT
Test type set.

### type deadbandSweep

NAME

type deadbandSweep - Set the test type for the current test.

SYNOPSIS

type deadbandSweep

DESCRIPTION

Set the test type for the current test. This command is valid in Test Mode (`bridge(config-test-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`type deadbandSweep`

EXAMPLE OUTPUT
Test type set.

### type deviceAction

NAME

type deviceAction - Set the test type for the current test.

SYNOPSIS

type deviceAction

DESCRIPTION

Set the test type for the current test. This command is valid in Test Mode (`bridge(config-test-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`type deviceAction`

EXAMPLE OUTPUT
Test type set.

### device add <name>

NAME

device add <name> - Enter device configuration mode for the named device, creating it if needed.

SYNOPSIS

device add <name>

DESCRIPTION

Enter device configuration mode for the named device, creating it if needed. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`device "SPARKMAX/NEO 25"`

EXAMPLE OUTPUT
Device updated.

### no device <name>

NAME

no device <name> - Remove a device from the current group.

SYNOPSIS

no device <name>

DESCRIPTION

Remove a device from the current group. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <name>: Identifier for a named entity (group, device, test, profile) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`no device <name>`

EXAMPLE OUTPUT
Device removed.

### inputSource <controller>.<inputId>

NAME

inputSource <controller>.<inputId> - Set the input source for a button/composite test.

SYNOPSIS

inputSource <controller>.<inputId>

DESCRIPTION

Set the input source for a button/composite test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <controller>: Controller label (as defined in bindings).

- <inputId>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`inputSource <controller>.<inputId>`

EXAMPLE OUTPUT
Updated.

### deadband <value>

NAME

deadband <value> - Set the joystick deadband for the current test.

SYNOPSIS

deadband <value>

DESCRIPTION

Set the joystick deadband for the current test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`deadband <value>`

EXAMPLE OUTPUT
Updated.

### duty <value>

NAME

duty <value> - Set fixed output duty for button/composite tests.

SYNOPSIS

duty <value>

DESCRIPTION

Set fixed output duty for button/composite tests. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`duty <value>`

EXAMPLE OUTPUT
Updated.

### action toggle_led|set_color

NAME

action toggle_led|set_color - Set the device action for a deviceAction test.

SYNOPSIS

action toggle_led|set_color

DESCRIPTION

Set the device action for a deviceAction test. This command is valid in Test Mode (`bridge(config-test-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`action toggle_led`

EXAMPLE OUTPUT
Updated.

### color #RRGGBB

NAME

color #RRGGBB - Set parameters for a deviceAction test.

SYNOPSIS

color #RRGGBB

DESCRIPTION

Set parameters for a deviceAction test. This command is valid in Test Mode (`bridge(config-test-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`color #FF00FF`

EXAMPLE OUTPUT
Updated.

### pattern solid

NAME

pattern solid - Set parameters for a deviceAction test.

SYNOPSIS

pattern solid

DESCRIPTION

Set parameters for a deviceAction test. This command is valid in Test Mode (`bridge(config-test-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`pattern solid`

EXAMPLE OUTPUT
Updated.

### brightness <value>

NAME

brightness <value> - Set parameters for a deviceAction test.

SYNOPSIS

brightness <value>

DESCRIPTION

Set parameters for a deviceAction test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`brightness <value>`

EXAMPLE OUTPUT
Updated.

### duration <seconds>

NAME

duration <seconds> - Set parameters for a deviceAction test.

SYNOPSIS

duration <seconds>

DESCRIPTION

Set parameters for a deviceAction test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <seconds>: Time value in seconds.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`duration 2.0`

EXAMPLE OUTPUT
Updated.

### rotation limit <value>

NAME

rotation limit <value> - Configure rotation termination or encoder source for the test.

SYNOPSIS

rotation limit <value>

DESCRIPTION

Configure rotation termination or encoder source for the test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`rotation limit <value>`

EXAMPLE OUTPUT
Updated.

### rotation encoderKey <label|internal>

NAME

rotation encoderKey <label|internal> - Configure rotation termination or encoder source for the test.

SYNOPSIS

rotation encoderKey <label|internal>

DESCRIPTION

Configure rotation termination or encoder source for the test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <label|internal>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`rotation encoderKey <label|internal>`

EXAMPLE OUTPUT
Updated.

### rotation encoderSource <internal|sparkmax_alt|external>

NAME

rotation encoderSource <internal|sparkmax_alt|external> - Configure rotation termination or encoder source for the test.

SYNOPSIS

rotation encoderSource <internal|sparkmax_alt|external>

DESCRIPTION

Configure rotation termination or encoder source for the test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <internal|sparkmax_alt|external>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`rotation encoderSource <internal|sparkmax_alt|external>`

EXAMPLE OUTPUT
Updated.

### rotation encoderMotorIndex <index>

NAME

rotation encoderMotorIndex <index> - Configure rotation termination or encoder source for the test.

SYNOPSIS

rotation encoderMotorIndex <index>

DESCRIPTION

Configure rotation termination or encoder source for the test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <index>: Zero-based index into the current list of bindings/axes.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`rotation encoderMotorIndex <index>`

EXAMPLE OUTPUT
Updated.

### rotation encoderCountsPerRev <value>

NAME

rotation encoderCountsPerRev <value> - Configure rotation termination or encoder source for the test.

SYNOPSIS

rotation encoderCountsPerRev <value>

DESCRIPTION

Configure rotation termination or encoder source for the test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`rotation encoderCountsPerRev <value>`

EXAMPLE OUTPUT
Updated.

### time timeout <seconds>

NAME

time timeout <seconds> - Configure time-based termination behavior.

SYNOPSIS

time timeout <seconds>

DESCRIPTION

Configure time-based termination behavior. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <seconds>: Time value in seconds.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`time timeout <seconds>`

EXAMPLE OUTPUT
Updated.

### time onTimeout <pass|fail>

NAME

time onTimeout <pass|fail> - Configure time-based termination behavior.

SYNOPSIS

time onTimeout <pass|fail>

DESCRIPTION

Configure time-based termination behavior. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <pass|fail>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`time onTimeout <pass|fail>`

EXAMPLE OUTPUT
Updated.

### hold onRelease <pass|fail>

NAME

hold onRelease <pass|fail> - Configure hold behavior for a hold termination.

SYNOPSIS

hold onRelease <pass|fail>

DESCRIPTION

Configure hold behavior for a hold termination. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <pass|fail>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`hold onRelease <pass|fail>`

EXAMPLE OUTPUT
Updated.

### limitswitch onHit <pass|fail>

NAME

limitswitch onHit <pass|fail> - Configure limit switch termination behavior.

SYNOPSIS

limitswitch onHit <pass|fail>

DESCRIPTION

Configure limit switch termination behavior. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <pass|fail>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`limitswitch onHit <pass|fail>`

EXAMPLE OUTPUT
Updated.

### limitswitch id <id>

NAME

limitswitch id <id> - Configure limit switch termination behavior.

SYNOPSIS

limitswitch id <id>

DESCRIPTION

Configure limit switch termination behavior. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <id>: Numeric identifier (controller id, device id, or limit switch id) depending on command context.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`limitswitch id <id>`

EXAMPLE OUTPUT
Updated.

### deadbandSweep startDuty <value>

NAME

deadbandSweep startDuty <value> - Configure parameters for a deadband sweep test.

SYNOPSIS

deadbandSweep startDuty <value>

DESCRIPTION

Configure parameters for a deadband sweep test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`deadbandSweep startDuty <value>`

EXAMPLE OUTPUT
Updated.

### deadbandSweep maxDuty <value>

NAME

deadbandSweep maxDuty <value> - Configure parameters for a deadband sweep test.

SYNOPSIS

deadbandSweep maxDuty <value>

DESCRIPTION

Configure parameters for a deadband sweep test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`deadbandSweep maxDuty <value>`

EXAMPLE OUTPUT
Updated.

### deadbandSweep stepDuty <value>

NAME

deadbandSweep stepDuty <value> - Configure parameters for a deadband sweep test.

SYNOPSIS

deadbandSweep stepDuty <value>

DESCRIPTION

Configure parameters for a deadband sweep test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`deadbandSweep stepDuty <value>`

EXAMPLE OUTPUT
Updated.

### deadbandSweep stepHoldSec <value>

NAME

deadbandSweep stepHoldSec <value> - Configure parameters for a deadband sweep test.

SYNOPSIS

deadbandSweep stepHoldSec <value>

DESCRIPTION

Configure parameters for a deadband sweep test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`deadbandSweep stepHoldSec <value>`

EXAMPLE OUTPUT
Updated.

### deadbandSweep motionThresholdRot <value>

NAME

deadbandSweep motionThresholdRot <value> - Configure parameters for a deadband sweep test.

SYNOPSIS

deadbandSweep motionThresholdRot <value>

DESCRIPTION

Configure parameters for a deadband sweep test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`deadbandSweep motionThresholdRot <value>`

EXAMPLE OUTPUT
Updated.

### deadbandSweep requiredSamples <value>

NAME

deadbandSweep requiredSamples <value> - Configure parameters for a deadband sweep test.

SYNOPSIS

deadbandSweep requiredSamples <value>

DESCRIPTION

Configure parameters for a deadband sweep test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`deadbandSweep requiredSamples <value>`

EXAMPLE OUTPUT
Updated.

### deadbandSweep encoderKey <label|internal>

NAME

deadbandSweep encoderKey <label|internal> - Configure parameters for a deadband sweep test.

SYNOPSIS

deadbandSweep encoderKey <label|internal>

DESCRIPTION

Configure parameters for a deadband sweep test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <label|internal>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`deadbandSweep encoderKey <label|internal>`

EXAMPLE OUTPUT
Updated.

### deadbandSweep encoderSource <internal|sparkmax_alt|external>

NAME

deadbandSweep encoderSource <internal|sparkmax_alt|external> - Configure parameters for a deadband sweep test.

SYNOPSIS

deadbandSweep encoderSource <internal|sparkmax_alt|external>

DESCRIPTION

Configure parameters for a deadband sweep test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <internal|sparkmax_alt|external>: Command parameter.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`deadbandSweep encoderSource <internal|sparkmax_alt|external>`

EXAMPLE OUTPUT
Updated.

### deadbandSweep encoderMotorIndex <index>

NAME

deadbandSweep encoderMotorIndex <index> - Configure parameters for a deadband sweep test.

SYNOPSIS

deadbandSweep encoderMotorIndex <index>

DESCRIPTION

Configure parameters for a deadband sweep test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <index>: Zero-based index into the current list of bindings/axes.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`deadbandSweep encoderMotorIndex <index>`

EXAMPLE OUTPUT
Updated.

### deadbandSweep encoderCountsPerRev <value>

NAME

deadbandSweep encoderCountsPerRev <value> - Configure parameters for a deadband sweep test.

SYNOPSIS

deadbandSweep encoderCountsPerRev <value>

DESCRIPTION

Configure parameters for a deadband sweep test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`deadbandSweep encoderCountsPerRev <value>`

EXAMPLE OUTPUT
Updated.

### enabled true|false|on|off

NAME

enabled true|false|on|off - Enable or disable the current test.

SYNOPSIS

enabled true|false|on|off

DESCRIPTION

Enable or disable the current test. This command is valid in Test Mode (`bridge(config-test-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`enabled true|false|on|off`

EXAMPLE OUTPUT
Updated.

### termination hold

NAME

termination hold - Add or update a termination condition for the test.

SYNOPSIS

termination hold

DESCRIPTION

Add or update a termination condition for the test. This command is valid in Test Mode (`bridge(config-test-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`termination hold`

EXAMPLE OUTPUT
Updated.

### termination time <seconds>

NAME

termination time <seconds> - Add or update a termination condition for the test.

SYNOPSIS

termination time <seconds>

DESCRIPTION

Add or update a termination condition for the test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <seconds>: Time value in seconds.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`termination time 3.0`

EXAMPLE OUTPUT
Updated.

### termination rotation <value>

NAME

termination rotation <value> - Add or update a termination condition for the test.

SYNOPSIS

termination rotation <value>

DESCRIPTION

Add or update a termination condition for the test. This command is valid in Test Mode (`bridge(config-test-...)#`).

PARAMETERS

- <value>: Numeric or string value required by the command.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`termination rotation <value>`

EXAMPLE OUTPUT
Updated.

### termination limitswitch [id]

NAME

termination limitswitch [id] - Add or update a termination condition for the test.

SYNOPSIS

termination limitswitch [id]

DESCRIPTION

Add or update a termination condition for the test. This command is valid in Test Mode (`bridge(config-test-...)#`).

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`termination limitswitch [id]`

EXAMPLE OUTPUT
Updated.

### write tests <path>

NAME

write tests <path> - Deprecated: export standalone tests JSON (legacy).

SYNOPSIS

write tests <path>

DESCRIPTION

Deprecated export. Writes the current tests to a standalone JSON file. Exit to Config Mode first, then use `save unified-config <path>` to persist tests in `bringup_system.json` under `bridgeConfig.byProfile.<profile>.tests`.

PARAMETERS

- <path>: Filesystem path to a JSON file.

RETURNS

Prints output to the console or updates in-memory state; errors are reported inline.

SIDE EFFECTS

May update local in-memory config. If connected, some commands may send updates to the robot.

ERRORS

Reports invalid syntax, missing entities, or validation failures when applicable.

NOTES

You can suffix the command with `?` to see valid next arguments. Device references use labels.

EXAMPLE

`save unified-config data/bringup_system.json`

EXAMPLE OUTPUT
Wrote tests.



## Appendix A: Command List
## Command List
Purpose: Enumerate every supported command by mode. Every command may be suffixed with `?` to show valid next arguments.

### Common (All Modes)
- `help`
- `help <topic>`
- `ping`
- `exit`
- `end`
- `quit`

### Exec Mode (`bridge>`)
- `show status [robot|local|both] [--json] [--pretty]`
- `show groups [robot|local|both] [--json] [--pretty]`
- `show group <name> [robot|local|both] [--json] [--pretty]`
- `show devices [robot|local|both] [--json] [--pretty]`
- `show device <name> [local] [--json] [--pretty]`
- `show device-group <name> [robot|local|both] [--json] [--pretty]`
- `show bindings [robot|local|both] [--json] [--pretty]`
- `show selected-device [robot|local|both] [--json] [--pretty]`
- `show runtime-state [robot|local|both] [--json] [--pretty]`
- `show runtime-components [local] [--json] [--pretty]`
- `show config [robot|local|both] [--json] [--pretty]`
- `show config local-raw [local] [--json] [--pretty]`
- `show config dirty [local] [--json] [--pretty]`
- `show profiles [local] [--json] [--pretty]`
- `show profile [local] [--json] [--pretty]`
- `show profile <name> [local] [--json] [--pretty]`
- `show visibility [local] [--json] [--pretty]`
- `show visibility summary [local] [--json] [--pretty]`
- `show visibility <device> [local] [--json] [--pretty]`
- `show tests [--json] [--pretty]`
- `show test <name> [--json] [--pretty]`
- `tests select <name>`
- `tests toggle`
- `tests run`
- `tests run-all`
- `diagnose motor <label>`
- `diagnose device <label>`
- `configure terminal`
- `connect`
- `disconnect`

### Config Mode (`bridge(config-...)#`)
- `group <name>`
- `no group <name>`
- `profile <name>`
- `diagnose motor <label>`
- `diagnose device <label>`
- `selected-device <device>`
- `selected-mode on`
- `selected-mode off`
- `merge config <path>`
- `import config <path>`
- `export runtime-groups <path>`
- `export cli-script <path>`
- `save config <path>`
- `save local-config <path>`
- `save profiles <path>`
- `save unified-config <path>`
- `rename device <old> <new>`
- `device <name>`
- `device <name> set <field> <value>`
- `validate config [path]`
- `show <target> [robot|local|both] [--json] [--pretty]`
- `bindings show [controllers|bindings|axes] [--json] [--pretty]`
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
- `can-mappings show [manufacturers|device-types] [--json] [--pretty]`
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

### Group Mode (`bridge(config-...-group-...)#`)
- `show`
- `show members`
- `show binding`
- `show <target> [robot|local|both] [--json] [--pretty]`
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
- `write tests <path>`

### Device Mode (`bridge(config-device-...)#`)
- `show`
- `show <target> [robot|local|both] [--json] [--pretty]`
- `set <field> <value>`
- `no <field>`
- `write tests <path>`

### Test Mode (`bridge(config-test-...)#`)
- `show`
- `type joystick`
- `type button`
- `type composite`
- `type deadbandSweep`
- `type deviceAction`
- `device add <name>`
- `no device <name>`
- `inputSource <controller>.<inputId>`
- `deadband <value>`
- `duty <value>`
- `action toggle_led|set_color`
- `color #RRGGBB`
- `pattern solid`
- `brightness <value>`
- `duration <seconds>`
- `rotation limit <value>`
- `rotation encoderKey <label|internal>`
- `rotation encoderSource <internal|sparkmax_alt|external>`
- `rotation encoderMotorIndex <index>`
- `rotation encoderCountsPerRev <value>`
- `time timeout <seconds>`
- `time onTimeout <pass|fail>`
- `hold onRelease <pass|fail>`
- `limitswitch onHit <pass|fail>`
- `limitswitch id <id>`
- `deadbandSweep startDuty <value>`
- `deadbandSweep maxDuty <value>`
- `deadbandSweep stepDuty <value>`
- `deadbandSweep stepHoldSec <value>`
- `deadbandSweep motionThresholdRot <value>`
- `deadbandSweep requiredSamples <value>`
- `deadbandSweep encoderKey <label|internal>`
- `deadbandSweep encoderSource <internal|sparkmax_alt|external>`
- `deadbandSweep encoderMotorIndex <index>`
- `deadbandSweep encoderCountsPerRev <value>`
- `enabled true|false|on|off`
- `termination hold`
- `termination time <seconds>`
- `termination rotation <value>`
- `termination limitswitch [id]`
- `write tests <path>`
