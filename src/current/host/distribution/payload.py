"""Explicit host payload selection; no historical builds, profiles or test tools."""

import shutil
from pathlib import Path

MODULES = (
    "distribution",
    "platform_support",
    "gameplay",
    "menu_host",
    "music",
    "native_menu",
    "tracker",
    "transition",
    "visuals",
)
SHARED_MENU_FILES = ("menu_seed.py", "menu_clipboard.py")
LEGACY_HOST_FILES = ("menu_host/ui.py", "menu_host/audio.py", "menu_host/loading.py")

ROOT_FILES = (
    "app_paths.py",
    "build_profiles.py",
    "export_native_run.py",
    "export_route_probe.py",
    "fusion_native_menu.py",
)
SUFFIXES = {".py", ".json", ".png", ".html", ".js", ".css", ".csx"}


def copy_tree(source, target, suffixes=SUFFIXES):
    source, target = Path(source), Path(target)
    seen = {}
    for path in sorted(source.rglob("*")):
        if (
            path.is_symlink()
            or not path.is_file()
            or path.suffix not in suffixes
            or "__pycache__" in path.parts
        ):
            continue
        if (
            path.name.endswith("_live.py")
            or path.name.startswith("test_")
            or path.name == "continuity.py"
        ):
            continue
        key = path.relative_to(source).as_posix().casefold()
        if key in seen:
            if path.read_bytes() != seen[key].read_bytes():
                raise ValueError("Conflicting Windows package paths: " + key)
            continue  # Identical case aliases cannot coexist on Windows.
        seen[key] = path
        destination = target / path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def stage(lab, shared, destination):
    lab, shared, destination = map(Path, (lab, shared, destination))
    if destination.exists():
        raise FileExistsError("Host payload must be staged into a new directory")
    destination.mkdir(parents=True)
    app = destination / "app"
    app.mkdir()
    for name in ROOT_FILES:
        shutil.copy2(lab / name, app / name)
    for name in MODULES:
        copy_tree(lab / name, app / name)
    # These prototypes are still used by historical regression probes, but
    # the shipped entry point never imports their separate GUI/audio/loading UI.
    for relative in LEGACY_HOST_FILES:
        (app / relative).unlink(missing_ok=True)
    # Parser source is kept with its license. No editor, recovery UI, historical
    # binaries or mutable reference data is part of the runtime.
    vendor = lab / "KlikBack"
    copy_tree(vendor / "src/klikback/core", app / "KlikBack/src/klikback/core", {".py"})
    shutil.copy2(
        vendor / "src/klikback/__init__.py", app / "KlikBack/src/klikback/__init__.py"
    )
    shutil.copy2(vendor / "LICENSE", app / "KlikBack/LICENSE")
    for name in ("rules", "graphics", "audio"):
        copy_tree(
            shared / "src/python" / name,
            destination / "shared/src/python" / name,
            {".py"},
        )
    menu = destination / "shared/src/python/menu"
    menu.mkdir(parents=True)
    for name in SHARED_MENU_FILES:
        shutil.copy2(shared / "src/python/menu" / name, menu / name)
    copy_tree(shared / "src/shared/PY", destination / "shared/src/shared/PY", {".py"})
    copy_tree(
        shared / "assets",
        destination / "shared/assets",
        SUFFIXES | {".webp", ".ttf", ".ini"},
    )
    fonts = app / "resources/fonts"
    fonts.mkdir(parents=True)
    from platform_support.fonts import font_path

    for language in ("en", "ja"):
        font = Path(font_path(language))
        shutil.copy2(font, fonts / font.name)
    licenses = destination / "licenses"
    licenses.mkdir()
    for name, path in {
        "DejaVu.txt": "/usr/share/doc/fonts-dejavu-core/copyright",
        "Noto.txt": "/usr/share/doc/fonts-noto-cjk/copyright",
    }.items():
        shutil.copy2(path, licenses / name)
    return destination
