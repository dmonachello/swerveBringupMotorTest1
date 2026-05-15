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
- adjacency language still leaks into some surfaces as `neighborLinks` /
  `neighborPorts` rather than explicit endpoint-to-endpoint edge records
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
- Physical truth: port count, port labels, and terminator state are separate
  concepts and must not be conflated.
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
- explicit port-to-port edge semantics
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
- declared ports
- layout metadata
- source metadata

Neighbor displays, left/right chains, and branch summaries are derived views.

`neighborLinks` and `neighborPorts` are not canonical record types in the
target design.

Topology is not "just the drawing."

The graph must distinguish between:

- declared physical port capacity on a node
- actual wired edges in the active profile topology
- optional bus/junction helper nodes used to represent branch structure
- electrical end-of-bus state indicated by the device `terminator` field

Port count does not imply terminator state.

Terminator state does not imply port count.

### 6.1 Graph normalization

All topology consumers must use one shared graph normalization layer.

That layer must:

- parse raw topology JSON
- build node-key lookup maps
- build label and `deviceRef` lookup maps
- resolve `deviceRef` references into configured device records
- resolve effective port declarations
- validate edge endpoint references
- derive neighbor views
- derive filtered views
- derive traversal and path structures
- preserve unknown or invalid references for actionable diagnostics

Rule:

- no CLI, editor, GUI, or diagnostic code may walk raw topology JSON directly
  for semantic decisions
- semantic decisions must operate on normalized graph objects

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

### 8.1 Profile membership rule

Topology is per profile.

Rules:

- every `device` node `deviceRef` must belong to that profile's device list
- non-device nodes do not require profile membership
- the same configured device may appear in more than one profile
- topology nodes are not shared across profiles in V1

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
- `ports`
- `notes`
- `tags`

Rules:

- `key` must be unique within the profile topology
- non-device node `label` values must be unique within the profile topology
- for `device` nodes, `deviceRef` must reference a configured device label
- node-level `ports` may be omitted only when the node can be resolved from a
  known device or node class that provides default port definitions

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
- `terminator`

May also own device-class physical-capacity fields such as:

- `canPorts`
- `canPortCount`
- `canPortLabels`
- `canPortMode`

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
- `terminator`

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

Graph identity rules:

- persisted edges use node keys
- CLI input accepts labels and resolves them to node keys
- labels are user-facing identity and display text
- node keys are graph identity
- `deviceRef` links a topology node to a configured device record but is not
  itself graph identity

### 12.2 Why this rule exists

This avoids duplicated truth between:

- the `devices[]` table
- the topology graph

Without this rule, rename drift and stale copied fields become likely.

### 12.3 Rename behavior

If a configured device label changes through supported config flows:

- all `deviceRef` references must be updated in the same operation
- validation must fail if a `deviceRef` points to a missing configured device
- migration and repair tools must report stale `deviceRef` values clearly

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

### 14.1 Edge families

Minimum edge-family groupings:

- physical-forwarding: `can_trunk`, `can_drop`, `dio`, `pwm`, `analog`,
  `power`
- observer: `can_tap`
- diagnostic-only: `virtual`
- unknown: `unknown`

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
- a node cannot exceed its declared CAN port capacity
- port-usage validation is based on declared node/device ports, not on
  inferred left/right chain position

### 15.1 Edge id rule

Edge ids must remain stable across load/save round trips.

Recommended rules:

- imported or migrated topology should use deterministic ids derived from
  endpoints where practical
- interactively created topology may use monotonic ids such as `edge_<N>`
- layout-only edits must not rewrite edge ids

## 16. Ports

Ports are strings with declared per-node semantics.

V1 must support explicit port declarations even if some nodes still use
class-default ports.

Common ports:

- `can`
- `canA`
- `canB`
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

### 16.1 Port declarations

Each topology-capable node class must have a resolved set of allowed ports.

That set may come from:

- the referenced device record
- a built-in device-class mapping
- explicit `ports` declared on the topology node for non-device nodes

Example device-class port shapes:

- 1-port endpoint-capable device: `["can"]`
- 2-port inline-capable device: `["canA", "canB"]`
- 6-port CANnect device: `["1", "2", "3", "4", "5", "6"]`

### 16.1.1 Port capability metadata

