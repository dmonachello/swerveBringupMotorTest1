# Feature Spec: Topology Upgrade (Branch Target)

## 1. Purpose

Purpose: define the target topology model for the `topology_upgrade`
branch.

This spec replaces the weaker "diagram metadata plus neighbor tables"
approach with a topology system that is treated as first-class shared system
data.

The target model must support:

- common FRC serial CAN layouts
- Swyft / CANnect / junction-based branch layouts
- analyzer placement
- non-CAN links such as DIO, PWM, analog, and power
- CLI inspection
- topology editor authoring
- GUI/live-topology filtering
- future topology-assisted diagnostics

This spec is intended as a target implementation contract, not a low-risk
compatibility patch.

## 2. Status

Branch target for `topology_upgrade`.

This branch is allowed to make broad topology-model changes in order to reach
a coherent final design.

## 3. Problem

The current topology shape is useful but too weak as long-term semantic truth.

Current limitations:

- topology is still framed partly as editor/diagram metadata
- adjacency is stored primarily as `neighborLinks` / `neighborPorts`
- branching semantics are not first-class
- analyzer locations are not first-class topology entities
- non-CAN connections are not modeled as part of the same general graph
- topology filtering is not a first-class concept in editor and GUI surfaces

Result:

- the common serial case works
- advanced layouts are awkward
- diagnostic expansion is constrained by the stored model

## 4. Design Principles

- Graph truth: topology is a graph, not a left/right list.
- Serial-first UX: the most common FRC serial CAN case must remain easy to
  author.
- Typed connections: every connection type must have explicit semantics.
- Mixed-network support: CAN and non-CAN links belong in the same topology
  system.
- View filtering: users must be able to focus on selected connection types.
- Derived neighbors: neighbor views are derived from graph truth.
- Diagnostic growth: the model must support analyzer nodes, inferred edges,
  and later fault-localization overlays.

## 5. Scope

### In scope

- canonical topology graph model
- persisted JSON contract for topology
- node and edge typing
- serial-first authoring rules
- junction and analyzer support
- non-CAN link modeling
- topology validation rules
- topology filtering model for editor and GUI
- CLI topology inspection behavior
- migration from current topology fields
- regression requirements

### Out of scope

- final fault-localization scoring logic
- full automatic topology discovery from CAN traffic
- motion automation
- visual pixel-diff testing

## 6. Core Model

Topology is a first-class graph.

The graph contains:

- nodes
- edges
- ports
- layout metadata
- source metadata

Neighbor displays, left/right chains, and branch summaries are derived views.

Topology is not "just the drawing."

## 7. Canonical Persisted JSON Shape

The target persisted shape adds a root-level `topology` section.

```json
{
  "topology": {
    "version": 1,
    "source": "local",
    "profiles": {
      "dsl_demo_050426": {
        "nodes": [],
        "edges": []
      }
    }
  }
}
```

Notes:

- Topology is stored per profile.
- The root `source` field defines where the authored topology came from.
- Later versions may support more than one source view, but V1 stores the
  authored profile topology here.

## 8. Profile Topology Shape

Each profile topology contains:

- `nodes`
- `edges`
- optional editor view settings

Example:

```json
{
  "topology": {
    "version": 1,
    "source": "local",
    "profiles": {
      "demo_profile": {
        "nodes": [
          {
            "key": 1,
            "nodeType": "device",
            "deviceRef": "roborio",
            "layout": {
              "bus": 0,
              "row": 0,
              "x": 0.0
            }
          },
          {
            "key": 2,
            "label": "CANnect A",
            "nodeType": "junction",
            "manufacturer": "Swyft",
            "model": "CANnect",
            "layout": {
              "bus": 0,
              "row": 0,
              "x": 250.0
            }
          },
          {
            "key": 3,
            "nodeType": "device",
            "deviceRef": "FALCON 9",
            "layout": {
              "bus": 0,
              "row": 1,
              "x": 250.0
            }
          }
        ],
        "edges": [
          {
            "id": "edge_1",
            "fromNode": 1,
            "fromPort": "can",
            "toNode": 2,
            "toPort": "trunkIn",
            "edgeType": "can_trunk"
          },
          {
            "id": "edge_2",
            "fromNode": 2,
            "fromPort": "drop1",
            "toNode": 3,
            "toPort": "can",
            "edgeType": "can_drop"
          }
        ]
      }
    }
  }
}
```

