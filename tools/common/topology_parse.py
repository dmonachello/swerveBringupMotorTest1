from __future__ import annotations

"""
NAME
    topology_parse.py - Shared diagram/profile parsing helpers.

SYNOPSIS
    from tools.common.topology_parse import parse_diagram_nodes

DESCRIPTION
    Extracts nodes and link metadata from bringup_system.json diagram sections.
"""

from typing import Dict, Iterable, List, Tuple


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


def parse_bridge_groups(payload: Dict[str, object]) -> List[Dict[str, object]]:
    """
    NAME
        parse_bridge_groups - Return bridgeConfig group metadata.
    """
    bridge = payload.get("bridgeConfig")
    if not isinstance(bridge, dict):
        return []
    groups = bridge.get("groups")
    if isinstance(groups, list):
        return [entry for entry in groups if isinstance(entry, dict)]
    return []
