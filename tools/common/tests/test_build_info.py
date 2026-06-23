"""
NAME
    test_build_info.py - Focused tests for shared build metadata output.
"""

import unittest

from tools.common.build_info import (
    BUILD_LABEL_CODE_REVISION,
    BUILD_LABEL_REVISION,
    BUILD_LABEL_WORKSPACE_REVISION,
    KEY_BUILD_FIELDS,
    KEY_BUILD_LABEL,
    KEY_BUILD_VALUE,
    build_info_payload,
    build_lines,
)


class BuildInfoTests(unittest.TestCase):
    def test_build_lines_include_revision_first(self) -> None:
        lines = build_lines()
        self.assertGreater(len(lines), 2)
        self.assertTrue(lines[0].startswith(f"{BUILD_LABEL_REVISION}: "))
        self.assertTrue(lines[1].startswith(f"{BUILD_LABEL_WORKSPACE_REVISION}: "))
        self.assertTrue(lines[2].startswith(f"{BUILD_LABEL_CODE_REVISION}: "))

    def test_build_payload_includes_non_empty_revision_field(self) -> None:
        payload = build_info_payload()
        fields = payload[KEY_BUILD_FIELDS]
        self.assertGreater(len(fields), 2)
        self.assertEqual(BUILD_LABEL_REVISION, fields[0][KEY_BUILD_LABEL])
        self.assertTrue(str(fields[0][KEY_BUILD_VALUE]).strip())
        self.assertEqual(BUILD_LABEL_WORKSPACE_REVISION, fields[1][KEY_BUILD_LABEL])
        self.assertTrue(str(fields[1][KEY_BUILD_VALUE]).strip())
        self.assertEqual(BUILD_LABEL_CODE_REVISION, fields[2][KEY_BUILD_LABEL])
        self.assertTrue(str(fields[2][KEY_BUILD_VALUE]).strip())


if __name__ == "__main__":
    unittest.main()
