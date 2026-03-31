from __future__ import annotations

"""
NAME
    power_diag_model.py - Data models for power distribution telemetry.

SYNOPSIS
    from tools.can_nt.power_diag_model import PowerDistributionTelemetry

DESCRIPTION
    Defines normalized PDH/PDP telemetry records.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PowerDistributionTelemetry:
    """
    NAME
        PowerDistributionTelemetry - Normalized PDH/PDP telemetry.
    """

    label: Optional[str] = None
    device_type: Optional[str] = None
    vendor: Optional[str] = None
    present: Optional[bool] = None
    bus_v: Optional[float] = None
    total_current_a: Optional[float] = None
    temperature_c: Optional[float] = None
    switchable_enabled: Optional[bool] = None
    fault_flags: List[str] = field(default_factory=list)
    sticky_fault_flags: List[str] = field(default_factory=list)
    channel_current_a: List[float] = field(default_factory=list)
    channel_fault: List[bool] = field(default_factory=list)
    channel_sticky_fault: List[bool] = field(default_factory=list)
