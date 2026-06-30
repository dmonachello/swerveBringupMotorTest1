from __future__ import annotations

"""
NAME
    generate_robot_test_dsl_reference.py - Build the generated DSL reference artifact.

DESCRIPTION
    Collects device-level markdown help kept beside DSL signal support code,
    merges it with the authoritative generated signal catalog, and emits one
    JSON artifact consumed by host surfaces such as the DSL reference popup.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.common.paths import repo_root
from tools.common.robot_test_dsl import signal_catalog

REFERENCE_OUTPUT_PATH = (
    repo_root() / "tools" / "common" / "generated" / "robot_test_dsl_reference.json"
)
SIGNALS_DOCS_DIR = (
    repo_root() / "src" / "main" / "java" / "frc" / "robot" / "tests" / "dsl" / "signals"
)
DOC_GLOB = "*.devices.md"
SECTION_FUNCTION = "function"
SECTION_DETAILS = "details"
SECTION_EXAMPLES = "examples"
DEVICE_TYPE_PREFIX = "# Device Type:"
SCHEMA_VERSION = 1
GENERATED_FROM = "tools.common.generate_robot_test_dsl_reference"
SIGNAL_SECTION_EMPTY = "(no signals)"
TOPIC_DEVICE_PREFIX = "topic_device_type_"


def generate_reference_payload() -> Dict[str, object]:
    """
    NAME
        generate_reference_payload - Build the full generated DSL reference payload.
    """
    catalog = signal_catalog()
    device_docs = load_device_reference_docs(SIGNALS_DOCS_DIR)
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedFrom": GENERATED_FROM,
        "topics": build_reference_topics(catalog, device_docs),
    }


def write_reference_payload(output_path: Path = REFERENCE_OUTPUT_PATH) -> Path:
    """
    NAME
        write_reference_payload - Persist the generated DSL reference artifact.
    """
    payload = generate_reference_payload()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path


def load_device_reference_docs(directory: Path) -> Dict[str, Dict[str, object]]:
    """
    NAME
        load_device_reference_docs - Parse device-reference markdown files by DSL device type.
    """
    result: Dict[str, Dict[str, object]] = {}
    if not directory.exists():
        return result
    for path in sorted(directory.glob(DOC_GLOB)):
        entry = parse_device_reference_markdown(path)
        device_type = str(entry.get("deviceType", "")).strip()
        if device_type:
            result[device_type] = entry
    return result


def parse_device_reference_markdown(path: Path) -> Dict[str, object]:
    """
    NAME
        parse_device_reference_markdown - Parse one device-reference markdown file.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    device_type = ""
    title = ""
    sections: Dict[str, List[str]] = {
        SECTION_FUNCTION: [],
        SECTION_DETAILS: [],
        SECTION_EXAMPLES: [],
    }
    current_section = ""
    in_code_block = False
    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            if current_section == SECTION_EXAMPLES and in_code_block:
                sections[current_section].append("")
            continue
        if stripped.startswith(DEVICE_TYPE_PREFIX):
            device_type = stripped[len(DEVICE_TYPE_PREFIX):].strip()
            title = device_type
            continue
        if stripped.startswith("## "):
            heading = stripped[3:].strip().lower()
            if heading in ("function", "purpose", "summary"):
                current_section = SECTION_FUNCTION
            elif heading == "details":
                current_section = SECTION_DETAILS
            elif heading == "examples":
                current_section = SECTION_EXAMPLES
            else:
                current_section = ""
            continue
        if current_section == SECTION_EXAMPLES and stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if current_section == SECTION_FUNCTION:
            sections[SECTION_FUNCTION].append(stripped.removeprefix("- ").strip())
            continue
        if current_section == SECTION_DETAILS:
            sections[SECTION_DETAILS].append(stripped.removeprefix("- ").strip())
            continue
        if current_section == SECTION_EXAMPLES:
            sections[SECTION_EXAMPLES].append(line)
    summary = sections[SECTION_FUNCTION][0] if sections[SECTION_FUNCTION] else ""
    details = sections[SECTION_DETAILS]
    if len(sections[SECTION_FUNCTION]) > 1:
        details = sections[SECTION_FUNCTION][1:] + details
    return {
        "deviceType": device_type,
        "title": title or device_type,
        "summary": summary,
        "details": [line for line in details if str(line).strip()],
        "examples": _trim_example_lines(sections[SECTION_EXAMPLES]),
        "sourcePath": str(path.relative_to(repo_root())).replace("\\", "/"),
    }


