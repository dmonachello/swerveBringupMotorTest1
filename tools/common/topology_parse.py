from __future__ import annotations

"""
NAME
    topology_parse.py - Shared diagram/profile parsing helpers.

SYNOPSIS
    from tools.common.topology_parse import parse_diagram_nodes

DESCRIPTION
    Extracts nodes and link metadata from bringup_system.json diagram sections.
"""

from typing import Dict, Iterable, List, Tuple, Optional

from tools.common.profile_constants import (
    KEY_BRIDGE_BY_PROFILE,
    KEY_BRIDGE_GROUPS,
    KEY_DEVICE_LINKS,
    KEY_LABEL,
    KEY_LINK_A,
    KEY_LINK_B,
    KEY_LINK_DEVICE,
    KEY_LINK_NEIGHBOR,
    KEY_LINK_NEIGHBOR_PORT,
    KEY_LINK_NODE,
    KEY_LINK_PORT,
    KEY_NODE_KEY,
    KEY_NEIGHBOR_LINKS,
    KEY_NEIGHBOR_PORTS,
    NEIGHBOR_PORT_BRANCH1,
    NEIGHBOR_PORT_BRANCH2,
    NEIGHBOR_PORT_NEXT,
    CANNECT_PORT_ONE,
    CANNECT_PORT_TWO,
    CANNECT_PORT_THREE,
)

LINK_PAIR_LEN = 2
EMPTY_STRING = ""


def parse_diagram_nodes(diagram: Dict[str, object]) -> List[Dict[str, object]]:
    """
    NAME
        parse_diagram_nodes - Return raw node dicts from diagram metadata.
    """
    nodes = diagram.get("nodes")
    if isinstance(nodes, list):
        return [entry for entry in nodes if isinstance(entry, dict)]
    return []

def parse_diagram_links(diagram: Dict[str, object]) -> Tuple[List[Tuple[int, int]], List[Dict[str, int]], List[Dict[str, int]]]:
    """
    NAME
        parse_diagram_links - Extract ethernet/can/device links from diagram metadata.
    """
    ethernet = [
        (int(link.get("a")), int(link.get("b")))
        for link in (diagram.get("ethernetLinks") or [])
        if isinstance(link, dict) and "a" in link and "b" in link
    ]
    can_links = [
        {"node": int(link.get("node")), "bus": int(link.get("bus")), "port": int(link.get("port", 1))}
        for link in (diagram.get("canLinks") or [])
        if isinstance(link, dict) and "node" in link and "bus" in link
    ]
    device_links = [
        {"node": int(link.get("node")), "device": int(link.get("device")), "port": int(link.get("port", 1))}
        for link in (diagram.get("deviceLinks") or [])
        if isinstance(link, dict) and "node" in link and "device" in link
    ]
    return ethernet, can_links, device_links


def parse_diagram_neighbor_links(diagram: Dict[str, object]) -> List[Tuple[int, int]]:
    """
    NAME
        parse_diagram_neighbor_links - Extract neighbor links from diagram metadata.
    """
    neighbor_links: List[Tuple[int, int]] = []
    entries = diagram.get(KEY_NEIGHBOR_LINKS)
    if not isinstance(entries, list):
        return neighbor_links
    for entry in entries:
        if isinstance(entry, dict):
            a = entry.get(KEY_LINK_A)
            b = entry.get(KEY_LINK_B)
        elif isinstance(entry, (list, tuple)) and len(entry) == LINK_PAIR_LEN:
            a, b = entry
        else:
            continue
        if not isinstance(a, int) or not isinstance(b, int):
            continue
        if a == b:
            continue
        link = (min(a, b), max(a, b))
        if link not in neighbor_links:
            neighbor_links.append(link)
    return neighbor_links


