# Test Plan: CAN Fault Finder Live Mode Phase 1

## Purpose

Provide a focused hardware test plan for the first live-mode refactor slice of `CAN Fault Finder`.

This phase is intended to validate:

- dirty-device priority reevaluation
- per-device transition/event logging
- faster disconnect/reconnect detection while the app is already running
- shared interpreted-device state consistency across `Evidence`, `Live Topology`, and `CAN Fault Finder`

This phase does not validate:

- baseline-compare mode
- baseline storage/selection
- full topology-aware region ranking improvements beyond the current live-mode consumer

## Automated Gate

Run these first:

```text
python -m unittest tools.can_nt.tests.test_passive_discovery_integration_service tools.can_nt.tests.test_bringup_ui_actions tools.can_nt.tests.test_can_fault_inference tools.can_topology.tests.test_live_topology_view
```

Expected:

- all tests pass
- no regression in the incremental evaluator
- no regression in fault-finder freeze/catch-up behavior
- no regression in topology color/status consumption

## Setup

Use:

- the current working tree
- profile `test_minimal_25_9`
- the normal Bringup UI launch path

Recommended startup:

```text
python tools/can_nt/can_nt_bridge.py --ui
```

Recommended tabs:

- `Evidence`
- `Live Topology`
- `CAN Fault Finder`
- `Visibility`

Recommended actions:

- `Active Presence Probe`
- `Run CAN Break Check`

Important operator rule:

- after each physical change, give the UI a few seconds to converge
- then run `Run CAN Break Check`

## What To Compare

For each tested device, compare:

- `Evidence`
  - `Existence`
  - `Operability`
  - `Confidence`
  - `Conflicts / Notes`
- `Live Topology`
  - node color
  - selected-device presence status
  - selected-device full-probe status
- `CAN Fault Finder`
  - affected devices
  - infrastructure summary
  - top candidate

This phase passes only if those three surfaces tell the same broad story.

## Test 1: All-Connected Baseline

Steps:

1. Power the robot normally with all expected CAN devices connected.
2. Launch the UI and wait 10-20 seconds.
3. Open `Evidence`, `Live Topology`, `Visibility`, and `CAN Fault Finder`.
4. Run `Active Presence Probe`.
5. Run `Run CAN Break Check`.

Expected:

- no false major fault candidate
- motion devices settle to `present` / `ok` or honest `degraded` / `stale`
- infrastructure devices are not falsely marked missing just because they are out of motion scope
- no long-lived contradiction between `Evidence`, `Live Topology`, and `CAN Fault Finder`

## Test 2: Live Disconnect of FALCON 9

Steps:

1. Start from the healthy baseline state with the app already running.
2. Disconnect `FALCON 9`.
3. Watch the UI for several seconds.
4. Run `Run CAN Break Check`.

Expected:

- `FALCON 9` is reevaluated quickly
- the changed device updates before unrelated devices are silently rescored
- `CAN Fault Finder` does not stay at `no_fault_detected`
- `FALCON 9` becomes the top or near-top affected device

Failure signs:

- `CAN Fault Finder` still says `no_fault_detected`
- `Evidence` still says `present` long after the disconnect
- the changed device lags behind unrelated cursor updates

## Test 3: Live Reconnect of FALCON 9

Steps:

1. From the failed `FALCON 9` state, reconnect `FALCON 9`.
2. Wait for convergence.
3. Run `Run CAN Break Check` again.

Expected:

- `FALCON 9` recovers toward `present`
- stale missing/fault state does not persist too long
- `CAN Fault Finder` updates accordingly

## Test 4: Live Disconnect of SPARKMAX/NEO 25

Steps:

1. Start healthy with the app already running.
2. Disconnect `SPARKMAX/NEO 25`.
3. Wait for convergence.
4. Run `Run CAN Break Check`.

Expected:

- `SPARKMAX/NEO 25` is reevaluated quickly
- the device becomes affected in the shared interpreted state
- fault finder does not miss the disconnect

## Test 5: Live Reconnect of SPARKMAX/NEO 25

Steps:

1. Reconnect `SPARKMAX/NEO 25`.
2. Wait for convergence.
3. Run `Run CAN Break Check`.

Expected:

- state returns toward `present`
- no long-lived stale `missing` state

## Test 6: Live Disconnect of PDP

Steps:

1. Start healthy with the app already running.
2. Disconnect `pdp`.
3. Watch LEDs on the hardware and UI surfaces.
4. Run `Run CAN Break Check`.

Expected:

- `pdp` does not remain indefinitely under infrastructure `visible`
- it moves toward `missing`, `stale`, or `conflict`
- `CAN Fault Finder` does not report `candidates=none`
- result should implicate the infrastructure path more honestly than before

Failure signs:

- `visible=pdp, roborio` remains after disconnect
- `missing=none`
- `candidates=none`

## Test 7: Live Reconnect of PDP

Steps:

1. Reconnect `pdp`.
2. Wait for convergence.
3. Run `Run CAN Break Check`.

Expected:

- infrastructure summary improves promptly
- stale infrastructure-missing state does not linger

## Test 8: Console-Heavy Disconnect Case

Steps:

1. Disconnect a device that produces obvious console errors, such as `FALCON 9`.
2. Confirm that console messages appear in the UI output.
3. Run `Run CAN Break Check`.

Expected:

- console evidence contributes to reevaluation priority
- the implicated device is not ignored
- fault finder does not stay blind while console errors are present

## Test 9: App Starts After the Robot Is Already Broken

Steps:

1. Stop the UI.
2. Physically disconnect one known device before restart.
3. Start the UI while the robot is already in the broken state.
4. Wait for convergence.
5. Run `Run CAN Break Check`.

Expected:

- the system is still useful from current snapshot evidence
- it may be weaker than the live-transition case, but it should not be blind
- this phase does not require baseline-compare mode yet

## Test 10: Surface Consistency Audit

Repeat this check for:

- `FALCON 9`
- `SPARKMAX/NEO 25`
- `pdp`
- `roborio`

For each selected device, compare:

- `Evidence`
- `Live Topology`
- `CAN Fault Finder`

Expected:

- the same device should not be `present` in one surface and clearly `missing` in another after convergence
- wording may differ, but meaning should match

## Pass Criteria

This phase is successful only if all of these are true:

- the automated gate passes
- live disconnects are detected more reliably than before
- changed devices are reevaluated promptly
- reconnects recover without stale false-fault persistence
- infrastructure devices no longer stay falsely `visible` from stale evidence after real disconnect
- `CAN Fault Finder`, `Evidence`, and `Live Topology` stay aligned on the broad device meaning

## Record Template

For each scenario, record:

- date/time
- robot state
- connected/disconnected device
- whether the app was already running
- whether `Active Presence Probe` was run
- whether `Run CAN Break Check` was run
- `Evidence` result
- `Live Topology` result
- `CAN Fault Finder` result
- pass/fail
- screenshot if failed

