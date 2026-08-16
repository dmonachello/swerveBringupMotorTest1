# Release Validation Procedure 2026-08-16

## Purpose

Provide one concrete verification procedure for the 2026-08-16 stabilization pass.

This procedure covers:

- the repository-side P1 fixes completed in this pass
- the maintained local regression gate
- the operator-facing manual checks that still need to be run on Windows
- the connected roboRIO checks that cannot be closed by local source edits alone

## Scope

This procedure verifies:

- deterministic local verification behavior
- topology editor profile-source behavior
- topology editor degraded-save reporting
- Windows installer and launcher portability
- release identity and supported documentation path
- maintained host-side regression coverage
- required connected robot safety and recovery checks

This procedure does not verify:

- full event-side field bringup on a competition robot
- every historical document in the repository
- every experimental passive-discovery path

## Preconditions

- Current date context: August 16, 2026.
- Work from the repository root on Windows.
- Use the current stabilization branch/worktree for this pass.
- If connected validation will be run:
  - roboRIO is reachable
  - Driver Station is available
  - the robot can be safely enabled/disabled

## Expected Outcomes

At the end of this procedure:

- the maintained local regression suite should pass
- the local source test surfaces touched by this pass should pass
- `gradlew test` should not dirty the worktree
- topology profile browsing should stay bound to the active opened config
- topology save degradation should be visible to the operator
- Windows launcher behavior should no longer depend on one developer machine
- the remaining release risk should be limited to connected robot verification and any intentionally experimental workflows

## Section 1: Local Regression Gate

Run:

```powershell
python tools/can_nt/scripts/run_regressions.py --suite local --no-history
```

Expected:

- `dsl-unit` passes
- `cli-unit` passes
- `java-unit` passes
- `group-targeting-v1` passes
- `group-targeting-4m2g3t` passes
- `topology-editor` passes
- `cross-surface` passes
- `changelog-guard` passes
- `config-api-guard` passes
- `ui-runtime-rules-lockstep` may report `missing_baseline`, but the suite must still finish with zero failed bundles

Record:

- overall suite summary
- any unexpected failed bundle

## Section 2: Focused Source Tests

Run:

```powershell
python -m pytest tools/can_nt/tests/test_bringup_ui_actions.py -q
python -m pytest tools/can_nt/tests/test_host_ui_state_service.py -q
python -m pytest tools/can_topology/tests/test_can_top_editor_profile_load.py -q
```

Expected:

- all three commands pass
- the topology profile-load file may include one skipped fixture-dependent case; no failures are acceptable

Record:

- pass/fail result for each command

## Section 3: Deterministic Build Verification

Start from a clean worktree if possible.

Run:

```powershell
.\gradlew.bat test
git status --short
```

Expected:

- Gradle test succeeds
- no tracked build metadata files are rewritten by the test run
- no unexpected source files become modified just because verification ran

Fail criteria:

- `src/main/java/frc/robot/BuildInfo.java` changes
- `tools/common/build_info.py` changes
- any other tracked-file mutation caused only by the verification run

## Section 4: Topology Editor Active-Source Verification

Purpose: Verify the P1 fix for the lower `Profiles` dropdown and `Load` action.

Preparation:

- Have two different `bringup_system.json` files available.
- File A should contain one profile set.
- File B should contain a different profile set with at least one profile name not present in File A.

Steps:

1. Start the topology editor.
2. Let it load the default/canonical config.
3. Observe the lower `Profiles` dropdown once.
4. Use `File -> Open Config...` and open File B.
5. Observe the lower `Profiles` dropdown again.
6. Choose a profile that exists only in File B.
7. Press `Load`.

Expected:

- after `Open Config...`, the lower dropdown values change to the profiles from File B
- canonical-only profile names do not remain in the lower dropdown
- `Load` opens the selected profile from File B rather than loading from the canonical deploy config
- the editor canvas/list/details update to the File B profile contents

Fail criteria:

- lower dropdown still shows canonical-only names after opening File B
- `Load` opens the wrong profile or wrong file

## Section 5: Topology Save Degradation Reporting

Purpose: Verify that backup or deploy-sync problems are no longer silent.

### Normal Save Path

Steps:

1. Open a writable config in topology editor.
2. Make a small non-destructive change.
3. Run `Save Config`.

Expected:

- save succeeds
- standard save confirmation appears
- no degraded-save warning appears

### Backup Failure Visibility

One practical method is to use a target location where the main file can still be written but backup creation is blocked by permissions or file policy.

Steps:

1. Prepare a config path where the main write remains possible.
2. Block or break the backup side path behavior.
3. Save again.

Expected:

- the main save may still succeed
- the UI must show `Saved With Warnings`
- the warning text must mention backup failure explicitly

### Deploy Sync Failure Visibility

If testing `Save To Deploy`, create a condition where canonical save can succeed but deploy copy/sync fails.

Expected:

- canonical save succeeds
- the UI shows `Saved With Warnings`
- the warning text must mention deploy sync failure explicitly

Fail criteria:

- save silently succeeds with no warning even though backup/sync failed

## Section 6: Windows Installer And Launcher Portability

Purpose: Verify that the Windows path is no longer tied to one machine-specific Python path or one hard-coded roboRIO host.

### Installer

Run:

```powershell
.\install_windows.cmd
```

Expected:

- installs pinned Python dependencies
- does not install retired NetworkTables Python packages
- creates expected log/capture folders
- prints guidance for `CAN_NT_PYTHON` and `BRINGUP_RIO_HOST`

### Launcher Environment Override

Set:

```powershell
$env:CAN_NT_PYTHON="C:\Path\To\python.exe"
$env:BRINGUP_RIO_HOST="roborio-XXXX-frc.local"
```

Run:

```powershell
cli.bat --help
uiNoCan.bat --help
tools\can_nt\run_can_nt.cmd --help
```

Expected:

- wrappers launch without depending on the old user-specific Python 3.13 path
- extra CLI arguments are forwarded through the wrappers
- `BRINGUP_RIO_HOST` overrides the default roboRIO target

Fail criteria:

- wrappers still require a machine-specific Python path
- `uiNoCan.bat` drops forwarded arguments
- launcher ignores `BRINGUP_RIO_HOST`

## Section 7: Release Identity And Supported Doc Path

Verify these files:

- `tools/can_nt/VERSION`
- `tools/common/app_versions.py`
- `src/main/java/frc/robot/AppVersion.java`
- `README.md`
- `docs/TCP_UI_PROTOCOL.md`
- `docs/USER_GUIDE.md`
- `docs/APP_NOTE_DISCOVERY_FIRST_CONFIG_BOOTSTRAP.md`

Expected:

- shipped version surfaces report `1.0.0-rc1`
- README presents release-candidate stabilization, not contradictory alpha-vs-1.0 messaging
- README uses repository-relative links rather than machine-specific `/abs/path/...` links
- `docs/TCP_UI_PROTOCOL.md` is clearly marked historical/retired
- stale supported-path NetworkTables guidance is removed from the user-facing doc entry path
- discovery-first bootstrap is explicitly marked experimental during stabilization

## Section 8: Connected roboRIO Validation

Purpose: Close the remaining release item that cannot be verified through source-only work.

Run:

```powershell
python tools/can_nt/scripts/run_regressions.py --suite robot-non-motion --rio <rio-ip>
```

Record:

- exact roboRIO address used
- pass/fail result
- any manual operator observations during the run

## Section 9: Manual Connected Safety Checks

These must be verified on a connected robot with safe operator control.

### Runtime Activate

Steps:

1. Start the supported host surface.
2. Select a valid profile.
3. Put the robot in teleop enabled state.
4. invoke `Runtime Activate`.

Expected:

- activation succeeds
- operator messaging references `Runtime Activate`
- runtime state reflects the selected active scope/profile

### Driver Station Disable

Steps:

1. Activate runtime.
2. Disable from Driver Station.
3. Re-enable teleop.

Expected:

- outputs stop on disable
- runtime must require a fresh explicit `Runtime Activate` before motion resumes
- no misleading “still runnable” messaging remains on the host surface

### E-Stop

Steps:

1. Reach a safe test configuration.
2. Trigger E-stop.
3. Observe host and robot state.

Expected:

- motion is blocked
- host messaging clearly indicates E-stop
- recovery guidance is explicit

### Disconnect / Reconnect

Steps:

1. Start with an active session.
2. Interrupt host-to-robot connectivity.
3. Restore connectivity.

Expected:

- host notices disconnect
- state becomes non-runnable while disconnected
- reconnect path restores state cleanly without stale success indications

### Session Lock Conflict

Steps:

1. Connect one CLI or UI session.
2. Attempt a second session from another surface/client.

Expected:

- single-client ownership rules are enforced
- the losing client gets clear conflict messaging

### Stop-Latch Behavior

Steps:

1. Start a controlled action path.
2. Interrupt it using the supported stop/deactivate path.
3. Confirm motion does not resume until reactivated by the approved workflow.

Expected:

- stop/deactivate state remains latched until a fresh activation path is taken

## Section 10: Pass Criteria

This stabilization pass is verified when:

- maintained local regression suite passes
- focused UI and topology source tests pass
- `gradlew test` does not dirty tracked build metadata
- topology active-source behavior matches the current UI/runtime rules
- degraded save paths are visible to the operator
- Windows launcher/install path is portable and overrideable
- release identity and supported documentation path are internally consistent
- connected robot non-motion and manual safety checks pass

## Section 11: Remaining Known Limits

Even after this procedure passes:

- discovery-first remains experimental until separately promoted
- broad connected robot validation still depends on real hardware access
- historical documents outside the curated supported path may still describe older architectures

