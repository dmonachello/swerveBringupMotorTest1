# Feature Spec: CLI Usability and Configuration Workflow

## Summary
This spec defines a set of CLI usability improvements to make configuration workflows understandable, scoped, and recoverable. The goal is to reduce hidden state, make validation actionable, and make saving changes explicit. Documentation updates are a required deliverable alongside code changes.

## Problem Statement
Users struggle to configure the system via the CLI because:
- State is hidden (loaded files, active profile/set, dirty flags).
- Validation is global and noisy.
- Errors are not actionable.
- Mode boundaries are unforgiving.
- Multiple files are intertwined without clear ownership.

## Goals
- Provide a single “workspace view” that answers: what’s loaded, what’s active, what’s dirty, and what to do next.
- Make validation scoped and actionable.
- Make save operations explicit and safe.
- Improve discoverability of valid values for manufacturers/device types and input sources.
- Prevent CLI crashes on malformed input.
- Keep docs aligned with behavior.

## Non-Goals
- Changing robot-side behavior.
- Changing UI behavior, except for documentation alignment.
- Changing JSON schema definitions beyond what the CLI already accepts.

## Scope
CLI-only changes in:
- `tools/can_nt/bridge_cli.py`
- `tools/can_nt/bridge_cli_parser.py` and EBNF
- `tools/can_nt/gen_bridge_cli_parser.py`
- `tools/config/schema_store.py`
- Docs in `docs/`

## Terminology
- Profiles file: `data/bringup_system.json` (canonical).
- Tests source: `bringup_system.json` under `bridgeConfig.byProfile.<profile>.tests` (canonical).
  - `bringup_tests.json` is a legacy import/export format only.
- Active profile: currently selected profile in CLI.
- Active test set: currently selected test set in CLI.
- Dirty flags: indicate unsaved changes for profiles/tests/bindings/mappings.
- Recovery mode: CLI started even if profiles file is invalid.

## User Stories
- As a user, I can run one command to see what files are loaded, what profile/set is active, and what needs saving.
- As a user, I can validate just the active profile or active test set without being flooded by unrelated errors.
- As a user, I can save all dirty changes in one step without knowing every file path.
- As a user, I can see valid manufacturer and deviceType values when setting device fields.
- As a user, I can recover from invalid profiles without leaving the CLI.

## Functional Requirements

### 1) Workspace Visibility
Add command:
- `show workspace` (alias `show session`)

Output must include:
- Profiles source path and load status.
- Tests source path and load status.
- Active profile name.
- Active test set name and default test set.
- Dirty flags for profiles/tests/bindings/mappings.
- Message level and echo state.
- Recovery mode status.

JSON output:
- `show workspace --json [--pretty]` returns a structured object:
  - `profiles`: `{path, loaded, activeProfile, dirty, recoveryMode, loadWarnings[]}`
  - `tests`: `{path, loaded, activeSet, defaultSet, dirty}`
  - `bindings`: `{path, loaded, dirty}`
  - `mappings`: `{path, loaded, dirty}`
  - `cli`: `{messageLevel, echo}`

### 2) Scoped Validation
Add scoped validation targets:
- `validate profiles --active`
- `validate tests --active-set`

Rules:
- Default `validate profiles` validates all profiles.
- Default `validate tests` validates all test sets.
- `--active` and `--active-set` limit to active profile/test set.
- Output must include profile/test set name when scoped.

Error output:
- Must include the exact profile/test set name.
- Must include actionable fix text when possible.

### 3) Save All
Add command:
- `save all`

Behavior:
- Saves all dirty sections using their current source paths.
- If a path is unknown, prints a single-line fix:
  - “No unified-config destination set. Fix: `save unified-config data/bringup_system.json`”
- No prompts in batch mode.
- Optional `save all --prompt` to confirm per-section in interactive mode.

### 4) Contextual Value Help (All Contexts)
Add contextual help anywhere a field has a bounded/known value set. `?` prints **all valid values inline**.

Applies to:
- Device fields: `interface`, `manufacturer`, `deviceType`, `type`, `model`, `terminator`, `bus`, `limits` (where enumerated), `tags` (if preset list exists).
- Test fields: `inputSource` (known controllers + inputs), `termination` (time/rotation/hold/limitSwitch), `rotation` subfields, `time` subfields, `limitswitch` subfields, `deadbandSweep` subfields.
- Bindings fields: controller `type`, `input`, `id`, `mode`; axis `id`, `invert`, `deadband`.
- Mappings fields: `manufacturer` IDs, `deviceType` IDs.

