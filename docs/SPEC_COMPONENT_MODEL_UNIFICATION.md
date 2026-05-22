SPEC_STATUS: PARTIALLY_IMPLEMENTED

# Component Model Unification

## Purpose

Define a single canonical config model and a mandatory shared interpreter layer so all consumers of bringup configuration data derive the same meaning from the same file.

## Status

Proposed implementation refactor and schema direction.

No backward compatibility is required.

Old config shapes may be converted or regenerated.

## Problem

The current system has multiple consumers of the same underlying config data:

- topology editor
- live topology view
- CLI
- shared Python services
- Java runtime consumers

Those consumers do not share a deep enough normalization and interpretation layer.

As a result, they can silently disagree about:

- what is a device
- what is infrastructure
- which objects belong in runtime inventory
- how topology nodes map to real components
- what tests are allowed to reference
- which relationships are structural versus runtime-relevant

This divergence is a major bug source and a major architectural risk as the system grows.

## Goal

Create one canonical component model and one shared interpretation model so all consumers use the same semantics for the same persisted data.

The desired outcome is:

- one canonical persisted config structure
- one canonical component classification model
- one canonical topology model
- one shared interpretation layer per language
- no local ad hoc parsing of core config semantics

## Non-Goals

- preserve legacy config compatibility
- minimize short-term code churn at the expense of architecture
- create a global cross-language shared codebase
- redesign unrelated runtime behavior beyond what is required to align the model

## Design Principles

- canonical persisted data must have one meaning
- profile ownership must be explicit
- labels remain the identity of components
- component semantics must not be re-derived differently by each consumer
- topology is the only persisted topology model
- shared interpreter use is mandatory
- duplicate interpretation logic is a bug

## Canonical File Model

### One File, Optional Multiple Profiles

The system continues to support:

- one config file containing multiple profiles
- separate config files when users prefer stronger isolation

The current default filename may remain supported.

Filename choice is user-controlled.

### Ownership Rule

A config file is a container of profiles.

Each profile owns its own:

- components
- topology

Tests remain file-level and are keyed by profile name.

`bridgeConfig` remains separate operator metadata and is not part of the core component/topology/test model.

## Canonical Root Structure

The canonical file structure is:

```json
{
  "schemaVersion": 1,
  "dataVersion": "...",
  "dataHash": "...",
  "defaultProfile": "profileName",
  "profiles": {
    "profileName": {
      "components": [],
      "topology": {}
    }
  },
  "testsByProfile": {
    "profileName": {
      "defaultSet": "default",
      "testSets": {},
      "testsByName": {}
    }
  },
  "bridgeConfig": {}
}
```

Field names may continue to use repo naming conventions, but the structure above is the required semantic model.

## Component Model

### Purpose

Provide one system-wide classification model for all real and structural components.

### Canonical Rule

Every component is either:

- `device`
- `infrastructure`

No third component class exists in the core model.

### Device

A runtime-addressable component.

Examples:

- motors
- encoders
- limit switches
- controllers
- PDH/PDP
- roboRIO
- pigeon
- CANdle

Device characteristics:

- may be instantiated by runtime
- may expose signals
- may be referenced by tests
- may appear in runtime inventory

### Infrastructure

A non-runtime structural component.

Examples:

- CANnect Direct
- CANnect Inject
- analyzer nodes
- passive junctions
- bus structure helpers
- structural power distribution helpers

Infrastructure characteristics:

- not instantiated by runtime
- not part of runtime device inventory
- not promoted into runtime device registries
- may appear in topology
- may be referenced by tests only if a concrete future use case requires it

## Canonical Component Record

### Purpose

Provide one common schema for both device and infrastructure components.

### Shape

Each component record includes:

- `label`
- `componentType`
- `subtype`
- `interface`
- `capabilities`
- `meta`

Canonical example:

```json
{
  "label": "frontLeft Drive Motor",
  "componentType": "device",
  "subtype": "motor",
  "interface": {
    "kind": "CAN",
    "id": 2
  },
  "capabilities": {
    "signals": ["output", "velocity", "current", "temperature"]
  },
  "meta": {
    "vendor": "CTRE",
    "model": "krakenx60"
  }
}
```

