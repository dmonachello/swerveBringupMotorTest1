CLI User Manual (Bringup Bridge CLI)

Purpose: Explain how to use the CAN bringup bridge CLI for local configs and robot control.

Overview
Purpose: Summarize what the CLI does.
- Manages bringup groups, device membership, bindings, and metadata.
- Supports local-only editing (no robot/CAN) or robot-connected runtime control.
- Reads and writes unified bringup_system.json (profiles + bridgeConfig.byProfile).
- Device labels are unique and shared across tools via bringup_system.json.

Configuration Paths
Purpose: Explain the multiple ways to build and edit configs.
There is more than one valid path to configure the system. You can start
from the topology tool, from the CLI, or from the sniffer. Many paths can
feed into each other.

Path A: Topology Tool (profiles-first)
Purpose: Use the topology UI to define devices and layout.
Workflow:
- Edit bringup_system.json (device lists + diagram).
- Ensure labels are unique.
- Load in CLI with merge config and create groups.
- Save unified config with groups.

Path B: CLI-Only (no topology tool)
Purpose: Build a unified bringup_system.json with devices and groups.
Workflow:
- Create devices in CLI (device <name>).
- Create groups and bindings.
- Save unified config.

Path C: Sniffer Bootstrap
Purpose: Use observed CAN traffic to seed bringup_system.json.
Workflow:
- Run sniffer and dump a profile.
- Rename labels to be unique and meaningful.
- (Optional) edit topology diagram.
- Load bringup_system.json in CLI and add groups.

Path D: Manual JSON Edit
Purpose: Edit bringup_system.json directly.
Workflow:
- Edit JSON by hand (labels, IDs, tags, attachments).
- Validate.
- Load into CLI for group work.

Cross-Editing (mixing paths)
Purpose: Describe how data flows between tools.
- Topology edits -> CLI groups (profiles are canonical).
- Sniffer profile -> manual rename -> topology refine -> CLI groups.
- CLI-only config -> export script -> manual tweaks -> re-run script.
- Robot runtime groups -> save config -> edit in CLI.

Quick Start (Local-Only)
Purpose: Run the CLI without robot or CANable.
Example:
  python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt
  merge config data/bringup_system.json
  show groups local
  configure terminal
  profile robot
  group swerve_front_left
  add device "Drive Motor (swerve-front-left)"
  exit
  save unified-config data/bringup_system.json
Notes:
- Windows paths accept either / or \\. Use quotes if the path contains spaces.

Quick Start (Robot-Connected)
Purpose: Use live robot runtime groups.
Example:
  python tools\can_nt\can_nt_bridge.py --cli --rio 172.22.11.2
  connect
  show groups
  save config x.json

Test Authoring (Bringup Tests)
Purpose: Create and edit bringup tests without writing JSON.
Workflow:
- Enter config mode: `configure terminal`.
- Select or create a test set: `test set <name>`.
- Create a test: `test create <name>` (enters test mode).
- Configure fields (`type`, `device add`, `inputSource`, `duty`, `termination`, etc.).
- Save: `write tests bringup_tests.json`.
Notes:
- Device labels come from `data/bringup_system.json`.
- See `docs/CLI_TEST_AUTHORING_USER_GUIDE.md` for the full walkthrough.

Modes
Purpose: Explain prompt modes and how to enter/exit.
- Exec mode: bridge>
- Config mode: bridge(config-profile-<name>)#
- Group mode: bridge(config-profile-<name>-group-<name>)#
- Device mode: bridge(config-device-<name>)#
- exit pops one mode; end returns to exec.
- Windows EOF: Ctrl+Z then Enter behaves like exit (Ctrl+D on POSIX shells).

Core Commands (Exec)
Purpose: High-level control.
- help / help <topic>
- connect / disconnect
- show ... (see Show Commands)

