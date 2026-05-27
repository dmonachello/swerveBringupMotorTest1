# Release 1.0 Readiness

## Purpose

Define the product, workflow, quality, and verification requirements to move from a strong internal/alpha-quality bringup system to a trustworthy 1.0 release.

## Big-Picture Assessment

The project already has the core ingredients of a real product:
- Robot-side bringup harness with controlled actuation.
- PC-side passive CAN diagnostics and evidence capture.
- CLI and GUI operator surfaces.
- Shared profile/config schema.
- Safety model with TCP ownership and stop-latch rules.
- Significant documentation and growing regression coverage.

The main 1.0 gap is no longer basic architecture. The main 1.0 gap is productization:
- One supported workflow.
- One supported setup path.
- Stable contracts.
- Stronger failure handling and recovery guidance.
- Clear feature maturity boundaries.
- Repeatable verification that gives teams confidence before an event.

## Definition Of 1.0

Purpose: set the bar for a first public or team-wide stable release.

A 1.0 release means:
- A new team member can install, validate, and use the system on a supported Windows laptop without code edits.
- A supported robot project can build/deploy with the documented WPILib toolchain.
- The standard bringup workflow is documented end-to-end and works reliably.
- Safety behavior under disconnect/disable/lock conflict conditions is documented and verified.
- TCP, NT, and config contracts are stable and tested.
- Operators can tell which features are supported, advanced, or experimental.

Not required for 1.0:
- Perfect UI polish.
- Every advanced reverse-engineering workflow fully matured.
- Support for every possible OS/toolchain combination.
- Full architectural decomposition of every remaining large file.

## What Is Still Lacking

## 1. Release Scope Is Not Yet Explicit Enough

Purpose: avoid shipping an impressive repo that still feels undefined.

The project needs a short 1.0 scope statement that says:
- Which surfaces are officially supported.
- Which workflows are considered standard.
- Which host OS and hardware assumptions are supported.
- Which features are advanced or experimental.

### Needed
- A `1.0 Scope` section in release docs.
- A supported environment matrix.
- A feature maturity table.

## 2. One Blessed Workflow Is Still More Important Than More Features

Purpose: reduce operator confusion and make the tool feel predictable.

There are many available paths today:
- Topology editor.
- CLI.
- Bringup Control UI.
- Validate/sync.
- Registry/config push.
- Profile activation on host vs robot.
- Tests authoring from multiple entry points.

For 1.0, there must be one canonical path that is documented as the default.

### The standard workflow should answer
1. How to create or edit a profile.
2. How to validate and sync it.
3. How to deploy robot code.
4. How to run the PC tool.
5. How to connect CLI/UI.
6. How to perform bringup.
7. How to capture evidence.
8. How to recover from common failures.

### Needed
- One official quick-start workflow.
- One official tests-authoring workflow.
- Clear de-emphasis of alternate paths in user docs.

## 3. Setup And Environment Verification Need To Be Boring

Purpose: make first-run success predictable.

The system still depends on several environment assumptions:
- Python version and packages.
- WPILib/JDK setup.
- Windows serial/CANable availability.
- Config file validity.
- NT/TCP runtime expectations.

### Needed
- One supported Python version range.
- One supported WPILib/JDK expectation.
- One install path for Windows.
- One environment doctor/smoke-check command that verifies:
  - Python version.
  - Required imports.
  - Canonical config validity.
  - Optional COM port discovery.
  - Basic CLI/bridge startup sanity.

## 4. Cross-Boundary Verification Is Not Strong Enough Yet For 1.0

Purpose: the system spans too many contracts to rely mainly on informal confidence.

Critical contracts include:
- Java robot command behavior.
- Python command/tool behavior.
- `bringup_system.json` schema and semantic rules.
- TCP UI protocol.
- NT key ownership and update behavior.
- CLI command semantics.

### Needed
- More protocol-level tests.
- More config lifecycle tests.
- More failure-path tests.
- Explicit parity checks for shared CLI/UI command behavior.
- A documented 1.0 verification matrix.

## 5. Failure Handling And Recovery Need To Be More Explicit

Purpose: teams need to trust behavior under ugly pit conditions, not just ideal ones.

