from __future__ import annotations

"""
NAME
    ui_theme.py - Shared host-side UI theme tokens and Tk application helpers.

SYNOPSIS
    from tools.can_nt.ui_theme import (
        UI_THEME_FIELD_CONSOLE,
        apply_ttk_theme,
        get_ui_theme_palette,
        list_ui_theme_names,
    )

DESCRIPTION
    Defines the supported desktop theme palettes for the Bringup UI family and
    provides a small helper that applies stable ttk style overrides. Theme
    meaning is centralized here so the main UI and topology view can stay in
    sync without scattering color literals.
"""

from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk
from typing import Dict, List

# Theme identifiers.
UI_THEME_FIELD_CONSOLE = "field_console"
UI_THEME_FIELD_CONSOLE_MEDIUM = "field_console_medium"
UI_THEME_FIELD_CONSOLE_DARK = "field_console_dark"
UI_THEME_DEFAULT = UI_THEME_FIELD_CONSOLE

# Display labels.
UI_THEME_LABEL_FIELD_CONSOLE = "Field Console"
UI_THEME_LABEL_FIELD_CONSOLE_MEDIUM = "Field Console Medium"
UI_THEME_LABEL_FIELD_CONSOLE_DARK = "Field Console Dark"

# ttk style names.
STYLE_APP_FRAME = "App.TFrame"
STYLE_APP_LABEL = "App.TLabel"
STYLE_APP_LABELFRAME = "App.TLabelframe"
STYLE_APP_LABELFRAME_LABEL = "App.TLabelframe.Label"
STYLE_APP_BUTTON = "App.TButton"
STYLE_APP_CHECKBUTTON = "App.TCheckbutton"
STYLE_APP_ENTRY = "App.TEntry"
STYLE_APP_COMBOBOX = "App.TCombobox"
STYLE_APP_NOTEBOOK = "App.TNotebook"
STYLE_APP_NOTEBOOK_TAB = "App.TNotebook.Tab"
STYLE_APP_TREEVIEW = "App.Treeview"
STYLE_APP_TREEVIEW_HEADING = "App.Treeview.Heading"
STYLE_APP_PANEDWINDOW = "App.TPanedwindow"


@dataclass(frozen=True)
class UiThemePalette:
    """
    NAME
        UiThemePalette - Stable color tokens for the desktop host UI.
    """

    name: str
    display_name: str
    app_bg: str
    panel_bg: str
    sidebar_bg: str
    surface_bg: str
    border: str
    text_primary: str
    text_secondary: str
    text_inverse: str
    accent: str
    accent_hover: str
    selection_bg: str
    input_bg: str
    input_fg: str
    text_widget_bg: str
    text_widget_fg: str
    text_widget_insert: str
    line_number_bg: str
    line_number_fg: str
    canvas_bg: str
    status_warn_fg: str
    status_error_fg: str
    status_success_fg: str
    runnable_ready_bg: str
    runnable_ready_fg: str
    runnable_inactive_bg: str
    runnable_inactive_fg: str
    runnable_neutral_bg: str
    runnable_neutral_fg: str
    runnable_error_bg: str
    runnable_error_fg: str
    runnable_border: str


