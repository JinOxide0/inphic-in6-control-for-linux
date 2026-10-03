"""关于 / 诊断页."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from .. import __version__
from ..i18n import _
from .widgets import battery_text

LANGUAGE_IDS = ["auto", "zh", "en"]


class AboutPage(Adw.PreferencesPage):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._battery_status: int | None = None
        self._battery_level: int | None = None

        device_group = Adw.PreferencesGroup(title=_("设备"))
        self.add(device_group)

        self.name_row = Adw.ActionRow(title=_("设备名称"), subtitle=_("未连接"))
        self.id_row = Adw.ActionRow(title="USB ID", subtitle="—")
        self.iface_row = Adw.ActionRow(title=_("命令接口"), subtitle="—")
        self.battery_row = Adw.ActionRow(title=_("电量"), subtitle="—")
        for row in (self.name_row, self.id_row, self.iface_row, self.battery_row):
            device_group.add(row)

        group = Adw.PreferencesGroup(title=_("协议"))
        self.add(group)
        group.add(
            Adw.ActionRow(
                title=_("IN6 配置协议"),
                subtitle=_("Report ID 4 · 厂商接口 · 命令类型 4/5/6/8/9"),
            )
        )
        group.add(
            Adw.ActionRow(
                title=_("支持功能"),
                subtitle=_("DPI · 轮询率 · 灯光 · 性能 · 按键映射 · 宏 (两页分包)"),
            )
        )
        group.add(
            Adw.ActionRow(
                title=_("协议来源"),
                subtitle=_("由官方 Web 驱动物理分析 + 社区逆向文档交叉验证"),
            )
        )
        group.add(
            Adw.ActionRow(
                title=_("感谢"),
                subtitle="HarukaYamamoto0/attack-shark-x11-driver · D3m0nZOnFire/mousectl",
            )
        )

        lang_group = Adw.PreferencesGroup(title=_("界面语言"))
        self.add(lang_group)
        self.language_row = Adw.ComboRow(title=_("语言"))
        self.language_row.set_model(
            Gtk.StringList.new([_("跟随系统"), "简体中文", "English"])
        )
        current = window.config.language if window.config.language in LANGUAGE_IDS else "auto"
        self.language_row.set_selected(LANGUAGE_IDS.index(current))
        self.language_row.connect("notify::selected", self._on_language_changed)
        lang_group.add(self.language_row)

        self.perm_group = Adw.PreferencesGroup(title=_("权限"))
        self.add(self.perm_group)
        self.perm_row = Adw.ActionRow(
            title=_("hidraw 访问权限"),
            subtitle=_("RPM 已安装 udev 规则, 重新插拔接收器后生效"),
        )
        self.perm_group.add(self.perm_row)

        about = Adw.PreferencesGroup(title=_("关于"))
        self.add(about)
        about.add(
            Adw.ActionRow(
                title="Inphic Control",
                subtitle=_("版本 {version} · GTK4 / libadwaita").format(version=__version__),
            )
        )
        about.add(
            Adw.ActionRow(
                title=_("支持的设备"),
                subtitle=_("Inphic IN6 / IN6SE · 8K 接收器 (1d57:fa65)"),
            )
        )

    # ------------------------------------------------------------ 语言
    def _on_language_changed(self, row: Adw.ComboRow, _pspec) -> None:
        index = row.get_selected()
        if 0 <= index < len(LANGUAGE_IDS):
            self.window.set_language(LANGUAGE_IDS[index])

    # ------------------------------------------------------------ 设备
    def set_device(self, info) -> None:
        if info is None:
            self.name_row.set_subtitle(_("未连接"))
            self.id_row.set_subtitle("—")
            self.iface_row.set_subtitle("—")
            return
        self.name_row.set_subtitle(info.label)
        self.id_row.set_subtitle(f"{info.vid:04x}:{info.pid:04x}")
        self.iface_row.set_subtitle(f"{info.interface} · {info.hidraw}")

    def set_battery(self, status: int, level: int) -> None:
        self._battery_status = status
        self._battery_level = level
        self.battery_row.set_subtitle(f"{level}% · {battery_text(status, level)}")

    def refresh(self) -> None:
        pass
