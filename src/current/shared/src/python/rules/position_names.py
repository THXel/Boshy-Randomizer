"""Readable position names with a frozen compatibility boundary for old seeds.

Author positions using location names only. Historical BR12 seeds, route hashes
and native stage numbers keep their existing identities; never hash a new name
in place of its legacy key. Coordinates and game-save filenames are unrelated.
"""

LEGACY_KEYS = {
    "prehistorik": "save1.ini",
    "green_greens_before_kracko": "save2.ini",
    "cheetahmen_ii": "save3.ini",
    "vvvvvv_before_gravitron": "save4.ini",
    "vvvvvv_checkpoint": "save5.ini",
    "wario": "save6.ini",
    "castlevania": "save7.ini",
    "kid_icarus_upper_checkpoint": "save8.ini",
    "random_world_part_1": "save9.ini",
    "random_world_part_2": "save10.ini",
    "mega_man_world": "save11.ini",
    "kid_icarus_before_miniboss": "save12.ini",
    "ninja_gaiden_before_ryu": "save13.ini",
    "secret_mario": "save14.ini",
    "desert": "save15.ini",
    "justin_tv_before_kappa": "save17.ini",
    "terranigma_final_path": "save18.ini",
    "pokemon": "save19.ini",
    "tower": "save20.ini",
    "world_of_warcraft": "save21.ini",
    "ninja_gaiden_after_ryu": "save22.ini",
    "green_greens_after_kracko": "save23.ini",
    "hello_kitty": "boss1.ini",
    "kracko": "boss2.ini",
    "king_dedede": "boss3.ini",
    "ryu": "boss4.ini",
    "gastly_encounter": "boss5.ini",
    "mario": "boss6.ini",
    "gravitron": "boss7.ini",
    "biollante": "boss8.ini",
    "sonic": "boss9.ini",
    "gradius": "boss10.ini",
    "skeleton_king": "boss11.ini",
    "mega_man": "boss12.ini",
    "shang_tsung": "boss13.ini",
    "kid_icarus_encounter_checkpoint": "boss14.ini",
    "bomberman": "boss15.ini",
    "ryu_dodge": "boss16.ini",
    "missingno": "boss17.ini",
    "kappa_encounter_checkpoint": "boss18.ini",
    "questionmark": "boss19.ini",
    "ridley": "boss20.ini",
    "cheetahman": "boss21.ini",
    "ganon": "boss22.ini",
    "old_sonic": "boss23.ini",
    "solgryn": "boss_solgryn.ini",
    "kappa": "boss_kappa",
    "kid_icarus": "boss_kid_icarus",
    "kid_icarus_after_miniboss": "kid_icarus_after",
}

POSITION_NAMES = {legacy: name for name, legacy in LEGACY_KEYS.items()}


def legacy_key(name):
    """Translate a readable name; already-frozen and custom names pass through."""
    return LEGACY_KEYS.get(name, name)


def position_name(key):
    """Readable identifier, without a category prefix or filename extension."""
    return POSITION_NAMES.get(key, key)


def legacy_catalogue(points):
    """Normalize old or new catalogues, rejecting ambiguous duplicate aliases."""
    result = {}
    for name, point in points.items():
        key = legacy_key(name)
        if key in result:
            raise ValueError("Duplicate position aliases: " + key)
        result[key] = point
    return result


def legacy_positions(positions):
    return {
        category: legacy_catalogue(points) for category, points in positions.items()
    }