Ports are not just names.

Each resolved port should carry enough metadata for validation.

Minimum target fields:

- `name`
- `family`
- `maxConnections`
- `allowedEdgeTypes`

Possible later fields:

- `role`
- `direction`

### 16.2 Port count versus terminator

Port count and `terminator` are independent.

Rules:

- a 1-port CAN device may or may not be a terminator
- a 2-port CAN device may be configured as a terminator in the current profile
- `terminator=true` means the device is intended to sit at a terminated bus
  end in the configured wiring
- `terminator=false` means the device is not marked as a terminated end by
  configuration

The topology graph defines connectivity.

The device record defines terminator state.

The system must not infer terminator state from port count alone.

### 16.3 Port usage rules

Default V1 rules:

- each declared CAN port may be used by at most one CAN-family edge
- a device may not have more CAN edges than its declared CAN ports allow
- node classes that intentionally support branch fanout must declare the
  corresponding ports explicitly
- if a node class allows shared or multiplexed usage later, that must be
  explicit in schema and validation rather than inferred

### 16.3.1 Edge-family compatibility rules

Validation must enforce family compatibility between edges and ports.

Examples:

- `can_trunk`, `can_drop`, and `can_tap` require CAN-capable ports
- `dio` requires DIO-capable ports
- `pwm` requires PWM-capable ports
- `analog` requires analog-capable ports
- `power` requires power-capable ports
- `virtual` may connect any family, but must be marked diagnostic-only

Impossible combinations must fail validation.

Examples:

- `edgeType=dio` connected to a CAN-only port
- `edgeType=power` connected to a CAN-only port

Validation:

- unknown ports warn in V1
- invalid endpoint references fail
- edges that overuse a node's declared port capacity fail

### 16.4 Bus and junction usage

The model must support both:

- direct device-port to device-port CAN edges for ordinary serial authoring
- bus/junction helper nodes when the wiring contains explicit branch or
  distribution structure

This means bus/junction nodes are supported but not mandatory for every simple
serial chain.

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
- bus/junction helper nodes may remain implicit in the common serial case
- explicit junction modeling is required when branch structure or multi-port
  distribution hardware needs to be represented faithfully

## 18. Swyft / CANnect Rule

Swyft CANnect modules must be represented with explicit multi-port semantics.

Example:

```text
roborio -- CANnect A -- CANnect B -- PDH
             |    |
          F9     NEO25
```

Canonical representation:

- `CANnect A` may be represented as a `junction` node or another explicit
  multi-port node class, but it must expose its real CAN attachment points
- the representation must support up to the real hardware port count
- each used CANnect port must be individually addressable in edges
- trunk and drop semantics may be represented by port names, edge types, or
  both, but must remain machine-readable

This is the primary reason the topology model must be graph-based.

### 18.1 Mixed-capacity device rule

The topology system must correctly support at least these physical patterns:

- 1-port CAN device
- 2-port CAN device
- 6-port CAN distribution device

The system must not force all CAN devices into one of these false models:

- every device has `left` and `right`
- every 1-port device is always a terminator
- every branch must be flattened into a serial neighbor list

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

Minimum V1 non-CAN scope:

- schema support for `dio`, `pwm`, `analog`, and `power`
- validation support for basic port-family matching
- editor display and filtering support
- no requirement for advanced non-CAN diagnostics in V1

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

### 20.1 Bus versus layout

`layout.bus` must not become the long-term semantic network model.

If used in V1, it is a rendering-grouping field only.

Rules:

- layout fields are view metadata
- semantic connectivity comes from edges
- network identity should be a separate semantic concept when introduced
- code must not treat `layout.bus` as authoritative network identity for graph
  semantics

## 21. Source Model

V1 source values:

- `local`
- `robot`

Planned later:

- `observed`
- `inferred`

Every topology response in CLI or GUI context should include its source.

### 21.1 Unknown handling

Unknown topology content is allowed only under controlled rules.

Rules:

- `unknown` edge types may be allowed as warnings in authoring mode
- strict or deploy validation may warn or fail on unknown edge types
- diagnostics must ignore unknown edges unless explicitly enabled

## 22. Derived Neighbor View

Neighbors are derived from graph edges.