def _trim_example_lines(lines: List[str]) -> List[str]:
    """
    NAME
        _trim_example_lines - Trim empty leading/trailing lines from example text blocks.
    """
    start = 0
    end = len(lines)
    while start < end and not str(lines[start]).strip():
        start += 1
    while end > start and not str(lines[end - 1]).strip():
        end -= 1
    return [str(line) for line in lines[start:end]]


def build_reference_topics(
    catalog: Dict[str, Dict[str, object]],
    device_docs: Dict[str, Dict[str, object]],
) -> List[Dict[str, object]]:
    """
    NAME
        build_reference_topics - Build the DSL help topic tree.
    """
    return [
        {
            "id": "overview",
            "title": "Overview",
            "summary": "Start here for the shape of one DSL test.",
            "details": [
                "A DSL test declares devices, then uses init/main/close phases to read signals, write outputs, and decide pass/fail.",
                "Use the tree on the left to drill into supported devices, top-level declarations, phases, and individual statements.",
            ],
            "examples": [
                'test "spark25_leftY"',
                'device "SPARKMAX/NEO 25"',
                'device "controller0"',
                "",
                "main:",
                '    set "SPARKMAX/NEO 25".output_percent_cmd = controller0.leftY deadband 0.08 scaled 0.25 default 0.0',
                "    until timer.elapsed >= 10.0",
                '    require "SPARKMAX/NEO 25".position_delta outside -1.0 1.0',
            ],
            "children": [
                {
                    "id": "category_devices",
                    "title": "Supported Devices",
                    "summary": "Currently supported DSL device families, what they do, and which signals they expose.",
                    "children": build_device_topics(catalog, device_docs),
                },
                {
                    "id": "category_top",
                    "title": "Top Level",
                    "summary": "Declarations that appear before phases.",
                    "children": [
                        {
                            "id": "topic_test",
                            "title": 'test "name"',
                            "summary": "Declare the test name shown in UI, CLI, and results.",
                            "syntax": ['test "my_test_name"'],
                            "details": [
                                "Exactly one test declaration should appear at the top of the source.",
                                "The name is the stable identifier used by profile test sets and selection commands.",
                            ],
                            "examples": [
                                'test "falcon9_move_150_rotations"',
                                'test "test_minimal_25_9_spark25_leftY"',
                            ],
                        },
                        {
                            "id": "topic_device",
                            "title": 'device "label"',
                            "summary": "Declare each device label the test references.",
                            "syntax": ['device "SPARKMAX/NEO 25"'],
                            "details": [
                                "Every referenced device must be declared before init/main/close.",
                                "Labels must match the configured bringup device labels exactly.",
                            ],
                            "examples": [
                                'device "SPARKMAX/NEO 25"',
                                'device "controller0"',
                                'device "lmtSw0"',
                            ],
                        },
                    ],
                },
                {
                    "id": "category_phases",
                    "title": "Phases",
                    "summary": "Execution sections that group statements by when they run.",
                    "children": [
                        {
                            "id": "topic_init",
                            "title": "init:",
                            "summary": "Runs once at test start before the main loop.",
                            "syntax": ["init:"],
                            "details": [
                                "Use init for one-time setup such as zeroing outputs, clearing signals, or applying startup values.",
                                "Init statements run after devices are instantiated and before main begins.",
                            ],
                            "examples": [
                                "init:",
                                '    clear "FALCON 9".sticky_fault',
                                '    set "FALCON 9".output_percent_cmd = 0.0',
                            ],
                        },
                        {
                            "id": "topic_main",
                            "title": "main:",
                            "summary": "Runs every test tick until a success/abort/until ends the test.",
                            "syntax": ["main:"],
                            "details": [
                                "Put active control logic and pass/fail conditions here.",
                                "Statement order does not create nested blocks; all main statements belong to the main phase.",
                            ],
                            "examples": [
                                "main:",
                                '    set "SPARKMAX/NEO 25".output_percent_cmd = controller0.leftY deadband 0.08 scaled 0.25 default 0.0',
                                "    until timer.elapsed >= 10.0",
                                '    require "SPARKMAX/NEO 25".position_delta outside -1.0 1.0',
                            ],
                        },
                        {
                            "id": "topic_close",
                            "title": "close:",
                            "summary": "Runs once when the test stops, regardless of pass or fail.",
                            "syntax": ["close:"],
                            "details": [
                                "Use close for cleanup and safe shutdown requests.",
                                "Close runs after the result is decided, so it is not part of pass/fail evaluation.",
                            ],
                            "examples": [
                                "close:",
                                '    set "SPARKMAX/NEO 25".output_percent_cmd = 0.0',
                            ],
                        },
                    ],
                },
                {
                    "id": "category_statements",
                    "title": "Statements",
                    "summary": "Actions and conditions used inside phases.",
                    "children": [
                        {
                            "id": "topic_set",
                            "title": "set",
                            "summary": "Write a literal or scaled signal into a writable device signal.",
                            "syntax": [
                                'set "FALCON 9".output_percent_cmd = 0.2',
                                'set "SPARKMAX/NEO 25".output_percent_cmd = controller0.leftY deadband 0.08 scaled 0.25 default 0.0',
                            ],
                            "details": [
                                "Literal form writes a fixed value every tick in that phase.",
                                "Scaled form reads another signal, applies deadband/scale/default, then writes the result.",
                            ],
                            "examples": [
                                'set "FALCON 9".output_percent_cmd = 0.15',
                                'set "SPARKMAX/NEO 25".output_percent_cmd = controller0.leftY deadband 0.08 scaled 0.25 default 0.0',
                            ],
                        },
                        {
                            "id": "topic_clear",
                            "title": "clear",
                            "summary": "Clear a clearable signal such as a sticky fault.",
                            "syntax": ['clear "pdp".sticky_fault'],
                            "details": [
                                "Use clear when the target signal supports a clear operation.",
                                "This is usually paired with init so the test starts from a known state.",
                            ],
                            "examples": [
                                "init:",
                                '    clear "pdp".sticky_fault',
                            ],
                        },
                        {
                            "id": "topic_until",
                            "title": "until",
                            "summary": "Stop the test when the condition becomes true.",
                            "syntax": ["until timer.elapsed >= 10.0"],
                            "details": [
                                "Until decides when the test ends.",
                                "If requires are present, they must have latched true before the until ends the test or the result becomes FAIL.",
                            ],
                            "examples": [
                                "main:",
                                "    until timer.elapsed >= 10.0",
                                '    require "FALCON 9".position_delta > 150.0',
                            ],
                        },
                        {
                            "id": "topic_abort",
                            "title": "abort",
                            "summary": "Fail immediately when the condition becomes true.",
                            "syntax": ['abort "pdp".brownout == true'],
                            "details": [
                                "Abort is a hard failure guard.",
                                "Use it for safety or clearly-invalid runtime states that should stop the test immediately.",
                            ],
                            "examples": [
                                "main:",
                                '    abort "pdp".brownout == true',
                            ],
                        },
                        {
                            "id": "topic_success",
                            "title": "success",
                            "summary": "Pass immediately when the condition becomes true.",
                            "syntax": ['success "lmtSw0".pressed == true'],
                            "details": [
                                "Success ends the test as PASS as soon as the condition is met.",
                                "This is useful when there is a clear completion event and no fixed timeout is needed.",
                            ],
                            "examples": [
                                "main:",
                                '    success lmtSw0.pressed',
                            ],
                        },
                        {
                            "id": "topic_require",
                            "title": "require",
                            "summary": "Latch evidence that must become true sometime before the test ends.",
                            "syntax": [
                                'require "FALCON 9".position_delta > 150.0',
                                'require "SPARKMAX/NEO 25".position_delta outside -1.0 1.0',
                            ],
                            "details": [
                                "Require does not stop the test by itself.",
                                "The condition may become true at any time during the run; once satisfied it stays latched for final pass/fail evaluation.",
                                "This is the right tool for proving motion, current draw, button press, or other evidence before an until timeout.",
                            ],
                            "examples": [
                                "main:",
                                "    until timer.elapsed >= 10.0",
                                '    require "SPARKMAX/NEO 25".position_delta outside -1.0 1.0',
                            ],
                        },
                        {
                            "id": "topic_unsafe_exit",
                            "title": "unsafe-exit",
                            "summary": "Declare a signal that should be cleared/stopped if the test exits unexpectedly.",
                            "syntax": ['unsafe-exit "FALCON 9".output_percent_cmd'],
                            "details": [
                                "Unsafe-exit marks outputs that must be driven safe if the test is interrupted or errors out.",
                                "Use it for actuators that would be dangerous to leave commanded on exit.",
                            ],
                            "examples": [
                                'unsafe-exit "SPARKMAX/NEO 25".output_percent_cmd',
                            ],
                        },
                    ],
                },
            ],
        }
    ]


