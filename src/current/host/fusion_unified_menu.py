"""Open one prepared private run with its menu and game in the same process."""

import argparse
import time
from pathlib import Path
from menu_host.store import Store
from native_menu.unified import PreparedController


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--slot", type=int, choices=(1, 2, 3), default=1)
    args = parser.parse_args()
    store = Store(args.profile)
    with store.lock():
        controller = PreparedController(store, args.slot)
        try:
            controller.open()
            controller.enter()
            while not controller.closed:
                controller.tick()
                time.sleep(0.04)
        finally:
            controller.close()


if __name__ == "__main__":
    main()
