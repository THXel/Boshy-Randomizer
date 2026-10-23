from __future__ import annotations

import os
import re
from typing import Tuple

from .logger import log
from .config import rc4_key
from .rc4_utils import rc4_crypt, encrypt_save


def smart_read(path: str) -> Tuple[str | None, bool]:
    if not os.path.exists(path):
        return None, False
    try:
        with open(path, "rb") as f:
            raw = f.read()
        if not raw:
            return "", False
        # Encrypted bytes can contain both markers by chance; require an INI header.
        if re.match(br"\s*\[[A-Za-z0-9_ -]+\]\s*(?:\r?\n|$)", raw):
            text = raw.decode("latin-1", errors="ignore")
            return text, False
        decrypted = rc4_crypt(rc4_key, raw)
        try:
            text = decrypted.decode("latin-1", errors="ignore")
        except Exception:
            text = decrypted.decode("utf-8", errors="ignore")
        return text, True
    except Exception as e:
        try:
            name = os.path.basename(path)
        except Exception:
            name = str(path)
        log(f" smart_read failed for {name}: {e}")
        return None, False


def smart_write(path: str, text: str, was_encrypted: bool) -> None:
    try:
        if was_encrypted:
            encrypt_save(text, path, rc4_key)
        else:
            with open(path, "w", encoding="latin-1", errors="ignore") as f:
                f.write(text)
    except Exception as e:
        try:
            name = os.path.basename(path)
        except Exception:
            name = str(path)
        log(f" smart_write failed for {name}: {e}")
