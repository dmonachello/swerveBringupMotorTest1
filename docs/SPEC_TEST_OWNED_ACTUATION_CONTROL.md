# Test-Owned Actuation Control (CLI/UI/Xbox)

Purpose:

Define a single control contract where any actuator action (motors now, non-motor actuators later) occurs only during an explicit test run, regardless of whether commands originate from CLI, UI, or direct Xbox controller bindings on the robot.

## Group and Targeting V1 Update (April 20, 2026)

Purpose:

Add finalized group/targeting test constraints that affect test-owned actuation workflows.

- Name resolution is exact and case-insensitive.
- Device/group names share one global namespace.
- `active` is reserved, always present, non-persistent, and reset on save/commit.
- Group membership is set-based (duplicate add warn/no-op, missing remove warn/no-op).
- `group delete active` must fail.
- Device/group delete operations must fail when references exist in tests/groups.
- Non-interactive copy into existing named group must fail with no mutation.

## Goal

Purpose:

Lock actuation control to test execution while preserving familiar operator workflows and controller bindings.

- `add all` and `add next` remain instantiate-only commands.
- Actuator output commands are valid only while a test is actively running.
- Outside active tests, robot code does not continuously command actuator outputs.
- Existing controller-driven workflows are preserved by migrating manual output actions into always-available tests.

## Non-Goals

Purpose:

Clarify what this change does not attempt to solve.

- No new operator arming/latch UX is introduced.
- No change to Python CAN passive/read-only rule.
- No change to existing CAN diagnostics/report contracts.
- No required NetworkTables contract change for this phase.

## Problem Statement

Purpose:

Capture why current behavior can be surprising and unsafe.

- Today, `add all` can be followed by unexpected movement because non-test periodic output paths can become effective as soon as devices are instantiated.
- This violates the desired operator mental model: "nothing moves until `run test ...`."
- The behavior can occur from any command origin (CLI, UI, Xbox), which makes consistency and safety harder to reason about.

## Control Contract (Normative)

Purpose:

Define the required behavior in implementation-neutral terms.

- Motion authority is test-owned.
- A command path may instantiate devices while idle, but may not apply non-zero duty unless a test is running.
- On transition from running to idle, actuator outputs are stopped/deactivated once, then remain untouched unless another test starts.
- CLI, UI, and Xbox entry points must converge on the same runtime rule.

## Runtime State Model

Purpose:

Specify minimal states needed to enforce deterministic behavior.

- `IDLE`:
  - No active test.
  - No periodic actuator write loop.
  - Device instantiation allowed.
- `TEST_RUNNING`:
  - One active test owns actuator outputs.
  - Test-defined control (timed, button-held, joystick-driven) is allowed.
- `STOPPING` (internal transition):
  - One-time stop-all on exit from `TEST_RUNNING`.
  - Immediately returns to `IDLE`.

## Command Semantics

Purpose:

Lock command meaning so behavior is predictable across interfaces.

- `add all`, `add next`:
  - Instantiates configured devices only.
  - Must not start motion.
- `run test <name>`:
  - Enters `TEST_RUNNING` for selected test.
  - Uses per-test `targetMode`.
  - Default `targetMode` is `test-defined`, where the test's own device list is authoritative.
  - `targetMode=active-group` remains a design option and is not the standard operator flow in current docs.
- `run all tests`:
  - Runs tests sequentially under test-owned control.
- `stop`/test end/abort:
  - Performs one-time stop/deactivate and returns to `IDLE`.

## Active Group Workflow (Normative)

Purpose:

Define deterministic active-group device progression while keeping actuation test-owned.

- The system maintains one explicit `active group` whose contents are operator-visible.
- The active group is a named group `active-group` that is always defined.
- Membership changes are command-driven only and must not imply motion.
- Motion still requires explicit `run test ...`.
- Active-group membership changes are runtime-only and are not persisted to config/profile files.

### Active Group Commands

Purpose:

Specify additive command behaviors for group progression.

- `active add` (grow mode):
  - Adds the next device to the active group.
  - Existing members remain in the group.
  - Duplicate members are not allowed.
- `active next` (rotate mode):
  - Deactivates/stops the current primary device.
  - Removes the current primary device from the active group.
  - Adds the next device as the new primary member.
  - Must not start motion by itself.
- Runtime-state constraint:
  - `active add` and `active next` are rejected while `TEST_RUNNING`.
- End-of-list behavior:
  - The next-device cursor wraps to the first device.
  - The command response must include a warning that wrap occurred.

### Active Group Visibility

Purpose:

Ensure operators can explicitly inspect effective group state.

- `active show` returns human-readable active-group contents.
- `active show --json` returns structured active-group contents for tooling.
- Any command that mutates active-group membership must return updated contents in the response.
- Wrap warnings are explicit and consistent: `WARNING: device list wrapped to first entry.`

### Active Group Eligibility and Warnings

