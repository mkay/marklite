import json
import os
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import GObject

DEFAULTS = {
    "root_directory": str(Path.home() / "Documents"),
    "font_family": "Sans",
    "font_size": 16,
    "theme": "system",
    "editor_font_family": "Monospace",
    "editor_font_size": 14,
    "file_watching": True,
}

CONFIG_DIR = Path.home() / ".config" / "marklite"
CONFIG_FILE = CONFIG_DIR / "settings.json"


class SettingsManager(GObject.Object):
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self):
        super().__init__()
        self._data = dict(DEFAULTS)
        self._load()

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    stored = json.load(f)
                for k, v in stored.items():
                    if k in DEFAULTS:
                        self._data[k] = v
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key):
        return self._data.get(key, DEFAULTS.get(key))

    def set(self, key, value):
        if self._data.get(key) != value:
            self._data[key] = value
            self._save()
            self.emit("changed", key)

    @property
    def root_directory(self):
        return os.path.expanduser(self.get("root_directory"))

    @property
    def font_family(self):
        return self.get("font_family")

    @property
    def font_size(self):
        return self.get("font_size")

    @property
    def theme(self):
        return self.get("theme")

    @property
    def editor_font_family(self):
        return self.get("editor_font_family")

    @property
    def editor_font_size(self):
        return self.get("editor_font_size")

    @property
    def file_watching(self):
        return self.get("file_watching")
