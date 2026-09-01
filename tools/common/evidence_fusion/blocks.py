from __future__ import annotations

"""
NAME
    blocks.py - Envelope validation and queue-lane selection for evidence blocks.
"""

from typing import List, Optional, Sequence, Tuple

from tools.common.evidence_fusion.constants import (
    MAJOR_TYPES,
    MAJOR_TYPE_CLOCK_TICK,
    MAJOR_TYPE_CONTEXT_REVISION,
    MAJOR_TYPE_SOURCE_STATE,
    PRIORITY_HINT_DEFAULT,
    PRIORITY_HINTS,
    QUEUE_LANE_CLOCK_TICK,
    QUEUE_LANE_CONTEXT,
    QUEUE_LANE_OFFLINE_REPLAY,
    QUEUE_LANE_PERIODIC_PASSIVE,
    QUEUE_LANE_PERIODIC_RUNTIME,
    QUEUE_LANE_SOURCE_HEALTH,
    SCHEMA_VERSION_1,
    SCOPES,
    SOURCE_TYPES_USING_PASSIVE_LANE,
    SOURCE_TYPES_USING_RUNTIME_LANE,
    ZERO_INT,
)
from tools.common.evidence_fusion.types import EvidenceBlock, EvidenceTarget

EMPTY_STRING = ""
PAYLOAD_FIELD_DIMENSION = "dimension"

FIELD_SCHEMA_VERSION = "schema_version"
FIELD_BLOCK_ID = "block_id"
FIELD_SOURCE_TYPE = "source_type"
FIELD_SOURCE_INSTANCE = "source_instance"
FIELD_SOURCE_SESSION_ID = "source_session_id"
FIELD_MAJOR_TYPE = "major_type"
FIELD_SCOPE = "scope"
FIELD_OBSERVED_AT = "observed_at_monotonic_ms"
FIELD_RECEIVED_AT = "received_at_monotonic_ms"
FIELD_CONTEXT_REVISION_ID = "context_revision_id"
FIELD_PRIORITY_HINT = "priority_hint"


def _clean_string(value: object) -> str:
    """
    NAME
        _clean_string - Return one stripped string or an empty string.
    """
    return str(value or EMPTY_STRING).strip()


def validate_evidence_block(block: EvidenceBlock) -> Tuple[bool, Tuple[str, ...]]:
    """
    NAME
        validate_evidence_block - Return whether one block satisfies the stage-1 envelope rules.
    """
    errors: List[str] = []
    if block.schema_version != SCHEMA_VERSION_1:
        errors.append(FIELD_SCHEMA_VERSION)
    if not _clean_string(block.block_id):
        errors.append(FIELD_BLOCK_ID)
    if not _clean_string(block.source_type):
        errors.append(FIELD_SOURCE_TYPE)
    if not _clean_string(block.source_instance):
        errors.append(FIELD_SOURCE_INSTANCE)
    if not _clean_string(block.source_session_id):
        errors.append(FIELD_SOURCE_SESSION_ID)
    if block.major_type not in MAJOR_TYPES:
        errors.append(FIELD_MAJOR_TYPE)
    if block.scope not in SCOPES:
        errors.append(FIELD_SCOPE)
    if not isinstance(block.observed_at_monotonic_ms, int) or block.observed_at_monotonic_ms < ZERO_INT:
        errors.append(FIELD_OBSERVED_AT)
    if not isinstance(block.received_at_monotonic_ms, int) or block.received_at_monotonic_ms < ZERO_INT:
        errors.append(FIELD_RECEIVED_AT)
    if not _clean_string(block.context_revision_id):
        errors.append(FIELD_CONTEXT_REVISION_ID)
    if block.priority_hint not in PRIORITY_HINTS:
        errors.append(FIELD_PRIORITY_HINT)
    if block.target is not None and not isinstance(block.target, EvidenceTarget):
        errors.append("target")
    if not isinstance(block.payload, dict):
        errors.append("payload")
    return len(errors) == ZERO_INT, tuple(errors)


def select_queue_lane(block: EvidenceBlock) -> str:
    """
    NAME
        select_queue_lane - Return the scheduler lane for one accepted block.
    """
    if block.major_type == MAJOR_TYPE_SOURCE_STATE:
        return QUEUE_LANE_SOURCE_HEALTH
    if block.major_type == MAJOR_TYPE_CONTEXT_REVISION:
        return QUEUE_LANE_CONTEXT
    if block.major_type == MAJOR_TYPE_CLOCK_TICK:
        return QUEUE_LANE_CLOCK_TICK
    if block.source_type in SOURCE_TYPES_USING_RUNTIME_LANE:
        return QUEUE_LANE_PERIODIC_RUNTIME
    if block.source_type in SOURCE_TYPES_USING_PASSIVE_LANE:
        return QUEUE_LANE_PERIODIC_PASSIVE
    return QUEUE_LANE_OFFLINE_REPLAY


def build_coalescing_key(block: EvidenceBlock) -> Optional[Tuple[str, ...]]:
    """
    NAME
        build_coalescing_key - Return a latest-wins key for replaceable blocks.
    """
    if block.major_type in (MAJOR_TYPE_SOURCE_STATE, MAJOR_TYPE_CONTEXT_REVISION):
        return None
    target = block.target
    configured_label = EMPTY_STRING if target is None else _clean_string(target.configured_label)
    vendor = EMPTY_STRING if target is None else _clean_string(target.vendor)
    device_type = EMPTY_STRING if target is None else _clean_string(target.device_type)
    interface_type = EMPTY_STRING if target is None else _clean_string(target.interface_type)
    bus_name = EMPTY_STRING if target is None else _clean_string(target.bus_name)
    address_value = EMPTY_STRING if target is None or target.address_value is None else str(target.address_value)
    payload_dimension = _clean_string(block.payload.get(PAYLOAD_FIELD_DIMENSION)) if isinstance(block.payload, dict) else EMPTY_STRING
    return (
        block.source_type,
        block.source_instance,
        block.source_session_id,
        block.major_type,
        block.scope,
        configured_label,
        vendor,
        device_type,
        interface_type,
        bus_name,
        address_value,
        payload_dimension,
    )


def build_unknown_device_key(target: EvidenceTarget) -> str:
    """
    NAME
        build_unknown_device_key - Return a stable unresolved-device key from partial target identity.
    """
    parts: Sequence[object] = (
        target.vendor,
        target.device_type,
        target.interface_type,
        target.bus_name,
        target.address_value,
        target.mechanism_name,
    )
    return "|".join(_clean_string(part) for part in parts)
