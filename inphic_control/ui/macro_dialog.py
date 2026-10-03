"""宏编辑对话框."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gtk

from .. import keys, protocol as P
from ..config import MacroDef

TRIGGER_LABELS = [
    "循环次数播放",
    "任意键按下停止",
    "按住播放，松开停止",
    "当前宏键按下停止",
]


class _KeyCaptureDialog(Adw.Dialog):
    """捕获一个按键 (宏内不支持修饰键, 只取单键)."""

    def __init__(self):
        super().__init__()
        self.set_title("捕获按键")
        self.set_content_width(380)
        self.set_content_height(230)
        self.usage: int | None = None

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_show_start_title_buttons(False)
        header.set_show_end_title_buttons(False)
        toolbar.add_top_bar(header)

        cancel = Gtk.Button(label="取消")
        cancel.connect("clicked", lambda *_: self.close())
        header.pack_start(cancel)
        ok = Gtk.Button(label="确定")
        ok.add_css_class("suggested-action")
        ok.connect("clicked", self._on_ok)
        header.pack_end(ok)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        body.set_margin_top(24)
        body.set_margin_bottom(24)
        body.set_margin_start(24)
        body.set_margin_end(24)
        toolbar.set_content(body)

        hint = Gtk.Label(label="按下要录制的按键（A-Z、0-9、F1-F24 等）")
        hint.add_css_class("dim-label")
        body.append(hint)

        self.display = Gtk.Label(label="—")
        self.display.add_css_class("shortcut-display")
        body.append(self.display)

        self.warning = Gtk.Label(label="")
        self.warning.add_css_class("error-label")
        body.append(self.warning)

        self.set_child(toolbar)

        controller = Gtk.EventControllerKey()
        controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        controller.connect("key-pressed", self._on_key)
        body.add_controller(controller)
        body.set_focusable(True)
        self._key_body = body

    def grab_keys(self) -> None:
        """聚焦内部区域, 保证按键事件能被捕获."""
        self._key_body.grab_focus()

    def _on_key(self, _c, keyval, _code, _state) -> bool:
        from gi.repository import Gdk as G

        if keyval == G.KEY_Escape:
            self.close()
            return True
        usage = keys.keyval_to_usage(keyval)
        if usage is None or 224 <= usage <= 231:
            self.warning.set_label("该按键不支持，请换一个")
            return True
        self.usage = usage
        self.display.set_label(keys.describe_key(usage))
        self.warning.set_label("")
        return True

    def _on_ok(self, _btn) -> None:
        if self.usage is None:
            self.warning.set_label("请先按下一个按键")
            return
        self.close()


class _MoveDialog(Adw.Dialog):
    """鼠标移动动作参数."""

    def __init__(self, x: int = 0, y: int = 0):
        super().__init__()
        self.set_title("鼠标移动")
        self.set_content_width(360)
        self.set_content_height(260)
        self.result: tuple[int, int] | None = None

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_show_start_title_buttons(False)
        header.set_show_end_title_buttons(False)
        toolbar.add_top_bar(header)

        cancel = Gtk.Button(label="取消")
        cancel.connect("clicked", lambda *_: self.close())
        header.pack_start(cancel)
        ok = Gtk.Button(label="确定")
        ok.add_css_class("suggested-action")
        ok.connect("clicked", self._on_ok)
        header.pack_end(ok)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        body.set_margin_top(20)
        body.set_margin_bottom(20)
        body.set_margin_start(20)
        body.set_margin_end(20)
        toolbar.set_content(body)

        self.x_spin = Gtk.SpinButton.new_with_range(-32768, 32767, 1)
        self.x_spin.set_value(x)
        self.y_spin = Gtk.SpinButton.new_with_range(-32768, 32767, 1)
        self.y_spin.set_value(y)

        row_x = Adw.ActionRow(title="水平移动 X", subtitle="-32768 ~ 32767 (像素)")
        row_x.add_suffix(self.x_spin)
        body.append(row_x)
        row_y = Adw.ActionRow(title="垂直移动 Y", subtitle="-32768 ~ 32767 (像素)")
        row_y.add_suffix(self.y_spin)
        body.append(row_y)

        self.set_child(toolbar)

    def _on_ok(self, _btn) -> None:
        self.result = (int(self.x_spin.get_value()), int(self.y_spin.get_value()))
        self.close()


class _ActionRow(Gtk.ListBoxRow):
    """一条宏动作."""

    def __init__(self, dialog: "MacroDialog", index: int, action: dict):
        super().__init__()
        self.dialog = dialog
        self.index = index

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        self.set_child(box)

        self.label = Gtk.Label(label="")
        self.label.set_xalign(0)
        self.label.set_hexpand(True)
        box.append(self.label)

        delay = Gtk.SpinButton.new_with_range(1, 25500, 10)
        delay.set_value(int(action.get("delay", 10)))
        delay.set_width_chars(5)
        delay.set_tooltip_text("与上一动作的间隔 (毫秒)")
        delay.connect("value-changed", self._on_delay)
        box.append(delay)

        label_ms = Gtk.Label(label="ms")
        label_ms.add_css_class("dim-label")
        box.append(label_ms)

        delete = Gtk.Button.new_from_icon_name("edit-delete-symbolic")
        delete.add_css_class("flat")
        delete.set_tooltip_text("删除此动作")
        delete.connect("clicked", self._on_delete)
        box.append(delete)

        self._update_label(action)

    def _update_label(self, action: dict) -> None:
        if action["kind"] == "key":
            name = keys.describe_key(int(action.get("key", 0)))
            state = "按下" if action.get("down", True) else "抬起"
            self.label.set_label(f"{state} {name}")
        else:
            self.label.set_label(
                f"移动 ({int(action.get('x', 0))}, {int(action.get('y', 0))})"
            )

    def _on_delay(self, spin: Gtk.SpinButton) -> None:
        action = self.dialog.actions[self.index]
        action["delay"] = int(spin.get_value())

    def _on_delete(self, _btn) -> None:
        self.dialog.actions.pop(self.index)
        self.dialog.rebuild()


class MacroDialog(Adw.Dialog):
    """编辑并保存一个宏."""

    def __init__(self, window, macro_id: int, button_name: str):
        super().__init__()
        self.window = window
        self.macro_id = macro_id
        self.set_title(f"编辑宏 — {button_name}")
        self.set_content_width(560)
        self.set_content_height(520)

        saved = window.config.macros.get(str(macro_id))
        self.trigger = saved.trigger if saved else 0
        self.loops = saved.loops if saved else 1
        self.actions: list[dict] = [dict(a) for a in (saved.actions if saved else [])]

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_show_start_title_buttons(False)
        header.set_show_end_title_buttons(False)
        toolbar.add_top_bar(header)

        cancel = Gtk.Button(label="取消")
        cancel.connect("clicked", lambda *_: self.close())
        header.pack_start(cancel)
        save = Gtk.Button(label="保存并应用")
        save.add_css_class("suggested-action")
        save.connect("clicked", self._on_save)
        header.pack_end(save)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_margin_top(14)
        content.set_margin_bottom(14)
        content.set_margin_start(16)
        content.set_margin_end(16)
        toolbar.set_content(content)

        # 触发方式 + 循环次数
        self.trigger_row = Adw.ComboRow(title="触发方式")
        self.trigger_row.set_model(Gtk.StringList.new(TRIGGER_LABELS))
        self.trigger_row.set_selected(self.trigger)
        self.trigger_row.connect("notify::selected", self._on_trigger)
        content.append(self.trigger_row)

        self.loops_row = Adw.SpinRow.new_with_range(1, 255, 1)
        self.loops_row.set_title("循环次数")
        self.loops_row.set_subtitle("触发方式为「循环次数播放」时生效")
        self.loops_row.set_value(self.loops)
        self.loops_row.connect("notify::value", self._on_loops)
        content.append(self.loops_row)

        hint = Gtk.Label(label="动作列表（每条动作的间隔 = 与上一动作的时间）")
        hint.add_css_class("dim-label")
        hint.set_xalign(0)
        hint.set_margin_top(6)
        content.append(hint)

        # 添加按钮 (置于列表上方, 始终可见可点)
        add_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        add_key = Gtk.Button(label="＋ 按键")
        add_key.connect("clicked", self._on_add_key)
        add_row.append(add_key)
        add_move = Gtk.Button(label="＋ 鼠标移动")
        add_move.connect("clicked", self._on_add_move)
        add_row.append(add_move)
        content.append(add_row)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.set_min_content_height(160)
        content.append(scroll)

        self.listbox = Gtk.ListBox()
        self.listbox.add_css_class("boxed-list")
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.set_child(self.listbox)

        self.empty_label = Gtk.Label(label="还没有动作，点击上方按钮添加")
        self.empty_label.add_css_class("dim-label")
        self.empty_label.set_margin_top(8)
        content.append(self.empty_label)

        self.set_child(toolbar)
        self.rebuild()
        self._sync_options()

    # ------------------------------------------------------------ 触发
    def _on_trigger(self, row: Adw.ComboRow, _pspec) -> None:
        self.trigger = int(row.get_selected())
        self._sync_options()

    def _on_loops(self, row: Adw.SpinRow, _pspec) -> None:
        self.loops = int(row.get_value())

    def _sync_options(self) -> None:
        self.loops_row.set_sensitive(self.trigger == 0)

    # ------------------------------------------------------------ 动作
    def rebuild(self) -> None:
        child = self.listbox.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.listbox.remove(child)
            child = nxt
        for i, action in enumerate(self.actions):
            self.listbox.append(_ActionRow(self, i, action))
        self.empty_label.set_visible(len(self.actions) == 0)

    def _on_add_key(self, _btn) -> None:
        dialog = _KeyCaptureDialog()

        def on_closed(_d) -> None:
            if dialog.usage is not None:
                self.actions.append(
                    {"kind": "key", "key": dialog.usage, "down": True, "delay": 10}
                )
                self.actions.append(
                    {"kind": "key", "key": dialog.usage, "down": False, "delay": 50}
                )
                self.rebuild()

        dialog.connect("closed", on_closed)
        dialog.present(self)
        dialog.grab_keys()

    def _on_add_move(self, _btn) -> None:
        dialog = _MoveDialog()

        def on_closed(_d) -> None:
            if dialog.result is not None:
                x, y = dialog.result
                self.actions.append({"kind": "move", "x": x, "y": y, "delay": 10})
                self.rebuild()

        dialog.connect("closed", on_closed)
        dialog.present(self)

    # ------------------------------------------------------------ 保存
    def _on_save(self, _btn) -> None:
        if not self.actions:
            self.window.toast("宏至少需要一个动作")
            return
        window = self.window
        macro = MacroDef(
            trigger=self.trigger,
            loops=self.loops,
            actions=self.actions,
        )
        window.config.macros[str(self.macro_id)] = macro
        window.save_config()
        self.close()

        # 绑定按键 + 下发宏
        from ..config import ButtonBinding

        for ui_index, (slot_index, _name) in enumerate(P.USER_BUTTONS):
            if ui_index + 1 == self.macro_id:
                window.config.buttons[slot_index] = ButtonBinding(
                    kind="macro", macro_id=self.macro_id
                )
        window.pages["buttons"].refresh()
        window.push_buttons()
        window.push_macro(self.macro_id)
