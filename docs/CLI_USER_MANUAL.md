CLI User Manual (Bringup Bridge CLI)

Purpose: Teach operators how to use the Bridge CLI to inspect, edit, and save bringup configs and tests.

## What This CLI Is
Purpose: Give a simple mental model of what the CLI does.

The Bridge CLI is a Windows-side tool for:
- Inspecting robot runtime groups and local configs.
- Editing per-profile groups and bindings.
- Authoring bringup tests without editing JSON.

It does not replace the topology tool. It consumes `bringup_system.json` and writes updates back when you save.

## Core Concepts
Purpose: Explain the few ideas you must remember.

- Labels are the only identifiers. Every device reference is a label string.
- Profiles define which device labels exist.
- Groups live under `bridgeConfig.byProfile.<profileName>`.
- Local edits are in memory until you save.
- `show config local-raw` shows the raw bridgeConfig data.

## Quick Start (Local-Only, No Robot)
Purpose: Get a minimal group edited and saved quickly.

Example:
```
python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt
configure terminal
profile home_030226
group motors
add device "SPARKMAX/NEO 25"
add device "SPARKMAX/NEO550 7"
add device "FALCON 9"
exit
save profiles data/bringup_system.json
end
```

Notes:
- Use quotes for labels with spaces.
- `save profiles` persists groups into `bringup_system.json`.

## Quick Start (Robot-Connected)
Purpose: Read and snapshot live robot groups.

Example:
```
python tools\can_nt\can_nt_bridge.py --cli --rio 172.22.11.2
connect
show groups
save config runtime_groups.json
```

Notes:
- `save config` captures runtime groups from the robot.
- Use `import config` to replace groups with a file.

## Modes and Prompts
Purpose: Show how the CLI indicates context.

Prompts:
- Exec: `bridge>` or `bridge-profile-<name>>`
- Config: `bridge(config-profile-<name>)#`
- Group: `bridge(config-profile-<name>-group-<name>)#`
- Device: `bridge(config-device-<name>)#`
- Test: `bridge(config-test-<name>)#`

Navigation:
- `configure terminal` enters config mode.
- `exit` goes up one level.
- `end` returns to exec mode.

## How to Choose a Profile
Purpose: Ensure groups are tied to the right profile.

Commands:
```
show profiles
profile <name>
show profile
```

Rules:
- Groups are stored under the active profile.
- If you do not select a profile, the CLI uses the default profile.

## Inspecting State
Purpose: Learn the inspection commands you will use constantly.

Common show commands:
- `show status`
- `show groups`
- `show group <name>`
- `show devices`
- `show device <name>`
- `show device registry <name>`
- `show bindings`
- `show runtime-state`
- `show config local-raw`
- `show config dirty`
- `show profiles`
- `show profile`
- `show tests`
- `show test <name>`
- `bindings show`
- `can-mappings show`

Notes:
- Use `--json` for machine-readable output.
- `show config local-raw` prints `bridgeConfig.byProfile`.
- `show config dirty` shows unsaved local changes.

## Creating and Editing Groups
Purpose: Teach the everyday workflow.

Create a group:
```
configure terminal
profile home_030226
group swerve_front_left
add device "Drive Motor (swerve-front-left)"
add device "Angle Motor (swerve-front-left)"
add device "Encoder (CANCoder) (swerve-front-left)"
bind controller0.leftY analog
exit
```

Modify a group:
```
configure terminal
profile home_030226
group swerve_front_left
no device "Encoder (CANCoder) (swerve-front-left)"
member "Drive Motor (swerve-front-left)" disable
bind controller0.leftY analog
exit
```

Save your changes:
```
save profiles data/bringup_system.json
```

## Saving and Files
Purpose: Explain what each save command does.

- `save profiles <path>`
  Writes `bringup_system.json` with updated `bridgeConfig.byProfile`.
- `save local-config <path>`
  Writes a bridgeConfig-only file for local reuse.
- `save config <path>`
  Captures runtime groups from the robot.
- `save unified-config <path>`
  Writes a full bringup_system.json with profiles + bridgeConfig.

Use `show config dirty` before you exit to avoid losing work.

## Test Authoring (No JSON)
Purpose: Create tests without editing `bringup_tests.json` directly.

Create a test:
```
configure terminal
test set default
test create MotorPulse
type button
device add "FALCON 9"
inputSource controller0.A
duty 0.2
termination time 1.5
end
write tests bringup_tests.json
```

