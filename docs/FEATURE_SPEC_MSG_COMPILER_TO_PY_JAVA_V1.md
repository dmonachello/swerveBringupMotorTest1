SPEC_STATUS: NOT_IMPLEMENTED

# Feature Spec: MSG Compiler to Python and Java (V1)

## Purpose

Define a deterministic utility that compiles OpenVMS-style `.MSG` files into generated Python and Java status-code include artifacts.

## Goal

Provide one source-of-truth message definition flow where `.MSG` files are machine-validated and compiled into language-specific artifacts used by:

- Python CLI and tooling status handling.
- Java robot/UI status handling.
- Shared status reporting and test assertions.

## Scope

In scope:

- Parse `.MSG` files under a configured source directory.
- Validate facilities, severities, message names, and message text.
- Generate Python include artifact(s).
- Generate Java include artifact(s).
- Generate a machine-readable intermediate catalog JSON.
- Fail fast on compile errors.
- Support strict deterministic output ordering.

Out of scope (V1):

- Runtime localization.
- Automatic migration of legacy ad hoc status strings.
- Dynamic reload while processes are running.

## Source Model

### Input Files

Default source directories:

- `tools/status_codes/vms_msg/`
- `tools/status_codes/vms_msg_surface/` (optional profile mode)

Accepted file extension:

- `.MSG` (case-insensitive)

### Supported Directives

Compiler supports these directives:

- `.TITLE <text>`
- `.IDENT /<text>/`
- `.FACILITY <name>,<number> /PREFIX=<prefix>_`
- `.SEVERITY <SUCCESS|INFORMATION|WARNING|ERROR|FATAL>`
- Message line: `<MESSAGE_NAME>, "<message text>"`
- `.END`

Unknown directives:

- Non-interactive mode: compile fails.
- Interactive mode (future): prompt may be allowed, but V1 CLI defaults to fail.

## Canonical Semantics

### Names

- Case-insensitive parse, canonicalized to uppercase.
- Facility names must be globally unique.
- Message names must be unique within a facility.
- Numeric `(facility, message, severity)` collisions are not allowed.

### Ordering

Generated outputs are deterministic:

- Facilities sorted by facility number then name.
- Messages sorted by severity rank then message name.
- Severity rank: `SUCCESS`, `INFORMATION`, `WARNING`, `ERROR`, `FATAL`.

### Last-One-Wins Policy

V1 policy is explicit and strict:

- Duplicate symbol with different numeric assignment: error.
- Duplicate symbol with identical full definition: allowed but warns.
- Effective output follows last definition only when duplicates are byte-identical.

## Compiler Outputs

## Intermediate Catalog

Compiler always emits an intermediate catalog:

- `tools/status_codes/generated/status_catalog.compiled.json`

Catalog includes:

- Compiler version.
- Source file list and content hash.
- Normalized severities/facilities/messages.
- Encoded status numeric fields.
- Validation warnings.

## Python Output

Default generated files:

- `tools/can_nt/status/generated/status_catalog_generated.py`
- `tools/can_nt/status/generated/status_messages_generated.py`
- `tools/can_nt/status/generated/status_runtime_generated.py`

Python requirements:

- No runtime parsing of `.MSG`.
- Import-only constants/tables.
- Stable names for status checks and printing.
- Include `GENERATED_FROM_HASH` for parity checks.

## Java Output

Default generated files:

- `src/main/java/frc/robot/status/generated/StatusCatalogGenerated.java`
- `src/main/java/frc/robot/status/generated/StatusMessagesGenerated.java`
- `src/main/java/frc/robot/status/generated/StatusRuntimeGenerated.java`

Java requirements:

- `public final` constants-only classes.
- No reflection required.
- Include `GENERATED_FROM_HASH` for parity checks.
- Compatible with existing robot build pipeline.

## CLI Contract

Primary command:

- `python tools/status_codes/compile_msg_to_lang.py`

Arguments:

- `--src <dir>` repeatable.
- `--out-py <dir>` optional override.
- `--out-java <dir>` optional override.
- `--out-catalog <path>` optional override.
- `--strict` (default true in CI).
- `--check` verify up-to-date, no writes.
- `--fail-on-warning` optional.

Exit codes:

- `0` success.
- `1` compile/validation error.
- `2` check-mode mismatch (generated outputs stale).

## Validation Rules

The compiler must validate:

- Facility number range is legal integer range for project encoding.
- Message number range is legal integer range for project encoding.
- Severity is one of allowed values.
- Message text must be non-empty.
- No orphan message lines before `.FACILITY` and `.SEVERITY`.
- File must terminate with `.END`.

Failure behavior:

- Non-interactive should fail.
- No partial writes on failure.

## Atomic Write Rules

Compiler writes outputs atomically:

- Write temp files first.
- Validate generated content.
- Replace targets in one commit phase.
- If any write fails, roll back all generated artifacts.

## Integration Points

## Python Integration

- Existing Python status modules switch from manual tables to generated imports.
- Existing message rendering path remains behavior-compatible.

## Java Integration

- Java status reporting paths consume generated constants/messages.
- `ack/status` string behavior remains backward-compatible until explicit migration.

## CI Integration

Add CI job step:

- Run compiler in `--check --strict` mode.
- Fail if source and generated outputs drift.

## Compatibility and Migration

V1 migration strategy:

- Keep existing status API call sites stable.
- Introduce generated modules/classes under `generated/` namespace.
- Provide one iteration where legacy paths proxy to generated data.
- Remove legacy manual catalogs in V2 cleanup.

## Testing Plan

Unit tests:

- Parser directive handling.
- Duplicate and collision detection.
- Deterministic ordering snapshots.
- Numeric encoding parity tests.

Golden tests:

- Known `.MSG` inputs produce exact Python and Java outputs.

Failure tests:

- Missing `.END`.
- Invalid severity.
- Duplicate conflicting symbol.
- Unknown directive in strict mode.

Cross-language parity tests:

- Compare generated Python and Java facility/message maps against compiled catalog.

## Example Input and Output Summary

Example input:

- `.FACILITY EXECUTOR,3 /PREFIX=EXECUTOR_`
- `.SEVERITY ERROR`
- `INVALID_STATE, "Executor state invalid."`

Expected generated symbols:

- Python: `SS__EXECUTOR__INVALID_STATE`
- Java: `StatusCatalogGenerated.SS__EXECUTOR__INVALID_STATE`
- Shared text: `"Executor state invalid."`

## Risks and Tradeoffs

Tradeoffs:

- Compiler strictness improves safety but may block quick edits.
- Generated files reduce drift but add build-step discipline.

Risks:

- Manual edits to generated outputs.
- Divergent project encoding assumptions.

Mitigations:

- Header banners: generated file do-not-edit markers.
- CI check mode enforcement.
- Single encoder implementation shared by both generators.

## Future Extensions

- Emit C/C++ and TypeScript targets.
- Emit markdown/HTML status catalog docs from same source.
- Add localization layers by message key.
- Add source map from generated symbol back to `.MSG` file and line.


