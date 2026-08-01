# Add a New Device

## Purpose

Explain how to extend the system when a new CAN device must be supported.

This guide covers three different cases:

- an existing manufacturer adds another motor
- an existing manufacturer adds a brand new device type
- a brand new manufacturer adds a brand new device

It is written for the system we are building now:

- profile-driven where possible
- discovery-library driven where possible
- additive and evidence-based
- intended to become user-extensible instead of requiring project authors to hand-edit code for every normal addition

## Design Goal

The long-term goal is:

- users add normal devices by editing config/profile data
- users do not need to rewrite UI code to add hardware
- new discovery methods plug into one shared source model
- vendor-specific support stays isolated behind explicit seams

The practical reality today is:

- some additions are already mostly data-driven
- some additions still require classifier or wrapper code
- the code is now structured so those changes are localized instead of spread across the UI

This guide is honest about both:

- what should be user-extensible
- what still requires developer work today

## Core Idea

Adding a device can affect up to six layers:

1. profile/config layer
2. passive discovery layer
3. enrichment layer
4. robot runtime layer
5. DSL and operator workflow layer
6. UI interpretation layer

The system is healthiest when a new device only changes the lowest necessary layer.

For example:

- another Spark MAX with a new CAN ID should usually be only a profile change
- a new CTRE motor model with the same device type might need profile plus possible classifier tuning
- a brand new vendor usually needs new robot-side and discovery-side support

## Quick Decision Matrix

### Case A: Existing Manufacturer, Existing Device Family, New Instance

Example:

- another Spark MAX
- another Falcon
- another PDP or CANcoder with a different ID

Typical outcome:

- profile/config only

Usually needed:

- add the device to `bringup_system.json`
- add it to topology/groups/tests as needed

Usually not needed:

- UI code changes
- passive discovery engine changes
- new source plugins

### Case B: Existing Manufacturer, Existing General Category, New Motor Model

Example:

- CTRE releases a new motor controller that still speaks the same family of CAN status traffic
- REV releases a new motor that still behaves like the current Spark family on CAN

Typical outcome:

- profile/config change
- maybe metadata/model mapping update
- maybe passive classifier tuning if the message families differ

May be needed:

- update model naming tables
- update family-role rules if status families changed
- update robot wrapper if telemetry fields or APIs differ

### Case C: Existing Manufacturer, Brand New Device Type

Example:

- existing vendor adds a gyro, sensor hub, or encoder family that is not just another motor

Typical outcome:

- profile/config change
- discovery-rule update
- likely robot wrapper/attachment work
- maybe enrichment update

Usually needed:

- new device-type routing and readable naming
- passive family classification for the new message families
- runtime attachment or snapshot support if the roboRIO should read it directly

### Case D: Brand New Manufacturer, Brand New Device

Example:

- a vendor never seen before in this repo

Typical outcome:

- real implementation work is required today

Usually needed:

- manufacturer mapping
- robot-side wrapper
- discovery classification work
- optional enrichment plugin
- tests and documentation

## The Six Extension Layers

## 1. Profile and Config Layer

## Purpose

Define that a device exists in a robot configuration and where it belongs in topology and workflows.

Main file:

- `src/main/deploy/bringup_system.json`

Typical fields:

- label
- manufacturer
- deviceType
- id
- model
- type
- topology placement
- group membership
- test membership

This is the first place to change for every new device.

### User-Extensible Status

This layer is already intended to be user-editable.

If a device is only another instance of a known family, this should be the only required change.

## 2. Passive Discovery Layer

## Purpose

Decide whether observed traffic counts as real passive evidence that a device is present.

Main library area:

- `tools/passive_discovery_poc/`

Important files:

- [classify.py](/c:/Users/dmona/swerve3/tools/passive_discovery_poc/classify.py)
- [models.py](/c:/Users/dmona/swerve3/tools/passive_discovery_poc/models.py)
- [sources.py](/c:/Users/dmona/swerve3/tools/passive_discovery_poc/sources.py)

Passive discovery does not just ask:

- did we see packets with this ID?

It asks:

- did we see recurring device-emitted status families for this device identity?

That means a new device may need no passive work, or it may need family classification work.

### User-Extensible Status

Today:

- adding another known device instance is already user-extensible
- adding a new protocol family is not fully user-extensible yet

The architecture now helps by isolating the work:

- source plugin if the traffic source is new
- classifier rule if the family pattern is new

### When You Need Passive Discovery Changes

You need passive discovery changes if:

- the vendor/device emits families not currently recognized
- the existing role heuristics mark the device traffic as `UNKNOWN`
- the device presence should be inferred from a new set of status families

Typical changes:

- update family-role rules in `classify.py`
- add metadata/model hints if necessary
- add regression fixtures and tests

## 3. Enrichment Layer

## Purpose

Add corroborating evidence that is not passive CAN traffic.

Examples:

- CTRE HTTP snapshot
- topology rows
- roboRIO console log parsing
- future vendor USB/HTTP diagnostics

Important files:

- [enrichment.py](/c:/Users/dmona/swerve3/tools/passive_discovery_poc/enrichment.py)
- [sources.py](/c:/Users/dmona/swerve3/tools/passive_discovery_poc/sources.py)

If a new device family has a vendor API outside CAN, this is where it should plug in.

### User-Extensible Status

Today:

- this is partially extensible by plugin pattern
- a truly new enrichment method still requires implementation work

The important improvement is:

- it no longer requires rewriting the Evidence tab
- it plugs in through `EnrichmentRecord`

## 4. Robot Runtime Layer

## Purpose

Allow the roboRIO Java bringup harness to instantiate and read/control the device directly.

Important for:

- manual tests
- full probe
- active lifecycle behavior
- runtime snapshots

Main code areas:

- `src/main/java/frc/robot/devices/...`
- `src/main/java/frc/robot/manufacturers/...`

If the robot must actively control or read the device, this layer matters.

If the device only needs passive discovery on the host, this layer may not need changes immediately.

### User-Extensible Status

Today:

- this is not yet fully user-extensible for a truly new vendor/device family

A new vendor or truly new device type usually still needs Java implementation work.

## 5. DSL And Operator Workflow Layer

## Purpose

Define whether the device can be tested through the Robot Diagnostic Test DSL and what external stimulus or operator action is required.

Important areas:

- [docs/SPEC_DSL_DEVICE_SIGNAL_INTERFACE.md](/c:/Users/dmona/swerve3/docs/SPEC_DSL_DEVICE_SIGNAL_INTERFACE.md)
- [docs/USER_GUIDE_ROBOT_TEST_DSL.md](/c:/Users/dmona/swerve3/docs/USER_GUIDE_ROBOT_TEST_DSL.md)
- [docs/SPEC_NON_MOTOR_DEVICE_TESTING_AND_DSL_INTERVENTION.md](/c:/Users/dmona/swerve3/docs/SPEC_NON_MOTOR_DEVICE_TESTING_AND_DSL_INTERVENTION.md)
- [src/main/java/frc/robot/tests/dsl/DslSignalRegistry.java](/c:/Users/dmona/swerve3/src/main/java/frc/robot/tests/dsl/DslSignalRegistry.java)
- [tools/common/robot_test_dsl/service.py](/c:/Users/dmona/swerve3/tools/common/robot_test_dsl/service.py)

This layer matters most for non-motor devices:

- encoders need a shaft/module rotation stimulus
- IMUs need a yaw/tilt stimulus
- ambiguous checks may need a human confirmation signal
- workflow scenarios must have matching regression coverage

### User-Extensible Status

Today:

- ordinary motor and controller tests are supported
- non-motor sensor tests need deliberate signal contracts and procedures

A new sensor family is not complete until DSL-visible signals, operator instructions, and regression coverage are defined.

## 6. UI Interpretation Layer

## Purpose

Render the unified evidence and runtime state without device-specific ad hoc UI logic.

Important host files:

- [passive_discovery_integration_service.py](/c:/Users/dmona/swerve3/tools/can_nt/passive_discovery_integration_service.py)
- [bringup_ui.py](/c:/Users/dmona/swerve3/tools/can_nt/bringup_ui.py)
- [live_topology_view.py](/c:/Users/dmona/swerve3/tools/can_topology/live_topology_view.py)

The current goal is:

- new devices should normally not require new UI code
- the shared evidence model should already be enough

### User-Extensible Status

Today:

- this is mostly where we want it
- normal additions should not require UI changes

If a new device requires UI changes, that is usually a sign the lower layers were not normalized enough.

## Case 1: Existing Manufacturer Adds Another Motor

## Purpose

Document the easiest and most common path.

Example:

- add another Spark MAX
- add another Falcon
- add another Kraken if it follows an already-supported CTRE motor family

### What You Change

Usually only:

- `bringup_system.json`

Possible additions:

- topology node/links
- group membership
- tests referencing the label

### What You Verify

1. the profile loads
2. the topology shows the new device
3. passive discovery shows the new device identity
4. runtime/manual/probe behave if the robot layer already supports that family

### What Should Not Be Necessary

- new UI code
- new source plugin
- new Evidence-tab section logic

### Failure Modes

If the device does not show up correctly:

- wrong manufacturer/deviceType/id in config
- device family is not actually the same as the existing one
- passive classifier does not recognize its status traffic
- robot-side wrapper differs from the older family

## Case 2: Existing Manufacturer Adds a New Motor Model

## Purpose

Handle the case where the vendor is known but the new model may not be a drop-in protocol equivalent.

Example:

- vendor keeps the same overall category but changes status message families
- vendor keeps the same manufacturer ID but adds a new controller mode or telemetry layout

### Minimum First Step

Try the simplest path first:

1. add the device to profile/config
2. capture passive traffic
3. see whether the current classifier already recognizes it

### Best Outcome

Best case:

- only metadata/model naming changes are needed

That means:

- the traffic families already match an existing supported family
- only the human-readable model name was missing

### If Classification Fails

