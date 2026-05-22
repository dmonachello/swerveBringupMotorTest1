SPEC_STATUS: PARTIALLY_IMPLEMENTED

# Feature Spec: Config Store (Windows Python)

## Purpose
Define a centralized in-memory config database with JSON import/export and validation for all Windows-side Python tools.

## Goals
- Provide a single API for Bridge UI, Bridge CLI, and topology editor to load and edit config data.
- Treat the in-memory store as the live database during runtime.
- Keep JSON as the import/export format.
- Keep thin wrappers over raw dict/list structures.
- Centralize validation with strict and lenient modes.
- Track dirty state inside the store.

## Non-Goals
- Changing robot runtime behavior.
- Replacing JSON with a database.
- Altering NetworkTables contracts.

## Scope
Purpose: List files governed by the store.

Included:
- `data/bringup_system.json`
- Legacy tests export/import (optional): `bringup_tests.json` (repo root, when present)
- Legacy tests export/import (optional): `src/main/deploy/bringup_tests.json` (when present)
- `bringup_bindings.json` (repo root, when present)
- `src/main/deploy/bringup_bindings.json`
- `src/main/deploy/can_mappings.json`

Excluded:
- TCP runtime state
- NetworkTables state
- PCAP/PCAPNG data

## Location
Purpose: Define where the API lives.

- Module: `tools/config/config_store.py`
- Shared by: Bridge CLI, Bridge UI, topology editor

## API Summary
Purpose: Provide a stable public interface.

Construction / Import:
- `ConfigStore.load(repo_root)`

Accessors:
- `profiles()`
- `devices()`
- `device_by_label(label)`
- `groups(profile)`
- `selected_device(profile)`
- `tests_model()`
- `bindings()`
- `can_mappings()`

Validation:
- `validate(strict=True|False)`

Persistence / Export:
- `save_profiles(path)`
- `save_tests(path)`
- `save_bindings(path)`
- `save_mappings(path)`

Dirty tracking:
- `dirty_flags()`

## In-Memory DB Semantics
Purpose: Clarify how the store behaves as a runtime database.

- The store is the canonical source during a tool session.
- All edits apply to the in-memory DB first.
- Validation runs against the in-memory DB snapshot.
- JSON files are imported at load and exported on save.

## File Precedence
Purpose: Preserve existing behavior.

- Repo-root tests/bindings override deploy copies.
- When both exist, the store merges and emits warnings.

## Merge Rules
Purpose: Define merge behavior when duplicates exist.

- Shallow merge by top-level sections.
- Tests: `test_sets` from repo-root override deploy with same set name.
- Bindings: repo-root `controllers/bindings/axes` override deploy when both exist.
- Warnings returned to the caller, no printing inside the store.

## Validation Model
Purpose: Centralize validation with strictness levels.

Strict mode:
- Unknown keys are errors.
- Type mismatches are errors.
- Missing required fields are errors.

Lenient mode:
- Unknown keys are warnings.
- Type mismatches are errors.
- Missing required fields are errors.

Validation targets:
- Profiles and devices table coherence.
- Group references to device labels.
- Test definitions and termination rules.
- Bindings controllers and axes consistency.
- CAN mappings key/value shape.

## Isolation Rules
Purpose: Keep the store CLI-agnostic.

- No printing or prompting in the store.
- Return `ValidationIssue` records to the caller.
- Caller decides how to render warnings and errors.

## Dirty Tracking
Purpose: Expose edit state to all tools.

Flags:
- `profiles`
- `groups`
- `tests`
- `bindings`
- `can-mappings`

## Compatibility
Purpose: Ensure no breaking changes.

- JSON schema and filenames remain unchanged.
- Java code continues to read the same files.
- CLI and UI behavior remains unchanged except for centralized validation.

## Examples
Purpose: Show intended usage.

Load and validate:
```
store = ConfigStore()
warnings = store.load(repo_root)
result = store.validate(strict=False)
```

Save tests:
```
store.save_profiles("data/bringup_system.json")
```

## Tradeoffs
Purpose: Record known tradeoffs.

- Thin wrappers reduce refactor risk but keep some raw dict usage.
- Merge + warn can mask conflicts if warnings are ignored.
- Strict validation may block legacy data without explicit lenient mode.

## Future Extensions
Purpose: Document compatible next steps.

- Add transaction boundaries and undo history.
- Add schema version migration helpers.
- Add optional JSON schema export.

