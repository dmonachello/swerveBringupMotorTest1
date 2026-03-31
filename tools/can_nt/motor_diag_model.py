from __future__ import annotations

"""
NAME
    motor_diag_model.py - Data models for motor diagnosis.

SYNOPSIS
    from tools.can_nt.motor_diag_model import NormalizedMotorTelemetry

DESCRIPTION
    Defines the normalized telemetry records and diagnosis output shapes.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from tools.can_nt.power_diag_model import PowerDistributionTelemetry


@dataclass
class PowerState:
    """
    NAME
        PowerState - Normalized power telemetry.
    """

    bus_v: Optional[float] = None
    applied_duty: Optional[float] = None
    applied_v: Optional[float] = None
    cmd_duty: Optional[float] = None
    motor_v: Optional[float] = None


@dataclass
class LoadState:
    """
    NAME
        LoadState - Normalized load telemetry.
    """

    motor_current_a: Optional[float] = None
    temp_c: Optional[float] = None


@dataclass
class ControllerState:
    """
    NAME
        ControllerState - Controller fault/warn telemetry.
    """

    last_error: Optional[str] = None
    faults_raw: Optional[int] = None
    sticky_faults_raw: Optional[int] = None
    warnings_raw: Optional[int] = None
    sticky_warnings_raw: Optional[int] = None
    fault_flags: List[str] = field(default_factory=list)
    sticky_fault_flags: List[str] = field(default_factory=list)
    warning_flags: List[str] = field(default_factory=list)
    sticky_warning_flags: List[str] = field(default_factory=list)
    fault_status: Optional[str] = None
    sticky_status: Optional[str] = None
    reset: Optional[bool] = None


@dataclass
class LimitState:
    """
    NAME
        LimitState - Normalized limit switch state.
    """

    label: Optional[str] = None
    dio: Optional[int] = None
    invert: Optional[bool] = None
    closed: Optional[bool] = None


@dataclass
class EncoderState:
    """
    NAME
        EncoderState - Normalized encoder telemetry.
    """

    abs_deg: Optional[float] = None
    vel_rpm: Optional[float] = None
    last_error: Optional[str] = None


@dataclass
class MotorSpec:
    """
    NAME
        MotorSpec - Optional motor spec metadata.
    """

    model: Optional[str] = None
    nominal_v: Optional[float] = None
    free_current_a: Optional[float] = None
    stall_current_a: Optional[float] = None


@dataclass
class NotesState:
    """
    NAME
        NotesState - Additional notes for diagnostics.
    """

    health_note: Optional[str] = None
    low_current_note: Optional[str] = None
    snapshot_note: Optional[str] = None


@dataclass
class NormalizedMotorTelemetry:
    """
    NAME
        NormalizedMotorTelemetry - Vendor-agnostic motor telemetry.
    """

    label: Optional[str] = None
    vendor: Optional[str] = None
    present: Optional[bool] = None
    power: PowerState = field(default_factory=PowerState)
    load: LoadState = field(default_factory=LoadState)
    controller: ControllerState = field(default_factory=ControllerState)
    limits: List[LimitState] = field(default_factory=list)
    encoder: EncoderState = field(default_factory=EncoderState)
    spec: MotorSpec = field(default_factory=MotorSpec)
    notes: NotesState = field(default_factory=NotesState)


@dataclass
class DiagnosisFinding:
    """
    NAME
        DiagnosisFinding - One diagnosis cause plus evidence.
    """

    cause: str
    confidence: str
    evidence: List[str] = field(default_factory=list)


@dataclass
class DiagnosisReport:
    """
    NAME
        DiagnosisReport - Full diagnosis result.
    """

    causes: List[DiagnosisFinding] = field(default_factory=list)
    findings: List[DiagnosisFinding] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)


@dataclass
class NormalizeResult:
    """
    NAME
        NormalizeResult - Output from normalization + label lookup.
    """

    telemetry: Optional[NormalizedMotorTelemetry] = None
    errors: List[str] = field(default_factory=list)
    candidates: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    profile_labels: List[str] = field(default_factory=list)
    power_devices: List[PowerDistributionTelemetry] = field(default_factory=list)
