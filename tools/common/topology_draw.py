from __future__ import annotations

"""
NAME
    topology_draw.py - Shared topology drawing helpers.

SYNOPSIS
    from tools.common.topology_draw import draw_links

DESCRIPTION
    Centralizes link drawing styles for topology views.
"""

from typing import Dict, Iterable, List, Tuple


def draw_canvas_shape_for_kind(
    canvas,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    kind: str,
    fill: str,
    outline: str,
    width: int = 2,
) -> List[int]:
    """
    NAME
        draw_canvas_shape_for_kind - Draw one node shape on a Tk canvas.
    """
    if kind == "motor":
        inset = max(6.0, min(14.0, (x1 - x0) * 0.08, (y1 - y0) * 0.25))
        points = [
            x0 + inset,
            y0,
            x1 - inset,
            y0,
            x1,
            y0 + inset,
            x1,
            y1 - inset,
            x1 - inset,
            y1,
            x0 + inset,
            y1,
            x0,
            y1 - inset,
            x0,
            y0 + inset,
        ]
        return [canvas.create_polygon(points, fill=fill, outline=outline, width=width, joinstyle="round")]
    if kind == "sensor":
        inset = max(8.0, min(18.0, (x1 - x0) * 0.18))
        yc = (y0 + y1) / 2.0
        points = [
            x0 + inset,
            y0,
            x1 - inset,
            y0,
            x1,
            yc,
            x1 - inset,
            y1,
            x0 + inset,
            y1,
            x0,
            yc,
        ]
        return [canvas.create_polygon(points, fill=fill, outline=outline, width=width, joinstyle="round")]
    if kind == "power":
        xc = (x0 + x1) / 2.0
        yc = (y0 + y1) / 2.0
        points = [xc, y0, x1, yc, xc, y1, x0, yc]
        return [canvas.create_polygon(points, fill=fill, outline=outline, width=width, joinstyle="round")]
    if kind == "controller":
        tab_w = max(18.0, min(42.0, (x1 - x0) * 0.35))
        tab_h = max(10.0, min(18.0, (y1 - y0) * 0.25))
        xc = (x0 + x1) / 2.0
        points = [
            x0,
            y1,
            x1,
            y1,
            x1,
            y0 + tab_h,
            xc + tab_w / 2.0,
            y0 + tab_h,
            xc + tab_w / 2.0,
            y0,
            xc - tab_w / 2.0,
            y0,
            xc - tab_w / 2.0,
            y0 + tab_h,
            x0,
            y0 + tab_h,
        ]
        return [canvas.create_polygon(points, fill=fill, outline=outline, width=width, joinstyle="round")]
    return [canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline=outline, width=width)]


def draw_links(
    canvas,
    node_centers: Dict[int, Tuple[float, float]],
    node_bounds: Dict[int, Tuple[float, float, float, float]],
    bus_ys: Iterable[float],
    ethernet_links,
    can_links,
    device_links,
    cannect_nodes,
    *,
    ethernet_ports: Dict[int, Dict[str, Tuple[float, float]]] | None = None,
    can_ports: Dict[int, Dict[int, Tuple[float, float]]] | None = None,
) -> None:
    """
    NAME
        draw_links - Draw ethernet/can/device links and cannect trunks.
    """
    bus_list = list(bus_ys)
    ethernet_ports = ethernet_ports or {}
    can_ports = can_ports or {}
    for a, b in ethernet_links:
        if a in node_centers and b in node_centers:
            ax, ay = node_centers[a]
            bx, by = node_centers[b]
            a_ports = ethernet_ports.get(a)
            b_ports = ethernet_ports.get(b)
            if a_ports:
                ax, ay = a_ports.get("out", a_ports.get("in", (ax, ay)))
            if b_ports:
                bx, by = b_ports.get("in", b_ports.get("out", (bx, by)))
            canvas.create_line(ax, ay, bx, by, width=2, fill="#2563eb", dash=(4, 3))
    for link in can_links:
        node_key = link.get("node")
        bus_index = link.get("bus", 0)
        port = int(link.get("port", 1))
        if node_key not in node_centers or not bus_list:
            continue
        bus_index = min(max(int(bus_index), 0), max(len(bus_list) - 1, 0))
        nx, ny = node_centers[node_key]
        by = bus_list[bus_index]
        port_map = can_ports.get(node_key)
        if port_map and port in port_map:
            nx, start_y = port_map[port]
        else:
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
        if kind != "inject":
            continue
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
        port = int(link.get("port", 1))
        if node_key not in node_centers or device_key not in node_centers:
            continue
        nx, ny = node_centers[node_key]
        dx, dy = node_centers[device_key]
        port_map = can_ports.get(node_key)
        if port_map and port in port_map:
            nx, ny = port_map[port]
        bounds = node_bounds.get(device_key)
        if bounds is not None:
            dx0, dy0, dx1, _dy1 = bounds
            dx = (dx0 + dx1) / 2.0
            dy = dy0
        canvas.create_line(nx, ny, dx, dy, width=2, fill="#0f766e", dash=(3, 2))


