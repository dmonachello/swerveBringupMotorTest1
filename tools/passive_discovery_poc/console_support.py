from __future__ import annotations

"""
NAME
    console_support.py - roboRIO console-log enrichment for passive discovery.

DESCRIPTION
    Parses saved console logs with the existing host-side regex rule set and
    emits normalized console evidence records for later diagnosis.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Tuple

from tools.common.profile_constants import KEY_LABEL
from tools.passive_discovery_poc.constants import (
    CONSOLE_CATEGORY_DEVICE,
    CONSOLE_CATEGORY_SYSTEM,
    CONSOLE_CONFIDENCE_HIGH,
    CONSOLE_CONFIDENCE_LOW,
    CONSOLE_CONFIDENCE_MEDIUM,
    CONSOLE_EVIDENCE_UNRESOLVED,
    CONSOLE_HINT_KEYWORDS,
    CONSOLE_RECORD_KIND,
    CONSOLE_UNRESOLVED_RECORD_KIND,
    DEFAULT_CONSOLE_RULES_PATH,
    ENCODING_UTF8,
    ERR_REPLACE,
)
from tools.passive_discovery_poc.profile_support import load_profile_expectations


RULES_KEY = "rules"
RULE_NAME_KEY = "name"
RULE_REGEX_KEY = "regex"
RULE_SEVERITY_KEY = "severity"
RULE_SCOPE_KEY = "scope"
RULE_EVENT_TYPE_KEY = "event_type"
RULE_DEVICE_ID_GROUP_KEY = "device_id_group"
RULE_DEVICE_LABEL_KEY = "device_label"
RULE_IGNORE_CASE_KEY = "ignore_case"

SEVERITY_INFO = "INFO"
CATEGORY_TEXT = "text"
PROVENANCE_CONSOLE_RULES = "console_rules"


class _ConsoleRule:
    """
    NAME
        _ConsoleRule - Parsed console regex rule.
    """

    def __init__(
        self,
        *,
        name: str,
        regex: Pattern[str],
        severity: str,
        category: str,
        event_type: str,
        device_id_group: Optional[int],
        device_label: str,
    ) -> None:
        self.name = name
        self.regex = regex
        self.severity = severity
        self.category = category
        self.event_type = event_type
        self.device_id_group = device_id_group
        self.device_label = device_label


def parse_console_log(
    log_path: str,
    *,
    rules_path: str = DEFAULT_CONSOLE_RULES_PATH,
    profile_path: str = "",
    profile_name: str = "",
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[str]]:
    """
    NAME
        parse_console_log - Parse one saved roboRIO console log into evidence rows.
    """
    rules = _load_rules(rules_path)
    line_rows = _read_lines(log_path)
    by_label, by_id = _load_profile_indexes(profile_path=profile_path, profile_name=profile_name)
    evidence_records: List[Dict[str, Any]] = []
    warnings: List[str] = []
    matched_count = 0
    unresolved_count = 0
    for line_number, line in enumerate(line_rows, start=1):
        matched = False
        for rule in rules:
            match = rule.regex.search(line)
            if match is None:
                continue
            matched = True
            matched_count += 1
            evidence_records.append(
                _matched_record(
                    line=line,
                    line_number=line_number,
                    rule=rule,
                    match=match,
                    by_label=by_label,
                    by_id=by_id,
                    rules_path=rules_path,
                )
            )
        if matched:
            continue
        if _looks_like_can_diagnostic_line(line):
            unresolved_count += 1
            evidence_records.append(
                {
                    "kind": CONSOLE_UNRESOLVED_RECORD_KIND,
                    "lineNumber": line_number,
                    "timestamp": "",
                    "rawMessage": line,
                    "severity": SEVERITY_INFO,
                    "category": CONSOLE_CATEGORY_SYSTEM,
                    "candidateDeviceIdentity": {},
                    "candidateProfileNode": "",
                    "candidateVendor": "",
                    "candidateDeviceType": "",
                    "candidateDeviceId": None,
                    "candidateErrorCode": "",
                    "parsedEvidenceType": CONSOLE_EVIDENCE_UNRESOLVED,
                    "confidence": CONSOLE_CONFIDENCE_LOW,
                    "provenance": PROVENANCE_CONSOLE_RULES,
                }
            )
    metadata = {
        "logPath": log_path,
        "rulesPath": rules_path,
        "profilePath": profile_path,
        "profileName": profile_name,
        "lineCount": len(line_rows),
        "matchedCount": matched_count,
        "unresolvedCount": unresolved_count,
    }
    return evidence_records, metadata, warnings


def _matched_record(
    *,
    line: str,
    line_number: int,
    rule: _ConsoleRule,
    match: re.Match[str],
    by_label: Dict[str, Dict[str, Any]],
    by_id: Dict[int, List[Dict[str, Any]]],
    rules_path: str,
) -> Dict[str, Any]:
    """
    NAME
        _matched_record - Build one normalized evidence row from one matched rule.
    """
    candidate_device_id = _resolve_device_id(rule=rule, match=match)
    candidate_label = _resolve_device_label(rule=rule, candidate_device_id=candidate_device_id, by_label=by_label, by_id=by_id)
    identity = _resolve_identity(candidate_label=candidate_label, candidate_device_id=candidate_device_id, by_label=by_label, by_id=by_id)
    confidence = _resolve_confidence(identity=identity, candidate_device_id=candidate_device_id, candidate_label=candidate_label)
    return {
        "kind": CONSOLE_RECORD_KIND,
        "lineNumber": line_number,
        "timestamp": "",
        "rawMessage": line,
        "severity": rule.severity,
        "category": rule.category,
        "candidateDeviceIdentity": identity,
        "candidateProfileNode": candidate_label,
        "candidateVendor": str(identity.get("manufacturer", "")),
        "candidateDeviceType": str(identity.get("deviceType", "")),
        "candidateDeviceId": candidate_device_id,
        "candidateErrorCode": rule.event_type,
        "parsedEvidenceType": rule.event_type,
        "confidence": confidence,
        "provenance": rules_path,
    }


def _resolve_device_id(rule: _ConsoleRule, match: re.Match[str]) -> Optional[int]:
    """
    NAME
        _resolve_device_id - Extract one candidate CAN id from a regex match.
    """
    if rule.device_id_group is None:
        return None
    try:
        return int(match.group(rule.device_id_group))
    except (IndexError, TypeError, ValueError):
        return None


def _resolve_device_label(
    *,
    rule: _ConsoleRule,
    candidate_device_id: Optional[int],
    by_label: Dict[str, Dict[str, Any]],
    by_id: Dict[int, List[Dict[str, Any]]],
) -> str:
    """
    NAME
        _resolve_device_label - Resolve one candidate profile label when possible.
    """
    if rule.device_label:
        return rule.device_label
    if candidate_device_id is None:
        return ""
    candidates = by_id.get(candidate_device_id, [])
    if len(candidates) == 1:
        return str(candidates[0].get(KEY_LABEL, "")).strip()
    return ""


def _resolve_identity(
    *,
    candidate_label: str,
    candidate_device_id: Optional[int],
    by_label: Dict[str, Dict[str, Any]],
    by_id: Dict[int, List[Dict[str, Any]]],
) -> Dict[str, int]:
    """
    NAME
        _resolve_identity - Resolve one candidate CAN identity from label or CAN id.
    """
    if candidate_label:
        row = by_label.get(candidate_label)
        if isinstance(row, dict):
            return _identity_from_expected_row(row)
    if candidate_device_id is None:
        return {}
    candidates = by_id.get(candidate_device_id, [])
    if len(candidates) == 1:
        return _identity_from_expected_row(candidates[0])
    return {}


def _resolve_confidence(
    *,
    identity: Dict[str, int],
    candidate_device_id: Optional[int],
    candidate_label: str,
) -> str:
    """
    NAME
        _resolve_confidence - Bound console parsing confidence.
    """
    if identity:
        return CONSOLE_CONFIDENCE_HIGH
    if candidate_device_id is not None or candidate_label:
        return CONSOLE_CONFIDENCE_MEDIUM
    return CONSOLE_CONFIDENCE_LOW


def _identity_from_expected_row(row: Dict[str, Any]) -> Dict[str, int]:
    """
    NAME
        _identity_from_expected_row - Convert one expected-row entry into identity form.
    """
    manufacturer = row.get("manufacturer")
    device_type = row.get("deviceType")
    device_id = row.get("deviceId")
    if not isinstance(manufacturer, int) or not isinstance(device_type, int) or not isinstance(device_id, int):
        return {}
    return {
        "manufacturer": manufacturer,
        "deviceType": device_type,
        "deviceId": device_id,
    }


def _looks_like_can_diagnostic_line(line: str) -> bool:
    """
    NAME
        _looks_like_can_diagnostic_line - Identify unresolved lines worth preserving.
    """
    lowered = line.lower()
    return any(keyword in lowered for keyword in CONSOLE_HINT_KEYWORDS)


def _load_rules(path: str) -> List[_ConsoleRule]:
    """
    NAME
        _load_rules - Load regex rules from the shared console rules file.
    """
    payload = json.loads(Path(path).read_text(encoding=ENCODING_UTF8))
    rows = payload.get(RULES_KEY, []) if isinstance(payload, dict) else []
    rules: List[_ConsoleRule] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get(RULE_NAME_KEY, "")).strip()
        regex_text = str(row.get(RULE_REGEX_KEY, "")).strip()
        if not name or not regex_text:
            continue
        flags = re.IGNORECASE if bool(row.get(RULE_IGNORE_CASE_KEY, True)) else 0
        rules.append(
            _ConsoleRule(
                name=name,
                regex=re.compile(regex_text, flags),
                severity=str(row.get(RULE_SEVERITY_KEY, SEVERITY_INFO)).upper(),
                category=_normalize_category(str(row.get(RULE_SCOPE_KEY, CONSOLE_CATEGORY_SYSTEM)).strip().lower()),
                event_type=str(row.get(RULE_EVENT_TYPE_KEY, name)).strip(),
                device_id_group=int(row.get(RULE_DEVICE_ID_GROUP_KEY)) if isinstance(row.get(RULE_DEVICE_ID_GROUP_KEY), int) else None,
                device_label=str(row.get(RULE_DEVICE_LABEL_KEY, "")).strip(),
            )
        )
    return rules


def _normalize_category(raw: str) -> str:
    """
    NAME
        _normalize_category - Bound console rule scopes into the public categories.
    """
    if raw == CONSOLE_CATEGORY_DEVICE:
        return CONSOLE_CATEGORY_DEVICE
    return CONSOLE_CATEGORY_SYSTEM


def _read_lines(path: str) -> List[str]:
    """
    NAME
        _read_lines - Read one saved console log as stripped lines.
    """
    return [line.strip() for line in Path(path).read_text(encoding=ENCODING_UTF8, errors=ERR_REPLACE).splitlines() if line.strip()]


def _load_profile_indexes(profile_path: str, profile_name: str) -> Tuple[Dict[str, Dict[str, Any]], Dict[int, List[Dict[str, Any]]]]:
    """
    NAME
        _load_profile_indexes - Load expected-row mappings for label and CAN-id resolution.
    """
    if not profile_path.strip():
        return {}, {}
    _resolved_name, expected_rows = load_profile_expectations(profile_path=profile_path, profile_name=profile_name)
    by_label: Dict[str, Dict[str, Any]] = {}
    by_id: Dict[int, List[Dict[str, Any]]] = {}
    for row in expected_rows.values():
        label = str(row.get(KEY_LABEL, "")).strip()
        device_id = row.get("deviceId")
        if label:
            by_label[label] = dict(row)
        if isinstance(device_id, int):
            by_id.setdefault(device_id, []).append(dict(row))
    return by_label, by_id
