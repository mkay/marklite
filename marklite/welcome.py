from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from marklite import APP_NAME, VERSION

_RESOURCE_PATH = "/de/singular/marklite/icons/hicolor/scalable/apps/de.singular.marklite.svg"
_FILE_PATH = Path(__file__).parent / "data" / "icons" / "hicolor" / "scalable" / "apps" / "de.singular.marklite.svg"


class WelcomeView(Adw.Bin):
    """Empty state shown when no file is open."""

    def __init__(self):
        super().__init__()

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            valign=Gtk.Align.CENTER,
            halign=Gtk.Align.CENTER,
            vexpand=True,
            hexpand=True,
            margin_top=48,
            margin_bottom=48,
            margin_start=48,
            margin_end=48,
        )

        img = self._load_image()
        img.set_pixel_size(128)
        img.set_margin_bottom(12)
        box.append(img)

        title = Gtk.Label(label=f"Welcome to {APP_NAME}", css_classes=["title-1"])
        box.append(title)

        desc = Gtk.Label(
            label=f"Version {VERSION}\n\nSelect a Markdown file from the sidebar to start reading.",
            justify=Gtk.Justification.CENTER,
            wrap=True,
            css_classes=["dim-label"],
            margin_top=6,
        )
        box.append(desc)

        self.set_child(box)

    def _load_image(self):
        if _FILE_PATH.exists():
            return Gtk.Image.new_from_file(str(_FILE_PATH))
        return Gtk.Image.new_from_resource(_RESOURCE_PATH)
