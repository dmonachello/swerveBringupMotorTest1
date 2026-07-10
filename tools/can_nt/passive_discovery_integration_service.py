from __future__ import annotations

"""
NAME
    passive_discovery_integration_service.py - First-slice host integration helpers for passive_discovery_poc.

DESCRIPTION
    Centralizes the initial rollout boundary between legacy host UI evidence
    composition and the new passive discovery library. The first slice uses the
    passive discovery profile loader as the authoritative source for selected
    profile inventory while keeping the remaining Evidence-tab sections plainly
    marked as legacy until frame-backed integration is ready.
"""

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from tools.common.config_api.repository import ConfigRepository
from tools.common.motor_runtime_verdict import (
    RESULT_ELECTRICAL,
    RESULT_ROTATING,
    RESULT_STALLED,
    infer_motor_runtime_verdict,
    runtime_motor_attachment,
)
from tools.common.profile_constants import KEY_ID, KEY_LABEL, KEY_MANUFACTURER, KEY_MODEL
from tools.passive_discovery_poc.discovery import analyze_frames
from tools.passive_discovery_poc.enrichment import enrich_topology
from tools.passive_discovery_poc.models import DeviceRecord, RunResult
from tools.passive_discovery_poc.profile import load_profile

ENGINE_LABEL_LEGACY = "LEGACY"
ENGINE_LABEL_MIXED = "MIXED"
ENGINE_LABEL_NEW = "NEW"

ENGINE_ID_LEGACY = "legacy"
ENGINE_ID_PASSIVE_DISCOVERY_POC = "passive_discovery_poc"
ENGINE_ID_PASSIVE_DISCOVERY_POC_MIXED = "passive_discovery_poc_mixed"

ROLLOUT_MODE_LEGACY_ONLY = "legacy_only"
ROLLOUT_MODE_NEW_ONLY = "new_only"
ROLLOUT_MODE_SHADOW_COMPARE = "shadow_compare"

SECTION_PROFILE_INVENTORY = "profileInventory"
SECTION_PRESENCE_CHECK = "presenceCheck"
SECTION_PASSIVE = "passive"
SECTION_CONSOLE = "console"
SECTION_PROBE = "probe"
SECTION_MANUAL = "manual"
SECTION_TOPOLOGY_VIEW = "topologyView"
SECTION_INTERPRETATION = "interpretation"

PROFILE_PATH_AUTO = ""
TEXT_EMPTY = ""
TEXT_SECTION_SEPARATOR = "; "
TEXT_ENGINE_BANNER_PREFIX = "Evidence Engine: "
TEXT_ROLLOUT_PREFIX = "rollout="
TEXT_SECTION_PREFIX = "sections="
KEY_DEVICE_TYPE = "deviceType"
KEY_PROFILE_NODE = "profileNode"
KEY_BUS = "bus"
KEY_EVIDENCE_ENGINE_ID = "evidenceEngineId"
KEY_EVIDENCE_ENGINE_LABEL = "evidenceEngineLabel"
KEY_TOPOLOGY_NODE_KEY = "topologyNodeKey"
KEY_TOPOLOGY_NODE_TYPE = "topologyNodeType"
KEY_TOPOLOGY_NEIGHBOR_COUNT = "topologyNeighborCount"
RUN_METADATA_SOURCE = "source"
RUN_METADATA_SOURCE_KIND = "sourceKind"
RUN_METADATA_FRAME_PROVIDER = "visibility_provider"
RUN_METADATA_HOST_PASSIVE = "host_live_passive_discovery"
ATTACHMENT_KEY_TYPE = "type"
ATTACHMENT_TYPE_PRESENCE_CHECK = "presenceCheck"
PRESENCE_KEY_BUCKET = "bucket"
PRESENCE_KEY_STATUS = "status"
PRESENCE_KEY_SOURCE = "source"
PRESENCE_KEY_UPDATED_AT_MS = "updatedAtMs"
PRESENCE_KEY_MESSAGE = "message"
PRESENCE_KEY_SCORE = "score"
PRESENCE_KEY_AGE_SECONDS = "ageSeconds"
PRESENCE_KEY_AGE_TEXT = "ageText"
PRESENCE_KEY_EXISTENCE = "existence"
PRESENCE_KEY_CONFIDENCE = "confidence"
PRESENCE_VALUE_PRESENT = "present"
PRESENCE_VALUE_ABSENT = "absent"
PRESENCE_VALUE_UNKNOWN = "unknown"
EVIDENCE_STATUS_PRESENT = "PRESENT"
EVIDENCE_STATUS_ABSENT = "ABSENT"
EVIDENCE_STATUS_OK = "OK"
EVIDENCE_STATUS_DEGRADED = "DEGRADED"
EVIDENCE_STATUS_FAILED = "FAILED"
EVIDENCE_STATUS_UNKNOWN = "UNKNOWN"
EVIDENCE_STATUS_MATCHING = "MATCHING"
EVIDENCE_STATUS_WRONG = "WRONG"
EVIDENCE_STATUS_NOT_RUN = "NOT RUN"
EVIDENCE_STATUS_CONFLICT = "CONFLICT"
EVIDENCE_CONFIDENCE_HIGH = "HIGH"
EVIDENCE_CONFIDENCE_MEDIUM = "MEDIUM"
EVIDENCE_CONFIDENCE_LOW = "LOW"
EVIDENCE_SOURCE_NONE = "--"
RUNTIME_DEVICE_KEY_ATTACHMENTS = "attachments"
RUNTIME_DEVICE_KEY_PRESENCE_CONFIDENCE = "presenceConfidence"
TEXT_SECONDS_AGO_FORMAT = "{value:.1f}s ago"
PRESENCE_SCORE_HIGH_THRESHOLD = 0.5
PRESENCE_SCORE_LOW_THRESHOLD = 0.05
CONSOLE_SCOPE_DEVICES = "devices"
CONSOLE_SCOPE_SYSTEM = "system"
CONSOLE_KEY_SYSTEM_TEXT = "systemText"
CONSOLE_KEY_SYSTEM_CONFLICT = "systemConflict"
CONSOLE_KEY_EVENTS = "events"
CONSOLE_KEY_SUMMARY = "summary"
CONSOLE_KEY_HAS_ERROR = "hasError"
CONSOLE_KEY_HAS_WARN = "hasWarn"
CONSOLE_KEY_WARN_COUNT = "warnCount"
CONSOLE_KEY_ERROR_COUNT = "errorCount"
CONSOLE_KEY_FATAL_COUNT = "fatalCount"
CONSOLE_SEVERITY_WARN = "WARN"
CONSOLE_SEVERITY_ERROR = "ERROR"
CONSOLE_SEVERITY_FATAL = "FATAL"
CONSOLE_SEVERITY_INFO = "INFO"
CONSOLE_EVENT_BUS_FAULT = "BUS_FAULT_SUSPECTED"
CONSOLE_TEXT_STALE = "stale"
ATTACHMENT_TYPE_ACTIVE_PRESENCE_PROBE = "activePresenceProbe"
PROBE_KEY_BUCKET = "bucket"
PROBE_KEY_SCORE = "score"
PROBE_KEY_MAX_SCORE = "maxScore"
PROBE_KEY_UPDATED_AT_MS = "updatedAtMs"
PROBE_KEY_FAILED_CHECKS = "failedChecks"
PROBE_KEY_WARNINGS = "warnings"
PROBE_KEY_ERRORS = "errors"
PROBE_BUCKET_UNKNOWN = "unknown"
PROBE_BUCKET_NOT_RUN = "not_run"
PROBE_AGE_FRESH = "fresh"
PROBE_AGE_AGING = "aging"
PROBE_AGE_STALE = "stale"
PROBE_FRESH_SEC = 15.0
PROBE_AGING_SEC = 60.0
PROBE_STATS_WAITING = "Updates only when Full Probe is run."
PROBE_STATS_RUNNING = "Full Probe is running now."
PROBE_STATS_LAST_COMPLETE_FMT = "Last Full Probe completed {age} ago."
PROBE_STATS_RUN_COUNT_FMT = "Full Probe runs requested: {count}"
PROBE_NOT_RUN_YET = "Not run yet"
PROBE_NO_DEVICE_RESULT = "No device-specific full-probe result for this device."
PROBE_NOT_IN_RUNTIME_SET = "This device was not part of the active runtime probe set when Full Probe ran."
PROBE_INFRA_SCOPE_NOTE = "Not probed in current motion-test scope."
PROBE_INFRA_SCOPE_DETAIL = "Infrastructure device; evaluated from passive/runtime evidence instead."
PROBE_TEXT_FIELD = "text"
PROBE_SUMMARY_FIELD = "summary"
PROBE_SCORE_TEXT_FIELD = "scoreText"
PROBE_AGE_BUCKET_FIELD = "ageBucket"
PROBE_AGE_TEXT_FIELD = "ageText"
PROBE_STATS_TEXT_FIELD = "statsText"
PROBE_MISSING_TEXT_FIELD = "missingText"
PROBE_DISPLAY_BUCKET_FIELD = "displayBucket"
STATUS_NOT_RUN = "NOT RUN"
TEXT_WAITING = "Waiting"
TEXT_UPDATE_DELIM = " | "
TEXT_COMMA_DELIM = ", "
MANUAL_PLACEHOLDER = "Not run"
MANUAL_OUTCOME_CORRECT = "correct_response"
MANUAL_OUTCOME_NO_RESPONSE = "no_response"
MANUAL_OUTCOME_WRONG_DEVICE = "wrong_device_response"
MANUAL_OUTCOME_WRONG_BRANCH = "wrong_branch_response"
MANUAL_OUTCOME_INTERMITTENT = "intermittent_response"
MANUAL_OUTCOME_DEGRADED = "degraded_response"
MANUAL_OUTCOME_UNCERTAIN = "operator_uncertain"
MANUAL_OUTCOME_LABELS = {
    MANUAL_OUTCOME_CORRECT: "Correct response",
    MANUAL_OUTCOME_NO_RESPONSE: "No response",
    MANUAL_OUTCOME_WRONG_DEVICE: "Wrong device",
    MANUAL_OUTCOME_WRONG_BRANCH: "Wrong branch",
    MANUAL_OUTCOME_INTERMITTENT: "Intermittent",
    MANUAL_OUTCOME_DEGRADED: "Degraded",
    MANUAL_OUTCOME_UNCERTAIN: "Uncertain",
}
MANUAL_AUTO_RESULT_RUNNING = "test_running"
MANUAL_AUTO_RESULT_ROTATION = "rotation_detected"
MANUAL_AUTO_RESULT_NO_ROTATION = "no_rotation_detected"
MANUAL_AUTO_RESULT_LABELS = {
    MANUAL_AUTO_RESULT_RUNNING: "Test running",
    MANUAL_AUTO_RESULT_ROTATION: "Rotation detected",
    MANUAL_AUTO_RESULT_NO_ROTATION: "No rotation detected",
}
MANUAL_LINE_RESULT = "result={value}"
MANUAL_LINE_AGE = "age={value}"
MANUAL_LINE_OBSERVED = "observed={value}"
MANUAL_LINE_NOTES = "note={value}"
MANUAL_LINE_RECORDED = "at={value}"
MANUAL_LINE_AUTO_RESULT = "autoResult={value}"
MANUAL_LINE_MOTION = "motionCheck={value}"
MANUAL_LINE_MOTION_VALUES = "cmdDuty={cmd} | appliedDuty={applied} | velRpm={vel} | positionRot={position} | positionDeltaRot={delta} | motorCurrentA={current}"
MANUAL_MOTION_ACTIVE = "active"
MANUAL_MOTION_PASS = "rotation_detected"
MANUAL_MOTION_FAIL = "no_rotation_detected"
MANUAL_MOTION_IDLE = "idle"
MANUAL_MOTION_WINDOW_SEC = 3.0
MANUAL_MOTION_SETTLE_SEC = 0.4
MOTION_CMD_THRESHOLD_DUTY = 0.15
MOTION_MIN_RPM = 5.0
MOTION_MIN_POSITION_DELTA_ROT = 0.05
VALUE_NOT_APPLICABLE = "n/a"
MANUAL_SUMMARY_FIELD = "summary"
INTERPRET_KEY_LABEL = "label"
INTERPRET_KEY_PASSIVE = "passive"
INTERPRET_KEY_CONSOLE = "console"
INTERPRET_KEY_PROBE = "probe"
INTERPRET_KEY_PROBE_SCORE = "probeScore"
INTERPRET_KEY_MANUAL = "manual"
INTERPRET_KEY_EXISTENCE = "existence"
INTERPRET_KEY_OPERABILITY = "operability"
INTERPRET_KEY_IDENTITY = "identity"
INTERPRET_KEY_CONFIDENCE = "confidence"
INTERPRET_KEY_PRESENCE_TEXT = "presenceText"
INTERPRET_KEY_PASSIVE_TEXT = "passiveText"
INTERPRET_KEY_CONSOLE_TEXT = "consoleText"
INTERPRET_KEY_PROBE_TEXT = "probeText"
INTERPRET_KEY_MANUAL_TEXT = "manualText"
INTERPRET_KEY_NOTES_TEXT = "notesText"
INTERPRET_KEY_STATE = "state"
INTERPRET_KEY_CONFLICTED = "conflicted"
EVIDENCE_NOTE_SEPARATOR = " | "
EVIDENCE_TEXT_DEVICE_TIMEOUT = "timeout"
EVIDENCE_STATE_OK = "ok"
EVIDENCE_STATE_DEGRADED = "degraded"
EVIDENCE_STATE_MISSING = "missing"
EVIDENCE_STATE_UNKNOWN = "unknown"
EVIDENCE_STATE_IDENTITY = "identity"
EVIDENCE_PROBE_DETAIL_LIMIT = 4
EVIDENCE_MANUAL_OPERABILITY_WINDOW_SEC = 120.0
EVIDENCE_MANUAL_IDENTITY_WINDOW_SEC = 900.0
EVIDENCE_MANUAL_NOTE_AGE_IDENTITY_ONLY = "Manual result is older than the operability window; using it only as identity evidence."
EVIDENCE_MANUAL_NOTE_STALE = "Manual result is stale and not being used for automatic conclusions."
EVIDENCE_MANUAL_NOTE_CONFLICT = "Manual evidence conflicts with stronger automatic evidence."
EVIDENCE_MOTION_NOTE_NO_ROTATION = "Motor commanded but no rotation detected."
EVIDENCE_MOTION_NOTE_ROTATING = "Motor rotation detected."
EVIDENCE_PROBE_NOTE_AGING = "Full-probe result is aging; lowering its weight."
EVIDENCE_PROBE_NOTE_STALE = "Full-probe result is stale; using it only as historical evidence."
EVIDENCE_PROBE_NOTE_ONE_SHOT = "Full Probe is a cached manual one-shot diagnostic result."
EVIDENCE_NOTE_PASSIVE_WITHOUT_PROBE_RESULT = "Passive CAN traffic is present, but Full Probe did not produce a device-specific result here."
EVIDENCE_NOTE_PASSIVE_OVERRIDES_RUNTIME_ABSENCE = "Passive CAN shows recurring device-emitted traffic even though the robot-local presence snapshot did not observe this device."
EVIDENCE_NOTE_INFRA_SCOPE_ABSENCE = "Infrastructure device is outside the current motion-test scope; local snapshot absence is not treated as definitive missing evidence."
EVIDENCE_NOTE_NONE = "No major source conflict."
DETAIL_SNAPSHOT_PRESENCE = "presence"
DETAIL_SNAPSHOT_PRESENCE_STATUS = "presenceStatus"
DETAIL_SNAPSHOT_PRESENCE_AGE = "presenceAge"
DETAIL_SNAPSHOT_PRESENCE_SOURCE = "presenceSource"
DETAIL_SNAPSHOT_FULL_PROBE_BUCKET = "fullProbeBucket"
DETAIL_SNAPSHOT_FULL_PROBE_AGE = "fullProbeAge"
DETAIL_SNAPSHOT_FULL_PROBE_SCORE = "fullProbeScore"
DETAIL_SNAPSHOT_FULL_PROBE_STATUS = "fullProbeStatus"
DETAIL_SNAPSHOT_FULL_PROBE_MESSAGE = "fullProbeMessage"
DETAIL_SNAPSHOT_LIFECYCLE_STATE = "lifecycleState"
DETAIL_SNAPSHOT_TESTABLE = "testable"
DETAIL_SNAPSHOT_OVERRIDE_ACTIVE = "overrideActive"
DETAIL_SNAPSHOT_OVERRIDE_ORIGINATED = "overrideOriginated"
DETAIL_SNAPSHOT_OVERRIDE_FAILURE = "overrideFailure"
DETAIL_SNAPSHOT_NOT_TESTABLE_REASON = "notTestableReason"
DETAIL_SNAPSHOT_LAST_SEEN = "lastSeen"
DETAIL_SNAPSHOT_CURRENT_A = "currentA"
DETAIL_SNAPSHOT_CURRENT_AVG_A = "currentAvgA"
DETAIL_SNAPSHOT_CURRENT_PEAK_A = "currentPeakA"
DETAIL_SNAPSHOT_CURRENT_NONZERO = "currentNonzero"
DETAIL_SNAPSHOT_CURRENT_SAMPLES = "currentSamples"
DETAIL_SNAPSHOT_CMD_DUTY = "cmdDuty"
DETAIL_SNAPSHOT_APPLIED_DUTY = "appliedDuty"
DETAIL_SNAPSHOT_VEL_RPM = "velRpm"
DETAIL_SNAPSHOT_POSITION_ROT = "positionRot"
INFRASTRUCTURE_DEVICE_LABELS = {"roborio", "pdp", "pdh"}
DETAIL_SNAPSHOT_POSITION_DELTA_ROT = "positionDeltaRot"
DETAIL_SNAPSHOT_TEMP_C = "tempC"
DETAIL_SNAPSHOT_SELECTED = "selected"
EVIDENCE_FIELD_CMD_DUTY = "cmdDuty"
EVIDENCE_FIELD_APPLIED_DUTY = "appliedDuty"
EVIDENCE_FIELD_VEL_RPM = "velRpm"
EVIDENCE_FIELD_MOTOR_CURRENT_A = "motorCurrentA"
EVIDENCE_FIELD_POSITION_ROT = "positionRot"
VIS_IDENTITY_UNKNOWN = "--"
VIS_PACKET_COUNT_UNKNOWN = "--"
VIS_PACKET_RATE_UNKNOWN = "--"