Do not keep a second independent neighbor truth table as the primary model.

The word "neighbor" is read/query vocabulary, not persisted connection-truth
vocabulary.

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

### 22.1 Traversal rules

Traversal and path queries must distinguish between edge families.

Default traversal behavior:

- physical-forwarding edges participate in normal connectivity and path queries
- observer edges do not act as path-through connections
- diagnostic-only edges are excluded unless explicitly requested
- unknown edges are excluded unless explicitly requested

Analyzer rule:

- analyzer nodes attach through observer/tap edges
- analyzers must not be treated as traffic-forwarding nodes during normal
  connectivity traversal

## 23. CLI Surface

Required V1 commands:

- `show topology`
- `show topology --json`
- `show topology nodes`
- `show topology edges`
- `topology edge set "<nodeA>" <portA> "<nodeB>" <portB> type <edgeType>`
- `topology edge delete "<node>" <port>`
- `topology edge clear "<node>"`
- `show topology node "<label>"`
- `show neighbors "<label>"`
- `validate topology`
- `validate topology --strict`

Later candidates:

- `show path <from> <to>`
- `show topology diff local robot`
- `show topology diff local inferred`
- `show topology problems`

User-facing CLI should accept labels.

Internal graph operations should use stable node keys.

Rule:

- write/edit commands must use edge-native vocabulary
- neighbor-oriented commands are read/query convenience surfaces only
- do not expose `neighborLinks` or `neighborPorts` as canonical editable
  records in the final design

Command error behavior:

- semantic failures must report semantic errors, not generic syntax errors
- unknown labels must report the unresolved label
- conflicting port reuse must report the conflicting node/port or edge id
- delete behavior must be explicitly defined rather than assumed idempotent

JSON output contracts must be documented and tested for:

- `show topology --json`
- `show topology nodes --json`
- `show topology edges --json`
- `show topology node "<label>" --json`
- `show neighbors "<label>" --json`
- `validate topology --json`

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
- edge references a port not declared for that node
- node exceeds declared CAN port capacity
- edge type is incompatible with either endpoint port family
- duplicate reciprocal migration creates conflicting edges

### Warnings

- configured device missing from profile topology
- topology node not in active profile where that matters
- unknown port name
- unknown edge type
- junction has no edges
- device has no edges
- layout position missing
- topology disconnected from roboRIO for topologies that include roboRIO
- device terminator configuration appears inconsistent with graph position
- ambiguous one-sided migrated neighbor records

### Validation modes

Support two validation modes:

- authoring
- strict/deploy

Authoring mode:

- allows incomplete work in progress
- reports warnings for unknown or provisional content where safe

Strict/deploy mode:

- blocks broken endpoint references
- blocks graph-integrity failures
- blocks impossible edge-family and port-family combinations

## 25. Editor Requirements

The topology editor must:

- load topology from the new canonical topology section
- save topology into the canonical topology section
- display nodes
- display typed edges
- edit node position
- edit node type
- edit ports and edges
- expose or derive per-node port definitions during authoring
- support serial chain authoring
- support branch/junction authoring
- support non-CAN connection authoring

Editor behavior rules:

- common 1-port, 2-port, and CANnect-class nodes must be easy to author
- the editor must not imply that all CAN devices have `left` and `right`
- the editor must validate port overuse with device-specific error messages
- the editor should allow simple serial authoring without forcing visible
  junction nodes unless needed
- filtering must never mutate saved graph truth

Headless editor tests must cover:

- load graph fixture
- move node
- add edge
- delete edge
- save
- reload
- compare normalized graph

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

Recommended saved view shape:

```json
{
  "view": {
    "filters": {
      "edgeTypes": ["can_trunk", "can_drop"],
      "showVirtual": false,
      "showAnalyzers": true
    }
  }
}
```

## 28. Internal Model Rule

The codebase must use a shared canonical graph normalization layer.

That layer should:

- parse persisted topology JSON
- build node-key maps
- build label and `deviceRef` lookup maps
- resolve device references
- resolve effective ports
- expose normalized nodes and edges
- derive neighbor views
- derive traversal and path structures
- support validation
- support filtering
- support future diagnostic overlays

Expected location:

- `tools/common/` shared topology graph helpers

The canonical persisted connection model is:

