Purpose: Install the PC-side Python tools and prepare a Windows workstation.

## Source Install (Windows)
Purpose: Set up Python dependencies and folders from a repo clone.

1) Install Python 3.10+ (3.12 recommended).
2) Open PowerShell in the repo root.
3) Run the installer:
   - `.\install_windows.cmd`

### Options
Purpose: Point the installer at a specific Python executable.

- `.\install_windows.cmd -Python C:\Path\To\Python\python.exe`

### What It Does
Purpose: Explain what the installer configures.

- Verifies Python + pip.
- Installs required Python packages:
  - `python-can`
  - `pyserial`
  - `reportlab`
  - `prompt_toolkit` (CLI inline `?` prefill)
- Creates log folders:
  - `tools\can_nt\logs`
  - `tools\can_nt\captures`

## Next Steps
Purpose: Quick commands to confirm the install works.

- Topology editor:
  - `python tools\can_topology\can_top_editor.py`
- CAN listener:
  - `python tools\can_nt\can_nt_bridge.py --rio <roborio-ip>`
- Robot code:
  - Open the repo in VS Code with the WPILib extension installed, then deploy via GradleRIO.

## Notes
Purpose: Known requirements and constraints.

- Python install is required before running the installer.
