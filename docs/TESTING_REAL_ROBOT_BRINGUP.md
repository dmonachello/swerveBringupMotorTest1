# Real-Robot Bringup Test Plan (CLI + Topology Editor)

Purpose: Validate CLI, topology editor, and CAN diagnostics against a real robot with a blank configuration.

Scope
- CLI config lifecycle, profiles, and bindings.
- Topology editor save/load and neighbor ports.
- Visibility matrix basics (single analyzer acceptable).
- Robot-side interaction safety (no CAN transmit from PC tool).

Pre-Flight
- Robot and Driver Station PC on the same network.
- CANable connected (if using live CAN). For CLI-only testing, use `--no-can`.
- Robot code deployed and enabled to provide NetworkTables and bringup harness.
- If using a blank config, back up existing files first.

Files and Paths
- Profiles: `src\main\deploy\bringup_system.json`
- Bindings: `src\main\deploy\bringup_bindings.json`
- CLI entry: `python -m tools.can_nt.can_nt_bridge --cli`
- Topology editor: `python -m tools.can_topology.can_top_editor`

Safety Rules
- Do not send CAN frames from the PC tool.
- Keep motors disabled unless explicitly testing motion.
- Use low duty cycles and short durations when you do test.

---

## Phase 1: Blank Config → home_031226 (Main Test)

Goal: Start empty and rebuild a working profile that matches `home_031226` without loading any prior config.

1. Start CLI.

```powershell
cd C:\Users\dmona\swerveBringupMotorTest\swerveBringupMotorTest1
python -m tools.can_nt.can_nt_bridge --cli
```

2. Initialize a blank profile.

```
profiles init
profile home_031226
show profile
show devices
show topology
```

Expected
- Active profile is `test_blank`.
- Devices are empty.
- Topology shows `(none)`.

3. Build device registry entries from scratch.

```
device "SPARKMAX/NEO 25"
set interface CAN
set manufacturer 5
set deviceType 2
set id 25
set model "REV NEO"
set type motor
exit

device "SPARKMAX/NEO550 7"
set interface CAN
set manufacturer 5
set deviceType 2
set id 7
set model "REV NEO 550"
set type motor
exit

device "lmSw1"
set interface DIO
set type limitSwitch
set dio 0
set invert true
exit

device "FALCON 9"
set interface CAN
set manufacturer 4
set deviceType 2
set id 9
set model "CTRE Falcon 500 motor"
set type motor
exit

device "PDH"
set interface CAN
set manufacturer 5
set deviceType 8
set id 1
set model "REV PDH"
set type power
exit

device "roboRIO"
set interface CAN
set manufacturer 0
set deviceType 1
set id 0
set model "roboRIO"
set type roborio
exit

device "candle"
set interface CAN
set manufacturer 4
set deviceType 10
set id 2
set model "CTRE CANdle"
set type misc
exit
```

Expected
- `show devices` lists: `SPARKMAX/NEO 25`, `SPARKMAX/NEO550 7`, `FALCON 9`, `PDH`, `roboRIO`, `candle`, `lmSw1`.

4. Add topology (use the editor for layout).

```powershell
python -m tools.can_topology.can_top_editor
```

In the editor:
- Select profile `home_031226`.
- Add nodes matching the labels above.
- Place them on the bus.
- Save to `src\main\deploy\bringup_system.json`.

Back in the editor, confirm the topology is present for `home_031226`.

No CLI reload is required for this test. Stay in the editor for topology validation.

5. Auto-assign or manually set neighbor ports.

```
conf terminal
topology neighbor-auto all
show topology neighbors
```

Expected
- Neighbor entries exist.

6. Save the profile after CLI + topology edits.

```
save profiles src\main\deploy\bringup_system.json --force
```

Expected
- File saved with a backup snapshot created.

----

## Phase 3: Topology Editor Round-Trip

Goal: Validate that the editor can open, modify, and save topology without breaking CLI parsing.

1. Open the editor.

```powershell
python -m tools.can_topology.can_top_editor
```

2. Load the target profile (host/editor context).

