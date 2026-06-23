from __future__ import annotations

"""
NAME
    update_build_info.py - Update build metadata constants from git.

SYNOPSIS
    python tools\\update_build_info.py
    python tools\\update_build_info.py --dry-run
"""

import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from time import time
from typing import Dict, Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
PY_BUILD_INFO_PATH = REPO_ROOT / "tools/common/build_info.py"
JAVA_BUILD_INFO_PATH = REPO_ROOT / "src/main/java/frc/robot/BuildInfo.java"

ENCODING_UTF8 = "utf-8"
NEWLINE = "\n"
SPACE = " "
EQUALS = "="
QUOTE = "\""
TEXT_EMPTY = ""

CMD_GIT = "git"
ARG_DESCRIBE = "describe"
ARG_TAGS = "--tags"
ARG_ALWAYS = "--always"
ARG_DIRTY = "--dirty"
ARG_REV_PARSE = "rev-parse"
ARG_REV_LIST = "rev-list"
ARG_SHORT = "--short"
ARG_ABBREV_REF = "--abbrev-ref"
ARG_COUNT = "--count"
ARG_STATUS = "status"
ARG_PORCELAIN = "--porcelain"
ARG_LOG = "log"
ARG_FORMAT = "--format=%cI"
ARG_HEAD = "HEAD"
ARG_LOG_LAST = "-1"

FIELD_DESCRIBE = "describe"
FIELD_REVISION = "revision"
FIELD_WORKSPACE_REVISION = "workspace_revision"
FIELD_CODE_REVISION = "code_revision"
FIELD_SHA = "sha"
FIELD_BRANCH = "branch"
FIELD_DIRTY = "dirty"
FIELD_TIME = "timestamp"

VALUE_UNKNOWN = "unknown"
VALUE_DIRTY = "dirty"
VALUE_CLEAN = "clean"

PY_KEY_DESCRIBE = "BUILD_GIT_DESCRIBE"
PY_KEY_REVISION = "BUILD_REVISION"
PY_KEY_WORKSPACE_REVISION = "BUILD_WORKSPACE_REVISION"
PY_KEY_CODE_REVISION = "BUILD_CODE_REVISION"
PY_KEY_SHA = "BUILD_GIT_SHA"
PY_KEY_BRANCH = "BUILD_GIT_BRANCH"
PY_KEY_DIRTY = "BUILD_GIT_DIRTY"
PY_KEY_TIME = "BUILD_TIMESTAMP"

JAVA_KEY_DESCRIBE = "BUILD_GIT_DESCRIBE"
JAVA_KEY_REVISION = "BUILD_REVISION"
JAVA_KEY_WORKSPACE_REVISION = "BUILD_WORKSPACE_REVISION"
JAVA_KEY_CODE_REVISION = "BUILD_CODE_REVISION"
JAVA_KEY_SHA = "BUILD_GIT_SHA"
JAVA_KEY_BRANCH = "BUILD_GIT_BRANCH"
JAVA_KEY_DIRTY = "BUILD_GIT_DIRTY"
JAVA_KEY_TIME = "BUILD_TIMESTAMP"

JAVA_PREFIX_MATCH = "public static final String "
JAVA_PREFIX_WRITE = "  public static final String "
PY_ASSIGN_PREFIX = SPACE + EQUALS + SPACE
JAVA_ASSIGN_PREFIX = SPACE + EQUALS + SPACE
JAVA_SUFFIX = ";"

FLAG_DRY_RUN = "--dry-run"
MSG_APPLY = "APPLY"
MSG_DRY_RUN = "DRY-RUN"
MSG_ERROR_PREFIX = "ERROR: "
MSG_UPDATED = "Updated build info."
MSG_ERR_GIT_UNAVAILABLE = "git metadata unavailable"
LABEL_GIT = "git"
LABEL_BUILD_REVISION = "build-revision"
LABEL_WORKSPACE_REVISION = "workspace-revision"
LABEL_CODE_REVISION = "code-revision"
LABEL_GIT_SHA = "git-sha"
LABEL_GIT_BRANCH = "git-branch"
LABEL_GIT_DIRTY = "git-dirty"
LABEL_BUILD_TIME = "build-time"
MSG_PREFIX_SEP = " "
MSG_LABEL_SEP = ": "
CODE_HASH_LENGTH = 12
EXT_JAVA = ".java"
EXT_PY = ".py"
ENCODING_UTF8_STRICT = "utf-8"
PATH_BUILD_INFO_PY_REL = "tools/common/build_info.py"
PATH_BUILD_INFO_JAVA_REL = "src/main/java/frc/robot/BuildInfo.java"
PATH_BUILD_STATE_REL = ".build_identity_state.json"
STATE_KEY_WORKSPACE_REVISION = "workspaceRevision"
STATE_KEY_CODE_REVISION = "codeRevision"
STATE_KEY_UPDATED_AT_MS = "updatedAtMs"
VALUE_ZERO = 0
VALUE_ONE = 1
STATE_PATH = REPO_ROOT / PATH_BUILD_STATE_REL


