SPEC_STATUS: PARTIALLY_IMPLEMENTED

# Feature Spec: Passive CAN Discovery Library API

## Purpose

Define the public library API for the passive CAN discovery PoC as it is refactored from a tool-first implementation into a self-contained host-side library.

This spec is intentionally narrower than [FEATURE_SPEC_PASSIVE_CAN_DEVICE_DISCOVERY_POC.md](/c:/Users/dmona/swerve3/docs/FEATURE_SPEC_PASSIVE_CAN_DEVICE_DISCOVERY_POC.md). The PoC spec defines product behavior and milestones. This spec defines the library boundary, public entrypoints, object model, and integration contract.

## Status

`PARTIALLY_IMPLEMENTED`

## Goal

The passive discovery code should become a real library with one consistent public contract used by:

- the standalone PoC CLI
- future main-project integration code
- test code
- future UI or workflow consumers

The library should be usable without importing CLI internals or PoC-only helpers.

## Relationship to Existing PoC

This is a refactor of the existing code under:

- `tools/passive_discovery_poc/`

It is not a greenfield rewrite.

Existing working behavior should be preserved where practical:

- offline capture reading
- live source capture
- frame normalization
- family classification
- device inference
- optional CTRE enrichment
- optional profile comparison
- rendering helpers
- JSON serialization

What should change is the API shape and module boundary, not the fact that the current PoC already works.

## Design Direction

The passive discovery package should become:

- standalone-first
- library-first
- CLI-second
- explicit about public versus internal modules

The library must own its own canonical result model. It must not directly depend on main-project device object implementations inside the core public API.

Integration back into the main project should happen through explicit adapters.

## Hard Requirements

- The core library must remain read-only on CAN.
- The CLI must be a thin wrapper over the same public library API used by all other consumers.
- The public API must be modular and purpose-specific, not one multi-purpose catch-all call.
- Live observation must use explicit session lifecycle management.
- Result snapshots must be safe to share without hidden mutation.
- JSON serialization is part of the public contract.
- Rendering helpers are part of the public contract.
- Integration into existing device objects must use explicit adapter calls.
- Adapter behavior must require explicit context rather than guessing project defaults.

## Non-Goals

- backward compatibility with the current PoC module layout
- preserving accidental current imports from internal helper files
- a single universal `analyze(...)` entrypoint for all use cases
- hiding all distinctions between capture, discovery, enrichment, and adaptation

## Public Module Boundary

The package should be organized into explicit public modules.

Preferred public module set:

- `capture`
- `discovery`
- `enrichment`
- `profile`
- `adapters`
- `render`
- `json_api`
- `sources`

Preferred non-public module set:

- `internal`
- `internal.capture`
- `internal.rules`
- `internal.scoring`
- `internal.vendor`
- `internal.util`

Only the public modules should be imported by external callers.

## Source Plugin Model

The library should move toward a plugin-style source architecture.

The goal is:

- new sources can be added by implementing a required contract
- the rest of the library consumes normalized source output
- source-specific details stay isolated inside source plugins

This should apply to both built-in and future-added sources.

### Source Axes

The source model must represent two distinct axes:

1. what the source produces
- frame source
- enrichment source

2. how the source behaves
- live
- recorded

These axes must not be collapsed into one flat type.

### Source Classes

The library should recognize two top-level source classes:

- `FrameSourcePlugin`
- `EnrichmentSourcePlugin`

Frame sources produce normalized frame evidence.

Enrichment sources produce normalized enrichment or corroboration records.

### Source Modes

Each source must also declare its mode:

- `live`
- `recorded`

Examples:

- offline `pcapng`
  - recorded frame source
- live CANable/slcan
  - live frame source
- offline REV USB relay capture
  - recorded frame source
- live REV USB relay stream
  - live frame source
- CTRE HTTP snapshot
  - recorded enrichment source
- bringup profile
  - recorded enrichment source
- topology data
  - recorded enrichment source
- roboRIO console error string stream
  - live enrichment source

For console evidence specifically:

- saved roboRIO console log
  - recorded enrichment source
- live roboRIO console stream
  - live enrichment source

