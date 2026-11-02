"""Small, throttled progress protocol consumed by the setup wizard.

Counts belong to the current phase, never to an estimated overall duration.
A zero total requests an animated activity bar. No paths enter this protocol.
"""

import sys
import time


class Cancelled(Exception):
    """Cooperative cancellation at a transactional safe point."""

    code = "cancelled"


def ignore(stage, current=0, total=0):
    pass


class Reporter:
    def __init__(self, stream=None, clock=time.monotonic, cancel_file=None):
        self.stream = sys.stdout if stream is None else stream
        self.cancel_file = cancel_file
        self.clock = clock
        self.last_stage = None
        self.last_time = float("-inf")

    def __call__(self, stage, current=0, total=0):
        if self.cancel_file is not None and self.cancel_file.exists():
            raise Cancelled("Setup cancelled")
        if stage == "committing":
            self.cancel_file = None
        if not stage.isascii() or not stage.isalpha():
            raise ValueError("Invalid progress stage")
        if not 0 <= current <= total:
            raise ValueError("Invalid progress count")
        now = self.clock()
        if stage == self.last_stage and current != total and now - self.last_time < 0.2:
            return
        self.last_stage, self.last_time = stage, now
        if self.stream is not None:
            print(
                f"BOSHY_PROGRESS|{stage}|{current}|{total}",
                file=self.stream,
                flush=True,
            )
