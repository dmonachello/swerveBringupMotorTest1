Purpose: Single reference for the Bridge CLI feature, including requirements, restrictions, design, and implementation notes.

## Summary

Purpose: Describe the feature at a high level.

Add a Cisco-style CLI mode inside the bridge app. The CLI is a second operator surface alongside the GUI and must share the same core session, runtime state, and business logic. The CLI is a front end only, not a separate system.

## Goals

Purpose: Define the operator outcomes.

- Contextual prompts and hierarchical modes.
- Shared command execution and response parsing with the GUI.
- Scriptable batch operation with deterministic behavior.
- Streaming output to console (no buffering).
- `--json` output for show commands (one JSON blob per command). Use `--pretty` for pretty JSON output.

## Host vs Robot Context

Purpose: Ensure operators do not confuse host-local editing context with robot runtime state.

Definitions:

- Host context: the CLI's local working state loaded from disk (active profile for editing, active test set for authoring, dirty flags, file paths).
- Robot context: the roboRIO runtime state over TCP (active profile, selected test, runAllActive, etc.).

Rules:

- Host-only commands MUST NOT change robot state as a side effect.
- Robot state MUST change only via explicit robot-targeting commands over TCP.

Examples:

- `profile <name>` changes host context only.
- `profiles activate <name>` changes robot active profile (TCP).
- `show workspace` is host-only; `show status robot` inspects robot state.

## Non-Goals

Purpose: Clarify what is out of scope.

- Separate standalone bridge implementation.
- Privilege levels.

- Fuzzy abbreviations.
- DSL or scripting language.
- Per-command force flags.

## Restrictions

Purpose: Hard rules that must not be violated.

- CLI must not duplicate send/receive logic.
- CLI must not duplicate response parsing.
- CLI must not duplicate runtime state logic.
- CLI must not implement its own bridge.
- GUI and CLI must share the same session and operations layers.

## No-Regression Guarantee

Purpose: Ensure current behavior remains unchanged when CLI/groups are unused.

- Existing GUI behavior remains unchanged.
- Existing TCP command names and semantics remain unchanged.
- Existing NetworkTables keys remain unchanged.
- CLI is additive only.

## Architecture

Purpose: Define required layers and responsibilities.

### Bridge Core / Session Layer

Purpose: Centralize connect/send/receive and runtime state.

- Connect/disconnect.
- Send commands.
- Receive ACK/OUT.
- Stream output.
- Maintain runtime state snapshot (merge TCP state + NT state).

### Shared Operations Layer

Purpose: Centralize domain logic for all front ends.

- Group operations.
- Device membership operations.
- Binding operations.
- Selected-device operations.
- Show/query operations.
- Merge/import/export operations (local config files on Windows).
- Conflict policy handling.

### CLI Module

Purpose: Provide a Cisco-style operator surface only.

- Prompt loop and mode handling.
- Command parsing/dispatch.
- Batch/script execution.
- Invokes shared operations only.

### Parser Generation

Purpose: Keep the CLI grammar and parser constants in sync with the EBNF spec.

- Canonical EBNF: `tools/can_nt/bridge_cli_ebnf.txt`
- Metadata sidecar: `tools/can_nt/bridge_cli_grammar_meta.json`
- Generator: `python tools\can_nt\gen_bridge_cli_parser.py`
- Generated outputs: `tools/can_nt/bridge_cli_grammar_gen.py` and `tools/can_nt/bridge_cli_constants_gen.py`

### EBNF Rationale

Purpose: Justify the choice of EBNF for the CLI grammar.

- EBNF is compact and human-readable, making command syntax reviewable in diffs.
- The grammar is tool-agnostic, avoiding lock-in to a single parser library.
- It provides a stable single source of truth for code generation and tests.
- Complex verbs (`bindings`, `can-mappings`, `tests`) route through explicit subcommand productions.
- The language fits the problem size: a small command DSL with clear modes.
- The EBNF is the heart of the CLI: defining the language shapes how the CLI functions.

