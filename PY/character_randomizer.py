# ======================================================
# character_randomizer.py
# - Lädt Charakter-Pool aus INI/characters_rando.json
# - Schreibt Character / CharacterName in onlineLicense.ini (RC4)
# - API:
#     set_character(char_id, char_name)
#     set_random_character() -> {"id": int, "name": str}
#
#  Extra:
#   - No-Repeat-Pool + Anti-Back-to-Back
#
#  NEU:
#   - Character Lock / F3-Block (nur Windows)
#       enable_character_lock(): sperrt F3 (Character-Menü in IWBTB)
#       disable_character_lock(): gibt F3 wieder frei
#   - Seed-Unterstützung:
#       init_seed(seed): initialisiert deterministische RNG für Charakterwahl
# ======================================================

from __future__ import annotations
import os
import json
import random
import threading
import ctypes
import atexit

from .config import ini_folder, iwbtb_folder, rc4_key
from .rc4_utils import decrypt_save, encrypt_save
from .logger import log

# Pfade
_CHAR_JSON_PATH = os.path.join(ini_folder, "characters_rando.json")
_IWBTB_LICENSE_PATH = os.path.join(iwbtb_folder, "onlineLicense.ini")

# --- interner Pool-State -----------------------------------------------------
_CHAR_POOL: list[dict] | None = None
_UNUSED_POOL: list[dict] = []
_LAST_CHOICE: dict | None = None

# NEU: Seeded RNG (optional)
_SEEDED_RNG: random.Random | None = None


def init_seed(seed: int | None):
    """
    Initialisiert eine lokale RNG-Instanz für deterministische Charakterwahl.
    Wird z.B. aus rando_script mit cfg.route_seed aufgerufen.
    """
    global _SEEDED_RNG, _UNUSED_POOL, _LAST_CHOICE

    if seed is None:
        _SEEDED_RNG = None
        return

    try:
        seed_int = int(seed)
        _SEEDED_RNG = random.Random(seed_int)
        log(f"🎲 Character RNG seeded with: {seed_int}")
    except Exception as e:
        _SEEDED_RNG = None
        log(f"⚠️ Character seed invalid ({seed!r}) – fallback to normal randomizer: {e}")
        return

    # Pool-Zustand zurücksetzen, damit der Seed-Durchlauf sauber startet
    _UNUSED_POOL.clear()
    _LAST_CHOICE = None


def _shuffle_with_rng(seq: list, rnd: random.Random):
    """
    Kleine Hilfsfunktion, um eine Liste mit einer gegebenen RNG zu mischen
    (Fisher-Yates, ohne globales random zu benutzen).
    """
    n = len(seq)
    for i in range(n - 1, 0, -1):
        j = int(rnd.random() * (i + 1))
        seq[i], seq[j] = seq[j], seq[i]


# ---------------------------------------------------------------------------
#  F3-Block / Character Lock (nur Windows)
# ---------------------------------------------------------------------------

