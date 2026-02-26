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

Important context (plain language):
- `bus` = the roboRIO's own CAN controller health. This is the first place to check for wiring/termination problems.
- `pc` = optional CAN sniffer data from the Driver Station PC. If it's missing, ignore these fields.
- `devices` = direct readings from robot-side vendor APIs (REV/CTRE). These are local, not sniffer data.
- If `appliedDuty > 0` and `motorCurrentA = 0`: the controller is commanding output but the motor is not connected or not drawing current.
- If `cmdDuty > 0` but `appliedDuty = 0`: the command is not reaching the output (config, disabled, follower mode, or limit).
- If `bus` shows errors, `txFull`, or `busOff`: treat this as a wiring/termination issue before anything else.

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
- `devices[].appliedDuty>0` and `devices[].motorCurrentA=0`: motor leads or motor itself not connected.
- `devices[].faultsRaw` or `devices[].warningsRaw` nonzero: address device-specific faults first.
- `devices[].stickyWarningsRaw` with `reset=true`: device reboot/brownout occurred at some point.

