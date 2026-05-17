# Bindings Test Plan

## Summary

Purpose: Define a complete test plan for all current bindings-related functionality in the CLI and the underlying config/runtime surfaces.

This plan covers two different binding systems that currently share similar words but serve different purposes:

- global controller bindings edited with `bindings ...`
- group bindings edited in group mode with `bind ...`

The plan treats them separately, then tests the places where they intentionally meet, such as `show bindings --all`.

## Why Bindings Exist

Purpose: Explain the intent of bindings clearly before testing details.

Bindings exist so operators can declare how physical controls and CLI-managed runtime targets relate, without editing JSON by hand and without requiring code changes for normal bringup workflows.

There are two layers:

- Global controller bindings:
  - stored in `bringup_bindings.json`
  - define controller inventory and persistent named button/axis mappings
  - edited with `bindings controller ...`, `bindings binding ...`, and `bindings axis ...`
  - used as host-local configuration data
- Group bindings:
  - stored in the local bridge config / profile-group state
  - define how a runtime group consumes an input and drives a group action
  - edited in group mode with `bind ...` and `no bind`
  - represent per-group runtime intent rather than the global controller catalog

These two systems are related, but they are not the same thing.

## Binding Intentions

Purpose: State what the current product is trying to achieve.

The intended operator model is:

- A team declares controller names and reusable input mappings in `bringup_bindings.json`.
- The CLI can inspect, validate, load, save, and edit that file safely.
- Group-level runtime configuration can define additional bindings that are tied to an active profile/group context.
- Operators can inspect both views and understand which data came from which source.
- Binding-related failures should be specific and actionable.

The current CLI now implements first-pass group binding diagnostics such as `bind list`, `bind explain <binding>`, and `bind test <binding>`, but it does not yet implement the full planned ownership and runtime-value explanation model. This test plan therefore distinguishes:

- current implemented behavior that must pass now
- planned future behavior that should get its own test section once implemented

## Scope

Purpose: Define what is in and out of scope for this test plan.

In scope:

- CLI parsing and help for all `bindings ...` commands
- local config editing behavior for global bindings payloads
- `show bindings` local rendering behavior
- `show bindings --all` merged rendering behavior
- bindings load/save/validate workflows
- dirty tracking and save provenance effects caused by bindings edits
- index handling, controller reference validation, and delete guards
- compatibility alias handling where intentionally supported

Also in scope:

- group-mode `bind ...` and `no bind`
- group-mode `bind list`, `bind explain`, and `bind test`
- group binding visibility through `show bindings`
- separation between global bindings and group bindings

Out of scope for this pass:

- full joystick/control lease enforcement
- robot-side live binding activation semantics beyond the currently exposed surfaces
- UI-only behaviors outside the CLI/TIU contract

## Source of Truth

Purpose: Identify where binding behavior currently comes from.

Global bindings:

- file payload:
  - `src/main/deploy/bringup_bindings.json`
  - repo-root override when supported by current source loading rules
- CLI implementation:
  - [tools/can_nt/bridge_cli.py](/c:/Users/dmona/swerveBringupMotorTest/swerveBringupMotorTest1/tools/can_nt/bridge_cli.py)
- grammar:
  - [tools/can_nt/bridge_cli_ebnf.txt](/c:/Users/dmona/swerveBringupMotorTest/swerveBringupMotorTest1/tools/can_nt/bridge_cli_ebnf.txt)

Group bindings:

- profile/group config payload in local bridge config state
- CLI group-mode commands in [tools/can_nt/bridge_cli.py](/c:/Users/dmona/swerveBringupMotorTest/swerveBringupMotorTest1/tools/can_nt/bridge_cli.py)

Automated regression coverage:

- [tools/can_nt/tests/test_bridge_cli_visibility.py](/c:/Users/dmona/swerveBringupMotorTest/swerveBringupMotorTest1/tools/can_nt/tests/test_bridge_cli_visibility.py)

## Key Behavioral Rules

Purpose: Make the expected behavior explicit before test cases.

Current expected rules for global `bindings ...`:

- `bindings ...` commands are valid from `exec` mode.
- `bindings show` is local-only.
- `bindings show` supports:
  - `controllers`
  - `bindings`
  - `axes`
  - `--json`
  - `--pretty`
  - `--all`
