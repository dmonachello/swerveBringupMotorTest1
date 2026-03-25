from __future__ import annotations

"""
NAME
    topology_draw.py - Shared topology drawing helpers.

SYNOPSIS
    from tools.common.topology_draw import draw_links

DESCRIPTION
    Centralizes link drawing styles for topology views.
"""

from typing import Dict, Iterable, Tuple


def draw_links(
    canvas,
    node_centers: Dict[int, Tuple[float, float]],
    node_bounds: Dict[int, Tuple[float, float, float, float]],
    bus_ys: Iterable[float],
    ethernet_links,
    can_links,
    device_links,
    cannect_nodes,
) -> None:
    """
    NAME
        draw_links - Draw ethernet/can/device links and cannect trunks.
    """
    bus_list = list(bus_ys)
    for a, b in ethernet_links:
        if a in node_centers and b in node_centers:
            ax, ay = node_centers[a]
            bx, by = node_centers[b]
            canvas.create_line(ax, ay, bx, by, width=2, fill="#2563eb", dash=(4, 3))
    for link in can_links:
        node_key = link.get("node")
        bus_index = link.get("bus", 0)
        if node_key not in node_centers or not bus_list:
            continue
        bus_index = min(max(int(bus_index), 0), max(len(bus_list) - 1, 0))
        nx, ny = node_centers[node_key]
        by = bus_list[bus_index]
        start_y = ny
        bounds = node_bounds.get(node_key)
        if bounds is not None:
            x0, y0, x1, y1 = bounds
            start_y = y1 if ny < by else y0
        canvas.create_line(nx, start_y, nx, by, width=2, fill="#2563eb", dash=(2, 2))
    linked_nodes = {int(link.get("node")) for link in can_links if "node" in link}
    for entry in cannect_nodes:
        node_key = entry.get("node")
        bus_index = entry.get("bus", 0)
        kind = entry.get("kind", "")
        if node_key in linked_nodes:
            continue
        if node_key not in node_centers or not bus_list:
            continue
        bus_index = min(max(int(bus_index), 0), max(len(bus_list) - 1, 0))
        nx, ny = node_centers[node_key]
        by = bus_list[bus_index]
        if kind == "inject" and len(bus_list) > 1:
            target = bus_index + 1 if bus_index + 1 < len(bus_list) else bus_index - 1
            if target >= 0:
                by = bus_list[target]
        start_y = ny
        bounds = node_bounds.get(node_key)
        if bounds is not None:
            x0, y0, x1, y1 = bounds
            start_y = y1 if ny < by else y0
        canvas.create_line(nx, start_y, nx, by, width=2, fill="#2563eb", dash=(2, 2))
    for link in device_links:
        node_key = link.get("node")
        device_key = link.get("device")
        if node_key not in node_centers or device_key not in node_centers:
            continue
        nx, ny = node_centers[node_key]
        dx, dy = node_centers[device_key]
        canvas.create_line(nx, ny, dx, dy, width=2, fill="#0f766e", dash=(3, 2))


def draw_group_overlays(
    canvas,
    label_bounds: Dict[str, Tuple[float, float, float, float]],
    groups,
    *,
    zoom: float,
) -> None:
    """
    NAME
        draw_group_overlays - Draw bounding boxes for bridgeConfig groups.
    """
    if not groups or not label_bounds:
        return
    palette = ["#1f6feb", "#f97316", "#16a34a", "#a855f7", "#0ea5e9", "#e11d48"]
    pad = 10.0
    for idx, group in enumerate(groups):
        if not isinstance(group, dict):
            continue
        name = str(group.get("name", "")).strip()
        if not name:
            continue
        members = group.get("members", []) or []
        bounds_list = []
        for member in members:
            if isinstance(member, dict):
                label = member.get("device")
            else:
                label = member
            if not isinstance(label, str):
                continue
            bounds = label_bounds.get(label.strip())
            if bounds:
                bounds_list.append(bounds)
        if not bounds_list:
            continue
        x0 = min(b[0] for b in bounds_list) - pad
        y0 = min(b[1] for b in bounds_list) - pad
        x1 = max(b[2] for b in bounds_list) + pad
        y1 = max(b[3] for b in bounds_list) + pad
        color = palette[idx % len(palette)]
        rect = canvas.create_rectangle(
            x0,
            y0,
            x1,
            y1,
            outline=color,
            width=2,
            dash=(6, 4),
        )
        canvas.tag_lower(rect)
        canvas.create_text(
            x0 + 6,
            y0 + 6,
            text=name,
            anchor="nw",
            fill=color,
            font=("Segoe UI", max(8, int(10 * zoom))),
        )


def draw_bus_segments(
    canvas,
    bus_ys,
    bus_lefts,
    bus_rights,
    *,
    scale: float,
    min_x: float,
    max_x: float,
    x_shift: float,
) -> None:
    """
    NAME
        draw_bus_segments - Draw CAN bus segments with curved connectors.
    """
    bus_list = list(bus_ys)
    if not bus_list:
        return
    turn_radius = max(8.0, 18 * scale)
    for idx, bus_y in enumerate(bus_list):
        seg_left = (
            (bus_lefts[idx] if idx < len(bus_lefts) else min_x - 120) - x_shift
        ) * scale
        seg_right = (
            (bus_rights[idx] if idx < len(bus_rights) else max_x + 240) - x_shift
        ) * scale
        if idx % 2 == 0:
            start_x, end_x = seg_left, seg_right
        else:
            start_x, end_x = seg_right, seg_left
        canvas.create_line(start_x, bus_y, end_x, bus_y, width=4, fill="#444444")
        if idx + 1 < len(bus_list):
            next_y = bus_list[idx + 1]
            connector_x = end_x
            offset = turn_radius if idx % 2 == 0 else -turn_radius
            canvas.create_line(
                connector_x,
                bus_y,
                connector_x + offset,
                bus_y + turn_radius,
                connector_x + offset,
                next_y - turn_radius,
                connector_x,
                next_y,
                width=4,
                fill="#444444",
                smooth=True,
                splinesteps=12,
            )
