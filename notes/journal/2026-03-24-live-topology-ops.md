## Live topology ops overlay

Purpose: Capture the new live overlay feature for the topology editor.

- Added a live overlay mode that can poll runtime state over the TCP UI command channel (no NT dependency).
- Runtime state includes presenceConfidence and lastSeenMs plus key motor telemetry (current, cmdDuty, appliedDuty, tempC).
- Overlay updates at a configurable rate (default 5 Hz) and colors nodes by presence/staleness.
- Offline testing supported by loading a runtime-state JSON file in the editor.
- Phase 1 intentionally defers faults and control actions; focus is read-only visibility.