## 9. Node Types

Minimum node types:

- `device`
- `junction`
- `analyzer`
- `power`
- `virtual`

### 9.1 `device`

A real robot device.

Examples:

- roboRIO
- PDH / PDP
- Talon FX
- Spark MAX
- CANcoder

### 9.2 `junction`

A wiring or distribution module.

Examples:

- CANnect A
- CANnect B
- splice block
- branch module

### 9.3 `analyzer`

A tap or observation point.

Examples:

- CANable Rio End
- CANable Mid Bus
- CANable PDH End

### 9.4 `power`

A power-specific topology node.

Examples:

- battery
- main breaker
- PDH channel block
- VRM

### 9.5 `virtual`

An inferred or diagnostic-only node.

Examples:

- suspected break
- unknown branch
- temporary observer placeholder

## 10. Node Fields

Common node fields:

- `key` (stable per-profile integer key)
- `nodeType`
- `layout`

Optional by type:

- `deviceRef` for `device`
- `label` for non-device nodes
- `manufacturer`
- `model`
- `notes`
- `tags`

Rules:

- `key` must be unique within the profile topology
- non-device node `label` values must be unique within the profile topology
- for `device` nodes, `deviceRef` must reference a configured device label

## 11. Record Types and Ownership

The topology upgrade uses several distinct record types.

### 11.1 Root config record

The top-level unified config object.

Owns:

- `devices`
- `profiles`
- `topology`
- `bridgeConfig`
- `dslTests`

### 11.2 Device record

The authoritative configured hardware record.

Lives in:

- `devices[]`

Owns device identity and hardware/config fields such as:

- `label`
- `deviceInterface`
- `manufacturer`
- `deviceType`
- `id`
- `model`

### 11.3 Profile record

The named profile describing device membership.

Lives in:

- `profiles.<profileName>`

### 11.4 Topology root record

The root topology container.

Lives in:

- `topology`

### 11.5 Topology profile record

The graph for one profile.

Lives in:

- `topology.profiles.<profileName>`

Owns:

- `nodes`
- `edges`
- optional view/layout settings

### 11.6 Topology node record

A node in the topology graph.

Lives in:

- `topology.profiles.<profileName>.nodes[]`

This is not the same thing as a device record.

### 11.7 Topology edge record

A connection between two topology nodes.

Lives in:

- `topology.profiles.<profileName>.edges[]`

### 11.8 Layout record

Embedded rendering/layout metadata for nodes and profile view state.

## 12. No-Duplication Rule for Device-Backed Nodes

Device-backed topology nodes must be thin references to device records.

That means:

- the configured `devices[]` table remains authoritative for device identity
- topology `device` nodes point to configured devices using `deviceRef`
- topology `device` nodes do not duplicate device identity fields

For `device` nodes, do not duplicate:

- `label`
- `manufacturer`
- `deviceType`
- `id`
- `model`

Those fields are owned by the referenced device record.

Example device-backed topology node:

```json
{
  "key": 3,
  "nodeType": "device",
  "deviceRef": "FALCON 9",
  "layout": {
    "bus": 0,
    "row": 1,
    "x": 250.0
  }
}
```

### 12.1 Device identity rule

For this project, the configured device is identified by its `label`.

So in V1:

- `deviceRef` is the device label text
- any record type that refers to a configured device uses `deviceRef` the same
  way

### 12.2 Why this rule exists

This avoids duplicated truth between:

- the `devices[]` table
- the topology graph

Without this rule, rename drift and stale copied fields become likely.

## 13. Standalone Topology Nodes

Non-device topology nodes are self-describing because they do not reference a
configured device record.

These node types may carry their own `label` and optional metadata:

- `junction`
- `analyzer`
- `power`
- `virtual`