Purpose:

Define how candidate devices are filtered and how warning conditions are reported.

- `active add` and `active next` include only devices that are totally ready.
- Devices that are not totally ready are skipped and listed by device name in warning output.
- Duplicate add attempts result in warning + no-op.
- Warnings/status are emitted in all output channels (text, JSON payload fields, and status code/message).
- Required warning conditions:
  - No eligible next device is found for `active add`.
  - No eligible next device is found for `active next`.
  - Candidate devices are skipped as not totally ready.
  - Duplicate add attempt.
  - End-of-list wrap occurred.
  - Command rejected because system is in `TEST_RUNNING`.

## Future Device Classes (Normative)

Purpose:

Ensure this ownership model applies to future non-motor tests.

- This contract is actuator-generic and not limited to motors.
- Any future non-motor test that can change hardware state (for example pneumatics, LEDs, servos, relays, or other active outputs) must use the same test-owned control rule.
- Such actions must not run from idle/periodic non-test paths.
- If a device class supports explicit deactivation, idle transition must invoke that deactivation once.
- For rotating tests, if a rotate limit is reached by a device, the test terminates and reports which device hit the limit.

## Migration: Existing Manual Motor Paths

Purpose:

Preserve user workflows while enforcing the new ownership model.

Current non-test output behaviors that directly command motors (for example joystick/fixed-speed/group binding output) must be migrated to always-available test definitions.

### Migration Rules

Purpose:

Define how each existing behavior is preserved without violating the new contract.

- Keep the same Xbox control surfaces (same buttons/axes from operator perspective).
- Replace direct output actions with equivalent test invocations.
- Ensure those tests are always present in active profile/runtime tests table.
- During active test, axis/button reads continue exactly as before for driver feel consistency.

### Example Mapping Matrix

Purpose:

Show representative migration intent; final names may vary by team preference.

- `left stick direct drive` -> `test manual_left_stick_drive`
- `right stick direct drive` -> `test manual_right_stick_drive`
- `fixed speed 25%` -> `test fixed_speed_25`
- `fixed speed 50%` -> `test fixed_speed_50`
- `fixed speed 75%` -> `test fixed_speed_75`
- `fixed speed 100%` -> `test fixed_speed_100`

Legacy "manual jog" behavior is test-only with no exceptions; no actuator-output path is allowed outside active tests.

## Implementation Scope

Purpose:

Describe expected code-touch areas without prescribing line-level patches.

- Centralize output authority checks in robot runtime core.
- Gate/retire non-test periodic actuator output writes while `IDLE`.
- Keep add/instantiate commands functional and motion-free.
- Ensure UI/CLI/controller all call into the same ownership-enforced runtime path.
- Keep behavior additive where possible and avoid broad unrelated refactors.

## Backward Compatibility

Purpose:

Define compatibility expectations during migration.

- Controller bindings remain recognizable from operator perspective.
- Command vocabulary remains stable (`add all`, `run test`, etc.).
- If a legacy path would have changed actuator state outside tests, it now no-ops with explicit status feedback: `Actuation blocked: no active test.`

## Safety and Failure Behavior

Purpose:

Ensure deterministic and safe outcomes under faults and transitions.

- Test failure/exception must trigger one-time stop/deactivate and return to `IDLE`.
- Profile activate/reload during running test must stop outputs before transition.
- Driver Station disable results in safe stop behavior independent of command source.
- On Driver Station disable->enable transition, tests do not auto-resume; an explicit `run test` command is required.

## Verification Plan

Purpose:

Define acceptance checks to confirm contract compliance.

- With non-zero stick input, run `add all`: motors do not move.
- Run `run test <name>`: only test-intended motors move.
- End/abort test: outputs stop once; no further idle writes.
- Repeat scenarios from CLI, UI, and Xbox-triggered commands.
- Confirm non-motion commands (reports, show, profile info) remain functional.

## Acceptance Criteria

Purpose:

Provide go/no-go requirements for completion.

- No actuator action occurs without an active test.
- `add all` never causes actuator movement/state change by itself.
- Existing operator workflows remain available via always-available tests.
- Behavior is consistent across CLI, UI, and direct robot controller operation.

## Tradeoffs

Purpose:

Call out expected costs and benefits of this design.

- Benefit: deterministic safety contract and reduced surprise motion.
- Benefit: one mental model across all control entry points.
- Cost: ad-hoc free-drive outside tests is removed unless explicitly modeled as a test.
- Cost: requires migration/maintenance of manual-drive test definitions.

## Future Extensions

Purpose:

Identify optional follow-on work once baseline contract is implemented.

- Add structured telemetry for blocked motion requests (count/reason/source).
- Add explicit "manual mode test" templates auto-generated per profile.
- Add test priority/ownership metadata for clearer arbitration diagnostics.
- Add regression test scripts that validate the no-actuation-without-test invariant.
