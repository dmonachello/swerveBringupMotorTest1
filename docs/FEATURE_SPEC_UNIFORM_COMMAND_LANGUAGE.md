# FEATURE_SPEC_UNIFORM_COMMAND_LANGUAGE

**Purpose**

Define a single, consistent command language for the entire Bridge CLI.
This is a breaking redesign with no backward compatibility.

## Scope

**Purpose**

Apply one command model across all major command families and modes:

- Core mode commands (`exec`, `config`, context modes)
- Entity editing (`device`, `group`, `test`, `profile`)
- Subsystems (`bindings`, `can-mappings`, `topology`)
- Persistence and transfer (`save`, `load`, `merge`, `import`, `export`, `push`)
- Validation and diagnostics

## Breaking Policy

**Purpose**

Remove legacy syntax and aliases; only canonical syntax remains.

- No compatibility shims.
- No alias fallback for deprecated forms.
- All docs, tests, and scripts must migrate in the same change window.

## Language Principles

**Purpose**

Define non-negotiable rules for command consistency.

1. All mutable resources use one edit contract.
2. Scalar fields use `set`/`no`.
3. Collection fields use `add`/`remove`.
4. Actions that are not state edits remain imperative verbs.
5. Context mode supports shorthand `field value` for scalar `set`.
6. Inline config forms and context forms are semantically identical.
7. Help and grammar are generated from one schema source.

## Canonical Command Contract

**Purpose**

Standardize state mutation semantics across resources.

Canonical edit operations:

- `show`
- `set <field> <value>`
- `no <field>`
- `add <field> <value>`
- `remove <field> <value>`
- `delete`

Canonical action operations:

- `run ...`
- `push ...`
- `reload ...`
- `validate ...`
- `connect` / `disconnect`

Rule:

- If a command changes a resource field, it must use edit operations.
- If a command executes behavior, it must use action operations.

## Resource Model

**Purpose**

Define all language surfaces as resources with typed fields.

Required resources:

- `device`
- `group`
- `test`
- `profile`
- `bindings.controller`
- `bindings.binding`
- `bindings.axis`
- `canMappings.manufacturer`
- `canMappings.deviceType`
- `topology.node`
- `topology.edge` (or neighbor-port mapping)
- `workspace.sources` (where applicable)

Each resource must declare:

- `resourceName`
- `key` fields (identity)
- mutable fields
- field types and constraints
- allowed operations per field

## Field Schema

**Purpose**

Provide one source of truth for parser, validator, help, and docs.

For each field:

- `kind`: `scalar` or `collection`
- `type`: `string` | `number` | `bool` | `enum` | `json`
- `ops`: allowed ops (`set/no` or `add/remove`)
- optional constraints:
  - numeric range
  - enum domain
  - dependency rules
  - uniqueness rules

## Grammar Architecture

**Purpose**

Replace bespoke per-family grammar with composable resource grammar.

### Global form

```text
<resource-ref> <edit-op>
<action-op>
```

### Resource reference

```text
<resource> <identity...>
```

Examples:

- `device motor1`
- `group intake`
- `test neo25_button`
- `bindings controller controller0`
- `can-mappings manufacturer 5`

### Edit operations

```text
show
set <field> <value>
no <field>
add <field> <value>
remove <field> <value>
delete
```

### Context shorthand

In context modes only:

```text
<field> <value>   => set <field> <value>
```

## Mode Semantics

**Purpose**

Guarantee same meaning across modes.

### Config inline

```text
device motor1 set id 25
group intake add members motor1
test neo25_button set duty 0.25
bindings controller controller0 set port 0
```

### Context mode

```text
id 25
members motor1
duty 0.25
port 0
```

These must normalize to identical AST and behavior as inline forms.

## AST Contract

**Purpose**

Unify execution path for all edit commands.

Normalized edit AST:

```text
{
  resource: <resourceName>,
  identity: <resource identity map>,
  op: "show" | "set" | "no" | "add" | "remove" | "delete",
  field: <field or empty>,
  value: <typed value or empty>
}
```

