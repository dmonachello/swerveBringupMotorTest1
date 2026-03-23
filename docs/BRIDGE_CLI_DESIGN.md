Purpose: Define the CLI feature design, protocol mapping, and no-regression guarantees.

## Scope
Purpose: Capture what this design covers and what it excludes.

Included:
- CLI module design and behavior.
- Shared session/operations layers.
- Robot-side command mapping.
- No-regression guarantees.

Excluded:
- Implementation details.
- UI layout changes.
- New hardware support.

## No-Regression Guarantee
Purpose: Ensure existing workflows continue to work unchanged.

- Existing GUI behavior remains unchanged when CLI/groups are unused.
- Existing TCP commands remain supported with identical names and semantics.
- Existing NT keys and UI protocol monitoring remain unchanged.
- CLI is additive; no required changes to existing user workflows.

## Architecture
Purpose: Define required layers and responsibilities.

### Bridge Core / Session Layer
Purpose: Centralize connect/send/receive and runtime state.
- Connect/disconnect to TCP UI server.
- Send commands and stream ACK/OUT responses.
- Merge runtime state from TCP responses and NT state.
- Provide a single event stream to GUI and CLI.

### Shared Operations Layer
Purpose: Contain all bridge business logic.
- Group membership operations.
- Binding operations.
- Selected-device operations.
- Show/query operations.
- Merge/import/export operations (local config files on Windows).
- Conflict handling (move/error policies).

### CLI Module
Purpose: Provide a Cisco-style operator surface.
- Prompt loop and mode handling.
- Command parsing and dispatch.
- Batch/script execution.
- Streams output to console (no buffering).

### GUI Front End
Purpose: Continue operating with shared logic.
- Uses the same operations and session layer as CLI.

## Modes
Purpose: Define operator contexts and prompts.

- Exec: `bridge>`
- Config: `bridge(config)#`
- Group: `bridge(config-group-<name>)#`

Batch mode:
- Invoked via `bridge.py --batch --script <file>`
- Fails if no script file is provided.
- No prompts.
- Deterministic output.

## Output Handling
Purpose: Standardize console output behavior.

- All output streams directly to console.
- ACK/OUT/CONSOLE are printed as received.
- `--json` prints one JSON blob per command.

## Config File
Purpose: Define where merge/import/export/save operate.

- Config files live on the Windows host.
- Import/merge read JSON and emit group commands.
- Export/save use `showRuntimeState --json` and write a file.

## Conflict Policy
Purpose: Handle device ownership conflicts.

Policies:
- `error` (default): warn, do not move.
- `move`: warn, automatically move.

Interactive prompting:
- Device move between groups.
- Deleting groups.
- Clearing groups.
- Default response: no.

Batch mode:
- No prompts allowed.

## Command Mapping (Robot TCP)
Purpose: Map CLI commands to robot-side TCP command names and args.

Exec / Show:
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
Purpose: Keep ACK/OUT stable across GUI and CLI.

ACK:
- `type, seq, name, status, message, ts, sessionId, state`

OUT:
- `type, seq, name, text, ts, sessionId, json (optional), state`

State:
- `enabled, estopped, mode`

## Tradeoffs
Purpose: Record known design tradeoffs.

- Adding robot-side group commands increases protocol surface area but keeps a single source of truth.
- CLI depends on TCP UI path; offline use is not supported.
- JSON outputs are per-command blobs, which is simple but less stream-friendly.

## Future Extensions
Purpose: Track safe, compatible next steps.

- Optional `?` help shorthand.
- NDJSON stream mode for long show commands.
- GUI reuse of CLI command help strings for consistency.
