# Feature Spec: Simplify And Unify

## Purpose

Reduce complexity by collapsing overlapping concepts, eliminating redundant state, and making CLI behavior self-evident.

## Scope

Includes:

- Consolidating overlapping configuration concepts (profiles, tests, bindings)
- Simplifying runtime state and ownership (local vs loaded vs active vs dirty)
- Normalizing command behaviors and outputs for clarity
- Removing redundant commands or aliases where they add ambiguity

Overlap here means device labels, groups, tests, and bindings are defined or referenced in multiple files or subsystems, which can diverge.

Excludes:

- New hardware features
- New network transports
- Major UI redesigns
- Robot-side persistence changes (unless required by simplification)

## Current Pain Points

- Overlapping concepts: profiles, tests, bindings, and config sources feel duplicated. Examples: tests/bindings reference device labels defined in profiles; groups/tests live in separate files but execute together; devices table and local config can drift.
- Multiple states: local vs loaded vs active vs dirty causes confusion and recovery needs.
- Command ambiguity: similar actions spread across save/load/merge/import, etc. Examples: `write tests` vs `save tests`, `merge/import/load config`, `save profiles` vs `save config`.
- Output ambiguity: commands do not always say what changed or where it persists. Fix: enforce an output contract (action, scope, persistence, source).

## Goals

- One clear model of ownership for configuration data.
- Fewer states and fewer commands, with stronger defaults.
- Outputs that make the system behavior obvious without extra docs.
- Reduce recovery needs by preventing corruption and ambiguity upstream.
- Preserve the Cisco-style CLI UX (modes, prompts, abbreviations, and `?` help).

Ownership must be visible in CLI outputs and in `show workspace` so users can see what is authoritative.

## Glossary

Purpose: Define key terms used in this spec.

Canonical configuration graph:
The single authoritative in-memory structure that represents all configuration
state and relationships. Profiles, tests, bindings, mappings, and selections are
modeled as subtrees of this graph. Files are serialized views of the graph, not
separate sources of truth.

Ownership:
The explicit designation of which subtree or file is authoritative and responsible for persistence. Commands must surface ownership when they mutate or save.

## State Definitions

Purpose: Provide consistent meanings for state terms used in the CLI.

- local: PC-side in-memory workspace used when not connected or when explicitly targeting local state.
- loaded: Data source present in memory (profiles/config/bindings/tests can be loaded independently).
- active: Current selection within loaded data (active profile, active test set, selected device/mode).
- dirty: In-memory changes not yet persisted to disk.

## Non-Goals

- Adding new commands or layers unless they remove others.
- Increasing feature surface without removing existing complexity.


## Work Item 0: Unified Config Schema (Design First)

Purpose: Define the canonical root so all commands and files become views of one graph.

Decisions:

- Canonical root is a unified config schema.
- Robot config is writable from the PC tool.
- Correctness over backward compatibility.

Design Deliverables:

- Unified config schema (draft) with a full example.
- Explicit mapping from existing files to unified subtrees.
- Validation rules for cross-subtree references.

## Proposed Simplifications

### Work Item 1: Collapse Overlapping Concepts

Purpose: Reduce duplication across profiles, tests, bindings, and config sources by making one authoritative graph.

Why Needed:

- Multiple overlapping concepts create ambiguity about where truth lives.
- Duplicate entry points allow conflicting edits to the same data.
- Users cannot predict which file or subsystem owns the final state.

Benefits:

- A single source of truth for configuration.
- Fewer sync points and fewer opportunities for divergence.
- Clearer mental model for users and maintainers.

Work Items:

- Define a canonical configuration graph and its ownership boundaries.
- Map profiles, tests, and bindings as subtrees of that graph.
- Remove or deprecate commands that bypass the canonical graph.

Notes:

- Compatibility shims may be required for existing scripts.

### Work Item 2: Eliminate Redundant State

Purpose: Remove multiple competing state concepts and replace them with one active view and explicit persistence status.

Why Needed:

- Independent sources can be valid in isolation but inconsistent together (tests and bindings can reference devices not present in the active profile).
- Active selection is not always explicit to the user when switching profiles, test sets, or sources.
- Some transitions are implicit (load/merge/import can reset context, connect/disconnect switches source, profiles init clears loaded state).
- Dirty flags signal change but do not explain scope, ownership, or persistence target.

Benefits:

- Users always know what state is active and what it applies to.
- Fewer edge cases when switching profiles or loading sources.
- Lower need for recovery workflows because context and persistence are explicit.

Proposed Active View Model:

- Maintain a single active context object: profile, test set, selected device, selected mode, and source (local or robot).
- Profile-scoped commands require an explicit context (prompt or flag) and must fail without it.
- Any context change must print the new active context in one line.

Proposed Persistence Status Model:

- Replace raw dirty flags with explicit persistence states per source.
- States: clean, modified, and pending-save (optional if we want staged writes).
- `show workspace` must list each source with its persistence state and file path.

Work Items:

- Define a single active state model and its lifecycle.
- Replace implicit state transitions with explicit context changes and outputs.
- Make persistence status explicit in outputs and status views.

Notes:

- Data chunks include: profiles/devices tables (devices + profiles), bridgeConfig (groups/selected state), tests payload, bindings payload, and CAN mappings.
- This does not remove data chunks; it clarifies their ownership and cross-file consistency.

### Work Item 3: Normalize Command Semantics

Purpose: Make commands predictable by enforcing a consistent pattern for action, scope, and persistence.

Why Needed:

- Commands that look similar behave differently.
- Outputs do not always say what changed or where it was saved.
- Multiple synonyms exist without clear need.

Examples:

- `write tests <path>` vs `save tests <path>` (same intent, different verb).
- `merge config <path>` keeps existing config intact and adds to it, while `import config <path>` replaces the current config.
- `save profiles <path>` vs `save config <path>` (different roots).
- `show sources` vs `show workspace` (overlapping status views).

Benefits:

- Lower learning curve and fewer mistakes.
- Better script portability and automation.
- CLI becomes self-documenting through outputs.

Output Contract:

- Action: what changed.
- Scope: which subtree or profile/test set was targeted.
- Persistence: whether it was saved, and where.
- Source: local or robot.


Work Items:

- Define a consistent command contract for change, scope, and persistence.
- Update command outputs to always report change + persistence.
- Deprecate redundant commands and alias only where necessary.

Notes:

- Migration guidance will be provided as CLI warnings + a script conversion guide.
- The CLI will emit deprecation warnings with the replacement command.

## Concrete Examples (Draft)

Example 1: Save vs Write vs Save Sources
Current: `write tests <path>`, `save tests <path>`, `save sources`.
Issue: Multiple verbs imply different persistence semantics for the same data.
Proposed: `save config <path>` as the canonical persistence command. `save tests`/`write tests` become legacy export-only commands (deprecated with warnings). `save sources` is reserved for saving all currently loaded sources.
Benefit: Clear persistence expectations and fewer ambiguous synonyms.

Example 2: Load vs Import vs Merge
Current: `load sources`, `import config <path>`, `merge config <path>`.
Issue: Overlapping verbs make it hard to predict whether data is replaced or merged.
Current behavior note: `merge config <path>` keeps existing config intact and adds to it, while `import config <path>` replaces the current config. `load sources` reloads all previously configured source paths (devices/config/bindings/mappings/tests) and uses replace semantics for the devices table.
Proposed: Single entry point for config ingestion (for example `load config <path>`) with explicit mode flags such as `--merge` or `--replace`. Rename `load sources` to `reload sources` to make its "refresh existing paths" behavior explicit.
Benefit: One mental model for ingestion and a consistent contract across sources.

Example 3: Profiles vs Unified Config
Current: `save profiles`, `save config`, `save config`, `profiles init`.
Issue: Multiple roots create ambiguity about the authoritative config graph.
Proposed: A single canonical root (unified config). Profile-only save becomes a scoped operation on the unified root rather than a separate file type.
Benefit: Fewer sources of truth and less need for recovery tooling.

Example 4: Show Sources vs Show Workspace
Current: `show sources` and `show workspace` provide overlapping visibility.
Issue: Two commands for the same core state split the user's mental model.
Proposed: `show workspace` becomes the canonical view. `show sources` remains as an alias (or is removed after migration).
Benefit: A single authoritative status view.

Example 5: Active vs Default vs Selected
Current: `profile <name>`, `profile default <name>`, `selected-device`, `selected-mode`, and test set selection.
Issue: Multiple "active" concepts without a unified state summary.
Proposed: One active context model, surfaced explicitly in `show workspace` with clear labels for active profile, active test set, selected device, and selected mode.
Benefit: Users can always explain the current runtime context without guessing.

