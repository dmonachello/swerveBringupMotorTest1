from __future__ import annotations

"""
NAME
    motor_diag_constants.py - Constants for motor diagnosis.

SYNOPSIS
    from tools.can_nt.motor_diag_constants import CAUSE_CAN_BUS_ISSUE

DESCRIPTION
    Centralizes literals for the motor diagnosis pipeline.
"""

STR_EMPTY = ""

CMD_DIAGNOSE = "diagnose"
CMD_MOTOR = "motor"

INT_ZERO = 0
INT_ONE = 1
INT_TWO = 2
INT_THREE = 3

FLOAT_ZERO = 0.0
FLOAT_ONE = 1.0

SEP_EQ = "="
SEP_COMMA_SPACE = ", "
SEP_NEWLINE = "\n"
BRACKET_OPEN = "["
BRACKET_CLOSE = "]"
TEXT_TRUE = "true"
TEXT_FALSE = "false"

KEY_DEVICES = "devices"
KEY_LABEL = "label"
KEY_VENDOR = "vendor"
KEY_TYPE = "type"
KEY_ID = "id"
KEY_PRESENT = "present"
KEY_PRESENCE_CONF = "presenceConfidence"
KEY_ATTACHMENTS = "attachments"
KEY_ATTACHMENT_TYPE = "type"
KEY_NOTE = "note"

ATTACHMENT_REV_MOTOR = "revMotor"
ATTACHMENT_CTRE_MOTOR = "ctreMotor"
ATTACHMENT_LIMITS = "limits"
ATTACHMENT_ENCODER = "encoder"
ATTACHMENT_MOTOR_SPEC = "motorSpec"

FIELD_BUS_V = "busV"
FIELD_APPLIED_DUTY = "appliedDuty"
FIELD_APPLIED_V = "appliedV"
FIELD_CMD_DUTY = "cmdDuty"
FIELD_MOTOR_CURRENT_A = "motorCurrentA"
FIELD_TEMP_C = "tempC"
FIELD_MOTOR_V = "motorV"
FIELD_LAST_ERROR = "lastError"
FIELD_FAULTS_RAW = "faultsRaw"
FIELD_STICKY_FAULTS_RAW = "stickyFaultsRaw"
FIELD_WARNINGS_RAW = "warningsRaw"
FIELD_STICKY_WARNINGS_RAW = "stickyWarningsRaw"
FIELD_FAULT_FLAGS = "faultFlags"
FIELD_STICKY_FAULT_FLAGS = "stickyFaultFlags"
FIELD_WARNING_FLAGS = "warningFlags"
FIELD_STICKY_WARNING_FLAGS = "stickyWarningFlags"
FIELD_FAULT_STATUS = "faultStatus"
FIELD_STICKY_STATUS = "stickyStatus"
FIELD_RESET = "reset"
FIELD_HEALTH_NOTE = "healthNote"
FIELD_LOW_CURRENT_NOTE = "lowCurrentNote"
FIELD_THRESHOLD = "threshold"
FIELD_LIMIT = "limit"
FIELD_PROFILE_MISSING = "profileMissing"

STR_KOK = "kok"
FIELD_SWITCHES = "switches"
FIELD_DIO = "dio"
FIELD_INVERT = "invert"
FIELD_CLOSED = "closed"
FIELD_ABS_DEG = "absDeg"
FIELD_VEL_RPM = "velRpm"
FIELD_MODEL = "model"
FIELD_NOMINAL_V = "nominalV"
FIELD_FREE_CURRENT_A = "freeCurrentA"
FIELD_STALL_CURRENT_A = "stallCurrentA"

VENDOR_REV = "REV"
VENDOR_CTRE = "CTRE"
VENDOR_UNKNOWN = "UNKNOWN"

CAUSE_CAN_BUS_ISSUE = "CAN_BUS_ISSUE"
CAUSE_CONTROLLER_FAULT = "CONTROLLER_FAULT"
CAUSE_POWER_DISTRIBUTION_FAULT = "POWER_DISTRIBUTION_FAULT"
CAUSE_NO_POWER = "NO_POWER"
CAUSE_LIMIT_ACTIVE = "LIMIT_ACTIVE"
CAUSE_NO_MOTION = "NO_MOTION"
CAUSE_LOW_CURRENT = "LOW_CURRENT"
CAUSE_STALL = "STALL"
CAUSE_NOT_COMMANDED = "NOT_COMMANDED"
CAUSE_CONFIG_MISMATCH = "CONFIG_MISMATCH"
CAUSE_UNKNOWN = "UNKNOWN"

CONF_HIGH = "high"
CONF_MED = "medium"
CONF_LOW = "low"

CAUSE_ORDER = (
    CAUSE_CAN_BUS_ISSUE,
    CAUSE_CONTROLLER_FAULT,
    CAUSE_POWER_DISTRIBUTION_FAULT,
    CAUSE_NO_POWER,
    CAUSE_LIMIT_ACTIVE,
    CAUSE_NO_MOTION,
    CAUSE_LOW_CURRENT,
    CAUSE_STALL,
    CAUSE_NOT_COMMANDED,
    CAUSE_UNKNOWN,
)

APPLIED_V_MIN = 1.0
BUS_V_LOW = 6.0
LOW_CURRENT_FALLBACK = 0.05
LOW_CURRENT_FACTOR = 0.3
STALL_FACTOR = 0.6
MOTION_EPS_RPM = 1.0

MAX_CAUSES = 3

MSG_DEVICE_NOT_FOUND = "ERROR: Device not found."
MSG_DEVICE_AMBIGUOUS = "ERROR: Device label is ambiguous."
MSG_DEVICE_CANDIDATES = "Candidates: {candidates}"
MSG_RUNTIME_MISSING = "ERROR: Failed to fetch runtime state."
MSG_RUNTIME_REQUIRED = "ERROR: Robot connection required."
MSG_DIAGNOSE_SYNTAX = "ERROR: diagnose motor <label>"
MSG_DIAGNOSE_TARGET = "ERROR: diagnose requires motor|device."

OUT_LIKELY_CAUSES = "Likely causes:"
OUT_FINDINGS = "Additional findings:"
OUT_UNKNOWN = "UNKNOWN"
OUT_MISSING_DATA = "Missing data:"
OUT_EVIDENCE = "Evidence:"
OUT_MISSING_FIELDS = "Missing fields:"

FMT_CAUSE_LINE = "{index}) {cause} ({confidence})"
FMT_FINDING_LINE = "- {cause} ({confidence})"
FMT_EVIDENCE_LINE = "  Evidence: {evidence}"
FMT_MISSING_LINE = "  {fields}"

CAUSE_EXPLANATIONS = {
    CAUSE_CAN_BUS_ISSUE: "Device not present on the bus.",
    CAUSE_CONTROLLER_FAULT: "Controller reported a fault or error.",
    CAUSE_POWER_DISTRIBUTION_FAULT: "Power distribution reported a fault or brownout.",
    CAUSE_NO_POWER: "Bus voltage is too low for the controller.",
    CAUSE_LIMIT_ACTIVE: "A limit switch is closed while motion is expected.",
    CAUSE_NO_MOTION: "Motor is commanded but encoder reports no motion.",
    CAUSE_LOW_CURRENT: "Controller is driving but current is unusually low.",
    CAUSE_STALL: "Controller is driving and current is abnormally high.",
    CAUSE_NOT_COMMANDED: "No command was issued to drive the motor.",
    CAUSE_CONFIG_MISMATCH: "Device label is not in the active profile.",
    CAUSE_UNKNOWN: "Insufficient telemetry to determine a cause.",
}
