from __future__ import annotations

"""
NAME
    topology_parse.py - Shared topology graph and compatibility parsing helpers.

SYNOPSIS
    from tools.common.topology_parse import topology_profile_from_payload

DESCRIPTION
    Reads the canonical root-level topology graph and exposes both graph-native
    helpers and compatibility views used by older topology renderers.
"""

from typing import Dict, Iterable, List, Optional, Tuple

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
    KEY_BRIDGE_BY_PROFILE,
    KEY_BRIDGE_CONFIG,
    KEY_BRIDGE_GROUPS,
    KEY_BUS,
    KEY_CAN_LINKS,
    KEY_CATEGORY,
    KEY_DEVICE_REF,
    KEY_DEVICE_LINKS,
    KEY_EDGE_ID,
    KEY_EDGE_TYPE,
    KEY_ETHERNET_LINKS,
    KEY_FROM_NODE,
    KEY_FROM_PORT,
    KEY_LABEL,
    KEY_LAYOUT,
    KEY_LINK_A,
    KEY_LINK_B,
    KEY_LINK_DEVICE,
    KEY_LINK_NEIGHBOR,
    KEY_LINK_NEIGHBOR_PORT,
    KEY_LINK_NODE,
    KEY_LINK_PORT,
    KEY_MODEL,
    KEY_NODE_KEY,
    KEY_OBJECT_TYPE,
    KEY_NODE_TYPE,
    KEY_TO_NODE,
    KEY_TO_PORT,
    KEY_TOPOLOGY,
    KEY_TOPOLOGY_EDGES,
    KEY_TOPOLOGY_NODES,
    KEY_TOPOLOGY_PROFILES,
    KEY_TOPOLOGY_VIEW,
    KEY_VENDOR,
    LAYOUT_KEY_ROW,
    LAYOUT_KEY_X,
    LAYOUT_KEY_Y,
    NODE_TYPE_DEVICE,
    get_object_type,
)

