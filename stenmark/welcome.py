import os

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from stenmark import APP_NAME, VERSION


class WelcomeView(Adw.Bin):
    """Empty state shown when no file is open."""

    def __init__(self, settings=None, on_set_root=None, on_new_file=None):
        super().__init__()
        self._settings = settings
        self._on_set_root = on_set_root
        self._on_new_file = on_new_file

        self._status = Adw.StatusPage(
            icon_name="de.singular.stenmark-symbolic",
            title=f"Welcome to {APP_NAME}",
            vexpand=True,
            hexpand=True,
        )

        child_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            halign=Gtk.Align.CENTER,
        )

        self._set_root_btn = Gtk.Button(
            label="Set a Root Directory for Stenmark",
            halign=Gtk.Align.CENTER,
            css_classes=["pill", "suggested-action"],
        )
        self._set_root_btn.connect("clicked", self._on_root_btn_clicked)
        child_box.append(self._set_root_btn)

        self._create_label = Gtk.Label(
            use_markup=True,
            halign=Gtk.Align.CENTER,
        )
        self._create_label.set_markup(
            'Select a Markdown file from the sidebar or <a href="create">click here to create one</a>.'
        )
        self._create_label.connect("activate-link", self._on_link_activated)
        child_box.append(self._create_label)

        self._status.set_child(child_box)

        self._update_state()
        self.set_child(self._status)

    def _root_is_missing(self):
        if self._settings is None:
            return False
        root = self._settings.root_directory
        return not root or not os.path.isdir(root)

    def _update_state(self):
        missing = self._root_is_missing()
        if missing:
            self._status.set_description(
                f"Your Markdown Librarian\nVersion {VERSION}\n\n"
                "No root directory is set, or the configured directory is missing.\n"
                "Choose a folder to get started."
            )  # nosec B608
            self._set_root_btn.set_visible(True)
            self._create_label.set_visible(False)
        else:
            self._status.set_description(
                f"Your Markdown Librarian\nVersion {VERSION}\n\n"
                "Stenmark is alpha software\n"
                "Features may appear, disappear, or spontaneously improve."
            )  # nosec B608
            self._set_root_btn.set_visible(False)
            self._create_label.set_visible(True)

    def refresh(self):
        """Re-evaluate root directory state and update the view."""
        self._update_state()

    def _on_root_btn_clicked(self, _btn):
        if self._on_set_root:
            self._on_set_root()

    def _on_link_activated(self, _label, uri):
        if uri == "create" and self._on_new_file:
            self._on_new_file()
            return True
        return False
