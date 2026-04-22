# Feature Spec: Host/Robot Active Context Clarity

## Purpose

Define clear, explicit rules for "active profile" and "active tests" when the Bridge CLI is connected to the robot, so users do not confuse host-local editing context with robot runtime state.

## Scope

Purpose: Define what this spec changes and what it does not.

- Bridge CLI behavior and outputs (Windows Python tool).
- Visibility of host vs robot active contexts in status/prints.
- Documentation updates that describe the new mental model.

Out of scope:

- Robot-side profile loading rules and persistence format.
- NetworkTables key paths (must remain stable unless separately specified).
- Any CAN transmit capability (PC tool remains read-only on CAN).

## Problem Statement

Purpose: Explain the user confusion this spec addresses.

Today the user can have two different "active" contexts at the same time:

- Host: what the CLI/editor is currently editing (local profile/test set context).
- Robot: what the roboRIO is currently running (active profile, selected test, enabled flags).

This is confusing because the word "active" reads as singular, and users naturally assume:

- "If I select a profile in the CLI, the robot is now on that profile."
- "If I am looking at tests in the CLI, those are the same tests the robot will run."

## Goals

Purpose: Define the user-facing outcomes.

- Robot runtime state changes only on explicit robot-targeting commands.
- Host-local editing context remains safe and predictable, even when connected.
- The CLI makes host vs robot context obvious in normal workflows.
- When host and robot contexts diverge, the CLI indicates it clearly and suggests the correct explicit command(s).

## Non-Goals

Purpose: Avoid accidental scope creep.

- No automatic pushing of profiles/config to the robot.
- No implicit robot activation when the host profile changes.
- No prompts in batch mode.

## Definitions

Purpose: Provide precise language for the rest of the spec.

- Host context:
  - The CLI's current local working state loaded from disk (typically `data/bringup_system.json`).
  - Includes: local active profile name, test authoring active set, dirty flags, file paths.
- Robot context:
  - The robot's runtime state over TCP (active bringup profile, selected test name/index, runAllActive, etc.).
- Connected:
  - The Bridge CLI has an active TCP session and handshake with the robot.

SID_COMMENT: The word "host" is used instead of "local" to avoid confusion with "local vs robot vs both" show sources.

## Proposed Behavior

Purpose: Specify the rules and command semantics.

### Core Rule: Explicit Robot Changes Only

Purpose: Prevent surprise behavior when connected.

- Host-only commands MUST NOT change robot state as a side effect.
- Robot state MUST change only via explicit robot-targeting commands.

Examples:

- `profile <name>` changes host active profile (editing context) only.
- `profiles activate <name>` changes robot active profile (and SHOULD update host active profile display only if the host already has that profile loaded; see "Show Workspace").

### Host Profile Selection While Connected

Purpose: Define what happens when the user changes host profile while connected.

When connected and user runs:

- `profile <name>`

Then:

- Host active profile becomes `<name>`.
- Robot active profile does not change.
- The CLI SHOULD warn once per session when host and robot profiles differ.

Suggested warning text (informational):

- `WARNING: Host profile != robot profile. Host=<host> Robot=<robot>. Use 'profiles activate <host>' to switch the robot.`

### Robot Profile Activation

Purpose: Define explicit robot activation semantics.

When connected and user runs:

- `profiles activate <name>`

Then:

- CLI sends the robot command to activate `<name>`.
- On success, the CLI SHOULD refresh and display robot active profile.
- The CLI MAY update host active profile display (without changing local files) if `<name>` exists in the loaded host profiles.

SID_QUESTION: Should `profiles activate <name>` hard-require that `<name>` exists on the host, or allow activating a robot-only profile and show host as "(unloaded)"?

### Robot Test Runner Commands

Purpose: Define explicit robot test-runner semantics.

When connected and user runs:

- `tests select <name>`: selects a test by name on the robot.
- `tests toggle`: toggles enabled state of the currently selected robot test.
- `tests run`: runs the selected robot test.
- `tests run-all`: runs all enabled robot tests.

Constraints:

- These commands MUST require an active robot connection.
- These commands MUST NOT modify host-local test definitions.

SID_COMMENT: Host test authoring already exists separately (configure/test mode + save config).

## Outputs And Surfaces

Purpose: Make the system state obvious without requiring tribal knowledge.

### Show Workspace

Purpose: Provide one place to see both contexts.

`show workspace` output MUST include:

- Host context:
  - active host profile
  - tests authoring active set (host)
  - dirty flags and loaded paths
- Robot context (only when connected):
  - active robot profile
  - selected test name/index (if available)
  - runAllActive and active test name/status (if available)

Example (text):
```text
Host: profile=home_042126V1 testsSet=default dirty=tests=False profiles=False
Robot: connected=YES profile=practice_042126 selectedTest=neo25_button runAllActive=NO
```

SID_QUESTION: Should this be a single JSON object with `host` and `robot` keys in `--json` mode, or keep the existing shape and add `robot`?

### Prompt And Mode Indicators

Purpose: Prevent users from assuming host==robot.

When connected:

- Prompt SHOULD NOT imply the robot matches the host.
- If the prompt includes profile info, it MUST be labeled, e.g.:
  - `bridge[host:home_042126V1 robot:practice_042126]>`

SID_QUESTION: Do we want prompts to change, or only `show workspace` + one-time warnings?

### Help Text

Purpose: Teach the rule at the point of use.

- `help profile` MUST state: "Host-only; does not change the robot."
- `help profiles activate` MUST state: "Robot-only; changes the robot active profile."
- `help tests ...` MUST state: "Robot-only test runner controls."

## Error Handling

Purpose: Keep failures actionable and non-destructive.

- If a robot-targeting command is executed while not connected:
  - Print a clear error and no host state changes.
- If a robot command fails (ACK error or timeout):
  - Print the robot failure.
  - Keep host context unchanged.

Batch mode:

- No prompts.
- Warnings should be concise and deterministic (avoid repeating every line).

## Backward Compatibility

Purpose: Avoid breaking existing scripts and dashboards.

- Existing `profile <name>` host semantics remain valid.
- Existing `profiles activate <name>` remains the canonical robot profile switch.
- New outputs (extra workspace fields) are additive.

## Verification Plan

Purpose: Define objective checks for this behavior.

1. Offline (no robot):
   - `profile <name>` changes host context.
   - `tests select <name>` errors clearly (not connected).
2. Connected (robot present):
   - Host profile change does not affect robot profile.
   - `profiles activate <name>` changes robot profile.
   - Mismatch warning appears when host!=robot (once per session).
   - `tests select/toggle/run/run-all` act on robot and do not dirty host files.
3. Batch mode:
   - No prompts.
   - Deterministic outputs suitable for scripting.

## Tradeoffs

Purpose: Document why this is a deliberate choice.

- Explicit robot changes reduce surprise but require the user to learn two commands (`profile` vs `profiles activate`).
- Showing both contexts everywhere adds verbosity; mitigate with one-time warnings and a strong `show workspace`.

## Future Extensions

Purpose: Capture follow-on ideas without coupling them to this change.

- Add an optional "safety interlock" mode:
  - Refuse to run robot tests when host!=robot unless `--force` is used.
- Add an explicit "sync host->robot" workflow command:
  - `profiles push <path> --activate <name>` as the single-step happy path.
- Add UI parity:
  - Surface host vs robot profile mismatch in the Bringup Control UI status bar.

