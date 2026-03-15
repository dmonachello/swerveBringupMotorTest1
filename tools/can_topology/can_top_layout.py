"""
NAME
    can_top_layout.py - Layout helpers for the CAN topology editor.

SYNOPSIS
    from tools.can_topology.can_top_layout import tidy_selection

DESCRIPTION
    Provides stateless layout helpers (tidy, align, distribute, reset).
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple


def snap_value(value: float, grid_size: int) -> float:
    """
    NAME
        snap_value - Snap a value to the given grid size.
    """
    size = max(1, int(grid_size or 1))
    return round(value / size) * size


def node_half_width(node, box_w: float) -> float:
    """
    NAME
        node_half_width - Compute half the node width in diagram units.
    """
    node_scale = max(0.6, min(2.0, getattr(node, "scale", 1.0)))
    base_w = 180.0 if getattr(node, "node_type", "device") == "callout" else float(box_w)
    return base_w * node_scale / 2.0


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
        bus_lefts.extend([40.0] * (len(bus_offsets) - len(bus_lefts)))
    if len(bus_rights) < len(bus_offsets):
        bus_rights.extend([max_node_x + 200.0] * (len(bus_offsets) - len(bus_rights)))
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


def align_selected(
    nodes: List[object],
    selected_keys: Iterable[int],
    eff_lefts: List[float],
    eff_rights: List[float],
    mode: str,
    box_w: float,
    snap_to_grid: bool,
    grid_size: int,
    margin: float = 10.0,
) -> None:
    """
    NAME
        align_selected - Align selected nodes horizontally.
    """
    selected = {key for key in selected_keys}
    grouped: Dict[int, List[object]] = {}
    for node in nodes:
        if getattr(node, "key", None) not in selected:
            continue
        grouped.setdefault(int(getattr(node, "bus_index", 0)), []).append(node)
    for bus_index, group in grouped.items():
        if not group:
            continue
        xs = [float(getattr(n, "x", 0.0)) for n in group]
        if mode == "left":
            target = min(xs)
        elif mode == "right":
            target = max(xs)
        else:
            target = (min(xs) + max(xs)) / 2.0
        left = eff_lefts[bus_index] if bus_index < len(eff_lefts) else 40.0
        right = eff_rights[bus_index] if bus_index < len(eff_rights) else target + 200.0
        for node in group:
            half_w = node_half_width(node, box_w)
            min_x = left + half_w + margin
            max_x = right - half_w - margin
            if min_x > max_x:
                min_x = max_x = (left + right) / 2.0
            node.x = max(min_x, min(max_x, target))
            if snap_to_grid:
                node.x = snap_value(node.x, grid_size)


def distribute_selected_horizontally(
    nodes: List[object],
    selected_keys: Iterable[int],
    eff_lefts: List[float],
    eff_rights: List[float],
    box_w: float,
    snap_to_grid: bool,
    grid_size: int,
    margin: float = 10.0,
) -> None:
    """
    NAME
        distribute_selected_horizontally - Evenly space selected nodes.
    """
    selected = {key for key in selected_keys}
    grouped: Dict[int, List[object]] = {}
    for node in nodes:
        if getattr(node, "key", None) not in selected:
            continue
        grouped.setdefault(int(getattr(node, "bus_index", 0)), []).append(node)
    for bus_index, group in grouped.items():
        if len(group) < 3:
            continue
        group.sort(key=lambda n: float(getattr(n, "x", 0.0)))
        left = eff_lefts[bus_index] if bus_index < len(eff_lefts) else 40.0
        right = eff_rights[bus_index] if bus_index < len(eff_rights) else group[-1].x + 200.0
        min_x = max(left + margin, float(getattr(group[0], "x", 0.0)))
        max_x = min(right - margin, float(getattr(group[-1], "x", 0.0)))
        spacing = (max_x - min_x) / max(len(group) - 1, 1)
        for idx, node in enumerate(group):
            target = min_x + spacing * idx
            half_w = node_half_width(node, box_w)
            min_bound = left + half_w + margin
            max_bound = right - half_w - margin
            if min_bound > max_bound:
                min_bound = max_bound = (left + right) / 2.0
            node.x = max(min_bound, min(max_bound, target))
            if snap_to_grid:
                node.x = snap_value(node.x, grid_size)


def tidy_selection(
    nodes: List[object],
    selected_keys: Iterable[int],
    eff_lefts: List[float],
    eff_rights: List[float],
    box_w: float,
    snap_to_grid: bool,
    grid_size: int,
    margin: float = 12.0,
) -> None:
    """
    NAME
        tidy_selection - Tidy selected nodes within bus bounds.
    """
    selected = {key for key in selected_keys}
    groups: Dict[int, List[object]] = {}
    for node in nodes:
        if getattr(node, "key", None) not in selected:
            continue
        groups.setdefault(int(getattr(node, "bus_index", 0)), []).append(node)

    bus_indices = [idx for idx in groups.keys() if 0 <= idx < len(eff_lefts)]
    max_columns = max((len(group) for group in groups.values()), default=0)
    use_columns = len(bus_indices) > 1 and max_columns >= 2
    shared_left = max((eff_lefts[idx] for idx in bus_indices), default=40.0)
    shared_right = min(
        (eff_rights[idx] for idx in bus_indices),
        default=max((float(getattr(n, "x", 0.0)) for n in nodes), default=0.0) + 200.0,
    )
    max_half = max((node_half_width(n, box_w) for n in nodes), default=0.0)
    if use_columns:
        left_bound = shared_left + max_half + margin
        right_bound = shared_right - max_half - margin
        if right_bound - left_bound < 40.0:
            use_columns = False

    for bus_index, group in groups.items():
        if not group:
            continue
        group.sort(key=lambda n: float(getattr(n, "x", 0.0)))
        left = eff_lefts[bus_index] if bus_index < len(eff_lefts) else 40.0
        right = eff_rights[bus_index] if bus_index < len(eff_rights) else group[-1].x + 200.0
        if use_columns:
            left_bound = shared_left + max_half + margin
            right_bound = shared_right - max_half - margin
            columns = max_columns
            if columns <= 1 or right_bound <= left_bound:
                use_columns = False
            else:
                spacing = (right_bound - left_bound) / max(columns - 1, 1)
                col_positions = [left_bound + spacing * idx for idx in range(columns)]
                count = len(group)
                for idx, node in enumerate(group):
                    if count <= 1:
                        col_idx = (columns - 1) // 2
                    else:
                        col_idx = int(round(idx * (columns - 1) / (count - 1)))
                    col_idx = max(0, min(columns - 1, col_idx))
                    pos = col_positions[col_idx]
                    half_w = node_half_width(node, box_w)
                    min_bound = left + half_w + margin
                    max_bound = right - half_w - margin
                    if min_bound > max_bound:
                        min_bound = max_bound = (left + right) / 2.0
                    node.x = max(min_bound, min(max_bound, pos))
                    if snap_to_grid:
                        node.x = snap_value(node.x, grid_size)
                continue
        left_bound = left + margin
        right_bound = right - margin
        widths = [node_half_width(n, box_w) * 2 for n in group]
        total_width = sum(widths)
        count = len(group)
        available = max(1.0, right_bound - left_bound)
        gap = 20.0
        if count > 1:
            gap = max(0.0, (available - total_width) / (count - 1))
        positions: List[float] = []
        cursor = left_bound
        for node, width in zip(group, widths):
            half_w = width / 2.0
            cursor = cursor + half_w
            positions.append(cursor)
            cursor = cursor + half_w + gap
        if positions:
            first_half = widths[0] / 2.0
            last_half = widths[-1] / 2.0
            min_edge = positions[0] - first_half
            max_edge = positions[-1] + last_half
            if max_edge > right_bound:
                shift = max_edge - right_bound
                positions = [p - shift for p in positions]
            if positions[0] - first_half < left_bound:
                shift = left_bound - (positions[0] - first_half)
                positions = [p + shift for p in positions]
        for node, pos in zip(group, positions):
            half_w = node_half_width(node, box_w)
            min_bound = left + half_w + margin
            max_bound = right - half_w - margin
            if min_bound > max_bound:
                min_bound = max_bound = (left + right) / 2.0
            node.x = max(min_bound, min(max_bound, pos))
            if snap_to_grid:
                node.x = snap_value(node.x, grid_size)


def reset_layout_per_bus(
    nodes: List[object],
    eff_lefts: List[float],
    eff_rights: List[float],
    box_w: float,
    snap_to_grid: bool,
    grid_size: int,
    margin: float = 12.0,
) -> None:
    """
    NAME
        reset_layout_per_bus - Evenly spread nodes per bus segment.
    """
    groups: Dict[int, List[object]] = {}
    for node in nodes:
        groups.setdefault(int(getattr(node, "bus_index", 0)), []).append(node)
    for bus_index, group in groups.items():
        if not group:
            continue
        group.sort(key=lambda n: float(getattr(n, "x", 0.0)))
        left = eff_lefts[bus_index] if bus_index < len(eff_lefts) else 40.0
        right = eff_rights[bus_index] if bus_index < len(eff_rights) else left + 400.0
        avail_left = left + margin
        avail_right = right - margin
        count = len(group)
        if count == 1:
            pos = (avail_left + avail_right) / 2.0
            node = group[0]
            half_w = node_half_width(node, box_w)
            node.x = max(left + half_w + margin, min(right - half_w - margin, pos))
            if snap_to_grid:
                node.x = snap_value(node.x, grid_size)
            continue
        spacing = (avail_right - avail_left) / max(count - 1, 1)
        for idx, node in enumerate(group):
            target = avail_left + spacing * idx
            half_w = node_half_width(node, box_w)
            min_bound = left + half_w + margin
            max_bound = right - half_w - margin
            if min_bound > max_bound:
                min_bound = max_bound = (left + right) / 2.0
            node.x = max(min_bound, min(max_bound, target))
            if snap_to_grid:
                node.x = snap_value(node.x, grid_size)
