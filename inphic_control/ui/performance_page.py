"""性能设置页."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from .widgets import slider, value_label

POLLING_RATES = [125, 250, 500, 1000, 2000, 4000, 8000]


class PerformancePage(Adw.PreferencesPage):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._syncing = False
        self.rate_buttons: dict[int, Gtk.ToggleButton] = {}

        # ---------------------------------------------------- 轮询率
        rate_group = Adw.PreferencesGroup(
            title="轮询率",
            description="8K 接收器支持最高 8000 Hz; 高轮询率会增加 CPU 占用",
        )
        self.add(rate_group)

        rate_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        rate_row.set_margin_top(12)
        rate_row.set_margin_bottom(12)
        rate_row.set_margin_start(12)
        rate_row.set_margin_end(12)
        rate_row.add_css_class("linked")
        rate_group.add(rate_row)

        first = None
        for rate in POLLING_RATES:
            button = Gtk.ToggleButton(label=f"{rate}")
            button.add_css_class("segment")
            button.set_tooltip_text(f"{rate} Hz")
            if first is None:
                first = button
            else:
                button.set_group(first)
            button.connect("toggled", self._on_rate_toggled, rate)
            rate_row.append(button)
            self.rate_buttons[rate] = button

        # ---------------------------------------------------- 传感器
        sensor_group = Adw.PreferencesGroup(title="传感器")
        self.add(sensor_group)

        self.ripple_row = Adw.SwitchRow(
            title="波纹控制 (Ripple Control)",
            subtitle="降低无线传输带来的抖动",
        )
        self.ripple_row.connect("notify::active", self._on_sensor_switch, "ripple")
        sensor_group.add(self.ripple_row)

        self.snap_row = Adw.SwitchRow(
            title="角度捕捉 (Angle Snapping)",
            subtitle="让直线移动更平稳",
        )
        self.snap_row.connect("notify::active", self._on_sensor_switch, "angle_snap")
        sensor_group.add(self.snap_row)

        self.sync_row = Adw.SwitchRow(
            title="运动同步 (Motion Sync)",
            subtitle="传感器采样与 USB 上报同步",
        )
        self.sync_row.connect("notify::active", self._on_sensor_switch, "motion_sync")
        sensor_group.add(self.sync_row)

        self.lod_row = Adw.ComboRow(title="抬起高度 (LOD)")
        self.lod_row.set_model(Gtk.StringList.new(["1 mm", "2 mm"]))
        self.lod_row.connect("notify::selected", self._on_lod_changed)
        sensor_group.add(self.lod_row)

        # ---------------------------------------------------- 电源
        power_group = Adw.PreferencesGroup(title="电源管理")
        self.add(power_group)

        self.sleep_scale, self.sleep_label = self._slider_row(
            power_group,
            "休眠时间",
            "无操作后进入浅睡的时间 (0.5 - 30 分钟)",
            0.5, 30, 0.5,
            self._on_sleep_changed,
        )
        self.deep_scale, self.deep_label = self._slider_row(
            power_group,
            "深度休眠",
            "进入深度省电的时间 (1 - 60 分钟)",
            1, 60, 1,
            self._on_deep_changed,
        )

        # ---------------------------------------------------- 按键响应
        response_group = Adw.PreferencesGroup(title="按键响应")
        self.add(response_group)
        self.debounce_scale, self.debounce_label = self._slider_row(
            response_group,
            "按键去抖",
            "数值越低响应越快 (4 - 50 ms)",
            4, 50, 2,
            self._on_debounce_changed,
        )

        self.refresh()

    # ------------------------------------------------------------ 构建
    def _slider_row(self, group, title, subtitle, minimum, maximum, step, callback):
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        label = value_label("—", 70)
        scale = slider(minimum, maximum, step, minimum)
        scale.set_size_request(190, -1)
        scale.connect("value-changed", callback)
        row.add_suffix(scale)
        row.add_suffix(label)
        group.add(row)
        return scale, label

    # ------------------------------------------------------------ 交互
    def _on_rate_toggled(self, button: Gtk.ToggleButton, rate: int) -> None:
        if self._syncing or not button.get_active():
            return
        self.window.config.polling_rate = rate
        self.window.push_polling()
        self.window.pages["dashboard"].refresh()

    def _on_sensor_switch(self, row: Adw.SwitchRow, _pspec, field: str) -> None:
        if self._syncing:
            return
        setattr(self.window.config, field, row.get_active())
        self.window.push_dpi()

    def _on_lod_changed(self, row: Adw.ComboRow, _pspec) -> None:
        if self._syncing:
            return
        self.window.config.lift_off = int(row.get_selected())
        self.window.push_dpi()

    def _on_sleep_changed(self, scale: Gtk.Scale) -> None:
        if self._syncing:
            return
        value = round(scale.get_value() * 2) / 2
        self.window.config.sleep_minutes = value
        self.sleep_label.set_label(f"{value:g} min")
        self.window._debounce("lighting", self.window.push_lighting, 280)

    def _on_deep_changed(self, scale: Gtk.Scale) -> None:
        if self._syncing:
            return
        value = int(round(scale.get_value()))
        self.window.config.deep_sleep_minutes = value
        self.deep_label.set_label(f"{value} min")
        self.window._debounce("lighting", self.window.push_lighting, 280)

    def _on_debounce_changed(self, scale: Gtk.Scale) -> None:
        if self._syncing:
            return
        value = int(round(scale.get_value() / 2) * 2)
        self.window.config.debounce_ms = value
        self.debounce_label.set_label(f"{value} ms")
        self.window._debounce("lighting", self.window.push_lighting, 280)

    # ------------------------------------------------------------ 同步
    def refresh(self) -> None:
        cfg = self.window.config
        self._syncing = True
        button = self.rate_buttons.get(cfg.polling_rate)
        if button is not None:
            button.set_active(True)
        self.ripple_row.set_active(cfg.ripple)
        self.snap_row.set_active(cfg.angle_snap)
        self.sync_row.set_active(cfg.motion_sync)
        self.lod_row.set_selected(0 if cfg.lift_off == 0 else 1)

        self.sleep_scale.set_value(cfg.sleep_minutes)
        self.sleep_label.set_label(f"{cfg.sleep_minutes:g} min")
        self.deep_scale.set_value(cfg.deep_sleep_minutes)
        self.deep_label.set_label(f"{cfg.deep_sleep_minutes} min")
        self.debounce_scale.set_value(cfg.debounce_ms)
        self.debounce_label.set_label(f"{cfg.debounce_ms} ms")
        self._syncing = False
