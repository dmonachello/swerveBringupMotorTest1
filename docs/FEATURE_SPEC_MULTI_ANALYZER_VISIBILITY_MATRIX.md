SPEC_STATUS: NOT_IMPLEMENTED

# Multi-Analyzer Visibility Matrix Spec

Purpose: Define a PC-local visibility matrix for multiple CAN analyzers.

## User Value

Purpose: Explain what the feature provides to the user and how it helps debug CAN issues.

- Provides concrete evidence for wiring or termination issues without claiming exact fault location.
- Helps isolate where along the bus a device disappears by comparing sources.
- Separates device silent from source unavailable so gaps are not misread.
- Makes observation differences obvious without interpreting them.
- Shows, at a glance, which analyzers see each device right now.
- Enables fast checks during bringup: move analyzers and watch the matrix change.

## Feature Points Addressed

Purpose: Explicitly map each feature point to a concrete user-facing behavior.

- Provides concrete evidence for wiring or termination issues without claiming exact fault location.
  Evidence: visibility flips across adjacent analyzer positions show a propagation boundary for many devices at once.
  Limits: the matrix does not claim the exact connector or break location.
- Helps isolate where along the bus a device disappears by comparing sources.
  Evidence: per-device row shows the first source where visibility changes from `Y` to `N`.
  Usage: compare rows for multiple devices to confirm the same boundary.
- Separates device silent from source unavailable so gaps are not misread.
  Evidence: source availability is shown as `?` and is distinct from `N`.
  Usage: `N` means not visible at an available source; `?` means source offline.
- Makes observation differences obvious without interpreting them.
  Evidence: the matrix presents raw `Y`/`N`/`?` without automatic diagnosis labels.
  Usage: the operator sees differences directly and decides next steps.
- Shows, at a glance, which analyzers see each device right now.
  Evidence: one row per device and one column per analyzer with live state.
  Usage: the matrix is the primary at-a-glance view.
- Enables fast checks during bringup: move analyzers and watch the matrix change.
  Evidence: analyzer placement changes cause immediate, visible column changes.
  Usage: move an analyzer and confirm the boundary shifts as expected.

## What The User Gets

Purpose: Summarize the user-facing outputs.

- A live visibility matrix (CLI and UI) with one column per analyzer and one row per device.
- Per-device drill-down showing age, rate, and last-seen timing at each source.
- A summary view that counts devices visible everywhere vs partially vs nowhere.
- Clear unavailable-source indicators (`?`) that prevent false negatives.

## Example Diagnostic Interpretations

Purpose: Show how a user can read the matrix without implying exact fault location.

- Pattern: `Y Y Y` for a device across all sources.
  Interpretation: device traffic is seen consistently; wiring and termination are likely OK for that segment.
- Pattern: `Y Y N` where the `N` is at the far end source.
  Interpretation: traffic is present near the robot but not at the far end; investigate downstream wiring, termination, or analyzer placement.
- Pattern: `Y N N` for a device with the `Y` closest to the device.
  Interpretation: device is alive locally but traffic is not propagating; suspect a bus break or short between the first and second analyzer.
- Pattern: `N Y Y` for a device with the `N` closest to the robot.
  Interpretation: device might be on a branch that bypasses the first analyzer or the first analyzer is missing traffic; verify analyzer placement.
- Pattern: `N N N` for an expected device.
  Interpretation: device not visible anywhere; check power, CAN ID, or the device itself.
- Pattern: `? ? ?` for a source column.
  Interpretation: source is unavailable; do not conclude anything about visibility until the source is online.
- Pattern: Mixed `Y` and `N` that flips when moving an analyzer.
  Interpretation: confirms the analyzer location is affecting observation; use to narrow the fault region.

## Scope

Purpose: Define what this feature includes and excludes.

- Includes simultaneous ingestion from multiple CAN analyzers.
- Includes per-source device tracking and metrics.
- Includes visibility matrix, CLI output, and UI output.
- Excludes automatic topology discovery.
- Excludes fault localization or branch inference.
- Excludes NetworkTables publication for this feature.

## Constraints

Purpose: Capture non-negotiable rules that shape implementation.

- The PC tool remains read-only on CAN and must never transmit frames.
- Windows is the primary host; avoid Linux-only assumptions.
- This feature does not add or change NetworkTables keys.
- Visibility data stays in-process in the bridge; no TCP transport.

## Terminology

Purpose: Define the core terms.

