CLI User Manual (Bringup Bridge CLI)

Purpose: Explain how to use the CAN bringup bridge CLI for local configs and robot control.

Overview
Purpose: Summarize what the CLI does.
- Manages bringup groups, device membership, bindings, and metadata.
- Supports local-only editing (no robot/CAN) or robot-connected runtime control.
- Reads and writes bridgeConfig-only files (non-redundant).
- Device labels are unique and shared across profiles and bridgeConfig.

Configuration Paths
Purpose: Explain the multiple ways to build and edit configs.
There is more than one valid path to configure the system. You can start
from profiles, from a CLI-only config, from the topology tool, or from the
sniffer. Many paths can feed into each other.

Path A: Topology Tool (profiles-first)
Purpose: Use the topology UI to define devices and layout.
Workflow:
- Edit bringup_profiles.json (device lists + diagram).
- Ensure labels are unique.
- Load in CLI with merge config and create groups.
- Save groups-only config.

Path B: CLI-Only (no profiles)
Purpose: Build a standalone bridgeConfig with devices and groups.
Workflow:
- Create devices in CLI (device <name>).
- Create groups and bindings.
- Save full bridgeConfig JSON.

Path C: Sniffer Bootstrap
Purpose: Use observed CAN traffic to seed a profiles file.
Workflow:
- Run sniffer and dump a profile.
- Rename labels to be unique and meaningful.
- (Optional) edit topology diagram.
- Load profiles in CLI and add groups.

Path D: Manual JSON Edit
Purpose: Edit bringup_profiles.json or bridgeConfig directly.
Workflow:
- Edit JSON by hand (labels, IDs, tags, limits).
- Validate.
- Load into CLI for group work.

Cross-Editing (mixing paths)
Purpose: Describe how data flows between tools.
- Topology edits → CLI groups (profiles are canonical).
- Sniffer profile → manual rename → topology refine → CLI groups.
- CLI-only config → export script → manual tweaks → re-run script.
- Robot runtime groups → save config → edit in CLI.

Quick Start (Local-Only)
Purpose: Run the CLI without robot or CANable.
Example:
  python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt
  merge config x.json
  show groups local
  configure terminal
  group swerve_front_left
  add device "Drive Motor (swerve-front-left)"
  exit
  save local-config x.json

Quick Start (Robot-Connected)
Purpose: Use live robot runtime groups.
Example:
  python tools\can_nt\can_nt_bridge.py --cli --rio 172.22.11.2
  connect
  show groups
  save config x.json

Modes
Purpose: Explain prompt modes and how to enter/exit.
- Exec mode: bridge>
- Config mode: bridge(config)#
- Group mode: bridge(config-group-<name>)#
- Device mode: bridge(config-device-<name>)#
- exit pops one mode; end returns to exec.

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
- show bindings [local|robot|both] [--json]
- show runtime-state [local|robot|both] [--json]

Config Commands
Purpose: Build and edit groups.
- group <name> / no group <name>
- selected-device <name>
- selected-mode <on|off>
- rename device <old> <new>
- merge config <path>
- import config <path>
- validate config [path]
- save local-config <path>
- save config <path>

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
- You must create a device entry first (device <name>) before add device.
  This applies in both local-only and robot-connected sessions.
- Batch scripts are linted before execution to ensure device entries appear
  before add device commands.

Validate Local Config
Purpose: Validate the current in-memory config without a file.
Example:
  validate config

Device Mode Commands
Purpose: Edit device metadata in local config.
- show
- set <manufacturer|deviceType|deviceId|vendor|role|notes|bus|tags|limits> <value>
- no <manufacturer|deviceType|deviceId|vendor|role|notes|bus|tags|limits>
Note:
- manufacturer and deviceType accept numeric IDs or names from can_mappings.json.
  Examples: set manufacturer CTRE, set deviceType MotorController.
- When a profiles file is loaded, device edits write back to profiles and require save profiles.

Config Files
Purpose: Define inputs/outputs and expected shape.
bridgeConfig-only file (when not using profiles):
  {
    "schemaVersion": 1,
    "generatedAt": null,
    "devices": [...],
    "groups": [...],
    "selectedDevice": { "device": "", "enabled": false }
  }
groups-only file (profiles-backed sessions):
  {
    "schemaVersion": 1,
    "generatedAt": null,
    "groups": [...],
    "selectedDevice": { "device": "", "enabled": false }
  }
Note:
- When writing configs, devices are listed before groups for consistency.
- Device names must be unique. Duplicate labels are invalid.

Profiles and bridgeConfig
Purpose: Clarify source of truth.
- Profiles (bringup_profiles.json) are the single source of truth for device labels.
- bridgeConfig.devices are auto-generated from profiles when loading a profiles file.
- Groups reference the same labels, so labels remain consistent across tools.
- The default_profile is used when generating bridgeConfig.devices.
- Profiles schema_version is 2 (see docs/PROFILE_SCHEMA_REFACTOR.md).

