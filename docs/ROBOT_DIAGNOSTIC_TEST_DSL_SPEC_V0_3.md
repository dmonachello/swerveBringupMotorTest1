# Robot Diagnostic Test DSL Spec v0.3

## 1. Purpose

This DSL defines robot bring-up and diagnostic tests.

This specification defines **execution semantics only**.

Out of scope:

- test enable/disable
- grouping and catalogs
- orchestration / scheduling
- UI concerns

Core model:

A test defines live rules evaluated every control-loop tick.

This spec also defines startup and shutdown safety behavior, including explicit opt-out for retained outputs at test exit.

## 2. Execution Model

A test has three phases:

- `init` -> runs once before execution
- `main` -> runs every tick (required)
- `close` -> runs once after termination

There are no loops, branching, or sequencing constructs.

In addition, a test may declare exit-retention exceptions:

```text
unsafe-exit device.signal
```

## 3. Device Model

Each test must declare devices it uses.

```text
device "<name>"
```

Rules:

- must bind to existing configured device
- unknown device = validation error
- devices must be declared before use
- `timer` is built-in and must not be declared

All references are explicit:

```text
device.signal
```

## 4. Engine Guarantees

At start of `main`:

1. all writable outputs are set to device-defined safe value
2. `init` runs, if present
3. `timer.elapsed = 0`
4. `main` begins

At termination:

1. termination result is determined
2. `close` runs, if present
3. all writable outputs are returned to device-defined safe value by default
4. signals declared with `unsafe-exit` are exempt from final safe-state application

Safe values are defined by device metadata, not assumed to be `0`.

A device with writable command outputs must provide safe-state metadata or a safe-state provider.

## 5. Statements

### `set`

```text
set device.signal = value
set device.signal = source.signal scaled number default value
set device.signal = source.signal deadband number scaled number default value
```

Semantics:

Literal-valued `set` writes the authored literal value.

Signal-driven `set` reads a source signal and writes a derived target value.

For signal-driven `set`:

- `scaled` is required
- `default` is required
- `deadband` is optional
- if `deadband` is present, values with `abs(source) < deadband` resolve to `0.0`
- deadband is applied before scaling
- if the source is unavailable in `init`, startup fails
- if the source is unavailable in `main`, the authored default value is used
- if the source is unavailable in `close`, that write is skipped

In `init`:

- applied once before execution begins

In `main`:

- applied every tick
- establishes continuous ownership of the written signal during the test

In `close`:

- applied once after termination

### `abort`

```text
abort condition
```

- evaluated every tick
- if true -> immediate termination
- result = `FAIL`

`abort` means forbidden condition.

### `success`

```text
success condition
```

- evaluated every tick
- if true -> immediate termination
- result = `PASS`

`success` means sufficient evidence.

### `until`

```text
until condition
```

- evaluated every tick
- if true -> normal termination

Multiple `until` statements are OR'd.

### `require`

```text
require condition
```

`require` is a latched evidence condition.

- evaluated every tick during `main`
- once true, it remains satisfied for the rest of the test
- checked only on normal termination via `until`

At `until` termination:

- `PASS` if all `require` conditions are satisfied
- `FAIL` otherwise

`require` means required evidence.

Multiple `require` statements are AND'd.

`require` is not evaluated for result determination on `abort`, `success`, or external stop.

### `clear`

```text
clear device.signal
```

Rules:

- allowed only in `init` and `close`
- signal must be marked clearable in metadata
- otherwise = validation error

`clear` is a capability-specific operation, not shorthand for assigning zero.

### `unsafe-exit`

```text
unsafe-exit device.signal
```

Rules:

- declared at test scope
- not allowed inside `init`, `main`, or `close`
- target must be a writable signal
- after `close`, the engine skips final safe-state application for that signal
- affects exit behavior only
- does not change startup safing
- does not change `abort`, `success`, `until`, or `require` semantics

## 6. Conditions (v1)

Simple only:

```text
device.signal op value
device.signal
```

Operators:

```text
> >= < <= == !=
```

Rules:

- bare `device.signal` is allowed only for boolean-valued signals
- a bare boolean reference means `device.signal == true`
- non-boolean bare references are validation errors

No compound expressions.

Units are inferred from signal metadata.

## 7. Tick Execution Order

Per tick:

1. command preparation -> resolve source values needed by signal-driven `set`
2. command -> apply `main` `set` statements
3. sample -> read signals for conditions
4. evaluate -> `abort`, `success`, `until`, `require`

Priority:

```text
abort > success > until
```

Flow:

- if `abort` -> `FAIL`
- else if `success` -> `PASS`
- else if `until` -> evaluate `require`
- else continue

## 8. Termination Modes

A test may terminate via:

- `abort`
- `success`
- `until`
- external stop

External stop includes:

- disable
- estop
- manual cancel

Result:

- `INTERRUPTED`

## 9. `require` vs `abort`

`abort` means forbidden condition.

`require` means required evidence.

They are not opposites.

## 10. Close Phase

If present, the engine executes `close` after termination.

Rules:

- `close` is executed regardless of termination reason
- failures in `close` do not affect `PASS` / `FAIL` / `INTERRUPTED`
- `close` is cleanup only
- after `close`, the engine applies final safe-state by default
- signals declared with `unsafe-exit` are not forced to safe-state at final exit

## 11. Forever Tests

Valid:

```text
main:
    set motor.output = 0.5
    abort motor.current > 40
```

Behavior:

- runs indefinitely
- stopped externally
- result = `INTERRUPTED`

## 12. EBNF

```text
test_file       = { test_def } ;

test_def        = "test" string_lit { device_decl } { unsafe_exit_decl } phase_body ;

device_decl     = "device" string_lit ;
unsafe_exit_decl = "unsafe-exit" reference ;

phase_body      = [ init_block ] main_block [ close_block ] ;

init_block      = "init" ":" { init_stmt } ;
main_block      = "main" ":" { main_stmt } ;
close_block     = "close" ":" { close_stmt } ;

init_stmt       = set_stmt | clear_stmt ;
main_stmt       = set_stmt | abort_stmt | until_stmt | success_stmt | require_stmt ;
close_stmt      = set_stmt | clear_stmt ;

set_stmt        = "set" reference "=" literal ;
clear_stmt      = "clear" reference ;

abort_stmt      = "abort" condition ;
until_stmt      = "until" condition ;
success_stmt    = "success" condition ;
require_stmt    = "require" condition ;

condition       = reference comparison_op literal
                | reference ;

reference       = device_name "." signal_name ;

comparison_op   = "==" | "!=" | "<" | "<=" | ">" | ">=" ;

literal         = number | string_lit | "true" | "false" ;

device_name     = identifier | string_lit ;
signal_name     = identifier ;

identifier      = letter { letter | digit | "_" | "-" } ;
number          = [ "-" ] digit { digit } [ "." digit { digit } ] ;
string_lit      = "\"" { character } "\"" ;

character       = ? any character except quote and newline ? ;
letter          = "A".."Z" | "a".."z" ;
digit           = "0".."9" ;

```

## 13. Validation

Errors:

- missing `main`
- duplicate `init`
- duplicate `main`
- duplicate `close`
- phases out of order
- undeclared device
- unknown signal
- invalid clear target
- `set` to read-only signal
- invalid `unsafe-exit` target
- `unsafe-exit` outside test scope
- `require` / `abort` / `success` / `until` outside `main`
- bare non-boolean condition reference
- declaring reserved built-in device `timer`
- writable signal has no safe value
- controlled device has no safe-state provider

Warnings:

- no `until` or `success` -> runs forever
- only `abort` termination -> may never stop
- `until` without `require` -> may pass without proof
- `unsafe-exit` bypasses default final safing

## 14. Mental Model

```text
init    = setup
main    = live rules
close   = cleanup

abort   = bad -> fail immediately
success = good enough -> pass immediately
until   = stop boundary
require = evidence that must occur

external stop = INTERRUPTED
```

## 15. Summary

The DSL expresses intent only.

The engine owns:

- timing
- safety
- lifecycle
- execution order
