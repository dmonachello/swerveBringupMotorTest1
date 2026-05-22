SPEC_STATUS: SUPERSEDED

# Feature Spec: Config Recovery & Damage Prevention

## Purpose
Prevent configuration corruption and provide fast, CLI-driven recovery.

## Scope

Includes:
- Atomic saves
- Save gating (validate before save)
- Local snapshots and last-good pointers
- Recovery commands
- Repair command
- Audit log and notifications

Excludes:
- Cloud sync
- GUI recovery flows
- Robot-side persistence changes

## Consolidated Feature Set

### 1) Atomic Save
Purpose: Prevent partial writes.

Behavior:
- Write to `<path>.tmp`
- Validate temp file
- Move `<path>` to `<path>.bak`
- Rename `<path>.tmp` to `<path>`
- On any failure, revert

### 2) Save Gating
Purpose: Prevent saving invalid configs.

Behavior:
- `save` runs `validate all` by default
- If validation fails, save is blocked
- Override with `--force`

Examples:
- `save sources`
- `save sources --force`

### 3) Local Snapshots (Event-Driven)
Purpose: Provide fast recovery without Git.

Behavior:
- On any save, write a timestamped snapshot in `backup_data/backups/`
- Maintain a `last_good` copy per source

Example snapshot names:
- `bringup_system.20260402_141000.json`
- `bringup_system.last_good.json`

### 4) Recovery
Purpose: Restore a known-good snapshot.

Commands:
- `recover last-good`
- `recover from <timestamp>`
- `recover list`

Behavior:
- Loads snapshot into memory
- Does not auto-save
- User runs `save sources` to persist

### 5) Repair
Purpose: Fix malformed configs when no good snapshot exists.

Command:
- `validate file <path> --repair`

Repair actions:
- Add missing required keys
- Normalize `schema_version`
- Recompute `data_hash`

### 6) Audit Log + Notifications
Purpose: Provide traceability and user visibility.

Audit log:
- `backup_data/backups/index.json`
- Records time, action, source, hash, validation status

CLI notifications:
- Save blocked (with reason)
- Snapshot created
- Recovery applied

## CLI Additions Summary

- `save sources --force`
- `recover last-good`
- `recover from <timestamp>`
- `recover list`
- `validate file <path> --repair`

## Tradeoffs

Pros:
- Strong guardrails against corruption
- Fast recovery without Git
- Auditable changes

Cons:
- More disk usage
- Slightly slower saves
- More commands to learn

## Future Extensions

- GUI recovery wizard
- Auto-rollback on validation failure
- Snapshot diff viewer
- Cloud backup integration

