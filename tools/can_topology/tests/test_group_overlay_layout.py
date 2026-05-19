from __future__ import annotations

import unittest

from tools.common.topology_draw import draw_group_overlays


class _FakeCanvas:
    def create_rectangle(self, *args, **kwargs):  # noqa: ANN002, ANN003
        _ = (args, kwargs)
        return 1

    def create_text(self, *args, **kwargs):  # noqa: ANN002, ANN003
        _ = (args, kwargs)
        return 1

    def tag_lower(self, *args, **kwargs):  # noqa: ANN002, ANN003
        _ = (args, kwargs)

    def tag_raise(self, *args, **kwargs):  # noqa: ANN002, ANN003
        _ = (args, kwargs)


class GroupOverlayLayoutTests(unittest.TestCase):
    @staticmethod
    def _rects_overlap(left, right) -> bool:
        left_x0, left_y0, left_x1, left_y1 = left
        right_x0, right_y0, right_x1, right_y1 = right
        return not (
            left_x1 <= right_x0
            or left_x0 >= right_x1
            or left_y1 <= right_y0
            or left_y0 >= right_y1
        )

    @staticmethod
    def _is_adjacent(label_bounds, group_bounds, max_gap: float = 12.0) -> bool:
        lx0, ly0, lx1, ly1 = label_bounds
        gx0, gy0, gx1, gy1 = group_bounds
        horizontal_overlap = not (lx1 <= gx0 or lx0 >= gx1)
        vertical_overlap = not (ly1 <= gy0 or ly0 >= gy1)
        above = horizontal_overlap and abs(ly1 - gy0) <= max_gap
        below = horizontal_overlap and abs(ly0 - gy1) <= max_gap
        left = vertical_overlap and abs(lx1 - gx0) <= max_gap
        right = vertical_overlap and abs(lx0 - gx1) <= max_gap
        return above or below or left or right

    def test_overlapping_group_labels_are_stacked(self) -> None:
        canvas = _FakeCanvas()
        label_bounds = {
            "A": (100.0, 100.0, 140.0, 140.0),
            "B": (180.0, 100.0, 220.0, 140.0),
        }
        groups = [
            {"name": "group1", "members": [{"device": "A"}, {"device": "B"}]},
            {"name": "group2", "members": [{"device": "A"}, {"device": "B"}]},
        ]

        overlays = draw_group_overlays(canvas, label_bounds, groups, zoom=1.0)

        self.assertEqual(2, len(overlays))
        self.assertNotEqual(overlays[0]["label_bounds"], overlays[1]["label_bounds"])
        self.assertFalse(self._rects_overlap(overlays[0]["label_bounds"], overlays[1]["label_bounds"]))
        self.assertTrue(self._is_adjacent(overlays[0]["label_bounds"], overlays[0]["bounds"]))
        self.assertTrue(self._is_adjacent(overlays[1]["label_bounds"], overlays[1]["bounds"]))

    def test_group_label_can_remain_inside_parent_group_region(self) -> None:
        canvas = _FakeCanvas()
        label_bounds = {
            "A": (100.0, 100.0, 140.0, 140.0),
            "B": (180.0, 100.0, 220.0, 140.0),
            "C": (120.0, 120.0, 160.0, 160.0),
        }
        groups = [
            {"name": "wide", "members": [{"device": "A"}, {"device": "B"}]},
            {"name": "nested", "members": [{"device": "C"}]},
        ]

        overlays = draw_group_overlays(canvas, label_bounds, groups, zoom=1.0)

        self.assertEqual(2, len(overlays))
        first_bounds = overlays[0]["bounds"]
        second_label = overlays[1]["label_bounds"]
        self.assertTrue(self._rects_overlap(second_label, first_bounds))
        self.assertTrue(self._is_adjacent(second_label, overlays[1]["bounds"]))

    def test_group_label_can_move_below_own_group_when_above_is_blocked(self) -> None:
        canvas = _FakeCanvas()
        label_bounds = {
            "TopA": (100.0, 100.0, 140.0, 140.0),
            "TopB": (180.0, 100.0, 220.0, 140.0),
            "BottomA": (100.0, 220.0, 140.0, 260.0),
            "BottomB": (180.0, 220.0, 220.0, 260.0),
        }
        groups = [
            {"name": "top", "members": [{"device": "TopA"}, {"device": "TopB"}]},
            {"name": "bottom", "members": [{"device": "BottomA"}, {"device": "BottomB"}]},
        ]

        overlays = draw_group_overlays(canvas, label_bounds, groups, zoom=1.0)

        self.assertEqual(2, len(overlays))
        bottom_bounds = overlays[1]["bounds"]
        bottom_label = overlays[1]["label_bounds"]
        self.assertTrue(self._is_adjacent(bottom_label, bottom_bounds))


if __name__ == "__main__":
    unittest.main()
