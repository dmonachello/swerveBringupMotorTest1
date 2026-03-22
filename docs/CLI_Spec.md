Add an interactive Cisco-style CLI mode to the bridge app. This is not a separate tool. It is a second operator surface inside the bridge app, alongside the Windows UI. The CLI and GUI must share the same core command/send/receive logic and runtime state handling. Do not duplicate business logic.

Goal

Provide a live, prompt-based operator console for the bridge app with:

contextual prompts

hierarchical modes

command parsing

shared bridge command execution

shared response parsing

scriptable batch operation

no prompt noise in batch mode


Architecture

Implement the CLI as a front end over shared bridge core logic.

Required layers:

bridge core/session layer

connect/disconnect

send command

receive ACK/OUT

collect streamed output

maintain latest runtime state snapshot


shared operations layer

create/select/delete/rename group

add/remove device

enable/disable group

enable/disable/toggle member

bind/unbind group

selected-device operations

show/query operations

merge/import/export operations


GUI front end

must call the shared operations layer


CLI front end

must call the same shared operations layer



Do not implement separate command formatting or response interpretation logic in the CLI.

CLI style

Use a Cisco-like CLI style with:

hierarchical modes

context-sensitive prompts

show ... inspection commands

configure terminal to enter config mode

group <name> to enter or create group config mode

no ... for removal/clearing

exit to go up one level

end to return to exec mode


Do not implement Cisco privilege levels or loose abbreviation parsing. Keep this version explicit and predictable.

Modes

Support these modes:

1. exec mode Prompt: bridge>



Purpose:

inspection

connection/control status

entering config mode


2. config mode Prompt: bridge(config)#



Purpose:

structural edits

entering group config mode

selected-device control setup

config merge/import/export operations


3. group config mode Prompt: bridge(config-group-<groupName>)#



Purpose:

edit one group

add/remove devices

enable/disable members

bind/unbind group control

enable/disable group

run tests on current group


4. batch mode This is a non-interactive execution mode, not a fourth prompt hierarchy level in normal interactive use. It may be entered either:



from startup, e.g. bridge.py --batch

or via script execution mode


Batch mode requirements:

no prompts

deterministic behavior

operations that would prompt in interactive mode must follow a configured batch conflict policy


Batch conflict policy

Support batch conflict handling for operations that would otherwise prompt, especially when moving a device from one group to another.

Provide a batch conflict policy with at least:

error

move


Meaning:

error: emit warning/error and do not perform the action

move: emit warning and perform the move automatically


Default batch policy:

error


Allow configuration by startup option and/or explicit CLI setting in batch context.

Do not require per-command --force flags. Use batch mode and batch policy instead.

Interactive prompting

In normal interactive CLI mode, operations that would silently alter ownership or delete structure must warn and prompt y/n.

Example cases:

adding a device to a new group when it already belongs to another group

deleting a group

clearing a group

destructive merge/import cases if applicable


Requirements:

default selection should be effectively “no”

if user declines, state must remain unchanged

moves must be atomic when accepted


No prompting is allowed in batch mode.

Command grammar style

The CLI is mode-based. Commands are interpreted according to current mode.

Common commands

Available where sensible:

exit

end

help

ping

quit


Exec mode commands

Support:

show status

show groups

show group <name>

show devices

show device <name>

show bindings

show selected-device

show runtime-state

configure terminal

connect

disconnect


Config mode commands

Support:

all appropriate show ... commands

group <name>

if group exists, enter its group config mode

if group does not exist, create it and enter its group config mode


no group <name>

selected-device <device>

selected-mode on

selected-mode off

merge config <file>

import config <file>

export runtime-groups <file>

save config <file>


Group config mode commands

Current group is implied by the mode.

Support:

show

show members

show binding

add device <device>

no device <device>

member <device> enable

member <device> disable

member <device> toggle

bind <input> analog

bind <input> hold <value>

bind <input> toggle <value>

bind <input> jog-forward <value>

bind <input> jog-reverse <value>

no bind

enable

disable

run test

run test <name>


Control identifiers

Use normalized control identifiers in the CLI. Examples:

driver.left.y

driver.right.y

operator.left.y

operator.right.y

driver.a

driver.b

driver.x

driver.y

driver.lb

driver.rb

operator.a

operator.b

operator.x

operator.y

operator.lb

operator.rb

ui.slider1

ui.slider2

ui.button1

ui.button2


These identifiers must map into the shared normalized input abstraction already planned for group bindings.

Binding behavior rules

Support these binding behaviors:

analog

hold

toggle

jog-forward

jog-reverse


Rules:

analog bindings use live analog value from axis/slider and do not take a fixed numeric output value

button-based bindings must explicitly specify a fixed output value

fixed output value belongs to the binding, not the device and not the group membership


Lock in these semantics:

hold: output = configured value while pressed, else 0

toggle: each press toggles configured value on/off

jog-forward: output = +configured value while pressed, else 0

