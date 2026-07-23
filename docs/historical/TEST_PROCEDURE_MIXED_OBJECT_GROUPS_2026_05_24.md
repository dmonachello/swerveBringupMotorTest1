# Test Procedure - Mixed-Object Groups - May 24, 2026

## Purpose

Verify that bridge groups are label-based over the shared object set and can include both runtime devices and topology infrastructure nodes.

## Scope

This procedure covers:

- topology editor group creation with device and SWYFT nodes
- CLI group membership edits for non-device labels
- save/load roundtrip of `bringup_system.json`
- `show topology --grouped` behavior with SWYFT-backed regional groups
- runtime skip reporting for unsupported group members

This procedure does not cover:

- DSL test authoring
- global bindings schema behavior
- connected motion testing

## Preconditions

- Repo is on the current local workspace state for May 24, 2026.
- Python is available on the host.
- Java is available for `.\gradlew.bat test`.
- Use the checked-in [src/main/deploy/bringup_system.json](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/deploy/bringup_system.json:1) as the baseline config.

## Automated Baseline

Run these first:

```powershell
python -m unittest tools.common.tests.test_schema_store_profiles tools.can_topology.tests.test_can_top_editor_profile_load tools.can_nt.tests.test_bridge_cli_topology_show tools.can_nt.tests.test_bridge_cli_visibility -q
python tools/can_nt/scripts/bridge_cli_v1_group_targeting_regression.py
python tools/can_nt/scripts/bridge_cli_group_targeting_4m2g3t_regression.py
python -m unittest tools.can_nt.tests.test_bridge_cli_robot_test_dsl_cli -q
.\gradlew.bat test
```

Expected result:

- All commands pass.

## Manual Procedure

### A. Topology Editor Group Membership

1. Launch the topology editor.

```powershell
python -m tools.can_topology.can_top_editor
```

2. Load `src/main/deploy/bringup_system.json`.
3. Select `robot_2026_swerve`.
4. In the node list, confirm these groups appear in the `Group` column:
   - `frontLeft Drive Motor` includes `frontLeft` and `driveTrain`
   - `cannect 3` includes `frontLeft`
   - `cannect 2` includes `backLeft`
   - `cannect 4` includes `frontRight` and `frntRight`
   - `CANnect Direct` includes `backRight`
5. Select `cannect 3` and `frontLeft Drive Motor`.
6. Use `Groups -> Create Group from Selection...`.
7. Enter `mixedFrontLeft`.
8. Confirm the left-side table refreshes immediately.
9. Confirm both selected labels now show `mixedFrontLeft` in the `Group` column.
10. Save to a temporary file.
11. Reload that saved file.
12. Confirm `mixedFrontLeft` still contains both:
    - `cannect 3`
    - `frontLeft Drive Motor`

Expected result:

- Infrastructure labels and device labels can coexist in the same group.
- The left-side table updates immediately after create/remove.
- Save/reload preserves mixed membership.

### B. CLI Group Membership

1. Launch the CLI.

```powershell
python tools/can_nt/bridge_cli.py
```

2. Run:

```text
configure terminal
merge config src/main/deploy/bringup_system.json
profile robot_2026_swerve
show groups
```

3. Confirm the listed groups include the checked-in region groups.
4. Run:

```text
group frontLeft
member assign "cannect 3"
show group frontLeft --json --pretty
```

5. Confirm the `members` payload uses `label`, not `device`.
6. Confirm `cannect 3` appears as a member.
7. Run:

```text
member remove "cannect 3"
show group frontLeft --json --pretty
```

8. Confirm `cannect 3` is removed.
9. Run:

```text
group member assign "frontLeft" "cannect 3"
save config %TEMP%\mixed_object_groups_manual.json
```

10. Open the saved file.
11. Confirm group members are stored as:

```json
{ "label": "..." , "enabled": true }
```

Expected result:

- CLI accepts non-device labels for group membership.
- Saved config uses `members[].label`.

### C. Grouped Topology Output

1. In the same CLI session, run:

```text
show topology --grouped local
```

2. Confirm SWYFT-backed sections use SWYFT names rather than fake device-to-device hops.
3. Confirm `frontLeft` includes:
   - `cannect 3 -> frontLeft Drive Motor`
   - `cannect 3 -> frontLeft Angle Motor`
   - `cannect 3 -> frontLeft Encoder`

Expected result:

- Grouped topology output reflects CANnect branch structure.
- No invented cross-module neighbor lines appear in the `frontLeft` section.

### D. Mixed Runtime Behavior Reporting

1. Keep `cannect 3` in `frontLeft`.
2. Add a binding to `frontLeft` that drives from a real controller input.
3. Run the robot with current code.
4. Trigger the binding input.
5. Run:

```text
show group frontLeft --json --pretty
```

Expected result:

- Device members respond normally.
- `cannect 3` is not treated like a motor.
- The command succeeds.
- The group report includes `skippedMembers` when unsupported labels were skipped during runtime application.

## Pass Criteria

- Mixed groups can contain both device and infrastructure labels.
- The topology editor, CLI, persisted config, and grouped topology output all agree on the same memberships.
- Saved group members use `label`.
- Unsupported runtime members are skipped and reported, not treated as fatal errors.

## Notes

- `selectedDevice` remains device-only.
- Current robot-local command transport names still use `groupAddDevice` / `groupMemberEnable` internally; that transport naming is not the persisted config contract.