Infrastructure example:

```json
{
  "label": "cannect 2",
  "componentType": "infrastructure",
  "subtype": "cannect_direct",
  "interface": {
    "kind": "structural"
  },
  "capabilities": {
    "powerSource": true,
    "canPorts": 3
  },
  "meta": {
    "vendor": "SWYFT"
  }
}
```

### Field Rules

#### `label`

- required
- unique within a profile
- primary identity used by tests and topology

#### `componentType`

- required
- one of:
  - `device`
  - `infrastructure`

#### `subtype`

- required
- applies to both component classes
- examples:
  - `motor`
  - `encoder`
  - `limit_switch`
  - `controller_xbox`
  - `pdh`
  - `roborio`
  - `cannect_direct`
  - `cannect_inject`
  - `analyzer`

#### `interface`

- required
- structured object
- may describe:
  - CAN
  - DIO
  - USB
  - internal/runtime
  - structural/no-runtime interface

#### `capabilities`

- optional but standard field
- structured object
- used for normalized capability declarations
- should not be inferred differently by each consumer

#### `meta`

- optional but standard field
- structured object
- for descriptive, rendering, and non-core vendor/model data

## Topology Model

### Purpose

Persist one canonical topology representation for all views and tools.

### Rule

`topology` is the only persisted topology model.

No persisted parallel `diagram` model exists in the target architecture.

All editor, live, CLI, and diagnostic views are derived from canonical topology through shared code.

## Canonical Topology Node Model

### Purpose

Represent both devices and infrastructure using one node envelope.

### Rule

Each topology node is made of exactly two parts:

1. common part
2. type-specific part

No duplicated data may exist between the common part and the typed part.

### Shape

```json
{
  "common": {
    "key": 19,
    "nodeType": "infrastructure",
    "label": "cannect 2",
    "layout": {
      "bus": 0,
      "row": 0,
      "x": 384.0,
      "y": 1019.0
    }
  },
  "infrastructure": {
    "subtype": "cannect_direct",
    "meta": {}
  }
}
```

Device example:

```json
{
  "common": {
    "key": 3,
    "nodeType": "device",
    "label": "frontLeft Encoder",
    "layout": {
      "bus": 0,
      "row": 1,
      "x": 855.0,
      "y": 542.25
    }
  },
  "device": {
    "deviceRef": "frontLeft Encoder"
  }
}
```

### Common Part

Required fields:

- `key`
- `nodeType`
- `label`
- `layout`

#### `nodeType`

Allowed values:

- `device`
- `infrastructure`

No other top-level node kinds are allowed in the canonical model.

Subtyping belongs in the typed payload, not in `nodeType`.

### Device Part

Required field:

- `deviceRef`

Rules:

- references a profile-local component label
- referenced component must have `componentType: device`
- topology must not duplicate device classification data

### Infrastructure Part

Required field:

- `subtype`

Optional field:

- `meta`

Rules:

- subtype is mandatory
- infrastructure-specific rendering or structural metadata belongs here

### Layout

Layout remains embedded in the common node part.

Required/optional fields:

- `bus`
- `row`
- `x`
- optional `y`

## Canonical Edge Model

### Purpose

Represent all structural relationships with one generic edge shape.

### Shape

Edges remain generic:

- `fromNode`
- `fromPort`
- `toNode`
- `toPort`
- `edgeType`

This applies equally to:

- device-device relationships
- infrastructure-infrastructure relationships
- device-infrastructure relationships

## Tests Model

### Purpose

Keep tests distinct from components while aligning test references to the same shared component interpretation model.

### Rule

Tests are not devices and are not infrastructure.

Tests are workflows that reference components by label.

### Ownership

Tests remain file-level and are keyed by profile name.

### Reference Semantics

Tests reference components by label.

The shared interpreter must resolve those labels through the canonical component model.

Current expected behavior:

- device references are first-class
- infrastructure references are schema-allowed but should only be runtime-supported when an explicit use case exists

