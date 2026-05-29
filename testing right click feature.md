Use this exact flow.

**Deploy**  
From repo root:

`cd C:\Users\dmona\swerveBringupMotorTest1-main .\gradlew.bat deploy`

Wait for deploy to finish and robot code to restart.

**Driver Station**

1. Open Driver Station.
2. Leave the robot Disabled for now.
3. Confirm communications are green.

**Launch UI**  
From repo root:

`cd C:\Users\dmona\swerveBringupMotorTest1-main python -m tools.can_nt.can_nt_bridge --ui --no-can --rio 172.22.11.2`

**Connect UI**

1. In Bringup Control, connect to the robot if it is not already connected.
2. Confirm the UI shows REST connected.
3. In the profile dropdown, select test_minimal_25_9.
4. Do not assume this activates anything.

**Push Config**

1. Click Push Config.
2. Wait for success.
3. Confirm the selected profile is test_minimal_25_9.
4. Confirm runtime is still inactive after push.

Optional:

1. Click Download Current Config.
2. Confirm the UI still shows test_minimal_25_9.

**Activate Runtime**

1. Click Runtime Activate.
2. Confirm the UI shows:
    - selected profile: test_minimal_25_9
    - active runtime profile: test_minimal_25_9
    - runtime active: true

**Open Live Topology**

1. Go to Live Topology.
2. Set source to rest.
3. Turn on Enable Live Overlay.
4. Leave the default rate at 2 Hz unless you need to change it.
5. Confirm SPARKMAX/NEO 25 and FALCON 9 are visible.

**Enable Robot**

1. In Driver Station, enable Teleop.
2. Do not touch joysticks yet.

**Test Spark Right-Click Run**

1. In Live Topology, right-click SPARKMAX/NEO 25.
2. Move the manual speed slider slowly to about 0.10.
3. Observe motor motion.
4. Increase slightly if needed, for example 0.15 or 0.20.
5. Return slider to 0.0.
6. Left-click the topology background to clear manual duty.

Expected:

- Spark moves only while commanded.
- Falcon does not move.
- Spark stops when slider returns to zero or manual duty is cleared.

**Test Falcon Right-Click Run**

1. Right-click FALCON 9.
2. Move the manual speed slider slowly to about 0.10.
3. Observe motor motion.
4. Increase slightly if needed.
5. Return slider to 0.0.
6. Left-click the topology background to clear manual duty.

Expected:

- Falcon moves only while commanded.
- Spark does not move.
- Falcon stops when slider returns to zero or manual duty is cleared.

**Watch Selection Pane**  
While each motor is selected and live overlay is on, expect the right pane to update with robot-local telemetry such as:

- Presence
- Last Seen
- Current (A)
- Applied Duty
- Temp (C)

For Falcon, Cmd Duty should now populate too.

**Finish**

1. Disable the robot in Driver Station.
2. In the UI, click Runtime Deactivate.
3. Disconnect or close the UI.

**Pass Criteria**

- Push Config succeeds.
- Runtime Activate succeeds only when explicitly clicked.
- Spark right-click run works.
- Falcon right-click run works.
- Motors stop cleanly when cleared or disabled.
- Selection pane updates while live overlay is on.

If you want, I can also turn this into a short clipboard-ready checklist version.