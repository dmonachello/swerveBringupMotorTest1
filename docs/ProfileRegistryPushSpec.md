# Profile Registry Push (TCP UI Command) – Spec

## Purpose
Enable explicit, TCP-based delivery of the full device/profile registry to the robot, with strict validation, staged apply, and no implicit apply.

## Scope

Includes:
- New TCP UI command for registry apply
- CLI commands to push registry and full config
- Staged apply pipeline (integrity -> validation -> apply -> verify)
- Strict reject-on-error behavior
- Detailed status reporting per stage

Excludes:
- NT command transport (TCP only)
- Persistent storage on roboRIO filesystem (future extension)

## Terminology

- Registry: devices + profiles + default_profile from bringup_system.json
- Full config: entire bringup_system.json including bridgeConfig
- Apply: update in-memory robot state only

## Validation Model

Validation occurs in two places:

1. Host-side validation
   - Performed before sending
   - Improves UX and catches errors early
   - Does not imply trust

2. Robot-side validation
   - Performed again on receipt
   - Authoritative for apply
   - Must make no assumptions about host correctness

The robot must treat all incoming data as untrusted until validation completes successfully.

## Unknown Field Handling

- Unknown fields are allowed
- They must not cause validation failure solely for being unknown
- They are passed through and preserved where possible
- Validation applies only to required known fields and invariants

## User-Facing CLI

### Registry push
profiles push <path> [--activate <profile>]

Behavior:
- Reads JSON file locally
- Sends full JSON over TCP as a single UI command
- Robot runs staged apply pipeline
- If --activate is provided, activation occurs only after all stages pass
- If any stage fails, no success is reported

### Full config push
config push <path> [--activate <profile>]

Behavior:
- Executes profiles push first
- If registry apply fails, stop
- If registry apply succeeds, run existing import config <path> for groups/bindings

Important:
- This is NOT atomic across both steps
- If import config fails, registry remains applied

## TCP UI Command

Command name (TCP only):
profilesApply

Args JSON:
{
  "registryJson": "<raw bringup_system.json contents>",
  "activateProfile": "<profileName>"
}

Rules:
- Must be sent over TCP
- Reject if invoked over NT
- registryJson is raw JSON string for hash consistency

## Apply Pipeline

Registry/config push uses a staged apply pipeline. Each stage must pass before the next stage begins.

### Stage 1: Transfer Integrity Check
- Verify payload completeness and integrity (CRC or equivalent)
- Fail -> reject immediately

### Stage 2: Content Validation
Reject if any of the following fail:

- JSON parse fails
- schema_version mismatch
- data_version missing/empty
- data_hash missing/empty
- data_hash mismatch
- profiles missing/empty
- devices missing/empty
- Duplicate device labels
- Invalid device references in profiles
- Duplicate labels within a profile
- activateProfile invalid

Unknown fields are ignored (passthrough).

Fail -> reject immediately

### Stage 3: Apply
- Replace in-memory registry atomically
- Rebuild internal structures

No file persistence.

### Stage 4: Post-Apply Verification
- Verify internal consistency
- Verify active profile validity
- Confirm system is usable

Fail -> report failure (no success reported)

## Success Condition

Success is defined as:
- All pipeline stages pass

## Failure Condition

If any stage fails:
- Stop processing
- Report failing stage and reason
- Do not report success

## Activation Semantics

- If --activate is provided:
  - Activation occurs only after all stages pass
  - Activation is part of the same apply sequence

- If --activate is NOT provided:
  - Active profile remains unchanged
  - default_profile is updated in memory only

No implicit activation ever occurs.

## Status Reporting

The robot must report results for each stage.

Required stages:
- transfer integrity
- content validation
- apply
- post-apply verification

Each stage reports:
- pass/fail
- message

Machine-readable output example:
{
  "transferCheck": { "ok": true, "message": "" },
  "contentValidation": { "ok": true, "message": "" },
  "apply": { "ok": true, "message": "" },
  "postApplyCheck": { "ok": true, "message": "" },
  "overallOk": true,
  "activeProfile": "home_030226",
  "activated": true
}

Text output (success):
Profiles applied. devices=<N> profiles=<M> active=<profile>

On failure:
- overallOk = false
- failing stage identified
- reason included

## Error Codes

- CONFIG.INVALID
- CONFIG.PROFILE_REQUIRED
- NETWORK.NOT_CONNECTED
- EXECUTOR.NOT_SUPPORTED

## Transport Behavior

On:
- not connected
- timeout
- truncated payload
- non-TCP invocation

Behavior:
- return error
- do not modify state

## Compatibility

- No NT key changes
- Existing commands unchanged
- Older robot code will reject profilesApply

## Examples

Push registry and activate:
profiles push data\\bringup_system.json --activate home_030226

Push full config:
config push data\\bringup_system.json --activate home_030226

Validate after push:
validate profiles robot

## Tradeoffs

Pros:
- No redeploy required
- Explicit, safe apply
- Clear failure reporting

Cons:
- Large payload over TCP
- No persistence
- Requires updated robot code

## Future Extensions

- Persistent save/load
- Diff-based updates
- Versioned schema
- Dry-run validation mode