- Controller names must exist before binding or axis entries can reference them.
- Binding and axis indexes are 1-based.
- A controller cannot be deleted while a binding or axis entry still references it.
- `bindings save <path>` writes only the global bindings payload:
  - `controllers`
  - `bindings`
  - `axes`
- `bindings validate [path]` validates either the in-memory payload or the file payload.

Current expected rules for group `bind ...`:

- group bindings are separate from `bringup_bindings.json`
- group bindings are scoped to the selected profile and current group
- `bind list` inspects current-group bindings using local config truth
- `bind explain <binding>` explains one current-group binding using local config truth
- `bind test <binding>` reports pass or fail using current local binding resolution checks
- `show bindings` shows group bindings from local profile/group config
- `show bindings --all` augments that with global bindings payload data

## Test Strategy

Purpose: Explain how bindings functionality should be tested end to end.

Use three layers:

1. Parser and command-surface tests
2. Host-local state mutation and persistence tests
3. Operator workflow and visibility tests

Use two execution styles:

- automated regression for repeatable host-local behavior
- manual CLI and robot-connected checks where runtime behavior matters

## Test Data

Purpose: Keep test inputs consistent across automated and manual runs.

Recommended baseline global bindings payload:

```json
{
  "controllers": [
    { "name": "driver0", "type": "XBOX", "port": 0 },
    { "name": "operator0", "type": "XBOX", "port": 1 }
  ],
  "bindings": [
    {
      "command": "stop",
      "controller": "driver0",
      "input": "button",
      "id": "A",
      "mode": "pressed"
    }
  ],
  "axes": [
    {
      "command": "drive",
      "controller": "driver0",
      "id": "leftY",
      "invert": false,
      "deadband": 0.12
    }
  ]
}
```

Recommended baseline group setup:

- at least one profile loaded
- at least one group with members
- at least one group binding created with `bind ...`

## Automated Regression Plan

Purpose: Define the required automated coverage.

### A1. Parser Acceptance

Verify every documented global bindings command parses in `exec` mode:

- `bindings show`
- `bindings show controllers`
- `bindings show bindings`
- `bindings show axes`
- `bindings show --json`
- `bindings show --pretty`
- `bindings show --all`
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
- `bindings validate`
- `bindings validate <path>`

Expected result:

- parser accepts all documented forms
- command AST is consistent with bindings handling

### A2. End-to-End Global Bindings Command Surface

Use one ordered regression that:

1. starts from an empty in-memory bindings payload
2. runs `bindings show`
3. adds a controller
4. edits the controller
5. renames the controller
6. adds a button binding
7. edits the button binding
8. adds an axis binding
9. edits the axis binding
10. saves to a temporary file
11. validates the temporary file
12. validates the in-memory payload
13. deletes the binding
14. deletes the axis
15. removes the controller
16. loads a known file payload
17. validates again

Expected result:

- each command succeeds
- saved file content matches expected transformed payload
- load restores expected file payload
- no parser/runtime mismatch exists

Current implementation status:

- covered by `test_bindings_command_surface_regression`

### A3. Global Bindings Negative Cases

Add or maintain explicit automated checks for:

- `bindings show robot`
  - expect local-only error
- `bindings binding add ...` with missing controller
  - expect controller-not-found error
- `bindings axis add ...` with missing controller
  - expect controller-not-found error
- invalid controller port
  - expect integer validation failure
- invalid deadband text
  - expect numeric validation failure
- deadband out of range
  - expect range validation failure
- `bindings binding set 0 ...`
  - expect index out of range
- `bindings axis set 0 ...`
  - expect index out of range
- deleting controller still referenced by bindings
  - expect in-use error
- deleting controller still referenced by axes
  - expect in-use error
- `bindings validate <missing-path>`
  - expect read/validation failure
- malformed JSON file for `bindings load`
  - expect read failure

### A4. Dirty-State Integration

Verify that bindings edits participate correctly in config lifecycle state:

1. start clean
2. run a mutating `bindings ...` command
3. confirm prompt dirty marker appears
4. confirm `show dirty` reports bindings dirty
5. save bindings
6. confirm dirty state clears
7. confirm provenance updates if applicable

### A5. `show bindings` Source Split

Automate the distinction between group bindings and global bindings:

- Case 1:
  - local group bindings present
  - no global bindings payload loaded
  - `show bindings`
  - expect only group binding content
- Case 2:
  - same local group bindings
  - global bindings payload loaded
  - `show bindings --all`
  - expect:
    - group binding section
    - separate global bindings section