def default_profile_path() -> str:
    """
    NAME
        default_profile_path - Return the canonical bringup profile path used by the host UI.
    """
    return str(ConfigRepository().canonical_path())


def default_evidence_engine_status() -> Dict[str, Any]:
    """
    NAME
        default_evidence_engine_status - Return the first-slice Evidence-tab engine ownership map.
    """
    status = {
        "engineLabel": ENGINE_LABEL_NEW,
        "engineId": ENGINE_ID_PASSIVE_DISCOVERY_POC,
        "rolloutMode": ROLLOUT_MODE_NEW_ONLY,
        "sections": {
            SECTION_PROFILE_INVENTORY: ENGINE_LABEL_NEW,
            SECTION_PRESENCE_CHECK: ENGINE_LABEL_NEW,
            SECTION_PASSIVE: ENGINE_LABEL_NEW,
            SECTION_CONSOLE: ENGINE_LABEL_NEW,
            SECTION_PROBE: ENGINE_LABEL_NEW,
            SECTION_MANUAL: ENGINE_LABEL_NEW,
            SECTION_TOPOLOGY_VIEW: ENGINE_LABEL_NEW,
            SECTION_INTERPRETATION: ENGINE_LABEL_NEW,
        },
    }
    return normalize_evidence_engine_status(status)


def evidence_engine_banner_text(status: Dict[str, Any]) -> str:
    """
    NAME
        evidence_engine_banner_text - Format one explicit migration banner for the Evidence tab.
    """
    engine_label = str(status.get("engineLabel", ENGINE_LABEL_LEGACY)).strip() or ENGINE_LABEL_LEGACY
    rollout_mode = str(status.get("rolloutMode", ROLLOUT_MODE_LEGACY_ONLY)).strip() or ROLLOUT_MODE_LEGACY_ONLY
    sections = status.get("sections")
    section_parts = []
    if isinstance(sections, dict):
        for section_key in (
            SECTION_PROFILE_INVENTORY,
            SECTION_PRESENCE_CHECK,
            SECTION_PASSIVE,
            SECTION_CONSOLE,
            SECTION_PROBE,
            SECTION_MANUAL,
            SECTION_TOPOLOGY_VIEW,
            SECTION_INTERPRETATION,
        ):
            label = str(sections.get(section_key, ENGINE_LABEL_LEGACY)).strip() or ENGINE_LABEL_LEGACY
            section_parts.append(f"{section_key}={label}")
    return (
        TEXT_ENGINE_BANNER_PREFIX
        + engine_label
        + " | "
        + TEXT_ROLLOUT_PREFIX
        + rollout_mode
        + " | "
        + TEXT_SECTION_PREFIX
        + TEXT_SECTION_SEPARATOR.join(section_parts)
    )


def section_engine_label(status: Dict[str, Any], section_key: str) -> str:
    """
    NAME
        section_engine_label - Return the declared engine label for one Evidence-tab subsection.
    """
    sections = status.get("sections")
    if not isinstance(sections, dict):
        return ENGINE_LABEL_LEGACY
    label = str(sections.get(section_key, ENGINE_LABEL_LEGACY)).strip()
    return label or ENGINE_LABEL_LEGACY


def evidence_section_title(base_title: str, status: Dict[str, Any], section_key: str) -> str:
    """
    NAME
        evidence_section_title - Append one explicit engine label to a UI section title.
    """
    label = section_engine_label(status, section_key)
    return f"{base_title} [{label}]"


def evidence_overall_title(base_title: str, status: Dict[str, Any]) -> str:
    """
    NAME
        evidence_overall_title - Append the overall engine label to a top-level Evidence surface title.
    """
    label = str(status.get("engineLabel", ENGINE_LABEL_LEGACY)).strip() or ENGINE_LABEL_LEGACY
    return f"{base_title} [{label}]"


def normalize_evidence_engine_status(status: Dict[str, Any]) -> Dict[str, Any]:
    """
    NAME
        normalize_evidence_engine_status - Recompute overall engine/rollout labels from section ownership.
    """
    sections = status.get("sections")
    if not isinstance(sections, dict):
        sections = {}
        status["sections"] = sections
    labels = [
        str(sections.get(section_key, ENGINE_LABEL_LEGACY)).strip() or ENGINE_LABEL_LEGACY
        for section_key in (
            SECTION_PROFILE_INVENTORY,
            SECTION_PRESENCE_CHECK,
            SECTION_PASSIVE,
            SECTION_CONSOLE,
            SECTION_PROBE,
            SECTION_MANUAL,
            SECTION_TOPOLOGY_VIEW,
            SECTION_INTERPRETATION,
        )
    ]
    if labels and all(label == ENGINE_LABEL_NEW for label in labels):
        status["engineLabel"] = ENGINE_LABEL_NEW
        status["engineId"] = ENGINE_ID_PASSIVE_DISCOVERY_POC
        status["rolloutMode"] = ROLLOUT_MODE_NEW_ONLY
        return status
    if labels and all(label == ENGINE_LABEL_LEGACY for label in labels):
        status["engineLabel"] = ENGINE_LABEL_LEGACY
        status["engineId"] = ENGINE_ID_LEGACY
        status["rolloutMode"] = ROLLOUT_MODE_LEGACY_ONLY
        return status
    status["engineLabel"] = ENGINE_LABEL_MIXED
    status["engineId"] = ENGINE_ID_PASSIVE_DISCOVERY_POC_MIXED
    status["rolloutMode"] = ROLLOUT_MODE_SHADOW_COMPARE
    return status


