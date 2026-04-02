# Spec for Repo-Level Version Helper and Release Workflow Commands

## Purpose

Replace the current thin wrapper approach with a small, stable, repo-level command surface that is easy for humans and Codex to discover, understand, and use consistently.

The new command set should do more than just translate arguments into update_versions.py calls. It should provide:

- a clear public interface for version operations
- readable output that Codex can parse and reason about
- dry-run support for safe automation
- a simple read path for current versions
- an extensible base for later release automation

This spec does not require implementing full release orchestration yet, but the structure must make that easy to add.

## Goals

1. Create a single public version command at repo root:
   `bump ...`

2. Support clear, discoverable subcommands:
   - `bump show <app|all>`
   - `bump bump <app|all> <major|minor|patch>`
   - `bump set <app|all> <full-semver>`
   - `bump field-set <app|all> <major|minor|patch> <value>`
   - `bump help`

3. Produce machine-friendly and human-friendly output.
   Every mutating command must print:
   - old version
   - new version
   - whether it was dry-run or applied
   - one line per app updated

4. Add dry-run support to all mutating commands.

5. Make `all` a first-class target.

6. Keep `tools/update_versions.py` as the underlying engine if practical, but make `bump` the stable public interface.

7. Preserve Windows-first usability from repo root.

## Non-goals

1. Do not reintroduce version bumping into the bridge CLI.
2. Do not require users to know update_versions.py arguments.
3. Do not implement git tagging, commit creation, pushing, or test execution in this change.
4. Do not redesign version storage format unless needed to support correctness.
5. Do not add fallback parsers or fuzzy command interpretation.

## High-level design

The repo will expose one public root command:

`bump`

This command will be implemented via:
- a root-level `bump.cmd` for Windows shell use
- a Python entry script at `tools/bump_version.py`

The Python script becomes the canonical logic layer for version-related helper commands.

The existing `tools/update_versions.py` remains the low-level engine for actually reading, modifying, and writing versions, unless a clean abstraction requires light refactoring there.

The new wrapper should behave like a proper command with subcommands, not just a positional shortcut.

## Required command surface

### 1. Show current version(s)

Command:
`bump show bridge_cli`

Command:
`bump show all`

Behavior:
- Reads current version values from the authoritative source
- Prints one line per app
- Must not modify files
- Must return exit code 0 on success

Required output format:
`bridge_cli: 0.4.1`

For all:
```
can_nt_bridge: 0.x.y
bridge_cli: 0.x.y
bringup_ui: 0.x.y
can_topology_editor: 0.x.y
robot_bringup: 0.x.y
```

### 2. Bump semantic field

Command:
`bump bump bridge_cli minor`

Command:
`bump bump all patch`

Behavior:
- Reads current version(s)
- Computes new version(s) using semantic version bump logic
- Applies changes unless `--dry-run` is present
- Prints old -> new mapping for each app
- Must fail cleanly on invalid app or field
- Must return non-zero on error

Semantic rules:
- bump major: increment major, reset minor and patch to 0
- bump minor: increment minor, reset patch to 0
- bump patch: increment patch only

Required output format for applied change:
`APPLY bridge_cli: 0.3.2 -> 0.4.0`

Required output format for dry-run:
`DRY-RUN bridge_cli: 0.3.2 -> 0.4.0`

For multiple apps:
```
APPLY can_nt_bridge: 0.3.1 -> 0.3.2
APPLY bridge_cli: 0.4.0 -> 0.4.1
...
```

### 3. Set full version directly

Command:
`bump set bridge_cli 0.4.1`

Command:
`bump set all 1.0.0`

Behavior:
- Sets the full semantic version directly
- Must validate full version format as X.Y.Z where X, Y, Z are non-negative integers
- Applies to one app or all apps
- Supports `--dry-run`
- Prints old -> new mapping

Required output format:
`APPLY bridge_cli: 0.4.0 -> 0.4.1`

### 4. Set one field only

Command:
`bump field-set bridge_cli minor 4`

Command:
`bump field-set all patch 0`

Behavior:
- Reads current version(s)
- Replaces only the selected field
- Leaves the other fields unchanged
- Does not auto-reset other fields
- Supports `--dry-run`
- Value must be a non-negative integer

Example:
Current: `1.3.9`
`field-set minor 4`
Result: `1.4.9`

This subcommand exists because it is already close to what the current helper supports. Keep it, but make it explicit and secondary to `set`.

### 5. Help

Command:
`bump help`

Also valid:
`bump`
`bump --help`
`bump -h`

Behavior:
- Prints usage summary
- Includes examples
- Includes list of valid apps
- Includes brief explanation of each subcommand

