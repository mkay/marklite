# MarkLite

A lightweight GTK4 Markdown reader and editor.

## Features

- Sidebar file browser with expandable directories, filtered to `.md` files
- WebKit-based rendered markdown view with syntax highlighting
- Inline GtkSourceView editor with markdown highlighting
- Dark mode — follows system theme
- File management — rename, trash, new file/folder
- File watching — auto-reloads on disk changes
- Configurable root directory, fonts, and theme

## Dependencies

- Python 3.10+
- GTK 4.0, libadwaita 1
- WebKitGTK 6.0
- GtkSourceView 5
- python-markdown, Pygments
- Meson, Ninja (build)

### Arch Linux

```bash
pacman -S python python-gobject gtk4 libadwaita webkitgtk-6.0 gtksourceview5 python-markdown python-pygments meson ninja
```

## Install (Arch Linux)

```bash
makepkg -sic
```

## Building from source

```bash
meson setup builddir --prefix=/usr
ninja -C builddir
sudo meson install -C builddir
```

For a user-local install:

```bash
meson setup builddir --prefix=~/.local
ninja -C builddir
meson install -C builddir
```

## Configuration

Settings are stored in `~/.config/marklite/settings.json` and can be changed from the Preferences dialog. All changes take effect immediately.

## Disclaimer

This project was created with AI assistance. The code has not been thoroughly reviewed. Verify its correctness and suitability before use. 
