from __future__ import annotations

"""
NAME
    cli_helpers.py - Small argparse helpers for tool CLIs.

SYNOPSIS
    from tools.common.cli_helpers import add_input_arg

DESCRIPTION
    Thin wrappers around argparse.add_argument to keep common CLI flags
    consistent without changing behavior.
"""

import argparse
from typing import Any, Optional


def add_input_arg(
    parser: argparse.ArgumentParser,
    *,
    default: Any,
    help_text: str,
    required: bool = False,
    arg: str = "--input",
) -> None:
    """
    NAME
        add_input_arg - Add a standard --input argument.
    """
    parser.add_argument(arg, default=default, help=help_text, required=required)


def add_output_arg(
    parser: argparse.ArgumentParser,
    *,
    default: Optional[Any],
    help_text: str,
    required: bool = False,
    arg: str = "--output",
) -> None:
    """
    NAME
        add_output_arg - Add a standard --output argument.
    """
    parser.add_argument(arg, default=default, help=help_text, required=required)


def add_path_arg(
    parser: argparse.ArgumentParser,
    *,
    default: Any,
    help_text: str,
    required: bool = False,
    arg: str = "--path",
) -> None:
    """
    NAME
        add_path_arg - Add a standard --path argument.
    """
    parser.add_argument(arg, default=default, help=help_text, required=required)
