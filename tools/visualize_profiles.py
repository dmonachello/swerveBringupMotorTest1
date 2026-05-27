from __future__ import annotations

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

"""
NAME
    visualize_profiles.py - Render bringup_system.json into an HTML diagram.

SYNOPSIS
    python tools\\visualize_profiles.py [--input PATH] [--output PATH]

DESCRIPTION
    Generates a self-contained HTML report with per-profile CAN ID diagrams,
    counts, and tables. Intended for quick visual inspection of the shared
    bringup profiles database.
"""

import argparse
import html
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from tools.common.cli_helpers import add_input_arg, add_output_arg
from tools.common.json_io import read_json
from tools.common.profile_constants import (
    INTERFACE_CAN,
    KEY_DEFAULT_PROFILE,
    KEY_DEVICE_TYPE,
    KEY_DEVICES,
    KEY_ID,
    KEY_INTERFACE,
    KEY_LABEL,
    KEY_MANUFACTURER,
    KEY_MODEL,
    KEY_PROFILE_DEVICES,
    KEY_PROFILES,
    KEY_TAGS,
    KEY_TYPE,
    KEY_VENDOR,
    get_device_interface,
)
from tools.common.topology_render import (
    fill_color_for_vendor,
    outline_color_for_vendor,
    shape_kind_for_category,
    svg_shape_for_kind,
    text_color_for_fill,
    vendor_key_for_category,
)

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Visualize bringup profiles.")
    add_input_arg(
        parser,
        default=str(Path("src") / "main" / "deploy" / "bringup_system.json"),
        help_text="Path to bringup_system.json",
    )
    add_output_arg(
        parser,
        default=str(Path("docs") / "bringup_system_diagram.html"),
        help_text="Output HTML path",
    )
    return parser.parse_args()


