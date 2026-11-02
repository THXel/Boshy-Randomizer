"""One registry for private Fusion builds and their isolated test namespaces."""

import json
from app_paths import LAB, PREFIX
BUILDS = {
    "music-original": (
        "route-build-music-original.json",
        "Boshy-music-original.exe",
        "-music-original",
    ),
    "music-kamilia3": (
        "route-build-music-kamilia3.json",
        "Boshy-music-kamilia3.exe",
        "-music-kamilia3",
    ),
    "music-wannafest22": (
        "route-build-music-wannafest22.json",
        "Boshy-music-wannafest22.exe",
        "-music-wannafest22",
    ),
    "blood-wannafest22": (
        "route-build-blood-wannafest22.json",
        "Boshy-blood-wannafest22.exe",
        "-blood-wannafest22",
    ),
    "blood-kamilia3": (
        "route-build-blood-kamilia3.json",
        "Boshy-blood-kamilia3.exe",
        "-blood-kamilia3",
    ),
    "blood-original": (
        "route-build-blood-original.json",
        "Boshy-blood-original.exe",
        "-blood-original",
    ),
    "base": ("route-build.json", "Boshy-routes.exe", ""),
    "guards": ("route-build-guards.json", "Boshy-route-guards.exe", "-guards"),
    "scenery": ("route-build-scenery.json", "Boshy-scenery.exe", "-scenery"),
    "actors": ("route-build-actors.json", "Boshy-actors.exe", "-actors"),
}


def profile(build):
    if build not in BUILDS:
        raise ValueError("Unknown private test build")
    return json.loads((LAB / BUILDS[build][0]).read_text())


def executable(build):
    return PREFIX / "drive_c/BoshyTransitions" / BUILDS[build][1]


def case_name(scene, build):
    return "rebuilt-" + scene + BUILDS[build][2]


def seed_folder(scene, build):
    return "seed-" + (build + "-" if build != "base" else "") + scene