if os.name == "nt":
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    WH_KEYBOARD_LL = 13
    WM_KEYDOWN = 0x0100
    WM_SYSKEYDOWN = 0x0104
    VK_F3 = 0x72

    class KBDLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [
            ("vkCode", ctypes.c_uint32),
            ("scanCode", ctypes.c_uint32),
            ("flags", ctypes.c_uint32),
            ("time", ctypes.c_uint32),
            ("dwExtraInfo", ctypes.c_void_p),
        ]

    class MSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", ctypes.c_void_p),
            ("message", ctypes.c_uint32),
            ("wParam", ctypes.c_size_t),
            ("lParam", ctypes.c_size_t),
            ("time", ctypes.c_uint32),
            ("pt_x", ctypes.c_long),
            ("pt_y", ctypes.c_long),
        ]

    # Signaturen explizit setzen (hilft SetWindowsHookExW etc.)
    user32.SetWindowsHookExW.argtypes = [
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
    ]
    user32.SetWindowsHookExW.restype = ctypes.c_void_p

    user32.CallNextHookEx.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    user32.CallNextHookEx.restype = ctypes.c_long

    user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
    user32.UnhookWindowsHookEx.restype = ctypes.c_bool

    user32.GetMessageW.argtypes = [
        ctypes.POINTER(MSG),
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
    ]
    user32.GetMessageW.restype = ctypes.c_int

    LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
        ctypes.c_long, ctypes.c_int, ctypes.c_uint32, ctypes.c_void_p
    )

    _F3_BLOCK_ACTIVE: bool = False
    _HOOK_PROC: LowLevelKeyboardProc | None = None
    _HOOK_HANDLE = None
    _HOOK_THREAD: threading.Thread | None = None

    def _low_level_keyboard_proc(nCode, wParam, lParam):
        """
        Low-Level Keyboard Hook:
        - wenn _F3_BLOCK_ACTIVE True ist und F3 gedrückt wird,
          wird das Event geschluckt (return 1).
        """
        try:
            if nCode == 0 and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                if kb.vkCode == VK_F3 and _F3_BLOCK_ACTIVE:
                    return 1  # F3 blocken
        except Exception as e:
            try:
                log(f"⚠️ Keyboard hook error: {e}")
            except Exception:
                pass

        return user32.CallNextHookEx(_HOOK_HANDLE, nCode, wParam, lParam)

    def _hook_thread_func():
        """
        Thread, der den LowLevelKeyboard-Hook setzt und eine Message-Loop fährt.
        Läuft als Daemon im Hintergrund, solange der Randomizer-Prozess lebt.
        """
        global _HOOK_PROC, _HOOK_HANDLE

        _HOOK_PROC = LowLevelKeyboardProc(_low_level_keyboard_proc)

        # Wichtig: Für WH_KEYBOARD_LL darf hMod = NULL sein,
        # threadId = 0 für globalen Hook.
        _HOOK_HANDLE = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            _HOOK_PROC,
            ctypes.c_void_p(0),  # hMod = NULL
            0,                   # threadId = 0 => global
        )

        if not _HOOK_HANDLE:
            err = kernel32.GetLastError()
            try:
                log(f"⛔ Failed to install keyboard hook for F3 block. GetLastError={err}")
            except Exception:
                pass
            return

        try:
            log("✅ Keyboard hook for F3 block installed.")
        except Exception:
            pass

        msg = MSG()
        # klassische Message-Loop
        while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if _HOOK_HANDLE:
            user32.UnhookWindowsHookEx(_HOOK_HANDLE)

    def _ensure_hook_thread():
        """
        Stellt sicher, dass der Hook-Thread läuft.
        """
        global _HOOK_THREAD
        if _HOOK_THREAD is None or not _HOOK_THREAD.is_alive():
            _HOOK_THREAD = threading.Thread(
                target=_hook_thread_func, name="F3BlockHookThread", daemon=True
            )
            _HOOK_THREAD.start()

    def _uninstall_hook():
        """
        Versucht beim Prozessende, den Hook sauber zu entfernen.
        """
        global _HOOK_HANDLE
        try:
            if _HOOK_HANDLE:
                user32.UnhookWindowsHookEx(_HOOK_HANDLE)
                _HOOK_HANDLE = None
                log("🧹 Keyboard hook for F3 block uninstalled.")
        except Exception:
            pass

    atexit.register(_uninstall_hook)

    def enable_character_lock():
        """
        Aktiviert den Character-Lock:
        - F3 wird blockiert, solange dieser Modus aktiv ist.
        - Der Hook-Thread wird bei Bedarf automatisch gestartet.
        """
        global _F3_BLOCK_ACTIVE
        _ensure_hook_thread()
        _F3_BLOCK_ACTIVE = True
        try:
            log("🔒 Character lock enabled – F3 will be blocked (no character menu).")
        except Exception:
            pass

    def disable_character_lock():
        """
        Deaktiviert den Character-Lock:
        - F3 wird wieder normal durchgereicht.
        """
        global _F3_BLOCK_ACTIVE
        _F3_BLOCK_ACTIVE = False
        try:
            log("🔓 Character lock disabled – F3 is no longer blocked.")
        except Exception:
            pass

