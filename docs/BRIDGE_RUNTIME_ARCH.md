# Bridge Runtime Architecture

**Purpose**
Define the runtime model, thread roles, and component lifecycle for the PC-side bridge (CLI/UI + CAN sniffer).

**Scope**
This document describes the bridge process only. It covers threads, component lifecycles, and the `show runtime-components` snapshot.

**Runtime Overview**
**Purpose**
Explain how the bridge process is structured at runtime.

The bridge has a single process with optional subsystems enabled by CLI flags. The core loop is the CAN sniffer, which can be disabled when no sources are enabled. The CLI and UI share the same session and runtime component model.

**Component Model**
**Purpose**
Define the components that appear in runtime snapshots.

Components are named subsystems with a coarse status string. They are distinct from OS threads.

Components:
- `cli` — The interactive CLI loop.
- `sniffer` — The CAN sniffer loop that processes frames and publishes summaries.
- `session` — The TCP bridge session to the robot.
- `visibility` — Visibility tracking and matrix calculation.
- `pcap` — PCAP/PCAPNG capture.
- `console-monitor` — NetConsole/console ingest.
- `sources` — Aggregate status for configured CAN sources.
- `source:<id>` — Per-source status for each configured source.

**Thread Model**
**Purpose**
Describe the threads and when they are created.

Threads are created only when their subsystem is enabled.

Threads:
- `MainThread` — Process main thread. Runs CLI input loop or UI mainloop.
- `sniffer` — Runs `_run_sniffer` when at least one source is enabled or console monitor is enabled.
- `keyboard` — Windows key capture for marker/reload input. Starts only when the sniffer starts.
- `source:<id>` — One reader thread per enabled CAN source. Reads frames and enqueues them.
- `tcp-reader` — Reads inbound TCP ACK/OUT responses when the session connects to the robot.
- `tx-replay` — Replays CAN frames when `--tx-seq` is enabled.

**Lifecycle by Mode**
**Purpose**
Summarize which components and threads are expected by startup mode.

`--no-can --no-nt --cli`:
- Components: `cli` running, `sniffer` stopped, `session` disconnected, `pcap` disabled.
- Threads: `MainThread` only.

`--cli` with CAN sources enabled:
- Components: `cli` running, `sniffer` running, `sources` enabled, `pcap` enabled or disabled per flags.
- Threads: `MainThread`, `sniffer`, `keyboard`, `source:<id>` threads, optional `tx-replay`.

`--ui` (with NT available):
- Components: `sniffer` running, `session` connected or disconnected, `visibility` enabled.
- Threads: `MainThread` (UI), `sniffer`, `keyboard`, `source:<id>` threads, optional `tcp-reader`.

**Runtime Snapshot**
**Purpose**
Define what `show runtime-components` reports.

The command lists two sections:
- `components` — Component names and statuses with optional detail text.
- `threads` — OS thread names, id, daemon, and alive flags.

Example:
```
Local runtime-components:
  components:
    cli: running
    sniffer: stopped
    session: disconnected (handshake=pending)
    visibility: enabled
    pcap: disabled
    console-monitor: disabled
    sources: disabled (count=0 available=0)
    source:default: unavailable (disabled)
  threads:
    MainThread id=15304 daemon=false alive=true
```

**Operational Notes**
**Purpose**
Clarify what the runtime state does and does not imply.

- `sniffer` may be stopped when no CAN sources are enabled; this is expected.
- `sources: disabled` means no sources are enabled, not a hardware error.
- `session: disconnected` is expected when the robot is not connected.
- `tcp-reader` only appears after a successful TCP connection.

**Tradeoffs**
- The runtime snapshot is a coarse health view; it does not replace detailed diagnostics.
- Thread naming favors operator clarity over internal object names.

**Future Extensions**
- Add per-thread CPU time and queue depth in the snapshot.
- Add explicit component dependency graphs.
- Add optional automatic self-tests for runtime subsystems.
