# Bringup DSL Semantic Model

## Purpose

Describe the semantic model of the robot bringup DSL as a whitepaper-style architectural topic rather than a command reference.

## Thesis

The bringup DSL is best understood not as a scripting language, a command macro system, a telemetry dashboard, or a device configuration interface, but as a language for expressing controlled experiments on a robot.

It models bringup as a sequence of domain-level experiments on a robot with verifiable results, rather than as a sequence of machine instructions or raw device commands.

Its meaning comes from the robot's configured structure, the scope in which control is permitted, the expected physical behavior of hardware, and the evidence used to verify outcomes.

The semantic unit of the DSL is therefore not a command, but an experiment with an expected and verifiable outcome.

## Why This Distinction Matters

Many adjacent tools in the robot ecosystem are organized around different centers of meaning.

- Configuration tools center on parameters, IDs, and persistent settings.
- Telemetry dashboards center on displaying current values and status.
- Manual control panels center on directly commanding one device or mechanism.
- Vendor diagnostics center on one device family and its vendor-specific semantics.
- General scripting tools center on ordered execution of low-level commands.

The bringup DSL is different.

It is centered on the execution of a controlled experiment and the judgment of its result.

That distinction is important because it explains why the language has to account for:

- named devices and groups
- control-scope legality
- observation windows
- expected physical response
- incomplete or conflicting evidence
- explicit outcome classification

In other words, this DSL does not merely ask, "What command should be sent?"

It asks, "What experiment should be run, under what conditions, against what target, and how will the outcome be verified?"

## Domain Basis

The DSL is grounded in a specific world model.

Its semantics come from several underlying domain models.

## Configured Robot Model

The robot is treated as a configured system of named devices, groups, profiles, and topology relationships.

The language assumes that a target is not merely a low-level address.

A target is a semantic object such as:

- `FALCON 9`
- `SPARKMAX/NEO 25`
- `pdp`
- `roborio`
- `active-group`

This means that the language refers to a configured robot world, not to anonymous endpoints.

The meaning of a program depends on the profile and structure of the robot it is applied to.

## Control-Scope Model

Not every device may be acted on at every moment.

The language assumes that control authority is scoped and stateful.

That scope may depend on:

- whether the robot is enabled
- whether a lifecycle session is active
- whether a device is in the active group
- whether the current workflow permits the action

As a result, a DSL action does not simply mean "send output."

It means "attempt this action within the currently valid and safe control scope."

That makes legality part of semantics, not just implementation detail.

## Physical-Behavior Model

The language is grounded in expected physical behavior.

Its meaning depends on the fact that:

- motors rotate
- current rises or falls
- sensors change
- mechanisms move
- infrastructure devices provide runtime and bus evidence

This means the DSL is not fundamentally about software state transition alone.

It is about commanded physical effect and observed physical response.

The same command has different semantic value depending on whether the physical system responds as expected.

## Evidence Model

The domain assumes that truth is established through evidence, not through command issuance alone.

The language lives in a world where multiple evidence sources may contribute to the interpretation of an experiment.

Examples include:

- robot-local runtime state
- active probe results
- passive CAN visibility
- console warnings
- manual observations
- enrichment or corroboration sources

These sources may be:

- fresh
- stale
- partial
- conflicting
- unavailable

That makes the DSL more than a command language.

It is a language for experiments whose outcomes must be verified through evidence.

## Workflow Model

Bringup is procedural.

Operators do not merely issue isolated commands.

They typically:

1. select a target
2. activate the correct scope
3. run an action
4. observe the response
5. judge the outcome
6. decide what to do next

The DSL captures that operational workflow.

It is therefore a language for structured bringup procedure, not a thin wrapper over transport commands.

## What a DSL Program Means

A program in this DSL denotes an ordered set of domain-level experiments over a configured robot.

Each experiment has meaning in terms of:

- target selection
- permitted control scope
- applied action
- observation window
- expected behavior
- evidence-based evaluation
- structured result

This is the key semantic distinction.

A statement in the DSL is meaningful not because it calls a low-level function, but because it participates in a controlled experiment with a verifiable outcome.

## The Semantic Unit

The most important semantic idea in this DSL is that the command is not the primary unit of meaning.

The primary unit of meaning is the experiment.

That experiment typically contains:

- a domain target
- a safe action
- an observation phase
- an expected outcome
- a verification step

This leads to the most concise description of the language:

> The semantic unit of the bringup DSL is not a command, but an experiment with an expected and verifiable outcome.

## What It Is Not

The DSL should not be confused with several nearby categories.

It is not:

- a general-purpose programming language
- a raw command transport protocol
- a parameter configuration format
- a vendor-specific diagnostics interface
- a pure assertion language
- a telemetry dashboard description language

Those systems may coexist with this DSL and may be used by it, but they do not define its meaning.

The bringup DSL is narrower and more domain-specific.

It exists to encode operational experiments over a robot system.

## Lifecycle Reuse

Although the language is rooted in bringup, it is not useful only during initial bringup.

The same domain-level experiment can serve multiple lifecycle roles.

## Initial Bringup

An experiment may first be used to prove that a new robot or subsystem behaves correctly at first activation.

Examples include:

- confirming that a motor spins under controlled scope
- confirming that a sensor reports plausible data
- confirming that a group of devices can be safely activated and observed

## Regression Verification

Once a subsystem is known to work, the same experiment can be rerun after:

- code changes
- wiring changes
- hardware replacement
- configuration updates
- repairs

In that role, the experiment becomes a regression test.

Its purpose is no longer initial discovery, but confirmation that previously verified behavior still holds.

## Troubleshooting

When a subsystem is suspected to be faulty, the same experiment can be reused as a troubleshooting procedure.

In that role, the experiment helps isolate:

- whether a target still responds
- whether the evidence now differs from a known-good result
- whether the failure appears local, scoped, stale, or conflicting

This makes the DSL especially valuable because it preserves operational knowledge in reusable form.

The same test can begin its life as bringup, continue as regression, and later serve as structured troubleshooting.

The lifecycle idea can be summarized like this:

> The same DSL experiment can serve three lifecycle roles: initial bringup, later regression verification, and focused troubleshooting.

## Why a DSL Is Appropriate

A DSL is appropriate here because the domain has its own stable concepts that are richer than raw API calls.

Those concepts include:

- named robot devices
- groups and profiles
- controlled scope and lifecycle state
- physical action and response
- evidence-backed verification
- structured operator-facing results

If these concepts are expressed only through low-level scripting or ad hoc UI actions, the system loses:

- clarity
- repeatability
- reusability
- auditable intent
- lifecycle continuity

The DSL preserves those concepts directly.

It lets the system describe what is being tested, why it is being tested, how it is being verified, and what result was obtained.

## Contrast With Other Tools

The most useful contrast is not syntax, but semantic center.

- A configuration app asks: what values should this device store?
- A dashboard asks: what values should be shown now?
- A manual control panel asks: what command should be sent now?
- A vendor diagnostic app asks: what does this vendor-specific device report now?
- A general script asks: what sequence of operations should execute?

The bringup DSL asks:

- what experiment should be run on this robot component
- under what controlled scope
- with what expected physical behavior
- and how will the result be verified

That is the distinguishing idea.

## Practical Implications

Viewing the DSL through this semantic model has several design implications.

- The language should remain profile-aware and target named domain objects.
- Safety and control scope should remain first-class semantics.
- Verification should not be optional decoration; it is central to meaning.
- Evidence freshness and conflict handling matter because experiments are judged, not merely executed.
- Results should remain structured and reusable across bringup, regression, and troubleshooting workflows.

These implications help explain why the language should not collapse into a generic command runner.

## Tradeoffs

This semantic model has advantages and costs.

Advantages:

- captures domain intent directly
- supports repeatable and auditable procedures
- preserves operational knowledge across the robot lifecycle
- enables stronger troubleshooting and regression reuse

Costs:

- more contextual semantics than a simple command script
- dependence on configured profiles and scope state
- need for evidence interpretation rather than simple command acknowledgment
- greater care required when explaining results to operators

These tradeoffs are acceptable because the value of the language comes from domain meaning, not from minimal implementation complexity.

## Conclusion

The bringup DSL should be understood as a language for controlled robot experiments with verifiable outcomes.

Its semantics are grounded in the configured robot model, valid control scope, expected physical behavior, and the evidence used to judge whether that behavior occurred.

That makes it fundamentally different from command macros, dashboards, and vendor tools.

It also explains why the language remains useful beyond initial activation.

Once expressed in the DSL, an experiment can outlive bringup and become a regression test or a troubleshooting procedure.

This is the core idea:

> The bringup DSL models robot work as domain-level experiments with verifiable results, not as sequences of machine instructions.