- nodes
- declared ports
- edges

Everything neighbor-oriented is derived from that model.

## 29. Migration Rule

This branch is expected to switch fully to the graph-native model.

Implementation expectations:

- move semantic truth fully into `topology.profiles`
- update topology editor, CLI, validation, and tests together
- replace neighbor-oriented write semantics with edge-native write semantics
- remove any requirement to preserve `neighborLinks` / `neighborPorts` as
  authoritative or first-class persisted connection records
- define deterministic conversion from old neighbor-shaped data to edge records
- prefer coherent final model over minimizing change count

This spec does not require gradual compatibility steps inside the branch
target.

Migration from older topology data must:

- create one node per topology-bearing device
- preserve key and layout coordinates where available
- convert left/right or neighbor pairs into explicit edges
- avoid duplicate reciprocal edges
- assign deterministic edge ids
- preserve legacy port names only when true device-port mapping is unknown
- emit warnings for ambiguous or one-sided records

## 30. Regression Requirements

Required regression coverage:

- topology fixture validation with the new graph schema
- topology editor load/save round-trip tests
- CLI `show topology` and `show neighbors` tests
- CLI edge-edit command tests
- node-type and edge-type validation tests
- filter-state behavior tests where headless validation is practical
- negative-path tests for malformed graph input and broken references
- JSON output contract tests for topology CLI commands
- headless normalized-graph round-trip tests

Round-trip expectations:

- load -> normalize -> save must not unexpectedly change valid topology
- editor position changes must not rewrite edge identity
- filtering must not affect saved graph truth
- neighbor views must not be persisted as authoritative graph truth

Because this project is used by students and non-expert operators, topology
errors must be tested for:

- safe failure
- actionable help

## 31. Acceptance Criteria

The feature is considered implemented when:

- topology is stored as first-class graph data in unified config
- the topology editor loads and saves nodes and edges from the new graph model
- CLI topology commands operate on the graph model
- CLI write/edit topology commands operate on explicit edges, not neighbor
  records
- neighbor views are derived from edges
- serial CAN layouts remain easy to author
- 1-port, 2-port, and CANnect-class multi-port devices are represented without
  false left/right assumptions
- Swyft / CANnect layouts are modeled with junction nodes and branch edges
- analyzer nodes are supported
- non-CAN links are supported
- GUI/live topology surfaces can filter by connection type
- validation reports graph errors and warnings correctly
- shared graph normalization is used by all topology consumers
- regression coverage exists for the new topology model

## 32. Tradeoffs

- A graph model is more complex than simple left/right adjacency, but it is
  semantically correct for branch layouts and diagnostic growth.
- Keeping neighbors only as a derived read/query concept is a cleaner mental
  model, but it requires renaming or replacing older neighbor-oriented edit
  surfaces.
- Supporting explicit per-device port capacity adds schema and validator
  complexity, but prevents incorrect assumptions about 1-port, 2-port, and
  multi-port hardware.
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

## 34. Implementation Plan

Purpose: define the recommended execution order for implementing this spec in
the `topology_upgrade` branch.

This plan assumes the branch switches fully to edge-native topology truth and
does not preserve neighbor-shaped records as authoritative model state.

### 34.1 Phase 1: shared graph core

Implement the shared normalized graph layer first.

Primary targets:

- `tools/common/profile_constants.py`
- new shared topology graph helpers under `tools/common/`
- `tools/common/topology_parse.py`

Required outcomes:

- normalized node-key map
- normalized label and `deviceRef` lookup maps
- resolved device-backed node view
- resolved port declarations and capability metadata
- edge-family classification
- derived neighbor and traversal helpers

Gate:

- no topology consumer should need to walk raw topology JSON directly for
  semantic decisions once this phase lands

### 34.2 Phase 2: validation

Implement shared topology validation on top of the normalized graph.

Primary targets:

- `tools/config/schema_store.py`
- `tools/can_topology/validate_profiles.py`
- shared validation helpers under `tools/common/`

Required outcomes:

- authoring validation mode
- strict/deploy validation mode
- endpoint reference validation
- device membership validation
- port-capacity validation
- edge-family versus port-family validation
- deterministic and actionable diagnostics

Gate:

- CLI and editor validation must call the shared validation layer rather than
  maintaining separate semantic rules

