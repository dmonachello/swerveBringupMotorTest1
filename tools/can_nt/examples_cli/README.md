Purpose: Describe example Bridge CLI scripts used for local testing and reference.

## Overview
Purpose: Explain how to use these scripts.

These files are example inputs for the Bridge CLI batch mode.
Run with:
`python -m tools.can_nt.can_nt_bridge --no-can --no-nt --batch --script <path>`

Notes:
- Scripts run over the robot REST command server; the robot must be reachable if commands require robot data.

## Files
Purpose: Describe each file in this folder.

- `tmp_cli_robot2026.txt`: Recreates the 2026 robot bridgeConfig.byProfile groups and prints show outputs.
- `tmp_cli_mixed.txt`: Mixed valid/invalid commands for parser and mode behavior testing.
- `tmp_cli_device_ok.txt`: Device-mode only set commands with numeric and text values.
- `tmp_cli_script.txt`: Small baseline script for quick batch CLI smoke tests.
- `out_cli_robot2026.txt`: Output from `export cli-script` using the 2026 robot example.
- `2026.txt`: Raw notes from 2026 bringup experiments (kept for reference).
- `x.txt`: Scratchpad notes (kept to preserve historical context).
