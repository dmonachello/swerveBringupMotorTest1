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

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    from tools.common.json_io import read_json
    from tools.common.paths import can_mappings_path, repo_root
except ImportError:  # Allow running as a script from tools/can_topology.
    import sys
    from pathlib import Path as _Path

    sys.path.append(str(_Path(__file__).resolve().parents[1]))
    from common.json_io import read_json  # type: ignore
    from common.paths import can_mappings_path, repo_root  # type: ignore
BUCKET_CATEGORIES = [
    "neos",
    "neo550s",
    "flexes",
    "krakens",
    "falcons",
    "cancoders",
    "candles",
]
SINGLETON_CATEGORIES = ["pdh", "pdp", "pigeon", "robotController"]
GENERIC_CATEGORY = "devices"
DIAGRAM_CATEGORY_CANNECT_INJECT = "cannect_inject"
DIAGRAM_CATEGORY_CANNECT_DIRECT = "cannect_direct"
DIAGRAM_CATEGORY_ANALYZER = "analyzer"
DIAGRAM_CATEGORIES = [
    DIAGRAM_CATEGORY_CANNECT_INJECT,
    DIAGRAM_CATEGORY_CANNECT_DIRECT,
    DIAGRAM_CATEGORY_ANALYZER,
]
INTERFACE_CAN = "CAN"
INTERFACE_DIO = "DIO"
DIO_DEVICE_TYPES = ["limitSwitch", "encoderExternal"]
VENDOR_CTRE = "CTRE"
VENDOR_REV = "REV"
VENDOR_NI = "NI"
DEVICE_NAME_NEO = "NEO"
DEVICE_NAME_NEO_550 = "NEO 550"
DEVICE_NAME_FLEX = "FLEX"
DEVICE_NAME_KRAKEN = "KRAKEN"
DEVICE_NAME_FALCON = "FALCON"
DEVICE_NAME_CANCODER = "CANCoder"
DEVICE_NAME_CANDLE = "CANdle"
DEVICE_NAME_PIGEON = "Pigeon"
DEVICE_NAME_POWER = "PowerDistributionModule"
DEVICE_NAME_ROBOT_CONTROLLER = "robotController"
DEVICE_NAME_MOTOR_CONTROLLER = "MotorController"
DEVICE_NAME_ENCODER = "Encoder"
DEVICE_NAME_GYRO = "GyroSensor"
DEVICE_NAME_MISC = "Miscellaneous"
MODEL_REV_NEO = "REV NEO"
MODEL_REV_NEO_550 = "REV NEO 550"
MODEL_REV_VORTEX = "REV NEO Vortex"
MODEL_CTRE_KRAKEN_X60 = "CTRE Kraken X60"
MODEL_CTRE_FALCON_500 = "CTRE Falcon 500"
MODEL_CTRE_CANCODER = "CTRE CANCoder"
MODEL_CTRE_CANDLE = "CTRE CANdle"
MODEL_CTRE_PIGEON_2 = "CTRE Pigeon 2"
MODEL_PDH = "PDH"
MODEL_PDP = "PDP"
MODEL_ROBORIO = "roboRIO"
MODEL_SYSTEMCORE = "SystemCore"
MOTOR_SPECS_DEPLOY_RELATIVE = ("src", "main", "deploy", "motor_specs.json")
KEY_MOTORS = "motors"
KEY_MODEL = "model"

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
        path = can_mappings_path()
        data = read_json(path)
        manufacturers = sorted(set(str(v) for v in data.get("manufacturers", {}).values()))
        device_types = sorted(set(str(v) for v in data.get("device_types", {}).values()))
        if manufacturers and device_types:
            return manufacturers, device_types
    except Exception:
        pass
    return DEFAULT_MANUFACTURERS, DEFAULT_DEVICE_TYPES


SUPPORTED_MANUFACTURERS, SUPPORTED_DEVICE_TYPES = load_can_mappings()

MODEL_CHOICES_ROBOT_CONTROLLER = [MODEL_ROBORIO, MODEL_SYSTEMCORE]

