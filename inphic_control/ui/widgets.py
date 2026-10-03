"""自定义 UI 组件."""
from __future__ import annotations

import math

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GObject, Gtk

from ..i18n import _
from ..protocol import (
    BATTERY_CHARGING,
    BATTERY_FULL,
    BATTERY_NORMAL,
)


def battery_text(status: int | None, level: int | None) -> str:
    if status == BATTERY_FULL:
        return _("已充满")
    if status == BATTERY_CHARGING:
        return _("充电中")
    return _("使用中")


class BatteryPill(Gtk.DrawingArea):
    """自绘电池胶囊: 外框 + 电量填充 + 充电闪电."""

    def __init__(self, width: int = 64, height: int = 26):
        super().__init__()
        self.set_content_width(width)
        self.set_content_height(height)
        self.add_css_class("battery-pill")
        self._level = -1
        self._charging = False
        self.set_draw_func(self._draw)

    def set_state(self, level: int | None, charging: bool) -> None:
        self._level = -1 if level is None else max(0, min(100, level))
        self._charging = charging
        self.queue_draw()

    def _draw(self, _area, cr, width, height):
        # 颜色
        level = self._level
        unknown = level < 0
        if self._charging:
            fill = (0.30, 0.72, 0.45, 0.95)
        elif unknown:
            fill = (0, 0, 0, 0)
        elif level <= 15:
            fill = (0.92, 0.35, 0.35, 0.95)
        elif level <= 35:
            fill = (0.95, 0.72, 0.30, 0.95)
        else:
            fill = (0.36, 0.61, 1.0, 0.95)

        margin = 1.5
        radius = (height - margin * 2) / 2
        x0, y0 = margin, margin
        x1, y1 = width - 5 - margin, height - margin

        # 外框
        cr.set_line_width(1.6)
        cr.set_source_rgba(1, 1, 1, 0.28 if not unknown else 0.16)
        _rounded_rect(cr, x0, y0, x1 - x0, y1 - y0, radius)
        cr.stroke()

        # 电池头
        cr.set_source_rgba(1, 1, 1, 0.28 if not unknown else 0.16)
        _rounded_rect(cr, x1 + 1.0, height / 2 - 4, 3.2, 8, 1.4)
        cr.fill()

        # 填充
        pad = 3.0
        inner_w = max(0.0, (x1 - x0 - pad * 2) * max(0, level) / 100.0)
        if inner_w > 0.5:
            cr.set_source_rgba(*fill)
            _rounded_rect(cr, x0 + pad, y0 + pad, inner_w, y1 - y0 - pad * 2, max(1.0, radius - pad))
            cr.fill()

        if self._charging:
            cx, cy = (x0 + x1) / 2, height / 2
            cr.set_source_rgba(1, 1, 1, 0.95)
            cr.set_line_width(2.2)
            cr.set_line_cap(1)  # cairo.LINE_CAP_ROUND
            cr.move_to(cx + 1.5, cy - 5)
            cr.line_to(cx - 2.0, cy + 0.5)
            cr.line_to(cx + 1.0, cy + 0.5)
            cr.line_to(cx - 1.5, cy + 5)
            cr.stroke()


def _rounded_rect(cr, x, y, w, h, r):
    r = max(0.0, min(r, w / 2, h / 2))
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


