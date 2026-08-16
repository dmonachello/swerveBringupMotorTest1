# Application Note: Discovery-First Config Bootstrap

## Status

Purpose: State current release maturity for this workflow.

This workflow remains experimental during release stabilization.

- The bootstrap concept is real and useful for development.
- The supporting PoC/spec/test surface is not yet complete enough to present as a fully supported release workflow.
- Treat it as a developer/operator experiment until the release checklist explicitly promotes it.

## Purpose

Explain the supported operator workflow for starting from a brand new blank config in Bringup Control and growing it into:

- a useful subsystem config
- a larger multi-profile robot config
- a topology-backed full robot config

This note is current-behavior guidance. It is written for the current Bringup Control, topology editor, and robot runtime behavior.

## Audience

Purpose: Identify who should use this note.

- student operators bringing up a new robot
- developers building a new `bringup_system.json`
- maintainers converting a partial config into a more complete robot config

## Scope

Purpose: Define what this note covers.

This note covers:

- `File -> New Blank Config...`
- discovery-first device promotion from `Unrecognized Nodes`
- automatic bootstrap of the first usable profile
- save, push, and runtime activation behavior
- how to stop at a subsystem-sized config
- how to continue to a fuller multi-profile robot config
- when to hand off to topology editor

This note does not cover:

- detailed DSL test authoring
- vendor-specific firmware setup
- full topology layout authoring instructions
- connected deployment details beyond the config workflow

## Core Ideas

Purpose: Establish the few concepts that make the workflow understandable.

- A blank config session starts truly empty.
- Bringup Control can now be the first supported config-authoring surface.
- Discovery-first authoring is a supported bootstrap path.
- `Open Config...` is local-only. It does not push to the robot by itself.
- `Push Config` is explicit host-to-robot transfer.
- `Runtime Activate` is explicit robot-side runtime activation after a profile is selected.

The workflow separates four different meanings:

- local config session: what the host UI is editing
- saved config file: what is written to disk
- pushed robot config: what was transferred to the robot
- active runtime profile: what the robot is currently instantiating and using

Do not treat those as the same thing.

## Start States

Purpose: Show the valid ways to begin.

You can start from either of these:

1. In-memory blank session
2. File-backed blank session

Use an in-memory blank session when:

- you want to discover devices first
- you are not ready to choose a permanent file path yet

Use a file-backed blank session when:

- you already know where the new `bringup_system.json` belongs
- you want saves and later pushes to target that path immediately

## Blank Session Behavior

Purpose: Make the blank-session semantics explicit.

When you choose `File -> New Blank Config...`:

- the local config session becomes blank
- no predefined profile exists
- no predefined `default_profile` exists
- no predefined device rows exist beyond the empty top-level containers
- passive discovery memory is cleared
- profile-derived label reuse from the prior session is cleared

This means a new blank session should behave like a true fresh start inside the running UI process.

## The First Working Profile

Purpose: Explain how the first usable profile appears.

The first time you promote a discovered device and the session has no usable default profile, Bringup Control automatically:

- creates a profile named `default`
- sets it as the default profile
- selects it for local authoring
- adds the promoted device to the shared inventory
- adds that device label to `profiles.default.devices[]`

This is a bootstrap convenience. It does not mean every final robot config must stay single-profile or must keep `default` as the long-term primary profile.

If you later rename the profile that is currently designated as the config's default profile, the default-profile designation follows the renamed profile automatically.

## Workflow Map

Purpose: Provide the short version before the detailed procedure.

The discovery-first workflow is:

1. Start a blank config session.
2. Observe passive CAN devices in `Unrecognized Nodes`.
3. Promote real devices with `Create Device Definition...`.
4. Let the UI auto-create `default` when needed.
5. Continue promoting devices until the subsystem or robot slice is represented.
6. Save the config.
7. Push the config when you want the robot to use it.
8. Select the target profile.
9. Activate runtime when you want robot-side instantiation.
10. Later, open the same config in topology editor and place nodes when layout work matters.

## Detailed Procedure

## Phase 1: Start Blank

Purpose: Begin a new authoring session with no pre-existing config assumptions.