Show Commands
Purpose: Inspect state.
- show status [local|robot|both] [--json]
- show groups [local|robot|both] [--json]
- show group <name> [local|robot|both] [--json]
- show devices [local|robot|both] [--json]
- show device <name> [local|robot|both] [--json]
- show device registry <name> [local|--local] [--json]
- show bindings [local|robot|both] [--json]
- show runtime-state [local|robot|both] [--json]
- show config local-raw [local] [--json]
- show profiles [local] [--json]
- show profile [local] [--json]
Notes:
- show group prints member names and binding details in text mode.
- show devices (local) lists the full profile-derived device inventory, not just group members.
- show device includes the profile label and metadata.
- show device registry returns the full device registry entry (local only).
- On startup, the CLI auto-imports `data/bringup_system.json` if it exists (replaces groups).
- merge config is only allowed when the incoming profiles hash matches the loaded profiles; otherwise use import config.

Config Commands
Purpose: Build and edit groups.
- group <name> / no group <name>
- profile <name>
- selected-device <name>
- selected-mode <on|off>
- rename device <old> <new>
- merge config <path>
- import config <path>
- validate config [path]
- save unified-config <path>
- save local-config <path>
- save config <path>
- save profiles <path>

Group Mode Commands
Purpose: Manage devices and bindings in a group.
- add device <name>
- no device <name>
- member <name> <enable|disable|toggle>
- bind <input> <analog|hold|toggle|jog-forward|jog-reverse> [value]
- no bind
- enable / disable
- run test [name]
- show [members|binding]

Group Mode Rule
Purpose: Ensure device entries exist before group membership.
- Device labels must exist in the active profile before add device.
  Create or rename device labels in the topology tool and reload profiles.
- Batch scripts are linted before execution to ensure device entries appear
  before add device commands.

Validate Local Config
Purpose: Validate the current in-memory config without a file.
Example:
  validate config

Device Mode Commands
Purpose: Edit device metadata in local config.
- show
- set <vendor|role|notes|bus|tags> <value>
- no <vendor|role|notes|bus|tags>
Note:
- Device identity is label-only; CAN ID metadata lives in bringup_system.json.
- When bringup_system.json is loaded, device edits write back to profiles and require save profiles or save unified-config.

Config Files
Purpose: Define inputs/outputs and expected shape.
Unified bringup_system.json:
  {
    "schema_version": 4,
    "data_version": "...",
    "data_hash": "...",
    "default_profile": "robot",
    "profiles": { ... },
    "devices": [ ... ],
    "diagram": { "profiles": { ... } },
    "bridgeConfig": {
      "schemaVersion": 2,
      "generatedAt": null,
      "byProfile": {
        "robot": {
          "groups": [...],
          "selectedDevice": { "device": "", "enabled": false }
        }
      }
    }
  }
bridgeConfig-only file (legacy local-only):
  {
    "schemaVersion": 2,
    "generatedAt": null,
    "byProfile": {
      "robot": {
        "groups": [...],
        "selectedDevice": { "device": "", "enabled": false }
      }
    }
  }
Note:
- bridgeConfig-only files are legacy and will be removed after the unified workflow is adopted.
Note:
- When writing configs, devices are listed before groups for consistency.
- Device names must be unique. Duplicate labels are invalid.

Unified Config (bringup_system.json)
Purpose: Clarify source of truth.
- bringup_system.json is the single source of truth for device labels and groups.
- The devices registry defines device identity and attachments.
- The profiles section lists device labels only.
- bridgeConfig stores groups/bindings/selectedDevice per profile that reference those labels.
- The default_profile is used when generating local device metadata.
- schema_version is 4 (see docs/PROFILE_SCHEMA_REFACTOR.md).

Config Save Formats
Purpose: Explain which files to save and why.
- Unified JSON (authoritative): save unified-config <path>
  Use as the primary source of truth for devices + groups.
- Groups-only JSON (local use): save local-config <path>
  Use for quick local per-profile group edits without changing profiles.
- Runtime bridgeConfig JSON (from robot): save config <path>
  Captures live runtime groups from the robot for later review or reuse.
- CLI script (derived): export cli-script <path>
  Convenience batch script generated from the current local config.
  Regenerate from JSON; do not hand-edit.
- Profiles JSON (devices only): save profiles <path>
  Writes bringup_system.json after device edits and preserves bridgeConfig.byProfile.