Important 1.0 questions:
- What happens on TCP disconnect?
- What happens on stale session state?
- What happens on lock conflict?
- What happens when the PC tool is absent?
- What happens when NT diagnostics are stale or missing?
- What happens after robot reboot with an old client still running?

### Needed
- A failure modes and recovery guide.
- Tests for disconnect, handshake, stop-latch, disabled/E-stop, stale-state, and duplicate-seq behavior.
- Operator-visible messaging that says what failed and what to do next.

## 6. Feature Maturity Needs To Be Explicit

Purpose: avoid overpromising every tool in the repo equally.

Not all features are likely equally mature. 1.0 should distinguish:
- Supported core features.
- Advanced but supported features.
- Experimental features.

### Needed
A feature maturity table such as:
- Robot bringup harness: supported.
- Windows CAN bridge: supported.
- CLI core commands: supported.
- Bringup Control UI: supported.
- Topology editor: supported.
- PCAP/inventory diff: advanced but supported.
- Reverse-engineering helpers: experimental.

## 7. Config Lifecycle Clarity Still Needs More Operator Help

Purpose: prevent confusion between canonical, deploy, and runtime state.

This project has an intentionally strong config model, but it is still easy for users to confuse:
- `src/main/deploy/bringup_system.json`.
- `src/main/deploy/bringup_system.json`.
- Host-selected profile.
- Robot-active profile.
- In-memory pushed registry vs on-disk file state.

### Needed
- More visible source/path reporting in CLI and UI.
- Clear status output for canonical vs deploy vs robot runtime state.
- Strong warnings when a user is editing host-local state only.
- More operator docs emphasizing host vs robot context.

## 8. Operator Docs Need A Smaller Official Entry Path

Purpose: extensive docs are good, but 1.0 needs a curated operator-first path.

The repo already has many useful docs, but 1.0 requires a smaller "start here" set.

### Needed operator docs
- Quick Start.
- Setup.
- Standard Workflow.
- Troubleshooting / Recovery.
- Safety Model.
- CLI Reference.
- UI Guide.

### Needed maintainer docs
- Architecture.
- Command Handler Architecture.
- TCP UI Protocol.
- NT Contract.
- Profile/config schema docs.
- Release process.

## 9. Error Message And Recovery UX Still Need A Polish Pass

Purpose: 1.0 errors should be safe, specific, and actionable.

Error handling should consistently answer:
- What failed.
- Why it failed.
- Whether robot state changed.
- What the operator should do next.

### Needed
- A startup-failure pass for CLI/UI/bridge scripts.
- A config-validation message pass.
- A protocol-failure message pass.
- Consistent lock/handshake/disabled-state recovery hints.

## 10. Release Engineering Needs To Be Formalized

Purpose: a 1.0 release needs a process, not just a code snapshot.

### Needed
- Release checklist.
- Supported environment matrix.
- Known issues section.
- Versioning/release process expectations.
- Required smoke checks before tagging.
- Migration notes when config schema or command forms change.

## Top 1.0 Priorities

Purpose: identify the highest-value work that should gate 1.0.

1. Freeze and document one official operator workflow.
2. Make setup and smoke verification boring on supported Windows machines.
3. Strengthen contract/failure-path verification.
4. Clarify supported vs advanced vs experimental feature tiers.
5. Improve failure recovery documentation and operator messaging.
6. Make config source-of-truth and runtime state differences obvious.
7. Add release engineering discipline around tagging and verification.

## Release 1.0 Checklist

Purpose: provide a concrete pass/fail list for declaring 1.0.

### A. Scope And Support Envelope
- [ ] Supported surfaces are explicitly listed.
- [ ] Supported host OS and toolchain versions are explicitly listed.
- [ ] Supported hardware assumptions are explicitly listed.
- [ ] Experimental features are explicitly marked.
- [ ] Advanced-but-supported features are explicitly marked.

### B. Setup And Installation
- [ ] One official Windows install path is documented.
- [ ] One official run path for the PC tool is documented.
- [ ] Python dependency installation is accurate and current.
- [ ] WPILib/JDK expectations are accurate and current.
- [ ] One smoke-check or doctor command exists and is documented.

