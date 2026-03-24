Profile Schema Refactor (v2)

Purpose: Define the refactored bringup_profiles.json schema and migration plan.

Overview
Purpose: Explain why the schema refactor exists.
- Profiles are the single source of truth for device labels.
- Labels must be unique within a profile.
- bridgeConfig.devices are generated from profiles to keep labels consistent.

Schema v2 Rules
Purpose: Document required conventions for bringup_profiles.json.
- schema_version must be 2.
- data_version and data_hash are required.
- Device labels are unique within each profile.
- Device entries keep existing fields (id, label, tags, limits, vendor/type for generic devices).
- Diagram labels must match device labels.

Single Source of Truth
Purpose: Clarify ownership between profiles and bridgeConfig.
- Profiles define device labels and CAN IDs.
- bridgeConfig.devices are derived from the default_profile device list.
- Groups reference the same labels as profiles.

Migration Plan
Purpose: Convert existing profiles to schema v2.
1) Run the migration tool:
   python tools\\migrate_profiles.py --source data\\bringup_profiles.json --dest data\\bringup_profiles.json
2) Sync to deploy:
   python tools\\sync_profiles.py
3) Validate:
   python tools\\can_topology\\validate_profiles.py --path data\\bringup_profiles.json --strict

Migration Behavior
Purpose: Describe how duplicates are resolved.
- Duplicate labels are disambiguated using tags when available:
  "Drive Motor" + tag "swerve-front-left" becomes "Drive Motor (swerve-front-left)".
- If no tag exists, the CAN ID is appended:
  "Drive Motor" id 5 becomes "Drive Motor (id 5)".
- Diagram node labels are updated to match.
- data_hash is recomputed after changes.

Compatibility
Purpose: Explain how tools consume schema v2.
- can_profiles.py expects schema_version 2.
- validate_profiles.py expects schema_version 2 and enforces unique labels.
- bridgeConfig devices are regenerated from profiles when loading a profiles file.

Tradeoffs
Purpose: Explain costs of the refactor.
- Requires unique labels (may force renaming existing devices).
- Migration tool may rename labels for disambiguation.
- Any downstream tooling that assumed duplicate labels must be updated.

Future Extensions
Purpose: Describe next steps.
- Add a report of renamed labels for review in dashboards.
- Add a "labels preview" mode before applying migrations.
- Add a schema v2 JSON schema file for external validation.
