from __future__ import annotations

"""
NAME
    json_api.py - Public JSON conversion API for passive discovery.

DESCRIPTION
    Exposes JSON-compatible dictionary conversion and persistence helpers for
    the public passive discovery result model.
"""

from pathlib import Path
from typing import Any, Dict

from tools.passive_discovery_poc.constants import ENCODING_UTF8, JSON_INDENT
from tools.passive_discovery_poc.models import RunResult
from tools.passive_discovery_poc.serializer import run_result_to_dict, write_run_result


def result_to_json_dict(result: RunResult) -> Dict[str, Any]:
    """
    NAME
        result_to_json_dict - Convert one public result into canonical JSON data.
    """
    return run_result_to_dict(result)


def result_from_json_dict(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    NAME
        result_from_json_dict - Return one canonical JSON payload for caller-side restoration.

    NOTES
        The current PoC treats the JSON-compatible payload as the stable restored
        representation. Typed object reconstruction can be added later without
        changing the JSON contract.
    """
    return dict(payload)


def write_json_result(path: str, result: RunResult) -> None:
    """
    NAME
        write_json_result - Persist one result through the public JSON API.
    """
    write_run_result(path=path, result=result)