Tradeoffs:

- EBNF alone cannot express runtime validation or mode transitions.
- Some behavior (errors, labels) still lives in metadata.


### GUI Front End

Purpose: Remain a thin front end.

- Invokes shared operations only.

## Modes

Purpose: Define CLI contexts and prompts.

### Mode Transitions

Purpose: Show how operators enter and exit each mode.

- Exec -> Config: `configure terminal`
- Config -> Group: `group <name>`
- Config -> Device: `device <name>`
- Group -> Config: `exit`
- Device -> Config: `exit`
- Any Mode -> Exec: `end`
- Exec -> Exit CLI: `exit` or `quit`

### Exec

Prompt: `bridge>` or `bridge-profile-<name>>` when a profile is active/default.

Purpose:

- inspection
- connection status
- entry to config mode

### Config

Prompt: `bridge(config-profile-<name>)#`

Purpose:

- structural edits
- group creation/selection
- selected device control
- merge/import/export
- profile selection (`profile <name>`)

### Group Config

Prompt: `bridge(config-profile-<name>-group-<name>)#`

Purpose:

- manage a single group
- membership and bindings
- enable/disable
- run tests

### Device Config

Prompt: `bridge(config-device-<name>)#`

Purpose:

- edit device metadata
- inspect device fields

### Test Config

Prompt: `bridge(config-test-<name>)#`

Purpose:

- create and edit bringup tests
- edit bindings and termination settings

### Batch

Purpose: Run scripts deterministically without prompts.

- Invoked via `bridge.py --batch --script <file>`
- Fails if no script file is provided.
- No prompts.
- Uses conflict policy.

## Output Handling

Purpose: Specify streaming and formatting rules.

- All output streams directly to console.
- ACK/OUT/CONSOLE are printed as received.
- `--json` prints one JSON blob per command. Add `--pretty` for formatted JSON.
- No buffering unless required for formatting.

## Conflict Policy

Purpose: Define device ownership handling.

Policies:

- `error` (default): warn, do not move.
- `move`: warn, automatically move.

Interactive prompts:

- moving devices between groups
- deleting groups
- clearing groups

Rules:

- default answer is no
- operations must be atomic

Batch mode:

- no prompts allowed

## Command Set

Purpose: Define CLI commands by mode.

Common:

- `exit`
- `end`
- `help`
- `ping`
- `tiu on`
- `tiu off`
- `echo on`
- `echo off`
- `quit`
- Windows EOF: Ctrl+Z then Enter behaves like `exit` (Ctrl+D on POSIX shells).
- Inline help: a trailing `?` shows valid next arguments (e.g., `show groups ?`).
- For bounded values, `?` prints the full inline list and any numeric ranges.

Exec:

- `show status [robot|local|both]`
- `show active [robot|local|both]`
- `show groups [robot|local|both]`
- `show group <name> [robot|local|both]`
- `show devices [robot|local|both]`
- `show device <name> [local]`
- `show device-group <name> [robot|local|both]`
- `show instantiated [robot|local|both]`
- `show faults [robot|local|both]`
- `show signals [local]`
- `show signal <name> [local]`
- `show bindings [robot|local|both]`
- `show selected-device [robot|local|both]`
- `show runtime-state [robot|local|both]`
- `show runtime-components [local]`
- `show config [robot|local|both]` (alias for runtime-state)
- `show config local-raw [local]` (raw bridgeConfig.byProfile)
- `show config dirty [local]` (local unsaved flags)
- `show profiles [local]` (profile names from bringup_system.json)
- `show profile [local]` (active/default profile summary)
- `show profile <name> [local]` (device labels for a profile)
- `show topology [local]` (diagram nodes for the active profile)
- `show topology neighbors [local]` (neighbor ports for the active profile)
- `show visibility [local]` (multi-analyzer visibility matrix)
- `show visibility summary [local]` (visibility counts)
- `show visibility <device> [local]` (per-source visibility details)
- `show tests [--json] [--pretty]`
- `show test <name> [--json] [--pretty]`
- `show workspace [--json] [--pretty]`
- `show controllers [--json] [--pretty]`
- `bindings show [controllers|bindings|axes] [--all] [--json] [--pretty]`
- `configure terminal`
- `connect`
- `disconnect`

