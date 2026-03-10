# TBD Work Tracker

Purpose: Consolidate all planned or future work discussed so far.

## Dashboard Migration
- Migrate from Shuffleboard to Elastic for the driver dashboard.
- Use AdvantageScope for debugging and visualization workflows.
- Port the current Shuffleboard layout (presenceConfidence tiles + bringup tree) into Elastic.

## Reverse Engineering (Python Tool)
- Add capture session tagging: `--session` and `--session-dir` to group outputs.
- Add API inventory output: `--dump-api-inventory` JSON with `(mfg,type,id,apiClass,apiIndex)` counts and rates.
- Add inventory diff: `--diff-inventory A.json B.json` with new/missing pairs and biggest rate changes.
- Add byte fingerprinting per `(mfg,type,id,apiClass,apiIndex)` with change positions and entropy/variation.
- Add NetworkTables publishing under `bringup/diag/can/...` for inventory and summaries.
- Add decoder registry keyed by `(manufacturer, deviceType, apiClass, apiIndex)` with confidence scoring.
- Add replay mode that re-emits markers during offline analysis.
- Add optional marker label indices in bytes 6..7 for offline correlation.

## Reverse Engineering Roadmap (Process)
- Stage 1: Inventory capture of `(manufacturer, device type, device id, api class, api index)` + rates.
- Stage 2: Controlled experiments with one variable at a time + PCAP + inventory snapshots.
- Stage 3: Diff inventories to flag command-like vs periodic status frames.
- Stage 4: Fingerprint byte changes and score confidence per candidate field.
- Stage 5: Publish insights to NetworkTables without breaking existing keys.

## Architecture Future Extensions
- Add more controller types in `bringup_bindings.json` beyond Xbox.
- Add new test check types without changing existing JSON fields.
- Add dashboard widgets for live test status and PC tool health.
- Maintain decoder registry for CAN reverse engineering outputs.

## Documentation Gaps / Planned Fields
- Some report rows are vendor-tool-only or planned fields (e.g., last error codes, reset flags); complete or remove as appropriate.