- Case 3:
  - `show bindings --all --json --pretty`
  - expect JSON payload contains local group data plus `globalBindings`

### A6. Compatibility Alias

The documented form is:

- `bindings no controller <name>`

The compatibility-only alias is:

- `bindings controller no <name>`

Test both.

Expected result:

- documented form remains canonical
- compatibility form remains supported until explicitly removed

## Manual CLI Test Plan

Purpose: Validate operator-facing behavior that should be checked interactively.

### M1. Help and Discoverability

Commands:

```text
help bindings
bindings ?
bindings show ?
bindings controller ?
bindings binding ?
bindings axis ?
```

Verify:

- help text matches real accepted syntax
- contextual `?` suggestions are sensible
- documented forms are the same forms the parser accepts

### M2. Global Bindings Editing Workflow

Commands:

```text
bindings show
bindings controller add driver0 XBOX 0
bindings binding add stop driver0 button A pressed
bindings axis add drive driver0 leftY invert on deadband 0.12
bindings show --all --json --pretty
bindings save src/main/deploy/bringup_bindings.json
bindings validate
```

Verify:

- output is readable
- controller, binding, and axis entries appear in expected sections
- `--all` does not hide the local section
- save path and validation output are explicit

### M3. Group Binding Editing Workflow

Commands:

```text
configure terminal
group motion
bind controller0.leftY analog
bind list
bind explain 1
bind test 1
show binding
end
show bindings
show bindings --all
```

Verify:

- group binding appears in group-mode output
- `bind list` reports current-group binding status
- `bind explain` reports why the binding is active or inactive
- `bind test` reports pass or fail consistently with `bind explain`
- `show bindings` shows group binding content
- `show bindings --all` still keeps global bindings visually separate

### M4. Error Clarity

Attempt:

- binding add with unknown controller
- axis add with invalid deadband
- delete controller still in use
- invalid index edits

Verify:

- errors are specific
- operator can tell the next required fix
- no generic parse failure hides a semantic issue

### M5. Save/Reload Consistency

Workflow:

1. edit global bindings
2. save to temp file
3. clear or restart CLI
4. load saved file
5. show bindings

Verify:

- saved content reloads identically
- indexes and entry ordering are stable

## Robot-Connected Checks

Purpose: Validate the points where local binding config interacts with robot/runtime surfaces.

### R1. Runtime Visibility Contract

Preconditions:

- robot connected
- profile/groups loaded
- relevant controllers available if needed

Check:

- `show bindings`
- `show active`
- any current runtime binding-related status output

Verify:

- host-local bindings are not mislabeled as robot runtime truth
- robot-side visibility and local host config are clearly labeled

### R2. `show bindings --all` Source Separation

Check that operators can tell:

- which bindings came from group/profile config
- which bindings came from the global bindings file

Expected result:

- no ambiguous mixed list
- source boundary remains visible in text and JSON

## Future Tests To Add

Purpose: Reserve coverage for planned but not yet implemented binding observability.

Add once implemented:

- ownership conflict reporting in binding activation
- last input value and last output value reporting
- `signal watch` interaction with binding diagnostics

## Pass Criteria

Purpose: Define when bindings functionality is considered adequately tested.

Bindings functionality passes when:

- all documented `bindings ...` commands parse and execute as documented
- `show bindings` and `show bindings --all` correctly distinguish local group bindings from global bindings payloads
- save/load/validate workflows are repeatable
- dirty tracking reflects bindings edits correctly
- error cases produce specific actionable failures
- automated regression passes locally
- manual operator workflows do not reveal hidden source ambiguity

## Suggested Regression Commands

Purpose: Give a repeatable command set for developers.

Targeted bindings-only run:

```text
python -m pytest tools/can_nt/tests/test_bridge_cli_visibility.py -k bindings
```

Full CLI visibility test file:

```text
python -m pytest tools/can_nt/tests/test_bridge_cli_visibility.py
```

## Notes

Purpose: Record important clarifications for reviewers.

- In the current product, `bindings ...` and group `bind ...` are separate mechanisms and must not be conflated in docs or test expectations.
- `show bindings --all --json --pretty` is currently the clearest inspection surface for seeing both group binding context and global bindings payload in one response.
- If the command contract changes, update:
  - help text
  - parser rules
  - grammar files
  - this plan
  - regression tests
