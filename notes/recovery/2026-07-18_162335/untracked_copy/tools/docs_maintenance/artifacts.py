from __future__ import annotations

"""
NAME
    artifacts.py - Render generated documentation artifacts from the docs-maintenance report.
"""

from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

from .pipeline import (
    KEY_DEFINITION,
    KEY_LINK_TEXT,
    KEY_PAGES,
    KEY_PAGES_PROCESSED,
    KEY_PURPOSE,
    KEY_QUALITY_CONCERNS,
    KEY_RELATED,
    KEY_RELATED_PAGES,
    KEY_SECTIONS,
    KEY_SECTION_PAGES,
    KEY_SEE_ALSO,
    KEY_SOURCE,
    KEY_TARGET,
    KEY_TITLE,
    REPORT_KEY_BROKEN_LINKS,
    REPORT_KEY_DUPLICATE_TITLES,
    REPORT_KEY_GLOSSARY_ENTRIES,
    REPORT_KEY_HEALTH_SUMMARY,
    REPORT_KEY_ORPHAN_CANDIDATES,
    REPORT_KEY_PROPOSED_MOCS,
    REPORT_KEY_RELATED_TOPICS,
    REPORT_KEY_RENAME_RECOMMENDATIONS,
    REPORT_KEY_TOP_LEVEL_INDEX,
    REPORT_KEY_WIKI_LINK_SUGGESTIONS,
)


GENERATED_HEADER = "> AUTO-GENERATED FILE. Do not modify; changes will be lost on regeneration."
DOCS_DIR_NAME = "docs"
MOCS_DIR_NAME = "mocs"
INDEX_FILE_NAME = "INDEX.md"
GLOSSARY_FILE_NAME = "GLOSSARY.md"
HEALTH_REPORT_FILE_NAME = "DOCS_HEALTH_REPORT.md"
SUGGESTIONS_FILE_NAME = "DOCS_GRAPH_SUGGESTIONS.md"
SECTION_RELATED_TOPICS = "Related Topics"
HEADING_LEVEL_ONE = "# "
HEADING_LEVEL_TWO = "## "
HEADING_LEVEL_THREE = "### "
BULLET_PREFIX = "- "
NEWLINE = "\n"
WIKI_LINK_FORMAT = "[[{target}|{label}]]"
EMPTY_TEXT = ""
MAX_SUGGESTION_ROWS = 20
NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    return NON_ALNUM.sub("_", value.lower()).strip("_")


def _wiki_link(repo_path: str, label: str) -> str:
    return WIKI_LINK_FORMAT.format(target=repo_path, label=label.replace("[", "").replace("]", ""))


def _moc_repo_path(title: str) -> str:
    slug = _slugify(title)
    return f"{DOCS_DIR_NAME}/{MOCS_DIR_NAME}/{slug}.md"


def _render_lines(lines: Iterable[str]) -> str:
    return NEWLINE.join(lines).rstrip() + NEWLINE


def _render_index(report: Mapping[str, Any]) -> str:
    moc_by_title = {
        entry[KEY_TITLE]: _moc_repo_path(str(entry[KEY_TITLE]))
        for entry in report[REPORT_KEY_PROPOSED_MOCS]
    }
    lines = [
        GENERATED_HEADER,
        EMPTY_TEXT,
        HEADING_LEVEL_ONE + "Documentation Index",
        EMPTY_TEXT,
        "Purpose: primary entry point for the repository knowledge graph.",
        EMPTY_TEXT,
    ]
    for section in report[REPORT_KEY_TOP_LEVEL_INDEX]:
        lines.append(HEADING_LEVEL_TWO + str(section["section"]))
        lines.append(EMPTY_TEXT)
        pages = list(section[KEY_PAGES])
        if not pages:
            lines.append(BULLET_PREFIX + "No hub page proposed yet.")
            lines.append(EMPTY_TEXT)
            continue
        for page in pages:
            repo_path = moc_by_title.get(str(page), f"{DOCS_DIR_NAME}/{str(page).replace(' ', '_')}.md")
            lines.append(BULLET_PREFIX + _wiki_link(repo_path, str(page)))
        lines.append(EMPTY_TEXT)
    return _render_lines(lines)


