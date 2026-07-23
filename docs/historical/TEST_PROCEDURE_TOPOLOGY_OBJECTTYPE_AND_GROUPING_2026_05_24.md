# Test Procedure - Topology `objectType`, SWYFT Topology View, and Group Refresh - May 24, 2026

Purpose: Manually verify the topology/object model changes made on May 24, 2026.

## Scope

- canonical topology/diagram `objectType` persistence
- compatibility mirror of `nodeType`
- `show topology --grouped` SWYFT rendering
- topology editor left-table refresh after group create/remove

## Preconditions

- Use the current repo checkout.
- Use the checked-in `robot_2026_swerve` profile.
- Use a local working copy of [src/main/deploy/bringup_system.json](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/deploy/bringup_system.json:1).
- No robot connection is required.

## Automated Sanity

Run these first from the repo root:

```powershell
python -m unittest tools.can_nt.tests.test_bridge_cli_topology_show -q
python -m unittest tools.can_topology.tests.test_live_topology_view -q
python -m unittest tools.can_topology.tests.test_validate_profiles_topology -q
python -m unittest tools.common.tests.test_schema_store_profiles -q
python -m unittest tools.can_topology.tests.test_can_top_editor_profile_load.TopologyEditorProfileLoadTests.test_new_profile_topology_snapshot_uses_device_ref_before_registry_exists tools.can_topology.tests.test_can_top_editor_profile_load.TopologyEditorProfileLoadTests.test_apply_topology_snapshot_accepts_object_type_without_legacy_node_type tools.can_topology.tests.test_can_top_editor_profile_load.TopologyEditorProfileLoadTests.test_create_group_from_selection_refreshes_list tools.can_topology.tests.test_can_top_editor_profile_load.TopologyEditorProfileLoadTests.test_remove_group_refreshes_list -q
python tools/can_nt/scripts/bridge_cli_v1_group_targeting_regression.py
python tools/can_nt/scripts/bridge_cli_group_targeting_4m2g3t_regression.py
```

Expected result:

- all unit tests pass
- both CLI regressions end with `failed=0`

## Manual Test 1 - `show topology --grouped`

1. Start the bridge CLI using the team’s normal local workflow.
2. Enter config mode and select the profile if needed.
3. Run:

```text
show topology --grouped
```

Expected result:

- output starts with `SOURCE: local`
- output contains `CAN Bus`
- output contains `SWYFT Backbone:`
- output contains SWYFT names such as `inject`, `CANnect Direct`, `cannect 2`, `cannect 3`, `cannect 4`
- front-left style sections show SWYFT-to-device lines such as:

```text
frontLeft:
  cannect 3 -> frontLeft Drive Motor
  cannect 3 -> frontLeft Angle Motor
  cannect 3 -> frontLeft Encoder
```

- output does not invent lines like:

```text
frontLeft Drive Motor -> backLeft Drive Motor
frontLeft Angle Motor -> backLeft Angle Motor
```

## Manual Test 2 - Create Group Refreshes Left Table

1. Open the CAN topology editor with the `robot_2026_swerve` profile.
2. In the canvas, select two or more nodes.
3. Use the editor action to create a new group from the selection.
4. Look at the left-side table immediately after the group is created.

Expected result:

- the `Group` column updates immediately
- selected nodes show the new group without needing to reload the profile or restart the editor

5. Remove the same group.

Expected result:

- the `Group` column updates immediately again
- removed group membership disappears from the left-side table without restart

## Manual Test 3 - `objectType` Is Written to Saved Topology and Diagram Data

1. Open the CAN topology editor on a copy of `bringup_system.json`.
2. Move one device node slightly so the file will change.
3. Save the profile/topology using the normal editor save path.
4. Open the saved JSON file.
5. Inspect one topology node under:

```text
topology.profiles.robot_2026_swerve.nodes[]
```

Expected result:

- each saved topology node has `objectType`
- each saved topology node still also has `nodeType`
- for a normal device node, both fields read `device`
- for a SWYFT node, both fields read `junction`

6. Inspect one diagram node under:

```text
diagram.profiles.robot_2026_swerve.nodes[]
```

Expected result:

- each saved diagram node has `objectType`
- each saved diagram node still also has `nodeType`

## Manual Test 4 - Load Works with `objectType`

1. Make a temporary copy of `bringup_system.json`.
2. In that copy, for a few topology nodes:
   - keep `objectType`
   - remove `nodeType`
3. Save the edited file.
4. Reopen that file in the topology editor.
5. Reload the same profile.

Expected result:

- the profile loads successfully
- device nodes still resolve correctly by label
- SWYFT/junction nodes still appear in the canvas
- no topology data is silently dropped just because `nodeType` was removed

## Manual Test 5 - Save Re-Mirrors `nodeType`

1. Using the temporary file from Manual Test 4, make any small editor change.
2. Save again.
3. Reopen the JSON file.

Expected result:

- the editor writes both `objectType` and `nodeType`
- `nodeType` is restored as a mirror of `objectType`

## Record Results

Use this block for the next pass:

```text
SID_COMMENT:
- Date:
- Operator:
- Profile:
- Automated sanity:
- Manual Test 1:
- Manual Test 2:
- Manual Test 3:
- Manual Test 4:
- Manual Test 5:
- Notes:
```
