import os
import time

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Gio, GObject, Gdk, Graphene

from marklite.sidebar import Sidebar


def _collect_md_files(dir_path):
    """Return sorted list of .md file paths in a directory (non-recursive)."""
    files = []
    try:
        for entry in sorted(os.scandir(dir_path), key=lambda e: e.name.lower()):
            if entry.name.startswith("."):
                continue
            if entry.is_file() and entry.name.lower().endswith(".md"):
                files.append(entry.path)
    except OSError:
        pass
    return files


def _collect_md_files_recursive(root):
    """Return dict of {dir_path: [file_paths]} for all subdirs with .md files."""
    groups = {}
    # Root-level files
    root_files = _collect_md_files(root)
    if root_files:
        groups[root] = root_files
    try:
        for entry in sorted(os.scandir(root), key=lambda e: e.name.lower()):
            if entry.name.startswith("."):
                continue
            if entry.is_dir(follow_symlinks=False):
                _collect_subdir_files(entry.path, groups)
    except OSError:
        pass
    return groups


def _collect_subdir_files(dir_path, groups):
    """Recursively collect .md files into groups dict."""
    files = _collect_md_files(dir_path)
    if files:
        groups[dir_path] = files
    try:
        for entry in sorted(os.scandir(dir_path), key=lambda e: e.name.lower()):
            if entry.name.startswith("."):
                continue
            if entry.is_dir(follow_symlinks=False):
                _collect_subdir_files(entry.path, groups)
    except OSError:
        pass


