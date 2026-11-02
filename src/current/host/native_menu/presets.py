"""Named user presets. Only validated run options are persisted, never seeds."""

import json
import unicodedata
import uuid
from pathlib import Path
from copy import deepcopy
from menu_host.draft import validate
from menu_host.store import atomic

LIMIT = 40


def name(value):
    value = unicodedata.normalize("NFC", value).strip()
    if (
        not value
        or len(value) > LIMIT
        or any(unicodedata.category(c).startswith("C") for c in value)
    ):
        raise ValueError("Invalid preset name")
    return value


class Presets:
    def __init__(self, root):
        self.path = Path(root) / "native-presets.json"

    def read(self):
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if (
            not isinstance(data, dict)
            or data.get("schema") != 1
            or not isinstance(data.get("presets"), list)
        ):
            raise ValueError("Unsupported preset file")
        result = []
        for item in data["presets"]:
            result.append(
                dict(
                    id=str(uuid.UUID(item["id"])),
                    name=name(item["name"]),
                    options=validate(item["options"]),
                )
            )
        if len({p["id"] for p in result}) != len(result):
            raise ValueError("Duplicate preset identifier")
        return result

    def save(self, title, options):
        title = name(title)
        rows = self.read()
        if any(p["name"].casefold() == title.casefold() for p in rows):
            raise ValueError("Duplicate preset name")
        row = dict(
            id=str(uuid.uuid4()), name=title, options=validate(deepcopy(options))
        )
        rows.append(row)
        self.write(rows)
        return row["id"]

    def delete(self, ident):
        rows = self.read()
        if not any(p["id"] == ident for p in rows):
            raise KeyError(ident)
        self.write([p for p in rows if p["id"] != ident])

    def write(self, rows):
        atomic(
            self.path,
            (
                json.dumps(dict(schema=1, presets=rows), ensure_ascii=False, indent=2)
                + "\n"
            ).encode("utf-8"),
        )

    def apply(self, ident, draft):
        row = next(p for p in self.read() if p["id"] == ident)
        options = validate(deepcopy(row["options"]))
        # Spider also has a personal preference. A preset must not rewrite it.
        options["extras"]["spider"] = draft.options["extras"]["spider"]
        draft.options = options
        draft._route_choices = {}
        draft.remember_choices()
        draft.consume_seed()
