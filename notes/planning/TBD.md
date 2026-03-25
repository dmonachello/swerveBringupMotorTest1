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
- Topology app: add a feature to break up a selected long segment into multiple segments and distribute the nodes across all segments.

## Documentation Gaps / Planned Fields
- Some report rows are vendor-tool-only or planned fields (e.g., last error codes, reset flags); complete or remove as appropriate.

## NetworkTables Contract Follow-ups
- Align `bringup/diag/busErrorCount` publishing: Java reads it, current Python tool does not publish it.

## Tests
- If performance is an issue, consider moving the CANable sniffer capture loop to a dedicated C program and keep Python for analysis/publishing.
- Add runtime counters (frames received vs processed, max queue depth, processing lag) to verify Python CAN sniffer keeps up with CANable traffic.
- The first test tbd idea.

## UI Performance Tuning (Live Topology)
- Work done: add live overlay change detection (skip redraw when derived state is unchanged), quantize telemetry, ignore timestamp-only churn, and file mtime checks.
- Work done: add adaptive polling backoff and idle pause for live overlay polling.
- Work done: reduce idle UI polling frequency when disconnected/no overlay.
- Next: cap redraw FPS (separate poll rate from render rate).
- Next: incremental redraw (only update changed nodes rather than full canvas).
- Next: move TCP/NT to background reader with event queue, keep a slower UI tick (Tk-safe).
- Next: add optional file system watcher to eliminate JSON polling.
