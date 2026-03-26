"""
NAME
    bridge_cli_constants.py - Shared constants for the Bridge CLI.
"""

CLI_PARSER_CONST = {
    "legacy": "legacy",
    "ebnf": "ebnf",
    "strict_default": False,
    "arg_name": "cli_parser",
    "arg_default": None,
    "arg_help": "Select CLI parser implementation.",
    "arg_choices": ("legacy", "ebnf"),
}
