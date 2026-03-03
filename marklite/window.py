import os

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Gio

from marklite import APP_ID, APP_NAME, VERSION
from marklite.sidebar import Sidebar
from marklite.document_panel import DocumentPanel
from marklite.viewer import MarkdownViewer
from marklite.editor import MarkdownEditor
from marklite.welcome import WelcomeView


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, application, settings):
        super().__init__(application=application)
        self._settings = settings
        self._current_file = None
        self._editing = False
        self._watcher = None

        self.set_default_size(settings.window_width, settings.window_height)
        self.set_title(APP_NAME)

        self._build_ui()
        self._connect_signals()
        self._setup_actions()

    def _build_ui(self):
        # === Sidebar ToolbarView ===
        sidebar_header = Adw.HeaderBar(show_end_title_buttons=False)
        sidebar_header.set_title_widget(
            Gtk.Label(label=APP_NAME, css_classes=["title"])
        )

        self._sidebar = Sidebar(self._settings)

        sidebar_toolbar = Adw.ToolbarView()
        sidebar_toolbar.add_css_class("app-sidebar")
        sidebar_toolbar.add_top_bar(sidebar_header)
        sidebar_toolbar.set_content(self._sidebar)

        # === Content ToolbarView ===
        self._content_header = Adw.HeaderBar(show_start_title_buttons=False)

        # Edit toggle (start)
        self._edit_btn = Gtk.ToggleButton(
            icon_name="marklite-edit-symbolic",
            tooltip_text="Toggle edit mode",
            sensitive=False,
        )
        self._edit_btn.set_focus_on_click(False)
        self._content_header.pack_start(self._edit_btn)

        # Title
        self._title_widget = Adw.WindowTitle(title=APP_NAME, subtitle="")
        self._content_header.set_title_widget(self._title_widget)

        # Hamburger menu (rightmost end)
        menu = Gio.Menu()
        window_section = Gio.Menu()
        window_section.append("New Window", "app.new-window")
        window_section.append("Window Size", "app.window-size")
        menu.append_section(None, window_section)
        prefs_section = Gio.Menu()
        prefs_section.append("Preferences", "win.preferences")
        menu.append_section(None, prefs_section)
        about_section = Gio.Menu()
        about_section.append("About", "win.about")
        menu.append_section(None, about_section)
        menu_btn = Gtk.MenuButton(
            icon_name="marklite-open-menu-symbolic",
            menu_model=menu,
            tooltip_text="Menu",
        )
        menu_btn.set_focus_on_click(False)
        self._content_header.pack_end(menu_btn)

        # Sidebar toggle (left of menu)
        self._sidebar_btn = Gtk.Button(
            icon_name="marklite-sidebar-hide-symbolic",
            tooltip_text="Toggle sidebar",
        )
        self._sidebar_btn.set_focus_on_click(False)
        self._content_header.pack_end(self._sidebar_btn)

        # Content stack
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        self._welcome = WelcomeView()
        self._stack.add_named(self._welcome, "welcome")

        self._doc_panel = DocumentPanel(self._settings)
        self._stack.add_named(self._doc_panel, "documents")

        self._viewer = MarkdownViewer(self._settings)
        self._stack.add_named(self._viewer, "view")

        self._editor = MarkdownEditor(self._settings)
        self._stack.add_named(self._editor, "edit")

        self._stack.set_visible_child_name("welcome")

        content_toolbar = Adw.ToolbarView()
        content_toolbar.add_top_bar(self._content_header)
        content_toolbar.set_content(self._stack)

        # === Split View ===
        self._split_view = Adw.OverlaySplitView()
        self._split_view.set_show_sidebar(True)
        self._split_view.set_sidebar(sidebar_toolbar)
        self._split_view.set_content(content_toolbar)

        self.set_content(self._split_view)

    def _connect_signals(self):
        self._sidebar_btn.connect("clicked", self._on_sidebar_toggled)
        self._split_view.connect("notify::show-sidebar", self._on_split_sidebar_changed)
        self._edit_btn.connect("toggled", self._on_edit_toggled)
        self._sidebar.connect("folder-selected", self._on_folder_selected)
        self._doc_panel.connect("file-selected", self._on_file_selected)
        self._doc_panel.connect("file-trashed", self._on_file_trashed)
        self._doc_panel.connect("file-renamed", self._on_file_renamed)
        self._settings.connect("changed", self._on_settings_changed)

    def _setup_actions(self):
        prefs = Gio.SimpleAction.new("preferences", None)
        prefs.connect("activate", self._on_preferences)
        self.add_action(prefs)

        about = Gio.SimpleAction.new("about", None)
        about.connect("activate", self._on_about)
        self.add_action(about)

        find = Gio.SimpleAction.new("find", None)
        find.connect("activate", self._on_find)
        self.add_action(find)
        self.get_application().set_accels_for_action("win.find", ["<Control>f"])

    def _on_find(self, *_args):
        if self._editing:
            self._editor.toggle_search()
        else:
            self._viewer.toggle_search()

    def _on_sidebar_toggled(self, _btn):
        self._split_view.set_show_sidebar(not self._split_view.get_show_sidebar())

    def _on_split_sidebar_changed(self, split_view, _param):
        if split_view.get_show_sidebar():
            self._sidebar_btn.set_icon_name("marklite-sidebar-hide-symbolic")
        else:
            self._sidebar_btn.set_icon_name("marklite-sidebar-show-symbolic")

    def _on_edit_toggled(self, btn):
        if not self._current_file:
            btn.set_active(False)
            return

        if btn.get_active():
            # Enter edit mode
            try:
                with open(self._current_file, encoding="utf-8") as f:
                    text = f.read()
            except OSError:
                btn.set_active(False)
                return
            self._editor.load_text(text)
            self._stack.set_visible_child_name("edit")
            self._editing = True
            self._stop_watching()
        else:
            # Exit edit mode — save and re-render
            text = self._editor.get_text()
            try:
                with open(self._current_file, "w", encoding="utf-8") as f:
                    f.write(text)
            except OSError:
                pass
            self._viewer.render_text(text, self._current_file)
            self._stack.set_visible_child_name("view")
            self._editing = False
            self._start_watching()

    def _on_folder_selected(self, _sidebar, folder_path):
        if self._editing:
            # Save first, then show documents
            text = self._editor.get_text()
            try:
                with open(self._current_file, "w", encoding="utf-8") as f:
                    f.write(text)
            except OSError:
                pass
            self._editing = False
            self._edit_btn.set_active(False)

        from marklite.sidebar import Sidebar
        if folder_path == Sidebar.ALL_DOCUMENTS:
            self._title_widget.set_subtitle("All Documents")
        else:
            self._title_widget.set_subtitle(os.path.basename(folder_path))

        self._edit_btn.set_sensitive(False)
        self._doc_panel.show_folder(folder_path)
        self._stack.set_visible_child_name("documents")

    def _on_file_selected(self, _panel, path):
        if self._editing:
            self._prompt_unsaved(path)
            return
        self._load_file(path)

    def _load_file(self, path):
        self._current_file = path
        self._edit_btn.set_sensitive(True)
        self._title_widget.set_subtitle(os.path.basename(path))
        self._viewer.load_file(path)
        self._stack.set_visible_child_name("view")
        self._start_watching()

    def _prompt_unsaved(self, next_path):
        dialog = Adw.AlertDialog(
            heading="Unsaved Changes",
            body="You have unsaved changes. What would you like to do?",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("discard", "Discard")
        dialog.add_response("save", "Save")
        dialog.set_response_appearance("discard", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")
        dialog.set_close_response("cancel")

        dialog.connect("response", self._on_unsaved_response, next_path)
        dialog.present(self)

    def _on_unsaved_response(self, _dialog, response, next_path):
        if response == "cancel":
            return
        if response == "save":
            text = self._editor.get_text()
            try:
                with open(self._current_file, "w", encoding="utf-8") as f:
                    f.write(text)
            except OSError:
                pass
        # For both "save" and "discard"
        self._editing = False
        self._edit_btn.set_active(False)
        self._stack.set_visible_child_name("view")
        self._load_file(next_path)

    def _start_watching(self):
        self._stop_watching()
        if not self._settings.file_watching or not self._current_file:
            return
        try:
            from marklite.file_watcher import FileWatcher
            self._watcher = FileWatcher(self._current_file, self._on_file_changed)
        except Exception:
            pass

    def _stop_watching(self):
        if self._watcher:
            self._watcher.stop()
            self._watcher = None

    def _on_file_changed(self):
        if not self._editing and self._current_file:
            self._viewer.load_file(self._current_file)

    def _on_file_trashed(self, _panel, path):
        if self._current_file == path:
            self._stop_watching()
            self._current_file = None
            self._editing = False
            self._edit_btn.set_active(False)
            self._edit_btn.set_sensitive(False)
            self._title_widget.set_subtitle("")
            self._stack.set_visible_child_name("documents")
        self._sidebar.refresh()

    def _on_file_renamed(self, _panel, old_path, new_path):
        if self._current_file == old_path:
            self._current_file = new_path
            self._title_widget.set_subtitle(os.path.basename(new_path))
            self._start_watching()
        self._sidebar.refresh()

    def _on_settings_changed(self, _mgr, key):
        if key == "root_directory":
            self._sidebar.refresh()
            self._doc_panel.refresh()
        elif key in ("font_family", "font_size"):
            self._viewer.update_style()
        elif key in ("editor_font_family", "editor_font_size"):
            self._editor.update_style()
        elif key == "file_watching":
            if self._settings.file_watching:
                self._start_watching()
            else:
                self._stop_watching()

    def _on_preferences(self, *_args):
        from marklite.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self._settings)
        dialog.present(self)

    def _on_about(self, *_args):
        about = Adw.AboutDialog(
            application_name=APP_NAME,
            application_icon="de.singular.marklite-symbolic",
            version=VERSION,
            developer_name="MarkLite",
            comments="A lightweight GTK4 Markdown reader and editor",
        )
        about.present(self)
