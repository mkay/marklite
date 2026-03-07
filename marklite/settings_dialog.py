import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


class SettingsDialog(Adw.PreferencesDialog):
    def __init__(self, settings):
        super().__init__(title="Preferences")
        self._settings = settings
        self._build_ui()

    def _build_ui(self):
        # --- General page ---
        general_page = Adw.PreferencesPage(
            title="General",
            icon_name="preferences-other-symbolic",
        )

        # Directory group
        dir_group = Adw.PreferencesGroup(title="Files")

        dir_row = Adw.EntryRow(title="Root Directory")
        dir_row.set_text(self._settings.get("root_directory"))
        dir_row.connect("changed", self._on_root_dir_changed)
        dir_group.add(dir_row)

        watch_row = Adw.SwitchRow(
            title="File Watching",
            subtitle="Auto-reload when files change on disk",
        )
        watch_row.set_active(self._settings.file_watching)
        watch_row.connect("notify::active", self._on_file_watching_changed)
        dir_group.add(watch_row)

        general_page.add(dir_group)

        # Theme group
        theme_group = Adw.PreferencesGroup(title="Appearance")

        theme_row = Adw.ComboRow(title="App Theme")
        theme_list = Gtk.StringList.new(["System", "Light", "Dark"])
        theme_row.set_model(theme_list)
        idx = {"system": 0, "light": 1, "dark": 2}.get(self._settings.theme, 0)
        theme_row.set_selected(idx)
        theme_row.connect("notify::selected", self._on_theme_changed)
        theme_group.add(theme_row)
        self._theme_row = theme_row

        viewer_theme_row = Adw.ComboRow(title="Viewer Theme")
        viewer_theme_row.set_subtitle("Style used when reading documents")
        _VIEWER_THEMES = [
            ("Auto", "auto"),
            ("GitHub", "github"),
            ("GitHub Dark", "github-dark"),
            ("Sepia", "sepia"),
            ("Solarized Light", "solarized-light"),
            ("Solarized Dark", "solarized-dark"),
        ]
        viewer_theme_row.set_model(
            Gtk.StringList.new([label for label, _ in _VIEWER_THEMES])
        )
        viewer_theme_keys = [key for _, key in _VIEWER_THEMES]
        current_vt = self._settings.viewer_theme
        viewer_theme_row.set_selected(
            viewer_theme_keys.index(current_vt) if current_vt in viewer_theme_keys else 0
        )
        viewer_theme_row.connect(
            "notify::selected",
            lambda row, _: self._settings.set(
                "viewer_theme", viewer_theme_keys[row.get_selected()]
            ),
        )
        theme_group.add(viewer_theme_row)

        general_page.add(theme_group)
        self.add(general_page)

        # --- Fonts page ---
        fonts_page = Adw.PreferencesPage(
            title="Fonts",
            icon_name="font-select-symbolic",
        )

        viewer_group = Adw.PreferencesGroup(title="Viewer Font")

        font_row = Adw.EntryRow(title="Font Family")
        font_row.set_text(self._settings.font_family)
        font_row.connect("changed", self._on_font_family_changed)
        viewer_group.add(font_row)

        size_row = Adw.SpinRow.new_with_range(8, 32, 1)
        size_row.set_title("Font Size")
        size_row.set_value(self._settings.font_size)
        size_row.connect("notify::value", self._on_font_size_changed)
        viewer_group.add(size_row)

        fonts_page.add(viewer_group)

        editor_group = Adw.PreferencesGroup(title="Editor Font")

        ed_font_row = Adw.EntryRow(title="Font Family")
        ed_font_row.set_text(self._settings.editor_font_family)
        ed_font_row.connect("changed", self._on_editor_font_family_changed)
        editor_group.add(ed_font_row)

        ed_size_row = Adw.SpinRow.new_with_range(8, 32, 1)
        ed_size_row.set_title("Font Size")
        ed_size_row.set_value(self._settings.editor_font_size)
        ed_size_row.connect("notify::value", self._on_editor_font_size_changed)
        editor_group.add(ed_size_row)

        fonts_page.add(editor_group)
        self.add(fonts_page)

        # --- Editor page ---
        editor_page = Adw.PreferencesPage(
            title="Editor",
            icon_name="text-editor-symbolic",
        )

        editor_appearance_group = Adw.PreferencesGroup(title="Appearance")

        _EDITOR_THEMES = [
            ("Auto", "auto"),
            ("Adwaita Light", "adwaita-light"),
            ("One Dark", "one-dark"),
            ("GitHub Light", "github-light"),
            ("GitHub Dark", "github-dark"),
            ("Dracula", "dracula"),
            ("Solarized Light", "solarized-light"),
            ("Solarized Dark", "solarized-dark"),
            ("Tokyo Night", "tokyo-night"),
        ]
        self._editor_theme_keys = [key for _, key in _EDITOR_THEMES]

        theme_row = Adw.ComboRow(title="Color Theme")
        theme_row.set_model(
            Gtk.StringList.new([label for label, _ in _EDITOR_THEMES])
        )
        current_et = self._settings.editor_theme
        theme_row.set_selected(
            self._editor_theme_keys.index(current_et)
            if current_et in self._editor_theme_keys else 0
        )
        theme_row.connect("notify::selected", self._on_editor_theme_changed)
        editor_appearance_group.add(theme_row)

        line_numbers_row = Adw.SwitchRow(title="Line Numbers")
        line_numbers_row.set_active(self._settings.editor_line_numbers)
        line_numbers_row.connect("notify::active", self._on_line_numbers_changed)
        editor_appearance_group.add(line_numbers_row)

        line_wrap_row = Adw.SwitchRow(title="Line Wrap")
        line_wrap_row.set_active(self._settings.editor_line_wrap)
        line_wrap_row.connect("notify::active", self._on_line_wrap_changed)
        editor_appearance_group.add(line_wrap_row)

        editor_page.add(editor_appearance_group)

        editor_shortcuts_group = Adw.PreferencesGroup(title="Shortcuts")

        edit_shortcut_row = Adw.EntryRow(title="Toggle Edit Mode")
        edit_shortcut_row.set_text(self._settings.edit_shortcut)
        edit_shortcut_row.connect("changed", self._on_edit_shortcut_changed)
        editor_shortcuts_group.add(edit_shortcut_row)

        editor_page.add(editor_shortcuts_group)
        self.add(editor_page)

    def _on_root_dir_changed(self, row):
        self._settings.set("root_directory", row.get_text())

    def _on_file_watching_changed(self, row, _pspec):
        self._settings.set("file_watching", row.get_active())

    def _on_theme_changed(self, row, _pspec):
        themes = ["system", "light", "dark"]
        self._settings.set("theme", themes[row.get_selected()])

    def _on_font_family_changed(self, row):
        self._settings.set("font_family", row.get_text())

    def _on_font_size_changed(self, row, _pspec):
        self._settings.set("font_size", int(row.get_value()))

    def _on_editor_font_family_changed(self, row):
        self._settings.set("editor_font_family", row.get_text())

    def _on_editor_font_size_changed(self, row, _pspec):
        self._settings.set("editor_font_size", int(row.get_value()))

    def _on_editor_theme_changed(self, row, _pspec):
        self._settings.set("editor_theme", self._editor_theme_keys[row.get_selected()])

    def _on_line_numbers_changed(self, row, _pspec):
        self._settings.set("editor_line_numbers", row.get_active())

    def _on_line_wrap_changed(self, row, _pspec):
        self._settings.set("editor_line_wrap", row.get_active())

    def _on_edit_shortcut_changed(self, row):
        self._settings.set("edit_shortcut", row.get_text())
