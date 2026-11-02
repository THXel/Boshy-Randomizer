"""Small user preferences shared by menu adapters; no run-seed side effects."""

import json
import locale
import os
from pathlib import Path

LANGUAGES = ("de", "en", "es", "ru", "ja")


def language_code(value):
    if not isinstance(value, str):
        return None
    code = value.strip().split(":", 1)[0].split(".", 1)[0].split("@", 1)[0]
    code = code.replace("-", "_").split("_", 1)[0].lower()
    return code if code in LANGUAGES else None


def system_language():
    if os.name == "nt":
        import ctypes

        name = ctypes.create_unicode_buffer(85)
        if ctypes.windll.kernel32.GetUserDefaultLocaleName(name, len(name)):
            return language_code(name.value) or "en"
    for key in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(key)
        if value:
            return language_code(value) or "en"
    try:
        return language_code(locale.getlocale()[0]) or "en"
    except (ValueError, TypeError):
        return "en"


def load_preferences(root):
    try:
        data = json.loads((Path(root) / "native-preferences.json").read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_preferences(root, **changes):
    from menu_host.store import atomic

    data = load_preferences(root)
    data.update(changes)
    atomic(Path(root) / "native-preferences.json", json.dumps(data).encode())


def load_language(root):
    chosen = load_preferences(root).get("language")
    return chosen if chosen in LANGUAGES else system_language()


def read_native_settings(path, timeout=0.5):
    """INI++ rewrites in place; tolerate only a bounded, transient write gap."""
    import configparser
    import time
    from menu_host.store import save

    deadline = time.monotonic() + timeout
    while True:
        try:
            before = path.read_bytes()
            cfg = save(path)
            if not cfg.has_section("Options") or not cfg["Options"]:
                raise ValueError("Native options write incomplete")
            time.sleep(0.005)
            if path.read_bytes() != before:
                raise ValueError("Native options changed during read")
            return cfg
        except (OSError, ValueError, configparser.Error):
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.01)