def parse_diagram_neighbor_ports(diagram: Dict[str, object]) -> List[Dict[str, object]]:
    """
    NAME
        parse_diagram_neighbor_ports - Extract neighbor port links from diagram metadata.

    NOTES
        CANnect device links are expanded into neighborPorts entries (next/branch1/branch2)
        using diagram node labels for readability.
    """
    entries = diagram.get(KEY_NEIGHBOR_PORTS)
    if not isinstance(entries, list):
        entries = []
    links: List[Dict[str, object]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        node_key = entry.get(KEY_LINK_NODE)
        port = entry.get(KEY_LINK_PORT)
        neighbor_key = entry.get(KEY_LINK_NEIGHBOR)
        neighbor_port = entry.get(KEY_LINK_NEIGHBOR_PORT)
        if not isinstance(node_key, (int, str)) or not isinstance(neighbor_key, (int, str)):
            continue
        if not isinstance(port, str) or not isinstance(neighbor_port, str):
            continue
        if isinstance(node_key, str):
            node_key = node_key.strip()
        if isinstance(neighbor_key, str):
            neighbor_key = neighbor_key.strip()
        links.append(
            {
                KEY_LINK_NODE: node_key,
                KEY_LINK_PORT: port,
                KEY_LINK_NEIGHBOR: neighbor_key,
                KEY_LINK_NEIGHBOR_PORT: neighbor_port,
            }
        )
    device_links = diagram.get(KEY_DEVICE_LINKS)
    if not isinstance(device_links, list):
        return links
    nodes = parse_diagram_nodes(diagram)
    label_by_key: Dict[object, str] = {}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        key = node.get(KEY_NODE_KEY)
        label = node.get(KEY_LABEL)
        if key is None or not isinstance(label, str):
            continue
        label_text = label.strip()
        if not label_text:
            continue
        label_by_key[key] = label_text
    port_map = {
        CANNECT_PORT_ONE: NEIGHBOR_PORT_NEXT,
        CANNECT_PORT_TWO: NEIGHBOR_PORT_BRANCH1,
        CANNECT_PORT_THREE: NEIGHBOR_PORT_BRANCH2,
    }
    existing = {
        (
            str(entry.get(KEY_LINK_NODE, EMPTY_STRING)).strip().lower(),
            str(entry.get(KEY_LINK_PORT, EMPTY_STRING)).strip().lower(),
            str(entry.get(KEY_LINK_NEIGHBOR, EMPTY_STRING)).strip().lower(),
            str(entry.get(KEY_LINK_NEIGHBOR_PORT, EMPTY_STRING)).strip().lower(),
        )
        for entry in links
    }
    for link in device_links:
        if not isinstance(link, dict):
            continue
        node_key = link.get(KEY_LINK_NODE)
        device_key = link.get(KEY_LINK_DEVICE)
        port = link.get(KEY_LINK_PORT)
        node_label = label_by_key.get(node_key)
        device_label = label_by_key.get(device_key)
        if not node_label or not device_label:
            continue
        port_name = port_map.get(port)
        if port_name is None:
            continue
        forward = (
            node_label.lower(),
            port_name.lower(),
            device_label.lower(),
            NEIGHBOR_PORT_NEXT.lower(),
        )
        if forward not in existing:
            links.append(
                {
                    KEY_LINK_NODE: node_label,
                    KEY_LINK_PORT: port_name,
                    KEY_LINK_NEIGHBOR: device_label,
                    KEY_LINK_NEIGHBOR_PORT: NEIGHBOR_PORT_NEXT,
                }
            )
            existing.add(forward)
        reverse = (
            device_label.lower(),
            NEIGHBOR_PORT_NEXT.lower(),
            node_label.lower(),
            port_name.lower(),
        )
        if reverse not in existing:
            links.append(
                {
                    KEY_LINK_NODE: device_label,
                    KEY_LINK_PORT: NEIGHBOR_PORT_NEXT,
                    KEY_LINK_NEIGHBOR: node_label,
                    KEY_LINK_NEIGHBOR_PORT: port_name,
                }
            )
            existing.add(reverse)
    return links


def parse_bridge_groups(payload: Dict[str, object], profile_name: Optional[str]) -> List[Dict[str, object]]:
    """
    NAME
        parse_bridge_groups - Return per-profile bridgeConfig group metadata.
    """
    bridge = payload.get("bridgeConfig")
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
        return [entry for entry in groups if isinstance(entry, dict)]
    return []
