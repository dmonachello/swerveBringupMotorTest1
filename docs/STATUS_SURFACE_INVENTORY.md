# Status Surface Inventory

> AUTO-GENERATED FILE. Do not modify; changes will be lost on regeneration.

## Purpose

Inventory canonical status-coded definitions and unstructured status/error string surfaces across Python and Java.

## Summary

- Generated At (UTC): `2026-04-22T18:00:15.302637+00:00`
- Canonical Python status message entries: `36`
- Unstructured Python candidates: `1607`
- Unstructured Java text candidates: `503`
- Java ack/status literal candidates: `0`

## Top Canonical Python Entries

- `tools\can_nt\status\cli_parser_codes.py:15` SS__CLI_PARSER__INVALID_SYNTAX: Invalid command syntax.
- `tools\can_nt\status\cli_parser_codes.py:16` SS__CLI_PARSER__UNKNOWN_COMMAND: Unknown command.
- `tools\can_nt\status\cli_parser_codes.py:17` SS__CLI_PARSER__MISSING_ARGUMENT: Missing required argument: {arg}.
- `tools\can_nt\status\cli_parser_codes.py:18` SS__CLI_PARSER__INVALID_FLAG: Invalid flag: {flag}.
- `tools\can_nt\status\cli_validator_codes.py:14` SS__CLI_VALIDATOR__INVALID_VALUE: Invalid value: {value}.
- `tools\can_nt\status\cli_validator_codes.py:15` SS__CLI_VALIDATOR__OUT_OF_RANGE: Value out of range: {value}.
- `tools\can_nt\status\cli_validator_codes.py:16` SS__CLI_VALIDATOR__REQUIRED: Required value missing: {field}.
- `tools\can_nt\status\config_codes.py:20` SS__CONFIG__NOT_LOADED: Config not loaded.
- `tools\can_nt\status\config_codes.py:21` SS__CONFIG__INVALID: Config invalid: {detail}.
- `tools\can_nt\status\config_codes.py:22` SS__CONFIG__SAVED: Config saved.
- `tools\can_nt\status\config_codes.py:23` SS__CONFIG__MERGED: Config merged.
- `tools\can_nt\status\config_codes.py:24` SS__CONFIG__IMPORTED: Config imported.
- `tools\can_nt\status\config_codes.py:25` SS__CONFIG__VALID: Config valid.
- `tools\can_nt\status\config_codes.py:26` SS__CONFIG__PROFILE_REQUIRED: Active profile required.
- `tools\can_nt\status\config_codes.py:27` SS__CONFIG__DUPLICATE_LABEL: Duplicate label: {label}.
- `tools\can_nt\status\config_codes.py:28` SS__CONFIG__MISSING_DEVICE: Missing device: {device}.
- `tools\can_nt\status\device_codes.py:14` SS__DEVICE__NOT_FOUND: Device not found: {device}.
- `tools\can_nt\status\device_codes.py:15` SS__DEVICE__NOT_DEFINED: Device not defined: {device}.
- `tools\can_nt\status\device_codes.py:16` SS__DEVICE__INVALID_FIELD: Invalid device field: {field}.
- `tools\can_nt\status\executor_codes.py:16` SS__NORMAL: Success.

## Top Unstructured Python Candidates