Example junction node:

```json
{
  "key": 2,
  "label": "CANnect A",
  "nodeType": "junction",
  "manufacturer": "Swyft",
  "model": "CANnect",
  "layout": {
    "bus": 0,
    "row": 0,
    "x": 250.0
  }
}
```

## 14. Edge Types

Minimum edge types:

- `can_trunk`
- `can_drop`
- `can_tap`
- `dio`
- `pwm`
- `analog`
- `power`
- `virtual`
- `unknown`

Rationale:

- CAN should not be forced to represent every connection
- non-CAN links are part of the robot connection topology
- filtering and diagnostics need typed edges

## 15. Edge Fields

Required edge fields:

- `id`
- `fromNode`
- `fromPort`
- `toNode`
- `toPort`
- `edgeType`

Optional:

- `bidirectional` (default `true` for physical links unless a later subtype
  says otherwise)
- `bridge` (for explicit cross-bus bridging when relevant)
- `notes`
- `tags`

Rules:

- `id` must be unique within the profile topology
- both endpoints must reference existing node keys
- the same node/port cannot be reused by multiple edges unless explicitly
  allowed by node type

## 16. Ports

Ports are strings.

Do not over-model ports in V1.

Common ports:

- `left`
- `right`
- `can`
- `trunkIn`
- `trunkOut`
- `drop1`
- `drop2`
- `drop3`
- `tap`
- `dio`
- `pwm`
- `analog`
- `power`
- `unknown`

Validation:

- unknown ports warn in V1
- invalid endpoint references fail

## 17. Serial-First Authoring Rule

Most FRC robots are expected to use one of these:

- simple serial CAN chain
- mostly serial CAN with one or two branches
- backbone with a few drops

Therefore:

- the topology editor must keep the serial case low-friction
- users must be able to author a simple device chain quickly
- serial layout must be treated as a simple graph shape, not a special
  different data model

In other words:

- simple serial is the easiest authoring mode
- graph is still the underlying truth

## 18. Swyft / CANnect Rule

Swyft CANnect modules are represented as `junction` nodes.

Example:

```text
roborio -- CANnect A -- CANnect B -- PDH
             |    |
          F9     NEO25
```

Canonical representation:

- `CANnect A` is a node with `nodeType = "junction"`
- `trunkIn` and `trunkOut` connect the main path
- `drop1`, `drop2`, ... connect devices

This is the primary reason the topology model must be graph-based.

## 19. Non-CAN Connection Rule

Topology is not limited to CAN.

The same graph system must also represent:

- roboRIO DIO links
- PWM links
- analog links
- power relationships
- analyzer taps

This allows:

- one consistent topology model
- multi-type filtering
- future richer diagnostics

## 20. Layout Metadata

Layout metadata belongs on nodes and view settings, not in a separate
competing topology model.

Node layout fields:

- `bus`
- `row`
- `x`
- optional `y`
- optional `scale`

Optional profile view fields:

- `busOffsets`
- `busSpacing`
- `zoom`
- `panY`

Rule:

- layout affects rendering
- layout does not define semantic connectivity

## 21. Source Model

V1 source values:

- `local`
- `robot`

Planned later:

- `observed`
- `inferred`

Every topology response in CLI or GUI context should include its source.

## 22. Derived Neighbor View

Neighbors are derived from graph edges.

Do not keep a second independent neighbor truth table as the primary model.

For a node, the neighbor view should show:

- local port
- remote node
- remote port
- edge type
- edge id

Example:

```text
neighbor can:
  connectedTo: CANnect A.drop1
  edgeType: can_drop
```

## 23. CLI Surface

Required V1 commands:

- `show topology`
- `show topology --json`
- `show topology nodes`
- `show topology edges`
- `show topology node "<label>"`
- `show neighbors "<label>"`
- `validate topology`

Later candidates:

- `show path <from> <to>`
- `show topology diff local robot`
- `show topology diff local inferred`
- `show topology problems`

User-facing CLI should accept labels.

Internal graph operations should use stable node keys.

## 24. Validation Rules

### Hard errors