- Source: a configured CAN analyzer instance.
- Device: a CAN device identified by (manufacturer, deviceType, deviceId).
- Visibility: a device is visible at a source if last_seen is within the timeout.
- Visibility Matrix: rows are devices and columns are sources with visible/not visible cells.

### Arb-id mapping and canonical keys

Purpose: Make it explicit how frames map to device identity.

- The sniffer MUST provide the raw `arb_id` for every frame.
- If a decoder maps `arb_id` to `(manufacturer, deviceType, deviceId)`, the provider should use that canonical `mfg:type:id` key.
- If no mapping exists, the provider MUST fall back to a stable canonical key of the form `arb:0x{arb_id:x}` (hex).

## Current Interfaces

Purpose: Inventory existing Java/Python NetworkTables usage for awareness only.

- Java writes: `bringup/ui/*`, `bringup/ui_tcp/*`, `bringup/tests/*`.
- Java reads: `bringup/diag/*` (device presence, console, pc summary), `bringup/ui/cmd/*`.
- Python writes: `bringup/diag/*` (device presence, console, pc summary), `bringup/ui/cmd/*`.
- Python reads: `bringup/ui/state/*`, `bringup/tests/*`, `bringup/diag/dev/*` presence values.
- This feature must not add or modify any NetworkTables keys.

## In-Process Interface

Purpose: Define the PC-local visibility provider API.

- Visibility data is computed and served in the same process as the bridge.
- No TCP or NetworkTables transport is used for this feature.
- CLI and UI query the provider directly.

## Visibility Provider API

Purpose: Specify the required public interface.

- `set_sources(sources)` load configured analyzers and order.
- `set_expected_devices(devices)` load expected devices from the active profile.
- `ingest_frame(source_id, arb_id, ts_ms, decoded_key=None)` record a frame for a source.
- `set_source_available(source_id, available, ts_ms)` update source availability.
- `tick(now_ms)` recompute rates and visibility.
- `snapshot(scope, now_ms)` return the full matrix (see data shapes below).
- `snapshot_device(selector, now_ms)` return per-source detail for one device.
- `summary(scope, now_ms)` return aggregate counts.

Notes:

- Timestamps use unix epoch milliseconds (`ts_ms`, `now_ms`, `lastSeenMs`).
- `ingest_frame` should be safe on the hot path and keep updates small.

## Snapshot Data Shapes

Purpose: Define the data returned to CLI and UI.

- `VisibilitySnapshot`:
  - `sources`: list of `{id, label, available}`.
  - `devices`: list of `{key, label, visibility, metrics, unexpected?}`.
  - `timeoutMs`: integer.
  - `tsMs`: unix epoch milliseconds.
  - `scope`: one of `expected`, `observed`, or `both`.

- `VisibilitySnapshot` device fields:
  - `key`: string, e.g. `mfg:type:id` or fallback `arb:0x123`.
  - `label`: string or empty.
  - `visibility`: object mapping `source_id -> true|false|null` where `null` indicates source unavailable.
  - `metrics`: object mapping `source_id -> {ageMs, framesPerSec, msgCount, lastSeenMs}` or `null` when source unavailable.
  - `unexpected` (optional): boolean, true when device was observed but not in the active profile.

- `DeviceVisibilitySnapshot`:
  - `device`: `{key, label}`.
  - `sources`: list of `{id, label, available, visible, ageMs, framesPerSec, msgCount, lastSeenMs}`.

- `VisibilitySummary`:
  - `sources`: number.
  - `devicesShown`: number.
  - `visibleAll`: number.
  - `visibleSome`: number.
  - `visibleNone`: number.

Example (VisibilitySnapshot, epoch ms):

```json
{
  "sources": [
    {"id":"rio_end","label":"RIO End","available":true},
    {"id":"mid_bus","label":"Mid Bus","available":false}
  ],
  "devices": [
    {
      "key":"rev:neo:10",
      "label":"FL_DRIVE",
      "visibility":{"rio_end":true,"mid_bus":null},
      "metrics":{
        "rio_end":{"lastSeenMs":1700000000123,"ageMs":120,"msgCount":600,"framesPerSec":50.0},
        "mid_bus":null
      }
    }
  ],
  "timeoutMs":1000,
  "tsMs":1700000000123,
  "scope":"expected"
}
```

## Threading Model

Purpose: Define how the provider is used safely.

- The existing sniffer loop thread calls `ingest_frame` and `tick`.
- CLI and UI read snapshots from the same provider.
- Provider protects shared state with a lock or uses copy-on-write snapshots.

## Source Configuration

Purpose: Define how multiple analyzers are configured.

