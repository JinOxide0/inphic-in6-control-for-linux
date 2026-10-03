"""按键映射页."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from .. import keys, protocol as P
from ..config import ButtonBinding
from ..i18n import _
from .widgets import ShortcutDialog

# (preset id, 显示名)
PRESETS: list[tuple[str, str]] = [
    ("off", "无功能"),
    ("left", "鼠标左键"),
    ("right", "鼠标右键"),
    ("middle", "鼠标中键"),
    ("backward", "后退"),
    ("forward", "前进"),
    ("double_click", "双击"),
    ("dpi_cycle", "DPI 循环"),
    ("dpi_up", "DPI +"),
    ("dpi_down", "DPI -"),
    ("scroll_up", "向上滚动"),
    ("scroll_down", "向下滚动"),
    ("tilt_left", "滚轮左倾"),
    ("tilt_right", "滚轮右倾"),
    ("easy_aim", "狙击键 (Easy Aim)"),
    ("play_pause", "播放 / 暂停"),
    ("previous", "上一曲"),
    ("next", "下一曲"),
    ("media_stop", "停止播放"),
    ("media_player", "打开播放器"),
    ("volume_up", "音量 +"),
    ("volume_down", "音量 -"),
    ("mute", "静音"),
    ("calculator", "计算器"),
    ("email", "邮件"),
    ("browser_back", "浏览器后退"),
    ("browser_forward", "浏览器前进"),
    ("browser_refresh", "刷新浏览器"),
    ("browser_home", "浏览器主页"),
    ("browser_search", "浏览器搜索"),
    ("copy", "复制"),
    ("paste", "粘贴"),
    ("cut", "剪切"),
    ("undo", "撤销"),
    ("redo", "重做"),
    ("select_all", "全选"),
    ("save", "保存"),
    ("find", "查找"),
    ("print", "打印"),
    ("swap_windows", "切换窗口"),
    ("close_window", "关闭窗口"),
    ("show_desktop", "显示桌面"),
    ("lock_pc", "锁定电脑"),
    ("run", "运行"),
    ("screenshot", "截图"),
    ("browser_favorites", "收藏夹"),
    ("profile_cycle", "配置循环"),
    ("profile_up", "上一配置"),
    ("profile_down", "下一配置"),
]

SHORTCUT_ITEM = "键盘快捷键…"
MACRO_ITEM = "宏…"


class ButtonsPage(Adw.PreferencesPage):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._syncing = False
        self.rows: list[tuple[int, int, Adw.ActionRow, Gtk.DropDown]] = []

        group = Adw.PreferencesGroup(
            title=_("鼠标按键"),
            description=_("修改后立即写入鼠标"),
        )
        self.add(group)

        items = [_(label) for _key, label in PRESETS] + [_(SHORTCUT_ITEM), _(MACRO_ITEM)]

        for ui_index, (slot_index, name) in enumerate(P.USER_BUTTONS):
            row = Adw.ActionRow(title=_(name))
            dropdown = Gtk.DropDown.new_from_strings(items)
            dropdown.set_valign(Gtk.Align.CENTER)
            dropdown.connect(
                "notify::selected", self._on_selected, slot_index, ui_index, row, dropdown
            )
            row.add_suffix(dropdown)
            group.add(row)
            self.rows.append((slot_index, ui_index, row, dropdown))

        note = Adw.PreferencesGroup(title=_("说明"))
        self.add(note)
        note.add(
            Adw.ActionRow(
                title=_("宏"),
                subtitle=_("选择「宏…」即可为按键录制键盘/移动宏"),
            )
        )
        note.add(
            Adw.ActionRow(
                title=_("其余 13 个功能槽位保持默认"),
                subtitle=_("DPI 键 / 模式键 / 滚轮等由固件固定处理"),
            )
        )

        self.refresh()

    # ------------------------------------------------------------ 交互
    def _on_selected(
        self, dropdown: Gtk.DropDown, _pspec, slot_index: int,
        ui_index: int, row: Adw.ActionRow, _dd,
    ) -> None:
        if self._syncing:
            return
        selected = dropdown.get_selected()
        cfg = self.window.config

        if selected == len(PRESETS):  # 自定义快捷键
            self._pick_shortcut(slot_index, row, dropdown)
            return
        if selected == len(PRESETS) + 1:  # 宏
            self._pick_macro(ui_index, row, dropdown)
            return

        preset = PRESETS[selected][0]
        cfg.buttons[slot_index] = ButtonBinding(kind="preset", preset=preset)
        row.set_subtitle(_(PRESETS[selected][1]))
        self.window.push_buttons()

    def _pick_macro(self, ui_index: int, row: Adw.ActionRow, dropdown: Gtk.DropDown) -> None:
        from .macro_dialog import MacroDialog

        macro_id = ui_index + 1
        name = row.get_title()
        dialog = MacroDialog(self.window, macro_id, name)
        dialog.connect("closed", lambda *_: self.refresh())
        dialog.present(self.window)

    def _pick_shortcut(self, slot_index: int, row: Adw.ActionRow, dropdown: Gtk.DropDown) -> None:
        current = self.window.config.buttons[slot_index]
        dialog = ShortcutDialog(
            current.mods if current.kind == "shortcut" else 0,
            current.usage if current.kind == "shortcut" else 0,
        )

        def on_closed(_dialog) -> None:
            if dialog.result is not None:
                mods, usage = dialog.result
                self.window.config.buttons[slot_index] = ButtonBinding(
                    kind="shortcut", mods=mods, usage=usage
                )
                row.set_subtitle(
                    _("键盘: {shortcut}").format(
                        shortcut=keys.describe_shortcut(mods, usage)
                    )
                )
                self.window.push_buttons()
            else:
                self.refresh()

        dialog.connect("closed", on_closed)
        dialog.present(self.window)
        dialog.grab_keys()

    # ------------------------------------------------------------ 同步
    def refresh(self) -> None:
        cfg = self.window.config
        self._syncing = True
        for slot_index, _ui_index, row, dropdown in self.rows:
            if slot_index >= len(cfg.buttons):
                continue
            binding = cfg.buttons[slot_index]
            if binding.kind == "shortcut":
                dropdown.set_selected(len(PRESETS))
                row.set_subtitle(
                    _("键盘: {shortcut}").format(
                        shortcut=keys.describe_shortcut(binding.mods, binding.usage)
                    )
                )
            elif binding.kind == "macro":
                dropdown.set_selected(len(PRESETS) + 1)
                macro = cfg.macros.get(str(binding.macro_id))
                if macro and macro.actions:
                    row.set_subtitle(
                        _("宏: {count} 个动作").format(count=len(macro.actions))
                    )
                else:
                    row.set_subtitle(_("宏: 未编辑"))
            else:
                ids = [preset for preset, _ in PRESETS]
                index = ids.index(binding.preset) if binding.preset in ids else 0
                dropdown.set_selected(index)
                row.set_subtitle(_(PRESETS[index][1]))
        self._syncing = False
