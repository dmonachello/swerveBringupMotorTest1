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

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from tools.can_nt.can_fault_inference import build_fault_diagnosis, render_fault_diagnosis
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
from tools.passive_discovery_poc.enrichment import enrich_console_log, enrich_ctre, enrich_topology
from tools.passive_discovery_poc.constants import MODEL_UNKNOWN
from tools.passive_discovery_poc.models import DeviceRecord, EnrichmentRecord, FamilyRecord, RunResult
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
SECTION_ENRICHMENT = "enrichment"
SECTION_TOPOLOGY_VIEW = "topologyView"
SECTION_INTERPRETATION = "interpretation"

PROFILE_PATH_AUTO = ""
TEXT_EMPTY = ""
TEXT_COLON_DELIM = ":"
TEXT_GUESS_PREFIX = "Guess: "
TEXT_SECTION_SEPARATOR = "; "
TEXT_ENGINE_BANNER_PREFIX = "Evidence Engine: "
TEXT_ROLLOUT_PREFIX = "rollout="
TEXT_SECTION_PREFIX = "sections="
FAULT_SNAPSHOT_KEY_ROWS = "rows"
FAULT_SNAPSHOT_KEY_RESULT = "result"
FAULT_SNAPSHOT_KEY_RENDERED_TEXT = "renderedText"
FAULT_SNAPSHOT_KEY_CANDIDATE_COUNT = "candidateCount"
FAULT_SNAPSHOT_KEY_RAN_AT = "ranAt"
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
INT_ZERO = 0
INT_ONE = 1
INT_TWO = 2
COUNT_THREE = 3
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
EVIDENCE_SOURCE_LOCAL_SNAPSHOT = "localSnapshot"
EVIDENCE_SOURCE_RUNTIME_STATE = "runtimeState"
EXPECTED_STATUS_UNEXPECTED = "unexpected"
ROLE_DEVICE_EMITTED_PREFIX = "DEVICE_EMITTED_"
ROLE_DEVICE_EMITTED_PRIMARY_STATUS = "DEVICE_EMITTED_PRIMARY_STATUS"
ROLE_DEVICE_EMITTED_SECONDARY_STATUS = "DEVICE_EMITTED_SECONDARY_STATUS"
ROLE_DEVICE_EMITTED_HEARTBEAT_HOUSEKEEPING = "DEVICE_EMITTED_HEARTBEAT_HOUSEKEEPING"
RUNTIME_DEVICE_KEY_ATTACHMENTS = "attachments"
RUNTIME_DEVICE_KEY_PRESENCE_CONFIDENCE = "presenceConfidence"
RUNTIME_DEVICE_KEY_INSTANTIATED = "instantiated"
RUNTIME_DEVICE_KEY_LAST_SEEN_MS = "lastSeenMs"
RUNTIME_DEVICE_KEY_LIFECYCLE_STATE = "lifecycleState"
RUNTIME_DEVICE_KEY_ACTIVE_GROUP_LABEL = "activeGroupLabel"
RUNTIME_DEVICE_KEY_BUS_V = "busV"
RUNTIME_DEVICE_KEY_TOTAL_CURRENT_A = "totalCurrentA"
RUNTIME_DEVICE_KEY_TEMP_C = "tempC"
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
CONSOLE_KEY_TOTAL_COUNT = "totalCount"
CONSOLE_KEY_STATS = "stats"
CONSOLE_KEY_STATS_TEXT = "statsText"
CONSOLE_KEY_EXAMPLES = "examples"
CONSOLE_KEY_RECORDS = "records"
CONSOLE_KEY_DEVICE_EVENT_COUNT = "deviceEventCount"
CONSOLE_KEY_SYSTEM_EVENT_COUNT = "systemEventCount"
CONSOLE_KEY_UNCLASSIFIED_EVENT_COUNT = "unclassifiedEventCount"
CONSOLE_KEY_TOP_FAULT_FAMILIES = "topFaultFamilies"
CONSOLE_KEY_TOP_VENDORS = "topVendors"
CONSOLE_KEY_FRESH_COUNT = "freshCount"
CONSOLE_KEY_AGING_COUNT = "agingCount"
CONSOLE_KEY_STALE_COUNT = "staleCount"
CONSOLE_KEY_FIRST_SEEN_SEC = "firstSeenSec"
CONSOLE_KEY_LAST_SEEN_SEC = "lastSeenSec"
CONSOLE_KEY_FIRST_SEEN_AGE_TEXT = "firstSeenAgeText"
CONSOLE_KEY_LAST_SEEN_AGE_TEXT = "lastSeenAgeText"
CONSOLE_KEY_SCOPE = "scope"
CONSOLE_KEY_VENDOR = "vendor"
CONSOLE_KEY_CAN_ID = "canId"
CONSOLE_KEY_FAULT_FAMILY = "faultFamily"
CONSOLE_KEY_MATCHED_LABEL = "matchedLabel"
CONSOLE_KEY_RAW_TEXT = "rawText"
CONSOLE_KEY_ORIGIN = "origin"
CONSOLE_KEY_SOURCE_LENS = "sourceLens"
CONSOLE_KEY_TIMESTAMP = "timestamp"
CONSOLE_KEY_AGE_SEC = "ageSec"
CONSOLE_KEY_FRESHNESS = "freshness"
CONSOLE_KEY_PARSER_CONFIDENCE = "parserConfidence"
CONSOLE_KEY_NORMALIZATION_STATUS = "normalizationStatus"
CONSOLE_KEY_REPEAT_RATE_HZ = "repeatRateHz"
CONSOLE_KEY_TOP_FAULT_FAMILY = "topFaultFamily"
CONSOLE_SEVERITY_WARN = "WARN"
CONSOLE_SEVERITY_ERROR = "ERROR"
CONSOLE_SEVERITY_FATAL = "FATAL"
CONSOLE_SEVERITY_INFO = "INFO"
CONSOLE_EVENT_BUS_FAULT = "BUS_FAULT_SUSPECTED"
CONSOLE_EVENT_CAN_TIMEOUT = "CAN_TIMEOUT"
CONSOLE_EVENT_TALON_STALE = "TALON_STATUS_SIGNAL_STALE"
CONSOLE_EVENT_SPARK_TIMEOUT = "SPARK_STATUS_TIMEOUT"
CONSOLE_EVENT_SPARK_FW_QUERY_FAIL = "SPARK_FW_QUERY_FAIL"
CONSOLE_EVENT_SPARK_WRONG_DEVICE = "SPARK_WRONG_DEVICE"
CONSOLE_EVENT_PDP_TIMEOUT = "PDP_STATUS_READER_TIMEOUT"
CONSOLE_EVENT_PDH_TIMEOUT = "PDH_STATUS_READER_TIMEOUT"
CONSOLE_EVENT_HIGH_UTIL = "CAN_BUS_UTIL_HIGH"
CONSOLE_EVENT_RECOVERED = "CAN_BUS_UTIL_RECOVER"
CONSOLE_EVENT_LOOP_OVERRUN = "LOOP_OVERRUN"
CONSOLE_EVENT_ERROR_SPIKE = "CAN_ERROR_SPIKE"
CONSOLE_EVENT_HAL_TIMEOUT = "HAL_CAN_RECEIVE_TIMEOUT"
CONSOLE_TEXT_STALE = "stale"
CONSOLE_EXAMPLE_LIMIT = 3
CONSOLE_TOP_COUNT_LIMIT = 3
CONSOLE_FRESH_SEC = 5.0
CONSOLE_AGING_SEC = 15.0
CONSOLE_FRESHNESS_FRESH = "fresh"
CONSOLE_FRESHNESS_AGING = "aging"
CONSOLE_FRESHNESS_STALE = "stale"
CONSOLE_ORIGIN_ROBOT = "robot"
CONSOLE_SOURCE_LENS = "console"
CONSOLE_NORMALIZATION_STRUCTURED = "structured"
CONSOLE_NORMALIZATION_PARTIAL = "partial_match"
CONSOLE_NORMALIZATION_UNCLASSIFIED = "unclassified"
CONSOLE_PARSER_CONFIDENCE_HIGH = "high"
CONSOLE_PARSER_CONFIDENCE_MEDIUM = "medium"
CONSOLE_PARSER_CONFIDENCE_LOW = "low"
CONSOLE_VENDOR_CTRE = "ctre"
CONSOLE_VENDOR_REV = "rev"
CONSOLE_VENDOR_WPILIB = "wpilib"
CONSOLE_VENDOR_UNKNOWN = "unknown"
CONSOLE_FAULT_FAMILY_CTRE_STALE = "ctre_stale_status_signal"
CONSOLE_FAULT_FAMILY_CTRE_TIMEOUT = "ctre_timeout"
CONSOLE_FAULT_FAMILY_CTRE_UNREACHABLE = "ctre_device_unreachable"
CONSOLE_FAULT_FAMILY_REV_TIMEOUT = "rev_timeout"
CONSOLE_FAULT_FAMILY_DEVICE_STALE = "device_signal_stale"
CONSOLE_FAULT_FAMILY_BUS_OFF = "bus_off"
CONSOLE_FAULT_FAMILY_TX_FULL = "tx_full"
CONSOLE_FAULT_FAMILY_ERROR_SPIKE = "error_spike"
CONSOLE_FAULT_FAMILY_HIGH_UTIL = "high_util"
CONSOLE_FAULT_FAMILY_RUNTIME_HEALTH = "runtime_health"
CONSOLE_FAULT_FAMILY_CONTROLLER_SIDE = "controller_side_comm_loss"
CONSOLE_FAULT_FAMILY_UNKNOWN_DEVICE = "unknown_device_fault"
CONSOLE_FAULT_FAMILY_UNKNOWN_SYSTEM = "unknown_system_fault"
CONSOLE_DEVICE_TYPE_TALON_FX = "talon fx"
CONSOLE_DEVICE_TYPE_SPARK_MAX = "spark max"
CONSOLE_DEVICE_TYPE_PDP = "pdp"
CONSOLE_DEVICE_TYPE_PDH = "pdh"
CONSOLE_DEVICE_TYPE_UNKNOWN = "unknown"
CONSOLE_DEVICE_FAILURE_FAMILIES = {
    CONSOLE_FAULT_FAMILY_CTRE_STALE,
    CONSOLE_FAULT_FAMILY_CTRE_TIMEOUT,
    CONSOLE_FAULT_FAMILY_CTRE_UNREACHABLE,
    CONSOLE_FAULT_FAMILY_REV_TIMEOUT,
    CONSOLE_FAULT_FAMILY_DEVICE_STALE,
}
CONSOLE_STATS_HEADER_GENERAL = "General Console Stats:"
CONSOLE_STATS_HEADER_DEVICE = "Selected Device Console Stats:"
CONSOLE_STATS_VERDICT_STRONG = "Console Verdict=Strong targeted negative evidence"
CONSOLE_STATS_VERDICT_WEAK = "Console Verdict=Weak targeted evidence"
CONSOLE_STATS_VERDICT_NONE = "Console Verdict=No device-targeted console evidence"
CONSOLE_STATS_SCOPE_DEVICE = "device"
CONSOLE_STATS_SCOPE_SYSTEM = "system"
CONSOLE_STATS_SCOPE_UNKNOWN = "unknown"
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
INFRA_RUNTIME_FRESH_SEC = 3.0
VISIBILITY_FRESH_SEC = 3.0
PROBE_STATS_WAITING = "Updates only when Full Probe is run."
PROBE_STATS_RUNNING = "Full Probe is running now."
PROBE_STATS_LAST_COMPLETE_FMT = "Last Full Probe completed {age} ago."
PROBE_STATS_RUN_COUNT_FMT = "Full Probe runs requested: {count}"
PROBE_NOT_RUN_YET = "Not run yet"
PROBE_NO_DEVICE_RESULT = "No device-specific full-probe result for this device."
PROBE_NOT_IN_RUNTIME_SET = "This device was not part of the active runtime probe set when Full Probe ran."
PROBE_INFRA_SCOPE_NOTE = "Not probed in current motion-test scope."
PROBE_INFRA_SCOPE_DETAIL = "Infrastructure device; evaluated from passive/runtime evidence instead."
PROBE_INFRA_RUNTIME_DETAIL = "No device-specific Full Probe result; using singleton runtime telemetry and passive/runtime evidence instead."
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
INTERPRET_KEY_DEVICE_TYPE = "deviceType"
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
INTERPRET_KEY_ENRICHMENT_TEXT = "enrichmentText"
INTERPRET_KEY_NOTES_TEXT = "notesText"
INTERPRET_KEY_STATE = "state"
INTERPRET_KEY_CONFLICTED = "conflicted"
INTERPRET_KEY_PRESENCE_SCORE = "presenceScore"
INTERPRET_KEY_PRESENCE_STATE = "presenceState"
INTERPRET_KEY_PRESENCE_REASONS = "presenceReasons"
INTERPRET_KEY_FRESHNESS = "freshness"
INTERPRET_KEY_SOURCE_SCORES = "sourceScores"
INTERPRET_KEY_DIRTY = "dirty"
INTERPRET_KEY_DIRTY_REASONS = "dirtyReasons"
INTERPRET_KEY_LAST_KNOWN_GOOD_AT = "lastKnownGoodAt"
INTERPRET_KEY_LAST_SEEN_PRESENT_AT = "lastSeenPresentAt"
INTERPRET_KEY_LAST_SEEN_MISSING_AT = "lastSeenMissingAt"
INTERPRET_KEY_LAST_STATE_CHANGE_AT = "lastStateChangeAt"
INTERPRET_KEY_LAST_EVALUATION_AT = "lastEvaluationAt"
INTERPRET_KEY_CHANGE_REASON = "changeReason"
INTERPRET_KEY_EVENT_LOG = "eventLog"


@dataclass(frozen=True)
class InterpretedDeviceState:
    """
    NAME
        InterpretedDeviceState - Shared typed interpreted evidence contract for one device.

    DESCRIPTION
        Holds the canonical interpreted evidence state before legacy row-dict adapters
        are applied for existing UI and fault-finder consumers.
    """

    label: str
    device_type: str
    passive: str
    console: str
    probe: str
    probe_score: str
    manual: str
    existence: str
    operability: str
    identity: str
    confidence: str
    presence_text: str
    passive_text: str
    console_text: str
    probe_text: str
    manual_text: str
    enrichment_text: str
    notes_text: str
    state: str
    conflicted: bool
    presence_score: int
    presence_state: str
    presence_reasons: List[str]
    freshness: str
    source_scores: Dict[str, Any]
    dirty: bool = False
    dirty_reasons: List[str] = None
    last_known_good_at: Optional[float] = None
    last_seen_present_at: Optional[float] = None
    last_seen_missing_at: Optional[float] = None
    last_state_change_at: Optional[float] = None
    last_evaluation_at: Optional[float] = None
    change_reason: str = EVIDENCE_SOURCE_NONE
    event_log: List[Mapping[str, Any]] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "presence_reasons", list(self.presence_reasons or []))
        object.__setattr__(self, "source_scores", dict(self.source_scores or {}))
        object.__setattr__(self, "dirty_reasons", list(self.dirty_reasons or []))
        object.__setattr__(self, "event_log", list(self.event_log or []))

    def to_row(self) -> Dict[str, Any]:
        """
        NAME
            to_row - Adapt the typed state to the legacy interpreted-row mapping contract.
        """
        return {
            INTERPRET_KEY_LABEL: self.label,
            INTERPRET_KEY_DEVICE_TYPE: self.device_type,
            INTERPRET_KEY_PASSIVE: self.passive,
            INTERPRET_KEY_CONSOLE: self.console,
            INTERPRET_KEY_PROBE: self.probe,
            INTERPRET_KEY_PROBE_SCORE: self.probe_score,
            INTERPRET_KEY_MANUAL: self.manual,
            INTERPRET_KEY_EXISTENCE: self.existence,
            INTERPRET_KEY_OPERABILITY: self.operability,
            INTERPRET_KEY_IDENTITY: self.identity,
            INTERPRET_KEY_CONFIDENCE: self.confidence,
            INTERPRET_KEY_PRESENCE_TEXT: self.presence_text,
            INTERPRET_KEY_PASSIVE_TEXT: self.passive_text,
            INTERPRET_KEY_CONSOLE_TEXT: self.console_text,
            INTERPRET_KEY_PROBE_TEXT: self.probe_text,
            INTERPRET_KEY_MANUAL_TEXT: self.manual_text,
            INTERPRET_KEY_ENRICHMENT_TEXT: self.enrichment_text,
            INTERPRET_KEY_NOTES_TEXT: self.notes_text,
            INTERPRET_KEY_STATE: self.state,
            INTERPRET_KEY_CONFLICTED: self.conflicted,
            INTERPRET_KEY_PRESENCE_SCORE: self.presence_score,
            INTERPRET_KEY_PRESENCE_STATE: self.presence_state,
            INTERPRET_KEY_PRESENCE_REASONS: list(self.presence_reasons),
            INTERPRET_KEY_FRESHNESS: self.freshness,
            INTERPRET_KEY_SOURCE_SCORES: dict(self.source_scores),
            INTERPRET_KEY_DIRTY: self.dirty,
            INTERPRET_KEY_DIRTY_REASONS: list(self.dirty_reasons),
            INTERPRET_KEY_LAST_KNOWN_GOOD_AT: self.last_known_good_at,
            INTERPRET_KEY_LAST_SEEN_PRESENT_AT: self.last_seen_present_at,
            INTERPRET_KEY_LAST_SEEN_MISSING_AT: self.last_seen_missing_at,
            INTERPRET_KEY_LAST_STATE_CHANGE_AT: self.last_state_change_at,
            INTERPRET_KEY_LAST_EVALUATION_AT: self.last_evaluation_at,
            INTERPRET_KEY_CHANGE_REASON: self.change_reason,
            INTERPRET_KEY_EVENT_LOG: list(self.event_log),
        }
