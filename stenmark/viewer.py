import json
import os
import re

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")
from gi.repository import Adw, Gdk, Gtk, WebKit

from stenmark.markdown_renderer import MarkdownRenderer
from stenmark.html_template import wrap_html


class MarkdownViewer(Gtk.Box):
    def __init__(self, settings):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._settings = settings
        self._renderer = MarkdownRenderer()
        self._current_path = None

        self._skip_next_load = False

        ucm = WebKit.UserContentManager()
        ucm.register_script_message_handler("copyCode")
        ucm.connect("script-message-received::copyCode", self._on_copy_code)
        ucm.register_script_message_handler("checkboxToggled")
        ucm.connect("script-message-received::checkboxToggled", self._on_checkbox_toggled)

        self._webview = WebKit.WebView(user_content_manager=ucm)
        self._webview.set_vexpand(True)
        self._webview.set_hexpand(True)

        ws = self._webview.get_settings()
        ws.set_enable_developer_extras(False)

        self.append(self._webview)
        self._build_search_bar()
        self._show_empty()

    def _build_search_bar(self):
        self._find_controller = self._webview.get_find_controller()

        box = Gtk.Box(spacing=4)
        box.add_css_class("toolbar")
        box.set_margin_start(6)
        box.set_margin_end(6)
        box.set_margin_top(4)
        box.set_margin_bottom(4)

        self._search_entry = Gtk.SearchEntry(hexpand=True, placeholder_text="Find in document")
        self._search_entry.connect("search-changed", self._on_search_changed)
        self._search_entry.connect("activate", lambda *_: self._find_controller.search_next())
        box.append(self._search_entry)

        prev_btn = Gtk.Button(icon_name="stenmark-go-up-symbolic", tooltip_text="Previous match")
        prev_btn.connect("clicked", lambda *_: self._find_controller.search_previous())
        box.append(prev_btn)

        next_btn = Gtk.Button(icon_name="stenmark-go-down-symbolic", tooltip_text="Next match")
        next_btn.connect("clicked", lambda *_: self._find_controller.search_next())
        box.append(next_btn)

        close_btn = Gtk.Button(icon_name="stenmark-close-symbolic", tooltip_text="Close")
        close_btn.connect("clicked", lambda *_: self.hide_search())
        box.append(close_btn)

        self._search_bar = box
        self._search_bar.set_visible(False)
        self.prepend(self._search_bar)

        key_ctl = Gtk.EventControllerKey()
        key_ctl.connect("key-pressed", self._on_search_key)
        self._search_entry.add_controller(key_ctl)

    def _on_search_changed(self, entry):
        text = entry.get_text()
        if text:
            self._find_controller.search(
                text,
                WebKit.FindOptions.CASE_INSENSITIVE | WebKit.FindOptions.WRAP_AROUND,
                0,
            )
        else:
            self._find_controller.search_finish()

    def _inject_find_css(self):
        css = (
            "::highlight(search) { background: #ffdd00 !important; color: #000 !important; }"
            "::highlight(current) { background: #ff6a00 !important; color: #000 !important; }"
        )
        script = (
            f"(function(){{ var s = document.createElement('style');"
            f"s.textContent = '{css}'; document.head.appendChild(s); }})()"
        )
        self._webview.evaluate_javascript(script, -1, None, None, None, None)

    def _on_search_key(self, _ctl, keyval, _keycode, _state):
        if keyval == Gdk.KEY_Escape:
            self.hide_search()
            return True
        return False

    def toggle_search(self):
        if self._search_bar.get_visible():
            self.hide_search()
        else:
            self._search_bar.set_visible(True)
            self._search_entry.grab_focus()

    def hide_search(self):
        self._search_bar.set_visible(False)
        self._find_controller.search_finish()
        self._search_entry.set_text("")

    def _on_checkbox_toggled(self, _ucm, result):
        try:
            data = json.loads(result.to_string())
            index = data["index"]
            checked = data["checked"]
        except Exception:
            return
        if not self._current_path:
            return
        try:
            with open(self._current_path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            return
        pattern = re.compile(r'^(\s*[-*+]\s+)\[[ xX]\]', re.MULTILINE)
        matches = list(pattern.finditer(text))
        if index >= len(matches):
            return
        m = matches[index]
        mark = "x" if checked else " "
        bracket_pos = m.end(1) + 1  # position of the space or 'x' inside [...]
        new_text = text[:bracket_pos] + mark + text[bracket_pos + 1:]
        try:
            with open(self._current_path, "w", encoding="utf-8") as f:
                f.write(new_text)
        except OSError:
            return
        self._skip_next_load = True

    def _on_copy_code(self, _ucm, result):
        text = result.to_string()
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)

    def _is_dark(self):
        style = Adw.StyleManager.get_default()
        return style.get_dark()

    def _show_empty(self):
        html = wrap_html(
            "<p style='color:#888; text-align:center; margin-top:40vh;'>"
            "Select a markdown file to view</p>",
            self._settings.font_family,
            self._settings.font_size,
            dark=self._is_dark(),
            viewer_theme=self._settings.viewer_theme,
        )
        self._webview.load_html(html, "file:///")

    def load_file(self, path):
        if self._skip_next_load and path == self._current_path:
            self._skip_next_load = False
            return
        self._skip_next_load = False
        self._current_path = path
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            self._show_empty()
            return
        self.render_text(text, path)

    def render_text(self, text, path=None):
        if path:
            self._current_path = path
        body = self._renderer.render(text)
        html = wrap_html(body, self._settings.font_family, self._settings.font_size,
                         dark=self._is_dark(), viewer_theme=self._settings.viewer_theme)
        base_uri = "file://"
        if self._current_path:
            base_uri = "file://" + os.path.dirname(os.path.abspath(self._current_path)) + "/"
        self._webview.load_html(html, base_uri)

    def reload(self):
        if self._current_path:
            self.load_file(self._current_path)

    def print_pdf(self, parent):
        op = WebKit.PrintOperation.new(self._webview)
        op.run_dialog(parent)

    def scroll_to_line(self, line):
        self._webview.evaluate_javascript(
            f"window.scrollToSourceLine && window.scrollToSourceLine({line})",
            -1, None, None, None, None,
        )

    def update_style(self):
        if self._current_path:
            self.reload()
