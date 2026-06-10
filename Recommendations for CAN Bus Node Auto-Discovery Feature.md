I'll start by loading the relevant abilities and then examine the repository to understand the current architecture and make recommendations for CAN bus node auto-discovery.Now let me explore the architecture and CAN-related documentation to understand the current system better:Now I have a comprehensive view of the system. Let me synthesize recommendations for the CAN bus node auto-discovery feature:

## Recommendations for CAN Bus Node Auto-Discovery Feature

Based on my review of the architecture, existing code, and system constraints, here are my recommendations:

### **1. Discovery Strategy (align with existing inversion pattern)**

The system already has strong separation between:
- **Robot-side**: Creates devices via explicit `BringupCore.add()` / `add-all` using pre-defined `bringup_system.json` profile
- **PC-side (CAN tool)**: Passively observes CAN traffic via CANable

**Recommendation**: Add discovery as a *read-only, passive operation* on the PC side:

```
Discovery Phase (new):
- Inventory phase: PC tool captures baseline of (mfg, type, apiClass, apiIndex) pairs
- Analysis phase: Group frames by manufacturer + device type; infer device count and IDs
- Report phase: Surface candidates for adding to profile without transmitting

This preserves the hard rule: "Python side must be read-only on CAN. Never transmit CAN frames."
```

### **2. Implementation Layers (follow existing 6-layer model)**

Add auto-discovery logic at these layers:

**Layer 2 (Adapter/Protocol)**: `tools/can_nt/can_analyzer.py`
- Extend `CanLiveAnalyzer.summary()` to detect device boundaries
- Group frames by (mfg, type, id) triplet
- Track first/last seen timestamp and frame count per triplet

**Layer 3 (Domain Logic)**: New module `tools/common/can_discovery/can_discovery_service.py`
- Consume analyzer summaries
- Build device candidates with confidence scoring
- Compare against declared profile to flag missing/extra devices

**Layer 5 (Presentation)**: CLI and UI
- `show discovered` (CLI) — list candidates
- `--publish-discovery` (bridge_cli.py flag) — emit to NT under `bringup/diag/can/discovered/...`
- Topology editor: import candidates into profile

### **3. Data Model for Discovery**

Extend inventory JSON schema (existing `tools/can_inventory/can_inventory.py`):

```json
{
  "devices": [...],
  "discovery": {
    "candidates": [
      {
        "manufacturer": "CTRE",
        "device_type": "FALCON",
        "estimated_can_ids": [10, 11, 12],
        "api_classes_seen": [5, 6, 7],
        "frame_count": 1250,
        "rate_hz": 25.0,
        "confidence": 0.95,
        "status": "missing_from_profile"
      }
    ],
    "scan_duration_sec": 45.0,
    "scan_timestamp": "2026-06-09T15:32:00Z"
  }
}
```

### **4. Avoid Adding to Hard Rules; Instead Add Process Doc**

Create `docs/CAN_AUTO_DISCOVERY_WORKFLOW.md`:

```markdown
## CAN Auto-Discovery Workflow

Purpose: Find unknown devices on the bus and suggest profile additions.

Process (Pit Diagnosis Direction):
1. Connect CANable and start bridge: `--publish-discovery`
2. Robot: Press Start to add all *declared* devices
3. PC tool: Watch for undeclared traffic
4. View candidates: `show discovered` (CLI) or check NT `bringup/diag/can/discovered/...`
5. Validate candidates against robot behavior
6. Topology editor: Drag + drop candidates into profile
7. Redeploy or `config push` to activate

Key rule: Discovery is passive observation only. No CAN transmissions.
```

### **5. Wire to Existing Reverse-Engineering Infrastructure**

The repo already has:
- `tools/can_inventory/can_inventory.py` — inventory snapshots
- `docs/FEATURE_SPEC_BYTE_FINGERPRINTING.md` — per-byte analysis (planned)
- `can_analyzer.py` — live frame aggregation
- Wireshark dissector path (mentioned in README)

