from __future__ import annotations

"""
NAME
    diagnostics - Shared diagnostics normalization helpers.
"""

from .normalize import normalize_device_attachments, summarize_attachment_metrics

__all__ = [
    "normalize_device_attachments",
    "summarize_attachment_metrics",
]