Usage Guidance
Purpose: Recommend a stable workflow.
- Use JSON as the canonical config and store it in version control.
- Generate scripts from JSON for quick rebuild or demos.
- Recreate a config by running the script, then save JSON:
  python tools\can_nt\can_nt_bridge.py --batch --script x_rebuild.txt --no-can --no-nt
  save unified-config data\bringup_system.json

Manual CLI Batch Scripts
Purpose: Explain when and how to hand-write a batch script.
Batch scripts are just CLI command lists. You can hand-write them when you want a
human-readable sequence of steps, but the preferred flow is to export a script
from JSON and treat scripts as derived artifacts.
Guidance:
- Put all device definitions before any add device commands.
- If you are using bringup_system.json profiles, start with: merge config <bringup_system.json>.
- Keep one command per line; avoid extra prompts or output lines.
Example:
  configure terminal
  device "Arm Motor"
  exit
  group arm
  add device "Arm Motor"
  bind LY analog
  exit
Run:
  python tools\can_nt\can_nt_bridge.py --batch --script arm_rebuild.txt --no-can --no-nt

Guided Walkthrough: Build a Full Config From Scratch
Purpose: Step-by-step guide to create a complete unified config.
This assumes a local-only session (no topology tool).

Step 1: Start the CLI
Purpose: Launch in local-only mode.
Example:
  python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt

Step 2: Enter config mode
Purpose: Create an empty local config in this session.
Example:
  configure terminal

Step 3: Create all device entries first
Purpose: Devices must exist before groups can reference them.
Do this for each device you plan to group.
Example (repeat pattern for all devices):
  device "Drive Motor (swerve-front-left)"
  set vendor CTRE
  set role "swerve drive"
  set tags ["swerve","drive","front-left"]
  exit

Example (sensor device):
  device "Encoder (CANCoder) (swerve-front-left)"
  set vendor CTRE
  set role encoder
  set tags ["encoder","swerve-front-left"]
  exit

Step 4: Create groups and add devices
Purpose: Organize devices into testable groups.
Example:
  group swerve_front_left
  add device "Drive Motor (swerve-front-left)"
  add device "Angle Motor (swerve-front-left)"
  add device "Encoder (CANCoder) (swerve-front-left)"
  bind LY analog
  exit

Step 5: Validate the config
Purpose: Ensure all group members exist in devices.
Example:
  validate config

Step 6: Save the config
Purpose: Write a unified bringup_system.json file.
Example:
  save unified-config data\bringup_system.json

Step 7: Export a rebuild script (optional)
Purpose: Generate a replayable script for future rebuilds.
Example:
  export cli-script x_rebuild.txt

Step 8: Reuse the config
Purpose: Load and reuse in a future session.
Example:
  merge config data\bringup_system.json

Unified Workflow (Topology + CLI)
Purpose: Use bringup_system.json as the single source of truth.
1) Edit profiles (labels must be unique). Use the topology tool or edit JSON.
2) Load bringup_system.json in the CLI:
   merge config data\bringup_system.json
3) Create groups using those labels.
4) Save unified config:
   save unified-config data\bringup_system.json
Notes:
- Device edits update the loaded profiles data and require save profiles or save unified-config.
- The CLI derives devices from the default_profile.

Device Mode Examples
Purpose: Show how to create and fully define device entries in local sessions.

Example: Create a new device entry with all attributes
Purpose: Create a new device and set CAN identity fields.
Example:
  configure terminal
  device "Test Motor 1"
  set vendor REV
  set role "arm motor"
  set notes "bench test motor"
  set bus 0
  set tags ["arm","motor","test"]
  exit

Example: Update device metadata (decimal and hex)
Purpose: Demonstrate edits using decimal and hex.
Example:
  configure terminal
  device "Drive Motor (swerve-front-left)"
  set vendor CTRE
  set role "swerve drive"
  set tags ["swerve","drive"]
  exit

Example: Clear a device field
Purpose: Remove a field from the device entry.
Example:
  configure terminal
  device "Test Motor 1"
  exit

Example: Create device first, then add to group
Purpose: Show preferred ordering for scripts.
Example:
  configure terminal
  device "Arm Motor"
  exit
  group arm
  add device "Arm Motor"
  bind LY analog
  exit