def _escape(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _collect_devices(
    profile: Dict[str, Any],
    registry: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    devices: List[Dict[str, Any]] = []
    labels = profile.get(KEY_PROFILE_DEVICES)
    if not isinstance(labels, list):
        return devices
    for label in labels:
        if not isinstance(label, str):
            continue
        entry = registry.get(label.strip().lower())
        if entry is None:
            continue
        if get_device_interface(entry) != INTERFACE_CAN:
            continue
        can_id = entry.get(KEY_ID)
        if not isinstance(can_id, int):
            continue
        vendor = _resolve_vendor(entry)
        dtype = _resolve_type(entry)
        category = _resolve_category(entry)
        devices.append(
            {
                "id": can_id,
                "label": entry.get(KEY_LABEL) or label,
                "vendor": vendor,
                "type": dtype,
                "category": category,
                "tags": entry.get(KEY_TAGS) or [],
            }
        )
    return devices


def _build_registry(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    registry: Dict[str, Dict[str, Any]] = {}
    devices = payload.get(KEY_DEVICES)
    if not isinstance(devices, list):
        return registry
    for entry in devices:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get(KEY_LABEL, "")).strip()
        if not label:
            continue
        registry[label.lower()] = entry
    return registry


def _resolve_vendor(entry: Dict[str, Any]) -> str:
    vendor = entry.get(KEY_VENDOR)
    if isinstance(vendor, str) and vendor:
        return vendor
    manufacturer = entry.get(KEY_MANUFACTURER)
    if manufacturer == 5:
        return "REV"
    if manufacturer == 4:
        return "CTRE"
    if manufacturer == 1:
        return "NI"
    return "Unknown"


def _resolve_type(entry: Dict[str, Any]) -> str:
    dtype = entry.get(KEY_TYPE)
    if isinstance(dtype, str) and dtype:
        return dtype
    model = entry.get(KEY_MODEL)
    if isinstance(model, str) and model:
        return model
    return "Unknown"


def _resolve_category(entry: Dict[str, Any]) -> str:
    manufacturer = entry.get(KEY_MANUFACTURER)
    device_type = entry.get(KEY_DEVICE_TYPE)
    model = str(entry.get(KEY_MODEL, "")).lower()
    dtype = str(entry.get(KEY_TYPE, "")).lower()
    if manufacturer == 5 and device_type == 2:
        if "550" in model:
            return "neo550s"
        if "vortex" in model or "flex" in model:
            return "flexes"
        return "neos"
    if manufacturer == 4 and device_type == 2:
        if "falcon" in model:
            return "falcons"
        return "krakens"
    if manufacturer == 4 and device_type == 7:
        return "cancoders"
    if manufacturer == 4 and device_type == 10:
        return "candles"
    if manufacturer == 5 and device_type == 8:
        return "pdh"
    if manufacturer == 4 and device_type == 8:
        return "pdp"
    if manufacturer == 4 and device_type == 4:
        return "pigeon"
    if manufacturer == 1 and device_type == 1:
        return "roborio"
    if dtype:
        return dtype
    return "devices"


def _svg_for_profile(devices: List[Dict[str, Any]]) -> str:
    width = 980
    x0 = 40
    x1 = 940
    label_width = 260
    label_height = 16
    lane_height = 18
    top_margin = 16
    padding = 6

    by_id: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for dev in devices:
        if dev["id"] is None or dev["id"] < 0:
            continue
        by_id[int(dev["id"])].append(dev)

    items: List[Tuple[float, str, int]] = []
    for can_id, entries in sorted(by_id.items()):
        cx = x0 + (x1 - x0) * (can_id / 62.0)
        for dev in entries:
            label = f"{dev['label']} ({dev['vendor']} {dev['type']} {can_id})"
            items.append((cx, label, can_id))

    lanes_end: List[float] = []
    lane_assignments: List[Tuple[float, str, int, int]] = []
    for cx, label, can_id in sorted(items, key=lambda v: (v[0], v[1])):
        text_x = cx + 10
        lane_idx = None
        for i, end_x in enumerate(lanes_end):
            if text_x > end_x + padding:
                lane_idx = i
                lanes_end[i] = text_x + label_width
                break
        if lane_idx is None:
            lane_idx = len(lanes_end)
            lanes_end.append(text_x + label_width)
        lane_assignments.append((cx, label, can_id, lane_idx))

    lane_count = max(1, len(lanes_end))
    line_y = top_margin + (lane_count * lane_height) + 16
    height = line_y + 70
    line = f'<line x1="{x0}" y1="{line_y}" x2="{x1}" y2="{line_y}" stroke="#1f2937" stroke-width="2"/>'

    circles = []
    labels = []
    leaders = []
    for cx, label, can_id, lane_idx in lane_assignments:
        text_x = cx + 10
        label_y = top_margin + (lane_idx * lane_height)
        text_y = label_y + 11
        circles.append(
            f'<circle cx="{cx:.1f}" cy="{line_y:.1f}" r="6" fill="#2563eb"/>'
        )
        leaders.append(
            f'<line x1="{cx:.1f}" y1="{line_y - 2:.1f}" x2="{text_x - 2:.1f}" y2="{label_y + 8:.1f}" stroke="#cbd5e1" stroke-width="1"/>'
        )
        labels.append(
            f'<rect x="{text_x:.1f}" y="{label_y:.1f}" width="{label_width}" height="{label_height}" '
            f'fill="#ffffff" opacity="0.85" rx="2" ry="2"/>'
        )
        labels.append(
            f'<text x="{text_x + 4:.1f}" y="{text_y:.1f}" font-size="10" fill="#111827">{_escape(label)}</text>'
        )

    ticks = []
    for tick in range(0, 63, 10):
        tx = x0 + (x1 - x0) * (tick / 62.0)
        ticks.append(
            f'<text x="{tx:.1f}" y="{line_y + 24:.1f}" font-size="10" fill="#6b7280">{tick}</text>'
        )

    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="CAN ID map">'
        + line
        + "".join(ticks)
        + "".join(leaders)
        + "".join(circles)
        + "".join(labels)
        + "</svg>"
    )


def _svg_for_topology(diagram: Dict[str, Any]) -> str:
    """
    NAME
        _svg_for_topology - Render a topology diagram from editor metadata.
    """
    box_w = 140.0
    box_h = 60.0
    margin = 40.0

    zoom = float(diagram.get("zoom", 1.0))
    pan_y = float(diagram.get("panY", 0.0))
    bus_count = int(diagram.get("busCount", 1) or 1)
    bus_spacing = float(diagram.get("busSpacing", 160.0))

    bus_offsets = diagram.get("busOffsets")
    if isinstance(bus_offsets, list) and bus_offsets:
        offsets = [float(v) for v in bus_offsets]
    else:
        offsets = [i * bus_spacing for i in range(bus_count)]

    bus_lefts = diagram.get("busLefts")
    if not isinstance(bus_lefts, list) or not bus_lefts:
        bus_lefts = [40.0] * len(offsets)
    bus_rights = diagram.get("busRights")
    if not isinstance(bus_rights, list) or not bus_rights:
        max_node_x = max((float(n.get("x", 0.0)) for n in diagram.get("nodes", []) or []), default=800.0)
        bus_rights = [max_node_x + 200.0] * len(offsets)

    nodes = diagram.get("nodes") or []
    callouts = diagram.get("callouts") or []

    node_positions: Dict[int, Tuple[float, float, float, float]] = {}
    min_x = min(bus_lefts) if bus_lefts else 0.0
    max_x = max(bus_rights) if bus_rights else 800.0
    min_y = min(offsets) if offsets else 0.0
    max_y = max(offsets) if offsets else 0.0

    for node in nodes:
        try:
            x = float(node.get("x", 0.0))
            node_scale = max(0.6, min(2.0, float(node.get("scale", 1.0))))
            row = int(node.get("row", 0))
            bus_index = int(node.get("bus", 0))
            free_y = node.get("freeY")
            free_rel = bool(node.get("freeYRelative", False))
        except Exception:
            continue
        bus_index = min(max(bus_index, 0), max(len(offsets) - 1, 0))
        bus_y = offsets[bus_index]
        if free_y is not None:
            try:
                free_val = float(free_y)
            except Exception:
                free_val = 0.0
            center_y = (bus_y + free_val) if free_rel else free_val
        else:
            if row == 1:
                center_y = bus_y + 30.0 + (box_h * node_scale / 2.0)
            else:
                center_y = bus_y - 30.0 - (box_h * node_scale / 2.0)

        half_w = (box_w * node_scale) / 2.0
        half_h = (box_h * node_scale) / 2.0
        min_x = min(min_x, x - half_w)
        max_x = max(max_x, x + half_w)
        min_y = min(min_y, center_y - half_h)
        max_y = max(max_y, center_y + half_h)
        key = node.get("key")
        if isinstance(key, int):
            node_positions[key] = (x, center_y, half_w, half_h)

    for callout in callouts:
        try:
            x = float(callout.get("x", 0.0))
            y = float(callout.get("y", 0.0))
        except Exception:
            continue
        min_x = min(min_x, x - 90.0)
        max_x = max(max_x, x + 220.0)
        min_y = min(min_y, y - 30.0)
        max_y = max(max_y, y + 30.0)

    min_y = min_y + pan_y
    max_y = max_y + pan_y
    shift_x = margin - min_x
    shift_y = margin - min_y

    width = (max_x - min_x + margin * 2.0) * zoom
    height = (max_y - min_y + margin * 2.0) * zoom

    bus_lines = []
    bus_connectors = []
    for idx, offset in enumerate(offsets):
        bus_y = (offset + shift_y + pan_y) * zoom
        left = (float(bus_lefts[idx]) + shift_x) * zoom
        right = (float(bus_rights[idx]) + shift_x) * zoom
        if idx % 2 == 0:
            start_x, end_x = left, right
        else:
            start_x, end_x = right, left
        bus_lines.append(
            f'<line x1="{start_x:.1f}" y1="{bus_y:.1f}" x2="{end_x:.1f}" y2="{bus_y:.1f}" '
            f'stroke="#1f2937" stroke-width="3" stroke-linecap="round"/>'
        )
        if idx + 1 < len(offsets):
            next_y = (offsets[idx + 1] + shift_y + pan_y) * zoom
            turn_radius = max(8.0, 18.0 * zoom)
            offset_x = turn_radius if idx % 2 == 0 else -turn_radius
            bus_connectors.append(
                f'<path d="M {end_x:.1f} {bus_y:.1f} '
                f'C {end_x + offset_x:.1f} {bus_y + turn_radius:.1f}, '
                f'{end_x + offset_x:.1f} {next_y - turn_radius:.1f}, '
                f'{end_x:.1f} {next_y:.1f}" '
                f'stroke="#1f2937" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            )

    node_shapes = []
    node_labels = []
    node_leaders = []
    for node in nodes:
        vendor = vendor_key_for_category(node.get("category", ""), node.get("vendor", ""))
        fill = fill_color_for_vendor(vendor)
        stroke = outline_color_for_vendor(vendor)
        dashed = bool(node.get("nodeType") == "diagram" and node.get("profileVisible") is False)
        try:
            x = float(node.get("x", 0.0))
            node_scale = max(0.6, min(2.0, float(node.get("scale", 1.0))))
            row = int(node.get("row", 0))
            bus_index = int(node.get("bus", 0))
            free_y = node.get("freeY")
            free_rel = bool(node.get("freeYRelative", False))
        except Exception:
            continue
        bus_index = min(max(bus_index, 0), max(len(offsets) - 1, 0))
        bus_y = offsets[bus_index]
        if free_y is not None:
            try:
                free_val = float(free_y)
            except Exception:
                free_val = 0.0
            center_y = (bus_y + free_val) if free_rel else free_val
        else:
            if row == 1:
                center_y = bus_y + 30.0 + (box_h * node_scale / 2.0)
            else:
                center_y = bus_y - 30.0 - (box_h * node_scale / 2.0)

        half_w = (box_w * node_scale) / 2.0
        half_h = (box_h * node_scale) / 2.0
        x0 = (x - half_w + shift_x) * zoom
        y0 = (center_y - half_h + shift_y + pan_y) * zoom
        w = (half_w * 2.0) * zoom
        h = (half_h * 2.0) * zoom
        kind = shape_kind_for_category(node.get("category", ""))
        node_shapes.append(
            svg_shape_for_kind(
                kind,
                x0,
                y0,
                x0 + w,
                y0 + h,
                fill,
                stroke,
                width=2,
                dashed=dashed,
            )
        )
        node_id = node.get("id")
        label = node.get("label")
        if not label:
            if node_id is not None:
                try:
                    label = f"ID {int(node_id)}"
                except Exception:
                    label = node.get("category") or "diagram"
            else:
                label = node.get("category") or "diagram"
        line1 = _escape(str(label))
        line2 = ""
        if node_id is not None:
            try:
                if int(node_id) >= 0:
                    line2 = _escape(f"ID {int(node_id)}")
            except Exception:
                line2 = ""
        text_x = x0 + w / 2.0
        text_y = y0 + h / 2.0 - 4
        text_color = text_color_for_fill(fill)
        node_labels.append(
            f'<text x="{text_x:.1f}" y="{text_y:.1f}" text-anchor="middle" font-size="11" fill="{text_color}">{line1}</text>'
        )
        if line2:
            node_labels.append(
                f'<text x="{text_x:.1f}" y="{text_y + 14:.1f}" text-anchor="middle" font-size="10" fill="{text_color}">{line2}</text>'
            )
        bus_y_screen = (bus_y + shift_y + pan_y) * zoom
        if center_y < bus_y:
            line_start_y = y0 + h
        else:
            line_start_y = y0
        node_leaders.append(
            f'<line x1="{(x + shift_x) * zoom:.1f}" y1="{line_start_y:.1f}" '
            f'x2="{(x + shift_x) * zoom:.1f}" y2="{bus_y_screen:.1f}" stroke="#64748b" stroke-width="2"/>'
        )

    callout_shapes = []
    for callout in callouts:
        try:
            x = float(callout.get("x", 0.0))
            y = float(callout.get("y", 0.0))
            scale = max(0.6, min(2.0, float(callout.get("scale", 1.0))))
        except Exception:
            continue
        w = 180.0 * scale * zoom
        h = 50.0 * scale * zoom
        x0 = (x + shift_x) * zoom
        y0 = (y + shift_y + pan_y) * zoom
        callout_shapes.append(
            f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="8" ry="8" fill="#f1f5f9" stroke="#64748b" stroke-width="2"/>'
        )
        text = _escape(str(callout.get("text", "")))
        callout_shapes.append(
            f'<text x="{x0 + w / 2.0:.1f}" y="{y0 + h / 2.0 + 4:.1f}" '
            f'text-anchor="middle" font-size="11" fill="#0f172a">{text}</text>'
        )
        target_type = callout.get("targetType")
        if target_type == "bus":
            bus_index = int(callout.get("targetBus", 0) or 0)
            bus_index = min(max(bus_index, 0), max(len(offsets) - 1, 0))
            tx = x0 + w / 2.0
            ty = (offsets[bus_index] + shift_y + pan_y) * zoom
            callout_shapes.append(
                f'<line x1="{tx:.1f}" y1="{y0 + h:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" stroke="#94a3b8" stroke-width="2"/>'
            )
        elif target_type == "node":
            key = callout.get("targetNodeKey")
            if isinstance(key, int) and key in node_positions:
                nx, ny, _, _ = node_positions[key]
                tx = (nx + shift_x) * zoom
                ty = (ny + shift_y + pan_y) * zoom
                callout_shapes.append(
                    f'<line x1="{x0 + w / 2.0:.1f}" y1="{y0 + h:.1f}" '
                    f'x2="{tx:.1f}" y2="{ty:.1f}" stroke="#94a3b8" stroke-width="2"/>'
                )

    return (
        f'<svg viewBox="0 0 {width:.1f} {height:.1f}" role="img" aria-label="Topology diagram">'
        + "".join(bus_lines)
        + "".join(bus_connectors)
        + "".join(node_leaders)
        + "".join(callout_shapes)
        + "".join(node_shapes)
        + "".join(node_labels)
        + "</svg>"
    )


def _table_for_profile(devices: List[Dict[str, Any]]) -> str:
    rows = []
    for dev in sorted(devices, key=lambda d: (d["id"], d["vendor"], d["type"], d["label"])):
        rows.append(
            "<tr>"
            f"<td>{_escape(dev['id'])}</td>"
            f"<td>{_escape(dev['vendor'])}</td>"
            f"<td>{_escape(dev['type'])}</td>"
            f"<td>{_escape(dev['label'])}</td>"
            f"<td>{_escape(dev['category'])}</td>"
            f"<td>{_escape(', '.join(dev.get('tags', [])))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="6">(no devices)</td></tr>')
    return (
        "<table>"
        "<thead><tr><th>ID</th><th>Vendor</th><th>Type</th><th>Label</th><th>Category</th><th>Tags</th></tr></thead>"
        "<tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _html(payload: Dict[str, Any]) -> str:
    profiles = payload.get(KEY_PROFILES, {})
    diagram_profiles = (payload.get("diagram") or {}).get("profiles", {})
    data_version = payload.get("data_version", "")
    data_hash = payload.get("data_hash", "")
    registry = _build_registry(payload)
    cards = []
    for name in sorted(profiles.keys()):
        profile = profiles.get(name) or {}
        devices = _collect_devices(profile, registry)
        diagram = diagram_profiles.get(name) if isinstance(diagram_profiles, dict) else None
        if isinstance(diagram, dict):
            diagram_html = _svg_for_topology(diagram)
        else:
            diagram_html = _svg_for_profile(devices)
        counts: Dict[str, int] = defaultdict(int)
        for dev in devices:
            counts[dev["category"]] += 1
        count_line = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        cards.append(
            f"<section class=\"card\">"
            f"<h2>{_escape(name)}</h2>"
            f"<div class=\"meta\">devices: {len(devices)} | { _escape(count_line) }</div>"
            f"<div class=\"diagram\">{diagram_html}</div>"
            f"{_table_for_profile(devices)}"
            f"</section>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Bringup Profiles Diagram</title>
  <style>
    body {{
      font-family: "Segoe UI", Arial, sans-serif;
      background: #f8fafc;
      color: #0f172a;
      margin: 0;
      padding: 24px;
    }}
    h1 {{
      margin: 0 0 6px 0;
      font-size: 24px;
    }}
    .meta {{
      color: #475569;
      font-size: 13px;
      margin-bottom: 12px;
    }}
    .card {{
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 16px;
      margin: 16px 0;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }}
    .diagram {{
      margin: 8px 0 16px 0;
      background: #f1f5f9;
      border-radius: 8px;
      padding: 8px;
      overflow: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }}
    th, td {{
      border: 1px solid #e2e8f0;
      padding: 6px 8px;
      text-align: left;
    }}
    th {{
      background: #f1f5f9;
      font-weight: 600;
    }}
    tbody tr:nth-child(even) {{
      background: #f8fafc;
    }}
  </style>
</head>
<body>
  <h1>Bringup Profiles Diagram</h1>
  <div class="meta">data_version: {_escape(data_version)} | data_hash: {_escape(data_hash)}</div>
  {"".join(cards)}
</body>
</html>
"""


def main() -> int:
    args = _parse_args()
    path = Path(args.input)
    if not path.exists():
        print(f"ERROR: input not found: {path}")
        return 2
    payload = read_json(path)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_html(payload), encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