EMPTY_STRING = ""
GRAPH_LAYOUT_KEYS = (KEY_BUS, LAYOUT_KEY_ROW, LAYOUT_KEY_X, LAYOUT_KEY_Y)
LAYOUT_KEY_Y_RELATIVE = "yRelative"
KEY_FREE_Y = "freeY"
KEY_FREE_Y_RELATIVE = "freeYRelative"
KEY_PROFILE_VISIBLE = "profileVisible"
KEY_SCALE = "scale"
KEY_TEXT = "text"
CAN_EDGE_TYPES = {
    EDGE_TYPE_CAN_TRUNK,
    EDGE_TYPE_CAN_DROP,
    EDGE_TYPE_CAN_TAP,
}
SUPPORTED_EDGE_TYPES = {
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


def topology_root_from_payload(payload: Dict[str, object]) -> Dict[str, object]:
    """
    NAME
        topology_root_from_payload - Return the root topology section.
    """
    topology = payload.get(KEY_TOPOLOGY)
    return topology if isinstance(topology, dict) else {}


def topology_profile_from_payload(payload: Dict[str, object], profile_name: Optional[str]) -> Dict[str, object]:
    """
    NAME
        topology_profile_from_payload - Return one profile topology graph.
    """
    if not isinstance(profile_name, str) or not profile_name.strip():
        return {}
    topology_root = topology_root_from_payload(payload)
    profiles = topology_root.get(KEY_TOPOLOGY_PROFILES)
    if not isinstance(profiles, dict):
        return {}
    profile = profiles.get(profile_name)
    return profile if isinstance(profile, dict) else {}


def topology_nodes(topology_profile: Dict[str, object]) -> List[Dict[str, object]]:
    """
    NAME
        topology_nodes - Return raw topology node dicts.
    """
    nodes = topology_profile.get(KEY_TOPOLOGY_NODES)
    if isinstance(nodes, list):
        return [entry for entry in nodes if isinstance(entry, dict)]
    return []


def topology_edges(topology_profile: Dict[str, object]) -> List[Dict[str, object]]:
    """
    NAME
        topology_edges - Return raw topology edge dicts.
    """
    edges = topology_profile.get(KEY_TOPOLOGY_EDGES)
    if isinstance(edges, list):
        return [entry for entry in edges if isinstance(entry, dict)]
    return []


def topology_node_lookup(
    topology_profile: Dict[str, object],
    registry: Optional[Dict[str, Dict[str, object]]] = None,
) -> Dict[int, Dict[str, object]]:
    """
    NAME
        topology_node_lookup - Build a resolved lookup keyed by topology node key.

    DESCRIPTION
        Device-backed topology nodes are resolved against the device registry so
        consumers can render labels and vendor/model details without duplicating
        those fields inside the topology node itself.
    """
    resolved: Dict[int, Dict[str, object]] = {}
    registry = registry or {}
    for entry in topology_nodes(topology_profile):
        key = entry.get(KEY_NODE_KEY)
        if not isinstance(key, int):
            continue
        layout = entry.get(KEY_LAYOUT)
        layout_dict = layout if isinstance(layout, dict) else {}
        resolved_entry = dict(entry)
        resolved_entry[KEY_LAYOUT] = layout_dict
        object_type = get_object_type(entry)
        resolved_entry[KEY_OBJECT_TYPE] = object_type
        resolved_entry.setdefault(KEY_NODE_TYPE, object_type)
        if object_type == NODE_TYPE_DEVICE:
            device_ref = str(entry.get(KEY_DEVICE_REF, EMPTY_STRING)).strip()
            if device_ref:
                device = registry.get(device_ref.lower())
                if isinstance(device, dict):
                    resolved_entry[KEY_LABEL] = device_ref
                    resolved_entry[KEY_VENDOR] = device.get(KEY_VENDOR, EMPTY_STRING)
                    resolved_entry[KEY_MODEL] = device.get(KEY_MODEL, EMPTY_STRING)
        resolved[key] = resolved_entry
    return resolved


def topology_neighbor_ports(
    topology_profile: Dict[str, object],
    node_key: int,
) -> List[Dict[str, object]]:
    """
    NAME
        topology_neighbor_ports - Derive directed neighbor entries from edges.
    """
    neighbors: List[Dict[str, object]] = []
    for edge in topology_edges(topology_profile):
        from_node = edge.get(KEY_FROM_NODE)
        to_node = edge.get(KEY_TO_NODE)
        from_port = edge.get(KEY_FROM_PORT)
        to_port = edge.get(KEY_TO_PORT)
        if not isinstance(from_node, int) or not isinstance(to_node, int):
            continue
        if not isinstance(from_port, str) or not isinstance(to_port, str):
            continue
        if from_node == node_key:
            neighbors.append(
                {
                    KEY_LINK_NODE: from_node,
                    KEY_LINK_PORT: from_port,
                    KEY_LINK_NEIGHBOR: to_node,
                    KEY_LINK_NEIGHBOR_PORT: to_port,
                    KEY_EDGE_ID: edge.get(KEY_EDGE_ID),
                    KEY_EDGE_TYPE: edge.get(KEY_EDGE_TYPE),
                }
            )
        elif to_node == node_key:
            neighbors.append(
                {
                    KEY_LINK_NODE: to_node,
                    KEY_LINK_PORT: to_port,
                    KEY_LINK_NEIGHBOR: from_node,
                    KEY_LINK_NEIGHBOR_PORT: from_port,
                    KEY_EDGE_ID: edge.get(KEY_EDGE_ID),
                    KEY_EDGE_TYPE: edge.get(KEY_EDGE_TYPE),
                }
            )
    return neighbors


def topology_neighbor_links(topology_profile: Dict[str, object], node_key: int) -> List[Tuple[int, int]]:
    """
    NAME
        topology_neighbor_links - Derive undirected neighbor links from edges.
    """
    pairs: List[Tuple[int, int]] = []
    seen: set[Tuple[int, int]] = set()
    for edge in topology_edges(topology_profile):
        from_node = edge.get(KEY_FROM_NODE)
        to_node = edge.get(KEY_TO_NODE)
        if not isinstance(from_node, int) or not isinstance(to_node, int):
            continue
        if node_key not in (from_node, to_node) or from_node == to_node:
            continue
        pair = (min(from_node, to_node), max(from_node, to_node))
        if pair in seen:
            continue
        seen.add(pair)
        pairs.append(pair)
    return pairs


def parse_diagram_nodes(diagram: Dict[str, object]) -> List[Dict[str, object]]:
    """
    NAME
        parse_diagram_nodes - Return compatibility node dicts from topology data.

    DESCRIPTION
        The historical parser name is retained so live/read-only surfaces can
        consume the new graph model without a full caller rename.
    """
    nodes: List[Dict[str, object]] = []
    for entry in topology_nodes(diagram):
        layout = entry.get(KEY_LAYOUT)
        layout_dict = layout if isinstance(layout, dict) else {}
        compat = {
            KEY_NODE_KEY: entry.get(KEY_NODE_KEY),
            KEY_OBJECT_TYPE: get_object_type(entry),
            KEY_NODE_TYPE: get_object_type(entry),
            KEY_BUS: layout_dict.get(KEY_BUS, 0),
            LAYOUT_KEY_ROW: layout_dict.get(LAYOUT_KEY_ROW, 0),
            LAYOUT_KEY_X: layout_dict.get(LAYOUT_KEY_X, 0.0),
        }
        if LAYOUT_KEY_Y in layout_dict:
            compat[KEY_FREE_Y] = layout_dict.get(LAYOUT_KEY_Y)
            compat[KEY_FREE_Y_RELATIVE] = bool(layout_dict.get(LAYOUT_KEY_Y_RELATIVE, False))
        if get_object_type(entry) == NODE_TYPE_DEVICE:
            compat[KEY_LABEL] = str(entry.get(KEY_DEVICE_REF, EMPTY_STRING)).strip()
        else:
            compat[KEY_LABEL] = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
            if KEY_CATEGORY in entry:
                compat[KEY_CATEGORY] = entry.get(KEY_CATEGORY)
            if KEY_VENDOR in entry:
                compat[KEY_VENDOR] = entry.get(KEY_VENDOR)
            if KEY_MODEL in entry:
                compat[KEY_MODEL] = entry.get(KEY_MODEL)
            if KEY_TEXT in entry:
                compat[KEY_TEXT] = entry.get(KEY_TEXT)
        if KEY_PROFILE_VISIBLE in entry:
            compat[KEY_PROFILE_VISIBLE] = entry.get(KEY_PROFILE_VISIBLE)
        if KEY_SCALE in entry:
            compat[KEY_SCALE] = entry.get(KEY_SCALE)
        nodes.append(compat)
    return nodes


def parse_diagram_links(
    diagram: Dict[str, object],
) -> Tuple[List[Tuple[int, int]], List[Dict[str, int]], List[Dict[str, int]]]:
    """
    NAME
        parse_diagram_links - Return compatibility link lists from topology data.

    DESCRIPTION
        This preserves the older return shape used by the read-only topology
        view. Ethernet and device-link buckets do not exist in the canonical
        graph and therefore return empty lists for now.
    """
    view = diagram.get(KEY_TOPOLOGY_VIEW)
    view_dict = view if isinstance(view, dict) else {}
    ethernet_links: List[Tuple[int, int]] = []
    raw_ethernet_links = view_dict.get(KEY_ETHERNET_LINKS)
    if isinstance(raw_ethernet_links, list):
        for entry in raw_ethernet_links:
            if not isinstance(entry, dict):
                continue
            a = entry.get(KEY_LINK_A)
            b = entry.get(KEY_LINK_B)
            if not isinstance(a, int) or not isinstance(b, int):
                continue
            ethernet_links.append((min(a, b), max(a, b)))
    can_links: List[Dict[str, int]] = []
    raw_can_links = view_dict.get(KEY_CAN_LINKS)
    if isinstance(raw_can_links, list):
        for entry in raw_can_links:
            if not isinstance(entry, dict):
                continue
            node = entry.get(KEY_LINK_NODE)
            bus = entry.get(KEY_BUS)
            port = entry.get(KEY_LINK_PORT, 1)
            if not isinstance(node, int) or not isinstance(bus, int):
                continue
            if not isinstance(port, int):
                port = 1
            can_links.append(
                {
                    KEY_LINK_NODE: node,
                    KEY_BUS: bus,
                    KEY_LINK_PORT: port,
                }
            )
    device_links: List[Dict[str, int]] = []
    raw_device_links = view_dict.get(KEY_DEVICE_LINKS)
    if isinstance(raw_device_links, list):
        for entry in raw_device_links:
            if not isinstance(entry, dict):
                continue
            node = entry.get(KEY_LINK_NODE)
            device = entry.get(KEY_LINK_DEVICE)
            port = entry.get(KEY_LINK_PORT, 1)
            if not isinstance(node, int) or not isinstance(device, int):
                continue
            if not isinstance(port, int):
                port = 1
            device_links.append(
                {
                    KEY_LINK_NODE: node,
                    KEY_LINK_DEVICE: device,
                    KEY_LINK_PORT: port,
                }
            )
    if ethernet_links or can_links or device_links:
        return ethernet_links, can_links, device_links
    can_links = []
    for edge in topology_edges(diagram):
        edge_type = str(edge.get(KEY_EDGE_TYPE, EMPTY_STRING)).strip()
        from_node = edge.get(KEY_FROM_NODE)
        if edge_type not in CAN_EDGE_TYPES or not isinstance(from_node, int):
            continue
        bus_index = _edge_bus_index(diagram, edge)
        if bus_index is None:
            continue
        can_links.append(
            {
                KEY_LINK_NODE: from_node,
                KEY_BUS: bus_index,
                KEY_LINK_PORT: 1,
            }
        )
    return [], can_links, []


def parse_diagram_aux_links(
    diagram: Dict[str, object],
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]], List[Tuple[int, int]]]:
    """
    NAME
        parse_diagram_aux_links - Extract power, attachment, and DIO edge pairs.
    """
    power_links: List[Tuple[int, int]] = []
    attachment_links: List[Tuple[int, int]] = []
    dio_links: List[Tuple[int, int]] = []
    for edge in topology_edges(diagram):
        from_node = edge.get(KEY_FROM_NODE)
        to_node = edge.get(KEY_TO_NODE)
        edge_type = str(edge.get(KEY_EDGE_TYPE, EMPTY_STRING)).strip()
        if not isinstance(from_node, int) or not isinstance(to_node, int):
            continue
        pair = (from_node, to_node)
        if edge_type == EDGE_TYPE_POWER:
            power_links.append(pair)
        elif edge_type == EDGE_TYPE_VIRTUAL:
            attachment_links.append(pair)
        elif edge_type == EDGE_TYPE_DIO:
            dio_links.append(pair)
    return power_links, attachment_links, dio_links