Example: Sensors with metadata
Purpose: Define IMU and encoder device identities.
Example:
  configure terminal
  device "IMU (Pigeon2)"
  set vendor CTRE
  set role imu
  set tags ["imu","swerve"]
  exit
  device "Encoder (CANCoder) (swerve-front-left)"
  set vendor CTRE
  set role encoder
  set tags ["encoder","swerve-front-left"]
  exit

Examples
Purpose: Provide ready-to-run patterns for common networks.

Example: 4-Module Swerve (Kraken drive, NEO angle, CANCoder)
Purpose: Four swerve groups, each with drive/angle/encoder.
Example:
  configure terminal
  group swerve_front_left
  add device "Drive Motor (swerve-front-left)"
  add device "Angle Motor (swerve-front-left)"
  add device "Encoder (CANCoder) (swerve-front-left)"
  exit
  group swerve_front_right
  add device "Drive Motor (swerve-front-right)"
  add device "Angle Motor (swerve-front-right)"
  add device "Encoder (CANCoder) (swerve-front-right)"
  exit
  group swerve_back_left
  add device "Drive Motor (swerve-back-left)"
  add device "Angle Motor (swerve-back-left)"
  add device "Encoder (CANCoder) (swerve-back-left)"
  exit
  group swerve_back_right
  add device "Drive Motor (swerve-back-right)"
  add device "Angle Motor (swerve-back-right)"
  add device "Encoder (CANCoder) (swerve-back-right)"
  exit

Example: Shooter + Feeder (2 flywheels + feeder)
Purpose: Shooter group for coordinated testing.
Example:
  configure terminal
  device "Feeder Motor"
  set vendor CTRE
  set role feeder
  exit
  device "Flywheel Motor (Leader)"
  set vendor CTRE
  set role flywheel
  exit
  device "Flywheel Motor (Follower)"
  set vendor CTRE
  set role flywheel
  exit
  group shooter
  add device "Feeder Motor"
  add device "Flywheel Motor (Leader)"
  add device "Flywheel Motor (Follower)"
  bind LY analog
  exit

Example: Intake + Pivot
Purpose: Separate intake and pivot control.
Example:
  configure terminal
  device "Fuel Intake Motor"
  set vendor REV
  set role intake
  exit
  group intake
  add device "Fuel Intake Motor"
  bind A toggle 1
  exit
  device "Pivot Intake Motor"
  set vendor REV
  set role pivot
  exit
  device "Pivot Intake Follower"
  set vendor REV
  set role pivot
  exit
  group intake_pivot
  add device "Pivot Intake Motor"
  add device "Pivot Intake Follower"
  bind B toggle 1
  exit

Example: Climber
Purpose: One device with a hold binding.
Example:
  configure terminal
  device "Climb Motor"
  set vendor CTRE
  set role climb
  exit
  group climb
  add device "Climb Motor"
  bind RB hold 1
  exit

Example: Sensor-Only Validation
Purpose: Group sensors for presence checks.
Example:
  configure terminal
  device "IMU (Pigeon2)"
  set vendor CTRE
  set role imu
  set tags ["imu","swerve"]
  exit
  device "Encoder (CANCoder) (swerve-front-left)"
  set vendor CTRE
  set role encoder
  set tags ["encoder","swerve-front-left"]
  exit
  device "Encoder (CANCoder) (swerve-front-right)"
  set vendor CTRE
  set role encoder
  set tags ["encoder","swerve-front-right"]
  exit
  device "Encoder (CANCoder) (swerve-back-left)"
  set vendor CTRE
  set role encoder
  set tags ["encoder","swerve-back-left"]
  exit
  device "Encoder (CANCoder) (swerve-back-right)"
  set vendor CTRE
  set role encoder
  set tags ["encoder","swerve-back-right"]
  exit
  group sensors
  add device "IMU (Pigeon2)"
  add device "Encoder (CANCoder) (swerve-front-left)"
  add device "Encoder (CANCoder) (swerve-front-right)"
  add device "Encoder (CANCoder) (swerve-back-left)"
  add device "Encoder (CANCoder) (swerve-back-right)"
  exit

