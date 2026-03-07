from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk, Gio, GLib

from marklite import APP_ID, APP_NAME, VERSION
from marklite.settings_manager import SettingsManager


class Application(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self.settings = SettingsManager()

    def do_startup(self):
        Adw.Application.do_startup(self)
        self._apply_theme()
        self.settings.connect("changed", self._on_settings_changed)
        self._register_icons()
        self._load_css()
        self._setup_actions()

    def _setup_actions(self):
        new_window = Gio.SimpleAction.new("new-window", None)
        new_window.connect("activate", self._on_new_window)
        self.add_action(new_window)
        self.set_accels_for_action("app.new-window", ["<Control><Shift>n"])

        window_size = Gio.SimpleAction.new("window-size", None)
        window_size.connect("activate", self._on_window_size)
        self.add_action(window_size)

    def _register_icons(self):
        pkg_dir = Path(__file__).parent
        gresource = pkg_dir / "data" / "de.singular.marklite.gresource"
        gresource_xml = pkg_dir / "data" / "de.singular.marklite.gresource.xml"
        if not gresource.exists() and gresource_xml.exists():
            # Dev mode: compile the gresource on the fly
            import subprocess
            subprocess.run(
                ["glib-compile-resources",
                 f"--sourcedir={pkg_dir / 'data'}",
                 str(gresource_xml),
                 f"--target={gresource}"],
                check=True,
            )
        if gresource.exists():
            Gio.resources_register(Gio.resource_load(str(gresource)))
            Gtk.IconTheme.get_for_display(
                Gdk.Display.get_default()
            ).add_resource_path("/de/singular/marklite/icons/hicolor")

    def _load_css(self):
        css = Gtk.CssProvider()
        css.load_from_string(
            ".app-sidebar { background-color: shade(@window_bg_color, 0.97); }"
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

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

    def do_command_line(self, command_line):
        args = command_line.get_arguments()[1:]
        if args:
            path = Path(args[0]).expanduser().resolve()
            if path.is_dir():
                self.settings.set_override("root_directory", str(path))
        self.do_activate()
        return 0

    def do_activate(self):
        win = self.get_active_window()
        if not win:
            from marklite.window import MainWindow
            win = MainWindow(application=self, settings=self.settings)
        win.present()

    def _on_new_window(self, _action, _param):
        from marklite.window import MainWindow
        win = MainWindow(application=self, settings=self.settings)
        win.present()

    def _on_window_size(self, _action, _param):
        win = self.props.active_window
        if not win:
            return

        dialog = Adw.Dialog(title="Window Size", content_width=320, content_height=220)

        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar(show_start_title_buttons=False, show_end_title_buttons=False)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda _: dialog.close())
        header.pack_start(cancel_btn)

        save_btn = Gtk.Button(label="Save", css_classes=["suggested-action"])
        header.pack_end(save_btn)
        toolbar_view.add_top_bar(header)

        clamp = Adw.Clamp(maximum_size=320, margin_top=16, margin_bottom=16, margin_start=16, margin_end=16)
        group = Adw.PreferencesGroup()

        width_row = Adw.SpinRow(
            title="Width",
            adjustment=Gtk.Adjustment(value=self.settings.window_width, lower=800, upper=3840, step_increment=10),
        )
        group.add(width_row)

        height_row = Adw.SpinRow(
            title="Height",
            adjustment=Gtk.Adjustment(value=self.settings.window_height, lower=600, upper=2160, step_increment=10),
        )
        group.add(height_row)

        clamp.set_child(group)
        toolbar_view.set_content(clamp)
        dialog.set_child(toolbar_view)

        def on_save(_):
            self.settings.set("window_width", int(width_row.get_value()))
            self.settings.set("window_height", int(height_row.get_value()))
            dialog.close()

        save_btn.connect("clicked", on_save)
        dialog.present(win)
