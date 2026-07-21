from __future__ import annotations

"""
NAME
    inventory.py - Inventory and classify Markdown documentation in the repo tree.
"""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, List, Sequence


MARKDOWN_GLOB = "*.md"
PATH_PART_BIN = "bin"
PATH_PART_BUILD = "build"
PATH_PART_DOCS = "docs"
PATH_PART_NOTES = "notes"
PATH_PART_TOOLS = "tools"
PATH_PART_SRC = "src"
PATH_PART_PYTEST_CACHE = ".pytest_cache"
PATH_PART_CODEX = ".codex"
PATH_PART_GIT = ".git"
PATH_PART_VENVS = ".venv"
PATH_PART_DECISIONS = "decisions"
PATH_PART_JOURNAL = "journal"
PATH_PART_RESEARCH = "research"
PATH_PART_PROCEDURES = "procedures"
PATH_PART_PLANNING = "planning"
PATH_PART_UI_LAYOUTS = "ui_layout_mockups"
CATEGORY_ROOT = "root"
CATEGORY_DOCS = "docs"
CATEGORY_NOTES = "notes"
CATEGORY_TOOLS = "tools"
CATEGORY_SRC = "src"
CATEGORY_OTHER = "other"
EDIT_MODE_EDITABLE = "editable"
EDIT_MODE_GENERATED = "generated"
EDIT_MODE_UNKNOWN = "unknown"
GENERATED_MARKER_AUTO = "auto-generated file"
GENERATED_MARKER_DO_NOT_EDIT = "do not modify"
GENERATED_MARKER_WILL_BE_LOST = "changes will be lost on regeneration"
GENERATED_MARKERS = (
    GENERATED_MARKER_AUTO,
    GENERATED_MARKER_DO_NOT_EDIT,
    GENERATED_MARKER_WILL_BE_LOST,
)
GENERATED_SCAN_LINE_COUNT = 12
IGNORED_PATH_PARTS = {
    PATH_PART_BIN,
    PATH_PART_BUILD,
    PATH_PART_PYTEST_CACHE,
    PATH_PART_CODEX,
    PATH_PART_GIT,
    PATH_PART_VENVS,
    "__pycache__",
}
ROOT_ENTRYPOINT_NAMES = {
    "readme.md",
    "agents.md",
    "changelog.md",
}
DOCS_ENTRYPOINT_NAMES = {
    "readme.md",
    "architecture.md",
    "user_guide.md",
    "workflows.md",
    "feature_catalog.md",
    "feature_matrix.md",
    "glossary.md",
    "index.md",
}
LINK_PATTERN_MARKDOWN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
LINK_PATTERN_WIKI = re.compile(r"\[\[([^\]|#]+)")


@dataclass(frozen=True)
class MarkdownDocument:
    """
    NAME
        MarkdownDocument - Structured metadata for one Markdown file in the repo tree.
    """

    repo_path: str
    category: str
    edit_mode: str
    is_entrypoint: bool
    markers: Sequence[str]
    outgoing_links: Sequence[str]


def _relative_repo_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _path_category(path: Path) -> str:
    parts = {part.lower() for part in path.parts}
    if PATH_PART_DOCS in parts:
        return CATEGORY_DOCS
    if PATH_PART_NOTES in parts:
        return CATEGORY_NOTES
    if PATH_PART_TOOLS in parts:
        return CATEGORY_TOOLS
    if PATH_PART_SRC in parts:
        return CATEGORY_SRC
    if len(path.parts) == 1:
        return CATEGORY_ROOT
    return CATEGORY_OTHER


def _entrypoint_name_set(category: str) -> set[str]:
    if category == CATEGORY_ROOT:
        return set(ROOT_ENTRYPOINT_NAMES)
    if category == CATEGORY_DOCS:
        return set(DOCS_ENTRYPOINT_NAMES)
    return set()


def _is_entrypoint(path: Path, category: str) -> bool:
    return path.name.lower() in _entrypoint_name_set(category)


def _detect_generated_markers(text: str) -> List[str]:
    lowered = "\n".join(text.lower().splitlines()[:GENERATED_SCAN_LINE_COUNT])
    markers: List[str] = []
    for marker in GENERATED_MARKERS:
        if marker in lowered:
            markers.append(marker)
    return markers


def _classify_edit_mode(path: Path, text: str) -> tuple[str, List[str]]:
    markers = _detect_generated_markers(text)
    if markers:
        return EDIT_MODE_GENERATED, markers
    if PATH_PART_UI_LAYOUTS in {part.lower() for part in path.parts}:
        return EDIT_MODE_EDITABLE, markers
    if path.suffix.lower() == ".md":
        return EDIT_MODE_EDITABLE, markers
    return EDIT_MODE_UNKNOWN, markers


def _normalize_markdown_target(
    current_path: Path,
    root: Path,
    raw_target: str,
) -> str | None:
    target = raw_target.strip()
    if not target or target.startswith("http://") or target.startswith("https://") or target.startswith("mailto:"):
        return None
    if target.startswith("#"):
        return None
    target = target.split("#", 1)[0].strip()
    if not target:
        return None
    if ".md" not in target.lower():
        return None
    candidate = (current_path.parent / target).resolve() if not Path(target).is_absolute() else Path(target)
    try:
        relative = candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return relative.as_posix()


def _extract_outgoing_links(current_path: Path, root: Path, text: str) -> List[str]:
    links: List[str] = []
    for match in LINK_PATTERN_MARKDOWN.finditer(text):
        normalized = _normalize_markdown_target(current_path, root, match.group(1))
        if normalized:
            links.append(normalized)
    for match in LINK_PATTERN_WIKI.finditer(text):
        wiki_target = match.group(1).strip()
        if not wiki_target:
            continue
        links.append(wiki_target)
    return sorted(set(links))


def iter_markdown_paths(root: Path) -> Iterable[Path]:
    for path in root.rglob(MARKDOWN_GLOB):
        relative = path.relative_to(root)
        parts = {part.lower() for part in relative.parts}
        if parts.intersection(IGNORED_PATH_PARTS):
            continue
        yield path


def inventory_markdown_documents(root: Path) -> List[MarkdownDocument]:
    """
    NAME
        inventory_markdown_documents - Discover and classify Markdown files under the repo root.
    """
    documents: List[MarkdownDocument] = []
    for path in sorted(iter_markdown_paths(root)):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="replace")
        category = _path_category(path.relative_to(root))
        edit_mode, markers = _classify_edit_mode(path.relative_to(root), text)
        documents.append(
            MarkdownDocument(
                repo_path=_relative_repo_path(root, path),
                category=category,
                edit_mode=edit_mode,
                is_entrypoint=_is_entrypoint(path.relative_to(root), category),
                markers=tuple(markers),
                outgoing_links=tuple(_extract_outgoing_links(path, root, text)),
            )
        )
    return documents