- Add a data-driven source list file (example `config/sources.json`) or CLI flag that supports multiple entries.
- Each source defines `id`, `label`, `port`, and `enabled`.
- Source IDs must be unique.
- Disabled sources are not opened and are marked unavailable in updates.

Example `sources.json` snippet:

```json
{
  "sources": [
    {"id":"rio_end","label":"RIO End","port":"COM3","enabled":true,"visibilityTimeoutMs":1000},
    {"id":"mid_bus","label":"Mid Bus","port":"COM4","enabled":true}
  ]
}
```

Notes:

- `visibilityTimeoutMs` is an optional per-source override.
- v1 default is `1000` ms.

## Analyzer Topology Nodes

Purpose: Define how analyzer placement is represented in topology.

- Add a new topology node type `analyzer` that represents a physical analyzer location on the CAN bus.
- Analyzer nodes have no CAN ID and do not emit traffic.
- Analyzer nodes exist only to mark placement relative to devices and segments.
- Analyzer nodes are diagram-only and do not appear in device lists.

Mapping rules:

- Each configured source SHOULD reference a topology analyzer node by id.
- If a source has no topology node, it still functions, but UI placement-based interpretations are unavailable.
- Multiple analyzers may exist without any connected source (planning or offline use).

CLI expectations:

- The CLI should support adding analyzer nodes to the topology and linking them like other topology nodes.
- The node type must be explicit so it can be rendered and filtered distinctly from devices.

## Neighbor Ports Model

Purpose: Define directed, port-based adjacency for neighbor relationships.

- Neighbor relationships are not inferred from x/y coordinates.
- Each node exposes a finite set of named ports based on node type.
- Links connect a specific port on one node to a specific port on another.
- This supports linear nodes (2 ports) and branch nodes (>2 ports) without ambiguity.

Port rules:
- Linear devices: ports `left`, `right`.
- End devices: port `next` only.
- Branch nodes: ports `left`, `right`, `branch1`, `branch2` (extendable).
- Analyzer nodes: ports `left`, `right` by default unless configured as branch taps.

Schema (diagram metadata):

```json
{
  "neighborPorts": [
    { "node": 12, "port": "left", "neighbor": 10, "neighborPort": "right" },
    { "node": 12, "port": "right", "neighbor": 14, "neighborPort": "left" },
    { "node": 12, "port": "branch1", "neighbor": 30, "neighborPort": "next" }
  ]
}
```

Compatibility:
- `neighborLinks` is deprecated for topology-aware inference.
- If both are present, `neighborPorts` takes precedence.

## Per-Source Metrics

Purpose: Define required metrics for each (device, source) pair.

- Required: `lastSeenMs`, `ageMs`, `msgCount`, `framesPerSec`.
- Optional: `errorCount`, `droppedFrames`, `captureState`.

## Visibility Rules

Purpose: Define how visibility is computed.

- Visible when `now_ms - lastSeenMs <= visibilityTimeoutMs`.
- `visibilityTimeoutMs` is a global config value in v1.
- Default `visibilityTimeoutMs` is `1000` ms.

## Matrix Model

Purpose: Define the in-memory visibility matrix shape.

- Rows are devices and columns are sources.
- Source order uses configured order.
- Device order uses label, then canonical key.

## Device Scope

Purpose: Define which devices appear in the matrix.

- Scope A: observed devices from any source.
- Scope B: expected devices from the active profile.
- Default: show expected devices when a profile is loaded, otherwise observed only.
- Observed-but-unexpected devices are included and flagged as `unexpected: true`.
- Expected devices with no visibility show `N` or `?` in all columns.

## Observed Device Retention

Purpose: Avoid instant disappearance of observed-but-unexpected devices.

- Observed devices are retained for a short window after last seen.
- Default `observedRetentionSec` is `10.0`.
- Expected devices are always included even if not seen.

## Source Availability

Purpose: Separate source availability from device visibility.

- Unavailable sources are reported in `sources[].available`.
- UI and CLI must indicate unavailable sources distinctly from `not visible`.
- Suggested cell marker for unavailable: `?`.

Mapping to text: `true -> Y`, `false -> N`, `null -> ?`.

## CLI Output

Purpose: Define CLI commands and output shape.

- `show visibility` prints the matrix with one column per source.
- `show visibility <device>` prints per-source metrics for one device.
- `show visibility summary` prints aggregate counts.
- `--json` returns the snapshot data shapes defined above.

## CLI Examples

Purpose: Provide concrete text examples.

