SPEC_STATUS: IMPLEMENTED

# Robot Diagnostic Test DSL Spec v0.3

## 1. Purpose

Purpose: define the current execution semantics of the Robot Diagnostic Test DSL.

This document is the canonical language spec for:

- phase structure
- statement semantics
- condition semantics
- runtime safety behavior
- pass, fail, and interrupted outcomes

This document does not define:

- CLI command syntax
- UI layout
- dashboard rendering
- NetworkTables publication

## 2. Core Model

A DSL test is a live rule set evaluated by the robot runtime.

It is not a procedural script.

The authored structure is:

1. `init`
2. `main`
3. `close`

Only those three phases are sequenced.

Within a phase, source line order does not define execution order.

The engine owns:

- startup safing
- per-tick execution order
- pass and fail decisions
- cleanup and final safing

## 3. Test Structure

Each test contains:

- one `test` declaration
- zero or more `device` declarations
- zero or more test-scope `unsafe-exit` declarations
- optional `init`
- required `main`
- optional `close`

Example:

```text
test "spin_up_motor1"
device "FALCON 9"

main:
    set "FALCON 9".output = 0.2
    until timer.elapsed >= 2.0
    require "FALCON 9".velocity > 100
```

## 4. Device Model

Each authored device must be explicitly declared:

```text
device "FALCON 9"
device "controller0"
```

Signal references always use:

```text
device.signal
```

Examples:

```text
"FALCON 9".output
lmtSw0.pressed
controller0.leftY
timer.elapsed
```

Rules:

- referenced configured devices must exist in the active runtime
- referenced configured devices must be declared in the test before use
- `timer` is built in and must not be declared
- quoted and unquoted device references are equivalent when the unquoted name is lexically valid

## 5. Engine Guarantees

### 5.1 Startup

At test start:

1. declared runtime devices are resolved and created
2. starting positions are captured for delta-style position signals when available
3. writable DSL signals are forced to their declared safe values
4. `init` `clear` statements run
5. `init` `set` statements run
6. `timer.elapsed` starts at `0`
7. `main` begins

### 5.2 Termination

At termination:

1. the result is determined
2. `close` `clear` statements run
3. `close` `set` statements run
4. writable DSL signals are returned to safe values
5. any signal named by `unsafe-exit` is exempt from final safe-state application

### 5.3 Safe Values

Safe values come from DSL signal metadata, not from hardcoded assumptions in authored tests.

A writable DSL signal must provide either:

- a literal safe value
- or a device-owned safe-state provider

## 6. Statements

### 6.1 `set`

Supported forms:

```text
set device.signal = literal
set device.signal = source.signal scaled number default literal
set device.signal = source.signal deadband number scaled number default literal
```

Literal-valued `set` writes the authored literal.

Signal-driven `set` reads a source signal and derives a numeric target write.

Signal-driven `set` rules:

- target must be writable and numeric
- source must be readable and numeric
- `scaled` is required
- `default` is required
- `deadband` is optional
- deadband is applied before scaling
- values with `abs(source) < deadband` resolve to `0.0`
- if the source is unavailable in `init`, startup fails
- if the source is unavailable in `main`, the authored `default` is written
- if the source is unavailable in `close`, the write is skipped
- if fallback is active on the tick that triggers normal `until` termination, the test fails

Phase semantics:

- `init`: write once before live execution
- `main`: write every tick
- `close`: write once during cleanup

### 6.2 `clear`

Syntax:

```text
clear device.signal
```

Rules:

- valid only in `init` and `close`
- target must be marked clearable in DSL signal metadata
- `clear` is a device-owned clear operation
- `clear` is not shorthand for assigning zero

### 6.3 `abort`

Syntax:

```text
abort condition
```

Semantics:

- evaluated every tick in `main`
- if true, the test fails immediately
- result = `FAIL`

`abort` means forbidden condition.

### 6.4 `success`

Syntax:

```text
success condition
```

Semantics:

- evaluated every tick in `main`
- if true, the test passes immediately
- result = `PASS`

`success` means sufficient evidence by itself.

### 6.5 `until`

Syntax:

```text
until condition
```

Semantics:

- evaluated every tick in `main`
- multiple `until` statements are OR'd
- when one becomes true, normal termination begins
- on normal termination:
  - if any signal-set fallback is active that tick, result = `FAIL`
  - else result = `PASS` only if all `require` conditions have latched satisfied
  - else result = `FAIL`

### 6.6 `require`

Syntax:

```text
require condition
```

Semantics:

- evaluated every tick in `main`
- once true, it remains satisfied for the rest of the run
- `require` is latched evidence, not a steady-state assertion
- `require` contributes to result only on normal `until` termination
- `require` does not decide the result of `abort`, `success`, or external stop

Multiple `require` statements are AND'd.

### 6.7 `unsafe-exit`

Syntax:

```text
unsafe-exit device.signal
```

Rules:

- declared at test scope
- not allowed inside phases
- target must be writable
- affects final safing only
- does not bypass startup safing
- does not change `abort`, `success`, `until`, or `require` semantics

## 7. Conditions

Supported forms:

```text
device.signal > literal
device.signal >= literal
device.signal < literal
device.signal <= literal
device.signal == literal
device.signal != literal
device.signal
```

Rules:

- bare `device.signal` is valid only for boolean signals
- bare boolean reference means `device.signal == true`
- bare non-boolean reference is a validation error
- compound expressions are not supported
- arithmetic expressions are not supported
- `and` and `or` are not supported