def build_device_topics(
    catalog: Dict[str, Dict[str, object]],
    device_docs: Dict[str, Dict[str, object]],
) -> List[Dict[str, object]]:
    """
    NAME
        build_device_topics - Build per-device DSL help topics from docs plus signal metadata.
    """
    topics: List[Dict[str, object]] = []
    for device_type in sorted(catalog.keys(), key=lambda value: str(value).lower()):
        metadata = device_docs.get(device_type, {})
        title = str(metadata.get("title", device_type)).strip() or str(device_type)
        summary = str(metadata.get("summary", "")).strip() or f"{device_type} device type."
        details = [
            str(line) for line in metadata.get("details", []) if str(line).strip()
        ]
        if not details:
            details = [f'Use device labels whose configured DSL type resolves to "{device_type}".']
        examples = [
            str(line) for line in metadata.get("examples", []) if str(line).strip()
        ]
        if not examples:
            examples = [f'device "{title}"']
        topics.append(
            {
                "id": TOPIC_DEVICE_PREFIX + str(device_type),
                "title": title,
                "summary": summary,
                "syntax": [f'device "<label>"  # resolves to DSL type {device_type}'],
                "details": details,
                "signals": build_signal_lines_for_device(catalog.get(device_type, {})),
                "examples": examples,
                "sourcePath": str(metadata.get("sourcePath", "") or ""),
            }
        )
    return topics