def parse_diagram_neighbor_links(diagram: Dict[str, object]) -> List[Tuple[int, int]]:
    """
    NAME
        parse_diagram_neighbor_links - Extract neighbor pairs from edges.
    """
    links: List[Tuple[int, int]] = []
    seen: set[Tuple[int, int]] = set()
    for edge in topology_edges(diagram):
        from_node = edge.get(KEY_FROM_NODE)
        to_node = edge.get(KEY_TO_NODE)
        if not isinstance(from_node, int) or not isinstance(to_node, int):
            continue
        if from_node == to_node:
            continue
        pair = (min(from_node, to_node), max(from_node, to_node))
        if pair in seen:
            continue
        seen.add(pair)
        links.append(pair)
    return links


def parse_diagram_neighbor_ports(diagram: Dict[str, object]) -> List[Dict[str, object]]:
    """
    NAME
        parse_diagram_neighbor_ports - Extract directed edge endpoints.
    """
    links: List[Dict[str, object]] = []
    for edge in topology_edges(diagram):
        from_node = edge.get(KEY_FROM_NODE)
        to_node = edge.get(KEY_TO_NODE)
        from_port = edge.get(KEY_FROM_PORT)
        to_port = edge.get(KEY_TO_PORT)
        if not isinstance(from_node, int) or not isinstance(to_node, int):
            continue
        if not isinstance(from_port, str) or not isinstance(to_port, str):
            continue
        links.append(
            {
                KEY_LINK_NODE: from_node,
                KEY_LINK_PORT: from_port,
                KEY_LINK_NEIGHBOR: to_node,
                KEY_LINK_NEIGHBOR_PORT: to_port,
                KEY_EDGE_ID: edge.get(KEY_EDGE_ID),
                KEY_EDGE_TYPE: edge.get(KEY_EDGE_TYPE),
            }
        )
        links.append(
            {
                KEY_LINK_NODE: to_node,
                KEY_LINK_PORT: to_port,
                KEY_LINK_NEIGHBOR: from_node,
                KEY_LINK_NEIGHBOR_PORT: from_port,
                KEY_EDGE_ID: edge.get(KEY_EDGE_ID),
                KEY_EDGE_TYPE: edge.get(KEY_EDGE_TYPE),
            }
        )
    return links


