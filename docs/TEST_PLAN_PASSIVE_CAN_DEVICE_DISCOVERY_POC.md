# Test Plan: Passive CAN Device Discovery PoC

## Purpose

Define the complete validation plan for the Passive CAN Device Discovery PoC.

This plan is intended to prove three things:

- the PoC produces a reliable passive device inventory
- the PoC produces useful health/confidence output with explicit gaps
- the PoC preserves and exposes reverse-engineering evidence that is useful for further CAN analysis

## Related Docs

- [FEATURE_SPEC_PASSIVE_CAN_DEVICE_DISCOVERY.md](/c:/Users/dmona/swerve3/docs/FEATURE_SPEC_PASSIVE_CAN_DEVICE_DISCOVERY.md)
- [FEATURE_SPEC_PASSIVE_CAN_DEVICE_DISCOVERY_POC.md](/c:/Users/dmona/swerve3/docs/FEATURE_SPEC_PASSIVE_CAN_DEVICE_DISCOVERY_POC.md)
- [2026-07-08_rev_passive_can_findings.md](/c:/Users/dmona/swerve3/notes/research/vendor_diagnostics/2026-07-08_rev_passive_can_findings.md)
- [2026-07-08_ctre_diagnostic_server_endpoint_matrix.md](/c:/Users/dmona/swerve3/notes/research/vendor_diagnostics/2026-07-08_ctre_diagnostic_server_endpoint_matrix.md)

## Scope

This plan covers:

- offline `pcapng` analysis
- offline candump/text analysis
- profile-comparison behavior
- optional CTRE HTTP enrichment behavior
- canonical JSON artifact validation
- minimal terminal output validation
- live-source validation once implemented
- failure and degradation behavior

This plan does not cover:

- dashboard presentation quality
- NetworkTables behavior
- Java-side consumption
- final production integration into the main CLI/UI
- automated fault localization from topology

## Success Criteria

The PoC succeeds only if all three are true:

1. device inventory is reliable enough to trust for further work
2. health assessment is useful and honest about evidence gaps
3. reverse-engineering evidence is rich enough to guide the next round of analysis

## Validation Strategy

Run validation in five stages:

1. Offline parser and fixture sanity
2. Offline semantic analysis
3. Enrichment and profile comparison
4. Live-source validation
5. Regression bundle and artifact review

This order is intentional:

- fail fast on ingestion bugs
- verify semantic correctness before adding live acquisition complexity
- validate optional enrichments only after the passive core is stable
- use live runs only after offline behavior is trustworthy

## Preconditions

- Windows host with Python on `PATH`
- working directory at repo root
- current PoC code present in workspace
- required fixture captures present under `tools/vendor_diag/`
- `src/main/deploy/bringup_system.json` present

For CTRE enrichment checks:

- roboRIO reachable at `172.22.11.2`
- CTRE diagnostic server reachable on port `1250`

For live CAN checks:

- CANable/slcan hardware available
- correct COM port known or discoverable
- robot CAN bus powered and stable

## Required Fixture Set

Initial required fixture set:

- `tools/vendor_diag/usbCap2_can.pcapng`
- `tools/vendor_diag/usbCap3_can.pcapng`
- `tools/vendor_diag/usbCap4_can.pcapng`
- `tools/vendor_diag/usbCap8_can.pcapng`
- `tools/vendor_diag/usbCap5_socketcan.pcapng`
- `tools/vendor_diag/usbCap6_socketcan.pcapng`
- `tools/vendor_diag/usbCap7_socketcan.pcapng`
- `tools/vendor_diag/usbCap8_socketcan.pcapng`

Minimum profile comparison fixture:

- `src/main/deploy/bringup_system.json`
- profile `test_minimal_25_9`

The fixture set should remain extensible.

## Stage 1: Offline Parser and Fixture Sanity

## Purpose

Prove that the PoC can ingest the supported offline formats and normalize frames correctly.

### 1.1 SocketCAN `pcapng` Reader

Command:

```text
python -m unittest tools.passive_discovery_poc.tests.test_readers
```

Expected:

- tests pass
- SocketCAN fixture yields many frames
- both REV and CTRE frames appear when expected

### 1.2 Candump/Text Reader

Command:

```text
python -m unittest tools.passive_discovery_poc.tests.test_readers
```

Expected:

- sample candump line parses
- FRC extended-ID fields decode correctly
- payload bytes are preserved exactly

### 1.3 Unknown Traffic Preservation

Manual check:

- feed one input containing malformed or non-FRC-decodable traffic

Expected:

- run does not silently drop the traffic
- unknown/raw traffic appears in JSON output

## Stage 2: Offline Semantic Analysis

## Purpose

Prove that family classification and device inference behave correctly on known captures.

### 2.1 Baseline Semantic Tests