def load_profile_device_catalog(
    profile_name: str,
    *,
    profile_path: str = PROFILE_PATH_AUTO,
) -> Dict[str, Dict[str, Any]]:
    """
    NAME
        load_profile_device_catalog - Load one selected-profile CAN device catalog via passive_discovery_poc.
    """
    resolved_path = _resolve_profile_path(profile_path)
    _resolved_profile, expected_rows = load_profile(
        profile_path=resolved_path,
        profile_name=profile_name,
    )
    topology_record = enrich_topology(
        resolved_path,
        profile_name=profile_name,
    )
    topology_by_label = _index_topology_by_label(topology_record)
    catalog: Dict[str, Dict[str, Any]] = {}
    for manufacturer, device_type, device_id in sorted(expected_rows.keys()):
        row = expected_rows[(manufacturer, device_type, device_id)]
        label = str(row.get(KEY_LABEL, TEXT_EMPTY)).strip()
        if not label:
            continue
        entry: Dict[str, Any] = {
            KEY_LABEL: label,
            KEY_MANUFACTURER: manufacturer,
            KEY_DEVICE_TYPE: device_type,
            KEY_ID: device_id,
            KEY_MODEL: str(row.get(KEY_MODEL, TEXT_EMPTY)).strip(),
            KEY_PROFILE_NODE: str(row.get(KEY_PROFILE_NODE, TEXT_EMPTY)).strip(),
            KEY_BUS: str(row.get(KEY_BUS, TEXT_EMPTY)).strip(),
            KEY_EVIDENCE_ENGINE_ID: ENGINE_ID_PASSIVE_DISCOVERY_POC,
            KEY_EVIDENCE_ENGINE_LABEL: ENGINE_LABEL_NEW,
        }
        topology_info = topology_by_label.get(label.lower())
        if isinstance(topology_info, dict):
            entry.update(topology_info)
        catalog[label.lower()] = entry
    return catalog


def build_live_passive_result(
    visibility_provider: Any,
    profile_devices: Mapping[str, Mapping[str, Any]],
) -> Optional[RunResult]:
    """
    NAME
        build_live_passive_result - Analyze recent host-observed frames through passive_discovery_poc.
    """
    if visibility_provider is None or not profile_devices:
        return None
    recent_frames = getattr(visibility_provider, "recent_frames", None)
    if not callable(recent_frames):
        return None
    frames = recent_frames()
    if not isinstance(frames, list):
        frames = list(frames or ())
    return analyze_frames(
        frames,
        expected_rows=_expected_rows_from_profile_devices(profile_devices),
        run_metadata={
            RUN_METADATA_SOURCE: RUN_METADATA_FRAME_PROVIDER,
            RUN_METADATA_SOURCE_KIND: RUN_METADATA_HOST_PASSIVE,
        },
    )


def index_run_result_by_identity(result: Optional[RunResult]) -> Dict[Tuple[int, int, int], DeviceRecord]:
    """
    NAME
        index_run_result_by_identity - Index analyzed passive devices by canonical identity.
    """
    if result is None:
        return {}
    indexed: Dict[Tuple[int, int, int], DeviceRecord] = {}
    for device in result.device_records:
        indexed[
            (
                int(device.identity.manufacturer),
                int(device.identity.device_type),
                int(device.identity.device_id),
            )
        ] = device
    return indexed