jog-reverse: output = -configured value while pressed, else 0


Validation:

bind <input> analog is valid only for analog-capable inputs

bind <input> hold|toggle|jog-forward|jog-reverse <value> requires a numeric value

invalid combinations must produce clear errors


Device ownership rule

A device may belong to only one runtime group at a time.

When adding a device to a group:

if device is not already in any group, add normally

if device is already in another group:

interactive mode: warn and prompt y/n before moving

batch mode with policy error: warn/error and do not move

batch mode with policy move: warn and move automatically



Do not allow a device to belong to multiple groups simultaneously.

Per-member enable rule

A device may remain in a group but be disabled within that group.

CLI must support:

member <device> enable

member <device> disable

member <device> toggle


This affects participation in control, not membership.

Group execution is not implemented in the CLI itself, but CLI commands must manipulate the shared state used by execution logic.

Selected-device override support

CLI must expose selected-device mode control.

Support:

selected-device <device> in config mode

selected-mode on

selected-mode off

show selected-device state via show selected-device


This must operate through the shared bridge operations layer, not bespoke CLI logic.

Response handling

CLI must use the same command send/receive and response parsing logic as the GUI.

CLI must display:

short command response flow

streamed output when applicable


Suggested display tags:

CMD

ACK

OUT

CONSOLE


Do not invent a separate protocol or output path for CLI.

Help system

Add a command help system.

Minimum requirements:

help

command-specific usage help

clear usage errors


Preferred later enhancement:

? support for next-token help and contextual help


Do not block initial implementation on full ? support. help is enough for v1.

Error behavior

Error messages must be specific.

Good examples:

unknown device FL_DRIEV; did you mean FL_DRIVE?

hold binding requires an output value

no current group selected

input driver.left.y is not valid for toggle binding

device FL_DRIVE already belongs to group swerve_drive


Bad example:

syntax error


Batch/script support

Support non-interactive execution.

Required capabilities:

run a script file

optional single-command execution if easy

no prompts in batch/script mode

deterministic conflict policy


Examples of desired use:

bridge.py --batch --script setup.txt

bridge.py --batch --conflict-policy move --script setup.txt


Do not create a separate scripting language. Scripts are plain CLI command lines.

Batch/script commands may still use Cisco-style mode navigation:

configure terminal

group swerve_drive

add device FL_DRIVE

bind driver.left.y analog

enable

end


Scriptability requirements

To make the Cisco-style CLI usable in scripts:

support batch mode

support deterministic conflict policy

avoid hanging on prompts

provide structured output option for inspection commands


Structured output

Add structured output support for inspection commands, at least for scripting/batch use.

Support a machine-readable output mode such as JSON for:

show status

show groups

show group <name>

show devices

show device <name>

show bindings

show selected-device

show runtime-state


Do not require scripts to parse human-formatted output.

Non-goals

Do not implement:

a separate standalone CLI app for the bridge

privilege levels

fuzzy abbreviations like Cisco IOS

drag-and-drop or fancy terminal UI

a second scripting language

duplicate bridge logic in the CLI

per-command --force flag clutter as the primary non-interactive mechanism


Implementation constraints

the CLI is part of the bridge app

CLI and GUI must share common send/receive routines

CLI and GUI must share common command operations

preserve the existing bridge command path

keep the parser simple and maintainable

a hand-written mode-aware dispatcher is preferred over overbuilt parser-generator complexity unless there is a compelling reason otherwise


Suggested implementation approach

1. Build shared bridge session/core APIs first



connection/session handling

send/receive

response parsing

state snapshot access


2. Build shared operations layer



group operations

member operations

binding operations

selected-device operations

show/query operations

merge/import/export operations


3. Build CLI shell on top



prompt loop

mode stack/state

parser/dispatcher

help

batch/script execution


4. Keep GUI wired to the same operations



Prompt examples

bridge>

bridge(config)#

bridge(config-group-swerve_drive)#


Example interactive session

bridge> show groups
bridge> configure terminal
bridge(config)# group swerve_drive
bridge(config-group-swerve_drive)# add device FL_DRIVE
bridge(config-group-swerve_drive)# add device FR_DRIVE
bridge(config-group-swerve_drive)# member FR_DRIVE disable
bridge(config-group-swerve_drive)# bind driver.left.y analog
bridge(config-group-swerve_drive)# enable
bridge(config-group-swerve_drive)# exit
bridge(config)# selected-device FL_DRIVE
bridge(config)# selected-mode on
bridge(config)# end
bridge> show group swerve_drive

Example batch script

configure terminal
group swerve_drive
add device FL_DRIVE
add device FR_DRIVE
bind driver.left.y analog
enable
end
show group swerve_drive

Summary intent

Implement a Cisco-style, mode-based CLI inside the bridge app that acts as a live alternate operator surface to the GUI, shares all core bridge logic with the GUI, supports batch/script execution without prompts, and provides structured output for automation.