### Shared Base Contract

All source plugins should share common metadata contract fields such as:

- stable plugin id
- human-readable source name
- source class
- source mode
- supported configuration fields
- provenance/trust metadata

### Specialized Execution Contracts

The execution contract should then specialize by class and mode.

Recommended specialized source interfaces:

- `RecordedFrameSourcePlugin`
- `LiveFrameSourcePlugin`
- `RecordedEnrichmentSourcePlugin`
- `LiveEnrichmentSourcePlugin`

This allows:

- shared registration and metadata
- different runtime behavior where needed

without pretending all sources execute the same way.

### Output Contract

Frame source plugins must output:

- normalized frames
- source provenance

Enrichment source plugins must output:

- normalized enrichment records
- source provenance

Plugins must not emit arbitrary ad hoc structures into the shared pipeline.

### Console Enrichment Contract

Console CAN-device error messages should be modeled as enrichment plugins, not frame plugins.

Recommended plugin ids:

- `rio_console_log`
- `rio_console_stream`

Recommended plugin classes:

- `RecordedEnrichmentSourcePlugin`
- `LiveEnrichmentSourcePlugin`

The console plugins should preserve both:

- the raw message text
- the parsed or inferred device-related evidence when available

Console evidence is valuable for:

- missing expected device diagnosis
- communication failures reported by robot-owned code
- conflicts between passive CAN evidence and robot-side runtime evidence
- distinguishing expected-but-quiet from expected-but-erroring devices

Console evidence must not be treated as passive CAN proof by itself.

It should primarily influence:

- health
- notes
- evidence gaps
- confidence adjustments

and only carefully influence inventory or presence.

### Recommended Console Plugin Entry Points

Recommended public-facing plugin ids and meanings:

- `rio_console_log`
  - read a saved roboRIO console log artifact and emit normalized enrichment records
- `rio_console_stream`
  - attach to a live roboRIO console feed and emit normalized enrichment records over time

### Recommended EnrichmentRecord Shape For Console Evidence

The shared `EnrichmentRecord` type should be capable of carrying console evidence with at least the following normalized fields:

- `pluginId`
- `sourceClass`
- `sourceMode`
- `timestamp`
- `rawMessage`
- `severity`
- `category`
- `candidateDeviceIdentity`
- `candidateProfileNode`
- `candidateVendor`
- `candidateDeviceType`
- `candidateDeviceId`
- `candidateErrorCode`
- `parsedEvidenceType`
- `confidence`
- `provenance`

The exact object layout may evolve, but the above information should be representable without lossy string-only handling.

### Console Parsing Goals

The first useful console parser should recognize at least:

- CAN disconnected style messages
- device not found or missing device messages
- duplicate ID style messages if present
- timeout or communication failure messages
- vendor-specific device errors when the message text names vendor or model

When parsing succeeds, the plugin should emit evidence tied to:

- `(manufacturer, deviceType, deviceId)` when available
- otherwise a lower-confidence profile node or text-only candidate

When parsing does not succeed, the raw message should still be preserved as an enrichment record with low-confidence unresolved evidence.

### Registry

The library should expose a source registry so callers can:

- register built-in source plugins
- register future source plugins
- resolve sources by plugin id or source kind

The registry should be the standard path for source discovery and composition.

### Concrete Python Interface Sketch

The first implementation should use explicit Python protocol or abstract-base style interfaces close to the following shape.

#### Shared Base

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterator, Mapping, Protocol


@dataclass(frozen=True)
class SourcePluginInfo:
    plugin_id: str
    display_name: str
    source_class: str
    source_mode: str
    description: str
    config_schema: Mapping[str, Any]
    trust_notes: str


class SourcePluginBase(Protocol):
    def plugin_info(self) -> SourcePluginInfo:
        ...

    def validate_config(self, config: Mapping[str, Any]) -> None:
        ...
```

#### Live Frame Source

```python
class LiveFrameSession(Protocol):
    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def close(self) -> None:
        ...

    def frames(self) -> Iterator[NormalizedFrame]:
        ...


