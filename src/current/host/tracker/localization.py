"""Translate presentation fields without changing tracker identities or receipts."""

import json
from functools import lru_cache
from menu_host.labels import LANGUAGES, ROWS
from app_paths import REPO


@lru_cache(maxsize=5)
def catalogue(language):
    english = json.loads((REPO / "assets/locales/en.json").read_text())
    english.update(json.loads((REPO / "assets/locales" / (language + ".json")).read_text()))
    return english


def present(data, language):
    language = language if language in LANGUAGES else "en"
    strings = catalogue(language)
    index = LANGUAGES.index(language)
    result = dict(data)
    for field in ("location",):
        if field in result:
            result[field] = strings.get(result[field], result[field])
    for field in ("bosses", "goals", "route_stages"):
        if field in result:
            result[field] = [dict(row, name=strings.get(row["name"], row["name"])) for row in result[field]]
    if "active_extras" in result:
        result["active_extras"] = [
            dict(row,
                 label=ROWS[row["key"]][index] if row["key"] in ROWS else strings.get(row["label"], row["label"]),
                 hint=ROWS[row["key"] + "_hint"][index] if row["key"] + "_hint" in ROWS else strings.get(row["hint"], row["hint"]))
            for row in result["active_extras"]
        ]
    if data.get("test_run"):
        from native_menu.debug_actions import TEST_LABELS
        result["location"] = TEST_LABELS[index] + " · " + result.get("location", "")
    return result
