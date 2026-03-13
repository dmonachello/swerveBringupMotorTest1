"""
NAME
    can_top_models.py - Data models and constants for CAN topology editor.

SYNOPSIS
    from tools.can_topology.can_top_models import Node

DESCRIPTION
    Defines shared constants, device mappings, and the Node dataclass used by
    the topology editor UI.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

BUCKET_CATEGORIES = [
    "neos",
    "neo550s",
    "flexes",
    "krakens",
    "falcons",
    "cancoders",
    "candles",
]
SINGLETON_CATEGORIES = ["pdh", "pdp", "pigeon", "roborio"]
GENERIC_CATEGORY = "devices"

DEFAULT_MANUFACTURERS = [
    "CTRE",
    "REV",
    "KauaiLabs",
    "PlayingWithFusion",
    "AndyMark",
]
DEFAULT_DEVICE_TYPES = [
    "MotorController",
    "Encoder",
    "GyroSensor",
    "PowerDistributionModule",
    "PneumaticsController",
    "Miscellaneous",
]


def load_can_mappings() -> Tuple[List[str], List[str]]:
    """
    NAME
        load_can_mappings - Load manufacturer and device type names.

    DESCRIPTION
        Attempts to read src/main/deploy/can_mappings.json to populate dropdowns.
        Falls back to a small built-in list if unavailable.

    RETURNS
        Tuple of (manufacturers, device_types) lists.
    """
    try:
        root = Path(__file__).resolve().parents[2]
        path = root / "src" / "main" / "deploy" / "can_mappings.json"
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        manufacturers = sorted(set(str(v) for v in data.get("manufacturers", {}).values()))
        device_types = sorted(set(str(v) for v in data.get("device_types", {}).values()))
        if manufacturers and device_types:
            return manufacturers, device_types
    except Exception:
        pass
    return DEFAULT_MANUFACTURERS, DEFAULT_DEVICE_TYPES


SUPPORTED_MANUFACTURERS, SUPPORTED_DEVICE_TYPES = load_can_mappings()


@dataclass
class Node:
    """
    NAME
        Node - In-memory representation of a CAN node on the diagram.

    DESCRIPTION
        Holds diagram data and profile fields for one CAN device. The x
        coordinate is only used for display and is not saved into the profile.
    """

    key: int
    category: str
    label: str
    can_id: int
    node_type: str = "device"  # "device" or "callout"
    vendor: str = ""
    device_type: str = ""
    motor: str = ""
    limits: Optional[Dict[str, int | bool]] = None
    terminator: Optional[bool] = None
    x: float = 0.0
    row: int = 0
    bus_index: int = 0
    scale: float = 1.0
    callout_text: str = ""
    callout_target_type: str = "node"  # "node" or "bus"
    callout_target_bus: int = 0
    callout_target_node_key: Optional[int] = None
    callout_target_category: str = ""
    callout_target_label: str = ""
    callout_target_id: Optional[int] = None
    callout_y: float = 0.0
    free_y: Optional[float] = None

    def display_text(self) -> str:
        """
        NAME
            display_text - Build a short label for the canvas.

        RETURNS
            Text string used for the node box label.
        """
        if self.node_type == "callout":
            return self.callout_text
        return f"{self.label} (id {self.can_id})"

    def display_text_pdf(self) -> str:
        """
        NAME
            display_text_pdf - Build the PDF label text (category omitted).
        """
        if self.node_type == "callout":
            return self.callout_text
        return f"{self.label} (id {self.can_id})"