else:
    # Nicht-Windows: No-Op mit Log
    def enable_character_lock():
        log("ℹ️ Character lock (F3 block) not available on this platform.")

    def disable_character_lock():
        log("ℹ️ Character lock (F3 block) not available on this platform.")


# ---------------------------------------------------------------------------
#  Charakter-Pool / Randomizer-Logik
# ---------------------------------------------------------------------------

def _load_char_pool_from_disk() -> list[dict]:
    """
    Lädt den Charakter-Pool direkt von der Platte.
    Returns Liste von dicts: {name, id} aus INI/characters_rando.json,
    gefiltert auf status == "unlocked".
    """
    try:
        if not os.path.exists(_CHAR_JSON_PATH):
            raise FileNotFoundError(_CHAR_JSON_PATH)

        with open(_CHAR_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f) or {}

        pool = [
            {"name": c.get("name", "Boshy"), "id": int(c.get("id", 12))}
            for c in (data.get("characters") or [])
            if str(c.get("status", "unlocked")).lower() == "unlocked"
        ]
        if pool:
            log(f"📦 Loaded {len(pool)} characters from characters_rando.json")
            return pool
    except Exception as e:
        log(f"⚠️ _load_char_pool_from_disk failed, using fallback Boshy: {e}")

    log("📦 Fallback pool: only Boshy (ID 12)")
    return [{"name": "Boshy", "id": 12}]


def _ensure_pool():
    global _CHAR_POOL, _UNUSED_POOL

    if _CHAR_POOL is None:
        _CHAR_POOL = _load_char_pool_from_disk()

    if not _UNUSED_POOL:
        _UNUSED_POOL = list(_CHAR_POOL)
        # wichtig: hier bewusst globales random, damit sich das alte Verhalten
        # ohne Seed nicht ändert. Seeded-Modus mischt separat.
        random.shuffle(_UNUSED_POOL)
        names_preview = ", ".join(c["name"] for c in _UNUSED_POOL[:5])
        log(f"🎲 Character cycle refreshed (size={len(_UNUSED_POOL)}), first few: {names_preview}")


def _next_character_from_pool() -> dict:
    global _UNUSED_POOL, _LAST_CHOICE

    _ensure_pool()

    if len(_UNUSED_POOL) == 1 and _LAST_CHOICE is not None:
        _UNUSED_POOL = list(_CHAR_POOL or [])
        random.shuffle(_UNUSED_POOL)

    if not _UNUSED_POOL:
        _UNUSED_POOL = list(_CHAR_POOL or [])
        random.shuffle(_UNUSED_POOL)

    choice = _UNUSED_POOL.pop(0)

    if (
        _LAST_CHOICE is not None
        and len(_UNUSED_POOL) > 0
        and choice.get("id") == _LAST_CHOICE.get("id")
        and choice.get("name") == _LAST_CHOICE.get("name")
    ):
        _UNUSED_POOL.append(choice)
        choice = _UNUSED_POOL.pop(0)

    _LAST_CHOICE = choice
    return choice


