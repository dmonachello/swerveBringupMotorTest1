import json
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent / "test_templates"
OUTPUT_FILE = Path(__file__).resolve().parents[1] / "src" / "main" / "deploy" / "bringup_tests.json"


def _prompt(text, default=None):
    if default is None:
        prompt = f"{text}: "
    else:
        prompt = f"{text} [{default}]: "
    value = input(prompt).strip()
    return value if value else default


def _list_templates():
    if not TEMPLATE_DIR.exists():
        return []
    return sorted([p for p in TEMPLATE_DIR.glob("*.json") if p.is_file()])


def _choose_template(templates):
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
    tests = payload.get("tests", [])
    if not isinstance(tests, list):
        return payload
    for idx, test in enumerate(tests, start=1):
        name = test.get("name", f"Test {idx}")
        print(f"\nTest {idx}: {name}")
        motor_keys = test.get("motorKeys")
        if isinstance(motor_keys, list) and motor_keys:
            default_keys = ", ".join(motor_keys)
            new_keys = _prompt("Motor keys (comma-separated VENDOR:TYPE:ID)", default_keys)
            keys = [part.strip() for part in (new_keys or "").split(",") if part.strip()]
            if keys:
                test["motorKeys"] = keys
        rotation = test.get("rotation")
        if isinstance(rotation, dict):
            encoder_key = rotation.get("encoderKey")
            if encoder_key and encoder_key.lower() != "internal":
                new_encoder = _prompt("Encoder (internal or VENDOR:TYPE:ID)", encoder_key)
                rotation["encoderKey"] = new_encoder
        tests[idx - 1] = test
    payload["tests"] = tests
    return payload


def main():
    templates = _list_templates()
    if not templates:
        print("No templates found.")
        return 1
    tpl_path = _choose_template(templates)
    payload = json.loads(tpl_path.read_text(encoding="utf-8"))
    payload = _edit_tests(payload)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
