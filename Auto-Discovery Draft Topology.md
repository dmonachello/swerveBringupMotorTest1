# Auto-Discovery Draft Topology

  
#robotics
#bringup

## Purpose

  

Define a first-pass auto-discovery workflow that gives operators a useful starting topology/config draft for a new robot, then relies on the topology editor for correction and finalization.

  

This feature is explicitly **not** trying to fully and automatically generate a final trusted robot config.

  

The V1 goal is:

  

- discover enough from passive observation to avoid a blank starting point

- show uncertainty honestly

- let the operator correct the draft in the topology editor

  

## Product Goal

  

When the user connects the system to a new robot with little or no config, the system should be able to produce:

  

- a draft inventory of likely CAN devices

- likely vendor/type/ID guesses

- reasonable provisional labels

- confidence and evidence for each guess

- a topology-editor view where the draft can be reviewed and corrected

  

Success means:

  

- “this gave me a good starting point”

  

Not:

  

- “this generated a fully correct final config automatically”

  

## V1 Scope

  

V1 should focus on:

  

- passive capture from the host-side CAN sniffer

- first-pass host-side analysis

- saving a host-side discovery artifact

- loading that discovery artifact into the topology editor

- allowing node info to be corrected/fixed up

- exporting or applying a draft config skeleton after review

  

V1 should avoid:

  

- silent automatic mutation of the main config

- overclaiming exact mechanism roles

- pretending non-CAN devices are discoverable from passive CAN alone

- topology/wiring inference beyond what can be justified

  

## Core Workflow

  

## 1. Capture Discovery Snapshot

  

The user triggers a capture action from the UI.

  

Example button/command:

  

- `Capture Discovery Snapshot`

  

The system saves a host-side discovery file.

  

Example location:

  

- `tools/can_nt/logs/discovery_<timestamp>.json`

  

The capture should include:

  

- timestamp

- current selected profile context if any

- host observer/source identity

- passive CAN visibility/inventory data

- packet/rate/last-seen evidence

- optional runtime-state context if available

  

This artifact is the raw input for first-pass discovery analysis.

  

## 2. First-Pass Analysis

  

The host analyzes the capture and produces candidate discovered nodes.

  

For each candidate device, the system should try to infer:

  

- vendor

- likely device class/type

- CAN ID

- likely model where confidence is high enough

- provisional label

- confidence score

- evidence summary

  

The analysis should also classify each candidate as:

  

- high confidence

- medium confidence

- low confidence

- ambiguous

- unknown

  

## 3. Load Discovery Draft Into Topology Editor

  

The topology editor should be able to open the discovery artifact as a draft overlay or editable working draft.

  

The editor should show:

  

- discovered nodes

- confidence/uncertainty

- any known matches to configured devices

- unknown or ambiguous nodes

- missing configured devices if a profile context exists

  

V1 should treat discovery results as a proposed draft, not final truth.

  

## 4. Operator Fix-Up

  

The topology editor becomes the main correction surface.

  

The user should be able to:

  

- rename provisional labels

- correct vendor/type/model guesses

- mark a discovered node as matching an existing configured node

- create a new config node from a discovered node

- reject false positives

- merge duplicates

  

This is the key product assumption:

  

- discovery gets the user most of the way

- the editor is where correctness is established

  

## 5. Export / Apply Draft Config

  

After review, the user should be able to turn the corrected draft into config.

  

Preferred first-pass behavior:

  

- export a proposed config payload or patch

- or explicitly apply a reviewed draft to config

  

V1 should not silently rewrite the canonical config from discovery alone.

  

## Zero-Config New Robot Scenario

  

## Goal

  

Understand what the system can do when there is effectively no config.

  

## Step 1: Passive Capture With No Config

  

The host sniffer runs on a robot with no meaningful profile loaded.

  

From passive CAN observation alone, the system can often determine:

  

- which CAN IDs are present

- likely vendor families

- likely device classes for many devices

- talker rates / message presence

- which devices are active or quiet

- basic bus health signals

  

The system usually cannot know with confidence:

  

- semantic labels like `frontLeft Drive Motor`

- physical location on the robot

- exact mechanism role

- DIO/USB devices from CAN alone

- exact topology wiring

  

## Step 2: Draft Device Inventory

  

From that capture, the system should be able to draft nodes like:

  

- `CTRE FALCON CAN 9`

- `REV NEO/SPARK MAX CAN 25`

- `CTRE PDP CAN 20`

- `roboRIO`

  

That is already valuable because it converts “unknown robot” into a usable starting device list.

  

## Step 3: Topology Editor Review

  

The operator opens the discovery draft in the topology editor and sees:

  

- discovered nodes

- guessed identities

- confidence

- missing fields

- ambiguous guesses

  

This is the moment where the system transitions from passive discovery to human-guided configuration.

  

## Step 4: Active Bringup / Manual Tests

  

Once a draft config exists, normal bringup tools can refine it.

  

These can help resolve:

  

- which motor is which mechanism

- which semantic label belongs to which CAN ID

- whether a guessed model/type was correct

  

This means the real path to a valid config is:

  

- discover

- draft

- review

- test

- correct

- finalize

  

## V1 Conclusion For Zero-Config

  

