# Groups Guide (Bridge CLI)

**Purpose**

Explain what groups are, why they exist, how `defaultGroup` and `active-group` differ, and how to run tests using each.

## What A Group Is

**Purpose**

Define the runtime control unit used by the robot bringup system.

A group is a runtime collection of device labels plus optional bindings and enable state.
Groups are used to decide which devices receive commands when tests or group actions run.

Key points:

- Groups are profile-scoped.
- Device references are label-based.
- Group configuration is stored under `bridgeConfig.byProfile.<profile>.groups`.

## Why Groups Exist

**Purpose**

Separate device ownership/control intent from the full profile device catalog.

Profiles answer: "What devices exist?"
Groups answer: "Which devices are being controlled together right now?"

This supports:

- Subsystem-style targeting (for example one corner, intake-only, shooter-only).
- Safer bringup progression.
- Bindings and run commands that act on an explicit set.

## Special Groups

**Purpose**

Clarify built-in runtime groups that are easy to confuse.

### `defaultGroup`

- Primary runtime group used by default test-run flows.
- Common place where configured devices initially belong.
- `run test <name>` in exec mode targets this flow.

### `active-group`

- Built-in runtime working set for progression commands.
- Used by `active show`, `active add`, and `active next`.
- Intended for stepping through ready devices in a controlled sequence.
- Not user-created manually.

## Membership Rule (Current Behavior)

**Purpose**

Document current ownership constraints explicitly.

A device has single-group membership at runtime.
If a device is already in one group, adding it to another group can fail with:
`already in group: <groupName>`.

Implication:

- `active add` may fail if the next ready device is already owned by `defaultGroup`.

## `add all` vs `active add`

**Purpose**

Separate device instantiation from active working-set selection.

- `add all`
  - Instantiates all configured devices for runtime use.
  - Does not populate `active-group`.
- `active add`
  - Adds the next ready device to `active-group`.
  - One device per call.

## Running Tests By Group

**Purpose**

Show how group context changes test execution target.

### Exec mode

- `run test <name>` uses the default exec flow (typically `defaultGroup`).

### Group mode

Use:

```text
configure terminal
group <name>
run test <name>
```

This runs the test in that selected group context.

## Practical Bringup Sequence

**Purpose**

Give a minimal sequence that avoids common confusion.

```text
connect
add all
active show --json --pretty
active add
active show --json --pretty
run test neo25_button
```

If `active add` reports "already in group", either:

- run tests from that existing owning group, or
- move membership intentionally.

## Troubleshooting

**Purpose**

Map common symptoms to cause quickly.

- `show devices` lists devices but `active-group` is empty
  - Expected after `add all`; run `active add`.
- `active add` says already in another group
  - Membership conflict due to single-group ownership.
- Test does not run in TUI/CLI after safety event
  - Clear stop latch, re-enable test, and retry.
