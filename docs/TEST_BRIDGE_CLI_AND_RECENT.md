Purpose: Full test plan for the Bridge CLI feature and other changes added since Saturday.

## Scope
Purpose: List what this test plan covers.

- Bridge CLI (interactive + batch).
- Shared Bridge session/ops layers.
- Robot-side UI/TCP handler refactor.
- Profile validation rule updates (full CAN ID vs numeric CAN ID).
- Direct script execution for select tools (no `-m`).

## Preconditions
Purpose: Capture required environment and safety checks.

- PC has Python 3.10+.
- Repo root is the current working directory.
- roboRIO running bringup code (for on-robot tests).
- CANable not required for CLI-only tests (use `--no-can`).

## Offline Tests (no roboRIO)
Purpose: Validate CLI parsing, profiles, and tooling without the robot.

1) Validate profiles schema + CAN ID rules
   - `python tools\can_topology\validate_profiles.py --path data\bringup_profiles.json --verbose`
   - Expect: schema/hash checks pass; numeric ID collisions show WARN; full CAN ID collisions show FAIL.

2) Visualize profiles
   - `python tools\visualize_profiles.py --input data\bringup_profiles.json --output docs\bringup_profiles_diagram.html`
   - Expect: HTML generated with per-profile diagrams.

3) Dump CAN config from profile (no CAN, no robot)
   - `python tools\can_nt\can_nt_bridge.py --profile demo_club --dump-can-config tools\can_nt\can_nt_config.json --no-can`
   - Expect: JSON file written, schema intact.

4) CLI parser smoke (no robot)
   - `python tools\can_nt\can_nt_bridge.py --batch --script tools\can_nt\scripts\bridge_cli_smoke.txt --no-can --list-keys`
   - Expect: command parsing succeeds; no robot errors; list-keys prints.

## On-Robot Tests (CLI)
Purpose: Validate end-to-end TCP UI path + robot-side behavior.

### A) Interactive CLI
1) Launch:
   - `python tools\can_nt\can_nt_bridge.py --cli --rio 172.22.11.2 --no-can`
2) Run show commands:
   - `show status`
   - `show groups`
   - Expect: ACK + OUT, text output.
3) Configure group:
   - `configure terminal`
   - `group swerve_drive`
   - `add device FL_DRIVE`
   - `bind driver.left.y analog`
   - `enable`
   - `end`
4) Verify:
   - `show group swerve_drive`
   - Expect: members + bindings reflect changes.

### B) Batch CLI
1) Run smoke script:
   - `python tools\can_nt\can_nt_bridge.py --batch --script tools\can_nt\scripts\bridge_cli_smoke.txt --no-can --rio 172.22.11.2`
2) Expect:
   - ACK/OUT for each command.
   - No prompts in batch.

### C) Conflict Policy
1) Start CLI with error policy:
   - `python tools\can_nt\can_nt_bridge.py --cli --no-can --rio 172.22.11.2 --conflict-policy error`
2) Add a device to two groups:
   - Expect: warning + prompt; default "no" cancels.
3) Batch with move policy:
   - `python tools\can_nt\can_nt_bridge.py --batch --script tools\can_nt\scripts\setup.txt --no-can --rio 172.22.11.2 --conflict-policy move`
   - Expect: devices auto-move (no prompts).

## On-Robot Tests (GUI + TCP)
Purpose: Ensure GUI still works with shared session + handler refactor.

1) Launch UI:
   - `python tools\can_nt\can_nt_bridge.py --ui --rio 172.22.11.2`
2) Run basic actions:
   - Add Motor, Add All, Print State.
   - Expect: ACK + OUT; robot responds.
3) UI handshake lock:
   - Open second UI instance.
   - Expect: lock error on second client.
4) Release lock:
   - Use "Release UI Lock" in first UI.
   - Second UI should now succeed.

## Script Execution Modes
Purpose: Ensure tools run both with and without `-m`.

1) Direct script execution:
   - `python tools\can_nt\can_nt_bridge.py --help`
   - `python tools\can_topology\validate_profiles.py --help`
   - `python tools\can_topology\can_table_import.py --help`
   - `python tools\visualize_profiles.py --help`
2) Module execution:
   - `python -m tools.can_nt.can_nt_bridge --help`
   - `python -m tools.can_topology.validate_profiles --help`
3) Expect: no import errors in either mode.

## Regression Checks
Purpose: Confirm existing behavior is unchanged when CLI/groups are unused.

- Run `python tools\can_nt\can_nt_bridge.py --rio 172.22.11.2` (normal mode).
- Verify CAN summary output unchanged.
- Ensure existing NT keys under `bringup/diag/*` are unchanged.

## Exit Criteria
Purpose: Define when tests are complete.

- All offline tests pass.
- CLI interactive + batch pass on robot.
- GUI still operates with TCP UI channel.
- No regressions in CAN tool output or NT keys.

## Tradeoffs
Purpose: Record known test limitations.

- Offline tests do not exercise TCP UI path.
- Full CLI validation requires a running roboRIO.

## Future Extensions
Purpose: Track next testing improvements.

- Add a mock TCP UI server for offline CLI testing.
- Add automated smoke tests in CI for schema validation.
