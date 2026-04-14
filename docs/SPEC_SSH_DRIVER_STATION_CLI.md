# SSH into Driver Station (superspec1) to Run CLI

Purpose: Run the interactive bringup CLI on the Driver Station PC without interfering with Driver Station safety keyboard controls.

Tags

- `#robotics`
- `#bringup`

## Background

Purpose: Explain why running an interactive CLI directly on the Driver Station is risky during live bringup.

The FRC Driver Station actively monitors keyboard input for safety and control. Certain keypresses, especially Space and Enter, can cause:

- Robot to transition to Disabled.
- Robot to enter E-Stop.
- Loss of enable state during testing.

This behavior is intentional and critical for safety. Attempting to bypass or disable Driver Station E-Stop functionality would be unsafe and irresponsible.

## Approach

Purpose: Preserve safety controls while enabling interactive CLI use.

Run the CLI on the Driver Station PC via SSH from a separate laptop. This keeps the Driver Station keyboard dedicated to Driver Station control (including E-Stop), while the operator uses the laptop keyboard for CLI interaction.

## Machines

Purpose: Define the endpoints and paths used in this procedure.

- Host (Driver Station PC): `superspec1`
- User on host: `sshuser`
- Project directory on host: `C:\Users\dmona\swerveBringupMotorTest1-main`

## Known Quirk

Purpose: Document the observed SSH startup failure mode.

SSH connection from the laptop may fail unless the host has first pinged the laptop.

Likely causes:

- ARP resolution not established.
- Windows firewall/network discovery behavior.

## Procedure

Purpose: Provide a repeatable workflow.

### 1. Host warm-up (superspec1)

Purpose: Prime the network path so the laptop can SSH reliably.

On the host, open Command Prompt and run:

```text
ping <laptop-ip>
```

Example:

```text
ping 192.168.1.50
```

### 2. Laptop SSH into the host

Purpose: Establish the remote session used to run the CLI.

From the laptop:

```text
ssh sshuser@superspec1
```

If hostname resolution fails:

```text
ssh sshuser@<host-ip>
```

### 3. Run CLI on the host (over SSH)

Purpose: Start the interactive CLI without using the Driver Station keyboard directly.

After SSH login:

```text
cd C:\Users\dmona\swerveBringupMotorTest1-main
.\cli.bat
```

## One-Line Option (Optional)

Purpose: Reduce the steps when you don’t need an interactive shell.

```text
ssh sshuser@superspec1 "cd C:\Users\dmona\swerveBringupMotorTest1-main && .\cli.bat"
```

## Notes / Gotchas

Purpose: Prevent common operator mistakes.

- In PowerShell, use `.\cli.bat` to execute a local script.
- `sshuser` must have read/execute access to `C:\Users\dmona\swerveBringupMotorTest1-main`.
- If SSH fails initially, repeat the host ping step.

## Future Improvement (Optional)

Purpose: Capture follow-on ideas without changing current behavior.

This setup works, but it’s a workaround. Better long-term options include:

- TCP socket-based CLI (no SSH needed).
- Web UI or remote command interface.
- Dedicated input relay service.
