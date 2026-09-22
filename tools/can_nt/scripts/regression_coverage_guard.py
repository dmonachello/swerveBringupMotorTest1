from __future__ import annotations

"""
NAME
    regression_coverage_guard.py - Detect tests omitted from maintained suites.

SYNOPSIS
    python tools/can_nt/scripts/regression_coverage_guard.py

DESCRIPTION
    Infers test coverage from assigned commands in the regression manifest.
    Fails when a Python test, Java test, or standalone regression script is
    neither executed by a maintained suite nor explicitly excluded with a
    reason.
"""

import json
import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import Mapping, Sequence


REPO_ROOT_DEPTH = 3
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[REPO_ROOT_DEPTH]
MANIFEST_PATH = REPO_ROOT / "tests/regression/fixtures/regression_runner_manifest.json"
EXCLUSIONS_PATH = REPO_ROOT / "tests/regression/fixtures/regression_coverage_exclusions.json"

EXIT_OK = 0
EXIT_FAILED = 1

KEY_SCHEMA_VERSION = "schemaVersion"
KEY_COMMANDS = "commands"
KEY_SUITES = "suites"
KEY_ARGV = "argv"
KEY_EXCLUSIONS = "exclusions"
KEY_PATH = "path"
KEY_REASON = "reason"
SUPPORTED_SCHEMA_VERSION = 1

TOKEN_REPO_PREFIX = "{repo}/"
TOKEN_UNITTEST = "unittest"
TOKEN_DISCOVER = "discover"
TOKEN_START_DIRECTORY = "-s"
TOKEN_PATTERN = "-p"
DEFAULT_UNITTEST_PATTERN = "test*.py"
TOKEN_GRADLE_TEST = "test"
TOKEN_GRADLE = "{gradlew}"
GRADLE_EXECUTABLE_NAMES = {TOKEN_GRADLE, "gradlew", "gradlew.bat"}

TOOLS_DIRECTORY = "tools"
TEST_DIRECTORY_PART = "tests"
JAVA_TEST_ROOT = "src/test/java"
PYTHON_TEST_PATTERNS = ("test_*.py", "*_test.py")
JAVA_TEST_PATTERNS = ("*Test.java", "*Tests.java")
REGRESSION_SCRIPT_SUFFIX = "_regression.py"
PYTHON_SUFFIX = ".py"
PATH_SEPARATOR = "/"
PARENT_SEGMENT = ".."

MSG_PASS = "PASS: every discovered test and regression script is assigned or explicitly excluded."
MSG_FAIL = "FAIL: regression coverage registration is incomplete."
MSG_UNCOVERED = "uncovered test or regression: {path}"
MSG_REASON_REQUIRED = "exclusion '{path}' must have a non-empty reason"
MSG_INVALID_EXCLUSION = "exclusion path is invalid: {path}"
MSG_UNUSED_COMMAND = "manifest command is not assigned to any suite: {command_id}"
MSG_INVALID_MANIFEST = "manifest must contain object properties 'commands' and 'suites'"
MSG_INVALID_EXCLUSIONS = "coverage exclusions must contain an 'exclusions' array"