Normalized action AST:

```text
{
  action: <actionName>,
  args: <typed args>
}
```

## Executor Contract

**Purpose**

Apply all edit commands through one mutation engine.

Flow:

1. Parse to normalized AST.
2. Resolve resource and identity.
3. Validate op against field schema.
4. Coerce value to declared type.
5. Apply mutation.
6. Emit consistent status/error payload.

## Persistence Command Unification

**Purpose**

Standardize save/load/import/export semantics.

Required canonical meanings:

- `save config <path>`: full canonical config.
- `save bridge-config <path>`: bridge-only profile state.
- `save runtime-groups <path>`: runtime snapshot from robot.
- `save sources`: save all loaded local sources.

Rule:

- Command names must map 1:1 to data scope.
- No overlapping names for different scopes.

## Naming Rules

**Purpose**

Prevent drift in fields and commands.

- Field naming style: `camelCase` (single standard).
- Command verbs are lowercase tokens.
- Resource names are stable and explicit.
- No dual spellings for the same concept.

## Error Model

**Purpose**

Make all parse and validation errors predictable.

Required classes:

- unknown command/resource
- missing identity
- unknown field
- invalid operation for field
- type coercion failure
- missing required value
- constraint violation

Error messages must include:

- resource
- identity (if provided)
- field
- expected form/type

## Help and Docs Generation

**Purpose**

Keep runtime help and markdown docs in sync with grammar/schema.

Requirements:

- Generate help command syntax from resource schema metadata.
- Generate command reference sections from same source.
- No hand-written divergent command signatures.

## Migration Tasks (No Compatibility)

**Purpose**

Define exact migration workload for breaking cut.

1. Remove old parser branches and aliases.
2. Remove legacy grammar alternatives.
3. Convert scripts and regression fixtures.
4. Update docs and examples repo-wide.
5. Update autocompletion suggestions to canonical forms only.
6. Remove deprecated hint text.

## Acceptance Criteria

**Purpose**

Define completion gates.

1. Every mutable command family supports canonical edit ops.
2. Inline and context commands produce equivalent AST and results.
3. No legacy syntaxes parse successfully.
4. Help output shows only canonical forms.
5. Docs and scripts contain no deprecated forms.
6. End-to-end workflows still function:
   - create/edit config
   - save/load/import/export
   - push/activate
   - run tests
   - validate flows

## Test Matrix

**Purpose**

Specify minimum coverage for language unification.

Parser tests:

- Valid and invalid forms for each resource/op.
- Context shorthand acceptance in context modes.
- Legacy form rejection.

Executor tests:

- Type coercion and constraint checks.
- `set/no/add/remove` behavior by field kind.
- Resource identity resolution.

Integration tests:

- Bringup flow scripts with canonical commands.
- Save/push/activate cycle.
- Test authoring and run cycle.

Doc lint tests:

- command snippets match canonical syntax
- no forbidden legacy tokens

## Implementation Plan

**Purpose**

Deliver in safe, reviewable increments.

1. Build resource-field schema layer and validators.
2. Implement normalized AST model.
3. Refactor grammar/parser to canonical forms.
4. Refactor executor to shared mutation engine.
5. Remove legacy paths and aliases.
6. Regenerate help/reference surfaces.
7. Update docs and scripts.
8. Run full regression and workflow tests.

## Risks and Mitigations

**Purpose**

Track primary risk areas for a flag-day language cut.

Risks:

- Hidden dependencies on legacy command strings.
- Incomplete field schema coverage.
- Ambiguous shorthand collisions with verbs.

Mitigations:

- Pre-migration inventory with static grep gates.
- Schema completeness checklist per resource.
- Reserved keyword list and parser precedence tests.

## Open Questions

**Purpose**

Capture decisions needed before implementation freeze.

SID_QUESTION: Confirm final canonical resource naming for nested families (`bindings controller` vs flattened resource names).

SID_QUESTION: Confirm whether `delete` is supported in all context modes or only where identity semantics are unambiguous.

