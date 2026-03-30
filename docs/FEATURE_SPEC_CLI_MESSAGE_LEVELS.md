# Proposal: CLI Message Levels

## Purpose
Provide configurable verbosity for CLI-generated guidance without affecting command results or robot/system output.

## Levels
- beginner (default): errors + warnings + tips
- medium: errors + warnings
- expert: errors + essential warnings only

## Scope
Applies only to CLI-generated guidance and status messages.

Does not affect:
- robot output
- NetworkTables output
- UI output
- `show` command content
- parser errors
- command result data
- validation failures

## Definitions
- error: command failed or state is invalid
- warning: important condition or risk the user should notice
- tip: optional guidance or next-step suggestion

## Tip Guidelines
Tips must be:
- short (one line)
- state-driven (only when relevant)
- actionable

Allowed tip categories:
- unsaved changes reminders
- next-step guidance after successful commands
- safety reminders when leaving a mode
- brief hints after validation failure

Not allowed:
- repeated explanations of commands
- generic help spam
- narration of obvious actions

## Repetition Rule
- Duplicate tips must be suppressed until relevant state changes
- Example: unsaved warning shown once per dirty state, not on every exit attempt

## Configuration
- startup:
  - `--cli-messages <beginner|medium|expert>`
- in session:
  - `messages <beginner|medium|expert>`
- query current level:
  - `show message-level`

## Persistence
Persist level in local settings file:
- `.bridge_cli_settings.json`

### Precedence
1. startup flag (applies to current session only)
2. persisted setting
3. default = beginner

### Behavior
- Changing level in session updates the active level immediately
- Setting is written to the local settings file unless overridden by startup flag

## Batch Mode Behavior
- Batch mode suppresses all tips
- Errors and warnings still apply

## Dirty State Behavior
When leaving config/test mode with unsaved changes:
- beginner:
  - warning + tip
  - example:
    - “You have unsaved changes. Use `write tests ...` to save.”
- medium:
  - warning only
- expert:
  - warning only (no tip)

## Example Beginner Tips
- On exit with unsaved changes:
  - “You have unsaved changes. Use `write tests ...` to save.”
- After save:
  - “Saved. Use `show config dirty` to confirm.”
- After validation failure:
  - one short next-step hint (if applicable)

## Constraints
- Must not alter command behavior
- Must not suppress actual errors
- Must not interfere with scripting or batch workflows
- Must not introduce duplicate or noisy output
