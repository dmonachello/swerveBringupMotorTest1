from __future__ import annotations

"""
NAME
    topology_render.py - Shared topology rendering helpers.

SYNOPSIS
    from tools.common.topology_render import shape_kind_for_category

DESCRIPTION
    Centralizes category-to-shape and vendor color mapping so the topology
    editor and HTML visualizations stay consistent.
"""

from typing import Iterable, List

# Constants (categories).
CATEGORY_ANALYZER = "analyzer"
CATEGORY_CANNECT_INJECT = "cannect_inject"
CATEGORY_CANNECT_DIRECT = "cannect_direct"

# Constants (vendor keys).
VENDOR_ANALYZER = "ANALYZER"
DEVICE_TYPE_ANALYZER = "ANALYZER"


def shape_kind_for_category(category: str) -> str:
    """
    NAME
        shape_kind_for_category - Map a category to a shape kind.
    """
    cat = (category or "").lower()
    if cat in ("neos", "neo550s", "flexes", "krakens", "falcons"):
        return "motor"
    if cat in ("cancoders", "pigeon"):
        return "sensor"
    if cat in ("pdh", "pdp"):
        return "power"
    if cat in ("roborio", CATEGORY_CANNECT_INJECT, CATEGORY_CANNECT_DIRECT):
        return "controller"
    if cat == CATEGORY_ANALYZER:
        return "sensor"
    if cat in ("candles",):
        return "misc"
    if cat == "devices":
        return "misc"
    return "misc"


def vendor_key_for_category(category: str, vendor_override: str = "") -> str:
    """
    NAME
        vendor_key_for_category - Normalize vendor key for a category.
    """
    vendor = (vendor_override or "").strip().upper().replace(" ", "")
    if vendor:
        return vendor
    cat = (category or "").lower()
    if cat in ("neos", "neo550s", "flexes", "pdh"):
        return "REV"
    if cat in ("krakens", "falcons", "cancoders", "candles", "pdp", "pigeon"):
        return "CTRE"
    if cat in ("roborio",):
        return "NI"
    if cat in (CATEGORY_CANNECT_INJECT, CATEGORY_CANNECT_DIRECT):
        return "SWYFT"
    if cat == CATEGORY_ANALYZER:
        return VENDOR_ANALYZER
    return ""


def device_type_key_for_category(category: str, device_type_override: str = "") -> str:
    """
    NAME
        device_type_key_for_category - Normalize device type key for a category.
    """
    cat = (category or "").lower()
    if cat in ("neos", "neo550s", "flexes", "krakens", "falcons"):
        return "MOTORCONTROLLER"
    if cat in ("cancoders",):
        return "ENCODER"
    if cat in ("pigeon",):
        return "GYROSENSOR"
    if cat in ("pdh", "pdp"):
        return "POWERDISTRIBUTIONMODULE"
    if cat in ("candles",):
        return "MISCELLANEOUS"
    if cat in ("roborio",):
        return "ROBOTCONTROLLER"
    if cat in (CATEGORY_CANNECT_INJECT, CATEGORY_CANNECT_DIRECT):
        return "MISCELLANEOUS"
    if cat == CATEGORY_ANALYZER:
        return DEVICE_TYPE_ANALYZER
    if cat == "devices":
        override = (device_type_override or "").strip().upper().replace(" ", "")
        return override or "UNKNOWN"
    return "UNKNOWN"


def fill_color_for_vendor(vendor: str) -> str:
    """
    NAME
        fill_color_for_vendor - Resolve fill color for a vendor key.
    """
    palette = {
        "CTRE": "#b7e1b2",
        "REV": "#ffd5a6",
        "KAUAILABS": "#bfe7ff",
        "PLAYINGWITHFUSION": "#c8f2c3",
        "ANDYMARK": "#c9d2ff",
        "NI": "#e7e7e7",
        "SWYFT": "#e0d7ff",
        VENDOR_ANALYZER: "#cbd5f5",
    }
    return palette.get(vendor, "#f7f7f7")


def outline_color_for_vendor(vendor: str) -> str:
    """
    NAME
        outline_color_for_vendor - Resolve outline color for a vendor key.
    """
    palette = {
        "CTRE": "#1d6b1a",
        "REV": "#b26200",
        "KAUAILABS": "#1c6ba8",
        "PLAYINGWITHFUSION": "#2f7a2f",
        "ANDYMARK": "#3b4aa0",
        "NI": "#6a6a6a",
        "SWYFT": "#5b4aa0",
        VENDOR_ANALYZER: "#3b4aa0",
    }
    return palette.get(vendor, "#222222")


def text_color_for_fill(fill: str) -> str:
    """
    NAME
        text_color_for_fill - Choose a readable text color for a fill color.
    """
    if not fill.startswith("#") or len(fill) != 7:
        return "#111111"
    try:
        r = int(fill[1:3], 16)
        g = int(fill[3:5], 16)
        b = int(fill[5:7], 16)
    except Exception:
        return "#111111"
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "#111111" if luminance > 150 else "#ffffff"


def _svg_polygon(points: Iterable[float], fill: str, outline: str, width: int, dashed: bool) -> str:
    pts = " ".join(f"{p:.1f}" for p in points)
    dash = ' stroke-dasharray="4,3"' if dashed else ""
    return (
        f'<polygon points="{pts}" fill="{fill}" stroke="{outline}" stroke-width="{width}"{dash}/>'
    )


def svg_shape_for_kind(
    kind: str,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    fill: str,
    outline: str,
    width: int = 2,
    dashed: bool = False,
) -> str:
    """
    NAME
        svg_shape_for_kind - Draw a device shape as SVG.
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
        return _svg_polygon(points, fill, outline, width, dashed)
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
        return _svg_polygon(points, fill, outline, width, dashed)
    if kind == "power":
        xc = (x0 + x1) / 2.0
        yc = (y0 + y1) / 2.0
        points = [xc, y0, x1, yc, xc, y1, x0, yc]
        return _svg_polygon(points, fill, outline, width, dashed)
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
        return _svg_polygon(points, fill, outline, width, dashed)
    dash = ' stroke-dasharray="4,3"' if dashed else ""
    return (
        f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{(x1 - x0):.1f}" height="{(y1 - y0):.1f}" '
        f'rx="6" ry="6" fill="{fill}" stroke="{outline}" stroke-width="{width}"{dash}/>'
    )