### C. Standard Workflow
- [ ] One canonical profile authoring workflow is documented.
- [ ] One canonical validate+sync workflow is documented.
- [ ] One canonical robot deploy workflow is documented.
- [ ] One canonical PC-tool bringup workflow is documented.
- [ ] One canonical evidence-capture workflow is documented.
- [ ] One canonical tests-authoring workflow is documented.

### D. Safety And Failure Handling
- [ ] TCP disconnect behavior is documented and verified.
- [ ] Handshake/lock behavior is documented and verified.
- [ ] Stop-latch behavior is documented and verified.
- [ ] Disabled/E-stop gating is documented and verified.
- [ ] PC-tool-absent behavior is documented and verified.
- [ ] Stale or missing NT diagnostics behavior is documented and verified.

### E. Contracts And Compatibility
- [ ] `docs/TCP_UI_PROTOCOL.md` is current and verified.
- [ ] `docs/NT_CONTRACT.md` is current and verified.
- [ ] Profile/config schema docs are current and verified.
- [ ] Host-vs-robot context rules are current and documented.
- [ ] Canonical-vs-deploy config workflow is current and documented.

### F. Automated Verification
- [ ] Focused Python unit tests cover current facade/transport boundaries.
- [ ] CLI regressions pass on supported Windows environment.
- [ ] Config validation tests cover common schema and semantic failures.
- [ ] Protocol tests cover handshake, lock conflict, send failure, and malformed input.
- [ ] Robot Java compile/build check passes with supported toolchain.
- [ ] At least one representative end-to-end bringup checklist pass is documented.

### G. Documentation
- [ ] Quick Start doc exists and is current.
- [ ] Setup doc exists and is current.
- [ ] Troubleshooting / recovery doc exists and is current.
- [ ] CLI user/reference docs are current.
- [ ] UI guide/help path is current.
- [ ] Release notes and known issues are prepared for 1.0.

### H. Product Hygiene
- [ ] Repo root is curated and free of confusing leftovers.
- [ ] Derived/generated artifacts are clearly identified.
- [ ] `.gitignore` covers local/generated noise appropriately.
- [ ] Canonical file locations are obvious to contributors and operators.

## Gap Analysis By Area

Purpose: summarize the current likely state versus 1.0 target.

| Area | Current Direction | 1.0 Gap |
| --- | --- | --- |
| Architecture | Strong and improving | Mostly adequate; focus now is product hardening |
| Command boundaries | Improving with new facade/executor split | Add more verification and maintain doc alignment |
| Safety model | Well-defined in docs | Needs broader failure-path testing and operator recovery docs |
| Setup | Better than before | Needs one boring install + doctor path |
| Workflow clarity | Many tools and paths exist | Needs one blessed happy path |
| Config lifecycle | Conceptually strong | Needs more operator-visible source/runtime clarity |
| Documentation depth | Strong | Needs a smaller official operator entry path |
| Regression mindset | Present | Needs broader contract and failure-path coverage |
| Release process | Emerging | Needs a formal 1.0 checklist and support envelope |

## Recommended Implementation Order

Purpose: focus on the work that most increases 1.0 confidence.

1. Define and publish the 1.0 support envelope.
2. Freeze one official operator workflow.
3. Add a setup doctor/smoke-check command and document it.
4. Expand protocol/config/failure-path test coverage.
5. Add a failure modes and recovery guide.
6. Improve config source/runtime visibility in CLI/UI.
7. Prepare release checklist, known issues, and environment matrix.

## Suggested 1.0 Deliverables

Purpose: convert the gap analysis into concrete artifacts.

- `docs/RELEASE_1_0_READINESS.md` (this document)
- `docs/QUICK_START.md` or equivalent official getting-started doc
- `docs/TROUBLESHOOTING_AND_RECOVERY.md`
- Supported environment matrix section in setup/release docs
- Feature maturity table in user-facing docs
- Windows doctor/smoke-check command or script
- Expanded protocol and failure-path automated tests
- 1.0 release checklist and known issues section

## Exit Decision

Purpose: make the release decision explicit.

Release 1.0 should be declared only when the project is no longer merely powerful for maintainers, but predictable for operators:
- easy to install
- clear to use
- safe under failure
- stable at its contracts
- verified with repeatable checks
