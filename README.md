# Stenmark

Your markdown librarian. A lightweight GTK4 Markdown reader and editor.

> **Alpha software.** Still tightening the screws..

![Stenmark Icon](data/de.singular.stenmark.svg)

## Features

- Folder sidebar with document panel — browse and manage markdown files
- Subfolder navigation — drill into nested folders from the document panel
- Root folder switcher — quickly change scope via the sidebar header
- Open a file or directory from the command line: `stenmark ~/notes/` or `stenmark todo.md`
- Full-text search across documents (`Ctrl+Shift+F`) — scoped to the selected folder
- Quick filter on the document list (`Ctrl+F` on the documents page)
- Find in document (`Ctrl+F` in viewer) with customizable highlight colors
- WebKit-based rendered markdown view with syntax highlighting
- CodeMirror 6 editor with live preview pane and scroll sync
- Dark mode — follows system theme
- File management — rename, move, trash, delete empty folders, create documents from context menu
- Pin folders to top — pinned folders appear first in the sidebar and document panel with a pin icon
- Pin documents to top — pinned documents float to the top of their folder; click the pin icon to unpin
- File watching — auto-reloads on disk changes
- Task list checkboxes — toggle directly in the rendered view
- Table of contents popover — navigate headings, click to scroll
- Export to PDF (via menu), open in external app, copy as rich text
- Welcome screen with root directory setup prompt when no folder is configured
- Remember last folder across sessions (optional, in Preferences)
- Configurable keyboard shortcuts, fonts, and themes

## Dependencies

- Python 3.10+
- GTK 4.0, libadwaita 1
- WebKitGTK 6.0
- python-markdown, Pygments
- Meson, Ninja (build)

## Install

### Arch Linux

```bash
pacman -S python python-gobject gtk4 libadwaita webkitgtk-6.0 python-markdown python-pygments meson ninja
makepkg -sic
```

### Debian / Ubuntu

```bash
sudo apt install ./stenmark_*.deb
```

### From source

```bash
meson setup builddir --prefix=/usr
meson compile -C builddir
sudo meson install -C builddir
```

## Usage

```bash
stenmark                        # opens the configured root directory
stenmark ~/Documents/Notes/     # opens a specific directory (session only)
stenmark ~/Notes/todo.md        # opens a file directly (sidebar hidden)
```

## Configuration

Settings are stored in `~/.config/stenmark/settings.json` and can be changed from the Preferences dialog. All changes take effect immediately.

## License

MIT

## Credits

Stenmark uses [Phosphor Icons](https://phosphoricons.com/) (MIT)

## Screenshots

![View screen](assets/stenmark_view.png)

![Editor screen](assets/stenmark_edit.png)

## Disclaimer

This project was developed with AI assistance. The code has been analysed with Codacy and Bandit. Use at your own discretion.  
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/2256d98bf65c4dccac37123e0d824d8f)](https://app.codacy.com/gh/mkay/stenmark/dashboard)