def draw_group_overlays(
    canvas,
    label_bounds: Dict[str, Tuple[float, float, float, float]],
    groups,
    *,
    zoom: float,
) -> List[Dict[str, object]]:
    """
    NAME
        draw_group_overlays - Draw bounding boxes for bridgeConfig by-profile groups.
    """
    if not groups or not label_bounds:
        return []
    palette = ["#1f6feb", "#f97316", "#16a34a", "#a855f7", "#0ea5e9", "#e11d48"]
    pad = 10.0
    overlays: List[Dict[str, object]] = []
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
        label_font_px = max(10, int(12 * zoom))
        label_pad_x = max(6.0, 6.0 * zoom)
        label_pad_y = max(3.0, 3.0 * zoom)
        label_w = max(36.0, len(name) * max(7.5, 8.5 * zoom))
        label_h = max(18.0, 18.0 * zoom)
        label_x0 = x0 + 4.0
        label_y1 = y0 - 4.0
        label_y0 = label_y1 - label_h
        label_x1 = label_x0 + label_w
        label_bg = canvas.create_rectangle(
            label_x0,
            label_y0,
            label_x1,
            label_y1,
            fill="#ffffff",
            outline=color,
            width=1,
        )
        label_text = canvas.create_text(
            label_x0 + label_pad_x,
            label_y0 + label_pad_y,
            text=name,
            anchor="nw",
            fill=color,
            font=("Segoe UI", label_font_px),
        )
        if hasattr(canvas, "tag_raise"):
            canvas.tag_raise(label_bg)
            canvas.tag_raise(label_text)
        overlays.append(
            {
                "name": name,
                "bounds": (x0, y0, x1, y1),
                "label_bounds": (label_x0, label_y0, label_x1, label_y1),
            }
        )
    return overlays


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