def build_runtime_presence_catalog(
    runtime_devices: Mapping[str, Mapping[str, Any]],
    profile_devices: Mapping[str, Mapping[str, Any]],
    *,
    now_s: Optional[float] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    NAME
        build_runtime_presence_catalog - Normalize robot-local presence-check evidence for the host UI.
    """
    if now_s is None:
        import time

        now_s = time.time()
    catalog: Dict[str, Dict[str, Any]] = {}
    for label_key, profile_device in profile_devices.items():
        runtime_device = runtime_devices.get(label_key)
        label = str(profile_device.get(KEY_LABEL, label_key)).strip() or str(label_key)
        entry = _normalize_presence_entry(label, runtime_device, now_s)
        catalog[str(label_key).strip().lower()] = entry
    return catalog


def build_console_snapshot_from_entries(entries: Any) -> Dict[str, Any]:
    """
    NAME
        build_console_snapshot_from_entries - Normalize host console monitor entries into the shared Evidence snapshot shape.
    """
    result: Dict[str, Any] = {
        CONSOLE_SCOPE_DEVICES: {},
        CONSOLE_SCOPE_SYSTEM: [],
        CONSOLE_KEY_SYSTEM_TEXT: EVIDENCE_SOURCE_NONE,
        CONSOLE_KEY_SYSTEM_CONFLICT: False,
    }
    system_events = []
    for entry in list(entries or ()):
        if not bool(getattr(entry, "active", False)):
            continue
        severity = str(getattr(entry, "severity", TEXT_EMPTY) or TEXT_EMPTY).strip().upper()
        event_type = str(getattr(entry, "event_type", TEXT_EMPTY) or TEXT_EMPTY).strip()
        message = str(getattr(entry, "last_message", TEXT_EMPTY) or TEXT_EMPTY).strip()
        event_summary = f"[{severity or CONSOLE_SEVERITY_INFO}] {event_type}"
        if message:
            event_summary = f"{event_summary}: {message}"
        device_label = str(getattr(entry, "device_label", TEXT_EMPTY) or TEXT_EMPTY).strip()
        event_count = int(getattr(entry, "count", 0) or 0)
        if device_label:
            row = result[CONSOLE_SCOPE_DEVICES].setdefault(
                device_label.lower(),
                {
                    CONSOLE_KEY_EVENTS: [],
                    CONSOLE_KEY_SUMMARY: EVIDENCE_SOURCE_NONE,
                    CONSOLE_KEY_HAS_ERROR: False,
                    CONSOLE_KEY_HAS_WARN: False,
                    CONSOLE_KEY_WARN_COUNT: 0,
                    CONSOLE_KEY_ERROR_COUNT: 0,
                    CONSOLE_KEY_FATAL_COUNT: 0,
                    KEY_LABEL: device_label,
                    KEY_EVIDENCE_ENGINE_ID: ENGINE_ID_PASSIVE_DISCOVERY_POC,
                    KEY_EVIDENCE_ENGINE_LABEL: ENGINE_LABEL_NEW,
                },
            )
            row[CONSOLE_KEY_EVENTS].append(event_summary)
            if severity == CONSOLE_SEVERITY_WARN:
                row[CONSOLE_KEY_HAS_WARN] = True
                row[CONSOLE_KEY_WARN_COUNT] += max(1, event_count)
            elif severity == CONSOLE_SEVERITY_ERROR:
                row[CONSOLE_KEY_HAS_ERROR] = True
                row[CONSOLE_KEY_ERROR_COUNT] += max(1, event_count)
            elif severity == CONSOLE_SEVERITY_FATAL:
                row[CONSOLE_KEY_HAS_ERROR] = True
                row[CONSOLE_KEY_FATAL_COUNT] += max(1, event_count)
            if row[CONSOLE_KEY_SUMMARY] == EVIDENCE_SOURCE_NONE:
                row[CONSOLE_KEY_SUMMARY] = event_summary
        else:
            system_events.append(event_summary)
    for row in result[CONSOLE_SCOPE_DEVICES].values():
        if row[CONSOLE_KEY_SUMMARY] != EVIDENCE_SOURCE_NONE:
            continue
        if row[CONSOLE_KEY_FATAL_COUNT] > 0 or row[CONSOLE_KEY_ERROR_COUNT] > 0:
            row[CONSOLE_KEY_SUMMARY] = (
                f"errors={row[CONSOLE_KEY_ERROR_COUNT]} fatal={row[CONSOLE_KEY_FATAL_COUNT]}"
            )
        elif row[CONSOLE_KEY_WARN_COUNT] > 0:
            row[CONSOLE_KEY_SUMMARY] = f"warn={row[CONSOLE_KEY_WARN_COUNT]}"
    result[CONSOLE_SCOPE_SYSTEM] = system_events
    result[CONSOLE_KEY_SYSTEM_TEXT] = system_events[0] if system_events else EVIDENCE_SOURCE_NONE
    result[CONSOLE_KEY_SYSTEM_CONFLICT] = any(
        CONSOLE_EVENT_BUS_FAULT in event or CONSOLE_TEXT_STALE in event.lower()
        for event in system_events
    )
    return result


def build_runtime_probe_snapshot(
    runtime_device: Optional[Mapping[str, Any]],
    *,
    label: str = TEXT_EMPTY,
    probe_pending: bool,
    last_probe_completed_at: float,
    probe_run_count: int,
    now_s: Optional[float] = None,
) -> Dict[str, Any]:
    """
    NAME
        build_runtime_probe_snapshot - Normalize one runtime-device full-probe result into shared UI fields.
    """
    if now_s is None:
        import time

        now_s = time.time()
    attachment = _active_probe_attachment(runtime_device)
    raw_bucket = _probe_bucket_value(attachment)
    age_seconds = _presence_age_seconds(
        attachment.get(PROBE_KEY_UPDATED_AT_MS) if isinstance(attachment, Mapping) else None,
        now_s,
    )
    age_bucket = _probe_age_bucket(age_seconds)
    age_text = _format_probe_age_text(age_seconds)
    stats_text = _probe_stats_text(
        probe_pending=probe_pending,
        last_probe_completed_at=last_probe_completed_at,
        probe_run_count=probe_run_count,
        now_s=now_s,
    )
    is_infrastructure_device = _is_infrastructure_device(label)
    missing_text = _probe_missing_text(
        runtime_device=runtime_device,
        last_probe_completed_at=last_probe_completed_at,
        is_infrastructure_device=is_infrastructure_device,
    )
    failed_checks = _string_list_value(attachment, PROBE_KEY_FAILED_CHECKS)
    warnings = _string_list_value(attachment, PROBE_KEY_WARNINGS)
    errors = _string_list_value(attachment, PROBE_KEY_ERRORS)
    score_text = _format_probe_score_text(attachment)
    text_lines = [missing_text, stats_text]
    if isinstance(attachment, Mapping):
        text_lines = [
            TEXT_UPDATE_DELIM.join(
                (
                    f"bucket={raw_bucket}",
                    f"score={score_text}",
                    f"updated={age_text}",
                    f"ageClass={age_bucket if age_bucket != PROBE_BUCKET_UNKNOWN else STATUS_NOT_RUN}",
                )
            )
        ]
        if failed_checks:
            text_lines.append("failed: " + TEXT_COMMA_DELIM.join(failed_checks[:4]))
        if warnings:
            text_lines.append("warnings: " + TEXT_COMMA_DELIM.join(warnings[:4]))
        if errors:
            text_lines.append("errors: " + TEXT_COMMA_DELIM.join(errors[:4]))
        text_lines.append(stats_text)
        message_text = str(attachment.get(PRESENCE_KEY_MESSAGE, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE
        if message_text:
            text_lines.append(message_text)
        text_lines.append("Full Probe is a cached manual one-shot diagnostic result.")
    return {
        PROBE_KEY_BUCKET: raw_bucket,
        PROBE_SCORE_TEXT_FIELD: score_text,
        PROBE_AGE_BUCKET_FIELD: age_bucket,
        PROBE_AGE_TEXT_FIELD: age_text,
        PROBE_STATS_TEXT_FIELD: stats_text,
        PROBE_MISSING_TEXT_FIELD: missing_text,
        PROBE_TEXT_FIELD: "\n".join(text_lines),
        PROBE_SUMMARY_FIELD: _probe_display_bucket(raw_bucket, age_bucket),
        KEY_EVIDENCE_ENGINE_ID: ENGINE_ID_PASSIVE_DISCOVERY_POC,
        KEY_EVIDENCE_ENGINE_LABEL: ENGINE_LABEL_NEW,
    }


def build_manual_snapshot(
    manual_entry: Optional[Mapping[str, Any]],
    manual_observation: Optional[Mapping[str, Any]],
    manual_motion: Optional[Mapping[str, Any]],
    runtime_values: Optional[Mapping[str, Any]] = None,
    *,
    now_s: Optional[float] = None,
) -> Dict[str, Any]:
    """
    NAME
        build_manual_snapshot - Normalize one manual-evidence bundle into shared summary/text fields.
    """
    if now_s is None:
        import time

        now_s = time.time()
    manual_summary = MANUAL_PLACEHOLDER
    if isinstance(manual_entry, Mapping):
        outcome = str(manual_entry.get("outcome", TEXT_EMPTY)).strip().lower()
        manual_summary = MANUAL_OUTCOME_LABELS.get(outcome, outcome or MANUAL_PLACEHOLDER)
    if isinstance(manual_observation, Mapping):
        auto_result = str(manual_observation.get("autoResult", TEXT_EMPTY)).strip()
        if auto_result:
            manual_summary = MANUAL_AUTO_RESULT_LABELS.get(auto_result, auto_result)
    manual_lines = [MANUAL_PLACEHOLDER]
    manual_age_sec = _manual_age_seconds(manual_entry, now_s)
    if isinstance(manual_entry, Mapping):
        manual_lines = [MANUAL_LINE_RESULT.format(value=manual_summary)]
        observed = str(manual_entry.get("observed", TEXT_EMPTY)).strip()
        notes_value = str(manual_entry.get("notes", TEXT_EMPTY)).strip()
        recorded = str(manual_entry.get("recordedAt", TEXT_EMPTY)).strip()
        if isinstance(manual_age_sec, (int, float)):
            manual_lines.append(MANUAL_LINE_AGE.format(value=_format_age_text(float(manual_age_sec))))
        if observed:
            manual_lines.append(MANUAL_LINE_OBSERVED.format(value=observed))
        if notes_value:
            manual_lines.append(MANUAL_LINE_NOTES.format(value=notes_value))
        if recorded:
            manual_lines.append(MANUAL_LINE_RECORDED.format(value=recorded))
    elif isinstance(manual_observation, Mapping):
        auto_result = str(manual_observation.get("autoResult", TEXT_EMPTY)).strip() or MANUAL_PLACEHOLDER
        auto_result_label = MANUAL_AUTO_RESULT_LABELS.get(auto_result, auto_result)
        manual_lines = [MANUAL_LINE_AUTO_RESULT.format(value=auto_result_label)]
        observation_age_sec = _manual_age_seconds(manual_observation, now_s)
        observation_recorded = str(manual_observation.get("recordedAt", TEXT_EMPTY)).strip()
        if isinstance(observation_age_sec, (int, float)):
            manual_lines.append(MANUAL_LINE_AGE.format(value=_format_age_text(float(observation_age_sec))))
        if observation_recorded:
            manual_lines.append(MANUAL_LINE_RECORDED.format(value=observation_recorded))
    motion_snapshot = _build_manual_motion_snapshot(
        manual_observation=manual_observation,
        manual_motion=manual_motion,
        runtime_values=runtime_values or {},
        now_s=now_s,
    )
    if motion_snapshot["active"]:
        manual_lines.append(MANUAL_LINE_MOTION.format(value=motion_snapshot["state"]))
        manual_lines.append(
            MANUAL_LINE_MOTION_VALUES.format(
                cmd=_format_motion_value(motion_snapshot["cmdDuty"]),
                applied=_format_motion_value(motion_snapshot["appliedDuty"]),
                vel=_format_motion_value(motion_snapshot["velRpm"]),
                position=_format_motion_value(motion_snapshot["positionRot"]),
                delta=_format_motion_value(motion_snapshot["positionDeltaRot"]),
                current=_format_motion_value(motion_snapshot["motorCurrentA"]),
            )
        )
    return {
        MANUAL_SUMMARY_FIELD: manual_summary,
        PROBE_TEXT_FIELD: "\n".join(manual_lines),
        KEY_EVIDENCE_ENGINE_ID: ENGINE_ID_PASSIVE_DISCOVERY_POC,
        KEY_EVIDENCE_ENGINE_LABEL: ENGINE_LABEL_NEW,
    }


def build_interpreted_evidence_row(
    *,
    label: str,
    presence_entry: Optional[Mapping[str, Any]],
    passive_device: Optional[Any],
    visibility_device: Optional[Mapping[str, Any]],
    runtime_device: Optional[Mapping[str, Any]],
    console_entry: Optional[Mapping[str, Any]],
    system_console: Mapping[str, Any],
    manual_entry: Optional[Mapping[str, Any]],
    manual_observation: Optional[Mapping[str, Any]],
    manual_motion: Optional[Mapping[str, Any]],
    probe_pending: bool,
    last_probe_completed_at: float,
    probe_run_count: int,
    now_s: Optional[float] = None,
    visibility_identity_text: str = VIS_IDENTITY_UNKNOWN,
    visibility_last_seen_text: str = VIS_IDENTITY_UNKNOWN,
    visibility_packet_count_text: str = VIS_PACKET_COUNT_UNKNOWN,
    visibility_packet_rate_text: str = VIS_PACKET_RATE_UNKNOWN,
) -> Dict[str, Any]:
    """
    NAME
        build_interpreted_evidence_row - Build one shared Evidence-tab interpretation row.
    """
    if now_s is None:
        import time

        now_s = time.time()
    probe_snapshot = build_runtime_probe_snapshot(
        runtime_device,
        label=label,
        probe_pending=probe_pending,
        last_probe_completed_at=last_probe_completed_at,
        probe_run_count=probe_run_count,
        now_s=now_s,
    )
    probe_attachment = _active_probe_attachment(runtime_device)
    presence_bucket = VIS_IDENTITY_UNKNOWN
    presence_value = (
        presence_entry.get(PRESENCE_KEY_SCORE)
        if isinstance(presence_entry, Mapping)
        else None
    )
    if isinstance(presence_entry, Mapping):
        presence_bucket = str(
            presence_entry.get(PRESENCE_KEY_BUCKET, VIS_IDENTITY_UNKNOWN)
        ).strip() or VIS_IDENTITY_UNKNOWN
    presence_age_text = (
        str(presence_entry.get(PRESENCE_KEY_AGE_TEXT, VIS_IDENTITY_UNKNOWN)).strip()
        if isinstance(presence_entry, Mapping)
        else VIS_IDENTITY_UNKNOWN
    )
    raw_probe_bucket = str(probe_snapshot.get(PROBE_KEY_BUCKET, VIS_IDENTITY_UNKNOWN)).strip() or VIS_IDENTITY_UNKNOWN
    probe_bucket = raw_probe_bucket
    probe_age_bucket = str(probe_snapshot.get(PROBE_AGE_BUCKET_FIELD, VIS_IDENTITY_UNKNOWN)).strip() or VIS_IDENTITY_UNKNOWN
    probe_age_text = str(probe_snapshot.get(PROBE_AGE_TEXT_FIELD, EVIDENCE_STATUS_NOT_RUN)).strip() or EVIDENCE_STATUS_NOT_RUN
    passive_summary = EVIDENCE_SOURCE_NONE
    passive_visible = False
    passive_identity = EVIDENCE_STATUS_UNKNOWN
    passive_confidence = EVIDENCE_CONFIDENCE_LOW
    passive_expected_status = TEXT_EMPTY
    passive_gaps: list[str] = []
    passive_family_summaries: Tuple[str, ...] = ()
    if passive_device is not None:
        passive_summary = EVIDENCE_NOTE_SEPARATOR.join(
            (
                f"presence={str(getattr(passive_device, 'presence_confidence', TEXT_EMPTY)).strip() or TEXT_EMPTY}",
                f"score={int(getattr(passive_device, 'presence_score', 0))}/100",
            )
        )
        passive_visible = int(getattr(passive_device, "presence_score", 0)) > 0
        passive_identity = EVIDENCE_STATUS_MATCHING if passive_visible else EVIDENCE_STATUS_UNKNOWN
        passive_confidence = str(
            getattr(passive_device, "presence_confidence", EVIDENCE_CONFIDENCE_LOW)
        ).strip().upper() or EVIDENCE_CONFIDENCE_LOW
        passive_expected_status = str(getattr(passive_device, "expected_status", TEXT_EMPTY)).strip().lower()
        passive_gaps = list(getattr(passive_device, "evidence_gaps", ()) or ())
        passive_family_summaries = tuple(getattr(passive_device, "evidence_family_summaries", ()) or ())
    elif isinstance(visibility_device, Mapping):
        passive_summary = " / ".join((visibility_last_seen_text, visibility_packet_rate_text))
        visibility = visibility_device.get("visibility") if isinstance(visibility_device.get("visibility"), Mapping) else {}
        passive_visible = any(value is True for value in visibility.values())
        if visibility_identity_text != VIS_IDENTITY_UNKNOWN:
            passive_identity = EVIDENCE_STATUS_MATCHING
    elif isinstance(runtime_device, Mapping) and isinstance(runtime_device.get("lastSeenMs"), (int, float)):
        passive_summary = visibility_last_seen_text
    console_summary = console_entry.get(CONSOLE_KEY_SUMMARY) if isinstance(console_entry, Mapping) else EVIDENCE_SOURCE_NONE
    console_events = console_entry.get(CONSOLE_KEY_EVENTS, []) if isinstance(console_entry, Mapping) else []
    console_has_error = bool(console_entry.get(CONSOLE_KEY_HAS_ERROR)) if isinstance(console_entry, Mapping) else False
    console_has_warn = bool(console_entry.get(CONSOLE_KEY_HAS_WARN)) if isinstance(console_entry, Mapping) else False
    manual_auto_result = (
        str(manual_observation.get("autoResult", TEXT_EMPTY)).strip()
        if isinstance(manual_observation, Mapping)
        else TEXT_EMPTY
    )
    manual_age_sec = _manual_age_seconds(manual_entry, now_s)
    manual_recent_operability = isinstance(manual_age_sec, (int, float)) and manual_age_sec <= EVIDENCE_MANUAL_OPERABILITY_WINDOW_SEC
    manual_recent_identity = isinstance(manual_age_sec, (int, float)) and manual_age_sec <= EVIDENCE_MANUAL_IDENTITY_WINDOW_SEC
    manual_summary = MANUAL_PLACEHOLDER
    existence = EVIDENCE_STATUS_UNKNOWN
    operability = EVIDENCE_STATUS_UNKNOWN
    identity = passive_identity
    confidence = EVIDENCE_CONFIDENCE_LOW
    notes: list[str] = []
    evidence_state = EVIDENCE_STATE_UNKNOWN
    evidence_conflicted = False
    cmd_duty = _runtime_device_field_from_mapping(runtime_device, EVIDENCE_FIELD_CMD_DUTY)
    applied_duty = _runtime_device_field_from_mapping(runtime_device, EVIDENCE_FIELD_APPLIED_DUTY)
    velocity_rpm = _runtime_device_field_from_mapping(runtime_device, EVIDENCE_FIELD_VEL_RPM)
    motor_current = _runtime_device_field_from_mapping(runtime_device, EVIDENCE_FIELD_MOTOR_CURRENT_A)
    applied_v = _runtime_device_field_from_mapping(runtime_device, "appliedV")
    bus_v = _runtime_device_field_from_mapping(runtime_device, "busV")
    position_rot = _runtime_device_field_from_mapping(runtime_device, EVIDENCE_FIELD_POSITION_ROT)
    motor_attachment = runtime_motor_attachment(dict(runtime_device or {}))
    manual_snapshot = build_manual_snapshot(
        manual_entry=manual_entry,
        manual_observation=manual_observation,
        manual_motion=manual_motion,
        runtime_values={
            EVIDENCE_FIELD_CMD_DUTY: cmd_duty,
            EVIDENCE_FIELD_APPLIED_DUTY: applied_duty,
            EVIDENCE_FIELD_VEL_RPM: velocity_rpm,
            EVIDENCE_FIELD_MOTOR_CURRENT_A: motor_current,
            EVIDENCE_FIELD_POSITION_ROT: position_rot,
        },
        now_s=now_s,
    )
    motion_commanded = (
        isinstance(cmd_duty, (int, float)) and abs(float(cmd_duty)) >= MOTION_CMD_THRESHOLD_DUTY
    ) or (
        isinstance(applied_duty, (int, float)) and abs(float(applied_duty)) >= MOTION_CMD_THRESHOLD_DUTY
    )
    motion_detected = isinstance(velocity_rpm, (int, float)) and abs(float(velocity_rpm)) >= MOTION_MIN_RPM
    position_delta_rot = None
    manual_motion_window_active = False
    manual_motion_failed = False
    if isinstance(manual_motion, Mapping):
        started_at = manual_motion.get("startedAt")
        duty_value = manual_motion.get("duty")
        start_position_rot = manual_motion.get("startPositionRot")
        if isinstance(position_rot, (int, float)) and isinstance(start_position_rot, (int, float)):
            position_delta_rot = float(position_rot) - float(start_position_rot)
        if isinstance(started_at, (int, float)) and isinstance(duty_value, (int, float)):
            age_sec = max(0.0, float(now_s) - float(started_at))
            if age_sec <= MANUAL_MOTION_WINDOW_SEC and abs(float(duty_value)) >= MOTION_CMD_THRESHOLD_DUTY:
                manual_motion_window_active = True
                motion_commanded = True
                motion_detected = motion_detected or bool(manual_motion.get("sawMotion"))
                if not motion_detected and isinstance(position_delta_rot, (int, float)):
                    motion_detected = abs(float(position_delta_rot)) >= MOTION_MIN_POSITION_DELTA_ROT
                if age_sec >= MANUAL_MOTION_SETTLE_SEC and not motion_detected:
                    manual_motion_failed = True
    if manual_auto_result == MANUAL_AUTO_RESULT_ROTATION:
        motion_detected = True
        manual_motion_failed = False
    is_infrastructure_device = _is_infrastructure_device(label)
    passive_supports_presence_override = (
        passive_visible
        and passive_confidence in (EVIDENCE_CONFIDENCE_HIGH, EVIDENCE_CONFIDENCE_MEDIUM)
        and passive_expected_status != "missing"
        and bool(passive_family_summaries)
    )
    if isinstance(presence_entry, Mapping):
        presence_existence = str(presence_entry.get(PRESENCE_KEY_EXISTENCE, EVIDENCE_STATUS_UNKNOWN)).strip() or EVIDENCE_STATUS_UNKNOWN
        presence_confidence = str(presence_entry.get(PRESENCE_KEY_CONFIDENCE, EVIDENCE_CONFIDENCE_LOW)).strip() or EVIDENCE_CONFIDENCE_LOW
        if presence_existence == EVIDENCE_STATUS_PRESENT:
            existence = EVIDENCE_STATUS_PRESENT
            confidence = presence_confidence
            evidence_state = EVIDENCE_STATE_OK
        elif presence_existence == EVIDENCE_STATUS_ABSENT:
            if passive_supports_presence_override and not console_has_error:
                existence = EVIDENCE_STATUS_PRESENT
                confidence = EVIDENCE_CONFIDENCE_MEDIUM
                evidence_state = EVIDENCE_STATE_DEGRADED
                evidence_conflicted = True
                notes.append(EVIDENCE_NOTE_PASSIVE_OVERRIDES_RUNTIME_ABSENCE)
            elif is_infrastructure_device:
                existence = EVIDENCE_STATUS_UNKNOWN
                confidence = EVIDENCE_CONFIDENCE_LOW
                evidence_state = EVIDENCE_STATE_UNKNOWN
                notes.append(EVIDENCE_NOTE_INFRA_SCOPE_ABSENCE)
            else:
                existence = EVIDENCE_STATUS_ABSENT
                confidence = presence_confidence
                evidence_state = EVIDENCE_STATE_MISSING
    if probe_attachment is None:
        probe_bucket = PROBE_BUCKET_NOT_RUN
    elif probe_age_bucket == PROBE_AGE_STALE:
        notes.append(EVIDENCE_PROBE_NOTE_STALE)
    elif probe_age_bucket == PROBE_AGE_AGING:
        notes.append(EVIDENCE_PROBE_NOTE_AGING)
    if probe_bucket == PRESENCE_VALUE_PRESENT and probe_age_bucket != PROBE_AGE_STALE:
        if existence == EVIDENCE_STATUS_UNKNOWN:
            existence = EVIDENCE_STATUS_PRESENT
        if operability == EVIDENCE_STATUS_UNKNOWN:
            operability = EVIDENCE_STATUS_OK
        if confidence == EVIDENCE_CONFIDENCE_LOW:
            confidence = EVIDENCE_CONFIDENCE_MEDIUM
        if evidence_state == EVIDENCE_STATE_UNKNOWN:
            evidence_state = EVIDENCE_STATE_OK
    elif probe_bucket == "degraded" and probe_age_bucket != PROBE_AGE_STALE:
        if existence == EVIDENCE_STATUS_UNKNOWN:
            existence = EVIDENCE_STATUS_PRESENT
        operability = EVIDENCE_STATUS_DEGRADED
        confidence = EVIDENCE_CONFIDENCE_MEDIUM
        evidence_state = EVIDENCE_STATE_DEGRADED
    elif probe_bucket == PRESENCE_VALUE_ABSENT and probe_age_bucket != PROBE_AGE_STALE:
        if existence == EVIDENCE_STATUS_PRESENT:
            existence = EVIDENCE_STATUS_CONFLICT
            evidence_conflicted = True
            notes.append("Full probe says absent but live presence check says present.")
            if confidence == EVIDENCE_CONFIDENCE_HIGH:
                confidence = EVIDENCE_CONFIDENCE_MEDIUM
        elif existence == EVIDENCE_STATUS_UNKNOWN:
            existence = EVIDENCE_STATUS_ABSENT
            confidence = EVIDENCE_CONFIDENCE_HIGH
            evidence_state = EVIDENCE_STATE_MISSING
        if operability == EVIDENCE_STATUS_UNKNOWN:
            operability = EVIDENCE_STATUS_FAILED
    if probe_age_bucket == PROBE_AGE_AGING:
        if confidence == EVIDENCE_CONFIDENCE_HIGH:
            confidence = EVIDENCE_CONFIDENCE_MEDIUM
        elif confidence == EVIDENCE_CONFIDENCE_MEDIUM:
            confidence = EVIDENCE_CONFIDENCE_LOW
    if existence == EVIDENCE_STATUS_UNKNOWN and passive_visible:
        existence = EVIDENCE_STATUS_PRESENT
        confidence = passive_confidence if passive_device is not None else EVIDENCE_CONFIDENCE_MEDIUM
        evidence_state = EVIDENCE_STATE_OK
    elif existence == EVIDENCE_STATUS_UNKNOWN and passive_device is not None and passive_expected_status == "missing":
        existence = EVIDENCE_STATUS_ABSENT
        confidence = passive_confidence
        evidence_state = EVIDENCE_STATE_MISSING
    if console_has_error:
        if existence == EVIDENCE_STATUS_PRESENT:
            operability = EVIDENCE_STATUS_DEGRADED
            confidence = EVIDENCE_CONFIDENCE_MEDIUM
            evidence_state = EVIDENCE_STATE_DEGRADED
        elif existence == EVIDENCE_STATUS_UNKNOWN:
            operability = EVIDENCE_STATUS_FAILED
            evidence_state = EVIDENCE_STATE_DEGRADED
        if any(EVIDENCE_TEXT_DEVICE_TIMEOUT in str(entry).lower() for entry in console_events):
            notes.append("Device-specific timeout evidence present.")
    elif console_has_warn and operability == EVIDENCE_STATUS_UNKNOWN:
        operability = EVIDENCE_STATUS_DEGRADED
        confidence = EVIDENCE_CONFIDENCE_LOW
        evidence_state = EVIDENCE_STATE_DEGRADED
    if bool(system_console.get(CONSOLE_KEY_SYSTEM_CONFLICT)):
        notes.append("System-level console fault may reflect broader CAN isolation.")
        evidence_conflicted = True
        if confidence == EVIDENCE_CONFIDENCE_HIGH and probe_bucket != PRESENCE_VALUE_ABSENT:
            confidence = EVIDENCE_CONFIDENCE_MEDIUM
        elif confidence == EVIDENCE_CONFIDENCE_MEDIUM:
            confidence = EVIDENCE_CONFIDENCE_LOW
    if isinstance(manual_entry, Mapping):
        outcome = str(manual_entry.get("outcome", TEXT_EMPTY)).strip().lower()
        manual_summary = MANUAL_OUTCOME_LABELS.get(outcome, outcome or MANUAL_PLACEHOLDER)
        if outcome == MANUAL_OUTCOME_CORRECT:
            if not manual_recent_identity:
                notes.append(EVIDENCE_MANUAL_NOTE_STALE)
            elif probe_bucket == PRESENCE_VALUE_ABSENT or console_has_error:
                existence = EVIDENCE_STATUS_CONFLICT if probe_bucket == PRESENCE_VALUE_ABSENT else existence
                operability = EVIDENCE_STATUS_CONFLICT
                identity = EVIDENCE_STATUS_MATCHING
                confidence = EVIDENCE_CONFIDENCE_LOW
                evidence_state = EVIDENCE_STATE_DEGRADED
                evidence_conflicted = True
                notes.append(EVIDENCE_MANUAL_NOTE_CONFLICT)
            elif manual_recent_operability:
                existence = EVIDENCE_STATUS_PRESENT
                operability = EVIDENCE_STATUS_OK
                identity = EVIDENCE_STATUS_MATCHING
                confidence = EVIDENCE_CONFIDENCE_HIGH
                evidence_state = EVIDENCE_STATE_OK
            else:
                existence = EVIDENCE_STATUS_PRESENT
                identity = EVIDENCE_STATUS_MATCHING
                confidence = EVIDENCE_CONFIDENCE_MEDIUM
                notes.append(EVIDENCE_MANUAL_NOTE_AGE_IDENTITY_ONLY)
        elif outcome == MANUAL_OUTCOME_NO_RESPONSE:
            if manual_recent_operability:
                operability = EVIDENCE_STATUS_FAILED
                confidence = EVIDENCE_CONFIDENCE_HIGH
                evidence_state = EVIDENCE_STATE_DEGRADED
            else:
                notes.append(EVIDENCE_MANUAL_NOTE_STALE)
        elif outcome in (MANUAL_OUTCOME_INTERMITTENT, MANUAL_OUTCOME_DEGRADED):
            if manual_recent_operability:
                existence = EVIDENCE_STATUS_PRESENT
                operability = EVIDENCE_STATUS_DEGRADED
                confidence = EVIDENCE_CONFIDENCE_HIGH
                evidence_state = EVIDENCE_STATE_DEGRADED
            else:
                notes.append(EVIDENCE_MANUAL_NOTE_STALE)
        elif outcome in (MANUAL_OUTCOME_WRONG_DEVICE, MANUAL_OUTCOME_WRONG_BRANCH):
            if manual_recent_identity:
                existence = EVIDENCE_STATUS_PRESENT
                identity = EVIDENCE_STATUS_WRONG
                confidence = EVIDENCE_CONFIDENCE_HIGH if manual_recent_operability else EVIDENCE_CONFIDENCE_MEDIUM
                if manual_recent_operability:
                    operability = EVIDENCE_STATUS_FAILED
                evidence_state = EVIDENCE_STATE_IDENTITY
                if not manual_recent_operability:
                    notes.append(EVIDENCE_MANUAL_NOTE_AGE_IDENTITY_ONLY)
            else:
                notes.append(EVIDENCE_MANUAL_NOTE_STALE)
        elif outcome == MANUAL_OUTCOME_UNCERTAIN:
            confidence = EVIDENCE_CONFIDENCE_LOW
            notes.append("Operator marked manual result uncertain.")
    motion_verdict_position_delta = position_delta_rot
    if not isinstance(motion_verdict_position_delta, (int, float)) and isinstance(manual_observation, Mapping):
        motion_verdict_position_delta = manual_observation.get("maxAbsPositionDeltaRot")
    motion_verdict = infer_motor_runtime_verdict(
        present=existence != EVIDENCE_STATUS_ABSENT and existence != EVIDENCE_STATUS_UNKNOWN,
        cmd_duty=cmd_duty,
        applied_duty=applied_duty,
        applied_v=applied_v,
        bus_v=bus_v,
        vel_rpm=velocity_rpm,
        position_delta_rot=motion_verdict_position_delta,
        motor_current_a=motor_current,
        attachment=motor_attachment,
        duty_threshold=MOTION_CMD_THRESHOLD_DUTY,
        rpm_threshold=MOTION_MIN_RPM,
        position_delta_threshold=MOTION_MIN_POSITION_DELTA_ROT,
        current_active_threshold=0.2,
        low_bus_v_threshold=7.0,
        applied_v_active_threshold=1.0,
    )
    if manual_auto_result == MANUAL_AUTO_RESULT_ROTATION:
        motion_detected = True
    elif manual_auto_result == MANUAL_AUTO_RESULT_NO_ROTATION and motion_commanded:
        motion_detected = False
    if motion_commanded:
        if motion_detected or str(motion_verdict.get("result", TEXT_EMPTY)).strip() == RESULT_ROTATING:
            if existence == EVIDENCE_STATUS_UNKNOWN:
                existence = EVIDENCE_STATUS_PRESENT
            if operability == EVIDENCE_STATUS_UNKNOWN:
                operability = EVIDENCE_STATUS_OK
            confidence = EVIDENCE_CONFIDENCE_HIGH if confidence == EVIDENCE_CONFIDENCE_LOW else confidence
            if evidence_state == EVIDENCE_STATE_UNKNOWN:
                evidence_state = EVIDENCE_STATE_OK
            notes.append(EVIDENCE_MOTION_NOTE_ROTATING)
        elif manual_motion_failed or (not manual_motion_window_active):
            operability = EVIDENCE_STATUS_FAILED
            confidence = EVIDENCE_CONFIDENCE_HIGH if probe_bucket == PRESENCE_VALUE_PRESENT else EVIDENCE_CONFIDENCE_MEDIUM
            evidence_state = EVIDENCE_STATE_DEGRADED
            verdict_result = str(motion_verdict.get("result", TEXT_EMPTY)).strip()
            if verdict_result == RESULT_STALLED:
                notes.append("Motor commanded with current draw but no motion; possible stall/bind.")
            elif verdict_result == RESULT_ELECTRICAL:
                notes.append("Motor commanded with little current and no motion; possible electrical/output-path issue.")
            else:
                notes.append(EVIDENCE_MOTION_NOTE_NO_ROTATION)
    if identity == EVIDENCE_STATUS_MATCHING and existence == EVIDENCE_STATUS_PRESENT:
        if evidence_state == EVIDENCE_STATE_UNKNOWN:
            evidence_state = EVIDENCE_STATE_IDENTITY
    elif identity != EVIDENCE_STATUS_WRONG:
        identity = EVIDENCE_STATUS_UNKNOWN
    if (
        not is_infrastructure_device
        and probe_bucket in (VIS_IDENTITY_UNKNOWN, PROBE_BUCKET_NOT_RUN)
        and passive_visible
        and not console_has_error
    ):
        notes.append(EVIDENCE_NOTE_PASSIVE_WITHOUT_PROBE_RESULT)
    if passive_device is not None:
        notes.extend(note for note in passive_gaps if note and note not in notes)
    if not notes:
        notes.append(EVIDENCE_NOTE_NONE)
    presence_text = _build_presence_text(presence_entry, presence_bucket, presence_value, presence_age_text)
    passive_text = _build_passive_text(
        passive_device=passive_device,
        passive_visible=passive_visible,
        visibility_device=visibility_device,
        visibility_identity_text=visibility_identity_text,
        visibility_last_seen_text=visibility_last_seen_text,
        visibility_packet_count_text=visibility_packet_count_text,
        visibility_packet_rate_text=visibility_packet_rate_text,
    )
    console_text = (
        EVIDENCE_NOTE_SEPARATOR.join(str(entry) for entry in console_events)
        if console_events
        else str(system_console.get(CONSOLE_KEY_SYSTEM_TEXT, EVIDENCE_SOURCE_NONE))
    )
    probe_text = str(probe_snapshot.get(PROBE_TEXT_FIELD, EVIDENCE_SOURCE_NONE))
    manual_text = str(manual_snapshot.get(PROBE_TEXT_FIELD, MANUAL_PLACEHOLDER))
    return {
        INTERPRET_KEY_LABEL: label,
        INTERPRET_KEY_PASSIVE: passive_summary,
        INTERPRET_KEY_CONSOLE: console_summary or EVIDENCE_SOURCE_NONE,
        INTERPRET_KEY_PROBE: str(probe_snapshot.get(PROBE_SUMMARY_FIELD, TEXT_WAITING)),
        INTERPRET_KEY_PROBE_SCORE: str(probe_snapshot.get(PROBE_SCORE_TEXT_FIELD, EVIDENCE_SOURCE_NONE)),
        INTERPRET_KEY_MANUAL: str(manual_snapshot.get(MANUAL_SUMMARY_FIELD, manual_summary)),
        INTERPRET_KEY_EXISTENCE: existence,
        INTERPRET_KEY_OPERABILITY: operability,
        INTERPRET_KEY_IDENTITY: identity,
        INTERPRET_KEY_CONFIDENCE: confidence,
        INTERPRET_KEY_PRESENCE_TEXT: presence_text,
        INTERPRET_KEY_PASSIVE_TEXT: passive_text,
        INTERPRET_KEY_CONSOLE_TEXT: console_text,
        INTERPRET_KEY_PROBE_TEXT: probe_text,
        INTERPRET_KEY_MANUAL_TEXT: manual_text,
        INTERPRET_KEY_NOTES_TEXT: EVIDENCE_NOTE_SEPARATOR.join(notes),
        INTERPRET_KEY_STATE: evidence_state,
        INTERPRET_KEY_CONFLICTED: evidence_conflicted,
    }


def build_runtime_device_detail_snapshot(
    runtime_device: Optional[Mapping[str, Any]],
    *,
    manual_observation: Optional[Mapping[str, Any]] = None,
    now_s: Optional[float] = None,
) -> Dict[str, str]:
    """
    NAME
        build_runtime_device_detail_snapshot - Build a shared topology/runtime detail snapshot.
    """
    if now_s is None:
        import time

        now_s = time.time()
    snapshot = {
        DETAIL_SNAPSHOT_PRESENCE: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_PRESENCE_STATUS: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_PRESENCE_AGE: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_PRESENCE_SOURCE: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_FULL_PROBE_BUCKET: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_FULL_PROBE_AGE: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_FULL_PROBE_SCORE: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_FULL_PROBE_STATUS: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_FULL_PROBE_MESSAGE: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_LIFECYCLE_STATE: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_TESTABLE: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_OVERRIDE_ACTIVE: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_OVERRIDE_ORIGINATED: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_OVERRIDE_FAILURE: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_NOT_TESTABLE_REASON: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_LAST_SEEN: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_CURRENT_A: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_CURRENT_AVG_A: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_CURRENT_PEAK_A: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_CURRENT_NONZERO: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_CURRENT_SAMPLES: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_CMD_DUTY: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_APPLIED_DUTY: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_VEL_RPM: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_POSITION_ROT: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_POSITION_DELTA_ROT: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_TEMP_C: EVIDENCE_SOURCE_NONE,
    }
    if not isinstance(runtime_device, Mapping):
        return snapshot
    presence = runtime_device.get(RUNTIME_DEVICE_KEY_PRESENCE_CONFIDENCE)
    presence_check = _presence_attachment(runtime_device)
    probe = _active_probe_attachment(runtime_device)
    snapshot[DETAIL_SNAPSHOT_PRESENCE] = _format_optional_float(presence, precision=2)
    snapshot[DETAIL_SNAPSHOT_PRESENCE_STATUS] = (
        str(presence_check.get(PRESENCE_KEY_STATUS, EVIDENCE_SOURCE_NONE)).strip()
        if isinstance(presence_check, Mapping)
        else EVIDENCE_SOURCE_NONE
    )
    snapshot[DETAIL_SNAPSHOT_PRESENCE_SOURCE] = (
        str(presence_check.get(PRESENCE_KEY_SOURCE, EVIDENCE_SOURCE_NONE)).strip()
        if isinstance(presence_check, Mapping)
        else EVIDENCE_SOURCE_NONE
    )
    snapshot[DETAIL_SNAPSHOT_PRESENCE_AGE] = _format_age_text(
        _presence_age_seconds(
            presence_check.get(PRESENCE_KEY_UPDATED_AT_MS) if isinstance(presence_check, Mapping) else None,
            now_s,
        )
    )
    snapshot[DETAIL_SNAPSHOT_FULL_PROBE_BUCKET] = (
        str(probe.get(PROBE_KEY_BUCKET, EVIDENCE_SOURCE_NONE)).strip()
        if isinstance(probe, Mapping)
        else EVIDENCE_SOURCE_NONE
    )
    snapshot[DETAIL_SNAPSHOT_FULL_PROBE_AGE] = _format_probe_age_text(
        _presence_age_seconds(
            probe.get(PROBE_KEY_UPDATED_AT_MS) if isinstance(probe, Mapping) else None,
            now_s,
        )
    )
    snapshot[DETAIL_SNAPSHOT_FULL_PROBE_SCORE] = _format_probe_score_text(probe)
    snapshot[DETAIL_SNAPSHOT_FULL_PROBE_STATUS] = (
        str(probe.get(PRESENCE_KEY_STATUS, EVIDENCE_SOURCE_NONE)).strip()
        if isinstance(probe, Mapping)
        else EVIDENCE_SOURCE_NONE
    )
    snapshot[DETAIL_SNAPSHOT_FULL_PROBE_MESSAGE] = (
        str(probe.get(PRESENCE_KEY_MESSAGE, EVIDENCE_SOURCE_NONE)).strip()
        if isinstance(probe, Mapping)
        else EVIDENCE_SOURCE_NONE
    )
    snapshot[DETAIL_SNAPSHOT_LIFECYCLE_STATE] = str(runtime_device.get("lifecycleState", EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE
    snapshot[DETAIL_SNAPSHOT_TESTABLE] = _bool_text(runtime_device.get("testable"))
    snapshot[DETAIL_SNAPSHOT_OVERRIDE_ACTIVE] = _bool_text(runtime_device.get("overrideActive"))
    snapshot[DETAIL_SNAPSHOT_OVERRIDE_ORIGINATED] = _bool_text(runtime_device.get("overrideOriginated"))
    snapshot[DETAIL_SNAPSHOT_OVERRIDE_FAILURE] = _bool_text(runtime_device.get("overrideFailure"))
    snapshot[DETAIL_SNAPSHOT_NOT_TESTABLE_REASON] = str(runtime_device.get("notTestableReason", EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE
    snapshot[DETAIL_SNAPSHOT_LAST_SEEN] = _format_last_seen_text(runtime_device.get("lastSeenMs"), now_s)
    snapshot[DETAIL_SNAPSHOT_CURRENT_A] = _format_optional_float(_runtime_display_current_a(runtime_device), precision=2)
    snapshot[DETAIL_SNAPSHOT_CURRENT_AVG_A] = _format_optional_float(_runtime_device_field_from_mapping(runtime_device, "currentAvgA"), precision=2)
    snapshot[DETAIL_SNAPSHOT_CURRENT_PEAK_A] = _format_optional_float(_runtime_device_field_from_mapping(runtime_device, "currentPeakA"), precision=2)
    snapshot[DETAIL_SNAPSHOT_CURRENT_NONZERO] = _format_optional_float(_runtime_device_field_from_mapping(runtime_device, "currentNonzeroRatio"), precision=2)
    current_samples = _runtime_device_field_from_mapping(runtime_device, "currentSampleCount")
    snapshot[DETAIL_SNAPSHOT_CURRENT_SAMPLES] = str(int(current_samples)) if isinstance(current_samples, (int, float)) else EVIDENCE_SOURCE_NONE
    snapshot[DETAIL_SNAPSHOT_CMD_DUTY] = _format_optional_float(_runtime_device_field_from_mapping(runtime_device, EVIDENCE_FIELD_CMD_DUTY), precision=2)
    snapshot[DETAIL_SNAPSHOT_APPLIED_DUTY] = _format_optional_float(_runtime_device_field_from_mapping(runtime_device, EVIDENCE_FIELD_APPLIED_DUTY), precision=2)
    snapshot[DETAIL_SNAPSHOT_VEL_RPM] = _format_optional_float(_runtime_device_field_from_mapping(runtime_device, EVIDENCE_FIELD_VEL_RPM), precision=2)
    position_rot = _runtime_device_field_from_mapping(runtime_device, EVIDENCE_FIELD_POSITION_ROT)
    snapshot[DETAIL_SNAPSHOT_POSITION_ROT] = _format_optional_float(position_rot, precision=2)
    position_delta_rot = None
    if isinstance(manual_observation, Mapping):
        position_delta_rot = manual_observation.get("positionDeltaRot")
        max_abs_position_delta_rot = manual_observation.get("maxAbsPositionDeltaRot")
        if not isinstance(position_delta_rot, (int, float)) and isinstance(max_abs_position_delta_rot, (int, float)):
            position_delta_rot = max_abs_position_delta_rot
    snapshot[DETAIL_SNAPSHOT_POSITION_DELTA_ROT] = _format_optional_float(position_delta_rot, precision=2)
    snapshot[DETAIL_SNAPSHOT_TEMP_C] = _format_optional_float(_runtime_device_field_from_mapping(runtime_device, "tempC"), precision=1)
    return snapshot


def _resolve_profile_path(profile_path: str) -> str:
    """
    NAME
        _resolve_profile_path - Resolve the effective profile path for passive discovery integration.
    """
    clean = str(profile_path or TEXT_EMPTY).strip()
    if clean:
        return clean
    return default_profile_path()


def _runtime_device_field_from_mapping(runtime_device: Optional[Mapping[str, Any]], key: str) -> Any:
    """
    NAME
        _runtime_device_field_from_mapping - Read a runtime/motor field from top-level or motor attachments.
    """
    if not isinstance(runtime_device, Mapping):
        return None
    value = runtime_device.get(key)
    if value is not None:
        return value
    attachments = runtime_device.get(RUNTIME_DEVICE_KEY_ATTACHMENTS)
    if not isinstance(attachments, list):
        return None
    for attachment in attachments:
        if not isinstance(attachment, Mapping):
            continue
        attachment_type = str(attachment.get(ATTACHMENT_KEY_TYPE, TEXT_EMPTY)).strip()
        if attachment_type not in ("revMotor", "ctreMotor"):
            continue
        value = attachment.get(key)
        if value is not None:
            return value
    return None


def _runtime_display_current_a(runtime_device: Optional[Mapping[str, Any]]) -> Any:
    """
    NAME
        _runtime_display_current_a - Return the best current reading for one runtime device.
    """
    current_a = _runtime_device_field_from_mapping(runtime_device, EVIDENCE_FIELD_MOTOR_CURRENT_A)
    if isinstance(current_a, (int, float)):
        return current_a
    instant_current_a = _runtime_device_field_from_mapping(runtime_device, "currentInstantA")
    return instant_current_a


def _string_list_values(value: Any) -> list[str]:
    """
    NAME
        _string_list_values - Normalize one arbitrary list of strings.
    """
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = str(item or TEXT_EMPTY).strip()
        if text:
            result.append(text)
    return result


def _build_presence_text(
    presence_entry: Optional[Mapping[str, Any]],
    presence_bucket: str,
    presence_value: Any,
    presence_age_text: str,
) -> str:
    """
    NAME
        _build_presence_text - Format one shared presence evidence block.
    """
    if isinstance(presence_entry, Mapping):
        lines = [
            EVIDENCE_NOTE_SEPARATOR.join(
                (
                    f"bucket={presence_bucket}",
                    f"score={float(presence_value):.2f}" if isinstance(presence_value, (int, float)) else "score=--",
                    f"updated={presence_age_text}",
                    f"source={str(presence_entry.get(PRESENCE_KEY_SOURCE, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE}",
                )
            )
        ]
        message_text = str(presence_entry.get(PRESENCE_KEY_MESSAGE, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE
        if message_text:
            lines.append(message_text)
        return "\n".join(lines)
    if isinstance(presence_value, (int, float)):
        return EVIDENCE_NOTE_SEPARATOR.join(
            (
                f"bucket={presence_bucket}",
                f"score={float(presence_value):.2f}",
                f"updated={presence_age_text}",
                "source=runtimeState",
            )
        )
    return EVIDENCE_SOURCE_NONE


def _build_passive_text(
    *,
    passive_device: Optional[Any],
    passive_visible: bool,
    visibility_device: Optional[Mapping[str, Any]],
    visibility_identity_text: str,
    visibility_last_seen_text: str,
    visibility_packet_count_text: str,
    visibility_packet_rate_text: str,
) -> str:
    """
    NAME
        _build_passive_text - Format one shared passive evidence block.
    """
    if passive_device is not None:
        lines = [
            EVIDENCE_NOTE_SEPARATOR.join(
                (
                    "source=passive_discovery_poc",
                    f"identity={EVIDENCE_STATUS_MATCHING if passive_visible else EVIDENCE_STATUS_UNKNOWN}",
                    f"presence={str(getattr(passive_device, 'presence_confidence', TEXT_EMPTY)).strip() or TEXT_EMPTY}",
                    f"score={int(getattr(passive_device, 'presence_score', 0))}/100",
                )
            )
        ]
        passive_family_summaries = tuple(getattr(passive_device, "evidence_family_summaries", ()) or ())
        if passive_family_summaries:
            lines.append(", ".join(passive_family_summaries[:4]))
        if isinstance(visibility_device, Mapping):
            lines.append(
                EVIDENCE_NOTE_SEPARATOR.join(
                    (
                        "observer=CANable",
                        f"lastSeen={visibility_last_seen_text}",
                        f"packets={visibility_packet_count_text}",
                        f"rate={visibility_packet_rate_text}",
                    )
                )
            )
        return "\n".join(lines)
    if isinstance(visibility_device, Mapping):
        return EVIDENCE_NOTE_SEPARATOR.join(
            (
                "source=CANable observer",
                f"identity={visibility_identity_text}",
                f"lastSeen={visibility_last_seen_text}",
                f"packets={visibility_packet_count_text}",
                f"rate={visibility_packet_rate_text}",
            )
        )
    return EVIDENCE_SOURCE_NONE


def _bool_text(value: Any) -> str:
    """
    NAME
        _bool_text - Format one optional truthy runtime field.
    """
    if value is None:
        return EVIDENCE_SOURCE_NONE
    return "yes" if bool(value) else "no"


def _format_optional_float(value: Any, *, precision: int) -> str:
    """
    NAME
        _format_optional_float - Format one optional float field.
    """
    if not isinstance(value, (int, float)):
        return EVIDENCE_SOURCE_NONE
    return f"{float(value):.{precision}f}"


def _format_last_seen_text(last_seen_ms: Any, now_s: float) -> str:
    """
    NAME
        _format_last_seen_text - Format one runtime last-seen timestamp.
    """
    if not isinstance(last_seen_ms, (int, float)) or float(last_seen_ms) <= 0.0:
        return EVIDENCE_SOURCE_NONE
    age_sec = max(0.0, float(now_s) - (float(last_seen_ms) / 1000.0))
    return _format_age_text(age_sec)


def _index_topology_by_label(topology_record: Any) -> Dict[str, Dict[str, Any]]:
    """
    NAME
        _index_topology_by_label - Index topology enrichment rows by canonical device label.
    """
    indexed: Dict[str, Dict[str, Any]] = {}
    evidence_rows = getattr(topology_record, "evidence_records", ())
    for row in evidence_rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("kind", TEXT_EMPTY)).strip() != "topology_node":
            continue
        label = str(row.get(KEY_LABEL, TEXT_EMPTY)).strip()
        if not label:
            continue
        indexed[label.lower()] = {
            KEY_TOPOLOGY_NODE_KEY: row.get(KEY_TOPOLOGY_NODE_KEY),
            KEY_TOPOLOGY_NODE_TYPE: str(row.get(KEY_TOPOLOGY_NODE_TYPE, TEXT_EMPTY)).strip(),
            KEY_TOPOLOGY_NEIGHBOR_COUNT: row.get("neighborCount"),
        }
    return indexed


def _expected_rows_from_profile_devices(
    profile_devices: Mapping[str, Mapping[str, Any]],
) -> Dict[Tuple[int, int, int], Dict[str, object]]:
    """
    NAME
        _expected_rows_from_profile_devices - Build passive-discovery expected rows from the UI profile catalog.
    """
    rows: Dict[Tuple[int, int, int], Dict[str, object]] = {}
    for device in profile_devices.values():
        if not isinstance(device, Mapping):
            continue
        try:
            manufacturer = int(device.get(KEY_MANUFACTURER))
            device_type = int(device.get(KEY_DEVICE_TYPE))
            device_id = int(device.get(KEY_ID))
        except Exception:
            continue
        rows[(manufacturer, device_type, device_id)] = {
            KEY_LABEL: str(device.get(KEY_LABEL, TEXT_EMPTY)).strip(),
            KEY_MODEL: str(device.get(KEY_MODEL, TEXT_EMPTY)).strip(),
            KEY_PROFILE_NODE: str(device.get(KEY_PROFILE_NODE, TEXT_EMPTY)).strip(),
            KEY_BUS: str(device.get(KEY_BUS, TEXT_EMPTY)).strip(),
        }
    return rows


def _normalize_presence_entry(
    label: str,
    runtime_device: Optional[Mapping[str, Any]],
    now_s: float,
) -> Dict[str, Any]:
    """
    NAME
        _normalize_presence_entry - Convert one runtime presence snapshot into a UI-stable normalized record.
    """
    attachment = _presence_attachment(runtime_device)
    score_value = _presence_score_value(runtime_device)
    bucket = PRESENCE_VALUE_UNKNOWN
    source = EVIDENCE_SOURCE_NONE
    updated_at_ms = None
    message = EVIDENCE_SOURCE_NONE
    if isinstance(attachment, Mapping):
        bucket = str(attachment.get(PRESENCE_KEY_BUCKET, PRESENCE_VALUE_UNKNOWN)).strip().lower() or PRESENCE_VALUE_UNKNOWN
        source = str(attachment.get(PRESENCE_KEY_SOURCE, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE
        updated_at_ms = attachment.get(PRESENCE_KEY_UPDATED_AT_MS)
        message = str(attachment.get(PRESENCE_KEY_MESSAGE, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE
    elif isinstance(score_value, (int, float)):
        bucket = _presence_bucket_from_score(float(score_value))
        source = "runtimeState"
    age_seconds = _presence_age_seconds(updated_at_ms, now_s)
    return {
        KEY_LABEL: label,
        PRESENCE_KEY_BUCKET: bucket,
        PRESENCE_KEY_SCORE: score_value,
        PRESENCE_KEY_SOURCE: source,
        PRESENCE_KEY_UPDATED_AT_MS: updated_at_ms,
        PRESENCE_KEY_AGE_SECONDS: age_seconds,
        PRESENCE_KEY_AGE_TEXT: _format_age_text(age_seconds),
        PRESENCE_KEY_MESSAGE: message,
        PRESENCE_KEY_EXISTENCE: _presence_existence(bucket),
        PRESENCE_KEY_CONFIDENCE: _presence_confidence(bucket),
        KEY_EVIDENCE_ENGINE_ID: ENGINE_ID_PASSIVE_DISCOVERY_POC,
        KEY_EVIDENCE_ENGINE_LABEL: ENGINE_LABEL_NEW,
    }


def _presence_attachment(runtime_device: Optional[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
    """
    NAME
        _presence_attachment - Return the presenceCheck attachment from one runtime device when present.
    """
    if not isinstance(runtime_device, Mapping):
        return None
    attachments = runtime_device.get(RUNTIME_DEVICE_KEY_ATTACHMENTS)
    if not isinstance(attachments, list):
        return None
    for attachment in attachments:
        if not isinstance(attachment, Mapping):
            continue
        attachment_type = str(attachment.get(ATTACHMENT_KEY_TYPE, TEXT_EMPTY)).strip()
        if attachment_type == ATTACHMENT_TYPE_PRESENCE_CHECK:
            return attachment
    return None


def _active_probe_attachment(runtime_device: Optional[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
    """
    NAME
        _active_probe_attachment - Return the activePresenceProbe attachment from one runtime device when present.
    """
    if not isinstance(runtime_device, Mapping):
        return None
    attachments = runtime_device.get(RUNTIME_DEVICE_KEY_ATTACHMENTS)
    if not isinstance(attachments, list):
        return None
    for attachment in attachments:
        if not isinstance(attachment, Mapping):
            continue
        attachment_type = str(attachment.get(ATTACHMENT_KEY_TYPE, TEXT_EMPTY)).strip()
        if attachment_type == ATTACHMENT_TYPE_ACTIVE_PRESENCE_PROBE:
            return attachment
    return None


def _presence_score_value(runtime_device: Optional[Mapping[str, Any]]) -> Optional[float]:
    """
    NAME
        _presence_score_value - Return one normalized numeric presence score when available.
    """
    if not isinstance(runtime_device, Mapping):
        return None
    score = runtime_device.get(RUNTIME_DEVICE_KEY_PRESENCE_CONFIDENCE)
    if not isinstance(score, (int, float)):
        return None
    return float(score)


def _presence_bucket_from_score(score_value: float) -> str:
    """
    NAME
        _presence_bucket_from_score - Map one numeric runtime score into the UI's semantic presence bucket.
    """
    if score_value > PRESENCE_SCORE_HIGH_THRESHOLD:
        return PRESENCE_VALUE_PRESENT
    if score_value > PRESENCE_SCORE_LOW_THRESHOLD:
        return PRESENCE_VALUE_PRESENT
    return PRESENCE_VALUE_ABSENT


def _presence_age_seconds(updated_at_ms: Any, now_s: float) -> Optional[float]:
    """
    NAME
        _presence_age_seconds - Return elapsed age in seconds for one presence-check update time.
    """
    if not isinstance(updated_at_ms, (int, float)) or float(updated_at_ms) <= 0.0:
        return None
    return max(0.0, float(now_s) - (float(updated_at_ms) / 1000.0))


def _format_age_text(age_seconds: Optional[float]) -> str:
    """
    NAME
        _format_age_text - Format one optional elapsed age for Evidence-tab display.
    """
    if not isinstance(age_seconds, (int, float)):
        return EVIDENCE_SOURCE_NONE
    return TEXT_SECONDS_AGO_FORMAT.format(value=float(age_seconds))


def _presence_existence(bucket: str) -> str:
    """
    NAME
        _presence_existence - Map a normalized presence bucket into the Evidence-tab existence vocabulary.
    """
    if bucket == PRESENCE_VALUE_PRESENT:
        return EVIDENCE_STATUS_PRESENT
    if bucket == PRESENCE_VALUE_ABSENT:
        return EVIDENCE_STATUS_ABSENT
    return EVIDENCE_STATUS_UNKNOWN


def _presence_confidence(bucket: str) -> str:
    """
    NAME
        _presence_confidence - Map one normalized presence bucket into the Evidence-tab confidence vocabulary.
    """
    if bucket == PRESENCE_VALUE_PRESENT:
        return EVIDENCE_CONFIDENCE_HIGH
    if bucket == PRESENCE_VALUE_ABSENT:
        return EVIDENCE_CONFIDENCE_MEDIUM
    return EVIDENCE_CONFIDENCE_LOW


def _probe_bucket_value(attachment: Optional[Mapping[str, Any]]) -> str:
    """
    NAME
        _probe_bucket_value - Return the normalized probe bucket for one attachment.
    """
    if not isinstance(attachment, Mapping):
        return PROBE_BUCKET_UNKNOWN
    bucket = str(attachment.get(PROBE_KEY_BUCKET, PROBE_BUCKET_UNKNOWN)).strip().lower()
    return bucket or PROBE_BUCKET_UNKNOWN


def _format_probe_score_text(attachment: Optional[Mapping[str, Any]]) -> str:
    """
    NAME
        _format_probe_score_text - Format one probe attachment score for UI display.
    """
    if not isinstance(attachment, Mapping):
        return EVIDENCE_SOURCE_NONE
    bucket = _probe_bucket_value(attachment)
    if bucket in (PROBE_BUCKET_UNKNOWN, PROBE_BUCKET_NOT_RUN):
        return EVIDENCE_SOURCE_NONE
    score = attachment.get(PROBE_KEY_SCORE)
    max_score = attachment.get(PROBE_KEY_MAX_SCORE)
    if isinstance(score, (int, float)) and isinstance(max_score, (int, float)):
        return f"{int(score)}/{int(max_score)}"
    if isinstance(score, (int, float)):
        return str(int(score))
    return EVIDENCE_SOURCE_NONE


def _probe_age_bucket(age_seconds: Optional[float]) -> str:
    """
    NAME
        _probe_age_bucket - Classify one probe result by age.
    """
    if not isinstance(age_seconds, (int, float)):
        return PROBE_BUCKET_UNKNOWN
    if age_seconds <= PROBE_FRESH_SEC:
        return PROBE_AGE_FRESH
    if age_seconds <= PROBE_AGING_SEC:
        return PROBE_AGE_AGING
    return PROBE_AGE_STALE


def _format_probe_age_text(age_seconds: Optional[float]) -> str:
    """
    NAME
        _format_probe_age_text - Format one probe result age for UI display.
    """
    if not isinstance(age_seconds, (int, float)):
        return STATUS_NOT_RUN
    return _format_age_text(float(age_seconds))


def _probe_stats_text(
    *,
    probe_pending: bool,
    last_probe_completed_at: float,
    probe_run_count: int,
    now_s: float,
) -> str:
    """
    NAME
        _probe_stats_text - Summarize probe session cadence for the Evidence inspector.
    """
    if probe_pending:
        return PROBE_STATS_RUNNING
    if float(last_probe_completed_at or 0.0) > 0.0:
        age_sec = max(0.0, float(now_s) - float(last_probe_completed_at))
        return PROBE_STATS_LAST_COMPLETE_FMT.format(age=_format_age_text(age_sec))
    if int(probe_run_count or 0) > 0:
        return PROBE_STATS_RUN_COUNT_FMT.format(count=int(probe_run_count))
    return PROBE_STATS_WAITING


def _probe_missing_text(
    *,
    runtime_device: Optional[Mapping[str, Any]],
    last_probe_completed_at: float,
    is_infrastructure_device: bool = False,
) -> str:
    """
    NAME
        _probe_missing_text - Explain why no device-specific probe result exists.
    """
    if is_infrastructure_device:
        return TEXT_UPDATE_DELIM.join((PROBE_INFRA_SCOPE_NOTE, PROBE_INFRA_SCOPE_DETAIL))
    if float(last_probe_completed_at or 0.0) <= 0.0:
        return PROBE_NOT_RUN_YET
    if not isinstance(runtime_device, Mapping):
        return PROBE_NOT_IN_RUNTIME_SET
    if not bool(runtime_device.get("instantiated", False)):
        return PROBE_NOT_IN_RUNTIME_SET
    return PROBE_NO_DEVICE_RESULT


def _is_infrastructure_device(label: object) -> bool:
    """
    NAME
        _is_infrastructure_device - Return whether one Evidence label is a singleton infrastructure device.
    """
    normalized = str(label or TEXT_EMPTY).strip().lower()
    return normalized in INFRASTRUCTURE_DEVICE_LABELS


def _probe_display_bucket(raw_bucket: str, age_bucket: str) -> str:
    """
    NAME
        _probe_display_bucket - Convert raw probe state into the compact table bucket text.
    """
    if raw_bucket in (PROBE_BUCKET_UNKNOWN, PROBE_BUCKET_NOT_RUN):
        return TEXT_WAITING
    if age_bucket in (PROBE_AGE_AGING, PROBE_AGE_STALE):
        return f"{raw_bucket}*"
    return raw_bucket


def _string_list_value(attachment: Optional[Mapping[str, Any]], key: str) -> list[str]:
    """
    NAME
        _string_list_value - Return one attachment string-list field as a cleaned list.
    """
    if not isinstance(attachment, Mapping):
        return []
    values = attachment.get(key)
    if not isinstance(values, list):
        return []
    result = []
    for value in values:
        text = str(value or TEXT_EMPTY).strip()
        if text:
            result.append(text)
    return result


def _manual_age_seconds(entry: Optional[Mapping[str, Any]], now_s: float) -> Optional[float]:
    """
    NAME
        _manual_age_seconds - Return elapsed age in seconds for one recorded manual-test entry.
    """
    if not isinstance(entry, Mapping):
        return None
    recorded_epoch = entry.get("recordedAtEpochSec")
    if not isinstance(recorded_epoch, (int, float)):
        return None
    return max(0.0, float(now_s) - float(recorded_epoch))


def _build_manual_motion_snapshot(
    *,
    manual_observation: Optional[Mapping[str, Any]],
    manual_motion: Optional[Mapping[str, Any]],
    runtime_values: Mapping[str, Any],
    now_s: float,
) -> Dict[str, Any]:
    """
    NAME
        _build_manual_motion_snapshot - Normalize manual motion-check display fields.
    """
    cmd_duty = runtime_values.get("cmdDuty")
    applied_duty = runtime_values.get("appliedDuty")
    vel_rpm = runtime_values.get("velRpm")
    motor_current_a = runtime_values.get("motorCurrentA")
    position_rot = runtime_values.get("positionRot")
    position_delta_rot = runtime_values.get("positionDeltaRot")
    if isinstance(manual_observation, Mapping):
        cmd_duty = manual_observation.get("cmdDuty", cmd_duty)
        applied_duty = manual_observation.get("appliedDuty", applied_duty)
        vel_rpm = manual_observation.get("velRpm", vel_rpm)
        motor_current_a = manual_observation.get("motorCurrentA", motor_current_a)
        position_rot = manual_observation.get("positionRot", position_rot)
        position_delta_rot = manual_observation.get("positionDeltaRot", position_delta_rot)
        max_position_delta = manual_observation.get("maxAbsPositionDeltaRot")
        if not isinstance(position_delta_rot, (int, float)) and isinstance(max_position_delta, (int, float)):
            position_delta_rot = max_position_delta
    motion_commanded = (
        isinstance(cmd_duty, (int, float)) and abs(float(cmd_duty)) >= MOTION_CMD_THRESHOLD_DUTY
    ) or (
        isinstance(applied_duty, (int, float)) and abs(float(applied_duty)) >= MOTION_CMD_THRESHOLD_DUTY
    )
    motion_detected = isinstance(vel_rpm, (int, float)) and abs(float(vel_rpm)) >= MOTION_MIN_RPM
    manual_motion_window_active = False
    manual_motion_failed = False
    if isinstance(manual_motion, Mapping):
        started_at = manual_motion.get("startedAt")
        duty_value = manual_motion.get("duty")
        start_position_rot = manual_motion.get("startPositionRot")
        if isinstance(position_rot, (int, float)) and isinstance(start_position_rot, (int, float)):
            position_delta_rot = float(position_rot) - float(start_position_rot)
        if isinstance(started_at, (int, float)) and isinstance(duty_value, (int, float)):
            age_sec = max(0.0, float(now_s) - float(started_at))
            if age_sec <= MANUAL_MOTION_WINDOW_SEC and abs(float(duty_value)) >= MOTION_CMD_THRESHOLD_DUTY:
                manual_motion_window_active = True
                motion_commanded = True
                motion_detected = motion_detected or bool(manual_motion.get("sawMotion"))
                if not motion_detected and isinstance(position_delta_rot, (int, float)):
                    motion_detected = abs(float(position_delta_rot)) >= MOTION_MIN_POSITION_DELTA_ROT
                if age_sec >= MANUAL_MOTION_SETTLE_SEC and not motion_detected:
                    manual_motion_failed = True
    auto_result = (
        str(manual_observation.get("autoResult", TEXT_EMPTY)).strip()
        if isinstance(manual_observation, Mapping)
        else TEXT_EMPTY
    )
    if auto_result == MANUAL_AUTO_RESULT_ROTATION:
        motion_detected = True
        manual_motion_failed = False
    elif auto_result == MANUAL_AUTO_RESULT_NO_ROTATION and motion_commanded:
        motion_detected = False
    active = (
        motion_commanded
        or manual_motion_window_active
        or isinstance(manual_motion, Mapping)
        or isinstance(manual_observation, Mapping)
    )
    motion_state = MANUAL_MOTION_IDLE
    if motion_detected:
        motion_state = MANUAL_MOTION_PASS
    elif motion_commanded and (manual_motion_failed or not manual_motion_window_active):
        motion_state = MANUAL_MOTION_FAIL
    elif motion_commanded or manual_motion_window_active:
        motion_state = MANUAL_MOTION_ACTIVE
    elif auto_result == MANUAL_AUTO_RESULT_ROTATION:
        motion_state = MANUAL_MOTION_PASS
    elif auto_result == MANUAL_AUTO_RESULT_NO_ROTATION:
        motion_state = MANUAL_MOTION_FAIL
    elif auto_result == MANUAL_AUTO_RESULT_RUNNING:
        motion_state = MANUAL_MOTION_ACTIVE
    return {
        "active": active,
        "state": motion_state,
        "cmdDuty": cmd_duty,
        "appliedDuty": applied_duty,
        "velRpm": vel_rpm,
        "motorCurrentA": motor_current_a,
        "positionRot": position_rot,
        "positionDeltaRot": position_delta_rot,
    }


def _format_motion_value(value: Any) -> str:
    """
    NAME
        _format_motion_value - Format one motion sample value for shared manual-evidence text.
    """
    if isinstance(value, (int, float)):
        return f"{float(value):.2f}"
    return VALUE_NOT_APPLICABLE
