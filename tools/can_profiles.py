from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple


DEMO_DEVICES: List[Dict[str, Any]] = [
    {"label": "NEO 22", "manufacturer": 5, "device_type": 2, "device_id": 22, "group": "neos"},
    {"label": "NEO 25", "manufacturer": 5, "device_type": 2, "device_id": 25, "group": "neos"},
    {"label": "NEO 10", "manufacturer": 5, "device_type": 2, "device_id": 10, "group": "neos"},
]

# Fill this in later using --dump-can-expected-ids on a known-good demo setup.
DEMO_CAN_EXPECTED_IDS: List[int] = []


ROBOT_DEVICES: List[Dict[str, Any]] = [
    # NEOs (REV)
    {"label": "FR NEO", "manufacturer": 5, "device_type": 2, "device_id": 10, "group": "neos"},
    {"label": "FL NEO", "manufacturer": 5, "device_type": 2, "device_id": 1,  "group": "neos"},
    {"label": "BR NEO", "manufacturer": 5, "device_type": 2, "device_id": 7,  "group": "neos"},
    {"label": "BL NEO", "manufacturer": 5, "device_type": 2, "device_id": 4,  "group": "neos"},

    # Krakens (CTRE Talon FX)
    {"label": "FR KRAK", "manufacturer": 4, "device_type": 2, "device_id": 11, "group": "krakens"},
    {"label": "FL KRAK", "manufacturer": 4, "device_type": 2, "device_id": 2,  "group": "krakens"},
    {"label": "BR KRAK", "manufacturer": 4, "device_type": 2, "device_id": 8,  "group": "krakens"},
    {"label": "BL KRAK", "manufacturer": 4, "device_type": 2, "device_id": 5,  "group": "krakens"},

    # CANcoders (CTRE)
    {"label": "FR CANC", "manufacturer": 4, "device_type": 7, "device_id": 12, "group": "cancoders"},
    {"label": "FL CANC", "manufacturer": 4, "device_type": 7, "device_id": 3,  "group": "cancoders"},
    {"label": "BR CANC", "manufacturer": 4, "device_type": 7, "device_id": 9,  "group": "cancoders"},
    {"label": "BL CANC", "manufacturer": 4, "device_type": 7, "device_id": 6,  "group": "cancoders"},
]

# Fill this in later using --dump-can-expected-ids on a known-good full robot setup.
ROBOT_CAN_EXPECTED_IDS: List[int] = []


def get_profile(profile: str) -> Tuple[List[Dict[str, Any]], Set[int]]:
    if profile == "demo":
        return (list(DEMO_DEVICES), set(DEMO_CAN_EXPECTED_IDS))
    if profile == "robot":
        return (list(ROBOT_DEVICES), set(ROBOT_CAN_EXPECTED_IDS))
    raise ValueError(f"Unknown profile: {profile}")
