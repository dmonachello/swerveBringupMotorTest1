# Migration: `interface` ? `deviceInterface` (bringup_system.json)

Purpose: Migrate the devices-table key name from legacy `interface` to canonical `deviceInterface` without breaking existing configs during the transition window.

## Quick Procedure (Do This First)

Purpose: Get the repo back to a clean, validated state with `deviceInterface` everywhere.

1. Migrate the canonical config file.

   ```powershell
   cd %USERPROFILE%\swerveBringupMotorTest\swerveBringupMotorTest1
   python -m tools.migrate_device_interface_key --path data\bringup_system.json
   ```

2. Validate + stamp + sync canonical ? deploy.

   ```powershell
   python -m tools.validate_sync
   ```

3. Confirm the legacy key is gone (optional).

   ```powershell
   rg -n "\"interface\"" data\bringup_system.json
   ```

If `validate_sync` still reports `Unknown key: interface`, re-run step 1 and then step 2.

## Summary

- Old key (legacy): `interface`
- New key (canonical): `deviceInterface`
- Backward compatibility: readers accept both keys for one iteration.
- Migration tool: `python -m tools.migrate_device_interface_key`
- Related tag: `deviceInterface-migration-2026-04-14`

## Why This Change Exists

Purpose: Remove ambiguity and avoid Java keyword mapping friction while keeping the JSON contract explicit.

- `interface` is a reserved keyword in Java, which required annotation-based mapping.
- `deviceInterface` is unambiguous and can be used consistently across Java, Python, docs, and JSON.

## Compatibility Contract (Transition Window)

Purpose: Define what is supported during the migration period.

During the transition:

- Writers should produce `deviceInterface`.
- Readers accept:
  - `deviceInterface` (preferred)
  - `interface` (legacy fallback)

After the transition window, legacy support can be removed.

## How to Migrate

Purpose: Convert existing config files to the canonical key.

### Step 1: Migrate the canonical file

```powershell
cd %USERPROFILE%\swerveBringupMotorTest\swerveBringupMotorTest1
python -m tools.migrate_device_interface_key --path data\bringup_system.json
```

Notes:

- Default behavior rewrites the file in-place.
- Legacy `interface` keys are removed when `deviceInterface` is present.

### Step 2: Validate, stamp, and sync to deploy

```powershell
python -m tools.validate_sync
```

### Step 3: Confirm legacy key is gone (optional)

```powershell
rg -n "\"interface\"" data\bringup_system.json
```

## Migration Tool Reference

Purpose: Document the supported command-line flags.

### Dry run (no write)

```powershell
python -m tools.migrate_device_interface_key --path data\bringup_system.json --no-write
```

### Keep the legacy key (not recommended)

```powershell
python -m tools.migrate_device_interface_key --path data\bringup_system.json --keep-legacy
```

## Validation Expectations

Purpose: Clarify the most common failure mode and its fix.

If validation reports an unknown key:

- Example: `Unknown key: interface`
- Fix: run the migration tool, then re-run `python -m tools.validate_sync`.

## Tradeoffs

Purpose: Make the downsides explicit.

- Adds a short transition period where two keys are accepted on read.
- Requires one-time file migration for existing configs.

## Future Extensions

Purpose: Define the cleanup end-state.

- Remove legacy read support for `interface` after the transition iteration.
- Optionally bump `schema_version` and enforce `deviceInterface` only.