FIELD_CONSOLE_PALETTE = UiThemePalette(
    name=UI_THEME_FIELD_CONSOLE,
    display_name=UI_THEME_LABEL_FIELD_CONSOLE,
    app_bg="#EEF2F5",
    panel_bg="#DCE5EB",
    sidebar_bg="#D7E1E8",
    surface_bg="#FFFFFF",
    border="#B9C6D0",
    text_primary="#162028",
    text_secondary="#4D5B68",
    text_inverse="#F7FBFD",
    accent="#006C8E",
    accent_hover="#00546E",
    selection_bg="#D5ECF3",
    input_bg="#FFFFFF",
    input_fg="#162028",
    text_widget_bg="#FBFCFD",
    text_widget_fg="#162028",
    text_widget_insert="#006C8E",
    line_number_bg="#E7EEF3",
    line_number_fg="#647481",
    canvas_bg="#F8FBFD",
    status_warn_fg="#B36A00",
    status_error_fg="#B02E24",
    status_success_fg="#1F7A45",
    runnable_ready_bg="#dcfce7",
    runnable_ready_fg="#166534",
    runnable_inactive_bg="#fef3c7",
    runnable_inactive_fg="#92400e",
    runnable_neutral_bg="#fef3c7",
    runnable_neutral_fg="#92400e",
    runnable_error_bg="#fee2e2",
    runnable_error_fg="#991b1b",
    runnable_border="#cbd5e1",
)

FIELD_CONSOLE_MEDIUM_PALETTE = UiThemePalette(
    name=UI_THEME_FIELD_CONSOLE_MEDIUM,
    display_name=UI_THEME_LABEL_FIELD_CONSOLE_MEDIUM,
    app_bg="#D7E0E6",
    panel_bg="#C8D3DA",
    sidebar_bg="#BFCBD3",
    surface_bg="#EDF3F7",
    border="#90A2AF",
    text_primary="#142129",
    text_secondary="#425360",
    text_inverse="#F4F8FA",
    accent="#0D6E8C",
    accent_hover="#0A5971",
    selection_bg="#CBE4EE",
    input_bg="#F7FBFD",
    input_fg="#142129",
    text_widget_bg="#EAF1F5",
    text_widget_fg="#142129",
    text_widget_insert="#0D6E8C",
    line_number_bg="#D4DDE4",
    line_number_fg="#556774",
    canvas_bg="#E8EFF4",
    status_warn_fg="#A76400",
    status_error_fg="#A9352A",
    status_success_fg="#256B46",
    runnable_ready_bg="#D6EDE0",
    runnable_ready_fg="#205E3D",
    runnable_inactive_bg="#F4E2B8",
    runnable_inactive_fg="#8F5900",
    runnable_neutral_bg="#CBD8E0",
    runnable_neutral_fg="#365265",
    runnable_error_bg="#EFD1CD",
    runnable_error_fg="#983228",
    runnable_border="#8FA0AD",
)

FIELD_CONSOLE_DARK_PALETTE = UiThemePalette(
    name=UI_THEME_FIELD_CONSOLE_DARK,
    display_name=UI_THEME_LABEL_FIELD_CONSOLE_DARK,
    app_bg="#1B2329",
    panel_bg="#232D34",
    sidebar_bg="#202931",
    surface_bg="#2A353D",
    border="#40515D",
    text_primary="#E6EEF3",
    text_secondary="#A9BAC4",
    text_inverse="#F7FBFD",
    accent="#2C8CAE",
    accent_hover="#23728E",
    selection_bg="#314550",
    input_bg="#2E3941",
    input_fg="#E6EEF3",
    text_widget_bg="#20282E",
    text_widget_fg="#E6EEF3",
    text_widget_insert="#4DB7D1",
    line_number_bg="#283139",
    line_number_fg="#8FA3B0",
    canvas_bg="#253039",
    status_warn_fg="#E0A341",
    status_error_fg="#E37B72",
    status_success_fg="#6FC290",
    runnable_ready_bg="#21392E",
    runnable_ready_fg="#8AD0A4",
    runnable_inactive_bg="#493B21",
    runnable_inactive_fg="#F1BF68",
    runnable_neutral_bg="#2E3C45",
    runnable_neutral_fg="#BED0DA",
    runnable_error_bg="#472927",
    runnable_error_fg="#F3A29A",
    runnable_border="#40515D",
)

