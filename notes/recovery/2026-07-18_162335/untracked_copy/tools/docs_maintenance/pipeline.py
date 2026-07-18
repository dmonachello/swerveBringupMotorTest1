from __future__ import annotations

"""
NAME
    pipeline.py - Modular pass runner for documentation maintenance inventory and reporting.
"""

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Dict, List, Mapping, Sequence

from .inventory import (
    CATEGORY_DOCS,
    CATEGORY_NOTES,
    CATEGORY_ROOT,
    EDIT_MODE_EDITABLE,
    EDIT_MODE_GENERATED,
    MarkdownDocument,
    inventory_markdown_documents,
)


PASS_NAME_INVENTORY = "inventory"
PASS_NAME_HEALTH = "health_report"
PASS_NAME_LINK_GRAPH = "link_graph"
PASS_NAME_TERMINOLOGY = "terminology"
PASS_NAME_MOC_PLAN = "moc_plan"
PASS_NAME_RELATED_TOPICS = "related_topics"
PASS_NAME_GLOSSARY = "glossary"
PASS_NAME_SUMMARY = "summary"
REPORT_KEY_ROOT = "root"
REPORT_KEY_TOTAL = "totalPages"
REPORT_KEY_EDITABLE = "editablePages"
REPORT_KEY_GENERATED = "generatedPages"
REPORT_KEY_ENTRYPOINTS = "entrypoints"
REPORT_KEY_CATEGORIES = "categories"
REPORT_KEY_GENERATED_FILES = "generatedFiles"
REPORT_KEY_ORPHAN_CANDIDATES = "orphanCandidates"
REPORT_KEY_BROKEN_LINKS = "brokenLinks"
REPORT_KEY_LINKED_PAGES = "linkedPages"
REPORT_KEY_TERMINOLOGY_VARIANTS = "terminologyVariants"
REPORT_KEY_DUPLICATE_TITLES = "duplicateTitles"
REPORT_KEY_PROPOSED_MOCS = "proposedMocs"
REPORT_KEY_TOP_LEVEL_INDEX = "topLevelIndex"
REPORT_KEY_RELATED_TOPICS = "relatedTopicSuggestions"
REPORT_KEY_WIKI_LINK_SUGGESTIONS = "wikiLinkSuggestions"
REPORT_KEY_GLOSSARY_ENTRIES = "glossaryEntries"
REPORT_KEY_RENAME_RECOMMENDATIONS = "renameRecommendations"
REPORT_KEY_HEALTH_SUMMARY = "healthSummary"
REPORT_KEY_PASSES = "passes"
KEY_PREFERRED = "preferred"
KEY_VARIANTS = "variants"
KEY_TITLE = "title"
KEY_TOP_LEVEL_SECTION = "topLevelSection"
KEY_SECTIONS = "sections"
KEY_SECTION_PAGES = "sectionPages"
KEY_PAGES = "pages"
KEY_REPO_PATH = "repoPath"
KEY_RELATED = "related"
KEY_LINK_TEXT = "linkText"
KEY_SOURCE = "source"
KEY_TARGET = "target"
KEY_REASON = "reason"
KEY_DEFINITION = "definition"
KEY_PURPOSE = "purpose"
KEY_RELATED_PAGES = "relatedPages"
KEY_SEE_ALSO = "seeAlso"
KEY_PAGES_PROCESSED = "pagesProcessed"
KEY_WIKI_LINKS_ADDED = "wikiLinksAdded"
KEY_RELATED_TOPICS_CREATED = "relatedTopicsSectionsCreated"
KEY_HUBS_UPDATED = "hubPagesUpdated"
KEY_TAGS_ADDED = "tagsAdded"
KEY_DUPLICATE_COUNT = "duplicatePagesDetected"
KEY_ORPHAN_COUNT = "orphanPages"
KEY_BROKEN_COUNT = "brokenLinks"
KEY_RENAME_COUNT = "suggestedRenames"
KEY_QUALITY_CONCERNS = "documentationQualityConcerns"
ENTRYPOINT_CATEGORY_ORDER = (
    CATEGORY_ROOT,
    CATEGORY_DOCS,
    CATEGORY_NOTES,
)
TERM_ACTIVATION_MANAGER = "Activation Manager"
TERM_ACTIVE_GROUP = "Active Group"
TERM_TOPOLOGY_EDITOR = "Topology Editor"
TERM_REST_SERVER = "REST Server"
TERM_DSL_EXECUTOR = "DSL Executor"
TERM_ROBOT_RUNTIME = "Robot Runtime"
TERM_SCOPE_MEMBERSHIP = "scope membership"
TERM_DSL = "DSL"
TERM_CAN_DIAGNOSTICS = "CAN Diagnostics"
TERM_TOPOLOGY = "Topology"
TERM_TESTING = "Testing"
TERM_ROBOT_BRINGUP = "Robot Bringup"
TERM_UI = "UI"
TERM_REST_API = "REST API"
TERM_ARCHITECTURE = "Architecture"
TERM_GLOSSARY = "Glossary"
TERM_PROJECT_OVERVIEW = "Project Overview"
TERMINOLOGY_VARIANT_SPECS = (
    {
        KEY_PREFERRED: TERM_ACTIVATION_MANAGER,
        KEY_VARIANTS: ("Activation Manager", "activation manager"),
    },
    {
        KEY_PREFERRED: TERM_ACTIVE_GROUP,
        KEY_VARIANTS: ("Active Group", "active group", "active-group"),
    },
    {
        KEY_PREFERRED: TERM_TOPOLOGY_EDITOR,
        KEY_VARIANTS: ("Topology Editor", "topology editor"),
    },
    {
        KEY_PREFERRED: TERM_REST_SERVER,
        KEY_VARIANTS: ("REST Server", "rest server", "REST server"),
    },
    {
        KEY_PREFERRED: TERM_DSL_EXECUTOR,
        KEY_VARIANTS: ("DSL Executor", "dsl executor"),
    },
    {
        KEY_PREFERRED: TERM_ROBOT_RUNTIME,
        KEY_VARIANTS: ("Robot Runtime", "robot runtime"),
    },
    {
        KEY_PREFERRED: TERM_SCOPE_MEMBERSHIP,
        KEY_VARIANTS: ("scope membership", "controlled lifecycle", "lifecycle scope"),
    },
)
TITLE_PREFIX_FEATURE_SPEC = "feature spec "
TITLE_PREFIX_SPEC = "spec "
TITLE_PREFIX_TEST_PLAN = "test plan "
TITLE_PREFIX_TEST_PROCEDURE = "test procedure "
TITLE_PREFIX_USER_GUIDE = "user guide "
TITLE_PREFIX_WORKFLOW = "workflow "
TITLE_PREFIX_WHITESPACE = re.compile(r"[\s_\-]+")
TITLE_PREFIX_NON_ALNUM = re.compile(r"[^a-z0-9 ]+")
TEXT_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
HEADING_PATTERN = re.compile(r"^\s*#\s+(.+?)\s*$", re.MULTILINE)
MIN_SUBSTANTIAL_TEXT_LENGTH = 200
MAX_RELATED_TOPIC_SUGGESTIONS = 6
MAX_WIKI_LINK_SUGGESTIONS = 12
MAX_GLOSSARY_LINKS = 8
MIN_TOKEN_LENGTH = 3
MIN_TITLE_TOKEN_COUNT = 2
TITLE_WORD_README = "readme"
TITLE_WORD_AGENTS = "agents"
TITLE_WORD_CHANGELOG = "changelog"
TRIVIAL_TITLES = {
    TITLE_WORD_README,
    TITLE_WORD_AGENTS,
    TITLE_WORD_CHANGELOG,
    "tbd",
}
DEFAULT_RELATED_TOPIC_REASON = "shared terminology and neighboring links"
DEFAULT_GLOSSARY_DEFINITION_PREFIX = "Repository topic cluster centered on "
DEFAULT_GLOSSARY_PURPOSE_PREFIX = "Helps locate design, workflow, and implementation notes related to "
TOP_LEVEL_INDEX_SECTION_ORDER = (
    TERM_PROJECT_OVERVIEW,
    TERM_ARCHITECTURE,
    "Subsystems",
    TERM_TESTING,
    "Diagnostics",
    TERM_DSL,
    "REST",
    TERM_TOPOLOGY,
    TERM_UI,
    "Future Work",
    TERM_GLOSSARY,
)
SECTION_FALLBACK_GENERAL = "General"
SECTION_KEYWORD_MAP = {
    "Concepts": ("concept", "overview", "model", "architecture", "semantic"),
    "Signals": ("signal", "signals", "telemetry"),
    "Runtime": ("runtime", "state", "activation"),
    "Authoring": ("authoring", "create", "creation", "editor"),
    "Testing": ("test", "procedure", "plan", "regression"),
    "Hardware": ("pdp", "pdh", "motor", "hardware", "controller", "sensor"),
    "Evidence": ("evidence", "console", "observer", "fault"),
    "Tests": ("test", "procedure", "plan", "regression"),
    "Troubleshooting": ("fault", "debug", "issue", "diagnosis", "break"),
    "Editor": ("editor", "authoring", "layout"),
    "Plans": ("plan", "roadmap"),
    "Procedures": ("procedure", "workflow"),
    "Regression": ("regression", "validation"),
    "Validation": ("validation", "sanity"),
    "Overview": ("overview", "intent", "bringup"),
    "Activation": ("activation", "scope", "membership"),
    "Operator Workflow": ("operator", "workflow", "manual"),
    "Operator Surfaces": ("operator", "ui", "surface"),
    "State": ("state", "ownership", "context"),
    "Views": ("view", "topology", "visibility"),
    "Behavior": ("behavior", "interaction", "stability"),
    "Endpoints": ("endpoint", "rest", "api"),
    "Protocol": ("protocol", "tcp", "serialization"),
    "Integration": ("integration", "contract", "networktables"),
    "Core": ("architecture", "component", "model"),
    "Host": ("host", "python", "pc"),
    "Robot": ("robot", "java", "roborio"),
    "Refactor": ("refactor", "migration", "shared"),
}
MOC_SPECS = (
    {
        KEY_TITLE: TERM_DSL,
        "keywords": ("dsl", "robot_test_dsl", "signal_set", "selected_test"),
        KEY_SECTIONS: ("Concepts", "Signals", "Runtime", "Authoring", "Testing"),
        KEY_TOP_LEVEL_SECTION: TERM_DSL,
    },
    {
        KEY_TITLE: TERM_CAN_DIAGNOSTICS,
        "keywords": ("can", "fault", "evidence", "diagnosis", "pdp", "pdh"),
        KEY_SECTIONS: ("Concepts", "Hardware", "Evidence", "Tests", "Troubleshooting"),
        KEY_TOP_LEVEL_SECTION: "Diagnostics",
    },
    {
        KEY_TITLE: TERM_TOPOLOGY,
        "keywords": ("topology", "group", "active-group", "scope membership"),
        KEY_SECTIONS: ("Concepts", "Editor", "Runtime", "Tests"),
        KEY_TOP_LEVEL_SECTION: TERM_TOPOLOGY,
    },
    {
        KEY_TITLE: TERM_TESTING,
        "keywords": ("test", "testing", "procedure", "plan", "regression"),
        KEY_SECTIONS: ("Plans", "Procedures", "Regression", "Validation"),
        KEY_TOP_LEVEL_SECTION: TERM_TESTING,
    },
    {
        KEY_TITLE: TERM_ROBOT_BRINGUP,
        "keywords": ("bringup", "runtime", "activation", "lifecycle", "scope"),
        KEY_SECTIONS: ("Overview", "Runtime", "Activation", "Operator Workflow"),
        KEY_TOP_LEVEL_SECTION: TERM_PROJECT_OVERVIEW,
    },
    {
        KEY_TITLE: TERM_UI,
        "keywords": ("ui", "gui", "operator", "view", "visibility"),
        KEY_SECTIONS: ("Operator Surfaces", "State", "Views", "Behavior"),
        KEY_TOP_LEVEL_SECTION: TERM_UI,
    },
    {
        KEY_TITLE: TERM_REST_API,
        "keywords": ("rest", "tcp", "protocol", "api", "server"),
        KEY_SECTIONS: ("Concepts", "Endpoints", "Protocol", "Integration"),
        KEY_TOP_LEVEL_SECTION: "REST",
    },
    {
        KEY_TITLE: TERM_ARCHITECTURE,
        "keywords": ("architecture", "layer", "shared service", "refactor", "component model"),
        KEY_SECTIONS: ("Core", "Host", "Robot", "Refactor"),
        KEY_TOP_LEVEL_SECTION: TERM_ARCHITECTURE,
    },
)


