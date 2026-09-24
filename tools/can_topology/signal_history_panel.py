"""
NAME
    signal_history_panel.py - Live signal-history controls and Matplotlib lanes.

DESCRIPTION
    Renders the shared host telemetry store as at most four dimension lanes and
    eight traces. Acquisition remains outside this widget, so pause and review
    affect only the visible time window.
"""

from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from tools.common.telemetry.constants import (
    DEFAULT_WINDOW_SECONDS,
    MAX_ACTIVE_SIGNALS,
    MAX_LANES,
    WINDOW_CHOICES_SECONDS,
)
from tools.common.telemetry.history import TelemetryHistoryStore
from tools.common.telemetry.model import (
    SignalDescriptor,
    TelemetryCaptureStatus,
    TelemetrySample,
)


FRAME_RATE_LIMIT = 20.0
MIN_RENDER_INTERVAL_SECONDS = 1.0 / FRAME_RATE_LIMIT
AUTOSCALE_INTERVAL_SECONDS = 5.0
FIGURE_WIDTH_INCHES = 8.0
FIGURE_HEIGHT_INCHES = 3.4
FIGURE_DPI = 100
MIN_PIXEL_COLUMNS = 2
PLOT_PAD_FRACTION = 0.05
MODE_LIVE = "LIVE"
MODE_REVIEW = "REVIEW"
SECONDS_SUFFIX = " s"
CUSTOM_WINDOW_PREFIX = "Custom · "
MICROSECONDS_PER_SECOND = 1_000_000.0
LOGIC_DIMENSION = "LOGIC"
EMPTY_STATUS = "Select a graphable signal in the device inspector."
TRACE_COLORS = (
    "#4f8cff",
    "#ff7f5c",
    "#2fc284",
    "#19c9d8",
    "#c58cff",
    "#f2c14e",
    "#ec5fa1",
    "#8bd450",
)


