import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib

from marklite import APP_ID, APP_NAME, VERSION
from marklite.settings_manager import SettingsManager


class Application(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.settings = SettingsManager()

    def do_startup(self):
        Adw.Application.do_startup(self)
        self._apply_theme()
        self.settings.connect("changed", self._on_settings_changed)

    def _apply_theme(self):
        style = self.get_style_manager()
        theme = self.settings.theme
        if theme == "dark":
            style.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        elif theme == "light":
            style.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        else:
            style.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def _on_settings_changed(self, _mgr, key):
        if key == "theme":
            self._apply_theme()

    def do_activate(self):
        win = self.get_active_window()
        if not win:
            from marklite.window import MainWindow
            win = MainWindow(application=self, settings=self.settings)
        win.present()