def parse_bridge_groups(payload: Dict[str, object], profile_name: Optional[str]) -> List[Dict[str, object]]:
    """
    NAME
        parse_bridge_groups - Return per-profile bridgeConfig group metadata.
    """
    bridge = payload.get(KEY_BRIDGE_CONFIG)
    if not isinstance(bridge, dict):
        return []
    by_profile = bridge.get(KEY_BRIDGE_BY_PROFILE)
    if not isinstance(by_profile, dict) or not profile_name:
        return []
    entry = by_profile.get(profile_name)
    if not isinstance(entry, dict):
        return []
    groups = entry.get(KEY_BRIDGE_GROUPS)
    if isinstance(groups, list):
        return [group for group in groups if isinstance(group, dict)]
    return []


def _edge_bus_index(topology_profile: Dict[str, object], edge: Dict[str, object]) -> Optional[int]:
    """
    NAME
        _edge_bus_index - Resolve the bus index for one edge from node layout.
    """
    node_by_key = {entry.get(KEY_NODE_KEY): entry for entry in topology_nodes(topology_profile)}
    for key_name in (KEY_FROM_NODE, KEY_TO_NODE):
        node = node_by_key.get(edge.get(key_name))
        if not isinstance(node, dict):
            continue
        layout = node.get(KEY_LAYOUT)
        if not isinstance(layout, dict):
            continue
        bus_index = layout.get(KEY_BUS)
        if isinstance(bus_index, int):
            return bus_index
    return None