class SignalHistoryPanel(ttk.Frame):
    """Display live, paused, and review-mode traces from one history store."""

    def __init__(
        self,
        parent: tk.Widget,
        store: TelemetryHistoryStore,
        on_unwatch: Callable[[str], None],
        on_collapse: Callable[[], None],
        on_export_csv: Callable[[], None],
        on_capture_toggle: Optional[
            Callable[[bool], Optional[TelemetryCaptureStatus]]
        ] = None,
        on_capture_settings: Optional[
            Callable[[bool, bool], Optional[TelemetryCaptureStatus]]
        ] = None,
    ) -> None:
        super().__init__(parent, padding=6)
        self._store = store
        self._on_unwatch = on_unwatch
        self._on_collapse = on_collapse
        self._on_export_csv = on_export_csv
        self._on_capture_toggle = on_capture_toggle
        self._on_capture_settings = on_capture_settings
        self._capture_recording = False
        self._window_seconds = DEFAULT_WINDOW_SECONDS
        self._mode = MODE_LIVE
        self._time_origin_us = 0
        self._last_render_s = 0.0
        self._last_full_draw_s = 0.0
        self._axes = []
        self._lines: Dict[str, object] = {}
        self._axis_backgrounds = []
        self._cursor_lines = []
        self._annotation = None
        self._manual_y_limits: Dict[str, Tuple[float, float]] = {}
        self._lane_membership: Dict[str, Tuple[str, ...]] = {}
        self._rendering = False
        self._watch_vars: Dict[str, tk.BooleanVar] = {}
        self._watch_value_vars: Dict[str, tk.StringVar] = {}
        self._trace_colors: Dict[str, str] = {}
        self._next_trace_color = 0

        controls = ttk.Frame(self)
        controls.pack(fill="x")
        ttk.Button(controls, text="Collapse", command=self._on_collapse).pack(side="left")
        ttk.Button(controls, text="Pause", command=self.pause).pack(side="left", padx=(6, 0))
        ttk.Button(controls, text="Resume live", command=self.resume_live).pack(side="left", padx=(6, 0))
        ttk.Label(controls, text="Window").pack(side="left", padx=(14, 4))
        self._window_var = tk.StringVar(
            value=f"{DEFAULT_WINDOW_SECONDS}{SECONDS_SUFFIX}"
        )
        window_box = ttk.Combobox(
            controls,
            textvariable=self._window_var,
            values=tuple(
                f"{value}{SECONDS_SUFFIX}" for value in WINDOW_CHOICES_SECONDS
            ),
            state="readonly",
            width=5,
        )
        window_box.pack(side="left")
        window_box.bind("<<ComboboxSelected>>", self._on_window_changed)
        ttk.Button(controls, text="Fit Y", command=self.fit_y).pack(side="left", padx=(6, 0))
        ttk.Button(controls, text="Export CSV", command=self._on_export_csv).pack(
            side="left", padx=(6, 0)
        )
        self._record_button = ttk.Button(
            controls,
            text="Record",
            command=self._toggle_capture,
        )
        self._record_button.pack(side="left", padx=(6, 0))
        if self._on_capture_toggle is None:
            self._record_button.configure(state="disabled")
        self._capture_var = tk.StringVar(value="Capture: status pending")
        ttk.Label(controls, textvariable=self._capture_var).pack(side="left", padx=(8, 0))
        self._auto_match_var = tk.BooleanVar(value=False)
        self._auto_exception_var = tk.BooleanVar(value=False)
        auto_match = ttk.Checkbutton(
            controls,
            text="Auto: match",
            variable=self._auto_match_var,
            command=self._update_capture_settings,
        )
        auto_match.pack(side="left", padx=(10, 0))
        auto_exception = ttk.Checkbutton(
            controls,
            text="Auto: exception",
            variable=self._auto_exception_var,
            command=self._update_capture_settings,
        )
        auto_exception.pack(side="left", padx=(6, 0))
        if self._on_capture_settings is None:
            auto_match.configure(state="disabled")
            auto_exception.configure(state="disabled")
        self._mode_var = tk.StringVar(value=MODE_LIVE)
        ttk.Label(controls, textvariable=self._mode_var).pack(side="right")
        self._clock_var = tk.StringVar(value=self._store.clock_summary)
        ttk.Label(controls, textvariable=self._clock_var).pack(side="right", padx=(0, 12))

        graph_row = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        graph_row.pack(fill="both", expand=True, pady=(6, 0))
        self._watch_frame = ttk.LabelFrame(graph_row, text="Watched signals", padding=4)
        graph_row.add(self._watch_frame, weight=1)
        self._empty_var = tk.StringVar(value=EMPTY_STATUS)
        self._empty_label = ttk.Label(self._watch_frame, textvariable=self._empty_var)
        self._empty_label.pack(anchor="w")

        plot_frame = ttk.Frame(graph_row)
        graph_row.add(plot_frame, weight=5)
        self._figure = Figure(
            figsize=(FIGURE_WIDTH_INCHES, FIGURE_HEIGHT_INCHES),
            dpi=FIGURE_DPI,
            constrained_layout=True,
        )
        self._canvas = FigureCanvasTkAgg(self._figure, master=plot_frame)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)
        self._toolbar = NavigationToolbar2Tk(self._canvas, plot_frame, pack_toolbar=False)
        self._toolbar.pack(fill="x")
        self._canvas.mpl_connect("button_press_event", self._on_plot_interaction)
        self._canvas.mpl_connect("scroll_event", self._on_plot_interaction)
        self._canvas.mpl_connect("button_release_event", self._on_plot_interaction_finished)
        self._canvas.mpl_connect("motion_notify_event", self._on_cursor_motion)

    def sync_watch_list(self) -> None:
        """Rebuild synchronized native checkboxes for the persistent watch set."""
        for child in self._watch_frame.winfo_children():
            child.destroy()
        self._watch_vars.clear()
        self._watch_value_vars.clear()
        self._clock_var.set(self._store.clock_summary)
        descriptors = self._store.watched_descriptors()
        active_ids = {descriptor.signal_id for descriptor in descriptors}
        self._trace_colors = {
            signal_id: color
            for signal_id, color in self._trace_colors.items()
            if signal_id in active_ids
        }
        for descriptor in descriptors:
            if descriptor.signal_id not in self._trace_colors:
                self._trace_colors[descriptor.signal_id] = TRACE_COLORS[
                    self._next_trace_color % len(TRACE_COLORS)
                ]
                self._next_trace_color += 1
        self._watch_frame.configure(
            text=f"Watched signals · {len(descriptors)} / {MAX_ACTIVE_SIGNALS} selected"
        )
        if not descriptors:
            self._empty_label = ttk.Label(self._watch_frame, text=EMPTY_STATUS)
            self._empty_label.pack(anchor="w")
            return
        for descriptor in descriptors:
            variable = tk.BooleanVar(value=True)
            self._watch_vars[descriptor.signal_id] = variable
            row = ttk.Frame(self._watch_frame)
            row.pack(fill="x", pady=(0, 4))
            ttk.Checkbutton(
                row,
                variable=variable,
                command=lambda signal_id=descriptor.signal_id: self._remove_checked(signal_id),
            ).pack(side="left")
            tk.Label(
                row,
                text="■",
                foreground=self._trace_colors[descriptor.signal_id],
            ).pack(side="left")
            latest = self._store.latest_sample(descriptor.signal_id)
            if latest is not None:
                value = f"{latest.numeric_value:.3f} {descriptor.unit_symbol}".rstrip()
                quality = self._store.current_quality(descriptor.signal_id)
            else:
                value = "no samples"
                quality = "UNAVAILABLE"
            value_var = tk.StringVar(
                value=f"{self._trace_label(descriptor)} · {value} · {quality}"
            )
            self._watch_value_vars[descriptor.signal_id] = value_var
            ttk.Label(
                row,
                textvariable=value_var,
            ).pack(side="left", fill="x", expand=True)

    def refresh_status(self) -> None:
        """Refresh provenance and continuity status without rebuilding controls."""
        self._clock_var.set(self._store.clock_summary)
        for descriptor in self._store.watched_descriptors():
            value_var = self._watch_value_vars.get(descriptor.signal_id)
            if value_var is None:
                continue
            latest = self._store.latest_sample(descriptor.signal_id)
            if latest is None:
                value = "no samples"
                quality = "UNAVAILABLE"
            else:
                value = f"{latest.numeric_value:.3f} {descriptor.unit_symbol}".rstrip()
                quality = self._store.current_quality(descriptor.signal_id)
            value_var.set(f"{self._trace_label(descriptor)} · {value} · {quality}")

    def trace_color(self, signal_id: str) -> str:
        """Return the stable session color assigned to a watched signal."""
        return self._trace_colors.get(signal_id, "")

    def pause(self) -> None:
        """Freeze viewport advancement while acquisition continues."""
        if self._mode == MODE_LIVE:
            self._time_origin_us = self._newest_source_timestamp_us()
        self._mode = MODE_REVIEW
        self._update_mode_status()

    def resume_live(self) -> None:
        """Return to a rolling live window and repaint immediately."""
        self._mode = MODE_LIVE
        self._time_origin_us = self._newest_source_timestamp_us()
        self._update_mode_status()
        self.refresh(force=True)

    def fit_y(self) -> None:
        """Autoscale each engineering-dimension lane without changing time mode."""
        self._manual_y_limits.clear()
        self._rendering = True
        for axis in self._axes:
            axis.relim()
            axis.autoscale_view(scalex=False, scaley=True)
        self._rendering = False
        self._draw_graph(full=True)

    def update_capture_status(self, status: TelemetryCaptureStatus) -> None:
        """Synchronize the Record toggle and selected-storage status."""
        self._capture_recording = status.recording
        self._record_button.configure(text="Stop recording" if status.recording else "Record")
        detail = status.path if status.recording and status.path else status.storage
        self._capture_var.set(f"Capture: {detail or status.message or 'ready'}")
        self._auto_match_var.set(status.auto_match_enabled)
        self._auto_exception_var.set(status.auto_exception_enabled)

    def refresh(self, force: bool = False) -> None:
        """Repaint at the bounded UI rate using extrema-preserving decimation."""
        now_s = time.monotonic()
        if not force and now_s - self._last_render_s < MIN_RENDER_INTERVAL_SECONDS:
            return
        self._last_render_s = now_s
        descriptors = self._store.watched_descriptors()
        dimensions = []
        for descriptor in descriptors:
            if descriptor.engineering_dimension not in dimensions:
                dimensions.append(descriptor.engineering_dimension)
        dimensions = dimensions[:MAX_LANES]
        previous_limits = [axis.get_xlim() for axis in self._axes]
        next_membership = {
            dimension: tuple(
                descriptor.signal_id
                for descriptor in descriptors
                if descriptor.engineering_dimension == dimension
            )
            for dimension in dimensions
        }
        structure_changed = next_membership != self._lane_membership
        for dimension, membership in next_membership.items():
            if self._lane_membership.get(dimension) != membership:
                self._manual_y_limits.pop(dimension, None)
        self._lane_membership = next_membership
        if not dimensions:
            if self._axes:
                self._figure.clear()
                self._axes = []
                self._lines.clear()
                self._cursor_lines = []
                self._axis_backgrounds = []
            self._draw_graph(full=True)
            return
        newest_us = self._newest_source_timestamp_us()
        if self._mode == MODE_LIVE or self._time_origin_us == 0:
            self._time_origin_us = newest_us
        if self._mode == MODE_LIVE or not previous_limits:
            view_limits = (-float(self._window_seconds), 0.0)
        else:
            view_limits = previous_limits[0]
        start_us = self._time_origin_us + int(
            view_limits[0] * MICROSECONDS_PER_SECOND
        )
        end_us = self._time_origin_us + int(
            view_limits[1] * MICROSECONDS_PER_SECOND
        )
        self._rendering = True
        if structure_changed:
            self._figure.clear()
            self._axes = []
            self._lines.clear()
            self._cursor_lines = []
            self._axis_backgrounds = []
            self._annotation = None
            for lane_index, dimension in enumerate(dimensions):
                axis = self._figure.add_subplot(
                    len(dimensions),
                    1,
                    lane_index + 1,
                    sharex=self._axes[0] if self._axes else None,
                )
                self._axes.append(axis)
                lane_descriptors = [
                    descriptor
                    for descriptor in descriptors
                    if descriptor.engineering_dimension == dimension
                ]
                for descriptor in lane_descriptors:
                    color = self._trace_colors.get(
                        descriptor.signal_id,
                        TRACE_COLORS[0],
                    )
                    if dimension == LOGIC_DIMENSION:
                        line = axis.step(
                            (),
                            (),
                            where="post",
                            label=self._trace_label(descriptor),
                            color=color,
                        )[0]
                    else:
                        line = axis.plot(
                            (),
                            (),
                            label=self._trace_label(descriptor),
                            color=color,
                        )[0]
                    line.set_animated(True)
                    self._lines[descriptor.signal_id] = line
                axis.set_ylabel(lane_descriptors[0].unit_symbol or dimension)
                axis.grid(True, alpha=0.25)
                axis.legend(loc="upper left", fontsize="small")
                cursor_line = axis.axvline(
                    0.0,
                    color="#cccccc",
                    linestyle="--",
                    visible=False,
                )
                cursor_line.set_animated(True)
                self._cursor_lines.append(cursor_line)
                axis.callbacks.connect(
                    "ylim_changed",
                    lambda changed_axis, lane_dimension=dimension: self._capture_y_limit(
                        lane_dimension,
                        changed_axis,
                    ),
                )
            self._axes[-1].set_xlabel("seconds relative to source-session origin")
        axis_by_dimension = dict(zip(dimensions, self._axes))
        pixel_width = self._plot_pixel_width()
        dimension_extrema: Dict[str, Tuple[float, float]] = {}
        for descriptor in descriptors:
            points = self._store.decimated_samples(
                descriptor.signal_id,
                pixel_width,
                start_us,
                end_us,
            )
            times = project_source_times(points, self._time_origin_us)
            plotted_times = []
            plotted_values = []
            for point_time, point in zip(times, points):
                if point.gap_before and plotted_times:
                    plotted_times.append(point_time)
                    plotted_values.append(float("nan"))
                plotted_times.append(point_time)
                plotted_values.append(point.numeric_value)
            self._lines[descriptor.signal_id].set_data(plotted_times, plotted_values)
            finite_values = [
                value for value in plotted_values if value == value
            ]
            if finite_values:
                minimum = min(finite_values)
                maximum = max(finite_values)
                previous = dimension_extrema.get(descriptor.engineering_dimension)
                dimension_extrema[descriptor.engineering_dimension] = (
                    min(minimum, previous[0]) if previous else minimum,
                    max(maximum, previous[1]) if previous else maximum,
                )
        full_draw = structure_changed
        autoscale_due = (
            now_s - self._last_full_draw_s >= AUTOSCALE_INTERVAL_SECONDS
        )
        for lane_index, dimension in enumerate(dimensions):
            axis = axis_by_dimension[dimension]
            if dimension == LOGIC_DIMENSION:
                axis.set_ylim(-0.1, 1.1)
                axis.set_yticks((0.0, 1.0), labels=("false", "true"))
            elif dimension in self._manual_y_limits:
                axis.set_ylim(self._manual_y_limits[dimension])
            elif (
                autoscale_due
                or structure_changed
                or self._outside_y_limits(axis, dimension_extrema.get(dimension))
            ):
                axis.relim()
                axis.autoscale_view(scalex=False, scaley=True)
                full_draw = True
            if tuple(axis.get_xlim()) != tuple(view_limits):
                axis.set_xlim(view_limits)
                full_draw = True
        self._rendering = False
        self._update_mode_status()
        self._draw_graph(full=full_draw)

    @staticmethod
    def _outside_y_limits(
        axis: object,
        extrema: Optional[Tuple[float, float]],
    ) -> bool:
        """Request immediate autoscale when a new value would be clipped."""
        if extrema is None:
            return False
        lower, upper = axis.get_ylim()
        return extrema[0] < lower or extrema[1] > upper

    def _draw_graph(self, full: bool) -> None:
        """Use a full layout draw only when axes changed; otherwise blit trace artists."""
        if full or len(self._axis_backgrounds) != len(self._axes):
            self._canvas.draw()
            self._axis_backgrounds = [
                self._canvas.copy_from_bbox(axis.bbox) for axis in self._axes
            ]
            self._last_full_draw_s = time.monotonic()
        for axis, background in zip(self._axes, self._axis_backgrounds):
            self._canvas.restore_region(background)
            for line in axis.lines:
                axis.draw_artist(line)
            if self._annotation is not None and self._annotation.axes is axis:
                axis.draw_artist(self._annotation)
            self._canvas.blit(axis.bbox)

    def _remove_checked(self, signal_id: str) -> None:
        self._on_unwatch(signal_id)

    def _toggle_capture(self) -> None:
        if self._on_capture_toggle is None:
            return
        status = self._on_capture_toggle(not self._capture_recording)
        if status is not None:
            self.update_capture_status(status)

    def _update_capture_settings(self) -> None:
        if self._on_capture_settings is None:
            return
        status = self._on_capture_settings(
            self._auto_match_var.get(),
            self._auto_exception_var.get(),
        )
        if status is not None:
            self.update_capture_status(status)

    def _on_window_changed(self, _event: object = None) -> None:
        selected = self._window_var.get().removesuffix(SECONDS_SUFFIX)
        self._window_seconds = int(selected)
        if self._mode != MODE_LIVE:
            for axis in self._axes:
                left, right = axis.get_xlim()
                center = (left + right) / 2.0
                half_window = float(self._window_seconds) / 2.0
                axis.set_xlim(center - half_window, center + half_window)
        self.refresh(force=True)

    def _on_plot_interaction(self, _event: object) -> None:
        if self._mode == MODE_LIVE:
            self._time_origin_us = self._newest_source_timestamp_us()
        self._mode = MODE_REVIEW
        self._update_mode_status()
        self.after_idle(self._show_custom_window)

    def _on_plot_interaction_finished(self, event: object) -> None:
        """Clamp a completed pan or zoom to retained history and approved durations."""
        if not self._axes or self._mode != MODE_REVIEW:
            return
        source_axis = getattr(event, "inaxes", None)
        if source_axis not in self._axes:
            source_axis = self._axes[0]
        left, right = source_axis.get_xlim()
        duration = min(
            float(self._store.retention_seconds),
            max(1.0, abs(right - left)),
        )
        live_edge = (
            self._newest_source_timestamp_us() - self._time_origin_us
        ) / MICROSECONDS_PER_SECOND
        right = min(live_edge, right)
        left = max(live_edge - float(self._store.retention_seconds), right - duration)
        right = left + duration
        for axis in self._axes:
            axis.set_xlim(left, right)
        self._update_mode_status()
        self.after_idle(self._show_custom_window)

    def _show_custom_window(self) -> None:
        if not self._axes or self._mode != MODE_REVIEW:
            return
        left, right = self._axes[0].get_xlim()
        duration = abs(right - left)
        self._window_var.set(f"{CUSTOM_WINDOW_PREFIX}{duration:.1f}s")

    def _on_cursor_motion(self, event: object) -> None:
        if not self._axes or getattr(event, "xdata", None) is None:
            return
        target_time = float(event.xdata)
        target_us = self._time_origin_us + int(target_time * MICROSECONDS_PER_SECOND)
        nearest = self._nearest_samples(target_us)
        if not nearest:
            return
        for line in self._cursor_lines:
            line.set_xdata([target_time, target_time])
            line.set_visible(True)
        text = "\n".join(
            f"{descriptor.device_label} · {descriptor.signal_name}: "
            f"{sample.numeric_value:.3f} {descriptor.unit_symbol} · "
            f"{sample.quality} · source {sample.source_timestamp_us} µs"
            for descriptor, sample in nearest
        )
        axis = event.inaxes if event.inaxes in self._axes else self._axes[0]
        if self._annotation is not None:
            self._annotation.remove()
        self._annotation = axis.annotate(
            text,
            xy=(target_time, nearest[0][1].numeric_value),
            xytext=(12, 12),
            textcoords="offset points",
            bbox={"boxstyle": "round", "facecolor": "#20242a", "alpha": 0.9},
            color="white",
        )
        self._annotation.set_animated(True)
        self._draw_graph(full=False)

    def _update_mode_status(self) -> None:
        """Show the viewport state and review lag from the newest sample."""
        if self._mode == MODE_LIVE or not self._axes:
            self._mode_var.set(MODE_LIVE)
            return
        _left, right = self._axes[0].get_xlim()
        live_edge = (
            self._newest_source_timestamp_us() - self._time_origin_us
        ) / MICROSECONDS_PER_SECOND
        lag = max(0.0, live_edge - right)
        self._mode_var.set(f"{MODE_REVIEW} · {lag:.1f}s behind live")

    def _newest_source_timestamp_us(self) -> int:
        """Return the newest accepted source timestamp across watched traces."""
        return max(
            (
                self._store.latest_source_timestamp_us(descriptor.signal_id)
                for descriptor in self._store.watched_descriptors()
            ),
            default=0,
        )

    def _nearest_samples(
        self,
        target_us: int,
    ) -> List[Tuple[SignalDescriptor, TelemetrySample]]:
        nearest = []
        for descriptor in self._store.watched_descriptors():
            sample = self._store.nearest_sample(descriptor.signal_id, target_us)
            if sample is not None:
                nearest.append((descriptor, sample))
        return nearest

    def _capture_y_limit(self, dimension: str, axis: object) -> None:
        if self._rendering or dimension == LOGIC_DIMENSION:
            return
        self._manual_y_limits[dimension] = tuple(axis.get_ylim())

    def _plot_pixel_width(self) -> int:
        return max(MIN_PIXEL_COLUMNS, int(self._canvas.get_tk_widget().winfo_width()))

    @staticmethod
    def _trace_label(descriptor: SignalDescriptor) -> str:
        unit = f" ({descriptor.unit_symbol})" if descriptor.unit_symbol else ""
        return f"{descriptor.device_label} · {descriptor.signal_name}{unit}"


