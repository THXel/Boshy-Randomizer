"""Stable application entry point for the native Boshy menu."""

from menu_controller import MenuController
from native_session import real_store


def run():
    MenuController(real_store()).run()


if __name__ == '__main__':
    run()
