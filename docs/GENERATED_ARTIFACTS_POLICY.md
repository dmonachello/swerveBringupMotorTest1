# Generated Artifacts Policy

Purpose: Document which files are generated, what each file does, and why this repo keeps generated outputs in source control.

## Decision Summary

- We keep generated status-code artifacts in git.
- We keep generated cross-language outputs (Python + Java) in git.
- We keep generated `.MSG` exports in git.
- We regenerate artifacts in the same change whenever source status definitions change.

## Source Of Truth

Primary source inputs:

- `tools/status_codes/status_codes_source.json`
- `tools/status_codes/generate_status_codes.py`

These drive the generated status catalog and downstream language/runtime files.

## Generated Files And Purpose

### Status Catalog JSON

- `tools/status_codes/status_codes.generated.json`
  - Purpose: Generated canonical status schema output from source definitions.
  - Used by: Codegen and validation workflows.

- `tools/status_codes/generated/status_catalog.compiled.json`
  - Purpose: Compiled/flattened runtime catalog used by Python status runtime.
  - Used by: `tools/can_nt/status/status_catalog.py`, `tools/can_nt/status/status_messages.py`.

### Python Generated Runtime Files

- `tools/can_nt/status/generated/status_catalog_generated.py`
  - Purpose: Generated Python constants for severities/facilities/messages.

- `tools/can_nt/status/generated/status_messages_generated.py`
  - Purpose: Generated Python message-template lookup table.

- `tools/can_nt/status/generated/__init__.py`
  - Purpose: Python package marker for generated status module imports.

### Java Generated Runtime Files

- `src/main/java/frc/robot/status/generated/StatusCatalogGenerated.java`
  - Purpose: Generated Java status constants and encoded status code values.

- `src/main/java/frc/robot/status/generated/StatusMessagesGenerated.java`
  - Purpose: Generated Java message-template lookup table.

### MSG Export Artifacts

- `tools/status_codes/vms_msg/*.MSG`
  - Purpose: Per-facility canonical message exports.
  - Example files: `CLI_PARSER.MSG`, `CONFIG.MSG`, `NETWORK.MSG`.

- `tools/status_codes/vms_msg_surface/*.MSG`
  - Purpose: Full status/message surface exports for Python and Java status consumers.
  - Example files: `PY_CANONICAL_SURFACE.MSG`, `JAVA_ACK_STATUS_SURFACE.MSG`.

### Inventory Report

- `tools/status_codes/reports/status_surface_inventory.json`
  - Purpose: Generated inventory snapshot for status-code/message coverage and auditing.

## Why We Keep Generated Files

- Traceability: every generated contract change is visible in PR diffs.
- Reproducibility: any commit contains complete runtime artifacts.
- Cross-language consistency: Python and Java generated outputs evolve together.
- Review quality: reviewers can inspect actual emitted constants/messages, not only generator logic.
- Operational safety: build/use workflows are less dependent on local generator availability.

## Tradeoffs

- Larger diffs when status definitions change.
- More frequent merge conflicts in generated files.
- Additional discipline required to regenerate artifacts during updates.

## Update Workflow

When status definitions or generation logic changes:

1. Update source/spec files.
2. Regenerate artifacts.
3. Commit source changes and generated outputs in the same change.
4. Verify Python and Java consumers still resolve status constants/messages.

## Commit Rule

- Do not submit status definition changes without updated generated artifacts.
- Do not hand-edit generated files unless explicitly debugging and followed by regeneration.