Config:

- `group <name>`
- `no group <name>`
- `profile <name>`
- `selected-device <device>`
- `selected-mode on`
- `selected-mode off`
- `merge config <bringup_system.json>`
- `import config <bringup_system.json>`
- `export runtime-groups <bridgeConfig.json>`
- `export cli-script <path>`
- `save runtime-groups <runtime_groups.json>`
- `save all [--prompt]`
- `save sources`
- `save bridge-config <path>` (local-only; writes groups-only when profiles are loaded)
- `save runtime-groups <path>` (robot snapshot; writes current runtime groups)
- `save profiles <path>` (profiles-only; preserves bridgeConfig)
- `save config <path>`
- `revert`
- `rename device <old> <new>` (local-only; updates profiles when loaded)
- `device <name>`
- `device <name> set <field> <value>`
- `topology neighbor-ports set <node> <port> <neighbor> <neighborPort>`
- `topology neighbor-ports delete <node> <port>`
- `topology neighbor-ports clear <node>`
- `topology neighbor-auto all [label1,label2]`
- `topology neighbor-auto node <label>`
  - CANnect device links populate `next/branch1/branch2` neighbor ports.
  - If label1,label2 is provided, only those labels are updated; omit to update all nodes.
  - Label lists are comma-separated; wrap in quotes if spaces are present.
- `validate config [path] [--all]`
- `validate profiles [robot|local] [--active]`
- `validate tests [--active-set]`
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
- `show <...>` (same targets as exec)
- `write tests <path>`
- `test set <name>`
- `test create <name>`
- `test delete <name>`
- `test <name>` (edit existing)

Show Output Notes:

- `show group` text output includes members and bindings.
- `show devices` (local) lists the full profile-derived device inventory, not only group members.
- `show device` returns the full device definition from bringup_system.json (local only).
- `show device-group` returns the device’s group membership/usage info.
- The CLI auto-imports `src/main/deploy/bringup_system.json` on startup when present (replaces groups).
- merge config is only allowed when the incoming profiles hash matches the loaded profiles; otherwise use import config.
- `validate config [path]`

Group:

- `show`
- `show members`
- `show binding`
- `show <target> [--json] [--pretty]`
- `add device <device>`
- `no device <device>`
- `member <device> enable`
- `member <device> disable`
- `member <device> toggle`
- `bind list`
- `bind explain <binding>`
- `bind test <binding>`
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

Device:

- `show`
- `show <target> [--json] [--pretty]`
- `set <field> <value>`
- `no <field>`
- `write tests <path>`

Test:

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

## Control Identifiers

Purpose: Define allowed input names.

Examples:

- `controller0.leftY`
- `controller0.rightY`
- `controller0.A`
- `controller0.B`
- `controller0.X`
- `controller0.Y`
- `controller0.LB`
- `controller0.RB`
- `controller1.leftY`
- `controller1.rightY`
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

Purpose: Define supported binding behaviors.

Behaviors:

- `analog`
- `hold`
- `toggle`
- `jog-forward`
- `jog-reverse`

Rules:

- `analog` uses live input value.
- button bindings require a value.
- value belongs to the binding, not the device or group.

Semantics:

- `hold`: output = value while pressed, else 0
- `toggle`: toggles value on/off
- `jog-forward`: +value while pressed
- `jog-reverse`: -value while pressed

## Device Ownership Rule

Purpose: Enforce one group per device.

Interactive:

- warn and prompt

Batch:

- `error` or `move` policy

Multiple group membership is not allowed.

## Per-Member Enable

Purpose: Control participation without changing membership.

Commands:

- `member <device> enable`
- `member <device> disable`
- `member <device> toggle`

## Selected Device Mode

