# Workflow 01: New Robot Bring-up

Purpose: define the primary end-to-end workflow for bringing up a brand new robot by adding and verifying one hardware component at a time.

## Goal

Start from a minimal or incomplete robot configuration and build confidence incrementally:
- add one component
- validate config and tests
- sync deploy files
- deploy or apply runtime config
- run a focused bring-up test
- verify expected behavior
- capture evidence when needed
- repeat for the next component

This is the first-class workflow for a new robot because it reduces ambiguity and isolates wiring, ID, and hardware problems early.

## When To Use This Workflow

Use this workflow when:
- building a brand new robot
- replacing or re-wiring major hardware
- migrating to a new profile/config
- re-verifying a subsystem after repairs
- validating that each device behaves correctly before tuning or full-system integration

Do not start with full-system tests if you have not yet verified the basic hardware path one component at a time.

## Core Rules

Purpose: keep the workflow safe, repeatable, and easy to debug.

- Canonical config lives in `data/bringup_system.json`.
- Deploy copy lives in `src/main/deploy/bringup_system.json`.
- Run the validate+sync gate after edits:
  - `python -m tools.validate_sync`
- Profiles reference devices by label only.
- The devices table owns CAN identity fields.
- One system config file can contain multiple profiles.
- The system config file defines the shared device inventory once.
- Each profile selects the subset of device labels it uses.
- Host context and robot context are different:
  - host context = what you are editing locally
  - robot context = what the roboRIO is actively using
- Prefer one small test for one component over one big test for many components.
- Do not move on to the next component until the current one is understood.

## Supported Surfaces In This Workflow

Purpose: show the normal tools used in order.

Primary tools:
- Topology editor: create/edit devices and profile membership
- Validate+sync gate: `python -m tools.validate_sync`
- Robot deploy: normal GradleRIO deploy
- Bringup Control UI or Bridge CLI: run reports and tests
- PC CAN bridge (optional but recommended): passive CAN visibility and evidence capture

Recommended command surfaces:
- Config authoring: topology editor first
- Validation/sync: command line
- Runtime bring-up actions: Bringup Control UI or Bridge CLI
- Passive CAN observation: `python -m tools.can_nt.can_nt_bridge ...`

## Workflow Service Mapping

Purpose: map the documented workflow to shared application-service ownership in host-side code.

- Workflow sequencing service: `tools/common/workflows/workflow01_service.py`
- Config lifecycle service: `tools/common/config_lifecycle/service.py`
- Shared test-domain semantics: `tools/common/tests_domain/semantics.py`
- Shared diagnostics normalization: `tools/common/diagnostics/normalize.py`

Implementation rule:

- operator surfaces should consume these shared services instead of re-owning workflow/config/test/diagnostics semantics inline

## Standard Loop

Purpose: describe the repeated one-component-at-a-time bring-up loop.

```text
add one component
-> create or update matching test(s)
-> validate + sync
-> deploy robot code or apply config
-> run focused report(s)
-> run focused test(s)
-> verify expected behavior
-> capture evidence if needed
-> fix/retry or mark good
-> continue to next component
```

## Prerequisites

Purpose: make the expected setup explicit before touching hardware.

Before starting:
- Robot project builds with the supported WPILib toolchain.
- RoboRIO is reachable and deployable.
- Xbox/controller input is available if your bring-up path uses local controls.
- If using passive CAN diagnostics, CANable is connected and visible on Windows.
- Python dependencies are installed for the PC tool.
- The intended robot profile name is chosen.

Recommended pre-checks:
- Run config validation once before editing:
  - `python -m tools.validate_sync`
- Confirm the PC tool can start:
  - `python -m tools.can_nt.can_nt_bridge --version`
- If using CANable, list ports:
  - `python -m tools.can_nt.can_nt_bridge --list-ports`

## Step 1: Start From A Minimal Profile

Purpose: create the smallest useful starting point.

Preferred path:
- Open the topology editor.
- Load or create the intended profile in `data/bringup_system.json`.
- Start with only the devices you are actually ready to verify.
- Keep labels unique and descriptive.

Good label examples:
- `FL DRIVE`
- `FL TURN`
- `FL CANCODER`
- `PDH`
- `PIGEON`

At this stage, avoid adding many unverified devices at once unless they are purely placeholders and clearly marked.

## Step 2: Add One Component

Purpose: define one physical device in the config before testing it.

For each component:
- Add or update the device entry in the devices table.
- Add the device label to the active profile.
- Add optional metadata that helps bring-up:
  - model
  - tags
  - notes
  - limits
  - attachments
