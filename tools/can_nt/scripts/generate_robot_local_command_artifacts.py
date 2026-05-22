from __future__ import annotations

"""
NAME
    generate_robot_local_command_artifacts.py - Generate host UI artifacts from Java command registry.

SYNOPSIS
    python tools/can_nt/scripts/generate_robot_local_command_artifacts.py

DESCRIPTION
    Calls the Java registry inventory emitter and writes:
    - tools/can_nt/generated/robot_local_command_inventory.json
    - tools/can_nt/generated/robot_local_commands_generated.py

NOTES
    Java remains the source of truth. Users are not expected to hand-edit the
    generated Python artifacts.
"""

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
GRADLEW = REPO_ROOT / "gradlew.bat"
GENERATED_DIR = REPO_ROOT / "tools" / "can_nt" / "generated"
JSON_PATH = GENERATED_DIR / "robot_local_command_inventory.json"
PY_PATH = GENERATED_DIR / "robot_local_commands_generated.py"
GRADLE_TASK = "emitRobotLocalCommandInventory"
JSON_KEY_COMMANDS = "commands"
JSON_KEY_SHOW_IN_HOST_UI = "showInHostUi"
JSON_KEY_UI_SECTION = "uiSection"
JSON_KEY_NAME = "name"
PY_HEADER = '''from __future__ import annotations

"""
NAME
    robot_local_commands_generated.py - Generated host UI command metadata.

DESCRIPTION
    Generated from the Java RobotLocalCommandRegistry. Do not hand-edit.
"""

'''


def _load_inventory() -> dict:
    """
    NAME
        _load_inventory - Run the Java inventory emitter and parse its JSON output.
    """
    result = subprocess.run(
        [str(GRADLEW), "-q", GRADLE_TASK],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    for line in reversed(lines):
      if line.startswith("{") and line.endswith("}"):
          return json.loads(line)
    raise RuntimeError("Failed to find JSON inventory in Gradle output.")


def _build_sections(inventory: dict) -> list[dict]:
    """
    NAME
        _build_sections - Build host UI sections from inventory metadata.
    """
    grouped: dict[str, list[dict]] = {}
    for row in inventory.get(JSON_KEY_COMMANDS, []):
        if not row.get(JSON_KEY_SHOW_IN_HOST_UI):
            continue
        section = str(row.get(JSON_KEY_UI_SECTION, "")).strip()
        if not section:
            continue
        grouped.setdefault(section, []).append(dict(row))
    sections: list[dict] = []
    for section, commands in grouped.items():
        commands.sort(key=lambda row: str(row.get(JSON_KEY_NAME, "")))
        sections.append({"section": section, "commands": commands})
    return sections


def _write_json(path: Path, payload: dict) -> None:
    """
    NAME
        _write_json - Write pretty JSON output.
    """
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _write_python(path: Path, inventory: dict, sections: list[dict]) -> None:
    """
    NAME
        _write_python - Emit generated Python metadata module.
    """
    commands = inventory.get(JSON_KEY_COMMANDS, [])
    commands_by_name = {row.get(JSON_KEY_NAME, ""): row for row in commands}
    parts = [
        PY_HEADER,
        f"COMMANDS = {json.dumps(commands, indent=4, sort_keys=False)}\n\n",
        f"COMMANDS_BY_NAME = {json.dumps(commands_by_name, indent=4, sort_keys=True)}\n\n",
        f"HOST_UI_SECTIONS = {json.dumps(sections, indent=4, sort_keys=False)}\n",
    ]
    path.write_text("".join(parts), encoding="utf-8")


def main() -> None:
    """
    NAME
        main - Generate mirrored host-side robot local command artifacts.
    """
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    inventory = _load_inventory()
    sections = _build_sections(inventory)
    _write_json(JSON_PATH, inventory)
    _write_python(PY_PATH, inventory, sections)
    print(f"Wrote {JSON_PATH}")
    print(f"Wrote {PY_PATH}")


if __name__ == "__main__":
    main()