## 8. Per-Tick Execution Order

During `main`, the engine performs this order every tick:

1. apply all `main` `set` statements
2. sample every signal referenced by conditions
3. update and latch `require`
4. evaluate `abort`
5. evaluate `success`
6. evaluate `until`

Priority is therefore:

```text
abort > success > until
```

Important note:

- `require` latching happens before `abort`, `success`, and `until` evaluation on that same tick

## 9. Results

### 9.1 `PASS`

A test passes when:

- a `success` condition becomes true

or:

- an `until` condition becomes true
- no signal-set fallback is active on that tick
- all `require` conditions have latched satisfied

### 9.2 `FAIL`

A test fails when:

- an `abort` condition becomes true

or:

- an `until` condition becomes true
- and one or more `require` conditions were never satisfied

or:

- an `until` condition becomes true
- and signal-set fallback is active on that tick

or:

- startup, runtime write, or runtime clear behavior fails in a way the engine treats as fatal

### 9.3 `INTERRUPTED`

A test is interrupted when it stops externally, including:

- robot disable
- estop
- manual cancel

In that case:

- `close` still runs
- final safing still runs unless bypassed by `unsafe-exit`
- result = `INTERRUPTED`

## 10. Range and Availability Rules

Writable DSL targets are device-owned and range-checked at runtime.

Important current behaviors:

- signal-driven `set` defaults are validated for target range
- out-of-range values during `init` or `main` fail the test
- out-of-range values during `close` are skipped and reported as warnings
- unsupported runtime writes fail the test
- unsupported runtime clears fail the test

## 11. Built-In Timer

The built-in timer is referenced as:

```text
timer.elapsed
```

Rules:

- `timer` must not be declared as a device
- `timer.elapsed` is measured as seconds since test start
- the timer is readable only

## 12. Current Supported Signal Families

The detailed signal catalog lives in:

- [USER_GUIDE_ROBOT_TEST_DSL.md](./USER_GUIDE_ROBOT_TEST_DSL.md)
- [SPEC_DSL_DEVICE_SIGNAL_INTERFACE.md](./SPEC_DSL_DEVICE_SIGNAL_INTERFACE.md)
- [tools/common/generated/robot_test_dsl_signals.json](../tools/common/generated/robot_test_dsl_signals.json)

Current high-level families include:

- motor signals
- limit switch signals
- external encoder signals
- Xbox controller signals
- built-in timer signals

## 13. Unsupported Features in v0.3

The current language does not support:

- loops
- branches
- stages or multi-step sequencing
- compound boolean expressions
- arithmetic expressions in conditions
- free-form functions

## 14. EBNF

```text
test_file         = { test_def } ;

test_def          = "test" string_lit
                    { device_decl }
                    { unsafe_exit_decl }
                    phase_body ;

device_decl       = "device" string_lit ;
unsafe_exit_decl  = "unsafe-exit" reference ;

phase_body        = [ init_block ] main_block [ close_block ] ;

init_block        = "init" ":" { init_stmt } ;
main_block        = "main" ":" { main_stmt } ;
close_block       = "close" ":" { close_stmt } ;

init_stmt         = set_stmt | clear_stmt ;
main_stmt         = set_stmt | abort_stmt | until_stmt | success_stmt | require_stmt ;
close_stmt        = set_stmt | clear_stmt ;

set_stmt          = "set" reference "=" set_rhs ;
set_rhs           = literal
                  | reference [ deadband_clause ] scaled_clause default_clause ;
deadband_clause   = "deadband" number ;
scaled_clause     = "scaled" number ;
default_clause    = "default" literal ;

clear_stmt        = "clear" reference ;

abort_stmt        = "abort" condition ;
until_stmt        = "until" condition ;
success_stmt      = "success" condition ;
require_stmt      = "require" condition ;

condition         = reference comparison_op literal
                  | reference ;

reference         = device_name "." signal_name ;

comparison_op     = "==" | "!=" | "<" | "<=" | ">" | ">=" ;

literal           = number | string_lit | "true" | "false" ;

device_name       = identifier | string_lit ;
signal_name       = identifier ;

identifier        = letter { letter | digit | "_" | "-" } ;
number            = [ "-" ] digit { digit } [ "." digit { digit } ] ;
string_lit        = "\"" { character } "\"" ;

character         = ? any character except quote and newline ? ;
letter            = "A".."Z" | "a".."z" ;
digit             = "0".."9" ;
```

## 15. Validation Summary

Typical validation errors include:

- missing `main`
- duplicate `init`, `main`, or `close`
- phases out of order
- undeclared device reference
- unknown device
- unknown signal
- bare non-boolean condition
- invalid clear target
- `set` to read-only signal
- invalid `unsafe-exit` target
- declaring built-in `timer`
- missing required `scaled` or `default` in signal-driven `set`
- invalid deadband or scale ranges
- motor-device source signal in signal-driven `set`

Typical warnings include:

- no `until` and no `success`
- `until` without `require`
- only `abort`-based termination
- use of `unsafe-exit`

## 16. Mental Model

Use this model when reading or authoring tests:

```text
init    = one-time setup
main    = live rules
close   = one-time cleanup

abort   = forbidden condition -> fail now
success = sufficient proof -> pass now
until   = normal stop boundary
require = evidence that must have happened
```

And remember:

- `require` means at least once before normal stop
- `main set` means continuous ownership
- source line order inside a phase does not define tick order
