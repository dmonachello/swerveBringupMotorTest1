# TCP UI Command Test Plan

Purpose: validate the TCP UI command channel, single-client lock, error handling, and NT protocol monitor behavior.

## Quick Test Plan (10–15 minutes)

1) Basic connect + handshake
- Run: `tools\can_nt\run_can_nt.cmd --ui`
- Expect: UI shows "TCP Connected" and logs `uiHandshake` ACK + OUT.

2) Single command
- Click **Add Motor**.
- Expect: ACK + OUT in UI; robot acts.

3) Single-client lock
- Launch a second UI instance.
- Expect: second UI command returns "UI locked by another client".

4) Release lock
- In the first UI, click **Release UI Lock**.
- Expect: second UI can handshake and send commands.

5) Protocol monitor toggle
- Click **Protocol Monitor ON**, then **OFF**.
- Expect: `bringup/ui_tcp/enabled` toggles in NetworkTables.

6) Disabled/E-Stop handling
- Disable robot (or E-Stop).
- Send a command.
- Expect: error response "Robot disabled" or "Robot disabled (E-Stop)".

## Full Test Plan (Comprehensive)

### A) Connectivity + Handshake
1) Launch UI with `--ui` and confirm TCP connects.
2) Verify auto-handshake:
   - UI log shows ACK + OUT for `uiHandshake`.
   - `minNextSeq` is applied (seq increments properly).
3) Reboot roboRIO and confirm:
   - UI reconnects.
   - New handshake completes.

### B) Command Flow (happy path)
4) Run each category once:
   - `addMotor`, `addAll`, `printState`, `printHealth`, `printCANdiag`, `clearFaults`, `runTest`.
5) Verify each command:
   - Produces ACK + OUT in UI.
   - Causes expected robot behavior.

### C) Single-Client Lock
6) Start UI #1 and send `uiHandshake`.
7) Start UI #2 and attempt any command:
   - Expect "UI locked by another client".
8) In UI #1, click **Release UI Lock**.
9) In UI #2, handshake and send a command:
   - Expect success.

### D) Timeout + Retry
10) Simulate missed command:
- Disable robot or interrupt TCP server briefly.
11) Send a command:
- Expect timeout (1.5s) in UI.
12) Restore robot:
- UI should re-handshake and retry the last command once.
- Command should execute once.

### E) Disabled / E-Stop Safety
13) Disable robot:
- Send command; expect "Robot disabled" error.
14) E-Stop:
- Send command; expect "Robot disabled (E-Stop)" error.
15) Re-enable robot:
- Command should succeed.

### F) Protocol Monitor (NT Dashboard)
16) Click **Protocol Monitor ON**.
- Verify `bringup/ui_tcp/*` keys:
  - `enabled=true`
  - `connected=true`
  - `lastSeq`, `lastName`, `lastStatus`, `lastMessage` update per command.
17) Click **Protocol Monitor OFF**.
- Verify `enabled=false` and `connected=false`.

### G) Crash/Exit Handling
18) Close UI window or Ctrl-C in console.
19) Start new UI instance:
- Should connect and handshake without reboot.
- Lock should be released from prior client.

### H) Stale Robot State Visibility
20) Stop robot code (leave NT running).
21) UI should show "Robot state stale (code not running?)".
22) Restore robot code and verify status clears.

## Notes
- TCP port defaults to 5809 (override with `--ui-tcp-port`).
- NetworkTables still provides state/diagnostic visibility.
- If a command is missed, UI retries the last command once after recovery.
