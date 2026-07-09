from __future__ import annotations

"""
NAME
    metadata.py - Vendor and device naming helpers for passive discovery.

DESCRIPTION
    Provides lightweight mappings for manufacturer, device type, and model hints
    without depending on larger UI or bridge modules.
"""

from typing import Dict, Tuple

from tools.passive_discovery_poc.constants import (
    CTRE_DEVICE_TYPE_PIGEON_CANONICAL,
    CTRE_DEVICE_TYPE_PIGEON_PASSIVE,
    CTRE_MANUFACTURER,
    DEVICE_TYPE_BROADCAST,
    DEVICE_TYPE_MOTOR_CONTROLLER,
    DEVICE_TYPE_POWER_DISTRIBUTION,
    MODEL_UNKNOWN,
    REV_MANUFACTURER,
    ROBORIO_MANUFACTURER,
)

MANUFACTURER_NAME_MAP: Dict[int, str] = {
    CTRE_MANUFACTURER: "CTRE",
    REV_MANUFACTURER: "REV",
    ROBORIO_MANUFACTURER: "NI",
}

DEVICE_TYPE_NAME_MAP: Dict[int, str] = {
    DEVICE_TYPE_BROADCAST: "Broadcast",
    1: "RobotController",
    DEVICE_TYPE_MOTOR_CONTROLLER: "MotorController",
    CTRE_DEVICE_TYPE_PIGEON_CANONICAL: "Pigeon",
    7: "Encoder",
    DEVICE_TYPE_POWER_DISTRIBUTION: "PowerDistribution",
}

MODEL_HINT_MAP: Dict[Tuple[int, int], str] = {
    (REV_MANUFACTURER, DEVICE_TYPE_MOTOR_CONTROLLER): "Spark MAX/Flex",
    (REV_MANUFACTURER, DEVICE_TYPE_POWER_DISTRIBUTION): "PDH",
    (CTRE_MANUFACTURER, DEVICE_TYPE_MOTOR_CONTROLLER): "Talon FX/Falcon/Kraken",
    (CTRE_MANUFACTURER, 6): "Pigeon",
    (CTRE_MANUFACTURER, DEVICE_TYPE_POWER_DISTRIBUTION): "PDP/PDP-like",
    (ROBORIO_MANUFACTURER, 1): "roboRIO",
}


def manufacturer_name(manufacturer: int) -> str:
    """
    NAME
        manufacturer_name - Return a friendly manufacturer name.
    """
    return MANUFACTURER_NAME_MAP.get(int(manufacturer), f"mfg:{int(manufacturer)}")


def device_type_name(device_type: int) -> str:
    """
    NAME
        device_type_name - Return a friendly device-type name.
    """
    return DEVICE_TYPE_NAME_MAP.get(int(device_type), f"type:{int(device_type)}")


def model_hint(manufacturer: int, device_type: int) -> str:
    """
    NAME
        model_hint - Return a coarse model-family hint for a device key.
    """
    return MODEL_HINT_MAP.get((int(manufacturer), int(device_type)), MODEL_UNKNOWN)


def normalize_device_type(manufacturer: int, device_type: int) -> int:
    """
    NAME
        normalize_device_type - Convert raw observed device types into canonical types.

    DESCRIPTION
        Some CTRE passive CAN families use a different raw device-type value than
        the CTRE HTTP inventory path. The PoC normalizes these so both evidence
        sources merge onto one canonical device identity.
    """
    normalized_manufacturer = int(manufacturer)
    normalized_device_type = int(device_type)
    if normalized_manufacturer == CTRE_MANUFACTURER and normalized_device_type == CTRE_DEVICE_TYPE_PIGEON_PASSIVE:
        return CTRE_DEVICE_TYPE_PIGEON_CANONICAL
    return normalized_device_type
