from __future__ import annotations

"""
NAME
    topology_layout.py - Shared topology layout math helpers.

SYNOPSIS
    from tools.common.topology_layout import node_box_dims

DESCRIPTION
    Centralizes layout math so the topology editor and live views stay aligned.
"""

from typing import Iterable, List, Tuple


DEFAULT_BUS_LEFT = 40.0
DEFAULT_BUS_RIGHT_PAD = 200.0
DEFAULT_BUS_RIGHT_MIN = 480.0


def _node_scale(node) -> float:
    return max(0.6, min(2.0, float(getattr(node, "scale", 1.0))))


def node_box_dims(node, base_w: float, base_h: float, scale: float) -> Tuple[float, float]:
    """
    NAME
        node_box_dims - Return box width/height for a node at a scale.
    """
    node_scale = _node_scale(node)
    if getattr(node, "node_type", "device") == "callout":
        return 180 * scale * node_scale, 50 * scale * node_scale
    return base_w * scale * node_scale, base_h * scale * node_scale


def node_box_y(node, bus_y: float, box_h: float, scale: float) -> Tuple[float, float]:
    """
    NAME
        node_box_y - Return top/bottom Y coordinates for a node box.
    """
    if getattr(node, "row", 0) == 1:
        y0 = bus_y + 30 * scale
        y1 = y0 + box_h
    else:
        y1 = bus_y - 30 * scale
        y0 = y1 - box_h
    return y0, y1


def node_center_y_unscaled(node, bus_offsets: Iterable[float], base_h: float) -> float:
    """
    NAME
        node_center_y_unscaled - Compute unscaled center Y for a node.
    """
    free_y = getattr(node, "free_y", None)
    if free_y is not None:
        offsets = list(bus_offsets)
        if not offsets:
            return float(free_y)
        bus_index = min(max(int(getattr(node, "bus_index", 0)), 0), max(len(offsets) - 1, 0))
        return offsets[bus_index] + float(free_y)
    offsets = list(bus_offsets)
    if not offsets:
        bus_offset = 0.0
    else:
        bus_index = min(max(int(getattr(node, "bus_index", 0)), 0), max(len(offsets) - 1, 0))
        bus_offset = offsets[bus_index]
    node_scale = _node_scale(node)
    if getattr(node, "node_type", "device") == "callout":
        box_h = 50.0 * node_scale
    else:
        box_h = float(base_h) * node_scale
    if getattr(node, "row", 0) == 1:
        return bus_offset + 30.0 + box_h / 2.0
    return bus_offset - 30.0 - box_h / 2.0


def bus_ys(base_y: float, bus_offsets: Iterable[float], scale: float) -> List[float]:
    """
    NAME
        bus_ys - Compute bus Y positions from offsets.
    """
    return [base_y + offset * scale for offset in bus_offsets]


def effective_bus_bounds(
    bus_offsets: List[float],
    bus_lefts: List[float],
    bus_rights: List[float],
    max_node_x: float,
) -> Tuple[List[float], List[float], List[float], List[float]]:
    """
    NAME
        effective_bus_bounds - Compute bus left/right bounds with connectors.
    """
    if len(bus_lefts) < len(bus_offsets):
        bus_lefts.extend([DEFAULT_BUS_LEFT] * (len(bus_offsets) - len(bus_lefts)))
    if len(bus_rights) < len(bus_offsets):
        default_right = max(max_node_x + DEFAULT_BUS_RIGHT_PAD, DEFAULT_BUS_RIGHT_MIN)
        bus_rights.extend([default_right] * (len(bus_offsets) - len(bus_rights)))
    if len(bus_lefts) > len(bus_offsets):
        bus_lefts[:] = bus_lefts[: len(bus_offsets)]
    if len(bus_rights) > len(bus_offsets):
        bus_rights[:] = bus_rights[: len(bus_offsets)]
    eff_lefts = list(bus_lefts)
    eff_rights = list(bus_rights)
    for idx in range(len(eff_lefts) - 1):
        if idx % 2 == 0:
            eff_rights[idx + 1] = eff_rights[idx]
        else:
            eff_lefts[idx + 1] = eff_lefts[idx]
    return bus_lefts, bus_rights, eff_lefts, eff_rights
