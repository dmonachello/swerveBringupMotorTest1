Purpose: Document the shared Python helper modules under tools/common.

# Shared Code Libraries

## Overview
Purpose: Centralize small, dependency-free helpers used across multiple Python tools.

These modules live under `tools/common/` and are intended to reduce duplicated
logic without changing behavior. They are utilities only (no business logic).

## Module Catalog

### tools/common/cli_helpers.py
Purpose: Standardize common CLI arguments.

Use for `--input`, `--output`, and `--path` flags so help text and defaults stay consistent.

Examples:
- `add_input_arg(parser, default="data.json", help_text="Input JSON.")`
- `add_output_arg(parser, default="out.json", help_text="Output JSON.")`
- `add_path_arg(parser, default="notes.md", help_text="Path to notes.")`

### tools/common/json_io.py
Purpose: Consistent UTF-8 JSON read/write.

Use to avoid repeating `read_text` / `write_text` encoding logic.

Examples:
- `payload = read_json(Path("data.json"))`
- `write_json(Path("out.json"), payload, indent=2)`

### tools/common/paths.py
Purpose: Centralized repo path resolution.

Use for shared file locations so tools stay aligned.

Examples:
- `profiles_canonical_path()` -> `data/bringup_system.json`
- `profiles_deploy_path()` -> `src/main/deploy/bringup_system.json`
- `tests_deploy_path()` -> `src/main/deploy/bringup_tests.json`
- `can_mappings_path()` -> `src/main/deploy/can_mappings.json`
- `logs_dir()` -> `tools/can_nt/logs`

### tools/common/profile_io.py
Purpose: Shared profile hash and schema checks.

Use to keep `data_hash` calculation and schema validation consistent.

Examples:
- `compute_profiles_hash(payload)`
- `validate_profiles_schema(payload, schema_version=4)`

### tools/common/tests_io.py
Purpose: Shared bringup_tests.json handling.

Use to load/write tests payloads and extract test names without duplicating logic.

Examples:
- `payload = load_tests_payload(tests_deploy_path())`
- `write_tests_payload(tests_deploy_path(), payload)`
- `names = extract_test_names(payload)`

### tools/common/time_utils.py
Purpose: Standardized timestamp formatting.

Use for `data_version` stamps and human-readable timestamps.

Examples:
- `timestamp_version()` -> `YYYY-MM-DD_HHMMSS`
- `timestamp_compact("sniffer")` -> `sniffer_YYYYMMDD_HHMMSS`
- `timestamp_human()` -> `YYYY-MM-DD HH:MM:SS`
- `timestamp_hms()` -> `HH:MM:SS`

### tools/common/text_io.py
Purpose: Consistent text file line IO.

Use for reading and writing line-based files.

Examples:
- `lines = read_lines(Path("table.txt"))`
- `write_lines(Path("out.txt"), lines)`

### tools/common/can_id.py
Purpose: Shared FRC CAN extended-ID decode.

Use to decode 29-bit arbitration IDs consistently across tools.

Examples:
- `decoded = decode_frc_ext_id(arb_id)`
- `decoded.manufacturer`, `decoded.device_type`, `decoded.api_class`, `decoded.api_index`, `decoded.device_id`

### tools/common/topology_render.py
Purpose: Shared topology rendering mappings and SVG shapes.

Use to keep category-to-shape and vendor color logic consistent between the topology editor and HTML visualization.

Examples:
- `shape_kind_for_category("neos")`
- `vendor_key_for_category("krakens")`
- `fill_color_for_vendor("CTRE")`
- `svg_shape_for_kind("motor", x0, y0, x1, y1, fill, outline)`

## Usage Guidelines
Purpose: Keep shared utilities small, stable, and low-risk.

- Prefer using helpers rather than re-implementing file IO or timestamps.
- Avoid adding business logic here; keep these modules dependency-free.
- Keep existing behavior and outputs stable when migrating.

## Tradeoffs
Purpose: Make the consequences of shared utilities explicit.

- Pros: Consistent behavior, fewer bugs from drift, easier maintenance.
- Cons: Indirection adds a small learning curve; changes affect multiple tools.

## Future Extensions
Purpose: Track likely additions without committing to behavior changes.

- Shared profile payload validation and repair helpers.
- Shared JSON schema evolution and migration tooling.
- Shared CAN inventory diff helpers and reporting formatters.