def build_signal_lines_for_device(signal_map: object) -> List[str]:
    """
    NAME
        build_signal_lines_for_device - Format supported-signal lines for one DSL device type.
    """
    if not isinstance(signal_map, dict) or not signal_map:
        return [SIGNAL_SECTION_EMPTY]
    lines: List[str] = []
    for signal_name in sorted(signal_map.keys(), key=lambda value: str(value).lower()):
        metadata = signal_map.get(signal_name)
        if not isinstance(metadata, dict):
            continue
        value_type = str(metadata.get("valueType", "unknown") or "unknown").strip()
        flags: List[str] = []
        if bool(metadata.get("readable", False)):
            flags.append("read")
        if bool(metadata.get("writable", False)):
            flags.append("write")
        if bool(metadata.get("clearable", False)):
            flags.append("clear")
        flag_text = ", ".join(flags) if flags else "metadata unavailable"
        safe_value = metadata.get("safeValue")
        safe_provider = bool(metadata.get("safeProvider", False))
        extras: List[str] = [value_type, flag_text]
        if safe_provider:
            extras.append("safe-provider")
        elif safe_value is not None:
            extras.append(f"safe={safe_value}")
        lines.append(f"- {signal_name}: " + " | ".join(extras))
    return lines if lines else [SIGNAL_SECTION_EMPTY]


def main() -> int:
    """
    NAME
        main - Generate the DSL reference artifact.
    """
    output_path = write_reference_payload()
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
