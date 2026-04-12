"""
NAME
    copy_test_template.py - Interactive test template copier/editor.

SYNOPSIS
    python -m tools.test_template_wizard.copy_test_template

DESCRIPTION
    Legacy template copier that wrote bringup_tests.json. This workflow is disabled.
    Tests now live in bringup_system.json under bridgeConfig.byProfile.

SIDE EFFECTS
    Reads template files, prompts on stdin, writes JSON output.
"""

from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent / "test_templates"


def _prompt(text, default=None):
    """
    NAME
        _prompt - Prompt for a value with an optional default.
    """
    if default is None:
        prompt = f"{text}: "
    else:
        prompt = f"{text} [{default}]: "
    value = input(prompt).strip()
    return value if value else default


def _list_templates():
    """
    NAME
        _list_templates - Return available JSON templates.
    """
    if not TEMPLATE_DIR.exists():
        return []
    return sorted([p for p in TEMPLATE_DIR.glob("*.json") if p.is_file()])


def _choose_template(templates):
    """
    NAME
        _choose_template - Prompt for a template selection.

    RETURNS
        Path to the chosen template.
    """
    print("Available templates:")
    for idx, tpl in enumerate(templates, start=1):
        print(f"  {idx}. {tpl.name}")
    while True:
        raw = _prompt("Select template by number", "1")
        try:
            choice = int(raw)
        except (TypeError, ValueError):
            print("Enter a number.")
            continue
        if 1 <= choice <= len(templates):
            return templates[choice - 1]
        print("Out of range.")


def _edit_tests(payload):
    """
    NAME
        _edit_tests - Interactive editing of test entries.

    DESCRIPTION
        Updates motor labels and encoder keys in-place based on user input.
    """
    set_name = payload.get("default_test_set") or "default"
    test_sets = payload.get("test_sets", {})
    if not isinstance(test_sets, dict):
        test_sets = {}
    tests = test_sets.get(set_name, [])
    if not isinstance(tests, list):
        tests = []
    for idx, test in enumerate(tests, start=1):
        name = test.get("name", f"Test {idx}")
        print(f"\nTest {idx}: {name}")
        motor_labels = test.get("motorLabels")
        if isinstance(motor_labels, list) and motor_labels:
            default_labels = ", ".join(motor_labels)
            new_labels = _prompt("Motor labels (comma-separated)", default_labels)
            labels = [part.strip() for part in (new_labels or "").split(",") if part.strip()]
            if labels:
                test["motorLabels"] = labels
        rotation = test.get("rotation")
        if isinstance(rotation, dict):
            encoder_key = rotation.get("encoderKey")
            if encoder_key and encoder_key.lower() != "internal":
                new_encoder = _prompt("Encoder (internal or device label)", encoder_key)
                rotation["encoderKey"] = new_encoder
        tests[idx - 1] = test
    test_sets[set_name] = tests
    payload["test_sets"] = test_sets
    return payload


def _ensure_test_sets(payload):
    """
    NAME
        _ensure_test_sets - Normalize legacy payloads to test_sets format.
    """
    if not isinstance(payload, dict):
        payload = {}
    test_sets = payload.get("test_sets")
    if isinstance(test_sets, dict):
        if "default_test_set" not in payload:
            payload["default_test_set"] = "default"
        return payload
    tests = payload.get("tests", [])
    if not isinstance(tests, list):
        tests = []
    payload = {
        "default_test_set": payload.get("default_test_set", "default"),
        "test_sets": {"default": tests},
    }
    return payload


def main():
    """
    NAME
        main - CLI entry point for template copying.
    """
    print("ERROR: bringup_tests.json is legacy and not supported.")
    print("Use the CLI test authoring commands and `save unified-config` instead.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