### 34.3 Phase 3: migration

Implement deterministic conversion from older topology-bearing records into the
canonical `nodes` / `edges` model.

Primary targets:

- migration logic in shared topology helpers
- topology editor load paths
- CLI/local config load paths

Required outcomes:

- old `neighborLinks` / `neighborPorts` convert into edges
- duplicate reciprocal edges are suppressed
- deterministic edge ids are assigned
- legacy port names are preserved only when real port mapping is unknown
- ambiguous or one-sided old records emit warnings

Gate:

- load -> normalize -> save must preserve valid topology semantics without
  recreating neighbor-shaped truth

### 34.4 Phase 4: CLI read surfaces

Move all topology read/report behavior onto the normalized graph.

Primary targets:

- `tools/can_nt/bridge_cli.py`

Required outcomes:

- `show topology`
- `show topology nodes`
- `show topology edges`
- `show topology node "<label>"`
- `show neighbors "<label>"`
- stable JSON output contracts for all of the above

Gate:

- neighbor output must be clearly derived from edges, not loaded from stored
  neighbor tables

### 34.5 Phase 5: CLI write surfaces

Replace neighbor-oriented write commands with edge-native edit commands.

Primary targets:

- `tools/can_nt/bridge_cli.py`
- CLI docs and grammar artifacts when command text changes

Required outcomes:

- `topology edge set "<nodeA>" <portA> "<nodeB>" <portB> type <edgeType>`
- `topology edge delete "<node>" <port>`
- `topology edge clear "<node>"`
- semantic error messages that name unresolved labels, conflicting ports, or
  conflicting edges

Gate:

- no canonical topology write path should require `neighborLinks` or
  `neighborPorts` command semantics

### 34.6 Phase 6: editor load/save and editing model

Move the topology editor fully onto canonical graph truth.

Primary targets:

- `tools/can_topology/can_top_editor.py`
- shared topology helpers under `tools/common/`

Required outcomes:

- load canonical `topology.profiles.<profile>`
- save canonical `topology.profiles.<profile>`
- use resolved port definitions during editing
- enforce device-specific port limits
- keep filtering/view state separate from graph truth
- preserve edge identity across layout-only edits

Gate:

- editor save must not persist neighbor-shaped authoritative topology state

### 34.7 Phase 7: filtering and traversal behavior

Finalize filtered views and traversal semantics on the normalized graph.

Primary targets:

- shared topology helpers under `tools/common/`
- editor and live view surfaces

Required outcomes:

- connection-type filtering that does not mutate graph truth
- observer-edge traversal rules for analyzers
- explicit handling of `virtual` and `unknown` edges
- path and neighbor derivation behavior consistent across CLI and GUI surfaces

Gate:

- filtering changes only rendering/query views, never saved graph truth

### 34.8 Phase 8: regression and fixtures

Add fixtures and tests after the core semantics are stable.

Primary targets:

- `tests/regression/`
- topology-related Python tests under `tools/common/tests/`,
  `tools/can_nt/tests/`, and `tools/can_topology/`

Required outcomes:

- simple serial fixture
- one-branch serial fixture
- Swyft CANnect trunk-with-drops fixture
- round-trip tests
- migration tests
- strict validation tests
- CLI JSON contract tests
- headless editor graph tests

Gate:

- the topology regression suite must fail on semantic drift in graph shape,
  validation behavior, or edge-edit behavior

## 35. Example Fixtures

The spec should maintain concrete example fixtures for at least:

- simple serial CAN chain
- serial chain with one branch
- Swyft CANnect trunk with drops

These examples are test and implementation anchors, not optional illustrations.

## 36. Diagnostics Terminology

Standard terms:

- suspect edge
- suspect branch
- suspect junction
- suspect downstream segment
- observed visibility
- inferred boundary
- confidence

Avoid overclaiming physical causes such as:

- bad wire
- broken connector
- short
- termination failure

unless supported by physical-layer evidence.

## 37. Do Not Do

Do not:

- store neighbor tables as authoritative topology truth
- duplicate device identity fields into topology nodes
- infer terminator state from port count
- assume all CAN devices have left/right ports
- let filtering mutate saved graph data
- make diagnostics scrape rendered neighbor text