1. Open Bringup Control.
2. Choose `File -> New Blank Config...`.
3. Pick one mode:
   - `Yes` for in-memory blank session
   - `No` for immediately file-backed blank session
4. Confirm that the profile selection is `(none)`.
5. Confirm that `Defined Nodes` is empty.

Expected result:

- you have a true empty local config session
- no old profile should be silently re-adopted
- no old config path should be silently reused unless you explicitly chose file-backed mode

## Phase 2: Discover Devices

Purpose: Turn passive observation into shared config inventory.

1. Connect to the robot and let passive observation populate.
2. Watch `Unrecognized Nodes`.
3. Ignore obvious noise or devices you are not ready to author yet.
4. For each real device you want in the config, use `Create Device Definition...`.
5. Confirm the proposed label and identity details.

Expected result:

- the new device appears in `Defined Nodes`
- the current local config session is now dirty
- if no profile existed, `default` is auto-created
- the device is added to both inventory and the `default` profile

Operator note:

- discovery promotion is explicit
- it does not write to disk by itself
- it does not push to the robot by itself

## Phase 3: Stop At A Useful Subsystem

Purpose: Explain the smallest good stopping point.

You do not need a full robot before the config is useful.

A subsystem-sized config is already useful when it has:

- the real devices for that subsystem in `devices[]`
- those device labels in one profile
- labels that are stable and understandable
- enough metadata for the robot to instantiate them correctly

Examples of good subsystem stopping points:

- one drive motor plus one encoder
- one intake motor plus one limit switch
- one shooter motor pair
- one gyro plus power distribution plus one motion device

Recommended subsystem-first pattern:

1. promote only the devices for one subsystem
2. save the config
3. push the config
4. activate the selected profile
5. verify bringup behavior for that subsystem
6. continue only after the subsystem is understood

This is usually safer than attempting a full robot authoring pass in one shot.

## Phase 4: Save The Local Session

Purpose: Turn local authoring into a durable file.

Use:

- `File -> Save Config` if the session is already file-backed
- `File -> Save Config As...` if you want a new path
- `Push Config` if you want the UI to save first and then push

Important behavior:

- a discovery-created local session can exist only in memory
- if you push while the session is in memory, the UI prompts for a save path first
- if you cancel the save-path prompt, the push does not continue

Recommended naming:

- use one clear repo-owned `bringup_system.json` for the working config
- keep alternate snapshots or experiments under explicit names if needed

## Phase 5: Push To The Robot

Purpose: Transfer the authored config to the robot.

Use `Push Config` only when you want the robot to consume the current saved config.

What `Push Config` does:

- ensures local edits are saved
- transfers the config to the robot
- reports push progress and final result

What `Push Config` does not do by itself:

- it does not guarantee runtime is already active
- it does not replace the need to select the intended profile
- it does not make every device immediately move or actuate

## Phase 6: Select Profile And Activate Runtime

Purpose: Make the robot actually instantiate the profile.

After push:

1. Confirm the intended profile is selected.
2. Use `Runtime Activate` when you are ready for robot-side instantiation.
3. Verify runtime state and device presence before any motion testing.

Expected result:

- the selected profile becomes the active runtime profile
- devices in that profile can become instantiated and testable

Important distinction:

- selected profile is a choice
- active runtime profile is what the robot is actually running

## Growing From One Profile To Many

Purpose: Explain how to evolve beyond the bootstrap `default` profile.

A discovery-first bootstrap often begins with one profile:

- `default`

That is normal.

Later, expand into multiple profiles when there is a clear reason, for example:

- full robot profile
- drivetrain-only profile
- intake-only profile
- pit diagnostics profile
- alternate hardware set profile

A practical growth pattern is:

1. bootstrap everything into `default`
2. verify the device inventory is real and stable
3. split or copy profile membership later in topology editor or CLI
4. keep shared device inventory global
5. keep profile membership intentional and label-based

Do not create extra profiles just because the system supports them. Create them when they express a useful operator or bringup meaning.

## When To Move Into Topology Editor

Purpose: Clarify the handoff point.

Use topology editor after discovery-first bootstrap when you need:

- device placement on the CAN diagram
- visual topology authoring
- profile-scoped layout refinement
- group overlays and richer visual organization