class HeroCard(Gtk.Box):
    """仪表盘顶部大卡片."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add_css_class("hero-card")

        inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        inner.set_margin_top(22)
        inner.set_margin_bottom(22)
        inner.set_margin_start(24)
        inner.set_margin_end(24)
        self.append(inner)

        self.icon = Gtk.Image.new_from_icon_name("input-mouse-symbolic")
        self.icon.set_pixel_size(64)
        self.icon.add_css_class("hero-icon")
        self.icon.set_valign(Gtk.Align.CENTER)
        inner.append(self.icon)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info.set_valign(Gtk.Align.CENTER)
        info.set_hexpand(True)
        inner.append(info)

        self.title = Gtk.Label(label=_("未检测到设备"))
        self.title.set_xalign(0)
        self.title.add_css_class("hero-title")
        info.append(self.title)

        self.subtitle = Gtk.Label(label=_("请将 8K 接收器插入 USB 端口"))
        self.subtitle.set_xalign(0)
        self.subtitle.add_css_class("hero-subtitle")
        info.append(self.subtitle)

        self.conn_chip = Gtk.Label(label=_("未连接"))
        self.conn_chip.add_css_class("chip")
        self.conn_chip.add_css_class("chip-offline")
        self.conn_chip.set_halign(Gtk.Align.START)
        self.conn_chip.set_valign(Gtk.Align.CENTER)
        inner.append(self.conn_chip)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        right.set_valign(Gtk.Align.CENTER)
        right.set_halign(Gtk.Align.END)
        inner.append(right)

        self.battery = BatteryPill(84, 30)
        self.battery.set_halign(Gtk.Align.CENTER)
        right.append(self.battery)

        self.battery_label = Gtk.Label(label="--")
        self.battery_label.add_css_class("hero-battery")
        self.battery_label.set_halign(Gtk.Align.CENTER)
        right.append(self.battery_label)

    def set_connected(self, connected: bool, label: str = "", wired: bool = False) -> None:
        if connected:
            self.title.set_label(label or _("Inphic 设备"))
            self.subtitle.set_label(_("8K 接收器") if not wired else _("USB 有线连接"))
            self.conn_chip.set_label(_("已连接"))
            self.conn_chip.remove_css_class("chip-offline")
            self.conn_chip.add_css_class("chip-online")
        else:
            self.title.set_label(_("未检测到设备"))
            self.subtitle.set_label(_("请使用 8K 接收器或有线连接（蓝牙模式不支持配置）"))
            self.conn_chip.set_label(_("未连接"))
            self.conn_chip.remove_css_class("chip-online")
            self.conn_chip.add_css_class("chip-offline")

    def set_battery(self, status: int | None, level: int | None) -> None:
        charging = status in (BATTERY_CHARGING, BATTERY_FULL)
        self.battery.set_state(level, charging)
        if level is None:
            self.battery_label.set_label("--")
        else:
            suffix = f" · {battery_text(status, level)}"
            self.battery_label.set_label(f"{level}%{suffix}")


class StatTile(Gtk.Box):
    """仪表盘上的小统计卡片."""

    def __init__(self, icon: str, title: str, value: str = "—"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.add_css_class("stat-tile")
        self.set_hexpand(True)

        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        img = Gtk.Image.new_from_icon_name(icon)
        img.add_css_class("stat-icon")
        head.append(img)
        label = Gtk.Label(label=title)
        label.add_css_class("stat-title")
        label.set_xalign(0)
        head.append(label)
        self.append(head)

        self.value_label = Gtk.Label(label=value)
        self.value_label.set_xalign(0)
        self.value_label.add_css_class("stat-value")
        self.append(self.value_label)

        self.detail_label = Gtk.Label(label="")
        self.detail_label.set_xalign(0)
        self.detail_label.add_css_class("stat-detail")
        self.detail_label.set_visible(False)
        self.append(self.detail_label)

    def set_value(self, value: str, detail: str | None = None) -> None:
        self.value_label.set_label(value)
        if detail is not None:
            self.detail_label.set_label(detail)
            self.detail_label.set_visible(bool(detail))


class SidebarRow(Gtk.ListBoxRow):
    def __init__(self, page_id: str, title: str, icon_name: str):
        super().__init__()
        self.page_id = page_id
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(9)
        box.set_margin_bottom(9)
        box.set_margin_start(12)
        box.set_margin_end(12)
        self.set_child(box)

        image = Gtk.Image.new_from_icon_name(icon_name)
        image.set_pixel_size(18)
        box.append(image)

        label = Gtk.Label(label=title)
        label.set_xalign(0)
        label.set_hexpand(True)
        box.append(label)


class ShortcutDialog(Adw.Dialog):
    """捕获一个键盘组合键."""

    __gtype_name__ = "ShortcutDialog"

    def __init__(self, mods: int = 0, usage: int = 0):
        super().__init__()
        self.set_title(_("设置键盘快捷键"))
        self.set_content_width(420)
        self.set_content_height(260)
        self._mods = mods
        self._usage = usage
        self.result: tuple[int, int] | None = None

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_show_start_title_buttons(False)
        header.set_show_end_title_buttons(False)
        toolbar.add_top_bar(header)

        cancel = Gtk.Button(label=_("取消"))
        cancel.connect("clicked", lambda *_: self.close())
        header.pack_start(cancel)

        ok = Gtk.Button(label=_("确定"))
        ok.add_css_class("suggested-action")
        ok.connect("clicked", self._on_ok)
        header.pack_end(ok)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        body.set_margin_top(28)
        body.set_margin_bottom(28)
        body.set_margin_start(28)
        body.set_margin_end(28)
        toolbar.set_content(body)

        hint = Gtk.Label(label=_("请直接按下想要绑定的按键组合"))
        hint.add_css_class("dim-label")
        body.append(hint)

        self.display = Gtk.Label(label="—")
        self.display.add_css_class("shortcut-display")
        self.display.set_hexpand(True)
        self.display.set_valign(Gtk.Align.CENTER)
        body.append(self.display)

        self.warning = Gtk.Label(label="")
        self.warning.add_css_class("error-label")
        body.append(self.warning)

        self.set_child(toolbar)
        self._update_display()

        controller = Gtk.EventControllerKey()
        controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        controller.connect("key-pressed", self._on_key)
        body.add_controller(controller)
        body.set_focusable(True)
        self._key_body = body

    def grab_keys(self) -> None:
        """聚焦内部区域, 保证按键事件能被捕获."""
        self._key_body.grab_focus()

    def _update_display(self) -> None:
        from .. import keys

        if self._usage == 0:
            self.display.set_label("—")
        else:
            self.display.set_label(keys.describe_shortcut(self._mods, self._usage))

    def _on_key(self, _c, keyval, _keycode, state) -> bool:
        from gi.repository import Gdk

        from .. import keys

        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        usage = keys.keyval_to_usage(keyval)
        if usage is None or 224 <= usage <= 231:
            self.warning.set_label(_("该按键不支持，请换一个"))
            return True
        self.warning.set_label("")
        self._mods = keys.modifier_mask(state)
        self._usage = usage
        self._update_display()
        return True

    def _on_ok(self, _btn) -> None:
        if self._usage == 0:
            self.warning.set_label(_("请先按下一个按键"))
            return
        self.result = (self._mods, self._usage)
        self.close()


def color_button(rgba_hex: str | None = None, *, size: int = 24) -> Gtk.ColorDialogButton:
    button = Gtk.ColorDialogButton()
    dialog = Gtk.ColorDialog()
    dialog.set_with_alpha(False)
    button.set_dialog(dialog)
    button.add_css_class("color-button")
    button.set_size_request(size, size)
    if rgba_hex:
        rgba = Gdk.RGBA()
        rgba.parse(rgba_hex)
        button.set_rgba(rgba)
    return button


def rgba_hex(rgba: Gdk.RGBA) -> str:
    return "#%02X%02X%02X" % (
        round(rgba.red * 255),
        round(rgba.green * 255),
        round(rgba.blue * 255),
    )


def slider(minimum: float, maximum: float, step: float, value: float) -> Gtk.Scale:
    scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, minimum, maximum, step)
    scale.set_value(value)
    scale.set_draw_value(False)
    scale.set_size_request(200, -1)
    scale.add_css_class("slider")
    return scale


def value_label(text: str, width: int = 76) -> Gtk.Label:
    label = Gtk.Label(label=text)
    label.set_size_request(width, -1)
    label.set_xalign(1)
    label.add_css_class("value-label")
    return label


class SegmentedControl(Gtk.Box):
    """一排互斥按钮 (图标/文字均可)."""

    def __init__(self, options: list[tuple[str, object]], css: str = "segmented"):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add_css_class(css)
        self.add_css_class("linked")
        self._buttons: dict[object, Gtk.ToggleButton] = {}
        first = None
        for label, value in options:
            button = Gtk.ToggleButton(label=label)
            button.add_css_class("segment")
            if first is None:
                first = button
            else:
                button.set_group(first)
            button.connect("toggled", self._on_toggled, value)
            self.append(button)
            self._buttons[value] = button
        self._callback = None

    def _on_toggled(self, button: Gtk.ToggleButton, value) -> None:
        if button.get_active() and self._callback:
            self._callback(value)

    def connect_changed(self, callback) -> None:
        self._callback = callback

    def set_value(self, value, *, notify: bool = False) -> None:
        button = self._buttons.get(value)
        if button is None:
            return
        old = self._callback
        if not notify:
            self._callback = None
        button.set_active(True)
        self._callback = old
