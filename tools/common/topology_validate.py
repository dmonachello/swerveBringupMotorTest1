from __future__ import annotations

"""
NAME
    topology_validate.py - Shared topology validation helpers.

SYNOPSIS
    from tools.common.topology_validate import validate_topology_payload

DESCRIPTION
    Centralizes topology graph validation so validator, schema-store, editor,
    and CLI surfaces consume one semantic rule set instead of maintaining
    parallel checks.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from tools.common.profile_constants import (
    EDGE_TYPE_ANALOG,
    EDGE_TYPE_CAN_DROP,
    EDGE_TYPE_CAN_TAP,
    EDGE_TYPE_CAN_TRUNK,
    EDGE_TYPE_DIO,
    EDGE_TYPE_POWER,
    EDGE_TYPE_PWM,
    EDGE_TYPE_UNKNOWN,
    EDGE_TYPE_VIRTUAL,
    KEY_DEVICE_REF,
    KEY_EDGE_ID,
    KEY_EDGE_TYPE,
    KEY_FROM_NODE,
    KEY_NODE_KEY,
    KEY_NODE_TYPE,
    KEY_OBJECT_TYPE,
    KEY_TO_NODE,
    NODE_TYPE_DEVICE,
    get_object_type,
)
from tools.common.topology_parse import topology_edges, topology_nodes, topology_root_from_payload

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"

MESSAGE_NODE_KEY_DUP = "Profile '{profile}' topology duplicate node key: {key}."
MESSAGE_DEVICE_REF_REQUIRED = "Profile '{profile}' topology node {key} missing deviceRef."
MESSAGE_DEVICE_REF_UNKNOWN = (
    "Profile '{profile}' topology node {key} references unknown deviceRef '{label}'."
)
MESSAGE_EDGE_ENDPOINT = "Profile '{profile}' topology edge '{edge}' references missing node endpoint."
MESSAGE_EDGE_TYPE_UNKNOWN = "Profile '{profile}' topology edge '{edge}' unknown edgeType '{edge_type}'."

KNOWN_EDGE_TYPES = {
    EDGE_TYPE_CAN_TRUNK,
    EDGE_TYPE_CAN_DROP,
    EDGE_TYPE_CAN_TAP,
    EDGE_TYPE_DIO,
    EDGE_TYPE_PWM,
    EDGE_TYPE_ANALOG,
    EDGE_TYPE_POWER,
    EDGE_TYPE_VIRTUAL,
    EDGE_TYPE_UNKNOWN,
}


@dataclass(frozen=True)
class TopologyIssue:
    """
    NAME
        TopologyIssue - One normalized topology validation issue.
    """

    severity: str
    profile: str
    message: str
    code: str
    details: Dict[str, object]


ISSUE_DUPLICATE_NODE_KEY = "duplicate_node_key"
ISSUE_DEVICE_REF_REQUIRED = "device_ref_required"
ISSUE_DEVICE_REF_UNKNOWN = "device_ref_unknown"
ISSUE_EDGE_ENDPOINT = "edge_endpoint"
ISSUE_EDGE_TYPE_UNKNOWN = "edge_type_unknown"


def registry_label_keys(registry: Dict[str, Dict[str, object]] | Iterable[str]) -> set[str]:
    """
    NAME
        registry_label_keys - Normalize a registry or label iterable to lookup keys.
    """
    if isinstance(registry, dict):
        labels = registry.keys()
    else:
        labels = registry
    return {str(label).strip().lower() for label in labels if str(label).strip()}


def validate_topology_profile(
    topology_profile: Dict[str, object],
    *,
    profile_name: str,
    registry_keys: set[str],
    normalize_nodes: bool = True,
) -> List[TopologyIssue]:
    """
    NAME
        validate_topology_profile - Validate one topology profile graph.
    """
    issues: List[TopologyIssue] = []
    nodes = topology_nodes(topology_profile)
    node_keys: set[int] = set()
    for node in nodes:
        node_key = node.get(KEY_NODE_KEY)
        if isinstance(node_key, int):
            if node_key in node_keys:
                issues.append(
                    TopologyIssue(
                        severity=SEVERITY_ERROR,
                        profile=profile_name,
                        message=MESSAGE_NODE_KEY_DUP.format(profile=profile_name, key=node_key),
                        code=ISSUE_DUPLICATE_NODE_KEY,
                        details={"key": node_key},
                    )
                )
            node_keys.add(node_key)
        object_type = get_object_type(node)
        if normalize_nodes and KEY_OBJECT_TYPE not in node and object_type:
            node[KEY_OBJECT_TYPE] = object_type
        if normalize_nodes and KEY_NODE_TYPE not in node and object_type:
            node[KEY_NODE_TYPE] = object_type
        if object_type != NODE_TYPE_DEVICE:
            continue
        device_ref = node.get(KEY_DEVICE_REF)
        node_key_text = node_key if isinstance(node_key, int) else "?"
        if not isinstance(device_ref, str) or not device_ref.strip():
            issues.append(
                TopologyIssue(
                    severity=SEVERITY_ERROR,
                    profile=profile_name,
                    message=MESSAGE_DEVICE_REF_REQUIRED.format(profile=profile_name, key=node_key_text),
                    code=ISSUE_DEVICE_REF_REQUIRED,
                    details={"key": node_key_text},
                )
            )
            continue
        label_text = device_ref.strip()
        if label_text.lower() not in registry_keys:
            issues.append(
                TopologyIssue(
                    severity=SEVERITY_ERROR,
                    profile=profile_name,
                    message=MESSAGE_DEVICE_REF_UNKNOWN.format(
                        profile=profile_name,
                        key=node_key_text,
                        label=label_text,
                    ),
                    code=ISSUE_DEVICE_REF_UNKNOWN,
                    details={"key": node_key_text, "label": label_text},
                )
            )
    for edge in topology_edges(topology_profile):
        edge_id = edge.get(KEY_EDGE_ID, "?")
        from_node = edge.get(KEY_FROM_NODE)
        to_node = edge.get(KEY_TO_NODE)
        if not isinstance(from_node, int) or not isinstance(to_node, int):
            issues.append(
                TopologyIssue(
                    severity=SEVERITY_ERROR,
                    profile=profile_name,
                    message=MESSAGE_EDGE_ENDPOINT.format(profile=profile_name, edge=edge_id),
                    code=ISSUE_EDGE_ENDPOINT,
                    details={"edge": edge_id},
                )
            )
            continue
        if from_node not in node_keys or to_node not in node_keys:
            issues.append(
                TopologyIssue(
                    severity=SEVERITY_ERROR,
                    profile=profile_name,
                    message=MESSAGE_EDGE_ENDPOINT.format(profile=profile_name, edge=edge_id),
                    code=ISSUE_EDGE_ENDPOINT,
                    details={"edge": edge_id},
                )
            )
        edge_type = edge.get(KEY_EDGE_TYPE)
        if isinstance(edge_type, str) and edge_type not in KNOWN_EDGE_TYPES:
            issues.append(
                TopologyIssue(
                    severity=SEVERITY_WARNING,
                    profile=profile_name,
                    message=MESSAGE_EDGE_TYPE_UNKNOWN.format(
                        profile=profile_name,
                        edge=edge_id,
                        edge_type=edge_type,
                    ),
                    code=ISSUE_EDGE_TYPE_UNKNOWN,
                    details={"edge": edge_id, "edge_type": edge_type},
                )
            )
    return issues


def validate_topology_payload(
    payload: Dict[str, object],
    registry: Dict[str, Dict[str, object]] | Iterable[str],
    *,
    normalize_nodes: bool = True,
) -> Tuple[List[str], List[str]]:
    """
    NAME
        validate_topology_payload - Validate all topology profiles in one payload.

    RETURNS
        (errors, warnings) lists.
    """
    topology = topology_root_from_payload(payload)
    topology_profiles = topology.get("profiles")
    if not isinstance(topology_profiles, dict):
        return [], []
    keys = registry_label_keys(registry)
    issues: List[TopologyIssue] = []
    for profile_name, topology_profile in topology_profiles.items():
        if not isinstance(topology_profile, dict):
            continue
        issues.extend(
            validate_topology_profile(
                topology_profile,
                profile_name=str(profile_name),
                registry_keys=keys,
                normalize_nodes=normalize_nodes,
            )
        )
    errors = [issue.message for issue in issues if issue.severity == SEVERITY_ERROR]
    warnings = [issue.message for issue in issues if issue.severity == SEVERITY_WARNING]
    return errors, warnings