Example: Minimal Bench Test (Single Motor)
Purpose: Quick bench setup with one device.
Example:
  configure terminal
  device "Test Motor 1"
  exit
  group bench
  add device "Test Motor 1"
  bind LY analog
  exit

Example: Mixed Vendors (REV + CTRE)
Purpose: Two groups split by vendor.
Example:
  configure terminal
  group rev_motors
  add device "Angle Motor (swerve-front-left)"
  add device "Angle Motor (swerve-front-right)"
  exit
  group ctre_motors
  add device "Drive Motor (swerve-front-left)"
  add device "Drive Motor (swerve-front-right)"
  exit

Example: Duplicate Labels (Disambiguate)
Purpose: Split repeated labels using module tags.
Example:
  configure terminal
  group swerve_front_left
  add device "Drive Motor (swerve-front-left)"
  exit
  group swerve_front_right
  add device "Drive Motor (swerve-front-right)"
  exit

Example: Binding Cleanup
Purpose: Remove bindings from a group.
Example:
  configure terminal
  group shooter
  no bind
  exit

Example: Save and Reuse
Purpose: Save a config and reload it later.
Example:
  save unified-config data\bringup_system.json
  merge config data\bringup_system.json

Appendix: Full Example Script (2026 Robot-Style)
Purpose: Provide a complete batch script that recreates a full config.
Example:
  configure terminal
  device "Encoder (CANCoder) (swerve-back-left)"
  exit
  device "Encoder (CANCoder) (swerve-back-right)"
  exit
  device "Encoder (CANCoder) (swerve-front-left)"
  exit
  device "Encoder (CANCoder) (swerve-front-right)"
  exit
  device "IMU (Pigeon2)"
  exit
  device "Climb Motor"
  exit
  device "Fuel Intake Motor"
  exit
  device "Pivot Intake Motor"
  exit
  device "Pivot Intake Follower"
  exit
  device "Feeder Motor"
  exit
  device "Flywheel Motor (Leader)"
  exit
  device "Flywheel Motor (Follower)"
  exit
  device "Drive Motor (swerve-back-left)"
  exit
  device "Angle Motor (swerve-back-left)"
  exit
  device "Drive Motor (swerve-back-right)"
  exit
  device "Angle Motor (swerve-back-right)"
  exit
  device "Drive Motor (swerve-front-left)"
  exit
  device "Angle Motor (swerve-front-left)"
  exit
  device "Drive Motor (swerve-front-right)"
  exit
  device "Angle Motor (swerve-front-right)"
  exit
  group swerve_front_left
  add device "Drive Motor (swerve-front-left)"
  add device "Angle Motor (swerve-front-left)"
  add device "Encoder (CANCoder) (swerve-front-left)"
  exit
  group swerve_front_right
  add device "Drive Motor (swerve-front-right)"
  add device "Angle Motor (swerve-front-right)"
  add device "Encoder (CANCoder) (swerve-front-right)"
  exit
  group swerve_back_left
  add device "Drive Motor (swerve-back-left)"
  add device "Angle Motor (swerve-back-left)"
  add device "Encoder (CANCoder) (swerve-back-left)"
  exit
  group swerve_back_right
  add device "Drive Motor (swerve-back-right)"
  add device "Angle Motor (swerve-back-right)"
  add device "Encoder (CANCoder) (swerve-back-right)"
  exit
  group shooter
  add device "Feeder Motor"
  add device "Flywheel Motor (Leader)"
  add device "Flywheel Motor (Follower)"
  exit
  group flywheel
  bind LY analog
  exit

Troubleshooting
Purpose: Common errors and fixes.
- Invalid config: file is not bridgeConfig-only or unified bringup_system.json.
- Paths with backslashes: use quotes or forward slashes.
- No CAN IDs shown: labels are the identifiers; CAN IDs live in bringup_system.json.

Tradeoffs
Purpose: Explain design choices.
- bridgeConfig-only outputs are compact but do not carry profiles or topology.
- Unified bringup_system.json preserves shared data but is larger.

Future Extensions
Purpose: Planned improvements.
- Batch command to set device metadata in one line.