def _read_title(path):
    """Return the first # heading from a markdown file, or None."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line.startswith("# "):
                    return line[2:].strip() or None
                if line:  # stop at first non-empty non-heading line
                    return None
    except OSError:
        pass
    return None


def _format_size(size):
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


def _format_date(mtime):
    now = time.time()
    delta = now - mtime
    if delta < 60:
        return "just now"
    elif delta < 3600:
        m = int(delta / 60)
        return f"{m} min ago"
    elif delta < 86400:
        h = int(delta / 3600)
        return f"{h}h ago"
    else:
        return time.strftime("%b %d, %Y", time.localtime(mtime))


class DocumentPanel(Gtk.Box):
    __gsignals__ = {
        "file-selected": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "file-trashed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "file-renamed": (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
    }

    def __init__(self, settings):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._settings = settings
        self._current_folder = None
        self._context_path = None

        # Main scrolled area
        scrolled = Gtk.ScrolledWindow(vexpand=True)

        self._clamp = Adw.Clamp(
            maximum_size=640,
            tightening_threshold=400,
        )

        self._content_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            margin_start=12,
            margin_end=12,
            margin_top=12,
            margin_bottom=12,
        )

        self._clamp.set_child(self._content_box)
        scrolled.set_child(self._clamp)

        # Empty state
        self._empty = Adw.StatusPage(
            title="No Documents",
            description="This folder has no markdown files.",
            icon_name="marklite-file-markdown-symbolic",
        )
        self._empty.set_visible(False)

        self.append(scrolled)
        self.append(self._empty)

        self._setup_context_menu()

    def show_folder(self, folder_path):
        """Display documents for the given folder path, or all if ALL_DOCUMENTS."""
        self._current_folder = folder_path
        self._clear()

        if folder_path == Sidebar.ALL_DOCUMENTS:
            self._show_all_documents()
        else:
            self._show_single_folder(folder_path)

    def _clear(self):
        child = self._content_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self._content_box.remove(child)
            child = next_child

    def _show_single_folder(self, dir_path):
        files = _collect_md_files(dir_path)
        if not files:
            self._empty.set_visible(True)
            return
        self._empty.set_visible(False)

        listbox = self._make_listbox()
        for path in files:
            listbox.append(self._make_document_row(path))
        self._content_box.append(listbox)

    def _show_all_documents(self):
        root = self._settings.root_directory
        groups = _collect_md_files_recursive(root)

        if not groups:
            self._empty.set_visible(True)
            return
        self._empty.set_visible(False)

        for dir_path, files in groups.items():
            # Section header
            if dir_path == root:
                section_name = "Root"
            else:
                section_name = os.path.relpath(dir_path, root)

            header = Gtk.Label(
                label=section_name,
                xalign=0,
                css_classes=["heading"],
                margin_top=20,
                margin_bottom=6,
                margin_start=4,
            )
            self._content_box.append(header)

            listbox = self._make_listbox()
            for path in files:
                listbox.append(self._make_document_row(path))
            self._content_box.append(listbox)

    def _make_listbox(self):
        listbox = Gtk.ListBox(css_classes=["boxed-list"])
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.connect("row-activated", self._on_row_activated)
        return listbox

    def _make_document_row(self, path):
        box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            margin_start=12,
            margin_end=12,
            margin_top=10,
            margin_bottom=10,
        )

        info_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            hexpand=True,
            spacing=2,
        )

        basename = os.path.basename(path)
        stem = basename[:-3] if basename.lower().endswith(".md") else basename
        md_title = _read_title(path)
        display_name = md_title or stem

        title = Gtk.Label(
            label=display_name,
            css_classes=["heading"],
            xalign=0,
        )

        # Subtitle: filename + size + modified date
        try:
            stat = os.stat(path)
            size_date = f"{_format_size(stat.st_size)} \u00b7 {_format_date(stat.st_mtime)}"
        except OSError:
            size_date = ""

        if md_title:
            subtitle_text = f"{stem} \u00b7 {size_date}" if size_date else stem
        else:
            subtitle_text = size_date

        subtitle = Gtk.Label(
            label=subtitle_text,
            css_classes=["dim-label", "caption"],
            xalign=0,
        )

        info_box.append(title)
        info_box.append(subtitle)
        box.append(info_box)

        row = Gtk.ListBoxRow(child=box)
        row._file_path = path

        # Right-click gesture per row
        gesture = Gtk.GestureClick(button=Gdk.BUTTON_SECONDARY)
        gesture.connect("pressed", self._on_row_right_click, row)
        row.add_controller(gesture)

        return row

    def _on_row_activated(self, _listbox, row):
        if hasattr(row, "_file_path"):
            self.emit("file-selected", row._file_path)

    # ---- Context menu ---------------------------------------------------

    def _setup_context_menu(self):
        section = Gio.Menu()
        section.append("Rename", "docpanel.rename")
        section.append("Move to Trash", "docpanel.trash")
        section.append("Reveal in File Manager", "docpanel.reveal")

        menu = Gio.Menu()
        menu.append_section(None, section)

        self._popover = Gtk.PopoverMenu(menu_model=menu)
        self._popover.set_parent(self)
        self._popover.set_has_arrow(False)

        group = Gio.SimpleActionGroup()

        rename_action = Gio.SimpleAction.new("rename", None)
        rename_action.connect("activate", self._on_rename_activate)
        group.add_action(rename_action)

        trash_action = Gio.SimpleAction.new("trash", None)
        trash_action.connect("activate", self._on_trash_activate)
        group.add_action(trash_action)

        reveal_action = Gio.SimpleAction.new("reveal", None)
        reveal_action.connect("activate", self._on_reveal_activate)
        group.add_action(reveal_action)

        self.insert_action_group("docpanel", group)

    def _on_row_right_click(self, gesture, _n_press, x, y, row):
        self._context_path = row._file_path

        # Compute position relative to self (popover parent)
        src_point = Graphene.Point()
        src_point.x = x
        src_point.y = y
        success, dest_point = row.compute_point(self, src_point)
        if success:
            px, py = dest_point.x, dest_point.y
        else:
            px, py = x, y

        rect = Gdk.Rectangle()
        rect.x = int(px)
        rect.y = int(py)
        rect.width = 1
        rect.height = 1
        self._popover.set_pointing_to(rect)
        self._popover.popup()

    def _on_reveal_activate(self, *_args):
        if not self._context_path:
            return
        gfile = Gio.File.new_for_path(self._context_path)
        launcher = Gtk.FileLauncher.new(gfile)
        launcher.open_containing_folder(self.get_root(), None, None)

    def _on_trash_activate(self, *_args):
        if not self._context_path:
            return
        name = os.path.basename(self._context_path)
        dialog = Adw.AlertDialog(
            heading="Move to Trash?",
            body=f"\u201c{name}\u201d will be moved to the trash.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("trash", "Move to Trash")
        dialog.set_response_appearance("trash", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_trash_response, self._context_path)
        dialog.present(self.get_root())

    def _on_trash_response(self, _dialog, response, path):
        if response != "trash":
            return
        gfile = Gio.File.new_for_path(path)
        try:
            gfile.trash(None)
        except Exception:
            return
        self.emit("file-trashed", path)
        self.refresh()

    def _on_rename_activate(self, *_args):
        if not self._context_path:
            return
        name = os.path.basename(self._context_path)
        dialog = Adw.AlertDialog(
            heading="Rename",
            body=f"Enter a new name for \u201c{name}\u201d:",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("rename", "Rename")
        dialog.set_response_appearance("rename", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("rename")
        dialog.set_close_response("cancel")

        entry = Gtk.Entry(text=name)
        entry.set_activates_default(True)
        dot = name.rfind(".")
        sel_end = dot if dot > 0 else len(name)
        entry.connect("map", self._focus_and_select, 0, sel_end)
        dialog.set_extra_child(entry)
        dialog.connect("response", self._on_rename_response, self._context_path, entry)
        dialog.present(self.get_root())

    @staticmethod
    def _focus_and_select(entry, start, end):
        entry.grab_focus()
        entry.select_region(start, end)

    def _on_rename_response(self, _dialog, response, old_path, entry):
        if response != "rename":
            return
        new_name = entry.get_text().strip()
        old_name = os.path.basename(old_path)
        if not new_name or new_name == old_name:
            return
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        if os.path.exists(new_path):
            return
        try:
            os.rename(old_path, new_path)
        except OSError:
            return
        self.emit("file-renamed", old_path, new_path)
        self.refresh()

    # ---- Public ---------------------------------------------------------

    def refresh(self):
        if self._current_folder:
            self.show_folder(self._current_folder)
