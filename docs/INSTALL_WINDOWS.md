# Install the Windows development workstation

## Purpose

Use this procedure to prepare a Windows PC for the complete project. The
recommended work environment is the season-specific WPILib VS Code. Open the
repository there and run the host-tool commands from its integrated PowerShell
terminal.

WPILib VS Code is the expected path for most users, but it is not mandatory. The
command-line build and Python tools also work from another editor or a
standalone PowerShell terminal when the required WPILib JDK, Git, and Python
commands are configured correctly.

You do not need to activate the Python environment to use the standard
launchers. Activation is optional.

The repository installer creates a private Python environment, installs the
required packages, and verifies the host tools. The repository installer does
not install WPILib, VS Code, Driver Station, Git, or Python. Install those tools
first as described below.

This procedure does not build, deploy, connect to, enable, or command a robot.

## Tool checklist

Install or confirm each tool that applies to your work:

- **WPILib 2026 is required for Java robot development.** It supplies GradleRIO,
  the WPILib JDK, robot libraries, deployment tools, and the season-specific
  development environment.
- **WPILib VS Code and the WPILib extension are the recommended editor.** They
  provide the supported FRC build, test, deploy, simulation, and project
  commands. The WPILib installer configures this separate VS Code installation.
- **Git for Windows is required for normal source control.** It clones the
  repository and supports updates, commits, tags, and pushes.
- **Python 3.10 or newer is required for the host tools.** It creates `.venv`
  and runs the CAN, topology, CLI, documentation, and regression tools.
- **FRC Driver Station and FRC Game Tools are required to enable and operate a
  robot.** Offline host work does not require them.
- **The Codex IDE extension is optional and recommended.** It adds
  repository-aware coding assistance. Install it in WPILib VS Code, not only in
  another VS Code installation.
- **Ollama and the configured local model are optional.** They run the local
  check-in and regression-report analysis without using Codex for that analysis.
- **Wireshark is optional.** It opens PCAP or PCAPNG captures and supports the
  live named-pipe capture workflow.
- **A CANable with slcan firmware is required only for passive PC-side CAN
  observation.** It connects the Windows host to the CAN bus through a COM port.
  The supported diagnostics path is read-only on CAN.

## Before you start

You need:

- Windows 10 or newer;
- the WPILib 2026 development environment for Java robot work;
- network access to the configured Python package source unless every required
  package artifact is already cached;
- Git, unless you already have the repository files;
- Python 3.10 or newer;
- the Python `venv` component;
- the Python Tcl/Tk component, which provides `tkinter`; and
- permission to create files in the repository directory.

Administrator access is not normally required. The installer writes to the
repository and to a Python virtual environment. It does not install a Windows
service or write packages into the system Python environment.

If your organization filters Python package downloads, configure the required
proxy or certificate settings before you run the installer. The installer
downloads packages through `pip` from the package source configured for the
selected Python installation.

## Install WPILib 2026 and WPILib VS Code

This repository uses GradleRIO `2026.2.1` and Java 17. Install the matching
WPILib 2026 development environment before you build or deploy the robot
application.

