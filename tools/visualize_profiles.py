from __future__ import annotations

"""
NAME
    visualize_profiles.py - Render bringup_profiles.json into an HTML diagram.

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

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Visualize bringup profiles.")
    add_input_arg(
        parser,
        default=str(Path("data") / "bringup_profiles.json"),
        help_text="Path to bringup_profiles.json",
    )
    add_output_arg(
        parser,
        default=str(Path("docs") / "bringup_profiles_diagram.html"),
        help_text="Output HTML path",
    )
    return parser.parse_args()


def _escape(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _collect_devices(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    devices: List[Dict[str, Any]] = []

    def add_list(category: str, vendor: str, dtype: str) -> None:
        for entry in profile.get(category, []) or []:
            if not isinstance(entry, dict):
                continue
            if "id" not in entry:
                continue
            devices.append(
                {
                    "id": int(entry.get("id")),
                    "label": entry.get("label") or f"{dtype} {entry.get('id')}",
                    "vendor": vendor,
                    "type": dtype,
                    "category": category,
                    "tags": entry.get("tags") or [],
                }
            )

    add_list("neos", "REV", "NEO")
    add_list("neo550s", "REV", "NEO 550")
    add_list("flexes", "REV", "FLEX")
    add_list("krakens", "CTRE", "KRAKEN")
    add_list("falcons", "CTRE", "FALCON")
    add_list("cancoders", "CTRE", "CANCoder")
    add_list("candles", "CTRE", "CANdle")

    for entry in profile.get("devices", []) or []:
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        devices.append(
            {
                "id": int(entry.get("id")),
                "label": entry.get("label") or f"Device {entry.get('id')}",
                "vendor": entry.get("vendor") or "Unknown",
                "type": entry.get("type") or "Unknown",
                "category": "devices",
                "tags": entry.get("tags") or [],
            }
        )

    for key, vendor, dtype in [
        ("pdh", "REV", "PDH"),
        ("pdp", "CTRE", "PDP"),
        ("pigeon", "CTRE", "Pigeon"),
        ("roborio", "NI", "roboRIO"),
    ]:
        entry = profile.get(key)
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        devices.append(
            {
                "id": int(entry.get("id")),
                "label": entry.get("label") or dtype,
                "vendor": vendor,
                "type": dtype,
                "category": key,
                "tags": entry.get("tags") or [],
            }
        )

    return devices


def _svg_for_profile(devices: List[Dict[str, Any]]) -> str:
    width = 980
    height = 220
    x0 = 40
    x1 = 940
    y = 70
    line = f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="#1f2937" stroke-width="2"/>'

    by_id: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for dev in devices:
        if dev["id"] is None or dev["id"] < 0:
            continue
        by_id[int(dev["id"])].append(dev)

    circles = []
    labels = []
    for can_id, entries in sorted(by_id.items()):
        cx = x0 + (x1 - x0) * (can_id / 62.0)
        for idx, dev in enumerate(entries):
            direction = -1 if idx % 2 == 0 else 1
            tier = idx // 2
            cy = y + direction * (18 + (tier * 16))
            circles.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="#2563eb"/>'
            )
            label = f"{dev['label']} ({dev['vendor']} {dev['type']} {can_id})"
            text_x = cx + 10
            text_y = cy + 4
            labels.append(
                f'<rect x="{text_x:.1f}" y="{text_y - 12:.1f}" width="260" height="16" fill="#ffffff" opacity="0.75"/>'
            )
            labels.append(
                f'<text x="{text_x:.1f}" y="{text_y:.1f}" font-size="10" fill="#111827">{_escape(label)}</text>'
            )

    ticks = []
    for tick in range(0, 63, 10):
        tx = x0 + (x1 - x0) * (tick / 62.0)
        ticks.append(
            f'<text x="{tx:.1f}" y="{y + 24}" font-size="10" fill="#6b7280">{tick}</text>'
        )

    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="CAN ID map">'
        + line
        + "".join(ticks)
        + "".join(circles)
        + "".join(labels)
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
    profiles = payload.get("profiles", {})
    data_version = payload.get("data_version", "")
    data_hash = payload.get("data_hash", "")
    cards = []
    for name in sorted(profiles.keys()):
        profile = profiles.get(name) or {}
        devices = _collect_devices(profile)
        counts: Dict[str, int] = defaultdict(int)
        for dev in devices:
            counts[dev["category"]] += 1
        count_line = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        cards.append(
            f"<section class=\"card\">"
            f"<h2>{_escape(name)}</h2>"
            f"<div class=\"meta\">devices: {len(devices)} | { _escape(count_line) }</div>"
            f"<div class=\"diagram\">{_svg_for_profile(devices)}</div>"
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
