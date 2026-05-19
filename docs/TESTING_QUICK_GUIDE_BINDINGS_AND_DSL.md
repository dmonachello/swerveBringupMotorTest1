# Testing Quick Guide: Bindings and DSL

## Purpose

Provide a short operator/developer guide for choosing the right testing layer when working on bringup controls, bindings, and authored tests.

## Three Levels

This repo currently has three practical testing layers:

1. Group `bind` commands
2. `bindings binding ...` commands
3. DSL tests

They are not interchangeable. Each one serves a different purpose and different level of rigor.

## Level 1: Group `bind`

### Purpose

Use group `bind` for the fastest ad hoc control test.

This is the quickest way to answer questions like:

- Does this input move the intended group?
- Is the direction/sign correct?
- Does a hold/toggle/jog behavior feel right?
- Does the active profile/group wiring behave as expected right now?

### Typical Use

Enter group config mode and attach one input directly to the current group:

```text
configure terminal
group intake
add device "FALCON 9"
bind controller0.leftY analog
show binding
```

### Good Fit

- Quick bringup checks
- One-off debugging
- Live operator feel checks
- Verifying group membership plus runtime response

### Not a Good Fit

- Persistent controller scheme design
- Larger controller mapping maintenance
- Structured, repeatable test definitions

## Level 2: `bindings binding ...`

### Purpose

Use `bindings binding ...` when you want to manage global controller-command mappings in the unified config instead of a one-off group-local runtime bind.

This layer is useful for questions like:

- Is the controller-device mapping defined correctly?
- Do the controller device labels and inputs validate?
- Does the binding set look correct before save/deploy?

### Typical Use

```text
configure terminal
device driver
set interface USB
set type xboxController
set port 0
end
bindings binding add runTest driver button A hold
bindings show bindings
bindings validate
```

### Good Fit

- Editing controller-command mapping data
- Validating bindings files
- Maintaining reusable input configuration tied to controller devices
- Checking controller labels and input vocabulary

### Not a Good Fit

- Detailed motor/test pass criteria
- Multi-step test behavior
- Rich device/assertion logic

## Level 3: DSL Tests

### Purpose

Use DSL tests for comprehensive, repeatable, reviewable test behavior.

This layer is for questions like:

- Can this test be compiled and validated against the active profile?
- Does the test declare the right devices and signals?
- Does the test define actual stop/pass/fail behavior?
- Can this behavior be preserved as a regression surface?

### Typical Use

```text
configure terminal
test set default
test create spin_up_motor1
test spin_up_motor1
```

Example DSL source:

```text
test "spin_up_motor1"
device "FALCON 9"
device "controller0"

main:
    set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0
    until timer.elapsed >= 3.0
    require "FALCON 9".velocity > 1000
```

### Good Fit

- Repeatable bringup tests
- Structured pass/fail logic
- Validation against device and signal catalogs
- Regression-friendly test definitions

### Not a Good Fit

- Fast “just see if this input moves the motor” checks
- Tiny one-off experiments where authored test structure would slow you down

## How To Choose

### If You Need Speed

Use group `bind`.

This is the fastest path for immediate runtime checks.

### If You Need Config Confidence

Use `bindings binding ...`.

This is the right layer for global controller-command mapping data and validation.

### If You Need Repeatability

Use DSL tests.

This is the right layer when the behavior should be saved, reviewed, rerun, and validated with explicit structure.

## Recommended Workflow

### Purpose

Move from quick experimentation to durable coverage without overbuilding too early.

Recommended sequence:

1. Start with group `bind` to confirm the basic device/input behavior.
2. Move to `bindings binding ...` if the controller mapping should become maintained config.
3. Promote the behavior to a DSL test when it needs explicit stop conditions, expectations, and repeatable regression value.

## Regression Relationship

### Purpose

Clarify how these layers connect to the maintained regression surface.

- Group/targeting behavior is covered by local regression scripts such as `bridge_cli_v1_group_targeting_regression.py`.
- DSL behavior is covered by the DSL compiler/validator/unit test surface and by the unified regression runner suites.
- The unified runner is the maintained entrypoint when you want repo-level regression checks:

```text
python tools/can_nt/scripts/run_regressions.py --suite local
```

## Rule of Thumb

Use:

- `bind` for immediate runtime experiments
- `bindings binding ...` for maintained controller mapping config
- DSL for real test cases

If a check needs a real success condition, stop condition, or long-term regression value, it probably belongs in the DSL layer rather than staying as a binding-only workflow.