```text
Device       rio_end  mid_bus  pdh_end
FL_DRIVE     Y        Y        ?
FR_DRIVE     Y        Y        Y
INTAKE       Y        N        ?
CLIMBER      N        Y        ?
```

```text
Device: FL_DRIVE
Key: 5:2:10

Source     Visible  Age(s)  FPS
rio_end    Y        0.12    50.0
mid_bus    Y        0.10    49.5
pdh_end    ?        -       -
```

Additional CLI examples:

```text
bridge(config-profile-home_031226)# show visibility
Device        rio_end  mid_bus  pdh_end
FL_DRIVE      Y        Y        N
FR_DRIVE      Y        Y        Y
INTAKE        Y        N        N
CLIMBER       ?        ?        ?
PDH           Y        Y        Y
ROBORIO       Y        Y        Y
UNKNOWN(arb:0x18feef00)  N      ?        ?

Legend: Y=visible, N=not visible, ?=source unavailable
Scope: expected+observed (profile=home_031226)
Observed retention: 10s  Visibility timeout: 1.0s
```

```text
bridge(config-profile-home_031226)# show visibility FL_DRIVE
Device: FL_DRIVE
Key: rev:neo:10

Source     Available  Visible  Age(s)  FPS
rio_end    Y          Y        0.12    50.0
mid_bus    Y          Y        0.10    49.5
pdh_end    Y          N        2.47    0.0
```

```text
bridge(config-profile-home_031226)# show visibility summary
Sources: 3
Devices shown: 12
Visible at all sources: 7
Visible at some sources only: 4
Visible at no sources: 1
Unavailable sources: 0
```

```json
{
  "sources":[
    {"id":"rio_end","label":"RIO End","available":true},
    {"id":"mid_bus","label":"Mid Bus","available":true},
    {"id":"pdh_end","label":"PDH End","available":true}
  ],
  "devices":[
    {
      "key":"rev:neo:10",
      "label":"FL_DRIVE",
      "visibility":{"rio_end":true,"mid_bus":true,"pdh_end":false},
      "metrics":{
        "rio_end":{"lastSeenMs":1700000000123,"ageMs":120,"msgCount":600,"framesPerSec":50.0},
        "mid_bus":{"lastSeenMs":1700000000100,"ageMs":100,"msgCount":598,"framesPerSec":49.5},
        "pdh_end":{"lastSeenMs":1699999998000,"ageMs":2470,"msgCount":0,"framesPerSec":0.0}
      }
    }
  ],
  "timeoutMs":1000,
  "tsMs":1700000000123,
  "scope":"expected"
}
```

## UI Output

Purpose: Define the visibility matrix view in the UI.

- Table with Device and one column per source.
- Clear visible/not-visible indicators with text fallback.
- Sorting by device label, canonical key, or visible-source count.
- Filtering by visibility state or text match.
- Live refresh based on in-process snapshot updates.

### Topology Overlay

Purpose: Define how matrix state colors nodes on the topology map.

- Use only `grey`, `red`, `yellow`, and `green` in visibility mode.
- Green: device visible at all available sources.
- Yellow: device visible at some available sources.
- Red: device visible at no available sources.
- Grey: visibility unknown because all sources are unavailable.
- Analyzer nodes show availability state and do not use device visibility colors.

UI examples:

Matrix view (table):

```text
+------------------------------+---------+---------+---------+---------+
| Device                       | rio_end | mid_bus | pdh_end | Visible |
+------------------------------+---------+---------+---------+---------+
| FL_DRIVE                     |    Y    |    Y    |    N    |   2/3   |
| FR_DRIVE                     |    Y    |    Y    |    Y    |   3/3   |
| INTAKE                       |    Y    |    N    |    N    |   1/3   |
| CLIMBER                      |    ?    |    ?    |    ?    |   ?/3   |
| PDH                          |    Y    |    Y    |    Y    |   3/3   |
| UNKNOWN (arb:0x18feef00)     |    N    |    ?    |    ?    |   ?/3   |
+------------------------------+---------+---------+---------+---------+
```

Topology overlay (nodes):

```text
RIO --- FL_DRIVE --- FR_DRIVE --- INTAKE --- CLIMBER --- PDH
  G         G            G          Y         ?         G

Legend:
G = visible at all available sources
Y = visible at some sources
R = visible at no available sources
? = all sources unavailable
```

## Update Model

Purpose: Define how updates occur.

- PC sniffer recomputes visibility on a fixed cadence.
- Visibility provider stores the latest matrix snapshot per update.
- CLI and UI queries read the latest stored snapshot from the provider.

## Error Handling