- Confirm CAN identity fields are correct for CAN devices:
  - manufacturer
  - deviceType
  - id

Examples of good incremental additions:
- one drive motor
- one turning motor
- one encoder
- one power distribution device
- one gyro

Do not add a whole subsystem unless you are intentionally ready to diagnose multiple interacting devices.

## Step 3: Create Focused Bring-up Tests

Purpose: create the smallest test set that proves the new component behaves correctly.

Tests should be:
- data-driven
- safe by default
- small in scope
- easy to interpret

Preferred patterns:
- one test for one new component
- one smoke test before any more aggressive test
- one clear expected behavior per test

Examples:
- motor low-duty forward spin
- motor low-duty reverse spin
- encoder movement verification
- limit switch verification
- joystick-to-device sanity test

Test sources:
- `bringup_system.json` under `bridgeConfig.byProfile.<profile>.tests`
- test authoring tools/workflows documented elsewhere in the repo

If using the generator path, keep generated tests simple first, then refine only after the component is known-good.

## Step 4: Validate And Sync Every Time

Purpose: catch mistakes before they turn into runtime confusion.

After each config/test update, run:

```cmd
python -m tools.validate_sync
```

Expected outcomes:
- canonical config validates
- semantic references validate
- `data_version` and `data_hash` are correct
- deploy copy is written to `src/main/deploy/bringup_system.json`

Do not skip this step.

Typical failures to fix here:
- duplicate labels
- duplicate IDs
- missing fields
- unknown test device references
- bad interface-specific fields
- profile references to missing devices

## Step 5: Deploy Robot Code

Purpose: put the validated config and current robot harness on the roboRIO.

Use the normal WPILib deployment flow.

At minimum, confirm:
- robot code deploys cleanly
- deploy files are present on the roboRIO
- the intended profile is available
- the robot comes up without obvious startup errors

If using runtime apply/push features, be explicit about whether the change is:
- local only
- runtime only
- persisted to disk

For first bring-up on a brand new robot, a normal deploy is usually the clearest path.

## Step 6: Start Passive CAN Observation (Recommended)

Purpose: gain an independent view of device presence and traffic.

Recommended command shape:

```cmd
python -m tools.can_nt.can_nt_bridge --profile <profile> --interface slcan --channel COM3 --bitrate 1000000 --rio <robot-ip> --publish-can-summary
```

Useful optional flags:
- `--print-publish`
- `--print-summary-period 2`
- `--publish-unknown`
- `--pcap <path>`

Why this matters:
- confirms a device is seen on the bus
- distinguishes local API issues from bus visibility issues
- captures evidence for later review

The PC tool must remain read-only on CAN during this workflow.

## Step 7: Verify Basic Robot State First

Purpose: do not run device tests until robot state is sane.

Before running a focused device test, confirm:
- robot mode is what you expect
- no obvious stop latch confusion
- profile/test context is what you expect
- controller connection is what you expect
- if using UI/CLI, session/lock state is what you expect

Recommended first checks:
- State report
- Profile devices report
- Inputs/bindings report if controls matter
- Health report for obvious local faults

## Step 8: Run One Focused Test

Purpose: verify the current component behaves exactly as expected.

Run only the test(s) relevant to the newly added component.

Examples:
- select one motor smoke test and run it
- select one encoder test and run it
- verify one switch input only

Expected test qualities:
- low energy first
- clear pass/fail interpretation
- obvious physical observation
- minimal interaction with other unfinished components

Do not broaden scope until the current test result is understood.

## Step 9: Verify Expected Behavior

Purpose: decide whether the component is good, bad, or still ambiguous.

For each test, answer these questions:
- Did the commanded device move/respond?
- Did the correct device move/respond?
- Did it move/respond in the correct direction?
- Did the expected sensor reading change?
- Did local health look normal?
- Was the device visible on CAN if expected?
- Did console output show warnings/errors?

Possible outcomes:
- PASS: behavior matches expectation
- FAIL: behavior clearly wrong
- AMBIGUOUS: behavior not explained yet; collect more evidence before continuing

If ambiguous, do not move on to the next component yet.

## Step 10: Capture Evidence When Needed

Purpose: save enough data to explain failures later.

Recommended evidence:
- robot report output
- `bringup_report.json`
- CAN visibility/summary output
- PCAP/PCAPNG capture when useful
- console warnings/errors from the PC tool
- notes about physical observations

