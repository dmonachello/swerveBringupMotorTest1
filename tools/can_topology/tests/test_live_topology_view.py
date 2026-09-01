from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from tools.can_topology import live_topology_view as live_view_module
from tools.can_nt.ui_theme import (
    UI_THEME_FIELD_CONSOLE_DARK,
    get_ui_theme_palette,
)
from tools.common import topology_draw


class _BoolVarStub:
    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self) -> bool:
        return self.value

    def set(self, value: bool) -> None:
        self.value = bool(value)


class _StringVarStub:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = str(value)


class _NodeStub:
    def __init__(self, label: str, can_id: int) -> None:
        self.label = label
        self.can_id = can_id


class _LabelStub:
    def __init__(self) -> None:
        self.text = ""
        self.bg = None
        self.fg = None

    def configure(self, **kwargs) -> None:
        if "text" in kwargs:
            self.text = str(kwargs["text"])
        if "bg" in kwargs:
            self.bg = kwargs["bg"]
        if "fg" in kwargs:
            self.fg = kwargs["fg"]


class _PanelStub:
    def __init__(self) -> None:
        self.bg = None
        self.highlightbackground = None

    def configure(self, **kwargs) -> None:
        if "bg" in kwargs:
            self.bg = kwargs["bg"]
        if "highlightbackground" in kwargs:
            self.highlightbackground = kwargs["highlightbackground"]


class _CanvasStub:
    def __init__(self, width: int = 800, height: int = 600) -> None:
        self.mark = None
        self.drag = None
        self.xview = None
        self.yview = None
        self.scrollregion = "0 0 1000 1000"
        self.width = width
        self.height = height

    def scan_mark(self, x: int, y: int) -> None:
        self.mark = (x, y)

    def scan_dragto(self, x: int, y: int, gain: int = 1) -> None:
        self.drag = (x, y, gain)

    def cget(self, key: str) -> str:
        if key == "scrollregion":
            return self.scrollregion
        return ""

    def configure(self, **kwargs) -> None:
        if "scrollregion" in kwargs:
            region = kwargs["scrollregion"]
            self.scrollregion = " ".join(str(value) for value in region)

    def winfo_width(self) -> int:
        return self.width

    def winfo_height(self) -> int:
        return self.height

    def canvasx(self, value: int) -> float:
        return float(value)

    def canvasy(self, value: int) -> float:
        return float(value)

    def xview_moveto(self, fraction: float) -> None:
        self.xview = fraction

    def yview_moveto(self, fraction: float) -> None:
        self.yview = fraction


class _ShapeCanvasStub:
    def __init__(self) -> None:
        self.calls = []
        self._next_id = 1

    def _record(self, kind: str, *args, **kwargs) -> int:
        item_id = self._next_id
        self._next_id += 1
        self.calls.append((kind, args, kwargs))
        return item_id

    def create_polygon(self, *args, **kwargs) -> int:
        return self._record("polygon", *args, **kwargs)

    def create_rectangle(self, *args, **kwargs) -> int:
        return self._record("rectangle", *args, **kwargs)


