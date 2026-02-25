# AI Diagnosis Using `bringup_report.json`

This guide helps you use an AI tool to diagnose CAN bringup issues using the JSON report generated on the roboRIO.

## What To Provide To The AI
- The full contents of `/home/lvuser/bringup_report.json`.
- The short interpretation guide below.
- A one-line symptom description (for example: "FLEX LED changes but motor does not move").

## Prompt Template (Copy/Paste)
```
You are diagnosing an FRC CAN bringup system. Analyze this JSON report and return:
1) A concise diagnosis.
2) The most likely root causes.
3) Next checks ordered by speed and confidence.
4) Anything that looks healthy that rules out a CAN bus issue.

Important context:
- "bus" is roboRIO CAN controller health.
- "pc" is optional CAN sniffer data; it may be missing.
- "devices" are local API readings from roboRIO vendor libraries.
- If applied > 0 and current = 0, suspect motor/output wiring.
- If applied = 0 while set > 0, suspect config or follower mode.
- If bus has errors/txFull/busOff, treat as wiring/termination first.

JSON report:
<paste bringup_report.json here>
Symptom:
<one-line symptom here>
```

## Interpretation Quick Guide (JSON Fields)
- `bus.utilizationPct`: high steady values mean bus saturation.
- `bus.rxErrors` / `bus.txErrors`: rising means noise/corruption or controller transmit trouble.
- `bus.txFull`: rising means CAN TX buffer saturation.
- `bus.busOff`: any nonzero means hard bus failure.
- `pc.openOk=false` or `pc.heartbeatAgeSec<0`: PC sniffer not connected (ignore PC data).
- `devices[].present=false`: device not instantiated in bringup (not a CAN health issue).
- `devices[].applied>0` and `devices[].currentA=0`: motor leads or motor itself not connected.
- `devices[].faultsRaw` or `devices[].warningsRaw` nonzero: address device-specific faults first.
- `devices[].stickyWarningsRaw` with `reset=true`: device reboot/brownout occurred at some point.