Purpose: Override group control for a single device.

Commands:

- `selected-device <device>`
- `selected-mode on`
- `selected-mode off`

Behavior:

- selected device overrides group control
- group output suppressed for that device

## Response Handling

Purpose: Define the response pipeline.

Pipeline:

- `CMD`
- `ACK`
- `OUT`
- `CONSOLE`

All output is printed directly.

## Show Sources

Purpose: Choose whether show commands read from robot, local config, or both.

Sources:

- `robot` (live from roboRIO)
- `local` (Windows-side config snapshot from merge/import)
- `both` (local first, then robot)

Defaults:

- robot if connected
- local if not connected

Output labeling:

- each show output includes a `SOURCE: <robot|local>` line before its payload.

## Structured Output

Purpose: Define JSON output rules.

Commands:

- `show status --json`
- `show groups --json`
- `show group <name> --json`
- `show devices --json`
- `show device <name> --json` (definition)
- `show device-group <name> --json` (usage)
- `show bindings --json`
- `show selected-device --json`
- `show runtime-state --json`
- `show runtime-components --json`
- `show config --json`
- `show config local-raw --json`
- `show config dirty --json`
- `show profiles --json`
- `show profile --json`
- `show tests --json`
- `show test <name> --json`
- `show visibility --json`

JSON is one blob per command.

## Shared Config (bringup_system.json)

Purpose: Store bridge group config inside the single shared data file.

- The shared file is `src/main/deploy/bringup_system.json`.
- The bridge CLI reads/writes a top-level `bridgeConfig` object.
- Other tools ignore unknown fields; `bridgeConfig` is optional.
- `data_hash` is computed from profiles + diagram; `bridgeConfig` changes do not affect it.

`bridgeConfig` object:

- `schemaVersion` (required, current: 2)
- `byProfile` (map of profile name -> per-profile config)
- `generatedAt` (optional timestamp)

Per-profile config object:

- `groups` (list of group objects)
- `selectedDevice` (selected-device override)

Group object:

- `name` (string, required)
- `enabled` (boolean, default true)
- `members` (list of `{device, enabled}`)
- `bindings` (list of `{input, kind, value?}`)

Device object (optional, local-only):

- `name` (string, required)

Example:
```
{
  "schema_version": 4,
  "data_version": "2026-03-20_143148",
  "data_hash": "...",
  "default_profile": "robot",
  "devices": [
    { "label": "FL_DRIVE", "deviceInterface": "CAN", "manufacturer": 5, "deviceType": 2, "id": 1 }
  ],
  "profiles": {
    "robot": { "devices": ["FL_DRIVE"] }
  },
  "bridgeConfig": {
    "schemaVersion": 2,
    "generatedAt": "2026-03-23T14:02:00Z",
    "byProfile": {
      "robot": {
        "groups": [
          {
            "name": "swerve_drive",
            "enabled": true,
            "members": [
              {"device": "FL_DRIVE", "enabled": true},
              {"device": "FR_DRIVE", "enabled": true}
            ],
            "bindings": [
              {"input": "controller0.leftY", "kind": "analog"}
            ]
          }
        ],
        "selectedDevice": {
          "device": "FL_DRIVE",
          "enabled": false
        }
      }
    }
  }
}
```

## Errors

Purpose: Require specific, actionable errors.

Examples:

- `unknown device FL_DRIEV, did you mean FL_DRIVE?`
- `hold binding requires value`
- `device already in group swerve_drive`

Avoid generic syntax errors.

## Robot Command Mapping (TCP UI)

Purpose: Map CLI commands to robot-side TCP command names and args.

Show:

- `show status` -> `showStatus`
- `show groups` -> `showGroups`
- `show group <name>` -> `showGroup` `{name}`
- `show devices` -> `showDevices`
- `show device-group <name>` -> `showDevice` `{name}`
- `show bindings` -> `showBindings`
- `show selected-device` -> `showSelectedDevice`
- `show runtime-state` -> `showRuntimeState`

Config:

- `group <name>` -> `groupCreate` `{name}`
- `no group <name>` -> `groupDelete` `{name, confirm}`
- `selected-device <device>` -> `selectedDeviceSet` `{name}`
- `selected-mode on|off` -> `selectedModeSet` `{enabled}`
- `merge config <file>` -> local: read config, emit group commands
- `import config <file>` -> local: delete groups, then emit group commands
- `export runtime-groups <file>` -> local: `showRuntimeState --json`, write file
- `save runtime-groups <file>` -> local: `showRuntimeState --json`, write file
- `save bridge-config <file>` -> local: write bridgeConfig-byProfile only
- `save profiles <file>` -> local: write bringup_system.json (profiles + diagram + bridgeConfig.byProfile)
- `save config <file>` -> local: write bringup_system.json (profiles + bridgeConfig.byProfile)
- `write tests <file>` -> local: deprecated alias for exporting a standalone tests JSON (legacy); use `save config <file>` to persist tests in bringup_system.json

Group:

- `add device <device>` -> `groupAddDevice` `{group, device, conflictPolicy, forceMove}`
- `no device <device>` -> `groupRemoveDevice` `{group, device}`
- `member <device> enable` -> `groupMemberEnable` `{group, device}`
- `member <device> disable` -> `groupMemberDisable` `{group, device}`
- `member <device> toggle` -> `groupMemberToggle` `{group, device}`
- `bind <input> analog` -> `groupBind` `{group, input, kind:"analog"}`
- `bind <input> hold <value>` -> `groupBind` `{group, input, kind:"hold", value}`
- `bind <input> toggle <value>` -> `groupBind` `{group, input, kind:"toggle", value}`
- `bind <input> jog-forward <value>` -> `groupBind` `{group, input, kind:"jog-forward", value}`
- `bind <input> jog-reverse <value>` -> `groupBind` `{group, input, kind:"jog-reverse", value}`
- `no bind` -> `groupUnbind` `{group}`
- `enable` -> `groupEnable` `{group}`
- `disable` -> `groupDisable` `{group}`
- `run test` -> `groupRunTest` `{group}`
- `run test <name>` -> `groupRunTest` `{group, name}`

## Response Schema

Purpose: Standardize ACK/OUT payloads.

ACK:

- `type, seq, name, status, message, ts, sessionId, state`

OUT:

- `type, seq, name, text, ts, sessionId, json (optional), state`

State:

- `enabled, estopped, mode`

Runtime-state JSON:

- `schemaVersion, generatedAtMs, build, profile`
- `groups[]` with members/bindings
- `selectedDevice`
- `devices[]` (label + interface/identity fields)

## Implementation Notes

Purpose: Provide guidance to avoid duplication.

- Extract shared TCP send/receive and response parsing into a single session module.
- Refactor GUI to use session + operations modules.
- Add CLI module that only parses and dispatches.
- Implement robot-side commands only after shared layers are in place.
- Keep existing UI commands unchanged.

## Examples

Purpose: Show the target usage.

Interactive:
```
bridge> show groups
bridge> configure terminal
bridge(config)# group swerve_drive
bridge(config-group-swerve_drive)# add device FL_DRIVE
bridge(config-group-swerve_drive)# bind controller0.leftY analog
bridge(config-group-swerve_drive)# enable
bridge(config-group-swerve_drive)# exit
bridge(config)# selected-device FL_DRIVE
bridge(config)# selected-mode on
bridge(config)# end
bridge> show group swerve_drive
```

Batch:
```
bridge.py --batch --script setup.txt
```

Script:
```
configure terminal
group swerve_drive
add device FL_DRIVE
add device FR_DRIVE
bind controller0.leftY analog
enable
end
```

## Tradeoffs

Purpose: Record known design tradeoffs.

- Robot-side group commands increase protocol surface area but provide a single source of truth.
- CLI depends on TCP UI path; offline use is not supported.
- JSON outputs are per-command blobs for simplicity.

## Future Extensions