Config Save Formats
Purpose: Explain which files to save and why.
- Groups JSON (authoritative): save local-config <path>
  Use as the primary source of truth for groups and selectedDevice.
- Runtime bridgeConfig JSON (from robot): save config <path>
  Captures live runtime groups from the robot for later review or reuse.
- CLI script (derived): export cli-script <path>
  Convenience batch script generated from the current local config.
  Regenerate from JSON; do not hand-edit.
- Profiles JSON (authoritative for devices): save profiles <path>
  Writes bringup_profiles.json after device edits.

Usage Guidance
Purpose: Recommend a stable workflow.
- Use JSON as the canonical config and store it in version control.
- Generate scripts from JSON for quick rebuild or demos.
- Recreate a config by running the script, then save JSON:
  python tools\can_nt\can_nt_bridge.py --batch --script x_rebuild.txt --no-can --no-nt
  save local-config x.json

Manual CLI Batch Scripts
Purpose: Explain when and how to hand-write a batch script.
Batch scripts are just CLI command lists. You can hand-write them when you want a
human-readable sequence of steps, but the preferred flow is to export a script
from JSON and treat scripts as derived artifacts.
Guidance:
- Put all device definitions before any add device commands.
- If you are profiles-backed, start with: merge config <bringup_profiles.json>.
- Keep one command per line; avoid extra prompts or output lines.
Example:
  configure terminal
  device "Arm Motor"
  set manufacturer CTRE
  set deviceType MotorController
  set deviceId 42
  exit
  group arm
  add device "Arm Motor"
  bind LY analog
  exit
Run:
  python tools\can_nt\can_nt_bridge.py --batch --script arm_rebuild.txt --no-can --no-nt

Guided Walkthrough: Build a Full Config From Scratch
Purpose: Step-by-step guide to create a complete bridgeConfig.
This assumes a bridgeConfig-only session (no profiles loaded).

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
  set manufacturer CTRE
  set deviceType MotorController
  set deviceId 2
  set vendor CTRE
  set role "swerve drive"
  set tags ["swerve","drive","front-left"]
  exit

Example (sensor device):
  device "Encoder (CANCoder) (swerve-front-left)"
  set manufacturer CTRE
  set deviceType Encoder
  set deviceId 3
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
  validate config x.json

Step 6: Save the config
Purpose: Write a non-redundant bridgeConfig file.
Example:
  save local-config x.json

Step 7: Export a rebuild script (optional)
Purpose: Generate a replayable script for future rebuilds.
Example:
  export cli-script x_rebuild.txt

Step 8: Reuse the config
Purpose: Load and reuse in a future session.
Example:
  merge config x.json

Profiles-Backed Workflow (Canonical Labels)
Purpose: Use bringup_profiles.json as the single source of truth.
1) Edit profiles (labels must be unique). Use the topology tool or edit JSON.
2) Load profiles in the CLI:
   merge config data\bringup_profiles.json
3) Create groups using those labels.
4) Save groups-only config:
   save local-config groups.json
Notes:
- Device edits update the loaded profiles data and require save profiles to persist.
- The CLI derives devices from the default_profile.

Device Mode Examples
Purpose: Show how to create and fully define device entries (bridgeConfig-only sessions).

Example: Create a new device entry with all attributes
Purpose: Create a new device and set CAN identity fields.
Example:
  configure terminal
  device "Test Motor 1"
  set manufacturer REV
  set deviceType MotorController
  set deviceId 31
  set vendor REV
  set role "arm motor"
  set notes "bench test motor"
  set bus 0
  set tags ["arm","motor","test"]
  set limits {"fwdDio":0,"revDio":1,"invert":false}
  exit

Example: Update device metadata (decimal and hex)
Purpose: Demonstrate edits using decimal and hex.
Example:
  configure terminal
  device "Drive Motor (swerve-front-left)"
  set manufacturer 0x04
  set deviceType 2
  set deviceId 2
  set vendor CTRE
  set role "swerve drive"
  set tags ["swerve","drive"]
  exit

Example: Clear a device field
Purpose: Remove a field from the device entry.
Example:
  configure terminal
  device "Test Motor 1"
  no deviceType
  exit

