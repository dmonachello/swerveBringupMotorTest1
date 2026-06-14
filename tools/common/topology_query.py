from __future__ import annotations

"""
NAME
    topology_query.py - Shared topology query and projection helpers.

SYNOPSIS
    from tools.common.topology_query import topology_device_summary

DESCRIPTION
    Builds stable node/neighbor summaries from the canonical topology graph so
    CLI and other host-side consumers do not maintain separate projection code.
"""

from typing import Dict, Optional

from tools.common.profile_constants import (
    KEY_BUS,
    KEY_DEVICE_REF,
    KEY_EDGE_ID,
    KEY_EDGE_TYPE,
    KEY_LABEL,
    KEY_LAYOUT,
    KEY_LINK_NEIGHBOR,
    KEY_LINK_NEIGHBOR_PORT,
    KEY_LINK_PORT,
    KEY_NEIGHBOR_LINKS,
    KEY_NEIGHBOR_PORTS,
    KEY_NODE_CLASS,
    KEY_NODE_KEY,
    KEY_NODE_TYPE,
    KEY_OBJECT_TYPE,
    LAYOUT_KEY_ROW,
    LAYOUT_KEY_X,
    get_node_class,
    get_object_type,
)
from tools.common.topology_parse import (
    topology_neighbor_links,
    topology_neighbor_ports,
    topology_node_lookup,
    topology_profile_from_payload,
)


def topology_node_label(node: Dict[str, object]) -> str:
    """
    NAME
        topology_node_label - Resolve the display label for one topology node.
    """
    if str(node.get(KEY_NODE_TYPE, "")).strip() == "device":
        return str(node.get(KEY_DEVICE_REF, "")).strip()
    return str(node.get(KEY_LABEL, "")).strip()


def topology_neighbor_entry(
    key: int,
    node_by_key: Dict[int, Dict[str, object]],
) -> Dict[str, object]:
    """
    NAME
        topology_neighbor_entry - Build one normalized neighbor summary.
    """
    node = node_by_key.get(key, {})
    layout = node.get(KEY_LAYOUT)
    layout_dict = layout if isinstance(layout, dict) else node
    return {
        KEY_NODE_KEY: key,
        KEY_LABEL: topology_node_label(node),
        KEY_BUS: layout_dict.get(KEY_BUS),
        LAYOUT_KEY_ROW: layout_dict.get(LAYOUT_KEY_ROW),
        LAYOUT_KEY_X: layout_dict.get(LAYOUT_KEY_X),
        KEY_OBJECT_TYPE: node.get(KEY_OBJECT_TYPE, get_object_type(node)),
        KEY_NODE_TYPE: node.get(KEY_NODE_TYPE, get_object_type(node)),
        KEY_NODE_CLASS: node.get(KEY_NODE_CLASS, get_node_class(node)),
    }


def resolve_topology_node_key(label: str, node_by_key: Dict[int, Dict[str, object]]) -> Optional[int]:
    """
    NAME
        resolve_topology_node_key - Resolve one topology label to its node key.
    """
    label_key = str(label).strip().lower()
    for key, node in node_by_key.items():
        if topology_node_label(node).strip().lower() == label_key:
            return key
    return None


def topology_device_summary(
    payload: Dict[str, object],
    profile_name: Optional[str],
    label: str,
    registry: Dict[str, Dict[str, object]],
) -> Dict[str, object]:
    """
    NAME
        topology_device_summary - Return topology details for one node label.
    """
    topology_profile = topology_profile_from_payload(payload, profile_name)
    if not topology_profile:
        return {}
    node_by_key = topology_node_lookup(topology_profile, registry)
    node_key = resolve_topology_node_key(label, node_by_key)
    if not isinstance(node_key, int):
        return {}
    target_node = node_by_key.get(node_key)
    if not isinstance(target_node, dict):
        return {}
    layout = target_node.get(KEY_LAYOUT)
    layout_dict = layout if isinstance(layout, dict) else {}
    topology: Dict[str, object] = {
        KEY_NODE_KEY: node_key,
        KEY_LABEL: topology_node_label(target_node),
        KEY_BUS: layout_dict.get(KEY_BUS),
        LAYOUT_KEY_ROW: layout_dict.get(LAYOUT_KEY_ROW),
        LAYOUT_KEY_X: layout_dict.get(LAYOUT_KEY_X),
        KEY_OBJECT_TYPE: target_node.get(KEY_OBJECT_TYPE, get_object_type(target_node)),
        KEY_NODE_TYPE: target_node.get(KEY_NODE_TYPE),
        KEY_NODE_CLASS: target_node.get(KEY_NODE_CLASS, get_node_class(target_node)),
    }
    neighbor_links = []
    for a, b in topology_neighbor_links(topology_profile, node_key):
        other = b if a == node_key else a
        neighbor_links.append(topology_neighbor_entry(other, node_by_key))
    if neighbor_links:
        topology[KEY_NEIGHBOR_LINKS] = neighbor_links
    neighbor_ports = []
    for entry in topology_neighbor_ports(topology_profile, node_key):
        neighbor = entry.get(KEY_LINK_NEIGHBOR)
        if not isinstance(neighbor, int):
            continue
        neighbor_entry = topology_neighbor_entry(neighbor, node_by_key)
        neighbor_entry[KEY_LINK_PORT] = entry.get(KEY_LINK_PORT)
        neighbor_entry[KEY_LINK_NEIGHBOR_PORT] = entry.get(KEY_LINK_NEIGHBOR_PORT)
        if KEY_EDGE_TYPE in entry:
            neighbor_entry[KEY_EDGE_TYPE] = entry.get(KEY_EDGE_TYPE)
        if KEY_EDGE_ID in entry:
            neighbor_entry[KEY_EDGE_ID] = entry.get(KEY_EDGE_ID)
        neighbor_ports.append(neighbor_entry)
    if neighbor_ports:
        topology[KEY_NEIGHBOR_PORTS] = neighbor_ports
    return topology