Required help content:

Usage:
```
bump show <app|all>
bump bump <app|all> <major|minor|patch> [--dry-run]
bump set <app|all> <X.Y.Z> [--dry-run]
bump field-set <app|all> <major|minor|patch> <value> [--dry-run]
```

Apps:
```
can_nt_bridge
bridge_cli
bringup_ui
can_topology_editor
robot_bringup
all
```

Examples:
```
bump show bridge_cli
bump bump bridge_cli minor
bump bump all patch --dry-run
bump set bridge_cli 0.4.1
bump field-set bridge_cli patch 7
```

## Why this shape

This command layout is intentional.

- show gives Codex and humans a read path
- bump performs normal semantic version changes
- set handles exact release version assignment
- field-set preserves specialized control without overloading set
- help makes the interface discoverable

## Implementation requirements

### 1. Root wrapper

File:
`bump.cmd`

Purpose:
Allow users and Codex to run version commands from repo root as:
`bump ...`

Behavior:
- Pass all args through to Python
- Use repo-relative pathing
- Return Python exit code

Suggested implementation shape:
```
@echo off
python tools\bump_version.py %*
```

No extra logic should live in bump.cmd.

### 2. Python command entry point

File:
`tools/bump_version.py`

Responsibilities:
- parse subcommands and flags
- validate arguments
- read current versions
- compute updated versions
- call the underlying engine
- print stable output
- return meaningful exit codes

Requirements:
- no traceback on user error
- no dependency on bridge CLI
- no implicit behavior beyond documented commands
- no silent success on invalid input

### 3. Underlying engine integration

Existing file:
`tools/update_versions.py`

Expectations:
- continue to own authoritative version read/write behavior if possible
- wrapper may call functions from it
- if update_versions.py is too CLI-shaped internally, refactor modestly to expose reusable functions

Preferred internal API shape inside update_versions.py:

- get_current_versions() -> dict[str, str]
- parse_version(version: str) -> tuple[int, int, int]
- format_version(parts: tuple[int, int, int]) -> str
- bump_version(parts, field) -> tuple[int, int, int]
- write_versions(updates: dict[str, str]) -> int or None

The goal is to stop relying on wrapper logic that reaches into private helpers unless you intentionally decide those helpers are now public within the module.

### 4. Supported app names

The public interface must support exactly these app names unless existing repo definitions require adjustment:
- can_nt_bridge
- bridge_cli
- bringup_ui
- can_topology_editor
- robot_bringup
- all

The actual app list should be defined once in a canonical place and reused by both help and validation.

## Argument parsing rules

### General

- Commands are case-sensitive by default unless current repo conventions strongly prefer lowercase normalization
- Subcommand names may be normalized to lowercase
- App names should match canonical names
- Semantic fields must be exactly: major, minor, patch

### Show

Valid:
- bump show bridge_cli
- bump show all

Invalid:
- bump show
- bump show bogus_app

### Bump

Valid:
- bump bump bridge_cli patch
- bump bump all minor
- bump bump bridge_cli patch --dry-run

Invalid:
- bump bump bridge_cli
- bump bump bridge_cli build
- bump bump bogus_app minor

### Set

Valid:
- bump set bridge_cli 0.4.1
- bump set all 1.0.0
- bump set bridge_cli 0.4.1 --dry-run

Invalid:
- bump set bridge_cli 4
- bump set bridge_cli 0.4
- bump set bridge_cli 0.4.x
- bump set bridge_cli -1.2.3

### Field-set

Valid:
- bump field-set bridge_cli patch 7
- bump field-set all major 2
- bump field-set bridge_cli minor 4 --dry-run

Invalid:
- bump field-set bridge_cli patch
- bump field-set bridge_cli build 4
- bump field-set bridge_cli patch -1

## Dry-run behavior

Supported on:
- bump bump ...
- bump set ...
- bump field-set ...

Not needed on:
- show
- help

Rules:
- dry-run must compute and print the exact would-be change
- dry-run must not modify any files
- dry-run must return success if arguments are valid
- output must clearly say DRY-RUN, not just "would update"

## Output requirements

General rules:
- one primary result line per app
- avoid chatty prose
- avoid ambiguous wording
- keep output stable across runs
- no decorative text
- no random blank lines unless part of help output

### Show output

One line per app:
`bridge_cli: 0.4.1`

### Bump/set/field-set output

Dry-run:
`DRY-RUN bridge_cli: 0.3.2 -> 0.4.0`

Applied:
`APPLY bridge_cli: 0.3.2 -> 0.4.0`