def decimate_samples(
    samples: Sequence[TelemetrySample],
    pixel_width: int,
) -> Tuple[TelemetrySample, ...]:
    """Preserve first, last, minimum, and maximum values in each pixel bucket."""
    if len(samples) <= max(MIN_PIXEL_COLUMNS, pixel_width):
        return tuple(samples)
    bucket_count = max(MIN_PIXEL_COLUMNS, pixel_width)
    bucket_size = max(1, (len(samples) + bucket_count - 1) // bucket_count)
    selected: List[TelemetrySample] = []
    for start in range(0, len(samples), bucket_size):
        bucket = samples[start : start + bucket_size]
        if not bucket:
            continue
        minimum = min(bucket, key=lambda item: item.numeric_value)
        maximum = max(bucket, key=lambda item: item.numeric_value)
        if start == 0:
            extreme = max(
                (minimum, maximum),
                key=lambda item: abs(item.numeric_value - bucket[0].numeric_value),
            )
            candidates = (bucket[0], extreme)
        elif start + bucket_size >= len(samples):
            extreme = max(
                (minimum, maximum),
                key=lambda item: abs(item.numeric_value - bucket[-1].numeric_value),
            )
            candidates = (extreme, bucket[-1])
        else:
            candidates = (minimum, maximum)
        candidates = (*candidates, *(item for item in bucket if item.gap_before))
        for sample in sorted(set(candidates), key=lambda item: item.sequence):
            if not selected or selected[-1].sequence != sample.sequence:
                selected.append(sample)
    return tuple(selected)


def project_source_times(
    samples: Sequence[TelemetrySample],
    origin_us: int,
) -> List[float]:
    """Project source timestamps against a stable live or review origin."""
    return [
        (sample.source_timestamp_us - origin_us) / MICROSECONDS_PER_SECOND
        for sample in samples
    ]
