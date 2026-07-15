# Sanity Test: Evidence UI Migration 2026-07-10

## Purpose

Provide a short post-integration sanity test plan for the host-side Evidence tab after the passive discovery migration, layout changes, fit-to-window behavior, and infrastructure-device interpretation updates.

## Scope

This sanity pass is intended to catch regressions in:

- host UI startup
- tab switching
- topology diagram fit behavior
- group-based activation workflow
- Evidence source ownership labels
- passive discovery presentation
- singleton infrastructure-device handling for `roborio` and `pdp`/`pdh`

This pass is not intended to replace the deeper PoC validation plan in [TEST_PLAN_PASSIVE_CAN_DEVICE_DISCOVERY_POC.md](/c:/Users/dmona/swerve3/docs/TEST_PLAN_PASSIVE_CAN_DEVICE_DISCOVERY_POC.md).

## Automated Gate

Run these first:

```text
python -m unittest tools.can_nt.tests.test_passive_discovery_integration_service
python -m unittest tools.can_nt.tests.test_bringup_ui_actions
python -m unittest tools.can_topology.tests.test_live_topology_view
```

Expected:

- all tests pass
- no startup-fit regression
- no Evidence ownership regression
- no infrastructure-device interpretation regression

## Startup Check

Launch the UI:

```text
python tools/can_nt/can_nt_bridge.py --ui
```

Expected:

- UI opens normally
- no `Not Responding` window at startup
- no sustained spinning/busy cursor
- profile selector, tabs, and left rail render normally
- incremental `Add Motor` / `Add All Motors` buttons are not shown in the normal left rail

## Diagram Tab Fit Check

Open these tabs one by one:

- `Live Topology`
- `Visibility`
- `Evidence`

Expected each time:

- the diagram auto-fits the current pane when the tab becomes active
- no giant zoomed-in carryover from a previous tab
- no startup freeze or tab-switch freeze

## Evidence Ownership Check

Open `Evidence`.

Expected:

- title reads `Device Evidence [NEW]`
- summary banner starts with `Evidence Engine: NEW`
- banner shows:
  - `profileInventory=NEW`
  - `presenceCheck=NEW`
  - `passive=NEW`
  - `console=NEW`
  - `probe=NEW`
  - `manual=NEW`
  - `enrichment=NEW`
  - `topologyView=NEW`
  - `interpretation=NEW`

## Layout Check

Expected:

- topology pane is smaller than before
- inspector text panes are large enough to show multiple lines without immediate truncation
- `CAN Bus Health`, `Robot Runtime Scope Check`, and `Passive CAN Evidence` appear under the diagram
- selected-device interpretation sections remain readable on the right

## Passive Device Check

With passive CAN traffic present, select:

- one REV motor
- one CTRE motor

Expected:

- `Passive CAN Evidence` shows `source=passive_discovery_poc`
- known recurring families appear in the passive text
- expected CTRE/REV devices can reach `PRESENT` from passive evidence

## Enrichment Run Check

Click `Run Enrichment`.

Expected:

- `Enrichment Evidence` panel updates from `Not run yet`
- the panel shows the host-side corroboration lens line
- topology source reports `ok`
- CTRE HTTP either:
  - reports a base URL and device count, or
  - clearly reports unavailable
- console-log enrichment either:
  - reports parsed record count, or
  - clearly reports no log text / empty

Expected for CTRE devices when CTRE HTTP is reachable:

- `Enrichment Evidence` shows `ctreHttp=present`
- `Conflicts / Notes` no longer needs `no CTRE HTTP corroboration available`
- confidence may rise relative to passive-only evidence

## Infrastructure Device Check

Select:

- `roborio`
- `pdp` or `pdh`

Expected:

- these devices are not treated like motion-test targets
- stale full-probe scope text does not act like hard missing evidence
- `Full Probe` text uses infrastructure wording:
  - `Not probed in current motion-test scope.`
  - `Infrastructure device; evaluated from passive/runtime evidence instead.`

Expected specifically for `pdp`/`pdh` when passive power-status traffic exists:

- passive evidence can lift the device out of hard `ABSENT`
- result may still be `UNKNOWN` or `DEGRADED`, but should not be missing-red purely because it was outside the active group

Expected specifically for `roborio` when there is no strong direct presence evidence:

- do not force `ABSENT` solely from out-of-scope presence/probe behavior
- `UNKNOWN` is acceptable when the available evidence is weak

## Notes Panel Check

Expected:

- notes are relevant to the current evidence mix
- infrastructure devices can show scope notes without looking like probe failures
- passive-only CTRE gaps such as `no CTRE HTTP corroboration available` may still appear when CTRE HTTP enrichment is absent
- after `Run Enrichment`, CTRE corroboration notes should reflect the fresh enrichment result rather than a stale pre-run state

## Quick Regression Scenarios

### Scenario 1: Normal startup

Expected:

- UI starts cleanly
- `Evidence` opens without freezing

### Scenario 2: Switch tabs repeatedly

Switch between:

- `Output`
- `Live Topology`
- `Evidence`
- `Visibility`

Expected:

- no hangs
- diagram fits each diagram-backed tab on entry

### Scenario 3: Active-group motor vs infrastructure device

Select:

- one active-group motor
- `pdp` or `pdh`
- `roborio`

Expected:

- motor can show motion/probe/manual-target style evidence
- infrastructure devices show passive/runtime-oriented evidence instead

### Scenario 4: Group-based workflow consistency

Expected:

- `Activate Group` depends on active-group membership only
- UI does not present incremental instantiation buttons that bypass the active-group model
- a device can be testable only when it is part of the relevant active group/scope

## Pass Criteria

This sanity pass is successful only if all of these are true:

- automated gate passes
- UI startup does not hang
- diagram-backed tabs fit on entry
- Evidence ownership remains `NEW`
- `roborio` and `pdp`/`pdh` no longer look like ordinary missing motion-test targets just because they are outside the active group

## Follow-Up

If this pass fails, capture:

- screenshot
- active selected device
- active profile
- current tab
- whether passive CAN hardware was connected
- whether the device was in the active group