No-op optional behavior:
If old == new, either:
- still print `APPLY bridge_cli: 0.4.1 -> 0.4.1`
- or print `NO-CHANGE bridge_cli: 0.4.1 -> 0.4.1`

Pick one approach and use it consistently. Simpler choice is to print the same old->new line.

### Error output

Examples:
- `ERROR: unknown app 'bridgecl'`
- `ERROR: invalid version field 'build'`
- `ERROR: invalid semantic version '0.4'`
- `ERROR: missing required argument <app|all>`

## Exit codes

- 0 = success
- 2 = usage or validation error
- 1 = unexpected operational failure

## Behavior details

1. Determining current version

The command must read current versions from the same authoritative place update_versions.py already uses.
Do not invent a second source of truth.

2. Order of app processing

When target is all, process apps in canonical order:
- can_nt_bridge
- bridge_cli
- bringup_ui
- can_topology_editor
- robot_bringup

This keeps output stable for both users and Codex.

3. Atomicity expectations

For "all" updates:
- prefer computing all changes first
- then applying them in one write pass if underlying implementation supports it
- avoid partially updated output if validation fails before write

If full atomic write is impractical, at minimum:
- validate everything first
- only then begin file changes

4. Validation before modification

All commands that mutate must:
- validate subcommand shape
- validate app target
- validate field/version/value
- compute updated versions
- only then write changes

5. No hidden resets in field-set

field-set patch 7 means exactly patch becomes 7.
Do not reset any other field there.

6. Reset semantics only belong to bump

Only semantic bump rules should reset subordinate fields.

Examples:
- bump minor: 1.3.9 -> 1.4.0
- field-set minor 4: 1.3.9 -> 1.4.9

## Documentation updates required

Update repo docs anywhere version tooling is described.

At minimum:
- README or developer docs section for version helper usage
- any setup or workflow docs that mention update_versions.py directly as the user-facing path
- remove stale references to CLI version bump/set commands

### Required doc content

Add a short section like:

Version helper

Use the repo root bump command for version operations.

Examples:
- bump show bridge_cli
- bump bump bridge_cli minor
- bump set bridge_cli 0.4.1
- bump field-set bridge_cli patch 7
- bump bump all patch --dry-run

The underlying script tools/update_versions.py still exists, but bump is the preferred public interface for interactive and Codex-driven workflows.

## Future-ready structure

This change should leave room for a later release command, such as:
`release bridge_cli`

That future command may eventually:
- bump version
- run tests
- commit version files
- create git tag
- push

Do not implement that now, but structure the code so adding a new subcommand later is straightforward.

That means:
- use subcommand dispatch cleanly
- keep version calculation separate from output formatting
- keep output formatting separate from write logic

## Suggested internal structure

Inside tools/bump_version.py, organize around small functions like:
- cmd_show(...)
- cmd_bump(...)
- cmd_set(...)
- cmd_field_set(...)
- print_usage(...)
- resolve_apps(...)
- parse_semver(...)
- format_transition(...)

The names do not matter. The separation does.

## Acceptance criteria

1. From repo root, these commands work:

- bump show bridge_cli
- bump show all
- bump bump bridge_cli patch
- bump bump bridge_cli minor --dry-run
- bump bump all patch
- bump set bridge_cli 0.4.1
- bump set all 1.0.0 --dry-run
- bump field-set bridge_cli patch 7
- bump help

2. Invalid input does not produce a traceback.

3. Invalid input prints a clear ERROR line and returns exit code 2.

4. Successful mutating commands print exactly one result line per affected app with old -> new.

5. Dry-run prints DRY-RUN lines and makes no file changes.

6. show prints current version lines and makes no file changes.

7. "all" processes apps in stable canonical order.

8. Repo docs are updated to treat bump as the public interface.

9. No bridge CLI version bump/set functionality is reintroduced.

## Nice-to-have but optional

If easy, add:
- --json output mode later, but not required now
- a small unit test file for argument parsing and version transformation logic
- one integration-style test that verifies dry-run does not modify files

## Suggested implementation notes for Codex

- Start by inspecting tools/update_versions.py and identifying what functions can be reused safely.
- If needed, refactor update_versions.py lightly so bump_version.py does not depend on private helpers unless that is acceptable within the repo.
- Keep behavior strict and explicit.
- Prefer predictable output over cleverness.
- Do not add fuzzy matching for app names or fields.
- Do not add git/release orchestration in this change.
- Do not add unrelated cleanup.

## Short rationale to include in commit or PR description

This change promotes version operations from a thin wrapper into a small, stable repo command surface that works well for both humans and Codex. It adds read support, dry-run support, clearer output, a better help path, and a cleaner foundation for future release automation, while keeping update_versions.py as the underlying engine.