## Reduced Command Set (Draft)

| Area | Keep (Canonical) | Deprecate or Replace | Benefit |
| --- | --- | --- | --- |
| Save | `save ...` | `write tests` | One verb for persistence. |
| Load/Import | `load config <path>` | `merge config`, `import config` | One entry point with explicit mode flags. |
| Profiles | `profile <name>`, `profile default <name>` | `profiles init` (if unified root is canonical) | Fewer roots and clearer ownership. |
| Tests | `test ...`, `tests ...`, `save tests` | Duplicate test IO commands | Consistent authoring flow. |
| Bindings | `bindings ...` | N/A | Centralized edit surface. |
| CAN Mappings | `can-mappings ...` | N/A | Centralized edit surface. |
| Validation | `validate all`, `validate file` | Fragmented per-source commands (if redundant) | Clear pre-save checks. |
| Recovery | `recover ...` | Ad-hoc recovery flows | Explicit recovery path only. |
| Status/Show | `show workspace` | `show sources` (alias or remove) | Single status view. |


## Inventory: Redundant Commands And Overlapping Responsibilities (Draft)

Command-level overlaps:

| Commands | Overlap | Proposed Direction |
| --- | --- | --- |
| `write tests <path>` vs `save tests <path>` | Same persistence action, different verbs. | Deprecate `write tests`, keep `save tests`. |
| `savep <path>` vs `save profiles [<path>]` | Alias for saving profiles. | Remove `savep` or keep as hidden legacy alias. |
| `show sources` vs `show workspace` vs `show session` | Overlapping status views. | Keep `show workspace`; remove `show session`. |
| `show bindings` vs `bindings show` | Same data, two entry points. | Keep `show bindings`, deprecate `bindings show` or make one alias. |
| `show can-mappings` vs `can-mappings show` | Same data, two entry points. | Keep `show can-mappings`, deprecate `can-mappings show` or make one alias. |
| `merge config <path>` vs `import config <path>` vs `load sources` | Multiple ingest paths with unclear replace/merge semantics. | Replace with `load config <path> --merge|--replace` and rename `load sources` to `reload sources`. |
| `save profiles` vs `save config` vs `save config` vs `save bridge-config` | Multiple persistence roots. | Keep one canonical root (unified config). |
| `ls` vs `show`, `val` vs `validate`, `prof` vs `profile`, `cfg` vs `configure terminal` | Hard aliases that duplicate grammar. | Enforce canonical form and hard-error removed aliases. |

Responsibility overlaps:

| Responsibility | Overlap | Risk |
| --- | --- | --- |
| profiles/devices tables vs tests payload | Tests reference device labels defined in profiles. | Tests can become invalid when profiles change. |
| profiles/devices tables vs bindings | Bindings reference devices/controllers defined elsewhere. | Bindings can point to missing or renamed devices. |
| bridgeConfig vs devices table | Groups/selected state stored separately from devices table. | Group membership can drift from device definitions. |
| Local vs robot state | Local and robot can diverge across connect/disconnect. | Confusion about what is authoritative. |
| Default vs active selection | Default profile/test set stored in config while active selection can differ in memory. | Commands may target unexpected context if not explicit. |


## Design Artifacts (Draft)

### Unified Config Schema (Example)

Purpose: Provide a concrete example of the canonical graph.