def _next_character_seeded() -> dict:
    """
    Wie _next_character_from_pool, aber nutzt die lokale Seed-RNG
    (_SEEDED_RNG), falls vorhanden. Fällt zurück auf den normalen Pool,
    wenn keine Seed-RNG gesetzt ist.
    """
    global _CHAR_POOL, _UNUSED_POOL, _LAST_CHOICE, _SEEDED_RNG

    if _SEEDED_RNG is None:
        return _next_character_from_pool()

    if _CHAR_POOL is None:
        _CHAR_POOL = _load_char_pool_from_disk()

    if not _UNUSED_POOL:
        _UNUSED_POOL = list(_CHAR_POOL or [])
        _shuffle_with_rng(_UNUSED_POOL, _SEEDED_RNG)
        names_preview = ", ".join(c["name"] for c in _UNUSED_POOL[:5])
        log(f"🎲 (Seeded) Character cycle refreshed (size={len(_UNUSED_POOL)}), first few: {names_preview}")

    if len(_UNUSED_POOL) == 0:
        _UNUSED_POOL = list(_CHAR_POOL or [])
        _shuffle_with_rng(_UNUSED_POOL, _SEEDED_RNG)

    choice = _UNUSED_POOL.pop(0)

    if (
        _LAST_CHOICE is not None
        and len(_UNUSED_POOL) > 0
        and choice.get("id") == _LAST_CHOICE.get("id")
        and choice.get("name") == _LAST_CHOICE.get("name")
    ):
        _UNUSED_POOL.append(choice)
        choice = _UNUSED_POOL.pop(0)

    _LAST_CHOICE = choice
    return choice


def _set_license_character_plaintext(plain: str, char_id: int, char_name: str) -> str:
    lines = (plain or "").splitlines()
    out = []
    in_license = False
    saw_char = False
    saw_name = False
    had_any_section = False

    for ln in lines:
        s = ln.strip()
        if s.startswith("[") and s.endswith("]"):
            if in_license:
                if not saw_char:
                    out.append(f"Character={char_id}")
                if not saw_name:
                    out.append(f"CharacterName={char_name}")
            in_license = (s.strip("[]").lower() == "license")
            saw_char = False
            saw_name = False
            out.append(ln)
            had_any_section = True
            continue

        if in_license and "=" in s:
            k, _ = s.split("=", 1)
            kl = k.strip().lower()
            if kl == "character":
                out.append(f"Character={char_id}")
                saw_char = True
                continue
            if kl == "charactername":
                out.append(f"CharacterName={char_name}")
                saw_name = True
                continue

        out.append(ln)

    if not had_any_section:
        out.append("[License]")
        out.append(f"Character={char_id}")
        out.append(f"CharacterName={char_name}")
    elif in_license:
        if not saw_char:
            out.append(f"Character={char_id}")
        if not saw_name:
            out.append(f"CharacterName={char_name}")

    return "\n".join(out) + "\n"


def _update_license_file(path: str, char_id: int, char_name: str) -> bool:
    try:
        if os.path.exists(path):
            plain = decrypt_save(path, rc4_key)
        else:
            plain = "[License]\n"
    except Exception as e:
        log(f"⚠️ Failed to decrypt license at {path}, creating new [License]: {e}")
        plain = "[License]\n"

    new_plain = _set_license_character_plaintext(plain, int(char_id), str(char_name))
    try:
        encrypt_save(new_plain, path, rc4_key)
        return True
    except Exception as e:
        log(f"⚠️ Failed to encrypt/write license at {path}: {e}")
        return False


def set_character(char_id: int, char_name: str):
    ok_iwbtb = _update_license_file(_IWBTB_LICENSE_PATH, char_id, char_name)

    if ok_iwbtb:
        log(f"✅ IWBTB license updated for character {char_name} (ID={char_id})")
    else:
        log(f"⛔ Failed to update IWBTB license for character {char_name} (ID={char_id})")


def set_random_character():
    """
    Wählt einen zufälligen Charakter:
    - Wenn ein Seed gesetzt wurde (init_seed), wird der Seeded-Pfad genutzt.
    - Ansonsten bleibt das alte Verhalten (_next_character_from_pool).
    """
    if _SEEDED_RNG is not None:
        choice = _next_character_seeded()
        set_character(choice["id"], choice["name"])
        log(f"🎲 (Seeded) Random character set → {choice['name']} (ID={choice['id']})")
        return choice

    choice = _next_character_from_pool()
    set_character(choice["id"], choice["name"])
    log(f"🎲 Random character set → {choice['name']} (ID={choice['id']})")
    return choice