CATEGORY_DEVICE_DEFAULTS: Dict[str, Tuple[str, str, str]] = {
    "neos": (VENDOR_REV, DEVICE_NAME_NEO, MODEL_REV_NEO),
    "neo550s": (VENDOR_REV, DEVICE_NAME_NEO_550, MODEL_REV_NEO_550),
    "flexes": (VENDOR_REV, DEVICE_NAME_FLEX, MODEL_REV_VORTEX),
    "krakens": (VENDOR_CTRE, DEVICE_NAME_KRAKEN, MODEL_CTRE_KRAKEN_X60),
    "falcons": (VENDOR_CTRE, DEVICE_NAME_FALCON, MODEL_CTRE_FALCON_500),
    "cancoders": (VENDOR_CTRE, DEVICE_NAME_CANCODER, MODEL_CTRE_CANCODER),
    "candles": (VENDOR_CTRE, DEVICE_NAME_CANDLE, MODEL_CTRE_CANDLE),
    "pigeon": (VENDOR_CTRE, DEVICE_NAME_PIGEON, MODEL_CTRE_PIGEON_2),
    "pdh": (VENDOR_REV, DEVICE_NAME_POWER, MODEL_PDH),
    "pdp": (VENDOR_CTRE, DEVICE_NAME_POWER, MODEL_PDP),
    "robotcontroller": (VENDOR_NI, DEVICE_NAME_ROBOT_CONTROLLER, MODEL_ROBORIO),
}


def _normalize_key(value: str) -> str:
    return str(value or "").strip().upper().replace(" ", "")


def _motor_specs_path():
    return repo_root().joinpath(*MOTOR_SPECS_DEPLOY_RELATIVE)


def load_motor_spec_models() -> List[str]:
    """
    NAME
        load_motor_spec_models - Load canonical motor model keys from deploy specs.
    """
    try:
        payload = read_json(_motor_specs_path())
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        return []
    motors = payload.get(KEY_MOTORS)
    if not isinstance(motors, list):
        return []
    models: List[str] = []
    for entry in motors:
        if not isinstance(entry, dict):
            continue
        model = str(entry.get(KEY_MODEL, "")).strip()
        if model and model not in models:
            models.append(model)
    return models


MOTOR_SPEC_MODELS = load_motor_spec_models()
MODEL_CHOICES_REV_MOTOR = [model for model in MOTOR_SPEC_MODELS if _normalize_key(model).startswith("REV")]
MODEL_CHOICES_CTRE_MOTOR = [model for model in MOTOR_SPEC_MODELS if _normalize_key(model).startswith("CTRE")]


def category_device_defaults(category: str, interface: str = INTERFACE_CAN) -> Tuple[str, str, str]:
    """
    NAME
        category_device_defaults - Return vendor/type/model defaults for one editor category.
    """
    if str(interface or "").strip().upper() != INTERFACE_CAN:
        return ("", "", "")
    defaults = CATEGORY_DEVICE_DEFAULTS.get(str(category or "").strip().lower())
    if defaults is None:
        return ("", "", "")
    return defaults


def model_choices_for_context(
    category: str,
    vendor: str,
    device_type: str,
    interface: str = INTERFACE_CAN,
) -> List[str]:
    """
    NAME
        model_choices_for_context - Resolve allowed model values for one editor context.
    """
    if str(interface or "").strip().upper() != INTERFACE_CAN:
        return []
    defaults = category_device_defaults(category, interface)
    if defaults != ("", "", ""):
        return [defaults[2]] if str(category or "").strip().lower() not in {"robotcontroller"} else list(MODEL_CHOICES_ROBOT_CONTROLLER)
    vendor_key = _normalize_key(vendor)
    device_key = _normalize_key(device_type)
    if vendor_key == VENDOR_REV:
        if DEVICE_NAME_POWER.upper() in device_key or MODEL_PDH in device_key:
            return [MODEL_PDH]
        if DEVICE_NAME_MOTOR_CONTROLLER.upper() in device_key:
            return list(MODEL_CHOICES_REV_MOTOR)
        if DEVICE_NAME_NEO_550.replace(" ", "") in device_key:
            return [MODEL_REV_NEO_550]
        if DEVICE_NAME_FLEX in device_key:
            return [MODEL_REV_VORTEX]
        if DEVICE_NAME_NEO in device_key:
            return [MODEL_REV_NEO]
    if vendor_key == VENDOR_CTRE:
        if DEVICE_NAME_POWER.upper() in device_key or MODEL_PDP in device_key:
            return [MODEL_PDP]
        if DEVICE_NAME_MOTOR_CONTROLLER.upper() in device_key:
            return list(MODEL_CHOICES_CTRE_MOTOR)
        if DEVICE_NAME_FALCON in device_key:
            return [MODEL_CTRE_FALCON_500]
        if DEVICE_NAME_KRAKEN in device_key:
            return [MODEL_CTRE_KRAKEN_X60]
        if DEVICE_NAME_CANCODER.upper() in device_key:
            return [MODEL_CTRE_CANCODER]
        if DEVICE_NAME_CANDLE.upper() in device_key:
            return [MODEL_CTRE_CANDLE]
        if DEVICE_NAME_PIGEON.upper() in device_key or DEVICE_NAME_GYRO.upper() in device_key:
            return [MODEL_CTRE_PIGEON_2]
    if vendor_key == VENDOR_NI or DEVICE_NAME_ROBOT_CONTROLLER.upper() in device_key:
        return list(MODEL_CHOICES_ROBOT_CONTROLLER)
    return []


