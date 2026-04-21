# NetworkTables Contract

## Purpose
Define the NetworkTables (NT) key contract between the robot bringup harness (Java, roboRIO) and the PC CAN sniffer tool (Python, Windows).

## Scope
- Keys under `bringup/diag/...`: published by the PC tool, read by the robot and dashboards.
- Keys under `bringup/tests/...`: published by the robot, read by dashboards and optional PC UI/CLI surfaces.

## Rules
Purpose: Keep the interface stable and safe.

- Key paths are an API contract. Additive changes only for alpha.
- Ownership is single-writer per key:
  - PC tool owns `bringup/diag/...`.
  - Robot owns `bringup/tests/...` and other robot-local bringup tables.
- Java must fail soft when the PC tool is absent (missing keys are treated as stale/unavailable).

## Host vs Robot Context (Non-NT)
Purpose: Prevent confusion about what NetworkTables does and does not define.

- NetworkTables is diagnostics/state visibility only.
- The robot "active profile" is a robot runtime concept controlled via robot args/Xbox/TCP commands.
- The CLI/topology editor "active profile" is host-local editing/inspection context.
- Host context MUST NOT change robot context unless an explicit TCP robot command is executed (for example `profiles activate <name>`).

## PC Tool -> Robot (`bringup/diag/...`)
Purpose: Publish passive CAN visibility/presence telemetry.

### Global Keys
- `bringup/diag/busErrorCount` (`double`)
  - Meaning: PC-observed bus error counter if available (otherwise may be unset/0 depending on capture backend).
- `bringup/diag/can/summary/json` (`string`)
  - Meaning: Compact JSON summary (fps, missing count, top talkers, capture health).
- `bringup/diag/can/pc/heartbeat` (`double`)
  - Meaning: Monotonic-ish heartbeat timestamp (seconds); robot uses age to detect staleness.
- `bringup/diag/can/pc/openOk` (`string`)
  - Meaning: `"YES"` when capture is open; otherwise unset/`"NO"` depending on mode.
- `bringup/diag/can/pc/framesPerSec` (`double`)
- `bringup/diag/can/pc/framesTotal` (`double`)
- `bringup/diag/can/pc/readErrors` (`double`)
- `bringup/diag/can/pc/lastFrameAgeSec` (`double`)

### Per-Device Keys
Purpose: Provide per-device presence/age by label identity.

Label key encoding:
- `labelKey = encode_label_for_nt(<device label>)`
- The label comes from `bringup_system.json` devices-table entries.

Keys (per device):
- `bringup/diag/dev/<labelKey>/label` (`string`)
- `bringup/diag/dev/<labelKey>/status` (`string`)
  - Values: `OK`, `MISSING`, `CONTROL_ONLY`.
- `bringup/diag/dev/<labelKey>/presenceSource` (`string`)
  - Values: `STATUS`, `TRAFFIC`, `CONTROL_ONLY`, `NONE`.
- `bringup/diag/dev/<labelKey>/presenceConfidence` (`string`)
  - Values: `HIGH`, `LOW`, `NONE`.
- `bringup/diag/dev/<labelKey>/ageSec` (`double`)
- `bringup/diag/dev/<labelKey>/trafficAgeSec` (`double`)
- `bringup/diag/dev/<labelKey>/statusAgeSec` (`double`)
- `bringup/diag/dev/<labelKey>/msgCount` (`double`)
- `bringup/diag/dev/<labelKey>/lastSeen` (`double`)

### Console Monitor Keys
Purpose: Optional “console-like” counters published by rule sets.

- `bringup/diag/console/reset` (`bool`)
  - Meaning: When toggled true, the console monitor clears its counters.
- `bringup/diag/console/system/warnCount` (`double`)
- `bringup/diag/console/system/errorCount` (`double`)
- `bringup/diag/console/system/fatalCount` (`double`)
- `bringup/diag/console/devices/<labelKey>/warnCount` (`double`)
- `bringup/diag/console/devices/<labelKey>/errorCount` (`double`)
- `bringup/diag/console/devices/<labelKey>/fatalCount` (`double`)
- Additional keys may exist under `bringup/diag/console/...` depending on active rules.

## Robot -> Dashboards/Tools (`bringup/tests/...`)
Purpose: Publish tests overview for UI/dashboards.

Top-level:
- `bringup/tests/activeSet` (`string`)
- `bringup/tests/defaultSet` (`string`)
- `bringup/tests/usingTestSets` (`bool`)
- `bringup/tests/totalCount` (`double`)
- `bringup/tests/enabledCount` (`double`)
- `bringup/tests/selectedIndex` (`double`)
- `bringup/tests/selectedName` (`string`)
- `bringup/tests/activeName` (`string`)
- `bringup/tests/activeStatus` (`string`)
- `bringup/tests/runAllActive` (`bool`)

Rows:
- `bringup/tests/rows/<index>/index` (`double`)
- `bringup/tests/rows/<index>/name` (`string`)
- `bringup/tests/rows/<index>/enabled` (`bool`)
- `bringup/tests/rows/<index>/selected` (`bool`)
- `bringup/tests/rows/<index>/type` (`string`)
- `bringup/tests/rows/<index>/status` (`string`)
- `bringup/tests/rows/<index>/motors` (`string`) (comma-separated labels)

## Behavior When PC Tool Is Absent
Purpose: Define “fail soft” expectations.

- Robot-side reports show `PC: NOT CONNECTED` or `STALE`.
- Per-device PC presence fields are treated as unknown/unavailable.
- Robot bringup actions and tests still function using roboRIO-local APIs.

## Tradeoffs
- Using JSON strings (`.../json`) is easy for dashboards but less type-safe than structured topics.
- Label-based device keys are stable for humans but require consistent label discipline in config.

## Future Extensions
- Additive keys under `bringup/diag/can/...` for inventory diffs and byte fingerprints.
- Provide a generated “NT inventory” JSON artifact from both Java and Python builds.
