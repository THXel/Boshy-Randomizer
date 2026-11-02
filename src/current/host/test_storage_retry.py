"""Windows native readers can briefly deny atomic replacement."""

from unittest.mock import patch
import unittest
from platform_support.storage import _retry_windows_move


def winerror(code):
    error = OSError("Windows file is busy")
    error.winerror = code
    return error


def check_transient(code):
    calls = []

    def move(source, destination):
        calls.append((source, destination))
        if len(calls) < 3:
            raise winerror(code)

    with patch("platform_support.storage.time.sleep"):
        _retry_windows_move(move, "prepared", "existing")
    assert calls == [("prepared", "existing")] * 3


def test_permanent_access_denied_is_bounded():
    with (
        patch("platform_support.storage.time.monotonic", side_effect=[10, 10, 13]),
        patch("platform_support.storage.time.sleep"),
    ):
        with unittest.TestCase().assertRaises(OSError):
            _retry_windows_move(lambda *_: (_ for _ in ()).throw(winerror(5)), "a", "b")


def test_unrelated_error_is_not_retried():
    with patch("platform_support.storage.time.sleep") as sleep:
        with unittest.TestCase().assertRaises(OSError):
            _retry_windows_move(
                lambda *_: (_ for _ in ()).throw(winerror(112)), "a", "b"
            )
        sleep.assert_not_called()


class StorageRetryTests(unittest.TestCase):
    def test_transient_errors(self):
        for code in (5, 32, 33):
            with self.subTest(code=code):
                check_transient(code)

    test_permanent_access_denied_is_bounded = staticmethod(
        test_permanent_access_denied_is_bounded
    )
    test_unrelated_error_is_not_retried = staticmethod(
        test_unrelated_error_is_not_retried
    )
