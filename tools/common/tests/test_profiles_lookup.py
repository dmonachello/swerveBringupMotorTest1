from __future__ import annotations

import unittest

from tools.common.profiles import find_device_by_label, list_profile_names, resolve_active_profile


class ProfilesLookupTests(unittest.TestCase):
    """Validate shared profile lookup helpers."""

    def test_list_profile_names_returns_sorted_names(self) -> None:
        payload = {
            "profiles": {
                "beta": {},
                "alpha": {},
            }
        }
        self.assertEqual(list_profile_names(payload), ["alpha", "beta"])

    def test_resolve_active_profile_prefers_selected_name(self) -> None:
        payload = {
            "defaultProfile": "home",
            "profiles": {"home": {}, "practice": {}},
        }
        self.assertEqual(resolve_active_profile(payload, "practice"), "practice")

    def test_find_device_by_label_matches_case_insensitive(self) -> None:
        payload = {
            "devices": [
                {"label": "FL DRIVE", "id": 1},
            ]
        }
        entry = find_device_by_label(payload, "fl drive")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.get("id"), 1)


if __name__ == "__main__":
    unittest.main()

