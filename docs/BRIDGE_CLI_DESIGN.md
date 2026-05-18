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
- Windows EOF: Ctrl+Z then Enter behaves like `exit` (Ctrl+D on POSIX shells).

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

Host vs Robot Context
Purpose: Prevent "active profile" confusion when connected.

- Host context: local editing/inspection selection used for groups/bindings/test authoring.
- Robot context: runtime state on the roboRIO (active profile, selected test, run status).
- Rule: `profile <name>` changes host context only; robot context changes only via explicit TCP commands (for example `profiles activate <name>` and `tests ...`).

Exec / Show:

- `show status` -> `showStatus`
- `show active` -> local/robot summary composed from shared status paths
- `show groups` -> `showGroups`
- `show group <name>` -> `showGroup` `{name}`
- `show devices` -> `showDevices`
- `show device-group <name>` -> `showDevice` `{name}`
- `show device <name>` -> local-only devices-table lookup (definition)
- `show instantiated` -> local or robot instantiation-focused view
- `show faults` -> local or robot fault-focused view
- `show signals` -> local signal-catalog view
- `show signal <name>` -> local signal-catalog view for one device
- `show bindings` -> `showBindings`
- `show workspace` -> local-only (loaded paths, active profile/set, dirty flags)
- `show controllers` -> local-only (declared controllers + supported inputs)
- `show selected-device` -> `showSelectedDevice`
- `show runtime-state` -> `showRuntimeState`
- `show config` -> `showRuntimeState`

Show sources:

- `show <...> robot|local|both` selects data source.
- Default is `robot` when connected, otherwise `local`.
- Local source reads `bridgeConfig.byProfile` from `data/bringup_system.json` plus profile-derived devices.
- Each show output is prefixed with `SOURCE: robot|local`.
- `show group` text output includes members and bindings.
- `show devices` (local) lists the full profile-derived device inventory, not only group members.
- `show device` returns the full device definition from bringup_system.json (local only).
- `show device-group` returns the device’s group membership/usage info.

Config:

- `group <name>` -> `groupCreate` `{name}`
- `no group <name>` -> `groupDelete` `{name, confirm}`
- `selected-device <device>` -> `selectedDeviceSet` `{name}`
- `selected-mode on|off` -> `selectedModeSet` `{enabled}`
- `merge config <bringup_system.json>` -> local: read bridgeConfig.byProfile, emit group commands for the active profile
- `import config <bringup_system.json>` -> local: delete groups, then emit group commands
- `export runtime-groups <bridgeConfig.json>` -> local: update bridgeConfig.byProfile for the active profile
- `save runtime-groups <runtime_groups.json>` -> local: snapshot robot runtime groups to file
- `save bridge-config <path>` -> local: update bridgeConfig.byProfile only
- `save profiles <path>` -> local: update profiles/diagram only
- `save config <path>` -> local: update shared bringup_system.json
- `save sources` -> local: save dirty canonical source files where known
- `revert` -> local: discard unsaved in-memory state and reload from disk sources
- `rename device <old> <new>` -> local: rename device in profiles when loaded, update bridgeConfig references

Group:

- `add device <device>` -> `groupAddDevice` `{group, device, conflictPolicy, forceMove}`
- `no device <device>` -> `groupRemoveDevice` `{group, device}`
- `member <device> enable` -> `groupMemberEnable` `{group, device}`
- `member <device> disable` -> `groupMemberDisable` `{group, device}`
- `member <device> toggle` -> `groupMemberToggle` `{group, device}`
- `bind list` -> local-only current-group binding diagnostics
- `bind explain <binding>` -> local-only current-group binding explanation
- `bind test <binding>` -> local-only current-group binding pass/fail check
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

Common presentation:

- `tiu on|off` -> CLI presentation-only dashboard mode; no robot command is sent

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

- Expand `?` help to include all bounded values and numeric ranges (now supported).
- NDJSON stream mode for long show commands.
- GUI reuse of CLI command help strings for consistency.
