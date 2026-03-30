from __future__ import annotations

"""
NAME
    config_store.py - Backwards-compatible alias to schema store.

SYNOPSIS
    from tools.config.config_store import ConfigStore

DESCRIPTION
    Re-exports the schema-aware store to keep older imports working.
    New code should import ConfigSchemaStore from schema_store.py.
"""

from tools.config.schema_store import (
    ConfigSchemaStore,
    ValidationIssue,
    ValidationResult,
)


ConfigStore = ConfigSchemaStore
