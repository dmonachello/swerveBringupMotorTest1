from __future__ import annotations

"""
NAME
    paths.py - Repository path helpers for tooling.

SYNOPSIS
    from tools.common.paths import repo_root, profiles_canonical_path

DESCRIPTION
    Provides stable, centralized path resolution for shared config files
    without embedding repeated Path(__file__).resolve() logic throughout
    the tools.
"""

from pathlib import Path


def repo_root() -> Path:
    """
    NAME
        repo_root - Resolve the repository root directory.

    RETURNS
        Path to the repository root.
    """
    return Path(__file__).resolve().parents[2]


def profiles_canonical_path() -> Path:
    """
    NAME
        profiles_canonical_path - Path to the unified deploy bringup_system.json.
    """
    return profiles_deploy_path()


def profiles_deploy_path() -> Path:
    """
    NAME
        profiles_deploy_path - Path to src/main/deploy/bringup_system.json.
    """
    return repo_root() / "src" / "main" / "deploy" / "bringup_system.json"


def legacy_profiles_canonical_path() -> Path:
    """
    NAME
        legacy_profiles_canonical_path - Path to data/bringup_profiles.json.
    """
    # LEGACY (remove after v3 unified file adoption).
    return repo_root() / "data" / "bringup_profiles.json"


def legacy_profiles_deploy_path() -> Path:
    """
    NAME
        legacy_profiles_deploy_path - Path to src/main/deploy/bringup_profiles.json.
    """
    # LEGACY (remove after v3 unified file adoption).
    return repo_root() / "src" / "main" / "deploy" / "bringup_profiles.json"


def tests_deploy_path() -> Path:
    """
    NAME
        tests_deploy_path - Path to src/main/deploy/bringup_tests.json.
    """
    return repo_root() / "src" / "main" / "deploy" / "bringup_tests.json"


def bindings_deploy_path() -> Path:
    """
    NAME
        bindings_deploy_path - Path to the unified config file that owns bindings.
    """
    return profiles_deploy_path()


def can_mappings_path() -> Path:
    """
    NAME
        can_mappings_path - Path to src/main/deploy/can_mappings.json.
    """
    return repo_root() / "src" / "main" / "deploy" / "can_mappings.json"


def test_templates_dir() -> Path:
    """
    NAME
        test_templates_dir - Path to tools/test_template_wizard/test_templates.
    """
    return repo_root() / "tools" / "test_template_wizard" / "test_templates"


def logs_dir() -> Path:
    """
    NAME
        logs_dir - Default logs directory for tools.
    """
    return repo_root() / "tools" / "can_nt" / "logs"