Yes, the system should be able to get from “no config” to a strong draft starting point.

  

No, passive discovery alone should not claim to produce a final trusted config.

  

## Discovery Artifact

  

The discovery file should be a durable host-side artifact that can be:

  

- captured

- analyzed

- loaded into the topology editor

- edited/fixed up

- exported into config

  

The artifact should support both raw evidence and corrected metadata.

  

Suggested contents:

  

- capture metadata

- observer/source information

- raw discovered device inventory

- analyzed candidate nodes

- confidence/evidence per candidate

- optional user correction fields

- optional merge status

  

This makes the artifact useful across multiple sessions.

  

## Proposed V1 Data Model

  

Each discovered candidate should carry fields like:

  

- provisional label

- vendor guess

- type guess

- model guess

- CAN ID

- confidence

- evidence summary

- raw identity details

- match state

  

Example match states:

  

- `unmatched`

- `matchesConfigured`

- `configuredMissing`

- `ambiguous`

- `rejected`

  

## Provisional Labeling

  

V1 should use honest, mechanical provisional labels.

  

Examples:

  

- `CTRE FALCON CAN 9`

- `REV NEO CAN 25`

- `CTRE PDP CAN 20`

  

These are better than pretending to know semantic mechanism roles too early.

  

The topology editor can then support renaming to:

  

- `frontLeft Drive Motor`

- `intake roller`

- etc.

  

## Confidence Model

  

The feature must surface uncertainty clearly.

  

The system should prefer:

  

- simple confidence buckets

- short evidence notes

- explicit ambiguity markers

  

Examples:

  

- high confidence: vendor, class, and ID strongly match known traffic patterns

- medium confidence: vendor and ID are clear, class/model less certain

- low confidence: only partial identity evidence

- ambiguous: multiple plausible interpretations

  

## Editor Integration

  

The topology editor should be the main correction surface for V1.

  

This implies:

  

- discovery should load into the same editor model, not a parallel incompatible view

- corrected node data should be editable with the normal node edit flows

- the user should be able to promote discovered nodes into normal config objects

  

The shared contract must be common-code owned.

  

Do not build a separate discovery-only topology composition pipeline unless there is a documented adapter.

  

## What V1 Should Not Infer

  

V1 should not overclaim:

  

- physical mechanism names

- exact drive/angle roles

- non-CAN devices not visible from passive evidence

- electrical topology beyond observed evidence

- final correctness without operator review

  

## UX Principles

  

The user experience should optimize for:

  

- good starting draft

- transparent uncertainty

- easy correction

- explicit finalization

  

It should not optimize for:

  

- one-click “magic final config”

  

## Suggested UI Surfaces

  

Possible first-pass UI actions:

  

- `Capture Discovery Snapshot`

- `Open Discovery Draft`

- `Promote Discovery Draft To Config`

  

Possible topology editor surfaces:

  

- discovery overlay

- discovered-node list

- confidence/evidence panel

- accept/reject/match controls

  

## Implementation Phases

  

## Phase 1

  

Capture and save discovery snapshot.

  

Deliverables:

  

- host-side capture command

- saved discovery JSON artifact

- minimal analysis output

  

## Phase 2

  

Generate analyzed candidate nodes.

  

Deliverables:

  

- vendor/type/ID guesses

- provisional labels

- confidence/evidence

  

## Phase 3

  

Load discovery draft into topology editor.

  

Deliverables:

  

- discovery draft rendering

- mismatch/unknown visibility

- editable node info

  

## Phase 4

  

Promote reviewed draft into config.

  

Deliverables:

  

- export/apply reviewed draft

- explicit operator confirmation path

  

## Risks

  

- overconfident inference could create bad drafts

- discovery and config models could drift if not shared

- users may assume discovery output is final truth unless clearly labeled

- future multi-sniffer support could force rework if observer identity is not represented early

  

## Multi-Sniffer Future Compatibility

  

Even though this spec is for single-observer V1, the data model should already carry observer/source identity.

  

That way, later multi-sniffer support can extend the same discovery artifact and candidate model instead of replacing it.

  

Recommended early assumption:

  

- every observation belongs to a named observer/source

  

## Open Questions

  

SID_QUESTION: Should the discovery artifact contain both raw capture evidence and editor-corrected fields in one file, or should those be split into separate raw-vs-reviewed artifacts?

  

SID_QUESTION: Should “apply reviewed draft to config” directly update `bringup_system.json`, or should V1 only generate an export/patch that the user explicitly imports?

  

SID_QUESTION: What minimum set of inferred device classes is valuable enough for V1:

  

- motors

- PDP/PDH

- CANcoder

- pigeon

- roboRIO

  

SID_QUESTION: Should the topology editor load discovery as an overlay on an existing profile, or as a standalone draft workspace first?

  

## Tradeoffs

  

- A conservative draft is safer, but may require more manual correction.

- A more aggressive draft is faster, but risks misleading the operator.

- Single-artifact workflows are simpler, but may mix raw evidence and corrected truth too early.

  

## Future Extensions

  

- multiple CAN observer support

- observer visibility comparison

- ambiguity reduction using controlled robot-side tests

- suggested mechanism-role inference after active testing

- guided “new robot bringup from zero config” workflow