## `bridgeConfig`

### Purpose

Hold operator and workflow metadata.

Examples:

- groups
- selected device
- local bindings
- operator-focused organization state

### Rule

`bridgeConfig` is separate from the canonical component/topology/test model.

It must not own core component semantics.

It must not be used as an alternate source of truth for component classification or topology meaning.

## Shared Interpreter Rule

### Hard Rule

All consumers of canonical config semantics must go through shared interpreter code.

Local duplicate parsing of the same core semantics is a bug.

### Python

Python shared/common code must own:

- config loading
- profile selection
- component classification
- device vs infrastructure interpretation
- topology node resolution
- topology edge resolution
- test-reference resolution
- derived compatibility/read models for UI/CLI/editor/live surfaces

Consumers that must use shared interpreters:

- topology editor
- live topology view
- CLI
- shared Python workflow/services

### Java

Java will not share Python implementation code.

Java must implement a matching interpreter layer for the same canonical model.

Java must share:

- schema contract
- derivation contract
- fixtures/expected behavior

with the Python side.

### Cross-Language Rule

Python and Java may have separate code, but they must not have different interpretations of the canonical model.

## Derived Views

### Rule

Any non-persisted view must be derived through shared/common code.

Examples:

- editor node list
- live topology node list
- CLI topology display payloads
- runtime topology report objects
- test-resolved component sets

No consumer may reconstruct these views from raw config independently.

## Migration Direction

### Required Changes

1. Remove persisted parallel topology models.
2. Convert topology consumers to canonical `topology` only.
3. Replace separate device-only and diagram-only assumptions with the unified component model.
4. Eliminate local parsers that duplicate shared interpretation logic.
5. Move all component classification into shared interpreters.
6. Move all topology node/edge derivation into shared interpreters.
7. Move test component resolution into shared interpreters.

### Backward Compatibility

Not required.

Old config may be converted or regenerated.

## Failure Modes

### Invalid Component Classification

If a referenced label does not resolve to a known component in the active profile:

- validation must fail
- runtime must not guess

### Invalid Topology Node Reference

If a topology device node references a non-device component:

- validation must fail

If an infrastructure node is missing subtype:

- validation must fail

### Divergent Consumer Logic

If a consumer attempts to interpret canonical model fields outside the shared interpreter:

- that is an architectural bug
- refactor to shared/common code is required

## Observability

The shared interpreter layer should expose:

- resolved profile summary
- resolved component list
- resolved topology node list
- resolved topology edge list
- resolved test component references

This should support both:

- automated validation
- debugging/reporting surfaces

## Test Strategy

### Required

- shared-parser unit tests
- profile fixture round-trip tests
- topology fixture interpretation tests
- test-reference resolution tests
- editor/live/CLI consumer tests against shared fixtures

### Cross-Consumer Requirement

For a given fixture, the following must agree:

- shared parser output
- editor interpretation
- live view interpretation
- CLI interpretation

When Java consumes the same fixture, Java interpretation must match the documented expected result.

## Rollout Strategy

### Recommended Sequence

1. Land this spec.
2. Create canonical shared interpreters for:
   - profile
   - components
   - topology
   - tests
3. Convert Python consumers to those interpreters.
4. Remove duplicated local parsing paths.
5. Update Java consumers to the same contract.
6. Convert or regenerate config fixtures.

## Tradeoffs

### Benefits

- one meaning for one piece of data
- lower bug rate from drift
- easier reasoning about ownership
- easier future feature work
- cleaner device vs infrastructure handling

### Costs

- more up-front refactor work
- some current code paths will be deleted or reshaped
- config conversion/regeneration work is required
- Java and Python must both be kept aligned deliberately

## Definition of Done

This refactor/feature is done when:

- canonical config structure is implemented
- component classification is unified
- topology is the only persisted topology model
- tests resolve components through shared interpreters
- Python consumers no longer locally reinterpret core config semantics
- Java has a matching canonical interpretation contract
- representative fixtures produce the same interpretation across all consumers
- old compatibility parsing paths for replaced models are removed

