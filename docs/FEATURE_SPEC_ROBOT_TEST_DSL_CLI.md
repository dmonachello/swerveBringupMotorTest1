SPEC_STATUS: IMPLEMENTED

# Robot Test DSL CLI Spec

## 1. Purpose

Purpose: Define the CLI command surface for source-based Robot Diagnostic Test DSL workflows.

This spec covers host-side CLI behavior for:

- importing DSL source files
- exporting DSL source files
- validating stored DSL tests
- showing DSL source and normalized JSON
- managing named DSL test sets
- selecting and running saved tests

This spec does not redefine runtime execution semantics. Runtime behavior is defined by:

- [ROBOT_DIAGNOSTIC_TEST_DSL_SPEC_V0_3.md](./ROBOT_DIAGNOSTIC_TEST_DSL_SPEC_V0_3.md)

## 2. Core Rules

The CLI uses these rules:

- DSL source text is the editable source of truth.
- Normalized JSON is a generated artifact stored alongside source.
- Host-side CLI compiles and validates source before saving.
- Robot-side execution uses normalized JSON only.
- If source and normalized JSON are out of sync, validation fails.
- Old local test authoring commands are removed.

## 3. Storage Model

DSL tests are stored in `bringup_system.json` under a top-level section:

```text
dslTests
```

Expected structure:

- `testsByName`
- `testSets`
- `defaultSet`

Profiles reference the active DSL test set with:

```text
profiles.<profile>.dslTestSet
```

## 4. Modes

### 4.1 Config Mode

These commands run in `configure terminal` mode:

- `test import`
- `test export`
- `test validate`
- `test delete`
- `test set ...`

### 4.2 Exec Mode

These commands are allowed in exec mode:

- `show test ...`
- `show tests`
- `show test sets`
- `tests select ...`
- `tests run`
- `tests run-all`

## 5. Command Set

## 5.1 Import

```text
test import <name> <path> [set <set_name>]
```

Meaning:

- read DSL source from file
- compile source to normalized JSON
- validate against current profile devices and generated signal metadata
- store source and normalized JSON into `bringup_system.json`
- add the test to the named set

Rules:

- `<name>` is the stable test key
- `<path>` is a source file path
- if `set` is omitted, use the profile default set or `default`
- imported source becomes authoritative

Example:

```text
test import spin_up_motor1 temp_test.dsl set default
```

## 5.2 Export

```text
test export <name> <path>
```

Meaning:

- write stored DSL source text to file

Rules:

- export writes source only, not normalized JSON

Example:

```text
test export spin_up_motor1 out\spin_up_motor1.dsl
```

## 5.3 Validate

```text
test validate
test validate <name>
```

Meaning:

- validate all stored DSL tests, or one named test

Validation checks:

- source parses
- normalized payload exists
- source and normalized payload match
- source hash matches
- declared devices exist in the active profile
- referenced signals exist in generated signal metadata
- writable, clearable, and safe-state rules are satisfied
- named test-set references resolve

Output:

- text summary by default
- JSON when `--json --pretty` is supported by the CLI surface

## 5.4 Delete

```text
test delete <name>
```

Meaning:

- remove the named test from `testsByName`
- remove the name from all test sets

Rules:

- deleting a missing test is an error

## 5.5 Test Set Management

Create a set:

```text
test set create <set_name>
```

Delete a set:

```text
test set delete <set_name>
```

Add a test to a set:

```text
test set add <set_name> <test_name>
```

Remove a test from a set:

```text
test set remove <set_name> <test_name>
```

Set the default set:

```text
test set default <set_name>
```

Rules:

- set names are stable string keys
- a set contains ordered test names
- deleting a set referenced by a profile is an error unless the profile is updated in the same operation
- deleting the default set is an error unless a replacement default is chosen in the same operation

## 6. Show Commands

## 6.1 Show Source

```text
show test <name>
```

Meaning:

- print stored DSL source text

This command must not render legacy test fields such as:

- `type: composite`
- `duty`
- `termination`
- `inputSource`

## 6.2 Show Normalized

```text
show test <name> normalized
show test <name> normalized --json --pretty
```

Meaning:

- display compiled normalized JSON for the named test

## 6.3 Show All Tests

```text
show tests
show tests --json --pretty
```

Output should include:

- test name
- set membership
- source-present state
- normalized-present state
- validation state

## 6.4 Show Test Sets

```text
show test sets
show test sets --json --pretty
```

Output should include:

- all set names
- default set
- test membership per set
- current profile-selected set

## 7. Run Commands

These commands operate on saved normalized DSL tests.

Select a test:

```text
tests select <name>
```

Run selected test:

```text
tests run
```

Run all tests in the active set:

```text
tests run-all
```

Optional direct form:

```text
test run <name>
```

Rules:

- robot execution uses normalized JSON only
- run commands do not compile source on demand
- tests with validation errors must not run

## 8. Status and Output Rules

Text output should be concise and operator-readable.

Machine-readable output must remain stable.

JSON show/run output should include:

- run state
- result
- status
- message
- details

For DSL runs, `details` should include when available:

- condition ids
- condition text
- latched require satisfaction
- require satisfaction timestamps
- sampled values
- unsafe-exit declarations

## 9. Error Rules

Errors:

- missing test
- missing set
- unknown profile
- source compile failure
- validation failure
- source/normalized mismatch
- profile references unknown set
- test set references unknown test

Warnings:

- no `until` or `success`
- `until` without `require`
- `unsafe-exit` present

## 10. Removed Commands

The following old local authoring patterns are removed:

- historical: `test create ...` (removed)
- `type composite`
- `device add ...` in test edit mode
- `command ...`
- `until ...`
- `expect ...`
- `success ...`
- `abort ...`
- `manual_stop ...`
- `passive ...`

Reason:

- source text is the authority
- CLI is not the source editor
- file-based import/export is the supported authoring workflow

## 11. Examples

Import and validate:

```text
configure terminal
profile dsl_demo_050426
test import spin_up_motor1 temp_test.dsl set default
test validate spin_up_motor1
end
```

Show source:

```text
show test spin_up_motor1
```

Show normalized JSON:

```text
show test spin_up_motor1 normalized --json --pretty
```

Run:

```text
tests select spin_up_motor1
tests run
```

## 12. Out of Scope

Out of scope for this CLI spec:

- visual DSL editing
- source text mutation inside the CLI
- runtime execution semantics
- dashboard layout behavior

## 13. Future Extensions

Possible future additions:

- `show test <name> source --json`
- `test compile <name>` as an explicit regeneration command
- editor integration helpers
- diff between source and normalized payload

## 14. Summary

This CLI model is file-based and source-authoritative.

The CLI is responsible for:

- import
- export
- compile
- validate
- inspect
- run saved tests

The robot is responsible for:

- executing normalized DSL tests
- applying runtime safety rules
- reporting run outcomes and details

