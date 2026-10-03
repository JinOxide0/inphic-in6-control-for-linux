"""关于 / 诊断页."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from .widgets import battery_text


class AboutPage(Adw.PreferencesPage):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._battery_status: int | None = None
        self._battery_level: int | None = None

        device_group = Adw.PreferencesGroup(title="设备")
        self.add(device_group)

        self.name_row = Adw.ActionRow(title="设备名称", subtitle="未连接")
        self.id_row = Adw.ActionRow(title="USB ID", subtitle="—")
        self.iface_row = Adw.ActionRow(title="命令接口", subtitle="—")
        self.battery_row = Adw.ActionRow(title="电量", subtitle="—")
        for row in (self.name_row, self.id_row, self.iface_row, self.battery_row):
            device_group.add(row)

        group = Adw.PreferencesGroup(title="协议")
        self.add(group)
        group.add(
            Adw.ActionRow(
                title="IN6 配置协议",
                subtitle="Report ID 4 · 厂商接口 · 命令类型 4/5/6/8/9",
            )
        )
        group.add(
            Adw.ActionRow(
                title="支持功能",
                subtitle="DPI · 轮询率 · 灯光 · 性能 · 按键映射 · 宏 (两页分包)",
            )
        )
        group.add(
            Adw.ActionRow(
                title="协议来源",
                subtitle="由官方 Web 驱动物理分析 + 社区逆向文档交叉验证",
            )
        )
        group.add(
            Adw.ActionRow(
                title="感谢",
                subtitle="HarukaYamamoto0/attack-shark-x11-driver · D3m0nZOnFire/mousectl",
            )
        )

        self.perm_group = Adw.PreferencesGroup(title="权限")
        self.add(self.perm_group)
        self.perm_row = Adw.ActionRow(
            title="hidraw 访问权限",
            subtitle="RPM 已安装 udev 规则, 重新插拔接收器后生效",
        )
        self.perm_group.add(self.perm_row)

        about = Adw.PreferencesGroup(title="关于")
        self.add(about)
        about.add(Adw.ActionRow(title="Inphic Control", subtitle="版本 0.3.0 · GTK4 / libadwaita"))
        about.add(
            Adw.ActionRow(
                title="支持的设备",
                subtitle="Inphic IN6 / IN6SE · 8K 接收器 (1d57:fa65)",
            )
        )

    def set_device(self, info) -> None:
        if info is None:
            self.name_row.set_subtitle("未连接")
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