def _print_error(message: str) -> int:
    """
    NAME
        _print_error - Print a consistent error message.
    """
    print(f"{MSG_ERROR_PREFIX}{message}")
    return 1


def _run_git(args: Iterable[str]) -> Tuple[int, str]:
    """
    NAME
        _run_git - Run a git command and return code/output.
    """
    try:
        result = subprocess.run(
            [CMD_GIT, *list(args)],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return (1, TEXT_EMPTY)
    return (result.returncode, result.stdout.strip())


def _git_value(args: Iterable[str]) -> str:
    """
    NAME
        _git_value - Return git command output or empty string.
    """
    code, output = _run_git(args)
    if code != 0:
        return TEXT_EMPTY
    return output


def _detect_dirty() -> str:
    """
    NAME
        _detect_dirty - Detect whether the repo has uncommitted changes.
    """
    status = _git_value([ARG_STATUS, ARG_PORCELAIN])
    if status:
        return VALUE_DIRTY
    return VALUE_CLEAN


def _load_build_state() -> Dict[str, object]:
    """
    NAME
        _load_build_state - Read the persisted workspace revision state.
    """
    try:
        raw = json.loads(STATE_PATH.read_text(encoding=ENCODING_UTF8))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _save_build_state(workspace_revision: int, code_revision: str) -> None:
    """
    NAME
        _save_build_state - Persist workspace revision state.
    """
    payload = {
        STATE_KEY_WORKSPACE_REVISION: int(workspace_revision),
        STATE_KEY_CODE_REVISION: code_revision,
        STATE_KEY_UPDATED_AT_MS: int(time() * 1000.0),
    }
    STATE_PATH.write_text(json.dumps(payload, indent=2) + NEWLINE, encoding=ENCODING_UTF8)


def _compute_workspace_revision(code_revision: str) -> str:
    """
    NAME
        _compute_workspace_revision - Return monotonic local workspace revision.
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


def _iter_source_paths() -> List[Path]:
    """
    NAME
        _iter_source_paths - Return source files that participate in code revision.
    """
    excluded = {
        (REPO_ROOT / PATH_BUILD_INFO_PY_REL).resolve(),
        (REPO_ROOT / PATH_BUILD_INFO_JAVA_REL).resolve(),
    }
    paths: List[Path] = []
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
        _compute_code_revision - Build a short source fingerprint for local code.
    """
    digest = sha256()
    for path in _iter_source_paths():
        rel = path.relative_to(REPO_ROOT).as_posix()
        digest.update(rel.encode(ENCODING_UTF8_STRICT))
        digest.update(NEWLINE.encode(ENCODING_UTF8_STRICT))
        digest.update(path.read_bytes())
        digest.update(NEWLINE.encode(ENCODING_UTF8_STRICT))
    return digest.hexdigest()[:CODE_HASH_LENGTH]


def _load_git_info() -> Dict[str, str]:
    """
    NAME
        _load_git_info - Gather git-derived build metadata.
    """
    describe = _git_value([ARG_DESCRIBE, ARG_TAGS, ARG_ALWAYS, ARG_DIRTY])
    revision = _git_value([ARG_REV_LIST, ARG_COUNT, ARG_HEAD])
    sha = _git_value([ARG_REV_PARSE, ARG_SHORT, ARG_HEAD])
    branch = _git_value([ARG_REV_PARSE, ARG_ABBREV_REF, ARG_HEAD])
    timestamp = _git_value([ARG_LOG, ARG_LOG_LAST, ARG_FORMAT])
    dirty = _detect_dirty()
    code_revision = _compute_code_revision()
    workspace_revision = _compute_workspace_revision(code_revision)
    if not describe:
        describe = sha or VALUE_UNKNOWN
    return {
        FIELD_DESCRIBE: describe or VALUE_UNKNOWN,
        FIELD_REVISION: revision or VALUE_UNKNOWN,
        FIELD_WORKSPACE_REVISION: workspace_revision or VALUE_UNKNOWN,
        FIELD_CODE_REVISION: code_revision or VALUE_UNKNOWN,
        FIELD_SHA: sha or VALUE_UNKNOWN,
        FIELD_BRANCH: branch or VALUE_UNKNOWN,
        FIELD_DIRTY: dirty or VALUE_UNKNOWN,
        FIELD_TIME: timestamp or VALUE_UNKNOWN,
    }


def _update_python_build_info(path: Path, info: Dict[str, str]) -> None:
    """
    NAME
        _update_python_build_info - Update build_info.py constants.
    """
    lines = path.read_text(encoding=ENCODING_UTF8).splitlines()
    updates = {
        PY_KEY_DESCRIBE: info[FIELD_DESCRIBE],
        PY_KEY_REVISION: info[FIELD_REVISION],
        PY_KEY_WORKSPACE_REVISION: info[FIELD_WORKSPACE_REVISION],
        PY_KEY_CODE_REVISION: info[FIELD_CODE_REVISION],
        PY_KEY_SHA: info[FIELD_SHA],
        PY_KEY_BRANCH: info[FIELD_BRANCH],
        PY_KEY_DIRTY: info[FIELD_DIRTY],
        PY_KEY_TIME: info[FIELD_TIME],
    }
    new_lines: List[str] = []
    for line in lines:
        updated = line
        stripped = line.strip()
        for key, value in updates.items():
            if stripped.startswith(f"{key}{PY_ASSIGN_PREFIX}"):
                updated = f"{key}{PY_ASSIGN_PREFIX}{QUOTE}{value}{QUOTE}"
                break
        new_lines.append(updated)
    path.write_text(NEWLINE.join(new_lines) + NEWLINE, encoding=ENCODING_UTF8)


def _update_java_build_info(path: Path, info: Dict[str, str]) -> None:
    """
    NAME
        _update_java_build_info - Update BuildInfo.java constants.
    """
    lines = path.read_text(encoding=ENCODING_UTF8).splitlines()
    updates = {
        JAVA_KEY_DESCRIBE: info[FIELD_DESCRIBE],
        JAVA_KEY_REVISION: info[FIELD_REVISION],
        JAVA_KEY_WORKSPACE_REVISION: info[FIELD_WORKSPACE_REVISION],
        JAVA_KEY_CODE_REVISION: info[FIELD_CODE_REVISION],
        JAVA_KEY_SHA: info[FIELD_SHA],
        JAVA_KEY_BRANCH: info[FIELD_BRANCH],
        JAVA_KEY_DIRTY: info[FIELD_DIRTY],
        JAVA_KEY_TIME: info[FIELD_TIME],
    }
    new_lines: List[str] = []
    for line in lines:
        updated = line
        stripped = line.strip()
        for key, value in updates.items():
            prefix = f"{JAVA_PREFIX_MATCH}{key}{JAVA_ASSIGN_PREFIX}"
            if stripped.startswith(prefix):
                updated = (
                    f"{JAVA_PREFIX_WRITE}{key}{JAVA_ASSIGN_PREFIX}{QUOTE}{value}{QUOTE}{JAVA_SUFFIX}"
                )
                break
        new_lines.append(updated)
    path.write_text(NEWLINE.join(new_lines) + NEWLINE, encoding=ENCODING_UTF8)


def _print_info(info: Dict[str, str], dry_run: bool) -> None:
    """
    NAME
        _print_info - Print build info summary.
    """
    prefix = MSG_DRY_RUN if dry_run else MSG_APPLY
    print(prefix + MSG_PREFIX_SEP + LABEL_BUILD_REVISION + MSG_LABEL_SEP + info[FIELD_REVISION])
    print(prefix + MSG_PREFIX_SEP + LABEL_WORKSPACE_REVISION + MSG_LABEL_SEP + info[FIELD_WORKSPACE_REVISION])
    print(prefix + MSG_PREFIX_SEP + LABEL_CODE_REVISION + MSG_LABEL_SEP + info[FIELD_CODE_REVISION])
    print(prefix + MSG_PREFIX_SEP + LABEL_GIT + MSG_LABEL_SEP + info[FIELD_DESCRIBE])
    print(prefix + MSG_PREFIX_SEP + LABEL_GIT_SHA + MSG_LABEL_SEP + info[FIELD_SHA])
    print(prefix + MSG_PREFIX_SEP + LABEL_GIT_BRANCH + MSG_LABEL_SEP + info[FIELD_BRANCH])
    print(prefix + MSG_PREFIX_SEP + LABEL_GIT_DIRTY + MSG_LABEL_SEP + info[FIELD_DIRTY])
    print(prefix + MSG_PREFIX_SEP + LABEL_BUILD_TIME + MSG_LABEL_SEP + info[FIELD_TIME])


def main(argv: Iterable[str] | None = None) -> int:
    """
    NAME
        main - Entry point for build-info updates.
    """
    args = list(argv) if argv is not None else []
    dry_run = FLAG_DRY_RUN in args
    info = _load_git_info()
    if info[FIELD_SHA] == VALUE_UNKNOWN and info[FIELD_DESCRIBE] == VALUE_UNKNOWN:
        return _print_error(MSG_ERR_GIT_UNAVAILABLE)
    _print_info(info, dry_run)
    if dry_run:
        return 0
    _update_python_build_info(PY_BUILD_INFO_PATH, info)
    _update_java_build_info(JAVA_BUILD_INFO_PATH, info)
    print(MSG_UPDATED)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
