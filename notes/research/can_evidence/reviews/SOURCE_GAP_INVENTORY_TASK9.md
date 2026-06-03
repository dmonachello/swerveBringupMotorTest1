# Source Gap Inventory

## Purpose

Purpose: explicitly list the current gaps that remain in each evidence source before detailed implementation of the full CAN device evidence system.

This is a Task 9 preparation artifact for:

- `docs/TASK_LIST_CAN_EVIDENCE_SOURCE_PREP.md`
- `docs/FEATURE_SPEC_CAN_DEVICE_EVIDENCE_SOURCE_CONTRACTS.md`

## Scope

This gap inventory is organized by source:

- passive visibility
- console diagnostics
- active vendor probe
- manual stimulus-response

It focuses on gaps that matter to:

- correctness
- explainability
- schema design
- validation

## Source 1: Passive Visibility Gaps

## Gap 1.1: explicit per-class freshness/absence thresholds are not fully pinned down

Why it matters:

- different device classes may go stale differently
- one generic threshold can overclaim absence

## Gap 1.2: unsupported/unknown device handling needs clearer promotion rules

Why it matters:

- unrecognized nodes already appear in the UI
- later analysis needs a stable way to distinguish expected vs unexpected visibility

## Gap 1.3: passive evidence is not yet normalized into the common source-result envelope

Why it matters:

- consumers still read source-specific fields rather than a standardized source result

## Gap 1.4: observer-placement effects are not yet part of first-pass single-observer interpretation

Why it matters:

- the roboRIO-isolated case shows how observer placement changes what “missing” means

## Source 2: Console Diagnostics Gaps

## Gap 2.1: parser coverage is incomplete

Known missing or not yet formalized families:

- `BUS_OFF_EVENT`
- `CAN_MESSAGE_STALE`

Why it matters:

- both families were important in the current test corpus

## Gap 2.2: message-family trust is not yet encoded as machine-readable policy

Why it matters:

- we reviewed meanings in notes, but the parser/runtime does not yet carry those trust semantics formally

## Gap 2.3: broad-vs-device-local interpretation is not yet enforced systematically

Why it matters:

- `HAL_CAN_RECEIVE_TIMEOUT` can be broad by itself
- some device-specific stack/reader context is needed to avoid overblaming one device

## Gap 2.4: repeated-message deduplication and aging behavior need implementation alignment

Why it matters:

- repeated stale or timeout spam can dominate results unless deduped and time-bounded correctly

## Source 3: Active Vendor Probe Gaps

## Gap 3.1: current work is still mid-integration

Why it matters:

- the active probe code exists in progress, but it is not yet a fully validated finished feature in the repo state

## Gap 3.2: device-class validation depth is uneven

Examples:

- `SparkMax` has stronger current evidence than `SparkFlex`
- `PDP`/`PDH` remain conservative classes

## Gap 3.3: identity/mapping claims from active probe remain inherently limited

Why it matters:

- direct API communication success does not prove the correct physical mechanism is the one that will respond

## Gap 3.4: standardized normalized source-result output is not yet the canonical external contract

Why it matters:

- current active-probe outputs still need to be aligned with the shared source-result envelope

## Source 4: Manual Stimulus-Response Gaps

## Gap 4.1: manual test results do not yet have a canonical implemented machine-readable record

Why it matters:

- we made the storage decision, but the implementation path does not yet exist

## Gap 4.2: outcome vocabulary now exists on paper but is not yet wired into the product

Why it matters:

- operators and code still need a shared result code path

## Gap 4.3: current test corpus lacks explicit wrong-device and wrong-branch cases

Why it matters:

- these are the highest-value identity/mapping cases
- they are not yet represented in our real validation set

## Gap 4.4: command window and observation window capture are not yet standardized in implementation

Why it matters:

- later cross-source correlation depends on precise timing windows

## Cross-Source Gaps

## Gap 5.1: shared schema/enums are not yet implemented

Why it matters:

- all preparation work assumes a common source-result envelope, but no canonical artifact exists yet

## Gap 5.2: combined analyzer does not exist yet

Why it matters:

- source semantics are now better defined, but no implementation yet reconciles them

## Gap 5.3: source result storage layer is not yet implemented as a formal subsystem

Why it matters:

- later consumers should read normalized results rather than raw source internals

## Gap 5.4: more recovery and degraded-state cases are still needed

Why it matters:

- current matrix is strong on missing/isolated cases
- it is weaker on degraded/intermittent/recovery behaviors

## Current Recommendation

Before detailed implementation is considered complete, the project should at minimum:

- formalize the missing console parser families
- implement the shared schema/enums
- implement source normalization outputs
- implement the manual result record path
- preserve or collect a few more non-binary validation cases

## Summary

The current prep work is strong enough to begin detailed feature and implementation spec work.

The main remaining risks are no longer “we do not know what we want.”

They are now implementation-facing:

- parser completeness
- schema implementation
- source normalization
- timing/window handling
- validation depth on more nuanced fault cases
