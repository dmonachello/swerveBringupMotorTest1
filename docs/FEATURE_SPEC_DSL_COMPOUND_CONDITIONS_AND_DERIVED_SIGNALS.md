SPEC_STATUS: PROPOSED

# Feature Spec: DSL Compound Conditions And Derived Signals

## 1. Purpose

Purpose: define the next declarative expansion of the Robot Diagnostic Test DSL by adding:

1. compound boolean conditions
2. test-scoped derived signals
3. additional runtime-provided signals as needed by the device signal registry

This spec is intended to increase authored expressiveness without adding procedural execution.

This spec does not add:

- loops
- mutable variables
- callbacks
- ordered statement execution inside a phase
- general-purpose scripting
- hardware-affecting behavior outside the existing DSL runtime model

## 2. Design Rule

The language must gain more vocabulary, not more control flow.

A DSL test remains:

- a live rule set
- evaluated every robot control-loop tick
- phase-structured only at `init`, `main`, and `close`

Within a phase, authored source order still must not define execution order.

## 3. Goals

This feature should support:

- richer pass/fail conditions without procedural workarounds
- reusable named meanings inside one test
- canonical use of derived runtime signals such as confidence-related signals
- clearer authored tests for noisy, ambiguous, or multi-signal hardware behavior
- future alignment between runtime signals, UI surfaces, reports, and DSL conditions

## 4. Non-Goals

This feature does not add:

- `if`
- `else`
- `while`
- `for`
- user-authored variables with mutable assignment
- user-authored recursion
- backtracking or search
- rule-triggered hardware actions
- test-defined devices or runtime registry mutation

This feature is not intended to replace:

- the device signal registry
- the current `set` / `clear` / `abort` / `success` / `until` / `require` model
- host-side source compilation to normalized JSON

## 5. Terminology

### 5.1 Primitive Signal

A primitive signal is a readable DSL signal supplied by the runtime device/signal registry.

Examples:

- `motor1.current`
- `motor1.velocity`
- `motor1.confidenceLevel`
- `controller0.A`
- `timer.elapsed`

Primitive signals may be vendor-native, runtime-derived, or host/robot-integrated, but they are provided by the canonical registry rather than authored inside the test.

### 5.2 Derived Signal

A derived signal is a test-scoped, read-only authored signal whose value is computed from other signals or conditions.

Derived signals do not own hardware.

Derived signals do not write hardware.

Derived signals exist only within the test that declares them.

### 5.3 Condition Expression

A condition expression is a boolean expression composed from:

- primitive signal predicates
- derived signal references
- boolean operators
- supported condition operators such as comparison, `between`, `outside`, and `stable`

## 6. Feature Summary

This spec introduces three compatible capabilities:

### 6.1 Compound Conditions

Conditions may now combine subconditions with:

- `and`
- `or`
- `not`

### 6.2 Test-Scoped Derived Signals

Authors may define named derived signals at test scope and then reference them in later conditions.

Derived signals are expressions only.

They are not statements with side effects.

### 6.3 Additional Canonical Runtime Signals

The device signal registry may continue to add new primitive signals such as:

- `confidenceLevel`
- `presenceConfidenceLevel`
- `functionConfidenceLevel`
- `healthy`
- `responding`
- `stalled`
- `canVisible`

This spec does not require those exact names beyond examples, but it assumes the signal registry remains the authoritative source for runtime-provided signals.

## 7. Syntax

## 7.1 Compound Conditions

Existing single-condition forms remain valid.

New boolean composition forms are added:

```text
condition and condition
condition or condition
not condition
( condition )
```

Examples:

```text
require motor1.confidenceLevel > 75 and motor1.faults == false
abort motor1.current > 40 or motor1.temperature > 80
success controller0.A and motor1.velocity > 100
require not motor1.faults
require (motor1.velocity > 100 and motor1.current between 5 30)
```

## 7.2 Derived Signal Declarations

New test-scope declaration form:

```text
derived signal <name> = <condition-expression>
```

Examples:

```text
derived signal ready = motor1.confidenceLevel > 75 and not motor1.faults
derived signal stallSuspect = motor1.output > 0.4 and motor1.velocity < 100 stable 0.250
derived signal operatorConfirmed = controller0.A stable 0.100
```

Rules:

- `<name>` is a test-scoped identifier
- a derived signal evaluates to a boolean value in this version
- derived signals are declared outside `init`, `main`, and `close`
- derived signals are read-only
- derived signals may reference primitive signals and earlier or later derived signals if the dependency graph is acyclic

## 7.3 Statement Usage

