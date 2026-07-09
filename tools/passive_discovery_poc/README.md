# Passive Discovery PoC

## Purpose

Purpose: provide a standalone-first proof of concept for passive CAN device discovery, health inference, and reverse-engineering evidence extraction.

## Status

Experimental.

## Public API

The current library-shaped public modules are:

- `capture`
- `discovery`
- `enrichment`
- `profile`
- `adapters`
- `render`
- `json_api`

The CLI is intended to be a thin wrapper over those public entrypoints.

## Current Inputs

- offline SocketCAN-style `pcapng`
- offline candump/text logs
- live CANable/slcan capture
- live REV serial bridge capture
- optional CTRE diagnostic HTTP enrichment
- optional bringup profile comparison via `bringup_system.json`

## Current Output

One canonical JSON artifact per run plus a compact terminal device/evidence table.

The public result model now exposes both:

- semantic confidence buckets such as `high` and `uncertain`
- numeric scores such as `presence_score`, `inventory_score`, and `health_score`

## Library Examples

Offline analysis:

```python
from tools.passive_discovery_poc.capture import load_expected_rows
from tools.passive_discovery_poc.discovery import analyze_capture
from tools.passive_discovery_poc.render import render_summary_table

_, expected_rows = load_expected_rows(
    profile_path="src/main/deploy/bringup_system.json",
    profile_name="test_minimal_25_9",
)
result = analyze_capture(
    "tools/vendor_diag/usbCap8_socketcan.pcapng",
    expected_rows=expected_rows,
)
print(render_summary_table(result))
```

Live session:

```python
from tools.passive_discovery_poc.capture import observe_slcan_session

session = observe_slcan_session(channel="COM3", duration_sec=5.0)
session.start()
session.wait(timeout=7.0)
result = session.snapshot()
session.close()
```

Adapter usage:

```python
from tools.passive_discovery_poc.adapters import apply_discovery_to_devices
from tools.passive_discovery_poc.models import AdapterContext

updated_devices = apply_discovery_to_devices(
    existing_devices={},
    result=result,
    context=AdapterContext(),
)
```

## Example

```text
python tools/passive_discovery_poc/passive_discovery.py ^
  --input tools/vendor_diag/usbCap8_socketcan.pcapng ^
  --profile-path src/main/deploy/bringup_system.json ^
  --profile-name test_minimal_25_9 ^
  --full-dump
```

Live CANable/slcan example:

```text
python tools/passive_discovery_poc/passive_discovery.py ^
  --live-slcan ^
  --channel COM3 ^
  --duration 5.0
```

Live REV serial bridge example:

```text
python tools/passive_discovery_poc/passive_discovery.py ^
  --live-rev-serial COM7 ^
  --rev-baud 115200 ^
  --duration 5.0
```

Live slcan plus CTRE enrichment example:

```text
python tools/passive_discovery_poc/passive_discovery.py ^
  --live-slcan ^
  --channel COM3 ^
  --duration 5.0 ^
  --ctre-base-url http://172.22.11.2:1250
```

## Current Limitations

- the PCAPNG reader is intentionally narrow and targets SocketCAN captures already produced by repo tooling
- family decoding is heuristic-first and incomplete
- CTRE enrichment is currently limited to inventory plus decorated-self-test fault extraction
- live-source validation still depends on real hardware availability

## Integration Direction

The PoC is intentionally separate, but its core modules are structured so they can later move into shared host-side Python code while leaving the standalone CLI as a thin wrapper.
