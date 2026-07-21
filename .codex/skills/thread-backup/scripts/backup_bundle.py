#!/usr/bin/env python
"""
NAME
    backup_bundle.py - Create one local thread-backup bundle for the repo.

SYNOPSIS
    python .codex/skills/thread-backup/scripts/backup_bundle.py --repo-root . --label refactor --summary-stdin

DESCRIPTION
    Captures repo and git state into a timestamped directory under
    notes/thread_backups/. Optionally stores a restoration summary and a
    user-provided transcript file.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


DEFAULT_BACKUP_ROOT = Path("notes") / "thread_backups"
ENCODING = "utf-8"
TIME_FORMAT = "%Y-%m-%d_%H%M%S"
FILE_ENVIRONMENT = "environment.json"
FILE_MANIFEST = "manifest.json"
FILE_HEAD = "HEAD.txt"
FILE_BRANCH = "branch.txt"
FILE_GIT_STATUS = "git_status.txt"
FILE_GIT_STATUS_FULL = "git_status_full.txt"
FILE_RECENT_LOG = "git_log_recent.txt"
FILE_TRACKED_PATCH = "tracked_changes.patch"
FILE_UNTRACKED = "untracked_files.txt"
FILE_RESTORATION_SUMMARY = "restoration_summary.md"
FILE_TRANSCRIPT_MD = "thread_transcript.md"
FILE_TRANSCRIPT_TXT = "thread_transcript.txt"


def _run(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        args,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding=ENCODING,
        errors="replace",
        check=False,
    )
    return result.stdout


def _git(args: list[str], cwd: Path) -> str:
    return _run(["git", *args], cwd)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=ENCODING)


def _copy_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _safe_label(raw: Optional[str]) -> str:
    if not raw:
        return ""
    keep = []
    for ch in raw.strip().lower():
        if ch.isalnum():
            keep.append(ch)
        elif ch in {"-", "_", " "}:
            keep.append("-")
    label = "".join(keep).strip("-")
    while "--" in label:
        label = label.replace("--", "-")
    return label[:48]


def _bundle_dir(repo_root: Path, label: str) -> Path:
    stamp = datetime.now().strftime(TIME_FORMAT)
    name = stamp if not label else f"{stamp}-{label}"
    return repo_root / DEFAULT_BACKUP_ROOT / name


def _read_summary(args: argparse.Namespace) -> str:
    if args.summary_file:
        return Path(args.summary_file).read_text(encoding=ENCODING)
    if args.summary_stdin:
        return sys.stdin.read()
    return ""


def _transcript_target_name(source: Path) -> str:
    suffix = source.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return FILE_TRANSCRIPT_MD
    return FILE_TRANSCRIPT_TXT


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--label", default="")
    parser.add_argument("--summary-file")
    parser.add_argument("--summary-stdin", action="store_true")
    parser.add_argument("--transcript-file")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    label = _safe_label(args.label)
    bundle = _bundle_dir(repo_root, label)
    bundle.mkdir(parents=True, exist_ok=True)

    branch = _git(["branch", "--show-current"], repo_root).strip()
    head = _git(["rev-parse", "HEAD"], repo_root).strip()
    status_short = _git(["status", "--short"], repo_root)
    status_full = _git(["status"], repo_root)
    recent_log = _git(["log", "--oneline", "--decorate", "-n", "30"], repo_root)
    tracked_patch = _git(["diff", "--binary", "HEAD", "--"], repo_root)
    untracked = _git(["ls-files", "--others", "--exclude-standard"], repo_root)

    _write_text(bundle / FILE_BRANCH, branch + ("\n" if branch else ""))
    _write_text(bundle / FILE_HEAD, head + ("\n" if head else ""))
    _write_text(bundle / FILE_GIT_STATUS, status_short)
    _write_text(bundle / FILE_GIT_STATUS_FULL, status_full)
    _write_text(bundle / FILE_RECENT_LOG, recent_log)
    _write_text(bundle / FILE_TRACKED_PATCH, tracked_patch)
    _write_text(bundle / FILE_UNTRACKED, untracked)

    summary_text = _read_summary(args)
    if summary_text.strip():
        _write_text(bundle / FILE_RESTORATION_SUMMARY, summary_text)

    transcript_path = None
    if args.transcript_file:
        source = Path(args.transcript_file)
        if source.exists():
            target = bundle / _transcript_target_name(source)
            _copy_if_exists(source, target)
            transcript_path = str(target.relative_to(repo_root))

    environment = {
        "cwd": str(repo_root),
        "timestamp": datetime.now().astimezone().isoformat(),
        "branch": branch,
        "head": head,
        "python": sys.version,
        "platform": os.name,
    }
    _write_text(bundle / FILE_ENVIRONMENT, json.dumps(environment, indent=2))

    manifest = {
        "bundle": str(bundle.relative_to(repo_root)),
        "branch": branch,
        "head": head,
        "has_summary": bool(summary_text.strip()),
        "transcript_file": transcript_path,
        "files": [
            FILE_BRANCH,
            FILE_HEAD,
            FILE_GIT_STATUS,
            FILE_GIT_STATUS_FULL,
            FILE_RECENT_LOG,
            FILE_TRACKED_PATCH,
            FILE_UNTRACKED,
            FILE_ENVIRONMENT,
        ],
    }
    if summary_text.strip():
        manifest["files"].append(FILE_RESTORATION_SUMMARY)
    if transcript_path:
        manifest["files"].append(Path(transcript_path).name)
    _write_text(bundle / FILE_MANIFEST, json.dumps(manifest, indent=2))

    print(str(bundle))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