Useful actions:
- dump report from robot side
- keep CLI/UI output log snippets
- save inventory snapshots if comparing before/after changes

Evidence is especially important when the issue could be:
- wrong CAN ID
- wrong device type
- wiring fault
- reversed direction
- bad sensor mapping
- bus presence mismatch

## Step 11: Fix Or Mark Good

Purpose: close the loop before adding more hardware.

If the component passed:
- keep the device entry
- keep the useful smoke test
- optionally tag or note the component as verified
- move to the next component

If the component failed:
- fix config, wiring, power, or hardware
- rerun validate+sync
- redeploy or reapply as needed
- rerun the same focused test

If the result is ambiguous:
- gather more evidence first
- do not mask the problem by adding more components

## Recommended Bring-up Order

Purpose: suggest a practical sequencing for a new robot.

Typical order:
1. Power and core infrastructure devices
   - roboRIO
   - PDH/PDP
   - gyro if present
2. One motor controller at a time
3. One paired sensor/encoder at a time
4. One full module at a time
5. One subsystem at a time
6. Whole-robot integration only after individual parts are verified

For swerve, a practical order may be:
1. PDH/PDP
2. gyro
3. one drive motor
4. one turn motor
5. one module encoder
6. verify one full swerve module
7. repeat module-by-module
8. whole-swerve tests

## Expected Success Criteria Per Component

Purpose: define what “good enough to move on” means.

A component is ready to move on when:
- its config is validated
- its focused test runs predictably
- the expected physical behavior is observed
- the correct device responds
- no unexplained warnings/errors remain
- any required sensor feedback matches expectation
- CAN visibility is consistent with expectation when applicable

## Common Failure Categories

Purpose: help operators classify failures quickly.

### Config mistakes
- wrong CAN ID
- wrong manufacturer/deviceType
- wrong profile membership
- wrong test device label
- incorrect invert/limits/settings

### Wiring or power problems
- no response at all
- intermittent response
- brownout or power fault signals
- CAN visibility missing or unstable

### Command/selection mistakes
- wrong profile active on robot
- wrong host profile selected locally
- wrong test selected
- wrong device/group targeted

### Safety/state gating
- robot disabled
- stop latch active
- TCP session/lock issue
- controller not connected

## Troubleshooting Decision Order

Purpose: keep triage disciplined and fast.

When a component test fails, check in this order:
1. Are you targeting the correct profile and test?
2. Did validate+sync succeed after the latest edit?
3. Is the robot running the expected config?
4. Is the device visible on CAN if it should be?
5. Does robot-local health show faults/warnings?
6. Did the wrong device move?
7. Did the correct device move in the wrong direction?
8. Did console output reveal a vendor/runtime warning?
9. Only then escalate to deeper hardware replacement or subsystem-wide debugging.

## What Not To Do

Purpose: prevent common workflow mistakes.

Do not:
- add a large batch of unverified devices at once
- skip validate+sync after edits
- mix local host edits with assumptions about robot runtime state
- broaden tests before single-component behavior is understood
- treat missing CAN visibility and local API faults as the same thing
- tune behavior before basic hardware verification is complete

## Minimal Command Checklist

Purpose: provide a compact repeatable checklist for each iteration.

Per component:
1. Add/update the device in `data/bringup_system.json`
2. Add/update focused test(s)
3. Run:
   - `python -m tools.validate_sync`
4. Deploy robot code
5. Optionally start PC bridge
6. Check state/health/profile reports
7. Run one focused test
8. Verify expected behavior
9. Capture evidence if needed
10. Fix/retry or mark good

## Completion Criteria For Workflow 01

Purpose: define when the robot is ready to leave incremental bring-up mode.

Workflow 01 is complete when:
- every required hardware component has been added to config
- every required component has at least one verified bring-up test or equivalent verification path
- each component has passed focused verification or has a known documented issue
- deploy config is current and validated
- whole-subsystem and full-robot testing can begin from a known-good hardware baseline

## Related Docs

Purpose: point to the next documents operators should use.

- `docs/USER_GUIDE.md`
- `docs/ARCHITECTURE.md`
- `docs/COMMAND_HANDLER_ARCHITECTURE.md`
- `docs/TCP_UI_PROTOCOL.md`
- `docs/CLI_USER_MANUAL.md`
- `docs/CLI_REFERENCE_MANUAL.md`
- `docs/CLI_TEST_AUTHORING_USER_GUIDE.md`
- `docs/TESTING_REAL_ROBOT_BRINGUP.md`
- `docs/RELEASE_1_0_READINESS.md`