def find_coverage_issues(
    repo_root: Path,
    manifest: Mapping[str, object],
    exclusion_config: Mapping[str, object],
) -> list[str]:
    """
    NAME
        find_coverage_issues - Return deterministic registration problems.

    DESCRIPTION
        Treats suite assignment as the authority. Commands present in the
        manifest but absent from every suite do not provide coverage.
    """
    commands = manifest.get(KEY_COMMANDS)
    suites = manifest.get(KEY_SUITES)
    if not isinstance(commands, dict) or not isinstance(suites, dict):
        return [MSG_INVALID_MANIFEST]

    assigned_ids = _assigned_command_ids(suites)
    issues = _unused_command_issues(commands, assigned_ids)
    discovery_specs: set[tuple[str, str]] = set()
    exact_paths: set[str] = set()
    gradle_test_assigned = False

    for command_id in sorted(assigned_ids):
        command = commands.get(command_id)
        if not isinstance(command, dict):
            continue
        raw_argv = command.get(KEY_ARGV)
        if not isinstance(raw_argv, list):
            continue
        argv = tuple(str(item) for item in raw_argv)
        discovery_spec = _discovery_spec(argv)
        if discovery_spec:
            discovery_specs.add(discovery_spec)
        exact_paths.update(_exact_paths_from_argv(argv))
        if _is_gradle_test_command(argv):
            gradle_test_assigned = True

    exclusions, exclusion_issues = _validated_exclusions(exclusion_config)
    issues.extend(exclusion_issues)
    inventory = _python_test_paths(repo_root)
    inventory.extend(_regression_script_paths(repo_root))
    inventory.extend(_java_test_paths(repo_root))

    for relative_path in sorted(set(inventory)):
        if _is_excluded(relative_path, exclusions):
            continue
        if relative_path.startswith(JAVA_TEST_ROOT + PATH_SEPARATOR):
            covered = gradle_test_assigned
        else:
            covered = relative_path in exact_paths or _covered_by_discovery(
                relative_path, discovery_specs
            )
        if not covered:
            issues.append(MSG_UNCOVERED.format(path=relative_path))
    return sorted(set(issues))


def load_json_object(path: Path) -> Mapping[str, object]:
    """
    NAME
        load_json_object - Load one UTF-8 JSON object from disk.

    ERRORS
        Raises ValueError when the document root is not an object.
    """
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    """
    NAME
        main - Check the repository's maintained test registration.
    """
    _ = argv
    try:
        manifest = load_json_object(MANIFEST_PATH)
        exclusions = load_json_object(EXCLUSIONS_PATH)
        issues = find_coverage_issues(REPO_ROOT, manifest, exclusions)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(MSG_FAIL)
        print(f"  - {exc}")
        return EXIT_FAILED
    if issues:
        print(MSG_FAIL)
        for issue in issues:
            print(f"  - {issue}")
        return EXIT_FAILED
    print(MSG_PASS)
    return EXIT_OK


def _assigned_command_ids(suites: Mapping[str, object]) -> set[str]:
    assigned: set[str] = set()
    for command_ids in suites.values():
        if not isinstance(command_ids, list):
            continue
        assigned.update(str(command_id) for command_id in command_ids)
    return assigned


def _unused_command_issues(
    commands: Mapping[str, object], assigned_ids: set[str]
) -> list[str]:
    return [
        MSG_UNUSED_COMMAND.format(command_id=command_id)
        for command_id in sorted(commands)
        if command_id not in assigned_ids
    ]


def _discovery_spec(argv: tuple[str, ...]) -> tuple[str, str] | None:
    if TOKEN_UNITTEST not in argv or TOKEN_DISCOVER not in argv:
        return None
    try:
        start_index = argv.index(TOKEN_START_DIRECTORY) + 1
    except (ValueError, IndexError):
        return None
    if start_index >= len(argv):
        return None
    root = _normalize_manifest_path(argv[start_index])
    pattern = DEFAULT_UNITTEST_PATTERN
    if TOKEN_PATTERN in argv:
        pattern_index = argv.index(TOKEN_PATTERN) + 1
        if pattern_index < len(argv):
            pattern = argv[pattern_index]
    return root, pattern


def _exact_paths_from_argv(argv: tuple[str, ...]) -> set[str]:
    paths: set[str] = set()
    for token in argv:
        normalized = _normalize_manifest_path(token)
        if normalized.endswith(PYTHON_SUFFIX) and PATH_SEPARATOR in normalized:
            paths.add(normalized)
    if TOKEN_UNITTEST not in argv or TOKEN_DISCOVER in argv:
        return paths
    module_index = argv.index(TOKEN_UNITTEST) + 1
    for token in argv[module_index:]:
        if token.startswith("-"):
            continue
        module_path = token.replace(".", PATH_SEPARATOR) + PYTHON_SUFFIX
        paths.add(_normalize_manifest_path(module_path))
    return paths


