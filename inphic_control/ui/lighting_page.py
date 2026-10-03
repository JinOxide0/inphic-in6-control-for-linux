"""灯光设置页."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gtk

from ..i18n import _
from .widgets import color_button, slider, value_label

MODES: list[tuple[str, str]] = [
    ("off", "关闭"),
    ("static", "常亮"),
    ("breathing", "呼吸"),
    ("neon", "霓虹"),
    ("cycle_breathing", "循环呼吸"),
    ("static_dpi", "DPI 常亮"),
    ("breathing_dpi", "DPI 呼吸"),
]
SPEED_MODES = {"breathing", "breathing_dpi"}


class LightingPage(Adw.PreferencesPage):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._syncing = False

        mode_group = Adw.PreferencesGroup(
            title=_("灯光模式"),
            description=_("「DPI 常亮 / DPI 呼吸」会显示当前 DPI 档位的颜色"),
        )
        self.add(mode_group)

        self.mode_row = Adw.ComboRow(title=_("模式"))
        self.mode_row.set_model(Gtk.StringList.new([_(label) for _key, label in MODES]))
        self.mode_row.connect("notify::selected", self._on_mode_changed)
        mode_group.add(self.mode_row)

        color_group = Adw.PreferencesGroup(title=_("颜色"))
        self.add(color_group)

        self.color_row = Adw.ActionRow(
            title=_("灯光颜色"), subtitle=_("仅常亮 / 呼吸模式使用")
        )
        self.color_hex = value_label("#0000FF", 80)
        self.color_button = color_button("#0000FF", size=28)
        self.color_button.connect("notify::rgba", self._on_color_changed)
        self.color_row.add_suffix(self.color_hex)
        self.color_row.add_suffix(self.color_button)
        color_group.add(self.color_row)

        level_group = Adw.PreferencesGroup(title=_("亮度与速度"))
        self.add(level_group)

        self.level_row = Adw.ActionRow(
            title=_("亮度"), subtitle=_("1 (最暗) - 8 (最亮)")
        )
        self.level_label = value_label("2", 44)
        self.level_scale = slider(1, 8, 1, 2)
        self.level_scale.set_size_request(200, -1)
        self.level_scale.connect("value-changed", self._on_level_changed)
        self.level_row.add_suffix(self.level_scale)
        self.level_row.add_suffix(self.level_label)
        level_group.add(self.level_row)

        self.refresh()

    # ------------------------------------------------------------ 交互
    def _mode_key(self) -> str:
        index = self.mode_row.get_selected()
        if 0 <= index < len(MODES):
            return MODES[index][0]
        return "off"

    def _is_speed(self) -> bool:
        return self._mode_key() in SPEED_MODES

    def _on_mode_changed(self, row: Adw.ComboRow, _pspec) -> None:
        if self._syncing:
            return
        self.window.config.light_mode = self._mode_key()
        self._sync_level_row()
        self.window.push_lighting()
        self.window.pages["dashboard"].refresh()

    def _on_color_changed(self, button: Gtk.ColorDialogButton, _pspec) -> None:
        if self._syncing:
            return
        rgba = button.get_rgba()
        self.window.config.color = [
            round(rgba.red * 255),
            round(rgba.green * 255),
            round(rgba.blue * 255),
        ]
        self.color_hex.set_label(
            "#%02X%02X%02X" % tuple(self.window.config.color)
        )
        self.window._debounce("lighting", self.window.push_lighting, 200)
        self.window.pages["dashboard"].refresh()

    def _on_level_changed(self, scale: Gtk.Scale) -> None:
        if self._syncing:
            return
        value = int(round(scale.get_value()))
        if self._is_speed():
            self.window.config.speed = value
        else:
            self.window.config.brightness = value
        self.level_label.set_label(str(value))
        self.window._debounce("lighting", self.window.push_lighting, 200)

    # ------------------------------------------------------------ 同步
    def _sync_level_row(self) -> None:
        cfg = self.window.config
        mode = self._mode_key()
        speed = mode in SPEED_MODES
        self.level_row.set_sensitive(mode != "off")
        if speed:
            self.level_row.set_title(_("呼吸速度"))
            self.level_row.set_subtitle(_("1 (最慢) - 8 (最快)"))
        else:
            self.level_row.set_title(_("亮度"))
            self.level_row.set_subtitle(_("1 (最暗) - 8 (最亮)"))
        self._syncing = True
        self.level_scale.set_value(cfg.speed if speed else cfg.brightness)
        self.level_label.set_label(str(cfg.speed if speed else cfg.brightness))
        self._syncing = False

    def refresh(self) -> None:
        cfg = self.window.config
        self._syncing = True
        keys = [key for key, _ in MODES]
        if cfg.light_mode in keys:
            self.mode_row.set_selected(keys.index(cfg.light_mode))

        rgba = Gdk.RGBA()
        rgba.parse("#%02X%02X%02X" % tuple(cfg.color))
        self.color_button.set_rgba(rgba)
        self.color_hex.set_label("#%02X%02X%02X" % tuple(cfg.color))
        self._syncing = False
        self._sync_level_row()