@dataclass(frozen=True)
class PassResult:
    """
    NAME
        PassResult - One pipeline pass result payload.
    """

    name: str
    payload: Mapping[str, Any]


def _read_text(root: Path, repo_path: str) -> str:
    path = root / repo_path
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _extract_title(root: Path, repo_path: str) -> str:
    text = _read_text(root, repo_path)
    match = HEADING_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    return Path(repo_path).stem.replace("_", " ").strip()


def _category_counts(documents: Sequence[MarkdownDocument]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for document in documents:
        counts[document.category] = counts.get(document.category, 0) + 1
    return counts


def _entrypoints(documents: Sequence[MarkdownDocument]) -> List[str]:
    prioritized: List[str] = []
    remaining: List[str] = []
    for document in documents:
        if not document.is_entrypoint:
            continue
        if document.category in ENTRYPOINT_CATEGORY_ORDER:
            prioritized.append(document.repo_path)
        else:
            remaining.append(document.repo_path)
    return sorted(prioritized) + sorted(remaining)


def _orphan_candidates(documents: Sequence[MarkdownDocument]) -> List[str]:
    incoming = _incoming_link_count(documents)
    return sorted(
        document.repo_path
        for document in documents
        if document.edit_mode == EDIT_MODE_EDITABLE and not document.is_entrypoint
        and incoming.get(document.repo_path, 0) == 0
        and len(document.outgoing_links) == 0
    )


def _document_path_set(documents: Sequence[MarkdownDocument]) -> set[str]:
    return {document.repo_path for document in documents}


def _incoming_link_count(documents: Sequence[MarkdownDocument]) -> Dict[str, int]:
    path_set = _document_path_set(documents)
    counts: Dict[str, int] = {}
    for document in documents:
        for link in document.outgoing_links:
            if link not in path_set:
                continue
            counts[link] = counts.get(link, 0) + 1
    return counts


def _broken_links(documents: Sequence[MarkdownDocument]) -> List[Dict[str, str]]:
    path_set = _document_path_set(documents)
    broken: List[Dict[str, str]] = []
    for document in documents:
        for link in document.outgoing_links:
            if link in path_set:
                continue
            broken.append({"source": document.repo_path, "target": link})
    return broken


def _linked_pages(documents: Sequence[MarkdownDocument]) -> List[str]:
    path_set = _document_path_set(documents)
    linked = set()
    for document in documents:
        if document.outgoing_links:
            linked.add(document.repo_path)
        for link in document.outgoing_links:
            if link in path_set:
                linked.add(link)
    return sorted(linked)


def _compile_variant_pattern(variant: str) -> re.Pattern[str]:
    return re.compile(r"\b" + re.escape(variant) + r"\b", re.IGNORECASE)


def _terminology_variants(root: Path, documents: Sequence[MarkdownDocument]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    editable_documents = [
        document for document in documents if document.edit_mode == EDIT_MODE_EDITABLE
    ]
    for spec in TERMINOLOGY_VARIANT_SPECS:
        per_variant: Dict[str, List[str]] = {}
        for variant in spec[KEY_VARIANTS]:
            pattern = _compile_variant_pattern(str(variant))
            matches: List[str] = []
            for document in editable_documents:
                text = _read_text(root, document.repo_path)
                if pattern.search(text):
                    matches.append(document.repo_path)
            if matches:
                per_variant[str(variant)] = sorted(matches)
        if len(per_variant) > 1:
            findings.append(
                {
                    KEY_PREFERRED: spec[KEY_PREFERRED],
                    KEY_VARIANTS: per_variant,
                }
            )
    return findings


def _normalized_title_key(repo_path: str) -> str:
    stem = Path(repo_path).stem.lower()
    stem = TITLE_PREFIX_WHITESPACE.sub(" ", stem).strip()
    for prefix in (
        TITLE_PREFIX_FEATURE_SPEC,
        TITLE_PREFIX_SPEC,
        TITLE_PREFIX_TEST_PLAN,
        TITLE_PREFIX_TEST_PROCEDURE,
        TITLE_PREFIX_USER_GUIDE,
        TITLE_PREFIX_WORKFLOW,
    ):
        if stem.startswith(prefix):
            stem = stem[len(prefix):].strip()
            break
    stem = TITLE_PREFIX_NON_ALNUM.sub("", stem)
    stem = TITLE_PREFIX_WHITESPACE.sub(" ", stem).strip()
    return stem


def _display_title(root: Path, repo_path: str) -> str:
    return _extract_title(root, repo_path).replace("[", "").replace("]", "")


def _title_tokens(repo_path: str, title: str) -> set[str]:
    normalized = " ".join((_normalized_title_key(repo_path), title.lower()))
    return {
        token
        for token in TEXT_TOKEN_PATTERN.findall(normalized)
        if len(token) >= MIN_TOKEN_LENGTH
    }


def _duplicate_titles(documents: Sequence[MarkdownDocument]) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[str]] = {}
    for document in documents:
        if document.edit_mode != EDIT_MODE_EDITABLE:
            continue
        key = _normalized_title_key(document.repo_path)
        if not key:
            continue
        buckets.setdefault(key, []).append(document.repo_path)
    duplicates: List[Dict[str, Any]] = []
    for key, paths in sorted(buckets.items()):
        if len(paths) < 2:
            continue
        duplicates.append({"normalizedTitle": key, "pages": sorted(paths)})
    return duplicates


def _rename_recommendations(root: Path, duplicates: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    recommendations: List[Dict[str, Any]] = []
    for duplicate in duplicates:
        pages = [str(page) for page in duplicate[KEY_PAGES]]
        recommended_path = sorted(
            pages,
            key=lambda path: (0 if path.startswith("docs/") else 1, path),
        )[0]
        recommendations.append(
            {
                "normalizedTitle": duplicate["normalizedTitle"],
                KEY_PAGES: pages,
                "recommendedCanonicalPage": recommended_path,
                "recommendedTitle": _display_title(root, recommended_path),
            }
        )
    return recommendations


def _document_match_score(root: Path, document: MarkdownDocument, keywords: Sequence[str]) -> int:
    haystack = " ".join(
        (
            document.repo_path.lower(),
            _normalized_title_key(document.repo_path),
            _read_text(root, document.repo_path).lower(),
        )
    )
    score = 0
    for keyword in keywords:
        if keyword.lower() in haystack:
            score += 1
    return score


def _section_pages(root: Path, documents: Sequence[MarkdownDocument], section_names: Sequence[str]) -> Dict[str, List[str]]:
    section_pages: Dict[str, List[str]] = {section: [] for section in section_names}
    section_pages[SECTION_FALLBACK_GENERAL] = []
    for document in documents:
        text = _read_text(root, document.repo_path).lower()
        assigned = False
        for section_name in section_names:
            keywords = SECTION_KEYWORD_MAP.get(section_name, ())
            if any(keyword in text or keyword in document.repo_path.lower() for keyword in keywords):
                section_pages[section_name].append(document.repo_path)
                assigned = True
        if not assigned:
            section_pages[SECTION_FALLBACK_GENERAL].append(document.repo_path)
    return {key: value for key, value in section_pages.items() if value}


def _proposed_mocs(root: Path, documents: Sequence[MarkdownDocument]) -> List[Dict[str, Any]]:
    editable_documents = [
        document for document in documents if document.edit_mode == EDIT_MODE_EDITABLE
    ]
    proposals: List[Dict[str, Any]] = []
    for spec in MOC_SPECS:
        matches: List[tuple[int, str]] = []
        for document in editable_documents:
            score = _document_match_score(root, document, spec["keywords"])
            if score <= 0:
                continue
            matches.append((score, document.repo_path))
        if not matches:
            continue
        matches.sort(key=lambda item: (-item[0], item[1]))
        selected_documents = [
            next(document for document in editable_documents if document.repo_path == path)
            for _score, path in matches[:20]
        ]
        proposals.append(
            {
                KEY_TITLE: spec[KEY_TITLE],
                KEY_TOP_LEVEL_SECTION: spec[KEY_TOP_LEVEL_SECTION],
                KEY_SECTIONS: list(spec[KEY_SECTIONS]),
                KEY_PAGES: [path for _score, path in matches[:20]],
                KEY_SECTION_PAGES: _section_pages(root, selected_documents, spec[KEY_SECTIONS]),
            }
        )
    return proposals


def _top_level_index(proposed_mocs: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[str]] = {section: [] for section in TOP_LEVEL_INDEX_SECTION_ORDER}
    for proposal in proposed_mocs:
        section = str(proposal.get(KEY_TOP_LEVEL_SECTION, "")).strip()
        title = str(proposal.get(KEY_TITLE, "")).strip()
        if section in grouped and title:
            grouped[section].append(title)
    entries: List[Dict[str, Any]] = []
    for section in TOP_LEVEL_INDEX_SECTION_ORDER:
        entries.append(
            {
                "section": section,
                "pages": sorted(grouped.get(section, [])),
            }
        )
    return entries


def _page_metadata(root: Path, documents: Sequence[MarkdownDocument]) -> Dict[str, Dict[str, Any]]:
    metadata: Dict[str, Dict[str, Any]] = {}
    incoming = _incoming_link_count(documents)
    for document in documents:
        title = _display_title(root, document.repo_path)
        metadata[document.repo_path] = {
            KEY_TITLE: title,
            "tokens": _title_tokens(document.repo_path, title),
            "incomingLinks": incoming.get(document.repo_path, 0),
            "outgoingLinks": len(document.outgoing_links),
            "isSubstantial": len(_read_text(root, document.repo_path).strip()) >= MIN_SUBSTANTIAL_TEXT_LENGTH,
        }
    return metadata


def _related_score(
    source_path: str,
    target_path: str,
    source_document: MarkdownDocument,
    target_document: MarkdownDocument,
    metadata: Mapping[str, Mapping[str, Any]],
) -> int:
    if source_path == target_path:
        return 0
    source_tokens = set(metadata[source_path]["tokens"])
    target_tokens = set(metadata[target_path]["tokens"])
    score = len(source_tokens.intersection(target_tokens)) * 3
    if source_document.category == target_document.category:
        score += 2
    if target_path in source_document.outgoing_links:
        score += 4
    if source_path in target_document.outgoing_links:
        score += 3
    if metadata[target_path]["incomingLinks"] > 0:
        score += 1
    return score


def _related_topic_suggestions(root: Path, documents: Sequence[MarkdownDocument]) -> List[Dict[str, Any]]:
    editable_documents = [document for document in documents if document.edit_mode == EDIT_MODE_EDITABLE]
    metadata = _page_metadata(root, editable_documents)
    suggestions: List[Dict[str, Any]] = []
    by_path = {document.repo_path: document for document in editable_documents}
    for source_document in editable_documents:
        if not metadata[source_document.repo_path]["isSubstantial"] and not source_document.is_entrypoint:
            continue
        scored: List[tuple[int, str]] = []
        for target_document in editable_documents:
            score = _related_score(
                source_document.repo_path,
                target_document.repo_path,
                source_document,
                target_document,
                metadata,
            )
            if score > 0:
                scored.append((score, target_document.repo_path))
        scored.sort(key=lambda item: (-item[0], item[1]))
        related_paths = [path for _score, path in scored[:MAX_RELATED_TOPIC_SUGGESTIONS]]
        if not related_paths:
            continue
        suggestions.append(
            {
                KEY_REPO_PATH: source_document.repo_path,
                KEY_TITLE: metadata[source_document.repo_path][KEY_TITLE],
                KEY_RELATED: related_paths,
                KEY_REASON: DEFAULT_RELATED_TOPIC_REASON,
            }
        )
    return suggestions


def _candidate_link_titles(root: Path, documents: Sequence[MarkdownDocument]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for document in documents:
        if document.edit_mode != EDIT_MODE_EDITABLE:
            continue
        title = _display_title(root, document.repo_path)
        normalized = _normalized_title_key(document.repo_path)
        if normalized in TRIVIAL_TITLES:
            continue
        tokens = normalized.split()
        if len(tokens) < MIN_TITLE_TOKEN_COUNT:
            continue
        candidates.append(
            {
                KEY_REPO_PATH: document.repo_path,
                KEY_TITLE: title,
                "normalizedTitle": normalized,
            }
        )
    return candidates


def _wiki_link_suggestions(root: Path, documents: Sequence[MarkdownDocument]) -> List[Dict[str, Any]]:
    candidates = _candidate_link_titles(root, documents)
    editable_documents = [document for document in documents if document.edit_mode == EDIT_MODE_EDITABLE]
    suggestions: List[Dict[str, Any]] = []
    for document in editable_documents:
        text = _read_text(root, document.repo_path)
        existing_links = set(document.outgoing_links)
        matches: List[Dict[str, str]] = []
        for candidate in candidates:
            if candidate[KEY_REPO_PATH] == document.repo_path:
                continue
            if candidate[KEY_REPO_PATH] in existing_links:
                continue
            pattern = _compile_variant_pattern(candidate["normalizedTitle"])
            if pattern.search(text):
                matches.append(
                    {
                        KEY_TARGET: candidate[KEY_REPO_PATH],
                        KEY_LINK_TEXT: candidate[KEY_TITLE],
                    }
                )
        if matches:
            suggestions.append(
                {
                    KEY_REPO_PATH: document.repo_path,
                    KEY_TITLE: _display_title(root, document.repo_path),
                    "suggestions": matches[:MAX_WIKI_LINK_SUGGESTIONS],
                }
            )
    return suggestions


def _glossary_entries(
    root: Path,
    documents: Sequence[MarkdownDocument],
    proposed_mocs: Sequence[Mapping[str, Any]],
    terminology_variants: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    metadata = _page_metadata(root, [document for document in documents if document.edit_mode == EDIT_MODE_EDITABLE])
    term_to_pages: Dict[str, set[str]] = defaultdict(set)
    for proposal in proposed_mocs:
        title = str(proposal[KEY_TITLE])
        for page in proposal[KEY_PAGES]:
            term_to_pages[title].add(str(page))
    for entry in terminology_variants:
        preferred = str(entry[KEY_PREFERRED])
        for paths in entry[KEY_VARIANTS].values():
            for path in paths:
                term_to_pages[preferred].add(str(path))
    glossary: List[Dict[str, Any]] = []
    for term, pages in sorted(term_to_pages.items()):
        related_pages = sorted(
            pages,
            key=lambda path: (-int(metadata.get(path, {}).get("incomingLinks", 0)), path),
        )[:MAX_GLOSSARY_LINKS]
        if not related_pages:
            continue
        see_also = sorted(other for other in term_to_pages.keys() if other != term)[:MAX_RELATED_TOPIC_SUGGESTIONS]
        glossary.append(
            {
                KEY_TITLE: term,
                KEY_DEFINITION: DEFAULT_GLOSSARY_DEFINITION_PREFIX + term + ".",
                KEY_PURPOSE: DEFAULT_GLOSSARY_PURPOSE_PREFIX + term + ".",
                KEY_RELATED_PAGES: related_pages,
                KEY_SEE_ALSO: see_also[:MAX_RELATED_TOPIC_SUGGESTIONS],
            }
        )
    return glossary


def _health_summary(report: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        KEY_PAGES_PROCESSED: report[REPORT_KEY_TOTAL],
        KEY_WIKI_LINKS_ADDED: 0,
        KEY_RELATED_TOPICS_CREATED: len(report[REPORT_KEY_RELATED_TOPICS]),
        KEY_HUBS_UPDATED: len(report[REPORT_KEY_PROPOSED_MOCS]),
        KEY_TAGS_ADDED: 0,
        KEY_DUPLICATE_COUNT: len(report[REPORT_KEY_DUPLICATE_TITLES]),
        KEY_ORPHAN_COUNT: len(report[REPORT_KEY_ORPHAN_CANDIDATES]),
        KEY_BROKEN_COUNT: len(report[REPORT_KEY_BROKEN_LINKS]),
        KEY_RENAME_COUNT: len(report[REPORT_KEY_RENAME_RECOMMENDATIONS]),
        KEY_QUALITY_CONCERNS: [
            "Broken internal links remain unresolved.",
            "Duplicate title families still need canonical consolidation.",
            "Related Topics and wiki links are suggested but not yet inlined into every page.",
        ],
    }


def run_docs_inventory_pipeline(root: Path) -> Dict[str, Any]:
    """
    NAME
        run_docs_inventory_pipeline - Run the first documentation-maintenance passes and return one machine-readable report.
    """
    documents = inventory_markdown_documents(root)
    proposed_mocs = _proposed_mocs(root, documents)
    terminology_variants = _terminology_variants(root, documents)
    duplicate_titles = _duplicate_titles(documents)
    related_topics = _related_topic_suggestions(root, documents)
    wiki_link_suggestions = _wiki_link_suggestions(root, documents)
    glossary_entries = _glossary_entries(root, documents, proposed_mocs, terminology_variants)
    passes: List[PassResult] = [
        PassResult(
            name=PASS_NAME_INVENTORY,
            payload={
                REPORT_KEY_TOTAL: len(documents),
                REPORT_KEY_EDITABLE: sum(1 for document in documents if document.edit_mode == EDIT_MODE_EDITABLE),
                REPORT_KEY_GENERATED: sum(1 for document in documents if document.edit_mode == EDIT_MODE_GENERATED),
                REPORT_KEY_CATEGORIES: _category_counts(documents),
            },
        ),
        PassResult(
            name=PASS_NAME_HEALTH,
            payload={
                REPORT_KEY_ENTRYPOINTS: _entrypoints(documents),
                REPORT_KEY_GENERATED_FILES: [
                    document.repo_path
                    for document in documents
                    if document.edit_mode == EDIT_MODE_GENERATED
                ],
                REPORT_KEY_ORPHAN_CANDIDATES: _orphan_candidates(documents),
            },
        ),
        PassResult(
            name=PASS_NAME_LINK_GRAPH,
            payload={
                REPORT_KEY_BROKEN_LINKS: _broken_links(documents),
                REPORT_KEY_LINKED_PAGES: _linked_pages(documents),
            },
        ),
        PassResult(
            name=PASS_NAME_TERMINOLOGY,
            payload={
                REPORT_KEY_TERMINOLOGY_VARIANTS: terminology_variants,
                REPORT_KEY_DUPLICATE_TITLES: duplicate_titles,
                REPORT_KEY_RENAME_RECOMMENDATIONS: _rename_recommendations(root, duplicate_titles),
            },
        ),
        PassResult(
            name=PASS_NAME_MOC_PLAN,
            payload={
                REPORT_KEY_PROPOSED_MOCS: proposed_mocs,
                REPORT_KEY_TOP_LEVEL_INDEX: _top_level_index(proposed_mocs),
            },
        ),
        PassResult(
            name=PASS_NAME_RELATED_TOPICS,
            payload={
                REPORT_KEY_RELATED_TOPICS: related_topics,
                REPORT_KEY_WIKI_LINK_SUGGESTIONS: wiki_link_suggestions,
            },
        ),
        PassResult(
            name=PASS_NAME_GLOSSARY,
            payload={
                REPORT_KEY_GLOSSARY_ENTRIES: glossary_entries,
            },
        ),
    ]
    report: Dict[str, Any] = {
        REPORT_KEY_ROOT: str(root),
        REPORT_KEY_PASSES: [
            {
                "name": pass_result.name,
                "payload": dict(pass_result.payload),
            }
            for pass_result in passes
        ],
    }
    for pass_result in passes:
        report.update(pass_result.payload)
    report[REPORT_KEY_HEALTH_SUMMARY] = _health_summary(report)
    return report
