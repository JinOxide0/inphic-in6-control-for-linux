"""应用入口."""
from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from . import i18n
from .config import Config
from .device_manager import DeviceManager
from .ui.window import MainWindow

APP_ID = "io.github.inphic.InphicControl"


class InphicControlApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.config = Config.load()
        i18n.set_language(self.config.language)
        self.manager = DeviceManager()
        self.window: MainWindow | None = None

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)

        provider = Gtk.CssProvider()
        provider.load_from_path(str(Path(__file__).parent / "style.css"))
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def do_activate(self) -> None:
        if self.window is None:
            self.window = MainWindow(self.config, self.manager, application=self)
            self.manager.start()
        self.window.present()

    def do_shutdown(self) -> None:
        self.manager.stop()
        Adw.Application.do_shutdown(self)

    # ------------------------------------------------------------ 语言
    def apply_language(self, preference: str) -> None:
        """切换界面语言 (字符串在构建期生效, 因此重建窗口)."""
        self.config.language = preference
        self.config.save()
        i18n.set_language(preference)
        GLib.idle_add(self._rebuild_window)

    def _rebuild_window(self) -> bool:
        old = self.window
        self.window = MainWindow(self.config, self.manager, application=self)
        self.window.present()
        if old is not None:
            old.destroy()
            self.window.toast(i18n._("语言已切换"))
        return False


def main(argv: list[str] | None = None) -> int:
    app = InphicControlApp()
    return app.run(argv)