Example: Create device first, then add to group
Purpose: Show preferred ordering for scripts.
Example:
  configure terminal
  device "Arm Motor"
  set manufacturer 5
  set deviceType 2
  set deviceId 42
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
  set manufacturer 4
  set deviceType 4
  set deviceId 19
  set vendor CTRE
  set role imu
  set tags ["imu","swerve"]
  exit
  device "Encoder (CANCoder) (swerve-front-left)"
  set manufacturer 4
  set deviceType 7
  set deviceId 3
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
  set deviceId 28
  set vendor CTRE
  set role feeder
  exit
  device "Flywheel Motor (Leader)"
  set deviceId 27
  set vendor CTRE
  set role flywheel
  exit
  device "Flywheel Motor (Follower)"
  set deviceId 23
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
  set deviceId 24
  set vendor REV
  set role intake
  exit
  group intake
  add device "Fuel Intake Motor"
  bind A toggle 1
  exit
  device "Pivot Intake Motor"
  set deviceId 22
  set vendor REV
  set role pivot
  exit
  device "Pivot Intake Follower"
  set deviceId 11
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
  set deviceId 60
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
  set manufacturer 4
  set deviceType 4
  set deviceId 19
  set vendor CTRE
  set role imu
  set tags ["imu","swerve"]
  exit
  device "Encoder (CANCoder) (swerve-front-left)"
  set manufacturer 4
  set deviceType 7
  set deviceId 3
  set vendor CTRE
  set role encoder
  set tags ["encoder","swerve-front-left"]
  exit
  device "Encoder (CANCoder) (swerve-front-right)"
  set manufacturer 4
  set deviceType 7
  set deviceId 12
  set vendor CTRE
  set role encoder
  set tags ["encoder","swerve-front-right"]
  exit
  device "Encoder (CANCoder) (swerve-back-left)"
  set manufacturer 4
  set deviceType 7
  set deviceId 6
  set vendor CTRE
  set role encoder
  set tags ["encoder","swerve-back-left"]
  exit
  device "Encoder (CANCoder) (swerve-back-right)"
  set manufacturer 4
  set deviceType 7
  set deviceId 9
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
  group bench
  add device "Test Motor 1"
  bind LY analog
  exit
  device "Test Motor 1"
  set manufacturer 5
  set deviceType 2
  set deviceId 3
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
  save local-config x.json
  merge config x.json

Appendix: Full Example Script (2026 Robot-Style)
Purpose: Provide a complete batch script that recreates a full config.
Example:
  configure terminal
  device "Encoder (CANCoder) (swerve-back-left)"
  set manufacturer 4
  set deviceType 7
  set deviceId 6
  exit
  device "Encoder (CANCoder) (swerve-back-right)"
  set manufacturer 4
  set deviceType 7
  set deviceId 9
  exit
  device "Encoder (CANCoder) (swerve-front-left)"
  set manufacturer 4
  set deviceType 7
  set deviceId 3
  exit
  device "Encoder (CANCoder) (swerve-front-right)"
  set manufacturer 4
  set deviceType 7
  set deviceId 12
  exit
  device "IMU (Pigeon2)"
  set manufacturer 4
  set deviceType 4
  set deviceId 19
  exit
  device "Climb Motor"
  set deviceId 60
  exit
  device "Fuel Intake Motor"
  set deviceId 24
  exit
  device "Pivot Intake Motor"
  set deviceId 22
  exit
  device "Pivot Intake Follower"
  set deviceId 11
  exit
  device "Feeder Motor"
  set deviceId 28
  exit
  device "Flywheel Motor (Leader)"
  set deviceId 27
  exit
  device "Flywheel Motor (Follower)"
  set deviceId 23
  exit
  device "Drive Motor (swerve-back-left)"
  set manufacturer 4
  set deviceType 2
  set deviceId 5
  exit
  device "Angle Motor (swerve-back-left)"
  set manufacturer 5
  set deviceType 2
  set deviceId 4
  exit
  device "Drive Motor (swerve-back-right)"
  set manufacturer 4
  set deviceType 2
  set deviceId 8
  exit
  device "Angle Motor (swerve-back-right)"
  set manufacturer 5
  set deviceType 2
  set deviceId 7
  exit
  device "Drive Motor (swerve-front-left)"
  set manufacturer 4
  set deviceType 2
  set deviceId 2
  exit
  device "Angle Motor (swerve-front-left)"
  set manufacturer 5
  set deviceType 2
  set deviceId 1
  exit
  device "Drive Motor (swerve-front-right)"
  set manufacturer 4
  set deviceType 2
  set deviceId 11
  exit
  device "Angle Motor (swerve-front-right)"
  set manufacturer 5
  set deviceType 2
  set deviceId 10
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
- Invalid config: file is not bridgeConfig or full profiles schema.
- Paths with backslashes: use quotes or forward slashes.
- No CAN IDs shown: set deviceId in device mode.

Tradeoffs
Purpose: Explain design choices.
- bridgeConfig-only outputs are compact but do not carry profiles or topology.
- Full profiles files preserve shared data but are larger.

Future Extensions
Purpose: Planned improvements.
- Batch command to set manufacturer/deviceType/deviceId in one line.
- Optional full profiles output mode on save/export.
