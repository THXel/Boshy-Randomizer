"""Bounded read-only retry when MMF is rewriting the active save."""

import logging
import time


def validate(store, manifest):
    name = f"SaveFile{manifest['slot']}.ini"
    retryable = {
        f'Spielstand und Lauf passen nicht zusammen: {name}',
        f'Ungültiger Fundortstatus: {name}',
    }
    for attempt in range(5):
        try:
            result = store.validate(manifest)
            if attempt:
                logging.getLogger(__name__).info(
                    'Live save validation recovered after %s retries', attempt
                )
            return result
        except ValueError as error:
            # Asset integrity, manifest identity and all unrelated errors remain fatal.
            # A persistent foreign/damaged save still fails after at most 200 ms.
            if str(error) not in retryable or attempt == 4:
                raise
            time.sleep(0.05)