Command:

```text
python -m unittest tools.passive_discovery_poc.tests.test_analysis
```

Expected:

- tests pass
- known devices in `usbCap8_socketcan` are surfaced
- expected and unexpected status handling works
- canonical JSON shape remains stable enough for code consumption

### 2.2 `usbCap8_socketcan` End-to-End

Command:

```text
python tools/passive_discovery_poc/passive_discovery.py ^
  --input tools/vendor_diag/usbCap8_socketcan.pcapng ^
  --profile-path src/main/deploy/bringup_system.json ^
  --profile-name test_minimal_25_9
```

Expected:

- one canonical JSON artifact is written
- default terminal output includes device rows and supporting evidence families
- `SPARKMAX/NEO 25` appears as expected/observed
- REV device `7` appears as unexpected/observed
- `FALCON 9` appears as observed
- `roborio` appears as missing under the test profile

### 2.3 Command-Family Exclusion

Purpose: confirm known REV command families do not count as passive presence evidence.

Relevant captures:

- `usbCap2_can.pcapng`
- `usbCap3_can.pcapng`
- `usbCap4_can.pcapng`

Commands:

```text
python tools/passive_discovery_poc/passive_discovery.py ^
  --input tools/vendor_diag/usbCap2_can.pcapng ^
  --full-dump

python tools/passive_discovery_poc/passive_discovery.py ^
  --input tools/vendor_diag/usbCap3_can.pcapng ^
  --full-dump

python tools/passive_discovery_poc/passive_discovery.py ^
  --input tools/vendor_diag/usbCap4_can.pcapng ^
  --full-dump
```

Expected:

- command families such as REV `api_class=0`, `api_index=2/5/6` are present in family output
- those families are not the reason a device is marked present
- for device `25`, the command family should appear as `CONTROLLER_EMITTED_COMMAND`
- recurring `b8xx/b84x/bc0x`-style families should still be the evidence used for presence/health

### 2.4 Shared-Bus Exclusion

Purpose: confirm shared REV bus-control families are not used as presence proof.

Relevant capture:

- `usbCap8_socketcan.pcapng`

Command:

```text
python tools/passive_discovery_poc/passive_discovery.py ^
  --input tools/vendor_diag/usbCap8_socketcan.pcapng ^
  --profile-path src/main/deploy/bringup_system.json ^
  --profile-name test_minimal_25_9 ^
  --full-dump
```

Expected:

- `deviceId=0` or broadcast-style families appear in family output
- they are classified as shared or uncertain
- they do not raise presence confidence for a specific device
- specifically, shared families such as the REV `deviceId=0` traffic should not be the evidence used for Spark `7` or Spark `25`

### 2.5 Reverse-Engineering Evidence Depth

Run with full dump:

```text
python tools/passive_discovery_poc/passive_discovery.py ^
  --input tools/vendor_diag/usbCap8_socketcan.pcapng ^
  --profile-path src/main/deploy/bringup_system.json ^
  --profile-name test_minimal_25_9 ^
  --full-dump
```

Expected:

- family inventory is visible
- role classification is visible
- cadence and counts are visible
- evidence is useful enough to continue manual reverse engineering

## Stage 3: Profile Comparison and CTRE Enrichment

## Purpose

Validate optional multi-source behavior and conflict handling.

### 3.1 Profile Comparison

Command:

```text
python tools/passive_discovery_poc/passive_discovery.py ^
  --input tools/vendor_diag/usbCap8_socketcan.pcapng ^
  --profile-path src/main/deploy/bringup_system.json ^
  --profile-name test_minimal_25_9
```

Expected:

- expected devices missing from the passive evidence are shown by default
- unexpected observed devices are shown by default
- profile-backed labels are used where available

### 3.2 CTRE Enrichment Happy Path

Command:

```text
python tools/passive_discovery_poc/passive_discovery.py ^
  --input tools/vendor_diag/usbCap8_socketcan.pcapng ^
  --profile-path src/main/deploy/bringup_system.json ^
  --profile-name test_minimal_25_9 ^
  --ctre-base-url http://172.22.11.2:1250
```

Expected:

- run succeeds
- CTRE devices receive enrichment where supported
- CTRE fault/sticky-fault information is preserved in JSON when available
- CTRE evidence source is listed for enriched devices

### 3.3 CTRE-Only Discovery Mode

Purpose: prove the PoC can still produce useful output when only CTRE HTTP is available.

Command:

```text
python tools/passive_discovery_poc/passive_discovery.py ^
  --ctre-base-url http://172.22.11.2:1250
```

Expected:

- run succeeds
- CTRE inventory is surfaced
- output is clearly weaker on passive evidence

### 3.4 CTRE Degradation Path

