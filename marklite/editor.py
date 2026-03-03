import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
gi.require_version("GtkSource", "5")
from gi.repository import Adw, Gdk, Gtk, GtkSource


class MarkdownEditor(Gtk.Box):
    def __init__(self, settings):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._settings = settings

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        self._buffer = GtkSource.Buffer()
        lang_manager = GtkSource.LanguageManager.get_default()
        lang = lang_manager.get_language("markdown")
        if lang:
            self._buffer.set_language(lang)
        self._buffer.set_highlight_syntax(True)

        self._view = GtkSource.View(buffer=self._buffer)
        self._view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._view.set_show_line_numbers(True)
        self._view.set_tab_width(4)
        self._view.set_insert_spaces_instead_of_tabs(True)
        self._view.set_auto_indent(True)
        self._view.set_monospace(True)
        self._view.set_top_margin(8)
        self._view.set_bottom_margin(8)
        self._view.set_left_margin(8)
        self._view.set_right_margin(8)

        self._apply_style()
        self._apply_scheme()
        self._setup_shortcuts()

        scrolled.set_child(self._view)
        self.append(scrolled)
        self._build_search_bar()

    def _setup_shortcuts(self):
        ctrl = Gtk.EventControllerKey()
        ctrl.connect("key-pressed", self._on_key_pressed)
        self._view.add_controller(ctrl)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        mod = state & Gtk.accelerator_get_default_mod_mask()
        ctrl = Gdk.ModifierType.CONTROL_MASK
        ctrl_shift = ctrl | Gdk.ModifierType.SHIFT_MASK

        if mod == ctrl:
            if keyval == Gdk.KEY_b:
                self._wrap_selection("**", "**")
                return True
            if keyval == Gdk.KEY_i:
                self._wrap_selection("*", "*")
                return True
            if keyval == Gdk.KEY_k:
                self._insert_link()
                return True
            if keyval == Gdk.KEY_grave:
                self._wrap_selection("`", "`")
                return True
        elif mod == ctrl_shift:
            if keyval in (Gdk.KEY_x, Gdk.KEY_X):
                self._wrap_selection("~~", "~~")
                return True
            if keyval in (Gdk.KEY_k, Gdk.KEY_K):
                self._insert_code_block()
                return True

        return False

    def _wrap_selection(self, prefix, suffix):
        buf = self._buffer
        has_sel = buf.get_has_selection()
        buf.begin_user_action()
        if has_sel:
            start, end = buf.get_selection_bounds()
            text = buf.get_text(start, end, True)
            buf.delete(start, end)
            buf.insert(start, prefix + text + suffix)
            # Reselect the inner text
            cursor = buf.get_iter_at_mark(buf.get_insert())
            end_sel = cursor.copy()
            start_sel = cursor.copy()
            start_sel.backward_chars(len(suffix) + len(text))
            end_sel.backward_chars(len(suffix))
            buf.select_range(start_sel, end_sel)
        else:
            buf.insert_at_cursor(prefix + suffix)
            cursor = buf.get_iter_at_mark(buf.get_insert())
            cursor.backward_chars(len(suffix))
            buf.place_cursor(cursor)
        buf.end_user_action()

    def _insert_link(self):
        buf = self._buffer
        has_sel = buf.get_has_selection()
        buf.begin_user_action()
        if has_sel:
            start, end = buf.get_selection_bounds()
            text = buf.get_text(start, end, True)
            buf.delete(start, end)
            buf.insert(start, "[" + text + "](url)")
            # Select "url" so user can type the URL
            cursor = buf.get_iter_at_mark(buf.get_insert())
            end_sel = cursor.copy()
            end_sel.backward_chars(1)  # before )
            start_sel = end_sel.copy()
            start_sel.backward_chars(3)  # before url
            buf.select_range(start_sel, end_sel)
        else:
            buf.insert_at_cursor("[](url)")
            cursor = buf.get_iter_at_mark(buf.get_insert())
            cursor.backward_chars(6)  # inside []
            buf.place_cursor(cursor)
        buf.end_user_action()

    def _insert_code_block(self):
        buf = self._buffer
        has_sel = buf.get_has_selection()
        buf.begin_user_action()
        if has_sel:
            start, end = buf.get_selection_bounds()
            text = buf.get_text(start, end, True)
            buf.delete(start, end)
            buf.insert(start, "```\n" + text + "\n```")
        else:
            buf.insert_at_cursor("```\n\n```")
            cursor = buf.get_iter_at_mark(buf.get_insert())
            cursor.backward_chars(4)  # between the newlines
            buf.place_cursor(cursor)
        buf.end_user_action()

    def _apply_scheme(self):
        sm = GtkSource.StyleSchemeManager.get_default()
        dark = Adw.StyleManager.get_default().get_dark()
        scheme_id = "marklite-dark" if dark else "marklite-light"
        scheme = sm.get_scheme(scheme_id)
        if not scheme:
            scheme_id = "Adwaita-dark" if dark else "Adwaita"
            scheme = sm.get_scheme(scheme_id)
        if scheme:
            self._buffer.set_style_scheme(scheme)

    def _apply_style(self):
        css = (
            f"textview {{ font-family: {self._settings.editor_font_family}; "
            f"font-size: {self._settings.editor_font_size}pt; }}"
        )
        provider = Gtk.CssProvider()
        provider.load_from_string(css)
        self._view.get_style_context().add_provider(
            provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self._css_provider = provider

    def _build_search_bar(self):
        self._search_settings = GtkSource.SearchSettings()
        self._search_settings.set_case_sensitive(False)
        self._search_settings.set_wrap_around(True)
        self._search_context = GtkSource.SearchContext(
            buffer=self._buffer, settings=self._search_settings,
        )
        self._search_context.set_highlight(True)

        box = Gtk.Box(spacing=4)
        box.add_css_class("toolbar")
        box.set_margin_start(6)
        box.set_margin_end(6)
        box.set_margin_top(4)
        box.set_margin_bottom(4)

        self._search_entry = Gtk.SearchEntry(hexpand=True, placeholder_text="Find in editor")
        self._search_entry.connect("search-changed", self._on_search_changed)
        self._search_entry.connect("activate", lambda *_: self._search_next())
        box.append(self._search_entry)

        prev_btn = Gtk.Button(icon_name="go-up-symbolic", tooltip_text="Previous match")
        prev_btn.connect("clicked", lambda *_: self._search_prev())
        box.append(prev_btn)

        next_btn = Gtk.Button(icon_name="go-down-symbolic", tooltip_text="Next match")
        next_btn.connect("clicked", lambda *_: self._search_next())
        box.append(next_btn)

        close_btn = Gtk.Button(icon_name="window-close-symbolic", tooltip_text="Close")
        close_btn.connect("clicked", lambda *_: self.hide_search())
        box.append(close_btn)

        self._search_box = box
        self._search_box.set_visible(False)
        self.prepend(self._search_box)

        key_ctl = Gtk.EventControllerKey()
        key_ctl.connect("key-pressed", self._on_search_key)
        self._search_entry.add_controller(key_ctl)

    def _on_search_changed(self, entry):
        self._search_settings.set_search_text(entry.get_text() or None)

    def _on_search_key(self, _ctl, keyval, _keycode, _state):
        if keyval == Gdk.KEY_Escape:
            self.hide_search()
            return True
        return False

    def _search_next(self):
        cursor = self._buffer.get_iter_at_mark(self._buffer.get_insert())
        found, start, end, _ = self._search_context.forward(cursor)
        if found:
            # Avoid getting stuck on current match
            if start.equal(self._buffer.get_iter_at_mark(self._buffer.get_insert())):
                cursor.forward_char()
                found, start, end, _ = self._search_context.forward(cursor)
            if found:
                self._buffer.select_range(start, end)
                self._view.scroll_to_iter(start, 0.2, False, 0, 0)

    def _search_prev(self):
        cursor = self._buffer.get_iter_at_mark(self._buffer.get_insert())
        found, start, end, _ = self._search_context.backward(cursor)
        if found:
            self._buffer.select_range(start, end)
            self._view.scroll_to_iter(start, 0.2, False, 0, 0)

    def toggle_search(self):
        if self._search_box.get_visible():
            self.hide_search()
        else:
            self._search_box.set_visible(True)
            self._search_entry.grab_focus()

    def hide_search(self):
        self._search_box.set_visible(False)
        self._search_settings.set_search_text(None)
        self._search_entry.set_text("")
        self._view.grab_focus()

    def load_text(self, text):
        self._buffer.set_text(text)
        self._buffer.place_cursor(self._buffer.get_start_iter())

    def get_text(self):
        start = self._buffer.get_start_iter()
        end = self._buffer.get_end_iter()
        return self._buffer.get_text(start, end, True)

    def update_style(self):
        self._view.get_style_context().remove_provider(self._css_provider)
        self._apply_style()
        self._apply_scheme()
