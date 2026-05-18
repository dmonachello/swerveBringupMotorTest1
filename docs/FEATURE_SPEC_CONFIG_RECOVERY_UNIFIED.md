# Feature Spec: Configuration Recovery & Damage Prevention

## Purpose
Prevent configuration corruption and provide fast, CLI-driven recovery.

## Scope

Includes:
- Atomic saves
- Save gating
- Local snapshots
- Recovery commands
- Repair tooling
- Audit logging
- CLI notifications

Excludes:
- Cloud sync
- GUI recovery flows
- Robot-side persistence changes

## Atomic Saves
Purpose: Guarantee all-or-nothing writes.

Behavior:
1. Write to `<path>.tmp`
2. Validate temp file
3. Move `<path>` to `<path>.bak`
4. Rename `<path>.tmp` to `<path>`
5. On failure, revert

## Save Gating
Purpose: Prevent invalid saves.

Behavior:
- `save` runs `validate all` by default
- If validation fails, save is blocked
- Override with `--force`

Examples:
- `save sources`
- `save sources --force`

## Local Snapshots
Purpose: Fast recovery without Git.

Behavior:
- On any save, write a timestamped snapshot in `backup_data/backups/`
- Maintain a `last_good` copy per source

Naming:
- `bringup_system.20260402_141000.json`
- `bringup_system.last_good.json`

## Recovery Commands
Purpose: Restore known-good configurations.

Commands:
- `recover last-good`
- `recover from <timestamp>`
- `recover list`

Behavior:
- Loads snapshot into memory
- Does not auto-save
- User runs `save sources` to persist

## Repair
Purpose: Fix malformed configs when no good snapshot exists.

Commands:
- `validate file <path>`
- `validate file <path> --repair`

Repair actions:
- Add missing required keys
- Normalize `schema_version`
- Recompute `data_hash`

## Audit Logging
Purpose: Traceability for all changes.

Location:
- `backup_data/backups/index.json`

Content:
- timestamp
- action
- source
- hash
- validation status

## CLI Commands
Purpose: User-facing control of recovery.

Core commands:
- `save`
- `save sources --force`
- `recover last-good`
- `recover from <timestamp>`
- `recover list`
- `validate file <path> --repair`

## Notifications
Purpose: Make outcomes explicit.

CLI must print:
- Save blocked (with reason)
- Snapshot created
- Recovery applied
- Repair applied

## Tradeoffs
- Performance vs. safety: more validation increases save time.
- Complexity vs. usability: more recovery features increase learning curve.
- Storage vs. recovery: snapshots consume disk.

## Future Extensions
- Cloud backups
- Snapshot diff viewer
- GUI recovery wizard
- Auto-rollback on validation failure

## Implementation Schedule
Purpose: Sequenced rollout plan with clear exit criteria.

| Phase | Duration | Scope | Exit Criteria |
| --- | --- | --- | --- |
| Phase 0 | 1-2 days | Design + scaffolding (backup schema, helpers, CLI stubs). | Helpers added, CLI stubs wired, no behavior changes. |
| Phase 1 | 2-3 days | Atomic save + audit log for all save paths. | All save paths use atomic write and audit entries. |
| Phase 2 | 1-2 days | Local snapshots + retention policy. | Snapshot files created and `last_good` maintained. |
| Phase 3 | 1-2 days | Save gating + `--force`. | Validation blocks save by default; override works. |
| Phase 4 | 1-2 days | Recovery commands. | `recover list/last-good/from` loads snapshots in memory only. |
| Phase 5 | 1-2 days | Repair command. | `validate file <path> --repair` produces valid output. |
| Phase 6 | 1-2 days | Notifications + docs + tests. | CLI messages updated and docs/tests complete. |

## Implementation Checklist

### Phase 0 - Design & Scaffolding
- [ ] Create `backup_data/backups/` convention and index schema
- [ ] Add helper utilities: `atomic_write`, `snapshot_write`, `audit_log_append`
- [ ] Add CLI stubs for recovery/repair commands

### Phase 1 - Atomic Save + Audit Log
- [ ] Implement atomic write for all save paths
- [ ] Generate `.bak` on save
- [ ] Write audit log entries for every save

### Phase 2 - Local Snapshots
- [ ] Write timestamped snapshots on save
- [ ] Maintain `last_good` copies per source
- [ ] Enforce retention policy (e.g., last 10)

### Phase 3 - Save Gating + Force Override
- [ ] Run `validate all` before save
- [ ] Block save on validation failures
- [ ] Add `--force` to bypass gating

### Phase 4 - Recovery Commands
- [ ] Implement `recover list`
- [ ] Implement `recover last-good`
- [ ] Implement `recover from <timestamp>`
- [ ] Ensure recovery loads into memory only

### Phase 5 - Repair Command
- [ ] Implement `validate file <path> --repair`
- [ ] Repair missing keys, normalize schema, recompute hash
- [ ] Log repair actions

### Phase 6 - Notifications & UX
- [ ] Standardize CLI messages for save/recover/repair outcomes
- [ ] Update CLI help and docs