Then do:

1. capture representative traffic
2. inspect family list in passive discovery output
3. identify recurring candidate status families
4. update `classify.py`
5. add a narrow regression fixture/test

### Robot-Side Considerations

If the new motor model needs different telemetry fields or API calls:

- add or adjust the robot-side wrapper
- update vendor attachment readers

### User-Extensible Goal

The target user experience is:

- most new models from existing supported motor families should require only profile/config changes
- at worst, a small classifier rule update by an advanced maintainer

## Case 3: Existing Manufacturer Adds a Brand New Device Type

## Purpose

Handle new sensors or controllers from an already-known vendor.

Example:

- a new gyro
- a new encoder family
- a new power/control accessory

### What Usually Changes

- profile/config
- readable metadata/model mapping
- passive classifier rules
- likely robot-side wrapper and attachment support

### Why This Is Harder

The manufacturer is known, but the semantics are not:

- new device type means new message families
- new telemetry fields
- maybe different health/probe expectations

### Recommended Process

1. add the device to config with the best-known manufacturer/deviceType/id
2. capture passive traffic
3. record family inventory and rates
4. classify device-emitted families
5. add robot-side support if direct control/telemetry is needed
6. verify Evidence-tab behavior without UI-specific hacks

### User-Extensible Goal

The system should let a user add the device to config immediately.

But full support for the new device type may still require:

- discovery rule updates
- robot-side support

That is acceptable as long as the work is localized and obvious.

## Case 4: Brand New Manufacturer and Brand New Device

## Purpose

Describe the most expensive path honestly.

### What Is Required Today

Usually all of these:

- manufacturer mapping
- readable model/type metadata
- passive discovery classification work
- possible new source plugin if the capture path is unusual
- robot-side wrapper if the robot must use the device directly
- optional enrichment plugin if the vendor has useful side-channel diagnostics

### Passive Discovery Side

You will likely need to:

- capture traffic
- determine recurring device-emitted families
- add classification rules
- add regression tests

### Robot Runtime Side

You will likely need to:

- add vendor library
- implement wrapper and telemetry attachment
- register manufacturer/device group

### User-Extensible Goal

A brand new manufacturer is not yet a pure end-user config-only action.

But the architecture should make the required changes obvious and bounded:

- config in one place
- discovery rules in one place
- enrichment plugin in one place
- robot wrapper in one place

## How to Decide Whether a New Source Plugin Is Needed

## Purpose

Separate “new device” from “new way of observing the device.”

A new source plugin is needed only if the observation method is new.

Examples that need a new source plugin:

- a new live CAN hardware interface
- a new offline capture file format
- a new vendor USB relay stream

Examples that do not need a new source plugin:

- another Spark on the same CAN sniffer
- another CTRE motor in the same `pcapng`
- a new device family visible through the same existing CANable or REV relay path

## How to Decide Whether a New Enrichment Plugin Is Needed

## Purpose

Separate passive presence from corroborating evidence.

A new enrichment plugin is needed if:

- the vendor exposes useful HTTP/USB/console/query information outside passive CAN
- you want to improve confidence or health using that source

Examples:

- CTRE HTTP enrichment
- roboRIO console log parser
- future vendor-specific USB query

## User-Extensible Target State

## Purpose

State clearly what “extensible by the user” should mean.

### Normal User-Extensible Additions

These should be config-only:

- another device of an already-supported family
- another device label/ID/topology position
- another group membership or test membership

### Advanced Maintainer Additions

These may require small localized support work:

- new motor model in an existing family
- new device type from an existing vendor
- new corroboration source

### Developer-Level Additions

These still require real implementation today:

- brand new manufacturer
- brand new robot-side vendor library integration
- brand new source transport

## Recommended Workflow for Any New Device

1. Add the device to profile/config first.
2. Capture passive traffic.
3. Check whether the current system already supports it.
4. If not, determine whether the gap is:
   - config only
   - classifier only
   - enrichment only
   - robot wrapper only
   - or multiple layers
5. Make the smallest layer changes necessary.
6. Add a regression test or capture fixture for the new support.
7. Verify the Evidence tab shows the device without one-off UI hacks.

## Acceptance Criteria

A new device addition is done only if:

- profile/config validates
- topology can place the device
- passive discovery either recognizes it or honestly reports the current evidence gap
- robot runtime support works if direct control/telemetry is required
- Evidence/Visibility surfaces do not require bespoke per-device UI logic

## Tradeoffs

- pure user-extensibility is realistic for known families, not yet for brand new vendors
- aggressive heuristic support can produce false positives if classifier rules are too loose
- forcing every new family through hardcoded UI logic would make extensibility worse, so the system should resist that

## Future Extensions

To improve user-extensibility further, the best next steps are:

- move more family classification into data/rule tables instead of hand-coded `if` logic
- make manufacturer and device-type metadata registry-driven
- make enrichment plugin registration easier for site-local extensions
- document a fixture-capture workflow for unsupported devices
- add a “new device bringup wizard” that tells the user which layer is missing
