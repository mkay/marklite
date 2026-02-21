import os
import shutil

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Gio, GObject, Gdk, Pango


class FileItem(GObject.Object):
    __gtype_name__ = "FileItem"

    def __init__(self, path, name, is_dir):
        super().__init__()
        self.path = path
        self.name = name
        self.is_dir = is_dir


class Sidebar(Gtk.Box):
    __gsignals__ = {
        "file-selected": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "file-trashed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "file-renamed": (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
    }

    def __init__(self, settings):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._settings = settings
        self._current_path = None
        self._context_item = None
        self._drop_highlight = None

        self.set_size_request(220, -1)

        # Drop-highlight CSS
        css = Gtk.CssProvider()
        css.load_from_string(
            ".drop-target { background: alpha(@accent_color, 0.15); "
            "border-radius: 6px; }"
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._listview = Gtk.ListView()
        self._listview.set_vexpand(True)
        self._listview.set_margin_top(6)
        self._listview.set_margin_bottom(6)
        self._listview.add_css_class("navigation-sidebar")

        self._build_model()
        self._setup_context_menu()
        self._setup_drop_target()

        scrolled.set_child(self._listview)
        self.append(scrolled)

        # Bottom action bar
        action_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        action_bar.add_css_class("toolbar")

        new_file_btn = Gtk.Button(icon_name="document-new-symbolic",
                                  tooltip_text="New File")
        new_file_btn.set_hexpand(True)
        new_file_btn.connect("clicked", lambda _b: self._new_file(self._settings.root_directory))

        new_dir_btn = Gtk.Button(icon_name="folder-new-symbolic",
                                 tooltip_text="New Folder")
        new_dir_btn.set_hexpand(True)
        new_dir_btn.connect("clicked", lambda _b: self._new_directory(self._settings.root_directory))

        action_bar.append(new_file_btn)
        action_bar.append(new_dir_btn)
        self.append(action_bar)

    # ---- Model ----------------------------------------------------------

    def _build_model(self):
        root_store = self._create_dir_model(self._settings.root_directory)

        tree_model = Gtk.TreeListModel.new(
            root_store,
            passthrough=False,
            autoexpand=False,
            create_func=self._create_child_model,
        )

        selection = Gtk.SingleSelection(model=tree_model)
        selection.set_autoselect(False)
        selection.connect("selection-changed", self._on_selection_changed)
        self._selection = selection

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)

        self._listview.set_model(selection)
        self._listview.set_factory(factory)

    def _create_dir_model(self, dir_path):
        store = Gio.ListStore(item_type=FileItem)
        if not os.path.isdir(dir_path):
            return store

        try:
            entries = sorted(os.listdir(dir_path))
        except OSError:
            return store

        dirs = []
        files = []
        for name in entries:
            if name.startswith("."):
                continue
            full = os.path.join(dir_path, name)
            if os.path.isdir(full):
                dirs.append(FileItem(full, name, True))
            elif name.lower().endswith(".md"):
                files.append(FileItem(full, name, False))

        for item in dirs + files:
            store.append(item)
        return store

    def _create_child_model(self, item):
        if not item.is_dir:
            return None
        store = self._create_dir_model(item.path)
        if store.get_n_items() == 0:
            return None
        return store

    # ---- Factory --------------------------------------------------------

    def _on_factory_setup(self, _factory, list_item):
        expander = Gtk.TreeExpander()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon = Gtk.Image()
        label = Gtk.Label(xalign=0)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        box.append(icon)
        box.append(label)
        expander.set_child(box)
        list_item.set_child(expander)

        # Drag source per row
        drag = Gtk.DragSource()
        drag.set_actions(Gdk.DragAction.MOVE)
        drag.connect("prepare", self._on_drag_prepare)
        expander.add_controller(drag)

    def _on_factory_bind(self, _factory, list_item):
        expander = list_item.get_child()
        row = list_item.get_item()
        expander.set_list_row(row)

        item = row.get_item()
        expander._file_item = item   # stash for drag handler

        box = expander.get_child()
        icon = box.get_first_child()
        label = icon.get_next_sibling()

        if item.is_dir:
            icon.set_from_icon_name("folder-symbolic")
        else:
            icon.set_from_icon_name("text-x-generic-symbolic")

        label.set_label(item.name)

    # ---- Selection ------------------------------------------------------

    def _on_selection_changed(self, selection, _pos, _n_items):
        row = selection.get_selected_item()
        if row is None:
            return
        item = row.get_item()
        if item and not item.is_dir:
            self._current_path = item.path
            self.emit("file-selected", item.path)

    # ---- Drag source ----------------------------------------------------

    def _on_drag_prepare(self, source, _x, _y):
        expander = source.get_widget()
        item = getattr(expander, "_file_item", None)
        if item is None:
            return None
        val = GObject.Value(GObject.TYPE_STRING, item.path)
        return Gdk.ContentProvider.new_for_value(val)

    # ---- Drop target (single, on the listview) --------------------------

    def _setup_drop_target(self):
        drop = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
        drop.connect("drop", self._on_dnd_drop)
        drop.connect("motion", self._on_dnd_motion)
        drop.connect("leave", self._on_dnd_leave)
        self._listview.add_controller(drop)

    def _on_dnd_motion(self, _target, x, y):
        self._clear_drop_highlight()

        picked = self._listview.pick(x, y, Gtk.PickFlags.DEFAULT)
        if picked:
            item = self._find_item_from_widget(picked)
            if item and item.is_dir:
                exp = self._find_expander_from_widget(picked)
                if exp:
                    exp.add_css_class("drop-target")
                    self._drop_highlight = exp
                return Gdk.DragAction.MOVE

        return Gdk.DragAction.MOVE   # accept root-level drops too

    def _on_dnd_leave(self, _target):
        self._clear_drop_highlight()

    def _clear_drop_highlight(self):
        if self._drop_highlight:
            self._drop_highlight.remove_css_class("drop-target")
            self._drop_highlight = None

    def _on_dnd_drop(self, _target, value, x, y):
        source_path = value
        if not os.path.exists(source_path):
            return False

        # Determine destination directory
        dest_dir = self._settings.root_directory
        picked = self._listview.pick(x, y, Gtk.PickFlags.DEFAULT)
        if picked:
            item = self._find_item_from_widget(picked)
            if item:
                dest_dir = item.path if item.is_dir else os.path.dirname(item.path)

        source_name = os.path.basename(source_path)
        new_path = os.path.join(dest_dir, source_name)

        # Guard: no-op, already exists, or moving dir into itself
        if new_path == source_path:
            return False
        if os.path.exists(new_path):
            return False
        if os.path.isdir(source_path) and dest_dir.startswith(source_path + os.sep):
            return False

        try:
            shutil.move(source_path, new_path)
        except OSError:
            return False

        self._clear_drop_highlight()
        self.refresh()
        self.emit("file-renamed", source_path, new_path)
        return True

    # ---- Widget helpers -------------------------------------------------

    def _find_expander_from_widget(self, widget):
        w = widget
        while w and w != self._listview:
            if isinstance(w, Gtk.TreeExpander):
                return w
            w = w.get_parent()
        return None

    def _find_item_from_widget(self, widget):
        exp = self._find_expander_from_widget(widget)
        if exp:
            row = exp.get_list_row()
            if row:
                return row.get_item()
        return None

    # ---- Context menu ---------------------------------------------------

    def _setup_context_menu(self):
        item_section = Gio.Menu()
        item_section.append("Rename", "sidebar.rename")
        item_section.append("Move to Trash", "sidebar.trash")
        item_section.append("Reveal in File Manager", "sidebar.reveal")

        new_section = Gio.Menu()
        new_section.append("New File", "sidebar.new-file")
        new_section.append("New Folder", "sidebar.new-dir")

        menu = Gio.Menu()
        menu.append_section(None, item_section)
        menu.append_section(None, new_section)

        self._popover = Gtk.PopoverMenu(menu_model=menu)
        self._popover.set_parent(self._listview)
        self._popover.set_has_arrow(False)

        group = Gio.SimpleActionGroup()

        rename_action = Gio.SimpleAction.new("rename", None)
        rename_action.connect("activate", self._on_rename_activate)
        group.add_action(rename_action)
        self._rename_action = rename_action

        trash_action = Gio.SimpleAction.new("trash", None)
        trash_action.connect("activate", self._on_trash_activate)
        group.add_action(trash_action)
        self._trash_action = trash_action

        reveal_action = Gio.SimpleAction.new("reveal", None)
        reveal_action.connect("activate", self._on_reveal_activate)
        group.add_action(reveal_action)
        self._reveal_action = reveal_action

        new_file_action = Gio.SimpleAction.new("new-file", None)
        new_file_action.connect("activate", self._on_new_file_activate)
        group.add_action(new_file_action)

        new_dir_action = Gio.SimpleAction.new("new-dir", None)
        new_dir_action.connect("activate", self._on_new_dir_activate)
        group.add_action(new_dir_action)

        self._listview.insert_action_group("sidebar", group)

        gesture = Gtk.GestureClick(button=Gdk.BUTTON_SECONDARY)
        gesture.connect("pressed", self._on_right_click)
        self._listview.add_controller(gesture)

    def _on_right_click(self, gesture, _n_press, x, y):
        target = self._listview.pick(x, y, Gtk.PickFlags.DEFAULT)
        item = None
        if target is not None:
            item = self._find_item_from_widget(target)

        self._context_item = item
        self._rename_action.set_enabled(item is not None)
        self._trash_action.set_enabled(item is not None)
        self._reveal_action.set_enabled(item is not None)

        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        self._popover.set_pointing_to(rect)
        self._popover.popup()

    # ---- Reveal in File Manager -----------------------------------------

    def _on_reveal_activate(self, *_args):
        item = self._context_item
        if item is None:
            return
        gfile = Gio.File.new_for_path(item.path)
        launcher = Gtk.FileLauncher.new(gfile)
        launcher.open_containing_folder(self.get_root(), None, None)

    # ---- Trash ----------------------------------------------------------

    def _on_trash_activate(self, *_args):
        item = self._context_item
        if item is None:
            return

        window = self.get_root()
        dialog = Adw.AlertDialog(
            heading="Move to Trash?",
            body=f"\u201c{item.name}\u201d will be moved to the trash.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("trash", "Move to Trash")
        dialog.set_response_appearance("trash", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_trash_response, item)
        dialog.present(window)

    def _on_trash_response(self, _dialog, response, item):
        if response != "trash":
            return
        gfile = Gio.File.new_for_path(item.path)
        try:
            gfile.trash(None)
        except Exception:
            return
        trashed_path = item.path
        self.refresh()
        self.emit("file-trashed", trashed_path)

    # ---- Rename ---------------------------------------------------------

    def _on_rename_activate(self, *_args):
        item = self._context_item
        if item is None:
            return

        window = self.get_root()
        dialog = Adw.AlertDialog(
            heading="Rename",
            body=f"Enter a new name for \u201c{item.name}\u201d:",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("rename", "Rename")
        dialog.set_response_appearance("rename", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("rename")
        dialog.set_close_response("cancel")

        entry = Gtk.Entry()
        entry.set_text(item.name)
        basename = item.name
        dot = basename.rfind(".")
        sel_end = dot if dot > 0 and not item.is_dir else len(basename)
        entry.set_activates_default(True)
        entry.connect("map", self._focus_and_select, 0, sel_end)

        dialog.set_extra_child(entry)
        dialog.connect("response", self._on_rename_response, item, entry)
        dialog.present(window)

    def _on_rename_response(self, _dialog, response, item, entry):
        if response != "rename":
            return
        new_name = entry.get_text().strip()
        if not new_name or new_name == item.name:
            return

        old_path = item.path
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        if os.path.exists(new_path):
            return

        try:
            os.rename(old_path, new_path)
        except OSError:
            return
        self.refresh()
        self.emit("file-renamed", old_path, new_path)

    # ---- New file / folder ----------------------------------------------

    def _context_dir(self):
        item = self._context_item
        if item is None:
            return self._settings.root_directory
        if item.is_dir:
            return item.path
        return os.path.dirname(item.path)

    def _on_new_file_activate(self, *_args):
        self._new_file(self._context_dir())

    def _on_new_dir_activate(self, *_args):
        self._new_directory(self._context_dir())

    @staticmethod
    def _focus_and_select(entry, start, end):
        entry.grab_focus()
        entry.select_region(start, end)

    def _new_file(self, parent_dir):
        window = self.get_root()
        dialog = Adw.AlertDialog(
            heading="New File",
            body="Enter a name for the new markdown file:",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("create", "Create")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("create")
        dialog.set_close_response("cancel")

        entry = Gtk.Entry()
        entry.set_text("Untitled.md")
        entry.set_activates_default(True)
        entry.connect("map", self._focus_and_select, 0, entry.get_text().rfind("."))
        dialog.set_extra_child(entry)

        dialog.connect("response", self._on_new_file_response, parent_dir, entry)
        dialog.present(window)

    def _on_new_file_response(self, _dialog, response, parent_dir, entry):
        if response != "create":
            return
        name = entry.get_text().strip()
        if not name:
            return
        if not name.lower().endswith(".md"):
            name += ".md"
        path = os.path.join(parent_dir, name)
        if os.path.exists(path):
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# {os.path.splitext(name)[0]}\n")
        except OSError:
            return
        self.refresh()
        self.emit("file-selected", path)

    def _new_directory(self, parent_dir):
        window = self.get_root()
        dialog = Adw.AlertDialog(
            heading="New Folder",
            body="Enter a name for the new folder:",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("create", "Create")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("create")
        dialog.set_close_response("cancel")

        entry = Gtk.Entry()
        entry.set_text("New Folder")
        entry.set_activates_default(True)
        entry.connect("map", self._focus_and_select, 0, len("New Folder"))
        dialog.set_extra_child(entry)

        dialog.connect("response", self._on_new_dir_response, parent_dir, entry)
        dialog.present(window)

    def _on_new_dir_response(self, _dialog, response, parent_dir, entry):
        if response != "create":
            return
        name = entry.get_text().strip()
        if not name:
            return
        path = os.path.join(parent_dir, name)
        if os.path.exists(path):
            return
        try:
            os.makedirs(path)
        except OSError:
            return
        self.refresh()

    # ---- Public ---------------------------------------------------------

    def refresh(self):
        self._build_model()

    def get_current_path(self):
        return self._current_path
