import os
import re

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk, Gio

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
        self._preview_timeout_id = None
        self._toc_headings = []

        self.set_default_size(settings.window_width, settings.window_height)
        self.set_title(APP_NAME)

        self._build_ui()
        self._connect_signals()
        self._setup_actions()

    def _build_ui(self):
        # === Sidebar ToolbarView ===
        sidebar_header = Adw.HeaderBar(show_end_title_buttons=False)

        self._root_popover = Gtk.Popover(position=Gtk.PositionType.BOTTOM)
        self._root_popover.set_has_arrow(True)

        self._root_label = Gtk.Label(
            label=os.path.basename(self._settings.root_directory),
            ellipsize=3,  # Pango.EllipsizeMode.END
            css_classes=["heading"],
        )
        self._root_btn = Gtk.MenuButton(
            css_classes=["flat"],
            popover=self._root_popover,
            child=self._root_label,
            direction=Gtk.ArrowType.NONE,
        )
        self._root_btn.connect("notify::active", self._on_root_btn_toggled)
        sidebar_header.set_title_widget(self._root_btn)

        # The "ceiling" is the configured root from settings (ignoring session overrides)
        self._root_ceiling = self._settings._data.get("root_directory", self._settings.get("root_directory"))

        self._sidebar = Sidebar(self._settings)

        sidebar_toolbar = Adw.ToolbarView()
        sidebar_toolbar.add_css_class("app-sidebar")
        sidebar_toolbar.add_top_bar(sidebar_header)
        sidebar_toolbar.set_content(self._sidebar)

        # === Content ToolbarView ===
        self._content_header = Adw.HeaderBar(show_start_title_buttons=False)

        # Back button (start, leftmost)
        self._back_btn = Gtk.Button(
            icon_name="marklite-go-previous-symbolic",
            tooltip_text="Back",
            visible=False,
        )
        self._back_btn.connect("clicked", self._on_back_clicked)
        self._content_header.pack_start(self._back_btn)

        # Edit toggle (start)
        self._edit_btn = Gtk.ToggleButton(
            icon_name="marklite-edit-symbolic",
            tooltip_text="Toggle edit mode",
            sensitive=False,
        )
        self._edit_btn.set_focus_on_click(False)
        self._content_header.pack_start(self._edit_btn)

        # Preview toggle (only visible while editing)
        self._preview_btn = Gtk.ToggleButton(
            icon_name="marklite-preview-symbolic",
            tooltip_text="Toggle live preview",
            active=True,
            visible=False,
        )
        self._preview_btn.set_focus_on_click(False)
        self._content_header.pack_start(self._preview_btn)

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

        # Sidebar toggle (left of menu button)
        self._sidebar_btn = Gtk.Button(
            icon_name="marklite-sidebar-hide-symbolic",
            tooltip_text="Toggle sidebar",
        )
        self._sidebar_btn.set_focus_on_click(False)
        self._content_header.pack_end(self._sidebar_btn)

        # Export to PDF (visible when a file is open)
        self._export_pdf_btn = Gtk.Button(
            icon_name="marklite-export-pdf-symbolic",
            tooltip_text="Export to PDF",
            visible=False,
        )
        self._export_pdf_btn.set_focus_on_click(False)
        self._content_header.pack_end(self._export_pdf_btn)

        # Copy as rich text (visible when a file is open)
        self._copy_rich_btn = Gtk.Button(
            icon_name="marklite-copy-rich-text-symbolic",
            tooltip_text="Copy as rich text",
            visible=False,
        )
        self._copy_rich_btn.set_focus_on_click(False)
        self._content_header.pack_end(self._copy_rich_btn)

        # Table of contents popover (visible when a file is open)
        self._toc_btn = Gtk.MenuButton(
            icon_name="marklite-list-bullet-symbolic",
            tooltip_text="Table of contents",
            visible=False,
        )
        self._toc_btn.set_focus_on_click(False)
        self._toc_popover = Gtk.Popover()
        self._toc_popover.set_size_request(280, -1)
        self._toc_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self._toc_list.add_css_class("navigation-sidebar")
        self._toc_list.connect("row-activated", self._on_toc_row_activated)
        scroll = Gtk.ScrolledWindow(
            max_content_height=400,
            propagate_natural_height=True,
        )
        scroll.set_child(self._toc_list)
        self._toc_popover.set_child(scroll)
        self._toc_btn.set_popover(self._toc_popover)
        self._content_header.pack_end(self._toc_btn)

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
        self._preview_viewer = MarkdownViewer(self._settings)

        self._edit_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self._edit_paned.set_start_child(self._editor)
        self._edit_paned.set_end_child(self._preview_viewer)
        self._edit_paned.set_resize_start_child(True)
        self._edit_paned.set_resize_end_child(True)
        self._edit_paned.set_shrink_start_child(False)
        self._edit_paned.set_shrink_end_child(False)
        self._edit_paned.set_position(self._settings.window_width // 2)
        self._stack.add_named(self._edit_paned, "edit")

        self._stack.set_visible_child_name("welcome")

        # === Status bar ===
        self._status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self._status_bar.add_css_class("toolbar")
        self._status_bar.set_margin_start(12)
        self._status_bar.set_margin_end(12)
        self._status_bar.set_visible(False)

        spacer = Gtk.Box(hexpand=True)
        self._status_bar.append(spacer)
        self._word_count_label = Gtk.Label(css_classes=["caption", "dim-label"])
        self._reading_time_label = Gtk.Label(css_classes=["caption", "dim-label"])
        self._status_bar.append(self._word_count_label)
        self._status_bar.append(self._reading_time_label)

        content_toolbar = Adw.ToolbarView()
        content_toolbar.add_top_bar(self._content_header)
        content_toolbar.add_bottom_bar(self._status_bar)
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
        self._sidebar.connect("changed", lambda _s: self._doc_panel.refresh())
        self._doc_panel.connect("file-selected", self._on_file_selected)
        self._doc_panel.connect("file-trashed", self._on_file_trashed)
        self._doc_panel.connect("file-renamed", self._on_file_renamed)
        self._doc_panel.connect("folder-navigated", self._on_folder_navigated)
        self._settings.connect("changed", self._on_settings_changed)
        self._editor.set_save_callback(self._on_editor_save)
        self._editor.set_preview_callback(self._on_preview_text_changed)
        self._editor.set_scroll_callback(self._on_editor_scroll)
        self._preview_btn.connect("toggled", self._on_preview_toggled)
        self._copy_rich_btn.connect("clicked", self._on_copy_rich_text)
        self._export_pdf_btn.connect("clicked", self._on_export_pdf)

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

        edit_toggle = Gio.SimpleAction.new("edit-toggle", None)
        edit_toggle.connect("activate", self._on_edit_shortcut)
        self.add_action(edit_toggle)
        self._apply_edit_shortcut()

    def _on_editor_save(self):
        if not self._current_file or not self._editing:
            return
        text = self._editor.get_text()
        try:
            with open(self._current_file, "w", encoding="utf-8") as f:
                f.write(text)
        except OSError:
            pass

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
            if self._preview_btn.get_active():
                self._preview_viewer.render_text(text, self._current_file)
            self._stack.set_visible_child_name("edit")
            self._editing = True
            self._preview_btn.set_visible(True)
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
            self._preview_btn.set_visible(False)
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
            self._preview_btn.set_visible(False)

        from marklite.sidebar import Sidebar
        if folder_path == Sidebar.ALL_DOCUMENTS:
            self._title_widget.set_subtitle("All Documents")
        elif folder_path == Sidebar.NO_FOLDER:
            self._title_widget.set_subtitle("No Folder")
        else:
            self._title_widget.set_subtitle(os.path.basename(folder_path))

        self._edit_btn.set_sensitive(False)
        self._copy_rich_btn.set_visible(False)
        self._export_pdf_btn.set_visible(False)
        self._toc_btn.set_visible(False)
        self._status_bar.set_visible(False)
        self._doc_panel.show_folder(folder_path)
        self._stack.set_visible_child_name("documents")
        self._update_back_btn()

    def _on_folder_navigated(self, _panel, folder_path):
        self._title_widget.set_subtitle(os.path.basename(folder_path))
        self._update_back_btn()

    def _update_back_btn(self):
        page = self._stack.get_visible_child_name()
        if page in ("view", "edit"):
            self._back_btn.set_visible(True)
        elif page == "documents" and self._doc_panel.is_drilled_in:
            self._back_btn.set_visible(True)
        else:
            self._back_btn.set_visible(False)

    def _on_back_clicked(self, _btn):
        page = self._stack.get_visible_child_name()
        if page in ("view", "edit"):
            # Exit document view — save if editing
            if self._editing:
                text = self._editor.get_text()
                try:
                    with open(self._current_file, "w", encoding="utf-8") as f:
                        f.write(text)
                except OSError:
                    pass
                self._editing = False
                self._edit_btn.set_active(False)
                self._preview_btn.set_visible(False)
            self._stop_watching()
            self._current_file = None
            self._edit_btn.set_sensitive(False)
            self._copy_rich_btn.set_visible(False)
            self._export_pdf_btn.set_visible(False)
            self._toc_btn.set_visible(False)
            self._status_bar.set_visible(False)
            self._doc_panel.refresh()
            self._stack.set_visible_child_name("documents")
            # Restore subtitle to folder name
            from marklite.sidebar import Sidebar
            folder = self._doc_panel._current_folder
            if folder == Sidebar.ALL_DOCUMENTS:
                self._title_widget.set_subtitle("All Documents")
            elif folder == Sidebar.NO_FOLDER:
                self._title_widget.set_subtitle("No Folder")
            elif self._doc_panel.is_drilled_in:
                self._title_widget.set_subtitle(os.path.basename(self._doc_panel._browsing_folder))
            else:
                self._title_widget.set_subtitle(os.path.basename(folder))
        elif page == "documents" and self._doc_panel.is_drilled_in:
            self._doc_panel.navigate_back()
        self._update_back_btn()

    def _on_file_selected(self, _panel, path):
        if self._editing:
            self._prompt_unsaved(path)
            return
        self._load_file(path)

    def _load_file(self, path):
        self._current_file = path
        self._back_btn.set_visible(True)
        self._edit_btn.set_sensitive(True)
        self._copy_rich_btn.set_visible(True)
        self._export_pdf_btn.set_visible(True)
        self._toc_btn.set_visible(True)
        self._title_widget.set_subtitle(os.path.basename(path))
        self._viewer.load_file(path)
        self._stack.set_visible_child_name("view")
        self._start_watching()
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            self._update_stats(text)
            self._update_toc(text)
        except OSError:
            pass

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
            self._copy_rich_btn.set_visible(False)
            self._export_pdf_btn.set_visible(False)
            self._toc_btn.set_visible(False)
            self._title_widget.set_subtitle("")
            self._status_bar.set_visible(False)
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
            # Update ceiling if this was a persistent change (not an override)
            persisted = self._settings._data.get("root_directory")
            if persisted and "root_directory" not in self._settings._overrides:
                self._root_ceiling = persisted
            self._update_root_label()
            self._sidebar.refresh()
            self._doc_panel.refresh()
        elif key in ("font_family", "font_size", "viewer_theme"):
            self._viewer.update_style()
            self._preview_viewer.update_style()
        elif key in ("editor_font_family", "editor_font_size",
                     "editor_theme", "editor_line_numbers", "editor_line_wrap"):
            self._editor.update_style()
        elif key == "edit_shortcut":
            self._apply_edit_shortcut()
        elif key == "file_watching":
            if self._settings.file_watching:
                self._start_watching()
            else:
                self._stop_watching()

    def _on_preview_toggled(self, btn):
        active = btn.get_active()
        self._preview_viewer.set_visible(active)
        btn.set_icon_name(
            "marklite-preview-symbolic" if active else "marklite-preview-off-symbolic"
        )
        if active:
            text = self._editor.get_text()
            self._preview_viewer.render_text(text, self._current_file)

    def _on_preview_text_changed(self, text):
        self._update_stats(text)
        self._update_toc(text)
        if not self._preview_btn.get_active():
            return
        if self._preview_timeout_id:
            GLib.source_remove(self._preview_timeout_id)
        self._preview_timeout_id = GLib.timeout_add(
            150, self._do_preview_update, text
        )

    def _do_preview_update(self, text):
        self._preview_timeout_id = None
        self._preview_viewer.render_text(text, self._current_file)
        return GLib.SOURCE_REMOVE

    def _on_editor_scroll(self, line):
        if self._stack.get_visible_child_name() == "edit" and self._preview_btn.get_active():
            self._preview_viewer.scroll_to_line(line)

    def _on_export_pdf(self, _btn):
        if self._editing:
            self._preview_viewer.print_pdf(self)
        else:
            self._viewer.print_pdf(self)

    def _on_copy_rich_text(self, _btn):
        if self._editing:
            text = self._editor.get_text()
        elif self._current_file:
            try:
                with open(self._current_file, encoding="utf-8") as f:
                    text = f.read()
            except OSError:
                return
        else:
            return

        from marklite.markdown_renderer import MarkdownRenderer
        body = MarkdownRenderer().render(text)
        html = f"<html><body>{body}</body></html>"

        providers = [
            Gdk.ContentProvider.new_for_bytes(
                "text/html", GLib.Bytes.new(html.encode("utf-8"))
            ),
            Gdk.ContentProvider.new_for_value(text),
        ]
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set_content(Gdk.ContentProvider.new_union(providers))

    def _update_stats(self, text):
        words = len(text.split())
        minutes = max(1, round(words / 200))
        self._word_count_label.set_label(f"{words} words")
        self._reading_time_label.set_label(f"{minutes} min read")
        self._status_bar.set_visible(True)

    def _apply_edit_shortcut(self):
        shortcut = self._settings.edit_shortcut
        if shortcut:
            self.get_application().set_accels_for_action(
                "win.edit-toggle", [shortcut]
            )
        else:
            self.get_application().set_accels_for_action("win.edit-toggle", [])

    def _on_edit_shortcut(self, *_args):
        if self._current_file:
            self._edit_btn.set_active(not self._edit_btn.get_active())

    def _parse_headings(self, text):
        headings = []
        in_fence = False
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            m = re.match(r'^(#{1,6})\s+(.+)', line)
            if m:
                level = len(m.group(1))
                title = m.group(2).strip()
                headings.append((level, title, i))
        return headings

    def _update_toc(self, text):
        self._toc_headings = self._parse_headings(text)
        while True:
            row = self._toc_list.get_row_at_index(0)
            if row is None:
                break
            self._toc_list.remove(row)
        for level, title, _line in self._toc_headings:
            label = Gtk.Label(
                label=title,
                xalign=0,
                ellipsize=3,  # Pango.EllipsizeMode.END
            )
            label.set_margin_start((level - 1) * 16)
            if level == 1:
                label.add_css_class("heading")
            elif level >= 3:
                label.add_css_class("dim-label")
            self._toc_list.append(label)

    def _on_toc_row_activated(self, _listbox, row):
        self._toc_popover.popdown()
        idx = row.get_index()
        if idx >= len(self._toc_headings):
            return
        level, title, line_num = self._toc_headings[idx]
        if self._editing:
            self._editor._js(f"scrollToLine({line_num})")
        else:
            self._viewer._webview.evaluate_javascript(
                f"document.querySelectorAll('h1,h2,h3,h4,h5,h6')[{idx}]?.scrollIntoView({{behavior:'smooth'}});",
                -1, None, None, None, None,
            )

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
            license_type=Gtk.License.MIT_X11,
        )
        about.present(self)

    # ---- Root folder navigation (sidebar header) -------------------------

    def _update_root_label(self):
        self._root_label.set_label(
            os.path.basename(self._settings.root_directory)
        )

    def _on_root_btn_toggled(self, btn, _pspec):
        if not btn.get_active():
            return

        from marklite.sidebar import _collect_subdirs

        current_root = self._settings.root_directory
        ceiling = os.path.expanduser(self._root_ceiling)

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
            margin_start=4,
            margin_end=4,
            margin_top=4,
            margin_bottom=4,
        )

        # "Back" row if drilled deeper than ceiling
        if os.path.normpath(current_root) != os.path.normpath(ceiling):
            parent = os.path.dirname(current_root)
            back_btn = Gtk.Button(css_classes=["flat"])
            back_box = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL,
                spacing=8,
                margin_start=6,
                margin_end=6,
                margin_top=4,
                margin_bottom=4,
            )
            back_box.append(Gtk.Image(icon_name="marklite-go-previous-symbolic"))
            back_box.append(Gtk.Label(
                label=os.path.basename(parent) if parent != current_root else "Back",
                xalign=0,
                hexpand=True,
            ))
            back_btn.set_child(back_box)
            back_btn.connect("clicked", self._on_root_nav, parent)
            box.append(back_btn)
            box.append(Gtk.Separator())

        # Child folder rows
        subdirs = _collect_subdirs(current_root)
        if subdirs:
            for dir_path, dir_name in subdirs:
                btn = Gtk.Button(css_classes=["flat"])
                row_box = Gtk.Box(
                    orientation=Gtk.Orientation.HORIZONTAL,
                    spacing=8,
                    margin_start=6,
                    margin_end=6,
                    margin_top=4,
                    margin_bottom=4,
                )
                row_box.append(Gtk.Image(icon_name="marklite-folder-symbolic"))
                row_box.append(Gtk.Label(label=dir_name, xalign=0, hexpand=True))
                btn.set_child(row_box)
                btn.connect("clicked", self._on_root_nav, dir_path)
                box.append(btn)
        else:
            box.append(Gtk.Label(
                label="No subfolders",
                css_classes=["dim-label"],
                margin_start=6,
                margin_end=6,
                margin_top=8,
                margin_bottom=8,
            ))

        self._root_popover.set_child(box)

    def _on_root_nav(self, _btn, dir_path):
        self._root_popover.popdown()
        self._settings.set_override("root_directory", dir_path)