def render_topology_canvas_common(
    *,
    canvas,
    nodes,
    bus_ys,
    base_y: float,
    scale: float,
    x_shift: float,
    eff_lefts,
    eff_rights,
    show_can: bool,
    show_dio: bool,
    show_virtual: bool,
    show_power: bool,
    groups,
    selected_node_keys,
    selected_bus_indices,
    drag_free_y,
    bus_connectors,
    bus_lefts,
    bus_rights,
    min_x: float,
    max_x: float,
    bus_offsets,
    box_w_base: float,
    box_h_base: float,
    linked_devices,
    can_bus_links,
    device_links,
    power_links,
    attachment_links,
    dio_links,
    ethernet_links,
    show_groups: bool,
    node_box_dims_fn,
    node_bus_y_fn,
    node_box_y_fn,
    node_center_y_unscaled_fn,
    should_clamp_node_to_bus_fn,
    is_swyft_node_fn,
    is_dio_node_fn,
    shape_kind_fn,
    fill_color_fn,
    outline_color_fn,
    text_color_fn,
    label_text_fn,
    fit_font_size_fn,
    wrap_label_lines_fn,
    node_tag_name_fn=None,
    is_callout_fn=None,
    selected_outline_color: str = "#1f6feb",
    default_outline_width: int = 2,
    show_selection_box: bool = False,
    selection_box_color: str = "#2563eb",
    swyft_port_fill: str = "#4aa3df",
    swyft_port_outline: str = "#1c6ba8",
    swyft_can_color: str = "#2f7a2f",
    swyft_power_text_color: str = "#555555",
    power_line_color: str = "#c05000",
    attach_line_color: str = "#7a5d00",
    dio_line_color: str = "#1f6feb",
    link_line_width: int = 2,
    link_dash=(6, 4),
):
    """
    NAME
        render_topology_canvas_common - Render the shared topology scene layer.

    DESCRIPTION
        Draws bus segments, device/junction nodes, group overlays, and link
        families using one common code path for both editor and read-only live
        views. Surface-specific interactions and editor-only overlays remain
        outside this function.
    """
    import tkinter.font as tkfont

    is_callout_fn = is_callout_fn or (lambda node: getattr(node, "node_type", "") == "callout")
    bus_ys_list = list(bus_ys)
    selected_node_keys = set(selected_node_keys or set())
    selected_bus_indices = set(selected_bus_indices or set())
    linked_devices = set(linked_devices or set())
    drag_free_y = dict(drag_free_y or {})
    if show_can:
        turn_radius = max(8.0, 18 * scale)
        for idx, bus_y in enumerate(bus_ys_list):
            bus_color = "#1f6feb" if idx in selected_bus_indices else "#444444"
            bus_width = 5 if idx in selected_bus_indices else 4
            seg_left = eff_lefts[idx] * scale if idx < len(eff_lefts) else min_x * scale
            seg_right = eff_rights[idx] * scale if idx < len(eff_rights) else max_x * scale
            if idx % 2 == 0:
                start_x, end_x = seg_left, seg_right
            else:
                start_x, end_x = seg_right, seg_left
            canvas.create_line(start_x, bus_y, end_x, bus_y, width=bus_width, fill=bus_color)
            if idx + 1 < len(bus_ys_list):
                if bus_connectors and idx < len(bus_connectors) and not bus_connectors[idx]:
                    continue
                if bus_connectors or len(bus_ys_list) > 1:
                    next_y = bus_ys_list[idx + 1]
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
                        width=bus_width,
                        fill="#444444",
                        smooth=True,
                        splinesteps=12,
                    )
    node_bounds: Dict[int, Tuple[float, float, float, float]] = {}
    node_centers: Dict[int, Tuple[float, float]] = {}
    ethernet_ports: Dict[int, Dict[str, Tuple[float, float]]] = {}
    can_ports: Dict[int, Dict[int, Tuple[float, float]]] = {}
    bounds: List[Tuple[float, float, float, float]] = []
    box_w = box_w_base * scale
    box_h = box_h_base * scale
    for node in nodes:
        if is_callout_fn(node):
            continue
        node_x = (float(getattr(node, "x", 0.0)) - x_shift) * scale
        bus_index = min(max(int(getattr(node, "bus_index", 0)), 0), max(len(bus_ys_list) - 1, 0))
        bus_y = bus_ys_list[bus_index] if bus_ys_list else base_y
        node_bus_y = node_bus_y_fn(node, bus_y, scale)
        node_scale = max(0.6, min(2.0, float(getattr(node, "scale", 1.0))))
        node_box_w = box_w * node_scale
        node_box_h = box_h * node_scale
        seg_left = eff_lefts[bus_index] * scale if bus_index < len(eff_lefts) else min_x * scale
        seg_right = eff_rights[bus_index] * scale if bus_index < len(eff_rights) else max_x * scale
        if should_clamp_node_to_bus_fn(node):
            node_x = min(max(node_x, seg_left + 20), seg_right - 20)
        x0 = node_x - node_box_w / 2.0
        x1 = node_x + node_box_w / 2.0
        if getattr(node, "key", None) in drag_free_y:
            center_y = base_y + float(drag_free_y[getattr(node, "key")]) * scale
            if is_dio_node_fn(node):
                center_y += 30.0 * scale
            y0 = center_y - node_box_h / 2.0
            y1 = center_y + node_box_h / 2.0
            allow_trunk = (not is_swyft_node_fn(node)) or (getattr(node, "category", "") == "cannect_inject")
            if getattr(node, "key", None) not in linked_devices and allow_trunk and not is_dio_node_fn(node) and show_can:
                line_y = y0 if center_y > bus_y else y1
                canvas.create_line(node_x, bus_y, node_x, line_y, width=2, fill="#444444")
        else:
            free_y = getattr(node, "free_y", None)
            if free_y is not None:
                center_y = base_y + float(node_center_y_unscaled_fn(node)) * scale
                if is_dio_node_fn(node):
                    center_y += 30.0 * scale
                y0 = center_y - node_box_h / 2.0
                y1 = center_y + node_box_h / 2.0
                allow_trunk = (not is_swyft_node_fn(node)) or (getattr(node, "category", "") == "cannect_inject")
                if getattr(node, "key", None) not in linked_devices and allow_trunk and not is_dio_node_fn(node) and show_can:
                    line_y = y0 if center_y > bus_y else y1
                    canvas.create_line(node_x, bus_y, node_x, line_y, width=2, fill="#444444")
            else:
                if int(getattr(node, "row", 0)) == 1:
                    y0 = node_bus_y + 30 * scale
                    y1 = y0 + node_box_h
                    allow_trunk = (not is_swyft_node_fn(node)) or (getattr(node, "category", "") == "cannect_inject")
                    if getattr(node, "key", None) not in linked_devices and allow_trunk and not is_dio_node_fn(node) and show_can:
                        canvas.create_line(node_x, bus_y, node_x, y0, width=2, fill="#444444")
                else:
                    y1 = node_bus_y - 30 * scale
                    y0 = y1 - node_box_h
                    allow_trunk = (not is_swyft_node_fn(node)) or (getattr(node, "category", "") == "cannect_inject")
                    if getattr(node, "key", None) not in linked_devices and allow_trunk and not is_dio_node_fn(node) and show_can:
                        canvas.create_line(node_x, y1, node_x, bus_y, width=2, fill="#444444")
        fill = fill_color_fn(node)
        outline = selected_outline_color if getattr(node, "key", None) in selected_node_keys else outline_color_fn(node)
        shape_ids = draw_canvas_shape_for_kind(
            canvas,
            x0,
            y0,
            x1,
            y1,
            shape_kind_fn(node),
            fill,
            outline,
            width=default_outline_width,
        )
        text_color = text_color_fn(fill)
        if is_swyft_node_fn(node):
            cy = (y0 + y1) / 2.0
            ports: Dict[str, Tuple[float, float]] = {}
            if getattr(node, "category", "") == "cannect_inject":
                ports["out"] = (x1, cy)
                ports["power_in"] = (node_x, y1)
            else:
                ports["in"] = (x0, cy)
                ports["out"] = (x1, cy)
                ports["power_out"] = (node_x, y1)
            ethernet_ports[getattr(node, "key")] = ports
            port_w = 6 * scale
            port_h = 10 * scale
            for port_name, (px, py) in ports.items():
                if str(port_name).startswith("power_"):
                    continue
                canvas.create_rectangle(
                    px - port_w / 2,
                    py - port_h / 2,
                    px + port_w / 2,
                    py + port_h / 2,
                    fill=swyft_port_fill,
                    outline=swyft_port_outline,
                    width=1,
                )
            can_count = 1 if getattr(node, "category", "") == "cannect_inject" else 3
            can_ports[getattr(node, "key")] = {}
            inset = 12 * scale
            step = (node_box_w - inset * 2) / max(can_count, 1)
            for idx in range(can_count):
                px = x0 + inset + step * (idx + 0.5)
                can_ports[getattr(node, "key")][idx + 1] = (px, y0 - 10 * scale)
                canvas.create_line(px - 3 * scale, y0, px - 3 * scale, y0 - 10 * scale, width=2, fill=swyft_can_color)
                canvas.create_line(px + 3 * scale, y0, px + 3 * scale, y0 - 10 * scale, width=2, fill=swyft_can_color)
                canvas.create_text(px, y0 - 12 * scale, text=f"C{idx + 1}", font=("Segoe UI", max(7, int(7 * scale))), fill=swyft_can_color)
            power_label = "Power In" if getattr(node, "category", "") == "cannect_inject" else "Power Out"
            power_key = "power_in" if getattr(node, "category", "") == "cannect_inject" else "power_out"
            if power_key in ports:
                px, py = ports[power_key]
                canvas.create_text(px, py + 10 * scale, text=power_label, font=("Segoe UI", max(7, int(7 * scale))), fill=swyft_power_text_color)
        label_text = label_text_fn(node)
        if isinstance(getattr(node, "can_id", None), int) and int(getattr(node, "can_id")) >= 0:
            id_font_size = max(6, int(8 * scale * node_scale))
            id_font = tkfont.Font(family="Segoe UI", size=id_font_size)
            id_line_h = id_font.metrics("linespace")
            label_max_h = max(8.0, node_box_h - id_line_h - 6 * scale)
            label_font_size = max(6, int(9 * scale * node_scale))
            label_font = tkfont.Font(family="Segoe UI", size=label_font_size)
            label_lines = wrap_label_lines_fn(label_text, label_font, node_box_w - 12)
            label_text_wrapped = "\n".join(label_lines)
            label_font_size = fit_font_size_fn(label_text_wrapped, node_box_w - 12, label_max_h, label_font_size)
            label_y = (y0 + y1) / 2.0 - id_line_h * 0.4
            text_id = canvas.create_text(node_x, label_y, text=label_text_wrapped, font=("Segoe UI", label_font_size), fill=text_color, justify="center", width=max(40, int(node_box_w - 12)))
            canvas.create_text(node_x, y1 - id_line_h * 0.6, text=f"ID {getattr(node, 'can_id')}", font=("Segoe UI", id_font_size), fill=text_color, justify="center")
        else:
            font_size = fit_font_size_fn(label_text, node_box_w - 10, node_box_h - 10, int(9 * scale * node_scale))
            text_id = canvas.create_text(node_x, (y0 + y1) / 2.0, text=label_text, font=("Segoe UI", font_size), fill=text_color, justify="center", width=max(40, int(node_box_w - 10)))
        if show_selection_box and getattr(node, "key", None) in selected_node_keys:
            canvas.create_rectangle(x0 - 4, y0 - 4, x1 + 4, y1 + 4, outline=selection_box_color, width=2)
        node_key = getattr(node, "key", None)
        node_bounds[node_key] = (x0, y0, x1, y1)
        node_centers[node_key] = (node_x, node_bus_y)
        bounds.append((x0, y0, x1, y1))
        if node_tag_name_fn is not None and node_key is not None:
            tag_name = node_tag_name_fn(node_key)
            for shape_id in shape_ids:
                canvas.addtag_withtag(tag_name, shape_id)
            canvas.addtag_withtag(tag_name, text_id)
    group_regions = []
    if show_groups and groups:
        label_bounds = {}
        for node in nodes:
            if is_callout_fn(node):
                continue
            bounds_entry = node_bounds.get(getattr(node, "key", None))
            if bounds_entry:
                label_bounds[getattr(node, "label", "")] = bounds_entry
        group_regions = draw_group_overlays(canvas, label_bounds, groups, zoom=scale)
    if bounds:
        min_x0 = min(b[0] for b in bounds) - 40
        min_y0 = min(b[1] for b in bounds) - 40
        max_x1 = max(b[2] for b in bounds) + 40
        max_y1 = max(b[3] for b in bounds) + 40
        canvas.configure(scrollregion=(min_x0, min_y0, max_x1, max_y1))
    cannect_nodes = [
        {"node": getattr(node, "key"), "bus": getattr(node, "bus_index", 0), "kind": "inject" if getattr(node, "category", "") == "cannect_inject" else "direct"}
        for node in nodes
        if is_swyft_node_fn(node)
    ]
    filtered_can_links = can_bus_links if show_can else []
    filtered_device_links = device_links if show_can else []
    filtered_cannect_nodes = cannect_nodes if show_can else []
    if ethernet_links or filtered_can_links or filtered_device_links or filtered_cannect_nodes:
        draw_links(
            canvas,
            node_centers,
            node_bounds,
            bus_ys_list,
            ethernet_links,
            filtered_can_links,
            filtered_device_links,
            filtered_cannect_nodes,
            ethernet_ports=ethernet_ports,
            can_ports=can_ports,
        )
    if show_power:
        for a_key, b_key in power_links:
            if a_key not in node_centers or b_key not in node_centers:
                continue
            a_bounds = node_bounds.get(a_key)
            b_bounds = node_bounds.get(b_key)
            ax, ay = ((a_bounds[0] + a_bounds[2]) / 2.0, (a_bounds[1] + a_bounds[3]) / 2.0) if a_bounds else node_centers[a_key]
            bx, by = ((b_bounds[0] + b_bounds[2]) / 2.0, (b_bounds[1] + b_bounds[3]) / 2.0) if b_bounds else node_centers[b_key]
            canvas.create_line(ax, ay, bx, by, width=link_line_width, fill=power_line_color)
    if show_virtual:
        for host_key, attach_key in attachment_links:
            if host_key not in node_centers or attach_key not in node_centers:
                continue
            host_bounds = node_bounds.get(host_key)
            attach_bounds = node_bounds.get(attach_key)
            hx, hy = ((host_bounds[0] + host_bounds[2]) / 2.0, (host_bounds[1] + host_bounds[3]) / 2.0) if host_bounds else node_centers[host_key]
            ax, ay = ((attach_bounds[0] + attach_bounds[2]) / 2.0, (attach_bounds[1] + attach_bounds[3]) / 2.0) if attach_bounds else node_centers[attach_key]
            canvas.create_line(hx, hy, ax, ay, width=link_line_width, fill=attach_line_color, dash=link_dash)
        for a, b in ethernet_links:
            if a not in ethernet_ports or b not in ethernet_ports or a not in node_centers or b not in node_centers:
                continue
            ax, _ = node_centers[a]
            bx, _ = node_centers[b]
            ports_a = ethernet_ports[a]
            ports_b = ethernet_ports[b]
            pa = ports_a["in"] if ("in" in ports_a and "out" in ports_a and bx < ax) else (ports_a.get("out") or ports_a.get("in"))
            pb = ports_b["in"] if ("in" in ports_b and "out" in ports_b and ax < bx) else (ports_b.get("out") or ports_b.get("in"))
            if pa and pb:
                canvas.create_line(pa[0], pa[1], pb[0], pb[1], width=2, fill="#1c6ba8", dash=(6, 4))
    if show_dio:
        for robo_key, dev_key in dio_links:
            if robo_key not in node_centers or dev_key not in node_centers:
                continue
            robo_bounds = node_bounds.get(robo_key)
            dev_bounds = node_bounds.get(dev_key)
            rx, ry = ((robo_bounds[0] + robo_bounds[2]) / 2.0, robo_bounds[1]) if robo_bounds else node_centers[robo_key]
            dx, dy = ((dev_bounds[0] + dev_bounds[2]) / 2.0, dev_bounds[1]) if dev_bounds else node_centers[dev_key]
            canvas.create_line(rx, ry, dx, dy, width=link_line_width, fill=dio_line_color, dash=link_dash)
    return {
        "node_bounds": node_bounds,
        "node_centers": node_centers,
        "group_overlay_regions": group_regions,
        "ethernet_ports": ethernet_ports,
        "can_ports": can_ports,
    }