class LiveFrameSourcePlugin(SourcePluginBase, Protocol):
    def open_live_session(self, config: Mapping[str, Any]) -> LiveFrameSession:
        ...
```

#### Recorded Frame Source

```python
class RecordedFrameSourcePlugin(SourcePluginBase, Protocol):
    def read_frames(self, config: Mapping[str, Any]) -> Iterator[NormalizedFrame]:
        ...
```

#### Live Enrichment Source

```python
class LiveEnrichmentSession(Protocol):
    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def close(self) -> None:
        ...

    def records(self) -> Iterator[EnrichmentRecord]:
        ...


class LiveEnrichmentSourcePlugin(SourcePluginBase, Protocol):
    def open_live_session(self, config: Mapping[str, Any]) -> LiveEnrichmentSession:
        ...
```

#### Recorded Enrichment Source

```python
class RecordedEnrichmentSourcePlugin(SourcePluginBase, Protocol):
    def read_records(self, config: Mapping[str, Any]) -> Iterator[EnrichmentRecord]:
        ...
```

### Normalized Plugin Output Types

The plugin interfaces should target shared normalized output types rather than custom per-plugin structures.

Expected shared output types:

- `NormalizedFrame`
- `EnrichmentRecord`

The first implementation may evolve `EnrichmentRecord` details, but it should be a real shared type and not an unstructured `dict`.

### Live Frame Plugin Requirements

If a developer adds a new live frame source plugin, it must:

- implement `plugin_info()`
- implement `validate_config(...)`
- implement `open_live_session(...)`
- return a session with `start()`, `stop()`, `close()`, and `frames()`
- emit only shared `NormalizedFrame` objects
- preserve source provenance on emitted frames
- fail clearly on invalid config or runtime source failure
- release resources cleanly without leaking ports, threads, or handles

The plugin must not:

- classify devices
- assign confidence
- render output
- write JSON artifacts
- mutate unrelated shared state

## Public Entry Points

The public API should expose multiple well-defined entrypoints.

### Capture Module

Purpose: turn one capture source into normalized frame streams or live sessions.

Expected entrypoints:

- `read_pcapng(...)`
- `read_candump(...)`
- `observe_slcan_session(...)`
- `observe_rev_serial_session(...)`

These functions should not perform discovery by themselves unless a clearly named convenience wrapper is also provided elsewhere.

### Discovery Module

Purpose: analyze normalized frames into family evidence and device-level results.

Expected entrypoints:

- `analyze_frames(...)`
- `analyze_capture(...)`

`analyze_capture(...)` may be a convenience wrapper over capture plus discovery, but it must still remain explicit about the source type.

### Enrichment Module

Purpose: apply optional external evidence to an existing discovery result.

Expected entrypoints:

- `enrich_ctre(...)`

This enrichment should also be allowed as an explicit optional parameter to relevant analysis or session setup APIs.

### Profile Module

Purpose: compare discovery results to expected configuration data.

Expected entrypoints:

- `compare_profile(...)`

This comparison should also be allowed as an explicit optional parameter to relevant analysis or session setup APIs.

### Adapters Module

Purpose: bridge the library’s canonical model into existing main-project device objects.

Expected entrypoints:

- `update_or_create_device(...)`
- `apply_discovery_to_devices(...)`

Both single-device and batch forms are required.

### Render Module

Purpose: produce human-readable output from public snapshot/result objects.

Expected entrypoints:

- `render_summary_table(...)`
- `render_full_dump(...)`

Rendering must consume the same public result objects available to non-CLI callers.

### JSON Module

Purpose: serialize and restore the public result model.

Expected entrypoints:

- `result_to_json_dict(...)`
- `result_from_json_dict(...)`

File-writing convenience helpers are allowed, but the stable contract is the JSON-compatible object shape, not the file path behavior.

## Result Model

The library should own a canonical internal result model that is also the public API model.

This model should be distinct from the current main-project device object model.

### Public Result Principles

- snapshots/results should be immutable
- live session objects may be mutable
- evidence and provenance are first-class
- summary state should not duplicate existing project device semantics more than necessary

The library’s main distinct value should be:

- evidence-backed updates
- confidence values
- provenance
- unknown traffic
- optional enrichment metadata

## Confidence Contract

The public device/result model must expose confidence in two parallel forms:

- semantic confidence buckets
- numeric normalized scores

This applies equally to:

- newly discovered devices
- expected or existing devices from profile or integration context

Recommended fields:

- `presenceConfidence`: `none | uncertain | low | medium | high`
- `presenceScore`: `0..100`
- `inventoryConfidence`: `none | uncertain | low | medium | high`
- `inventoryScore`: `0..100`
- `healthConfidence`: `none | uncertain | low | medium | high`
- `healthScore`: `0..100`

The semantic bucket is the stable operator and logic-facing interpretation.

The numeric score is intended for:

- UI gradients
- sorting
- thresholding
- compact machine comparison

Status-style fields such as expected, missing, observed, or unexpected should remain separate from confidence fields.

## Live Observation Model

Live observation should use a session or collector object as the primary public API.

Recommended shape:

- `session.start()`
- `session.stop()`
- `session.close()`
- `session.snapshot()`
- `session.subscribe(...)`

The session should support both:

- periodic full snapshots
- event or callback hooks

Suggested callback/event categories:

- `on_frame`
- `on_snapshot`
- `on_warning`

The exact callback naming may change during implementation, but the library must support both snapshot polling and callback-driven live consumption.

## Immutability and Lifecycle

Public rule:

- live session or collector objects are mutable and explicitly owned
- result and snapshot objects are immutable

Live sessions must provide explicit stop or close lifecycle management.

The library should not hide long-lived background ownership in ordinary result objects.

## Summary State vs Evidence State

The library may expose summary device state, but it should avoid becoming a second competing full device-state system.

If an existing project device object already owns fields such as:

- presence
- health
- faults
- attachments

then the passive discovery library should focus on exposing:

- updates or overlays
- supporting evidence
- confidence
- provenance
- unknown or unresolved traffic

## Adapter Contract

The adapter layer should be explicit and integration-facing.

### Adapter Rules

- adapters must accept explicit context/configuration
- adapters may create a new existing-project device object when needed
- adapters may update an existing existing-project device object when present
- batch adaptation must be supported
- adapter output must make evidence provenance visible to the caller

The adapter layer should not rely on hidden global state or automatic project inference.

## JSON Contract

JSON serialization is a first-class public API concern.

At minimum, the canonical result JSON must preserve:

- run/source metadata
- device identities
- summary classifications
- evidence references
- confidence values
- unknown traffic
- enrichment data
- profile comparison results when present

This spec does not yet require separate JSON contracts for event streams versus snapshots. That may be decided during implementation. Full snapshot JSON is acceptable as the initial live JSON contract.

## CLI Contract

The CLI must use only the public library API.

The CLI must not:

- reach into internal helper modules
- implement parallel logic not present in the public API
- invent result shapes not available from the public library model

The CLI may still provide argument parsing, file path defaults, and operator-friendly printing.

## Migration Plan

The refactor should happen in place in `tools/passive_discovery_poc/`.

Recommended phases:

1. introduce explicit public modules and move current implementation behind them
2. create internal modules for heuristics and source-specific helpers
3. switch CLI to use only public entrypoints
4. add adapter layer for existing project device objects
5. add tests that enforce public API usage and JSON contract behavior

## Testing Requirements

The refactor must add tests for:

- public offline capture entrypoints
- public live session entrypoints
- public discovery entrypoints
- explicit enrichment as a separate step
- explicit enrichment as an optional parameter
- explicit profile comparison as a separate step
- explicit profile comparison as an optional parameter
- rendering helpers using public result types
- JSON round-trip using public result types
- adapter single-device update/create behavior
- adapter batch behavior
- CLI using only public entrypoints

## Definition of Done

This refactor is done when:

- the current PoC behavior still works through the new public API
- the CLI is only a thin wrapper over public library entrypoints
- the package has a documented public versus internal split
- existing working offline and live PoC features remain available
- explicit adapters can update or create existing project device objects
- public rendering helpers consume public result objects
- JSON serialization and restoration work from the public model
- tests enforce the public API shape rather than current incidental module structure