1. Follow the official
   [WPILib installation guide](https://docs.wpilib.org/en/stable/docs/zero-to-robot/step-2/wpilib-setup.html).
2. Download the Windows WPILib 2026 installer.
3. Mount or extract the downloaded installer image as directed by WPILib.
4. Run the WPILib installer.
5. Choose the installation scope that matches the PC's team or school policy.
6. Allow the installer to download and configure its recommended VS Code copy.
7. Complete the full Java development installation, not a tools-only install.
8. Finish the installer.
9. Start **WPILib VS Code 2026** from the shortcut created by the installer.

WPILib installs a separate, season-specific VS Code. Do not substitute an
unrelated system VS Code for the recommended workflow. A system VS Code can edit
the files, but it does not automatically have the WPILib extension, JDK,
GradleRIO integration, or season-specific settings.

Confirm the WPILib extension in WPILib VS Code:

1. Open the command palette with **Ctrl+Shift+P**.
2. Enter `WPILib`.
3. Confirm that WPILib build, deploy, test, and other FRC commands appear.

If no WPILib commands appear, confirm that you started **WPILib VS Code 2026**
rather than another VS Code installation. Repair or reinstall WPILib if the
extension is absent from the WPILib copy.

## Install Driver Station for connected robot work

Skip this section only if the PC will never enable or operate a robot.

1. Follow the official
   [FIRST Driver Station installation guide](https://docs.wpilib.org/en/stable/docs/zero-to-robot/step-2/first-driver-station-installation.html).
2. Install the season-compatible FRC Game Tools package.
3. Restart Windows if the FRC Game Tools installer requests it.
4. Start Driver Station once and confirm that it opens.

Driver Station is not required to install Python packages, edit configuration,
run offline tests, or inspect saved captures. It is required for normal robot
communications, enable control, and field-style operation.

## Understand the two Python installations

The procedure uses two Python locations:

1. The bootstrap Python is the Python 3.10 or newer installation already present
   on the PC. The installer uses it to create the virtual environment.
2. The runtime Python is `.venv\Scripts\python.exe` inside the repository. The
   installer puts the project packages there. The host tools use this
   interpreter after installation.

The `-Python` installer option selects the bootstrap Python. It does not cause
the installer to add project packages to that interpreter.

The default virtual environment path is:

```text
<repository>\.venv
```

The repository ignores `/.venv/` through `.gitignore`. Git does not include the
environment in commits.

## Install Git

Skip this section if `git --version` already succeeds or if you received the
repository as an extracted archive.

1. Install Git for Windows from the official Git website.
2. Accept an installation option that makes `git` available from PowerShell.
3. Close the old PowerShell window.
4. Open a new PowerShell window.
5. Verify Git:

```powershell
git --version
```

The command must print a Git version and return to the prompt.

## Install Python

Skip this section if the PC already has Python 3.10 or newer with both `venv`
and `tkinter`.

1. Download a supported Windows Python installer from the official Python
   website.
2. Install Python 3.10 or newer.
3. Include the standard-library `venv` component.
4. Include the Tcl/Tk component so that `tkinter` is available.
5. Make Python available on `PATH`, or record the full path to `python.exe`.
6. Close the old PowerShell window.
7. Open a new PowerShell window.

Verify the default Python:

```powershell
python --version
```

The version must be `3.10` or newer. For example, Python 3.10, 3.11, 3.12, or
3.13 satisfies the current minimum.

Verify `venv`:

```powershell
python -m venv --help
```

Verify `tkinter` without opening a window:

```powershell
python -c "import tkinter; print(tkinter.TkVersion)"
```

Both commands must return exit code `0`. The `tkinter` command prints a Tcl/Tk
version.

If `python` selects the wrong installation, locate all matching executables:

```powershell
where.exe python
```

Use the required executable with the installer's `-Python` option. Put a path
that contains spaces inside quotes.

## Get the repository

### Clone with Git

Choose a parent directory, then run:

```powershell
cd C:\Users\YourName\source
git clone https://github.com/dmonachello/swerveBringupMotorTest1.git swerve3
cd .\swerve3
```

If the clone already exists, do not clone it again. Change to its root directory
instead.

### Use an archive

If you received a ZIP or another archive:

1. Extract the complete archive.
2. Do not run the installer from inside the archive viewer.
3. Record the full path to the extracted repository root.

## Open the repository in WPILib VS Code

Use this workflow for normal development:

1. Start **WPILib VS Code 2026**.
2. Select **File > Open Folder**.
3. Select the repository root. This is the directory that contains
   `build.gradle`, `gradlew.bat`, `install_windows.cmd`, `src`, and `tools`.
4. Approve the workspace only if you trust this repository and its local files.
5. Wait for the Java and Gradle project import to finish.
6. Select **Terminal > New Terminal**.
7. Confirm that the terminal profile is PowerShell.

The integrated terminal should open in the repository root. Check it with:

```powershell
Get-Location
```

All PowerShell commands in this guide can run in that integrated terminal. You
can use a standalone PowerShell terminal instead, but WPILib VS Code keeps the
editor, robot commands, source control, and terminal in one place.

## Install Codex in WPILib VS Code

Codex is optional. It is useful for source review, implementation, tests,
documentation, and Git workflows in this repository.

Install the extension in the WPILib VS Code instance:

1. Start **WPILib VS Code 2026**.
2. Open **Extensions** with **Ctrl+Shift+X**.
3. Search for `Codex`.
4. Select the Codex coding-agent extension published by OpenAI. Verify the
   publisher before you install it.
5. Select **Install**.
6. Open the Codex view after installation.
7. Sign in with an account that has access to Codex.
8. Open this repository as the active workspace.
9. Start a Codex conversation and confirm that it can see the repository root.

Installing Codex in a system VS Code installation does not prove that it is
installed in WPILib VS Code. Open the Extensions view inside **WPILib VS Code
2026** and confirm the extension there.

OpenAI maintains current Codex guidance on the
[official Codex resources page](https://developers.openai.com/learn/codex).
Codex is not required to build, deploy, or run the project. Do not put an OpenAI
API key in the repository. Follow the extension's sign-in flow unless a separate
approved workflow explicitly requires an API key.

## Confirm the repository root

Run the remaining commands in the WPILib VS Code integrated PowerShell terminal
unless a section says otherwise. The install command must run from the
repository root. Confirm the location:

```powershell
Get-Location
Test-Path .\install_windows.cmd
Test-Path .\install_windows.ps1
Test-Path .\requirements-windows.txt
Test-Path .\tools\can_nt
```

Each `Test-Path` command must print `True`.

If a command prints `False`, change to the directory that contains
`install_windows.cmd`. Do not run a copied installer from another directory. The
installer resolves the repository from its own file location.

## Run the standard installation

Run:

```powershell
.\install_windows.cmd
```

Do not close the terminal while the installer is running. The first run creates
`.venv` and downloads packages, so it takes longer than later runs.

The batch file performs these actions:

1. It confirms that `install_windows.ps1` exists beside it.
2. It starts Windows PowerShell with `-NoProfile`.
3. It applies `-ExecutionPolicy Bypass` only to that installer process.
4. It forwards all installer arguments to `install_windows.ps1`.
5. It returns the PowerShell exit code to the calling terminal.

The PowerShell installer then performs these actions in order:

1. It changes the working directory to the repository root.
2. It confirms that `requirements-windows.txt` exists.
3. It runs the bootstrap Python and reads its exact version.
4. It rejects Python versions older than 3.10.
5. It creates `.venv` if `.venv\Scripts\python.exe` does not exist.
6. It rejects an existing but incomplete `.venv` directory. It does not delete
   that directory automatically.
7. It verifies the runtime Python version inside `.venv`.
8. It installs the direct package versions listed in `requirements-windows.txt`.
9. It runs `pip check` to detect incompatible or missing package dependencies.
10. It imports `can`, `serial`, `prompt_toolkit`, `reportlab`, `docx`, and
    `tkinter`.
11. It loads `tools/can_nt/bridge_cli_ebnf.txt` through the repository-owned
    grammar model.
12. It creates `tools\can_nt\logs` and `tools\can_nt\captures` if they do not
    exist.
13. It prints `Done.` only after every required step succeeds.

The installer returns exit code `0` on success. It returns exit code `2` for a
detected installation failure.

## Check the installer output

A successful run contains lines similar to these:

```text
== FRC Bringup Diagnostics Install (Windows) ==
Repo: C:\path\to\swerve3
Bootstrap Python: <version> (<bootstrap command>)
Creating virtual environment: C:\path\to\swerve3\.venv
Runtime Python: <version> (C:\path\to\swerve3\.venv\Scripts\python.exe)
Installing pinned dependencies...
Checking dependency consistency...
Checking required imports and the canonical EBNF...
Creating log folders...

Done.
Installed runtime: C:\path\to\swerve3\.venv\Scripts\python.exe
```

On a later run, the installer prints `Reusing virtual environment` instead of
`Creating virtual environment`.

Treat the installation as failed if the output contains `Install failed`, if
`Done.` is absent, or if the command returns a nonzero exit code.

Check the exit code immediately after the command if you need a machine-readable
result:

```powershell
.\install_windows.cmd
$LASTEXITCODE
```

The second command must print `0`.

## Verify the installation

Run every command in this section from the repository root.

Confirm that the runtime interpreter exists:

```powershell
Test-Path .\.venv\Scripts\python.exe
```

The command must print `True`.

Confirm the runtime Python version:

```powershell
.\.venv\Scripts\python.exe --version
```

Confirm package consistency:

```powershell
.\.venv\Scripts\python.exe -m pip check --disable-pip-version-check
```

The expected result is:

```text
No broken requirements found.
```

List the installed packages and versions:

```powershell
.\.venv\Scripts\python.exe -m pip list --disable-pip-version-check
```

The authoritative direct package versions are in `requirements-windows.txt`.
Transitive packages can also appear in `pip list` because the direct packages
depend on them.

Verify the host application's offline version command:

```powershell
.\.venv\Scripts\python.exe -m tools.can_nt.can_nt_bridge --version
```

This command does not require a CANable or a roboRIO. It must print the
application and build version information, then return to PowerShell without an
exception.

Verify the shared configuration:

```powershell
.\.venv\Scripts\python.exe -m tools.validate_sync
```

This command validates the repository configuration. It is separate from package
installation.

Run the maintained non-robot regression suite when you need full local
verification:

```powershell
.\.venv\Scripts\python.exe tools\can_nt\scripts\run_regressions.py --suite local
```

The local suite includes Python tests, Java unit tests, and maintained host-tool
regressions. It does not connect to a robot unless you explicitly select a
connected suite.

## Run without activation

Activation is not required. Use the standard CAN launcher:

```powershell
.\tools\can_nt\run_can_nt.cmd --ui
```

The batch launcher selects Python in this order:

1. An explicit first argument whose extension is `.exe`.
2. The `CAN_NT_PYTHON` environment variable.
3. `.venv\Scripts\python.exe` in the repository.
4. The first `python` command on `PATH`.

The PowerShell launcher selects Python in this order:

1. The `CAN_NT_PYTHON` environment variable.
2. `.venv\Scripts\python.exe` in the repository.
3. The first `python` command on `PATH`.

Run the PowerShell launcher with:

```powershell
.\tools\can_nt\run_can_nt.ps1 --ui
```

Both launchers print the selected interpreter before they start the host
application.

For any direct Python command, call the runtime interpreter explicitly:

```powershell
.\.venv\Scripts\python.exe -m tools.can_topology.can_top_editor
.\.venv\Scripts\python.exe -m tools.can_nt.can_nt_bridge --list-ports
```

## Activate the environment temporarily

Activation changes the `python` and `pip` commands for the current terminal
session. It does not install anything and does not affect other terminal
windows.

Activate the repository environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

The PowerShell prompt normally gains a `(.venv)` prefix. Confirm the selected
interpreter:

```powershell
python -c "import sys; print(sys.executable)"
```

The printed path must end with:

```text
swerve3\.venv\Scripts\python.exe
```

You can now use shorter commands:

```powershell
python -m tools.validate_sync
python -m tools.can_nt.can_nt_bridge --version
```

Deactivate the environment when you finish:

```powershell
deactivate
```

Closing the terminal also ends activation.

If PowerShell blocks `Activate.ps1`, either skip activation and use the explicit
interpreter path, or change the policy only for the current PowerShell process:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

The main `install_windows.cmd` command does not require this manual policy
change. Its batch wrapper already uses a process-scoped bypass for the installer
invocation.

## Select a specific bootstrap Python

Use this option when `python` on `PATH` is missing, too old, or the wrong
installation:

```powershell
.\install_windows.cmd -Python "C:\Path\To\Python\python.exe"
```

The selected executable must run Python 3.10 or newer and must include `venv`
and `tkinter`.

Do not put interpreter arguments inside the `-Python` value. For example, do not
pass `"py -3.12"` as one path. Pass the full path to the required `python.exe`.

The installer still creates the runtime interpreter at
`.venv\Scripts\python.exe` unless you also set `-VenvPath`.

## Use a custom environment path

The default `.venv` location is the supported path for the standard launchers.
Use a custom path only when repository policy, storage, or access controls
require one.

Create or update a custom environment:

```powershell
.\install_windows.cmd -VenvPath "D:\PythonEnvironments\swerve3"
```

The path can be absolute or relative to the repository root. The installer
creates the environment only when the target path does not exist. If the target
directory exists without `Scripts\python.exe`, the installer stops and reports
an incomplete environment.

The standard launchers discover only the repository `.venv`. Before you use a
custom environment with a launcher, set `CAN_NT_PYTHON` for the current
terminal:

```powershell
$env:CAN_NT_PYTHON = "D:\PythonEnvironments\swerve3\Scripts\python.exe"
.\tools\can_nt\run_can_nt.cmd --ui
```

To remove the override from the current terminal:

```powershell
Remove-Item Env:CAN_NT_PYTHON
```

You can also call the custom interpreter directly:

```powershell
& "D:\PythonEnvironments\swerve3\Scripts\python.exe" `
  -m tools.can_nt.can_nt_bridge --version
```

## Set the default roboRIO host

The standard CAN launchers use `172.22.11.2` when `BRINGUP_RIO_HOST` is unset.
To use another address for the current terminal:

```powershell
$env:BRINGUP_RIO_HOST = "roborio-2186-frc.local"
.\tools\can_nt\run_can_nt.cmd --ui
```

To remove the override:

```powershell
Remove-Item Env:BRINGUP_RIO_HOST
```

Installing the host tools does not test robot reachability. Verify the network
and robot separately before a connected workflow.

## Re-run after an update

Re-run the installer after you pull changes that modify
`requirements-windows.txt` or the setup scripts:

```powershell
git pull
.\install_windows.cmd
```

The installer reuses `.venv`, applies the direct package versions from the
current requirements file, and repeats all checks.

The installer does not remove unrelated packages that someone manually added to
`.venv`. To prove that the environment contains only dependencies produced from
the current requirements, rebuild it as described in the next section.

## Rebuild a damaged or contaminated environment

Close every host tool and terminal that is using `.venv` before you rebuild it.

From the repository root, confirm the exact target:

```powershell
Resolve-Path .\.venv
```

The result must point to the `.venv` directory inside this repository. Do not
continue if it points anywhere else.

Remove only that environment:

```powershell
Remove-Item -LiteralPath .\.venv -Recurse -Force
```

Create and verify a fresh environment:

```powershell
.\install_windows.cmd
```

Deleting `.venv` does not delete source files, configuration, captures, or Git
history. The installer recreates the environment from
`requirements-windows.txt`. Direct dependency versions stay fixed, but
transitive versions can change because the current manifest does not pin them.

If you used a custom `-VenvPath`, resolve and verify that exact custom path
before you remove it. Never substitute the repository root, your home directory,
or a broad parent directory in the recursive removal command.

## Remove the host-tool environment

To remove only the installed Python environment:

1. Close applications that use `.venv`.
2. Deactivate it if the current terminal shows `(.venv)`.
3. Confirm that `Resolve-Path .\.venv` points inside this repository.
4. Run:

```powershell
Remove-Item -LiteralPath .\.venv -Recurse -Force
```

This removal is recoverable by running `install_windows.cmd` again. It does not
remove the source repository.

The installer also creates these data directories:

```text
tools\can_nt\logs
tools\can_nt\captures
```

Do not remove those directories as part of environment cleanup if they contain
captures or logs that you need.

## Dependency ownership

`requirements-windows.txt` is the only dependency-version authority for this
installer. It contains exact versions for the direct dependencies:

- `python-can` provides CAN interfaces and frame types;
- `pyserial` provides Windows serial-port access;
- `prompt_toolkit` provides interactive CLI editing;
- `reportlab` generates PDF outputs; and
- `python-docx` generates Microsoft Word documents.

`pip` resolves and installs any transitive dependencies required by those
packages. The requirements file pins the direct packages, not every transitive
package or package hash.

Do not add a separate package list to a launcher or another installer. Update
`requirements-windows.txt`, then update tests and documentation that describe
the dependency contract.

## EBNF and Lark

`tools/can_nt/bridge_cli_ebnf.txt` is the authoritative CLI grammar. The runtime
parser and `tools/can_nt/gen_bridge_cli_parser.py` read that file through
repository-owned Python code.

The project does not require the external Lark package. The generated grammar
artifact can contain a Lark-format grammar string, but generating and using the
current CLI grammar does not import Lark.

The installer verifies that the repository-owned grammar model can load the
canonical EBNF. The regression suite also runs the generator without Python site
packages, which protects the no-Lark dependency contract.

## What the installer changes

The standard installation can create or update:

- `.venv` and its installed Python packages;
- `tools\can_nt\logs`; and
- `tools\can_nt\captures`.

The installer reads:

- `requirements-windows.txt`;
- `tools\can_nt\bridge_cli_ebnf.txt`; and
- Python modules needed for its import checks.

The installer does not:

- install or update Git;
- install or update Python itself;
- install WPILib or a JDK;
- build or deploy the Java robot application;
- edit the Windows system `PATH`;
- persist `CAN_NT_PYTHON` or `BRINGUP_RIO_HOST`;
- install packages into the bootstrap Python's global environment;
- create a Windows service or scheduled task;
- connect to a CAN interface;
- connect to a roboRIO;
- transmit CAN frames;
- add files to Git;
- create a commit or tag; or
- push to a remote repository.

## Troubleshoot installation failures

### PowerShell cannot find `install_windows.cmd`

You are not in the repository root, or the repository is incomplete.

Run:

```powershell
Get-Location
Get-ChildItem .\install_windows.*
```

Change to the directory that contains both installer files, then retry.

### Python is not found

Run:

```powershell
where.exe python
python --version
```

If no executable appears, install Python or pass the full executable path with
`-Python`.

### The installer reports Python older than 3.10

Install a supported Python or select an existing supported installation:

```powershell
.\install_windows.cmd -Python "C:\Path\To\SupportedPython\python.exe"
```

Deleting `.venv` is required if the existing environment was created by an
unsupported Python. Verify the `.venv` path before you remove it.

### The virtual environment is incomplete

The target directory exists, but `Scripts\python.exe` is absent. This can happen
after an interrupted first installation.

Close processes that use the directory. Verify the path, remove only the
incomplete environment, and rerun the installer. Follow
[Rebuild a damaged or contaminated environment](#rebuild-a-damaged-or-contaminated-environment).

### Environment creation fails

Confirm that the bootstrap Python provides `venv`:

```powershell
python -m venv --help
```

Confirm that you can write to the repository directory. Security software can
also block executable creation under `.venv\Scripts`.

Do not work around an access failure by running every host tool as
Administrator. Put the repository in a directory that your normal user account
can write to.

### Package installation cannot reach the package source

Confirm internet, DNS, proxy, and TLS certificate access for the selected Python
installation. Test `pip` through the runtime interpreter if `.venv` exists:

```powershell
.\.venv\Scripts\python.exe -m pip index versions python-can
```

If your organization uses an internal Python package index, configure `pip`
according to that organization's policy, then rerun the installer.

### `pip check` reports broken requirements

Copy the complete `pip check` output. Rerun the installer once. If the failure
remains, rebuild `.venv` from the current requirements file.

Do not silence `pip check`. The installer treats an inconsistent package
environment as a failed installation.

### The installer reports a missing import

The failure text names the import that failed. Rebuild `.venv` first. If
`tkinter` is missing, modify or reinstall the bootstrap Python with Tcl/Tk
support, remove the environment, and run the installer again.

### Activation is blocked

Activation is optional. Use `.\.venv\Scripts\python.exe` directly, or use a
process-scoped execution-policy change as shown in
[Activate the environment temporarily](#activate-the-environment-temporarily).

Do not change the machine-wide execution policy for this project.

### A launcher uses the wrong Python

Run the launcher and read its `Using Python:` line.

Check for an override:

```powershell
Get-Item Env:CAN_NT_PYTHON -ErrorAction SilentlyContinue
```

Remove a stale current-session override:

```powershell
Remove-Item Env:CAN_NT_PYTHON
```

Confirm the default environment exists:

```powershell
Test-Path .\.venv\Scripts\python.exe
```

### The host tool cannot find a COM port

Package installation is complete, but the CANable is absent, disconnected, or
using another port.

List ports:

```powershell
.\.venv\Scripts\python.exe -m tools.can_nt.can_nt_bridge --list-ports
```

Check Windows Device Manager if the expected port is absent.

### The host tool cannot reach the roboRIO

The Python installation can still be correct. Confirm the robot address and
network separately. For a USB roboRIO connection, the normal address is
`172.22.11.2`.

Use an offline command to separate installation health from robot connectivity:

```powershell
.\.venv\Scripts\python.exe -m tools.can_nt.can_nt_bridge --version
```

## Continue setup

After the host installation passes, continue with:

- [Getting started](./GETTING_STARTED.md) for the complete first-use workflow;
- [System setup](./SETUP.md) for robot build and deployment steps; and
- [Regression runner guide](./USER_GUIDE_REGRESSION_RUNNER.md) for local and
  connected test suites.