Purpose: prove CTRE HTTP failure degrades to passive-only rather than killing a passive run.

Command:

```text
python tools/passive_discovery_poc/passive_discovery.py ^
  --input tools/vendor_diag/usbCap8_socketcan.pcapng ^
  --profile-path src/main/deploy/bringup_system.json ^
  --profile-name test_minimal_25_9 ^
  --ctre-base-url http://172.22.11.2:9999
```

Expected:

- run still succeeds
- warning is emitted
- passive results still appear

### 3.5 Profile Failure Path

Purpose: prove malformed or missing profile input is fatal when requested.

Command example:

```text
python tools/passive_discovery_poc/passive_discovery.py ^
  --input tools/vendor_diag/usbCap8_socketcan.pcapng ^
  --profile-path does_not_exist.json
```

Expected:

- run fails hard
- failure is explicit

## Stage 4: Live-Source Validation

## Purpose

Validate the live modes required by the PoC spec once those modes are implemented.

### 4.1 Live CANable/slcan

Command:

```text
python tools/passive_discovery_poc/passive_discovery.py ^
  --live-slcan ^
  --channel COM3 ^
  --duration 5.0
```

Alternative when auto-detecting CANable by description:

```text
python tools/passive_discovery_poc/passive_discovery.py ^
  --live-slcan ^
  --auto-match CANable ^
  --duration 5.0
```

Workflow:

- connect CANable to the robot CAN bus
- run live passive observation
- compare live inventory against known physical devices and offline captures

Expected:

- live frames ingest correctly
- no CAN transmission occurs
- device inventory is plausible

### 4.2 Live REV USB Bridge

Command:

```text
python tools/passive_discovery_poc/passive_discovery.py ^
  --live-rev-serial COM7 ^
  --rev-baud 115200 ^
  --duration 5.0
```

Workflow:

- connect to the REV USB gateway path
- observe live bus activity through the bridge path

Expected:

- live ingestion works
- recurring per-device families match offline observations
- output remains read-only from the PoC side

### 4.3 Live CTRE Enrichment

Command:

```text
python tools/passive_discovery_poc/passive_discovery.py ^
  --live-slcan ^
  --channel COM3 ^
  --duration 5.0 ^
  --ctre-base-url http://172.22.11.2:1250
```

Alternative with live REV serial passive source:

```text
python tools/passive_discovery_poc/passive_discovery.py ^
  --live-rev-serial COM7 ^
  --rev-baud 115200 ^
  --duration 5.0 ^
  --ctre-base-url http://172.22.11.2:1250
```

Workflow:

- run live passive observation with CTRE HTTP enabled against the roboRIO

Expected:

- passive device identities align with CTRE HTTP data
- disagreements are surfaced, not hidden
- CTRE enrichment warnings are visible in normal CLI output when the CTRE endpoint is unavailable

## Stage 5: Artifact and Contract Review

## Purpose

Validate that the JSON output and terminal verification surface are usable for both humans and future code.

### 5.1 Canonical JSON Review

Check:

- one artifact per run by default
- top-level run metadata present
- device rows include confidence and evidence-source fields
- family rows include metrics and role
- unknown traffic is preserved

Expected:

- downstream code can reasonably consume the result without scraping terminal text

### 5.2 Minimal Human Verification Output

Check:

- default terminal output is short
- device rows are readable
- evidence families are visible without full dump

Expected:

- enough information is present to quickly decide whether a run looks sane

## Required Automated Checks

At minimum, automated tests must continue to cover:

- `pcapng` reader
- candump reader
- semantic detection on known fixtures
- command-family exclusion from presence
- shared-bus exclusion from presence
- unknown traffic preservation
- expected/missing/unexpected handling
- canonical JSON contract shape

## Pass Criteria

The PoC passes this plan when:

- all current automated tests pass
- `usbCap8_socketcan` end-to-end results are sane
- profile comparison works
- CTRE enrichment works and degrades correctly
- JSON output is stable enough for code consumption
- reverse-engineering evidence is visibly useful
- all later live checks pass once those modes are implemented

## Failure Conditions

Any of these should block calling the PoC successful:

- shared or command traffic is used as passive presence proof
- expected devices are silently omitted rather than marked missing
- unexpected devices are silently dropped
- unknown traffic disappears from output
- CTRE failure kills a passive run unexpectedly
- profile failure silently degrades instead of failing hard
- JSON output lacks enough structure for later integration

## Recommended Execution Order

For day-to-day validation:

1. run the automated unit tests
2. run one `usbCap8_socketcan` end-to-end check
3. run one CTRE-enriched check
4. inspect the JSON artifact when schema-affecting code changed

For milestone validation:

1. complete all offline fixture checks
2. complete all enrichment checks
3. complete all live-source checks
4. archive representative outputs for regression comparison