- Select profile `home_031226` in the editor and load it.
- Move one node slightly.
- Save back to `src\main\deploy\bringup_system.json`.

Expected
- Node positions updated in the editor.
- No schema or parse errors on save.

No CLI reload is required for this test. Stay in the editor for topology validation.

---

## Phase 4: Neighbor Ports (Manual + Auto)

Goal: Validate neighbor auto-assign and manual overrides.

1. Auto-assign all.

```
conf terminal
topology neighbor-auto all
show topology neighbors
```

2. Auto-assign only selected labels.

```
topology neighbor-auto all PDH,roboRIO
show topology neighbors
```

3. Manual override.

```
topology neighbor-ports set "PDH" right "roboRIO" left
show topology neighbors
```

Expected
- Neighbor entries exist.
- Manual entries replace conflicting ports for that node.

Note
- For branched wiring, do not use auto-assign beyond the linear segments.

---

## Phase 5: CANnect Device Links

Goal: Ensure CANnect links appear as `next/branch1/branch2` neighbor ports.

1. With CANnect nodes linked in the diagram.

```
show topology neighbors
```

Expected
- Neighbor entries for CANnect port links using `next/branch1/branch2`.

---

## Phase 6: Visibility Matrix (Single Analyzer)

Goal: Confirm visibility output format and basic state changes.

1. Start CLI with live CAN.

```powershell
python -m tools.can_nt.can_nt_bridge --cli
```

2. Show visibility.

```
show visibility
show visibility summary
show visibility <device_label>
```

Expected
- Matrix includes the single source.
- Visible devices show `Y`.
- Missing devices show `N` or `?` depending on source availability.

---

## Phase 7: Bindings and Inputs

Goal: Ensure bindings and alias behavior remain consistent.

```
show bindings
show bindings --all
show binding-usage driver.a
show binding-usage controller0.a
```

Expected
- Usage resolves aliases consistently.
- Local bindings override global when they match the same input.

---

## Phase 8: Tests (Create From Scratch)

Goal: Create a minimal test set without loading templates.

1. Verify bindings exist (controller0 must be present).

```
show bindings
```

2. Create a simple motor pulse test.

```
conf terminal
test create neoPulse
type button
device add "SPARKMAX/NEO 25"
inputSource controller0.A
duty 0.1
termination time 1.0
exit
```

3. Create a limit-switch stop test.

```
test create neoLimit
type button
device add "SPARKMAX/NEO 25"
inputSource controller0.B
duty 0.1
termination limitswitch 0
exit
```

4. Show and save tests.

```
show tests
save unified-config data/bringup_system.json
```

Expected
- Two tests exist and are listed.

----

## Phase 9: Execute Tests (Robot + Bridge UI)

Goal: Run the tests on the robot and verify motion/behavior and UI updates.

1. Ensure robot is enabled and safety is clear.

2. Run from CLI (robot-connected).

```
run test neoPulse
run test neoLimit
```

Expected
- NEO motor pulses at low duty.
- Motor stops when limit switch is triggered (neoLimit).

3. Run from controller (robot side).

- Use the configured controller binding for Run Test.
- Use the configured controller binding for Run All Tests.

Expected
- Tests run without CLI and match configured behavior.

4. Run from Bridge UI.

- Open the Bridge UI.
- Select `neoPulse`, click Run.
- Select `neoLimit`, click Run.
- Run All Tests (if available).

Expected
- UI reflects active test and status changes.
- Robot behavior matches test definitions.

----

## Phase 10: Save and Validate

Goal: Confirm save and validation paths run clean.

```
validate profiles --active
save profiles src\main\deploy\bringup_system.json --force
```

Expected
- Validation should not crash. Any errors should be actionable.
- Save produces a backup snapshot and writes the file.

---

## Pass/Fail Summary

Log the following:
- CLI startup and profile load success.
- Topology editor save/load success.
- Neighbor ports auto/manual behavior.
- CANnect neighbor port mapping.
- Visibility output format and sanity.
- Binding usage correctness.
- Validation and save success.

If any step fails, capture:
- The exact command.
- The CLI output.
- Which profile was active.