Derived signals may be referenced anywhere a boolean condition is currently valid in `main`.

Examples:

```text
require ready
abort stallSuspect
success operatorConfirmed and motor1.velocity > 100
until timer.elapsed >= 3.0 and ready
```

This version does not add derived-signal usage to `set` source expressions.

## 8. Boolean Operator Semantics

## 8.1 `and`

`A and B` is true only when both operands are true.

## 8.2 `or`

`A or B` is true when either operand is true.

## 8.3 `not`

`not A` is true when operand `A` is false.

## 8.4 Parentheses

Parentheses control grouping and must be preserved by normalization.

## 8.5 Precedence

The language uses this precedence order:

1. parenthesized subexpression
2. atomic predicate or derived-signal reference
3. postfix `stable`
4. prefix `not`
5. `and`
6. `or`

Associativity:

- `and` is left-associative
- `or` is left-associative

Examples:

```text
not A and B
```

means:

```text
(not A) and B
```

and:

```text
A or B and C
```

means:

```text
A or (B and C)
```

## 9. Predicate Semantics

The current atomic predicate forms remain valid:

```text
device.signal
device.signal > literal
device.signal >= literal
device.signal < literal
device.signal <= literal
device.signal == literal
device.signal != literal
device.signal between low high
device.signal outside low high
```

`stable <seconds>` remains a postfix modifier on one atomic predicate or parenthesized subexpression.

Examples:

```text
controller0.A stable 0.100
(motor1.velocity > 100 and motor1.current between 5 30) stable 0.250
```

Semantics:

- the raw expression is evaluated every tick
- the effective expression becomes true only after the raw expression has remained continuously true for the stable duration
- `stable` modifies truth over time, not clause priority

## 10. Derived Signal Semantics

## 10.1 Scope

Derived signals are test-scoped only.

They are not added to the global device registry.

They are not added to `bringup_system.json` outside the owning test payload.

## 10.2 Evaluation Model

Derived signals are live boolean definitions.

They are re-evaluated every control-loop tick using the same sampled signal snapshot used for normal condition evaluation.

Derived signals do not latch automatically unless their definition itself includes operators such as `stable` or references latched statement semantics externally through `require`.

## 10.3 Dependency Rules

Derived signals may depend on:

- primitive signals
- built-in signals such as `timer.elapsed`
- other derived signals

Dependency rules:

- the dependency graph must be acyclic
- self-reference is invalid
- cyclic reference across multiple derived signals is invalid

## 10.4 Visibility

Derived signals are visible only by their test-scoped name.

In this version, a derived signal name must not collide with:

- a declared device name
- `timer`
- another derived signal name

## 10.5 Type

In this version, derived signals are boolean only.

Future versions may add numeric derived signals, but that is intentionally deferred.

## 11. Statement Semantics With Compound Conditions

The existing statement model remains intact.

Only the condition language becomes richer.

### 11.1 `abort`

`abort <condition-expression>`

If the effective expression becomes true, the test fails immediately.

### 11.2 `success`

`success <condition-expression>`

If the effective expression becomes true, the test passes immediately.

### 11.3 `until`

`until <condition-expression>`

Multiple `until` statements remain OR'd at the statement level.

Each individual `until` statement may now contain a compound expression.

### 11.4 `require`

`require <condition-expression>`

Each `require` statement still latches once satisfied.

The expression inside one `require` is evaluated as a boolean whole.

Example:

```text
require motor1.confidenceLevel > 75 and not motor1.faults
```

This latches satisfied only when the entire expression becomes true.

## 12. Normalization Model

Normalized JSON must stop treating a condition as a flat operator triplet only.

The normalized form must support an expression tree.

Minimum normalized node kinds:

- `signal_ref`
- `literal`
- `compare`
- `range`
- `stable`
- `not`
- `and`
- `or`
- `derived_ref`

Minimum derived-signal normalized fields:

- `name`
- `expr`
- optional source text for diagnostics

Example conceptual normalized shape:

```json
{
  "derivedSignals": [
    {
      "name": "ready",
      "expr": {
        "kind": "and",
        "left": {
          "kind": "compare",
          "op": ">",
          "left": { "kind": "signal_ref", "device": "motor1", "signal": "confidenceLevel" },
          "right": { "kind": "literal", "value": 75 }
        },
        "right": {
          "kind": "not",
          "expr": {
            "kind": "signal_ref",
            "device": "motor1",
            "signal": "faults"
          }
        }
      }
    }
  ]
}
```

This JSON is illustrative.

The exact schema may differ, but tree structure is mandatory.

## 13. Validation Rules

