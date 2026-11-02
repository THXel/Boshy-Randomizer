"""Explicit allowlist of isolated route fixtures (never the installed game)."""

CASES = {
    "mario-routes": "boss6.ini",
    "dedede-shortcut-routes": "save2.ini",
    "random1-bonus-routes": "save9.ini",
    "questionmark-routes": "boss19.ini",
    "ridley-routes": "boss20.ini",
    "ninja-routes": "save13.ini",
    "kid-routes": "save12.ini",
    "kappa-routes": "save17.ini",
    "random1-routes": "save9.ini",
    "random2-routes": "save10.ini",
    "finale-routes": "boss_solgryn.ini",
}

from exit_matrix import MATRIX

CASES.update({scene: spec[0] for scene, spec in MATRIX.items()})
