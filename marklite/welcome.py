import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw

from marklite import APP_NAME, VERSION


class WelcomeView(Adw.Bin):
    """Empty state shown when no file is open."""

    def __init__(self):
        super().__init__()

        status = Adw.StatusPage(
            icon_name="de.singular.marklite-symbolic",
            title=f"Welcome to {APP_NAME}",
            description=f"Your Markdown Librarian\nVersion {VERSION}\n\nMarklite is alpha software\nFeatures may appear, disappear, or spontaneously improve.\n\nSelect a Markdown file from the sidebar.",
            vexpand=True,
            hexpand=True,
        )

        self.set_child(status)