- `tools\add_journal_note.py:39` parser.add_argument("--text", required=True, help="Note content.")
- `tools\add_tbd_note.py:24` parser.add_argument("--text", required=True, help="TBD note text.")
- `tools\add_tbd_note.py:42` print("ERROR: text is required.")
- `tools\bump_version.py:60` print(f"ERROR: {message}")
- `tools\bump_version.py:79` raise ValueError(f"unknown app '{target}'")
- `tools\bump_version.py:102` return _print_error(f"invalid semantic version '{version}'")
- `tools\bump_version.py:122` return _print_error(f"invalid version field '{field}'")
- `tools\bump_version.py:145` return _print_error(f"invalid version field '{field}'")
- `tools\bump_version.py:149` return _print_error("invalid version value")
- `tools\bump_version.py:151` return _print_error("invalid version value")
- `tools\bump_version.py:189` return _print_error("missing required argument <app|all>")
- `tools\bump_version.py:193` return _print_error("missing required argument <app|all> or <major|minor|patch>")
- `tools\bump_version.py:197` return _print_error("missing required argument <app|all> or <X.Y.Z>")
- `tools\bump_version.py:201` return _print_error("missing required argument <app|all> or <value>")
- `tools\gen_cli_cheatsheet_pdf.py:42` "    Required so relative paths resolve consistently.",
- `tools\gen_cli_cheatsheet_pdf.py:57` "  [--list-ports] [--no-can] [--rio RIO] [--no-nt] [--timeout TIMEOUT]\n"
- `tools\gen_cli_cheatsheet_pdf.py:62` "  [--console-timeout CONSOLE_TIMEOUT] [--console-rate CONSOLE_RATE]\n"
- `tools\gen_cli_cheatsheet_pdf.py:67` "  [--list-keys] [--dump-nt DUMP_NT] [--publish-unknown] [--dump-profile DUMP_PROFILE]\n"
- `tools\gen_cli_cheatsheet_pdf.py:69` "  [--dump-profile-include-unknown] [--dump-api-inventory DUMP_API_INVENTORY]\n"
- `tools\gen_cli_cheatsheet_pdf.py:157` "       What it does: Highlights new/missing device pairs or rate changes between runs.",

## Top Unstructured Java Candidates

- `src\main\java\frc\robot\BridgeGroupManager.java:287` *   Group instance or null when not found.
- `src\main\java\frc\robot\BridgeGroupManager.java:315` *   True when created, false if invalid or already exists.
- `src\main\java\frc\robot\BridgeGroupManager.java:334` *   True when removed, false if missing.
- `src\main\java\frc\robot\BridgeGroupManager.java:413` *   True when removed, false if missing.
- `src\main\java\frc\robot\BridgeGroupManager.java:436` *   True when updated, false if missing.
- `src\main\java\frc\robot\BridgeGroupManager.java:460` *   True when toggled, false if missing.
- `src\main\java\frc\robot\BridgeGroupManager.java:483` *   True when cleared, false if missing.
- `src\main\java\frc\robot\BridgeGroupManager.java:505` *   True when binding added, false if group or kind invalid.
- `src\main\java\frc\robot\BridgeUiCommandHandler.java:103` private static final String WARNING_WRAPPED = "WARNING: device list wrapped to first entry.";
- `src\main\java\frc\robot\BridgeUiCommandHandler.java:104` private static final String WARNING_NO_ELIGIBLE_ADD = "WARNING: no eligible next device for active add.";
- `src\main\java\frc\robot\BridgeUiCommandHandler.java:105` private static final String WARNING_NO_ELIGIBLE_NEXT = "WARNING: no eligible next device for active next.";
- `src\main\java\frc\robot\BridgeUiCommandHandler.java:106` private static final String WARNING_DUPLICATE_PREFIX = "WARNING: device already in active-group: ";
- `src\main\java\frc\robot\BridgeUiCommandHandler.java:107` private static final String WARNING_SKIPPED_PREFIX = "WARNING: skipped not-ready device: ";
- `src\main\java\frc\robot\BridgeUiCommandHandler.java:109` "WARNING: command rejected while TEST_RUNNING.";
- `src\main\java\frc\robot\BridgeUiCommandHandler.java:112` private static final String MESSAGE_ACTIVE_NOT_FOUND = "Active group not found.";
- `src\main\java\frc\robot\BridgeUiCommandHandler.java:116` private static final String JSON_KEY_OK = "ok";
- `src\main\java\frc\robot\BridgeUiCommandHandler.java:163` private static final String TEXT_DEVICE_NOT_FOUND = "Device: (not found)";
- `src\main\java\frc\robot\BridgeUiCommandHandler.java:194` private static final String TEXT_PROFILE_ACTIVATE_FAIL = "Profile activation failed.";
- `src\main\java\frc\robot\BridgeUiCommandHandler.java:196` private static final String TEXT_PROFILES_RELOAD_FAILED = "Profiles reload failed: %s";
- `src\main\java\frc\robot\BridgeUiCommandHandler.java:198` private static final String TEXT_PROFILES_APPLY_FAILED = "Profiles apply failed.";

## Java ACK Status Literal Candidates


## Output Artifacts

- `tools/status_codes/reports/status_surface_inventory.json`
- `docs/STATUS_SURFACE_INVENTORY.md`

