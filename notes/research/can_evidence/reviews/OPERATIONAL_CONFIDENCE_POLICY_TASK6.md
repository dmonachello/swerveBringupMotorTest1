# Operational Confidence Policy

## Purpose

Purpose: define what “high confidence” means in practice for the CAN device evidence system so later implementation can prefer honest uncertainty over confident-looking wrong answers.

This is a Task 6 preparation artifact for:

- `docs/TASK_LIST_CAN_EVIDENCE_SOURCE_PREP.md`
- `docs/FEATURE_SPEC_CAN_DEVICE_EVIDENCE_SOURCE_CONTRACTS.md`

## Core Principle

The system should be conservative.

It is better to emit:

- `unknown`
- `inconclusive`
- `conflicted`

than to emit a confident wrong statement about:

- device existence
- operability
- identity/mapping

## Practical Meaning Of High Confidence

First-pass `high confidence` should mean:

- the conclusion is supported by one strong source with little contradiction, or
- the conclusion is supported by multiple independent sources that agree, and
- there is no strong conflicting evidence that would require downgrading the claim

High confidence does **not** mean certainty.

It means the system has enough source quality and agreement that an operator can act on the conclusion without the result being treated as a guess.

## Confidence Posture By Question

## 1. Existence

Preferred behavior:

- use `present` or `absent` only when the source quality justifies it
- use `unknown` when evidence is stale, weak, contradictory, or device-class-limited

High-confidence existence examples:

- active vendor probe directly fails on a supported device class and console evidence agrees
- manual stimulus-response strongly confirms the intended target exists and responds

Low-confidence existence examples:

- passive traffic seen but no active/manual confirmation
- one weak source says “missing” but the device class is known to be ambiguous

## 2. Operability

Preferred behavior:

- require stronger evidence than existence for positive healthy claims
- allow strong negative claims when direct failure evidence is timely and specific
- use `degraded` or `unknown` instead of overclaiming healthy operation

High-confidence operability examples:

- correct manual stimulus-response with expected telemetry
- supported active probe shows healthy communication and no strong negative console evidence

High-confidence negative operability examples:

- repeated specific vendor/HAL timeout behavior
- manual test produces no response or degraded/intermittent response

## 3. Identity/Mapping

Preferred behavior:

- be the most conservative here
- do not infer correct mapping from passive presence alone
- require stimulus-response or explicit wrong-device evidence for strong mapping claims

High-confidence identity examples:

- intended target responds during manual test and no wrong device responds
- wrong device or wrong branch responds during manual test

Low-confidence identity examples:

- a device appears present on the bus
- an active probe succeeds but no command/response evidence exists

## When `unknown` Is Preferred

The system should prefer `unknown` when:

- the source is stale
- a source is not strong enough for the question being asked
- device-class semantics are known to be weak
- two strong sources disagree
- a broad bus-health problem could explain several device-local symptoms
- the observation window is incomplete or not aligned
- operator observation is uncertain

## Most Dangerous False Positives

These should be avoided most aggressively.

## 1. False positive healthy operability

Bad claim:

- “device is working correctly”

when the device is only present on the bus or only weakly responding.

Why it is dangerous:

- it can send the operator away from a still-broken mechanism

## 2. False positive correct identity/mapping

Bad claim:

- “the right device is responding”

when the wrong motor, wrong controller, or wrong branch actually responds.

Why it is dangerous:

- it can hide configuration or wiring mistakes that manual testing is supposed to reveal

## 3. False positive single-device root cause during broad bus isolation

Bad claim:

- “Spark is the fault”

when multiple device families are failing because the roboRIO is isolated from the CAN bus.

Why it is dangerous:

- it misdirects troubleshooting to the wrong component

## More Acceptable False Negatives

These are still undesirable, but more acceptable than the false positives above.

- saying `unknown` when a device is actually healthy
- saying `unknown` when mapping is actually correct
- delaying a positive claim until a manual test confirms it

This is the intended system bias.

## Confidence Downgrade Rules

A result should be downgraded when:

- a strong source conflicts with another strong source
- the result depends on one broad/generic message rather than one specific message
- the device class is only conservatively supported
- the system-level bus health is poor enough that device-local claims become less trustworthy
- the observation window is old or incomplete

Recommended downgrade path:

- `high` -> `medium`
- `medium` -> `low`
- `low` -> `unknown`

## First-Pass Confidence Bands

Recommended first-pass bands:

- `high`
  - strong direct evidence or strong multi-source agreement
- `medium`
  - useful evidence, but with some ambiguity or incomplete corroboration
- `low`
  - weak hint only
- `unknown`
  - not enough evidence for a responsible claim

## Current Recommendation

The first implementation should be intentionally conservative.

The system should:

- prefer `unknown` over optimistic `present` or `operable`
- prefer `degraded` over healthy when strong negative evidence exists
- require the most evidence for strong identity/mapping claims
- require broad-fault cases to stay broad until evidence localizes them

## What This Unlocks

This policy gives the later implementation specs a practical rule set for:

- source result scoring
- confidence downgrade logic
- ambiguity handling
- operator-surface wording

Without this policy, the system is likely to sound more certain than the evidence deserves.
