"""
NAME
    build_info.py - Build metadata captured from git.
"""

BUILD_GIT_DESCRIBE = "rest_runtime_activation_2026-05-27-1-gebf2304-dirty"
BUILD_GIT_SHA = "ebf2304"
BUILD_GIT_BRANCH = "main"
BUILD_GIT_DIRTY = "dirty"
BUILD_TIMESTAMP = "2026-05-29T12:31:14-04:00"

BUILD_LABEL_GIT = "git"
BUILD_LABEL_SHA = "git-sha"
BUILD_LABEL_BRANCH = "git-branch"
BUILD_LABEL_DIRTY = "git-dirty"
BUILD_LABEL_TIME = "build-time"

BUILD_SEPARATOR = ": "
TEXT_EMPTY = ""

BUILD_FIELDS_ORDER = (
    BUILD_LABEL_GIT,
    BUILD_LABEL_SHA,
    BUILD_LABEL_BRANCH,
    BUILD_LABEL_DIRTY,
    BUILD_LABEL_TIME,
)

BUILD_INFO = {
    BUILD_LABEL_GIT: BUILD_GIT_DESCRIBE,
    BUILD_LABEL_SHA: BUILD_GIT_SHA,
    BUILD_LABEL_BRANCH: BUILD_GIT_BRANCH,
    BUILD_LABEL_DIRTY: BUILD_GIT_DIRTY,
    BUILD_LABEL_TIME: BUILD_TIMESTAMP,
}

KEY_BUILD = "build"
KEY_BUILD_FIELDS = "fields"
KEY_BUILD_LABEL = "label"
KEY_BUILD_VALUE = "value"


def format_build_line(label: str, value: str) -> str:
    """
    NAME
        format_build_line - Build a standard build-info line.
    """
    return f"{label}{BUILD_SEPARATOR}{value}"


def build_fields_payload() -> list[dict[str, str]]:
    """
    NAME
        build_fields_payload - Build a list payload for build metadata.
    """
    fields = []
    for label in BUILD_FIELDS_ORDER:
        value = BUILD_INFO.get(label, TEXT_EMPTY)
        fields.append({KEY_BUILD_LABEL: label, KEY_BUILD_VALUE: value})
    return fields


def build_info_payload() -> dict[str, object]:
    """
    NAME
        build_info_payload - Build the build-info payload for JSON output.
    """
    return {KEY_BUILD_FIELDS: build_fields_payload()}


def build_lines() -> list[str]:
    """
    NAME
        build_lines - Build formatted build-info lines.
    """
    lines = []
    for label in BUILD_FIELDS_ORDER:
        value = BUILD_INFO.get(label, TEXT_EMPTY)
        lines.append(format_build_line(label, value))
    return lines