- duplicate node key
- duplicate node label
- duplicate edge id
- edge references missing `fromNode`
- edge references missing `toNode`
- device node missing `deviceRef`
- device node `deviceRef` does not exist in configured devices table
- same node port used by multiple edges unless explicitly allowed
- edge endpoint references unknown node

### Warnings

- configured device missing from profile topology
- topology node not in active profile where that matters
- unknown port name
- unknown edge type
- junction has no edges
- device has no edges
- layout position missing
- topology disconnected from roboRIO for topologies that include roboRIO

## 25. Editor Requirements

The topology editor must:

- load topology from the new canonical topology section
- save topology into the canonical topology section
- display nodes
- display typed edges
- edit node position
- edit node type
- edit ports and edges
- support serial chain authoring
- support branch/junction authoring
- support non-CAN connection authoring

Minimum visual forms:

- linear chain
- trunk with drops
- free graph layout

## 26. GUI / Live View Requirements

The GUI/live topology view must:

- load the same canonical topology graph
- render typed edges
- support connection-type filtering
- support multi-select connection-type filtering
- preserve live overlays independent of filtering

Filtering affects only view state, not semantic truth.

## 27. Connection-Type Filtering

Filtering is a core requirement.

Both the topology editor and the GUI/live topology view must support:

- showing only selected connection types
- showing multiple connection types together
- switching quickly between useful presets

Recommended presets:

- `CAN`
- `CAN + Power`
- `Control IO`
- `All Physical`
- `Diagnostic Overlay`
- `All`

Examples:

- only CAN
- CAN + power
- only DIO / PWM / analog
- only analyzer taps
- only inferred / virtual edges

Rule:

- filtering changes rendering only
- filtering must not change validation or inference semantics

## 28. Internal Model Rule

The codebase must use a shared canonical graph normalization layer.

That layer should:

- parse persisted topology JSON
- expose normalized nodes and edges
- derive neighbor views
- support validation
- support filtering
- support future diagnostic overlays

Expected location:

- `tools/common/` shared topology graph helpers

Current `neighborLinks` / `neighborPorts` handling should be treated as legacy
input compatibility, not the final semantic model.

## 29. Migration Rule

This branch is allowed to migrate aggressively.

Migration expectations:

- move semantic truth from `diagram.profiles` adjacency fields into
  `topology.profiles`
- retain import support for older diagram-adjacency data where practical
- update topology editor, CLI, validation, and tests together
- prefer coherent final model over minimizing change count

If temporary compatibility adapters exist, they should be clearly marked as
legacy migration paths.

## 30. Regression Requirements

Required regression coverage:

- topology fixture validation with the new graph schema
- topology editor load/save round-trip tests
- CLI `show topology` and `show neighbors` tests
- node-type and edge-type validation tests
- filter-state behavior tests where headless validation is practical
- negative-path tests for malformed graph input and broken references

Because this project is used by students and non-expert operators, topology
errors must be tested for:

- safe failure
- actionable help

## 31. Acceptance Criteria

The feature is considered implemented when:

- topology is stored as first-class graph data in unified config
- the topology editor loads and saves nodes and edges from the new graph model
- CLI topology commands operate on the graph model
- neighbor views are derived from edges
- serial CAN layouts remain easy to author
- Swyft / CANnect layouts are modeled with junction nodes and branch edges
- analyzer nodes are supported
- non-CAN links are supported
- GUI/live topology surfaces can filter by connection type
- validation reports graph errors and warnings correctly
- regression coverage exists for the new topology model

## 32. Tradeoffs

- A graph model is more complex than simple left/right adjacency, but it is
  semantically correct for branch layouts and diagnostic growth.
- Supporting non-CAN links in the same system increases scope, but avoids
  building a second incompatible wiring model later.
- This branch will require broader changes, but it avoids preserving a weak
  model for compatibility alone.

## 33. Future Extensions

- observed and inferred topology sources
- topology diff views
- analyzer movement tracking
- live evidence overlays
- suspect edge / suspect branch scoring
- topology-aware fault-localization CLI and GUI surfaces
