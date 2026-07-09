from __future__ import annotations

"""
NAME
    enrich_ctre.py - Optional CTRE HTTP enrichment for passive discovery.

DESCRIPTION
    Queries the CTRE diagnostic server for inventory and selected self-test data
    so passive observations can be corroborated with richer CTRE-specific state.
"""

import json
import urllib.parse
import urllib.request
from typing import Dict, List, Tuple

from tools.passive_discovery_poc.constants import (
    CTRE_HTTP_ACTION_DECORATED_SELFTEST,
    CTRE_HTTP_ACTION_GET_DEVICES,
    CTRE_HTTP_CANBUS_RIO,
    CTRE_MANUFACTURER,
    ENCODING_UTF8,
)
from tools.passive_discovery_poc.metadata import normalize_device_type


def collect_ctre_enrichment(base_url: str) -> Tuple[Dict[Tuple[int, int, int], Dict[str, object]], List[str]]:
    """
    NAME
        collect_ctre_enrichment - Collect CTRE device inventory and selected details.

    RETURNS
        Mapping keyed by passive device identity plus a warning list.
    """
    warnings: List[str] = []
    if not base_url.strip():
        return ({}, warnings)
    try:
        devices_payload = _http_get_json(base_url=base_url, params={"action": CTRE_HTTP_ACTION_GET_DEVICES})
    except Exception as exc:
        warnings.append(f"CTRE HTTP unavailable: {exc}")
        return ({}, warnings)
    device_array = devices_payload.get("DeviceArray", [])
    if not isinstance(device_array, list):
        warnings.append("CTRE HTTP getdevices response missing DeviceArray")
        return ({}, warnings)
    result: Dict[Tuple[int, int, int], Dict[str, object]] = {}
    for device in device_array:
        if not isinstance(device, dict):
            continue
        model = str(device.get("Model", "")).strip()
        device_id = device.get("ID")
        if not isinstance(device_id, int):
            continue
        device_type = normalize_device_type(CTRE_MANUFACTURER, _infer_ctre_device_type(model))
        key = (CTRE_MANUFACTURER, device_type, device_id)
        entry: Dict[str, object] = {
            "model": model,
            "name": str(device.get("Name", "")).strip(),
            "firmware": str(device.get("CurrentVers", "")).strip(),
            "supportsDecoratedSelfTest": bool(device.get("SupportsDecoratedSelfTest", False)),
            "supportsConfigs": bool(device.get("SupportsConfigs", False)),
        }
        if bool(device.get("SupportsDecoratedSelfTest", False)) and model:
            try:
                detail_payload = _http_get_json(
                    base_url=base_url,
                    params={
                        "action": CTRE_HTTP_ACTION_DECORATED_SELFTEST,
                        "model": model,
                        "id": str(device_id),
                        "canbus": CTRE_HTTP_CANBUS_RIO,
                    },
                )
                self_test = detail_payload.get("SelfTest", {})
                if isinstance(self_test, dict):
                    entry["faultsTrue"] = _collect_true_flags(self_test=self_test, prefix="Fault_")
                    entry["stickyFaultsTrue"] = _collect_true_flags(self_test=self_test, prefix="StickyFault_")
            except Exception as exc:
                warnings.append(f"CTRE decoratedselftest failed for {model} {device_id}: {exc}")
        result[key] = entry
    return (result, warnings)


def _http_get_json(base_url: str, params: Dict[str, str]) -> Dict[str, object]:
    """
    NAME
        _http_get_json - Issue one CTRE diagnostic GET and decode JSON.
    """
    query = urllib.parse.urlencode(params)
    url = f"{base_url.rstrip('/')}/?{query}"
    with urllib.request.urlopen(url) as response:
        payload = response.read().decode(ENCODING_UTF8)
    decoded = json.loads(payload)
    if not isinstance(decoded, dict):
        raise ValueError("CTRE HTTP response root was not a JSON object")
    return decoded


def _infer_ctre_device_type(model: str) -> int:
    """
    NAME
        _infer_ctre_device_type - Infer FRC deviceType from CTRE model string.
    """
    normalized = model.lower()
    if "talon fx" in normalized:
        return 2
    if "pigeon" in normalized:
        return 6
    if "pdp" in normalized:
        return 8
    if "cancoder" in normalized:
        return 7
    return 0


def _collect_true_flags(self_test: Dict[str, object], prefix: str) -> List[str]:
    """
    NAME
        _collect_true_flags - Extract true fault-style flags from decorated self-test.
    """
    result: List[str] = []
    for key, value in self_test.items():
        if not isinstance(key, str):
            continue
        if not key.startswith(prefix):
            continue
        if isinstance(value, dict) and str(value.get("Value", "")).strip() == "True":
            result.append(key)
    return result
