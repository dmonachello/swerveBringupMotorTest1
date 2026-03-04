import json
from pathlib import Path

TESTS_FILE = Path(__file__).resolve().parents[1] / "src" / "main" / "deploy" / "bringup_tests.json"


def _prompt(text, default=None):
    if default is None:
        prompt = f"{text}: "
    else:
        prompt = f"{text} [{default}]: "
    value = input(prompt).strip()
    return value if value else default


def _prompt_float(text, default):
    while True:
        raw = _prompt(text, str(default))
        try:
            return float(raw)
        except (TypeError, ValueError):
            print("Enter a number.")


def _prompt_bool(text, default):
    default_str = "y" if default else "n"
    while True:
        raw = _prompt(text, default_str)
        if raw is None:
            return default
        raw = raw.strip().lower()
        if raw in ("y", "yes", "true", "1"):
            return True
        if raw in ("n", "no", "false", "0"):
            return False
        print("Enter y or n.")


def _load_tests():
    if not TESTS_FILE.exists():
        return {"tests": []}
    try:
        return json.loads(TESTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"tests": []}


def _save_tests(payload):
    TESTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TESTS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _pick_type():
    types = ["composite", "joystick"]
    print("Available test types:")
    for idx, name in enumerate(types, start=1):
        print(f"  {idx}. {name}")
    while True:
        raw = _prompt("Select type by number", "1")
        try:
            choice = int(raw)
        except (TypeError, ValueError):
            print("Enter a number.")
            continue
        if 1 <= choice <= len(types):
            return types[choice - 1]
        print("Out of range.")


def _prompt_device_keys(label):
    while True:
        raw = _prompt(label)
        if not raw:
            print("Enter at least one key.")
            continue
        keys = [part.strip() for part in raw.split(",") if part.strip()]
        if all(key.count(":") == 2 for key in keys):
            return keys
        print("Use VENDOR:TYPE:ID (example: REV:NEO:10). Separate multiple with commas.")


def _prompt_encoder_key():
    while True:
        raw = _prompt("Encoder (internal or VENDOR:TYPE:ID)", "internal")
        if raw and raw.lower() == "internal":
            return "internal"
        if raw and raw.count(":") == 2:
            return raw
        print("Use 'internal' or VENDOR:TYPE:ID (example: CTRE:CANCoder:12)")


def _prompt_action(label, default):
    while True:
        raw = _prompt(label, default).strip().lower()
        if raw in ("pass", "fail"):
            return raw
        print("Enter 'pass' or 'fail'.")


def _build_composite():
    name = _prompt("Test name", "Composite test")
    enabled = _prompt_bool("Enabled", False)
    motor_keys = _prompt_device_keys("Motor keys (comma-separated VENDOR:TYPE:ID)")
    duty = _prompt_float("Duty (-1.0..1.0)", 0.2)

    rotation_enabled = _prompt_bool("Enable rotation check", True)
    rotation = None
    if rotation_enabled:
        limit_rot = _prompt_float("Limit rotations", 10.0)
        encoder_key = _prompt_encoder_key()
        rotation = {
            "limitRot": limit_rot,
            "encoderKey": encoder_key,
        }

    time_enabled = _prompt_bool("Enable time check", True)
    time_check = None
    if time_enabled:
        timeout = _prompt_float("Timeout sec", 2.0)
        on_timeout = _prompt_action("On timeout (pass/fail)", "pass")
        time_check = {
            "timeoutSec": timeout,
            "onTimeout": on_timeout,
        }

    limit_enabled = _prompt_bool("Enable limit switch check", True)
    limit_switch = None
    if limit_enabled:
        on_hit = _prompt_action("On limit hit (pass/fail)", "pass")
        limit_switch = {
            "enabled": True,
            "onHit": on_hit,
        }

    hold_enabled = _prompt_bool("Enable hold-to-run check", False)
    hold_check = None
    if hold_enabled:
        on_release = _prompt_action("On release (pass/fail)", "pass")
        hold_check = {
            "enabled": True,
            "onRelease": on_release,
        }

    entry = {
        "type": "composite",
        "name": name,
        "enabled": enabled,
        "motorKeys": motor_keys,
        "duty": duty,
    }
    if rotation is not None:
        entry["rotation"] = rotation
    if time_check is not None:
        entry["time"] = time_check
    if limit_switch is not None:
        entry["limitSwitch"] = limit_switch
    if hold_check is not None:
        entry["hold"] = hold_check
    return entry


def _build_joystick():
    name = _prompt("Test name", "Joystick motor")
    enabled = _prompt_bool("Enabled", False)
    motor_keys = _prompt_device_keys("Motor keys (comma-separated VENDOR:TYPE:ID)")
    deadband = _prompt_float("Deadband", 0.12)
    axis = _prompt("Input axis (primary or secondary)", "primary").strip().lower()
    if axis not in ("primary", "secondary"):
        axis = "primary"
    return {
        "type": "joystick",
        "name": name,
        "enabled": enabled,
        "motorKeys": motor_keys,
        "deadband": deadband,
        "inputAxis": axis,
    }

def main():
    print("Bringup Test Wizard")
    payload = _load_tests()
    tests = payload.get("tests", [])
    if not isinstance(tests, list):
        tests = []
    test_type = _pick_type()
    if test_type == "composite":
        entry = _build_composite()
    elif test_type == "joystick":
        entry = _build_joystick()
    else:
        print("Unknown test type.")
        return 1
    tests.append(entry)
    payload["tests"] = tests
    _save_tests(payload)
    print(f"Wrote {TESTS_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
