"""Application-local Windows bootstrap; profile data never goes in Programs."""

import json
import os
import sys
from pathlib import Path


def configure(root):
    root = Path(root).resolve()
    state = Path(os.environ["LOCALAPPDATA"]) / "BoshyRandomizer"
    state.mkdir(parents=True, exist_ok=True)
    config = {
        "schema": 1,
        "prefix": str(state),
        "original": str(root / "resources/original.bin"),
        "soundpacks": str(root / "resources/soundpacks"),
        "game": str(root / "game/I Wanna Be The Boshy.exe"),
        "wine": sys.executable,  # Unused on native Windows; retained config schema.
        "repository": str(root / "shared"),
    }
    # A launcher process gets its own configuration; parallel launch attempts
    # cannot replace the paths of a host that has already read its config.
    path = state / ("runtime-" + str(os.getpid()) + ".json")
    path.write_text(json.dumps(config), encoding="utf-8")
    os.environ["BOSHY_RUNTIME_CONFIG"] = str(path)
    return path


def main():
    root = Path(__file__).resolve().parents[2]
    config = configure(root)
    try:
        from fusion_native_menu import main as run

        run()
    except Exception:
        import traceback
        from ctypes import windll

        error = traceback.format_exc()
        report = config.parent / "startup-error.txt"
        report.write_text(error, encoding="utf-8")
        windll.user32.MessageBoxW(
            None,
            "Boshy Randomizer could not start.\n\n" + error[-1800:],
            "Boshy Randomizer",
            0x10,
        )
        raise
    finally:
        config.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