EVIDENCE_NOTE_SEPARATOR = " | "
EVIDENCE_TEXT_DEVICE_TIMEOUT = "timeout"
EVIDENCE_TEXT_CAN_MESSAGE_STALE = "can message is stale"
EVIDENCE_TEXT_STATUS_SIGNAL_STALE = "status signal stale"
EVIDENCE_STATE_OK = "ok"
EVIDENCE_STATE_DEGRADED = "degraded"
EVIDENCE_STATE_FAILED = "failed"
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
EVIDENCE_PROBE_NOTE_INVALIDATED_CONSOLE = "Full-probe result was invalidated by fresh device-targeted console fault evidence."
EVIDENCE_MANUAL_NOTE_INVALIDATED_CONSOLE = "Manual result is being treated as historical only because fresh device-targeted console fault evidence conflicts with it."
EVIDENCE_PROBE_SUMMARY_INVALIDATED = "Invalidated by console fault"
EVIDENCE_MANUAL_SUMMARY_HISTORICAL_ONLY = "Historical only"
SOURCE_SCORE_PROBE_INVALIDATED = "Stale Full Probe invalidated by fresh console fault."
SOURCE_SCORE_MANUAL_INVALIDATED = "Manual evidence invalidated by fresh console fault."
EVIDENCE_PROBE_NOTE_ONE_SHOT = "Full Probe is a cached manual one-shot diagnostic result."
EVIDENCE_NOTE_PASSIVE_WITHOUT_PROBE_RESULT = "Passive CAN traffic is present, but Full Probe did not produce a device-specific result here."
EVIDENCE_NOTE_PASSIVE_OVERRIDES_RUNTIME_ABSENCE = "Passive CAN shows recurring device-emitted traffic even though the robot-local presence snapshot did not observe this device."
EVIDENCE_NOTE_INFRA_SCOPE_ABSENCE = "Infrastructure device is outside the current motion-test scope; local snapshot absence is not treated as definitive missing evidence."
EVIDENCE_NOTE_INFRA_RUNTIME_PRESENT = "Infrastructure singleton runtime telemetry is present even though the current motion-test scope did not include this device."
EVIDENCE_NOTE_INFRA_PASSIVE_PRESENT = "Infrastructure device observed by passive CAN even though the current motion-test scope did not include it."
EVIDENCE_NOTE_INFRA_PASSIVE_LIMITED = "Infrastructure device observed by passive CAN, but active test-scope/runtime evidence is limited."
EVIDENCE_NOTE_CONSOLE_DEVICE_TIMEOUT = "Device-targeted stale/timeout console evidence present."
EVIDENCE_NOTE_CONSOLE_DEVICE_TIMEOUT_CONFLICT = "Fresh targeted console fault evidence conflicts with weak/stale positive presence evidence."
EVIDENCE_NOTE_INFRA_CONSOLE_MISSING = "Fresh device-targeted console timeout evidence with no fresh positive corroboration is being treated as missing infrastructure presence."
EVIDENCE_NOTE_INFRA_RUNTIME_LOCAL_ONLY = "Fresh singleton runtime telemetry alone is being treated as robot-local evidence and is not enough to override direct CAN-loss evidence."
EVIDENCE_NOTE_NONE = "No major source conflict."
EVIDENCE_NOTE_RUNTIME_SNAPSHOT_UNCONFIRMED_MOTION = "Runtime scope snapshot says present, but recent motion check and passive CAN did not confirm the motor as physically present."
ENRICHMENT_SOURCE_CTRE = "ctreHttp"
ENRICHMENT_SOURCE_TOPOLOGY = "topology"
ENRICHMENT_SOURCE_CONSOLE_LOG = "consoleLog"
ENRICHMENT_STATUS_NOT_RUN = "not_run"
ENRICHMENT_STATUS_OK = "ok"
ENRICHMENT_STATUS_EMPTY = "empty"
ENRICHMENT_STATUS_UNAVAILABLE = "unavailable"
ENRICHMENT_DEVICE_KEY_CTRE = "ctre"
ENRICHMENT_DEVICE_KEY_TOPOLOGY = "topology"
ENRICHMENT_DEVICE_KEY_CONSOLE = "console"
ENRICHMENT_METADATA_BASE_URL = "baseUrl"
ENRICHMENT_METADATA_PROFILE_NAME = "profileName"
ENRICHMENT_METADATA_DEVICE_COUNT = "devices"
ENRICHMENT_METADATA_RECORD_COUNT = "records"
ENRICHMENT_CTRE_KEY_MODEL = "model"
ENRICHMENT_CTRE_KEY_FIRMWARE = "firmware"
ENRICHMENT_CTRE_KEY_FAULTS_TRUE = "faultsTrue"
ENRICHMENT_CTRE_KEY_STICKY_FAULTS_TRUE = "stickyFaultsTrue"
ENRICHMENT_CTRE_KEY_VENDOR = "vendor"
ENRICHMENT_CTRE_KEY_STATUS = "status"
ENRICHMENT_CTRE_KEY_CANBUS = "canbus"
ENRICHMENT_CTRE_KEY_HARDWARE_REV = "hardwareRev"
ENRICHMENT_CTRE_KEY_BOOTLOADER = "bootloader"
ENRICHMENT_CTRE_KEY_MANUFACTURED = "manufactured"
ENRICHMENT_CTRE_KEY_IS_PRO_LICENSED = "isProLicensed"
ENRICHMENT_CTRE_KEY_SUPPORTS_CONTROL = "supportsControl"
ENRICHMENT_CTRE_KEY_SUPPORTS_CONFIGS = "supportsConfigs"
ENRICHMENT_CTRE_KEY_SUPPORTS_DECORATED_SELF_TEST = "supportsDecoratedSelfTest"
CONSOLE_RECORD_KEY_CANDIDATE_PROFILE_NODE = "candidateProfileNode"
CONSOLE_RECORD_KEY_SEVERITY = "severity"
CONSOLE_RECORD_KEY_PARSED_EVIDENCE_TYPE = "parsedEvidenceType"
CONSOLE_RECORD_KEY_RAW_MESSAGE = "rawMessage"
ENRICHMENT_RUN_AGE_KEY = "ageText"
ENRICHMENT_RUN_STATUS_KEY = "status"
ENRICHMENT_RUN_SUMMARY_KEY = "summary"
ENRICHMENT_RUN_WARNINGS_KEY = "warnings"
ENRICHMENT_RUN_METADATA_KEY = "metadata"
ENRICHMENT_RUN_DEVICES_KEY = "devices"
ENRICHMENT_RUN_RECORDS_KEY = "records"
ENRICHMENT_RUN_AT_EPOCH_KEY = "ranAtEpochSec"
ENRICHMENT_RUN_LABEL = "Run Enrichment"
ENRICHMENT_STATUS_LABEL_PREFIX = "Enrichment: "
ENRICHMENT_STATUS_NOT_RUN_TEXT = "Enrichment: not run"
ENRICHMENT_STATUS_FMT = "Enrichment: ran {age} | deviceMatches={devices} | warnings={warnings}"
ENRICHMENT_PANEL_EMPTY = "Not run yet."
ENRICHMENT_PANEL_LENS = "Lens=host-side corroboration/enrichment sources; results are additive and not active-group scoped."
ENRICHMENT_PANEL_DEVICE_NONE = "deviceContribution=none for selected device"
ENRICHMENT_PANEL_DEVICE_PRESENT_FMT = "deviceContribution={sources}"
ENRICHMENT_CTRE_BASE_URL_FMT = "http://{host}:1250"
ENRICHMENT_NOTE_CTRE_CONFIRMED = "CTRE HTTP corroborated this CTRE device."
ENRICHMENT_NOTE_CTRE_ONLY = "CTRE HTTP reported this CTRE device even though passive CAN evidence was weak or absent."
ENRICHMENT_NOTE_CTRE_FAULTS = "CTRE HTTP reported active or sticky fault fields."
ENRICHMENT_NOTE_CONSOLE_ENRICHMENT_ERROR = "Console-log enrichment found device-specific warning/error evidence."
ENRICHMENT_NOTE_TOPOLOGY_CONFIRMED = "Topology enrichment confirms this device is part of the selected profile layout."
ENRICHMENT_NOTE_RUN_FMT = "Host enrichment ran {age}; ctreHttp={ctre}; topology={topology}; consoleLog={console}."
DETAIL_SNAPSHOT_PRESENCE = "presence"
DETAIL_SNAPSHOT_PRESENCE_STATUS = "presenceStatus"
DETAIL_SNAPSHOT_PRESENCE_AGE = "presenceAge"
DETAIL_SNAPSHOT_PRESENCE_SOURCE = "presenceSource"
DETAIL_SNAPSHOT_FULL_PROBE_BUCKET = "fullProbeBucket"
DETAIL_SNAPSHOT_FULL_PROBE_AGE = "fullProbeAge"
DETAIL_SNAPSHOT_FULL_PROBE_SCORE = "fullProbeScore"
DETAIL_SNAPSHOT_FULL_PROBE_STATUS = "fullProbeStatus"
DETAIL_SNAPSHOT_FULL_PROBE_MESSAGE = "fullProbeMessage"
DETAIL_SNAPSHOT_GROUP_MEMBER = "groupMember"
DETAIL_SNAPSHOT_SCOPE_ACTIVE = "scopeActive"
DETAIL_SNAPSHOT_INSTANTIATED = "instantiated"
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
INFRASTRUCTURE_CAN_PATH_SINGLETON_LABELS = {"pdp", "pdh"}
DEVICE_CLASS_MOTION = "motion_device"
DEVICE_CLASS_INFRASTRUCTURE = "infrastructure_device"
DEVICE_CLASS_UNPROFILED = "unprofiled_device"
PRESENCE_STATE_PRESENT = "present"
PRESENCE_STATE_MISSING = "missing"
PRESENCE_STATE_UNKNOWN = "unknown"
PRESENCE_STATE_CONFLICT = "conflict"
SOURCE_SCORE_KEY_SCORE = "score"
SOURCE_SCORE_KEY_STATE = "state"
SOURCE_SCORE_KEY_REASON = "reason"
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
ACTIVE_GROUP_NAME = "active-group"
LIFECYCLE_STATE_CONTROLLED_ACTIVE = "controlled-active"


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
            SECTION_ENRICHMENT: ENGINE_LABEL_NEW,
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
            SECTION_ENRICHMENT,
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
        evidence_section_title - Return the visible title for one Evidence inspector section.
    """
    return str(base_title or "")


def evidence_overall_title(base_title: str, status: Dict[str, Any]) -> str:
    """
    NAME
        evidence_overall_title - Return the visible title for the top-level Evidence surface.
    """
    return str(base_title or "")


def normalize_evidence_engine_status(status: Dict[str, Any]) -> Dict[str, Any]:
    """
    NAME
        normalize_evidence_engine_status - Recompute overall engine/rollout labels from section ownership.
    """
    sections = status.get("sections")
    if not isinstance(sections, dict):
        sections = {}
        status["sections"] = sections
    existing_section_labels = [
        str(value).strip() or ENGINE_LABEL_LEGACY
        for value in sections.values()
        if isinstance(value, str)
    ]
    fallback_label = str(status.get("engineLabel", ENGINE_LABEL_LEGACY)).strip() or ENGINE_LABEL_LEGACY
    if existing_section_labels and all(label == existing_section_labels[0] for label in existing_section_labels):
        fallback_label = existing_section_labels[0]
    elif existing_section_labels:
        label_counts: Dict[str, int] = {}
        for label in existing_section_labels:
            label_counts[label] = label_counts.get(label, 0) + 1
        fallback_label = max(
            sorted(label_counts.keys()),
            key=lambda candidate: label_counts.get(candidate, 0),
        )
    for section_key in (
        SECTION_PROFILE_INVENTORY,
        SECTION_PRESENCE_CHECK,
        SECTION_PASSIVE,
        SECTION_CONSOLE,
        SECTION_PROBE,
        SECTION_MANUAL,
        SECTION_ENRICHMENT,
        SECTION_TOPOLOGY_VIEW,
        SECTION_INTERPRETATION,
    ):
        sections.setdefault(section_key, fallback_label)
    labels = [
        str(sections.get(section_key, ENGINE_LABEL_LEGACY)).strip() or ENGINE_LABEL_LEGACY
        for section_key in (
            SECTION_PROFILE_INVENTORY,
            SECTION_PRESENCE_CHECK,
            SECTION_PASSIVE,
            SECTION_CONSOLE,
            SECTION_PROBE,
            SECTION_MANUAL,
            SECTION_ENRICHMENT,
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


def default_enrichment_run_snapshot() -> Dict[str, Any]:
    """
    NAME
        default_enrichment_run_snapshot - Return the empty host-side enrichment snapshot shape.
    """
    return {
        ENRICHMENT_RUN_AT_EPOCH_KEY: 0.0,
        ENRICHMENT_RUN_AGE_KEY: EVIDENCE_SOURCE_NONE,
        ENRICHMENT_RUN_DEVICES_KEY: {},
        ENRICHMENT_RUN_RECORDS_KEY: (),
        ENRICHMENT_RUN_WARNINGS_KEY: (),
        ENRICHMENT_RUN_METADATA_KEY: {
            ENRICHMENT_SOURCE_CTRE: {
                ENRICHMENT_RUN_STATUS_KEY: ENRICHMENT_STATUS_NOT_RUN,
                ENRICHMENT_RUN_SUMMARY_KEY: ENRICHMENT_PANEL_EMPTY,
            },
            ENRICHMENT_SOURCE_TOPOLOGY: {
                ENRICHMENT_RUN_STATUS_KEY: ENRICHMENT_STATUS_NOT_RUN,
                ENRICHMENT_RUN_SUMMARY_KEY: ENRICHMENT_PANEL_EMPTY,
            },
            ENRICHMENT_SOURCE_CONSOLE_LOG: {
                ENRICHMENT_RUN_STATUS_KEY: ENRICHMENT_STATUS_NOT_RUN,
                ENRICHMENT_RUN_SUMMARY_KEY: ENRICHMENT_PANEL_EMPTY,
            },
        },
    }


def refresh_enrichment_run_snapshot_age(
    snapshot: Optional[Mapping[str, Any]],
    *,
    now_s: Optional[float] = None,
) -> Dict[str, Any]:
    """
    NAME
        refresh_enrichment_run_snapshot_age - Return one enrichment snapshot copy with a fresh age text field.
    """
    result = dict(snapshot) if isinstance(snapshot, Mapping) else default_enrichment_run_snapshot()
    if now_s is None:
        import time

        now_s = time.time()
    ran_at = result.get(ENRICHMENT_RUN_AT_EPOCH_KEY)
    if isinstance(ran_at, (int, float)) and float(ran_at) > 0.0:
        age_sec = max(0.0, float(now_s) - float(ran_at))
        result[ENRICHMENT_RUN_AGE_KEY] = _format_age_text(age_sec)
    elif str(result.get(ENRICHMENT_RUN_AGE_KEY, TEXT_EMPTY)).strip() == TEXT_EMPTY:
        result[ENRICHMENT_RUN_AGE_KEY] = EVIDENCE_SOURCE_NONE
    return result


def enrichment_run_status_text(
    snapshot: Optional[Mapping[str, Any]],
    *,
    now_s: Optional[float] = None,
) -> str:
    """
    NAME
        enrichment_run_status_text - Build one concise host-visible enrichment run status line.
    """
    refreshed = refresh_enrichment_run_snapshot_age(snapshot, now_s=now_s)
    ran_at = refreshed.get(ENRICHMENT_RUN_AT_EPOCH_KEY)
    if not isinstance(ran_at, (int, float)) or float(ran_at) <= 0.0:
        return ENRICHMENT_STATUS_NOT_RUN_TEXT
    devices = refreshed.get(ENRICHMENT_RUN_DEVICES_KEY)
    warnings = refreshed.get(ENRICHMENT_RUN_WARNINGS_KEY)
    return ENRICHMENT_STATUS_FMT.format(
        age=str(refreshed.get(ENRICHMENT_RUN_AGE_KEY, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE,
        devices=len(devices) if isinstance(devices, Mapping) else 0,
        warnings=len(tuple(warnings)) if isinstance(warnings, (list, tuple)) else 0,
    )


def build_enrichment_run_snapshot(
    *,
    profile_devices: Mapping[str, Mapping[str, Any]],
    profile_path: str = PROFILE_PATH_AUTO,
    profile_name: str = TEXT_EMPTY,
    rio_host: str = TEXT_EMPTY,
    output_log_text: str = TEXT_EMPTY,
    now_s: Optional[float] = None,
) -> Dict[str, Any]:
    """
    NAME
        build_enrichment_run_snapshot - Run host-side corroboration sources and normalize one shared snapshot.
    """
    if now_s is None:
        import time

        now_s = time.time()
    snapshot = default_enrichment_run_snapshot()
    snapshot[ENRICHMENT_RUN_AT_EPOCH_KEY] = float(now_s)
    snapshot[ENRICHMENT_RUN_AGE_KEY] = _format_age_text(0.0)
    resolved_path = _resolve_profile_path(profile_path)
    devices_by_label: Dict[str, Dict[str, Any]] = {}
    warnings: List[str] = []
    records: List[EnrichmentRecord] = []

    topology_record = enrich_topology(resolved_path, profile_name=profile_name)
    records.append(topology_record)
    topology_by_label = _index_topology_by_label(topology_record)
    snapshot[ENRICHMENT_RUN_METADATA_KEY][ENRICHMENT_SOURCE_TOPOLOGY] = {
        ENRICHMENT_RUN_STATUS_KEY: ENRICHMENT_STATUS_OK,
        ENRICHMENT_RUN_SUMMARY_KEY: (
            f"profile={topology_record.metadata.get(ENRICHMENT_METADATA_PROFILE_NAME, profile_name or TEXT_EMPTY)}"
            + TEXT_UPDATE_DELIM
            + f"nodes={int(topology_record.metadata.get('topologyNodeCount', 0) or 0)}"
            + TEXT_UPDATE_DELIM
            + f"edges={int(topology_record.metadata.get('topologyEdgeCount', 0) or 0)}"
        ),
    }
    for label_key, topology_info in topology_by_label.items():
        device_entry = devices_by_label.setdefault(label_key, {})
        device_entry[ENRICHMENT_DEVICE_KEY_TOPOLOGY] = dict(topology_info)

    ctre_base_url = _ctre_base_url_for_rio(rio_host)
    ctre_rows: Dict[Tuple[int, int, int], Dict[str, object]] = {}
    if ctre_base_url:
        ctre_rows, ctre_warnings = enrich_ctre(ctre_base_url)
        warnings.extend(str(item) for item in ctre_warnings)
        snapshot[ENRICHMENT_RUN_METADATA_KEY][ENRICHMENT_SOURCE_CTRE] = {
            ENRICHMENT_RUN_STATUS_KEY: ENRICHMENT_STATUS_OK if ctre_rows else ENRICHMENT_STATUS_UNAVAILABLE,
            ENRICHMENT_RUN_SUMMARY_KEY: (
                f"baseUrl={ctre_base_url}"
                + TEXT_UPDATE_DELIM
                + f"devices={len(ctre_rows)}"
            ),
            "baseUrl": ctre_base_url,
        }
        if ctre_rows or ctre_warnings:
            records.append(
                EnrichmentRecord(
                    plugin_id=ENRICHMENT_SOURCE_CTRE,
                    source_class="enrichment",
                    source_mode="live",
                    metadata={ENRICHMENT_METADATA_BASE_URL: ctre_base_url},
                    device_enrichment=dict(ctre_rows),
                    warnings=tuple(str(item) for item in ctre_warnings),
                )
            )
        for label_key, profile_device in profile_devices.items():
            identity_key = _device_identity_key_from_profile_device(profile_device)
            if identity_key is None:
                continue
            ctre_entry = ctre_rows.get(identity_key)
            if not isinstance(ctre_entry, dict):
                continue
            device_entry = devices_by_label.setdefault(label_key, {})
            device_entry[ENRICHMENT_DEVICE_KEY_CTRE] = dict(ctre_entry)
    else:
        snapshot[ENRICHMENT_RUN_METADATA_KEY][ENRICHMENT_SOURCE_CTRE] = {
            ENRICHMENT_RUN_STATUS_KEY: ENRICHMENT_STATUS_UNAVAILABLE,
            ENRICHMENT_RUN_SUMMARY_KEY: "CTRE HTTP base URL unavailable.",
        }

    console_text = str(output_log_text or TEXT_EMPTY)
    console_record = _collect_console_log_enrichment(
        output_log_text=console_text,
        profile_path=resolved_path,
        profile_name=profile_name,
    )
    if console_record is not None:
        records.append(console_record)
        warnings.extend(str(item) for item in console_record.warnings)
        console_by_label = _index_console_enrichment_by_label(console_record)
        snapshot[ENRICHMENT_RUN_METADATA_KEY][ENRICHMENT_SOURCE_CONSOLE_LOG] = {
            ENRICHMENT_RUN_STATUS_KEY: ENRICHMENT_STATUS_OK if console_by_label else ENRICHMENT_STATUS_EMPTY,
            ENRICHMENT_RUN_SUMMARY_KEY: (
                f"{ENRICHMENT_METADATA_RECORD_COUNT}={len(tuple(console_record.evidence_records))}"
                + TEXT_UPDATE_DELIM
                + f"warnings={len(tuple(console_record.warnings))}"
            ),
        }
        for label_key, console_info in console_by_label.items():
            device_entry = devices_by_label.setdefault(label_key, {})
            device_entry[ENRICHMENT_DEVICE_KEY_CONSOLE] = dict(console_info)
    else:
        snapshot[ENRICHMENT_RUN_METADATA_KEY][ENRICHMENT_SOURCE_CONSOLE_LOG] = {
            ENRICHMENT_RUN_STATUS_KEY: ENRICHMENT_STATUS_EMPTY,
            ENRICHMENT_RUN_SUMMARY_KEY: "No output log text available to parse.",
        }

    snapshot[ENRICHMENT_RUN_DEVICES_KEY] = devices_by_label
    snapshot[ENRICHMENT_RUN_RECORDS_KEY] = tuple(records)
    snapshot[ENRICHMENT_RUN_WARNINGS_KEY] = tuple(warnings)
    return snapshot


def build_live_passive_result(
    visibility_provider: Any,
    profile_devices: Mapping[str, Mapping[str, Any]],
    *,
    ctre_enrichment: Optional[Mapping[Tuple[int, int, int], Mapping[str, object]]] = None,
    enrichment_records: Optional[Tuple[EnrichmentRecord, ...]] = None,
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
        ctre_enrichment=dict(ctre_enrichment or {}),
        enrichment_records=tuple(enrichment_records or ()),
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


def build_console_snapshot_from_entries(entries: Any, now_s: Optional[float] = None) -> Dict[str, Any]:
    """
    NAME
        build_console_snapshot_from_entries - Normalize host console monitor entries into the shared Evidence snapshot shape.
    """
    if now_s is None:
        import time

        now_s = time.time()
    result: Dict[str, Any] = {
        CONSOLE_SCOPE_DEVICES: {},
        CONSOLE_SCOPE_SYSTEM: [],
        CONSOLE_KEY_SYSTEM_TEXT: EVIDENCE_SOURCE_NONE,
        CONSOLE_KEY_SYSTEM_CONFLICT: False,
        CONSOLE_KEY_RECORDS: [],
        CONSOLE_KEY_STATS: {
            CONSOLE_KEY_TOTAL_COUNT: 0,
            CONSOLE_KEY_WARN_COUNT: 0,
            CONSOLE_KEY_ERROR_COUNT: 0,
            CONSOLE_KEY_FATAL_COUNT: 0,
            CONSOLE_KEY_DEVICE_EVENT_COUNT: 0,
            CONSOLE_KEY_SYSTEM_EVENT_COUNT: 0,
            CONSOLE_KEY_UNCLASSIFIED_EVENT_COUNT: 0,
            CONSOLE_KEY_EXAMPLES: [],
            CONSOLE_KEY_TOP_FAULT_FAMILIES: {},
            CONSOLE_KEY_TOP_VENDORS: {},
            CONSOLE_KEY_FRESH_COUNT: 0,
            CONSOLE_KEY_AGING_COUNT: 0,
            CONSOLE_KEY_STALE_COUNT: 0,
            CONSOLE_KEY_FIRST_SEEN_SEC: None,
            CONSOLE_KEY_LAST_SEEN_SEC: None,
        },
    }
    system_events = []
    stats = result[CONSOLE_KEY_STATS]
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
        device_id = getattr(entry, "device_id", None)
        event_count = int(getattr(entry, "count", 0) or 0)
        first_seen_sec = getattr(entry, "first_seen", None)
        last_seen_sec = getattr(entry, "last_seen", None)
        scoped_count = max(1, event_count)
        record = _console_normalized_record(
            event_type=event_type,
            severity=severity,
            message=message,
            device_label=device_label,
            device_id=device_id,
            first_seen_sec=first_seen_sec,
            last_seen_sec=last_seen_sec,
            event_count=event_count,
            now_s=now_s,
        )
        result[CONSOLE_KEY_RECORDS].append(record)
        stats[CONSOLE_KEY_TOTAL_COUNT] += scoped_count
        if severity == CONSOLE_SEVERITY_WARN:
            stats[CONSOLE_KEY_WARN_COUNT] += scoped_count
        elif severity == CONSOLE_SEVERITY_ERROR:
            stats[CONSOLE_KEY_ERROR_COUNT] += scoped_count
        elif severity == CONSOLE_SEVERITY_FATAL:
            stats[CONSOLE_KEY_FATAL_COUNT] += scoped_count
        _console_stats_increment_freshness(stats, str(record.get(CONSOLE_KEY_FRESHNESS, TEXT_EMPTY)).strip())
        _console_stats_increment_counter(stats[CONSOLE_KEY_TOP_FAULT_FAMILIES], str(record.get(CONSOLE_KEY_FAULT_FAMILY, TEXT_EMPTY)).strip(), scoped_count)
        _console_stats_increment_counter(stats[CONSOLE_KEY_TOP_VENDORS], str(record.get(CONSOLE_KEY_VENDOR, TEXT_EMPTY)).strip(), scoped_count)
        _console_stats_update_first_last(stats, first_seen_sec, last_seen_sec)
        if len(stats[CONSOLE_KEY_EXAMPLES]) < CONSOLE_EXAMPLE_LIMIT:
            stats[CONSOLE_KEY_EXAMPLES].append(event_summary)
        if device_label:
            stats[CONSOLE_KEY_DEVICE_EVENT_COUNT] += scoped_count
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
                    CONSOLE_KEY_TOTAL_COUNT: 0,
                    CONSOLE_KEY_EXAMPLES: [],
                    CONSOLE_KEY_RECORDS: [],
                    CONSOLE_KEY_SCOPE: CONSOLE_STATS_SCOPE_DEVICE,
                    CONSOLE_KEY_VENDOR: CONSOLE_VENDOR_UNKNOWN,
                    KEY_DEVICE_TYPE: CONSOLE_DEVICE_TYPE_UNKNOWN,
                    CONSOLE_KEY_CAN_ID: None,
                    CONSOLE_KEY_TOP_FAULT_FAMILY: EVIDENCE_SOURCE_NONE,
                    CONSOLE_KEY_FIRST_SEEN_SEC: None,
                    CONSOLE_KEY_LAST_SEEN_SEC: None,
                    CONSOLE_KEY_REPEAT_RATE_HZ: 0.0,
                    CONSOLE_KEY_PARSER_CONFIDENCE: CONSOLE_PARSER_CONFIDENCE_LOW,
                    CONSOLE_KEY_NORMALIZATION_STATUS: CONSOLE_NORMALIZATION_UNCLASSIFIED,
                    CONSOLE_KEY_FRESHNESS: CONSOLE_FRESHNESS_STALE,
                    KEY_LABEL: device_label,
                    KEY_EVIDENCE_ENGINE_ID: ENGINE_ID_PASSIVE_DISCOVERY_POC,
                    KEY_EVIDENCE_ENGINE_LABEL: ENGINE_LABEL_NEW,
                },
            )
            row[CONSOLE_KEY_EVENTS].append(event_summary)
            row[CONSOLE_KEY_TOTAL_COUNT] += scoped_count
            row[CONSOLE_KEY_RECORDS].append(record)
            row[CONSOLE_KEY_VENDOR] = str(record.get(CONSOLE_KEY_VENDOR, CONSOLE_VENDOR_UNKNOWN)).strip() or CONSOLE_VENDOR_UNKNOWN
            row[KEY_DEVICE_TYPE] = str(record.get(KEY_DEVICE_TYPE, CONSOLE_DEVICE_TYPE_UNKNOWN)).strip() or CONSOLE_DEVICE_TYPE_UNKNOWN
            row[CONSOLE_KEY_CAN_ID] = record.get(CONSOLE_KEY_CAN_ID)
            row[CONSOLE_KEY_TOP_FAULT_FAMILY] = str(record.get(CONSOLE_KEY_FAULT_FAMILY, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE
            row[CONSOLE_KEY_FIRST_SEEN_SEC] = _console_min_time_value(row.get(CONSOLE_KEY_FIRST_SEEN_SEC), first_seen_sec)
            row[CONSOLE_KEY_LAST_SEEN_SEC] = _console_max_time_value(row.get(CONSOLE_KEY_LAST_SEEN_SEC), last_seen_sec)
            row[CONSOLE_KEY_REPEAT_RATE_HZ] = _console_repeat_rate_hz(
                row[CONSOLE_KEY_TOTAL_COUNT],
                row[CONSOLE_KEY_FIRST_SEEN_SEC],
                row[CONSOLE_KEY_LAST_SEEN_SEC],
            )
            row[CONSOLE_KEY_PARSER_CONFIDENCE] = str(
                record.get(CONSOLE_KEY_PARSER_CONFIDENCE, CONSOLE_PARSER_CONFIDENCE_LOW)
            ).strip() or CONSOLE_PARSER_CONFIDENCE_LOW
            row[CONSOLE_KEY_NORMALIZATION_STATUS] = str(
                record.get(CONSOLE_KEY_NORMALIZATION_STATUS, CONSOLE_NORMALIZATION_UNCLASSIFIED)
            ).strip() or CONSOLE_NORMALIZATION_UNCLASSIFIED
            row[CONSOLE_KEY_FRESHNESS] = str(record.get(CONSOLE_KEY_FRESHNESS, CONSOLE_FRESHNESS_STALE)).strip() or CONSOLE_FRESHNESS_STALE
            if len(row[CONSOLE_KEY_EXAMPLES]) < CONSOLE_EXAMPLE_LIMIT:
                row[CONSOLE_KEY_EXAMPLES].append(event_summary)
            if severity == CONSOLE_SEVERITY_WARN:
                row[CONSOLE_KEY_HAS_WARN] = True
                row[CONSOLE_KEY_WARN_COUNT] += scoped_count
            elif severity == CONSOLE_SEVERITY_ERROR:
                row[CONSOLE_KEY_HAS_ERROR] = True
                row[CONSOLE_KEY_ERROR_COUNT] += scoped_count
            elif severity == CONSOLE_SEVERITY_FATAL:
                row[CONSOLE_KEY_HAS_ERROR] = True
                row[CONSOLE_KEY_FATAL_COUNT] += scoped_count
            if row[CONSOLE_KEY_SUMMARY] == EVIDENCE_SOURCE_NONE:
                row[CONSOLE_KEY_SUMMARY] = event_summary
        else:
            if str(record.get(CONSOLE_KEY_SCOPE, TEXT_EMPTY)).strip() == CONSOLE_STATS_SCOPE_SYSTEM:
                stats[CONSOLE_KEY_SYSTEM_EVENT_COUNT] += scoped_count
            else:
                stats[CONSOLE_KEY_UNCLASSIFIED_EVENT_COUNT] += scoped_count
            system_events.append(event_summary)
    stats[CONSOLE_KEY_TOP_FAULT_FAMILIES] = _console_top_counts(stats.get(CONSOLE_KEY_TOP_FAULT_FAMILIES))
    stats[CONSOLE_KEY_TOP_VENDORS] = _console_top_counts(stats.get(CONSOLE_KEY_TOP_VENDORS))
    stats[CONSOLE_KEY_FIRST_SEEN_AGE_TEXT] = _console_first_last_age_text(stats.get(CONSOLE_KEY_FIRST_SEEN_SEC), now_s)
    stats[CONSOLE_KEY_LAST_SEEN_AGE_TEXT] = _console_first_last_age_text(stats.get(CONSOLE_KEY_LAST_SEEN_SEC), now_s)
    for row in result[CONSOLE_SCOPE_DEVICES].values():
        if row[CONSOLE_KEY_SUMMARY] != EVIDENCE_SOURCE_NONE:
            row[CONSOLE_KEY_STATS_TEXT] = _console_device_stats_text(row)
            continue
        if row[CONSOLE_KEY_FATAL_COUNT] > 0 or row[CONSOLE_KEY_ERROR_COUNT] > 0:
            row[CONSOLE_KEY_SUMMARY] = (
                f"errors={row[CONSOLE_KEY_ERROR_COUNT]} fatal={row[CONSOLE_KEY_FATAL_COUNT]}"
            )
        elif row[CONSOLE_KEY_WARN_COUNT] > 0:
            row[CONSOLE_KEY_SUMMARY] = f"warn={row[CONSOLE_KEY_WARN_COUNT]}"
        row[CONSOLE_KEY_FIRST_SEEN_AGE_TEXT] = _console_first_last_age_text(row.get(CONSOLE_KEY_FIRST_SEEN_SEC), now_s)
        row[CONSOLE_KEY_LAST_SEEN_AGE_TEXT] = _console_first_last_age_text(row.get(CONSOLE_KEY_LAST_SEEN_SEC), now_s)
        row[CONSOLE_KEY_STATS_TEXT] = _console_device_stats_text(row)
    result[CONSOLE_SCOPE_SYSTEM] = system_events
    result[CONSOLE_KEY_SYSTEM_TEXT] = system_events[0] if system_events else EVIDENCE_SOURCE_NONE
    result[CONSOLE_KEY_SYSTEM_CONFLICT] = any(
        CONSOLE_EVENT_BUS_FAULT in event or CONSOLE_TEXT_STALE in event.lower()
        for event in system_events
    )
    result[CONSOLE_KEY_STATS_TEXT] = _console_general_stats_text(result)
    return result


def _console_general_stats_text(snapshot: Mapping[str, Any]) -> str:
    """
    NAME
        _console_general_stats_text - Render generalized console statistics for Evidence UI display.
    """
    stats = snapshot.get(CONSOLE_KEY_STATS, {}) if isinstance(snapshot, Mapping) else {}
    if not isinstance(stats, Mapping):
        return CONSOLE_STATS_HEADER_GENERAL + "\n" + EVIDENCE_SOURCE_NONE
    lines = [
        CONSOLE_STATS_HEADER_GENERAL,
        TEXT_UPDATE_DELIM.join(
            (
                f"total={int(stats.get(CONSOLE_KEY_TOTAL_COUNT, 0) or 0)}",
                f"device={int(stats.get(CONSOLE_KEY_DEVICE_EVENT_COUNT, 0) or 0)}",
                f"system={int(stats.get(CONSOLE_KEY_SYSTEM_EVENT_COUNT, 0) or 0)}",
                f"unclassified={int(stats.get(CONSOLE_KEY_UNCLASSIFIED_EVENT_COUNT, 0) or 0)}",
                f"warn={int(stats.get(CONSOLE_KEY_WARN_COUNT, 0) or 0)}",
                f"error={int(stats.get(CONSOLE_KEY_ERROR_COUNT, 0) or 0)}",
                f"fatal={int(stats.get(CONSOLE_KEY_FATAL_COUNT, 0) or 0)}",
            )
        ),
        TEXT_UPDATE_DELIM.join(
            (
                f"fresh={int(stats.get(CONSOLE_KEY_FRESH_COUNT, 0) or 0)}",
                f"aging={int(stats.get(CONSOLE_KEY_AGING_COUNT, 0) or 0)}",
                f"stale={int(stats.get(CONSOLE_KEY_STALE_COUNT, 0) or 0)}",
                f"firstSeen={str(stats.get(CONSOLE_KEY_FIRST_SEEN_AGE_TEXT, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE}",
                f"lastSeen={str(stats.get(CONSOLE_KEY_LAST_SEEN_AGE_TEXT, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE}",
            )
        ),
    ]
    top_fault_families = stats.get(CONSOLE_KEY_TOP_FAULT_FAMILIES, [])
    if isinstance(top_fault_families, list) and top_fault_families:
        lines.append(
            "topFaultFamilies=" + TEXT_COMMA_DELIM.join(
                f"{str(name).strip()}({int(count)})"
                for name, count in top_fault_families[:CONSOLE_TOP_COUNT_LIMIT]
                if str(name).strip()
            )
        )
    top_vendors = stats.get(CONSOLE_KEY_TOP_VENDORS, [])
    if isinstance(top_vendors, list) and top_vendors:
        lines.append(
            "topVendors=" + TEXT_COMMA_DELIM.join(
                f"{str(name).strip()}({int(count)})"
                for name, count in top_vendors[:CONSOLE_TOP_COUNT_LIMIT]
                if str(name).strip()
            )
        )
    examples = stats.get(CONSOLE_KEY_EXAMPLES, [])
    if isinstance(examples, list) and examples:
        lines.append("examples=" + TEXT_COMMA_DELIM.join(str(item).strip() for item in examples[:CONSOLE_EXAMPLE_LIMIT] if str(item).strip()))
    return "\n".join(lines)


def _console_device_stats_text(console_entry: Mapping[str, Any]) -> str:
    """
    NAME
        _console_device_stats_text - Render selected-device console statistics for Evidence UI display.
    """
    if not isinstance(console_entry, Mapping):
        return CONSOLE_STATS_HEADER_DEVICE + "\n" + CONSOLE_STATS_VERDICT_NONE
    has_error = bool(console_entry.get(CONSOLE_KEY_HAS_ERROR))
    has_warn = bool(console_entry.get(CONSOLE_KEY_HAS_WARN))
    verdict = CONSOLE_STATS_VERDICT_NONE
    if has_error:
        verdict = CONSOLE_STATS_VERDICT_STRONG
    elif has_warn:
        verdict = CONSOLE_STATS_VERDICT_WEAK
    lines = [
        CONSOLE_STATS_HEADER_DEVICE,
        verdict,
        TEXT_UPDATE_DELIM.join(
            (
                f"label={str(console_entry.get(KEY_LABEL, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE}",
                f"vendor={str(console_entry.get(CONSOLE_KEY_VENDOR, CONSOLE_VENDOR_UNKNOWN)).strip() or CONSOLE_VENDOR_UNKNOWN}",
                f"deviceType={str(console_entry.get(KEY_DEVICE_TYPE, CONSOLE_DEVICE_TYPE_UNKNOWN)).strip() or CONSOLE_DEVICE_TYPE_UNKNOWN}",
                f"canId={str(console_entry.get(CONSOLE_KEY_CAN_ID, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE}",
                f"total={int(console_entry.get(CONSOLE_KEY_TOTAL_COUNT, 0) or 0)}",
                f"warn={int(console_entry.get(CONSOLE_KEY_WARN_COUNT, 0) or 0)}",
                f"error={int(console_entry.get(CONSOLE_KEY_ERROR_COUNT, 0) or 0)}",
                f"fatal={int(console_entry.get(CONSOLE_KEY_FATAL_COUNT, 0) or 0)}",
            )
        ),
        TEXT_UPDATE_DELIM.join(
            (
                f"freshness={str(console_entry.get(CONSOLE_KEY_FRESHNESS, CONSOLE_FRESHNESS_STALE)).strip() or CONSOLE_FRESHNESS_STALE}",
                f"repeatRateHz={float(console_entry.get(CONSOLE_KEY_REPEAT_RATE_HZ, 0.0) or 0.0):.2f}",
                f"firstSeen={str(console_entry.get(CONSOLE_KEY_FIRST_SEEN_AGE_TEXT, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE}",
                f"lastSeen={str(console_entry.get(CONSOLE_KEY_LAST_SEEN_AGE_TEXT, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE}",
            )
        ),
    ]
    summary = str(console_entry.get(CONSOLE_KEY_SUMMARY, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE
    lines.append(f"summary={summary}")
    lines.append(
        TEXT_UPDATE_DELIM.join(
            (
                f"topFaultFamily={str(console_entry.get(CONSOLE_KEY_TOP_FAULT_FAMILY, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE}",
                f"parserConfidence={str(console_entry.get(CONSOLE_KEY_PARSER_CONFIDENCE, CONSOLE_PARSER_CONFIDENCE_LOW)).strip() or CONSOLE_PARSER_CONFIDENCE_LOW}",
                f"normalizationStatus={str(console_entry.get(CONSOLE_KEY_NORMALIZATION_STATUS, CONSOLE_NORMALIZATION_UNCLASSIFIED)).strip() or CONSOLE_NORMALIZATION_UNCLASSIFIED}",
            )
        )
    )
    examples = console_entry.get(CONSOLE_KEY_EXAMPLES, [])
    if isinstance(examples, list) and examples:
        lines.append("examples=" + TEXT_COMMA_DELIM.join(str(item).strip() for item in examples[:CONSOLE_EXAMPLE_LIMIT] if str(item).strip()))
    return "\n".join(lines)


def _console_normalized_record(
    *,
    event_type: str,
    severity: str,
    message: str,
    device_label: str,
    device_id: Any,
    first_seen_sec: Any,
    last_seen_sec: Any,
    event_count: int,
    now_s: float,
) -> Dict[str, Any]:
    """
    NAME
        _console_normalized_record - Convert one monitor entry into a structured console fault record.
    """
    scope = CONSOLE_STATS_SCOPE_DEVICE if device_label or isinstance(device_id, int) else CONSOLE_STATS_SCOPE_SYSTEM
    if not event_type:
        scope = CONSOLE_STATS_SCOPE_UNKNOWN
    vendor = _console_vendor_from_event_type(event_type)
    device_type = _console_device_type_from_event_type(event_type, message, device_label)
    fault_family = _console_fault_family_from_event_type(event_type, scope)
    can_id = _console_can_id_from_entry(device_id, message, device_label)
    age_sec = _console_age_seconds(last_seen_sec, now_s)
    freshness = _console_freshness_bucket(age_sec)
    parser_confidence = _console_parser_confidence(
        scope=scope,
        vendor=vendor,
        device_type=device_type,
        can_id=can_id,
        matched_label=device_label,
        fault_family=fault_family,
    )
    normalization_status = _console_normalization_status(
        scope=scope,
        fault_family=fault_family,
        parser_confidence=parser_confidence,
    )
    return {
        CONSOLE_KEY_SOURCE_LENS: CONSOLE_SOURCE_LENS,
        CONSOLE_KEY_ORIGIN: CONSOLE_ORIGIN_ROBOT,
        CONSOLE_KEY_SCOPE: scope,
        CONSOLE_KEY_VENDOR: vendor,
        KEY_DEVICE_TYPE: device_type,
        CONSOLE_KEY_CAN_ID: can_id,
        CONSOLE_KEY_MATCHED_LABEL: device_label or EVIDENCE_SOURCE_NONE,
        CONSOLE_KEY_FAULT_FAMILY: fault_family,
        CONSOLE_KEY_TIMESTAMP: float(last_seen_sec) if isinstance(last_seen_sec, (int, float)) else None,
        CONSOLE_KEY_AGE_SEC: age_sec,
        CONSOLE_KEY_FRESHNESS: freshness,
        CONSOLE_KEY_PARSER_CONFIDENCE: parser_confidence,
        CONSOLE_KEY_NORMALIZATION_STATUS: normalization_status,
        CONSOLE_KEY_RAW_TEXT: message,
        CONSOLE_KEY_SUMMARY: event_type,
        CONSOLE_KEY_TOTAL_COUNT: max(1, int(event_count or 0)),
        CONSOLE_KEY_FIRST_SEEN_SEC: float(first_seen_sec) if isinstance(first_seen_sec, (int, float)) else None,
        CONSOLE_KEY_LAST_SEEN_SEC: float(last_seen_sec) if isinstance(last_seen_sec, (int, float)) else None,
        "severity": severity or CONSOLE_SEVERITY_INFO,
    }


def _console_vendor_from_event_type(event_type: str) -> str:
    event_name = str(event_type or TEXT_EMPTY).strip().upper()
    if event_name in {CONSOLE_EVENT_TALON_STALE, CONSOLE_EVENT_PDP_TIMEOUT}:
        return CONSOLE_VENDOR_CTRE
    if event_name in {
        CONSOLE_EVENT_SPARK_TIMEOUT,
        CONSOLE_EVENT_SPARK_FW_QUERY_FAIL,
        CONSOLE_EVENT_SPARK_WRONG_DEVICE,
        CONSOLE_EVENT_PDH_TIMEOUT,
    }:
        return CONSOLE_VENDOR_REV
    if event_name in {CONSOLE_EVENT_LOOP_OVERRUN, CONSOLE_EVENT_HAL_TIMEOUT}:
        return CONSOLE_VENDOR_WPILIB
    if event_name in {
        CONSOLE_EVENT_HIGH_UTIL,
        CONSOLE_EVENT_RECOVERED,
        CONSOLE_EVENT_ERROR_SPIKE,
        CONSOLE_EVENT_CAN_TIMEOUT,
        CONSOLE_EVENT_BUS_FAULT,
    }:
        return CONSOLE_VENDOR_UNKNOWN
    return CONSOLE_VENDOR_UNKNOWN


def _console_device_type_from_event_type(event_type: str, message: str, device_label: str) -> str:
    event_name = str(event_type or TEXT_EMPTY).strip().upper()
    if event_name == CONSOLE_EVENT_TALON_STALE:
        return CONSOLE_DEVICE_TYPE_TALON_FX
    if event_name in {CONSOLE_EVENT_SPARK_TIMEOUT, CONSOLE_EVENT_SPARK_FW_QUERY_FAIL, CONSOLE_EVENT_SPARK_WRONG_DEVICE}:
        return CONSOLE_DEVICE_TYPE_SPARK_MAX
    if event_name == CONSOLE_EVENT_PDP_TIMEOUT or device_label.lower() == CONSOLE_DEVICE_TYPE_PDP:
        return CONSOLE_DEVICE_TYPE_PDP
    if event_name == CONSOLE_EVENT_PDH_TIMEOUT or device_label.lower() == CONSOLE_DEVICE_TYPE_PDH:
        return CONSOLE_DEVICE_TYPE_PDH
    lower_message = str(message or TEXT_EMPTY).strip().lower()
    if "talon fx" in lower_message:
        return CONSOLE_DEVICE_TYPE_TALON_FX
    if "spark max" in lower_message:
        return CONSOLE_DEVICE_TYPE_SPARK_MAX
    return CONSOLE_DEVICE_TYPE_UNKNOWN


def _console_can_id_from_entry(device_id: Any, message: str, device_label: str) -> Optional[int]:
    if isinstance(device_id, int):
        return int(device_id)
    import re

    label_match = re.search(r"(\d+)\s*$", str(device_label or TEXT_EMPTY).strip())
    if label_match is not None:
        try:
            return int(label_match.group(1))
        except ValueError:
            return None
    message_match = re.search(r"\b(?:talon fx|device|id(?:s)?)\s+(\d+)\b", str(message or TEXT_EMPTY).strip().lower())
    if message_match is not None:
        try:
            return int(message_match.group(1))
        except ValueError:
            return None
    return None


def _console_fault_family_from_event_type(event_type: str, scope: str) -> str:
    event_name = str(event_type or TEXT_EMPTY).strip().upper()
    if event_name == CONSOLE_EVENT_TALON_STALE:
        return CONSOLE_FAULT_FAMILY_CTRE_STALE
    if event_name in {CONSOLE_EVENT_PDP_TIMEOUT}:
        return CONSOLE_FAULT_FAMILY_CTRE_TIMEOUT
    if event_name in {CONSOLE_EVENT_SPARK_TIMEOUT, CONSOLE_EVENT_SPARK_FW_QUERY_FAIL, CONSOLE_EVENT_PDH_TIMEOUT}:
        return CONSOLE_FAULT_FAMILY_REV_TIMEOUT
    if event_name in {CONSOLE_EVENT_CAN_TIMEOUT, CONSOLE_EVENT_SPARK_WRONG_DEVICE}:
        return CONSOLE_FAULT_FAMILY_DEVICE_STALE
    if event_name == CONSOLE_EVENT_HIGH_UTIL:
        return CONSOLE_FAULT_FAMILY_HIGH_UTIL
    if event_name == CONSOLE_EVENT_ERROR_SPIKE:
        return CONSOLE_FAULT_FAMILY_ERROR_SPIKE
    if event_name == CONSOLE_EVENT_LOOP_OVERRUN:
        return CONSOLE_FAULT_FAMILY_RUNTIME_HEALTH
    if event_name in {CONSOLE_EVENT_HAL_TIMEOUT, CONSOLE_EVENT_BUS_FAULT}:
        return CONSOLE_FAULT_FAMILY_CONTROLLER_SIDE
    if scope == CONSOLE_STATS_SCOPE_DEVICE:
        return CONSOLE_FAULT_FAMILY_UNKNOWN_DEVICE
    if scope == CONSOLE_STATS_SCOPE_SYSTEM:
        return CONSOLE_FAULT_FAMILY_UNKNOWN_SYSTEM
    return CONSOLE_FAULT_FAMILY_UNKNOWN_SYSTEM


def _console_age_seconds(last_seen_sec: Any, now_s: float) -> Optional[float]:
    if not isinstance(last_seen_sec, (int, float)):
        return None
    return max(0.0, float(now_s) - float(last_seen_sec))


def _console_freshness_bucket(age_sec: Optional[float]) -> str:
    if not isinstance(age_sec, (int, float)):
        return CONSOLE_FRESHNESS_STALE
    if float(age_sec) <= CONSOLE_FRESH_SEC:
        return CONSOLE_FRESHNESS_FRESH
    if float(age_sec) <= CONSOLE_AGING_SEC:
        return CONSOLE_FRESHNESS_AGING
    return CONSOLE_FRESHNESS_STALE


def _console_parser_confidence(
    *,
    scope: str,
    vendor: str,
    device_type: str,
    can_id: Optional[int],
    matched_label: str,
    fault_family: str,
) -> str:
    if scope == CONSOLE_STATS_SCOPE_DEVICE and vendor != CONSOLE_VENDOR_UNKNOWN and device_type != CONSOLE_DEVICE_TYPE_UNKNOWN and (can_id is not None or matched_label):
        return CONSOLE_PARSER_CONFIDENCE_HIGH
    if fault_family not in {CONSOLE_FAULT_FAMILY_UNKNOWN_DEVICE, CONSOLE_FAULT_FAMILY_UNKNOWN_SYSTEM}:
        return CONSOLE_PARSER_CONFIDENCE_MEDIUM
    return CONSOLE_PARSER_CONFIDENCE_LOW


def _console_normalization_status(*, scope: str, fault_family: str, parser_confidence: str) -> str:
    if parser_confidence == CONSOLE_PARSER_CONFIDENCE_HIGH and scope in {CONSOLE_STATS_SCOPE_DEVICE, CONSOLE_STATS_SCOPE_SYSTEM}:
        return CONSOLE_NORMALIZATION_STRUCTURED
    if fault_family not in {CONSOLE_FAULT_FAMILY_UNKNOWN_DEVICE, CONSOLE_FAULT_FAMILY_UNKNOWN_SYSTEM}:
        return CONSOLE_NORMALIZATION_PARTIAL
    return CONSOLE_NORMALIZATION_UNCLASSIFIED


def _console_stats_increment_counter(counter_map: Any, key: str, amount: int) -> None:
    if not isinstance(counter_map, dict):
        return
    normalized_key = str(key or TEXT_EMPTY).strip()
    if not normalized_key:
        return
    counter_map[normalized_key] = int(counter_map.get(normalized_key, 0) or 0) + int(amount or 0)


def _console_top_counts(counter_map: Any) -> List[Tuple[str, int]]:
    if not isinstance(counter_map, dict):
        return []
    items: list[Tuple[str, int]] = []
    for key, value in counter_map.items():
        normalized_key = str(key or TEXT_EMPTY).strip()
        if not normalized_key:
            continue
        items.append((normalized_key, int(value or 0)))
    items.sort(key=lambda item: (-item[1], item[0]))
    return items[:CONSOLE_TOP_COUNT_LIMIT]


def _console_stats_increment_freshness(stats: Any, freshness: str) -> None:
    if not isinstance(stats, dict):
        return
    if freshness == CONSOLE_FRESHNESS_FRESH:
        stats[CONSOLE_KEY_FRESH_COUNT] = int(stats.get(CONSOLE_KEY_FRESH_COUNT, 0) or 0) + 1
    elif freshness == CONSOLE_FRESHNESS_AGING:
        stats[CONSOLE_KEY_AGING_COUNT] = int(stats.get(CONSOLE_KEY_AGING_COUNT, 0) or 0) + 1
    else:
        stats[CONSOLE_KEY_STALE_COUNT] = int(stats.get(CONSOLE_KEY_STALE_COUNT, 0) or 0) + 1


def _console_stats_update_first_last(stats: Any, first_seen_sec: Any, last_seen_sec: Any) -> None:
    if not isinstance(stats, dict):
        return
    stats[CONSOLE_KEY_FIRST_SEEN_SEC] = _console_min_time_value(stats.get(CONSOLE_KEY_FIRST_SEEN_SEC), first_seen_sec)
    stats[CONSOLE_KEY_LAST_SEEN_SEC] = _console_max_time_value(stats.get(CONSOLE_KEY_LAST_SEEN_SEC), last_seen_sec)


def _console_min_time_value(current_value: Any, candidate_value: Any) -> Optional[float]:
    if not isinstance(candidate_value, (int, float)):
        return float(current_value) if isinstance(current_value, (int, float)) else None
    if not isinstance(current_value, (int, float)):
        return float(candidate_value)
    return min(float(current_value), float(candidate_value))


def _console_max_time_value(current_value: Any, candidate_value: Any) -> Optional[float]:
    if not isinstance(candidate_value, (int, float)):
        return float(current_value) if isinstance(current_value, (int, float)) else None
    if not isinstance(current_value, (int, float)):
        return float(candidate_value)
    return max(float(current_value), float(candidate_value))


def _console_first_last_age_text(timestamp_value: Any, now_s: float) -> str:
    age_sec = _console_age_seconds(timestamp_value, now_s)
    if not isinstance(age_sec, (int, float)):
        return EVIDENCE_SOURCE_NONE
    return _format_age_text(age_sec)


def _console_repeat_rate_hz(total_count: int, first_seen_sec: Any, last_seen_sec: Any) -> float:
    if not isinstance(first_seen_sec, (int, float)) or not isinstance(last_seen_sec, (int, float)):
        return 0.0
    duration_sec = max(1.0, float(last_seen_sec) - float(first_seen_sec))
    return float(total_count) / duration_sec


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
    device_type = classify_device_type(
        label,
        profile_device=None,
        runtime_device=runtime_device,
    )
    is_infrastructure_device = device_type == DEVICE_CLASS_INFRASTRUCTURE
    missing_text = _probe_missing_text(
        runtime_device=runtime_device,
        last_probe_completed_at=last_probe_completed_at,
        is_infrastructure_device=is_infrastructure_device,
        now_s=now_s,
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


def build_interpreted_device_state(
    *,
    label: str,
    presence_entry: Optional[Mapping[str, Any]],
    passive_device: Optional[Any],
    enrichment_snapshot: Optional[Mapping[str, Any]] = None,
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
) -> InterpretedDeviceState:
    """
    NAME
        build_interpreted_device_state - Build one shared typed Evidence-tab interpretation state.
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
    visibility_metrics = (
        visibility_device.get("metrics")
        if isinstance(visibility_device, Mapping) and isinstance(visibility_device.get("metrics"), Mapping)
        else {}
    )
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
        visibility = visibility_device.get("visibility") if isinstance(visibility_device.get("visibility"), Mapping) else {}
        metric_last_seen_present = _visibility_metrics_fresh(visibility_metrics, now_s)
        for metric_entry in visibility_metrics.values():
            if not isinstance(metric_entry, Mapping):
                continue
        passive_visible = (
            any(value is True for value in visibility.values())
            or metric_last_seen_present
        )
        passive_summary = EVIDENCE_NOTE_SEPARATOR.join(
            (
                f"lastSeen={visibility_last_seen_text}",
                f"packets={visibility_packet_count_text}",
                f"rate={visibility_packet_rate_text}",
            )
        )
        if visibility_identity_text != VIS_IDENTITY_UNKNOWN:
            passive_identity = EVIDENCE_STATUS_MATCHING
    elif isinstance(runtime_device, Mapping) and isinstance(runtime_device.get("lastSeenMs"), (int, float)):
        passive_summary = visibility_last_seen_text
    console_summary = console_entry.get(CONSOLE_KEY_SUMMARY) if isinstance(console_entry, Mapping) else EVIDENCE_SOURCE_NONE
    console_events = console_entry.get(CONSOLE_KEY_EVENTS, []) if isinstance(console_entry, Mapping) else []
    console_has_error = bool(console_entry.get(CONSOLE_KEY_HAS_ERROR)) if isinstance(console_entry, Mapping) else False
    console_has_warn = bool(console_entry.get(CONSOLE_KEY_HAS_WARN)) if isinstance(console_entry, Mapping) else False
    console_targets_failure = _console_entry_targets_device_failure(console_entry)
    enrichment_entry = _enrichment_device_entry(enrichment_snapshot, label)
    enrichment_run_note = _build_enrichment_run_note(enrichment_snapshot, now_s=now_s)
    manual_auto_result = (
        str(manual_observation.get("autoResult", TEXT_EMPTY)).strip()
        if isinstance(manual_observation, Mapping)
        else TEXT_EMPTY
    )
    manual_age_sec = _manual_age_seconds(manual_entry, now_s)
    manual_recent_operability = isinstance(manual_age_sec, (int, float)) and manual_age_sec <= EVIDENCE_MANUAL_OPERABILITY_WINDOW_SEC
    manual_recent_identity = isinstance(manual_age_sec, (int, float)) and manual_age_sec <= EVIDENCE_MANUAL_IDENTITY_WINDOW_SEC
    manual_observation_age_sec = _manual_age_seconds(manual_observation, now_s)
    manual_recent_observation = (
        isinstance(manual_observation_age_sec, (int, float))
        and manual_observation_age_sec <= EVIDENCE_MANUAL_OPERABILITY_WINDOW_SEC
    )
    manual_summary = MANUAL_PLACEHOLDER
    existence = EVIDENCE_STATUS_UNKNOWN
    operability = EVIDENCE_STATUS_UNKNOWN
    identity = passive_identity
    confidence = EVIDENCE_CONFIDENCE_LOW
    notes: list[str] = []
    if enrichment_run_note:
        notes.append(enrichment_run_note)
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
    if manual_recent_observation and manual_auto_result == MANUAL_AUTO_RESULT_ROTATION:
        motion_detected = True
        manual_motion_failed = False
    device_type = classify_device_type(
        label,
        profile_device=None,
        runtime_device=runtime_device,
        passive_device=passive_device,
    )
    is_infrastructure_device = device_type == DEVICE_CLASS_INFRASTRUCTURE
    requires_can_visible_infrastructure_presence = _requires_can_visible_infrastructure_presence(label)
    runtime_infrastructure_present = (
        is_infrastructure_device and _runtime_infrastructure_signal_present(runtime_device, now_s=now_s)
    )
    passive_live_support = (
        _visibility_metrics_support_live_presence(visibility_metrics, now_s)
        if visibility_metrics
        else passive_visible
    )
    passive_supports_presence_override = (
        passive_visible
        and passive_live_support
        and passive_confidence in (EVIDENCE_CONFIDENCE_HIGH, EVIDENCE_CONFIDENCE_MEDIUM)
        and passive_expected_status != "missing"
        and bool(passive_family_summaries)
    )
    passive_infrastructure_missing = bool(
        is_infrastructure_device
        and passive_device is not None
        and passive_expected_status == "missing"
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
                if is_infrastructure_device:
                    notes.append(EVIDENCE_NOTE_INFRA_PASSIVE_PRESENT)
                else:
                    evidence_conflicted = True
                    notes.append(EVIDENCE_NOTE_PASSIVE_OVERRIDES_RUNTIME_ABSENCE)
            elif is_infrastructure_device:
                if runtime_infrastructure_present and not (
                    passive_infrastructure_missing and requires_can_visible_infrastructure_presence
                ):
                    existence = EVIDENCE_STATUS_PRESENT
                    confidence = EVIDENCE_CONFIDENCE_HIGH
                    if operability == EVIDENCE_STATUS_UNKNOWN:
                        operability = EVIDENCE_STATUS_OK
                    evidence_state = EVIDENCE_STATE_OK
                    notes.append(EVIDENCE_NOTE_INFRA_RUNTIME_PRESENT)
                elif passive_infrastructure_missing and requires_can_visible_infrastructure_presence:
                    existence = EVIDENCE_STATUS_ABSENT
                    confidence = presence_confidence if presence_confidence != EVIDENCE_CONFIDENCE_LOW else EVIDENCE_CONFIDENCE_MEDIUM
                    operability = EVIDENCE_STATUS_FAILED if operability == EVIDENCE_STATUS_UNKNOWN else operability
                    evidence_state = EVIDENCE_STATE_MISSING
                    notes.append(EVIDENCE_NOTE_INFRA_RUNTIME_LOCAL_ONLY)
                else:
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
    ctre_enrichment_entry = enrichment_entry.get(ENRICHMENT_DEVICE_KEY_CTRE)
    if isinstance(ctre_enrichment_entry, Mapping):
        if existence in (EVIDENCE_STATUS_UNKNOWN, EVIDENCE_STATUS_ABSENT):
            existence = EVIDENCE_STATUS_PRESENT
            confidence = EVIDENCE_CONFIDENCE_MEDIUM
            evidence_state = EVIDENCE_STATE_DEGRADED if not passive_visible else evidence_state
            evidence_conflicted = evidence_conflicted or not passive_visible
            notes.append(ENRICHMENT_NOTE_CTRE_ONLY if not passive_visible else ENRICHMENT_NOTE_CTRE_CONFIRMED)
        else:
            notes.append(ENRICHMENT_NOTE_CTRE_CONFIRMED)
        if identity == EVIDENCE_STATUS_UNKNOWN:
            identity = EVIDENCE_STATUS_MATCHING
        if str(ctre_enrichment_entry.get(ENRICHMENT_CTRE_KEY_MODEL, TEXT_EMPTY)).strip():
            confidence = EVIDENCE_CONFIDENCE_HIGH if confidence != EVIDENCE_CONFIDENCE_LOW else EVIDENCE_CONFIDENCE_MEDIUM
        if ctre_enrichment_entry.get(ENRICHMENT_CTRE_KEY_FAULTS_TRUE) or ctre_enrichment_entry.get(ENRICHMENT_CTRE_KEY_STICKY_FAULTS_TRUE):
            operability = EVIDENCE_STATUS_DEGRADED if operability == EVIDENCE_STATUS_UNKNOWN else operability
            evidence_state = EVIDENCE_STATE_DEGRADED
            notes.append(ENRICHMENT_NOTE_CTRE_FAULTS)
    topology_enrichment_entry = enrichment_entry.get(ENRICHMENT_DEVICE_KEY_TOPOLOGY)
    if isinstance(topology_enrichment_entry, Mapping) and existence == EVIDENCE_STATUS_PRESENT:
        if identity == EVIDENCE_STATUS_UNKNOWN:
            identity = EVIDENCE_STATUS_MATCHING
        notes.append(ENRICHMENT_NOTE_TOPOLOGY_CONFIRMED)
    console_enrichment_entry = enrichment_entry.get(ENRICHMENT_DEVICE_KEY_CONSOLE)
    if isinstance(console_enrichment_entry, Mapping):
        if bool(console_enrichment_entry.get(CONSOLE_KEY_HAS_ERROR)) or bool(console_enrichment_entry.get(CONSOLE_KEY_HAS_WARN)):
            if operability == EVIDENCE_STATUS_UNKNOWN:
                operability = EVIDENCE_STATUS_DEGRADED
            if evidence_state in (EVIDENCE_STATE_UNKNOWN, EVIDENCE_STATE_OK):
                evidence_state = EVIDENCE_STATE_DEGRADED
            confidence = EVIDENCE_CONFIDENCE_MEDIUM if confidence == EVIDENCE_CONFIDENCE_HIGH else confidence
            notes.append(ENRICHMENT_NOTE_CONSOLE_ENRICHMENT_ERROR)
    if (
        existence == EVIDENCE_STATUS_UNKNOWN
        and runtime_infrastructure_present
        and not (passive_infrastructure_missing and requires_can_visible_infrastructure_presence)
    ):
        existence = EVIDENCE_STATUS_PRESENT
        confidence = EVIDENCE_CONFIDENCE_HIGH
        if operability == EVIDENCE_STATUS_UNKNOWN:
            operability = EVIDENCE_STATUS_OK
        evidence_state = EVIDENCE_STATE_OK
        notes.append(EVIDENCE_NOTE_INFRA_RUNTIME_PRESENT)
    if existence == EVIDENCE_STATUS_UNKNOWN and passive_visible and passive_live_support:
        existence = EVIDENCE_STATUS_PRESENT
        confidence = passive_confidence if passive_device is not None else EVIDENCE_CONFIDENCE_MEDIUM
        if is_infrastructure_device and passive_device is None:
            if runtime_infrastructure_present:
                confidence = EVIDENCE_CONFIDENCE_HIGH
                if operability == EVIDENCE_STATUS_UNKNOWN:
                    operability = EVIDENCE_STATUS_OK
                evidence_state = EVIDENCE_STATE_OK
            else:
                evidence_state = EVIDENCE_STATE_DEGRADED
                notes.append(EVIDENCE_NOTE_INFRA_PASSIVE_LIMITED)
        else:
            evidence_state = EVIDENCE_STATE_OK
    elif existence == EVIDENCE_STATUS_UNKNOWN and passive_device is not None and passive_expected_status == "missing":
        if is_infrastructure_device:
            if requires_can_visible_infrastructure_presence:
                existence = EVIDENCE_STATUS_ABSENT
                confidence = passive_confidence if passive_confidence != EVIDENCE_CONFIDENCE_LOW else EVIDENCE_CONFIDENCE_MEDIUM
                operability = EVIDENCE_STATUS_FAILED if operability == EVIDENCE_STATUS_UNKNOWN else operability
                evidence_state = EVIDENCE_STATE_MISSING if evidence_state == EVIDENCE_STATE_UNKNOWN else evidence_state
                notes.append(EVIDENCE_NOTE_INFRA_CONSOLE_MISSING)
            else:
                existence = EVIDENCE_STATUS_UNKNOWN
                confidence = EVIDENCE_CONFIDENCE_LOW
                evidence_state = EVIDENCE_STATE_UNKNOWN
                notes.append(EVIDENCE_NOTE_INFRA_SCOPE_ABSENCE)
        else:
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
    if console_targets_failure:
        operability = EVIDENCE_STATUS_FAILED
        confidence = EVIDENCE_CONFIDENCE_LOW if confidence == EVIDENCE_CONFIDENCE_HIGH else EVIDENCE_CONFIDENCE_MEDIUM
        evidence_state = EVIDENCE_STATE_FAILED
        notes.append(EVIDENCE_NOTE_CONSOLE_DEVICE_TIMEOUT)
    probe_invalidated_by_console = bool(
        console_targets_failure and probe_bucket != PROBE_BUCKET_NOT_RUN and probe_age_bucket in {PROBE_AGE_AGING, PROBE_AGE_STALE}
    )
    manual_invalidated_by_console = bool(
        console_targets_failure
        and not manual_recent_operability
        and (
            isinstance(manual_entry, Mapping)
            or isinstance(manual_observation, Mapping)
        )
    )
    if probe_invalidated_by_console:
        notes.append(EVIDENCE_PROBE_NOTE_INVALIDATED_CONSOLE)
    if manual_invalidated_by_console:
        notes.append(EVIDENCE_MANUAL_NOTE_INVALIDATED_CONSOLE)
    stronger_positive_contradiction = _console_has_stronger_positive_contradiction(
        probe_bucket=probe_bucket,
        probe_age_bucket=probe_age_bucket,
        passive_live_support=passive_live_support,
        manual_recent_observation=manual_recent_observation,
        manual_auto_result=manual_auto_result,
    )
    runtime_infrastructure_only_positive = bool(
        is_infrastructure_device
        and runtime_infrastructure_present
        and not passive_live_support
        and probe_bucket != PRESENCE_VALUE_PRESENT
        and not manual_recent_operability
    )
    if _console_should_demote_existence(
        console_entry=console_entry,
        console_targets_failure=console_targets_failure,
        stronger_positive_contradiction=stronger_positive_contradiction,
    ):
        if existence == EVIDENCE_STATUS_PRESENT:
            existence = EVIDENCE_STATUS_CONFLICT
            evidence_conflicted = True
            notes.append(EVIDENCE_NOTE_CONSOLE_DEVICE_TIMEOUT_CONFLICT)
        elif existence == EVIDENCE_STATUS_UNKNOWN:
            confidence = EVIDENCE_CONFIDENCE_LOW
    if (
        is_infrastructure_device
        and console_targets_failure
        and not stronger_positive_contradiction
        and (not runtime_infrastructure_present or runtime_infrastructure_only_positive)
    ):
        existence = EVIDENCE_STATUS_ABSENT
        operability = EVIDENCE_STATUS_FAILED
        confidence = EVIDENCE_CONFIDENCE_MEDIUM
        evidence_state = EVIDENCE_STATE_FAILED
        notes.append(EVIDENCE_NOTE_INFRA_CONSOLE_MISSING)
        if runtime_infrastructure_only_positive:
            notes.append(EVIDENCE_NOTE_INFRA_RUNTIME_LOCAL_ONLY)
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
    if manual_recent_observation and manual_auto_result == MANUAL_AUTO_RESULT_ROTATION:
        motion_detected = True
    elif manual_recent_observation and manual_auto_result == MANUAL_AUTO_RESULT_NO_ROTATION and motion_commanded:
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
    runtime_presence_from_local_snapshot = bool(
        isinstance(presence_entry, Mapping)
        and str(presence_entry.get(PRESENCE_KEY_SOURCE, EVIDENCE_SOURCE_NONE)).strip() == EVIDENCE_SOURCE_LOCAL_SNAPSHOT
        and str(presence_entry.get(PRESENCE_KEY_EXISTENCE, EVIDENCE_STATUS_UNKNOWN)).strip().upper() == EVIDENCE_STATUS_PRESENT
    )
    motion_like_runtime_device = bool(
        not is_infrastructure_device
        and (
            device_type == DEVICE_CLASS_MOTION
            or any(
                isinstance(value, (int, float))
                for value in (
                    cmd_duty,
                    applied_duty,
                    velocity_rpm,
                    motor_current,
                    position_rot,
                )
            )
        )
    )
    weak_motion_presence_contradiction = bool(
        motion_like_runtime_device
        and runtime_presence_from_local_snapshot
        and manual_recent_observation
        and manual_auto_result == MANUAL_AUTO_RESULT_NO_ROTATION
        and not passive_supports_presence_override
        and probe_bucket in (VIS_IDENTITY_UNKNOWN, PROBE_BUCKET_NOT_RUN)
        and not isinstance(ctre_enrichment_entry, Mapping)
    )
    if weak_motion_presence_contradiction:
        existence = EVIDENCE_STATUS_CONFLICT
        operability = EVIDENCE_STATUS_FAILED
        confidence = EVIDENCE_CONFIDENCE_LOW
        evidence_state = EVIDENCE_STATE_FAILED
        evidence_conflicted = True
        notes.append(EVIDENCE_NOTE_RUNTIME_SNAPSHOT_UNCONFIRMED_MOTION)
    if identity == EVIDENCE_STATUS_MATCHING and existence == EVIDENCE_STATUS_PRESENT:
        if evidence_state == EVIDENCE_STATE_UNKNOWN:
            evidence_state = EVIDENCE_STATE_IDENTITY
    elif identity != EVIDENCE_STATUS_WRONG:
        identity = EVIDENCE_STATUS_UNKNOWN
    if operability == EVIDENCE_STATUS_FAILED:
        evidence_state = EVIDENCE_STATE_FAILED
    if (
        not is_infrastructure_device
        and probe_bucket in (VIS_IDENTITY_UNKNOWN, PROBE_BUCKET_NOT_RUN)
        and passive_visible
        and not console_has_error
    ):
        notes.append(EVIDENCE_NOTE_PASSIVE_WITHOUT_PROBE_RESULT)
    if passive_device is not None:
        notes.extend(note for note in passive_gaps if note and note not in notes)
        if passive_visible and not passive_live_support:
            notes.append("Passive CAN observation is stale or no longer emitting traffic at a non-zero rate.")
    if not notes:
        notes.append(EVIDENCE_NOTE_NONE)
    source_scores = _collect_device_source_scores(
        device_type=device_type,
        passive_visible=passive_visible and passive_live_support,
        passive_confidence=passive_confidence,
        runtime_presence_entry=presence_entry if isinstance(presence_entry, Mapping) else None,
        runtime_infrastructure_present=runtime_infrastructure_present,
        probe_bucket=probe_bucket,
        probe_age_bucket=probe_age_bucket,
        console_has_error=console_has_error,
        console_has_warn=console_has_warn,
        console_targets_failure=console_targets_failure,
        manual_entry=manual_entry if isinstance(manual_entry, Mapping) else None,
        manual_observation=manual_observation if isinstance(manual_observation, Mapping) else None,
        manual_age_sec=manual_age_sec if isinstance(manual_age_sec, (int, float)) else manual_observation_age_sec,
        probe_invalidated_by_console=probe_invalidated_by_console,
        manual_invalidated_by_console=manual_invalidated_by_console,
        enrichment_entry=enrichment_entry if isinstance(enrichment_entry, Mapping) else None,
    )
    presence_state = _state_from_final_row(existence, evidence_state, evidence_conflicted)
    presence_score = _presence_score_from_final_row(existence, confidence, evidence_conflicted)
    freshness = _presence_freshness(
        presence_age_text,
        probe_age_bucket,
        isinstance(presence_entry, Mapping)
        and str(presence_entry.get(PRESENCE_KEY_EXISTENCE, EVIDENCE_STATUS_UNKNOWN)).strip().upper()
        == EVIDENCE_STATUS_PRESENT,
        (passive_visible and passive_live_support) or runtime_infrastructure_present,
    )
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
    console_general_text = (
        str(system_console.get(CONSOLE_KEY_STATS_TEXT, EVIDENCE_SOURCE_NONE)).strip()
        if isinstance(system_console, Mapping)
        else EVIDENCE_SOURCE_NONE
    ) or EVIDENCE_SOURCE_NONE
    console_device_text = (
        str(console_entry.get(CONSOLE_KEY_STATS_TEXT, EVIDENCE_SOURCE_NONE)).strip()
        if isinstance(console_entry, Mapping)
        else EVIDENCE_SOURCE_NONE
    ) or EVIDENCE_SOURCE_NONE
    console_text_parts = [console_general_text]
    if console_device_text != EVIDENCE_SOURCE_NONE:
        console_text_parts.append(console_device_text)
    elif console_events:
        console_text_parts.append(EVIDENCE_NOTE_SEPARATOR.join(str(entry) for entry in console_events))
    else:
        console_text_parts.append(str(system_console.get(CONSOLE_KEY_SYSTEM_TEXT, EVIDENCE_SOURCE_NONE)))
    console_text = "\n".join(
        str(part).strip() for part in console_text_parts if str(part).strip()
    ) or EVIDENCE_SOURCE_NONE
    probe_text = str(probe_snapshot.get(PROBE_TEXT_FIELD, EVIDENCE_SOURCE_NONE))
    manual_text = str(manual_snapshot.get(PROBE_TEXT_FIELD, MANUAL_PLACEHOLDER))
    probe_summary_value = str(probe_snapshot.get(PROBE_SUMMARY_FIELD, TEXT_WAITING))
    probe_score_value = str(probe_snapshot.get(PROBE_SCORE_TEXT_FIELD, EVIDENCE_SOURCE_NONE))
    manual_summary_value = str(manual_snapshot.get(MANUAL_SUMMARY_FIELD, manual_summary))
    if probe_invalidated_by_console:
        probe_summary_value = EVIDENCE_PROBE_SUMMARY_INVALIDATED
        probe_score_value = EVIDENCE_SOURCE_NONE
        probe_text = EVIDENCE_PROBE_NOTE_INVALIDATED_CONSOLE
    if manual_invalidated_by_console:
        manual_summary_value = EVIDENCE_MANUAL_SUMMARY_HISTORICAL_ONLY
        manual_text = EVIDENCE_MANUAL_NOTE_INVALIDATED_CONSOLE
    enrichment_text = _build_enrichment_text(
        enrichment_snapshot=enrichment_snapshot,
        enrichment_entry=enrichment_entry,
        now_s=now_s,
    )
    return InterpretedDeviceState(
        label=label,
        device_type=device_type,
        passive=passive_summary,
        console=console_summary or EVIDENCE_SOURCE_NONE,
        probe=probe_summary_value,
        probe_score=probe_score_value,
        manual=manual_summary_value,
        existence=existence,
        operability=operability,
        identity=identity,
        confidence=confidence,
        presence_text=presence_text,
        passive_text=passive_text,
        console_text=console_text,
        probe_text=probe_text,
        manual_text=manual_text,
        enrichment_text=enrichment_text,
        notes_text=EVIDENCE_NOTE_SEPARATOR.join(notes),
        state=evidence_state,
        conflicted=evidence_conflicted,
        presence_score=presence_score,
        presence_state=presence_state,
        presence_reasons=list(notes),
        freshness=freshness,
        source_scores=source_scores,
        dirty=False,
        dirty_reasons=[],
        last_known_good_at=None,
        last_seen_present_at=None,
        last_seen_missing_at=None,
        last_state_change_at=None,
        last_evaluation_at=None,
        change_reason=EVIDENCE_SOURCE_NONE,
        event_log=[],
    )


def build_interpreted_evidence_row(
    *,
    label: str,
    presence_entry: Optional[Mapping[str, Any]],
    passive_device: Optional[Any],
    enrichment_snapshot: Optional[Mapping[str, Any]] = None,
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
        build_interpreted_evidence_row - Build the legacy interpreted row adapter from shared typed state.
    """
    return build_interpreted_device_state(
        label=label,
        presence_entry=presence_entry,
        passive_device=passive_device,
        enrichment_snapshot=enrichment_snapshot,
        visibility_device=visibility_device,
        runtime_device=runtime_device,
        console_entry=console_entry,
        system_console=system_console,
        manual_entry=manual_entry,
        manual_observation=manual_observation,
        manual_motion=manual_motion,
        probe_pending=probe_pending,
        last_probe_completed_at=last_probe_completed_at,
        probe_run_count=probe_run_count,
        now_s=now_s,
        visibility_identity_text=visibility_identity_text,
        visibility_last_seen_text=visibility_last_seen_text,
        visibility_packet_count_text=visibility_packet_count_text,
        visibility_packet_rate_text=visibility_packet_rate_text,
    ).to_row()


def build_evidence_fault_snapshot(
    *,
    evidence_rows: List[Mapping[str, Any]],
    console_snapshot: Optional[Mapping[str, Any]],
    topology_profile: Optional[Mapping[str, Any]],
    now_s: float,
) -> Dict[str, Any]:
    """
    NAME
        build_evidence_fault_snapshot - Freeze evidence rows and their derived fault-finder diagnosis in one shared contract.
    """
    frozen_rows = [dict(row) for row in evidence_rows]
    result = build_fault_diagnosis(
        evidence_rows=frozen_rows,
        console_snapshot=console_snapshot,
        topology_profile=topology_profile,
        now_s=now_s,
    )
    candidates = result.get("candidates")
    candidate_count = len(candidates) if isinstance(candidates, list) else 0
    return {
        FAULT_SNAPSHOT_KEY_ROWS: frozen_rows,
        FAULT_SNAPSHOT_KEY_RESULT: dict(result),
        FAULT_SNAPSHOT_KEY_RENDERED_TEXT: render_fault_diagnosis(result),
        FAULT_SNAPSHOT_KEY_CANDIDATE_COUNT: candidate_count,
        FAULT_SNAPSHOT_KEY_RAN_AT: now_s,
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
        DETAIL_SNAPSHOT_GROUP_MEMBER: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_SCOPE_ACTIVE: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_INSTANTIATED: EVIDENCE_SOURCE_NONE,
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
    lifecycle_state = str(
        runtime_device.get(RUNTIME_DEVICE_KEY_LIFECYCLE_STATE, EVIDENCE_SOURCE_NONE)
    ).strip() or EVIDENCE_SOURCE_NONE
    active_group_label = str(
        runtime_device.get(RUNTIME_DEVICE_KEY_ACTIVE_GROUP_LABEL, EVIDENCE_SOURCE_NONE)
    ).strip().lower()
    snapshot[DETAIL_SNAPSHOT_GROUP_MEMBER] = _bool_text(
        active_group_label == ACTIVE_GROUP_NAME
    )
    snapshot[DETAIL_SNAPSHOT_SCOPE_ACTIVE] = _bool_text(
        lifecycle_state.lower() == LIFECYCLE_STATE_CONTROLLED_ACTIVE
    )
    snapshot[DETAIL_SNAPSHOT_INSTANTIATED] = _bool_text(
        runtime_device.get(RUNTIME_DEVICE_KEY_INSTANTIATED)
    )
    snapshot[DETAIL_SNAPSHOT_LIFECYCLE_STATE] = lifecycle_state
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


def build_passive_device_detail_snapshot(
    label: str,
    *,
    passive_result: Optional[RunResult],
    visibility_device: Optional[Mapping[str, Any]] = None,
    now_s: Optional[float] = None,
) -> Dict[str, str]:
    """
    NAME
        build_passive_device_detail_snapshot - Build one shared passive CAN detail snapshot for lens-aware inspectors.
    """
    if now_s is None:
        import time

        now_s = time.time()
    snapshot = {
        DETAIL_SNAPSHOT_PRESENCE: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_PRESENCE_STATUS: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_PRESENCE_AGE: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_PRESENCE_SOURCE: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_LAST_SEEN: EVIDENCE_SOURCE_NONE,
    }
    clean_label = str(label or TEXT_EMPTY).strip().lower()
    if not clean_label or not isinstance(passive_result, RunResult):
        return snapshot
    visibility_identity_text = _visibility_identity_text_from_device(visibility_device)
    visibility_metrics = (
        visibility_device.get("metrics")
        if isinstance(visibility_device, Mapping) and isinstance(visibility_device.get("metrics"), Mapping)
        else {}
    )
    device_record = resolve_passive_visibility_device_record(
        label=clean_label,
        passive_result=passive_result,
        visibility_identity_text=visibility_identity_text,
    )
    if device_record is None:
        latest_seen_ms: Optional[float] = None
        for metric_entry in visibility_metrics.values():
            if not isinstance(metric_entry, Mapping):
                continue
            last_seen_ms = metric_entry.get("lastSeenMs")
            if not isinstance(last_seen_ms, (int, float)):
                continue
            latest_seen_ms = (
                float(last_seen_ms)
                if latest_seen_ms is None
                else max(latest_seen_ms, float(last_seen_ms))
            )
        if isinstance(latest_seen_ms, (int, float)):
            snapshot[DETAIL_SNAPSHOT_PRESENCE] = _format_optional_float(0.0, precision=2)
            snapshot[DETAIL_SNAPSHOT_PRESENCE_STATUS] = "none"
            snapshot[DETAIL_SNAPSHOT_PRESENCE_AGE] = _format_last_seen_text(latest_seen_ms, now_s)
            snapshot[DETAIL_SNAPSHOT_PRESENCE_SOURCE] = "passiveCan"
            snapshot[DETAIL_SNAPSHOT_LAST_SEEN] = _format_last_seen_text(latest_seen_ms, now_s)
        return snapshot
    family_records_by_key = {family.key: family for family in passive_result.family_records}
    evidence_families: List[FamilyRecord] = []
    last_seen_s: Optional[float] = None
    for family_key in tuple(device_record.evidence_family_keys or ()):
        family = family_records_by_key.get(family_key)
        if family is None:
            continue
        evidence_families.append(family)
        family_last_seen_s = getattr(family.metrics, "last_seen_s", None)
        if isinstance(family_last_seen_s, (int, float)):
            last_seen_s = max(float(last_seen_s), float(family_last_seen_s)) if isinstance(last_seen_s, (int, float)) else float(family_last_seen_s)
    age_sec = None
    if isinstance(last_seen_s, (int, float)):
        age_sec = max(float(now_s) - float(last_seen_s), 0.0)
    snapshot[DETAIL_SNAPSHOT_PRESENCE] = _format_optional_float(float(device_record.presence_score) / 100.0, precision=2)
    snapshot[DETAIL_SNAPSHOT_PRESENCE_STATUS] = str(device_record.presence_confidence or EVIDENCE_SOURCE_NONE).strip() or EVIDENCE_SOURCE_NONE
    snapshot[DETAIL_SNAPSHOT_PRESENCE_AGE] = _format_age_text(age_sec)
    snapshot[DETAIL_SNAPSHOT_PRESENCE_SOURCE] = "passiveCan"
    snapshot[DETAIL_SNAPSHOT_LAST_SEEN] = _format_age_text(age_sec)
    return snapshot


def build_interpreted_device_detail_snapshot(
    evidence_row: Optional[Mapping[str, Any]],
) -> Dict[str, str]:
    """
    NAME
        build_interpreted_device_detail_snapshot - Build one shared interpreted-evidence detail snapshot for lens-aware inspectors.
    """
    snapshot = {
        DETAIL_SNAPSHOT_PRESENCE: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_PRESENCE_STATUS: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_PRESENCE_AGE: EVIDENCE_SOURCE_NONE,
        DETAIL_SNAPSHOT_PRESENCE_SOURCE: EVIDENCE_SOURCE_NONE,
    }
    if not isinstance(evidence_row, Mapping):
        return snapshot
    presence_score = evidence_row.get(INTERPRET_KEY_PRESENCE_SCORE)
    if isinstance(presence_score, (int, float)):
        snapshot[DETAIL_SNAPSHOT_PRESENCE] = _format_optional_float(float(presence_score) / 100.0, precision=2)
    snapshot[DETAIL_SNAPSHOT_PRESENCE_STATUS] = str(
        evidence_row.get(INTERPRET_KEY_PRESENCE_STATE, EVIDENCE_SOURCE_NONE)
    ).strip() or EVIDENCE_SOURCE_NONE
    snapshot[DETAIL_SNAPSHOT_PRESENCE_AGE] = str(
        evidence_row.get(INTERPRET_KEY_FRESHNESS, EVIDENCE_SOURCE_NONE)
    ).strip() or EVIDENCE_SOURCE_NONE
    snapshot[DETAIL_SNAPSHOT_PRESENCE_SOURCE] = "interpretedEvidence"
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


def classify_device_type(
    label: object,
    profile_device: Optional[Mapping[str, Any]] = None,
    runtime_device: Optional[Mapping[str, Any]] = None,
    passive_device: Optional[Any] = None,
) -> str:
    """
    NAME
        classify_device_type - Classify one device into the first-pass scoring classes.
    """
    del runtime_device
    if _is_infrastructure_device(label):
        return DEVICE_CLASS_INFRASTRUCTURE
    if profile_device is None and passive_device is not None:
        return DEVICE_CLASS_UNPROFILED
    return DEVICE_CLASS_MOTION


def _source_score(score: int, state: str, reason: str) -> Dict[str, Any]:
    """
    NAME
        _source_score - Normalize one per-source score row.
    """
    bounded_score = max(0, min(100, int(score)))
    return {
        SOURCE_SCORE_KEY_SCORE: bounded_score,
        SOURCE_SCORE_KEY_STATE: state,
        SOURCE_SCORE_KEY_REASON: str(reason or EVIDENCE_SOURCE_NONE).strip() or EVIDENCE_SOURCE_NONE,
    }


def _state_from_final_row(existence: str, evidence_state: str, conflicted: bool) -> str:
    """
    NAME
        _state_from_final_row - Collapse the final row into one stable presence-state label.
    """
    if conflicted:
        return PRESENCE_STATE_CONFLICT
    if str(existence or EVIDENCE_STATUS_UNKNOWN).strip().upper() == EVIDENCE_STATUS_ABSENT:
        return PRESENCE_STATE_MISSING
    if str(evidence_state or EVIDENCE_STATE_UNKNOWN).strip().lower() == EVIDENCE_STATE_MISSING:
        return PRESENCE_STATE_MISSING
    if str(existence or EVIDENCE_STATUS_UNKNOWN).strip().upper() == EVIDENCE_STATUS_PRESENT:
        return PRESENCE_STATE_PRESENT
    return PRESENCE_STATE_UNKNOWN


def _presence_score_from_final_row(existence: str, confidence: str, conflicted: bool) -> int:
    """
    NAME
        _presence_score_from_final_row - Map final row interpretation into one numeric presence score.
    """
    if conflicted:
        return 40
    confidence_value = str(confidence or EVIDENCE_CONFIDENCE_LOW).strip().upper()
    if str(existence or EVIDENCE_STATUS_UNKNOWN).strip().upper() == EVIDENCE_STATUS_PRESENT:
        if confidence_value == EVIDENCE_CONFIDENCE_HIGH:
            return 100
        if confidence_value == EVIDENCE_CONFIDENCE_MEDIUM:
            return 75
        return 55
    if str(existence or EVIDENCE_STATUS_UNKNOWN).strip().upper() == EVIDENCE_STATUS_ABSENT:
        return 0
    return 25


def _presence_freshness(
    presence_age_text: str,
    probe_age_bucket: str,
    runtime_present: bool,
    passive_present: bool,
) -> str:
    """
    NAME
        _presence_freshness - Return one compact freshness label for the shared interpreted-device result.
    """
    if probe_age_bucket == PROBE_AGE_STALE:
        return CONSOLE_TEXT_STALE
    if runtime_present or passive_present:
        return "fresh"
    if presence_age_text and presence_age_text != VIS_IDENTITY_UNKNOWN:
        return "aging"
    return CONSOLE_TEXT_STALE


def _visibility_metrics_fresh(
    visibility_metrics: Mapping[str, Any],
    now_s: float,
) -> bool:
    """
    NAME
        _visibility_metrics_fresh - Return whether visibility metrics include a recent passive observation.
    """
    latest_seen_ms: Optional[float] = None
    for metric_entry in visibility_metrics.values():
        if not isinstance(metric_entry, Mapping):
            continue
        last_seen_ms = metric_entry.get("lastSeenMs")
        if not isinstance(last_seen_ms, (int, float)):
            continue
        latest_seen_ms = float(last_seen_ms) if latest_seen_ms is None else max(latest_seen_ms, float(last_seen_ms))
    if latest_seen_ms is None or latest_seen_ms <= 0.0:
        return False
    age_sec = max(0.0, now_s - (latest_seen_ms / 1000.0))
    return age_sec <= VISIBILITY_FRESH_SEC


def _visibility_metrics_support_live_presence(
    visibility_metrics: Mapping[str, Any],
    now_s: float,
) -> bool:
    """
    NAME
        _visibility_metrics_support_live_presence - Return whether visibility metrics still support active passive presence.
    """
    if not _visibility_metrics_fresh(visibility_metrics, now_s):
        return False
    max_rate_hz = 0.0
    for metric_entry in visibility_metrics.values():
        if not isinstance(metric_entry, Mapping):
            continue
        frames_per_sec = metric_entry.get("framesPerSec")
        if not isinstance(frames_per_sec, (int, float)):
            continue
        max_rate_hz = max(max_rate_hz, float(frames_per_sec))
    return max_rate_hz > 0.0


def _console_targets_device_failure(console_events: Sequence[object]) -> bool:
    """
    NAME
        _console_targets_device_failure - Return whether device-targeted console events imply a strong device failure signal.
    """
    for entry in list(console_events or ()):
        text = str(entry or TEXT_EMPTY).strip().lower()
        if not text:
            continue
        if EVIDENCE_TEXT_CAN_MESSAGE_STALE in text:
            return True
        if EVIDENCE_TEXT_STATUS_SIGNAL_STALE in text:
            return True
        if EVIDENCE_TEXT_DEVICE_TIMEOUT in text:
            return True
    return False


def _console_entry_targets_device_failure(console_entry: Optional[Mapping[str, Any]]) -> bool:
    """
    NAME
        _console_entry_targets_device_failure - Return whether structured console evidence implies a strong fresh targeted device fault.
    """
    if not isinstance(console_entry, Mapping):
        return False
    records = console_entry.get(CONSOLE_KEY_RECORDS, [])
    if isinstance(records, list):
        for record in records:
            if not isinstance(record, Mapping):
                continue
            fault_family = str(record.get(CONSOLE_KEY_FAULT_FAMILY, TEXT_EMPTY)).strip()
            freshness = str(record.get(CONSOLE_KEY_FRESHNESS, TEXT_EMPTY)).strip()
            scope = str(record.get(CONSOLE_KEY_SCOPE, TEXT_EMPTY)).strip()
            if scope != CONSOLE_STATS_SCOPE_DEVICE:
                continue
            if fault_family in CONSOLE_DEVICE_FAILURE_FAMILIES and freshness in {
                CONSOLE_FRESHNESS_FRESH,
                CONSOLE_FRESHNESS_AGING,
            }:
                return True
    return _console_targets_device_failure(console_entry.get(CONSOLE_KEY_EVENTS, []))


def _console_has_stronger_positive_contradiction(
    *,
    probe_bucket: str,
    probe_age_bucket: str,
    passive_live_support: bool,
    manual_recent_observation: bool,
    manual_auto_result: str,
) -> bool:
    """
    NAME
        _console_has_stronger_positive_contradiction - Return whether fresh direct evidence still strongly supports continued device presence.
    """
    if probe_bucket == PRESENCE_VALUE_PRESENT and probe_age_bucket == PROBE_AGE_FRESH:
        return True
    if passive_live_support:
        return True
    if manual_recent_observation and manual_auto_result == MANUAL_AUTO_RESULT_ROTATION:
        return True
    return False


def _console_should_demote_existence(
    *,
    console_entry: Optional[Mapping[str, Any]],
    console_targets_failure: bool,
    stronger_positive_contradiction: bool,
) -> bool:
    """
    NAME
        _console_should_demote_existence - Return whether targeted console faults should demote existence out of a plain PRESENT classification.
    """
    if stronger_positive_contradiction or not console_targets_failure:
        return False
    if not isinstance(console_entry, Mapping):
        return True
    total_count = int(console_entry.get(CONSOLE_KEY_TOTAL_COUNT, 0) or 0)
    freshness = str(console_entry.get(CONSOLE_KEY_FRESHNESS, TEXT_EMPTY)).strip()
    if total_count >= 2 and freshness in {CONSOLE_FRESHNESS_FRESH, CONSOLE_FRESHNESS_AGING}:
        return True
    records = console_entry.get(CONSOLE_KEY_RECORDS, [])
    if isinstance(records, list):
        matching_records = 0
        for record in records:
            if not isinstance(record, Mapping):
                continue
            if str(record.get(CONSOLE_KEY_SCOPE, TEXT_EMPTY)).strip() != CONSOLE_STATS_SCOPE_DEVICE:
                continue
            if str(record.get(CONSOLE_KEY_FRESHNESS, TEXT_EMPTY)).strip() not in {
                CONSOLE_FRESHNESS_FRESH,
                CONSOLE_FRESHNESS_AGING,
            }:
                continue
            matching_records += int(record.get(CONSOLE_KEY_TOTAL_COUNT, 1) or 1)
        if matching_records >= 2:
            return True
    return bool(console_entry.get(CONSOLE_KEY_HAS_ERROR) or console_entry.get(CONSOLE_KEY_HAS_WARN))


def _collect_device_source_scores(
    *,
    device_type: str,
    passive_visible: bool,
    passive_confidence: str,
    runtime_presence_entry: Optional[Mapping[str, Any]],
    runtime_infrastructure_present: bool,
    probe_bucket: str,
    probe_age_bucket: str,
    console_has_error: bool,
    console_has_warn: bool,
    console_targets_failure: bool,
    manual_entry: Optional[Mapping[str, Any]],
    manual_observation: Optional[Mapping[str, Any]],
    manual_age_sec: Optional[float],
    probe_invalidated_by_console: bool,
    manual_invalidated_by_console: bool,
    enrichment_entry: Optional[Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    NAME
        _collect_device_source_scores - Build the shared per-source score map for one device.
    """
    source_scores: Dict[str, Dict[str, Any]] = {}
    passive_score_value = 0
    if passive_visible:
        passive_score_value = 85 if passive_confidence == EVIDENCE_CONFIDENCE_HIGH else 70
    source_scores["passive"] = _source_score(
        passive_score_value,
        PRESENCE_STATE_PRESENT if passive_visible else PRESENCE_STATE_UNKNOWN,
        "Passive CAN visibility.",
    )
    runtime_present = False
    runtime_absent = False
    if isinstance(runtime_presence_entry, Mapping):
        runtime_existence = str(
            runtime_presence_entry.get(PRESENCE_KEY_EXISTENCE, EVIDENCE_STATUS_UNKNOWN)
        ).strip().upper()
        runtime_present = runtime_existence == EVIDENCE_STATUS_PRESENT
        runtime_absent = runtime_existence == EVIDENCE_STATUS_ABSENT
    if device_type == DEVICE_CLASS_INFRASTRUCTURE and runtime_infrastructure_present:
        source_scores["runtime"] = _source_score(90, PRESENCE_STATE_PRESENT, "Fresh singleton runtime telemetry.")
    elif runtime_present:
        source_scores["runtime"] = _source_score(90, PRESENCE_STATE_PRESENT, "Runtime presence snapshot.")
    elif runtime_absent:
        source_scores["runtime"] = _source_score(0, PRESENCE_STATE_MISSING, "Runtime presence snapshot absent.")
    else:
        source_scores["runtime"] = _source_score(25, PRESENCE_STATE_UNKNOWN, "No runtime presence claim.")
    if probe_invalidated_by_console:
        source_scores["probe"] = _source_score(0, PRESENCE_STATE_CONFLICT, SOURCE_SCORE_PROBE_INVALIDATED)
    elif probe_bucket == PRESENCE_VALUE_PRESENT and probe_age_bucket != PROBE_AGE_STALE:
        source_scores["probe"] = _source_score(95, PRESENCE_STATE_PRESENT, "Fresh Full Probe present.")
    elif probe_bucket == PRESENCE_VALUE_ABSENT and probe_age_bucket != PROBE_AGE_STALE:
        source_scores["probe"] = _source_score(0, PRESENCE_STATE_MISSING, "Fresh Full Probe absent.")
    elif probe_age_bucket == PROBE_AGE_STALE:
        source_scores["probe"] = _source_score(20, PRESENCE_STATE_UNKNOWN, "Stale Full Probe.")
    else:
        source_scores["probe"] = _source_score(25, PRESENCE_STATE_UNKNOWN, "No device-specific Full Probe result.")
    if console_has_error or console_targets_failure:
        source_scores["console"] = _source_score(20, PRESENCE_STATE_CONFLICT, "Console error evidence.")
    elif console_has_warn:
        source_scores["console"] = _source_score(45, PRESENCE_STATE_UNKNOWN, "Console warning evidence.")
    else:
        source_scores["console"] = _source_score(50, PRESENCE_STATE_UNKNOWN, "No console warning/error evidence.")
    manual_recent = (
        isinstance(manual_age_sec, (int, float))
        and float(manual_age_sec) <= EVIDENCE_MANUAL_OPERABILITY_WINDOW_SEC
    )
    if manual_invalidated_by_console:
        source_scores["manual"] = _source_score(0, PRESENCE_STATE_CONFLICT, SOURCE_SCORE_MANUAL_INVALIDATED)
    elif manual_recent and (isinstance(manual_entry, Mapping) or isinstance(manual_observation, Mapping)):
        source_scores["manual"] = _source_score(60, PRESENCE_STATE_PRESENT, "Manual evidence recorded.")
    else:
        source_scores["manual"] = _source_score(25, PRESENCE_STATE_UNKNOWN, "No manual evidence.")
    if isinstance(enrichment_entry, Mapping) and enrichment_entry:
        source_scores["enrichment"] = _source_score(65, PRESENCE_STATE_PRESENT, "Host-side enrichment evidence.")
    else:
        source_scores["enrichment"] = _source_score(25, PRESENCE_STATE_UNKNOWN, "No enrichment evidence.")
    return source_scores


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
            "Lens=robot-local runtime snapshot; result applies only to the current runtime/test scope.",
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
        return "\n".join(
            (
                "Lens=robot-local runtime snapshot; result applies only to the current runtime/test scope.",
                EVIDENCE_NOTE_SEPARATOR.join(
                    (
                        f"bucket={presence_bucket}",
                        f"score={float(presence_value):.2f}",
                        f"updated={presence_age_text}",
                        "source=runtimeState",
                    )
                ),
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


def build_passive_visibility_deep_dive_text(
    *,
    label: str,
    passive_result: Optional[RunResult],
    visibility_device: Optional[Mapping[str, Any]],
    visibility_identity_text: str,
    visibility_last_seen_text: str,
    visibility_packet_count_text: str,
    visibility_packet_rate_text: str,
) -> str:
    """
    NAME
        build_passive_visibility_deep_dive_text - Render one CAN Visibility deep-dive block from the shared passive analyzer result.
    """
    clean_label = str(label or TEXT_EMPTY).strip()
    if not clean_label:
        return EVIDENCE_SOURCE_NONE
    passive_device = resolve_passive_visibility_device_record(
        label=clean_label,
        passive_result=passive_result,
        visibility_identity_text=visibility_identity_text,
    )
    if passive_device is None:
        return "\n".join(
            [
                "Shared Passive CAN Deep Dive",
                f"label={clean_label}",
                "No shared passive CAN analysis result available for this device.",
                EVIDENCE_NOTE_SEPARATOR.join(
                    (
                        f"observerIdentity={visibility_identity_text}",
                        f"lastSeen={visibility_last_seen_text}",
                        f"packets={visibility_packet_count_text}",
                        f"rate={visibility_packet_rate_text}",
                    )
                ),
            ]
        )
    family_records_by_key = {
        family.key: family
        for family in passive_result.family_records
    } if isinstance(passive_result, RunResult) else {}
    evidence_family_keys = tuple(passive_device.evidence_family_keys or ())
    evidence_families: List[FamilyRecord] = []
    supporting_families: List[FamilyRecord] = []
    evidence_packet_count = 0
    for family_key in evidence_family_keys:
        family = family_records_by_key.get(family_key)
        if family is None:
            continue
        if str(family.role or TEXT_EMPTY).startswith("DEVICE_EMITTED_"):
            evidence_families.append(family)
            evidence_packet_count += int(getattr(family.metrics, "count", 0) or 0)
        else:
            supporting_families.append(family)
    family_count = len(evidence_families) + len(supporting_families)
    lines: List[str] = [
        "Shared Passive CAN Deep Dive",
        EVIDENCE_NOTE_SEPARATOR.join(
            (
                f"label={clean_label}",
                "source=passive_discovery_poc",
                f"presence={passive_device.presence_confidence}",
                f"passiveScore={int(passive_device.presence_score)}/100",
                f"expected={passive_device.expected_status}",
            )
        ),
        EVIDENCE_NOTE_SEPARATOR.join(
            (
                f"observerIdentity={visibility_identity_text}",
                f"lastSeen={visibility_last_seen_text}",
                f"packets={visibility_packet_count_text}",
                f"rate={visibility_packet_rate_text}",
                f"existencePackets={evidence_packet_count}",
            )
        ),
        EVIDENCE_NOTE_SEPARATOR.join(
            (
                f"evidenceFamilies={len(evidence_families)}",
                f"supportingFamilies={len(supporting_families)}",
                f"familyTotal={family_count}",
                f"evidenceSources={TEXT_COMMA_DELIM.join(passive_device.evidence_sources) or EVIDENCE_SOURCE_NONE}",
            )
        ),
        "",
        "Evidence Families",
    ]
    if evidence_families:
        for family in evidence_families:
            lines.append(_passive_visibility_family_detail_line(family, counts_for_presence=True))
    else:
        lines.append("No fresh device-emitted families are currently contributing to passive presence.")
    lines.extend(("", "Supporting / Reference Families"))
    if supporting_families:
        for family in supporting_families:
            lines.append(_passive_visibility_family_detail_line(family, counts_for_presence=False))
    else:
        lines.append("No supporting/reference-only families were retained for this device.")
    lines.extend(("", "Evidence Gaps"))
    gaps = tuple(passive_device.evidence_gaps or ())
    if gaps:
        for gap in gaps[:8]:
            lines.append(f"- {str(gap).strip()}")
    else:
        lines.append("No major passive CAN evidence gaps reported.")
    lines.extend(("", "Guesses"))
    guesses = _passive_visibility_guess_lines(
        passive_device=passive_device,
        evidence_families=evidence_families,
        supporting_families=supporting_families,
    )
    if guesses:
        lines.extend(guesses)
    else:
        lines.append("No conservative passive-only guesses available.")
    return "\n".join(lines)


def resolve_passive_visibility_device_record(
    *,
    label: str,
    passive_result: Optional[RunResult],
    visibility_identity_text: str,
) -> Optional[DeviceRecord]:
    """
    NAME
        resolve_passive_visibility_device_record - Resolve one passive visibility row to a shared DeviceRecord by label first, then passive identity.
    """
    clean_label = str(label or TEXT_EMPTY).strip().lower()
    if not clean_label or not isinstance(passive_result, RunResult):
        return None
    for device in passive_result.device_records:
        device_label = str(device.profile_label or TEXT_EMPTY).strip().lower()
        if device_label == clean_label:
            return device
    parsed_identity = _parse_visibility_identity_key(visibility_identity_text)
    if parsed_identity is None:
        return None
    manufacturer, device_type, device_id = parsed_identity
    for device in passive_result.device_records:
        identity = getattr(device, "identity", None)
        if identity is None:
            continue
        if (
            int(getattr(identity, "manufacturer", -1)) == manufacturer
            and int(getattr(identity, "device_type", -1)) == device_type
            and int(getattr(identity, "device_id", -1)) == device_id
        ):
            return device
    return None


def _parse_visibility_identity_key(identity_text: object) -> Optional[Tuple[int, int, int]]:
    """
    NAME
        _parse_visibility_identity_key - Parse one passive visibility identity key into manufacturer, device type, and device id.
    """
    clean_identity = str(identity_text or TEXT_EMPTY).strip()
    if not clean_identity:
        return None
    parts = [part.strip() for part in clean_identity.split(TEXT_COLON_DELIM)]
    if len(parts) != COUNT_THREE:
        return None
    try:
        manufacturer = int(parts[INT_ZERO])
        device_type = int(parts[INT_ONE])
        device_id = int(parts[INT_TWO])
    except ValueError:
        return None
    return (manufacturer, device_type, device_id)


def _visibility_identity_text_from_device(visibility_device: Optional[Mapping[str, Any]]) -> str:
    """
    NAME
        _visibility_identity_text_from_device - Return one passive visibility identity key from a visibility row payload.
    """
    if not isinstance(visibility_device, Mapping):
        return TEXT_EMPTY
    identity = visibility_device.get("identityKey")
    return str(identity or TEXT_EMPTY).strip()


def _passive_visibility_guess_lines(
    *,
    passive_device: DeviceRecord,
    evidence_families: List[FamilyRecord],
    supporting_families: List[FamilyRecord],
) -> List[str]:
    """
    NAME
        _passive_visibility_guess_lines - Build conservative labeled hypotheses from passive-only evidence.
    """
    guesses: List[str] = []
    manufacturer_name = str(passive_device.manufacturer_name or TEXT_EMPTY).strip()
    device_type_name = str(passive_device.device_type_name or TEXT_EMPTY).strip()
    model_name = str(passive_device.model_name or TEXT_EMPTY).strip()
    expected_status = str(passive_device.expected_status or TEXT_EMPTY).strip().lower()
    presence_confidence = str(passive_device.presence_confidence or TEXT_EMPTY).strip().lower()
    evidence_roles = {
        str(family.role or TEXT_EMPTY).strip()
        for family in evidence_families
        if str(family.role or TEXT_EMPTY).strip()
    }
    if manufacturer_name or device_type_name:
        guess_text = f"{TEXT_GUESS_PREFIX}likely manufacturer={manufacturer_name or EVIDENCE_SOURCE_NONE}"
        if device_type_name:
            guess_text += f", deviceType={device_type_name}"
        guesses.append(guess_text)
    if model_name and model_name != MODEL_UNKNOWN:
        guesses.append(f"{TEXT_GUESS_PREFIX}likely model family={model_name}")
    if expected_status == EXPECTED_STATUS_UNEXPECTED and presence_confidence in ("high", "medium"):
        guesses.append(
            f"{TEXT_GUESS_PREFIX}likely a real bus participant that is missing from the selected profile, not random noise."
        )
    if (
        ROLE_DEVICE_EMITTED_PRIMARY_STATUS in evidence_roles
        and ROLE_DEVICE_EMITTED_SECONDARY_STATUS in evidence_roles
    ):
        guesses.append(
            f"{TEXT_GUESS_PREFIX}periodic primary and secondary status traffic suggests a device that is actively emitting structured status frames."
        )
    if ROLE_DEVICE_EMITTED_HEARTBEAT_HOUSEKEEPING in evidence_roles:
        guesses.append(
            f"{TEXT_GUESS_PREFIX}heartbeat/housekeeping traffic suggests the device is alive on the bus, but not necessarily healthy or correctly configured."
        )
    if not supporting_families and evidence_families:
        guesses.append(
            f"{TEXT_GUESS_PREFIX}current passive evidence is mostly device-emitted; topology position and attached mechanism still cannot be inferred from CAN traffic alone."
        )
    return guesses


def _passive_visibility_family_detail_line(
    family: FamilyRecord,
    *,
    counts_for_presence: bool,
) -> str:
    """
    NAME
        _passive_visibility_family_detail_line - Render one compact family-level CAN evidence line.
    """
    return EVIDENCE_NOTE_SEPARATOR.join(
        (
            f"api={int(family.key.api_class)}/{int(family.key.api_index)}",
            f"role={str(family.role or TEXT_EMPTY).strip() or EVIDENCE_SOURCE_NONE}",
            f"rate={float(getattr(family.metrics, 'rate_hz', 0.0) or 0.0):.1f}Hz",
            f"count={int(getattr(family.metrics, 'count', 0) or 0)}",
            f"countsForPresence={'yes' if counts_for_presence else 'no'}",
        )
    )


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


def _ctre_base_url_for_rio(rio_host: str) -> str:
    """
    NAME
        _ctre_base_url_for_rio - Build the default CTRE diagnostic base URL for one connected roboRIO host.
    """
    clean_host = str(rio_host or TEXT_EMPTY).strip()
    if not clean_host:
        return TEXT_EMPTY
    return ENRICHMENT_CTRE_BASE_URL_FMT.format(host=clean_host)


def _device_identity_key_from_profile_device(
    profile_device: Mapping[str, Any],
) -> Optional[Tuple[int, int, int]]:
    """
    NAME
        _device_identity_key_from_profile_device - Resolve one passive identity key from a profile-device row.
    """
    try:
        return (
            int(profile_device.get(KEY_MANUFACTURER)),
            int(profile_device.get(KEY_DEVICE_TYPE)),
            int(profile_device.get(KEY_ID)),
        )
    except Exception:
        return None


def _collect_console_log_enrichment(
    *,
    output_log_text: str,
    profile_path: str,
    profile_name: str,
) -> Optional[EnrichmentRecord]:
    """
    NAME
        _collect_console_log_enrichment - Parse the current host output pane as one console-log enrichment source.
    """
    clean_text = str(output_log_text or TEXT_EMPTY).strip()
    if not clean_text:
        return None
    temp_path = TEXT_EMPTY
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            suffix="_bringup_console.log",
            delete=False,
        ) as handle:
            handle.write(clean_text)
            temp_path = str(handle.name)
        return enrich_console_log(
            temp_path,
            profile_path=profile_path,
            profile_name=profile_name,
        )
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def _index_console_enrichment_by_label(record: EnrichmentRecord) -> Dict[str, Dict[str, Any]]:
    """
    NAME
        _index_console_enrichment_by_label - Group parsed console-log enrichment rows by device label.
    """
    indexed: Dict[str, Dict[str, Any]] = {}
    for row in tuple(record.evidence_records):
        if not isinstance(row, dict):
            continue
        label = str(row.get(CONSOLE_RECORD_KEY_CANDIDATE_PROFILE_NODE, TEXT_EMPTY)).strip()
        if not label:
            continue
        key = label.lower()
        entry = indexed.setdefault(
            key,
            {
                KEY_LABEL: label,
                CONSOLE_KEY_EVENTS: [],
                CONSOLE_KEY_SUMMARY: EVIDENCE_SOURCE_NONE,
                CONSOLE_KEY_HAS_ERROR: False,
                CONSOLE_KEY_HAS_WARN: False,
            },
        )
        severity = str(row.get(CONSOLE_RECORD_KEY_SEVERITY, TEXT_EMPTY)).strip().upper()
        parsed_type = str(row.get(CONSOLE_RECORD_KEY_PARSED_EVIDENCE_TYPE, TEXT_EMPTY)).strip()
        raw_message = str(row.get(CONSOLE_RECORD_KEY_RAW_MESSAGE, TEXT_EMPTY)).strip()
        summary = parsed_type or raw_message or EVIDENCE_SOURCE_NONE
        entry[CONSOLE_KEY_EVENTS].append(summary)
        if severity in (CONSOLE_SEVERITY_ERROR, CONSOLE_SEVERITY_FATAL):
            entry[CONSOLE_KEY_HAS_ERROR] = True
        elif severity == CONSOLE_SEVERITY_WARN:
            entry[CONSOLE_KEY_HAS_WARN] = True
        if entry[CONSOLE_KEY_SUMMARY] == EVIDENCE_SOURCE_NONE:
            entry[CONSOLE_KEY_SUMMARY] = summary
    return indexed


def _enrichment_device_entry(
    enrichment_snapshot: Optional[Mapping[str, Any]],
    label: str,
) -> Dict[str, Any]:
    """
    NAME
        _enrichment_device_entry - Return the normalized enrichment bundle for one device label.
    """
    if not isinstance(enrichment_snapshot, Mapping):
        return {}
    devices = enrichment_snapshot.get(ENRICHMENT_RUN_DEVICES_KEY)
    if not isinstance(devices, Mapping):
        return {}
    entry = devices.get(str(label or TEXT_EMPTY).strip().lower())
    return dict(entry) if isinstance(entry, Mapping) else {}


def _build_enrichment_text(
    *,
    enrichment_snapshot: Optional[Mapping[str, Any]],
    enrichment_entry: Mapping[str, Any],
    now_s: Optional[float] = None,
) -> str:
    """
    NAME
        _build_enrichment_text - Format one shared enrichment evidence block.
    """
    if not isinstance(enrichment_snapshot, Mapping):
        return ENRICHMENT_PANEL_EMPTY
    refreshed_snapshot = refresh_enrichment_run_snapshot_age(enrichment_snapshot, now_s=now_s)
    metadata = refreshed_snapshot.get(ENRICHMENT_RUN_METADATA_KEY)
    age_text = str(refreshed_snapshot.get(ENRICHMENT_RUN_AGE_KEY, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE
    lines: List[str] = [
        ENRICHMENT_PANEL_LENS,
        f"runStatus={enrichment_run_status_text(refreshed_snapshot, now_s=now_s)}",
        f"runAge={age_text}",
    ]
    if isinstance(metadata, Mapping):
        for source_key in (
            ENRICHMENT_SOURCE_CTRE,
            ENRICHMENT_SOURCE_TOPOLOGY,
            ENRICHMENT_SOURCE_CONSOLE_LOG,
        ):
            source_row = metadata.get(source_key)
            if not isinstance(source_row, Mapping):
                continue
            status_text = str(source_row.get(ENRICHMENT_RUN_STATUS_KEY, ENRICHMENT_STATUS_NOT_RUN)).strip() or ENRICHMENT_STATUS_NOT_RUN
            summary_text = str(source_row.get(ENRICHMENT_RUN_SUMMARY_KEY, ENRICHMENT_PANEL_EMPTY)).strip() or ENRICHMENT_PANEL_EMPTY
            lines.append(f"{source_key}={status_text} | {summary_text}")
    device_sources: List[str] = []
    ctre_entry = enrichment_entry.get(ENRICHMENT_DEVICE_KEY_CTRE)
    if isinstance(ctre_entry, Mapping):
        device_sources.append(ENRICHMENT_SOURCE_CTRE)
        ctre_parts = [
            "ctreHttp=present",
            f"model={str(ctre_entry.get(ENRICHMENT_CTRE_KEY_MODEL, TEXT_EMPTY)).strip() or EVIDENCE_SOURCE_NONE}",
            f"firmware={str(ctre_entry.get(ENRICHMENT_CTRE_KEY_FIRMWARE, TEXT_EMPTY)).strip() or EVIDENCE_SOURCE_NONE}",
            f"status={str(ctre_entry.get(ENRICHMENT_CTRE_KEY_STATUS, TEXT_EMPTY)).strip() or EVIDENCE_SOURCE_NONE}",
            f"vendor={str(ctre_entry.get(ENRICHMENT_CTRE_KEY_VENDOR, TEXT_EMPTY)).strip() or EVIDENCE_SOURCE_NONE}",
            f"canbus={str(ctre_entry.get(ENRICHMENT_CTRE_KEY_CANBUS, TEXT_EMPTY)).strip() or EVIDENCE_SOURCE_NONE}",
            f"hardwareRev={str(ctre_entry.get(ENRICHMENT_CTRE_KEY_HARDWARE_REV, TEXT_EMPTY)).strip() or EVIDENCE_SOURCE_NONE}",
            f"bootloader={str(ctre_entry.get(ENRICHMENT_CTRE_KEY_BOOTLOADER, TEXT_EMPTY)).strip() or EVIDENCE_SOURCE_NONE}",
            f"manufactured={str(ctre_entry.get(ENRICHMENT_CTRE_KEY_MANUFACTURED, TEXT_EMPTY)).strip() or EVIDENCE_SOURCE_NONE}",
            f"isProLicensed={_bool_text(ctre_entry.get(ENRICHMENT_CTRE_KEY_IS_PRO_LICENSED))}",
            f"supportsControl={_bool_text(ctre_entry.get(ENRICHMENT_CTRE_KEY_SUPPORTS_CONTROL))}",
            f"supportsConfigs={_bool_text(ctre_entry.get(ENRICHMENT_CTRE_KEY_SUPPORTS_CONFIGS))}",
            (
                "supportsDecoratedSelfTest="
                + _bool_text(ctre_entry.get(ENRICHMENT_CTRE_KEY_SUPPORTS_DECORATED_SELF_TEST))
            ),
        ]
        lines.append(
            EVIDENCE_NOTE_SEPARATOR.join(ctre_parts)
        )
    topology_entry = enrichment_entry.get(ENRICHMENT_DEVICE_KEY_TOPOLOGY)
    if isinstance(topology_entry, Mapping):
        device_sources.append(ENRICHMENT_SOURCE_TOPOLOGY)
        lines.append(
            EVIDENCE_NOTE_SEPARATOR.join(
                (
                    "topology=present",
                    f"nodeType={str(topology_entry.get(KEY_TOPOLOGY_NODE_TYPE, TEXT_EMPTY)).strip() or EVIDENCE_SOURCE_NONE}",
                    f"neighbors={str(topology_entry.get(KEY_TOPOLOGY_NEIGHBOR_COUNT, EVIDENCE_SOURCE_NONE))}",
                )
            )
        )
    console_entry = enrichment_entry.get(ENRICHMENT_DEVICE_KEY_CONSOLE)
    if isinstance(console_entry, Mapping):
        device_sources.append(ENRICHMENT_SOURCE_CONSOLE_LOG)
        lines.append(
            EVIDENCE_NOTE_SEPARATOR.join(
                (
                    "consoleLog=present",
                    f"summary={str(console_entry.get(CONSOLE_KEY_SUMMARY, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE}",
                )
            )
        )
    if device_sources:
        lines.append(
            ENRICHMENT_PANEL_DEVICE_PRESENT_FMT.format(
                sources=TEXT_COMMA_DELIM.join(device_sources)
            )
        )
    else:
        lines.append(ENRICHMENT_PANEL_DEVICE_NONE)
    if len(lines) == 2 and not isinstance(metadata, Mapping):
        return ENRICHMENT_PANEL_EMPTY
    return "\n".join(lines)


def _build_enrichment_run_note(
    enrichment_snapshot: Optional[Mapping[str, Any]],
    *,
    now_s: Optional[float] = None,
) -> str:
    """
    NAME
        _build_enrichment_run_note - Format one concise enrichment-run clue for shared notes/conflict text.
    """
    if not isinstance(enrichment_snapshot, Mapping):
        return TEXT_EMPTY
    refreshed_snapshot = refresh_enrichment_run_snapshot_age(enrichment_snapshot, now_s=now_s)
    ran_at = refreshed_snapshot.get(ENRICHMENT_RUN_AT_EPOCH_KEY)
    if not isinstance(ran_at, (int, float)) or float(ran_at) <= 0.0:
        return TEXT_EMPTY
    metadata = refreshed_snapshot.get(ENRICHMENT_RUN_METADATA_KEY)
    if not isinstance(metadata, Mapping):
        return TEXT_EMPTY
    ctre_row = metadata.get(ENRICHMENT_SOURCE_CTRE, {})
    topology_row = metadata.get(ENRICHMENT_SOURCE_TOPOLOGY, {})
    console_row = metadata.get(ENRICHMENT_SOURCE_CONSOLE_LOG, {})
    return ENRICHMENT_NOTE_RUN_FMT.format(
        age=str(refreshed_snapshot.get(ENRICHMENT_RUN_AGE_KEY, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE,
        ctre=str(
            ctre_row.get(ENRICHMENT_RUN_STATUS_KEY, ENRICHMENT_STATUS_NOT_RUN)
            if isinstance(ctre_row, Mapping)
            else ENRICHMENT_STATUS_NOT_RUN
        ).strip()
        or ENRICHMENT_STATUS_NOT_RUN,
        topology=str(
            topology_row.get(ENRICHMENT_RUN_STATUS_KEY, ENRICHMENT_STATUS_NOT_RUN)
            if isinstance(topology_row, Mapping)
            else ENRICHMENT_STATUS_NOT_RUN
        ).strip()
        or ENRICHMENT_STATUS_NOT_RUN,
        console=str(
            console_row.get(ENRICHMENT_RUN_STATUS_KEY, ENRICHMENT_STATUS_NOT_RUN)
            if isinstance(console_row, Mapping)
            else ENRICHMENT_STATUS_NOT_RUN
        ).strip()
        or ENRICHMENT_STATUS_NOT_RUN,
    )


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
        source = EVIDENCE_SOURCE_RUNTIME_STATE
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
    now_s: Optional[float] = None,
) -> str:
    """
    NAME
        _probe_missing_text - Explain why no device-specific probe result exists.
    """
    if is_infrastructure_device:
        if _runtime_infrastructure_signal_present(runtime_device, now_s=now_s):
            return TEXT_UPDATE_DELIM.join((PROBE_INFRA_SCOPE_NOTE, PROBE_INFRA_RUNTIME_DETAIL))
        return TEXT_UPDATE_DELIM.join((PROBE_INFRA_SCOPE_NOTE, PROBE_INFRA_SCOPE_DETAIL))
    if float(last_probe_completed_at or 0.0) <= 0.0:
        return PROBE_NOT_RUN_YET
    if not isinstance(runtime_device, Mapping):
        return PROBE_NOT_IN_RUNTIME_SET
    if not bool(runtime_device.get(RUNTIME_DEVICE_KEY_INSTANTIATED, False)):
        return PROBE_NOT_IN_RUNTIME_SET
    return PROBE_NO_DEVICE_RESULT


def _runtime_infrastructure_signal_present(
    runtime_device: Optional[Mapping[str, Any]],
    *,
    now_s: Optional[float] = None,
) -> bool:
    """
    NAME
        _runtime_infrastructure_signal_present - Return whether singleton runtime telemetry provides real presence evidence.
    """
    if not isinstance(runtime_device, Mapping):
        return False
    if now_s is None:
        import time

        now_s = time.time()
    last_seen_ms = runtime_device.get(RUNTIME_DEVICE_KEY_LAST_SEEN_MS)
    has_fresh_last_seen = False
    if isinstance(last_seen_ms, (int, float)) and float(last_seen_ms) > 0.0:
        age_sec = max(0.0, float(now_s) - (float(last_seen_ms) / 1000.0))
        has_fresh_last_seen = age_sec <= INFRA_RUNTIME_FRESH_SEC
        if not has_fresh_last_seen:
            return False
    if bool(runtime_device.get(RUNTIME_DEVICE_KEY_INSTANTIATED, False)):
        if has_fresh_last_seen:
            return True
    lifecycle_state = str(runtime_device.get(RUNTIME_DEVICE_KEY_LIFECYCLE_STATE, TEXT_EMPTY)).strip().lower()
    if has_fresh_last_seen and (lifecycle_state.startswith("instantiated") or lifecycle_state.startswith("controlled")):
        return True
    bus_v = runtime_device.get(RUNTIME_DEVICE_KEY_BUS_V)
    if isinstance(bus_v, (int, float)) and float(bus_v) > 1.0:
        return True
    total_current_a = runtime_device.get(RUNTIME_DEVICE_KEY_TOTAL_CURRENT_A)
    if isinstance(total_current_a, (int, float)) and float(total_current_a) > 0.05:
        return True
    temp_c = runtime_device.get(RUNTIME_DEVICE_KEY_TEMP_C)
    if isinstance(temp_c, (int, float)) and float(temp_c) > 1.0:
        return True
    attachments = runtime_device.get(RUNTIME_DEVICE_KEY_ATTACHMENTS)
    if isinstance(attachments, list) and len(attachments) > 0:
        return True
    return has_fresh_last_seen and (lifecycle_state.startswith("instantiated") or lifecycle_state.startswith("controlled"))


def _is_infrastructure_device(label: object) -> bool:
    """
    NAME
        _is_infrastructure_device - Return whether one Evidence label is a singleton infrastructure device.
    """
    normalized = str(label or TEXT_EMPTY).strip().lower()
    return normalized in INFRASTRUCTURE_DEVICE_LABELS


def _requires_can_visible_infrastructure_presence(label: object) -> bool:
    """
    NAME
        _requires_can_visible_infrastructure_presence - Return whether an infrastructure singleton must stay CAN-visible.
    """
    normalized = str(label or TEXT_EMPTY).strip().lower()
    return normalized in INFRASTRUCTURE_CAN_PATH_SINGLETON_LABELS


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
