from __future__ import annotations

"""
NAME
    topology_support.py - Bringup topology loading for passive discovery.

DESCRIPTION
    Loads the topology graph for one bringup profile and normalizes it into
    enrichment records that can be attached to passive discovery results.
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

from tools.common.profile_constants import (
    INTERFACE_CAN,
    KEY_DEVICE_REF,
    KEY_DEVICES,
    KEY_EDGE_ID,
    KEY_EDGE_TYPE,
    KEY_FROM_NODE,
    KEY_FROM_PORT,
    KEY_LAYOUT,
    KEY_MANUFACTURER,
    KEY_MODEL,
    KEY_NODE_KEY,
    KEY_DEVICE_TYPE,
    KEY_ID,
    KEY_LABEL,
    KEY_TO_NODE,
    KEY_TO_PORT,
    KEY_TOPOLOGY,
    KEY_TOPOLOGY_EDGES,
    KEY_TOPOLOGY_NODES,
    KEY_TOPOLOGY_PROFILES,
    get_device_interface,
    get_node_class,
    get_object_type,
)
from tools.passive_discovery_poc.constants import (
    BUS_UNKNOWN,
    PROFILE_NODE_UNKNOWN,
    TOPOLOGY_EDGE_COUNT_KEY,
    TOPOLOGY_NODE_COUNT_KEY,
    TOPOLOGY_RECORD_KIND_EDGE,
    TOPOLOGY_RECORD_KIND_NODE,
)
from tools.passive_discovery_poc.metadata import normalize_device_type
from tools.passive_discovery_poc.profile_support import _index_devices_by_label, _load_payload, _resolve_profile_name


TopologyRows = List[Dict[str, Any]]
DeviceEnrichmentRows = Dict[Tuple[int, int, int], Dict[str, object]]


def load_topology_rows(profile_path: str, profile_name: str) -> Tuple[str, DeviceEnrichmentRows, TopologyRows, Dict[str, Any]]:
    """
    NAME
        load_topology_rows - Load one profile topology into enrichment-friendly rows.
    """
    payload = _load_payload(path=Path(profile_path))
    resolved_profile = _resolve_profile_name(payload=payload, explicit_name=profile_name)
    topology_root = payload.get(KEY_TOPOLOGY)
    if not isinstance(topology_root, dict):
        raise ValueError("topology mapping missing from bringup profile payload")
    topology_profiles = topology_root.get(KEY_TOPOLOGY_PROFILES)
    if not isinstance(topology_profiles, dict):
        raise ValueError("topology profiles mapping missing from bringup profile payload")
    selected = topology_profiles.get(resolved_profile)
    if not isinstance(selected, dict):
        raise ValueError(f"topology profile not found: {resolved_profile}")
    node_rows = selected.get(KEY_TOPOLOGY_NODES)
    if not isinstance(node_rows, list):
        raise ValueError(f"topology nodes missing for profile: {resolved_profile}")
    edge_rows = selected.get(KEY_TOPOLOGY_EDGES)
    if not isinstance(edge_rows, list):
        raise ValueError(f"topology edges missing for profile: {resolved_profile}")
    root_devices = payload.get(KEY_DEVICES)
    if not isinstance(root_devices, list):
        raise ValueError("root devices list missing from bringup profile payload")
    by_label = _index_devices_by_label(root_devices)
    node_lookup = _index_nodes_by_key(node_rows)
    device_enrichment: DeviceEnrichmentRows = {}
    evidence_rows: TopologyRows = []
    for node in node_rows:
        if not isinstance(node, dict):
            continue
        evidence_rows.append(_node_record(node=node, by_label=by_label, profile_name=resolved_profile))
        _merge_device_topology_enrichment(device_enrichment=device_enrichment, node=node, by_label=by_label)
    for edge in edge_rows:
        if not isinstance(edge, dict):
            continue
        evidence_rows.append(_edge_record(edge=edge, node_lookup=node_lookup, profile_name=resolved_profile))
    metadata = {
        "profilePath": profile_path,
        "profileName": resolved_profile,
        TOPOLOGY_NODE_COUNT_KEY: len([row for row in node_rows if isinstance(row, dict)]),
        TOPOLOGY_EDGE_COUNT_KEY: len([row for row in edge_rows if isinstance(row, dict)]),
    }
    return resolved_profile, device_enrichment, evidence_rows, metadata


def _index_nodes_by_key(rows: List[object]) -> Dict[object, Dict[str, Any]]:
    """
    NAME
        _index_nodes_by_key - Build a node lookup by topology key.
    """
    result: Dict[object, Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = row.get(KEY_NODE_KEY)
        if key is not None:
            result[key] = row
    return result


def _node_record(node: Dict[str, Any], by_label: Dict[str, Dict[str, object]], profile_name: str) -> Dict[str, Any]:
    """
    NAME
        _node_record - Normalize one topology node into one evidence row.
    """
    device_ref = str(node.get(KEY_DEVICE_REF, "")).strip()
    candidate_identity, candidate_profile_node = _resolve_candidate_identity(device_ref=device_ref, by_label=by_label)
    return {
        "kind": TOPOLOGY_RECORD_KIND_NODE,
        "profileName": profile_name,
        "topologyNodeKey": node.get(KEY_NODE_KEY),
        "topologyObjectType": get_object_type(node),
        "topologyNodeClass": get_node_class(node),
        "topologyLayout": dict(node.get(KEY_LAYOUT, {})) if isinstance(node.get(KEY_LAYOUT), dict) else {},
        "candidateProfileNode": candidate_profile_node,
        "candidateDeviceIdentity": candidate_identity,
        "deviceRef": device_ref,
        "rawNode": dict(node),
    }


def _edge_record(edge: Dict[str, Any], node_lookup: Dict[object, Dict[str, Any]], profile_name: str) -> Dict[str, Any]:
    """
    NAME
        _edge_record - Normalize one topology edge into one evidence row.
    """
    from_node = node_lookup.get(edge.get(KEY_FROM_NODE), {})
    to_node = node_lookup.get(edge.get(KEY_TO_NODE), {})
    return {
        "kind": TOPOLOGY_RECORD_KIND_EDGE,
        "profileName": profile_name,
        "topologyEdgeId": edge.get(KEY_EDGE_ID),
        "topologyEdgeType": edge.get(KEY_EDGE_TYPE),
        "fromNodeKey": edge.get(KEY_FROM_NODE),
        "fromPort": edge.get(KEY_FROM_PORT),
        "toNodeKey": edge.get(KEY_TO_NODE),
        "toPort": edge.get(KEY_TO_PORT),
        "fromDeviceRef": str(from_node.get(KEY_DEVICE_REF, "")).strip(),
        "toDeviceRef": str(to_node.get(KEY_DEVICE_REF, "")).strip(),
        "rawEdge": dict(edge),
    }


def _resolve_candidate_identity(
    device_ref: str,
    by_label: Dict[str, Dict[str, object]],
) -> Tuple[Dict[str, int], str]:
    """
    NAME
        _resolve_candidate_identity - Map one topology deviceRef to one CAN identity when possible.
    """
    entry = by_label.get(device_ref)
    if not isinstance(entry, dict):
        return {}, PROFILE_NODE_UNKNOWN
    if str(get_device_interface(entry) or "").strip() != INTERFACE_CAN:
        return {}, str(entry.get(KEY_LABEL, PROFILE_NODE_UNKNOWN)).strip()
    manufacturer = entry.get(KEY_MANUFACTURER)
    device_type = entry.get(KEY_DEVICE_TYPE)
    device_id = entry.get(KEY_ID)
    if not isinstance(manufacturer, int) or not isinstance(device_type, int) or not isinstance(device_id, int):
        return {}, str(entry.get(KEY_LABEL, PROFILE_NODE_UNKNOWN)).strip()
    return (
        {
            "manufacturer": manufacturer,
            "deviceType": normalize_device_type(manufacturer, device_type),
            "deviceId": device_id,
        },
        str(entry.get(KEY_LABEL, PROFILE_NODE_UNKNOWN)).strip(),
    )


def _merge_device_topology_enrichment(
    device_enrichment: DeviceEnrichmentRows,
    node: Dict[str, Any],
    by_label: Dict[str, Dict[str, object]],
) -> None:
    """
    NAME
        _merge_device_topology_enrichment - Attach topology fields to one device-enrichment row.
    """
    device_ref = str(node.get(KEY_DEVICE_REF, "")).strip()
    candidate_identity, candidate_profile_node = _resolve_candidate_identity(device_ref=device_ref, by_label=by_label)
    if not candidate_identity:
        return
    key = (
        int(candidate_identity["manufacturer"]),
        int(candidate_identity["deviceType"]),
        int(candidate_identity["deviceId"]),
    )
    entry = device_enrichment.setdefault(
        key,
        {
            "profileNode": candidate_profile_node or PROFILE_NODE_UNKNOWN,
            "bus": BUS_UNKNOWN,
            "topologyNodes": [],
            "topologyDeviceRef": device_ref,
            "model": str(by_label.get(device_ref, {}).get(KEY_MODEL, "")).strip(),
        },
    )
    topology_nodes = entry.setdefault("topologyNodes", [])
    if isinstance(topology_nodes, list):
        topology_nodes.append(
            {
                "nodeKey": node.get(KEY_NODE_KEY),
                "nodeClass": get_node_class(node),
                "objectType": get_object_type(node),
            }
        )
