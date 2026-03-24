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
- `--json` output for show commands (one JSON blob per command).

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

### GUI Front End
Purpose: Remain a thin front end.

- Invokes shared operations only.

## Modes
Purpose: Define CLI contexts and prompts.

### Exec
Prompt: `bridge>`

Purpose:
- inspection
- connection status
- entry to config mode

### Config
Prompt: `bridge(config)#`

Purpose:
- structural edits
- group creation/selection
- selected device control
- merge/import/export

### Group Config
Prompt: `bridge(config-group-<name>)#`

Purpose:
- manage a single group
- membership and bindings
- enable/disable
- run tests

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
- `--json` prints one JSON blob per command.
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
- `quit`

Exec:
- `show status [robot|local|both]`
- `show groups [robot|local|both]`
- `show group <name> [robot|local|both]`
- `show devices [robot|local|both]`
- `show device <name> [robot|local|both]`
- `show bindings [robot|local|both]`
- `show selected-device [robot|local|both]`
- `show runtime-state [robot|local|both]`
- `show config [robot|local|both]` (alias for runtime-state)
- `configure terminal`
- `connect`
- `disconnect`

Config:
- `group <name>`
- `no group <name>`
- `selected-device <device>`
- `selected-mode on`
- `selected-mode off`
- `merge config <bringup_profiles.json>`
- `import config <bringup_profiles.json>`
- `export runtime-groups <bringup_profiles.json>`
- `save config <bringup_profiles.json>`
- `save local-config <path>` (local-only; writes groups-only when profiles are loaded)
- `rename device <old> <new>` (local-only; disabled when profiles are loaded)
- `validate config [path]`

Group:
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

## Control Identifiers
Purpose: Define allowed input names.

Examples:
- `driver.left.y`
- `driver.right.y`
- `driver.a`
- `driver.b`
- `driver.x`
- `driver.y`
- `driver.lb`
- `driver.rb`
- `operator.left.y`
- `operator.right.y`
- `operator.a`
- `operator.b`
- `operator.x`
- `operator.y`
- `operator.lb`
- `operator.rb`
- `ui.slider1`
- `ui.slider2`
- `ui.button1`
- `ui.button2`

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
- `show device <name> --json`
- `show bindings --json`
- `show selected-device --json`
- `show runtime-state --json`
- `show config --json`

JSON is one blob per command.

## Shared Config (bringup_profiles.json)
Purpose: Store bridge group config inside the single shared data file.

- The shared file is `data/bringup_profiles.json`.
- The bridge CLI reads/writes a top-level `bridgeConfig` object.
- Other tools ignore unknown fields; `bridgeConfig` is optional.
- `data_hash` is recomputed whenever `bridgeConfig` is saved.

`bridgeConfig` object:
- `schemaVersion` (required, current: 1)
- `groups` (list of group objects)
- `devices` (optional list of device metadata for local use)
- `selectedDevice` (selected-device override)
- `generatedAt` (optional timestamp)

Group object:
- `name` (string, required)
- `enabled` (boolean, default true)
- `members` (list of `{device, enabled}`)
- `bindings` (list of `{input, kind, value?}`)

Device object (optional, local-only):
- `name` (string, required)
- `manufacturer` (string or int, optional)
- `deviceType` (string or int, optional)
- `deviceId` (int, optional)

Example:
```
{
  "schema_version": 2,
  "data_version": "2026-03-20_143148",
  "data_hash": "…",
  "default_profile": "robot",
  "profiles": {
    "robot": { "neos": [], "krakens": [] }
  },
  "bridgeConfig": {
    "schemaVersion": 1,
    "generatedAt": "2026-03-23T14:02:00Z",
    "devices": [
      {"name": "FL_DRIVE", "manufacturer": "REV", "deviceType": "neo", "deviceId": 10}
    ],
    "groups": [
      {
        "name": "swerve_drive",
        "enabled": true,
        "members": [
          {"device": "FL_DRIVE", "enabled": true},
          {"device": "FR_DRIVE", "enabled": true}
        ],
        "bindings": [
          {"input": "driver.left.y", "kind": "analog"}
        ]
      }
    ],
    "selectedDevice": {
      "device": "FL_DRIVE",
      "enabled": false
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
- `show device <name>` -> `showDevice` `{name}`
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
- `save config <file>` -> local: `showRuntimeState --json`, write file

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
- `devices[]` (label/vendor/type/id)

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
bridge(config-group-swerve_drive)# bind driver.left.y analog
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
bind driver.left.y analog
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
