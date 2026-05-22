SPEC_STATUS: NOT_IMPLEMENTED

## Purpose
Define byte fingerprinting for CAN frames to identify which bytes change, how often they change, and provide a simple variation score per (mfg, type, id, apiClass, apiIndex).

## Scope
Includes:
- Live capture accumulation of per-byte change stats
- Inventory JSON schema additions
- Diff output extensions to surface byte changes
- Optional NT publish of compact summaries

Excludes:
- Decoder field naming or scaling
- Any active CAN transmission
- GUI changes beyond existing JSON and CLI outputs

## Terminology
- Pair: `(mfg, type, id, apiClass, apiIndex)`
- Byte fingerprint: per-byte change mask + change rate + variation score
- Variation score: simple scalar 0..1 derived from byte value changes

## Goals
- Identify which bytes change within each frame type
- Quantify how often each byte changes
- Provide a compact score for prioritizing candidate command/status frames
- Preserve compatibility with existing inventory JSON consumers

## Non-Goals
- Do not label bytes as specific fields
- Do not infer scaling or units
- Do not require synchronized captures across devices
- Do not claim electrical integrity issues (this is logical payload analysis)

## Why This Exists
Purpose: Explain what problems byte fingerprinting helps solve beyond simple presence/rate data.
- A device can be â€œpresentâ€ but the message meaning is still unknown.
- Status vs command-like frames are often distinguished by which bytes move and how fast.
- Fingerprints give a stable, low-effort signal to guide experiments and decoder hypotheses.

## Questions It Can Answer
Purpose: Clarify the decisions this feature supports.
- Which bytes in a given frame ever change?
- Which bytes change on every frame vs occasionally?
- Which frames become â€œactiveâ€ only when you command a device?
- Which frame types are likely control/command candidates?

## Questions It Cannot Answer
Purpose: Set expectations about limitations.
- Exact physical meaning or units of a byte.
- Whether a change is â€œgoodâ€ or â€œbadâ€ without context.
- Electrical-layer health (termination, noise, bus errors).
- True sender identity beyond arbitration ID grouping.

## Primary Use Cases
Purpose: Show how teams should use the data.
- **Command isolation**: Run an experiment (setpoint step) and find frames whose changing bytes spike.
- **Decoder scaffolding**: Start hypotheses where a small subset of bytes change consistently.
- **Regression checks**: Compare fingerprints across firmware changes to see if payload patterns shifted.
- **Bus sanity checks**: Detect unexpected variability in frames that should be constant.

## Data Flow
1. Live capture: update per-pair byte statistics on each frame
2. Inventory dump: persist fingerprints to JSON
3. Inventory diff: highlight byte-level changes between snapshots
4. Optional NT publish: compact JSON under `bringup/diag/can/...`

## Interpretation Guide
Purpose: Explain how to read the metrics without overfitting.
- A high change rate on a byte suggests a frequently updated field (speed, position, or command).
- A low change rate with occasional spikes may indicate state flags or rare events.
- Frames with many changing bytes are more likely to be â€œstatus dumps.â€
- Frames with a small changing subset are good command-candidate targets.

## Example Workflow
Purpose: Show a concrete end-to-end usage sequence.
1. Capture baseline: `--dump-api-inventory baseline.json`
2. Apply stimulus: set motor output to a steady value.
3. Capture stimulus: `--dump-api-inventory step.json`
4. Diff: `--diff-inventory baseline.json step.json`
5. Identify frames with new changing bytes or large variation deltas.
6. Use those frames in the next controlled experiment (stop/reverse).

## Byte Fingerprint Model
Per pair, track:
- `byteMask`: bitmask for byte positions that changed at least once
- `byteChangeRate[]`: fraction of frames where each byte changed
- `byteVariation[]`: simple variation score per byte
- `overallVariation`: aggregate score (mean or max of byteVariation)

Variation score options (choose one, default #1):
1. **Normalized distinct count**: `distinct_values / 256`
2. **Normalized variance**: `min(1.0, variance / 65025)`
3. **Entropy estimate**: `entropy_bits / 8`

## Inventory JSON Schema (Additive)
Add to each frame entry:
```
fingerprint: {
  byteMask: "0x000000ff",
  byteChangeRate: [0.0..1.0],
  byteVariation: [0.0..1.0],
  overallVariation: 0.0..1.0
}
```

Rules:
- Omit `fingerprint` if not enough samples
- `byteChangeRate` and `byteVariation` length equals DLC observed (max 8)
- Schema remains backward compatible

## Diff Output (Additive)
Extend `--diff-inventory` to include:
- New byte changes: bytes that changed in B but not in A
- Biggest variation deltas per pair

Example:
```
Byte deltas (top 5):
  label=Drive Motor apiClass=6 apiIndex=0 bytes: [0,1] variation +0.42
```

## NT Publishing (Optional)
Add under `bringup/diag/can/...`:
- `can/fingerprints/json` (compact summary)
- `can/candidates/json` (frames with high variation and control-like rates)

NT publishing is additive and must not alter existing keys.

## Sampling Requirements
Minimum sample count per pair before emitting fingerprints:
- Default: 50 frames
- Configurable via CLI flag (future)

## Decision Criteria
Purpose: Provide simple thresholds to focus attention.
- Flag as â€œcommand candidateâ€ if:
  - `overallVariation >= 0.6`, and
  - `byteMask` has <= 2 bytes set, and
  - frame rate increases during command stimulus.
- Flag as â€œstatus candidateâ€ if:
  - `overallVariation <= 0.4`, and
  - `byteMask` has > 2 bytes set, and
  - frame rate is steady across experiments.

## Performance Constraints
- O(1) update per frame
- Minimal memory growth per observed pair
- No heavy dependencies

## Error Handling
- If frames are too few, omit fingerprints and report `samplesTooLow`
- Do not fail capture on fingerprint errors

## Examples
Example fingerprint (status-like):
```
byteMask: 0x00000013   // bytes 0,1,4 changed
byteChangeRate: [0.9, 0.2, 0.0, 0.0, 0.05, 0.0, 0.0, 0.0]
byteVariation: [0.8, 0.1, 0.0, 0.0, 0.02, 0.0, 0.0, 0.0]
overallVariation: 0.18
```

Example fingerprint (command-like):
```
byteMask: 0x00000003   // bytes 0,1 changed
byteChangeRate: [1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
byteVariation: [0.95, 0.92, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
overallVariation: 0.94
```

## Compatibility
- Inventory schema changes are additive
- Older tools ignore the new `fingerprint` field
- No NetworkTables key changes required

## Risks and Misinterpretation
Purpose: Call out common pitfalls.
- High variation can be noise or packing effects, not necessarily a command.
- A constant command may appear â€œstatus-likeâ€ if the setpoint is steady.
- Short captures can overfit; longer capture windows improve stability.

## Tradeoffs
- Simple metrics are fast but can overestimate â€œmeaningfulâ€ changes
- Entropy/variance is sensitive to noise and scaling
- More samples improve accuracy but slow feedback

## Future Extensions
- Per-byte change timing (lag correlation to commands)
- Separate â€œcommand candidateâ€ classifier
- Multi-sniffer cross-validation of fingerprints
- Export to Wireshark dissector hints

