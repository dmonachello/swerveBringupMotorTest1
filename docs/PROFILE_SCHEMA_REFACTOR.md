Profile Schema Refactor (v3)

Purpose: Define the unified bringup_system.json schema and migration plan.

Overview
Purpose: Explain why the schema refactor exists.
- One file for device catalog, diagram metadata, and groups/bindings.
- Profiles remain the single source of truth for device labels.
- bridgeConfig stores groups/bindings without duplicating the device catalog.
 - Topology editor can create/edit bridgeConfig groups in the same file.

Schema v3 Rules
Purpose: Document required conventions for bringup_system.json.
- schema_version must be 3.
- data_version and data_hash are required.
- data_hash is computed from profiles + diagram (bridgeConfig is excluded).
- Device labels are unique within each profile.
- Device entries keep existing fields (id, label, tags, limits, vendor/type for generic devices).
- Diagram labels must match device labels when present.
- bridgeConfig is optional and may be omitted.

Single Source of Truth
Purpose: Clarify ownership between profiles and bridgeConfig.
- Profiles define device labels and CAN IDs.
- bridgeConfig groups reference those labels.
- bridgeConfig does not own device catalog data.

Migration Plan
Purpose: Convert existing profiles to schema v3.
1) Run the migration tool:
   python tools\migrate_profiles.py --source data\bringup_system.json --dest data\bringup_system.json
2) Sync to deploy:
   python tools\sync_profiles.py
3) Validate:
   python tools\can_topology\validate_profiles.py --path data\bringup_system.json --strict

Migration Behavior
Purpose: Describe how duplicates are resolved.
- Duplicate labels are disambiguated using tags when available:
  "Drive Motor" + tag "swerve-front-left" becomes "Drive Motor (swerve-front-left)".
- If no tag exists, the CAN ID is appended:
  "Drive Motor" id 5 becomes "Drive Motor (id 5)".
- Diagram node labels are updated to match.
- data_hash is recomputed after changes.

Compatibility
Purpose: Explain how tools consume schema v3.
- can_profiles.py expects schema_version 3 (legacy v2 accepted for transition).
- validate_profiles.py expects schema_version 3 and enforces unique labels.
- bridgeConfig devices are regenerated from profiles when loading a unified file.
- Topology editor may write bridgeConfig groups for visualization; robot ignores them.

Tradeoffs
Purpose: Explain costs of the refactor.
- Requires unique labels (may force renaming existing devices).
- Migration tool may rename labels for disambiguation.
- Any downstream tooling that assumed duplicate labels must be updated.

Future Extensions
Purpose: Describe next steps.
- Add a report of renamed labels for review in dashboards.
- Add a "labels preview" mode before applying migrations.
- Add a schema v3 JSON schema file for external validation.
