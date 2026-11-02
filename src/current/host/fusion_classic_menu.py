"""Start the restored original intro and Game/Options menu in a private copy."""

import argparse
import time
from pathlib import Path
from menu_host.store import Store
from native_menu.classic import ClassicController
from export_route_probe import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        type=Path,
        default=ROOT / "outputs/Fusion-ClassicMenu-20261025/profile",
    )
    args = parser.parse_args()
    store = Store(args.profile)
    with store.lock():
        controller = ClassicController(store)
        try:
            controller.open()
            # No automatic Return: the full native intro belongs to the user.
            while not controller.closed:
                controller.tick()
                time.sleep(0.04)
        finally:
            controller.close()


if __name__ == "__main__":
    main()