```json
{
  "schema_version": 1,
  "data_version": "2026-04-02_120000",
  "data_hash": "<computed>",
  "generated_at": "2026-04-02T12:00:00-04:00",
  "devices": [
    {
      "label": "FALCON 9",
      "interface": "CAN",
      "manufacturer": 4,
      "deviceType": 2,
      "id": 9,
      "model": "CTRE Falcon 500",
      "type": "motor"
    },
    {
      "label": "SPARKMAX/NEO 25",
      "interface": "CAN",
      "manufacturer": 5,
      "deviceType": 2,
      "id": 25,
      "model": "REV NEO",
      "type": "motor"
    },
    {
      "label": "SPARKMAX/NEO550 7 limit fwd",
      "interface": "DIO",
      "type": "limitSwitch",
      "dio": 0,
      "invert": true
    }
  ],
  "profiles": {
    "home_031226": {
      "devices": ["FALCON 9", "SPARKMAX/NEO 25", "SPARKMAX/NEO550 7 limit fwd"],
      "notes": "Home profile",
      "tags": ["home", "demo"]
    }
  },
  "tests": {
    "home_031226": {
      "default_test_set": "default",
      "test_sets": {
        "default": [
          {
            "name": "Hold to run",
            "type": "composite",
            "devices": ["FALCON 9"],
            "duty": 0.2,
            "termination": {"hold": true},
            "hold": {"onRelease": "pass"},
            "enabled": false
          }
        ]
      }
    }
  },
  "bindings": {
    "global": {
      "controllers": [
        {"name": "controller0", "type": "XBOX", "port": 0}
      ],
      "bindings": [
        {"command": "runTest", "controller": "controller0", "input": "button", "id": "A", "mode": "hold"}
      ],
      "axes": [
        {"command": "leftDrive", "controller": "controller0", "id": "leftY", "invert": true, "deadband": 0.12}
      ]
    },
    "by_profile": {}
  },
  "can_mappings": {
    "manufacturers": {"4": "CTRE", "5": "REV"},
    "device_types": {"2": "MotorController"}
  },
  "bridge_config": {
    "by_profile": {
      "home_031226": {
        "groups": [
          {"name": "motors", "devices": ["FALCON 9", "SPARKMAX/NEO 25"], "enabled": true}
        ],
        "selected_device": {"device": "FALCON 9", "enabled": false},
        "selected_mode": "off"
      }
    }
  }
}
```

### Active Context Object (Draft)

Purpose: Make the active selection explicit and visible.

Example:
```json
{
  "source": "local",
  "profile": "home_031226",
  "test_set": "default",
  "selected_device": "FALCON 9",
  "selected_mode": "off"
}
```

Rules:

- Any change to this context must be printed as a single-line summary.
- Commands that mutate state must echo the active context used.

### Command Behavior Table (Draft)

Purpose: Map old commands to new canonical forms.

| Old Command | New Command | Notes |
| --- | --- | --- |
| `write tests <path>` | `save config <path>` | Deprecate `write tests` (legacy export). |
| `savep <path>` | `save profiles <path>` or `save config <path>` | Prefer unified root. |
| `merge config <path>` | `load config <path> --merge` | Explicit merge flag. |
| `import config <path>` | `load config <path> --replace` | Explicit replace flag. |
| `load sources` | `reload sources` | Refresh existing configured paths. |
| `show sources` | `show workspace` | Single status view. |
| `show session` | `show workspace` | Removed; hard-error with canonical replacement. |
| `bindings show` | `show bindings` | Single entry point. |
| `can-mappings show` | `show can-mappings` | Single entry point. |
| `prof ...` | `profile ...` | Removed; hard-error with canonical replacement. |
| `cfg` | `configure terminal` | Removed; hard-error with canonical replacement. |
| `val ...` | `validate ...` | Removed; hard-error with canonical replacement. |
| `ls` | `show` | Removed; hard-error with canonical replacement. |

Note: Subcommand mappings (group/device/test modes) will follow the same rule: one canonical verb, explicit context, and explicit persistence reporting.

## Active Context Rules

Purpose: Remove ambiguity when multiple items exist in one config.

Rules:

- Any profile-scoped command must require a visible profile context (prompt context or explicit flag).
- No silent fallback to default profile when a profile is required.
- Any state-mutating command must echo the active profile/test set it used.
- Commands that do not require a profile must say so explicitly in their output.
- If a command can target both local and robot sources, it must state which source was used.

## Open Questions

- What is the minimal set of commands required to manage configuration safely?
- What is the acceptable deprecation timeline for legacy commands and scripts?

## Tradeoffs

- Fewer commands means a steeper migration for existing users. This is acceptable now; we will prioritize correctness over backward compatibility.
- Stronger defaults may remove some flexibility.
- Collapsing concepts reduces flexibility but increases clarity.

## Migration Strategy (Sketch)

- Phase 1: Shadow mode that warns on deprecated flows.
- Phase 2: Hard deprecation and removal of old flows.
- Phase 3: Documentation updates and script migration.

## Success Criteria

- Users can explain the config state after any command without consulting docs.
- Recovery tooling is rarely needed because corruption/ambiguity is prevented.
- Command set is smaller and more consistent than today.

## Immediate Actions (Execute Now)

- Inventory redundant commands and overlapping responsibilities.
- Propose a reduced command set with explicit behavior tables.
- Draft a migration plan with deprecation timeline.

