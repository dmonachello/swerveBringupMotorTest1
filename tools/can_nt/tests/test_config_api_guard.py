from __future__ import annotations

import unittest

from tools.can_nt.scripts.config_api_guard import (
    EXIT_FAILED,
    EXIT_OK,
    main,
    scan_text,
)


class ConfigApiGuardTests(unittest.TestCase):
    def test_flags_direct_path_helper_outside_allowed_files(self) -> None:
        source = "from tools.common.paths import profiles_canonical_path\npath = profiles_canonical_path()\n"

        violations = scan_text(source, "tools/can_nt/example.py")

        self.assertEqual(
            [
                "tools/can_nt/example.py:2: direct path helper 'profiles_canonical_path' is not allowed here"
            ],
            violations,
        )

    def test_allows_path_helper_inside_allowed_file(self) -> None:
        source = "path = profiles_canonical_path()\n"

        violations = scan_text(source, "tools/common/config_lifecycle/service.py")

        self.assertEqual([], violations)

    def test_flags_direct_read_json_with_literal_bringup_path(self) -> None:
        source = (
            "from pathlib import Path\n"
            "from tools.common.json_io import read_json\n"
            "payload = read_json(Path('src') / 'main' / 'deploy' / 'bringup_system.json')\n"
        )

        violations = scan_text(source, "tools/can_nt/example.py")

        self.assertEqual(
            [
                "tools/can_nt/example.py:3: direct read_json(...) targeting bringup_system.json bypasses ConfigRepository"
            ],
            violations,
        )

    def test_flags_direct_write_json_with_tainted_name(self) -> None:
        source = (
            "from pathlib import Path\n"
            "from tools.common.json_io import write_json\n"
            "target_path = Path('src') / 'main' / 'deploy' / 'bringup_system.json'\n"
            "write_json(target_path, {'ok': True})\n"
        )

        violations = scan_text(source, "tools/can_nt/example.py")

        self.assertEqual(
            [
                "tools/can_nt/example.py:4: direct write_json(...) targeting bringup_system.json bypasses ConfigRepository"
            ],
            violations,
        )

    def test_allows_unrelated_json_read(self) -> None:
        source = (
            "from pathlib import Path\n"
            "from tools.common.json_io import read_json\n"
            "payload = read_json(Path('templates') / 'demo.json')\n"
        )

        violations = scan_text(source, "tools/can_nt/example.py")

        self.assertEqual([], violations)

    def test_main_passes_when_no_violations(self) -> None:
        import tools.can_nt.scripts.config_api_guard as guard

        original = guard.python_source_paths
        original_scan = guard.scan_path
        try:
            guard.python_source_paths = lambda: []  # type: ignore[assignment]
            guard.scan_path = lambda path: []  # type: ignore[assignment]
            exit_code = main([])
        finally:
            guard.python_source_paths = original  # type: ignore[assignment]
            guard.scan_path = original_scan  # type: ignore[assignment]

        self.assertEqual(EXIT_OK, exit_code)

    def test_main_fails_when_violations_exist(self) -> None:
        import tools.can_nt.scripts.config_api_guard as guard

        original = guard.python_source_paths
        original_scan = guard.scan_path
        try:
            guard.python_source_paths = lambda: ["ignored.py"]  # type: ignore[assignment]
            guard.scan_path = lambda path: ["tools/can_nt/example.py:2: violation"]  # type: ignore[assignment]
            exit_code = main([])
        finally:
            guard.python_source_paths = original  # type: ignore[assignment]
            guard.scan_path = original_scan  # type: ignore[assignment]

        self.assertEqual(EXIT_FAILED, exit_code)


if __name__ == "__main__":
    unittest.main()