Purpose: Track compatible next steps.

- Optional `?` shorthand.
- NDJSON stream mode for long show commands.
- GUI reuse of CLI help text strings.

## Appendix A: CLI Formal Grammar

Purpose: Provide a precise EBNF reference for the CLI command language.

```
(* Bridge CLI Grammar (EBNF) *)

line           = ws? command ws? [ "?" ] ;
command        = common
               | exec
               | config
               | group
               | device
               | test ;

common         = "exit"
               | "end"
               | "help"
               | "ping"
               | "echo" ws ("on" | "off")
               | "quit" ;

exec           = show_exec
               | "configure" ws "terminal"
               | "connect"
               | "disconnect" ;

show_exec      = "show" ws show_target [ ws show_flags ] ;

show_target    = "status"
               | "groups"
               | "group" ws name
               | "devices"
               | "device" ws name
               | "device-group" ws name
               | "bindings"
               | "selected-device"
               | "runtime-state"
               | "runtime-components"
               | "config"
               | "config" ws "local-raw"
               | "config" ws "dirty"
               | "profiles"
               | "profile" [ ws name ]
               | "tests"
               | "test" ws name
               | "workspace"
               | "session"
               | "controllers"
               | "visibility" [ ws name ] ;

show_source    = "robot" | "local" | "both" ;
show_flags     = show_flag { ws show_flag } ;
show_flag      = show_source | "--json" | "--pretty" ;

config         = "group" ws name
               | "no" ws "group" ws name
               | "profile" ws name
               | "selected-device" ws name
               | "selected-mode" ws ("on" | "off")
               | "merge" ws "config" ws path
               | "import" ws "config" ws path
               | "export" ws "runtime-groups" ws path
               | "export" ws "cli-script" ws path
               | "save" ws "all" [ ws "--prompt" ]
               | "save" ws "config" ws path
               | "save" ws "bridge-config" ws path
               | "save" ws "profiles" ws path
               | "save" ws "config" ws path
               | "rename" ws "device" ws name ws name
               | "device" ws name
               | "device" ws name ws "set" ws field ws value_text
               | "validate" ws "config" [ ws path ] [ ws "--all" ]
               | "validate" ws "profiles" [ ws ("robot" | "local") ] [ ws "--active" ]
               | "validate" ws "tests" [ ws "--active-set" ]
               | "show" ws show_target [ ws show_flags ]
               | "bindings" [ ws bindings_args ]
               | "can-mappings" [ ws mappings_args ]
               | "tests" [ ws tests_args ]
               | "write" ws "tests" ws path
               | "test" ws ("set" ws name
                           | "create" ws name
                           | "delete" ws name
                           | name) ;

bindings_args  = "show" [ ws ("controllers" | "bindings" | "axes") ] [ ws show_flags ]
               | "controller" ws ("add" ws name ws name ws number
                                   | "set" ws name ws field ws value_text
                                   | "rename" ws name ws name
                                   | "list"
                                   | "no" ws name)
               | "binding" ws ("add" ws name ws name ws name ws name ws name
                                | "set" ws number ws field ws value_text
                                | "delete" ws number)
               | "axis" ws ("add" ws name ws name ws name ws "invert" ws ("on" | "off") ws "deadband" ws number
                             | "set" ws number ws field ws value_text
                             | "delete" ws number)
               | "load" ws path
               | "save" ws path
               | "validate" [ ws path ] ;

mappings_args  = "show" [ ws ("manufacturers" | "device-types") ] [ ws show_flags ]
               | "manufacturer" ws ("set" ws number ws value_text | "delete" ws number | "no" ws number)
               | "device-type" ws ("set" ws number ws value_text | "delete" ws number | "no" ws number)
               | "load" ws path
               | "save" ws path
               | "validate" [ ws path ] ;

tests_args     = "templates"
               | "load" ws path
               | "load" ws "template" ws name
               | "save" ;

group          = "show"
               | "show" ws "members"
               | "show" ws "binding"
               | "show" ws show_target [ ws show_flags ]
               | "add" ws "device" ws name
               | "no" ws "device" ws name
               | "member" ws name ws ("enable" | "disable" | "toggle")
               | "bind" ws input ws "analog"
               | "bind" ws input ws ("hold" | "toggle" | "jog-forward" | "jog-reverse") ws value
               | "no" ws "bind"
               | "enable"
               | "disable"
               | "run" ws "test" [ ws name ]
               | "write" ws "tests" ws path ;

device         = "show"
               | "show" ws show_target [ ws show_flags ]
               | "set" ws field ws value_or_text
               | "no" ws field
               | "write" ws "tests" ws path ;

test           = "show"
               | "type" ws ("joystick" | "button" | "composite" | "deadbandSweep" | "deviceAction")
               | "device" ws "add" ws name
               | "no" ws "device" ws name
               | "inputSource" ws name
               | "deadband" ws number
               | "duty" ws number
               | "action" ws name
               | "color" ws name
               | "pattern" ws name
               | "brightness" ws number
               | "duration" ws number
               | "rotation" ws "limit" ws number
               | "rotation" ws ("encoderKey" | "encoderSource") ws name
               | "rotation" ws ("encoderMotorIndex" | "encoderCountsPerRev") ws number
               | "time" ws "timeout" ws number
               | "time" ws "onTimeout" ws name
               | "hold" ws "onRelease" ws name
               | "limitswitch" ws ("onHit" | "id") ws name
               | "deadbandSweep" ws ("startDuty" | "maxDuty" | "stepDuty" | "stepHoldSec" | "motionThresholdRot") ws number
               | "deadbandSweep" ws "requiredSamples" ws number
               | "deadbandSweep" ws ("encoderKey" | "encoderSource") ws name
               | "deadbandSweep" ws ("encoderMotorIndex" | "encoderCountsPerRev") ws number
               | "enabled" ws ("true" | "false" | "on" | "off")
               | "termination" ws "hold"
               | "termination" ws "time" ws number
               | "termination" ws "rotation" ws number
               | "termination" ws "limitswitch" [ ws name ]
               | "write" ws "tests" ws path ;

(* Lexical conventions *)

name           = token ;
input          = token ;
value          = number ;
value_or_text  = number | value_text ;
path           = token ;
field          = token ;
value_text     = token { ws token } ;

token          = token_char { token_char } ;
token_char     = ? any non-whitespace character ? ;

number         = ["+"|"-"] digit { digit } [ "." digit { digit } ] ;
digit          = "0"..."9" ;
ws             = { " " | "\t" } ;
```

