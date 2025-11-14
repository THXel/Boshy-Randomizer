# ======================================================
# character_randomizer.py
# - Lädt Charakter-Pool aus INI/characters_rando.json
# - Schreibt Character / CharacterName in onlineLicense.ini (RC4)
# - API:
#     set_character(char_id, char_name)
#     set_random_character() -> {"id": int, "name": str}
# ======================================================

from __future__ import annotations
import os, json, random

from .config import ini_folder, iwbtb_folder, rc4_key
from .rc4_utils import decrypt_save, encrypt_save
from .logger import log

# Pfade
_CHAR_JSON_PATH = os.path.join(ini_folder, "characters_rando.json")
_IWBTB_LICENSE_PATH = os.path.join(iwbtb_folder, "onlineLicense.ini")


def _load_char_pool():
    """
    Returns a list of dicts: {name, id} aus INI/characters_rando.json,
    gefiltert auf status == "unlocked".
    Fallback: Boshy (ID 12), falls Datei fehlt/leer ist.
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
            return pool
    except Exception as e:
        log(f"⚠️ _load_char_pool failed, using fallback Boshy: {e}")

    return [{"name": "Boshy", "id": 12}]


def _set_license_character_plaintext(plain: str, char_id: int, char_name: str) -> str:
    """
    Update [License] Character, CharacterName in plaintext license content.
    Erstellt [License]-Section, falls fehlend.
    """
    lines = (plain or "").splitlines()
    out = []
    in_license = False
    saw_char = False
    saw_name = False
    had_any_section = False

    for ln in lines:
        s = ln.strip()
        if s.startswith("[") and s.endswith("]"):
            # Section-Wechsel → ggf. fehlende Keys nachschieben
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

    # Falls keine Section vorhanden war → neue [License]-Section anhängen
    if not had_any_section:
        out.append("[License]")
        out.append(f"Character={char_id}")
        out.append(f"CharacterName={char_name}")
    elif in_license:
        # Wir waren bis zum Ende in [License]
        if not saw_char:
            out.append(f"Character={char_id}")
        if not saw_name:
            out.append(f"CharacterName={char_name}")

    return "\n".join(out) + "\n"


def _update_license_file(path: str, char_id: int, char_name: str) -> bool:
    """
    Aktualisiert eine einzelne onlineLicense.ini (RC4) an 'path'.
    Gibt True zurück, wenn es geklappt hat.
    """
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
    """
    Setzt Character & CharacterName NUR in:
      - IWBTB\onlineLicense.ini

    Die INI\onlineLicense.ini bleibt das unveränderte Template.
    """
    ok_iwbtb = _update_license_file(_IWBTB_LICENSE_PATH, char_id, char_name)

    if ok_iwbtb:
        log(f"✅ IWBTB license updated for character {char_name} (ID={char_id})")
    else:
        log(f"⛔ Failed to update IWBTB license for character {char_name} (ID={char_id})")


def set_random_character():
    """
    Wählt zufälligen freigeschalteten Charakter aus dem Pool und setzt ihn
    in der IWBTB-Lizenz. Gibt das choice-Dict zurück.
    """
    pool = _load_char_pool()
    choice = random.choice(pool)
    set_character(choice["id"], choice["name"])
    log(f"🎲 Random character set → {choice['name']} (ID={choice['id']})")
    return choice