UI_THEME_PALETTES: Dict[str, UiThemePalette] = {
    UI_THEME_FIELD_CONSOLE: FIELD_CONSOLE_PALETTE,
    UI_THEME_FIELD_CONSOLE_MEDIUM: FIELD_CONSOLE_MEDIUM_PALETTE,
    UI_THEME_FIELD_CONSOLE_DARK: FIELD_CONSOLE_DARK_PALETTE,
}


def list_ui_theme_names() -> List[str]:
    """
    NAME
        list_ui_theme_names - Return theme identifiers in UI menu order.
    """

    return [
        UI_THEME_FIELD_CONSOLE,
        UI_THEME_FIELD_CONSOLE_MEDIUM,
        UI_THEME_FIELD_CONSOLE_DARK,
    ]


def get_ui_theme_palette(theme_name: str) -> UiThemePalette:
    """
    NAME
        get_ui_theme_palette - Resolve a theme palette with default fallback.
    """

    return UI_THEME_PALETTES.get(str(theme_name or ""), UI_THEME_PALETTES[UI_THEME_DEFAULT])


def apply_ttk_theme(root: tk.Misc, style: ttk.Style, palette: UiThemePalette) -> None:
    """
    NAME
        apply_ttk_theme - Apply the shared desktop theme to ttk and the root shell.

    DESCRIPTION
        Uses conservative ttk styling so the host UI can shift palettes without
        replacing the widget toolkit. The helper targets the base ttk classes
        that dominate the bringup surface.
    """

    style.theme_use("clam")
    root.configure(background=palette.app_bg)
    style.configure(".", background=palette.app_bg, foreground=palette.text_primary)
    style.configure("TFrame", background=palette.panel_bg)
    style.configure("TLabel", background=palette.panel_bg, foreground=palette.text_primary)
    style.configure(
        "TLabelframe",
        background=palette.surface_bg,
        bordercolor=palette.border,
        relief="solid",
    )
    style.configure(
        "TLabelframe.Label",
        background=palette.surface_bg,
        foreground=palette.text_secondary,
    )
    style.configure(
        "TButton",
        background=palette.panel_bg,
        foreground=palette.text_primary,
        bordercolor=palette.border,
        focusthickness=1,
        focuscolor=palette.accent,
    )
    style.map(
        "TButton",
        background=[
            ("active", palette.selection_bg),
            ("pressed", palette.panel_bg),
            ("disabled", palette.panel_bg),
        ],
        foreground=[("disabled", palette.text_secondary)],
    )
    style.configure(
        "TCheckbutton",
        background=palette.panel_bg,
        foreground=palette.text_primary,
    )
    style.configure(
        "TEntry",
        fieldbackground=palette.input_bg,
        foreground=palette.input_fg,
        bordercolor=palette.border,
        insertcolor=palette.accent,
    )
    style.configure(
        "TCombobox",
        fieldbackground=palette.input_bg,
        foreground=palette.input_fg,
        bordercolor=palette.border,
        arrowsize=14,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", palette.input_bg)],
        foreground=[("readonly", palette.input_fg)],
        selectbackground=[("readonly", palette.selection_bg)],
    )
    style.configure("TNotebook", background=palette.app_bg, bordercolor=palette.border)
    style.configure(
        "TNotebook.Tab",
        background=palette.panel_bg,
        foreground=palette.text_secondary,
        padding=(10, 4),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", palette.surface_bg), ("active", palette.selection_bg)],
        foreground=[("selected", palette.text_primary), ("active", palette.text_primary)],
    )
    style.configure(
        "Treeview",
        background=palette.surface_bg,
        fieldbackground=palette.surface_bg,
        foreground=palette.text_primary,
        bordercolor=palette.border,
    )
    style.map(
        "Treeview",
        background=[("selected", palette.selection_bg)],
        foreground=[("selected", palette.text_primary)],
    )
    style.configure(
        "Treeview.Heading",
        background=palette.panel_bg,
        foreground=palette.text_secondary,
        bordercolor=palette.border,
    )
    style.configure("TPanedwindow", background=palette.app_bg)
