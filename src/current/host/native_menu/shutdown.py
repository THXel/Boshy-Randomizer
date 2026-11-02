"""Bounded regular close requests, rechecking ownership before every retry."""

import time


def close_owned(folder, processes, windows, request, *, timeout=8.0):
    end = time.monotonic() + timeout
    next_request = 0.0
    retry = False
    while True:
        owned = processes()
        if folder not in owned.values():
            return
        now = time.monotonic()
        if now >= end:
            raise RuntimeError("Native menu still running")
        if now >= next_request:
            for row in windows():
                if owned.get(int(row[2])) == folder:
                    try:
                        request(row, retry)
                    except OSError:
                        # A successful close can race the following request.
                        if processes().get(int(row[2])) == folder:
                            raise
            retry = True
            next_request = now + 0.75
        time.sleep(0.1)
