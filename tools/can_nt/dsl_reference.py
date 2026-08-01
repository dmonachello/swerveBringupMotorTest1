from __future__ import annotations

"""
NAME
    dsl_reference.py - Shared DSL reference topics and rendering helpers for host surfaces.

DESCRIPTION
    Loads the generated DSL reference artifact and renders its hierarchical
    topics for the host UI. Device-level descriptions come from markdown files
    kept beside DSL signal support code and are merged with the authoritative
    generated signal catalog during artifact generation.
"""

from pathlib import Path
from typing import Dict, List

from tools.common.json_io import read_json
from tools.common.paths import repo_root

TEST_SOURCE_REFERENCE_TITLE = "DSL Reference"
TEST_SOURCE_REFERENCE_GEOMETRY = "860x520"
TEST_SOURCE_REFERENCE_TREE_WIDTH = 260
TEST_SOURCE_REFERENCE_SIGNAL_SECTION_TITLE = "Supported Signals:"
TEST_SOURCE_REFERENCE_OVERVIEW = "overview"
TEST_SOURCE_REFERENCE_CATEGORY_TOP = "category_top"
TEST_SOURCE_REFERENCE_CATEGORY_PHASES = "category_phases"
TEST_SOURCE_REFERENCE_CATEGORY_STATEMENTS = "category_statements"
TEST_SOURCE_REFERENCE_CATEGORY_DEVICES = "category_devices"
TEST_SOURCE_REFERENCE_CATEGORY_LANGUAGE = "category_language"
TEST_SOURCE_REFERENCE_TOPIC_TEST = "topic_test"
TEST_SOURCE_REFERENCE_TOPIC_DEVICE = "topic_device"
TEST_SOURCE_REFERENCE_TOPIC_COMMENTS = "topic_comments"
TEST_SOURCE_REFERENCE_TOPIC_NAMES_AND_LABELS = "topic_names_and_labels"
TEST_SOURCE_REFERENCE_TOPIC_INIT = "topic_init"
TEST_SOURCE_REFERENCE_TOPIC_MAIN = "topic_main"
TEST_SOURCE_REFERENCE_TOPIC_CLOSE = "topic_close"
TEST_SOURCE_REFERENCE_TOPIC_SET = "topic_set"
TEST_SOURCE_REFERENCE_TOPIC_CLEAR = "topic_clear"
TEST_SOURCE_REFERENCE_TOPIC_UNTIL = "topic_until"
TEST_SOURCE_REFERENCE_TOPIC_ABORT = "topic_abort"
TEST_SOURCE_REFERENCE_TOPIC_SUCCESS = "topic_success"
TEST_SOURCE_REFERENCE_TOPIC_REQUIRE = "topic_require"
TEST_SOURCE_REFERENCE_TOPIC_UNSAFE_EXIT = "topic_unsafe_exit"
TEST_SOURCE_REFERENCE_TOPIC_DEVICE_TYPE_PREFIX = "topic_device_type_"
REFERENCE_ARTIFACT_PATH = (
    repo_root() / "tools" / "common" / "generated" / "robot_test_dsl_reference.json"
)


def dsl_reference_topics() -> List[Dict[str, object]]:
    """
    NAME
        dsl_reference_topics - Return the generated hierarchical DSL reference topic tree.
    """
    payload = read_json(REFERENCE_ARTIFACT_PATH)
    if not isinstance(payload, dict):
        return []
    topics = payload.get("topics")
    if not isinstance(topics, list):
        return []
    return [topic for topic in topics if isinstance(topic, dict)]


def collect_dsl_reference_topic_map(topics: List[Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    """
    NAME
        collect_dsl_reference_topic_map - Flatten the DSL reference topic tree by id.
    """
    topic_map: Dict[str, Dict[str, object]] = {}

    def _walk(nodes: List[Dict[str, object]]) -> None:
        for node in nodes:
            topic_id = str(node.get("id", "")).strip()
            if topic_id:
                topic_map[topic_id] = node
            children = node.get("children")
            if isinstance(children, list):
                _walk([child for child in children if isinstance(child, dict)])

    _walk(topics)
    return topic_map


def render_dsl_reference_detail(topic: Dict[str, object]) -> str:
    """
    NAME
        render_dsl_reference_detail - Render one DSL reference topic into detail text.
    """
    lines: List[str] = []
    title = str(topic.get("title", "")).strip()
    summary = str(topic.get("summary", "")).strip()
    if title:
        lines.append(title)
        lines.append("")
    if summary:
        lines.append(summary)
        lines.append("")
    syntax = topic.get("syntax")
    if isinstance(syntax, list) and syntax:
        lines.append("Syntax:")
        lines.append("")
        for item in syntax:
            lines.append(f"  {str(item)}")
        lines.append("")
    details = topic.get("details")
    if isinstance(details, list) and details:
        lines.append("Details:")
        lines.append("")
        for item in details:
            lines.append(f"- {str(item)}")
        lines.append("")
    signals = topic.get("signals")
    if isinstance(signals, list) and signals:
        lines.append(TEST_SOURCE_REFERENCE_SIGNAL_SECTION_TITLE)
        lines.append("")
        for item in signals:
            lines.append(str(item))
        lines.append("")
    examples = topic.get("examples")
    if isinstance(examples, list) and examples:
        lines.append("Examples:")
        lines.append("")
        for item in examples:
            lines.append(str(item))
    return "\n".join(lines).rstrip()
