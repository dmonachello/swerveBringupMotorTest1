"""
NAME
    build_info.py - Build metadata captured from git.
"""

from __future__ import annotations

import json
import subprocess
from hashlib import sha256
from pathlib import Path
from time import time

BUILD_GIT_DESCRIBE = "ui-group-topology-checkpoint-2026-06-26-dirty"
BUILD_REVISION = "235"
BUILD_WORKSPACE_REVISION = "48"
BUILD_CODE_REVISION = "2e371f988a0b"
BUILD_GIT_SHA = "f434968"
BUILD_GIT_BRANCH = "main"
BUILD_GIT_DIRTY = "dirty"
BUILD_TIMESTAMP = "2026-06-26T21:54:40-04:00"

BUILD_LABEL_REVISION = "build-revision"
BUILD_LABEL_WORKSPACE_REVISION = "workspace-revision"
BUILD_LABEL_CODE_REVISION = "code-revision"
BUILD_LABEL_GIT = "git"
BUILD_LABEL_SHA = "git-sha"
BUILD_LABEL_BRANCH = "git-branch"
BUILD_LABEL_DIRTY = "git-dirty"
BUILD_LABEL_TIME = "build-time"

BUILD_SEPARATOR = ": "
TEXT_EMPTY = ""
TEXT_UNKNOWN = "unknown"
CODE_HASH_SEPARATOR = "\n"

REPO_ROOT = Path(__file__).resolve().parents[2]
CMD_GIT = "git"
ARG_HEAD = "HEAD"
ARG_TAGS = "--tags"
ARG_ALWAYS = "--always"
ARG_DIRTY = "--dirty"
ARG_SHORT = "--short"
ARG_ABBREV_REF = "--abbrev-ref"
ARG_COUNT = "--count"
ARG_DESCRIBE = "describe"
ARG_REV_LIST = "rev-list"
ARG_REV_PARSE = "rev-parse"
ARG_STATUS = "status"
ARG_PORCELAIN = "--porcelain"
ARG_LOG = "log"
ARG_LOG_LAST = "-1"
ARG_FORMAT = "--format=%cI"
CODE_HASH_LENGTH = 12
EXT_JAVA = ".java"
EXT_PY = ".py"
PATH_BUILD_INFO_PY_REL = "tools/common/build_info.py"
PATH_BUILD_INFO_JAVA_REL = "src/main/java/frc/robot/BuildInfo.java"
PATH_BUILD_STATE_REL = ".build_identity_state.json"
KEY_REVISION = "revision"
KEY_WORKSPACE_REVISION = "workspace_revision"
KEY_CODE_REVISION = "code_revision"
KEY_DESCRIBE = "describe"
KEY_SHA = "sha"
KEY_BRANCH = "branch"
KEY_DIRTY = "dirty"
KEY_TIME = "time"
VALUE_DIRTY = "dirty"
VALUE_CLEAN = "clean"
VALUE_ONE = 1
VALUE_ZERO = 0
STATE_KEY_WORKSPACE_REVISION = "workspaceRevision"
STATE_KEY_CODE_REVISION = "codeRevision"
STATE_KEY_UPDATED_AT_MS = "updatedAtMs"
STATE_DEFAULT = {}

BUILD_FIELDS_ORDER = (
    BUILD_LABEL_REVISION,
    BUILD_LABEL_WORKSPACE_REVISION,
    BUILD_LABEL_CODE_REVISION,
    BUILD_LABEL_GIT,
    BUILD_LABEL_SHA,
    BUILD_LABEL_BRANCH,
    BUILD_LABEL_DIRTY,
    BUILD_LABEL_TIME,
)

KEY_BUILD = "build"
KEY_BUILD_FIELDS = "fields"
KEY_BUILD_LABEL = "label"
KEY_BUILD_VALUE = "value"
STATE_PATH = REPO_ROOT / PATH_BUILD_STATE_REL


def _generated_build_info() -> dict[str, str]:
    """
    NAME
        _generated_build_info - Return generated fallback build metadata.
    """
    return {
        BUILD_LABEL_REVISION: BUILD_REVISION,
        BUILD_LABEL_WORKSPACE_REVISION: BUILD_WORKSPACE_REVISION,
        BUILD_LABEL_CODE_REVISION: BUILD_CODE_REVISION,
        BUILD_LABEL_GIT: BUILD_GIT_DESCRIBE,
        BUILD_LABEL_SHA: BUILD_GIT_SHA,
        BUILD_LABEL_BRANCH: BUILD_GIT_BRANCH,
        BUILD_LABEL_DIRTY: BUILD_GIT_DIRTY,
        BUILD_LABEL_TIME: BUILD_TIMESTAMP,
    }


