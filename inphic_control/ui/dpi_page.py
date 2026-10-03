"""DPI 设置页."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from ..i18n import _
from .widgets import color_button, rgba_hex, slider, value_label

DPI_MIN, DPI_MAX, DPI_STEP = 50, 26000, 50


class DpiPage(Adw.PreferencesPage):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._syncing = False
        self.scales: list[Gtk.Scale] = []
        self.switches: list[Gtk.Switch] = []
        self.value_labels: list[Gtk.Label] = []
        self.color_buttons: list[Gtk.ColorDialogButton] = []
        self.chips: list[Gtk.ToggleButton] = []

        # ---------------------------------------------------- 当前档位
        active_group = Adw.PreferencesGroup(
            title=_("当前档位"),
            description=_("按鼠标底部的 DPI 键可在启用的档位间切换"),
        )
        self.add(active_group)

        chip_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        chip_row.set_margin_top(12)
        chip_row.set_margin_bottom(12)
        chip_row.set_margin_start(12)
        chip_row.set_margin_end(12)
        chip_row.add_css_class("linked")
        active_group.add(chip_row)

        first = None
        for i in range(8):
            chip = Gtk.ToggleButton(label=str(i + 1))
            chip.add_css_class("segment")
            if first is None:
                first = chip
            else:
                chip.set_group(first)
            chip.connect("toggled", self._on_chip_toggled, i)
            chip_row.append(chip)
            self.chips.append(chip)

        self.active_label = Gtk.Label(label="")
        self.active_label.add_css_class("dim-label")
        self.active_label.set_xalign(0)
        self.active_label.set_margin_start(12)
        self.active_label.set_margin_bottom(6)
        active_group.add(self.active_label)

        # ---------------------------------------------------- 档位列表
        stages = Adw.PreferencesGroup(
            title=_("DPI 档位"),
            description=_("范围 {minimum} - {maximum}, 步进 {step}").format(
                minimum=DPI_MIN, maximum=DPI_MAX, step=DPI_STEP
            ),
        )
        self.add(stages)

        for i in range(8):
            row = Adw.ActionRow(title=_("档位 {index}").format(index=i + 1))

            color = color_button("#FFFFFF")
            color.set_tooltip_text(_("该档位的指示灯颜色"))
            color.connect("notify::rgba", self._on_color_changed, i)
            row.add_suffix(color)
            self.color_buttons.append(color)

            value = value_label("—", 66)
            row.add_suffix(value)
            self.value_labels.append(value)

            scale = slider(DPI_MIN, DPI_MAX, DPI_STEP, 800)
            scale.set_size_request(190, -1)
            scale.connect("value-changed", self._on_scale_changed, i)
            row.add_suffix(scale)
            self.scales.append(scale)

            enable = Gtk.Switch()
            enable.set_valign(Gtk.Align.CENTER)
            enable.connect("notify::active", self._on_switch_toggled, i)
            row.add_suffix(enable)
            self.switches.append(enable)

            stages.add(row)

        self.refresh()

    # ------------------------------------------------------------ 交互
    def _on_chip_toggled(self, button: Gtk.ToggleButton, index: int) -> None:
        if self._syncing or not button.get_active():
            return
        if not self.window.config.dpi_enabled[index]:
            # 已禁用的档位不可选
            self._syncing = True
            self.chips[self.window.config.active_stage - 1].set_active(True)
            self._syncing = False
            return
        self.window.config.active_stage = index + 1
        self._update_active_label()
        self.window.push_dpi()

    def _on_switch_toggled(self, switch: Gtk.Switch, _pspec, index: int) -> None:
        if self._syncing:
            return
        enabled = switch.get_active()
        cfg = self.window.config
        if not enabled and sum(1 for on in cfg.dpi_enabled if on) <= 1:
            # 至少保留一个档位
            self._syncing = True
            switch.set_active(True)
            self._syncing = False
            self.window.toast(_("至少需要启用一个 DPI 档位"))
            return
        cfg.dpi_enabled[index] = enabled
        if not enabled and cfg.active_stage == index + 1:
            cfg.active_stage = next(i + 1 for i, on in enumerate(cfg.dpi_enabled) if on)
        self.scales[index].set_sensitive(enabled)
        self.chips[index].set_sensitive(enabled)
        self.refresh()
        self.window.push_dpi()

    def _on_scale_changed(self, scale: Gtk.Scale, index: int) -> None:
        if self._syncing:
            return
        value = int(round(scale.get_value() / DPI_STEP) * DPI_STEP)
        self.window.config.dpi_values[index] = value
        self.value_labels[index].set_label(f"{value}")
        self._update_active_label()
        self.window._debounce("dpi", self.window.push_dpi, 260)

    def _on_color_changed(self, button: Gtk.ColorDialogButton, _pspec, index: int) -> None:
        if self._syncing:
            return
        rgba = button.get_rgba()
        self.window.config.dpi_colors[index] = [
            round(rgba.red * 255),
            round(rgba.green * 255),
            round(rgba.blue * 255),
        ]
        self.window._debounce("dpi", self.window.push_dpi, 260)

    # ------------------------------------------------------------ 同步
    def _update_active_label(self) -> None:
        cfg = self.window.config
        stage = max(1, min(8, cfg.active_stage))
        self.active_label.set_label(
            _("当前: 档位 {stage} · {dpi} DPI").format(
                stage=stage, dpi=cfg.dpi_values[stage - 1]
            )
        )

    def refresh(self) -> None:
        cfg = self.window.config
        self._syncing = True
        for i in range(8):
            enabled = bool(cfg.dpi_enabled[i])
            value = int(cfg.dpi_values[i])
            self.switches[i].set_active(enabled)
            self.switches[i].set_sensitive(True)
            self.scales[i].set_value(value)
            self.scales[i].set_sensitive(enabled)
            self.value_labels[i].set_label(f"{value}")
            self.chips[i].set_sensitive(enabled)
            self.chips[i].set_active(cfg.active_stage == i + 1)
            rgba = self.color_buttons[i].get_rgba()
            color = "#%02X%02X%02X" % tuple(
                int(cfg.dpi_colors[i][j]) & 0xFF for j in range(3)
            )
            from gi.repository import Gdk

            parsed = Gdk.RGBA()
            parsed.parse(color)
            self.color_buttons[i].set_rgba(parsed)
        self._syncing = False
        self._update_active_label()
