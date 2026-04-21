Profile Schema Refactor (v4)

Purpose: Define the unified bringup_system.json schema and label-only model.

Overview
Purpose: Explain why the schema refactor exists.
- One file for device catalog, diagram metadata, and per-profile groups/bindings.
- The devices table is the single source of truth for device identity.
- Profiles reference devices by label only.
- bridgeConfig.byProfile stores groups/bindings without duplicating the device catalog.
- The topology editor can create/edit bridgeConfig.byProfile groups in the same file.

Schema v4 Rules
Purpose: Document required conventions for bringup_system.json.
- schema_version must be 4.
- data_version and data_hash are required.
- data_hash is computed from profiles + diagram (bridgeConfig is excluded).
- Device labels are unique in the devices table.
- Profiles list device labels only.
- Device entries own identity fields (interface + CAN or port metadata).
- Diagram labels must match device labels when present.
- bridgeConfig is optional and may be omitted.

Single Source of Truth
Purpose: Clarify ownership between profiles and bridgeConfig.
- The devices table defines device labels and identity.
- bridgeConfig.byProfile groups reference those labels.
- bridgeConfig.byProfile does not own device catalog data.

Migration Plan
Purpose: Convert existing profiles to schema v4.
1) Update bringup_system.json to include a devices table at the root.
2) Replace profile device lists with label-only arrays.
3) Sync to deploy:
   python -m tools.validate_sync
4) Validate:
   python tools\can_topology\validate_profiles.py --path data\bringup_system.json --strict

Compatibility
Purpose: Explain how tools consume schema v4.
- can_profiles.py expects schema_version 4.
- validate_profiles.py expects schema_version 4 and enforces unique labels.
- bridgeConfig.byProfile is loaded per profile when present.
- Topology editor may write bridgeConfig.byProfile groups for visualization; robot ignores them.

Tradeoffs
Purpose: Explain costs of the refactor.
- Requires unique labels (may force renaming existing devices).
- Profiles are thinner, so the devices table must be kept up to date.
- Any downstream tooling that assumed duplicate labels must be updated.

Future Extensions
Purpose: Describe next steps.
- Add a report of renamed labels for review in dashboards.
- Add a "labels preview" mode before applying migrations.
- Add a schema v4 JSON schema file for external validation.