You do not need topology layout before the config is valid.

A discovery-created config is already a normal config when it has:

- valid device inventory
- valid profile membership
- a usable default profile

Topology metadata can come later.

Recommended handoff point:

- after the device inventory for a subsystem or robot slice is stable
- before you need polished topology layout, presentation, or profile visual cleanup

## Full Robot Progression

Purpose: Show how a blank config becomes a full robot config.

Recommended progression:

1. Start blank.
2. Discover and promote infrastructure first:
   - roboRIO
   - power distribution
   - gyro
3. Add one motion subsystem at a time.
4. Save and verify after each subsystem-sized chunk.
5. Push and activate only when the current chunk is ready to verify.
6. Continue until the robot inventory is complete.
7. Open the resulting config in topology editor for layout and cleanup.
8. Split into more profiles only when needed.

Good order for many robots:

- infrastructure devices
- one drive corner or one drive side
- one manipulator subsystem
- the rest of the drivetrain
- remaining sensors and attachments

This order tends to isolate wiring, IDs, and configuration mistakes earlier.

## Save, Push, Deploy, Activate

Purpose: Prevent the most common operator confusion.

These actions are different:

- `Save Config`: write the current local config session to disk
- `Push Config`: transfer the saved config to the robot
- robot code deploy: deploy the Java bringup harness and deploy files through the normal GradleRIO path
- `Runtime Activate`: instantiate and use the selected profile on the robot

Short rule:

- save changes the file
- push changes the robot’s loaded config
- deploy changes the robot program and deploy-owned files
- activate changes the live runtime state

## Common Good Stopping Points

Purpose: Help an operator decide when the config is “good enough for now.”

A good first stop:

- one subsystem is represented
- the robot can instantiate that subsystem
- labels are stable
- no obvious identity mismatches remain

A good second stop:

- all major robot devices exist in inventory
- one practical profile can instantiate the full robot
- runtime activation works

A good final stop:

- topology is placed and readable
- useful extra profiles exist where needed
- the config supports both bringup and later troubleshooting workflows

## Common Mistakes

Purpose: Prevent avoidable confusion.

- Mistake: assuming `Open Config...` pushes to the robot.
  Fix: it is local-only.

- Mistake: assuming a discovered device is already saved.
  Fix: discovery promotion dirties the local session; save explicitly.

- Mistake: assuming a pushed config is already active.
  Fix: select the profile and activate runtime explicitly.

- Mistake: waiting for a full robot before verifying anything.
  Fix: stop at a subsystem-sized config and validate incrementally.

- Mistake: treating `default` as a permanent architecture decision.
  Fix: it is a bootstrap profile name; reorganize later if needed.

- Mistake: thinking missing topology placement means the config is malformed.
  Fix: discovery-first configs can be valid before topology layout exists.

## Recommended Operator Checklist

Purpose: Provide a compact reusable field checklist.

1. Start `New Blank Config...`.
2. Confirm the session is truly blank.
3. Observe `Unrecognized Nodes`.
4. Promote only the devices you want to keep.
5. Let `default` auto-create when needed.
6. Stop at one useful subsystem first.
7. Save the config.
8. Push the config when you want robot-side use.
9. Select the intended profile.
10. Activate runtime.
11. Verify subsystem behavior.
12. Repeat for the next subsystem.
13. Open topology editor later for layout and cleanup.

## Related Docs

Purpose: Point to the next documents an operator or maintainer will need.

- [USER_GUIDE.md](USER_GUIDE.md)
- [FEATURE_SPEC_BRINGUP_UI_DISCOVERY_FIRST_CONFIG_AUTHORING.md](FEATURE_SPEC_BRINGUP_UI_DISCOVERY_FIRST_CONFIG_AUTHORING.md)
- [WORKFLOW_01_NEW_ROBOT_BRINGUP.md](WORKFLOW_01_NEW_ROBOT_BRINGUP.md)
- [TEST_PROCEDURE_FULL_ROBOT_FROM_SCRATCH_V3.md](TEST_PROCEDURE_FULL_ROBOT_FROM_SCRATCH_V3.md)