## Appendix B: EBNF References

Purpose: Provide approachable books and articles for learning BNF/EBNF.

Books:

- Niklaus Wirth, *Compiler Construction*.
- Alfred V. Aho, Ravi Sethi, Jeffrey D. Ullman, *Compilers: Principles, Techniques, and Tools*.
- Terence Parr, *The Definitive ANTLR 4 Reference*.

Articles / Tutorials:

- Lars Marius Garshol, *BNF and EBNF: What are they and how do they work?*
- W3C, *Extensible Markup Language (XML) 1.0 (Fifth Edition)*, Appendix on notation.

## Appendix C: EBNF Change Workflow

Purpose: Document the steps to update the CLI grammar and regenerate code.

1. Edit the canonical grammar:
   - `tools/can_nt/bridge_cli_ebnf.txt`
2. Update metadata if needed:
   - `tools/can_nt/bridge_cli_grammar_meta.json`
3. Regenerate parser artifacts (PowerShell):
   - `tools\can_nt\regen_cli_parser.ps1`
4. Sanity test locally (no roboRIO required):
   - `python -m tools.can_nt.can_nt_bridge --no-can --no-nt --batch --script tools\can_nt\tmp_cli_mixed.txt`
5. Commit updated generated files:
   - `tools/can_nt/bridge_cli_grammar_gen.py`
   - `tools/can_nt/bridge_cli_constants_gen.py`