def canonicalize_model_for_context(
    model: str,
    category: str,
    vendor: str,
    device_type: str,
    interface: str = INTERFACE_CAN,
) -> str:
    """
    NAME
        canonicalize_model_for_context - Normalize one model string to a context-approved value.
    """
    raw = str(model or "").strip()
    if not raw:
        return raw
    norm = _normalize_key(raw)
    choices = model_choices_for_context(category, vendor, device_type, interface)
    for choice in choices:
        if _normalize_key(choice) == norm:
            return choice
    alias_pairs = (
        ("ROBORIO", MODEL_ROBORIO),
        ("SYSTEMCORE", MODEL_SYSTEMCORE),
        ("KRAKENX44", "CTRE Kraken X44"),
        ("KRAKEN", MODEL_CTRE_KRAKEN_X60),
        ("FALCON500", MODEL_CTRE_FALCON_500),
        ("FALCON", MODEL_CTRE_FALCON_500),
        ("CANCODER", MODEL_CTRE_CANCODER),
        ("CANDLE", MODEL_CTRE_CANDLE),
        ("PIGEON", MODEL_CTRE_PIGEON_2),
        ("NEO20", "REV NEO 2.0"),
        ("NEO2", "REV NEO 2.0"),
        ("NEO550", MODEL_REV_NEO_550),
        ("NEO", MODEL_REV_NEO),
        ("NEOVORTEX", MODEL_REV_VORTEX),
        ("VORTEX", MODEL_REV_VORTEX),
        ("FLEX", MODEL_REV_VORTEX),
        ("PDH", MODEL_PDH),
        ("PDP", MODEL_PDP),
    )
    for token, canonical in alias_pairs:
        if token in norm and canonical in choices:
            return canonical
    return raw


@dataclass
class Node:
    """
    NAME
        Node - In-memory representation of a CAN node on the diagram.

    DESCRIPTION
        Holds diagram data and profile fields for one CAN device. The x
        coordinate is only used for display and is not saved into the profile.
        Tags are freeform labels stored as a string list.
    """

    key: int
    category: str
    label: str
    can_id: int
    node_type: str = "device"  # "device" or "callout"
    interface: str = INTERFACE_CAN
    vendor: str = ""
    device_type: str = ""
    motor: str = ""
    limits: Optional[Dict[str, int | bool]] = None
    dio: Optional[int] = None
    invert: Optional[bool] = None
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
    tags: List[str] = field(default_factory=list)
    profile_visible: bool = True

    def display_text(self) -> str:
        """
        NAME
            display_text - Build a short label for the canvas.

        RETURNS
            Text string used for the node box label.
        """
        if self.node_type == "callout":
            return self.callout_text
        return self.label

    def display_text_pdf(self) -> str:
        """
        NAME
            display_text_pdf - Build the PDF label text (category omitted).
        """
        if self.node_type == "callout":
            return self.callout_text
        if not isinstance(self.can_id, int) or self.can_id < 0:
            return self.label
        return f"{self.label} (id {self.can_id})"