class LiveTopologyViewTests(unittest.TestCase):
    """
    NAME
        LiveTopologyViewTests - Validate live topology filter behavior.
    """

    def _make_view(self) -> live_view_module.LiveTopologyView:
        view = live_view_module.LiveTopologyView.__new__(live_view_module.LiveTopologyView)
        view._profile_name = "demo"
        view._fit_on_load = False
        view._fit_pending = False
        view._manage_runtime_notice_internally = True
        view._nodes = []
        view._profile_device_labels = []
        view._diagram_meta = {}
        view._bridge_groups = []
        view._runtime_groups = []
        view._runtime_state = {}
        view._presence_overrides = {}
        view._overlay_lens = live_view_module.TOPOLOGY_LENS_RUNTIME
        view._evidence_state = {}
        view._passive_detail_state = {}
        view._evidence_detail_state = {}
        view._visibility_enabled = False
        view._visibility_state = {}
        view._visibility_sources = {}
        view._visibility_fingerprint = None
        view._selected_label = None
        view._selected_enabled = None
        view._bus_offsets = [0.0]
        view._bus_spacing = 160.0
        view._bus_lefts = []
        view._bus_rights = []
        view._pan_y = 0.0
        view._zoom = 1.0
        view._node_bounds = {}
        view._selected_node = None
        view._use_diagram_layout = False
        view._ethernet_links = []
        view._can_links = []
        view._device_links = []
        view._show_groups = True
        view._runtime_fingerprint = None
        view._runtime_state_seen = False
        view._runtime_state_notice_text = ""
        view._runtime_event_notice_text = ""
        view._theme_name = live_view_module.UI_THEME_DEFAULT
        view._theme_palette = get_ui_theme_palette(view._theme_name)
        view._active_group_edit_action_state = live_view_module.ACTION_STATE_ALLOWED
        view._override_action_state = live_view_module.ACTION_STATE_ALLOWED
        view._active_group_summary_var = None
        view._active_group_status_var = None
        view._detail_vars = {}
        view._group_inspector_name = ""
        view._group_inspector_targets = []
        view._selection_inspector_mode = live_view_module.GROUP_INSPECTOR_MODE_DEVICE
        view._group_inspector_frame = None
        view._detail_device_frame = None
        view._manual_test_observations = {}
        view._synthetic_selection_detail = {}
        view._connection_filter_vars = {
            key: _BoolVarStub(True) for key in live_view_module.CONNECTION_FILTERS_ORDER
        }
        view._status_label = _LabelStub()
        view._canvas = _CanvasStub()
        view.after_idle = lambda callback: callback()
        view.after = lambda _delay_ms, callback: callback()
        view.update_idletasks = lambda: None
        view._redraw = lambda *_args, **_kwargs: None
        return view

    def test_active_group_checkbox_toggle_uses_shared_action_gate(self) -> None:
        view = self._make_view()
        calls = []
        view._on_active_group_member_toggled_cb = lambda label, enabled: calls.append((label, enabled))
        view._active_group_member_update_in_progress = False
        view._active_group_member_vars = {"falcon 9": _BoolVarStub(True)}
        view.set_active_group_edit_action_state(
            live_view_module.HostActionAccessState(
                allowed=False,
                blocked_reason="blocked",
                refresh_before_action=False,
                refresh_after_action=False,
                refresh_when_blocked=False,
            )
        )

        view._on_active_group_member_checkbox_toggled("FALCON 9")

        self.assertEqual([], calls)

    def test_active_group_checkbox_toggle_does_not_apply_singleton_snapback_heuristic(self) -> None:
        view = self._make_view()
        calls = []
        view._on_active_group_member_toggled_cb = lambda label, enabled: calls.append((label, enabled))
        view._active_group_member_update_in_progress = False
        variable = _BoolVarStub(False)
        view._active_group_member_vars = {"pdp": variable}
        view.set_active_group_edit_action_state(live_view_module.ACTION_STATE_ALLOWED)
        view._runtime_state = {"pdp": {"instantiated": True, "lifecycleKind": "SINGLETON"}}

        view._on_active_group_member_checkbox_toggled("pdp")

        self.assertEqual([("pdp", False)], calls)
        self.assertFalse(variable.get())

    def test_display_active_group_uses_configured_profile_fallback_when_runtime_membership_is_empty(self) -> None:
        view = self._make_view()
        view._configured_active_group_member_labels = ("FALCON 9", "SPARKMAX/NEO 25")
        view._bridge_groups = []
        view._runtime_groups = [{"name": "active-group", "members": []}]

        active_group = view._display_active_group()

        self.assertIsInstance(active_group, dict)
        self.assertEqual(
            ["FALCON 9", "SPARKMAX/NEO 25"],
            live_view_module.group_member_labels(active_group, enabled_only=False),
        )

    def test_override_action_uses_shared_action_gate(self) -> None:
        view = self._make_view()
        calls = []
        view._selected_node = type("NodeStub", (), {"label": "FALCON 9", "can_id": 9})()
        view._on_override_action_cb = lambda label, action: calls.append((label, action))
        view.set_override_action_state(
            live_view_module.HostActionAccessState(
                allowed=False,
                blocked_reason="blocked",
                refresh_before_action=False,
                refresh_after_action=False,
                refresh_when_blocked=False,
            )
        )

        view._invoke_override_action("instantiate")

        self.assertEqual([], calls)

    def test_update_details_shows_motor_spec_warning_fields(self) -> None:
        view = self._make_view()
        view._detail_vars = {
            live_view_module.DETAIL_KEY_LABEL: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_CAN_ID: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_PRESENCE: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_PRESENCE_STATUS: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_PRESENCE_AGE: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_PRESENCE_SOURCE: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_FULL_PROBE_BUCKET: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_FULL_PROBE_AGE: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_FULL_PROBE_SCORE: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_FULL_PROBE_STATUS: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_FULL_PROBE_MESSAGE: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_GROUP_MEMBER: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_SCOPE_ACTIVE: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_INSTANTIATED: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_LIFECYCLE_STATE: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_TESTABLE: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_OVERRIDE_ACTIVE: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_OVERRIDE_ORIGINATED: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_OVERRIDE_FAILURE: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_NOT_TESTABLE_REASON: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_LAST_SEEN: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_CURRENT_A: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_CURRENT_AVG_A: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_CURRENT_PEAK_A: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_CURRENT_NONZERO: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_CURRENT_SAMPLES: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_CMD_DUTY: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_APPLIED_DUTY: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_VEL_RPM: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_POSITION_ROT: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_POSITION_DELTA_ROT: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_TEMP_C: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_MOTOR_SPEC_MATCH: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_MOTOR_SPEC_MODEL: _StringVarStub("--"),
            live_view_module.DETAIL_KEY_SELECTED: _StringVarStub("--"),
        }
        view._selected_node = _NodeStub("FALCON 9", 9)
        view._runtime_state = {
            "falcon 9": {
                "presenceConfidence": 1.0,
                "attachments": [
                    {"type": "motorSpec", "matched": False, "requestedModel": "Unknown Motor"}
                ],
            }
        }

        view._update_details()

        self.assertEqual("missing", view._detail_vars[live_view_module.DETAIL_KEY_MOTOR_SPEC_MATCH].get())
        self.assertEqual("Unknown Motor", view._detail_vars[live_view_module.DETAIL_KEY_MOTOR_SPEC_MODEL].get())

    def _attach_detail_vars(self, view: live_view_module.LiveTopologyView) -> None:
        view._detail_vars = {
            key: _StringVarStub("--")
            for key in (
                live_view_module.DETAIL_KEY_LABEL,
                live_view_module.DETAIL_KEY_CAN_ID,
                live_view_module.DETAIL_KEY_PRESENCE,
                live_view_module.DETAIL_KEY_PRESENCE_STATUS,
                live_view_module.DETAIL_KEY_PRESENCE_AGE,
                live_view_module.DETAIL_KEY_PRESENCE_SOURCE,
                live_view_module.DETAIL_KEY_FULL_PROBE_BUCKET,
                live_view_module.DETAIL_KEY_FULL_PROBE_AGE,
                live_view_module.DETAIL_KEY_FULL_PROBE_SCORE,
                live_view_module.DETAIL_KEY_FULL_PROBE_STATUS,
                live_view_module.DETAIL_KEY_FULL_PROBE_MESSAGE,
                live_view_module.DETAIL_KEY_GROUP_MEMBER,
                live_view_module.DETAIL_KEY_SCOPE_ACTIVE,
                live_view_module.DETAIL_KEY_INSTANTIATED,
                live_view_module.DETAIL_KEY_LIFECYCLE_STATE,
                live_view_module.DETAIL_KEY_TESTABLE,
                live_view_module.DETAIL_KEY_OVERRIDE_ACTIVE,
                live_view_module.DETAIL_KEY_OVERRIDE_ORIGINATED,
                live_view_module.DETAIL_KEY_OVERRIDE_FAILURE,
                live_view_module.DETAIL_KEY_NOT_TESTABLE_REASON,
                live_view_module.DETAIL_KEY_LAST_SEEN,
                live_view_module.DETAIL_KEY_CURRENT_A,
                live_view_module.DETAIL_KEY_CURRENT_AVG_A,
                live_view_module.DETAIL_KEY_CURRENT_PEAK_A,
                live_view_module.DETAIL_KEY_CURRENT_NONZERO,
                live_view_module.DETAIL_KEY_CURRENT_SAMPLES,
                live_view_module.DETAIL_KEY_CMD_DUTY,
                live_view_module.DETAIL_KEY_APPLIED_DUTY,
                live_view_module.DETAIL_KEY_VEL_RPM,
                live_view_module.DETAIL_KEY_POSITION_ROT,
                live_view_module.DETAIL_KEY_POSITION_DELTA_ROT,
                live_view_module.DETAIL_KEY_TEMP_C,
                live_view_module.DETAIL_KEY_MOTOR_SPEC_MATCH,
                live_view_module.DETAIL_KEY_MOTOR_SPEC_MODEL,
                live_view_module.DETAIL_KEY_SELECTED,
            )
        }

    def test_visibility_lens_selection_details_use_passive_snapshot(self) -> None:
        view = self._make_view()
        self._attach_detail_vars(view)
        view._selected_node = type("NodeStub", (), {"label": "roborio", "can_id": 0})()
        view._runtime_state = {
            "roborio": {
                "presenceConfidence": 0.0,
                "attachments": [
                    {"type": "presenceCheck", "source": "localSnapshot", "status": "warning"},
                ],
                "lifecycleState": "in-scope-stale",
                "instantiated": False,
                "testable": False,
            }
        }
        view.set_passive_detail_snapshot(
            {
                "roborio": {
                    live_view_module.DETAIL_SNAPSHOT_PRESENCE: "0.78",
                    live_view_module.DETAIL_SNAPSHOT_PRESENCE_STATUS: "medium",
                    live_view_module.DETAIL_SNAPSHOT_PRESENCE_AGE: "0.0s ago",
                    live_view_module.DETAIL_SNAPSHOT_PRESENCE_SOURCE: "passiveCan",
                    live_view_module.DETAIL_SNAPSHOT_LAST_SEEN: "0.0s ago",
                }
            }
        )

        view.set_overlay_lens(live_view_module.TOPOLOGY_LENS_VISIBILITY)

        self.assertEqual("0.78", view._detail_vars[live_view_module.DETAIL_KEY_PRESENCE].get())
        self.assertEqual(
            "medium",
            view._detail_vars[live_view_module.DETAIL_KEY_PRESENCE_STATUS].get(),
        )
        self.assertEqual(
            "passiveCan",
            view._detail_vars[live_view_module.DETAIL_KEY_PRESENCE_SOURCE].get(),
        )
        self.assertEqual(
            "in-scope-stale",
            view._detail_vars[live_view_module.DETAIL_KEY_LIFECYCLE_STATE].get(),
        )

    def test_visibility_lens_selection_details_use_synthetic_payload_when_no_node_matches(self) -> None:
        view = self._make_view()
        self._attach_detail_vars(view)
        view._selected_node = None
        view.set_overlay_lens(live_view_module.TOPOLOGY_LENS_VISIBILITY)

        view.set_synthetic_selection_detail(
            {
                live_view_module.DETAIL_KEY_LABEL: "UNPROFILED_DEVICE_50207",
                live_view_module.DETAIL_KEY_CAN_ID: "7",
                live_view_module.DETAIL_KEY_PRESENCE_STATUS: "unrecognized-passive",
                live_view_module.DETAIL_KEY_PRESENCE_SOURCE: "passiveCan",
                live_view_module.DETAIL_KEY_SELECTED: "passive-only",
            }
        )

        self.assertEqual(
            "UNPROFILED_DEVICE_50207",
            view._detail_vars[live_view_module.DETAIL_KEY_LABEL].get(),
        )
        self.assertEqual("7", view._detail_vars[live_view_module.DETAIL_KEY_CAN_ID].get())
        self.assertEqual(
            "unrecognized-passive",
            view._detail_vars[live_view_module.DETAIL_KEY_PRESENCE_STATUS].get(),
        )
        self.assertEqual(
            "passive-only",
            view._detail_vars[live_view_module.DETAIL_KEY_SELECTED].get(),
        )

    def test_evidence_lens_selection_details_use_interpreted_snapshot(self) -> None:
        view = self._make_view()
        self._attach_detail_vars(view)
        view._selected_node = type("NodeStub", (), {"label": "FALCON 9", "can_id": 9})()
        view._runtime_state = {
            "falcon 9": {
                "presenceConfidence": 0.0,
                "attachments": [
                    {"type": "presenceCheck", "source": "localSnapshot", "status": "warning"},
                ],
                "lifecycleState": "defined",
                "instantiated": False,
                "testable": False,
            }
        }
        view.set_evidence_detail_snapshot(
            {
                "falcon 9": {
                    live_view_module.DETAIL_SNAPSHOT_PRESENCE: "1.00",
                    live_view_module.DETAIL_SNAPSHOT_PRESENCE_STATUS: "present",
                    live_view_module.DETAIL_SNAPSHOT_PRESENCE_AGE: "fresh",
                    live_view_module.DETAIL_SNAPSHOT_PRESENCE_SOURCE: "interpretedEvidence",
                }
            }
        )

        view.set_overlay_lens(live_view_module.TOPOLOGY_LENS_EVIDENCE)

        self.assertEqual("1.00", view._detail_vars[live_view_module.DETAIL_KEY_PRESENCE].get())
        self.assertEqual(
            "present",
            view._detail_vars[live_view_module.DETAIL_KEY_PRESENCE_STATUS].get(),
        )
        self.assertEqual(
            "interpretedEvidence",
            view._detail_vars[live_view_module.DETAIL_KEY_PRESENCE_SOURCE].get(),
        )
        self.assertEqual(
            "defined",
            view._detail_vars[live_view_module.DETAIL_KEY_LIFECYCLE_STATE].get(),
        )

    def test_filter_helpers_toggle_all_and_none(self) -> None:
        view = self._make_view()

        view._disable_all_connection_filters()
        self.assertEqual(view._active_connection_filters(), set())

        view._enable_all_connection_filters()
        self.assertEqual(
            view._active_connection_filters(),
            set(live_view_module.CONNECTION_FILTERS_ORDER),
        )

    def test_refresh_runtime_notice_waits_for_runtime_state_before_showing_ready(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = False
        view._runtime_state_notice_text = ""
        view._runtime_event_notice_text = ""
        view._runnable_scope_headline_var = _StringVarStub("")
        view._runnable_scope_detail_var = _StringVarStub("")
        view._notice_panel = _PanelStub()
        view._notice_title_label = _LabelStub()
        view._notice_headline_label = _LabelStub()
        view._notice_detail_label = _LabelStub()

        view._refresh_runtime_notice()

        self.assertEqual("WAITING FOR STATE", view._runnable_scope_headline_var.get())
        self.assertEqual(
            "waiting for robot runtime state",
            view._runnable_scope_detail_var.get(),
        )

    def test_update_runtime_state_marks_runtime_state_seen(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = False
        view._runnable_scope_headline_var = _StringVarStub("")
        view._runnable_scope_detail_var = _StringVarStub("")
        view._notice_panel = _PanelStub()
        view._notice_title_label = _LabelStub()
        view._notice_headline_label = _LabelStub()
        view._notice_detail_label = _LabelStub()
        view._update_details = lambda: None

        view.update_runtime_state({"enabled": True, "devices": []})

        self.assertTrue(view._runtime_state_seen)

    def test_update_runtime_state_skips_internal_notice_when_host_managed(self) -> None:
        view = self._make_view()
        view._manage_runtime_notice_internally = False
        calls = []
        view._apply_runtime_notice_from_state = (
            lambda *_args: calls.append("called")
        )
        view._update_details = lambda: None

        view.update_runtime_state(
            {
                "enabled": False,
                "estopped": False,
                "runtimeActive": True,
                "controlledLifecycleActive": True,
                "devices": [],
                "groups": [],
            }
        )

        self.assertEqual([], calls)

    def test_active_group_members_not_editable_before_runtime_state(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = False
        view._controlled_lifecycle_active = False

        self.assertFalse(view._active_group_members_editable())

    def test_active_group_members_not_editable_during_controlled_lifecycle(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = True
        view._controlled_lifecycle_active = True

        self.assertFalse(view._active_group_members_editable())

    def test_active_group_members_not_editable_during_transition_resync(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = True
        view._controlled_lifecycle_active = False
        view._scope_transition_pending = True

        self.assertFalse(view._active_group_members_editable())

    def test_active_group_members_editable_after_runtime_state_when_unlocked(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = True
        view._controlled_lifecycle_active = False

        self.assertTrue(view._active_group_members_editable())

    def test_active_scope_eligible_labels_use_full_profile_device_list(self) -> None:
        view = self._make_view()
        view._profile_device_labels = [
            "SPARKMAX/NEO 25",
            "FALCON 9",
            "controller0",
            "pdp",
            "roborio",
            "lmtSw0",
        ]
        view._nodes = [
            live_view_module.LiveNode(
                key=1,
                category="falcons",
                label="FALCON 9",
                can_id=9,
                bus_index=0,
                row=0,
                x=0.0,
                device_type="2",
            ),
        ]

        self.assertEqual(
            [
                "controller0",
                "FALCON 9",
                "lmtSw0",
                "pdp",
                "roborio",
                "SPARKMAX/NEO 25",
            ],
            view._active_scope_eligible_labels(),
        )

    def test_active_scope_eligible_labels_fallback_to_nodes_when_profile_list_missing(self) -> None:
        view = self._make_view()
        view._profile_device_labels = []
        view._nodes = [
            live_view_module.LiveNode(
                key=1,
                category="falcons",
                label="FALCON 9",
                can_id=9,
                bus_index=0,
                row=0,
                x=0.0,
                device_type="2",
            ),
            live_view_module.LiveNode(
                key=2,
                category="pdp",
                label="pdp",
                can_id=20,
                bus_index=0,
                row=0,
                x=1.0,
                device_type="8",
            ),
        ]

        self.assertEqual(["FALCON 9", "pdp"], view._active_scope_eligible_labels())

    def test_resolved_active_group_state_locks_instantiated_singleton_members(self) -> None:
        group_state = live_view_module.resolve_group_state_from_member_map(
            name="active-group",
            member_map={"pdp": {"label": "pdp", "enabled": True}},
            runtime_state_by_label={
                "pdp": {
                    "instantiated": False,
                    "lifecycleState": "controlled-instantiated",
                    "lifecycleKind": "SINGLETON",
                }
            },
            primary_label="pdp",
            scope_active=False,
        )

        self.assertTrue(group_state.members[0].locked)

    def test_runtime_notice_requires_activation_before_manual_run(self) -> None:
        view = self._make_view()
        notices = []
        view.set_runtime_state_notice = lambda text, level="warn": notices.append((text, level))
        view.clear_runtime_state_notice = lambda: notices.append(("__clear__", "clear"))

        view._apply_runtime_notice_from_state(False, False, True, False, "teleop")

        self.assertEqual(
            [("Press Runtime Activate.", "warn")],
            notices,
        )

    def test_runtime_notice_is_ready_when_controlled_scope_is_active(self) -> None:
        view = self._make_view()
        notices = []
        view.set_runtime_state_notice = lambda text, level="warn": notices.append((text, level))
        view.clear_runtime_state_notice = lambda: notices.append(("__clear__", "clear"))

        view._apply_runtime_notice_from_state(False, True, True, False, "teleop")

        self.assertEqual([("__clear__", "clear")], notices)

    def test_apply_runnable_scope_state_clears_stale_disabled_event_when_scope_is_ready(self) -> None:
        view = self._make_view()
        view._runtime_event_notice_text = "Robot disabled."
        clears = []
        view.clear_runtime_notice = lambda: clears.append("event")
        notices = []
        view.set_runtime_state_notice = lambda text, level="warn": notices.append((text, level))
        view.clear_runtime_state_notice = lambda: notices.append(("__clear__", "clear"))
        state = live_view_module.resolve_runnable_scope_state(
            scope_kind=live_view_module.RUNNABLE_SCOPE_KIND_MANUAL,
            local_selected_profile="test_minimal_25_9",
            local_profile_required=False,
            tcp_connected=True,
            runtime_state_seen=True,
            stale_state=False,
            robot_enabled=True,
            robot_estopped=False,
            robot_mode="teleop",
            manual_group_empty=False,
            scope_active=True,
        )

        view.apply_runnable_scope_state(state)

        self.assertEqual(["event"], clears)
        self.assertEqual([("__clear__", "clear")], notices)

    def test_runtime_notice_warning_uses_attention_palette(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = True
        view._runnable_scope_headline_var = _StringVarStub("")
        view._runnable_scope_detail_var = _StringVarStub("")
        view._notice_panel = _PanelStub()
        view._notice_title_label = _LabelStub()
        view._notice_headline_label = _LabelStub()
        view._notice_detail_label = _LabelStub()
        view.set_runtime_state_notice("Activate Group first.", "warn")

        self.assertEqual(
            live_view_module.RUNNABLE_PANEL_INACTIVE_BG,
            view._notice_panel.bg,
        )

    def test_runtime_notice_error_uses_error_palette(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = True
        view._runnable_scope_headline_var = _StringVarStub("")
        view._runnable_scope_detail_var = _StringVarStub("")
        view._notice_panel = _PanelStub()
        view._notice_title_label = _LabelStub()
        view._notice_headline_label = _LabelStub()
        view._notice_detail_label = _LabelStub()
        view.set_runtime_state_notice("Robot E-Stop. Manual run blocked.", "error")

        self.assertEqual(
            live_view_module.RUNNABLE_PANEL_ERROR_BG,
            view._notice_panel.bg,
        )

    def test_set_theme_updates_runtime_notice_palette(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = True
        view._runnable_scope_headline_var = _StringVarStub("")
        view._runnable_scope_detail_var = _StringVarStub("")
        view._notice_panel = _PanelStub()
        view._notice_title_label = _LabelStub()
        view._notice_headline_label = _LabelStub()
        view._notice_detail_label = _LabelStub()

        view.set_theme(UI_THEME_FIELD_CONSOLE_DARK)
        view.set_runtime_state_notice("Blocked.", "warn")

        self.assertEqual(
            get_ui_theme_palette(UI_THEME_FIELD_CONSOLE_DARK).runnable_inactive_bg,
            view._notice_panel.bg,
        )

    def test_evidence_fill_uses_degraded_color_for_conflict_presence_state(self) -> None:
        view = self._make_view()
        node = type("NodeStub", (), {"label": "FALCON 9"})()
        view._evidence_state = {"falcon 9": "conflict"}

        self.assertEqual(
            live_view_module.EVIDENCE_COLOR_DEGRADED,
            view._evidence_fill(node),
        )

    def test_live_fill_uses_warning_color_when_presence_status_is_warning(self) -> None:
        view = self._make_view()
        node = type("NodeStub", (), {"label": "roborio", "interface": "CAN"})()
        view._runtime_state = {
            "roborio": {
                "presenceConfidence": 0.0,
                "attachments": [
                    {"type": "presenceCheck", "status": "warning"},
                ],
            }
        }

        self.assertEqual(
            live_view_module.PRESENCE_COLOR_LOW,
            view._live_fill(node, 0),
        )

    def test_live_fill_uses_neutral_none_color_when_presence_confidence_is_zero_without_error_status(self) -> None:
        view = self._make_view()
        node = type("NodeStub", (), {"label": "pdp", "interface": "CAN"})()
        view._runtime_state = {
            "pdp": {
                "presenceConfidence": 0.0,
            }
        }

        self.assertEqual(
            live_view_module.PRESENCE_COLOR_NONE,
            view._live_fill(node, 0),
        )

    def test_live_fill_uses_error_color_when_presence_status_is_error(self) -> None:
        view = self._make_view()
        node = type("NodeStub", (), {"label": "pdp", "interface": "CAN"})()
        view._runtime_state = {
            "pdp": {
                "presenceConfidence": 0.0,
                "attachments": [
                    {"type": "presenceCheck", "status": "error"},
                ],
            }
        }

        self.assertEqual(
            live_view_module.PRESENCE_COLOR_ERROR,
            view._live_fill(node, 0),
        )

    def test_evidence_lens_uses_interpreted_state_and_ignores_runtime_fill(self) -> None:
        view = self._make_view()
        node = type("NodeStub", (), {"label": "falcon 9", "interface": "CAN"})()
        view._runtime_state = {
            "falcon 9": {
                "presenceConfidence": 0.0,
                "attachments": [
                    {"type": "presenceCheck", "status": "error"},
                ],
            }
        }
        view._evidence_state = {"falcon 9": "present"}
        view.set_overlay_lens(live_view_module.TOPOLOGY_LENS_EVIDENCE)

        self.assertEqual(
            live_view_module.EVIDENCE_COLOR_OK,
            view._live_fill(node, 0),
        )

    def test_set_evidence_snapshot_accepts_structured_snapshot_and_updates_detail_state(
        self,
    ) -> None:
        view = self._make_view()
        self._attach_detail_vars(view)
        view._selected_node = type("NodeStub", (), {"label": "FALCON 9", "can_id": 9})()

        view.set_evidence_snapshot(
            {
                "snapshotType": "interpretedEvidence",
                "devices": {
                    "falcon 9": {
                        "presenceState": "present",
                        "detail": {
                            live_view_module.DETAIL_SNAPSHOT_PRESENCE: "1.00",
                            live_view_module.DETAIL_SNAPSHOT_PRESENCE_STATUS: "present",
                            live_view_module.DETAIL_SNAPSHOT_PRESENCE_AGE: "fresh",
                            live_view_module.DETAIL_SNAPSHOT_PRESENCE_SOURCE: "interpretedEvidence",
                        },
                    }
                },
            }
        )
        view.set_overlay_lens(live_view_module.TOPOLOGY_LENS_EVIDENCE)

        self.assertEqual({"falcon 9": "present"}, view._evidence_state)
        self.assertEqual(
            "present",
            view._detail_vars[live_view_module.DETAIL_KEY_PRESENCE_STATUS].get(),
        )

    def test_evidence_lens_does_not_fallback_to_runtime_when_interpreted_state_missing(self) -> None:
        view = self._make_view()
        node = type("NodeStub", (), {"label": "falcon 9", "interface": "CAN"})()
        view._runtime_state = {
            "falcon 9": {
                "presenceConfidence": 0.0,
                "attachments": [
                    {"type": "presenceCheck", "status": "error"},
                ],
            }
        }
        view.set_overlay_lens(live_view_module.TOPOLOGY_LENS_EVIDENCE)

        self.assertIsNone(view._live_fill(node, 0))

    def test_visibility_lens_uses_visibility_state_and_not_runtime_fill(self) -> None:
        view = self._make_view()
        node = type("NodeStub", (), {"label": "falcon 9", "interface": "CAN", "category": "krakens"})()
        view._runtime_state = {
            "falcon 9": {
                "presenceConfidence": 0.0,
                "attachments": [
                    {"type": "presenceCheck", "status": "error"},
                ],
            }
        }
        view._visibility_state = {"falcon 9": live_view_module.VIS_STATE_ALL}
        view.set_overlay_lens(live_view_module.TOPOLOGY_LENS_VISIBILITY)

        self.assertEqual(
            live_view_module.VIS_COLOR_ALL,
            view._live_fill(node, 0),
        )

    def test_visibility_lens_prefers_passive_none_over_broad_visibility_state(self) -> None:
        view = self._make_view()
        node = type("NodeStub", (), {"label": "falcon 9", "interface": "CAN", "category": "krakens"})()
        view._visibility_state = {"falcon 9": live_view_module.VIS_STATE_ALL}
        view._passive_detail_state = {
            "falcon 9": {
                live_view_module.DETAIL_SNAPSHOT_PRESENCE: "0.00",
                live_view_module.DETAIL_SNAPSHOT_PRESENCE_STATUS: "none",
                live_view_module.DETAIL_SNAPSHOT_PRESENCE_SOURCE: "passiveCan",
            }
        }
        view.set_overlay_lens(live_view_module.TOPOLOGY_LENS_VISIBILITY)

        self.assertEqual(
            live_view_module.VIS_COLOR_NONE,
            view._live_fill(node, 0),
        )

    def test_set_visibility_snapshot_demotes_true_visibility_when_metrics_are_history_only(self) -> None:
        view = self._make_view()
        redraw_calls = []
        view._redraw = lambda *_args, **_kwargs: redraw_calls.append(True)

        view.set_visibility_snapshot(
            {
                live_view_module.VIS_KEY_SOURCES: [
                    {
                        live_view_module.VIS_KEY_ID: "observerA",
                        live_view_module.VIS_KEY_LABEL: "analyzer0",
                        live_view_module.VIS_KEY_AVAILABLE: True,
                    }
                ],
                live_view_module.VIS_KEY_DEVICES: [
                    {
                        live_view_module.VIS_KEY_LABEL: "pdp",
                        live_view_module.VIS_KEY_VISIBILITY: {
                            "observerA": live_view_module.VIS_VISIBLE_TRUE,
                        },
                        live_view_module.VIS_KEY_METRICS: {
                            "observerA": {
                                live_view_module.VIS_KEY_MSG_COUNT: 0,
                                live_view_module.VIS_KEY_LAST_SEEN_MS: 0,
                                live_view_module.VIS_KEY_FRAMES_PER_SEC: 0.0,
                            }
                        },
                    }
                ],
            }
        )

        self.assertEqual(
            live_view_module.VIS_STATE_NONE,
            view._visibility_state["pdp"],
        )
        self.assertEqual(1, len(redraw_calls))

    def test_runtime_notice_prefers_disabled_over_activation_blocker(self) -> None:
        view = self._make_view()
        notices = []
        view.set_runtime_state_notice = lambda text, level="warn": notices.append((text, level))
        view.clear_runtime_state_notice = lambda: notices.append(("__clear__", "clear"))

        view._apply_runtime_notice_from_state(False, False, False, False, "teleop")

        self.assertEqual(
            [("Robot disabled. Enable teleop to run motors.", "info")],
            notices,
        )

    def test_active_group_status_waits_for_runtime_state(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = False

        self.assertEqual(
            live_view_module.ACTIVE_GROUP_STATUS_WAITING_TEXT,
            view._active_group_status_text({"name": "active-group"}, {"falcon 9": {}}),
        )

    def test_active_group_status_reports_empty_group(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = True
        view._controlled_lifecycle_active = False

        self.assertEqual(
            live_view_module.ACTIVE_GROUP_STATUS_EMPTY_TEXT,
            view._active_group_status_text({"name": "active-group"}, {}),
        )

    def test_active_group_status_reports_editable_when_inactive(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = True
        view._controlled_lifecycle_active = False

        self.assertEqual(
            live_view_module.ACTIVE_GROUP_STATUS_EDITABLE_TEXT,
            view._active_group_status_text({"name": "active-group"}, {"falcon 9": {}}),
        )

    def test_active_group_status_reports_ready_when_active_members_present(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = True
        view._controlled_lifecycle_active = True
        view._runtime_state = {
            "falcon 9": {"presenceConfidence": 1.0},
            "sparkmax/neo 25": {"presenceConfidence": 1.0},
        }

        self.assertEqual(
            live_view_module.ACTIVE_GROUP_STATUS_READY_TEXT,
            view._active_group_status_text(
                {"name": "active-group"},
                {"falcon 9": {}, "sparkmax/neo 25": {}},
            ),
        )

    def test_active_group_status_reports_locked_when_active_members_not_present(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = True
        view._controlled_lifecycle_active = True
        view._runtime_state = {"falcon 9": {"presenceConfidence": 0.0}}

        self.assertEqual(
            live_view_module.ACTIVE_GROUP_STATUS_LOCKED_TEXT,
            view._active_group_status_text({"name": "active-group"}, {"falcon 9": {}}),
        )

    def test_active_group_status_reports_resync_during_transition_wait(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = True
        view._controlled_lifecycle_active = True
        view._scope_transition_pending = True
        view._runtime_state = {"falcon 9": {"presenceConfidence": 1.0}}

        self.assertEqual(
            live_view_module.ACTIVE_GROUP_STATUS_RESYNC_TEXT,
            view._active_group_status_text({"name": "active-group"}, {"falcon 9": {}}),
        )

    def test_reload_profile_applies_saved_connection_filters(self) -> None:
        view = self._make_view()

        original_load_payload = live_view_module._load_profiles_payload
        original_load_registry = live_view_module._load_device_registry
        try:
            payload = {
                "default_profile": "demo",
                "profiles": {"demo": {"devices": ["roborio", "motor1"]}},
                "devices": [
                    {"label": "roborio", "deviceInterface": "CAN", "manufacturer": 1, "deviceType": 1, "id": 0},
                    {"label": "motor1", "deviceInterface": "CAN", "manufacturer": 5, "deviceType": 2, "id": 25},
                ],
                "topology": {
                    "profiles": {
                        "demo": {
                            "nodes": [
                                {
                                    "key": 1,
                                    "nodeType": "device",
                                    "deviceRef": "roborio",
                                    "layout": {"bus": 0, "row": 0, "x": 0.0},
                                },
                                {
                                    "key": 2,
                                    "nodeType": "device",
                                    "deviceRef": "motor1",
                                    "layout": {"bus": 0, "row": 0, "x": 100.0},
                                },
                            ],
                            "edges": [
                                {
                                    "id": "edge_1",
                                    "fromNode": 1,
                                    "fromPort": "right",
                                    "toNode": 2,
                                    "toPort": "left",
                                    "edgeType": "can_trunk",
                                }
                            ],
                            "view": {
                                "connectionFilters": ["can", "power"],
                            },
                        }
                    }
                },
            }
            live_view_module._load_profiles_payload = lambda: (payload, "")
            live_view_module._load_device_registry = lambda _payload: {
                "roborio": payload["devices"][0],
                "motor1": payload["devices"][1],
            }

            view.reload_profile("demo")

            self.assertEqual(view._active_connection_filters(), {"can", "power"})
            self.assertEqual(view._status_label.text, "Profile: demo")
        finally:
            live_view_module._load_profiles_payload = original_load_payload
            live_view_module._load_device_registry = original_load_registry

    def test_middle_button_pan_uses_canvas_scan(self) -> None:
        view = self._make_view()

        press_result = view._on_canvas_pan_press(type("Event", (), {"x": 10, "y": 20})())
        drag_result = view._on_canvas_pan_drag(type("Event", (), {"x": 40, "y": 60})())
        release_result = view._on_canvas_pan_release(None)

        self.assertEqual(press_result, "break")
        self.assertEqual(drag_result, "break")
        self.assertEqual(release_result, "break")
        self.assertEqual(view._canvas.mark, (10, 20))
        self.assertEqual(view._canvas.drag, (40, 60, live_view_module.CANVAS_PAN_GAIN))

    def test_fit_to_window_updates_zoom_pan_and_view(self) -> None:
        view = self._make_view()
        view._nodes = [
            live_view_module.LiveNode(
                key=1,
                category="robotController",
                label="roborio",
                can_id=0,
                bus_index=0,
                row=0,
                x=100.0,
            ),
            live_view_module.LiveNode(
                key=2,
                category="pdh",
                label="pdh",
                can_id=1,
                bus_index=0,
                row=1,
                x=900.0,
            ),
        ]
        redraw_calls = []
        view._redraw = lambda *_args, **_kwargs: redraw_calls.append(True)

        view._fit_to_window()

        self.assertTrue(redraw_calls)
        self.assertGreaterEqual(view._zoom, live_view_module.ZOOM_MIN)
        self.assertLessEqual(view._zoom, live_view_module.ZOOM_MAX)
        self.assertIsNotNone(view._canvas.xview)
        self.assertEqual(view._canvas.yview, 0.0)

    def test_schedule_fit_to_window_runs_deferred_fit_once_geometry_exists(self) -> None:
        view = self._make_view()
        fit_calls = []
        view._fit_to_window = lambda: fit_calls.append(True)

        view.schedule_fit_to_window()

        self.assertEqual([True], fit_calls)
        self.assertFalse(view._fit_pending)

    def test_pending_fit_retries_with_timed_callback_when_canvas_is_not_ready(self) -> None:
        view = self._make_view()
        view._canvas = _CanvasStub(width=1, height=1)
        retry_calls = []
        fit_calls = []

        def _after(delay_ms: int, callback) -> None:
            retry_calls.append(delay_ms)

        view.after = _after
        view._fit_pending = True
        view._fit_to_window = lambda: fit_calls.append(True)

        view._apply_pending_fit_to_window()

        self.assertEqual([live_view_module.FIT_RETRY_DELAY_MS], retry_calls)
        self.assertEqual([], fit_calls)
        self.assertTrue(view._fit_pending)

    def test_selected_canvas_shape_overlay_draws_halo_and_outline(self) -> None:
        canvas = _ShapeCanvasStub()

        ids = topology_draw.draw_selected_canvas_shape_overlay(
            canvas,
            10.0,
            20.0,
            110.0,
            70.0,
            "motor",
            halo_color="#ffffff",
            outline_color="#1f6feb",
        )

        self.assertEqual(len(ids), 2)
        self.assertEqual(len(canvas.calls), 2)
        first_kind, _first_args, first_kwargs = canvas.calls[0]
        second_kind, _second_args, second_kwargs = canvas.calls[1]
        self.assertEqual(first_kind, "polygon")
        self.assertEqual(second_kind, "polygon")
        self.assertEqual(first_kwargs["fill"], "")
        self.assertEqual(first_kwargs["outline"], "#ffffff")
        self.assertEqual(
            first_kwargs["width"],
            topology_draw.SELECTION_SHAPE_HALO_WIDTH,
        )
        self.assertEqual(second_kwargs["fill"], "")
        self.assertEqual(second_kwargs["outline"], "#1f6feb")
        self.assertEqual(
            second_kwargs["width"],
            topology_draw.SELECTION_SHAPE_OUTLINE_WIDTH,
        )

    def test_canvas_click_selects_node_and_triggers_redraw(self) -> None:
        view = self._make_view()
        redraw_calls = []
        selection_events = []
        details_calls = []
        node = live_view_module.LiveNode(
            key=25,
            category="neos",
            label="SPARKMAX/NEO 25",
            can_id=25,
            bus_index=0,
            row=0,
            x=0.0,
        )
        view._nodes = [node]
        view._node_bounds = {25: (10.0, 20.0, 110.0, 70.0)}
        view._redraw = lambda *_args, **_kwargs: redraw_calls.append(True)
        view._update_details = lambda: details_calls.append(True)
        view._on_selection_changed_cb = lambda selected: selection_events.append(selected)
        view._on_left_click_cb = None

        view._on_canvas_click(type("Event", (), {"x": 50, "y": 40})())

        self.assertIs(view._selected_node, node)
        self.assertTrue(details_calls)
        self.assertTrue(redraw_calls)
        self.assertEqual(selection_events, [node])

    def test_diagram_nodes_preserve_topology_layout_y_and_registry_category(self) -> None:
        registry = {
            "frontleft encoder": {
                "label": "frontLeft Encoder",
                "deviceInterface": "CAN",
                "manufacturer": 4,
                "deviceType": 7,
                "id": 3,
            }
        }
        diagram = {
            "nodes": [
                {
                    "key": 5,
                    "nodeType": "device",
                    "deviceRef": "frontLeft Encoder",
                    "layout": {
                        "bus": 0,
                        "row": 1,
                        "x": 120.0,
                        "y": 64.0,
                        "yRelative": False,
                    },
                },
                {
                    "key": 16,
                    "nodeType": "junction",
                    "label": "cannect 3",
                    "category": "cannect_direct",
                    "vendor": "SWYFT",
                    "layout": {
                        "bus": 0,
                        "row": 1,
                        "x": 220.0,
                        "y": 180.0,
                        "yRelative": False,
                    },
                },
            ],
            "view": {
                "busOffsets": [-20.0],
            },
        }

        nodes, _meta = live_view_module._diagram_nodes(diagram, registry)

        self.assertEqual(len(nodes), 2)
        encoder = next(node for node in nodes if node.label == "frontLeft Encoder")
        cannect = next(node for node in nodes if node.label == "cannect 3")
        self.assertEqual(encoder.category, "cancoders")
        self.assertEqual(encoder.vendor, "CTRE")
        self.assertEqual(encoder.device_type, "7")
        self.assertEqual(encoder.free_y, 84.0)
        self.assertEqual(encoder.node_class, "device")
        self.assertEqual(cannect.category, "cannect_direct")
        self.assertEqual(cannect.node_type, "diagram")
        self.assertEqual(cannect.node_class, "infrastructure")
        self.assertEqual(cannect.free_y, 200.0)

    def test_diagram_nodes_accept_object_type_without_legacy_node_type(self) -> None:
        registry = {
            "roborio": {
                "label": "roborio",
                "deviceInterface": "CAN",
                "manufacturer": 1,
                "deviceType": 1,
                "id": 0,
            }
        }
        diagram = {
            "nodes": [
                {
                    "key": 1,
                    "objectType": "device",
                    "deviceRef": "roborio",
                    "layout": {"bus": 0, "row": 0, "x": 0.0},
                },
                {
                    "key": 2,
                    "objectType": "junction",
                    "label": "cannect 3",
                    "category": "cannect_direct",
                    "layout": {"bus": 0, "row": 0, "x": 100.0},
                },
            ]
        }

        nodes, _meta = live_view_module._diagram_nodes(diagram, registry)

        self.assertEqual([node.label for node in nodes], ["roborio", "cannect 3"])
        self.assertEqual(nodes[0].node_type, "device")
        self.assertEqual(nodes[0].node_class, "device")
        self.assertEqual(nodes[1].node_type, "diagram")
        self.assertEqual(nodes[1].node_class, "infrastructure")

    def test_base_fill_and_outline_distinguish_non_can_nodes(self) -> None:
        view = self._make_view()
        view._overlay_lens = live_view_module.TOPOLOGY_LENS_RUNTIME
        view._presence_overrides = {}
        view._runtime_state = {}
        view._evidence_state = {}
        view._visibility_state = {}
        view._visibility_sources = {}
        view._passive_detail_state = {}
        can_node = live_view_module.LiveNode(
            key=1,
            category="falcons",
            label="FALCON 9",
            can_id=9,
            bus_index=0,
            row=0,
            x=0.0,
            vendor="CTRE",
            interface="CAN",
        )
        non_can_node = live_view_module.LiveNode(
            key=2,
            category="devices",
            label="controller0",
            can_id=0,
            bus_index=0,
            row=0,
            x=100.0,
            interface="USB",
        )

        self.assertEqual(
            live_view_module.NON_CAN_NODE_FILL,
            view._base_fill(non_can_node, now_ms=0),
        )
        self.assertEqual(
            live_view_module.NON_CAN_NODE_OUTLINE,
            view._base_outline(non_can_node),
        )
        self.assertNotEqual(
            live_view_module.NON_CAN_NODE_FILL,
            view._base_fill(can_node, now_ms=0),
        )
        self.assertNotEqual(
            live_view_module.NON_CAN_NODE_OUTLINE,
            view._base_outline(can_node),
        )

    def test_reload_profile_preserves_canonical_layout_y_in_live_nodes(self) -> None:
        view = self._make_view()

        original_load_payload = live_view_module._load_profiles_payload
        original_load_registry = live_view_module._load_device_registry
        try:
            payload = {
                "default_profile": "demo",
                "profiles": {"demo": {"devices": ["roborio", "motor1"]}},
                "devices": [
                    {
                        "label": "roborio",
                        "deviceInterface": "CAN",
                        "manufacturer": 1,
                        "deviceType": 1,
                        "id": 0,
                    },
                    {
                        "label": "motor1",
                        "deviceInterface": "CAN",
                        "manufacturer": 5,
                        "deviceType": 2,
                        "id": 25,
                    },
                ],
                "topology": {
                    "profiles": {
                        "demo": {
                            "nodes": [
                                {
                                    "key": 1,
                                    "nodeType": "device",
                                    "deviceRef": "roborio",
                                    "layout": {
                                        "bus": 0,
                                        "row": 0,
                                        "x": 0.0,
                                        "y": -40.0,
                                        "yRelative": True,
                                    },
                                },
                                {
                                    "key": 2,
                                    "nodeType": "device",
                                    "deviceRef": "motor1",
                                    "layout": {
                                        "bus": 0,
                                        "row": 1,
                                        "x": 100.0,
                                        "y": 180.0,
                                        "yRelative": False,
                                    },
                                },
                            ],
                            "view": {
                                "busOffsets": [25.0],
                                "connectionFilters": ["can"],
                            },
                        }
                    }
                },
            }
            live_view_module._load_profiles_payload = lambda: (payload, "")
            live_view_module._load_device_registry = lambda _payload: {
                "roborio": payload["devices"][0],
                "motor1": payload["devices"][1],
            }

            view.reload_profile("demo")

            roborio = next(node for node in view._nodes if node.label == "roborio")
            motor = next(node for node in view._nodes if node.label == "motor1")
            self.assertEqual(roborio.free_y, -40.0)
            self.assertEqual(motor.free_y, 155.0)
            self.assertEqual(view._bus_offsets, [25.0])
        finally:
            live_view_module._load_profiles_payload = original_load_payload
            live_view_module._load_device_registry = original_load_registry

    def test_reload_profile_refreshes_active_group_details_immediately(self) -> None:
        view = self._make_view()
        view._update_details_calls = 0
        view._update_details = lambda: setattr(
            view, "_update_details_calls", view._update_details_calls + 1
        )

        original_load_payload = live_view_module._load_profiles_payload
        original_load_registry = live_view_module._load_device_registry
        original_parse_bridge_groups = live_view_module.parse_bridge_groups
        original_redraw = view._redraw

        try:
            live_view_module._load_profiles_payload = lambda: (
                {
                    "defaultProfile": "demo",
                    "profiles": {
                        "demo": {
                            "devices": [
                                {"label": "FALCON 9", "type": "motor", "deviceType": 2, "id": 9},
                            ]
                        }
                    },
                },
                "",
            )
            live_view_module._load_device_registry = lambda _payload: {}
            live_view_module.parse_bridge_groups = lambda _payload, _profile: []
            view._redraw = lambda *_args, **_kwargs: None

            view.reload_profile("demo")

            self.assertEqual(1, view._update_details_calls)
        finally:
            live_view_module._load_profiles_payload = original_load_payload
            live_view_module._load_device_registry = original_load_registry
            live_view_module.parse_bridge_groups = original_parse_bridge_groups
            view._redraw = original_redraw

    def test_reload_profile_aligns_diagram_device_nodes_to_profile_membership(self) -> None:
        view = self._make_view()

        original_load_payload = live_view_module._load_profiles_payload
        original_load_registry = live_view_module._load_device_registry
        original_parse_bridge_groups = live_view_module.parse_bridge_groups
        original_redraw = view._redraw

        try:
            payload = {
                "default_profile": "demo",
                "profiles": {
                    "demo": {
                        "devices": ["FALCON 9", "pigeon 2", "controller0"],
                    }
                },
                "devices": [
                    {"label": "FALCON 9", "deviceInterface": "CAN", "manufacturer": 4, "deviceType": 2, "id": 9},
                    {"label": "pigeon 2", "deviceInterface": "CAN", "manufacturer": 4, "deviceType": 9, "id": 19},
                    {"label": "controller0", "deviceInterface": "USB", "manufacturer": 1, "deviceType": 1, "id": 0},
                ],
                "topology": {
                    "profiles": {
                        "demo": {
                            "nodes": [
                                {
                                    "key": 1,
                                    "nodeType": "device",
                                    "deviceRef": "FALCON 9",
                                    "layout": {"bus": 0, "row": 0, "x": 0.0},
                                },
                                {
                                    "key": 2,
                                    "nodeType": "device",
                                    "deviceRef": "CTRE_GYRO_19",
                                    "layout": {"bus": 0, "row": 0, "x": 100.0},
                                },
                            ],
                            "edges": [],
                            "view": {},
                        }
                    }
                },
            }
            live_view_module._load_profiles_payload = lambda: (payload, "")
            live_view_module._load_device_registry = lambda _payload: {
                "falcon 9": payload["devices"][0],
                "pigeon 2": payload["devices"][1],
                "controller0": payload["devices"][2],
            }
            live_view_module.parse_bridge_groups = lambda _payload, _profile: []
            view._redraw = lambda *_args, **_kwargs: None

            view.reload_profile("demo")

            device_labels = [
                node.label
                for node in view._nodes
                if getattr(node, "node_type", "device") == "device"
            ]
            self.assertEqual(["FALCON 9", "pigeon 2", "controller0"], device_labels)
        finally:
            live_view_module._load_profiles_payload = original_load_payload
            live_view_module._load_device_registry = original_load_registry
            live_view_module.parse_bridge_groups = original_parse_bridge_groups
            view._redraw = original_redraw

    def test_reload_profile_without_saved_topology_includes_non_can_profile_devices(self) -> None:
        view = self._make_view()

        original_load_payload = live_view_module._load_profiles_payload
        original_load_registry = live_view_module._load_device_registry
        original_parse_bridge_groups = live_view_module.parse_bridge_groups
        original_redraw = view._redraw

        try:
            payload = {
                "default_profile": "demo",
                "profiles": {
                    "demo": {
                        "devices": ["FALCON 9", "pigeon 2", "controller0", "lmtSw0"],
                    }
                },
                "devices": [
                    {"label": "FALCON 9", "deviceInterface": "CAN", "manufacturer": 4, "deviceType": 2, "id": 9},
                    {"label": "pigeon 2", "deviceInterface": "CAN", "manufacturer": 4, "deviceType": 9, "id": 19},
                    {"label": "controller0", "deviceInterface": "USB", "manufacturer": 1, "deviceType": 1, "id": 0},
                    {"label": "lmtSw0", "deviceInterface": "DIO", "type": "limitSwitch", "id": 0},
                ],
            }
            live_view_module._load_profiles_payload = lambda: (payload, "")
            live_view_module._load_device_registry = lambda _payload: {
                "falcon 9": payload["devices"][0],
                "pigeon 2": payload["devices"][1],
                "controller0": payload["devices"][2],
                "lmtsw0": payload["devices"][3],
            }
            live_view_module.parse_bridge_groups = lambda _payload, _profile: []
            view._redraw = lambda *_args, **_kwargs: None

            view.reload_profile("demo")

            self.assertEqual(
                ["FALCON 9", "pigeon 2", "controller0", "lmtSw0"],
                [node.label for node in view._nodes if getattr(node, "node_type", "device") == "device"],
            )
        finally:
            live_view_module._load_profiles_payload = original_load_payload
            live_view_module._load_device_registry = original_load_registry
            live_view_module.parse_bridge_groups = original_parse_bridge_groups
            view._redraw = original_redraw

    def test_reload_profile_none_clears_nodes_instead_of_falling_back_to_default_profile(self) -> None:
        view = self._make_view()
        view._nodes = [
            live_view_module.LiveNode(
                key=1,
                category="robotController",
                label="roborio",
                can_id=0,
                bus_index=0,
                row=0,
                x=0.0,
            )
        ]
        view._diagram_meta = {"stale": True}
        view._bridge_groups = [{"name": "active-group"}]
        view._update_details_calls = 0
        view._update_details = lambda: setattr(
            view, "_update_details_calls", view._update_details_calls + 1
        )

        original_load_payload = live_view_module._load_profiles_payload

        try:
            live_view_module._load_profiles_payload = lambda: (
                {
                    "defaultProfile": "demo",
                    "profiles": {
                        "demo": {
                            "devices": [
                                {"label": "FALCON 9", "type": "motor", "deviceType": 2, "id": 9},
                            ]
                        }
                    },
                },
                "",
            )

            view.reload_profile(live_view_module.PROFILE_NONE)

            self.assertEqual([], view._nodes)
            self.assertEqual({}, view._diagram_meta)
            self.assertEqual([], view._bridge_groups)
            self.assertEqual("Profile: (none)", view._status_label.text)
            self.assertEqual(1, view._update_details_calls)
        finally:
            live_view_module._load_profiles_payload = original_load_payload

    def test_apply_diagnostic_profile_state_uses_shared_blank_scene_decision(self) -> None:
        view = self._make_view()
        applied = []
        view.reload_profile = lambda profile_name=None: applied.append(profile_name)
        view._profile_name = "demo"

        profile_state = type(
            "ProfileStateStub",
            (),
            {
                "effective_profile": live_view_module.PROFILE_NONE,
                "show_blank_profile_state": True,
                "blank_reason": "Local profile selection required.",
            },
        )()

        view.apply_diagnostic_profile_state(profile_state)

        self.assertEqual([live_view_module.PROFILE_NONE], applied)

    def test_apply_topology_scene_state_skips_reload_when_scene_is_unchanged(self) -> None:
        view = self._make_view()
        reloads = []
        view.reload_profile = lambda profile_name=None: reloads.append(profile_name)
        view._profile_name = "demo"

        scene_state = live_view_module.TopologySceneState(
            profile_name="demo",
            is_blank=False,
            blank_reason="",
            active_group_meaningful=True,
            should_reload=False,
        )

        view.apply_topology_scene_state(scene_state)

        self.assertEqual([], reloads)

    def test_reload_profile_error_clears_active_group_details_immediately(self) -> None:
        view = self._make_view()
        view._update_details_calls = 0
        view._update_details = lambda: setattr(
            view, "_update_details_calls", view._update_details_calls + 1
        )

        original_load_payload = live_view_module._load_profiles_payload
        original_redraw = view._redraw

        try:
            live_view_module._load_profiles_payload = lambda: (None, "load failed")
            view._redraw = lambda *_args, **_kwargs: None

            view.reload_profile("demo")

            self.assertEqual(1, view._update_details_calls)
        finally:
            live_view_module._load_profiles_payload = original_load_payload
            view._redraw = original_redraw

    def test_reload_profile_missing_requested_profile_clears_instead_of_falling_back(self) -> None:
        view = self._make_view()
        view._nodes = [
            live_view_module.LiveNode(
                key=1,
                category="robotController",
                label="roborio",
                can_id=0,
                bus_index=0,
                row=0,
                x=0.0,
            )
        ]
        view._diagram_meta = {"stale": True}
        view._bridge_groups = [{"name": "active-group"}]
        view._update_details_calls = 0
        view._update_details = lambda: setattr(
            view, "_update_details_calls", view._update_details_calls + 1
        )

        original_load_payload = live_view_module._load_profiles_payload

        try:
            live_view_module._load_profiles_payload = lambda: (
                {
                    "defaultProfile": "demo",
                    "profiles": {
                        "demo": {
                            "devices": [
                                {"label": "FALCON 9", "type": "motor", "deviceType": 2, "id": 9},
                            ]
                        }
                    },
                },
                "",
            )

            view.reload_profile("missing_profile")

            self.assertEqual([], view._nodes)
            self.assertEqual({}, view._diagram_meta)
            self.assertEqual([], view._bridge_groups)
            self.assertEqual("Profile: missing_profile (missing)", view._status_label.text)
            self.assertEqual(1, view._update_details_calls)
        finally:
            live_view_module._load_profiles_payload = original_load_payload

    def test_load_profiles_payload_uses_shared_override_path_before_store_or_canonical(self) -> None:
        payload = {"profiles": {"default": {"devices": []}}}
        override_path = Path("C:/tmp/fromScratch.json")

        with patch(
            "tools.can_topology.live_topology_view.get_profiles_path_override",
            return_value=override_path,
        ):
            with patch(
                "tools.can_topology.live_topology_view._load_profiles_payload_from_path",
                return_value=(payload, ""),
            ) as load_path_mock:
                with patch(
                    "tools.can_topology.live_topology_view._load_profiles_payload_from_store",
                    side_effect=AssertionError("store loader should not run when override path exists"),
                ):
                    loaded_payload, error = live_view_module._load_profiles_payload()

        self.assertEqual(payload, loaded_payload)
        self.assertEqual("", error)
        load_path_mock.assert_called_once_with(override_path)

    def test_effective_groups_preserve_static_members_when_runtime_group_only_has_counts(self) -> None:
        view = self._make_view()
        view._bridge_groups = [
            {
                "name": "motors",
                "enabled": True,
                "members": [
                    {"label": "SPARKMAX/NEO 25", "enabled": True},
                    {"label": "FALCON 9", "enabled": True},
                ],
                "bindings": [{"input": "controller0.rightY", "kind": "analog"}],
            }
        ]
        view._runtime_groups = [
            {
                "name": "motors",
                "enabled": True,
                "memberCount": 2,
                "bindingCount": 1,
            }
        ]

        groups = view._effective_groups()

        self.assertEqual(1, len(groups))
        self.assertEqual("motors", groups[0]["name"])
        self.assertEqual(
            [
                {"label": "SPARKMAX/NEO 25", "enabled": True},
                {"label": "FALCON 9", "enabled": True},
            ],
            groups[0]["members"],
        )
        self.assertEqual(
            [{"input": "controller0.rightY", "kind": "analog"}],
            groups[0]["bindings"],
        )