def _is_gradle_test_command(argv: tuple[str, ...]) -> bool:
    if not argv:
        return False
    executable = Path(argv[0].replace("\\", PATH_SEPARATOR)).name.lower()
    return executable in GRADLE_EXECUTABLE_NAMES and TOKEN_GRADLE_TEST in argv


def _validated_exclusions(
    config: Mapping[str, object],
) -> tuple[dict[str, str], list[str]]:
    raw_exclusions = config.get(KEY_EXCLUSIONS)
    if not isinstance(raw_exclusions, list):
        return {}, [MSG_INVALID_EXCLUSIONS]
    exclusions: dict[str, str] = {}
    issues: list[str] = []
    for raw_entry in raw_exclusions:
        if not isinstance(raw_entry, dict):
            issues.append(MSG_INVALID_EXCLUSION.format(path=str(raw_entry)))
            continue
        path = _normalize_manifest_path(str(raw_entry.get(KEY_PATH, "")))
        reason = str(raw_entry.get(KEY_REASON, "")).strip()
        if not path or PARENT_SEGMENT in Path(path).parts:
            issues.append(MSG_INVALID_EXCLUSION.format(path=path))
            continue
        if not reason:
            issues.append(MSG_REASON_REQUIRED.format(path=path))
            continue
        exclusions[path.rstrip(PATH_SEPARATOR)] = reason
    return exclusions, issues


def _python_test_paths(repo_root: Path) -> list[str]:
    tools_root = repo_root / TOOLS_DIRECTORY
    paths: set[str] = set()
    if not tools_root.exists():
        return []
    for pattern in PYTHON_TEST_PATTERNS:
        for path in tools_root.rglob(pattern):
            relative = path.relative_to(repo_root)
            if TEST_DIRECTORY_PART in relative.parts:
                paths.add(_normalize_path(relative))
    return sorted(paths)


def _regression_script_paths(repo_root: Path) -> list[str]:
    tools_root = repo_root / TOOLS_DIRECTORY
    if not tools_root.exists():
        return []
    return sorted(
        _normalize_path(path.relative_to(repo_root))
        for path in tools_root.rglob(f"*{REGRESSION_SCRIPT_SUFFIX}")
        if TEST_DIRECTORY_PART not in path.relative_to(repo_root).parts
    )


def _java_test_paths(repo_root: Path) -> list[str]:
    java_root = repo_root / JAVA_TEST_ROOT
    paths: set[str] = set()
    if not java_root.exists():
        return []
    for pattern in JAVA_TEST_PATTERNS:
        paths.update(
            _normalize_path(path.relative_to(repo_root))
            for path in java_root.rglob(pattern)
        )
    return sorted(paths)


def _is_excluded(relative_path: str, exclusions: Mapping[str, str]) -> bool:
    for excluded_path in exclusions:
        if relative_path == excluded_path:
            return True
        if relative_path.startswith(excluded_path + PATH_SEPARATOR):
            return True
    return False


def _covered_by_discovery(
    relative_path: str, specs: set[tuple[str, str]]
) -> bool:
    file_name = relative_path.rsplit(PATH_SEPARATOR, maxsplit=1)[-1]
    return any(
        relative_path.startswith(root + PATH_SEPARATOR)
        and fnmatch(file_name, pattern)
        for root, pattern in specs
    )


def _normalize_manifest_path(value: str) -> str:
    normalized = value.replace("\\", PATH_SEPARATOR)
    if normalized.startswith(TOKEN_REPO_PREFIX):
        normalized = normalized[len(TOKEN_REPO_PREFIX) :]
    return normalized.strip(PATH_SEPARATOR)


def _normalize_path(path: Path) -> str:
    return str(path).replace("\\", PATH_SEPARATOR)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
