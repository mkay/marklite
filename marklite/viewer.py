import os

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")
from gi.repository import Adw, Gdk, Gtk, WebKit

from marklite.markdown_renderer import MarkdownRenderer
from marklite.html_template import wrap_html


class MarkdownViewer(Gtk.Box):
    def __init__(self, settings):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._settings = settings
        self._renderer = MarkdownRenderer()
        self._current_path = None

        ucm = WebKit.UserContentManager()
        ucm.register_script_message_handler("copyCode")
        ucm.connect("script-message-received::copyCode", self._on_copy_code)

        self._webview = WebKit.WebView(user_content_manager=ucm)
        self._webview.set_vexpand(True)
        self._webview.set_hexpand(True)

        ws = self._webview.get_settings()
        ws.set_enable_developer_extras(False)

        self.append(self._webview)
        self._show_empty()

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
        )
        self._webview.load_html(html, "file:///")

    def load_file(self, path):
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
                         dark=self._is_dark())
        base_uri = "file://"
        if self._current_path:
            base_uri = "file://" + os.path.dirname(os.path.abspath(self._current_path)) + "/"
        self._webview.load_html(html, base_uri)

    def reload(self):
        if self._current_path:
            self.load_file(self._current_path)

    def update_style(self):
        if self._current_path:
            self.reload()
