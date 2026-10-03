"""概览页."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from .. import protocol as P
from .widgets import HeroCard, StatTile


class DashboardPage(Gtk.ScrolledWindow):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(18)
        box.set_margin_bottom(24)
        box.set_margin_start(18)
        box.set_margin_end(18)
        self.set_child(box)

        self.hero = HeroCard()
        box.append(self.hero)

        grid = Gtk.Grid()
        grid.set_column_spacing(14)
        grid.set_row_spacing(14)
        grid.set_column_homogeneous(True)
        box.append(grid)

        self.tile_dpi = StatTile("speedometer-symbolic", "当前 DPI")
        self.tile_polling = StatTile("power-profile-performance-symbolic", "轮询率")
        self.tile_light = StatTile("color-select-symbolic", "灯光")
        self.tile_buttons = StatTile("input-keyboard-symbolic", "按键映射")
        grid.attach(self.tile_dpi, 0, 0, 1, 1)
        grid.attach(self.tile_polling, 1, 0, 1, 1)
        grid.attach(self.tile_light, 0, 1, 1, 1)
        grid.attach(self.tile_buttons, 1, 1, 1, 1)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        actions.set_margin_top(4)
        box.append(actions)

        apply_all = Gtk.Button(label="应用全部设置")
        apply_all.add_css_class("suggested-action")
        apply_all.add_css_class("pill")
        apply_all.connect("clicked", lambda *_: self.window.push_all(manual=True))
        actions.append(apply_all)

        reset = Gtk.Button(label="恢复默认")
        reset.add_css_class("pill")
        reset.connect("clicked", self._on_reset)
        actions.append(reset)

        hint = Gtk.Label(
            label="设置会立即写入鼠标; 修改后自动保存到本地配置。"
        )
        hint.add_css_class("dim-label")
        hint.set_xalign(0)
        hint.set_margin_top(6)
        box.append(hint)

        self.refresh()

    # ------------------------------------------------------------ 数据
    def refresh(self) -> None:
        cfg = self.window.config

        stage = max(1, min(8, cfg.active_stage))
        dpi = cfg.dpi_values[stage - 1]
        enabled = sum(1 for on in cfg.dpi_enabled if on)
        self.tile_dpi.set_value(f"{dpi} DPI", f"档位 {stage} / 共 {enabled} 档")

        rate = cfg.polling_rate
        self.tile_polling.set_value(
            f"{rate} Hz",
            "竞技模式" if rate >= 4000 else ("游戏模式" if rate >= 1000 else "省电模式"),
        )

        mode_names = {
            "off": "关闭",
            "static": "常亮",
            "breathing": "呼吸",
            "neon": "霓虹",
            "cycle_breathing": "循环呼吸",
            "static_dpi": "DPI 常亮",
            "breathing_dpi": "DPI 呼吸",
        }
        self.tile_light.set_value(
            mode_names.get(cfg.light_mode, cfg.light_mode),
            f"#{cfg.color[0]:02X}{cfg.color[1]:02X}{cfg.color[2]:02X} · 亮度 {cfg.brightness}",
        )

        custom = 0
        for i, (_slot, preset) in enumerate(P.BUTTON_SLOTS):
            if i >= len(cfg.buttons):
                break
            binding = cfg.buttons[i]
            if binding.kind != "preset" or binding.preset != preset:
                custom += 1
        self.tile_buttons.set_value(f"{custom} 个自定义", "共 18 个动作槽位")

    def set_device(self, info) -> None:
        self.hero.set_connected(bool(info), info.label if info else "", info.is_wireless is False if info else False)
        self.refresh()

    def set_battery(self, status: int, level: int) -> None:
        self.hero.set_battery(status, level)

    # ------------------------------------------------------------ 动作
    def _on_reset(self, _button) -> None:
        from ..config import Config

        window = self.window
        fresh = Config()
        fresh.buttons = [type(b)(preset=p) for _, p in P.BUTTON_SLOTS]
        window.config = fresh
        window.save_config()
        for page in window.pages.values():
            if hasattr(page, "refresh"):
                page.refresh()
        window.push_all(manual=True)
        window.toast("已恢复默认设置")