Rules:
- `?` prints full inline lists (no truncation).
- If a list is empty or unknown, print: “No known values; see docs.”
- If a value is numeric and has known ranges, print the range (example: `duty: -1.0..1.0`).

Data sources:
- Use mappings from `can_mappings.json` or in-memory mappings store.
- Use bindings/controller config for controller names and inputs.
- Use CLI grammar enums (EBNF) for bounded keywords.

### 5) Controller Visibility
Add command:
- `show controllers`

Output:
- Default controller naming (`controller0`..`controller5`).
- Connected/declared controllers if bindings are loaded.
- Supported input names (leftX/leftY/rightX/rightY, A/B/X/Y, etc.).

### 6) Mode Error Guidance
Improve guidance for common mis-modes:
- `write tests` in `config-test-*` should print:
  - “You are in test edit mode. Use `exit` or `end` first.”
- `tests load` and `tests merge` should be disallowed in test edit mode with a direct fix message.

### 7) Recovery Mode Clarity
When profiles fail to load:
- CLI starts in recovery mode.
- Print a short banner:
  - What failed.
  - The active file.
  - The next command to inspect or fix (`show devices`, `show device <name>`, `validate profiles --active`).

### 8) Validation Output Quality
Validation errors must be:
- Grouped by profile/test set when possible.
- De-duplicated where identical issues repeat.
- Actionable, with fix commands where possible.

### 9) Documentation Updates (Required)
Update these docs to match behavior:
- `docs/CLI_TEST_AUTHORING_USER_GUIDE.md`
- `docs/CORRECTED_STEP_BY_STEP_CLI_BRINGUP.md`
- `docs/CLI_REFERENCE_MANUAL.md` or `docs/CLI_USER_MANUAL.md` as applicable

Add “Workspace” section:
- Explain loaded file sources and dirty flags.

Add “Scoped validate” section:
- Describe `--active` and `--active-set`.

Add “Save all” section:
- Explain expected behavior and error messages.

## Command Syntax (Detailed)

### show workspace
```
show workspace [--json] [--pretty]
show session [--json] [--pretty]
```

### validate profiles
```
validate profiles [--active]
```

### validate tests
```
validate tests [--active-set]
```

### save all
```
save all [--prompt]
```

### show controllers
```
show controllers [--json] [--pretty]
```

### contextual help
```
device "<label>"
set manufacturer ?
set deviceType ?
```

## Example Outputs

### show workspace (text)
```
Profiles: data/bringup_system.json (loaded, dirty)
Active profile: example_default
Tests: data/bringup_system.json (loaded, clean)
Active set: default (default=default)
Bindings: src/main/deploy/bringup_bindings.json (loaded, clean)
Mappings: src/main/deploy/can_mappings.json (loaded, clean)
CLI: messages=beginner echo=off
Recovery mode: OFF
```

### validate profiles --active (error)
```
ERROR: profile example_default: missing device label PDP.
Fix: add device "pdp" or remove "PDP" from profile devices.
```

### save all (missing tests path)
```
ERROR: No unified-config destination set. Fix: save unified-config data/bringup_system.json
Saved profiles to data/bringup_system.json.
```

## Error Handling
- No CLI command should throw a traceback on user input.
- All parse errors must return a CLI error and remain in session.
- Batch mode must never prompt.

## Acceptance Criteria
- `show workspace` is available and accurate.
- `validate profiles --active` and `validate tests --active-set` work and reduce noise.
- `save all` saves all dirty sections or prints a single-line fix.
- `set manufacturer ?` and `set deviceType ?` print valid mappings.
- Recovery mode clearly explains how to repair.
- Docs updated to match new commands and outputs.

## Implementation Notes
- Update EBNF and regenerate parser.
- Add JSON output format for `show workspace` and `show controllers`.
- Use existing mappings store and bindings store for value resolution.
- Ensure CLI help (`help`, `show commands`) includes new commands.

## Test Plan
- Unit tests for:
  - `show workspace --json` schema.
  - Scoped validate behavior.
  - `save all` when paths are missing.
  - Contextual `?` help for manufacturer/deviceType.
- Integration test:
  - Load profiles/tests, set active profile/set, modify, validate, save all.
  - Ensure no tracebacks with invalid input in batch mode.

## Rollout
- Update docs first or in the same change set.
- Add release notes entry describing new commands and behaviors.