Purpose: Define resilience rules.

- One analyzer failing must not break the matrix.
- Bad source data is isolated to that source.
- CLI and UI remain functional if one source drops out.
- No unhandled exceptions on missing data.

Error guidance:

- If a source fails to open, mark `available=false` and log a warning; continue running.
- If duplicate source IDs are configured, prefer failing fast at startup and log the error.

## Performance

Purpose: Keep runtime cost small and predictable.

- Target 2-4 sources and tens of devices.
- Avoid quadratic scans of message history.
- Use rolling counters and timestamps.

## Logging

Purpose: Provide minimal debug visibility.

- Log source online/offline transitions at debug level.
- Log per-device visibility transitions at debug level.

Suggested debug events:

- `source_availability_change{source_id,available,ts_ms}`
- `device_visibility_change{device_key,source_id,from,to,ts_ms}`

## Acceptance Criteria

Purpose: Define when the feature is done.

- Multiple analyzers run simultaneously and stay isolated.
- Each source reports visibility independently.
- CLI `show visibility` and `show visibility summary` work.
- UI shows the same matrix state as CLI.
- Expected devices with no visibility are shown.
- Source unavailability is distinguishable from invisibility.

### Automated tests (suggested)

- Unit: new VisibilityProvider unit tests covering:
- ingest_frame from two sources -> snapshot shows Y/N/null as expected.
- set_source_available(false) -> snapshot shows `available=false` and `visible=null` for that source.
- Integration: replay a short pcap for two analyzers, run `show visibility --json`, assert snapshot fields and counts.

## Tradeoffs

Purpose: Document key design tradeoffs.

- In-process avoids TCP or NT churn but ties visibility to the bridge process lifetime.
- Full-matrix updates are simple but heavier than deltas.
- Profile-based expected devices simplify interpretation but require profile sync.

## Future Extensions

Purpose: List explicitly deferred follow-ons.

- Topology-aware fault region inference.
- Visibility pattern classification and confidence scoring.
- Group-level summaries and topology overlays.
- Per-source visibility timeouts.

## Appendix A: Using The Matrix To Find CAN Breaks

Purpose: Explain how the matrix helps isolate where traffic stops propagating.

- Place analyzers at known points along the bus (for example `rio_end`, `mid_bus`, `pdh_end`).
- Compare columns to find where visibility transitions from `Y` to `N`.
- Patterns to interpret:
- `Y Y N` for a device: traffic seen near robot and mid-bus but not at the far end.
  Interpretation: likely issue between `mid_bus` and `pdh_end` (break, termination, or wiring).
- `Y N N`: traffic seen only near the robot.
  Interpretation: likely issue between `rio_end` and `mid_bus`.
- `N Y Y`: traffic seen away from robot but not at the robot end.
  Interpretation: analyzer placement mismatch or a branch bypassing the robot-side analyzer.
- Use movement to confirm:
- Move the middle analyzer toward one side and see whether the visibility boundary shifts.
- A shifting boundary narrows the physical segment containing the fault.
- Distinguish break vs device offline:
- If many devices disappear after the same point, suspect a bus break or termination.
- If only one device disappears while others remain visible, suspect that device's power, ID, or local wiring.

## Appendix B: What The Matrix Tells You

Purpose: State the concrete inferences the matrix supports.

- It shows where traffic is seen and where it stops for each device.
- It distinguishes device-specific issues from bus-wide issues by comparing many devices at once.
- It indicates how far a device's traffic propagates across analyzer positions.
- It shows when analyzers are unavailable (`?`), preventing false conclusions.

## Appendix C: Allowed Inferences (And Limits)

Purpose: Keep diagnosis evidence-based without overclaiming precision.

- Allowed:
- A device is talking if any available source sees it.
- A propagation boundary exists between two analyzer locations when visibility flips.
- A bus segment is likely suspect when many devices disappear after the same point.
- A device is likely suspect when only that device disappears while others remain visible.
- Not allowed in v1:
- Exact fault location or connector identification.
- Short vs open diagnosis without additional tests.
- Branch topology inference beyond what the analyzer placement already implies.

## Appendix D: Bus State Classification

Purpose: Provide common bus-level states inferred from the matrix.

- OK: most devices visible at all available sources.
- Dead: no devices visible at any available source.
- Divided or segmented: clear visibility boundary across analyzer positions.
- Degraded: visibility is intermittent or low-rate across sources.
- Device-specific failure: one or a few devices missing while others are visible.
- Source unavailable: analyzers offline; visibility is unknown (`?`), not a bus state.