Inspect tests:
```
show tests
show test MotorPulse
```

Limit switch termination:
```
termination limitswitch
limitswitch onHit pass
limitswitch id limitA
```

Notes:
- Validation rejects invalid `onHit` values and empty ids.
- Use `show test <name>` to infer CLI commands from current settings.
- Use `tests templates` to list available templates.
- Use `tests load template <name>` to load a template into the editor.

## Device Metadata Editing
Purpose: Explain when to use device mode.

Device edits apply to the loaded profiles. You must save afterward.

Rules:
- `device <label>` creates the device in the registry and adds it to the active profile.
- Labels must be unique across the entire registry.

Example (create a new CAN device):
```
configure terminal
profile home_030226
device "Drive Motor (swerve-front-left)"
set interface CAN
set manufacturer 5
set deviceType 2
set id 11
set vendor CTRE
set role "swerve drive"
set tags ["swerve","drive","front-left"]
exit
save profiles data/bringup_system.json
```

Notes:
- The CLI validates required fields when you create or edit a device.

Required fields by interface:
- CAN: `interface`, `manufacturer`, `deviceType`, `id`
- DIO: `interface`, `dio`, `invert`
- PWM: `interface`, `pwm`
- ANALOG: `interface`, `analog`

Supported `set` fields:
- `interface`, `manufacturer`, `deviceType`, `id`, `model`, `type`
- `dio`, `invert`, `pwm`, `analog`
- `attachments`, `terminator`
- `vendor`, `role`, `notes`, `tags`, `limits`

## Controller Bindings (bringup_bindings.json)
Purpose: Edit controller bindings without touching JSON.

Show bindings:
```
configure terminal
bindings show
bindings show controllers
bindings show bindings
bindings show axes
```

Add or edit controllers:
```
bindings controller add controller2 XBOX 2
bindings controller set controller2 port 2
bindings controller rename controller2 controller_op
bindings no controller controller_op
```

Add or edit bindings:
```
bindings binding add runTest controller1 button A hold
bindings binding set 3 mode edge
bindings binding delete 3
```

Add or edit axes:
```
bindings axis add leftDrive controller0 leftY invert on deadband 0.12
bindings axis set 2 deadband 0.08
bindings axis delete 2
```

Save or validate:
```
bindings save src/main/deploy/bringup_bindings.json
bindings validate
```

Notes:
- Controller names must exist before bindings/axes reference them.
- Indexes are 1-based and shown in `bindings show`.

## CAN Mappings (can_mappings.json)
Purpose: Edit manufacturer and device type lookup tables.

Show mappings:
```
configure terminal
can-mappings show
can-mappings show manufacturers
can-mappings show device-types
```

Edit entries:
```
can-mappings manufacturer set 21 NewVendor
can-mappings manufacturer delete 21
can-mappings device-type set 14 RangeSensor
can-mappings device-type delete 14
```

Save or validate:
```
can-mappings save src/main/deploy/can_mappings.json
can-mappings validate
```

## Validation
Purpose: Explain how to catch mistakes.

Validate the current local config:
```
validate config
```

Typical errors:
- Missing device entries in a group.
- Duplicate device labels in a profile.
- Invalid test parameters.
- Invalid device definitions (missing required interface fields).
- Invalid bindings or CAN mappings.

The validator reports profile and group context for missing device labels.

## Troubleshooting
Purpose: Common errors and fixes.

- `ERROR: Profile not selected`  
  Run `profile <name>` in config mode.

- Groups vanish after restart  
  You forgot to save. Run `save profiles data/bringup_system.json`.

- Exit prompts about unsaved changes  
  Run `show config dirty` and save profiles or tests.

- Device label not found  
  Verify the label exists in `bringup_system.json` for the active profile.

## Learning Path
Purpose: Suggested path for new users.

1. Run local-only CLI and list profiles.
2. Create a simple group and save it.
3. Inspect it with `show group` and `show config local-raw`.
4. Create a simple test and `write tests`.
5. Connect to a robot and compare `show groups` local vs robot.

## Reference Pointers
Purpose: Where to find deeper specs.

- Full command list: `docs/BRIDGE_CLI_FULL_SPEC.md`
- Test authoring tutorial: `docs/CLI_TEST_AUTHORING_USER_GUIDE.md`
- Profiles schema: `docs/bringup_profiles_schema.md`
