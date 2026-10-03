"""主窗口: 侧边栏 + 页面栈 + 命令下发."""
from __future__ import annotations

import os

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk

from .. import protocol as P
from ..config import Config
from ..device_manager import DeviceManager
from .about_page import AboutPage
from .buttons_page import ButtonsPage
from .dashboard import DashboardPage
from .dpi_page import DpiPage
from .lighting_page import LightingPage
from .performance_page import PerformancePage
from .widgets import BatteryPill

APP_VERSION = "0.3.0"


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, config: Config, manager: DeviceManager, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.manager = manager
        self.set_default_size(1024, 720)
        self.set_size_request(860, 600)
        self._timers: dict[str, int] = {}
        self._status_reset: int | None = None

        self.set_title("Inphic Control")

        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        toolbar = Adw.ToolbarView()
        self.toast_overlay.set_child(toolbar)

        # ------------------------------------------------------ 顶栏
        self.header = Adw.HeaderBar()
        self.header.set_title_widget(Gtk.Label(label="Inphic Control"))
        toolbar.add_top_bar(self.header)

        self.sidebar_toggle = Gtk.ToggleButton()
        self.sidebar_toggle.set_icon_name("sidebar-show-symbolic")
        self.sidebar_toggle.set_tooltip_text("显示/隐藏侧边栏")
        self.header.pack_start(self.sidebar_toggle)

        self.status_stack = Gtk.Stack()
        self.status_stack.set_valign(Gtk.Align.CENTER)
        self.status_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.status_stack.add_named(Gtk.Box(), "idle")

        self.spinner = Gtk.Spinner()
        self.status_stack.add_named(self.spinner, "sending")

        ok_icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
        ok_icon.add_css_class("status-ok")
        self.status_stack.add_named(ok_icon, "ok")

        err_icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
        err_icon.add_css_class("status-error")
        self.status_stack.add_named(err_icon, "error")
        self.status_stack.set_visible_child_name("idle")
        self.header.pack_end(self.status_stack)

        self.mini_battery = BatteryPill(48, 20)
        self.mini_battery.set_margin_start(8)
        self.mini_battery.set_tooltip_text("鼠标电量")
        self.mini_battery.set_visible(False)
        self.header.pack_end(self.mini_battery)

        apply_button = Gtk.Button()
        apply_button.set_icon_name("document-save-symbolic")
        apply_button.set_tooltip_text("重新应用全部设置")
        apply_button.add_css_class("flat")
        apply_button.connect("clicked", lambda *_: self.push_all(manual=True))
        self.header.pack_end(apply_button)

        # ------------------------------------------------------ 布局
        self.split = Adw.OverlaySplitView()
        self.split.set_min_sidebar_width(216)
        self.split.set_max_sidebar_width(240)
        self.split.set_sidebar_width_fraction(0.22)
        toolbar.set_content(self.split)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar.add_css_class("sidebar-panel")
        self.split.set_sidebar(sidebar)

        sidebar_header = Gtk.Label(label="设置")
        sidebar_header.set_xalign(0)
        sidebar_header.add_css_class("sidebar-heading")
        sidebar_header.set_margin_top(14)
        sidebar_header.set_margin_bottom(6)
        sidebar_header.set_margin_start(20)
        sidebar.append(sidebar_header)

        self.listbox = Gtk.ListBox()
        self.listbox.add_css_class("navigation-sidebar")
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.set_vexpand(True)
        self.listbox.connect("row-selected", self._on_row_selected)
        sidebar.append(self.listbox)

        footer = Gtk.Label(label=f"Inphic IN6 · v{APP_VERSION}")
        footer.add_css_class("sidebar-footer")
        footer.set_margin_top(6)
        footer.set_margin_bottom(12)
        sidebar.append(footer)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(140)
        self.split.set_content(self.stack)

        self.pages: dict[str, Gtk.Widget] = {}
        self._add_page("dashboard", "概览", "input-mouse-symbolic", DashboardPage(self))
        self._add_page("dpi", "DPI", "speedometer-symbolic", DpiPage(self))
        self._add_page("performance", "性能", "power-profile-performance-symbolic", PerformancePage(self))
        self._add_page("lighting", "灯光", "color-select-symbolic", LightingPage(self))
        self._add_page("buttons", "按键", "input-keyboard-symbolic", ButtonsPage(self))
        self._add_page("about", "关于", "help-about-symbolic", AboutPage(self))

        self.split.bind_property("show-sidebar", self.sidebar_toggle, "active", 2)

        # ------------------------------------------------------ 信号
        manager.connect("changed", self._on_device_changed)
        manager.connect("battery", self._on_battery)
        manager.connect("ack", self._on_ack)
        manager.connect("sent", self._on_sent)
        manager.connect("dpi-cycle", self._on_dpi_cycle)

        self.listbox.select_row(self.listbox.get_row_at_index(0))
        self._on_device_changed(manager, manager.connected, manager.info)
        if manager.battery_level is not None:
            self._on_battery(manager, manager.battery_status or 1, manager.battery_level)

    # ------------------------------------------------------------ 页面
    def _add_page(self, page_id: str, title: str, icon: str, page: Gtk.Widget) -> None:
        from .widgets import SidebarRow

        row = SidebarRow(page_id, title, icon)
        self.listbox.append(row)
        self.pages[page_id] = page
        self.stack.add_named(page, page_id)

    def _on_row_selected(self, _listbox, row) -> None:
        if row is not None:
            self.stack.set_visible_child_name(row.page_id)

    # ------------------------------------------------------------ 状态
    def toast(self, text: str) -> None:
        toast = Adw.Toast.new(text)
        toast.set_timeout(2)
        self.toast_overlay.add_toast(toast)

    def _set_status(self, name: str, reset_after: float | None = None) -> None:
        if self._status_reset is not None:
            GLib.source_remove(self._status_reset)
            self._status_reset = None
        if name == "sending":
            self.spinner.start()
        else:
            self.spinner.stop()
        self.status_stack.set_visible_child_name(name)
        if reset_after:
            self._status_reset = GLib.timeout_add(
                int(reset_after * 1000), self._reset_status
            )

    def _reset_status(self) -> bool:
        self._status_reset = None
        self.status_stack.set_visible_child_name("idle")
        return False

    def _on_sent(self, _mgr, _length) -> None:
        self._set_status("sending")
        # 鼠标侧确认通常 0.7-1 秒到达; 超时(如鼠标休眠)自动复位
        if self._status_reset is not None:
            GLib.source_remove(self._status_reset)
        self._status_reset = GLib.timeout_add(2600, self._reset_status)

    def _on_ack(self, _mgr, _command, ok: bool) -> None:
        self._set_status("ok" if ok else "error", reset_after=1.8)
        if not ok:
            self.toast("鼠标可能休眠中，已安排自动重试（唤醒后自动应用）")

    # ------------------------------------------------------------ 设备
    def _on_device_changed(self, _mgr, connected: bool, info) -> None:
        dashboard = self.pages["dashboard"]
        if connected and info is not None:
            dashboard.set_device(info)
            self.toast(f"已连接 {info.label}")
        else:
            dashboard.set_device(None)
            self.mini_battery.set_visible(False)
        self.pages["about"].set_device(info)

    def _on_battery(self, _mgr, status: int, level: int) -> None:
        if status < 0 or level < 0:
            return
        charging = status in (P.BATTERY_CHARGING, P.BATTERY_FULL)
        self.mini_battery.set_state(level, charging)
        self.mini_battery.set_visible(True)
        self.pages["dashboard"].set_battery(status, level)
        self.pages["about"].set_battery(status, level)

    def _on_dpi_cycle(self, _mgr, stage: int) -> None:
        self.config.active_stage = stage
        self.save_config()
        self.pages["dpi"].refresh()
        self.pages["dashboard"].refresh()

    # ------------------------------------------------------------ 下发
    def save_config(self) -> None:
        self.config.save()

    def _debounce(self, key: str, callback, delay_ms: int = 220) -> None:
        timer = self._timers.pop(key, None)
        if timer is not None:
            GLib.source_remove(timer)

        def run() -> bool:
            self._timers.pop(key, None)
            callback()
            return False

        self._timers[key] = GLib.timeout_add(delay_ms, run)

    # 各组命令
    def build_dpi(self) -> bytes:
        return P.build_dpi_packet(
            self.config.dpi_values,
            self.config.active_stage,
            active_mask=self.config.active_mask(),
            lift_off_distance=self.config.lift_off,
            ripple=self.config.ripple,
            angle_snap=self.config.angle_snap,
            motion_sync=self.config.motion_sync,
            colors=[tuple(c) for c in self.config.dpi_colors],
        )

    def build_polling(self) -> bytes:
        return P.build_polling_packet(self.config.polling_rate)

    def build_lighting(self) -> bytes:
        return P.build_lighting_packet(
            light_mode=self.config.light_mode,
            brightness=self.config.brightness,
            speed=self.config.speed,
            red=self.config.color[0],
            green=self.config.color[1],
            blue=self.config.color[2],
            sleep_minutes=self.config.sleep_minutes,
            deep_sleep_minutes=self.config.deep_sleep_minutes,
            debounce_ms=self.config.debounce_ms,
        )

    def build_buttons(self) -> bytes:
        return P.build_buttons_packet([b.to_action() for b in self.config.buttons])

    def push_dpi(self) -> None:
        self.save_config()
        self.manager.send(self.build_dpi())

    def push_polling(self) -> None:
        self.save_config()
        self.manager.send(self.build_polling())

    def push_lighting(self) -> None:
        self.save_config()
        self.manager.send(self.build_lighting())

    def push_buttons(self) -> None:
        self.save_config()
        self.manager.send(self.build_buttons())

    def push_macro(self, macro_id: int) -> None:
        """下发指定编号的宏 (两页分包)."""
        macro = self.config.macros.get(str(macro_id))
        if macro is None or not macro.actions:
            return
        actions = [P.MacroAction(**a) for a in macro.actions]
        payload = P.build_macro_payload(
            macro_id,
            trigger=macro.trigger,
            loops=macro.loops,
            actions=actions,
            color=tuple(macro.color),
        )
        self.save_config()
        self.manager.send_pages(P.build_macro_pages(payload))

    def push_all(self, manual: bool = False) -> None:
        if not self.manager.connected:
            if manual:
                self.toast("设备未连接")
            return
        self.save_config()
        self.manager.send_many(
            [self.build_dpi(), self.build_polling(), self.build_lighting(), self.build_buttons()]
        )
        if manual:
            self.toast("已重新应用全部设置")
