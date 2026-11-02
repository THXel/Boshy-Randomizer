"""Start the private native Fusion main menu, with its headless run controller."""

import argparse, time
import logging
from tracker.server import start as start_tracker, stop as stop_tracker
from pathlib import Path
from menu_host.store import Store
from native_menu.classic import ClassicController as Controller
from app_paths import PROFILE
import os


def main():
    if os.name == "nt":
        from platform_support.windows_api import dpi_aware
        dpi_aware()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--profile",
        type=Path,
        default=PROFILE,
    )
    p.add_argument(
        "--persistent",
        action="store_true",
        default=os.name == "nt",
        help="Keep the native menu and gameplay in one game process",
    )
    args = p.parse_args()
    if args.persistent:
        from functools import partial
        from export_native_run import export
        from native_menu.combined import CombinedController

        store = Store(args.profile, exporter=partial(export, dynamic=True))
        controller = partial(CombinedController, dynamic=True)
    else:
        store = Store(args.profile)
        controller = Controller
    with store.lock():
        c = controller(store)
        from menu_host.cleanup import collect
        c.cleanup_summary = collect(store)
        tracker = None
        try:
            try:
                tracker = start_tracker()
            except OSError as error:
                logging.warning("Browser tracker unavailable: %s", error)
            c.open()
            while not c.closed:
                c.tick()
                time.sleep(0.04)
        except Exception as error:
            if getattr(c, "diagnostics", None):
                c.diagnostics.record_error("runtime", error)
            raise
        finally:
            try:
                c.close()
                c.cleanup_summary = collect(store)
            finally:
                stop_tracker(tracker)


if __name__ == "__main__":
    main()
