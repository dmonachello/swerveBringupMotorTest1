# Getting started from a new Windows PC

## Purpose

Use this tutorial to install the project, verify it without robot hardware,
deploy it to a roboRIO, connect the Bringup Control UI, and run one controlled
test.

At the end, you will have:

- a working Windows development environment
- a locally validated robot configuration
- Java code and configuration deployed to the roboRIO
- a REST connection from the Bringup Control UI to the robot
- one profile selected and one test ready to run
- a clear way to stop the robot and collect diagnostic evidence

The detailed manuals linked throughout this tutorial remain the reference for
each tool.

## Read the safety limits first

This project can command real motors. Before you power or enable the robot:

- Put the robot on blocks so that driven wheels cannot move it.
- Remove mechanisms that can release stored energy, when practical.
- Keep the Driver Station **Disable** and **E-Stop** controls within reach.
- Start with low-duty tests that target one device.
- Confirm the expected CAN ID and device label before each motion test.
- Keep people clear of moving parts.

Use Driver Station **Disable** as the normal immediate stop. Use **E-Stop** for
an emergency.

Do not depend on closing the UI, losing the network connection, REST session
timeout, or a REST stop request to stop hardware. Those events do not yet prove
that active robot execution was cancelled.

## Know the four parts

You will work with four parts of the system:

1. The Java robot application runs on the roboRIO. It owns device instances,
   tests, outputs, and robot-local safety actions.
2. The Python Bringup Control UI and Bridge CLI run on the Windows PC. They use
   the robot REST server on port `5805`.
3. `src/main/deploy/bringup_system.json` contains the shared device inventory,
   profiles, groups, topology data, and DSL tests.
4. An optional CANable lets the PC observe CAN traffic independently. The
   supported PC diagnostic path is read-only on CAN.

NetworkTables is not required for the supported bringup workflow.

## Gather the hardware and software

You need:

- a Windows PC
- Git
- Python 3.10 or newer
- the WPILib 2026 development environment used by this project
- a USB cable or another working network connection to the roboRIO
- an FRC Driver Station connection to the robot
- the robot hardware that you intend to test

You may also use:

- an Xbox controller for configured robot-local bindings
- a CANable with slcan firmware for passive CAN observation
- Wireshark for detailed CAN captures

The Gradle project targets Java 17. The WPILib installation provides the normal
JDK and GradleRIO environment for robot development.

### Install the external tools

If this PC has no FRC development tools:

1. Install Git from [Git for Windows](https://git-scm.com/download/win).
2. Install Python 3.10 or newer from
   [Python for Windows](https://www.python.org/downloads/windows/).
3. Install the full WPILib 2026 environment by following the
   [WPILib installation guide](https://docs.wpilib.org/en/stable/docs/zero-to-robot/step-2/wpilib-setup.html).
4. Install Driver Station by following the
   [FIRST Driver Station guide](https://docs.wpilib.org/en/stable/docs/zero-to-robot/step-2/first-driver-station-installation.html).

Use the WPILib VS Code installation, not an unrelated system VS Code
installation, for the normal robot build and deploy workflow.

If the roboRIO has not been prepared for the 2026 season, follow the WPILib
[roboRIO imaging guide](https://docs.wpilib.org/en/stable/docs/zero-to-robot/step-3/imaging-your-roborio.html)
before you deploy this project.

## Install the project

### Clone the repository

Open PowerShell and run:

```powershell
git clone https://github.com/dmonachello/swerveBringupMotorTest1.git
cd swerveBringupMotorTest1
```

If the repository already exists, open PowerShell in its root directory. The
root contains `gradlew.bat`, `install_windows.cmd`, `src`, `tools`, and `docs`.

### Check the required commands

Run:

```powershell
git --version
python --version
```

The Python version must be 3.10 or newer. If PowerShell cannot find `python`,
install Python and enable its PATH option before you continue.

### Install the Python dependencies

Run the repository installer:

```powershell
.\install_windows.cmd
```

The installer upgrades `pip`, installs the pinned Python packages, and creates
the local capture directories. It does not install WPILib, deploy robot code,
or change system environment variables.

Confirm that the host application starts:

```powershell
python -m tools.can_nt.can_nt_bridge --version
```

The command must print a version and return to PowerShell without an error.

For installer details, see [Windows setup](./SETUP.md).

## Verify the repository without a robot

Run these checks before you connect or enable hardware.

### Validate the shared configuration

```powershell
python -m tools.validate_sync
```

This command validates references and schema rules, then updates the canonical
configuration hash. Fix validation errors before you deploy.

### Build and test the Java application

If `JAVA_HOME` is set, point it at the WPILib JDK root, not its `bin`
directory. Then run:

```powershell
.\gradlew.bat build
```

The build compiles the robot application and runs its Java unit tests. It does
not deploy to the robot.

### Run the maintained local regressions

```powershell
python tools/can_nt/scripts/run_regressions.py --suite local
```

The local suite does not require a robot. Do not continue with an unexplained
failure. See the [regression runner guide](./USER_GUIDE_REGRESSION_RUNNER.md)
for suite contents and failure handling.

## Choose what the robot should contain

### Understand the configuration terms

The system keeps several states separate:

- **Defined** means that a device exists in `bringup_system.json`.
- **Seen** means that a robot-local or passive observer has evidence for the
  device.
- **Required** means that the selected profile, group, or test needs the
  device.
- **Active** means that the robot currently owns the device in a controlled
  runtime scope.

A device can be defined without being seen or active. Selecting a profile does
not activate its hardware.

### Use an existing profile

Open `src/main/deploy/bringup_system.json` and find `default_profile` and the
profiles under `profiles`. Confirm that the profile you plan to use contains
only the device labels intended for that robot.

For your first session, use a small profile with one known device whenever
possible. Confirm each device's manufacturer, device type, interface, and ID.

### Create or edit a profile

Start the topology editor:

```powershell
python -m tools.can_topology.can_top_editor
```

Use the editor to create devices, manage profile membership, and arrange the
topology. Save changes to
`src/main/deploy/bringup_system.json`.

After every configuration or test edit, run:

```powershell
python -m tools.validate_sync
```

Use [Add a new device](./ADD_A_NEW_DEVICE.md) for the field-by-field procedure.
Use the [new robot bringup workflow](./WORKFLOW_01_NEW_ROBOT_BRINGUP.md) when you
are adding an entire robot one component at a time.

## Connect and deploy

### Prepare the robot

1. Put the robot in a mechanically safe test position.
2. Connect the Driver Station PC to the roboRIO. USB normally uses
   `172.22.11.2`.
3. Confirm that `.wpilib/wpilib_preferences.json` contains the correct team
   number. This repository currently contains team `2186`.
4. Set the same team number in Driver Station and on the roboRIO.
5. Start Driver Station and leave the robot disabled.
6. Confirm that Driver Station can see robot communications and robot code.

### Deploy the Java application and configuration

From the repository root, run:

```powershell
.\gradlew.bat deploy
```

You can also use the WPILib deploy command in VS Code. GradleRIO deploys the
Java application and the files under `src/main/deploy`.

Keep the robot disabled after deployment. Wait for Driver Station to show that
robot code is running.

## Start the Bringup Control UI

### Start without a CANable

You do not need a CANable to use the robot REST connection. Run:

```powershell
python -m tools.can_nt.can_nt_bridge --ui --no-can --rio 172.22.11.2
```

### Start with passive CAN observation

List the serial ports:

```powershell
python -m tools.can_nt.can_nt_bridge --list-ports
```

Then start the UI with the CANable port. Replace `COM3` with the port shown on
your PC:

```powershell
python -m tools.can_nt.can_nt_bridge --ui --channel COM3 --rio 172.22.11.2
```

The CANable path observes traffic. It does not transmit CAN frames.

### Confirm the connection

Wait for the top status area to show `REST Connected`. If it remains
`REST Disconnected`, do not attempt a motion test.

Check these items:

- Driver Station shows robot communications.
- Robot code is running.
- The PC can reach `172.22.11.2`.
- Windows Firewall is not blocking the connection.
- No other UI owns the active REST session.
- Port `5805` is available on the robot.

Use **Help > Help** in the UI for descriptions of the current controls.

## Select and synchronize a profile

In the UI:

1. Open the profile controls.
2. Select the intended profile from the profile list.
3. Confirm that the topology and device lists match the physical robot.

Profile selection changes the target context. It does not instantiate devices
or enable outputs.

If you changed the local configuration after the last deploy:

1. Click **Save Config** to write pending local edits.
2. Run `python -m tools.validate_sync` in PowerShell.
3. Click **Push Config** to send the configuration to the robot.
4. Check the UI output for a successful acknowledgment.

**Push Config** updates the robot's in-memory configuration and selects the
chosen profile. It does not activate the runtime by default.

If you are unsure which configuration the robot has, use
**Download Current Config** and save it to a separate path for comparison. Do
not overwrite local work until you understand the difference.

## Inspect the robot without motion

Keep the robot disabled and inspect state first:

1. Click **Show Runtime State**.
2. Open **Live Topology**.
3. Review the selected profile, expected devices, and presence information.
4. Review warnings for missing devices, identity conflicts, or stale robot
   state.

Robot-local presence and CANable presence are different evidence sources. A
device instantiated by the robot is not automatically proven visible to the
CANable. A CANable observation does not prove that the robot instantiated the
device correctly.

If the CANable sees hardware that is not in the configuration, the device
appears under **Unrecognized Nodes**. To add one discovered device:

1. Select the intended profile.
2. Open the context menu for the unrecognized row.
3. Choose **Create Device Definition...**.
4. Confirm the identity and assign a clear label.
5. Click **Save Config**.
6. Run `python -m tools.validate_sync`.
7. Click **Push Config**.

Creating the definition changes the in-memory host configuration first. Saving
and pushing are separate actions.

## Run the first controlled test

Use an existing low-energy DSL test whose required devices you have checked.
Do not make the first run a whole-robot or run-all test.

### Prepare the selected-test scope

1. Open the **Tests** tab.
2. Select the known-safe test.
3. Review the test source and its required device list.
4. Confirm that the required list names only the intended hardware.
5. Confirm that the robot is not E-Stopped.
6. Enable the robot in teleop only when the area is clear.
7. Click **Runtime Activate**.

For selected-test ownership, **Runtime Activate** can load the test's exact
required device set into `active-group`, instantiate that controlled scope, and
make it eligible to run. Activation remains separate from selection.

If the UI reports that a scope swap is required, click **Runtime Deactivate**
first. Select the test again, verify its devices, and activate the new scope.

### Run and observe one test

1. Have one person watch the mechanism and one person watch Driver Station.
2. Click **Run Selected**.
3. Watch the physical device, UI output, robot state, and current draw.
4. Disable the robot immediately if the wrong device moves or behavior differs
   from the test description.
5. Record whether the expected device moved in the expected direction.

Do not proceed to another device while the result remains unexplained.

### End the test session

1. Disable the robot in Driver Station.
2. Confirm that outputs have stopped.
3. Use **Runtime Deactivate** if the runtime remains active.
4. Save any output, report, or CAN evidence needed for later diagnosis.

Driver Station disable deactivates the current runtime in the normal UI
workflow. You must activate the runtime again before another motion test.

## Use the Bridge CLI instead of the UI

Start the interactive CLI without a CANable:

```powershell
python -m tools.can_nt.can_nt_bridge --cli --no-can --rio 172.22.11.2
```

Start with read-only commands:

```text
help
show version --robot
show devices both
show runtime-state both
```

Use the [CLI reference manual](./CLI_REFERENCE_MANUAL.md) for command syntax.
Do not guess a write or motion command at the prompt.

## Create or import a DSL test

Robot tests are DSL source stored in the shared configuration. The removed
interactive `test create` workflow is not supported.

For a new test:

1. Write a small `.dsl` source file.
2. Import the source through the UI or CLI.
3. Validate the test.
4. Save the configuration.
5. Run `python -m tools.validate_sync`.
6. Push the configuration.
7. Select, activate, and run only that test.

Use the [Robot Test DSL user guide](./USER_GUIDE_ROBOT_TEST_DSL.md) and the
[CLI test authoring guide](./CLI_TEST_AUTHORING_USER_GUIDE.md) for syntax and
examples.

## Collect diagnostic evidence

The robot writes its JSON diagnostic report to:

```text
/home/lvuser/bringup_report.json
```

The `dumpReport` robot command refreshes that file. It does not copy the file
to the Windows PC. Retrieve the file from the roboRIO separately, then use
[AI diagnosis](./AI_DIAGNOSIS.md) to interpret it.

Important report fields include:

- `bus.rxErrors`, `bus.txErrors`, `bus.txFull`, and `bus.busOff`
- `devices[].attachments[type=revMotor|ctreMotor].cmdDuty`
- `devices[].attachments[type=revMotor|ctreMotor].appliedDuty`
- `devices[].attachments[type=revMotor|ctreMotor].motorCurrentA`

Host-side CANable evidence remains separate from the robot-local report. Keep
both when a device is visible to one observer but not the other.

To capture passive CAN traffic, start the host tool with `--pcap`:

```powershell
python -m tools.can_nt.can_nt_bridge --channel COM3 --rio 172.22.11.2 --pcap tools/can_nt/logs/first-bringup.pcapng
```

See the [CAN tool reference](../tools/can_nt/README_CAN_NT.md) for inventory,
capture, and Wireshark options.

## Troubleshoot the first connection

### Python does not start

- Run `python --version`.
- Reinstall Python 3.10 or newer with PATH enabled if the command is missing.
- Run `.\install_windows.cmd` again.

### Configuration validation fails

- Read the first error from `python -m tools.validate_sync`.
- Check duplicate labels and interface IDs.
- Check profile, group, and test references for missing device labels.
- Do not deploy until validation succeeds.

### The Java build fails

- Open the project with the WPILib 2026 environment.
- Confirm that `JAVA_HOME` points to the JDK root.
- Run `.\gradlew.bat test --stacktrace` for the detailed failure.

### The UI reports REST disconnected

- Confirm that Driver Station sees the robot.
- Confirm that deployed robot code is running.
- Confirm that the address is `172.22.11.2` for USB.
- Close another Bringup Control UI that may own the session.
- Restart the UI after the robot application is available.

### A device is missing

- Confirm the selected profile and device label.
- Confirm the configured manufacturer, device type, interface, and ID.
- Compare robot-local runtime state with passive CANable evidence.
- Inspect power, CAN wiring, termination, and vendor status LEDs.
- Do not change several configuration fields at once.

### A test cannot activate

- Put Driver Station in enabled teleop when activation requires it.
- Confirm that E-Stop is clear.
- Check whether the stop latch is active.
- Confirm that the selected test has valid required devices.
- Deactivate the old runtime before changing active scope.

## Verify future changes

Run the maintained non-robot checks before you deploy later changes:

```powershell
python tools/can_nt/scripts/run_regressions.py --suite local
```

To run the local-AI regression report after Ollama is available:

```powershell
.\tools\local-regression-report.ps1
```

Robot-connected regression is optional unless a change affects robot REST or
UI behavior:

```powershell
python tools/can_nt/scripts/run_regressions.py --suite robot-non-motion --rio 172.22.11.2
```

The connected suite is non-motion, but it still requires a reachable roboRIO.

## Continue with the detailed guides

- [Windows setup](./SETUP.md)
- [New robot bringup workflow](./WORKFLOW_01_NEW_ROBOT_BRINGUP.md)
- [Add a new device](./ADD_A_NEW_DEVICE.md)
- [Current UI and runtime rules](../Current%20UI%20And%20Runtime%20Rules%20-%20V2.md)
- [Robot Test DSL user guide](./USER_GUIDE_ROBOT_TEST_DSL.md)
- [CLI reference manual](./CLI_REFERENCE_MANUAL.md)
- [Testing](./TESTING.md)
- [Regression runner guide](./USER_GUIDE_REGRESSION_RUNNER.md)
- [AI diagnosis](./AI_DIAGNOSIS.md)
- [Documentation map](./README.md)
- [Stability analysis](./STABILITY_ANALYSIS_2026-09-15.md)
