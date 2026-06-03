# Manual Test Outcome Vocabulary

## Purpose

Purpose: define the first-pass structured outcome vocabulary for manual stimulus-response tests such as right-click motor tests.

This is a Task 3 preparation artifact for:

- `docs/TASK_LIST_CAN_EVIDENCE_SOURCE_PREP.md`
- `docs/FEATURE_SPEC_CAN_DEVICE_EVIDENCE_SOURCE_CONTRACTS.md`

## Scope

This vocabulary is for the manual stimulus-response source.

It is intended to capture:

- machine-observed response
- operator-observed response
- identity/mapping outcomes
- limited ambiguity

It is not intended to encode a full diagnosis by itself.

## Design Rules

- Keep the list small enough to be used consistently.
- Prefer outcome codes over freeform prose.
- Separate outcome code from supporting details.
- Allow `unknown` or `uncertain` rather than forcing a false claim.
- Make identity/mapping failures explicit rather than burying them in notes.

## Recommended First-Pass Outcome Codes

## 1. `correct_response`

- Meaning:
  - the intended configured target responded as expected during the test window
- Typical use:
  - the correct motor moved
  - telemetry aligned with the commanded target
- Primary questions supported:
  - existence
  - operability
  - identity/mapping

## 2. `no_response`

- Meaning:
  - the intended target did not show an observable response during the test window
- Typical use:
  - no motion
  - no meaningful telemetry change
  - no visible response from the expected target
- Primary questions supported:
  - existence
  - operability

## 3. `wrong_device_response`

- Meaning:
  - some device responded, but it was not the intended configured target
- Typical use:
  - a different motor spun
  - a different controller or actuator appears to have responded
- Primary questions supported:
  - identity/mapping
  - operability

## 4. `wrong_branch_response`

- Meaning:
  - the response appeared on the wrong topology branch or wrong local region of the robot
- Typical use:
  - response observed in the wrong subsystem branch
  - evidence suggests a branch-level mapping or routing problem
- Primary questions supported:
  - identity/mapping

## 5. `intermittent_response`

- Meaning:
  - the intended target responded inconsistently during the test window
- Typical use:
  - starts and stops unpredictably
  - some commands work and others do not
  - visible flicker or inconsistent telemetry correlation
- Primary questions supported:
  - operability

## 6. `degraded_response`

- Meaning:
  - the intended target responded, but in a clearly reduced, abnormal, or suspicious way
- Typical use:
  - weak motion
  - delayed response
  - abnormal current or feedback behavior with some motion still present
- Primary questions supported:
  - operability

## 7. `operator_uncertain`

- Meaning:
  - the operator could not confidently determine what responded
- Typical use:
  - limited visibility
  - too much simultaneous activity
  - ambiguous physical observation
- Primary questions supported:
  - none directly
- Notes:
  - use this instead of guessing

## Optional Supporting Detail Fields

The outcome code should stay compact.

Supporting fields can carry more detail:

- `targetLabel`
- `observedLabel`
- `observedBranch`
- `commandKind`
- `commandValue`
- `preWindowStartMs`
- `commandStartMs`
- `commandEndMs`
- `postWindowEndMs`
- `operatorNotes`
- `machineEvidence[]`

## Example Shapes

## Correct Target Responded

```json
{
  "outcome": "correct_response",
  "targetLabel": "SPARKMAX/NEO 25",
  "observedLabel": "SPARKMAX/NEO 25",
  "commandKind": "manual_duty_test",
  "operatorNotes": "Correct motor spun in commanded direction."
}
```

## No Response

```json
{
  "outcome": "no_response",
  "targetLabel": "FALCON 9",
  "commandKind": "manual_duty_test",
  "operatorNotes": "No visible motion."
}
```

## Wrong Device Responded

```json
{
  "outcome": "wrong_device_response",
  "targetLabel": "FALCON 9",
  "observedLabel": "SPARKMAX/NEO 25",
  "commandKind": "manual_duty_test",
  "operatorNotes": "Spark motor moved instead of Falcon."
}
```

## Wrong Branch Responded

```json
{
  "outcome": "wrong_branch_response",
  "targetLabel": "FALCON 9",
  "observedBranch": "intake_branch",
  "commandKind": "manual_duty_test",
  "operatorNotes": "Response appeared in the wrong branch."
}
```

## Interpretation Notes

- `correct_response` is the strongest single manual-test outcome.
- `wrong_device_response` is extremely valuable because it directly supports identity/mapping failure.
- `wrong_branch_response` is a topology-aware special case and should remain distinct from plain wrong-device response.
- `no_response` should not automatically mean the device does not exist; it means the test did not produce the expected response.
- `operator_uncertain` should not be treated as negative evidence.

## Recommended Consumer Behavior

Manual-test consumers should:

- treat `correct_response` as strong positive evidence
- treat `wrong_device_response` and `wrong_branch_response` as strong identity/mapping negatives
- treat `intermittent_response` and `degraded_response` as strong operability negatives
- treat `no_response` as strong negative for operability but only moderate negative for existence unless corroborated by another source
- treat `operator_uncertain` as non-committal

## Open Follow-Up Questions

- Should direction-specific wrong-response cases need their own code later
- Should “responded only in one direction” be encoded separately from general degraded response
- Should “response required multiple retries” be a separate code or supporting detail only

## Current Recommendation

Use this seven-code vocabulary for the first implementation pass:

- `correct_response`
- `no_response`
- `wrong_device_response`
- `wrong_branch_response`
- `intermittent_response`
- `degraded_response`
- `operator_uncertain`
