"""
NAME
    tools.common.evidence_fusion - Isolated evidence-fusion core package.

DESCRIPTION
    Hosts the additive evidence-ingestion core used by future fusion
    evaluators, offline replay, and regression fixtures. This package is kept
    independent from UI, transport, and roboRIO-specific code so it can be
    adopted or discarded cleanly.
"""

from tools.common.evidence_fusion.api import (
    drain_evaluation_budget,
    get_current_snapshot,
    get_runtime_stats,
    reset_runtime_state,
    submit_evidence_block,
)

__all__ = [
    "drain_evaluation_budget",
    "get_current_snapshot",
    "get_runtime_stats",
    "reset_runtime_state",
    "submit_evidence_block",
]