Host-side validation must reject:

- unknown derived-signal references
- duplicate derived-signal names
- derived-signal/device-name collisions
- cyclic derived-signal dependencies
- use of non-boolean expressions where a boolean is required
- numeric operators on non-numeric signals
- bare signal references on non-boolean signals
- `stable` durations that are non-positive
- malformed parentheses or operator placement

Validation must preserve the current rule that all referenced primitive device signals resolve through the canonical generated signal metadata.

## 14. Runtime Rules

Runtime behavior must preserve these invariants:

- no authored source ordering inside a phase becomes observable as execution order
- compound conditions do not introduce side effects
- derived signals do not introduce writable ownership
- all hardware-affecting behavior still flows through existing `set` / `clear` semantics
- the runtime remains the sole owner of pass/fail/interrupted outcomes

## 15. Examples

### 15.1 Confidence Gate

```text
test "motor_confidence_check"
device motor1

derived signal ready = motor1.confidenceLevel > 75 and not motor1.faults

main:
    require ready
    until timer.elapsed >= 1.0
```

### 15.2 Stall Suspicion

```text
test "stall_watch"
device motor1

derived signal stallSuspect = (motor1.output > 0.4 and motor1.velocity < 100) stable 0.250

main:
    set motor1.output = 0.5
    abort stallSuspect
    until timer.elapsed >= 2.0
```

### 15.3 Operator Confirmation

```text
test "operator_acknowledged_spin"
device motor1
device controller0

derived signal operatorConfirmed = controller0.A stable 0.100
derived signal healthySpin = motor1.velocity > 200 and motor1.current between 2 30

main:
    set motor1.output = 0.3
    require operatorConfirmed and healthySpin
    abort motor1.current outside 0 40 stable 0.100
    until timer.elapsed >= 2.0
```

## 16. Migration Guidance

Existing tests remain valid with no required change.

Migration principles:

- keep current simple tests simple
- prefer new primitive runtime signals when a shared semantic already exists
- use derived signals to name reusable test-local meanings
- use compound conditions instead of duplicating many nearly-identical `require` statements when the intent is one combined truth

## 17. Implementation Guidance

Recommended implementation order:

1. extend the condition parser to build an expression tree
2. extend normalized JSON and source-hash validation to include tree-shaped conditions
3. extend runtime condition evaluation for `and`, `or`, `not`, and grouped `stable`
4. add test-scoped derived-signal validation and cycle checks
5. add runtime support for derived-signal evaluation from the same per-tick sample snapshot

## 18. Deferred Items

These are intentionally deferred from this version:

- numeric derived signals
- derived signals used as `set` numeric sources
- quantifiers such as `all` / `any`
- group-scoped expressions
- cross-test shared derived-signal libraries and imports
- user-authored weighting or scoring formulas

## 18.1 Future Direction: Derived-Signal Libraries

Reusable libraries of derived signals are a valid future direction for this DSL.

They should be treated as a later declarative extension layered on top of:

- compound conditions
- test-scoped derived signals
- normalized expression-tree conditions

The main purpose of such libraries would be:

- reuse of common health or fault interpretations
- reuse of common device-family semantics
- reduction of repeated test-local derived-signal declarations

Example future shapes:

```text
include "motor_health.dslinc"
```

or:

```text
import "motor_health.dslinc" as motorHealth
```

Potential later usage:

```text
require motorHealth.ready
abort motorHealth.stallSuspect
```

or, if parameterization is later added:

```text
require motorHealth.ready(motor1)
abort motorHealth.stallSuspect(motor1)
```

This spec intentionally does not define library syntax or semantics yet.

When libraries are added later, they should follow these design constraints:

- libraries remain purely declarative
- libraries must not write hardware
- libraries must not add execution-order semantics
- library expansion must be reproducible for normalized JSON generation
- name resolution rules must be explicit
- cycle detection must include cross-file dependencies
- source-hash and validation behavior must remain deterministic
- parameterization, if added, should be explicit rather than implied by textual substitution

Recommended architectural rule for the future:

- prefer import-style semantics over raw textual include semantics

Reason:

- import-style semantics are easier to validate
- import-style semantics reduce accidental name collisions
- import-style semantics fit better with expression-tree normalization
- raw textual include risks making the language feel script-like instead of declarative

## 19. Open Question

One design point should be decided explicitly during implementation:

- whether `stable` may apply only to atomic predicates
- or whether `stable` may apply to any parenthesized boolean subexpression

This spec currently recommends allowing:

```text
(A and B) stable 0.250
```

because it preserves declarative expressiveness without introducing procedure.