def _render_glossary(report: Mapping[str, Any]) -> str:
    lines = [
        GENERATED_HEADER,
        EMPTY_TEXT,
        HEADING_LEVEL_ONE + "Glossary",
        EMPTY_TEXT,
        "Purpose: working glossary seed for major repository concepts.",
        EMPTY_TEXT,
    ]
    for entry in report[REPORT_KEY_GLOSSARY_ENTRIES]:
        lines.append(HEADING_LEVEL_TWO + str(entry[KEY_TITLE]))
        lines.append(EMPTY_TEXT)
        lines.append(BULLET_PREFIX + "Definition: " + str(entry[KEY_DEFINITION]))
        lines.append(BULLET_PREFIX + "Purpose: " + str(entry[KEY_PURPOSE]))
        lines.append(BULLET_PREFIX + "Related Pages: " + ", ".join(
            _wiki_link(page, Path(page).stem.replace("_", " "))
            for page in entry[KEY_RELATED_PAGES]
        ))
        lines.append(BULLET_PREFIX + "See Also: " + ", ".join(
            _wiki_link(_moc_repo_path(term), term)
            if term in {moc[KEY_TITLE] for moc in report[REPORT_KEY_PROPOSED_MOCS]}
            else term
            for term in entry[KEY_SEE_ALSO]
        ))
        lines.append(EMPTY_TEXT)
    return _render_lines(lines)


def _render_moc(entry: Mapping[str, Any]) -> str:
    lines = [
        GENERATED_HEADER,
        EMPTY_TEXT,
        HEADING_LEVEL_ONE + str(entry[KEY_TITLE]),
        EMPTY_TEXT,
        "Purpose: hub page for related documentation in this topic cluster.",
        EMPTY_TEXT,
    ]
    rendered_sections = set()
    for section_name in entry[KEY_SECTIONS]:
        section_pages = list(entry[KEY_SECTION_PAGES].get(section_name, ()))
        if not section_pages:
            continue
        rendered_sections.add(section_name)
        lines.append(HEADING_LEVEL_TWO + str(section_name))
        lines.append(EMPTY_TEXT)
        for page in section_pages:
            lines.append(BULLET_PREFIX + _wiki_link(str(page), Path(str(page)).stem.replace("_", " ")))
        lines.append(EMPTY_TEXT)
    remaining_pages = list(entry[KEY_SECTION_PAGES].get("General", ()))
    if remaining_pages:
        lines.append(HEADING_LEVEL_TWO + "General")
        lines.append(EMPTY_TEXT)
        for page in remaining_pages:
            lines.append(BULLET_PREFIX + _wiki_link(str(page), Path(str(page)).stem.replace("_", " ")))
        lines.append(EMPTY_TEXT)
    lines.append(HEADING_LEVEL_TWO + SECTION_RELATED_TOPICS)
    lines.append(EMPTY_TEXT)
    lines.append(BULLET_PREFIX + _wiki_link(f"{DOCS_DIR_NAME}/{INDEX_FILE_NAME}", "Documentation Index"))
    lines.append(BULLET_PREFIX + _wiki_link(f"{DOCS_DIR_NAME}/{GLOSSARY_FILE_NAME}", "Glossary"))
    lines.append(EMPTY_TEXT)
    return _render_lines(lines)