def _run_git(args: list[str]) -> str:
    """
    NAME
        _run_git - Return stripped git output or an empty string.
    """
    try:
        result = subprocess.run(
            [CMD_GIT, *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return TEXT_EMPTY
    if result.returncode != 0:
        return TEXT_EMPTY
    return result.stdout.strip()


def _load_build_state() -> dict[str, object]:
    """
    NAME
        _load_build_state - Read the persisted workspace revision state.
    """
    try:
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return dict(STATE_DEFAULT)
    return raw if isinstance(raw, dict) else dict(STATE_DEFAULT)


def _save_build_state(workspace_revision: int, code_revision: str) -> None:
    """
    NAME
        _save_build_state - Persist the current workspace revision state.
    """
    payload = {
        STATE_KEY_WORKSPACE_REVISION: int(workspace_revision),
        STATE_KEY_CODE_REVISION: code_revision,
        STATE_KEY_UPDATED_AT_MS: int(time() * 1000.0),
    }
    STATE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _compute_workspace_revision(code_revision: str) -> str:
    """
    NAME
        _compute_workspace_revision - Return the monotonic local workspace revision.
    """
    state = _load_build_state()
    stored_code_revision = str(state.get(STATE_KEY_CODE_REVISION, TEXT_EMPTY)).strip()
    stored_workspace_raw = state.get(STATE_KEY_WORKSPACE_REVISION, VALUE_ZERO)
    try:
        stored_workspace = int(stored_workspace_raw)
    except Exception:
        stored_workspace = VALUE_ZERO
    if stored_code_revision == code_revision and stored_workspace >= VALUE_ONE:
        return str(stored_workspace)
    next_workspace = stored_workspace + VALUE_ONE if stored_workspace >= VALUE_ONE else VALUE_ONE
    _save_build_state(next_workspace, code_revision)
    return str(next_workspace)


def _iter_source_paths() -> list[Path]:
    """
    NAME
        _iter_source_paths - Return source files included in code revision.
    """
    excluded = {
        (REPO_ROOT / PATH_BUILD_INFO_PY_REL).resolve(),
        (REPO_ROOT / PATH_BUILD_INFO_JAVA_REL).resolve(),
    }
    paths: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in (EXT_JAVA, EXT_PY):
            continue
        resolved = path.resolve()
        if resolved in excluded:
            continue
        paths.append(resolved)
    paths.sort(key=lambda item: item.relative_to(REPO_ROOT).as_posix())
    return paths


def _compute_code_revision() -> str:
    """
    NAME
        _compute_code_revision - Build a short local source fingerprint.
    """
    digest = sha256()
    for path in _iter_source_paths():
        rel = path.relative_to(REPO_ROOT).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(CODE_HASH_SEPARATOR.encode("utf-8"))
        digest.update(path.read_bytes())
        digest.update(CODE_HASH_SEPARATOR.encode("utf-8"))
    return digest.hexdigest()[:CODE_HASH_LENGTH]


def _runtime_git_info() -> dict[str, str] | None:
    """
    NAME
        _runtime_git_info - Build live git metadata for host-side tools.
    """
    revision = _run_git([ARG_REV_LIST, ARG_COUNT, ARG_HEAD])
    describe = _run_git([ARG_DESCRIBE, ARG_TAGS, ARG_ALWAYS, ARG_DIRTY])
    sha = _run_git([ARG_REV_PARSE, ARG_SHORT, ARG_HEAD])
    branch = _run_git([ARG_REV_PARSE, ARG_ABBREV_REF, ARG_HEAD])
    dirty = VALUE_DIRTY if _run_git([ARG_STATUS, ARG_PORCELAIN]) else VALUE_CLEAN
    timestamp = _run_git([ARG_LOG, ARG_LOG_LAST, ARG_FORMAT])
    code_revision = _compute_code_revision()
    workspace_revision = _compute_workspace_revision(code_revision)
    if not revision and not sha and not describe:
        return None
    if not describe:
        describe = sha or TEXT_UNKNOWN
    return {
        KEY_REVISION: revision or TEXT_UNKNOWN,
        KEY_WORKSPACE_REVISION: workspace_revision or TEXT_UNKNOWN,
        KEY_CODE_REVISION: code_revision or TEXT_UNKNOWN,
        KEY_DESCRIBE: describe or TEXT_UNKNOWN,
        KEY_SHA: sha or TEXT_UNKNOWN,
        KEY_BRANCH: branch or TEXT_UNKNOWN,
        KEY_DIRTY: dirty or TEXT_UNKNOWN,
        KEY_TIME: timestamp or TEXT_UNKNOWN,
    }


def _load_build_info() -> dict[str, str]:
    """
    NAME
        _load_build_info - Prefer live host git metadata, else generated fallback.
    """
    runtime_info = _runtime_git_info()
    if runtime_info is None:
        return _generated_build_info()
    return {
        BUILD_LABEL_REVISION: runtime_info[KEY_REVISION],
        BUILD_LABEL_WORKSPACE_REVISION: runtime_info[KEY_WORKSPACE_REVISION],
        BUILD_LABEL_CODE_REVISION: runtime_info[KEY_CODE_REVISION],
        BUILD_LABEL_GIT: runtime_info[KEY_DESCRIBE],
        BUILD_LABEL_SHA: runtime_info[KEY_SHA],
        BUILD_LABEL_BRANCH: runtime_info[KEY_BRANCH],
        BUILD_LABEL_DIRTY: runtime_info[KEY_DIRTY],
        BUILD_LABEL_TIME: runtime_info[KEY_TIME],
    }


BUILD_INFO = _load_build_info()


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