**Recommendation**: Make discovery the *entry point* to reverse-engineering workflow:

1. **Discover** → group unknown frames
2. **Fingerprint** (existing spec) → analyze byte patterns
3. **Experiment** → controlled robot actions to narrow meaning
4. **Document** → update `docs/CAN_BACKGROUND.md` with new device types
5. **Integrate** → add decoder to `can_mappings.json` and manufacturer layer

### **6. Constants and Configuration**

Per hard rules, no magic numbers in code. Define in `tools/common/app_versions.py` or new `tools/common/discovery_config.py`:

```python
# Discovery tuning
DISCOVERY_MIN_FRAMES_PER_DEVICE = 50
DISCOVERY_STALE_THRESHOLD_SEC = 10
DISCOVERY_CONFIDENCE_HIGH = 0.90
DISCOVERY_CONFIDENCE_MEDIUM = 0.70
DISCOVERY_CONFIDENCE_LOW = 0.50

# API class groupings (from CAN_BACKGROUND.md)
KNOWN_STATUS_API_CLASSES = [5, 6]
KNOWN_CONFIG_API_CLASSES = [7]
KNOWN_CONTROL_API_CLASSES = [0, 1, 2, 3, 4]
```

### **7. Telemetry Publishing (NetworkTables)**

Add under `bringup/diag/can/discovered/`:
```
bringup/diag/can/discovered/count = 3
bringup/diag/can/discovered/json = {...}  (compact summary)
bringup/diag/can/discovered/timestamp = 123456789
```

Follow existing NT contract: **stable keys, additive only, no deletions**.

### **8. CLI Integration Examples**

```bash
# Show discovered devices
show discovered

# Show discovered devices with confidence >0.7
show discovered --min-confidence 0.70

# Dump discovery data as JSON
show discovered --format json > candidates.json

# Long-form with fingerprints (when FEATURE_SPEC_BYTE_FINGERPRINTING ships)
show discovered --include-fingerprints
```

### **9. Validation and Regression**

Add to `tools/regression/` or `docs/TESTING.md`:

```
Test: Discovery of known device inventory
- Baseline profile: 5 devices defined
- Capture: 30s of known traffic
- Assert: discovered count = 5
- Assert: confidence >= 0.90 for all

Test: Discovery of extra device (not in profile)
- Baseline profile: 4 devices
- Capture: 5 devices on bus (1 extra)
- Assert: discovered count = 5
- Assert: extra device flagged with status="not_in_profile"
```

### **10. Documentation Rules Compliance**

When adding discovery feature:
- [ ] Create `docs/FEATURE_SPEC_CAN_AUTO_DISCOVERY.md` (follows existing spec template)
- [ ] Update `docs/ARCHITECTURE.md` Section G (Reports + Outputs) with discovery inventory as output artifact
- [ ] Update `docs/CAN_BACKGROUND.md` Section "Discovery Process" to reference new workflow
- [ ] Add `docs/CAN_AUTO_DISCOVERY_WORKFLOW.md` with pit diagnosis steps
- [ ] All markdown must pass markdownlint (MD022, MD032 for spacing)
- [ ] Update `docs/README.md` to link new discovery docs

### **11. Key Tradeoffs & Future Extensions**

**Tradeoffs:**
- Simple group-by-ID doesn't distinguish *multiple* devices on the same ID (limitation)
- High frame rates can cause false-positive device splits; stale threshold helps
- Confidence score is heuristic; humans must validate

**Future Extensions:**
- Multi-sniffer cross-validation (compare PC tool + second CANable)
- Device-class inference (use fingerprints + API class patterns)
- Automated profile generation from discovery + topology layout suggestions
- Wireshark dissector hints from fingerprint data

---

**Bottom Line**: Keep auto-discovery **passive, non-transmitting, and additive to existing flow**. Make it the gateway into your byte-fingerprinting and reverse-engineering workflows. Update docs simultaneously to prevent drift.