def _render_health_report(report: Mapping[str, Any]) -> str:
    summary = report[REPORT_KEY_HEALTH_SUMMARY]
    lines = [
        GENERATED_HEADER,
        EMPTY_TEXT,
        HEADING_LEVEL_ONE + "Documentation Health Report",
        EMPTY_TEXT,
        f"{BULLET_PREFIX}Pages processed: {summary[KEY_PAGES_PROCESSED]}",
        f"{BULLET_PREFIX}Broken links: {len(report[REPORT_KEY_BROKEN_LINKS])}",
        f"{BULLET_PREFIX}Orphan pages: {len(report[REPORT_KEY_ORPHAN_CANDIDATES])}",
        f"{BULLET_PREFIX}Duplicate title families: {len(report[REPORT_KEY_DUPLICATE_TITLES])}",
        f"{BULLET_PREFIX}Suggested renames: {len(report[REPORT_KEY_RENAME_RECOMMENDATIONS])}",
        EMPTY_TEXT,
        HEADING_LEVEL_TWO + "Broken Links",
        EMPTY_TEXT,
    ]
    for broken_link in report[REPORT_KEY_BROKEN_LINKS]:
        lines.append(BULLET_PREFIX + f"{broken_link[KEY_SOURCE]} -> {broken_link[KEY_TARGET]}")
    if not report[REPORT_KEY_BROKEN_LINKS]:
        lines.append(BULLET_PREFIX + "None")
    lines.append(EMPTY_TEXT)
    lines.append(HEADING_LEVEL_TWO + "Quality Concerns")
    lines.append(EMPTY_TEXT)
    for concern in summary[KEY_QUALITY_CONCERNS]:
        lines.append(BULLET_PREFIX + str(concern))
    lines.append(EMPTY_TEXT)
    return _render_lines(lines)


def _render_suggestions(report: Mapping[str, Any]) -> str:
    lines = [
        GENERATED_HEADER,
        EMPTY_TEXT,
        HEADING_LEVEL_ONE + "Documentation Graph Suggestions",
        EMPTY_TEXT,
        "Purpose: non-destructive suggestions for future in-page linking and navigation updates.",
        EMPTY_TEXT,
        HEADING_LEVEL_TWO + "Related Topics Suggestions",
        EMPTY_TEXT,
    ]
    for entry in report[REPORT_KEY_RELATED_TOPICS][:MAX_SUGGESTION_ROWS]:
        lines.append(HEADING_LEVEL_THREE + str(entry[KEY_TITLE]))
        lines.append(EMPTY_TEXT)
        for related_path in entry[KEY_RELATED]:
            lines.append(BULLET_PREFIX + _wiki_link(str(related_path), Path(str(related_path)).stem.replace("_", " ")))
        lines.append(EMPTY_TEXT)
    lines.append(HEADING_LEVEL_TWO + "Wiki Link Suggestions")
    lines.append(EMPTY_TEXT)
    for entry in report[REPORT_KEY_WIKI_LINK_SUGGESTIONS][:MAX_SUGGESTION_ROWS]:
        lines.append(HEADING_LEVEL_THREE + str(entry[KEY_TITLE]))
        lines.append(EMPTY_TEXT)
        for suggestion in entry["suggestions"]:
            lines.append(BULLET_PREFIX + f"{suggestion[KEY_LINK_TEXT]} -> {suggestion[KEY_TARGET]}")
        lines.append(EMPTY_TEXT)
    return _render_lines(lines)


def write_docs_maintenance_artifacts(root: Path, report: Mapping[str, Any]) -> list[str]:
    docs_dir = root / DOCS_DIR_NAME
    mocs_dir = docs_dir / MOCS_DIR_NAME
    docs_dir.mkdir(parents=True, exist_ok=True)
    mocs_dir.mkdir(parents=True, exist_ok=True)
    written_paths: list[str] = []
    artifact_map = {
        docs_dir / INDEX_FILE_NAME: _render_index(report),
        docs_dir / GLOSSARY_FILE_NAME: _render_glossary(report),
        docs_dir / HEALTH_REPORT_FILE_NAME: _render_health_report(report),
        docs_dir / SUGGESTIONS_FILE_NAME: _render_suggestions(report),
    }
    for moc_entry in report[REPORT_KEY_PROPOSED_MOCS]:
        artifact_map[root / _moc_repo_path(str(moc_entry[KEY_TITLE]))] = _render_moc(moc_entry)
    for path, content in artifact_map.items():
        path.write_text(content, encoding="utf-8")
        written_paths.append(path.relative_to(root).as_posix())
    return sorted(written_paths)
